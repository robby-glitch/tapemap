"""onesided.py -- THE ONE-SIDED METER, the day type from vote consistency (research-findings §1o).

THE BINDING TEXT is docs/setup-review/ONESIDED-PREREG.md (sha256 60ba8f8f...2f14, anchored in §1o). Every number is
that file's; none is to be tuned. Mary, 22 Oct: "in chop days the data is often mixed ... and keep getting our stoplosses
trigged". DISPLAY ONLY: gates nothing; a COUNT, never a probability, no hit rate. Pure except `log` (the daily row).
Causal: a vote at a close reads only bars closed and chain rows recorded by then. [I]

VOTES per closed 5-min bar (decode's bars5 = confluence_log.push_bars: NIFTY GoCharting's, Upstox's where GC lacks the
slot; BANKNIFTY / SENSEX Upstox's), each 1 (▲) / -1 (▼) / 0 (·) or None (?, the data is missing -- never a ·):
  delta      the bar's delta / its volume >= +0.05 / <= -0.05
  cvd        CVD now minus 3 bars ago (the 3 bars' delta) / those 3 bars' volume, the same; all 3 bars present
  vwap       the close beyond +/-0.02% of the session VWAP (faded.vwaps, market.js vwapSeries)
  writers    the PE lead (faded.leads: read.writers' nine strikes, aaj likha) >= +15 / <= -15
  writers15  the PE lead's change over the 15 min >= +10 / <= -10 on ONE strike set (lead15: gap A24)
  fut_oi     |futures OI change over the 15 min| >= 0.10%: price up (fresh longs / covering) ▲, price down ▼
  peers      both other indices on the same side of their VWAP (the vwap vote's rule)
A bar is ▲ / ▼ when >= 5 votes agree; · when neither side could reach 5 even with its ? votes; ? when one could.
`thin` (N6, display only): closed bars under 20 lots, where one lot moves the delta share past the 0.05 threshold --
SENSEX's futures (median 15 lots a 5-min bar on 22 Oct); `lots_med` their median. The votes never read it.

DAY TYPE over the closed bars (live at every close):
  TREND d  one-sided bars >= 10, >= 80% of them d, flips <= 1, VWAP crosses <= 2
  PIN      range < 0.5% of the open, and VWAP crosses >= 4
  CHOP     VWAP crosses >= 4, or flips >= 3
  MIXED    anything else
flips = changes of direction between consecutive one-sided bars; a VWAP cross = a close on the other side (the vwap
vote) from the last close that was not ·.
"""
from __future__ import annotations

import bisect
import json
import os
import threading
import time

import faded
import fronts
import hold2
import read

REV = "onesided-1 (ONESIDED-PREREG 60ba8f8f)"
SHARE = 0.05                      # delta and CVD 15m: the share of volume
VW_BAND = 0.0002                  # VWAP side: beyond +/-0.02%
LEAD_IN, LEAD_MOVE = 15, 10       # writers: the PE lead; writers 15m: its change
OI_PCT = 0.10                     # futures OI x price: |ΔOI| over 15 min, %
AGREE = 5                         # of 7 votes
TREND_N, TREND_DOM, TREND_FLIPS, TREND_X = 10, 0.80, 1, 2
PIN_RANGE, CROSS_MIN, FLIPS_MIN = 0.5, 4, 3
NEAR_SD = 0.5                     # the realised shape: the close within 0.5 sigma of VWAP
THIN_LOTS = 1 / SHARE             # N6 (display only): under 20 lots one lot moves a bar's delta share past +/-0.05
AT_1130 = 11 * 3600 + 30 * 60     # the judging clock (prereg, Judging)
KEYS = ("delta", "cvd", "vwap", "writers", "writers15", "fut_oi", "peers")
CH = {1: "▲", -1: "▼", 0: "·", None: "?"}
PATH = os.path.join("data", "onesided", "onesided_log.jsonl")


def _th(x, lim):
    return None if x is None else 1 if x >= lim else -1 if x <= -lim else 0


def _side(c, vw):
    if c is None or vw is None:
        return None
    return 1 if c > vw * (1 + VW_BAND) else -1 if c < vw * (1 - VW_BAND) else 0


def sides(bars5):
    """{bar s: the vwap vote} over the session's bars."""
    return {b["s"]: _side(b.get("c"), v) for b, v in zip(bars5, faded.vwaps(bars5))}


# ---- A24: the lead's 15-min change on ONE strike set ---------------------------------------------------------------

