#!/usr/bin/env python3
"""One-time setup: get a Spotify refresh token for the round clock.

1. Create an app at https://developer.spotify.com/dashboard
2. Add redirect URI: http://127.0.0.1:8888/callback
3. Run: python3 scripts/spotify_get_refresh_token.py
4. Paste Client ID and Client Secret when prompted
5. Copy the printed refresh token into include/secrets.h
"""

import base64
import json
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-currently-playing user-read-playback-state"
PORT = 8888


class Handler(BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            Handler.code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Spotify linked</h1><p>You can close this tab and return to the terminal.</p>"
            )
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    client_id = input("Spotify Client ID: ").strip()
    client_secret = input("Spotify Client Secret: ").strip()

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    }
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)
    print("\nOpening browser — log in and approve the app...\n")
    print(auth_url, "\n")
    try:
        import webbrowser

        webbrowser.open(auth_url)
    except Exception:
        print("Open the URL above manually.")

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    while Handler.code is None:
        server.handle_request()

    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": Handler.code,
            "redirect_uri": REDIRECT_URI,
        }
    ).encode()
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=body,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)

    print("\nAdd these lines to include/secrets.h:\n")
    print(f'#define SPOTIFY_CLIENT_ID     "{client_id}"')
    print(f'#define SPOTIFY_CLIENT_SECRET "{client_secret}"')
    print(f'#define SPOTIFY_REFRESH_TOKEN "{data["refresh_token"]}"')
    print()


if __name__ == "__main__":
    main()
