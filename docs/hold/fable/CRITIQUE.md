# Critique of the other window (Opus 5.5) — Fable, 2026-09-25 01:40 IST

Method: I ran **both engines on the same minutes of the same trades** —
`scratch/compare.js` loads their `verdict.js` + `scratch/facts_*.json.gz` and my
`hold.js` + `data.js`, prints both readings side by side, and the full output is
`scratch/compare_out.txt`. Every row below is from that file. "What followed" is
the contract's premium from the chain record, [M] on the chain's expiry. Their
page was opened at 1536×695, light; its window text was read off the DOM.
Nothing was changed in `docs/hold/opus/`.

Their files: `RULES.md` (23:45, before replay; §9 logs three changes, one
post-data), `verdict.js` (one implementation, page + tables), `hold-window.html`
(2.7 MB, self-contained), `scratch/build_facts.py` (facts from `fronts` /
`board` / `grounds` / `trendbox`, cut per minute, fill runs rebuilt from
`data/book` through `ladder.Ladder` + `runs.Runs`), `REPORT.md`.

## 1. Their window at her real moments — the rows where the two windows disagree

Read minute = the last finished minute before the fill, in both windows.
"Right" is hindsight on one row; 23 rows on four days is a description, not a
rate.

| # | minute · trade | Fable said | Opus said | what followed (premium) | right |
|---|---|---|---|---|---|
| 1 | 09-24 09:41 · 74200PE entry #1 | HOLD (line 74,362, 170 room; fuel unclear; flow with you) | WATCH — PE 74,200 still adding, writers adding in its way | 175 → 196 (09:46, PE 74,200 folded) → 203 her exit → 620 close | Fable |
| 2 | 09-24 10:14 · from 09:42 | WATCH — flow: CVD +26 vs price −18 | **FOLD @194.7** — CE 74,000 folded 10:14 + PE adding | 233 (10:22), 179 (10:37), 154 (11:19), 620 close | neither on thesis; Opus the better price |
| 3 | 09-24 10:18 · entry #2 | WATCH — divergence at the 10:15 low | HOLD · NOISE — "what holds this trade has not changed" | 233 (10:22) then 179 (10:37); both FOLD 10:37 @179.15 | tie |
| 4 | 09-24 12:31 · entry #3 | WATCH — divergence at the 12:25 low | HOLD — PE 74,000 paying, PE 73,700 folded 12:27 | 203 → 448 (14:35) → 520 close | **Opus** |
| 5 | 09-24 13:12 · from 12:32 | WATCH — PE 74,000 adding again | **FOLD @201.9** — CE 74,300 folded 13:08 + PE adding | 282 (13:26), 410 (13:50), 477 (14:12) | **Fable** — their own candidate (i): the ceiling moved, it did not vanish |
| 6 | 09-24 13:25 · entry #6 | HOLD (70 room; flow with you) | WATCH — CE 73,900 folded 13:19 | 218 → 336 (13:50) → 477 (14:12) | Fable |
| 7 | 09-24 13:50 · from 13:26 / 12:32 | WATCH — divergence at the 13:45 low | **FOLD @335.95 / 410.1** — CE 74,200 folded 13:39 + divergence | 477 (14:12); 366 / 448 at Fable's 14:35 FOLD | Fable on price (+182 vs +152 on #6); Opus's exit was a fine one |
| 8 | 09-24 13:53 · entry #11 | WATCH — divergence | **FOLD at entry** — CE 74,200 folded 13:39 + divergence | 259, 297 (13:58), 224 (14:35), 182 (14:40); she took −12 | **Opus** — the FOMO guard fired where it should |
| 9 | 09-24 14:22 · entry #13 | HOLD — fuel unclear (both unwinding), flow with you, trend 3/3 | HOLD — CVD your way; both sides' writers leaving | the low printed 2 min later; 224 (14:35), 182 (14:40) | both wrong |
| 10 | 09-24 14:35 · from 13:57 | **FOLD @223.6** — SENSEX closed 73,702 over the line 73,690 | HOLD — "nothing is paying and nothing is against you, 1 quiet min" | 182 (14:40), 219 close | **Fable** — OI was blind, the line was not; Opus folded 14:40 @181.85 |
| 11 | 09-23 09:17 · 23450CE entry 1 | HOLD — fuel "unclear" | PATA NAHI — fronts forming, 2 of 15 marks | — | **Opus** — my "unclear" was a slope over two marks (RULES §10 F) |
| 12 | 09-23 09:50 · from 09:18 | HOLD | **FOLD @90.9 — reason gone**, nothing paid in 15 min | 92.55 (09:57, Fable's FOLD), 103 (10:30), 107 close | tie |
| 13 | 09-23 09:59 · entry 3 | WATCH — flow against | **FOLD at entry** — PE 23,450 folded 09:57 + CE adding | 95 → 90.8 her exit; she sat 9 min inside a FOLD in both | **Opus** — mine took one more minute |
| 14 | 09-23 10:40 · from 10:19 / 10:33 | WATCH — divergence at the 10:35 high | **FOLD @108.45** — PE 23,350 folded 10:38 + divergence | 114 (12:00), 119.75 (12:47, Fable's FOLD), 107 close | Fable held to +17.9 / +13.3; Opus's +6.6 / +2 was not wrong |
| 15 | 09-23 11:37 · from 11:07 | WATCH | **FOLD @118.2** | 119.75 (12:47), 107 close | tie |
| 16 | 09-23 11:39 · SENSEX 74900CE at her exit | WATCH — divergence at the 11:30 high | HOLD · NOISE — CE 75,000 paying, CE 74,900 folded 11:38 | 252.55 at 12:06 | **Opus** |
| 17 | 09-23 12:06 · same | WATCH | **FOLD @252.55** — PE 74,600 folded + divergence | 224 (12:32, Fable's FOLD), 166 close | **Opus** — the 30-minute high |
| 18 | 09-22 10:37 · 23550PE at her exit | HOLD — fuel burning, flow with you | WATCH — CE 23,550 folded 10:31 | 164 (11:14), 271 (14:00), 220 close | Fable |
| 19 | 09-22 11:14 · same | **FOLD @164.25** — line broken by 2 pts + fuel against | WATCH; FOLD 11:19 @170.65 | 158–271 after, 220 close | tie; both wrong on thesis, Opus 6 pts better |
| 20 | 09-22 13:47 · 23500PE entry (her +₹1,410) | HOLD — 10 pts of room, fuel burning | **FOLD at entry** — CE 23,350 folded 13:43 + prints against | 195 (13:53), 222.5 (14:00), 134 (14:14) | **Fable** — their FOLD-at-entry hit her best trade |
| 21 | 09-22 10:21 · 23300CE | **FOLD @155.15** — line 23,450 broken | HOLD · NOISE; FOLD 10:25 @148.85 | 28.85 close | Fable |
| 22 | writer 09-24 10:59 · short 74500CE | HOLD (16 pts room) | **FOLD at entry** — CE 74,200 folded 10:56 + PE adding | 64 (11:19, Fable's structure FOLD), 39 (12:00), **0.15 close** | Fable at entry; both misled the writer by noon |
| 23 | writer 09-24 10:40 · short 74200CE | HOLD | **FOLD @146.9** — CE 74,000 folded 10:37 + PE adding | 166 (11:00), 133 (11:30), 93 (13:00), 0.15 close | Opus over the next 20 min; both wrong against the expiry; Fable's 10:52 FOLD @170.4 was the worst exit on the page |

Rows where the two agree are not listed: both said FOLD 10:37 on 09-24 and
09:46 on the short-PE writer (a correct fold — that put went to 620), both
FOLD-at-entry on the 09-23 in-the-money short call, both HOLD at 13:40–13:45 on
09-24.

**Calm when it should be.** Their HOLD · NOISE chip did the job on rows 3, 4
and 16: the premium was red, the word stayed HOLD, and the sentence named what
had not changed. On row 4 it was calmer than mine and right. **Shouts when it
should.** Rows 8, 13, 17, and 10:25 on 09-22: the FOLD-at-entry reads are the
best single thing either window did for failure (b). **Shouts when it should
not.** Rows 2, 5, 20, 22: every one is a fold on the *holding* side that was the
ceiling (or floor) moving one strike, not leaving — their own candidate (i).
**Silent when it should not be.** Rows 9–10: from 14:21 both sides' writers
were leaving, OI read flat, and the window ran on a 15-minute CVD; it folded
at 14:40, five minutes and 42 points after my line broke at 14:35.

The entry read a fresh trade would have got at every minute of 09-24
(SENSEX, the trend day), both engines:

| | Fable H / W / F | Opus PN / H / W / F |
|---|---|---|
| buyer PE (with the trend) | 178 / 182 / **14** | 13 / 188 / 81 / **92** |
| buyer CE (against it) | 13 / 209 / **152** | 13 / 186 / 109 / **66** |
| writer CE (with) | 284 / 82 / 8 | 13 / 188 / 88 / 85 |
| writer PE (against) | 13 / 185 / 176 | 13 / 186 / 109 / 66 |

Theirs folds a with-trend put on more minutes than an against-trend call on a
trend day. That is rule 3A reading each ceiling move as a break, and it is the
structural fault of the design.

## 2. Rules and discipline

- **Thresholds.** Principled. Their three new numbers (3-minute persistence,
  15-minute recency, 15-minute reason-gone) are §1d's `STALE_MIN`, grounds'
  window and §1d's slope, reused and said so. Nothing was fitted; the section
  "what I had already seen when I wrote this" at the top of their RULES is the
  right way to declare contamination.
- **Post-data changes.** Logged, timestamped, and honest: §9.1 and §9.2 are
  clarifications made before the run (fronts forming = PATA NAHI; readable
  minutes only); §9.3 is a label-only change after seeing 14:25–14:38 on 09-24
  and is flagged as post-data in both files. Three candidate fixes (i)–(iii)
  seen on one day are listed and not applied. This is the standard.
- **Hidden score.** None. "2 for · 1 against — a count, not odds" is a count;
  `rank 1.00` is grounds' own percentile of the day's 15-minute moves. One
  inconsistency: the displayed word changes between `HOLD` and `HOLD · NOISE`
  with the last 1-minute *premium* candle. The class does not move, the chip
  does — and their RULES §1 says no candle is an input. It is a label, not a
  verdict, but it is the one thing on their window that a red candle can move.
- **Writer.** Same break rules as a buyer (Q and R swap), exempt from
  reason-gone ("time is paying the writer"). Their own note (iii) is right:
  "payers adding" gives a writer a WATCH that does not threaten her. Deeper:
  for a writer R is her own crowd, and an R-fold reads "the side holding your
  trade is leaving" — on 09-24 that was call writers at lower strikes cashing
  in during a fall, a profit-taking cue, and it folded a short call that
  expired at 0.15 (row 22–23). Mine misread the same rows the same way (RULES
  §10 G). Neither window reads a writer correctly on a with-trend short yet.
- **Expiry afternoons, both sides unwinding.** They say what happens and it
  is what happened: OI reads flat, the verdict runs on a 15-minute CVD, and it
  lagged the 14:24 low by 16 minutes (49 such minutes on 09-24 after 13:30).
  The window is honest about it ("both sides' writers leaving — OI cannot say
  which way; order flow decides"), and it has nothing else to stand on.
- **Order flow blind (SENSEX prints).** Handled better than mine: they
  rebuilt fill runs from `data/book` the way a restart does, so their FLOW row
  had real prints where my replay said "could not check"; where the book was
  thin (331 minutes on SENSEX 09-23, 100 on 09-24) the row reads `?` with the
  reason and never "quiet". SENSEX order flow is then CVD alone, which they
  state.

## 3. The window itself

388 px wide, light, draggable, collapses to one line; DRAFT stamped on the
verdict. **First**: the word on a colour band with its since-clock. **Second**:
one sentence of facts. **Third**: a three-row ledger — PAYERS, HOLDERS, ORDER
FLOW — each with ● / ✕ / ○ / ? and [M]/[I], then "n for · n against — a count,
not odds", the buyer's "paid last HH:MM · quiet n of 15 min" clock, and, on
WATCH, what would turn it into FOLD. Then premium, entry, points and ₹ in
neutral ink, σ against its own VWAP, spot, 5m/15m rows. Eleven lines, about
300 px tall against my 260. No chart; the strip is a state strip. Light.

What reads well: the verdict band, the sentence, the ledger marks, the
paid-last clock, the WATCH→FOLD hint — a trader reads the word, the sentence,
then the ✕ row. What reads less well: the sentence re-words itself whenever a
front's lakh count ticks (+22.8L → +25.4L → +25.9L …), so the change log
records a "change" every few minutes while the word is unchanged; the
collapsed line carries `you −8.1%` — the P&L in the one place she sees when
collapsed, which is the panic number in a calmer font; and eleven lines is a
lot for a window that floats over a chart. Absence: "could not check — why" is
everywhere and correct (forming fronts, stale grid, thin book, contract not in
the record); "checked, none" is implicit in `○ 0 sell / 0 buy`; neither their
window nor mine prints "not showing you — the engine's headline, because it
read CONTRADICTED on 09-24". Both should.

## 4. What they got right that I missed — and the reverse

**Theirs, specific:**
1. **PATA NAHI while the fronts are forming** (fewer than 15 marks). Mine read
   a two-mark slope as "flat" at 09:17 on 09-23. Theirs is house rule 6 read
   correctly. Now RULES §10 F, on my variant toggle.
2. **The nearer front** (`board.nearer` of the §1d top 2) instead of grounds'
   #1 by peak. On 09-24 grounds' #1 CE front sat 700 points from spot all
   afternoon; their HOLDERS row read the strike that mattered. This is her
   "nearest ATM" doctrine, and it is why their 13:53 FOLD-at-entry exists.
3. **Folds as votes on both sides**, with `still_folded` checked — a payers'
   fold pays, a holders' fold is a break candidate. My window printed the
   fold list and gave it no vote.
4. **The paid-last clock and REASON GONE** for buyers: the only mechanism on
   either window for "re-entering again and again when nothing is paying",
   and the countdown makes the FOLD unsurprising.
5. **"the break has healed since — a re-entry is a new trade"** on a latched
   FOLD. The most honest sentence on either window.
6. **Fill runs rebuilt from the book record** (`ladder.Ladder` + `runs.Runs`,
   as `_ux_drain` does), and the grid validated against `/api/oihist`
   (373/373 minutes, 47 folds, 9 runs). My replay lacked runs entirely.
7. **HOLD · NOISE** as a named state that says what did not change, and the
   §9.3 correction that it needs a standing fact.
8. **The WATCH line says what would make it FOLD.**
9. Examples chosen by a rule that the tool itself produced (the zone
   machine's 09-23 BUY entries), and reported as misleading when they were.

**Mine, specific:**
1. **A price line.** The index's own 5-minute structure never goes blind: row
   10 (14:35 vs 14:40, 42 points) and row 21 (10:21 vs 10:25) are the line
   firing while OI could not speak. Theirs has no fact that is a price.
2. **The trend vote**, which gives the with-trend / against-trend asymmetry
   the table in §1 shows (14 vs 152 FOLD minutes; theirs 92 vs 66).
3. **A holders' fold is not a break on its own.** I kept it out of the verdict
   (RULES §8.5); their 3A made it one, and rows 2, 5, 20, 22 are the cost.
4. **Room in points** on the window — "16 pts of room" at the writer's entry
   is the number a trader acts on, and no rule has to encode it.
5. No P&L on the collapsed line; the only colour is the verdict.
6. The picker takes a spread (second leg into P&L, verdict on the net
   direction).

## 5. Which window would I want on my own desk, and why

**Mine, as the base — and I would spend the first evening moving three of
their pieces into it.**

Why mine: on her real rows the line fired when the OI went blind (rows 10 and
21), and the trend vote kept FOLD off her with-trend puts on the one day she
was right about direction (row 5 alone is the difference between +₹9,830 and
−₹80 on the 12:32 entry). On the disagreement rows I count 10 for mine, 7 for
theirs, 6 ties — a description of 23 rows, not evidence, and three of theirs
(8, 13, 17) are the kind of call I would most want on a range day.

Why not theirs untouched: rule 3A. A window that folds a with-trend put every
time the ceiling steps down a strike will reproduce failure (a) on exactly the
days she is right, and it did so four times on this record. They saw it and
listed it as candidate (i); it is the first thing to register away. And, to be
fair to them, my own §8.5 candidate is the same fact with a distance
parameter, and when I switched it on it fired at 10:14 too (§7 below) — so on
this point neither of us has a rule, they just ran theirs.

What I would take from theirs on day one, in order: the nearer-front ledger
with folds as votes; PATA NAHI on forming fronts; the paid-last clock and
REASON GONE; then the "healed" line and the WATCH→FOLD hint. Choosing theirs
would have been reasonable for the OI read alone; the reason I do not is the
line.

## 6. The one merged window

1. Header: the word (HOLD / WATCH / FOLD / PATA NAHI) on a band, its
   since-clock, DRAFT until registered; the header turns red only on FOLD.
2. One sentence: the fact that broke it, or the facts that hold it; on a
   latched FOLD, "the break has healed since — a re-entry is a new trade".
3. **THE LINE [M]** — the index's last 5-minute swing beyond price, trailing
   one way, room in points; a 1-minute close beyond it is FOLD. Never blind.
4. **PAYERS / HOLDERS [M]** — the *nearer* §1d front on each side, with folds
   as votes and `still_folded` checked; both unwinding reads flat with the
   note; a holders' fold within 2 steps of spot prints "winners cashing in"
   and is a WATCH, never a FOLD on its own.
5. **ORDER FLOW [I]** — grounds' CVD and prints, runs rebuilt from the book;
   against is a WATCH, never a FOLD alone.
6. **TREND [I]** — 5m · 15m · 1h voted; against is a WATCH.
7. FOLD = the line broken; or positioning flipped (payers BUILDING and
   holders UNWINDING, each held 3 minutes); or, buyers only, nothing paid in
   15 readable minutes. WATCH = any one against. Latched. One tone on FOLD.
8. Buyer's clock "paid last HH:MM · quiet n of 15"; every WATCH says what
   would make it FOLD.
9. Absence, three sentences: PATA NAHI while the fronts are forming or the
   grid is stale; each blind row says why; one grey line "not shown: the
   engine's headline — its 09-24 calls read CONTRADICTED".
10. Footer grey: premium, entry, P&L neutral [M], σ vs its own VWAP, read
    minute. Collapsed: `FOLD · 73800 PE · line 73,690 broken · CE 74,000 folded
    at spot · since 14:35` — never the P&L. Chrome Document PiP for "over
    every tab". Writer amendment (RULES §10 G) registered before a writer sees
    a verdict.

## 7. What I changed in my own prototype after this review — and what the toggle showed

- `hold.js` / `index.html`: a **variant toggle, off by default**, labelled
  "variant A+F (post-data, unregistered)": (A) a wall fold within 2 steps of
  spot in the last 15 min reads FUEL against for a buyer; (F) FUEL is blind
  under 15 grid marks. The registered rule is untouched; the minute table
  says when the variant is on.
- **What A did when switched on, stated before anyone tunes it.** On 09-24,
  for a put buyer, A fires on 119 minutes, the first at **10:14** (CE 74,000
  folded 10:14, 134 pts from spot) — the same fact and the same minute as
  their rule 3A's first FOLD — and it does **not** fire at 14:12–14:24, because
  the folds the brief called "near spot" (CE 74,200 at 13:39, CE 74,000 at
  14:12) were 320 and 352 points from spot, more than two steps. So the
  candidate I kept out of my verdict and criticised in theirs is, with a
  distance parameter, the same trap: the ceiling stepping down (10:14, 134 pts)
  and the winners cashing in (14:12, 352 pts) are not told apart by distance —
  if anything the exhaustion fold was the farther one. The number stays at 2
  and A stays off; nobody should try 4. What did differ at 14:12 was that the
  **payers' side had gone quiet** (the last PE fold was 13:46, both fronts
  unwinding) — which is the domain of their paid-last clock, not of a fold's
  distance. That is a point for their design, found by my toggle. F fired
  where it should (09-23 09:17: "fronts forming, 2 of 15 marks").
- `RULES.md` §10: F (forming fronts), G (the writer's own-crowd unwind needs a
  direction), H (why 3A stays out), all proposals.
- `scratch/compare.js`, `scratch/compare_out.txt`: the side-by-side.
