# Hold-or-fold window: REPORT (Opus 5.5)

*Saved by the coordinator from the agent's final message. The agent's harness blocked it from writing
this file. The text is the agent's own.*

## Paths
- `RULES.md`: written 2026-09-24 23:45, before any replay. §9 logs every change since, including one
  made after seeing data.
- `hold-window.html`: the prototype, 2.7 MB, self-contained, light. It was checked in Chrome at about
  1536×695 with no console errors.
- `verdict.js`: the rule, written once. The page and the tables below both run it.
- `scratch/`:
  - `build_facts.py`: per-minute facts, built only from TapeMap's `fronts` / `board` / `grounds` /
    `trendbox`.
  - `trades.py`: FIFO round trips and examples.
  - `replay.js`, `follow.js`.
  - `frozen_*`, `rest_opt_*`: the frozen 09-24 data.

**Implementation checks (not evidence).** The 09-24 SENSEX OI grid rebuilt here matched the server's
`/api/oihist` exactly: 373 of 373 recorded minutes, all 47 folds and all 9 fill runs. Folds on a grid
cut at any minute match folds on the full grid.

## The window
1. It floats about 390 px wide, drags anywhere, and collapses to one line: `FOLD · SENSEX 74,100 CE short
   · you −8.1% · Thesis broken: …`.
2. **First:** the verdict word, big, on a colour band:
   - HOLD in calm green;
   - WATCH in amber, silent;
   - FOLD in solid red, the only state that shouts (one pulse, optional single tone);
   - PATA NAHI in grey.

   Beside it: how long it has stood, and a DRAFT stamp.
3. **Second:** one sentence of facts, e.g. "Thesis broken: CE 74,200 folded 13:39, and CVD turned against
   you".
4. A small `noise` chip marks a HOLD whose premium is under water while its reason still stands. The big
   word stays HOLD, so it doesn't flicker.
5. **Third:** a three-row ledger, each row marked ● for / ✕ against / ○ flat / ? blind:
   - **PAYERS**: the writers forced if the move goes her way;
   - **HOLDERS**: the writers whose staying protects her ("your side" for a writer);
   - **ORDER FLOW**: 15-min CVD with its rank, prints of size, divergence.
6. Under the ledger: "n for · n against — a count, not odds".
7. Buyers get a clock: "paid last 13:57 · quiet 3 of 15 min", with 15 ticks, so the "reason gone" FOLD is
   never a surprise.
8. A WATCH always says what would turn it into a FOLD.
9. Context, small and grey, never a vote:
   - the premium, her entry, and the change in her direction, in neutral ink (never red or green);
   - σ against the premium's own session VWAP;
   - spot, and the 5m / 15m trend rows.
10. There are no charts. The page around the window is only a replay harness:
    - a trade list;
    - a strip coloured by verdict for each minute;
    - a change log;
    - a "what it said at her fills" box;
    - a custom trade form.

## The rules in brief
- **The trade becomes a direction and a role.** Long CE or short PE bets up; long PE or short CE bets
  down.
  - **Q** = the writers who pay if price moves her way.
  - **R** = the writers whose staying protects the trade. For a writer, R is her own side.
- **The facts:**
  - §1d state of the nearer of each side's top-2 fronts;
  - folds that are still folded;
  - grounds' 15-min CVD (rank and divergence) and prints of size.
  - When both sides are unwinding, OI reads flat, because it can't say which way.
- **FOLD, thesis broken, either way:**
  - **A:** an R-side fold in the last 15 min, still folded, plus one confirmation: Q writers adding (held
    3 min), CVD against, or prints against.
  - **B:** Q writers adding and R writers leaving, both held 3 min.
- **FOLD, reason gone (buyers only):** nothing has paid for the trade in 15 readable minutes.
- **WATCH:** any single fact against, short of FOLD. It is not an exit. Order flow alone can reach WATCH,
  never FOLD.
- **HOLD:** otherwise.
- **PATA NAHI:** grid stale, fronts not read, or fronts still forming (fewer than 15 one-minute marks).
- **Latch:** once FOLD fires it stays FOLD for that trade.
- **Numbers:** the only new ones are 3 min persistence, 15 min recency and 15 min reason-gone, all
  reused from windows the house already uses.

