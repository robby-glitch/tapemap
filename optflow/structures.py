"""structures.py -- THE READ'S TRADE: the one or two option structures that express the ladder's said word, with their
legs priced off the chain, their risk, and the WHO change that kills them. Display only: status + reason, never a score
(HANDOFF-DESK §4); no sizing beyond one lot; no order path. Pure: no I/O, no clock.

    pick(close, snap, lot, dte, minute, em) -> {"seller": cand | None, "buyer": cand | None, "blocked": [cand...]}

`close` is ladder.build's close row (said, lean_said, walls, atm, step), `snap` the chain snapshot at that minute
(strikes with ce/pe {bid, ask, ltp, delta}, spot), `em` the ATM straddle (the market's own expected move) or None.
A candidate: {name, side, status (DEPLOYABLE | STAND_ASIDE | BLOCKED), why, legs [{k, sd, act, px, delta}], credit (₹ per
lot, + received / − paid), max_loss (₹ per lot, None = undefined), breakevens, net_delta (per lot), em_used (short strike
distance in expected moves), kill, explain}. The mapping read -> structure is [I] (spec 2026-11-05 §B).
"""
from __future__ import annotations

MAX_SPREAD_VS_EDGE = 2.0      # [I] the old desk's rule: a leg whose own bid/ask is wider than 2× the credit per unit blocks it
WING_MIN_EM = 0.5             # [I] the old desk's STRANGLE_MIN_MOVES: a condor's short strikes sit ≥ half an expected move out
PIN_FROM = 13 * 60            # the PIN lens: 0-1 DTE, from 13:00 (§1s R4)

EXPLAIN = {
    "iron_condor": ("sell a call above and a put below, buy one further out each side", "price stays between the short strikes to expiry",
                    "wing width − credit, if price runs through a wing"),
    "iron_fly": ("sell the ATM call and put, buy a wing each side", "price pins at the strike into expiry", "wing width − credit, fast on a break"),
    "bull_put_spread": ("sell a put at the floor, buy the next lower put", "price holds above the floor", "width − credit, if the floor breaks"),
    "bear_call_spread": ("sell a call at the cap, buy the next higher call", "price holds under the cap", "width − credit, if the cap breaks"),
    "bull_call_spread": ("buy the ATM call, sell the cap call", "price rises to the cap before theta eats the debit", "the debit paid"),
    "bear_put_spread": ("buy the ATM put, sell the floor put", "price falls to the floor before theta eats the debit", "the debit paid"),
    "short_straddle": ("sell the ATM call and put, naked", "a pin", "unlimited beyond the credit; margin not computed here"),
    "short_strangle": ("sell a call above and a put below, naked", "price stays inside the wings", "unlimited beyond; margin not computed here"),
}

# the read -> (seller's structure, buyer's structure, why)   [I]
MAP = {
    "PIN": ("iron_fly", None, "both sides writing at the strike"),
    "UP FUEL": ("bull_put_spread", "bull_call_spread", "writers running above, floor holding"),
    "LID BREAKING": ("bull_put_spread", "bull_call_spread", "cap writers covering"),
    "SQUEEZE": (None, None, "both sides covering: direction not said"),
    "DOWN FUEL": ("bear_call_spread", "bear_put_spread", "writers running below, cap holding"),
    "FLOOR BREAKING": ("bear_call_spread", "bear_put_spread", "floor writers covering"),
    "LID": ("bear_call_spread", None, "cap writing, floor quiet"),
    "FLOOR UP": ("bull_put_spread", None, "floor writing, cap quiet"),
    "UP BUYERS": (None, None, "buyers chasing, no writer behind it: stand aside"),
    "DOWN BUYERS": (None, None, "buyers chasing, no writer behind it: stand aside"),
    "BUYERS OUT": (None, None, "longs leaving both sides: stand aside"),
    "QUIET": ("iron_condor", None, "nothing moved: the range between the walls"),
}
SELLER = ("iron_condor", "iron_fly", "bull_put_spread", "bear_call_spread")
BUYER = ("bull_call_spread", "bear_put_spread")


def _leg(snap, k, sd, act):
    s = next((x for x in (snap or {}).get("strikes") or [] if x["k"] == k), None)
    q = (s or {}).get(sd.lower()) or {}
    bid, ask, ltp = q.get("bid"), q.get("ask"), q.get("ltp")
    px = round((bid + ask) / 2, 2) if bid and ask else ltp
    if px is None:
        return None
    return {"k": k, "sd": sd, "act": act, "px": px, "bid": bid, "ask": ask, "delta": q.get("delta"),
            "spread": round(ask - bid, 2) if bid and ask else None}


def _blocked(name, side, why):
    return {"name": name, "side": side, "status": "BLOCKED", "why": why, "legs": [], "explain": EXPLAIN[name]}


