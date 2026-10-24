"""trademap.py -- THE TRADE MAP in the one voice (Mary 2026-10-24, "build it"; spec
docs/superpowers/specs/2026-10-24-trade-map-design.md; NOTEPAD A53-A59; why each line exists:
docs/trade-map/FABLE-CRITIQUE-2026-10-24.md). Two DESCRIPTION lines join the voice's three (voice.py):

  l4  push ▼ HH:MM (N min) · ulta push · din range X.XX EM -- her direction's latest PUSH closed since entry and the other
      side's (hold2.pushes, §1m, unchanged), the day's spot range over the 1σ EM (engine.js emOf, ported)
  l5  pullback zone Kf / Ks (N pts) · K PE OI -- the wall ahead NOW (engine.js wallNearest, ported): where the pullback
      comes, never a target; at it (spot within one step) a SURVIVOR EFFORT read only, from the DECODE block

and a [detail ▸] list (fuel pinned at entry, levels on the way, R via `into`, the seller's premium path). DISPLAY ONLY: no
state, no stop, no WARN / EXIT source, no rate, no prediction, no question. Pure: no I/O, no clock; causal (minute
`now_m` reads chain rows, 5-min bars and DECODE closes available by then). OI [M]; "trapped" [I] (OI has no side or
vintage); EM, theta and premium-at-zone [I]."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

import effort
import gamma
import hold2
import holdshadow

REV = "trademap-2 (TRADE MAP spec 2026-10-24 + A61 BADA at the zone, W-BLEED a gauge)"
EM_FROM, EM_TO = "09:20:00", "09:30:00"    # engine.js R3.EM_FROM / EM_TO
IB_END = "10:15:00"                        # the initial balance: 09:15-10:15 spot
TV_MIN = 10                                # the seller line's "10 min: prem, fut"
hm = hold2.hm


def _sec(ts):
    p = [int(x) for x in str(ts).split(":")[:3]] + [0, 0]
    return p[0] * 3600 + p[1] * 60 + p[2]


def _n(x):
    return "?" if x is None else f"{x:,.0f}"


def _L(x, nd=1):
    return "?" if x is None else f"{x / 1e5:.{nd}f}L"


def _leg(r, k, leg):
    s = next((s for s in r.get("strikes") or () if isinstance(s, dict) and s.get("k") == k), None)
    return (s or {}).get(leg) or {}


def _oi(r, k, leg):
    v = _leg(r, k, leg).get("oi")
    return v if isinstance(v, (int, float)) else None


def _step(r):
    ks = sorted({s["k"] for s in r.get("strikes") or () if isinstance(s, dict) and s.get("k") is not None})
    gaps = [b - a for a, b in zip(ks, ks[1:]) if b > a]
    return min(gaps) if gaps else None


def snaps(chain_rows, now_m):
    """The chain recorder's snapshots 09:15 -> the end of minute now_m with a spot, in time order."""
    end = (now_m + 1) * 60
    return sorted((r for r in chain_rows or () if isinstance(r, dict) and isinstance(r.get("ts"), str)
                   and "09:15:00" <= r["ts"] <= "15:30:00" and r.get("spot") is not None and _sec(r["ts"]) < end),
                  key=lambda r: r["ts"])


def weekdays(a, b):
    """engine.js weekdays: Mon-Fri from a to b, both counted; holidays not removed [I]."""
    if not a or not b or b < a:
        return None
    d0, d1 = date.fromisoformat(a), date.fromisoformat(b)
    return sum(1 for i in range((d1 - d0).days + 1) if (d0 + timedelta(i)).weekday() < 5) or None


def em(rows, day):
    """engine.js emOf: the day's 1σ = the first chain row at or after 09:20 (before 09:30), its ATM straddle / 0.8 / √N,
    N = weekdays today -> expiry. -> ({em, straddle, K, t, N} [I], None) or (None, why)."""
    r = next((r for r in rows if r["ts"] >= EM_FROM), None)
    if r is None or r["ts"] >= EM_TO:
        return None, "no chain row 09:20–09:30"
    ce, pe = _leg(r, r.get("atm"), "ce").get("ltp"), _leg(r, r.get("atm"), "pe").get("ltp")
    N = weekdays(day, r.get("expiry"))
    if ce is None or pe is None:
        return None, "no ATM straddle on the 09:20 row"
    if not N:
        return None, "no expiry"
    return {"em": (ce + pe) / 0.8 / math.sqrt(N), "straddle": ce + pe, "K": r.get("atm"), "t": r["ts"][:5], "N": N}, None


