# Contract Tape — a live trade analyser for a single option contract

**Date:** 2026-07-29
**Branch:** `feature/dashboard-v2`
**Status:** design approved, not yet implemented

## The idea in one paragraph

Pick one option contract — say NIFTY 23800 CE — and watch it the way you watch
it in your broker terminal: its own premium candles, its own VWAP with standard
deviation bands, open interest in a pane below. On top of that, a narration
track that writes a line for every candle as it forms, and marks the candles
where **absorption** happened directly on the chart. If you tell it your entry,
it frames the narration around your trade.

## Why this is not a chart with commentary bolted on

The engine today emits an `ABSORPTION` event, but it fires on the **futures**
and it is defined as *high volume, small range* — effort without result
(`engine.py:748`). It never looks at open interest.

On an option's own tape you can do fundamentally better, because **OI tells you
who won the exchange**. Volume alone says a lot of contracts changed hands.
Volume plus a rising OI says the seller was *opening* — someone wrote into the
buying rather than closing out. That is the difference between "a fight
happened" and "the writers won the fight", and no part of this codebase
currently makes it.

The second half of the insight is the **spot cross-check**. A call premium
sagging while spot sags is not absorption, it is delta doing its job. Absorption
is only meaningful when **spot moved in the option's favour and the premium
refused to follow.** Every state below is gated on that.

## Scope

In scope: a new `Trade` tab in `ui-v2/`, a new backend route, a new narration
module, and a vendored copy of the CandL charting library.

Out of scope for this spec: the multi-contract watchlist, alerts/notifications,
and Echoes (historical analogue matching). Echoes is sketched at the end as a
later phase because it changes what data we cache, and that is worth knowing now.

---

## 1. The narration engine

New module `contract_tape.py`. Pure stdlib, no I/O, never imported by
`engine.py` — the same shape and the same isolation as `chain_metrics.py`.

### Inputs

Per bar of the contract: `O H L C V OI`, plus the session VWAP and σ bands, plus
the **spot close for the same minute**.

### Features

All features are expanding percentile ranks over the session so far, reusing
`engine.Rank`. **No absolute thresholds** — invariant #1. Ranks never see a
future bar — invariant #2.

| Feature | Definition |
|---|---|
| `vol_r` | percentile of `V` |
| `oi_r` | percentile of `abs(dOI)` |
| `rng_r` | percentile of `H − L` |
| `dOI` | `OI[i] − OI[i−1]` |
| `dPrem` | `C[i] − O[i]` |
| `dSpot` | spot close change over the same bar |
| `z` | `(C − VWAP) / (U1 − VWAP)` — position in σ, on the option's own VWAP |
| `favour` | `dSpot > 0` for a CE, `dSpot < 0` for a PE. A flat spot (`dSpot == 0`) is **not** favour — with no move to refuse, there is nothing to absorb. |

`z` is the same formula the engine already uses (`engine.py:123`), applied to
the contract's own premium instead of the future's price. This is what lets the
narration say *where* something happened, not just that it happened.

### The four states

| State | Condition | What it means |
|---|---|---|
| **ABSORPTION** | `vol_r > 0.9` · `oi_r > 0.9` · `dOI > 0` · `dPrem <= 0` · `favour` | Buyers paid up, spot went their way, premium refused, and OI *grew*. Writers took the other side and ate it. |
| **IGNITION** | `vol_r > 0.9` · `dOI < 0` · `dPrem > 0` · `rng_r > 0.8` | OI falling while premium rips — writers buying themselves back. Short covering inside the option. |
| **EXHAUSTION** | `vol_r > 0.9` · `dOI < 0` · `dPrem < 0` | Volume high, OI falling, premium falling — longs liquidating into each other. Nobody is opening. |
| **BUILD** | `oi_r > 0.9` · `dOI > 0` · `dPrem > 0` | Fresh longs and the premium is confirming them. |

The rank cutoffs (0.9, 0.8) are percentile positions, not price or volume
levels, so they self-calibrate to the contract. A 5-rupee weekly and a
300-rupee monthly get the same treatment.

**Where a state cannot be computed it is `UNKNOWN`, never `NONE`.** If OI is
missing for a bar, absorption is unknowable — and "unknowable" must not render
as "did not happen". This is honesty rule 3 applied to a new surface.

### Tiering

Every candle gets a record, so the track never breaks and you can always scroll
back. Loudness is what varies.

- **Tier 2** — one of the four states above. Full line with the numbers that
  triggered it.
- **Tier 1** — notable but not decisive: a σ-band tag, a premium/spot
  divergence, an IV shift, or this strike's role flipping. The last two come
  from the chain, not the bar series: `iv` off the strike's `ce`/`pe` dict and
  `ChainState.role[k]` (`CEILING` / `FLOOR` / `CONTESTED`). When the chain has
  no row for this strike — a far strike outside the index window — tier 1 falls
  back to band and divergence tells only, and the record says which inputs were
  unavailable rather than staying silent about it.
- **Tier 0** — everything else. One dim line: *"drifting, 340 lots, OI flat."*

### Output

One record per bar:

