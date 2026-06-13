import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()


class TokenManager:
    def __init__(self):
        self.api_key = "key_live_596d1cc1a8ec4cf4972d2a3847649041"
        self.api_secret = "secret_live_fdab340fc4704fd2bb18295563b158cc"

        self.base_url = "https://api.sandbox.co.in/authenticate"

        self.token = None
        self.expiry = 0  # timestamp

    # 🔥 check token valid or not
    def _is_token_valid(self):
        return self.token and time.time() < self.expiry

    # 🔥 generate new token
    def _generate_token(self):
        print("🔄 Generating new access token...")

        headers = {
            "x-api-key": self.api_key,
            "x-api-secret": self.api_secret,
            "x-api-version": "1.0",
            "Content-Type": "application/json",
        }

        response = requests.post(self.base_url, headers=headers)
        data = response.json()

        self.token = data["data"]["access_token"]

        # assume token valid for 1 hour (change if API provides expiry)
        self.expiry = time.time() + 3600

        print("✅ Token generated successfully")

    # 🔥 public method (use everywhere)
    def get_token(self):
        if not self._is_token_valid():
            self._generate_token()

        return self.token


# global instance (singleton style)
token_manager = TokenManager()

