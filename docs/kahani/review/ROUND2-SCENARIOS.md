# KAHANI round 2 — first principles, scenario by scenario (Fable, 28 Oct 2026, after close)

Rules as amended in `ROUND1-ANSWERS.md`. Rows come from the 16 NIFTY book days (01, 05–09, 12, 13, 16, 19, 21–23, 26–28 Oct), the answers file's measurements, and `scripts/export_mockup.py` over 28 Oct 11:07–13:40 (its output is `mockup/data_28oct.json`). [M] measured there; [I] reasoned from the mechanism with no row yet. Levels s / f. Rows, never rates. Nothing under `data/` was written.

**How to read each scenario:** who is doing what → what the rules print, minute by minute → where it helps → where it misleads, and the fix. "Verdict" means the SELL / BUY band verdict at ARM → TRIGGER → +5 → +10.

**The 28 Oct reference, as the amended rules print it [M, mockup export]:**

| Minute | Chapter | Fuel | SELL verdict |
|---|---|---|---|
| 11:07 | DEEWAR 22,700s CE (STALLED, +49.1L chg; peak seen live 11:08, the 10:37 peak never seen, finding 7) | none | (a) GHUMEGA 2/2 · 1 ? |
| 11:26 | DASTAK ×1 (11:25 ▲ +213 → NAHI 11:29) | none | GHUMEGA 3/3 at 11:30 |
| 11:40–11:51 | THAKAN 11:48 → DASTAK 11:49 (§1d flickers STALL↔UNWIND) | none | flips GHUMEGA ↔ SAAF NAHI **6 times in 11 minutes** |
| 12:10 | DASTAK ×3 · RASAD bina toot (COVER 12:10, −775, ▲ shorts cover) | COVER −775 | CHALEGA 1/2 (FUEL ✗) |
| 12:12 **SELL 22,704f** | THAKAN 12:13 (UNWINDING held 3 min) | COVER −775, KHATAM 12:14 | **CHALEGA 0/2** (FUEL ✗, WALL ✗ −7.6L peak se); ARM 12:09 had read GHUMEGA 2/2 |
| 12:24–12:40 | THAKAN; pushes 12:26 / 12:40 NAHI | memory: run ▲ till 12:14 → FUEL ✗ | CHALEGA; stop 22,745f hit 12:39–12:40 |
| 12:41 | THAKAN · RASAD bina toot | COVER 12:41 (base 12:36) | CHALEGA 0/2 |
| 12:48 | TOOT? (12:44 ▲ +434 crossed −3.7L at 12:47) | −1,134 | (a) CHALEGA |
| 12:49 | **TOOT 12:44** held at 12:48 → RASAD cover ▲ | −1,134 | (b) CHALEGA 0/1 · 2 ? |
| 12:54 | NAYA FLOOR 22,700s PE +4.3L (12:49 ▼ TIKI held 12:53; flip: CE −34L off peak) | −1,493 | CHALEGA |
| 12:54–13:00 | laptop asleep: chain 12:55–12:59 missing; fuel from REST (tagged) | −2,146 by 12:59 | CHALEGA (fuel still driving) |
| 13:03 **SELL 22,821f** | KHATAM 13:03 (publish clock; 13:02 on the raw clock) | KHATAM −2,146 | **SAAF NAHI 1/1 · 2 ?** (NEXT ?, ULTA ?) |
| 13:15 **SELL 22,802f** | KHATAM | spent | SAAF NAHI 1/1 · 2 ? |
| 13:31 | **PIN** (13:19 ▼ NAHI at 22,700s PE, 13:26 ▲ NAHI) | none | (b) **GHUMEGA 2/2** at 13:31 |
| 13:32 | new fight DEEWAR 22,700s CE (BUILDING +19.2L, WAPSI) | none | (a) **CHALEGA 2/3** (FUEL ✗ "run ▲ 13:03 tak, 30 min") → SAAF NAHI 13:34 → GHUMEGA 13:37 |

Two things in that table are defects, not the market, and they recur in every scenario below: **(D1)** the verdict's WALL piece reads the raw §1d state and flickers; **(D2)** the (a) FUEL 30-minute memory survives an ending. Both fixes are in §17.

