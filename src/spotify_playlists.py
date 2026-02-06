from datetime import datetime
from typing import Optional
from spotify_auth import get_spotify_client
from database import get_db


def get_user_id() -> str:
    """Get current user's Spotify ID."""
    sp = get_spotify_client()
    return sp.current_user()["id"]


def create_playlist(
    name: str,
    description: str = "",
    public: bool = False,
) -> dict:
    """Create a new Spotify playlist."""
    sp = get_spotify_client()
    user_id = get_user_id()

    playlist = sp.user_playlist_create(
        user=user_id,
        name=name,
        public=public,
        description=description,
    )

    return {
        "id": playlist["id"],
        "name": playlist["name"],
        "url": playlist["external_urls"]["spotify"],
        "public": playlist["public"],
    }


def add_tracks_to_playlist(playlist_id: str, track_uris: list[str]) -> int:
    """
    Add tracks to a playlist.

    Returns number of tracks added.
    """
    sp = get_spotify_client()

    # Spotify API limit: 100 tracks per request
    added = 0
    for i in range(0, len(track_uris), 100):
        batch = track_uris[i:i + 100]
        sp.playlist_add_items(playlist_id, batch)
        added += len(batch)

    return added


def create_playlist_from_track_ids(
    name: str,
    track_ids: list[str],
    description: str = "",
    public: bool = False,
) -> dict:
    """Create playlist from database track IDs."""
    # Convert IDs to URIs
    track_uris = [f"spotify:track:{tid}" for tid in track_ids]

    playlist = create_playlist(name, description, public)
    added = add_tracks_to_playlist(playlist["id"], track_uris)

    return {**playlist, "tracks_added": added}


def create_top_tracks_playlist(
    time_range: str = "medium_term",
    limit: int = 50,
    public: bool = False,
) -> dict:
    """Create playlist from user's top tracks."""
    time_labels = {
        "short_term": "Last 4 Weeks",
        "medium_term": "Last 6 Months",
        "long_term": "All Time",
    }

    with get_db() as conn:
        rows = conn.execute("""
            SELECT track_id FROM top_tracks
            WHERE time_range = ?
            ORDER BY rank
            LIMIT ?
        """, (time_range, limit)).fetchall()

    track_ids = [row[0] for row in rows]

    if not track_ids:
        raise ValueError(f"No top tracks found for {time_range}")

    name = f"Top {limit} - {time_labels.get(time_range, time_range)}"
    description = f"Auto-generated from your top tracks ({time_labels.get(time_range)})"

    return create_playlist_from_track_ids(name, track_ids, description, public)


def create_recently_played_playlist(
    limit: int = 50,
    public: bool = False,
) -> dict:
    """Create playlist from recently played tracks (unique)."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT track_id
            FROM plays
            ORDER BY played_at DESC
            LIMIT ?
        """, (limit,)).fetchall()

    track_ids = [row[0] for row in rows]

    if not track_ids:
        raise ValueError("No recently played tracks found")

    name = f"Recently Played - {datetime.now().strftime('%b %d')}"
    description = "Auto-generated from your recent listening history"

    return create_playlist_from_track_ids(name, track_ids, description, public)


def create_most_played_playlist(
    limit: int = 50,
    public: bool = False,
) -> dict:
    """Create playlist from most played tracks."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT track_id, play_count
            FROM track_stats
            ORDER BY play_count DESC
            LIMIT ?
        """, (limit,)).fetchall()

    track_ids = [row[0] for row in rows]

    if not track_ids:
        raise ValueError("No play stats found - run sync first")

    name = f"Most Played - {datetime.now().strftime('%b %Y')}"
    description = f"Your {limit} most played tracks"

    return create_playlist_from_track_ids(name, track_ids, description, public)


