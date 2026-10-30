# J1: Data Truth Implementation Plan (KAHANI / JARVIS)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jarvis must never speak from a fake push, an unconfirmed wall break, or a blind minute. Its 2–3 minute delay must be measured live so the fix rests on facts.

**Architecture:** Three surgical changes to the existing handshake (A132) and the message pass, plus a replay check on the record:
1. `handshake.holes` drops every minute a book gap > 60 s touches, from the flow and the futures OI.
2. `answer` (first-crossing) stamps TOOT / PHANS / TIKI only when the next chain minute confirms it (handshake-2).
3. `_msg_pass` writes its own timing to `data/messages/pass_<day>.jsonl`.

`palat` reads the same `book_flow` (one copy), so it inherits the hole rule; its m+4 read (`first=False`) is unchanged.

**Tech Stack:** Python 3.13, pytest, the record files (`book_log`, `confluence_log`).

**Spec:** `docs/superpowers/specs/2026-10-28-kahani-design.md` §7, §14 rows 1 / 8 / 9, §16.6 J1.

## Global Constraints

- Display only; **no order path**; no hit rate, win rate or %.
- Tests never write under `data/`: conftest redirects every DIR to `tmp_path`.
- §1b / §1d / §1i–§1r are untouched. `fronts.py` is untouched.
- **No commit:** commit only on her word (standing rule; it overrides the skill's commit steps).
- **No server or Vite restart, and nothing during market hours.** Her restart loads it in the morning.
- The book is the 1-second futures book (`book_log`), rows `{t: epoch ms, ltp, b, a, vtt, oi, ik}`.

## Two J1 items dropped, with the measurement that dropped them

1. **The chain backfill seeding §1d's peaks (A143 finding 7) was wrong about the live tool.** `chain_live` → `chain_backfill.start_backfill` writes the REST morning into `ChainState.minutes`, and `fronts.read` builds each front's peak from those minutes. The 10:37 peak was missing only from **my replay and Fable's export**, which read `data/chain/` alone. The J2 loader must read `chain_backfill.read_grid`, as `confluence_log` does.
2. **Coverage of the sleep already reached her.** On 28 Oct the stream logged `HEALTH · RECORDING NAHI · GoCharting` at 13:00 and `RECORDING OK` at 13:02. The frame-level coverage box is J2 (§6.4).

## The lag, as measured tonight (why Task 3 measures instead of fixing)

| Fact | Measured |
|---|---|
| The 12:44 TOOT | crossed at the 12:47 chain minute; its last snapshot is at 12:47:52 (one snapshot every ~11 s, median) |
| `_hs_pass` rule | the minute is known once `upto = (now−20)//60 ≥ 12:48`, i.e. from 12:48:20 |
| The FLOW line | written at 12:49:50, about 90 s later |
| Offline cost of one pass | read log 0.03 s, decode log 0.02 s, build 0.01 s, `palat.load` 1.3 s, `handshake.load` 1.0–2.3 s |

The pass's own work does not explain 90 s. The live process does, and only live timing rows can say which part. The fix follows those rows.

---

### Task 1: Book holes drop their minutes from the flow and the futures OI

**Files:**
- Modify: `handshake.py`:
  - add `GAP_S`, `holes`, `hole_minutes`;
  - `book_flow`;
  - `load` (the `oim` entry and `holes`).
- Test: `test_handshake.py` (append).

**Interfaces:**
- Produces:
  - `handshake.GAP_S = 60`;
  - `holes(rows) -> list[tuple[int, int]]` (ms pairs);
  - `hole_minutes(hs) -> set[int]`;
  - `inp["holes"]`.
- Consumes: `handshake.mod(ms) -> int`.

- [ ] **Step 1: Write the failing test**

```python
def _book(t0_ms, secs, gap_at=None, gap_s=0, buy_after_gap=0):
    """1-second book rows from t0, 1 lot at the ask each; a gap of gap_s seconds before row gap_at, whose first row carries
    buy_after_gap lots of catch-up volume (the laptop waking)."""
    rows, t, vtt = [], t0_ms, 0
    for i in range(secs):
        if gap_at is not None and i == gap_at:
            t += gap_s * 1000
            vtt += buy_after_gap * 65
        rows.append({"t": t, "ltp": 101.0, "b": [[100.0, 1]], "a": [[101.0, 1]], "vtt": vtt, "oi": 1000 + i})
        t += 1000
        vtt += 65
    return rows


def test_a_book_hole_drops_every_minute_it_touches_from_the_flow():
    t0 = int(datetime(2026, 10, 28, 12, 50, tzinfo=IST).timestamp() * 1000)
    rows = _book(t0, 600, gap_at=250, gap_s=374, buy_after_gap=3534)
    hs = handshake.holes(rows)
    assert len(hs) == 1 and hs[0][1] - hs[0][0] == 375 * 1000
    blind = handshake.hole_minutes(hs)
    d, v = handshake.book_flow(rows, 65)
    assert blind and not (blind & set(d)) and not (blind & set(v))   # no flow is read in a minute the book could not see
    assert max(abs(x) for x in d.values()) < 100                     # the catch-up's 3,534 lots never become a minute's delta
    assert handshake.holes(_book(t0, 600)) == []
```

- [ ] **Step 2: Run it and see it fail.** `python -m pytest test_handshake.py -q -k hole`. Expected: `AttributeError: ... 'holes'`.

- [ ] **Step 3: Implement** (exact code as built: see `handshake.py`, `holes` / `hole_minutes` / `book_flow` / `load`).
  - `book_flow` skips any trade whose previous row is more than `GAP_S` s older.
  - It drops every `hole_minutes` minute from both dicts.
  - `load` drops them from `oim` and returns `"holes"`.

- [ ] **Step 4: Run the tests.** `python -m pytest test_handshake.py test_palat.py -q`. Expected: all pass.

- [ ] **Step 5: No commit** (her word).

### Task 2: handshake-2, an answer is stamped only when the next chain minute confirms it

**Files:**
- Modify: `handshake.py`: `REV`, `answer`, `read`.
- Test: `test_handshake.py`. Update the first-crossing test, and append the wapas test.

**Interfaces:**
- Produces:
  - `answer` adds `"held": j2` to a confirmed TOOT / PHANS / TIKI, and `"wapas": True` to a NAHI whose wall crossed and came back;
  - a crossing that is not yet confirmable returns `None`;
  - `read()` rows gain `"held"` (`"HH:MM"` | None) and `"wapas"` (bool);
  - `REV = "handshake-2 (A143)"`.
- Unchanged: `first=False` (palat). `k=` (the voice's `defend`) inherits the hold.

- [ ] **Step 1: Tests.** In `test_the_answer_is_the_first_minute_the_wall_crosses_its_bar`, replace the `643 == {... "am": 642}` line with:

```python
    assert handshake.answer(R, ms, p[0], 643) is None                     # crossed at 10:42; 10:43 has not confirmed it yet
    assert handshake.answer(R, ms, p[0], 644) == {"ans": "TOOT", "k": 22550, "chg": -5.0, "bar": 4.0, "am": 642, "held": 643}
```

Append:

```python
def test_a_crossing_that_comes_back_the_next_minute_is_wapas_not_toot():
    """A143: 17 of 103 NIFTY answers over 16 days read differently at m+4 than at the first crossing; 13 were a TOOT that
    read NAHI (19 Oct 10:41: -12.8L, then +4.4L). Here the wall is cut 5L at 10:42 only and is back at 10:43."""
    inp = scene()
    p = handshake.pushes(inp["F"], inp["ms"], 150)[0]
    R = copy.deepcopy(inp["R"])
    for m in range(643, 690):
        for s in R[m]["strikes"]:
            if s["k"] == S - 50:
                s["pe"]["oi"] = 1e7
    assert handshake.answer(R, inp["ms"], p, 644) is None                 # un-crossed at 10:43: read on to 10:44 (m+4)
    assert handshake.answer(R, inp["ms"], p, 645) == {"ans": "NAHI", "k": S - 50, "chg": 0.0, "bar": 4.0, "am": 644,
                                                      "wapas": True}
    row = handshake.read(dict(inp, R=R), 646)[0]
    assert row["ans"] == "NAHI" and row["wapas"] is True and row["held"] is None
```

- [ ] **Step 2: Run them and see them fail.** `python -m pytest test_handshake.py -q -k "first_minute or wapas"`.

- [ ] **Step 3: Implement** in `answer`'s first-crossing loop:
  1. A crossing at j < m4 returns `None` until the next chain minute j2 is known.
  2. If j2 crosses the bar the same way, return j's answer with `"held": j2`.
  3. Otherwise set `wapas` and keep reading.
  4. m4 is final as before. A NAHI at m4 after a wapas carries `"wapas": True`.

  `read` copies `held` / `wapas` onto the row.

- [ ] **Step 4: Run the tests.** `python -m pytest test_handshake.py test_palat.py test_voice.py -q`.

- [ ] **Step 5: No commit** (her word).

### Task 3: The message pass writes its own timing (the lag, measured live)

**Files:**
- Modify: `server.py`: `_msg_pass` gains `time.perf_counter()` marks around read / health / palat / hs / write, plus a new `_pass_log(day, d, ts)`.

**Produces:**
- `data/messages/pass_<day>.jsonl`, one row per pass between 09:15 and 15:45:
  `{t, read_s, health_s, palat_s, hs_s, write_s, total_s, hs_upto, chain_last}`;
- fail-soft;
- display only.

- [ ] **Step 1: Implement** (I/O only, fail-soft; no branch worth a test).
- [ ] **Step 2: Run the tests.** `python -m pytest test_messages.py test_handshake.py -q` (conftest's mock redirects `MSG_DIR`).
- [ ] **Step 3: No commit** (her word).

### Task 4: Prove it on the record, then the full suite

- [ ] **Step 1:** `docs/kahani/review/scripts/j1_check.py` (read-only). For every NIFTY book day it prints:
  - the holes;
  - the pushes and how many were answered;
  - the wapas count;
  - every 28 Oct row.

- [ ] **Step 2:** Run it. Expected on 28 Oct:
  - one hole at 12:54 (≈375 s);
  - **no 13:01 push**;
  - 12:44 TOOT with am 12:47 and held 12:48;
  - 12:49 TIKI held 12:53;
  - 12:53 TOOT;
  - the other pushes NAHI, as in A142.
- [ ] **Step 3:** `python -m pytest -q`. Expected: as before J1 (2079 pass, 1 skipped, the known flaky `test_v2feed` A49) plus the 2 new tests.
- [ ] **Step 4:** NOTEPAD entry (CRLF-safe):
  - what changed;
  - the 28 Oct before / after;
  - finding 7 corrected;
  - "loads at her restart".
- [ ] **Step 5: No commit.** Tell her to restart before the open; the pass log appears in `data/messages/pass_<day>.jsonl`.
