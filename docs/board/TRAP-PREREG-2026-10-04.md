# The trap layer: pre-registration (rev `trap-1`)

**Fixed 2026-10-04 02:11 IST.** This was written before any trap read was run against outcomes, and before Monday
2026-10-05's open.

Source: Fable's framework, `FABLE-TRAP-FRAMEWORK-2026-10-04.md` §3 (the checklist) and §5 (the three Board lines and
"must be pre-registered" 1–6). Mary's word: "go build the trap layer".

**Status: SHADOW.** It is display and log only, tagged [I]. It changes no verdict, no word and no count anywhere. It
is built as `tapemap/trap.py` (pure), `/api/trap`, and `data/trap/trap_YYYY-MM-DD.jsonl`.

**Read before fixing this.** The structure of 1 Oct was looked at before fixing, but not its outcomes, and it is said
here:
- which levels warmap stamped and what they were;
- the top-2 net adds per side in a few windows;
- the reader's legs around 12:00.

That look decided rule R1's gap clause and rule R5's attachment, below. No f15/f30 or outcome of any trap was computed
before this file existed.

---

## 1. The six states (per index, per level)

**Levels.** Only the stable levels warmap's sequence machine already runs (`levels.py` → `sequence.py`):
- PDH, PDL, PDC, PWH, PWL, OPEN;
- ROUND levels on the **major** grid only (`levels.ROUND_STEPS`: NIFTY 100, BANKNIFTY 500, SENSEX 500).

Minor rounds (NIFTY 50s) are not traps.

**Stamps.** Warmap's own sequence rows are reused unchanged: `data/warmap/warmap_<day>.jsonl`, plus `_backfill.jsonl`
for a restart's replay of the morning. A row's `backfill: true` makes everything derived from it `src: "backfill"`.
`dwell.py`'s band and `DWELL_MIN_S = 300 s` are reused unchanged.

One trap record per (index, level) per session. It accumulates every stamp in time order:

| state | opens when | notes |
|---|---|---|
| **REACHED** · pahuncha | the level's first `APPROACH` stamp today | every later APPROACH increments `tests` |
| **DWELL** · ruka | a `DWELL` stamp at the level (dwell.py: in-band ≥ 300 s) | each DWELL is listed |
| **INDUCED** · phansaya | a `BREAK` stamp at the level (with its `RUN` and named target), direction UP/DOWN | **Gap clause:** at the session's first stamped minute, a static level (PDH, PDL, PWH, PWL; not PDC, the reference, nor OPEN) lying strictly between the previous close (PDC) and the session's first index print is INDUCED at 09:15, in the direction of the gap, tagged `gap`. Warmap's machine starts IDLE and cannot stamp a break that happened between sessions. A gap-INDUCED level is REACHED at 09:15 too |
| **FAILED** · fail hua | a `FAILED` stamp on that level's RUN (price back through the broken level by more than a band) | for a gap-INDUCED level: a later `BREAK` at the same level in the opposite direction |
| **RELEASED** · chhoota | see R4 | per index; attached to one trap by R5 |
| **TRAVELLING** · chal pada | the first warmap `HIT` stamp (any level) after a RELEASED, in the release direction | each later HIT that way, up to the next RELEASED on the index or the close, is the chain `→ 22500 → 22400` |

A trap record never closes during the session; its stamps are the record. REJECT stamps are kept, and REACHED +
REJECT with nothing else is the "pahuncha · toota nahi" read.

## 2. Rules

- **R1 The level price is AT.**
  - At a mark t, the levels whose machine state is APPROACH or DWELL (from the stamps up to t) are "at".
  - The TRAP line shows the one nearest to the index print. If none is at, it shows the most recently stamped level
    with its last state.
- **R2 The loaded side** (pre-registered item 2). Over the trap's slots "during the dwell", meaning the sides slots
  from its REACHED up to (not including) the slot being judged whose closing mark found price AT the level (R1):
  - sum the sides read's `dce_top2` and `dpe_top2`, the top-2-by-OI fronts at the nine;
  - the loaded side is the one with the larger **positive** sum;
  - neither positive gives "koi load nahi".
  - One rule, no number.
- **R3 Away from the loaded side.** Loaded CALL (a lid above) means away is ▼. Loaded PUT (a floor below) means away is
  ▲.
