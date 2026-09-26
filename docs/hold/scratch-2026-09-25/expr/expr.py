# THE EXPRESSION READ (EXPRESSION-PREREG-DRAFT.md §A), the writer's VALIDATE word (§B) and the writer's reach
# clause (§C), run AS WRITTEN over the frozen fixtures, for DISCLOSURE only. Counts and rows, never a rate.
# Reads docs/hold/opus/scratch (frozen) through test_hold's own loaders; writes only into this scratch folder.
# Nothing here is tuned: the rules were written in the draft first; this file implements them once.
import gzip, json, os, sys
TM = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, TM)   # rev b: no chdir -- nothing may land in the repo
import board, fronts, gamma, hold, validate   # noqa: E402
import test_hold as th                          # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
REV0 = os.environ.get("EXPR_REV0") == "1"     # rev 0's PREMIUM (the ATM pair vs VWAP), kept to disclose both versions
S = th.S
mm, hm = hold.mm, hold.hm
T0 = mm("09:15")
# the chain each fixture's premiums belong to (the trade symbols in trades.json; NIFTY weekly 09-22, monthly 09-29;
# SENSEX 09-24; BANKNIFTY monthly 09-29) -- used ONLY for the [I] Black-76 greeks of §B's reward fact
EXPIRY = {("NIFTY", "2026-09-22"): "2026-09-22", ("NIFTY", "2026-09-23"): "2026-09-29",
          ("NIFTY", "2026-09-24"): "2026-09-29", ("SENSEX", "2026-09-22"): "2026-09-24",
          ("SENSEX", "2026-09-23"): "2026-09-24", ("SENSEX", "2026-09-24"): "2026-09-24",
          ("BANKNIFTY", "2026-09-22"): "2026-09-29", ("BANKNIFTY", "2026-09-23"): "2026-09-29",
          ("BANKNIFTY", "2026-09-24"): "2026-09-29"}


# ---------------------------------------------------------------- the walls (top 2 per side) for ROOM's target
def oihist_fr(idx, day):
    """{t: fr} from the frozen /api/oihist grid (09-24 only), ranked by the open + the running high on the marks
    -- the server's own fallback (_hold_rec without a chain record). [I] ranking; states [M]."""
    p = os.path.join(S, f"frozen_oihist_{idx}_{day}.json.gz")
    if not os.path.exists(p):
        return None
    O = json.load(gzip.open(p, "rt"))
    minutes = O["minutes"]
    opens = {(float(o["k"]), o["side"]): o["oi"] for o in O["open"]}
    g = fronts.grid(minutes)
    times, _sp, _ks, _S, RP = g
    jx = {t: j for j, t in enumerate(times)}
    out = {}
    for t in hold.SESSION:
        cut = fronts.cut(minutes, t)
        if not cut:
            continue
        j = jx.get(max(cut))
        pk = {}
        if j is not None:
            for (k, side), rp in RP.items():
                o = opens.get((k, side.lower()))
                if o is not None:
                    pk[(k, side.lower())] = o + rp[j]
        fr = fronts.read(cut, pk)
        out[t] = [{"k": f["k"], "side": f["side"], "state": f["state"], "built": f["peak"] > 0} for f in fr]
    return out


def fr_at(D, i, FR):
    m = D["minutes"][i]
    if FR is not None and m["t"] in FR:
        return FR[m["t"]], "M"
    fr = []                                    # 09-22 / 09-23: the nearer front per side only [I]
    for side in ("CE", "PE"):
        f = m.get(side)
        if f:
            fr.append({"k": f["k"], "side": side, "state": f["state"], "built": bool(f.get("built"))})
    return fr, "I-nearer-only"


# ---------------------------------------------------------------- premium helpers
def prem(D, k, side, i):
    p = D["prem"].get(f"{int(k)}{side}")
    if not p:
        return None
    c = p["c"][i] if i < len(p["c"]) else None
    return c


