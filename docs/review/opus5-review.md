# Independent review — TapeMap, the brain

**Reviewer:** clean-room read, 2026-09-23, market open, server live on :8765.
**Method:** Python modules at the repo root, `CLAUDE.md`, `START-HERE.md`,
`context/research-findings.md` in full, `context/DEFERRED.md`, `HANDOFF.md`,
the mechanism sections of `docs/superpowers/specs/`, and ~20 live GET payloads
pulled between 10:20 and 10:32 IST. No POST was made. No file was modified.

**What I deliberately did not open**, on instruction: `ui/`, `ui-v2/`,
`docs/mockups/`, `chrome-ext/`, any `.html`/`.tsx`/`.jsx`/`.css`, `docs/*.png`,
`context/ui-audit.md`, `context/ui-context.md`, `context/ui-v2-dashboard.md`,
and `orderflow-desk/src/shell/`. I also **skipped §B–§G of
`docs/superpowers/specs/2026-09-16-operator-desk-design.md`** (three screen
layouts), **§F of the prints, order-flow-levels, upstox-tape and
convergence-chips specs** (drawing/tab sections), and the `ui-v2` file paths
quoted inside `research-findings.md` §1b and §6. I read §1b's *content* —
your Kite zone rule — which is load-bearing and which I have used. I have
never seen a screen for this engine.

---

## Ratings

| # | axis | score |
|---|---|---|
| 1 | Answers a trader's actual questions | **6 / 10** |
| 2 | Epistemic honesty | **8 / 10** |
| 3 | Coherence | **4 / 10** |
| 4 | Signal quality | **6 / 10** |
| 5 | Completeness against its own thesis | **4 / 10** |
| 6 | Leanness — what should not be here | **3 / 10** |
| | **Overall** | **5.5 / 10** |

A first-rate epistemology wrapped around a second-rate decision surface, with
at least one live number that would cost money. The document
`research-findings.md` is better than most professional research desks produce.
The screen-facing object it feeds cannot name the one thing the doctrine says
decides everything.

---

## 1 · Does it answer a trader's actual questions? — 6/10

**What earns the 6.** `frame.py` is the right idea, executed with discipline.
It composes and never measures; the five objects (`where` / `trapped` /
`walls` / `tape` / `setup`) map almost exactly onto questions 2–4 of your own
list; every nullable field has a sibling `*_why`; the empty shapes are module
constants so the hole path and the happy path cannot drift. `visit.py`'s
latched reach, `signals.py`'s ballot and `fronts.py` are all built to answer a
question a trader asked, not a question that was computable.

**What costs it 4.** Three of your five questions are not answered by the
object designed to answer them, and two of those are structural rather than
transient.

**"What gear is the market in" — permanently null on the frame.**
`server._book_for` hardcodes `senses = None` (server.py:1073). `frame._trapped`
reads `book["senses"]["gear"]`. So `trapped.gear` is `null` with
`gear_why: "senses not answered"` on every request, forever. Live at 10:32:

```
"gear": null, "gear_why": "senses not answered", "gear_tag": "I"
```

The doctrine's sentence is *"every play is legal in exactly one gear."* The
gear is available — `/api/senses.read["NIFTY-23400CE"].gear` = `TRANSITION`
right now — and the composed read does not carry it. The docstring explains
why the composer must not re-derive the reading; that reason is sound and the
consequence was never followed through. It is one wire.

**"Is today a day to trade at all" — cannot ever leave PATA NAHI.**
`gate.py` is well designed (a hole *wins*, which fixes a real P0). But
`_book_for` also passes `"ivrv": None` unconditionally, and `gate.state`
appends `"event calendar not wired"` on every call with no way to satisfy it.
So the level is `PATA NAHI` by construction on every frame of every session.
That is honest and it is also useless: a gate that can only ever say "don't
know" is not a gate, and `would_be: "TRADE"` sitting beside it is the number a
tired trader will read.

**"Who is trapped and what will they be forced to do" — the first half only.**
`trapped.writers` names a side and a worst leg. Nothing anywhere converts that
into *what they must do and where that takes price*. `warmap.runways` computes
exactly this — fuel per point to the next level, itemised by strike — and it
is on `/api/warmap` only. It is not on the frame.

