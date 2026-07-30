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


def _intraday_body(sec_id, instrument, day, oi, seg="NSE_FNO", to_day=None):
    """Build the POST body for /v2/charts/intraday.

    The ONE body builder in the codebase: `rest_intraday` below and
    `live._intraday` both come through here, so there is a single place where
    a date range is decided and a single place this note has to be read.

    `toDate` HAS NO SINGLE RULE. Measured against the live endpoint on
    2026-07-31 (NIFTY index, security id 13 / IDX_I -- 07-30 was the newest
    session carrying data), and consistent with the 2026-07-30 measurement
    that introduced the day + 1::

        07-30 -> 07-30:    0 bars      07-30 -> 07-31:  375 (07-30 only)
        07-29 -> 07-29:  375 bars      07-29 -> 07-30:  375 (07-29 only)
        07-28 -> 07-28:  375 bars      07-28 -> 07-29:  750 (07-28 AND 07-29)
        07-27 -> 07-27:  375 bars      07-27 -> 07-28:  750 (07-27 AND 07-28)

    So `toDate` behaves EXCLUSIVE for the newest session -- fromDate == toDate
    == day returns nothing for it -- and INCLUSIVE for older ones, where
    day + 1 silently drags the FOLLOWING session in as well. An earlier plan
    recorded "fromDate == toDate returns zero bars" as a general fact; the
    07-29 / 07-28 / 07-27 rows above falsify it, and the 750-bar rows are the
    reason `chain()` had been writing two days into one file.

    `to_day` therefore DEFAULTS to day + 1 -- the only value that serves the
    newest session -- but is settable. `live._intraday` passes `day`, because
    both of its callers (the current session in `build_payload`, the prior
    session in `_pivots`) consume the response whole and rely on exactly one
    session coming back; day + 1 would hand `_pivots` two sessions of H/L/C.

    Whichever value is sent, ONE DAY REQUESTED IS NOT ONE DAY RETURNED. Any
    caller that PERSISTS the bars must date each bar from its own IST
    timestamp and drop the rest -- `_one_session` below does exactly that, and
    `chain()` and `/api/contract` both go through it.

    `seg` is the exchange segment. It defaults to NSE_FNO (what every caller
    before /api/contract needed) but must be BSE_FNO for SENSEX legs --
    `instruments.py` carries the right value per index as `fut_seg`, and
    sending the wrong one returns an empty series rather than an error.
    """
    if to_day is None:
        to_day = (datetime.strptime(day, "%Y-%m-%d")
                  + timedelta(days=1)).strftime("%Y-%m-%d")
    return {
        "securityId": str(sec_id),
        "exchangeSegment": seg,
        "instrument": instrument,
        "interval": "1",
        "oi": bool(oi),
        "fromDate": day,
        "toDate": to_day,
    }


def _one_session(raw, day):
    """Slice a rest_intraday response down to the bars that really fall on
    `day` (IST). Returns `(payload, served, lost)`.

    WHY THIS EXISTS: `_intraday_body`'s measured table shows that neither
    `toDate == day` nor `toDate == day + 1` returns exactly one session for
    every date -- day + 1 returns TWO sessions once the requested day is old
    enough (07-28 -> 07-29 gave 750 bars across both days). So a response for
    "day" cannot be assumed to contain only "day", and the request date is not
    a safe label for the bars that come back.

    The bars are therefore dated from their OWN timestamps. Bars belonging to
    another session are removed here rather than downstream, because they
    would otherwise be banded into this session's VWAP -- two trading days
    sharing one 09:15 anchor, which is exactly the leak the per-session split
    exists to prevent. `served` reports what Dhan actually sent, per date, so
    the over-fetch stays visible instead of being quietly discarded.

    `lost` counts rows dropped before reshape: ragged-array truncation plus
    rows whose timestamp is not a real instant and so cannot be placed in any
    session at all.

    Lives here, next to the body builder whose behaviour makes it necessary,
    rather than in `live.py`: `dhan_fetch.chain` needs it too and `dhan_fetch`
    must not depend on `live`. `live.py` imports it.
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


def rest_intraday(token, sec_id, instrument, day, oi=False, seg="NSE_FNO"):
    """Direct REST 1-min chart call (the SDK lacks the oi flag; validated
    pattern: POST /v2/charts/intraday with oi:true returns open_interest).

    `day` names ONE calendar session, but the response is not guaranteed to
    contain only that session -- see `_intraday_body` for the measured date
    behaviour, and pass the result through `_one_session` before keeping it.
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


