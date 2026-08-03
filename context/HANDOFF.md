# TapeMap v2 — handoff

**Point a new session at this file first.** It is the entry point; the deep
history is in `context/ui-v2-dashboard.md`, and the operator's own edge is
specified in `docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md`.

Last updated: 2026-08-03, after the build's first live session.
Branch: `feature/dashboard-v2`. Nothing is pushed.

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
| **`band_rotation` — the operator's edge** | ❌ **NEVER SCORED** |
| ZONE READ confluence | ❌ makes no claim by design; unvalidated as a read |

## 7. Open work, in priority order

1. **Score `band_rotation`.** The gap that matters. The spec's own rule —
   *"Encode, then score — in that order, and score before trusting"* — was never
   applied to the detector the whole tool exists to serve. Use
   `signal_review.py` against `data/backtest/` (NIFTY 65, BANKNIFTY 44,
   SENSEX 44), with controls, per-index before pooled. Everything else is
   decoration until this is done.
2. **Cross-check the leg pivots against Kite** — one session, five minutes.
3. **The trap filter's premise is broken.** 2026-07-30: tightest band of the day
   at 12:27, high at 12:33, never exceeded — compression can precede a move that
   fails. Needs a second condition or a rewrite.
4. **The `/api/contract` pair chart** — premium-matched pair across different
   strikes with the two-leg `confirm`. Still unbuilt, still the only place the
   full rule can reach a screen. Operator wants per-leg pivots there too
   ("B first, both eventually" — B is done).
5. **SWEEP/FILL events** in `structure.py`, so the panel can say "pool taken"
   instead of "pool at".
6. **SUPPORTS/AGAINST tagging** in ZONE READ — the operator wants it, but the
   rules belong in the engine and must be scored first.

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
