# Option order flow: the Dext bridge and the Option Battlefield

Built 3 Nov 2026, in one session, on Mary's word at each step. Committed on `feature/operator-objects` (not pushed).
Code: `optflow/`. Wiring: `start-v2.bat`, `stop.bat`. Backlog row: NOTEPAD **A215**.

## In one paragraph

TapeMap reads every strike's **OI** from the Upstox chain, but OI only says that positions opened or closed. It cannot
say **who**. The option strike's own **order flow** can: buyers lifting or sellers hitting, at each price, every minute.
Put the two together and each strike says *writers opening, writers covering, buyers opening* or *longs exiting*. That is
the read her playbook needs (writers' walls, trapped inventory, stops as liquidity), and the futures tape cannot give it.
The Dext **desktop** app already loads this footprint from Dhan. `optflow/dext_bridge.mjs` asks it, once a minute, for
NIFTY and SENSEX **ATM ±5, CE and PE**, and hands it to TapeMap. `optflow/optflow.py` draws it as one picture, the
**Option Battlefield** at http://127.0.0.1:8790/.

## Why we built it

Mary, 3 Nov 2026: *"we have order flow of options as well and they also [work] quite well … do you think we should
make an orderflow reader for option order flow as well, at least ±3 to 5 strike"*.

- **The trader's reason.** In India the money is on the writing side (see memory "India options market structure",
  `operator-thesis`). Futures flow shows the push. Option-strike flow at the strike, read with OI at that strike, shows who
  is behind it: a writer building a wall, a writer running, a buyer getting trapped.
- **The gap it closes.** Fable's clean-room OI audit said it in October: OI snapshots *give OI no side*; option aggressor
  flow was "not measurable" from what TapeMap recorded (`oi-lab/AUDIT_OI.md` F9, `oi-lab/flow/AUDIT.md`).
- **What it is NOT.**
  - Not a timing signal: the 9-day check below showed option flow alone does not time the next 5 minutes. It is a WHO read.
  - Not an order path: it reads, it never trades.
  - Not a rule: nothing here is registered in `context/research-findings.md`. The SENSEX option flow is collected, but
    reading it in place of NIFTY's flow would change §1q, which only Mary signs.

## Daily use

1. Double-click **`start-v2.bat`**, as every morning. It now also starts:
   - **Dext** with the order-flow port (9229). Dext must be opened by the launcher: a Dext already open without the port
     cannot gain it, and the launcher says so.
   - **The Dext bridge** (minimised window "Dext bridge"), which keeps a lock on port 9230 so it can't start twice.
   - **The Option Battlefield** (minimised window "Option Battlefield") on 8790.
2. Keep **one chart open in Dext**, any chart. The bridge borrows that chart's login.
3. Open http://127.0.0.1:8790/. Use the **NIFTY · SENSEX** switch at the top, or open `/?idx=SENSEX` directly.

`stop.bat` stops the bridge and the board as well. Dext stays open, because it is her app.

## How to read the Battlefield

- **Rows** are strikes, highest at the top. **Left to right** is the session, 09:15 to 15:30.
- Each row has two lanes: **calls on top, puts below**. One block is 5 minutes.
- **Red block** = call writers adding at that strike (a cap, *likh rahe*). **Green block** = put writers adding (a floor).
  Darker = more OI.
- **Hollow outline** = those writers leaving (*cover · bhaag rahe*). That is how a wall breaks.
- **Grey** = the order flow says it was **not writers**, but option buyers in or out. This is the 3 Nov 11:55 trap:
  OI fell, but sellers were hitting, so it was longs exiting, not writers covering.
- **Faded** = OI only: no Dext footprint for that strike.
- **Dots** = the biggest single-price hit of the 5 minutes. Red = bearish (a call sold, or a put bought), green = bullish.
  Bigger dot = more quantity. The floor is NIFTY 5L / SENSEX 0.2L qty, and the size is written from 10L / 0.5L.
- **Black line** = the index spot.
- **Pills on top:**
  - **CAP**: the strike above spot with the most call OI, and whether its writers are building, holding, or leaving.
  - **FLOOR**: the same for puts below spot.
  - **LEAN**: UP when the cap's writers leave, DOWN when the floor's leave, RANGE when both hold.
