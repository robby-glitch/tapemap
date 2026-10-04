"""trap.py -- the trap layer: level -> dwell -> induce -> failure -> release -> travel. SHADOW.

Her thesis (2026-08-22): price is walked to a retail reaction point, left there while
retail loads, the stops become liquidity, and the move runs to the next reaction point.
Fable's framework (docs/board/FABLE-TRAP-FRAMEWORK-2026-10-04.md) turned it into a
checklist; the rules here are PRE-REGISTERED in docs/board/TRAP-PREREG-2026-10-04.md
(rev trap-1, fixed 2026-10-04 02:11 IST, before any trap was read against outcomes).
DO NOT TUNE: a change is a new revision with its own date, written in that file first.

JOIN, NOT RE-IMPLEMENTATION. Every state comes from a machine that already runs:
  * levels.py lists the levels; sequence.py (warmap's machine) stamps APPROACH / DWELL /
    BREAK / RUN / HIT / FAILED / REJECT at them; dwell.py's band and 300 s make DWELL --
    this file reads those stamps (`data/warmap/`), it never re-detects a level event;
  * sides.py (rev sides-3) gives each 5-min slot's POWER, direction, forced chip and the
    top-2-by-OI fronts' changes -- the release and the loaded side are read from it;
  * reader.py's legs give WHO on the release leg; xindex.py's X2 / X3 give the
    cross-index extremes at an induce; the recorders give the tape, pulled quotes and
    yesterday's book.
States: REACHED · DWELL · INDUCED · FAILED · RELEASED · TRAVELLING (prereg §1).

Display [I] on [M] stamps. Nothing here gates anything, re-words a sides read, changes a
count or the headline. f15 / f30 are logged, never shown. Pure: stdlib only, NO I/O,
NO clock; the caller hands every input in, already parsed (sides_log / trap_log do I/O).
"""
from __future__ import annotations

REV = "trap-1"
FIXED_AT = "2026-10-04 02:11 IST"
STATIC = ("PDH", "PDL", "PDC", "PWH", "PWL", "OPEN")
GAP_KINDS = ("PDH", "PDL", "PWH", "PWL")             # PDC is the reference, OPEN is today's
MAJOR = {"NIFTY": 100, "BANKNIFTY": 500, "SENSEX": 500}   # levels.ROUND_STEPS' major grid
WEEKLY_TAPE = ("NIFTY",)                             # the only futures tape thick enough to read
CC = "could not check — "
HI_ST = {"ADD": "likh", "COV": "kaat", "FLAT": "flat"}   # sides' states in her words (Board.tsx SIDE_HI)
TAPE_THIN = "check nahi — futures tape patla (~4 lots/min)"
ARROW = {1: "▲", -1: "▼"}
WAY = {1: "upar", -1: "neeche"}
WHO_WORD = {"new_longs": "chalega", "new_shorts": "chalega", "short_covering": "agle level tak",
            "long_liquidation": "agle level tak", "rotation": "OI flat", "oi_cant": "check nahi"}
STATE_HI = {"REACHED": "pahuncha", "DWELL": "ruka", "INDUCED": "toota", "FAILED": "fail hua",
            "RELEASED": "chhoota", "TRAVELLING": "chal pada"}


def _mm(t):
    return int(t[:2]) * 60 + int(t[3:5])


def _hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _L(x):
    return f"{x / 1e5:+.1f}L"


def level_key(kind, px):
    return f"{kind}@{px:.1f}"


def in_set(idx, kind, px):
    """prereg §1: the static levels and the MAJOR round grid only."""
    if kind in STATIC:
        return True
    return kind == "ROUND" and px is not None and abs(px / MAJOR.get(idx, 500) - round(px / MAJOR.get(idx, 500))) < 1e-9