**Question 5, "am I still safe", is not asked at all.** `exit_why` is a re-fire
lock, START-HERE §0.5 says so, and the management arm that `trail_score`
measured as the winner (hold the stop to VWAP, then trail band-to-band; from
+2σ, 15 under the high) exists in no live module. The tool tells you when to
get in and has nothing to say once you are in.

**And the ratio.** Against those gaps: a VPIN fast line, a paper book with a
short-variance hedger, an impact model, a runs detector, a ladder-agreement
gate, 13 desk structures with statuses, a convergence-chip layer. None of them
answers any of your five questions. The things that got built are the things
that were buildable.

---

## 2 · Epistemic honesty — 8/10

**This is the best thing in the repo and it is not close.** Evidence, all
verified:

- `research-findings.md` §5d records a **FAIL** that missed the pre-registered
  bar by 4.4 points of hit rate and **0.65 of a point** of median, states "no
  promising, no directionally right, no re-cutting to another horizon", and
  does not rescue it. I have not seen that done before.
- §1 is marked **VOID** — *"correctly measured, wrong instrument"* — rather
  than quietly deleted, and the distinction between void and disproven is
  maintained throughout.
- §1b corrects a mistake **in place, naming the reasoning error**, including
  that the tool's own correction was then written into memory and acted on.
- §1d was corrected at 01:10 *"before any row was logged against it"*, with the
  looser reading deliberately chosen because it is the **harder** test for the
  gate. Recorded rather than silently reconciled.
- `/api/signals` returns `no_rate_why` at n=27 scored entries and refuses the
  rate, with §5e's "owed by the operator" as the reason.
- `gate.py`, `frame.py`'s `_EMPTY_*` constants, `signals.py`'s three-valued
  votes (`True` / `False` / `None` with `why`), `fronts.fade_gate`'s "a missing
  input is PATA NAHI, never legal" — the three-sentence rule is in the types,
  not in discipline.
- `signals.py` enforces §H.1 **in the function signature** — `walls_rows` is
  not a parameter, and `_only_oi` raises rather than quietly voting. Putting a
  guardrail where it cannot be forgotten is the right instinct.

**The two points off are for three live cases where absence renders as
silence**, which is the one thing rule 6 forbids. All three are in §D below:
the silently dropped levels, `/api/oiflow`'s untagged `sentiment`, and the
drag day trace. The doctrine is near-perfect; the execution leaks in exactly
the places nobody re-checked.

---

## 3 · Coherence — 4/10

Modules do not agree, and there is no test anywhere that asserts two modules
computing the same quantity produce the same answer. Five live disagreements,
all pulled from one server at one minute:

**a. Four regime vocabularies on one index.** At 10:32, NIFTY:

| source | field | value |
|---|---|---|
| `/api/desk` | `regime.state` | `AMPLIFYING` |
| `/api/desk` | `view.gear` | `TRANSITION` |
| `/api/frame` | `breadth.regime` | `FLOOR` |
| `/api/frame` | `trapped.gear` | `null` |
| `/api/senses` | `read[…].gear` | `TRANSITION` (per leg, and `UNKNOWN` for every BANKNIFTY leg) |

Two of those vocabularies do not intersect at all. `senses.read` returns a
gear **per option leg**, which is a category error on its face — the gear is a
property of the market, not of one strike.

**b. The lot size is 65 and 5 on the same server.** `/api/tape` → `lot: 65`.
`/api/desk` → `lot_size: 5, lot_size_src: "measured"`. See §D1.

**c. Two PDH rows and two PDC rows, 45 points apart, same label.**
`/api/frame.walls.rows` at 10:20 carried:

```
PDH 23522.8  (state IDLE)     PDH 23477.6  (state null)
PDC 23410.0  (state null)     PDC 23362.8  (state IDLE)
```

One pair comes from `levels.py` (index prior-day candles, `[M]`, basis-shifted
+33.8 by `frame._walls`); the other from `structure.prior_day_hlc`, which
inverts the futures floor pivots and is added to the same futures-frame axis
**with no basis applied**. `_walls`'s own docstring says *"One axis, futures
frame."* Two of the three prior-day levels a retail chart draws appear twice,
at two prices, both labelled the same, with nothing on the row saying which is
which.

