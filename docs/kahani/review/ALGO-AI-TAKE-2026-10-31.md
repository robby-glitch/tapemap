# AI-Plus-Algo-Trading (`algo_ai`): what to take into TapeMap / Jarvis (31 Oct 2026)

Her ask: "before you make this i want you check one my project once go through this once and what we can take from here
to include in our tool."

Read in full, read-only: `C:\Users\kaam\Downloads\AI-Plus-Algo-Trading\algo_ai\` (9 Python files, 6,288 lines incl. the
dashboard; `token.json` not opened). Judged against her method (writers first, both ways, OI at levels, no %, no order
path) and against what TapeMap already has.

---

## 1. What it is

A buyer-only, one-shot morning engine for NIFTY weekly options on Zerodha Kite, with a Flask + Socket.IO dashboard.
One Execute = one analysis pass (OI walls and PCR on ATM ±5, VWAP from the future, a 15-min opening-range breakout,
gap vs average range, India VIX expected move blended with the recent open-to-close range, momentum used, CPR width,
yesterday-vs-today OI at the walls, live ATM premiums) → seven ±5-point nudges into one upside probability → one AI
sentiment call (Gemini or Claude, with web search, fixed prompt, JSON only) → CALL / PUT / BOTH / NO_TRADE → enter →
a dumb safety loop (₹ stop / target / time exit / 15:15 force exit, settings re-read every second, broker positions
reconciled on restart). `dry_run` defaults on and is not a UI toggle. Two pure-function test files.

Well engineered for what it is. Its market reads are retail aggregate reads that TapeMap's method has either superseded
(one daily OI ratio at two walls, against §1d fronts per minute, ±7 writer flow and Sides) or killed (ORB, gap plays).
Its AI is a once-a-day news nudge; Jarvis's would be a live narrator of a measured frame. What transfers is the
discipline and three missing inputs, not the signals.

---

## 2. Take (ranked by what helps her)

| # | From `algo_ai` | What TapeMap lacks today [M] | How it lands in our tool | Size |
|---|---|---|---|---|
| **T1** | `engine.reconcile_open_positions` / `resume_existing_position`: on every login or restart the open option position is rebuilt from the broker's own `positions()` (real entry price, qty, symbol), never from memory | **Nothing reads her live positions** (grep: zero hits in `upstox_*`, `server.py`, `receipts.py`). Her trade marking stopped after 6 Oct (A22); A52 says "unmarked-position nudge NOT built". So the ONE VOICE, the TRADE MAP, Validate's in-trade face and Jarvis's MANAGE all go blind the day she forgets to mark | **CORRECTED 31 Oct (her: "i trade in multiple brokers i use upstox for data stream for our tape map")**: a GET of Upstox positions would miss every trade placed elsewhere, so the broker read is NOT the fix (my error: I assumed the data broker was the trading broker). Broker-neutral marking instead: **(a)** one `/mark` command in one grammar on every face she already has: Telegram (`telegram_in`, today only `/now` `/last`), the terminal and the Jarvis command box, e.g. `/mark NIFTY 23000 PE buy 325` and `/flat` → `trade_record`, entry = her number, tagged `src: mark`; her mark on the Float still wins. **(b)** later, if she wants it: read-only positions from each broker she names, merged and tagged `src: <broker>`; each is its own daily token, so (a) first. No order path either way | small (a) / medium (b) |
| **T2** | `get_india_vix`: one quote of INDIA VIX per run, fed as context | **India VIX is read nowhere** (only named in `jarvis.NOT_READ`; GAPS §3 G lists it as "—") | One Upstox quote per minute → a location-line item: `VIX 13.4 · +0.6 since open`; tagged like every level. A rate, not a level: its change since open is the read | small |
| **T3** | `get_atm_premiums` + `required_move_* = live ATM premium × profit_margin_factor`, compared with the day's expected move before any BUY | The buyer's expression line says "buy the CE on the pullback" with no idea what that CE must travel today. `trademap.em` already has the day's 1σ her way (09:20 straddle ÷ 0.8 ÷ √N) and l4 has range used | On Jarvis's buyer line and Validate: `this CE needs +62 pts to break even today [I ×1.15] · EM left ≈ 40 pts` → the buyer's "is it worth paying for" check, both ways (the seller's side already has the PREMIUM PATH, A57). Counts and points, no probability | small |
| **T4** | `ai_sentiment.py`: ONE fixed prompt, JSON-only output constrained to three words, a safe default on any failure, a provider seam (Gemini / Claude behind one function), the prompt shown read-only on the dashboard, an optional trader's note appended as one more factor, a 429 on search grounding → retry the same call without search | Confirms the fence I proposed for the Jarvis voice (JARVIS-REVIEW §5 P2 #11): numbers only from the card, never the verdict, falls back to engine sentences. Adds three things we did not have: **show the prompt on the panel**, **her daily note** ("RBI 11:00 today"), and the only place web search earns its cost: **a once-a-day pre-open brief** (events today: RBI / Fed / expiry / big earnings; global cues) as Jarvis's first line of the day. Everything else in Jarvis reads the frame, never the web | small (inside P2) |
| **T5** | `_read_live_exit_settings`: the safety fields are re-read from `settings.json` every tick, so a change takes effect without a restart; `restart_status`: a red banner when any `.py` changed after the process started | "Live at her restart" is in dozens of NOTEPAD rows; a restart in market hours is forbidden. A179 ("did you change anything?") cost an evening | (a) Jarvis's and legs' [I] thresholds in one `jarvis_thresholds.json`, re-read per build: tune display thresholds without a restart, every change still a NOTEPAD line. (b) `/api/health` gains `code_changed_since_start: n files` and the panel shows it | small |
| **T6** | `compute_volatility_confidence`: a separate "HOW MUCH" gauge beside the "WHICH WAY" probability (expected move vs recent range, breakout, move used, fresh OI magnitude, CPR width) | Jarvis has a lean and no magnitude line. The pieces exist and are unread by Jarvis: `onesided` day type, trademap l4 range used, VIX (T2), CPR width = one formula on `levels.py`'s PDH / PDL / PDC | A MAGNITUDE line in the call: `day CHOP · range used 0.7 of EM · VIX +0.6 · CPR narrow` as named rows, judged forward. **Never their 0-100 score or summed weights** (rule 4; their README says it is "not backtested") | small (inside P0 #4) |
| **T7** | `run_headless.py`: the same engine with a console face and a `stop` listener | The terminal Jarvis (P2 #10) is exactly this shape | Nothing to copy, a confirmation the shape is right | — |

The atlas already measured T6's core: her late losers had range used ≥ 0.98 (A59) and legs ≥ 120 pts at the call
(A192); `algo_ai`'s "momentum above 65 % used is EXCLUDED, not extra evidence" is the same don't-chase rule, stated as a
fraction.

---

## 3. Not to take, and why

| Piece | Why not |
|---|---|
| Opening-range breakout (15 min) as a vote and a bonus | dead: research-findings §2 "classic 15-min ORB" |
| Large gap → buy BOTH legs | gaps have no edge (§2); buying a straddle on a rich-IV open is the opposite of how she trades (she sells rich premium) |
| PCR level, proximity-weighted PCR, OI-wall ratio → probability | her method reads OI at LEVELS per minute (fronts, ±7, Sides, the handshake); PCR counts only as a CHANGE (GAPS §3 F) |
| yesterday-close vs today OI ratio at two walls | `fronts.py` already has BUILDING / STALLED / UNWINDING per minute with peaks and slopes |
| the ±5-point nudge sum, `upside_probability`, the 0-100 Volatility Confidence | rule 4: no probability, no confidence score; and a sum of equal hand weights is a vote, not a read |
| the AI as a news-sentiment nudge into the direction | the direction must come from the frame; the model is the voice (§16.3). A news read belongs in the pre-open brief, labelled as context |
| ₹ stop / target / time-exit loop, manual Buy buttons, square-off | no order path, ever |
| Kite login, ticker, proxy | Upstox project |

---

## 4. Build order (hers)

T1(a) first: the `/mark` command changes what she sees in a trade every day, works on any broker, and every in-trade
module already built waits on it. T2 and T3 ride P0 #4 (wire the reads). T4's pre-open brief and T5 ride P2 / P1. Nothing here changes a
registered rule; T3's ×1.15 is [I] and says so.
