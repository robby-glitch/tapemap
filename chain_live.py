"""Option-chain poller: Dhan REST option_chain -> normalized snapshots ->
chain_metrics.ChainState -> a JSON payload box served by server.py at
/api/chain. Multi-index: one poller round-robins NIFTY / BANKNIFTY / SENSEX,
holding one ChainState + one payload box per index. Persists every live
snapshot to data/chain/chain_<IDX>_<date>.jsonl (each live day becomes
replayable per index) and offers a --mock mode that replays
data/chain_sample.jsonl into every index box with no token / no SDK.

Rate limit: Dhan allows 1 unique option-chain request per 3 seconds; the
round-robin sleeps ~RR_GAP_S BETWEEN indices, so no two chain requests fire
within that gap and each index refreshes ~every RR_GAP_S * N. Expiry is
auto-resolved per index from expiry_list at startup (no hardcoded expiry).
Token comes from env DHAN_TOKEN, falling back to the .dhan_token file, with a
JWT exp check surfaced as a payload error instead of a crash.
"""

import base64
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from chain_metrics import ChainState, thin_series

IST = timezone(timedelta(hours=5, minutes=30))
ROOT = Path(__file__).parent
FIXTURE = ROOT / "data" / "chain_sample.jsonl"
CHAIN_DIR = ROOT / "data" / "chain"

log = logging.getLogger("tapemap")       # same logger server.py wires to
                                          # tapemap.log via basicConfig, so a
                                          # timeout logged here reaches the
                                          # file even though this module never
                                          # calls basicConfig itself

MOCK_S = 1                             # mock replays 1 snapshot/s (demo pace)
RR_GAP_S = 3.5                         # gap BETWEEN chain requests (limit: 1/3s)
WINDOW_PTS = 1500                      # default strike window (cfg overrides)
CHAIN_DEADLINE_S = 20                  # wall-clock cap on dhan.option_chain():
                                        # a healthy call finishes in ~1-2s;
                                        # this is far above that but far below
                                        # a genuine stall, so it trips fast
                                        # enough to keep the round-robin
                                        # moving without flagging slow-but-ok
                                        # responses (2026-07-30: a hang here
                                        # silently froze the poller for 95min)

SESS_OPEN = 9 * 3600 + 15 * 60         # 09:15 IST — NSE/BSE session open
SESS_CLOSE = 15 * 3600 + 30 * 60       # 15:30 IST — session close


def _sec_of_day(now):
    return now.hour * 3600 + now.minute * 60 + now.second


def in_session(now):
    """True only inside a weekday market session (09:15–15:30 IST). The chain
    polls/records ONLY inside this window, so overnight/closed-market snapshots
    never pollute the per-day history — each trading day starts fresh at 09:15."""
    if now.weekday() >= 5:             # Sat / Sun
        return False
    return SESS_OPEN <= _sec_of_day(now) <= SESS_CLOSE


def read_token():
    tok = os.environ.get("DHAN_TOKEN", "").strip()
    if tok:
        return tok
    p = ROOT / ".dhan_token"
    return p.read_text().strip() if p.exists() else ""


def token_status(tok):
    """Decode the JWT exp claim. Never logs or returns the token itself."""
    if not tok:
        return {"ok": False, "msg": "no token: set DHAN_TOKEN or .dhan_token"}
    try:
        pay = tok.split(".")[1]
        pay += "=" * (-len(pay) % 4)
        exp = json.loads(base64.urlsafe_b64decode(pay)).get("exp")
    except Exception:
        return {"ok": False, "msg": "token is not a decodable JWT"}
    if exp is None:
        return {"ok": True, "msg": "token has no exp claim"}
    left = exp - time.time()
    if left <= 0:
        return {"ok": False,
                "msg": "Dhan token EXPIRED — generate a fresh access token"}
    return {"ok": True, "msg": f"token valid ~{left / 3600:.1f}h"}


