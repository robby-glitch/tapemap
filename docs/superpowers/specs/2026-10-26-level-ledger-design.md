# LEVEL LEDGER: one support/resistance object on real data (DRAFT for her signature, 2026-10-26)

## Origin (verbatim)
- **Mary, 26 Oct ~19:50**, after the BigBeluga "Volume Delta Pivot Matrix" check (NOTEPAD A113): "but we can make it
  better with real data how it should be write a very strong support and resistance right with correct data"
- **Mary, 26 Oct ~20:15:** "Yes, write the LEVEL ledger spec for my signature."
- **Her OI reading rule** (oi-liquidity-hunt thesis, 22 Sep, verbatim): "hamesha read nearest ATM pe rehni chahiye …
  Hamesha check karo the strike with most of OI and second best on both sides, and always check which side stops first
  increasing their positions and then unwinding."
- **Her playbook:** reaction points (PDH/PDL, weekly high/low, round numbers); dwell; stops as liquidity; the run to the
  next reaction point.

## Why one ledger, not a new indicator (NOTEPAD A114)
- **Too many level objects already.** TapeMap and the chart draw about 20 kinds of level, with about 8 OI-wall definitions
  and 5 test and 5 break definitions. **None is graded.**
- **What the 38 recorded days measured** (oi-lab, descriptive, in-sample):
  - Plain touches of PD levels, VWAP, VA/POC and OI walls were noise.
  - The **futures leg at the touch** separated holds from breaks.
  - **Effort per point** survived two holdouts.
  - **OI composition** at the extreme did not separate holds from breaks.
- **BigBeluga's flaw:** its pivots are known only after the fact (look-ahead), and its "delta" is candle shape. On
  26 Oct it had the opposite sign to the real footprint on 23 of 75 NIFTY 5-min bars.

**So the ledger generates no new levels.** It gives each existing reaction point one identity, judges every test live
with the reads that measured, keeps one state machine, draws only the nearest levels, and logs every test forward to be
graded.

## 1. Sources (consumed, never changed)
A source proposes a price. Sources within one **band** of each other become **one level** that lists all of them.

| Source | From | Frame |
|---|---|---|
| PDH / PDL / PDC | `levels.fetch_daily` (1-min bars ≤ 15:15, the CAS rule) | index → fut |
| PWH / PWL | `levels.py` (A114 notes they include the auction print; consumed as they are) | index → fut |
| Day high / low (once left by 2 bands: a past extreme, never the price being made now) | the session's own 1-min futures bars | fut |
| DEEWAR | the extension's qualified walls (`/api/frame` `walls`) | fut |
| Naked POC | `prints.py` (prior sessions' untouched POC) | fut |
| OI wall | `fronts.py` (§1d): top 2 by peak OI among the 9 strikes nearest spot, each side | strike → fut |
| Round | 100s only, within 0.8 % of price (`levels.py` ROUND) | index → fut |

- **Level price:** the first of these present in the merged level: PD/PW → day H/L → DEEWAR → naked POC → OI wall →
  round.
- **Frame:** futures. Every level is shown `fut|spot` through **one basis**: `fold.BIX_MS`, her display basis, a 3-min
  median (A60).
- **Band:** the war map's dwell band, 2 × the median 1-min move (`dwell.py`), live per index. It merges sources, defines
  the touch, and debounces tests.
- **Zone context:** the 3-min zone pocket (d2→d3, u2→u3; ZONE-3M from 28 Oct, the 1-min zone before) is a tag on a
  test ("zone mein"), never a source, because it moves every bar.

## 2. Role and the state machine (one definition, replacing the five)
- **Role:** support when the level is below price at birth, resistance when above. It flips only through FLIPPED.
- **TEST begins:** a 1-min bar trades within one band of the level from the defending side, after price has been at
  least 2 bands away since the last test. The first touch is a test.
- **TEST ends:** price leaves by 2 bands. The outcome is one of:

| Outcome | Rule | Chip |
|---|---|---|
| **HELD** | left on the defending side, no BREAK | `N test tika` |
| **STOP-HUNT** | traded more than 1 band beyond, but never 3 consecutive minutes beyond, then left on the defending side | `stop hunt` |
| **BROKEN** | 3 consecutive 1-min bars entirely beyond the level by ≥ 1 band (acceptance by time and distance, not a single close) | `TOOTI` |
| **FLIPPED** | a BROKEN level later HELD from the other side; its role flips | `palti` |

- **The state** is FRESH (no test yet), TESTED n, or the last outcome.
- **A BROKEN level** not flipped within 60 minutes leaves the face; it stays in the log.
- **Levels reset** each session; their sources re-derive (PD/PW, naked POC and OI walls carry over by their own rules).

## 3. The four families, read at each test (the count)
Each family is read **causally at the test's deepest minute**. Each answers **FOR** (defends the level), **AGAINST**, or
**?** (could not read, with the reason; it never counts either way). **The count is FOR families out of 4**; AGAINST
families are shown beside it: `3/4 · 1 khilaaf`. Never a %.

| Family | Definition (reused, not new) | FOR | AGAINST |
|---|---|---|---|
| **FUT LEG** [M] | oi-lab DETECTOR §3: futures ΔOI over W = 10 min (\|ΔOI\| < 0.15 % = "fut OI flat"); the 5-min bar's delta/volume (> +10 % buyers hitting, < −10 % sellers hitting). Roll-week negative ΔOI = "?" | resistance: fut OI flat + buyers hitting · support: new shorts + sellers hitting | resistance: new longs + buyers hitting · support: fut OI flat + sellers hitting |
| **EFFORT** [I] | `effort.py`, Fable's lots per point at a fresh extreme (NIFTY, BANKNIFTY; from 09:56). A test that is not at `effort.py`'s fresh extreme reads "?" | resistance at a fresh high: ≥ 2× the day median (mehenga) | support at a fresh low: ≤ 0.5× (sasta) |
| **OI SEQ** [I] | `fronts.py` (§1d), her rule: the defending side's (PE for support, CE for resistance) top-2 near-ATM front, if it is among the 3 strikes nearest the level (DETECTOR's band); else "?" | BUILDING | STALLED or UNWINDING ("the side that stops first … then unwinding" is forced) |
| **TRAPPED** [M] | the fold engine's `trapped` marks (not yet `released`) within one band of the level | resistance: buyers trapped at it · support: sellers trapped at it | none |

