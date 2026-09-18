# Convergence chips — the story layer as the moment the book and the tape agree

**Date:** 2026-09-19 · **Status:** specification, nothing built yet · **Branch:** `feature/operator-objects`
**Depends on:** `2026-09-19-orderflow-levels-design.md` (spec 1) — the `tm` mark family and `data/tape/ofd_marks_*`.
**Sources:** the operator's ruling of 2026-09-19 — *"the story thing… I want them to be now backed by order flow as
well… it uses OI already so if I add order flow that will really be a good combo"* — and her acceptance of the
reframe: a chip is the **agreement** of the book and the tape, on its own clock. Plus `BRIEF-for-the-builder.md` §2
(the 2026-09-11 convergence), the signal-layer spec §A.4 (the ballot's join), and both codebases read in full.
Every claim about existing code carries a file:line; every chosen value is in §J.

**Read first:** `context/research-findings.md` §2 (the engine event stream is DEAD as a signal: −0.1 / −6.2 vs a
+4.1 control, `signal_review.py`) and §5 (pre-register before any number is read); `CLAUDE.md` rules 4–7 and 9.

---

## §A Purpose and boundary

**The problem stated honestly.** The story chips are the engine's **book** reads — CAMPAIGN, BUYER-BUILD, PRESS,
DIVERGENCE, SPRING, IGNITION, the engine's own ABSORPTION and CLIMAX (`engine.py:13–20`, `:560–964`) — grouped one
per bar by `ui-v2/src/trade/narration.ts:92–135`. As a signal that stream lost to the do-nothing control and is OFF
by default (`trade/TradeTab.tsx:379–393`). The tape marks (spec 1) are a second stream of reads, unverified by the
operator's own account. **Adding the second stream to the first makes more chips, not better ones.** ~83 a day
was the failure mode; two unscored witnesses at equal weight is the same failure twice.

**The reframe.** A chip fires only when the book and the tape say the same thing at the same place and time — or
when they say *opposite* things in the one way that matters. This is the product the brief already names:
2026-09-11, 13:45–14:15, tape −7,670 net sell into a 49-point rally while the chain showed CE covering and PE
writing; *"one instrument was wrong… together they were unambiguous. That convergence is the product."* The ballot
does this at the zone edge for one setup (`signals.py:137–175`, the `event` vote). This spec does it per bar, all
day, and **its frequency is bounded by construction**: a conjunction of two independent reads is rare, the way
`is_edge` bounds the bell (signal-layer spec §A.8).

**What ships.** `convergence.py` (pure), seven chip kinds (§C), rendered through the chip machinery that exists
(§F), forward-logged as they fire (§E), on a pre-registered kill clock the operator arms (§K).

**What does not ship, ever, from this spec.** A direction banner (the parked-deletions plan); a hit rate
(rule 4); a sound (the bell is the ballot's, §A.8 — *"nothing else ever makes a sound"*); a vote in the ballot
(`signals.py`'s signature does not change); a change to any detector, the engine's or the extension's; a scorer
before §K is armed.

**Three absorptions are three populations.** The engine's ABSORPTION is a book read (`engine.py:816–834`: volume
rank > 0.95, range rank < 0.55, the side from the approach leg); the extension's `absorption` is a tape read
(`board.js:85–89`); the `tm` `absorption` is the standard tape read (spec 1 §E). A chip names which two it paired.
They are never summed, never counted together, never called one thing (rule 5).

---

## §B Inputs — both already on the server, neither changed

| witness | where it is | shape | side | place |
|---|---|---|---|---|
| **book** — the engine's events | the day payload, `engine.py:1292` → `live._remap_events` (`live.py:951–993`), keyed by **clock label** | `{t: "HH:MM", kind, msg, data?}` | `data.side` (`"UP"/"DN"/"BULL"/"BEAR"/"TWO-SIDED"`) or parsed from `msg` — **exactly `evDir`**, `ui-v2/src/data.ts:566–597`, mirrored in `signal_review.ev_dir` (`signal_review.py:72`) | level-bound kinds carry a price: SPRING/ARMED (`lvl` in msg, `data.level_name`), BAND-BREAK/-REVERSAL (`data.px`), ABSORPTION/CLIMAX (`near <C>` in msg), DIVERGENCE (the extreme). CAMPAIGN / BUYER-BUILD / PRESS / IGNITION / OI-PEAK-LAG are **book-wide: no price** |
| **tape** — the marks | `_SENSES["tape"][idx]["doc"]["events"]` (extension's, `src: "ofd"`) and `prints.tm_marks(bars)` (spec 1, `src: "tm"`) | `{t (ms), kind, side (±1/0), p, size}` | as carried | `p`, at tick precision |

A Python `book_side(event) → -1|0|1` is added to `convergence.py`, **a line-for-line port of `evDir`**, and pinned by
a test against a table of the same message strings `evDir`'s own cases name. If `evDir` changes, that test fails —
the same contract `signal_review.py` states for itself.

---

## §C The pairing grammar — seven kinds, one table, no other rule

A pair fires when a book event and a tape mark fall in the same **5-minute tape bar ± 1 bar** (join on the
`"HH:MM"` label, never on an index — the standing rule, `signal-layer-design.md` §A table, `visit.py` docstring)
and, when the book event carries a price, within **`EDGE_ROWS × rowSize`** of the mark (`signals.py:57`,
`EDGE_ROWS = 3`; `rowSize` from the doc). Book-wide kinds join on time alone.

| # | book kind (side per `evDir`) | tape kind | relation | chip kind | chip side | claim |
|---|---|---|---|---|---|---|
| 1 | CAMPAIGN | absorption | tape side **opposes** the press | `PRESS-ABSORBED` | tape's side | `call` |
| 2 | CAMPAIGN | initiative | tape side **matches** the press | `PRESS-CONFIRMED` | book's side | `call` |
| 3 | DIVERGENCE | exhaustion | same extreme (price join), same side | `DOUBLE-DIVERGENCE` | book's side | `call` |
| 4 | SPRING / ARMED | absorption | at the spring's level (price join), tape side matches the spring | `SPRING-ABSORBED` | book's side | `call` |
| 5 | IGNITION | climax | same bar | `IGNITION-UNRESOLVED` | 0 | `risk` |
| 6 | IGNITION | initiative | same bar, same side | `IGNITION-CONFIRMED` | book's side | `call` |
| 7 | CAMPAIGN / PRESS / SPRING / ARMED | **the bar's aggressor** — `sign(delta)` of the tape bar, `[M]` | aggressor **opposes** the book's forced-flow side | `CONFLICT` | 0 | `risk` |

Row 7 is the 2026-09-11 chip. It does not need a mark: the tape bar's own `delta` sign (spec 1's `bars[].delta`)
is the witness — *"tape sold into forced covering."* Its side is 0 on purpose: it is a warning, not a call, and its
tone is neither bull nor bear (§F).

**One chip per bar per book kind.** If both an `ofd` and a `tm` mark satisfy the same row on the same bar, one chip
fires and `tape` lists both sources — agreement across three readers is the strongest thing this layer can say and
it says it in one chip, not two. If only one family fires, the chip says which, and the operator reads that too.

**Nothing else pairs.** Trap and vacuum (tape), TRAP-SPRUNG and the rest (book) are not in the table because no
pairing was proposed and none is invented here. The table grows only by the operator's word, and a row that is
added after §K is armed starts its own clock.

---

## §D `convergence.py` — pure, stdlib, no I/O, no clock

```
build(book_events, tape_bars, ofd_marks, tm_marks, row_size, interval_ms=300000) -> list[chip]
chip = {t: "HH:MM", kind, side: -1|0|1, p: float|None,
        book: {kind, t, side, p|None}, tape: [{kind, src, t, p, side}],   # the two witnesses, verbatim
        why: str, tag: "I"}
```

- `book_side()` — the `evDir` port (§B). `book_price()` — `data.px`, else the number after `at`/`near` in `msg`
  for the level-bound kinds, else `None`; a level-bound kind with no parseable price **does not pair** and is
  counted in `build`'s `unpaired_why` ("SPRING at 10:20 carried no price").
- Time join: the tape bar containing the book event's minute, ± 1 bar. Price join: `abs(p_book − p_tape) ≤
  EDGE_ROWS × row_size`. Row 7 uses `sign(bar.delta)` of the containing bar only (no ± 1: the aggressor is a
  fact about that bar).
- `why` is one sentence in the extension's voice, from the two witnesses' own words:
  *"writers pressing (CAMPAIGN 10:20) and 340 lots absorbed at 23,312 against them (tm 10:25)"*.
- **Every chip is `[I]`** — a pairing of two inferences is an inference (rule 7). The `CONFLICT` chip's aggressor
  witness is `[M]`, and the chip stays `[I]`: the reading of the conflict is the inference.
- Pure: identical output on identical input, pinned.

---

## §E Where it runs, and the record

**Computed in the `/api/frame` POST path** (`server.py:1183–1195`), the moment a tape doc lands (once a second):
the engine's current events via `payload_at(box, iv)` for `idx` (the same read `_book_for` performs,
`server.py:534–541`), the doc's `closed` bars and `events`, `prints.tm_marks(closed)`. Result held in
`_SENSES["convergence"][idx]` under `_SENSES_LOCK`, beside `frame` and `tape`.

**Served two ways:**
1. **`/api/data`** — the day's `events` list gains the chips, each as `{t, kind, msg: why, data: {side: "UP"|"DN"|
   "FLAT", book, tape, tag: "I"}}`, appended at serve time from `_SENSES["convergence"]` — so `buildNarration`,
   the ribbon, the callout and `signal_review.py` all see them through the shape they already read. `msg` carries
   `why`; nothing downstream parses the chip's side from prose, because `data.side` is present (§F).
2. **`/api/frame`** — `tape.convergence`, the newest four, beside `tape.events` (`frame.py:353–356`), so the
   extension's face can print them under GoCharting too. Additive; the face's generic block renderer needs no code.

**Forward-logged as fired.** `convergence_log.py` (`DIR = data/convergence`, `frame_log.py`'s fail-soft shape) writes
`data/convergence/conv_<idx>_<day>.jsonl`, one row per chip, write-once by `(t, kind, book.t, book.kind)`. **Recorded, not recomputed** — unlike the `tm`
marks: this population is the one §K scores, and a scored row must be the chip as it fired at the time, not a
re-derivation after `convergence.py` changed (the `vpin_log` rule: *"a reconstruction written into it is
indistinguishable from an observation the moment it lands"*). The EOD capture already keeps the engine's events
(`eod_capture.py:193–216` dumps `/api/data`), and spec 1 keeps the tape; replay can therefore *re-derive* chips for
display, but only the logged rows are ever scored. Registered in `_isolate_mock_writers` and the
`test_day_state.py:97–98` pin list; `data/convergence/` gitignored with the reason.

**Anytime-start.** A late-started server has the engine's whole morning (REST rebuild, `live.build_session`) and
the extension's replayed marks (`record_read.py:9–12`), so it *derives* the morning's chips — and writes them with
`src: "backfill"`, which §K's scorer never counts (the ballot's own rule, signal-layer spec §A.4, last paragraph).
Observed chips carry `src: "observed"`.

---

## §F Rendering — the chip machinery that exists, plus one tier

- **`narration.ts`**: the seven kinds go in a new `TIER4` set; `Tier` becomes `0|1|2|3|4` and `Ribbon.tsx`'s
  `TIER_H` gains `4: 20` (the full track). Rationale: `buildNarration` keeps the highest tier per bar and breaks
  ties by payload order (`narration.ts:104–113`); a convergence chip must win its bar over the single-witness
  chip it was built from, and tier is the mechanism that exists for exactly that.
- **`evDir`** (`data.ts:566`): one case for the seven kinds — `s === 'UP' ? 1 : s === 'DN' ? -1 : 0` on `data.side`,
  the ARMED/SPRING convention. **`signal_review.ev_dir` gets the same line** (its docstring binds the two).
- **Tone**: `toneOf` gives bull/bear from `dir` for rows 1–4 and 6; `CONFLICT` and `IGNITION-UNRESOLVED` get a new
  tone `'caution'` rendered in `pal.caution` (already in the palette, `App.tsx:TapeTab refColor`) — a warning is
  neither a direction nor structure, and the one-meaning-per-colour rule (`theme.ts`) forbids borrowing brass.
- **`hinglish.ts`**: seven gloss entries in the existing shape (`hinglish.ts:52–75`) and seven `CLAIM` rows
  (`:192–215`) per §C's last column — the `signal_review` buckets.
- **Own toggle**, `tape.convergence`, default **on**, beside the story toggle (`TradeTab.tsx:389–393`) and
  independent of it: the story layer is off because it lost; this layer is new and bounded. Balloons on the chart
  follow this toggle; the ribbon tick and hover callout show a convergence chip regardless, as they do every chip
  (`ContractChart.tsx` props comment: *"`narrs` still reaches the hover Callout either way"*).
- **The legend line** under the chart states, once: *"convergence chips: n aaj, clock n/30 per kind, abhi score
  nahi hue"* — the disclosure this tab already makes for every unscored layer (`TradeTab.tsx:1011–1030`).
- Nothing here draws a level or moves a mark; spec 1's overlay work is untouched.

---

## §G Tests

| file | pins |
|---|---|
| `test_convergence.py` (synthetic, `test_signals.py`'s style — no recorded day is a target) | each of the seven rows fires on a built case and stays silent one bar outside the window and one row outside the price band; opposite sides never pair as agreement; a book-wide kind pairs on time alone; a level-bound kind with no price does not pair and is named in `unpaired_why`; `ofd` + `tm` on one bar → one chip listing both; `CONFLICT` fires on `sign(delta)` alone with no mark; two calls, identical output; `book_side` equals `evDir` on a table of the exact strings `evDir` matches |
| `test_frame_api.py` | after a POST whose doc pairs with a stubbed payload event, `_SENSES["convergence"]` holds one chip, the file holds one row, a second POST writes 0; `/api/data` `events` carries it with `data.side` and `tag: "I"`; a chip derived on a late start carries `src: "backfill"` |
| `test_day_state.py` | the pin list names `convergence_log.DIR` |
| `ui-v2` | `npm run typecheck`; a replay day with a stubbed chip shows it winning its bar in the ribbon at tier 4, and the two caution kinds in `pal.caution`. Not automated (no runner), stated so. |

---

## §H Docs and registrations

`.gitignore` · `_isolate_mock_writers` + pin list · `context/HANDOFF.md` entry (what shipped, the seven rows, the
clock armed but not started) · `context/research-findings.md`: **only the pre-registration the operator writes
(§K)**, nothing else · test counts in the four pinned files.

---

## §I Out of scope, deliberately

| deferred | why |
|---|---|
| the scorer | not until §K is armed by the operator; `signal_review.py`'s method is the one to reuse |
| more pairs (trap × TRAP-SPRUNG, vacuum × PRESS, …) | none proposed; each new row starts its own clock |
| a chip as a ballot vote | the ballot's signature is the guardrail (`signals.py` docstring); a chip can be looked at beside a LIVE signal, never counted |
| sound | §A.8 of the signal layer |
| the extension drawing chips on GoCharting | `tape.convergence` is on the wire; drawing is the face's choice, later |
| Upstox-derived tape as a third tape source | spec 2; when it exists it is a third `src`, same table |

---

## §J Spec decisions — choices neither source named

1. **Conjunction, no thresholds.** The only parameters are the join windows the ballot already uses (±1 bar,
   `EDGE_ROWS`). A chip with a tunable strength is a score, and a score is what the story layer was.
2. **`CONFLICT` reads the bar's delta sign, not a mark.** The 2026-09-11 case was net flow against forced flow, not
   a named tape event; `delta` is a measurement and needs no detector to be right.
3. **Tier 4, not a re-ordering of the payload.** Payload order is the engine's; leaning on it would be a hidden
   coupling.
4. **Default on, with the clock disclosed.** The DEPTH vote shipped on with its clock running (signal-layer spec
   §A.10); this layer is bounded by conjunction and is new evidence, not the dead stream revived.
5. **Recorded, not recomputed.** The scored population must be what fired (§E).
6. **`'caution'` tone.** Two warning kinds need a colour that is not a direction and not structure.

---

## §K Pre-registration — armed by the operator, not by this spec

Before any number is read, the operator writes in `context/research-findings.md`, in §5d's form (*written before
the run, committed before the run*):

- **Agreement kinds** (rows 1–4, 6): at n = 30 per kind, the +6-bar excursion in the chip's side must exceed the
  unconditional control's by **one standard deviation of the control** — the ballot's own bar (signal-layer spec
  §A.10) — or the row is deleted from §C.
- **`CONFLICT`**: at n = 30, the +6-bar excursion in the **tape aggressor's** side must be **below** the control —
  following the tape alone would have lost — or the row is deleted. This is the chip's whole claim and it is
  falsifiable.
- **`IGNITION-UNRESOLVED`**: at n = 30, the +6-bar absolute range after the chip must not exceed the control's —
  "don't chase" was right — or it goes.
- Sides reported separately, never pooled; backfilled chips never counted; no rate printed — rows, and the
  operator's verdict.

The margin above is a proposal in the ballot's units. It is hers to keep, tighten or replace before the first
scored row exists. Until she writes it, the chips draw, the file fills, and nothing is concluded.
