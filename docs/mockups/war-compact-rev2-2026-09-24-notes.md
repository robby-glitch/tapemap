# WAR, compact rev 2: design notes (2026-09-24)

Mockup: `war-compact-rev2-2026-09-24.html` (self-contained, 658 KB, light only). Generator:
`gen_war_compact_rev2.py`, which reuses rev 1's data pass (`gen_war_compact.build`). The rev 1 files
are untouched. Inputs are the same, all read-only: the `/api/oihist` and `/api/warmap` payloads saved
at 00:47 IST, `data/chain/chain_<IDX>_2026-09-23.jsonl`, and now also
`data/warmap/warmap_2026-09-23.jsonl` (the war map's forward log). No code, data or extension edits;
no restart; no commits.

It was checked in Chrome at 1:1 inside a dashed 1600×690 frame (the app's tab area), with the mockup
controls outside the frame. I looked at NIFTY 13:36, NIFTY after close and BANKNIFTY 13:36, and
measured all six index/view pairs.

| View | WAR height | Rows × lane | Truncated lines | Past the frame |
|---|---|---|---|---|
| NIFTY 13:36 / close | 667 / 657 px | 15 × 12 px | 0 | 0 |
| BANKNIFTY 13:36 / close | 651 / 651 px | 16 × 11 px | 0 | 0 |
| SENSEX 13:36 / close | 645 / 645 px | 17 × 10 px | 0 | 0 |

## What changed from rev 1, and why

1. **Light only.** The dark tokens and the toggle are gone; there is nothing to persist. (Her call.)
2. **The tab-area frame is 1600×690 at 1:1, with no scaling.** Rev 1 designed a 900 px stage and
   scaled it. WarTab's padding becomes 12 px top and bottom, 24 px at the sides.
3. **Rank is weight on the map, the same way the ladder shades it.** The four server fronts draw at
   full ink, the rest of §1d's nine at half, and rows outside the nine at 0.2. That covers cells,
   hatches, rings and amber alike. The nine are shaded in the map's gutter as on the ladder, and
   front rows keep their side tab and bold label.
   - The nine are §1d's nine **now**, applied to the whole day's history, just as the ladder applies
     them to the book now.
   - At NIFTY 13:36, 23,650/23,700 CE are faint. CE 23,500, CE/PE 23,400 and PE 23,300 own the map.
4. **12 px lanes when there are 15 rows or fewer.** A strike is then 30 px (12 CE + 1 + 12 PE + 5 gap),
   so the plot is 450 px.
   - With more rows, lanes thin to fit 450 px (BANKNIFTY 11 px, SENSEX 10 px).
   - The height channel (share of its own high still held) now has 12 levels on NIFTY instead of 8.
5. **Event labels stack.** Each label goes in the first free row at its own x, with a leader line when
   it is not in row one; stop labels are bold and unwind labels plain. NIFTY 13:28 / 13:31 / 13:32 /
   13:34 take four rows and never overlap.
   - Every stacked row past four is taken out of the plot budget, so a crowded minute can never push
     the tab past 690.
6. **Dwell boxes on the spot line.** They come from the war map's own forward log (`dwell.py` +
   `sequence.py`, APPROACH→DWELL→BREAK/REJECT, observed rows only), not re-derived.
   - Box geometry: brass, the level ±`band` from the log. It opens 5 min before the DWELL stamp
     (`dwell.DWELL_MIN_S`, since the log has no hold start) and closes at the exit. It is dashed while
     still holding. The minutes are printed on top of the box.
   - "Loaded during it" is the largest OI change among the legs within `dwell.NEAR_STEPS` (2) strikes
     of the level, over the box window, from the minute grid [M]. The "retail loading" reading stays
     [I], as `dwell.py` says.
   - The rail's PARKED block lists the two latest dwells; hovering a box puts the full line in the
     readout.
   - NIFTY 09-23 **[M]**:
     - 23,400 10:27–10:37 (11 min, then break): PE 23,400 +7.4L
     - 23,450 13:12–13:30 (19 min, then reject): PE 23,450 +1.2L
     - 23,450 14:10–14:29 (20 min, then break): CE 23,400 −7.1L
7. **"First" is stamped once.** It is the first minute the server's `fronts.broke()` named an UNWINDING
   front, rolled forward with peak OI as the poller held it at each minute. It is never re-decided.
   - Why it matters: `broke()` changes its answer through the day, 8 times on NIFTY, 50 on BANKNIFTY
     and 32 on SENSEX on 09-23.
   - Stamps [M]: NIFTY CE 23,400 (stopped 10:15 @ 23,375, named 10:20); BANKNIFTY PE 56,500 (09:25,
     a +0.6L build, named 09:40); SENSEX PE 74,700 (09:24, named 09:36).
   - The answer strip's first line is this stamp. The second line is the latest stop and a count of
     the four fronts' current states.
   - The "1ST" chip marks a rail card only when the card describes **the same stop** (same `peak_at`).
     A front that re-built past its first stop is describing a later stop; BANKNIFTY PE 56,500 at
     13:36 is one, so it gets no chip and the answer line says "re-built to +3.2L (12:43)".
8. **§1d is untouched and not smoothed.** Every state word is the rule's own read, and "→ §1d:
   unwinding HH:MM" is its first unwinding read after the high.
   - One wording change, from §1d's own text and `fade_gate`: a BUILDING front at least
     `fronts.UNWIND_FRAC` under its own high shows **ADDING AGAIN** and names the distance.
     BANKNIFTY CE 56,500 at 13:36 reads "adding again now · 91.0K under its +1.1L high". The rule's
     state is still in the tooltip.
   - The flag `under` is computed with the server's constant in Python, never in the page.
9. **Forced / released** is a labelled empty slot on each card: "forced / released: pending §1d
   addendum". Nothing is computed and 09-23 was not looked at through it.
10. **Rail rank reads "#1 peak OI 136.9L".** That is session-peak absolute OI, the server's rank
    basis, and the tooltip says so. It cannot be read against the board's OI at the minute. The
    ladder footer says "box = top two by peak OI".
11. **The ladder is self-contained for reuse on the BOARD.** It has its own defs, its own footer key
    (CE · OI now · PE, full bar, │ = session high, box, shade, dashed = cursor) and a dashed spot line
    across the book, so each bar's side of spot, and so ITM/OTM, is visible without a word.
    - Weight tiers match the map. The input is `rows`, `yP`, `oi` now and at the cursor, `peak_abs`,
      `fronts` and `near`, and nothing else.
12. **Smaller fixes.**
    - Amber "could not check" is quieter (thinner dashes, dimmed outside the nine) but still drawn.
    - The answer strip never prints "1.2L off" for a STALLED front; it says "stalled".
    - Provenance is one line; the legend is one line.

## Where I disagreed with Fable 5.1, and why

- **"NIFTY's 15 rows fit at 12px inside the 340 cap."** The arithmetic does not hold: 15 × (12 + 1 +
  12 + 5) = 450 px. It fits because the 690 px frame has room for a 450 px plot, not because of 340.
  Rev 1's cap is replaced by 450, derived from the frame.
- **The first stop is the rule's own read, even when it is small.** On BANKNIFTY the stamp lands on a
  +0.6L PE 56,500 build at 09:25, which a trader would not call "the" first stop. I kept it and
  printed its size rather than invent a minimum-build floor, since she said §1d stays as it is. If she
  wants a floor, it is a §1d parameter (method), not a face change. Question for her below.
- **Legs, not minutes (Fable fix 4)** is right for the BOARD's ribbons. WAR never drew per-minute
  state, and with her "no smoothing" call it keeps the rule's reads as two stamps per front. No
  change was needed.
- **ITM/OTM "as the loudest attribute"** is Fable's main-page advice. On WAR it would be a word on
  every card; I used the ladder's spot line instead (geometry, no new word). The BOARD can promote it.
- **Fable's example dwell ("PE 23400 +22L during it")** is illustrative. 09-23's real loads during
  NIFTY dwells were 7.4L at most. The box prints what the grid measured.

## Wiring added since rev 1 (smallest first; rev 1's list still stands)

1. `under` on each `/api/oihist` front: one expression, the same test `fronts.fade_gate` uses for
   "adding again".
2. `dwells` on `/api/warmap`: the day's APPROACH→DWELL→exit rows from `data/warmap/warmap_<day>.jsonl`
   (the ledger `sequence.py` already writes; today the route serves only the current `dwell`).
   About 15 lines, and it survives a restart because the ledger is on disk. Rows from
   `_backfill.jsonl` are drawn lighter (weight). Include `held_s` at the DWELL stamp so the box start
   stops being "stamp − 5 min".
3. `first` on `/api/oihist`: persist in `day_state` the first time `broke()` names an UNWINDING front
   (side, k, peak_at, peak, named_at). Rebuilding it after a restart needs peak OI per minute, which
   is rev 1's item 7 (absolute OI in the minute grid). Until then, persisting it is the only
   anytime-start-safe way.
4. The BOARD's copy of the ladder takes the same inputs. Build it once as a component and use it in
   both places.

## Questions for her (method, not presentation)

1. **Should the first stop need a minimum build?** Today it can land on a +0.6L front (BANKNIFTY
   09:25). A floor would be a §1d parameter; without one, the face prints the size.
2. Still open from rev 1: should §1d read the nine (±4) or the ±6 she sees? BANKNIFTY 57,000 CE, the
   biggest CE bar on the ladder, is faint because it is outside the nine.
