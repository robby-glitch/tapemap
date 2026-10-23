"""replay.py -- VALIDATE 2 evidence, read-only, in-sample hindsight.

For a (day, idx, trade, moment) it rebuilds what the proposed VALIDATE would have said at the mark: the rev 6 engine's
read for a mark made then (fold.py, fed the way fold_live feeds it), the chain facts (moneyness, time value, spread,
near-ATM PCR, the top-2 fronts per side with their state), CVD off the engine's own ladder bars, the other two indices'
latest extremes, the expression log's word at the last 3-min close, VPIN's percentile, and the ten checks + word of
docs/validate2/fable/PREREG-DRAFT.md. Then the better-trade search at the same moment (the 4 ATM legs + 2 ITM sales per
index whose files exist). Nothing tracked is edited; no server is touched; no POST.

Usage:  python replay.py entry  DAY IDX K TY SIDE P0 HH:MM:SS      -> the checks + the better-trade board at the mark
        python replay.py path   DAY IDX K TY SIDE P0 HH:MM:SS [TO] -> the in-trade path, one row per minute: word, chips,
                                                                      W off its peak (the slow bleed), premium
Run from tapemap/ (it imports the engine modules from there)."""
from __future__ import annotations

import bisect
import copy
import json
import os
import pickle
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import book_log      # noqa: E402
import daylog        # noqa: E402
import fold          # noqa: E402
import fold_live     # noqa: E402
import fronts        # noqa: E402

LOT = {"NIFTY": 65, "BANKNIFTY": 30, "SENSEX": 20}
STEP = {"NIFTY": 50, "BANKNIFTY": 100, "SENSEX": 100}
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
CACHE = os.path.join(HERE, "_cache")
os.makedirs(CACHE, exist_ok=True)
hms, ms = fold.hms, fold.ms


def _jsonl(path):
    out = []
    try:
        with daylog.open_text(path) as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def have(day, idx):
    return daylog.exists(os.path.join("data", "book", f"book_{idx}_{day}.jsonl")) and \
        daylog.exists(os.path.join("data", "chain", f"chain_{idx}_{day}.jsonl"))


def prior_days(day, idx, n=5):
    days = sorted({f.split("_")[2].split(".")[0] for f in os.listdir(os.path.join("data", "book")) if f.startswith(f"book_{idx}_")})
    return [d for d in days if d < day][-n:]


