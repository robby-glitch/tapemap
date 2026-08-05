"""Does the Upstox WEBSOCKET give what the REST chain refused?

WHY THIS EXISTS. `upstox_probe.py` measured the REST surface of the operator's
Analytics Token and found a split verdict: history works, the chain does not.
Six endpoints, one token --

    /v2/historical-candle/intraday/...   200  candles WITH open interest
    /v2/option/chain                     401  UDAPI100050
    /v3/market-quote/option-greek        401  UDAPI100050
    ... and three more 401s

That looked like the end of the road, because per-strike **implied volatility**
is the hinge: gamma, dealer-signed GEX, the flip price, both walls and the whole
ZONE READ are computed from it. Bars and OI are replaceable; IV is not.

But the token's own description says it covers "Market Data **and Real-time &
Streaming** APIs", and the V3 feed's proto carries the missing fields directly:

    message FirstLevelWithGreeks {      // <- what `option_greeks` mode returns
      LTPC ltpc = 1;  Quote firstDepth = 2;  OptionGreeks optionGreeks = 3;
      int64 vtt = 4;  double oi = 5;  double iv = 6;
    }

So REST-401 does not settle it. Streaming is a different scope, and this probe
asks the only question that matters: **does the socket hand us iv per strike?**

    python upstox_ws_probe.py            # ~25s, read-only, market hours

MEASURED 2026-08-05 10:17 IST, market open, one Analytics Token, one minute:

    wss://api.upstox.com/v3/feed/market-data-feed   401 at the HANDSHAKE
    /v3/feed/market-data-feed/authorize             401 UDAPI100050
    /v2/feed/market-data-feed/authorize             401 UDAPI100050
    /v2/historical-candle/intraday/NSE_INDEX|Nifty 50/1minute   200, live candles

**The API is not the problem; the token type is.** The feed really does carry
per-strike iv and the greeks -- the proto above is Upstox's own. But an
Analytics Token opens HISTORY ONLY: every live surface (quotes, chain,
option-greek, and now streaming) refuses it with the same UDAPI100050. Note
that code says "Invalid token used to access API", not "expired" -- it is a
token-CLASS rejection, and the 200 on the same token in the same second proves
the token itself is alive.

The unblock is therefore not code and not a static IP. It is a **regular OAuth
access token** from the daily login flow -- see `upstox_auth.py`.

CONFIRMED 2026-08-05 11:27 IST, market open, same probe, OAuth token:

    handshake            OK, socket accepted
    25 seconds           159 messages across 20 instruments
    segment status       NSE_FO / NSE_EQ / NSE_INDEX all NORMAL_OPEN
    IV per strike        18 of 18
    also arriving        oi, delta, gamma, theta -- per strike, live

    NIFTY 24700 CE  ltp 114.10  iv 0.1112  oi 8916050  delta  0.4359  gamma 0.0011
    NIFTY 24700 PE  ltp 164.50  iv 0.1033  oi 3740620  delta -0.5694  gamma 0.0012
    NIFTY 50 index  ltp 24613.45     (future last 24700.00 -> basis ~ +86.55)

So **Upstox can drive the whole stack**, and the greeks arrive already computed
-- the Black-Scholes step `chain_metrics` performs on Dhan's IV becomes a
cross-check rather than the only source. Whether to trust Upstox's greeks or
keep deriving our own is a real decision and is NOT settled here.

What this proves is that the DATA exists. It does not make the migration done:
the adapter, the chain-snapshot cadence, and the futures/index frame handling
are all still to be written.

The WebSocket 401 arrives as a bare handshake failure with no readable body,
which is why the error code above had to be recovered from the REST authorize
endpoint. Anything debugging this feed should reach for that endpoint first.

READ-ONLY. Subscribes, listens, disconnects. Writes nothing, places nothing,
and never prints the token. Reads `.upstox_token` (gitignored).

Two implementation notes worth keeping even if the answer is no:

  * The subscribe message must be sent as a **binary** frame. Sent as text the
    socket stays open and simply never delivers a feed -- a silent no-op that
    reads exactly like "no data available".
  * There is no protobuf build step here. The v3 schema is 14 small messages
    and fully known, so `_dec` walks the wire format against the SCHEMA tables
    below. That keeps `protoc` out of the repo for good.

A THROWAWAY probe, not part of the app -- the sibling of `upstox_probe.py`.
"""

import gzip
import io
import json
import struct
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime

import websocket