def _stamps(idx, rows):
    """warmap rows for this index, in the level set, oldest first, with t = 'HH:MM:SS'."""
    out = []
    for r in rows or ():
        if r.get("idx", idx) != idx or not in_set(idx, r.get("level"), r.get("px")):
            continue
        ts = str(r.get("ts") or "")
        t = ts[11:19] if len(ts) >= 19 else ts[:8]
        if len(t) == 8:
            out.append(dict(r, t=t))
    out.sort(key=lambda r: r["t"])
    return out


def _at_levels(stamps, upto):
    """{key: (kind, px)} of the levels whose machine is APPROACH or DWELL after every stamp <= upto."""
    st = {}
    for r in stamps:
        if r["t"] > upto:
            break
        st[level_key(r["level"], r["px"])] = (r["to"], r["level"], r["px"])
    return {k: (v[1], v[2]) for k, v in st.items() if v[0] in ("APPROACH", "DWELL")}


def _xindex_at(xin, t, direction):
    """xindex X2 / X3 at the first 3-min bar at or after t, in the break direction."""
    if not xin:
        return {"x_why": "check nahi (xindex log nahi)"}
    row = next((x for x in xin if x.get("t") and x["t"] >= t[:5]), None)
    if row is None:
        return {"x_why": "check nahi (no xindex bar after the break yet)"}
    side = "high" if direction == "UP" else "low"
    ex = ((row.get("extremes") or {}).get(side)) or {}
    lead = row.get("lead") or {}
    return {"x_t": row["t"], "x2_verdict": ex.get("verdict"),
            "x2_per": {i: (p or {}).get("status") for i, p in (ex.get("per") or {}).items()},
            "x3_first": lead.get("first"), "x3_stamps": lead.get("stamps"), "x_why": None if ex else "no extreme at that bar"}


def _window(buckets, a, b):
    """Sum per-minute buckets {'HH:MM': {k: v}} over minutes a < m <= b (marks as 'HH:MM')."""
    out = {}
    for m in range(_mm(a) + 1, _mm(b) + 1):
        for k, v in ((buckets or {}).get(_hm(m)) or {}).items():
            out[k] = out.get(k, 0.0) + (v or 0.0)
    return out


def tape_with(idx, s, tape):
    """prereg §3: raw tape fields on a POWER slot, NIFTY only, no threshold."""
    if idx not in WEEKLY_TAPE:
        return None, TAPE_THIN
    if not tape:
        return None, CC + "no NIFTY tape record for this session"
    f, t = s["from"], s["t"]
    vp = [v for v in tape.get("vpin") or () if f + ":59" < v["at"] <= t + ":59"]
    top = max(vp, key=lambda v: abs(v["buy"] - v["sell"]), default=None)
    ux = next((u for u in tape.get("ux") or () if u["t"] == f), None)
    sw = _window(tape.get("minutes"), f, t)
    return ({"vpin_fast_max": (None if top is None else
                               {"at": top["at"], "imb": round((top["buy"] - top["sell"]) / max(top["buy"] + top["sell"], 1), 3),
                                "buy": top["buy"], "sell": top["sell"]}),
             "ux_delta": ux and ux.get("delta"), "ux_vol": ux and ux.get("vol"),
             "swept_net": (round(sw.get("swept_buy", 0.0) - sw.get("swept_sell", 0.0)) if sw else None)},
            None)


