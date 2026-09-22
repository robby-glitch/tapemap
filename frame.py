# tapemap/frame.py
"""frame.py -- THE READ, composed. One frame per tape post.

COMPOSITION ONLY, the warmap.py precedent: nothing here measures anything
new. The tape (bars, bands, walls, events, taps) arrives from the GoCharting
extension; the book (war map, chain minutes, zone state, VPIN, senses)
arrives from the modules TapeMap already runs. This file only decides what
sits in which object, tags it M or I, and states every absence with its own
reason. An object that quietly measured would be the one defect the
composition test exists to catch.

FRAME SHAPE (spec §C amended by §E): the nine uniform blocks are gone. The
frame answers five questions -- where, who is trapped, where the walls are,
what the tape just did, what I am waiting for -- as `where`, `trapped`,
`walls`, `tape`, `setup`, plus `head` (session/expiry/gate) and `record`
(the server's write receipt). Every field that can be null carries a sibling
`*_why` that is non-null exactly when the field is null; `tag` appears only
on the five inferred objects. The face formats and computes nothing.

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

import breadth as breadth_mod   # positioning breadth; no direction field exists in that object by construction
import fronts as fronts_mod     # research-findings §1d: the near-ATM fronts and the fade gate
import gate as gate_mod
import signals as signal_mod     # the ballot and the state machine; frame.py never measures a vote
import structure   # prior_day_hlc: the payload's floor pivots inverted back to the prior session's H/L/C
import visit as visit_mod   # the latched reach and the visit key; frame.py composes, visit.py measures
import watch as watch_mod       # the ladder rows worth watching; none of them is an entry

WARM_HHMM = "09:25"         # band_rotation.ANCHOR_HHMM; sigma is not trusted before it
# A TIME GATE IS NOT A QUALITY GATE. On 2026-09-17 the posted band carried sigma = 1.41 points
# against a 23,300 price at 09:32 -- past WARM_HHMM, so `warm` was True and z printed +31. The
# "sell zone" then sat thirty points BELOW price and every bar read as deep inside it. With the
# reach latched (visit.py) that phantom visit would consume sell ordinal 1 and silence the real
# visit later in the window, which is the one she trades. So sigma must also be wide enough that
# 2 sigma names a zone rather than noise: 0.025% of price is ~5.8 pts on NIFTY, ~14 on BANKNIFTY,
# ~19 on SENSEX -- below any real session band and far above a degenerate one.
# ponytail: a fraction of price, not a fitted floor. JUDGEMENT CALL -- kill condition: if over 30
# sessions any row is held un-warm after 09:45 while the day's later sigma stays within 2x this
# floor, the floor is too high and comes out.
SIGMA_FLOOR_PCT = 0.00025
WALL_CAP = 3                # nearest walls shown each side (spec §E default 3); every row is still on the wire
CONFIRMS = ("absorption", "exhaustion", "trap")
_WALL_KINDS = ("S", "B", "CE", "PE")
_LEVEL_KINDS = ("PDH", "PDL", "PDC", "ROUND", "FLIP")

# Module-level empty shapes, every §C key of the object, null (spec ruling: "the empty shapes are module
# constants used by the happy path too, so they cannot drift"). Enum/flag fields the contract never nulls
# (state's "PATA NAHI" hole value, tag literals, warm=False, cap, floors_taken) keep their real default.
_EMPTY_HEAD = {"symbol": None, "expiry": None, "expiry_why": None, "dte": None, "started": None, "late_min": None,
               "gate": {"level": "PATA NAHI", "reason": None, "reason_full": None, "would_be": None, "would_be_reason": None, "tag": "I"}}
_EMPTY_WHERE = {"px": None, "px_why": None, "vwap": None, "sigma": None, "z": None, "warm": False, "warm_at": WARM_HHMM,
                "buy_zone": None, "sell_line": None, "sell_zone": None, "edge": None, "zone_why": None,
                "open": None, "high": None, "low": None, "from_open": None, "off_extreme": None, "hour": None, "bars_why": None}
_EMPTY_TRAPPED = {"writers": None, "writers_why": None, "window": None, "window_why": None, "pace": None, "pace_why": None,
                   "fut_oi": None, "fut_oi_why": None, "gear": None, "gear_why": None, "gear_tag": "I"}
_EMPTY_WALLS = {"rows": [], "cap": WALL_CAP, "floors_taken": 0, "oi_why": None, "prior_why": None, "basis": None,
                "watch": {"rows": [], "broken": None, "cap": watch_mod.CAP, "shown": 0,
                          "why": "the watch list did not build",
                          "broken_why": "the watch list did not build",
                          "note": watch_mod.NOTE}}
_EMPTY_BREADTH = {"window_min": breadth_mod.WINDOW_MIN, "t0": None, "t1": None,
                  "written_ce": None, "unwound_ce": None, "written_pe": None, "unwound_pe": None,
                  "strikes_seen": 0, "counts_why": "breadth did not build",
                  "concentration_top1": None, "concentration_top3": None, "concentration_why": "breadth did not build",
                  "advancing": None, "retreating": None, "fronts_seen": 0, "fronts_why": "breadth did not build",
                  "pressed": None, "bought": None, "premium_why": "breadth did not build",
                  "fut_oi_day": None, "fut_px_day": None, "fut_oi_window": None, "fut_px_window": None,
                  "fut_why": "breadth did not build", "regime": None, "pinned": None, "regime_tag": "I",
                  "regime_why": "breadth did not build", "backfill_minutes": 0, "tag": "M",
                  "note": breadth_mod.NOTE}
_EMPTY_TAPE = {"events": [], "aggressor": None, "aggressor_why": None}
_EMPTY_SETUP = {"side": "buy", "state": "PATA NAHI", "state_why": None, "ref": None, "candles_left": None, "level": None,
                 "reached": False, "in_pocket": False, "flow": [], "fire": False, "visit": None, "tells": [],
                 "confirm": {"value": "UNKNOWN", "why": "setup did not build", "why_full": None, "tag": "I"}, "falsifies": None,
                 "signal": dict(signal_mod.EMPTY_SIGNAL), "votes": dict(signal_mod.EMPTY_VOTES),
                 "gate": {"legal": None, "why": "the fade gate did not build", "side": None,
                          "defender": None, "front": None, "veto": None, "tag": "I"}}
# The same shape `_setup`'s hole carries, so a failure inside the gate and a
# failure before it reach the face identically (research-findings §1d: a
# missing input is PATA NAHI, never legal).
_EMPTY_GATE = dict(_EMPTY_SETUP["gate"])


def _hhmm(t_ms: int) -> str:
    s = (t_ms // 1000 + 19800) % 86400
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}"


def _why(s: Optional[str], n: int = 48) -> Optional[str]:
    """One clause on the face. The long form, where one exists, rides in a *_full sibling."""
    if s is None:
        return None
    return s if len(s) <= n else s[: n - 1] + "…"


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


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


def _bands_now(tape: dict) -> Optional[dict]:
    bands = tape.get("bands") or []
    return bands[-1] if bands else None


_ZONE_ACTIVE = ("ARMED", "TRIGGERED", "IN_TRADE")


def _pick_side(in_buy: bool, in_sell: bool, buy_last: Optional[dict], sell_last: Optional[dict]) -> str:
    """Which machine is the live setup. Price in a pocket wins outright --
    in_sell picks sell, in_buy picks buy, and if somehow both are true (bands
    crossed) sell wins, the seller's tool. With neither pocket touched: if
    only one machine is active (ARMED/TRIGGERED/IN_TRADE) it wins outright; if
    both are active the more recent reference bar is the live setup (larger
    ref_i wins), sell on an exact tie or when either ref_i is missing; if
    neither is active, buy is the default read. See spec §6, defect C2."""
    if in_sell:
        return "sell"
    if in_buy:
        return "buy"
    buy_active = bool(buy_last) and buy_last.get("state") in _ZONE_ACTIVE
    sell_active = bool(sell_last) and sell_last.get("state") in _ZONE_ACTIVE
    if buy_active and sell_active:
        bi, si = buy_last.get("ref_i"), sell_last.get("ref_i")
        return "buy" if (bi is not None and si is not None and bi > si) else "sell"
    return "sell" if sell_active else "buy"


def _safe(fn, empty: dict) -> dict:
    """One object of the frame built in isolation (spec §2 isolation): a raising object becomes its own `why`
    over the empty shape; the other objects still print."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 -- the reason is the value
        return {**empty, "why": f"{type(e).__name__}: {e}"}