WS_URL = "wss://api.upstox.com/v3/feed/market-data-feed"
BASE = "https://api.upstox.com/v2"
INSTRUMENTS_URL = ("https://assets.upstox.com/market-quote/instruments/"
                   "exchange/NSE.json.gz")
TOKEN_FILE = ".upstox_token"
LISTEN_SECONDS = 25
STRIKES_EACH_SIDE = 4

# Cloudflare answers Python's default User-Agent with Error 1010 -- a 403 that
# reads exactly like an auth failure and is not one. Measured 2026-08-05 on the
# REST side; sent here too so a socket refusal cannot be blamed on the UA.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")


# --------------------------------------------------------------------------
# protobuf, by hand. See MarketDataFeed.proto v3.
# --------------------------------------------------------------------------

def _f(name, kind, sub=None, rep=False):
    return (name, kind, sub, rep)


LTPC = {1: _f("ltp", "double"), 2: _f("ltt", "int64"),
        3: _f("ltq", "int64"), 4: _f("cp", "double")}
QUOTE = {1: _f("bidQ", "int64"), 2: _f("bidP", "double"),
         3: _f("askQ", "int64"), 4: _f("askP", "double")}
GREEKS = {1: _f("delta", "double"), 2: _f("theta", "double"),
          3: _f("gamma", "double"), 4: _f("vega", "double"),
          5: _f("rho", "double")}
OHLC = {1: _f("interval", "string"), 2: _f("open", "double"),
        3: _f("high", "double"), 4: _f("low", "double"),
        5: _f("close", "double"), 6: _f("vol", "int64"), 7: _f("ts", "int64")}
MARKET_OHLC = {1: _f("ohlc", "msg", OHLC, True)}
MARKET_LEVEL = {1: _f("bidAskQuote", "msg", QUOTE, True)}
MARKET_FULL = {1: _f("ltpc", "msg", LTPC), 2: _f("marketLevel", "msg", MARKET_LEVEL),
               3: _f("optionGreeks", "msg", GREEKS),
               4: _f("marketOHLC", "msg", MARKET_OHLC), 5: _f("atp", "double"),
               6: _f("vtt", "int64"), 7: _f("oi", "double"), 8: _f("iv", "double"),
               9: _f("tbq", "double"), 10: _f("tsq", "double")}
INDEX_FULL = {1: _f("ltpc", "msg", LTPC), 2: _f("marketOHLC", "msg", MARKET_OHLC)}
FULL_FEED = {1: _f("marketFF", "msg", MARKET_FULL),
             2: _f("indexFF", "msg", INDEX_FULL)}
GREEK_FEED = {1: _f("ltpc", "msg", LTPC), 2: _f("firstDepth", "msg", QUOTE),
              3: _f("optionGreeks", "msg", GREEKS), 4: _f("vtt", "int64"),
              5: _f("oi", "double"), 6: _f("iv", "double")}
FEED = {1: _f("ltpc", "msg", LTPC), 2: _f("fullFeed", "msg", FULL_FEED),
        3: _f("firstLevelWithGreeks", "msg", GREEK_FEED),
        4: _f("requestMode", "enum")}
FEED_ENTRY = {1: _f("key", "string"), 2: _f("value", "msg", FEED)}
STATUS_ENTRY = {1: _f("key", "string"), 2: _f("value", "enum")}
MARKET_INFO = {1: _f("segmentStatus", "map", STATUS_ENTRY)}
FEED_RESPONSE = {1: _f("type", "enum"), 2: _f("feeds", "map", FEED_ENTRY),
                 3: _f("currentTs", "int64"), 4: _f("marketInfo", "msg", MARKET_INFO)}

TYPE_NAME = {0: "initial_feed", 1: "live_feed", 2: "market_info"}
MODE_NAME = {0: "ltpc", 1: "full_d5", 2: "option_greeks", 3: "full_d30"}
STATUS_NAME = {0: "PRE_OPEN_START", 1: "PRE_OPEN_END", 2: "NORMAL_OPEN",
               3: "NORMAL_CLOSE", 4: "CLOSING_START", 5: "CLOSING_END"}


