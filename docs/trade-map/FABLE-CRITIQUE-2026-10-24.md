# TRADE MAP — trader critique (Fable, 2026-10-24, one pass)

Reviewer lens: index-options prop desk, live positions. Not a software review.
Every number: [M] measured (her 10 held October trades, scratch `tm/`; the repo; oi-lab) or [I] inferred.
IN-SAMPLE throughout. Counts are counts, never a rate.

**VERDICT: the one-voice block is tradeable as it stands. The five-row TRADE MAP, as drawn, is not: it puts a
first target on the face that the first leg usually reaches, then asks a question beside it. That mechanises the leak
it was built to close.**

---

## 0. What I read

| source | what it fixed in my head |
|---|---|
| how-she-sells, oi-liquidity-hunt-thesis, two-regimes | 4 reads: ZONE · ORDER FLOW · OI · VPIN. Fold on them, never a candle/strike. Near-ATM top-2 per side; the side that stalls then unwinds is the fuel |
| §1b / §1d / §1m, HOLD-V2-PREREG | zone = d2→d3 ring; fronts BUILDING/STALLED/UNWINDING (15 % off peak); v2 line = push origin + 0.25U, lock at 2R, gave-up = UNWINDING + price on writers' losing side by 0.25U. FROZEN |
| voice.py, hold2.py, effort.py, engine.js levels()/emOf() | the block, the trail, EFFORT (survivor only at ≥2× high / ≤0.5× low), T1 = `wallNearest` ahead, EM = 09:20 straddle/0.8/√N |
| oi-lab DETECTOR / WEAVE / flow AUDIT | OI speed at extremes does not separate (1,982 ep.); composition + trapped + futures leg do; CVD div. inverted; effort/pt the only flow survivor, on a bearish 19-day sample |
| NOTEPAD A52–A58 | the block built; A53 design; A54 (OI at T1 doesn't separate); A57 sellers; A58 EFFORT blind to 09:56 |
| scratch evidence.py / touch.py (+ my range_used.py, fuel21.py) | her 10 rows, re-run; two extensions below |

---

## 1. Attacks, ranked (where it misleads her mid-trade)

### A1 · T1 = "the wall ahead" is a TARGET on the face. Her first leg usually ends there. [M]

| row | T1 pts | first move ended | T1 − end |
|---|---|---|---|
| 30 Sep 10:10 CE | +58 | +70 @12:49 | −12 |
| 05 Oct 09:28 CE | +36 | +41 @09:50 | −5 |
| 05 Oct 09:35 CE | +14 | +29 @09:50 | −15 |
| 05 Oct 12:09 PE | +11 | +11 @12:09 | 0 |
| 06 Oct 10:03 PE | +54 | +49 @10:10 | +5 |
| 06 Oct 14:12 CE | +29 | +8 @14:14 | +20 |
| 21 Oct 10:07 PE | +79 | +333 @14:47 | −254 (through T1, T2) |
| 22 Oct 13:00 SEN CE | +45 | +6 @13:01 | +39 |

- 5 of 8 rows: the first leg ended within 15 pts of T1 [M]. A trader reads that as: **T1 is where the pullback comes**,
  not where the trade ends. The face labels it a target with a points countdown ("T1 22,916f (−9 pts)").
- Her leak is exiting winners early. A countdown to a level the first leg reaches is a reason to exit at that level.
  The design's defence is AT T1 (A3). AT T1 cannot carry it (below).
- The one row that mattered (21 Oct) went 61 pts through T1 while the wall was at a fresh peak [M, touch.py]. The
  wall's OI said nothing (A54, and Fable's 1,982 episodes). So the wall is a MAP (who stands there), never a verdict.
- 06 Oct 14:12: touch.py's "touch 15:29, 42 % off peak" is AFTER 15:20 and after her 15:24 exit; the OI drop is
  end-of-day squaring (chain_metrics SQ_SQUARE_AT 15:05). That row is not a T1 touch. The real "6 Oct +5" is the 10:03 PE,
  whose T1 was never touched (end +49, T1 +54) [M].

**Where it misleads:** on a trend day she holds a winner to T1, the face shows "−9 pts" then "0 pts", the AT T1 row says
"read nahi → tighten" (A3), she exits. On 21 Oct that is +79 of +333.

### A2 · FUEL's trajectory is OI-speed-at-the-extreme renamed, and the sum does not move. [M]

The design: "trapped behind … covering = fuel burning; spent = the move is near its end."

