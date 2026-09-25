# Cross-review: Fable's HOLD / FOLD window, judged as Mary would

Written by Opus, finished 2026-09-25 00:30 IST (file mtime; an earlier draft of this line said 02:45, an estimate that was wrong), after reading everything in `docs/hold/fable/`.

How I compared them:
- I ran their `hold.js` on their `data.js` in node and replayed their page at 1536×695.
- Both engines were run on the same trades and read at the same finished
  minutes (`scratch/xreview/both.js`, `side.js`, `flicker.js`).
- The judge is the same premium series for both: Upstox 1-min [M] where it
  was frozen, and the chain record's LTP [I] for 09-22.

Nothing here is evidence. There are four days, two of them expiries for the
contract traded, and one trend day that pays anyone who holds puts.

## 1. Their window at her real moments

**Where it stays calm when it should.** The afternoon of 2026-09-24 is her
failure (a) in its purest form: eleven round trips from 12:32 to 14:23, most
exited within a minute.
- Their window was on WATCH or HOLD from 12:31 to 14:34 and never said FOLD.
  The line tightened from 74,115 to 74,037 to 73,690 and never broke; the
  trend rows read "3 of 3 with you".
- Held from her 12:32 entry to their 14:35 FOLD, the 74100 PE is **+239.8 pts
  against her +13.7**.
- Mine folded that same trade at **13:12 at 200.4 (−1.9)**. That was 13
  minutes before the 13:25–13:50 collapse, on "CE 74,300 folded 13:08 + PE
  writers adding", a consolidation near 74,000 that my rule read as the
  holders leaving.
- **On the day's biggest move, theirs kept her in and mine took her out.**

**Where it shouts when it should.**
- After the 14:24 low, their line broke at **14:35** (SENSEX closed 73,702
  over the 14:15 swing high 73,690).
- Mine said HOLD until 14:39 and FOLD at 14:40. Both sides were unwinding,
  so my OI facts were flat, and my 15-min CVD still read "her way".
- For the 14:23 put: theirs **−67.9 pts**, mine **−105.3**. Both late,
  theirs less late.

**Where it misleads, in rows.**
- **09-22 13:48 23500PE: HOLD through a 14-minute give-back.** 222.5 at 14:00
  fell to 133.95 at 14:14 inside an intact line (36 pts of room). Theirs
  folded at −47.6. Mine said FOLD at the entry minute (CE 23,350 folded
  13:43 + prints against), −5.0 if followed. She took +21.7 at 13:54, better
  than both.
- **09-23 SENSEX 74900CE.** Theirs folded at **12:32 at 224.9** (+9.7). Mine
  folded at **12:06 at 256.2** (+41.0), the 30-minute high.
