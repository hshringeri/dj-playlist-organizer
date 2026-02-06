import pytest
import database
import sync


class TestSyncRecentlyPlayed:
    def test_syncs_tracks_to_db(self, temp_db, mocker, mock_spotify_client):
        """Should sync recently played tracks to database."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        count = sync.sync_recently_played()

        assert count == 2
        stats = database.get_stats()
        assert stats["total_tracks"] == 2
        assert stats["total_plays"] == 2

    def test_records_play_events(self, temp_db, mocker, mock_spotify_client):
        """Should create play events for each track."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        sync.sync_recently_played()

        with database.get_db() as conn:
            plays = conn.execute("SELECT * FROM plays").fetchall()

        assert len(plays) == 2


class TestSyncTopTracks:
    def test_syncs_all_time_ranges(self, temp_db, mocker, mock_spotify_client):
        """Should sync top tracks for all time ranges."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        counts = sync.sync_top_tracks()

        assert "short_term" in counts
        assert "medium_term" in counts
        assert "long_term" in counts
        assert counts["short_term"] == 3

    def test_saves_rankings(self, temp_db, mocker, mock_spotify_client):
        """Should save track rankings."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        sync.sync_top_tracks()

        with database.get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM top_tracks WHERE time_range = 'medium_term' ORDER BY rank"
            ).fetchall()

        assert len(rows) == 3
        assert rows[0]["rank"] == 1


class TestFullSync:
    def test_full_sync_without_saved(self, temp_db, mocker, mock_spotify_client):
        """Full sync should run without saved tracks."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        results = sync.full_sync(include_saved=False)

        assert results["recently_played"] == 2
        assert results["saved_tracks"] == 0
        assert "short_term" in results["top_tracks"]

    def test_full_sync_with_saved(self, temp_db, mocker, mock_spotify_client):
        """Full sync should include saved tracks when requested."""
        mock_spotify_client.current_user_saved_tracks.return_value = {
            "items": [
                {
                    "added_at": "2024-01-15T12:00:00Z",
                    "track": {
                        "id": "saved1",
                        "name": "Saved Track",
                        "artists": [{"name": "Artist"}],
                        "album": {"name": "Album"},
                        "duration_ms": 200000,
                        "uri": "spotify:track:saved1",
                    },
                }
            ],
            "next": None,
        }
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        results = sync.full_sync(include_saved=True)

        assert results["saved_tracks"] == 1

    def test_full_sync_returns_timestamp(self, temp_db, mocker, mock_spotify_client):
        """Full sync should include timestamp."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        results = sync.full_sync(include_saved=False)

        assert "timestamp" in results
