# PRE-REGISTERED — THE HOLD / FOLD WINDOW AND THE SIDE READ, merged (rev 4, written 2026-09-25 01:37 IST by the clock, before any code, UNTESTED)

Registered **before** the window exists, per research-findings §5 and in the
form of §1d (the fade gate). **Nothing below is a result.** Author: Fable, on
the base Mary chose (Fable's window) with Opus's OI read, clock and absence
rules merged in, Mary's decisions applied verbatim — the buyer's quiet clock
is a **FOLD**; buyer and writer rules are registered **together**; the
"better trade" read is reduced to **which side, CALLS / PUTS / no side** —
and Opus's reviews (`docs/hold/opus/PREREG-REVIEW.md`, `PREREG-REVIEW-2.md`)
fixed: M1–M5, S1–S7, N1–N5 and the second review's should-fixes. The change
log is §12. Times are read from the clock; the file's modification
time is the proof.

**What had already been seen when this was written, so nobody has to guess:**
both prototypes' replays of her 31 round trips over 2026-09-21 → 09-24, both
critiques, Opus's probe of rev 1 on the same four days, and both round-3
"better trade" reads. Every parameter below is inherited from a module that
already exists (§1d, `grounds`, `trendbox`, `board`) or was written down in a
RULES file before that replay. New choices are named where they occur; **one
clause (§4, the writer's own-side direction) was designed after seeing one
writer row and is flagged as such.** No parameter was moved after data.

---

## Why this exists

Her words, 2026-09-24: *"identifying direction is never my problem but holding
a trade is: closing too early on my trade, getting panicked with even 1 single
red candle, or holding a bad trade in FOMO and not getting out."* Two
failures: **(a)** leaving a good trade on noise; **(b)** staying in a bad trade
after its reason is gone. The window answers one question every finished
minute, from facts: **is the reason you entered still standing?** It never
answers "is this trade profitable". No candle of the premium is an input.

And, 2026-09-25: *"ce or pe is good enough call because … i often trade itm or
atm so which option i m holding hardly matters."* So the second read (§10)
answers one more question, every finished minute, whether she is flat or in a
trade: **which side — CALLS, PUTS, or no side — and does mine agree.**

## 1. The trade, reduced

A trade is (index, strike, CE/PE, long/short, entry time, entry price, qty). A
spread reads on its net direction (debit = its long leg, credit = its short
leg); the second leg enters P&L only.

| trade | role | direction `d` the thesis needs | **PAYERS** (Q): writers forced if price goes `d` | **HOLDERS** (R): writers whose staying protects the thesis |
|---|---|---|---|---|
| long CE | buyer | up | CE writers | PE writers |
| long PE | buyer | down | PE writers | CE writers |
| short PE | writer | not down (+1) | CE writers | **PE writers — her own side** |
| short CE | writer | not up (−1) | PE writers | **CE writers — her own side** |

The facts are the same for a buyer and a writer of the same `d`; the two
differ in §3 (the quiet clock, buyers only) and §4 (the writer's own-side
clause, the danger-side line, and what "payers adding" does for her).

## 2. The reads, every finished minute `t`, every input cut to `t`

Read at the last **finished** minute before a fill (a 13:41:38 fill is read at
13:40). A restart re-reads any past minute identically (REST backfill is exact;
the grid, ladder and fill runs are rebuilt from the day record).

**THE LINE [M] — price structure.** L = the most recent 5-minute swing of
TODAY beyond the index's 1-min close at entry (a swing = trendbox's pivot,
PIV = 2 either side, 09:15-aligned closed bars); if none, the session extreme
so far. For `d` = down the swing is a high above price; for `d` = up a low
below. L trails one way: when a new pivot confirms (two bars after it) that is
nearer to price than L and still beyond price, L moves to it; never away.
**Broken** = a 1-minute index CLOSE beyond L, buffer 0. A wick is not a break.
**Room** = the distance from the index to L, in points, printed at all times.
For a writer the line sits on the **danger** side (short CE: the swing high
above; short PE: the swing low below), same construction, with its room. The
line is **blind** at a minute with no index candle (S4).

**PAYERS / HOLDERS [M] — her OI reading rule.** From `fronts.read` (nine
strikes nearest spot, top 2 per side by the **running** session-peak OI — the
peak as of `t`, never the day's end), take the **nearer to spot** of each
side's two (`board.nearer`). Each is BUILDING / STALLED / UNWINDING by §1d
(15 % off its own peak with a falling 15-mark slope = UNWINDING; slope inside
±5 % = STALLED; else by the slope's sign). Folds are events from
`fronts.folds` (a sized front first read UNWINDING after a new high); a fold
is **live** while it is within 15 minutes of its stamp **and**
`board.still_folded` holds (S3).

- **Payers pay** when their nearer front is UNWINDING, or a payers'-side fold
  is live. **Payers against** when their nearer front is BUILDING with a
  build today, held for 3 finished minutes ("writers adding in its way").
- **Holders hold** when their nearer front is BUILDING. **Holders against**
  when their nearer front is UNWINDING, held 3 minutes ("the side holding
  your trade is leaving"). A live **holders' fold** is a WATCH-level fact —
  "the ceiling / floor stepped" — and **never a FOLD on its own** (§11, unsolved).
- **Both sides UNWINDING**: every OI fact reads flat and the row says "both
  sides' writers leaving — OI cannot say which way". It is a **read**, not a
  blindness (§3, rule 5).

**ORDER FLOW [I] — `grounds` + `board.aggression`, unchanged.** CVD over the
last 3 closed 5-minute ladder bars ranked against the day's own 15-minute
changes (STRONG = 0.50); prints of size = fill runs (rebuilt from the book) +
stacked imbalances, a side dominating with ≥ 2 and ≥ 2× the other. **Flow is
"with" or "against" only when CVD is strong AND the prints dominate the same
way** (`board.aggression`'s rule). A lone CVD divergence or a lone print count
is printed and does not count. **Blind** — "could not check — why" — when
fewer than 4 closed bars, when neither runs nor stacks can be read, and **when
the prints are too thin to rank** (`board.aggression`'s own sentence, "too
thin to read"; S2). On SENSEX that was 331 of 375 minutes on 09-23 and 100 of
375 on 09-24 (Opus's probe, fill runs rebuilt from the book; S-b) — the row
says so each minute, and the consequence is stated in §3 rule 6 and §7.

**TREND [I] — trendbox's 5m / 15m / 1h rows.** For a buyer: with her when ≥ 2
of 3 read `d` and none the other way; against when ≥ 2 read the other way.
For a writer: against when ≥ 2 read the danger direction; with her when none
does and none is forming. Else flat.

**Blind rules.** Fronts forming (fewer than `fronts.SLOPE_MARKS` = 15 grid
marks), the grid stale (> `fronts.STALE_MIN` = 3 min behind `t`), or fronts
not read → the OI rows are "could not check — why". No index candle at `t` →
the line is blind.

## 3. The verdict, in order — the first rule that matches wins

1. **FOLD, latched (M1).** Once FOLD has fired for this trade it stays FOLD
   through every later minute, **including minutes where the line or the OI
   rows are blind**; it shows the time it fired and the fact. If the facts
   later reverse, the sentence adds "the break has healed since HH:MM — a
   re-entry is a new trade"; the word never flips back. Re-picking the trade
   starts a new trade with a new line.
2. **PATA NAHI** when the line is blind and no FOLD is latched. When the line
   reads and OI is blind, the verdict is still computed from the line, FLOW
   and TREND, and is worded **"HOLD · structure only — OI could not check:
   <why>"** (or WATCH / FOLD as those rows say). A plain HOLD is never shown
   with OI blind.
3. **FOLD — the line is broken** (a 1-min index close beyond L).
4. **FOLD — positioning flipped**: payers against AND holders against, each
   held 3 minutes (the board's own OI read turning to the opposite trend).
   **This applies to writers too** (M2): a writer's "payers against" is the
   other side's writers adding in the way of her thesis' direction, and her
   "holders against" is her own side leaving under §4's squeeze clause.
5. **FOLD — the reason is gone** (buyers only, **her call**): nothing has paid
   in the last 15 **readable** minutes since entry. "Paid" = payers UNWINDING,
   or a live payers' fold, or flow with her by the strict rule. **Readable
   (M3):** a minute counts toward the clock **only when the OI rows read**
   (fronts not forming, grid not stale, fronts read); a minute with OI blind
   does not count, whatever the line or the flow say, because the facts that
   could have paid were not readable. **A both-sides-leaving minute counts,
   and counts as unpaid**: OI read it and said nothing is paying — "both
   leaving" is a read, not a blindness, and her intent is "nothing is paying".
   *Consequence, stated now for the six 09-24 puts entered 13:26–13:57 (from
   Opus's probe of rev 1):* with both-leaving minutes counted the clock folds
   all six at 14:08–14:10, before the 14:24 low, at +204.9 / +129.2 / +112.6 /
   +88.8 / +40.3 / −11.3 points from entry; not counted, they ride to the line
   at 14:35 at +176.9 / +95.9 / +79.3 / +55.4 / +8.4 / −47.9. On that day the
   chosen reading is the better one. It is not chosen for that: on a trend day
   where the winning side cashes in while the move continues, the same clock
   will fold early, and that cost is what §7's kill clause for this rule
   counts. The clock is visible at all times ("paid last HH:MM · quiet n of
   15"), so this FOLD never surprises.
6. **FOLD — two families against at once**: any two of OI (payers against),
   FLOW (against, strict), TREND (against). For a writer the OI family's
   "against" is her payers against, as in rule 4 (M2). Where FLOW is blind
   (SENSEX, most minutes) this rule is OI + TREND, and the row says "flow
   could not check — too thin to read".
7. **WATCH** — exactly one of: payers against (buyers; for a writer see §4),
   holders against, a live holders' fold, flow against, trend against. WATCH
   is silent, never latched, and always says what would turn it into FOLD.
8. **HOLD** — nothing against. If the premium is under her entry or its last
   1-minute candle went against her, the tag **noise** is added and the
   sentence names what has not changed — only when at least one "for" fact
   stands; with none, it reads "HOLD · nothing paying (n min)" and the clock
   shows.

**The entry check**, from the same reading at the entry minute, printed at the
head of the window **until the first 5-minute ladder bar closes after entry,
and for at least 3 minutes** (S6), then kept in the footer ("entered HH:MM
into …"):

- FOLD at entry (rule 4 or 6 — the line is set beyond price at entry and the
  clock starts at entry, so a FOLD at entry is always positioning flipped or
  two families against; M5): **"You entered into a broken setup — the reason
  was already gone at HH:MM, because <the two facts>."** Example this map can
  produce, from Opus's probe of it on 2026-09-23 at her 09:47 call entry
  (read 09:46): *"You entered into a broken setup — the reason was already
  gone at 09:46, because CE 23,400 writers were adding in its way (held 3
  min) and flow was against you (CVD −529 since 09:30 with price +9.8, rank
  0.67, prints selling)."*
- WATCH at entry: **"You entered into WATCH — <the one fact against>; it
  becomes FOLD if <what would confirm it>."**
- HOLD at entry: **"You entered into HOLD — line 74,037, 175 pts of room;
  <what is paying>."**
- The buyer's clock starts at the entry minute. Beside the entry check, §10's
  line: "your side vs the read: agrees / against / no side".

## 4. The writer rules, registered alongside

A writer is a bet that the danger move is absent or exhausted; time pays her.
Same facts, same map, with these clauses of her own:

- **Your side.** The HOLDERS row is labelled "your side" for a writer. An
  own-side front UNWINDING reads **against only while spot has moved toward
  her strike over the same 15-minute window** (grounds' `dpx` sign) — a
  squeeze. With spot moving **away** it reads **for**: "winners cashing in —
  your strike is farther from spot than at entry". A holders' fold on her own
  side follows the same clause. **When `dpx` is blind** (fewer than 4 closed
  ladder bars — the first ~20 minutes — or no ladder), the own-side row reads
  "could not check — no ladder window yet"; rule 4 (positioning flipped) is
  then unavailable for her, and her payers-against still counts in rule 6
  (S-a). **Flagged (S1): this clause was designed after
  seeing one writer row (the 09-24 with-trend short call that both prototypes
  folded and that expired at 0.15). It is registered here, not evidenced, and
  W1 judges it on forward rows only.**
- **Payers adding (M2).** The other side's writers adding in the way of her
  thesis' direction is **not a WATCH by itself** for a writer (it does not
  threaten a short by itself). It **is** her OI family's "against" in rules 4
  and 6: together with her own side leaving it is positioning flipped, and
  together with FLOW or TREND against it is two families against. A short
  against the trend can therefore be folded by OI, which is her doctrine.
- **The danger-side line** with its room, as in §2. A writer's WATCH/FOLD
  from the line means the index closed through the structure on the side
  that hurts her. No writer-specific room clause is registered (§11.2); until
  she registers one, W1 tests the whole window, line included.
- **No quiet clock.** Rule 3.5 does not apply; "nothing against you — time is
  paying the writer" is a HOLD.

Buyers and writers are **two populations** in the forward log and in the
falsifier (§7). Never pooled.

## 5. What is shown, what may alert

Shown, in reading order: the word (HOLD / WATCH / FOLD / PATA NAHI) with its
since-clock and a DRAFT stamp until registered; the line and the room; one
sentence; the rows PAYERS · HOLDERS (your side) · ORDER FLOW · TREND, each a
state word, a fact, and [M]/[I]; "n for · n against — a count, not odds"; the
buyer's clock; the WATCH hint; the side line (§10); a grey footer with the
premium, her entry, P&L in neutral ink, σ against the premium's own session
VWAP, and the read minute. Collapsed: `WORD · contract · line & room · the
one against-fact · since` — never the P&L. Colour only on the word; the
header turns red only on FOLD.

**May alert:** one tone on the transition into FOLD. Nothing on WATCH.
Nothing on HOLD. Nothing from the side read.

**Not shown, and said so:** the engine's headline (WAIT / SPENT / GO) — "not
shown: the engine's headline; its 09-24 calls read CONTRADICTED by the tool's
own grounding". Never an order, a size, a target, a stop price, a probability.
**Until §7 passes, every verdict carries DRAFT** (M4.4).

**Three sentences, always:** "checked, none" / "could not check — why" / "not
showing you — why". A missing value is never 0.

**Float:** Chrome's Document Picture-in-Picture (a real always-on-top window,
one call) with the GoCharting content script as the fallback.

## 6. Parameters, fixed now, not to be grid-searched

| parameter | value | from |
|---|---|---|
| swing bar · PIV | 5-min, 09:15-aligned, closed only · 2 | trendbox |
| break | 1-min index close beyond L, buffer 0 | Fable RULES §2.1, before replay |
| trail | one way, on confirmation, never away | Fable RULES §2.1 |
| fronts NEAR · TOP · UNWIND · STALL · SLOPE | 9 · 2 · 0.15 · 0.05 · 15 marks | §1d |
| which front | the nearer of the side's top 2 (`board.nearer`) | board (rev 3), her 2026-09-22 rule |
| fold size · fold liveness | 0.15 · within 15 min AND `board.still_folded` | fronts / Opus RULES §4 |
| PERSIST for against-states | 3 finished minutes | §1d `STALE_MIN`, Opus RULES §8 |
| ladder window · STRONG · ONE_SIDED · dominance | 3 bars · 0.50 · 0.80 · ≥ 2 and ≥ 2× | grounds |
| flow "against" needs CVD strong AND prints dominant; thin prints = blind | — | `board.aggression` (Fable P2; its "too thin to read") |
| trend rows · N | 5m 15m 1h · 20 | trendbox |
| quiet clock | 15 readable minutes (OI rows read; both-leaving counts as unpaid) | grounds' W × 5, Opus RULES §8; **FOLD by her decision** |
| soft FOLD | 2 of {OI, FLOW, TREND} | Fable RULES §3 |
| stale grid · forming | > 3 min · < 15 marks | fronts |
| latch | FOLD yes, WATCH no; survives blind minutes | both RULES; M1 |
| entry check shown | until the first 5-min ladder bar closes after entry, ≥ 3 min | S6 |
| side read (§10) vote | ≥ 2 of 3 rows one way and none against | the TREND rule above, reused |
| time bound | 30 sessions | grounds' own kill window |

Changing any one is a new registration.

## 7. Predictions and the falsifier, committed in advance (M4)

**Units.** A **FOLD stamp** is the first FOLD of a trade; latched minutes after
it are not events. A **noise stamp** is the first HOLD · noise minute of a
trade, and thereafter the first in each new 15-minute block. **Unlatched
state** of a minute is the verdict the map gives that minute with the latch
removed. **Excursion** = the option's favourable excursion in the trade's
direction over the 30 minutes after the stamp, **as a percentage of the
stamp-minute premium** [M from the chain record or REST], so NIFTY and SENSEX
stamps weigh alike; every comparison is also shown split by index. **A trend
day** is one where §10's side vote names the **same side** (CALLS or PUTS) on
**more than half** of the session's readable minutes; **a pinned day** is one
where "no side" stands on more than half — computed from the §10 rows in
`side_<day>.jsonl` (§8), no new number, and "more than half" so a day cannot
be both (N1). *Disclosed:* rev 2's definition ("5m, 15m and 1h all one way on
at least half") labelled **no** day in the record a trend day (SENSEX 09-24
scored 46 %); this one was chosen after that was seen and is checked, not
fitted, against the four days: SENSEX 09-24 PUTS 94 %, NIFTY 09-24 PUTS 91 %
[I candles], NIFTY 09-21 CALLS 94 %, SENSEX 09-21 CALLS 81 % — trend days;
NIFTY 09-23 no side 62 %, SENSEX 09-23 55 %, NIFTY 09-22 65 %, SENSEX 09-22
63 % — pinned, including 09-22, which fell 105 points in 30 minutes inside a
range: a leg inside a range day is still a range day. **BANKNIFTY 09-24 is the
edge case:** PUTS on 55 % of readable minutes on Fable's candles and 48 % on
Opus's, both reconstructed from chain spot [I] because REST served no 09-24
candles — a borderline day reads borderline, and with [I] candles its label
is not to be trusted either way.

**Buyers (population B):**
- B1. On trend days, with-trend trades' FOLD stamps come from the line or
  from positioning flipped more often than from the quiet clock or two
  families — a count of *where* FOLDs come from, read off `fold_rule` (§8).
- B2. On pinned days, buyers reach "reason gone" within 25 minutes of entry
  more often than on trend days (counts per population, described).
- B3. Noise stamps are followed by larger excursions than FOLD stamps.
- B4. FOLD at the entry minute is a minority of entries.
- B5. On trend days the **unlatched** FOLD state covers a minority of
  in-trade minutes (rows with `after_exit: false`) for trades whose side
  agrees (§10.4) with the day's majority side — the side named on more than
  half of the readable minutes in `side_<day>.jsonl`.

**Writers (population W):**
- W1. A with-trend short (her side is the winning side) is **not folded at
  all** — not by the line, not by OI — while spot moves away from her strike
  (the whole window, line included; S1).
- W2. A short against the trend (her side is being hunted) gets a FOLD stamp
  within the first 15 minutes, from the line or from positioning flipped or
  two families — which rule 4 and rule 6 can now produce for a writer (M2).

**Falsifier, per population, computed from the forward log only (§8), when
≥ 15 FOLD stamps and ≥ 15 noise stamps exist in that population **and at
least 10 sessions** have been logged (§1d's own horizon; at her pace the
stamps arrive in two or three sessions and would then span one regime), and
in any case at 30 sessions.** The map for that population dies if any of
these holds:
1. the excursion after noise stamps is **not** larger than after FOLD stamps
   (as two distributions; medians and the full rows shown, never a rate);
2. FOLD stamps at the entry minute exceed half of entries;
3. on trend days the unlatched FOLD state covers the majority of in-trade
   minutes (`after_exit: false`) for trades whose side agrees (§10.4) with
   the day's majority side;
4. the result **collapses** once the single best day is removed — "collapses"
   = clause 1's comparison reverses (N5);
5. **kill clause for her quiet-clock FOLD (rule 5):** stamps with
   `fold_rule = 5` are followed by larger excursions than noise stamps — then
   the clock reverts to WATCH and rule 5 is re-registered or dropped; the
   rest of the map stands;
6. **time bound:** at 30 sessions with fewer than 15 stamps in a population
   (writers on this account, likely), that population is **inconclusive and
   not signed live**; its verdicts stay DRAFT.

The reads (§1d, grounds, trendbox) stay regardless; they have their own kill
conditions.

**Hazards recorded now:** the latch keeps FOLD after a break price reverses
within a minute; buffer 0 produced a 2-point break on 09-22 11:14; a 5-min
pivot confirms ~10 minutes after the swing, so early in a leg the line is the
session extreme; the running-peak ranking can switch the nearer front between
two minutes; the quiet clock as a FOLD (her call) exited a trend-day
consolidation one minute before the move in Opus's 9.6 test — the cost she
accepted, counted by clause 5; FLOW is blind on SENSEX most of the day, so on
SENSEX rule 6 is OI + TREND and the clock is an OI clock; sub-minute trades
get one reading.

## 8. The forward logs — `data/hold/hold_<day>.jsonl` and `data/hold/side_<day>.jsonl`, write-once

**The trade log.** One row per finished minute per trade, appended by the
`/api/hold` route the way `calls_log` appends `/api/calls`, **never
rewritten**. **Horizon (N3): every trade is logged from its entry minute to
15:29, whatever she does** — rows after her exit carry `after_exit: true` —
so her early exits cannot censor the FOLD stamps, the noise stamps or the 30
minutes after them (the reason for the simpler "to 15:29" rather than
"first FOLD + 30": it also keeps "what if she had held" describable from the
rows). A restart re-reads the trade (entry minute, L, the latch, the clock)
from `data/day_state/` and continues the same rows. **At the close, an import
of the day's tradebook through the same route (S5)** replays every trade she
did not mark, causally, from the day record; those rows carry
`src: "import"`, marked rows `src: "marked"`, and the two are shown apart.
Row:

```
{day, t, idx, trade_id, src, after_exit, strike, side, role, qty, entry_t, entry_px, exit_t,
 verdict, since, fold_rule (3 line | 4 flipped | 5 quiet | 6 two | null), entry_verdict, unlatched,
 line: {L, src, room, broken_at},
 payers: {k, state, fold_t}, holders: {k, state, fold_t}, both_leaving,
 flow: {cvd_d, rank, buy, sell, word, why}, trend: {5m, 15m, 1h, word},
 clock: {paid_last, quiet, readable}, prem, prem_pct_of_entry, pnl, blind: [..],
 side_read: {side, since, agrees},
 tag: "I", src_data: {grid, ladder, trend}}
```

**The side log (N2).** One row per finished minute **per index, whether or
not she is in a trade**, written live and completed by the close-time import
(anytime-start makes it exact), so the trend-day / pinned-day labels (§7) and
the side falsifier (§10.6) are computable on days she never traded or traded
only in the afternoon. Row:

```
{day, t, idx, rows: {5m, 15m, 1h}, side, since, stamp (true on the first minute of a new side),
 facts: {payers, holders, aggression}, oi_half, blind: [..], expiry,
 atm: {k, ce_px, pe_px},                       -- this minute's ATM strike and its two premiums
 stamp_track: {k, from: t, to: HH:MM, short: bool,  -- on a stamp row only: THAT strike's
               ce: [{t, px}...], pe: [{t, px}...]}  -- CE and PE premium for the next 30 finished minutes
 tag: "I", src_data: {grid, ladder, trend}}
```

**One contract per stamp.** The ATM strike moves with spot — on SENSEX 09-24,
NIFTY 09-23 and NIFTY 09-22 it changed within 30 minutes after 9 of 21 side
stamps (Opus's probe) — so a per-minute "ATM price" splices contracts. On
every **stamp** row the log therefore records `stamp_track`: the strike that
was ATM at the stamp minute (`atm.k`) and **that strike's** CE and PE premium
at each of the next 30 finished minutes, from the chain record, appended as
those minutes finish (and completed by the import). A stamp after 14:59 is
tracked **to 15:29 and flagged `short: true`**; its window is shorter than 30
minutes and is shown as such, never padded. §10.6's excursions are computed
from `stamp_track` only, so "from these rows and nowhere else" stays true.

Nothing is suppressed: she can act against the window, and that disagreement
is the evidence. §7 and §10.6 are answered from these rows and nowhere else.

## 9. What stays unsolved, stated so it is not papered over

1. **The ceiling stepping down a strike versus the trend ending.** On
   2026-09-24 CE 74,000 folded at 10:14 (134 pts from spot) and the fall
   continued to 620 on the put; CE 74,000 folded again at 14:12 (352 pts from
   spot) and the low printed twelve minutes later. Opus's rule 3A (holders'
   fold + one confirmation) folded at 10:14 and 13:12; Fable's distance
   variant fired at 10:14 and not at 14:12. **Distance from spot does not
   separate the two**; the only thing that differed at 14:12 was that the
   payers' side had gone quiet (last put fold 13:46, both sides unwinding).
   This registration therefore keeps a holders' fold at WATCH and gives the
   quiet clock the both-leaving minutes (rule 5): it is the one mechanism here
   that reads "the payers have gone quiet". Whether that is the right
   separation is what clause 5 of §7 decides.
2. **A buyer's stop applied to a writer.** Both prototypes folded a
   with-trend short call on a 29-point line break with 16 points of room at
   entry; the call expired at 0.15. §4's own-side clause addresses the OI half;
   the line half (a minimum-room clause, or a wider structure for writers) is
   hers to register or reject. Until then W1 tests the line too.
3. **Expiry afternoons with both sides unwinding.** OI reads "cannot say
   which way" (49 minutes on 09-24 after 13:30); the window stands on the
   line, the clock and the strict flow read, and says so.
4. **Sub-minute trades** get the entry read and nothing more.
5. **The premium's own give-back inside an intact line** (09-22 13:48–14:14,
   222 → 134 with 36 points of room on expiry day). The window is a thesis
   read, not a profit-taking read; the mirror's DIVERGES is the candidate and
   is not in this registration.

## 10. THE SIDE READ — CALLS / PUTS / no side, registered here

Her simplification, verbatim: *"ce or pe is good enough call because holding
any ce or any put because i often trade itm or atm so which option i m holding
hardly matters."* So: no index ranking, no buying/selling day word, no
structures, no second-best. One line, every finished minute, per index, that
**speaks** — it is price-led, and OI and flow are counted facts, not gates.
Both round-3 reads sat silent nine minutes in ten because they gated on the
price rows AND the OI read agreeing; this one does not.

**10.1 The side.** From trendbox's 5m · 15m · 1h rows at `t`, by the same vote
the window's TREND row uses: **≥ 2 of 3 read UP and none DOWN → CALLS side**;
**≥ 2 of 3 read DOWN and none UP → PUTS side**; otherwise **no side**, with
the rows printed ("5m RANGE · 15m DOWN · 1h RANGE — no side"). A forming row →
"could not check — a middle row is still forming". Shown with "since HH:MM".

**10.2 The counted facts, for and against the named side** — three, each
named, each [M] or [I], each one of for / against / flat / could not check:
1. **Payers** [M]: the nearer front on the named side's payers UNWINDING, or a
   live payers' fold = for; BUILDING = against ("writers adding in its way");
   STALLED = flat.
2. **Holders** [M]: the nearer front on the other side BUILDING = for;
   UNWINDING = against ("the floor / ceiling is leaving"); STALLED = flat.
3. **Aggression** [I] (`board.aggression`, strict): pressing / leaning the
   side's way = for; the other way = against; none = flat; too thin = could
   not check (SENSEX on most 09-23 minutes, §2).
**The OI half** (`board.oi_read`: TREND UP / TREND DOWN / PIN / BOTH LEAVING)
is **printed as a summary line and not counted** (N4): it is, by
construction, "holders building and payers not building", a copy of facts 1
and 2 — on the four days it agreed with them on every minute it read for or
against. Printed as "PUTS side since 12:41 · 2 for · 0 against · 1 could not
check · OI: BOTH LEAVING", then the three lines. A count, never odds. Blind
facts are named, never counted as against.

**10.3 The expiry line.** When the index's front weekly expires today — read
from **the day's own record**: the frame head's `expiry` while the GoCharting
extension posts; **otherwise the chain poller's resolved expiry for that
index** (`upstox_chain`'s per-index resolution, kept in the day's chain
record — present on every day the poller ran, flat days included); or the
tradebook's `expiry_date` for an imported trade — never from the live
instrument dump, which no longer lists the weekly at the close-time import on
an expiry day. When none of the three exists: "could not check — expiry not
in the day's record". One line under the side:
**"0DTE today for <index>: the ATM strike's theta is at its fastest and its
gamma at its largest — a side is not a hold; the window's clock and line
decide when to leave."** On other days: "expiry <date>, <n> days". No number
is invented; theta is not estimated here.

**10.4 In a trade.** Beside the entry check: **"your side vs the read: agrees"**
(long on the read's side, or short the other side), **"against"** (long the
other side, or short the read's side), or **"no side — the rows do not
agree"**. It never tells her to exit; the verdict does.

**10.5 What it will do at turns, said now.** The rows are 20-bar windows on 5-,
15- and 60-minute bars, so the side turns **after** the index turns: the 5m
row needs the mean, the swings or the slope of twenty 5-minute bars to move;
the 15m and 1h rows later still. At a V-turn the read will keep the old side
for tens of minutes and then say "no side" before it says the new side. The
counted facts (a payers' front building, aggression the other way) are where
the turn shows first, and they are printed for that reason. This lag is a
property of the trend box, not a defect to tune out; the description in
`docs/hold/fable/BETTER-REPORT.md` §7 measures it on the four days.

**10.6 Predictions and falsifier, forward-logged in §8's row (`side_read`).**
- S-P1. On a trend day (§7's definition) one side stands for most readable
  minutes; on a pinned day "no side" stands for most.
- S-P2. Her entries against the read lose more often than her entries that
  agree, described as counts per day, never a rate.
- S-P3. At the day's extreme (the session high or low), the read is still
  on the old side or "no side"; it names the new side later — on the four
  days that was 9 minutes after the 09-23 NIFTY low, 19 after its high, 60
  after the 09-24 SENSEX low, and never inside the 09-22 NIFTY fall (PUTS
  came at 12:11). That range is the expectation, not a bound; the lag is
  **measured forward** from the side log as minutes from the session extreme
  to the first stamp of the new side.
- **Falsifier**, from the side log (§8), when ≥ 15 side stamps exist and at
  least 10 sessions, and in any case at 30 sessions: for each **side stamp**
  (the first minute a side is named after "no side" or the other side), the
  option on the named side **at the stamp-minute ATM strike** [M,
  `stamp_track` in the stamp row — one contract, never re-centred] must have
  a larger favourable excursion over the next 30 finished minutes (to 15:29,
  flagged, for a stamp after 14:59), **as a percentage of its stamp-minute
  premium**, than the same strike's option on the other side, as two
  distributions, shown also per index; **or** on more than half
  of the stamps **the side read names the other side, or no side, within 15
  minutes** (N5 — a reversal is the read's own change, no size is invented);
  **or** the result collapses — clause one's comparison reverses — when the
  best day is removed. Then the side line is deleted, not tuned. The trend
  box stays; it is display.

**10.7 Not tuned.** It is described on her 31 entries of 09-21 → 09-24 in
`docs/hold/fable/BETTER-REPORT.md` §7, with its lag at the turns, and nothing
in 10.1–10.4 was chosen by looking at those rows: the vote is the window's
TREND rule, the three facts are the board's rows, the expiry line is a
sentence. (The replay in that report counted the OI half as a fourth fact;
rev 3 dropped it from the count per N4. The side words and minutes are
unchanged by that; only the "n for / n against" totals shrink by the copy.)

## 11. What stays unsolved for the side read

The lag at turns (10.5) is the whole cost, and it is not solvable inside the
trend box. A faster side would need a faster price fact, which is a new
registration. The OI half reads PIN or BOTH LEAVING on most trend-day
afternoons (the winners cashing in), so fact 1 will often be flat exactly when
the side is right; it is printed, not counted against.

## 12. Change log

**rev 2, 2026-09-25 01:22 IST — read from the clock (`date`) immediately
before this edit; the file's mtime and the coordinator's commit are the
proof.** Fixes from `docs/hold/opus/PREREG-REVIEW.md`:

- **M1** — rule order: the latch is rule 1, PATA NAHI rule 2; a latched FOLD
  survives blind minutes. Why: a REST gap after a FOLD would have flip-flopped
  PATA NAHI / FOLD.
- **M2** — writers: "payers adding" is not a WATCH by itself but is the OI
  family's "against" in rules 4 and 6, with the own-side squeeze clause; W2
  re-stated on what the rules can do. Why: under rev 1 a writer's OI could
  never fold her.
- **M3** — the quiet clock's readable minutes defined: OI rows must read;
  both-sides-leaving counts and counts as unpaid; the consequence for the six
  09-24 puts stated both ways (14:08–14:10 vs 14:35) and the choice made on
  principle ("both leaving" is a read that nothing is paying), with clause 5
  of §7 as its exit.
- **M4** — falsifier made computable: FOLD stamps and noise stamps as units;
  unlatched state for the trend-day clause; trend day and pinned day defined
  from the trend box in advance; a kill clause for her quiet-clock FOLD; a
  30-session bound with "inconclusive = not signed, DRAFT"; B1 rewritten as a
  count of where FOLDs come from; B5 added.
- **M5** — the entry-check example replaced with one the map can produce
  (09-23 09:46, two families against, from Opus's probe).
- **S1** — the writer's own-side clause flagged as designed after one writer
  row; W1 now tests the whole window, line included.
- **S2** — thin prints registered as blind ("could not check — too thin to
  read"), and the SENSEX consequence stated (rule 6 = OI + TREND; the clock
  is an OI clock).
- **S3** — fold liveness: "within 15 minutes AND still folded".
- **S4** — "never blind" removed; the line is blind without a candle.
- **S5** — end-of-day tradebook import into the forward log, `src: import`.
- **S6** — the entry check is shown until the first 5-minute ladder bar
  closes after entry, at least 3 minutes.
- **S7** — times are read from the clock; the file's mtime is the time. Fable
  RULES §10 carried an estimated "01:50" on an entry written earlier; noted
  there.
- **§10 added** — the side read, per her simplification, replacing the
  round-3 "better trade" read (day word, index ranking, engine call, second
  best dropped; expiry line kept).

**rev 3, 2026-09-25 01:32 IST — read from the clock (`date`) immediately
before these edits.** Fixes from `docs/hold/opus/PREREG-REVIEW-2.md`:

- **N1** — trend day / pinned day defined by §10's own side vote on more than
  half of the readable minutes (no new number); rev 2's definition labelled
  no day in the record a trend day, disclosed; the four days' labels listed
  as a check; BANKNIFTY 09-24 stated as the edge case (55 % vs 48 % PUTS on
  two [I] candle sets — not to be trusted either way).
- **N2** — `data/hold/side_<day>.jsonl`, one row per finished minute per
  index whether or not she is in a trade, written live and completed by the
  import; the day labels and the side falsifier read from it.
- **N3** — every trade logged from entry to 15:29 whatever she does, rows
  after her exit flagged `after_exit`; chosen over "first FOLD + 30" so that
  "what if she had held" stays describable from the rows.
- **N4** — the OI half printed as a summary line, not counted; the side read
  counts three facts. Why: it is a copy of the payers and holders facts.
- **N5** — `fold_rule` in the trade row (3 line / 4 flipped / 5 quiet / 6
  two); "collapses" = clause 1's comparison reverses; "reversal within 15
  minutes" = the side read names the other side or no side within 15 minutes.
- **S-P3** — the "15–45 minutes" lag window removed; the observed lags on the
  four days (9, 19, 60 minutes; never inside the 09-22 fall) stated as the
  expectation, and the lag measured forward from the side log.
- **Excursion units** — percentage of the stamp-minute premium, pooled across
  indices and also shown per index, so SENSEX points do not swamp NIFTY.
- **Minimum sessions** — "and at least 10 sessions" added to the trigger of
  every falsifier (§1d's horizon), with the 30-session bound kept.
- **B1** — the vacuous second half dropped.
- **Expiry line** — read from the day's record (frame head `expiry` or the
  tradebook), never the live dump.
- **S-a** — the writer's own-side row when `dpx` is blind: "could not check —
  no ladder window yet"; rule 4 unavailable for her until then.
- **S-b** — "most of the day" replaced by the measured shares (331 / 375 on
  09-23, 100 / 375 on 09-24).
- Nothing Mary decided was reopened: the merged window, the quiet clock as
  FOLD, writers registered together, the side-only read.

**rev 4, 2026-09-25 01:37 IST — read from the clock (`date`) immediately
before these edits.** The last blocker from `docs/hold/opus/PREREG-REVIEW-3.md`:

- **`atm.k` and `stamp_track`** — the side-log row now carries the ATM
  strike, and every side-stamp row tracks **that one strike's** CE and PE
  premium for the next 30 finished minutes (to 15:29 and flagged `short` for
  a stamp after 14:59). §10.6's excursions read `stamp_track` only, so one
  contract is compared with itself and §8's "from these rows and nowhere
  else" holds. Why: the ATM strike moved within 30 minutes after 9 of 21
  stamps on the record, and a per-minute ATM price would have spliced
  contracts into fake excursions.
- **Clause 3 and B5** — "with-trend trades" replaced by "trades whose side
  agrees (§10.4) with the day's majority side", with in-trade minutes as the
  rows flagged `after_exit: false`.
- **Expiry line** — falls back from the frame head to the chain poller's
  resolved expiry (present on flat days and without the extension), then the
  tradebook, then "could not check".
