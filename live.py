"""LIVE mode: fetch today's bars-so-far from Dhan, compute the indicator
stack (session VWAP + sigma bands, prior-day pivots), run the SAME engine as
replay (architecture invariant 2: causal engine == live engine) and hand the
UI payload to server.py.

Instrument-agnostic: build_payload(cfg) takes an instrument config from
instruments.py (NIFTY / BANKNIFTY / SENSEX). All volatile ids (futures
security-id, expiry, prior day) come from cfg via resolve_dynamic.

Standalone check:  python live.py         (resolves NIFTY, prints bars/state)
Serving:           python server.py live  (refreshes every REFRESH_S)
"""

import json
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import contract_bars
import instruments
import structure
from engine import Session, session_json

IST = timezone(timedelta(hours=5, minutes=30))
REFRESH_S = 15
INTRADAY_URL = "https://api.dhan.co/v2/charts/intraday"
STICK_F = Path(__file__).parent / "data" / "stick_state.json"

_ids_cache = {}                         # (sym, expiry, strike) -> {"CE": id, "PE": id}
_piv_cache = {}                         # (sym, prev_day) -> pivots dict


def _load_stick():
    """Sticky-ATM state survives a mid-day restart (same day only — a strike
    carried over from Friday would poison Monday's hysteresis)."""
    try:
        d = json.loads(STICK_F.read_text(encoding="utf-8"))
        if d.get("day") == datetime.now(IST).strftime("%Y-%m-%d"):
            return d.get("sticks", {})
    except Exception:
        pass
    return {}


def _save_stick():
    try:
        STICK_F.parent.mkdir(parents=True, exist_ok=True)
        STICK_F.write_text(json.dumps(
            {"day": datetime.now(IST).strftime("%Y-%m-%d"), "sticks": _stick}),
            encoding="utf-8")
    except OSError:
        pass                            # persistence is best-effort


_stick = _load_stick()                  # per-index sticky-ATM state: sym -> {...}


def _token():
    return open(".dhan_token").read().strip()


def _pick_strike(F, cfg):
    """Sticky ATM on the cfg['step'] grid, keyed per index. Migrate only after
    price holds clearly nearer another strike (>0.6 grid steps away from the
    current one) for 5 consecutive refreshes — kills midpoint whipsaw on pin
    days while the hysteresis stays relative to the instrument's strike spacing."""
    sym, step = cfg["under_sym"], cfg["step"]
    st = _stick.setdefault(sym, {"strike": None, "drift": 0})
    cand = round(F / step) * step
    if st["strike"] is None:
        st["strike"], st["drift"] = cand, 0
        _save_stick()
        return cand
    if cand != st["strike"] and abs(F - st["strike"]) > 0.6 * step:
        st["drift"] += 1
    else:
        st["drift"] = 0
    if st["drift"] >= 5:
        st["strike"], st["drift"] = cand, 0
    _save_stick()
    return st["strike"]


# one gate for ALL Dhan intraday calls: the per-index builder threads
# (server.refresh_one) otherwise burst simultaneously every cycle and trip
# Dhan's rate limit (2026-07-28 open: 107x HTTP 429, tape stale ~4 min)
_gate_lock = threading.Lock()
_gate_t = [0.0]


def _throttle(min_gap=0.35):
    with _gate_lock:
        wait = _gate_t[0] + min_gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _gate_t[0] = time.monotonic()


def _intraday(tok, sec_id, instrument, day, oi=True, seg="NSE_FNO"):
    _throttle()
    body = json.dumps({"securityId": str(sec_id), "exchangeSegment": seg,
                       "instrument": instrument, "interval": "1", "oi": oi,
                       "fromDate": day, "toDate": day}).encode()
    req = urllib.request.Request(INTRADAY_URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "access-token": tok})
    return json.loads(
        instruments.fetch_bytes(req, 20, f"intraday {sec_id}").decode())


