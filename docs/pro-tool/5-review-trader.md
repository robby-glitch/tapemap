# 5 · The trader's review of the final blueprint

**Written:** 2026-09-28, after the close. Read-only on code and data; nothing edited, started or committed outside `docs/pro-tool/`.
**Reviewer's chair:** twenty years of Indian index options, a footprint and a book on the other screen.
**What was replayed:** the blueprint's own engine (`scratchpad/pro3/reader_p3.py`, the `PF_*` column: FOLD_NEEDS=p3, MODE=fill, TRAIL_ON_BREAK=0) on the five recorded days, plus **19 new runs of my own** in `scratchpad/t5/` (`prereg.txt` written first, `run5.py`, `variant.py`, `variant2.py`, `metrics.py`, `expr.py`). Every number below is [M] from those runs unless tagged [I].

**Trades fixed before outcomes.** The blueprint's eight (six mechanical, two hand-picked) plus:
- **S1–S8**: the blueprint's §4 alternative, "SELL the other side", at the same second and strike as each of the eight, folded by the same engine with d flipped (§3.9). Never replayed before tonight.
- **R-A2, R-A4, R-A5**: the §5 re-entry read taken as a trade, chosen mechanically from the PF logs (first fixed win by her side after a print w back inside G). The blueprint offers this read as its answer to the whipsaw.
- Two rule variants, run to price two fixes rather than argue them: an acceptance floor (PA) and an expiry-afternoon trail (PX). A third (PB, trail after any bank or break) re-checks the judge's rejection.

---

## 1. Per trade: words, exit, give-back, flicker

Percentages are of entry premium. "Clause/h" is the text under HOLD (the headline itself changed 0–0.7/h, as the blueprint says). "Chips/h" is condition chips excluding FLOW, the blueprint's own exemption.

| trade | words over time | exit vs best | peak before exit → give-back | pullbacks | flicker |
|---|---|---|---|---|---|
| **A1** 22 Sep put 47.75, 09:39 (expiry) | BEHIND → TIRING 09:49 → BEHIND 10:32 → … PAST GIVE-UP 11:28, withdrawn 11:30 → FAILED LOW 12:01 → PULLBACK 12:18 → … FAILED LOW 13:50 → PULLBACK 14:12 → **FOLD 14:19 flow+OI** | **+77** · best +264 at 14:00 · 15:00 +108 | +264 → **187 pts given back in 19 min** | 11:28 poke past G held (+68, later +264); 12:18 held | 3.9 clause/h · 2.8 chips/h · 1 sound · VPIN CAN'T CHECK all day (no rows for 22 Sep) |
| **A2** 22 Sep call 43.65, 12:01 | PULLBACK → TIRING → BEHIND 12:19 → PULLBACK 12:49 → BEHIND 13:15 → TIRING 13:43 → PULLBACK 13:50 → **FOLD 13:51 at entry** | **−42** · best +78 at 14:21 | +13 → 55 | none held | 2.4 · 2.4 · 1 |
| **A3** 23 Sep put 122.3, 10:40 | BEHIND → TIRING 11:04 → BEHIND → TIRING 11:31 → PULLBACK 11:39 → **FOLD 12:04 at entry** | **−12** · best +3 | +2 → 14 | — | 1.2 · 3.0 · 1; OI chip flipped 9× on a 55L wall |
| **A4** 25 Sep put 111.6, 09:31 | NO READ → TIRING → BEHIND 09:39 → TIRING → BEHIND 09:51 → TIRING 10:04 → PAST GIVE-UP 10:07 → **FOLD 10:08 flow+OI** (n=3, 2.3 % dip; held breach would fire 10:09) | **+7** · best +42 at 12:57 · 15:00 −26 | +35 → 28 | none | 1.3 · **6.6** · 2 sounds; VPIN 16 flips |
| **A5** 25 Sep call 96.5, 09:39 | NO READ → PULLBACK 09:39 → **FOLD 09:47 at entry** (512 lots in 80 s) — its own falsifier: NOISE, back inside 49 s later | **−10** · best +53 at 14:06 | — | — | 0.4 · **7.1** · 2 |
| **A6** 28 Sep call 84.05, 09:31 | PULLBACK → TIRING → BEHIND → TIRING → PULLBACK → **FOLD 10:16 at entry** (308 lots in 58 s) | **−17** · best 0 · 15:00 −61 | — | — | 0.9 · 3.7 · 1 |
| **H1** 24 Sep put 102.65, 09:30 (hindsight) | BEHIND/TIRING/PULLBACK cycling **44 times**; PAST GIVE-UP 14:03, withdrawn 8 s later; **FOLD 14:39 held breach** | **+98** · best +154 at 13:59 | +153 → 55 | 09:47→10:56 (127→105) held; OI AGAINST at 10:55 (3.6 %, +3 %) rightly ignored | **8.0** clause/h, 9 within a minute · **6.7** · 1 |
| **H2** 28 Sep put 120.4, 09:30 (hers) | 25 clause changes; three W OI events (1.7 / 1.1 / 1.1 %, n = 1/3/1) all withdrawn; G **loosened** 22913 → 22924 at 13:34; **no FOLD** | **+71 at 15:00** · best +97 at 14:38 · she left +37 | +92 → 21 | 11:16→12:28 (182.7→154, 16 % of premium) held | 4.6 · 5.3 · 0 |

