# REV 6: THE PRO TOOL, one amendment (not yet signable)

**Written:** 2026-09-28, late evening, by the judge, after the trader's and the safety reviews. Before any code; UNTESTED.
**The design it registers:** `docs/pro-tool/6-blueprint.md` (§ numbers below point there). It replaces `4-amendment-draft.md`, which is never presented.

**How this file becomes signable, in order:**
1. She reads it and **commits it**. Her commit fixes its sha256 and its time; that commit, not a file's modification time, is the proof of order.
2. Package P2-04 then runs the gates and writes `docs/pro-tool/6-gate-table.md`, **after** that commit. It reports the design days (22–28 Sep, on which every (h) threshold here was chosen) apart from the unseen days (29 Sep, expiry; 30 Sep, the roll).
3. If every gate in §8 passes, she signs. If one fails, this file is not presented; a revised file gets a new commit and a new hash, and the gates run again.

**This file is never edited after her commit.** Nothing is filled in inside it. Her signature, the time, this file's sha256 and the in-force date are written only into `context/research-findings.md` as **§1i**.

**What she is asked for:** one signature. No switch, no count, no knob.

---

## 1. What this changes, in plain words

**Today** the window folds you on a 3-minute close past a session-high line, a trend vote, a 15-minute quiet clock, then a latch that keeps FOLD on the screen all day. Validate says GO / WAIT / NO from the same line and trend. The expression reads only at 3-minute closes, against the chain's spot. **You use none of those.**

**After this amendment** there is one engine for your marked trade, on your four reads: zone, order flow, OI and VPIN.

- **Until your stop has trailed past your entry:** you are out when price is *accepted* past your give-up: a bucket of real business traded there, for a normal stretch of time, without coming back.
- **Once it has trailed past your entry, it gives you rope.** You are out on the first of:
  - price accepted past the give-up **and** the writers defending you really coming off their peak (at least 3 updates and 3 % of the wall);
  - that acceptance holding two more buckets;
  - price accepted back through your entry. A winner never becomes a loser.
- **Expiry day after 13:30:** once you are trailed, your give-up follows your best price, and acceptance past it is enough. Expiring writers leave for their own reasons then; waiting for them costs gamma.
- **Your give-up only ever tightens.**
- **The screen says HOLD, PAST GIVE-UP, FOLD, or CAN'T CHECK** when it cannot see. Under HOLD it says what is behind you and what is against you, or "nothing behind you now, nothing against you". Quiet is not against.
- **Line 2 always says, before it happens, exactly what would take you out.**
- **One sound: FOLD, once.** FOLD stays on screen until you press I'M OUT; the live read keeps printing under it.
- **The tool never tells you to bank.** It shows the wall ahead as numbers, your premium's peak and what you have given back; on expiry day, how much of your premium is time.
- **No GO / NO before entry.** You see what the screen would say if you were in.
- **Buy or sell** is read from the wall ahead against your defenders, with both numbers printed, frozen when you open the mark row. It shows only once it has proved it is not stuck on one answer.
- **Every price judgement** (ATM, in the money, "beyond the wall") is made against the options' own forward, never the chain's spot print.

---

## 2. What it closes

**No signed file is edited.** The closures are recorded only in `research-findings.md` §1i, which lists the table below. §1e–§1h and every PREREG file keep their text and their hashes.

**In force from:** the first session in which the rev 6 face (blueprint §11, Phase 3) is live. Until then every section below stays in force and keeps writing its rows. That date is written into §1i when it happens. Rows of the closed sections stay their own population, never pooled with rev 6's. Rev 6 rows written before that date carry `shadow: true` and are a third population.

