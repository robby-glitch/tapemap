"""confluence.py -- THE CONFLUENCE SETUP: zone + OI + order flow, and its pass bar (research-findings §1i).

THE BINDING TEXT is docs/setup-review/CONFLUENCE-PREREG.md (sha256 d5c4937f...aa73, anchored in §1i). Every number
below is that file's, fixed by trader judgement before any outcome existed; none is to be grid-searched (§5c's rule).
Mary, 2026-10-21: "when everything matches thats when those become buy or sell zones".

    ZONE  a zone ENTRY (band_rotation.run_states at d2 / u2, exactly as live.py runs it), split by its extreme:
          POCKET did not go beyond d3 (BUY) / u3 (SELL) at the arm bar's sigma; EXHAUSTION did.
    OI    fronts.read on the chain minutes cut at the bar close (§1d's parameters). POCKET: the DEFENDING front
          (PE for BUY, CE for SELL) is BUILDING. EXHAUSTION: the ATTACKING front (CE for BUY, PE for SELL) is
          STALLED or UNWINDING. The engine's NO FADE veto is NOT part of it (a stamp where it exists).
    FLOW  the Upstox futures book, sided by rank.py's rule -- ladder.attribute through ladder.Ladder.step, the record
          rank.py ranks (ux_log). BUY: tilt(last 5 min) >= +0.10 and tilt(the 15 min before) <= 0; SELL mirrored.
          NIFTY: a GoCharting bar on the same 5 minutes tilting <= -0.10 (BUY) / >= +0.10 (SELL) is "sources
          disagree" -> FLOW not ok. Absent GoCharting is not disagreement.
    ENTRY the first 3-min bar close, trigger bar through +3 bars (<= 9 min), with OI ok and FLOW ok, the close still
          beyond the 1-sigma ring on the zone's side, the close at or before 15:00. One per zone setup.
    R     stop (POCKET: d3/u3 at entry; EXHAUSTION: extreme -/+ 0.25 sigma; risk floored at 0.5 sigma), target the
          live session VWAP on 1-min first passage (a bar touching both is stop first), else marked at 15:20.

CAUSAL BY CONSTRUCTION: every read at a bar takes `at` / `close` and looks at nothing later -- test_confluence's
no-look-ahead test cuts the inputs at the bar and gets the identical answer. Pure: stdlib + band_rotation, fronts,
ladder (all pure). No I/O, no clock. DESCRIPTIVE ONLY: no hit rate is computed here or anywhere (§4, CLAUDE.md 4).
"""
from __future__ import annotations

import bisect

import band_rotation
import fronts
import ladder

REV = "confluence-1 (CONFLUENCE-PREREG d5c4937f)"
INTERVAL = band_rotation.SCORED_INTERVAL      # 3: the zone machine's bar
POCKET, EXHAUSTION = "POCKET", "EXHAUSTION"

# ---- the pre-registered numbers (CONFLUENCE-PREREG.md). Fixed; never tuned. ------------------------------------
TILT = 0.10                 # §1 FLOW: the 5-min tilt that says aggression turned
FAST, SLOW = 5, 15          # §1 FLOW: last 5 min, and the 15 min before those 5
WINDOW_BARS = 3             # §1 ENTRY: trigger bar through 3 bars after it
WINDOW_MIN = 9              # ... (<= 9 min)
CUTOFF = 15 * 60            # §1: no entry after 15:00 (an entry is a bar CLOSE)
MARK = 15 * 60 + 20         # §2: held at most to 15:20, marked at the 15:20 close
EXH_BUF = 0.25              # §2: EXHAUSTION stop, sigma beyond the setup's extreme
MIN_RISK = 0.5              # §2: risk floor, sigma
RP_NEAR = 0.25              # §1 stamp: a reaction point within 0.25 sigma of the extreme
PASS_N, PASS_MEAN, PASS_DIFF, DAY_SHARE = 20, 0.25, 0.20, 0.40      # §4

# ---- plumbing, not a definition (named in the report's readings) -----------------------------------------------
HOLE_S = 60                 # a book arrival gap this long is a recorder hole: the next frame carries its volume
IST_MS = ladder.IST_MS


