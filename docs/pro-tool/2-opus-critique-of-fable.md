# Opus cross-examines Fable's blueprint

**Written:** 2026-09-28, after the close. Read-only. Nothing was edited, started or posted outside this file.
**The chair:** the desk, with her trade on, reading Fable's screen at the moment it matters.
**Checked against:**
- Fable's own replay traces, `scratchpad/fb/*.txt` and `reader7.py`;
- `data/chain/chain_NIFTY_2026-09-28.jsonl` and `data/book/book_NIFTY_2026-09-{24,28}.jsonl`;
- the extension's `src/engine/fit.js` and `adapter.js`.

**Tags:** [M] measured, [I] inferred.

---

## 0. The verdict in five lines

1. Fable's engine and mine are about 80% the same: H v3, give-up G, her wall W, the OI event, acceptance, one engine behind two faces, and no GO. The disagreements are few, and they are where the money is.
2. **Its one entry refusal would have said NO to her own best trade today** (§1.1).
3. **Its AT THE WALL · giving claim for her put is contradicted by the chain** (§1.2). As specified, the clause would flicker, and it would tell her to bank early.
4. **Its replay table misreports its own engine** (§1.3). On the trade that cost her money, its location rule exits later and 8 points worse than plain acceptance.
5. **It is better than mine in three places,** and I take all three (§6). The biggest: its held-breach exit closes a real hole in my winner mode.

---

## 1. Claims checked against the data and the code

### 1.1 The one refusal, run on her 28 Sep put [M] inputs, [I] verdict

Fable §3 says: NO when "the room to the wall ahead is less than the distance to G". It uses its one wall rule (§6.1): "the nearer of the top two OTM strikes by day-high OI beyond the forward by w".

At her 09:30 entry:

| input | value |
|---|---|
| forward (K + CE − PE, 6 nearest strikes) | 22940.6 |
| future | 22941–22949 |
| top two OTM puts by day-high OI | 22900 PE (126.6L) and 22800 PE (124.1L) |
| wall ahead A (the nearer) | **22900** |
| room | **≈ 41 pts** |
| give-up G, from Fable's own trace (`H2_0928_PE.txt`) | 23013 at 09:30:29, then 22997 at 09:30:49 |
| distance to G | **56–72 pts** |

Room is less than risk, so the screen says **NO** on the put that went to **+97%** and was still +71% at 15:00.

This is not bad luck. It is the rule's logic. On a trend day the first wall ahead is the one that *gives*, and a giving wall is her fuel. Capping room at the first wall refuses exactly the trades where writers get run over.

**Mine shares the ratio, in a softer form.** My expression says BUY only when room ≥ distance to G, so at 09:30 it would have said SELL the CE. On a down day that is her own practice and it would have paid. It is still the same defect, and I carry it into the fix (§6).

### 1.2 "Her put: at 22850 PE 10:42–13:16, giving all along [M]": false by the chain

The 22850 PE open interest, from the chain file:

| time | OI | running peak | off peak |
|---|---|---|---|
| 10:42 | 120.9L | 122.1L (10:40) | 1.2 |
| 11:00 | 113.5L | 122.1L | 8.6 |
| 12:00 | 120.1L | 133.3L (11:53) | 13.2 |
| 12:30 | 135.4L | **new high** | 0 |
| 13:16 | 134.2L | 145.7L (12:51) | 11.4 |
| 14:01 | 151.3L | **new high, 151.7L** | 0 |
| **14:28** | **96.6L** | 151.7L | **55.2** |

The floor made **seven new highs** between 10:40 and 14:01. It was *building*, with ±10L breathing. The real give was one event: **−55L in 27 minutes, 14:01 → 14:28**, just before the break that took the put from about +60% to +97%.

Three problems follow.

- **Flicker.** "Giving" is "A off its peak", which is the same OI event as W's. On this strike it fires on the 11:00, 12:00 and 13:16 dips and withdraws on each new high. So the clause would have toggled holding ↔ giving all day, not stood still.
- **The wrong nudge.** On every "holding" stretch the face prints "pros bank into a holding wall". That puts a bank line under her put at +20% to +45%, on the trader whose stated problem is "holding trades for longer".
- **The one moment that mattered was not distinct.** The 14:01–14:28 unwind looked no different from the morning's 10L dips.

Fable's trace does not produce this word. `reader7.py` hides the `(ahead)` lines (L618), and no AT THE WALL state is computed there. The [M] tag sits on a reading that was never run.

