"""Fetch 1-min OHLCV+OI from Dhan for NIFTY FUT / CE / PE and validate vs CSVs.

Usage:
  python dhan_fetch.py resolve                 # find security ids
  python dhan_fetch.py validate 2026-07-17 ID  # fetch FUT day, print sample bars
  python dhan_fetch.py chain 2026-07-17        # fetch GEX chain -> data/chain_<date>.json
"""

import csv
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dhanhq import DhanContext, dhanhq

IST = timezone(timedelta(hours=5, minutes=30))


def _client_id():
    """Dhan client id from env or a gitignored .dhan_client file (never in source)."""
    cid = os.environ.get("DHAN_CLIENT_ID", "").strip()
    if cid:
        return cid
    p = Path(__file__).parent / ".dhan_client"
    if p.exists():
        return p.read_text().strip()
    raise RuntimeError("set DHAN_CLIENT_ID env var or create .dhan_client file")


FUT_ID = "61093"                 # NIFTY Jul-2026 future (from `resolve`)
CHAIN_EXPIRY = "2026-07-21"      # weekly expiry the GEX chain prices against
CHAIN_STRIKES = [24000, 24100, 24200, 24300, 24400]
INTRADAY_URL = "https://api.dhan.co/v2/charts/intraday"


def client():
    token = open(".dhan_token").read().strip()
    return dhanhq(DhanContext(_client_id(), token))


def resolve():
    """Find NIFTY current FUT + 24200 CE/PE (21 Jul 2026 expiry) in security master."""
    import io
    import urllib.request
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    raw = urllib.request.urlopen(url, timeout=60).read().decode("utf-8", "replace")
    rdr = csv.DictReader(io.StringIO(raw))
    hits = []
    for r in rdr:
        sym = (r.get("SEM_TRADING_SYMBOL") or "")
        inst = (r.get("SEM_INSTRUMENT_NAME") or "")
        if not sym.startswith("NIFTY"):
            continue
        exp = (r.get("SEM_EXPIRY_DATE") or "")[:10]
        if inst == "FUTIDX" and exp.startswith("2026-07"):
            hits.append(("FUT", sym, r["SEM_SMST_SECURITY_ID"], exp, ""))
        if inst == "OPTIDX" and exp == "2026-07-21":
            strike = (r.get("SEM_STRIKE_PRICE") or "")
            if strike.split(".")[0] == "24200":
                hits.append((r.get("SEM_OPTION_TYPE"), sym,
                             r["SEM_SMST_SECURITY_ID"], exp, strike))
    for h in hits:
        print(h)


def fetch_day(dhan, sec_id, instrument, day):
    r = dhan.intraday_minute_data(
        security_id=str(sec_id),
        exchange_segment="NSE_FNO",
        instrument_type=instrument,
        from_date=day,
        to_date=day,
    )
    if r.get("status") != "success":
        print("FAIL:", r.get("remarks"))
        return None
    return r["data"]