- **09-24 morning 74200PE (#1).** Theirs folded at 10:37 at 179.15 (−0.4).
  Mine folded at 10:14 at 194.45 (+15.2). Both folded a put that ended at 620.
- **Writers with the day's direction.**
  - Their own example (09-24 short 74500CE, 16 pts of room) folded at 11:19,
    and the call expired at 0.15.
  - My example (short ATM 74100CE at 10:30): theirs folded at 10:52, −38.3;
    mine at 10:40, −13.8. That call also expired at 0.15.
  - A 1-minute close over the last 5-minute swing is a buyer's stop applied
    to a writer. Mine is no better in kind (it folds writers on the same
    bounce), only earlier.
- **09-23 zone BUY (SENSEX 74700CE, gate legal).** Theirs was HOLD, then
  folded at 10:11 at −27.2, just before the CE ran to 297. Mine said FOLD at
  entry (0). Both missed the move. Mine lost less if followed.

**Following each window from her own entry to its first FOLD:**
- theirs did better on 15 rows, mine on 12, and 8 were within 1 point;
- the rows are **not independent**. Eight of their 15 are the same 09-24
  afternoon leg; three of my 12 are the 09-22 10:42–10:44 scalps, one
  episode.
- By distinct episodes:
  - theirs won the 09-24 afternoon (large), the 14:24 low (5 minutes
    earlier), 09-23 mid-morning (held the 10:19 and 10:33 CEs to 12:47) and
    09-22 09:42;
  - mine won the 09-24 morning, the 09-23 SENSEX call, 09-22 13:48, the
    with-trend writer and the zone example.
- **The one episode that carried real money was theirs.**

**Calm, measured.** From entry to each window's first FOLD, over her 28
readable trades:
- mine changed verdict 53 times in 680 minutes, and **352 of those 680
  minutes were WATCH**;
- theirs changed 63 times in 1,563 minutes, 651 of them WATCH.
- **Theirs flips about half as often per minute.** Mine spends about half of
  every trade in WATCH, and a window that is amber half the time is not calm.
  Most of my WATCH minutes are unconfirmed opposite-side folds. Most of
  theirs are a lone CVD divergence.

## 2. Rules and discipline

- **Thresholds.**
  - Every parameter of theirs is inherited: PIV = 2 and 5-min bars from
    trendbox; W, STRONG, ONE_SIDED and the 2× dominance from grounds; the
    §1d fronts.
  - Two genuine choices are their own: buffer 0 and "2 of 3". Both are stated
    with reasons, before replay.
  - Nothing looks fitted to 09-24. The TREND vote favours the day's
    direction, but that is a design bias declared in advance, not a fit.
- **Changes after data.**
  - **Cleaner than mine.** §10 changes no rule and moves no parameter. A to E
    are proposals, and each says why it was not applied.
  - I changed a label after seeing data (my §9.3, logged). It moved no
    verdict, but it was post-data.
  - Two small provenance nits:
    - the report says it was written at 00:40, while the files were last
      modified at 00:05 and 00:08. I withdraw this as a mark against them:
      my own clock times on RULES §9 were estimates too, and two were wrong
      in the same direction (corrected in RULES §9). The file mtimes are the
      record for both of us;
    - their §4 text says "HOLD at eight exits, WATCH at five", but their own
      table and engine give **9 HOLD / 4 WATCH**.
- **Hidden score?** No. "2 of 3 against" is a count. P&L is shown, grey and
  uncoloured, and feeds nothing. There are no odds anywhere.
- **Writers.** "Writer = grounds' exhaust read on the danger direction" is
  elegant and new-free. FUEL "holding / running" reads correctly for a
  writer. The weak part is STRUCTURE for writers, a tight buyer's stop (16
  pts of room). Mine shares the weakness in a different form.
- **Expiry afternoons (both sides unwinding).** Both of us inherit grounds'
  rule, so OI reads flat. **Theirs still has a working input, the line, and
  mine does not.** That is the single biggest design advantage I found.
- **Order flow blind (SENSEX prints).**
  - Theirs merges CVD and prints: against if either is against, blind only
    if both are.
  - Their replay has **no fill runs at all** ("fill runs: could not check"
    on every minute), because it never rebuilt them from `data/book`. So
    their replayed FLOW is not what the live server would have shown. Mine
    rebuilt runs identical to the server's (9 of 9 on SENSEX 09-24).
  - Their FUEL is grounds' **#1 front by session-peak OI**, not the nearer
    of the two. On 09-24 afternoon that was CE 74300, 700 points away, so
    FUEL read "unclear" while CE 74,200 and 74,000 folded at spot. Their
    proposal A admits it. My read, the nearer front plus folds as events, is
    her 2026-09-22 reading rule; theirs is not.
- **Absence.**
  - Their three sentences exist and the rows print "could not check — why".
  - But their verdict treats blind reads as "not against". On **09-21**
    (no chain record, no ladder) it says **HOLD** on structure and trend
    alone, and at 09:18 on 09-23 (fronts not yet formed) it says HOLD.
  - Mine says PATA NAHI on both. To her, OI is the point, so a HOLD with the
    OI row blind should at least say "structure only".

## 3. The window itself

| | Fable | Opus |
|---|---|---|
| size | 390 px; collapsed ≤ 640 px, one line | 388 px; collapsed 388 px, one line |
| first read | small verdict chip in a header that stays **white on HOLD** | big verdict word on a full colour band |
| second read | "line 74,037 holds (175 pts of room) · fuel unclear · flow quiet · trend 3 of 3 with you" | one sentence of facts, plus a `noise` chip |
| third read | 4 rows: structure / fuel / flow / trend, state words ("burning", "out", "unclear") | 3 rows: payers / holders / order flow, ● ✕ ○ ? marks, a count |
| calm | quieter face; flips about half as often | louder face; amber half the time before FOLD |
| buyer's clock | none | "paid last · quiet n of 15" |
| P&L | footer, grey, signed | neutral ink, in the trade's direction (+/− for a writer too) |
| light theme / no charts / [M]-[I] | yes / yes / yes | yes / yes / yes |
| float over everything | **Document Picture-in-Picture** (real always-on-top window) | only over the tool's own tabs, in my wiring |