**d. Two state machines on one object, different vocabularies.** At 10:32
`setup.state = "WAITING"` sits beside `setup.signal.state = "PATA NAHI"`.
The spec supersedes one with the other; the frame ships both.

**e. "Trapped" means two different things.** `frame._trapped` = `max(pain)`
over every leg in the heat map. `trapped_inventory.py` / `chainside.py` =
something else entirely. `fronts.py`'s own docstring documents that
`frame._trapped` returned **PE 23700 at confidence "low"** — a strike nobody
carries margin on — on the morning PE 23400 broke. That module was written
*because* the other one is wrong, and the wrong one is still on the frame,
still first, still called `trapped`.

**f. The desk contradicts itself in one payload.** NIFTY: `game:
"STAND_ASIDE"`, `view.why`: *"gear is TRANSITION… BOTH games lose here, so
nothing is named best however well it prices"* — and immediately below,
`vertical_relative_value: status DEPLOYABLE, edge 3.48`. This is precisely
the "two modules, one minute, opposite instructions" failure §1d was written
to fix, recurring in the other half of the stack.

Also: every `margin` on every desk candidate is `null`, while the desk's stated
ranking is *"edge per rupee of margin"*. The ranking cannot be computed and the
rows are ordered anyway.

---

## 4 · Signal quality — 6/10

**Load-bearing:**

- **The zone on d2/u2.** Correcting from the line to the zone is the single
  most important thing that has happened to this tool. §1b's evidence is
  overwhelming and the machine now runs `band="d2"`/`"u2"`.
- **`visit.py`.** The latched reach and the `arm.first_t` visit key are a real
  defect fix that protects months of record: keying on the live `ref_i` split
  one setup into several rows every time a lower low printed. The reasoning
  about flooring the end-of-visit rule at the machine's own drop is careful
  and correct.
- **The ballot's threshold of one.** Derived from an actual bucket table
  (0-of-4 worst, 1-of-4 best, 2-of-4 *not* better and worse on adverse
  excursion), with "some gate beats no gate, a second stacked gate bought
  nothing" stated plainly, and OI excluded from counting alone because it is
  true 3 times in 4. That is a real finding honestly used.
- **`fronts.py`.** Encodes your stated rule, ranks by **peak** OI not current
  for exactly the right reason, is extension-independent, and rides alongside
  the forward log without suppressing a row. Best code in the repo.
- **`taps[].ex`.** Each zone visit today with its +5/+15/+30-bar excursion.
  This is the only place the tool describes what today's own setups paid
  without printing a rate, and it is the right shape.

**Decoration:**

- **The confirm layer does not exist.** `setup.confirm` is permanently
  `"not wired"`. The signal-layer spec already concedes it *"is a no-op wearing
  a gate's clothes"* and that on a single index series it is structurally
  `UNKNOWN` and always will be. It should be deleted from the setup object, not
  left as a field.
- **The DEPTH vote ships negative.** The spec's own study: present n=4, VWAP-hit
  **25% vs 70% absent**. It ships with its kill clock already running, which is
  honest, but it is a vote whose only evidence points the wrong way.
- **`walls.cap = 3` while 50 rows ride the wire.** And on today's rows, `pain`
  is `0.0` on every single PE row, `tests`/`last_outcome` are `null` on every
  row that is not a warmap level, and `size`/`since`/`leaned` are `null` on
  every OI row. Most of the ladder's columns are structurally empty.
- **`aggressor`.** `{side: "buyers"}` off the sign of summed delta — the exact
  "buyers vs sellers" framing the doctrine rejects, and one of the few fields
  on the frame with no tag and no `why`.

**The gate's real problem is not its thresholds, it is its question.** Your
rule is comparative — *"which side stops FIRST increasing and then unwinds"*.
`fronts.broke()` implements that comparison, correctly, and is exposed on
`/api/oihist` only. `fade_gate()` asks a **unilateral** question: is *my*
defender still building. Those give opposite answers right now. See §D2.

