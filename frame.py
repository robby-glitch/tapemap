# tapemap/frame.py
"""frame.py -- THE READ, composed. One frame per tape post.

COMPOSITION ONLY, the warmap.py precedent: nothing here measures anything
new. The tape (bars, bands, walls, events, taps) arrives from the GoCharting
extension; the book (war map, chain minutes, zone state, VPIN, senses)
arrives from the modules TapeMap already runs. This file only decides what
sits in which block, tags it M or I, names its source, and states every
absence with its own reason. A block that quietly measured would be the one
defect the composition test exists to catch.

BLOCK SHAPE, uniform so the face never learns block semantics:
    {"title", "kind": "chips"|"rows"|"lines", "items": [{"k","v","tag","cls","why"}],
     "src": [module names], "falsifies": str}

PATA NAHI is a value, never a hole: a book that did not answer yields one
PATA NAHI item per block with THAT block's reason.

KILL CONDITIONS (spec §8), declared here before the first row is logged:
  taps: at n=30, converged (>=2 ladder rows in the zone) must exceed bare by
        one standard deviation of +6-bar excursions, else the field goes;
  ladder rows: over 30 sessions, pain>0 rows taken no more often than pain=0
        rows -> the pain column goes;
  tells: over 30 sessions, a tell resolving no better than its logged control
        -> deleted; flow gate on notify: at n=30 taps, flow-confirmed taps must
        exceed bare by one sd at +6 bars, else notify fires on the zone alone
        and says so.

Pure, stdlib only, no I/O, no clock (now_hhmm is passed in)."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import gate as gate_mod

BASIS_WHY = "index and strike levels shifted by the live basis"
TAP_Z = 1.85                # the extension's own tap threshold (taps.js)
WARM_HHMM = "09:25"         # band_rotation.ANCHOR_HHMM; sigma is not trusted before it


def _item(k, v, tag=None, cls=None, why=None):
    return {"k": k, "v": v, "tag": tag, "cls": cls, "why": why}


def _absent(k, why):
    return _item(k, "PATA NAHI", None, "hole", why)


def _block(title, kind, items, src, falsifies):
    return {"title": title, "kind": kind, "items": items, "src": src, "falsifies": falsifies}


def _hhmm(t_ms: int) -> str:
    s = (t_ms // 1000 + 19800) % 86400
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"


def window_change(minutes: Optional[dict], t0: str, t1: str) -> Dict[int, Tuple[float, float]]:
    """Per-strike (ce, pe) OI change between two marks of ChainState.minutes,
    whose `k` holds change-since-open per strike. A mark missing on either end
    is an empty answer, never an interpolation."""
    a, b = (minutes or {}).get(t0), (minutes or {}).get(t1)
    if not a or not b:
        return {}
    out = {}
    for k, (ce1, pe1) in (b.get("k") or {}).items():
        ce0, pe0 = (a.get("k") or {}).get(k, (None, None))
        if None not in (ce0, pe0, ce1, pe1):
            out[int(k)] = (ce1 - ce0, pe1 - pe0)
    return out


def basis(tape: dict, book: dict) -> Optional[float]:
    fut, spot = tape.get("futPx"), book.get("spot")
    return round(fut - spot, 1) if fut is not None and spot is not None else None


def ladder(tape: dict, book: dict) -> dict:
    """One axis, futures frame. A ROW EXISTS IFF IT CARRIES STATE THE CHART
    CANNOT DRAW: OI with day change and pain, tape walls with lean counts,
    a level with sequence-machine state. Sigma lines are the ZONE header,
    not rows. Max pain is not a row."""
    items: List[dict] = []
    src = ["board.js walls", "warmap.heat", "warmap.sequence", "warmap.dwell"]
    b = basis(tape, book)
    wm = book.get("warmap") or {}
    fut = tape.get("futPx")
    for w in tape.get("walls") or []:
        items.append(dict(_item(f"{'S' if w['side'] < 0 else 'B'} {w['price']:.0f}",
                                f"wall since {w.get('since')} · {w['size'] / 1000:.1f}K · leaned {w.get('hits', 0)}×",
                                "M", "wall"),
                          p=float(w["price"]), kind="S" if w["side"] < 0 else "B", side=w["side"], state="held",
                          snapshot=bool(w.get("snapshot"))))
    if not wm:
        items.append(dict(_absent("book rows", "tapemap did not answer: no OI walls, no level state"), p=None))
    else:
        if b is None:
            items.append(dict(_absent("basis", "no index spot from the chain; strike rows cannot be placed"), p=None))
        else:
            for h in wm.get("heat") or []:
                for side in ("ce", "pe"):
                    oi = h.get(f"{side}_oi")
                    if oi is None:
                        continue
                    pain = h.get(f"{side}_pain")
                    items.append(dict(_item(f"{side.upper()} {h['k']:.0f}",
                                            f"{oi / 1e6:.0f}M · {(h.get(f'{side}_chg') or 0) / 1e6:+.0f}M today"
                                            + (f" · {pain:.0f} under" if pain else ""),
                                            "M", side, BASIS_WHY),
                                      p=float(h["k"]) + b, kind=side.upper(), oi=oi, pain=pain,
                                      pain_tag="I", conf=h.get(f"{side}_conf"), state="held"))
            for L in wm.get("levels") or []:
                st = (wm.get("sequence") or {}).get(f"{L['kind']}@{L['px']}")
                if not st:
                    continue                 # no machine state: the chart draws the line; not a row
                px = float(L["px"]) + (b if L.get("frame") == "index" else 0.0)
                items.append(dict(_item(f"{L['kind']} {L['px']:.0f}",
                                        f"{st['state']} · tested {st['tests']}× · last {st.get('last_outcome') or '—'}",
                                        L.get("tag", "M"), "level", BASIS_WHY if L.get("frame") == "index" else None),
                                  p=px, kind=L["kind"], state=st["state"]))
    if fut is not None:
        items.append(dict(_item("price", f"{fut:.1f}", "M", "px"), p=float(fut), kind="PX", state="now"))
    items.sort(key=lambda r: -(r["p"] if r.get("p") is not None else -1e18))
    for r in items:
        r["d"] = round(r["p"] - fut, 1) if r.get("p") is not None and fut is not None else None
    return {**_block("Ladder", "rows", items, src, "a held row is taken (re-read at +30/+60m)"),
            "rows": [r for r in items if r.get("p") is not None], "basis": b}


def _bands_now(tape: dict) -> Optional[dict]:
    bands = tape.get("bands") or []
    return bands[-1] if bands else None


def zone(tape: dict, book: dict, now_hhmm: str) -> dict:
    """The one verb. Location from the 5-minute bands; state from the one
    zone machine (book['zone_state'], run_states at SCORED_INTERVAL); flow
    confirmation from the tape's own events at the zone price and the
    chain's confirm. FIRE only when both agree, once per zone visit.
    Flow anchors on the band at this instant, or on the machine's level
    once armed."""
    src = ["market.js vwapSeries", "band_rotation.run_states", "board.js events", "taps.js"]
    bn = _bands_now(tape)
    if not bn or not bn.get("sigma"):
        return {**_block("Zone", "chips", [_absent("zone", "no bands on the tape yet")], src, "—"),
                "state": "PATA NAHI", "reached": False, "confirmed": False, "fire": False, "visit": None, "z": None, "flow": []}
    if now_hhmm < WARM_HHMM:
        return {**_block("Zone", "chips", [_item("zone", f"σ not yet trusted, {WARM_HHMM}", "M", "warm")], src, "—"),
                "state": "WARMUP", "reached": False, "confirmed": False, "fire": False, "visit": None, "z": None, "flow": []}
    fut = tape.get("futPx")
    z = (fut - bn["vwap"]) / bn["sigma"] if fut is not None else None
    buy_lo, buy_hi, sell = bn["d3"], bn["d2"], bn["u3"]
    in_buy = fut is not None and buy_lo <= fut <= buy_hi
    at_sell = fut is not None and fut >= sell
    items = [_item("buy zone", f"{buy_lo:.0f}–{buy_hi:.0f} (−3σ..−2σ)", "M", "sig"),
             _item("sell line", f"{sell:.0f} (+3σ)", "M", "sig"),
             _item("z", f"{z:+.2f}" if z is not None else "—", "M", "big")]
    zs = book.get("zone_state")
    machine = "PATA NAHI"
    if zs:
        last = zs[-1] if isinstance(zs, list) else zs
        machine = last.get("state", "PATA NAHI")
        items.append(_item("setup", machine, "M", "setup",
                           f"ref {last.get('ref_high')} · {last.get('candles_left')} candles left" if last.get("ref_high") else None))
    else:
        items.append(_absent("setup", "zone machine not answering (band_rotation.run_states)"))
    row = float(tape.get("rowSize") or 5)
    # the flow check anchors on the band price at this instant, or, once the
    # machine has armed, on the machine's own level: the touch already
    # happened, and a close a hair past d3 is only the falsification region
    # if it holds three bars (see `falsifies` below)
    m_level = (zs[-1] if isinstance(zs, list) else zs).get("level") if zs else None
    edge = buy_hi if in_buy else sell if at_sell else (m_level if machine in ("ARMED", "TRIGGERED", "IN_TRADE") and m_level is not None else None)
    flow = [e for e in tape.get("events") or [] if edge is not None and e.get("p") is not None
            and abs(e["p"] - edge) <= 3 * row and e.get("kind") in ("absorption", "exhaustion", "trap")]
    for e in flow:
        items.append(_item(e["kind"], f"{_hhmm(e['t'])} at {e['p']:.0f}", "M", "flow"))
    chain_confirm = (book.get("senses") or {}).get("confirm")       # Kleene: CONFIRMED / UNCONFIRMED / UNKNOWN
    items.append(_item("chain confirm", chain_confirm or "UNKNOWN", "I", "flow",
                       None if chain_confirm else "pair rotation and OI deceleration not read"))
    reached = in_buy or at_sell or machine in ("ARMED", "TRIGGERED", "IN_TRADE")
    confirmed = bool(flow) and chain_confirm != "UNCONFIRMED"
    fire = reached and confirmed
    # visit must be STABLE for the life of a visit (one beep, not one per bar):
    # anchor on the machine's own reference bar while it holds one, else on the
    # earliest bar of the contiguous band-touch run, else fall back to today's
    # last-bar behaviour (frame.py stays stateless -- these are all read off
    # fields already on the tape/machine, nothing is remembered here).
    visit = None
    if reached and tape.get("closed"):
        closed = tape["closed"]
        side = "sell" if at_sell else "buy"
        ref_i = None
        if zs and machine in ("ARMED", "TRIGGERED", "IN_TRADE"):
            last = zs[-1] if isinstance(zs, list) else zs
            ref_i = last.get("ref_i")
        if ref_i is not None and 0 <= ref_i < len(closed):
            visit = f"{side}@{_hhmm(closed[ref_i]['t'])}"
        elif in_buy or at_sell:
            bands_list = tape.get("bands") or []
            key = "d2" if in_buy else "u3"

            def _touches(idx):
                lvl = bands_list[idx].get(key)
                if lvl is None:
                    return False
                bar = closed[idx]
                return bar["l"] <= lvl if in_buy else bar["h"] >= lvl

            i = len(closed) - 1
            if i < len(bands_list) and _touches(i):
                while i > 0 and _touches(i - 1):
                    i -= 1
                visit = f"{side}@{_hhmm(closed[i]['t'])}"
        if visit is None:
            visit = f"{side}@{_hhmm(closed[-1]['t'])}"
    items.append(_item("signal", "ZONE + FLOW" if fire else "zone reached, flow not confirmed" if reached else "not in zone",
                       "I", "fire" if fire else None))
    return {**_block("Zone", "chips", items, src, "price closes past 3σ and holds 3 bars"),
            "state": machine, "reached": reached, "confirmed": confirmed, "fire": fire, "visit": visit, "z": z,
            "flow": [e["kind"] for e in flow]}


def build(tape: dict, book: dict, now_hhmm: str) -> dict:
    book = book or {}
    wm = book.get("warmap") or {}
    closed = tape.get("closed") or []
    missing: List[str] = []
    if not wm:
        missing.append("warmap")
    if not book.get("minutes"):
        missing.append("chain minutes")

    g = gate_mod.state(book.get("ivrv"), book.get("expiry"), (tape.get("session") or "").split("|")[-1],
                       book.get("vpin_pct"), False)
    header = _block("Header", "chips", [
        _item("session", tape.get("session") or "—", "M"),
        _item("legs", f"expiry {book['expiry']}", "M") if book.get("expiry") else _absent("legs", "chain expiry not answered"),
        _item("gate", g["level"], "I", "gate", g["reason"]),
    ], ["chain expiry", "gate.py"], "—")

    items = []
    if closed:
        o, c = closed[0]["o"], closed[-1]["c"]
        bh, bl = max(closed, key=lambda b: b["h"]), min(closed, key=lambda b: b["l"])
        items += [_item("open", f"{o:.1f}", "M"), _item("high", f"{bh['h']:.1f} at {_hhmm(bh['t'])}", "M"),
                  _item("low", f"{bl['l']:.1f} at {_hhmm(bl['t'])}", "M"), _item("now", f"{c:.1f}", "M")]
        w = closed[-12:]
        net = abs(w[-1]["c"] - w[0]["o"])
        travel = sum(abs(w[i]["c"] - (w[i - 1]["c"] if i else w[0]["o"])) for i in range(len(w)))
        items += [_item("last 60m net", f"{net:.0f}", "M"), _item("last 60m travel", f"{travel:.0f}", "M")]
    else:
        items.append(_absent("bars", "no closed bars posted"))
    mins = book.get("minutes") or {}
    marks = sorted(mins)
    if len(marks) >= 2:
        t0, t1 = (marks[-4] if len(marks) >= 4 else marks[0]), marks[-1]
        ch = window_change(mins, t0, t1)
        ce = sum(v[0] for v in ch.values()); pe = sum(v[1] for v in ch.values())
        items.append(_item(f"OI {t0}–{t1}", f"CE {ce / 1e6:+.0f}M · PE {pe / 1e6:+.0f}M", "M", None,
                           "arithmetic on per-strike change; who wrote it is not visible"))
    else:
        items.append(_absent("OI window", "chain minutes not answered"))
    session = _block("Session", "rows", items, ["bars", "ChainState.minutes"], "a leg whose window carries the opposite OI sign")

    items = []
    walls = tape.get("walls") or []; broke = tape.get("broke") or []
    items.append(_item("floors taken", str(sum(1 for x in broke if x.get("side") == 1)), "M"))
    items.append(_item("walls held", ", ".join(f"{'S' if x['side'] < 0 else 'B'} {x['price']:.0f}×{x.get('hits', 0)}" for x in walls) or "none", "M"))
    if wm.get("heat"):
        ce_w = sum(h.get("ce_chg") or 0 for h in wm["heat"]); pe_w = sum(h.get("pe_chg") or 0 for h in wm["heat"])
        items.append(_item("writing today", f"CE {ce_w / 1e6:+.0f}M · PE {pe_w / 1e6:+.0f}M", "M"))
        pain = [(h["k"], s, h.get(f"{s}_pain")) for h in wm["heat"] for s in ("ce", "pe") if (h.get(f"{s}_pain") or 0) > 0]
        items.append(_item("writers under", ", ".join(f"{s.upper()} {k:.0f} −{p:.0f}" for k, s, p in pain) or "none", "I",
                           None, "writer-dominated assumed (trapped_inventory)"))
    else:
        items.append(_absent("writing today", "tapemap heat not answered"))
    if closed:
        d = sum(b.get("delta", 0) for b in closed)
        items.append(_item("tape aggression", f"{'sellers' if d < 0 else 'buyers'} · sign only", "M", None,
                           "shape and sequence, never magnitude; the 8% floor is gone"))
        items.append(_item("fut OI vs price", f"{(closed[-1].get('oi') or 0) - (closed[0].get('oi') or 0):+.0f} on {closed[-1]['c'] - closed[0]['o']:+.0f} pts", "M"))
    paid = _block("Paid", "rows", items, ["board.js walls", "warmap.heat", "trapped_inventory", "bars"], "the named side loses its last held shelf")

    items = []
    if len(marks) >= 4:
        paces = [window_change(mins, marks[i - 1], marks[i]) for i in range(1, len(marks))]
        ce_p = [sum(v[0] for v in p.values()) for p in paces]; pe_p = [sum(v[1] for v in p.values()) for p in paces]

        def rank(xs):
            return sum(1 for x in xs if x <= xs[-1]) / len(xs)
        items.append(_item("CE writing pace", f"rank {rank(ce_p):.2f} of session", "M"))
        items.append(_item("PE writing pace", f"rank {rank(pe_p):.2f} of session", "M"))
    else:
        items.append(_absent("writing pace", "fewer than 4 chain minutes; nothing to rank"))
    for e in [e for e in (tape.get("events") or []) if e.get("kind") == "absorption"][-3:]:
        items.append(_item("absorption", f"{_hhmm(e['t'])} at {e['p']:.0f}", "M"))
    failing = _block("Failing", "chips", items, ["ChainState.minutes", "board.js events"], "price follows the aggressor within 2 bars")

    items = []
    if wm.get("heat"):
        worst = max(((h["k"], s, h.get(f"{s}_pain") or 0, h.get(f"{s}_conf")) for h in wm["heat"] for s in ("ce", "pe")),
                    key=lambda x: x[2])
        items.append(_item("trapped side", worst[1].upper() if worst[2] > 0 else "none", "I"))
        items.append(_item("worst leg", f"{worst[1].upper()} {worst[0]:.0f} −{worst[2]:.0f} · conf {worst[3]}", "I", None,
                           "basis is an estimate in expiry week"))
    else:
        items.append(_absent("fuel", "tapemap heat not answered: no trapped side to name"))
    sn = book.get("senses") or {}
    items.append(_item("gear", sn.get("gear"), "I") if sn.get("gear") else _absent("gear", "senses not answered"))
    fuel = _block("Fuel", "chips", items, ["trapped_inventory", "chainside", "senses"], "pain rises while that side's OI keeps building")

    lad = ladder(tape, book)
    zn = zone(tape, book, now_hhmm)

    tells = []
    heat = wm.get("heat") or []
    b = lad.get("basis")
    if heat and b is not None and closed:
        px = closed[-1]["c"]
        below = sorted((h for h in heat if h.get("pe_oi") and h["k"] + b < px), key=lambda h: -h["pe_oi"])
        if below:
            k = below[0]["k"]
            tells.append({"name": "DOWN", "predicate": f"close < {k + b:.0f} AND PE {k:.0f} OI falling",
                          "target": f"{zn['items'][0]['v'].split(' ')[0].split('–')[0]}" if zn.get("items") and zn["items"][0]["k"] == "buy zone" else "zone",
                          "negation": f"close back above {k + b:.0f}"})
        above = sorted((h for h in heat if h.get("ce_oi") and h["k"] + b > px), key=lambda h: h["k"])
        if above:
            k = above[0]["k"]
            tells.append({"name": "PIN", "predicate": f"PE writing continues AND CE {k:.0f} OI falling",
                          "target": f"{k + b:.0f}", "negation": f"CE {k:.0f} OI still building"})
    tells.append({"name": "ELSE", "predicate": "neither tell printed", "target": "flat", "negation": "—"})
    watch = {**_block("Watch", "lines", [_item(t["name"], f"{t['predicate']} → {t['target']} · falsified by {t['negation']}", "I")
                                          for t in tells], ["warmap.heat", "frame.zone"], "each tell prints its own negation"),
             "tells": tells}

    footer = _block("Not known", "lines", [
        _item("OI", "unsigned, always", None),
        _item("VPIN", f"pct {book['vpin_pct']:.2f}", "I") if book.get("vpin_pct") is not None else _absent("VPIN", "vpin not answered"),
        _item("coverage", str(book.get("coverage") or {}), None),
        _item("missing", ", ".join(missing) or "nothing", None),
    ], ["coverage"], "—")

    bn = _bands_now(tape)
    fut = tape.get("futPx")
    strip = {"z": zn.get("z"),
             "zone_edge_d": round(min(abs(fut - bn["d2"]), abs(fut - bn["u3"])), 1) if bn and fut is not None else None,
             "setup": zn.get("state"), "fire": zn.get("fire"),
             "level_under": next((r for r in lad["rows"] if r.get("d") is not None and r["d"] < 0 and r.get("kind") in ("B", "S")), None),
             "gate": g["level"], "missing": missing}

    return {"ok": True, "idx": tape.get("idx") or "NIFTY", "ts": now_hhmm, "have_bars": len(closed),
            "strip": strip, "header": header, "session": session, "paid": paid, "failing": failing,
            "ladder": lad, "fuel": fuel, "zone": zn, "watch": watch, "footer": footer,
            "events": [{"t": _hhmm(e["t"]), "kind": e["kind"]} for e in (tape.get("events") or [])]
                      + [{"t": _hhmm(t["t"]), "kind": "tap"} for t in (tape.get("taps") or [])],
            "missing": missing, "coverage": book.get("coverage") or {}}