def _cand(name, side, legs, lot, spot, em, kill):
    """Price a defined-risk structure from its legs."""
    if any(l is None for l in legs):
        return _blocked(name, side, "a leg has no quote on the chain")
    credit_u = sum(l["px"] if l["act"] == "S" else -l["px"] for l in legs)        # per unit, + received
    ks_s = [l["k"] for l in legs if l["act"] == "S"]
    ks_b = [l["k"] for l in legs if l["act"] == "B"]
    width = max(abs(b - s) for s in ks_s for b in ks_b) if ks_s and ks_b else None
    if name in ("iron_condor", "iron_fly"):
        width = max(abs(l2["k"] - l1["k"]) for l1 in legs if l1["act"] == "S" for l2 in legs if l2["act"] == "B" and l2["sd"] == l1["sd"])
    max_loss_u = (width - credit_u) if credit_u >= 0 and width is not None else (-credit_u if credit_u < 0 else None)
    nd = sum((-1 if l["act"] == "S" else 1) * (l["delta"] or 0) for l in legs)
    be = []
    if name in ("iron_condor", "iron_fly"):
        be = [round(min(ks_s) - credit_u, 1), round(max(ks_s) + credit_u, 1)]
    elif name == "bull_put_spread":
        be = [round(max(ks_s) - credit_u, 1)]
    elif name == "bear_call_spread":
        be = [round(min(ks_s) + credit_u, 1)]
    elif name == "bull_call_spread":
        be = [round(min(ks_b) - credit_u, 1)]
    elif name == "bear_put_spread":
        be = [round(max(ks_b) + credit_u, 1)]
    em_used = round(min(abs(k - spot) for k in ks_s) / em, 2) if em and spot and ks_s else None
    c = {"name": name, "side": side, "status": "DEPLOYABLE", "why": "", "legs": legs,
         "credit": round(credit_u * lot), "max_loss": None if max_loss_u is None else round(max_loss_u * lot),
         "breakevens": be, "net_delta": round(nd * lot, 1), "em_used": em_used, "kill": kill, "explain": EXPLAIN[name],
         "per_unit": {"credit": round(credit_u, 2), "max_loss": None if max_loss_u is None else round(max_loss_u, 2), "width": width}}
    worst = max((l["spread"] for l in legs if l["spread"] is not None), default=None)      # the quote gate (old desk)
    if credit_u > 0 and worst is not None and worst > MAX_SPREAD_VS_EDGE * credit_u:
        c["status"], c["why"] = "BLOCKED", f"a leg's own spread ₹{worst} outweighs the credit ₹{round(credit_u, 2)} per unit"
    elif name == "iron_condor" and em_used is not None and em_used < WING_MIN_EM:
        c["status"], c["why"] = "STAND_ASIDE", f"short strike only {em_used} expected moves from spot (floor {WING_MIN_EM})"
    return c


def pick(close, snap, lot, dte, minute, em):
    said, spot = close.get("said"), (snap or {}).get("spot")
    step, atm = close.get("step") or 50, close.get("atm")
    ck = ((close.get("walls") or {}).get("ce") or {}).get("k")
    fk = ((close.get("walls") or {}).get("pe") or {}).get("k")
    out = {"seller": None, "buyer": None, "blocked": [], "read": said, "why": None}
    if not snap or spot is None:
        out["why"] = "no chain snapshot at this close: dekh nahi paaye"
        return out
    if said in (None, "OI?"):
        out["why"] = "the read is OI?: nothing to express"
        return out
    sel, buy, why = MAP.get(said, (None, None, f"no structure mapped for {said}"))
    out["why"] = why
    if said == "PIN" and not (dte is not None and dte <= 1 and minute >= PIN_FROM):
        out["why"], sel = "PIN read outside the pin lens (0-1 DTE, from 13:00): stand aside", None

    def build(name, side):
        if name == "iron_condor":
            if not (ck and fk):
                return _blocked(name, side, "no wall on one side")
            legs = [_leg(snap, ck, "CE", "S"), _leg(snap, ck + step, "CE", "B"), _leg(snap, fk, "PE", "S"), _leg(snap, fk - step, "PE", "B")]
            return _cand(name, side, legs, lot, spot, em, "a wall leaves (COVER) on either side")
        if name == "iron_fly":
            w = max(step, int(round((em or step) / step) * step))
            legs = [_leg(snap, atm, "CE", "S"), _leg(snap, atm, "PE", "S"), _leg(snap, atm + w, "CE", "B"), _leg(snap, atm - w, "PE", "B")]
            return _cand(name, side, legs, lot, spot, em, "either side stops writing at the pin")
        if name == "bull_put_spread":
            return _blocked(name, side, "no floor wall") if not fk else _cand(name, side, [_leg(snap, fk, "PE", "S"), _leg(snap, fk - step, "PE", "B")], lot, spot, em, "floor writers COVER")
        if name == "bear_call_spread":
            return _blocked(name, side, "no cap wall") if not ck else _cand(name, side, [_leg(snap, ck, "CE", "S"), _leg(snap, ck + step, "CE", "B")], lot, spot, em, "cap writers COVER")
        if name == "bull_call_spread":
            hi = ck if ck and ck > atm else atm + 2 * step
            return _cand(name, side, [_leg(snap, atm, "CE", "B"), _leg(snap, hi, "CE", "S")], lot, spot, em, "floor writers COVER, or cap WRITE resumes")
        if name == "bear_put_spread":
            lo = fk if fk and fk < atm else atm - 2 * step
            return _cand(name, side, [_leg(snap, atm, "PE", "B"), _leg(snap, lo, "PE", "S")], lot, spot, em, "cap writers COVER, or floor WRITE resumes")
        return None

    if sel:
        out["seller"] = build(sel, "seller")
    if buy:
        out["buyer"] = build(buy, "buyer")
    for name in ("short_straddle", "short_strangle"):      # the catalog's naked rows stay visible, never hidden (HANDOFF-DESK §4)
        out["blocked"].append(_blocked(name, "seller", "naked: margin and gap survival not computed here"))
    for name in SELLER + BUYER:
        if name not in (sel, buy):
            out["blocked"].append({"name": name, "side": "seller" if name in SELLER else "buyer", "status": "STAND_ASIDE",
                                   "why": f"not the read's trade ({said})", "legs": [], "explain": EXPLAIN[name]})
    return out


