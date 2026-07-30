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
import logging
import sys
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import instruments
from analyze import analyze

ROOT = Path(__file__).parent
log = logging.getLogger("tapemap")


def _setup_logging():
    """Console AND tapemap.log — the 2026-07-27 freeze left its only evidence
    in a closed console window; the log file survives."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(ROOT / "tapemap.log", encoding="utf-8"),
                  logging.StreamHandler()])


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
            box = self.payloads.get(idx)
            if box is None:
                # Never serve one index's tape under another's name. Replay
                # mode only builds DEFAULT, and the old fallback chain quietly
                # answered /api/data?idx=BANKNIFTY with NIFTY's session — three
                # identical panels that looked live and were mislabelled.
                self._json(json.dumps({
                    "index": idx, "strike": None, "days": [],
                    "built_at": time.time(),
                    "live_error": f"no {idx} tape in this server mode — "
                                  f"start with: python server.py live"}).encode())
                return
            pl = box["payload"] if isinstance(box, dict) else box
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
        elif self.path.startswith("/api/oiflow"):
            # Trending-OI table. Aggregated server-side on purpose: the minute
            # grid it reads is a few hundred KB while the raw chain is ~180 MB
            # a day, so the browser must never see the latter.
            idx = self._idx()
            if not self.poller:
                self._json(b'{"ok":false,"error":"no chain poller"}')
                return
            st = self.poller.states.get(idx)
            if st is None:
                self._json(json.dumps({"ok": False,
                                       "error": f"no chain state for {idx}"}).encode())
                return
            q = parse_qs(urlsplit(self.path).query)
            try:
                interval = max(1, min(60, int((q.get("interval") or ["15"])[0])))
            except ValueError:
                interval = 15
            raw = (q.get("strikes") or [""])[0]
            strikes = None
            if raw:
                try:
                    strikes = [float(x) for x in raw.split(",") if x.strip()]
                except ValueError:
                    strikes = None
            rows = st.oi_flow(interval=interval, strikes=strikes)
            avail = sorted({k for m in st.minutes.values() for k in m["k"]})
            self._json(json.dumps({"ok": True, "index": idx,
                                   "interval": interval, "strikes": avail,
                                   "selected": strikes, "rows": rows}).encode())
        elif self.path.startswith("/api/contract"):
            # Option-premium tape: 1-min bars + their own session VWAP bands,
            # per leg. The heavy lifting is live.build_contract (fetch + the
            # pure contract_bars/contract_pair layers); this handler only
            # parses params and keeps one index's failure off the others.
            idx = self._idx()
            q = parse_qs(urlsplit(self.path).query)

            def _int(name, dflt, lo, hi):
                try:
                    return max(lo, min(hi, int((q.get(name) or [str(dflt)])[0])))
                except ValueError:
                    return dflt

            interval = _int("interval", 3, 1, 60)
            days = _int("days", 1, 1, 10)
            side = ((q.get("side") or ["both"])[0] or "both").upper()
            if side not in ("CE", "PE", "BOTH"):
                side = "BOTH"
            raw = (q.get("strike") or [""])[0].strip()
            strike = None
            if raw:
                try:
                    strike = float(raw)
                except ValueError:
                    strike = None      # unparseable -> let the pair picker choose
            # Reuse the chain snapshot the poller already paid for rather than
            # spending another request against Dhan's 1-per-3s chain limit.
            # `atm` rides along with it so contract_pair.pick_pair ranks
            # candidates against the real ATM instead of its own proxy.
            rows, atm = None, None
            box = (self.chains or {}).get(idx)
            if box and box.get("payload"):
                try:
                    pl = json.loads(box["payload"])
                    if pl.get("ok"):
                        rows = pl.get("strikes")
                        atm = pl.get("atm")
                except ValueError:
                    rows = None
            import live                          # local: same style as do_POST
            try:
                body = live.build_contract(idx, strike=strike, side=side,
                                           interval=interval, days=days,
                                           chain_rows=rows, atm=atm)
            except Exception as e:
                # Same isolation as /api/data: this index reports its own
                # failure, the others are untouched, and the traceback lands
                # in tapemap.log rather than a closed console.
                log.exception("contract build failed %s", idx)
                body = {"ok": False, "index": idx, "strike": strike,
                        "side": side, "interval": interval, "days": days,
                        "expiry": None, "sessions": [],
                        "pair": None, "pair_why": None,
                        "legs": {}, "bars": None, "vwap": None, "oi": None,
                        "bar_days": None, "gaps": [], "gap_reasons": {},
                        # empty, never absent: a consumer that reads `rotation`
                        # must not have to tell "no signals" from "no field".
                        "rotation": [], "rotation_rule": live.ROTATION_RULE,
                        "forming": None, "forming_why": live.FORMING_WHY,
                        "built_at": time.time(),
                        "live_error": f"{type(e).__name__}: {e}"}
            self._json(json.dumps(body).encode())
        elif self.path.startswith("/api/gex"):
            # newest gex_YYYY-MM-DD.json (filenames sort chronologically)
            files = sorted((ROOT / "data").glob("gex_*.json"))
            if not files:
                self.send_error(404)
                return
            try:
                pl = json.loads(files[-1].read_text(encoding="utf-8"))
                pl["as_of"] = files[-1].stem[len("gex_"):]
                self._json(json.dumps(pl).encode())
            except (OSError, ValueError):
                self._json(files[-1].read_bytes())
        else:
            super().do_GET()

    def log_message(self, *a):
        pass


def _start_chain(mock, configs):
    from chain_live import ChainPoller
    poller = ChainPoller(configs, mock=mock)
    poller.start()
    log.info("chain poller started%s for %s",
             " (MOCK fixture)" if mock else "",
             ", ".join(c["under_sym"] for c in configs))
    return poller


def main():
    _setup_logging()
    argv = [a for a in sys.argv[1:] if a != "--mock-chain"]
    mock_chain = "--mock-chain" in sys.argv[1:]
    if argv and argv[0] == "live":
        import threading
        import time as _t
        from live import REFRESH_S, build_payload
        port = int(argv[1]) if len(argv) > 1 else 8765

        def _waiting(sym, why):
            return json.dumps({"index": sym, "strike": None, "days": [],
                               "built_at": time.time(),
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
        log.info("LIVE server up on http://127.0.0.1:%s for %s (refresh %ss). "
                 "Need a token? Click TOKEN in the UI.", port, list(cfgs), REFRESH_S)

        # One refresh thread PER INDEX: a slow download or bad instrument on
        # one index can no longer stall the other two (2026-07-27: a single
        # serial loop froze all three tapes at once). The scrip master behind
        # resolve_dynamic is lock-guarded and day-cached in instruments, so
        # three threads still cost one download.
        def refresh_one(x, c, stagger):
            _t.sleep(stagger)       # de-phase the per-index cycles
            first = True
            while True:
                if not first:
                    _t.sleep(REFRESH_S)
                first = False
                try:
                    if "fut_id" not in c:
                        instruments.resolve_dynamic(
                            c, "", _t.strftime("%Y-%m-%d"))
                    payloads[x]["payload"] = build_payload(c)
                    have[x] = True
                except Exception as e:  # keep last good data; else ask for a token
                    log.exception("live build failed %s", x)
                    if not have[x]:
                        payloads[x]["payload"] = _waiting(x,
                            "waiting for a valid Dhan token — click ⟳ TOKEN")
                    if "429" in str(e):     # rate-limited: back off, don't hammer
                        log.warning("%s rate-limited, backing off 20s", x)
                        _t.sleep(20)

        for n, (x, c) in enumerate(cfgs.items()):
            threading.Thread(target=refresh_one, args=(x, c, n * 5),
                             daemon=True, name=f"refresh-{x}").start()
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
    log.info("analysis ready (%s KB), serving on http://127.0.0.1:%s",
             len(payload) // 1024, port)
    ThreadingHTTPServer(("127.0.0.1", port),
                        partial(Handler, payloads=payloads,
                                chains=chains, poller=poller)).serve_forever()


if __name__ == "__main__":
    main()