def create_time_based_playlist(
    hour_start: int,
    hour_end: int,
    name: str,
    limit: int = 50,
    public: bool = False,
) -> dict:
    """
    Create playlist from tracks played during specific hours.

    hour_start/hour_end: 0-23 (e.g., 22, 4 for late night)
    """
    with get_db() as conn:
        # Handle wrap-around (e.g., 22:00 to 04:00)
        if hour_start <= hour_end:
            rows = conn.execute("""
                SELECT track_id, COUNT(*) as cnt
                FROM plays
                WHERE CAST(strftime('%H', played_at) AS INTEGER) >= ?
                  AND CAST(strftime('%H', played_at) AS INTEGER) < ?
                GROUP BY track_id
                ORDER BY cnt DESC
                LIMIT ?
            """, (hour_start, hour_end, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT track_id, COUNT(*) as cnt
                FROM plays
                WHERE CAST(strftime('%H', played_at) AS INTEGER) >= ?
                   OR CAST(strftime('%H', played_at) AS INTEGER) < ?
                GROUP BY track_id
                ORDER BY cnt DESC
                LIMIT ?
            """, (hour_start, hour_end, limit)).fetchall()

    track_ids = [row[0] for row in rows]

    if not track_ids:
        raise ValueError(f"No tracks found for hours {hour_start}-{hour_end}")

    description = f"Tracks you listen to between {hour_start}:00-{hour_end}:00"

    return create_playlist_from_track_ids(name, track_ids, description, public)


def create_all_smart_playlists(public: bool = False) -> list[dict]:
    """Create a set of smart playlists based on listening patterns."""
    results = []

    # Top tracks for each time range
    for time_range in ["short_term", "medium_term", "long_term"]:
        try:
            result = create_top_tracks_playlist(time_range, limit=50, public=public)
            results.append({"type": f"top_{time_range}", **result})
            print(f"Created: {result['name']}")
        except Exception as e:
            print(f"Skipped top {time_range}: {e}")

    # Most played
    try:
        result = create_most_played_playlist(limit=50, public=public)
        results.append({"type": "most_played", **result})
        print(f"Created: {result['name']}")
    except Exception as e:
        print(f"Skipped most played: {e}")

    # Time-based playlists
    time_slots = [
        (6, 12, "Morning Vibes"),
        (12, 18, "Afternoon Energy"),
        (18, 22, "Evening Session"),
        (22, 4, "Late Night"),
    ]

    for hour_start, hour_end, name in time_slots:
        try:
            result = create_time_based_playlist(
                hour_start, hour_end, name, limit=30, public=public
            )
            results.append({"type": "time_based", **result})
            print(f"Created: {result['name']}")
        except Exception as e:
            print(f"Skipped {name}: {e}")

    return results


def create_dj_folder_playlist(
    folder_name: str,
    bpm_min: float = 0,
    bpm_max: float = 300,
    limit: int = 50,
    public: bool = False,
) -> dict:
    """
    Create a Spotify playlist for a specific DJ folder.

    Tracks are ordered by play count (most played first).
    """
    with get_db() as conn:
        # Get folder description
        folder = conn.execute(
            "SELECT description FROM vibes WHERE name = ?", (folder_name,)
        ).fetchone()

        if not folder:
            raise ValueError(f"DJ folder not found: {folder_name}")

        # Get tracks in this folder, filtered by BPM
        rows = conn.execute("""
            SELECT t.id
            FROM tracks t
            JOIN track_vibes tv ON t.id = tv.track_id
            JOIN vibes v ON tv.vibe_id = v.id
            JOIN audio_features af ON t.id = af.track_id
            LEFT JOIN track_stats ts ON t.id = ts.track_id
            WHERE v.name = ?
              AND af.bpm >= ? AND af.bpm <= ?
            ORDER BY COALESCE(ts.play_count, 0) DESC, tv.confidence DESC
            LIMIT ?
        """, (folder_name, bpm_min, bpm_max, limit)).fetchall()

    track_ids = [row[0] for row in rows]

    if not track_ids:
        raise ValueError(f"No tracks found in folder: {folder_name}")

    # Create playlist name with BPM range if filtered
    if bpm_min > 0 or bpm_max < 300:
        name = f"DJ | {folder_name} | {bpm_min:.0f}-{bpm_max:.0f} BPM"
    else:
        name = f"DJ | {folder_name}"

    description = f"{folder['description'][:200]}"

    return create_playlist_from_track_ids(name, track_ids, description, public)


def create_all_dj_folder_playlists(
    public: bool = False,
    min_tracks: int = 3,
) -> list[dict]:
    """
    Create Spotify playlists for all DJ folders that have tracks.

    Only creates playlists for folders with at least min_tracks.
    """
    from vibe_classifier import DJ_FOLDERS

    results = []

    # Group folders by category for nicer output
    categories = {
        "SET POSITION": ["Openers", "Builders", "Peak Time", "Weapons", "Closers"],
        "TEXTURE": ["Organic", "Synthetic", "Gritty"],
        "RHYTHM": ["4x4 Locked", "Broken Beat", "Halftime / Slow", "Fast & Chaotic"],
        "EMOTIONAL": ["Melancholic", "Euphoric", "Hypnotic", "Aggressive"],
        "FUNCTIONAL": ["Transitions", "Curveballs"],
    }

    for category, folder_names in categories.items():
        print(f"\n  {category}")
        print("  " + "-" * 40)

        for folder_name in folder_names:
            try:
                result = create_dj_folder_playlist(folder_name, public=public)
                if result["tracks_added"] >= min_tracks:
                    results.append({"category": category, **result})
                    print(f"    {folder_name:20} | {result['tracks_added']:3} tracks")
                else:
                    print(f"    {folder_name:20} | skipped ({result['tracks_added']} tracks)")
            except ValueError as e:
                print(f"    {folder_name:20} | skipped (no tracks)")
            except Exception as e:
                print(f"    {folder_name:20} | error: {e}")

    return results


def create_dj_folder_with_bpm_splits(
    folder_name: str,
    bpm_bucket_size: int = 5,
    min_tracks: int = 3,
    public: bool = False,
) -> list[dict]:
    """
    Create multiple playlists for a DJ folder, split by BPM ranges.

    E.g., "Peak Time" becomes:
    - DJ | Peak Time | 122-127 BPM
    - DJ | Peak Time | 127-132 BPM
    """
    from vibe_classifier import get_bpm_buckets_for_folder

    buckets = get_bpm_buckets_for_folder(folder_name, bpm_bucket_size)
    results = []

    for bucket in buckets:
        if bucket["track_count"] < min_tracks:
            continue

        # Parse BPM range from bucket
        bpm_range = bucket["bpm_range"]
        bpm_min, bpm_max = map(float, bpm_range.split("-"))

        try:
            result = create_dj_folder_playlist(
                folder_name,
                bpm_min=bpm_min,
                bpm_max=bpm_max,
                public=public,
            )
            results.append(result)
            print(f"  Created: {result['name']} ({result['tracks_added']} tracks)")
        except Exception as e:
            print(f"  Skipped {folder_name} {bpm_range}: {e}")

    return results


def create_full_dj_library(
    split_by_bpm: bool = True,
    bpm_bucket_size: int = 5,
    min_tracks: int = 3,
    public: bool = False,
) -> dict:
    """
    Create the complete DJ playlist library.

    If split_by_bpm is True, creates sub-playlists per BPM range within each folder.
    """
    from vibe_classifier import DJ_FOLDERS

    results = {
        "folders_created": 0,
        "playlists_created": 0,
        "total_tracks": 0,
        "playlists": [],
    }

    categories = {
        "SET POSITION": ["Openers", "Builders", "Peak Time", "Weapons", "Closers"],
        "TEXTURE": ["Organic", "Synthetic", "Gritty"],
        "RHYTHM": ["4x4 Locked", "Broken Beat", "Halftime / Slow", "Fast & Chaotic"],
        "EMOTIONAL": ["Melancholic", "Euphoric", "Hypnotic", "Aggressive"],
        "FUNCTIONAL": ["Transitions", "Curveballs"],
    }

    for category, folder_names in categories.items():
        print(f"\n{'='*50}")
        print(f"  {category}")
        print(f"{'='*50}")

        for folder_name in folder_names:
            if split_by_bpm:
                playlists = create_dj_folder_with_bpm_splits(
                    folder_name,
                    bpm_bucket_size=bpm_bucket_size,
                    min_tracks=min_tracks,
                    public=public,
                )
            else:
                try:
                    playlist = create_dj_folder_playlist(folder_name, public=public)
                    playlists = [playlist] if playlist["tracks_added"] >= min_tracks else []
                    if playlists:
                        print(f"  Created: {playlist['name']} ({playlist['tracks_added']} tracks)")
                except Exception as e:
                    playlists = []
                    print(f"  Skipped {folder_name}: {e}")

            if playlists:
                results["folders_created"] += 1
                results["playlists_created"] += len(playlists)
                results["total_tracks"] += sum(p["tracks_added"] for p in playlists)
                results["playlists"].extend(playlists)

    return results


def list_created_playlists() -> list[dict]:
    """List playlists created by this app (by naming pattern)."""
    sp = get_spotify_client()
    user_id = get_user_id()

    playlists = []
    results = sp.current_user_playlists(limit=50)

    # Include DJ folder playlists
    patterns = ["Top 50", "Top 30", "Most Played", "Recently Played",
                "Morning", "Afternoon", "Evening", "Late Night",
                "DJ |"]

    for item in results["items"]:
        if item["owner"]["id"] == user_id:
            if any(p in item["name"] for p in patterns):
                playlists.append({
                    "id": item["id"],
                    "name": item["name"],
                    "tracks": item["tracks"]["total"],
                    "public": item["public"],
                    "url": item["external_urls"]["spotify"],
                })

    return playlists


if __name__ == "__main__":
    import sys
    from database import init_db

    init_db()

    print("=" * 60)
    print("SPOTIFY PLAYLIST GENERATOR")
    print("=" * 60)

    # Check command line args
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "smart":
            print("\nCreating smart playlists (private)...\n")
            results = create_all_smart_playlists(public=False)
            print(f"\nCreated {len(results)} playlists")

        elif cmd == "dj":
            print("\nCreating DJ folder playlists (private)...\n")
            results = create_all_dj_folder_playlists(public=False)
            print(f"\nCreated {len(results)} playlists")

        elif cmd == "dj-bpm":
            print("\nCreating DJ folder playlists with BPM splits (private)...\n")
            results = create_full_dj_library(
                split_by_bpm=True,
                bpm_bucket_size=5,
                min_tracks=3,
                public=False,
            )
            print(f"\n{'='*50}")
            print(f"SUMMARY")
            print(f"{'='*50}")
            print(f"  Folders with tracks: {results['folders_created']}")
            print(f"  Playlists created:   {results['playlists_created']}")
            print(f"  Total tracks:        {results['total_tracks']}")

        elif cmd == "list":
            print("\nYour generated playlists:\n")
            playlists = list_created_playlists()
            for p in playlists:
                status = "public" if p["public"] else "private"
                print(f"  {p['name']:40} | {p['tracks']:3} tracks | {status}")

        else:
            print(f"Unknown command: {cmd}")
            print("\nUsage:")
            print("  python spotify_playlists.py smart    - Create smart playlists")
            print("  python spotify_playlists.py dj       - Create DJ folder playlists")
            print("  python spotify_playlists.py dj-bpm   - Create DJ playlists split by BPM")
            print("  python spotify_playlists.py list     - List created playlists")

    else:
        print("\nUsage:")
        print("  python spotify_playlists.py smart    - Create smart playlists (top tracks, time-based)")
        print("  python spotify_playlists.py dj       - Create DJ folder playlists")
        print("  python spotify_playlists.py dj-bpm   - Create DJ playlists split by BPM")
        print("  python spotify_playlists.py list     - List all created playlists")
        print("\nAll playlists are created as PRIVATE by default.")
