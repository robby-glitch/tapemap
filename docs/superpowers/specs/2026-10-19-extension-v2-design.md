# GoCharting extension v2 — design (Mary approved the build, 19 Oct 2026)

**Inputs:**
- `2026-10-11-decode-loop-design.md` (§4 RANK and FLOW STATE, §5, §10b)
- `docs/fresh-take/ORDERFLOW-STUDY.md`
- `docs/fresh-take/FLOW-STATE-STUDY.md`
- `docs/extension-v2/` (rule-driven mockup, NOTES, CRITIQUE-SONNET.md)

Mary: "we are modifying the whole extension, nothing is off limits." The extension is
`C:/Users/kaam/Desktop/Go charting/orderflow-desk`.

## 0. What the evidence says, and so what the extension must do
- **Marks:** as a stream they are close to no-information (era B: trap 15/14, absorption 28/27 WITH/AGAINST).
- **Prior-day nodes:** look like a placebo.
- **Flow states** describe the bar; they don't predict.
- **What did match the day:** writers' one-sidedness, VWAP crosses, fuel.

So the extension **draws far less, ranks everything against normal, says where and whether each thing still holds,
and logs every drawn object forward**.

## 1. Rules that bind (unchanged)
- **Roles:**
  - Advisory, no order path.
  - The page senses and draws; TapeMap is the brain, and the one wire stays `POST /api/frame`. Frame additions must be **additive**, so today's extension keeps working.
- **Display:**
  - Light theme only.
  - Hinglish chips with numbers, ≤ 28 characters.
  - Every level shows spot | fut, with "≈" where the basis drifts.
- **Folding and integrity:**
  - Fold on zone / flow / OI / VPIN, **never a candle close**.
  - No look-ahead.
  - A missing input shows "?", never zero.
  - The three absences ("checked, nothing" / "could not check" / "not shown") are never merged.
- **Process:**
  - No commits without her word.
  - No server or extension restarts during market hours.
  - She loads v2 herself.

## 2. Walls ("Buyers / Sellers ki deewar") — rebuilt
Today (`board.js walls()`), a wall is the top 20% of *today's own* 5-pt bins by net delta, the holder flips on two closes,
and one-bar "defended" absorptions are drawn as levels. So there are always walls, even on small moves.

**v2: a deewar must clear all four tests.**
1. **Big against normal:** the bin's net delta ranks ≥ p90 against **other days'** bins in the same day-part
   (reference from TapeMap, §7). Show the rank and N; while N < 30 the rank is marked provisional.
2. **Proven:** at least one **test held**: price came back into the row and left on the holder's side. An untested
   shelf is not a wall.
3. **Near:** within 1.5σ of price. Farther walls become edge ticks only.
4. **Ownership needs more than two closes.** It changes only on a **ranked** flow bar (SIZE ≥ p70) through the row
   plus a close beyond it.

**How it is drawn:**
- Chip: **"KHARIDAR KI DEEWAR 23,040 · p94 · 2 test"** (or SELLER).
- An OI-agreeing strike (fresh writing at the nearest strike, ranked) adds **"+ PE likh rahe"**.
- When broken: ✕ with **"TOOTI 23,040"** for 30 min, then gone.
- One-bar absorption "defended" levels are **never** lines; they are marks at most (§3).

## 3. Marks
1. **One cluster = one mark.** An absorption followed by a trap at the same price within 2 bars merges into one mark.
   Era B: 24 of 34 traps duplicated their absorption.
2. **Drawn (solid) only if:**
   - rank ≥ p90 against the same kind, other days, era-B-or-later builds only;
   - **and** the bar reached a σ ring (±1/2/3σ or VWAP), with σ frozen at the mark's birth ("@10:15").
   - Prior-day and developing-value levels are **not** part of this gate.
3. **Ghost tier:** rank p70–89 at a ring is drawn **hollow**, with no chip. Everything else is counted in the panel
   ("baaki N chhote").
4. **The flow state is a tag, not a gate:** PUSH / CLIMAX / ROKA from the FLOW-STATE definitions (SIZE slot-ranked,
   SHARE, within-day RVOL, R). CLIMAX and ROKA appear as a thin tint under the bar.
5. **Arrow-first names, where the arrow always means "favours up / down":**

   | Mark | Up | Down |
   |---|---|---|
   | trap | **▲ BECHNE WALE PHANSE** | **▼ KHARIDNE WALE PHANSE** |
   | absorption | **▲ KHAREEDAR NE ROKA** | **▼ BECHNE WALE NE ROKA** |
   | big print | **● BADA KHARIDAR / BADA BECHNE WALA {lots} @{p}** | |

   - A big-print bubble is sized by rank and drawn **at print time**, not at bar close.
