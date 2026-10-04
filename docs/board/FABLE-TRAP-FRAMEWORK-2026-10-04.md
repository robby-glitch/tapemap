# The trap framework: how order flow, OI and levels connect — Fable, 2026-10-04 (round 2)

Read-only. Nothing in the repo edited, nothing started, nothing written under `data/`. Three throwaway probes ran in my
scratch area (`flow1oct.py`, `otherdays.py`, `morning.py`). **[M]** = measured on recorded rows; **[I]** = inferred.
Rows are described; no rate is printed. Her thesis (2026-08-22) is the spine: price is walked to a retail reaction
point, left there while retail loads, the stops become liquidity, the move runs to the next reaction point.

---

## 0. What order-flow data exists, honestly

| source | days | indices | what it is | usable for |
|---|---|---|---|---|
| `data/tape/tape_NIFTY_*` (GoCharting 5-min footprint, ladder, delta, fut OI) | 11 Sep, 18 Sep, 21 Sep–1 Oct | **NIFTY only** | vendor-classified buy/sell per print | NIFTY delta/CVD, marks |
| `data/tape/ux_<IDX>_*` (Upstox book → 5-min bars via `ladder.py`) | 22 Sep–1 Oct | all three | side inferred per print against the touch | NIFTY: full. **BANKNIFTY: thin** (60–900 lots/bar). **SENSEX: unreadable** (median 4 lots/min on 1 Oct, zero depth sweeps all day) |
| `data/tape/ofd_marks_NIFTY_*` (the extension's P/A/E/C marks) | 21 Sep–1 Oct | NIFTY | absorption / initiative / trap / climax / exhaustion / vacuum per bar | witnesses; 93 marks on 1 Oct [M], too many to be a signal |
| `data/reader/reader_<IDX>_*` (the leg engine: legs, effort/result, WHO) | **30 Sep, 1 Oct only** | all three | legs with Δ, lam, OI, WHO class, absorbed | the cleanest "who" read; SENSEX legs 34 of 46 `thin` [M] |
| `data/vpin_fast.jsonl` / `vpin_log.jsonl` | 23 Sep–1 Oct / 25 Aug–1 Oct | **NIFTY future only** | toxicity buckets, percentile-so-far | one-sidedness confirmation, lagging |
| `data/senses/` (depth events: swept / pulled, qty, side) | 20 Aug–1 Oct, ~1M rows a day | all three futures | sweeps and withdrawn quotes | NIFTY intensity; BN thin; SENSEX none |
| `data/warmap/` (level machine: APPROACH/DWELL/BREAK/RUN/HIT/FAILED/REJECT at PDH/PDL/PDC/OPEN/PWH/PWL/ROUND) | 24 Aug–1 Oct | all three (index price) | **the level stamps** | every index, every day — the one flow-independent piece |
| `data/xindex/` (cross-index extremes, lead, sync) | 30 Sep–3 Oct | all three | did each index take its own swing high/low; who first | the induce's signature |
| `data/chain/` (per-strike OI, ltp, avg, iv, vol) | 20 Aug–1 Oct | all three | the books | the sides read, forced/voluntary, who loaded |
| `data/frame/` (extension frames) | 15 Sep–1 Oct | all three | trapped.writers, tape.aggressor, breadth pressed/bought | corroboration only |

**So:** the full six-piece read exists on **NIFTY for 30 Sep and 1 Oct**; a five-piece read (no reader legs) on NIFTY
22–29 Sep; and on **SENSEX and BANKNIFTY the flow pieces are the index price (warmap, xindex) and the option book
(sides). Their futures tape must never vote.** The framework below is built so that it still works on those two from
levels + OI alone, and says "tape: NIFTY only" where it does.

---

## 1. 1 October as a trap, minute by minute

### 1.1 The setting

30 Sep afternoon: all three fell from the day's high into 14:43 (NIFTY 22809 → 22598, SENSEX 73058 → 72369,
BANKNIFTY 55129 → 54633 close) and bounced into the close [M]. Previous-day levels for 1 Oct [M, chain spot]:

| | PDH | PDL | PDC | 1 Oct first print | gap |
|---|---|---|---|---|---|
| NIFTY | 22809 | 22598 | 22620 | 22566–22584 (09:17) | **−36 to −54** |
| SENSEX | 73058 | 72369 | 72480 | 72388–72418 | **−62** |
| BANKNIFTY | 55129 | 54364 | 54633 | 54830 | **+197 (gap up)** |

SENSEX was 0DTE, NIFTY 5 DTE, BANKNIFTY 26 DTE. The OI baseline is the 09:15 candle, so whoever wrote puts into
30 Sep's 14:43 low and close was already underwater at the open and **invisible to every OI read** (review item 9,
`oi_prev` not built) — the first trap of the day is one the tool cannot see.

### 1.2 Trap 1 — sellers, below PDL (09:17–09:24, released 09:24–10:07)

