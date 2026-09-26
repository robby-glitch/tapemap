# REVISION e, implemented once from the fingerprinted text (rules_reve_before_run.md, sha256 fb583979...0cc9):
#  - §B.2: a writer's GO also needs the wall behind the sale; with none (§A's R6) the word is WAIT (third review B-N1).
# Everything else is rev d's (expr_d), unchanged. Writes nothing.
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import expr_d as E        # noqa: E402
X = E.X


def gate(word, blind, wall):
    """Rev e's clause on top of rev d's word: GO needs a wall behind the sale (OI blind is already WAIT by rev d)."""
    return "WAIT" if word == "GO" and not blind and wall is None else word


def writer_word_e(D, i, side, k, d, FR=None):
    w = E.writer_word_d(D, i, side, k, d, FR)
    if not w.get("word"):
        return w
    m = D["minutes"][i]
    fr, _ = X.fr_at(D, i, FR)
    wall = E.wall_behind(fr, side, m["ix"][0], D["step"])
    w["word_d"] = w["word"]
    w["word"] = gate(w["word"], m.get("blind"), wall)
    w["no_wall"] = wall is None and not m.get("blind")
    return w


if __name__ == "__main__":
    assert gate("GO", False, None) == "WAIT"
    assert gate("GO", False, {"k": 1}) == "GO"
    assert gate("NO", False, None) == "NO"
    assert gate("WAIT", False, None) == "WAIT"
    print("ok")
