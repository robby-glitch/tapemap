# REVISION c, implemented once from the fingerprinted text (rules_revc_before_run.md, sha256 64ad9d7f...2010):
#  - a tie with ONE leg refused names the open leg as LEANS "· {other} refused", named by refusal, lead 0;
#    STAND ASIDE is both refused, or the refused leg leads (unchanged);
#  - §C.7 answered NO: on the sold option's expiry day a line break folds as today (expr_b.reach_b with answer_yes=False).
# Facts, refusals, strikes and rule 3s are rev b's, unchanged. Writes nothing.
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_b as B        # noqa: E402
A, X, hold = B.A, B.X, B.hold


def grade(e):
    w, named, lead = B.grade(e)
    if w == "STAND ASIDE · tie":                      # exactly one leg refused, b == s
        if e["ref_s"]:
            return f"LEANS BUY {e['buy']['side']} · selling refused", "refusal", 0
        return f"LEANS SELL {e['sell']['side']} · buying refused", "refusal", 0
    return w, named, lead


def expression_c(D, i, d, FR):
    e = A.expression_a(D, i, d, FR)
    w, named, lead = grade(e)
    e["word_a"] = e.get("word")
    e["word"], e["named_by"], e["lead"] = w, named, lead
    return e


def reach_c(D, rows, k, side, d, prem_k, expiry_today):
    return B.reach_b(D, rows, k, side, d, prem_k, False, expiry_today)


if __name__ == "__main__":      # one check: the grading's only change
    base = {"nb": 1, "ns": 1, "buy": {"side": "CE"}, "sell": {"side": "PE"}, "word": "x"}
    assert grade({**base, "ref_b": [], "ref_s": ["R4"]}) == ("LEANS BUY CE · selling refused", "refusal", 0)
    assert grade({**base, "ref_b": ["R5"], "ref_s": []}) == ("LEANS SELL PE · buying refused", "refusal", 0)
    assert grade({**base, "ref_b": ["R5"], "ref_s": ["R1"]})[0] == "STAND ASIDE · both refused"
    assert grade({**base, "nb": 0, "ref_b": [], "ref_s": ["R4"]})[0] == "STAND ASIDE · led"
    assert grade({**base, "nb": 2, "ns": 1, "ref_b": [], "ref_s": ["R4"]})[0] == "LEANS BUY CE · selling refused"
    assert grade({**base, "ref_b": [], "ref_s": []})[0] == "EITHER"
    print("ok")
