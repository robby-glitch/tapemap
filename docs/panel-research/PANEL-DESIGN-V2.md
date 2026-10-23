# Right panel v3: design v2 (20 Oct 2026). Merges CRITIQUE-SONNET.md and TRADER-NOTES-OPUS.md. Not yet approved by Mary.

This file supersedes `PANEL-DESIGN-DRAFT.md`.
- **Measures:** taken from Sonnet's §3. They are measured, and they beat mine.
- **Face:** taken from the v2.3 lesson. Mary rejected a design that read as code, so **the measures are rendered as
  pictures, never as number pairs.**

## A. Measures (Sonnet §3, adopted as written unless stated)
1. **Normal = slot reference × today's tempo** (Sonnet #1). This is one rule for flow and OI, and it deletes the
   day-kind split.
   - The tempo shows once, uncoloured: `aaj 0.8×` (flow) / `aaj 2.9×` (OI).
   - `EXP` is a header chip.
2. **LEG + rasad replaces TREND** (Sonnet #2).
   - The leg is the READ's since-time while the READ is fresh. When the READ is older than 5 min, the zigzag leg takes
     over.
   - Rows:
     - where the leg's points came from;
     - the burst that fed it;
     - since then;
     - `rasad`, the last-fed time per feeder (flow · OI · fut OI · BANKNIFTY).
   - This is how "is the trend still being fed" is answered.
3. **KAUN DABA RAHA = PACE ladder + TILT ladder** (5m · 15m · pichle 45m) plus a burst line (Sonnet #3, #4).
   - Speed = the shape of the ladder.
   - The row-end word is `tez ho raha` or `thak raha`. It appears only when the ladder is monotonic and has held for 3
     evaluations (Sonnet #9). Otherwise there is no word.
4. **KAUN LIKH RAHA:**
   - **Gross quarters on fixed strikes** (Sonnet #5): four 15-min builds, a bounded share, and `churn` checked first.
     Words: `badh raha` / `dheema` / `nikal rahe` / `churn`.
   - **Deewar tokens** (Sonnet #6): merged adjacent strikes, concentration plus a tempo-free rank, at most 3 rows,
     each with its distance from spot in points.
   - **fut OI** with a dead-band.
5. **DOOSRE INDEX** = `din %` plus the spread to NIFTY, ranked (Sonnet #7).
   - SENSEX collapses to `= NIFTY` when its spread is inside noise.
   - A confirm word (✓ / ✗) appears only after a test, i.e. NIFTY made a new extreme in the last 15 min (mine).
   - σ is cut, and SENSEX pace is cut.
6. **Thresholds tighten with N** (Sonnet #8). One `ref 11d` chip sits in the header. No `kam data` or `N` anywhere
   else.
7. **Three honest states** (Sonnet #10): `shaant ✓` = checked and quiet · `—` = this feeder never fed · `?` = could not
   check. They must never share a glyph.
8. **PLAN prints spot and fut.**
9. **SIRF BADE** is ≤ 2–3 rows: KHEL-relevant first, then newest; never two rows of one event. The P/R/T/Z/B legend
   moves to its title.
10. **Data hygiene:**
    - leave out the first Upstox minute after a recorder hole;
    - a stale READ shows as `READ hh:mm ka`;
    - backfilled rows that would not have existed live at T get a grey `bad mein aaya` tag in the mockup.

## B. The face (binding)
Every rule here exists because v2.3 failed by reading like code.
1. **No number pairs on the face.** The draft's `tilt GC|UX −5|−3` is banned. TILT renders as **one bar per window**:
   - green bar = buyers, red bar = sellers, length = the winner's share;
   - **hatched grey** when GC and UX disagree in sign;
   - a small `GC` or `UX` when only one source exists.
   Exact numbers go on hover.
2. **PACE cells are `1.2×` with a tint.** The tint deepens with rank against the N-based threshold. Below the
   threshold the cell is a quiet grey.
3. **No p-numbers and no N on the face.** The only exceptions are the header's `ref 11d` and `aaj 0.8×`.
4. **Arrows mean price direction only.** Speed words are bold ink, never coloured by side.
5. **Colours:** one meaning each. Green = buyers / up, red = sellers / down, grey = quiet. Amber only for "could not
   check".
6. **Rasad is four small chips with times.** A chip is solid ink if that feeder fed within 15 min, grey if stale, and
   `—` if it never fed.
7. **OI quarters are four small up/down blocks** per side, oldest → newest, sized by lakh. This is a read of OI, not a
   price chart.
8. **Size:** ≤ 6 words per cell, 360 px wide, fits 820 px tall, 12 px type minimum.
9. **The face is judged as a picture at 360 px.** If a trader can't tell who is pressing and whether the leg is fed
   within 2 seconds, the panel fails, whatever the text says.

## D. Round-3 decisions (20 Oct, after looking at shots-v2 as a trader)
**What I saw:** 19 Oct 14:30 tells its story. 16 Oct 11:05 is a wall of grey slivers: the sellers' takeover at the 10:36
high of a 230-pt rally is invisible, missed by 0.004 on a knife-edge threshold. The flow speed words fired 0 of 15 times,
so the "speed" Mary asked for is not on the screen. **The cause is the rendering and binary gating, not the measures.**

1. **Continuous intensity replaces lit / quiet.**
   - Every PACE and TILT cell is drawn at a strength that grows smoothly with its rank: faint below p70, darkening
     through p90, full at p97+.
   - No knife edges, so a miss by 0.004 looks like its neighbour.
   - Words (`tez ho raha`, `churn` …) still need the rule's gate. Bars don't.
2. **TILT is a diverging bar from a centre line.**
   - Sellers extend left in red, buyers right in green, length = (share − 50%).
   - 51% is a stub; 64% is clearly long.
   - Hatched when the sources disagree, with the house two-source rule: one source beyond is tinted and capped below
     full.
3. **PACE is a bar too.** Length = × normal (capped at 3×), so the 5m / 15m / 45m ladder reads as a shape: growing
   left-to-right means slowing, shrinking means speeding up. Keep the `1.2×` text beside it.
4. **OI quarters are 4 columns,** each at least 14 px tall and 8 px wide.
   - Up = adding, down = cutting. Height = lakh, on a shared scale per side.
   - The intensity tint is driven by rank.
   - Each column's lakh value appears on hover.
5. **LEG = main leg + current pullback,** the way a trader says it.
   - The main leg runs from the session extreme or READ anchor to the leg extreme, e.g. `▲ 09:35–10:36 +230`.
   - Then the pullback since, e.g. `abhi −45 (20% wapas) 10:40 se`.
   - The zigzag threshold moves from 25 pts to 0.5 × today's IV-priced 30-min σ, or 50 pts if larger, on 5-min
     closes.
   - Rasad times are measured on the main leg; the pullback row shows who is pressing it.
6. **A dead feed shows its last known value with the time,** e.g. `fut OI −0.4L · 09:48 tak`, in amber italics, never
   as live. This keeps the 16 Oct covering visible as it was known.
7. **The BNF chip has one meaning:** confirms (✓, ink) or refuses (✗, red outline). There is no "fed" state for a peer.
8. **SIRF BADE `×N` merges only same-price marks.** Different levels keep their own rows, still capped at 3.

## C. Pass bar for the mockup (written before re-running)
A trader looks at the pictures, never at the text alone. The panel must make each of these visible:
- **19 Oct 14:30:** the leg was fed only 13:15–13:30; nothing has fed it since; BANKNIFTY refuses. This must be visible
  in under 2 s.
- **16 Oct 11:05:** the buyer-to-seller handover at about 10:40; the PUT wave fading; call churn.
- **16 Oct 10:00:** what has happened since the low (thin lift, shorts covering) to the extent the data existed at T.
  Where the data died, it shows `?` with the reason.
- **Expiry and normal days light up at similar rates.** No block is blind on 19 Oct.