- **R4 RELEASED** (per index). A rev-`sides-3` POWER slot whose `pdir` is away from the loaded side of the trap it
  attaches to (R5), with that slot's forced chip ≥ 1/2.
  - A morning POWER slot (t ≤ 10:30) can release, tagged `subah witness`, as sides-3 B4 treats it.
  - A slot with no forced reading (no saved snapshot) cannot release, and says so.
- **R5 Attachment.** A POWER slot is judged against the trap of the level price was AT at the slot's **opening** mark
  (R1), or, if none was at, of the level that BROKE inside the slot. If several, the one nearest the index print at
  the opening mark. If none, the POWER slot is logged as `release_unattached` ("kisi trap pe nahi") and is never a
  RELEASED.
- **R6 WHO on the release leg** (item 5). This is the reader's first confirmed leg in the release direction whose start
  t0 is at or after the release slot's opening mark:
  - `new_longs` / `new_shorts` give **chalega** (new positioning);
  - `short_covering` / `long_liquidation` give **agle level tak** (covering only);
  - `rotation` gives "OI flat";
  - no reader log or no such leg yet gives "check nahi" with the reason.
  - Log only; it is shown on the AGLA line as a witness.

## 3. Log-only fields (items 3, 4, 6 and `oi_prev`)

- **`tape_with`** on every sides POWER slot, NIFTY only, raw, no threshold:
  - `vpin_fast_max`: the fast VPIN bucket (`data/vpin_fast.jsonl`, NIFTY future) with the largest |buy − sell| closing
    inside the slot, as signed imbalance and buy/sell;
  - `ux_delta` and `ux_vol`: the 5-min UX bar opening at the slot's opening mark (`data/tape/ux_NIFTY_<day>.jsonl`);
  - `swept_net`: buy − sell swept quantity on NIFTY-FUT inside the slot (`data/senses/`).
  - SENSEX and BANKNIFTY: `tape_with: null`, `tape_why: "check nahi — futures tape patla (~4 lots/min)"`.
- **Cross-index extremes at INDUCED** (item 4). From the xindex shadow log row at the first 3-min bar at or after the
  BREAK stamp (`data/xindex/`), in the break direction:
  - the verdict, each index's status (TOOK / EQUAL / FAILED / NAHI) and X3's first and stamps;
  - "check nahi (xindex log nahi)" before 30 Sep.
- **`pulled`** (item 6): `pulled_buy_qty` / `pulled_sell_qty` on the index future in the five minutes before the
  POWER slot opens, (from − 5, from], and inside the slot, from `data/senses/`.
- **`oi_prev`**: yesterday's closing book per strike, from the previous session's saved chain file (its last
  snapshot: `oi`, `avg`, `ltp`, per side).
  - Logged per slot: `prev_oi_top2_ce/pe` (yesterday's closing OI at today's top-2 strikes) and
    `prev_underwater_ce/pe` (0–2 of today's top-2 whose ltp at the mark is above **yesterday's** VWAP), so overnight
    writers who are underwater at 09:15 are visible.
  - **A new field only.** No existing module's 09:15 baseline is changed; Mary has not approved that.

## 4. The forward log, `data/trap/trap_YYYY-MM-DD.jsonl`

- `kind:"state"`: one row per state change (REACHED, DWELL, INDUCED, FAILED, RELEASED, TRAVELLING, and
  `release_unattached`), with the level, its px, the stamp time, the direction, `src`, and the item 3–5 fields where
  they belong.
- `kind:"slot"`: one row per index per closed 5-min slot: the level price is at, the active trap and its states so
  far, the loaded side with both sums, `tape_with`, `pulled`, the `oi_prev` fields, and `src`.
- `kind:"outcome"`: per RELEASED, f15 / f30 / mfe30 / mae30, written once by the live process after t+30 (sides'
  `outcome`), never recomputed.
- The market-hours guard, once-only per row key, the same-session guard and the src tags are `sides_log`'s, reused.

## 5. Kill conditions, SIGNED

**Signed by Mary, 2026-10-04 ~11:10 IST: sab haan.** Every bar K1–K7, K-A–K-D and the optional K-Z is signed **HAAN** as drafted, unchanged, together with the three standing lines. Her words were "yes do all fixes and sab haan", relayed by the coordinator. By the sheet's own rule the clock starts at the first session after signing, Mon 2026-10-05. The 27 sides sessions and the ten trap sessions already seen never count.

These are copied verbatim from `FABLE-DAYS-ZONE-KILLBARS-2026-10-04.md` §3, which holds the sheet's rules (`f30`, `base30`, 15 per cell, seen rows never pooled). They replace the placeholders `K_A_BAR … K_D_BAR = ⟨Mary⟩` that stood here at 02:11.

