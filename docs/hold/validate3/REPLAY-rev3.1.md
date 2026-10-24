# SENSEX reads NIFTY's order flow: flags OFF vs ON on her trades (2026-10-24/25, after the close; DRAFT, not signed; descriptive, in-sample, no hit rates)

The rule text is `docs/hold/SENSEX-NIFTY-FLOW-PREREG.md` (sha256 `552d6927b6bee8d2cb7ea0dbf3e39d70aa5293f69fe22821e8c53d1db0ca73c9`). It was hashed before this replay ran and is unchanged. **It is not signed.** The flags ship OFF (`sensex_flow.ON = False`, `engine.js R31.ON = false`). This replay turns them on inside its own process only.

Everything below is **in-sample**. The 22 Oct row was known when FRESH-AFTER's 10 min / 1.5 steps were chosen (§2), and it can never count for this rule. Rows are described, never scored.

## Method

- **(a) Validate.** Run `python -I -X utf8 docs/hold/validate3/replay.py OUT_DIR --r31`.
  - The entries are the 51 of `REPLAY.md`. Each runs through the same engine twice: rev 3 (`R31.ON` false) and rev 3.1 (true).
  - Both runs get the same day payload (`v2feed.serve`) and the same DECODE blocks for all three indices, readable at the entry: close + 60 s ≤ entry, from `server._decode_all`.
  - Each entry is a fresh press at its entry second.
- **(b) The one voice, HOLD v2 and the trade map.** Run `python -I -X utf8 docs/hold/validate3/replay31_voice.py OUT.json`. It calls `voice_path.run`, the module behind `GET /api/voice_path`, twice per trade.
  - **The trades:**
    - the 9 SENSEX trades of 1 Oct, verbatim from `data/day_state/day_2026-10-01.json` (imports from her tradebook, no thesis invalidation);
    - 22 Oct 13:00, rebuilt as in `tools/voice_replay.py` (73400 CE, out 13:25, premium from the chain).
  - **The window:** each trade runs from her entry to her exit + 15 min. Rows after her exit are labelled.
  - **With ON, voice_path also runs the all-day NIFTY flat engine,** `fold.State(None)`, fed minute by minute. Its flat FLOW row at the same second is mapped to her direction (§1.3), and NIFTY's pushes are translated onto SENSEX's 5-min bars (§1.2).
  - Frames are read at the record's own second, `hh:mm:38` on 22 Oct, everything fed before it.
- **(c) The 22 Oct sanity check.** Each NIFTY push of the day is set beside the SENSEX bar it was translated onto, and beside the raw SENSEX 1-min bar (`data/backtest/SENSEX/fut_2026-10-22.json`). The NIFTY flow chip is set beside the NIFTY engine's own fights.

**OFF is today, byte for byte.** It was checked three ways:
1. The rev 3 column below equals `REPLAY.md`'s rev 3 column on all 51 entries.
2. `tools/voice_replay.py`'s JSON (21 Oct, 22 Oct, 30 Sep) is identical to a capture made before any edit.
3. The 9 SENSEX paths of 1 Oct are identical to a pre-edit capture, compared with `cmp`.

The tests prove the amendment's functions are never entered while OFF (`test_sensex_flow.py`).

## (a) Validate: rev 3 vs rev 3.1, all 51 entries

