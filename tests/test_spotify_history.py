import pytest
import spotify_history


class TestGetRecentlyPlayed:
    def test_returns_track_list(self, mocker, mock_spotify_client):
        """Should return a list of track dictionaries."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        tracks = spotify_history.get_recently_played(limit=50)

        assert isinstance(tracks, list)
        assert len(tracks) == 2

    def test_track_has_required_fields(self, mocker, mock_spotify_client):
        """Each track should have required fields."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        tracks = spotify_history.get_recently_played()
        track = tracks[0]

        assert "id" in track
        assert "name" in track
        assert "artist" in track
        assert "album" in track
        assert "duration_ms" in track
        assert "played_at" in track
        assert "uri" in track

    def test_multiple_artists_joined(self, mocker, mock_spotify_client):
        """Multiple artists should be joined with comma."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        tracks = spotify_history.get_recently_played()
        # Second track has two artists
        assert tracks[1]["artist"] == "Artist 2, Artist 2b"


class TestGetTopTracks:
    def test_returns_ranked_tracks(self, mocker, mock_spotify_client):
        """Should return tracks with rank field."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        tracks = spotify_history.get_top_tracks(time_range="medium_term")

        assert len(tracks) == 3
        assert tracks[0]["rank"] == 1
        assert tracks[1]["rank"] == 2
        assert tracks[2]["rank"] == 3

    def test_includes_time_range(self, mocker, mock_spotify_client):
        """Each track should include the time_range."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        tracks = spotify_history.get_top_tracks(time_range="short_term")

        for track in tracks:
            assert track["time_range"] == "short_term"

    def test_includes_popularity(self, mocker, mock_spotify_client):
        """Each track should include popularity score."""
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        tracks = spotify_history.get_top_tracks()

        for track in tracks:
            assert "popularity" in track
            assert isinstance(track["popularity"], int)


class TestGetSavedTracks:
    def test_yields_tracks(self, mocker, mock_spotify_client):
        """Should yield track dictionaries."""
        mock_spotify_client.current_user_saved_tracks.return_value = {
            "items": [
                {
                    "added_at": "2024-01-15T12:00:00Z",
                    "track": {
                        "id": "saved1",
                        "name": "Saved Track",
                        "artists": [{"name": "Saved Artist"}],
                        "album": {"name": "Saved Album"},
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

        tracks = list(spotify_history.get_saved_tracks(limit=10))

        assert len(tracks) == 1
        assert tracks[0]["id"] == "saved1"
        assert "added_at" in tracks[0]

    def test_respects_limit(self, mocker, mock_spotify_client):
        """Should stop after reaching limit."""
        mock_spotify_client.current_user_saved_tracks.return_value = {
            "items": [
                {
                    "added_at": f"2024-01-{i:02d}T12:00:00Z",
                    "track": {
                        "id": f"saved{i}",
                        "name": f"Saved Track {i}",
                        "artists": [{"name": "Artist"}],
                        "album": {"name": "Album"},
                        "duration_ms": 200000,
                        "uri": f"spotify:track:saved{i}",
                    },
                }
                for i in range(10)
            ],
            "next": "more_url",
        }
        mocker.patch(
            "spotify_history.get_spotify_client", return_value=mock_spotify_client
        )

        tracks = list(spotify_history.get_saved_tracks(limit=3))

        assert len(tracks) == 3