| # | what is compared | fields | judge at | PROPOSED bar | if it fails | sign |
|---|---|---|---|---|---|---|
| **K-A** trap premise | RELEASED rows (POWER + forced ≥ 1/2 away from the loaded side, within 60 min after REACHED / INDUCED / FAILED at a named level) against POWER rows with no level within 60 min | `trap_state, level, loaded_side, first, forced, f30` | 15 RELEASED and 15 no-level POWER rows | RELEASED median signed `f30` ≥ **1.5 ×** the no-level rows' median, and ≥ **0.75 × base30** | line 1 (TRAP) becomes description only: no word RELEASE, no arrow | **HAAN** |
| **K-B** induce → release | INDUCED + FAILED events, counted by whether a RELEASED away from the break follows within 60 min | `trap_state` transitions with stamps | 15 FAILED events | at least **8 of 15** release within 60 minutes | line 1 reads `trap toota · release ka intezaar` and never anticipates a release | **HAAN** |
| **K-C** tape witness | RELEASED rows on NIFTY split by `tape_with` sign agreeing / disagreeing with the fuel direction | `tape_with, f30` (NIFTY only) | 15 rows in **each** cell (the disagreeing cell may stay thin → INCONCLUSIVE, the clause stays) | agreeing median signed `f30` ≥ **1.5 ×** disagreeing median | the tape clause leaves line 2; `tape_with` stays a logged field | **HAAN** |
| **K-D** WHO | RELEASED rows split by the reader's class on the release leg: new positions (`new_longs` / `new_shorts`) vs covering only (`short_covering` / `long_liquidation` / `rotation`), each counted on "reached the next level and reversed ≥ 0.5 × base30 within 30 min" | `who_class, next_level, f30, mfe30, mae30` | 15 rows per class (NIFTY; BN/SENSEX only if their reader legs are not `thin`) | covering-only rows reverse at the next level in **≥ 8 of 15**; new-position rows in **≤ 5 of 15** | line 3 drops `chalega` / `agle level tak`; WHO stays logged | **HAAN** |

The standing lines, signed with them:

1. **Seen rows never count.** The 27 sides sessions and the ten trap sessions in this and the two earlier Fable
   documents are the record of how the bars were chosen, not evidence for them.
2. **Under 15 per cell is INCONCLUSIVE** and gets no verdict and no screen change, favourable or not.
3. **The scorer must run.** `trigger_log.py score` after each close (or scheduled), or K-Z and every zone question
   above stay unanswerable; the fold outcome rows and the kill-clock reader the review asked for (`tools/kill_clocks.py`)
   are the same need in one file.

## 6. The Board

Under TEENO, collapsed by default as `TRAP · shadow ▸`. Opened, it shows Fable's three lines for the active index:

```
TRAP     <level px> pahuncha <t> · <toota t / toota nahi> · <fail t> · ruka <N min> · <loaded side> likhe <sum>
CHHOOTA  <▼/▲ t · kaat ×N · forced n/2 · tape (NIFTY) · CE/PE …>   or   koi release nahi · <why>
AGLA     <next levels HIT> · <WHO: chalega / agle level tak> · <f30 never shown>
```

Hinglish words, with the number beside every glyph. Each index has its own could-not-check sentence. The headline,
TEENO and every count are untouched.

---

## Addendum, 2026-10-04 02:38 IST: build notes (no state, rule or threshold changed)

Written after the build and before any outcome was read for a decision. None of these changes what a state means.

- **A restart is read as one machine.** Warmap's `_backfill.jsonl` holds a restart's replay of the morning, and the
  live machine continues from that replay. So the day per index is the **last** replay plus the live rows after its
  last mark. An earlier process's live rows inside the replayed stretch, and earlier replays, are superseded, never
  counted twice (`trap_log.Day.stamps`, pinned by a test).
- **A gap row's src.** The 09:15 gap rows are `src: backfill` when the process started after 09:15. They were rebuilt
  from the grid, not observed.
- **The log waits for the war map.** An index's trap rows are not written until the war map reports its morning
  replay done. A read before that would lose the morning, and that row is once-only.
- **The release names the side that made it POWER.** The RELEASED row's `act` names it in her words, and
  `x = max ×` across those sides, as TEENO does. For example `PE kaat ×9`, or `CE likh ×4 · PE kaat ×4`. The first
  draft printed the cut side always, which mislabelled a CE-likh release.