---

## 1. Trend day DOWN (08 Oct −311 pts; 21 Oct −315 pts; 01 Oct)

**Participants.** Put writers below price are run over all day: each PE front gets hit, cuts (TOOT) or is run through under water (PHANSE). Call writers above price are never tested; they add with every bounce (the CE fronts read BUILDING, fat and calm). Futures: fresh shorts on each leg (FRESH ▼), then pauses; the bounces are shorts covering a little (small COVER ▲ runs, rarely ≥ 500) and dip-buyers who become the next leg's fuel. The roll (21 Oct) is on top of all of this.

**What the rules print [M, 08 Oct and 21 Oct rows].** 28 and 26 pushes; **▲ pushes: NAHI 12 / TOOT 0 and NAHI 10 / TOOT 0; ▼ pushes: TOOT 4 and TOOT 5.** So the fights are PE fights: DEEWAR (PE) → DASTAK → TOOT → RASAD fresh ▼ (new shorts) → KHATAM → CHAL (a new FRESH ▼ run) → the next PE wall. The CE side never has a fight: every ▲ push is a NAHI at a BUILDING CE wall. On 21 Oct the fuel reads COVER 10 of 10 runs — the roll (finding 4), so RASAD prints `? (roll hafta)` all day.

**Verdict, a BUY at d2/d3 mid-trend (01 Oct 12:30 is the row: fut FRESH +1,064 [M]).** (a): FUEL ✗ (a FRESH ▼ run live or within 30 min); WALL = the PE front: UNWINDING or just TOOT'd → ✗; DASTAK = the last ▼ push: TOOT → ✗. **CHALEGA 0/3 at ARM, TRIGGER, +5, +10.** The 1 Oct row went −108 / −103 / −140 along the fade; CHALEGA is the right word. A SELL at u2 on a bounce: FUEL ✓ (fresh shorts drive the trade's way), WALL = CE front BUILDING ✓, DASTAK = the last ▲ push NAHI ✓ → **GHUMEGA 3/3**, and that is the trade of the day.

**Helps.** The TOOT tally by side (▲ 0 vs ▼ 4) is the trend signature in one chip, visible from the first PE TOOT. CHAL as an ending names "it is not over". The CE wall's calm BUILDING state tells her where the bounces die.

**Misleads.** (i) Between two FRESH ▼ runs there is a pause: a BUY arm 25 minutes after the last KHATAM reads FUEL ✓ ("koi run nahi") with the 30-minute memory expired, WALL could read STALLED (the PE front has been flat since it was hit), DASTAK ✓ if the last ▼ push was a NAHI → **GHUMEGA into a trend**. Fix: inside a fight that ended CHAL, the memory is the *fight's*, not 30 minutes: FUEL stays ✗ for a fade until a run the other way comes (§17 D2). (ii) On the roll week the fuel is "?" so the strongest piece is missing exactly on 21 Oct: the TOOT tally must stand in (§ADDITIONS #2). (iii) PHANSE (run over, under water) prints "stored fuel ahead", which is true, but on a trend day the squeeze that stored fuel promises can be days away; the chip must say `PHANSE · wapas aane pe` not "squeeze".

## 2. Trend day UP (26 Oct +301 pts)

**Participants.** The mirror: call writers above get hit and cut (26 Oct ▲ pushes: TOOT 4, PHANS 1, TIKI 3 [M]); put writers below add calmly; futures FRESH ▲ (new longs) on each leg, dips are COVER ▼ (longs closing a little). 26 Oct 09:52 / 09:56: TOOTs at 22,500s / 22,600s CE with **no floor** (the adds behind were buyer-opened, PE +4.2L / +7.3L kharidar [M, A132]).

**What the rules print.** CE fights in series: DEEWAR → DASTAK ×1–2 → TOOT → RASAD fresh ▲ → KHATAM → CHAL → the next CE wall. NAYA FLOOR never stamps (the flip rule needs WRITERS behind; the adds were buyers), so the hero reads `peeche PE +7.3L (kaun: kharidar) · floor nahi`. Three TIKI answers [M]: three walls that absorbed; the chip `dastak ×2 · jawab 1 (tiki)`.

