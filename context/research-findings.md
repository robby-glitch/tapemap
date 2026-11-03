# Research findings — what has been scored, and what died

**Point a new session here for anything about "does X work".** `HANDOFF.md` §6
carries one-line verdicts; the evidence, the exact rule tested and the
failure modes live here. Every scorer named below is a standalone CLI in the
repo root and re-runs offline from `data/backtest/`.

Last updated: 2026-08-04.

---

## 1. The one surviving edge

**NIFTY (and SENSEX) — d3 band reversal, intraday, buy-side only.**

> ### ⚠️ VOID as of 2026-08-05 — measured on the wrong trigger
>
> Every number in this section describes a **one-candle** rule: a bar pierces
> d3 *and the same bar closes back above it*, enter at that close. Asked
> directly on 2026-08-05, the operator described a **two-candle** rule: a bar
> **touches** d3 (no close-back needed), and entry comes when a **later** bar
> closes above **that bar's high**. Entry is therefore later and higher.
>
> So **72% / +21.0 pts / −20.7 adverse swing are VOID — not disproven.**
> Correctly measured, wrong instrument. The same thing that happened to
> `confirm_score` (HANDOFF §6b). `band_rotation._trigger` still implements the
> old rule, so the pills on the chart do not mark the operator's entries.
>
> The real rule is pre-registered in **§5c** and must be scored before any of
> it is trusted or drawn. Keep this section as the record of what was measured.

The rule, as the data supports it (**the OLD, one-candle trigger — see the
VOID notice above**):

> After **09:30**, a 3-min candle's low pierces **d3 (−3σ of session VWAP)**
> and the *same candle closes back above it*. Enter at that close. Stop 20 pts
> below the band. **Touch nothing until VWAP.** Past VWAP, trail band-to-band;
> from +2σ, 15 pts under the high. Flat by 15:15.

| measure | value | source |
|---|---|---|
| hit rate @30m | **72%** (n=18, first-of-run post-09:25) | `rotation_score.py` |
| median move @30m | **+21.0 pts** (≈ +0.085%) | same |
| control (any bar, same horizon) | +0.3 pts, 50% | same |
| with 09:30 gate | 73%, med +23.7 (n=15) | ad-hoc, 2026-08-04 |
| typical adverse swing before it works | **−20.7 pts** | `trail_score.py` |

**Frequency ~1–2 per week.** SENSEX agrees (n=4, 100%). BANKNIFTY inverts.

### What management actually to use — measured, counter-intuitive

| management | mean | hit |
|---|---|---|
| no stop, fixed 30-min exit | +9.3 | 72% |
| **hold stop till VWAP, then trail** | **+4.8** | **56%** |
| band-to-band trail from entry | +2.5 | 44% |
| breakeven-if-narrow, then trail (operator's first description) | **−3.9** | 22% |

Two leaks, both measured: **moving to breakeven costs ~13 pts/trade** (NIFTY
re-tests the entry zone before rotating — 6 of 18 winners became scratches),
and **trailing below VWAP costs ~7 pts/trade** (compressed σ puts two rungs
inside one 3-min bar and parks the stop ~8 pts from price). The trail is
correct *above* VWAP: the 5 runners that reached u1+ kept +19 to +44.

The residual gap to the no-stop number is the 20-pt stop itself sitting
exactly at the typical adverse swing. Widening it is a **risk decision owed
by the operator** — deliberately not grid-searched.

---

## 1b. THE ZONE — what the operator has always traded (stated 2026-08-14)

**Read this before §5c, §5d or §5e. All three register a LINE. The operator
trades a ZONE. They are testing the wrong instrument — the same failure that
made §1 VOID, and it is repo-wide, not a detail.**

### The rule, in the operator's words

> "it was always a zone as you can see the shadings between the vwap bands the
> upper sky blue and the lower sky blue is the zones if we looking for. and
> thats my rule"
>
> "the lower band is my zone to look for buy signals and the upper band is
> where i look for sell if market condition is right"

### What the zone is, read off the code that draws it

`ui-v2/src/proto/protoRibbon.ts:210-211` (verbatim from
`LevelsOverlay.ts:1169-1173`) fills exactly two azure rings —
`BAND_RGB.outer = '0,168,232'`, Kite's azure, the "sky blue":

```
ring('u3', 'u2', BAND_RGB.outer)   // UPPER zone = u2 -> u3   SELL side
ring('d2', 'd3', BAND_RGB.outer)   // LOWER zone = d3 -> d2   BUY  side
```

So the zone is the **2σ→3σ ring on each side**, and nothing else:

| zone | span | side | colour |
|---|---|---|---|
| lower azure | **d2 → d3** | BUY | `0,168,232` |
| upper azure | **u2 → u3** | SELL | `0,168,232` |
| 1σ→2σ ring | d1→d2 / u1→u2 | *not a zone* | sage `143,188,143` |
| ±1σ core | d1→u1 | *not a zone* | dark red `139,26,26` |

**Entering the zone means the bar reached d2 (or u2), not d3 (or u3).** d3 is
the far edge of the zone, not the trigger.

### The correction this forces — the tool was wrong twice, on the record

Sessions on **2026-08-11 and 2026-08-13** each spent a round of argument
treating "price entered the blue but the low was 6–10 pts short of d3" as an
operator misreading. It was not. The operator was reading their own zone
correctly; the tool was measuring a line nobody trades. That mistake was then
written into memory as "the d2/d3 reading trap" **and acted on**: the chart was
changed to draw d3/u3 as solid 2.5px brass lines with "no other band edge
drawn", which removes the near edge of the very zone being traded.

**Do not repeat this.** A low that reaches d2 and turns is a zone event. It is
not a near-miss, and it is not the operator being imprecise.

### What this invalidates, and what it does not

- **§5c** ("d3 only", post-09:25 two-candle) — wrong instrument. Not disproven;
  **unmeasured**, exactly like §1.
- **§5d** ("u3 only, never u2") — same, on the sell side.
- **§5e / §5f** — inherit it, being the live forward test of the above.
- **`trigger_log.py`** logs `rule: "5c"` rows on the d3/u3 line. Every row is
  still a true record of *that* trigger; none of them is a record of the zone
  rule. The 20 rows at 2026-08-14 do not begin a zone dataset.
- **`band_rotation.detect_index_run`** is the line detector. The `rotation`
  layer the proto tab draws already fires on **d2, d3 and u3** — which is why
  the proto tab showed a good 09:30 d2 BUY on 2026-08-14 that `trigger_log`
  could not see (0 rows that day).

**Their bodies are deliberately NOT edited.** §5d voids itself if edited after
a result is known; the pre-registrations stay byte-identical and this section
carries the correction instead.

### PRE-REGISTERED — the zone rule, UNTESTED

Registered per §5, **before** any scoring run. **Nothing here is a result.**

1. **ARM** — a bar whose **low enters the lower azure** (low ≤ **d2**) arms a
   BUY; a bar whose **high enters the upper azure** (high ≥ **u2**) arms a
   SELL. That bar is the reference.
2. **RE-ARM** — a later bar printing a new lower low (BUY) / higher high
   (SELL) replaces the reference. Falling lows collapse into one setup.
3. **TRIGGER, STOP, MANAGE, RE-FIRE, EXPIRY** — carried over from §5c
   unchanged, pending the operator's answer below.
4. **GATE** — 09:25, carried over from §5c, pending the same.

**Open — the operator's to answer, not to be assumed:**

- **a.** Is the trigger the §5c two-candle close-beyond-the-reference, or the
  one-candle reclaim the proto tab currently draws?
- **b.** Where is the stop, now that the arm is at d2? `d3 − 20` (far edge, as
  §5c) or `d2 − 20` (the arming edge)? These are ~11 pts apart on NIFTY.
- **c.** What is *"if market condition is right"* — the compression/trap test
  `band_rotation` already computes, or a separate read?
- **d.** Does the 09:25 gate survive? It exists because σ needs ~10 readings to
  rank a width; the 2026-08-14 09:30 signal passed the clock gate and still
  failed the width test ("only 5 index band readings").

**Falsifier (committed in advance):** hit rate at the operator's horizon at or
below the unconditional control, **or** the zone result collapsing to the line
result once entries that reached d3 anyway are removed — which would mean the
zone adds nothing over §5c and the extra fires are noise.

**Hazard:** the zone fires **more often** than the line by construction. More
signals is not evidence; it is the thing that must be paid for in hit rate.

### OBSERVATION — 2026-08-14, the first live day after registering it (n=1, UNSCORED)

**This is not a result.** One session, ten signals, no outcome scored, and the
pattern below was spotted *after* the fact. Recorded now only so the day is not
reconstructed from memory later — §5's stop rule still binds.

**The line rule saw nothing. The zone rule saw the whole day.**

NIFTY's lowest low was **24370.0** (11:36); d3 sat at **~24357** and was
**never touched on the BUY side**, so §5c logged **zero BUY signals** all day
while the zone produced six.

> **Corrected at 15:00.** An earlier draft of this section said
> `trigger_log.jsonl` wrote **0 rows** for 2026-08-14. That was checked at
> 09:57 and is **false for the full day**: the file gained **7 rows** in the
> afternoon — 5 arms and 2 entries, **all SELL u3** (NIFTY arms 13:45/13:57/
> 14:00 and entry 14:06 @ 24457.2; SENSEX arm 13:45/14:00 and entry 14:06 @
> 78300.5). The buy-side claim stands; the "0 rows" claim did not survive the
> session. **Do not quote a same-day log count as final before the close** —
> `eod_capture` exists precisely because the record is still being written.
>
> Unresolved: the NIFTY 14:00 arm logs `level 24482.1`, but that bar's high was
> **24477.0** — below its own u3. Either the arm was written off a forming bar
> or the logged `level` is not the level that armed it. **Check before any of
> these rows is scored.**

Over the same hour the zone produced six entries:

| bar | low | d2 | close | vs d2 |
|---|---|---|---|---|
| 10:30 | 24376.1 | 24378.7 | 24377.9 | −0.8 |
| 10:33 | 24375.0 | 24376.8 | 24383.9 | +7.1 |
| 11:00 | 24374.4 | 24374.8 | 24380.4 | +5.6 |
| 11:09 | 24372.0 | 24373.5 | 24385.1 | +11.6 |
| 11:12 | 24371.7 | 24372.6 | 24379.0 | +6.4 |
| 11:30 | 24370.2 | 24370.6 | 24376.0 | +5.4 |

All six reclaimed. Price then broke up and reached **24416.5** at 12:21 —
**+40.5** from the last entry's close, +31 to +40 from every one of the six.

**The afternoon inverted the result on the same rule.** Between 13:42 and 14:03
the upper zone was tagged four times (u2 at 13:42/13:54, u3 at 13:45/13:48/13:51)
and **none rejected**; price walked up the outside of the band, closing at or
near its high repeatedly, and the band outran it (u3 24467.3 → 24486.0). It
ended not as a band rejection but as an engine-flagged **BULL TRAP at 14:04,
24470.6**, after which price closed back under u2 at 14:06.

**The split — a HYPOTHESIS, to be pre-registered before it is tested:**

| half | 30m range pctile | tags | outcome |
|---|---|---|---|
| morning, d2 | p22 → p62 (**compressed**) | 6 | all rejected, +40 into the break |
| afternoon, u2/u3 | p94 → p100 (**expanding**) | 4 | none rejected, walked through |

`trap` returned **SUSPECT on all ten** and discriminated nothing. `rng_r` —
already in the payload — separated the two halves cleanly. That is a candidate
mechanical answer to open question **(c)**, *"if market condition is right"*,
and it is the same thing §7 names as unmeasured: rejecting the band vs walking
along it. **Do not encode it from this day.** Register it, then score it.

**Hazards on this observation, recorded before anyone quotes it:**

- Post-hoc. The compression/expansion split was noticed after both halves were
  known — exactly the move §5 exists to stop.
- The six morning entries may be **one** setup, not six: §1b's re-arm clause
  collapses falling lows into a single reference, and they came inside 60
  minutes on a descending d2.
- Gamma was `AMPLIFIED-DOWN` across all six morning entries and they worked
  anyway; it was `AMPLIFIED-UP` in the afternoon and the fade failed. Read
  literally, the gamma regime was **anti-predictive** both times. n=1.

**Tooling lesson, cost two wrong reads on the day:** the backend computes
`rotation` on the **forming** bar, and a forming bar's close moves. 10:33
reported a reclaim that evaporated; 13:51 reported a close 9.6 below u3 that
finished 2.9 below. Only judge a closed bar.

**VERIFIED against Kite** (2026-08-14 14:38, via Kite MCP —
`NFO:NIFTY26AUGFUT` token 14866434 and `NSE:NIFTY 50` token 256265, both
stamped `14:37:59+05:30`). This is the leg-pivot cross-check HANDOFF §6 lists
as never done, run on the FUT tape rather than the option legs:

| | TapeMap | Kite | diff |
|---|---|---|---|
| index | 24368.75 | 24367.80 | 0.95 |
| basis | 81.25 | 82.20 | 0.95 |
| **implied future** | **24450.00** | **24450.00** | **0.00** |
| day fut O/H/L | 24452.0 / 24477.0 / 24370.0 | identical | 0.00 |

All six zone entries match Kite exactly on close; five of six exactly on low
(11:12 differs 0.1, both sides of d2, signal unaffected). **The basis moved
54.6 → 81.25 intraday and TapeMap tracked it** — the drift was real, not an
error, and the levels are placed correctly.

**One data-quality note, unresolved.** Of 22 bars compared (10:27–11:30), 17
matched exactly and 5 differed — **four of the five with TapeMap printing the
LOWER low** (10:39 −3.0, 11:27 −1.4, 11:06 −0.3, 11:12 −0.1; 11:18 +0.4).
None changed a signal today. The direction is the concerning one: a too-low low
is precisely what manufactures a **false BUY zone entry**. n=5 is not enough to
call it systematic, and tick-aggregation vs exchange-consolidated bars is the
likely cause. **Re-check this on the next cross-check before trusting a
marginal d2 tag** — a 0.1-point entry like 11:12 is inside this error bar.

---

## 1c. THE BANDS DO NOT MATCH THE OPERATOR'S CHART (measured 2026-08-14)

**Upstream of everything else in this file.** Every signal, every backtest and
every §1b entry is derived from σ bands. Measured against the operator's own
Kite export today, **TapeMap's σ is systematically WIDER than the σ on their
screen**, and the gap grows through the session.

Source: operator's Kite CSV export of `NIFTY AUG FUT`, 3-min, 2026-08-14
(columns `VWAP`, `SDVWAP2±`, `SDVWAP3±`), against the live `/api/data` payload
for the same bars.

| bar | σ Kite | σ TapeMap | TapeMap/Kite | u3 gap |
|---|---|---|---|---|
| 10:30 | 10.780 | 11.027 | 1.023 | −0.03 |
| 11:30 | 12.037 | 12.683 | 1.054 | +2.28 |
| 13:45 | 17.610 | 19.087 | **1.084** | +5.79 |
| 14:00 | 23.673 | 24.847 | 1.050 | +5.22 |
| 14:06 | 24.623 | 25.797 | 1.048 | +5.30 |

VWAP diverges too — Kite 24405.86 vs TapeMap 24407.56 at 14:00 (**+1.70**).

### Why this matters: the error can only ever produce FALSE NEGATIVES

A wider σ pushes u2/u3 **up** and d2/d3 **down** — both **further from price**.
So TapeMap can never fire a signal the operator's chart does not show; it can
only **fail to fire ones it does**. Two confirmed misses on 2026-08-14:

- **14:00 SELL.** High 24477.00 vs Kite u3 **24476.88** → poked through by 0.12
  and closed 24475.00 back below: a textbook tag-and-reject on the operator's
  screen. TapeMap's u3 was **24482.10** — the high fell **5.10 short**, so
  nothing fired. *This is the bar the operator circled and asked about.*
- **11:36 BUY.** Low 24370.00 vs Kite d2 **24370.81** → inside the blue, closed
  24379.40 back above. TapeMap's d2 was **24369.75** — 0.25 short, no signal.

### CAUSE PROVEN 2026-08-15 — granularity, and the operator has ACCEPTED it

**The "seeding difference" guess is WRONG.** It was the obvious suspect and it
was not the cause. Kept as a caution: the plausible mechanism was not the real
one, and only the measurement separated them.

Experiment: rebuild σ four ways from `data/backtest/fut_2026-08-14.json`
(379 raw 1-minute bars) and score each against the operator's Kite CSV.

| bar | Kite σ | **A** 1m + running | **B** 3m + running | **C** 3m + true var | A/K | B/K |
|---|---|---|---|---|---|---|
| 09:15 | 0.000 | 8.752 | **0.000** | 0.000 | — | — |
| 10:30 | 10.780 | 11.025 | 9.857 | 11.039 | 1.023 | 0.914 |
| 13:45 | 17.610 | 19.088 | **17.633** | 18.371 | 1.084 | **1.001** |
| 14:00 | 23.673 | 24.849 | **23.731** | 24.348 | 1.050 | **1.002** |
| 14:06 | 24.623 | 25.797 | **24.685** | 25.278 | 1.048 | **1.003** |

**A reproduces the shipped ratios exactly** (1.023 / 1.084 / 1.050 / 1.048 —
the same numbers measured above), which validates the harness.

**The cause is GRANULARITY.** `contract_bars` computes bands on the **1-minute**
series and `_fold` only SAMPLES them into the display bucket — deliberate; the
comment at `contract_bars.py:218` calls it interval invariance. Kite computes
SDVWAP on the **3-minute** series. The extra intrabar observations carry
variance the 3-minute bars smooth away.

**The variance recurrence is NOT at fault.** Column C — the "true" weighted
variance around the final VWAP instead of `_Vwap`'s running one — is *worse*
(1.011–1.043). `cvar += v*(tp-vwap_running)**2` at `contract_bars.py:173` is
right. **Do not "fix" it.**

**Residuals granularity does NOT explain**, left open:
- B is off **8.6% at 10:30** and 2.7% at 11:30 while near-exact after 13:45.
- **VWAP is still 1.83 out** on 3-minute bars (Kite 24405.86 vs 24407.69).
  Granularity cannot explain this at all — suspect a volume mismatch.

### DECIDED 2026-08-15 — not fixing it

The operator's call, verbatim: *"thats not required the difference is small we
can manage with out it."* What supports it: the error is
**false-negative-only**, bounded at ~5 pts at 3σ, and the fix would make bands
**shift when the interval changes** — Kite's behaviour, but not what
`contract_bars.py:218` currently guarantees.

**So the bands stay wider than the chart, knowingly.** The consequence is
permanent and must be repeated wherever counts are quoted: **every TapeMap
signal count is a FLOOR, not a total.** If the operator says a touch fired on
their screen and not in the tool, that is expected behaviour, not a new bug.

**A fix, if it is ever wanted**, is one line: `live.py:522` reads
`resample(vwap_bands(one), interval)`; column B is `vwap_bands(resample(one,
interval))`. It **contradicts HANDOFF §6's** recorded "band pipeline order
✅ 0.972; reversed order 0.948" — one of those two measurements is wrong, and
that must be settled before the swap is trusted.

### What this downgrades

**HANDOFF §6's "σ bands match the operator's Kite export — ✅ VWAP 0.078 pts
median, ±3σ ratio 0.981" no longer holds.** Today measures ratio **1.023–1.084**
and a VWAP gap up to **1.70**. Whatever session that ✅ was earned on, it is not
today's. The row is downgraded there.

**§1b's six morning entries survive but the count is a FLOOR, not a total.**
They cleared the *wider* band, so they clear the operator's narrower one too —
but there were at least seven on the operator's chart (11:36 is the known
extra). Any frequency claim from 2026-08-14 is a lower bound.

