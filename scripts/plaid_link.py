"""
Links a bank account via Plaid Link and stores the access token.

Run once per account you want to connect:
  uv run scripts/plaid_link.py

To link a second account, run it again.
"""

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from integrations.plaid.client import create_link_token, exchange_public_token, get_institution_name
from core.db import get_conn, init_db

PORT = 8765
public_token_received = None


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head><title>Link Bank Account</title></head>
<body>
<h2>Connecting your bank...</h2>
<p id="status">Opening Plaid Link...</p>
<script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
<script>
const handler = Plaid.create({{
  token: '{link_token}',
  onSuccess: function(public_token, metadata) {{
    document.getElementById('status').innerText = 'Connected! Saving...';
    fetch('/callback', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{public_token: public_token, institution: metadata.institution.name}})
    }}).then(() => {{
      document.getElementById('status').innerText = 'Done! You can close this tab.';
    }});
  }},
  onExit: function(err, metadata) {{
    document.getElementById('status').innerText = err ? 'Error: ' + err.display_message : 'Cancelled.';
  }},
}});
handler.open();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html_page.encode())

    def do_POST(self):
        global public_token_received
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        public_token_received = body.get("public_token")
        self.send_response(200)
        self.end_headers()
        threading.Thread(target=self.server.shutdown, daemon=True).start()


def run():
    global html_page, public_token_received
    init_db()

    print("Creating Plaid link token...")
    link_token = create_link_token()
    html_page = HTML_TEMPLATE.format(link_token=link_token)

    server = HTTPServer(("localhost", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Opening browser at {url}")
    webbrowser.open(url)

    print("Waiting for you to complete the bank login in your browser...")
    server.serve_forever()

    if not public_token_received:
        print("No token received — did you complete the flow?")
        return

    print("Exchanging token...")
    access_token, item_id = exchange_public_token(public_token_received)

    print("Fetching institution name...")
    try:
        institution_name = get_institution_name(item_id, access_token)
    except Exception:
        institution_name = "Unknown"

    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM plaid_items WHERE item_id=?", (item_id,)
    ).fetchone()

    if existing:
        print(f"Account already linked: {institution_name}")
    else:
        conn.execute(
            "INSERT INTO plaid_items (item_id, access_token, institution_name) VALUES (?, ?, ?)",
            (item_id, access_token, institution_name),
        )
        conn.commit()
        print(f"Linked: {institution_name} (item_id: {item_id})")

    conn.close()
    print("\nDone. Run again to link a second account.")


if __name__ == "__main__":
    run()