def wall_nearest(r, leg, beyond, spot):
    """engine.js wallNearest: the nearest strike beyond price on `leg` whose OI is >= 1/2 of that side's largest beyond
    price -> {k, leg, oi} or None."""
    c = {s["k"]: s[leg]["oi"] for s in r.get("strikes") or () if isinstance(s, dict) and s.get("k") is not None
         and (s["k"] > spot if beyond > 0 else s["k"] < spot) and isinstance((s.get(leg) or {}).get("oi"), (int, float))}
    if not c:
        return None
    mx = max(c.values())
    ok = sorted(k for k, v in c.items() if v >= 0.5 * mx)
    k = ok[0] if beyond > 0 else ok[-1]
    return {"k": k, "leg": leg.upper(), "oi": c[k]}


def survivor(d, dec, m):
    """The DECODE block's effort at minute m (holdshadow._dec_at: close + 1 <= m), as a survivor read only -- d < 0 cheap
    (<= 0.5x) at a fresh LOW, d > 0 expensive (>= 2x) at a fresh HIGH, the extreme within 15 min -- else None. The
    mirrors, "read nahi" and before 09:56 are None: there is no default."""
    e = (holdshadow._dec_at(dec or {}, m)[1] or {}).get("effort") or {}
    x, t = e.get("x"), holdshadow._mm(e.get("t"))
    if x is None or t is None or t < m - holdshadow.W15:
        return None
    if d < 0 and e.get("at") == "LOW" and x <= effort.LO:
        return f"EFFORT {x:g}× sasta @ naya low"
    if d > 0 and e.get("at") == "HIGH" and x >= effort.HI:
        return f"EFFORT {x:g}× mehenga @ naya high"
    return None


def bada(prints, zf, step, t0_ms, t1_ms):
    """Her extension's own BADA PRINT (decoder E1, `decoder_log.read_events`: the mark on her footprint, never a top-N)
    within one strike step of the zone's fut level, its 5-min bar closed after her entry and by now -> the latest as
    "BADA BUYER 625 lots @22,727f 13:40" [M], else None. Who stood at the level, never a verdict (A61)."""
    xs = [e for e in prints or () if e.get("kind") == "E1" and e.get("shown") and isinstance(e.get("t"), (int, float))
          and isinstance(e.get("p"), (int, float)) and t0_ms < e["t"] + 300000 <= t1_ms and abs(e["p"] - zf) <= step]
    if not xs:
        return None
    e = max(xs, key=lambda e: e["t"])
    return f"BADA {'BUYER' if (e.get('side') or 0) > 0 else 'SELLER'} {_n(e.get('lots'))} lots @{_n(e['p'])}f {e.get('time') or '?'}"


def _push(d, P, start, now_m):
    """The latest PUSH of direction d whose bar closed after her entry minute and by now (hold2.exit_v2's own filter)."""
    xs = [p for p in P if p["d"] == d and start < p["close"] <= now_m]
    return xs[-1] if xs else None