def _safe_list(fn) -> Tuple[list, Optional[str]]:
    """The `_safe` pattern for a list-shaped section (not one of the six named objects, so there is no dict
    to merge a `why` into): a raising section becomes an empty list plus its own reason, never killing `build()`."""
    try:
        return fn(), None
    except Exception as e:  # noqa: BLE001 -- the reason is the value
        return [], f"{type(e).__name__}: {e}"


def _head(tape: dict, book: dict) -> dict:
    sess = (tape.get("session") or "").split("|")
    symbol, day = (sess[0] or None), (sess[-1] if len(sess) >= 3 else None)
    expiry = book.get("expiry")
    dte = None
    if expiry and day:
        try:
            from datetime import date
            dte = (date.fromisoformat(expiry) - date.fromisoformat(day)).days
        except ValueError:
            dte = None
    cov = book.get("coverage") or {}
    # squeeze is never measured here: None is the honest absence
    g = gate_mod.state(book.get("ivrv"), book.get("expiry"), day or "", book.get("vpin_pct"), None)
    return {**_EMPTY_HEAD, "symbol": symbol or "—", "expiry": expiry, "expiry_why": _why(None if expiry else "chain expiry not answered"), "dte": dte,
            "started": cov.get("server_up"), "late_min": cov.get("late_min"),
            "gate": {"level": g["level"], "reason": _why(g["reason"]), "reason_full": g["reason"],
                     "would_be": g.get("would_be"), "would_be_reason": g.get("would_be_reason"), "tag": "I"}}


