"""expression.py against the signed text (docs/hold/EXPRESSION-PREREG.md rev e): §D's disclosed rows reproduced
from the PRODUCTION code on the nine frozen index-days, and §H.7's owed tests.

The disclosure's inputs, rebuilt here exactly as its code read them (docs/hold/scratch-2026-09-25/expr/expr.py;
nothing is imported from that folder): the frozen facts through test_hold._day; the §1d top two per side from the
frozen /api/oihist grid on 09-24 [M], the nearer front per side only on 09-22 and 09-23 [I]; Black-76 greeks on the
fixture premium [I] (the live server reads the broker's). In-sample by construction: this pins the CODE to the TEXT
and to the numbers disclosed before signing, never the market."""
import gzip
import json
import os
from datetime import datetime

from contextlib import contextmanager

import pytest

import expression as X
import fronts
import gamma
import hold
import hold_log
import test_hold as th

HERE = os.path.dirname(os.path.abspath(__file__))
EXPR = os.path.join(HERE, "docs", "hold", "scratch-2026-09-25", "expr")
DAYS = [(i, d) for d in ("2026-09-22", "2026-09-23", "2026-09-24") for i in ("NIFTY", "SENSEX", "BANKNIFTY")]
EXPIRY = {("NIFTY", "2026-09-22"): "2026-09-22", ("NIFTY", "2026-09-23"): "2026-09-29",
          ("NIFTY", "2026-09-24"): "2026-09-29", ("SENSEX", "2026-09-22"): "2026-09-24",
          ("SENSEX", "2026-09-23"): "2026-09-24", ("SENSEX", "2026-09-24"): "2026-09-24",
          ("BANKNIFTY", "2026-09-22"): "2026-09-29", ("BANKNIFTY", "2026-09-23"): "2026-09-29",
          ("BANKNIFTY", "2026-09-24"): "2026-09-29"}
mm = hold.mm


def _oihist_fr(idx, day):
    """{t: top-2 fronts} off the frozen /api/oihist grid (09-24 only), ranked by the open + the running high."""
    p = os.path.join(th.S, f"frozen_oihist_{idx}_{day}.json.gz")
    if not os.path.exists(p):
        return None
    O = json.load(gzip.open(p, "rt"))
    minutes = O["minutes"]
    opens = {(float(o["k"]), o["side"]): o["oi"] for o in O["open"]}
    times, _sp, _ks, _S, RP = fronts.grid(minutes)
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
        out[t] = [{"k": f["k"], "side": f["side"], "state": f["state"], "built": f["peak"] > 0}
                  for f in fronts.read(cut, pk)]
    return out


def _fr(m, FR):
    if FR is not None and m["t"] in FR:
        return FR[m["t"]]
    return [{"k": m[s]["k"], "side": s, "state": m[s]["state"], "built": bool(m[s].get("built"))}
            for s in ("CE", "PE") if m.get(s)]


def _b76(F0, idx, day):
    def gk(k, side, i):
        m = F0["minutes"][i]
        F = (m.get("ix") or [None])[0] or m.get("spot")
        c = _px(F0)(k, side, i)
        if F is None or c is None:
            return None
        T = max((datetime.strptime(f"{EXPIRY[(idx, day)]} 15:30", "%Y-%m-%d %H:%M")
                 - datetime.strptime(f"{day} {m['t']}", "%Y-%m-%d %H:%M")).total_seconds() / (365 * 86400), 1e-6)
        kind = "C" if side == "CE" else "P"
        iv = gamma.implied_vol(c, F, k, T, kind)
        return None if iv is None else (gamma.delta(F, k, iv, T, kind), gamma.gamma(F, k, iv, T))
    return gk


def _px(F0):
    def px(k, side, i):
        p = F0["prem"].get(f"{int(k)}{side}")
        return (p["c"][i] if i < len(p["c"]) else None) if p else None
    return px


_D = {}


