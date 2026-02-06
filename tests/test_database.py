import pytest
import database


class TestDatabaseInit:
    def test_init_creates_tables(self, temp_db):
        """Database init should create all required tables."""
        with database.get_db() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {t[0] for t in tables}

        expected_tables = {
            "tracks",
            "plays",
            "track_stats",
            "audio_features",
            "vibes",
            "track_vibes",
            "top_tracks",
        }
        assert expected_tables.issubset(table_names)

    def test_init_creates_indexes(self, temp_db):
        """Database init should create indexes."""
        with database.get_db() as conn:
            indexes = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            index_names = {i[0] for i in indexes}

        assert "idx_plays_track" in index_names
        assert "idx_audio_bpm" in index_names


class TestUpsertTrack:
    def test_insert_new_track(self, temp_db, sample_track):
        """Should insert a new track."""
        database.upsert_track(sample_track)

        with database.get_db() as conn:
            row = conn.execute(
                "SELECT * FROM tracks WHERE id = ?", (sample_track["id"],)
            ).fetchone()

        assert row is not None
        assert row["name"] == sample_track["name"]
        assert row["artist"] == sample_track["artist"]

    def test_update_existing_track(self, temp_db, sample_track):
        """Should update an existing track."""
        database.upsert_track(sample_track)

        updated_track = sample_track.copy()
        updated_track["name"] = "Updated Name"
        database.upsert_track(updated_track)

        with database.get_db() as conn:
            row = conn.execute(
                "SELECT * FROM tracks WHERE id = ?", (sample_track["id"],)
            ).fetchone()

        assert row["name"] == "Updated Name"

    def test_upsert_preserves_count(self, temp_db, sample_track):
        """Upserting should not duplicate tracks."""
        database.upsert_track(sample_track)
        database.upsert_track(sample_track)
        database.upsert_track(sample_track)

        with database.get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]

        assert count == 1


class TestRecordPlay:
    def test_record_play_creates_event(self, temp_db, sample_track):
        """Should create a play event."""
        database.upsert_track(sample_track)
        database.record_play(sample_track["id"], "2024-01-15T12:00:00Z")

        with database.get_db() as conn:
            play = conn.execute(
                "SELECT * FROM plays WHERE track_id = ?", (sample_track["id"],)
            ).fetchone()

        assert play is not None
        assert play["played_at"] == "2024-01-15T12:00:00Z"

    def test_record_play_updates_stats(self, temp_db, sample_track):
        """Should update track stats."""
        database.upsert_track(sample_track)
        database.record_play(sample_track["id"], "2024-01-15T12:00:00Z")
        database.record_play(sample_track["id"], "2024-01-16T12:00:00Z")

        with database.get_db() as conn:
            stats = conn.execute(
                "SELECT * FROM track_stats WHERE track_id = ?", (sample_track["id"],)
            ).fetchone()

        assert stats["play_count"] == 2

    def test_duplicate_play_ignored(self, temp_db, sample_track):
        """Duplicate play events should be ignored."""
        database.upsert_track(sample_track)
        database.record_play(sample_track["id"], "2024-01-15T12:00:00Z")
        database.record_play(sample_track["id"], "2024-01-15T12:00:00Z")

        with database.get_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM plays WHERE track_id = ?", (sample_track["id"],)
            ).fetchone()[0]

        assert count == 1


class TestSaveTopTracks:
    def test_save_top_tracks(self, temp_db, sample_tracks):
        """Should save top tracks with rankings."""
        database.save_top_tracks(sample_tracks, "medium_term")

        with database.get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM top_tracks WHERE time_range = ? ORDER BY rank",
                ("medium_term",),
            ).fetchall()

        assert len(rows) == 5
        assert rows[0]["rank"] == 1
        assert rows[4]["rank"] == 5

    def test_save_top_tracks_replaces_old(self, temp_db, sample_tracks):
        """Saving should replace old rankings."""
        database.save_top_tracks(sample_tracks, "medium_term")
        database.save_top_tracks(sample_tracks[:2], "medium_term")

        with database.get_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM top_tracks WHERE time_range = ?",
                ("medium_term",),
            ).fetchone()[0]

        assert count == 2


class TestGetMostPlayed:
    def test_get_most_played_ordered(self, temp_db, sample_tracks):
        """Should return tracks ordered by play count."""
        for track in sample_tracks:
            database.upsert_track(track)
            # Give each track different play counts
            for _ in range(5 - track["rank"]):
                database.record_play(
                    track["id"], f"2024-01-{15 + track['rank']:02d}T{_:02d}:00:00Z"
                )

        most_played = database.get_most_played(limit=3)

        assert len(most_played) == 3
        assert most_played[0]["play_count"] >= most_played[1]["play_count"]


class TestGetStats:
    def test_get_stats_empty(self, temp_db):
        """Should return zeros for empty database."""
        stats = database.get_stats()

        assert stats["total_tracks"] == 0
        assert stats["total_plays"] == 0

    def test_get_stats_with_data(self, temp_db, sample_tracks):
        """Should return correct counts."""
        for track in sample_tracks:
            database.upsert_track(track)
            database.record_play(track["id"], track["played_at"])

        stats = database.get_stats()

        assert stats["total_tracks"] == 5
        assert stats["total_plays"] == 5