def _where(tape: dict, closed: list, now_hhmm: str) -> dict:
    bn, fut = _bands_now(tape), tape.get("futPx")
    have_sigma = bool(bn and bn.get("sigma"))
    floor = (fut or (bn or {}).get("vwap") or 0) * SIGMA_FLOOR_PCT
    wide = have_sigma and bn["sigma"] >= floor
    warm = have_sigma and wide and now_hhmm >= WARM_HHMM
    w = {**_EMPTY_WHERE, "px": fut, "px_why": _why(None if fut is not None else "no futures price on the tape"),
         "vwap": bn["vwap"] if have_sigma else None, "sigma": bn["sigma"] if have_sigma else None, "warm": warm,
         "zone_why": _why(None if warm else ("no bands on the tape yet" if not have_sigma
                          else f"σ {bn['sigma']:.1f} too narrow to name a zone" if not wide
                          else f"σ not trusted until {WARM_HHMM}"))}
    if warm:
        w["buy_zone"], w["sell_line"], w["sell_zone"] = [bn["d3"], bn["d2"]], bn["u3"], [bn["u2"], bn["u3"]]
        if fut is not None:
            w["z"] = round((fut - bn["vwap"]) / bn["sigma"], 3)
            # signed points to the nearer zone edge: buy edge is d2 (positive = zone still below price),
            # sell edge is u2 (positive = zone still above price); negative means price is past that edge
            db, ds = round(float(fut - bn["d2"]), 1), round(float(bn["u2"] - fut), 1)
            w["edge"] = {"side": "buy", "d": db} if abs(db) <= abs(ds) else {"side": "sell", "d": ds}
    if closed and closed[0].get("o") is not None and closed[-1].get("c") is not None:
        o, c = closed[0]["o"], closed[-1]["c"]
        bh, bl = max(closed, key=lambda b: b["h"]), min(closed, key=lambda b: b["l"])
        px = fut if fut is not None else c
        w.update(open=o, high={"p": bh["h"], "t": _hhmm(bh["t"])}, low={"p": bl["l"], "t": _hhmm(bl["t"])}, from_open=round(float(px - o), 1))
        dl, dh = px - bl["l"], bh["h"] - px
        w["off_extreme"] = {"which": "low", "d": round(float(dl), 1)} if dl <= dh else {"which": "high", "d": round(float(dh), 1)}
        wnd = closed[-12:]
        w["hour"] = {"bars": len(wnd), "net": round(float(wnd[-1]["c"] - wnd[0]["o"]), 1),
                     "travel": round(float(sum(abs(wnd[i]["c"] - (wnd[i - 1]["c"] if i else wnd[0]["o"])) for i in range(len(wnd)))), 1)}
    else:
        w["bars_why"] = _why("no closed bars posted" if not closed else "the first/last bar has no joined OHLC yet")
    return w


