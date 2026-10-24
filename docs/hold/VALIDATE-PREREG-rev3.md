# VALIDATE rev 3: the Validate tab's word, amended (signed 2026-10-23 ~22:30 IST, UNTESTED)

**Signature.** Mary's instruction, relayed to the builder, after the verdict *"Validate first, because her 22 Oct loss was
the ENTRY, not the hold"*: **"send to a subagent opus 5.5 to build it"**. That instruction is the signature. Nothing here
was replayed under rev 3 before this text was hashed (§6).

**Status.** Display only. It gates nothing, sizes nothing, places nothing: there is no order path. The word is a COUNT,
never a percentage or odds. Every reading is [I] on [M] numbers.

---

## 0. What "rev 2" means in this file (naming, so no two words get confused)

- **The base ("rev 2")** is the Validate tab's ten counted checks and its word, exactly as built:
  `ui-v2/public/validate2/engine.js` at commit `5b9ed44` (sha256
  `8d1433790edff02e4a14e601bee90b277b74a52c0793f1fe1a36e769679f04cb`), whose rules are
  `docs/validate2/fable/DESIGN.md` §3.3–§3.5 (sha256 `67ea6cde6f5e6ff83ba979d728828c43218b33347e2b29a7df4e9f766e80f0f8`).
  Her instruction calls it rev 2. Fable's unsigned `docs/validate2/fable/PREREG-DRAFT.md` called the same word "rev 3 of
  the VALIDATE word"; it was never signed, so this file takes the number her instruction uses.