- **09:17–09:24** opening drive down: NIFTY 22566 → **22514** (81 under PDL 22595), SENSEX 72388 → **72234** (132 under
  PDL 72366), BN 54864 → 54700 [M]. NIFTY futures −73 in 7 min, UX Δ −1,168 (43% of volume), OI +84 lots (noise):
  reader WHO **"rotation, OI flat"** — nobody opened a position on the drive [M]. VPIN fast −19k at 09:20 [M].
- Warmap: SENSEX PDL APPROACH 09:23 → REJECT 09:24 (a reject from below = the break failed at once) [M].
- Marks: 09:25 `trap−@22612 (231)` — sellers trapped at the low [M].
- **Release:** 09:24–09:33 +72 pts on Δ +485 and OI +202 ("rotation") [M]. The weeklies had taken out the previous
  day's low on both exchanges and come straight back: **stops under PDL were the liquidity, and the buyers of them
  opened nothing new.** By the sides read (rev 2, kal ka scale): 09:25 NIFTY/BN **CAPPED ▼** (call writers adding on
  the drive), 09:35 NIFTY+SENSEX **FAKE ▲** weekly 2/2 — the recovery was read as fake by OI; it ran +59 / +216 [M].
  The book was wrong about the bounce because the bounce was the release of a trap the OI could not see (overnight
  inventory).

### 1.3 Trap 2 — buyers, at PDC (loaded 09:36–10:07 and 10:28–10:41, dwelt to 12:00, released 12:04–12:10)

**The walk to the level (09:36–10:07).**
- NIFTY futures +36 in 13 min on Δ +63 (5.6% of volume) then +77 in 7 min on Δ +133 (11%): reader WHO **new_longs**
  then rotation; **lam 582 pts per 1,000 lots** (rank 5): price rose on almost no aggressive buying [M]. CVD UX fell
  from −939 to −1,063 while spot rose 60 pts — **CVD divergence at the first high** [M].
- Put writers wrote the floor into the push: NIFTY PE 22500/22600 **+128k, +178k, +152k, +290k, +343k, +459k, +162k,
  +128k, +96k units per minute 09:58–10:07** (~1.9M in ten minutes), with PE 22500 ltp 96 → 76 against avg 98 (writers
  in profit, confident) [M]. SENSEX 0DTE call writers were squeezed at the PDC break: CE 72500/72400 **−1.49M in one
  minute at 10:02** [M].
- Warmap: NIFTY OPEN 22544 BREAK → RUN → HIT 10:00:16–10:00:58; **PDC 22620 APPROACH 10:01:18 → REJECT 10:03 →
  APPROACH 10:03 → REJECT 10:09: NIFTY never broke PDC** (high 22608 at 10:07, −12). SENSEX PDL HIT 10:00:43 (back
  above), **PDC 72480 BREAK → RUN 10:07:33** (72569). BN ROUND 55000 REJECT ×6 09:33–10:19 [M].
- Tape at the push: NIFTY buy sweeps 11k/14k units at 10:01–10:02, VPIN fast bucket **B 0.72** at 10:01, mark 10:00
  `initiative+@22668 (291)` [M]. Aggressive buyers were there — the induce had takers. Mary was one: SENSEX 72400 CE
  bought 10:00:48, out 10:01:26 (+21) and 10:06:02 (−16) [M, tradebook via `TRADER-REVIEW-2026-10-03.md`].
- xindex X2 at 10:03: **CONFIRMED** high, all three took the 09:49 swing high at 10:01–10:02 [M]. At the first push the
  cross-index read said "real".

**The failure (10:04–10:14) — in order:**
1. **10:04–10:05** call writers at NIFTY 22700/22600 flip from covering (−290k, −289k at 10:01–10:02) to **adding
   (+175k, +146k)**: the lid re-forms while price is still at the high [M].
2. **10:05 bar** marks `absorption−@22700 (123)` and **`trap+@22700 (90)`**: buyers at futures 22700 (= spot ~22605, the
   PDC zone) absorbed and trapped [M]. (Futures carry ~95 pts of October basis; 22700 fut ≈ 22605 spot.)
3. **10:08** SENSEX −73 in one minute (72565 → 72492) [M]: the PDC break lasted 6 minutes.
4. **10:09–10:10** NIFTY sell sweeps 5k/7k, mark `initiative−@22671 (297)`, VPIN fast S 0.30, CE top-2 −348k/−128k and
   PE **+295k** (put writers still defending into the dip) [M].
5. **10:13:51 SENSEX PDC → FAILED** (72435) [M]. Reader leg 10:02–10:28 ▼ −66 pts, Δ −585 (27%), OI **+828 lots → new_shorts**:
   fresh shorts entered on the failure [M].

**First to turn at the failure:** the call writers re-adding (10:04) and the absorption/trap marks at the level (10:05
bar), three to four minutes before the price failure (10:08) and nine before the warmap FAILED stamp (10:13:51).