def _trapped(book: dict, closed: list, mins: dict, marks: list) -> dict:
    wm = book.get("warmap") or {}
    heat = wm.get("heat") or []
    t = {**_EMPTY_TRAPPED}
    if heat:
        legs = [(h["k"], s, h.get(f"{s}_pain") or 0, h.get(f"{s}_conf")) for h in heat for s in ("ce", "pe")]
        k, s, pain, conf = max(legs, key=lambda x: x[2])
        t["writers"] = {"side": s.upper() if pain > 0 else "none", "worst": {"k": k, "pain": round(pain, 1), "conf": conf} if pain > 0 else None,
                        "ce_chg": sum(h.get("ce_chg") or 0 for h in heat), "pe_chg": sum(h.get("pe_chg") or 0 for h in heat), "tag": "I"}
    else:
        t["writers_why"] = _why("tapemap heat not answered" if not wm else "no heat rows yet")
    if len(marks) >= 2:
        t0, t1 = (marks[-4] if len(marks) >= 4 else marks[0]), marks[-1]
        ch = window_change(mins, t0, t1)
        t["window"] = {"t0": t0, "t1": t1, "minutes": _mins(t1) - _mins(t0), "ce": sum(v[0] for v in ch.values()), "pe": sum(v[1] for v in ch.values())}
    else:
        t["window_why"] = _why("chain minutes not answered" if not mins else "fewer than 2 chain minutes")
    if len(marks) >= 4:
        paces = [window_change(mins, marks[i - 1], marks[i]) for i in range(1, len(marks))]
        ce_p = [sum(v[0] for v in p.values()) for p in paces]
        pe_p = [sum(v[1] for v in p.values()) for p in paces]

        def rank(xs):
            return round(sum(1 for x in xs if x <= xs[-1]) / len(xs), 2)
        t["pace"] = {"ce": rank(ce_p), "pe": rank(pe_p)}
    else:
        t["pace_why"] = _why("fewer than 4 chain minutes; nothing to rank")
    if closed and closed[0].get("o") is not None and closed[-1].get("c") is not None:
        t["fut_oi"] = {"d_oi": (closed[-1].get("oi") or 0) - (closed[0].get("oi") or 0), "d_px": round(float(closed[-1]["c"] - closed[0]["o"]), 1)}
    else:
        t["fut_oi_why"] = _why("no joined OHLC yet")
    sn = book.get("senses")
    if sn is None:
        t["gear_why"] = _why("senses not answered")
    elif sn.get("gear"):
        t["gear"] = sn["gear"]
    else:
        t["gear_why"] = _why("senses answered, no gear")
    return t


def _row(kind, p, **kw) -> dict:
    r = {"kind": kind, "p": float(p), "d": None, "size": None, "since": None, "leaned": None, "snapshot": False,
         "oi": None, "chg": None, "pain": None, "pain_tag": None, "conf": None, "state": None, "tests": None,
         "last_outcome": None, "strike": None, "agree": None}
    r.update(kw)
    return r