def _atm_ids(strike, cfg):
    """CE/PE security ids for the strike nearest `strike` at cfg['expiry'].

    Matched on UNDERLYING_SYMBOL / INSTRUMENT / OPTION_TYPE / STRIKE_PRICE —
    uniform across NSE and BSE (SENSEX option trading symbols are the generic
    'BSXOPT', so a trading-symbol prefix match would fail).

    Resolved ONCE per (index, expiry, strike) from the daily scrip-master
    cache and remembered — the ids only change when the sticky strike migrates
    or expiry rolls. Re-downloading the 37 MB master per refresh cycle is what
    froze the tape on 2026-07-27. Both legs must resolve within one strike
    step; anything farther means a stale/truncated master and must fail loudly
    rather than chart the wrong contract."""
    key = (cfg["under_sym"], cfg["expiry"], strike)
    ids = _ids_cache.get(key)
    if ids:
        return ids
    sym, exp = cfg["under_sym"], cfg["expiry"]
    best = {}                                    # option_type -> (dist, sec_id)
    for r in instruments._load_scrip():
        if (r.get("UNDERLYING_SYMBOL") == sym
                and r.get("INSTRUMENT") == "OPTIDX"
                and (r.get("SM_EXPIRY_DATE") or "")[:10] == exp
                and r.get("OPTION_TYPE") in ("CE", "PE")):
            try:
                dist = abs(float(r.get("STRIKE_PRICE") or 0) - strike)
            except ValueError:
                continue
            ot = r["OPTION_TYPE"]
            if ot not in best or dist < best[ot][0]:
                best[ot] = (dist, r["SECURITY_ID"])
    if set(best) != {"CE", "PE"} or max(d for d, _s in best.values()) > cfg["step"]:
        got = {ot: round(d) for ot, (d, _s) in best.items()}
        raise RuntimeError(f"{sym} {exp}: ATM legs unresolved near {strike:.0f} "
                           f"(nearest {got}) — scrip master stale or truncated?")
    ids = {ot: sid for ot, (_d, sid) in best.items()}
    _ids_cache[key] = ids
    return ids


def _pivots(tok, cfg):
    """Standard pivots off the prior session's FUT H/L/C — fetched once per
    (index, prior day); yesterday's bars cannot change intraday."""
    key = (cfg["under_sym"], cfg["prev_day"])
    if key in _piv_cache:
        return _piv_cache[key]
    d = _intraday(tok, cfg["fut_id"], "FUTIDX", cfg["prev_day"], oi=False,
                  seg=cfg["fut_seg"])
    H, L, C = max(d["high"]), min(d["low"]), d["close"][-1]
    P = (H + L + C) / 3.0
    piv = {"P": P, "R1": 2 * P - L, "S1": 2 * P - H,
           "R2": P + (H - L), "S2": P - (H - L),
           "R3": H + 2 * (P - L), "S3": L - 2 * (H - P)}
    _piv_cache[key] = piv
    return piv


def _bars(d, piv):
    """Dhan arrays -> engine bar dicts with session VWAP + sigma bands
    (VWAP = cum(TP*V)/cumV, TP=(H+L+C)/3; bands = VWAP ± n*sqrt(Var_w)).

    The band recurrence used to be inlined here. It was extracted verbatim to
    `contract_bars.vwap_sigma` so the option-premium tape and this FUT path
    share ONE derivation -- two would drift, and then v1 and v2 would disagree
    about the same band on the same data (contract-tape spec, section 2).
    The numbers this function returns are unchanged.
    """
    n = len(d.get("close", []))
    oi = d.get("open_interest") or [0.0] * n
    bands = contract_bars.vwap_sigma(
        (d["high"][i], d["low"][i], d["close"][i], d["volume"][i])
        for i in range(n))
    bars = []
    for i in range(n):
        ts = datetime.fromtimestamp(d["timestamp"][i], IST)
        b = bands[i]
        bar = {"T": ts.strftime("%H:%M"), "O": d["open"][i], "H": d["high"][i],
               "L": d["low"][i], "C": d["close"][i],
               "VWAP": b["vwap"],
               "U1": b["u1"], "D1": b["d1"],
               "U2": b["u2"], "D2": b["d2"],
               "U3": b["u3"], "D3": b["d3"],
               "OI": oi[i], "V": d["volume"][i]}
        bar.update(piv)
        bars.append(bar)
    return bars


