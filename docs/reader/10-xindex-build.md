# 10. The cross-index read and LOOK HERE: build report (SHADOW)

**Status:** SHADOW. The sheet is unsigned, and nothing replaces the old LOOK HERE chip until she signs.
**Built:** 2026-09-30, to `9-cross-index-design.md` (with the supervisor's correction).
**No outcome is scored anywhere.** There is no hit rate and no "next leg". Every count below is a count of the read's own behaviour.

## 1. What was built

| File | What |
|---|---|
| `xindex.py` | Pure. Built on `reader.py`'s leg rows, and never cuts a leg.<br>**The reads:**<br>• SYNC (directions, size in each index's own ruler, the odd one named, NIFTY/BANKNIFTY WHO);<br>• EXTREMES (at the latest push, TOOK / EQUAL / FAILED against each index's own previous extreme, giving CONFIRMED / DIVERGENT / BARABAR plus the level that ends a divergence);<br>• LEAD (minute stamps; "saath mein" within 1 minute; never "X leads");<br>• WALLS (option OI added within reach);<br>• POTENTIAL.<br>**LOOK HERE:** a count of 6 lines (zone · flow · WHO · walls · sync · extremes), awarded on her zone + 2 more or 4 without it, and for ≥ against + 2. It has hold, switch, a 2-bar cooldown and a session cap.<br>**The three state words follow STRUCTURE ONLY** (trader's call, 2026-09-30). Each carries its start, confirm and kill levels:<br>• **ban sakta** = her zone ARMED, or a reader RANGE box pressed at an edge (the reader widened it there);<br>• **chal raha** = her zone TRIGGERED or IN_TRADE, or a reader BREAKOUT or TREND in force (kill = her stop, or the trend-break level);<br>• **ho gaya** = her zone's exit (stop or VWAP), the reader's trend broken, or a range after a trend or breakout.<br>Flow, OI, sync and extremes stay in the count and the why line. **They never flip the word.**<br>**Also:** one `SHEET`; `audit()`, the automatic misdescription check. |
| `test_xindex.py` | 12 tests:<br>• the sheet;<br>• determinism;<br>• no repaint (a prefix run equals the full run; a stepped bar never changes);<br>• each state from structure, with its levels;<br>• ho gaya and ban sakta from structure events (trend broken, range after a trend, box widened, her trade closed);<br>• **a flow flip alone cannot change the word** (flow, WHO, walls and peers flip for 8 bars, and the word holds);<br>• the gating (zone + 2; 3 without the zone refused; 4 awarded; the margin);<br>• the cooldown and the cap;<br>• the thin SENSEX;<br>• CAN'T CHECK on holes, a missing zone and missing flow, the 15:15 freeze and before 09:30;<br>• extremes confirmed and divergent, SENSEX as a witness only;<br>• walls;<br>• a clean audit. |
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
  - BANKNIFTY has no zone rows on 28 and 29 Sep. Both are **WAITING, verified** by the supervisor (29 Sep on the served bars; 28 Sep on REST candles, with a NIFTY control that reproduces its log exactly).
- **Walls:** the chain now vs 15 minutes before. On 29 Sep the NIFTY and BANKNIFTY chains are 0DTE, labelled "expiry din".

## 3. Pre-registered bars (stated in `9-cross-index-design.md` §4.4 before this build) and the results

| Day | Awards (≤ 10) | Changes (≤ 16) | Switches | Flips inside 6 min (0) | Word changes N / B / S (≤ 12 each) | Bars with LOOK HERE | Audit violations (0) |
|---|---|---|---|---|---|---|---|
| 22 Sep | 2 | 4 | 0 | 0 | 9 / 6 / 6 | 16 / 125 | 0 |
| 23 Sep | 0 | 0 | 0 | 0 | 7 / 7 / 4 | 0 / 125 | 0 |
| 24 Sep | 3 | 7 | 1 | 0 | **14** / 5 / **14** | 10 / 125 | 0 |
| 25 Sep | 3 | 6 | 0 | 0 | 7 / 7 / 11 | 27 / 125 | 0 |
| 28 Sep | 2 | 4 | 0 | 0 | 4 / 7 / 8 | 11 / 125 | 0 |
| 29 Sep | 4 | 8 | 0 | 0 | 4 / **16** / 7 | 21 / 125 | 0 |

A data hole or the 15:15 freeze reads CAN'T CHECK. That is "could not check", not a word change, so the count compares only the words it could read.

**What these results mean:**
- **LOOK HERE churn is met on all 6 days:** 0–4 awards, 0–8 changes and 0 flips.
- **The automatic misdescription audit is met on all 6 days** (0 violations). It re-derives every count from its lines, and checks:
  - every CAN'T CHECK has a reason;
  - the thin tape never votes flow or WHO;
  - "ban sakta" on a range carries its start level, and "chal raha" carries a kill level or says why it has none;
  - LOOK HERE only between 09:30 and 15:15;
  - no % or probability words in anything the face would say.
- **The state word, now structure only: the maximum is 16, and 15 of 18 index-days are at or under 12.** Before the rule the maximum was 21.
- **The three misses are the structure's own churn, not the word's.** They are kept as misses, not re-tuned:
  - **BANKNIFTY 29 Sep (16):** the reader's auction went RANGE → BREAKOUT seven times on that expiry day. By its own count it had 14 auction changes, over its own ≤ 12 bar.
  - **NIFTY and SENSEX 24 Sep (14 each):** her zone machine armed and triggered seven times on each index that day.
  - A word that follows structure cannot be quieter than the structure. The levers are the structure itself (the reader's BREAKOUT rule, her zone's re-arm), and both are hers to sign.
- **Manual misdescription audit (owed in shadow):** 60 random reads a day, checked against the raw files by someone who did not write them. The bar is 0 contradictions of an [M] number.

## 4. What the replays say (description, not verdict)

- **29 Sep** (structure-only words):
  - **09:42 NIFTY ▲, 3 of 6:** her d2 trigger · buyers pressing · BANKNIFTY with it. 1 against: CE written at 22,650, expiry day.
  - **11:12 BANKNIFTY ▲, 5 of 6:** the reader's BREAKOUT (chal raha, start 53,991, kill 53,935) · sellers absorbed · new longs · PE written at 54,000 · NIFTY with it · "Teeno ne naya high banaya".
  - **12:21 NIFTY ▼, 3 of 6:** her u2 trigger · sellers pressing · BANKNIFTY with it. 1 against: PE written at 22,700.
  - **13:21 NIFTY ▼, 4 of 5.** Its word still reads "her trade is on": in the replay the trade's exit is not logged, so her last known state holds. Live, her machine's exit gives "ho gaya".
  - **BANKNIFTY's word** went RANGE → BREAKOUT seven times (16 changes), each one a reader auction event.
  - After 15:15, "cash auction".
- **Extremes notes** name divergences with the level that ends them. Example, 29 Sep 10:45: "BANKNIFTY ne naya high banaya, NIFTY ne nahi · khatam: NIFTY 22,643.1 ke upar".
- **Most of the day has no LOOK HERE** (0–27 of 125 bars): "koi saaf jagah nahi · best X n/m". That is by design. A line-up of her zone plus 2, or 4 lines, is not common.

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
