import sys
import pytest
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create a temporary database for testing."""
    import database
    db_path = tmp_path / "test_library.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_db()
    return db_path


@pytest.fixture
def sample_track():
    """Sample track data for testing."""
    return {
        "id": "test123",
        "name": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album",
        "duration_ms": 180000,
        "uri": "spotify:track:test123",
    }


@pytest.fixture
def sample_tracks():
    """Multiple sample tracks for testing."""
    return [
        {
            "id": f"track{i}",
            "name": f"Track {i}",
            "artist": f"Artist {i}",
            "album": f"Album {i}",
            "duration_ms": 180000 + i * 1000,
            "uri": f"spotify:track:track{i}",
            "rank": i + 1,
            "played_at": f"2024-01-{15+i:02d}T12:00:00Z",
        }
        for i in range(5)
    ]


@pytest.fixture
def mock_spotify_client(mocker):
    """Mock Spotify client for testing without API calls."""
    mock_client = mocker.MagicMock()

    mock_client.current_user.return_value = {
        "id": "test_user",
        "display_name": "Test User",
        "followers": {"total": 100},
    }

    mock_client.current_user_recently_played.return_value = {
        "items": [
            {
                "played_at": "2024-01-15T12:00:00Z",
                "track": {
                    "id": "track1",
                    "name": "Recent Track 1",
                    "artists": [{"name": "Artist 1"}],
                    "album": {"name": "Album 1"},
                    "duration_ms": 200000,
                    "uri": "spotify:track:track1",
                },
            },
            {
                "played_at": "2024-01-15T11:00:00Z",
                "track": {
                    "id": "track2",
                    "name": "Recent Track 2",
                    "artists": [{"name": "Artist 2"}, {"name": "Artist 2b"}],
                    "album": {"name": "Album 2"},
                    "duration_ms": 180000,
                    "uri": "spotify:track:track2",
                },
            },
        ]
    }

    mock_client.current_user_top_tracks.return_value = {
        "items": [
            {
                "id": f"top{i}",
                "name": f"Top Track {i}",
                "artists": [{"name": f"Top Artist {i}"}],
                "album": {"name": f"Top Album {i}"},
                "duration_ms": 200000,
                "popularity": 80 - i * 5,
                "uri": f"spotify:track:top{i}",
            }
            for i in range(3)
        ]
    }

    return mock_client
