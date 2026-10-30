# J2: the Jarvis Brain (`jarvis.py`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One server-side brain that, for any index / day / minute, builds the full Jarvis frame from the record (causal). It feeds Fable's jarvis2 face live through `GET /api/jarvis`, and the evening replay from the same code.

**Architecture:** `docs/kahani/review/scripts/export_mockup.py` already computes almost the whole frame, validated on 28 and 29 Oct in jarvis2 / jarvis2_live:
- walls, handshake, fuel runs, fights, verdicts, bands;
- Sides and writer flow ±7.

But it is procedural and pulls REST and HTTP on import. J2 does the following:
1. **Moves that body into `jarvis.py`** as `build(day, idx, upto)`: a pure function of the record, with no network.
2. **Ports the face's reads into Python**, so the face only draws (one brain):
   - SPEED, TOP / BOTTOM SIGNS, ALL 3, MANAGE, today in jarvis2.html JS;
   - WRITER FLOW ±7 states, today in jarvis2_live.html JS.
3. **Adds the GAPS checklist's missing pieces:**
   - health with Dext named;
   - the one CALL, both ways;
   - "fuel still driving" counting option-side fuel;
   - MANAGE judged against price.
4. **Serves it at `/api/jarvis`** and lets jarvis2.html load it live.

`export_mockup.py` becomes a thin wrapper.

**Tech Stack:** Python 3.13 (stdlib only), pytest, the existing record modules (`handshake`, `fronts`, `chain_backfill`, `dext_log`, `book_log`, `sides`, `effort`), and the static jarvis2.html page.

**Inputs and order:** `docs/kahani/review/GAPS-AND-LIVE-CHECKLIST.md` §3 / §4 / §5. **Findings:** `docs/live/DAY-2026-10-29.md` §4–§8. **Spec:** `docs/superpowers/specs/2026-10-28-kahani-design.md` §14–§17. **NOTEPAD:** A149–A175.

## Global Constraints

- **Display only. No order path, ever.** MANAGE lines carry "guidance only".
- **No hit rate, win rate or %:** counts like `2/3`, `tested ×5 · broke 0`. Levels tagged `s` / `f`. Thresholds marked `[I]` (inferred).
- **English words (§16.2):**
  - WALL, PUSH, HELD / DEFENDED / BROKEN / TRAPPED / BREAK FAILED;
  - FUEL / FUEL SPENT, ROTATE / CONTINUE / UNCLEAR;
  - NO TRADE: quiet / can't see / shock.
- **Causal:** `build(day, idx, upto)` reads only minutes `< upto` (a minute m is complete at m+1).
- **A missing source is named, never read as zero** (CLAUDE.md rule 6: "checked-nothing / could-not-check / not-shown" stay three sentences).
- **Reuse before building:** call the existing modules (`handshake`, `fronts`, `sides`, `effort`, `chain_backfill`, `dext_log`). Never add a second copy of a read that exists.
- **Writers first** (GAPS §2.2): fuel = futures-OI runs + Sides 2×2 + writer flow ±7 + handshake BROKEN + put writers lifting the floor (call writers lowering the cap).
- **Untouched:** §1b / §1d / §1i–§1r registrations, `fronts.py`, `voice.py` and the zone machine are not changed.
- **Tests never write under `data/`:** conftest redirects DIRs; read-only fixtures from the record are allowed.
- **No commit:** commit only on her word. **No server or Vite restart by the agent; nothing during market hours** (09:15–15:40 IST). She restarts.
- **Never read or print** `tapemap/telegr/*` or `.upstox_token`. J2 needs no network at all.
- **Browser global names** (`top`, `name`, `status`, `event`, `parent`…) are never top-level identifiers in page JS.

---

### Task 1: `jarvis.build`, the exporter as a pure, causal module

**Files:**
- Create: `tapemap/jarvis.py`.
- Modify: `tapemap/docs/kahani/review/scripts/export_mockup.py` becomes a thin wrapper: `data = jarvis.build(DAY, IDX, END_minute)`, then write JSON as today, keeping `KAHANI_DAY / KAHANI_END / KAHANI_OUT`.
- Test: `tapemap/test_jarvis.py`.

**Interfaces:**
- Produces: `jarvis.build(day: str, idx: str = "NIFTY", upto: int | None = None) -> dict`.
  - The dict keeps **every key** the exporter writes today (`mins, fut, fo, fhi, flo, spot, delta, fvol, vwap, sd, bnf, sx, oi, oi_src, runs, pushes, timeline, verdict, zone, fights, holes, chain_missing, ladder, strikes, sides…, wf_ce, wf_pe`…), so jarvis2.html and jarvis2_live.html load it unchanged.
  - `upto` = minute-of-day; None = the whole session.
