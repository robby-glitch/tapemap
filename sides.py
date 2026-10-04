"""sides.py -- the OI flow split by side, against the index move. Real or fake?

THE QUESTION (Mary, 2026-10-03): the OI Flow tab's "chg in dir" NETS the two sides
(put added - call added), so "call writers covering" and "put writers adding" print
the same, and a flip from - to + can be noise. Read the two sides SEPARATELY, per
index, per closed 5-minute slot, on HER strikes (the nine nearest spot), against
what the index did in that slot:

    UP slot     call writers   put writers     read
                covering       adding          REAL     forced buying above + a new floor below
                covering       flat/covering   SQUEEZE  short-covering fuel, nobody underwriting
                adding         adding/flat     CAPPED   writers sell into the rise
                adding         covering        FAKE     nobody in the book believes it
                flat           adding          BACKED   the move's own side builds, no forced flow
                flat           covering        HOLLOW   the floor leaves, no fuel
                flat           flat            QUIET
    DOWN slot   the mirror, CALL <-> PUT.
    FLAT index  a side COVERING at POWER size -> PRESSURE (effort, no result yet);
                a side ADDING at POWER size   -> WALL; else FLAT.

DEFINITIONS -- rev sides-1 fixed 2026-10-03 23:38 IST, AMENDED to rev sides-2 on
2026-10-04 00:25 IST before the next open (docs/board/real-vs-fake-2026-10-03.md §2,
§2a; the amendment adopts Fable 5.1's critique, FABLE-CRITIQUE-real-vs-fake-2026-10-04.md),
and to rev sides-3 on 2026-10-04 01:25 IST -- the morning scale, a POST-HOC change made
after the rows were seen (§2b; FABLE-TRAP-FRAMEWORK-2026-10-04.md §6).
DO NOT TUNE ANY NUMBER BELOW against what price did afterwards; a change is a new
revision with its own date, written in that note first.

    strikes   the nine nearest spot at the slot's closing mark (fronts.nine)        A1
    FLAT_K    0.5    |change| <= 0.5 x its scale -> FLAT
    POWER_R   3.0    |change| >= 3 x its scale AND both of the side's top-2-by-OI
                     fronts inside the nine moved that way (2/2)                    A2
    scale     t <= 10:30: the PREVIOUS session's SAME window, the median over its
              slots 09:20-10:30 ("kal ki subah ka scale"), CAN'T CHECK when that
              session is missing or was this index's expiry day; t > 10:30: today's
              own expanding median (needs WARM = 6 earlier slots). Every basis's
              ratio is logged on every row.                                        B1-B3, B5
    morning   POWER at t <= 10:30 is a WITNESS, never a vote in the counts          B4
    first     each direction armed at the open; a POWER slot disarms its direction
              and re-arms the opposite one; later same-direction POWER is
              continuation. The chip says PUSHTI (confirmation).                    A4, A6
    forced    a CHIP, never a word: the fuel side's top-2 with ltp > avg (0-2) and
              the nine's median IV change, from the saved snapshot at the mark      A3
    FREEZE    15:15: the spot indices freeze for the cash auction (xindex FREEZE)

Display [I] on [M] OI, premiums and prints. Nothing here gates anything: not
fronts.fade_gate, not setup.gate, not the zone machine, not trigger_log. Near-ATM
intraday option OI is read as writer-dominated (trapped_inventory.py assumption 3),
and the forced chip exists because that is not always true. Counts, never a %,
never odds; the one percentage, "fuel gone", is a measured share of OI, not a chance.

Pure: stdlib + fronts' window helpers, NO I/O, NO clock -- the caller hands in the
grid, the opens, the snapshot book, the previous session's scale and `now`, so the
same inputs give the same reads whenever they are read.
"""
from __future__ import annotations

import statistics
from collections import Counter

import fronts