### 1.3 The replay table versus its own traces

Fable's GAVE UP fires on **either** flow + OI **or** the held breach, whichever comes first. Its table reports the held time even where flow + OI fired first.

| trade | flow + OI (v3) | held (A) | Fable's engine should say | Fable wrote |
|---|---|---|---|---|
| 22 Sep put | 14:19, +77 | 14:24, +70 | **+77** | +70 |
| 22 Sep call | −42 | −45 | **−42** | −45 |
| 23 Sep put | −12 | −14 | **−12** | −14 |
| 25 Sep call | 12:47, −19 | 12:50, −21 | **−19** | −21 |
| **28 Sep call** | never | **10:18, −25** | −25 | −25 |

Plain acceptance, which is my loser mode, fired on the 28 Sep call at **10:16 at −17** (`A6_0928_CE.txt`, the "flow" row). On the trade that cost her money, Fable's extra "2 more closes and 2× the median time" costs 2 minutes and 8 points of premium.

On the 25 Sep call, my acceptance exits at −10 on a whipsaw (the trade later ran to +53). Fable's time floor avoids that whipsaw, then exits at −19 anyway. **On losers, its confirmation never bought a better exit** in these 8 trades [M].

### 1.4 Other claims: confirmed

| claim | result |
|---|---|
| The book starts 09:17:01 (24 Sep) and 09:17:19 (28 Sep) | **Confirmed** [M] |
| Spot runs 20–45 pts under the forward | **Confirmed.** Today 24–46 [M]; my "33–49" was too narrow. |
| `fit.js`: with no date tick, every day is a candidate | **Confirmed.** It is `src/engine/fit.js:194/203`, not `src/shell`. |
| `adapter.js:133–151` carries BUY/SELL tick sides | **Confirmed** |

---

## 2. Where it would lose her money, or hold and exit badly

1. **The entry NO** (§1.1). It refuses trend trades at the first wall and passes box trades where the wall is far.
2. **Banking on the wrong trade.** The wall ahead is picked against the *forward*, not her *entry*, and AT THE WALL has no profit condition. On the 28 Sep call (entry future 22950, price 22880–22900 from 10:27 to 11:41) it would print "22900 CE · holding · pros bank into a holding wall" while she is at −25% to −30%. "Bank" on a loser teaches the son the wrong word. In a loser the only honest word is where the trade is wrong.
3. **Its SELL misses how she sells.** Fable sells the other side only in a box ("both walls building and VPIN quiet"). Her practice (how-she-sells, 26 Sep) is to sell ATM or ITM *with the trend*. That is the 24 Sep day, when the window folded 11 sold calls that expired at ₹0.10. Fable's rule never says SELL on a trend day.

   The BUY half keys on "the newest fight her way was INITIATIVE". Fights flip at 4–8 words an hour on trend days (8.0/h on 24 Sep, its own trace), so the expression would flip with them.