def lead15(X, c):
    """The PE lead's change over the 15 min to close c (minute), on ONE strike set: read.writers' nine at the last chain
    row before c - 15, re-summed (aaj likha) at the last row before c. "shifted": the nine re-centred meanwhile, so a
    plain now-minus-then would mix two strike sets (the SENSEX 13:00 jump, 22 Oct). None when either row is missing or
    stale (faded.leads' rule), or a side has written nothing."""
    t = (X or {}).get("t") or []

    def row(sec):
        i = bisect.bisect_left(t, sec) - 1
        return i if i >= 0 and sec - t[i] <= fronts.STALE_MIN * 60 else None
    i0, i1 = row((c - 15) * 60), row(c * 60)
    if i0 is None or i1 is None:
        return None
    w0, w1 = read.writers(X, i0), read.writers(X, i1)
    if w0.get("ce") is None or w1.get("ce") is None:
        return None
    pos = {k: j for j, k in enumerate(X["ks"])}

    def add(s):
        return sum(v for v in (read._add(X, s, i1, pos[k]) for k in w0["ks"] if k in pos) if v is not None)
    ce, pe = add("ce"), add("pe")
    t0, t1 = abs(w0["ce"]) + abs(w0["pe"]), abs(ce) + abs(pe)
    if not t0 or not t1:
        return None
    a, b = 100.0 * (w0["pe"] - w0["ce"]) / t0, 100.0 * (pe - ce) / t1
    return {"a15": a, "now": b, "chg": b - a, "shifted": w1["ks"] != w0["ks"]}


# ---- the votes and the day type ---------------------------------------------------------------------------------------

def votes(bars5, l5, l15, peer_sides):
    """[{key: vote}] per bar. l5 = faded.leads' {close minute: {"pe"}}, l15 = {close minute: lead15(...)},
    peer_sides = [sides(peer bars5)] for the other indices."""
    by = {b["s"]: b for b in bars5}
    vws = faded.vwaps(bars5)
    out = []
    for b, vw in zip(bars5, vws):
        c, v = faded.close(b), {}
        v["delta"] = _th(b["delta"] / b["vol"], SHARE) if b.get("vol") and b.get("delta") is not None else None
        w = [by.get(b["s"] - 600), by.get(b["s"] - 300), b]
        vol3 = sum(x.get("vol") or 0 for x in w) if None not in w else 0
        v["cvd"] = _th(sum(x["delta"] for x in w) / vol3, SHARE) if vol3 else None
        v["vwap"] = _side(b.get("c"), vw)
        v["writers"] = _th((l5.get(c) or {}).get("pe"), LEAD_IN)
        f = l15.get(c)
        v["writers15"] = None if f is None else _th(f["chg"], LEAD_MOVE)
        a = by.get(b["s"] - 900)
        if a and a.get("oi") and b.get("oi") and a.get("c") is not None and b.get("c") is not None:
            doi, dp = (b["oi"] - a["oi"]) / a["oi"] * 100, b["c"] - a["c"]
            v["fut_oi"] = 0 if abs(doi) < OI_PCT else (dp > 0) - (dp < 0)
        else:
            v["fut_oi"] = None
        ps = [p.get(b["s"]) for p in peer_sides]
        v["peers"] = (None if len(ps) != 2 else 0 if 0 in ps else None if None in ps else ps[0] if ps[0] == ps[1] else 0)
        out.append(v)
    return out


def state(v):
    """1 / -1 one-sided (>= 5 agree), 0 mixed (no side can reach 5 even with its ?), None (?: the missing could)."""
    vs = list(v.values())
    up, dn, unk = vs.count(1), vs.count(-1), sum(1 for x in vs if x is None)
    return 1 if up >= AGREE else -1 if dn >= AGREE else None if max(up, dn) + unk >= AGREE else 0


def kind(up, down, flips, crosses, range_pct):
    """The day type from the counts (the prereg's order: TREND, PIN, CHOP, MIXED)."""
    n = up + down
    if n >= TREND_N and max(up, down) >= TREND_DOM * n and flips <= TREND_FLIPS and crosses <= TREND_X:
        return "TREND " + ("▲" if up > down else "▼")
    if range_pct is not None and range_pct < PIN_RANGE and crosses >= CROSS_MIN:
        return "PIN"
    if crosses >= CROSS_MIN or flips >= FLIPS_MIN:
        return "CHOP"
    return "MIXED"


def _crosses(ss):
    n, last = 0, 0
    for s in ss:
        if s:
            n += bool(last and s != last)
            last = s
    return n


def blank(why):
    return {"type": None, "why": why, "up": None, "down": None, "mix": None, "unk": None, "dom": None, "flips": None,
            "crosses": None, "range_pct": None, "last": None, "strip": None, "thin": None, "lots_med": None, "tag": "I"}