def day(idx, dd):
    """One frozen index-day in expression.py's input shape."""
    if (idx, dd) not in _D:
        F0 = th._day(idx, dd)
        FR = _oihist_fr(idx, dd)
        mins = [{**m, "fr": _fr(m, FR)} for m in F0["minutes"]]
        _D[(idx, dd)] = {"idx": idx, "day": dd, "step": F0["step"], "minutes": mins, "pivots": F0["pivots"],
                         "px": _px(F0), "gk": _b76(F0, idx, dd), "late": None}
    return _D[(idx, dd)]


CLOSES = [i for i, t in enumerate(hold.SESSION) if hold.is_close(t)]
_SERIES = {}


@contextmanager
def reading(which):
    """The spot the legs' ATM strike and the wall are read against: "text" = the chain mark's (the signed text,
    §A.5: "the side log's atm.k"; production); "disclosure" = the index close, as the §D disclosure code read it."""
    was = X.leg_spot
    if which == "disclosure":
        X.leg_spot = lambda m: (m.get("ix") or [None])[0]
    try:
        yield
    finally:
        X.leg_spot = was


def series(which="disclosure"):
    """Every 3-minute close of the nine index-days, both directions: {(key, d): [(i, read, writer)]}."""
    if which not in _SERIES:
        out = {}
        with reading(which):
            for key in DAYS:
                D = day(*key)
                for d in (1, -1):
                    rows = []
                    for i in CLOSES:
                        e = X.read(D, i, d)
                        w = X.writer(D, i, d, e["sell"]["side"], e["sell"]["k"], Sr=e["_short"]) if e["word"] else None
                        rows.append((i, e, w))
                    out[(key, d)] = rows
        _SERIES[which] = out
    return _SERIES[which]


def _load(*p):
    return json.load(open(os.path.join(EXPR, *p), encoding="utf-8"))


def _tab(e):
    w = e["word"] or ""
    sub = ("both" if "both" in w else "led" if "led" in w else
           "tie" if e.get("lead") == 0 and e.get("named_by") == "refusal" else "")
    return f"{X.base(e['word'])}·{e.get('named_by')}·{sub}"


# ================================================================ §D reproduced from the production code
# Under the disclosure's reading of spot (the index close for the legs' ATM strike and the wall); every other input
# is read exactly as production reads it. test_D_the_text_reading attributes every difference the text makes.
def test_D1_the_words_at_the_2250_closes():
    """§D.1: BUY 293 · LEANS BUY 516 · EITHER 275 · LEANS SELL 325 · SELL 255 · STAND ASIDE 586, with the split."""
    want = _load("revd", "stability.json")["totals"]["3m"]
    words, tab = {}, {}
    for rows in series().values():
        for _i, e, _w in rows:
            words[X.base(e["word"])] = words.get(X.base(e["word"]), 0) + 1
            tab[_tab(e)] = tab.get(_tab(e), 0) + 1
    assert words == want["words"] == {"BUY": 293, "LEANS BUY": 516, "EITHER": 275, "LEANS SELL": 325, "SELL": 255,
                                      "STAND ASIDE": 586}
    assert tab == want["tab"]
    assert tab["LEANS BUY·refusal·tie"] == 169 and tab["STAND ASIDE·refusal·both"] == 360
    assert tab["STAND ASIDE·refusal·led"] == 226


def test_D2_stability_at_the_close():
    """§D.2: 1,010 changes of 2,232 transitions; 562 of 1,028 runs last one read; 11 BUY ↔ SELL; 185 side flips."""
    ch = runs = one = strong = side = 0
    B, S = ("BUY", "LEANS BUY"), ("SELL", "LEANS SELL")
    for rows in series().values():
        b = [X.base(e["word"]) for _i, e, _w in rows]
        ch += sum(1 for a, c in zip(b, b[1:]) if a != c)
        strong += sum(1 for a, c in zip(b, b[1:]) if {a, c} == {"BUY", "SELL"})
        side += sum(1 for a, c in zip(b, b[1:]) if (a in B and c in S) or (a in S and c in B))
        r = 1
        for a, c in zip(b, b[1:]):
            if a == c:
                r += 1
            else:
                runs, one, r = runs + 1, one + (r == 1), 1
        runs, one = runs + 1, one + (r == 1)
    assert (ch, runs, one, strong, side) == (1010, 1028, 562, 11, 185)