- **Where the reads come from:**
  - The FOR / AGAINST cells of FUT LEG are AUDIT_OI's measured cells (38 days: 66/93, 9/24, 23/41, 44/111). These
    numbers live in that file, never on a face (rule 4).
  - EFFORT's mirrors failed in Fable's audit, so they read "?" ("read nahi").
- **OI SEQ is in the count because it is her method (§1d).** OI composition at extremes did not separate holds from
  breaks on 38 days. Its forward record decides whether it keeps its vote (§6).
- **Stamped on every test, not counted:** DTE to the option expiry (defence held near expiry and broke far from it,
  AUDIT_OI), and "zone mein".

## 4. Indices
- **NIFTY and BANKNIFTY:** all four families.
- **SENSEX:** sources and OI SEQ are its own. FUT LEG, EFFORT and TRAPPED read "?" with "SENSEX flow = NIFTY's (§1q),
  not mapped to SENSEX levels in v1". SENSEX futures are too thin to read on their own (A25).

## 5. What she sees (display only)
- **Her GoCharting chart (the extension):** only the **nearest 2 levels above and 2 below**, one line each, one chip:
  `KHARIDAR KI DEEWAR 22,500f|22,422s · 3/4 · put likh rahe · fut OI flat · 2 test tika`
  `BECHNE WALE KI DEEWAR 22,800f|22,782s · 1/4 · 2 khilaaf · calls bhaag rahe · taaza`
  - The ledger's lines **replace** today's DEEWAR lines and PDH/PDL/PDC lines; those two become ledger sources.
  - Marks stay as they are: R/Z, BADA print, P, PUSH and the TOOTI cross.
- **ui-v2 Trade tab:** a LEVELS grid with every live ledger level and columns `fut|spot · role · sources · state · n/4 ·
  khilaaf · last test`.
- **Not in v1:** no Telegram, no stream line, no gate on any setup.

## 6. The record and its grading (stack doctrine: kill conditions at birth)
- **Forward log** `data/levels/levels_<day>.jsonl`: one write-once row per resolved test, keyed (day, idx, level id,
  test start), with the level's `fut|spot` and sources, its role, the deepest price, the outcome, the four family
  answers, the count, DTE and the zone tag. No forward excursion is ever written on the row; a scorer measures that later.
- **Grading after 30 sessions** (`tools/levels_score.py`, built then), with the pass bar stated by her before reading
  (§5e). Under 15 tests per role is inconclusive. No hit rate is ever printed.
- **Kill rules:**
  - A family that does not separate HELD from BROKEN better than the bare touch leaves the count and is shown as
    context only.
  - If the count itself separates nothing, the face shows sources and states only.

## 7. Anytime start (the A106 / A107 pattern)
- **Sources** come from backfill: PD/PW, chain backfill for OI walls from 09:15, exchange 1-min candles for price.
- **Tests before the start** are rebuilt from the exchange 1-min candles: price, state and futures OI.
  - FUT LEG's delta part, EFFORT and TRAPPED read "?" there ("flow from HH:MM").
  - Rebuilt rows are tagged `rebuilt`, never blended with observed ones.

## 8. Architecture
- **`levels_ledger.py`** (new, pure, no I/O, no clock): merge sources into levels, run the test state machine over
  1-min bars, read the four families from inputs handed in, and produce the nearest-N view.
- **`server.py`:** gathers the inputs it already holds per index on its refresh, serves `GET /api/levels?idx=` and the
  frame field `levels`, and writes the forward log once per resolved test.
- **Extension:** draws `levels` from the frame, nearest 2 + 2; stops drawing DEEWAR and PD lines (they become sources).
- **ui-v2:** the Trade tab's LEVELS grid.

## 9. Not changed
- Registered setups §1b, §1d, §1i–§1r.
- The rules of `fronts.py`, the fold engine, the extension's DEEWAR detection, `levels.py`, `prints.py`, `effort.py`
  and `dwell.py`: all consumed as they are.
- DECODE, the stream, Telegram, trigger_log, the zone machine.

## 10. Acceptance (26 Oct, in-sample, described only, never tuned)
The build's replay of 26 Oct NIFTY prints the ledger's rows for:
- the 09:20–09:41 lows (22,440–22,487f);
- the 10:05 high (22,790f);
- the 12:45 low (22,611f);
- the 15:12 hold (22,753–22,760f).

Each row shows its sources, family answers, count and outcome, and is reported as is. No threshold above may be moved
because of what it shows.

## Signature
Hers: "commit — I sign" on this text, then the build plan (writing-plans), then the build on her word.
