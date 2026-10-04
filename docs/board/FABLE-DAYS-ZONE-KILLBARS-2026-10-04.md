# Other days, her band rotation, and the kill bars — Fable, 2026-10-04 (round 3)

Read-only. Nothing in the repo edited, nothing started; `data/trigger_log.jsonl` was read, never written. Probes in my
scratch area: `otherdays.py` (levels, warmap stamps, NIFTY tape), `zonejoin.py` (zone rows joined to the level state
and the sides slot). **[M]** measured on recorded rows; **[I]** inferred. Rows are described; no rate is printed.

**Data honesty up front.** Sides read: `docs/board/sides-all-sessions-rev3.txt` (frozen) for PUSHTI / forced / weekly;
the per-slot word beside each zone row comes from the analysis `sides.py` (rev 1: no forced, no kal scale) and says so.
Levels: `data/warmap/` from 24 Aug. NIFTY futures tape: GoCharting from 11 Sep, Upstox from 22 Sep; SENSEX and
BANKNIFTY futures never vote. Reader legs (WHO): 30 Sep and 1 Oct only. Fast VPIN: from 23 Sep. xindex: from 30 Sep.
So 25 Aug and 1 Sep are told from levels + option book + zone only, and say so.

---

## 1. The other days, as traps

Format per day: what trapped whom at which level → what led (levels / book) → what confirmed late (tape / VPIN /
xindex) → did the release travel or stop (WHO where the reader exists; otherwise the next level) → what the read
should have said.

### 25 Aug (Mon; NIFTY+BANKNIFTY expiry; gap −80 / −226 / −173) — three seller traps under PDL, released up
1. Gap-down under PDC; NIFTY ran to OPEN (BREAK → HIT 09:41–09:43) and then **PDL 24144 BREAK 10:20 → FAILED 10:48,
   BREAK 11:12 → FAILED 11:21, BREAK 13:13 → FAILED 13:53** [M]: three pokes under the previous day's low, three
   failures; SENSEX PDL the same at 10:23 → 10:47 and 13:14 → 13:54.
2. Dwell 10:20–13:50 at 24119–24210 with the book FLAT/QUIET in every slot (rev-1 words) [M]: nobody loaded; three
   sets of sellers were induced under PDL and each set's stops were the liquidity for the next poke.
3. Release: BANKNIFTY 13:55 SQUEEZE ▲ CE covering ×9.4 (PUSHTI); SENSEX 14:40 **REAL ▲ CE ×28 / PE ×19**; NIFTY 14:55
   REAL ▲ forced 2/2 [M]. PDC 24219 BREAK → HIT 14:52 (NIFTY), PDC 77369 HIT 14:52 (SENSEX); close at the high +196.
4. Led: the third PDL FAILED (13:53) and the BN call covering (13:55). Late: the weekly books' POWER came 14:40–14:55,
   when the leg was 100 points old. No tape on this date.
5. Travelled: to PDC and beyond into the close (expiry-day squaring of calls on NIFTY/BN is part of it: 0DTE).
6. The read should have said at 13:53: `PDL teen baar toota, teen baar FAILED · book flat · sellers phanse` — and at
   14:40 `release ▲ chal raha · agla PDC`.

### 1 Sep (Tue; NIFTY expiry; gap −46 / −529 / −74) — a buyer trap at PDH on all three
1. Morning drive down under PDL/PWL on NIFTY (23995 → 23955-area tests), then a walk up through the OPEN/PWL/PDC
   cluster (NIFTY BREAK 11:08–11:10 → HIT 11:20; SENSEX the same at 10:50–11:09) [M].
2. The induce: **SENSEX PDH 77177 BREAK 11:30 → FAILED 11:39, BREAK 12:07 → FAILED 12:23, DWELL 12:32; NIFTY PDH
   24129 DWELL 12:09** [M]. Day highs 11:30–11:31 on all three.
3. Book at the top: FAKE / CAPPED on every slot 11:00–12:15 (CE covering ×0.8–1.2 while **PE adding ×1.1–1.8**: put
   writers underwriting the top = the loaded side) [M].
4. Release: 13:10 NIFTY ▼ REAL, 13:15 SENSEX ▼ REAL forced 2/2 weekly 2/2, 13:20 BN ▼ REAL forced 2/2 (f30 −193) [M];
   PDC/OPEN/PWL BREAK → HIT 13:11–13:12, PDL 23994 HIT 14:09 (NIFTY), PDL 76751 HIT 14:08 (SENSEX).
5. Led: PDH FAILED (11:39, 12:23). Late: the POWER release 13:10–13:20, 50 minutes after the second failure.
   No tape on this date.
6. Travelled: PDH → PDL, the whole previous day's range, in 2.5 hours; a seller trap under PDL at 14:09 then bounced
   +100 into the close (zone BUY 14:27, §2).
7. Should have said at 12:23: `PDH do baar FAILED · PE writers likh rahe (loaded) · release ka intezaar`; at 13:15:
   `release ▼ forced 2/2 weekly 2/2 · agla PDC → PDL`.