def meter(bars5, l5, l15, peers=(), upto=None):
    """The block's `onesided` (decode.decode): the type and its numbers over the bars closed by `upto` (sec; None = all
    given). `peers` = the other indices' bars5. type None with `why` when it cannot be read."""
    cut = lambda bs: [b for b in bs or () if upto is None or b["s"] + faded.BAR * 60 <= upto]    # noqa: E731
    bars5 = cut(bars5)
    why = faded.opened(bars5)
    if why:
        return blank(why)
    st = [state(v) for v in votes(bars5, l5 or {}, l15 or {}, [sides(cut(p)) for p in peers])]
    one = [s for s in st if s in (1, -1)]
    up, down = one.count(1), one.count(-1)
    flips = sum(1 for a, b in zip(one, one[1:]) if a != b)
    crosses = _crosses(sides(bars5).values())
    hs, ls = [b["h"] for b in bars5 if b.get("h") is not None], [b["l"] for b in bars5 if b.get("l") is not None]
    o = bars5[0].get("o")
    rng = 100 * (max(hs) - min(ls)) / o if hs and ls and o else None
    vols = sorted(b["vol"] for b in bars5 if isinstance(b.get("vol"), (int, float)))
    return {"type": kind(up, down, flips, crosses, rng), "why": None, "up": up, "down": down, "mix": st.count(0),
            "unk": sum(1 for s in st if s is None), "dom": round(100 * max(up, down) / (up + down)) if one else None,
            "flips": flips, "crosses": crosses, "range_pct": None if rng is None else round(rng, 2),
            "last": faded.hm(faded.close(bars5[-1])), "strip": "".join(CH[s] for s in st),
            # N6, display only (the votes are unchanged): bars so thin one lot can swing the delta vote, and the median
            "thin": sum(1 for v in vols if v < THIN_LOTS), "lots_med": vols[len(vols) // 2] if vols else None, "tag": "I"}


# ---- the daily row (prereg, Judging) --------------------------------------------------------------------------------

def shape(bars5):
    """The day's realised shape: range in sigma, VWAP crosses, the close within 0.5 sigma of VWAP. sigma = the 5-min
    vwapSeries sigma at the last close (hold2.sigma_at, the stack's U unit)."""
    if not bars5:
        return None
    sg, vw, c = hold2.sigma_at(bars5, faded.close(bars5[-1])), faded.vwaps(bars5)[-1], bars5[-1].get("c")
    hs, ls = [b["h"] for b in bars5 if b.get("h") is not None], [b["l"] for b in bars5 if b.get("l") is not None]
    at = [b for b in bars5 if b["s"] + faded.BAR * 60 <= AT_1130]
    return {"sigma": None if sg is None else round(sg, 2), "sigma_src": "hold2.sigma_at (5-min vwapSeries sigma)",
            "range_sd": round((max(hs) - min(ls)) / sg, 2) if sg and hs and ls else None,
            "crosses": _crosses(sides(bars5).values()), "open": bars5[0].get("o"), "c_1130": at[-1]["c"] if at else None,
            "close": c, "vwap": None if vw is None else round(vw, 2),
            "near_vwap": None if not sg or vw is None or c is None else abs(c - vw) <= NEAR_SD * sg}


def row(day, idx, bars5, l5, l15, peers=()):
    """One index's row: the final type and numbers, the 11:30 type (the judging clock, cut causally) and the shape."""
    return dict(meter(bars5, l5, l15, peers), day=day, index=idx, at_1130=meter(bars5, l5, l15, peers, AT_1130),
                shape=shape(bars5), rev=REV, at=time.time())


_seen = {}
_lock = threading.Lock()


def log(rows, path=None):
    """Append each (day, index) row not yet on disk; a restart re-reads the keys, so a day is never written twice.
    Fail-soft (trigger_log's rule): any error is swallowed and 0 returned. Returns rows written."""
    path = path or PATH
    try:
        with _lock:
            if path not in _seen:
                keys = set()
                try:
                    with open(path, encoding="utf-8") as f:
                        for line in f:
                            try:
                                r = json.loads(line)
                            except ValueError:
                                continue
                            if isinstance(r, dict):
                                keys.add((r.get("day"), r.get("index")))
                except FileNotFoundError:
                    pass
                _seen[path] = keys
            seen = _seen[path]
            out = [r for r in rows if (r["day"], r["index"]) not in seen]
            if not out:
                return 0
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in out))
            seen.update((r["day"], r["index"]) for r in out)
            return len(out)
    except Exception:
        return 0