- **Inputs, no network:**
  - futures 1-minute OHLC + OI from Dext 0.8.1's `dext_log.read_ohlc(tag, day)`, else built from the book (`book_log` ltp / oi per minute), tagged `src`;
  - spot from the chain record + `chain_backfill.read_grid` (carried);
  - Sides from the same function the server's `/api/sides` route calls (find it in `server.py`; no HTTP);
  - everything else as the exporter does now.

- [ ] **Step 1:** Read `export_mockup.py` end to end, plus `jarvis2.html` and `jarvis2_live.html` (their data contract).
- [ ] **Step 2: Write the failing tests** (`test_jarvis.py`). They read the record read-only, are skipped when the day's files are absent, and the numbers are measured (A155 / A157):

```python
import os
import pytest
import jarvis

def _has(day):
    return any(os.path.exists(f"data/book/book_NIFTY_{day}.jsonl{z}") for z in ("", ".gz"))

@pytest.mark.skipif(not _has("2026-10-28"), reason="28 Oct record not present")
def test_28oct_the_break_the_fuel_and_the_verdict():
    d = jarvis.build("2026-10-28", "NIFTY", 13 * 60 + 41)
    assert d["mins"][0] == "09:15" and d["mins"][-1] == "13:40"
    toot = [p for p in d["pushes"] if p["t"] == "12:43"][0]
    assert toot["ans"] == "TOOT" and toot["held_at"] == "12:47"        # Dext flow + handshake-2 (A155)
    cover = [r for r in d["runs"] if r["kind"] == "COVER" and r["start"] == "12:41"][0]
    assert cover["khatam"] == "12:58" and cover["lots"] == -1726
    assert d["verdict"]["SELL"]["12:12"]["word"] == "CHALEGA"           # CONTINUE: fuel x (cover -775)

@pytest.mark.skipif(not _has("2026-10-28"), reason="28 Oct record not present")
def test_causal_prefix():
    full = jarvis.build("2026-10-28", "NIFTY", 13 * 60 + 41)
    part = jarvis.build("2026-10-28", "NIFTY", 12 * 60 + 50)
    assert part["mins"][-1] == "12:49"
    for p in part["pushes"]:
        if p.get("held_at") or p.get("am"):
            assert any(q["t"] == p["t"] and q["ans"] == p["ans"] for q in full["pushes"])
```

- [ ] **Step 3:** Implement `jarvis.build`.
  - Move the exporter's body into functions. Nested defs that read the day's state are fine.
  - Replace `bars()` (REST) with the Dext / book source, and the Sides HTTP GET with the direct call.
  - Make the window end = `upto`.
  - Keep every rule exactly as the exporter has it: this task only moves code.
- [ ] **Step 4:** `python -m pytest test_jarvis.py -q` → PASS. Then `KAHANI_DAY=2026-10-28 python docs/kahani/review/scripts/export_mockup.py`; its `pushes`, `runs` and `verdict` must equal the current `mockup/data_28oct.json` (minus `made`). Back the JSON up to the scratchpad before overwriting it.
- [ ] **Step 5:** No commit (her word).

### Task 2: the reads move from the face into the brain (one brain)

**Files:**
- Modify: `tapemap/jarvis.py`; adds `reads(d) -> dict`, called at the end of `build`, stored as `d["reads"]`.
- Test: `tapemap/test_jarvis.py`.

**Interfaces:** `d["reads"]` holds:
- `speed[i]` = `{x, dir, word}`;
- `signs` = `[{b, at, isHigh, n, items[], driving}]`;
- `sync[i]` = `{dir, ch}`;
- `writers[i]` = `{state: "UP" | "DOWN" | "PAUSED" | "BACK" | "RISK" | None, ce, pe}`;
- `manage` = `[{at, t, side, st, pts, trail, with[], against[]}]`;
- `notrade` = `[{from, to, why}]`.

**Rules** (port them exactly from jarvis2.html / jarvis2_live.html JS, then apply these corrections from DAY-2026-10-29 §8):
1. **SPEED:** |3-min delta| ÷ its own median so far; FAST ≥ 2, SLOW ≤ 0.5 [I].
2. **TOP / BOTTOM SIGNS:**
   - at a fresh 30-min high or low, on the 3-min bars from 09:15;
   - the signs: candle against delta; absorption (lots/pt ≥ 2× the median of the 3-min bars so far); exhaustion (delta < ½ of the stronger of the 2 bars before);
   - speaks at ≥ 2/3.
   - **`driving` = ANY fuel still pushing into the extreme:** a live futures-OI run that way (unless a ≥ 2× bar run spent ≤ 10 min ago); writers ±7 UP for a high / DOWN for a low; a handshake BROKEN that way in the last 10 min; put writers lifting the floor (PE ±7 ≥ +10L / 3 min) for a high, call writers lowering the cap for a low.