def _with_deadline(fn, deadline_s, what):
    """Run fn() on a short-lived daemon thread and wait up to deadline_s for
    it to finish, so a hung call (e.g. dhan.option_chain(), which accepts no
    deadline/timeout of its own) can never block the caller past deadline_s.

    Mirrors instruments.fetch_bytes's wall-clock guard for the same failure
    mode (2026-07-27 outage; recurred for the chain fetch on 2026-07-30):
    urllib/SDK timeout= only bounds individual socket ops, not the whole
    call, so a slow-trickling or stalled response can hang forever with no
    exception raised.

    Threads cannot be killed in Python, so on timeout the worker thread is
    simply abandoned still running -- it is created daemon=True precisely so
    an abandoned, permanently-blocked worker can never prevent process exit.
    The important property this buys is that the POLL LOOP itself is never
    blocked again: on timeout we raise TimeoutError here, which the existing
    `except Exception` in the poll loop turns into a tagged, skipped index.
    """
    result = {}

    def _run():
        try:
            result["value"] = fn()
        except Exception as e:                # noqa: BLE001 - re-raised below
            result["error"] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(deadline_s)
    if t.is_alive():
        log.error("chain: %s: no response in %ss (worker thread abandoned, "
                   "daemon=True)", what, deadline_s)
        raise TimeoutError(f"{what}: no response in {deadline_s}s")
    if "error" in result:
        raise result["error"]
    return result["value"]


def _client(tok):
    from dhanhq import DhanContext, dhanhq
    cid = os.environ.get("DHAN_CLIENT_ID", "").strip()
    if not cid:
        from dhan_fetch import _client_id
        cid = _client_id()                           # env or .dhan_client file
    return dhanhq(DhanContext(cid, tok))


def _broker():
    """Which data source the live poller uses. Dhan unless told otherwise.

    `TAPEMAP_BROKER=upstox` switches the chain to the Upstox socket. Default
    is dhan so that setting nothing keeps the behaviour that has been running,
    and so a missing or misspelled env var can never silently move the tool
    onto a different broker mid-session.
    """
    return os.environ.get("TAPEMAP_BROKER", "dhan").strip().lower()


def _upstox_source(existing=None):
    """The Upstox chain source, imported only when actually selected.

    A local import so that a Dhan-only run never pays for -- or fails on --
    the websocket dependency chain.
    """
    if existing is not None:
        return existing
    from upstox_chain import UpstoxChainSource
    return UpstoxChainSource()


def _inner(resp):
    """SDK wraps as {status, data}; the chain API nests one more 'data'."""
    if not isinstance(resp, dict) or resp.get("status") != "success":
        raise RuntimeError(f"dhan api failure: {str(resp)[:200]}")
    d = resp.get("data")
    if isinstance(d, dict) and "data" in d and "oc" not in d:
        d = d["data"]
    return d


def resolve_expiry(dhan, today, uid, seg):
    lst = _inner(dhan.expiry_list(uid, seg))
    if isinstance(lst, dict):
        lst = lst.get("data") or []
    days = sorted(x for x in lst if str(x) >= today)
    if not days:
        raise RuntimeError(f"no expiry >= {today} in expiry_list")
    return str(days[0])


def t_years(expiry, now):
    """Year-fraction to expiry-day 15:30 IST. Floored above zero."""
    y, m, d = (int(x) for x in expiry.split("-"))
    exp_dt = datetime(y, m, d, 15, 30, tzinfo=IST)
    return max((exp_dt - now).total_seconds() / (365.0 * 86400.0), 1e-4)


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v


def _side(raw):
    if not isinstance(raw, dict):
        return None
    iv = _num(raw.get("implied_volatility"))
    if iv is not None:
        iv = iv / 100.0 if iv > 1.5 else iv          # percent -> fraction
        if iv <= 0:
            iv = None
    g = raw.get("greeks") or {}
    oi_now = int(_num(raw.get("oi")) or 0)
    chg = _num(raw.get("oi_change"))
    if chg is None:                     # live API ships previous_oi instead
        prev_oi = _num(raw.get("previous_oi"))
        chg = (oi_now - prev_oi) if prev_oi is not None else 0
    return {
        "ltp": _num(raw.get("last_price")) or 0.0,
        "oi": oi_now,
        "oi_chg": int(chg),
        "iv": iv,
        "vol": int(_num(raw.get("volume")) or 0),
        "bid": _num(raw.get("top_bid_price")),
        "ask": _num(raw.get("top_ask_price")),
        "avg": _num(raw.get("average_price")),
        "gamma": _num(g.get("gamma")),
        "delta": _num(g.get("delta")),
    }


def normalize(data, now, window=WINDOW_PTS):
    """Raw Dhan chain payload -> the chain_metrics snapshot contract."""
    spot = _num(data.get("last_price"))
    oc = data.get("oc") or {}
    if not spot or not oc:
        raise RuntimeError("chain response missing last_price/oc")
    rows = []
    for kstr, sides in oc.items():
        k = _num(kstr)
        if k is None or abs(k - spot) > window:
            continue
        ce, pe = _side(sides.get("ce")), _side(sides.get("pe"))
        if ce is None or pe is None:
            continue
        rows.append({"k": int(k), "ce": ce, "pe": pe})
    if not rows:
        raise RuntimeError("no strikes inside window")
    rows.sort(key=lambda r: r["k"])
    atm = min(rows, key=lambda r: abs(r["k"] - spot))["k"]
    sec = now.hour * 3600 + now.minute * 60 + now.second
    return {"ts": now.strftime("%H:%M:%S"), "sec": sec,
            "spot": spot, "atm": atm, "strikes": rows}


