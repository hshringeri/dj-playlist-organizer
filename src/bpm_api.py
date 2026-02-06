"""
External BPM API integration using GetSongBPM.

Free API - requires attribution to getsongbpm.com
Sign up at: https://getsongbpm.com/api
"""

import os
import time
import requests
from typing import Optional
from database import get_db
from dotenv import load_dotenv

load_dotenv()

GETSONGBPM_API_KEY = os.getenv("GETSONGBPM_API_KEY")
BASE_URL = "https://api.getsongbpm.com"


def search_song(artist: str, title: str) -> Optional[dict]:
    """
    Search for a song on GetSongBPM.

    Returns dict with: id, title, artist, tempo, key_of, time_sig, etc.
    """
    if not GETSONGBPM_API_KEY:
        raise ValueError("GETSONGBPM_API_KEY not set in .env")

    # Clean up search terms
    artist = artist.split(",")[0].strip()  # Take first artist if multiple
    title = title.split("(")[0].split("-")[0].strip()  # Remove remix/version info

    params = {
        "api_key": GETSONGBPM_API_KEY,
        "type": "both",
        "lookup": f"song:{title} artist:{artist}",
    }

    try:
        response = requests.get(f"{BASE_URL}/search/", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("search") and len(data["search"]) > 0:
            return data["search"][0]
        return None

    except requests.RequestException as e:
        print(f"API error: {e}")
        return None


def get_song_details(song_id: str) -> Optional[dict]:
    """Get detailed info for a song by GetSongBPM ID."""
    if not GETSONGBPM_API_KEY:
        raise ValueError("GETSONGBPM_API_KEY not set in .env")

    params = {
        "api_key": GETSONGBPM_API_KEY,
        "type": "song",
        "id": song_id,
    }

    try:
        response = requests.get(f"{BASE_URL}/song/", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("song")
    except requests.RequestException as e:
        print(f"API error: {e}")
        return None


def fetch_and_store_bpm(track_id: str, artist: str, title: str) -> Optional[dict]:
    """
    Fetch BPM data from API and store in database.

    Returns the audio features dict or None if not found.
    """
    result = search_song(artist, title)

    if not result:
        return None

    # Extract data
    tempo = result.get("tempo")
    key_of = result.get("key_of", "")
    time_sig = result.get("time_sig", "4/4")

    if not tempo:
        return None

    # Parse key into numeric format (0-11)
    key_map = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
               "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
               "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}

    key_num = 0
    mode = 1  # Default major
    if key_of:
        # Parse "G minor" or "C major" or just "G"
        parts = key_of.split()
        if parts:
            key_num = key_map.get(parts[0], 0)
            if len(parts) > 1 and "min" in parts[1].lower():
                mode = 0

    features = {
        "bpm": float(tempo),
        "key": key_num,
        "mode": mode,
        "energy": 0.5,  # Default - API doesn't provide this
        "valence": 0.5,
        "danceability": 0.5,
        "loudness": -10.0,
        "spectral_centroid": 0.0,
        "spectral_rolloff": 0.0,
        "zero_crossing_rate": 0.0,
    }

    # Store in database
    with get_db() as conn:
        conn.execute("""
            INSERT INTO audio_features
                (track_id, bpm, energy, danceability, valence, loudness,
                 key, mode, spectral_centroid, spectral_rolloff, zero_crossing_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(track_id) DO UPDATE SET
                bpm = excluded.bpm,
                key = excluded.key,
                mode = excluded.mode,
                analyzed_at = CURRENT_TIMESTAMP
        """, (
            track_id,
            features["bpm"],
            features["energy"],
            features["danceability"],
            features["valence"],
            features["loudness"],
            features["key"],
            features["mode"],
            features["spectral_centroid"],
            features["spectral_rolloff"],
            features["zero_crossing_rate"],
        ))

    return features


def fetch_all_tracks_bpm(rate_limit_delay: float = 0.5) -> dict:
    """
    Fetch BPM for all tracks in database.

    rate_limit_delay: seconds between API calls (be nice to free API)
    """
    if not GETSONGBPM_API_KEY:
        print("ERROR: GETSONGBPM_API_KEY not set in .env")
        print("Sign up at: https://getsongbpm.com/api")
        return {"error": "No API key"}

    with get_db() as conn:
        # Get tracks without audio features
        tracks = conn.execute("""
            SELECT t.id, t.name, t.artist
            FROM tracks t
            LEFT JOIN audio_features af ON t.id = af.track_id
            WHERE af.track_id IS NULL
        """).fetchall()

    results = {
        "total": len(tracks),
        "found": 0,
        "not_found": 0,
        "errors": 0,
    }

    print(f"Fetching BPM for {len(tracks)} tracks...")
    print("-" * 50)

    for i, (track_id, name, artist) in enumerate(tracks):
        try:
            features = fetch_and_store_bpm(track_id, artist, name)

            if features:
                results["found"] += 1
                print(f"  [{i+1}/{len(tracks)}] {artist} - {name}")
                print(f"           BPM: {features['bpm']:.0f}, Key: {features['key']}")
            else:
                results["not_found"] += 1
                print(f"  [{i+1}/{len(tracks)}] {artist} - {name} [NOT FOUND]")

            # Rate limiting
            time.sleep(rate_limit_delay)

        except Exception as e:
            results["errors"] += 1
            print(f"  [{i+1}/{len(tracks)}] {artist} - {name} [ERROR: {e}]")

    return results


def get_coverage_stats() -> dict:
    """Get stats on how many tracks have BPM data."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        with_bpm = conn.execute(
            "SELECT COUNT(*) FROM audio_features WHERE bpm > 0"
        ).fetchone()[0]

    return {
        "total_tracks": total,
        "with_bpm": with_bpm,
        "missing_bpm": total - with_bpm,
        "coverage": f"{(with_bpm/total*100):.1f}%" if total > 0 else "0%",
    }


if __name__ == "__main__":
    from database import init_db

    init_db()

    print("=" * 60)
    print("BPM API FETCHER (GetSongBPM)")
    print("=" * 60)

    # Check API key
    if not GETSONGBPM_API_KEY:
        print("\nNo API key found!")
        print("\n1. Sign up at: https://getsongbpm.com/api")
        print("2. Add to your .env file:")
        print("   GETSONGBPM_API_KEY=your_key_here")
        exit(1)

    print("\nCurrent coverage:")
    stats = get_coverage_stats()
    print(f"  Total tracks:  {stats['total_tracks']}")
    print(f"  With BPM:      {stats['with_bpm']}")
    print(f"  Missing:       {stats['missing_bpm']}")
    print(f"  Coverage:      {stats['coverage']}")

    if stats["missing_bpm"] > 0:
        print(f"\nFetching BPM for {stats['missing_bpm']} tracks...")
        print("(This may take a while due to rate limiting)\n")

        results = fetch_all_tracks_bpm(rate_limit_delay=0.5)

        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"  Found:     {results['found']}")
        print(f"  Not found: {results['not_found']}")
        print(f"  Errors:    {results['errors']}")

        print("\nUpdated coverage:")
        stats = get_coverage_stats()
        print(f"  Coverage: {stats['coverage']}")
    else:
        print("\nAll tracks already have BPM data!")