def read(idx, stamps, slots, now=None, static=None, first_print=None, legs=None, xin=None, tape=None,
         pulled=None, oi_prev=None, book=None, live_from=None):
    """The day's traps for one index.

    stamps       warmap sequence rows (any index; filtered here), live and backfill alike
    slots        sides.read() output for this index (rev sides-3)
    now          'HH:MM' -- only stamps before it and closed slots count (None: a past session)
    static       {kind: px} of today's static levels (PDC needed for the gap clause); None: from the stamps
    first_print  the session's first index print (the 09:15 mark), for the gap clause
    legs         reader legs, each {"t0": 'HH:MM', "t1": 'HH:MM', "dir": +-1, "who": class, "oi": moved}
    xin          xindex rows, each {"t": 'HH:MM', "extremes": {...}, "lead": {...}}
    tape         NIFTY only: {"vpin": [{"at": 'HH:MM:SS', "buy", "sell"}], "ux": [{"t": 'HH:MM', "delta",
                 "vol"}], "minutes": {'HH:MM': {"swept_buy", "swept_sell"}}}
    pulled       {'HH:MM': {"pulled_buy", "pulled_sell"}} on this index's future
    oi_prev      {strike: {"ce": (oi, avg, ltp), "pe": (...)}} from the previous session's last snapshot
    book         sides' {mark: {strike: {"ce": (ltp, avg, iv, vol), "pe": ...}}} -- today's ltp at a mark
    live_from    'HH:MM' marks at or before it were rebuilt by a restart (src backfill)
    """
    cut = (now + ":00") if now else "99:99:99"
    st = [r for r in _stamps(idx, stamps) if r["t"] < cut]
    slots = [s for s in slots or () if now is None or s["t"] < now]
    lvl = dict(static or {})
    for r in st:
        if r["level"] in STATIC:
            lvl.setdefault(r["level"], r["px"])
    traps, events = {}, []

    def trap(kind, px):
        k = level_key(kind, px)
        if k not in traps:
            traps[k] = {"key": k, "kind": kind, "px": px, "reached": None, "tests": 0, "dwells": [], "induced": [],
                        "failed": [], "rejects": 0, "released": [], "gap": None, "sum_ce": 0.0, "sum_pe": 0.0,
                        "last": None, "last_t": None}
        return traps[k]

    def ev(T, state, t, src, **kw):
        row = {"kind": "state", "t": t, "level": T["kind"], "px": T["px"], "state": state, "src": src, "tag": "I", **kw}
        events.append(row)
        T["last"], T["last_t"] = state, t
        return row

    # the gap clause (prereg §1): a static level between yesterday's close and today's first print
    pdc = lvl.get("PDC")
    if pdc is not None and first_print is not None and first_print != pdc:
        gd = "DOWN" if first_print < pdc else "UP"
        gsrc = "backfill" if live_from is not None and live_from > "09:15" else "live"   # a later start rebuilt 09:15
        for kind in GAP_KINDS:
            px = lvl.get(kind)
            if px is not None and min(pdc, first_print) < px < max(pdc, first_print):
                T = trap(kind, px)
                T["reached"], T["gap"] = "09:15:00", gd
                ev(T, "REACHED", "09:15:00", gsrc, gap=True)
                T["induced"].append({"t": "09:15:00", "dir": gd, "gap": True, "target": None})
                ev(T, "INDUCED", "09:15:00", gsrc, dir=gd, gap=True,
                   why=f"opened {'below' if gd == 'DOWN' else 'above'} {kind} {px:,.1f} (yesterday's close {pdc:,.1f}, "
                       f"first print {first_print:,.1f}) — a break between sessions")

    last_break = {}
    hits = []
    for r in st:
        T = trap(r["level"], r["px"])
        src = "backfill" if r.get("backfill") else "live"
        to = r["to"]
        if to == "APPROACH":
            if T["reached"] is None:
                T["reached"] = r["t"]
                ev(T, "REACHED", r["t"], src, side=r.get("side"))
            T["tests"] += 1
        elif to == "DWELL":
            T["dwells"].append(r["t"])
            ev(T, "DWELL", r["t"], src, oi_ce=r.get("oi_ce"), oi_pe=r.get("oi_pe"))
        elif to == "BREAK":
            d = r.get("direction")
            last_break[T["key"]] = d
            if T["gap"] and d and d != T["gap"]:
                T["failed"].append({"t": r["t"], "gap": True})
                ev(T, "FAILED", r["t"], src, gap=True, why="came back through the gap level")
            T["induced"].append({"t": r["t"], "dir": d, "gap": False, "target": None})
            ev(T, "INDUCED", r["t"], src, dir=d, **_xindex_at(xin, r["t"], d))
        elif to == "RUN" and T["induced"]:
            T["induced"][-1]["target"] = r.get("target")
        elif to == "FAILED":
            T["failed"].append({"t": r["t"], "gap": False})
            ev(T, "FAILED", r["t"], src)
        elif to == "HIT":
            hits.append({"t": r["t"], "from_level": T["key"], "dir": last_break.get(T["key"]),
                         "target": r.get("target"), "src": src})
        elif to == "REJECT":
            T["rejects"] += 1
            T["last"], T["last_t"] = "REJECT", r["t"]

    # the slots: loaded side "during the dwell", releases (R2-R5), and the per-slot rows
    rows, releases = [], []
    spot_at = {s["t"]: s.get("spot") for s in slots}
    for s in slots:
        f, t = s["from"], s["t"]
        at_open = _at_levels(st, f + ":59")
        at_close = _at_levels(st, t + ":59")
        broke_in = {level_key(r["level"], r["px"]): (r["level"], r["px"]) for r in st
                    if r["to"] == "BREAK" and f + ":59" < r["t"] <= t + ":59"}
        rel = None
        tw, tw_why = (tape_with(idx, s, tape) if s.get("power") else (None, None))
        pw_prev = _window(pulled, _hm(_mm(f) - 5), f)
        pw_slot = _window(pulled, f, t)
        unattached = None
        if s.get("power") and s.get("pdir") in (1, -1):
            cands = at_open or broke_in
            sp0 = spot_at.get(f) if spot_at.get(f) is not None else s.get("spot")
            if not cands:
                unattached = {"kind": "state", "t": t + ":00", "level": None, "px": None, "state": "release_unattached",
                              "src": s["src"], "tag": "I", "pdir": s["pdir"], "word": s.get("word"),
                              "why": "kisi trap pe nahi — price was at no level when this POWER slot opened"}
                events.append(unattached)
            else:
                k = min(cands, key=lambda q: abs(cands[q][1] - (sp0 if sp0 is not None else cands[q][1])))
                T = trap(*cands[k])
                loaded = ("ce" if T["sum_ce"] > max(T["sum_pe"], 0) else "pe" if T["sum_pe"] > max(T["sum_ce"], 0)
                          else None)
                away = -1 if loaded == "ce" else 1 if loaded == "pe" else None
                forced = s.get("fuel_top2_underwater")
                ok = loaded is not None and s["pdir"] == away and forced is not None and forced >= 1
                why = (None if ok else "koi load nahi (neither top-2 side added at the level)" if loaded is None else
                       f"POWER {ARROW[s['pdir']]} is toward the loaded side ({loaded.upper()})" if s["pdir"] != away else
                       "forced: could not check (no saved snapshot)" if forced is None else "forced 0/2 — writers in profit")
                if ok:
                    who = _who(legs, s["pdir"], f)
                    pw = [(n, s[n]) for n in ("ce", "pe") if (s.get(n) or {}).get("power")]   # the side(s) that made it POWER
                    rel = {"t": t, "from": f, "trap": T["key"], "level": T["kind"], "px": T["px"], "dir": s["pdir"],
                           "loaded": loaded, "sum_ce": round(T["sum_ce"]), "sum_pe": round(T["sum_pe"]),
                           "forced": forced, "x": max((c.get("x") or 0) for _, c in pw) if pw else None,
                           "act": " · ".join(f"{n.upper()} {HI_ST.get(c.get('st'), c.get('st'))} ×{(c.get('x') or 0):.0f}"
                                             for n, c in pw) or None, "word": s.get("word"),
                           "morning": bool(s.get("morning")), "tape_with": tw, "tape_why": tw_why, **who}
                    T["released"].append(rel)
                    releases.append(rel)
                    ev(T, "RELEASED", t + ":00", s["src"], **{k2: v for k2, v in rel.items() if k2 not in ("t", "trap")})
                else:
                    events.append({"kind": "state", "t": t + ":00", "level": T["kind"], "px": T["px"],
                                   "state": "power_not_release", "src": s["src"], "tag": "I", "pdir": s["pdir"],
                                   "loaded": loaded, "why": why})
        for k, (kind, px) in at_close.items():          # this slot is "during the dwell" for the levels price is at
            T = traps.get(k)
            if T and T["reached"] and T["reached"] <= t + ":59":
                T["sum_ce"] += s.get("dce_top2") or 0.0
                T["sum_pe"] += s.get("dpe_top2") or 0.0
        prev = _prev_fields(s, oi_prev, book)
        act = _active(at_close, traps, st, s.get("spot"), t)
        rows.append({"kind": "slot", "t": t, "from": f, "src": s["src"], "tag": "I",
                     "at": sorted(at_close), "active": act, "active_state": traps[act]["last"] if act else None,
                     "loaded_ce": round(traps[act]["sum_ce"]) if act else None,
                     "loaded_pe": round(traps[act]["sum_pe"]) if act else None,
                     "power": bool(s.get("power")), "pdir": s.get("pdir"), "release": rel is not None,
                     "release_unattached": unattached is not None, "tape_with": tw, "tape_why": tw_why,
                     "pulled_prev5_buy": pw_prev.get("pulled_buy"), "pulled_prev5_sell": pw_prev.get("pulled_sell"),
                     "pulled_slot_buy": pw_slot.get("pulled_buy"), "pulled_slot_sell": pw_slot.get("pulled_sell"),
                     **prev})
    # TRAVELLING (prereg §1): the first HIT after a release, in its direction, up to the next release
    for n, rel in enumerate(releases):
        stop = releases[n + 1]["t"] + ":00" if n + 1 < len(releases) else "99:99:99"
        dname = "UP" if rel["dir"] > 0 else "DOWN"
        chain = [h for h in hits if rel["t"] + ":00" <= h["t"] < stop and h["dir"] == dname]
        rel["travel"] = [{"t": h["t"], "target": h["target"], "src": h["src"]} for h in chain]
        if chain:
            T = traps[rel["trap"]]
            ev(T, "TRAVELLING", chain[0]["t"], chain[0]["src"], dir=dname, target=chain[0]["target"],
               who=rel.get("who"), who_word=rel.get("who_word"))
    events.sort(key=lambda e: e["t"])
    return {"rev": REV, "idx": idx, "traps": traps, "events": events, "slots": rows, "releases": releases,
            "lines": lines(idx, traps, releases, rows, st, slots), "tag": "I"}


