# PHASE 0 + 1 — build report (decode loop)

Built 19 Oct 2026 after the close, against `docs/superpowers/specs/2026-10-11-decode-loop-design.md` and
`PHASE01-PLAN.md`. **Nothing is committed.**

- The TapeMap server was never started, stopped or restarted. It was running after the close; it got ~a dozen cached GETs for the layout screenshots and one `/api/health`.
- Nothing under `data/` was written except `data/rank/` (below).
- Her running server kept writing its own `day_state` / `feed_log`.

## The basis root cause (D6)

**There is no feed bug.** Every source is the right instrument:

| source | instrument, as recorded |
|---|---|
| book / recorder future | `NSE_FO|48704` "NIFTY FUT 27 OCT 26" on every day 5–19 Oct (no roll, no wrong series); SENSEX `BSE_FO|864571` (29 Oct); BANKNIFTY `NSE_FO|48699` (27 Oct) |
| chain `spot` | `NSE_INDEX|Nifty 50` LTP off the socket; matches Upstox's REST index candles (`chain_backfill`) within a median 3 pts on 16 Oct |
| `/api/contract` `index_series` | the same future (REST); 16 Oct opened at 23,058 against a REST spot of 23,050 |

**The low basis is the market's own.** The options' put-call-parity forward (ATM±1, bid/ask mids) and the future agree with each other every day, within 2–13 pts once the carry between the two expiries is allowed for.

On 16 Oct both priced the forward about 45 NIFTY points (~0.19%) and about 150 SENSEX points (~0.2%) below spot + carry. Measured over the day, D = spot + carry − the instrument:

| | D (future) | D (options) |
|---|---|---|
| NIFTY 16 Oct | 44.7 | 44.4 |
| SENSEX 16 Oct | 156 | 144 |
| NIFTY 19 Oct | 26 | 9 (0-DTE noise) |
| BANKNIFTY | no such shift (−9 … −53) | no such shift |

A non-bank event common to NIFTY and SENSEX (a dividend or corporate action), or hedging demand that cash arbitrage could not close, would look exactly like this. The data cannot say which, and it does not need to.

**The bug was the plausibility rule.** The carry-only band (`frame_v2.basis_band`) called a real basis "implausible", so the v2 page printed `SPOT ?` and hid every spot level on 16 and 19 Oct.

**The fix.** The band now asks a second witness, `frame_v2.parity_basis`: the median, over 15 one-minute samples, of the ATM±1 synthetic forward carried to the future's expiry.

- **Outside the carry band, but within 0.1% of spot of the options:** plausible, flagged `unusual`, with the reason. Example: 16 Oct NIFTY at 11:20 `basis −0 · carry 47 · opt +15 ✓`.
- **The options disagree:** still `?`, no fut level printed, and the reason names both.

The basis now prints live on the Read card's LINES header, with its carry and the options' check.

## What changed, per item

