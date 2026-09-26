# REVISION a of the expression draft, implemented once from the fingerprinted text (rules_reva_before_run.md,
# sha256 79d7daa6...162d). Reuses rev 0a's helpers (expr.py, REV0 off). Disclosure only; writes into this folder only.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import expr as X          # noqa: E402
hold, th, validate = X.hold, X.th, X.validate
mm, hm = hold.mm, hold.hm


def base(word):
    """The word she reads in large type: BUY / SELL / EITHER / STAND ASIDE / could not check."""
    if not word:
        return "could not check"
    return word.split(" ")[0] if word.startswith(("BUY", "SELL")) else ("STAND ASIDE" if word.startswith("STAND") else word)


def expression_a(D, i, d, FR):
    m = D["minutes"][i]
    t, step = m["t"], D["step"]
    x = m.get("ix")
    if not x:
        return {"word": None, "why": f"could not check — no {D['idx']} candle for {t}"}
    spot = x[0]
    bs, ss = ("CE", "PE") if d > 0 else ("PE", "CE")
    atm = round(spot / step) * step
    L = X.leg_read(D, i, bs, "long", atm)
    if not L.get("ok"):
        return {"word": None, "why": L.get("why")}
    lr = L["rows"][0]
    facts, ref_b, ref_s = {}, [], []
    oi_blind = m.get("blind")
    # 1 SPEED
    if lr["payers"]["state"] == "blind" and lr["holders"]["state"] == "blind":
        facts["speed"] = ("neither", "could not check — OI")
    elif lr["clock"].get("paid_last") == t:
        facts["speed"] = ("buy", "paid now")
    else:
        facts["speed"] = ("neither", "checked, none")
    # 2 ROOM in VALIDATE §1.3's order (rev a, S1)
    fr, frsrc = X.fr_at(D, i, FR)
    Mx = list(D["minutes"])
    Mx[i] = {**m, "fr": fr}
    g = validate.geometry(Mx, i, d, lr["line"])
    tg = g["target"]
    if g["line"] is None or g["noise"] is None:
        facts["room"] = ("neither", "could not check — line or noise")
    elif g["line"] <= g["noise"]:
        facts["room"] = ("neither", f"a read: line {g['line']} inside one candle ({g['noise']})")
    elif tg.get("blind"):
        facts["room"] = ("neither", "could not check — walls")
    elif tg["src"] == "none" or tg["pts"] >= g["line"]:
        facts["room"] = ("buy", f"target {tg.get('pts')} ≥ line {g['line']}" if tg["src"] != "none" else "price discovery")
    else:
        facts["room"] = ("sell", f"target {tg['pts']} < line {g['line']}")
    # 3 SHIELD, the wall behind the sale
    beyond = (lambda k: k <= spot + step / 2) if ss == "PE" else (lambda k: k >= spot - step / 2)
    cands = [f for f in fr if f["side"] == ss and beyond(f["k"])]
    wall = min(cands, key=lambda f: abs(f["k"] - spot)) if cands else None
    if oi_blind:
        facts["shield"] = ("neither", "could not check — OI")
        ref_s.append("R3")
    elif wall is None:
        facts["shield"] = ("neither", "no wall")
        ref_s.append("R6")
    elif wall["state"] == hold.BLD and wall["built"]:
        facts["shield"] = ("sell", f"{ss} {wall['k']} BUILDING")
    else:
        facts["shield"] = ("neither", f"{ss} {wall['k']} {wall['state']}")
    # 4 REGIME
    sd, why = hold.side_of(m)
    mine = "CALLS" if d > 0 else "PUTS"
    facts["regime"] = (("neither", "could not check") if sd is None else ("buy", sd) if sd == mine else
                       ("sell", "no side") if sd == "no side" else ("neither", sd))
    # 5 PREMIUM: the straddle fixed at t-15; unreadable fails closed (R4)
    sq, swhy = X.straddle15(D, i)
    if sq is None:
        facts["premium"] = ("neither", swhy)
        ref_s.append("R4cnc")
    else:
        facts["premium"] = ({"rose": "buy", "fell": "sell"}.get(sq["state"], "neither"), sq["state"])
        if sq["state"] == "both rose":
            ref_s.append("R4")
    # the sell strike (Q3): at the wall within one ATM straddle of spot, else ATM; S unreadable -> R4
    S, _ = X.straddle(D, i)
    sk, placement, r_w = None, None, None
    import math
    k0 = (math.floor(spot / step) * step) if ss == "PE" else (math.ceil(spot / step) * step)   # never in the money
    if wall is not None and not oi_blind:
        r_w = round((spot - wall["k"]) if ss == "PE" else (wall["k"] - spot), 2)
        if S is None:
            if "R4cnc" not in ref_s:
                ref_s.append("R4cnc")
        elif r_w > S:
            sk, placement = k0, "atm"
        else:
            sk = min(wall["k"], k0) if ss == "PE" else max(wall["k"], k0)
            placement = "wall" if sk == wall["k"] else "k0 (wall at the money, in-the-money side)"
    Sr = X.leg_read(D, i, ss, "short", sk or atm)
    sr = Sr["rows"][0] if Sr.get("ok") else None
    if lr["unlatched"] == "FOLD":
        ref_b.append("R5")
    if sr and sr["unlatched"] == "FOLD":
        ref_s.append("R1")
    if sr and sr["holders"]["state"] == "against":
        ref_s.append("R2")
    nb = sum(1 for v in facts.values() if v[0] == "buy")
    ns = sum(1 for v in facts.values() if v[0] == "sell")
    nb4 = nb - (facts["premium"][0] == "buy")
    ns4 = ns - (facts["premium"][0] == "sell")

    def word_of(b, s):
        bok, sok = not ref_b, not ref_s
        if not bok and not sok:
            return "STAND ASIDE · both refused", "refusal"
        if bok and not sok:
            return (f"BUY {bs} · selling refused", "refusal") if b >= s else ("STAND ASIDE · led", "refusal")
        if sok and not bok:
            return (f"SELL {ss} · buying refused", "refusal") if s >= b else ("STAND ASIDE · led", "refusal")
        return ((f"BUY {bs}", "count") if b > s else (f"SELL {ss}", "count") if s > b else ("EITHER", "count"))
    w, named = word_of(nb, ns)
    w4, _ = word_of(nb4, ns4)
    return {"word": w, "named_by": named, "word4": w4, "t": t, "d": d, "nb": nb, "ns": ns, "facts": facts,
            "ref_b": ref_b, "ref_s": ref_s, "S": S, "spot": spot, "L": g["L"], "line": g["line"], "noise": g["noise"],
            "buy": {"side": bs, "k": atm, "px": X.prem(D, atm, bs, i), "entry": lr["unlatched"]},
            "sell": {"side": ss, "k": sk, "px": X.prem(D, sk, ss, i) if sk else None, "placement": placement,
                     "wall": wall and (wall["k"], wall["state"]), "r_w": r_w,
                     "r_over_S": round(r_w / S, 2) if (r_w is not None and S) else None,
                     "entry": sr["unlatched"] if sr else None},
            "frsrc": frsrc}