| entry | trade | rev 3 checks (1–10) | rev 3 word | rev 3.1 checks (1–10) | rev 3.1 word |
|---|---|---|---|---|---|
| 10-22 13:00 | SENSEX 73400 CE BUY @191 | `W · W · W c p W A W` | **WAIT** 5w 1a 2n 1c /9 | `W · W · W W p W A W` | **WAIT** 6w 1a 2n 0c /9 |
| 10-21 10:07 | NIFTY 23000 PE BUY @174.85 | `W · W W · W p A W ·` | **WAIT** 5w 1a 3n 0c /9 | `W · W W · W p A W ·` | **WAIT** 5w 1a 3n 0c /9 |
| 10-06 09:35 | NIFTY 22600 CE SELL @65.8 | `W · A W – · p W W ·` | **WAIT** 4w 1a 3n 0c /8 | `W · A W – · p W W ·` | **WAIT** 4w 1a 3n 0c /8 |
| 10-06 10:02 | NIFTY 22650 PE SELL @55.9 | `W · A · – A p · W ·` | **NO** 2w 2a 4n 0c /8 | `W · A · – A p · W ·` | **NO** 2w 2a 4n 0c /8 |
| 10-06 10:03 | NIFTY 22650 PE BUY @55 | `W · A · · W p · W ·` | **WAIT** 3w 1a 5n 0c /9 | `W · A · · W p · W ·` | **WAIT** 3w 1a 5n 0c /9 |
| 10-06 14:12 | NIFTY 22600 CE BUY @133 | `W W A · · · p W W ·` | **WAIT** 4w 1a 4n 0c /9 | `W W A · · · p W W ·` | **WAIT** 4w 1a 4n 0c /9 |
| 10-05 09:28 | NIFTY 22600 CE BUY @94.25 | `W · W W · W p c W ·` | **WAIT** 5w 0a 3n 1c /9 | `W · W W · W p c W ·` | **WAIT** 5w 0a 3n 1c /9 |
| 10-05 09:35 | NIFTY 22550 CE BUY @134.95 | `W · W W · · p · A ·` | **WAIT** 3w 1a 5n 0c /9 | `W · W W · · p · A ·` | **WAIT** 3w 1a 5n 0c /9 |
| 10-05 12:09 | NIFTY 22550 PE BUY @174.75 | `W · W · W · p W A W` | **WAIT** 5w 1a 3n 0c /9 | `W · W · W · p W A W` | **WAIT** 5w 1a 3n 0c /9 |
| 10-05 13:41 | NIFTY 22650 PE SELL @131.35 | `W · A · – · p · W W` | **WAIT** 3w 1a 4n 0c /8 | `W · A · – · p · W W` | **WAIT** 3w 1a 4n 0c /8 |
| 10-01 09:21 | NIFTY 22600 PE BUY @142.4 | `W · W W · c p c A ·` | **WAIT** 3w 1a 3n 2c /9 | `W · W W · c p c A ·` | **WAIT** 3w 1a 3n 2c /9 |
| 10-01 09:26 | NIFTY 22600 PE BUY @149.75 | `W · A W · c p c A ·` | **WAIT** 2w 2a 3n 2c /9 | `W · A W · c p c A ·` | **WAIT** 2w 2a 3n 2c /9 |
| 10-01 09:30 | SENSEX 72400 CE BUY @209.4 | `W · A W · c p c A ·` | **WAIT** 2w 2a 3n 2c /9 | `W · A W · · p c A ·` | **WAIT** 2w 2a 4n 1c /9 |
| 10-01 10:00 | SENSEX 72400 CE BUY @237.25 | `W · W · · c p W A ·` | **WAIT** 3w 1a 4n 1c /9 | `W · W · · · p W A ·` | **WAIT** 3w 1a 5n 0c /9 |
| 10-01 10:02 | SENSEX 72400 CE BUY @276.05 | `W · W W W c p W W W` | **GO** 7w 0a 1n 1c /9 | `W · W W W · p W W W` | **GO** 7w 0a 2n 0c /9 |
| 10-01 12:06 | SENSEX 72400 PE BUY @223.97 | `W · A W · c p · A ·` | **WAIT** 2w 2a 4n 1c /9 | `W · A W · W p · A ·` | **WAIT** 3w 2a 4n 0c /9 |
| 10-01 12:10 | SENSEX 72400 PE BUY @281.45 | `W · W · W c p W A W` | **WAIT** 5w 1a 2n 1c /9 | `W · W · W W p W A W` | **WAIT** 6w 1a 2n 0c /9 |
| 10-01 12:10 | SENSEX 72300 PE BUY @224.1 | `W · W · W c p W A W` | **WAIT** 5w 1a 2n 1c /9 | `W · W · W W p W A W` | **WAIT** 6w 1a 2n 0c /9 |
| 10-01 12:19 | SENSEX 72300 PE BUY @232 | `W · A · · c p · A ·` | **WAIT** 1w 2a 5n 1c /9 | `W · A · · W p · A ·` | **WAIT** 2w 2a 5n 0c /9 |
| 10-01 12:22 | SENSEX 72300 PE BUY @246.4 | `W · W · W c p W A W` | **WAIT** 5w 1a 2n 1c /9 | `W · W · W W p W A W` | **WAIT** 6w 1a 2n 0c /9 |
| 10-01 12:27 | SENSEX 72300 PE BUY @296.9 | `W · W W W c p · A W` | **WAIT** 5w 1a 2n 1c /9 | `W · W W W W p · A W` | **WAIT** 6w 1a 2n 0c /9 |
| 09-30 10:10 | NIFTY 22750 CE BUY @164.7 | `W · W · · · p W W ·` | **WAIT** 4w 0a 5n 0c /9 | `W · W · · · p W W ·` | **WAIT** 4w 0a 5n 0c /9 |
| 09-29 09:18 | NIFTY 22800 PE BUY @113.95 | `W · A W A c p c A A` | **NO** 2w 4a 1n 2c /9 | `W · A W A c p c A A` | **NO** 2w 4a 1n 2c /9 |
| 09-22 09:42 | NIFTY 23300 CE BUY @166.4 ‡ | `W · A W · · p c A ·` | **WAIT** 2w 2a 4n 1c /9 | `W · A W · · p c A ·` | **WAIT** 2w 2a 4n 1c /9 |
| 09-22 10:32 | NIFTY 23550 PE BUY @134.8 ‡ | `W · A · W W p · A W` | **WAIT** 4w 2a 3n 0c /9 | `W · A · W W p · A W` | **WAIT** 4w 2a 3n 0c /9 |
| 09-22 10:42 | NIFTY 23550 PE BUY @174.75 ‡ | `W W A W · W p W A ·` | **WAIT** 5w 2a 2n 0c /9 | `W W A W · W p W A ·` | **WAIT** 5w 2a 2n 0c /9 |
| 09-22 10:43 | NIFTY 23550 PE BUY @175.05 ‡ | `W W A · W W p W A W` | **WAIT** 6w 2a 1n 0c /9 | `W W A · W W p W A W` | **WAIT** 6w 2a 1n 0c /9 |
| 09-22 10:44 | NIFTY 23550 PE BUY @171.5 ‡ | `W W A · W W p W W W` | **WAIT** 7w 1a 1n 0c /9 | `W W A · W W p W W W` | **WAIT** 7w 1a 1n 0c /9 |
| 09-22 10:52 | NIFTY 23500 PE BUY @146.15 ‡ | `W W W · · · p A A ·` | **WAIT** 3w 2a 4n 0c /9 | `W W W · · · p A A ·` | **WAIT** 3w 2a 4n 0c /9 |
| 09-22 13:48 | NIFTY 23500 PE BUY @181.5 ‡ | `W W A · · · p W A ·` | **WAIT** 3w 2a 4n 0c /9 | `W W A · · · p W A ·` | **WAIT** 3w 2a 4n 0c /9 |
| 09-23 09:18 | NIFTY 23450 CE BUY @100 ‡ | `W · A W · c p c A ·` | **WAIT** 2w 2a 3n 2c /9 | `W · A W · c p c A ·` | **WAIT** 2w 2a 3n 2c /9 |
| 09-23 09:47 | NIFTY 23450 CE BUY @99.4 ‡ | `W · A · · · p · A ·` | **WAIT** 1w 2a 6n 0c /9 | `W · A · · · p · A ·` | **WAIT** 1w 2a 6n 0c /9 |
| 09-23 09:49 | NIFTY 23400 PE BUY @125 ‡ | `W · W · · · p · A ·` | **WAIT** 2w 1a 6n 0c /9 | `W · W · · · p · A ·` | **WAIT** 2w 1a 6n 0c /9 |
| 09-23 10:00 | NIFTY 23450 CE BUY @98.6 ‡ | `W · A · · · p · A ·` | **WAIT** 1w 2a 6n 0c /9 | `W · A · · · p · A ·` | **WAIT** 1w 2a 6n 0c /9 |
| 09-23 10:19 | NIFTY 23450 CE BUY @101.85 ‡ | `W · A · · · p · A ·` | **WAIT** 1w 2a 6n 0c /9 | `W · A · · · p · A ·` | **WAIT** 1w 2a 6n 0c /9 |
| 09-23 10:33 | NIFTY 23450 CE BUY @106.45 ‡ | `W · A · · · p W W ·` | **WAIT** 3w 1a 5n 0c /9 | `W · A · · · p W W ·` | **WAIT** 3w 1a 5n 0c /9 |
| 09-23 11:07 | NIFTY 23450 CE BUY @115.65 ‡ | `W · W · · · p W W ·` | **WAIT** 4w 0a 5n 0c /9 | `W · W · · · p W W ·` | **WAIT** 4w 0a 5n 0c /9 |
| 09-23 11:32 | SENSEX 74900 CE BUY @215.25 ‡ | `W W A · · c p W A ·` | **WAIT** 3w 2a 3n 1c /9 | `W W A · · · p W A ·` | **WAIT** 3w 2a 4n 0c /9 |
| 09-24 09:42 | SENSEX 74200 PE BUY @179.25 ‡ | `W · A · W c p W A W` | **WAIT** 4w 2a 2n 1c /9 | `W · A · W W p W A W` | **WAIT** 5w 2a 2n 0c /9 |
| 09-24 10:19 | SENSEX 74200 PE BUY @215.65 ‡ | `W · A · · c p W A W` | **WAIT** 3w 2a 3n 1c /9 | `W · A · · · p W A W` | **WAIT** 3w 2a 4n 0c /9 |
| 09-24 12:32 | SENSEX 74100 PE BUY @202.35 ‡ | `W · W · · c p W A ·` | **WAIT** 3w 1a 4n 1c /9 | `W · W · · · p W A ·` | **WAIT** 3w 1a 5n 0c /9 |
| 09-24 12:35 | SENSEX 74000 PE BUY @179.8 ‡ | `W · W · W c p · A W` | **WAIT** 4w 1a 3n 1c /9 | `W · W · W · p · A W` | **WAIT** 4w 1a 4n 0c /9 |
| 09-24 12:44 | SENSEX 74000 PE BUY @167.95 ‡ | `W · W · W c p W W W` | **GO** 6w 0a 2n 1c /9 | `W · W · W · p W W W` | **GO** 6w 0a 3n 0c /9 |
| 09-24 13:26 | SENSEX 74000 PE BUY @184.2 ‡ | `W · A · · c p A W ·` | **NO** 2w 2a 4n 1c /9 | `W · A · · · p A W ·` | **NO** 2w 2a 5n 0c /9 |
| 09-24 13:41 | SENSEX 73900 PE BUY @188.9 ‡ | `W · W · W c p A A W` | **WAIT** 4w 2a 2n 1c /9 | `W · W · W · p A A W` | **WAIT** 4w 2a 3n 0c /9 |
| 09-24 13:43 | SENSEX 73900 PE BUY @206.55 ‡ | `W · W · W c p A A W` | **WAIT** 4w 2a 2n 1c /9 | `W · W · W · p A A W` | **WAIT** 4w 2a 3n 0c /9 |
| 09-24 13:44 | SENSEX 73900 PE BUY @230.45 ‡ | `W · W · W c p A A W` | **WAIT** 4w 2a 2n 1c /9 | `W · W · W · p A A W` | **WAIT** 4w 2a 3n 0c /9 |
| 09-24 13:45 | SENSEX 73800 PE BUY @211.05 ‡ | `W · W · W c p · A W` | **WAIT** 4w 1a 3n 1c /9 | `W · W · W · p · A W` | **WAIT** 4w 1a 4n 0c /9 |
| 09-24 13:54 | SENSEX 73800 PE BUY @252.15 ‡ | `W · W · · c p W A ·` | **WAIT** 3w 1a 4n 1c /9 | `W · W · · · p W A ·` | **WAIT** 3w 1a 5n 0c /9 |
| 09-24 13:57 | SENSEX 73800 PE BUY @267.4 ‡ | `W · W · · c p W A ·` | **WAIT** 3w 1a 4n 1c /9 | `W · W · · · p W A ·` | **WAIT** 3w 1a 5n 0c /9 |
| 09-24 14:23 | SENSEX 73800 PE BUY @287.45 ‡ | `W · W · · c p W A ·` | **WAIT** 3w 1a 4n 1c /9 | `W · W · · · p W A ·` | **WAIT** 3w 1a 5n 0c /9 |

