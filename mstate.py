"""mstate.py -- JARVIS MARKET STATE: the state word with memory per index (TREND ▲ / TREND ▼ / RANGE), the volatility
state, the zone card and the cross-index read. Spec docs/superpowers/specs/2026-11-06-jarvis-market-state-design.md
(approved 6 Nov 2026); plan docs/superpowers/plans/2026-11-06-jarvis-market-state.md.

STRUCTURE (spec §3) reuses reader.py's leg engine -- pivots confirmed on closes -- fed Jarvis's 3-minute bars (the
frame's futures; SENSEX's spot, §1q), its reversal decode.py's size at each close (max of 50 NIFTY-equivalent points,
0.5 x the IV-priced 30-min sigma). reader's own auction (`au`) is NOT the word: it breaks live on a minute's low and
flips straight to the opposite trend; the spec's trend ends only at her §1e close rule or her §1m "gave up".
  TREND ▲      a close confirmed a higher low after a higher high (or after the day's first high while a legs.py TREND ▲
               leg is live: the leg was the break). The line is the latest HL. TREND ▼ mirrors it.
  ends         the first of: a 3-min close past the line by more than one median 1-min candle (§1e), or the trend-side
               front UNWINDING with spot on its writers' losing side by 0.25U (hold2.losing, §1m) -> RANGE.
  unconfirmed  a legs.py TREND leg with no pullback held yet reads "TREND ▲ (leg, unconfirmed)" -- unless efficiency
               (net move / path over EFF_WIN min) < EFF_RANGE with >= VWAP_X VWAP returns: RANGE. A leg whose trend just
               ended never comes back as unconfirmed (it must be a new leg).
Pure: no I/O but norm() (the prior sessions' bars, read only), no clock. Causal: row i reads minutes <= i only. Counts, never a %. DISPLAY ONLY: no gate, no order path;
her §1d gate is not touched (phase 4 is a registration she signs)."""
from __future__ import annotations

import functools
import os
import statistics

import decode
import fold as _fold
import fronts
import hold2
import legs
import reader
import thresholds

START_M = 555                 # 09:15: her 3-min bars count from here (legs.START_M)
ARR = {1: "▲", -1: "▼"}
EFF_WIN = 45                  # [I] efficiency = |net move| / path of the 1-min closes over the last 45 min (spec §3)
EFF_RANGE = 0.3               # [I] an unconfirmed TREND leg reads RANGE at efficiency < 0.3 ...
VWAP_X = 2                    # [I] ... with >= 2 VWAP returns (fut crossing its VWAP) in those 45 min
NORM_N = 10                   # [I] the bar-range yardstick: the same 3-min slot's median range over the last 10 sessions
NORM_MIN = 5                  # [I] ... read only with >= 5 of them on the record (fewer: could not check)
RANGE_HI, RANGE_LO = 1.5, 0.67  # [I] a bar >= 1.5x its slot's median votes EXPANDING, <= 0.67x CONTRACTING
GAUGE_WIN = 15                # [I] the straddle / VIX / IV gauges read their change over the last 15 min
VIX_PTS = 0.3                 # [I] India VIX up >= 0.3 in 15 min votes EXPANDING, down >= 0.3 CONTRACTING
IV_PTS = 0.5                  # [I] ATM IV up >= 0.5 vol points in 15 min votes EXPANDING, down >= 0.5 CONTRACTING
VOL_N = 2                     # [I] EXPANDING / CONTRACTING needs 2 gauges that way (and more than the other way) ...
VOL_CLOSES = 2                # [I] ... at 2 consecutive 3-min closes (spec §4); the day's first close says it at once
HING = {"TREND ▲": "upar ka trend", "TREND ▼": "neeche ka trend", "RANGE": "range: dono taraf",
        "OPENING": "abhi swing nahi"}  # her Hinglish chips (symbols need Hinglish chips)

_I = ("EFF_WIN", "EFF_RANGE", "VWAP_X", "NORM_N", "NORM_MIN", "RANGE_HI", "RANGE_LO", "GAUGE_WIN", "VIX_PTS", "IV_PTS",
      "VOL_N", "VOL_CLOSES")
_DEF = {n: globals()[n] for n in _I}
_APPLIED = [None]
_fmt = legs._fmt


def _thresholds():
    """The [I] numbers from jarvis_thresholds.json ("mstate.<NAME>"), applied again only when the file changed."""
    st = thresholds.stamp()
    if st != _APPLIED[0]:
        globals().update({n: thresholds.get(f"mstate.{n}", v) for n, v in _DEF.items()})
        _APPLIED[0] = st


