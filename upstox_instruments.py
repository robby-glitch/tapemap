"""Which instrument keys to subscribe to, resolved once a day and cached.

WHY THE CACHE IS THE POINT. Upstox publishes the whole NSE universe as one
gzipped dump. On 2026-07-27 this tool served a frozen tape for most of a
session because the equivalent Dhan scrip master (37MB) was being pulled every
cycle; the fetch, not the logic, was the outage. So the dump is fetched at most
once per `MAX_AGE_H`, and what is written to disk is the FILTERED slice -- a
few thousand NIFTY rows instead of the full universe -- so re-reads are cheap
and a stale cache is obvious from its date.

`resolve()` returns everything the feed and the adapter need:

    idx_key   the index, whose ltp is the chain's spot
    fut_key   the near future, whose ltp is the tape's own frame
    expiry    the nearest LIVE expiry, as YYYY-MM-DD
    keys      what to subscribe -- index, future and both legs per strike
    meta      {instrument_key: (strike, "ce"|"pe")}, exactly what
              `upstox_adapter.chain_payload` needs to know who each key is

NIFTY WEEKLIES EXPIRE ON **TUESDAY** (2026-08-11, -18, -25, straight from the
dump). Anything in this repo that still assumes Thursday is wrong; the expiry
is read from the data here rather than computed from a weekday.

Strikes are chosen by distance from spot, not by a fixed step, because the
step is not ours to assume -- it is whatever the exchange listed.
"""

import gzip
import io
import json
import os
import time
import urllib.request
from datetime import datetime

DUMP_URL = ("https://assets.upstox.com/market-quote/instruments/exchange/"
            "NSE.json.gz")
CACHE = os.path.join("data", "upstox_nifty.json")
MAX_AGE_H = 20                     # one trading day; the dump changes overnight
STRIKES_EACH_SIDE = 8

INDEX_KEY = {"NIFTY": "NSE_INDEX|Nifty 50",
             "BANKNIFTY": "NSE_INDEX|Nifty Bank"}


def _fetch_rows():
    with urllib.request.urlopen(DUMP_URL, timeout=120) as r:
        raw = gzip.GzipFile(fileobj=io.BytesIO(r.read())).read()
    return json.loads(raw.decode())


def _slice(rows, name):
    """Only what this tool ever subscribes to -- the rest is not cached."""
    return [{"instrument_key": x.get("instrument_key"),
             "instrument_type": (x.get("instrument_type") or "").upper(),
             "strike_price": x.get("strike_price"),
             "expiry": x.get("expiry"),
             "trading_symbol": x.get("trading_symbol")}
            for x in rows
            if x.get("segment") == "NSE_FO"
            and (x.get("name") or "").upper() == name]


def load(name="NIFTY", cache=CACHE, max_age_h=MAX_AGE_H, fetch=None):
    """Filtered rows for `name`, from disk when fresh enough.

    `fetch` is injectable so the cache policy can be tested without the
    network.
    """
    if os.path.exists(cache):
        age_h = (time.time() - os.path.getmtime(cache)) / 3600.0
        if age_h < max_age_h:
            try:
                with open(cache, encoding="utf-8") as f:
                    blob = json.load(f)
                if blob.get("name") == name and blob.get("rows"):
                    return blob["rows"]
            except (json.JSONDecodeError, OSError):
                pass                 # a corrupt cache is a re-fetch, not a crash
    rows = _slice((fetch or _fetch_rows)(), name)
    os.makedirs(os.path.dirname(cache) or ".", exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump({"name": name, "rows": rows}, f)
    return rows


def live_expiries(rows, now_ms=None):
    """Expiry timestamps still ahead of us, soonest first."""
    if now_ms is None:
        now_ms = datetime.now().timestamp() * 1000
    return sorted({x["expiry"] for x in rows
                   if isinstance(x.get("expiry"), (int, float))
                   and x["expiry"] >= now_ms})


def fut_key(name="NIFTY", rows=None):
    """The near-month future's instrument key.

    Separate from `resolve` because the bar path needs the future BEFORE it
    has a spot -- the future's own last price is what the spot is derived
    from -- while the strike window cannot be chosen without one.
    """
    rows = rows if rows is not None else load(name)
    futs = sorted((x for x in rows if x["instrument_type"] in ("FUT", "FUTIDX")),
                  key=lambda x: x.get("expiry") or 0)
    if not futs:
        raise RuntimeError(f"{name}: no future in the dump")
    return futs[0]["instrument_key"]


def option_keys(strike, name="NIFTY", rows=None, now_ms=None):
    """{'CE': key, 'PE': key} at `strike` on the NEAREST LIVE expiry.

    The bar path's answer to Dhan's `_atm_ids`. Raises rather than returning a
    partial dict: half a pair would chart one leg against nothing, and the
    caller reads both.
    """
    rows = rows if rows is not None else load(name)
    opts = [x for x in rows if x["instrument_type"] in ("CE", "PE")]
    exps = live_expiries(opts, now_ms)
    if not exps:
        raise RuntimeError(f"{name}: no live option expiry in the dump")
    want = float(strike)
    out = {x["instrument_type"]: x["instrument_key"] for x in opts
           if x["expiry"] == exps[0] and x.get("strike_price") == want}
    if "CE" not in out or "PE" not in out:
        raise RuntimeError(
            f"{name} {want:.0f}: expiry {exps[0]} has {sorted(out) or 'neither leg'}"
            f" — the strike is not listed on the nearest expiry")
    return out


def resolve(spot, name="NIFTY", each_side=STRIKES_EACH_SIDE, rows=None,
            now_ms=None):
    """-> {idx_key, fut_key, expiry, strikes, keys, meta}.

    `spot` centres the strike window. It is an argument rather than something
    fetched here so this stays pure and so the caller decides which frame it
    is centring on -- the index and the future differ by the basis, and a
    window centred on the wrong one is silently shifted by that much.
    """
    rows = rows if rows is not None else load(name)
    futs = sorted((x for x in rows if x["instrument_type"] in ("FUT", "FUTIDX")),
                  key=lambda x: x.get("expiry") or 0)
    opts = [x for x in rows if x["instrument_type"] in ("CE", "PE")]
    exps = live_expiries(opts, now_ms)
    if not exps:
        raise RuntimeError(f"{name}: no live option expiry in the dump")
    exp = exps[0]
    near = [x for x in opts if x["expiry"] == exp]

    strikes = sorted({x["strike_price"] for x in near
                      if isinstance(x.get("strike_price"), (int, float))},
                     key=lambda k: abs(k - spot))[:each_side * 2 + 1]
    chosen = sorted((x for x in near if x["strike_price"] in set(strikes)),
                    key=lambda x: (x["strike_price"], x["instrument_type"]))

    meta = {x["instrument_key"]: (int(x["strike_price"]),
                                  x["instrument_type"].lower())
            for x in chosen}
    idx_key = INDEX_KEY.get(name, f"NSE_INDEX|{name}")
    fut_key = futs[0]["instrument_key"] if futs else None
    keys = [idx_key] + ([fut_key] if fut_key else []) + list(meta)
    return {"idx_key": idx_key, "fut_key": fut_key,
            "expiry": datetime.fromtimestamp(exp / 1000).strftime("%Y-%m-%d"),
            "strikes": sorted(strikes), "keys": keys, "meta": meta}