| # | change | where | its test (fails on the old code) |
|---|---|---|---|
| D1a | The recorder subscribes ±16 strikes once (3 × 68 keys, under the 2,000-key `full` cap). Every poll hands downstream the ±8 nearest the **live** spot. Downstream width (walls, GEX, PCR) is unchanged; senses still pick their 7 from the wider set. | `upstox_instruments.SUBSCRIBE_EACH_SIDE`, `upstox_chain.near/start/poll` | `test_upstox_only::test_d1_each_poll_recentres_the_window_on_the_live_spot` |
| D1b | THE READ's nine = ATM±4 on the strike grid. A missing strike narrows the window to ATM±m on **both** sides and says so (`edge`). m < 2 is "could not check". REV becomes `read-1.1 (2026-10-19)`. The card shows `ATM±m ?` and COVERAGE names the edge. | `read._sym/_nine/writers` | `test_read::test_d1_the_nine_are_symmetric_around_atm_and_say_the_edge` |
| D2 | Writing vs buying, [I]: per strike, the 30-min IV change minus the ATM-wide IV change, weighted by the OI added, per side. ≤ −0.25 vol pt reads "bech ke likha"; ≥ +0.25 reads "khareed ke"; anything else reads "?". IV is kept in memory on v2feed's slow rows, off the VALIDATE wire. **Display only:** the test proves `read.timeline` is identical with or without it. | `v2feed` (IV), `read.writing_vs_buying`, the 30 MIN row | `test_read::test_d2_…never_moves_the_read` |
| D4 | Not a `tape_log` bug, and the v2 build did not touch it. The page never posted the 9 Oct 11:15 bar: the frame record's `have_bars` (= the post's closed list) stayed 24 from 11:15 to 11:24 and became 25 at 11:25. The server was up 10:10–11:30. 12:35 and 13:20 are the same. COVERAGE now names every missing GoCharting bar and every footprint-only bar. | `coverage.py` | `test_coverage::test_the_9_oct_gaps_are_named_d4` |
| D5 | BANKNIFTY / SENSEX flow ranks are Upstox only. They carry `1 src` and are capped at notable. COVERAGE says "GoCharting reads NIFTY only". NIFTY without GC (a late start) is capped the same way. | `rank.card_ranks`, `coverage` | `test_rank::test_a_single_source_index_never_reads_bada_on_flow_d5`, `test_coverage::…one_source_d5` |
| D6a | The basis band's options witness (above). | `frame_v2.basis_band(parity=)`, `parity_basis` | `test_frame_v2::test_d6_the_options_confirm…`, `…parity_basis…` |
| D6b | Day high / low from ticks. Futures: v2feed now keeps each second's tick high and low (`hl`, in memory). Spot: every chain row (~10 s). Shown on the card as `DIN H …s\|…f · L …s\|…f · 1.6σd [I]`. The Board's squares take the same high / low instead of the minute grid's marks. | `v2feed._tick`, `read.day_hl`, `board.squares(hilo=)`, `server._board_hilo` | `test_read::test_d6_…ticks_not_a_grid`, `test_v2feed::test_d6_…`, `test_board::test_d6_…` |
| COV | `/api/read` cards carry `coverage`: one row per source (CHAIN, FUT, GC, UX, RANK, BASIS, LEVELS, D2, QUIT). Each row has a kind: `ok` / `none` (checked, nothing) / `cnc` (could not check) / `hidden` (not shown). They show in three typographies in the card footer (amber `?`, grey italic `—`, grey `✓`); the title holds every row. | `coverage.py`, `server._read_decode`, `ReadTab.Coverage` | `test_coverage::test_three_absences_never_merge` |
| P1 | **RANK beside every number:** see below. | `rank.py`, `tools/rank_build.read_ref`, `server._read_reply/_read_decode`, `ReadTab.tsx` | `test_rank` (9), `test_rank_build::test_the_read_section…`, `test_frame_v2::test_api_read…`, `…page_never_receives…` |

### Phase 1: RANK

**One reference.** `tools/rank_build.py` adds a `read` section to the same `data/rank/rank_ref_<IDX>_<day>.json`.

- It uses days strictly before `<day>`, and the definitions live once in `rank.py`.
- The extension's tables are **byte-identical**: checked on the 20 Oct NIFTY file, all 13 keys.
- The top-level `v` stays 1.
- The server strips `read` (~100–200 KB) from what it sends the page. The test proves the page never receives it.

**What is ranked.** Every number on the Read card and the answer band's READ line that measures the market:

| row | numbers |
|---|---|
| LIKHNA | CE / PE build at the nine |
| 30 MIN | CE / PE 30-min change at the nine |
| FLOW | CVD since open, day volume |
| ABHI (new) | last bar Δ, two sources for NIFTY; 40-min CVD; 40-min futures OI % with its FUEL word |
| AAJ (new) | opening CVD 09:15–10:00, VWAP crosses since 09:30, bar volume |
| DIN line | range ÷ IV-priced day σ (a scale unit, [I]) |

**How it is ranked.**

- **Day kinds** NORMAL / EXPIRY / ROLL, each ranked only against its own kind. The expiry is read from the chain row, or from the surface log for rows before ~23 Sep, never computed from a weekday.
- **Same clock:**
  - running totals are compared at the exact 5-minute mark of the READ row;
  - bar and window metrics are compared within the spec's four day-parts;
  - SIZE uses the same-15-minute-slot median (FLOW-STATE);
  - SENSEX bar metrics use 15-minute bars with a 30-lot floor.