def demo():
    """The one runnable check: an iron condor priced off a synthetic chain, its numbers by hand, and the gates."""
    q = lambda b, a, d: {"bid": b, "ask": a, "ltp": (a + b) / 2, "delta": d}
    snap = {"spot": 23900, "strikes": [
        {"k": 23700, "ce": q(230, 231, 0.9), "pe": q(20, 21, -0.1)}, {"k": 23750, "ce": q(190, 191, 0.8), "pe": q(30, 31, -0.2)},
        {"k": 23900, "ce": q(100, 101, 0.5), "pe": q(100, 101, -0.5)},
        {"k": 24000, "ce": q(60, 61, 0.3), "pe": q(160, 161, -0.7)}, {"k": 24050, "ce": q(45, 46, 0.2), "pe": q(190, 191, -0.8)}]}
    close = {"said": "QUIET", "atm": 23900, "step": 50, "walls": {"ce": {"k": 24000}, "pe": {"k": 23750}}}
    r = pick(close, snap, 65, 5, 600, 200)
    c = r["seller"]
    assert c["name"] == "iron_condor" and c["status"] == "DEPLOYABLE", c
    assert c["per_unit"]["credit"] == 25.0 and c["per_unit"]["width"] == 50, c["per_unit"]     # 60.5 − 45.5 + 30.5 − 20.5
    assert c["credit"] == 25 * 65 and c["max_loss"] == 25 * 65 and c["breakevens"] == [23725.0, 24025.0]
    assert c["em_used"] == 0.5 and c["kill"].startswith("a wall leaves")
    assert pick(close, snap, 65, 5, 600, 400)["seller"]["status"] == "STAND_ASIDE"          # walls inside half the expected move
    r3 = pick(dict(close, said="LID BREAKING"), snap, 65, 5, 600, 200)
    assert r3["seller"]["name"] == "bull_put_spread" and r3["buyer"]["name"] == "bull_call_spread"
    assert r3["buyer"]["per_unit"]["credit"] == -40.0 and r3["buyer"]["max_loss"] == 40 * 65 and r3["buyer"]["breakevens"] == [23940.0]
    assert pick(dict(close, said="PIN"), snap, 65, 0, 12 * 60, 200)["seller"] is None
    r5 = pick(dict(close, said="PIN"), snap, 65, 0, 14 * 60, 150)
    assert r5["seller"]["name"] == "iron_fly" and [l["k"] for l in r5["seller"]["legs"]] == [23900, 23900, 24050, 23750]
    wide = {"spot": 23900, "strikes": [{"k": 24000, "ce": q(40, 80, 0.3)}, {"k": 24050, "ce": q(54.5, 55.5, 0.2)},
                                        {"k": 23750, "pe": q(30, 31, -0.2)}, {"k": 23700, "pe": q(20, 21, -0.1)}]}
    w = pick(close, wide, 65, 5, 600, 200)["seller"]                    # credit 15 per unit, one leg 40 wide: blocked
    assert w["status"] == "BLOCKED" and w["per_unit"]["credit"] == 15.0, w
    assert pick(close, None, 65, 5, 600, 200)["seller"] is None
    assert any(b["name"] == "short_straddle" for b in r["blocked"])
    print("structures: demo ok")


if __name__ == "__main__":
    demo()