_thresholds()


def _m(t):
    return int(t[:2]) * 60 + int(t[3:5])


def _hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def _series(d):
    """The frame's price for structure -> (close, high, low, "fut" | "spot"): SENSEX on its spot (§1q), the rest on
    their futures' 1-min bars."""
    import sensex_flow
    if sensex_flow.on(d.get("idx")):
        return d["spot"], d["spot"], d["spot"], "spot"
    return d["fut"], d.get("fhi") or d["fut"], d.get("flo") or d["fut"], "fut"


def _opt(d, t, back=3):
    """The chain's ATM read (ctx.opt) at minute t, else the last within `back` min carrying an IV, else None."""
    o = (d.get("ctx") or {}).get("opt") or {}
    ks = [k for k in o if k <= t and _m(t) - _m(k) <= back and o[k].get("iv") is not None]
    return o[max(ks)] if ks else None


def _thr(d, i, c):
    """decode.zz_thr's reversal at minute i: max(50 pts NIFTY-equivalent, 0.5 x the IV-priced 30-min sigma) [I], the
    IV the chain's ATM IV at or just before i; none -> the floor alone (decode's own fallback)."""
    o = _opt(d, d["mins"][i])
    s30 = d["spot"][i] * o["iv"] / 100 / 365 ** 0.5 * (365 * 30 / (252 * 375)) ** 0.5 if o else 0.0
    return max(decode.ZZ_PCT * c, decode.ZZ_SIG * s30)


def _pivot(piv, kind, px, t, known):
    """Append a pivot labelled against the last one of its kind: HH / LH, HL / LL (the day's first: H or L)."""
    prev = next((p for p in reversed(piv) if p["kind"] == kind), None)
    lab = kind if prev is None else ({"H": "HH", "L": "HL"} if px > prev["px"] else {"H": "LH", "L": "LL"})[kind]
    p = {"kind": kind, "lab": lab, "px": round(px, 2), "t": t, "known": known}
    piv.append(p)
    return p


def _confirms(piv, live):
    """TREND from the pivots, read at a close that confirmed a new one -> 1 / -1 / None. ▲: the newest pivot is an HL
    and the one before it an HH -- or the day's first H while a legs.py TREND ▲ leg is live (`live`). ▼ mirrors."""
    if len(piv) < 2:
        return None
    p, q = piv[-1], piv[-2]
    for D, low, high, qk in ((1, "HL", "HH", "H"), (-1, "LH", "LL", "L")):
        if p["lab"] == low and q["kind"] == qk and (q["lab"] == high or (q["lab"] == qk and live == D)):
            return D
    return None


def _gave_up(d, i, D):
    """Her §1m "gave up" at the close ending minute i for a trend D -> the why, or None: the trend-side front (▲: PE,
    ▼: CE; fronts.side_front of the minute's fronts) UNWINDING with spot on its writers' losing side of the spot at the
    front's peak minute by more than 0.25U (hold2.losing; U = max(the frame's VWAP sigma, 0.1 % of spot), legs.U_at's)."""
    side = "PE" if D > 0 else "CE"
    f = fronts.side_front(((d.get("timeline") or [{}] * (i + 1))[i] or {}).get("fronts"), side)
    if not f or f.get("state") != fronts.UNWINDING or f.get("peak_at") not in d["mins"]:
        return None
    j, spot = d["mins"].index(f["peak_at"]), d["spot"][i]
    U = max(d["sd"][i] or 0.0, 0.001 * spot)
    if hold2.losing(D, spot, d["spot"][j], U) != "lose":
        return None
    return (f"writers gave up: {_fmt(f['k'])}s {side} UNWINDING, spot {_fmt(spot)} past their {f['peak_at']} spot "
            f"{_fmt(d['spot'][j])} by more than 0.25U")


def _eff(C, fut, vw, i):
    """(efficiency, VWAP returns) over the last EFF_WIN frame minutes: |net| / path of the closes, and how often the
    future crossed its VWAP; (None, 0) before EFF_WIN minutes or on a flat path."""
    j = i - EFF_WIN
    if j < 0:
        return None, 0
    path = sum(abs(C[k] - C[k - 1]) for k in range(j + 1, i + 1))
    sg = [1 if f >= w else -1 for f, w in zip(fut[j:i + 1], vw[j:i + 1]) if f is not None and w is not None]
    return (round(abs(C[i] - C[j]) / path, 2) if path else None), sum(1 for a, b in zip(sg, sg[1:]) if a != b)


