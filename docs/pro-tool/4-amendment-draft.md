# REV 6: THE PRO TOOL, one amendment (DRAFT, not yet signable)

**Written:** 2026-09-28, after the close, by the judge of the Fable / Opus debate. Before any code; UNTESTED.
**The design it registers:** `docs/pro-tool/4-final-blueprint.md` (§ numbers below point there).
**Not signable until:**
1. the Phase 2 gate table (package P2-04: every recorded day, with ZONE made event-born and VPIN's 2-close exit) exists as `docs/pro-tool/4-gate-table.md`, with its numbers produced **after** this text was hashed;
2. this file's sha256 is written into `context/research-findings.md` as §1i.

The file's modification time is the proof of order.
**What she is asked for:** one signature. No switch, no count, no knob.

---

## 1. What this changes, in plain words

**Today** the window folds you on:
- a 3-minute close past a session-high line;
- a trend vote;
- a 15-minute quiet clock;
- then a latch that keeps FOLD on the screen all day.

Validate says GO / WAIT / NO from the same line and trend. The expression reads only at 3-minute closes, against the chain's spot. **You use none of those.**

**After this amendment** there is one engine, for your marked trade, on your four reads: zone, order flow, OI and VPIN.

- **If your stop has not yet trailed past your entry:** you are out when price is *accepted* past your give-up level. That means a bucket of real business traded there, for a normal stretch of time, without coming back. A poke that comes straight back does not count.
- **Once it has trailed past your entry (a free trade), it gives you rope.** You are out on the first of:
  - price accepted past the give-up **and** the writers defending you coming off their peak (your rule: "somebody gave up, OI off from the peak");
  - that acceptance simply holding for two more buckets;
  - price accepted back through your entry. A winner never becomes a loser.
- **The screen says HOLD, PAST GIVE-UP or FOLD.** Line 2 always says, before it happens, exactly what would take you out.
- **One sound: FOLD, once.** The FOLD stays on screen until you press I'M OUT; the live read keeps printing under it.
- **The tool never tells you to bank.** It shows the wall ahead as numbers (its OI and its peak), your premium's peak and what you have given back.
- **No GO / NO before entry.** You see exactly what the screen would say if you were in: your give-up and the premium there, and the wall ahead and the premium there. Three amber reminders at most.
- **Buy or sell** is read at the level, frozen when you open the mark row. Selling at or in the money with the trend is a first-class choice. The sale is folded by the same engine: no reach, no strike stop, as you answered on 26 Sep.
- **Every price judgement** (ATM, in the money, "beyond the wall") is made against the options' own forward, never the chain's spot print.

---

## 2. What it closes

Each section below stops being in force on the first session after she signs. **Its logged rows stay its own population, never pooled with rev 6's.** No file is edited or deleted; each gets one line at its top, "closed by rev 6 (research-findings §1i) on <date>".

| signed text | sections closed | what replaces it |
|---|---|---|
| `PREREG-merged.md` rev 4 (§1e) | §1 (which strike each role reads), §2 (the line, "nearer", order flow, trend, blind rules), §3 (verdict rules 1–8 and the entry-check copy), §4 (writer rules), §5 (what is shown and may alert), §6 (parameters: SLOPE 15, which front, the ladder window, trend rows, the quiet clock, the latch), §7 (predictions and falsifier), §8 (the logs `hold_<day>`, `side_<day>`), §10–§11 (the side read, built on trend) | Blueprint §3 (the engine), §3.6 (what is shown, one sound), §3.9 (writers), §6 (faces); the logs in §5 below. §9 and §12 are history and stay as written. |
| `PREREG-rev5.md` (option B) and `PREREG-rev5-COPY-1.md` | §A (the line break, A.0 incl. the latch A.0.5 and heal A.0.6, A.2 option B), §B (the display after a FOLD), §C (PAYERS precedence: "adding beats a live fold"), §D (the window's copy, incl. COPY-1's writer sentences), §F (clause 7-B and the forward clocks), §G (what moved in rev 4) | Acceptance past G (blueprint §3.5) replaces the line and its close. The frozen FOLD with a live line under it (§3.6) replaces the latch and heal. |
| `VALIDATE-PREREG.md` rev 2 (§1g) | §1.2 (Right now), §1.3 (Room: line, noise, target), §1.4 (Paying), §1.6 (a writer), §2 (the GO/WAIT/NO word), §3 (the press and outcome rows), §4 (prediction and falsifier), §5 (parameters) | The entry face, IF YOU WERE IN (blueprint §4): no word, two printed distances, three amber clauses. **§1.1 "Your setup" stays** as the ZONE row's sentence, never a vote. |
| `EXPRESSION-PREREG.md` rev e (§1h) | §A.2 (the 3-minute cadence), §A.3 facts 1–4 (ROOM, REGIME, SPEED on the old flow rank, WALL), §A.4 R1 and R5, §A.5 (ATM only, on spot), §B (the writer's GO/WAIT/NO), §C ("fold as today"), §E (its parameters, falsifiers, logs, clocks), §F.1 (the Validate tab copy) | The expression table in blueprint §4, read at bucket closes on F\*, frozen when the mark row opens. **R2 (never sell into a squeeze) and R4 (never sell a bid straddle) stay in force.** §C's substance (no reach, no strike stop) carries into rev 6 unchanged. §A.8 hazards and §D disclosures are history. |
| `PLAN-PREREG.md` rev 3 (§1f) | §2.1 (STOP = the line, and the ₹ risk from it), §2.2 (NEXT RUNG by the plan's own wall rule), §2.3 (ROOM), §2.4 (at the rung), §2.5 (the runner's two exits), §2.6 (a writer's stop), §3, §5, §6 | STOP becomes G and line 2. NEXT RUNG becomes the wall ahead A, by the one ranking, as numbers. **§2.7's band stays** as a printed level (in NEXT FIGHT and the ZONE row), never a target or a verdict. |
| `context/research-findings.md` | §1e, §1f, §1g, §1h: each gains one line, "closed in part by §1i (rev 6); see its table". Their hashes are untouched. | **§1i:** this amendment, with its sha256 and the time she signs. |

**Not touched, and not closed by this signature:**
- **§1d, the fade gate,** with its own wall rule and reference;
- the zone machine and its 09:25 anchor;
- `data/trigger_log.jsonl`;
- the thesis table for four roles;
- "premium is never an input to the verdict";
- her 15:00 practice, which stays a display reminder and never a rule.

---

## 3. What it registers (every rule is the blueprint's text; thresholds marked (h))

1. **Units (§3.2).**
   - bucket = 3 (h) × the median 1-min volume, pooled over ≤ 5 (h) prior sessions of the **front-month** series;
   - B = today's median 1-min range; θ = 2B, w = B/2 (h);
   - F\* = the future less its 15-min (h) median basis to (K + C − P), over strikes with |Δ| > 0.3.
2. **Fights, levels, traps, G and W** as H v3 §4, §6.1 and §7.1–7.3.
   - G is seeded at the mark and re-set on her side's wins.
   - It locks once touched: it tightens, never loosens.
3. **One wall ranking (§3.4):** by current OI, near-ATM, beyond F\* by w, with a 2-close hold. W behind her, A ahead. §1d excepted.
4. **The OI event:** a drop ≥ 3 (h) σ √n from the since-reference peak on W.
   - σ = 1.4826 × the median |ΔOI| over the 15 updates before the peak, floor 1 lot.
   - Withdrawn by a rebuild above the peak, or by a new G.
5. **Acceptance:**
   - 1 (h) bucket of lots at or beyond G, over ≥ the session's median bucket duration;
   - a print w back inside restarts it, or withdraws it.
6. **The mode:** *trailed* when d·(G − E) > 0, where E is the future at her mark; else *at entry*. It is never shown as a word.
7. **FOLD:**
   - *at entry:* acceptance beyond G;
   - *trailed:* the first of (acceptance **and** a live OI event on W in the same epoch), the **held breach** (2 (h) more bucket closes and ≥ 2 (h) × the median bucket duration, with no win by her side and no print w back inside), or the **backstop** (acceptance beyond E ∓ w).
8. **The headline** HOLD · PAST GIVE-UP · FOLD, and its clause:
   - the newest of a fight's winner or a FAILED extreme (≥ w beyond, rejected ≥ w);
   - the TIRING suffix (5-bucket window, 2 in, 2 out (h));
   - words computed once per event batch.
9. **Line 2:** the out-condition, stated before it happens, in the three forms of blueprint §3.6.
10. **After FOLD:** frozen, with the live line under it, until I'M OUT or unmark. One sound per epoch; ids are kept, so a reload is silent.
11. **The four chips** ZONE · FLOW · OI · VPIN:
    - ZONE event-born;
    - FLOW event-born;
    - OI from W's events;
    - VPIN in at lead ≥ 2 of 10 buckets, out only after 2 (h) closes past zero;
    - condition-born changes need 2 (h) bucket closes.
12. **Premium at G and at A [I]:**
    - the chain's own price at K′ = K + F\* − G (or A), interpolated between the two nearest strikes;
    - a chain older than 60 (h) s reads "could not check".
13. **The wall ahead:** numbers only, in every mode (strike, points, OI, its peak and time). Never a word, a colour for side, or a sound.
14. **The entry face,** IF YOU WERE IN, with no word and no refusal. Three amber clauses: "past your give-up", "at the 22900 PE writers (n L)", "after 15:00".
15. **The expression:** BUY / SELL the other side / EITHER, by the table in blueprint §4.
    - The expiry-day BUY rule needs the wall ahead off its peak.
    - Read at bucket closes, confirmed on 2 (h), frozen when the mark row opens.
    - R2 and R4 kept.
16. **Flat:**
    - NEXT FIGHT with its two confirmations;
    - the SELLERS / BUYERS GAVE UP event, frozen and silent;
    - the re-entry read, after a FOLD, silent.
17. **Writers:** the same engine with d flipped; her short strike against F\* is always a level. **SENSEX:** its own clock; FLOW and VPIN read "could not check" with the lot count.
18. **Absence:** three sentences, never one. A missing value is never a zero. Every number is [M] or [I].

---

## 4. Predictions and falsifiers (committed now; forward rows only; counts, never rates on screen)

| read | wrong if |
|---|---|
| FOLD, at entry | trading comes back w inside G within 20 (h) min |
| FOLD, flow + OI | the same, or W rebuilt above the event's peak within 20 min |
| FOLD, held breach | back inside G by w within 20 min |
| FOLD, backstop | back inside E by w within 20 min |
| PAST GIVE-UP | it ended withdrawn (counted against those that ended in a FOLD) |
| pullback clause | G accepted within 20 min |
| tiring / failed clause | a new extreme her way by θ within 20 min |
| re-entry read | G accepted again within 20 min |
| SELLERS / BUYERS GAVE UP (flat) | price back through the level by w within 20 min |
| the expression, BUY | the premium at +20 min below the entry premium while the future moved her way by ≥ θ (the buyer paid theta on a move she caught) |
| the expression, SELL | the sold option's premium at +20 min above its entry while the future moved her way by ≥ θ |

---

## 5. The forward logs (write-once, additive, a restart continues the same rows)

**`data/fold/fold_<IDX>_<day>.jsonl`**, one row per event batch per marked trade.

- **Horizon:** every trade is logged **from its mark to 15:29, whatever she does**; rows after her exit carry `after_exit: true`. Her exits cannot censor the FOLD stamps. Scoring stops at 15:00, her practice.
- **Close-time import:** her tradebook through `/api/hold/import` replays every unmarked trade causally, as `src: "import"`, never pooled with `src: "marked"`.

```
{rev: "6", day, ts, idx, ik, expiry, trade_id, src, after_exit,
 side, role, d, strike, qty, entry_t, E, p0,
 units: {bucket, B, theta, w, med_bucket_s, pooled_sessions},
 mode, G: {px, why, set_t, locked}, W: {k, side, oi, peak, peak_t},
 A: {k, pts, oi, peak, peak_t},
 event: seed|reset|lock|refused_loosen|touch|tally|accepted|withdrawn|oi_event|oi_withdrawn|
        held|backstop|fold|past_give_up|clause|chip,
 headline, clause, line2, chips: {Z, F, O, V},
 prem: {now, peak, peak_t, at_G, at_A, chain_age_s},
 alt: {plain_accept: {t, prem}, flow_oi: {t, prem}, held: {t, prem}, backstop: {t, prem}},
 sound_id, thresholds_sha, tag: {M: [...], I: [...]}}
```

**Outcome rows** are written once, 20 minutes after each falsifiable read: `{ref_id, read, verdict: real|noise, why}`.

**Also rev "6", each its own file or its own `rev` value, never pooled with rev 2 or rev e rows:**
- `data/fold/flat_<IDX>_<day>.jsonl`: next fight, confirmations, GAVE UP events, re-entry reads;
- `data/hold/check_<day>.jsonl`: IF YOU WERE IN at each press;
- `data/hold/expr_<day>.jsonl`: the expression at each bucket close and at the mark-row freeze.

---

## 6. The kill conditions (the pass bar is stated before any rev 6 row is read)

**The clock:** 30 sessions from the first live session after she signs. Fewer than 15 cases for a clause means **inconclusive, and nothing changes** (the house rule).

1. **A FOLD on arrival is a defect, not a result.** A FOLD whose OI peak or acceptance tally began before her mark sends the face back to shadow until it is fixed. It is counted.
2. **The at-entry rule is killed** if, with ≥ 15 at-entry FOLDs, the noise verdicts outnumber the real ones. Its replacement comes back as a new registration; the candidate on file is the 2-close time floor.
3. **The trailed rule is decided by its own columns.** With ≥ 15 trailed trades that folded:
   - if one logged alternative (plain acceptance, flow + OI alone, the held breach alone) exited at a better premium than rev 6's first fire in **at least two-thirds** of them, that alternative replaces rev 6's trailed rule by a new registration she signs;
   - otherwise rev 6 stands.
4. **The face's noise budget is killed** if, on ≥ 5 sessions:
   - the headline changed more than once an hour in any trade;
   - or a FOLD sounded more than once an hour;
   - or the condition chips changed more than 6 times an hour (median over the session's trades).

   The face then returns to shadow and the replay; the engine's rows continue.
5. **The expression** is killed as a read (it stops printing, and its rows continue) if, with ≥ 15 BUY or ≥ 15 SELL reads at her mark, the §4 falsifier is met in more than half of that side's reads.
6. **Not a kill; logged for her, counts only:** each trade where she pressed I'M OUT while HOLD showed, with the premium 20 and 40 minutes later. This is the question the tool exists for: does it help her hold?

---

## 7. What she signs

> "I sign rev 6. It closes the sections in §2 as they stand, their rows stay their own, and it registers §3–§6. §1d, the zone, its 09:25 anchor and trigger_log are untouched."

Signed: ____________ · time (IST, by the clock): ____________ · sha256 of this file: ____________

---

## 8. The gate table

Kept in `docs/pro-tool/4-gate-table.md`, written by P2-04 after this file is hashed, so this file never changes after its hash. If a gate fails, this draft is not presented; a revised draft gets a new hash.