- **Tags:** `p94·N=17`, grey `noise` (< p70), `BAHUT KAM` (≤ p10), `RECORD Nd`, and `?` with the reason in the title.
- **Gates on the label:**
  - the thin gate (bar volume ≤ p10 of its day-part) means never BADA;
  - a single source is capped at notable;
  - delta follows the two-source rule (GC and UX both ≥ p70 with the same sign, else `src ≠` and noise).
- **Positioning words:** `PUT LIKH RAHE`, `naye long / naye short / covering / long chhod rahe` show only at ≥ p70. Otherwise the card says `PUT ki taraf · likhna noise` or `OI flat`. The READ's votes are untouched.

## Tests

| suite | before | after |
|---|---|---|
| `python -m pytest -q` (tapemap) | 1,660 passed, 1 skipped | **1,684 passed, 1 skipped** (+24) |
| `node test/shell.mjs` / `engine.mjs` / `overlay.mjs` / `panel.mjs` (orderflow-desk, `dist-v2`) | 78 / 70 / 26 / 35 | 78 / 70 / 26 / 35, 0 failed |
| `tsc --noEmit` + `npm run build` (ui-v2) | clean | clean |

**Fails on the old code.** The pre-build code was rebuilt in a scratch tree:

- tracked files from `git HEAD`;
- untracked files by reversing this build's edits, checked by running the old suites on it: 52 passed.

All 24 new tests fail there:

- 11 by assertion or missing function;
- `test_rank` (9) and `test_coverage` (4) cannot import modules that did not exist.

## The 9 Oct replay (Phase 1's done test, checked rather than claimed)

`/api/read?day=2026-10-09`, with references built from days before 9 Oct:

| check | result |
|---|---|
| CE writing | **BAHUT KAM** (p0, N=17–20 at every mark checked). PE build p88–95 BADA/notable; \|A\| 0.88 is **RECORD**. |
| Opening CVD 09:15–10:00 | **+6,244 = p100 of 10 GoCharting days.** It reads **notable · 1 src**, not RECORD: Upstox ticks began 10:11 (late start), so the two-source rule caps it. The spec's done test expects RECORD; the spec's own rule makes it notable. Mary's call. |
| VWAP crosses | **could not check:** no closes from 09:15 on a 10:10 start; GC 09:15–10:05 are footprint-only. |
| Bars after 10:00 (NIFTY) | 49 bars: 27 noise · 13 notable · 8 BAHUT KAM · **1 BADA** (11:25, −281, both sources p97, same sign). |
| BANKNIFTY | 38 noise · 7 notable · 1 BAHUT KAM · 3 ? |
| SENSEX | 20 noise · 15 notable · 14 ? (mostly under the 15-min / 30-lot floor) |

**D1's effect on recorded READ words (22 Sep – 19 Oct, 3,368 marks).**

- **197 change word (5.8%).** They are concentrated in BANKNIFTY 28 Sep (58/75) and 30 Sep (36/75), SENSEX 12 Oct (33/54), and 12 Oct NIFTY (9).
- **594 marks are now read on a narrowed (edge) window.** NIFTY 8 Oct changes no word but narrows 38 marks.
- Replays of those days now say `ATM±m ?` where the old window was lopsided. From the next session the recorder recentres, so the edge should be rare.

## Screenshots (1245×720, headless Chrome)

`docs/decode-loop/shots/`:

| frame | before | after |
|---|---|---|
| 9 Oct, whole day (to 14:10) | `read_2026-10-09_before.png` | `read_2026-10-09_after.png` |
| 9 Oct, as of 13:40 | — | `read_2026-10-09_1340_after.png` |
| 16 Oct, whole day (to 11:20) | `read_2026-10-16_before.png` | `read_2026-10-16_after.png` |
| 9 Oct, no backend (NOT LIVE banner) | `read_2026-10-09_before_nobackend.png` | `read_2026-10-09_after_nobackend.png` |

**How they were made.**

- A scratch server answered `/api/read` with the replay JSON (from `server._read_reply`, references built into scratch).
- Every other `/api` GET was fetched once from her running server and cached; the CHAIN STALE banner is hers, after the close.
- The 16 Oct "before" reply comes from the reconstructed pre-build code.

**Read with the layout:** everything fits 1245×720 with no scroll, even with a full-width banner.