# ---- /api/contract: option-premium tape (Phase 5) --------------------------
#
# The glue lives here rather than in a module of its own because every Dhan
# intraday concern it needs is already in this file: the token, the shared
# 5-req/s gate (_throttle), and the strike -> CE/PE security-id resolver
# (_atm_ids). The pure computation it drives lives in contract_bars.py and
# contract_pair.py, which do no I/O at all.

CONTRACT_DEADLINE_S = 25        # wall-clock cap on ONE intraday chart call.
                                # urllib's timeout= only bounds individual
                                # socket reads, so a trickling response can
                                # hang a request thread forever (2026-07-27
                                # outage). chain_live._with_deadline bounds
                                # the whole call; a healthy 375-bar fetch
                                # returns in well under a second.
CONTRACT_MAX_DAYS = 10          # days x legs is one request each; bounded so a
                                # stray ?days=900 cannot walk into the rate cap

FORMING_WHY = (
    "forming is null in this build. The incomplete candle is aggregated from "
    "the ChainPoller's ~10.5s ticks (contract-tape spec section 2, 'The "
    "forming candle'); wiring that up is a later task and cannot be verified "
    "until the market is open. It is never synthesised from the last "
    "completed bar -- a closed candle held open would look live and be a lie.")


def _sessions_back(day, n):
    """The `n` trading sessions ending on or before `day`, OLDEST FIRST.

    Weekends are skipped (instruments._prev_trading_day's rule). Exchange
    holidays are NOT modelled, so a holiday inside the window is requested,
    comes back empty, and is reported as a gap -- which is the honest outcome
    and strictly better than silently sliding the window to hide it.
    """
    d = datetime.strptime(day, "%Y-%m-%d")
    while d.weekday() >= 5:                      # a Sat/Sun request means the
        d -= timedelta(days=1)                   # session that actually traded
    out = [d.strftime("%Y-%m-%d")]
    while len(out) < n:
        out.append(instruments._prev_trading_day(out[-1]))
    return list(reversed(out))


def _one_session(raw, day):
    """Slice a rest_intraday response down to the bars that really fall on
    `day` (IST). Returns `(payload, served, lost)`.

    WHY THIS EXISTS -- measured against live Dhan on 2026-07-31, security
    65852, and REPRODUCIBLE over three passes:

        fromDate=2026-07-30 toDate=2026-07-30 ->    0 bars
        fromDate=2026-07-30 toDate=2026-07-31 ->  375 bars, 07-30 only
        fromDate=2026-07-29 toDate=2026-07-29 ->  375 bars, 07-29 only
        fromDate=2026-07-29 toDate=2026-07-30 ->  375 bars, 07-29 only
        fromDate=2026-07-28 toDate=2026-07-28 ->  375 bars, 07-28 only
        fromDate=2026-07-28 toDate=2026-07-29 ->  750 bars, 07-28 AND 07-29
        fromDate=2026-07-27 toDate=2026-07-28 ->  750 bars, 07-27 AND 07-28

    No single rule fits: toDate behaves EXCLUSIVE for the most recent session
    (which is why dhan_fetch sends day+1 at all -- without it the newest day
    returns nothing) and INCLUSIVE for older ones, where day+1 silently drags
    in the NEXT session too. So a response for "day" cannot be assumed to
    contain only "day", and the request date is not a safe label for the bars
    that come back.

    The bars are therefore dated from their OWN timestamps. Bars belonging to
    another session are removed here rather than downstream, because they
    would otherwise be banded into this session's VWAP -- two trading days
    sharing one 09:15 anchor, which is exactly the leak the per-session split
    exists to prevent. `served` reports what Dhan actually sent, per date, so
    the over-fetch stays visible instead of being quietly discarded.

    `lost` counts rows dropped before reshape: ragged-array truncation plus
    rows whose timestamp is not a real instant and so cannot be placed in any
    session at all.
    """
    if not isinstance(raw, dict):
        return {}, {}, 0
    arrays = {k: v for k, v in raw.items() if isinstance(v, (list, tuple))}
    if "timestamp" not in arrays or not arrays:
        return raw if isinstance(raw, dict) else {}, {}, 0
    lens = [len(v) for v in arrays.values()]
    n, longest = min(lens), max(lens)
    ts = arrays["timestamp"]
    served, keep, bad = {}, [], 0
    for i in range(n):
        t = ts[i]
        d = None
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            try:
                d = datetime.fromtimestamp(t, IST).strftime("%Y-%m-%d")
            except (OverflowError, OSError, ValueError):
                d = None
        if d is None:
            bad += 1
            continue
        served[d] = served.get(d, 0) + 1
        if d == day:
            keep.append(i)
    out = dict(raw)
    for k, v in arrays.items():
        out[k] = [v[i] for i in keep]
    return out, served, (longest - n) + bad