def l4_line(d, start, now_m, bars5, refs, rows, day, flow=None):
    """`flow` (SENSEX-NIFTY-FLOW §1.4, sensex_flow.ON only): {"P": NIFTY's pushes in SENSEX prices (sensex_flow.line) or
    None, "why"}, printed "NIFTY push"; None = this index's own pushes, as today."""
    arr, ul = ("▼", "▲") if d < 0 else ("▲", "▼")
    n = "NIFTY " if flow else ""
    P = (flow.get("P") or []) if flow else hold2.pushes(bars5, refs) if refs and bars5 else []
    if flow and flow.get("P") is None:
        push, ulta, ptxt = None, None, flow.get("why") or f"NIFTY {hold2.NO_REF}"   # could not check, never SENSEX's
    elif not flow and not refs:
        push, ulta, ptxt = None, None, hold2.NO_REF               # could not check: never "none"
    elif not flow and not bars5:
        push, ulta, ptxt = None, None, "push ? — no 5-min bars"
    else:
        push, ulta = _push(d, P, start, now_m), _push(-d, P, start, now_m)
        ptxt = (f"{n}push {arr} {push['t']} ({now_m - push['close']} min)" if push else f"{n}push {arr} abhi nahi") + " · " + (
            f"ulta {n}push {ul} {ulta['t']} @ {_n(ulta['origin'])}f" if ulta else f"ulta {n}push: none")
    E1, why = em(rows, day)
    sp = [r["spot"] for r in rows]
    rg = {"hi": max(sp), "lo": min(sp)} if sp else {}
    if E1 and sp:
        rg.update(em=round(E1["em"], 1), used=round((rg["hi"] - rg["lo"]) / E1["em"], 2), em_of=E1)
        rtxt = f"din range {rg['used']:.2f} EM"
    else:
        rg["why"] = why or "no chain row yet"
        rtxt = "din range ? — no 09:20 straddle"
    return f"{ptxt} · {rtxt}", push, ulta, rg, P


def fuel(d, rows, t0):
    """The losing leg's three largest-OI strikes PINNED at her entry (ITM or within one step of ATM there), entry -> now ->
    the session peak of their sum; a strike that reads None now is "could not check", never 0."""
    leg = "pe" if d < 0 else "ce"
    r0 = next((r for r in reversed(rows) if r["ts"] <= t0), rows[0] if rows else None)
    if r0 is None:
        return {"text": "fuel: could not check — no chain row", "tip": None}, None
    st, s0, a0 = _step(r0) or 0, r0["spot"], r0.get("atm")
    c = [(k, v) for k, v in ((s.get("k"), _oi(r0, s.get("k"), leg)) for s in r0.get("strikes") or ())
         if v is not None and k is not None and ((k > s0 if leg == "pe" else k < s0) or (a0 is not None and abs(k - a0) <= st))]
    ks = sorted(k for k, _ in sorted(c, key=lambda x: -x[1])[:3])
    if not ks:
        return {"text": f"fuel: could not check — no {leg.upper()} OI at {r0['ts'][:5]}", "tip": None}, None
    rn = rows[-1]
    per = {k: (_oi(r0, k, leg), _oi(rn, k, leg)) for k in ks}
    pk = (None, None)
    for r in rows:
        v = [_oi(r, k, leg) for k in ks]
        if None not in v and (pk[0] is None or sum(v) > pk[0]):
            pk = (sum(v), r["ts"][:5])
    f = {"ks": ks, "leg": leg.upper(), "t0": r0["ts"][:5], "entry": sum(a for a, _ in per.values()),
         "per": {k: {"entry": a, "now": b} for k, (a, b) in per.items()}, "peak": pk[0], "peak_t": pk[1], "tag": "M"}
    tip = " · ".join(f"{k:.0f} {leg.upper()} {_L(a)} → {_L(b)}" for k, (a, b) in per.items()) + \
        f" · pinned at {f['t0']} · OI [M], trapped [I]: OI has no side or vintage"
    miss = [k for k, (_, b) in per.items() if b is None]
    name = "/".join(f"{k:.0f}" for k in ks)
    if miss:
        return {"text": f"fuel: could not check — {miss[0]:.0f} {leg.upper()} not in the snapshot", "tip": tip}, dict(f, now=None)
    f["now"] = sum(b for _, b in per.values())
    return {"text": f"fuel {name} {leg.upper()} · entry {_L(f['entry'], 0)} → now {_L(f['now'], 0)} · peak "
                    f"{_L(f['peak'], 0)} {f['peak_t'] or '?'}", "tip": tip}, f


