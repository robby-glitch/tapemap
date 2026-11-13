# EXECUTE THE EDGE: design (13–14 Nov 2026)

Her words: "help me to develop my tool to execute my edge" · "i can hold the trade till the time nothing changes in data because i
know that i can get the best leg of the day" · "in a working leg price reaches opposite side and signal a valid one it would exit
the leg that i m in and take the other side but careful with it" · 14 Nov: **"Build this plan"** (GAP DAY in, CAREFUL FLIP logged only).
Evidence: NOTEPAD A313–A332. Status: **APPROVED design. Not built, nothing live changed, nothing committed.**

## 1. What the tool does

Every NIFTY session, one screen line tells her where she is in HER setup; at a trigger it hands her a ticket with four checks
and one word, TAKE or SKIP. It never places an order (house rule 10). A forward log judges the checks on days not yet seen.

## 2. The rules

| Rule | Value | Origin |
|---|---|---|
| Setup | her zone: arm at the first u2/d2 touch, re-arm at each new extreme, trigger on a close beyond the reference bar, 3-min futures bands | §1r ZONE-3M; `band_rotation.run_states` (OPERATOR stop), as `look_cause_effect.replay` |
| Entry | the trigger bar's close | the zone machine |
| Stop | beyond the extreme made in the band; never tightened, never moved to cost | A321: cost-to-cost worse at every arm |
| Exit | a VALID opposite signal (all four checks ✓): out, and take it · the stop · 15:00 | A319/A320; booking at VWAP negative in every month |
| Hold through | a WEAK opposite signal (any check ✗) neither ends the trade nor is taken | A327 (her marks): +720 → +1,117 on the order-flow days, both halves up |
| One position | a same-side trigger while in a trade is not added | `look_edge_walk` |
| From 15:00 | nothing new; flat at 15:00 | her practice |
| After a stop | look again; the next trigger is a new try | A313 |

## 3. The four checks (in the order they become known)

Each is shown with its number and ✓ / ✗. Any ✗ → the word is **SKIP** and names the reason. A check that cannot be read says
so ("could not check: …"), never counts as ✓ or ✗, and does not block (house rule 6).

| Check | ✗ when | Known | Origin | Record |
|---|---|---|---|---|
| GAP | the 09:15 futures open is outside yesterday's futures high–low (previous weekday with candles, same contract) | 09:15 | Dalton's initiative open; A331 (found in the split, not fixed beforehand) | 60 days +1,262 → +1,650, both halves up, same drawdown |
| TREND | VWAP untouched by any 3-min bar for 120 minutes or more at the trigger (`look_cause_effect.so_far` "vw") | each trigger | A313, held on the 37 unseen sessions (A320) | negative under all five exits on 60 days |
| LEG PAID | a PLAN B trade today already closed at 2× its own stop or more, and this trigger is on the other side | after such a close | hold2.LOCK_R (§1m) | other-side trades after a 2R win: 44, won 16, −182 (A323) |
| FLOW | Dext delta summed from the bar after the extreme to the trigger close is 0 or against the trade | each trigger | A321 (sign only) | its trades won 5 of 26, 18 stopped, −404 |

GAP is "could not check" when the previous weekday has no candles or the futures contract changed since yesterday (the first
session after a monthly expiry). LEG PAID is read before a flip for the hold decision and again after it for the entry.

All four with hold-through (A331): 21 order-flow days 24 trades, won 14, +1,260 (every trigger: 83, won 30, +206). 60 days
without Dext (GAP + TREND + LEG): 119 trades, won 52, +1,650, drawdown 190, without the best five +858, halves +820 / +830.

**Information only, never a vote, shown and logged:**
- LIVE LEG: every earlier opposite signal whose stop is not hit, with its points now (`LIVE LEG  BUY 09:36 alive +72`). As a skip it cost (A328).
- OI, in a trade: the other side's writers near the money (ATM ± 2) since the entry: `OTHER SIDE adding (fuel)` or `cutting (being paid)`. Both mean hold (A332).
- SYNC, in a trade from 30 min after the entry: are BANKNIFTY and SENSEX futures moving her way since the entry? `ALL 3 WITH YOU · hold` / `1 of 2 with you` / `NIFTY alone`. A hold reason, never an exit (A334: both with her on 28 of 53 trades, won 20, +625 more after the 30-minute mark; when neither, cutting at 30 min would have been worse).
- ROOM: the entry's distance from VWAP in her σ (feeds PLAN C).

**Status:** the four checks are candidates until the forward log holds ≥15 SKIPs a side per check and she signs them (house rule 4, §5e).

## 4. The six states (one line each, same words on every face)

