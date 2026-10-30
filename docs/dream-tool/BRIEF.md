# THE DREAM TOOL — brief for Fable (27 Oct 2026)

You are designing the live, real-time trade tool Mary has been trying to describe for months. She asked for
you by name: "send it to fable and ask him to design mockup for us and he can further explore every
possibility of making the dream come true ... ask him go insane completely. its a dream tool for me."

Go insane on IDEAS and on CRAFT. Stay strict on the house rules at the bottom: they are not style; each one
exists because a past build hurt her.

---

## 1. Who she is (60 seconds)

Mary is a discretionary NIFTY / BANKNIFTY / SENSEX options trader. She buys OR sells options depending on the
market (ATM or even ITM with the trend). She reads order flow on a GoCharting 5-minute footprint chart, her
ZONE on 3-minute bands, and OI on the nearest-ATM strikes. She trades SENSEX on NIFTY's order flow plus
SENSEX's own OI. Her exits come from zones, levels, order flow and OI, never from a candle close or a fixed
strike stop. She stops new trades after 15:00.

TapeMap (this folder) is the brain: a Python server that records the market from Upstox and computes every
read. A Chrome extension draws on her GoCharting chart. TapeMap decides; the extension only draws.

## 2. Her words, verbatim (do not paraphrase them away)

**26–27 Oct, the ask that started the live chart:**

> "think items where live on chart things getting triggered flashed on placed and then as things are building
> or cvd moving it showing whats happening like a live analysing everything and you now stays as green if
> trends continuous and maybe change color as it getting strengthen levels flashing in chart which we are
> targeting stoploss placed . pull backs or telling us as buyers and seller interacting in the move where it
> leaning or who is winning who is getting absorbed like todays up lot of sellers during this up move maybe
> getting absorbed or there stoplosses getting . a live right on chart decoding everything live ."

**27 Oct, after seeing the mockup (this brief exists because of this message):**

> "Close, but still its not look professional or a finished i have more real and as the setup armed it needs
> check what happened before in data everything means oi cvd vpin writing pressure plus cross index price
> action or their oi etc if they are also pointing in the same direction etc that gives any piece of info .
> and when the setup fired lets it should figure or mark the target, stop loss, and it can be anything, like
> maybe previous day low, close, previous month high, close, weekly high. It can be any important level that
> we have here. It can be LVN, HVN from previous day, or it can be OI floor, you know, any kind of piece of
> data that we have. So once the setup fired and it's triggered, it should now live on every candle. It should
> check everything and kind of, you know, give us if it is a trend is moving, or it is getting a strength, if
> there is any pullback with no, you know, changes, so that we can still hold the trade, or as a trader, think
> about it. It's a real-time tool. So when you set up fired, it kind of like you are in a trade. Now every
> candle is like telling you something in the other, okay? In like every data point that we have, that it
> should calculate real time. You know, it's like a real live tool that detects everything. Okay, what is the
> CVD? What's the pressure there? What's the OI is doing? Okay, and it can, and it should be able to
> anticipate, you know, which are low volume nodes where price can go, you know, once it break through any
> levels thats buyers or sellers are holding, after it can give a good move, and the targets that we can look
> for, the liquidity levels even below, or the liquidity levels that above that we can target. who is running
> or where they can run big spike come if flow is getting heavier or delta is increasing or stack imbalance
> are forming on the moving side So it has to be a real-time tool, you understand? Okay, let's brainstorm
> this. ... i like real quant tool or live ai tool which has eye on anything and everything and detect even
> slightest hints and easily identify and figure out noise from real data and make sense of everything .
> maybe i am not able to put in words but ask him go insane completely . its a dream tool for me ."

**Earlier, still standing:**
- 26 Oct, on the alert text: "too much to read and make sense ... it should be look like a tool not a answer
  it spit in fives lines". A zone CARD was then rejected ("no i dont like it"). **The read lives ON the chart.**
- 6 Oct: screens read like a terminal (grids, numbers, state pills, cells of six words or fewer), never
  paragraphs.
