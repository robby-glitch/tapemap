# 10. The cross-index read and LOOK HERE: build report (SHADOW)

**Status:** SHADOW. The sheet is unsigned, and nothing replaces the old LOOK HERE chip until she signs.
**Built:** 2026-09-30, to `9-cross-index-design.md` (with the supervisor's correction).
**No outcome is scored anywhere.** There is no hit rate and no "next leg". Every count below is a count of the read's own behaviour.

## 1. What was built

| File | What |
|---|---|
| `xindex.py` | Pure. Built on `reader.py`'s leg rows, and never cuts a leg.<br>**The reads:**<br>• SYNC (directions, size in each index's own ruler, the odd one named, NIFTY/BANKNIFTY WHO);<br>• EXTREMES (at the latest push, TOOK / EQUAL / FAILED against each index's own previous extreme, giving CONFIRMED / DIVERGENT / BARABAR plus the level that ends a divergence);<br>• LEAD (minute stamps; "saath mein" within 1 minute; never "X leads");<br>• WALLS (option OI added within reach);<br>• POTENTIAL.<br>**LOOK HERE:** a count of 6 lines (zone · flow · WHO · walls · sync · extremes), awarded on her zone + 2 more or 4 without it, and for ≥ against + 2. It has hold, switch, a 2-bar cooldown and a session cap.<br>**The three state words** come with their start, confirm and kill levels. A word moves at once only on a named event (her zone's state or the reader's auction state changed); otherwise the same candidate must hold for 2 bars.<br>**Also:** one `SHEET`; `audit()`, the automatic misdescription check. |
| `test_xindex.py` | 11 tests:<br>• the sheet;<br>• determinism;<br>• no repaint (a prefix run equals the full run; a stepped bar never changes);<br>• each state with its levels;<br>• the event-or-2-bar word rule;<br>• the gating (zone + 2; 3 without the zone refused; 4 awarded; the margin);<br>• the cooldown and the cap;<br>• the thin SENSEX;<br>• CAN'T CHECK on holes, a missing zone and missing flow, the 15:15 freeze and before 09:30;<br>• extremes confirmed and divergent, SENSEX as a witness only;<br>• walls;<br>• a clean audit. |
| `tools/xindex_replay.py` | Replays each recorded day as-of: reader engines stepped minute by minute, her zone from `trigger_log` (never a reconstruction), and chain walls. It writes `docs/reader/replays/xindex_<day>.txt`. |

**Thin tape:**
- SENSEX flow and WHO never vote ("patla").
- SENSEX is a witness in SYNC and EXTREMES, never the decider.
- Without her zone, SENSEX cannot reach the bar: the most lines it can check is 4.

**Cash auction:** bars after 15:15 read CAN'T CHECK, and LOOK HERE is released.

## 2. Replay sources and what they cannot show

- **Legs:** `reader.py` on the same inputs as `tools/reader_replay.py`. The NIFTY exchange candle exists for 29 Sep only; every other minute is book-built.
- **Her zone:** `trigger_log` arms and triggers (rule "zone" only).
  - After a trigger, the trade's exit is not in the log, so the zone line reads **CAN'T CHECK** until that side arms again. Live, `/api/data`'s `zone_state` carries IN_TRADE exactly. The replay therefore shows fewer zone-backed awards after triggers than live would.
  - BANKNIFTY has no zone rows on 28 and 29 Sep. 29 Sep is **WAITING, verified live** (supervisor). 28 Sep is **CAN'T CHECK: not verified.**
- **Walls:** the chain now vs 15 minutes before. On 29 Sep the NIFTY and BANKNIFTY chains are 0DTE, labelled "expiry din".

## 3. Pre-registered bars (stated in `9-cross-index-design.md` §4.4 before this build) and the results

| Day | Awards (≤ 10) | Changes (≤ 16) | Switches | Flips inside 6 min (0) | Word changes N / B / S (≤ 12 each) | Bars with LOOK HERE | Audit violations (0) |
|---|---|---|---|---|---|---|---|
| 22 Sep | 5 | 10 | 0 | 0 | **21** / **14** / **19** | 41 / 125 | 0 |
| 23 Sep | 2 | 4 | 0 | 0 | 11 / 11 / 9 | 6 / 125 | 0 |
| 24 Sep | 3 | 7 | 1 | 0 | **21** / 9 / **13** | 10 / 125 | 0 |
| 25 Sep | 3 | 6 | 0 | 0 | 11 / 9 / **13** | 18 / 125 | 0 |
| 28 Sep | 3 | 6 | 0 | 0 | 12 / 7 / 10 | 15 / 125 | 0 |
| 29 Sep | 3 | 6 | 0 | 0 | 12 / **17** / **20** | 16 / 125 | 0 |

**What these results mean:**
- **LOOK HERE churn is met on all 6 days:** 2–5 awards, 4–10 changes and 0 flips.
- **The automatic misdescription audit is met on all 6 days** (0 violations). It re-derives every count from its lines, and checks:
  - every CAN'T CHECK has a reason;
  - the thin tape never votes flow or WHO;
  - running words carry a start level;
  - LOOK HERE only between 09:30 and 15:15;
  - no % or probability words in anything the face would say.
- **The state-word bar (≤ 12 per index) is missed on 4 of 6 days** (bold cells). It is **kept as a miss, not re-tuned.** The named events that pass at once include every reader auction change: BANKNIFTY had 14 on 29 Sep by the reader's own count, and each re-arm of her zone is another. The 2-bar rule removed about half the raw changes (29 Sep before the rule: 26 / 55 / 35).
- **The owed decision:** whether the word should follow only her zone and the auction state (at most the reader's own churn). That is hers to sign; it was not tuned here.
- **Manual misdescription audit (owed in shadow):** 60 random reads a day, checked against the raw files by someone who did not write them. The bar is 0 contradictions of an [M] number.

## 4. What the replays say (description, not verdict)

- **29 Sep:**
  - NIFTY ▲ at 09:42: her d2 trigger · buyers pressing · BANKNIFTY with it. 1 line against: CE written at 22,650, expiry day.
  - NIFTY ▼ at 12:21: her u2 trigger · sellers pressing · BANKNIFTY with it. 1 against: PE written at 22,700.
  - NIFTY ▼ at 13:21, 4 of 5, inside the afternoon range: range break level 22,604.
  - **BANKNIFTY was never awarded**, since her zone had no setup there.
  - After 15:15, "cash auction".
- **Extremes notes** name divergences with the level that ends them. Example, 29 Sep 10:45: "BANKNIFTY ne naya high banaya, NIFTY ne nahi · khatam: NIFTY 22,643.1 ke upar".
- **Most of the day has no LOOK HERE** (6–41 of 125 bars): "koi saaf jagah nahi · best X n/m". That is by design. A line-up of her zone plus 2, or 4 lines, is not common.

## 5. Step 4: live, shadow (built on the coordinator's go)

| File | What |
|---|---|
| `xindex_live.py` | Runs on the reader thread's pass. Per 3-minute close it takes:<br>• the reader's snapshot **as of that close** (recorded by `reader_live` while it steps minutes, so a restart rebuilds the same snapshots);<br>• her zone machine's state for that bar (the server's own 3-minute payload; another session's payload, or a bar not served within 2 bars, is CAN'T CHECK);<br>• the chain file for the walls.<br>It appends each new bar once to `data/xindex/xindex_<day>.jsonl` and serves `read()`. |
| `reader_live.py` (2 surgical edits) | • Records a snapshot at each bar close while it steps minutes.<br>• Calls `xindex_live.tick` after its per-index loop, inside a try. A failure is served as "could not check — xindex failed: …" and costs the reader, fold and the feed nothing. |
| `server.py` (4 surgical edits) | • `import xindex_live`;<br>• `GET /api/xindex`, read-only;<br>• `_xindex_zone()`, the zone seam: `zone_state` / `zone_state_sell` plus the payload's session label;<br>• `xindex_live.DIR` in `_isolate_mock_writers`. |
| `conftest.py` | `xindex_live.DIR` → tmp. The leak guard covers it. |
| `test_xindex_live.py` | Each bar logged once; a restart repaints nothing; a stale zone payload is CAN'T CHECK; a failure costs the reader nothing. |
| `ui-v2/src/trade/legs.tsx` | A **"LOOK HERE · SHADOW"** block at the top of the existing "LEGS · shadow" panel. It is **off by default** with that toggle, and marked unsigned. It shows:<br>• the LOOK HERE line;<br>• per index: word, count and hover reasons;<br>• the sync, extremes and walls chips;<br>• today's changes.<br>It computes nothing. **The glance bar's old LOOK HERE chip is untouched.** |

**Not done here:** the server is not restarted. `/api/xindex` appears at her next start.

## 6. Known limits

1. **The index-candle engines** in the design (§3, cross-index price legs cut on the index itself) are **not built**: no index candle feed exists yet. SYNC and EXTREMES use the futures legs, with SENSEX weighted as thin.
2. **Compression** (`band_rotation`'s rank) is an optional input, not wired. POTENTIAL lists the zone, the range and the walls.
3. **Evaluated at 3-minute closes.** A live invalidation between closes (her stop) shows at the next close, at most 3 minutes later. Her zone machine is itself on 3-minute bars.
4. **Holidays** are not modelled, as elsewhere in the repo.
