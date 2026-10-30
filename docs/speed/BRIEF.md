# RAFTAAR — the real-time OI speed analyser: design brief (27 Oct 2026, written live, Oct monthly expiry)

Two designers, Fable and Opus, design this BLIND in round 1, critique each other in round 2, and converge in round 3.
The trader decides nothing up front: you decide every design and method question as a pro options trader would, with
evidence from the recorded days (her standing rule). She reads the result.

## 1. Who it is for

Mary: a discretionary NIFTY / BANKNIFTY / SENSEX weekly-options trader at prop scale (₹1–10 cr, zero brokerage). She buys
OR sells by market condition (ATM / ITM with the trend), and reads OI AT LEVELS: dealers hunt liquidity, writers defend
strikes, and trapped writers are the fuel. Read these first (they are short):
`C:\Users\kaam\.claude\projects\C--Users-kaam-Desktop-operator-mode\memory\`
- `user-mary-trader-profile.md`, `operator-thesis.md`, `oi-liquidity-hunt-thesis.md`, `how-she-sells.md`
- `read-changes-not-levels.md`, `read-her-method-before-designing.md`, `read-like-claude-direction.md`
- `tool-not-essay.md`, `symbols-need-hinglish-chips.md`, `light-mode-only.md`, `no-charts-reads-only.md`, `levels-tag-spot-or-fut.md`
- `tapemap-dead-hypotheses-and-house-rules.md`, `oi-edge-fable-2026-10-22.md`, `sensex-nifty-flow.md`

## 2. Her words, verbatim

First ask (27 Oct ~11:35):
> "i want you to work at something is the rate of change or speed of oi writing and covering once they stop like we mark
> on board tab i want it a like realtime tool to check the speed of both of these let say today itit marks ruka for ce
> 22700 at 09:27 and than it might have have started covering or something and other might accelerating or maybe they
> are also not building and what price is doing to check releative strenth as well effort vs result and when lets say
> again start building we should mark that time as well like they again started building you getting brain strom this i
> want it a real time dashboard which can tell all this peed and evevrything so that i one glace one can see if this
> accelrating or staying steady or declinging etc i hope you got me ."

Her rejection of the first build (27 Oct ~12:00):
> "i dont like this design send fable and instruction to make this real time analysier tp check what happening whats not
> in you deign in the bottom you have every writing stopping its not its for you to see and tell if its noise like if
> nothing signiciant happend say show if you keep showing ruke and likhe rhe h i will be confuse but these rate of change
> or speed will tell me if a a move is happening or market just chopping up and down and both side is writing or
> somewhat holding eual amount of position so its pin . sp brain strom with each other think and explore how we should
> build it . as a trader think ."

## 3. What was built, and why it failed

`tapemap/ui-v2/src/speed/speed.ts` (engine) and `SpeedTab.tsx` (face), live at http://127.0.0.1:5173 → **Speed** tab.
Read them, do not edit them. For her nine strikes nearest spot it shows, per strike-side, a flow word (LIKH RAHE / RUKE /
CHHOD RAHE), OI per minute over 5 min vs the 5 before, an acceleration word, a price word, and at the bottom KRAM: every
flow change of every strike, held 3 min, newest first.

**Why she rejected it.** It hands her the raw material and makes HER judge. Eighteen strike-sides flipping between
"likh rahe" and "ruke" is noise to a trader. What she wants is the judgement:
- **Is a MOVE happening** (which way, starting / accelerating / tiring)?
- **Or is the market CHOPPING** (price up and down, both sides writing in turns, nothing building)?
- **Or is it PINNED** (both sides writing or holding about equal positions around a strike)?
- When **nothing significant** happened, say so in one line and show nothing else.
- When something significant DID change (a side that stopped starts again, a side starts covering into price), say it once,
  with its time.

The speed / rate of change is the instrument. The screen's job is to say what it means.

## 4. What is already known: do not rediscover it, and do not contradict it without evidence

- **§1d fronts** (`tapemap/fronts.py`, registered, NEVER change): the top 2 per side among the nine strikes nearest spot,
  BUILDING / STALLED / UNWINDING on a 15-mark slope against the front's own peak. The Board tab shows them.
- **§1o one-sided meter** (`tapemap/onesided.py`, registered): the day type from per-5-min-bar votes.
  - TREND: one-sided bars ≥ 10, ≥ 80 % one way, flips ≤ 1, VWAP crosses ≤ 2.
  - PIN: range < 0.5 % of the open and VWAP crosses ≥ 4.
  - CHOP: crosses ≥ 4 or flips ≥ 3.
  - Your design must relate to it: reuse it, or say exactly what OI speed adds that it lacks. Never a second, contradicting
    day type.
- **THE READ** (`read.py`) and **DECODE** (`decode.py`, its DIN line) already print a day call. The doctrine is ONE VOICE: a
  new screen that disagrees with them must say why, never just disagree.
- **oi-lab** (Fable's clean-room research, `C:\Users\kaam\Desktop\operator mode\oi-lab\README.md` and `AUDIT_OI.md`):
  - no OI state at a fresh extreme separated holds from breaks at 30 min (DEFENDED 53 % held vs QUIET 59 %);
  - "OI speed into the pivot" was killed (look-ahead);
  - the futures leg did separate (fut OI flat + buyers hitting held 71 %), and so did composition and trapped writers;
  - effort per point (`effort.py`) is the one order-flow read that survived.

  So OI speed is a **STATE read (what is happening now)**, judged forward. Never sell it as a hold/break predictor.
- **House rules:**
  - Never print a hit rate, win rate or % confidence: agreement counts only.
  - Every number is [M] measured or [I] inferred.
  - Three absences are three different sentences: checked and found nothing / could not check / not showing.
  - A missing value is never a zero.
  - Every level is tagged spot (s) or fut (f).
  - LIGHT theme only. Terminal-like: grids, numbers, state pills, ≤ 6-word cells, and a Hinglish chip with its number on
    every glyph.
  - No price chart (she has her broker's charts). OI or speed sparklines are fine.
  - No new backtests or cache-slicing for edges (research-findings §5 stop rule). Running a design causally over past days
    to show what it WOULD HAVE SAID is fine and wanted: rows, not rates.
  - Display only. No order path, ever.

## 5. Data (read-only)

- **Option chain record:** `tapemap/data/chain/chain_<IDX>_<day>.jsonl` (`.gz` for older days). 41 days per index, 7 Sep →
  27 Oct 2026. One row per ~10 s:
  `{ts "HH:MM:SS", sec, spot, atm, strikes:[{k, ce:{ltp, oi, oi_chg, iv, vol, bid, ask, avg, gamma, delta}, pe:{…}}], ik, expiry}`.
  `oi_chg` = OI minus the 09:15 open. Today's NIFTY file was repaired at 11:12 (NOTEPAD A125). The file on disk is good;
  before the repair its near-ATM legs read 0.
- **Live minute grid:** `GET http://127.0.0.1:8765/api/oihist?idx=NIFTY|BANKNIFTY|SENSEX` returns
  `{minutes: {"HH:MM": {spot, k: {strike: [ce_chg, pe_chg]}}}, fronts, folds, …}`. At most one request per 15 s: the market
  is live and it is her server.