---

## 5 · What is missing that the thesis demands — 4/10

**a. The comparative front read, on the frame.** `broke()` exists, is right,
and reaches no screen and no gate.

**b. What the forced side will be forced to *do*.** Trapped inventory is the
fuel; the tool names the fuel and never names the direction or the distance.
`warmap.runways` already computes fuel-per-point to the next level. It is not
composed into the read.

**c. Band-riding vs band-rejection.** `research-findings.md` §7 calls this
*"the most promising un-encoded piece of the operator's read"*. §1b's
2026-08-14 observation found that `rng_r` — already in every `ctx` payload —
separated the morning (all six d2 tags rejected) from the afternoon (four
u2/u3 tags, none rejected, price walked the outside of the band) cleanly, while
`trap` returned SUSPECT on all ten and discriminated nothing. That is the
candidate mechanical answer to §1b's open question **(c)**, *"if market
condition is right"*. Five weeks on it is still not pre-registered and still
not measured, and §1d answered (c) with a *different* mechanism instead. Both
can be right; only one has been written down.

**d. The exit.** See §1. Your question 5 has no module.

**e. A same-quantity reconciliation test.** One test that asserts PDH from
`levels.py` equals PDH from `structure.prior_day_hlc` (after basis), and that
`desk.lot_size` equals `/api/tape.lot`, would have caught two of the three
dangerous findings below on the day they landed.

**f. A counter for the gate.** §1d's falsifier is stated in **counts** — *"the
gate marks illegal fewer than 1 in 10 fade arms over 10 sessions"*. There is
nowhere on the wire that says how many arms it has marked. Refusing to print
rates is right; it should not have become refusing to print arithmetic.

---

## 6 · What should be deleted — 3/10 on leanness

Named files, in order of confidence:

| delete | lines | why |
|---|---|---|
| `backtest.py` | 288 | fetches through `dhan_fetch`; Dhan's data API lapsed 2026-08-05 so it **cannot run**, and §5's stop rule forbids what it does |
| `trader.py.bak-before-shortstop` | 28 KB | a `.bak` file in the tree |
| `signal_review.py` | 308 | post-mortem scorer for the engine event stream, which §2 scored at −0.1 / −6.2 against a +4.1 do-nothing control and defaulted OFF |
| `run_score.py` | 230 | cache scorer under a stop rule; its last legitimate run was §5d, which is closed |
| `squeeze_score.py` | 386 | same — it survives only because `trigger_log` imports `load`. Lift that one function into `trigger_log` and delete the rest |
| `oi_dwell.py` + `replay_dwell.py` | 340 | a **mutual import pair** (`oi_dwell` ← `replay_dwell` ← `oi_dwell`), and `oi_dwell` prints BULLISH/BEARISH off aggregate `(put−call)/max(…)` — the aggregate read your own 2026-09-22 rule rejects |
| `chain_metrics.rows()`'s `sentiment` and `strength` columns, and their `/api/oiflow` rendering | — | an **untagged direction verdict from aggregate OI**, see §D4 |
| `structure.py` SMC layer | 543 | §2: 4× over-fires vs LuxAlgo, ⅔ UNKNOWN, default OFF. It reaches the live path only via `prior_day_hlc`, which is the function producing the duplicate PDH/PDC rows. Lift that function and drop the rest |
| `TAPEMAP_BROKER` default `"dhan"` (server.py:2629) | 1 | the default broker is a dead data source, and START-HERE says a dead source *"looks exactly like a quiet market"* |

**Not a delete, a scope call: the desk half.** `desk.py` (80 KB) + `trader.py`
(60 KB) + `surface.py` + `book.py` + `quoting.py` + `hedge.py` +
`direction.py`. Nothing in it reaches `frame.build`. It has no track record
(START-HERE §7 says so). It carries the lot-size defect. It ships a 19-row
catalogue of which 16 rows are `BLOCKED` on NIFTY and 17 on BANKNIFTY. Either
it is composed into the one read object or it is a second product on the same
port, and right now it is the second thing while being maintained as if it were
the first.

---

## The three most valuable things in here