6. **Status, live:**
   - **TIKA:** solid.
   - **TOOTA:** hollow with ✕ and the break price. A break is a close beyond plus σ-scale distance.
   - Marks more than 2σ from price are dimmed.
7. **Removed:** vacuum, the climax glyph (it becomes the tint), exhaustion on trend days, size labels, HH:MM stamps, tap
   rings, OI bars, drifting copies, broken-floor lines. Glyphs sit in the bar gutter, not on cells. At most 6 chips:
   at a level first, biggest first.
8. **Log** every drawn or ghost mark:
   - build version and row size;
   - **trapped side and winner as separate fields**;
   - rank and N, the ring, the flow tag;
   - status changes with their times.

## 4. Lines — budget: 2 when flat, 5 in a trade
- **In a trade:** kill · target · entry, drawn from their birth bar, with live points to each.
- **Flat:** the **armed plan** from the frame (trigger zone, kill, T1, with live distance). With no plan, the nearest
  qualifying deewar on each side (§2).
- **FLIP:** the writers' strike, from the READ via the frame.
- **Zone shading follows KHEL** (READ via the frame):
  - RIDE: the 1σ–2σ lane on the trend side;
  - FADE: her 2σ–3σ pockets;
  - BAITHO or unknown: none.
- Nothing beyond 3σ. Yesterday's H/L/C appear only when they are the nearest level on that side. HVN/LVN are edge ticks
  only.
- **Basis:**
  - a carry-model plausibility band (expiry-aware);
  - strike-native levels exact;
  - futures-native levels show "≈ spot";
  - an implausible basis is **one** banner, not a "?" on every label.

## 5. Right panel — terminal, the decode loop
```
NIFTY  {KHEL} · {SIZE} · {PREMIUM}                    {fut}f | {spot}s   {time}
khilaaf: {opposing ranked TIKA evidence within a row of price, if any}
DIN    writers A / absent side (ranked) · VWAP crosses · fuel over the swing (ranked: covering / naye long / naye short / OI flat)
ABHI   FLOW {PUSH▲|CLIMAX|ROKA|noise|no read} · p{rank} · GC+UX ✓ | GC only | sources disagree
SIRF BADE   time · event · rank · TIKA/TOOTA      (ranked ≥ notable only) · baaki N chhote · noise
PLAN   ≤ 2 rows with trigger / kill / T1 and live pts      — in a trade: FOLD BOARD
       ZONE · FLOW · OI · VPIN (entry → now, ranks) → HOLD / WATCH / FOLD
       VPIN counts only with flow against; otherwise a chip "expansion risk p84"
?      ≤ 3 lines, three typographies (checked-nothing / could-not-check / not-shown)
```
- Sizes and OI moves below p70 print as **"OI flat" / "noise"**, never as positioning words.
- SIZE shows only when it varies.
- One meaning per arrow.
- The 09:45 **day card** (|A| and the absent side, opening-flow rank, crosses, gap vs yesterday) is the top block
  until 10:15.

## 6. Alerts (≤ 4 kinds, a tone + notification, never for WATCH)
1. A solid mark is born.
2. The READ / KHEL word changes.
3. The fold board reaches FOLD.
4. The plan trigger hits (the zone touched with an agreeing ranked bar).

There is no feed-loss banner: Mary dropped it (18 Oct).

## 7. TapeMap side (additive, needed by the face)
- **`frame.read`:** the READ word / dir / KHEL / since / FLIP spot|fut / box. From `read.py`, already built.
- **`frame.plan`:** the armed READ-V2 §E entry zone, kill and T1 when the word allows it.
- **`frame.rank_ref`:** reference distributions per metric, slot and kind (wall-bin net delta, mark sizes by kind,
  5-min |Δ| by slot, the RVOL tail, writers' 30-min ATM±2 change, futures-OI swing change).
  - Built after the close by a tool (`tools/rank_build.py`) into `data/rank/`, from recorded days **before** today.
  - Served once per session; the page ranks against it.
- **`frame.writers`:** ATM±2 30-min CE/PE change with ranks, and QUIT events.
- Live after **her** restart, after the close.

## 8. Done when (checked by replaying recorded sessions through `main.js`, not just engine unit tests)
- `node test/engine.mjs` and `node test/shell.mjs` pass, plus a new test per rule in §2–§6 that fails on the old code.
- On replays of 9, 12, 13, 16 and 19 Oct and 3 random-time frames:
  - walls appear only when §2 passes;
  - the "always some walls" behaviour is gone on quiet stretches;
  - marks, lines and chips stay within budget;
  - nothing is drawn from data after T.
- Before/after screenshots per replay frame. `dist-v2/` is built **beside** `dist/` (her live extension is untouched).
- A short BUILD-REPORT covers what changed, what was deferred, how to load v2, and what needs her restart.
