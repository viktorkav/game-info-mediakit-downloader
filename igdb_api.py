import requests
import time
from datetime import datetime

class IGDBClient:
    AUTH_URL = "https://id.twitch.tv/oauth2/token"
    BASE_URL = "https://api.igdb.com/v4"

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = 0

    def authenticate(self):
        """Authenticates with Twitch to get an access token."""
        if self.access_token and time.time() < self.token_expiry:
            return

        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        response = requests.post(self.AUTH_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        self.access_token = data["access_token"]
        self.token_expiry = time.time() + data["expires_in"] - 60 # Buffer

    def _get_headers(self):
        self.authenticate()
        return {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
        }

    def search_games(self, query):
        """Searches for games by name."""
        url = f"{self.BASE_URL}/games"
        # Fields: name, date, cover, platforms, platform_logo
        body = f'search "{query}"; fields name, first_release_date, cover.url, platforms.name, platforms.platform_logo.url; limit 30;'
        
        response = requests.post(url, headers=self._get_headers(), data=body)
        response.raise_for_status()
        return response.json()

    def get_game_details(self, game_id):
        """Fetches detailed info for a single game."""
        url = f"{self.BASE_URL}/games"
        # We need: summary, storyline, websites, covers, screenshots, artworks
        # Added: genres, platforms, involved_companies
        fields = (
            "name, summary, storyline, first_release_date, "
            "cover.url, cover.image_id, "
            "screenshots.url, screenshots.image_id, "
            "artworks.url, artworks.image_id, "
            "websites.url, websites.category, "
            "genres.name, platforms.name, "
            "involved_companies.company.name, involved_companies.developer, involved_companies.publisher, "
            "rating, aggregated_rating, "
            "videos.video_id, "
            "screenshots.url, screenshots.image_id"
        )
        body = f"fields {fields}; where id = {game_id};"
        
        response = requests.post(url, headers=self._get_headers(), data=body)
        response.raise_for_status()
        data = response.json()
        return data[0] if data else None