def test_D3_the_refusals():
    """§D.3: R1 355 · R2 311 · R3 98 · R4 24 · R4cnc 138 · R5 372 · R6 440, and what stands behind the refusal words."""
    want = _load("revd", "refusals.json")
    refs, behind = {}, {}
    for rows in series().values():
        for _i, e, _w in rows:
            for r in e["refusal"]:
                refs[r] = refs.get(r, 0) + 1
            if e["named_by"] == "refusal":
                b = behind.setdefault(_tab(e), {"n": 0, "with_R6": 0, "only_R6": 0})
                b["n"] += 1
                b["with_R6"] += "R6" in e["ref_s"]
                b["only_R6"] += e["ref_s"] == ["R6"]
    assert refs == want["refusals"] == {"R1": 355, "R2": 311, "R3": 98, "R4": 24, "R4cnc": 138, "R5": 372, "R6": 440}
    assert behind == want["behind_refusal_words"]


def test_D4_the_word_at_her_28_frozen_entries():
    """§D.4: the word on the screen at each of her entries (the last close at or before her read minute), its
    lead, count and refusals, its since / was -- as revd/entries.json; and the writer's word (§B, rev e)."""
    want = {r["id"]: r for r in _load("revd", "entries.json")}
    writer_e = {r["id"]: r.get("word") for r in _load("reve", "writer.json")["entries"]}
    s, n = series(), 0
    for tr in th._trades():
        if not tr.get("mine"):
            continue
        w = want[tr["id"]]
        if "why" in w:                                   # 09-21 was never frozen
            assert not th._day(tr["idx"], tr["day"]).get("minutes")
            continue
        d = hold.thesis(tr["side"], tr["role"])["d"]
        rows = s[((tr["idx"], tr["day"]), d)]
        ir = mm(tr["read_from"]) - mm("09:15")
        j = max(n_ for n_, (i, _e, _w) in enumerate(rows) if i <= ir)
        e = rows[j][1]
        since, was = X.since([r[1] for r in rows], j)
        assert (e["word"] or "could not check") == w["word"], tr["id"]
        assert (e["named_by"], e["lead"], e["nb"], e["ns"]) == (w["named_by"], w["lead"], w["nb"], w["ns"]), tr["id"]
        assert sorted(e["refusal"]) == sorted(w["ref"]), tr["id"]
        assert since == w["since"] and (was or {}).get("word") == w["was"], tr["id"]
        assert (e["sell"]["side"], e["sell"]["k"]) == (w["sell"]["side"], w["sell"]["k"]), tr["id"]   # the ATM sale
        D = day(tr["idx"], tr["day"])
        with reading("disclosure"):
            ww = X.writer(D, ir, d, e["sell"]["side"], e["sell"]["k"])
        assert ww["word"] == writer_e[tr["id"]], tr["id"]
        n += 1
    assert n == 28


