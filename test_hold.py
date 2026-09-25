"""hold.py against the registration's own stated examples (PREREG-merged.md rev 4, amended
by PREREG-rev5.md option B), on the frozen facts the prototypes were probed with
(docs/hold/opus/scratch) and NIFTY 09-25 frozen from rev 5's disclosure run.

In-sample by construction: these pin the CODE to the TEXT that was signed, never
the market. Opus's literal probe of the text (xreview/probe_rev3.txt) is the table,
re-pinned to rev 5 §E.1's option B column where B moves a row (rev 5 §D.3)."""
import gzip
import json
import os

import hold

S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "hold", "opus", "scratch")
# never a skip: "39 passed" must not quietly become "30 passed, 9 skipped" (REVIEW §P2)
assert os.path.exists(os.path.join(S, "trades.json")), f"the frozen hold fixtures are missing: {S}"
RULE = {3: "line", 4: "flipped", 5: "quiet", 6: "two"}
# rev 5 §E.1, the option B column: the 11 frozen rows B moves; every other row reads as rev 4's probe (§D.3)
B_MOVED = {**{f"09-22 {t} NIFTY 23550PE": "11:20 quiet" for t in ("10:32", "10:42", "10:43", "10:44")},
           "09-22 10:52 NIFTY 23500PE": "11:20 quiet", "09-23 09:49 NIFTY 23400PE": "10:19 two",
           **{f"09-23 {t} NIFTY 23450CE": "12:52 quiet" for t in ("10:19", "10:33", "11:07")},
           "09-24 14:23 SENSEX 73800PE": "14:36 quiet", "EX 09-23 09:57 SENSEX zone BUY (gate legal)": "12:44 quiet"}
V = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "mockups", "validate-2026-09-25")


def _day(idx, day, _c={}):
    k = f"{idx}_{day}"
    if k not in _c:
        p = os.path.join(S, f"facts_{k}.json.gz")
        _c[k] = json.load(gzip.open(p, "rt")) if os.path.exists(p) else {}   # 09-21 was never frozen
    return _c[k]


def _trades():
    T = json.load(open(os.path.join(S, "trades.json"), encoding="utf-8"))
    out = []
    for tr in T["mine"]:
        out.append({**tr, "t0": hold.hm(hold.mm(tr["read_from"]) + 1)})
    for e in T["examples"]:
        D = _day(e["idx"], e["day"])
        i = hold.mm(e["read"]) - hold.mm("09:15")
        k = round(D["minutes"][i]["spot"] / D["step"]) * D["step"]
        out.append({**e, "k": k, "p0": D["prem"][f"{int(k)}{e['side']}"]["c"][i], "qty": D["lot"],
                    "t0": hold.hm(hold.mm(e["read"]) + 1)})
    return out


def _read(tr, upto=None):
    D = _day(tr["idx"], tr["day"])
    if not D.get("minutes"):
        return None, D
    return hold.read(tr, D["minutes"], D["pivots"], upto=upto, prem=D["prem"].get(f"{int(tr['k'])}{tr['side']}"),
                     idx=tr["idx"]), D


def _probe():
    rows = {}
    with open(os.path.join(S, "xreview", "probe_rev3.txt"), encoding="utf-8") as f:
        for line in f:
            if " entry " in line:
                head, rest = line.split(" entry ", 1)
                word, fold = rest.split(" first FOLD ", 1)
                rows[head.strip()] = (word.strip(), fold.split("(")[0].strip())
    return rows


def test_every_registered_trade_matches_the_literal_probe():
    """33 trades: the entry word and the first FOLD (minute and rule) as the text reads -- rev 4's probe,
    with option B's 11 moved rows as rev 5 §E.1 discloses them."""
    want, n, moved = _probe(), 0, set()
    for tr in _trades():
        r, _ = _read(tr)
        if r is None:
            continue
        f = r["fold"]
        key = tr["id"][:44].strip()
        exp = (want[key][0], B_MOVED[key]) if key in B_MOVED else want[key]
        moved |= {key} & set(B_MOVED)
        got = (r["entry"]["verdict"], f"{f['t']} {RULE[f['rule']]}" if f else "none")
        assert got == exp, tr["id"]
        n += 1
    assert n == 33 and moved == set(B_MOVED)


