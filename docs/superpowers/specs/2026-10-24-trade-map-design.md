# TRADE MAP in the one voice — design (2026-10-24, Mary: "build it")

Sources: NOTEPAD A53–A59 · `docs/trade-map/FABLE-CRITIQUE-2026-10-24.md` (Fable's trader critique, measured on her 10
held October trades, in-sample) · the one-voice block (A52, `voice.py`, extension v2.9 0.5.9).

**What it is.** The one-voice block stays the face: state · one stop · one reason. Two DESCRIPTION lines join it (the
push, the day's range used, the pullback zone ahead), and a `[detail ▸]` list (fuel pinned at entry, levels on the way,
R, the seller's premium path). Computed once in TapeMap, rendered verbatim on the three faces (GoCharting panel, hold
window, Validate). **Display only. No rule changes, no new WARN / EXIT source, no rate, no prediction, no question.**

## 1. The block (default face)

```
▼ 23000 PE · 73 min · +70 pts (₹+37)                                   l1  (R → detail)
HOLD   stop 22,992f / 22,964s ≈ ₹174 · BE lock at 22,906f              l2  unchanged
why: CE 23000 writers building · flow saath                            l3  unchanged
push ▼ 11:52 (12 min) · ulta push: none · din range 0.77 EM            l4  NEW
pullback zone 22,916f / 22,888s (9 pts) · 22900 PE 74.8L               l5  NEW
[detail ▸]
```

**l1.** `+N pts` = d × (fut − E), futures points [M]; replaces `+xR`. `r_now` stays in the fields and in detail.

**l4: PUSH · ULTA PUSH · RANGE.**
- `push ▼ HH:MM (N min)` = the latest PUSH of her direction (`hold2.pushes(bars5, refs)`: the registered §1m
  definition, unchanged) whose bar CLOSED after her entry minute and by now. HH:MM = the bar's open; N = minutes since
  its close. None yet: `push ▼ abhi nahi`.
- `ulta push ▲ HH:MM @ 22,840f` = the latest PUSH of the OPPOSITE direction closing after entry (origin, fut), else
  `ulta push: none`. No push reference tables: `push ? ref nahi` (`hold2.NO_REF`), which means could not check; never print
  "none" then.
- `din range X.XX EM` = (session spot high − session spot low, 09:15 → now) / the day's 1σ EM. EM is a line-for-line port of
  `ui-v2/public/validate2/engine.js` `emOf`: the first chain row in 09:20–09:30, its ATM straddle / 0.8 / √N, N = weekdays
  from today to expiry, both counted, holidays not removed [I]. No such row: `din range ? — no 09:20 straddle`.
- **Why these:** the push is her own pullback-vs-invalidation grammar (AAKHRI BADA PUSH). Range used separated her four late
  losers (≥ 0.98 EM) from her winners (0.29–0.77) where the signed σ did not. Collinear with the clock: a DESCRIPTION,
  never a gate (Fable A4).

**l5: the PULLBACK ZONE (was "T1").**
- The wall ahead NOW: a port of `engine.js` `wallNearest` on the paying leg (d > 0: CE above spot; d < 0: PE below spot) =
  the nearest strike beyond spot whose OI ≥ ½ of that side's largest in the chain window. Show it as fut = K + basis, spot = K,
  plus the unsigned pts from fut now, plus `{K} {CE|PE} {OI}L` [M].
- At the zone (spot within one strike step): append the reads AT the zone, **survivors only**:
  - d < 0 and EFFORT ≤ 0.5× at a fresh LOW: `· EFFORT 0.44× sasta @ naya low`.
  - d > 0 and EFFORT ≥ 2× at a fresh HIGH: `· EFFORT 2.3× mehenga @ naya high`.
  - Mirrors, "read nahi" or before 09:56: print NOTHING. There is no default-tighten.
  - Source: the DECODE block's `effort` dict (`data/decode/decode_<day>.jsonl` via `holdshadow.dec_rows` / `_dec_at`, which
    is `effort.read`'s dict). Reuse it; never recompute.