def test_D7_the_writer_word_at_the_closes_and_the_units():
    """§D.7: the writer's word (rev e) GO 633 · WAIT 1,262 · NO 355 at the 2,250 closes, no GO beside a sell refusal;
    at the 216 units GO 60 · WAIT 121 · NO 35, in the stratum GO 60 · WAIT 89 · NO 21, beyond the strike 196."""
    want = _load("reve", "writer.json")
    c, u, st, sb, beyond, go_ref = {}, {}, {}, {}, 0, 0
    r30 = r1529 = ns = 0
    for (key, d), rows in series().items():
        D = day(*key)
        for i, e, w in rows:
            c[w["word"]] = c.get(w["word"], 0) + 1
            go_ref += w["word"] == "GO" and bool(e["ref_s"])
            if not e["unit"]:
                continue
            u[w["word"]] = u.get(w["word"], 0) + 1
            beyond += w["beyond_strike"]
            k, side, t = e["sell"]["k"], e["sell"]["side"], hold.SESSION[i]
            o30 = X.writer_outcome(D, i, d, k, side, w, hm_(min(mm(t) + 30, mm("15:29"))))
            o1529 = X.writer_outcome(D, i, d, k, side, w, "15:29")
            r30 += o30 in ("target", "stop", "same minute")
            r1529 += o1529 in ("target", "stop", "same minute")
            ns += o30.startswith("not scored")
            if w["stratum"]:
                st[w["word"]] = st.get(w["word"], 0) + 1
                if w["beyond_strike"]:
                    sb[w["word"]] = sb.get(w["word"], 0) + 1
    assert c == want["closes"]["words"] == {"GO": 633, "WAIT": 1262, "NO": 355} and go_ref == 0
    assert u == want["grid"]["words"] == {"GO": 60, "WAIT": 121, "NO": 35}
    assert st == want["grid"]["stratum"] and sb == want["grid"]["stratum_beyond"] and beyond == 196
    assert (r30, r1529, ns) == (78, 127, 38)


def test_D7_G_is_scored_at_204_of_216_units():
    """§D.7: G scored at 204 of 216 (the sale always priced; R6 units scored); not scored: no premium 6, no greeks 6;
    the words at the units as disclosed."""
    want = _load("revd", "grid.json")
    n, scored, why, tab = 0, 0, {}, {}
    for (key, d), rows in series().items():
        D = day(*key)
        for i, e, _w in rows:
            if not e["unit"]:
                continue
            n += 1
            tab[_tab(e)] = tab.get(_tab(e), 0) + 1
            r = X.r_mults(D, i, d, e)
            if "G" in r:
                scored += 1
            else:
                y = r["buy"].get("why") or r["sell"].get("why")
                why[y] = why.get(y, 0) + 1
    assert (n, scored) == (216, 204) and why == {"no premium": 6, "no greeks": 6}
    assert tab == want["tab"]


def hm_(n):
    return hold.hm(n)


def test_D_the_text_reading_moves_only_where_spot_moves():
    """The signed text reads the legs' ATM strike and the wall against spot, "the side log's atm.k" (the chain mark);
    the disclosure read the index close there. Production follows the text. Every close where the text's word, its
    refusals or the writer's word differ from the disclosure's is one where the two spots name a different ATM
    strike or a different wall behind the sale -- nothing else moved: 12 words and 5 writer words of 2,250 closes."""
    txt, dis = series("text"), series("disclosure")
    moved_w = moved_ww = 0
    for key_d, rows in txt.items():
        D = day(*key_d[0])
        for (i, e1, w1), (_i, e2, w2) in zip(rows, dis[key_d]):
            m, st = D["minutes"][i], D["step"]
            ss = e1["sell"]["side"]
            atm_moves = round(m["spot"] / st) != round(m["ix"][0] / st)
            wall = lambda s_: (X.wall_behind(m["fr"], ss, s_, st) or {}).get("k")
            wall_moves = wall(m["spot"]) != wall(m["ix"][0])
            if (e1["word"], e1["refusal"]) != (e2["word"], e2["refusal"]):
                moved_w += 1
                assert wall_moves, (key_d, hold.SESSION[i])
            if w1["word"] != w2["word"]:
                moved_ww += 1
                assert wall_moves or atm_moves, (key_d, hold.SESSION[i])
            assert e1["sell"]["k"] == e1["buy"]["k"] == round(m["spot"] / st) * st      # the side log's atm.k
    assert (moved_w, moved_ww) == (12, 5)