def test_m5_the_entry_check_example():
    """§3: NIFTY 09-23, her 09:47 call read at 09:46 -- a broken setup, two families."""
    tr = next(t for t in _trades() if t["id"].startswith("09-23 09:47 NIFTY 23450CE"))
    r, _ = _read(tr)
    ent = r["entry"]
    assert ent["verdict"] == "FOLD" and ent["fold_rule"] == 6 and ent["t"] == "09:46"
    assert ent["text"].startswith("You entered into a broken setup — the reason was already gone (read 09:46): "
                                  "two families against you: ")
    assert "call writers at 23,400" in ent["text"] and "adding in your way (held 3 min)" in ent["text"]
    assert "CVD -529 since 09:30" in ent["text"] and "2 sell / 0 buy" in ent["text"]
    assert ent["head_until"] == "09:50"                   # the 09:45 ladder bar closes; >= 3 min


def test_the_quiet_clock_folds_the_six_puts_before_the_low():
    """§3 rule 5, her call: both-leaving minutes count as unpaid -> 14:08-14:10."""
    want = {"13:26": ("14:08", 204.9), "13:41": ("14:08", 129.2), "13:43": ("14:08", 112.6),
            "13:44": ("14:08", 88.8), "13:45": ("14:08", 40.3), "13:57": ("14:10", -11.3)}
    for tr in _trades():
        at = tr["id"][6:11]
        if not tr["id"].startswith("09-24") or "SENSEX" not in tr["id"] or at not in want:
            continue
        r, D = _read(tr)
        t, pts = want.pop(at)
        assert r["fold"]["t"] == t and r["fold"]["rule"] == 5, tr["id"]
        c = D["prem"][f"{int(tr['k'])}PE"]["c"][hold.mm(t) - hold.mm("09:15")]
        assert abs((c - tr["p0"]) - pts) < 0.06, tr["id"]
        row = next(x for x in r["rows"] if x["t"] == t)
        assert row["clock"]["quiet"] == 15 and row["verdict"] == "FOLD"
    assert not want


def test_the_short_atm_pe_writer_folds_at_entry():
    """W2's own example: 09-24 09:44, sold against the trend -> two families at entry."""
    tr = next(t for t in _trades() if "WRITER short ATM PE" in t["id"])
    r, _ = _read(tr)
    assert r["entry"]["verdict"] == "FOLD" and (r["fold"]["t"], r["fold"]["rule"]) == ("09:44", 6)
    assert r["rows"][0]["holders"]["label"] == "YOUR SIDE"
    assert all(x["clock"]["text"].startswith(hold.NOT_SHOWN) for x in r["rows"])   # no quiet clock for a writer


def test_the_side_read_on_the_two_reference_days():
    """§10: SENSEX 09-24 PUTS on 354 of 375 minutes; NIFTY 09-23 no side on 233."""
    def count(idx, day):
        c = {}
        for s in hold.sides(_day(idx, day)["minutes"]):
            c[s["side"]] = c.get(s["side"], 0) + 1
        return c
    assert count("SENSEX", "2026-09-24") == {"no side": 21, "PUTS": 354}
    nifty = count("NIFTY", "2026-09-23")
    assert nifty["no side"] == 233 and nifty["CALLS"] == 141