**1. `context/research-findings.md`.** Not a module. It is a genuine
pre-registration record — falsifiers committed before results, a FAIL that
missed by 0.65 of a point and was not rescued, corrections made in place with
the reasoning error named, a stop rule that is actually obeyed. It is the
reason this tool is worth repairing rather than replacing, and it is the only
asset here that a competitor could not rebuild in a month.

**2. `fronts.py` and `/api/oihist`.** ~250 lines that encode your actual stated
rule, rank by peak rather than current OI for exactly the right reason, survive
a dead extension tab, and stamp the forward log without suppressing a row —
so the gate can be judged later from rows logged forward rather than a re-cut
cache. That last property is worth more than the gate itself.

**3. `visit.py` + `taps[].ex`.** The latched reach and the first-arm visit key
protect months of record from a defect that was silently doubling rows. The tap
excursions are the only honest performance surface in the stack: today's own
visits, with what each one paid at +5/+15/+30 bars, described and not scored.

---

## The three most dangerous things — each could put you in a position

### D1 · The desk's NIFTY lot size is **5**, and it is tagged `measured`

`/api/desk?capital=1000000`, live:

```json
"lot_size": 5, "lot_size_src": "measured"
```

`/api/tape?idx=NIFTY` on the same server, same minute: `"lot": 65`.

`desk.lot_size_from_chain` takes the GCD across every OI and volume on the
chain. Today that GCD came back **5**. The guard written to catch exactly this
is `MIN_DERIVED_LOT = 5` and the comparison is inclusive, so the degenerate
value passes by one. Every margin, every sizing figure, every rupee-denominated
number the desk produces for NIFTY is **13× too small**, and it wears `[M]` —
the strongest confidence tag this stack has. The fallback table right beside it
has the correct 65.

The docstring says *"deriving it is not merely tidier than a table — it is the
only version that cannot rot."* It rotted in a way a table cannot: silently,
inside the session, wearing the measured tag.

**Fix:** make the guard exclusive and cross-check the derived value against
`LOT_SIZE`; when they disagree by more than a factor, refuse both and say so.

### D2 · The fade gate answers the wrong question, and it is answering it wrong right now

Live at 10:32, NIFTY, `/api/oihist` and `/api/frame` on the same server:

```
fronts:  CE 23400  UNWINDING   peak 10:15   −7.21L off peak   slope −650,390
         CE 23500  STALLED     peak 10:15
         PE 23400  BUILDING    peak 10:32   slope +2,019,355
         PE 23300  BUILDING    peak 10:32
broke:   CE 23400                                    ← /api/oihist only
```

Your rule, in your words: *"always check **which side stops first** increasing
their positions and then unwinding."* That side is **CE**. Call writers peaked
at 10:15 and are giving inventory back — covering a short call is buying, so
the pain relieves **upward** — and the sell zone is **7.4 points above price**.

What `/api/frame` says at the same instant:

```json
"setup": { "side": "buy", "state": "WAITING",
           "gate": { "legal": true, "why": "PE 23400 still building",
                     "side": "buy", "defender": "PE" } }
```

Two failures compounding:

1. **`fade_gate` is unilateral where your rule is comparative.** It asks "is
   *my* defender still building" and never asks which side broke first.
   `broke()` — the function that does ask — is called in exactly one place,
   `server.py:2031`, and appears on no composed object.
