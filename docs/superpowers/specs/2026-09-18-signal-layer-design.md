# The signal layer — buy, sell, levels, breadth

Designed 2026-09-18 against the brain as it runs (server up 09:33, NIFTY frame live on 8765). Advisory only: no order path, here or later. No hit rate, win rate, expectancy, probability or confidence score in anything this produces — §A.4 quotes the 2026-09-16 study's own figures to defend a threshold, and those figures stay in this document and never reach a screen. Every published number is tagged `[M]` measured or `[I]` inferred; every absence is one of three sentences — `—` checked and found nothing, `?` could not check with the reason printed inline, or omitted with the header naming what is gone.

This **subsumes the approved confirmations-both-sides design** (four votes: wall, event, depth, OI; one measured vote fires; OI never alone). Everything it specified survives; §A.9 lists what I change and why.

---

## A. The signal

### A.1 One grammar, two sides, one intent

A signal is a **visit**, not a bar and not a tick: one object per visit to a σ pocket, per side, per index. Both sides are the same machine with four comparisons flipped — `band_rotation.run_states` already is that machine and already runs on `d2`/`u2` (`live.py:1046`, the §1b zone rule: reaching the near edge *is* the event). Nothing new is built for the sell side.

**Both sides are a fade toward VWAP.** Buy fades up from the lower pocket, sell fades down from the upper. The signal's `target` is always the VWAP price. Every sell signal carries `not_a: "outright short"` and the upper zone on the Field is stamped `outright sell: dead list — rejected across five datasets`. There is no trend signal in this layer and there will not be one.

### A.2 States, and exactly what moves them

```
WATCHING → REACHED → ARMED → LIVE → SPENT | STOPPED
                 ↘ ──────────→ VOID
feed gap across an unclosed bar → the state HOLDS and prints BLIND
```