def _num(x):
    return band_rotation._num(x)


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def mod(ms):
    """epoch ms -> IST minute of day."""
    return (int(ms) + IST_MS) // 60000 % 1440


def flat(bar):
    return band_rotation._index_bar(bar) or {}


def sigma(bar):
    """The band sigma on this bar (VWAP - d1), or None."""
    vw, d1 = _num(bar.get("vwap")), _num(bar.get("d1"))
    s = None if vw is None or d1 is None else vw - d1
    return s if s and s > 0 else None


def close_of(t):
    """A 3-min bar's close, IST minute of day (the bar is labelled by its opening minute)."""
    m = band_rotation._minute(t)
    return None if m is None else m + INTERVAL


# ---- ZONE --------------------------------------------------------------------------------------------------------

def setups(bars):
    """Every zone ENTRY on the session, one per bar with trigger_log's slot rule (a BUY wins a bar both sides enter
    on), each with its kind. The machine is live.py's: run_states at d2 / u2 with OPERATOR_STOP_PTS."""
    rows = [flat(b) for b in bars or ()]
    by_i = {}
    for side, band in (("BUY", "d2"), ("SELL", "u2")):
        st = band_rotation.run_states(bars, stop_pts=band_rotation.OPERATOR_STOP_PTS, side=side, band=band)
        for s in st:
            e = s.get("entry") if isinstance(s, dict) else None
            if e is not None and e["i"] not in by_i:
                by_i[e["i"]] = _setup(rows, st, e, side)
    return [by_i[i] for i in sorted(by_i)]


def _setup(rows, st, e, side):
    buy = side == "BUY"
    ri = e["ref_i"]
    ref = rows[ri]
    # The reference bar holds the setup's extreme: a re-arm moves the reference only on a new lower low (higher
    # high), so its low IS the lowest low since the first arm. The arm bar's sigma is that bar's own d3 / u3.
    first_i = (st[ri].get("arm") or {}).get("first_i", ri)
    x, far = _num(ref.get("l" if buy else "h")), _num(ref.get("d3" if buy else "u3"))
    kind = None if x is None or far is None else (EXHAUSTION if (x < far if buy else x > far) else POCKET)
    vw, sg = _num(ref.get("vwap")), sigma(ref)
    pre = [r for r in rows[:first_i] if _num(r.get("h")) is not None and _num(r.get("l")) is not None]
    return {"i": e["i"], "t": e.get("t"), "side": side, "kind": kind, "extreme": x, "far": far,
            "ref_t": ref.get("t"), "first_t": rows[first_i].get("t"),
            "first_touch": not any((s.get("arm") or {}).get("rearm") is False for s in st[:first_i]),
            "depth": None if vw is None or not sg or x is None else round(((vw - x) if buy else (x - vw)) / sg, 2),
            "session_hl": (max(r["h"] for r in pre), min(r["l"] for r in pre)) if pre else None}


def zone_read(side, bar):
    """The close still beyond the 1-sigma ring on the zone's side."""
    c, ring = _num(bar.get("c")), _num(bar.get("d1" if side == "BUY" else "u1"))
    ok = None if c is None or ring is None else (c < ring if side == "BUY" else c > ring)
    return {"ok": ok, "c": c, "ring": ring}


# ---- OI ----------------------------------------------------------------------------------------------------------

def chain_grid(snaps, backfill=None):
    """(minutes, peaks) -- ChainState's minute grid rebuilt from the chain record, and its session-peak OI AS AT
    each minute (ChainState.peak is as-at-now, which on a replay would rank today's fronts with the future).

    `snaps` are chain_live's rows (market hours only, chain_live._warm_start's window); a minute keeps its LAST
    snapshot, as ChainState.update does. `backfill` is chain_backfill.read_grid's {minute: rec}: it fills only
    minutes the recorder never saw (chain_backfill's rule, "never clobber the socket") and carries no peak."""
    minutes, peaks, run = {}, {}, {}
    for s in snaps or ():
        ts = s.get("ts") if isinstance(s, dict) else None
        if not isinstance(ts, str) or not "09:15:00" <= ts <= "15:30:00" or s.get("spot") is None:
            continue
        k, px = {}, {}
        for r in s.get("strikes") or ():
            if not isinstance(r, dict) or r.get("k") is None:
                continue
            ce, pe = r.get("ce") or {}, r.get("pe") or {}
            k[r["k"]] = (ce.get("oi_chg") or 0.0, pe.get("oi_chg") or 0.0)
            px[r["k"]] = (ce.get("ltp"), pe.get("ltp"))
            for side, leg in (("ce", ce), ("pe", pe)):
                if _num(leg.get("oi")) is not None:
                    run[(r["k"], side)] = max(run.get((r["k"], side), 0.0), leg["oi"])
        minutes[ts[:5]] = {"spot": s["spot"], "k": k, "px": px}
        peaks[ts[:5]] = dict(run)
    for m, rec in (backfill or {}).items():
        if m not in minutes and m < "15:30":
            minutes[m] = dict(rec, src="backfill")
    return minutes, peaks