- **Also there:**
  - the futures book (`data/book/`, read by `effort.py`);
  - the GoCharting tape (`data/tape/`);
  - VPIN (`vpin*.py`);
  - the §1o daily rows (`data/onesided/onesided_log.jsonl`);
  - `chain_metrics.py` (how the minute grid is built), `sides.py`, `trap.py`.
- **Days:** use at least 5 of different kinds: a clean trend day (8 Oct trended down), a chop day (22 Oct, a stop-loss day),
  a pin / range day, an expiry day (27 Oct, the Oct monthly, is today), and others you pick from the §1o log and your own
  read. NEVER design off one day. Check BANKNIFTY and SENSEX too; SENSEX reads NIFTY's order flow but its own OI (§1q).

## 6. Rules for you

- Design only. Do not edit any file outside `tapemap/docs/speed/`.
- Never write under `tapemap/data/`.
- Never start, stop or restart a server.
- Never open anything under `tapemap/telegr/`.
- Python is `python`; stdlib only. Keep your scripts in your own folder.
- Write as a pro trader reads: short, numbers first, no essays.

## 7. Round 1 deliverable (BLIND: do not open the other designer's folder)

`tapemap/docs/speed/<fable|opus>/DESIGN.md`:

1. **The trader's question** in three lines.
2. **The states the screen can say** (your words; for example CHAL RAHA ▲ / THAK RAHA / CHOP / PIN / KHAMOSH). For each:
   - its exact causal definition from the minute grid (plus futures or tape if you use them);
   - every number tagged [I];
   - why a trader needs it.
3. **Significance:** how noise and quiet are decided, relative to what (the day's own distribution at that time, the strike's
   size, the index), and when, and only when, a line is stamped.
4. **The one-glance screen:** an ASCII wireframe, or a LIGHT HTML mockup in your folder. Say what is big, what is small, and
   what is hidden until asked.
5. **Replay:** your design run causally over ≥ 5 real days, as a state timeline per day (what it would have said, and when),
   with the script in your folder. Rows, not rates.
