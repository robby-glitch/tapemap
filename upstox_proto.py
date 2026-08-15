"""Upstox's v3 market-data protobuf, decoded without protoc.

WHY BY HAND. The feed is 14 small messages and the schema is published and
stable (`MarketDataFeed.proto` v3). Generating bindings would put a protoc
step, a build artifact and a `protobuf` runtime pin into a repo that currently
needs none of them, to save about eighty lines. The wire format is simpler
than the toolchain: a tag, a wire type, and a value.

Unknown fields are SKIPPED rather than raising, so Upstox adding a field
cannot take the tape down mid-session -- the decoder degrades to ignoring what
it does not know, which is exactly protobuf's own compatibility promise.

Pure: no socket, no token, no clock. `upstox_feed` owns the connection.

FIELD NUMBERS ARE THE CONTRACT. Renaming a key below is free; changing a
number silently decodes the wrong field into the right name, which downstream
reads as a real value. The tables mirror the .proto exactly.
"""

import struct

# The proto's own enums, spelled out so a log line says NORMAL_OPEN rather
# than 2.
TYPE_NAME = {0: "initial_feed", 1: "live_feed", 2: "market_info"}
STATUS_NAME = {0: "PRE_OPEN_START", 1: "PRE_OPEN_END", 2: "NORMAL_OPEN",
               3: "NORMAL_CLOSE", 4: "CLOSING_START", 5: "CLOSING_END"}


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
MARKET_FULL = {1: _f("ltpc", "msg", LTPC),
               2: _f("marketLevel", "msg", MARKET_LEVEL),
               3: _f("optionGreeks", "msg", GREEKS),
               4: _f("marketOHLC", "msg", MARKET_OHLC), 5: _f("atp", "double"),
               6: _f("vtt", "int64"), 7: _f("oi", "double"),
               8: _f("iv", "double"), 9: _f("tbq", "double"),
               10: _f("tsq", "double")}
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
                 3: _f("currentTs", "int64"),
                 4: _f("marketInfo", "msg", MARKET_INFO)}


def _varint(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, i
        s += 7


def decode(buf, schema):
    """Walk the wire format against `schema`. Raises only on a wire type the
    schema cannot contain, which means the bytes are not this message."""
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
            continue                             # forward compatible
        name, kind, sub, rep = f
        if kind == "string":
            v = v.decode("utf-8", "replace")
        elif kind == "msg":
            v = decode(v, sub)
        elif kind == "map":
            ent = decode(v, sub)
            out.setdefault(name, {})[ent.get("key")] = ent.get("value")
            continue
        if rep:
            out.setdefault(name, []).append(v)
        else:
            out[name] = v
    return out


def feed_response(buf):
    """One socket frame -> the decoded FeedResponse."""
    return decode(buf, FEED_RESPONSE)


def segment_status(resp):
    """{'NSE_FO': 'NORMAL_OPEN', ...} out of a market_info frame, or {}."""
    info = resp.get("marketInfo") or {}
    return {k: STATUS_NAME.get(v, v)
            for k, v in (info.get("segmentStatus") or {}).items()}