**Theirs reads better at a glance.** "175 pts of room" is the anti-panic
number: when a red candle comes she looks at the room, not the P&L. My big
green band is attractive but louder than a HOLD needs to be.

## 4. What they got right that I missed, and what I got right that they missed

**Theirs, generously:**
1. **An index structure line with points of room.** It is a concrete level,
   visible, calm by construction, and it still works when OI goes blind.
2. **Holding on a trend day.** Folds need two independent families or the
   line, so one OI event on a counter-bounce cannot eject her.
3. **Discipline:** zero post-data rule changes.
4. **Document PiP**, which is the literal answer to her "present on any
   windows or tab".
5. **Entry and exit verdict dots in the trade list**, plus the "entered into
   HOLD" footer. Review in one glance.
6. **Spreads in the picker** (debit and credit, second leg in P&L).
7. **They froze the index candles.** I did not, and I had to recover SENSEX
   09-24 from their record after midnight (disclosed in my RULES §9).
8. **The per-(role, direction) table over every minute of every day**, a
   broader test than trade rows.

**Mine:**
1. **Her OI reading rule applied as she stated it.** The nearer of each
   side's top 2, and folds as events (the holders' fold, the payers' fold),
   not grounds' #1 front.
2. **Replay fidelity:**
   - fill runs rebuilt from the book, 9 of 9 equal to the server;
   - the grid equal to the server's (373 of 373 marks, 47 of 47 folds);
   - REST [M] premium for 09-23 and 09-24.
3. **A buyer's "nothing is paying" clock** (REASON GONE, visible as a
   countdown). Their window has no answer to "holding a bad trade in hope"
   while the line holds.
4. **PATA NAHI when OI is blind or the fronts are still forming.**
5. **A lone CVD divergence never reaches WATCH.** Order flow alone never
   folds.
6. **Better on episodes where the holders really left:** 09-23 SENSEX 74900CE
   at its high, 09-22 13:48, the 09-24 morning, the with-trend writer.

## 5. The rows where the two windows disagree, and which was right

"Right" means what the premium did next, in her direction, from the same
minute.

| trade · minute | Opus | Fable | what happened | right |
|---|---|---|---|---|
| 09-24 #1 74200PE, 10:14 | FOLD (CE 74,000 folded + put writers adding) @ 194.45 | WATCH | 234 at 10:23, 178.9 at 10:37, 620 at close | **Opus** vs Fable's own 10:37 FOLD; neither vs holding |
| 09-24 #2 (10:18–10:22) and #3–#5 (12:31–12:53) | HOLD (put writers paying) | WATCH (lone CVD divergence at the low) | #2: 234 at 10:23; #3–#5: the 74000PE reached 392 by 13:5x | **Opus** at those minutes (a WATCH at her exits nudges failure (a)); then see 13:12 |
| 09-24 #3–#5, 13:12 | **FOLD** @ 200.4 / 148.6 | WATCH, then HOLD at 13:24 | collapse from 13:25; 442 / 366 at 14:35 | **Fable**, by a lot |
| 09-24 #6, 13:25–13:26 | WATCH (CE 73,900 folded 13:19) | HOLD, 70 pts of room | 184 → 392 | Fable (both stay in) |
| 09-24 #6–#10, 13:50 | FOLD @ 333.9 / 268.8 / 207.4 | WATCH → HOLD | 384.6 at 13:54; 361.1 / 290.9 / 223.6 at 14:35 | **Fable**, modestly |
| 09-24 #11, 13:53 (entry) | FOLD at entry | WATCH at entry, then HOLD | 232 → 298 by 13:58, 223.6 at 14:35 | Fable on the next 5 min; Opus if followed (−20.2 vs −32.7) |
| 09-24 #12/#13, 14:35 | HOLD (both sides leaving; CVD her way) | **FOLD** (line broke) | 219.5 → 177 by 14:39 | **Fable** |
| 09-22 13:47 (entry) | FOLD | HOLD, 10 pts of room | +41 by 14:00, then −88 by 14:14 | split. Opus if followed (−5 vs −47.6); Fable for 12 min |
| 09-22 11:14 vs 11:19 | FOLD 11:19 | FOLD 11:14 (a 2-pt line break) | 23550PE 164 → 171 | Opus, slightly |
| 09-23 10:40 (10:19 and 10:33 CEs) | FOLD (PE 23,350 folded + divergence) @ 107.5 | WATCH / HOLD, FOLD 12:47 @ 118.8 | 111–123 in between | **Fable** |
| 09-23 SENSEX 74900CE, 12:06 | FOLD @ 256.2 | WATCH, FOLD 12:32 @ 224.9 | the 30-min high was 264.5 at 12:19 | **Opus** |
| 09-23 zone BUY 74700CE, 09:59 | FOLD at entry | HOLD, FOLD 10:11 @ −27.2 | 210 low, then 297 by 10:59 | neither (Opus lost less) |
| 09-24 writer short 74100CE, 10:40 | FOLD @ 197.15 | HOLD, FOLD 10:52 @ 221.55 | 234 high, 0.15 at close | Opus less wrong; both wrong vs holding |
| 09-21 all day | PATA NAHI | HOLD, then FOLD 14:29 (structure only) | premium could not check | cannot judge. Fable gave a verdict with OI and flow blind |

