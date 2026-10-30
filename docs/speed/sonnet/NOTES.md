# RAFTAAR v2 — Sonnet's face (27 Oct 2026)

Open `RAFTAAR-v2.html` (self-contained, 438 KB, the data inside). Same five NIFTY days as v1, same engine
(`../final/raftaar.py`, untouched), played minute by minute. Space = play, arrows = step, click any strip = jump there.
Rebuild: `python export.py` (about 85 s, prints the self-check) or `python export.py --page` when only `live.html` changed.

Files: `export.py` (engine + fronts → `data.js` + the page) · `live.html` (template) · `data.js` · `RAFTAAR-v2.html`.
Reads only: `../final/*`, `tapemap/fronts.py`, `tapemap/data/chain|book|read` through `chainio`. Writes only here.

## 1. Three layouts I sketched

```
A  TIME STACK ON TOP, GAUGES BELOW          B  THREE COLUMNS                         C  HERO + ONE PRICE AXIS  (chosen)
+--------------------------------------+    +-------+-----------------+--------+    +-------+--------------------+-------+
| tile | sentence | OI trend           |    |ladder | price x time    | gauges |    | tile  | THE SENTENCE (big) |OI     |
+--------------------------------------+    |       |  (1.5 px/min)   |        |    +-------+--------------------+TREND  |
| price x time        (full width)     |    |       +-----------------+        |    |  stamp chips (RAFTAAR)  |ladder |
| lanes / trend / ribbon               |    |       | lanes           |        |    |  price x time ----------|=same  |
+--------------------------------------+    |       | trend / ribbon  |        |    |  CAP/FLOOR bands        |rows   |
| ladder | tug | tubes | quad            |    +-------+-----------------+--------+    |  lanes + KRAM           |-------|
+--------------------------------------+    time axis too narrow, ladder lonely       |  OI trend strip         |zor,   |
ladder far from price, 1000+ px tall                                                  |  picture ribbon         |tubes, |
                                                                                      +-------------------------+quad   |
```

**C and why (3 lines).** The ladder's rows ARE the price panel's rows (same strike axis, same row height, checked to the pixel), so
"where were the writers" and "where was price, and when" read as one picture: the spot path flows into the ladder, CAP / FLOOR
are bands you watch step over time and bars you read now. The sentence, the state tile and the OI-trend arrow are the first
thing the eye lands on (hero row); the lanes, the trend strip and the picture ribbon share the price panel's time axis, so a
vertical line through all of them is one minute. The gauges she liked (tug, tubes, effort-vs-result dot) stay, on the right.

## 2. What is new (her four asks)

