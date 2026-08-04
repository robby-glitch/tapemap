# TapeMap v2 — handoff

**Point a new session at this file first.** It is the entry point; every
strategy verdict is in `context/research-findings.md`, and the deep UI
history is in `context/ui-v2-dashboard.md`, and the operator's own edge is
specified in `docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md`.

Last updated: 2026-08-04, after the frame-bug day. 278 tests.
Branch: `feature/dashboard-v2`, six commits ahead. **Nothing is pushed.**

---

## 1. Boot sequence

Run BOTH in your own terminal windows. **Do not let the assistant start them** —
assistant-spawned processes die when its tool session recycles, which caused two
mid-session "disconnects" on 2026-08-03. The backend the operator started at
09:16 that day ran until close, untouched.

```bash
python server.py live 8765
```
```bash
corepack pnpm --dir "C:\Users\kaam\Desktop\new tool nifty\ui-v2" dev
```

- UI at `http://localhost:5173`; Vite proxies `/api` → `127.0.0.1:8765`.
- **The Dhan token expires daily** — first click of the day is **⟳ TOKEN**.
- `corepack pnpm`, never bare `pnpm` (not on PATH).
- **"The app stopped" → check BOTH ports:**
  `netstat -ano | grep -E ":(8765|5173)"`. Backend alive + Vite dead is the
  common case; no data is lost, just restart Vite.
- For maximum stability during a live session, `pnpm --dir ui-v2 preview`
  serves the built `dist/` (own proxy block, no HMR to fall over). Trade-off:
  code edits need a rebuild.

## 2. Gates — all three before any commit

```bash
corepack pnpm --dir ui-v2 exec tsc --noEmit
corepack pnpm --dir ui-v2 build
python -m pytest -q
```
265 tests as of 2026-08-03. `vite build` does **not** typecheck — run `tsc` too.