# ---------------------------------------------------------------- R-multiples on the shared line (M1)
def risk_to_L(D, i, k, side, role, R):
    g = X.greeks(D, k, side, i)
    p = X.prem(D, k, side, i)
    if g is None or p is None or R is None:
        return None, "no greeks"
    dl, gm = abs(g[0]), g[1]
    if role == "long":
        r = max(0.0, min(p, dl * R - 0.5 * gm * R * R))
        return (r if r > 0 else None), (None if r > 0 else "the buyer's clamp at 0")
    return dl * R + 0.5 * gm * R * R, None      # flagged, not refused, when the line lies beyond the strike (§B.1)


def r_mults(D, i, d, e, n=30):
    """Both legs from minute i: P&L over n finished minutes / premium at risk to L (PLAN §2.1)."""
    j = min(i + n, len(D["minutes"]) - 1)
    R = e["line"]
    out = {}
    for leg, role in (("buy", "long"), ("sell", "short")):
        k, side = e[leg]["k"], e[leg]["side"]
        if k is None:
            out[leg] = {"why": "no strike"}
            continue
        p0, p1 = X.prem(D, k, side, i), X.prem(D, k, side, j)
        risk, why = risk_to_L(D, i, k, side, role, R)
        if p0 is None or p1 is None or risk is None:
            out[leg] = {"why": why or "no premium"}
            continue
        pnl = (p1 - p0) if role == "long" else (p0 - p1)
        out[leg] = {"k": k, "p0": p0, "p30": p1, "pnl": round(pnl, 2), "risk": round(risk, 2), "r": round(pnl / risk, 2)}
    x0, x1 = D["minutes"][i]["ix"][0], (D["minutes"][j].get("ix") or [None])[0]
    mv = None if x1 is None else round((x1 - x0) * d, 1)
    out["move"] = (mv, None if mv is None else "with" if mv > 0 else "against" if mv < 0 else "flat")
    if "r" in out["buy"] and "r" in out["sell"]:
        out["G"] = round(out["buy"]["r"] - out["sell"]["r"], 2)
    return out