**What the 16 Oct pair shows.**

- *Before:* `basis −0 [M]`, and "DONO LIKH RAHE" on all three.
- *After:* `basis −0 · carry 47 · opt +15 ✓`. BANKNIFTY and SENSEX now read `dono taraf · noise` because their writing ranks under p70; NIFTY keeps "DONO LIKH RAHE" (p73 / p82).

## Decisions

1. **D6:** fixed the plausibility rule, not a feed (there was no feed fault). The options witness needs both expiries from the data; without them, the old carry-only answer stands.
2. **D4:** the drop is on the page (extension) side. TapeMap names it; changing the extension needs Mary's word (Deferred).
3. **D1, recorder:**
   - The recorder subscribes wide once rather than resubscribing at runtime (no live socket churn).
   - A drift past 8 strikes on a side shows as an edge `?`.
   - Startup baseline fetch grows from ~34 to ~66 REST calls per index (≈ +8 s each at 0.25 s).
4. **D1, READ:** a symmetric window changes a gate's input (READ words feed READ-V2 §E). This is the approved D1 item, not a tuning. REV is bumped and the forward log carries it.
5. **N** = reference days. A bucket under 5 days does not rank. Ties take the mid-rank.
6. **The partial 09:15 bar.** The Upstox 09:15 bar is partial on every recorded day, because the server starts ~09:17. Running totals accept it, so every day's total is "from the first tick" alike. Any other hole stops the total, and the hole is named.
7. **The READ's own FLOW numbers** (book ticks) are ranked against the Upstox history, the same feed. When they are GoCharting-filled (a late start), they are not the same number: `?`, and GC alone speaks, capped.
8. **Not ranked:**
   - prices and levels (spot, FLIP / T1 / T2, PDH / L / C, LTPs), times, and the READ's own change count: locations, not measurements;
   - the engine's answer-band chips (MAX PAIN, GEX, PCR, daytype evidence): the engine's voice, with no reference in the spec (Deferred).
9. **One reference:**
   - The 20 Oct NIFTY reference was rebuilt; its id goes from `…fa3c7480` to `…e086ff3f`, with tables identical. The old file is kept in `data/rank/_pre-phase01/`.
   - BANKNIFTY and SENSEX 20 Oct are new.
   - **21 Oct was pre-built for all three.** 20 Oct looks like a holiday: NIFTY's weekly expired on Monday 19 Oct.
   - Older files (9–19 Oct) have no `read` section. If the READ asks for one of those days, her server rebuilds it once in the background and overwrites it, with identical tables plus `read`.