# ================================================================ §H.7, the owed tests
def test_H7_the_word_order_and_named_by():
    """§A.4 in order: both refused; one refused (lead >= 2, one, the tie as LEANS by refusal, the other leading =
    STAND ASIDE · led); neither refused (BUY / LEANS / EITHER / LEANS / SELL on the count)."""
    G = lambda nb, ns, rb, rs: X.grade(nb, ns, rb, rs, "CE", "PE")
    assert G(3, 0, ["R5"], ["R1"]) == ("STAND ASIDE · both refused", "refusal", None, None)
    assert G(3, 1, [], ["R4"]) == ("BUY CE · selling refused", "refusal", 2, "lead")
    assert G(2, 1, [], ["R4"]) == ("LEANS BUY CE · selling refused", "refusal", 1, "leans")
    assert G(1, 1, [], ["R4cnc"]) == ("LEANS BUY CE · selling refused", "refusal", 0, "leans")    # rev c's refused tie
    assert G(0, 0, [], ["R6"]) == ("LEANS BUY CE · selling refused", "refusal", 0, "leans")
    assert G(0, 3, [], ["R4cnc"]) == ("STAND ASIDE · led", "refusal", -3, None)
    assert G(1, 1, ["R5"], []) == ("LEANS SELL PE · buying refused", "refusal", 0, "leans")
    assert G(3, 1, ["R5"], []) == ("STAND ASIDE · led", "refusal", -2, None)
    assert G(0, 2, ["R5"], []) == ("SELL PE · buying refused", "refusal", 2, "lead")
    assert G(3, 1, [], []) == ("BUY CE", "count", 2, "lead")
    assert G(2, 1, [], []) == ("LEANS BUY CE", "count", 1, "leans")
    assert G(2, 2, [], []) == ("EITHER", "count", 0, "tie")
    assert G(0, 0, [], []) == ("EITHER", "count", 0, "tie")
    assert G(1, 2, [], []) == ("LEANS SELL PE", "count", 1, "leans")
    assert G(0, 4, [], []) == ("SELL PE", "count", 4, "lead")
    for rows in series("text").values():                  # a word named by refusal is never dressed as one on the count
        for _i, e, _w in rows:
            assert (e["named_by"] == "refusal") == bool(e["ref_b"] or e["ref_s"])
            assert ("refused" in e["word"] or e["word"] == "STAND ASIDE · led") == (e["named_by"] == "refusal")


def test_H7_after_1500_changes_no_word_or_falsifier():
    """§E.3: after_1500 is written on every expression and outcome row, true at 15:00 or later, and gates nothing."""
    D = day("SENSEX", "2026-09-24")
    base_ = [X.read(D, i, -1) for i in CLOSES]
    for e in base_:
        assert e["after_1500"] == (e["t"] >= "15:00")
    keep = X.after_1500
    try:
        X.after_1500 = lambda t: not keep(t)                   # flip the flag everywhere
        flip = [X.read(D, i, -1) for i in CLOSES]
    finally:
        X.after_1500 = keep
    strip_ = lambda e: {k: v for k, v in e.items() if k not in ("after_1500", "_short", "_long")}
    assert [strip_(a) for a in base_] == [strip_(b) for b in flip]
    i44 = hold.SESSION.index("14:44")
    e = base_[CLOSES.index(i44)]
    o = X.outcome_row(D, e, X.writer(D, i44, -1, "CE", e["sell"]["k"]), "2026-09-24", "SENSEX")
    assert o["after_1500"] is False and o["short_window"] is False
    i14 = hold.SESSION.index("15:14")
    e = base_[CLOSES.index(i14)]
    o2 = X.outcome_row(D, e, X.writer(D, i14, -1, "CE", e["sell"]["k"]), "2026-09-24", "SENSEX")
    assert o2["after_1500"] is True and o2["short_window"] is True