**The second push (10:28–10:41) — the divergence.**
- NIFTY +62 pts in 9 min on **Δ −188** (share −0.28): reader WHO **new_longs, absorbed = True** — price rose while net
  flow was selling; depth sweeps 10:30 B21/S25, 10:35 B9/S14 (more sell than buy sweeps on a rise) [M]. GC and UX
  disagree on the 10:30 bar (+200 vs −106): SPLIT [M].
- Put writers covered at 10:31–10:32 (−463k, −162k) **with ltp 82 < avg 95: profit-taking**, then wrote **+1.6M at
  22500/22600 in eight minutes 10:34–10:41** — the trap reloaded at the second high; PE 22600 peaked at **10:41**
  (§1d, the Board's "puts broke at 10:41") [M].
- BN ran to **55079 at 10:36, 57 pts under its PDH 55136**, PDH APPROACH/REJECT ×5 10:32–10:38, ROUND 55000 BREAK →
  RUN 10:36:23 → **FAILED 10:48:17** [M]. BN's sides read fired **REAL ▲** at 10:35 (CE covering ×4.2, 7/9) — the
  26-DTE monthly book squeezed on the breakout; −174 followed [M].
- **xindex X2 at 10:36 and 10:42: BARABAR — BANKNIFTY TOOK a new high (55350 > 55250), NIFTY EQUAL (22697.9 vs 22702.4,
  −4.5), SENSEX did not** [M]. One book broke out alone; the heavyweights did not confirm. Mark 10:35
  `exhaustion−@22698` [M].
- Reader leg **10:37–11:25 ▼ −75.5 pts, 48 min, Δ −1,222, OI +752 → new_shorts, lam 61.8, rank 1** (the best result
  per effort of the day so far: price fell easily) [M].

**The dwell (10:45–12:00): the trap fully loaded.**
- NIFTY 22559–22572 for 70 minutes, bracketed by PDL 22595 above and OPEN 22544 below; warmap flickered
  APPROACH/REJECT between the two dozens of times [M]. SENSEX PDC DWELL 10:43 → REJECT 10:48, then 72400–72420 under
  PDC. BN ROUND 55000 DWELL 11:45 → REJECT 11:54 [M].
- Effort without result: UX CVD −2,188 (10:45) → −2,601 (12:00) with spot flat; 10:50 bar 1,029 lots, five
  `absorption−` marks at 22670–22680 [M]. Futures OI **rose every bar** (+79 … +194 lots): both sides opening — shorts
  pressing, longs absorbing [M]. VPIN slow pct 0.42 → 0.20: calm, two-sided [M].
- The books: call writers added in **every** slot 10:50–11:25 on all three (the grind the burst measure cannot see);
  calls written today passed puts written today at 11:00 (ce_chg 20.8M vs pe_chg 18.0M) [M]. The lid above, the floor
  below, the futures two-sided — nobody committed. **This is the trap being set, in numbers.**
- The last push 11:54–12:00: +39 pts on Δ +227 (77% of volume, "rotation"), buy sweeps 12k, VPIN fast +13k, mark 11:55
  `initiative+@22640`, call writers covering a little (−91k, −84k at 11:59–12:00) [M]. **The third push was the one
  that got aggressive buying — and the one that was sold.** Before it, 11:50–12:00 bids were **pulled** (senses `pulled
  buy` 13k, 10k) — the book thinned under price before the drop [M].

**The release (12:00–12:11) — which piece turned first [M, 1-minute grid; option OI reaches the feed 1–3 min after
the trade, so items 1 and 3 happened in trade time about 12:01–12:03]:**

| minute | piece | what it showed |
|---|---|---|
| 12:02–12:04 | call writers at 22700/22600 | −157k (12:02) then **+121k, +130k, +142k** (12:04–12:06): the lid turned from squeezed to selling the dip |
| **12:03:39** | **SENSEX PDL 72366 → BREAK → RUN** (warmap) | the first level to go, 6 minutes before NIFTY's |
| **12:04** | **NIFTY PE 22500 ltp crosses avg (92.8 / 92.8) and the first covering minute (−89k)** | the day's put writers go underwater at their heaviest strike; SENSEX PE 72000 crosses at 12:06 |
| 12:05 bar | tape | `initiative−@22636 (383)`, UX Δ −492, VPIN fast −31k one-sided |
| 12:07 | VPIN fast buckets **0.91, 1.00** (three buckets closed in one minute) | the futures tape went one-sided; PE −305k |
| 12:09 | call writers +195k on the bounce | the bounce is sold by the lid |
| **12:10** | **PE −1,094k in one minute** NIFTY; sell sweeps 14k; climax bar 1,721 lots; **NIFTY OPEN 22544 BREAK → RUN → HIT 12:10:12–12:10:23**; the 5-min sides read fires ×9.0 on 9/9, forced 2/2, weekly 2/2 | the capitulation and the morning longs' stops |
| 12:09–12:11 | SENSEX PE −983k, **−1,565k**; PDL HIT 12:10:19 | the 0DTE floor gives way |
| 12:12 | xindex: NIFTY TOOK the low (2.0 rulers), "saath mein low · 12:11" | all three at a new low together |
| 12:19–12:27 | VPIN fast pct **≥ 0.80** for the first time today | toxicity confirms, 15 minutes late |
| 12:24–12:26 | xindex X2 CONFIRMED low, "NIFTY 2 min pehle"; ROUND 22500 BREAK | the leg is confirmed across books |
| 12:45 | the 5,062-lot bar, Δ −1,266 / −2,583, **fut OI +2,073 lots**; VPIN 0.91–0.99 | size entered SHORT on the slam: new positioning, not covering |

The reader's leg 12:13–12:59: **▼ −244 pts, 46 min, Δ −4,330, OI +6,101 lots → new_shorts, lam 56.4, rank 1** [M].
Puts written today fell from 18.0M (12:05) to 4.6M (12:50): **75% of the day's put build was covered in 45 minutes**
while call writers added 14M on the way down (ce_chg 24.1M → 38.5M) — the next trap [M].

**First to turn, stated plainly:** the SENSEX PDL break (12:03:39) and the NIFTY put writers going underwater (12:04)
are the earliest readable tells, within the same 60–90 seconds and before any tape confirmation; the call writers'
flip to adding (12:04) is the same moment from the other side of the book. The futures tape confirmed one-sidedness
at 12:07 (+3 min), the 5-minute POWER read at the 12:10 mark (+6 min), VPIN percentile at 12:19 (+15 min),
cross-index confirmation at 12:24 (+20 min). **Levels and the book led; the tape confirmed; VPIN and xindex arrived
when the leg was already 100 points old.**

### 1.4 Trap 3 — sellers, below the previous day's low again (13:43–14:07, released 14:25–15:15)

- BN **PDL 54174 BREAK → RUN 14:02:37 → FAILED 14:07:40** [M]; NIFTY ROUND 22200 REJECT 14:05, SENSEX ROUND 71500 HIT
  13:58 / REJECT 14:08 [M]. Sides read at the low: NIFTY 14:00 REAL ▼ (the rev-1 false row), BN 14:05 SQUEEZE ▼.
- The put fuel was gone (115% of the first-sign build given back by 14:00, critique §F) and the call writers had
  loaded 14M on the way down: the trapped side had switched.
- Release: reader 14:28–14:37 **▲ +101 pts, Δ +2,027 (38%), OI +2,516 → new_longs, lam 50, rank 2**; 14:30 bar fut OI
  +1,711 lots, sweeps B63/S41, VPIN fast +64k, marks 14:25 and 14:30 `initiative+` [M]; sides 14:35 NIFTY CE covering
  ×6.2 on 9/9 (REAL ▲), SENSEX CE ×3.0 + PE ×3.6 (REAL ▲), weekly 2/2 [M]; xindex 14:36 all three took the high,
  CONFIRMED [M]. 15:02–15:22 ▲ +94 new_longs Δ +2,289 [M].

**Three traps in one day, each at a previous-day level (PDL → PDC → PDL again), each released toward the next
reaction point. The gap-down open "induced buyers and sellers everybody" exactly as she said: sellers at 09:24
under PDL, buyers at 10:00–10:37 at PDC/PDH, sellers again at 14:02 under PDL.**

---

## 2. What order flow adds to the OI sides read (first principles, with the rows)

**2.1 Writers covering + aggressive futures flow the same way = forced, and it travels.** 1 Oct 12:07–12:10 (PE
−305k … −1,094k/min with VPIN buckets 0.91/1.00, sell sweeps 14k, climax 1,721 lots, initiative− mark); 24 Sep
13:30–13:40 (PE ×8.7/×14.1/×8.4 with UX −919, climax−, initiative−); 30 Sep 14:20–14:35 (PE ×5.0 with initiative− ×3,
VPIN ≥ 0.9); 29 Sep 11:10–11:15 (CE ×8.9/×8.8/×12.9 with initiative+ +1,671 lots) [M]. The tape being one-sided in the
covering's direction is the confirmation that the covering is forced *now*, not squared.

**2.2 Then WHO decides how far it goes.** On 1 Oct the slam leg carried **OI +6,101 lots with Δ −4,330 (new shorts)**
and ran 300 points through four levels. On 29 Sep the 11:10 release carried **OI −470 with Δ +1,433 (short covering)**:
it ran to the next level (OPEN 22732, BREAK 12:07) and **FAILED at 12:20** [M]. On 24 Sep the release was mostly
liquidation (UX −2,500 over 20 min with OI roughly flat) and stopped at the weekly low (PWL HIT 13:58, then +28) [M].
**Release with new positioning travels; release that is only the trapped side covering reaches the next reaction
point and stops.** That is what the reader's WHO adds and the sides read cannot know.

**2.3 Writers covering into a tape that is not one-sided = voluntary.** 1 Oct 10:31–10:32: PE −463k/−162k on an
up-move, ltp 82 < avg 95, reader "new_longs absorbed" with Δ −188 — profit-taking, no release followed. 23 Sep
15:00–15:15: PE ×3–4 with 0/9 above avg and Δ −90/−75/−67 — squaring. 29 Sep 12:35: PE ×4–7 with 4/9 above avg and UX
**+234/+345** (buying) — expiry squaring after a bounce [M]. The premium (`ltp > avg`, now the forced chip) and the
tape agree on every one of these rows; either alone would do, both together are the honest read.

**2.4 Effort without result at the level says WHERE the trap is being set, not which way it springs.** 24 Sep: UX CVD
−7,649 by 12:00 with price flat at 23220–23260 for three hours; released **down** at 13:26. 29 Sep: CVD −3,758 by
10:00 with price flat at 22600 for 80 minutes; released **up** at 11:10. 1 Oct: CVD −350 more over the 10:45–12:00
dwell with price flat; released **down** [M]. Absorbed selling went both ways. What separated them was the **book**: on
29 Sep futures OI fell all morning (−751, −956, −1,171, −1,559 lots: forced long liquidation, which ends) and the call
writers were the loaded side (CE ×9–13 at the release); on 1 Oct futures OI rose through the dwell (both sides
opening) and the put writers had loaded 1.6M at 22500/22600 ten minutes before the top, in profit until 12:04.
**Flow finds the dwell (where); the sides read finds the fuel (who); `ltp > avg` finds the moment (when).** That is
how the pieces connect.

**2.5 CVD divergence is readable on NIFTY only, and only at the pushes.** 1 Oct: first push +60 pts with CVD falling
(−939 → −1,063); second push +62 pts on Δ −188; the third push was bought (Δ +227, 77%) and slammed [M]. The breakout
that finally gets aggressive buying is the one that is sold — the induce needs takers. Across indices, **CVD cannot be
compared**: SENSEX futures had zero sweeps and 4 lots a minute; BN's lam runs 500–3,000 pts per 1,000 lots (a few lots
move it). The cross-index read that *is* available on all three is **price extremes** (xindex X2): at 10:36 BN made a
new high alone — the induce's signature; at 12:11/12:24 all three took the low — the release confirmed [M].

