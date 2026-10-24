# VALIDATE rev 2 vs rev 3 on her real trades (2026-10-23, after the close; descriptive, in-sample, no hit rates)

The rule text is `docs/hold/VALIDATE-PREREG-rev3.md` (sha256 `a4186306…82a5`). It was hashed before this replay ran.

## Method

- **Rev 2** = `ui-v2/public/validate2/engine.js` at git 5b9ed44. **Rev 3** = the working tree.
- Both engines load the same day payload: `v2feed.serve(day)`, the face's own `/api/v2/data`.
- Each trade is validated at its entry second, as a fresh press with no sticky W / G, with the feed cut at that second.
- Rev 3 also gets the DECODE blocks of the latest close readable at the entry (close + 60 s ≤ entry), from `server._decode_all(day, close, False)`. That is what `GET /api/decode` serves.
- Re-run with `python -X utf8 docs/hold/validate3/replay.py`. It writes only to a temp folder.

**Her trades: 51 entries.**
- **22** marked or imported trades from `data/fold/fold_*.jsonl` (src ≠ ifin).
- **1:** her 22 Oct SENSEX 73400 CE. It was never marked; it comes from NOTEPAD 22 Oct 13:00 ("spot 73,443, CE 191"), at 13:00:00.
- **28** opening fills from her broker tradebook (`data/fixtures-private/tradebook_2026-09-21_24.csv`, private, read in place). A buy while flat in that contract counts as an entry; adds and exits do not.
  - 21 Sep has no recorded chain, so it is left out.
  - **‡** marks these rows: the 22–24 Sep chain records carry **no expiry**. So the expected move could not check there ("EM ?"), and the recorded strike's prices may come from a different expiry than her contract (on 23 Sep she traded the 29 Sep monthly).

**This is in-sample**, NIFTY-heavy, and describes what each check voted. It does not say whether a word was right.

**Bugs found in the replay and fixed, code to text:**
- The expected move read the 09:20 row on a press made before 09:20 (look-ahead, 29 Sep 09:18). It now reads "EM ?" until the row exists.

No rule was changed.

## The table