def _who(legs, d, f):
    """prereg R6: the reader's first leg in the release direction starting at or after the slot opened."""
    if legs is None:
        return {"who": None, "who_word": "check nahi", "who_why": "check nahi (reader log nahi)"}
    g = next((x for x in sorted(legs, key=lambda x: x["t0"]) if x["dir"] == d and x["t0"] >= f), None)
    if g is None:
        return {"who": None, "who_word": "check nahi", "who_why": "no reader leg that way yet"}
    return {"who": g["who"], "who_word": WHO_WORD.get(g["who"], g["who"]), "who_leg": f"{g['t0']}–{g['t1']}",
            "who_oi": g.get("oi"), "who_why": None}


def _prev_fields(s, oi_prev, book):
    """prereg §3 oi_prev: yesterday's closing OI at today's top-2, and how many are underwater on yesterday's VWAP."""
    out = {}
    for side in ("ce", "pe"):
        t2 = (s.get(side) or {}).get("top2") or []
        if not oi_prev or not t2:
            out.update({f"prev_oi_top2_{side}": None, f"prev_underwater_{side}": None})
            continue
        legs = [((oi_prev.get(k) or {}).get(side), (((book or {}).get(s["t"]) or {}).get(k) or {}).get(side)) for k in t2]
        out[f"prev_oi_top2_{side}"] = (round(sum(p[0] for p, _ in legs)) if all(p for p, _ in legs) else None)
        out[f"prev_underwater_{side}"] = (sum(1 for p, q in legs if q[0] > p[1])
                                          if all(p and q and p[1] is not None and q[0] is not None for p, q in legs)
                                          else None)
    return out