### 11 Sep (Fri; gap −229 / −726 / −684, 145 under PDL) — sellers trapped at the gap, trend up all day
1. Opening low 09:41–09:42 (NIFTY 23240, 145 under PDL) [M]. GC CVD was **rising from the open (+379 by 09:25, +639 by
   10:20) while price went nowhere 23303–23363**: buyers pressing into sellers who absorbed — effort without result
   on the buy side during the OPEN dwell (OPEN DWELL → BREAK 10:08 → HIT 10:13) [M].
2. Release: 11:10 bar +766 lots `initiative+`, CVD +1,464, **futures OI +355 / +597 / +599 lots** (new longs);
   ROUND 23300 HIT 11:17; sides 11:15 ▲ REAL forced 2/2 weekly 2/2 on all three [M].
3. Travelled on new positions: PDL 23380 BREAK 14:00 → HIT 14:03, PDC 56472 HIT 14:02 (BN), PDH 56575 BREAK 14:48
   (BN). The 14:00 bar +563 lots came with **OI −772** (short covering) and the leg stopped at 23500 [M]: the last
   push was covering, not positioning, exactly the K-D distinction.
4. Led: the OPEN break (10:08–10:13) and the book (REAL at 10:15 on NIFTY/BN). Confirmed late: the 11:10 climax bar
   and the 11:15 POWER slot. No VPIN fast on this date.
5. Zone fired 36 times (23 SELL on a +149 / +860 day), §2.
6. Should have said at 10:13: `gap PDL ke neeche · OPEN toota upar · CVD upar, price flat (absorb) · sellers phanse`;
   at 11:15: `release ▲ naye long · agla PDL 23380`.

### 22 Sep (Tue; NIFTY expiry; gap +94 / +197 / +613, above PDH) — a buyer trap at PDH, released down to PDL
1. Gap up above the previous day's high on all three. **SENSEX PDH 74987 DWELL 09:46 → BREAK 10:09 → FAILED 10:22;
   NIFTY OPEN 23454 DWELL 09:53 → BREAK 10:00 → FAILED 10:22** [M]; day highs 10:09–10:11.
2. Tape at the failure: 10:20 `initiative−`, 10:30 climax 802 lots UX, 10:35–10:40 `initiative−` ×2 with
   **futures OI +566 / +258 / +173 lots → new shorts** [M]. Sides 10:30 SENSEX ▼ REAL forced 2/2 (witness), **10:35
   all three ▼ REAL forced 2/2 weekly 2/2** (f30 −38 / −88 / −124) [M].
3. Led: the FAILED stamps (10:22) and the 10:30 book. Confirmed: the tape 10:30–10:40 (same minutes), POWER at
   10:35. No VPIN fast on this date.
4. Travelled: PDC 23414 BREAK 10:39 → HIT 11:51; PDL 23315 BREAK 14:00 → **FAILED 14:11** (sellers trapped under
   PDL, +40 bounce into the close; 14:15–14:20 ▲ REAL/PRESSURE weekly 2/2) [M].
5. Into the close: UX −2,190 / −1,873 lots at 14:55–15:00 with **OI +2,541 / +2,043** and price flat 23367 → 23368:
   aggressive selling absorbed, new shorts trapped at the low [M]. 23 Sep opened +44 and never broke a level.
6. Should have said at 10:22: `PDH FAILED (SENSEX) · OPEN FAILED (NIFTY) · buyers phanse`; at 10:35: `release ▼
   forced 2/2 weekly 2/2 · naye short · agla PDC → PDL`; at 15:00: `PDL ke neeche selling absorb · kal ke liye
   sellers phanse`.

### 23 Sep (Wed; range; gap +44 / +145 / +179) — reached PDH, never broke: no trap sprung
1. All three stopped under PDH (NIFTY 23463 vs 23467; SENSEX −64; BN −43) at 12:19 [M]. Warmap: ROUND 23400 HIT 09:54
   (below) → DWELL 10:32 → HIT 11:47 (reclaimed); **no BREAK, no FAILED at any previous-day level** [M].
2. Steady put writing all morning (the grind the burst measure cannot see); UX CVD −2,600 by the close with price
   flat/up: sellers absorbed all day [M].
3. 15:00–15:15 put covering 3/3 ▼ at 0/9 underwater: squaring, not a release (framework §2.3).
4. Nothing led because nothing broke. The honest read all afternoon: `PDH pahuncha · ruka · koi break nahi · koi
   release nahi` — stand aside. The zone traded the range edges (§2).

### 24 Sep (Thu; SENSEX expiry; gap −210 / −826 / −603) — a three-hour dwell at OPEN, released down to the weekly low
1. Never near PDC. **OPEN 23222 DWELL 10:00 → BREAK 10:22 → FAILED 10:37 → DWELL 10:49, 11:30; ROUND 23200 DWELL 11:55 →
   FAILED 12:02 → DWELL 12:17** [M]. UX CVD −4,502 by 10:00 and −7,649 by 12:00 with price flat at 23220 ± 25:
   sellers absorbed for three hours while puts were written under the level [M].