- 29 Sep: she cannot remember glyphs. Every symbol carries a short Hinglish chip with its number
  ("ROKA 640", "SL KATE", "PE likh rahe +38k").
- She HATES dark mode. Light theme only, everywhere.

## 3. What she called "close", and what it lacked

`docs/mockups/live-chart-2026-10-27/live-chart.html` (open `?d=2026-10-21&t=13:15`). It is a canvas replay of
four real days, built from `live_chart_build.py` and `move_facts.py`, both beside it. It has:
- a leg coloured by who is winning;
- pins for ROKA (wall held), THAKAN (exhaustion), PHANSE (trapped), ABSORB, SL KATE, ZOR (big print) and
  PALTA (flip);
- trapped boxes that burn;
- a pullback box;
- the zone entry, stop and opposite band;
- a Δ / CVD / OI strip.

What it lacked, in her words and mine:
1. **"not professional or finished".** It looks like a demo, not a desk tool.
2. **No pre-arm context.** When the setup arms, nothing checks what came before: OI, CVD, VPIN, writing
   pressure, and the other two indices' price and OI.
3. **Target and stop are not chosen from real levels.** It used only the opposite band and the zone stop.
4. **No in-trade voice per candle.** It never says "trend moving / strengthening / pullback with no change,
   still hold / something changed, think".
5. **No anticipation.** It does not show the LVN corridor past a held level, the liquidity above and below,
   who is running and where they can run, or spike risk as flow gets heavier, delta grows or stacked
   imbalances form on the moving side.
6. **No noise filter.** Every pin looks equally important. She wants the tool to know a whisper from a shout.

Use it as evidence of direction, not as a template. You may throw all of it away.

## 4. The five jobs (her structure)

| Job | When | What it must do |
|---|---|---|
| **A. ARM CHECK** | the setup arms (her zone touch; also RIDE pullback, FADE-D) | Look back over the data and say which pieces agree with the side and which fight it: OI on her strikes (writers per side), CVD trajectory, VPIN, writing pressure, cross-index price action, cross-index OI, basis, day type. As a COUNT (n of N), each piece named. |
| **B. FIRE** | entry | Choose and MARK the stop and the targets from the full level set (§5.3). Say WHY each was chosen: "PDL 24,612s · 18 pts beyond = SL pool". |
| **C. IN TRADE** | every candle (and finer, if you can make it real) | Re-read everything. Is the trend moving, strengthening, or fading? Is a pullback a pullback "with no changes" (hold) or a real change (think)? CVD, pressure, OI, who is winning, who is absorbed, whose stops are being hit. |
| **D. ANTICIPATE** | always | Where price CAN go: LVN corridors past the level buyers or sellers are holding, the liquidity pools above and below, who is running, where they run to, spike risk building. |
| **E. NOISE vs REAL** | always | Eye on everything, catch the slightest hint, and grade it: noise, whisper, real, loud. Define the grading against the day's own baseline, not a fixed number. |

She also said "let's brainstorm this". So the design doc is a real brainstorm: every possibility you can find
(order-flow microstructure, OI composition, options-side reads, volatility, cross-index lead and lag, basis,
book depth, sweeps and runs, effort versus result, regime and day type, and anything else in the data), each
graded by how real it is with today's data.

## 5. What the tool already records and computes (read the module docstrings; they are good)

**5.1 Recorded data (READ ONLY, never write here):** `tapemap/data/`
- `tape/tape_NIFTY_<day>.jsonl`: 5-min NIFTY futures footprint bars
  `{t epoch ms, o,h,l,c, buy, sell, delta, vol, ladder}`, where ladder is per price. It can contain
  duplicate bars; dedupe by `t`. There are 24 days from 2026-09-11 to 2026-10-26.
- `tape/ofd_marks2_NIFTY_<day>.jsonl`: the extension's chart marks (big prints, absorptions, rank).
- `tape/ux_<IDX>_<day>.jsonl`: Upstox book-derived flow per index (NIFTY, BANKNIFTY, SENSEX).
- `reader/reader_<IDX>_<day>.jsonl`: the 1-minute leg engine's rows and events per index (reader.py).
- `chain/chain_<IDX>_<day>.jsonl`: the option chain per snapshot (OI per strike per side, spot, LTP, IV).
  Spot per snapshot is here. NIFTY has 25 days.