def load_day(day, idx):
    """book, chain, vpin rows + the 5 prior sessions (pickled once)."""
    p = os.path.join(CACHE, f"{idx}_{day}.pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    book = list(book_log.read_rows(day, idx))
    chain = [r for r in _jsonl(os.path.join("data", "chain", f"chain_{idx}_{day}.jsonl")) if r.get("ts") and r.get("strikes")]
    vpin = [r for r in _jsonl(os.path.join("data", "vpin_fast.jsonl")) if r.get("day") == day]
    prior = [fold.session_from_book(list(book_log.read_rows(d, idx)), lot=LOT[idx], idx=idx, day=d) for d in prior_days(day, idx)]
    out = dict(book=book, chain=chain, vpin=vpin, prior=prior, expiry=(chain[-1].get("expiry") if chain else None))
    pickle.dump(out, open(p, "wb"))
    return out


def inputs_for(day, idx, D):
    return dict(day=day, idx=idx, lot=LOT[idx], prior=D["prior"], expiry=D["expiry"])


def feed_to(stt, D, day, t_ms, t_from=0):
    """Feed rows with t_from < key <= t_ms in fold_live's key order."""
    rows = [(r["t"], 1, r) for r in D["book"] if t_from < r["t"] <= t_ms] + \
           [(ms(day, r["ts"]), 0, r) for r in D["chain"] if t_from < ms(day, r["ts"]) <= t_ms]
    rows.sort(key=lambda x: (x[0], x[1]))
    stt.feed(book=[r for _, k, r in rows if k], chain=[r for _, k, r in rows if not k])
    return stt


def flat_state(day, idx, D, t_ms):
    """The market alone up to t (fold.State(None)), cached per minute."""
    key = (idx, day, t_ms // 60000)
    if key not in _FLAT:
        stt = fold.State(None, inputs_for(day, idx, D))
        stt.feed(vpin=D["vpin"])
        feed_to(stt, D, day, t_ms)
        _FLAT[key] = stt
    return _FLAT[key]


_FLAT = {}


def mark_now(day, idx, D, k, ty, side, t_ms, p0=None):
    """IF YOU WERE IN at t: the flat state copied, marked at the last chain row <= t (fold_live._ifin's method)."""
    fl = flat_state(day, idx, D, t_ms)
    c = max((r for r in D["chain"] if ms(day, r["ts"]) <= t_ms), key=lambda r: ms(day, r["ts"]), default=None)
    if c is None:
        return None, "no chain row yet"
    x = next((x for x in c["strikes"] if x["k"] == k), None)
    px = (x or {}).get(ty.lower(), {}).get("ltp") if x else None
    if not px:
        return None, f"no chain price for {k} {ty}"
    stt = copy.deepcopy(fl)
    tr = dict(k=k, ty=ty, side=side, p0=p0 if p0 is not None else px, entry_t=ms(day, c["ts"]), trade_id=f"ifin:{day}:{k}{ty}:{side[0]}:{c['ts']}")
    fold_live._as_trade(stt, tr)
    stt.feed(chain=[c])
    v = stt.view(ms(day, c["ts"]))
    v["p0_chain"] = px
    return v, None


# ---- chain facts at t
def chain_at(D, day, t_ms):
    return max((r for r in D["chain"] if ms(day, r["ts"]) <= t_ms), key=lambda r: ms(day, r["ts"]), default=None)


def grid_to(D, day, t_ms):
    """fronts.read's grid: per minute, OI change since the open per strike; and the session-peak OI."""
    first = {}
    minutes, peak = {}, {}
    for r in D["chain"]:
        tm = ms(day, r["ts"])
        if tm > t_ms:
            break
        kk = {}
        for x in r["strikes"]:
            k = x["k"]
            ce, pe = x["ce"].get("oi") or 0, x["pe"].get("oi") or 0
            first.setdefault((k, "ce"), ce)
            first.setdefault((k, "pe"), pe)
            peak[(k, "ce")] = max(peak.get((k, "ce"), 0), ce)
            peak[(k, "pe")] = max(peak.get((k, "pe"), 0), pe)
            kk[k] = (ce - first[(k, "ce")], pe - first[(k, "pe")])
        minutes[r["ts"][:5]] = {"spot": r.get("spot"), "k": kk}
    return minutes, peak


def pcr_near(c, n=9):
    ks = fronts.nine([x["k"] for x in c["strikes"]], c["spot"])
    ce = sum((x["ce"].get("oi") or 0) for x in c["strikes"] if x["k"] in ks)
    pe = sum((x["pe"].get("oi") or 0) for x in c["strikes"] if x["k"] in ks)
    return (pe / ce if ce else None), ce, pe


def leg(c, k, ty):
    x = next((x for x in c["strikes"] if x["k"] == k), None)
    return (x or {}).get(ty.lower()) or {}


# ---- CVD off the engine's ladder bars
def cvd(stt):
    out, acc = [], 0.0
    for b in stt.bars:
        d = sum(r["b"] - r["s"] for r in b["ladder"])
        acc += d
        out.append((b["t"] + 60000, acc, b["h"], b["l"], b["c"]))
    return out


def cvd_read(stt, d, t_ms, win_ms=60 * 60000):
    rows = [x for x in cvd(stt) if x[0] <= t_ms]
    if len(rows) < 5:
        return dict(why="fewer than 5 ladder minutes")
    px_i = max(range(len(rows)), key=lambda i: d * (rows[i][2] if d > 0 else rows[i][3]))
    cv_i = max(range(len(rows)), key=lambda i: d * rows[i][1])
    recent = [x for x in rows if x[0] >= t_ms - win_ms]
    px_r = max(range(len(recent)), key=lambda i: d * (recent[i][2] if d > 0 else recent[i][3]))
    cv_r = max(range(len(recent)), key=lambda i: d * recent[i][1])
    div = px_r > cv_r + 3           # a price extreme in d after the CVD extreme, > 3 minutes later = not paid for
    net_since_cvd_peak = rows[-1][1] - rows[cv_i][1]
    return dict(cvd_now=round(rows[-1][1]), cvd_peak_t=hms(rows[cv_i][0])[:5], px_ext_t=hms(rows[px_i][0])[:5],
                div_60m=div, net_since_peak=round(net_since_cvd_peak), why=None)


def vwap(stt):
    v = pv = 0.0
    for b in stt.bars:
        for r in b["ladder"]:
            q = r["b"] + r["s"] + r["u"]
            v += q
            pv += r["p"] * q
    return round(pv / v, 1) if v else None


# ---- the other indices' latest extreme in d
_PX = {}


def px_series(day, idx):
    if (day, idx) not in _PX:
        rows = [(r["ltt"], r["ltp"]) for r in book_log.read_rows(day, idx) if r.get("ltt") and r.get("ltp")]
        _PX[(day, idx)] = rows
    return _PX[(day, idx)]


def push(day, idx, t_ms, win_ms=30 * 60000):
    """The latest push: over the last 30 min the later of the high and the low ends the leg -> (leg, t, px, took, prev):
    took says whether that extreme went beyond the index's OWN previous swing (its extreme before the window)."""
    rows = [x for x in px_series(day, idx) if t_ms - win_ms <= x[0] <= t_ms]
    before = [x for x in px_series(day, idx) if x[0] < t_ms - win_ms]
    if len(rows) < 10:
        return None
    hi = max(rows, key=lambda x: (x[1], x[0]))
    lo = min(rows, key=lambda x: (x[1], -x[0]))
    leg, ext = (1, hi) if hi[0] > lo[0] else (-1, lo)
    prev = (max(x[1] for x in before) if leg > 0 else min(x[1] for x in before)) if before else None
    took = None if prev is None else (leg * (ext[1] - prev) > 0)
    return leg, ext[0], ext[1], took, prev


def xindex_read(day, idx, d, t_ms, match_ms=10 * 60000):
    mine = push(day, idx, t_ms)
    if mine is None:
        return dict(why="fewer than 10 prints in the last 30 min")
    leg, mt, mp, mtook, mprev = mine
    if mprev is None:
        return dict(why="no prior swing yet (fewer than 30 min of prints)")
    per, took = {}, (1 if mtook else 0)
    per[idx] = (f"{'TOOK' if mtook else 'FAILED'} its own prior {'high' if leg > 0 else 'low'} {mprev:.0f}") if mprev is not None else "no prior swing yet"
    for o in IDXS:
        if o == idx:
            continue
        if not daylog.exists(os.path.join("data", "book", f"book_{o}_{day}.jsonl")):
            per[o] = "could not check - no book file"
            continue
        rows = [x for x in px_series(day, o) if t_ms - 30 * 60000 <= x[0] <= t_ms]
        before = [x for x in px_series(day, o) if x[0] < t_ms - 30 * 60000]
        if len(rows) < 10 or not before:
            return dict(why=f"{o} has no prior swing yet")
        e = max(rows, key=lambda x: (x[1], x[0])) if leg > 0 else min(rows, key=lambda x: (x[1], -x[0]))
        prev = max(x[1] for x in before) if leg > 0 else min(x[1] for x in before)
        same = abs(e[0] - mt) <= match_ms and leg * (e[1] - prev) > 0
        per[o] = f"{'TOOK' if same else 'FAILED'} its own prior {'high' if leg > 0 else 'low'} {prev:.0f} ({hms(e[0])[:5]} at {e[1]:.0f})" + (" (thin tape: witness)" if o == "SENSEX" else "")
        took += same
    return dict(mine=f"{idx} latest push {'UP' if leg > 0 else 'DOWN'} to {mp:.0f} at {hms(mt)[:5]}", leg=leg, per=per, took=took, why=None)


# ---- the expression log and the side log
def expr_at(day, idx, t_hms, d=None):
    rows = [r for r in _jsonl(os.path.join("data", "hold", f"expr_{day}.jsonl")) if r.get("idx") == idx and r.get("kind") == "expr"]
    rows = [r for r in rows if r["t"] <= t_hms[:5] and (d is None or r.get("d") == d)]
    return rows[-1] if rows else None


def side_at(day, idx, t_hms):
    rows = [r for r in _jsonl(os.path.join("data", "hold", f"side_{day}.jsonl")) if r.get("idx") == idx and r.get("kind") == "minute"]
    rows = [r for r in rows if r["t"] <= t_hms[:5]]
    return rows[-1] if rows else None


def vpin_at(D, day, t_ms, idx="NIFTY"):
    rows = [r for r in D["vpin"] if r.get("inst") == f"{idx}-FUT:fast" and ms(day, r["at"]) <= t_ms and r.get("pct") is not None]
    return rows[-1] if rows else None


# ---- v2 helpers (written after the 10:03 and 14:57 rows were seen; disclosed in PREREG-DRAFT.md)
def wall_state(minutes, peak, k, side):
    """fronts._state on this strike's own OI-change series since the open (the day-long watch, not the mark's)."""
    times = sorted(minutes)
    if not times or k is None:
        return None
    i = 0 if side == "CE" else 1
    vals = [((minutes[t].get("k") or {}).get(k) or (0, 0))[i] for t in times]
    pk, chg = max(vals), vals[-1]
    back = vals[max(0, len(vals) - 1 - fronts.SLOPE_MARKS)]
    slope = chg - back
    oi_pk = peak.get((k, side.lower()))
    pct = (pk - chg) / oi_pk * 100 if oi_pk else None
    return dict(state=fronts._state(chg, pk, slope), peak_at=times[vals.index(pk)], pct_off=pct, slope=slope, oi_peak=oi_pk)


def payers(minutes, peak, spot, d):
    """The payers' side top-2 by session-peak OI inside the nine, BEYOND spot (OTM): CE above for up, PE below for down."""
    if not minutes:
        return []
    last = minutes[sorted(minutes)[-1]]
    ks = fronts.nine(list((last.get("k") or {}).keys()), spot)
    side = "CE" if d > 0 else "PE"
    beyond = [k for k in ks if (k > spot if d > 0 else k < spot)]
    rows = [dict(k=k, side=side, **(wall_state(minutes, peak, k, side) or {})) for k in beyond]
    rows = [r for r in rows if r.get("oi_peak")]
    rows.sort(key=lambda r: -r["oi_peak"])
    return rows[:2]


def daytype_at(day, idx, D, t_ms, minutes):
    try:
        import daytype
        bars = _jsonl(os.path.join("data", "tape", f"ux_{idx}_{day}.jsonl"))
        bars = [b for b in bars if isinstance(b.get("t"), (int, float)) and b.get("c") is not None]
        if not bars:
            return None
        opens = {}
        for r in D["chain"][:1]:
            for x in r["strikes"]:
                opens[(x["k"], "ce")] = x["ce"].get("oi") or 0
                opens[(x["k"], "pe")] = x["pe"].get("oi") or 0
        import datetime as _dt
        dte = (_dt.date.fromisoformat(D["expiry"]) - _dt.date.fromisoformat(day)).days if D.get("expiry") else None
        now_m = int(hms(t_ms)[:2]) * 60 + int(hms(t_ms)[3:5])
        tp = os.path.join("data", "trap", f"trap_{day}.jsonl")
        trap_events = ([r for r in _jsonl(tp) if r.get("idx") == idx and r.get("kind") == "state" and str(r.get("t", "")) <= hms(t_ms)]
                       if os.path.exists(tp) else None)
        out = daytype.read(idx, day, bars, now=now_m, minutes=minutes, opens=opens, dte=dte, trap_events=trap_events)
        if trap_events is None and isinstance(out, dict):
            out["word"] = (out.get("word") or "") + " (no trap log that day: the FAIL ender is absent)"
        return out
    except Exception as e:
        return dict(ok=False, why=f"daytype failed: {type(e).__name__}: {e}")


# ---- THE TEN CHECKS (PREREG-DRAFT.md §2)
W, A, N, CC = "WITH", "AGAINST", "NEITHER", "could not check"


def checks(day, idx, D, v, k, ty, side, t_ms):
    d, own = v["d"], (1 if side == "BUY" else -1)
    B = (v.get("units") or {}).get("B")
    c = chain_at(D, day, t_ms)
    out = []

    def add(name, state, text, counted=True):
        out.append(dict(name=name, state=state, text=text, counted=counted))
    # C1 right now
    h = v.get("headline") or ""
    add("RIGHT NOW", W if h.startswith("HOLD") else A if h.startswith(("FOLD", "PAST")) else CC, f"{h} · {v.get('clause') or v.get('why')}")
    # C2 day type: daytype.py rebuilt off the ux bars + the grid; the side log's trend rows when there is no ux file
    minutes, peak = grid_to(D, day, t_ms)
    dt = daytype_at(day, idx, D, t_ms, minutes)
    s = side_at(day, idx, hms(t_ms))
    if dt and dt.get("ok"):
        ty_, dr = dt.get("type"), dt.get("dir") or 0
        if ty_ == "TREND":
            stt_ = W if dr == d else A
        elif ty_ == "PIN":
            stt_ = W if own < 0 else N
        else:
            stt_ = N
        add("DAY / TREND", stt_, f"{dt.get('word')} since {dt.get('since')} [I] · " + " · ".join(e.get("chip", "") for e in (dt.get("evidence") or [])[:3]))
    elif s is None:
        add("DAY / TREND", CC, f"{CC} - no ux bars and no side log for {idx} {day}" + (f" ({dt.get('why')})" if dt else ""))
    else:
        rows = s.get("rows") or {}
        want = "UP" if d > 0 else "DOWN"
        other = "DOWN" if d > 0 else "UP"
        nw = sum(1 for x in rows.values() if x == want)
        na = sum(1 for x in rows.values() if x == other)
        txt = " · ".join(f"{tf} {w}" for tf, w in rows.items())
        add("DAY / TREND", W if nw >= 2 and na == 0 else A if na >= 2 else N, txt + f" [I] (trend rows, side log {s['t']}; no ux file for daytype)")
    # C3 expression: the log keeps one row per direction per close; hers (d) and the other way (-d)
    e, eo = expr_at(day, idx, hms(t_ms), d), expr_at(day, idx, hms(t_ms), -d)
    if e is None:
        add("EXPRESSION", CC, f"{CC} - no expression log for {day}")
    else:
        word, wo = e["word"], (eo or {}).get("word", "")
        if word.startswith("STAND") and wo and not wo.startswith(("STAND", "EITHER")):
            stt_, txt = A, f"the engine leans the OTHER way at {e['t']}: {wo} ({eo['nb']} buy · {eo['ns']} sell facts); your way: {word}"
        elif word.startswith("STAND"):
            stt_, txt = N, f"{word} at {e['t']} (and the other way: {wo or 'no row'})"
        elif word.startswith("EITHER"):
            stt_, txt = W, f"EITHER at {e['t']}: buy or sell, both read"
        else:
            buy_word = "BUY" in word
            stt_ = W if buy_word == (side == "BUY") else A
            card = e.get("sell" if side == "BUY" else "buy") or {}
            txt = f"{word} at {e['t']} ({e['nb']} buy · {e['ns']} sell facts)" + ("" if stt_ == W else
                  f" - same thesis, better expression: {'sell' if side == 'BUY' else 'buy'} {card.get('k')} {card.get('side')} @ {card.get('px')}")
        add("EXPRESSION", stt_, txt)
    # C4 wall behind (W): the day-long watch off the grid (a watch started at the mark reads "building, 0 % off" by construction)
    w = v.get("W")
    ws = wall_state(minutes, peak, w.get("k"), w.get("side")) if w else None
    if not w or not ws:
        add("WALL BEHIND", CC, f"{CC} - no wall behind read yet")
    else:
        add("WALL BEHIND", {"BUILDING": W, "STALLED": N, "UNWINDING": A}[ws["state"]],
            f"{w['k']} {w['side']} writers {w['oi'] / 1e5:.1f}L, {ws['state']} on the day's watch (day peak {ws['peak_at']}, {ws['pct_off']:.1f} % off it) [M]")
    # C5 wall ahead (A): a buyer's target must break it; a writer has no next wall
    a = v.get("A")
    as_ = wall_state(minutes, peak, a.get("k"), a.get("side")) if a else None
    if own < 0:
        add("WALL AHEAD", N, "not shown - a writer has no next wall; time is her target", counted=False)
    elif not a or not as_:
        add("WALL AHEAD", CC, f"{CC} - no wall ahead read yet")
    else:
        stt_ = W if as_["state"] == "UNWINDING" else (A if as_["state"] == "BUILDING" and B and a["pts"] <= 2 * B else N)
        add("WALL AHEAD", stt_, f"{a['k']} {a['side']} writers {a['oi'] / 1e5:.1f}L, {as_['state']} (day peak {as_['peak_at']}, {as_['pct_off']:.1f} % off), {a['pts']} pts ahead (fut) [M]")
    # C6 flow
    fr = (v.get("rows") or {}).get("flow") or {}
    stt_ = fr.get("chip")
    cv = cvd_read(flat_state(day, idx, D, t_ms), d, t_ms)
    cvtxt = (f"CVD {cv['cvd_now']:+,} (peak {cv['cvd_peak_t']}, price extreme {cv['px_ext_t']}" + (", NOT paid for in the last hour" if cv["div_60m"] else "") + ") [I]") if not cv.get("why") else f"CVD: {cv['why']}"
    add("ORDER FLOW", W if stt_ == "WITH" else A if stt_ == "AGAINST" else CC if (stt_ or "CAN'T") == "CAN'T CHECK" else N, f"{fr.get('sentence')} · {cvtxt}")
    # C7 vpin
    vr = (v.get("rows") or {}).get("vpin") or {}
    vp = vpin_at(D, day, t_ms, idx)
    add("VPIN", W if vr.get("chip") == "WITH" else A if vr.get("chip") == "AGAINST" else CC if vr.get("chip") == "CAN'T CHECK" else N,
        f"{vr.get('sentence')}" + (f" · toxicity pct {vp['pct']:.2f} (shadow)" if vp else " · no percentile (NIFTY-only gauge)"))
    # C8 cross-index: the latest push against each index's OWN prior swing; with her: 3 TOOK = WITH, 0-1 = AGAINST; against her: mirrored
    x = xindex_read(day, idx, d, t_ms)
    if x.get("why"):
        add("CROSS-INDEX", CC, f"{CC} - {x['why']}")
    else:
        with_her = x["leg"] == d
        stt_ = (W if x["took"] == 3 else N if x["took"] == 2 else A) if with_her else (A if x["took"] == 3 else N if x["took"] == 2 else W)
        add("CROSS-INDEX", stt_, f"{x['mine']} ({'with you' if with_her else 'against you'}) · {x['took']} of 3 took their prior swing · " + " · ".join(f"{o}: {t}" for o, t in x["per"].items()))
    # C9 room
    G = (v.get("G") or {}).get("px")
    fut = v.get("fut")
    if G is None or fut is None or B is None:
        add("ROOM", CC, f"{CC} — no give-up yet")
    else:
        to_g = round(d * (fut - G))
        to_a = a["pts"] if a and own > 0 else None
        stt_ = A if to_g <= B or (to_a is not None and to_a < to_g) else W
        add("ROOM", stt_, f"invalid at {G} fut ({to_g} pts; one candle B = {B:.0f})" + (f" · next wall {to_a} pts" if to_a is not None else "") + " [M]")
    # C10 paying: the payers' side top-2 by session-peak OI inside the nine, beyond spot (an ITM strike's unwind on 0DTE is mechanical)
    spot = (c or {}).get("spot")
    pay = payers(minutes, peak, spot, d) if spot else []
    if not pay:
        add("PAYING", CC, f"{CC} - no payers' front beyond spot inside the nine")
    else:
        states = [f["state"] for f in pay]
        txt = " · ".join(f"{f['side']} {f['k']:.0f} {f['state']} (day peak {f['peak_at']}, {f['pct_off']:.1f} % off)" for f in pay)
        add("PAYING", W if "UNWINDING" in states else A if all(s_ == "BUILDING" for s_ in states) else N, txt + " [M]")
    # printed, not counted
    lg = leg(c, k, ty) if c else {}
    prem = v.get("prem") or {}
    sp = (lg.get("ask") or 0) - (lg.get("bid") or 0)
    add("MONEYNESS", N, f"delta {lg.get('delta')} · intrinsic {prem.get('intrinsic')} · time value {prem.get('time')} of {prem.get('now')} [I]"
        + (" · deep ITM: a futures position in option's clothing" if lg.get("delta") is not None and abs(lg["delta"]) >= 0.85 else ""), counted=False)
    add("SPREAD", N, f"bid {lg.get('bid')} / ask {lg.get('ask')} = {sp:.2f} ({sp / 0.05:.0f} ticks) — you post, so it is revenue", counted=False)
    exp = D["expiry"] == day
    add("CLOCK", N, f"{hms(t_ms)[:5]} · " + ("EXPIRY DAY: " + (f"time value {prem.get('time')} burns to 0 by 15:30" if prem.get("time") is not None else "") if exp else f"expiry {D['expiry']}")
        + (" · past your 15:00 practice" if hms(t_ms) >= "15:00:00" else ""), counted=False)
    def pain(kk, tt):
        g = leg(c, kk, tt) if c else {}
        if not g.get("avg") or not g.get("ltp"):
            return f"{kk} {tt}: {CC} (no avg)"
        r_ = g["ltp"] / g["avg"]
        who = "writers UNDERWATER" if r_ >= 1.3 else "writers comfortable" if r_ <= 0.85 else "writers near their avg"
        return f"{kk} {tt} ltp {g['ltp']} vs day avg {g['avg']}: {who}"
    pain_rows = [pain(k, ty)] + ([pain(w["k"], w["side"])] if w and w.get("k") else []) + ([pain(a["k"], a["side"])] if a and a.get("k") else [])
    add("WHO IS IN PAIN", N, " · ".join(pain_rows) + " [I: avg is the day's traded average, chain_metrics' proxy]", counted=False)
    pcr, ce_, pe_ = pcr_near(c) if c else (None, 0, 0)
    c60 = chain_at(D, day, t_ms - 60 * 60000)
    pcr60 = pcr_near(c60)[0] if c60 else None
    add("PCR near-ATM", N, f"PCR(9) {pcr:.2f}" + (f" (was {pcr60:.2f} an hour ago)" if pcr60 else "") + f" · CE {ce_ / 1e5:.0f}L · PE {pe_ / 1e5:.0f}L [M]", counted=False)
    return out


def word_of(cs, side):
    cnt = [c for c in cs if c["counted"]]
    rn = next(c for c in cs if c["name"] == "RIGHT NOW")
    structural = {"DAY / TREND", "EXPRESSION", "WALL BEHIND", "WALL AHEAD", "ORDER FLOW", "CROSS-INDEX"}
    n_w = sum(1 for c in cnt if c["state"] == W)
    n_a = sum(1 for c in cnt if c["state"] == A)
    n_n = sum(1 for c in cnt if c["state"] == N)
    n_c = sum(1 for c in cnt if c["state"] == CC)
    a_struct = sum(1 for c in cnt if c["state"] == A and c["name"] in structural)
    need = 6
    if rn["state"] == A or a_struct >= 2:
        w = "NO"
    elif rn["state"] == W and n_a == 0 and n_c <= 1 and n_w >= need:
        w = "GO"
    else:
        w = "WAIT"
    return w, dict(with_=n_w, against=n_a, neither=n_n, cant=n_c, of=len(cnt))


def rank_key(w, cnt):
    return ({"GO": 0, "WAIT": 1, "NO": 2}[w], -cnt["with_"], cnt["against"], cnt["cant"])


def one(day, idx, D, k, ty, side, t_ms, p0=None):
    v, why = mark_now(day, idx, D, k, ty, side, t_ms, p0)
    if v is None or v.get("headline") is None:
        return dict(idx=idx, k=k, ty=ty, side=side, why=why or v.get("why"), word=None)
    cs = checks(day, idx, D, v, k, ty, side, t_ms)
    w, cnt = word_of(cs, side)
    G = (v.get("G") or {}).get("px")
    prem = v.get("prem") or {}
    return dict(idx=idx, k=k, ty=ty, side=side, p0=v.get("p0_chain"), d=v["d"], word=w, cnt=cnt, checks=cs, fut=v.get("fut"), F=v.get("F"),
                G=G, at_G=prem.get("at_G"), A=v.get("A"), at_A=prem.get("at_A"), basis_ix=(v.get("units") or {}).get("basis_ix"),
                headline=v.get("headline"), clause=v.get("clause"), line2=v.get("line2"))


def board(day, t_hms, her=None):
    """Every candidate on the board at t: the 4 ATM legs + the two ITM sales, per index with files."""
    out = []
    for idx in IDXS:
        if not have(day, idx):
            out.append(dict(idx=idx, why=f"{CC} — no book/chain file for {idx} {day}", word=None))
            continue
        D = load_day(day, idx)
        t_ms = ms(day, t_hms)
        c = chain_at(D, day, t_ms)
        if c is None:
            out.append(dict(idx=idx, why=f"{CC} — no chain row by {t_hms}", word=None))
            continue
        atm = c.get("atm") or min((x["k"] for x in c["strikes"]), key=lambda kk: abs(kk - c["spot"]))
        step = STEP[idx]
        cands = [(atm, "CE", "BUY"), (atm, "PE", "SELL"), (atm, "PE", "BUY"), (atm, "CE", "SELL"),
                 (atm + step, "PE", "SELL"), (atm - step, "CE", "SELL")]            # ITM sales: her way of selling
        for k, ty, side in cands:
            r = one(day, idx, D, k, ty, side, t_ms)
            r["atm"] = atm
            r["itm"] = (ty == "PE" and k > atm) or (ty == "CE" and k < atm)
            out.append(r)
    ranked = sorted([r for r in out if r.get("word")], key=lambda r: rank_key(r["word"], r["cnt"]) + (IDXS.index(r["idx"]),))
    return out, ranked


def fmt_checks(r):
    lines = [f"  {r['idx']} {r['side']} {r['k']} {r['ty']} @ {r['p0']}  ->  **{r['word']}**  {r['cnt']['with_']} with · {r['cnt']['against']} against · {r['cnt']['neither']} neither · {r['cnt']['cant']} could not check (of {r['cnt']['of']})",
             f"    engine: {r['headline']} · {r['clause']} · {r['line2']}",
             f"    fut {r['fut']} · F {r['F']} · basis_ix {r['basis_ix']} · give-up {r['G']} (prem there ~{r['at_G']}) · wall ahead {(r['A'] or {}).get('k')} {(r['A'] or {}).get('side')} {(r['A'] or {}).get('pts')} pts (prem there ~{r['at_A']})"]
    for c in r["checks"]:
        lines.append(f"    {'  ' if not c['counted'] else ''}{c['name']:<14} {c['state']:<16} {c['text']}")
    return "\n".join(lines)


def path(day, idx, k, ty, side, p0, t0, t1=None, every=60000):
    """The in-trade path, one row a minute: the engine's word, chips, W's OI off its peak, the premium."""
    D = load_day(day, idx)
    tr = dict(k=k, ty=ty, side=side, p0=p0, entry_t=t0)
    stt = fold.State(tr, inputs_for(day, idx, D))
    stt.feed(vpin=D["vpin"])
    a, b = ms(day, t0) - 60000 * 60 * 9, ms(day, t1) if t1 else ms(day, "15:30:00")
    keys = sorted([(r["t"], 1, r) for r in D["book"] if r["t"] <= b] + [(ms(day, r["ts"]), 0, r) for r in D["chain"] if ms(day, r["ts"]) <= b], key=lambda x: (x[0], x[1]))
    rows, i, t = [], 0, ms(day, t0)
    # everything before the mark at once
    pre = [x for x in keys if x[0] < t]
    stt.feed(book=[r for _, kk, r in pre if kk], chain=[r for _, kk, r in pre if not kk])
    i = len(pre)
    last = None
    while t <= b and i <= len(keys):
        chunk = []
        while i < len(keys) and keys[i][0] <= t:
            chunk.append(keys[i]); i += 1
        if chunk:
            stt.feed(book=[r for _, kk, r in chunk if kk], chain=[r for _, kk, r in chunk if not kk])
        if stt.seeded:
            v = stt.view(t)
            w = v.get("W") or {}
            off = round((w["peak"] - w["oi"]) / w["peak"] * 100, 1) if w.get("peak") else None
            ww = stt.Ww
            n_pk = (ww.j - ww.pk_i) if ww is not None and ww.pk_i is not None else None
            row = (hms(t)[:5], (v.get("headline") or "")[:22], v["chips"], w.get("k"), w.get("side"), w.get("state"), off, v.get("fut"), (v.get("prem") or {}).get("now"), (v.get("G") or {}).get("px"), n_pk)
            sig = row[1:6] + (None if off is None else int(off // 5), None if off is None else off >= 10, None if n_pk is None else n_pk >= 15)
            if sig != last:
                rows.append(row)
                last = sig
        t += every
    return rows


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "entry":
        day, idx, k, ty, side, p0, t0 = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6], float(sys.argv[7]), sys.argv[8]
        D = load_day(day, idx)
        her = one(day, idx, D, k, ty, side, ms(day, t0), p0)
        print(f"=== {day} {idx} her {side} {k} {ty} @ {p0} at {t0}")
        print(fmt_checks(her) if her.get("word") else her)
        allc, ranked = board(day, t0)
        print("\n=== THE BOARD at", t0, "(ranked: word, then with-count, then fewer against, then fewer could-not-check, then NIFTY > BANKNIFTY > SENSEX)")
        for r in ranked:
            print(f"  {r['word']:<4} {r['idx']:<9} {r['side']:<4} {r['k']} {r['ty']} {'ITM' if r['itm'] else 'ATM'} @ {r['p0']}  {r['cnt']['with_']}w/{r['cnt']['against']}a/{r['cnt']['neither']}n/{r['cnt']['cant']}c  "
                  f"against: {', '.join(c['name'] for c in r['checks'] if c['state'] == A and c['counted']) or '—'}")
        for r in allc:
            if not r.get("word"):
                print(f"  --   {r.get('idx')}: {r.get('why')}")
        if her.get("word"):
            hk = rank_key(her["word"], her["cnt"])
            better = [r for r in ranked if rank_key(r["word"], r["cnt"]) < hk]
            print("\n  BETTER than hers:", "none — your trade is the best on the board" if not better else "; ".join(f"{r['idx']} {r['side']} {r['k']} {r['ty']} ({r['word']}, {r['cnt']['with_']}w/{r['cnt']['against']}a)" for r in better[:3]))
            print("  TOP of the board:", f"{ranked[0]['idx']} {ranked[0]['side']} {ranked[0]['k']} {ranked[0]['ty']} ({ranked[0]['word']})" if ranked else "nothing")
            print("\n  top candidate in full:")
            if ranked and (ranked[0]["idx"], ranked[0]["k"], ranked[0]["ty"], ranked[0]["side"]) != (idx, k, ty, side):
                print(fmt_checks(ranked[0]))
    elif mode == "path":
        day, idx, k, ty, side, p0, t0 = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6], float(sys.argv[7]), sys.argv[8]
        t1 = sys.argv[9] if len(sys.argv) > 9 else None
        print(f"=== path {day} {idx} {side} {k} {ty} @ {p0} from {t0} (a row per change: min · word · Z/F/O/V · W · W state · W % off peak · fut · prem · G)")
        for r in path(day, idx, k, ty, side, p0, t0, t1):
            print("  ", r[0], r[1].ljust(22), "/".join(str(r[2].get(c)) for c in "ZFOV").ljust(34), r[3], r[4], str(r[5]).ljust(9), str(r[6]).ljust(5), "n" + str(r[10]).ljust(4), r[7], r[8], r[9])