REV = "sides-3"
FIXED_AT = "2026-10-03 23:38 IST (sides-1), amended 2026-10-04 00:25 IST (sides-2), 01:25 IST (sides-3, post-hoc)"
INTERVAL = 5
WARM, FLAT_K, POWER_R = 6, 0.5, 3.0
KAL_UNTIL, KAL_FROM, KAL_TO = "10:30", "10:30", "15:00"
MORN_FROM = "09:20"       # the previous session's same window: slots 09:20 <= t <= 10:30
FREEZE = "15:15"
DEFS = {"rev": REV, "fixed_at": FIXED_AT, "interval_min": INTERVAL, "strikes": "fronts.nine at the closing mark",
        "flat_k": FLAT_K, "power_x": POWER_R, "power_breadth": "both top-2-by-OI fronts of the side, 2/2",
        "scale": f"t <= {KAL_UNTIL}: previous session's {MORN_FROM}-{KAL_UNTIL} median (not if missing or its expiry "
                 f"day); later: today's (warm {WARM})", "morning_power": "a witness, never counted",
        "first_sign": "re-arms only after a POWER slot the opposite way; chip PUSHTI", "freeze": FREEZE,
        "note": "docs/board/real-vs-fake-2026-10-03.md §2a; display [I], gates nothing"}
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
WEEKLY = ("NIFTY", "SENSEX")
CC = "could not check — "
NO_KAL = CC + "subah ka scale — kal ka data nahi"
KAL_EXPIRY = CC + "subah ka scale — kal expiry din tha"
MORNING_TAG = "subah · kal ki subah ka scale"
WARMING = CC + f"warming: today's own scale needs {WARM} earlier slots"
FROZEN = "15:15 se check nahi — the spot indices freeze for the cash auction, so the index move is not read"
ARROW = {1: "▲", -1: "▼"}
WAY = {1: "upar", -1: "neeche"}
HI = {"ADD": "likh rahe", "COV": "kaat rahe"}
SIDE_WORD = {("ce", "ADD"): "call writers adding", ("ce", "COV"): "call writers covering",
             ("pe", "ADD"): "put writers adding", ("pe", "COV"): "put writers covering"}
ACTION = {("pe", "COV"): "PUT WRITERS KAAT RAHE", ("ce", "ADD"): "CALL WRITERS LIKH RAHE",
          ("ce", "COV"): "CALL WRITERS KAAT RAHE", ("pe", "ADD"): "PUT WRITERS LIKH RAHE"}
SI = {"ce": 0, "pe": 1}


def _mm(t):
    return int(t[:2]) * 60 + int(t[3:5])


def _hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _sgn(x):
    return (x > 0) - (x < 0)


def _cells(rec):
    """{strike: (ce_chg, pe_chg)} from one minute record, whatever key type the grid used."""
    out = {}
    for k, v in ((rec or {}).get("k") or {}).items():
        n = fronts._num(k)
        if n is not None:
            out[n] = fronts._pair(v)
    return out


def _med(xs):
    return statistics.median(xs) if xs else None


def _ratio(d, scale):
    if scale is None:
        return None
    return abs(d) / scale if scale > 0 else (float("inf") if d else 0.0)


def _state(d, scale):
    if scale is None:
        return None
    if abs(d) <= FLAT_K * scale:
        return "FLAT"
    return "ADD" if d > 0 else "COV"


def _r1(x):
    return None if x is None else (round(x, 2) if x != float("inf") else None)


def word(move, c, p, cpow=False, ppow=False):
    """The read word for one slot: `move` UP / DOWN / FLAT (or None), `c`/`p` the call / put side
    states ADD / COV / FLAT (or None), `cpow`/`ppow` whether that side is POWER. -> (word, dir)."""
    if move is None or c is None or p is None:
        return None, None
    if move == "FLAT":
        cov = [d for d, s, pw in ((1, c, cpow), (-1, p, ppow)) if pw and s == "COV"]
        if cov:
            return "PRESSURE", (cov[0] if len(cov) == 1 else 0)
        if (cpow and c == "ADD") or (ppow and p == "ADD"):
            return "WALL", 0
        return "FLAT", 0
    d = 1 if move == "UP" else -1
    fuel, back = (c, p) if d > 0 else (p, c)       # the move's own side: UP -> CE covering, PE adding
    if fuel == "COV" and back == "ADD":
        return "REAL", d
    if fuel == "COV":
        return "SQUEEZE", d
    if fuel == "ADD":
        return ("FAKE" if back == "COV" else "CAPPED"), d
    if back == "ADD":
        return "BACKED", d
    if back == "COV":
        return "HOLLOW", d
    return "QUIET", d


def _book_leg(book, t, k, side):
    """(ltp, avg, iv, vol) of one strike-side in the snapshot at mark t, or None."""
    leg = (((book or {}).get(t) or {}).get(k) or {}).get(side)
    return leg if isinstance(leg, (list, tuple)) and len(leg) >= 4 else None