- **Futures box:** NIFTY futures delta on both pages, by §1q.
- **● Live** reloads every 30 s. **Replay day** animates from 09:15, and the slider jumps to any minute. Everything at a
  minute uses only data up to that minute.
- Thresholds scale to the day's own size (the 90th percentile of 5-min moves), because SENSEX trades about 1/65 of NIFTY's
  option volume.

## How it works (for whoever maintains it)

```
Dext desktop (Electron, C:\Program Files\Dext, backgroundThrottling: false)
  └─ started with --remote-debugging-port=9229 --remote-debugging-address=127.0.0.1   (start-v2.bat)
       └─ chart frame https://dext-charts.dhan.co/  ──POST──▶ https://ticks.dhan.co/orderflow/getOrderFlow/v2
optflow/dext_bridge.mjs (Node 22, no dependencies, lock 127.0.0.1:9230)
  1 LISTEN  every getOrderFlow/v2 and getData response Dext loads on its own is forwarded
  2 ASK     once a minute, inside that chart frame, the same request for each target contract
  └─ POST http://127.0.0.1:8765/api/dext/candles   (TapeMap's existing Dext door, dext_log.py)
       └─ data/dext/dext_<EXCH>-<SEC_ID>_<day>.jsonl   (one 1-min footprint candle per line)
optflow/optflow.py (8790) + optflow/map.html
  └─ reads data/dext + data/chain/chain_<IDX>_<day>.jsonl + data/scrip_master.csv on every page load; writes nothing
```

- **The request.**
  - Body: `{"EXCH":"NSE"|"BSE","SEG":"D","SEC_ID":<id>,"START":<epoch s>,"END":<epoch s>,"START_TIME":"…Z","END_TIME":"…Z"}`.
  - Headers: Dext's own (`Auth`, `Accept`, `Content-Type`), copied from the app's own request. The bridge never stores or
    prints them.
  - Response: `{"success":true,"data":{"candles":[{"time","price":[…],"buy_vol":[…],"sell_vol":[…]}]}}`, i.e. the
    footprint. Converted by the Chrome extension's own parser, `orderFlowV2` in
    `C:\Users\kaam\Desktop\dext extension\dext-decoder\dext-decoder\lib\parsers.js` (the `PARSERS` constant), so TapeMap
    holds one shape whatever the source.
- **Any contract, no chart needed.** The endpoint answers for any NIFTY (NSE) or SENSEX (BSE) option id, open in Dext or
  not. Verified 3 Nov after the close: NIFTY 03 NOV 23550 CE and SENSEX 05 NOV 76600 CE gave 385 one-minute bars each.
  Dext's live updates come over a binary websocket that the bridge does not decode, and does not need to.
- **What it asks, from 09:15 to 15:45:**
  - the ATM strike, read from the tail of today's chain file (NIFTY in 50-point steps, SENSEX in 100);
  - ATM ±3, CE and PE, every minute; ATM ±4..5 every 3rd minute; plus any chart open in Dext;
  - about 33 requests a minute on her Dhan session;
  - a contract's first ask of the day fetches from 09:15, and later asks fetch the last 15 minutes.
- **Only closed minutes are sent.** TapeMap's door appends only lines that changed, so repeated sends cost nothing.
- **The board.** For each strike and 5-minute block it computes:
  - the OI change from the chain;
  - the order-flow delta and the biggest price cell from Dext;
  - the cell kind: OI up with sellers = writers; OI up with buyers = buyers (grey); OI down with buyers = writers covering;
    OI down with sellers = longs exiting (grey).
- **Checks:**
  - `python -I optflow\optflow.py --check [YYYY-MM-DD]` builds both indices and asserts each has chain data and Dext
    order flow;
  - `node optflow\dext_bridge.mjs --now` runs one full round at any hour, which is the after-close check.

### Its log lines
- `asked 44/44 (NIFTY 22, SENSEX 22) · N closed candles · M own Dext loads · S s`: a healthy round.
- `waiting for Dext to load a chart - change one chart's timeframe in Dext once`: the bridge has not seen Dext's login yet.
  Dext loads charts by itself in market hours; in the evening one timeframe change does it.
