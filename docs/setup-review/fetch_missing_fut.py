"""fetch_missing_fut.py -- 13 Nov 2026 (NOTEPAD A318), on her "yes fetch them".

The trigger log holds NIFTY days whose 1-min futures candles were never saved (no data/backtest file). This fetches
them once from Upstox's expired-instruments history: the NIFTY future expiring on or after the day (the cache's own
convention: on an expiry day, that day's contract). Saved apart, in docs/setup-review/candles/, so nothing the live
tool reads changes. Read-only towards Upstox; never prints the token.

    python -X utf8 docs/setup-review/fetch_missing_fut.py 2026-08-04 2026-08-05 ...
"""
import json
import os
import sys
import urllib.error
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import upstox_feed  # noqa: E402
import upstox_rest as U  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "candles")
IDX = urllib.parse.quote("NSE_INDEX|Nifty 50", safe="")


def main(days):
    tok = upstox_feed.read_token()
    os.makedirs(OUT, exist_ok=True)
    try:
        exps = sorted(U._get(f"{U.BASE}/expired-instruments/expiries?instrument_key={IDX}", tok).get("data") or [])
    except urllib.error.HTTPError as e:
        print(f"expiries: HTTP {e.code} {e.read()[:300]!r}")
        return 2
    keys = {}
    for day in days:
        exp = key = None
        for x in (x for x in exps if x >= day):              # the list holds the weekly option expiries too; futures are monthly
            if x not in keys:
                rows = U._get(f"{U.BASE}/expired-instruments/future/contract?instrument_key={IDX}&expiry_date={x}", tok).get("data") or []
                keys[x] = (rows[0] or {}).get("instrument_key") if rows else None
            if keys[x]:
                exp, key = x, keys[x]
                break
        if not key:
            print(f"{day}: no expired future on or after it")
            continue
        url = f"{U.BASE}/expired-instruments/historical-candle/{urllib.parse.quote(key, safe='')}/1minute/{day}/{day}"
        try:
            c = (U._get(url, tok).get("data") or {}).get("candles") or []
        except urllib.error.HTTPError as e:
            print(f"{day}: HTTP {e.code}")
            continue
        bars = sorted({r[0][11:16]: {"t": r[0][11:16], "o": r[1], "h": r[2], "l": r[3], "c": r[4], "v": r[5], "oi": r[6] if len(r) > 6 else None}
                       for r in c if "09:15" <= r[0][11:16] <= "15:29"}.values(), key=lambda b: b["t"])
        if bars:
            with open(os.path.join(OUT, f"fut_NIFTY_{day}.json"), "w", encoding="utf-8") as fh:
                json.dump({"day": day, "expiry": exp, "key": key, "source": "upstox expired-instruments 1minute", "bars": bars}, fh)
        print(f"{day}: expiry {exp} · {len(bars)} minutes · volume on {sum(1 for b in bars if b['v'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
