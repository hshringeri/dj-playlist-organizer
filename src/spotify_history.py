from datetime import datetime
from typing import Iterator
from spotify_auth import get_spotify_client


def get_recently_played(limit: int = 50) -> list[dict]:
    """Fetch recently played tracks (max 50 per Spotify API limit)."""
    sp = get_spotify_client()
    results = sp.current_user_recently_played(limit=limit)

    tracks = []
    for item in results["items"]:
        track = item["track"]
        tracks.append({
            "id": track["id"],
            "name": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": track["album"]["name"],
            "duration_ms": track["duration_ms"],
            "played_at": item["played_at"],
            "uri": track["uri"],
        })
    return tracks


def get_top_tracks(time_range: str = "medium_term", limit: int = 50) -> list[dict]:
    """
    Fetch user's top tracks.

    time_range: short_term (4 weeks), medium_term (6 months), long_term (years)
    """
    sp = get_spotify_client()
    results = sp.current_user_top_tracks(limit=limit, time_range=time_range)

    tracks = []
    for i, track in enumerate(results["items"]):
        tracks.append({
            "id": track["id"],
            "name": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": track["album"]["name"],
            "duration_ms": track["duration_ms"],
            "popularity": track["popularity"],
            "rank": i + 1,
            "time_range": time_range,
            "uri": track["uri"],
        })
    return tracks


# NOTE: Spotify deprecated audio features API for new apps (Nov 2024)
# We'll use local audio analysis with librosa/essentia instead - this is
# actually better for DJ use since we can do deeper mixing analysis


def get_saved_tracks(limit: int = None) -> Iterator[dict]:
    """Fetch all saved/liked tracks (paginated)."""
    sp = get_spotify_client()
    offset = 0
    batch_size = 50
    count = 0

    while True:
        results = sp.current_user_saved_tracks(limit=batch_size, offset=offset)

        if not results["items"]:
            break

        for item in results["items"]:
            track = item["track"]
            yield {
                "id": track["id"],
                "name": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "album": track["album"]["name"],
                "duration_ms": track["duration_ms"],
                "added_at": item["added_at"],
                "uri": track["uri"],
            }
            count += 1
            if limit and count >= limit:
                return

        offset += batch_size
        if not results["next"]:
            break


if __name__ == "__main__":
    print("=" * 60)
    print("RECENTLY PLAYED (last 50)")
    print("=" * 60)
    recent = get_recently_played()
    for t in recent[:10]:
        print(f"  {t['name']} - {t['artist']}")
    print(f"  ... and {len(recent) - 10} more\n")

    print("=" * 60)
    print("TOP TRACKS - Short Term (4 weeks)")
    print("=" * 60)
    top_short = get_top_tracks("short_term")
    for t in top_short[:10]:
        print(f"  #{t['rank']} {t['name']} - {t['artist']}")

    print()
    print("=" * 60)
    print("TOP TRACKS - Medium Term (6 months)")
    print("=" * 60)
    top_medium = get_top_tracks("medium_term")
    for t in top_medium[:10]:
        print(f"  #{t['rank']} {t['name']} - {t['artist']}")

    print()
    print("=" * 60)
    print("TOP TRACKS - Long Term (all time)")
    print("=" * 60)
    top_long = get_top_tracks("long_term")
    for t in top_long[:10]:
        print(f"  #{t['rank']} {t['name']} - {t['artist']}")
