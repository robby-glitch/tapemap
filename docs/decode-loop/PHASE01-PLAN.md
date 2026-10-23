# PHASE 0 + 1 — build plan (decode loop)

Contract: `docs/superpowers/specs/2026-10-11-decode-loop-design.md` (Mary approved the build, 19 Oct 2026).
Written 19 Oct 2026 after the close, before any code. Nothing here is committed; the server is never started, stopped
or restarted by this build; nothing under `data/` is rewritten except `data/rank/` (the reference store this build extends).

## What the investigation found before planning (so the plan fixes causes, not symptoms)

| item | finding | consequence for the plan |
|---|---|---|
| D6 basis | Every source is the right instrument. NIFTY book = `NSE_FO|48704` "NIFTY FUT 27 OCT 26" on every day 5–19 Oct (no roll, no wrong series); chain `spot` = `NSE_INDEX|Nifty 50` LTP, and it matches the REST index candles (chain_backfill) within a median 3 pts on 16 Oct. The low basis is **in the market**: on 16 Oct the options' put-call-parity forward and the future both sit ~45 NIFTY pts (~150 SENSEX pts) below spot + carry, and agree with each other within 2–13 pts. BANKNIFTY shows no such shift. | No data path to "fix". The root bug is the plausibility rule: a carry-only band calls a real basis "implausible" and hides spot (v2 "SPOT ?"). Fix = the band also asks the options; print the basis live with both. |
| D4 9 Oct 11:15 | The page never posted it: the frame record's `have_bars` (= the post's closed list) stayed 24 from 11:15 to 11:24 and became 25 at 11:25 with the 11:20 bar. The server was up 10:10–11:30 (restart at 11:30, after). Same for 12:35 and 13:20. `tape_log.append` writes every unseen `t` it is sent; the v2 build did not touch that path. | Not a `tape_log` bug. TapeMap fix = COVERAGE names the missing GC bars; the page-side drop is extension code (Mary's word) → Deferred. |
| D1 window | `upstox_chain.start()` subscribes the 17 strikes nearest the opening spot once; `poll()` hands all 17 downstream all day. | Subscribe wider once, hand downstream the 17 nearest the CURRENT spot. READ's nine = ATM±4 symmetric, narrowed with "?" at an edge. |

## Phase 0

| # | change | where | test that fails on the old code |
|---|---|---|---|
| D1a | recorder: subscribe ±16 strikes at start (keys 3×68 ≪ Upstox's 2000 `full` cap), and each poll hands downstream the ±8 nearest the live spot (recentred, symmetric). | `upstox_instruments.SUBSCRIBE_EACH_SIDE`, `upstox_chain.start/poll` | a poll after spot moves 300 pts returns strikes symmetric around the new ATM |
| D1b | READ: the nine = ATM±4 on the strike grid; if a strike is missing the window narrows symmetrically (ATM±m) and says so; m < 2 → writers "could not check". REV bumped. | `read._nine`, `writers` | a lopsided chain gives a symmetric set + `edge` |
| D2 | writing vs buying: per strike, 30-min IV change minus the ATM-wide IV change, OI-weighted over strikes whose OI rose, per side. ≤ −0.25 vol pts "bech ke likha [I]", ≥ +0.25 "khareed [I]", else "?". Display only; no READ gate reads it. | `v2feed` keeps IV on its slow rows (not on the wire); `read.writing_vs_buying` | OI up with falling residual IV is tagged writing; the READ word is unchanged with or without it |
| D4 | COVERAGE lists GC bars missing between the first and last recorded bar, and footprint-only bars. | `coverage.py` | 9 Oct-shaped tape with a hole → "GC 11:15 bar nahi aaya" |
| D5 | BANKNIFTY / SENSEX (and NIFTY without GC) flow ranks carry "single source" and are capped at notable. | `rank.py` | a p99 single-source delta is notable, never BADA |
| D6a | basis band: carry model as built (`frame_v2.basis_band`) + an options check (ATM±1 parity forward carried to the future's expiry, median of 15 one-minute samples). Outside carry but parity agrees within 0.1% of spot → plausible, flagged "carry se alag · options confirm". | `frame_v2.basis_band(parity=)`, `read.parity_basis` | 16 Oct: +6 at 11 DTE with parity +8 → ok; parity +60 → not ok |
| D6b | day high/low from ticks: futures H/L tracked on every book tick (v2feed), spot H/L from every chain row (~10 s); shown in spot AND fut on the Read card. Board's squares take the same H/L instead of the minute grid's. | `v2feed._tick`, `read.card`, `board.squares(hilo=)` | a spike inside a minute is the day high |
| COV | `/api/read` card gets `coverage`: per source (chain, fut ticks, GC, UX, rank ref, levels, basis) one row of kind `ok` / `none` (checked, nothing) / `cnc` (could not check) / `hidden` (not shown), with the reason. The three kinds are never merged. | `coverage.py`, `server._read_reply` | 9 Oct: the REST-rebuilt morning and the GC holes are named |

## Phase 1 — RANK beside every number

**One reference.** `tools/rank_build.py` gains a `read` section (schema `v` 2) in the same `rank_ref_<IDX>_<day>.json`
(days strictly before `<day>`). The extension's tables are untouched (checked byte-for-byte); the server strips `read`
from what it sends the page. The metric definitions live once in `rank.py` and the builder imports them.

**Buckets.** Day kind per index: EXPIRY (the chain's option expiry is that day), ROLL (the future's expiry is that day, or
the first day on a new contract), NORMAL. Each kind ranks only against its own kind. A bucket under 5 days does not rank.

**Same clock.** Day-level running totals (CVD since open, day volume, VWAP crosses since 09:30, writers' CE/PE build,
|A|) are stored per day at every 5-minute mark — a READ row is always on a 5-minute mark, so the comparison is exact.
Bar and window metrics (5-min delta SIZE = |Δ| ÷ same-15-min-slot median, share, 5-min volume, 40-min CVD, 40-min futures
OI %, 30-min nine-strike OI) are pooled within the spec's day-parts (09:15–10:00, 10:00–12:00, 12:00–13:30, 13:30–15:15).
SENSEX bar metrics use 15-minute bars with a 30-lot floor (FLOW-STATE §5).

**Rank object** (`rank.label`): `{raw, pct, pct_sign, n, tag, prov, why, src}`. `pct` = |value| (size), `pct_sign` = the
signed value's percentile (shown, gates nothing). Ties take the mid-rank (a count like "0 crosses" shared by many days is
not BAHUT KAM). Tags: ≤ p10 BAHUT KAM · < p70 noise · p70–89 notable · ≥ p90 BADA · above every reference value RECORD.
`prov` while N < 30 days. Thin bar (volume ≤ p10 of its day-part) → "thin", never BADA. Single source → capped at notable.
Delta two-source rule (NIFTY): a signal only if GC and Upstox are both ≥ p70 with the same sign; else "sources disagree".

**On screen** (existing Read tab and the answer band's READ line; no new screen):
- KYUN chips get their ranks inline: LIKHNA (CE/PE build, |A|), 30 MIN (CE/PE 30-min), FLOW (CVD, day volume).
  Positioning words (likh rahe / naye long / naye short / covering / long chhod rahe) only when the ranked move ≥ p70;
  else "OI flat" / "noise".
- one new KYUN row ABHI: last bar Δ (both sources), 40-min CVD, 40-min futures OI + its FUEL word.
- one new KYUN row AAJ: opening CVD (09:15–10:00), VWAP crosses since 09:30, 5-min volume.
- LINES: basis with its carry band and the options check; DIN H/L in spot | fut, with range ÷ IV-priced day σ [I].
- footer: COVERAGE "?" in three typographies beside ENGINE and DIN.
- Format: `p94 · N=17`; grey `noise` below p70; `BAHUT KAM` ≤ p10; N shown (provisional) while N < 30.
- Not ranked: prices and levels (spot, FLIP/T1/T2, PDH/L/C, LTPs), clock times and counts of the READ's own word changes
  — they are locations or bookkeeping, not measurements of the market (Decision).

## Order of work
1. `rank.py` + tests → 2. `rank_build.py` `read` section + tests → 3. `v2feed` IV / tick H/L + tests →
4. `read.py` D1b / D2 / parity / H/L + tests → 5. `frame_v2.basis_band(parity)` + test → 6. recorder D1a + test →
7. `coverage.py` + tests (D4) → 8. `server.py` wiring (`/api/read` ranks, coverage, `?at=` replays, rank_ref stripping,
schema-2 rebuild, board H/L) + tests → 9. `ReadTab.tsx` / `App.tsx` → 10. references for 20 Oct (all three indices;
the old NIFTY file kept under `data/rank/_pre-phase01/`) → 11. full pytest, the four extension suites, `tsc` + `vite build`,
before/after screenshots at 1245×720, the build report.

## Out of scope (from Mary / the spec)
D7 feed banner (dropped by Mary) · LEDGER / STATE / PLAN / SCORE (Phases 2–5) · any READ or zone gate change ·
win rates or confidence · extension code (the page-side GC drop is logged for her word).