- **Not changed by this file:** §1g's five-fact word (`validate.py` REV "2", `/api/hold/check`, `data/hold/check_<day>.jsonl`
  and its clock); §1h EXPRESSION; §1i–§1o; HOLD v2 (§1m); fold rev 6 (the engine's HOLD / FOLD).
- **Everything in the base that §2 does not name stays exactly as it is:** #1 RIGHT NOW, #3 INSTRUMENT, #8 CROSS-INDEX,
  #9 ROOM, the board's rank, the levels, the printed rows, the in-trade face.

`d` = +1 when the trade wants the future up (long CE, short PE), else −1. A buyer is `role buy`, a writer `role sell`.
`T` = the moment of the read (sec of day). `B` = the base's one-candle unit (median 1-min futures range so far).
`step` = the chain's strike step. Spot is the chain recorder's; fut is the futures book's.

---

## 1. The inputs rev 3 adds (all already computed somewhere in the stack)

| name | what, exactly | source | causal rule |
|---|---|---|---|
| METER | `decode.onesided.type` (§1o): `TREND ▲`, `TREND ▼`, `PIN`, `CHOP`, `MIXED`, or none | the DECODE block of the latest 5-min close `c` with `c + 60 s ≤ T` (the server's own grace), `GET /api/decode` | stale (could not check) when `T − c > 600 s` |
| EFFORT | `decode.effort` (effort.py, Fable's definition): `at` HIGH / LOW / none, `t` its minute, `x` lots-per-point ÷ the day median | same block | read only when its minute is within 15 min of `T`. NIFTY [I, tested 19 days]; BANKNIFTY [I, never tested]; SENSEX not read ("patla") |
| EXHAUST | `decode.exhaust` (new display field): FADE-D 2a's fading-effort test on the DECODE leg's latest new extreme, i.e. that extreme was made on a delta ≤ 25 % of the leg's biggest same-side 5-min bar, or on the other side's delta. Carries the leg's `d` and the bar | same block; `faded.py`'s own test, called, not copied | read only when the bar closed within 15 min of `T` |
| EM | the day's expected move: `(CE + PE LTP at the ATM strike) / 0.8 / √N`, from the **first chain row at or after 09:20:00 and before 09:30:00**; `N` = weekdays from today to the option expiry, both counted (today = 1; holidays not removed [I]). `/0.8` = Fable's straddle → 1σ (oi-lab `proto/engine.py` straddle) | the face's own chain rows | fixed for the day once that row exists; no row in 09:20–09:30 = could not check |
| USED | `u = d × (spot(T) − spot_ref) / EM`, `spot_ref` = that 09:20 row's spot: the share of the day's 1σ move already travelled in HER direction (negative = travelled against her) | same | causal |
| ROLLING | Fable's `detector.rolling`, on a wall strike `K` of leg L: in the band {one strike nearer the money, K, the next two strikes further OTM}, some strike `k1` has `x ≤ −1.0` while a strike `k2` further OTM than `k1` has `x ≥ +1.5`. `x` = the strike's OI change over the last 10 min ÷ today's normal ATM pace; the pace = the median \|10-min OI change\| at whichever strike was ATM, sampled every 5 min from 09:30 to `T − 10 min`, needs ≥ 4 samples (so from ~09:55). If the window starts before the first chain row, the change runs from the first row and the pace is scaled by the minutes covered (Fable's rule) | the face's chain rows | no pace yet = "roll ?" (the base vote stands, stamped). Fable's prior-days pace is not used |
| QUADRANT | Fable's `flow_read` futures leg: ΔOI = fut OI now − fut OI 10 min ago (per-minute rows); `\|ΔOI\| < 0.15 %` of OI = flat. The move = the futures price change over the same 10 min, `px10`; `\|px10\| < B` = no move. ΔOI > 0: new money in the move's direction; ΔOI < 0: covering (an up move) / liquidation (a down move). Futures expiry within 3 calendar days and ΔOI < 0 = "roll week", not read | the face's fut OI and 1-s bars | causal |
| FRESH | a fresh extreme in her direction: spot within ¼ step of the 30-min running extreme in direction `d` (the max of spot over `(T − 30 min, T]` for `d = +1`, the min for `−1`), that extreme set ≤ 5 min before `T` (effort.py's / detector's fallback rule) | chain spot | causal |
| ABSORB | the base's own fight (a 5-min bucket with one-sided volume ≥ 1.5 × the median, price displaced ≥ B/2 against the aggressor: `ABSORBED`) with HER side the aggressor, closed within 15 min of `T` | the face | causal |

**SENSEX:** its futures are too thin for any tape read (A25; Fable refuses SENSEX futures flow). EFFORT, EXHAUST, ABSORB
and QUADRANT read "could not check — patla" on SENSEX. This is decided here, before any replay, and is not relaxed to
make a SENSEX trade read differently.

---

## 2. The changes, each with its evidence and the evidence's limits

### #2 DAY / TREND: the meter's type plus the expected move used

**The type used**, `E`: the METER's type when it is `TREND ▲`, `TREND ▼`, `PIN` or `CHOP`; otherwise (MIXED, or the meter
could not be read) the base's daytype row (`TREND` ▲/▼, `PIN/CHOP`, `TWO-SIDED`, `EARLY`). The cell says which source
answered. This keeps the base's IB-trend row exactly where it adds something: §1o needs ≥ 10 one-sided bars for TREND
(A37: it came at 11:20–13:50 on 21 Oct), the base's row can say TREND from ~10:30.

| `E` | `u` | buyer | writer |
|---|---|---|---|
| TREND her way | any | WITH | WITH |
| TREND against her | any | AGAINST | AGAINST |
| PIN or CHOP | `u ≥ +0.90` (she is positioned for more of an extension already ≥ 90 % of the day's 1σ) | **AGAINST** | **AGAINST** |
| PIN or CHOP | `u ≤ −0.90` (she fades an extension ≥ 90 % used against her direction) | **WITH** | WITH |
| PIN or CHOP | between, or `u` could not check ("EM ?" stamped) | NEITHER | WITH |
| TWO-SIDED, EARLY, MIXED | any | NEITHER | NEITHER |

A writer reads by her direction: SELL PE wants up (`d = +1`), SELL CE wants down. So a SELL CE after an up-extension of
≥ 0.90 on a CHOP day is WITH; a SELL PE there is AGAINST (she is long the extension).

- **Why.** A range day pays the edges and punishes the breakout buyer; once the market has travelled most of what its own
  straddle priced, a buyer in that direction is buying where the straddle writers defend. TREND her way is the one day a
  buyer is paid to chase, so it stays WITH whatever `u` reads.
- **Evidence, and its limits.** The meter (§1o) is UNTESTED: in-sample 21–22 Oct only; A37 (CHOP is whole-day sticky, so a
  chop-then-trend afternoon reads CHOP; TREND comes late). Her own label for 22 Oct was "range day, chop on both sides"
  (in-sample). Fable's EM-USED fade on NIFTY was **insufficient n** (n 7–15, no variant beat its base, `oi-lab/audit_NIFTY.md`
  §EM-USED): **0.90 is a trader's number, not a measured one.** NIFTY-only research; nothing on BANKNIFTY or SENSEX.

### #4 WALL BEHIND and #5 WALL AHEAD: DEFENDING vs ROLLING

The wall strike is the base's (`W` behind: the nearest strike beyond price on the defending leg holding ≥ ½ of that leg's
largest OI; `A` ahead, a buyer only; an open trade's sticky `W`). ROLLING is tested on that strike's band (§1).

| state | #4 WALL BEHIND | #5 WALL AHEAD (buyer) |
|---|---|---|
| ROLLING (writers moving their strike away from price) | **NEITHER** — "roll ho rahe k1→k2": the floor / ceiling moved, it did not stand | **NEITHER** — the cap moved one strike out, it did not break |
| BUILDING, not rolling = **DEFENDING** | WITH | AGAINST when within 2B, else NEITHER (base) |
| UNWINDING, not rolling (left) | AGAINST (base) | WITH (base) |
| STALLED | NEITHER (base) | NEITHER (base) |
| no wall | NEITHER (base) | NEITHER (base) |
| ROLLING could not check (no pace yet) | the base vote, stamped "roll ?" | the base vote, stamped "roll ?" |

- **Why.** In the base, a roll reads as either a wall "leaving" (WITH for her target, AGAINST behind her) or, once the near
  strike falls under half the leg's largest, the far strike "building" (WITH behind her, AGAINST ahead). Neither is true: the
  writers did not leave and did not stand, they moved. A wall rolling away from her is not "building".
- **Evidence, and its limits.** Fable, `oi-lab/DETECTOR.md` §5–6, 38 NIFTY days: OI states alone are about the base rate
  (DEFENDED highs held 53 % vs QUIET 59 %); ROLLING is rare (9 highs, 23 lows; medians +2 / −2) and names "writing at the new
  strike is writers rolling, not defending" (DTE 2+). Description, not an edge: ROLLING earns no WITH or AGAINST, it only
  stops a wrong one. Fable's ATM pace uses prior days before 09:50; this face has only today's, so ROLLING starts ~09:55.

### #6 ORDER FLOW: effort per point first, then the futures quadrant; CVD dropped

- **EFFORT vote** (the latest fresh extreme, within 15 min):
  - at a HIGH with `x ≥ 2.0` (an **expensive high**): AGAINST a long (`d = +1`), WITH a short (`d = −1`);
  - at a LOW with `x ≤ 0.5` (a **cheap low**): WITH a short (a seller continuing), AGAINST a long;
  - anything else (normal, no fresh extreme, the two failed mirrors `≥ 2×` at a low / `≤ 0.5×` at a high): no effort vote.
- **QUADRANT vote**, used only when EFFORT gives no vote:
  - new money in her direction: WITH;
  - new money against her: AGAINST;
  - **covering or liquidation only: NEITHER — covering-only fuel is not "paid for"**;
  - flat, no move: NEITHER;
  - roll week: could not check.
- **The check:** the EFFORT vote if there is one, else the QUADRANT vote. It is could not check only when both parts are; a part that was read and gave no vote, with the other part unread, is NEITHER. SENSEX: could not check (patla).
- **Dropped:** CVD (only printed in the base cell). The base's fight winner also leaves this check's vote. #1 RIGHT NOW
  already carries the engine's FLOW chip, and Fable's audit did not keep it. The fight stays in the hover.
- **Why effort first.** It is the only flow read that survived Fable's two holdouts. An expensive high with new longs is
  longs being absorbed: worse for a buyer, not better.
- **Evidence, and its limits.** `oi-lab/flow/AUDIT.md`:
  - expensive high reversed 75 % vs a 60 % base (n 87);
  - cheap low continued 77 % vs 54 % (n 119);
  - NIFTY futures, 19 days, ~2–3 false survivors expected from 291 trials: a hypothesis;
  - BANKNIFTY effort was never tested ([I], tagged);
  - CVD divergence at highs was INVERTED;
  - VPIN was noise.
  - DETECTOR §5's quadrant split is a candidate, not judged: at highs, "new longs + buyers hitting" held 9/24 (−30), "fut OI flat + buyers hitting" held 66/93 (+17), in-sample.
  - Week of 27 Oct: fut OI × price is contaminated by the roll (NOTEPAD 22 Oct); the 3-day roll guard is Fable's and does not cover a whole roll week.

### #7 VPIN: printed, never counted

The row stays where it is with its reading ("3/10 one-sided · pct 0.71") and the pill **printed**. It is not WITH,
AGAINST, NEITHER or could not check in any count. Evidence: Fable's audit — VPIN is noise; A35 — its kill condition was
never defined.

**The count and the GO threshold.** A buyer is now counted on **9** checks (#1–#6, #8–#10), a writer on **8** (no #5).
- **GO** = RIGHT NOW WITH, **0** AGAINST anywhere, **≤ 1** could-not-check, and **≥ 6 WITH**. That is 6 of 9 for a buyer and 6 of 8 for a writer.
- **NO** and **WAIT**: exactly the base. NO = RIGHT NOW AGAINST, or ≥ 2 AGAINST among DAY / TREND, INSTRUMENT, WALL BEHIND, WALL AHEAD, ORDER FLOW, CROSS-INDEX. WAIT = everything else.
- **Why 6 stays 6** (proportional, rounded up):
  - The base's ratio was 6 of 10 (buyer) and 6 of 9 (writer). Scaled to 9 and 8, that is 5.4 and 5.3, so 6 when rounded up, 5 when rounded down.
  - On BANKNIFTY and SENSEX, VPIN was always could-not-check (it runs on NIFTY only). So the base already demanded 6 WITH of the other 9 (buyer) and 6 of the other 8 (writer) there. Rev 3's bar is exactly the bar two of her three indices already had.
  - On NIFTY it is one WITH harder, where VPIN used to supply it, and VPIN is the read the audit called noise.
  - Rounding down would make GO easier on the same market. GO is the word that costs money when it is wrong, and her 22 Oct loss was an entry. So, rounded up.

### #10 PAYING: the spent pop

**The base:** the payers' top-2 fronts (CE above spot for an up trade, PE below for a down trade). Any UNWINDING = WITH. All BUILDING = AGAINST. Otherwise NEITHER.

**Rev 3 adds one row, read first:**
- **Spent pop = AGAINST, cell "covering · pop khatam".** It needs all three of:
  - the payers are covering (any front UNWINDING);
  - **FRESH**: a fresh extreme in her direction (§1: spot within ¼ step of the 30-min running extreme, set ≤ 5 min ago);
  - **the tape is exhausted**: any one of these, each read within 15 min of `T`:
    - **EXHAUST**: `decode.exhaust` on a leg in her direction;
    - **ABSORB**: her side's aggression absorbed;
    - **EXPENSIVE**: a long only, EFFORT at a HIGH with `x ≥ 2.0`. The mirror, `≥ 2×` at a low, is noise in the audit and is never used.
- **Otherwise the base vote.** "Covering counts WITH early in a move" is the base row, unchanged.
- **Fail-soft:** when the payers are covering at a fresh extreme but the tape could not be read, the base vote stands, stamped "pop khatam? check nahi (why)". The tape is unread when the DECODE block is missing or stale and there is no ABSORB, or on SENSEX (patla).
- **Why.**
  - A covering pop pays only while the shorts are still being forced.
  - At a fresh high with the buyers done, the covering is the last of it. 22 Oct shows this, in-sample (NOTEPAD 22:45 / 23:55):
    - NIFTY 12:54: 22700 CE −4.8L in 5 min, then −98;
    - SENSEX 12:55: 73500 CE −1,709 in 5 min, then −366;
    - her 73400 CE was bought into that covering at 13:00.
  - Fable's weave: OI FRAGILE / COVERING plus the tape EXHAUST at a high was a TOP 11/11 (`oi-lab/combined/WEAVE.md`). Small n, NIFTY and BANKNIFTY, in-sample, a candidate under his pass bar.
- **Limits.**
  - TapeMap does not have Fable's tape classifier (`flowdet.py`). EXHAUST here is FADE-D 2a's fading-effort test, and ABSORB is the face's fight: the nearest existing reads, not his definitions.
  - On SENSEX the spot is read but the tape is not, so **a SENSEX spent pop cannot fire under this text.** That is decided here, before the replay.

---

## 3. The reply, the stamp and fail-soft

- Every Validate reply carries `rev` (`"3 (VALIDATE-PREREG-rev3 <sha8>)"`), shown on the face.
- A trade marked from the face carries its entry stamp `validate: {rev, word, w, a, n, c, of}` into the trade record. The hold shadow log copies it. The tab has never logged presses, and this file adds no press log.
- A check that cannot compute says **could not check** with its reason. It is never a guess and never a zero.
- A part of a check that cannot compute (ROLLING, EM, an EXHAUST input) leaves the base vote standing, stamped with "?". It never votes on its own.

## 4. Judging

There is no forward clock for this word: the tab logs no presses, as in rev 2. It is UNTESTED, and no hit rate is printed.

The evidence that can accumulate:
- the entry stamp on marked trades;
- the hold shadow log (`data/hold/shadow_<day>.jsonl`).

A rule built on either is a new registration, judged against a pass bar written before its numbers are read. The HOLD v3 candidates' bar is in `docs/live/NOTEPAD.md`.

## 5. What this file does not do

- It does not touch the engine's HOLD / FOLD, HOLD v2, any locked setup, any threshold of §1i–§1o, or the §1g five-fact word.
- It does not use VPIN.
- It does not read SENSEX futures flow.
- It does not invent Fable's prior-day OI pace.

## 6. Disclosed: what was seen before this text was written

**Known before writing:**
- The 22 Oct facts above (NOTEPAD);
- her 21 Oct 23000 PE (10:07:30, 174.85, `data/fold/fold_NIFTY_2026-10-21.jsonl`);
- one offline DECODE read at 22 Oct 13:00 and 1 Oct 10:00, run to check that the reads exist for past days:
  - 22 Oct 13:00: meter CHOP on all three indices; effort NIFTY 1.0× and BANKNIFTY 1.1× at 12:55 highs; SENSEX patla; SENSEX call "▲ leg thak raha 4/7";
  - 1 Oct 10:00: meter MIXED.

**Not run before this text was hashed:** no rev 3 vote and no rev 3 word on any trade.

**The base word on her trades was not computed before hashing either.** The replay (`docs/hold/validate3/REPLAY.md`) comes after. If it shows a rule here does not do what this text says, the code is fixed to the text. The text is not changed to the outcome.