**The sums.** Blueprint: +172. **The six mechanical trades: +3 (median −11 %).** The two hand-picked trades supply +169 of the +172. That is not the engine's fault, but the blueprint's §3.8 table lets the reader miss it, and the gate table must not.

**Sellers (S1–S8).** Words and exit times identical to the buys (the engine never reads premium): +58, −40, −16, +9, −16, −31, +39, +60 = **+63** against the buys' +172. The at-entry fold spared S6 (short 22950 PE, 28 Sep) a −78 close at −31; S5 whipsawed exactly as A5 did.

**Re-entries (R).** R-A5 10:24 @101.7 → FOLD 12:57 **−29**, NOISE by its own falsifier (best +45 after). R-A4 11:17 @114.75 → FOLD 14:01 **−11**. R-A2 14:15 @68.35 (expiry) → **no fold, −43 at 15:00**; G loosened 23357 → 23341 at 14:38 while the call went 77.8 → 36.

---

## 2. What a pro sees

**1. The stop on a loser is honest.** Four of six mechanical trades were stopped at −10 to −42, three of them "REAL" by the 20-minute test, and A6 (the trade that cost money) went to −61 unstopped under today's rules. The at-entry mode is the one part I would run tomorrow.

**2. The whipsaw is real, and the blueprint's answer to it loses.** Acceptance on a busy open is a one-minute test: 4 of 12 acceptances stood 55–80 s (`med_bk_dur` is today's opening buckets). But I tested the obvious cure and it fails: a 3-minute floor (PA) turned A5 −10 into −19, A6 −17 into −25, A1 +77 into +58 (NOISE). The judge was right that a slower stop is not the fix. What he offered instead, the re-entry read, **lost all three times it fired**. Until the forward log shows otherwise, the whipsaw has no answer and the blueprint must say so instead of pointing at §5.

**3. The OI signature is ornamental where it fires and absent where it matters.** 21 W events across the eight trades; **12 fired on ≤ 3 updates**, dips of 1.1–3.9 % of the wall, and every one of those was withdrawn by a rebuild. The one mechanical trailed fold it co-signed (A4, 10:08, a 2.3 % dip) was followed by the wall growing 26 %; the held breach would have fired at 10:09 anyway at the same +7. Where a pro needed the writers' verdict (A1 at 14:00, H2 at 14:12) the event said nothing new. Requiring n ≥ 3 and ≥ 3 % [h] keeps 8 of 21 and changes no exit.

**4. The headline and the chips disagree at the moments that decide the day.**
- Her put, 14:12, where she left at +37: **HOLD · tiring 31 min**, ZONE quiet, FLOW quiet, OI quiet (22900 CE *stopped*), wall ahead 22850 PE *building*, VPIN with. By her own words ("OI stopped building … I will fold") three of four were not behind her. The blueprint's §0 says the screen would have held her; the screen's own chips would have sent her out.
- A1, 14:00, +264 %: **HOLD · failed low**, FLOW against, OI against (W off 9.9 % since 13:45), A off. Everything against, headline in ink.
A son reads the chips. The headline must name what is behind her, and when nothing is, say so ("HOLD · nothing behind you yet · out if 22924 accepted"). Never a count, never a colour: a sentence.

**5. Expiry afternoons have no protection, and the blueprint admits it.** A1 gave back 187 points of entry premium in 19 minutes with HOLD on screen because G sat 73 points (7B) away: from 13:01 to 14:15 not one seller-won fight fixed, so the staircase never stepped. R-A2 lost 47 % in 45 minutes with the future never near G; a 0DTE call dies inside its give-up and the engine, premium-blind, cannot see it. I priced the fix (PX): after 13:30 on expiry day, G steps to best − θ every bucket her way. A1's acceptance then came at 14:12:45 at **+199 %**; waiting for the OI event cost 54 points in three minutes (+86 at 14:15:47). On non-expiry days the same trail is harmful (H2 +35 instead of +71), so it must be expiry-afternoon only, with **plain acceptance** and no OI wait (the writers are closing anyway; v3 already said OI CAN'T CHECK on expiry). The judge's PB (trail after any bank/break) is confirmed bad: H1 +25, H2 +28.