def _under(book, t, ks, side):
    """How many of `ks` had ltp above their own day VWAP (avg) at mark t: the day's writers underwater."""
    legs = [_book_leg(book, t, k, side) for k in ks]
    if not ks or any(x is None or x[0] is None or x[1] is None for x in legs):
        return None
    return sum(1 for x in legs if x[0] > x[1])


def read(rows, minutes, now=None, live_from=None, opens=None, book=None, kal=None):
    """Every slot of the day, oldest first, each a flat log-ready dict (Fable §5's field names)
    plus `ce` / `pe` / `move` for the face.

    rows       ChainState.oi_flow(interval=5) -- the OI Flow tab's own marks and index print
    minutes    ChainState.minutes -- the per-strike grid those rows were read from
    now        "HH:MM": a slot ending at mark t is CLOSED once t < now; open slots are not
               returned. None = a past session, every mark closed.
    live_from  "HH:MM": marks at or before it were REBUILT by a restart (the warm start from
               the saved chain); a minute stamped src "backfill" is chain_backfill's REST
               rebuild. None = everything watched live.
    opens      {(strike, "ce"|"pe"): OI at the open} -- the top-2 ranking and turnover. None:
               ranked by the running high change alone, tagged.
    book       {"HH:MM" mark: {strike: {"ce": (ltp, avg, iv, vol), "pe": (...)}}} -- the saved
               chain snapshot at each mark. None / a missing mark: the forced chip is CAN'T CHECK.
    kal        {"ce": m, "pe": m, "ix": m, "day": d} -- the previous session's scale
               (day_scale). None: every slot with t <= 10:30 is CAN'T CHECK, said in words.
    """
    mins = sorted(t for t in (minutes or {}) if isinstance(t, str) and len(t) == 5)
    rows = sorted((r for r in rows or () if isinstance(r, dict) and r.get("time")), key=lambda r: r["time"])
    opens = opens or {}
    rp, mi = {}, 0                                     # (strike, side) -> running high change, causal

    def advance(t):
        nonlocal mi
        while mi < len(mins) and mins[mi] <= t:
            for k, v in _cells(minutes[mins[mi]]).items():
                for side, i in SI.items():
                    rp[(k, side)] = max(rp.get((k, side), v[i]), v[i])
            mi += 1

    def rec_at(t):
        best = None
        for m in mins:
            if m > t:
                break
            best = m
        return best, (minutes.get(best) if best else None)

    def top2(nine, side):
        has = all((k, side) in opens for k in nine)
        key = (lambda k: opens[(k, side)] + rp.get((k, side), 0.0)) if has else (lambda k: rp.get((k, side), 0.0))
        return sorted(nine, key=lambda k: (-key(k), abs(k)))[:2], ("open+high" if has else "high")

    hist = {"ce": [], "pe": [], "ix": []}
    armed = {1: True, -1: True}                       # the counted day (t > 10:30)
    armed_m = {1: True, -1: True}                     # B6: the morning's own, a witness never consumes the day's sign
    ep = None                                          # the current PUSHTI episode
    out = []
    for a, b in zip(rows, rows[1:]):
        t, f = b["time"], a["time"]
        if now is not None and t >= now:
            break                                      # still open: never a read of half a slot
        ma, ra = rec_at(f)
        mb, rb = rec_at(t)
        rb_f = (live_from is not None and f <= live_from) or (ra or {}).get("src") == "backfill"
        rb_t = (live_from is not None and t <= live_from) or (rb or {}).get("src") == "backfill"
        s = {"t": t, "from": f, "slot_from": ma, "slot_to": mb, "src": "backfill" if (rb_f or rb_t) else "live",
             "grid_src": "backfill" if (rb_f and rb_t) else "mixed" if (rb_f or rb_t) else "live", "tag": "I",
             "her_read": None, "leg_traded": None}
        why = []
        if _mm(t) - _mm(f) != INTERVAL:
            why.append(CC + f"the chain has no mark between {f} and {t}, so this is not a 5-minute slot")
        elif ma != f or mb != t:
            why.append(CC + f"the chain's last minute before the {t if mb != t else f} mark is "
                       f"{mb if mb != t else ma} — a hole in the feed")
        if why:
            s.update(ce=None, pe=None, move=None, word=None, dir=None, power=False, pdir=None, first=False,
                     why=why, shown=False, shown_why="gap")
            out.append(s)
            continue
        advance(t)
        A, B = _cells(ra), _cells(rb)
        ks = [k for k in B if k in A]
        dk = {k: (B[k][0] - A[k][0], B[k][1] - A[k][1]) for k in ks}
        spot = b.get("ltp")
        nine = fronts.nine(ks, spot) if spot is not None and ks else []
        d = {"ce": sum(dk[k][0] for k in nine), "pe": sum(dk[k][1] for k in nine)}
        d17 = {"ce": sum(v[0] for v in dk.values()), "pe": sum(v[1] for v in dk.values())}
        morning = t <= KAL_UNTIL
        basis = "kal_morning" if morning else "today"
        kal_ok = bool(kal) and not kal.get("expiry_day") and bool(kal.get("morning"))
        km, kd = ((kal or {}).get("morning") or {}), ((kal or {}).get("midday") or {})
        dix = None
        if t > FREEZE:
            why.append(FROZEN)
        elif spot is not None and a.get("ltp") is not None:
            dix = spot - a["ltp"]
        side = {}
        for name in ("ce", "pe"):
            i = SI[name]
            same9 = sum(1 for k in nine if dk[k][i] and _sgn(dk[k][i]) == _sgn(d[name]))
            t2, t2b = top2(nine, name)
            agree = sum(1 for k in t2 if dk[k][i] and _sgn(dk[k][i]) == _sgn(d[name]))
            m_today = _med(hist[name]) if len(hist[name]) >= WARM else None
            m_kal = km.get(name) if kal_ok else None
            scale = m_kal if morning else m_today
            st, r = _state(d[name], scale), _ratio(d[name], scale)
            power = st in ("ADD", "COV") and r is not None and r >= POWER_R and agree == 2
            oi9 = (sum(opens[(k, name)] + B[k][i] for k in nine) if nine and all((k, name) in opens for k in nine)
                   else None)
            side[name] = {"st": st, "x": _r1(r), "x_why": ("its scale is 0" if r == float("inf") else None),
                          "power": power, "d": round(d[name]), "top2": t2, "agree": agree, "n": same9,
                          "of": len(nine), "run": 0}
            s.update({f"d{name}": round(d[name]), f"d{name}17": round(d17[name]), f"M_{name}": _r1(scale),
                      f"{name[0]}_state": st, f"{name[0]}_ratio": _r1(r),
                      f"{name[0]}_ratio_today": _r1(_ratio(d[name], m_today)),
                      f"{name[0]}_ratio_kal_morning": _r1(_ratio(d[name], km.get(name))),
                      f"{name[0]}_ratio_kal_midday": _r1(_ratio(d[name], kd.get(name))),
                      f"{name[0]}_same9": same9, f"{name[0]}_power": power,
                      f"top2_{name}": t2, f"d{name}_top2": round(sum(dk[k][i] for k in t2)),
                      f"top2_{name}_agree": agree, "top2_basis": t2b,
                      f"turn_{name}": (round(abs(d[name]) / oi9, 4) if oi9 else None)})
        mi_today = _med(hist["ix"]) if len(hist["ix"]) >= WARM else None
        mi_kal = km.get("ix") if kal_ok else None
        mi_ = mi_kal if morning else mi_today
        move = None
        if dix is not None and mi_ is not None:
            move = "FLAT" if abs(dix) <= FLAT_K * mi_ else ("UP" if dix > 0 else "DOWN")
        if morning and not kal_ok:
            why.append(KAL_EXPIRY if kal and kal.get("expiry_day") else NO_KAL)
        elif side["ce"]["st"] is None or (dix is not None and mi_ is None):
            why.append(WARMING)
        c, p = side["ce"], side["pe"]
        w, wd = word(move, c["st"], p["st"], c["power"], p["power"])
        dirs = set()
        if c["power"]:
            dirs.add(1 if c["st"] == "COV" else -1)
        if p["power"]:
            dirs.add(1 if p["st"] == "ADD" else -1)
        pdir = (dirs.pop() if len(dirs) == 1 else 0) if dirs else None
        first = False
        if pdir in (1, -1):
            arm = armed_m if morning else armed
            first = arm[pdir]
            arm[pdir], arm[-pdir] = False, True
        # who paid: the fuel side is PE for a down slot, CE for an up one
        fdir = pdir if pdir in (1, -1) else (1 if move == "UP" else -1 if move == "DOWN" else None)
        fs = None if fdir is None else ("pe" if fdir < 0 else "ce")
        bs = None if fs is None else ("ce" if fs == "pe" else "pe")
        div = None
        if fs and book and book.get(t) and book.get(f):
            ivs = [(_book_leg(book, t, k, fs), _book_leg(book, f, k, fs)) for k in nine]
            ivs = [(x[2] - y[2]) * 100 for x, y in ivs if x and y and x[2] is not None and y[2] is not None]
            div = round(_med(ivs), 2) if ivs else None
            vols = [(_book_leg(book, t, k, fs), _book_leg(book, f, k, fs)) for k in nine]
            dvol = sum(x[3] - y[3] for x, y in vols if x and y and x[3] is not None and y[3] is not None)
        else:
            dvol = None
        s.update(fuel_side=fs, fuel_top2_underwater=_under(book, t, side[fs]["top2"], fs) if fs else None,
                 fuel_dIV_med=div, fuel_dVol9=dvol,
                 back_top2_underwater=_under(book, t, side[bs]["top2"], bs) if bs else None,
                 forced_why=(None if fs and book and book.get(t) else
                             (CC + "no saved chain snapshot at this mark (a REST-rebuilt minute)" if fs else None)))
        # the PUSHTI episode: opened by a first sign, replaced by the next one either way
        if first:
            fs0 = "pe" if pdir < 0 else "ce"
            ep = {"t0": t, "dir": pdir, "spot0": spot, "nine0": list(nine), "fs": fs0,
                  "build0": sum(A[k][SI[fs0]] for k in nine), "rpe0": None}
            r0 = side[fs0]["x"]
            ep["rpe0"] = round(abs(dix) / r0, 2) if dix is not None and r0 else None
        if ep:
            gone = None
            if ep["build0"] > 0:
                now_b = sum(B[k][SI[ep["fs"]]] for k in ep["nine0"] if k in B)
                gone = round((ep["build0"] - now_b) / ep["build0"] * 100)
            rx = side[ep["fs"]]["x"]
            s.update(episode_t0=ep["t0"], episode_dir=ep["dir"], min_since_first=_mm(t) - _mm(ep["t0"]),
                     pts_since_first=(round(spot - ep["spot0"], 2) if spot is not None and ep["spot0"] is not None
                                      else None),
                     fuel_build0=round(ep["build0"]), fuel_gone_pct=gone,
                     fuel_left=(None if gone is None else 100 - gone),
                     rpe0=ep["rpe0"], result_per_effort=(round(abs(dix) / rx, 2) if dix is not None and rx else None))
        else:
            s.update(episode_t0=None, episode_dir=None, min_since_first=None, pts_since_first=None,
                     fuel_build0=None, fuel_gone_pct=None, fuel_left=None, rpe0=None, result_per_effort=None)
        shown = w is not None
        s.update(ce=c, pe=p, move={"st": move, "d": (round(dix, 2) if dix is not None else None)},
                 spot=spot, dI=(round(dix, 2) if dix is not None else None), M_I=_r1(mi_), I_state=move,
                 I_ratio_today=_r1(_ratio(dix, mi_today)) if dix is not None else None,
                 I_ratio_kal_morning=_r1(_ratio(dix, km.get("ix"))) if dix is not None else None,
                 I_ratio_kal_midday=_r1(_ratio(dix, kd.get("ix"))) if dix is not None else None, M_basis=basis,
                 morning=morning, kal_day=(kal or {}).get("day"), kal_expiry_day=(kal or {}).get("expiry_day"),
                 n_nine=len(nine), nine_below_spot=sum(1 for k in nine if spot is not None and k < spot),
                 word=w, dir=wd, power=bool(c["power"] or p["power"]), pdir=pdir, first=first, why=why,
                 shown=shown, shown_why=("ok" if shown else "frozen" if FROZEN in why else "no_kal" if (NO_KAL in why or KAL_EXPIRY in why)
                                         else "warm"))
        out.append(s)
        hist["ce"].append(abs(d["ce"]))
        hist["pe"].append(abs(d["pe"]))
        if dix is not None:
            hist["ix"].append(abs(dix))
    for i, s in enumerate(out):                         # grinds: the same non-flat state, slots running
        for name in ("ce", "pe"):
            x = s.get(name)
            if x and x["st"] in ("ADD", "COV"):
                px = out[i - 1].get(name) if i else None
                x["run"] = px["run"] + 1 if px and px["st"] == x["st"] else 1
    return out