21 Oct, her 23000 PE (▼). ITM put OI above spot, window +300, and the strikes the DETECTOR named as the trapped
inventory the fall ran on (23050/23100/23150 PE) [M, fuel21.py]:

| time | spot | ITM PE OI, +300 window | 23050/23100/23150 PE | event |
|---|---|---|---|---|
| 09:27 | 23079 | 112 L | 87 L | the build (DETECTOR) |
| 10:07 | 22988 | 257 L | 104 L | **her entry: still BUILDING** |
| 11:18 | 22947 | 260 L | 75 L | T1 touch |
| 12:34 | 22776 | 218 L | 49 L | voice EXIT (trail hit, A52) |
| 13:05 | 22735 | 240 L | 47 L | her exit |
| 14:47 | 22659 | 220 L | 39 L (14:00) | move's end |

- The windowed sum sits at 218–260 L all day: as price falls, new strikes become ITM and refill it. A moving-window
  "trapped behind" is a constant, not a gauge [M].
- The fixed set covered steadily: 104 L → 49 L by 12:34 (about half gone) — and the move ran 118 more points to 14:47.
  "Half covered = spent" would have been wrong by a third of the move [M].
- 14:47: two strikes read `None` in the snapshot; a naive sum prints 10.9 L — a collapse that never happened. A missing
  value is never a zero (CLAUDE.md rule 6). FUEL must print "could not check" per strike.
- "Trapped" is [I] twice: OI has no side (DETECTOR §6.3; `trapped_inventory.Ledger` ASSUMES writer-dominated builds),
  and overnight OI has no vintage. What IS measurable: OI at losing-side strikes now ITM, pinned at entry, vs its
  session peak. That is a description of who is paying. It is not "burning / spent".
- "Covering = fuel burning" at a low is DETECTOR's CAPITULATE/PRESSING (median −4/−5, 41 %/40 % held — i.e. mild
  continuation, population description, not an edge). "Spent" has no measurement behind it at all.

**Where it misleads:** holds a loser ("fuel still there, 220 L") on a range day; exits a winner ("fuel half spent") at
12:34 on 21 Oct.

### A3 · AT T1 (EFFORT at the touch) can only ever WARN a long, and was readable at 1 of her 5 real touches. [M]

| touch | EFFORT | Fable's word | what happened |
|---|---|---|---|
| 21 Oct 11:18 (▼, low) | 0.44× | sasta → continuation (survivor) | ran +254 more |
| 30 Sep 12:46 (▲, high) | 1.15× | normal (no read) | stopped +9; **198K seller print 12:50 on her footprint** [M, memory] |
| 05 Oct 09:32 (▲) | — | before 09:56 | +20 through, came back |
| 05 Oct 09:45 (▲) | — | before 09:56 | +20 through, came back |
| 21 Oct 14:47–14:50 (▼, low) | 1.49–1.99× | mehenga at a low = **mirror, failed holdouts** | move ended |

- The survivors are asymmetric: ≥2× at a HIGH → reversal; ≤0.5× at a LOW → continuation. Both mirrors failed
  (AUDIT §3.1: cheap at a high "inverted in-sample", expensive at a low noise). So for a CE buyer at a fresh high the
  row can say WARN or nothing; it can never say "aur chalega". For a PE buyer at a low it can say hold or nothing; never
  WARN. **A "help her hold" row that cannot say hold on an up-day is half a row.**