Check order: 1 RIGHT NOW · 2 DAY / TREND · 3 INSTRUMENT · 4 WALL BEHIND · 5 WALL AHEAD · 6 ORDER FLOW · 7 VPIN · 8 CROSS-INDEX · 9 ROOM · 10 PAYING.
Key: W with · A against · `·` neither · c could not check · – not shown (writer #5) · p printed (rev 3 VPIN).

| entry | trade | rev 2 checks (1–10) | rev 2 word | rev 3 checks (1–10) | rev 3 word |
|---|---|---|---|---|---|
| 10-22 13:00 | SENSEX 73400 CE BUY @191 | `W · W · W A c W A W` | **WAIT** 5w 2a 2n 1c /10 | `W · W · W c p W A W` | **WAIT** 5w 1a 2n 1c /9 |
| 10-21 10:07 | NIFTY 23000 PE BUY @174.85 | `W · W W · W W A W ·` | **WAIT** 6w 1a 3n 0c /10 | `W · W W · W p A W ·` | **WAIT** 5w 1a 3n 0c /9 |
| 10-06 09:35 | NIFTY 22600 CE SELL @65.8 | `W · A W – · A W W ·` | **WAIT** 4w 2a 3n 0c /9 | `W · A W – · p W W ·` | **WAIT** 4w 1a 3n 0c /8 |
| 10-06 10:02 | NIFTY 22650 PE SELL @55.9 | `W · A · – W W · W ·` | **WAIT** 4w 1a 4n 0c /9 | `W · A · – A p · W ·` | **NO** 2w 2a 4n 0c /8 |
| 10-06 10:03 | NIFTY 22650 PE BUY @55 | `W · A · · A A · W ·` | **NO** 2w 3a 5n 0c /10 | `W · A · · W p · W ·` | **WAIT** 3w 1a 5n 0c /9 |
| 10-06 14:12 | NIFTY 22600 CE BUY @133 | `W · A · · W W W W ·` | **WAIT** 5w 1a 4n 0c /10 | `W W A · · · p W W ·` | **WAIT** 4w 1a 4n 0c /9 |
| 10-05 09:28 | NIFTY 22600 CE BUY @94.25 | `W · W W · · W c W ·` | **WAIT** 5w 0a 4n 1c /10 | `W · W W · W p c W ·` | **WAIT** 5w 0a 3n 1c /9 |
| 10-05 09:35 | NIFTY 22550 CE BUY @134.95 | `W · W W · · W · A ·` | **WAIT** 4w 1a 5n 0c /10 | `W · W W · · p · A ·` | **WAIT** 3w 1a 5n 0c /9 |
| 10-05 12:09 | NIFTY 22550 PE BUY @174.75 | `W · W · W W W W A W` | **WAIT** 7w 1a 2n 0c /10 | `W · W · W · p W A W` | **WAIT** 5w 1a 3n 0c /9 |
| 10-05 13:41 | NIFTY 22650 PE SELL @131.35 | `W · A · – W W · W W` | **WAIT** 5w 1a 3n 0c /9 | `W · A · – · p · W W` | **WAIT** 3w 1a 4n 0c /8 |
| 10-01 09:21 | NIFTY 22600 PE BUY @142.4 | `W · W W · · c c A ·` | **WAIT** 3w 1a 4n 2c /10 | `W · W W · c p c A ·` | **WAIT** 3w 1a 3n 2c /9 |
| 10-01 09:26 | NIFTY 22600 PE BUY @149.75 | `W · A W · · · c A ·` | **WAIT** 2w 2a 5n 1c /10 | `W · A W · c p c A ·` | **WAIT** 2w 2a 3n 2c /9 |
| 10-01 09:30 | SENSEX 72400 CE BUY @209.4 | `W · A W · · c c A ·` | **WAIT** 2w 2a 4n 2c /10 | `W · A W · c p c A ·` | **WAIT** 2w 2a 3n 2c /9 |
| 10-01 10:00 | SENSEX 72400 CE BUY @237.25 | `W · W · · W c W A ·` | **WAIT** 4w 1a 4n 1c /10 | `W · W · · c p W A ·` | **WAIT** 3w 1a 4n 1c /9 |
| 10-01 10:02 | SENSEX 72400 CE BUY @276.05 | `W · W W W W c W W W` | **GO** 8w 0a 1n 1c /10 | `W · W W W c p W W W` | **GO** 7w 0a 1n 1c /9 |
| 10-01 12:06 | SENSEX 72400 PE BUY @223.97 | `W · A W · A c · A ·` | **NO** 2w 3a 4n 1c /10 | `W · A W · c p · A ·` | **WAIT** 2w 2a 4n 1c /9 |
| 10-01 12:10 | SENSEX 72400 PE BUY @281.45 | `W · W · W A c W A W` | **WAIT** 5w 2a 2n 1c /10 | `W · W · W c p W A W` | **WAIT** 5w 1a 2n 1c /9 |
| 10-01 12:10 | SENSEX 72300 PE BUY @224.1 | `W · W · W A c W A W` | **WAIT** 5w 2a 2n 1c /10 | `W · W · W c p W A W` | **WAIT** 5w 1a 2n 1c /9 |
| 10-01 12:19 | SENSEX 72300 PE BUY @232 | `W · A · · · c · A ·` | **WAIT** 1w 2a 6n 1c /10 | `W · A · · c p · A ·` | **WAIT** 1w 2a 5n 1c /9 |
| 10-01 12:22 | SENSEX 72300 PE BUY @246.4 | `W W W · W · c W A W` | **WAIT** 6w 1a 2n 1c /10 | `W · W · W c p W A W` | **WAIT** 5w 1a 2n 1c /9 |
| 10-01 12:27 | SENSEX 72300 PE BUY @296.9 | `W W W W W W c · A W` | **WAIT** 7w 1a 1n 1c /10 | `W · W W W c p · A W` | **WAIT** 5w 1a 2n 1c /9 |
| 09-30 10:10 | NIFTY 22750 CE BUY @164.7 | `W · W · · W A W W ·` | **WAIT** 5w 1a 4n 0c /10 | `W · W · · · p W W ·` | **WAIT** 4w 0a 5n 0c /9 |
| 09-29 09:18 | NIFTY 22800 PE BUY @113.95 | `W · A W A · c c A A` | **NO** 2w 4a 2n 2c /10 | `W · A W A c p c A A` | **NO** 2w 4a 1n 2c /9 |
| 09-22 09:42 | NIFTY 23300 CE BUY @166.4 ‡ | `W · A W · · c c A ·` | **WAIT** 2w 2a 4n 2c /10 | `W · A W · · p c A ·` | **WAIT** 2w 2a 4n 1c /9 |
| 09-22 10:32 | NIFTY 23550 PE BUY @134.8 ‡ | `W · A · W W c · A W` | **WAIT** 4w 2a 3n 1c /10 | `W · A · W W p · A W` | **WAIT** 4w 2a 3n 0c /9 |
| 09-22 10:42 | NIFTY 23550 PE BUY @174.75 ‡ | `W W A W · W c W A ·` | **WAIT** 5w 2a 2n 1c /10 | `W W A W · W p W A ·` | **WAIT** 5w 2a 2n 0c /9 |
| 09-22 10:43 | NIFTY 23550 PE BUY @175.05 ‡ | `W W A · W W c W A W` | **WAIT** 6w 2a 1n 1c /10 | `W W A · W W p W A W` | **WAIT** 6w 2a 1n 0c /9 |
| 09-22 10:44 | NIFTY 23550 PE BUY @171.5 ‡ | `W W A · W W c W W W` | **WAIT** 7w 1a 1n 1c /10 | `W W A · W W p W W W` | **WAIT** 7w 1a 1n 0c /9 |
| 09-22 10:52 | NIFTY 23500 PE BUY @146.15 ‡ | `W W W · · W c A A ·` | **WAIT** 4w 2a 3n 1c /10 | `W W W · · · p A A ·` | **WAIT** 3w 2a 4n 0c /9 |
| 09-22 13:48 | NIFTY 23500 PE BUY @181.5 ‡ | `W W A · · W c W A ·` | **WAIT** 4w 2a 3n 1c /10 | `W W A · · · p W A ·` | **WAIT** 3w 2a 4n 0c /9 |
| 09-23 09:18 | NIFTY 23450 CE BUY @100 ‡ | `W · A W · · c c A ·` | **WAIT** 2w 2a 4n 2c /10 | `W · A W · c p c A ·` | **WAIT** 2w 2a 3n 2c /9 |
| 09-23 09:47 | NIFTY 23450 CE BUY @99.4 ‡ | `W · A · · · A · A ·` | **WAIT** 1w 3a 6n 0c /10 | `W · A · · · p · A ·` | **WAIT** 1w 2a 6n 0c /9 |
| 09-23 09:49 | NIFTY 23400 PE BUY @125 ‡ | `W · W · · · W · A ·` | **WAIT** 3w 1a 6n 0c /10 | `W · W · · · p · A ·` | **WAIT** 2w 1a 6n 0c /9 |
| 09-23 10:00 | NIFTY 23450 CE BUY @98.6 ‡ | `W · A · · · A · A ·` | **WAIT** 1w 3a 6n 0c /10 | `W · A · · · p · A ·` | **WAIT** 1w 2a 6n 0c /9 |
| 09-23 10:19 | NIFTY 23450 CE BUY @101.85 ‡ | `W · A · · · A · A ·` | **WAIT** 1w 3a 6n 0c /10 | `W · A · · · p · A ·` | **WAIT** 1w 2a 6n 0c /9 |
| 09-23 10:33 | NIFTY 23450 CE BUY @106.45 ‡ | `W · A · · W A W W ·` | **WAIT** 4w 2a 4n 0c /10 | `W · A · · · p W W ·` | **WAIT** 3w 1a 5n 0c /9 |
| 09-23 11:07 | NIFTY 23450 CE BUY @115.65 ‡ | `W · W · · W · W W ·` | **WAIT** 5w 0a 5n 0c /10 | `W · W · · · p W W ·` | **WAIT** 4w 0a 5n 0c /9 |
| 09-23 11:32 | SENSEX 74900 CE BUY @215.25 ‡ | `W · A · · W c W A ·` | **WAIT** 3w 2a 4n 1c /10 | `W W A · · c p W A ·` | **WAIT** 3w 2a 3n 1c /9 |
| 09-24 09:42 | SENSEX 74200 PE BUY @179.25 ‡ | `W · A · W · c W A W` | **WAIT** 4w 2a 3n 1c /10 | `W · A · W c p W A W` | **WAIT** 4w 2a 2n 1c /9 |
| 09-24 10:19 | SENSEX 74200 PE BUY @215.65 ‡ | `W · A · · A c W A W` | **NO** 3w 3a 3n 1c /10 | `W · A · · c p W A W` | **WAIT** 3w 2a 3n 1c /9 |
| 09-24 12:32 | SENSEX 74100 PE BUY @202.35 ‡ | `W W W · · W c W A ·` | **WAIT** 5w 1a 3n 1c /10 | `W · W · · c p W A ·` | **WAIT** 3w 1a 4n 1c /9 |
| 09-24 12:35 | SENSEX 74000 PE BUY @179.8 ‡ | `W W W · W W c · A W` | **WAIT** 6w 1a 2n 1c /10 | `W · W · W c p · A W` | **WAIT** 4w 1a 3n 1c /9 |
| 09-24 12:44 | SENSEX 74000 PE BUY @167.95 ‡ | `W W W · W W c W W W` | **GO** 8w 0a 1n 1c /10 | `W · W · W c p W W W` | **GO** 6w 0a 2n 1c /9 |
| 09-24 13:26 | SENSEX 74000 PE BUY @184.2 ‡ | `W · A · · · c A W ·` | **NO** 2w 2a 5n 1c /10 | `W · A · · c p A W ·` | **NO** 2w 2a 4n 1c /9 |
| 09-24 13:41 | SENSEX 73900 PE BUY @188.9 ‡ | `W W W · W A c A A W` | **NO** 5w 3a 1n 1c /10 | `W · W · W c p A A W` | **WAIT** 4w 2a 2n 1c /9 |
| 09-24 13:43 | SENSEX 73900 PE BUY @206.55 ‡ | `W W W · W A c A A W` | **NO** 5w 3a 1n 1c /10 | `W · W · W c p A A W` | **WAIT** 4w 2a 2n 1c /9 |
| 09-24 13:44 | SENSEX 73900 PE BUY @230.45 ‡ | `W W W · W A c A A W` | **NO** 5w 3a 1n 1c /10 | `W · W · W c p A A W` | **WAIT** 4w 2a 2n 1c /9 |
| 09-24 13:45 | SENSEX 73800 PE BUY @211.05 ‡ | `W W W · W W c · A W` | **WAIT** 6w 1a 2n 1c /10 | `W · W · W c p · A W` | **WAIT** 4w 1a 3n 1c /9 |
| 09-24 13:54 | SENSEX 73800 PE BUY @252.15 ‡ | `W W W · · W c W A ·` | **WAIT** 5w 1a 3n 1c /10 | `W · W · · c p W A ·` | **WAIT** 3w 1a 4n 1c /9 |
| 09-24 13:57 | SENSEX 73800 PE BUY @267.4 ‡ | `W W W · · W c W A ·` | **WAIT** 5w 1a 3n 1c /10 | `W · W · · c p W A ·` | **WAIT** 3w 1a 4n 1c /9 |
| 09-24 14:23 | SENSEX 73800 PE BUY @287.45 ‡ | `W W W · · A c W A ·` | **WAIT** 4w 2a 3n 1c /10 | `W · W · · c p W A ·` | **WAIT** 3w 1a 4n 1c /9 |

**Words over the 51.**
- Rev 2: GO 2 · WAIT 41 · NO 8.
- Rev 3: GO 2 · WAIT 46 · NO 3.

**Seven entries changed word:**
- 6 Oct 10:02 SELL PE: WAIT → NO. Effort read an expensive fresh high (2.05×), so ORDER FLOW is AGAINST, alongside INSTRUMENT.
- 6 Oct 10:03 BUY PE: NO → WAIT. The same expensive high is WITH a short.
- 1 Oct 12:06 SENSEX PE, and 24 Sep 10:19, 13:41, 13:43 and 13:44 SENSEX PEs: NO → WAIT.
  - In all five, rev 2's AGAINST came from a fight on the thin SENSEX futures. Rev 3 does not read that tape: ORDER FLOW is "could not check — patla".
  - **So on SENSEX, rev 3 is more permissive than rev 2.** That is by design (A25, Fable), and it is worth her eye.

**The two GOs stayed GO:**
- 1 Oct 10:02 SENSEX CE: 7 with of 9.
- 24 Sep 12:44 SENSEX PE: 6 with of 9.
- On both, the meter or a SENSEX "pop ?" stood where rev 2 had more WITH.

## Her 22 Oct 13:00 SENSEX 73400 CE: rev 3 does not say NO, and why (reported, not tuned)

- **Rev 2 was WAIT, not GO:** 5 with, 2 against.
  - ORDER FLOW was against: sellers won 13:00 at 73,735f.
  - ROOM was against: the stop was 324 pts away, the wall 45.
  - PAYING counted WITH: CE 73500 UNWINDING, 35.4 % off its 12:49 peak.
- **Rev 3 is WAIT too:** 5 with, 1 against, 2 neither, 1 could not check, of 9. ROOM is the only AGAINST.
- **#10 PAYING did not fire the spent pop.** At 13:00 the price was not at a fresh extreme:
  - the 30-min high was 73,575.1 spot at 12:55;
  - spot was 73,455.2 at 13:00, 120 pts under it (more than ¼ step, 25 pts).
  - So the pop had already rolled over five minutes before her entry, and FRESH (§1) is false.
  - Even at 12:55 it could not have fired. DECODE did carry an EXHAUST on SENSEX then (the 12:50 bar's new high was printed on the other side's delta, ratio −1.68), but rev 3 does not read SENSEX tape (patla, §1, decided before the replay).
- **#2 DAY / TREND said NEITHER.** The meter was CHOP (DECODE 12:55), but the day's 1σ was only 38 % used her way:
  - 09:20 ATM straddle 557.1 on expiry day → 1σ 696 pts;
  - spot +264 from 09:20.
  - So the "≥ 90 % used" row did not apply.
- **#6 ORDER FLOW lost an AGAINST.** Rev 2's "sellers won 13:00" became "could not check — SENSEX fut patla".
- **What would have read her entry:**
  - the covering pop's *top* at 12:55, with a fresh-extreme test that also accepts an entry within a few minutes of the high;
  - a SENSEX tape read (or its peers' tape: NIFTY's 12:55 effort was 1.0×, normal).
  - Both are new rules. They are named as candidates in the NOTEPAD (A50), not built.

## Her 21 Oct 23000 PE (10:07:30, 174.85)

- WAIT in both: rev 2 6 with, 1 against; rev 3 5 with, 1 against of 9. VPIN's WITH left the count; ROOM is the AGAINST.
- ORDER FLOW is WITH in both, for different reasons:
  - rev 2: sellers won 10:05;
  - rev 3: a cheap fresh low, 0.37× the day's lots per point at 10:04 (the continuation read).
  - The quadrant would have said long liquidation, NEITHER.
- The meter was MIXED at 10:05 (A37: TREND came at 12:15), so DAY / TREND stayed NEITHER.

## Per-check notes across the 51

- **DAY / TREND.**
  - Where the expected move could be read (the 23 entries from 29 Sep to 22 Oct; the 22–24 Sep records carry no expiry), it never reached ±90 % her way. The largest were 85 % (6 Oct 14:12, the meter said TREND ▲, so WITH) and 83 % (5 Oct 12:09, MIXED). The 0.90 row never fired in her record.
  - The meter replaced the IB row's TREND ▼ with CHOP / PIN on 1 Oct SENSEX 12:22 / 12:27 and 24 Sep SENSEX 12:32 / 12:35 / 12:44 / 13:41–13:44, so WITH became NEITHER. That is A37's sticky CHOP.
  - It added TREND ▲ on 23 Sep SENSEX 11:32 and 6 Oct 14:12.
- **WALL BEHIND / AHEAD.**
  - ROLLING fired once: 6 Oct 14:12, the wall ahead 22700→22800 CE (−3.1× / +3.0×). It voted NEITHER, as before.
  - It read "roll ?" (no pace before ~09:55) on 12 entries; the base vote stood.
  - "building" now reads "defending" when there is no roll.
- **ORDER FLOW.**
  - Effort decided 3 entries: 21 Oct cheap low (WITH); 6 Oct 10:02 / 10:03 expensive high 2.05× (AGAINST the SELL PE, WITH the BUY PE).
  - The quadrant decided 5: 5 Oct 09:28 new longs WITH, and 22 Sep 10:32–10:44 new shorts WITH her PEs.
  - Covering or liquidation read NEITHER where it was the vote.
  - Before 09:56, effort could not check. In the futures record's first 10 minutes there is no 10-min OI change either, so the whole check was could not check.
  - All SENSEX entries: could not check.
- **VPIN** is printed on every row and counted on none.
- **PAYING.** The spent pop fired on none of the 51. On 11 SENSEX entries the payers were covering at a fresh extreme, but the tape could not be read: "pop ?".
  - 1 Oct: 10:02, 12:10 ×2, 12:22, 12:27.
  - 24 Sep: 10:19, 12:35, 13:41, 13:43, 13:44, 13:45.
  - **This is the rule's largest blind spot in her record:** her SENSEX covering pops. It is the same gap as the 22 Oct CE.

## Per trade, the checks that changed (cell rev 2 → rev 3; VPIN omitted, it changed on every row)

- **2026-10-22 13:00:00 SENSEX 73400 CE BUY** (NOTEPAD 22 Oct 13:00): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "TWO-SIDED since 11:30" → NEITHER "CHOP · EM 38% chal chuka"
  - ORDER FLOW: AGAINST "sellers won 13:00 @73,735f" → CNC "SENSEX fut patla"
- **2026-10-21 10:07:30 NIFTY 23000 PE BUY** (marked): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM 35% chal chuka"
  - WALL BEHIND: WITH "23000 CE 121L building" → WITH "23000 CE 121L defending"
  - ORDER FLOW: WITH "sellers won 10:05 @23,028f" → WITH "low 0.4× sasta"
- **2026-10-06 09:35:50 NIFTY 22600 CE SELL** (marked): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM -14% chal chuka"
  - WALL BEHIND: WITH "22650 CE 164L building" → WITH "22650 CE 164L defending · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 +390" → NEITHER "fut OI flat · effort ?"
- **2026-10-06 10:02:51 NIFTY 22650 PE SELL** (marked): rev 2 WAIT → rev 3 NO
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM 43% chal chuka"
  - ORDER FLOW: WITH "buyers won 10:00 @22,742f" → AGAINST "high 2.0× mehenga"
- **2026-10-06 10:03:21 NIFTY 22650 PE BUY** (marked): rev 2 NO → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM -43% chal chuka"
  - ORDER FLOW: AGAINST "buyers won 10:00 @22,742f" → WITH "high 2.0× mehenga"
- **2026-10-06 14:12:07 NIFTY 22600 CE BUY** (marked): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "PIN/CHOP since 13:25" → WITH "TREND ▲ · EM 85% chal chuka"
  - WALL AHEAD: NEITHER "22750 CE 305L flat · 29 pts" → NEITHER "22700→22800 CE roll · 29 pts"
  - ORDER FLOW: WITH "buyers won 14:10 @22,814f" → NEITHER "chaal nahi · effort 0.8×"
- **2026-10-05 09:28:13 NIFTY 22600 CE BUY** (marked): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM 5% chal chuka"
  - WALL BEHIND: WITH "22550 PE 84L building" → WITH "22550 PE 84L defending · roll ?"
  - WALL AHEAD: NEITHER "22600 CE 153L flat · 36 pts" → NEITHER "22600 CE 153L flat · 36 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 +44,980" → WITH "naye long · effort ?"
- **2026-10-05 09:35:06 NIFTY 22550 CE BUY** (marked): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM 18% chal chuka"
  - WALL BEHIND: WITH "22550 PE 109L building" → WITH "22550 PE 109L defending · roll ?"
  - WALL AHEAD: NEITHER "22600 CE 154L flat · 14 pts" → NEITHER "22600 CE 154L flat · 14 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 +62,010" → NEITHER "short covering · effort ?"
- **2026-10-05 12:09:58 NIFTY 22550 PE BUY** (marked): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "TWO-SIDED since 12:05" → NEITHER "MIXED · EM 83% chal chuka"
  - ORDER FLOW: WITH "sellers won 12:00 @22,570f" → NEITHER "fut OI flat · effort 1.3×"
- **2026-10-05 13:41:38 NIFTY 22650 PE SELL** (marked): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "TWO-SIDED since 13:40" → NEITHER "MIXED · EM -5% chal chuka"
  - ORDER FLOW: WITH "buyers won 13:40 @22,613f" → NEITHER "fut OI flat · effort 0.8×"
- **2026-10-01 09:21:04 NIFTY 22600 PE BUY** (import): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM 6% chal chuka"
  - WALL BEHIND: WITH "22600 CE 54L building" → WITH "22600 CE 54L defending · roll ?"
  - WALL AHEAD: NEITHER "22500 PE 89L building · 44 pts" → NEITHER "22500 PE 89L building · 44 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 -34,645" → CNC "fut OI ? · effort ?"
- **2026-10-01 09:26:45 NIFTY 22600 PE BUY** (import): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM 20% chal chuka"
  - WALL BEHIND: WITH "22600 CE 63L building" → WITH "22600 CE 63L defending · roll ?"
  - WALL AHEAD: NEITHER "22500 PE 90L flat · 22 pts" → NEITHER "22500 PE 90L flat · 22 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 -33,280" → CNC "fut OI ? · effort ?"
- **2026-10-01 09:30:46 SENSEX 72400 CE BUY** (import): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM 1% chal chuka"
  - WALL BEHIND: WITH "72300 PE 32L building" → WITH "72300 PE 32L defending · roll ?"
  - WALL AHEAD: NEITHER "72400 CE 30L flat · 37 pts" → NEITHER "72400 CE 30L flat · 37 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 -280" → CNC "SENSEX fut patla"
- **2026-10-01 10:00:48 SENSEX 72400 CE BUY** (import): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM 19% chal chuka"
  - ORDER FLOW: WITH "buyers won 09:50 @72,922f" → CNC "SENSEX fut patla"
- **2026-10-01 10:02:20 SENSEX 72400 CE BUY** (import): rev 2 GO → rev 3 GO
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM 29% chal chuka"
  - WALL BEHIND: WITH "72400 PE 40L building" → WITH "72400 PE 40L defending"
  - ORDER FLOW: WITH "buyers won 09:50 @72,922f" → CNC "SENSEX fut patla"
  - PAYING: WITH "73000 leaving · 72800 leaving" → WITH "73000 leaving · 72800 leaving · pop ?"
- **2026-10-01 12:06:38 SENSEX 72400 PE BUY** (import): rev 2 NO → rev 3 WAIT
  - DAY / TREND: NEITHER "TWO-SIDED since 10:20" → NEITHER "PIN · EM 11% chal chuka"
  - WALL BEHIND: WITH "72400 CE 58L building" → WITH "72400 CE 58L defending"
  - ORDER FLOW: AGAINST "buyers won 11:45 @72,976f" → CNC "SENSEX fut patla"
- **2026-10-01 12:10:13 SENSEX 72400 PE BUY** (import): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "TWO-SIDED since 10:20" → NEITHER "PIN · EM 18% chal chuka"
  - ORDER FLOW: AGAINST "buyers won 11:45 @72,976f" → CNC "SENSEX fut patla"
  - PAYING: WITH "72000 leaving · 72200 leaving" → WITH "72000 leaving · 72200 leaving · pop ?"
- **2026-10-01 12:10:20 SENSEX 72300 PE BUY** (import): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "TWO-SIDED since 10:20" → NEITHER "PIN · EM 24% chal chuka"
  - ORDER FLOW: AGAINST "buyers won 11:45 @72,976f" → CNC "SENSEX fut patla"
  - PAYING: WITH "72000 leaving · 72200 leaving" → WITH "72000 leaving · 72200 leaving · pop ?"
- **2026-10-01 12:19:41 SENSEX 72300 PE BUY** (import): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "TWO-SIDED since 10:20" → NEITHER "CHOP · EM 27% chal chuka"
  - ORDER FLOW: NEITHER "quiet · CVD15 -80" → CNC "SENSEX fut patla"
- **2026-10-01 12:22:35 SENSEX 72300 PE BUY** (import): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 12:20" → NEITHER "CHOP · EM 33% chal chuka"
  - ORDER FLOW: NEITHER "quiet · CVD15 +60" → CNC "SENSEX fut patla"
  - PAYING: WITH "72000 leaving · 71500 flat" → WITH "72000 leaving · 71500 flat · pop ?"
- **2026-10-01 12:27:39 SENSEX 72300 PE BUY** (import): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 12:20" → NEITHER "CHOP · EM 46% chal chuka"
  - WALL BEHIND: WITH "72300 CE 50L building" → WITH "72300 CE 50L defending"
  - ORDER FLOW: WITH "sellers won 12:25 @72,673f" → CNC "SENSEX fut patla"
  - PAYING: WITH "72000 leaving · 71500 flat" → WITH "72000 leaving · 71500 flat · pop ?"
- **2026-09-30 10:10:12 NIFTY 22750 CE BUY** (marked): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "PIN · EM 21% chal chuka"
  - ORDER FLOW: WITH "buyers won 09:55 @22,825f" → NEITHER "chaal nahi · effort 1.4×"
- **2026-09-29 09:18:07 NIFTY 22800 PE BUY** (marked): rev 2 NO → rev 3 NO
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "EARLY · EM ? chal chuka"
  - WALL BEHIND: WITH "22800 CE 137L building" → WITH "22800 CE 137L defending · roll ?"
  - WALL AHEAD: AGAINST "22700 PE 163L building · 16 pts" → AGAINST "22700 PE 163L building · 16 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 -5,070" → CNC "fut OI ? · effort ?"
- **2026-09-22 09:42:51 NIFTY 23300 CE BUY** (tradebook exp 2026-09-22; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM ? chal chuka"
  - WALL BEHIND: WITH "23450 PE 236L building" → WITH "23450 PE 236L defending · roll ?"
  - WALL AHEAD: NEITHER "23500 CE 335L flat · 47 pts" → NEITHER "23500 CE 335L flat · 47 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 -9,620" → NEITHER "chaal nahi · effort ?"
- **2026-09-22 10:32:42 NIFTY 23550 PE BUY** (tradebook exp 2026-09-22; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "TWO-SIDED since 10:20" → NEITHER "MIXED · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 10:20 @23,466f" → WITH "naye short · effort 0.8×"
- **2026-09-22 10:42:10 NIFTY 23550 PE BUY** (tradebook exp 2026-09-22; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 10:35" → WITH "TREND ▼ · EM ? chal chuka"
  - WALL BEHIND: WITH "23400 CE 268L building" → WITH "23400 CE 268L defending"
  - ORDER FLOW: WITH "sellers won 10:40 @23,419f" → WITH "naye short · effort 1.4×"
- **2026-09-22 10:43:03 NIFTY 23550 PE BUY** (tradebook exp 2026-09-22; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 10:35" → WITH "TREND ▼ · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 10:40 @23,419f" → WITH "naye short · effort 1.4×"
- **2026-09-22 10:44:10 NIFTY 23550 PE BUY** (tradebook exp 2026-09-22; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 10:35" → WITH "TREND ▼ · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 10:40 @23,419f" → WITH "naye short · effort 1.4×"
- **2026-09-22 10:52:56 NIFTY 23500 PE BUY** (tradebook exp 2026-09-22; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 10:35" → WITH "TREND ▼ · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 10:45 @23,397f" → NEITHER "fut OI flat · effort 1.4×"
- **2026-09-22 13:48:38 NIFTY 23500 PE BUY** (tradebook exp 2026-09-22; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 10:35" → WITH "TREND ▼ · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 13:25 @23,349f" → NEITHER "fut OI flat · effort 0.7×"
- **2026-09-23 09:18:03 NIFTY 23450 CE BUY** (tradebook exp 2026-09-29; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "EARLY · EM ? chal chuka"
  - WALL BEHIND: WITH "23300 PE 80L building" → WITH "23300 PE 80L defending · roll ?"
  - WALL AHEAD: NEITHER "23400 CE 85L flat · 8 pts" → NEITHER "23400 CE 85L flat · 8 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 +7,345" → CNC "fut OI ? · effort ?"
- **2026-09-23 09:47:57 NIFTY 23450 CE BUY** (tradebook exp 2026-09-29; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM ? chal chuka"
  - WALL BEHIND: NEITHER "23350 PE 57L flat" → NEITHER "23350 PE 57L flat · roll ?"
  - WALL AHEAD: NEITHER "23400 CE 131L flat · 16 pts" → NEITHER "23400 CE 131L flat · 16 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 +715" → NEITHER "chaal nahi · effort ?"
- **2026-09-23 09:49:26 NIFTY 23400 PE BUY** (tradebook exp 2026-09-29; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM ? chal chuka"
  - WALL BEHIND: NEITHER "23400 CE 130L flat" → NEITHER "23400 CE 130L flat · roll ?"
  - WALL AHEAD: NEITHER "23350 PE 58L flat · 16 pts" → NEITHER "23350 PE 58L flat · 16 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 +2,275" → NEITHER "chaal nahi · effort ?"
- **2026-09-23 10:00:41 NIFTY 23450 CE BUY** (tradebook exp 2026-09-29; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM ? chal chuka"
  - ORDER FLOW: NEITHER "quiet · CVD15 -11,895" → NEITHER "fut OI flat · effort ?"
- **2026-09-23 10:19:52 NIFTY 23450 CE BUY** (tradebook exp 2026-09-29; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM ? chal chuka"
  - ORDER FLOW: NEITHER "quiet · CVD15 +1,495" → NEITHER "fut OI flat · effort ?"
- **2026-09-23 10:33:44 NIFTY 23450 CE BUY** (tradebook exp 2026-09-29; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "TWO-SIDED since 10:20" → NEITHER "MIXED · EM ? chal chuka"
  - ORDER FLOW: WITH "buyers won 10:20 @23,414f" → NEITHER "chaal nahi · effort 1.5×"
- **2026-09-23 11:07:37 NIFTY 23450 CE BUY** (tradebook exp 2026-09-29; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "TWO-SIDED since 10:20" → NEITHER "MIXED · EM ? chal chuka"
  - ORDER FLOW: WITH "buyers won 10:40 @23,438f" → NEITHER "fut OI flat · effort 0.7×"
- **2026-09-23 11:32:24 SENSEX 74900 CE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "PIN/CHOP since 11:30" → WITH "TREND ▲ · EM ? chal chuka"
  - ORDER FLOW: WITH "buyers won 11:30 @74,847f" → CNC "SENSEX fut patla"
- **2026-09-24 09:42:43 SENSEX 74200 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM ? chal chuka"
  - WALL BEHIND: NEITHER "74200 CE 31L flat" → NEITHER "74200 CE 31L flat · roll ?"
  - WALL AHEAD: WITH "74100 PE 25L leaving · 88 pts" → WITH "74100 PE 25L leaving · 88 pts · roll ?"
  - ORDER FLOW: NEITHER "quiet · CVD15 +100" → CNC "SENSEX fut patla"
- **2026-09-24 10:19:11 SENSEX 74200 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 NO → rev 3 WAIT
  - DAY / TREND: NEITHER "EARLY since 09:15" → NEITHER "MIXED · EM ? chal chuka"
  - ORDER FLOW: AGAINST "buyers won 10:10 @74,211f" → CNC "SENSEX fut patla"
  - PAYING: WITH "74000 leaving · 74100 flat" → WITH "74000 leaving · 74100 flat · pop ?"
- **2026-09-24 12:32:32 SENSEX 74100 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 12:30" → NEITHER "PIN · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 12:20 @74,091f" → CNC "SENSEX fut patla"
- **2026-09-24 12:35:18 SENSEX 74000 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 12:30" → NEITHER "PIN · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 12:20 @74,091f" → CNC "SENSEX fut patla"
  - PAYING: WITH "73800 leaving · 73900 leaving" → WITH "73800 leaving · 73900 leaving · pop ?"
- **2026-09-24 12:44:46 SENSEX 74000 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 GO → rev 3 GO
  - DAY / TREND: WITH "TREND ▼ since 12:30" → NEITHER "PIN · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 12:40 @74,007f" → CNC "SENSEX fut patla"
- **2026-09-24 13:26:41 SENSEX 74000 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 NO → rev 3 NO
  - DAY / TREND: NEITHER "TWO-SIDED since 12:50" → NEITHER "PIN · EM ? chal chuka"
  - ORDER FLOW: NEITHER "quiet · CVD15 -260" → CNC "SENSEX fut patla"
- **2026-09-24 13:41:38 SENSEX 73900 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 NO → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 13:30" → NEITHER "CHOP · EM ? chal chuka"
  - ORDER FLOW: AGAINST "buyers won 13:35 @73,932f" → CNC "SENSEX fut patla"
  - PAYING: WITH "73800 leaving · 73500 flat" → WITH "73800 leaving · 73500 flat · pop ?"
- **2026-09-24 13:43:44 SENSEX 73900 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 NO → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 13:30" → NEITHER "CHOP · EM ? chal chuka"
  - ORDER FLOW: AGAINST "buyers won 13:35 @73,932f" → CNC "SENSEX fut patla"
  - PAYING: WITH "73800 leaving · 73500 leaving" → WITH "73800 leaving · 73500 leaving · pop ?"
- **2026-09-24 13:44:09 SENSEX 73900 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 NO → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 13:30" → NEITHER "CHOP · EM ? chal chuka"
  - ORDER FLOW: AGAINST "buyers won 13:35 @73,932f" → CNC "SENSEX fut patla"
  - PAYING: WITH "73800 leaving · 73500 leaving" → WITH "73800 leaving · 73500 leaving · pop ?"
- **2026-09-24 13:45:56 SENSEX 73800 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 13:30" → NEITHER "CHOP · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 13:45 @73,836f" → CNC "SENSEX fut patla"
  - PAYING: WITH "73500 leaving · 73700 leaving" → WITH "73500 leaving · 73700 leaving · pop ?"
- **2026-09-24 13:54:47 SENSEX 73800 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 13:30" → NEITHER "CHOP · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 13:50 @73,745f" → CNC "SENSEX fut patla"
- **2026-09-24 13:57:49 SENSEX 73800 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 13:30" → NEITHER "CHOP · EM ? chal chuka"
  - ORDER FLOW: WITH "sellers won 13:55 @73,721f" → CNC "SENSEX fut patla"
- **2026-09-24 14:23:31 SENSEX 73800 PE BUY** (tradebook exp 2026-09-24; chain exp null): rev 2 WAIT → rev 3 WAIT
  - DAY / TREND: WITH "TREND ▼ since 13:30" → NEITHER "CHOP · EM ? chal chuka"
  - ORDER FLOW: AGAINST "buyers won 14:15 @73,676f" → CNC "SENSEX fut patla"
