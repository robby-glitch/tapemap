# TRADE MAP — build report (24 Oct 2026, weekend; her word: "build it")

Spec: `docs/superpowers/specs/2026-10-24-trade-map-design.md` (binding). Built as written, nothing from its §7. Display only:
no registered rule, no voice state or trigger, no WARN / EXIT source changed. `hold2.py`, `fold.py`, VALIDATE rev 3 untouched.
**Uncommitted. Live at her TapeMap restart + reload of the extension at 0.5.10.**

## 1. What was built, and where

| piece | file:line | what |
|---|---|---|
| the brain | `trademap.py` (new) | `read()` :267 → `{ok, l4, l5, detail[], push, ulta, range, zone, fuel, levels, prem, events, tag "I", why}`; `into()` :314 merges it onto the voice. Pure, no I/O, no clock |
| l4 | `trademap.py:125` `l4_line` | push / ulta push from `hold2.pushes` (unchanged), filtered as `exit_v2` does (closed after the first whole minute after entry, and by now); `push ? ref nahi` (= `hold2.NO_REF`) when there is no reference table, never "none"; range = session spot hi − lo over the EM |
| EM | `trademap.py:76` `em`, `:68` `weekdays` | line-for-line port of `engine.js emOf` / `weekdays` (first row 09:20–09:30, ATM straddle / 0.8 / √N, both ends counted, holidays not removed [I]) |
| l5 | `trademap.py:91` `wall_nearest`, `:104` `survivor` | port of `engine.js wallNearest` on the paying leg; `{K+basis}f / {K}s (pts from fut now) · K leg OI`; at the zone (spot within one step) only `EFFORT x× sasta @ naya low` (d < 0, ≤ 0.5×) or `EFFORT x× mehenga @ naya high` (d > 0, ≥ 2×) from the DECODE block's effort (`holdshadow._dec_at`), extreme within 15 min; mirrors / read nahi / before 09:56 print nothing |
| fuel | `trademap.py:148` `fuel` | the losing leg's 3 largest-OI strikes pinned at the entry snapshot (ITM or within one step of ATM), entry → now → session peak of their sum; a strike that reads None now → `fuel: could not check — K leg not in the snapshot`; per-strike tooltip |
| levels | `trademap.py:181` `levels_line` | PDH/PDL (server memory `_read_levels`), IB hi/lo (09:15–10:15 spot), HOD/LOD, between spot and 2 EM her way, nearest first, `s/f`; `PD ? — not fetched` when absent |
| R | `trademap.py:314` `into` | `R +1.7 · BE lock at 2R`, `R +4.5 · BE lock ✓ 11:25` once engaged (third detail line) |
| seller | `trademap.py:210` `prem_path` | `premium = intrinsic + TV · theta ~₹/hr [I] · at zone ≈ ₹ [I] · 10 min: prem, fut`; only when `role == "short"` |
| forward log | `trademap.py:244` `zone_events` + `server.py:3352` `_map_log` | `data/hold/map_<day>.jsonl`, write-once per (trade, event, key): `ulta_push` (t, origin, fut) and `zone` (first minute within one step of each wall ahead: k, leg, fut, OI, effort or null, pts). Rebuilt from the record each minute (anytime-start); disk read before the first write. No outcomes |
| l1 / 15:20 | `voice.py:169`, `:179`, `:74` | `+N pts` = d × (fut − E) [M]; `pts` added to the fields; `r_now` kept. 15:20 reason `15:20 — spot 15:15 se frozen (HOLD v2)` |
| server | `server.py:3299–3312` (`_hold2_run`), `:3387`, `:3397` (`_in_trade`) | map read once a minute off-thread beside HOLD v2, stored as `out["map"]`; stripped from `hold2`; merged into `voice` (`l4`, `l5`, `detail`, `map`), or `map_why` and the three lines alone |
| A56 replay | `voice_path.py` (new), `tools/voice_replay.py` | `run()` moved out of the tool (same loop, plus the map, plus each read's own second `at`); the tool imports it and gains the 30 Sep trade |
| A56 endpoint | `server.py:3409` `_voice_path`, `:3440` `_voice_path_run`, route `:5625` | `GET /api/voice_path?id=&day=` → `{ok, path [{t, at, voice}], receipt, dec_src, rev}`; computed once off-thread, cached at `data/voice/path_<day>_<id>.json`; today's trade before 15:40 → `could not check — replay of today's trade after 15:40` |
| A54 | `ui-v2/public/validate2/engine.js:503–507`, `app.js:137, :247` | T1 → `PULLBACK`, T2 → `NEXT WALL`, `cond` dropped; consumers in app.js updated; harness + `test_validate3.py` assert the names |
| A55 | `app.js:138` (ladder STOP), `:319` ("to stop" cells) | with the voice on: `vc.stop_f` / `vc.stop_s`, tooltip names `vc.stop_src` — one stop on the screen |
| Validate face | `app.js:296–303` (voice, `v4`/`v5`, map rows, the replay's why), `:474` `voiceAt`, `:572` `pollVpath`, `app.css:367` | live voice while following the clock; off it, the path's latest read ≤ T |
| hold window | `ui-v2/src/hold/HoldWindow.tsx:43, :307–308, :317`, `hold.css:500` | `v4` / `v5` divs, map lines first in the opened detail |
| extension | `orderflow-desk/src/shell/panel.js:377` (`v4`/`v5` spans), `:384` `mapDetail`, `:434` | detail lines first in the `vOpen` detail; 0.5.10 (`manifest.src.json`, `recorder.js`, `v2.js BUILD 0.5.10-v2.10`); `dist-v2` rebuilt (main.js sha1 `2ac54aa0…`) |
| leak guard | `conftest.py`, `server._isolate_mock_writers` | `server.MAP_DIR`, `server.VOICE_DIR` under tmp / data/mock |

## 2. Decisions where the spec was silent (as a trader)

1. **l5's example `22,916f / 22,888s` contradicts its own rule** ("spot = K"). Built the rule: `22,926f / 22,900s`. The strike IS the
   spot level; a spot print 12 pts off the strike would mislabel the wall.
2. **Push window = HOLD v2's own** (`close > entry minute + 1`, `≤ now`), so l4's push is the same push that moves the trail.
   A bar closing at the end of her entry minute mostly predates her entry.
3. **Zone survivor freshness: the extreme within 15 min** (holdshadow's `W15`, VALIDATE rev 3). Without it a 25-min-old cheap low
   would be printed "at" a zone she reached later.
4. **Fuel uses the rule, not the example.** 21 Oct the rule picks 23000/23050/23100 PE (213 L at 10:07: 120.3 + 35.3 + 57.5) —
   23000 PE is ITM by 12 and ATM. The example's 23050/23100/23150 (104 L) was the DETECTOR's set. Same story: 213 → 114 L by 12:34.
5. **Fuel's entry snapshot** = the last chain row at or before her entry (first row if she entered before the recorder).
   **Peak** = the session peak of the three-strike sum over rows where all three read (a None row is skipped, never a 0).
6. **Levels:** one printed price is one level (`IB lo/LOD 22,926s`); IB only once complete (≥ 10:15 — before that IB = HOD/LOD);
   strictly beyond spot; no EM → unbounded, said (`her way (EM ?)`).
7. **R line:** `BE lock at 2R` only when HOLD v2 has a lock level; once engaged `BE lock ✓ HH:MM` (as l2 already says).
8. **Seller's "10 min: fut"** = Δspot over the same two chain snapshots as the premium (every f on this face is spot + the one
   basis). A recorder hole (no snapshot within 10–12 min ago) → `10 min: ?`, never a 40-min delta. Theta is calendar-time
   (`gamma.DAYS_PER_YEAR`), F = chain spot, [I].
9. **Forward log:** `zone.pts` = her trade's points at the touch (d × (fut − E)), the number a later scorer needs; `fut` there =
   spot + today's basis [I]; `ulta_push.fut` = the push bar's futures close. Both reproducible after a restart.
10. **Endpoint:** never computed in market hours (09:15–15:40 weekdays) for ANY day, not only today — the replay is ~5–15 s of
    CPU per trade under the GIL beside the live loop. A cached path is served any time. Path ends at her exit + 1 min (the recap
    takes over after it), 15:20 if open. A failed compute is said once, not retried until a restart. Cache keyed by `rev`.
11. **Replay effort:** the DECODE log began 23 Oct. For an older day `voice_path` rebuilds the block's effort at each 5-min close
    with the server's own recipe (`server._decode_effort`: `effort.read` on the futures book + chain spot), `dec_src: "rebuilt"`.
    The shadow lines keep the log alone (A52's receipts unchanged). PDH/PDL in a replay = the prior recorded session's chain spot
    to 15:15 (CAS) [M].
12. **Replay read time:** each path row carries `at` (its own second, e.g. 11:21:30); Validate shows the latest read ≤ T, so it
    never shows a read before its data existed.
13. **Faces:** l4 / l5 wrap (one CSS line each in Validate and the hold window) — the block's `nowrap` cut l5's survivor read to
    `EFFORT…`. In the panel the detail lines sit first in the opened detail, in the receipt's `.vc.rc` style.
14. **A56 needed one more fix:** Validate never listed a PAST day's trades — `/api/fold/record` returns her day_state mark
    (`t0`, `side` = CE|PE, `role`) and app.js mapped it as the engine's (`entry_t`), so `t0` was NaN. Now that shape goes through
    the existing `mapTrade` (`app.js:558`).
15. **Absence:** `push ? — no 5-min bars` when the bars are missing; `pullback zone ? — could not check: no chain row`; the map
    failing or not read yet → `map_why`, three lines alone.

## 3. What I could not do, and why

- **HoldWindow not seen rendered.** It needs the live server + vite; tsc is clean. Validate WAS seen rendered (a scratch mock
  serving the face's files, `/api/v2/data`, `/api/fold/record`, `/api/voice_path`; read-only): 21 Oct at 11:21:45 shows the
  replayed block (HOLD, l4, l5 with `EFFORT 0.44× sasta @ naya low`), the map rows, "to stop" 54 / 61 → 22,965s / 22,992f and the
  ladder's STOP 22,992f.
- **11:18 shows no EFFORT read** although A54 quotes "11:18 0.44×". The DECODE close at 11:15 (readable 11:16) read 1.43× normal;
  the 11:18 low's 0.44× is the 11:20 close, readable at 11:21. That is the block's latency (Fable A3), not a bug. Added 11:21.
- **`ui-v2/dist/` not rebuilt** — a stale build artifact; the live UI is vite on 5173 serving `public/`.
- **A test leak, fixed:** the first full run wrote one row to `data/hold/map_2026-09-30.jsonl` (test_fold_live's toy trade
  through `_hold2_run`). Removed; `MAP_DIR` / `VOICE_DIR` now in `conftest.py` and `_isolate_mock_writers`. `SHADOW_DIR` has the
  same gap (pre-existing, not touched).

## 4. Proofs (replay: `python -I -X utf8 tools/voice_replay.py <out>`, read-only, in-sample, describe only)

### 21 Oct `NIFTY-23000PE-long-100730` (long PE @174.85 10:07:30, out 13:05:04; effort rebuilt)

| t | state | l1 | l2 | l3 | l4 | l5 |
|---|---|---|---|---|---|---|
| 10:30 | HOLD | ▼ 23000 PE · 23 min · +27 pts (₹+8) | stop 23,052f / 23,030s ≈ ₹145 · BE lock at 22,906f | why: CE 23000 writers building · flow saath | push ▼ abhi nahi · ulta push: none · din range 1.01 EM | pullback zone 22,922f / 22,900s (54 pts) · 22900 PE 70.1L |
| 11:18 | WARN | ▼ 23000 PE · 71 min · +35 pts (₹+8) | stop 23,052f / 23,026s ≈ ₹144 · BE lock at 22,906f | why: CE front gave up @ 23,010f · line 23,052f (HOLD v2) · 11:06 | push ▼ abhi nahi · ulta push: none · din range 1.01 EM | pullback zone 22,926f / 22,900s (43 pts) · 22900 PE 74.5L |
| 11:21 | HOLD | ▼ 23000 PE · 74 min · +71 pts (₹+28) | stop 22,992f / 22,965s ≈ ₹172 · BE lock at 22,906f | why: flow saath · zone peeche | push ▼ 11:15 (1 min) · ulta push: none · din range 1.15 EM | pullback zone 22,927f / 22,900s (6 pts) · 22900 PE 70.7L · EFFORT 0.44× sasta @ naya low |
| 12:34 | EXIT | ▼ 23000 PE · 147 min · +220 pts (₹+140) | stop 22,780f / 22,762s ≈ ₹323 · BE lock ✓ 11:25 | why: stop hit 22,780f (HOLD v2) · 12:34 | push ▼ 12:20 (9 min) · ulta push: none · din range 2.15 EM | pullback zone 22,718f / 22,700s (66 pts) · 22700 PE 65.5L |
| 13:05 | EXIT | ▼ 23000 PE · 178 min · +237 pts (₹+150) | stop 22,780f / 22,761s ≈ ₹318 · BE lock ✓ 11:25 | why: stop hit 22,780f (HOLD v2) · 12:34 | push ▼ 12:20 (40 min) · ulta push: none · din range 2.15 EM | pullback zone 22,719f / 22,700s (47 pts) · 22700 PE 73.5L |

Detail at 12:34: `fuel 23000/23050/23100 PE · entry 213L → now 114L · peak 255L 09:46` · `levels LOD 22,705s/22,723f` ·
`R +4.5 · BE lock ✓ 11:25`. State sequence unchanged from A52 (refactor faithful).

### 30 Sep `NIFTY-22750CE-long-101012` (long CE @164.7 10:10:12, out 11:16:50; 12:46 read as if still in; effort rebuilt)

| t | state | l1 | l2 | l3 | l4 | l5 |
|---|---|---|---|---|---|---|
| 10:30 | HOLD | ▲ 22750 CE · 20 min · +14 pts (₹+2) | stop 22,849f / 22,726s ≈ ₹150 · BE lock at 22,897f | why: PE 22800 writers building · flow saath | push ▲ abhi nahi · ulta push: none · din range 0.55 EM | pullback zone 22,922f / 22,800s (44 pts) · 22800 CE 83.6L |
| 11:16 | EXIT | ▲ 22750 CE · 66 min · -80 pts (₹-38) | stop 22,849f / 22,736s ≈ ₹159 · BE lock at 22,897f | why: stop hit 22,849f (HOLD v2) · 10:34 | push ▲ abhi nahi · ulta push ▼ 10:55 @ 22,827f · din range 0.58 EM | pullback zone 22,812f / 22,700s (28 pts) · 22700 CE 99.0L |
| 12:46 | EXIT | ▲ 22750 CE · 156 min · +34 pts (₹+14) | stop 22,849f / 22,741s ≈ ₹154 · BE lock at 22,897f | why: stop hit 22,849f (HOLD v2) · 10:34 | push ▲ 12:35 (6 min) · ulta push ▼ 11:15 @ 22,802f · din range 0.71 EM | pullback zone 22,908f / 22,800s (9 pts) · 22800 CE 83.1L |

At 12:46 the wall is Fable's T1 touch (83.0 L); EFFORT read 1.15× normal → nothing printed (no survivor). The voice said EXIT at
10:34 (line 22,849f); she held to 11:16 at −80 pts.

### Trader sanity, every l4 / l5 number against the raw record at the read's own second

| read | fut (view / book) | spot (chain) | basis_ix / now | zone OI raw → face | range hi − lo / EM | push bar (5-min fut) |
|---|---|---|---|---|---|---|
| 21 Oct 10:30:30 | 22,976.0 / 22,981.1 | 22,956.45 | 22.0 / 24.6 | 22900 PE 7,009,925 → 70.1L ✓ | 23,119.25 − 22,925.5 = 193.8 / 192.3 = 1.01 ✓ | none since entry ✓ |
| 21 Oct 11:18:30 | 22,968.6 / 22,968.6 | 22,946.45 | 25.9 / 22.1 | 7,451,275 → 74.5L ✓ | 193.8 / 192.3 = 1.01 ✓ | none ✓ |
| 21 Oct 11:21:30 | 22,932.1 / 22,938.0 | 22,913.95 | 26.6 / 24.0 | 7,066,735 → 70.7L ✓ | 221.7 / 192.3 = 1.15 ✓ | 11:15 o 22,978.9 c 22,943.4 Δ −290 ✓ |
| 21 Oct 12:34:30 | 22,783.4 / 22,783.3 | 22,768.1 | 17.6 / 15.2 | 22700 PE 6,549,335 → 65.5L ✓ | 413.8 / 192.3 = 2.15 ✓ | 12:20 o 22,753.7 c 22,731 Δ −344 ✓ |
| 21 Oct 13:05:30 | 22,766.2 / 22,766.2 | 22,745.75 | 19.0 / 20.5 | 7,345,000 → 73.5L ✓ | 2.15 ✓ | 12:20 ✓ |
| 30 Sep 10:30:12 | 22,878.7 / 22,878.7 | 22,755.05 | 122.5 / 123.7 | 22800 CE 8,358,090 → 83.6L ✓ | 94.5 / 171.5 = 0.55 ✓ | none ✓ |
| 30 Sep 11:16:12 | 22,784.5 / 22,784.5 | 22,673.0 | 112.5 / 111.5 | 22700 CE 9,900,735 → 99.0L ✓ | 99.8 / 171.5 = 0.58 ✓ | none ✓ |
| 30 Sep 12:46:12 | 22,899.0 / 22,899.0 | 22,778.6 | 108.3 / **120.4** | 22800 CE 8,305,245 → 83.1L ✓ | 121.9 / 171.5 = 0.71 ✓ | 12:35 o 22,879.8 c 22,886.2 Δ +306 ✓ |

- EM: 21 Oct 09:20:07 row, ATM 23050, CE 178.85 + PE 165.10 = 343.95 / 0.8 / √5 (21, 22, 23, 26, 27 Oct) = 192.3 [I]. 30 Sep
  09:20:00, ATM 22700, 185.95 + 120.85 = 306.8 / 0.8 / √5 (to 6 Oct; 2 Oct holiday not removed) = 171.5 [I]. 21 Oct range at her
  entry = 0.77 EM, as Fable measured.
- Fuel at entry, raw: 21 Oct 120.3 + 35.3 + 57.5 = 213.0 L → 12:34 113.9 L; 30 Sep 94.0 + 47.4 + 87.4 = 228.8 L → 12:46 196.1 L ✓.
- f / s tags present on every level. **Watch:** the zone's f is K + the engine's 15-min basis. On 30 Sep (day 1 of the Oct
  contract) that basis was 108 while the live basis was 120: "9 pts" on the fut frame is 21 pts on spot. The `at zone` test uses
  spot (21 ≤ 50), so it is right; the printed f pts inherit the basis median.
- The engine view's fut lags the book by ≤ 6 pts at some reads (10:30, 11:21) — the engine's own number, already l1's in A52.
- Seller check (her 5 Oct SELL 22650 PE, replayed to 14:00): `premium 126 = 94 intrinsic + 31 TV · theta ~₹1.3/hr [I] · at zone ≈
  ₹95 [I] · 10 min: prem -72, fut +88`; din range 1.27 EM (Fable: 1.27); intrinsic 94 matches his ~94.

### Panel shots (light, `orderflow-desk/docs/v2-shots/v210/`, index `index.json`, before = v2.9 `.baseline/v29-dist-v2`)

| frame | v2.9 | v2.10 |
|---|---|---|
| 21 Oct 11:18 | WARN, `+0.7R` | WARN, `+35 pts`, l4 `push ▼ abhi nahi · ulta push: none · din range 1.01 EM`, l5 at 22900 PE 74.5L |
| 21 Oct 11:21 | HOLD | HOLD, l5 with `EFFORT 0.44× sasta @ naya low` |
| 30 Sep 12:46 | EXIT | EXIT, l4 `push ▲ 12:35 (6 min) · ulta push ▼ 11:15 @ 22,802f · din range 0.71 EM`, l5 22800 CE 83.1L |

The block grows 105 → 177 px at the panel's 359 px (l4, l5 wrap to two lines each). The 30 Sep chart is `test/session-2026-09-30.ofd.json`
(new, `node test/tape2session.mjs 2026-09-30`). Frames: scratch `frames_v210.py` (the recorded frame + v2 keys, `rank_ref` never
written) — command `OFD_PROBE=1 OFD_BUNDLES=.baseline/v29-dist-v2,dist-v2 OFD_LABELS=v2.9,v2.10 node test/replay-shots.mjs <frames> docs/v2-shots/v210`.

## 5. Tests

- `python -m pytest -q`: **1940 passed, 1 skipped, 1 failed** (1942 collected; +2 leak-guard params for `MAP_DIR` / `VOICE_DIR`) = the known flaky `test_v2feed::test_serve_caches_full_and_answers_delta`
  (A49; 8/8 alone). New: `test_trademap.py` 8 (push / ulta / ref nahi, range vs EM 120 / 0.8 / √3, wall ½-largest nearest, survivors
  vs mirrors, fuel pinned + None, levels + seller line, server strip/merge/log write-once, voice_path 15:40 + cache);
  `test_voice.py` +l1 pts +15:20 wording; `test_validate3.py` +PULLBACK / NEXT WALL.
- Extension (`dist-v2` 0.5.10): engine 116, fit 46, shell 139, overlay 39, **panel 99 (+4)**, decoder 21 — all green. Against the
  v2.9 panel (`OFD_PANEL=.baseline/pre-v210-2026-10-24/src/shell/panel.js`): 97 pass, 2 FAIL (the l4/l5 render and the detail lines;
  the other two are guards).
- `tsc --noEmit` clean.

## 6. Open (named, not built)

- **The chart still draws `T1 22,926f | ≈22,900s | −59 pts`** (extension `main.js` trade lines) — the countdown-to-target Fable A1
  warned against. The spec renamed Validate's T1 only. A one-word rename + dropping the pts countdown is her call.
- `SHADOW_DIR` is not in the test leak guard (pre-existing).
- No score of the map's forward log exists (by design); `map_<day>.jsonl` starts at her restart.
- Rollback: extension `.baseline/v29-dist-v2` or `.baseline/pre-v210-2026-10-24/`; TapeMap: the diff is display-only — revert
  `trademap.py`, `voice_path.py` and the hunks named in §1.

## 7. Review fixes (24 Oct, after the build, before her restart)

| fix | where | why |
|---|---|---|
| l5's pts = spot → strike, not fut → K + basis | `trademap.py` `read` (pts), `test_trademap.py` (110 pts) | the wall is a spot level; the engine's 15-min basis lagged 12 pts on 30 Sep, so "9 pts" was 21 on spot. Proof minutes now: 21 Oct 10:30 56 · 11:18 46 · 11:21 14 · 12:34 68 · 13:05 46; 30 Sep 10:30 45 · 11:16 27 · 12:46 21 (= spot 22,778.6 → 22,800 ✓) |
| the chart's in-trade T1 → **PULLBACK**, at the block's l5 level | extension `src/shell/main.js` (trade lines, `VZ` = `voice.map.zone.fut`) | §6's open item: the chart said `T1 … −59 pts`, the target countdown Fable A1 warns against, and a second number beside l5. Decided as a trader (standing rule); the plan's pre-trade `T1 VWAP` (§1i's registered target) is untouched |
| `SHADOW_DIR` in the leak guard | `conftest.py`, `server._isolate_mock_writers` | a toy trade (`NIFTY-23000PE-long-091530`) had written `data/hold/shadow_2026-09-30.jsonl` on 23 Oct 23:12; moved (not deleted) to `data/hold/_test_leak/`. After the full run: no `map_*` / `shadow_*` / `data/voice` written |

Re-verified: pytest **1941 passed, 1 skipped** (A49 flaky deselected) · extension engine 116, fit 46, shell 139, overlay 39, panel 99, decoder 21 · `dist-v2` rebuilt 0.5.10 · shots in `docs/v2-shots/v210/` re-rendered from the fixed replay (21 Oct 11:21: `PULLBACK 22,927f | ≈22,900s`, l5 `(14 pts) · EFFORT 0.44× sasta @ naya low`).

Known, not fixed: the chart's own pts on a line are fut-native (its price vs K + basis_ix), so on a lagging-basis day the chart's `−17 pts` and l5's `14 pts` differ by the basis error. One live basis everywhere is its own task (memory: tag levels spot or fut, "measure the basis live").

## 8. Her two open questions, decided as a trader (24 Oct, her words: "just do which ever you think as as a trader best for me")

| | decision | where | proof |
|---|---|---|---|
| A61 BADA PRINT at the zone | **built**. Fable's and my "the server has no prints" was wrong: `data/decoder/decoder_<day>.jsonl` holds her decoder's E1 since 5 Oct (GoCharting tab open) | `trademap.bada`, `read(..., prints, gc_t)`, `server._hold2_run` (`decoder_log.read_events`, the tape's last bar), `voice_path.run`; REV → trademap-2 (cached replays recompute) | 21 Oct replay to 13:47: 13:45 `pullback zone 22,722f / 22,700s (1 pts) · 22700 PE 78.5L · BADA BUYER 625 lots @22,727f 13:40` (the bar closed 13:45, never earlier); 13:46 the wall broke, zone → 22600 PE |
| A62 the gave-up alarms | **W-BLEED alone is no longer a WARN**; its number is `voice.gauge`, first in [detail]. HOLD v2's front gave up and GAVE UP (both need price against her) stay | `voice.py` `_triggers` / `ladder`, `trademap.into` | 30 Sep 10:46 detail `W-BLEED 22800 PE −18.4% off 66.5L peak · 15 upd [M] · gauge, not a give-up alone`, state EXIT as before; 21 Oct state sequence unchanged |

Tests: pytest 1942 passed, 1 skipped (A49 deselected), no rows leaked; `test_voice.py` (gauge, price-with-her = HOLD), `test_trademap.py` +1 (BADA since entry / bar closed / within a step / shown / tab nahi; the gauge line). The faces render `l5` and `detail` verbatim: no extension rebuild needed.

## 9. A60 one basis, and the floating window (24 Oct, her "do A60 … nothing is left")

- **A60**: every f/s on every face already came from one number, `fold.State.bas_ix` (`fold_live.basis` → the frame,
  `view.units.basis_ix` → the voice / map / HOLD v2 spot). Its 15-min median lagged; measured on 6 days against the ±2-min local
  median of time-aligned fut − index pairs: 15 min p50 2 / p90 5–6 / max 16 pts, 3 min p50 1 / p90 3 / max 8 [M]. `fold.BIX_MS`
  = 3 min (display only; `bas`, the forward basis behind G / zone reads / premiums, unchanged). 30 Sep 10:30 121.1 vs 121.3 local,
  11:16 111.0 vs 111.2; in a fast push the future leads the index and a 3–6 pt gap remains for a minute.
- **A63**: the floating window is `ui-v2/src/pro/Float.tsx` (App.tsx), not `hold/HoldWindow.tsx` (not mounted). It now shows the
  voice block with l4 / l5 on top, the map's detail then the DESK's face under [detail ▸], the voice's word + reason when
  collapsed, the voice's state in the tab title; l1 wraps under the float's 171-px buttons (`hold.css`). Rendered against a
  mock API (21 Oct 11:21 HOLD; 13:45 EXIT with `BADA BUYER 625 lots @22,727f 13:40`). `tsc` clean; pytest 1942 passed.