def _varint(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, i
        s += 7


def _dec(buf, schema):
    """Walk the wire format against `schema`. Unknown fields are skipped, so a
    server-side addition cannot break the decoder."""
    out, i, n = {}, 0, len(buf)
    while i < n:
        tag, i = _varint(buf, i)
        fno, wt = tag >> 3, tag & 7
        if wt == 0:
            v, i = _varint(buf, i)
        elif wt == 1:
            v = struct.unpack_from("<d", buf, i)[0]
            i += 8
        elif wt == 2:
            ln, i = _varint(buf, i)
            v, i = buf[i:i + ln], i + ln
        elif wt == 5:
            v = struct.unpack_from("<f", buf, i)[0]
            i += 4
        else:
            raise ValueError(f"unexpected wire type {wt} at field {fno}")
        f = schema.get(fno)
        if f is None:
            continue
        name, kind, sub, rep = f
        if kind == "string":
            v = v.decode("utf-8", "replace")
        elif kind == "msg":
            v = _dec(v, sub)
        elif kind == "map":
            ent = _dec(v, sub)
            out.setdefault(name, {})[ent.get("key")] = ent.get("value")
            continue
        if rep:
            out.setdefault(name, []).append(v)
        else:
            out[name] = v
    return out


# --------------------------------------------------------------------------
# what to subscribe to
# --------------------------------------------------------------------------

def _tok():
    try:
        t = open(TOKEN_FILE, encoding="utf-8").read().strip()
    except OSError:
        sys.exit(f"no {TOKEN_FILE} — paste the Upstox access token into that file")
    if not t:
        sys.exit(f"{TOKEN_FILE} is empty")
    return t


def _spot(tok, fut_key):
    """Futures last, used only to centre the strike window."""
    url = (f"{BASE}/historical-candle/intraday/"
           f"{urllib.parse.quote(fut_key, safe='')}/1minute")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/json",
        "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode()).get("data") or {}
        candles = data.get("candles") or []
        return float(candles[0][4]) if candles else None
    except Exception as e:                       # noqa: BLE001
        print(f"    (spot lookup failed: {type(e).__name__}: {e})")
        return None


def pick_instruments(tok):
    """-> (index_key, fut_key, [option keys], label map). Nearest expiry, the
    strikes either side of spot."""
    print("\n[a] resolving instruments")
    with urllib.request.urlopen(INSTRUMENTS_URL, timeout=90) as r:
        rows = json.loads(gzip.GzipFile(fileobj=io.BytesIO(r.read())).read().decode())

    def nifty(kinds):
        return [x for x in rows
                if x.get("segment") == "NSE_FO"
                and (x.get("name") or "").upper() == "NIFTY"
                and (x.get("instrument_type") or "").upper() in kinds]

    futs = sorted(nifty(("FUT", "FUTIDX")), key=lambda x: x.get("expiry") or 0)
    if not futs:
        sys.exit("    no NIFTY futures in the dump — schema changed")
    fut_key = futs[0]["instrument_key"]
    idx_key = next((x["instrument_key"] for x in rows
                    if (x.get("trading_symbol") or "") in ("Nifty 50", "NIFTY 50")
                    and x.get("segment") == "NSE_INDEX"), "NSE_INDEX|Nifty 50")

    opts = nifty(("CE", "PE"))
    now_ms = datetime.now().timestamp() * 1000
    exps = sorted({x["expiry"] for x in opts if (x.get("expiry") or 0) >= now_ms})
    if not exps:
        sys.exit("    no live option expiries")
    exp = exps[0]
    when = datetime.fromtimestamp(exp / 1000).strftime("%Y-%m-%d %A")
    near = [x for x in opts if x["expiry"] == exp]

    spot = _spot(tok, fut_key) or 0.0
    strikes = sorted({x["strike_price"] for x in near},
                     key=lambda s: abs(s - spot))[:STRIKES_EACH_SIDE * 2 + 1]
    chosen = [x for x in near if x["strike_price"] in strikes]
    chosen.sort(key=lambda x: (x["strike_price"], x["instrument_type"]))

    print(f"    spot (fut last): {spot}")
    print(f"    nearest expiry : {when}")
    print(f"    strikes        : {sorted(strikes)}")
    print(f"    option keys    : {len(chosen)}")
    label = {x["instrument_key"]: x.get("trading_symbol") for x in chosen}
    label[idx_key] = "NIFTY 50 (index)"
    label[fut_key] = futs[0].get("trading_symbol")
    return idx_key, fut_key, [x["instrument_key"] for x in chosen], label


def _sub(keys, mode):
    return json.dumps({"guid": str(uuid.uuid4()), "method": "sub",
                       "data": {"mode": mode, "instrumentKeys": keys}}).encode()


# --------------------------------------------------------------------------

def listen(tok, idx_key, fut_key, opt_keys, label):
    print(f"\n[b] connecting  {WS_URL}")
    try:
        ws = websocket.create_connection(
            WS_URL, timeout=10,
            header=[f"Authorization: Bearer {tok}", f"User-Agent: {UA}"])
    except Exception as e:                       # noqa: BLE001
        print(f"    FAIL — {type(e).__name__}: {e}")
        print("    A 401 here means the Analytics Token does NOT cover streaming,")
        print("    and Upstox cannot drive the chain. Anything else is a transport")
        print("    problem, not an answer.")
        return
    print("    OK — socket open, so the token is accepted for streaming")

    ws.send_binary(_sub(opt_keys, "option_greeks"))
    ws.send_binary(_sub([idx_key, fut_key], "full"))
    print(f"    subscribed: {len(opt_keys)} options (option_greeks), "
          f"index + future (full)")

    print(f"\n[c] listening {LISTEN_SECONDS}s")
    seen, kinds, msgs, deadline = {}, set(), 0, time.time() + LISTEN_SECONDS
    ws.settimeout(5)
    while time.time() < deadline:
        try:
            raw = ws.recv()
        except websocket.WebSocketTimeoutException:
            continue
        except Exception as e:                   # noqa: BLE001
            print(f"    socket ended: {type(e).__name__}: {e}")
            break
        if not isinstance(raw, (bytes, bytearray)) or not raw:
            continue
        msgs += 1
        try:
            r = _dec(raw, FEED_RESPONSE)
        except Exception as e:                   # noqa: BLE001
            print(f"    decode failed on message {msgs}: {type(e).__name__}: {e}")
            continue
        kinds.add(TYPE_NAME.get(r.get("type", 0), r.get("type")))
        if r.get("marketInfo"):
            st = {k: STATUS_NAME.get(v, v)
                  for k, v in (r["marketInfo"].get("segmentStatus") or {}).items()}
            for seg in ("NSE_FO", "NSE_EQ", "NSE_INDEX"):
                if seg in st:
                    print(f"    market status {seg}: {st[seg]}")
        for key, feed in (r.get("feeds") or {}).items():
            seen[key] = feed
    try:
        ws.close()
    except Exception:                            # noqa: BLE001
        pass

    report(seen, kinds, msgs, label, opt_keys, idx_key)


def report(seen, kinds, msgs, label, opt_keys, idx_key):
    print(f"\n[d] {msgs} messages, {len(seen)} instruments, types {sorted(kinds)}")
    if not seen:
        print("    no feeds arrived. Either the market is closed, or the sub")
        print("    message was rejected. Socket-open-but-silent is the signature")
        print("    of a text-framed subscribe; this probe sends binary.")
        return

    with_iv = 0
    for key in opt_keys:
        feed = seen.get(key)
        if not feed:
            continue
        g = feed.get("firstLevelWithGreeks") or {}
        if not g:
            continue
        iv, oi = g.get("iv"), g.get("oi")
        gk = g.get("optionGreeks") or {}
        ltp = (g.get("ltpc") or {}).get("ltp")
        if iv:
            with_iv += 1
        print(f"    {label.get(key, key):<24} ltp {ltp!s:>8}  iv {iv!s:>8}  "
              f"oi {oi!s:>12}  delta {gk.get('delta')!s:>8}  "
              f"gamma {gk.get('gamma')!s:>10}  theta {gk.get('theta')!s:>9}")

    idx = (seen.get(idx_key) or {}).get("fullFeed", {}).get("indexFF") or {}
    if idx:
        ivals = [o.get("interval") for o in (idx.get("marketOHLC") or {}).get("ohlc", [])]
        print(f"    {label.get(idx_key, idx_key):<24} "
              f"ltp {(idx.get('ltpc') or {}).get('ltp')}  ohlc intervals {ivals}")

    print()
    print(f"    strikes carrying a non-zero IV: {with_iv}/{len(opt_keys)}")
    print("    VERDICT:", "Upstox CAN drive the GEX stack — iv and oi arrive per "
          "strike, and the greeks come free." if with_iv else
          "IV absent or zero on every strike. Streaming does not close the gap.")


def main():
    tok = _tok()
    print("Upstox WEBSOCKET probe — read-only. The token is never printed.")
    print(f"now: {datetime.now():%Y-%m-%d %H:%M:%S} local")
    idx_key, fut_key, opt_keys, label = pick_instruments(tok)
    listen(tok, idx_key, fut_key, opt_keys, label)


if __name__ == "__main__":
    main()