def test_a_trend_day_and_a_range_day():
    """Trend day (SENSEX 09-24, PUTS on > half): her with-trend 74100PE entered into HOLD
    and is not folded before 13:14. Range day (NIFTY 09-23, no side on > half): her
    09:18 call's reason is gone at 09:44."""
    trs = _trades()
    r, D = _read(next(t for t in trs if t["id"].startswith("09-24 12:32 SENSEX 74100PE")))
    assert r["entry"]["verdict"] == "HOLD" and r["fold"]["t"] == "13:14"
    assert all(x["verdict"] != "FOLD" for x in r["rows"] if x["t"] < "13:14")
    sd = hold.sides(D["minutes"])
    assert sum(s["side"] == "PUTS" for s in sd) > len(sd) / 2
    assert hold.agrees("PE", "long", "PUTS") == "agrees" and hold.agrees("PE", "short", "PUTS") == "against"
    r, D = _read(next(t for t in trs if t["id"].startswith("09-23 09:18 NIFTY 23450CE")))
    assert r["entry"]["verdict"] == "HOLD" and (r["fold"]["t"], r["fold"]["rule"]) == ("09:44", 5)
    sd = hold.sides(D["minutes"])
    assert sum(s["side"] == "no side" for s in sd) > len(sd) / 2


def test_a_past_minute_reads_the_same_whenever_it_is_read():
    """Causal: a read cut at 13:00 is the first part of the read to the close, row for row
    (a restart re-reads any past minute identically, §2)."""
    tr = next(t for t in _trades() if t["id"].startswith("09-24 12:32 SENSEX"))
    full, _ = _read(tr)
    cut, _ = _read(tr, upto="13:00")
    assert cut["rows"] == full["rows"][:len(cut["rows"])] and cut["rows"][-1]["t"] == "13:00"


def test_the_latch_survives_a_blind_minute():
    """M1: once FOLD, a minute with no index candle stays FOLD, never PATA NAHI."""
    tr = next(t for t in _trades() if t["id"].startswith("09-23 09:47 NIFTY"))
    D = _day("NIFTY", "2026-09-23")
    mins = [dict(m) for m in D["minutes"]]
    i = hold.mm("09:50") - hold.mm("09:15")
    mins[i]["ix"] = None
    mins[i]["blind"] = "could not check — chain grid stale since 09:46"
    r = hold.read(tr, mins, D["pivots"])
    row = next(x for x in r["rows"] if x["t"] == "09:50")
    assert row["verdict"] == "FOLD" and row["unlatched"] == "PATA NAHI" and row["since"] == "09:46"


def test_expiry_line_and_the_three_absences():
    e = hold.expiry_line("SENSEX", "2026-09-24", "2026-09-24", "chain poller")
    assert e["zero_dte"] and e["text"].startswith("0DTE today for SENSEX")
    assert hold.expiry_line("NIFTY", "2026-09-25", "2026-09-29", "chain poller")["text"] == "expiry 2026-09-29, 4 days"
    assert hold.expiry_line("NIFTY", "2026-09-25", None, None)["text"] == hold.CC + "expiry not in the day's record"
    assert len({hold.CC, hold.NONE, hold.NOT_SHOWN}) == 3


def test_payers_building_in_your_way_outranks_a_live_fold():
    """REVIEW P0-4: the fact the WATCH / FOLD sentences quote as the reason is the one against
    you, the fold carried as a clause; not held 3 min, the fold still counts for you."""
    x = {"q": {"side": "PE", "k": 23100.0, "state": hold.BLD, "built": True, "words": "adding again"},
         "both": False, "q_pays": False, "q_build": True,
         "q_fold": {"side": "PE", "k": 22850.0, "t": "09:52", "off": 0.09, "high_at": "09:39"}}
    p = hold._payers(x, None, True, [], 0, "PE")
    assert p["state"] == "against" and p["fold_t"] == "09:52"
    assert p["fact"] == ("Put writers at 23,100 adding in your way (held 3 min) — adding again [M]"
                         "; the PE 22,850 fold of 09:52 is still with you")
    assert hold._payers(x, None, False, [], 0, "PE")["state"] == "for"