| signed text | sections closed | what replaces it |
|---|---|---|
| `PREREG-merged.md` rev 4 (§1e) | §1, §2, §3 (verdict rules 1–8 and the entry-check copy), §4, §5, §6 (SLOPE 15, which front, the ladder window, trend rows, the quiet clock, the latch), §7, §8 (`hold_<day>`, `side_<day>`), §10–§11 | Blueprint §4 (the engine), §4.7 (what is shown, one sound), §4.10 (writers), §7 (faces); the logs in §5 below. §9 and §12 stay as history. |
| `PREREG-rev5.md` (option B) and `PREREG-rev5-COPY-1.md` | §A (incl. the latch A.0.5 and heal A.0.6, A.2 option B), §B, §C ("adding beats a live fold"), §D (incl. COPY-1's writer sentences), §F (clause 7-B and its clocks), §G | Acceptance past G (§4.5). The frozen FOLD with a live line under it (§4.7). |
| `VALIDATE-PREREG.md` rev 2 (§1g) | §1.2, §1.3, §1.4, §1.6, §2 (GO/WAIT/NO), §3, §4, §5 | IF YOU WERE IN (blueprint §5). **§1.1 "Your setup" stays** as the ZONE row's sentence, never a vote. |
| `EXPRESSION-PREREG.md` rev e (§1h) | §A.2, §A.3 facts 1–4, §A.4 R1 and R5, §A.5, §B, §C ("fold as today"), §E, §F.1 | The expression in blueprint §5. **R2 and R4 stay in force.** §C's substance (no reach, no strike stop) carries over. §A.8 and §D are history. |
| `PLAN-PREREG.md` rev 3 (§1f) | §2.1–§2.6, §3, §5, §6 | STOP → G and line 2. NEXT RUNG → the wall ahead A, as numbers. **§2.7's band stays** as a printed level, never a target or a verdict. |

**Not touched, and not closed by this signature:** §1d, the fade gate, with its own wall rule and reference; the zone machine and its 09:25 anchor; `data/trigger_log.jsonl`; the thesis table for four roles; "premium is never an input to the verdict"; her 15:00 practice (a display reminder, never a rule).

---

## 3. What it registers (every rule is the blueprint's text; thresholds marked (h))

1. **Units (§4.2).**
   - bucket = 3 (h) × the median 1-min volume, pooled over ≤ 5 (h) prior sessions of the **front-month** series; a day with none uses its own first 15 minutes, flagged;
   - B = today's median 1-min range; θ = 2B, w = B/2 (h);
   - F\* = the future less its median basis to (K + C − P) over the last 15 (h) chain minutes, |Δ| > 0.3; fewer minutes are used and tagged "basis n of 15 min"; before the first chain snapshot, F\* does not exist and moneyness reads "could not check".
2. **Fights, levels, traps, G and W** as H v3 §4, §6.1, §7.1–7.3, with one change: **G never loosens.** It is seeded at the mark, re-set on her side's wins only when tighter; a refused loosening is logged.
3. **One wall ranking (§4.4):** current OI, near-ATM, beyond F\* by w, a 2-close hold. W behind her, A ahead. §1d excepted.
4. **The OI event:** on W, a drop ≥ 3 (h) σ √n from the since-reference peak, σ = 1.4826 × the median |ΔOI| over the 15 updates before the peak (floor 1 lot), **and** n ≥ 3 (h) updates **and** ≥ 3 % (h) of the peak. Withdrawn by a rebuild above the peak, or by a new G.
5. **Acceptance:** 1 (h) bucket of lots at or beyond G, over ≥ the session's median bucket duration; a print w back inside restarts it, or withdraws it. No tally and no OI event spans a data hole.
6. **The mode:** *trailed* when d·(G − E) > 0, E the future at her mark; else *at entry*. Never shown as a word.
7. **FOLD:**
   - *at entry:* acceptance beyond G;
   - *trailed:* the first of (acceptance **and** a live OI event on W, same epoch), the **held breach** (2 (h) more bucket closes and ≥ 2 (h) × the median bucket duration, no win by her side, no print w back inside), or the **backstop** (acceptance beyond E ∓ w);
   - *trailed, expiry day from 13:30 (h):* G steps to the best future since entry less d·θ at each bucket close her way (tighten only), and acceptance beyond G folds with no OI wait. **Designed on one expiry trade (22 Sep); flagged post hoc.**
8. **The headline:** HOLD · PAST GIVE-UP · FOLD · CAN'T CHECK.
   - HOLD's clause is built from the four reads in her order: "behind you: …", "against you: …", or "nothing behind you now, nothing against you". Never a count.
   - The tape words (won, pullback, failed extreme ≥ w beyond and rejected ≥ w, TIRING: 5-bucket window, 2 in, 2 out (h)) live in the FLOW row.
   - For a sale, the seller's three sentences (blueprint §4.7).
   - Words computed once per event batch.
9. **CAN'T CHECK** (blueprint §4.6): no G; order flow silent ≥ 30 (h) s in hours; a TapeMap downtime hole. A chain older than 180 (h) s blinds the OI row and the flow + OI fold only, and line 2 says so.
10. **Line 2:** the out-condition, stated before it happens, in the four forms of blueprint §4.7.
11. **After FOLD:** frozen, with the live line under it, until I'M OUT or unmark. One sound per epoch; ids kept, so a reload is silent.
12. **The four rows** ZONE · FLOW · OI · VPIN: ZONE event-born, and its sentence agrees with its chip; FLOW event-born; OI from W's events; VPIN in at lead ≥ 2 of 10 buckets, out only after 2 (h) closes past zero; condition-born changes need 2 (h) bucket closes.
13. **Premium at G and at A [I]:** the chain's own price at K′ = K + F\* − G (or A), interpolated; older than 60 (h) s reads "could not check". **On expiry day** the premium line splits in-the-money and time value [I]; the engine never reads it.
14. **The wall ahead:** numbers only, in every mode (strike, points, OI, its peak and time). Never a word, a colour for side, or a sound.
15. **The entry face,** IF YOU WERE IN, no word, no refusal. Three amber clauses: "past your give-up", "at the 22900 PE writers (n L)", "after 15:00".
16. **The expression:** BUY / SELL the other side / EITHER.
    - BUY: the newest fixed fight her way was initiative **and** the wall ahead's OI grew less, as % of its own over 6 (h) min, than her defenders'.
    - SELL: the wall ahead grew at least as fast; or her side's last win was absorption; or TIRING is live.
    - EITHER: otherwise. No calendar votes. Both numbers printed with the word.
    - Read at bucket closes, confirmed on 2 (h), frozen when the mark row opens. R2 and R4 kept.
    - **Printed on the face only if the gate table shows it reads both BUY and SELL across the design and unseen marks.** Otherwise it reads "not showing you: the buy-or-sell read is in test", and its rows continue.
17. **Flat:** NEXT FIGHT with its two confirmations; the SELLERS / BUYERS GAVE UP event, frozen and silent; **the re-entry read after a FOLD, silent and printed as unproven** (0 of 3 in replay).
18. **Writers:** the same engine with d flipped; her short strike against F\* is always a level. **SENSEX:** its own clock; FLOW and VPIN read "could not check" with the lot count.
19. **Absence:** three sentences, never one. A missing value is never a zero. Every number is [M] or [I].
20. **Shadow before force:** until the in-force date, the engine logs during hours and is shown only in RECORD after 15:30, unless she asks for it live.

---

## 4. Predictions and falsifiers (committed now; forward rows only; counts, never rates on screen)

| read | wrong if |
|---|---|
| FOLD, at entry | trading comes back w inside G within 20 (h) min (**the whipsaw column**) |
| FOLD, flow + OI | the same, or W rebuilt above the event's peak within 20 min |
| FOLD, held breach | back inside G by w within 20 min |
| FOLD, backstop | back inside E by w within 20 min |
| FOLD, expiry afternoon | back inside G by w within 20 min, **or** the premium at +20 min above the FOLD premium |
| PAST GIVE-UP | it ended withdrawn (counted against those that ended in a FOLD) |
| CAN'T CHECK | not falsifiable; each stretch counted with its length and why |
| "against you" clause | not followed by a FOLD or PAST GIVE-UP within 20 min (counted, not killed) |
| re-entry read | G accepted again within 20 min |
| SELLERS / BUYERS GAVE UP (flat) | price back through the level by w within 20 min |
| the expression, BUY | the premium at +20 min below the entry premium while the future moved her way by ≥ θ |
| the expression, SELL | the sold option's premium at +20 min above its entry while the future moved her way by ≥ θ |

---

## 5. The forward logs (write-once, additive)

**`data/fold/fold_<IDX>_<day>.jsonl`**, one row per event and one per bucket close per marked trade. Never one per batch.

- **Horizon:** every trade is logged from its mark to 15:29, whatever she does; rows after her exit carry `after_exit: true`. Scoring stops at 15:00, her practice.
- **Close-time import:** her tradebook through `/api/hold/import` is replayed causally as `src: "import"`, never pooled with `src: "marked"`.
- **Resume:** a restart recomputes causally from the recorded inputs (a book row by its arrival `t`, a chain row by its own `ts`). Words already logged win on screen and are not re-emitted; a difference writes a `diverged` row.

```
{rev: "6", shadow, day, ts, idx, ik, expiry, trade_id, src, after_exit,
 side, role, d, strike, qty, entry_t, E, p0,
 units: {bucket, B, theta, w, med_bucket_s, pooled_sessions, basis_minutes},
 mode, expiry_pm, G: {px, why, set_t, locked}, W: {k, side, oi, peak, peak_t},
 A: {k, pts, oi, peak, peak_t},
 event: seed|reset|lock|refused_loosen|touch|tally|accepted|withdrawn|oi_event|oi_withdrawn|
        held|backstop|expiry_trail|fold|past_give_up|clause|chip|cant_check|hole|diverged|bucket,
 headline, clause, line2, chips: {Z, F, O, V},
 prem: {now, peak, peak_t, at_G, at_A, chain_age_s, intrinsic, time},
 alt: {plain_accept: {t, prem}, flow_oi: {t, prem}, held: {t, prem}, backstop: {t, prem}},
 sound_id, thresholds_sha, code_sha, tag: {M: [...], I: [...]}}
```

**Outcome rows** are written once, 20 minutes after each falsifiable read: `{ref_id, read, verdict: real|noise, why}`.

**Also rev "6", each its own file, never pooled with rev 2 or rev e rows:** `data/fold/flat_<IDX>_<day>.jsonl` (next fight, confirmations, GAVE UP events, re-entry reads); `data/hold/check_<day>.jsonl` (IF YOU WERE IN at each press); `data/hold/expr_<day>.jsonl` (the expression at each bucket close and at the freeze).

---

## 6. The kill conditions (the pass bar is stated before any rev 6 row is read)

**The clock:** 30 sessions from the in-force date. Fewer than 15 cases for a clause means **inconclusive, and nothing changes** (the house rule). Shadow rows never count toward it.

1. **A FOLD on arrival is a defect, not a result.** A FOLD whose OI peak or acceptance tally began before her mark sends the face back to shadow until fixed. Counted.
2. **HOLD inside a data hole is a defect.** Any HOLD printed while §3.9 says CAN'T CHECK sends the face back to shadow until fixed.
3. **The at-entry rule is killed** if, with ≥ 15 at-entry FOLDs, the noise verdicts (the whipsaw column) outnumber the real ones. Its replacement comes back as a new registration; candidates on file: the 2-close floor, or the re-entry read, whichever the log ranks better.
4. **The trailed rule** (non-expiry) is tested against **one** named alternative, **the held breach alone**. With ≥ 15 trailed trades that folded: if the held breach alone exited at a better premium than rev 6's first fire in at least two-thirds of them, it replaces rev 6's trailed rule by a new registration she signs. Otherwise rev 6 stands. The other logged columns describe; they cannot replace.
5. **The expiry-afternoon rule** is killed if, with ≥ 15 expiry-afternoon folds, its falsifier (§4) is met in more than half. Until then it is inconclusive and stands.
6. **The face's noise budget** is killed if, on ≥ 5 sessions: the headline changed more than once an hour in any trade; or a FOLD sounded more than once an hour; or the condition chips ex-FLOW changed more than 6 times an hour (median over the session's trades). The face returns to shadow; the rows continue.
7. **The expression** is killed as a read (it stops printing; its rows continue) if, with ≥ 15 BUY or ≥ 15 SELL reads at her mark, the §4 falsifier is met in more than half of that side's reads.
8. **Not a kill; logged for her, counts only:** each trade where she pressed I'M OUT while HOLD showed, with the premium 20 and 40 minutes later, and which clause was on screen ("nothing against you", "against you: …"). This is the question the tool exists for: does it help her hold?

