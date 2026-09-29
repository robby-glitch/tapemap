# Fable's critique of the Opus blueprint

**Written:** 2026-09-28, after the close. Read-only: `1-opus-blueprint.md`, its replay (`scratchpad/pro1/reader_pro.py`, the `VH_*` runs = PRO-1), the chain and book on disk, `panel.js`, `fit.js`. Nothing edited, started or posted.
**Chair:** the same one. I read it as the trader who would sit in front of it on Wednesday.

## 0. Verdict in four lines

1. Its **spine is right**: two questions, not one. "Is the trade wrong" (a stop) and "is the trade done" (a read). That is how a desk thinks, and it is cleaner than my single held-breach rule.
2. Its **BANK ZONE is broken as coded and dangerous as designed**: it fires on evidence gathered before price reached the wall, it fires on walls that have already broken, and it never looks at the wall's own OI. On her put it tolled at +28% into a floor whose writers were leaving. For a trader whose stated problem is holding, that is the wrong sound.
3. Its **winner mode has no floor but her entry**, and it pairs that with an OI test it admits cannot see a slow bleed. A +100% trade can go to scratch and the screen will say PAST GIVE-UP the whole way.
4. Its **loser mode has no whipsaw guard**: at the open the volume clock runs in 70-second buckets, so a poke is "accepted" and OUT sounds on it (25 Sep call, −10%, noise by its own test).

## 1. Claims checked against data and code

| claim | check | result |
|---|---|---|
| BANK ZONE "+90% at 14:38:42, five seconds before the day's best" (§0.4) | `VH_H2_0928_PE.txt`: `14:38:42 REACHED … 14:38:42 BANK ZONE … holding (tiring)` | **Same second as REACHED.** The "holding" evidence is the TIRING state carried from 14:36, before price got there. Same on 09:45:10 and on 24 Sep 12:32:40. Code: `hold = s.tiring or (FAILED and s.failed) or (fight after reached)` (`reader_pro.py:476`): only the fight branch is time-gated. |
| BANK ZONE 09:45 on her put: "the wall shows it is holding" | `chain_NIFTY_2026-09-28.jsonl`, 22900 PE OI: 131.96L 09:34 → 114.57L 09:39 → 119.4L 09:45 | **The wall was covering**, 12.5L (−9.5%) off its peak at the moment the tone said "holding". It broke by θ at 10:41 (`WALL BROKE`) and the put went to +97%. |
| BANK ZONE "once per wall" on 22 Sep at 11:20 (+82%) | `VH_A1`: `10:42:31 WALL BROKE: 23400 PE` … `11:20:16 BANK ZONE: at the 23400 PE wall and it is holding` | **Banked a wall that broke 38 minutes earlier**, while price retraced to it from +112%. `s.banked` never checks `s.broke`. Same on 25 Sep call (broke 14:05:37, banked 14:11:33). |
| "Cuts losers at the level … no worse than v3" (§2.5) | `VH_A5_0925_CE`: `09:47:03 HYBRID OUT (loser) … SOUND #1`, verdict NOISE (back through in 49 s); best after +53% | True on the four listed, but the OUT it counts as −10 is a stop run. v3 withdrew that same acceptance in 49 s and never sounded. |
| `panel.js:515` innerHTML rebuild | `$('face').innerHTML = hdr + …` at ~513 | Confirmed. |
| `fit.js:194–203` "no date tick → every day is a candidate" | `src/engine/fit.js:198–203` and the comment above it | Confirmed, and the comment already names the 09-16 session jump. |
| "chain older than 60 s → could not check" | chain rows every ~10 s (`09:17:29, :39, :50`) | Fine; no boundary flicker. |

## 2. Where it would cost her money

### 2.1 BANK ZONE, the flagship, is the worst rule in the document

Her brief, in her words: "i have problem holding trades for longer". Now count the tones PRO-1 would have played her across the replay:

| trade | bank tone at | the wall then | trade went on to |
|---|---|---|---|
| her put, 28 Sep | **09:45 +28%** | covering; broke 10:41 | +97% |
| her put | 11:57 +48% | broke 14:18 | +97% |
| 24 Sep put | 12:32 +37% | broke 13:26 | +154% |
| 25 Sep put | 09:47 +26% | 30 min later +4% | (folded +7) |
| 22 Sep put | 11:20 +82% | already broken 10:42 | +264% |
| 22 Sep put | 12:01 +132% | broke 13:01 | +264% |
| 25 Sep call | 14:11 +31% | already broken 14:05 | +53% |

Seven tones. Five were on walls that broke, two on walls that had already broken. Only 22 Sep 13:54 (+221%) and 28 Sep 14:38 (+90%) were tops, and both fired on stale TIRING in the same second as REACHED. A soft tone that says "pros bank here" at +28% fifteen minutes into a trend day is a nudge to do exactly the thing she built the tool to stop doing. The §9 falsifier ("wall broken by θ within 20 min") is tuned not to catch this: every break above came 54–140 minutes later.

The design cause is deeper than the two code bugs. §0.3 says "OI tells me who is defending". BANK ZONE never reads the ahead wall's OI at all; "holding" means price paused. A wall is holding when its writers stay; it is giving when they cover, and that is a fact the chain prints every minute. My AT THE WALL · holding / giving reads it, with no sound. Keep the tone off until the wall's OI is in the sentence.

### 2.2 Winner mode: the only hard floor is her entry

In winner mode OUT needs acceptance beyond G **and** a live OI event on W. The blueprint's own §2.5 and H §12 say the √n OI test "cannot see a slow bleed" (the 28 Sep call: 147.8L → 113.8L, −23%, never fired). Put the two together: a winner whose defending wall bleeds instead of breaking gets PAST GIVE-UP, amber, no sound, until acceptance back through E ∓ w. On the 22 Sep put that backstop was 23459 against a give-up at 23385: from +264% to roughly 0% with the screen never saying OUT. The sample has no such case; the logic guarantees one eventually.

24 Sep shows the cost even when OI does fire: accepted through G at 14:37 at +105%, held 18 minutes for the writers, OUT at +81%. My held breach leaves at 14:39, +98%. Their §2.1 opens with "price accepted beyond the level is a stop, not negotiable, it does not wait for OI" — then winner mode waits for OI. The two halves of the document disagree, and the second half is the one that runs.

### 2.3 Loser mode: acceptance at the open is a poke

Bucket = 3 × pooled median 1-min volume. From 09:15 to ~10:00 volume runs several times median, so a bucket closes in 60–80 s and "median bucket duration so far" is small once five exist. Acceptance = one bucket beyond G over ≥ that time. On 25 Sep call that was 80 s (09:47:03), withdrawn 49 s later by v3; PRO-1's loser mode makes it OUT with two low tones. Their §2.1 step 2 ("stop runs poke; real moves accept") is the right question; the clock is wrong for it. My rule (two more closes and ≥ 2 × median time) exists for this minute of the day.

### 2.4 The mode boundary is her fill, which the market does not know

Mode flips when G trails past E. Two trades at the same level, one filled 3 points earlier, get different exit laws: one is stopped by price, the other needs price and OI. Location decides whether a level failed, not where she was filled. PRO-1 is the disposition effect written into the engine — held winners longer, cut losers faster — and the only defence offered is that it matches her sentence. Her sentence was about what "gave up" means, not about her entry price.

## 3. Where it is unclear at a glance

- **Line 4 doubles as BANK ZONE.** "ahead 22850 PE floor · 29 pts · ≈ 200" becomes "BANK ZONE · 22800 PE floor holding" on the same line as the word row also changes. Two places change for one event; she reads the wrong one first.
- **"the give-up for the rest stays 22831."** "The rest" presumes she took some off. That is a size by implication; the constraint forbids it. Say "if you stay, the give-up is 22831".
- **WALL BROKE re-labels the give-up in one step**: "22850 PE floor broke 14:18: now your roof" and G tightens to A ∓ θ. A floor turning into a roof mid-sentence, on a line that also shows the frozen G, will read as the give-up moving. It changed no exit in 8 trades; it costs one number and one rename per break. Cut it.