def mirror(D, i):
    """§A fact 5 / §B fact 4: the ATM pair against their own session VWAPs on the last closed 5-min bar [I recon]."""
    m = D["minutes"][i]
    spot = m.get("spot") or (m.get("ix") or [None])[0]
    if spot is None:
        return None, "could not check — no spot"
    step = D["step"]
    atm = round(spot / step) * step
    j = next((j for j in range(i, -1, -1) if (mm(D["minutes"][j]["t"]) - T0) % 5 == 4), None)
    if j is None:
        return None, "could not check — the first 5-min bar has not closed"
    zs = {}
    for side in ("CE", "PE"):
        p = D["prem"].get(f"{int(atm)}{side}")
        if not p or p["c"][j] is None or p["vw"][j] is None or not p["sd"][j]:
            return None, f"could not check — no premium / VWAP band for ATM {int(atm)}{side} at {D['minutes'][j]['t']}"
        zs[side] = (p["c"][j] - p["vw"][j]) / p["sd"][j]
    a, b = zs["CE"], zs["PE"]
    st = ("rotated" if (a > 0) != (b > 0) and a != 0 and b != 0 else
          "decaying together" if a < 0 and b < 0 else "risen together" if a > 0 and b > 0 else "flat")
    return {"state": st, "atm": atm, "z": (round(a, 2), round(b, 2)), "bar_t": D["minutes"][j]["t"]}, None


def straddle15(D, i):
    """rev 0a fact 5: the straddle of the strike ATM at t-15, CE + PE at t against at t-15 -- one contract."""
    if i < 15:
        return None, "could not check — the window needs t − 15 (from 09:30)"
    m0 = D["minutes"][i - 15]
    s0 = m0.get("spot") or (m0.get("ix") or [None])[0]
    if s0 is None:
        return None, f"could not check — no spot at {m0['t']}"
    K = round(s0 / D["step"]) * D["step"]
    ce0, pe0, ce1, pe1 = prem(D, K, "CE", i - 15), prem(D, K, "PE", i - 15), prem(D, K, "CE", i), prem(D, K, "PE", i)
    if None in (ce0, pe0, ce1, pe1):
        return None, f"could not check — a premium of {int(K)} is missing at {m0['t']} or {D['minutes'][i]['t']}"
    a, b = round(ce0 + pe0, 2), round(ce1 + pe1, 2)
    st = ("both rose" if ce1 > ce0 and pe1 > pe0 else "rose" if b > a else "fell" if b < a else "flat")
    return {"state": st, "K": K, "from": a, "to": b, "t0": m0["t"]}, None


def straddle(D, i):
    m = D["minutes"][i]
    spot = m.get("spot") or (m.get("ix") or [None])[0]
    if spot is None:
        return None, None
    atm = round(spot / D["step"]) * D["step"]
    ce, pe = prem(D, atm, "CE", i), prem(D, atm, "PE", i)
    if ce is None or pe is None:
        return None, atm
    return round(ce + pe, 2), atm


def greeks(D, k, side, i):
    """[I] Black-76 on the fixture premium, F = the index (no future in the fixture), T to 15:30 of the expiry."""
    from datetime import datetime
    m = D["minutes"][i]
    F = (m.get("ix") or [None])[0] or m.get("spot")
    c = prem(D, k, side, i)
    exp = EXPIRY.get((D["idx"], D["day"]))
    if F is None or c is None or exp is None:
        return None
    now = datetime.strptime(f"{D['day']} {m['t']}", "%Y-%m-%d %H:%M")
    end = datetime.strptime(f"{exp} 15:30", "%Y-%m-%d %H:%M")
    T = max((end - now).total_seconds() / (365 * 86400), 1e-6)
    kind = "C" if side == "CE" else "P"
    iv = gamma.implied_vol(c, F, k, T, kind)
    if iv is None:
        return None
    return gamma.delta(F, k, iv, T, kind), gamma.gamma(F, k, iv, T), iv


# ---------------------------------------------------------------- one leg's window read at minute i (entry = i)
def leg_read(D, i, side, role, k, upto=None):
    t = D["minutes"][i]["t"]
    p0 = prem(D, k, side, i)
    tr = {"side": side, "role": role, "t0": hm(mm(t) + 1), "k": k, "p0": p0, "qty": 1}
    return hold.read(tr, D["minutes"], D["pivots"], upto=upto if upto else t,
                     prem=D["prem"].get(f"{int(k)}{side}"), idx=D["idx"])