- `xindex/xindex_<day>.jsonl`: the cross-index read every 3 minutes (xindex.py).
- `sides/`, `warmap/`, `decode/`, `messages/`, `trap/`, `hold/`, `fold/`: per-day outputs of those
  modules.
- `vpin_log.jsonl`, `vpin_backfill.jsonl`, `vpin_fast.jsonl`: VPIN on NIFTY futures, per volume bucket.
- `confluence/` and `confluence_log.session(idx, day)`: 3-min futures bars with OI. `backtest/` holds 199
  cached sessions (NIFTY, `BANKNIFTY/`, `SENSEX/`): use them for previous-month high/low/close and weekly
  levels, which levels.py does not carry for months.

**5.2 Modules that already compute a read** (`tapemap/*.py`; each docstring states what it answers):
- **Levels and terrain.** `levels.py` (PDH/PDL/PDC, PWH/PWL, OPEN, ROUND, MAX_PAIN, GAMMA_FLIP,
  CE_WALL/PE_WALL, each tagged index or chain frame) · `prints.py` (POC/VAH/VAL, HVN/LVN, imbalances, stacked
  imbalances, unfinished auctions; a port of the extension's math) · `pools.py` (where size rests and where
  nothing does) · `hunt.py` (which runway pays more: the fuel per direction).
- **Order flow.** `absorption.py` · `sweep.py` · `runs.py` (three big same-side fills) · `effort.py`
  (lots per point at a fresh extreme: the one order-flow read that survived holdouts) · `impact.py`
  (lots per tick) · `vpin.py` · `ladder.py` (the per-price ladder from book snapshots) · `reader.py`
  (1-minute legs).
- **OI.** `fronts.py` (her near-ATM fronts rule, §1d) · `sides.py` (OI per side on her nine strikes against
  the move) · `trapped_inventory.py` · `chainside.py` · `dwell.py` · `oi_dwell.py` · `warmap.py` ·
  `trap.py` (level → dwell → induce → failure → release → travel).
- **State and read.** `daytype.py` · `onesided.py` · `regime.py` · `direction.py` · `read.py` (OI-first
  held read) · `decode.py` (the trajectory of every input and then ONE combined call: start here, it is the
  closest thing to the brain she wants) · `grounds.py` · `xindex.py` · `sensex_flow.py` ·
  `trendbox.py` (1m to D trend rows) · `breadth.py`.
- **Her setups and her hold.** `band_rotation.py` + `contract_bars.py` (the zone) · `ride.py` · `hold2.py`
  (push trail, profit lock) · `fold.py` · `plan.py` (STOP · NEXT RUNG · ROOM) · `confluence.py`.

**5.3 Her method: read it before designing**, because she must never be asked what is already written:
- `tapemap/context/research-findings.md`: §1b THE ZONE, §1d the fade gate and fronts, §1i confluence, §1j
  RIDE, §1l READ-2 + JAGAH, §1m HOLD v2, §1n FADE-D, §1o one-sided meter, §1q SENSEX = NIFTY flow, §1r
  ZONE-3M, §2 the dead ideas (do NOT revive them).
- `tapemap/docs/board/FABLE-TRAP-FRAMEWORK-2026-10-04.md` (your own earlier work) and
  `FABLE-CRITIQUE-real-vs-fake-2026-10-04.md`.
- `tapemap/docs/reader/FABLE-DECODER-DESIGN-2026-10-04.md`, `7-final-design.md`, `9-cross-index-design.md`.
- `tapemap/docs/live/NOTEPAD.md`: the live gap log, especially A100–A119 (A117/A118 are this thread; A119 is
  the roll-week OI problem).
- Her liquidity thesis, in one paragraph: dealers walk price to a retail reaction point, let positions load
  there, then run the stops beyond it; stops are liquidity. OI must be read AT levels, not in aggregate. The
  move runs to the next reaction point.