- `another dext bridge is already running - this copy stops`: the start script was run twice. That is harmless now.

## Traps already paid for (3 Nov), do not rediscover

1. **Chrome tabs stall.** The Dext Chrome extension in a 6-chart grid stopped sending every 5–60 minutes. Only one chart in a
   grid kept sending, background tabs were throttled, and an auto-refresh only hid it. The **desktop app does not
   throttle**, which is why the bridge uses it.
2. **`credentials: "include"` gives "Failed to fetch".** The app's own fetch sends no credentials mode. Copy that.
3. **A test copied from Dext's after-close poll** asks for the last few minutes and gets `candles: []` for every contract.
   It looks exactly like "Dhan refuses this contract". Always send an explicit 09:15 → now window.
4. **CDP sessions die when a frame reloads** ("Session with given id not found"). The bridge drops that session and
   re-learns from Dext's next request.
5. **A chart frame cannot be reloaded over CDP** (`Page.reload`: "only top-level targets"). That fallback was built and
   removed.
6. **A new frame's first request was missed.** Fixed by attaching with `waitForDebuggerOnStart` and then
   `Runtime.runIfWaitingForDebugger`.
7. **Three bridges at once.** The start script was double-clicked; the old copies treated each other's requests as "charts
   open in Dext" and re-asked them non-stop. Fixed with the lock port 9230, and by ignoring requests started from
   `Runtime.evaluate` (no script url).
8. **The Chrome extension labels every grid chart with the grid's first chart's name** in `data/dext/instruments.json`
   ("NIFTY NOV FUT" on option files). The data is filed by contract id and is correct; only the label is wrong. Still open.
9. **OI alone mislabels.** OI falling while premium rises looked like call writers covering at 11:55 on 3 Nov. The flow
   showed sellers hitting: longs exiting. The order flow decides.

## The reads behind it (as a trader)

### 2 Nov, replayed (NIFTY 23300 CE / PE, 03 NOV expiry)
- **09:30–10:15:** sellers ran both strikes, and OI rose on both (PE +69L at 09:30). Writers on both sides pinned 23300.
- **12:30:** both strikes flipped in one block: CE sellers −38.8L, PE buyers +33.9L. Futures delta was only −22K. **The
  options moved one block before the futures did.**
- **13:00:** CE sellers −57.9L, the day's biggest. PE buyers lifted while PE OI fell −82.5L, so put writers ran. The put
  went 94 → 159 and spot fell to 23,222.
- **14:30:** the day's biggest CE buying (+50L) with CE OI −65L. A 10.2L seller at 79.2 was run over. 15:15: CE writers
  covering again, and spot closed 23,441.

### The 9-day put check (descriptive, small n, not a rule)
- Saved Dext put footprints: 22800 PE (14–23 Oct), 23300 PE and SENSEX 75000 PE (21 Oct – 2 Nov).
- **NIFTY:** put flow did not link to the next 5 minutes (−0.17 to +0.15 per day) and added nothing beyond futures flow.
  The four OI × flow boxes did not separate either.
- **SENSEX 75000 PE:** +0.18 / +0.21 on its two near-the-money days, and put writing came before +10.8 pts typical
  against +1.6 drift. But the strike was deep ITM on most days and SENSEX rose all week, so it is a hint only.
- **Weakness:** most saved strikes were 450–1,900 points ITM.
- **Conclusion:** a WHO tool, not a timer.

### 3 Nov live (expiry day for the 03 NOV contracts)
- **09:15–09:50:** gap-up open at 23,572. Put writers opened at every strike (23500 PE +258L on the day by 09:47, 23600 PE
  +293L by 09:51). Call writers below spot covered. 23600 CE buyers +140L at the open. Futures +249K in the first 15
  minutes, then about zero.
- **09:48–10:15, the 80 wall on the 23600 CE:** buys of 8.2L @ 80.1, 6.0L @ 79.7, then 5.2 + 4.4 + 4.4L @ 79.9–80.8 were
  all absorbed. Premium kept stopping at 81.7. 23700 CE writers were opening (8.8L sold @ 29.8): the cap.
- **10:25, the break:** 6.3L bought @ 83.35, premium 76 → 90, 23600 CE OI 234 → 201L. Put writers chased price up
  (23600 PE +64L, 23650 PE +64L).