**6. The expression is dead on arrival.** At all eight marks the wall ahead was *adding* (OI builds monotonically through an Indian morning; 22850 PE went 115 → 124 L in the six minutes before her mark), so §4's table prints **SELL at every one of the eight marks**, including the +264, +154 and +97 buys. The sold side made +63 against +172. "Not adding" must be relative: the wall's pace against its own morning slope or against the other side's, or the BUY leg never fires before noon. Untested against R2/R4; the table needs a replay before it is registered.

**7. The chip gate is not met.** Ex-FLOW, three of eight trades ran 6.6–7.1 changes/h; ZONE flipped 12–22 times on H1/H2/A4/A5, VPIN 15–16 times on 25 Sep. The clause under HOLD changed 44 times on the best trend day. The blueprint says P2-04 will fix ZONE and VPIN; that is a promise, and the amendment is rightly not signable until the table exists.

**8. G loosened twice** (H2 13:34 by 11, R-A2 14:38 by 16), both on a "win" printed at a worse price with a wider trapped shelf. "Locked once touched" is not enough: a stop that widens is not a stop. Never loosen, ever.

**9. The sale gets a buyer's words.** TIRING is amber-ish for a buyer and good news for a short; PULLBACK is the seller's friend. Same engine, same numbers, different sentences: the seller's face needs its own three clauses, and short gamma on expiry (S6 worst −110 %) needs the expiry rule in §2.5 more than the buyer does.

**10. Data.** 22 Sep has no prior session on disk, so A1's and A2's bucket comes from the day's own first 15 minutes (not causal) and VPIN has no rows at all; the blueprint's biggest winner sits on its weakest plumbing. Report it in the gate table.

---

## 3. Would a pro trust it?

**As a stop-keeper on losers and a hold-supporter on trend days: yes, in shadow.** It kept H1 to +98 of +154 and her put to +71 of +97 through a 16 % pullback, and it stopped the 28 Sep call before −61. Line 2, the frozen FOLD and the one sound are the right shape; nothing flashes.

**As an exit engine for winners and a screen for the expiry afternoon: no.** Its two mechanical winners captured +7 of +42 and +77 of +264. Its answer to the whipsaw lost three of three. Its OI signature co-signs nothing a pro would sign. Its headline says HOLD while its own chips say leave. Its expression would have sold every day it should have bought.

The forward log will decide, but a father would not hand this to his son as it stands; he would hand him the at-entry stop, line 2 and the wall-ahead numbers, and keep the rest in shadow.

---

## 4. MUST-FIX, ranked

1. **Headline ↔ chips coherence (§3.6).** HOLD must carry what is behind her; when nothing is, the clause says so. Measured contradictions at H2 14:12 and A1 14:00. Wording, not a rule change: it still goes in the amendment as §8's text.
2. **Expiry afternoon (§3.5, §8).** After 13:30 on expiry day, trailed mode: G = best − θ on every bucket her way, fold on plain acceptance (no OI wait), and the premium line splits intrinsic / extrinsic. Measured: A1 +199 at 14:12 against +77; R-A2's silent −43 becomes visible.
3. **Stop calling the re-entry read the answer to the whipsaw (§1 #1, §5).** 0 of 3 in replay. Register it as a read with its falsifier, present it as unproven, and add "whipsaw within 20 min" as an at-entry outcome column so the log can rank it against the 2-close floor (which loses here too).
4. **OI event floor (§3.5): n ≥ 3 updates and ≥ 3 % [h] of the wall.** 12 of 21 events vanish, no exit changes, and the OI chip stops flipping 9 times on a 55 L wall.
5. **The expression's "not adding" (§4).** Relative to the wall's own pace or the other side's; replay before registering. All eight marks read SELL under the literal rule.
6. **The gate table (P2-04) must exist before signing**, split **mechanical / hand-picked / sold**, with each trade's peak-before-exit and give-back columns, not sums.
7. **G never loosens** (§3.3), touched or not.
8. **Seller clauses (§3.9):** three sentences of the seller's own for TIRING, PULLBACK, BEHIND YOU; the expiry rule of item 2 applies to the short with priority.
9. **Chip gate:** ZONE event-born and VPIN 2-close exit measured on all five days before the face is offered (ex-FLOW 6.6–7.1/h on three of eight today).
10. **22 Sep plumbing disclosed** in every table that uses it: non-causal bucket, no VPIN rows.

**Score: 5 / 10.** Up from v2's 6 in design and calm; down in what the replay shows once the eight are split and the sale and the re-entry are run. The at-entry stop and the face's shape are professional. The winner exit, the expiry afternoon and the expression are not yet.
