"""Which instrument keys to subscribe to, resolved once a day and cached.

WHY THE CACHE IS THE POINT, AND WHY IT IS PER INDEX. Upstox publishes each
exchange as one gzipped dump. On 2026-07-27 this tool served a frozen tape for
most of a session because the equivalent Dhan scrip master (37MB) was being
pulled every cycle; the fetch, not the logic, was the outage.

The first version of this file cached to ONE file for whatever index was asked
for last. With three indices enabled that thrashes -- NIFTY evicts SENSEX
evicts BANKNIFTY -- and every rotation re-downloads a dump. That is the same
outage rebuilt, so the cache is keyed per index and what lands on disk is the
FILTERED slice: a few thousand rows, not the exchange.

TWO EXCHANGES. SENSEX is not on the NSE dump. NIFTY and BANKNIFTY are NSE_FO;
SENSEX is BSE_FO and lives in the BSE dump, with its future typed `FUT` where
NIFTY's is `FUTIDX`. Both spellings are accepted below.

EXPIRY IS READ FROM THE DATA, NEVER COMPUTED FROM A WEEKDAY. Measured
2026-08-05: NIFTY weeklies expire **Tuesday** (2026-08-11), SENSEX weeklies
expire **Thursday** (2026-08-06). Any rule that assumes one weekday is wrong
for the other index, and both have moved before.

`resolve()` returns everything the feed and the adapter need:

    idx_key   the index, whose ltp is the chain's spot
    fut_key   the near future, whose ltp is the tape's own frame
    expiry    the nearest LIVE expiry, as YYYY-MM-DD
    keys      what to subscribe -- index, future and both legs per strike
    meta      {instrument_key: (strike, "ce"|"pe")}, exactly what
              `upstox_adapter.chain_payload` needs to know who each key is

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

DUMP_URL = "https://assets.upstox.com/market-quote/instruments/exchange/{}.json.gz"
CACHE_FMT = os.path.join("data", "upstox_{}.json")
MAX_AGE_H = 20                     # one trading day; the dump changes overnight
# Chosen deliberately, and measured 2026-08-05 (NIFTY, spot 24624, 11-Aug
# weekly) against the same tick recomputed at four widths:
#
#   each side   OI share   GEX share   max pain   CE wall   PE wall
#           8      46.3%       91.4%      24550     25000     24200
#          10      52.3%       97.4%      24550     25000     24200
#          15      66.0%       97.5%      24550     25000     24000
#          30     100.0%      100.0%      24550     25000     24000
#
# Max pain does not move at all -- far strikes cancel in the intrinsic-value
# sum -- and gamma decays fast enough that 8 strikes carry 91% of GEX. The near
# strikes really are where the positioning is.
#
# The one thing this width costs is WALL DISCOVERY. At +/-8 the PE wall reports
# 24200, which is the edge of the window; the real one is 24000, outside it. A
# wall sitting exactly on the boundary is usually the boundary, not a wall. The
# operator reads walls themselves and accepted that trade-off on 2026-08-05;
# raising this to 15 fixes it at the cost of ~20s more startup.
STRIKES_EACH_SIDE = 8
FUT_TYPES = ("FUT", "FUTIDX")      # NSE says FUTIDX, BSE says FUT

EXCHANGE = {"NIFTY": "NSE", "BANKNIFTY": "NSE", "SENSEX": "BSE"}

# What the index is called in its own dump's *_INDEX segment. Used to LOOK UP
# the instrument key rather than hardcode it, so a renamed key is a resolution
# failure with a message instead of a subscription that silently never ticks.
INDEX_SYMBOL = {"NIFTY": "nifty 50", "BANKNIFTY": "nifty bank",
                "SENSEX": "sensex"}


def exchange(name):
    exch = EXCHANGE.get(name.upper())
    if not exch:
        raise RuntimeError(
            f"{name}: no Upstox exchange mapped. Known: {sorted(EXCHANGE)}.")
    return exch


def _fetch_rows(exch):
    with urllib.request.urlopen(DUMP_URL.format(exch), timeout=120) as r:
        raw = gzip.GzipFile(fileobj=io.BytesIO(r.read())).read()
    return json.loads(raw.decode())


def _slice(rows, name, exch):
    """Only what this tool ever subscribes to -- the rest is not cached."""
    seg = f"{exch}_FO"
    return [{"instrument_key": x.get("instrument_key"),
             "instrument_type": (x.get("instrument_type") or "").upper(),
             "strike_price": x.get("strike_price"),
             "expiry": x.get("expiry"),
             "trading_symbol": x.get("trading_symbol")}
            for x in rows
            if x.get("segment") == seg
            and (x.get("name") or "").upper() == name]


def _find_index_key(rows, name, exch):
    """The index's own instrument key, out of the dump's *_INDEX segment."""
    seg, want = f"{exch}_INDEX", INDEX_SYMBOL.get(name.upper(), name).lower()
    for x in rows:
        if x.get("segment") == seg and (
                (x.get("trading_symbol") or "").strip().lower() == want
                or (x.get("name") or "").strip().lower() == want):
            return x.get("instrument_key")
    raise RuntimeError(
        f"{name}: no {seg} row matching '{want}'. The dump's naming changed; "
        f"subscribing to a guessed key would simply never tick.")


def _blob(name, max_age_h=MAX_AGE_H, fetch=None):
    """{'rows': [...], 'index_key': '...'} for `name`, from disk when fresh.

    `fetch` is injectable so the cache policy can be tested without the
    network.
    """
    name = name.upper()
    cache = CACHE_FMT.format(name.lower())
    if os.path.exists(cache):
        age_h = (time.time() - os.path.getmtime(cache)) / 3600.0
        if age_h < max_age_h:
            try:
                with open(cache, encoding="utf-8") as f:
                    blob = json.load(f)
                if blob.get("name") == name and blob.get("rows") \
                        and blob.get("index_key"):
                    return blob
            except (json.JSONDecodeError, OSError):
                pass                 # a corrupt cache is a re-fetch, not a crash
    exch = exchange(name)
    raw = (fetch or _fetch_rows)(exch)
    blob = {"name": name, "index_key": _find_index_key(raw, name, exch),
            "rows": _slice(raw, name, exch)}
    if not blob["rows"]:
        raise RuntimeError(f"{name}: no {exch}_FO rows in the {exch} dump")
    os.makedirs(os.path.dirname(cache) or ".", exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(blob, f)
    return blob


def load(name="NIFTY", fetch=None):
    """Filtered F&O rows for `name`."""
    return _blob(name, fetch=fetch)["rows"]


def index_key(name="NIFTY", fetch=None):
    """The index's instrument key -- the chain's spot comes from this."""
    return _blob(name, fetch=fetch)["index_key"]


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
    futs = sorted((x for x in rows if x["instrument_type"] in FUT_TYPES),
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
    name = name.upper()
    if rows is None:
        blob = _blob(name)
        rows, idx_key = blob["rows"], blob["index_key"]
    else:
        idx_key = None
    futs = sorted((x for x in rows if x["instrument_type"] in FUT_TYPES),
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
    fkey = futs[0]["instrument_key"] if futs else None
    keys = ([idx_key] if idx_key else []) + ([fkey] if fkey else []) + list(meta)
    return {"idx_key": idx_key, "fut_key": fkey,
            "expiry": datetime.fromtimestamp(exp / 1000).strftime("%Y-%m-%d"),
            "strikes": sorted(strikes), "keys": keys, "meta": meta}
