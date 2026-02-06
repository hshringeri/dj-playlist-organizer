import os
import re
from pathlib import Path
from difflib import SequenceMatcher
from typing import Optional
from database import get_db

# Supported audio formats
AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".aiff", ".aif", ".m4a", ".ogg", ".opus"}


def scan_music_directory(music_dir: str | Path) -> list[dict]:
    """
    Scan a directory for audio files.

    Returns list of dicts with: path, filename, artist_guess, title_guess
    """
    music_dir = Path(music_dir)
    if not music_dir.exists():
        raise FileNotFoundError(f"Directory not found: {music_dir}")

    files = []
    for root, dirs, filenames in os.walk(music_dir):
        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext in AUDIO_EXTENSIONS:
                file_path = Path(root) / filename
                parsed = parse_filename(filename)
                files.append({
                    "path": str(file_path),
                    "filename": filename,
                    "artist_guess": parsed.get("artist"),
                    "title_guess": parsed.get("title"),
                })

    return files


def parse_filename(filename: str) -> dict:
    """
    Parse artist and title from filename.

    Handles common patterns:
    - "Artist - Title.mp3"
    - "Artist_-_Title.mp3"
    - "01 Artist - Title.mp3"
    - "Title.mp3" (no artist)
    """
    # Remove extension
    name = Path(filename).stem

    # Remove track numbers at start
    name = re.sub(r"^\d+[\.\-_\s]+", "", name)

    # Try common separators
    for sep in [" - ", " _ ", "_-_", " – ", " — "]:
        if sep in name:
            parts = name.split(sep, 1)
            return {"artist": parts[0].strip(), "title": parts[1].strip()}

    # No separator found - assume it's just the title
    return {"artist": None, "title": name.strip()}


def normalize_string(s: str) -> str:
    """Normalize string for comparison."""
    if not s:
        return ""
    # Lowercase, remove special chars, normalize whitespace
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Remove common suffixes
    s = re.sub(r"\s*(original mix|extended mix|radio edit|remix|remaster(ed)?)\s*$", "", s, flags=re.I)
    return s


def similarity(a: str, b: str) -> float:
    """Calculate string similarity (0-1)."""
    a_norm = normalize_string(a)
    b_norm = normalize_string(b)
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def match_track_to_file(
    track_name: str,
    track_artist: str,
    files: list[dict],
    threshold: float = 0.7,
) -> Optional[dict]:
    """
    Find best matching local file for a Spotify track.

    Returns best match dict with 'path' and 'score', or None.
    """
    best_match = None
    best_score = 0

    for file in files:
        # Compare title
        title_score = similarity(track_name, file["title_guess"] or file["filename"])

        # Compare artist if available
        if file["artist_guess"] and track_artist:
            artist_score = similarity(track_artist, file["artist_guess"])
            # Weight: 60% title, 40% artist
            score = (title_score * 0.6) + (artist_score * 0.4)
        else:
            score = title_score * 0.8  # Penalize slightly for no artist match

        if score > best_score and score >= threshold:
            best_score = score
            best_match = {**file, "score": score}

    return best_match


def match_library(music_dir: str | Path, threshold: float = 0.7) -> dict:
    """
    Match all Spotify tracks in database to local files.

    Returns summary of matches.
    """
    print(f"Scanning: {music_dir}")
    files = scan_music_directory(music_dir)
    print(f"Found {len(files)} audio files")

    with get_db() as conn:
        tracks = conn.execute("""
            SELECT id, name, artist FROM tracks
            WHERE local_path IS NULL
        """).fetchall()

    results = {
        "total_tracks": len(tracks),
        "total_files": len(files),
        "matched": 0,
        "unmatched": 0,
        "matches": [],
    }

    print(f"Matching {len(tracks)} Spotify tracks...")

    for track in tracks:
        track_id, name, artist = track

        match = match_track_to_file(name, artist, files, threshold)

        if match:
            # Save match to database
            with get_db() as conn:
                conn.execute(
                    "UPDATE tracks SET local_path = ? WHERE id = ?",
                    (match["path"], track_id)
                )
            results["matched"] += 1
            results["matches"].append({
                "track": f"{artist} - {name}",
                "file": match["filename"],
                "score": match["score"],
            })
        else:
            results["unmatched"] += 1

    return results


def get_matched_tracks() -> list[dict]:
    """Get all tracks with local file paths."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, name, artist, local_path
            FROM tracks
            WHERE local_path IS NOT NULL
        """).fetchall()
        return [dict(row) for row in rows]


def get_unmatched_tracks() -> list[dict]:
    """Get tracks without local file paths."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, name, artist
            FROM tracks
            WHERE local_path IS NULL
        """).fetchall()
        return [dict(row) for row in rows]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python library_matcher.py <music_directory>")
        print("\nExample: python library_matcher.py ~/Music")
        print("         python library_matcher.py /Volumes/USB/DJ")
        sys.exit(1)

    music_dir = sys.argv[1]

    results = match_library(music_dir)

    print("\n" + "=" * 60)
    print("MATCHING RESULTS")
    print("=" * 60)
    print(f"Audio files found:  {results['total_files']}")
    print(f"Spotify tracks:     {results['total_tracks']}")
    print(f"Matched:            {results['matched']}")
    print(f"Unmatched:          {results['unmatched']}")

    if results["matches"]:
        print("\nSample matches:")
        for m in results["matches"][:10]:
            print(f"  {m['track'][:40]:40} -> {m['file'][:30]} ({m['score']:.0%})")
