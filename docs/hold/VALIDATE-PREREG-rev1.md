# PRE-REGISTERED — THE VALIDATE WORD: GO · WAIT · NO (rev 1, written 2026-09-25 12:15 IST, before any code, SIGNED 2026-09-25 13:20, UNTESTED)

**Her words, 2026-09-25 ~12:10:**
- "i want the validate button there when i choose the strike ce or pe and weather i long or short it";
- "and than it should tell weather the app the thinks i should take it or not or confidence score
  maybe".

This registers a pre-trade WORD. It **changes no rule** of the hold window (`PREREG-merged.md` rev 4)
or of THE PLAN (`PLAN-PREREG.md` rev 2a). It reads only their registered objects, at the latest
finished minute. Until §4 is judged, the word carries DRAFT.

**Why a count and not a percentage.** A percentage would be a number with no forward record behind
it: the "confidence score" CLAUDE.md rule 4 forbids. The count of registered facts lining up is the
honest score, and it is shown big. Every press is logged (§3), so the word earns its trust, or loses
it, on her own forward rows.

## 1. The five facts: each WITH you / AGAINST / NEITHER

| # | fact | WITH you | AGAINST | NEITHER |
|---|---|---|---|---|
| 1 | **Your setup** (the zone machine's latest trigger on the index today, its bar closed) | same direction as the trade AND its §1d gate legal | opposite direction | none today, gate illegal, or not read |
| 2 | **Right now** (the window's entry check, read now) | HOLD | FOLD (a broken setup) | WATCH or PATA NAHI |
| 3 | **Market side** (§10.4) | agrees | against | no side, or could not check |
| 4 | **Room to run** (PLAN §2.3) | a rung exists and its room ≥ the stop's room | rung room < stop room | no rung, or either distance unreadable |
| 5 | **The next wall** (PLAN §2.2 word) | GIVING WAY | DEFENDED | STALLED, a session extreme, or none |

## 2. The word

- **NO:** fact 2 is AGAINST (you would enter a broken setup), or 3 or more facts are AGAINST.
- **GO:** no fact is AGAINST and 4 or more are WITH you.
- **WAIT:** everything else. It names each AGAINST fact as "what would have to change".

Shown with it:
- "n of 5 line up";
- one plain sentence, built from the facts;
- the stop and the next wall.

It is never a size, never an order, and never a percentage. **It never gates anything**, and she
decides.

## 3. The log

Every press of VALIDATE writes one row to `data/hold/check_<day>.jsonl`, write-once and keyed
(index, read minute, strike, side, role):

`{day, at, t, idx, k, side, role, p0, word, n_for, n_against, facts: [[name, state, text]...], entry_verdict, zone_t, stop, rung, tag: "I"}`

A check marks no trade; "I'm in" is the separate door.

## 4. Prediction and falsifier (forward rows only)

**The measure (the same unit as rev 4 §7).** For each logged check, the checked option's maximum
favourable excursion over the next 30 finished minutes (to 15:29, flagged short), as a % of the
premium at the check [M, from the chain record]. For a writer, "favourable" is the premium falling.

**P.** GO checks are followed by larger excursions than NO checks: two distributions, medians and
full rows, split by index, never a rate.

**The falsifier.**
- It is judged at ≥ 15 GO and ≥ 15 NO checks and ≥ 10 sessions, and in any case at 30 sessions.
- If P does not hold, or it reverses once the best day is removed, the WORD is deleted. The five
  facts stay as a checklist.
- If there are fewer than 15 of either word at 30 sessions, the result is inconclusive and the word
  stays DRAFT.

## 5. Disclosed

**One live moment was seen** before this was written: her 2026-09-25 09:36 NIFTY 23200 PE.
- The facts there read: setup WITH, right now NEITHER (WATCH), side NEITHER, room AGAINST (4 vs 18
  pts), next wall AGAINST (PE 23,100 DEFENDED).
- By §2 that is **WAIT**, and the trade then ran from 150 to 181.
- Nothing above was changed to make that moment read differently.