# ---------------------------------------------------------------- §B the writer word, rev a
def writer_word_a(D, i, side, k, d, FR=None):
    m = D["minutes"][i]
    t = m["t"]
    R = X.leg_read(D, i, side, "short", k)
    if not R.get("ok") or k is None:
        return {"word": None, "why": R.get("why")}
    r = R["rows"][0]
    rn = r["unlatched"]
    f1 = "with" if rn == "HOLD" else "against" if rn == "FOLD" else "neither"
    spot = m["ix"][0]
    fr, _ = X.fr_at(D, i, FR)
    lo, hi = (k, spot) if side == "PE" else (spot, k)
    walls = [f for f in fr if f["side"] == side and lo - D["step"] / 2 <= f["k"] <= hi + D["step"] / 2]
    w = min(walls, key=lambda f: abs(f["k"] - spot)) if walls else None
    f2 = "with" if (not m.get("blind") and w and w["state"] == hold.BLD and w["built"]) else "neither"
    g = validate.geometry(D["minutes"], i, d, r["line"])
    c0 = X.prem(D, k, side, i)
    gk = X.greeks(D, k, side, i)
    otm = (k - spot) if side == "CE" else (spot - k)
    X_ = None
    if g["line"] is None or g["noise"] is None:
        f3 = "neither"
    elif g["line"] <= g["noise"]:
        f3 = "against"
    elif gk is None or c0 is None:
        f3 = "neither"
    else:
        X_ = abs(gk[0]) * g["line"] + 0.5 * gk[1] * g["line"] ** 2
        f3 = "against" if X_ > c0 else "with"
    sq, _ = X.straddle15(D, i)
    f4 = ("with" if sq and sq["state"] == "fell" else "against" if sq and sq["state"] == "both rose" else "neither")
    fs = [f1, f2, f3, f4]
    word = "NO" if f1 == "against" else "GO" if f1 == "with" and fs.count("against") == 0 and fs.count("neither") <= 1 else "WAIT"

    def outcome(end_mm):
        if X_ is None or g["L"] is None or c0 is None:
            return "not scored"
        tgt, L = c0 - X_, g["L"]
        for j in range(i + 1, len(D["minutes"])):
            mj = D["minutes"][j]
            if mm(mj["t"]) > end_mm:
                break
            xx = mj.get("ix")
            cj = X.prem(D, k, side, j)
            hs = xx is not None and ((xx[1] >= L) if d < 0 else (xx[2] <= L))
            ht = cj is not None and cj <= tgt
            if hs or ht:
                return "same minute" if hs and ht else "stop" if hs else "target"
        return "neither"
    stratum = bool(X_ is not None and g["line"] and g["noise"] and g["line"] > g["noise"] and c0 >= X_)
    return {"word": word, "facts": fs, "X": X_ and round(X_, 2), "c0": c0, "line": g["line"], "noise": g["noise"],
            "otm": round(otm, 1), "line_beyond_strike": bool(g["line"] is not None and g["line"] >= otm), "out30": outcome(min(mm(t) + 30, mm("15:29"))), "out1529": outcome(mm("15:29")),
            "stratum": stratum}


# ---------------------------------------------------------------- §C the reach, rev a (signed R, 3s, expiry switch, P_max)
def reach_a(D, rows, k, side, d, prem_k, answer_yes=True, expiry_today=False):
    at = {m["t"]: i for i, m in enumerate(D["minutes"])}
    held, events, pmax, pb = None, [], None, None
    for n, r in enumerate(rows):
        i = at[r["t"]]
        ln = r["line"]
        if held is not None and prem_k[i] is not None:
            pmax = max(pmax, prem_k[i]) if pmax is not None else prem_k[i]
        P, H, F, T = (r[x]["state"] for x in ("payers", "holders", "flow", "trend"))
        r4 = P == "against" and H == "against"
        r6 = sum(s == "against" for s in (P, F, T)) >= 2
        if (r4 or r6) and (n == 0 or not ln.get("blind")):
            return {"fold": r["t"], "rule": 4 if r4 else 6, "events": events, "held": held, "P_b": pb, "P_max": pmax}
        if n == 0 or not ln.get("bar_close") or ln.get("blind"):
            continue
        px = ln["px"]
        R = (k - px) if side == "CE" else (px - k)
        if R <= 0:
            return {"fold": r["t"], "rule": "3s", "R": round(R, 1), "events": events, "held": held, "P_b": pb, "P_max": pmax}
        if held is None:
            if not hold._beyond(px, ln["level"], d):
                continue
            S_, _ = X.straddle(D, i)
            if (expiry_today and not answer_yes) or S_ is None or R <= S_:
                return {"fold": r["t"], "rule": 3, "R": round(R, 1), "S": S_, "events": events, "held": None,
                        "P_b": None, "P_max": None}
            held = {"bar": ln["bar"], "t": r["t"], "L": ln["L"], "R": round(R, 1), "S": S_}
            pb = pmax = prem_k[i]
            events.append(("held", r["t"], round(R, 1), S_))
            continue
        if not hold._beyond(px, held["L"], d):
            events.append(("healed", r["t"]))
            held = None
            continue
        S_, _ = X.straddle(D, i)
        if S_ is None or R <= S_:
            return {"fold": r["t"], "rule": "3r", "R": round(R, 1), "S": S_, "events": events, "held": held,
                    "P_b": pb, "P_max": pmax}
    return {"fold": None, "rule": None, "events": events, "held": held, "P_b": pb, "P_max": pmax}
