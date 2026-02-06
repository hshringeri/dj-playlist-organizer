import pytest
import spotify_auth


class TestTestConnection:
    def test_returns_user_info(self, mocker, mock_spotify_client):
        """Should return user info dictionary."""
        mocker.patch(
            "spotify_auth.get_spotify_client", return_value=mock_spotify_client
        )

        result = spotify_auth.test_connection()

        assert result["id"] == "test_user"
        assert result["display_name"] == "Test User"
        assert result["followers"] == 100

    def test_calls_current_user(self, mocker, mock_spotify_client):
        """Should call current_user on the client."""
        mocker.patch(
            "spotify_auth.get_spotify_client", return_value=mock_spotify_client
        )

        spotify_auth.test_connection()

        mock_spotify_client.current_user.assert_called_once()


class TestScopes:
    def test_required_scopes_defined(self):
        """Should have required scopes for the app."""
        required = [
            "user-read-recently-played",
            "user-top-read",
            "user-library-read",
        ]

        for scope in required:
            assert scope in spotify_auth.SCOPES
