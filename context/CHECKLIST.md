# The rules register, and the chart checklist

**Why this file exists.** The rules are real and they are all written down — but
scattered across `HANDOFF.md`, `research-findings.md`, code comments and three
months of decisions. On 2026-08-05 the operator looked at the chart and said "I
don't think this chart is following all the rules", and there was no single place
to check that against. This is that place.

Nothing here is new. Every line names where it came from. **A rule with no source
does not belong in this file.**

Last updated: 2026-08-06.

---

## A · Honesty — load-bearing, not style (`HANDOFF` §9)

| # | rule |
|---|---|
| A1 | **Three different sentences.** "We checked and found nothing", "we could not check", and "we are not showing you" must never collapse into one rendering. |
| A2 | **Never invent a level, a greek, or a pivot.** An absence gets a reason. |
| A3 | **Score before trusting.** The one hypothesis that got that treatment died — which is the argument for doing it more, not less. |
| A4 | Answer the operator's trading questions straight. No "not a licensed advisor". |
| A5 | A cap on what is drawn must be **disclosed in the legend**, and the number the operator reads must come from the drawing code's **own predicate** — never a second count that can drift. (`STRUCT_ZONE_LIMIT`, `TradeTab.tsx:12`) |

## B · Frame — the bug that cost a whole day (`HANDOFF` §6b)

| # | rule |
|---|---|
| B1 | Anything **DRAWN** on the chart is **futures frame**. |
| B2 | Any **DISTANCE to a strike** is **index frame**. |
| B3 | `basis` is published; **a level whose frame is unknown is not drawn at all**. |
| B4 | `basis: null` ships with `basis_why`, never a fabricated `0.0`. Band is asymmetric (−0.15%..+1.0%) because futures trade above the index. |
| B5 | **Known gap:** when `basis` is null the engine still runs at `0.0`, so `ctx.pin.dist`, `cap` and `floor` are computed as if carry were zero. Not fixed. |

## C · What may be drawn as a SIGNAL (`research-findings`)

| # | rule | verdict |
|---|---|---|
| C1 | **d3 BUY, intraday, NIFTY/SENSEX** — the one surviving edge | §1, §5c |
| C2 | **d2 entries** — 180 NIFTY signals ≈ coin flip | **REJECTED** §2 |
| C3 | **Selling any upper band, every depth** — 5 datasets | **REJECTED** §2 |
| C4 | **BANKNIFTY inverts** — 37.5% hit, med −75.90 (n=8). The d3 rule does not apply there | §3, §5c |
| C5 | **d3 on F&O stocks** — pooled 47% hit, med 0.000% | **REJECTED** §3 |
| C6 | Overnight gap-fade · classic 15-min ORB · squeeze + falling-OI fade | **REJECTED** §2 |
| C7 | **Compression / trap=CLEAR as a filter is HARMFUL** — selected losers in 3 datasets. It is **context**, never a veto | §2 |
| C8 | **SMC layer** — 4× over-fires vs LuxAlgo, ⅔ UNKNOWN by construction | default **OFF** |
| C9 | **Engine event stream** — `risk` −0.1, `lean` −6.2 vs a +4.1 control | default **OFF** |
| C10 | The rule that must be drawn is **§5c's two-candle rule**. §1's one-candle rule is **VOID** — correctly measured, wrong trigger | §1 header |
| C11 | **OI strength ≥40% is NOT an entry veto** — it would have removed 10 of 12 signals including 9 winners. Hold/add past VWAP instead | §4 |

## D · Management — measured, and counter-intuitive (`trail_score.py`)

| # | rule | cost of breaking it |
|---|---|---|
| D1 | **Hold the stop until VWAP. Never move to breakeven.** | ~13 pts/trade |
| D2 | **Do not trail below VWAP.** | ~7 pts/trade |
| D3 | Past VWAP trail band-to-band; from +2σ, 15 pts under the high | — |
| D4 | Flat by **15:15** | — |
| D5 | **+6m is negative by design** (42.1%, med −2.70); it turns at +15m. This is *why* D1 holds | §5c |
| D6 | The **20-pt stop is a RISK decision owed by the operator** — deliberately not grid-searched | §5, §7.3 |

## E · Layout — has collapsed the chart twice (`HANDOFF` §4)

| # | rule |
|---|---|
| E1 | `TradeTab`'s root column **must keep a definite `height`**. `minHeight` collapses the index chart to **zero** (measured: `CANVAS 0 → DIV 0 → DIV 0` in a 420px box). |
| E2 | The column cannot grow, so **anything added after the chart goes in the section BELOW the column** — never inside it. |
| E3 | **Drawing toolbar goes ABOVE the chart.** A row under it is exactly what collapsed it. |
| E4 | After adding any row, **verify the index chart still renders** — not just that the new row looks right. That is the check that was skipped, twice. |
| E5 | Guards in place: chart `minHeight: 180`, column `overflow: hidden`. |

## F · Untouchable