---

## 1d. PRE-REGISTERED — THE FADE GATE (written 2026-09-23 00:40, before any code, UNTESTED)

Registered **before** the gate exists, per §5. **Nothing below is a result.**

### Why this exists

§1b left one clause of the operator's own rule unimplemented for five weeks:
*"the upper band is where i look for sell **if market condition is right**"*.
Open question **(c)** asked what that clause means. On **2026-09-22** she
answered it, in her own words, after the tool named the wrong strike:

> "hamesha read nearest ATM pe rehni chahiye. 23700 PE writers are irrelevant
> because wahan pe hedging ke liye positions banate hain... Hamesha check karo
> **the strike with most of OI and second best on both sides**, and always
> check **which side stops first increasing their positions and then
> unwinding**."

**What the day showed.** NIFTY fell 23475 → 23370 between 10:20 and 10:50.
The near-ATM put front **PE 23400 peaked at +234.2L at 10:19 and was at
+69.1L by 11:00** — one minute before the fall began, the side that would have
had to defend the lower band stopped adding and began giving inventory back.
Over that fall the zone machine armed **BUY ten times** (10:30, 10:33, 10:36,
10:39, 10:42, 11:45, 11:54, 13:51, 13:54, 14:00), twice with the engine
simultaneously printing **"NO FADE at 23360 — negative gamma; continuation
only"** (11:45 and 13:51). Two modules, one minute, opposite instructions.

### The rule, exactly

