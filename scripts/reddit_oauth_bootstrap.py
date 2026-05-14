#!/usr/bin/env python3
"""One-shot helper to generate a Reddit OAuth refresh token.

Run this LOCALLY (not in CI) once per bot account. Walks you through:

1. Opening Reddit's OAuth consent page in your browser.
2. Approving the bot account.
3. Capturing the redirect on localhost:8080.
4. Exchanging the authorization code for a refresh token.
5. Printing the refresh token so you can paste it into GitHub Actions
   secrets as ``REDDIT_REFRESH_TOKEN``.

Required env vars (or pass interactively):

  REDDIT_CLIENT_ID
  REDDIT_CLIENT_SECRET
  REDDIT_USER_AGENT     e.g. 'python:ldr-bot:v0.3 (by /u/your-username)'

Usage:

  pip install praw==7.8.1
  export REDDIT_CLIENT_ID=...
  export REDDIT_CLIENT_SECRET=...
  export REDDIT_USER_AGENT='...'
  python scripts/reddit_oauth_bootstrap.py
"""

from __future__ import annotations

import http.server
import os
import socketserver
import sys
import threading
import webbrowser
from urllib.parse import parse_qs, urlparse


REDIRECT_PORT = 8080
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"


class _OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    captured = {}

    def do_GET(self):  # noqa: N802 — required by stdlib
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            _OAuthCallbackHandler.captured["code"] = params["code"][0]
            _OAuthCallbackHandler.captured["state"] = params.get("state", [""])[0]
            body = (
                b"<html><body><h1>Authorization received.</h1>"
                b"<p>You can close this tab. Return to the terminal.</p>"
                b"</body></html>"
            )
        elif "error" in params:
            _OAuthCallbackHandler.captured["error"] = params["error"][0]
            body = b"<html><body><h1>Authorization failed.</h1></body></html>"
        else:
            body = b"<html><body><h1>Unexpected redirect.</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002 — required by stdlib
        # Silence stderr log lines from the dev server.
        return


def _serve_until_redirect():
    with socketserver.TCPServer(("127.0.0.1", REDIRECT_PORT), _OAuthCallbackHandler) as srv:
        srv.timeout = 300  # 5 min
        srv.handle_request()  # serves exactly one request, then returns


def main() -> int:
    try:
        import praw  # noqa: F401
    except ImportError:
        print(
            "PRAW not installed. Run: pip install praw==7.8.1",
            file=sys.stderr,
        )
        return 1
    import praw

    cid = os.environ.get("REDDIT_CLIENT_ID")
    csec = os.environ.get("REDDIT_CLIENT_SECRET")
    ua = os.environ.get("REDDIT_USER_AGENT")
    if not (cid and csec and ua):
        print(
            "Missing one of REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT",
            file=sys.stderr,
        )
        print("See docs/reddit-oauth-setup.md for setup steps.", file=sys.stderr)
        return 1

    state = os.urandom(8).hex()

    reddit = praw.Reddit(
        client_id=cid,
        client_secret=csec,
        redirect_uri=REDIRECT_URI,
        user_agent=ua,
    )
    # Scopes the Reddit QA bot needs: identity (to know who we are),
    # read (subreddit + submission), submit (post comments).
    auth_url = reddit.auth.url(
        scopes=["identity", "read", "submit", "history"],
        state=state,
        duration="permanent",  # required for refresh token
    )

    print()
    print("Opening Reddit's OAuth consent page in your browser...")
    print(f"If it doesn't open, copy this URL: {auth_url}")
    print()
    print(f"Listening for redirect on {REDIRECT_URI} (5 min timeout)...")

    server_thread = threading.Thread(target=_serve_until_redirect, daemon=True)
    server_thread.start()
    webbrowser.open(auth_url)
    server_thread.join(timeout=320)

    captured = _OAuthCallbackHandler.captured
    if "error" in captured:
        print(f"Reddit returned error: {captured['error']}", file=sys.stderr)
        return 1
    if "code" not in captured:
        print("Timed out waiting for browser redirect.", file=sys.stderr)
        return 1
    if captured.get("state") != state:
        print("State mismatch — possible CSRF. Aborting.", file=sys.stderr)
        return 1

    code = captured["code"]
    print("Exchanging authorization code for refresh token...")
    refresh_token = reddit.auth.authorize(code)
    if not refresh_token:
        print("Reddit didn't return a refresh token (did you request duration=permanent?).", file=sys.stderr)
        return 1

    print()
    print("=" * 60)
    print("SUCCESS. Add this to your repo's GitHub Actions secrets:")
    print("=" * 60)
    print(f"  REDDIT_REFRESH_TOKEN = {refresh_token}")
    print("=" * 60)
    print()
    print("Also confirm these are set in repo secrets:")
    print(f"  REDDIT_CLIENT_ID     = {cid}")
    print("  REDDIT_CLIENT_SECRET = <the secret you used here>")
    print(f"  REDDIT_USER_AGENT    = {ua}")
    print()
    print("Refresh tokens stay valid until revoked. See")
    print("https://www.reddit.com/prefs/apps to revoke if needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