| # | rule |
|---|---|
| F1 | `ui-v2/src/vendor/candl/` is **PRISTINE**. Never edit a file under `candl/` (`VENDOR.md`). |
| F2 | A frontend change that needs a backend change is a **separate, additive** change — agreed explicitly, never smuggled in. |
| F3 | **Do not let the assistant start servers.** Assistant-spawned processes die when its tool session recycles — two mid-session "disconnects" on 2026-08-03. |
| F4 | `corepack pnpm`, never bare `pnpm`. |

## G · Gates — all three before any commit

```bash
corepack pnpm --dir ui-v2 exec tsc --noEmit
```
```bash
corepack pnpm --dir ui-v2 build
```
```bash
python -m pytest -q
```

`vite build` does **not** typecheck — run `tsc` too. 401 tests as of 2026-08-06.

## H · Decisions owed by the operator — DO NOT GUESS (`HANDOFF` §8)

09:25 trigger gate · re-fire suppression on the same level · compression as
context vs co-condition · the expiry-day rule · a seller's stop and decay target ·
Setup B's expression · whether the ±1σ interior is no-trade with the edges as the
working zones.

---

# The chart checklist

Run this against what is on screen.

## Signals

| | check | state |
|---|---|---|
| ✅ | The chart draws **the population the score was measured on** — `d3` BUY, post-09:25, first-of-run (C1, C2, C3) | **DONE 2026-08-06** — `rotDrawPlan`. Matches `run_score.py:85-94` bar-for-bar, including computing first-of-run on the RAW stream before the band filter |
| ✅ | Withheld counts **stated in the legend, split by reason** (A1, A5) | **DONE** — rejected-band / pre-09:25 / repeat-in-run counted separately; a signal is withheld once, for one reason |
| ❗ | **How this was found:** the operator circled two pill clusters on 2026-08-05 and asked "what about no signal before 09:25, and the last-closing-candle rule". Both filters existed only in the SCORERS. `run_score.py:79` had already documented it — "the everything-pooled column answers *what do the pills on the chart actually mark*" — and nobody had read it back to the chart. | |
| ❌ | Pills mark the **§5c two-candle** entries (C10) | **OPEN** — `live.py:915` still calls the old `detect_index` |
| ❌ | Hover callout does not call a rejected band "apna setup" (A1) | **OPEN** — introduced 2026-08-05 by the fix above |
| ❓ | BANKNIFTY does not present d3 as tradeable (C4) | **UNVERIFIED** |
| ✅ | `trap` shown as context, never suppression (C7) | **HOLDS** — opacity + dash, never dropped |

## Frame

| | check | state |
|---|---|---|
| ✅ | `basis` known before any chain level is drawn (B3) | **HOLDS** — `basis 66.8`, `basis_why ""` |
| ❓ | `basis_why` is **displayed** when basis is null (B4, A2) | **UNVERIFIED** — never seen in the null case |

## Published but unread — the standing debt (`HANDOFF` §6b)

`basis_why` · `t_floored` / `t_real` · `w_bars_ce` / `w_bars_pe` · `gex_spot_band`
— all four published, **none read by the screen**.

> "The backend tells the truth; the screen is still silent." — §6b.
> That was written as v3's job. **v3 was cancelled 2026-08-05; the debt is v2's.**

## Readability

| | check | state |
|---|---|---|
| ❌ | Level labels at the left edge do not overlap | **FAILING** — `TRAP 24610.0`, `TRAP 24599.0`, `P 24583.1`, `−1σ 24620.5`, `PIN`, `CAP`, `HI` stacked |
| ❓ | Two different `TRAP` labels at two prices | **NEEDS A DECISION** — may be correct, may be a duplicate |
| ❌ | Pills do not sit over the candles they describe | **FAILING** in places |
| ✅ | FVG/OB zones capped and disclosed (A5) | **HOLDS** — `STRUCT_ZONE_LIMIT` |

## UI audit — re-run 2026-08-06, **10/20** (was 7/20 on 08-04)

Full report with measured numbers: **[`ui-audit.md`](ui-audit.md)**.

Still open, none fixed — the operator's call on 2026-08-06 was *"changes live
market mein karenge"*, because re-styling a trading screen against a closed
market and placeholder data is the wrong test:

Zero `@media` queries · no focus indicators (3 declarations for 22 buttons) ·
one ARIA attribute app-wide · no `prefers-reduced-motion` · `transition: width`
plus three `transition: all` · four side-tab accent borders · Inter/Roboto with
**no** `tabular-nums`, so ticking prices jitter · 22 hard-coded colours outside
`theme.ts` (was ~30) · **4 verified WCAG AA contrast failures**, the worst of
them on `23900`/`23808` — the CHANGES IF invalidation levels.

One decision owed: `vite.config.ts` binds `host: '0.0.0.0'` and the dashboard
was being read from another machine on 08-06, which contradicts PRODUCT.md's
"desktop only, no mobile usage scene". Either responsive work is P1, or the
bind should be `localhost`.

## Drawing tools

**None of `candl`'s 61 tools are wired.** The only app-side reference to the whole
drawings module is `LevelsOverlay.ts:5` importing the `Converters` *type*. Working
reference: `ui-v2/src/proto/ProtoDraw.tsx`. Toolbar goes **above** the chart (E3).
