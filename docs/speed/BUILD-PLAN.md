# RAFTAAR: what to build, and in what order (28 Oct 2026, 02:00)

One sentence: RAFTAAR is the live reader of **who is pushing, who answers, and where the fuel is**. It gives ONE graded picture,
updated every minute, on her screen and her chart, and on Telegram only when it matters.

Everything below was proven on the recorded days (rows, not rates) and is judged forward. Nothing touches §1d, §1o, THE READ
or the zone machine. RAFTAAR stands beside them, and may disagree only with its numbers shown.

## The brain: one place (TapeMap server), six small pure modules, each causal and each with one test file

| Module | What it does | Built on (proven where) |
|---|---|---|
| **flow1m** | ONE 1-minute futures flow line. Dext when alive (one row per minute: keep the fullest; near month only), else the Upstox 1-second book by the quote rule. Sources counted per minute: Dext + book now, GoCharting when its 5-min bar closes. | Fable CRITIQUE M1, M2, M5; A129 (real time) |
| **handshake** | PUSH (2-min delta ≥ 2× normal into a strike). ANSWER the first minute OI at that strike crosses its bar, within 4 min: toot / phans / tiki / no answer. WHO OPENED (premium vs delta). FLOOR / CAP behind price, only when writers opened it. Fut-OI leg, effort. | BRAINSTORM handshake; Fable M3, M4, M6, M7 |
| **raftaar** (the engine) | The picture: CHAL RAHA ▲▼ / WAPSI / CHOP / PIN / ATKA / UNWIND / KHAMOSH / ?. Grade n/N, the story line, writers by zone (roll up / down), stamps only on change. **Two new gates:** (a) no "≠ READ" and no "chop se bahar" without an answered push in the last 10 min; (b) no CHAL RAHA MAZBOOT continuation while PALAT steps 2–4 are lit. | docs/speed/final/raftaar.py; Fable's gating answer; A129 |
| **palat** | TOP / BOTTOM, counted 0–5: at a fresh extreme or her band; the last push answered by heavy covering with fut OI flat; the other side's writers at the extreme strike; the next same-side push gets no answer; the first opposite push gets one. Plus the P-mark alert, 3 of 4 (tonight). | A129, A130 (27 Oct top 12:45, bottom 14:16) |
| **shikaar** | AGLA SHIKAAR once a move is set: the strikes ahead whose writers would be trapped next (OI, how far under water, distance s / f), the next wall, day high / low, PDH / PDL, her next band. | her liquidity-hunt thesis; A129 |
| **coil** | COIL: the range squeezed under its normal, both sides writing near ATM, straddle and IV falling. Lean = the heavier near-ATM writer: "agar toota to fuel ▲ 120L at 22,750s". Never "it will break". | BRAINSTORM (29 Sep 10:21, 27 Oct 10:03) |

**One endpoint:** `GET /api/raftaar?idx=` returns one JSON, computed once a minute in the server (one voice):
- the picture and its grade;
- the story line;
- the handshake chain now;
- PALAT n/5;
- the SHIKAAR list;
- COIL;
- the sources n/3;
- the stamps;
- the contradiction line.

**Restart-safe:** at start it replays the day's record in step, so a 11:12 restart reads exactly like a run that never stopped
(the anytime-start rule).

## The faces: render only, no logic

1. **Speed tab (ui-v2)**, replacing the rejected one.
   - **Layout:** Opus v3 (hero: picture + SAHMATI + FUEL + OI trend · left: price × time + the §1d fronts · right: the fuel
     ladder).
   - **Added:** the handshake chain card (the 6 steps) and the three-source box.
2. **GoCharting chart layer (the extension overlay):**
   - the state ribbon under the bars;
   - ◆ push → ✓ / ✗ answer;
   - the TOP / BOTTOM BAN SAKTA chip with n/4 (or n/5);
   - walls and floors on the existing deewar lines;
   - all inside the line budget (2 flat, 5 in a trade).
3. **Telegram:**
   - ZONE with the day type (tonight);
   - TOP / BOTTOM BAN SAKTA at 3 of 4 (tonight);
   - later, opt-in: a RAFTAAR picture change only when it is MAZBOOT AND answered;
   - a budget of ≤ 6 lines per index per day, so the phone stays meaningful.

## The order: each phase ends with her restart and a live day, and logs forward rows (data/raftaar/) for the evening review

| Phase | When | What she gets live | Risk |
|---|---|---|---|
| **0** | tonight, loads at her morning restart | ZONE alerts carry "din CHOP / PIN: palat ki ummeed" or "din TREND: price discovery, fade khatra"; TOP / BOTTOM BAN SAKTA at 3 of 4 on Telegram | notification only |
| **1** | 28 Oct after close | flow1m + handshake + the engine as server modules, /api/raftaar, restart-safe replay, tests, replay on every recorded day; a plain debug view only | server code; her restart |
| **2** | the next evening | the Speed tab face on /api/raftaar (v3 + handshake chain + sources); the old tab removed | UI only (Vite reloads, no server restart) |
| **3** | after 2 | palat 0–5 and the two engine gates inside the engine; shikaar; coil | changes the engine's words: checked on all days first |
| **4** | after 3 | the GoCharting overlay layer | extension build + reload |

## What I decided as the trader (her standing rule), and why

- **Real time over confirmation.** An answer shows the minute it crosses its bar (1–4 min). Sources agree per minute on Dext
  plus the book; GoCharting's 5-min bar is a slower confirmation, never a wait.
- **A push with no OI answer blocks a breakout line.** It is a required check, not enough on its own: both right ≠ lines had
  one, 4 of the 7 wrong ones did not.
- **A floor is a floor only when writers opened it.** Put buyers opening OI under price is a bet, not support.
- **The P label alone is a coin.** It is an alert only with 3 of 4 confirmations: the 27 Oct 12:45 top had all four, and the
  losing "tops / bottoms" on trend days had none of them behind it.
- **Grades stay counts** (SAHMATI = checks agreeing), never odds, until forward days earn more.

## Owed / open

- **Nothing from 27 Oct is committed**, and none of this phase either. That includes A125 rebase, A126, the first Speed tab,
  docs/speed, and docs/dream-tool. Commit on her word.
- **27 Oct's stale NIFTY FIRST FOLD (A127)** lives in the 27 Oct day-state file. It is moot for today, unless she wants that
  file corrected for replays.
- **Dext:** it posts the same minute up to 4×, and it went blank on the 27 Oct afternoon. The book fallback covers it, but the
  extension is worth a look (A124).
