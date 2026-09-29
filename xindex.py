"""xindex.py -- THE CROSS-INDEX READ and LOOK HERE (docs/reader/9-cross-index-design.md). SHADOW ONLY. Pure.

Built ON TOP of reader.py's leg rows: it never cuts, measures or classifies a leg itself. Per index it takes the reader's
reply shape (confirmed `legs`, the `forming` leg, `auction`, `ruler`), her zone machine's state (never a reconstruction),
and the option chain; it returns, once per 3-minute bar close:

  X1 SYNC      do the legs point the same way, how big (in each index's own ruler), does WHO agree (NIFTY/BANKNIFTY)
  X2 EXTREMES  at the latest push: did each index take its own previous swing high/low (TOOK / EQUAL / FAILED)?
               CONFIRMED / DIVERGENT / BARABAR, with the level that ends a divergence
  X3 LEAD      who turned first THIS time (minute stamps), never "X leads"
  X4 WALLS     option OI added within reach of price, per index, and whether the three agree
  X5 POTENTIAL conditions forming (her zone armed, a range edge, writing at a wall), with levels
  LOOK HERE    a COUNT of six lines (zone, flow, WHO, walls, sync, extremes) -- never a %, never a probability --
               awarded on her zone + 2 more lines or 4 without it, held with hysteresis, capped per session
  STATE WORD   move ban sakta hai / chal raha hai / ho gaya, each with its start, confirm and kill levels

THIN TAPE. SENSEX's future trades 1-3k lots a day (9-cross-index-design.md §2.1): its flow and WHO never vote, it is a
witness (never the decider) in SYNC and EXTREMES, and without her zone it cannot reach the LOOK HERE bar.
CASH AUCTION. From 15:15 the spot indices freeze (NSE and BSE, measured 29 Sep): price reads are CAN'T CHECK and
LOOK HERE is released. HOLES. An index whose last minute is stale is CAN'T CHECK for every read and never awarded.

State is a plain dict carried bar to bar; `step()` for a bar already stepped returns the stored output unchanged
(no repaint). No hit rate, no outcome, anywhere.
"""
from __future__ import annotations

import statistics as st
from typing import Dict, List, Optional, Tuple

import reader

REV = "xindex-shadow-1"
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
ORDER = {"NIFTY": 0, "BANKNIFTY": 1, "SENSEX": 2}        # tie-break by liquidity, deterministic

# ---- THE THRESHOLD SHEET (h): every hand-picked number of this read, in one place, for her signature.
SHEET: List[Tuple[str, object, str]] = [
    ("THIN_IDX", ("SENSEX",), "a thin tape: the SENSEX future trades 687-3,419 lots a day (§2.1); flow/WHO never vote, "
                              "it witnesses SYNC/EXTREMES but never decides them"),
    ("SESSION_OPEN", 555, "09:15 in minutes of the day: bar k spans 09:15 + 3k"),
    ("BAR", 3, "minutes: evaluated at 3-minute bar closes, her canonical interval"),
    ("FROM", 570, "09:30: the first close of a bar at or after her 09:25 zone anchor; no read before it"),
    ("FREEZE", 915, "15:15: cash closing auction, spot frozen on NSE and BSE [M 29 Sep]; later bars: price reads "
                    "CAN'T CHECK and LOOK HERE released"),
    ("STALE", 2, "minutes: an index whose last minute is older than this at the bar close is a hole: CAN'T CHECK"),
    ("MATCH", 10, "minutes: a peer's push within 10 min of the newest is the same swing (81% N-B, 94% N-S, §2.4)"),
    ("TIE", 1, "minutes: turns within 1 minute are 'saath mein'; the canonical minute resolves no less"),
    ("TOL", 0.25, "x ruler: TOOK / EQUAL / FAILED band at an extreme"),
    ("SMALL", 0.5, "x ruler: a divergence whose failing gap is under this is labelled 'chhota'"),
    ("SIZE", 1.0, "x ruler: a leg of at least this is a running move; a peer under it is 'kamzor' sync"),
    ("NEAR", 0.5, "x ruler: price within this of a range edge is 'kinare par' (potential)"),
    ("SPENT", 2.0, "x ruler: 'ho gaya' = last confirmed leg >= this while the counter-leg is under SIZE"),
    ("REACH", 1.5, "x ruler: an option strike within this of price is 'within reach'"),
    ("WRITE_MIN", 15, "minutes: the OI-add window at the walls"),
    ("NOISE_Z", 3.0, "a strike's add counts only beyond 3 x robust sigma of every strike's add in the window"),
    ("DOM", 1.5, "one side's add must beat the other's by 1.5x to vote"),
    ("AWARD_ZONE", 3, "LOOK HERE with her zone among the lines: zone + 2 more"),
    ("AWARD", 4, "LOOK HERE without her zone: 4 lines"),
    ("MARGIN", 2, "lines for must beat lines against by at least 2"),
    ("SWITCH", 2, "a challenger must beat the holder by at least 2 lines"),
    ("HOLD", 2, "bars (6 min) a holder keeps LOOK HERE before any switch"),
    ("COOL", 2, "bars (6 min) after a release before any new award: 0 flips inside 6 minutes"),
    ("CAP", 16, "LOOK HERE changes per session; past it LOOK HERE stays blank for the day and says why"),
]
TH: Dict[str, object] = {k: v for k, v, _ in SHEET}
LINES = ("zone", "flow", "who", "walls", "sync", "ext")
WORD = {"ban_sakta": "Move ban sakta hai", "chal_raha": "Move chal raha hai", "ho_gaya": "Move ho gaya",
        "range": "Range, beech mein", "none": "Koi saaf move nahi", "cant": "Check nahi"}