def _dup_times(series):
    """The "HH:MM" labels that appear more than once in a `_series` output."""
    seen, dups = set(), []
    for t in series["t"]:
        if t in seen and t not in dups:
            dups.append(t)
        seen.add(t)
    return dups


def chain(day, fetch=None, ids=None, out_dir="data"):
    """Fetch FUT + 5-strike CE/PE 1-min OHLCV+OI -> <out_dir>/chain_<day>.json.

    ONE SESSION. Every response is cut down to `day` by `_one_session` before
    it is reshaped, because a single-day request does not return a single day
    (see `_intraday_body`: 07-28 -> 07-29 returns 750 bars across both). That
    slice is not optional here: `_series` labels bars "HH:MM" with no date, so
    a second session in the array is INVISIBLE in the file, and `gex_run.run`
    keys its alignment on that label (`idx = {t: j ...}`) -- duplicates
    collapse last-wins, pairing day-1 futures with day-2 option closes and
    computing every IV / writer score / GEX in the file off mismatched days.

    Nothing is written unless every series has unique timestamps: a duplicate
    means the slice failed and the file would be silently wrong, so it raises.
    `served_by_request` records what Dhan actually sent per date, so an
    over-fetch stays visible in the file instead of being quietly dropped.

    `fetch(sec_id, instrument, oi) -> rest_intraday payload` and `ids` are
    injectable so the assembly can be tested without a token or a network.
    """
    if fetch is None:
        token = open(".dhan_token").read().strip()

        def fetch(sec_id, instrument, oi, _tok=token):
            r = rest_intraday(_tok, sec_id, instrument, day, oi=oi)
            time.sleep(0.25)          # data APIs capped at 5 req/s
            return r

    if ids is None:
        print(f"resolving {CHAIN_EXPIRY} option ids from scrip master ...")
        ids = resolve_chain_ids()
    for k in CHAIN_STRIKES:
        if k not in ids or "CE" not in ids[k] or "PE" not in ids[k]:
            print(f"FAIL: strike {k} missing from scrip master ({ids.get(k)})")
            return
        print(f"  {k}: CE {ids[k]['CE']}  PE {ids[k]['PE']}")

    print(f"fetching FUT {FUT_ID} ...")
    fut, fut_served, _lost = _one_session(fetch(FUT_ID, "FUTIDX", False), day)
    if not fut.get("close"):
        print(f"FAIL: no {day} bars in FUT response "
              f"(Dhan served {fut_served or 'nothing at all'} by date)")
        return
    served = {"fut": fut_served}

    strikes = {}
    for k in CHAIN_STRIKES:
        sides = {}
        for side in ("CE", "PE"):
            print(f"fetching {k} {side} ({ids[k][side]}) ...")
            d, srv, _lost = _one_session(
                fetch(ids[k][side], "OPTIDX", True), day)
            if not d.get("close"):
                print(f"FAIL: no {day} bars for {k} {side} "
                      f"(Dhan served {srv or 'nothing at all'} by date)")
                return
            served[f"{k}{side}"] = srv
            sides[side.lower()] = _series(d, with_oi=True)
        strikes[str(k)] = sides

    out = {"date": day, "expiry": CHAIN_EXPIRY,
           "fut": _series(fut), "strikes": strikes,
           "served_by_request": served}

    for label, s in ([("fut", out["fut"])]
                     + [(f"{k} {sd}", strikes[k][sd])
                        for k in strikes for sd in ("ce", "pe")]):
        dups = _dup_times(s)
        if dups:
            raise ValueError(
                f"{label}: {len(dups)} duplicated timestamp(s) in a "
                f"single-session series for {day} (first: {dups[:3]}). The "
                f"response carried more than one session and the per-session "
                f"slice did not remove it. Refusing to write {out_dir}/"
                f"chain_{day}.json -- gex_run would silently pair the wrong "
                f"days. Dhan served: {served.get(label.split()[0], served)}")

    path = os.path.join(out_dir, f"chain_{day}.json")
    with open(path, "w") as f:
        json.dump(out, f)
    print(f"wrote {path}: FUT {len(out['fut']['t'])} bars, "
          f"{len(strikes)} strikes x CE/PE")
    return path


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "resolve"
    if cmd == "resolve":
        resolve()
    elif cmd == "validate":
        validate(sys.argv[2])
    elif cmd == "chain":
        chain(sys.argv[2] if len(sys.argv) > 2 else "2026-07-17")