**2.6 VPIN confirms, late.** First pct ≥ 0.80 on 1 Oct at 12:19 (release 12:04–12:10); 24 Sep 13:44 (break 13:26);
30 Sep 10:33 (fall from 10:30); 29 Sep 11:10–11:26 (with the release) [M]. It is direction-blind, NIFTY-only, and it
**also fired at the induce** (slow pct 0.78 at 10:07 on 1 Oct; fast B 0.72 at 10:01): toxic buying at a level break
can be the trap or the spring. It cannot tell; the book side can. Use: "hold, the flow is one-sided", never "enter".

**2.7 Big prints: one in four was a clean read.** 1 Oct 12:45 (5,062 lots, OI +2,073, both tapes agree in sign): clean,
new shorts. 1 Oct 13:40: GC +1,311 vs UX −2,991 on the same 4,073-lot bar — SPLIT, unreadable. 30 Sep 12:50: −3,007
with OI +2,964 then −2,936 at 13:00 — a publication or spread artefact. 29 Sep 10:05: +4,483, the spread leg the reader
debate dissected [M]. A block is evidence only when futures OI moves with it the same minute and the two tapes agree.

**2.8 Pulled quotes before the move (unused today).** Bids pulled 13k/10k at 11:50–12:00 before the 12:04 slam; asks
pulled 13k at 10:30 before the 10:31–10:36 push [M] (`sweep.py` `pulled`, `pools.py` VACUUM). The book thins on the
side price is about to travel toward. Rows only; worth logging as a field, not a vote.