**Verdict.** A SELL at u2 reads CHALEGA 0/3 (FUEL ✗ fresh ▲, WALL ✗ TOOT'd, DASTAK ✗ TOOT). A BUY at d2 on a dip: FUEL ✓, WALL = PE front BUILDING ✓, DASTAK = the last ▼ push NAHI ✓ → GHUMEGA 3/3.

**Helps.** Same as §1. The three TIKIs are the places a SELL could have worked for 15 minutes; the chip `jawab 1 (tiki)` is the only sign of a pause in a trend.

**Misleads.** A TIKI'd wall (absorbed) in a trend is a slow TOOT (BUILD-PLAN-FABLE §3): the verdict's DASTAK ✓ on a TIKI invites a SELL into the next leg. Fix: in a fight whose previous wall ended CHAL, a TIKI counts "·" (shown, not counted) until the wall holds a second push.

## 3. Range day (28 Oct 11:07–12:40; the 12:15–12:37 flat fut OI [M, A140])

**Participants.** Both sides write near ATM; the CE wall (22,700s) is knocked five times and shrinks without being cut (writers leaving quietly, THAKAN); futures OI flat ±80 lots a minute. Nobody is forced.

**What the rules print [M].** DEEWAR → DASTAK ×1 → THAKAN / DASTAK flicker (D1) → DASTAK ×3 · RASAD bina toot (12:10) → THAKAN 12:13. Fuel: one small COVER run (−775) then nothing until 12:41.

**Verdict.** The 12:12 SELL: **CHALEGA 0/2** on FUEL ✗ (the −775 cover run live) and WALL ✗ (THAKAN). The ARM at 12:09 read GHUMEGA 2/2 three minutes earlier. The row went +14 / −53 and the stop was hit: CHALEGA was right, and the reason it was right (a shrinking wall being knocked) was on no screen that day.

**Helps.** `dastak ×5 · jawab 0 · deewar −16.6L peak se` is the whole story of a range that is about to stop being one. THAKAN at 12:13 is 31 minutes before the TOOT.

**Misleads.** (i) D1: 11:40–11:51 the verdict flipped six times on §1d's STALL↔UNWIND flicker; a trader watching the Float would have stopped reading it. (ii) The 12:10 run is "RASAD bina toot": a range with a small cover run reads FUEL ✗ for a SELL for 30 minutes after its KHATAM (12:14 → 12:44); on 28 Oct that was right, but a −775 run that dies is weak evidence against a fade in a range that holds. Fix: the FUEL ✗-by-memory piece shows its size: `run ▲ −775 (12:14 tak)`; the verdict counts it ✗ only if the run was ≥ 2× the bar, else "·". [I], to be reproduced on the replay rows first.

## 4. Pin day (28 Oct 13:05–15:30: 39 minutes under 22,700s, CE +22.2L / PE +18.8L at the close [M, A139]; 19 Oct, 6 Oct expiry grinds)

**Participants.** Both sides write the same strike (straddle writers), each push is absorbed or ignored, futures OI flat (28 Oct 13:05–15:00: +83 lots [M]). Nobody is trapped; theta is the trade.

**What the rules print [M].** After KHATAM: 13:19 ▼ NAHI at 22,700s PE, 13:26 ▲ NAHI → **PIN 13:31**; the context chip `dono taraf deewar 1 step` (the dropped clause 2, now a chip); a new DEEWAR at 22,700s CE 13:32 with WAPSI (+19.2L rebuilt). KHAMOSH would print at 13:51 if no push came.

**Verdict.** 13:15 SELL: SAAF NAHI 1/1 at the trigger and +10, GHUMEGA 2/2 at 13:31 with the PIN. Then D2: 13:32 CHALEGA 2/3 on the dead cover run's memory, 13:34 SAAF NAHI, 13:37 GHUMEGA 3/3. Three words in six minutes on a pinned market.

**Helps.** PIN + `dono taraf deewar` + fuel flat is her theta screen: sell both sides, or nothing. The WAPSI chip says the broken cap is a cap again.

**Misleads.** D2 is the whole problem here. Fix §17.

## 5. Expiry day, weekly (NIFTY Tuesday) and monthly (27 Oct; SENSEX 29 Oct)

**Participants.** Morning: real walls at the ATM strikes, 100L+, and real fights. After ~14:30: every TOOT is writers booking the winner, every OI drop is settlement, not force (CRITIQUE S10's GAMMA ZONE). Futures: on the monthly, the roll pours into the next contract (27 Oct Nov FRESH +44,325 lots 09:20–14:16 [M]).

**What the rules print.** Every chip carries `EXPIRY`. Before 14:30 the chapters are normal. After 14:30 TOOT and PALAT pieces count "?" and the fuel reads "?" on the monthly (finding 4). The 27 Oct rows: 12:51 SELL **SAAF NAHI 1/1** at the trigger (NEXT PUSH ✓ 12:44 NAHI; ULTA known 12:53 → GHUMEGA 2/2 then; FUEL ?). 14:18 BUY SAAF NAHI 1/1 (14:04's TOOT un-crossed → NAHI; FUEL ?, WALL ?).

**Helps.** The honest "?" on fuel and on late-day TOOTs stops the 6 Oct 10:05 kind of row (expiry grind TOP, −10 / −33 / −43 [M]) from reading as a wall break.

**Misleads.** (i) On the monthly expiry the best fade day of the month (27 Oct: both of her trades) has FUEL "?" all day; GHUMEGA then needs NEXT + ULTA, which arrive after the trigger. Fix: subscribe near + next and read the next month's run (not the sum, which flips minute to minute [M]) as the fuel from T−1 on; tag `agle mahine ka`. (ii) After 14:30 a verdict with two "?" pieces is SAAF NAHI by construction; say `expiry 14:30 ke baad: sirf fuel` on the line, and after 15:00 `3 baje ke baad`.

## 6. The day after expiry (28 Oct for NIFTY; SENSEX Friday)

**Participants.** A new weekly: ATM strikes are built from the open, the biggest OI is the legacy monthly / far strikes, writers come in through the morning. On NIFTY the walls were already 50L+ of absolute OI with 15–50L of change [M, Q3]; on SENSEX the Friday after its Thursday expiry is thinner (not measured).

**What the rules print.** `fronts` ranks by absolute OI, so the morning walls are the legacy ones; every near strike reads BUILDING; THAKAN cannot occur until a peak exists (`deewar ki halat ~09:30 se`). TIKI / PHANS cross easily (every add is big relative to a young wall); TOOT rarely.

**Verdict.** (a) WALL ✓ everywhere, DASTAK ✓ on most NAHI / TIKI: a morning BUY or SELL reads GHUMEGA as soon as FUEL is ✓ — on walls that are 30 minutes old.

**Misleads.** A young wall is not a defender; TIKI on a 10L wall is a writer's first lot, not absorption. Fix: a wall younger than 30 minutes (first seen > 3L at t0) carries `nayi deewar` and its DASTAK ✓ reads "·" until it has held two pushes or is 30 minutes old. NIFTY needs no size floor [M, Q3]; SENSEX's Friday to be measured before the bar is set (Q56).

## 7. Gap up / gap down (no row among the 16 days with a > 150-pt gap; [I])

**Participants.** Gap down 150 pts: yesterday's PE writers at the old ATM are instantly under water (PHANSE at the open, no push needed); CE writers at yesterday's strikes are the new far walls; the first 30 minutes are their covering (fut COVER ▲ if shorts from yesterday's close cover; FRESH ▼ if the gap is sold). Gap up: mirror.

**What the rules print.** 09:21 at the earliest for a run (Q30). The fight: the §1d front within 2 steps in the direction of the 15-minute move; at 09:16 that is the legacy wall price just gapped through, read from absolute OI (Q69). No pushes until ~09:26 (the 10-sample rule, [M] 09:26–09:30 first push on full days). So the first 10 minutes read DEEWAR + RASAD only; if price is already 2 steps through yesterday's PE wall, §86's rule stamps **PHANSE** with no push: "run over".

**Verdict.** A gap-down BUY at d2 at 09:27: (a) FUEL = the first run (if COVER ▲, ✓: yesterday's shorts covering drive the trade's way; if FRESH ▼, ✗); WALL = the PE front: the legacy strike under price is PHANSE'd (UNWINDING) → ✗; DASTAK ? → CHALEGA or SAAF NAHI. Honest: a gap-fill trade is a fuel trade, not a wall trade.

**Misleads.** (i) The 15-minute move at 09:16 is the gap itself; the fight's direction is the gap's direction even when the first push is against it (gap-and-reverse). Fix: in the first 15 minutes the fight is born at the first *push*, not at the 15-minute move (the DEEWAR / KHISAK re-target rule in the mockup does this). (ii) Yesterday's PHANSE'd writers are the gap-fill's fuel (their buyback), which is the ledger addition (ADDITIONS #1): the open is where "under water lots" matters most.

## 8. A news spike (no row; [I])

**Participants.** A 100-point minute: both sides' near walls are cut (everyone with a short option buys it back), futures OI falls on both sides (longs and shorts stopped out), the next 5 minutes are two-way with no information. Then one side re-writes.

**What the rules print.** The jhatka guard (Q71): 1-min move ≥ 3× its 30-minute median *and* both near fronts dropping → `JHATKA (news?)`, the verdict "?" for 5 minutes. Without the guard: push 10× norm → TOOT on the attacked side, a COVER run with p5 in the spike's direction → `RASAD cover ▲ · shorts cover`, a GHUMEGA / CHALEGA on a coin.

**Helps.** The guard, plus `2/2 khisak` (both walls on the fight's side unwinding) which is what a spike looks like on the ladder.

**Misleads.** The guard's two conditions are both [I] with no row; a trend day's first leg can trip it (a 60-point minute at 09:35 with both near fronts cut). Fix: log JHATKA stamps forward with +15 / +30 and the §1o day type; the guard stays a chip (never a gate) until 15 rows exist; and the verdict's "?" is replaced by the three pieces shown with `jhatka` beside them, so she sees the pieces and the doubt together.

## 9. The first 30 minutes (28 Oct 09:20–09:53 FRESH +9,887; 10:00–10:18 FRESH +2,621 with price −124f [M])

**Participants.** Overnight orders, the auction print, fresh longs and shorts taking the day's first positions: the biggest OI run of the day, and the one whose direction matters most (28 Oct: FRESH ▼ at 10:00 = fresh shorts on the fall, the fuel of the whole morning). Walls: legacy, far.

**What the rules print.** No pushes until ~09:26 (`push padh nahi sakte: flow history`), the first run at 09:21 at the earliest, the §1d slope from ~09:30. The 09:42 BUY, 09:54 SELL, 10:24 BUY: all SAAF NAHI 1/1 on FUEL alone [M, A141]; the 09:54 SELL (fresh shorts +378 with price −17.8f) went +133 / −10.

**Misleads.** The one piece that is readable (FUEL) cannot make a verdict alone. Fix: context (c) for 09:21–10:00: FUEL counts double when |run| ≥ 2× the bar (so FUEL ✓ alone = GHUMEGA 2/2 "(c) sirf fuel"); walls are read from absolute OI with `legacy` on the chip; DASTAK "?". One row (09:54) supports it; it goes to the replay rows (reproduction, not tuning) and forward.

## 10. The last hour: 14:30–15:30, CAS at 15:15, F&O to 15:40

**Participants.** 14:30–15:00: position squaring; 15:00–15:15: the last real pushes; 15:15: the cash index freezes (CAS), options keep trading on a frozen spot to 15:30, futures to 15:40 with the basis doing the last move. Writers who are still under water at 15:00 cover into the close (the 28 Oct −701 lots into 15:39 [M, A139]).

**What the rules print.** Spot pieces (through, the 2-step band, DASTAK at a strike) freeze at 15:15 (Q72); the chain runs to 15:30; fuel on fut to 15:40 with `KHATAM nahi (band 15:30)` for an open run. After 15:00 every verdict carries `3 baje ke baad`.

**Misleads.** (i) 15:15–15:30: a push into a strike with a frozen spot reads the answer at a wall price is no longer at. Fix: after 15:15 the fight's price is fut converted by the 3-minute basis, tagged `f→s`. (ii) A COVER run 15:20–15:39 is the day's trapped side covering: not a fuel read for tomorrow, but its lots are the one number worth printing at the close: `band pe cover −701: kal ke liye kam eendhan`.

## 11. Roll week (T−3 to the monthly expiry; 21–27 Oct [M])

**Participants.** Near-month positions move to next month: the near contract's OI falls mechanically every afternoon (21 Oct COVER 10 of 10 runs; 22 Oct 6 of 9 [M]) while the next month's rises (27 Oct Nov +44,325 lots [M]); the sum flips sign minute to minute [M]. Real fuel is hidden under the roll.

**What the rules print.** `RASAD ? (roll hafta)` from T−3 (finding 4). Chapters run on the walls alone; the verdict loses its strongest piece for four sessions a month.

**Fix (disagree with "unless both subscribed and summed", agree with the subscription).** Read the **next month's** run alone from T−3 (it is the live money; the near is the exit), tagged `agle mahine ka`, with its own bar measured from its first week of rows (not tuned: the same 500-lot bar until rows say otherwise). The sum is the wrong object: two contracts with opposite mechanical flows.

## 12. Laptop sleep (28 Oct 12:54:12–13:00:20 [M])

**Participants.** The market did its last leg (22,815 → 22,875.5f) while nothing watched.

**What the rules print [M].** Book hole 374 s; the 13:01 +3,534 push dropped as an artifact (§7); minute 12:54 a hole (12 s of rows, finding 5); fuel 12:55–13:00 from REST tagged `rest`; chain 12:55–12:59 missing → the 12:53 push's answer reads at 13:00 (TOOT −6.6L held 13:00), the §1d slope "?" over the gap until the chain backfill (Q60). KHATAM 13:03 by the publish clock (13:02 raw). Coverage: `laptop soya 12:54–13:00 (Critical Battery 12:53:51)`.

**Helps.** The REST fill makes the fuel the one read that survives the sleep; the artifact rule removes a fake 7× push.

**Misleads.** The hero on wake-up at 13:00:36 shows RASAD live at −1,493 (the last book value) for one pass before REST lands; a trader reading that minute sees the fuel "still running". Fix: on a hole the fuel chip reads `? (bhar rahe)` until REST has landed, never the stale number.

## 13. Feed hole (Upstox outage, token death: 28 Oct 09:15–11:07 [M, A133])

**Participants.** The market opens; the server records nothing (dead token), the extension still posts frames.

**What the rules print.** Everything before 11:07 is "?" with its reason; the chain backfill seeds the §1d peaks (finding 7: without it 22,700s CE's peak reads +49.8L at 11:08 instead of +57.1L at 10:37); pushes from 11:25; fuel from REST for 09:15–11:07 tagged `rest` (REST was complete [M]).

**Misleads.** The morning's two FRESH runs (+9,887 and +2,621 ▼) are the day's story and are known only by REST; if the REST backfill runs once at start and the window still shows `?` for the morning, the afternoon's reader does not know ~10K lots of morning shorts are open under water [I, A139]. Fix: the fuel card's day strip is always REST-backed for the minutes the book missed, and the ledger (ADDITIONS #1) is seeded from REST too.

## 14. Dext absent (28 Oct: all 18 pushes from the book; 27 Oct Dext blank from 12:02 [M])

**What the rules print.** With book-primary flow (Q12) nothing changes when Dext is absent; Dext is a cross-check line `Dext: nahi`. The push median is the book's only.

**Misleads.** None in KAHANI once book-primary; the one open item is the scale check (Dext delta vs quote-rule delta on 27 Oct morning) before Dext is shown as a cross-check at all.

## 15. BANKNIFTY and SENSEX with no answer bar

**Participants.** BANKNIFTY: monthly only, the attacked strikes carried 1.3–1.4L with 0.0L change in 4 minutes on three pushes [M]; its minute OI may not move at all. SENSEX: weekly, thin futures, walls 6–16L; NIFTY's pushes (§1q); at a pure 4 % bar 12:40 ▲ and 12:44 ▲ would have read TOOT (−1.1L on 15.7L, −2.5L on 14.6L at 73,200s) [M].

**What the rules print.** SENSEX: DASTAK ×n forever, `jawab padh nahi sakte (bar baaki)`, fuel = NIFTY's RASAD, the context chip `NIFTY ki kahani: TOOT 12:44`, `teeno saath ▲` at 12:44 [M]. Verdict: `GHUMEGA mumkin nahi · sirf FUEL + WALL` in (a); in (b) FUEL only. BANKNIFTY: the same, with its own fuel (bar 200, 1–11 runs a day [M]) and the answer "?" until its minute OI is shown to move.

**Misleads.** A SENSEX SELL at u2 with NIFTY's cover run live reads CHALEGA (FUEL ✗) — right on 28 Oct. A SENSEX SELL on a day NIFTY and SENSEX diverge (SENSEX's own OI walls holding while NIFTY's break) has no piece that can say so. Fix: set SENSEX's bar from its 330 logged pushes in step 2 (decided), and until then show the two SENSEX pieces plus NIFTY's three as `NIFTY: …` on the same card, never summed.

## 16. The table: scenario → the one thing she must see

| Scenario | The one thing on screen |
|---|---|
| Trend down / up | `TOOT ▲ 0 · ▼ 4` (the session tally by side) beside `CHAL` |
| Range | `dastak ×5 · jawab 0 · deewar −16.6L peak se` (THAKAN) |
| Pin | `PIN · dono taraf deewar 1 step · fut flat` |
| Expiry (weekly / monthly) | `EXPIRY` on every chip; after 14:30 `sirf fuel`; monthly `fuel: agle mahine ka` |
| Day after expiry | `nayi deewar (28 min)` on every wall under 30 min old |
| Gap | `PHANSE · kal ke writers paani mein −x L` with the ledger's under-water lots |
| News spike | `JHATKA (news?)` with the pieces still shown beside it |
| First 30 min | `(c) sirf fuel: FRESH ▼ +2,621 naye short` |
| Last hour | `3 baje ke baad`; at the close `band pe cover −701` |
| Roll week | `fuel: agle mahine ka` (never `?` for four sessions) |
| Laptop sleep | `laptop soya 12:54–13:00` and the fuel chip `? (bhar rahe)` until REST lands |
| Feed hole | the morning's runs from REST on the day strip, tagged |
| Dext absent | `Dext: nahi · flow = book` (nothing else changes) |
| BANKNIFTY / SENSEX | `jawab padh nahi sakte (bar baaki) · GHUMEGA mumkin nahi` and `NIFTY ki kahani: …` |

## 17. The two fixes that every scenario needs (both are KAHANI's own reads; §1d is untouched)

- **D1 — the WALL piece uses the held state, with hysteresis.** Enter THAKAN / KHISAK when §1d reads UNWINDING for 3 consecutive marks (decided); **leave** it only when §1d reads BUILDING for 3 consecutive marks (STALLED keeps it). The verdict's WALL piece reads this held state, the same one the stamp uses. Evidence: 28 Oct 11:40–11:51, six verdict flips and a THAKAN 11:48 → DASTAK 11:49 → THAKAN 12:13 chain [M, mockup]. The raw §1d state stays visible as the chip's small text (`§1d: stalled`), so her registered read is never hidden, only not flickered.
- **D2 — an ending clears the fuel memory.** The (a) FUEL "run against in the last 30 minutes" is the *fight's* memory: a KHATAM followed by PIN / KHAMOSH / PALAT clears it; a KHATAM followed by CHAL keeps it until a run the other way. Evidence: 13:32 CHALEGA 2/3 on a pinned market [M, mockup].

Both are reproduced by the mockup export and must be reproduced by `test_kahani.py` before the rows are read as more than rows.
