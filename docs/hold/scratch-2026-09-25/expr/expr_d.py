# REVISION d, implemented once from the fingerprinted text (rules_revd_before_run.md, sha256 78b5f86c...d260):
#  - §A.5: the sale is at the ATM strike, the same strike as the buy (her words); R1/R2 read the short leg there;
#    R4 also refuses when the ATM straddle at t is unreadable, whatever the wall (the sale is one leg of that pair);
#  - §B.1 fact 2: Your wall is §A's wall behind the sale (at or beyond spot, OTM side, half a step, nearest);
#  - §B.2: a writer's GO never stands on a could-not-check risk fact (Your wall, Cushion, Time is paying) -> WAIT;
#  - §B.3: the stratum is line > noise and P >= X (rev a's code already), the line beyond the strike flagged, kept;
#  - §C: the window does not change for writers -- the sold leg's fold is rev 5 B as built (X.window_first_fold).
# Facts, their logic and the word's grading are rev c's (expr_a + expr_c.grade), unchanged. Writes nothing.
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_c as C        # noqa: E402
A, B, X, hold = C.A, C.B, C.X, C.hold
validate = X.validate
mm = hold.mm


def expression_d(D, i, d, FR):
    e = A.expression_a(D, i, d, FR)
    if not e.get("word"):
        e.update(word=None, named_by=None, lead=None)
        return e
    atm, ss = e["buy"]["k"], e["sell"]["side"]
    ref_s = [r for r in e["ref_s"] if r not in ("R1", "R2")]
    Sr = X.leg_read(D, i, ss, "short", atm)
    sr = Sr["rows"][0] if Sr.get("ok") else None
    if sr and sr["unlatched"] == "FOLD":
        ref_s.append("R1")
    if sr and sr["holders"]["state"] == "against":
        ref_s.append("R2")
    if e["S"] is None and "R4cnc" not in ref_s:
        ref_s.append("R4cnc")
    e["ref_s"] = ref_s
    e["sell"] = {"side": ss, "k": atm, "px": X.prem(D, atm, ss, i), "wall": e["sell"]["wall"],
                 "entry": sr["unlatched"] if sr else None}
    w, named, lead = C.grade(e)
    e["word_a"] = e.get("word")
    e["word"], e["named_by"], e["lead"] = w, named, lead
    return e


def wall_behind(fr, side, spot, step):
    beyond = (lambda k: k <= spot + step / 2) if side == "PE" else (lambda k: k >= spot - step / 2)
    c = [f for f in fr if f["side"] == side and beyond(f["k"])]
    return min(c, key=lambda f: abs(f["k"] - spot)) if c else None


def word_of(f1, fs, cnc):
    """VALIDATE rev 2 §2 for a writer, with rev d's clause: no GO on a could-not-check risk fact."""
    if f1 == "against":
        return "NO"
    if f1 == "with" and fs.count("against") == 0 and fs.count("neither") <= 1 and not cnc:
        return "GO"
    return "WAIT"


def writer_word_d(D, i, side, k, d, FR=None):
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
    cnc = []
    w = wall_behind(fr, side, spot, D["step"])
    if m.get("blind"):
        f2 = "neither"; cnc.append("your wall")
    else:
        f2 = "with" if (w and w["state"] == hold.BLD and w["built"]) else "neither"
    g = validate.geometry(D["minutes"], i, d, r["line"])
    c0 = X.prem(D, k, side, i)
    gk = X.greeks(D, k, side, i)
    otm = (k - spot) if side == "CE" else (spot - k)
    X_ = None
    if g["line"] is None or g["noise"] is None:
        f3 = "neither"; cnc.append("cushion")
    elif g["line"] <= g["noise"]:
        f3 = "against"
    elif gk is None or c0 is None:
        f3 = "neither"; cnc.append("cushion")
    else:
        X_ = abs(gk[0]) * g["line"] + 0.5 * gk[1] * g["line"] ** 2
        f3 = "against" if X_ > c0 else "with"
    sq, _ = X.straddle15(D, i)
    if sq is None:
        f4 = "neither"; cnc.append("time is paying")
    else:
        f4 = "with" if sq["state"] == "fell" else "against" if sq["state"] == "both rose" else "neither"
    fs = [f1, f2, f3, f4]
    word = word_of(f1, fs, cnc)
    word_c = word_of(f1, fs, [])          # without rev d's clause, for the disclosure only

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
    return {"word": word, "word_no_cnc_clause": word_c, "facts": fs, "cnc": cnc, "X": X_ and round(X_, 2), "c0": c0,
            "line": g["line"], "noise": g["noise"], "otm": round(otm, 1),
            "line_beyond_strike": bool(g["line"] is not None and g["line"] >= otm),
            "out30": outcome(min(mm(t) + 30, mm("15:29"))), "out1529": outcome(mm("15:29")), "stratum": stratum}


if __name__ == "__main__":      # checks of rev d's one new grading clause and the shared wall
    assert word_of("with", ["with", "with", "with", "neither"], []) == "GO"
    assert word_of("with", ["with", "neither", "with", "with"], ["your wall"]) == "WAIT"
    assert word_of("with", ["with", "with", "neither", "with"], ["cushion"]) == "WAIT"
    assert word_of("with", ["with", "with", "with", "neither"], ["time is paying"]) == "WAIT"
    assert word_of("against", ["against", "with", "with", "with"], []) == "NO"
    assert word_of("with", ["with", "neither", "neither", "with"], []) == "WAIT"
    fr = [{"side": "PE", "k": 23000}, {"side": "PE", "k": 23150}, {"side": "PE", "k": 23075}]
    assert wall_behind(fr, "PE", 23060, 50)["k"] == 23075      # within half a step above spot counts as "at"
    assert wall_behind(fr, "CE", 23060, 50) is None
    print("ok")
