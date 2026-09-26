# REVISION b, implemented once from the fingerprinted text (rules_revb_before_run.md, sha256 d7d9ab38...e6cd):
#  - the word shows its margin (BUY/SELL lead >= 2; LEANS lead 1; EITHER tie; a tie with one leg refused -> STAND ASIDE . tie);
#  - rule 3s with rev 5 option B's buffer: FOLD on a 3-min close beyond k +- B_k, B_k = rev 5's B read at entry, frozen,
#    buffer 0 until 15 candles exist (the named fallback). Facts, refusals and strikes are rev a's (expr_a), unchanged.
# Writes nothing; outputs go through run_b.py to absolute paths in this folder.
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_a as A        # noqa: E402
X, hold = A.X, A.hold
mm = hold.mm


def grade(e):
    """Rev b's word from rev a's expression (same facts, refusals, legs)."""
    if not e.get("word"):
        return None, None, None
    b, s = e["nb"], e["ns"]
    bs, ss = e["buy"]["side"], e["sell"]["side"]
    rb, rs = bool(e["ref_b"]), bool(e["ref_s"])
    if rb and rs:
        return "STAND ASIDE · both refused", "refusal", None
    if not rb and rs:
        lead = b - s
        if lead >= 2:
            return f"BUY {bs} · selling refused", "refusal", lead
        if lead == 1:
            return f"LEANS BUY {bs} · selling refused", "refusal", lead
        return ("STAND ASIDE · tie" if lead == 0 else "STAND ASIDE · led"), "refusal", lead
    if rb and not rs:
        lead = s - b
        if lead >= 2:
            return f"SELL {ss} · buying refused", "refusal", lead
        if lead == 1:
            return f"LEANS SELL {ss} · buying refused", "refusal", lead
        return ("STAND ASIDE · tie" if lead == 0 else "STAND ASIDE · led"), "refusal", lead
    lead = b - s
    if lead >= 2:
        return f"BUY {bs}", "count", lead
    if lead == 1:
        return f"LEANS BUY {bs}", "count", lead
    if lead <= -2:
        return f"SELL {ss}", "count", -lead
    if lead == -1:
        return f"LEANS SELL {ss}", "count", 1
    return "EITHER", "count", 0


def expression_b(D, i, d, FR):
    e = A.expression_a(D, i, d, FR)
    w, named, lead = grade(e)
    e["word_a"] = e.get("word")
    e["word"], e["named_by"], e["lead"] = w, named, lead
    return e


def base(word):
    """The word she reads in large type: BUY / LEANS BUY / EITHER / LEANS SELL / SELL / STAND ASIDE / could not check."""
    if not word:
        return "could not check"
    if word.startswith("STAND"):
        return "STAND ASIDE"
    for p in ("LEANS BUY", "LEANS SELL", "BUY", "SELL"):
        if word.startswith(p):
            return p
    return word


def reach_b(D, rows, k, side, d, prem_k, answer_yes=True, expiry_today=False):
    """Rev a's reach with rule 3s buffered by rev 5 B's B, read at the entry read (rows[0]), frozen; buffer 0 until read."""
    at = {m["t"]: i for i, m in enumerate(D["minutes"])}
    e = at[rows[0]["t"]]
    Bk, Bk_at = None, None
    held, events, pmax, pb = None, [], None, None
    for n, r in enumerate(rows):
        i = at[r["t"]]
        if Bk is None:
            v, _ = hold.noise(D["minutes"], i)
            if v is not None:
                Bk, Bk_at = v, r["t"]
        ln = r["line"]
        if held is not None and prem_k[i] is not None:
            pmax = max(pmax, prem_k[i]) if pmax is not None else prem_k[i]
        P, H, F, T = (r[x]["state"] for x in ("payers", "holders", "flow", "trend"))
        r4 = P == "against" and H == "against"
        r6 = sum(s_ == "against" for s_ in (P, F, T)) >= 2
        if (r4 or r6) and (n == 0 or not ln.get("blind")):
            return {"fold": r["t"], "rule": 4 if r4 else 6, "events": events, "held": held, "P_b": pb, "P_max": pmax,
                    "B_k": Bk, "B_at": Bk_at}
        if n == 0 or not ln.get("bar_close") or ln.get("blind"):
            continue
        px = ln["px"]
        R = (k - px) if side == "CE" else (px - k)
        if R < -(Bk or 0.0):                                   # rule 3s: beyond the strike's break level, strict
            return {"fold": r["t"], "rule": "3s", "R": round(R, 1), "events": events, "held": held, "P_b": pb,
                    "P_max": pmax, "B_k": Bk, "B_at": Bk_at}
        if held is None:
            if not hold._beyond(px, ln["level"], d):
                continue
            S_, _ = X.straddle(D, i)
            if (expiry_today and not answer_yes) or S_ is None or R <= S_:
                return {"fold": r["t"], "rule": 3, "R": round(R, 1), "S": S_, "events": events, "held": None,
                        "P_b": None, "P_max": None, "B_k": Bk, "B_at": Bk_at}
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
                    "P_b": pb, "P_max": pmax, "B_k": Bk, "B_at": Bk_at}
    return {"fold": None, "rule": None, "events": events, "held": held, "P_b": pb, "P_max": pmax, "B_k": Bk, "B_at": Bk_at}
