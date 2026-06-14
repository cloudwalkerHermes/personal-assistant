"""
Kroger OAuth login — two-step flow for WSL2.

Step 1: Start the auth server (run this, leave it running):
  uv run scripts/kroger_login.py

Step 2a: If WSL2 localhost forwarding works, it completes automatically.

Step 2b: If the browser shows a localhost error, copy the full URL from
         the address bar and pass it as an argument in a NEW terminal:
  uv run scripts/kroger_login.py "http://localhost:8000/callback?code=XXXX..."
"""

import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from core.db import init_db
from integrations.kroger.auth import get_auth_url, exchange_code, save_tokens
from integrations.kroger.history import sync_purchase_history


def extract_code(raw: str) -> str | None:
    if "code=" in raw:
        return parse_qs(urlparse(raw).query).get("code", [None])[0]
    return raw.strip() or None


def finish(code: str):
    print(f"Code received. Exchanging for tokens...")
    token_data = exchange_code(code)
    save_tokens(token_data)
    print("Tokens saved.")
    print("Syncing your Kroger purchase history...")
    sync_purchase_history()
    print("\nDone. You're all set.")


captured_code = [None]


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        code = params.get("code", [None])[0]
        if code:
            captured_code[0] = code
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Authorized. You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>No code received.</h2>")

    def log_message(self, format, *args):
        pass


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def run():
    init_db()

    # Step 2b: code or redirect URL passed as argument
    if len(sys.argv) > 1:
        code = extract_code(sys.argv[1])
        if not code:
            print("Could not extract code from argument.")
            sys.exit(1)
        finish(code)
        return

    # Step 1: start server and print auth URL
    url = get_auth_url()
    print("\nOpen this URL in your browser and log in with your SHOPPING Kroger account:\n")
    print(url)
    print("\nWaiting for callback on http://localhost:8000/callback (120s timeout)...")
    print("If the browser shows a connection error, copy the full URL from the address bar")
    print("and run:  uv run scripts/kroger_login.py \"<paste url here>\"\n")

    webbrowser.open(url)

    server = ReusableHTTPServer(("0.0.0.0", 8000), CallbackHandler)
    server.timeout = 120
    server.handle_request()

    if captured_code[0]:
        finish(captured_code[0])
    else:
        print("No code received. Try again or pass the redirect URL as an argument.")


if __name__ == "__main__":
    run()
