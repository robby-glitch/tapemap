"""Apply the v2 check rules to replay.py (written after the 10:03 and 14:57 rows were seen; disclosed in PREREG-DRAFT.md)."""
import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'replay.py')
s = open(p, encoding='utf-8').read()

HELPERS = '''# ---- v2 helpers (written after the 10:03 and 14:57 rows were seen; disclosed in PREREG-DRAFT.md)
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
        return daytype.read(idx, day, bars, now=now_m, minutes=minutes, opens=opens, dte=dte)
    except Exception as e:
        return dict(ok=False, why=f"daytype failed: {type(e).__name__}: {e}")


# ---- THE TEN CHECKS (PREREG-DRAFT.md §2)'''
s = s.replace('# ---- THE TEN CHECKS (PREREG-DRAFT.md §2)', HELPERS)

def swap(start, end, new):
    global s
    i, j = s.index(start), s.index(end)
    s = s[:i] + new + s[j:]

swap('    # C2 day type', '    # C3 expression', '''    # C2 day type: daytype.py rebuilt off the ux bars + the grid; the side log's trend rows when there is no ux file
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
''')

swap('    # C4 wall behind (W)', '    # C6 flow', '''    # C4 wall behind (W): the day-long watch off the grid (a watch started at the mark reads "building, 0 % off" by construction)
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
''')

swap('def push(day, idx, t_ms', '# ---- the expression log', '''def push(day, idx, t_ms, win_ms=30 * 60000):
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
            per[o] = "could not check - no prints / no prior swing"
            continue
        e = max(rows, key=lambda x: (x[1], x[0])) if leg > 0 else min(rows, key=lambda x: (x[1], -x[0]))
        prev = max(x[1] for x in before) if leg > 0 else min(x[1] for x in before)
        same = abs(e[0] - mt) <= match_ms and leg * (e[1] - prev) > 0
        per[o] = f"{'TOOK' if same else 'FAILED'} its own prior {'high' if leg > 0 else 'low'} {prev:.0f} ({hms(e[0])[:5]} at {e[1]:.0f})" + (" (thin tape: witness)" if o == "SENSEX" else "")
        took += same
    return dict(mine=f"{idx} latest push {'UP' if leg > 0 else 'DOWN'} to {mp:.0f} at {hms(mt)[:5]}", leg=leg, per=per, took=took, why=None)


''')

swap('    # C8 cross-index', '    # C9 room', '''    # C8 cross-index: the latest push against each index's OWN prior swing; with her: 3 TOOK = WITH, 0-1 = AGAINST; against her: mirrored
    x = xindex_read(day, idx, d, t_ms)
    if x.get("why"):
        add("CROSS-INDEX", CC, f"{CC} - {x['why']}")
    else:
        with_her = x["leg"] == d
        stt_ = (W if x["took"] == 3 else N if x["took"] == 2 else A) if with_her else (A if x["took"] == 3 else N if x["took"] == 2 else W)
        add("CROSS-INDEX", stt_, f"{x['mine']} ({'with you' if with_her else 'against you'}) · {x['took']} of 3 took their prior swing · " + " · ".join(f"{o}: {t}" for o, t in x["per"].items()))
''')

swap('    # C10 paying', '    # printed, not counted', '''    # C10 paying: the payers' side top-2 by session-peak OI inside the nine, beyond spot (an ITM strike's unwind on 0DTE is mechanical)
    spot = (c or {}).get("spot")
    pay = payers(minutes, peak, spot, d) if spot else []
    if not pay:
        add("PAYING", CC, f"{CC} - no payers' front beyond spot inside the nine")
    else:
        states = [f["state"] for f in pay]
        txt = " · ".join(f"{f['side']} {f['k']:.0f} {f['state']} (day peak {f['peak_at']}, {f['pct_off']:.1f} % off)" for f in pay)
        add("PAYING", W if "UNWINDING" in states else A if all(s_ == "BUILDING" for s_ in states) else N, txt + " [M]")
''')

s = s.replace('''            w = v.get("W") or {}
            off = round((w["peak"] - w["oi"]) / w["peak"] * 100, 1) if w.get("peak") else None
            row = (hms(t)[:5], (v.get("headline") or "")[:22], v["chips"], w.get("k"), w.get("side"), w.get("state"), off, v.get("fut"), (v.get("prem") or {}).get("now"), (v.get("G") or {}).get("px"))
            sig = row[1:6] + (None if off is None else int(off // 5),)''',
'''            w = v.get("W") or {}
            off = round((w["peak"] - w["oi"]) / w["peak"] * 100, 1) if w.get("peak") else None
            ww = stt.Ww
            n_pk = (ww.j - ww.pk_i) if ww is not None and ww.pk_i is not None else None
            row = (hms(t)[:5], (v.get("headline") or "")[:22], v["chips"], w.get("k"), w.get("side"), w.get("state"), off, v.get("fut"), (v.get("prem") or {}).get("now"), (v.get("G") or {}).get("px"), n_pk)
            sig = row[1:6] + (None if off is None else int(off // 5), None if off is None else off >= 10, None if n_pk is None else n_pk >= 15)''')
s = s.replace('''            print("  ", r[0], r[1].ljust(22), "/".join(str(r[2].get(c)) for c in "ZFOV").ljust(34), r[3], r[4], str(r[5]).ljust(9), r[6], r[7], r[8], r[9])''',
'''            print("  ", r[0], r[1].ljust(22), "/".join(str(r[2].get(c)) for c in "ZFOV").ljust(34), r[3], r[4], str(r[5]).ljust(9), str(r[6]).ljust(5), "n" + str(r[10]).ljust(4), r[7], r[8], r[9])''')
open(p, 'w', encoding='utf-8').write(s)
print("patched v2")