4. **"GAVE UP" persistence is unspecified.** The doc does not say what the face shows after the fold if she stays in. (Mine: OUT until she presses I'M OUT.) On the 28 Sep call the acceptance withdrew at 12:29 and came back at 12:34. A son will act on whatever the word reverts to.
5. **Premium at G on expiry.** Tomorrow, 09-29, is expiry, and Fable's "premium there [I]" gives no method. The linear delta form under-states the give-back on gamma. On 22 Sep it read +113% where the fill was +77%.

---

## 3. One glance, and flicker

- **Amber means "watch", but "giving" is her fuel.** Fable colours the "giving" clause amber. For a put buyer, writers leaving the floor ahead is the good news, and it is painted in the warning colour.
- **Precedence hides the live read.** AT THE WALL outranks TIRING and BEHIND YOU. For the hours it stands, she cannot see whether her side is still winning fights.
- **No chip budget as a gate.** Its own traces show chip changes of 8.4/h (her put), 9.2/h (25 Sep call) and 11.6/h (24 Sep). "2 bucket closes" did not tame ZONE and VPIN, and Fable sets no acceptance gate. My ≤ 6/h gate fails on half the trades too, but at least it is a gate.
- **"One wall rule" is three rules.**
  - W is "the most OI between the forward and G".
  - A is "the §1d wall".
  - §6.1 is "the nearer of the top two by *day-high* OI".

  Day-high also keeps a wall that has been abandoned: by 14:28 the 22850 PE still ranks on its 151.7L peak while only 96.6L remains.

---

## 4. Constraints and buildability

- **The live face ships before any shadow period.** Fable Phase 1 puts `fold.py` and the IN A TRADE face live, and closes rev 5 in the same phase. There is no forward shadow, and no restart-replays-identically test before she relies on it. The amendment would also register the entry face, the refusal and the expression (built in Phase 4) before a single replay of them. §1.1 shows why that matters.
- **Chart trust comes after the roll.** Chart trust, contract match and contract stamps are Phase 2, "next week", while "before Wednesday's open nothing else touches the live path". Wednesday 09-30 is the first October session. The session-jump bug and a Sep/Oct mismatch stay live on exactly the day they bite.
- **The Trade tab is hidden from the strip.** Her order was to keep the Trade tab's chart. Hiding the tab needs her word; it is not a cut an agent makes.
- **It asks her for numbers.** It keeps `FOLD_NEEDS` as a switch and asks her to pick the held-breach close count. She asked us to decide as traders. A knob on the stop rule is a knob a son turns mid-trade.

---

## 5. Data defects it leans on without facing

**Resting liquidity at the give-up.** Fable calls this "the best give-up tell". The book's 5 levels span a **median 2–4 pts, 90th percentile 4–8 pts** [M] (28 and 24 Sep). G sat 18–72 pts from price on her put. The book cannot see offers at G until price is already there. It is a touch read, not a lead.

My blueprint says "within θ of G", which is the same over-promise. Both of us should say "within the visible book, about 4 pts".

---

## 6. Where Fable is better, and what I take

**1. The held breach as the winner's location exit.** This is the big one.

My winner mode waits for W's OI event, with a backstop only at her entry. OI's known ceiling is that a slow bleed never fires. So my winner could hand back the *whole* profit on a writer bleed and still read PAST GIVE-UP. That breaks "a winner never becomes a loser" in spirit.

Fable's held breach (acceptance standing 2 more closes and ≥ 2× the median bucket time, with no win and no print w back inside) closes that hole. It also took the 24 Sep trend at **+98%** where mine took +81%.

**Taken:**

| mode | exit |
|---|---|
| loser | acceptance alone (unchanged) |
| winner | flow + OI, **or** the held breach, whichever comes first |
| backstop | the entry backstop stays under both |

Adding the columns of the existing traces [I], not rerun: 22 Sep put +77, 24 Sep +98, 25 Sep put +7, her put +71, losers −42 / −12 / −10 / −17. That sums to **+172**, against +155 for each blueprint alone. n = 8: this is a description, and the forward log keeps all three columns.

**2. A silent wall-ahead state, in place of my BANK ZONE tone.**

My BANK ZONE sounded at +28% and +48% on her put before +90%. That is two pings nudging the trader who cannot hold to leave early.

**Taken:** no sound, and the holding/giving clause. With my fixes, as a trader would want it:
- **profit-gated:** only when G is past her entry;
- **event-born:** "22850 PE writers pulled 55L since 14:01 [M]", frozen with its time, never a standing state;
- **"giving" in ink with her-side colour,** not amber.

**3. Data honesty and scope.**
- **SENSEX never borrows NIFTY's clock.** Mine used NIFTY's median bucket time for SENSEX acceptance. That is wrong; Fable is right.
- **Record the October future on 09-29,** so Wednesday's bucket and B come from the October contract's own record.
- **More chart-trust checks:** fitted date = feed date, latest bar within one bar.
- **Falsifiers for TIRING and FAILED** (a new extreme by θ). Mine had none.
- **Three screens: DESK, WAR, RECORD,** folding Board into the flat half of DESK. It is fewer places to look than my six. I take it subject to her review of the Board mockup, which is hers to decide.

**4. The expression (not Fable's, but triggered by §1.1).** Room is printed, never a refusal. The expression drops the room ≥ risk ratio. Selling ATM/ITM *with* the trend becomes a first-class choice, not only in a box. The refusals stay the three amber clauses: past give-up, at the wall ahead, after 15:00.

---

## 7. What neither blueprint solved

- **The 15-minute expiry-gamma V.** 22 Sep's +264% → +77%. No structure trail catches it.
- **Words at 8/h on trend days.** Both of us inherit this.
- **The early-bank pull on her own put.** Both designs, as written, drew a "bank" line or tone at +20% to +48% on the day's best trade. The fix in §6.2 is the least we owe her.