def test_the_rows_carry_their_counts_and_watch_items_and_the_latch_its_line():
    """The contract the UI reads instead of parsing prose: n_for / n_against are the count's
    numbers, watch_items the hint's conditions (WATCH only), and a rule-3 latch keeps the line
    that broke -- the row's line trails on after it."""
    trs = _trades()
    pick = ("09-22 10:32 NIFTY 23550PE", "09-22 10:52 NIFTY 23500PE", "09-24 14:23 SENSEX 73800PE",
            "09-23 09:47 NIFTY 23450CE", "09-24 10:19 SENSEX 74200PE", "09-23 09:18 NIFTY 23450CE",
            "09-22 13:48 NIFTY 23500PE")                     # under B the line folds this one (rev 5 §E.1)
    watch, rules = 0, set()
    for tr in (next(t for t in trs if t["id"].startswith(p)) for p in pick):
        r, _ = _read(tr)
        for x in r["rows"]:
            assert x["count"].startswith(f"{x['n_for']} for · {x['n_against']} against")
            assert (x["watch_items"] is None) == (x["verdict"] != "WATCH")
            if x["watch_items"]:
                watch += 1
                assert x["watch"] == "FOLD if any one of: " + " · ".join(x["watch_items"])
                assert not any(i.startswith("FOLD if") for i in x["watch_items"])
        f = r["fold"]
        rules.add(f["rule"])
        row = next(x for x in r["rows"] if x["t"] == f["t"])
        if f["rule"] == 3:
            assert (f["L"], f["px"]) == (row["line"]["L"], row["line"]["px"])
            assert f["by"] == round(abs(f["px"] - f["L"]), 1) and f["by"] > 0
            assert f"{f['L']:,.1f}" in f["why"]
        else:
            assert (f["L"], f["src"], f["px"], f["by"]) == (row["line"]["L"], row["line"]["src"], None, None)
    assert watch and rules == {3, 4, 5, 6}


# ---------------------------------------------------------------- rev 5, option B: the new clauses (§A, §B, §D, §F)
CE25 = {"side": "CE", "role": "long", "t0": "12:01:21", "k": 23100.0, "p0": 113.55, "qty": 65}   # her 12:01 CE
PE25 = {"side": "PE", "role": "long", "t0": "12:05:28", "k": 23200.0, "p0": 155.40, "qty": 65}   # her 12:05 PE


def _nifty25():
    """NIFTY 09-25 frozen from rev 5 §E's disclosure run: the index candles only -- OI, flow and trend blind,
    so only the line can fold (the rule 3 half of §E.1's live rows)."""
    F = json.load(open(os.path.join(V, "nifty_2026-09-25.json"), encoding="utf-8"))
    ix = {c[1]: [c[5], c[3], c[4]] for c in F["m1"]}
    mins = [{"t": t, "ix": ix.get(t), "blind": "could not check — no chain record in this test"} for t in hold.SESSION]
    raw = [[f"{d}T{t}:00+05:30", o, h, lo, c, 0, 0] for d, t, o, h, lo, c in reversed(F["m1"])]   # the REST order
    return mins, hold.pivots(raw, "2026-09-25")


def _gap(mins, *ts):
    out = [dict(m) for m in mins]
    for t in ts:
        out[hold.SESSION.index(t)]["ix"] = None
    return out


def test_nifty_0925_folds_where_option_b_says():
    """§D.3 / §E.1: her CE folds at 12:05, 8.0 past L and 3.1 past the level (not at A's 12:02), her PE at
    13:59 on the line trailed at 13:25 (not rev 4's 12:30 or A's 12:32)."""
    mins, pv = _nifty25()
    ce = hold.read(CE25, mins, pv, idx="NIFTY")
    f = ce["fold"]
    assert (f["t"], f["rule"], f["bar"], f["px"], f["L"], f["by"]) == ("12:05", 3, "12:03–12:05", 23067.2, 23075.2, 8.0)
    assert (f["B"], f["B_at"], f["level"], f["by_level"], f["read_at"], f["backfill"], f["clamped"]) == \
        (4.9, "12:00", 23070.3, 3.1, "12:05", False, False)
    assert f["why"] == ("the line is broken: NIFTY's 12:03–12:05 bar closed 23,067.2, 8.0 pts below your line 23,075.2 "
                        "(5m swing low 11:25) [M] — 3.1 past the break level 23,070.3 (one candle, 4.9 pts, read 12:00) [M]")
    a = next(x for x in ce["rows"] if x["t"] == "12:02")                  # A's fold: 1.4 through L, inside the level
    assert a["verdict"] != "FOLD" and a["line"]["bar_close"] and a["line"]["px"] == 23073.8
    head = ce["rows"][0]["line"]
    assert head["print"] == "line 23,075.2 · breaks on a 3-min close below 23,070.3 — one median candle, 4.9 pts [M], read 12:00"
    assert hold._line_item(head, "NIFTY", 1) == ("NIFTY closes a 3-min bar below 23,070.3 (your line less one candle, "
                                                 "4.9 pts [M]) — 7 pts away; next close 12:02")
    pe = hold.read(PE25, mins, pv, idx="NIFTY")
    f = pe["fold"]
    assert (f["t"], f["rule"], f["L"], f["B"], f["B_at"], f["level"], f["px"], f["by"]) == \
        ("13:59", 3, 23055.45, 5.3, "13:25", 23060.75, 23063.2, 7.8)
    assert all(x["verdict"] != "FOLD" for x in pe["rows"] if x["t"] < "13:59")
    assert [(b["L_at"], b["B"]) for b in pe["b_reads"]] == [("12:04", 5.3), ("12:25", 4.4), ("13:25", 5.3)]


