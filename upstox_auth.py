"""Trade one morning click for the whole Upstox surface.

WHY THIS EXISTS. `upstox_ws_probe.py` measured the wall exactly: an **Analytics
Token** opens Upstox's HISTORY and nothing else. Same token, same minute,
2026-08-05 10:17 IST --

    /v2/historical-candle/intraday/...               200, live candles
    /v2/option/chain, /v3/market-quote/option-greek  401 UDAPI100050
    /v3/feed/market-data-feed/authorize              401 UDAPI100050
    the WebSocket handshake itself                   401

UDAPI100050 reads "Invalid token used to access API" -- a token-CLASS refusal,
not an expiry, proven by the 200 on the same token in the same second. The feed
itself is not the problem: its proto carries `iv`, `oi` and the full greeks per
strike, which is precisely what the GEX stack, the flip price and both walls
need and what Dhan stopped supplying when its Data API subscription lapsed.

A **regular OAuth access token** covers that whole surface. This script gets one
with as little of your attention as the protocol allows:

    python upstox_auth.py

It opens the Upstox login page itself, catches the redirect on a local port,
exchanges the code and writes the token. You log in -- that is the only step
that is yours, because it is your password and nobody else should be typing it.
If the app's redirect_uri is not a localhost URL the script falls back to asking
you to paste the redirected URL, which works but is the slower road.

Cost: the token expires at 03:30 IST, so this is a once-a-morning ritual -- the
same one already run for Dhan ("first click of the day is TOKEN"), just free.

SETUP, once. Create `.upstox_app.json` (gitignored) from your app at
https://account.upstox.com/developer/apps :

    {"api_key": "...", "api_secret": "...", "redirect_uri": "http://localhost:5000/"}

The `redirect_uri` must match the app's registered value EXACTLY -- a trailing
slash is a mismatch, and Upstox reports it as an invalid client rather than as
a bad URI, which is a bad afternoon. Registering a localhost URL is what buys
the automatic capture; Upstox accepts one.

SECRETS. The key, the secret and the resulting token are never printed and
never logged. Nothing here belongs in a chat window or a shell argument, which
is why every value is read from and written to a file. The previous token is
kept at `.upstox_token.bak` rather than overwritten, so a failed exchange
cannot cost you the Analytics token you already have.

READ-ONLY against your account: this obtains a token, and places no order.
"""

import getpass
import http.server
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

APP_FILE = ".upstox_app.json"
TOKEN_FILE = ".upstox_token"
BACKUP_FILE = ".upstox_token.bak"
DIALOG = "https://api.upstox.com/v2/login/authorization/dialog"
TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"
WAIT_SECONDS = 300

# Cloudflare answers Python's default User-Agent with Error 1010 -- a 403 that
# reads exactly like an auth failure and is not one (measured 2026-08-05).
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

DONE_PAGE = b"""<!doctype html><meta charset=utf-8><title>TapeMap</title>
<body style="font:16px system-ui;padding:3rem;max-width:32rem">
<h2>Token captured.</h2><p>You can close this tab and go back to the terminal.</p>
</body>"""


def setup_app():
    """First run: take the three values straight into the file.

    Typed here rather than into a JSON file by hand, and rather than into a
    shell command -- arguments land in history, and the secret is echoed. This
    prompt writes them once and never shows them again.
    """
    print(f"""No {APP_FILE} yet. Open your app at
    https://account.upstox.com/developer/apps
and copy three values across. They go straight into {APP_FILE}, which is
gitignored; nothing is echoed or logged.

The redirect URI must match the app's registered value EXACTLY. If you can
edit the app, register  http://localhost:5000/  -- a localhost URL is what
lets this script catch the login automatically instead of making you paste
a URL back.
""")
    key = input("  API key      : ").strip()
    secret = getpass.getpass("  API secret   : (not shown) ").strip()
    redirect = input("  Redirect URI : ").strip()
    if not (key and secret and redirect):
        sys.exit("  all three are required")
    app = {"api_key": key, "api_secret": secret, "redirect_uri": redirect}
    with open(APP_FILE, "w", encoding="utf-8") as f:
        json.dump(app, f, indent=2)
    print(f"\n  saved to {APP_FILE} — you will not be asked again.\n")
    return app