# ---------------------------------------------------------------- §A THE EXPRESSION READ
def expression(D, i, d, FR):
    m = D["minutes"][i]
    t, step = m["t"], D["step"]
    x = m.get("ix")
    if not x:
        return {"word": None, "why": f"could not check — no {D['idx']} candle for {t}; the line can't be set"}
    spot = x[0]
    bs, ss = ("CE", "PE") if d > 0 else ("PE", "CE")
    atm = round(spot / step) * step
    L = leg_read(D, i, bs, "long", atm)
    if not L.get("ok"):
        return {"word": None, "why": L.get("why")}
    lr = L["rows"][0]
    facts, ref_b, ref_s = {}, [], []
    oi_blind = m.get("blind")
    # 1 SPEED -- the window's "paid" at this minute (VALIDATE §1.4 Paying, the buyer's clock)
    if lr["payers"]["state"] == "blind" and lr["holders"]["state"] == "blind":
        facts["speed"] = ("neither", "could not check — OI " + (hold._strip(oi_blind) or "not read"))
    elif lr["clock"].get("paid_last") == t:
        what = lr["payers"]["fact"] if lr["payers"]["state"] == "for" else "flow with you"
        facts["speed"] = ("buy", f"paid now: {what}")
    else:
        facts["speed"] = ("neither", "checked, none — nothing paying now")
    # 2 ROOM -- the target (VALIDATE §1.3, leaving walls out) against the line, both unrounded
    fr, frsrc = fr_at(D, i, FR)
    rec = {**m, "fr": fr}
    Mx = [dict(mm_) for mm_ in D["minutes"]]
    Mx[i] = rec
    g = validate.geometry(Mx, i, d, lr["line"])
    tg = g["target"]
    if g["line"] is None:
        facts["room"] = ("neither", "could not check — the line could not be set")
    elif tg.get("blind"):
        facts["room"] = ("neither", tg["blind"])
    elif tg["src"] == "none":
        facts["room"] = ("buy", f"no wall in the way — price discovery; line {g['line']} pts")
    elif tg["pts"] < g["line"]:
        facts["room"] = ("sell", f"{tg['src']} {tg.get('side')} {tg['k']} is {tg['pts']} pts away, nearer than the line at {g['line']}")
    else:
        facts["room"] = ("buy", f"{tg['src']} {tg.get('side')} {tg['k']} is {tg['pts']} pts away; the line {g['line']}")
    # 3 SHIELD -- the wall behind the sale: the nearest of the top 2 on the sold side at or beyond spot, BUILDING
    beyond = (lambda k: k <= spot + step / 2) if ss == "PE" else (lambda k: k >= spot - step / 2)
    cands = [f for f in fr if f["side"] == ss and beyond(f["k"])]
    wall = min(cands, key=lambda f: abs(f["k"] - spot)) if cands else None
    if oi_blind:
        facts["shield"] = ("neither", "could not check — OI " + hold._strip(oi_blind))
        ref_s.append("R3 OI blind — a writer does not sell a wall she cannot see")
    elif wall is None:
        facts["shield"] = ("neither", f"no {ss} front at or beyond spot among the top two")
        ref_s.append(f"R6 no {'floor' if ss == 'PE' else 'ceiling'} between price and any strike you would sell")
    elif wall["state"] == hold.BLD and wall["built"]:
        facts["shield"] = ("sell", f"{ss} {wall['k']} BUILDING — the wall behind the sale is defended")
    else:
        facts["shield"] = ("neither", f"{ss} {wall['k']} {wall['state']}")
    # 4 REGIME -- §10's side vote, price-led
    sd, why = hold.side_of(m)
    mine = "CALLS" if d > 0 else "PUTS"
    facts["regime"] = (("neither", "could not check — " + (hold._strip(why) or "")) if sd is None else
                       ("buy", f"{sd} — the rows trend your way") if sd == mine else
                       ("sell", f"no side — {why}") if sd == "no side" else
                       ("neither", f"{sd} — the rows trend against your direction"))
    # 5 PREMIUM (rev 0a) -- the straddle fixed at t-15: whose rent won
    if REV0:
        mr, mwhy = mirror(D, i)
        st = mr and {"rotated": "buy", "decaying together": "sell"}.get(mr["state"], "neither")
        facts["premium"] = (st, mr["state"]) if mr else ("neither", mwhy)
        if mr and mr["state"] == "risen together":
            ref_s.append("R4 both ATM legs above their own VWAP")
    else:
        sq, swhy = straddle15(D, i)
        if sq is None:
            facts["premium"] = ("neither", swhy)
        else:
            facts["premium"] = ({"rose": "buy", "fell": "sell"}.get(sq["state"], "neither"),
                                f"straddle {int(sq['K'])} {sq['from']} at {sq['t0']} → {sq['to']} — {sq['state']}")
            if sq["state"] == "both rose":
                ref_s.append("R4 both legs of the fixed straddle rose — the straddle is bid (the seller's vega alarm, her S5)")
    # the legs' own entry checks, and the squeeze (R1, R2, R5)
    sk = wall["k"] if wall else None
    Sr = leg_read(D, i, ss, "short", sk or atm)
    sr = Sr["rows"][0] if Sr.get("ok") else None
    if lr["unlatched"] == "FOLD":
        ref_b.append("R5 you would enter a broken setup (the long leg's entry check reads FOLD, rule "
                     f"{L['entry'].get('fold_rule')})")
    if sr and sr["unlatched"] == "FOLD":
        ref_s.append(f"R1 the short leg's entry check reads FOLD (rule {Sr['entry'].get('fold_rule')})")
    if sr and sr["holders"]["state"] == "against":
        ref_s.append("R2 your side is leaving under a squeeze (held 3 min)")
    nb = sum(1 for v in facts.values() if v[0] == "buy")
    ns = sum(1 for v in facts.values() if v[0] == "sell")
    bok, sok = not ref_b, not ref_s
    if not bok and not sok:
        w = "STAND ASIDE"
    elif bok and not sok:
        w = f"BUY {bs}" if nb >= ns else "STAND ASIDE"
    elif sok and not bok:
        w = f"SELL {ss}" if ns >= nb else "STAND ASIDE"
    else:
        w = f"BUY {bs}" if nb > ns else f"SELL {ss}" if ns > nb else "EITHER"
    return {"word": w, "t": t, "d": d, "nb": nb, "ns": ns, "facts": facts, "ref_b": ref_b, "ref_s": ref_s,
            "buy": {"side": bs, "k": atm, "px": prem(D, atm, bs, i), "entry": lr["unlatched"]},
            "sell": {"side": ss, "k": sk, "px": prem(D, sk, ss, i) if sk else None,
                     "entry": sr["unlatched"] if sr else None,
                     "otm": round(abs(sk - spot)) if sk else None},
            "frsrc": frsrc, "line": g["line"], "noise": g["noise"], "L": g["L"], "spot": spot}