def test_a_forming_minute_through_the_line_does_not_change_the_word():
    """§A.0.3: the line's state changes only when a close is read; a forming minute through it only says so --
    rev 4 folded her PE on this very 12:30 minute."""
    mins, pv = _nifty25()
    x = next(x for x in hold.read(PE25, mins, pv, idx="NIFTY")["rows"] if x["t"] == "12:30")
    assert x["verdict"] == "HOLD" and x["unlatched"] == "HOLD" and not x["line"]["bar_close"]
    assert x["line"]["note"] == ("through your line by 2.7 pts [M] — 1.7 pts to go to the break level 23,089.2; "
                                 "the 3-min bar closes at 12:32")
    y = next(x for x in hold.read(CE25, mins, pv, idx="NIFTY")["rows"] if x["t"] == "12:03")   # past the level too
    assert y["verdict"] == "HOLD" and y["line"]["note"] == "through your line by 11.9 pts [M] — the 3-min bar closes at 12:05"


def test_a_missing_mid_bar_candle_is_not_pata_nahi():
    """§A.0.4: the line's state is carried; only the room could not be checked."""
    mins, pv = _nifty25()
    r = hold.read(CE25, _gap(mins, "12:01"), pv, idx="NIFTY")
    x = next(x for x in r["rows"] if x["t"] == "12:01")
    assert x["verdict"] == "HOLD" and x["line"]["blind"] is None and x["line"]["room"] is None
    assert x["line"]["note"] == hold.CC + "no candle for 12:01" and x["line"]["note"] in x["blind"]
    assert r["fold"]["t"] == "12:05"


def test_a_due_close_that_has_not_landed_is_pata_nahi_until_a_close_is_read():
    """§A.0.4 / §D item 14: blind from the missing close until the next close is read."""
    mins, pv = _nifty25()
    r = hold.read(CE25, _gap(mins, "12:02"), pv, idx="NIFTY")
    by = {x["t"]: x for x in r["rows"]}
    assert [by[t]["verdict"] for t in ("12:01", "12:02", "12:03", "12:04", "12:05")] == \
        ["HOLD", "PATA NAHI", "PATA NAHI", "PATA NAHI", "FOLD"]
    assert by["12:02"]["line"]["blind"] == hold.CC + "the 12:00–12:02 bar's close has not landed"
    assert by["12:03"]["sentence"] == ("PATA NAHI — the 12:00–12:02 bar's close has not landed; the line can't say "
                                       "whether it broke. Last word: HOLD since 12:00.")
    none = hold.read(CE25, _gap(mins, "12:00"), pv, idx="NIFTY")                   # the entry minute itself
    assert {x["verdict"] for x in none["rows"]} == {"PATA NAHI"} and none["fold"] is None
    assert none["rows"][0]["sentence"] == "PATA NAHI — no NIFTY candle for 12:00; the line can't be set."
    assert none["entry"]["text"] == "You entered into PATA NAHI — no NIFTY candle for 12:00; the line can't be set."