- No wall ahead: `pullback zone: koi deewar nahi (checked ±8)`.
- A sale reads the same line in her sale's direction d.
- **Why "pullback zone", not "target":** her first leg ended within 15 pts of T1 on 5 of 8 rows. A trader reads that as
  where the pullback comes. A countdown to it plus "tighten" is the exit-early leak itself (Fable A1). The stop stays
  the trail.

## 2. `[detail ▸]` (≤ 4 lines, under the existing detail toggle, first)

- **fuel**: `fuel 23050/23100/23150 PE · entry 104L → now 75L · peak 112L 09:55`.
  - A FIXED set pinned at her entry minute: the losing leg's (d < 0: PE; d > 0: CE) three largest-OI strikes at that
    minute among those ITM or within one step of ATM. Per strike in the tooltip.
  - If any strike reads None now: `fuel: could not check — 23100 PE not in the snapshot`. Never sum a missing value as 0.
  - OI [M], "trapped" [I]: OI has no side or vintage. NO "burning / spent" words (Fable A2: the windowed sum was flat
    218–260 L all day on 21 Oct; the fixed set was half covered 118 pts before the move's end).
- **levels**: PDH / PDL, IB hi/lo (09:15–10:15 spot), HOD / LOD so far. Show those between spot and 2 EM in her direction,
  nearest first. Each is spot-tagged with fut beside it. Reuse what the server already holds (the frame's levels /
  `levels.fetch_daily`'s cache, read.py/decode.py facts). NEVER a new broker call; absent → `PD ? — not fetched`.
- **R**: `R +1.7 · BE lock at 2R` (the moved-out header number).
- **seller only**: `premium 131 = 94 intrinsic + 37 TV · theta ~₹X/hr [I] · at zone ≈ ₹Y [I] · 10 min: prem +11, fut +2`.
  - Premium now [M] from the chain LTP.
  - Intrinsic from spot.
  - At-zone via the engine's delta-linear interpolation (`fold_live.prem_at` / engine.js `premAt`) [I].
  - Theta = `gamma.bs_price` now minus 1 hour later at the chain's implied vol [I].
  - The 10-min deltas are a description (Fable A6: an ATM sale is a premium position; points cannot tell DTE 3 from
    DTE 0).

## 3. Where it is computed (one brain)

- **New pure module `trademap.py`**: `read(tr, view, chain_rows, bars5, refs, dec, levels, now_m) -> {ok, l4, l5,
  detail[], fields…, tag "I", why}`. No I/O, no clock. Pushes come from `hold2.pushes`; **hold2.py is untouched**.
- **Called in `server._hold2_run`.** It is already off the request thread, runs at most once a minute and holds chain_rows,
  bars5, refs and dec. It is stored as `out["map"]`.
- **`server._in_trade`** strips `map` from the `hold2` block, as it does `shadow`, and merges `l4`, `l5`, `detail` and
  `map` (fields) into the voice dict.
- **Map not ready or failed:** no l4 / l5, `map_why = "could not check — …"`, and the faces show the three lines alone.
  Fail-soft, as the voice is.
- **Forward log** `data/hold/map_<day>.jsonl`: write-once per (trade id, event). Events:
  - `ulta_push`: t, origin, fut;
  - `zone`: the first time within one step of each wall ahead, with k, leg, fut, OI, the effort read or null, and pts.
  
  Anytime-start: read existing rows before the first write, like `_shadow_log`. No outcomes are written; scoring is later
  and separate.

## 4. Faces (light mode, existing styles)

- **Extension `src/shell/panel.js` `voiceBlock`**: `v4` and `v5` spans under `v3` (v3's style). Detail lines first in the
  `vOpen` detail. Rebuild `dist-v2` (`node build.mjs --out dist-v2`) and bump to **0.5.10**. All suites green.
- **`ui-v2/src/hold/HoldWindow.tsx`**: `v4` / `v5` divs; detail lines in its detail area.
- **`ui-v2/public/validate2/app.js`**: `v4` / `v5` in `voiceEl`; detail lines on top of the `S.vOpen` view.

## 5. Validate fixes in the same build

- **A54**: `engine.js` `levels()`: rename T1 to `PULLBACK` and T2 to `NEXT WALL`, and drop `cond`. Update every consumer of
  the names (app.js, tests, tools).
- **A55**: `app.js` "to stop" cells: when the voice is on, use `vc.stop_f` / `vc.stop_s`, and the tooltip names
  `vc.stop_src`. One stop on the screen.
- **A56: the voice in replay.**
  - Refactor `tools/voice_replay.py`'s `run` into an importable module used by the tool and by a new
    `GET /api/voice_path?id=&day=`.
  - The endpoint returns `[{t, voice}]` (with the map lines) for a marked trade of a PAST day, or of today after 15:40. It
    is computed off-thread once and cached at `data/voice/path_<day>_<id>.json`.
  - Today's trade before 15:40 gets `could not check — replay of today's trade after 15:40`. Never load the live server in
    market hours.
  - Validate's replay uses the latest minute ≤ T.

## 6. Also

- `voice.py` 15:20 EXIT reason: `15:20 — din khatam (HOLD v2)` → `15:20 — spot 15:15 se frozen (HOLD v2)`. The time is
  unchanged (§1m); only the reason is honest (CAS freeze).

## 7. Named, NOT in this build

- **Rule changes:**
  - fold.py rev 6, `hold2` exit logic (§1m frozen), VALIDATE rev 3 reads;
  - the voice's states and triggers;
  - any "push against" WARN. It is logged, not a state.
- **R6, one "gave up" definition** (V2GU vs GAVEUP vs BLEED, 10 % vs 15 %): it changes signed reads → her word.
- **BADA PRINT at the zone: deferred.**
  - Fable's data claim was wrong: `data/tape/ofd_marks_*` holds initiative / exhaustion / absorption / trap / vacuum /
    climax, and no E1 prints.
  - It needs a port of the decoder E1 rule onto the ux ladder bars: its own task.
  - **CORRECTION 24 Oct: the BADA PRINTs ARE in TapeMap — `data/decoder/decoder_<day>.jsonl` (decoder_log.read_events, kind E1 'BADA PRINT', her extension's own rule, logged since 5 Oct while the GoCharting tab is open; e.g. 21 Oct 13:40 BUYER 625 lots @22,727, 22 Oct 12:55 SELLER 607 @22,742). Fable and I both looked only in data/tape/ofd_marks_*. Building it is small.** (NOTEPAD A61)
- **Fable's own practice** ("BE lock only after a 2nd push", "book a third at the first wall"): method changes, not
  proposed.
- **Never printed:** signed σ, "of ~2σ", "most moves stopped here", "aur girega?", "T2 in play", "toota to fansa",
  fuel "burning / spent", default-tighten.

## 8. Tests and proofs

- **`test_voice.py`**: l1 in pts; the 15:20 wording.
- **`test_trademap.py`**, one check per rule:
  - push / ulta push: direction, closed after entry, "ref nahi" ≠ none;
  - the range-used arithmetic: synthetic chain, EM = 120 / 0.8 / √3 as in test_validate3;
  - the wall-ahead port: ½ of the largest, nearest;
  - zone reads: survivors print, mirrors print nothing;
  - fuel: fixed at entry; a None strike → could not check, never 0.
- **Server test**: `map` stripped from hold2 and merged into voice; the voice still works with no map.
- **Extension test**: l4 / l5 render when present and nothing when absent.
- **Full pytest and every extension suite.**
- **Replay proofs** through the refactored replay with the map, l1–l5 at:
  - 21 Oct `NIFTY-23000PE-long-100730`: 10:30, 11:18, 12:34, 13:05;
  - 30 Sep `NIFTY-22750CE-long-101012`: 10:30, 11:16, 12:46.
  
  Table in the build report. Light-mode panel shots at 21 Oct 11:18 and 30 Sep 12:46 in `docs/v2-shots/v210/`.
- **Trader sanity:** every number on l4 / l5 at those minutes checked against raw data (fut, spot, OI lakhs, EM, basis),
  with f/s tags present.
