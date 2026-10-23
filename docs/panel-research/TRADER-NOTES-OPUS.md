# My read of mockup v1, as a trader (20 Oct, written before Sonnet's critique arrived)

**The verdict:** mockup v1 is not good enough to show Mary. On 19 Oct 14:30, the day's clearest trend and the one she
traded (put 178 → 348), the panel says almost nothing: flow `? ref kam`, OI grey, TREND blank. A panel that goes blind on
the day that mattered has failed, however honest each rule is.

## The fixes I'd make
1. **Make "normal" today's own normal, with other days kept for hover.**
   - Pace = this side's 5-min lots ÷ the median 5-min lots so far today (both sides), from 09:45.
   - Before 09:45 use prior days' same slot. The open is special, and her opening drive matters.
   - This works from day one, on expiry days and on every index. It also fixes "a high-volume day lights everything"
     (day-volume correlation 0.76–0.90) and the `kam data` that appears on every block.
2. **Show buyers vs sellers as pressure, not two independent paces.**
   - Speed words go only on the side that is pressing.
   - When total volume fades, one row says `volume thanda` instead of `peak se neeche` on both sides.
   - The useful turn read is "the pressing side is tiring while the other side quickens". Show it only when both
     happen.
3. **Arrows mean price direction only.** Speed uses words: `tez` / `dheema` / `thak raha`.
4. **TREND = the READ word + "is it still being fed?"**
   - The trend itself is the header word and its since-time.
   - The TREND row counts how many blocks *now* agree with it: `RIDE ▼ · 3/4 abhi bhi saath`, or `1/4 — khurak kam` (the
     fuel is thinning).
   - This is a 15-min agreement count with no trend label of its own, which kills the `3/4 naye short` at the 16 Oct low.
5. **OI speed has a floor.** When the 60-min base is below the noise floor and the 15-min build is ≥ p70, it reads
   `naya build`. There is no ratio.
6. **The top strike is shown in the row's direction only:** the biggest addition when the side is building, the biggest
   cut when it is unwinding.
7. **Peers say ✓ or ✗ only after a test,** meaning NIFTY made a new extreme in the last 15 min. Otherwise they show `·`.
8. **SIRF BADE is ordered by the KHEL filter first, then recency.** It never shows three of the same kind.
9. **Data hygiene (from the builder):**
   - leave out the first Upstox minute after a recorder hole;
   - "own σ" = the same-clock RMS of the spot move on prior days;
   - show a stale READ as `READ hh:mm ka`.
