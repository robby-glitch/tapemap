# AMENDMENT (DRAFT, NOT YET SIGNED): SENSEX reads NIFTY's order flow — VALIDATE rev 3.1, HOLD v2 Amendment 3, and the in-trade FLOW read (written 2026-10-24, before any replay of it, UNTESTED)

## Her words (verbatim)

- **The method, 2026-10-24:** "i dont consider sensex oderflow i take nifty oder flow and trade in sensex they almost work
  in sync so leave or remove sensex oderflow chart . but i consider its oi"
- **The instruction:** "write it" (to: "one amendment for your signature … I'd write it, replay all your SENSEX trades to
  show exactly what changes, and then you sign").
- **Signature:** _not yet._ It takes effect only on her word after she has seen the replay (§6). Until then every piece
  below is built behind flags that are OFF (§4), so her Monday restart runs exactly today's rules.

**Status.** Display and advisory only. It places nothing and sizes nothing; there is no order path. No hit rate anywhere.

---

## 0. What this amends, and what it leaves alone

| registration | file (sha256) | what changes here |
|---|---|---|
| §1p VALIDATE rev 3 | `docs/hold/VALIDATE-PREREG-rev3.md` (`a4186306…82a5`) | §1, §2 #6 and #10's tape part read NIFTY for SENSEX (§1.1); #10 gains FRESH-AFTER (§2) |
| §1m HOLD v2 | `docs/setup-review/HOLD-V2-PREREG.md` (`fca358a2…d9a6`) | "The push → Source" for SENSEX positions (§1.2) |
| fold rev 6, display | `fold.py` REV "6" | only the FLOW read SHOWN for a SENSEX trade (§1.3); the engine itself is not touched |

**Not changed:** NIFTY's and BANKNIFTY's reads (BANKNIFTY keeps its own flow); every OI read on every index; fold rev 6's
word, give-up G, acceptance tally and events; HOLD v2's lock, gave-up, 15:20 and pass bar; §1g, §1h, §1i–§1o; the SENSEX
order-flow chart and the Tape tab (left as she said: nothing reads them); DECODE's SENSEX lines (stamped "patla").

`d` = +1 when the trade wants the future up, else −1 (SENSEX's own direction; the two indices move together, her premise).

---

## 1. The rule: for a SENSEX trade or slip, ORDER FLOW is NIFTY futures'; OI is SENSEX's own

Every flow read below is labelled **"NIFTY"** on the face. A NIFTY read that cannot be made says
`could not check — NIFTY flow not read (why)`. It never falls back to SENSEX futures.

### 1.1 Validate rev 3.1 (amends §1p)

- **#6 ORDER FLOW**, for SENSEX:
  - **EFFORT vote:** NIFTY's DECODE `effort`, by rev 3's own rule: NIFTY's latest fresh extreme in direction `d`, read
    within 15 min. Expensive high (≥ 2×) is AGAINST a long and WITH a short; cheap low (≤ 0.5×) is WITH a short and
    AGAINST a long; mirrors give no vote.
  - **QUADRANT vote:** NIFTY futures OI × NIFTY futures price over the last 10 min, with NIFTY's `B` and rev 3's
    thresholds and roll guard.
  - **The check:** rev 3's, unchanged (the EFFORT vote if any, else the QUADRANT vote).
- **#10 PAYING, the tape part,** for SENSEX: EXHAUST = NIFTY's DECODE `exhaust` on a leg in direction `d`. ABSORB =
  NIFTY's fight, her side the aggressor and absorbed. EXPENSIVE = NIFTY's effort at a high ≥ 2× (a long only). The
  **covering** part (SENSEX's payers' fronts) and **FRESH** (SENSEX spot) stay SENSEX's own. So a SENSEX spent pop CAN
  now fire; rev 3 §2 #10 "cannot fire under this text" is replaced.
- **#1 RIGHT NOW's flow part** (the prototype's FLOW chip, the newest fight within 30 min), for SENSEX: NIFTY's newest
  fight.
- **Unchanged for SENSEX:**
  - #2 (meter and EM-used, on SENSEX);
  - #3;
  - #4 and #5 (walls, ROLLING);
  - #8;
  - #9;
  - #10's base and its covering;
  - #7 (printed only).
- **Text replaced in rev 3:**
  - §1's "SENSEX not read (patla)" and "SENSEX: could not check (patla)" (#6), and §5's "It does not read SENSEX futures
    flow", become: *"For SENSEX, every order-flow read is NIFTY futures', labelled NIFTY; SENSEX futures flow is never
    read."*
  - The GO / WAIT / NO counts and thresholds are unchanged.

### 1.2 HOLD v2 Amendment 3 (amends §1m "The push → Source")

- **For a SENSEX position, a PUSH is a NIFTY push.** It is NIFTY's closed 5-min futures bar (her chart's GoCharting bar,
  with the Upstox bar for a slot GoCharting lacks), ranked against NIFTY's own history, by §1m's definition unchanged
  (SIZE ≥ p90, R ≥ 0.25). It is the push NIFTY's own line would see.
- **The line moves in SENSEX prices.** When such a push in direction `d` closes after her entry, the SENSEX line moves to
  **o + 0.25U** (▼; mirrored ▲). Here:
  - **o** is the open of SENSEX's own 5-min futures bar for the same slot;
  - **U** = max(σ of SENSEX's 5-min bars at that bar (market.js vwapSeries, as §1m), 0.1 % of o).
  
  As in §1m, it moves only when o lies between the current line and price, and only toward price.
- **A slot with no SENSEX bar:** that push is skipped and stamped `NIFTY push hh:mm · SENSEX bar ?`.
- **Unchanged:** the initial line, the profit lock (MFE ≥ 2R), SOMEBODY GAVE UP (SENSEX's own trend-side front, OI),
  15:20, FADE → RIDE.
- **Scope:** live (her windows, the one voice) **and** forward scoring of SENSEX setup entries, from the signing time.
  Each scored row is stamped `push_src` (`SENSEX-ux` before, `NIFTY` after). Rows before the signature keep their source.
  The pass bar is unchanged and both sources stay in their group, labelled.

### 1.3 The in-trade FLOW read shown for a SENSEX trade (the display of fold rev 6)

- **What is shown as FLOW** (the panel's FOLD board, the hold reply, Validate's in-trade row, the one voice's "why" and its
  ZONE ALONE trigger) is the **NIFTY engine's flow read**: the all-day NIFTY engine's flat FLOW chip (BUYERS / SELLERS /
  QUIET / CAN'T CHECK) at the same minute, mapped to her direction:
  - BUYERS: WITH when `d = +1`, AGAINST when `d = −1`;
  - SELLERS: the reverse;
  - QUIET: QUIET;
  - CAN'T CHECK: CAN'T CHECK.
  
  Its sentence is NIFTY's, prefixed "NIFTY flow:".
- **Not touched:** the engine's own state. Its word (HOLD / PAST GIVE-UP / FOLD), G, the acceptance tally and its events
  are rev 6's, computed on SENSEX's own futures prices, as today.

### 1.4 The trade map (display, `trademap.py`)

For a SENSEX trade, l4's `push` and `ulta push` are §1.2's NIFTY pushes, printed `NIFTY push ▼ 13:05 (N min)` and
`ulta NIFTY push ▲ … @ <SENSEX o>f`.

---

## 2. Validate rev 3.1, item 2: FRESH-AFTER for #10 (all three indices)

- **FRESH-AFTER**, all three of:
  - the 30-min running extreme in direction `d` (rev 3 §1's) was set **≤ 10 min** before `T`;
  - spot is within **1.5 strike steps** of it (NIFTY 75 pts, BANKNIFTY 150, SENSEX 150);
  - no newer extreme has been set since.
- **In #10 only,** FRESH **or** FRESH-AFTER satisfies the fresh-extreme part of the spent pop. Everything else in #10 is
  unchanged: the payers covering and the tape exhausted. FRESH-AFTER is stamped `pop khatam (N min after the high)`.
- **Why:** buying a few minutes after a covering pop topped is the same trap as buying at its top. The covering is done
  and the price is already coming off.
- **Disclosed, and the limit:** her 22 Oct 13:00 SENSEX entry (5 min after the 12:55 high, about 120 pts below it) was
  known when 10 min and 1.5 steps were chosen, and 1.5 SENSEX steps covers it by construction. These are a trader's
  numbers, not measured ones. That row is in-sample and can never count for this rule.

---

## 3. Fail-soft and stamps

- **A NIFTY read missing** (DECODE stale, no fut OI, no fight) is the same "could not check" rev 3 already has, with
  "NIFTY" in the reason. It is never a SENSEX read and never a zero.
- **Rev strings:**
  - Validate: `"3.1 (SENSEX-NIFTY-FLOW <sha8>)"`;
  - HOLD v2 rows: `push_src`;
  - the hold reply: `flow_src: "NIFTY"` on a SENSEX trade.

## 4. Flags (until the signature)

- Python: `sensex_flow.ON = False`. JS: `R31.ON = false`, in `engine.js`.
- **While OFF,** every face, log and score is exactly today's. The replay (§6) runs both ways.
- **At her signature,** both flip to ON in one commit. §1q is added to `context/research-findings.md` with this file's
  sha256, and the rev strings change.

## 5. Judging

- **Untested.** Validate rev 3.1 has no forward clock (the tab logs no presses, as in rev 3). The evidence that
  accumulates is the entry stamp and the hold shadow log, as in rev 3 §4.
- **HOLD v2:** §1m's paired pass bar, unchanged. SENSEX rows are labelled by `push_src`.
- **The replay in §6** is IN-SAMPLE description. It is never counted.

## 6. Disclosed: what was seen before this text was written, and what is to be replayed

**Seen before writing:**
- the rev 3 replay's words on 18 SENSEX entries (`docs/hold/validate3/REPLAY.md`: 22 Oct 13:00; 1 Oct × 9; 23–24 Sep × 8):
  each had #6 could not check and #10 "pop ?";
- the one-voice replay of 22 Oct 13:00–13:25 (`tools/voice_replay.py`):
  - at 13:01 the block said "why: … flow saath" from SENSEX's own futures;
  - HOLD v2 read "push ? ref nahi" all trade, and the line never moved;
  - EXIT at 13:24 on the initial line;
- NIFTY at 22 Oct 12:55: effort 1.0× at the high (rev 3 §6).

**Not run before this text was hashed:** no rev 3.1 vote, no NIFTY-push line and no NIFTY flow chip on any SENSEX trade.

**To be replayed, then shown to her before she signs** (described only, flags OFF vs ON):
- Validate's word on the 18 SENSEX entries, and on every NIFTY / BANKNIFTY entry in REPLAY.md (FRESH-AFTER touches all
  three indices);
- the one voice and HOLD v2's line over her 10 SENSEX trades: the 9 marked on 1 Oct and 22 Oct 13:00.

## 7. What this file does not do

- It does not read SENSEX futures flow anywhere.
- It does not average NIFTY with BANKNIFTY.
- It does not change any OI read.
- It does not change fold rev 6's word, G or acceptance.
- It does not change any threshold of §1i–§1o or the GO / WAIT / NO counts.
- It does not remove the SENSEX order-flow chart.

---

## 8. Revision 1 (2026-10-25, AFTER the replay; corrections of fact only, no rule changed)

The draft above was hashed `552d6927b6bee8d2cb7ea0dbf3e39d70aa5293f69fe22821e8c53d1db0ca73c9` before any replay. The
replay (`docs/hold/validate3/REPLAY-rev3.1.md`) found two statements in it that were not true of the code. They are
corrected here. Nothing in §1–§5 is changed.

1. **§7's "It does not read SENSEX futures flow anywhere" is too wide.** Read it as: *"No SENSEX futures flow is SHOWN or
   COUNTED as an order-flow read."* The price mechanics that use SENSEX's own trades stay as they are:
   - Validate's give-up G (#1's engine-now proxy, #9 ROOM) and its acceptance;
   - #3's expression facts;
   - fold rev 6's G and acceptance.
   
   §1.1 already listed #3 and #9 as unchanged. Moving them onto NIFTY would need a SENSEX price from a NIFTY fight,
   which this text never defined. It is a candidate for a later registration, not part of this one.
2. **§6's count.** `docs/hold/validate3/REPLAY.md` holds **24** SENSEX entries, not 18 (the 18 came from a truncated
   listing). All 24 were seen as rev 3 words before this text was written, and all 24 were replayed.

**What the replay showed (in-sample, described only):**
- **Validate:** no word changed on any of the 51 entries. #6 on SENSEX went from could not check to a NIFTY read: 8 WITH,
  16 NEITHER, 0 AGAINST. FRESH-AFTER was met on 3 entries; the pop was never spent, so no vote changed.
- **The one voice:** no state changed while she was in, on any of her 10 SENSEX trades.
- **HOLD v2:** its line moved on NIFTY pushes on three 1 Oct trades, all after her exits.
- **22 Oct:** NIFTY's flow chip turned AGAINST at 13:14, nine minutes after SENSEX's own tape (13:05).

---

## 9. SIGNATURE (2026-10-25)

- **Her word, verbatim:** "sign without 5".
- **Item 5 is §2, FRESH-AFTER** (the post-high pop window). It is **STRUCK**: not part of the signed rule, and not built.
  Validate's #10 keeps rev 3's FRESH.
- **Signed:** §0, §1 (1.1–1.4), §3, §4, §5 and §7, as corrected by Revision 1 (§8).
- **Text history:**
  - the draft hashed before any replay: sha256 `552d6927…73c9`;
  - Revision 1: `7284a18b…8a93`.
  
  This file, with this section, is the signed text. Its sha256 is recorded in `context/research-findings.md` §1q.
- **In effect from** the signing day, 2026-10-25: `sensex_flow.ON = True`, `FROM = "2026-10-25"`, engine.js
  `R31.ON = true`. Forward HOLD v2 SENSEX rows from then are `push_src NIFTY`; rows before keep `SENSEX-ux`.