def _leg_series(fetch, sessions, interval):
    """One leg across `sessions`: reshape -> per-session VWAP -> resample.

    `fetch(day)` returns one `dhan_fetch.rest_intraday` payload, or raises.
    Each response is first cut down to the session it was asked for (see
    `_one_session` -- Dhan can and does return the following day too), then
    banded on ITS OWN 09:15 anchor and only then concatenated, so yesterday's
    volume can never bleed into today's VWAP (spec section 2: "anchored at
    09:15 and reset every session").

    `bars`, `vwap`, `oi` and `bar_days` are aligned 1:1 by index. `bar_days`
    exists because bar timestamps are "HH:MM" -- with more than one session in
    the array that is ambiguous, and dating the bars is the only way a caller
    can line a bar up against `gaps`.

    A session Dhan serves no bars for is listed in `gaps` and NEVER
    interpolated; `gap_reasons` says whether it came back empty or the call
    itself failed, because those are different facts about the world.
    """
    bars, vwap, oi, bar_days = [], [], [], []
    gaps, reasons, lengths, served_by = [], {}, {}, {}
    dropped = 0
    for sess in sessions:
        try:
            raw = fetch(sess)
        except Exception as e:                   # noqa: BLE001 - recorded, not swallowed
            gaps.append(sess)
            reasons[sess] = f"fetch failed: {type(e).__name__}: {e}"
            continue
        mine, served, lost = _one_session(raw, sess)
        if served:
            served_by[sess] = served
        one = contract_bars.to_bars(mine)
        dropped += one.dropped + lost
        if one.lengths:
            lengths[sess] = one.lengths
        rows = contract_bars.resample(contract_bars.vwap_bands(one), interval)
        if not rows:
            reasons[sess] = (
                "Dhan served no usable bars for this session (it returned "
                f"{served or 'nothing at all'} by date). The expired-option "
                "feed is rolling-ATM, so a strike far from spot that day may "
                "genuinely have no history -- see context/mental-map.md "
                "caveat 2.")
            gaps.append(sess)
            continue
        for b in rows:
            bars.append({k: b.get(k) for k in contract_bars.BAR_KEYS})
            vwap.append({k: b.get(k) for k in contract_bars.BAND_KEYS})
            oi.append(b.get("oi"))
            bar_days.append(sess)
    return {"bars": bars, "vwap": vwap, "oi": oi, "bar_days": bar_days,
            "gaps": gaps, "gap_reasons": reasons,
            "dropped": dropped, "lengths": lengths,
            "served_by_request": served_by,      # what Dhan sent per request
            "forming": None, "forming_why": FORMING_WHY}


