# ADDENDUM to THE PLAN — rev 3a draft: THE BAND RUNG (written 2026-09-25 10:15 IST, revised after review, before any code, SIGNED 2026-09-25 13:20 — merged into PLAN-PREREG.md rev 3, which is now the registered text; this file is its history)

This proposes rev 3 of `PLAN-PREREG.md`. **Rev 2a stays the signed text** (§1f, sha256
`a0295c20…158b`) until she signs this. If she does, it is merged in as §2.7, with a change-log
entry and a new hash in §1f.

**Her words, 2026-09-25 ~10:10:**
- "nifty tapped +2.4 vwap band and there was exhaustion i should have entred there but i didnt i
  was afraid";
- "didnt hold when the oder flow was also showing the sellers getting aggresive";
- "we should have traded till nifty reaches the lower band because … there is a bounce from there".
- "i m relying you to make the best descision".

**Seen before writing this: one session, one index, zero evidential weight, described.**
NIFTY on 2026-09-25, from the tool's own records (trigger_log and `/api/data` at 3 min):

| time | event | read |
|---|---|---|
| 09:27–09:30 | SELL u2 armed; highs 23,160–23,165 ≈ +2.4σ | |
| 09:33 | **SELL u2 triggered** at 23,141 | gate LEGAL (CE 23,200 building) |
| 09:39, 09:42 | the futures close at z −2.1 (d2) | the BUY-d2 gate ILLEGAL: PE 23,000 stopped, then gave up its build |
| 09:51 | BUY d2 armed | gate LEGAL again (PE 23,000 building) |
| 09:54 | **BUY d2 triggered** at 23,110 | |

Her 23200 PE, from the chain record [I]:
- 137 at the 09:33 trigger;
- 150 at her entry, ~09:36;
- 161 at her exit, 09:39;
- 181.5 at 09:43;
- 171–181 across 09:51–09:54;
- 142.75 at 10:09.

**Nothing new is introduced.**
- The bands, the zone machine (u2→u3 SELL, d2→d3 BUY, 3-minute) and the §1d fade gate already
  exist, are pre-registered and are logged forward.
- This only prints them as the rung she already trades to.

## §2.7 THE BAND RUNG (proposed)

**Buyers only; a writer's plan stays the stop alone.**

**The rung.** For a long PE the band rung is **d2** on the zone machine's own session-VWAP bands of
the near future (3-minute). For a long CE it is **u2**. It is shown beside the wall rung of §2.2,
never merged with it:
- `BAND d2 · now z −1.2 · target z −2`;
- the distance is in σ, because the bands are on the future and the line is on the index. No
  points are converted between the two.
- **The BAND line carries its own units clause (S3):** "σ on the future — not points, never
  comparable with the stop's index points".

**Its word** comes from the zone machine's own §1d gate on the **opposite fade** at that band (M1).
- **The exact lookup:** the `gate` on the `data/trigger_log.jsonl` row with `rule: "zone"`,
  `kind: "arm"`, `index` = hers, `side` = the band's own native fade (BUY at d2, SELL at u2), and
  `t` = the touch bar. `DEFENDER` makes "BUY legal at d2" mean the put writers at the band are
  building.
- It is read at the band only, meaning the 3-min bars that the zone machine itself arms at ±2σ.

Four outcomes, **each its own sentence, never merged**:
- **GIVING WAY:** `gate.legal` is false. "The floor/ceiling at the band is giving way — in your
  favour; the move may run past the band".
- **DEFENDED:** `gate.legal` is true. "The floor/ceiling at the band is defended — against your
  move".
- **could not check:** `gate.legal` is null (PATA NAHI), printed with `gate.why`.
- **checked, none:** there is no zone arm row for this bar at all. The machine did not arm there,
  either because the bar set no fresh extreme or because an earlier same-band trigger's re-fire
  lock is still open. It prints "the zone machine did not arm at this bar — no band word; the
  last word stands (HH:MM)", or "no band word yet" if there was none.

**The opposite trigger** (BUY d2 for a put, SELL u2 for a call) is printed as an event with its
time and legality, e.g. "BUY d2 triggered 09:54 (legal) — the other side has taken over".
- It is a fact, not an instruction.
- As in rev 2a, the plan never says "exit" or "book", and never sizes. Which one governs is hers.

**The entry line** gains one fact when a same-side zone trigger preceded her entry that session:
"entered N min after the SELL u2 trigger at HH:MM [M, trigger_log's clock]; the premium had moved
±P since [I, the chain record's last trade]". Each number carries its own tag (S2). It is a
description of timing, never a gate.

## §5 / §6 additions (proposed)

**The log.**
- Each band touch (the first 3-min bar at ±2σ after her entry) gets its own write-once
  `band_touch` row: `{trade_id, t, band, word, gate_why, opposite_trigger_t|null, next15}`, with
  `next15` exactly as §5 (M1) defines it.
- One per (trade, band).

**P2.** After a GIVING WAY band touch, the index goes further in her direction over the next 15
finished minutes than after a DEFENDED band touch.
- The unit is rev 2a §6's: two distributions, medians and full rows, split by index, never a rate.
- It is judged at at least 15 of each and at least 10 sessions, and by 30 sessions at the latest.
- It must survive removing the best day.
- If it fails, the band words are deleted, and the band stays as a level.

**Disclosed (S1).** One sharp move can touch her wall rung and the band in the same 3-min bar.
That hands P1 and P2 a sample from the same cause, in overlapping windows.
- The two stay separate populations (different row kinds, never pooled).
- A band touch in the same bar as a wall touch carries `also_wall_touch: true`, so the overlap can
  be counted, and each falsifier can be read with those rows removed.

## What stays unsolved

- **The bands are on the future, the line and the walls on the index.** The two are shown side by
  side, never converted.
- **Early in the session the bands are narrow.** Today u2 → d2 took 6–9 minutes, so the band is
  reached fast and the word carries the plan.
- **She named "the sellers getting aggressive" as a hold reason.** The window's ORDER FLOW row
  already reads it (strict: CVD strong AND prints dominant). Today it read FLAT at 09:39 (CVD −7,
  3 sell / 5 buy prints) and WITH her from 09:52. No change is proposed to that row.

## Change log

- **rev 3a:** the fixes from `docs/hold/PLAN-ADDENDUM-REVIEW.md` (Sonnet, the independent reviewer;
  NOT YET on rev 3):
  - **M1:** the band word's exact lookup (the zone arm row's `gate` at the touch bar, native side),
    and the fourth outcome, "checked, none — the zone machine did not arm at this bar", distinct
    from PATA NAHI.
  - **S1:** the same-bar wall and band touch disclosed, and flagged `also_wall_touch`.
  - **S2:** the entry-timing fact split into [M] and [I].
  - **S3:** a units clause on the BAND line.
  - No new number.