```json
{ "t": "13:24", "tier": 2, "kind": "ABSORPTION", "dir": -1,
  "head": "Writers absorbed the push at +2σ",
  "evidence": "vol rank 0.96 · OI +18,400 · premium −1.2 while spot +11",
  "z": 2.06 }
```

`head` and `evidence` are separate fields, not one prose string — the UI must
never parse prose (invariant #6). Every record carries the numbers that caused
it (invariant #5).

---

## 2. Backend

### `GET /api/contract`

| Param | Meaning |
|---|---|
| `idx` | NIFTY · BANKNIFTY · SENSEX |
| `strike` | any strike, not just ATM |
| `side` | CE · PE |
| `interval` | 1 · 2 · 3 · 5 · 15 minutes, default 3 |
| `days` | how many sessions back, default 1 |

Response:

```json
{ "ok": true, "index": "NIFTY", "strike": 23800, "side": "CE",
  "expiry": "2026-07-28", "interval": 3,
  "bars":   [{ "t": "...", "o": 0, "h": 0, "l": 0, "c": 0, "v": 0, "oi": 0 }],
  "vwap":   [{ "vwap": 0, "u1": 0, "d1": 0, "u2": 0, "d2": 0, "u3": 0, "d3": 0 }],
  "spot":   [0],
  "narration": [{ "t": "...", "tier": 2, "kind": "...", "head": "...",
                  "evidence": "...", "dir": -1, "z": 0 }],
  "forming": { "t": "...", "o": 0, "h": 0, "l": 0, "c": 0, "v": 0, "oi": 0 },
  "gaps": ["2026-07-25"],
  "live_error": null }
```

All arrays are aligned 1:1 by index. `forming` is the incomplete current candle
and is `null` when unavailable — see below.

### Where the data comes from

**Completed bars** — `dhan_fetch.rest_intraday(token, sec_id, "OPTIDX", day,
oi=True)`. This already returns real 1-minute OHLCV **plus open interest** for
any option security id; it has simply never been called for a non-ATM strike.
`live._atm_ids(strike, cfg)` already resolves an arbitrary strike to its CE/PE
ids for all three indices, so the resolution plumbing is strike-generic too —
only its caller is pinned to sticky-ATM. Multi-day is a loop, one call per
session, respecting the existing 0.22s rate-limit gap.

**The forming candle** — the `ChainPoller` already sees every strike within the
index window every ~10.5s, carrying `ltp`, `oi` and `vol`. Ticks since the
current interval opened are aggregated into O/H/L/C. This is the live-forming
part, and it needs no new feed.

**VWAP and σ bands** — computed server-side by reusing `live.py`'s existing
VWAP/σ routine, **anchored at 09:15 and reset every session**. Reusing it is the
point: v1 and v2 then show identical band numbers rather than two derivations
that drift. The browser never computes a band.

**Intervals** — 2m/3m/5m/15m are aggregated server-side from the 1-minute bars.
VWAP is computed on the 1-minute series and then sampled, not recomputed on
aggregated bars, so changing interval never moves the bands.

### Two honest failure modes

1. **Strike outside the chain window** (NIFTY ±1500, BANKNIFTY ±2000, SENSEX
   ±2500 per `instruments.py`) — the poller never sees it, so there is **no
   forming candle**. `forming` is `null` and the UI says so at full width. It
   does not hold the last completed candle open and let it look live.

2. **Missing prior sessions.** `mental-map.md` caveat #2 records that Dhan's
   expired-option feed is **rolling-ATM** — it serves a strike only while that
   strike was near ATM. A strike that sat far from spot on an earlier day may
   have no bars at all for that day. Those dates are listed in `gaps[]` and the
   chart renders a **visible gap**. Nothing is interpolated. This is the single
   biggest unknown in the design and Phase 1 exists partly to measure it.

---

## 3. Frontend

### Vendored library

`ui-v2/src/vendor/candl/` — upstream `src/` copied verbatim, plus `LICENSE` and
`NOTICE` (Apache-2.0 requires the attribution). **The tree stays pristine.**
Any change we need goes in a sibling file under `ui-v2/src/trade/`, never inline,
so we can still diff against upstream when it releases.

Imported from source rather than a built artifact: the package is not published
to npm (`@candllabs/charts` 404s) and its `files` field ships only `dist`, so a
git-URL install would depend on their build running. Vite compiles the source
with our app instead, which is simpler and gives us full visibility.

Four CandL capabilities carry this feature, and each would have been days of
work to build:

- `getMainConverters()` + `getMainPaneRect()` — live coordinate converters,
  documented for exactly this use. This is how narration glyphs land on candles.
- `setReplayCursor(index)` — clips every series-derived layer to bars `[0..index]`.
  Correctly causal already, which is what honesty rule 6 demands.
- `updateLast(candle)` — the forming candle, including right-edge auto-scroll.
- `setAlerts()` — draggable dashed price lines with tags. Entry and stop.

Note on indicators: `setIndicators(indicators: IndicatorRenderData[])` takes
**already-computed** arrays (`{instanceId, label, placement, outputs, range?}`),
aligned 1:1 with the candles. The engine never computes an indicator itself —
its `IndicatorDef` / `INDICATORS` registry is only a convenience layer for the
twelve built-ins, which we do not use. That contract is exactly invariant #4,
so every value on the chart comes from Python and the browser only reshapes.

Also worth recording, because it will be asked again: the OSS library has **no
user-editable indicator runtime**. A grep for `new Function`, `eval(`,
`registerIndicator` and `addIndicator` across `src/` returns nothing. The
JavaScript custom-indicator editor in the candl.live desktop product is
app-level and is not part of what we vendor. Custom indicators for this tool
therefore belong in Python, server-side — which is where invariant #4 wants
them regardless.

### Our code — `ui-v2/src/trade/`

| File | Responsibility |
|---|---|
| `useContract.ts` | polls `/api/contract`, returns bars, bands, OI, narration, forming candle |
| `indicators.ts` | maps server arrays into `IndicatorRenderData[]` for `setIndicators()` — a 7-output `overlay` (VWAP + six bands) and a 1-output `pane` (OI). Pure reshaping; it computes nothing. |
| `ContractChart.tsx` | mounts CandL, feeds `setData` / `updateLast`, owns the overlay canvas |
| `NarrationOverlay.ts` | draws state glyphs on candles. **The only file that touches CandL's coordinate system.** Re-queries converters every frame, as their docs require. |
| `NarrationRail.tsx` | the tiered scrolling feed |
| `PositionBar.tsx` | entry, qty, lot size, optional stop, live P&L |
| `TradeTab.tsx` | composition |

That split exists so the vendored engine has exactly one point of contact with
our code, and so the narration logic stays server-side and testable in pytest
like everything else.

### Layout — matching the broker terminal

- **Main pane** — premium candles, VWAP, ±1σ/±2σ/±3σ bands, absorption glyphs
- **Pane 2** — open interest line
- **Pane 3** — spot, thin and collapsible. Not present in Kite, but every
  absorption claim depends on spot direction, so the evidence is on screen.

Rail line and candle glyph are linked: clicking either highlights the other and
calls `scrollToTime`.

### Replay

The existing v2 transport drives `setReplayCursor(index)`, and the rail
truncates to the same index. Causal at both layers.

---

## 4. Position layer

Entry premium, quantity, **lot size entered with the trade**, and an optional
stop. Held in `localStorage` and **never sent to the server** — it is a private
trade and the backend has no reason to know it.

Entry and stop are drawn with `setAlerts()`. P&L sits in the header:
`(C − entry) × qty × lot`. Narration records gain position-framed asides
computed client-side from the same record — *"absorption at 84, two points above
your entry"*.

**Descriptive only.** The tool states what the market did to the contract and to
the position. It does not recommend entering or exiting, and it never places,
modifies or cancels an order — invariant #6, permanently.

---

## 5. Testing

`test_contract_tape.py`, alongside the existing 41 tests:

- **State tests** — synthetic bar sequences asserting each of the four states
  fires exactly when it should and, importantly, does *not* fire when the spot
  cross-check fails. A CE premium falling on falling spot must be classified as
  delta, not absorption. That single test is the one that protects the whole idea.
- **Causality** — narration computed over `bars[0..N]` must equal narration
  truncated at bar N. Ranks are expanding, so a regression here is silent
  otherwise.
- **UNKNOWN** — a bar with missing OI yields `UNKNOWN`, never a state.
- **Interval invariance** — VWAP bands at 3m equal the 1m bands sampled at 3m.

Existing gates still apply: `corepack pnpm exec tsc --noEmit`, `corepack pnpm
build`, `python -m pytest -q`.

---

## 6. Phasing

**Phase 1 — the data path.** `/api/contract` returning completed bars + VWAP
bands, rendered on the vendored CandL chart with the OI pane, plus a contract
selector. No narration. This proves the vendor decision and, critically,
**measures how much multi-day option history Dhan actually serves.**

**Phase 2 — the narration engine.** `contract_tape.py`, the four states, the
tiered rail, and on-candle glyphs. The heart of the feature.

**Phase 3 — the position layer.** Entry, stop, P&L, position-framed asides.

**Phase 4 — Echoes (later, not specified here).** CandL ships
`lab/similarity.ts` (377 lines) for historical analogue matching, and we hold
~55 cached Nifty days in `data/backtest/`. That would answer *"the last six
times this contract absorbed at +2σ, here is what the next twenty minutes did"*
— and `setProjections()` already draws ghost paths from the last candle. Listed
here because it implies caching per-contract history, which is worth knowing
before Phase 1 fixes a storage shape.

---

## 7. Invariants this design must not break

1. No absolute market thresholds — percentile ranks only.
2. Causal: bar `i` uses only bars `≤ i`. Replay is truncation, not recomputation.
3. `contract_tape.py` never modifies base engine signals.
4. No order execution, ever.
5. Flat files only.
6. UI renders, engine decides — including VWAP and every band.
7. Every signal carries its receipt: `evidence` names the actual numbers.

And the v2 honesty rules, which cost five real bugs to learn: a fallback must
never look like live data, failure is per-contract rather than global, never
compute a number you cannot source, never invent a greek, guard NaN at the
source, and replay must be causal.