def build_contract(idx, strike=None, side="BOTH", interval=3, days=1,
                   day=None, chain_rows=None, fetch=None):
    """The `/api/contract` payload: option-premium bars + their own VWAP.

    `strike` None means "let contract_pair.pick_pair choose", which needs a
    chain snapshot: pass `chain_rows` (the `strikes` list off an /api/chain
    payload) to reuse one the poller already paid for, or leave it None and
    one is fetched. `pick_pair` returns a `(pair, why)` TUPLE and the pair's
    CE and PE sit at DIFFERENT strikes -- that is the setup, not a bug.

    `fetch(sec_id, day) -> rest_intraday payload` is injectable so the
    assembly can be tested without a token or a network.

    Shape note: with `side=BOTH` the two legs are two different strikes, so
    there is no single top-level series and `bars`/`vwap`/`oi` are `null`; the
    arrays live under `legs.CE` / `legs.PE`. With one side requested the
    top-level arrays are filled in as spec section 2 describes.

    `day` defaults to today and is the newest session charted. Passing an
    older `day` backfills history, but note the asymmetry: the BARS are
    historical while the chain snapshot the pair is picked from is fetched
    LIVE, so with `day` != today the pair describes the market now and the
    bars describe the market then. The operator's setup picks the pair at
    ~09:20 of the session being traded, so only `day` == today is a faithful
    reproduction of it; a backfilled pair is a convenience, not the setup.

    Not implemented here, deliberately: `spot` (needs the FUT series per
    session -- another request per session, and no consumer yet) and
    `narration` (its own task). `forming` is always null; see FORMING_WHY.
    """
    import chain_live
    import dhan_fetch
    from contract_pair import pick_pair

    side = (side or "BOTH").upper()
    if side not in ("CE", "PE", "BOTH"):
        raise ValueError(f"side must be CE, PE or BOTH, got {side!r}")
    interval = max(1, min(60, int(interval)))
    days = max(1, min(CONTRACT_MAX_DAYS, int(days)))
    cfg = instruments.get(idx)                   # KeyError on an unknown index
    day = day or datetime.now(IST).strftime("%Y-%m-%d")
    sessions = _sessions_back(day, days)

    tok = chain_live.read_token()
    st = chain_live.token_status(tok)
    if not st["ok"]:
        raise RuntimeError(st["msg"])
    dhan = chain_live._client(tok)

    # The OPTION expiry, not the futures one build_payload resolves: _atm_ids
    # matches OPTIDX rows on cfg['expiry'], so this is what decides which
    # contract's history we are about to chart.
    expiry = chain_live._with_deadline(
        lambda: chain_live.resolve_expiry(dhan, day, cfg["under_id"],
                                          cfg["under_seg"]),
        chain_live.CHAIN_DEADLINE_S, f"{idx} expiry_list")
    cfg["expiry"] = expiry

    pair, why = None, None
    if chain_rows is None and strike is None:
        try:
            resp = chain_live._with_deadline(
                lambda: dhan.option_chain(cfg["under_id"], cfg["under_seg"],
                                          expiry),
                chain_live.CHAIN_DEADLINE_S, f"{idx} option_chain")
            chain_rows = chain_live.normalize(
                chain_live._inner(resp), datetime.now(IST),
                cfg.get("window", chain_live.WINDOW_PTS))["strikes"]
        except Exception as e:                   # noqa: BLE001 - reported below
            why = f"no chain snapshot to pick a pair from: {type(e).__name__}: {e}"
    if chain_rows:
        pair, why = pick_pair(chain_rows, idx)
    elif why is None:
        why = ("pair not computed: an explicit strike was requested and no "
               "chain snapshot was supplied, so no chain request was spent")

    sides = ("CE", "PE") if side == "BOTH" else (side,)
    if strike is not None:
        strike = float(strike)
        want = [(s, strike) for s in sides]
    else:
        if pair is None:
            raise RuntimeError(f"no strike requested and no pair could be "
                               f"picked: {why}")
        want = [(s, pair[s.lower()]["strike"]) for s in sides]

    def _real_fetch(sec_id, sess):
        _throttle()                              # the shared 5-req/s gate
        return chain_live._with_deadline(
            lambda: dhan_fetch.rest_intraday(tok, sec_id, "OPTIDX", sess,
                                             oi=True, seg=cfg["fut_seg"]),
            CONTRACT_DEADLINE_S, f"{idx} intraday {sec_id} {sess}")

    fetch = fetch or _real_fetch
    legs, gaps, reasons = {}, [], {}
    for s, k in want:
        # _atm_ids raises if neither leg resolves within one strike step, so a
        # truncated scrip master fails loudly instead of charting a neighbour.
        sec_id = _atm_ids(k, cfg)[s]
        leg = _leg_series(lambda sess, _i=sec_id: fetch(_i, sess),
                          sessions, interval)
        leg["side"], leg["strike"], leg["security_id"] = s, k, sec_id
        legs[s] = leg
        for g in leg["gaps"]:
            if g not in gaps:
                gaps.append(g)
            reasons[f"{s} {g}"] = leg["gap_reasons"][g]

    out = {"ok": True, "index": idx, "expiry": expiry, "interval": interval,
           "days": days, "sessions": sessions, "side": side, "strike": strike,
           "pair": pair, "pair_why": why, "legs": legs,
           "bars": None, "vwap": None, "oi": None, "bar_days": None,
           "gaps": sorted(gaps), "gap_reasons": reasons,
           "forming": None, "forming_why": FORMING_WHY,
           "built_at": time.time(), "live_error": None}
    if len(legs) == 1:
        only = next(iter(legs.values()))
        out.update({k: only[k] for k in
                    ("strike", "side", "bars", "vwap", "oi", "bar_days")})
    return out