def day_scale(slots):
    """A session's scale, from its read(): {"morning": medians of |dce| |dpe| |dI| over its slots
    09:20 <= t <= 10:30, "midday": the same over from >= 10:30 and t <= 15:00}; a window with no slot
    is None. Read with kal=None is fine: the changes are computed whatever the morning could say."""
    def win(xs):
        xs = [x for x in xs if x.get("dce") is not None and x.get("dpe") is not None]
        if not xs:
            return None
        ix = [abs(x["dI"]) for x in xs if x.get("dI") is not None]
        return {"ce": _med([abs(x["dce"]) for x in xs]), "pe": _med([abs(x["dpe"]) for x in xs]),
                "ix": _med(ix), "n": len(xs)}
    xs = list(slots or ())
    return {"morning": win([x for x in xs if MORN_FROM <= x["t"] <= KAL_UNTIL]),
            "midday": win([x for x in xs if x["from"] >= KAL_FROM and x["t"] <= KAL_TO])}


def board_at(minutes, opens, t):
    """§1d's leader at mark t (board.py's rule: the earliest-peaked UNWINDING front that built today,
    else the earliest STALLED one), ranked causally by the open + running high. For the log only."""
    cut = fronts.cut(minutes, t)
    times, spots, ks, S, RP = fronts.grid(cut)
    if not times:
        return {"board_verdict": None, "board_leader_side": None, "board_leader_peak_at": None}
    pk = {}
    for (k, side), run in RP.items():
        o = (opens or {}).get((k, side.lower()))
        if o is not None:
            pk[(k, side.lower())] = o + run[-1]
    fr = [f for f in fronts.read(cut, pk or None) if f["peak"] > 0]
    unw = sorted((f for f in fr if f["state"] == fronts.UNWINDING), key=lambda f: f["peak_at"])
    stl = sorted((f for f in fr if f["state"] == fronts.STALLED), key=lambda f: f["peak_at"])
    lead = (unw or stl or [None])[0]
    return {"board_verdict": lead["state"] if lead else ("BUILDING" if fr else None),
            "board_leader_side": lead["side"] if lead else None,
            "board_leader_peak_at": lead["peak_at"] if lead else None}