def levels_line(d, rows, spot, basis, levels, E1, now_m):
    """PDH / PDL, IB hi / lo (09:15-10:15 spot, once complete), HOD / LOD so far: those between spot and 2 EM in her
    direction, nearest first, each spot with fut beside it. PD absent -> said, never invented."""
    sp = [r["spot"] for r in rows]
    ib = [r["spot"] for r in rows if r["ts"] < IB_END] if now_m * 60 >= _sec(IB_END) else []
    pd = levels or {}
    cand = [("PDH", pd.get("PDH")), ("PDL", pd.get("PDL")), ("IB hi", max(ib) if ib else None),
            ("IB lo", min(ib) if ib else None), ("HOD", max(sp) if sp else None), ("LOD", min(sp) if sp else None)]
    far = 2 * E1["em"] if E1 else None
    on = {}
    for n, x in cand:
        if x is not None and spot is not None and 0 < d * (x - spot) and (far is None or d * (x - spot) <= far):
            on.setdefault(round(x), (x, []))[1].append(n)        # one printed price, one level: "IB lo/LOD 22,926s"
    on = sorted((("/".join(ns), x) for x, ns in on.values()), key=lambda c: abs(c[1] - spot))
    fut = (lambda x: "?") if basis is None else (lambda x: _n(x + basis))
    txt = ("levels " + " · ".join(f"{n} {_n(x)}s/{fut(x)}f" for n, x in on)) if on else \
        f"levels: none within {'2 EM' if far else 'her way (EM ?)'}"
    if pd.get("PDH") is None or pd.get("PDL") is None:
        txt += " · PD ? — not fetched"
    return {"text": txt, "tip": "spot [M] · fut = spot + basis [I] · between spot and 2 EM her way, nearest first"}, \
        [{"name": n, "spot": x, "fut": None if basis is None else round(x + basis, 1)} for n, x in on]


def _years(day, now_m, expiry):
    """chain_live.t_years: calendar year-fraction to expiry-day 15:30 IST, floored above zero."""
    a = datetime.fromisoformat(day) + timedelta(minutes=now_m)
    return max((datetime.fromisoformat(expiry) + timedelta(hours=15, minutes=30) - a).total_seconds() / (365.0 * 86400.0), 1e-4)


def prem_path(tr, rows, zone, day, now_m):
    """A sale's premium path: premium now [M] = intrinsic (spot) + TV, theta / hr (gamma.bs_price now minus an hour later at
    the chain's IV) [I], the premium at the zone (engine.js premAt, delta-linear) [I], and 10 min of premium vs fut."""
    K, ty = float(tr["k"]), str(tr.get("side") or "").upper()
    leg, rn = ty.lower(), rows[-1]
    g = _leg(rn, K, leg)
    p, s = g.get("ltp"), rn["spot"]
    if p is None:
        return {"text": f"premium ? — {K:.0f} {ty} not in the snapshot", "tip": None}, None
    intr = max(0.0, s - K) if ty == "CE" else max(0.0, K - s)
    iv, ex = g.get("iv"), rn.get("expiry")
    th = None
    if iv and ex:
        T = _years(day, now_m, ex)
        th = gamma.bs_price(s, K, iv, T, ty[0]) - gamma.bs_price(s, K, iv, max(T - 1 / (365.0 * 24), 0.0), ty[0])
    pz = None
    if zone and g.get("delta") is not None:                     # engine.js premAt at the zone's spot
        iz = max(0.0, zone["k"] - K) if ty == "CE" else max(0.0, K - zone["k"])
        pz = max(iz, 0.05, p + g["delta"] * (zone["k"] - s))
    r10 = next((r for r in reversed(rows) if _sec(r["ts"]) <= _sec(rn["ts"]) - TV_MIN * 60), None)
    if r10 is not None and _sec(r10["ts"]) < _sec(rn["ts"]) - (TV_MIN + 2) * 60:
        r10 = None                                                # a recorder hole: never a 10-min delta over 40 min
    p10 = _leg(r10, K, leg).get("ltp") if r10 else None
    dp, df = (None, None) if p10 is None else (p - p10, s - r10["spot"])     # fut = spot + the one basis: Δfut = Δspot
    out = {"now": p, "intrinsic": round(intr, 1), "tv": round(p - intr, 1), "theta_hr": None if th is None else round(th, 2),
           "at_zone": None if pz is None else round(pz, 1), "d10_prem": None if dp is None else round(dp, 1),
           "d10_fut": None if df is None else round(df, 1), "tag": {"M": ["now"], "I": ["theta_hr", "at_zone", "d10_fut"]}}
    txt = (f"premium {p:.0f} = {intr:.0f} intrinsic + {p - intr:.0f} TV · theta ~{'₹?' if th is None else f'₹{th:.1f}'}/hr [I]"
           + ("" if zone is None else f" · at zone ≈ {'₹?' if pz is None else f'₹{pz:.0f}'} [I]")
           + (" · 10 min: ?" if dp is None else f" · 10 min: prem {dp:+.0f}, fut {df:+.0f}"))
    return {"text": txt, "tip": "premium [M] chain LTP · intrinsic from spot · theta Black-76 at the chain's IV [I] · "
                                "at zone delta-linear [I] · Δfut = Δspot (one basis)"}, out