Key: W with · A against · · neither · c could not check · – not shown (writer #5) · p printed (rev 3 VPIN). Check order: RIGHT NOW, DAY / TREND, INSTRUMENT, WALL BEHIND, WALL AHEAD, ORDER FLOW, VPIN, CROSS-INDEX, ROOM, PAYING.

**Words over the 51: unchanged.**
- Rev 3: GO 2 · WAIT 46 · NO 3.
- Rev 3.1: GO 2 · WAIT 46 · NO 3.
- No entry changed word.

**What moved, and why (check by check):**

- **#6 ORDER FLOW, all 24 SENSEX entries.** `REPLAY.md` holds 24 SENSEX entries (22 Oct × 1, 1 Oct × 9, 23 Sep × 1, 24 Sep × 13). The amendment's §6 says 18, and all 24 were replayed. Each moves from "could not check — SENSEX fut patla" to a read on NIFTY futures:
  - **WITH on 8:**
    - **22 Oct 13:00 CE:** "NIFTY naye long". Effort 0.85× at the 12:54 high, normal, so no effort vote. The quadrant: NIFTY fut OI +26,520 (+0.18 %) in 10 min with price +70, i.e. new longs.
    - **1 Oct 12:06 / 12:10 / 12:10 PEs:** "NIFTY low 0.5× sasta". Effort 0.49× at the 12:04 fresh low, the cheap-low continuation.
    - **1 Oct 12:19 / 12:22 / 12:27 PEs and 24 Sep 09:42 PE:** "NIFTY naye short".
      - At 12:19 and 12:27 effort was 3.1× and 3.0× at a LOW. That is the failed mirror, so no effort vote, and the quadrant decided.
      - At 09:42 effort could not check: before 09:56, the day median needs 6 five-minute blocks.
  - **NEITHER on 16:** "NIFTY fut OI flat" (14) or "NIFTY chaal nahi" (2).
  - **AGAINST and could not check: none.**
  - So **every SENSEX entry loses its one could-not-check.**
  - On 5 of them the count reaches 6 WITH, the GO bar: 22 Oct 13:00, 1 Oct 12:10 × 2, 12:22, 12:27. All 5 stay WAIT only because #9 ROOM is AGAINST on each.
  - On her 22 Oct losing CE, rev 3.1 is one WITH closer to GO than rev 3: 6 with, 1 against, 0 could not check.
- **#10 PAYING, 11 SENSEX entries.**
  - These are the "pop ?" rows: the payers covering at a fresh extreme, with the tape unread.
    - 1 Oct: 10:02, 12:10 × 2, 12:22, 12:27.
    - 24 Sep: 10:19, 12:35, 13:41, 13:43, 13:44, 13:45.
  - Each now reads NIFTY's tape, finds it **not exhausted** (no EXHAUST, ABSORB or ≥ 2× high on NIFTY within 15 min), and keeps the base WITH without the "?".
  - **The spent pop fired on none of the 51.**
- **#10 FRESH-AFTER (§2, all indices).** It was "yes" on 3 entries, and in each the tape read (NIFTY's) was not exhausted, so the base WITH stood. The cell is unchanged; the hover gains the FRESH-AFTER line.
  - **22 Oct 13:00 SENSEX CE:** 4 min after the 73,575 spot high, 120 pts off it (≤ 150).
  - **22 Sep 10:44 NIFTY PE:** 2 min after the 23,370 low, 19 pts off.
  - **24 Sep 12:44 SENSEX PE:** 9 min after the 73,961 low, 26 pts off.
  - No other NIFTY entry moved; there is no BANKNIFTY entry in `REPLAY.md`.
- **#1 RIGHT NOW** (hover only; the chip is printed, never counted). On SENSEX its F chip is now NIFTY's newest prototype fight within 30 min.
  - 22 Oct 13:00: "F NIFTY AGAINST". The prototype's NIFTY 5-min bucket shows sellers winning at 22,755 at 13:00.
  - Note this is a different read from the fold engine's NIFTY flat chip, which said BUYERS at 13:01 (buyers won 12:54). See (c).
- **#2, #3, #4, #5, #7, #8, #9:** unchanged on every entry, as §1.1 says.

**Rev 3.1 hovers, the entries it moved:**

- **2026-10-22 13:00:00 SENSEX 73400 CE BUY** (NOTEPAD 22 Oct 13:00): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → WITH "NIFTY naye long · effort 0.8×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.85× the day's lots/pt at a fresh high 12:54 · QUADRANT NIFTY [M/I]: NIFTY fut OI +26,520 (0.18%) over 10 min, price +70 → naye long · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 22,755 13:00 (initiative, 367 lots) · saath
- **2026-10-01 09:30:46 SENSEX 72400 CE BUY** (import): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort ?"
    - rev 3.1 hover: EFFORT NIFTY [I]: could not check — NIFTY flow not read (could not check — the day median needs 6 five-minute blocks (has 0); from 09:56) · QUADRANT NIFTY [M/I]: NIFTY fut OI +22,035 (0.12%) over 10 min, price +19 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY no fight inside 30 min · kuch nahi
- **2026-10-01 10:00:48 SENSEX 72400 CE BUY** (import): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY chaal nahi · effort ?"
    - rev 3.1 hover: EFFORT NIFTY [I]: could not check — NIFTY flow not read (could not check — the day median needs 6 five-minute blocks (has 1); from 09:56) · QUADRANT NIFTY [M/I]: NIFTY fut OI +17,030 (0.09%) over 10 min, price +9 → chaal nahi · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): buyers won at 22,641 10:00 (absorbed, 268 lots) · kuch nahi