def norm(idx, day):
    """The bar-range yardstick -> ({3-min slot: the median high - low of that slot's futures bar over the last NORM_N
    sessions before `day`}, the days used): the futures' 1-min sessions on the record (data/backtest via
    confluence_log.session, the zone machine's own series). Read only; cached per (idx, day, the backtest dir)."""
    import squeeze_score
    return _norm(idx, day, squeeze_score.BT, NORM_N)


@functools.lru_cache(maxsize=16)
def _norm(idx, day, bt, n):
    import confluence_log
    import squeeze_score
    prev = sorted(x for x in (os.path.basename(p)[4:14] for p in squeeze_score._paths(idx)) if x < day)[-n:]
    by, used = {}, []
    for x in prev:
        s = confluence_log.session(idx, x)
        if not s:
            continue
        used.append(x)
        for b in s["bars"]:
            by.setdefault((_m(b["t"]) - START_M) // 3, []).append(b["h"] - b["l"])
    return {k: statistics.median(v) for k, v in by.items()}, tuple(used)


def gauges(d, i, chain=None, nm=None):
    """The five volatility gauges at the 3-min close ending at minute i (spec §4) -> [{"k", "vote", "text"}]; vote +1
    EXPANDING, -1 CONTRACTING, 0 neither, None could not check (its text says why). `chain` = the dict jarvis._legs builds for legs.read:
    {HH:MM: {"spot", "ce": {k: {"ltp", "delta"}}, "pe": ...}}; `nm` = norm()'s pair."""
    import jarvis
    mins, t = d["mins"], d["mins"][i]
    m, step, G = _m(t), d.get("step") or 50, []
    t0 = _hm(m - GAUGE_WIN)
    js = [j for j in range(max(0, i - 2), i + 1) if _m(mins[j]) >= m - 2]
    hi = max(d.get("fhi", [None] * (i + 1))[j] or d["fut"][j] for j in js)
    lo = min(d.get("flo", [None] * (i + 1))[j] or d["fut"][j] for j in js)
    slots, used = nm or ({}, ())
    med = slots.get((m - START_M) // 3)
    if len(used) < NORM_MIN or not med:
        G.append({"k": "range", "vote": None, "text": f"bar range: could not check — {len(used)} prior sessions on the "
                                                       f"record (needs {NORM_MIN})"})
    else:
        x = (hi - lo) / med
        G.append({"k": "range", "vote": 1 if x >= RANGE_HI else -1 if x <= RANGE_LO else 0,
                  "text": f"3-min range {hi - lo:.0f} pts = {x:.1f}× its {_hm(m - 2)} median ({len(used)} sessions)"
                          + (" · SENSEX fut: patla" if d.get("idx") == "SENSEX" else "")})
    a, b = (chain or {}).get(t0), (chain or {}).get(t)
    k0 = None if not a else round(a["spot"] / step) * step
    ls = [legs._chain_leg(chain, x, s, k0)[0] for x in (t0, t) for s in ("ce", "pe")] if a and b else []
    if not ls or any(not g or g.get("ltp") is None for g in ls):
        G.append({"k": "straddle", "vote": None, "text": f"straddle: could not check — no ATM premium at {t0} and {t}"})
    else:
        s0, s1, mv = ls[0]["ltp"] + ls[1]["ltp"], ls[2]["ltp"] + ls[3]["ltp"], abs(b["spot"] - a["spot"])
        G.append({"k": "straddle", "vote": 1 if s1 > s0 else -1 if mv < step / 2 else 0,
                  "text": f"{_fmt(k0)}s straddle {s0:.1f} → {s1:.1f} in {GAUGE_WIN} min, spot moved {mv:.0f} (no theta on "
                          "the record: a rise is net of decay; a fall counts only with spot inside half a step)"})
    vx = [x for x in (d.get("ctx") or {}).get("vix") or () if x[0] <= t]
    v0 = next((x for x in reversed(vx) if x[0] <= t0), None)
    if not vx or not v0:
        G.append({"k": "vix", "vote": None, "text": f"VIX: could not check — no row at or before {t0}"})
    elif m - _m(vx[-1][0]) > jarvis.BLIND_MIN or m - GAUGE_WIN - _m(v0[0]) > jarvis.BLIND_MIN:   # rule 6: stale is not current
        old = vx[-1][0] if m - _m(vx[-1][0]) > jarvis.BLIND_MIN else v0[0]
        G.append({"k": "vix", "vote": None, "text": f"VIX: could not check — last row {old}"})
    else:
        ch = vx[-1][1] - v0[1]
        G.append({"k": "vix", "vote": 1 if ch >= VIX_PTS else -1 if ch <= -VIX_PTS else 0,
                  "text": f"VIX {v0[1]:.2f} → {vx[-1][1]:.2f} ({ch:+.2f}) in {GAUGE_WIN} min"
                          + (" (backfilled)" if vx[-1][2] == "backfill" else "")})
    o1, o0 = _opt(d, t, jarvis.BLIND_MIN), _opt(d, t0, jarvis.BLIND_MIN)
    if not o1 or not o0:
        G.append({"k": "iv", "vote": None, "text": f"ATM IV: could not check — no chain IV at {t0} and {t}"})
    else:
        ch = o1["iv"] - o0["iv"]
        G.append({"k": "iv", "vote": 1 if ch >= IV_PTS else -1 if ch <= -IV_PTS else 0,
                  "text": f"ATM IV {o0['iv']:.1f} → {o1['iv']:.1f} ({ch:+.1f}) in {GAUGE_WIN} min"})
    ce, pe = [((d.get(k) or [])[i:i + 1] or [None])[0] for k in ("wf_ce", "wf_pe")]
    if ce is None or pe is None:
        G.append({"k": "raftaar", "vote": None, "text": "writers ±7: could not check — chain not read this minute"})
    else:
        p = jarvis.wf_push(ce, pe)
        both = ce >= jarvis.WF_L and pe >= jarvis.WF_L
        G.append({"k": "raftaar", "vote": 1 if p else -1 if both else 0,
                  "text": (f"writers ±7: {'call' if p > 0 else 'put'} writers running" if p else
                           "writers ±7: both sides adding" if both else "writers ±7: neither running")
                          + f" (CE {ce:+.1f}L · PE {pe:+.1f}L / 3 min)"})
    return G


def chip(row):
    """The state word's Hinglish chip with its number: "upar ka trend · 24,551" (rule: every symbol a chip)."""
    w = row["word"]
    base = ("upar ka leg, pakka nahi" if row["dir"] > 0 else "neeche ka leg, pakka nahi") \
        if w.endswith("(leg, unconfirmed)") else HING.get(w, w)
    return base + (f" · {row['line'].split()[1]}" if row.get("line") else "")


def fold(d, chain=None, nm=None):
    """The state per frame minute -> (rows, pivots). rows[i] = {"t", "word", "dir", "conf", "since", "why", "line",
    "eff", "vx", "price", "vol"}; pivots = the day's ordered swing list [{"kind", "lab", "px", "t", "known"}] (known =
    the close that confirmed it). Reads d["legs"]["rows"] for the unconfirmed leg (a frame without them has none),
    `chain` / `nm` for the volatility gauges (absent: those gauges could not check)."""
    mins = d["mins"]
    C, Hh, Ll, what = _series(d)
    LR = (d.get("legs") or {}).get("rows") or []
    eng, piv, nlegs = None, [], 0
    st = {"dir": 0, "conf": False, "line": None, "line_t": None, "why": "no swing confirmed yet", "ended": None}
    vol = {"word": None, "since": None, "up": 0, "down": 0, "read": 0, "gauges": []}
    word = since = vpend = None
    cand, out = [], []
    for i, t in enumerate(mins):
        m = _m(t)
        cand.append(abs(C[i] - C[i - 1]) if what == "spot" and i else Hh[i] - Ll[i] if what == "fut" else None)
        row = LR[i] if i < len(LR) and LR[i].get("t") == t else {}
        lg = row.get("leg") or {}
        live = lg.get("dir") if lg.get("quality") == "TREND" and row.get("lean") == lg.get("dir") else 0
        if (m - START_M) % 3 == 2:                                 # her 3-min close: the bar m-2..m is complete
            js = [j for j in range(max(0, i - 2), i + 1) if _m(mins[j]) >= m - 2]
            o = (d.get("fo") or C)[js[0]] if what == "fut" else C[max(js[0] - 1, 0)]
            bar = {"t": _fold.ms(d["day"], _hm(m - 2)), "o": o, "h": max(Hh[j] for j in js),
                   "l": min(Ll[j] for j in js), "c": C[i], "vol": 0.0, "oi": None}
            thr = _thr(d, i, C[i])
            if eng is None:
                eng = reader.Engine(idx=d.get("idx") or "?", day=d["day"], lot=1, unit=thr / reader.TH["K"])
            eng.delta = thr            # decode's size at this close (reader freezes its ruler at the open; spec §3: per close)
            for x in reader.canonical([], [bar]):
                eng.step(x)
            new = []
            for leg in eng.legs[nlegs:]:
                if not piv:                                        # the day's first leg: its start is a pivot too
                    new.append(_pivot(piv, "L" if leg["dir"] > 0 else "H", leg["px0"], reader.hm(leg["t0"]), t))
                new.append(_pivot(piv, "H" if leg["dir"] > 0 else "L", leg["px1"], reader.hm(leg["t1"]), t))
            nlegs = len(eng.legs)
            if st["conf"]:                                         # conf needs earlier closes, so cand is never empty here
                one = statistics.median([x for x in cand if x is not None])  # one median 1-min candle (her §1e)
                D = st["dir"]
                for p in new:                                      # a new HL (LH) carries the line
                    if p["lab"] == ("HL" if D > 0 else "LH") and D * (p["px"] - st["line"]) > 0:
                        st.update(line=p["px"], line_t=p["t"])
                end = (f"structure: a 3-min close {_fmt(C[i])} {'below' if D > 0 else 'above'} the "
                       f"{'HL' if D > 0 else 'LH'} {_fmt(st['line'])} ({st['line_t']}) by more than one 1-min candle "
                       f"({one:.1f})") if D * (C[i] - st["line"]) < -one else _gave_up(d, i, D)
                if end:
                    st.update(dir=0, conf=False, line=None, line_t=None, why=end, ended=(D, lg.get("origin_t")))
            elif new:
                D = _confirms(piv, live)
                if D:
                    p, q = piv[-1], piv[-2]
                    st.update(dir=D, conf=True, line=p["px"], line_t=p["t"], ended=None,
                              why=f"TREND {ARR[D]}: {q['lab']} {_fmt(q['px'])} ({q['t']}) then {p['lab']} "
                                  f"{_fmt(p['px'])} ({p['t']}) held")
            G = gauges(d, i, chain, nm)
            up, dn = sum(g["vote"] == 1 for g in G), sum(g["vote"] == -1 for g in G)
            rd = sum(g["vote"] is not None for g in G)
            cv = "?" if rd < VOL_N else "EXPANDING" if up >= VOL_N and up > dn else \
                "CONTRACTING" if dn >= VOL_N and dn > up else "NORMAL"
            vpend = None if cv == vol["word"] else [cv, vpend[1] + 1 if vpend and vpend[0] == cv else 1]
            if vpend and (vol["word"] is None or vpend[1] >= VOL_CLOSES):
                vol, vpend = dict(vol, word=cv, since=t), None
            vol = dict(vol, up=up, down=dn, read=rd, gauges=G)
        eff, vx = _eff(C, d["fut"], d["vwap"], i)
        if st["conf"]:
            D = st["dir"]
            w, why = f"TREND {ARR[D]}", st["why"]
            line = f"line {_fmt(st['line'])} ({'HL' if D > 0 else 'LH'} {st['line_t']})"
        elif live and (live, lg.get("origin_t")) != st["ended"]:
            D, line = live, f"line {_fmt(lg['origin'])} (origin {lg.get('origin_t')})"
            if eff is not None and eff < EFF_RANGE and vx >= VWAP_X:
                w, D = "RANGE", 0
                why = f"RANGE: a TREND leg, but efficiency {eff:.2f} with {vx} VWAP returns in {EFF_WIN} min"
            else:
                w = f"TREND {ARR[live]} (leg, unconfirmed)"
                why = (f"a TREND leg {lg.get('pts')} pts from {_fmt(lg['origin'])} ({lg.get('origin_t')}): "
                       "no pullback has held yet")
        elif not piv and word in (None, "OPENING"):                # never back to OPENING once a word was said
            w, D, line, why = "OPENING", 0, None, "OPENING: no swing confirmed yet and no TREND leg"
        else:
            w, D, line = "RANGE", 0, None
            why = st["why"] if st["why"].startswith(("structure", "writers")) else \
                "RANGE: overlapping swings " + " ".join(p["lab"] for p in piv[-4:])
        if w != word:
            word, since = w, t
        out.append({"t": t, "word": w, "dir": D, "conf": st["conf"], "since": since, "why": why, "line": line,
                    "eff": eff, "vx": vx, "price": what, "vol": vol})
    return out, piv