2. Release order [M]: **ROUND 23200 HIT 13:26 and SENSEX PWL 73981 BREAK 13:26** (level) → **13:30 sides 3/3 ▼ PE
   covering ×8.7 / ×14.1 / ×8.4 on 9/9, forced 2/2** (book) → 13:35 `initiative−`, 13:40 climax 919 lots UX (tape) →
   VPIN fast ≥ 0.90 at 13:44–13:48 (late).
3. Travelled to the weekly low: NIFTY PWL 23116 BREAK 13:46 → HIT 13:58; low 23049 at 14:23; then +28. The leg's
   futures OI was roughly flat through 13:35–14:00 (−105, −84, +144, −15) [M]: liquidation, not new positioning,
   and it stopped at the target.
4. Should have said at 12:02: `OPEN FAILED · ROUND FAILED · teen ghante absorb · PE writers loaded`; at 13:30:
   `release ▼ forced 2/2 · covering only · agla PWL 23116 tak`.

### 25 Sep (Fri; gap +33 / +180 / +127) — chop at PDC, one small seller trap under PDL
1. PDC 23063 BREAK → HIT 09:52 and 10:04–10:08, BREAK 10:48 → **FAILED 11:02**, DWELL 12:08: the previous close was
   re-crossed five times [M]. No trend.
2. **PDL 23046 BREAK 12:56 → FAILED 13:11** (low 23029 at 12:57) [M]. Sides 12:55 NIFTY+SENSEX ▼ REAL forced 2/2
   weekly 2/2 (PUSHTI) with f30 −5 / −11 [M]: put writers covered **into the PDL break, and the break failed** — the
   covering was the sellers' induce, not a release (the one PUSHTI ▼ in these days that was a trap for shorts).
   Tape: 12:50 `initiative−` −489 GC, 12:55 UX −302 with **OI +497** then 13:15 `initiative−` −347: shorts entered
   under PDL [M].
3. Release up: PDC HIT 14:01, 14:05 UX **+2,781 lots** (block), ROUND 23100 HIT 14:06, high 23142 [M]; 14:05 ▲ REAL
   weekly 2/2 forced 2/2 fired **at the high** (f30 −8 / −16): a continuation at exhaustion.
4. Should have said at 13:11: `PDL toota, FAILED 15 min mein · sellers phanse · release ▲ aane wala`; at 14:05:
   `PDC wapas · ROUND 23100 HIT · fuel khatam`.

### 28 Sep (Mon; gap −170 / −554 / −522, 264 under PDL) — a trend day with no reaction point: no trap at a level
1. Every previous-day level was above the open. The only stamps all day: ROUND 22900 HIT 09:38 and ROUND 22800
   DWELL 14:23 → FAILED 14:53 [M].
2. Tape: 09:15 −1,227 `initiative−`; CVD −3,286 by 10:30 with price 22970 → 22881; then **three hours flat at
   22866–22895 with futures OI falling every bar (−400-ish): long liquidation absorbed**; VPIN fast ≥ 0.90 at
   09:56–10:20 only [M]. 14:15 climax −780 UX at ROUND 22800, low 22765 at 14:38, 14:45 `initiative+` +408 [M].
3. Sides: morning witnesses CAPPED forced 2/2 on all three (call writers selling the gap, in profit); 12:00 NIFTY ▼
   PRESSURE; 14:20 BN/SENSEX ▼ weekly 2/2 at the low (f30 +8 / +25) [M].
4. Nothing led because there was no level to trap at. The read should have said: `gap PDL se 264 neeche · koi
   reaction point nahi · trend · liquidation absorb ho rahi (OI gir rahi)` — and the BANKNIFTY regime note from the
   dead list: banks trend, they do not revert.

### 29 Sep (Tue; NIFTY+BANKNIFTY expiry; gap −67 / −158 / −240) — sellers trapped under PDL, covering-only release
1. All three broke PDL at the open (NIFTY low 22574, 191 under PDL); ROUND 22600 DWELL 09:48 → FAILED 10:43 → DWELL
   10:50, 11:06 [M]. UX CVD −3,758 by 10:00 with price flat; **futures OI −751 / −956 / −1,171 / −1,559 lots**:
   forced long liquidation, which ends when the longs are gone [M].
2. Release: 11:10 `initiative+` +1,671 lots; **11:15 3/3 ▲ REAL forced 2/2 weekly 2/2 (CE ×8.9 / ×8.8 / ×12.9)**;
   WHO on the leg: Δ +1,433 with **OI −470 → short covering** [M]. VPIN fast ≥ 0.90 09:25–11:26 (with the move).
3. Led: the liquidation drying up (OI change flattening 10:15–11:05) and the 11:10 bar. Confirmed: POWER at 11:15.
4. **Stopped at the next level:** OPEN 22732 BREAK 12:07 → **FAILED 12:20**; the 12:35 3/3 ▼ put covering was expiry
   squaring (4/9 underwater, tape buying), not a release [M].
5. Should have said at 11:15: `release ▲ · covering only (OI −470) · agle level OPEN 22732 tak`; at 12:20: `OPEN FAILED
   · buyers phanse · expiry squaring, release nahi`.