- **2026-10-01 10:02:20 SENSEX 72400 CE BUY** (import): rev 3 GO → rev 3.1 GO
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort ?"
    - rev 3.1 hover: EFFORT NIFTY [I]: could not check — NIFTY flow not read (could not check — the day median needs 6 five-minute blocks (has 1); from 09:56) · QUADRANT NIFTY [M/I]: NIFTY fut OI +15,925 (0.09%) over 10 min, price +45 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): buyers won at 22,641 10:00 (absorbed, 268 lots) · kuch nahi
  - PAYING: WITH "73000 leaving · 72800 leaving · pop ?" → WITH "73000 leaving · 72800 leaving"
    - rev 3.1 hover: CE 73000 UNWINDING (peak 65.0L at 10:02, 6.7 % off) · CE 72800 UNWINDING (peak 32.9L at 09:59, 8.8 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (72,523 spot 10:02) · tape not exhausted · saath
- **2026-10-01 12:06:38 SENSEX 72400 PE BUY** (import): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → WITH "NIFTY low 0.5× sasta"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.49× the day's lots/pt at a fresh low 12:04 · QUADRANT NIFTY [M/I]: NIFTY fut OI -4,550 (-0.02%) over 10 min, price -7 → chaal nahi · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): buyers won at 22,652 12:00 (initiative, 151 lots) · saath
- **2026-10-01 12:10:13 SENSEX 72400 PE BUY** (import): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → WITH "NIFTY low 0.5× sasta"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.49× the day's lots/pt at a fresh low 12:04 · QUADRANT NIFTY [M/I]: NIFTY fut OI +19,565 (0.11%) over 10 min, price -74 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 22,620 12:10 (initiative, 368 lots) · saath
  - PAYING: WITH "72000 leaving · 72200 leaving · pop ?" → WITH "72000 leaving · 72200 leaving"
    - rev 3.1 hover: PE 72000 UNWINDING (peak 88.6L at 12:06, 5.1 % off) · PE 72200 UNWINDING (peak 48.9L at 11:52, 11.3 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (72,253 spot 12:10) · tape not exhausted · saath
- **2026-10-01 12:10:20 SENSEX 72300 PE BUY** (import): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → WITH "NIFTY low 0.5× sasta"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.49× the day's lots/pt at a fresh low 12:04 · QUADRANT NIFTY [M/I]: NIFTY fut OI +19,565 (0.11%) over 10 min, price -73 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 22,620 12:10 (initiative, 368 lots) · saath
  - PAYING: WITH "72000 leaving · 72200 leaving · pop ?" → WITH "72000 leaving · 72200 leaving"
    - rev 3.1 hover: PE 72000 UNWINDING (peak 88.6L at 12:06, 5.1 % off) · PE 72200 UNWINDING (peak 48.9L at 11:52, 11.3 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (72,218 spot 12:10) · tape not exhausted · saath
- **2026-10-01 12:19:41 SENSEX 72300 PE BUY** (import): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → WITH "NIFTY naye short · effort 3.1×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 3.13× the day's lots/pt at a fresh low 12:14 · QUADRANT NIFTY [M/I]: NIFTY fut OI +46,085 (0.25%) over 10 min, price -21 → naye short · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 22,597 12:15 (initiative, 154 lots) · saath
- **2026-10-01 12:22:35 SENSEX 72300 PE BUY** (import): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → WITH "NIFTY naye short · effort 1.4×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 1.37× the day's lots/pt at a fresh low 12:19 · QUADRANT NIFTY [M/I]: NIFTY fut OI +57,525 (0.31%) over 10 min, price -25 → naye short · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 22,595 12:20 (initiative, 183 lots) · saath
  - PAYING: WITH "72000 leaving · 71500 flat · pop ?" → WITH "72000 leaving · 71500 flat"
    - rev 3.1 hover: PE 72000 UNWINDING (peak 88.6L at 12:06, 15.1 % off) · PE 71500 STALLED (peak 47.5L at 12:22, 0.0 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (72,166 spot 12:19) · tape not exhausted · saath
- **2026-10-01 12:27:39 SENSEX 72300 PE BUY** (import): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → WITH "NIFTY naye short · effort 3.0×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 2.97× the day's lots/pt at a fresh low 12:24 · QUADRANT NIFTY [M/I]: NIFTY fut OI +44,655 (0.24%) over 10 min, price -49 → naye short · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 22,572 12:25 (initiative, 774 lots) · saath
  - PAYING: WITH "72000 leaving · 71500 flat · pop ?" → WITH "72000 leaving · 71500 flat"
    - rev 3.1 hover: PE 72000 UNWINDING (peak 88.6L at 12:06, 25.2 % off) · PE 71500 STALLED (peak 48.3L at 12:27, 0.0 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (72,089 spot 12:26) · tape not exhausted · saath
- **2026-09-23 11:32:24 SENSEX 74900 CE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 0.6×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.63× the day's lots/pt at a fresh high 11:16 — older than 15 min or no extreme: no vote · QUADRANT NIFTY [M/I]: NIFTY fut OI -1,495 (-0.01%) over 10 min, price +19 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY no fight inside 30 min · kuch nahi
- **2026-09-24 09:42:43 SENSEX 74200 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → WITH "NIFTY naye short · effort ?"
    - rev 3.1 hover: EFFORT NIFTY [I]: could not check — NIFTY flow not read (could not check — the day median needs 6 five-minute blocks (has 2); from 09:56) · QUADRANT NIFTY [M/I]: NIFTY fut OI +44,330 (0.28%) over 10 min, price -32 → naye short · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY no fight inside 30 min · saath
- **2026-09-24 10:19:11 SENSEX 74200 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 0.7×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.68× the day's lots/pt at a fresh high 10:11 · QUADRANT NIFTY [M/I]: NIFTY fut OI -17,615 (-0.11%) over 10 min, price -37 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,243 10:15 (initiative, 396 lots) · kuch nahi
  - PAYING: WITH "74000 leaving · 74100 flat · pop ?" → WITH "74000 leaving · 74100 flat"
    - rev 3.1 hover: PE 74000 UNWINDING (peak 53.0L at 10:15, 8.4 % off) · PE 74100 STALLED (peak 31.3L at 10:15, 4.4 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (74,090 spot 10:17) · tape not exhausted · saath
- **2026-09-24 12:32:32 SENSEX 74100 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 0.7×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.74× the day's lots/pt at a fresh low 12:29 · QUADRANT NIFTY [M/I]: NIFTY fut OI -4,550 (-0.03%) over 10 min, price -19 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,223 12:15 (pressing, 147 lots) · kuch nahi
- **2026-09-24 12:35:18 SENSEX 74000 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 0.7×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.74× the day's lots/pt at a fresh low 12:29 · QUADRANT NIFTY [M/I]: NIFTY fut OI +3,185 (0.02%) over 10 min, price -30 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,204 12:35 (initiative, 597 lots) · kuch nahi
  - PAYING: WITH "73800 leaving · 73900 leaving · pop ?" → WITH "73800 leaving · 73900 leaving"
    - rev 3.1 hover: PE 73800 UNWINDING (peak 40.1L at 12:17, 12.1 % off) · PE 73900 UNWINDING (peak 37.9L at 12:17, 24.0 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (73,962 spot 12:34) · tape not exhausted · saath
- **2026-09-24 12:44:46 SENSEX 74000 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 GO → rev 3.1 GO
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY chaal nahi · effort 1.1×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 1.13× the day's lots/pt at a fresh low 12:39 · QUADRANT NIFTY [M/I]: NIFTY fut OI +2,730 (0.02%) over 10 min, price 0 → chaal nahi · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,204 12:35 (initiative, 597 lots) · kuch nahi
- **2026-09-24 13:26:41 SENSEX 74000 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 NO → rev 3.1 NO
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 0.9×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.86× the day's lots/pt at a fresh high 13:13 · QUADRANT NIFTY [M/I]: NIFTY fut OI -18,070 (-0.12%) over 10 min, price -23 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY no fight inside 30 min · kuch nahi
- **2026-09-24 13:41:38 SENSEX 73900 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 1.0×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 1.02× the day's lots/pt at a fresh low 13:29 · QUADRANT NIFTY [M/I]: NIFTY fut OI -780 (-0.01%) over 10 min, price -23 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,167 13:30 (initiative, 345 lots) · kuch nahi
  - PAYING: WITH "73800 leaving · 73500 flat · pop ?" → WITH "73800 leaving · 73500 flat"
    - rev 3.1 hover: PE 73800 UNWINDING (peak 43.0L at 13:27, 24.5 % off) · PE 73500 STALLED (peak 42.6L at 13:40, 1.7 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (73,860 spot 13:40) · tape not exhausted · saath
- **2026-09-24 13:43:44 SENSEX 73900 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 1.0×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 1.02× the day's lots/pt at a fresh low 13:29 · QUADRANT NIFTY [M/I]: NIFTY fut OI -20,085 (-0.13%) over 10 min, price -37 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,167 13:30 (initiative, 345 lots) · kuch nahi
  - PAYING: WITH "73800 leaving · 73500 leaving · pop ?" → WITH "73800 leaving · 73500 leaving"
    - rev 3.1 hover: PE 73800 UNWINDING (peak 43.0L at 13:27, 31.6 % off) · PE 73500 UNWINDING (peak 42.6L at 13:40, 8.1 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (73,843 spot 13:43) · tape not exhausted · saath
- **2026-09-24 13:44:09 SENSEX 73900 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 1.0×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 1.02× the day's lots/pt at a fresh low 13:29 — older than 15 min or no extreme: no vote · QUADRANT NIFTY [M/I]: NIFTY fut OI -12,285 (-0.08%) over 10 min, price -42 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,167 13:30 (initiative, 345 lots) · kuch nahi
  - PAYING: WITH "73800 leaving · 73500 leaving · pop ?" → WITH "73800 leaving · 73500 leaving"
    - rev 3.1 hover: PE 73800 UNWINDING (peak 43.0L at 13:27, 31.6 % off) · PE 73500 UNWINDING (peak 42.6L at 13:40, 8.1 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (73,823 spot 13:44) · tape not exhausted · saath
- **2026-09-24 13:45:56 SENSEX 73800 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 1.0×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 1.02× the day's lots/pt at a fresh low 13:29 — older than 15 min or no extreme: no vote · QUADRANT NIFTY [M/I]: NIFTY fut OI -10,400 (-0.07%) over 10 min, price -60 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,144 13:45 (initiative, 259 lots) · kuch nahi
  - PAYING: WITH "73500 leaving · 73700 leaving · pop ?" → WITH "73500 leaving · 73700 leaving"
    - rev 3.1 hover: PE 73500 UNWINDING (peak 42.6L at 13:40, 8.1 % off) · PE 73700 UNWINDING (peak 31.6L at 13:40, 17.0 % off) [M]; the move needs somebody forced to pay for it · SPENT POP [I]: fresh extreme yes (73,763 spot 13:45) · tape not exhausted · saath
- **2026-09-24 13:54:47 SENSEX 73800 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 1.1×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 1.11× the day's lots/pt at a fresh low 13:48 · QUADRANT NIFTY [M/I]: NIFTY fut OI +8,385 (0.05%) over 10 min, price -40 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,104 13:50 (initiative, 318 lots) · kuch nahi
- **2026-09-24 13:57:49 SENSEX 73800 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 0.8×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.77× the day's lots/pt at a fresh low 13:54 · QUADRANT NIFTY [M/I]: NIFTY fut OI +12,155 (0.08%) over 10 min, price -26 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,104 13:50 (initiative, 318 lots) · kuch nahi
- **2026-09-24 14:23:31 SENSEX 73800 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 3 WAIT → rev 3.1 WAIT
  - ORDER FLOW: CNC "SENSEX fut patla" → NEITHER "NIFTY fut OI flat · effort 0.8×"
    - rev 3.1 hover: EFFORT NIFTY [I]: 0.79× the day's lots/pt at a fresh low 13:59 — older than 15 min or no extreme: no vote · QUADRANT NIFTY [M/I]: NIFTY fut OI -2,990 (-0.02%) over 10 min, price -26 → fut OI flat · effort first, then the quadrant; covering-only fuel is not paid for · NIFTY fight (printed, not counted): sellers won at 23,091 14:20 (initiative, 126 lots) · kuch nahi

## (b) The one voice, HOLD v2's line and the trade map, OFF vs ON, her 10 SENSEX trades

**In one paragraph:**
- **While she was in, no voice state changed on any of the 10 trades; every EXIT time is the same OFF and ON.** After her exit, ON adds TIGHTEN events on three 1 Oct PEs (the NIFTY pushes below).
- **The FLOW chip** is NIFTY's on every frame. It is labelled "NIFTY flow:", and the one voice's "why" says "NIFTY flow saath".
- **l4** says "NIFTY push ▲/▼ abhi nahi" (checked, none in her direction since entry) where it said "push ? ref nahi" (could not check).
- **The HOLD v2 line moved on NIFTY pushes on three 1 Oct trades,** each time after her exit:
  - 12:05 ▼ and 12:15 ▼, on her 12:06 PE;
  - 12:15 ▼, on the two 12:10 PEs.
- **Those moves were then undone by the window's own rule.** Her imported trades have no thesis invalidation, so the line starts each minute from the fold engine's give-up G (`hold2.live`, unchanged). When G later sat nearer price than the trailed line, the line restarted at G. That is today's behaviour too; it was seen here and not changed.
- **No NIFTY push was skipped for want of a SENSEX bar.**

#### 10-01 SENSEX-72400CE-long-093046

| | OFF (today) | ON (rev 3.1 / Amendment 3) |
|---|---|---|
| states | 09:32 HOLD [after her exit] → 09:35 EXIT (stop hit 72,851f (HOLD v2)) [after her exit] | 09:32 HOLD [after her exit] → 09:35 EXIT (stop hit 72,851f (HOLD v2)) [after her exit] |
| line moves | none | none |
| skipped pushes | none | none |
| FLOW chip | 09:32 QUIET — no fight in the last 0 buckets [after her exit] · 09:33 WITH — buyers won 09:31 at 72929 [after her exit] · 09:46 AGAINST — sellers won 09:40 at 72921 · pullback since 09:40 [after her exit] | 09:32 QUIET — NIFTY flow: no fight in the last 10 buckets [after her exit] |
| l4 entry | 09:32 push ? ref nahi · din range 0.36 EM | 09:32 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.36 EM |
| l4 midpoint | 09:32 push ? ref nahi · din range 0.36 EM | 09:32 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.36 EM |
| l4 exit | 09:32 push ? ref nahi · din range 0.36 EM | 09:32 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.36 EM |
| HOLD v2 (last frame) | HOLD v2 · line 72,301s\|72,851f touched 09:35 (initial) · PE front BUILDING · v2 out 09:35 (line) · push ? ref nahi — SENSEX 5-min bars are not rankable (its reference is 15-min bars, FLOW-STATE §5) | HOLD v2 · line 72,301s\|72,851f touched 09:35 (initial) · PE front BUILDING · v2 out 09:35 (line) |

#### 10-01 SENSEX-72400CE-long-100048

| | OFF (today) | ON (rev 3.1 / Amendment 3) |
|---|---|---|
| states | 10:02 HOLD [after her exit] | 10:02 HOLD [after her exit] |
| line moves | none | none |
| skipped pushes | none | none |
| FLOW chip | 10:02 WITH — buyers won 09:49 at 72951 [after her exit] · 10:12 AGAINST — failed high 10:11 [after her exit] | 10:02 WITH — NIFTY flow: buyers won 10:01 at 22664 [after her exit] |
| l4 entry | 10:02 push ? ref nahi · din range 0.51 EM | 10:02 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.51 EM |
| l4 midpoint | 10:02 push ? ref nahi · din range 0.51 EM | 10:02 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.51 EM |
| l4 exit | 10:02 push ? ref nahi · din range 0.51 EM | 10:02 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.51 EM |
| HOLD v2 (last frame) | HOLD v2 · line 72,300s\|72,851f (initial) · 135 pts · PE front BUILDING · push ? ref nahi — SENSEX 5-min bars are not rankable (its reference is 15-min bars, FLOW-STATE §5) | HOLD v2 · line 72,300s\|72,851f (initial) · 135 pts · PE front BUILDING |

#### 10-01 SENSEX-72400CE-long-100220

| | OFF (today) | ON (rev 3.1 / Amendment 3) |
|---|---|---|
| states | 10:04 HOLD | 10:04 HOLD |
| line moves | none | none |
| skipped pushes | none | none |
| FLOW chip | 10:04 WITH — buyers won 09:49 at 72951 · 10:12 AGAINST — failed high 10:11 [after her exit] · 10:19 AGAINST — sellers won 10:15 at 73004 · pullback since 10:15 [after her exit] · 10:20 WITH — buyers won 10:19 at 73045 [after her exit] · 10:21 AGAINST — sellers won 10:19 at 73022 · pullback since 10:19 [after her exit] | 10:04 WITH — NIFTY flow: buyers won 10:01 at 22664 |
| l4 entry | 10:04 push ? ref nahi · din range 0.54 EM | 10:04 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.54 EM |
| l4 midpoint | 10:05 push ? ref nahi · din range 0.54 EM | 10:05 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.54 EM |
| l4 exit | 10:06 push ? ref nahi · din range 0.55 EM | 10:06 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.55 EM |
| HOLD v2 (last frame) | HOLD v2 · line 72,377s\|72,938f (initial) · 29 pts · PE front BUILDING · push ? ref nahi — SENSEX 5-min bars are not rankable (its reference is 15-min bars, FLOW-STATE §5) | HOLD v2 · line 72,377s\|72,938f (initial) · 29 pts · PE front BUILDING |

#### 10-01 SENSEX-72400PE-long-120638

| | OFF (today) | ON (rev 3.1 / Amendment 3) |
|---|---|---|
| states | 12:08 HOLD → 12:23 EXIT (stop hit 72,698f (HOLD v2)) [after her exit] | 12:08 HOLD → 12:10 TIGHTEN (stop 72,972→72,869f (HOLD v2 trail)) [after her exit] → 12:11 HOLD [after her exit] → 12:20 TIGHTEN (stop 72,869→72,790f (HOLD v2 trail)) [after her exit] → 12:21 HOLD [after her exit] → 12:23 EXIT (stop hit 72,698f (HOLD v2)) [after her exit] |
| line moves | none | 12:10 72,972.0 → 72,869.1f (push 12:05 NIFTY, origin 72,850.90, U 72.85; seen at 12:10) [after her exit]; 12:20 72,869.1 → 72,790.2f (push 12:15 NIFTY, origin 72,772.00, U 72.77; seen at 12:20) [after her exit] |
| skipped pushes | none | none |
| FLOW chip | 12:08 WITH — sellers won 11:08 at 72950 · 12:23 WITH — sellers won 12:22 at 72674 [after her exit] | 12:08 WITH — NIFTY flow: sellers won 12:06 at 22654 · 12:20 QUIET — NIFTY flow: no fight in the last 10 buckets [after her exit] |
| l4 entry | 12:08 push ? ref nahi · din range 0.60 EM | 12:08 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.60 EM |
| l4 midpoint | 12:08 push ? ref nahi · din range 0.60 EM | 12:08 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.60 EM |
| l4 exit | 12:08 push ? ref nahi · din range 0.60 EM | 12:08 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.60 EM |
| HOLD v2 (last frame) | HOLD v2 · line 72,151s\|72,698f touched 12:08 (initial) · CE front BUILDING · v2 out 12:08 (line) · push ? ref nahi — SENSEX 5-min bars are not rankable (its reference is 15-min bars, FLOW-STATE §5) | HOLD v2 · line 72,151s\|72,698f touched 12:08 (initial) · CE front BUILDING · v2 out 12:08 (line) |

#### 10-01 SENSEX-72300PE-long-121020

| | OFF (today) | ON (rev 3.1 / Amendment 3) |
|---|---|---|
| states | 12:12 HOLD [after her exit] → 12:23 EXIT (stop hit 72,698f (HOLD v2)) [after her exit] | 12:12 HOLD [after her exit] → 12:20 TIGHTEN (stop 72,973→72,790f (HOLD v2 trail)) [after her exit] → 12:21 HOLD [after her exit] → 12:23 EXIT (stop hit 72,698f (HOLD v2)) [after her exit] |
| line moves | none | 12:20 72,973.0 → 72,790.2f (push 12:15 NIFTY, origin 72,772.00, U 72.77; seen at 12:20) [after her exit] |
| skipped pushes | none | none |
| FLOW chip | 12:12 WITH — sellers won 11:08 at 72950 [after her exit] · 12:23 WITH — sellers won 12:22 at 72674 [after her exit] · 12:24 WITH — sellers won 12:22 at 72667 [after her exit] | 12:12 WITH — NIFTY flow: sellers won 12:06 at 22654 [after her exit] · 12:20 QUIET — NIFTY flow: no fight in the last 10 buckets [after her exit] |
| l4 entry | 12:12 push ? ref nahi · din range 0.66 EM | 12:12 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.66 EM |
| l4 midpoint | 12:12 push ? ref nahi · din range 0.66 EM | 12:12 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.66 EM |
| l4 exit | 12:12 push ? ref nahi · din range 0.66 EM | 12:12 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.66 EM |
| HOLD v2 (last frame) | HOLD v2 · line 72,147s\|72,691f touched 12:12 (initial) · CE front BUILDING · v2 out 12:12 (line) · push ? ref nahi — SENSEX 5-min bars are not rankable (its reference is 15-min bars, FLOW-STATE §5) | HOLD v2 · line 72,147s\|72,691f touched 12:12 (initial) · CE front BUILDING · v2 out 12:12 (line) |

#### 10-01 SENSEX-72400PE-long-121013

| | OFF (today) | ON (rev 3.1 / Amendment 3) |
|---|---|---|
| states | 12:12 HOLD [after her exit] → 12:23 EXIT (stop hit 72,698f (HOLD v2)) [after her exit] | 12:12 HOLD [after her exit] → 12:20 TIGHTEN (stop 72,973→72,790f (HOLD v2 trail)) [after her exit] → 12:21 HOLD [after her exit] → 12:23 EXIT (stop hit 72,698f (HOLD v2)) [after her exit] |
| line moves | none | 12:20 72,973.0 → 72,790.2f (push 12:15 NIFTY, origin 72,772.00, U 72.77; seen at 12:20) [after her exit] |
| skipped pushes | none | none |
| FLOW chip | 12:12 WITH — sellers won 11:08 at 72950 [after her exit] · 12:23 WITH — sellers won 12:22 at 72674 [after her exit] · 12:24 WITH — sellers won 12:22 at 72667 [after her exit] | 12:12 WITH — NIFTY flow: sellers won 12:06 at 22654 [after her exit] · 12:20 QUIET — NIFTY flow: no fight in the last 10 buckets [after her exit] |
| l4 entry | 12:12 push ? ref nahi · din range 0.66 EM | 12:12 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.66 EM |
| l4 midpoint | 12:12 push ? ref nahi · din range 0.66 EM | 12:12 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.66 EM |
| l4 exit | 12:12 push ? ref nahi · din range 0.66 EM | 12:12 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.66 EM |
| HOLD v2 (last frame) | HOLD v2 · line 72,147s\|72,691f touched 12:12 (initial) · CE front BUILDING · v2 out 12:12 (line) · push ? ref nahi — SENSEX 5-min bars are not rankable (its reference is 15-min bars, FLOW-STATE §5) | HOLD v2 · line 72,147s\|72,691f touched 12:12 (initial) · CE front BUILDING · v2 out 12:12 (line) |

#### 10-01 SENSEX-72300PE-long-121941

| | OFF (today) | ON (rev 3.1 / Amendment 3) |
|---|---|---|
| states | 12:21 HOLD [after her exit] → 12:23 EXIT (stop hit 72,698f (HOLD v2)) [after her exit] | 12:21 HOLD [after her exit] → 12:23 EXIT (stop hit 72,698f (HOLD v2)) [after her exit] |
| line moves | none | none |
| skipped pushes | none | none |
| FLOW chip | 12:21 WITH — sellers won 11:08 at 72950 [after her exit] · 12:23 WITH — sellers won 12:22 at 72674 [after her exit] · 12:24 WITH — sellers won 12:22 at 72667 [after her exit] · 12:35 WITH — sellers won 12:29 at 72591 [after her exit] | 12:21 QUIET — NIFTY flow: no fight in the last 10 buckets [after her exit] |
| l4 entry | 12:21 push ? ref nahi · din range 0.70 EM | 12:21 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.70 EM |
| l4 midpoint | 12:21 push ? ref nahi · din range 0.70 EM | 12:21 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.70 EM |
| l4 exit | 12:21 push ? ref nahi · din range 0.70 EM | 12:21 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.70 EM |
| HOLD v2 (last frame) | HOLD v2 · line 72,072s\|72,616f touched 12:21 (initial) · CE front BUILDING · v2 out 12:21 (line) · push ? ref nahi — SENSEX 5-min bars are not rankable (its reference is 15-min bars, FLOW-STATE §5) | HOLD v2 · line 72,072s\|72,616f touched 12:21 (initial) · CE front BUILDING · v2 out 12:21 (line) |

#### 10-01 SENSEX-72300PE-long-122235

| | OFF (today) | ON (rev 3.1 / Amendment 3) |
|---|---|---|
| states | 12:24 HOLD [after her exit] → 12:25 TIGHTEN (BE lock ✓ 72,734f (HOLD v2)) [after her exit] → 12:26 HOLD [after her exit] → 12:35 EXIT (stop hit 72,616f (HOLD v2)) [after her exit] | 12:24 HOLD [after her exit] → 12:25 TIGHTEN (BE lock ✓ 72,734f (HOLD v2)) [after her exit] → 12:26 HOLD [after her exit] → 12:35 EXIT (stop hit 72,616f (HOLD v2)) [after her exit] |
| line moves | none | none |
| skipped pushes | none | none |
| FLOW chip | 12:24 WITH — sellers won 12:22 at 72667 [after her exit] · 12:35 WITH — sellers won 12:29 at 72591 [after her exit] | 12:24 QUIET — NIFTY flow: no fight in the last 10 buckets [after her exit] |
| l4 entry | 12:24 push ? ref nahi · din range 0.81 EM | 12:24 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.81 EM |
| l4 midpoint | 12:24 push ? ref nahi · din range 0.81 EM | 12:24 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.81 EM |
| l4 exit | 12:24 push ? ref nahi · din range 0.81 EM | 12:24 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.81 EM |
| HOLD v2 (last frame) | HOLD v2 · line 72,066s\|72,616f touched 12:24 (initial) · CE front BUILDING · v2 out 12:24 (line) · push ? ref nahi — SENSEX 5-min bars are not rankable (its reference is 15-min bars, FLOW-STATE §5) | HOLD v2 · line 72,066s\|72,616f touched 12:24 (initial) · CE front BUILDING · v2 out 12:24 (line) |

#### 10-01 SENSEX-72300PE-long-122739

| | OFF (today) | ON (rev 3.1 / Amendment 3) |
|---|---|---|
| states | 12:29 HOLD → 12:35 EXIT (stop hit 72,616f (HOLD v2)) [after her exit] | 12:29 HOLD → 12:35 EXIT (stop hit 72,616f (HOLD v2)) [after her exit] |
| line moves | none | none |
| skipped pushes | none | none |
| FLOW chip | 12:29 WITH — sellers won 12:22 at 72667 · 12:35 AGAINST — failed low 12:34 [after her exit] · 12:42 AGAINST — accepted past 72616 12:41 · failed low 12:34 [after her exit] | 12:29 QUIET — NIFTY flow: no fight in the last 10 buckets |
| l4 entry | 12:29 push ? ref nahi · din range 0.90 EM | 12:29 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.90 EM |
| l4 midpoint | 12:29 push ? ref nahi · din range 0.90 EM | 12:29 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.90 EM |
| l4 exit | 12:29 push ? ref nahi · din range 0.90 EM | 12:29 NIFTY push ▼ abhi nahi · ulta NIFTY push: none · din range 0.90 EM |
| HOLD v2 (last frame) | HOLD v2 · line 72,065s\|72,616f touched 12:29 (initial) · CE front STALLED · v2 out 12:29 (line) · push ? ref nahi — SENSEX 5-min bars are not rankable (its reference is 15-min bars, FLOW-STATE §5) | HOLD v2 · line 72,065s\|72,616f touched 12:29 (initial) · CE front STALLED · v2 out 12:29 (line) |

#### 10-22 SENSEX-73400CE-long-130000

| | OFF (today) | ON (rev 3.1 / Amendment 3) |
|---|---|---|
| states | 13:01 HOLD → 13:24 EXIT (stop hit 73,431f (HOLD v2)) | 13:01 HOLD → 13:24 EXIT (stop hit 73,431f (HOLD v2)) |
| line moves | none | none |
| skipped pushes | none | none |
| FLOW chip | 13:01 WITH — buyers won 12:55 at 73762 · 13:04 WITH — buyers won 12:55 at 73762 · tiring 1 min · 13:05 AGAINST — sellers won 13:03 at 73560 · pullback since 13:03 · 13:20 QUIET — no fight in the last 10 buckets · pullback since 13:03 · 13:25 AGAINST — sellers won 13:20 at 73505 · pullback since 13:20 · 13:27 AGAINST — accepted past 73431 13:26 · pullback since 13:20 [after her exit] · 13:28 AGAINST — accepted past 73431 13:26 [after her exit] | 13:01 WITH — NIFTY flow: buyers won 12:54 at 22772 · 13:06 QUIET — NIFTY flow: no fight in the last 10 buckets · 13:14 AGAINST — NIFTY flow: sellers won 13:12 at 22721 · 13:22 AGAINST — NIFTY flow: sellers won 13:21 at 22689 · 13:29 AGAINST — NIFTY flow: sellers won 13:27 at 22653 [after her exit] |
| l4 entry | 13:01 push ? ref nahi · din range 0.98 EM | 13:01 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.98 EM |
| l4 midpoint | 13:13 push ? ref nahi · din range 0.98 EM | 13:13 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.98 EM |
| l4 exit | 13:25 push ? ref nahi · din range 0.98 EM | 13:25 NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.98 EM |
| HOLD v2 (last frame) | HOLD v2 · line 73,260s\|73,431f touched 13:24 (initial) · PE 73000 gave up (unwinding, price neeche) · v2 out 13:24 (line) · push ? ref nahi — SENSEX 5-min bars are not rankable (its reference is 15-min bars, FLOW-STATE §5) | HOLD v2 · line 73,260s\|73,431f touched 13:24 (initial) · PE 73000 gave up (unwinding, price neeche) · v2 out 13:24 (line) |

### Her 22 Oct 13:00 SENSEX 73400 CE, OFF vs ON

- **State sequence:** identical. 13:01 HOLD → 13:24 EXIT (stop hit 73,431f, HOLD v2's initial line), both ways.
- **Line moves: none, both ways, for different reasons.**
  - OFF could not check: "push ? ref nahi", SENSEX 5-min bars are not rankable.
  - ON checked: NIFTY had no ▲ push closing between her 13:00 entry and 13:24.
    - The covering pop's ▲ push (NIFTY 12:50 bar, 22,674 → 22,770, size 19×, R 5.1) closed at 12:55, five minutes before she bought. Under §1m only a push closing after entry moves the line.
    - The next NIFTY push, 13:25 ▼, closed at 13:30, after her exit. It is the ulta push l4 shows from 13:30: "ulta NIFTY push ▼ 13:25 @ 73,389f".
- **The FLOW chip:**
  - **OFF (SENSEX's own thin tape):**
    - 13:01 WITH (buyers won 12:55 at 73,762);
    - 13:05 AGAINST (sellers won 13:03 at 73,560);
    - 13:20 QUIET;
    - 13:25 AGAINST.
  - **ON (NIFTY engine):**
    - 13:01 WITH (NIFTY buyers won 12:54 at 22,772);
    - 13:06 QUIET (that fight left the 10-bucket window);
    - 13:14 AGAINST (NIFTY sellers won 13:12 at 22,721);
    - 13:22 AGAINST (sellers won 13:21 at 22,689).
  - So on NIFTY's flow the chip turned against her **9 minutes later** than on SENSEX's own tape.
  - The voice never warned either way. ZONE ALONE needs OI not WITH, and the PE 73300 writers read building all trade, so OI was WITH ("why: PE 73300 writers building · NIFTY flow saath" until 13:05).
- **l4:** "NIFTY push ▲ abhi nahi · ulta NIFTY push: none · din range 0.98 EM" at entry (13:01), at the midpoint (13:13) and at her exit (13:25). OFF read "push ? ref nahi · din range 0.98 EM" at all three.
- **HOLD v2 text:** the trailing "push ? ref nahi — SENSEX 5-min bars are not rankable …" is gone. The block is otherwise the same: line 73,431f initial; v2 out 13:24 (line); PE 73000 gave up at 13:28, after her exit.

## (c) A trader's sanity check, 22 Oct: NIFTY's pushes on SENSEX's bars, and NIFTY's flow chip on NIFTY's fights

**Every NIFTY push of the day** comes from the GoCharting bar (all 11 are "gc"), ranked on NIFTY's own history (gc 19 days, ux 14). Beside each:
- the SENSEX ux 5-min bar of the same slot it was translated onto;
- the raw SENSEX 1-min bar at the slot's first minute (`data/backtest/SENSEX/fut_2026-10-22.json`, quantity in contracts; the lot is 20).

| NIFTY push (GoCharting bar) | dir | NIFTY o → c | SENSEX ux 5-min bar o → c | U (SENSEX σ / 0.1 % floor) | line would sit at | SENSEX 1-min bar at the slot's first minute (o, vol) |
|---|---|---|---|---|---|---|
| 10:00 (closed 10:05, size 12.296, R 1.979) | ▼ | 22,643.5 → 22,596.0 | 73,377.45 → 73,212.60 | 98.0 (σ) | 73,402.0 | 73,377.45, 20 contracts |
| 10:10 (closed 10:15, size 7.407, R 1.983) | ▲ | 22,629.9 → 22,677.5 | 73,263.90 → 73,464.40 | 96.8 (σ) | 73,239.7 | 73,263.90, 40 contracts |
| 10:20 (closed 10:25, size 30.962, R 3.078) | ▲ | 22,671.1 → 22,746.5 | 73,477.15 → 73,640.05 | 151.5 (σ) | 73,439.3 | 73,477.15, 40 contracts |
| 10:30 (closed 10:35, size 4.489, R 2.101) | ▲ | 22,727.8 → 22,779.7 | 73,626.00 → 73,715.95 | 160.4 (σ) | 73,585.9 | 73,626.00, 120 contracts |
| 11:10 (closed 11:15, size 6.5, R 0.99) | ▲ | 22,780.0 → 22,800.0 | 73,750.00 → 73,830.00 | 207.7 (σ) | 73,698.1 | 73,750.00, 540 contracts |
| 11:40 (closed 11:45, size 5.235, R 2.024) | ▼ | 22,748.0 → 22,706.1 | 73,625.00 → 73,525.00 | 209.7 (σ) | 73,677.4 | 73,634.95, 0 contracts |
| 11:45 (closed 11:50, size 10.193, R 4.034) | ▼ | 22,707.2 → 22,637.0 | 73,500.00 → 73,220.00 | 213.2 (σ) | 73,553.3 | 73,500.00, 260 contracts |
| 11:50 (closed 11:55, size 5.404, R 0.575) | ▲ | 22,632.0 → 22,642.0 | 73,273.90 → 73,316.50 | 213.2 (σ) | 73,220.6 | 73,273.90, 420 contracts |
| 12:15 (closed 12:20, size 6.516, R 1.196) | ▼ | 22,645.0 → 22,623.0 | 73,257.85 → 73,180.00 | 219.0 (σ) | 73,312.6 | 73,230.00, 0 contracts |
| 12:50 (closed 12:55, size 19.054, R 5.096) | ▲ | 22,674.2 → 22,770.0 | 73,404.90 → 73,699.65 | 209.5 (σ) | 73,352.5 | 73,300.00, 0 contracts |
| 13:25 (closed 13:30, size 8.358, R 1.115) | ▼ | 22,679.6 → 22,659.8 | 73,389.45 → 73,309.85 | 196.0 (σ) | 73,438.4 | 73,389.45, 180 contracts |

- **Times:** every translated push keeps NIFTY's slot, and each has a SENSEX bar, so none was skipped.
- **The translated o** is the SENSEX ux bar's open, i.e. the first SENSEX trade in that slot.
  - It equals the raw 1-min open on 8 of 11.
  - The other 3 are thin-tape minutes (A25): 11:40, 12:15 and 12:50. The slot's first 1-min bar has zero volume and carries the last price (12:50: 73,300.00, 0 contracts). The first trade came the next minute: 12:51 at 73,404.90 with 40 contracts, exactly the translated o.
  - The same holds at 11:40 (first trade 11:42 at 73,625.00) and 12:15 (first trade 12:17 at 73,257.85). So on a quiet SENSEX minute, o is the first real print in the slot, up to two minutes late [M].
- **U:** σ (SENSEX's own 5-min vwapSeries) was above the 0.1 % floor on all 11, 96–219 pts. The ▲ line for the 12:50 push would sit at 73,352.5f.
- **The covering pop is visible in both.** NIFTY 12:50 bar +96 pts. SENSEX: 12:51 73,404.90 → 12:55 73,775 high, with 3,540 contracts in 12:52 alone.
- **NIFTY's flow chip vs NIFTY's fights** (the NIFTY engine's own fixed fights, 12:30–13:40):
  - 12:35 buyers (fixed 12:39);
  - 12:54 buyers at 22,772.2 (fixed 12:55);
  - 13:12 sellers at 22,721.5 (fixed 13:13);
  - 13:21 sellers at 22,689.0 (fixed 13:22);
  - 13:27 sellers at 22,653.1 (fixed 13:29).
- **How the chip follows them:**
  - The chip read BUYERS (her WITH) from the 12:55 fix through 13:05:38.
  - It read QUIET at 13:06:38: the 12:54:55 fight fell out of the last 10 buckets, whose oldest now starts 12:55:15.
  - It read SELLERS (her AGAINST) at 13:14:38: the 13:12:27 fight was fixed at 13:13.
  - Checked again minute by minute with a separate causal feed: BUYERS at 13:05:00 and 13:06:00, QUIET 13:10–13:13, SELLERS from 13:14:00. The minute the chip flips depends on the second a bucket closes; the fights are the same.
- **Two NIFTY reads disagree at 13:00, by design of their sources.**
  - Validate's prototype (engine.js 5-min buckets) printed "sellers won at 22,755 13:00 (initiative, 367 lots)" for #1 and #6's hover.
  - The fold engine (volume buckets) said buyers won 12:54.
  - Both are NIFTY's tape. They are not the same fight definition, as on any index today.

## Where the text was not literal against the code, and what was built

1. **"SENSEX futures flow is never read" (§1.1, §7) vs "#3, #9 unchanged" (§1.1).**
   - The Validate prototype's give-up G (#1's engine-now proxy and #9 ROOM) comes from SENSEX's own fights (`zoneFight`) and its acceptance from SENSEX bar volume. #3's expression facts include SENSEX's fight, CVD and push.
   - §1.1 names only #1's FLOW chip, #6 and #10's tape, and lists #3 and #9 as unchanged, so those stay SENSEX's.
   - §7's "anywhere" is therefore not literally true inside Validate. For her to decide.
2. **FRESH-AFTER's "no newer extreme has been set since"** holds by construction: it is the running 30-min extreme. The stamp is the cell "covering · pop khatam (N min after the high)", "low" for a down trade.
3. **§1.3 "Validate's in-trade row":**
   - The prototype's own FLOW chip there is engine.js's NIFTY newest fight (§1.1's #1 read), labelled "NIFTY FLOW".
   - The server's one-voice block shown above it carries the fold engine's NIFTY flat chip.
4. **The labels.**
   - `voice.py` is unchanged. Its words "flow saath" and "· flow x" are renamed "NIFTY flow …" in the reply path (`sensex_flow.relabel`).
   - HOLD v2's "(PUSH ▼ 13:05)" becomes "(NIFTY PUSH ▼ 13:05)" in the server, not in `hold2.py`. `hold2.py` gained only the optional `pushes_`.
5. **`push_src`** is stamped only while ON (OFF rows stay exactly today's).
   - `sensex_flow.FROM`, the signing day, must be set in the same commit as ON. SENSEX rows before it read "SENSEX-ux".
   - `tools/hold2_score.py`'s READINGS #2 still says the SENSEX trail is inactive; it needs its line at the signature.
6. **"At the same minute" (§1.3):** live, the NIFTY flat read must be within 60 s of the trade's read, else CAN'T CHECK "NIFTY read hh:mm:ss, trade hh:mm:ss".
7. **The skipped-push stamp** `NIFTY push hh:mm · SENSEX bar ?` is on HOLD v2's text. None occurred in the replay.
8. **Not touched:** DECODE's SENSEX lines and FADE-D's HOLD v2 chip (`decode._held`), `tools/faded_score.py`, fold.py, every OI read, the GoCharting extension.