def validate(day):
    dhan = client()
    fut_id = sys.argv[3] if len(sys.argv) > 3 else None
    if not fut_id:
        print("pass FUT security id as 3rd arg (from `resolve`)")
        return
    d = fetch_day(dhan, fut_id, "FUTIDX", day)
    if d is None:
        return
    keys = list(d.keys())
    n = len(d.get("close", []))
    print("keys:", keys, "| bars:", n)
    for i in range(0, n, max(1, n // 8)):
        ts = datetime.fromtimestamp(d["timestamp"][i], IST).strftime("%H:%M")
        oi = (d.get("open_interest") or [0] * n)[i]
        print(f"{ts}  O {d['open'][i]:.1f} H {d['high'][i]:.1f} L {d['low'][i]:.1f} "
              f"C {d['close'][i]:.1f} V {d['volume'][i]:.0f} OI {oi:.0f}")


def _intraday_body(sec_id, instrument, day, oi, seg="NSE_FNO"):
    """Build the POST body for /v2/charts/intraday.

    `toDate` is EXCLUSIVE for the MOST RECENT session -- fromDate == toDate
    == day returns zero bars for it (verified live 2026-07-30: NIFTY sec id
    65852 returned 375 real 1-min bars with toDate = day + 1, none with
    toDate = day). So toDate is always day plus one calendar day here, even
    though callers still pass a single session -- do NOT "simplify" this back
    to toDate = day, it will silently break the newest fetch.

    It is NOT exclusive for older sessions. Re-measured 2026-07-31 against
    the same security, reproducible over three passes::

        07-30 -> 07-30:    0 bars      07-30 -> 07-31:  375 (07-30 only)
        07-29 -> 07-29:  375 bars      07-29 -> 07-30:  375 (07-29 only)
        07-28 -> 07-28:  375 bars      07-28 -> 07-29:  750 (07-28 AND 07-29)
        07-27 -> 07-28:  750 bars (07-27 AND 07-28)

    So day + 1 OVER-FETCHES the following session once the requested day is
    old enough. A caller asking for one session must therefore filter the
    response by each bar's own IST timestamp rather than trusting the request
    date -- `live._one_session` does exactly that and carries the receipt.

    `seg` is the exchange segment. It defaults to NSE_FNO (what every caller
    before /api/contract needed) but must be BSE_FNO for SENSEX legs --
    `instruments.py` carries the right value per index as `fut_seg`, and
    sending the wrong one returns an empty series rather than an error.
    """
    to_date = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    return {
        "securityId": str(sec_id),
        "exchangeSegment": seg,
        "instrument": instrument,
        "interval": "1",
        "oi": bool(oi),
        "fromDate": day,
        "toDate": to_date,
    }


def rest_intraday(token, sec_id, instrument, day, oi=False, seg="NSE_FNO"):
    """Direct REST 1-min chart call (the SDK lacks the oi flag; validated
    pattern: POST /v2/charts/intraday with oi:true returns open_interest).

    `day` is a single calendar session; see _intraday_body for why toDate
    is sent as day + 1 (the endpoint's toDate is exclusive) and why `seg`
    exists.
    """
    body = json.dumps(_intraday_body(sec_id, instrument, day, oi, seg)).encode()
    req = urllib.request.Request(
        INTRADAY_URL, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/json",
                 "access-token": token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def resolve_chain_ids():
    """Scrip-master lookup (same source as resolve()) -> {strike: {CE,PE} ids}."""
    import io
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    raw = urllib.request.urlopen(url, timeout=60).read().decode("utf-8", "replace")
    rdr = csv.DictReader(io.StringIO(raw))
    want = {float(k) for k in CHAIN_STRIKES}
    ids = {}
    for r in rdr:
        sym = (r.get("SEM_TRADING_SYMBOL") or "")
        if not sym.startswith("NIFTY"):
            continue
        if (r.get("SEM_INSTRUMENT_NAME") or "") != "OPTIDX":
            continue
        if (r.get("SEM_EXPIRY_DATE") or "")[:10] != CHAIN_EXPIRY:
            continue
        try:
            strike = float(r.get("SEM_STRIKE_PRICE") or "")
        except ValueError:
            continue
        if strike in want:
            ids.setdefault(int(strike), {})[r.get("SEM_OPTION_TYPE")] = \
                r["SEM_SMST_SECURITY_ID"]
    return ids


def _series(d, with_oi=False):
    """Dhan chart arrays -> compact {t(HH:MM IST), o,h,l,c,v[,oi]} lists."""
    n = len(d.get("close", []))
    out = {
        "t": [datetime.fromtimestamp(ts, IST).strftime("%H:%M")
              for ts in d["timestamp"]],
        "o": d["open"], "h": d["high"], "l": d["low"], "c": d["close"],
        "v": d["volume"],
    }
    if with_oi:
        out["oi"] = d.get("open_interest") or [0] * n
    return out


def chain(day):
    """Fetch FUT + 5-strike CE/PE 1-min OHLCV+OI -> data/chain_<day>.json."""
    token = open(".dhan_token").read().strip()
    print(f"resolving {CHAIN_EXPIRY} option ids from scrip master ...")
    ids = resolve_chain_ids()
    for k in CHAIN_STRIKES:
        if k not in ids or "CE" not in ids[k] or "PE" not in ids[k]:
            print(f"FAIL: strike {k} missing from scrip master ({ids.get(k)})")
            return
        print(f"  {k}: CE {ids[k]['CE']}  PE {ids[k]['PE']}")

    print(f"fetching FUT {FUT_ID} ...")
    fut = rest_intraday(token, FUT_ID, "FUTIDX", day)
    if not fut.get("close"):
        print("FAIL: empty FUT response", fut)
        return
    time.sleep(0.25)              # data APIs capped at 5 req/s

    strikes = {}
    for k in CHAIN_STRIKES:
        sides = {}
        for side in ("CE", "PE"):
            print(f"fetching {k} {side} ({ids[k][side]}) ...")
            d = rest_intraday(token, ids[k][side], "OPTIDX", day, oi=True)
            if not d.get("close"):
                print(f"FAIL: empty response for {k} {side}", d)
                return
            sides[side.lower()] = _series(d, with_oi=True)
            time.sleep(0.25)      # 5 req/s cap
        strikes[str(k)] = sides

    out = {"date": day, "expiry": CHAIN_EXPIRY,
           "fut": _series(fut), "strikes": strikes}
    path = f"data/chain_{day}.json"
    with open(path, "w") as f:
        json.dump(out, f)
    print(f"wrote {path}: FUT {len(out['fut']['t'])} bars, "
          f"{len(strikes)} strikes x CE/PE")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "resolve"
    if cmd == "resolve":
        resolve()
    elif cmd == "validate":
        validate(sys.argv[2])
    elif cmd == "chain":
        chain(sys.argv[2] if len(sys.argv) > 2 else "2026-07-17")
