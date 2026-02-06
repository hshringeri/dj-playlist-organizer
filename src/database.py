import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent / "data" / "dj_library.db"


@contextmanager
def get_db():
    """Context manager for database connections."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        conn.executescript("""
            -- Tracks from Spotify
            CREATE TABLE IF NOT EXISTS tracks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                artist TEXT NOT NULL,
                album TEXT,
                duration_ms INTEGER,
                uri TEXT,
                local_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Listening history (each play event)
            CREATE TABLE IF NOT EXISTS plays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id TEXT NOT NULL,
                played_at TIMESTAMP NOT NULL,
                source TEXT DEFAULT 'spotify',
                FOREIGN KEY (track_id) REFERENCES tracks(id),
                UNIQUE(track_id, played_at)
            );

            -- Aggregated listening stats per track
            CREATE TABLE IF NOT EXISTS track_stats (
                track_id TEXT PRIMARY KEY,
                play_count INTEGER DEFAULT 0,
                skip_count INTEGER DEFAULT 0,
                first_played TIMESTAMP,
                last_played TIMESTAMP,
                avg_play_hour REAL,
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            -- Audio features (computed locally with librosa)
            CREATE TABLE IF NOT EXISTS audio_features (
                track_id TEXT PRIMARY KEY,
                bpm REAL,
                energy REAL,
                danceability REAL,
                valence REAL,
                loudness REAL,
                key INTEGER,
                mode INTEGER,
                spectral_centroid REAL,
                spectral_rolloff REAL,
                zero_crossing_rate REAL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            -- Vibe classifications
            CREATE TABLE IF NOT EXISTS vibes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                energy_min REAL,
                energy_max REAL,
                valence_min REAL,
                valence_max REAL,
                bpm_min REAL,
                bpm_max REAL
            );

            -- Track to vibe mapping
            CREATE TABLE IF NOT EXISTS track_vibes (
                track_id TEXT,
                vibe_id INTEGER,
                confidence REAL DEFAULT 1.0,
                PRIMARY KEY (track_id, vibe_id),
                FOREIGN KEY (track_id) REFERENCES tracks(id),
                FOREIGN KEY (vibe_id) REFERENCES vibes(id)
            );

            -- Top tracks rankings (from Spotify)
            CREATE TABLE IF NOT EXISTS top_tracks (
                track_id TEXT,
                time_range TEXT,
                rank INTEGER,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (track_id, time_range),
                FOREIGN KEY (track_id) REFERENCES tracks(id)
            );

            -- Indexes for common queries
            CREATE INDEX IF NOT EXISTS idx_plays_track ON plays(track_id);
            CREATE INDEX IF NOT EXISTS idx_plays_time ON plays(played_at);
            CREATE INDEX IF NOT EXISTS idx_track_stats_count ON track_stats(play_count DESC);
            CREATE INDEX IF NOT EXISTS idx_audio_bpm ON audio_features(bpm);
            CREATE INDEX IF NOT EXISTS idx_audio_energy ON audio_features(energy);
        """)
        print(f"Database initialized at {DB_PATH}")


def _upsert_track(conn, track: dict) -> None:
    """Insert or update a track (internal, uses existing connection)."""
    conn.execute("""
        INSERT INTO tracks (id, name, artist, album, duration_ms, uri, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            artist = excluded.artist,
            album = excluded.album,
            duration_ms = excluded.duration_ms,
            uri = excluded.uri,
            updated_at = CURRENT_TIMESTAMP
    """, (track["id"], track["name"], track["artist"],
          track.get("album"), track.get("duration_ms"), track.get("uri")))


def upsert_track(track: dict) -> None:
    """Insert or update a track."""
    with get_db() as conn:
        _upsert_track(conn, track)


def record_play(track_id: str, played_at: str) -> None:
    """Record a play event and update stats."""
    with get_db() as conn:
        # Insert play event
        conn.execute("""
            INSERT OR IGNORE INTO plays (track_id, played_at)
            VALUES (?, ?)
        """, (track_id, played_at))

        # Update aggregated stats
        conn.execute("""
            INSERT INTO track_stats (track_id, play_count, first_played, last_played)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(track_id) DO UPDATE SET
                play_count = play_count + 1,
                first_played = MIN(first_played, excluded.first_played),
                last_played = MAX(last_played, excluded.last_played)
        """, (track_id, played_at, played_at))


def save_top_tracks(tracks: list[dict], time_range: str) -> None:
    """Save top tracks ranking."""
    with get_db() as conn:
        # Clear old rankings for this time range
        conn.execute("DELETE FROM top_tracks WHERE time_range = ?", (time_range,))

        for track in tracks:
            _upsert_track(conn, track)
            conn.execute("""
                INSERT INTO top_tracks (track_id, time_range, rank)
                VALUES (?, ?, ?)
            """, (track["id"], time_range, track["rank"]))


def get_most_played(limit: int = 50) -> list[dict]:
    """Get most played tracks."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT t.*, ts.play_count, ts.last_played
            FROM tracks t
            JOIN track_stats ts ON t.id = ts.track_id
            ORDER BY ts.play_count DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]


def get_tracks_by_vibe(vibe_name: str) -> list[dict]:
    """Get tracks for a specific vibe."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT t.*, af.bpm, af.energy, af.valence
            FROM tracks t
            JOIN track_vibes tv ON t.id = tv.track_id
            JOIN vibes v ON tv.vibe_id = v.id
            LEFT JOIN audio_features af ON t.id = af.track_id
            WHERE v.name = ?
            ORDER BY tv.confidence DESC
        """, (vibe_name,)).fetchall()
        return [dict(row) for row in rows]


def get_stats() -> dict:
    """Get database statistics."""
    with get_db() as conn:
        stats = {}
        stats["total_tracks"] = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        stats["total_plays"] = conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0]
        stats["analyzed_tracks"] = conn.execute("SELECT COUNT(*) FROM audio_features").fetchone()[0]
        stats["vibes"] = conn.execute("SELECT COUNT(*) FROM vibes").fetchone()[0]
        return stats


if __name__ == "__main__":
    init_db()
    print("\nDatabase stats:", get_stats())