# ---------------------------------------------------------------- §C the writer's reach clause over a writer's rows
def reach_read(D, rows, k, d):
    """Rule 3 for a WRITER under §C: a line break folds her only when her strike is within one ATM straddle of
    the index at that close; outside, it is held (WATCH, 'line broken, held') and every later 3-min close re-reads
    the reach -- the first close inside one straddle folds her (rule 3r). Rules 4 and 6 unchanged. No straddle
    readable at the break close: the line decides (FOLD). A heal (A.0.6) ends the held state."""
    at = {mm_["t"]: i for i, mm_ in enumerate(D["minutes"])}
    held, events = None, []
    for n, r in enumerate(rows):
        i = at[r["t"]]
        ln = r["line"]
        P, H, F, T = (r[x]["state"] for x in ("payers", "holders", "flow", "trend"))
        r4 = P == "against" and H == "against"
        r6 = sum(s == "against" for s in (P, F, T)) >= 2
        if n > 0 and (r4 or r6) and not ln.get("blind"):
            return {"fold": r["t"], "rule": 4 if r4 else 6, "events": events, "held": held}
        if n == 0 and (r4 or r6):
            return {"fold": r["t"], "rule": 4 if r4 else 6, "events": events, "held": held, "entry": True}
        if not ln.get("bar_close") or n == 0 or ln.get("blind"):
            continue
        px = ln["px"]
        if held is None:
            if not hold._beyond(px, ln["level"], d):        # rev 5 B's break: the close beyond the level in force
                continue
        elif not hold._beyond(px, held["L"], d):            # A.0.6: a close back on her side of the L that broke
            events.append(("healed", r["t"]))
            held = None
            continue
        S_, atm = straddle(D, i)                            # the reach, read at this close
        R = abs(k - px)
        if S_ is None:
            return {"fold": r["t"], "rule": "3r" if held else 3, "why": "no straddle readable — the line decides",
                    "events": events, "held": held}
        if R <= S_:
            return {"fold": r["t"], "rule": "3r" if held else 3, "R": round(R, 1), "S": S_,
                    "events": events, "held": held}
        if held is None:
            held = {"bar": ln["bar"], "t": r["t"], "L": ln["L"], "R": round(R, 1), "S": S_}
            events.append(("held", r["t"], round(R, 1), S_))
    return {"fold": None, "rule": None, "events": events, "held": held}