| State | When | The line (example) |
|---|---|---|
| WAIT | no arm open, flat | `WAIT · no zone armed` (on a gap day: `GAP DAY · opened above yesterday's high 25,180f · no fades`) |
| ARMED | u2 / d2 touched, no trigger yet | `ARMED SELL · u2 touched 10:03 · extreme 25,261f` |
| TRIGGER | a trigger bar just closed | the ticket below |
| IN TRADE | PLAN B holds a trade | `HOLD SELL 25,250f · wrong only at 25,285f · out on a valid BUY or 15:00 · OTHER SIDE adding (fuel)` |
| OUT | PLAN B was stopped | `STOPPED −35 · look again` |
| DAY END | from 15:00 | `PLAN B +188 (2) · PLAN A +142 (3) · PLAN C +201 (2) · YOU 2 marked` (her marked trades are options: strike, side, role, so a count, not futures points) |

The ticket:
```
SELL 10:54 · try 2 · entry 25,250f · stop 25,285f (35) · room 1.3σ
GAP    opened inside yesterday's range       ✓
TREND  VWAP touched 24 min ago               ✓
LEG    no 2R win today                       ✓
FLOW   sellers since the top −410            ✓
LIVE LEG  none
TAKE · hold till a valid BUY, the stop or 15:00
```
A weak opposite signal while in a trade shows as `BUY 12:18 · SKIP (FLOW ✗) · HOLD SELL`. Her hold voice (BOOK / TRAIL TIGHT,
`voice.py`) stays beside the line as information. Every level carries f (futures). Light mode only.

## 5. Architecture

One brain; faces render verbatim (the 24 Oct one-voice rule).

- **`execute.py` (new, tapemap root), pure:** `day_state(day, ones, delta, prev_ones, contract_changed, upto=None, ladder=None, spot=None) -> dict`.
  - `ones`: today's exchange 1-min futures candles (`ruler.ones_of(day)` shape); `delta`: Dext delta per minute (live frame
    `delta`, `{hh:mm: lots}`); `prev_ones`: the previous weekday's candles or None; `contract_changed`: bool; `upto`: last
    minute to use (None = all) — every read uses only minutes ≤ `upto`.
  - Bands `ruler.bands(ones, 3)`; triggers by the same loop as `look_cause_effect.replay` (lifted into execute.py).
  - Three walks over the same triggers: **PLAN A** every trigger, flip on any opposite trigger; **PLAN B** the rules of §2–§3
    (THE plan, the one the screen speaks); **PLAN C** PLAN B plus CAREFUL FLIP (in profit, a valid opposite signal also needs
    room ≥ 1σ to end the trade), logged only (A329).
  - Returns `{ok, day, upto, state, line, ticket, signals: [...], plan_a, plan_b, plan_c, gap, why}`; no I/O, no clock.
- **Server:** after the live NIFTY frame is built in the Jarvis pass, `fr["exec"] = execute.day_state(...)` (fail-soft: an
  exception gives `{ok: false, why}`); `jarvis_log.card` copies `exec` into `/api/jarvis/card` within its size contract. A stale
  frame already says why (`_jarvis_stale`).
- **Forward log** `data/exec/<day>.jsonl`: one row per signal (t, side, entry f, stop f, room, the four checks with numbers,
  LIVE LEG, PLAN A / B / C word) and one per plan close (plan, pts, why), keyed by (plan, t, side, event): a restart never writes
  twice. DAY END reads her marked trades (`_hold_list`) beside the plans.
- **Faces:** the Dext extension (`Desktop\dext extension\dext-decoder\dext-decoder`, 0.9.2 → 0.9.3): `lib/jarvis.js` already
  polls the card every 15 s; it renders `exec.line` and, at a trigger, `exec.ticket`, verbatim. The Jarvis page later.
- **Out of scope:** any order path; option premium; SENSEX (after NIFTY runs clean); new checks.

## 6. Testing

1. **Trigger parity:** execute.py's triggers = `look_cause_effect.replay` on all 60 sessions, and = the trigger log's NIFTY
   zone3 rows from 28 Oct (46 of 46).
2. **PLAN A parity:** = `look_edge_walk.walk(d, "FLIP")` trade for trade on all 60 sessions (+1,028 on 257).
3. **PLAN B parity:** 60 days without Dext → 119 trades, +1,650; the order-flow days with Dext → 24 trades, +1,260 (A331).
4. **No look-ahead:** for every trigger, `day_state(upto = the trigger close)` gives the same ticket as the full-day run.
5. **Missing data:** no Dext → FLOW "could not check"; no prior day or a changed contract → GAP "could not check".
6. `test_execute.py` (pytest, synthetic days, no repo data): each state; hold-through; LEG before/after a flip; GAP readable / not.
   The 60-session parity runs as a script (`docs/setup-review/check_execute_parity.py`), by hand.

## 7. Build order

1. `execute.py` + `test_execute.py` + the parity script (offline; outside market hours).
2. Server wiring (card field + forward log). A server change: shown to her as a replay of 11–13 Nov first; live only after her restart.
3. The extension face (0.9.3): she reloads it.
4. The Jarvis page.

Commit only on her word. No change to the live tool in market hours. Never start, stop or restart the server.

## 8. How we will know

DAY END shows PLAN B, PLAN A, PLAN C and her trades in points each session. After ≥15 SKIPs a side per check the counts go to
her (kept / skipped, won / stopped, points); she decides whether a check becomes a rule (a new registration).