def outcome(minutes, t, pdir, live_from=None):
    """f15 / f30 (index points from mark t) and, for a POWER direction, the best and worst excursion in
    that direction over (t, t+30] on the 1-minute grid. Read once by the live process at t+30."""
    mins = sorted(m for m in minutes or {} if isinstance(m, str) and len(m) == 5)
    sp = {m: (minutes[m] or {}).get("spot") for m in mins}
    at = lambda x: next((sp[m] for m in reversed(mins) if m <= x and sp[m] is not None), None)
    s0 = at(t)
    t15, t30 = _hm(_mm(t) + 15), _hm(_mm(t) + 30)
    out = {"kind": "outcome", "t": t, "f15": None, "f30": None, "mfe30": None, "mae30": None,
           "outcome_src": "live" if live_from is None or t > live_from else "backfill", "outcome_why": None}
    if s0 is None:
        out["outcome_why"] = CC + "no index print at the mark"
        return out
    if t15 <= FREEZE and at(t15) is not None:
        out["f15"] = round(at(t15) - s0, 2)
    if t30 <= FREEZE and at(t30) is not None:
        out["f30"] = round(at(t30) - s0, 2)
    if t30 > FREEZE:
        out["outcome_why"] = "15:15 se check nahi — the window crosses the auction freeze"
    if pdir in (1, -1):
        ex = [pdir * (sp[m] - s0) for m in mins if t < m <= min(t30, FREEZE) and sp[m] is not None]
        if ex:
            out["mfe30"], out["mae30"] = round(max(ex), 2), round(min(ex), 2)
    return out


