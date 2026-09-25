# Third review: `docs/hold/PREREG-merged.md` rev 3 (Opus)

Written 2026-09-25 01:37 IST, read from the clock. I checked it against the
rev 3 text (file mtime 01:34:56) and re-ran my literal probe
(`scratch/xreview/prereg_probe.js rev2`, updated for rev 3's writer clause).

## N1–N5

| | status | check |
|---|---|---|
| **N1** trend / pinned day | **resolved** | Defined by §10's own side vote, on **more than** half of readable minutes, with no new number. Disclosed as a post-hoc check against the reference days. My facts agree: SENSEX 09-24 PUTS 94 %; NIFTY 09-24 PUTS 88 % on my [I] candles (91 % on theirs); NIFTY 09-23 no side 62 %; SENSEX 09-23 55 %. BANKNIFTY 09-24 is named as the edge case. Computable from `side_<day>.jsonl` (`side` per minute; "could not check" minutes excluded). |
| **N2** a per-index minute log | **resolved** | `side_<day>.jsonl` has one row per minute per index, flat or not, written live and completed by the import. The day labels and the side stamps (`stamp`) are computable from it. |
| **N3** logging horizon | **resolved** | Every trade is logged to 15:29, with `after_exit` flagged, so her exits cannot censor the stamps. Clause 3's "in-trade minutes" are the rows with `after_exit: false`. No new defect, apart from the small note below on stamps after 14:59. |
| **N4** OI half double-counted | **resolved** | Printed as a summary line, not counted. Three facts. |
| **N5** undefined words | **resolved** | `fold_rule` (3, 4, 5, 6) is in the trade row, so clause 5 reads directly. "Collapses" = clause 1 reverses. "Reversal" = the read names the other side, or no side, within 15 minutes. |

The probe's verdicts are unchanged from rev 2. Rev 3's writer clause (S-a: when
`dpx` is blind, rule 4 is unavailable for her) changes no row: the writer
examples all start after the ladder window exists.

## One new defect, and it blocks signing

The side falsifier cannot be computed as specified. The side log stores
`atm: {ce_px, pe_px}` at each minute's own ATM strike, with **no strike**. The
falsifier needs the excursion of *the stamp-minute ATM option* over the next 30
minutes. When spot moves, per-minute "ATM" prices splice different contracts
together, and the result is fake excursions.

On SENSEX 09-24, NIFTY 09-23 and NIFTY 09-22, **the ATM strike changed within
30 minutes after 9 of the 21 side stamps.** §8 also says §10.6 is answered
"from these rows and nowhere else".

## Verdict: **NOT YET**

The one line that blocks signing:

- **Add `atm.k` to the side-log row, and on each `stamp` row log that strike's
  CE and PE prices for the next 30 minutes** (or let §10.6 read that one strike
  from the chain record, and amend "nowhere else"). With that, sign.

Not blocking; fix when convenient:
- **Late stamps.** A stamp after 14:59 has a window shorter than 30 minutes.
  Say "to 15:29, flagged".
- **"With-trend trade" in clause 3 / B5.** Say "her side agrees (10.4) with the
  day's majority side".
- **Expiry line.** The frame head exists only while the GoCharting extension
  posts. Fall back to the chain poller's resolved expiry on days with no frame
  and no trade.
