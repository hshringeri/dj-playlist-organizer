import os
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "user-read-recently-played",
    "user-top-read",
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public",
]

CACHE_PATH = Path(__file__).parent.parent / ".spotify_cache"


def get_spotify_client() -> spotipy.Spotify:
    """Get authenticated Spotify client with token refresh handling."""
    auth_manager = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback"),
        scope=" ".join(SCOPES),
        cache_path=str(CACHE_PATH),
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def test_connection() -> dict:
    """Test Spotify connection and return user profile."""
    sp = get_spotify_client()
    user = sp.current_user()
    return {
        "id": user["id"],
        "display_name": user["display_name"],
        "followers": user["followers"]["total"],
    }


if __name__ == "__main__":
    print("Testing Spotify connection...")
    try:
        user_info = test_connection()
        print(f"Connected as: {user_info['display_name']} ({user_info['id']})")
        print(f"Followers: {user_info['followers']}")
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have:")
        print("1. Created a Spotify app at https://developer.spotify.com/dashboard")
        print("2. Copied .env.example to .env and filled in your credentials")
        print("3. Added http://localhost:8888/callback to your app's redirect URIs")