---

## 7. What she signs (written into §1i, not here)

> "I sign rev 6, the file committed at <commit>, sha256 <hash>. It closes the sections in its §2 from the first session its face is live; their rows stay their own. It registers its §3–§6. §1d, the zone, its 09:25 anchor and trigger_log are untouched."

§1i then carries: her words above, the time (IST, by the clock), and later one added line, "in force from <date>", when the face goes live.

---

## 8. The gates (`docs/pro-tool/6-gate-table.md`, written by P2-04 after her commit)

Design days 22–28 Sep and unseen days 29–30 Sep are reported apart. Trades are split mechanical / hand-picked / sold / re-entry, each with exit, best, peak-before-exit and give-back, never sums alone. 22 Sep carries its note: no prior session on disk, no VPIN rows.

**All must pass for her to be asked to sign:**
1. No FOLD on arrival, on any day.
2. FOLD sounds ≤ 1 an hour; headline ≤ 1 change an hour, per trade.
3. Condition chips ex-FLOW ≤ 6 an hour (median over the day's trades), with ZONE event-born and VPIN's 2-close exit.
4. CAN'T CHECK printed over every data hole found on disk; never HOLD inside one.
5. The ZONE sentence agrees with its chip on every row.
6. A post-close recompute of one live shadow day against its log: zero `diverged` rows.

**Reported, not a pass bar:** each rule's exits against the best, on design and unseen days apart.

**Decides only §3.16's display:** the expression prints both BUY and SELL across the design and unseen marks, and R2/R4 are checked at each.