def test_H7_R4_fails_closed():
    """§A.4 R4: an unreadable fixed straddle (before 09:30, or a premium missing) or an unreadable ATM straddle at t
    refuses SELL, "R4 — could not check" -- never a word on the count."""
    n = 0
    for (key, d), rows in series("text").items():
        for i, e, _w in rows:
            if hold.SESSION[i] < "09:30":
                assert "R4cnc" in e["refusal"] and e["named_by"] == "refusal", (key, e["t"])
                assert not X.base(e["word"]).endswith("SELL") and e["word"] != "EITHER"
                n += 1
    assert n == 18 * 5                                     # 09:17 … 09:29, every index-day, both directions
    D = day("NIFTY", "2026-09-23")
    i = hold.SESSION.index("11:05")
    e0 = X.read(D, i, 1)
    assert "R4cnc" not in e0["refusal"]
    K = e0["sell"]["k"]
    gone = {**D, "px": lambda k, side, j: None if (k, side, j) == (K, "CE", i) else D["px"](k, side, j)}
    e1 = X.read(gone, i, 1)                                # the ATM straddle at t cannot be read
    assert "R4cnc" in e1["refusal"] and e1["named_by"] == "refusal"
    assert e1["why_ref"]["R4cnc"].startswith("could not check")


def test_H7_ROOM_noise_step():
    """§A.3 fact 2: a line inside one candle (a tie is inside) reads NEITHER, a read -- never a vote either way."""
    n = 0
    for (key, d), rows in series("text").items():
        for _i, e, _w in rows:
            if e["word"] and e["line"] is not None and e["noise"] is not None and e["line"] <= e["noise"]:
                room = e["facts"][1]
                assert room[0] == "ROOM" and room[1] == "neither" and room[2] is None, (key, e["t"])
                assert "inside one candle" in room[3] and "not read" in room[3]
                n += 1
    assert n > 0


def test_H7_the_sale_at_the_buys_ATM_and_an_R6_unit_priced_and_scored():
    """§A.5: the sale is the buy's ATM strike; with no wall behind it (R6) it is still priced, and its unit scored."""
    r6 = scored = 0
    for (key, d), rows in series("text").items():
        D = day(*key)
        for i, e, _w in rows:
            if not e["word"]:
                continue
            assert e["sell"]["k"] == e["buy"]["k"]
            if e["unit"] and "R6" in e["refusal"]:
                r6 += 1
                assert e["sell"]["wall"] is None
                if e["sell"]["px"] is not None:
                    scored += "G" in X.r_mults(D, i, d, e)
    assert r6 > 0 and scored > 0


def test_H7_the_writers_wall_is_As_wall_behind_the_sale():
    """§B.1 fact 2 (rev d): one wall, one definition in §A and §B."""
    for (key, d), rows in series("text").items():
        for _i, e, w in rows:
            if not e["word"] or e["facts"][2][2] == "blind":
                continue
            assert w["wall"] == e["sell"]["wall"], (key, e["t"])
            assert (e["facts"][2][1] == "sell") == (w["facts"][1][1] == "for"), (key, e["t"])


def _a_go():
    for (key, d), rows in series("text").items():
        for i, e, w in rows:
            if w and w["word"] == "GO" and "09:45" < e["t"] < "14:00":
                return key, d, i, e, w
    raise AssertionError("no GO on the frozen days")


def test_H7_a_writers_could_not_check_risk_fact_gives_WAIT_never_GO():
    """§B.2 (rev d): could not check on Your wall, Cushion or Time is paying reads WAIT."""
    for rows in series("text").values():
        for _i, _e, w in rows:
            assert not (w["word"] == "GO" and w["cnc"])
    key, d, i, e, _w = _a_go()
    D = day(*key)
    K0 = X.straddle15(D, i)[0]["K"]
    blind_t15 = {**D, "px": lambda k, side, j: None if (k, j) == (K0, i - X.QUIET) else D["px"](k, side, j)}
    w2 = X.writer(blind_t15, i, d, e["sell"]["side"], e["sell"]["k"])
    assert w2["word"] == "WAIT" and w2["cnc"] == ["Time is paying"] and "could not check Time is paying" in w2["needs"]
    w3 = X.writer({**D, "gk": lambda *a: None}, i, d, e["sell"]["side"], e["sell"]["k"])
    assert w3["word"] == "WAIT" and w3["cnc"] == ["Cushion"]