def _active(at_close, traps, st, spot, t):
    """R1: the level price is AT (nearest to the print), else the most recently stamped level."""
    if at_close:
        return min(at_close, key=lambda k: abs(at_close[k][1] - (spot if spot is not None else at_close[k][1])))
    done = [T for T in traps.values() if T["last_t"] and T["last_t"] <= t + ":59"]
    return max(done, key=lambda T: T["last_t"])["key"] if done else None


def lines(idx, traps, releases, rows, st, slots):
    """Fable §5's three lines, for the latest closed slot."""
    if not slots:
        return {"trap": CC + "no closed slot yet", "chhoota": None, "agla": None}
    last = rows[-1]
    act = last["active"]
    if not act:
        trap_line = "koi level nahi — price abhi kisi level pe nahi pahuncha"
    else:
        T = traps[act]
        bits = [f"{T['kind']} {T['px']:,.0f} pahuncha {T['reached'][:5]}"]
        ind = T["induced"]
        if ind:
            i = ind[-1]
            bits.append(("gap se toota 09:15" if i.get("gap") else f"toota {i['t'][:5]}")
                        + f" {ARROW[1 if i['dir'] == 'UP' else -1]} {'upar' if i['dir'] == 'UP' else 'neeche'}")
        else:
            bits.append("toota nahi")
        if T["failed"]:
            bits.append(f"fail {T['failed'][-1]['t'][:5]}")
        if T["dwells"]:
            bits.append(f"ruka {len(T['dwells'])}× (pehla {T['dwells'][0][:5]})")
        bits.append(f"{T['tests']} baar aaya")
        ce, pe = T["sum_ce"], T["sum_pe"]
        if max(ce, pe) > 0:
            side = "CE" if ce >= pe else "PE"
            bits.append(f"{side} likhe {_L(max(ce, pe))} (top-2, level pe)")
        else:
            bits.append("koi load nahi")
        trap_line = " · ".join(bits)
    if releases:
        r = releases[-1]
        tw = r.get("tape_with")
        tape = (r.get("tape_why") or "") if tw is None else (
            "tape: " + " · ".join(x for x in (
                (f"VPIN {tw['vpin_fast_max']['imb']:+.2f}" if tw.get("vpin_fast_max") else None),
                (f"UX Δ {tw['ux_delta']:+.0f}" if tw.get("ux_delta") is not None else None),
                (f"sweeps {tw['swept_net']:+,}" if tw.get("swept_net") is not None else None)) if x) or "tape: kuch nahi")
        chh = (f"{ARROW[r['dir']]} {WAY[r['dir']]} {r['t']} · {r.get('act') or '?'} · forced {r['forced']}/2"
               f" · {r['level']} {r['px']:,.0f} se · loaded {r['loaded'].upper()} · {tape}" + (" · subah witness" if r["morning"] else ""))
        trav = r.get("travel") or []
        agla_bits = [" → ".join(f"{(h['target'] or {}).get('kind', '?')} {((h['target'] or {}).get('px') or 0):,.0f} {h['t'][:5]}"
                                for h in trav[:4]) if trav else "abhi tak koi agla level nahi"]
        agla_bits.append(f"WHO {r['who_word']}" + (f" ({r['who']}, {r['who_leg']})" if r.get("who") else
                                                   f" ({r.get('who_why')})"))
        agla = " · ".join(agla_bits)
    else:
        pw = [x for x in rows if x["power"]]
        why = ("koi power nahi" if not pw else
               "power kisi trap pe nahi" if pw[-1]["release_unattached"] else "power hai, par release ki shart poori nahi")
        chh, agla = f"koi release nahi · {why}", None
    return {"trap": trap_line, "chhoota": chh, "agla": agla, "t": last["t"]}