ZWORD = {"ARMED": "armed", "TRIGGERED": "trigger hua", "IN_TRADE": "trade mein"}
SIDE = {1: "kharid", -1: "bikri"}
ARROW = {1: "▲", -1: "▼", 0: "·"}


# ---- helpers -------------------------------------------------------------------------------------------------
def mod(ms: int) -> int:
    """Minute of the day, IST."""
    return (int(ms) // 60000 + 330) % 1440


def hm(ms: int) -> str:
    m = mod(ms)
    return f"{m // 60:02d}:{m % 60:02d}"


def bar_of(asof: int) -> int:
    """The bar that CLOSES at `asof` (a 3-minute boundary): 09:18 closes bar 0."""
    return (mod(asof) - int(TH["SESSION_OPEN"])) // int(TH["BAR"]) - 1


def thin(idx: str) -> bool:
    return idx in TH["THIN_IDX"]


def num(x: float) -> str:
    return f"{x:,.0f}" if abs(x) >= 1000 else f"{x:,.1f}"


def _legs(s: dict) -> List[dict]:
    return [L for L in (s.get("legs") or []) if L.get("dir") in (1, -1)]


def _live(s: Optional[dict], asof: int) -> Tuple[bool, str]:
    """(checkable, why not). A reply that is not ok, has no ruler, or whose last minute is stale is a hole."""
    if not s:
        return False, "no reader reply"
    if not s.get("ok", True):
        return False, s.get("why") or "reader not ok"
    if not s.get("ruler"):
        return False, "reader warming: no ruler yet"
    t_last = s.get("t_last")
    if t_last is not None and asof - (t_last + 60000) > int(TH["STALE"]) * 60000:
        return False, f"data hole: last minute {hm(t_last)}"
    return True, ""


# ---- walls (X4 input): pure, from two option-chain snapshots -----------------------------------------------------
def walls(now: Optional[dict], then: Optional[dict], px: float, delta: float, lot: int,
          day: Optional[str] = None) -> Optional[dict]:
    """OI added over the window at the strikes within REACH x ruler of price. vote +1 = PE written below (a floor),
    -1 = CE written above (a lid), 0 = neither or both. None when a snapshot is missing (CAN'T CHECK)."""
    if not now or not then or not now.get("strikes") or not then.get("strikes") or not delta:
        return None
    was = {(k.get("k"), s): (k.get(s) or {}).get("oi") for k in then["strikes"] for s in ("ce", "pe")}
    adds, ce, pe = [], [], []
    reach = float(TH["REACH"]) * delta
    for k in now["strikes"]:
        for s in ("ce", "pe"):
            o1, o0 = (k.get(s) or {}).get("oi"), was.get((k.get("k"), s))
            if o1 is None or o0 is None:
                continue
            a = (o1 - o0) / lot
            adds.append(a)
            if s == "ce" and px <= k["k"] <= px + reach:
                ce.append((k["k"], a))
            elif s == "pe" and px - reach <= k["k"] <= px:
                pe.append((k["k"], a))
    sig = reader.robust_sigma(adds) or 0.0
    floor = float(TH["NOISE_Z"]) * sig
    c = max(ce, key=lambda x: x[1]) if ce else None
    p = max(pe, key=lambda x: x[1]) if pe else None
    cv = c[1] if c and c[1] > floor else 0.0
    pv = p[1] if p and p[1] > floor else 0.0
    exp = now.get("expiry")
    tag = " · expiry din" if day and exp == day else ""
    if cv and cv > float(TH["DOM"]) * pv:
        vote, why = -1, f"CE likh rahe {num(c[0])} (+{num(cv)} lots/{TH['WRITE_MIN']}m){tag}"
    elif pv and pv > float(TH["DOM"]) * cv:
        vote, why = 1, f"PE likh rahe {num(p[0])} (+{num(pv)} lots/{TH['WRITE_MIN']}m){tag}"
    elif cv or pv:
        vote, why = 0, f"dono taraf likh rahe (CE +{num(cv)} / PE +{num(pv)}){tag}"
    elif not ce and not pe:
        vote, why = 0, "koi strike pahunch mein nahi"
    else:
        vote, why = 0, f"pahunch mein koi likhai noise ({num(floor)} lots) se upar nahi{tag}"
    return {"vote": vote, "why": why, "ce": list(c) if c else None, "pe": list(p) if p else None,
            "floor": round(floor, 1), "expiry": exp, "zero_dte": bool(tag), "tag": "[M] OI · [I] meaning"}


# ---- zone ----------------------------------------------------------------------------------------------------
def _zone(z: Optional[dict]) -> Tuple[int, Optional[dict]]:
    """(side, state) of her machine: +1 BUY d2, -1 SELL u2, 0 WAITING. Both sides active: the more advanced wins;
    an exact tie is no side (never guessed)."""
    act = []
    for side, key in ((1, "buy"), (-1, "sell")):
        x = (z or {}).get(key) or {}
        if x.get("state") in ZWORD:
            act.append((0 if x["state"] == "ARMED" else 1, side, x))
    if not act:
        return 0, None
    act.sort(key=lambda a: a[0], reverse=True)
    if len(act) == 2 and act[0][0] == act[1][0]:
        return 0, None
    return act[0][1], act[0][2]


# ---- per-index pieces -------------------------------------------------------------------------------------------
def _dir(s: dict) -> int:
    f = s.get("forming")
    return f["dir"] if f and f.get("dir") in (1, -1) else 0


def _size(s: dict) -> float:
    f = s.get("forming")
    return abs(f.get("pts") or 0.0) / s["ruler"] if f and s.get("ruler") else 0.0


def _push(s: dict, typ: int) -> Optional[dict]:
    """The index's latest extreme of type `typ` (+1 high, -1 low) and the one before it: the forming leg's running
    extreme when it pushes that way, else the last confirmed leg ending there. Reader objects only."""
    ends = [(L["t1"], L["px1"]) for L in _legs(s) if L["dir"] == typ]
    f = s.get("forming")
    if f and f.get("dir") == typ and f.get("px1") is not None:
        ends.append((f["t1"], f["px1"]))
    if len(ends) < 2:
        return None
    (t_new, p_new), (t_old, p_old) = ends[-1], ends[-2]
    return {"t": t_new, "px": p_new, "ref": p_old, "ref_t": t_old, "gap": (p_new - p_old) * typ}


def extremes(snaps: Dict[str, dict], ok: Dict[str, bool], asof: int, typ: int) -> Optional[dict]:
    """X2-live for one type. An event exists when the newest push among the non-thin indices is within MATCH of now.
    Each index: TOOK / EQUAL / FAILED against its own previous extreme (TOL x its ruler); a push older than MATCH
    before the newest is NAHI (no fresh push = did not take it). The verdict is decided by the non-thin indices."""
    if mod(asof) < int(TH["FROM"]) or mod(asof) > int(TH["FREEZE"]):
        return None
    pushes = {i: _push(snaps[i], typ) for i in IDXS if ok.get(i)}
    firm = {i: p for i, p in pushes.items() if p and not thin(i)}
    if not firm:
        return None
    newest = max(p["t"] for p in firm.values())
    if asof - (newest + 60000) > int(TH["MATCH"]) * 60000:
        return None
    per = {}
    for i, p in pushes.items():
        if p is None:
            per[i] = {"status": "WARMING", "why": "do extreme abhi nahi"}
            continue
        tol = float(TH["TOL"]) * snaps[i]["ruler"]
        if newest - p["t"] > int(TH["MATCH"]) * 60000:
            st_ = "NAHI"
        else:
            st_ = "TOOK" if p["gap"] > tol else "FAILED" if p["gap"] < -tol else "EQUAL"
        per[i] = {"status": st_, "t": hm(p["t"]), "t_ms": p["t"], "px": p["px"], "ref": p["ref"],
                  "gap": round(p["gap"], 1), "rulers": round(p["gap"] / snaps[i]["ruler"], 2), "thin": thin(i)}
    fs = [per[i]["status"] for i in per if not thin(i) and per[i]["status"] != "WARMING"]
    if not fs:
        return None
    took, fail = "TOOK" in fs, any(x in ("FAILED", "NAHI") for x in fs)
    if len(fs) < 2:
        verdict = "PARTIAL"                   # one firm index checkable: nothing to confirm or diverge against
    else:
        verdict = "DIVERGENT" if took and fail else "CONFIRMED" if all(x == "TOOK" for x in fs) \
            else "BARABAR" if took or "EQUAL" in fs else "NONE"
    word = "high" if typ > 0 else "low"
    kind = "naya high" if typ > 0 else "naya low"
    if verdict == "PARTIAL":
        one = next(i for i in per if not thin(i) and per[i]["status"] != "WARMING")
        chip = f"{one} {per[one]['status'].lower()} · peer check nahi"
        ends = None
    elif verdict == "CONFIRMED":
        chip = "Teeno ne " + kind + " banaya" if all(per[i]["status"] == "TOOK" for i in per) else \
            "NIFTY/BANKNIFTY ne " + kind + " banaya"
        ends = None
    elif verdict == "DIVERGENT":
        a = [i for i in per if not thin(i) and per[i]["status"] == "TOOK"]
        b = [i for i in per if not thin(i) and per[i]["status"] in ("FAILED", "NAHI")]
        small = all(abs(per[i]["gap"]) < float(TH["SMALL"]) * snaps[i]["ruler"] for i in b if per[i]["status"] == "FAILED")
        chip = f"{'/'.join(a)} ne {kind} banaya, {'/'.join(b)} ne nahi" + (" (chhota)" if small else "")
        ends = {i: per[i]["ref"] for i in b}                  # the failing index taking its own extreme ends it
    elif verdict == "BARABAR":
        chip = f"{word.capitalize()} barabar · koi saaf {kind} nahi"
        ends = None
    else:
        chip = f"Kisi ne {kind} nahi banaya"
        ends = None
    wit = [f"{i} {per[i]['status'].lower()} (patla)" for i in per if thin(i) and per[i]["status"] != "WARMING"]
    if chip.startswith("Teeno"):
        wit = []
    return {"type": word, "verdict": verdict, "per": per, "chip": chip + (" · " + ", ".join(wit) if wit else ""),
            "ends": ends, "tag": "[M]"}


def lead(ev: Optional[dict]) -> Optional[dict]:
    """X3: who made this push first, THIS time. Minute stamps only; a spread within TIE is 'saath mein'."""
    if not ev:
        return None
    ts = {i: p["t_ms"] for i, p in ev["per"].items() if p.get("t_ms") and p["status"] in ("TOOK", "EQUAL")}
    if len(ts) < 2:
        return None
    first = min(ts, key=lambda i: (ts[i], ORDER[i]))
    spread = (max(ts.values()) - min(ts.values())) // 60000
    if spread <= int(TH["TIE"]):
        chip = f"Saath mein {ev['type']} · {hm(min(ts.values()))}"
    else:
        chip = f"{first} {spread} min pehle ({hm(ts[first])})"
    return {"first": first if spread > int(TH["TIE"]) else None, "spread_min": spread,
            "stamps": {i: hm(t) for i, t in ts.items()}, "chip": chip, "tag": "[M]"}


def sync(snaps: Dict[str, dict], ok: Dict[str, bool], asof: int) -> dict:
    """X1: legs' directions and sizes (rulers), the odd one named; WHO agreement between NIFTY and BANKNIFTY."""
    if mod(asof) > int(TH["FREEZE"]):
        return {"state": "CANT", "chip": "Cash auction · 15:15 se check nahi", "dots": {}}
    dots = {}
    for i in IDXS:
        if not ok.get(i) or not _dir(snaps[i]):
            dots[i] = {"dir": 0, "size": None, "thin": thin(i)}
        else:
            dots[i] = {"dir": _dir(snaps[i]), "size": round(_size(snaps[i]), 1), "thin": thin(i)}
    firm = [i for i in IDXS if not thin(i)]
    if any(dots[i]["dir"] == 0 for i in firm):
        miss = [i for i in firm if dots[i]["dir"] == 0]
        return {"state": "CANT", "chip": f"Sync check nahi ({'/'.join(miss)})", "dots": dots}
    d0 = dots[firm[0]]["dir"]
    same = all(dots[i]["dir"] == d0 for i in firm)
    sizes = " · ".join(f"{i} {dots[i]['size']}δ" for i in IDXS if dots[i]["dir"])
    tn = [i for i in IDXS if thin(i) and dots[i]["dir"] not in (0, d0)]
    note = (" · " + "/".join(tn) + " alag (patla)") if tn else ""
    if same:
        weak = [i for i in IDXS if dots[i]["dir"] == d0 and dots[i]["size"] < float(TH["SIZE"])]
        stt = "KAMZOR" if weak else "SAATH"
        chip = (f"Teeno saath {ARROW[d0]}" if not tn and all(dots[i]['dir'] == d0 for i in IDXS)
                else f"NIFTY/BANKNIFTY saath {ARROW[d0]}")
        if weak:
            chip = f"Saath par kamzor {ARROW[d0]} · {'/'.join(weak)} < {TH['SIZE']:g}δ"
        chip += " · " + sizes + note
    else:
        dirs = {i: dots[i]["dir"] for i in IDXS if dots[i]["dir"]}
        up = [i for i in dirs if dirs[i] > 0]
        dn = [i for i in dirs if dirs[i] < 0]
        odd = up if len(up) < len(dn) else dn
        stt = "ALAG"
        chip = f"{'/'.join(odd)} alag {ARROW[dirs[odd[0]]]} · {'/'.join(i for i in dirs if i not in odd)} " \
               f"{ARROW[-dirs[odd[0]]]}" + note
    fw = {i: (snaps[i].get("forming") or {}).get("who", {}).get("class") for i in firm}
    wv = [c for c in fw.values() if c and c != "oi_cant"]
    who = ("WHO: dono mein " + reader.Engine.WORDS[wv[0]][1].lower()) if len(wv) == 2 and wv[0] == wv[1] else \
        ("WHO: " + ", ".join(f"{i} {reader.Engine.WORDS[c][1].lower()}" for i, c in fw.items() if c)) if wv else \
        "WHO check nahi"
    key = stt + " " + "".join(ARROW[dots[i]["dir"]] for i in IDXS)
    return {"state": stt, "key": key, "chip": chip, "who": who, "dots": dots, "tag": "[M] legs · [I] WHO"}


# ---- the six lines for one index and one direction ------------------------------------------------------------
def _flow(s: dict, D: int, i: str):
    if thin(i):
        return None, "flow patla (future thin)"
    f = s.get("forming")
    if not f:
        return 0, "koi leg nahi"
    ux = f.get("ux") or {}
    if ux.get("state") == "cant":
        return None, "flow check nahi: " + str(ux.get("why") or "")
    w = f.get("who") or {}
    agg, ab, d = w.get("aggressor") or 0, bool(w.get("absorbed")), f["dir"]
    if not agg:
        return 0, "koi pakka taraf nahi"
    if agg == d:
        s_leg, word = (-1, f"{SIDE[agg]} dabi") if ab else (1, f"{SIDE[agg]} dabav")
    else:                                     # price went with the leg against its aggressor: the aggressor absorbed
        s_leg, word = 1, f"{SIDE[agg]} dabi"
    return (s_leg if d == D else -s_leg), word + " [I]"


def _who(s: dict, D: int, i: str):
    if thin(i):
        return None, "WHO patla (future thin)"
    f = s.get("forming")
    if not f:
        return 0, "koi leg nahi"
    w = f.get("who") or {}
    c, d = w.get("class"), f["dir"]
    if not c or c == "oi_cant":
        return None, "OI check nahi"
    word = reader.Engine.WORDS[c][1]
    opening, closing = c in ("new_longs", "new_shorts"), c in ("short_covering", "long_liquidation")
    if closing and (w.get("roll") or w.get("expiring")):
        return 0, word + " (ya roll) [I]"
    if d == D:
        return (1 if opening else 0), word + " [I]"
    return (1 if closing else -1 if opening else 0), word + (" (ulti taraf naye nahi)" if closing else "") + " [I]"


def _sync_line(i: str, D: int, snaps, ok, zs, asof):
    if mod(asof) > int(TH["FREEZE"]):
        return None, "cash auction · check nahi"
    firm = [p for p in IDXS if p != i and not thin(p)]
    if any(not ok.get(p) for p in firm):
        return None, "peer check nahi (" + "/".join(p for p in firm if not ok.get(p)) + ")"
    def with_(p):
        side = zs[p][0]
        return side == D if side else _dir(snaps[p]) == D
    n = sum(1 for p in firm if with_(p))
    wit = [p for p in IDXS if p != i and thin(p) and ok.get(p)]
    note = "".join(f" · {p} {'saath' if with_(p) else 'alag'} (patla)" for p in wit)
    names = "/".join(firm)
    if n == len(firm):
        return 1, f"{names} saath{note}"
    if n == 0:
        return -1, f"{names} alag · akela{note}"
    return 0, f"peers bante hue{note}"


def _ext_line(i: str, D: int, fade: bool, ev_hi, ev_lo, asof):
    if mod(asof) > int(TH["FREEZE"]):
        return None, "cash auction · check nahi"
    ev = (ev_lo if D > 0 else ev_hi) if fade else (ev_hi if D > 0 else ev_lo)
    if not ev or ev["verdict"] in ("NONE", "PARTIAL"):
        return 0, "koi taaza extreme nahi"
    if ev["verdict"] == "DIVERGENT":
        return (1 if fade else -1), ev["chip"]
    if ev["verdict"] == "CONFIRMED":
        return (-1 if fade else 1), ev["chip"]
    return 0, ev["chip"]


def _lines(i: str, D: int, snaps, ok, zs, wl, ev_hi, ev_lo, asof) -> Dict[str, dict]:
    s = snaps[i]
    side, zst = zs[i]
    out = {}
    if s.get("zone") is None:
        out["zone"] = (None, "zone check nahi: " + str(s.get("zone_why") or "no zone state"))
    elif side == 0:
        out["zone"] = (0, "zone WAITING")
    else:
        lv = zst.get("level")
        out["zone"] = (1 if side == D else 0,
                       f"zone {'d2' if side > 0 else 'u2'} {ZWORD[zst['state']]}" + (f" {num(lv)}" if lv else ""))
    out["flow"] = _flow(s, D, i)
    out["who"] = _who(s, D, i)
    w = wl.get(i)
    out["walls"] = (None, "chain check nahi") if w is None else (w["vote"] * D if w["vote"] else 0, w["why"])
    out["sync"] = _sync_line(i, D, snaps, ok, zs, asof)
    out["ext"] = _ext_line(i, D, bool(side) and side == D, ev_hi, ev_lo, asof)
    return {k: {"vote": v, "why": why} for k, (v, why) in out.items()}


def _count(lines: Dict[str, dict]) -> Tuple[int, int, int]:
    v = [x["vote"] for x in lines.values()]
    return sum(1 for x in v if x == 1), sum(1 for x in v if x == -1), sum(1 for x in v if x is not None)


# ---- state word and its levels ------------------------------------------------------------------------------------
def _pushing(s: dict) -> int:
    """The forming leg's direction while it is still pushing: at least SIZE rulers and within NEAR x ruler of its
    own extreme. 0 when stalled. (A reader leg is born >= 1 ruler, so size alone never says 'running'.)"""
    f, dl = s.get("forming"), s.get("ruler")
    if not f or not dl or f.get("dir") not in (1, -1):
        return 0
    size, back = abs(f.get("pts") or 0.0) / dl, (f.get("back") or 0.0) / dl
    return f["dir"] if size >= float(TH["SIZE"]) and back <= float(TH["NEAR"]) else 0


def _edge(s: dict) -> int:
    """In a RANGE: +1 near the upper edge, -1 near the lower (within NEAR x ruler), else 0 (both ways scored)."""
    band, dl, f = (s.get("auction") or {}).get("band"), s.get("ruler"), s.get("forming")
    px = f.get("now") if f and f.get("now") is not None else s.get("px")
    if not band or not dl or px is None:
        return 0
    near = float(TH["NEAR"]) * dl
    return 1 if band[1] - px <= near else -1 if px - band[0] <= near else 0


def _word(i: str, s: dict, D: int, side: int, zst: Optional[dict]) -> Tuple[str, dict]:
    """The state word and its levels, from her zone first, then the reader's auction and forming leg."""
    dl = s["ruler"]
    f = s.get("forming")
    au = s.get("auction") or {}
    px = f.get("now") if f and f.get("now") is not None else s.get("px")
    if side and zst:
        stop = zst.get("stop")
        if zst["state"] == "ARMED":
            ref = zst.get("ref")
            return "ban_sakta", {"start": ref, "confirm": f"3-min close {'upar' if side > 0 else 'neeche'} "
                                                         f"{num(ref) if ref else 'ref candle'} (her trigger)",
                                 "kill": stop, "from": "zone"}
        return "chal_raha", {"start": zst.get("level"), "confirm": "her trade is on", "kill": stop, "from": "zone"}
    if au.get("state") == "RANGE" and au.get("band"):
        lo, hi = au["band"]                   # a range IS the coil: one word, both levels (no edge-to-edge churn)
        return "ban_sakta", {"start": round(hi + dl, 1) if D > 0 else round(lo - dl, 1) if D < 0 else None,
                             "up": round(hi + dl, 1), "down": round(lo - dl, 1), "kill": None, "from": "range",
                             "confirm": f"range {num(lo)}–{num(hi)} toota: upar {num(hi + dl)} / neeche {num(lo - dl)}"}
    if f and D and _pushing(s) == D:
        return "chal_raha", {"start": f["px0"], "confirm": f"leg {abs(f['pts']) / dl:.1f}δ, extreme {num(f['px1'])}",
                             "kill": round(f["px1"] - D * dl, 1), "from": "leg"}
    if f and abs(f.get("pts") or 0) >= float(TH["SPENT"]) * dl and (f.get("back") or 0) > float(TH["NEAR"]) * dl:
        return "ho_gaya", {"start": f["px0"], "end": f["px1"], "rulers": round(abs(f["pts"]) / dl, 1),
                           "confirm": f"extreme {num(f['px1'])} {hm(f['t1'])}, abhi {num(f['back'])} peeche",
                           "kill": None, "dir": f["dir"], "from": "leg"}
    if f and abs(f.get("pts") or 0) < float(TH["SPENT"]) * dl and (f.get("back") or 0) > float(TH["NEAR"]) * dl:
        return None, {}                       # a small leg that stalled: no new word, the last one holds
    return "none", {"start": None, "confirm": None, "kill": None, "from": None}


def _potential(i, s, zs, wl) -> List[str]:
    out = []
    side, zst = zs[i]
    if side and zst and zst["state"] == "ARMED":
        out.append(f"zone {'d2' if side > 0 else 'u2'} armed")
    au = s.get("auction") or {}
    if au.get("state") == "RANGE" and au.get("band"):
        out.append(f"range {num(au['band'][0])}–{num(au['band'][1])}")
    w = wl.get(i)
    if w and w["vote"]:
        out.append(w["why"])
    if s.get("compression") is True:
        out.append("compression")
    return out


# ---- one bar ----------------------------------------------------------------------------------------------------
def new_state() -> dict:
    return {"bar": None, "holder": None, "hold_D": None, "hold_need": None, "held": 0, "cool": 0, "changes": 0,
            "awards": 0, "switches": 0, "releases": 0, "capped": False, "flips6": 0, "hist": [], "ws": {},
            "words": {}, "word_changes": {i: 0 for i in IDXS}, "out": None}


def step(asof: int, snaps: Dict[str, dict], state: Optional[dict] = None) -> Tuple[dict, dict]:
    """One 3-minute bar close. `snaps[idx]` = the reader's reply for that index as of `asof` (ok, ruler, legs,
    forming, auction, t_last, px) plus `zone` ({"buy": {...}, "sell": {...}} from her machine, or None with
    `zone_why`), `walls` (walls() output or None) and optional `compression`. Returns (output, new state).
    A bar already stepped returns its stored output: nothing repaints."""
    state = dict(state) if state else new_state()
    b = bar_of(asof)
    if state["bar"] is not None and b <= state["bar"]:
        return state["out"], state
    snaps = {i: dict(snaps.get(i) or {}) for i in IDXS}
    ok, why_not = {}, {}
    for i in IDXS:
        ok[i], why_not[i] = _live(snaps[i], asof)
    early, frozen = mod(asof) < int(TH["FROM"]), mod(asof) > int(TH["FREEZE"])
    zs = {i: _zone(snaps[i].get("zone")) if ok[i] else (0, None) for i in IDXS}
    wl = {i: snaps[i].get("walls") for i in IDXS}
    ev_hi = extremes(snaps, ok, asof, 1)
    ev_lo = extremes(snaps, ok, asof, -1)
    rows = {}
    for i in IDXS:
        s = snaps[i]
        if not ok[i]:
            rows[i] = {"ok": False, "why": why_not[i], "D": 0, "word": "cant", "chip": "Check nahi · " + why_not[i],
                       "levels": {}, "lines": {k: {"vote": None, "why": why_not[i]} for k in LINES},
                       "n_for": 0, "n_against": 0, "n_check": 0, "thin": thin(i), "potential": []}
            continue
        if frozen:
            rows[i] = {"ok": True, "why": None, "D": 0, "word": "cant", "chip": "Cash auction · 15:15 se check nahi",
                       "levels": {}, "lines": {k: {"vote": None, "why": "cash auction · 15:15 se check nahi"} for k in LINES},
                       "n_for": 0, "n_against": 0, "n_check": 0, "thin": thin(i), "potential": []}
            continue
        side, zst = zs[i]
        au = (s.get("auction") or {}).get("state")
        D = side or (_edge(s) if au == "RANGE" else _pushing(s))
        cands = [D] if D else [1, -1]
        best = None
        for d in cands:
            ln = _lines(i, d, snaps, ok, zs, wl, ev_hi, ev_lo, asof)
            nf, na, nc = _count(ln)
            key = (nf, -na)
            if best is None or key > best[0]:
                best = (key, d, ln, nf, na, nc)
            elif key == best[0] and not D:
                best = (key, 0, ln, nf, na, nc)        # a range scoring both ways equally has no direction
        _, D, ln, nf, na, nc = best
        cand, clv = _word(i, s, D, side, zst)
        word, lv, D_w = _settle(state, i, cand, clv, D, (side, (zst or {}).get("state")),
                                ((s.get("auction") or {}).get("state"), (s.get("auction") or {}).get("d")))
        chip = f"{WORD[word]} {ARROW[D_w]}" if D_w else WORD[word]
        rows[i] = {"ok": True, "why": None, "D": D, "word": word, "chip": chip, "levels": lv, "lines": ln,
                   "n_for": nf, "n_against": na, "n_check": nc, "thin": thin(i), "potential": _potential(i, s, zs, wl),
                   "zone_in": ln["zone"]["vote"] == 1, "word_dir": D_w}
    sy = sync(snaps, ok, asof)
    ld = lead(ev_hi if (ev_hi and (not ev_lo or max(p.get("t_ms") or 0 for p in ev_hi["per"].values())
                                   >= max(p.get("t_ms") or 0 for p in ev_lo["per"].values()))) else ev_lo)
    look = _look(state, rows, b, early, frozen)
    for i in IDXS:
        if state["words"].get(i) is not None and state["words"][i] != rows[i]["word"]:
            state["word_changes"] = {**state["word_changes"], i: state["word_changes"][i] + 1}
        state["words"] = {**state["words"], i: rows[i]["word"]}
    wsum = {i: wl[i]["vote"] for i in IDXS if wl.get(i)}
    oi_chip = ("Teeno mein PE likh rahe neeche" if len(wsum) == 3 and set(wsum.values()) == {1} else
               "Teeno mein CE likh rahe upar" if len(wsum) == 3 and set(wsum.values()) == {-1} else
               " · ".join(f"{i} {'PE' if v > 0 else 'CE' if v < 0 else 'dono/koi nahi'}" for i, v in wsum.items())
               or "walls check nahi")
    out = {"rev": REV, "shadow": True, "signed": False, "asof": asof, "t": hm(asof), "bar": b,
           "idx": rows, "sync": sy, "extremes": {"high": ev_hi, "low": ev_lo}, "lead": ld,
           "walls": {"chip": oi_chip, "per": wl}, "look": look,
           "counts": {k: state[k] for k in ("changes", "awards", "switches", "releases", "flips6")},
           "note": "counts of lines, never a %; [M] price/OI, [I] side/WHO/writing meaning; SHADOW, unsigned sheet"}
    state["bar"], state["out"] = b, out
    out["counts"] = {k: state[k] for k in ("changes", "awards", "switches", "releases", "flips6")}
    return out, state


def _settle(state: dict, i: str, cand: Optional[str], clv: dict, D: int, zkey, akey) -> Tuple[str, dict, int]:
    """The state word never moves on one bar's wiggle: a candidate replaces the shown word at once only on a named
    event (her zone's state or the reader's auction state changed this bar); otherwise it must repeat on 2 bars in a
    row. A stalled small leg (cand None) holds the shown word. Mutates state["ws"][i]."""
    ws = dict((state.get("ws") or {}).get(i) or {})
    event = ws.get("zkey") != list(zkey) or ws.get("akey") != list(akey)
    cd = clv.get("dir", D) if cand == "ho_gaya" else D
    shown = ws.get("word")
    if cand is not None and (shown is None or event or (cand == ws.get("cand") and cd == ws.get("cand_d"))):
        if cand != shown or cd != ws.get("d"):
            ws.update(word=cand, lv=clv, d=cd)
        else:
            ws["lv"] = clv
    ws.update(cand=cand, cand_d=cd, zkey=list(zkey), akey=list(akey))
    state["ws"] = {**(state.get("ws") or {}), i: ws}
    if ws.get("word") is None:
        return "none", {"start": None, "confirm": None, "kill": None, "from": None}, 0
    return ws["word"], ws["lv"], ws["d"]


def _need(r: dict) -> int:
    return int(TH["AWARD_ZONE"]) if r.get("zone_in") else int(TH["AWARD"])


def _eligible(r: dict) -> bool:
    return (r["ok"] and r["word"] not in ("ho_gaya", "cant") and r["D"] != 0 and r["n_for"] >= _need(r)
            and r["n_for"] >= r["n_against"] + int(TH["MARGIN"]))


def _line(i: str, r: dict) -> str:
    fors = [x["why"] for x in r["lines"].values() if x["vote"] == 1]
    ag = [x["why"] for x in r["lines"].values() if x["vote"] == -1]
    cc = [k for k, x in r["lines"].items() if x["vote"] is None]
    s = f"LOOK HERE · {i} {ARROW[r['D']]} · {r['n_for']} of {r['n_check']} line up: " + " · ".join(fors)
    s += f" | against {len(ag)}" + (": " + " · ".join(ag) if ag else "")
    s += f" | check nahi {len(cc)}" + (": " + ", ".join(cc) if cc else "")
    lv = r["levels"]
    s += f" | {WORD[r['word']]}" + (f" · start {num(lv['start'])}" if lv.get("start") else "") + \
         (f" · confirm: {lv['confirm']}" if lv.get("confirm") else "") + (f" · kill {num(lv['kill'])}" if lv.get("kill") else "")
    return s


def _look(state: dict, rows: Dict[str, dict], b: int, early: bool, frozen: bool) -> dict:
    """Award / hold / switch / release with hysteresis, cooldown and the session cap. Mutates `state`."""
    h, prev = state["holder"], state["holder"]
    elig = {i: r for i, r in rows.items() if _eligible(r)}
    key = lambda i: (elig[i]["n_for"], bool(elig[i].get("zone_in")), -elig[i]["n_against"], -ORDER[i])  # noqa: E731
    best = max(elig, key=key) if elig else None
    why_blank = None
    if state["capped"]:
        h, why_blank = None, f"aaj LOOK HERE {TH['CAP']} baar badla: cap · ab sirf lines"
    elif early:
        h, why_blank = None, "09:25 anchor se pehle nahi"
    elif frozen:
        h, why_blank = None, "cash auction · 15:15 se LOOK HERE nahi"
    elif h is not None:
        r = rows.get(h)
        keep = (r and r["ok"] and r["D"] == state["hold_D"] and r["word"] not in ("ho_gaya", "cant")
                and r["n_for"] >= state["hold_need"] - 1)
        if not keep:
            h = None
        elif best and best != h and elig[best]["n_for"] >= r["n_for"] + int(TH["SWITCH"]) and state["held"] >= int(TH["HOLD"]):
            h = best
    elif best and state["cool"] <= 0:
        h = best
    if h != prev:
        state["changes"] += 1
        if prev is None:
            state["awards"] += 1
        elif h is None:
            state["releases"] += 1
            state["cool"] = int(TH["COOL"])
        else:
            state["switches"] += 1
        hist = (state["hist"] + [(b, h)])[-3:]
        if len(hist) == 3 and hist[2][1] == hist[0][1] and hist[2][0] - hist[0][0] < int(TH["HOLD"]) + int(TH["COOL"]):
            state["flips6"] += 1
        state["hist"] = hist
        state["holder"], state["held"] = h, 0
        state["hold_D"] = rows[h]["D"] if h else None
        state["hold_need"] = _need(rows[h]) if h else None
        if state["changes"] >= int(TH["CAP"]) - 1:
            state["capped"] = True             # the next bar releases a holder: the session never passes CAP
    else:
        state["held"] += 1
        state["cool"] = max(0, state["cool"] - 1)
    if h is None:
        if why_blank is None:
            top = max(rows, key=lambda i: (rows[i]["n_for"], -rows[i]["n_against"], -ORDER[i]))
            r = rows[top]
            why_blank = (f"koi saaf jagah nahi · best {top} {r['n_for']}/{r['n_check']}" if r["ok"]
                         else "koi saaf jagah nahi")
            if state["cool"] > 0 and best:
                why_blank += f" · cooldown {state['cool']} bar"
        return {"idx": None, "D": 0, "n": None, "of": None, "line": "LOOK HERE: " + why_blank, "why_blank": why_blank}
    r = rows[h]
    return {"idx": h, "D": r["D"], "n": r["n_for"], "of": r["n_check"], "against": r["n_against"],
            "line": _line(h, r), "why_blank": None}


def audit(out: dict) -> List[str]:
    """The automatic misdescription audit of one output: its words re-derived from its own numbers. A list of
    violations (empty = clean). A count, never a rate."""
    bad = []
    for i, r in out["idx"].items():
        nf, na, nc = _count(r["lines"])
        if (nf, na, nc) != (r["n_for"], r["n_against"], r["n_check"]):
            bad.append(f"{out['t']} {i}: counts {r['n_for']}/{r['n_against']}/{r['n_check']} != lines {nf}/{na}/{nc}")
        for k, x in r["lines"].items():
            if x["vote"] is None and not x["why"]:
                bad.append(f"{out['t']} {i}: {k} CAN'T CHECK without a reason")
        if r["thin"] and (r["lines"]["flow"]["vote"] is not None or r["lines"]["who"]["vote"] is not None):
            bad.append(f"{out['t']} {i}: thin tape voted flow/WHO")
        if r["word"] in ("ban_sakta", "chal_raha") and r["ok"] and r["levels"].get("start") is None \
                and r["levels"].get("from") == "leg":
            bad.append(f"{out['t']} {i}: {r['word']} without a start level")
    lk = out["look"]
    if lk["idx"]:
        r = out["idx"][lk["idx"]]
        if lk["n"] != r["n_for"] or not r["ok"]:
            bad.append(f"{out['t']} LOOK HERE count {lk['n']} != {r['n_for']} or index not checkable")
        if mod(out["asof"]) > int(TH["FREEZE"]) or mod(out["asof"]) < int(TH["FROM"]):
            bad.append(f"{out['t']} LOOK HERE outside {TH['FROM']}..{TH['FREEZE']}")
    said = [lk["line"], (out.get("sync") or {}).get("chip", ""), (out.get("walls") or {}).get("chip", "")]
    said += [(e or {}).get("chip", "") for e in (out.get("extremes") or {}).values()]
    said += [r["chip"] for r in out["idx"].values()]
    said += [x["why"] for r in out["idx"].values() for x in r["lines"].values() if x["vote"] is not None]
    for w in ("%", "probab", "confidence", "hit rate", "win rate"):
        if any(w in (t or "").lower() for t in said):
            bad.append(f"{out['t']}: forbidden word '{w}' in what the face would say")
    return bad
