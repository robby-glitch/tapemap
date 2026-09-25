"""trendbox.py -- BOARD rev 3's floating trend box, on the INDEX's own candles.

THE SPEC is `docs/mockups/board-chess-rev3-2026-09-24-notes.md` §6.6; the
mockup's generator (g3.py) is the reference, ported rule for rule. [I]
throughout: display only, it gates nothing.

ROWS 1m 3m 5m 15m 1h 4h D, each on the last N CLOSED bars -- the forming bar is
never used. Intraday bars are aligned to 09:15 and run across sessions, so the
overnight gap sits inside the window; 1h is 09:15-10:14 ... 15:15-15:29, 4h is
09:15-13:14 and 13:15-15:29.
  POS    (price now - N-bar mean) / N-bar sigma: up at >= +1, down at <= -1
  SWINGS the last two pivot highs and lows (a pivot beats PIV bars either
         side): HH·HL up, LH·LL down, anything else mixed
  SLOPE  the least-squares rise across the N closes / sigma: up >= +1, down <= -1
  A row is UP when >= 2 of the 3 say up and none says down (DOWN mirrored),
  else RANGE; with fewer than N bars it is forming.
REGIME  TREND when 5m, 15m and 1h all point one way AND the OI read agrees;
        PIN / CHOP when two of those rows read RANGE and both sides' nearer
        fronts write; otherwise NOT AGREED, with both halves printed.
STRONG  BULLS at >= 4 UP rows and <= 1 DOWN, BEARS mirrored, else NEITHER.

WHY THE INDEX AND NOT FUTURES VWAP: the index prints no volume, and the future
rolls and expires (the SENSEX near future expired 2026-09-24). The N-bar mean
+-sigma is the same band shape, with one definition on all three indices.

Pure computation plus ONE declared I/O function, `fetch_daily` -- the levels.py
division. REST is exact, so a 13:00 start reads the same as a 09:15 one.
"""
from __future__ import annotations

import statistics

N = 20              # bars in every window
PIV = 2             # a swing high/low beats this many bars either side
TFS = ("1m", "3m", "5m", "15m", "1h", "4h", "D")
OPEN, CLOSE = "09:15", "15:30"


def _m(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[3:5])


def candles(c):
    """Upstox candles (newest first, ISO stamps) -> [(day, HH:MM, o, h, l, c)], oldest first."""
    out = []
    for x in reversed(c or []):
        try:
            out.append((str(x[0])[:10], str(x[0])[11:16], float(x[1]), float(x[2]), float(x[3]), float(x[4])))
        except (TypeError, ValueError, IndexError):
            continue
    return out


def _fold(rows, key):
    """Consecutive rows with the same key -> (day, start, end, o, h, l, c)."""
    out, cur = [], None
    for d, t, o, h, l, c in rows:
        k = key(d, t)
        if cur and cur[0] == k:
            b = cur[1]
            b[4], b[5], b[6], b[2] = max(b[4], h), min(b[5], l), c, t
        else:
            if cur:
                out.append(tuple(cur[1]))
            cur = (k, [d, t, t, o, h, l, c])
    if cur:
        out.append(tuple(cur[1]))
    return out