## 6. Which window would I want on my own desk, and why

**Theirs.** Her first-named problem is closing a good trade too early, and
the day in the record where that cost her most is 09-24 afternoon. There,
their window held and mine folded 13 minutes before the move. It is also
calmer (half the verdict changes per minute), it has a number she can hold
onto ("175 pts of room"), it still works on expiry afternoons when OI goes
blind, and its rules were not touched after the data.

I would not take it as-is:
- its OI read is not her reading rule (the #1 front 700 points away);
- its replay FLOW has no fill runs;
- its HOLD on blind OI should say "structure only";
- it has nothing for "nothing is paying" in a pinned range.

Those are exactly the parts of mine that hold up. Mine is better at the moment
the holders really leave (09-23 SENSEX CE, 09-22 13:48). But it reads a
trend-day consolidation as a thesis break, and on a buyer's desk that
reproduces failure (a) with better data. That is the worse error to ship.

## 7. The one merged design (a proposal, to be registered before anything is live)

1. **Face:** their quiet header (colour only on the verdict chip; white on
   HOLD). The first thing after the word is the room: "HOLD · line 74,037 ·
   175 pts of room".
2. **Float:** Document Picture-in-Picture (theirs). Fallback: the GoCharting
   extension's content script. Collapsed to one line, 400 px or less.
3. **Hard FOLD:** their STRUCTURE line (5-min PIV = 2 swing, trails one way,
   1-min index close, latched). Buffer and room minimums stay open for her
   to register or reject.
4. **The OI family is mine:** PAYERS and HOLDERS from the nearer of each
   side's §1d top 2, and folds as events (holders' fold, payers' fold). "Both
   sides leaving: OI cannot say which way" is stated, never implied.
5. **Soft FOLD needs two independent families against** (their map). The
   families:
   - OI (mine);
   - FLOW: CVD + prints, with fill runs rebuilt from the book (mine);
   - TREND: 5m / 15m / 1h (theirs).
6. **A lone CVD divergence, or a lone print count, is shown and never makes
   WATCH** (mine). That removes most of both windows' amber noise.
7. **The buyer's paid-last clock** is always visible (mine). "Nothing is
   paying for 15 min" is a **WATCH-level** state, not a FOLD. My own 9.6 test
   showed that as a FOLD it exits a trend-day consolidation one minute before
   the move.
8. **An entry read ("entered into HOLD / WATCH / FOLD")** heads the window
   for the first minutes (both). The trade list carries entry and exit
   verdict dots for review (theirs).
9. **PATA NAHI when OI is blind or the fronts are still forming** (mine). A
   structure-only minute reads "HOLD · structure only — OI could not check",
   never a plain HOLD.
10. **Writers are registered separately:** the line on the danger side with
    its room, OI "your side / would pay", no buyer-stop logic, and their own
    falsifier. Both of us folded two with-trend writers whose calls expired
    at 0.15.

My prototype carries 9.4 (their line), 9.5 and 9.6 as labelled toggles, off by
default (RULES §9). The full merged design above is not built; building it is
the next job, after she registers it.