6. **Where it meets §1d, §1o and THE READ,** and how it avoids being a second, contradicting voice.
7. **What you could not check,** plus at most 3 open questions you would put to the trader.

Round 2: you will be sent the other designer's DESIGN.md to critique. Round 3: one converged design plus a real-data
mockup.

## 8. ADDENDUM — her correction, 27 Oct ~12:10 (overrides §4's "never contradict" and widens §3)

Her words, verbatim:
> "bro contradict if it things its wrong but able to seprate noise from real change detect the speeding up or slowing
> down to help gauge the market because let call writer are covering 22600 22700ce but still holding 22800 ce or may be
> adding position there to cap because writers are on both side . write and vice versa or change in price in comparison
> to oi change that tell us a different story is in it imagne all the possible combination that can happen and rate or
> grdae them and put all of them together to see the real picture"

What this changes:

1. **Contradict when the evidence says so.** RAFTAAR may disagree with §1d, §1o, THE READ or DECODE. When it does, it
   says so in one line, and says WHY with the numbers (e.g. "READ: TREND ▲ · RAFTAAR: PIN, both sides +40L/15m at 22,750,
   spot ±8"). It never edits or overrides the registered rules; it stands beside them. What is still forbidden is silent
   disagreement, and disagreement on noise.
2. **Read the structure ACROSS strikes, not per strike.** Her example: CALL writers covering 22,600 / 22,700 CE while
   holding, or ADDING at 22,800 CE. That is not "calls covering"; it is the cap being ROLLED UP (writers moving their wall,
   still short calls), a very different story from calls covering everywhere (retreat, fuel). The same for puts, mirror
   image. Writers sit on both sides, so read both sides' structure together.
3. **Price vs OI change tells its own story.** For example:
   - price up while CE OI adds: writers absorbing, or getting trapped;
   - price up while CE OI falls: short covering, fuel;
   - price flat while both add: a pin being built;
   - price moving while OI is silent: a move with no writer behind it.
4. **Enumerate ALL the combinations.** Cover:
   - each side's flow by zone (ITM-side / ATM / OTM wall), including roll up / roll down;
   - each side's speed change (accelerating / steady / slowing);
   - the price move and its effort vs result;
   - optionally the futures leg and the other indices.

   Name each combination as a trader would. Then **GRADE** each one: how strong the evidence is, from its size against the
   day's own distribution at that time, its persistence, and its agreement across strikes and indices. A grade is a
   strength-of-evidence label or an agreement count, NEVER a probability, % confidence or hit rate.
5. **Put them together into ONE picture.** The screen leads with the strongest graded story now. It says when nothing
   clears the noise bar. It stamps a line only when the graded story changes. Show the combination table (all states,
   their definitions, their grades) in DESIGN.md, and replay it over the real days.

## 9. ADDENDUM — on her chart, 27 Oct ~16:00

Her words, verbatim:
> "can we put it on chart as the chart moving we are plotting it there"

The picture must also live ON her GoCharting chart (standing direction: the read lives on her chart), drawn by the
extension's overlay (`C:\Users\kaam\Desktop\Go charting\orderflow-desk\src\shell\overlay.js`). Read its header first: it
draws only what `main.js`'s face() decides, it keeps a LINE BUDGET (2 flat, 5 in a trade), ≤ 6 chips of ≤ 4 words,
fut | spot chips, KHEL shading under bars, ranked marks in the bar gutter, and the deewar (wall) lines. RAFTAAR must fit
inside that grammar, never add clutter beside it.

Design the chart layer:
- **The picture over time:** a thin state ribbon (one cell per bar), shaded by the big word, with the grade as strength.
  CHAL ▲ / ▼, CHOP, PIN, ATKA, WAPSI and KHAMOSH must each be readable; KHAMOSH is blank.
- **The stamps:** one mark at the bar where the graded picture changed, with a ≤ 4-word Hinglish chip carrying its number
  (e.g. "CHAL ▼ 8/10", "PIN 22,750s", "CAP UPAR 22,850").
- **The writer structure on price:** the cap / floor walls as the existing deewar lines, moving when they roll (e.g. CE cap
  22,700 → 22,850), tagged s / f. Never a second set of lines.
- **Hover:** the full one-line story and the contradiction line, if any.
- **Budget:** what is shown flat vs in a trade, and what gets hidden when the budget is full.
- **Mockup:** her real chart with the layer drawn on it, LIGHT, at the same four real moments.
- **Build path:** /api/raftaar → the extension's existing poll of TapeMap → face() → overlay. Same JSON for the ui-v2 tab.