- **10:35, the trap:** the biggest buys came at the very top (100.8, 96.65), then sellers took over (−22.7L). Put buyers
  came in (+28.5L).
- **11:00, the failed break:** the 23600 CE was sold through 80 (6.6L sell @ 74.8; range 92.6 → 71.35). 23650 PE writers
  covered.
- **11:30:** a flush to 23,635 and straight back. The 23600 PE's biggest buys were at its top (6.9L @ 52.2): trapped put
  buyers.
- **11:50–12:10:** a push to 23,702. The 23700 CE was sold (12.0L @ 43.7, 7.2L @ 47.45). **12:10: the day's biggest print,
  23.9L sold @ 22.85.** Put writers who had chased up covered (23600/23650/23700 PE −37 / −41 / −39L), and spot flushed
  50 points.
- **My wrong call, 11:59:** "breaking upward", read from call OI falling and premium rising. The order flow showed sellers.
  Lesson: OI alone cannot tell writers covering from longs exiting.
- **13:18, the real break above 23,700:** the 23700 CE flow from 12:57 to 13:14 was net buyers (+19L). There were 21.2L @
  40.2, 14.4L @ 37.5 and 13.9L @ 42.4 bought; the writers' last defence was 20.9L sold @ 34.15, twice. Its OI went 347 →
  267L (−80L). Put writers piled in at 23700 PE (+71L).
- **13:55–14:19:** a stall under the 23750 cap (+36L). The floor trimmed (23700 PE 414 → 389L) and call writers came back
  to 23700 (+31L). **14:19: the break failed** (spot 23,684, 23700 CE OI 265L).
- **14:44:** spot was back above 23,705, but the 23700 CE OI was **340L and rising**: writers selling into it. It was the
  expiry pin fight around 23,700.

**Lessons:**
- Read the flow first and OI second. A wall is effort without result: big prints at one premium, and price fails there.
- A break needs writers leaving (OI down) **with buyers lifting**.
- Biggest prints at the extreme followed by a flip = trapped traders.
- On expiry day, writers defend round strikes all afternoon.

## Her approvals, word for word (3 Nov 2026)

- **"Yes, once a minute":** the bridge may re-send Dext's own order-flow request for each open chart once a minute.
- **"lets check if we can do that":** the test requests for contracts with no chart open (9 in total).
- **"Build the bridge to follow ATM ±5 on NIFTY and SENSEX by itself":** the auto strikes, about 33 requests a minute.
- **"lets push every to the main session commit and make sure to update docs as well…":** this commit and this document.

## Open

- **The first live session** of the ATM-following bridge, and of the whole start-v2 path (built after the close on 3 Nov).
- **The options engine** (the plan drawn on 3 Nov):
  - an `options_flow.py` WHO / wall / break / trap per strike, with the 2 Nov and 3 Nov moments above as test fixtures;
  - a Jarvis **OPTIONS** line;
  - a strike ladder on the Float;
  - Telegram for BREAK / FAILED BREAK / TRAP only;
  - the evening log.
- **Recording Upstox option ticks** (ATM ±5) as a backup source when Dext is down: a new constant, not
  `SENSES_EACH_SIDE` (settled at 3).
- **SENSEX option flow in the reads** is a §1q change. It is hers to sign.
- **The Chrome extension's grid name label** (trap 8).
- **Scale:** at about 33 requests a minute nothing was throttled on 3 Nov. If Dhan ever throttles, the outer strikes go
  to every 5th minute.

## Files

| file | what |
|---|---|
| `optflow/dext_bridge.mjs` | the bridge: listen + ask, ATM targets, lock 9230, `--now` for one round |
| `optflow/optflow.py` | the Battlefield server on 8790, `--check [day]` |
| `optflow/map.html` | the Battlefield page (light only, canvas) |
| `start-v2.bat`, `stop.bat` | start and stop Dext-with-port, the bridge and the board |
| `dext_log.py` (unchanged) | TapeMap's Dext door, `POST /api/dext/candles`, and the record in `data/dext/` |
| `docs/optflow/replays/*.html` | the two replay pages behind the reads above (2 Nov 23300; 3 Nov to 11:27), open in a browser |
