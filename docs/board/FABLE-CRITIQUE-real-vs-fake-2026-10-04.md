# Critique: "Real or fake?" (the OI flow split by side) — Fable, 2026-10-04

Read-only. Nothing edited, nothing started. Files read: `real-vs-fake-2026-10-03.md`, `sides-slots-2026-10-01.txt`,
`sides-power-slots-5-sessions.txt`, `oiflow-3idx-2026-10-01.txt`, `analysis/sides.py`, `analysis/replay.py`,
`BOARD-OVERHAUL-2026-10-03.md`, `fronts.py`, `chain_metrics.oi_flow`, `reader.py` WHO, `docs/reader/1-research.md`,
`docs/reader/2-data-audit.md`, `trapped_inventory.py` (assumption 3), and the raw `data/chain/` snapshots for the five
sessions. Two throwaway probes ran in my scratch area (not in the repo) on those five sessions only. Every number
below from them is **[M]** on recorded data; every judgment is **[I]**. Rows are described; nothing is a rate.

---

## 1. Verdict

1. **It is a real deal.** Splitting the near-ATM OI change into a CALL side and a PUT side is the right cut: the netted
   `chg_dir` column could never say *who* was acting, and the split did find 1 Oct 12:10, 24 Sep 13:30, 30 Sep 12:25 and
   14:25 for the right reason (put or call writers giving back on 8-9 of 9 strikes at many times their day size).
2. **Biggest flaw: it measures the wrong strikes against a scale that drifts.** The side totals are summed over all
   17 strikes of a window fixed at the open, which breaks her own top-2-near-ATM rule and nets far-OTM hedging strikes
   against the near-money book: at NIFTY 1 Oct 14:00 the 17-strike CE total read **+629k adding** while her two CE
   fronts read **−247k covering** (the squeeze the Board stamped at 13:58) [M], so the read said REAL ▼ at the day's
   low. And the "day median" is 3.4× larger at 09:50 than at noon [M], so the morning is structurally blind: 2 POWER
   index-slots before 11:00 in 15 index-days [M].
3. **Second flaw: it reads OI change without the premium, so it cannot tell forced from voluntary**, which is behind
   three of its own listed failures (expiry squaring, 15:00+ squaring, FAKE both ways). The snapshot already carries
   `ltp`, `avg` (the day's VWAP per contract), `iv` and `vol` per strike-side; none is used. `ltp > avg` at the fuel
   side's fronts separates 1 Oct 12:10 (9/9 strikes' writers underwater: forced) from 29 Sep 12:35 (4/9: squaring) and
   23 Sep 15:05 (0/9: profit-taking) [M].

---

## 2. Where the plan is wrong (first principles)

**2.1 Every OI change is attributed to writers.** Every contract has one long and one short; "OI up" creates both. The
quadrant in §1 of the plan reads ADD as "writers sell more" and COV as "writers buy back" in every cell. Who *initiated*
is in the premium, not the OI: option OI up with its IV falling is supply (writers), with its IV rising is demand
(buyers paying up); OI down with the premium rising against the move is covering, OI down with the premium falling is
longs leaving. `trapped_inventory.py` states the writer-dominated assumption as "right on average, wrong on specific
strikes on specific days" — the plan quotes it and then applies it to every strike in every 5-minute slot. The row that
shows the cost: **30 Sep 11:20 SENSEX FAKE (up slot)**, read as "put writers taking profit and leaving": PE OI fell
2.0M with the PE premium **−24.5** and all 9 strikes still above the day's avg (today's writers were still underwater,
so they were not the ones leaving at a profit) [M]. That is put *buyers* dumping — bullish, and +124 followed. The word
FAKE was wrong because the actor was wrong.

**2.2 "Put writers covering in a down move" is forced only when they are losing.** A writer who sold at 150 in the
morning and buys back at 100 after a dip is protecting a profit, not forced; the flow looks identical in OI. `avg` is a
usable basis for today's writers: ltp above it means the average writer of the day is underwater. Across the probe
rows the forced ones were 9/9 above avg (1 Oct 12:10 NIFTY and SENSEX, 24 Sep 13:30 BN and SENSEX, 30 Sep 14:25
SENSEX) and the squaring/profit-taking ones were 0/9–4/9 (29 Sep 12:35 all three; 23 Sep 15:05) [M]. The Board already
prints "price against them / in their favour since the peak" as a fact for the §1d fronts; this read ignores it.