3. **WRITER FLOW ±7** (DAY §5):
   - 3-min OI change summed over ATM ±7 strikes per side;
   - UP = CE ≤ −10L and PE ≥ +10L (DOWN mirrors);
   - PAUSED = after UP, the covering side ≥ −2L and the building side < half its leg peak;
   - BACK = fuel returns;
   - **RISK = PAUSED and 3-min delta ≥ 2× day median against, within 9 min** [I].
4. **ALL 3:** NIFTY fut / BANKNIFTY / SENSEX all moved ≥ 10 / 25 / 35 pts the same way in 5 min [I].
5. **MANAGE**, per zone trigger, at 3-min closes for 45 min:
   - **judge the trade against price first: AGAINST YOU when pts ≤ −15**, whatever else says;
   - HOLD at ≥ +15 with the data with her;
   - BOOK / TRAIL TIGHT at ≥ +15 with any sign against;
   - ≥ 6 min apart, on change only;
   - trail = the nearest band (d2 / d1 / VWAP / u1 / u2) beyond price.
6. **NO TRADE:** 20 quiet minutes (no break, no fuel, no trigger, writers not UP / DOWN) → `why: "quiet"`. A data hole → `why: "can't see"`.

- [ ] **Step 1: Failing tests:**

```python
@pytest.mark.skipif(not _has("2026-10-28"), reason="28 Oct record not present")
def test_28oct_top_signs_at_the_high():
    r = jarvis.build("2026-10-28", "NIFTY", 13 * 60 + 41)["reads"]
    s = [x for x in r["signs"] if x["isHigh"] and x["n"] == 3]
    assert s and not s[0]["driving"] and s[0]["at"] == "13:03"          # red on +374, absorption, exhaustion (A157)
    early = [x for x in r["signs"] if x["isHigh"] and x["at"] in ("12:45", "12:48", "12:57")]
    assert early and all(x["driving"] for x in early)                    # cover still running: not a top yet

@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_29oct_writer_flow_sequence():
    d = jarvis.build("2026-10-29", "NIFTY", 11 * 60)
    st = {m: w["state"] for m, w in zip(d["mins"], d["reads"]["writers"]) if w["state"]}
    near = lambda hm, want: any(st.get(x) == want for x in (hm, f"{hm[:3]}{int(hm[3:]) - 1:02d}", f"{hm[:3]}{int(hm[3:]) + 1:02d}"))
    assert near("09:41", "UP") and near("09:44", "PAUSED") and near("10:38", "RISK")   # DAY §5, +/- 1 min

@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_manage_judges_the_trade_against_price():
    d = jarvis.build("2026-10-29", "NIFTY", 12 * 60)
    for m in d["reads"]["manage"]:
        assert not (m["st"] == "HOLD" and m["pts"] < 0)                  # the -120 pts HOLD bug (GAPS §1)
        assert m["pts"] > -15 or m["st"] == "AGAINST YOU"
```

Never change a rule to make a test pass: re-check the measurement, and report a real difference.
- [ ] **Step 2:** Implement `reads(d)` in Python, porting the JS line by line with the corrections above.
- [ ] **Step 3:** `python -m pytest test_jarvis.py -q` → PASS. No commit.

### Task 3: health and the ONE CALL (GAPS §4)

**Files:** Modify `tapemap/jarvis.py` (adds `health(d)` and `call(d)`, stored as `d["health"]` and `d["call"]`). Test: `tapemap/test_jarvis.py`.

**Interfaces:**
- `d["health"]` = `{dext: {minutes, missing: [[from, to]...], book_only_tail: n}, holes: [[a, b]...], chain_missing: [...], bnf_chain_readable: bool, notes: [str]}`.
- `d["call"]` at `upto` = `{word: "UP" | "DOWN" | "RANGE" | "NO TRADE", why: [str], wrong_line: str, up: str, dn: str, buyer: str, seller: str, missing: [str]}`.

**Rules:**
- **The order** is GAPS §4: health → location (bands, σ) → flow + speed → writers (Sides 2×2 slot, writer flow state, walls ahead / behind, handshake, trapped) → futures-OI quadrant → cross-index → her setup → one call.
- **The word:**
  - UP / DOWN only when writers (Sides REAL / BACKED, or ±7 UP / DOWN) and at least one more of {fuel run, speed FAST, ALL 3} agree;
  - RANGE when both sides add;
  - NO TRADE when quiet or blind;
  - writers RISK names the risk in `why`.
- **The expression, both ways:** buyer = buy the CE (UP) / PE (DOWN) at the band; seller = sell the side the writers are writing (PE on UP, CE on DOWN).
- **Every missing source goes into `missing`**, e.g. "Dext footprint missing since 14:45 · newest 26 min from the book".

- [ ] **Step 1: Failing tests:**