def _upto(d, at):
    keys = sorted(d)
    j = bisect.bisect_right(keys, at) - 1
    return d[keys[j]] if j >= 0 else None


def oi_read(kind, side, minutes, peaks, at):
    """OI ok at minute `at` (the last minute inside the bar): §1's front, judged by fronts.read on the cut grid.
    A stale or unreadable grid is "could not check" (ok None), never a verdict (§1d)."""
    cut = fronts.cut(minutes, at)
    want = (fronts.DEFENDER["buy" if side == "BUY" else "sell"] if kind == POCKET
            else ("CE" if side == "BUY" else "PE"))
    out = {"ok": None, "why": None, "front": None,
           "bf": any(isinstance(v, dict) and v.get("src") == "backfill" for v in cut.values()) or None}
    stale = fronts.stale(cut, at)
    rows = [] if stale else fronts.read(cut, _upto(peaks, at))
    f = fronts.side_front(rows, want)
    if kind is None:
        out["why"] = "the setup's kind could not be read"
    elif stale:
        out["why"] = stale
    elif f is None:
        out["why"] = f"no {want} front read at {at}"
    else:
        out["front"] = {"k": f["k"], "side": want, "state": f["state"], "peak_at": f["peak_at"]}
        out["ok"] = (f["state"] == fronts.BUILDING if kind == POCKET
                     else f["state"] in (fronts.STALLED, fronts.UNWINDING))
        out["why"] = f"{'defending' if kind == POCKET else 'attacking'} {want} {f['k']:.0f} {f['state']}"
    return out


# ---- FLOW --------------------------------------------------------------------------------------------------------

def book_flow(rows, tick=None):
    """(flow, seen, bad) from the Upstox book record, sided by rank.py's rule (ladder.attribute via Ladder.step).

    flow  {minute: [buy, sell]} by the fill's trade-time minute (exchange units; the tilt is a ratio, so the lot
          never matters). An unknown-side fill is neither.
    seen  the minutes at least one frame ARRIVED in. A minute with no frame is a hole, not a quiet minute.
    bad   the minute(s) of the first frame after a gap >= HOLE_S, and of the record's first frame: that frame's
          volume is the whole gap's, sided against a book from before it (INTERNAL.md's warning), so it is excluded.
    """
    lad = ladder.Ladder(tick=tick)
    flow, seen, bad, prev = {}, set(), set(), None
    for r in rows or ():
        t = r.get("t") if isinstance(r, dict) else None
        if not isinstance(t, (int, float)):
            continue
        _closed, fills = lad.step(r)
        m = mod(t)
        seen.add(m)
        if prev is None or t - prev >= HOLE_S * 1000:
            bad.add(m)
            bad.update(mod(f["ltt"]) for f in fills)
        for f in fills:
            if f["side"]:
                flow.setdefault(mod(f["ltt"]), [0, 0])[0 if f["side"] > 0 else 1] += f["q"]
        prev = t
    return flow, seen, bad


def tilt(book, a, b):
    """(buys - sells) / (buys + sells) over minutes [a, b), or (None, why)."""
    flow, seen, bad = book
    for m in range(a, b):
        if m not in seen:
            return None, f"no Upstox book frame in {hm(m)}"
        if m in bad:
            return None, f"{hm(m)} carries a book hole's volume"
    bs = [flow.get(m, (0, 0)) for m in range(a, b)]
    B, S = sum(x[0] for x in bs), sum(x[1] for x in bs)
    if B + S <= 0:
        return None, f"no sided volume {hm(a)}-{hm(b)}"
    return round((B - S) / (B + S), 4), None