def build_payload(cfg):
    """Fetch today, run the engine, return the /api/data JSON bytes for `cfg`."""
    tok = _token()
    today = datetime.now(IST).strftime("%Y-%m-%d")
    day_lbl = datetime.now(IST).strftime("%b %d")
    seg = cfg["fut_seg"]
    fut_raw = _intraday(tok, cfg["fut_id"], "FUTIDX", today, seg=seg)
    if not fut_raw.get("close"):
        return json.dumps({"index": cfg["under_sym"], "strike": None, "days": [],
                           "built_at": time.time(),
                           "live_error": "no bars yet for " + today}).encode()
    strike = float(_pick_strike(fut_raw["close"][-1], cfg))
    ids = _atm_ids(strike, cfg)
    time.sleep(0.22)
    ce_raw = _intraday(tok, ids["CE"], "OPTIDX", today, seg=seg)
    time.sleep(0.22)
    pe_raw = _intraday(tok, ids["PE"], "OPTIDX", today, seg=seg)
    piv = _pivots(tok, cfg)

    fut, ce, pe = (_bars(x, piv) for x in (fut_raw, ce_raw, pe_raw))
    # align on common minutes (options can miss the odd bar)
    keep = ({b["T"] for b in ce} & {b["T"] for b in pe} & {b["T"] for b in fut})
    fut = [b for b in fut if b["T"] in keep]
    ce = [b for b in ce if b["T"] in keep]
    pe = [b for b in pe if b["T"] in keep]

    exp = datetime.strptime(cfg["expiry"] + " 15:30",
                            "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    t_days = max((exp - datetime.now(IST)).total_seconds() / 86400.0, 0.25)
    s = Session(day_lbl + " LIVE", fut, ce, pe, quiet=True,
                strike=strike, t_days=t_days)
    s.run()
    js = session_json(s)
    # mid-session: the end-of-day CARRY verdict is meaningless until the
    # close — suppress it so the feed never shows a 15:29 event at 10:30
    if js["bars"] and js["bars"][-1]["t"] < "15:25":
        js["events"] = [e for e in js["events"] if e["kind"] != "CARRY"]
    # Phase 3.5 SMC/ICT layer, additive: each structure carries the index of
    # the bar that completed it, so the UI clips by `born` instead of the
    # backend re-deriving structure per scrub position. v1 ignores the key.
    # The pivots block goes in too: it is the prior session's H/L/C in reduced
    # form, and structure.py inverts PDH/PDL/PDC back out of it (refusing, and
    # emitting nothing, if the numbers do not check out as floor pivots).
    js["structures"] = structure.compute(js["bars"], pivots=js.get("pivots"))
    return json.dumps({"index": cfg["under_sym"], "strike": strike, "live": True,
                       "expiry": cfg["expiry"], "built_at": time.time(),
                       "days": [js]}).encode()


if __name__ == "__main__":
    from instruments import get, resolve_dynamic
    today0 = datetime.now(IST).strftime("%Y-%m-%d")
    cfg0 = resolve_dynamic(get("NIFTY"), _token(), today0)
    p = build_payload(cfg0)
    d = json.loads(p)
    if d.get("live_error"):
        print("live:", d["live_error"])
    else:
        day = d["days"][0]
        bars = day["bars"]
        last = bars[-1]
        print(f"LIVE {d['index']} {day['day']} strike {d['strike']:.0f}: "
              f"{len(bars)} bars, last {last['t']} FUT {last['fut']['c']:.1f}")
        ctx = last.get("ctx", {})
        print("verdict:", ctx.get("verdict"), "|", ctx.get("line"))
        print("events:", len(day["events"]))