**What a trader should demand as "more power", in order:** (1) the level named; (2) the dwell with the loaded side
named from the top-2 fronts; (3) the break with aggressive flow **and** a cross-index non-confirmation; (4) the failure
(FAILED stamp, the loaded side's front STALLED, a trap/absorption mark at the level); (5) the release: **fuel side
underwater + covering at POWER + tape one-sided the same way (NIFTY) + the other side adding**; (6) WHO on the leg
(new positions or covering) for how far. **Noise:** any single bar's delta sign (the tapes disagree on 31% of bars);
SENSEX and BN futures delta entirely; VPIN at a level break without the book; a block without OI and tape agreement;
the 93 marks a day as marks; the cumulative sentiment word; any single 5-minute slot alone.

---

## 3. The trap sequence as a checklist, and what measures each step

| step | what she sees | measured today by | missing |
|---|---|---|---|
| **1 LEVEL** · pahuncha | `PDC 22620 · 10:01` (or PDH/PDL/OPEN/PWH/PWL/major round), distance, which side of it | `levels.py` + `warmap.py` sequence machine: APPROACH stamps for every level, all three indices, every day [M]. 1,072 transitions on 1 Oct, **no screen reads them** | A per-level **summary** (first approach, minutes held, break, failed) instead of a 10-second transition stream |
| **2 DWELL** · ruka | `70 min · PE 22500/22600 +1.6M likhe · fut OI dono taraf · tape patla` | `dwell.py` DwellWatch (band, OI per side near the level, buyers paying up) — built, kill-clocked, no screen; the sides read's top-2 (who loaded); reader leg `absorbed` and lam rank; frame `pressed/bought` | The **join**: dwell minutes + which top-2 front loaded + futures OI direction through the dwell + CVD-vs-price (effort without result). `oi_prev` (review item 9) so overnight inventory counts |
| **3 INDUCE** · phansaya | `SENSEX PDC toota 10:07 · BN naya high akela 10:36 · NIFTY PDC nahi toota · buy sweeps 14k` | warmap BREAK → RUN; xindex X2 TOOK/EQUAL/FAILED per index and X3 who-first (shadow, off by default); marks `initiative`, sweeps, VPIN fast imbalance (NIFTY) | Joining "BREAK at a named level" with "X2 not confirmed by the other weekly book" — the two signatures of 1 Oct 10:07 and 10:36 sit in two files nobody reads together |
| **4 FAILURE** · fail hua | `SENSEX PDC FAILED 10:13 · CE 22700 phir likh rahe 10:04 · trap+ @22700 · PE 22600 ruka 10:41` | warmap FAILED; §1d STALLED/UNWINDING on the loaded side (`fronts.py`); marks `trap`/`absorption` at the level; reader `absorbed=True` on the push | CVD divergence at the extreme (reader design R7: **not built**); FAILED is logged but never shown |
| **5 RELEASE** · chhoota | `12:04 PE writers underwater · 12:10 kaat ×9 9/9 forced 2/2 · tape ek-taraf (VPIN 1.00, sweeps S14k) · CE likh rahe · NIFTY+SENSEX 2/2` | sides-2 POWER + forced chip (built); VPIN fast buckets, sweeps, initiative mark (NIFTY) in the same slot; the other side adding (sides-2 back side) | A **`tape_with` field on the POWER slot** (NIFTY only: max fast-bucket imbalance in the slot with sign, UX Δ sign, net sweeps), "tape: check nahi" on SENSEX/BN |
| **6 TARGET** · agla | `OPEN 22544 toota 12:10 → 22500 (12:43) → 22400 (12:53) → 22300 (13:58) · naye short +6.1k lots: chalega` | warmap next level and RUN → HIT stamps; `hunt.py` runways (fuel per point, [I], ranking unproven); reader WHO on the forming leg (new positions vs covering) | Showing WHO beside the target: "release with new shorts" vs "release = covering only, agle level pe ruk sakta hai" (29 Sep vs 1 Oct) |

Not measured anywhere, and never will be from this data: where the stops are (`hunt.stop_zone` names it [I]); who the
operator is (inferred from WHO at size on the release); the aggressor on SENSEX and BN futures.

---

## 4. The same story on the other sessions (rows, no rates)

| session | level reached | dwell / load | induce | failure | release | target | held? |
|---|---|---|---|---|---|---|---|
| **30 Sep** (Wed; NIFTY fresh weekly, SENSEX 1 DTE, BN fresh monthly) trap A | NIFTY PDC 22716 BREAK 10:06; **PDH 22753 DWELL 10:19 → BREAK 10:21**; SENSEX PDH BREAK 09:59 → HIT 10:16 [M] | short: 10 min at PDH | breakout above PDH on both weeklies | **NIFTY PDH FAILED 10:32, PDC FAILED 10:44; SENSEX PDH FAILED 11:28** [M] | 10:30–10:55 initiative− ×3, VPIN ≥ 0.9 10:33–11:29, UX CVD −1,206 by 10:55 [M] | fall to 22672 (11:15) | yes: longs trapped above PDH |
| 30 Sep trap B | NIFTY **PDC DWELL 10:55, 11:08, 11:51** (an hour at PDC) [M] | shorts loaded below PDC after trap A | PDC BREAK 11:56 → HIT 12:00; PDH BREAK 12:35 → HIT 12:46 | — | sides 3/3 ▲ 12:25 (CE ×3.6/×8.5/×4.7), initiative+ 12:20/12:35/12:45, +774 at 12:45 [M] | day high 22808 at 12:48 | yes: the morning shorts were the fuel; **12:50 3/3 ▲ continuation = the top** (exhaustion, critique §6) |
| 30 Sep trap C | 73000 FAILED 12:52 SENSEX; the 12:50 block (−3,007, OI +2,964 then −2,936: artefact) | — | the 12:25–12:48 breakout longs | PDH BREAK/HIT 13:44–13:45 (back below), PDC 14:21–14:24, OPEN 14:28–14:39 [M] | sides 3/3 ▼ 14:25 (PE ×5.0/×3.4/×4.1 on 9/9), initiative− 14:20/14:25/14:35, VPIN ≥ 0.9 14:20–14:40 [M] | low 22601 at 14:42 (PDL 22574 untouched); **SENSEX OPEN FAILED 14:45** = sellers trapped below OPEN → bounce into close | yes, then the mirror trap at the low |
| **29 Sep** (Tue; NIFTY+BN 0DTE; gap −67/−158/−240) | **PDL broken at the open** on all three (NIFTY 22574 low, 191 under PDL); ROUND 22600 DWELL 09:48 → FAILED 10:43 → DWELL 10:50, 11:06 [M] | 80 min at 22600; UX CVD −3,758 by 10:00 with price flat; **fut OI −751, −956, −1,171, −1,559: long liquidation** (forced sellers) [M] | the gap and the drive: sellers in below PDL | the liquidation ended (OI flattened 10:15–11:05) | **11:10 initiative+ +1,671 lots; sides 3/3 ▲ 11:15 (CE ×8.9/×8.8/×12.9); WHO short covering (OI −470)** [M] | OPEN 22732 BREAK 12:07 → **FAILED 12:20** [M]: covering-only release reached the next level and stopped | yes; 12:35 3/3 ▼ put covering = expiry squaring after the 12:10–12:30 fall, 4/9 underwater, tape buying: **not a release** |
| **24 Sep** (Thu; SENSEX 0DTE; gap −210/−826/−603) | never near PDC (−178); **OPEN 23222 DWELL 10:00 → BREAK 10:22 → FAILED 10:37 → DWELL 10:49, 11:30**; ROUND 23200 DWELL 11:55 → FAILED 12:02 → DWELL 12:17 [M] | **three hours** at OPEN ± 25; UX CVD −4,502 by 10:00, −7,649 by 12:00 with price flat (sellers absorbed); puts written under it all morning [M] | the 10:22 and 11:31 pokes above OPEN | 10:37 FAILED | **ROUND 23200 HIT 13:26 and SENSEX PWL 73981 BREAK 13:26** → sides 3/3 ▼ **13:30** (PE ×8.7/×14.1/×8.4 on 9/9) → initiative− 13:35, climax− 13:40, UX −919 → VPIN ≥ 0.9 13:44 [M]. Order: level 13:26, book 13:30, tape 13:35–13:40, VPIN 13:44 | NIFTY PWL 23116 BREAK 13:46 → HIT 13:58; low 23049 at 14:23; 14:00 REAL/SQUEEZE ▼ at the low → +28/+5 | yes: the weekly low was the target; the release was liquidation (OI flat), so it stopped there |
| **23 Sep** (Wed; range; gap +44/+145/+179) | **all three stopped under PDH: NIFTY 23463 vs 23467 (−5) at 12:19, SENSEX −64, BN −43** [M]; ROUND 23400 HIT 09:54 (below) → DWELL 10:32 → HIT 11:47 (reclaimed) | three hours under PDH with steady put writing (the sides' grind); UX CVD −2,600 by the close with price flat/up (sellers absorbed all day) | **none: no level broke** | — | **none** (15:00–15:15 3/3 ▼ put covering: 0/9 underwater, Δ flat = squaring) | — | **no trap sprung.** The checklist would have read "PDH pahuncha · ruka · koi break nahi · koi release nahi": stand aside |

Where it held: every trend leg in these five sessions began at a previous-day or weekly level that had been reached,
held, broken or failed, with the loaded side's writers underwater at the release. Where the market did not trap:
23 Sep, a level reached and never broken. Where the read is weakest: expiry squaring (29 Sep 12:35) and the open
before `oi_prev` exists (1 Oct 09:35 FAKE on the release of an invisible overnight trap).

---

## 5. On the Board: three lines, and what must be pre-registered

```
TRAP   PDC 22620 pahuncha 10:01 · toota nahi (SENSEX PDC toota 10:07 · FAILED 10:13 · BN naya high akela 10:36) · ruka 70 min · PE 22500/22600 +1.6M likhe · ruka 10:41
CHHOOTA ▼ 12:04 PE writers underwater · 12:10 kaat ×9 · 9/9 · forced 2/2 · NIFTY+SENSEX 2/2 · tape ek-taraf (NIFTY: VPIN 1.00 · sweeps S14k) · CE likh rahe ×2.8
AGLA   OPEN 22544 toota 12:10 → 22500 → 22400 → PWL · naye short +6.1k lots (chalega) · fuel 60% gaya · 40 min
```

Line 1 is the setup (level, induce, failure, dwell, who loaded); line 2 the release (the sides-2 chip plus the tape
witness); line 3 the travel (next levels from the warmap sequence, WHO from the reader, the exhaustion facts). Before
a release exists, line 2 reads `koi release nahi · PE writers profit mein (ltp < avg)`; when the level has not broken,
line 1 ends `koi break nahi`. On SENSEX and BN the tape clause reads `tape: check nahi (patla)`. After 15:15,
`15:15 se check nahi`.

**Pre-register before any of it logs forward (it changes what the log records):**
1. The six trap states and what closes each: REACHED (warmap APPROACH at a named level), DWELL (`dwell.py`'s band and
   `DWELL_MIN_S` = 300 s, as already declared), INDUCED (BREAK → RUN at that level), FAILED (warmap FAILED), RELEASED
   (sides-2 POWER with forced ≥ 1/2 in the direction away from the loaded side), TRAVELLING (RUN → HIT at the next
   level). Levels: PDH/PDL/PDC/OPEN/PWH/PWL and major rounds only, as `levels.py` already lists them.
2. **Which side is "loaded"**: the top-2 front on the side that added the most at the nine during the dwell (sides-2
   fields already logged); one rule, no number.
3. The **`tape_with` field** on every POWER slot, NIFTY only: max fast VPIN bucket imbalance in the slot with its sign,
   UX Δ sign and lots, net swept units; `null` with reason on SENSEX/BN. No threshold; a witness.
4. The **cross-index extremes** field at INDUCED: xindex X2 per-index status (TOOK/EQUAL/FAILED) and X3 who-first, as
   already computed in shadow.
5. **WHO on the release leg**: the reader's class and OI delta for the leg containing the POWER slot (new positions vs
   covering), logged, shown as `chalega` / `agle level tak`.
6. The `pulled` asymmetry in the five minutes before a POWER slot, logged only.
7. **Kill conditions**, bars written by Mary before Monday: (K-A) RELEASED rows (line 2 shown) listed against the
   non-RELEASED slots' signed f30, as in the critique's K1; (K-B) INDUCED+FAILED rows with no RELEASED within 60 min,
   counted — if most induces never release, line 1 is description not anticipation and says so; (K-C) RELEASED rows
   where `tape_with` disagreed in sign with the fuel direction, listed with f30 — if they end the same as agreeing
   rows, the tape witness comes off line 2; (K-D) releases classed covering-only vs new-positioning, each with
   "reached the next level and reversed" — if indistinguishable, line 3 drops the WHO clause.

---

## 6. The morning scale (coordinator's question, 2026-10-04): a post-hoc change, said plainly

We have seen these rows. Rev sides-2 sizes slots up to 10:30 against the previous session's 10:30–15:00 median ("kal
ka scale", my optional improvement 7), and the frozen run shows 146 of 294 PUSHTI at or before 10:30. Measured on
every session with a previous day on disk, 09:20–10:30 slots on the nine, 723 index-slots [M]:

| basis for the first hour | index-slots with a side ≥ 3× | median ratio | p75 | p90 |
|---|---|---|---|---|
| previous session 10:30–15:00 median (sides-2 as built) | **472 of 723** | 4.87 | 9.2 | 15.5 |
| **previous session 09:20–10:30 median (same window)** | **254 of 723** | 2.10 | 4.0 | 6.9 |
| turnover |ΔOI9|/OI9 against the previous session's midday turnover | 486 of 723 | 4.32 | 7.5 | 12.4 |

The opening is ~2× midday on almost every session (NIFTY opening/midday median |ΔPE9| ratio per day: 1.2–15.3,
typically 1.8–2.0; BN 0.7–4.3; SENSEX 1.0–5.9) [M], so a midday scale makes two of every three morning slots
"POWER". **Turnover is worse, not better**: near-ATM OI is small at the open (and tiny on fresh-series mornings), so the
denominator inflates it. The coordinator's like-with-like is right: **the first hour is sized against the previous
session's same window.** It halves the morning rows and brings the median to about 2×; it does not make the
morning quiet — a third of morning slots still clear 3× because the opening half-hour is itself a burst regime. On
1 Oct it keeps 09:25 (NIFTY CE 3.9, SENSEX CE 10.8/PE 4.1: call writers selling the gap-down drive) and SENSEX 09:35
(CE 4.4/PE 4.5), and drops NIFTY 09:35 (PE 2.6) — the FAKE ▲ becomes weekly 1/2, not 2/2 [M].

**Recommendation:** same-window basis; **show the morning from 09:20** (her anchor is 09:25, and trap 1 on 1 Oct
lived there), tagged `subah · kal ki subah ka scale`; **CAN'T CHECK** when the previous session is missing or was that
index's expiry day (a 0DTE morning is not a like for a fresh-series morning); and until the forward log says
otherwise the morning POWER chip is a **witness, not a vote** in the weekly 2/2 count (pre-register this). The forward
log is the judge; this section is the record that the basis was chosen after the rows were seen.