def _walls(tape: dict, book: dict, broke: list) -> dict:
    """One axis, futures frame. Tape walls with lean counts, OI strikes with pain (basis-shifted), levels with
    sequence-machine state, the prior session's H/L/C. A tape wall and an OI strike within one row of each other
    are one level and name each other (`agree`). Every row is on the wire; the face shows the nearest `cap` each side."""
    fut, lot, row = tape.get("futPx"), tape.get("lot"), float(tape.get("rowSize") or 5)
    wm, b = book.get("warmap") or {}, basis(tape, book)
    rows: List[dict] = []
    for w in tape.get("walls") or []:
        rows.append(_row("S" if w["side"] < 0 else "B", w["price"], size=(w["size"] * lot) if lot else None, since=w.get("since"),
                         leaned=int(w.get("hits") or 0), snapshot=bool(w.get("snapshot")), state="held"))
    oi_why = None
    if not wm:
        oi_why = _why("tapemap did not answer")
    elif b is None:
        oi_why = _why("no index spot; strikes cannot be placed")
    else:
        for h in wm.get("heat") or []:
            for side in ("ce", "pe"):
                if h.get(f"{side}_oi") is None:
                    continue
                rows.append(_row(side.upper(), float(h["k"]) + b, oi=h[f"{side}_oi"], chg=h.get(f"{side}_chg"), pain=h.get(f"{side}_pain"),
                                 pain_tag="I", conf=h.get(f"{side}_conf"), state="held", strike=float(h["k"])))
        for L in wm.get("levels") or []:
            st = (wm.get("sequence") or {}).get(f"{L['kind']}@{L['px']}")
            if not st:
                continue                       # no machine state: the chart draws the line; not a row
            rows.append(_row(L["kind"], float(L["px"]) + (b if L.get("frame") == "index" else 0.0),
                             state=st["state"], tests=st.get("tests"), last_outcome=st.get("last_outcome")))
    hlc = structure.prior_day_hlc(book["pivots"]) if book.get("pivots") else None
    prior_why = None
    if hlc:
        for kind, p in zip(("PDH", "PDL", "PDC"), hlc):
            rows.append(_row(kind, p))
    else:
        prior_why = _why("prior session H/L/C not answered (live._pivots)")
    # "within one row" is inclusive; when more than one OI strike qualifies for a tape wall the nearest wins
    # (a CE/PE pair at the same strike ties on distance -- the later one in heat order wins, as it always has)
    oi_rows = [r for r in rows if r["kind"] in ("CE", "PE")]
    for tr in (r for r in rows if r["kind"] in ("S", "B")):
        cands = [o for o in oi_rows if abs(tr["p"] - o["p"]) <= row]
        if cands:
            o = min(reversed(cands), key=lambda o: abs(tr["p"] - o["p"]))
            tr["agree"], o["agree"] = f"{o['kind']} {o['strike']:.0f}", f"{tr['kind']} {tr['p']:.0f}"
    for r in rows:
        r["d"] = round(float(r["p"] - fut), 1) if fut is not None else None
    rows.sort(key=lambda r: -r["p"])
    bn = _bands_now(tape)
    # THE WATCH LIST (spec §B). `prior` is the previous frame's own watch
    # object, handed over by the server so a broken level is remembered for
    # the rest of the session while this module stays pure and stateless.
    # `seq_fired_backfill` is the war map replay's own transitions, so a level
    # that broke before this process started still says so after a restart.
    wt = watch_mod.build(
        rows, fut, (bn or {}).get("sigma"), b,
        wm.get("dwell"), wm.get("sequence"), wm.get("seq_fired"), wm.get("runways"),
        book.get("minutes") or {}, book.get("peaks") or {}, book.get("watch_prior"),
        seq_fired_backfill=wm.get("seq_fired_backfill"))
    return {"rows": rows, "cap": WALL_CAP, "floors_taken": sum(1 for x in broke if x.get("side") == 1),
            "oi_why": oi_why, "prior_why": prior_why, "basis": b, "watch": wt}


def _place(p: float, bn: Optional[dict], walls_rows: list, row: float) -> Optional[dict]:
    """Where an event happened, in words: within one row (inclusive) of a held wall, an OI strike, or a level
    row (the NEAREST one; a wall wins a tie against a level), else inside a zone."""
    candidates = [r for r in walls_rows if r["kind"] in _WALL_KINDS + _LEVEL_KINDS and abs(r["p"] - p) <= row]
    if candidates:
        r = min(candidates, key=lambda r: (abs(r["p"] - p), 0 if r["kind"] in _WALL_KINDS else 1))
        return {"kind": "wall" if r["kind"] in _WALL_KINDS else "level", "label": f"at {r['kind']} {r['p']:.0f}"}
    if bn and bn.get("sigma"):
        if bn["d3"] <= p <= bn["d2"]:
            return {"kind": "zone", "label": "in the buy zone"}
        if bn["u2"] <= p <= bn["u3"]:
            return {"kind": "zone", "label": "in the sell zone"}
    return None


