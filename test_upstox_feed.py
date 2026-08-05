"""The decoder is tested against BYTES, and the feed against a fake socket.

Asserting a decoder against a dict someone typed proves only that the typist
and the reader agree. So these tests encode real protobuf wire format -- tag,
wire type, value -- and decode it back. `_uv`/`_dbl`/`_bytes` below are a
throwaway encoder that exists only here; the app never encodes anything.

The feed's socket is injected, so nothing here needs a token, a network or
market hours.
"""

import struct
import time

import upstox_feed
import upstox_proto


# --------------------------------------------------------------------------
# a minimal protobuf encoder, for tests only
# --------------------------------------------------------------------------

def _uv(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _tag(field, wire):
    return _uv((field << 3) | wire)


def _dbl(field, v):
    return _tag(field, 1) + struct.pack("<d", v)


def _int(field, v):
    return _tag(field, 0) + _uv(v)


def _bytes(field, b):
    return _tag(field, 2) + _uv(len(b)) + b


def _str(field, s):
    return _bytes(field, s.encode())


def greek_feed(ltp, oi, iv, delta, gamma):
    """FirstLevelWithGreeks, as `option_greeks` mode sends it."""
    ltpc = _dbl(1, ltp) + _int(2, 1) + _int(3, 50) + _dbl(4, ltp)
    depth = _int(1, 75) + _dbl(2, ltp - 0.5) + _int(3, 75) + _dbl(4, ltp + 0.5)
    greeks = (_dbl(1, delta) + _dbl(2, -11.37) + _dbl(3, gamma)
              + _dbl(4, 5.0) + _dbl(5, 0.1))
    return (_bytes(1, ltpc) + _bytes(2, depth) + _bytes(3, greeks)
            + _int(4, 123456) + _dbl(5, oi) + _dbl(6, iv))


def feed_msg(inner):
    return _bytes(3, inner) + _int(4, 2)          # firstLevelWithGreeks, mode 2


def response(entries, kind=1, segments=None):
    """A FeedResponse carrying {key: Feed} and optionally a market_info map."""
    out = _int(1, kind)
    for key, inner in entries.items():
        out += _bytes(2, _str(1, key) + _bytes(2, feed_msg(inner)))
    out += _int(3, 1785900000)
    if segments:
        info = b""
        for seg, code in segments.items():
            info += _bytes(1, _str(1, seg) + _int(2, code))
        out += _bytes(4, info)
    return out


CE = "NSE_FO|CE24700"
PE = "NSE_FO|PE24700"


# --------------------------------------------------------------------------
# the decoder
# --------------------------------------------------------------------------

def test_real_bytes_decode_to_the_measured_values():
    raw = response({CE: greek_feed(114.10, 8916050, 0.1112, 0.4359, 0.0011)})
    resp = upstox_proto.feed_response(raw)
    assert upstox_proto.TYPE_NAME[resp["type"]] == "live_feed"
    g = resp["feeds"][CE]["firstLevelWithGreeks"]
    assert g["ltpc"]["ltp"] == 114.10
    assert g["oi"] == 8916050
    assert g["iv"] == 0.1112
    assert g["optionGreeks"]["delta"] == 0.4359
    assert g["optionGreeks"]["gamma"] == 0.0011
    assert g["firstDepth"]["bidP"] == 113.60
    assert resp["feeds"][CE]["requestMode"] == 2


def test_two_instruments_in_one_frame():
    raw = response({CE: greek_feed(114.10, 8916050, 0.1112, 0.4359, 0.0011),
                    PE: greek_feed(164.50, 3740620, 0.1033, -0.5694, 0.0012)})
    feeds = upstox_proto.feed_response(raw)["feeds"]
    assert set(feeds) == {CE, PE}


def test_an_unknown_field_is_skipped_not_fatal():
    """Upstox adding a field must not take the tape down mid-session."""
    raw = response({CE: greek_feed(114.10, 8916050, 0.1112, 0.4359, 0.0011)})
    raw += _bytes(99, b"something new") + _int(98, 7)
    resp = upstox_proto.feed_response(raw)
    assert resp["feeds"][CE]["firstLevelWithGreeks"]["oi"] == 8916050


def test_segment_status_reads_as_names():
    raw = response({}, kind=2, segments={"NSE_FO": 2, "NSE_EQ": 3})
    assert upstox_proto.segment_status(upstox_proto.feed_response(raw)) == {
        "NSE_FO": "NORMAL_OPEN", "NSE_EQ": "NORMAL_CLOSE"}


def test_segment_status_of_a_plain_feed_is_empty():
    raw = response({CE: greek_feed(1.0, 1, 0.1, 0.1, 0.001)})
    assert upstox_proto.segment_status(upstox_proto.feed_response(raw)) == {}


# --------------------------------------------------------------------------
# the mailbox
# --------------------------------------------------------------------------

def _feed(**kw):
    return upstox_feed.UpstoxFeed([CE, PE], token="unused", **kw)


def test_a_frame_lands_in_the_mailbox():
    f = _feed()
    f._absorb(response({CE: greek_feed(114.10, 8916050, 0.1112, 0.4359, 0.0011)}))
    assert f.frames == 1
    assert list(f.snapshot()) == [CE]
    assert f.age() is not None


def test_quiet_instruments_are_not_blanked():
    """A frame carries only what ticked. Replacing instead of merging would
    empty every quiet strike -- downstream, a chain full of holes."""
    f = _feed()
    f._absorb(response({CE: greek_feed(114.10, 8916050, 0.1112, 0.4359, 0.0011)}))
    f._absorb(response({PE: greek_feed(164.50, 3740620, 0.1033, -0.5694, 0.0012)}))
    assert set(f.snapshot()) == {CE, PE}


def test_a_newer_tick_replaces_the_older_one_for_that_key():
    f = _feed()
    f._absorb(response({CE: greek_feed(114.10, 8916050, 0.1112, 0.4359, 0.0011)}))
    f._absorb(response({CE: greek_feed(120.00, 8916050, 0.1112, 0.4359, 0.0011)}))
    ltp = f.snapshot()[CE]["firstLevelWithGreeks"]["ltpc"]["ltp"]
    assert ltp == 120.00
    assert f.frames == 2


def test_a_corrupt_frame_is_recorded_not_fatal():
    f = _feed()
    f._absorb(b"\xff\xff\xff\xff")
    assert f.frames == 0
    assert f.last_error and "decode" in f.last_error
    assert f.snapshot() == {}


def test_the_snapshot_is_a_copy():
    f = _feed()
    f._absorb(response({CE: greek_feed(1.0, 1, 0.1, 0.1, 0.001)}))
    f.snapshot().clear()
    assert list(f.snapshot()) == [CE]


# --------------------------------------------------------------------------
# connected is not receiving -- the 2026-07-27 frozen tape
# --------------------------------------------------------------------------

def test_connected_but_silent_is_not_healthy():
    """The outage this check exists for: the socket was open all session and
    the tape never moved."""
    f = _feed()
    f.connected = True
    assert f.age() is None
    assert f.healthy() is False


def test_health_expires_with_the_last_frame_not_the_connection():
    f = _feed()
    f.connected = True
    f._absorb(response({CE: greek_feed(1.0, 1, 0.1, 0.1, 0.001)}))
    assert f.healthy() is True
    f.last_frame_at = time.monotonic() - (upstox_feed.STALE_AFTER + 1)
    assert f.healthy() is False
    assert f.age() > upstox_feed.STALE_AFTER


def test_a_disconnected_feed_is_never_healthy():
    f = _feed()
    f._absorb(response({CE: greek_feed(1.0, 1, 0.1, 0.1, 0.001)}))
    f.connected = False
    assert f.healthy() is False


def test_status_carries_no_token():
    f = upstox_feed.UpstoxFeed([CE], token="SECRET-TOKEN-VALUE")
    assert "SECRET-TOKEN-VALUE" not in repr(f.status())


# --------------------------------------------------------------------------
# the subscribe frame
# --------------------------------------------------------------------------

def test_the_subscribe_frame_is_binary_and_shaped_right():
    import json
    body = json.loads(upstox_feed.sub_frame([CE, PE]).decode())
    assert body["method"] == "sub"
    assert body["data"]["mode"] == "full"         # full, for atp
    assert body["data"]["instrumentKeys"] == [CE, PE]
    assert body["guid"]


# --------------------------------------------------------------------------
# the run loop, against a fake socket
# --------------------------------------------------------------------------

class FakeWS:
    def __init__(self, frames, feed=None):
        self.frames, self.feed = list(frames), feed
        self.sent, self.closed = [], False

    def send_binary(self, b):
        self.sent.append(b)

    def recv(self):
        if self.frames:
            return self.frames.pop(0)
        self.feed.stop()                          # end the test deterministically
        return b""

    def close(self):
        self.closed = True


def test_the_loop_subscribes_then_fills_the_mailbox():
    frames = [response({CE: greek_feed(114.10, 8916050, 0.1112, 0.4359, 0.0011)}),
              response({PE: greek_feed(164.50, 3740620, 0.1033, -0.5694, 0.0012)})]
    holder = {}

    def connect():
        holder["ws"] = FakeWS(frames, holder["feed"])
        return holder["ws"]

    f = upstox_feed.UpstoxFeed([CE, PE], token="unused", connect=connect)
    holder["feed"] = f
    f.run()                                       # synchronous, not start()
    assert len(holder["ws"].sent) == 1            # the subscribe
    assert set(f.snapshot()) == {CE, PE}
    assert holder["ws"].closed is True
    assert f.connected is False


def test_a_refused_connection_is_recorded_and_does_not_kill_the_thread():
    calls = {"n": 0}

    def connect():
        calls["n"] += 1
        f.stop()          # inside the attempt: run() checks _stop at the TOP,
        raise ConnectionError("401 Unauthorized")   # so setting it earlier
        #                     would skip the loop body entirely and prove
        #                     nothing. Stopping here lets exactly one attempt
        #                     run, then breaks before the backoff wait.

    f = upstox_feed.UpstoxFeed([CE], token="unused", connect=connect)
    f.run()
    assert calls["n"] == 1
    assert "401" in f.last_error
    assert f.healthy() is False
