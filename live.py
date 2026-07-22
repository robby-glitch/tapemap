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

import csv
import io
import json
import math
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from engine import Session, session_json
from instruments import SCRIP_URL

IST = timezone(timedelta(hours=5, minutes=30))
REFRESH_S = 15
INTRADAY_URL = "https://api.dhan.co/v2/charts/intraday"

_stick = {}                             # per-index sticky-ATM state: sym -> {...}


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
        return cand
    if cand != st["strike"] and abs(F - st["strike"]) > 0.6 * step:
        st["drift"] += 1
    else:
        st["drift"] = 0
    if st["drift"] >= 5:
        st["strike"], st["drift"] = cand, 0
    return st["strike"]


def _intraday(tok, sec_id, instrument, day, oi=True, seg="NSE_FNO"):
    body = json.dumps({"securityId": str(sec_id), "exchangeSegment": seg,
                       "instrument": instrument, "interval": "1", "oi": oi,
                       "fromDate": day, "toDate": day}).encode()
    req = urllib.request.Request(INTRADAY_URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "access-token": tok})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _atm_ids(tok, strike, cfg):
    """CE/PE security ids for the strike nearest `strike` at cfg['expiry'].

    Resolved from the detailed scrip master, matched on
    UNDERLYING_SYMBOL / INSTRUMENT / OPTION_TYPE / STRIKE_PRICE — uniform across
    NSE and BSE (SENSEX option trading symbols are the generic 'BSXOPT', so a
    trading-symbol prefix match would fail). Picks the nearest listed strike so
    a step mismatch never leaves a leg unresolved."""
    raw = urllib.request.urlopen(SCRIP_URL, timeout=60).read().decode("utf-8", "replace")
    sym, exp = cfg["under_sym"], cfg["expiry"]
    best = {}                                    # option_type -> (dist, sec_id)
    for r in csv.DictReader(io.StringIO(raw)):
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
    return {ot: sid for ot, (_d, sid) in best.items()}


def _pivots(tok, cfg):
    """Standard pivots off the prior session's FUT H/L/C."""
    d = _intraday(tok, cfg["fut_id"], "FUTIDX", cfg["prev_day"], oi=False,
                  seg=cfg["fut_seg"])
    H, L, C = max(d["high"]), min(d["low"]), d["close"][-1]
    P = (H + L + C) / 3.0
    return {"P": P, "R1": 2 * P - L, "S1": 2 * P - H,
            "R2": P + (H - L), "S2": P - (H - L),
            "R3": H + 2 * (P - L), "S3": L - 2 * (H - P)}


def _bars(d, piv):
    """Dhan arrays -> engine bar dicts with session VWAP + sigma bands
    (VWAP = cum(TP*V)/cumV, TP=(H+L+C)/3; bands = VWAP ± n*sqrt(Var_w))."""
    n = len(d.get("close", []))
    oi = d.get("open_interest") or [0.0] * n
    bars = []
    cv = ctpv = cvar = 0.0
    for i in range(n):
        ts = datetime.fromtimestamp(d["timestamp"][i], IST)
        h, l, c, v = d["high"][i], d["low"][i], d["close"][i], d["volume"][i]
        tp = (h + l + c) / 3.0
        cv += v
        ctpv += tp * v
        vwap = ctpv / cv if cv > 0 else c
        cvar += v * (tp - vwap) ** 2
        sd = math.sqrt(cvar / cv) if cv > 0 else 0.0
        bar = {"T": ts.strftime("%H:%M"), "O": d["open"][i], "H": h, "L": l,
               "C": c, "VWAP": vwap,
               "U1": vwap + sd, "D1": vwap - sd,
               "U2": vwap + 2 * sd, "D2": vwap - 2 * sd,
               "U3": vwap + 3 * sd, "D3": vwap - 3 * sd,
               "OI": oi[i], "V": v}
        bar.update(piv)
        bars.append(bar)
    return bars


def build_payload(cfg):
    """Fetch today, run the engine, return the /api/data JSON bytes for `cfg`."""
    tok = _token()
    today = datetime.now(IST).strftime("%Y-%m-%d")
    day_lbl = datetime.now(IST).strftime("%b %d")
    seg = cfg["fut_seg"]
    fut_raw = _intraday(tok, cfg["fut_id"], "FUTIDX", today, seg=seg)
    if not fut_raw.get("close"):
        return json.dumps({"index": cfg["under_sym"], "strike": None, "days": [],
                           "live_error": "no bars yet for " + today}).encode()
    strike = float(_pick_strike(fut_raw["close"][-1], cfg))
    ids = _atm_ids(tok, strike, cfg)
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
    return json.dumps({"index": cfg["under_sym"], "strike": strike, "live": True,
                       "expiry": cfg["expiry"], "days": [js]}).encode()


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