**GateGuard hook:** the first Write/Edit per file, and the first Bash call per
session, are denied with a request for facts (importers, affected API, data
schemas, the user's verbatim instruction). State them, retry the identical call.
Not a permission failure.

## 3. What is on screen (Trade tab, top to bottom)

| region | file | notes |
|---|---|---|
| stat strip + toggles | `trade/TradeTab.tsx` | LIGHT/DARK, FOCUS, SMC, STORY, LEGS, index switcher |
| disclosure lines | `TradeTab.tsx` | stale tape, date precision, chain stale, layer unavailable |
| **index chart** | `trade/ContractChart.tsx` + `trade/LevelsOverlay.ts` | candles, VWAP+σ ribbons, MAP levels, rotation pills |
| **OI strip** | `TradeTab.tsx` | latest `/api/oiflow` mark; 15s tab-local poll, no Dhan cost |
| ribbon + legend + "Hidden:" line | `TradeTab.tsx` | the Hidden line reports what the toggles withhold |
| **CE / PE premium panes** | `trade/LegChart.tsx` | own VWAP+σ, own OI pane, own prior-day pivots |
| **ZONE READ** | `trade/ZoneRead.tsx` | WHERE / BOOKS / GEX / FLOW / GAMMA / STRUCTURE / SETUP |
| ENGINE READ | `TradeTab.tsx` (`EngineReadPanel`) | verdict, setup, plays, floor/cap |

**localStorage keys:** `tape.mode`, `tape.focus`, `tape.smc` (default **OFF**),
`tape.story` (default **OFF**), `tape.legstack` (default OFF = side by side).
SMC and STORY default off deliberately — see §6.

## 4. ⚠️ The layout trap — read before touching TradeTab (cost two bad edits on 2026-08-03)

`TradeTab`'s root column **must** keep a definite `height: availH`, because
`ContractChart`'s root is `height:100%` and a percentage cannot resolve against
an auto-height flex container. Switching it to `minHeight` collapses the index
chart to **zero** (measured: `CANVAS 0 → DIV 0 → DIV 0` inside a 420px box).
The leg panes survive that, because they size from a real pixel `minHeight`.

Consequence: the column cannot grow, so **anything added after the chart goes in
the section BELOW the column**, never inside it. Rows inside compete for the
chart's pixels and, once the chart hits its floor, spill out and paint over the
CE pane. Current guards: chart `minHeight: 180`, column `overflow: hidden`.

**If you add a row under the chart, verify the index chart still renders** — not
just that your new row looks right. That is exactly the check that was skipped.

## 5. Backend map

| file | role |
|---|---|
| `server.py` | routes: `/api/data`, `/api/chain`, `/api/oiflow`, `/api/contract` |
| `live.py` | `build_payload`, `_nearest_opt_expiry`, `_floor_pivots`, `_opt_pivots`, `_atm_ids`, `_pivots`, `build_contract` |
| `engine.py` | `Session` / `session_json` — per-bar `ctx`, `gamma`, `setup`, and `fut`/`ce`/`pe` legs |
| `chain_metrics.py` | `ChainState`, `oi_flow` (minute grid; no Dhan call) |
| `structure.py` | SMC layer (FVG/OB/BOS/CHOCH/EQH/EQL/PDH/PDL/PREMIUM/DISCOUNT) |
| `band_rotation.py` | **the operator's own setup** — `detect_index` + two-leg `detect` |
| `contract_bars.py` / `contract_pair.py` | premium bars + σ bands; the 09:20 pair picker |
| `backfill.py` / `squeeze_score.py` | extend `data/backtest/`; score the squeeze hypothesis |
| `signal_review.py` | the scoring harness — **underused, see §7** |
| `trigger_log.py` | **live trigger logger (2026-08-04)** — server.py's refresh thread appends every NEW band-rotation record to `data/trigger_log.jsonl` with the bar's gamma/ctx + chain OI strength at that moment (fail-soft: can never stall the tape). `python trigger_log.py` = table, `score` = fill f15/f30 later. **Needs a server restart to activate.** Scores checklist items #17 (gamma regime) and #18 (ΔCE/ΔPE ratio) after ~20-25 live signals. |

**Ops gotchas:**
- Dhan `toDate` is exclusive for the newest session but INCLUSIVE for older
  ones — always slice with `_one_session`.
- `FUT_ID "61093"` in `dhan_fetch.py` is stale; the resolver gives 58072.
- **Dhan serves nothing before 2026-06-01** — expired contracts drop out of the
  scrip master, and `resolve_dynamic` silently returns the CURRENT contract for
  any historical date rather than failing.
- Contract OI ramps mechanically through rollover week (1.2M → 18M). Never
  compare front-month and far-month captures on OI *level*.
- `data/backtest/`: NIFTY flat (`fut_<ISO>.json`), other indices in
  subdirectories. An index PREFIX would corrupt eight readers that slice the
  date with `basename(p)[4:14]`.
- The Bash tool is Git Bash, not PowerShell: `@'…'@` here-strings mangle commit
  messages. Use `git commit -F - <<'MSG'`.

## 6. Verified vs unverified — the honest table

| claim | status |
|---|---|
| σ bands match the operator's Kite export | ✅ VWAP 0.078 pts median, ±3σ ratio 0.981 |
| backfilled Dhan == operator's Kite CSV | ✅ close diff 0.00, OI ratio 1.0000 |
| band pipeline order (`vwap_bands` → `resample`) | ✅ 0.972; reversed order 0.948 |
| option legs on the current weekly expiry | ✅ live 2026-08-03, held through a 24600→24700 strike hop |
| leg pivots vs Kite on the same contracts | ❌ **never cross-checked — do this first** |
| SMC layer | ❌ 4× over-fires vs LuxAlgo; ~⅔ UNKNOWN by construction → default OFF |
| engine event stream | ❌ `risk` −0.1, `lean` −6.2 vs a +4.1 control → default OFF |
| squeeze + falling OI = fade | ❌ **tested and REJECTED** — BANKNIFTY inverts the sign |
| d3 reversal on F&O STOCK futures | ❌ **REJECTED 2026-08-04** — pooled 47% hit, med 0.000% (n=47, 7 names + operator's own ADANIGREEN/RELIANCE TV exports). `stock_score.py`. Why, and the σ-scale arithmetic: **`research-findings.md` §3** |
| overnight gap-fade | ❌ **REJECTED 2026-08-03** — NIFTY fade ≈ 0 and below its own long control; reversion is intraday-only. `gap_score.py`. Detail: **`research-findings.md` §2** |
| classic 15-min ORB | ❌ **REJECTED 2026-08-03** — NIFTY breakouts *fade* (39% hit, −21.1 to close). `orb_score.py`. Detail: **`research-findings.md` §2** |
| **`band_rotation` — the operator's edge** | ⚠️ **SCORED — the one surviving edge.** NIFTY d3 buy: 72% hit, med +21 @30m vs +0.3 control (n=18). d2 = noise, selling = dead, compression filter = harmful. Management measured too (`trail_score.py`): **hold the stop until VWAP, never breakeven**. Two-leg confirm scored (`confirm_score.py`): does not help buys. **Full rule + numbers: `research-findings.md` §1** |
| ZONE READ confluence | ❌ makes no claim by design; unvalidated as a read |

## 6b. 2026-08-04 — the frame-bug day, and where v3 starts

**One class of bug produced most of what felt broken.** The tape is the MONTHLY
future; the option legs are the NEAREST WEEKLY. The carry between them ran
59→104 points that day — more than a strike step — and it was reaching both the
maths and the pixels. Fixed end to end (commit `67b9e6a`, `19ab6df`, `32e1db0`):
the engine's option forward and strike pick, `ctx.pin.dist`, `ctx.cap/floor`,
and on the UI side the walls, PIN, STK, max pain and gamma flip. The rule now
is one sentence: **anything DRAWN on the chart is futures-frame; any DISTANCE
to a strike is index-frame; `basis` is published in the payload and a level
whose frame is unknown is not drawn at all.**

Also fixed: `trigger_log` was logging forming bars (5 of 12 rows that morning
did not survive their own bar's close); `flip_px` conflated three kinds of
missing; `gex_regime` labelled off `gex_total` while the near-money book said
the opposite.

**A verdict went VOID.** `confirm_score.py` measured the two-leg confirm on
**monthly ATM** legs. The operator does not trade ATM — they take
**premium-matched legs, both above ₹100, within ±₹25 of each other**, going deep
ITM when the near strike gets cheap (see the `operator-trading-style` memory).
On 2026-08-04 the ₹11 ATM CE tagged no band all session — no entry signal and,
worse, no exit — while their real 24500 CE gave both. So "confirm does not help
buys" was measured on the wrong instrument: **void, not disproven.** Re-run it.

**Still broken** (independent audit, 2026-08-04) — none of these are cosmetic:

| | what |
|---|---|
| D2 | `engine.py` writer score self-scales off its own running max and reads direction from cumulative premium vs open with a 2% floor — on expiry day theta alone trips it, so `w_ce` pegs at 1.0 and the regime carries no information |
| D3 | raw Dhan IV feeds GEX with no clamp; the sanity gates exist but only on the display path |
| D5 | `gex_spot` sums ±1 strike (2 strikes) — too narrow to be stable |
| D7 | `t_days` floors at 0.25 and freezes through expiry afternoon |
| D8 | three independent writer-score methodologies feed three panels, with no confidence anywhere |
| P2 | wall migrations have no hysteresis — 12 "headlines" in one hour on 2026-08-04 |
| new | no sanity guard on `basis`; the post-close chain print gave −52.9 |

**UI audit** (`/impeccable audit`, scored 7/20): both P0s fixed. Seven left —
zero `@media` queries anywhere, no focus indicators, no `prefers-reduced-motion`,
`transition: width`, four side-tab accent borders, Inter/Roboto (a terminal needs
tabular figures), and ~30 hard-coded colours outside `theme.ts`.

**v3, agreed 2026-08-04.** Not a dashboard — a **state machine**: WAITING →
ARMED → TRIGGERED → IN TRADE → OUT, where the screen is mostly EMPTY because the
setup fires 1-2× a week. It is a **new frontend on this same backend**; if v3
touches the backend it is not v3, it is a third unfinished app. Order agreed:
commit (done) → D2 + basis guard → whale/`confirm_score` measurement → v3.
**Charting foundation — SETTLED 2026-08-05. Keep `candl`.** The throwaway
`/proto` spike ran. lightweight-charts **passed all three** pre-registered
proofs (σ envelope with `drawRibbon` reused at a one-line diff, OI pane from a
bare `paneIndex`, pills anchored with no rAF loop) — and the answer is still
candl, because the rubric missed the axis that decides it: **drawing tools.**
`candl` ships **61** with a full lifecycle API; lightweight-charts ships
**zero**. Full scoring, and the three things worth salvaging from the spike:
**`research-findings.md` §6.**

**The live finding underneath it:** ui-v2 turns **none** of those 61 tools on.
The entire app-side reference to candl's drawings module is
`LevelsOverlay.ts:5` importing the `Converters` *type*. The operator has never
been able to draw on their own chart, and the fix is a toolbar, not an engine —
`setActiveTool` / `setDrawings` / `onDrawingsChange` / `setMagnet` are already
on `IChartEngine`. Verified working 2026-08-05 (`ui-v2/src/proto/ProtoDraw.tsx`,
11 of the 61 exercised, drawings surviving a refresh via localStorage).

**So v3's first chart task is exposing that toolbar, not replacing the engine.**
Mind §4 when it lands in TradeTab — a row under the chart is exactly what
collapsed it twice.

`ui-v2/src/proto/` is a **throwaway**: delete the directory, revert the five
`App.tsx` lines, `corepack pnpm --dir ui-v2 remove lightweight-charts`. Kept
for now only as the evidence behind this verdict.

**Whale/volume-anomaly layer** (operator's TradingView indicator, source read
2026-08-04): buy/sell volume split by close position in the bar's range
(`(close-low)/range × volume`), flagged at 3/4.5/6σ over a 5-bar rolling mean.
Fully reproducible from data we already cache — no tick data needed — and better
on futures than on the index, where volume is synthetic. Two caveats: it is not
real delta (close position ≠ aggression), and a 5-bar σ window makes it fire in
clusters. Score it as a **d3 co-condition**, pre-registered, before it draws.

## 7. Open work, in priority order

**Read `context/research-findings.md` first** — it holds every verdict, the
surviving rule in full, and the stop-rule below.

1. **Collect live triggers.** `trigger_log.py` is wired into `server.py`'s
   refresh loop and needs a **server restart** to activate. It records every
   band-rotation fire with the bar's gamma/ctx and the chain's OI strength —
   the two conditions the operator watches that the cache cannot test.
   `python trigger_log.py score` fills outcomes once the day is cached.
   ~20-25 signals settles both. **This is the only source of new evidence.**
2. **🛑 STOP re-cutting `data/backtest/`.** Seven consecutive negative or
   falsified tests outside NIFTY/SENSEX d3 (2026-08-03/04), and two mid-search
   "findings" that evaporated on the next dataset. More slices will manufacture
   a false positive. Any new hypothesis must be **pre-registered in
   `research-findings.md` before the run**. See §5 there.
3. **The 20-pt stop is a RISK decision owed by the operator** — it sits exactly
   at the typical adverse swing (−20.7). Deliberately not grid-searched.
4. **Capture weekly option legs forward.** Expired weeklies vanish from Dhan's
   scrip master, so this data is unrecoverable later. Needed for the premium
   sell-side test (the only expression never fairly tested) and for the
   two-leg confirm on the expiry the operator actually trades.
5. **Cross-check the leg pivots against Kite** — one session, five minutes.
6. **The `/api/contract` pair chart** — premium-matched pair across strikes
   with the two-leg `confirm`. Still unbuilt.
7. **UI/UX overhaul** (dual review 2026-08-03, consensus 5/10): boot into
   Trade, delete the 7 fossil tabs, ZONE READ → price ladder on the chart's own
   axis, real type/spacing system, keyboard. Detail in `ui-v2-dashboard.md`.
8. **SWEEP/FILL events** in `structure.py`; **SUPPORTS/AGAINST** tagging in
   ZONE READ (rules belong in the engine and must be scored first).

## 8. Decisions still owed by the operator — do not guess

09:25 trigger gate · re-fire suppression on the same level · compression as
context vs co-condition (`CONFIRMED`+`CLEAR` = 0 of 64; they describe different
phases of a move) · the expiry-day rule · a seller's stop and decay target ·
Setup B's expression · whether the ±1σ interior is no-trade with the edges as
the working zones.

## 9. Working agreement that has held up

- Honesty rules are load-bearing: *"we checked and found nothing"*, *"we could
  not check"*, and *"we are not showing you"* are three different sentences and
  must never collapse into one rendering. Every panel follows this.
- Never invent a level, a greek, or a pivot. An absence gets a reason.
- Score before trusting. The one hypothesis that got that treatment died — which
  is the argument for doing it more, not less.
- Answer the operator's trading questions straight; no "not a licensed advisor"
  deflection.
- Ship a thin visible slice early. Weeks of backend-only work landed with
  nothing on their screen, and the chart they finally saw was unreadable.