def gc_tilt(gc, close):
    """The GoCharting 5-min bar covering exactly [close-5, close), whole, as a tilt -- or None (absent)."""
    for r in gc or ():
        if (isinstance(r, dict) and isinstance(r.get("t"), (int, float)) and mod(r["t"]) == close - FAST
                and not r.get("partial")):
            b, s = _num(r.get("buy")), _num(r.get("sell"))
            if b is not None and s is not None and b + s > 0:
                return round((b - s) / (b + s), 4)
    return None


def flow_read(side, book, close, gc=None):
    """FLOW ok at a bar closing at `close`. `gc` is NIFTY's GoCharting bars, None for the other indices."""
    buy = side == "BUY"
    t5, w5 = tilt(book, close - FAST, close)
    t15, w15 = tilt(book, close - FAST - SLOW, close - FAST)
    g = gc_tilt(gc, close) if gc is not None else None
    out = {"ok": None, "t5": t5, "t15": t15, "gc": g, "why": w5 or w15}
    if t5 is None or t15 is None:
        return out
    out["ok"] = (t5 >= TILT and t15 <= 0) if buy else (t5 <= -TILT and t15 >= 0)
    out["why"] = "aggression turned" if out["ok"] else "no flip"
    if out["ok"] and g is not None and (g <= -TILT if buy else g >= TILT):
        out.update(ok=False, why="sources disagree")
    return out


# ---- THE CONFLUENCE ENTRY ----------------------------------------------------------------------------------------

def trade(setup, bar):
    """(E, sigma, stop) entering at this bar's close (§2), or None when its sigma cannot be read."""
    buy = setup["side"] == "BUY"
    E, sg = _num(bar.get("c")), sigma(bar)
    if E is None or sg is None or setup["kind"] is None or setup["extreme"] is None:
        return None
    if setup["kind"] == POCKET:
        stop = _num(bar.get("d3" if buy else "u3"))
        if stop is None:
            return None
    else:
        stop = setup["extreme"] - EXH_BUF * sg if buy else setup["extreme"] + EXH_BUF * sg
    stop = min(stop, E - MIN_RISK * sg) if buy else max(stop, E + MIN_RISK * sg)
    return {"E": E, "sigma": round(sg, 4), "stop": round(stop, 4)}


def evaluate(setup, bars, chain, book, gc=None):
    """ZONE / OI / FLOW at the trigger bar and the next 3 bars, and the confluence entry (the first bar, closing by
    15:00, where all three hold) or None. `chain` = chain_grid(...), `book` = book_flow(...)."""
    i, side, kind = setup["i"], setup["side"], setup["kind"]
    c0 = close_of(setup["t"])
    out, entry = [], None
    for j in range(i, min(i + WINDOW_BARS + 1, len(bars))):
        b = flat(bars[j])
        close = close_of(b.get("t"))
        if close is None or c0 is None or close - c0 > WINDOW_MIN:
            break
        ev = {"t": b["t"], "close": hm(close), "zone": zone_read(side, b),
              "oi": oi_read(kind, side, chain[0], chain[1], fronts.bar_last_minute(b["t"], INTERVAL)),
              "flow": flow_read(side, book, close, gc), "late": close > CUTOFF}
        out.append(ev)
        if (entry is None and not ev["late"] and ev["zone"]["ok"] and ev["oi"]["ok"] and ev["flow"]["ok"]):
            tr = trade(setup, b)
            if tr is not None:
                entry = dict(tr, t=b["t"], close=hm(close), bar=j - i)
    return {"bars": out, "entry": entry}


def row(setup, bars, chain, book, gc=None, stamp_in=None):
    """The forward log's row (and the scorer's), everything known by the window's last bar close: no outcome."""
    ev = evaluate(setup, bars, chain, book, gc)
    at_bar = ev["entry"]["t"] if ev["entry"] else setup["t"]
    return {"t": setup["t"], "side": setup["side"], "kind": setup["kind"], "extreme": setup["extreme"],
            "ref_t": setup["ref_t"], "first_t": setup["first_t"], "bars": ev["bars"], "entry": ev["entry"],
            "atm": atm(setup["side"], chain[0], fronts.bar_last_minute(ev["entry"]["t"], INTERVAL))
            if ev["entry"] else None,
            "stamps": stamps(setup, bars, chain[0], at_bar, **(stamp_in or {})), "rev": REV}