def _majority(vals):
    best = Counter(v for v in vals if v).most_common()
    return best[0][0] if best and (len(best) == 1 or best[0][1] > best[1][1]) else None


def cross_at(by_idx, t):
    """The indices at slot t. n_power: most indices POWER the same way (all three). n_weekly_power: the
    weekly books (NIFTY, SENSEX) POWER the same way, in their own direction `weekly_dir` -- Mary's
    count, 2026-10-04. bn_power: BANKNIFTY's POWER direction (0 quiet), a witness never counted there."""
    cells = {i: next((s for s in (by_idx or {}).get(i) or [] if s["t"] == t), None) for i in IDXS}
    pw = {i: (s["pdir"] if s and s["power"] and s["pdir"] in (1, -1) else 0) for i, s in cells.items() if s and s.get("ce")}
    d = _majority(pw.values())
    dw = _majority(pw.get(i, 0) for i in WEEKLY)
    words = Counter((s["word"], s["dir"]) for s in cells.values() if s and s.get("word"))
    n3 = sum(1 for v in pw.values() if d and v == d)
    nw = sum(1 for i in WEEKLY if dw and pw.get(i) == dw)
    morning = t <= KAL_UNTIL                       # B4: a morning POWER slot is a witness, never a vote
    return {"n_power": 0 if morning else n3, "power_dir": d,
            "n_weekly_power": 0 if morning else nw, "weekly_dir": dw,
            "n_power_witness": n3 if morning else 0, "n_weekly_power_witness": nw if morning else 0,
            "morning_witness": morning,
            "bn_power": pw.get("BANKNIFTY"), "same_word": (words.most_common(1)[0][1] if words else 0),
            "n_read": len(pw)}