**2.3 The "back" side is the next trap, not just a floor.** REAL = fuel side covering + back side adding. By her own
thesis (trapped inventory is the fuel) put writers adding into a fall are loading tomorrow's squeeze. REAL is right
about *this* move and silent about the cycle. Not wrong; incomplete, and the forward log should keep the back side's
build so the next episode's fuel is on record.

**2.4 Expiry day changes the meaning twice.** On 0DTE the OTM side squares all afternoon (covering ≠ forced), *and* the
premium read breaks too because decay dominates: 24 Sep 12:30 SENSEX (0DTE) PE IV **−4.0 vol pts in 5 minutes** [M].
The plan's caveat ("a weaker read") is right but has no teeth: 29 Sep 12:35 fired a 3-of-3 ▼ first sign and all three
rose. NIFTY expires Tuesday, SENSEX Thursday, BANKNIFTY the last Tuesday of the month, so **every session has the
three books at different points of their cycle** (1 Oct: SENSEX 0 DTE, NIFTY 5, BANKNIFTY 26) and a 3-of-3 count is
three different gamma regimes voting as equals.

**2.5 BANKNIFTY is not a units problem; it is a 26-DTE monthly book.** Checked in the data [M]: BANKNIFTY chain
expiry 2026-10-27; all OI divisible by its lot (30), NIFTY by 65, SENSEX by 20. Near-ATM OI at 12:10 on 1 Oct: NIFTY
85.5M units = 1.32M lots = ₹1,925bn notional; SENSEX (0DTE) 57.9M units = 2.90M lots = ₹4,184bn; **BANKNIFTY 3.66M
units = 122k lots = ₹201bn**. So it is ~4% of NIFTY in units, ~10% in notional, not 1% (the 1% came from the netted
`diff` column). More important than size: at 26 DTE an ATM option has roughly a tenth of a 0DTE option's gamma, so
BANKNIFTY writers are not *forced* by a 100-point move the way SENSEX 0DTE writers are. Turnover of near-ATM OI in the
fuel slot: 0DTE books 23–45%, BANKNIFTY 2–5% [M]. Its "CE covering ×4.2" at 10:35 on 1 Oct (then −174) is the weakest
evidence on the screen, as the plan says — and it should not be a third equal vote.

**2.6 The 15:00–15:30 window.** 23 Sep 15:05 NIFTY PE covering ×4.1 with **0/9** strikes above avg and the premium
falling: writers closing winners into the close [M]. The clock guard ("15:15 se check nahi") is right; the data
signature says the same thing from 15:00 and does not need the clock.

**2.7 "First sign" is a confirmation by construction.** The slot compares ΔOI over (t−5, t] with ΔI over the same
window; OI reaches the feed about a minute after the trade (the data audit measured ~60 s for NSE futures OI, 162 s for
BSE). In the first-sign slots the index had already moved: 1 Oct 12:10 −35 / −100 / −109 inside the slot itself. The
plan's own round 2 says "agreement arrives *with* the move". That is fine — her question is "is this move real", and a
confirmation answers it — but the chip must not be called PEHLA SANKET unless the forward log earns it (kill K2).

**2.8 The scale is not stationary.** Expanding median of |ΔPE| for NIFTY 1 Oct: 1,838k at 09:50 → 1,325k at 10:30 →
538k at 12:00 → 520k at 15:00; SENSEX 2,484k → 738k; 30 Sep NIFTY 2,591k → 968k [M]. The same absolute burst is
"nothing" at 10:00 and "POWER ×3" at noon. Root cause: the six warm-up slots are the opening, and the opening is
3–10× midday (NIFTY 09:20: 6,084k/5,114k; 09:55: 822k/266k) [M]. **I tested a rolling one-hour median as the fix and it
does not work** — morning POWER goes 2 → 3 index-slots in 15 index-days, while afternoon rows go up ~40% (12:00–13:29:
35 → 49; 13:30–14:59: 36 → 58) [M]. The morning cannot be read against its own opening; see improvement 7.

---

## 3. Ranked improvements

Each says whether it alters a §2-fixed definition. **Anything marked DEFINITION must be decided and written into §2
before Monday's open**, because the forward log records what the definition produces.