10. **UI:** KYUN is widened (1.4fr), the rank pills are 9 px and written `p94·N=17` (the asked `p94 · N=17` without the spaces, so the read's own side is never clipped), and the footer gains a third COVERAGE slot. The answer band's READ line (`ReadLine`, rendered by `App.tsx`) carries the LIKHNA word, the last bar Δ and KHULA with their ranks; `App.tsx` itself is unchanged. No new screen, nothing removed. An older server gets the old card unchanged, because every new part is conditional.

## Deferred

- The page-side GoCharting bar drop (extension; her word).
- VWAP crosses and the opening CVD on a late start, rebuilt from REST 1-minute futures candles.
- Largest single-price cell rank (not on the Read tab).
- Ranks for the engine's answer-band chips.
- FLOW STATE / the rolling 1-minute read on the Read tab.
- Per-bar tags (expiring contract after 15:00, first day on a new contract).
- Day-bootstrap threshold ranges.
- `frame_v2._wall` accepting an options-confirmed basis. It would change READ-V2 §E's T2, a signed rule.
- moved ÷ priced is in the API and the tooltip; PREMIUM on screen is Phase 3.
- LEDGER / STATE / PLAN / SCORE (Phases 2–5).

## What Mary must do

1. **After the close:** `.\stop.bat; .\start-v2.bat`. This loads READ rev 1.1, RANK, COVERAGE, the recentred recorder, the basis witness, and the Board's high / low.
   - Startup takes ~25 s longer: the wider strike baseline is fetched once.
   - The 21 Oct references are already built. A missing day builds itself in ~20 s per index; meanwhile the newest earlier file is served.
2. **ui-v2:** the 5173 dev server picks up the source; press F5 on the TapeMap tab. A built copy needs `npm run build` in `tapemap/ui-v2`.
3. **Extension:** nothing to do. The v2 page receives its unchanged tables under the new id once. On a day like 16 Oct it now prints spot instead of `SPOT ?`.
4. **Rollback:**
   - Revert `server.py`, `board.py`, `upstox_chain.py`, `upstox_instruments.py`, and the edits in `read.py`, `v2feed.py`, `frame_v2.py`, `tools/rank_build.py`, `ui-v2/src/read/ReadTab.tsx`.
   - Delete `rank.py` and `coverage.py`.
   - Copy back `data/rank/_pre-phase01/rank_ref_NIFTY_2026-10-20.json`.
   - Restart after the close.

## Files

**New**

- `rank.py`, `coverage.py`, `test_rank.py`, `test_coverage.py`
- `docs/decode-loop/PHASE01-PLAN.md`, this report, `docs/decode-loop/shots/`
- `data/rank/rank_ref_{BANKNIFTY,SENSEX}_2026-10-20.json`, `rank_ref_{NIFTY,BANKNIFTY,SENSEX}_2026-10-21.json`, `data/rank/_pre-phase01/`

**Changed**

- `read.py`, `v2feed.py`, `frame_v2.py`, `tools/rank_build.py`, `server.py`, `board.py`, `upstox_chain.py`, `upstox_instruments.py`
- `ui-v2/src/read/ReadTab.tsx`
- `test_read.py`, `test_v2feed.py`, `test_frame_v2.py`, `test_rank_build.py`, `test_upstox_only.py`, `test_board.py`
- `data/rank/rank_ref_NIFTY_2026-10-20.json` (regenerated)

---

## Amendment, 19 Oct 2026 (evening): an absent source is not a disagreeing one

Decided as a trader under Mary's standing rule (method questions; she signs the amendment). CLAUDE.md rule 6: a missing
value is never treated as a contrary value.

**The rule now.**

- **Both sources present and agreeing** (both ≥ p70, same sign): the pair's rank, as before.
- **Both present and disagreeing** (signs differ, or one ≥ p70 and the other not): `sources disagree`, **capped at notable**.
  - The capped label is the stronger source's.
  - Before, this read "noise" with the weaker source's rank.
- **One source absent** (Upstox not yet ticking, a feed gap, or BANKNIFTY / SENSEX with no GoCharting): that source's own
  rank, **uncapped**, tagged `GC only` / `1 src`.
  - This replaces D5's "cap at notable".
  - The thin-bar cap is unchanged.

**Code.**

- `rank.label` and `rank.two_source`; `card_ranks`' BANKNIFTY / SENSEX branch.
- The pill (`ReadTab.Rk`) prints `GC only` / `1 src` / `sources disagree`.

**Tests.**

- Five `test_rank.py` tests fail on the pre-amendment `rank.py`, checked in a scratch copy:
  - the new `test_9_oct_record_opening_reads_record_gc_only_while_a_disagreement_still_caps`;
  - four amended rule tests: single source tagged not capped, the disagree cases capped, D5 `RECORD · 1 src`, and the NIFTY both-present-disagree bar.
- Full pytest, the four extension suites, `tsc` and `npm run build` were re-run; the final pytest count is below.

**The 9 Oct replay, re-run.**

- The opening CVD +6,244 now reads **RECORD · GC only** (p100 of 10 GoCharting days).
- NIFTY bars after 10:00: 17 noise · 22 notable · 8 BAHUT KAM · 1 BADA · 1 RECORD.
  - The RECORD is the 11:15 bar, +834. GoCharting never sent that bar, so it reads `UX only`.
  - The BADA is still 11:25, −281, both sources agreeing.
- The disagreeing bars that read noise now read notable · `sources disagree`.
- BANKNIFTY: 1 BADA · 1 src (13:45). SENSEX: 15-min bars at 11:15 and 12:00 read BADA · 1 src.
- **Final counts:** pytest 1,685 passed, 1 skipped (+1 test); extension suites shell 81 / engine 70 / overlay 26 / panel 35, 0 failed (shell was 78 earlier tonight: its suite grew outside this build); `tsc` and `npm run build` clean. No restart, no commit.