def load_app():
    if not os.path.exists(APP_FILE):
        return setup_app()
    try:
        app = json.load(open(APP_FILE, encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"{APP_FILE} is not valid JSON: {e}")
    missing = [k for k in ("api_key", "api_secret", "redirect_uri") if not app.get(k)]
    if missing:
        sys.exit(f"{APP_FILE} is missing: {', '.join(missing)}")
    return app


def dialog_url(app):
    return DIALOG + "?" + urllib.parse.urlencode({
        "client_id": app["api_key"], "redirect_uri": app["redirect_uri"],
        "response_type": "code"})


def _local_port(redirect_uri):
    """The port to listen on, or None if this redirect cannot be caught here."""
    u = urllib.parse.urlparse(redirect_uri)
    if u.hostname not in ("localhost", "127.0.0.1"):
        return None
    if u.scheme != "http":                       # https would need a cert
        return None
    return u.port or 80


def catch_code(port, url):
    """Serve once on `port` and return the ?code= Upstox redirects with."""
    box = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):                        # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in q:
                box["code"] = q["code"][0]
            elif "error" in q:
                box["error"] = q.get("error_description", q["error"])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DONE_PAGE)

        def log_message(self, *a):               # keep the console clean
            pass

    try:
        srv = http.server.HTTPServer(("127.0.0.1", port), Handler)
    except OSError as e:
        print(f"    cannot listen on port {port}: {e}")
        return None
    # Serve until the code arrives or the deadline passes -- NOT until the
    # first request. A browser's opening shot is usually /favicon.ico, and
    # stopping on that would report "no code arrived" after a perfectly good
    # login.
    srv.timeout = 2
    print(f"    listening on 127.0.0.1:{port} for the redirect")
    print("\n[2] A browser is opening. Log in there — that step is yours.")
    threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
    deadline = time.monotonic() + WAIT_SECONDS
    while not box and time.monotonic() < deadline:
        srv.handle_request()                     # returns after srv.timeout
    srv.server_close()
    if box.get("error"):
        sys.exit(f"    Upstox refused: {box['error']}")
    return box.get("code")


def ask_code(url, redirect_uri):
    """Fallback when the redirect cannot be caught locally."""
    print("\n[2] Open this and log in:\n")
    print("    " + url)
    print(f"""
    Upstox will send your browser to
        {redirect_uri}?code=SOMETHING
    That page may fail to load -- fine, the code is in the URL bar.""")
    raw = input("\n    Paste the code (or the whole URL): ").strip()
    if not raw:
        sys.exit("    nothing pasted")
    if "code=" in raw:
        q = urllib.parse.urlparse(raw).query or raw.split("?", 1)[-1]
        got = urllib.parse.parse_qs(q).get("code")
        if not got:
            sys.exit("    that URL has no ?code= parameter")
        return got[0]
    return raw


def exchange(app, code):
    body = urllib.parse.urlencode({
        "code": code, "client_id": app["api_key"],
        "client_secret": app["api_secret"], "redirect_uri": app["redirect_uri"],
        "grant_type": "authorization_code"}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={
        "accept": "application/json", "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        sys.exit(f"""
[!] HTTP {e.code} from the token endpoint:
    {detail}

    invalid client -> api_key, api_secret or redirect_uri does not match the
      app exactly (check for a trailing slash).
    invalid grant / expired code -> the code is single-use and short-lived;
      run this again.""")


def save(token):
    if os.path.exists(TOKEN_FILE):
        prev = open(TOKEN_FILE, encoding="utf-8").read()
        if prev.strip() and prev.strip() != token:
            open(BACKUP_FILE, "w", encoding="utf-8").write(prev)
            print(f"    previous token preserved at {BACKUP_FILE}")
    open(TOKEN_FILE, "w", encoding="utf-8").write(token)
    print(f"    written to {TOKEN_FILE} ({len(token)} chars, not shown)")


def main():
    app = load_app()
    print("Upstox OAuth — nothing secret is printed.")
    url = dialog_url(app)
    port = _local_port(app["redirect_uri"])
    print(f"\n[1] redirect_uri: {app['redirect_uri']}")
    code = catch_code(port, url) if port else ask_code(url, app["redirect_uri"])
    if not code:
        sys.exit(f"    no code arrived within {WAIT_SECONDS}s — run this again")
    print("\n[3] exchanging the code for an access token")
    data = exchange(app, code)
    token = data.get("access_token")
    if not token:
        sys.exit(f"    no access_token in the response: {sorted(data)}")
    save(token)
    print(f"\n    valid until 03:30 IST. user_type={data.get('user_type')} "
          f"exchanges={data.get('exchanges')}")
    print("\nNow re-run the probe — same measurement, new token class:")
    print("    python upstox_ws_probe.py")


if __name__ == "__main__":
    main()
