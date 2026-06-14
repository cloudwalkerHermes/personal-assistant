"""
One-time Kroger OAuth login. Run this once to authorize the app.

Steps:
  1. uv run scripts/kroger_login.py
  2. Open the printed URL in your browser
  3. Log in with your Kroger account
  4. You'll be redirected to localhost — the script catches it automatically

Requires http://localhost:8000/callback to be set as a redirect URI
in your Kroger developer app at developer.kroger.com.
"""

import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from core.db import init_db
from integrations.kroger.auth import get_auth_url, exchange_code, save_tokens
from integrations.kroger.history import sync_purchase_history

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Authorized. You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>No code received. Try again.</h2>")

    def log_message(self, format, *args):
        pass


def run():
    init_db()
    url = get_auth_url()

    print("\nOpen this URL in your browser to log in with your Kroger account:\n")
    print(url)
    print("\nWaiting for authorization...")

    server = HTTPServer(("localhost", 8000), CallbackHandler)
    server.timeout = 300

    opened = webbrowser.open(url)
    if not opened:
        print("(Could not open browser automatically — copy the URL above)")

    server.handle_request()

    if not auth_code:
        print("No authorization code received.")
        return

    print("Code received. Exchanging for tokens...")
    token_data = exchange_code(auth_code)
    save_tokens(token_data)
    print("Tokens saved.")

    print("Syncing your Kroger purchase history...")
    sync_purchase_history()
    print("\nDone. You're all set.")


if __name__ == "__main__":
    run()