## Her 13 exits, 09-24
It reads the minute finished before each fill. "Follow" means holding from her entry to the window's
first FOLD; points are in her direction.

| # | trade | at her exit | follow the window | her exit (pts) |
|---|---|---|---|---|
| 1 | 09:42 74200PE | HOLD: put writers paying, PE 74,100 folded 09:46 | FOLD 10:14 @ 194.5 (+15.2) | 203 (+23.8) |
| 2 | 10:19 74200PE | HOLD: PE 74,000 folded 10:22 | FOLD 10:37 @ 178.9 (−43.7) | 234 (+11.4) |
| 3 | 12:32 74100PE | HOLD | FOLD 13:12 @ 200.4 (−2.0) | 216 (+13.7) |
| 4 | 12:35 74000PE | HOLD (noise) | FOLD 13:12 @ 148.6 (−31.2) | 161 (−18.8) |
| 5 | 12:44 74000PE | HOLD (noise) | FOLD 13:12 @ 148.6 (−19.4) | 160 (−8.0) |
| 6 | 13:26 74000PE | WATCH: CE 73,900 fold, unconfirmed | FOLD 13:50 @ 333.9 (+149.7) | 220 (+35.8) |
| 7 | 13:41 73900PE | HOLD, then WATCH at the final fill | FOLD 13:50 @ 268.8 (+78.7) | 193 (+3.0) |
| 8 | 13:43 73900PE | WATCH | FOLD 13:50 (+62.2) | 207.3 (+0.8) |
| 9 | 13:44 73900PE | WATCH | FOLD 13:50 (+38.3) | 237.6 (+7.2) |
| 10 | 13:45 73800PE | WATCH | FOLD 13:50 @ 207.4 (−3.7) | 217.1 (+6.0) |
| 11 | 13:54 73800PE | FOLD, already at entry | (−20.2) | 240 (−12.2) |
| 12 | 13:57 73800PE | HOLD: CVD her way | FOLD 14:40 @ 182.2 (−85.3) | 297 (+29.6) |
| 13 | 14:23 73800PE | HOLD (noise) | FOLD 14:40 @ 182.2 (−105.3) | 294.8 (+7.4) |

At her final exit fills it said HOLD 7 times, WATCH 5 times and FOLD once. The CE 74,000 fold at 14:12
produced only a WATCH (14:14 to 14:20) because nothing confirmed it. By 14:21 both sides were leaving,
OI read flat, and the FOLD came at 14:40, 16 minutes after the 14:24 low.

## 09-23 (range day) and other days
Her seven NIFTY 23450CE / 23400PE entries, and what the window said at each entry:

| entry | window at entry | her result |
|---|---|---|
| 09:18 | PATA NAHI (fronts still forming) | −65 |
| 09:47 | WATCH: call writers adding in its way | −497 |
| 09:49 PE | WATCH | −52 |
| 10:00 | **FOLD at the entry minute**: PE 23,450 folded 09:57, call writers adding | −507 |
| 10:19 | HOLD | **+205** |
| 10:33 | HOLD (then FOLD at 10:40; she exited 11:04 about flat) | −29 |
| 11:07 | WATCH: new high without CVD | −367 |

- Her two HOLD entries were her two best rows. That is seven rows on one day, not a rate.
- On this personal account each round trip is charged, so the entry read is where the window earns its
  keep on a range day.
- SENSEX 74900CE (11:32): HOLD with noise at her −₹305 exit. The window's FOLD came at 12:06 at 256.2,
  the 30-minute high.
- The zone machine's 09:57 BUY examples (long ATM CE, one per index) both got FOLD at entry. The SENSEX
  74700CE then rose from 237 to 298 inside an hour, so that FOLD misled.
- 09-22 was an expiry day: the 13:48 PE was FOLD at entry, and that was her +₹1,410 trade.
- 09-21 is PATA NAHI: there is no chain record that day, and the 09-22 weekly can no longer be rebuilt
  from REST.
- Writer examples:
  - the 09-24 short PE against the trend was folded 2 minutes in (it later went to 619);
  - the 09-24 short CE with the trend was folded at 197 (it went to 234, then 0.15 by the close);
  - the 09-23 short CE was folded flat.