def test_a_late_close_folds_when_it_is_read_never_back_dated():
    """§A.0.4: the 12:05 candle lands at 12:07 -- the FOLD is stamped 12:07 and names its bar; the minutes
    between read blind; re-read with the same landings (a restart reads day state) it reads the same. A close
    first read from a backfill is read at its bar, and says so."""
    mins, pv = _nifty25()
    late = {"12:05": {"read_at": "12:07"}}
    r = hold.read(CE25, mins, pv, idx="NIFTY", late=late)
    f = r["fold"]
    assert (f["t"], f["bar"], f["read_at"], f["px"], f["backfill"]) == ("12:07", "12:03–12:05", "12:07", 23067.2, False)
    by = {x["t"]: x for x in r["rows"]}
    assert by["12:05"]["verdict"] == by["12:06"]["verdict"] == "PATA NAHI"
    assert by["12:07"]["sentence"].startswith("FOLD 12:07 — the line is broken: NIFTY's 12:03–12:05 bar closed 23,067.2 "
                                              "(read late, at 12:07), 8.0 pts below your line 23,075.2")
    assert hold.read(CE25, mins, pv, idx="NIFTY", late=late) == r
    assert hold.read(CE25, mins, pv, idx="NIFTY")["fold"]["t"] == "12:05"        # the record alone reads it on time
    bf = hold.read(CE25, mins, pv, idx="NIFTY", late={"12:05": {"read_at": None, "backfill": "13:30"}})["fold"]
    assert (bf["t"], bf["read_at"], bf["backfill"]) == ("12:05", None, True)
    assert "(read from backfill after a restart at 13:30)" in bf["why"]


def test_b_falls_back_to_buffer_0_before_15_candles_and_moves_away_once():
    """§A.2: an entry read at 09:20 has 6 of 15 candles -- B could not check and the line breaks at buffer 0;
    B is read at 09:29, the first minute with its own 15, and the level moves once, away from price (S-i)."""
    mins, pv = _nifty25()
    r = hold.read({**CE25, "t0": "09:21:10"}, mins, pv, idx="NIFTY")
    head, at29 = r["rows"][0]["line"], next(x for x in r["rows"] if x["t"] == "09:29")["line"]
    assert (head["B"], head["level"], head["B_why"]) == (None, head["L"], hold.CC + "6 of 15 candles")
    assert "buffer 0 until one median candle can be read" in head["print"]
    assert (at29["B"], at29["B_at"], at29["level"]) == (14.05, "09:29", round(at29["L"] - 14.05, 2))
    assert r["b_reads"][0] == {"L": 23030.0, "L_at": "09:20", "B": 14.05, "B_at": "09:29", "level": 23015.95,
                               "clamped": False}


def test_on_a_trail_the_level_never_moves_away_from_price():
    """§A.2 (S-d) and §D.1 (S-h), NIFTY 09-23 her 09:47 call: the 10:25 trail would have moved the level
    0.9 pts away, so the old level is kept and said so -- never "your line less one candle"."""
    r, _ = _read(next(t for t in _trades() if t["id"].startswith("09-23 09:47 NIFTY")))
    ln = next(x for x in r["rows"] if x["t"] == "10:25")["line"]
    assert ln["clamped"] and ln["clamp"] == {"t": "10:25", "away": 0.9} and ln["level"] == 23349.9
    assert ln["print"].endswith("breaks below 23,349.9 — kept; the 10:25 trail would have moved it 0.9 pts away")
    item = hold._line_item(ln, "NIFTY", 1)
    assert item.startswith("NIFTY closes a 3-min bar below 23,349.9 (kept — the 10:25 trail would have moved it "
                           "0.9 pts away) — ") and "less one candle" not in item