def window_first_fold(D, trade):
    r = hold.read(trade, D["minutes"], D["pivots"], prem=D["prem"].get(f"{int(trade['k'])}{trade['side']}"),
                  idx=D["idx"])
    return r


# ---------------------------------------------------------------- §B the writer's VALIDATE word at minute i
def writer_word(D, i, side, k, d, ex=None):
    m = D["minutes"][i]
    t = m["t"]
    R = leg_read(D, i, side, "short", k)
    if not R.get("ok"):
        return {"word": None, "why": R.get("why")}
    r = R["rows"][0]
    rn = r["unlatched"]
    f1 = "with" if rn == "HOLD" else "against" if rn == "FOLD" else "neither"
    spot = m["ix"][0]
    # 2 your wall: the holders' front between spot and her strike, BUILDING with a build
    fr, _ = fr_at(D, i, ex)
    lo, hi = (k, spot) if side == "PE" else (spot, k)
    walls = [f for f in fr if f["side"] == side and lo - D["step"] / 2 <= f["k"] <= hi + D["step"] / 2]
    w = min(walls, key=lambda f: abs(f["k"] - spot)) if walls else None
    f2 = "with" if (not m.get("blind") and w and w["state"] == hold.BLD and w["built"]) else "neither"
    # 3 cushion and reward
    g = validate.geometry(D["minutes"], i, d, r["line"])
    c0 = prem(D, k, side, i)
    gk = greeks(D, k, side, i)
    X = None
    if g["line"] is None or g["noise"] is None:
        f3 = "neither"
    elif g["line"] <= g["noise"]:
        f3 = "against"
    elif gk is None or c0 is None:
        f3 = "neither"
    else:
        X = abs(gk[0]) * g["line"] + 0.5 * gk[1] * g["line"] ** 2
        f3 = "against" if X > c0 else "with"
    # 4 time is paying: the fixed straddle (rev 0a)
    if REV0:
        mr, _ = mirror(D, i)
        f4 = ("with" if mr and mr["state"] == "decaying together" else
              "against" if mr and mr["state"] == "risen together" else "neither")
    else:
        mr, _ = straddle15(D, i)
        f4 = ("with" if mr and mr["state"] == "fell" else "against" if mr and mr["state"] == "both rose" else "neither")
    fs = [f1, f2, f3, f4]
    na, nn = fs.count("against"), fs.count("neither")
    word = "NO" if f1 == "against" else "GO" if f1 == "with" and na == 0 and nn <= 1 else "WAIT"
    # the writer's outcome (hindsight): premium falls by X (close) before the index touches the static L
    out = None
    if X is not None and g["L"] is not None:
        end = min(mm(t) + 30, mm("15:29"))
        tgt, L = c0 - X, g["L"]
        out = "neither"
        for j in range(i + 1, len(D["minutes"])):
            mj = D["minutes"][j]
            if mm(mj["t"]) > end:
                break
            xx = mj.get("ix")
            cj = prem(D, k, side, j)
            hs = xx is not None and ((xx[1] >= L) if d < 0 else (xx[2] <= L))
            ht = cj is not None and cj <= tgt
            if hs or ht:
                out = ("same minute" if hs and ht else "stop" if hs else "target") + f" {mj['t']}"
                break
    return {"word": word, "facts": fs, "right_now": rn, "wall": w and (w["k"], w["state"]),
            "line": g["line"], "noise": g["noise"], "X": X and round(X, 2), "c0": c0,
            "iv": gk and round(gk[2], 3), "mirror": mr and mr["state"], "outcome": out,
            "stratum": bool(X is not None and g["line"] and g["noise"] and g["line"] > g["noise"] and c0 >= X)}