```python
@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_29oct_health_names_dext_missing():
    h = jarvis.build("2026-10-29", "NIFTY", 15 * 60 + 11)["health"]
    assert any(a <= "14:46" and b >= "15:10" for a, b in h["dext"]["missing"])      # DAY §7: missing since 14:45

@pytest.mark.skipif(not _has("2026-10-29"), reason="29 Oct record not present")
def test_29oct_call_at_1040_names_the_risk():
    c = jarvis.build("2026-10-29", "NIFTY", 10 * 60 + 40)["call"]
    assert c["word"] != "UP" and "RISK" in " ".join(c["why"]).upper()               # 10:38 TOP RISK
```

- [ ] **Step 2:** Implement `health` and `call`. **Step 3:** Tests pass. No commit.

### Task 4: the server serves it, and fixes the two lag findings

**Files:**
- Modify `tapemap/server.py`: a `GET /api/jarvis?idx=&day=&upto=` route.
- Modify `server._hs_pass`: tag late-born pushes.
- Create `tapemap/tailread.py`: an incremental reader, only if `book_log` / `dext_log` / `confluence_log` have none. It is used by `handshake.load` and `jarvis.build`.
- Tests: `test_jarvis.py`, `test_handshake.py`.

**Rules:**
- **`/api/jarvis`:**
  - today = `jarvis.build(today, idx, now_minute)`, cached 20 s per idx;
  - a past day or an explicit `upto` replays on request, refused 09:15–15:40 IST except for today (spec §6.2);
  - JSON through the server's existing helper;
  - CORS the way the other `/api/*` GET routes do it.
- **Incremental loading** (A175: afternoon handshake passes 10–40 s, re-reading the whole day): keep `(path → offset, rows)`, append only new lines when the file grew, and re-read when it shrank or the day changed.
- **Late-born pushes** (A175: 09:53 shown 35 min late, 10:23 6 min late, born when a Dext refill rewrote past minutes): in `_hs_pass`, a newly answered push whose confirmation minute is more than 3 minutes before `upto` is written with `quiet: True` and its line ends `· backfilled`. Telegram already skips `quiet`.

- [ ] **Step 1: Failing tests:**
  - (a) the incremental reader equals a full read after an append, and re-reads after truncation;
  - (b) `_hs_pass` with a push first answered 5 minutes late writes `quiet: True`, following `test_handshake.py::test_the_server_says_each_push_once_and_logs_it_once_across_a_restart`;
  - (c) the `/api/jarvis` handler returns `ok` with `mins` for a mock day, following the existing server route tests.
- [ ] **Step 2:** Implement. **Step 3:** `python -m pytest test_jarvis.py test_handshake.py test_messages.py -q` → PASS. No commit, no restart.

### Task 5: jarvis2 reads the live frame

**Files:** Modify `tapemap/docs/kahani/review/mockup/jarvis2.html` (and `jarvis2_live.html` if it shares the loader).

**Rules:**
- **The source:** `?api=<url>` (e.g. `http://127.0.0.1:8765/api/jarvis?idx=NIFTY`) loads the frame instead of a JSON file, and re-polls every 20 s, keeping the playhead at "now" unless she scrubs.
- **One brain:** when `d.reads` / `d.call` / `d.health` exist, the page renders them instead of computing its own. Its JS reads stay only as the fallback for old JSON files.
- **Show** `health.missing` in the state strip, and `call` (word · wrong-line · buyer / seller) in the right panel's top card.

- [ ] **Step 1:** Implement.
- [ ] **Step 2:** Verify in the browser:
  - her server does not have `/api/jarvis` until her restart, so verify with JSON written by `export_mockup.py` from `jarvis.build` (same shape);
  - no console errors; screenshots at 12:12 and 13:03 (28 Oct) and 10:38 (29 Oct).
- [ ] **Step 3:** No commit.

### Task 6: the whole suite and the replay

- [ ] `python -m pytest -q -p no:cacheprovider --deselect test_v2feed.py::test_serve_caches_full_and_answers_delta` → all pass (2,113 before J2, plus the new ones).
- [ ] Replay 28 Oct and 29 Oct through `export_mockup.py` (KAHANI_DAY) and open them in jarvis2. DAY §5 and the A157 reads must show.
- [ ] **NOTEPAD entry** (CRLF-safe binary edit, next free A-number after A175): what was built, the checks with numbers, what stays owed. **No commit.**

## Self-review

| What | Where |
|---|---|
| GAPS §3 / §4 / §5 | Tasks 2–3 |
| DAY §8: lag, J2, option-side fuel in signs, MANAGE vs price, Dext missing | Tasks 2–4 |
| A175: late-born pushes, incremental load | Task 4 |
| one brain | Task 5 |

Out of scope, owed:
- J3, jarvis2 inside the ui-v2 Trade tab;
- READ's word listening to the writers;
- the BANKNIFTY / SENSEX answer bar;
- A105.