def test_H7_a_writer_with_no_wall_behind_the_sale_gives_WAIT_never_GO():
    """§B.2 (rev e): GO also needs the wall behind the sale; with none (§A's R6) the word is WAIT, not NO."""
    for rows in series("text").values():
        for _i, e, w in rows:
            assert not (w["word"] == "GO" and ("R6" in e["refusal"] or w["no_wall"]))
    key, d, i, e, _w = _a_go()
    D = day(*key)
    ss = e["sell"]["side"]
    mins = list(D["minutes"])
    mins[i] = {**mins[i], "fr": [f for f in mins[i]["fr"] if f["side"] != ss]}
    w2 = X.writer({**D, "minutes": mins}, i, d, ss, e["sell"]["k"])
    assert w2["word"] == "WAIT" and w2["no_wall"] and "no wall behind the sale (R6)" in w2["needs"]


def test_H7_beyond_strike_is_written_on_the_writer_object():
    """§E.3 (B-T2): the grid writer object carries beyond_strike, a bool, as the writer word read it."""
    D = day("NIFTY", "2026-09-23")
    for t in ("10:14", "12:44"):
        i = hold.SESSION.index(t)
        e = X.read(D, i, 1)
        w = X.writer(D, i, 1, "PE", e["sell"]["k"], Sr=e["_short"])
        o = X.outcome_row(D, e, w, "2026-09-23", "NIFTY", co_timed=["SENSEX"])
        assert isinstance(o["writer"]["beyond_strike"], bool) and o["writer"]["beyond_strike"] == w["beyond_strike"]
        assert o["writer"]["first_30"] and o["writer"]["first_1529"] and o["co_timed"] == ["SENSEX"]
        assert o["prereg"] == "expr-e" and o["kind"] == "expr_outcome"


def test_H7_the_stratum_keeps_units_with_the_line_beyond_the_strike():
    """§B.3 (B-M1): the stratum is line > noise and P >= X; units with the line beyond the strike are inside it,
    flagged, never excluded."""
    inside = 0
    for rows in series("text").values():
        for _i, e, w in rows:
            if e["unit"]:
                assert w["stratum"] == bool(w["X"] is not None and w["line"] > w["noise"] and w["P"] >= w["X"])
                inside += w["stratum"] and w["beyond_strike"]
    assert inside > 0


def test_H7_the_outcome_key_collision(tmp_path, monkeypatch):
    """§B.3: a long CE and a short PE share d, so the outcome key gains role; an existing row without one is long."""
    monkeypatch.setattr(hold_log, "DIR", str(tmp_path))
    monkeypatch.setattr(hold_log, "_seen", {})
    old = {"kind": "check_outcome", "idx": "NIFTY", "t": "10:31", "d": 1, "first": "stop"}      # a rev 2 row on disk
    short = {**old, "role": "short", "first_30": "target"}
    assert hold_log.key("check", old) == ("NIFTY", "10:31", 1, "long", "outcome")
    assert hold_log.key("check", {**old, "role": "long"}) == hold_log.key("check", old)
    assert hold_log.key("check", short) != hold_log.key("check", old)
    assert hold_log.append("check", "2026-09-28", [old]) == 1
    assert hold_log.has("check", "2026-09-28", ("NIFTY", "10:31", 1, "long", "outcome"))
    assert not hold_log.has("check", "2026-09-28", ("NIFTY", "10:31", 1, "short", "outcome"))
    assert hold_log.append("check", "2026-09-28", [short, old]) == 1                   # both kept, neither twice
    e1 = {"kind": "expr", "idx": "NIFTY", "t": "10:31", "d": 1}
    assert hold_log.append("expr", "2026-09-28", [e1, {**e1, "d": -1}]) == 2           # one row per direction
    assert hold_log.append("expr", "2026-09-28", [e1, {**e1, "kind": "expr_outcome"}]) == 1
