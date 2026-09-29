"""2026-09-28 trader audit, bug 1 and bug 9 (docs/hold/BUGFIX-2026-09-28.md).

The CVD rank counted the current 15-min change inside its own history, so the day's first read ranked 1.0
("pressing") by construction and the second at least 0.5 (STRONG). At 09:35 that read CVD +56 as buyers pressing
and folded a winning put. A rank needs earlier changes; without them it could not check.
"""
import board
import grounds
import hold

T0 = 1790567100000                  # 2026-09-28 09:15 IST, ms
FIVE = 5 * 60 * 1000


def bars(cvds):
    return [{"t": T0 + i * FIVE, "cvd": c, "c": 22900.0 - i, "h": 22910.0 - i, "l": 22890.0 - i}
            for i, c in enumerate(cvds)]


def test_the_current_change_is_not_its_own_history():
    assert grounds._rank(56, [0, 0, 0, 56]) is None                      # 4 bars: no earlier change
    assert grounds._rank(1, [0, 500, 0, 1, 501]) is None                 # 5 bars: one earlier change
    # 7 bars, 3 earlier changes |s[i] - s[i-3]| for i = 3..5: 300, 300, 300; the current one is small
    s = [0, 0, 0, 300, 300, 300, 310]
    assert grounds._rank(10, s) == 0.0
    assert grounds._rank(300, s) == 1.0


def test_the_first_read_of_the_day_could_not_check_never_strong():
    F = grounds.facts(bars([-693, -866, -602, -637]), [], [])           # 4 closed bars, today's shape
    c = F["cvd"]
    assert c["rank"] is None
    assert c["rank_why"] == "0 earlier 15-min changes today; sizing this one needs 3"
    assert c["dpx"] is not None                                          # the writer's squeeze still reads dpx
    dirn, word, fact, why = board.aggression({"cvd": c, "flow": {"buy": 6, "sell": 2}})
    assert (dirn, word, fact) == (0, None, None)
    assert why.startswith(board.CC)


def test_hold_reads_it_blind_so_it_cannot_make_a_fold():
    c = grounds.facts(bars([-693, -866, -602, -637]), [], [])["cvd"]
    rec = {"cvd": c, "flow": {"b": 6, "s": 2}}
    state, _fact, why = hold.flow(rec, -1)                               # a put buyer, the 09:35 case
    assert state == "blind" and why.startswith(board.CC)


def test_a_sized_rank_still_reads_with_and_against():
    # 8 bars: 4 earlier changes of 20; the current change is +400 with buy prints dominating
    cv = [0, 20, 40, 60, 80, 100, 120, 520]
    c = grounds.facts(bars(cv), [], [])["cvd"]
    assert c["rank"] == 1.0
    dirn, word, _fact, _why = board.aggression({"cvd": c, "flow": {"buy": 6, "sell": 2}})
    assert dirn == 1 and word == "pressing"


def test_a_footprint_event_is_visible_when_its_bar_closes_not_a_minute_later():
    # the 09:30 bar ends with the finished minute 09:34 (the rule board._closed already used)
    ev = board.tape_events({"tm": [{"t": T0 + 3 * FIVE, "kind": "absorption", "side": 1, "p": 1.0, "size": 1}]})
    assert ev[0]["vis"] == board.mm("09:34")


def test_the_near_future_is_blind_in_its_expiry_week():
    """P1-02: the roll drains the expiring contract while it still trades (Sep: 17.0M -> 10.4M over
    22-28 Sep), so its OI change would read the roll, not positioning. The CVD read is untouched."""
    assert grounds.roll_why("2026-09-28", "2026-09-29") == "the Sep future is rolling into Oct"
    assert grounds.roll_why("2026-09-23", "2026-09-29") == "the Sep future is rolling into Oct"   # 6 days out
    assert grounds.roll_why("2026-09-22", "2026-09-29") is None                                     # 7 days out: not yet
    assert grounds.roll_why("2026-09-30", "2026-09-29") is None                                     # the Oct contract's first day
    assert grounds.roll_why("2026-12-28", "2026-12-29") == "the Dec future is rolling into Jan"
    assert grounds.roll_why("2026-09-28", None) is None and grounds.roll_why(None, "2026-09-29") is None
    b = bars([0, 20, 40, 60, 80, 100, 120, 520])
    for i, x in enumerate(b):
        x["oi"] = 1000 + i
    assert grounds.facts(b, [], [])["fut_oi"].startswith("futures OI +3 with price")
    F = grounds.facts(b, [], [], roll=grounds.roll_why("2026-09-28", "2026-09-29"))
    assert F["fut_oi"] == "futures OI: could not check — the Sep future is rolling into Oct"
    assert F["cvd"]["rank"] == 1.0
    fr = [{"side": "CE", "k": 22900.0, "state": "BUILDING"}, {"side": "PE", "k": 22900.0, "state": "BUILDING"}]
    row = grounds.ground({"verdict": "WAIT"}, 22890.0, b, [], fr, roll="the Sep future is rolling into Oct")["calls"][0]
    assert row["oi"]["fact"].endswith("· futures OI: could not check — the Sep future is rolling into Oct")


def test_sensex_flow_is_blind_with_its_lot_count():
    """P1-02: a future printing 7-10 lots a bar has no flow to read; the count is the reason, never quiet."""
    b = bars([0, 20, 40, 60, 80])
    for x in b:
        x["vol"] = 8.0
    F = grounds.facts(b, [{"t": b[-1]["t"], "side": 1}], [], idx="SENSEX")
    assert F["flow"] is None and F["flow_why"] == "SENSEX future, 8 lots this bucket"
    assert F["cvd"] is not None                                          # only the flow read is blind
    assert grounds.facts(b, [], [], idx="NIFTY")["flow"] is not None
    assert grounds.facts([], [], [], idx="SENSEX")["flow_why"] == "SENSEX future: no closed ladder bar yet"
    row = grounds.ground({"verdict": "WAIT"}, 100.0, b, [], [], idx="SENSEX")["calls"][0]
    assert row["flow"]["state"] == grounds.BLIND and row["flow"]["fact"] == "SENSEX future, 8 lots this bucket"