## 4. What flickers

Their own budget: words ≤ 4/h, chips ≤ 6/h, "an acceptance gate". PRO-1 on 24 Sep: 44 words (8.0/h), 9 lasting a minute or less, 67 chip changes (12.2/h), worse than v3's 64. The gate is stated and then not applied to the one trend day in the set. Adding REACHED/BANK/BROKE lines on top of PULLBACK/BEHIND/TIRING alternation makes the trend day louder, not quieter. I do not fix 24 Sep either; I say so. They say they will gate on it and ship it failing.

## 5. Unbuildable, or against a fixed constraint

- **Phase 0(d), yesterday-close OI baseline "before Wednesday's roll":** Tuesday 29th is expiry. Tuesday's last chain snapshot is of the expiring weekly; Wednesday trades the 6 Oct weekly, which the recorder never saw (the next-weekly chain is their Phase 5 item 4). By their own "same expiry only" rule the baseline is null on the day they justify shipping it. It helps Thursday; say so, and do not spend Tuesday night on it.
- **Six tabs are still six.** Trade stays "kept by her order" (correct), War stays, Board stays as a 14-row strip. The brief was one screen for the day; §1 gives her Board for flat, Validate for in-trade, and the panel for both, so the in-trade word lives in two tabs and the flat word in a third.
- **`FOLD_NEEDS` dropped.** That is the one switch H registered for her to flip. PRO-1 removes her hand from it and replaces it with a mode she cannot see change except by reading line 2.

## 6. Data defects it ignores

- **The open's volume clock** (§2.3): every threshold is "scale-free" in volume, but the session's clock runs 5× faster for the first 45 minutes, and the doc never states what a bucket's duration is at 09:47.
- **BANK ZONE reads no OI** (§2.1), the one input that distinguishes a wall holding from a pause.
- **The 09:15–09:16 in-memory backfill** (audit §6) is not in the table; a restart at 09:20 loses it.

## 7. Where theirs is better, and what I take

1. **Two questions, named.** "The trade is wrong" versus "the trade is done" is the professional's grammar and it is missing from my blueprint, where AT THE WALL and GAVE UP sit in one precedence list. I take the frame and the loser-side rule: **while the give-up is still on the losing side of the fill, price acceptance alone is OUT** — kept under my time floor (two more closes, ≥ 2 × median bucket time) so the open cannot poke her out. On the four losers that is −17 / −12 / −10 / −42 against my −25 / −14 / −21 / −45; on the whipsaw it is v3's silence instead of a tone.
2. **The RE-ENTRY READ.** "Stop run failed at 22925: sellers won again 12:35" on the flat screen after an OUT. With free execution, the answer to a whipsaw is not a slower exit but a named re-entry. I had nothing after OUT except "who is trapped now". I take it whole, sound-free.
3. **Line 2's mode sentence and the entry refusal "you would be entering at the wall ahead: where pros bank, not enter".** Telling her *before* it happens what would fold her ("needs flow + OI") is better than my precedence table, and the wall-ahead refusal is one my single NO does not cover. I take both, without the mode, as "out on: price accepted past 22925" / "out on: that, and 22900 CE writers leaving".
4. **Phase 0 ordering.** fit.js single-day candidates, contract match, contract stamps: before Wednesday, before anything about the method. Mine put data truth "next week". Theirs is the right Tuesday night, minus item (d).

What I keep of mine against theirs: the held-breach exit for winners too (location decides, not the fill); AT THE WALL reading the ahead wall's OI, silent; three screens.

**n = 8 describes.** Everything above about outcomes is a description of how each rule fails; the forward log ranks.