2. **`_pick_side` defaults to `"buy"` when neither pocket is touched**
   (`frame.py`, `_pick_side`: *"if neither is active, buy is the default
   read"*). So the side the gate is asked about is an arbitrary default — while
   `where.edge` on the **same object** says `{"side": "sell", "d": 7.4}`.

The net effect on the face is a green-lit BUY fade, justified by the defending
put front, at the moment your own rule points at a broken call front and an
upward relief into a sell zone seven points away. That is not a missing
reading; it is the opposite reading, stated confidently.

### D3 · `/api/drag`'s day trace pools two sessions and reports the other one's peak as today's

`_SENSES["drag_day"]` is a `deque(maxlen=3000)` and **has no day roll** — there
is no line anywhere in `server.py` that clears it. The save is
`day_state.save(time.strftime("%Y-%m-%d"), …)` (server.py:2779): the
**filename** rolls at midnight, the **ring** does not. A process alive past
midnight — and `HANDOFF.md` records that you review after the close, often past
midnight — writes yesterday's ring into `day_<tomorrow>.json` stamped
`"day": "<tomorrow>"`. `day_state.load`'s same-day guard checks the stamp the
writer applied, not the day the rows were observed on, and the rows carry only
`"HH:MM"` with no date. Nothing downstream can separate them.

Measured on the live server, twice. At **10:20**: 61 downsampled points, the
first 52 spanning **09:17 → 15:26** (a completed prior session), the last 9
spanning **09:19 → 10:15** (today). At **10:39**, still mixed — points 0–49
run **09:17 → 15:29**, points 50–60 run **09:23 → 10:36**:

```
09:17 09:24 09:32 … 15:14 15:22 15:29 | 09:23 09:30 09:37 … 10:29 10:36
                     ^ prior session    ^ today, no separator, no tag
```

And on both pulls:

```json
"hi": { "t": "10:25", "frac": 17.8557, "side": "ce" }
```

A **17.9×** buyer's tax, headlined as the day's worst, at a clock time that had
**not yet occurred** when it was first read at 10:20. It is a prior-session
reading, and the `day.restored: true` flag next to it says only that an earlier
process *on the same day* gathered some rows — which is not what happened.

It clears only when `maxlen=3000` finally evicts the old rows, which at today's
~5–6 rows per minute lands near **midday**. So the trace is wrong for the whole
morning — the hours the drag number is most likely to be consulted — and looks
clean by the time anyone goes back to check.

`day_state.py`'s own docstring names this exact failure as the thing it
prevents: *"tomorrow morning starts cold instead of opening on yesterday's tax
as if it were today's… a stale series that renders is worse than an empty one
that says so."* The guard is in the right place and checks the wrong field.

**Fix:** stamp each row with its date, or clear `drag_day` on the day roll and
re-derive the save's day from the rows rather than the wall clock.

---

## Two more, one notch below

### D4 · `/api/oiflow` prints `sentiment: BULLISH / BEARISH` off aggregate OI

`chain_metrics.py:501`. `diff = put − call` summed over **all 17 strikes**,
`sentiment = BULLISH when diff > 0`. No `[M]`/`[I]` tag, no `why`, no kill
clock, and it is exactly the aggregate read your 2026-09-22 rule rejects — the
23,700 PE writers `fronts.py` was written to exclude are in that sum with full
weight. The adjacent `strength` column is §5b's pre-registered metric, which
§5b states in terms needs *"~15 sessions before any number is worth reading"*
and has never been scored. It is rendered as a labelled verdict.

### D5 · Three levels are silently dropped from the ladder

`sequence.py:207` builds its key as `f"{kind}@{px:.1f}"`. `frame.py:307` looks
it up as `f"{kind}@{px}"` — raw repr. Any level whose price is not already
one-decimal-exact misses, and `frame._walls` treats the miss as a legitimate
absence: *"no machine state: the chart draws the line; not a row."* Today that
silently removes **PDL 23285.75**, **PWH 23592.85** and **OPEN 23352.15** —
the prior-day low and today's open, two of the most-watched intraday levels —
from the wall ladder, with no `why` anywhere on the payload. Rule 6 in
`CLAUDE.md` exists for precisely this and the bug sits under its own comment.

---

## Where I disagree with the doctrine

**1. "Shadow, with a 30-session kill clock" has become storage, not testing.**
VPIN, `regime.py`, `direction.py` and the whole war map are shadow with
declared kill clocks. Those clocks live in docstrings and are reset in practice
by every restart and rewrite; VPIN's started 2026-08-25 and `/api/vpin.pct` is
`null` on the slow line right now. Shadow is the correct default — `regime.py`'s
argument that a gate is the only module that can make the system *worse* than
doing nothing is the single best paragraph of engineering prose in this repo,
and the 2026-08-19 σ-width gate that your own 15 sessions reversed proves it.
But a clock that does not survive a restart is not running. Either each shadow
module carries its own on-disk session counter and prints *"day 14 of 30"*, or
the honest statement is "we are not testing this", and it should say so.

**2. "Aggressor, not buyers vs sellers" is stated and not implemented.** The
doctrine's real question is *whose aggression is failing* — heavy delta one way
with price refusing to follow. The tool has both halves and never joins them:
`where.hour` carries `{net: −3.0, travel: 155.0}` (155 points of travel for 3
points of net — a textbook failing-aggression signature) and `tape.aggressor`
independently reports `"buyers"` off the sign of summed delta. Joining those
two is one function and it is probably the highest-value unbuilt thing here.
Meanwhile `aggressor` as shipped is the framing the doctrine explicitly
rejects, with no tag on it.

**3. "Never print a rate" is right and has over-reached into arithmetic.** The
refusal is correct for the §5c/zone populations. But it now means nothing on
the wire can say "the gate has marked 40 arms illegal and 3 legal today", which
is a **count**, is exactly what §1d's own falsifier is written in, and is the
only way you will ever know whether the newest module binds. Today the forward
log carries `gate` on **2 rows out of 1,855**.

**4. A small one, in the doctrine's favour.** "Being flat is the most common
correct answer, and the setup that funds the others is the skip" is correct and
the tool does not honour it. `setup.state: "WAITING"` is the same visual weight
as `"ARMED"`, and the default `side: "buy"` manufactures a lean where there is
none. The skip should be the loudest thing on the screen, not the quietest.

---

# Part 2 — the screen

**File:** `docs/review/opus5-screen.html`. Single file, no build step, no
external dependency, renders by double-click. Every number in it was pulled
from the live API at **10:32 IST, 2026-09-23** and nothing is invented;
where a value is missing it is missing in the live payload too, and the page
says which of three reasons applies.

## The shape: one column, docked

You sit in front of it with your broker chart open elsewhere, so this is not a
dashboard — it is a **rail**. One column, 480 px, full height, meant to live
down one side of the screen beside the chart. It never needs the width a chart
needs because it never draws a chart: your chart is the chart.

Your chart is white and red/green is spoken for there, so this rail is **dark**
and uses **no red and no green anywhere**. Two hues carry all meaning:
**amber = the side that is acting or forced**, **violet = the side that is
defending**. Everything else is grey. You can never confuse a mark on the rail
with a candle on Kite, and a colour on the rail never means "up" or "down".

## The five bands, in your order

**1 · THE GATE — is today a day to trade at all.** Largest type on the page.
Today it reads **PATA NAHI** in that largest type, with its four holes listed
one per line, each with its own reason. `would_be: TRADE` is rendered small,
greyed, and labelled *"not the answer — what the answer would be if the holes
were filled"*. **The hole occupies the same real estate the answer would
have.** That is the single most important decision on this page: absence is
loud, not quiet. A screen where "don't know" is small and "TRADE" is big
teaches you to read the wrong field.

**2 · THE GEAR — what gear is the market in.** Same treatment. Today the
frame's gear is `null`, so it renders as a dashed box the size of the word
`CASCADE` containing *"CAN'T CHECK — the composed read is not given the senses
reading (server `_book_for` passes `senses: None`)"*. Beside it, greyed and
labelled as a different question, the two regime words that **are** answered —
`FLOOR` from the engine and `TRANSITION` per-leg from senses — with a line
saying they are not the same vocabulary and do not substitute.

**3 · WHO IS TRAPPED — the fuel.** The section this engine earns its thesis on
and currently under-shows. One sentence at the top, in amber, the size of a
headline: **"CE 23400 broke first at 10:15 — short calls giving inventory back
— relief is UP."** That is `fronts.broke()`, which today reaches no screen.
Below it the four fronts as horizontal bars: build, distance from own peak,
peak time, state. CE amber (acting), PE violet (defending). Then the window
read — the last three minutes of OI change — because "what changed in the last
three minutes" is the only OI number that is not a slot machine.

**4 · WHERE, AND THE PLAY.** A **σ rail**, not a chart: a single vertical axis
from d3 to u3, with price, VWAP, the two azure zones drawn as bands, and the
nearest walls pinned at their own prices on the same axis. This is the one
place walls, zones and price share a coordinate. Distances in points to both
edges, always.

Under it the play. When there is none — as now — it says so in one line with
the two numbers that decide when there will be: *"nothing. buy edge 43 below ·
sell edge 7.4 above"*. When there is one it carries side, state, candles left,
the reference price, the **frozen** falsifier (frozen at the arm bar, with both
values shown if the live band has drifted more than 0.25σ), the ballot as
`n of m measurable` with each null vote named and its reason, and the fade
gate — **reported as the comparison your rule asks for, not the unilateral
one**: defender state *and* who broke first, and a visible DISAGREE flag when
they point opposite ways. Today they do, and the page shows it.

Then today's tap ledger: every zone visit today with its ±5/15/30-bar
excursion. Four rows, real numbers, no rate, no average, no verdict.

**5 · AM I STILL SAFE.** Bottom strip, small but never hidden: feed age, book
coverage, whether this frame was written to the record, and the drag number
with its anchor source. The day-peak drag is rendered as a **NOT SHOWN** hole
with the reason from D3 — a live demonstration of the grammar, on a real case.

## Hierarchy

| tier | what |
|---|---|
| **Largest** | the gate word, the gear word (or its hole), and the "who broke first" sentence |
| **One glance** | the four fronts, the σ rail with distances, the play line, the safety strip |
| **Behind a keystroke** | `1` the full 50-row ladder · `2` the watch list · `3` the tap ledger in full · `4` the coverage lists (reconstructed / not-reconstructable, as two separate lists, never merged) · `5` the vote detail and the record row |

Native `<details>`, bound to number keys. Nothing behind a key is needed to
make a decision; everything behind a key is needed to check one.

## What I deliberately left off, and why

- **Every price that ticks and changes nothing.** LTP to two decimals, PCR,
  GEX, max pain as a headline, VPIN's number, IV per strike, cvd/delta
  magnitude, the paper book's P&L, the 13-structure desk catalogue. Each of
  those updates constantly and changes no decision on this screen. Per your
  own rule, they are a slot machine.
- **`/api/oiflow`'s `sentiment`.** An aggregate direction verdict that your
  own OI rule rejects (D4).
- **Red and green**, everywhere. Your chart owns them.
- **Any rate, win rate, expectancy or confidence score.** The tap ledger shows
  rows; it computes no average.
- **The engine's `BULLISH`/`BEARISH` play strings.** §2, scored below a
  do-nothing control.
- **`setup.confirm`.** It is permanently `"not wired"` and structurally cannot
  work on a single index series. A field that will never have a value is not a
  hole, it is a promise; it comes off.
- **A default `side`.** When neither pocket is touched the play line says
  *"neither"* and names both distances. It does not pick buy.

## How state, uncertainty and absence are shown

Four rules, applied without exception:

1. **`[M]` measured** renders at full brightness. **`[I]` inferred** renders at
   65% opacity with a hairline underline. Every number carries one.
2. **Three absences, three words, never merged** — and the word *is* the
   signal, so it survives in greyscale:
   - **NOTHING FOUND** — we checked, the answer is negative. (e.g. "no level
     broke today, live or in the replay")
   - **CAN'T CHECK** — an input is missing, and **which** input is named.
     (e.g. the gear)
   - **NOT SHOWN** — we have a number and will not print it, with why.
     (e.g. the day-peak drag)
3. **A hole is a dashed box the size of the value it replaces**, containing its
   reason in italic. Never a zero, never a bare dash, never a confident default.
4. **Backfilled evidence gets a hatched left border** and is never counted
   toward anything that rings. Observed and reconstructed are drawn differently
   and never summed.

One rule I added because the code needs it: **when two sources give the same
named level two prices, the row appears once, with both prices, both sources
named, and a DISAGREE flag.** The page shows this on PDH (23522.8 vs 23477.6)
and PDC (23410.0 vs 23362.8). The current payload emits both rows with the same
label and no flag; a screen that draws them as two levels is drawing a level
that does not exist.

---

*No file in the repo was modified. Nothing was committed. Two files created,
both under `docs/review/`.*