## 6. Deliverables (all inside `tapemap/docs/dream-tool/`)

1. **`DESIGN.md`**: the brainstorm and the design.
   - Every read you can imagine, each with what it detects, the data it uses (file and module), whether that
     is measurable today [M] or an inference [I], and how it separates noise from real.
   - The five jobs (§4) specified.
   - What the screen looks like and why: what is on the chart, what sits beside it, what flashes, what stays
     quiet, and what the trader sees in the first second, in the first five seconds, and on a hover.
   - The gaps: what needs new recording, such as next-month futures in roll week (A119), monthly levels, or
     anything you discover.
2. **A working mockup**: `mockup/dream.html`, plus its builder script(s) beside it.
   - It REPLAYS real recorded days candle by candle (and finer if you can make the in-candle build-up real),
     from the files above. Nothing is invented.
   - Days: 2026-10-21 (trend down, where the zone bought into a red leg 5 times and was stopped 5 times),
     2026-10-22 (chop, 10 leg flips), 2026-10-23 (rip on fresh longs, no zone entry), 2026-10-26 (the
     bottom BUY that held).
   - Add at least ONE day outside the roll week (for example 2026-10-08, the trend-down day test, or
     2026-10-01), so OI reads are seen clean.
   - Quality bar: it must look like a professional terminal a prop desk would pay for (Bookmap, Sierra Chart
     and Quantower calibre of finish), in LIGHT theme. Professional means: a typographic system, one colour
     grammar, motion with meaning, nothing overlapping, nothing illegible, and a calm state when nothing is
     happening.
3. **Screenshots** (`mockup/*.png`) of each day at its key moments: arm, fire, a pullback held, a real change,
   and the exit. Headless Edge works for full-size shots:
   `"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --window-size=1440,900 --virtual-time-budget=6000 --screenshot=<out.png> "file:///<path>/dream.html?d=...&t=..."`
4. **`REPORT.md`**: what you built, what each day shows at its key moments (time, price, what the tool said,
   and whether that was right in hindsight; describe it, never score it as a rate), what you could not make
   real and why, and your honest ranking of the ideas by how much they would help HER trade.

## 7. House rules (hard; breaking one undoes the work)

- **No order path, ever.** Display and advisory only: no buttons that trade, no broker calls.
- **Never write under `tapemap/data/`.** Read only. Write only inside `tapemap/docs/dream-tool/` (and your
  scratch temp if you need it).
- **Never open, print, read or log anything in `tapemap/telegr/`** (her bot token lives there).
- **Never start, stop or restart her TapeMap server (port 8765) or Vite (5173).** Do not edit `server.py`,
  `decode.py` or any other production `.py`/`.ts`/`.js` file. This is a design and mockup job; import
  modules read-only if useful.
- **No hit rate, win rate or % confidence anywhere on screen.** Agreement is a COUNT ("3/5 saath"). Every
  [I] inference is labelled as such in the design doc.
- **Every price level says spot (s) or futures (f).** She confuses the two. The basis drifts 13–74 pts
  within a day, so use each bar's own basis from the chain (spot per snapshot) and never one constant.
- **Light theme only.**
- **Hinglish chips** on every symbol, with its number. Keep any engine sentence verbatim.
- **Tool, not essay.** On screen: numbers, pills, glyphs, cells of six words or fewer. Prose belongs only in
  DESIGN.md and REPORT.md.
- **Her registered rules** (§1b, §1d, §1i–§1r in research-findings) are never changed. If your design needs
  one changed, write it as a PROPOSED new registration in DESIGN.md, clearly marked, for her to sign.
- **Roll week (21–26 Oct):** only the October futures contract is recorded, so futures OI carries the roll.
  Mark those reads as raw ("kachche") and design the real fix.
- **No look-ahead.** At any replayed moment the tool may use only data at or before that moment. Your earlier
  OI-Edge work caught a look-ahead in mine; hold yourself to the same.
- **Never design off one day.** Every rule must survive all the replayed days, and the report must show where
  a rule fails.