# ---- the stamps (§1: recorded, never part of a rule) ---------------------------------------------------------------

FAM = {"absorption": "R", "E3": "R", "exhaustion": "T", "climax": "T", "E6": "T", "E7": "T", "trap": "P"}  # v2.js FAM


def both_legs(minutes, at):
    """§1h fact 5's straddle: the strike ATM at at-15, its CE and PE at at-15 and at `at`; True when both rose."""
    m0 = band_rotation._minute(at)
    a, b = _at_minute(minutes, hm(m0 - 15)), _at_minute(minutes, at)
    if a is None or b is None or a.get("spot") is None:
        return None
    k = _atm_k(a)
    p0, p1 = (a.get("px") or {}).get(k), (b.get("px") or {}).get(k)
    if k is None or not p0 or not p1 or None in (*p0, *p1):
        return None
    return p1[0] > p0[0] and p1[1] > p0[1]


def reaction(setup, sg, prior=None):
    """The reaction points within RP_NEAR sigma of the extreme: PDH/PDL, a round 100, the session's own high/low
    before the setup's first arm."""
    x = setup["extreme"]
    if x is None or not sg:
        return None
    lv = {"round100": round(x / 100) * 100}
    if prior:
        lv.update(PDH=prior.get("h"), PDL=prior.get("l"))
    if setup["session_hl"]:
        lv.update(session_high=setup["session_hl"][0], session_low=setup["session_hl"][1])
    return sorted(n for n, v in lv.items() if _num(v) is not None and abs(v - x) <= RP_NEAR * sg)


def stamps(setup, bars, minutes, at_bar, ctx=None, gate=None, read=None, marks=None, prior=None):
    """§1's stamps, at the entry bar (or the trigger bar when there is none). Inputs are only what existed then."""
    j = next((k for k, b in enumerate(bars) if flat(b).get("t") == at_bar), setup["i"])
    b = flat(bars[j])
    close = close_of(at_bar)
    plays = (ctx or {}).get("plays")
    words = [r for r in read or () if isinstance(r.get("t"), str) and band_rotation._minute(r["t"]) <= close]
    rtp = [{"fam": FAM[m["kind"]], "kind": m["kind"], "t": hm(mod(m["t"])), "side": m.get("side"), "p": m.get("p")}
           for m in marks or () if m.get("kind") in FAM and isinstance(m.get("t"), (int, float))
           and close - FAST - SLOW <= mod(m["t"]) and mod(m["t"]) + 5 <= close]
    return {"time": at_bar, "trigger_t": setup["t"], "dte": (ctx or {}).get("t_exp"),
            "first_touch": setup["first_touch"], "depth": setup["depth"],
            "read": words[-1].get("word_r1", words[-1].get("word")) if words else None,   # read-1.1's, as registered
            "both_legs": both_legs(minutes, fronts.bar_last_minute(at_bar, INTERVAL)),
            "reaction": reaction(setup, sigma(b), prior),
            "gate": (gate or {}).get("legal") if gate else None, "gate_why": (gate or {}).get("why"),
            "veto": (any(isinstance(p, str) and p.startswith(fronts.VETO) for p in plays)
                     if isinstance(plays, list) else None),
            "rtp": rtp if marks is not None else None}


# ---- outcome (the scorer only; never on a forward row) ----------------------------------------------------------------