class ChainPoller(threading.Thread):
    """Daemon thread owning per-index chain state; publishes JSON bytes into
    self.boxes[under_sym]['payload'] for each configured index."""

    def __init__(self, configs, mock=False):
        super().__init__(daemon=True)
        self.mock = mock
        self.configs = configs                       # list of cfg dicts
        self.boxes = {c["under_sym"]: {"payload": None} for c in configs}
        self.states = {c["under_sym"]: ChainState() for c in configs}
        self.prevs = {c["under_sym"]: None for c in configs}
        self.reload = False                          # set by /api/token to re-read the token

    def _publish(self, idx, snap, metrics, expiry, mode, error=None):
        by_k = {r["k"]: r for r in metrics.pop("per_strike", [])}
        strikes = []
        for s in snap["strikes"]:
            r = by_k.get(s["k"], {})
            # ce_pk/pe_pk are the session-high OI per book: "% off peak" is the
            # cheapest read of a wall losing its defenders, and without it here
            # the field never reaches either frontend.
            strikes.append({**s, "ce_w": r.get("ce_w"), "pe_w": r.get("pe_w"),
                            "gex": r.get("gex"),
                            "ce_pk": r.get("ce_pk"), "pe_pk": r.get("pe_pk")})
        self.boxes[idx]["payload"] = json.dumps({
            "ok": True, "mode": mode, "error": error, "index": idx,
            "ts": snap["ts"], "built_at": time.time(), "expiry": expiry,
            "spot": snap["spot"], "atm": snap["atm"],
            "strikes": strikes, "metrics": metrics,
            "series": thin_series(self.states[idx].series),
        }).encode()

    def _fail(self, idx, mode, msg):
        self.boxes[idx]["payload"] = json.dumps(
            {"ok": False, "mode": mode, "index": idx, "error": msg}).encode()

    def _tag_error(self, idx, mode, msg):
        """Keep the last good payload for `idx` but tag it with the error."""
        box = self.boxes[idx]
        if box["payload"]:
            try:
                pl = json.loads(box["payload"])
                pl["error"] = msg
                box["payload"] = json.dumps(pl).encode()
            except Exception:
                pass
        else:
            self._fail(idx, mode, msg)

    def run(self):
        if self.mock:
            self._run_mock()
        else:
            self._run_live()

    # ---- mock: replay the synthetic fixture into every index box ----

    def _run_mock(self):
        if not FIXTURE.exists():
            for idx in self.boxes:
                self._fail(idx, "mock", "data/chain_sample.jsonl missing — "
                                        "run: python make_chain_fixture.py")
            return
        snaps = [json.loads(x) for x in
                 FIXTURE.read_text(encoding="utf-8").splitlines() if x.strip()]
        while True:
            for idx in self.boxes:
                self.states[idx] = ChainState()
                self.prevs[idx] = None
            for snap in snaps:
                for idx in self.boxes:
                    metrics = self.states[idx].update(snap, snap.get("T", 1e-3),
                                                      self.prevs[idx])
                    self.prevs[idx] = snap
                    self._publish(idx, snap, metrics, "MOCK", "mock")
                time.sleep(MOCK_S)

    # ---- live: round-robin poll Dhan per index, persist, publish ----

    def _warm_start(self, idx, day_file, expiry):
        """Rebuild today's MARKET-HOURS series for `idx` from its persisted
        snapshots so a restart never loses history — while skipping any
        overnight / closed-market snapshots (09:15–15:30 IST only). A full
        fresh rebuild (state reset first), so it's safe to call on every
        (re)start and can't double-count."""
        self.states[idx] = ChainState()          # fresh: warm-start = full rebuild
        self.prevs[idx] = None
        if not day_file.exists():
            return
        try:
            today = day_file.stem.split("_")[-1]      # chain_<IDX>_<date>
            base = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=IST)
            prior = [json.loads(x) for x in
                     day_file.read_text(encoding="utf-8").splitlines()
                     if x.strip()]
            kept = 0
            for s in prior:
                hh, mm, ss = (int(x) for x in s["ts"].split(":"))
                if not (SESS_OPEN <= hh * 3600 + mm * 60 + ss <= SESS_CLOSE):
                    continue                          # skip closed-market snapshots
                snap_now = base.replace(hour=hh, minute=mm, second=ss)
                self.states[idx].update(s, t_years(expiry, snap_now),
                                        self.prevs[idx])
                self.prevs[idx] = s
                kept += 1
            print(f"chain warm-start {idx}: replayed {kept}/{len(prior)} "
                  f"market-hours snapshots from {day_file.name}")
        except Exception as e:
            print(f"chain warm-start {idx} skipped:", e)

    def _run_live(self):
        upstox = _broker() == "upstox"
        src = dhan = None
        while True:                        # outer: token / startup retry
            if upstox:
                # The Dhan gate below cannot judge an Upstox token: it parses a
                # Dhan JWT and would report a perfectly good OAuth token as
                # expired. UpstoxChainSource reads .upstox_token itself and
                # raises with its own message, which the startup except-block
                # already surfaces.
                st = {"ok": True, "msg": "upstox socket"}
            else:
                tok = read_token()
                st = token_status(tok)
                if not st["ok"]:
                    for c in self.configs:
                        self._fail(c["under_sym"], "live", st["msg"])
                    time.sleep(60)         # user may drop a fresh token in
                    continue
            try:
                today = datetime.now(IST).strftime("%Y-%m-%d")
                if upstox:
                    src = _upstox_source(src)
                    # Re-run on every outer pass: a new trading day needs new
                    # strikes, a new expiry and a fresh 09:15 baseline.
                    expiries = src.start(self.configs, today)
                else:
                    dhan = _client(tok)
                    expiries = {c["under_sym"]:
                                resolve_expiry(dhan, today, c["under_id"],
                                               c["under_seg"])
                                for c in self.configs}
            except Exception as e:
                for c in self.configs:
                    self._fail(c["under_sym"], "live",
                               f"chain startup failed: {e}")
                time.sleep(30)
                continue
            print("chain poller (multi-index): "
                  + ", ".join(f"{k} {v}" for k, v in expiries.items())
                  + f", ~{RR_GAP_S}s between indices ({st['msg']})")
            CHAIN_DIR.mkdir(parents=True, exist_ok=True)
            day_files = {c["under_sym"]:
                         CHAIN_DIR / f"chain_{c['under_sym']}_{today}.jsonl"
                         for c in self.configs}
            for c in self.configs:
                idx = c["under_sym"]
                self._warm_start(idx, day_files[idx], expiries[idx])
            sess_date = today
            while True:                    # inner: round-robin poll loop
                if self.reload:            # /api/token dropped a fresh token
                    self.reload = False
                    print("chain poller: reloading token / re-resolving expiries")
                    break                  # -> outer loop re-reads token + warm-starts
                now = datetime.now(IST)
                if now.strftime("%Y-%m-%d") != sess_date:
                    print("chain poller: new trading day -> fresh session")
                    break                  # -> outer: new day_file + clean warm-start
                if not in_session(now):    # closed: don't poll or record
                    for c in self.configs:
                        self._tag_error(c["under_sym"], "live",
                                        "market closed - polling resumes 09:15 IST")
                    time.sleep(30)
                    continue
                for c in self.configs:
                    idx = c["under_sym"]
                    t0 = time.time()
                    try:
                        now = datetime.now(IST)
                        if upstox:
                            # No network here: the socket already filled the
                            # mailbox, so a poll is a copy and a translation.
                            # A stale-but-connected feed raises rather than
                            # re-serving the last snapshot forever.
                            snap = src.poll(c, expiries[idx], now,
                                            c.get("window", WINDOW_PTS))
                        else:
                            resp = _with_deadline(
                                lambda: dhan.option_chain(
                                    c["under_id"], c["under_seg"], expiries[idx]),
                                CHAIN_DEADLINE_S, f"{idx} option_chain")
                            data = _inner(resp)
                            snap = normalize(data, now,
                                             c.get("window", WINDOW_PTS))
                        metrics = self.states[idx].update(
                            snap, t_years(expiries[idx], now), self.prevs[idx])
                        self.prevs[idx] = snap
                        self._publish(idx, snap, metrics, expiries[idx], "live")
                        with day_files[idx].open("a", encoding="utf-8") as f:
                            f.write(json.dumps(snap) + "\n")
                    except Exception as e:  # isolate: tag this index, go on
                        self._tag_error(idx, "live", f"poll failed: {e}")
                        if "token" in str(e).lower() or "401" in str(e):
                            self.reload = True   # force outer retry -> proper EXPIRED
                    time.sleep(max(0.5, RR_GAP_S - (time.time() - t0)))