def _tape(tape: dict, closed: list, walls_rows: list) -> dict:
    bn, row = _bands_now(tape), float(tape.get("rowSize") or 5)
    # sorted newest-first by timestamp (never assume the feed's own append order)
    evs = sorted((e for e in (tape.get("events") or []) if e.get("p") is not None), key=lambda e: e["t"], reverse=True)[:4]
    # SIDE TRAVELS WITH THE EVENT. The extension already decides it per mark
    # (main.js: a trap carries the INVERTED side, because the trapped party is
    # the one that matters) and it was being dropped here. Colour on her chart
    # IS the side, so a screen without it can only draw a neutral mark or
    # invent one -- and an invented side is a direction verdict. -1 sell / +1
    # buy / 0 or None when the extension did not say.
    out = {**_EMPTY_TAPE, "events": [{"t": _hhmm(e["t"]), "kind": e["kind"], "p": float(e["p"]), "side": e.get("side"), "at": _place(float(e["p"]), bn, walls_rows, row)} for e in evs]}
    if closed:
        d = sum(b.get("delta", 0) or 0 for b in closed)
        # sign only: shape and sequence, never magnitude (stack doctrine); rank stays None until a within-session rank is defined
        out["aggressor"] = {"side": "sellers" if d < 0 else "buyers" if d > 0 else "flat", "rank": None}
    else:
        out["aggressor_why"] = _why("no closed bars; no sign to report")
    return out


def _tells(book: dict, closed: list, b: Optional[float], bn: Optional[dict]) -> list:
    tells = []
    heat = (book.get("warmap") or {}).get("heat") or []
    if heat and b is not None and closed and bn:
        px = closed[-1]["c"]
        below = sorted((h for h in heat if h.get("pe_oi") and h["k"] + b < px), key=lambda h: -h["pe_oi"])
        if below:
            k = below[0]["k"]
            tells.append({"name": "DOWN", "predicate": f"close < {k + b:.0f} AND PE {k:.0f} OI falling",
                          "target": f"{bn['d3']:.0f}", "negation": f"close back above {k + b:.0f}", "tag": "I"})
        above = sorted((h for h in heat if h.get("ce_oi") and h["k"] + b > px), key=lambda h: h["k"])
        if above:
            k = above[0]["k"]
            tells.append({"name": "PIN", "predicate": f"PE writing continues AND CE {k:.0f} OI falling",
                          "target": f"{k + b:.0f}", "negation": f"CE {k:.0f} OI still building", "tag": "I"})
    return tells