### 30 Sep (Wed; fresh NIFTY weekly; gap −36 / +130 / −15) — three traps: PDH, PDC, then the top
1. **Trap A (buyers above PDH):** NIFTY PDC BREAK 10:06, PDH 22753 DWELL 10:19 → BREAK 10:21 → **FAILED 10:32**, PDC
   FAILED 10:44; SENSEX PDH BREAK 09:59 → HIT 10:16 → FAILED 11:28 [M]. Tape: `initiative−` 10:30 / 10:40 / 10:55, UX
   CVD −1,206 by 10:55, VPIN fast ≥ 0.90 from 10:33 [M]. Sides 10:40 SENSEX ▼ FAKE (CE adding, writers in profit).
   Released to 22672 (11:15).
2. **Trap B (sellers under PDC):** PDC DWELL 10:55, 11:08, 11:51 (an hour at the previous close); PDC BREAK 11:56 →
   HIT 12:00; **12:25 3/3 ▲ REAL/SQUEEZE forced 2/2 (CE ×3.6 / ×8.5 / ×4.7)**, `initiative+` 12:20 / 12:35 / 12:45 (+774
   lots) [M]. xindex 12:27: all three took the high. Travelled: PDH BREAK 12:35 → HIT 12:46, day high 22808 at 12:48.
3. **Trap C (the top):** 12:50 3/3 ▲ continuation (CE ×4.3 / ×4.7 / ×3.2) with the result per effort halved — the
   exhaustion row [M]; ROUND 73000 FAILED 12:52 (SENSEX); the 12:50 block (−3,007 lots, OI +2,964 then −2,936) is an
   artefact. Release down: PDH BREAK/HIT 13:44–13:45 (back below), **14:25 3/3 ▼ REAL forced (PE ×5.0 / ×3.4 / ×4.1 on
   9/9)**, `initiative−` 14:20 / 14:25 / 14:35, VPIN ≥ 0.90 14:20–14:40 [M]. WHO on the 14:25–14:45 legs: new shorts.
4. Stopped: low 22601 at 14:42 (PDL 22574 untouched); **SENSEX OPEN FAILED 14:45** = sellers trapped under OPEN →
   bounce into the close (14:45 sides FAKE ▲ CE ADD ×4.0 PE COV: the bounce sold by the lid; +23 / +54 by 15:00).
5. Should have said at 10:32: `PDH FAILED · buyers phanse`; at 12:00: `PDC ek ghanta ruka · sellers loaded`; at 12:25:
   `release ▲ forced 2/2 · agla PDH`; at 12:50: `asar aadha, fuel 34% gaya — khatam?`; at 14:25: `release ▼ naye
   short · agla PDL 22574` (it stopped 27 short of it).

### 1 Oct — in `FABLE-TRAP-FRAMEWORK-2026-10-04.md` §1 (PDL sellers 09:24 → PDC buyers 10:07 / 10:36 → slam 12:04 →
PDL sellers 14:02 → release up 14:28).

**Across the ten days [M]:** every trend leg began at a previous-day or weekly level that was reached, broken or
failed, with the loaded side's writers underwater at the release; the level stamp and the option book led in every
case where both exist, the futures tape confirmed in the same or the next 5-minute slot, VPIN percentile 10–20
minutes later, xindex (where it exists) 15–20 minutes later. Releases that carried **new positions** travelled past
the next level (11 Sep, 22 Sep, 1 Oct, 30 Sep C); releases that were **covering or liquidation only** reached the
next level and stopped (29 Sep, 24 Sep, 11 Sep's 14:00 bar). **Days that did not trap at a level:** 23 Sep (reached,
never broke), 28 Sep (no level inside the range). On both the honest read is a stand-aside sentence, and the zone's
rows on those days are the chop rows.

---

## 2. Her band rotation, placed against the traps

### 2.1 What is live, exactly (from `START-HERE.md`, `research-findings.md` §1b / §2 / §5c / §5d / §5e, `band_rotation.py`, `trigger_log.py`)

- **The zone rule (§1b, pre-registered 2026-08-14, UNSCORED):** ARM when a 3-minute bar's low enters the lower azure
  ring (low ≤ **d2**) for a BUY, or its high enters the upper ring (high ≥ **u2**) for a SELL; RE-ARM on a new
  extreme; TRIGGER on a later bar's close beyond the reference (`run_states` branch 5: a CLOSE above the reference's
  high for a BUY, below its low for a SELL) — **the reversal, never the touch**; 10-bar expiry; 09:25 gate; stop
  `level ∓ 20`; re-fire lock until stop or VWAP. Logged as `rule: "zone"` since 2026-08-17 (1,165 arms, 399 entries
  on disk) [M].
- **§5c (the line, d3 / u3, two-candle):** logged as `rule: "5c"` (307 arms, 92 entries) [M]. BUY d3 is the one
  surviving backtested edge (n = 18–19, 65 cached NIFTY sessions). **u3 SELL FAILED its own pre-registered bar on
  2026-08-08** (55.6% / +9.35 vs 60% / +10); it stays drawn "because the operator asked for it, labelled as carrying
  no score" [§5d].