A **FADE** arm or entry (the zone's BUY at d2/d3, or its SELL at u2/u3) is
**LEGAL** only when both hold at that bar:

1. **The defending front is still building.** For a BUY fade that is the **PE**
   front; for a SELL fade the **CE** front. "The front" is the strike with the
   **largest session-peak OI on that side among the nine strikes nearest
   spot**; "building" means its 15-minute OI-change slope is **rising** and it
   is not stalled (thresholds below).

   > **Corrected 2026-09-23 01:10, before any row was logged against it.** An
   > earlier draft of this line read "neither stalled nor off its own peak",
   > which describes a **latch** — once broken, broken for the session. The
   > implementation reads the **current direction** instead, so a front that
   > ran and then came back counts as building again. That is the deliberate
   > choice: writers who return are defending again, and a session-long latch
   > would mark a fade illegal for six hours on the strength of one ten-minute
   > flush. The looser reading is also the harder test for the gate, since it
   > lets more fades through. Recorded rather than silently reconciled. The
   > face must not say "still building" about a front far under its peak; it
   > names the distance instead.
2. **The engine has not vetoed it.** No `NO FADE` play for that side on the
   same bar.

Anything else is **ILLEGAL**, and a missing input is **PATA NAHI**, never legal.

**Parameters, fixed now, not to be grid-searched (§5c's rule):** nine nearest
strikes · top **2** per side by session-peak OI · **UNWIND** at 15 % off the
front's own peak with a falling 15-minute slope · **STALL** at a 15-minute
slope inside ±5 % of that peak · otherwise **BUILDING**. Ranking is by **peak**
OI, not current, deliberately: a front that has already given back 70 % is the
one being hunted, and ranking by current OI would drop it out of sight exactly
when it matters.

### What is NOT being changed, and this is the load-bearing part

**The forward log keeps every row it would have written.** No arm and no entry
is suppressed, renamed or dropped. The gate is stamped **alongside** each row
as a new `gate` field and rendered on the face. §5c's and §1b's running
populations are therefore untouched, and after N sessions the question "what
would obeying the gate have cost and saved" is answerable **from rows logged
forward**, with no cache re-cut. A gate that edited the log would destroy the
only evidence that could judge it.

### Predictions, committed in advance

1. It marks **illegal** a large minority of fade arms — most of them clustered
   inside single directional legs, not scattered.
2. On a trending day it marks **nearly every** fade arm illegal; on a pinned
   day **nearly none**. If it fires evenly across both, it is reading noise.
3. The arms it marks illegal have a **worse MAE distribution** than the ones it
   leaves legal.

**Falsifier (committed in advance):** the illegal set's MAE is no worse than
the legal set's, **or** the gate marks illegal fewer than 1 in 10 fade arms
over 10 sessions (it would then be a rule that never binds), **or** the result
collapses once the single worst leg is removed (§5 lesson 2).

**Hazards recorded now.** The gate can only make the tool refuse more; refusing
more is not evidence of anything by itself, and "fewer signals" must never be
reported as an improvement. The compression/trap filter is the standing warning
here: it was pre-registered too and turned out **actively harmful**, selecting
losers in three separate datasets. This one dies the same way if it fails.

**Still open, and NOT answered by this section** (§1b's own list): whether the
trigger is the two-candle close or the one-candle reclaim **(a)**, and whether
**u2 SELL survives at all** given that selling any upper band is dead on five
datasets. Both are the operator's to answer, and this gate is deliberately
written so it does not depend on either.

---

## 1e. PRE-REGISTERED — THE HOLD / FOLD WINDOW AND THE SIDE READ (signed 2026-09-25 01:42, before any code, UNTESTED)

**The full text is `docs/hold/PREREG-merged.md` rev 4** (written 2026-09-25
01:37 IST). This section is its anchor. **sha256 at signing:
`e7f50391da94a6a14b76ccc6dff5bc993c1b306859baaee8a78e36a7744709d0`.**
- Any later edit to that file is a new revision with its own change-log
  entry and a new hash here, never a silent change.
- **Nothing in it is a result.**

**Signed by the operator** when asked to sign it for building after the
close. Her words: *"build it we have enough time till tommorrow open and i
might not trade at all tommorrow so build it and than let me know . but this
sesiion is very long . so do it new session"*.

**Why it exists.** Her own diagnosis: *"identifying direction is never my
problem but holding a trade it closing too early on my trade getting panicked
with even 1 single red candle or holding a bad trade in fomo"*. The evidence
is her 2026-09-24 SENSEX put trades against what the tool's data said at each
exit (DEFERRED §0j.11).

**What it registers, in brief:**
- a floating, per-trade HOLD / WATCH / FOLD / PATA NAHI window, for buyers
  and writers;
- a price line as the hard FOLD, the nearer-front OI ledger, strict order
  flow and a 5m / 15m / 1h trend vote;
- her quiet clock as a FOLD, with its own kill clause;
- the entry check ("you entered into a broken setup");
- a CALLS / PUTS / no-side read;
- all parameters inherited;
- two write-once forward logs in `data/hold/`;
- a falsifier judged over 30 sessions (at least 10), in % of premium, that
  must survive removing the best day.

It is designed by two models blind (Fable 5.1 base, Opus 5.5 OI read, clock
and absences), then cross-reviewed. Opus reviewed it three times, and its
last blocker was fixed in rev 4.

**It gates nothing else.** It never feeds `setup.gate`, the zone machine or
`trigger_log`. It shows DRAFT until its falsifier is judged. There is no order
path.

**REV 5 (OPTION B), signed 2026-09-25 19:40 IST, on her delegation.** Her words:
*"but i dont get it or capable enough to answer as a trader you think is best take that for now"*. The full text is `docs/hold/PREREG-rev5.md`, **sha256
`06a54cee595688abe4c90a8f5a56930d2a73e2a752861db2e62cbabd038b5189`**. It amends
rev 4, which stays as it was, hash above.
- **Why a new revision:** `docs/hold/REVIEW-2026-09-25.md` P0-1. Her 12:01 CE was
  folded at 12:02 on a 1-minute close 1.4 pts through a line that sat 2 pts from
  her entry.
- **The line break (option B):** a 3-minute index close beyond L by more than
  one median 1-minute candle.
  - The candle is measured over 15 finished minutes when L is set or trailed,
    then frozen and printed as a level.
  - On a trail, the level never moves away from price.
  - Until the candle is read, the buffer is 0; that fallback is named.
- **Other changes:**
  - after a FOLD, the STOP shows the line that broke;
  - the PAYERS row's precedence;
  - copy.
- **Clause 7-B can kill it on forward rows.**
- **Who chose B:** Claude (Opus 5.5), on principle, on her delegation. The line
  separates a break from noise; option A only moves the timing. Option A is kept
  as the text not chosen.
- **Review:** three adversarial passes (`docs/hold/REV5-VALIDATE2-REVIEW.md`);
  option B was SIGNABLE.
- "For now": she may revisit.
- **PLAN rev 3a** (a pointer to this break, no PLAN rule moves): `docs/hold/PLAN-PREREG.md` sha256
  `b7549d79b6e78ff93b8b5c9e982db43c599ebda83e0dfe3e81dac0a57acef0c4`.
- **Copy amendment 1 to rev 5, signed 2026-09-26 22:37** (her words: *"fix the two backwards seller sentences in the
  window"*): the writer's own-side sentences of §D item 7″ now read by her direction ("spot moving against you — a
  squeeze" / "winners cashing in — spot moving your way"), not the strike. Copy only; no rule moves.
  `docs/hold/PREREG-rev5-COPY-1.md` sha256 `735c40078a12f80021a5fe39590b79e555914cf17c5f1f7430f6202f380f9631`.

---

## 1f. PRE-REGISTERED — THE PLAN: STOP · NEXT RUNG · ROOM (signed 2026-09-25 09:31, before any code, UNTESTED)

**The full text is `docs/hold/PLAN-PREREG.md` rev 2a.** This section is its
anchor. **sha256 at signing:
`a0295c202697679f14fd59aa157813bdbf74cc0f8b1fbff6da17cea5a1e7158b`.**
- Any later edit to that file is a new revision with its own change-log
  entry and a new hash here, never a silent change.
- **Nothing in it is a result.**

**Signed by the operator,** her word: *"sign"*.

**Her request:** *"think for yourself building a tool to tell you if you can
hold your trade target you can aim for stoploss one should look for"*.

**Her two decisions:** *"again depends on market leave the size to me"*. So:
- the plan never sizes, never says "book" or "exit";
- it prints the line and the window's word side by side, never merged.

**What it registers, in brief.** It sits beside §1e's window and changes none
of its rules.
- **STOP:** the window's line, in index points, with the premium at risk [I]
  from the broker's Δ, Γ (a buyer −½Γ clamped 0…premium; a writer +½Γ).
- **NEXT RUNG:** the nearest sized payers'-side front strictly beyond the
  index in her direction; else the session extreme; else "price discovery".
  It always carries DEFENDED / GIVING WAY / STALLED, says whose favour that
  is, and shows the raw §1d state.
- **ROOM:** points to the rung and to the stop, never a ratio as odds.
- **A touch:** one per (trade, strike, side), with its own write-once
  `rung_touch` row. `next15` there is the maximum favourable index excursion
  over 15 finished minutes, as §1e's extremum.
- **P1:** GIVING WAY touches are followed by larger excursions than DEFENDED
  touches. It is judged at at least 15 of each and at least 10 sessions, by 30
  sessions at the latest, and must survive removing the best day. If it fails,
  the words are deleted and STOP and ROOM stay as display.
- **Parameters:** all inherited; no new number.

Drafted by Opus 5.5. The review attempt by Fable 5.1 hit a usage limit before
writing anything. Sonnet reviewed rev 1a (NOT YET: M1 the excursion, M2
write-once) and rev 2 (SIGNABLE); the trail is `docs/hold/PLAN-REVIEW.md`.

**It gates nothing.** There is no order path. It shows DRAFT until P1 is
judged.

**REV 3 — THE BAND RUNG, signed 2026-09-25 13:20,** her word *"sign"*. It
comes from her 09-25 NIFTY 23200 PE (*"we should have traded till nifty
reaches the lower band"*). `docs/hold/PLAN-PREREG.md` is now **rev 3, sha256
`b3d2c63b79a9cc512fbe4a480b610f142d1b1ecbe87697fa3e0694ff05c85327`**. Rev 2a's
hash above stays as history.
- **§2.7:** the band rung, for buyers only.
  - A long PE aims at d2, a long CE at u2. These are the zone machine's own
    3-min bands on the future, in σ, and never converted to index points.
  - Its word is the §1d gate on the zone arm row at the touch bar, read on
    the band's native fade side. There are four outcomes, each its own
    sentence.
  - The opposite trigger is printed as a fact, never an instruction.
- **§5:** a write-once `band_touch` row.
- **§6:** P2 (GIVING WAY band touches vs DEFENDED ones, `next15`), judged
  like P1. The same-bar overlap with a wall touch is flagged
  `also_wall_touch`.
- Merged verbatim from `PLAN-ADDENDUM-rev3.md` rev 3a. Sonnet reviewed rev 3
  (NOT YET); M1 and S1–S3 were fixed in 3a, and the trail is
  `docs/hold/PLAN-ADDENDUM-REVIEW.md`.
- **Not built yet.** It gates nothing.

---

## 1g. PRE-REGISTERED — THE VALIDATE WORD: GO · WAIT · NO (signed 2026-09-25 13:20, UNTESTED)

**The full text is `docs/hold/VALIDATE-PREREG.md` rev 1.** This section is
its anchor. **sha256 at signing:
`6f1d9047dbdd699e6356e445b9287fc07a7cf719bdea5ea8018d06c849757db5`.**
- Any later edit to that file is a new revision with its own change-log
  entry and a new hash here, never a silent change.
- **Nothing in it is a result.**

**Signed by the operator,** her word: *"sign"*.

**Her request:** *"i want the validate button there when i choose the strike
ce or pe and weather i long or short it . and than it should tell weather the
app the thinks i should take it or not or confidence score maybe"*. She gets
a COUNT, never a percentage: rule 4, and there is no forward record yet.

**What it registers, in brief:**
- five facts, each WITH you / AGAINST / NEITHER, all read off already
  registered objects:
  - her setup (the zone trigger with its §1d gate);
  - right now (§1e's entry check);
  - the market side (§1e §10.4);
  - the room and the next wall (§1f).
- **NO** if the entry check is FOLD or 3 or more are against; **GO** if none
  is against and 4 or more are with her; otherwise **WAIT**, naming what would
  have to change.
- every press logged write-once to `data/hold/check_<day>.jsonl`.
- **P:** GO checks are followed by larger 30-minute premium excursions than
  NO checks (§1e §7's unit).
  - It is judged at 15 or more of each and 10 or more sessions, by 30
    sessions at the latest, and must survive removing the best day.
  - If it fails, the word is deleted and the five facts stay as a checklist.

**Written after one live moment was seen,** and disclosed: her 09:36 entry
reads WAIT (1 of 5), and it then ran 150 → 181. No rule was shaped to it.

**It gates nothing.** There is no order path. It shows DRAFT until P is
judged. Built 2026-09-25 12:25, before signing, exactly to this text.

**REV 2, signed 2026-09-25 19:40 IST, on her delegation** (*"but i dont get it or capable enough to answer as a trader you think is best take that for now"*).
`docs/hold/VALIDATE-PREREG.md` is now rev 2, **sha256
`4a9b59638606e28515283f17e7af7ace0ec33f39274e8b93ab96027485b34423`**. Rev 1 is
kept word for word in `docs/hold/VALIDATE-PREREG-rev1.md` (hash above).
- **Your setup** reads the zone machine's closed 3-minute bar.
- **Stop room** is measured against the index's own median 1-minute candle; a
  stop inside one candle is AGAINST.
- **One wall is one fact,** and the holdability fact is "paying".
- **GO needs "Right now" = HOLD.**
- **A writer** is told plainly what she gets.
- **The unit** is one press per index per direction per 30 minutes.
- **The outcome** is "target or line touched first", on 1-minute highs and lows.
  It reads no break rule.
- **Judging:** each word against WAIT, in a set where the geometry is comparable.
- **Review:** three adversarial passes; SIGNABLE. Rev 1's press rows are never
  pooled with rev 2's.

## 1h. PRE-REGISTERED — THE EXPRESSION: BUY THE OPTION, OR SELL THE OTHER SIDE (signed 2026-09-26 20:48, before any code, UNTESTED)

**The full text is `docs/hold/EXPRESSION-PREREG.md` rev e.** This section is
its anchor. **sha256 at signing:
`45d8d369957d50303ccda89cf4588a1cc1102ff3e3b9d33b29cfedf2de45fc1e`.**
- Any later edit to that file is a new revision with its own change-log
  entry and a new hash here, never a silent change.
- **Nothing in it is a result.**

**Signed by the operator,** her word: *"sign"*.

**Her request (2026-09-25):** *"if any trade pops up engine should be able to
tell me weather to buy any option make sense or selling the otherside"*.

**What it registers, in brief:**
- **the expression (§A):** given her direction, at each 3-minute close, BUY /
  LEANS BUY / EITHER / LEANS SELL / SELL / STAND ASIDE, from five counted facts
  (SPEED, ROOM, WALL, REGIME, PREMIUM) and each leg's own refusals. The sale is
  at the buy's ATM strike. LEANS is a one-fact lead, or a refused tie; words
  named by refusal are never pooled with words on the count.
- **the writer in VALIDATE (§B):** GO / WAIT / NO from four writer facts. GO
  never stands on a could-not-check risk fact, or with no wall behind the sale.
  It amends VALIDATE rev 2 §1.6, §2, §3 and §4, for writers only.
- **the writer in the window (§C): no change.** Her answers: fold as today on
  every day, and no strike stop.
- **Falsifiers (§E.2):** R-multiples on the shared line; each word against the
  count units that do not point its way, per direction, pooled and in *with*;
  at 15 or more units and 10 or more sessions, by 30 at the latest; it must
  survive removing the best day. A failed word is withdrawn.

**Disclosed before signing** (§D): four frozen days, in-sample hindsight,
never a rate. The word changes often, and 841 of its 1,389 directional words
are LEANS. The 09-24 sold calls still fold at 14:38, by her answer.

**It gates nothing.** There is no order path, and it shows DRAFT until each
word is judged. Four adversarial reviews; the last found all three parts
signable.

## 1i. PRE-REGISTERED: THE CONFLUENCE SETUP (zone + OI + order flow) and its pass bar (signed 2026-10-21 00:45, UNTESTED)

**The full text** is `docs/setup-review/CONFLUENCE-PREREG.md`, sha256
`d5c4937fde3f20ffc772a22d22701200ed67f93bed990b4708841a5f2c31aa73`. Never edit it; amend it here instead.

**What it registers:**
- **Mary's actual trade** is the zone ONLY when OI and order flow also match ("when everything matches thats when those
  become buy or sell zones"). It is split into POCKET and EXHAUSTION.
- **The pass bar,** owed since §5e (2026-08-08) and set by Claude on her delegation ("you decide the pass bar as a
  trader"), applies per cell:
  - n ≥ 20;
  - mean R ≥ +0.25;
  - mean R still > 0 with the best trade removed;
  - beats zone-alone by ≥ +0.20R;
  - no day supplies > 40% of the total.
- **Her binding corrections:**
  - no time rule before the 15:00 new-trade cutoff;
  - holds run to 15:20;
  - no expiry rule;
  - buying and selling options get equal weight.
- **The one-shot first look** runs once, after this anchor.

**AMENDMENT 1 (2026-10-21 ~01:45, before any outcome was computed): the one-shot is DEFERRED, not run.**
- **The dry run printed counts only.** Across 26 scorable index-days (22 Sep → 19 Oct), it found:
  - 116 zone entries;
  - OI ✓ 52, FLOW ✓ 67, both on one bar 14;
  - **full confluence 7**; the largest cell holds 2.
- **Why defer:** running now would spend the record's blindness on n ≤ 2 per cell, a guaranteed INCONCLUSIVE, while
  exposing outcomes that would tempt redefinition.
- **What happens instead:**
  - the recorded days stay blind;
  - they are scored ONCE, pooled with the forward rows from `data/confluence_log.jsonl`, when any cell first reaches
    n ≥ 20;
  - definitions are unchanged.
- **Builder's readings 1–12:** listed in `tools/confluence_score.py`'s output header. They are adopted as written.

---

## 1j. PRE-REGISTERED: RIDE, her second setup (signed 2026-10-21 ~02:30, UNTESTED)

**The full text** is `docs/setup-review/RIDE-PREREG.md`, sha256
`dcb306a11ad662291a25094e7db3288aeacc3367be403d2364900302843aff7e`. Never edit it.

**What it registers.** Her words: "register RIDE as second setup with same three checks".
- **LOCATION:** READ-V2 §E's trend-pullback ENTRY, unchanged.
- **OI:** the trend-side front is BUILDING and the defending front is not BUILDING.
- **FLOW:** the pullback was not led by strong counter-trend aggression, and the trend side is back.
- **Her hold, with no candle close and no fixed target.** It exits on the first of:
  - a hard line plus 0.25σ, trailing to FLIP;
  - the trend-side front UNWINDING ("somebody gave up");
  - 15:20.
- **Control:** §E ENTRY alone.
- **Pass bar:** the same as §1i, over 4 cells.
- **Expressions:** buy ATM, buy 1-ITM and sell the opposite ATM are all recorded, with equal weight.
- **Run policy:** the same as §1i Amendment 1. Dry counts only until a cell can reach n ≥ 20 with forward rows.

**BUILT 2026-10-21 (uncommitted; live at her restart).** `ride.py`, `test_ride.py`, `tools/ride_score.py`,
`confluence_log.ride_inputs / build_ride / log_ride` (FADE rows now carry `setup: "FADE"`), `frame_v2.bars3(width=)`
(default unchanged), and a fail-soft server hook beside `log_new`. pytest 1728 passed, 1 skipped.
- **§E is never re-implemented:** `ride.entries` calls `frame_v2.plan` at each 3-min close with the bars, READ rows
  and basis band as of that close. With one fixed band it equals a single full-day `plan()` call's ENTRY rows on all 25
  index-days where that call returns rows. The band as of each close matters on one day (24 Sep NIFTY: the day-end band
  would add an 11:51 ENTRY the frame could not show then); the causal band is used.
- **Dry counts (51 index-days, 22 Sep → 19 Oct), never an outcome:** §E entries 73, OI ✓ 30, FLOW ✓ 48, both on one
  bar 18, **RIDE 18**; per cell ▼ NIFTY+SENSEX 7, ▼ BANKNIFTY 5, ▲ NIFTY+SENSEX 2, ▲ BANKNIFTY 4. Gate SHUT; `--run`
  refuses.

---

## 1k. AMENDMENT 2 to §1i and §1j: the past is looked at on Mary's request (2026-10-21, before any outcome was computed)

**Her words:** "can you tell me when these condition met what happened in the market afterwards".

**What this changes.** It lifts the blindness that §1i Amendment 1 and §1j §6 placed on the recorded days. FADE (7
confluence entries) and RIDE (18 entries), with their controls, are scored once and described row by row.

**The conditions:**
1. **The rules are frozen exactly as registered.** That includes:
   - the builders' readings;
   - the RIDE review fixes (`docs/setup-review/RIDE-REVIEW.md`), all made before this look;
   - the trail's FLIP→fut conversion using the READ row's own measured basis even when the plausibility band flags
     it, a reading declared here.
2. **Any rule change after this look is a NEW registration,** judged only on forward rows logged after its own anchor.
   The recorded days can never test it.
3. **The pass bar is unchanged:** n ≥ 20 per cell, past and forward pooled, under the frozen rules.
4. **No hit rate is printed.** The output is rows, plus §4's fields per cell (n, mean R, mean R without the best trade,
   the control's mean R, the largest day's share), marked INCONCLUSIVE where n < 20.
5. **Descriptive extras that are not in any bar:** MFE and MAE in points from entry to exit; the move 30 and 60 minutes
   after entry in the trade's direction; the option expressions in premium points.

---

## 1l. PRE-REGISTERED: READ-2, a trend led by flow and fuel, plus JAGAH (signed 2026-10-21 ~13:15 on her word "yes build all three", UNTESTED)

**The full text** is `docs/read/READ-2-PREREG.md`, sha256
`182aa67db3f7b8dc949f56cbe8231c847b69e7e1ea250ff85a16adbfacefb6ae`.

**What it registers:**
- **A FUEL vote:** 40-min futures ΔOI ranked ≥ p80, voting with the sign of the price move.
- **A LEG FLOW vote:** since the leg's extreme, ≥ 6 bars, sell share S ≥ 0.70 and the sell/buy bar-size ratio M ≥ 2.0.
- **LEAN + FUEL + LEG FLOW** → `TREND · flow+fuel`, at full size.
- **JAGAH,** a placement line: room to the next reaction point, the obstacle behind, and fuel/flow in words. Never a
  probability.

**Logging and the kill condition:**
- read-1.1's word is logged beside it.
- The forward check runs from 2026-10-22.
- Kill at 20 upgrades if more than half saw price close back past FLIP first.

**21 Oct is in-sample** (it motivated the rule) and is not evidence.

**AMENDMENT 1 to READ-2 (2026-10-21 ~14:10, before the forward check starts on 22 Oct): persistence, not thresholds.**
- **The problem.** The literal "downgrade when FUEL or LEG FLOW stops" flickered on the in-sample replay of 21 Oct
  NIFTY:
  - up at 10:10, down at 10:25, up at 10:30, down at 10:40, up at 10:45, down at 10:50;
  - then LEAN for the rest of a day that kept trending down. FUEL is a rolling 40-min OI burst, so it fades while the
    trend continues.
- **This is a structural error, like read-1.1's LEAN-break fix of 2026-10-08,** not a number to tune.
- **The fix:**
  - **FUEL is the TRIGGER and is latched:** a FUEL = d vote at any mark since the leg began counts for the rest of
    that leg.
  - **LEG FLOW is the condition that keeps it:** TREND · flow+fuel drops to LEAN only after LEG FLOW has failed to
    vote d at **3 consecutive marks** (15 min), or on a LEAN break.
  - **No threshold changes.**
  - **JAGAH's fuel words show the leg's latched fuel** (its kind, its max rank and when it happened), plus "abhi"
    (the current 40-min rank).
- **The kill condition and the forward start date (2026-10-22) are unchanged.**
- **Disclosure:** 21 Oct was looked at to find this flaw. It remains in-sample.

---

## 1m. PRE-REGISTERED: HOLD v2, the push trail, the profit lock and FADE → RIDE (signed 2026-10-21 ~16:00 on her word, UNTESTED)

**The full text** is `docs/setup-review/HOLD-V2-PREREG.md`, sha256
`fca358a2b66337f4e51b38edec55281c87f9b16a62be895ad9a58f2548f5d9a6`.

**What it registers:**
- **A second exit, scored beside v1 on the same FADE (§1i) and RIDE (§1j) entries:**
  - a line trailing to the last PUSH origin + 0.25U, intrabar and never a close;
  - a breakeven lock once MFE ≥ 2R;
  - "gave up" (trend front UNWINDING);
  - 15:20.
- **FADE → RIDE at VWAP:** a fade that reaches VWAP while RIDE's OI and FLOW checks agree continues under v2.

**Pass bar, paired on ΔR:** n ≥ 20 per setup group, mean ΔR ≥ +0.20, drop-best > 0, max day share 40%.

**AMENDMENT 1 to HOLD v2 (2026-10-21 ~18:30, before its forward start on 22 Oct): a logic fix to "somebody gave up".
No number changes.**
- **The flaw.** As written, the exit fires whenever the trend-side front reads UNWINDING, whichever way price is going.
  The in-sample description showed it firing on call writers *buying back while price kept falling*, i.e. profit-taking
  by the winners, not capitulation. Examples: 21 Oct SENSEX FADE at 09:48, and Mary's 23000 PE at 10:54, after which
  the move ran a long way.
- **Her own rule** (§1d, 22 Sep) is about the side being **forced**: "which side stops first increasing their positions
  and then unwinding". A writer who unwinds while price moves in their favour is not forced.
- **The fix.** In HOLD v2, "gave up" requires the trend-side front to read UNWINDING **and** price at that 3-min close to
  be on the writers' losing side of the price at the front's peak time:
  - ▼ / CE writers: close > spot at the peak minute;
  - ▲ / PE writers: close < spot at the peak minute.
- **Unwinding with price still moving in the writers' favour** is stamped "munafa booking", never an exit.
- **RIDE v1 (§1j) is NOT changed.** It stays frozen as the baseline v2 is judged against.
- **Disclosure:** found on the in-sample description (§1k days and 21 Oct). Those days remain in-sample.

**AMENDMENT 2 to HOLD v2 (2026-10-21 ~19:15, before forward start): the "losing side" uses the system's standard break
distance.**
- **The problem.** Amendment 1's test "spot above the peak-minute spot" had no buffer. It fired on Mary's 23000 PE at
  10:54 on a **3.9-pt** excursion during chop at the peak level. That is noise.
- **The fix.** The losing side now means beyond the peak-minute spot by **0.25U** (U = max(σ, 0.1% of price)). This is
  **the same break distance the whole stack already uses:** marks TOOTA, push fail and the HOLD v2 line itself. No new
  number.
- **This is the LAST change before forward data.** From 2026-10-22 HOLD v2 is frozen as amended. Any further change is a
  new registration.
- **Disclosure:** found on her 21 Oct trade, which is in-sample.

**Scope:** forward only from 2026-10-22. Days up to 21 Oct are in-sample and never counted. Her hold window shows the v2
line for display only.

**BUILT 2026-10-21 (uncommitted; live at her restart).** `hold2.py` (pure: the PUSH port, `exit_v2`, `fade_convert`, the
window's line), `test_hold2.py`, `tools/hold2_score.py` (dry · `--run` gated on forward rows from 22 Oct, each group judged
once at n ≥ 20 · `--describe-in-sample [--trade ID]`, IN-SAMPLE, never counted), `tools/gen_push_expected.mjs` +
`test/fixtures/push_expected.json`, `confluence_log.push_bars / push_refs`, `fold_live.hold2_rows`, `server._hold2` (a
`hold2` block on `/api/fold?id=`, display only) and the float's HOLD v2 line (`ui-v2/src/pro/Desk.tsx`, `api.ts`). The
scorer's 12 readings are its own header.
- **Amendment 1 built the same evening:** `hold2.close_read` / `closes` (the front's peak minute and the chain spot then,
  cut causally); munafa booking is stamped, and the window reads "CE 23000 munafa booking (unwinding, price still neeche)".
  RIDE v1 is untouched: the v1 R column is identical on all 28 in-sample rows.
- **Amendment 2 built the same evening:** `hold2.losing` is "lose" only beyond 0.25U, using the line's own U (5-min
  vwapSeries σ via `sigma_at`, floored at 0.1% of spot). Inside the buffer it stamps "munafa / chop (within 0.25U)". The v1
  column is unchanged. pytest 1781 passed, 1 skipped. HOLD v2 is frozen as of here.
- **Port check:** v2.js flowState run through node on 9, 12, 13, 16, 19 and 21 Oct gives the same state on every bar. That
  is 289 tape bars with 27 PUSH, and 253 of the extension's own fixture bars with 33 PUSH. There were 0 differences.
- **References:** NIFTY has them (GoCharting, plus Upstox for the bars GC lacks) and so does BANKNIFTY (Upstox). SENSEX has
  none, because its 5-min bars are not rankable (FLOW-STATE §5), so its trail reads "push ? ref nahi".

---

## 1n. PRE-REGISTERED: FADE-D, the deceleration fade at an extreme (signed 2026-10-21 ~20:00 on her "offcourse", UNTESTED)

**The full text** is `docs/setup-review/FADE-D-PREREG.md`, sha256
`3fd5e84ed3b7fb2a2972a3bb64a4ff719a1313f0909ee45b0f8b1316ea31f237`.

**What it registers.** Her own "build-rate deceleration" at the zone or an extreme, never encoded in §1i:
- **Fading effort:** a new extreme made on delta ≤ 25% of the leg's biggest bar.
- **CVD turned:** the last bar's delta is against the move, and CVD is below its leg peak.
- **The winning side's OI lead breaks:** ≥ 10 points off its session peak within 15 min.
- **Entry:** all within 30 min of the location bar.
- **Exit:** HOLD v2.
- **Control:** the location alone.
- **Pass bar:** §1i §4.

**Scope:** forward only from 2026-10-22. 21 Oct is in-sample.

**AMENDMENT 1 to FADE-D (2026-10-21 ~21:30, before its forward start): remove the VWAP-room condition.**
- **The inconsistency.** §4's "close still above VWAP (room to target)" was carried over from FADE §1i, whose target
  *is* VWAP. FADE-D's exit is HOLD v2, which has no VWAP target, so the condition has no job.
- **What it does wrong.** It blocks a reversal exactly when price confirms it by crossing VWAP. On 21 Oct (in-sample)
  it blocked the NIFTY top entry at 10:00, when all four conditions held.
- **The fix.** The VWAP side becomes a **stamp**, not a condition.
- **Unchanged:** every number, including the 10-point lead drop. That drop read 9.8 at 09:55 on 21 Oct, and it stays
  at 10 because changing a number to fit the day that inspired it is fitting.
- **This is the last change before forward data.**

---

## 1o. PRE-REGISTERED: THE ONE-SIDED METER, the day type from vote consistency (signed 2026-10-22 ~15:45 on her "fix everything", UNTESTED)

**The full text** is `docs/setup-review/ONESIDED-PREREG.md`, sha256 `60ba8f8f7d0bb8bd5333a78f70010d86219c12aea42dc8861073f5be632b2f14`.

**What it registers:**
- **7 votes per 5-min bar:** delta, CVD 15m, VWAP side, writers, writers 15m (on a fixed strike set), futures OI × price, peers.
- **One-sided bar:** 5 or more votes agree.
- **Day type:**
  - **TREND:** ≥ 10 one-sided bars, ≥ 80% of them one way, flips ≤ 1, VWAP crosses ≤ 2.
  - **PIN:** range < 0.5% of the open and crosses ≥ 4.
  - **CHOP:** crosses ≥ 4 or flips ≥ 3.
  - **MIXED:** anything else.

**Scope:**
- **Display only;** it gates nothing.
- **Forward from 2026-10-23.**
- **Daily 15:30 log** beside the day's realised shape.
- **Kill condition:** if the 11:30 type matches the afternoon no better than the 11:30 READ word.
- **In-sample:** 21 and 22 Oct.

**BUILT 2026-10-22** (`onesided.py`; display only; live from the 23 Oct restart). It is exposed as `decode.onesided` on /api/read and `frame.decode`, the Read-tab DIN row and the extension's DIN line. It writes a daily row to `data/onesided/onesided_log.jsonl` (with the 11:30 type for the clock).
- The writers' 15-min vote uses a fixed strike set (A24).
- SENSEX bars under 20 lots are stamped "patla".
- In-sample replay: 21 Oct NIFTY TREND ▼, 22 Oct CHOP. **Watch (A37):** the counts are whole-day, so CHOP is sticky; TREND came late on 21 Oct.

---

## 1p. AMENDMENT: VALIDATE rev 3, the Validate tab's word (signed 2026-10-23 ~22:30 on her "send to a subagent opus 5.5 to build it", UNTESTED)

**The full text** is `docs/hold/VALIDATE-PREREG-rev3.md`, sha256
`a41863060880b5843293aff7660d3adee6a615056fc67895fabee2a1ef5f82a5`.

**Her verdict before it:** *Validate first, because her 22 Oct loss was the ENTRY, not the hold.*

**The base ("rev 2" in her instruction)** is the Validate tab's ten checks as built: `ui-v2/public/validate2/engine.js` at
5b9ed44, sha256 `8d143379…04cb`, i.e. DESIGN.md §3.3–§3.5. It is **not** §1g's five-fact word: `validate.py` REV "2",
`/api/hold/check` and its clock are untouched.

**What changes** (everything else stays as the base):
- **#2 DAY / TREND:** §1o's type plus the share of the day's straddle move used, `u`. The day's 1σ is the 09:20 ATM
  straddle ÷ 0.8 ÷ √(weekdays to expiry); `u` is measured in her direction.
  - TREND her way → WITH; TREND against → AGAINST.
  - CHOP / PIN:
    - `u ≥ 0.90` → AGAINST, buyer and writer;
    - `u ≤ −0.90` → WITH;
    - otherwise a writer WITH, a buyer NEITHER.
  - MIXED → the base's daytype row.
- **#4 / #5 walls:** ROLLING (Fable's `detector.rolling`, today's ATM pace) → NEITHER. Only a building wall that is not
  rolling counts as DEFENDING.
- **#6 ORDER FLOW:** CVD and the fight winner are dropped.
  - Effort per point first: an expensive high (≥ 2×) is AGAINST a long and WITH a short; a cheap low (≤ 0.5×) is WITH a
    short and AGAINST a long.
  - Then the futures quadrant: new money her way WITH, against AGAINST, covering or liquidation only NEITHER.
  - SENSEX: could not check.
- **#7 VPIN:** printed, never counted. A buyer is counted on 9 checks, a writer on 8. GO stays **≥ 6 WITH**, 0 against,
  ≤ 1 could not check: the base's bar rounded up, and the bar BANKNIFTY and SENSEX already had.
- **#10 PAYING:** the payers covering at a fresh extreme in her direction, with the tape exhausted (EXHAUST / ABSORB /
  effort ≥ 2× at a high), → AGAINST "pop khatam". On SENSEX the tape is not read, so it cannot fire there.

**Every reply carries `rev`.** Display only; nothing gated.

**Evidence:** Fable's oi-lab audits (NIFTY, 19–38 days, in-sample candidates except effort's two holdouts). Fable's
EM-USED was insufficient n, so **0.90 is a trader's number.**

**Disclosed:** written after the 22 Oct facts and one offline DECODE read (§6 of the file). No rev 3 vote was run before
hashing.

---

## 1q. AMENDMENT: SENSEX reads NIFTY's order flow — VALIDATE rev 3.1 and HOLD v2 Amendment 3 (signed 2026-10-25 on her "sign without 5", UNTESTED)

**The full text** is `docs/hold/SENSEX-NIFTY-FLOW-PREREG.md`, sha256
`9e2831b5b72a12a4f4a6e9fa6ed37d8ea81ca0a770ffa71d7d7ace80a47342e1` (signed, §9).
- Its draft was hashed `552d6927…73c9` before any replay.
- Revision 1 (§8: facts only, no rule changed) was hashed `7284a18b…8a93` after the replay.

**Her method, verbatim:** "i dont consider sensex oderflow i take nifty oder flow and trade in sensex they almost work in
sync so leave or remove sensex oderflow chart . but i consider its oi".

**What changes, for a SENSEX trade or slip.** Every ORDER-FLOW read is NIFTY futures', labelled NIFTY. Every OI read stays
SENSEX's own.
- **Validate rev 3.1** (amends §1p):
  - #6's effort and quadrant come from NIFTY;
  - #10's tape part (EXHAUST / ABSORB / EXPENSIVE) comes from NIFTY, so a SENSEX spent pop can fire;
  - #1's flow chip comes from NIFTY.
  - Rev string: `3.1 (SENSEX-NIFTY-FLOW 9e2831b5)`.
- **HOLD v2 Amendment 3** (amends §1m's push source): a SENSEX line moves on NIFTY's pushes, to SENSEX's own same-slot
  5-min open + 0.25U (U = SENSEX's σ, 0.1 % floor).
  - Applies live and to forward scoring from 2026-10-25.
  - Rows are stamped `push_src` (`SENSEX-ux` before, `NIFTY` after).
- **The FLOW read shown in a SENSEX trade** is the NIFTY engine's flat flow chip, mapped to her direction. fold rev 6's
  word, G and acceptance are untouched.
- **The trade map's l4** for SENSEX prints `NIFTY push`.

**Struck at signing:** §2 FRESH-AFTER (the post-high pop window), her "without 5". #10 keeps rev 3's FRESH.

**Not changed:**
- the price mechanics that use SENSEX's own trades (Validate's give-up G and #9 ROOM, #3, fold's G and acceptance);
- NIFTY and BANKNIFTY;
- every OI read;
- the SENSEX order-flow chart.

**Replay before signing** (`docs/hold/validate3/REPLAY-rev3.1.md`, IN-SAMPLE, described only):
- no Validate word changed on 51 entries;
- no in-trade state changed on her 10 SENSEX trades;
- on 22 Oct, NIFTY's flow turned against her at 13:14, nine minutes after SENSEX's own tape (13:05).

**Code:** `sensex_flow.ON = True`, `FROM = "2026-10-25"` (`sensex_flow.py`) and `R31.ON = true` (`engine.js`). OFF
restores rev 3 / §1m exactly; that is tested.

## 1r. REGISTRATION: ZONE-3M, the zone on her chart's 3-minute bands (signed 2026-10-26 18:13, effective 2026-10-28 09:15, UNTESTED)

**The full text** is `docs/setup-review/ZONE-3M-PREREG.md`, sha256
`41cbda8a254e26492bb2b044c9149220632c2211f625d43a76918ed4ea01db71` (signed).

**Her words, verbatim:**
- "Yes, reopen my 15 Aug call: compute the zone machine's bands on 3-minute bars like my chart, as a new registration
  starting from a date you name. Plan it after close."
- Signed: "commit — I sign ZONE-3M as written. Build it tonight, commit locally, don't push."

**What it reopens:** §1c's 15 Aug decision ("not required"), on 26 Oct's evidence.
- At 09:24 her 3-min d2→d3 BUY at the NIFTY low (22,440f) was never armed: the 1-min-σ d2 sat about 27 pts beyond
  hers.
- 15 Aug's "~5 pts" bound was measured mid and late session.

**What changes:** only the bands and how the 09:25 anchor is read.
- VWAP and σ are computed on the 3-min bars themselves (`_Vwap`), not copied from 1-min.
- A bar is eligible once it holds a minute at or after 09:25.

**What is unchanged:** the arm at d2/u2, the entry, the window, the ∓20 stop and the lock.

**Populations, never pooled:**
- New rows are `rule: "zone3"` with `bands_on: "3m"`, from 28 Oct.
- The 1-min `zone` (§1b) keeps logging beside it, for FADE §1i.
- 5c, Validate and the Signals ballot are unchanged.

**One switch, one date:** before 28 Oct nothing zone3 is logged, shown or sent.

**Acceptance on 26 Oct** (in-sample, described only):
- arm at the 09:24 bar;
- entry at 22,534.1f, at the 09:27 bar's close;
- stop 22,425.1f.

**Note on §1c's "one-line fix":** it cites `live.py:522`, which is now the option-leg path (~566). The zone path is
`resample_index` in `live._at_interval`.

---

## 1s. PRE-REGISTERED: OPTION-FLOW READS, four shadow stamps (registered 2026-11-04 ~02:00 on her "Yes, pre-register", forward from 2026-11-04 09:15, UNTESTED)

**The full text** is `docs/setup-review/OPTFLOW-READS-PREREG.md`, sha256
`962afdf35e38e0637f809544e1036c5347640b858f49c6c2e2692fc15d831fa3`.

**The four reads, NIFTY only, shadow (no gate, no vote, no alert, no screen until she signs a build):**
- **R1 band touch + WHO:** a premium band touch, stamped with the strike's WHO and the index at its own band or mid.
- **R2 pullback card:** HEALTHY / REVERSAL-START / MIXED at a pause's second close.
- **R3 SQUEEZE ON:** a state stamp when the cap (or floor) covers with the cascade. Never a forecast.
- **R4 PIN:** expiry afternoons only.

**In-sample, described only:** 28, 29, 30 Oct, 2 and 3 Nov (NOTEPAD A215–A219). **Pass bar: owed by the operator**
before any evaluation is read. Under 15 per cell is INCONCLUSIVE. No rate is printed. §1q, §1b, §1d and Jarvis's count
are unchanged.

**Amendment 1 (4 Nov ~03:00, before any forward row exists; her "make sure its able to fill evevry data from no matter whenever i turn on the computer evevrything that it uses shud be able to backfill"):** the anytime-start rule binds the replay.
- Minutes the chain recorder did not see (a late start, a restart gap): C3's OI and premium come from `data/chain_backfill/backfill_NIFTY_<day>.jsonl` (Upstox REST, per strike per minute), anchored to the first live snapshot.
- C8's delta for those minutes: the Black-Scholes delta from that premium, spot, strike and time to expiry (IV implied from the premium, r = 0) [I].
- Dext footprints: the bridge's catch-up (every strike the day's spot touched ±5 is asked once from 09:15, at any start time, after the close too), or `--now <day>` for an earlier day.
- Jarvis pause / call rows before the start: legs.py's rule re-run on the rebuilt frame.
- Every such reading is tagged `backfill`. Backfilled rows are counted in their own column and never pooled with observed rows unless she says so. The PREREG file is unchanged (sha above).

## 2. Dead — do not revive without new evidence

| hypothesis | verdict | scorer |
|---|---|---|
| squeeze + falling OI = fade | REJECTED — BANKNIFTY inverts the sign | `squeeze_score.py` |
| engine event stream | `risk` −0.1 / `lean` −6.2 vs +4.1 control → default OFF | `signal_review.py` |
| SMC layer | 4× over-fires vs LuxAlgo, ⅔ UNKNOWN → default OFF | — |
| classic 15-min ORB | REJECTED — NIFTY breakouts *fade* (39% hit, −21.1 to close) | `orb_score.py` |
| overnight gap-fade | REJECTED — NIFTY fade ≈ 0 and under its long control | `gap_score.py` |
| d3 on F&O **stocks** | REJECTED — pooled 47% hit, med 0.000% (n=47, 7 names) | `stock_score.py` |
| d2 (−2σ) entries | noise everywhere — 180 NIFTY signals ≈ coin flip | `rotation_score.py` |
| **selling** any upper band | REJECTED on 5 independent datasets, every depth | multiple |
| compression / trap=CLEAR filter | HARMFUL — selected losers in 3 separate datasets | multiple |

### Two filters that were pre-registered and falsified (2026-08-04)

1. **Morning window.** Found post-hoc on ADANIGREEN (09:30–10:00 = 71% hit),
   echoed on NIFTY (83%) — then **died on RELIANCE** (50%, −0.21R), the
   largest sample of the three. Classic small-sample mirage: two of three
   agreeing is what randomness looks like at n≈7.
2. **Rotation-vs-trend state** (≥80% of last 20 closes below VWAP + falling
   VWAP = TREND). Pooled **ROTATION 43%/−0.21R vs TREND 38%/−0.25R — no
   separation**; ADANIGREEN's ROTATION bucket was 0/3. *Design flaw worth
   fixing if ever retried:* the 20-bar lookback silently dropped every
   pre-10:15 trigger (n fell 16→9, 28→18, 17→9), so it never tested the
   morning trades it was built to explain.

---

## 3. The regime map — the most reusable thing learned

Four independent tests drew the same boundary:

| instrument / context | behaviour |
|---|---|
| NIFTY, SENSEX — intraday σ-stretch | **mean-reverts** (liquidity noise) |
| BANKNIFTY | **trends** — inverts every reversion test |
| Overnight gaps | no edge — informed repricing, not noise |
| Single F&O stocks | no edge — a stock's −3σ is often *news*, and news continues |

**The edge is specific to broad-index intraday liquidity noise.** A stretch
caused by information does not revert; a stretch caused by flow does.

### Why stocks fail, quantitatively

1σ as a share of price at a d3 trigger: **NIFTY 0.076% · RELIANCE 0.171% ·
ADANIGREEN 0.249%.** So NIFTY's 20-pt stop is 1.55σ, while the same σ-scaled
stop on a high-beta stock is 3× wider in price terms — for a bounce that is
not 3× bigger. Risk-reward inverts. (Verified across 1.0σ / 1.55σ / 2.0σ
stops; negative at all three, and negative at every width after dropping the
single best trade.)

---

## 4. Two conditions the operator watches that are NOT yet scored

Both are logged live by `trigger_log.py` and need ~20–25 signals.

- **Gamma regime at trigger** (their #17). Mechanically sound — negative
  gamma amplifies the move that made the d3, pin/positive damps it — but
  there is no per-trigger gamma history in the cache, so it is untestable
  backwards.
- **OI strength ≥40% on the side being bought** (their #18). The available
  proxy (single-strike monthly-leg ΔOI) says a **40% put-heavy entry veto
  would have removed 10 of 12 signals including 9 winners** — at a d3 low the
  flow is structurally CALL-heavy; put-heaviness arrives *after* the turn.
  **Recommendation: use it as a hold/add confirmation past VWAP, not an entry
  veto.** Post-hoc hint only (n=12, not pre-registered): the two worst trades
  were the only ones where ΔCE ≥ 3.5× ΔPE — a one-sided call-writing ceiling.

---

## 5. Stop rule for this line of work

**As of 2026-08-04, seven consecutive tests outside NIFTY/SENSEX d3 came back
negative or falsified.** Two "findings" appeared mid-search and both
evaporated on the next dataset.

> Further slicing of `data/backtest/` (incl. the ADANIGREEN / RELIANCE
> TradingView exports) will manufacture a false positive by multiple
> comparisons. **The next evidence must come from forward live logging
> (`trigger_log.py`), not from re-cutting this cache.**

If a new idea is worth testing, it must be **pre-registered in this file
before the run** — prediction first, then the number.

### The methodological lessons, both paid for today

1. **Hit rate without a stop is a mirage.** ADANIGREEN's d3 looked like 67% at
   a fixed 30-min horizon; with a real stop it was 25% hit and 15 of 16 trades
   stopped out.
2. **Always ask what remains after dropping the single best trade.** That one
   ADANIGREEN winner (+13.6R) carried an entire "positive" mean that was
   negative without it.

---

## 5b. PRE-REGISTERED — two-leg OI sign divergence (written 2026-08-04, UNTESTED)

Registered **before** any scoring run, per §5. Nothing below is a result.

**H1.** On a premium-matched leg pair (both legs ≥ ₹100, premiums within ±₹25 —
the operator's selection rule), the **sign relationship between the two legs'
ΔOI** separates directional moves from chop, and does so *earlier* than the
level of either leg's OI.

Metric, per 15-minute bucket:

```
strength = (ΔOI_CE - ΔOI_PE) / max(|ΔOI_CE|, |ΔOI_PE|)
```

**Predictions, committed in advance:**

1. `|strength| < 1` (both legs' OI moving the SAME way) → the index is
   ranging in that bucket; band triggers inside it underperform.
2. `|strength| > 1` (OPPOSITE signs) → directional bucket. **strength < 0 →
   index up** (call writers covering while put writers build); **strength > 0
   → index down**.
3. The sign of `strength` leads or coincides with the index's move for the
   bucket at a rate materially above 50%.
4. On the d3 setup specifically, `strength` turning negative is a **hold/add**
   signal after the VWAP cross — *not* an entry filter (same conclusion §4
   reached for chain-level OI; predicted to repeat per-leg).

**Falsifier:** prediction 3 at or below ~55% across ≥15 sessions, or
prediction 1 failing to separate at all.

**Provenance — this must not be forgotten.** The hypothesis was *generated*
from 2026-08-04, where all 6 buckets matched (0.07 ranging, then −1.13/−1.35
into the rally, then +1.51/+1.79/+1.35 into the fall). **That day therefore
cannot test it.** 2026-08-04 was also a weekly expiry, when OI unwinds
atypically — expiry days should be bucketed separately, not pooled.

**Data required, and why it does not exist yet:** per-leg 1-min OI for a
premium-matched pair. Expired weeklies drop out of Dhan's scrip master, so
this is forward-capture only. First capture:
`data/backtest/WEEKLY_LEGS/NIFTY_2026-08-04_*.json` (partial, to 10:52).
Needs ~15 sessions before any number is worth reading.

---

## 5d. PRE-REGISTERED — the u3 SELL mirror (written 2026-08-08, UNTESTED)

**Written BEFORE the run. Committed before the run. If this section is edited
after the result is known, the pre-registration is void and the result with
it.**

### Why this is allowed at all, given §5's stop rule

§5 says stop re-cutting `data/backtest/` and pre-register anything new. This
qualifies as new for one specific reason: **C3 rejected upper-band selling on
the OLD one-candle rule.** The §5c two-candle entry is a different trigger, and
moving from one to two candles is exactly the change that turned the buy side
from noise into the one surviving edge. So the mirror on the CURRENT entry has
never been tested.

That is a real distinction, not a loophole. It is also the LAST slice this
line of work gets without new live evidence: if it fails, the sell side stays
built (the operator asked for it over C3 and that stands, CHECKLIST C12) but is
never again presented as anything but a rule they follow.

### The rule under test, exactly

`band_rotation.detect_index_run(bars, side="SELL")` as it shipped 2026-08-08:
a bar's HIGH tags `u3`; that bar becomes the reference; within `RUN_WINDOW`
(10) bars a candle CLOSES below the reference candle's LOW; post-09:25;
first-of-run; stop `level + OPERATOR_STOP_PTS` (20). u3 only, never u2.

**Exits are NOT part of this test.** The operator's short exits were specified
on 2026-08-08 and are unbuilt, and one of their parameters (the CALL-heavy
threshold) is deliberately unanswered. So this scores the same way the BUY side
was scored — a fixed forward horizon with the stop applied — which is what
makes the two numbers comparable at all.

### Method

`run_score.py`'s existing apparatus, unchanged: `HORIZON_BARS` +6m/+15m/+30m,
`_stop_exit`, and the same unconditional control the buy side was measured
against. Favourable for a short means price FELL.

**Primary dataset: NIFTY only** (65 cached sessions, 18 signals emitted).
SENSEX and BANKNIFTY are reported but do NOT decide the verdict — picking the
best of three indices after the fact is the multiple-comparison fishing that
produced the two findings §5 says evaporated.

### The bar, stated before the numbers exist

**PASS** requires ALL THREE at +30m on NIFTY:
1. hit rate **≥ 60%**
2. median move **≥ +10 pts** in the trade's favour
3. median **≥ +10 pts above the unconditional control's median**

**FAIL** is anything else. There is no "promising", no "directionally right",
and no re-cutting to a different horizon to find a number that passes.

**INCONCLUSIVE** if n < 15 — the buy side's own verdict rests on n=18/19, and
anything thinner is not evidence either way.

### ⚠️ MEASURED ON THE MANAGEMENT THE OPERATOR DOES NOT USE (noticed 2026-08-08)

The bar below is written at a **fixed +30m horizon**. §1's own management table
lists that as *"no stop, fixed 30-min exit"* — one of four managements measured,
and **not the one adopted**. The adopted management is *"hold the stop until
VWAP, then trail band-to-band; from +2σ, 15 pts under the high. Flat by 15:15."*
The operator had refused the 30-minute exit before; it was never written down,
which is why it came back.

So this result says: **the sell mirror fails under a management the operator
does not trade.** It is untested under the one they do. Same standing as §1's
VOID notice — correctly measured, wrong thing measured.

**It is deliberately NOT being re-run.** §5's stop rule forbids re-cutting
`data/backtest/` until a number agrees with us, and "the criterion was wrong so
let me try again" is exactly how that starts. The sell side keeps shipping as
it is — drawn because the operator asked, labelled as carrying no score. The
real management gets measured on LIVE data (§5e), where it cannot be re-cut.

### RESULT — run 2026-08-08. **FAILED**, and narrowly, which is the point.

NIFTY, 65 sessions, 18 signals. The BUY side was run through the same harness
in the same pass as a control on the harness itself, and it reproduced the
record's 68.4% at +30m — so the apparatus was working when it returned this.

| horizon | SELL hit | SELL med | control med | edge |
|---|---|---|---|---|
| +6m | 33.3% | −3.10 | −0.00 | −3.10 |
| +15m | 55.6% | +4.25 | −0.00 | +4.25 |
| **+30m** | **55.6%** | **+9.35** | −0.00 | **+9.35** |

Against the bar written before the run:

| | required | got | |
|---|---|---|---|
| hit @+30m | ≥ 60% | 55.6% | ✗ |
| median @+30m | ≥ +10 | +9.35 | ✗ |
| edge over control | ≥ +10 | +9.35 | ✗ |

n=18, so not inconclusive. **All three missed. FAIL.**

Two of them missed by almost nothing — 4.4 points of hit rate and 0.65 of a
point of median. That is precisely the shape of result the pre-registration
exists to handle, and the criterion said in advance: no "promising", no
"directionally right", no re-cutting to another horizon. It fails.

**One honest observation that is NOT a rescue.** The sell curve has the same
signature as the buy: negative at +6m, positive by +30m. The trade goes against
you first and then works — the property §1 already records for the buy side.
That makes the mirror behave like a mirror, which is a statement about the
DETECTOR being correct, not about the edge existing.

**BANKNIFTY inverts again, and it is still not evidence.** Its SELL ran 60% /
+25.00 at +30m while its BUY ran 37.5% / −75.90, consistent with C4's finding
that BANKNIFTY runs the other way. n=5. The pre-registration excluded
BANKNIFTY from the verdict for exactly this reason, and n=5 is under the
inconclusive line anyway. **Do not act on it and do not re-cut to chase it.**

**SENSEX is unreadable here, not negative.** Every median came back exactly
0.00 across both sides and all three horizons. That is a data artefact, not a
result; the SENSEX cache needs looking at before any SENSEX number from this
harness is quoted.

### What this changes

Nothing about what ships. The operator asked for the sell signal over C3's
rejection on 2026-08-08 and that stands (C12). It draws, and it is labelled as
carrying no score — and that label is now backed by a test rather than only by
an old verdict on a different entry.

**This was the last slice.** §5's stop rule applies with full force now: no
further re-cutting of `data/backtest/` on the sell side. The only route to a
different answer is `trigger_log.py` collecting live fires, which needs a
server restart to activate.

### What a PASS would and would not mean

It would NOT overturn C3. C3 measured a different entry across five datasets,
and one passing test on 65 NIFTY sessions does not retire that. A PASS means
"worth collecting live triggers on", which is `trigger_log.py`'s job — not
"the sell side is now an edge".

A FAIL changes nothing about what ships. The operator asked for the signal
over a rejection already.

---

## 5e. PRE-REGISTERED — the LIVE forward test, both sides (written 2026-08-08)

**Written before a single row exists.** The operator: *"lets make it and we
will score everything from monday onwards buy and sell signal"*.

This is the clean kind of test. §5 closed `data/backtest/` to further slicing;
forward-collected triggers are the one route it leaves open, and a forward test
cannot be re-cut until it agrees with you.

### What is being collected

`trigger_log.py`, from the first session after 2026-08-08. Every fire of BOTH
sides, with the bar's gamma/ctx and the chain's OI strength at that moment.

**It needs a SERVER RESTART to activate.** Until that happens nothing is
collected and this section is measuring nothing.

### One thing had to be fixed first, and it was load-bearing

Until 2026-08-08 the logger read `rotation` — §1's ONE-CANDLE rule, which marks
the d3 TOUCH and which this file marks VOID. It never read `rotation_run`, the
two-candle ENTRY the chart actually draws, because the logger was written
2026-08-04 and `rotation_run` arrived on the 07th.

So a forward score started before this fix would have measured **a different
rule from the one on screen**, and nothing would have said so. The 256 rows
already on disk are from that path: they are **quarantined by `rule != "5c"`,
not deleted** — their gamma/ctx/OI context is real, only the rule is wrong.

**They do not count toward anything below. The sample starts at zero.**

### How it is measured — NOT on a clock

**Corrected 2026-08-08 after the operator caught it.** The first draft of this
section scored at a fixed +30m. That is §1's *"no stop, fixed 30-min exit"* —
a management that was measured and **not adopted**, and one the operator had
already refused. Scoring live trades on it would measure a trade they never
take.

The forward score uses the **adopted management**: hold the stop until VWAP,
then trail band-to-band; from +2σ, 15 pts under the high; flat by 15:15. On the
sell side, the operator's own exits
(`docs/superpowers/specs/2026-08-08-operator-short-exit.md`) once their two open
parameters are answered.

**This is why the logger captures the SIGNAL, not an outcome.** `trigger_log`
records the fire and its context; the bars afterwards are already cached, so
the exit can be scored later under whatever the settled rule is — and re-scored
if it changes, without throwing away a single collected signal. Nothing about
the exit has to be committed to now, which is the whole point.

> **⚠️ CORRECTED 2026-08-14 — "the bars afterwards are already cached" was
> FALSE, and it was load-bearing.** This section's central design bet assumed
> the tape would be waiting whenever the exit rule settled. It stopped being
> true on **2026-08-05**, when the Dhan data API lapsed: `backfill.py` fetches
> through `dhan_fetch`, so `data/backtest/` still ends **2026-07-31** and **no
> August session was ever materialised**. Every §5c row on disk therefore
> carries `unscored` — *"UNMEASURED, not flat"* — and a live session was
> scoreable only between the close and the server's midnight roll.
>
> **On 2026-08-13 that cost five rows permanently** (SENSEX 09:36, 11:09,
> 12:09, 12:48, 14:03): the API had rolled, the cache was empty, and the
> surviving chain snapshots carry only `spot` and OI — no futures OHLC, no
> volume — so the banded bars cannot be rebuilt. See `DEFERRED.md §0d`.
>
> **The property is restored, forward only.** `eod_capture.py` (`2499a12`)
> writes each session's raw 1-minute tape to `data/backtest/` after the close,
> scheduled Mon–Fri 15:35 IST. From 2026-08-14 the re-score-later guarantee
> above holds again. It does not reach backwards.

### Sample status — counted 2026-08-14, nothing scored yet

| | |
|---|---|
| §5c rows collected | **20** — 9 entries, 11 arms |
| across | 2026-08-10 · 2026-08-13 |
| by index | SENSEX 7 entries + 8 arms · NIFTY 1 entry + 3 arms · BANKNIFTY 1 |
| scored | **0 on disk.** Two 2026-08-13 rows were measured off the live tape before it rolled (HANDOFF 2026-08-14) |
| quarantined §1 rows | 256, `rule != "5c"`, counting toward nothing |

**No rate is to be quoted from this.** `trigger_log.rate_refusal` withholds one
below the floor, and 9 entries is nowhere near it. The bar below is still owed.

### The bar — **OWED BY THE OPERATOR, do not invent it**

The pass criterion must be stated in the terms of the real management —
points per trade, hit rate, or a ratio against the 20-point stop — and that is
the operator's call. The previous draft picked "≥60% / ≥+10 pts at +30m"
without asking, which is the same mistake in a different place.

**Do not read the result before n ≥ 15 on that side.** This is the rule that
matters most in a forward test and the easiest to break: stopping to look the
moment the number is flattering, and calling that the answer, is how a live
sample manufactures the same false positive §5 was written about. n < 15 is
INCONCLUSIVE and gets no verdict, favourable or not.

### What each outcome means

- **BUY passes** — expected; it confirms live what 65 cached sessions already
  said. It is not new information, it is the control on the whole exercise.
  If the BUY side FAILS live, that is the most important result this project
  could produce and the cached verdict has to be re-opened.
- **SELL passes** — the backtest FAILED it narrowly on 2026-08-08 (55.6% /
  +9.35 against 60% / +10). A live pass would mean the two disagree, and the
  answer then is more data, not picking the friendlier one.
- **SELL fails** — it stays exactly as it ships now: drawn because the operator
  asked for it over C3, labelled as carrying no score.

### Not covered by this test

The operator's short EXIT rules (`docs/superpowers/specs/2026-08-08-operator-short-exit.md`)
are unbuilt and two of their parameters are unanswered. This measures ENTRIES
at a fixed horizon, which is the only thing comparable to the buy side's own
scoring. Exits will need their own pre-registration.

---

## 5f. OBSERVATION — both sides under the ADOPTED management (2026-08-08)

**This is an OBSERVATION, not a test.** No pass criterion was set before the
run; the operator asked to see raw numbers first and was told, in the question
they answered, that this is the exact shape §5's stop rule exists to guard
against. It is recorded so nobody later mistakes it for a scored verdict.

Management = `patient="hold"` (hold the stop until VWAP, then trail
band-to-band) — the adopted arm, not the fixed 30-minute exit C13 refuses.
`trail_score.simulate` was made side-aware for this; the BUY path was proved
byte-identical against a baseline captured before the edit (md5
`4a24a97fcd5fb7d6b1846535e9a65bd1`).

NIFTY, 65 cached sessions:

| | n | mean | median | hit | losers |
|---|---|---|---|---|---|
| BUY d3 | 19 | **+0.32** | **+6.90** | 63.2% | 7/19 |
| SELL u3 | 18 | **+10.18** | **−0.75** | 44.4% | 10/18 |

### The mean is a lie on BOTH sides, and that is the finding

| strip the top… | BUY mean | BUY med | SELL mean | SELL med |
|---|---|---|---|---|
| — | +0.32 | +6.90 | +10.18 | −0.75 |
| 1 | −6.99 | +5.05 | +0.65 | −1.00 |
| 2 | −10.09 | +3.20 | −6.99 | −1.10 |
| 3 | −12.72 | +2.05 | −9.37 | −1.20 |

BUY's top 2 trades are +177.5 against a **+6.0 net** — the other 17 sum to
−171.5. SELL's top 2 are +295.1 against a **+183.3 net** — the other 16 sum to
−111.8. Neither side's mean survives its own tail at n≈19.

**The two differ in SHAPE, not size, and that is what matters:**

- **BUY has a centre.** 63% of trades win, the median is +6.90 and it HOLDS as
  winners are stripped (+5.05, +3.20, +2.05). Its mean is eaten by a few large
  losses (−87.5, −69.3, −63.5). The case for it rests on median and hit rate —
  **not on the mean**, which is barely above zero.
- **SELL has no centre.** The median is NEGATIVE and gets worse as winners are
  stripped (−1.00, −1.10, −1.20), with 44.4% hit. Mostly small losses,
  occasionally a jackpot (+172.2 on 2026-06-08, +122.9 on 2026-04-29). Reading
  its higher mean as "better than the buy" is exactly the misread this table
  exists to prevent.

### What this does NOT establish

n=18/19 is far too small to lean on tail-driven means, and no bar was set
beforehand, so nothing here passes or fails anything. It does not overturn C3,
does not promote the sell side, and does not demote the buy side.

**One thing it does flag for the buy side**, and it is new: §1's management
table (+4.8 mean / 56% hit) was measured on the VOID one-candle trigger. On the
CURRENT §5c entries under the same adopted management the mean is **+0.32**.
The scored edge's case is median-and-hit-rate, not mean, and any surface that
quotes a mean for it is quoting the wrong statistic.

**Nothing was re-cut to reach these numbers** — one run, both sides, all three
management arms, reported whole. The verdict route remains live collection
(§5e), where a number cannot be re-cut until it agrees.

---

## 6. Known gap the code cannot yet see

## 5c. PRE-REGISTERED — the operator's ACTUAL d3 rule (written 2026-08-05, UNTESTED)

Registered **before** any scoring run, per §5. **Nothing below is a result.**

**Why this exists.** §1's rule is not the rule the operator trades. `_trigger`
(`band_rotation.py:275`) implements a one-candle setup; the operator described a
two-candle one. §1 is therefore VOID, and this is what must be scored.

**The rule, as the operator specified it.** NIFTY index, 3-min bars, after
**09:25**, **d3 only**:

1. **ARM** — a candle whose **low touches or pierces d3**. *No close-back
   requirement.* That candle is the **reference**; remember its **high**.
2. **RE-ARM** — a later candle printing a **new lower low** becomes the new
   reference. Falling lows collapse into one setup; they do not stack.
3. **TRIGGER** — a candle **closes above the reference candle's high**.
   Entry at **that candle's close**.
4. **EXPIRY** — no trigger within **10 candles (30 min)** → setup cancels.
   *(Assumption, flagged: a new lower low restarts this countdown.)*
5. **STOP** — d3 − 20 pts.
6. **MANAGE** — unchanged from §1: hold the stop until VWAP; past VWAP trail
   band-to-band; from +2σ, 15 pts under the high; flat by 15:15.
7. **RE-FIRE** — after an entry: if **stopped out**, the next setup may arm
   immediately; otherwise **not until VWAP is touched**.

**Predictions, committed in advance:**

1. It fires **less often** than the old rule on the same sessions — a
   close-above-the-high is a stricter second condition than a same-bar reclaim.
2. Its **mean MAE is smaller in magnitude than −20.7**, because entry is later
   and higher.
3. Therefore the **20-pt stop is no longer sized to the adverse swing** and is
   probably loose. (Widening or tightening it stays a risk decision for the
   operator — this predicts the measurement, not the choice.)
4. Hit rate at +30m is **materially above** the ~50% / +0.3 pt control.

**Falsifier:** hit rate at +30m at or below **~55%**, **or** a median at or
below the control, **or** the result collapsing once the single best trade is
dropped (§5 lesson 2).

**Provenance and hazards — record these now, not after the number.**

- The rule was **not** mined from `data/backtest/`; it came from the operator's
  own description. That makes this a legitimate first test rather than another
  slice, so §5's stop-rule is satisfied.
- It is **one** rule with **one** parameter set. Do **not** grid-search the
  10-candle window, the 20-pt stop, or the band. If N is ever varied, **every**
  variant must be reported, never the best one.
- 2026-08-04 sits in the cache and was on screen while the rule was being
  specified. The rule was not derived from it, so it is not disqualified — but
  it is not independent evidence either.

**Data:** NIFTY 3-min bars via `squeeze_score.load` (`vwap_bands` → `resample(3)`
— that order is load-bearing: 0.972 vs 0.948 reversed).

**Scorer:** `run_score.py`, head-to-head against the old rule on identical
sessions, with a real stop applied (`rotation_score.py` is deliberately
stop-free).

### RESULT — run 2026-08-05. NOT falsified, but not for the predicted reason.

`run_score.py` reproduces §1's headline exactly on the old rule's own
population (d3 BUY, first-of-run, post-09:25: **n=18, 72.2%, med +21.00**),
which is what validates the scorer before anything new is read off it.

**NIFTY, 65 cached sessions, +30m:**

| | OLD d3 BUY (§1) | **NEW two-candle** | control |
|---|---|---|---|
| trades | 18 (0.28/session) | **19 (0.29/session)** | — |
| hit | 72.2% | **68.4%** | 49.5% |
| median | +21.00 | **+12.80** | +0.00 |
| MAE median | −22.20 | **−13.90** | — |
| **with the 20-pt stop** | 61.1%, med +15.65 | **68.4%, med +12.80** | — |
| **stopped out** | 5/18 = **27.8%** | **3/19 = 15.8%** | — |
| less the best trade | 70.6%, +18.70 | **66.7%, +11.40** | — |

**Falsifier not triggered:** 68.4% > 55%, median +12.80 > control, and it
survives dropping the single best trade. **The edge is real on NIFTY.**

**Prediction scorecard, scored honestly:**

1. *"fires less often"* — **WRONG.** 19 vs 18. Essentially identical frequency.
   The reasoning (a stricter second condition) was sound but the arming
   condition is looser (a touch, not a pierce-and-reclaim), and the two cancel.
2. *"MAE smaller than −20.7"* — **MIXED.** Median −13.90 (smaller), mean −29.97
   (larger). Outlier-driven; the median is the honest read of "typical".
3. *"the 20-pt stop is loose"* — **SUPPORTED**, by the halved stop-out rate.
4. *"hit materially above control"* — **CONFIRMED**, 68.4% vs 49.5%.

**The finding that matters, and it is not the headline.** On raw forward move
the old rule looks *better* (72.2% / +21.00 vs 68.4% / +12.80). **With the stop
applied — which is how it is actually traded — the new rule wins:** 68.4% vs
61.1%, and it is stopped out **half as often** (15.8% vs 27.8%). Entering later
and higher buys a trade that survives. The operator's rule trades median gain
for durability, which is exactly the trade a real stop rewards.

**Corroborating detail:** the new rule's **+6m is negative** (42.1%, med −2.70)
and only turns at +15m. The trade goes against you first and then works — which
is independent support for §1's measured management finding that moving to
breakeven costs ~13 pts/trade. Do not move the stop early.

**Where it fails, as expected.** BANKNIFTY: 37.5% hit, med −75.90 (n=8) — and
the old rule fails there too (14.3%, n=7). §3's regime map holds; BANKNIFTY
still inverts. SENSEX agrees with NIFTY (58.3%, med +23.28, **0/12 stopped
out**, n=12), though its own control is an odd 42% and the old rule's n=4 there
is not readable.

**Caveats that must travel with these numbers.**
- **n=19.** That is ~1.4 signals a week, matching the operator's own "1–2 per
  week" — but it is a small sample and one bad month would move it.
- Old and new were measured on the **same 65 sessions**, so they are not
  independent samples; the comparison is paired, the significance is not.
- Nothing here tests the **option-leg expression**. The operator trades
  premium-matched legs (ATM when its premium is > ₹100, else strikes > ₹100 on
  both sides), and this scores the **index** only.
### Management, re-run on the new entries (`trail_score.py`, 2026-08-05)

The `"hold"` arm existed in `simulate` from the start but was never wired into
`main` — so the operator's OWN chosen management was the one arm never printed.
Now wired, and run against both rules' entries.

**Pooled d3, all three indices** (pooling is a warning, not a result):

| entries | arm | mean | **median** | **hit** | scratches |
|---|---|---|---|---|---|
| OLD one-candle (n=29) | ladder | +3.6 | −9.0 | 41% | 0 |
| | patient | +0.1 | −9.0 | 28% | **6** |
| | hold | +4.5 | −15.2 | 48% | 0 |
| **NEW two-candle (n=39)** | ladder | +33.2 | +1.8 | 54% | 0 |
| | patient | +32.3 | +0.9 | 51% | 0 |
| | **hold** | +31.9 | **+6.9** | **59%** | 0 |

**Two things fall out, and they point the same way as §1's original management
finding rather than against it.**

1. **The new entries are better under EVERY arm.** Every OLD median is
   negative (−9.0 / −9.0 / −15.2); every NEW median is positive
   (+1.8 / +0.9 / +6.9). The entry rule, not the management, is what moved.
2. **`hold` buys consistency, not size.** It has the best hit rate (59% vs 54%
   / 51%) and much the best median (+6.9 vs +1.8 / +0.9), but the *lowest*
   mean (+31.9). Leaving the stop alone until VWAP wins more trades and gives
   up some tail. On NIFTY alone (n=19) the same shape: hold 63% hit and +6.9
   median against ladder's 58% and +3.2, while ladder's mean is higher (+4.8
   vs +0.3).

**`patient` produced 6 breakeven scratches on the old d3 entries and `hold`
produced none** — a direct, independent replay of §1's measured "moving to
breakeven costs ~13 pts/trade". The operator's instinct to leave the stop alone
is supported by a second, separate measurement.

Also visible: `hold`'s median exit rung is **u1** on NIFTY and SENSEX where
`patient` stops at **vwap**. Not touching the stop lets the runners run.

BANKNIFTY is negative on every arm (hold worst, −74.4, n=8). §3's regime map
holds.

**Still not measured:** the option-leg expression. Every number above is the
index. The operator trades premium-matched legs (ATM when its premium is
> ₹100, else strikes > ₹100 on both sides), and that has never been scored.

---

## 6. VERDICT — v3's charting foundation (2026-08-05)

The throwaway `/proto` spike ran against live bars and the 04-Aug fixture.
**Decision: keep `candl`.** Not because lightweight-charts failed — it passed
all three pre-registered proofs — but because the rubric asked the wrong
question.

### The three proofs, scored against the rubric written before the run

| proof | verdict | evidence |
|---|---|---|
| 1 · filled σ envelope | **PASS** | `drawRibbon` reused with **zero body changes** — `diff` vs `LevelsOverlay.ts:227-271` is exactly **one line** (`conv: Converters` → `conv: Conv`). Five annuli, distinct hues. `autoscaleInfo` exists in v5.2.0 and keeps ±3σ in view. |
| 2 · synced OI pane | **PASS** | `chart.addSeries(LineSeries, {}, 1)` creates the pane outright: `panes()` → 2, series `[2,1]`, 385 points, shared time axis, **zero glue code**. |
| 3 · rotation pill | **PASS** | Anchored by `logicalToCoordinate` + `priceToCoordinate`; 21 pills on their own candles at their own σ levels. **No rAF loop and no frame-skip signature needed** — the chart's own paint drives it. |
| time axis | **PASS** | `LWC holds 2026-08-04T14:51:00.000Z` for the bar the payload calls `14:51`. Machine-timezone independent (verified at offsets 0 and −330). |
| gates | **PASS** | tsc 0 · build 0 · pytest 278. |

### Why the verdict is still "keep candl"

**Drawing tools — the axis the rubric never covered.** `candl` ships **61**
tools with a full lifecycle API (`setActiveTool` / `setDrawings` /
`onDrawingsChange` / `onSelectionChange` / `setMagnet`). lightweight-charts
ships **zero**, by design — every tool would be hand-built as a primitive, with
hit-testing, drag handles, selection, persistence and undo.

The operator trades ICT/SMC. Trendlines, channels, fibs and boxes are the
method, not decoration. Verified working on 2026-08-05 via `ProtoDraw.tsx`.

**The thing nobody had noticed:** ui-v2 turns **none** of those 61 on. The only
app-side reference to the entire drawings module is `LevelsOverlay.ts:5`
importing the `Converters` *type*. The capability has been one toolbar away the
whole time — which is why the operator could never draw on their own chart.

### What the spike genuinely established (worth keeping)

- **`LevelsOverlay` was never candl-coupled.** Its whole runtime surface is two
  calls (`getMainConverters`, `getMainPaneRect`) and two methods off them. The
  migration was always cheap — it simply is not worth making.
- The **series-primitive + 2-method adapter** pattern works, if this is ever
  revisited. Use `logicalToCoordinate`, **not** `timeToCoordinate`: the latter
  returns null off-screen and `drawRibbon` treats non-finite as a run break, so
  the envelope would fragment under pan.
- lightweight-charts renders **UTC only**. Bars carry `"HH:MM"` IST and no
  epoch, so stamps must be built as *the epoch whose UTC clock is the IST wall
  clock* (`protoTime.ts`). Naive `dayBase()/1000` puts the axis 5:30 out.

### Costs that going LWC would have had to pay

61 drawing tools · the replay cursor (`candl` has native `setReplayCursor`
driven at 25× / 40 ms; LWC has no equivalent) · an OHLC legend (LWC draws none)
· `LegChart`, never proven · +55 kB gzip.

### Not measured — do not read this verdict as covering them

- The **replay cursor** port (the operator scoped the spike to three proofs).
- **`LegChart`**: its σ bands are plain *lines*, plus seven pivot lines, its own
  OI pane and a `map[]` for skipped bars. Three passing proofs say nothing
  about it.
- **50 of the 61** drawing tools. Eleven were exercised.

---

## 7. Known gap the code cannot yet see

The operator reads *"is price rejecting the band or walking along it"* off the
chart in one second (Kite screenshots, RELIANCE 31-Jul and 3-Aug, 2026-08-04).
Nothing in the repo measures band-riding vs band-rejection. The one attempt
(§2.2) was falsified, but the attempt was flawed rather than the idea being
disproven. **This is the most promising un-encoded piece of the operator's
read** — if it is retried, it must avoid a lookback that silently excludes the
morning, and it must be pre-registered.