def agg(rows, width):
    """1-min rows -> `width`-minute bars aligned to 09:15 per session, in session only."""
    return _fold([r for r in rows if OPEN <= r[1] < CLOSE], lambda d, t: (d, (_m(t) - _m(OPEN)) // width))


def one_h(rows):
    return _fold(rows, lambda d, t: (d, (_m(t) - _m(OPEN)) // 60))


def four_h(rows):
    return _fold(rows, lambda d, t: (d, 0 if t < "13:15" else 1))


def slot_end(start, width):
    a = _m(OPEN) + (_m(start) - _m(OPEN)) // width * width
    return min(a + width - 1, _m("15:29"))


def trow(bars, px):
    """One timeframe: POS, SWINGS, SLOPE and the row's verdict (+1 / -1 / 0),
    or v None (forming) with fewer than N closed bars."""
    if len(bars) < N:
        return {"v": None, "n": len(bars), "word": "forming"}
    w = bars[-N:]
    cl = [b[6] for b in w]
    mu, sd = statistics.fmean(cl), statistics.pstdev(cl)
    z = (px - mu) / sd if sd else 0.0
    pos = 1 if z >= 1 else -1 if z <= -1 else 0
    xb = (N - 1) / 2
    slope = sum((i - xb) * (c - mu) for i, c in enumerate(cl)) / sum((i - xb) ** 2 for i in range(N))
    rise = slope * (N - 1) / sd if sd else 0.0
    slp = 1 if rise >= 1 else -1 if rise <= -1 else 0
    hs = [i for i in range(PIV, N - PIV) if all(w[i][4] > w[x][4] for x in range(i - PIV, i))
          and all(w[i][4] > w[x][4] for x in range(i + 1, i + 1 + PIV))]
    ls = [i for i in range(PIV, N - PIV) if all(w[i][5] < w[x][5] for x in range(i - PIV, i))
          and all(w[i][5] < w[x][5] for x in range(i + 1, i + 1 + PIV))]
    if len(hs) >= 2 and len(ls) >= 2:
        h1, h2, l1, l2 = w[hs[-2]][4], w[hs[-1]][4], w[ls[-2]][5], w[ls[-1]][5]
        sw = ("HH" if h2 > h1 else "LH" if h2 < h1 else "EH") + "·" + ("HL" if l2 > l1 else "LL" if l2 < l1 else "EL")
        st = 1 if sw == "HH·HL" else -1 if sw == "LH·LL" else 0
    else:
        sw, st = "no swings", 0
    votes = (pos, st, slp)
    v = (1 if votes.count(1) >= 2 and -1 not in votes else
         -1 if votes.count(-1) >= 2 and 1 not in votes else 0)
    return {"v": v, "word": {1: "UP", -1: "DOWN", 0: "RANGE"}[v], "z": round(z, 1), "sw": sw,
            "r": round(rise, 1), "p": [pos, st, slp], "n": N, "mu": round(mu, 1), "sd": round(sd, 1)}


def rows(m1_prior, m1_today, m30, d1, day, asof):
    """The seven rows as of `asof`, a FINISHED minute of `day`. Inputs are raw
    Upstox candles: the prior session's 1-min, today's 1-min, 30-min and daily
    ranges (today's rows in those two are ignored -- today comes from the 1-min).
    None when today has no index candle at or before `asof`."""
    today = [r for r in candles(m1_today) if r[0] == day and r[1] <= asof]
    if not today:
        return None
    prior = [r for r in candles(m1_prior) if r[0] < day]
    r30 = [r for r in candles(m30) if r[0] < day]
    dd = [(r[0], r[1], r[1], r[2], r[3], r[4], r[5]) for r in candles(d1) if r[0] < day]
    px, now = today[-1][5], _m(asof)
    res = {}
    for tf, w in (("1m", 1), ("3m", 3), ("5m", 5), ("15m", 15)):
        res[tf] = trow([b for b in agg(prior + today, w) if b[0] < day or slot_end(b[1], w) <= now], px)
    res["1h"] = trow(one_h(r30) + [b for b in one_h(today) if slot_end(b[1], 60) <= now], px)
    res["4h"] = trow(four_h(r30) + [b for b in four_h(today)
                                    if (_m("13:14") if b[1] < "13:15" else _m("15:29")) <= now], px)
    res["D"] = trow(dd, px)
    return {"px": px, "at": today[-1][1], "rows": res, "d_last": dd[-1][0] if dd else None}


def strong(tr):
    """BULLS / BEARS / NEITHER off the seven rows, with the counts [up, down, range, forming]."""
    if not tr:
        return {"word": None, "n": [0, 0, 0, len(TFS)]}
    vs = [tr["rows"][k]["v"] for k in TFS]
    u, d, r, f = vs.count(1), vs.count(-1), vs.count(0), vs.count(None)
    return {"word": "BULLS" if u >= 4 and d <= 1 else "BEARS" if d >= 4 and u <= 1 else "NEITHER",
            "n": [u, d, r, f]}


def regime(tr, oi):
    """TREND / PIN-CHOP / NOT AGREED from two families that must agree: price
    (the 5m, 15m and 1h rows) and `oi` = (word, why), board.oi_read's read of
    the nearer of each side's §1d top 2."""
    if not tr:
        return {"word": None, "why": "no index candle yet — could not check"}
    mid = [tr["rows"][k]["v"] for k in ("5m", "15m", "1h")]
    if None in mid:
        price = ("FORMING", "a middle row is still forming")
    elif all(v == 1 for v in mid):
        price = ("TREND UP", "5m, 15m and 1h all UP")
    elif all(v == -1 for v in mid):
        price = ("TREND DOWN", "5m, 15m and 1h all DOWN")
    elif sum(1 for v in mid if v == 0) >= 2:
        price = ("CHOP", "two of 5m / 15m / 1h read RANGE")
    else:
        price = ("MIXED", "5m / 15m / 1h disagree")
    if price[0] == oi[0] and price[0].startswith("TREND"):
        word = price[0]
    elif price[0] == "CHOP" and oi[0] == "PIN":
        word = "PIN / CHOP"
    else:
        word = "NOT AGREED"
    return {"word": word, "price": list(price), "oi": list(oi)}


# --- the one I/O function ---------------------------------------------------

def fetch_daily(idx, day, tok=None):
    """The once-a-day REST behind the box [M]: the prior session's 1-min
    candles, ~5 weeks of 30-min and ~2 months of daily candles (completed
    sessions only). Three calls. Raises on a transport or auth failure -- the
    caller owns retry and the stated absence, as with levels.fetch_daily."""
    from datetime import datetime, timedelta

    import upstox_feed
    import upstox_instruments
    import upstox_rest

    tok = tok or upstox_feed.read_token()
    key = upstox_instruments.index_key(idx)
    d0 = datetime.strptime(day, "%Y-%m-%d")
    back = lambda n: (d0 - timedelta(days=n)).strftime("%Y-%m-%d")   # noqa: E731
    d1 = [c for c in upstox_rest.daily_range(key, tok, back(60), day, "day") if str(c[0])[:10] < day]
    prior = str(d1[0][0])[:10] if d1 else None                       # newest first
    m1p = upstox_rest.historical(key, tok, prior, "1minute") if prior else []
    m30 = [c for c in upstox_rest.daily_range(key, tok, back(35), day, "30minute") if str(c[0])[:10] < day]
    return {"day": day, "prior_day": prior, "m1_prior": m1p, "m30": m30, "d1": d1}