- n = 1 survivor read at one of her T1 touches. That is an anecdote agreeing with a hypothesis that passed on a 19-day
  bearish sample ("the two surviving reads are the two that agree with the drift" — Fable's own caveat).
- 21 Oct 14:47: the design's narrative ("expensive at the low = end") is exactly the read Fable killed. If the face
  prints it, she learns a dead rule from her best trade.
- 5-min lots/pt smooths a single print to "normal". 30 Sep: 1.15× while a 198K seller sat at the band (decoder E1 BADA
  PRINT, her trusted definition). The tool's own memory says those prints must be flagged.
- Latency: the read is on the last CLOSED minute; the touch is intrabar. The 21 Oct wall broke 61 pts in ~20 min.

**Where it misleads:** "mirror / unreadable → default to tighten" fires on most of her touches (3 of 5 above) at the
level where the first leg ends. That is the leak with a stamp on it.

### A4 · ROOM's σ ruler is the wrong one. The signed "σ used" read 0.38–0.85 on her four worst rows; the day's RANGE used read ≥ 0.98. [M, range_used.py]

| entry | signed σ used (design) | **range used (high−low / EM)** | entry at __ of day range (1.0 = her-side extreme) | move | result |
|---|---|---|---|---|---|
| 30 Sep 10:10 ▲ | +0.21 | 0.45 | 0.94 | +70 | +4 |
| 05 Oct 09:28 ▲ | +0.05 | 0.29 | 1.00 | +41 | +10 |
| 05 Oct 09:35 ▲ | +0.18 | 0.46 | 0.91 | +29 | −5 |
| 05 Oct 12:09 ▼ | +0.83 | **1.27** | 0.95 | +11 | −19 |
| 05 Oct 13:41 ▲ sale | −0.05 | **1.27** | 0.67 | +14 | −58 |
| 06 Oct 09:35 ▼ sale | −0.14 | 0.29 | 0.15 (sold the high) | +8 | −30 |
| 06 Oct 10:03 ▼ | −0.43 | 0.61 | 0.12 (sold the high) | +49 | −68 |
| 06 Oct 14:12 ▲ | +0.85 | **1.01** | 0.94 | +8 | −28 |
| 21 Oct 10:07 ▼ | +0.35 | 0.77 → 2.44 eod | 0.95 | +333 | +235 |
| 22 Oct 13:00 SEN ▲ | +0.38 | **0.98** (0.98 eod) | 0.63 | +6 | −243 |

- All four rows entered with the day's range ≥ 0.98 EM: moves +6 to +14, all four exited at a loss [M]. The design's
  signed σ said 0.38 and −0.05 on two of them. Range used is the late-flag; signed σ is not.
- Caveat, stated: those four are all afternoon entries (12:09, 13:41, 14:12, 13:00). Range-used and the clock are
  collinear on this sample. Ten rows cannot separate them. Describe, don't rank.
- "of ~2σ": on these five days the day's full range was 0.98–1.27 EM on four and 2.44 on the trend day [M]. "2σ" is
  the trend day. On an ordinary day the ceiling is ~1.0–1.3 EM of RANGE. Printing "~2σ" as the room invites holding a
  range day for a trend day's distance.
- Expiry day: the 09:20 straddle is the market's pin bet and decays through the day; by 13:00 it is stale. EM left on
  DTE 0 = the LIVE straddle / 0.8, or nothing. DTE 2+: /√N with "both ends counted" and holidays not removed [I, code
  comment]; the daily σ includes overnight variance the intraday move cannot use [I]. Fine as a ruler, wrong as a target.
- 22 Oct SENSEX: range 0.98 EM used at 13:00, entry mid-range (0.63), day's range never grew. The screen should have
  said "the day's move is done; you are buying mid-range at 13:00 on expiry" — a day-type / range-used sentence, not ROOM.

### A5 · The TRAIL (unchanged) exited her best trade 118 pts early, and the block has three definitions of one gave-up. [M]

- 21 Oct voice replay (A52): EXIT 12:34, trail line hit 22,780f (+215, "+4.5R"); the move ended 14:47 at 22,662f
  (+333). Left on the table by the block: 118 pts (35 % of the move's extent) [M]. She left 98 (exited 13:05 @ +235).
  **The block and she agreed within ₹2 — both out a third early. The existing block does not yet beat her.**
- 0.25U intrabar on 1-min: U = max(5-min VWAP σ, 0.1 % of price) → floor 0.25U ≈ 6 pts on NIFTY [I]; a routine wick.
  Not a change request (§1m is frozen): a fact for the forward log — "line hit by how many points, and did price go on".
- Three gave-up definitions on one face: V2GU (§1m: UNWINDING + losing side by 0.25U), GAVEUP (§5.4: oi_event or bleed
  with fut below E), BLEED (§5.5: ≥10 % off peak with ≥15 updates). §1d's UNWIND is 15 % off peak with a falling slope.
  Two thresholds (10 %, 15 %) for "came off its peak". "The first that triggered" hides it; the reason text flips as each
  clears. One method, one definition.
- BE lock at 2R on R = |G − E|: G is the engine's give-up, sometimes tens of points away; 2R then arrives in the first
  push and the line jumps to entry. A trend day's normal pullback to entry (+0) stops a working trade [I]. On 21 Oct it
  did not bite (lock 11:25, never revisited). Log the lock's revisit count forward.

### A6 · Sellers "in their direction" is the wrong unit. [M on her two sales]

| sale | fut at entry | strike / premium | moneyness | 13 min / 2 h later |
|---|---|---|---|---|
| 05 Oct 13:41 SELL 22650 PE @131 | 22,671 (spot ≈ 22,556 [I basis ~115]) | ~94 intrinsic + ~37 TV | ITM, trend-long | +14 then −85 pts MAE → −58 |
| 06 Oct 09:35 SELL 22600 CE @66 | 22,690 (spot ≈ 22,575) | ~0 intrinsic + 66 TV | ATM-ish, short | −31 pts MAE in 13 min → −30 |

- A57 says "neither had a T1". True and irrelevant: the first lost on a late (range 1.27 used) mid-range entry that
  never moved; the second on a 13-minute fade at the day's high. A T1 in points saves neither.
- An ITM sale is a futures position with a theta kicker (delta ~0.7–0.8): a points ruler is fine, the stop is the level.
  An ATM sale is half time-value: the pullback costs her ~nothing (theta pays while she waits) on DTE 2+, and doubles the
  premium on 30 pts against on DTE 0 (gamma). Points do not say which day she is on. **Sellers need the PREMIUM path:
  intrinsic + TV now, theta ₹/hr, premium at T1 (premAt exists), and "premium up while fut flat" (vega bid at her
  strike) as the seller-only WARN.**
- As the move goes her way the short's delta falls; T2 is worth little to a seller. KEEP ALL / BREAKEVEN are loser's
  levels; the seller's winner's level is "TV → 0".

### A7 · Five rows on three faces, with questions in them. [I]

- In a position I read three things: state, the one stop, one reason. Everything else is pre-trade (Validate) or an
  EVENT (T1 touched → one line, once). ROOM and FUEL are planning rows: they belong on the slip at entry and in [detail].
- "aur girega?", "T2 in play", "most moves stopped here": a question, a prediction and a rate claim (CLAUDE.md rule 4,
  from 5 rows) on an in-trade face. The GoCharting panel is her chart; six lines there is a second chart.
- "verbatim on three faces" is right for the brain (one record). The default face should be two lines; the map under
  [detail ▸], which the voice already has, shut by default.

---

## 2. The five questions

| question | answer |
|---|---|
| T1 = wall ahead the right first target? | As a LEVEL, yes (it is where the pullback comes, 5 of 8 rows). As a TARGET, no: it is where she exits. Rename it "pullback expected here"; the stop stays the trail. Wall OI at the touch is a map, not a verdict (A54, 1,982 ep.) |
| EM σ meaningful intraday, DTE 0 vs 2+? | As a late-flag via RANGE used, yes on her rows. As a signed target, no. DTE 0: the 09:20 straddle is stale by noon; use the live straddle or nothing. DTE 2+: /√N is a ruler with overnight variance in it; "~2σ" was the trend day only |
| "trapped behind" measurable live? | The NUMBER yes (losing-side OI now ITM, fixed set from entry, vs its peak), tagged [I] for side and vintage. The TRAJECTORY ("burning / spent") no: the windowed sum is flat all day (218–260 L on 21 Oct), the fixed set was half covered 118 pts before the end |
| Five rows too much live? | Yes. State · stop · why on the face; T1-touch as a one-time event line; ROOM/FUEL under [detail] |
| Evidence too thin to say anything? | For AT T1 as a face rule: yes (1 survivor read, on a bearish-sample hypothesis). For "range ≥ ~1.0 EM used = late": 4 consistent rows, collinear with the clock — describe it, log it forward, don't gate on it. For "the block beats her": not shown (21 Oct: within ₹2 of each other) |

---

## 3. My in-trade process (index weeklies, prop)

**Order, as the trade matures**

| # | look at | pullback says | invalidation says |
|---|---|---|---|
| 1 | the thesis LEVEL (spot for a strike/zone, fut for a flow origin) | wick through, no acceptance | accepted beyond, 3 min on spot (never a candle *close* rule for her — a touch of the trail) |
| 2 | the OTHER side's bars: did they PUSH (p90 Δ, R ≥ 0.25) or drift? | drift, shrinking Δ | a PUSH against from a level |
| 3 | WHO is paying: the losing-side strikes pinned at entry — covering slowly (trend) or REBUILDING at the new strike (defence moved, ROLLING) | covering slowly | rebuild / roll into the new strike |
| 4 | the trend-side front (her defence): BUILDING / STALLED / UNWINDING + losing side (her §1d, §1m) | building or munafa booking | gave up (§1m) |
| 5 | SYNC: do BANKNIFTY/SENSEX make the same extreme (her words: "in sync = real") | all three | NIFTY alone |
| 6 | time since the last push in my direction; range used vs EM | < 30 min; < ~1.0 EM | > 30 min flat (15 on DTE 0); range ≥ ~1.2 EM on a non-trend day |

**Trail.** To the origin of the last impulse in my direction (HOLD v2 has it). I never trail to T1 or to the wall. The
buffer is the impulse's own pullback depth, not a fixed unit [practice, I]. BE lock only after a second push, never on
the first.

**Targets / spent.** I have no targets in points. I have WHERE the other side must act: the losing side's strikes (they
hedge as it goes ITM) and the retail reaction points (PDH/PDL, round) where stops sit. The move is spent when: the
pullback after the last push holds (higher low for a short) AND the losing side stopped covering AND someone pushed
against. Any one alone is a pullback. **At the first wall I take a third when the move arrives on effort (≥2× at a high),
nothing when it arrives cheap — scaling, not a target. That is MY practice; for her it is a method change and needs her
word.**

**Sale vs long.**

| | long CE/PE | directional ATM/ITM sale |
|---|---|---|
| the pullback costs | theta every minute; on DTE 0 a 30-min hold is a visible slice of premium [I; gamma.py can price it] | nothing on DTE 2+ (theta pays her to wait) |
| the pullback kills | nothing until the level | on DTE 0 after ~13:00, gamma: 30 pts against ≈ premium ×2 [I] |
| the ruler | points of fut + ₹ | ITM: points (it is a future); ATM: PREMIUM = intrinsic + TV, theta ₹/hr |
| the seller-only tell | — | premium rising while fut is flat = IV bid at her strike (someone buying what she sold) |
| the winner's level | the trail | TV → 0 (ITM), or the trail (ATM) |

---

## 4. ADD (≤5, ranked)

| # | add | why (her rows) | data | exists? |
|---|---|---|---|---|
| 1 | **PUSH AGAINST** — the other side's PUSH bar since entry, as a WARN-grade line "PUSH ▲ 12:20 against · origin 22,840f", plus "last push ▼ hh:mm (N min)" in the header | this IS pullback-vs-invalidation in her grammar (AAKHRI BADA PUSH is on her chart); the registered PUSH definition, no new number | `hold2.pushes()` already returns every PUSH with its direction; `exit_v2` drops `d != trade d` | **EXISTS** as data (hold2.py, v2.js flowState); NEW: one filter + a face line; shadow-log "push against → what followed" |
| 2 | **RANGE USED** — (day high − low) / 09:20 EM, and "entry at x of the day's range", replacing the signed σ | separated her four late losers (≥0.98) from her winners (0.29–0.77) where signed σ did not (A4); collinear with the clock — show, don't gate | `emOf()`; spot series (v2feed payload / chain grid) | **EXISTS** (engine.js emOf, spot); NEW: one division. On DTE 0 use the live straddle |
| 3 | **FUEL as a FIXED SET** — at entry pin the losing-side strikes (ITM now or within 1 step), show OI now vs at entry vs session peak, per strike, `could not check` on a None | the window sum was flat all day; the fixed set told the story (104 L → 49 L → 39 L) — as a description, no "spent" | chain grid; `fronts.read` peaks | **EXISTS** (fronts.py, confluence.chain_grid; legacy trapped_inventory.Ledger); NEW: pin at entry |
| 4 | **BADA PRINT at the level** — decoder E1 within 1 step of T1 / the zone, side + lots, WARN-grade | 30 Sep 12:50: 198K seller at T1 while EFFORT read 1.15× "normal" (5-min smoothing); her trusted definition, not a top-N | E1 rows in `data/tape/ofd_marks_NIFTY_<day>.jsonl` (tape_log, from the extension) | **EXISTS** as a log (decoder.js E1; tape_log); NEW: the server reading its own log at T1 ± 1 step. Dies with the GC tab until the Upstox footprint (retire-GoCharting gate) |
| 5 | **SELLER PREMIUM PATH** — intrinsic + TV now, theta ₹/hr at DTE, premium at T1, and "premium ↑ / fut flat" as a seller WARN | points cannot tell a DTE-3 ATM sale (hold is free) from a DTE-0 one (gamma) (A6) | `premAt()`; `gamma.py` Black-76 price/vega/gamma; `chain_metrics.implied_vol`; `drag.py` | **EXISTS** (all four); NEW: the row |

Not in the five, free: SYNC in trade (her words; `xindex.py` shadow X1/X2, `engine.js xindex`) as one chip.

---

## 5. REMOVE

| # | cut | why |
|---|---|---|
| R1 | "most moves stopped here", "aur girega?", "T2 in play", "toota to fansa" | a rate claim from 5 rows (rule 4), a question, a prediction, a slogan — none belongs on an in-trade face |
| R2 | FUEL's trajectory words (covering = burning, spent = end) | OI speed at the extreme renamed; 1,982 episodes + fuel21 (half covered, 118 pts to go). Keep the numbers (ADD 3), drop the verdict |
| R3 | ROOM's signed "σ used" and the "of ~2σ" denominator | signed σ read 0.38 / −0.05 on two of her four late losers; 2σ was the trend day only. Replace with RANGE USED (ADD 2) |
| R4 | "mirror / unreadable → default to tighten" at T1 | fires on 3 of her 5 touches at the level the first leg ends; and TIGHTEN today is a 60-s event, not a stop move — undefined as a rule. Silence instead; survivor reads only, as descriptions |
| R5 | T1's "only if it comes off its peak" condition; the word "target" | A54 (3 touches + Fable); rename the row "pullback expected here · 22,916f / 22,900s" |
| R6 | two of the three gave-up WARN sources in voice.py (keep §1m's V2GU; §5.4 GAVEUP and §5.5 BLEED become numbers in [detail]) | one method, one definition of "came off its peak" (10 % vs 15 % today); the reason text flips as each clears |
| R7 | ROOM / FUEL / AT T1 from the DEFAULT face (panel, float, Validate) | under [detail ▸]; default = state · stop · why · event lines. Same brain, verbatim, less face |
| R8 | "15:20 — din khatam" wording | the reason is the 15:15 cash freeze (CAS): spot-based reads are blind. Same time, honest reason; her 15:00 practice stays a reminder |
| R9 | R in the header line ("+1.7R") | R = |G − E| inflates on a tight G; she thinks in pts and ₹. Keep R in [detail] for the lock |

---

## 6. One sentence

**Yes to the block as it stands (one state, one stop, one reason) — no to the five-row map on the default face; it flips
to yes when T1 stops being a target and becomes "pullback expected here", with PUSH-AGAINST and the day's RANGE-USED
beside it as descriptions, and ROOM / FUEL / AT T1 under [detail].**

---

## Appendix — rows, re-run 24 Oct (IN-SAMPLE, describe only)

### A. touch.py (T1 = Validate's wall ahead at entry; OI in L; "beyond" = spot through the strike, next 20 min) [M]

```
09-30 10:10 UP T1 22800CE stalled | touch 12:46 | OI 87.4→83.0L, peak 106.4L @11:49, off 22% | beyond +9
10-05 09:28 UP T1 22600CE stalled | touch 09:32 | OI 152.8→154.7L, peak 157.9L @09:31, off 2%  | beyond +20
10-05 09:35 UP T1 22600CE stalled | touch 09:45 | OI 154.0→174.6L, peak 174.6L @09:45, off 0%  | beyond +20
10-05 12:09 DN T1 22400PE          | never touched on spot (fut mapping reached it: basis ~115 — tag f/s)
10-06 10:03 DN T1 22600PE          | never touched
10-06 14:12 UP T1 22750CE stalled | touch 15:29 (after 15:20 and her 15:24 exit) | off 42% = EOD squaring, not a read
10-21 10:07 DN T1 22900PE stalled | touch 11:20 | OI 59.3→74.8L, peak 74.8L @11:20, off 0%   | beyond +61
10-22 13:00 UP T1 73500CE          | never touched
```

### B. range_used.py — see §A4 table. Columns: signed σ used (design) vs range used; entry position in the day's range.

### C. fuel21.py — see §A2 table. Window sum vs the fixed set, 21 Oct.

### D. 21 Oct 23000 PE timeline [M: evidence.json, A52, touch.py, fuel21.py]

```
10:07 entry 22,995f · range used 0.77 EM · PE 23050-23150 still BUILDING (104 L)
11:18 T1 22,916f touched · EFFORT 0.44x sasta (survivor) · wall at fresh peak 74.8 L · went 61 through
11:25 HOLD v2 lock engaged
12:34 voice EXIT: trail hit 22,780f (+215, "+4.5R", ≈₹323) · fixed-set fuel 49 L (half covered)
13:05 her exit +235 (₹325)
14:47 move's end 22,662f (+333) · 2.08σ signed · range used 2.15 at exit, 2.44 eod · EFFORT 1.49-1.99x at the low (mirror: no read)
left on the table: block 118 pts · her 98 pts
```