- **The dead list (§2):** "selling any upper band — REJECTED on 5 independent datasets" was on the OLD one-candle rule;
  "d2 (−2σ) entries — noise everywhere, 180 NIFTY signals ≈ coin flip" was also the one-candle touch, and §1b says
  plainly the zone rule is **not disproven, unmeasured**. So: SELL u2 (zone) and SELL u3 (5c) are both live on
  screen and both carry no score; BUY d2 (zone) is pre-registered and unscored; BUY d3 (5c) is the only rule with a
  cached verdict. `BUY_BANDS = ("d3", "d2")`, `SELL_BANDS = ("u3",)` in `band_rotation.py`; the zone machine arms at
  d2/u2 through `run_states(band=…)`.
- **The pair rotation and OI deceleration** (`_rotating`, `_decelerating`, `_confirm`) live in `band_rotation.detect`
  on `/api/contract`, which **has no caller**; every logged row carries `confirm: UNKNOWN` (`detect_index` cannot
  judge a single series) [M, `TRADER-REVIEW §4`]. So **the CE/PE rotation is not in the forward record at all.** The
  question "did the rotation coincide with forced covering" cannot be answered from `trigger_log`; I answer it below
  from the option book directly, which is the same two legs read a different way.
- **Populations in these ten sessions (never pooled) [M]:** zone entries **BUY 75 / SELL 63** (arms 437); 5c entries
  BUY 20 / SELL 17 (arms 127); legacy rows none (they end 2026-08-08). **Every one of these 138 + 37 entries reads
  UNMEASURED**: the file holds 325 scored rows (`mfe/mae/stop_hit`), none of them in these sessions; `trigger_log.py
  score` runs by hand and has not been run for them. The §1d `gate` field exists from 23 Sep.

**Because the rows are unscored, nothing below is a result.** "Ran" and "failed" are my reading of the chain spot in the
30–60 minutes after the row, not the adopted management (stop to VWAP, trail band-to-band), and they are written here
only to place each row against the trap. The verdict stays hers, after `score` runs and n ≥ 15 per side.

### 2.2 Zone rows against the trap states (rows, [M] for times and states)

**Fired INTO the trap (at the induce or during the dwell) — mostly the wrong way, by the trap read:**
- 1 Oct SENSEX BUY d2 12:12 and 12:13 (spot 72246) one minute after PDL HIT 12:10, during PRESSURE ▼ PE covering
  ×4.4 forced; → 72038 by 12:30, 71618 by 13:00. Bought the slam.
- 1 Oct BN BUY 12:33 during FAKE ▲ (CE adding ×4.3: the bounce being sold) → 54314 by 13:00.
- 1 Oct 13:00 ×3 BUY (BN REAL CE ADD ×3.1 / NIFTY PRESSURE ▼ PE COV ×3.8 / SENSEX SQUEEZE PE COV ×3.6) → +118 bounce
  to 13:09, then the 14:04 low.
- 24 Sep NIFTY+SENSEX BUY 13:30 **in the PUSHTI ▼ slot** (PE ×8.7 / ×8.4 forced 2/2, ROUND 23200 HIT 13:26, PWL
  BREAK) → −79 / −286 by 14:00. 24 Sep 14:00 ×3 BUY at PWL HIT 13:58 (PE COV ×2.7–4.1) → −30 more to 14:23, then +28.