def _setup(tape: dict, book: dict, now_hhmm: str, walls: dict) -> dict:
    """The one verb: location from the 5-minute bands; state from the zone machine (book['zone_state'] /
    ['zone_state_sell'], run_states at SCORED_INTERVAL); flow from the tape's own events within three rows of the
    edge; the chain's confirm. FIRE only when both agree, once per zone visit keyed on the machine's reference bar."""
    bn, fut, closed = _bands_now(tape), tape.get("futPx"), tape.get("closed") or []
    senses = book.get("senses")
    if senses is None:
        confirm = {"value": "not wired", "why": _why("senses assembly not factored out; tape-only beep"),
                   "why_full": "the /api/senses assembly is not factored out yet; the beep is tape-only", "tag": "I"}
    else:
        cv = senses.get("confirm")
        confirm = {"value": cv or "UNKNOWN", "why": _why(None if cv else "pair rotation and OI deceleration not read"),
                   "why_full": None, "tag": "I"}
    S = {**_EMPTY_SETUP, "confirm": confirm,
         "tells": _tells(book, closed, walls.get("basis"), bn), "falsifies": "nothing to falsify before σ exists"}
    if not bn or not bn.get("sigma"):
        S["state_why"] = _why("no bands on the tape yet")
        return S
    if now_hhmm < WARM_HHMM:
        S["state"], S["state_why"] = "WARMUP", _why(f"σ not trusted until {WARM_HHMM}")
        return S
    in_buy = fut is not None and bn["d3"] <= fut <= bn["d2"]
    in_sell = fut is not None and bn["u2"] <= fut <= bn["u3"]

    def _last(zs):
        return (zs[-1] if isinstance(zs, list) else zs) if zs else None
    last_buy, last_sell = _last(book.get("zone_state")), _last(book.get("zone_state_sell"))
    use_sell = _pick_side(in_buy, in_sell, last_buy, last_sell) == "sell"
    last = last_sell if use_sell else last_buy
    side = "sell" if use_sell else "buy"
    S["side"] = side
    S["falsifies"] = f"a close past {bn['u3']:.0f} (+3σ) held for 3 bars" if use_sell else f"a close past {bn['d3']:.0f} (−3σ) held for 3 bars"
    if last:
        # band_rotation.run_states emits ref_low on the SELL side, ref_high on BUY
        ref = last.get("ref_low") if use_sell else last.get("ref_high")
        S.update(state=last.get("state", "PATA NAHI"), ref=ref, candles_left=last.get("candles_left"), level=last.get("level"))
    else:
        S["state_why"] = _why("zone machine not answering (run_states)")
    machine = S["state"]
    row = float(tape.get("rowSize") or 5)
    in_pocket = in_sell if use_sell else in_buy
    near_edge = bn["u2"] if use_sell else bn["d2"]
    # flow anchors on the band at this instant, or on the machine's own level once armed (the touch already happened)
    edge = near_edge if in_pocket else (S["level"] if machine in _ZONE_ACTIVE and S["level"] is not None else None)
    flow = [e for e in tape.get("events") or [] if edge is not None and e.get("p") is not None
            and abs(e["p"] - edge) <= 3 * row and e.get("kind") in CONFIRMS]
    S["flow"] = [{"t": _hhmm(e["t"]), "kind": e["kind"], "p": float(e["p"])} for e in flow]
    # THE REACH IS LATCHED AND THE KEY IS `arm.first_t` (spec §A.2, §A.3, §A.9.4).
    # `reached` was a live-price test that went false the moment price left the pocket -- the
    # arm, not the reach -- and the key was `ref_i`, which branch 3 of run_states moves on
    # every new lower low, so one setup wrote two record rows. visit.py owns both rules now;
    # frame.py places the answer and measures nothing.
    zs = book.get("zone_state_sell") if use_sell else book.get("zone_state")
    zs = zs if isinstance(zs, list) else []
    # THE BALLOT AND THE STATE MACHINE (spec §A). Composed, never measured
    # here: signals.py owns every comparison. Only the CE/PE rows are handed
    # over -- `walls.rows` never enters signals.py (spec §B.1, §H.1) -- and the
    # OI vote's `src` is "backfill" when the war map replayed a rebuilt grid.
    oi_rows = [r for r in (walls.get("rows") or []) if r.get("kind") in ("CE", "PE")]
    S["signal"], S["votes"] = signal_mod.build(
        tape, zs, side, oi_rows, book.get("sweeps") or [], now_hhmm,
        oi_backfill=bool((book.get("warmap") or {}).get("backfill")))
    v = visit_mod.current(tape, zs, side)
    S["reached"], S["in_pocket"] = v is not None, bool(in_pocket)
    # THE CHAIN-CONFIRM TERM IS DELETED, NOT REPAIRED (spec §A.5). `_book_for`
    # passes `senses: None` on every request, so `confirm` is permanently
    # "not wired" and this term was a no-op wearing a gate's clothes. The
    # pair-rotation confirm belongs on the contract chart where both legs
    # exist; on a single index series it is structurally UNKNOWN
    # (band_rotation.SINGLE_SERIES_CONFIRM_WHY) and always will be. `confirm`
    # stays on the frame as a printed field with its reason; it stops
    # pretending to gate.
    S["fire"] = S["reached"] and bool(flow)
    if v is not None:
        S["visit"] = v["visit_key"]
    elif closed:
        S["visit"] = None
    return S