def test_after_a_fold_the_stop_shows_the_line_that_broke():
    """§B: the latched line, how far it broke, then how far back after a heal (§A.0.6); the trailed line is
    detail, and §8's `line` keeps it."""
    mins, pv = _nifty25()
    by = {x["t"]: x for x in hold.read(CE25, mins, pv, idx="NIFTY")["rows"]}
    assert by["12:04"]["after_fold"] is None
    assert by["12:05"]["after_fold"]["text"] == "broke 12:05 by 8.0 pts [M] (3.1 past the break level 23,070.3) · past it by 8 pts"
    assert by["12:05"]["after_fold"]["collapsed"] == "FOLD · NIFTY 23100 CE · line 23,075.2 broke 12:05 by 8.0 pts · since 12:05"
    assert by["12:11"]["after_fold"]["text"] == "broke 12:05 · the index is back 6 pts above it"
    assert by["12:11"]["sentence"].endswith("· the break has healed since 12:11 (a 3-min close back on your side of "
                                            "23,075.2) — a re-entry is a new trade")
    end = by["15:29"]
    assert end["line"]["L"] == 23109.05 and end["after_fold"]["L"] == 23075.2
    assert end["after_fold"]["detail"].startswith("the line has since moved to 23,109.0 (5m swing low 14:25) — detail")


def test_clause_7a_the_first_line_break_and_its_heal():
    """§F.1: a later 3-min close not beyond the L that broke (on L is a heal), within 15 clock minutes; a bar
    whose close was never read is no heal; a break after 15:14 is short."""
    mins, pv = _nifty25()
    assert hold.heal7a(hold.read(CE25, mins, pv, idx="NIFTY")["rows"], 1) == \
        {"t": "12:05", "bar": "12:03–12:05", "L": 23075.2, "healed_at": "12:11", "short": False}      # §E.3
    on = [dict(m) for m in mins]
    x = on[hold.SESSION.index("12:08")]["ix"]
    on[hold.SESSION.index("12:08")]["ix"] = [23075.2, max(x[1], 23075.2), x[2]]
    assert hold.heal7a(hold.read(CE25, on, pv, idx="NIFTY")["rows"], 1)["healed_at"] == "12:08"
    assert hold.heal7a(hold.read(CE25, _gap(mins, "12:11"), pv, idx="NIFTY")["rows"], 1)["healed_at"] == "12:14"
    late = {"t": "15:17", "line": {"broken_at": "15:17", "bar": "15:15–15:17", "L": 100.0, "px": 99.0, "bar_close": True}}
    assert hold.heal7a([late], 1) == {"t": "15:17", "bar": "15:15–15:17", "L": 100.0, "healed_at": None, "short": True}


def test_the_copy_of_rev5_d():
    """§D items 8, 9, 11 and 13 on the frozen facts: the HOLD sentences, the hint's order, OI blind, the
    collapsed line's blind families."""
    tr = next(t for t in _trades() if t["id"].startswith("09-23 09:49 NIFTY 23400PE"))
    r, _ = _read(tr)
    w = next(x for x in r["rows"] if x["verdict"] == "WATCH")["watch_items"]
    assert w[0].startswith("NIFTY closes a 3-min bar above ") and "(your line plus one candle, " in w[0]
    assert w[-2].startswith(("one more family turns against you: ", "two families turn against you, of: "))
    assert w[-1].startswith("nothing pays for 15 readable min — quiet ")
    held = [x for t in _trades() for x in (_read(t)[0] or {"rows": []})["rows"] if x["verdict"] == "HOLD"]
    noise = [x for x in held if x["tag"] == "noise"]
    plain = [x for x in held if x["tag"] is None]
    assert noise and all(x["sentence"].startswith(("Your premium is red; the reason has not changed: ",
                                                   "The premium you sold is up; the reason has not changed: "))
                         and x["sentence"].endswith(" [M].") for x in noise)
    assert plain and all(x["sentence"].startswith("HOLD — the reason stands: ") for x in plain)
    mins, pv = _nifty25()
    x = hold.read(CE25, mins, pv, idx="NIFTY")["rows"][0]
    assert x["tag"] == "OI blind" and x["sentence"].startswith("could not check OI: no chain record in this test; "
                                                               "the line decides; flow could not check — ")
    assert x["against"] == "nothing against you · OI could not check · flow could not check · trend could not check"
