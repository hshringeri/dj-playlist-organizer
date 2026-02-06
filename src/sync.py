from datetime import datetime
from spotify_history import get_recently_played, get_top_tracks, get_saved_tracks
from database import init_db, upsert_track, record_play, save_top_tracks, get_stats


def sync_recently_played() -> int:
    """Sync recently played tracks to database."""
    tracks = get_recently_played(limit=50)
    count = 0

    for track in tracks:
        upsert_track(track)
        record_play(track["id"], track["played_at"])
        count += 1

    return count


def sync_top_tracks() -> dict:
    """Sync top tracks for all time ranges."""
    counts = {}

    for time_range in ["short_term", "medium_term", "long_term"]:
        tracks = get_top_tracks(time_range=time_range, limit=50)
        save_top_tracks(tracks, time_range)
        counts[time_range] = len(tracks)

    return counts


def sync_saved_tracks(limit: int = None) -> int:
    """Sync saved/liked tracks to database."""
    count = 0

    for track in get_saved_tracks(limit=limit):
        upsert_track(track)
        count += 1
        if count % 100 == 0:
            print(f"  Synced {count} saved tracks...")

    return count


def full_sync(include_saved: bool = False, saved_limit: int = None) -> dict:
    """Run a full sync of all Spotify data."""
    print("Starting full sync...")
    print("-" * 40)

    results = {
        "timestamp": datetime.now().isoformat(),
        "recently_played": 0,
        "top_tracks": {},
        "saved_tracks": 0,
    }

    print("Syncing recently played...")
    results["recently_played"] = sync_recently_played()
    print(f"  {results['recently_played']} plays recorded")

    print("Syncing top tracks...")
    results["top_tracks"] = sync_top_tracks()
    for tr, count in results["top_tracks"].items():
        print(f"  {tr}: {count} tracks")

    if include_saved:
        print("Syncing saved tracks...")
        results["saved_tracks"] = sync_saved_tracks(limit=saved_limit)
        print(f"  {results['saved_tracks']} saved tracks")

    print("-" * 40)
    print("Sync complete!")
    return results


if __name__ == "__main__":
    init_db()

    print("\n" + "=" * 60)
    print("SPOTIFY SYNC")
    print("=" * 60 + "\n")

    results = full_sync(include_saved=False)

    print("\n" + "=" * 60)
    print("DATABASE STATS")
    print("=" * 60)
    stats = get_stats()
    for key, val in stats.items():
        print(f"  {key}: {val}")