def build(tape: dict, book: dict, now_hhmm: str) -> dict:
    book = book or {}
    closed, walls_in, broke = tape.get("closed") or [], tape.get("walls") or [], tape.get("broke") or []
    mins = book.get("minutes") or {}
    marks = sorted(mins)
    missing: List[str] = []
    if not book.get("warmap"):
        missing.append("warmap")
    if not mins:
        missing.append("chain minutes")
    sess = (tape.get("session") or "").split("|")
    day = sess[-1] if len(sess) >= 3 else None
    head = _safe(lambda: _head(tape, book), _EMPTY_HEAD)
    # the warm-up rule (σ trusted from WARM_HHMM) is judged on the TAPE's clock -- the close time of the last
    # closed bar -- not the wall clock: a session replayed at night, or a late start, carries its own time.
    # The wall clock is the fallback only when no bar has closed.
    iv_ms = int(tape.get("interval") or 5) * 60000
    clock = _hhmm(closed[-1]["t"] + iv_ms) if closed and closed[-1].get("t") is not None else now_hhmm
    where = _safe(lambda: _where(tape, closed, clock), _EMPTY_WHERE)
    trapped = _safe(lambda: _trapped(book, closed, mins, marks), _EMPTY_TRAPPED)
    walls = _safe(lambda: _walls(tape, book, broke), _EMPTY_WALLS)
    tape_o = _safe(lambda: _tape(tape, closed, walls["rows"]), _EMPTY_TAPE)
    setup = _safe(lambda: _setup(tape, book, clock, walls), _EMPTY_SETUP)
    # THE FADE GATE (research-findings §1d). The SAME function the /api/oihist
    # route calls, on the same minute grid this frame already receives for
    # `_trapped` -- one rule, one language. It SUPPRESSES NOTHING: `setup` is
    # returned untouched and every row the log would have written still gets
    # written, because the only way to judge this gate later is rows logged
    # forward beside it. See §1d, "What is NOT being changed".
    fronts_rows, fronts_err = _safe_list(lambda: fronts_mod.read(mins, book.get("peaks")))
    setup["gate"] = _safe(
        lambda: fronts_mod.fade_gate(fronts_rows, setup.get("side") or "buy",
                                     book.get("plays")),
        dict(_EMPTY_GATE))

    def _events_and_armed():
        armed = []
        for zs_list in (book.get("zone_state"), book.get("zone_state_sell")):
            if isinstance(zs_list, list):
                armed += [{"t": _hhmm(closed[i]["t"]), "kind": "armed"} for i, s in enumerate(zs_list) if isinstance(s, dict) and s.get("arm") is not None and i < len(closed)]
        return ([{"t": _hhmm(e["t"]), "kind": e["kind"]} for e in (tape.get("events") or [])]
                + [{"t": _hhmm(t["t"]), "kind": "tap"} for t in (tape.get("taps") or [])]
                + [{"t": w["since"], "kind": "wall"} for w in walls_in if w.get("since")]
                + [{"t": _hhmm(b["brokenT"]), "kind": "lost"} for b in broke if b.get("brokenT")] + armed)
    events, events_why = _safe_list(_events_and_armed)
    # POSITIONING BREADTH (spec §C.2), a TOP-LEVEL object because it is a
    # property of the session and not of the setup in play. The watched
    # strikes are the ladder's own OI rows, so breadth and the war map are
    # always describing the same fronts.
    watched = [(int(r["strike"]), r["kind"].lower())
               for r in (walls.get("rows") or [])
               if r.get("kind") in ("CE", "PE") and r.get("strike") is not None]
    breadth_o = _safe(lambda: breadth_mod.build(
        mins, closed, watched, book.get("regime"), book.get("pinned"), clock),
        _EMPTY_BREADTH)
    return {"ok": True, "idx": tape.get("idx") or "NIFTY", "ts": now_hhmm, "day": day, "interval": sess[1] if len(sess) >= 3 else None,
            "have_bars": len(closed), "lot": tape.get("lot"), "missing": missing, "coverage": book.get("coverage") or {},
            "events": events, "events_why": events_why, "taps": tape.get("taps") or [], "head": head, "record": {"written": False},
            "where": where, "trapped": trapped, "walls": walls, "tape": tape_o, "setup": setup, "breadth": breadth_o,
            # §1d. `trapped` answers "who is in pain" off max(pain) over every
            # leg; this answers "who stopped adding first, near the money".
            # They are different questions and on 2026-09-22 they named
            # different strikes -- 23700 and 23400 -- so both stay published.
            # NULL, not [], when it could not be read: this contract's rule is
            # that a `*_why` is non-null exactly when its field is null
            # (test_frame.test_every_why_is_non_null_exactly_when_its_field_is_null),
            # and an empty list would read as "checked, found no fronts".
            "fronts": fronts_rows or None,
            "fronts_why": None if fronts_rows else
                          (fronts_err or ("chain minutes not answered" if not mins else
                                          "no minute carries a spot and a strike grid yet"))}