def outcome(side, tr, start, ones):
    """First passage on the 1-min bars labelled >= `start` (the entry close) and before 15:20: the stop (a bar
    touching both is stop first), the bar's live session VWAP, else the last close before 15:20. -> dict or None."""
    buy = side == "BUY"
    E, stop = tr["E"], tr["stop"]
    win = [b for b in ones or () if isinstance(b, dict) and band_rotation._minute(b.get("t")) is not None
           and start <= band_rotation._minute(b["t"]) < MARK]
    ex = None
    for b in win:
        lo, hi, vw = _num(b.get("l")), _num(b.get("h")), _num(b.get("vwap"))
        if lo is None or hi is None:
            continue
        if (lo <= stop) if buy else (hi >= stop):
            ex = (stop, "stop", b["t"])
        elif vw is not None and ((hi >= vw) if buy else (lo <= vw)):
            ex = (vw, "target", b["t"])
        if ex:
            break
    if ex is None:
        last = next((b for b in reversed(win) if _num(b.get("c")) is not None), None)
        if last is None:
            return None
        ex = (last["c"], "mark", last["t"])
    R = (ex[0] - E) / (E - stop) if buy else (E - ex[0]) / (stop - E)
    return {"exit": round(ex[0], 4), "how": ex[1], "exit_t": ex[2], "R": round(R, 4)}


def _at_minute(minutes, at):
    """The RECORDED chain's mark at or before `at` (§5 "from the recorded chain"; a backfilled minute is not one),
    within fronts.STALE_MIN, or None."""
    keys = sorted(k for k, v in minutes.items() if k <= at and v.get("src") != "backfill")
    if not keys or band_rotation._minute(at) - band_rotation._minute(keys[-1]) > fronts.STALE_MIN:
        return None
    return minutes[keys[-1]]


def _atm_k(rec):
    ks = [k for k in (rec.get("px") or {}) if _num(rec.get("spot")) is not None]
    return min(ks, key=lambda k: (abs(k - rec["spot"]), k)) if ks else None


def atm(side, minutes, at):
    """§5's two expressions at entry: the with-side ATM option to buy and the opposite ATM option to sell."""
    rec = _at_minute(minutes, at)
    k = _atm_k(rec) if rec else None
    if k is None:
        return None
    ce, pe = rec["px"][k]
    with_leg = "CE" if side == "BUY" else "PE"
    return {"k": k, "spot": rec["spot"], "buy": with_leg, "sell": "PE" if with_leg == "CE" else "CE",
            "buy_px": ce if with_leg == "CE" else pe, "sell_px": pe if with_leg == "CE" else ce}


def expression(side, minutes, entry_at, exit_at):
    """Both ways, equal weight (§5): the same strike's premiums at entry and at exit, in premium points."""
    a = atm(side, minutes, entry_at)
    rec = _at_minute(minutes, exit_at)
    if a is None or rec is None or a["k"] not in (rec.get("px") or {}):
        return None
    ce, pe = rec["px"][a["k"]]
    b1, s1 = (ce, pe) if a["buy"] == "CE" else (pe, ce)
    if None in (a["buy_px"], a["sell_px"], b1, s1):
        return None
    return dict(a, buy_exit=b1, sell_exit=s1, buy_pts=round(b1 - a["buy_px"], 2),
                sell_pts=round(a["sell_px"] - s1, 2))


# ---- §4 ------------------------------------------------------------------------------------------------------------

def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def drop_best(xs):
    return (sum(xs) - max(xs)) / (len(xs) - 1) if len(xs) > 1 else None


def verdict(trades, control):
    """§4 for one cell. `trades` / `control` are [{"day", "R"}]. Never a hit rate."""
    rs = [x["R"] for x in trades]
    n, mean, ex, cm = len(rs), _mean(rs), drop_best(rs), _mean([x["R"] for x in control])
    tot = sum(rs)
    days = {}
    for x in trades:
        days[x["day"]] = days.get(x["day"], 0.0) + x["R"]
    share = max(days.values()) / tot if tot > 0 else None
    diff = None if mean is None or cm is None else mean - cm
    ok = (n >= PASS_N and mean >= PASS_MEAN and ex is not None and ex > 0 and diff is not None
          and diff >= PASS_DIFF and (share is None or share <= DAY_SHARE))
    bad = n >= PASS_N and (mean <= 0 or (diff is not None and diff < 0))
    r4 = lambda v: None if v is None else round(v, 4)          # noqa: E731
    return {"n": n, "mean_R": r4(mean), "mean_R_ex_best": r4(ex), "control_n": len(control),
            "control_mean_R": r4(cm), "diff": r4(diff), "largest_day_share": r4(share),
            "verdict": "PASS" if ok else "FAIL" if bad else "INCONCLUSIVE"}