1. **Price × time.** Spot path (tag s) coloured per minute by RAFTAAR's state (green CHAL ▲, red CHAL ▼, amber CHOP, purple PIN, blue ATKA,
   slate UNWIND, pale = KHAMOSH / BINA OI / WAPSI). CAP / FLOOR = bands at their strike that STEP when writers roll (a connector and
   "CAP ↑ 22,750s 12:45" at each step; band darkness = that wall's build so far). Every engine stamp is a ◆ at its time AND price;
   the newest ones are named in two rows of chips above the panel (time, Hinglish, grade n/N) with a dotted guide down to the ◆; older
   ones are named on hover. Writers' stamps (ruka / chhod / phir) are small markers on the path too. The future of the replay day is
   drawn faint behind the playhead (header says so); everything the engine "says" (tile, sentence, trend box, ladder) uses minutes ≤ now only.
2. **The sentence.** One Hinglish line ≤ 14 words in the middle of the hero row, built by template (`say()`), no AI. Pieces: the side the
   move hurts first, then the side it pays, each as "CALL 22,700 se bhaag rahe" / "PUT 22,600 pe likh rahe" / "CALL cap 22,700→22,800 upar" /
   "ruke" (strikes are the ones the engine itself named, biggest cut / biggest add), then the zor ("upar ka zor"), then price vs zor
   ("price saath" if the zor points the way price went, "price ulta" if not). Special lines for trapped writers ("… price chadh raha · phans
   rahe"), CHOP, PIN (k, s), ATKA, UNWIND, BINA OI, KHAMOSH, "padh rahe". Over 14 words it drops the least important piece first (checked: max 14
   on every minute of all five days, asserted in `check()`).
   **Held:** its key is word + direction (3 of 4 minutes) plus each side's behaviour class (covering / writing / rolling / still) and the
   zor sign (8 of 10 minutes); the text is the one said at the commit minute, so a flickering strike never rewrites it. 18–31 changes a
   day (about one per 12–20 min) against 5–18 for the word/direction alone.
3. **Writer timeline** (lanes under the price panel). See §3.
4. **OI trend.** See §4.

Kept as she liked: the coloured state tile (grade bar, ≠ READ badge, stamp toast), the strike ladder with growing bars, glowing tips and dashed
ghosts, the tug-of-war knob (with its 5-min ghost), the speed tubes, the effort-vs-result dot with its trail, the day ribbon (cell colour = picture,
height = grade, PUT ↑ / CALL ↓ speed under it), play / scrub / speed. Light theme only; every glyph sits next to a Hinglish word and a number
(time, lakh, n/N); every price is tagged s; no %, no hit rate.

## 3. Writer timeline — how it is computed (causal) and debounced

* **Fronts:** `fronts.read()` (§1d, unchanged) on the minute grid cut at minute T (`fronts.cut`), ranked by session-high absolute OI built
  the way `board.first_fold` builds it (open + running high of the change), for every minute from the 15th mark on. One lane per strike-side that
  was a top-2 front for ≥ 45 minutes of the day (max 3 per side); a flash-in-the-pan front is not a lane.
* **Raw state** per minute: B building at its high · S stalled · U unwinding · N never built today (§1d's own words). It flickers
  (27 Oct CE 22,700 around 09:40 reads B S B S U S U), so a lane state COMMITS only when it fills **≥ 3 of the last 4 minutes**; the two
  states that flicker on noise, a pause (S) and a restart (B), must fill **≥ 7 of the last 9 minutes** (~3 of her 3-min bars); no turn
  within 3 min of the last one; a commit is back-dated to the first minute of its window and is *known* at the commit minute (the replay
  draws a segment only once known ≤ now).
* **Stamps**, same vocabulary as Board.tsx: **ruka** = at the front's own high (`peak_at`; a restart that stalls again without a new high stops at its
  own local high); the lane is repainted amber from there. **chhodne lage** = first minute of the confirmed UNWINDING. **phir likhne lage** = first
  minute of the confirmed restart; the lane is hatched ("phir likh rahe") until the front makes a new high of its own, then solid again.
  Each stamp: time, spot at that minute (s), points since (spot now − spot then, live, ▲/▼), the build in lakh; hover + KRAM list + gutter line.
* **Checked against the Board** (`python export.py`, 27 Oct NIFTY, §1d re-read by the Board's own code at 10:00 … 15:00): for the Board's
  fronts that have a lane and are off their high, the Board's `peak_at` is a lane ruka stamp in **11 of 14**, and board.py's `unwind_at` is a lane
  chhod stamp within 2 min in **11 of 12**. E.g. CE 22,700: ruka 09:27, chhod 09:42 (Board: peak_at 09:27, unwind_at 09:42 — her example);
  CE 22,800 11:45 / 11:47 and 13:56 / 14:03; PE 22,600 11:19 / 11:32 and 14:32; CE 22,700 14:31 / 14:37. The misses are the Board's single
  day-peak cycle against a later cycle in the lane (the lane shows every committed cycle, the Board only the latest high), and
  PE 22,600 at 15:00 (Board peak_at 14:25, lane ruka 14:12), most likely a new high that came inside a restart shorter than the 7-of-9 bar
  (not traced further).

## 4. OI trend — definition (display, [I], causal)

For each of 15 / 30 / 60 min: Z = (PUT net OI change − CALL net OI change) over the 9 strikes nearest spot at t, the same strikes at both ends
(`raftaar.measures`, so the 15-min value is the engine's own net_L), and R = Z / (gross adds + cuts of both sides) ∈ [−1, 1], how one-sided the
writing was. A window **votes** ▲ (PUT build dominates; covering CALLs count) when R ≥ 0.40, ▼ when R ≤ −0.40 (≈ one side did 70 % of the
activity), else 0 (balanced); under 5 L of gross activity it cannot vote. **Verdict:** ▲ when ≥ 2 of 3 windows vote ▲ and none ▼; ▼ mirror;
else RANGE ("barabar" / "mila-jula" / "halka ▲ 1/3"). Held 3-of-4 to enter a trend, 6-of-8 to fall back to RANGE, ≥ 6 min per segment.
Shown as the big arrow + three window chips (direction and lakh) in the hero, and as a strip on the shared time axis (verdict row, then
three heat rows, colour = side, strength = |R|). It also says "OI ke SAATH / ULTA" against the 30-min price move (s). It is a direction
verdict, not a day type: RANGE here never contradicts §1o's CHOP / PIN, it only says the writers were not one-sided.

## 5. Checks done

* Page: 1,848 minute-by-minute draws over the five days + 618 more after the last build, 0 console errors, no NaN / undefined in any SVG,
  no horizontal scroll at 1229 or 900 px (single column under 1000 px), ~15 ms a draw. Hover tooltips, click-to-scrub and play verified.
* Ladder rows and price-panel rows share one top and one row height (measured, equal to the pixel at every day's strike count).
* `check()`: every sentence ≤ 14 words, lane segments monotone, the Board comparison above. Nothing under `tapemap/data` is written.

## 6. What I would still improve

* **BANKNIFTY / SENSEX** are run in lockstep (grades) but only NIFTY is drawn; the same stack works per index once `export.py` loops over them
  (SENSEX: NIFTY's flow, its own OI, §1q).
* **Live wiring:** fronts.read per minute is cheap (1.5 s for a whole day) but the server should keep each lane's raw series and commit
  segments as minutes arrive; lane set would then grow as fronts reach 45 min instead of being known from the full day (the replay hides a lane's
  label until its first segment is known, but the empty row exists).
* **Price axis zoom:** the ladder and the path share one axis, so on a 180-point day like 27 Oct the path is 4 rows tall; a toggle that zooms the
  price axis (ladder rows then stop lining up) would help a narrow day.
* **The debounce numbers** (3 of 4, 7 of 9, 8 of 10, R ≥ 0.40, ≥ 45 min lanes) are display [I] chosen on these five days by eye; they want her
  feel, not a backtest. 22 Oct PE 22,700 shows a lane with no stamps (building all day): a quiet lane is a result, but it costs a row.
* **On the chart** (BRIEF §9): the sentence, the three lane stamps and the CAP / FLOOR steps are the pieces that map onto the extension's
  grammar (≤ 6 chips, ≤ 4 words); not done here.
* **Chips are named for the newest ◆ only;** older ◆ rely on hover. A "last 6 stamps" list under the strip would name them without hovering.