| # | the problem | the evidence | the change | alters definitions? |
|---|---|---|---|---|
| **1** | Side totals sum 17 strikes of a window fixed at the open; nets far-OTM hedging against the near-money book; breaks her top-2 rule; window goes lopsided on trend days | NIFTY 1 Oct 14:00 CE: 17-strike **+629k** (ADD) vs nine +1,057k vs **her top-2 −247k** (COV) → read REAL ▼ at the low, then +83 [M]. SENSEX 12:10 CE: 17-strike +1,229k vs nine **+2,207k** (far 0DTE calls squaring hid 45% of the near-ATM writing) [M]. Re-run on the nine: every marquee turn survives (24 Sep 13:30 ×3, 29 Sep 11:15 ×3, 30 Sep 14:25 ×3, 1 Oct 12:10 N+S, 14:35), **1 Oct 14:00 NIFTY drops out of POWER**, 30 Sep 12:25 NIFTY goes ×3.6 → <3 (BN and SENSEX still powered) [M]; POWER count per band unchanged | ΔCE/ΔPE summed over `fronts.nine` at the mark (already computed for breadth); nothing else | **DEFINITION** (§2 "strikes", ΔCE/ΔPE) |
| **2** | Breadth 6/9 counts a one-lot move on a thin strike as equal to the ATM; BANKNIFTY 100-step strikes carry 15k–130k OI beside 788k/901k at the 500s, so its 8/9 is noise | BN 1 Oct 12:10 snapshot [M]; BN 12:25 top-2 CE −6k against a total of +2k [M] | POWER requires **both top-2-by-OI fronts on that side (inside the nine) moving the side's way** — her rule, a 2/2 count; keep n/9 as a logged field | **DEFINITION** (§2 "breadth", "POWER side") |
| **3** | OI change alone cannot say forced vs voluntary; this sits under failures 3, 4 and 6 | 1 Oct 12:10 NIFTY/SENSEX PE **9/9** above avg (forced; −300 leg). 29 Sep 12:35 NIFTY **4/9**, SENSEX **3/9**, premium flat, IV falling (squaring; rose). 23 Sep 15:05 NIFTY **0/9** (profit-taking; nothing). 30 Sep 11:20 SENSEX FAKE: PE premium −24.5 with OI down = longs leaving (+124). 30 Sep 10:40 SENSEX FAKE: CE OI +1.6M, IV −1.0, **1/9** above avg = writers supplying in profit (−38) [M] | A chip from existing fields: `forced 2/2` (ltp > avg at the fuel side's top-2) / `chhod rahe, profit mein` / `buyers nikle (premium gira)`; log the 0–2 count and the nine's median ΔIV. **Round 1: chip and log only, re-word nothing** | Not in round 1. If she wants it to re-word FAKE or expiry rows → DEFINITION, decide before Monday |
| **4** | "3 of 3" treats a 26-DTE monthly book as an equal vote to a 0DTE book | ₹201bn vs ₹1,925bn vs ₹4,184bn near-ATM notional; turnover 2–5% vs 23–45% [M]; BN's first sign 15 min late on 1 Oct, alone and wrong at 10:35 | The count is **weekly books agreeing, 0/1/2** (`NIFTY+SENSEX 2/2`), BANKNIFTY shown as `BN saath / BN chup / BN ulta`, every index with its DTE tag (`SENSEX 0DTE`); log `n_weekly_power` and `bn_power` apart | **DEFINITION** (§2 "three indices") |
| **5** | A 15-minute gap re-arms "first sign" inside one leg | NIFTY 1 Oct ▼ first signs at **12:10, 12:50, 13:45**; SENSEX ▼ at 12:10, 12:50, 15:30 [sides table] | A direction re-arms only after a POWER slot in the **opposite** direction; later same-direction POWER is `phir se`, never `pehla`. No number | **DEFINITION** (§2 "first sign") |
| **6** | The read does not know a leg is late | By 14:00 on 1 Oct, **115%** (NIFTY) / **107%** (SENSEX) of the put build that stood at the first-sign nine had been given back: nothing left to cover [M]. 30 Sep NIFTY 12:25 → 12:50: **34 pts for ×3.6 → 15 pts for ×4.3**, fuel-left still 66% — effort up, result down [M]. Neither measure catches both; show both | Two display facts under the chip: `110 min · −270 pts · fuel 115% gaya` and `asar: 34 → 15 pts` (|ΔI| per × of the fuel side, this slot vs the first-sign slot, same episode only, Kyle-style rank as `docs/reader` asks). No threshold | No (display + log) |
| **7** | The morning is blind: warm-up = the opening, 3–10× midday; nothing registers 09:50–10:30; rolling median does not fix it | §2.8 [M]; probe: 2 POWER index-slots before 11:00 in 15 index-days, 3 under rolling-12 [M] | Round 1: footer `subah ka scale: ~10:30 tak power dikhna mushkil` (honest absence, never QUIET) and log turnover `|ΔOI9| / OI9` so a stationary scale can be judged later. Option she can pre-register: first-hour scale = the previous session's 10:30–15:00 median for the same index, tagged `kal ka scale` (anytime-start compatible, the server holds yesterday's grid) | Footer: no. The option: **DEFINITION** (§2 "day scale M") |
| **8** | Grinds never reach ×3 (23 Sep morning; 1 Oct 10:50–11:25) | plan §5.1 | Do not invent a slope. The per-side row shows `likh rahe · 6 slots se` (TEENO's "N marks in a row" counter exists) plus the Board's §1d state for that side (`ruka 10:41`). POWER is the burst marker on top | No (display) |
| **9** | Nine English words (REAL/SQUEEZE/CAPPED/FAKE/BACKED/HOLLOW/QUIET/PRESSURE/WALL) for a 2-second read; REAL vs SQUEEZE did not separate outcomes (plan §5.2); FAKE split both ways (§5.6) | plan §5; probe C | Headline = fuel side + forced chip + books + age (see §6). The word becomes a logged field. **Log the raw side states and ratios**, so any re-wording later is a re-derivation and never breaks the log | No, provided raw states are logged (improvement 10) |
| **10** | `rec(t)` silently takes the last minute ≤ t, so a poller gap makes a "5-min" slot 8 minutes; the fixed window left **2/9** of the nine below spot at the 1 Oct low | probe B NIFTY 14:00 `below-spot 2/9` [M]; `sides.py` line 72 | Log `slot_from`, `slot_to`, `nine_below_spot`, `grid_src`; show `nine tedha` when either side of spot has < 3. (The poller's window following spot is a server change: name it, do not do it here) | No (log + display) |

Not an improvement, a correction to the plan's worry list: **drop the BANKNIFTY units question**; it is answered (§2.5).

---

## 4. Significance, look-ahead, cross-index (the questions asked)

**"≥3× own median AND ≥6/9".** 3× is a round, pre-registered number and fine as such. The median is the problem (§2.8)
and the breadth is unsized (improvement 2). Scale-free across indices it is not: the ratio compresses on expiry day
(the median is huge) and inflates on fresh-series mornings (Wednesday NIFTY, Friday SENSEX). Turnover `|ΔOI9| / OI9`
is the honest scale-free unit — 1 Oct 12:10 read **9.3% on both NIFTY and SENSEX** [M], identical on two exchanges —
but a fixed % would need a per-DTE table, which is tuning. Log it, do not threshold it.

**Look-ahead in `sides.py`:** none found. The median uses earlier slots only (history appended after the slot is
read), breadth and the nine are taken at the mark, the first-sign state is causal, and +15/+30 are the declared
outcome. Two honest caveats: the first slot can be shorter than 5 minutes (first live snapshot 09:17 against the
09:15 backfill mark), and backfill marks and live snapshots are mixed in the warm-up — tag, not bug.

**Cross-index.** NIFTY and SENSEX are near-duplicates in *price* (all 30 SENSEX names are in NIFTY 50) but
**independent samples in the book**: different exchange, different expiry weekday, different crowd. Two books forced
on the same move is the strong signal; that is why `2/2 weekly` beats `3/3`. BANKNIFTY (banks only, monthly) is a
witness. **Lead-lag is unreadable at 5-minute resolution** with ~1–3 minutes of OI dissemination lag: in the five
sessions the three fired in the same slot or NIFTY+SENSEX one slot ahead of BN (1 Oct), with no consistent leader.
Log each index's 1-minute first-cross time as a field; display nothing about lead-lag until 30 sessions say otherwise.

---

## 5. Forward-log spec and kill conditions

**One row per 5-min slot per index, every slot, not only POWER** (base rates need the quiet rows). Written by the
live process at the mark; outcome fields filled by the same process at t+15 / t+30, never recomputed from a re-cut
cache (CLAUDE.md §2, the anytime-start rule).

| group | fields |
|---|---|
| identity | `day t idx expiry dte expiry_day slot_from slot_to grid_src(live/backfill/mixed) n_nine nine_below_spot shown shown_why(ok/warm/frozen/stale)` |
| sides as fixed in §2 (whatever §2 says after Monday's decisions) | `dce dpe M_ce M_pe c_state p_state c_ratio p_ratio c_same9 p_same9 c_power p_power` |
| sides on her strikes (logged alongside whichever is not the definition) | `dce9 dpe9 top2_ce[] top2_pe[] dce_top2 dpe_top2 top2_ce_agree(0-2) top2_pe_agree(0-2) turn_ce turn_pe` |
| who paid | `fuel_side fuel_top2_underwater(0-2) fuel_dIV_med fuel_dVol9 back_top2_underwater` |
| index | `spot dI M_I I_state` |
| words | `word pdir first episode_t0 pts_since_first min_since_first fuel_left result_per_effort` |
| cross | `n_power n_weekly_power bn_power same_word` |
| Board at the same minute | `board_verdict board_leader_side board_leader_peak_at` (does this read add anything over §1d?) |
| outcome | `f15 f30 mfe30 mae30` (excursions in the sign's direction from the 1-min grid) `outcome_src` |
| hers, after close, optional | `her_read` (one word in her words) `leg_traded` |

**Kill conditions.** Pre-registered now; **Mary writes the bar for each before Monday** (the repo rule: the pass bar is
stated before the numbers are read; no rate is printed; rows are listed). Each is a comparison the log must make
possible; the number in the bar is hers.

- **K1 Premise.** First signs with `n_weekly_power = 2` in the same direction, signed `f30`, listed beside the same
  days' non-POWER slots' signed `f30`. If after 30 sessions they are not distinguishable by her bar → the three-index
  line comes off the Board.
- **K2 Lag honesty.** In first-sign rows, the slot's own `dI` against `f30`. If the slot's move is typically as large
  as what follows → the chip is renamed **PUSHTI** (confirmation) for good, never PEHLA SANKET.
- **K3 BANKNIFTY.** BN POWER rows against BN non-POWER rows. Indistinguishable → BN leaves the count, stays a witness.
- **K4 FAKE.** FAKE rows' signed `f30` still split both ways → the word is deleted; the two side numbers remain.
- **K5 Expiry.** On `expiry_day` rows, `fuel_top2_underwater` listed against outcome. If it does not separate squaring
  from forced → covering reads mute after 12:00 on that index's expiry day.
- **K6 Exhaustion.** Continuation rows with `fuel_left ≥ 100%` listed against first-sign rows. If they read the same and
  end the same → `fuel_left` becomes a word (`KHATAM`) on the chip.
- **K7 Grind.** Her after-close `leg_traded` legs that never had a POWER slot, counted. If most of her legs were
  grinds the read never saw → the burst marker is demoted to a chip on the §1d rows and stops being a headline.

**Must be decided before Monday (they change what the log records):** improvements **1, 2, 4, 5**, and whether **3**
is a chip or re-words, and whether **7**'s `kal ka scale` option is taken. Everything else can land any day.

---

## 6. Presentation: what she must see in 2 seconds

Line 1: `▼ PUT WRITERS KAAT RAHE · NIFTY ×9 · SENSEX ×4 (0DTE) · BN chup · forced 2/2 · 12:10`
Line 2: `40 min · −180 pts · fuel 60% gaya · CE likh rahe ×2.8 (floor banta)`

When nothing: `koi power nahi · PE likh rahe 6 slots se` (never a blank, never QUIET on a grind). Before ~10:30:
`subah ka scale` footer. After 15:15: `15:15 se check nahi`. Until K2 is passed the time chip reads `pushti 12:10`,
not `pehla sanket`.

---

## 7. Keep exactly as is

- The **per-side split** itself, and the reason for it (§1 of the plan: the netted column cannot answer her).
- The **5-minute slot on `ChainState.oi_flow`**, `fronts.nine`, the WHO template: reuse, not re-derivation.
- **≥3× as the burst number**, and sizing against the index's **own** scale (scale-free in intent; only the window of
  the median and the strike set are wrong).
- **PRESSURE / WALL on a flat index** — effort without result is the right instinct and the only place the plan reads
  effort against result.
- The direction mapping (CE covering ▲, PE adding ▲, PE covering ▼, CE adding ▼; two opposite POWER sides = no
  direction).
- The **15:15 freeze guard**, the "a missing index never agrees" rule, the expiry-day tag, the
  "steady writing, no power" sentence instead of an empty cell.
- **Display-only, gates nothing, counts never percentages, rows never rates**, and the plan's own §5 failure list,
  which is the most honest part of the document.
- `sides.py` as the analysis tool: causal, read-only, and it says where its numbers come from.