| Transition | What moves it | Source |
|---|---|---|
| WATCHING → REACHED | first bar of this visit whose low ≤ `d2` (buy) / high ≥ `u2` (sell), taken from that bar's own `tape.bands[i]`, not the current band | [M] tape |
| REACHED → ARMED | `zone_state[i].ref_i is not None` — the two-candle machine holds a reference | [M] `run_states` |
| ARMED → LIVE | `zone_state[i].entry is not None` (a close past the arm bar's extreme) **and** the ballot passes (§A.4) | [M] + ballot |
| ARMED → VOID | the reference expired: `i − ref_i > 10` bars, no entry | [M] `run_states` |
| LIVE → SPENT | a bar touches VWAP | [M] |
| LIVE → STOPPED | the frozen falsifier is hit (§A.6) | [M] |

**REACHED is latched.** Today `setup.reached` is `in_buy or in_sell or machine active` — a live-price test that goes false the moment price leaves the pocket. That reads the arm, not the reach, and it is the 09:45 failure the verdict caught. Latched means: once a bar of this visit has touched the near edge, `reached_at` is set and never moves for the life of the visit, whatever price does next. It may latch **intrabar** on the forming bar's running low/high, tagged `provisional: true` until that bar closes — a printed low does not un-print.

### A.3 The visit, its ordinal, and the window

`visit_key = "{side}@{first_t}"` where `first_t` is `arm.first_t` — the **setup's first arm**, not the current reference. This is a defect fix. `run_states` publishes `arm.{first_i, first_t}` precisely so that a run of falling lows collapses into one setup (§5c); `frame._setup` reads `ref_i`, so when branch 3 moves the reference to a new lower low the visit key changes mid-visit and the record gets two rows for one setup. `arm` is non-None only on arming bars, so `signal.py` scans the `zone_state` list backwards for the most recent non-None `arm` — the same walk `frame._events_and_armed` already does. No new input.

**A visit ends** when a bar closes on the VWAP side of the near edge by more than `0.5σ`, or at 15:30. A touch after that is the next visit. `visit_ordinal` counts per side per day and increments at each REACH latch.

**The window is 09:45–13:15 inclusive**, judged on `reached_at`, on the tape's clock (the close time of the last closed bar) — not the wall clock, so a late start or a replay carries its own time, the same rule `frame.build` already applies to warm-up. `is_edge = (visit_ordinal == 1) and in_window`.

A signal with `is_edge false` is still built, recorded and drawn — in grey, silent, first line reading `visit two — not your edge` or `13:48 — outside the window`. Its record rows are tagged `out_of_method` and never pool with the edge population.

### A.4 The ballot — four votes, threshold one

Verbatim from the approved design. Pocket `P = [d3,d2]` buy / `[u2,u3]` sell; edge `e = d2`/`u2`; row `r = tape.rowSize` (5).

1. **WALL [M]** — a tape wall of the setup's side, not broken, priced inside `P` or within `3r` of `e`, `since` inside the visit.
2. **EVENT [M]** — an initiative bar of the setup's side inside `P ± 3r`, or absorption / exhaustion / trap within `3r` of `e` (the existing `CONFIRMS` grammar).
3. **DEPTH [M]** — over the visit's minutes, futures depth sweeps (`senses` rows `kind: swept`) summed by side; buy: `buyQty ≥ 1.5 × sellQty` and `≥ 5` buy sweeps. `null` when the senses thread has no rows for the window.
4. **OI [I]** — buy: fresh put writing at strikes at or under `e` (`chg > 0`, at least one with `conf == "session"`) **and** put writers above `e` under water (`pain > 0`). Sell mirrored. From `walls.rows`, which already carries strike, chg, pain, conf, basis. `null` when the chain has not answered.

**Threshold T = 1 measured vote, and the vote may not be OI alone.**

From the study, not from taste. Over 35 triggered visits on six sessions: 0-of-4 is the worst bucket on both axes (VWAP-hit 57%, MFE6 mean 9.3, n=7); 1-of-4 is best (79%, 18.7, n=14); 2-of-4 does not improve on it and is worse on adverse excursion (54%, 14.4, MAE6 31.3 vs 23.3, n=13). 3-of-4 is n=1 and 4-of-4 is n=0 — untested, and no six-day sample will ever populate them. Some gate beats no gate; a second stacked gate bought nothing on the only sample that exists.

**Why OI never alone:** it is true on 20 of 27 visits where it is measurable. A condition true three times in four is background, not a filter, and it is the only `[I]` vote on the ballot — two OI heuristics on a ~10-second poll, not dealer positioning. So the ballot fires on one measured vote from **{wall, event, depth}**; OI adds weight and can never be the reason a sound happened.

**A vote computed on any backfilled minute is `ok: true, src: "backfill"` and does not count toward T.** The anytime-start rule applied to the ballot: a reconstructed morning may be shown, but only observed evidence rings a bell. A `null` vote never counts for or against; the card reads `2 of 3 measurable · depth not answered`.

### A.5 Fire, precisely

```
fire = reached_at is not None                   # latched, this visit
   AND zone_state[i].entry is not None          # close past the arm bar's extreme
   AND votes_observed ≥ 1, at least one of {wall, event, depth} true
   AND the trigger bar was not counted blind (§A.7)
```

Today's third term — `confirm["value"] != "UNCONFIRMED"` — is **deleted, not repaired**. `_book_for` passes `senses: None` on every request, so `confirm` is permanently `"not wired"` and the term is a no-op wearing a gate's clothes. The pair-rotation confirm belongs on the contract chart where both legs exist; on a single index series it is structurally `UNKNOWN` (`SINGLE_SERIES_CONFIRM_WHY`) and always will be. It stays on the frame as a printed field with its reason; it stops pretending to gate.

### A.6 The falsifier travels, frozen

Every signal carries, from REACH latch onward: `{px: d3 at the arm bar, rule: "a 5-minute close past 23,221 held for 3 bars", frozen_at: "09:45", drifted: false}`. Frozen at the arm bar's band values. Today `setup.falsifies` is a string rebuilt from the *current* band every frame, so the number she was shown at 09:45 is not the number being checked at 10:20 — the band moves with VWAP all session. When the live `d3`/`u3` has drifted more than `0.25σ` from the frozen one, `drifted: true` and the card prints both. The frozen one is what STOPPED is judged on.

### A.7 Blind is not waiting

If `health.gaps` covers a minute inside an unclosed bar between `ref_i` and now: `candles_left` does not decrement, the state does not advance, and the card says *"3 of 4 candles left. Feed down since 09:51 — the 09:50 bar's close is unseen; candles are not counted blind."* When the feed returns with the trigger already in the rebuilt bar, the signal goes LIVE carrying `seen_at` (when the brain saw it) beside `fired_at` (the bar that fired), and it sounds the **soft** bell, never the firm one.

### A.8 Sound — two, and nothing else

| Sound | When | Conditions |
|---|---|---|
| **soft click**, once | REACH latch | `is_edge` only. Also used for a LIVE the brain did not see live. |
| **firm bell**, once | → LIVE | `is_edge` only, `votes_observed ≥ 1` excluding OI-alone |

Nothing else ever makes a sound: not arming, not a vote landing, not a level going live or breaking, not a dead feed, not breadth, not the gate, not visit two, not a visit outside the window. The mute is on `is_edge`, not on the ballot, and that is what actually bounds frequency: at most two signals per index per session can sound, by construction, whatever T is.

### A.9 What I change from the approved design

1. **Votes move out of `frame.py` into a new pure `signal.py`.** `frame.py`'s own docstring says an object that quietly measured would be the one defect its composition test exists to catch. The ballot measures.
2. **`fire`'s chain-confirm term is deleted** (§A.5) — it gates nothing and could not on a single series.
3. **Added:** `reached_at` latched, `visit_ordinal`, `in_window`, `is_edge`. Her edge is the first visit in the window; the brain can compute that and does not state it.
4. **Added:** the visit key reads `arm.first_t`, not `ref_i` — a re-arm currently splits one setup in two.
5. **Added:** backfilled votes do not count toward T.
6. **Added:** the frozen falsifier.
7. **Added:** OI never alone — stated in the ask, supported by the study.

Nothing is removed: the four votes, their `null` semantics, `setup.pocket`, the chart ticks and the heavy edge segment all survive as written.

### A.10 Recorded forward, and what kills the population

`frame_log` already appends the whole frame on material change; `score_frame` already fills, per visit, favourable and adverse excursion at +1/+3/+6 bars and +90/+180 minutes, resolves each tell, and logs a control population of every walls row that was *not* the target at a similar distance. The signal row adds `signal{}` and `votes{}`. No new file, no new scorer.

The third column, from the verdict §6: **`took` / `skipped`**, one keystroke, written to `localStorage` against `visit_key` with an optional half-line and a lot count, exported with the record. No POST, no server write, no order path. It is a note, and notes are not orders.

**Kill conditions, stated before the first row:**

- **The ballot.** At n = 30 fired signals (sides reported separately, never merged into a verdict), if the +6-bar excursion of fired visits does not exceed the bare-reach control by one standard deviation of the control's own +6-bar distribution, the ballot is deleted, the signal fires on the reach alone, and the card says so.
- **Each vote.** At n = 30, any vote whose present-population +6-bar excursion does not exceed its absent-population by one sd is dropped from the ballot and demoted to a printed fact. DEPTH starts its clock with the study's warning attached (present n=4, VWAP-hit 25% vs 70% absent); it ships because n=4 is nothing, and it is the first candidate to go.
- **The window and ordinal.** At n = 30, if `is_edge` visits do not exceed non-edge visits by one sd at +6 bars, the mute rule is wrong, the window goes, and every visit sounds.
- **took/skipped.** If after 20 sessions more than half the rows are unanswered, the column is deleted rather than left on the screen as a half-kept promise.

---

## B. Levels to look for

### B.1 The split that must never blur

- **Hers to trade: two prices per side and one line.** `d2`/`d3`, `u2`/`u3`, VWAP. That is all of it. `signal.py` takes the bands and the tape and **never receives `walls.rows`**, except through the OI vote, which votes and does not originate. Enforced by the function signature, not by discipline.
- **Where the fight is: every ladder row.** A wall at 23,300 is not a trade. It is where a maker will walk price, let it dwell, and collect the stops. It changes where she expects to be *taken*, and what the runway pays if it breaks. It generates no entry.

The watch list carries a permanent header — `where the fight is — none of these is an entry`. That is the guardrail for the most likely way this screen makes her worse (§H.1), not decoration.

### B.2 Promotion to WATCHED

A `walls.rows` row is watched when it is within **1.5σ of spot** (σ scales with the day; a fixed point count does not) **and** any one of:

1. `agree` is non-null — a tape wall and an OI strike at one price. The strongest thing the brain can name, so always watched. [M]
2. `kind` in (PDH, PDL, PDC, ROUND, FLIP, OPEN) **and** the sequence machine is not IDLE — APPROACH, DWELL or RUN means price is engaging it. [M]
3. a tape wall with `leaned ≥ 2`. [M]
4. an OI strike in the day's top 3 by `|chg|` on its own side with `conf == "session"` — the ledger watched at least half of it build. [M]

**Cap 8, nearest first.** More than eight is a table again, and she rejected tables.

### B.3 Danger as flags, never as a score

Nothing is summed and no danger number is printed. Six named conditions, printed when met:

| Flag | Condition | Tag |
|---|---|---|
| `AGREE` | tape wall and OI strike at one price | [M] |
| `SIZE` | top 3 on its side by OI, or top 3 by tape wall size | [M] |
| `HELD \|\|\|` | `tests ≥ 2`, `last_outcome == "REJECT"` — tallied, not numbered | [M] |
| `DWELL 4m` | the dwell detector is holding here now, with minutes | [M] |
| `FUEL 41.2M` | trapped notional behind it, from `hunt.runways` | [I] |
| `CLOSING 8.4/min` | distance shrinking over the last 6 bars, points per minute | [M] |

The list is **ordered** by how many flags are met; the count orders and is never printed. Ordering is not a score, and the eye counts flags faster than it reads a number.

### B.4 WATCHED → LIVE

Price inside `dwell.band` of it — the dwell module's own calibrated band, not an invented point count — **and** the sequence machine in APPROACH or DWELL. Live levels take the top of the list and get the sentence.

### B.5 What the screen says when price walks into one

Three lines, entirely from fields the brain already publishes:

```
23,300  CE + tape wall  AGREE                    7 pts under · closing 8.4/min
        tests ||| last REJECT · 22.1M CE OI, +4.3M today · writers under water 6.20 [I] · dwell 4m
        above it: 41.2M forced covering to 23,400 [I] · stop zone 23,323 [I]
```

No verb, no side, no target of its own. It says where the fight is and what crossing it would cost.

### B.6 Broken, retired, remembered

When the sequence machine leaves a level through `_broke_through` (transition to RUN with a named target), the row moves to **BROKEN** and stays on screen for the rest of the session:

```
23,250 PE  broke 11:03 at 23,241 · peak 18.4M at 10:56, spot 23,309 · 62% unwound · target named 23,150
```

On the Field it becomes the ghost outline at peak thickness with live thickness inside — a front that gave up half its ground looks like one, and its high-water mark stays drawn. It is never deleted mid-session and never silently re-promoted: if price returns and the machine re-approaches, it re-enters WATCHED with `role: "flipped"` and its break history attached. A level that failed as resistance and is now tested as support is a different object, and the screen must not pretend otherwise.

---

## C. Breadth, continuously

Three different things wear this word here. One of them does not exist.

### C.1 Derivative breadth (`engine.py:1004`) — do not port the verdict

**What it measures.** Four direction signs summed to −4..+4 — futures z, ATM call premium change, ATM put premium change inverted, dealer regime lean — rendered as STRONG BULL / LEAN BULL / MIXED / LEAN BEAR / STRONG BEAR, damped to LEAN while PINNED. Three of those four are mechanically the same fact, the index moved, read through the index, its calls and its puts. Collinear by construction; only the regime lean is independent. It is not breadth — it is one instrument's direction counted three times, and it never reaches the new frame.

**Ruling: the verdict is not ported; two inputs are.** `regime` (PINNED / FLOOR / CEILING / AMPLIFIED-UP / AMPLIFIED-DOWN) and the PIN condition are real, independent and already computed; they land in the breadth object as named fields. The words STRONG BULL do not appear on this screen at any size. Its own author's comment records it printing STRONG BEAR at 12:54 on 2026-07-28 while price sat above VWAP on a 53M put wall. That ban is already paid for once.

### C.2 Positioning breadth — the one that matters

Her counterparty is the writer; this measures the writers, and every input is in memory now: `ChainState.minutes[HH:MM] = {spot, k:{strike:(ce_chg,pe_chg)}, px:{strike:(ce_ltp,pe_ltp)}}`, `ChainState.peak[(k,side)]`, and the futures bars' `oi`. Over a trailing window **W = 15 minutes** (three grid marks — long enough that one poll cannot move it, short enough to turn inside a leg):

| Field | What it says | Tag |
|---|---|---|
| `written_ce / unwound_ce / written_pe / unwound_pe` | how many strikes added vs shed OI on each book — four counts, never a ratio, never a word | [M] |
| `concentration_top1 / top3` | share of the day's absolute OI change in the largest strike and the top three — one wall or a curtain | [M] |
| `advancing / retreating` | across watched strikes: advancing = `unwound_frac < 0.10` with chg still rising; retreating = `unwound_frac ≥ 0.25`, where `unwound_frac = 1 − chg_now / peak_chg` from `ChainState.peak` | [M] |
| `pressed / bought` | of strikes that added OI this window, how many saw premium fall (writers pressing) vs rise (buyers building) — the axis `minutes.px` was stored for and nothing reads | [M] |
| `fut_oi_day / fut_oi_window` | futures OI change against futures price change, session and window | [M] |
| `regime`, `pinned` | ported from `engine.py`, as facts | [I] |
| `backfill_minutes` | how many minutes of the window were reconstructed | [M] |

Recomputed at chain pace (~10s) with the war map, published on the frame at frame pace. Backfilled minutes are counted and flagged, never blended silently.

**There is no direction field in this object** — not a word, not a sign, not a net vote. You cannot render a BULL/BEAR banner from data that does not contain one, and that is the enforcement.

### C.3 True market breadth — advances and declines — does not exist, and should not be built

`upstox_instruments.resolve` subscribes `idx_key`, `fut_key` and 17 strikes × 2 legs = 36 keys per index, ~105 across three. There is no equity key anywhere in this stack. Costed honestly:

- **Instruments:** NIFTY 50 + BANKNIFTY 12 + SENSEX 30, deduplicated ≈ 70 new keys → ~175 total. The `full` mode cap is 2000 (`upstox_feed.py` states it), so the cap is not the constraint.
- **Feed:** 70 liquid large caps in `full` mode is several times the current decode volume in the socket thread. The senses loop is p99 0.48 ms and HTTP p99 336 ms — neither is near a wall, but decode is not free, and the 2026-07-27 frozen-tape outage was a fetch, not logic.
- **Dump:** a second exchange slice (`NSE_EQ`) and cache file per index. One-time, cheap.
- **Rate limits:** none. This is socket, not REST.
- **The actual blocker:** index *membership* is not in the Upstox dump. No source of truth for "the NIFTY 50 constituents today" exists in this stack; it would be hardcoded and hand-maintained, and a stale list produces an advance/decline count that is quietly wrong in exactly the way nobody audits. That is a new input with a maintenance burden and no owner. That, not bandwidth, is the no.
- **What it adds over §C.2:** whether a move is broad or three heavyweights — which matters for trend continuation. Her trade is a mean reversion off a band inside a 3.5-hour window. It adds almost nothing to that decision and adds one more thing that can be wrong.

**Recommendation: do not build it.** Revisit only if, after 30 sessions of forward rows, the signal population's worst +6-bar excursions cluster on days when the index move was narrow — a question she can ask from free end-of-day constituent data, after the fact, without subscribing to one new instrument. If that clustering appears, build it then, and only then.

### C.4 How breadth may influence a signal: it may not

**Breadth is never a vote, never a gate, never a banner, never a sound.** The ballot's four votes are all local to the level in play; the day's weather does not join them. Breadth does exactly two things: it owns one quiet strip on the screen (§E), and when a signal is LIVE one caption may print under it naming what the fronts are doing on the side of the trade — *"PE fronts retreating (4 of 7 watched strikes) while you buy the lower band"* — because what her counterparty is doing at the moment of decision is a fact about the trade. It changes no state, casts no vote, suppresses no sound, and is built only from §C.2 counts.

The line: **breadth may caption a decision, never make one.** A breadth that quietly became a direction headline would be the doctrine broken, so the object is built with no direction in it.

---

## D. The contract

Three new pure modules — stdlib only, no I/O, no clock. `frame.py` composes and measures nothing.

- `signal.py` — `build(tape, bands_series, zone_states, walls_rows, sweeps, now_hhmm) -> (setup.signal, setup.votes)`
- `watch.py` — `build(walls_rows, spot, sigma, dwell, sequence, runways) -> walls.watch`
- `breadth.py` — `build(minutes, peaks, fut_bars, watched_strikes, regime, now_hhmm) -> breadth`

```json
"signal": {
  "state": "LIVE", "state_why": null,
  "side": "buy", "intent": "fade to VWAP", "not_a": null,
  "reached_at": "09:45", "reached_at_why": null, "reached_provisional": false,
  "visit_key": "buy@09:45", "visit_ordinal": 1, "in_window": true, "is_edge": true,
  "window": ["09:45", "13:15"],
  "armed_at": "09:45", "ref_px": 23196.0, "candles_left": 3, "candles_blind": false,
  "fired_at": "09:55", "seen_at": "10:03", "trigger_px": 23213.2,
  "target": 23327.4, "target_why": null,
  "falsifier": {"px": 23221.0, "rule": "a 5-minute close past 23,221 held for 3 bars",
                "frozen_at": "09:45", "drifted": false},
  "sound": "firm", "mute_why": null, "out_of_method": false, "tag": "M"
}
```
`state_why` is non-null exactly when `state` is `"PATA NAHI"`. `not_a` is `"outright short"` on every sell signal, `null` on buys. `mute_why` is non-null exactly when `sound` is `null`: `"visit two — not your edge"`, `"13:48 — outside 09:45–13:15"`, `"one measured vote, and it is OI"`. `"trigger bar rebuilt from REST; brain did not see it"` downgrades `sound` to `"soft"` rather than silencing it.

```json
"votes": {
  "n": 2, "of": 4, "measurable": 3, "threshold": 1, "passed": true, "passed_why": null,
  "items": [
    {"key":"wall","ok":true,"t":"09:45","p":23230.0,"src":"observed","why":null,"tag":"M",
     "label":"buy wall 23,230 built on the tap bar"},
    {"key":"event","ok":false,"t":null,"p":null,"src":null,"tag":"M","label":null,
     "why":"no initiative or absorption at the edge by the trigger"},
    {"key":"depth","ok":null,"t":null,"p":null,"src":null,"tag":"M","label":null,
     "why":"senses thread has no rows for 09:45–09:55"},
    {"key":"oi","ok":true,"t":"09:55","p":23256.3,"src":"observed","why":null,"tag":"I",
     "label":"fresh PE writing under the edge; PE writers above under water"}
  ]
}
```
`ok: true|false|null` — met, checked and not met, **could not check** with `why` printed. `src: "observed"|"backfill"|null`; a `backfill` vote does not count toward `n`.

```json
"walls": {"watch": {
  "rows": [{"p":23300.0,"kind":"CE","agree":"B 23300","d":-50.0,"live":true,
            "flags":["AGREE","SIZE","HELD","DWELL"],"tests":3,"last_outcome":"REJECT",
            "oi":22100000,"chg":4300000,"pain":6.20,"pain_tag":"I","conf":"session",
            "dwell_min":4,"closing_pts_min":8.4,"fuel":41200000,"fuel_tag":"I",
            "stop_zone":23323.0,"promoted_by":"agree","tag":"M"}],
  "broken": [{"p":23250.0,"kind":"PE","broke_at":"11:03","broke_spot":23241.0,
              "peak_oi":18400000,"peak_at":"10:56","peak_spot":23309.0,
              "unwound_frac":0.62,"target_named":23150.0,"role":null,"tag":"M"}],
  "cap": 8, "shown": 6, "why": null,
  "note": "where the fight is — none of these is an entry"
}}
```
`why` is non-null exactly when `rows` is empty, and distinguishes `"no ladder rows within 1.5σ"` (checked, found nothing) from `"warmap did not answer"` (could not check). Never one sentence for both.

```json
"breadth": {
  "window_min": 15, "t0": "12:45", "t1": "13:00",
  "written_ce": 3, "unwound_ce": 9, "written_pe": 11, "unwound_pe": 2,
  "strikes_seen": 17, "counts_why": null,
  "concentration_top1": 0.41, "concentration_top3": 0.68, "concentration_why": null,
  "advancing": 2, "retreating": 4, "fronts_seen": 7, "fronts_why": null,
  "pressed": 8, "bought": 3, "premium_why": null,
  "fut_oi_day": -412000, "fut_px_day": 75.0,
  "fut_oi_window": -88000, "fut_px_window": -12.5, "fut_why": null,
  "regime": "PINNED", "pinned": true, "regime_tag": "I", "regime_why": null,
  "backfill_minutes": 0, "tag": "M",
  "note": "counts of strikes, not a direction. calls written = a ceiling being built, or calls sold into strength before a roll."
}
```

**`GET /api/oihist?idx=`** serves the per-strike minute grid as it sits in memory — `{minutes, peak, backfill_marks}`. GET only. §C.2 and the Field's fronts rest on it; without it the fronts are drawn from one 10-second snapshot and the ghost outlines cannot exist.

---

## E. On the screen — the Field (verdict §5)

**The signal is not a card. It is a mark on the Field, captioned by a card.**

- **Reach ring** — hollow ring at `(reached_at, edge price)`; amber while live, ink once past; dashed while provisional.
- **Vote ticks** — filled triangles on the edge line at the bar each vote landed, apex into the pocket, lettered `W` `E` `D` 12 px above. The OI vote has no bar: a chip on the edge at the right reading `OI ✓ puts under · writers trapped`. (Approved design §E, kept verbatim.)
- **Heavy edge segment** — when LIVE, the edge from reach bar to trigger bar stroked heavy in the side's colour. A visit-two signal draws all of this in grey.
- **Falsifier** — a hairline at the frozen price with `frozen_at` in the gutter; when `drifted`, a second faint hairline at the live band and both numbers on the card.

**The SETUP card**, always visible: state word at **15 px** — a conclusion from a module that can say "don't know" does not get to be the largest thing on a trading screen; the ordinal in words on the first line whenever it is not one; candles-left as pips that stop moving when blind, with the blind sentence printed; the four ballot lines in order wall · event · depth · oi with `✓ · ~` and the reason inline for `~`; the frozen falsifier; `seen at` provenance when it applies.

**Watched levels** are the Field's left gutter rules — label, flags, tally ticks for tests. LIVE takes the `AT THIS LEVEL` card and the three lines of §B.5. BROKEN drop out of the gutter into grey and keep their ghost outline on the canvas.

**Breadth** is a **28 px strip along the bottom of the Field, on the same x axis**, because every breadth number is per-minute and the Field already owns time. Two 10 px rows: strikes written up / unwound down, CE row and PE row, one tick per minute; current counts print at the right edge. It reads as a coarser second battlefield under the real one, which is what it is. Its permanent caption is the `note` field above.

**Loudness, in order, never violated:** distance-to-zone chip 34 px › the Field › signal state word 15 px › watched-level labels 12 px › breadth strip 10 px. Breadth is the quietest thing on the screen that is still visible. Never breadth above a watched level, never a watched level above the signal, never the state word above the distance, never anything above the Field. Nothing animates; rows never re-sort while a signal is LIVE.

**Sounds:** the two of §A.8. That is the complete list.

---

## F. Measured versus judgement

**Measured — her method, or the tape's own arithmetic:** the bands, σ, z, VWAP and the pocket edges; the touch that latches REACH, from the bar's own printed low/high; the two-candle rule, the reference, the 10-bar window and the trigger close (`run_states`, unchanged); the wall, event and depth votes; tests, last outcome, dwell minutes, OI and its change, peak OI and its minute, premium levels; every count in §C.2; the excursions at 1/3/6 bars and 90/180 minutes and the control population.

**Judgement calls — mine, not hers, each with a kill:**

| Call | Chosen because | Kill |
|---|---|---|
| T = 1 measured vote | the six-day bucket table | §A.10 ballot clock, n = 30 |
| OI never alone | true on 20 of 27 — background, not a filter | folded into the per-vote clock |
| window 09:45–13:15 | her stated edge | §A.10 window clock, n = 30 |
| a visit ends 0.5σ back inside | a re-entry rule was needed; no evidence exists either way | if ordinals disagree with her own count on 10 sessions, it goes |
| watch radius 1.5σ, cap 8 | σ scales with the day; 8 is a list, 9 is a table | if she scrolls the list, the cap is wrong |
| the six danger flags | each is a fact the brain already holds | any flag that never varies across 30 sessions is deleted |
| retreating at `unwound_frac ≥ 0.25` | a quarter given back is visible on the canvas | tune against the ghost outlines after 10 sessions |
| breadth window 15 minutes | three grid marks; one poll cannot move it | if it flips more than twice an hour it is too short |
| pain, fuel, stop zone, regime | inherited `[I]` from `trapped_inventory` / `hunt` / `engine` | they carry their own |

---

## G. Build order

1. **`reached_at` latched, `visit_key` off `arm.first_t`, `visit_ordinal`, `in_window`.** No ballot, no endpoint. *Proves:* replaying the six cached sessions, `reached_at` equals the study's **First touch** column on all 49 visits, and a setup with a re-arm produces exactly one visit key.
2. **`signal.py`: the ballot, T = 1, OI-never-alone, backfill excluded.** *Proves:* the four vote columns reproduce the study's W / I / S / O per visit on the same six days, and a `null` vote never moves `n`.
3. **States, the frozen falsifier, blind-safe candles, the two sounds, the record row.** *Proves:* on a replayed session at most two sounds per index fire, none outside 09:45–13:15, none on visit two, and a signal whose trigger bar was rebuilt sounds soft and carries `seen_at`.
4. **`took` / `skipped` and the third record column.** *Proves:* a full session's rows carry the column; unanswered rows render `—` and are counted in the record header.
5. **`watch.py`.** *Proves:* the list never exceeds 8, every row names `promoted_by`, every broken level stays on screen with its peak and break minute.
6. **`/api/oihist` + `breadth.py`.** *Proves:* counts recompute identically from the served grid and from memory; backfilled minutes are counted and flagged; no field holds a direction.
7. **The Field marks** — rings, ticks, heavy segment, ghost outlines, breadth strip. *Proves:* at 1920 **and at 960** the Field, the spot chip, the watch gutter and the breadth strip are all on screen. Both prior designs deleted the battlefield at 960 by different bugs; this one is checked at 960 first.

Steps 1–3 are the signal. 4 is the only thing that makes the record legible a month from now. 5–7 can slip a week without changing a decision.

---

## H. The honest risks

1. **The watch list becomes an entry list.** Four flags on a wall reads like a setup. *Guardrail:* watched rows carry no side, no direction and no target of their own; `signal.py`'s signature does not accept `walls.rows`; the permanent header says *none of these is an entry*. If she ever reports taking a trade off a watched level, the flags come off the screen.
2. **One vote is a low bar and the bell goes stale.** 28 of 35 triggered visits in the study had ≥ 1 vote. *Guardrail:* the sound is gated on `is_edge`, not the ballot — at most two signals per index per session can sound, by construction. The threshold controls what is *drawn*; the window controls what is *heard*.
3. **The falsifier she was shown is not the one being checked.** *Guardrail:* frozen at the arm bar, prints `frozen_at`, prints both numbers once the live band drifts past 0.25σ.
4. **A signal fires blind and she acts on a stale bell.** *Guardrail:* candles are not counted blind; a trigger the brain did not see live sounds soft, never firm, and `fired_at` and `seen_at` are two separate printed facts.
5. **Breadth becomes a direction read anyway** — *"CE written 9, unwound 2"* will be read as bearish. *Guardrail:* no direction field exists in the object; the permanent caption names both readings each count admits; the strip is the quietest visible element on the screen.
6. **The record teaches nothing because took/skipped is never pressed.** *Guardrail:* the row is written regardless, unanswered renders `—`, the header counts unanswered, and the column is deleted at 20 sessions if most rows are blank. A half-kept promise on a record is worse than no column.
7. **The screen makes visit two attractive** because it still draws beautifully. *Guardrail:* grey, silent, `visit two — not your edge` as the card's first line, rows tagged `out_of_method` so they can never pool with the edge population.
8. **Backfill inflates the ballot on a late start.** *Guardrail:* `src: "backfill"` votes are shown and do not count toward T. Only what the brain watched happen can ring a bell.
9. **Four votes, eight watched levels and a breadth strip is more screen than a fade off a band needs.** The real failure mode of this layer is that it is interesting. *Guardrail:* every kill condition above deletes rather than tunes, and each carries a number and a session count set before the first row is written. If all of them fire, what is left is the distance to the zone, the reach ring, the trigger and the falsifier — her method with nothing added, which is an acceptable place to land.