## Where it would have misled her
- **(a) Folding good trades.** It happened at 09-24 10:14, 10:37, 13:12, the 13:53 FOLD at entry, 09-22
  13:47, the 09-23 zone buys and the 09-24 short CE writer. The cause each time: the other side's writers
  folded on a counter-bounce inside a trend. That is usually the ceiling moving to a lower strike, not
  disappearing.
- **(b) Holding bad trades.**
  - #12 and #13 across the 14:24 low: from 14:25 to 14:38 the premium went 283 → 188 while the window
    said HOLD. The two causes:
    - both sides were unwinding on the expiry afternoon, so OI went blind (49 such minutes on 09-24
      SENSEX, all after 13:30);
    - the 15-minute CVD lagged.
  - Before a post-data label fix (§9.3), the window even called that slide "noise". The fix changes the
    words only, no verdict.
  - It also held #4 through 179.8 → 137.9. On 09-22 09:42 and 09-23 09:49 its FOLD came later and worse
    than her own exit.
- **Where it helped:** #6 to #9, where holding to 13:50 beat her exits by a wide margin; the SENSEX
  74900CE; the 09-22 10:32 put; the short-PE writer.
- **The honest limit:** it separates "writers still paying" from "nothing paying" well. It can't yet
  tell a squeeze-bounce inside a trend from the end of the trend, and it goes blind to OI on expiry
  afternoons. Every day she traded was an expiry day for her contract except 09-23 NIFTY.
- **Other limits:**
  - SENSEX prints were blind for 331 minutes on 09-23 and 100 on 09-24, so SENSEX order flow is mostly
    CVD.
  - The 09-22 premium is inferred from the chain record, not measured.

## What she must pre-register
1. **The rule:** RULES.md §2–§5 as written, plus three changes in §9:
   - §9.1: fronts still forming = PATA NAHI;
   - §9.2: the reason-gone clock counts readable minutes only;
   - §9.3: the `noise` label needs a standing fact. This one was made after seeing data.
2. **The parameters:** everything §1d and grounds already fix, plus 3 / 15 / 15. Never grid-searched.
3. **Her decision on three candidate fixes found but NOT applied** (seen on one day only):
   - (i) an opposing fold breaks the trade only if that side isn't re-building nearer spot;
   - (ii) what to do on expiry afternoons when both sides are unwinding;
   - (iii) exempting writers from "the paying side is adding" as a WATCH.
4. **Predictions and falsifier (§8):**
   - minutes marked HOLD with noise are followed by a larger 30-minute favourable move than FOLD
     minutes;
   - FOLD fires within 5 minutes of entry on a minority of trades. Here it was 3 of 28 readable trades,
     all at the entry minute;
   - it dies if that fails over at least 15 stamps each, or if the result collapses when the best day is
     removed.
5. **Two method calls only she can make:**
   - should a writer share a buyer's break rules?
   - should FOLD at the entry minute read "the thesis was already broken when you entered"?
6. **A write-once forward log:** `data/hold/hold_<day>.jsonl`, every minute's read for every trade she
   marks, never edited.

## Wiring, smallest first
0. Register (the list above). No code before that.
1. **`hold.py`, pure:** a port of `verdict.js`, so the rule lives once, in Python. It uses the same
   per-minute facts, plus one assert-based self-check on a frozen 09-24 slice.
2. **`GET /api/hold?idx=&k=&side=&role=&t0=&p0=&qty=`:**
   - it reuses the server's existing pieces: `_board_core` (grid cut to the minute, folds, peak),
     `_board_facts` (CVD and prints), `_board_trend`, and `live.build_contract` for the premium;
   - it caches one row of facts per index per minute, so each request only applies the rule;
   - anytime-start holds: the grid is backfilled exactly, and the ladder and fill runs are rebuilt from
     the book record on restart.
3. The forward log above, written by `/api/hold`.
4. **A ui-v2 floating component at the app root, so it's on every tab:**
   - a trade form, kept in `localStorage`;
   - it polls `/api/hold` every 15 s;
   - the prototype's markup is the spec.
5. **Later, optional:**
   - the same one line in the GoCharting extension;
   - a read-only prefill of her position from PaperDesk. Never an order path.

Nothing in `ui-v2/src`, any repo `.py`, the extensions or `data/` was touched. No server restart, no
git. `docs/hold/fable/` was never opened.