def zone_events(d, rows, t0, basis, E, dec):
    """The forward log's `zone` events: the FIRST minute since entry spot came within one step of each wall ahead (as it
    stood that minute), with the DECODE effort read then (or None) and her pts there. Recomputed from the record each
    time, so a restart backfills it exactly (anytime-start)."""
    last, seen, out = {}, set(), []
    for r in rows:
        if r["ts"] >= t0:
            last[r["ts"][:5]] = r                                 # a minute keeps its last snapshot
    leg = "ce" if d > 0 else "pe"
    for t in sorted(last):
        r, st = last[t], _step(last[t])
        w = wall_nearest(r, leg, d, r["spot"])
        if not w or not st or w["k"] in seen or abs(r["spot"] - w["k"]) > st:
            continue
        seen.add(w["k"])
        e = (holdshadow._dec_at(dec or {}, _sec(t) // 60)[1] or {}).get("effort") or {}
        fut = None if basis is None else round(r["spot"] + basis, 1)
        out.append({"event": "zone", "key": w["k"], "t": t, "k": w["k"], "leg": w["leg"], "fut": fut, "oi": w["oi"],
                    "effort": {x: e.get(x) for x in ("at", "t", "x", "word")} if e.get("x") is not None else None,
                    "pts": None if None in (fut, E) else round(d * (fut - E), 1)})
    return out


def read(tr, view, chain_rows, bars5, refs, dec, levels, now_m, prints=None, gc_t=None, flow=None):
    """The map for her open marked trade at minute now_m: {ok, l4, l5, detail [{text, tip}], push, ulta, range, zone, fuel,
    levels, prem, events, tag "I", why}, or {ok False, why}. `tr` = server._hold_trade's record, `view` the fold engine's
    (d, E, fut, units.basis_ix, t), `chain_rows` the chain recorder's snapshots, `bars5` / `refs` hold2's push inputs,
    `dec` holdshadow.dec_rows(...), `levels` {"PDH", "PDL"} (index prices) or None, `prints` decoder_log.read_events
    (her BADA PRINTs), `gc_t` the last GoCharting bar's open ms seen by now (None: the tab never posted), `flow` l4_line's
    (SENSEX-NIFTY-FLOW, OFF: None)."""
    d, E = view.get("d"), view.get("E")
    if d not in (1, -1) or view.get("t") is None or not tr.get("t0"):
        return {"ok": False, "tag": "I", "why": "could not check — the engine has no direction for the trade yet"}
    day = (datetime(1970, 1, 1) + timedelta(milliseconds=view["t"] + 19800000)).strftime("%Y-%m-%d")
    basis = (view.get("units") or {}).get("basis_ix")
    t0 = str(tr["t0"])
    start = _sec(t0) // 60 + 1                                    # hold2.live's: the first whole minute after her entry
    rows = snaps(chain_rows, now_m)
    l4, push, ulta, rg, P = l4_line(d, start, now_m, bars5, refs, rows, day, flow)
    out = {"ok": True, "rev": REV, "l4": l4, "push": push, "ulta": ulta, "range": rg, "tag": "I", "why": None}
    if not rows:
        return dict(out, l5="pullback zone ? — could not check: no chain row", zone=None, fuel=None, levels=None, prem=None,
                    detail=[{"text": "fuel: could not check — no chain row", "tip": None}], events=[])
    rn, leg = rows[-1], "ce" if d > 0 else "pe"
    spot, st = rn["spot"], _step(rn)
    w = wall_nearest(rn, leg, d, spot)
    if w is None:
        l5, zone = "pullback zone: koi deewar nahi (checked ±8)", None
    else:
        zf = None if basis is None else w["k"] + basis
        pts = round(abs(spot - w["k"]))                          # spot to the strike: a lagging basis never moves it (30 Sep: 9 f vs 21 s)
        zone = dict(w, fut=zf, spot=w["k"], pts=pts, at=bool(st) and abs(spot - w["k"]) <= st, tag="M")
        zone["effort"] = survivor(d, dec, now_m) if zone["at"] else None
        base = view["t"] - ((view["t"] // 1000 + 19800) % 86400) * 1000              # IST midnight of the view's day, ms
        t1 = base + now_m * 60000                                 # a bar closing at minute m is read at m (hold2's pushes' rule)
        zone["bada"] = None if zf is None or not st else bada(prints, zf, st, base + _sec(t0) * 1000, t1)
        ext = [x for x in (zone["effort"], zone["bada"]) if x]
        if zone["at"] and not zone["bada"] and (gc_t is None or gc_t < t1 - 600000):
            ext.append("BADA ? GoCharting tab nahi")                 # could not check, never "none"
        l5 = (f"pullback zone {_n(zf)}f / {_n(w['k'])}s ({'?' if pts is None else pts} pts) · {w['k']:.0f} {w['leg']} "
              f"{_L(w['oi'])}" + "".join(f" · {x}" for x in ext))
    E1, _ = em(rows, day)
    fl, fd = fuel(d, rows, t0)
    lv, lvs = levels_line(d, rows, spot, basis, levels, E1, now_m)
    detail = [fl, lv]
    pr = None
    if tr.get("role") == "short":
        p, pr = prem_path(tr, rows, zone, day, now_m)
        detail.append(p)
    ev = [dict({"event": "ulta_push", "key": p["t"], "t": p["t"], "origin": p["origin"], "fut": p["c"]}, **({"push_src": "NIFTY"} if flow else {}))
          for p in P if p["d"] == -d and start < p["close"] <= now_m]
    ev += zone_events(d, rows, t0, basis, E, dec)
    return dict(out, l5=l5, zone=zone, fuel=fd, levels=lvs, prem=pr, detail=detail, events=ev)


FIELDS = ("rev", "push", "ulta", "range", "zone", "fuel", "levels", "prem", "tag")


def into(vc, m):
    """The map onto the one voice (server._in_trade and the replay: one merge): l4, l5, detail (fuel, levels, R -- the
    number moved out of l1 -- and a sale's premium path) and `map` (the fields). No map, or a failed one: `map_why`, and
    the faces show the three lines alone."""
    if not (vc or {}).get("ok"):
        return vc
    if not (m or {}).get("ok"):
        vc["map_why"] = str((m or {}).get("why") or "could not check — the map is reading the day (first look)")
        return vc
    r = vc.get("r_now")
    R = ("R ?" if r is None else f"R {r:+.1f}") + (f" · BE lock ✓ {vc['lock_t']}" if vc.get("lock_t") else
                                                   " · BE lock at 2R" if vc.get("lock_on_f") is not None else "")
    det = list(m["detail"])
    det.insert(2, {"text": R, "tip": "R = pts / |initial line − entry| [I] · BE lock engages at MFE 2R (HOLD v2)"})
    if vc.get("gauge"):                                           # A61: W-BLEED is a number here, never a WARN alone
        det.insert(0, {"text": vc["gauge"], "tip": "the wall behind you off its peak (§5.5): with price against you GAVE UP warns"})
    vc.update(l4=m["l4"], l5=m["l5"], detail=det, map={k: m.get(k) for k in FIELDS})
    return vc