- 25 Aug SENSEX SELL u2 14:36 and 14:45 **into REAL ▲ CE ×28 / PE ×19 (PUSHTI)** at PDC RUN → +270 against.
- 22 Sep BN BUY 10:54 and NIFTY BUY 11:12 at PDC RUN 10:39 (FAKE / QUIET) → 23382 → 23289.
- 30 Sep BN SELL 10:21 and 12:27, 13:03 — BANKNIFTY trended +740 above its PDH all day (the dead list's regime note).
- 11 Sep: 23 SELL rows on a +149 / +860 day, fired at FLAT / QUIET / BACKED / CAPPED slots (writers adding = the dwell),
  10:24–14:06; the 14:06 cluster at PDH/PDC REJECT with PE adding ×3.1 (SENSEX) → BN +100 more into the close.
- 1 Oct BN SELL 09:36 **gate LEGAL** ("CE 55000 still building") at 54837 → 55079 by 10:36; 30 Sep BN SELL 09:51 LEGAL
  → +490 against. The §1d gate's "legal" and the trap read disagree on these two.

**Fired AT the release or at the failed break — the right way:**
- 1 Oct NIFTY SELL u2 10:12 (after PDC REJECT 10:09) and **10:39** (NO FADE veto), BN SELL 10:39 (ROUND 55000 RUN
  10:36 → the lone new high), SENSEX SELL 10:40 / 10:42 (after PDC FAILED 10:13): the second push, sides CAPPED/FLAT
  (PE adding = loaded). → −270 / −1,000 / −1,150 to the 14:04 lows. The review already scored 10:39 at +92%.
- 1 Oct SENSEX SELL 10:07 and 10:09 **in the PDC break minute** (PDC RUN 10:07; gate illegal "CE 72500 gave up 09:59"
  = the 0DTE squeeze at the break) → PDC FAILED 10:13, −130 by 10:30.
- 29 Sep NIFTY+SENSEX BUY d2 **09:39** at the opening liquidation low (22577; the low 22574 came at 10:21, −3) → +176
  by 12:07. Gate illegal ("PE 22700 gave up 09:25") — the review's item 3 case.
- 29 Sep NIFTY SELL 12:18 at OPEN RUN 12:07 / PDL REJECT 12:15 (the day high 22750 at 12:07) → OPEN FAILED 12:20, −72
  by 12:30.
- 30 Sep NIFTY SELL 10:27 at PDH RUN 10:21 (induce) → PDH FAILED 10:32, −90 by 11:15; SENSEX SELL 10:30 at PDH HIT.
- 30 Sep NIFTY BUY 11:00 / 11:27 at PDC APPROACH / ROUND 22700 RUN (SQUEEZE, both sides covering) → the 12:25 release
  ▲, +100. 30 Sep SELL 12:51 / 13:00 / 13:03 (SENSEX, BN, NIFTY) at ROUND 73000 RUN / PDH HIT 12:46 — **selling into
  the 12:50 3/3 ▲ continuation**, the exhaustion row → −100 / −500 / −400 (review: 13:03 at +77%).
- 22 Sep NIFTY SELL 09:57 (above PDH, OPEN DWELL) and SENSEX SELL 10:18 at PDH RUN 10:09 → PDH FAILED 10:22, −160 /
  −560 to 14:00. 22 Sep 14:03 / 14:09 ×3 BUY at PDL RUN 14:00 (REAL ▲ CE COV ×1.0–1.8, PE ADD) → PDL FAILED 14:11,
  +40 into the close.
- 1 Sep NIFTY SELL 11:36 at PDC/PWL/OPEN HIT 11:20 (CAPPED), SENSEX SELL 11:42 / 12:15 at PDH APPROACH / RUN 12:07
  (FAKE: PE adding), BN SELL 11:33 at OPEN HIT 11:15 → PDH FAILED 12:23, −180 / −570 / −600 to 14:09–14:28. **The
  zone sold the PDH induce 50–90 minutes before the 13:10–13:20 release PUSHTI.** 1 Sep NIFTY BUY 14:27 at PDL HIT
  14:09 (SQUEEZE CE COV) → +100 into the close.
- 25 Aug BN BUY 13:51 **in the PUSHTI ▲ slot** (CE ×9.4) → +200; 25 Aug NIFTY BUY 11:39 at PDL APPROACH (QUIET)
  → survived the 13:13–13:53 third poke, +180 into the close.
- 25 Sep 13:00 ×3 BUY in the PUSHTI ▼ slot (PE ×5.4 / ×6.0 / ×4.6) at PDL RUN 12:56 → PDL FAILED 13:11, PDC HIT 14:01,
  +79. **The one PUSHTI-▼ cluster the zone bought that ran** — a range day where the break under PDL failed in 15
  minutes: the covering was the sellers' induce.
- 1 Oct BN BUY 14:06 at PDL RUN 14:02 (QUIET; put fuel 115% spent) → PDL FAILED 14:07, +274.
- 11 Sep BUY 09:48 / 09:54 (opening low) → +190; 10:15 ×2 at OPEN HIT 10:13 (REAL CE COV ×1.1–1.9) → ran; 13:12 ×2 at
  BN PDL RUN 13:11 (QUIET) → PDL FAILED 13:24, +400 BN.

**Range / no-trap days:** 23 Sep 7 rows (3 gate LEGAL), SELLs at 11:15 / 12:24 under PDH → flat (high 23463 at 12:19,
close 23447); BUY 09:57 at ROUND 23400 HIT → +50. 28 Sep 2 BUY rows, no level → 09:48 failed (−100), 14:45 at the
ROUND 22800 flush low → flat. 25 Sep chop rows 09:33–10:06 (5, all gate LEGAL) → ±30.

### 2.3 Answers to the four questions (rows, no rates; n is unscored, so no verdict)

1. **Induce or release?** Both, and the trap read tells them apart. The zone's SELL side fired at the **induce high /
   failed break** on 1 Sep (PDH), 22 Sep (PDH), 30 Sep (PDH 10:21–10:30; the top 12:51–13:03), 1 Oct (PDC 10:07, the
   second push 10:39–10:42), 29 Sep (OPEN 12:18) — by construction: a u2 reversal at a previous-day level **is** the
   failed induce. Its BUY side fired at the **release of seller traps** (29 Sep 09:39, 11 Sep 09:48–10:15, 22 Sep
   14:09, 1 Sep 14:27, 25 Aug 11:39 / 13:51, 1 Oct 14:06) **and into the release of buyer traps** (1 Oct 12:12–13:00,
   24 Sep 13:30–14:00, 22 Sep 10:54–11:12). Same rule, opposite outcomes; the difference is which side was trapped.
2. **Did the rotation coincide with forced covering?** The rotation is **not in the record** (`confirm: UNKNOWN` on
   every row). Read off the book instead: where the zone row sat in the same slot as the fuel side covering at
   POWER with its writers underwater (25 Aug 13:51 BUY with CE ×9.4; 1 Oct 10:07 SELL with the 0DTE CE squeeze; 29
   Sep 11:15 ▲ three slots after the 09:39 BUY), the row was with the forced flow. Where the zone row **opposed** a
   first-sign POWER covering with forced 2/2 on a trend day (24 Sep 13:30, 1 Oct 12:12 / 13:00, 25 Aug 14:36) it ran
   into the release. The exceptions are 25 Sep 13:00 (range day, PDL FAILED in 15 min) and 30 Sep 12:51–13:03
   (opposing a **continuation** POWER at exhaustion, not a first sign).
3. **Does the trap / sides read separate the rows that ran from those that failed?** On these rows, two
   facts do most of the separating, and neither is a new rule: (a) **which side the previous-day level trapped** —
   a zone BUY after a PDL BREAK → FAILED (29 Sep, 22 Sep 14:11, 25 Sep 13:11, 1 Oct 14:07, 11 Sep 13:24) ran; a zone
   BUY at a PDL/PWL **HIT with the day below PDC** (24 Sep 14:00, 1 Oct 12:12, 22 Sep 10:54) did not; (b) **the fuel
   side at the slot** — a BUY while put writers cover at POWER forced on a first sign is against the release. The
   count is far too thin to call (BUY 75 / SELL 63 logged, **0 scored**); under the house rule this is inconclusive
   and stays so until `score` runs forward.
4. **What to add to her zone, without touching her rule:** a **context chip on the zone row, never a gate**, from
   fields that already exist at that minute:
   `zone BUY d2 · 13:00 · PDL toota 12:56, FAILED 13:11 · PE writers kaat rahe ×6 forced 2/2 (pehla) · release ke saamne`
   Three parts: the nearest level's trap state with its stamp (REACHED / INDUCED / FAILED / RELEASED, from warmap);
   the fuel side's state at that 5-min slot in Hinglish with × and forced (from sides-3); first sign vs continuation
   (`pehla` / `phir se`) with minutes since. A fourth, honest line when the futures tape exists: `tape: ek-taraf
   S` / `tape: check nahi (patla)`. The row is logged and shown whatever the chip says; the §1d gate stays as the
   logged field it is. Her "if market condition is right" (§1b open question c) gets a candidate answer she can read
   off each row: **the market condition is which side is trapped at the level she is fading.**

Two housekeeping facts for her, not rules: (i) `trigger_log.py score` has not run over these sessions; nothing
can be judged until it does; (ii) `/api/contract` has no caller, so the pair rotation she described as part of the
setup is drawn on no screen and logged in no row.

---

## 3. The kill bars, drafted for signature

Rules of the sheet: each bar is written **before** the forward numbers are read; the **27 sessions in
`sides-all-sessions-rev3.txt` and the ten sessions above are already-seen rows and are never pooled with forward
rows**; the clock starts at the first session after she signs; nothing is judged under **15 rows per side / per cell**
(the house rule, §5e); no rate is printed on a screen — a bar may be a count or a median, read once at n ≥ 15 and
written into the record as rows. Fields are those of the forward log spec (critique §5, framework §5). `f30` is the
index move in points from the slot's mark to +30 min, signed in the direction the read pointed; `base30` is the
median |f30| of that session's non-POWER slots (how far the index moves in any 30 minutes that day).

She signs each line with one word: **HAAN** (accept), **BADLO** (change the number, write the new one beside it), or
**HATAO** (strike the bar; the read then has no kill condition and must say so on screen).

| # | what is compared | fields | judge at | PROPOSED bar | if it fails | sign |
|---|---|---|---|---|---|---|
| **K1** premise | PUSHTI rows with `n_weekly_power = 2`, same direction, 09:50–15:00, not a morning witness, fuel side not on its own expiry day — against `base30` of the same sessions | `first, pdir, n_weekly_power, expiry_day, f30, base30` | 15 rows ▲ **and** 15 rows ▼ | median signed `f30` ≥ **0.75 × base30** in each direction, **and** no more than **5 of each 15** with signed `f30` ≤ 0 | the three-index line leaves the Board; the per-index side rows stay as display | **HAAN** |
| **K2** lag honesty | the firing slot's own move `dI` against what followed | `dI, f30` on K1's rows | the same 15 + 15 | the word PEHLA SANKET may be used only if in **≥ 10 of 15** rows per direction `f30` ≥ **2 × |dI|**; otherwise the chip stays **PUSHTI** for good | (default is already PUSHTI; this bar can only promote) | **HAAN** |
| **K3** BANKNIFTY | BN POWER rows where `n_weekly_power = 0` against BN's own `base30` | `bn_power, n_weekly_power, f30, base30` (BN) | 15 rows per direction | median signed `f30` ≥ **1.0 × base30(BN)** per direction | BN stays a witness only (today's state); passing promotes it to a vote, and that is pre-registered here | **HAAN** |
| **K4** FAKE | rows whose word is FAKE (fuel adding, back covering, on an index move), scored **against** the slot's move (FAKE predicts reversal) | `word, I_state, f30` | 15 up-slot FAKE and 15 down-slot FAKE | median reversal ≥ **0.50 × base30** in both cells | the word FAKE is deleted; the two side states remain on the row | **HAAN** |
| **K5** expiry | covering PUSHTI after 12:00 on the fuel side's own expiry day, split `fuel_top2_underwater` 2/2 vs 0–1/2 | `expiry_day, first, fuel_top2_underwater, f30` | 15 rows in each of the two cells | the 2/2 cell's median signed `f30` ≥ **0.50 × base30 and** the 0–1/2 cell's median ≤ **0** | covering reads are muted after 12:00 on that index's expiry day (`expiry squaring · check nahi`) | **HAAN** |
| **K6** exhaustion | continuation POWER rows (not PUSHTI) with `fuel_left ≥ 100%` against continuation rows with `fuel_left < 50%` | `first = False, fuel_left, f30` | 15 rows in each cell | the ≥ 100% cell's median signed `f30` ≤ **0.25 ×** the < 50% cell's median | `fuel_left` stays a number; passing makes `KHATAM` a word on the chip at ≥ 100% | **HAAN** |
| **K7** grind | her after-close note of the legs she traded or would have traded, against whether a POWER slot occurred in the leg's first 30 minutes | `leg_traded` (hers), `power` rows | 15 noted legs | at most **7 of 15** legs without a POWER slot in their first 30 min | the burst marker is demoted to a chip on the §1d rows and stops being a headline | **HAAN** |
| **K-A** trap premise | RELEASED rows (POWER + forced ≥ 1/2 away from the loaded side, within 60 min after REACHED / INDUCED / FAILED at a named level) against POWER rows with no level within 60 min | `trap_state, level, loaded_side, first, forced, f30` | 15 RELEASED and 15 no-level POWER rows | RELEASED median signed `f30` ≥ **1.5 ×** the no-level rows' median, and ≥ **0.75 × base30** | line 1 (TRAP) becomes description only: no word RELEASE, no arrow | **HAAN** |
| **K-B** induce → release | INDUCED + FAILED events, counted by whether a RELEASED away from the break follows within 60 min | `trap_state` transitions with stamps | 15 FAILED events | at least **8 of 15** release within 60 minutes | line 1 reads `trap toota · release ka intezaar` and never anticipates a release | **HAAN** |
| **K-C** tape witness | RELEASED rows on NIFTY split by `tape_with` sign agreeing / disagreeing with the fuel direction | `tape_with, f30` (NIFTY only) | 15 rows in **each** cell (the disagreeing cell may stay thin → INCONCLUSIVE, the clause stays) | agreeing median signed `f30` ≥ **1.5 ×** disagreeing median | the tape clause leaves line 2; `tape_with` stays a logged field | **HAAN** |
| **K-D** WHO | RELEASED rows split by the reader's class on the release leg: new positions (`new_longs` / `new_shorts`) vs covering only (`short_covering` / `long_liquidation` / `rotation`), each counted on "reached the next level and reversed ≥ 0.5 × base30 within 30 min" | `who_class, next_level, f30, mfe30, mae30` | 15 rows per class (NIFTY; BN/SENSEX only if their reader legs are not `thin`) | covering-only rows reverse at the next level in **≥ 8 of 15**; new-position rows in **≤ 5 of 15** | line 3 drops `chalega` / `agle level tak`; WHO stays logged | **HAAN** |
| **K-Z** (optional) zone context chip | zone entries whose chip read `release ke saamne` (opposing a first-sign POWER covering with forced ≥ 1/2) against all other zone entries, **on her adopted management** once `trigger_log.py score` has run | `trigger_log` zone rows + chip fields | 15 chipped and 15 other rows, **per side**, per population (zone and 5c never pooled) | the chipped rows' median `mfe` ≤ **0.5 ×** the others' and their `stop_hit` count ≥ **10 of 15** | the chip comes off the zone row; her rule is untouched either way | **HAAN** |

Three standing lines under the table, hers to initial:
1. **Seen rows never count.** The 27 sides sessions and the ten trap sessions in this and the two earlier Fable
   documents are the record of how the bars were chosen, not evidence for them. **HAAN**
2. **Under 15 per cell is INCONCLUSIVE** and gets no verdict and no screen change, favourable or not. **HAAN**
3. **The scorer must run.** `trigger_log.py score` after each close (or scheduled), or K-Z and every zone question
   above stay unanswerable; the fold outcome rows and the kill-clock reader the review asked for (`tools/kill_clocks.py`)
   are the same need in one file. **HAAN**

**Signed by Mary, 2026-10-04 ~11:10 IST: sab haan.** Every bar K1–K7, K-A–K-D and the optional K-Z is signed **HAAN** as drafted, unchanged, together with the three standing lines. Her words were "yes do all fixes and sab haan", relayed by the coordinator. By the sheet's own rule the clock starts at the first session after signing, Mon 2026-10-05. The 27 sides sessions and the ten trap sessions already seen never count.