def _grind(s):
    """'PE likh rahe 6 slots se' for the side with the longer run, or 'flat' -- never QUIET, never blank."""
    runs = [(x["run"], n) for n, x in (("CE", s.get("ce")), ("PE", s.get("pe"))) if x and x["run"]]
    if not runs:
        return "dono taraf flat"
    r, n = max(runs)
    st = (s["ce"] if n == "CE" else s["pe"])["st"]
    return f"{n} {HI[st]} {r} slot{'s' if r > 1 else ''} se"


def three(by_idx, meta=None):
    """The indices at their newest COMMON closed slot, as Fable §6's two lines, in both count models:
    `line1_weekly` / `line2_weekly` / `dir_weekly` count the weekly books NIFTY + SENSEX (0/1/2) with
    BANKNIFTY a tagged witness, shown and never counted -- Mary's decision, 2026-10-04, the default;
    `line1` / `line2` / `dir_three` count all three. `meta` {idx: {"dte", "expiry_day"}}. A missing or
    stale index never agrees and never carries a read across a hole."""
    meta = meta or {}
    last = {i: s[-1]["t"] for i, s in (by_idx or {}).items() if s}
    missing = {i: CC + "no closed slot from this index" for i in IDXS if i not in last}
    if not last:
        none = CC + "no index has a closed slot yet"
        return {"t": None, "line1": none, "line1_weekly": none, "line2": None, "line2_weekly": None,
                "dir": None, "dir_three": None, "dir_weekly": None, "missing": missing, "tags": [], "tag": "I"}
    newest = max(_mm(t) for t in last.values())
    for i, t in last.items():
        if _mm(t) < newest - INTERVAL:
            missing[i] = CC + f"its chain stopped at {t}"
    live = [i for i in IDXS if i in last and i not in missing]
    T = min(last[i] for i in live)
    cells = {}
    for i in live:
        s = next((x for x in by_idx[i] if x["t"] == T), None)
        if s is None or not s.get("ce") or s["ce"]["st"] is None:
            missing[i] = (s["why"][0] if s and s["why"] else CC + f"no {T} slot")
            continue
        cells[i] = s
    cx = cross_at({i: by_idx[i] for i in cells}, T)
    D3, Dw = cx["power_dir"], cx["weekly_dir"]
    morning = cx["morning_witness"]

    def dte(i):
        return (meta.get(i) or {}).get("dte")

    def tagged(i):
        if i == "BANKNIFTY":
            return "BANKNIFTY (monthly" + (f" · {dte(i)} DTE" if dte(i) is not None else "") + ")"
        return f"{i} ({dte(i)}DTE)" if dte(i) is not None and dte(i) <= 1 else i

    def xof(s):
        return max((s[n]["x"] or 0) for n in ("ce", "pe") if s[n]["power"])

    def book(i, D):
        s = cells.get(i)
        if s is None:
            return f"{tagged(i)} check nahi"
        if not (s["power"] and s["pdir"] == D):
            return f"{tagged(i)} {'ulta' if s['power'] and s['pdir'] == -D else 'chup'}"
        u = s.get("fuel_top2_underwater")
        return (f"{tagged(i)} ×{xof(s):.0f}" + (f" · forced {u}/2" if u is not None else "")
                + (f" · pushti {s['episode_t0']}" if s.get("episode_t0") and s.get("episode_dir") == D else ""))

    def act(D, members):
        acts = Counter((n, cells[i][n]["st"]) for i in members if i in cells for n in ("ce", "pe")
                       if cells[i]["power"] and cells[i]["pdir"] == D and cells[i][n]["power"])
        return ACTION.get(acts.most_common(1)[0][0], "") if acts else ""

    bn = cells.get("BANKNIFTY")
    bn_tag = "monthly" + (f" · {dte('BANKNIFTY')} DTE" if dte("BANKNIFTY") is not None else "")

    def witness(D):
        if bn is None:
            return f"BN check nahi · {bn_tag}"
        if bn["power"] and bn["pdir"] in (1, -1):
            how = "saath" if D and bn["pdir"] == D else "ulta" if D and bn["pdir"] == -D else ARROW[bn["pdir"]]
            return f"BN {how} ×{xof(bn):.0f} · {bn_tag} · gina nahi"
        return f"BN {'chup' if D else _grind(bn)} · {bn_tag}"

    if D3:
        cnt3 = f"subah: {cx['n_power_witness']} of 3 witness, gina nahi" if morning else f"{cx['n_power']} of 3"
        line1 = f"{ARROW[D3]} {act(D3, IDXS)} · {cnt3} · " + " · ".join(book(i, D3) for i in IDXS)
    else:
        line1 = "koi power nahi · " + " · ".join(f"{i}: {_grind(cells[i])}" if i in cells else f"{i}: check nahi"
                                                 for i in IDXS)
    if Dw:
        cntw = (f"subah: NIFTY+SENSEX {cx['n_weekly_power_witness']}/2 witness, gina nahi" if morning
                else f"NIFTY+SENSEX {cx['n_weekly_power']}/2")
        line1_weekly = (f"{ARROW[Dw]} {act(Dw, WEEKLY)} · {cntw} · "
                        + " · ".join(book(i, Dw) for i in WEEKLY) + " · " + witness(Dw))
    else:
        line1_weekly = ("koi power nahi · " + " · ".join(f"{i}: {_grind(cells[i])}" if i in cells else f"{i}: check nahi"
                                                         for i in WEEKLY) + " · " + witness(None))

    def episode_line(members):
        eps = [(by_idx[i][-1].get("episode_t0"), i) for i in members if i in cells and by_idx[i][-1].get("episode_t0")]
        if not eps:
            return None
        t0, lead = max(eps)
        s = cells[lead]
        bits = [f"{lead} pushti {ARROW.get(s['episode_dir'], '')} {t0}", f"{s['min_since_first']} min",
                (f"{s['pts_since_first']:+.0f} pts" if s.get("pts_since_first") is not None else "pts ?"),
                (f"fuel {s['fuel_gone_pct']}% gaya" if s.get("fuel_gone_pct") is not None else "fuel: no build at the pushti")]
        if s.get("rpe0") is not None and s.get("result_per_effort") is not None:
            bits.append(f"asar {s['rpe0']:.0f} → {s['result_per_effort']:.0f} pts per ×")
        back = "ce" if s["episode_dir"] == -1 else "pe"
        bx = s[back]
        if bx["st"] in ("ADD", "COV"):
            bits.append(f"{back.upper()} {HI[bx['st']]} ×{bx['x'] or 0:.1f}"
                        + (" (chhat banti)" if back == "ce" and bx["st"] == "ADD" else
                           " (floor banta)" if back == "pe" and bx["st"] == "ADD" else ""))
        return " · ".join(bits)

    tags = []
    if T <= KAL_UNTIL:
        tags.append(MORNING_TAG)
        why_k = sorted({x for s in cells.values() for x in s["why"] if x in (NO_KAL, KAL_EXPIRY)})
        tags += [f"{', '.join(i for i, s in cells.items() if w in s['why'])}: {w[len(CC):]}" for w in why_k]
    exp = [i for i in IDXS if (meta.get(i) or {}).get("expiry_day")]
    if exp:
        tags.append("expiry din · " + ", ".join(exp))
    if any(FROZEN in s["why"] for s in cells.values()):
        tags.append("15:15 se check nahi · cash auction")
    if any(s["src"] == "backfill" for s in cells.values()):
        tags.append(f"{T}: rebuilt after a restart (backfill)")
    return {"t": T, "line1": line1, "line1_weekly": line1_weekly,
            "line2": episode_line(IDXS), "line2_weekly": episode_line(WEEKLY),
            "dir": None if morning else Dw, "dir_three": None if morning else D3,
            "dir_weekly": None if morning else Dw, "dir_witness": Dw if morning else None, "morning": morning,
            "n_power": cx["n_power"], "n_weekly_power": cx["n_weekly_power"], "bn_power": cx["bn_power"],
            "n_power_witness": cx["n_power_witness"], "n_weekly_power_witness": cx["n_weekly_power_witness"],
            "missing": missing, "tags": tags, "tag": "I"}
