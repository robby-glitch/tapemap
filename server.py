"""Local server for the tape-engine UI.

  python server.py [port] [data_dir] [strike] [--mock-chain]
  python server.py live [port] [--mock-chain]

Serves ui/ as static files, the analysis JSON at /api/data, and the live
option-chain analyser payload at /api/chain (chain_live.ChainPoller).

Multi-index: /api/data and /api/chain accept ?idx=NIFTY|BANKNIFTY|SENSEX
(default NIFTY). In live mode the server resolves + builds a payload per
enabled index and runs a single round-robin ChainPoller feeding one box per
index. --mock-chain replays the synthetic fixture into every index so the DATA
tab works with an expired token and outside market hours.
"""

import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import instruments
from analyze import analyze

ROOT = Path(__file__).parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, payloads=None, chains=None, poller=None, **kw):
        self.payloads = payloads or {}     # idx -> {"payload": bytes} (or bytes)
        self.chains = chains               # idx -> ChainPoller box, or None
        self.poller = poller               # ChainPoller object (for hot-reload), or None
        super().__init__(*a, directory=str(ROOT / "ui"), **kw)

    def _idx(self):
        """?idx= clamped to an enabled index; unknown/absent -> DEFAULT."""
        q = parse_qs(urlsplit(self.path).query)
        idx = (q.get("idx") or [instruments.DEFAULT])[0]
        return idx if idx in instruments.ENABLED else instruments.DEFAULT

    def _json(self, body, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # One-click token capture: validate a pasted/clipboard Dhan token, save
        # it to .dhan_token, and kick the poller. The token is never logged or
        # echoed — only the validity message from token_status goes back.
        if not self.path.startswith("/api/token"):
            self.send_error(404)
            return
        from chain_live import token_status
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if not 0 < n < 8192:
            self._json(b'{"ok":false,"msg":"bad request"}', 400)
            return
        try:
            tok = json.loads(self.rfile.read(n)).get("token", "").strip()
        except (ValueError, AttributeError):
            self._json(b'{"ok":false,"msg":"malformed request body"}', 400)
            return
        st = token_status(tok)
        if not st["ok"]:
            self._json(json.dumps({"ok": False, "msg": st["msg"]}).encode())
            return
        (ROOT / ".dhan_token").write_text(tok, encoding="utf-8")
        if self.poller is not None:
            self.poller.reload = True          # hot-reload the chain poller
        self._json(json.dumps({"ok": True, "msg": st["msg"]}).encode())

    def do_GET(self):
        if self.path.startswith("/api/data"):
            idx = self._idx()
            box = (self.payloads.get(idx) or self.payloads.get(instruments.DEFAULT)
                   or (next(iter(self.payloads.values())) if self.payloads else None))
            pl = (box["payload"] if isinstance(box, dict) else box) if box else b"{}"
            self._json(pl if pl is not None else b"{}")
        elif self.path.startswith("/api/chain"):
            idx = self._idx()
            if not self.chains:
                self.send_error(404)     # no poller: UI falls back to legacy
                return
            box = self.chains.get(idx) or self.chains.get(instruments.DEFAULT)
            if not box or box["payload"] is None:
                self._json(b'{"ok":false,"error":"chain poller warming up"}')
            else:
                self._json(box["payload"])
        elif self.path.startswith("/api/gex"):
            gex = ROOT / "data" / "gex_2026-07-17.json"
            if gex.exists():
                body = gex.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error(404)
        else:
            super().do_GET()

    def log_message(self, *a):
        pass


def _start_chain(mock, configs):
    from chain_live import ChainPoller
    poller = ChainPoller(configs, mock=mock)
    poller.start()
    print("chain poller started" + (" (MOCK fixture)" if mock else "")
          + " for " + ", ".join(c["under_sym"] for c in configs))
    return poller


def main():
    argv = [a for a in sys.argv[1:] if a != "--mock-chain"]
    mock_chain = "--mock-chain" in sys.argv[1:]
    if argv and argv[0] == "live":
        import threading
        import time as _t
        from live import REFRESH_S, build_payload
        port = int(argv[1]) if len(argv) > 1 else 8765
        today = _t.strftime("%Y-%m-%d")

        def _waiting(sym, why):
            return json.dumps({"index": sym, "strike": None, "days": [],
                               "live_error": why}).encode()

        # Crash-proof deferred startup: bind the server immediately with
        # "starting up" payloads, then resolve instruments + build the tape in
        # the background loop. A stale or missing .dhan_token can no longer stop
        # the server from coming up — start it, open the UI, click the TOKEN
        # button, and the next refresh (<= REFRESH_S) brings the tape live. The
        # chain poller only needs the static under_id/seg, so it starts on its
        # own. (resolve_dynamic uses the public scrip master, no token needed.)
        cfgs = {x: instruments.get(x) for x in instruments.ENABLED}
        payloads = {x: {"payload": _waiting(x, "starting up — resolving…")}
                    for x in instruments.ENABLED}
        have = {x: False for x in instruments.ENABLED}
        poller = _start_chain(mock_chain, list(cfgs.values()))
        chains = poller.boxes
        print(f"LIVE server up on http://127.0.0.1:{port} for {list(cfgs)} "
              f"(refresh {REFRESH_S}s). Need a token? Click TOKEN in the UI.")

        def refresh():
            first = True
            while True:
                if not first:
                    _t.sleep(REFRESH_S)
                first = False
                # resolve any unresolved indices from ONE scrip-master download
                todo = [c for c in cfgs.values() if "fut_id" not in c]
                if todo:
                    try:
                        rows = instruments._load_scrip()
                        for c in todo:
                            instruments.resolve_dynamic(c, "", today, rows=rows)
                    except Exception as e:
                        print("instrument resolve failed", e)
                for x, c in cfgs.items():
                    if "fut_id" not in c:                # still unresolved -> retry next cycle
                        continue
                    try:
                        payloads[x]["payload"] = build_payload(c)
                        have[x] = True
                    except Exception as e:  # keep last good data; else ask for a token
                        if not have[x]:
                            payloads[x]["payload"] = _waiting(x,
                                "waiting for a valid Dhan token — click ⟳ TOKEN")
                        print("live build failed", x, e)

        threading.Thread(target=refresh, daemon=True).start()
        ThreadingHTTPServer(("127.0.0.1", port),
                            partial(Handler, payloads=payloads,
                                    chains=chains, poller=poller)).serve_forever()
        return
    port = int(argv[0]) if argv else 8765
    base = argv[1] if len(argv) > 1 else "data"
    strike = float(argv[2]) if len(argv) > 2 else 24200.0
    poller = (_start_chain(True, [instruments.get(x) for x in instruments.ENABLED])
              if mock_chain else None)
    chains = poller.boxes if poller else None
    payload = json.dumps(analyze(base, strike)).encode()
    payloads = {instruments.DEFAULT: {"payload": payload}}
    print(f"analysis ready ({len(payload)//1024} KB), serving on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port),
                        partial(Handler, payloads=payloads,
                                chains=chains, poller=poller)).serve_forever()


if __name__ == "__main__":
    main()
