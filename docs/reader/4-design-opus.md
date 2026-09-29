# 4. Design B (Opus): the order-flow reader

**Role:** Designer B in the blind design debate. Design only: no code was edited, nothing was written under `data/`, and the server was not touched.
**Written:** 2026-09-29, after the close.
**Inputs:** `1-research.md` (rubric R1–R18, gates H1–H8, disputes D1–D5), `2-data-audit.md`, and `3-current-reader-audit.md`.

**Grounding:**
- Every 29 Sep number below comes from a read-only replay in my scratch folder: `...\scratchpad\designB\` (`book1m.py`, `reader.py`, `walk.py`, `window.py`, `asof.py`, `survey.py`, `d1.py`, `blocks.py`, `ladder_q.py`).
- The replay reads the recorded files and runs as-of: each read uses only data stamped before its time.
- It is a description check, not a backtest. No outcome is scored anywhere in this document.

**Tags:**
- **[M]** measured: price, volume, OI, timestamps.
- **[I]** inferred: any buy/sell side, delta, CVD, OFI, and every "who" label.
- **(h)** a hand-picked threshold. Each one is pre-registered in §7.4 for Mary to sign.

---

## 0. The design in twelve lines

1. **The unit of reading is the leg, not the bar.**
   - A leg ends when price reverses by δ = 3 × B from its extreme.
   - B is fold's own unit, the median 1-minute range, so the reader and the hold engine share one ruler.
   - Legs group into auctions: TREND, PAUSE, RANGE (balance) and BREAKOUT.
2. **Every leg carries four facts:**
   - points [M];
   - volume [M];
   - net delta on two tapes: GoCharting's vendor side, and an Upstox quote rule recomputed from the book with the correct tick [I];
   - Sep OI change [M].
3. **Effort vs result is a number:** points per 1,000 lots of net delta. It is compared with the last leg the same way, and ranked only against today's completed legs, with n shown.
4. **The "who" read joins delta, OI and price** into one of the classic states:
   - new longs, new shorts, short covering, long liquidation, or rotation;
   - plus **ABSORBED** when the aggressor pushes hard and gets little.
5. **Roll and expiry mode is automatic, from the instrument calendar.**
   - In the last five sessions before expiry, falling near-month OI is read as "closing or rolling", never as direction.
   - Oct is captured so that "rolled" can be told from "closed".
6. **Absorption is a state at a level, not a signal.** It needs a location, three or more visits, net aggression into the level, and no acceptance beyond it.
7. **Blocks are screened.** One print can never become a leg's story again.
8. **CVD divergence is checked only at confirmed swing extremes**, on both tapes.
9. **FEED HEALTH is the first line on every face.** When GoCharting stops, every GoCharting read goes to CAN'T CHECK with the reason and the fix. Stale marks are never shown as live.
10. **Mary's P/A/E/C marks and the zone machine stay.**
    - P/A/E/C: detector geometry frozen at a fixed row, the record kept in TapeMap, and three targeted fixes.
    - The zone machine: untouched.
11. **The reader feeds fold's FLOW row** with WITH / PULLBACK / AGAINST / SPLIT / CAN'T CHECK. It never replaces HOLD / PAST GIVE-UP / FOLD.
12. **On 29 Sep it reads the afternoon as she did:**
    - Read: "range 22633–22723 since 12:33; buyers Δ+6.1k (GC) / Δ+8.4k (UX) for +81 pts; Sep OI −11.2k (−9.3%), 9.9k of it after 14:30; short covering or roll, absorbed under 22706–22723".
    - It also says, in words, that Oct was not recorded.

---

## 1. My sides on the five disputes

### D1. Order flow = traded delta, or book imbalance? → **Delta for effort, on two tapes; OFI only as the book's answer inside absorption.**

**What I measured.** 6 days, 399 five-minute bars. Block bars and GoCharting-short bars are excluded. Each figure is the correlation with the same bar's price change (`d1.py`).

| Measure | Pooled | Range by day |
|---|---|---|
| GoCharting delta [I] | 0.46 | 0.21–0.64 |
| Upstox frame quote-rule delta [I] | 0.40 | 0.18–0.58 |
| L1 order-flow imbalance (OFI) from the 1 Hz book [I] | 0.47 | 0.42–0.61 |

**Why delta stays the effort measure:**
- OFI describes price change no better than delta, pooled.
- Part of OFI's fit is built in: its formula counts queue size whenever the touch moves.
- So OFI cannot be "effort". It is partly the result.

**What OFI adds that delta cannot:**
- It shows the passive side.
- On 29 Sep, 12:33–15:00, both delta tapes were net buying: GC Δ+2,965, UX Δ+5,227.
- In the same window OFI was −1,986: resting offers refilled and bids were pulled.
- That is absorption **seen in the book**, not only inferred from a low points-per-lot.

**Where OFI is used:** only as evidence inside the absorption read (R5). It is never a standalone read, and never a mark.

**The second tape:**
- It is a plain frame quote rule, computed on the recorded book rows with the rupee tick: print at or above the prior ask is a buy, at or below the prior bid is a sell, otherwise compared with the mid.
- It is **not** the recorded `ux` ladder. That ladder carries the paise-as-rupees tick defect (`2-data-audit.md` §3f).
- With the correct rule the two tapes agree far more. Example: 11:18–12:01, GC Δ+1,839 and UX Δ+1,641. The recorded ux said −389 for 11:35–12:05.

### D2. Absorption: a reversal signal, or ordinary liquidity? → **A state of efficiency at a location. Never a reversal claim.**

- **Why:**
  - Split orders make one-sided, low-impact flow the normal state [S22][S23].
  - Absorption alone is neutral [S39].
- **What the reader says:** "absorbed here", with the level, the side, the quantity and the count of visits.
- **What it never says:** "reversal".
- **Follow-through is a separate, later event.** A leg away from the level with efficient opposite aggression is required. It is written as its own sentence.
- Her bar-level **A** marks stay as her eyes on the footprint. They are evidence under this read, not the read.

### D3. Is the OI table directional on expiry and roll days? → **No, in the roll window. Read open-vs-close for the expiring month; read direction from combined OI and the next month.**

**Evidence** (Sep NIFTY OI [M], end of each session):

| Date | OI (lots) | Change |
|---|---|---|
| 22 Sep | 261.7k | |
| 25 Sep | 206.4k | |
| 28 Sep | 159.6k | −11.1% intraday |
| 29 Sep open | 135.3k | −24.3k overnight |
| 29 Sep close | 110.0k | −18.9% intraday |

The roll dominates the last four sessions.

**The rule:**
- **Roll window** = the last 5 sessions to the front expiry, inclusive, taken from the instrument dump. It is never computed from a weekday.
- Inside the window, a fall in near-month OI names "covering **or roll**" or "liquidation **or roll**".
- The "or roll" goes only when the next month is captured and resolves it:
  - Oct OI up by at least half the Sep fall, with Oct delta negative → **ROLLED**;
  - Oct OI flat (within 3σ√n) → **CLOSED**.
- **Not switched off.** `grounds.py`'s 7-day blind is replaced, because a blind throws away the one thing that is still true: the aggressive side were closing.

### D4. VPIN: early warning, or artefact? → **A gauge. It stays her fourth factor because she named it. Unchanged.**

- fold's VPIN row stays as it is: 10 fast buckets, today's percentile, mute for 10 buckets.
- The reader never uses VPIN for direction, and VPIN never flips a reader state.
- **Caption on every face:** "ek taraf ka flow / volume — disha nahi" (one-sidedness per unit of volume, not direction).
- On expiry afternoons the caption adds: "expiry unwind inflates this".
- No new bucket size, no cross-day reference. The earlier project rejected cross-day VPIN, and I agree.

### D5. Calibration and clock → **Unit: the leg. Ranks: today's completed legs, with n and an explicit warm-up. Scale units: fold's rule. No cross-day ranks, no time-of-day profile.**

- **δ = K × B(t), K = 3 (h).**
  - B(t) is fold's `B_at`: the median 1-minute range of today's completed minutes once at least 5 exist, and the prior-5-session median before that.
  - So the leg cut works from 09:15. It is never blind.
- **Ranks** ("low efficiency", "biggest effort") compare only against today's **completed** legs where that tape named an aggressor.
  - Mute until n ≥ 3, and it says so: "garam ho raha 2/3".
  - This avoids the flow-rank bug, because a forming leg is never ranked against itself.
- **The comparison available earliest** is pairwise: "vs the last leg the same way". It needs only one prior leg in that direction.
- **Why not cross-day or time-of-day:**
  - Lambda scales with depth [S17], and expiry days are their own regime (internal).
  - There is not enough same-contract, non-expiry history to build a matched profile honestly.
- **Fixed ratios** (shares, K, visit counts) are (h) and pre-registered. **No rule contains a lot count.** Sizes are multiples of today's own medians.

**Sensitivity of K** (not a tuning for edge; checking that the structure is stable):

| Day | K = 2.5 | K = 3 | K = 3.5 |
|---|---|---|---|
| 29 Sep legs | 31 | 21 | 17 |
| 29 Sep auction log entries | 14 | 8 | 8 |
| 28 Sep auction log entries | 6 | 4 | 4 |

- At K = 3 and K = 3.5 the named structure is identical on 29 and 28 Sep: base, breakout, trend break, range, with times within 20 minutes.
- At K = 2.5 the 11:11–12:27 grind splits into sub-ranges.
- Across six NIFTY days at K = 3, the median leg lasts 11–31 minutes, with 8–21 legs per day.

---

## 2. The reads

**Common definitions:**
- **Minute series.**
  - One row per minute: open/high/low/close, volume [M], OI [M], UX Δ [I], L1 OFI [I].
  - Built live from the Upstox book, persisted write-once to `data/reader/min_<idx>_<day>.jsonl`.
  - Minutes missing because the server was down are filled from `upstox_rest.intraday`. Those rows are tagged `rest` and carry price, volume and OI only, with no side.
  - The high and low inside a minute are ordered by their ltp timestamps. For `rest` minutes the open/close rule applies: close ≥ open means low first.
- **GC bar.** The extension's posted 5-minute bar. Tagged `short` when its volume is below 97% of Upstox volume for the same bin and the gap exceeds 10 lots (the audit's threshold).
- **Share** = net Δ ÷ volume, per tape.
  - A tape **names an aggressor** when |share| ≥ 0.10 (h).
  - It is **thin** below 0.05 (h).
- **OI moved** when |ΔOI| ≥ 3·σ₁·√n.
  - σ₁ is the robust σ (1.4826 × MAD) of today's 1-minute OI changes, using prior sessions until 15 minutes exist.
  - n is the number of minutes.
  - This is fold's own OI_Z = 3 rule, so the two engines share one grammar.
  - σ₁ on 29 Sep was 37 lots.
- **Stable IDs.** Legs are `NIFTY:2026-09-29:L07`, auctions `…:A03`, levels `…:V02`, blocks `…:K01`. An ID never changes.

### R-01. FEED HEALTH (the new requirement; the first line on every face)

| | |
|---|---|
| **Definition** | Three sources, each with a state:<br>• **GC** (GoCharting): **LIVE**; **SILENT** (no `/api/frame` POST for 15 s in session, 09:15–15:40, which is the extension's own `FRAME_STALE_MS`); **STALLED** (POSTs arrive but the forming bar's GC volume is under 80% of Upstox volume in the same bin, the gap is at least 1/3 of fold's bucket BK, and the bin is at least 60 s old); or **NONE** (no GoCharting feed for this index, i.e. BANKNIFTY or SENSEX).<br>• **UX** (Upstox book): SILENT after 30 s with no frame (fold's HOLE_MS).<br>• **CHAIN**: stale after 180 s (fold's CHAIN_STALE_MS). |
| **Inputs** | `_state["tape"][idx]["at"]` (the server already stores the last POST time); the forming bar in the POST; the Upstox minute series; the chain box. |
| **Self-calibration** | Stall size is in units of today's bucket (BK = 3 × the median 1-minute volume), not in lots. |
| **Lookback** | Now. |
| **Output** | EN: "GoCharting tape silent since 12:26:06 (no post for 15 s). GoCharting reads paused; reading on Upstox only."<br>Chip: **"GoCharting band · 12:26 se · tab kholo / F5"**.<br>Stall chip: **"GoCharting ticks ruke · 11:32 se · bar adhoora"**.<br>Upstox chip: **"Upstox ruka · 12:26 se · TapeMap window dekho"**. |
| **Rubric** | H3, H8; it protects R5, R7, R9, R16. |
| **Tag** | [M] (ages and volumes). |
| **On a hole** | It *is* the hole detector:<br>• Every read that depends on GC goes to **CAN'T CHECK — "GoCharting band hai (12:26 se)"**. That covers the GC Δ, P/A/E/C, the absorption ladder numbers, finished/unfinished extremes, stacks and tape agreement.<br>• Reads that run on Upstox continue, tagged **"1 tape"**.<br>• Marks made from GC data after the silence began are never drawn as live. The Trade tab hatches the span 12:25–16:08.<br>• When GC resumes and backfills, the new numbers are **appended as revisions** stamped with the backfill time ("added 16:08, not live"). They never overwrite. |

**How loud:**
- A black full-width band at the top of the GoCharting chart, the panel, the DESK, the float and the Trade tab. The alarm is inverse (black band, white text), so it uses no third hue.
- One double tick of sound the first time GC goes SILENT in session, and one when it returns. Never repeated.
- The panel can only show the banner if its content script is alive. That is why TapeMap's faces (DESK, float, Trade tab) are the ones that must shout. They do not depend on the page that died.

**Silence vs stall:**
- Silence catches the tab being discarded, or an orphaned content script (`boot.js:4` "extension context gone").
- Stall catches the tick stream dying while posts continue. That happened at 11:32 (bar 611 of 981 lots) and 12:25 (136 of 943).

**The stalled bar is also repaired** (§3.2):
- TapeMap answers the POST with `repair: [{t, why}]`.
- The extension asks GoCharting for that bar's `FOOTPRINT/V2` snapshot and re-posts it with `rev`.

**Chrome-side prevention (HER settings, not ours; the panel shows this once, in her words):**
1. Chrome → Settings → Performance → **Memory Saver** → "Always keep these sites active" → **Add** → `gocharting.com`. This stops Chrome discarding the background tab.
2. Keep GoCharting in its **own window** during market hours, not in a background tab. Chrome throttles hidden tabs.
3. **Never reload the extension between 09:15 and 15:40.** A reload orphans the page's script; if it happens, press F5 on the GoCharting tab.
4. If Energy Saver is on, turn it off during market hours.

### R-02. LEG (segmentation; the unit of reading)

| | |
|---|---|
| **Definition** | Directional change on the minute series:<br>• A leg in direction d runs from pivot P₀.<br>• Its extreme E updates while price makes new extremes.<br>• The leg is **confirmed ended** at the first trade δ(t) = 3·B(t) back from E. That is a price event inside the minute, never a bar close. E becomes the next leg's P₀.<br>• The first move from the open is a leg only if it covers ≥ δ; the open is not a pivot.<br>• Minute membership: a pivot minute belongs to the leg it ends.<br>• A GC 5-minute bar belongs to the leg that holds most of its Upstox volume. |
| **Inputs** | Minute series (UX price [M]); GC bars for the second tape. |
| **Self-calibration** | δ scales with B(t) as of the pivot; completed pivots are never re-cut with a later δ.<br>29 Sep: B went 9.8 (prior sessions) → 16.5 at 09:42 (the wide open) → 11.5 by the close, so δ went 29 → 50 → 34.5. |
| **Lookback** | The session (from 09:15; contract-scoped). |
| **Output** | Leg object `{id, n, dir, t0, p0, ext, ext_t, t_conf, forming}`.<br>EN: "▼ Leg 9 · 12:01–12:33 · −132 pts · 32 min".<br>Chip: **"Neeche −132 · 32 min"**. |
| **Rubric** | R1. |
| **Tag** | [M]. |
| **On a hole** | • Minutes filled from REST are tagged, and the cut runs on them the same way.<br>• If a hole cannot be filled (REST failed), the forming leg stays open and says **"Leg ka hisaab adhoora: 10:02–10:09 missing"**.<br>• No pivot is invented inside a hole. |

**AUCTION** (built on legs; this is what she reads first):

| State | Enters when | Leaves when |
|---|---|---|
| **TREND d** | The first confirmed leg; a breakout; or structure broken (price trades through the last counter-pivot, live, by price) | A trend-side pivot fails to extend beyond the last one by δ/2 → PAUSE; or a counter-pivot is broken → TREND −d |
| **PAUSE** | See above. The band = [the trend extreme, the last counter-pivot]. | A pivot beyond the band by δ/2 → TREND that way; otherwise (the other side fails too) → **RANGE** |
| **RANGE** (balance) | Both sides failed to extend. The band is frozen at declaration. A later pivot within δ/2 of an edge widens it, as an appended event. | Price trades beyond an edge by δ → **BREAKOUT** (live, by price) → TREND |

**Chips:**
- "Upar chal raha"
- "Neeche chal raha"
- "Ruk gaya @22590"
- "Range 22633–22723"
- "Range toota ▲ 22676"
- "Trend toota ↓ 22676"

**Replay, 6 NIFTY days:** 4–7 auction state changes per day (29 Sep: 7, plus one band-edge event), each with a named reason. The current fold ZONE row flipped its chip 110 times on 29 Sep.

### R-03. EFFORT vs RESULT per leg (the lambda read)

| | |
|---|---|
| **Definition** | Per leg and per tape (net Δ excludes blocks, R-10):<br>• **efficiency** λ = \|Δp\| ÷ \|net Δ\| × 1000, in pts per 1,000 lots. Defined only when the tape names an aggressor (share ≥ 0.10) and the aggressor's sign equals the leg's direction.<br>• **Amihud** = \|Δp\| ÷ volume × 1000, always defined.<br>• If the aggressor's sign is opposite to the leg's direction: **"price moved against the aggressor"** (the passive side won).<br>• If neither tape names an aggressor: **"two-sided"**. |
| **Inputs** | Leg (R-02); GC bar Δ (vendor side); UX quote-rule Δ; volume [M]. |
| **Self-calibration** | Two comparisons:<br>(a) vs the last completed leg in the same direction that has a defined λ on that tape (pairwise; from the second such leg);<br>(b) rank k of n among today's completed legs with defined λ on that tape, all directions. Mute until n ≥ 3.<br>**"Low"** = bottom third, or ≤ ½ of the last same-way leg on both tapes. **"Easy"** = top third. |
| **Lookback** | Today's completed legs. |
| **Output** | EN: "+89 for Δ+1,839 GC / Δ+1,011 UX = 48 / 88 pts per 1k; last up leg 114 / 119: heavy buying, less progress".<br>Chips: **"Mehnat zyada, fayda kam · 48/1k"**, **"Aasaan chaal · 114/1k"**, **"Kharid ke bawajood neeche"** (price down despite buying), **"Dono taraf barabar"** (two-sided). |
| **Rubric** | R2, R13. |
| **Tag** | [I] (λ carries Δ); Amihud [M]. |
| **On a hole** | • A GC-short bar inside the leg makes the GC λ **CAN'T CHECK ("GC bar 12:25 adhoora")**. The UX λ continues.<br>• When both tapes are down, only Amihud [M] shows. |

### R-04. WHO (delta × OI × price)

| | |
|---|---|
| **Definition** | Per leg, and per auction window (a RANGE, from its first pivot):<br>• **OI moved?** (3σ√n)<br>• **Aggressor**: named when at least one tape names a side, the other does not name the opposite side, and neither is SPLIT (R-09).<br>• **Price**: the leg's sign.<br>The table below gives the state. **ABSORBED** is added when an aggressor is named, and either price moved against it, or R-03 says "low" on every live tape. |
| **Inputs** | R-02, R-03, OI [M], R-05 mode. |
| **Self-calibration** | OI noise σ₁ from today; efficiency ranks from R-03. |
| **Lookback** | The leg; the auction since its first pivot. In roll mode, also "last 30 minutes vs today's pace". |
| **Output** | The state words below, with numbers. |
| **Rubric** | R3, R18. |
| **Tag** | [I] (OI [M], side [I]). |
| **On a hole** | • Aggressor from one tape: **"1 tape"**.<br>• OI missing (no OI update for more than 3 × the index's median OI gap: NIFTY 60 s, SENSEX 162 s): **"OI CAN'T CHECK: no OI since 12:41"**. |

| Price | OI | Aggressor | EN state | Chip |
|---|---|---|---|---|
| ↑ | ↑ | buyers or none | New longs | "Naye long · OI +x" |
| ↑ | ↑ | sellers | New longs, passive (sellers absorbed) | "Naye long (limit) · bikri dabi" |
| ↓ | ↑ | sellers or none | New shorts | "Naye short · OI +x" |
| ↓ | ↑ | buyers | New shorts, passive (buyers absorbed) | "Naye short (limit) · kharid dabi" |
| ↑ | ↓ | buyers | Short covering | "Short cover · OI −x" |
| ↑ | ↓ | sellers | Covering on bids, longs exiting into it | "Short cover (limit)" |
| ↓ | ↓ | sellers | Long liquidation | "Long nikal rahe · OI −x" |
| ↓ | ↓ | buyers | Liquidation, covering absorbed | "Long nikal rahe · kharid dabi" |
| any | ↓ | none | Both sides closing | "Dono nikal rahe · OI −x" |
| any | flat | named | Rotation, no new positions | "Sirf ghumaav · OI flat" |

**Roll mode rewrite (R-05):**
- Any "OI ↓" state in the expiring contract gets **"or roll"** / **"(ya roll)"**, until Oct resolves it.
- The sentence always ends: **"Sep closing flow, not direction."**
- **No state ever says "bullish" or "bearish".** The strongest words are the table's.

### R-05. EXPIRY / ROLL MODE (the contract calendar)

| | |
|---|---|
| **Definition** | • From the instrument dump (`upstox_instruments`, `futs[0]`, `futs[1]`, expiries): **roll mode** runs for the last 5 sessions to the front expiry; **expiry mode** runs on that day.<br>• The session is **09:15–15:40**: 77 five-minute bins, 385 minutes.<br>• From 15:15 the reader adds: "cash underlyings in the closing auction (15:15–15:35); futures flow expiry-distorted".<br>• **Next-month capture (build item):** subscribe `futs[1]` in Upstox `full` mode for the roll window, written to `book_<idx>_NEXT_<day>.jsonl` with `ik`/`expiry` on every row. At startup and after the close, backfill Oct 1-minute price, volume and OI from `upstox_rest.intraday(<Oct key>)`. The same quote rule gives Oct Δ [I].<br>• **Reads:** combined OI (Sep + Oct); per-window ΔSep, ΔOct and Oct Δ → **ROLLED / CLOSED / MIXED**; Oct-to-Sep volume ratio ("Oct volume passed Sep at 14:05"); rollover % = (Oct + Nov) ÷ (Sep + Oct + Nov) OI at the 15:40 print; rollover cost = (Oct − Sep) ÷ Sep × 100. |
| **Self-calibration** | "OI flat" for Oct uses Oct's own σ₁. |
| **Lookback** | The roll window; the auction window. |
| **Output** | From 09:15 on expiry day: EN "Sep expires today 15:40. Sep OI must reach zero; its changes are closing or rolling, not direction. Positioning is read in Oct." Chip: **"Sep expiry aaj · asli position Oct mein"**.<br>On T−4..T−1: chip **"Roll ke din · Sep OI = band/roll"**. |
| **Rubric** | R4, H6. |
| **Tag** | [M] OI, volume and calendar; [I] Oct Δ. |
| **On a hole** | Oct not captured (the case on 29 Sep): EN "Oct not recorded: rolled vs closed CAN'T CHECK". Chip **"Oct record nahi · roll/band check nahi"**. The "or roll" stays on every OI state. |

**Contract identity (H6):**
- Every number carries `contract: "NIFTY SEP FUT"` in the wire. On the face, the contract shows in the section header.
- Levels carry their contract:
  - an unfinished Sep high is labelled **"Sep"**;
  - it is dropped at 15:40 on expiry day;
  - it is never drawn on the Oct chart.
- Prior-day value is used only when the prior day is the same contract (`tape_log.prior_pool` already cuts by `ik`). On 30 Sep it reads **"pichla din alag contract — tulna nahi"** (the prior day is a different contract; no comparison).

**Time-critical for 29 Sep itself:**
- `upstox_rest.intraday` serves only the current day (audit §4).
- Pulling `NSE_FO|48704` (Oct) 1-minute data tonight would settle the 29 Sep roll-vs-close question after the fact.
- Whether `historical` serves it tomorrow is unverified.

### R-06. ABSORPTION AT A LEVEL (multi-bar)

| | |
|---|---|
| **Definition** | • **Levels** are only: the edges of a RANGE (the zone [edge − δ/2, edge]), and confirmed leg extremes that price revisits.<br>• A **visit** = price enters the zone after trading at least δ/2 away from it.<br>• **ABSORBED** when all of these hold:<br>&nbsp;&nbsp;(a) ≥ 3 visits (h);<br>&nbsp;&nbsp;(b) net Δ traded *inside the zone* is in the pushing direction on every live tape. GC uses ladder rows in the zone; UX uses frames whose ltp is in the zone.<br>&nbsp;&nbsp;(c) no acceptance beyond: less than 1 BK of volume traded beyond the edge by more than w = B/2 (fold's ACCEPT_BK = 1).<br>• **Book evidence (D1):** L1 OFI over the visits. Negative OFI under net buying (or the mirror) prints "passive side refilled". |
| **Inputs** | GC ladder (tick level) [M volume / I side]; UX frames; OFI [I]; R-02 auction. |
| **Self-calibration** | Zone width δ/2; acceptance in BK. No lot counts. |
| **Lookback** | The auction. |
| **Output** | Level `{id, lo, hi, side_absorbed, qty: {gc, ux}, visits, first, last, ofi, contract}`.<br>EN: "Ceiling 22706–22723 (Sep): buyers lifted Δ+704 GC / Δ+848 UX net in the zone over 6 visits; nothing traded above 22723; range OFI −1.3k: offers refilled. Absorbed here. Not a reversal call."<br>Chip: **"Upar kharid dabi · Δ+704 · 6 baar"**. |
| **Rubric** | R5 (D2). |
| **Tag** | [I]; the visits and the acceptance volume are [M]. |
| **On a hole** | • GC down: the qty.gc cell reads CAN'T CHECK and the level stays on UX with "1 tape".<br>• Visits and acceptance come from Upstox price and volume, so they survive. |

**Released or broken, appended as events and never silent:**
- **"Accepted above 22723 · 1 BK beyond"**: the level is broken, and the line turns to a dotted grey history line.
- **"Follow-through ↓ from 22723"**: a leg away with efficient opposite aggression. This is the only place a direction word may attach to absorption.

### R-07. EXHAUSTION (her E, fixed)

Her **E** stays the chart glyph. Two labelled forms go into one letter, carrying `form`:

| | |
|---|---|
| **E1 (board.js, fixed)** | The first bar making a new leg extreme whose with-leg Δ ≤ 60% of the leg's strongest bar (kept).<br>**Fixes:**<br>• It may re-fire in the same leg when a later extreme extends at least δ beyond the previous E *and* has lower with-leg Δ than that E's bar.<br>• The 100-lot floor becomes "the strongest bar ≥ today's median \|bar Δ\|, as of now". |
| **E2 (from tm, merged)** | A new 30-minute (6-bar) extreme made on Δ of the opposite sign: "new low on net buying". |
| **Inputs** | GC bars (the leg comes from R-02, not from `board.js legs()`: one leg definition). |
| **Output** | Chip **"Thak gaye · Δ−25 (GC)"**. When UX disagrees in sign on that bar, the E is drawn hollow with **"Tape alag · UX Δ−603"**. |
| **Rubric** | R15, R16 as evidence; not a standalone rubric read. |
| **Tag** | [I]. |
| **On a hole** | A GC-short bar never fires an E. This removes the 12:25 artefact. |

### R-08. CVD DIVERGENCE, AT STRUCTURE ONLY

| | |
|---|---|
| **Definition** | • Checked only when a **trend-side pivot extends**, or a **RANGE edge is re-tested**. It compares the CVD at this pivot with the CVD at the previous same-side pivot in the same auction, per tape.<br>• Bearish: a higher high with a lower CVD. Bullish: a lower low with a higher CVD.<br>• CVD is anchored at 09:15 and excludes blocks.<br>• **Subsumed** when an ABSORBED read already covers that edge on the same side: it is shown as evidence in the level line, not as its own chip. This is R15's sequence rule: in a range where buying is being absorbed, a bullish divergence at the low is expected by construction. |
| **Inputs** | R-02 pivots; both tapes' CVD. |
| **Lookback** | The current auction only. Never the whole session. |
| **Output** | Chip **"CVD ulta ▼ · GC ✓ UX ✗"**. The tape that shows it is named. |
| **Rubric** | R6. |
| **Tag** | [I]. |
| **On a hole** | A tape without data at either pivot reads CAN'T CHECK for that tape. |

**29 Sep, from the replay:**
- At the day high (12:01, 22764.9 vs 11:14, 22718), CVD was higher on both tapes: GC 7,857 vs 6,371; UX 6,972 vs 5,186. **No bearish divergence.** The reader says so and invents none.
- The old "UX divergence 11:45–12:15" came from the defective recorded ux ladder, comparing bar peaks inside one leg.
- At 15:22 (22616 vs the 12:33 low at 22633), CVD was higher on both tapes: GC 13,905 vs 7,501; UX 14,580 vs 5,003. That is bullish, but it is **subsumed** under the ceiling's absorption read.

### R-09. TWO TAPES (agree / differ / split)

| | |
|---|---|
| **Definition** | Per leg and per auction window: **AGREE** (same sign, both name an aggressor); **DIFFER** (same sign, one thin); **SPLIT** (opposite signs, both at least 0.05 share); **ONE** (only one tape exists). |
| **Inputs** | GC Δ, UX Δ (quote rule). |
| **Output** | Chips **"Dono tape ek"**, **"Tape alag · GC Δ+44 / UX Δ+352"**, **"Tape ulte"**. A SPLIT makes FLOW = SPLIT (R-13) and removes the aggressor from R-04. |
| **Rubric** | R16, H7. |
| **Tag** | [I]. |
| **On a hole** | GC down → ONE ("1 tape"), never SPLIT. |

**Replay, 6 NIFTY days, 70 legs with both tapes:**
- AGREE 39, SPLIT 5, one tape thin 26.
- At the bar level the audit found 67–72% sign agreement. At the leg level, of the 44 legs where both tapes named a side, 39 agreed.
- 29 Sep: 16 AGREE, 1 SPLIT, 4 thin.

### R-10. BLOCK PRINTS

| | |
|---|---|
| **Definition** | • **GC:** a ladder level where lots per print ≥ 100 × today's median lots per print (as of now), and the level is ≥ 25% of its bar (h).<br>• **UX:** one frame whose volume jump is ≥ 100 × today's median frame and ≥ 25% of its 5-minute bin.<br>• Each block is reported with the OI step in the next two minutes.<br>• Removed from leg Δ, CVD, efficiency and absorption quantities, and shown separately. |
| **Inputs** | GC ladder (`bt`/`st` trade counts); UX frames; OI. |
| **Output** | A hollow grey square at the print. EN: "Block: 4,528 lots at 22598.8 in one print (70% of its bar); OI +4.7k in the next minute. A position opened in one print; excluded from the leg." Chip **"Ek bada sauda · 4,528 @22598.8"**. |
| **Rubric** | R15 (one print is never a story), H7. |
| **Tag** | Size [M]; side [I]. |
| **On a hole** | The UX rule alone flags it. |

**Replay on 9 GC days:**
- 29 Sep: 10:05 (4,528 lots, 70%), 11:10 (729, 31%), 15:00 (2,030 in 3 prints, 59%).
- 23 Sep 10:35: 651 in 2 prints, 64%.
- Nothing on the other seven days.

### R-11. FINISHED / UNFINISHED EXTREMES

| | |
|---|---|
| **Definition** | • At each **confirmed leg extreme**, take the GC ladder rows within 1.0 point (h) of the extreme.<br>• **UNFINISHED** when both buy and sell volume are above 0 there. **FINISHED** when one side is 0.<br>• An unfinished extreme becomes a level line, labelled with its contract. It ends when traded through, or at the contract's last session close. |
| **Inputs** | GC ladder at the extreme bar. |
| **Output** | EN: "12:00 high 22762.1 unfinished (sell 3 × buy 137 at 22762)". Chip **"Adhoora high 22762"**; "Poora" is shown only in the leg table. |
| **Rubric** | R7. |
| **Tag** | [I]. |
| **On a hole** | GC-short extreme bar → CAN'T CHECK. It never guesses from UX, which carries no per-price side at the extreme. |

**29 Sep:**
- 12:00 high 22762 was unfinished, and was revisited at 12:05 (22764.5).
- The 12:05 high 22764.5 was finished (0 sold at the top).
- The 12:55 high 22723 was unfinished. It is labelled **Sep**, and is **dead at 15:40**.
- Lows at 09:35 (22580.5), 12:30 (22633.1) and 15:20 (22616) were finished.

### R-12. VALUE CONTEXT (initiative vs responsive) and PROFILE SHAPE

| | |
|---|---|
| **Definition** | • The prior same-contract session's POC and value area (70%), from the GC ladder in 5-point bins (the existing `prints` code).<br>• Each leg is tagged **initiative** (outside prior value, moving away) or **responsive** (moving toward it).<br>• **Profile shape** of a RANGE, from its own volume-at-price: **P** (POC in the upper third and a thin lower tail), **b** (the mirror) or **D** (otherwise). The shape is named, never forced. |
| **Output** | EN: "All day below prior value (28 Sep: VAL 22855, low 22793): up legs responsive, down legs initiative". "Range shape: D (POC 22685, value 22670–22705), not a P". |
| **Rubric** | R8, R10. |
| **Tag** | [M] volume at price. |
| **On a hole** | A different contract, or no prior tape file → "tulna nahi" (no comparison). |

### R-13. THE FLOW-ROW FEED (what fold receives)

Given her marked position side S (+1 for long CE or short PE; −1 for long PE or short CE):

| FLOW word | When | Chip |
|---|---|---|
| **WITH** | The current leg runs S's way and its aggressor is S's side (or two-sided with no SPLIT). "Absorbed" adds a caution clause but stays WITH. | "Saath · kharid Δ+667" |
| **PULLBACK** | The current leg runs against S, and all of these hold:<br>(a) its aggressor against S is not named, or its λ is below today's median, or R-03 says "price moved against the aggressor";<br>(b) price has not traded through the origin of S's last with-leg. | "Pullback · kamzor bikri · 22642 bacha hai" |
| **AGAINST** | The current leg runs against S with a named aggressor and λ at or above the median on the live tapes; or S's origin is broken; or S's side is ABSORBED at a level for 3 or more visits while S is pushing into it. | "Khilaaf · bikri Δ−1,815 · 73/1k" |
| **SPLIT** | The two tapes disagree in sign on the current leg. | "Tape ulte · check nahi" |
| **CAN'T CHECK** | No live tape (GC and UX both down), or the leg is younger than one minute after a hole. | "Check nahi · GoCharting band + Upstox ruka" |

- Changes are allowed only on a named event: a leg confirmed, an origin traded through, a level state change, or a tape going down. Each change is logged with its reason.
- The word is written to the flat read too, with S = the direction of the current auction.
- **Amendment for her to sign:** fold's FLOW row today is "the newest fight in the last 10 buckets". It becomes this word. Until she signs, the reader runs in shadow **beside** fold's row, and both are logged (§7.2).

### R-14. THE DAY (running story)

| | |
|---|---|
| **Definition** | • The list of auctions with their who-states, one clause each, plus the expiry clause.<br>• It updates when an auction changes. After 15:40 it adds rollover and the Oct resolution.<br>• It replaces fold's THE DAY fight count. That count called a +184-pt morning a "sellers' day". |
| **Rubric** | R17. |

**The 29 Sep text is in §6.**

---

## 3. What happens to every current detector

### 3.1 The table

| Detector (audit §A) | Verdict | What changes |
|---|---|---|
| board.js initiative | **KEEP** (not drawn) | Stays an input to signals and BOARD. The leg read supersedes it on the face. |
| board.js A, cluster form | **KEEP, FIX** | Fixed detection row (§3.2); the event carries `form: "cluster"`. |
| board.js A, effort form | **KEEP, FIX** | Same, with `form: "effort"`. Both forms screen blocks (R-10): a block bar says "block", not A. |
| board.js vacuum | **RETIRE** | Consumed by nothing, and it mislabelled the 09:35 exhaustion. |
| board.js C (climax) | **KEEP** | Fixed row only. |
| board.js P (trap) | **KEEP, FIX** | (1) A **negation** event when price trades one row back through the trapped side's level: the P greys, with "released". (2) The **same-print rule**: a P whose cluster is within one row and two bars of an A at the same price is suppressed and logged "same print", so no print is both A and P. (3) Inside a RANGE, a P not in an edge zone is **demoted**: small, grey, no chip. |
| board.js E | **KEEP, FIX, MERGE** | R-07: re-fire, a self-calibrated floor, tm's E2 merged, and it uses R-02's legs. |
| board.js walls (B/S) | **KEEP** | The lean count becomes the label ("B 22600 · 7 lean"). |
| board.js defended / trapped levels | **KEEP** (internal) | Placement only. |
| board.js HVN/LVN | **RETIRE** from the extension | TapeMap `prints.nodes` feeds R-12. |
| Band taps (rings) | **KEEP** | Untouched. They are the zone's eyes. |
| Flow since tap | **RETIRE** | Not shown since rev 6. |
| market.js priorLevels | **RETIRE** | Not contract-safe; R-12 replaces it. |
| decode.js readBar / imbalances | **RETIRE** | Dead code. |
| Marking rules (main.js) | **FIX** | §3.2. |
| tm absorption / tm climax | **RETIRE** | Duplicates on the same bars. |
| tm exhaustion | **MERGE** into E as E2 | |
| prints.py bar flags (stacks, unfinished, POC) | **KEEP** as evidence | Stacks attach to the leg line as "stacked buying 22662–22671"; they are never a mark. "Unfinished" is used only at leg extremes (R-11). The row is fixed per day (§3.2). |
| GC CVD (`prints.with_cvd`) | **KEEP** as input | Block-excluded variant added. |
| frame tape block | **KEEP** | |
| frame session aggressor | **RETIRE** | One block decided it for the whole day. |
| zone + flow `fire` | **KEEP**; amendment for her | The 3-row tolerance becomes B points. It is her choice (audit D.10), shown with the 09:31 evidence. |
| signals ballot and sound | **KEEP, untouched** | The window and fade-gate evidence is shown to her as a decision, not changed. |
| ux_gate family agreement | **REPLACE** on the face with R-09 | ux_gate stays as a bar-level diagnostic in `/api/tape`. |
| fit.contract | **KEEP** | Its trust bit also feeds H6. |
| fold units, buckets, fights, trapped/released, levels, named walls, in-trade | **KEEP** (fold's; signed) | Out of the reader's scope. Two amendments listed in §7.4: the expiring-series label for OI "off peak" on expiry afternoons, and the FLOW row. |
| fold flat FLOW | **REPLACE the source** with R-13 | Amendment. |
| fold THE DAY | **REPLACE** with R-14 | |
| fold GAVE UP / ZONE / NEXT FIGHT | fold's | Not touched here. The freeze and hysteresis fixes are owed by fold, per the audit. |
| ladder.py fill reconstruction | **Not used by the reader** | The reader's UX tape is the frame quote rule (D1). The tick-unit fix in `ladder.py`/`fold.py` stays fold's decision (`LADDER_TICK` is kept deliberately). |
| grounds CVD rank / aggression / FLOW-of-size | **REPLACE** with R-03/R-04 | BOARD and ANSWER read `/api/reader` instead. |
| grounds CVD divergence | **MERGE** into R-08 | Both tapes, at structure only. |
| grounds futures-OI quadrant (7-day blind) | **REPLACE** with R-04 + R-05 | Relabel in roll mode instead of blinding. |
| grounded calls | **KEEP**, re-grounded on reader facts | |
| VPIN | **KEEP** (fold's row) | Caption only. |
| sweep.py | **KEEP** (the signals depth vote) | |
| absorption.py (book replenishment) | **RETIRE** | R-06's OFI evidence replaces it; its kill clock can run out in the logs. |
| impact.py (λ) | **RETIRE** | λ is computed per leg in R-03. |
| hold.py flow family | **RETIRE** with hold.py | Outside this design, per the audit. |
| zone machine | **KEEP, untouched** | The reader annotates beside it and never gates it. |
| engine.py events | **KEEP**; rename on the face | "OI trap", "OI climax" and "OI absorption", so the tape's words mean one thing. |

### 3.2 The two named fixes

**Zoom-recompute stability** (the "marks come and go" root cause, `main.js:247`):
1. **The detection row is fixed per day.** It is chosen once at the open from the prior-session B: the nearest of {2.5, 5, 10} points to B/2. On 29 Sep that is 5.
   - `board()` runs on the tick-level ladder re-binned to that row, whatever the chart shows.
   - The chart's `rowSize` is used **only to place** a mark.
   - `P = new Map()` is no longer reset on a rowSize change.
2. **TapeMap's `ofd_marks` becomes the authority.**
   - On load or reload, the extension GETs the day's frozen marks and draws them.
   - It runs `board()` only for bars closed after the newest frozen mark.
   - Mark IDs are `<day>:<kind>:<bar t>:<price>`.
   - If a recompute (after a bar revision) differs, the extension posts a **revision** event; it never silently removes a mark.

**Truncated bars** (`adapter.js:142`, `session.js:27`, `tape_log` write-once):
1. TapeMap flags a GC bar `short` by comparing it with Upstox volume (R-01), and says so in the POST reply: `repair: [{t, have, want}]`.
2. The extension marks that bar `partial`. `session.js` then lets GoCharting's snapshot bar replace it, and re-posts with `rev: n`.
3. `tape_log` accepts a row for an existing `t` **only** with `rev > stored rev` and a `why`. It is appended, never overwritten, and readers take the latest rev.
4. Until repaired, reads on that bar are CAN'T CHECK. After repair, R-02..R-11 append revisions stamped with the repair time.

---

## 4. Architecture

### 4.1 Where each read is computed

| Read | Where | Why there |
|---|---|---|
| R-01 feed health | **TapeMap** (+ the extension's own page-side stall dot, already present) | The only process that sees all three feeds. It survives the GC tab dying. |
| R-02..R-06, R-08..R-14 | **TapeMap**: a new `reader.py` (pure functions over the minute series, GC bars and calendar) and `reader_live.py` (state and the append-only log) | One brain; anytime start; BANKNIFTY and SENSEX on the same code with "1 tape". |
| R-07 E, and her P/A/C | **Extension** `board.js` (her marks; the agreed architecture keeps "its own board"), with TapeMap holding the record | Minimal change to what she trusts; the frozen record makes it reproducible. |
| Minute series | TapeMap, from the book hook already installed (`server.py` `_hook_book`) | |
| Oct capture | TapeMap: `upstox_instruments.resolve` adds `futs[1]` in the roll window | |

### 4.2 Wire

`POST /api/frame` keeps its request. Its reply gains `reader` and `repair`. `GET /api/reader?idx=NIFTY[&day=][&since_id=]` returns the same block plus the event log, for the Trade tab, DESK, float and BOARD.

```json
"reader": {
  "v": 1, "idx": "NIFTY", "day": "2026-09-29",
  "contract": {"ik": "NSE_FO|68407", "name": "NIFTY SEP FUT", "expiry": "2026-09-29", "mode": "expiry",
               "next": {"ik": "NSE_FO|48704", "captured": false}},
  "asof": "14:00:04", "data_asof": {"minute": "13:59", "gc_bar": "12:20", "ux_frame": "14:00:03"},
  "feed": {"gc": {"state": "silent", "since": "12:26:06", "age_s": 5638, "why": "no /api/frame post for 15 s",
                  "fix": "GoCharting tab kholo / F5", "tag": "M"},
           "ux": {"state": "live", "age_s": 1}, "chain": {"state": "live", "age_s": 9}},
  "units": {"B": 11.3, "delta": 33.9, "oi_sigma": 37, "warm": {"legs_done": 13, "need": 3}},
  "auction": {"id": "A06", "state": "RANGE", "band": [22633.0, 22723.0], "since": "12:33", "declared": "13:03",
              "legs": 4, "chip": "Range 22633–22723"},
  "leg": {"id": "L14", "dir": 1, "t0": "13:40", "p0": 22642.0, "ext": 22697.0, "now": 22679.1, "forming": true,
          "dp": 37.1, "vol": {"v": 2607, "tag": "M"},
          "gc": {"state": "cant", "why": "GoCharting band (12:26 se)"},
          "ux": {"d": 938, "dx": 938, "share": 0.36, "tag": "I"},
          "ofi": {"v": 134, "tag": "I"}, "doi": {"v": -572, "moved": false, "tag": "M"},
          "tapes": "one", "eff": {"ux": 40, "vs_last_up": {"ux": 71}, "rank": {"ux": [1, 9]}},
          "who": {"state": "rotation", "absorbed": true, "roll": true, "chip": "Sirf ghumaav · kharid dab rahi"}},
  "window": {"from": "12:33", "dp": 46.1, "gc": {"state": "cant"}, "ux": {"dx": 3932}, "doi": -537, "ofi": 121},
  "levels": [{"id": "V02", "kind": "absorbed", "lo": 22706, "hi": 22723, "side": "buyers", "visits": 3,
              "qty": {"gc": null, "ux": 472}, "contract": "SEP", "state": "holding"}],
  "flow_row": {"state": "WITH", "side": 1, "why": "leg ▲ from 22642, buyers Δ+938 UX (1 tape)", "since": "13:41"},
  "chips": [{"id": "V02", "text": "Upar kharid dabi · Δ+472 · 3 baar", "tag": "I"}],
  "events": [{"id": "E0212", "at": "13:41:37", "kind": "leg_confirmed", "ref": "L13", "rev": 0}]
}
```

**Rules on the wire:**
- Every number is an object carrying `tag`, or sits under a key whose schema fixes the tag.
- A missing value is `{"state": "cant", "why": …}`, **never 0 and never null without a reason** (house rule 6).

### 4.3 Anytime start

On (re)start, `reader_live` rebuilds the day in this order:
1. **Minutes:**
   - persisted `min_<idx>_<day>.jsonl` rows are used as they are;
   - the gaps are filled from REST, tagged `rest`: price, volume and OI [M]; UX Δ for those minutes = **"side not recorded 10:02–11:20 (server down)"**.
2. **GC bars:** the extension posts the whole day on load, from GoCharting's history. Snapshot bars replace client-built tick bars, which is better data.
3. **Recompute:** R-02..R-14 are recomputed from 09:15 as-of, minute by minute. This is the same code path as live, and is deterministic.
4. **Compare:** each recomputed event is checked against the persisted log.
   - Equal → reused, same id.
   - Different → a revision is appended, with why ("GC bar 12:25 repaired" or "minutes 10:02–11:20 from REST").

**What a restart cannot rebuild, stated on the face:** UX side for the gap; OFI for the gap; the live forming-bar path.

**The guarantee (H8):**
- The restarted reader's cut and states equal the uninterrupted record's everywhere outside the labelled gap.
- Inside the gap they differ only where REST minute extremes differ from ltp-built ones. That is at most one pivot's price, and it is labelled.

### 4.4 No repaint

- `data/reader/reader_<idx>_<day>.jsonl` is **append-only**.
- Each event is `{id, rev, kind, at, data_asof, payload, why?}`.
- Every face draws from the log, never from a fresh recompute.
- A forming leg is drawn as forming: hollow label, grey, and "abhi" (now).
- At confirmation the leg is frozen with `t_conf`. A RANGE band is frozen at declaration, and widenings are new events.
- **Test:** replaying a day twice produces byte-equal logs. No event's `at` is earlier than its `data_asof`.

### 4.5 Prerequisites (owed by others; the reader depends on them)

- **P0, session end 15:40 everywhere** (audit §8.3, about 30 places). A live data-loss bug; it needs her word.
- The Upstox record starts at 09:17. REST backfill covers price, volume and OI for 09:15–09:16; the side is labelled not recorded.
- Oct subscription: the `full`-mode subscription limit must be checked first (audit: not verified).

---

## 5. The face

### 5.1 Design decisions (professional, restrained)

**Type:**
- One family: Inter, falling back to `system-ui`.
- Numbers always `font-variant-numeric: tabular-nums`, right-aligned in tables.
- Sizes: 11 px labels, 13 px body, 16 px for the one headline number on the DESK. Line height 1.35.
- **Two weights only: 400 and 600.** No italics, no underline except links, no emoji, no icons.
- Glyphs from the font only: ▲ ▼ □ ◇ ·

**Colour: two hues plus grey. Colour means SIDE, never good or bad.**

| Token | Value | Used for |
|---|---|---|
| `--buy` | `#1D5FA8` (blue) | Buyers' aggression, buyer-side levels, ▲ legs |
| `--sell` | `#B8432F` (vermilion) | Sellers' aggression, seller-side levels, ▼ legs |
| `--ink` | `#1F2328` | Text |
| `--ink-2` | `#57606A` | Secondary text, forming legs, demoted marks |
| `--line` | `#D0D7DE` | Hairlines, RANGE band |
| `--bg` / `--panel` | `#FFFFFF` / `#F6F8FA` | Light mode only |
| **Alarm** | inverse: `#111` background, `#FFF` text | FEED down, CAN'T CHECK banners. No third hue. |

- Her P/A/E/C keep their **shapes, letters and placement**. Their colours move onto `--buy`/`--sell`.
- **Inferred numbers are always written with Δ** ("Δ+667"). The panel footer carries a one-line legend: **"Δ = andaaza (side guessed) · OI, lots, pts = napa hua (measured)"**. The wire carries the tags. That is H2 without a symbol she has to learn.
- **Density:** at most **9 reader objects on the GoCharting chart at once**, plus her marks. Everything else lives in the panel or the Trade tab.

### 5.2 GoCharting overlay (what is drawn, and how few)

| Object | Mark | Size | Label (chip) | Max on screen |
|---|---|---|---|---|
| RANGE band | Two 1 px `--line` hairlines across the band's time span | 1 px | Right edge: "Range 22633–22723 · 12:33" | 1 |
| Breakout / trend break | ▲ or ▼ at the trigger price, side colour | 9 px | "Range toota ▲ 22676" | 1 |
| Pivot label | Text at the last **two** confirmed pivots | 11 px | "▼ −132 · 73/1k" | 2 |
| Forming leg | One grey hollow label at the running extreme | 11 px | "▲ abhi +37" | 1 |
| Absorbed level | A 2 px segment over the visits, in the absorbing side's colour | 2 px | "Upar kharid dabi · Δ+704 · 6 baar" | 2 |
| Unfinished extreme | A dotted 1 px grey line to the right edge | 1 px | "Adhoora 22723 · Sep" | 2 |
| Block | A hollow grey square at the print | 7 px | "Bada sauda 4,528" | as printed (0–3 a day) |
| FEED banner | A black full-width strip at the top | 22 px | "GOCHARTING BAND · 12:26 se · tab kholo / F5" | 1 |
| Her P/A/E/C | As today | as today | Her chips, plus "Tape alag" on a hollow E | her count |

- Inside a RANGE, P/A/E/C that are not in an edge zone are **demoted**: 60% size, `--ink-2`, no chip.
- Nothing is hidden: tapping a demoted mark shows its chip.

### 5.3 GoCharting panel (right side, about 300 px)

```
┌──────────────────────────────────────────────┐
│█ GOCHARTING BAND · 12:26 se · tab kholo / F5 █│  ← only when not live (black band)
│  (Upstox pe chal raha · 1 tape)              │
├──────────────────────────────────────────────┤
│ HOLD                              fold's word │  ← fold, untouched
│ ZONE  … │ FLOW  Saath · kharid Δ+938 (1 tape) │  ← FLOW = reader R-13
│ OI    … │ VPIN  …  · ek taraf, disha nahi     │
├──────────────────────────────────────────────┤
│ Range 22633–22723 · 12:33 se · 4 legs         │  auction
│ ▲ Leg 14 · 13:40 se · +37 · Δ+938 UX · OI −572│  leg (one line)
│ Sirf ghumaav · kharid dab rahi · 40/1k (1/9)  │  who + effort
│ Upar 22706–22723: kharid dabi Δ+472 · 3 baar  │  level
│ Sep expiry aaj · Oct record nahi              │  contract
├──────────────────────────────────────────────┤
│ Δ = andaaza · OI, lots, pts = napa hua        │  legend (grey, 11 px)
└──────────────────────────────────────────────┘
```

- Five reader lines, at most. The contract line shows only in roll or expiry mode.
- **The one-line leg sentence**, EN in the tooltip and API, Hinglish chip on screen:
  - EN: `▲ Leg 14 · 13:40–now · +37 pts · buyers Δ+938 UX (GC: can't check) · OI −572 (flat) · 40 pts/1k (last up leg 71)`
  - Chip: `▲ Leg 14 · 13:40 se · +37 · Δ+938 UX · OI −572`

### 5.4 Trade tab (ui-v2; "our playground")

- **On the futures chart:**
  - the leg zigzag, one 1 px `--ink-2` polyline through the confirmed pivots;
  - RANGE bands as 6%-grey rectangles;
  - absorbed levels, blocks, and unfinished extremes (as §5.2);
  - her P/A/E/C;
  - **hatched holes** where a feed was down (29 Sep: GC 11:32–11:39 stall, 12:25–16:08 silent).
- **Under the chart, the LEG TABLE** (the professional read; one row per leg; about 8–21 rows a day):

| # | Time | | Pts | Min | GC Δ | UX Δ | Tapes | OI | pts/1k GC / UX | Who |
|---|---|---|---|---|---|---|---|---|---|---|
| 6 | 11:06–11:14 | ▲ | +118 | 8 | +1,034 | +986 | ek | −1,028 | 114 / 119 | Short cover (ya roll) |
| 7 | 11:14–11:18 | ▼ | −42 | 4 | +107 | +145 | ek | −97 | — | Kharid ke bawajood neeche |
| 8 | 11:18–12:01 | ▲ | +89 | 43 | +1,839 | +1,011 | ek | −1,065 | 48 / 88 | Short cover (ya roll) · mehnat zyada |
| 9 | 12:01–12:33 | ▼ | −132 | 32 | −1,815 | −1,969 | ek | −1,319 | 73 / 67 | Long nikal rahe (ya roll) |

  - Block-excluded Δ.
  - The GC cell shows "✗ band" when GC is down.
- **Above the table:** the auction line and the day line.
- **No other new chart layers.**

### 5.5 DESK and float

- Line 1 (only if any feed is down): the black FEED band.
- Then fold's headline and four rows, with FLOW from R-13.
- One reader line: the auction plus leg chip.
- On the float, the leg chip only.

### 5.6 Chip vocabulary (the whole list; nothing else appears)

| Chip | Means |
|---|---|
| Upar chal raha / Neeche chal raha | Trend up / down |
| Ruk gaya @P | Pause: the trend side failed to extend at P |
| Range L–H | Balance band |
| Range toota ▲ P / Trend toota ↓ P | Breakout / structure broken |
| ▲ Leg n · t se · ±pts | The current leg |
| Aasaan chaal · x/1k | Efficient leg (top third) |
| Mehnat zyada, fayda kam · x/1k | Low efficiency (bottom third, or ≤ ½ the last same-way leg) |
| Kharid ke bawajood neeche / Bikri ke bawajood upar | Price moved against the aggressor |
| Dono taraf barabar | Two-sided (neither tape names an aggressor) |
| Naye long / Naye short · OI +x | New positions |
| Short cover / Long nikal rahe · OI −x | Covering / liquidation |
| Dono nikal rahe · OI −x | Both sides closing, no aggressor |
| Sirf ghumaav · OI flat | Rotation |
| … (ya roll) | Roll-mode qualifier |
| Upar kharid dabi / Neeche bikri dabi · Δ · n baar | Absorbed at a level |
| Thak gaye · Δ | E (exhaustion) |
| CVD ulta ▼/▲ · tape | Divergence at structure |
| Adhoora high/low P · contract | Unfinished extreme |
| Ek bada sauda · lots @P | Block |
| Dono tape ek / Tape alag / Tape ulte | Tapes agree / differ / split |
| Saath / Pullback / Khilaaf / Tape ulte / Check nahi | FLOW row words |
| Garam ho raha k/3 | Warm-up (ranks mute) |
| GoCharting band / GoCharting ticks ruke / Upstox ruka · since · fix | FEED |
| Sep expiry aaj · asli position Oct mein / Oct record nahi | Expiry |
| Pichla din alag contract — tulna nahi | Roll: no prior-day comparison |

---

## 6. 29 Sep, walked through (as-of replay; GC as it really was unless marked)

**Replay notes:**
- The Upstox record starts at 09:17. The 09:15 minutes are seeded from the GC 09:15 bar, as REST would give them.
- GC's forming bar is not recorded, so the as-of GC figures use closed bars.
- **Reality:** GC ticks stalled at 11:32:35 (the bar short by 370 lots) and again at 12:25:51. POSTs stopped at about 12:26 and resumed at 16:08.
- Upstox was live throughout, until the 15:30 recorder cut (a bug).

### All day, from 09:15
- Contract line: **"Sep expiry aaj 15:40 · Sep OI zero hoga · asli position Oct mein · Oct record nahi"**.
- Overnight: Sep OI 159.6k → 135.3k (−24.3k, −15%). The reader says **"overnight roll: −24.3k, not compared with the 09:15 change"** [M].
- Prior value (28 Sep, same contract): POC 22880, VA 22855–22965, low 22792.9. The open, 22755.5, is **below prior value**: "up legs responsive, down legs initiative" (R-12).

### 09:20
- **Warm-up:** B = 9.8 (prior sessions), δ = 29.4. Legs completed: 0; ranks mute: **"Garam ho raha 0/3"**.
- **Leg:** ▼ Leg 1 forming, 22761.3 (09:15) → 22692.6 low, −69 in 5 minutes. **Chip "Neeche −69 · 5 min"**.
- **Effort:**
  - UX Δ−564 (09:17–09:19; the side for 09:15–09:16 was not recorded);
  - GC 09:15 bar Δ−794;
  - both sellers: "Dono tape ek".
- **OI:** −408 since 09:17. With σ₁ from prior sessions (50) the bar is ±260, so OI moved. Who: **"Long nikal rahe (ya roll) · OI −0.4k"**.
- **fold:** unchanged. **Zone machine:** not armed yet (09:25 anchor).
- **Her E at 09:20 (22672):**
  - its bar Δ+47 GC vs −581 UX → **hollow E, "Tape alag · UX Δ−581"**;
  - inside a trend leg that is not at a level → **demoted**.
  - The audit graded it WRONG; this design no longer presents it as a live call.

### 09:35
- **Leg:** ▼ Leg 1 forming, −131 (22761 → 22630; running low 22625.5), 20 minutes. δ now 43.5 (the wide open raised B to 14.5).
- **Effort:**
  - GC Δ−1,014 (4 closed bars, share −13%); UX Δ−1,512 from 09:17 (share −24%): **"Dono tape ek"**.
  - Efficiency: GC ≈ 130, UX ≈ 87 pts/1k; **no rank yet (0 completed legs)**.
- **Who:** Sep OI −2.0k (−1.4%), moved → **"Long nikal rahe (ya roll) · OI −2.0k · Sep closing flow, not direction"**.
- **FLOW (flat read, S = down):** WITH the trend.
  - For her live **long 22800 PE**, it would read **Saath**. She exited at 09:35:26 at the low.
  - The reader has no "the low is in" read at 09:35. That comes at 09:41, when the up leg is confirmed.
  - It does not claim what it cannot see. fold's 09:33 "sellers absorbed" (UX buckets) stays fold's.

### 10:10
- **Auction:** TREND ▼ since 09:15 (declared 09:41). Legs: ▼1 −181 (09:15–09:38), ▲2 +63 (09:38–09:42).
- **Leg:** ▼ Leg 3 forming, 22643 → 22606 (low 22595), −37.
- **BLOCK:**
  - **"Ek bada sauda · 4,528 @22598.8"**: 10:07:42, one print, 70% of the 10:05 bar.
  - OI +4.7k (+3.6%) in the next minute: a position opened in one print.
  - Excluded from Leg 3's Δ.
- **Effort ex-block:**
  - GC Δ+571, UX Δ+231 (shares 5% / 2%): neither tape names an aggressor → **"Dono taraf barabar"**.
  - Price drifted down without sellers. "Kharid ke bawajood neeche" needs a named buyer, so it is not claimed.
- **Ranks:** 2 completed legs → **"Garam ho raha 2/3"**.
- **Who:** before the block, Sep OI fell −3.9k from 09:42 to 10:07 (moved) → **"Dono nikal rahe (ya roll) · OI −3.9k ex-block"**. The block's +4.7k step is shown on its own line, not netted in.
- **FLOW for the zone long** (armed 09:27, triggered 09:39, entry 22630.5): **PULLBACK**. Leg 3 is against it with no named aggressor, and Leg 2's origin (22580.5) is intact. Chip: "Pullback · bikri nahi · 22580 bacha hai".
- **Her marks:**
  - The 10:05 A sits on the block bar, so it says "block", not A.
  - The base Ps at 10:05–10:10 (22612–22618) are drawn: the auction is still TREND ▼, so nothing demotes them yet.
  - P's new negation greys them ("released") when price trades one row back through 22623, at 10:40.
  - From 11:02 the RANGE demotes any P that is not in an edge zone, including the 10:30 P.

### 11:10
- **Auction:** **RANGE 22580.5–22643.1**. Chain of events: PAUSE at 10:43 ("22590 low held vs 22580.5"), RANGE declared 11:02 (the 22640 high failed too). 5 legs.
- **Range window (09:38–11:10):**

| Tape | Raw Δ | Ex-block Δ | Share |
|---|---|---|---|
| GC | +5,739 | +1,211 | 6.8% |
| UX | +5,414 | +891 | 5.0% |

  - Both are thin once the block is out.
  - OI −8.6k (−6.5%; the block's +4.7k/−5.2k is inside).
  - Price +20 net.
  - Who: **"Dono nikal rahe · OI −8.6k (ya roll)"**, i.e. positions closing on both sides with no aggressor. This is the "positive delta in the base" the audit found GC-only; the reader shows it was the block.
- **Leg:** ▲ Leg 6 forming from 22600.3 (11:06), +35 to 22635; GC Δ+92, UX Δ+55.
- **11:11:xx:**
  - price trades 22676 (the band + δ): **"Range toota ▲ 22676"** is drawn and logged. That is 5 minutes before fold's GAVE UP would have been possible, and it is on price.
  - The trade that did it: 11:10 minute, 1,007 lots, UX Δ+893, including a **729-lot block at 22651.6** (flagged, excluded).
- **Ranks:** 5 completed legs, 3 with GC λ defined → ranks live: "3 legs · ranks on".
- **Zone machine:** the BUY exited at VWAP at 11:09. The reader says nothing about the exit.

### 12:05
- **Auction:** TREND ▲ since 11:11.
- **Legs:** ▲6 +118 (11:06–11:14) at 114 / 119 pts per 1k: rank 2 of 4 on GC, so not "aasaan", but it is the benchmark the next up leg is compared with. OI −1,028 → **"Short cover (ya roll)"**. ▼7 −42: "Kharid ke bawajood neeche".
- **Leg:** ▲ Leg 8 forming 11:18→, 22676 → 22764.9 high; as of 12:04, 22755.
- **Effort:**
  - GC Δ+1,839, UX Δ+1,022 ex-block (blocks at 11:28:57, 328 lots, and 12:01:06, 302 lots; UX only);
  - **43 / 77 pts per 1k vs the last up leg's 114 / 119**;
  - chip **"Mehnat zyada, fayda kam · 43/1k (pichla ▲ 114)"**.
- **Who:** OI −1.2k over the leg, moved → **"Short cover (ya roll) · mehnat zyada"**. That is **not** new longs.
- **R-08:** a new high with CVD higher on both tapes → **no divergence** (said, not invented).
- **R-11:** the 12:00 bar high 22762.1 is **unfinished**: "Adhoora high 22762 (sell 3 × buy 137)".
- **Context shown with it:**
  - her A at 12:00 at CE 22761, and the three As at 11:40;
  - the zone machine's SELL armed on u2 at 11:30;
  - the prior low 22793 above: **"prior value ke neeche · responsive"**.
- **FLOW for a long:** WITH, with the caution clause. For the zone SELL (armed, not triggered): nothing. The reader never gates the zone.

### 12:30 (as it really was)
- **FEED:**
  - GC ticks stalled 12:25:51; POSTs stopped about 12:26 → from 12:26:06 on every face: **"GOCHARTING BAND · 12:26 se · tab kholo / F5"** (black), plus one double tick of sound.
  - The 12:25 GC bar (136 of 943 lots) is flagged **short**. Its E ("new low on Δ−24") **does not fire** (R-07).
  - The 11:30 bar (611 of 981) was flagged at 11:32 as **"GoCharting ticks ruke"**, and cleared at 11:40, when GC volume matched Upstox again.
- **Auction:** TREND ▲; the 11:18 higher low (22676) is intact at 12:30:00.
- **Leg:** ▼ Leg 9 forming from 22764.9, −75 (to 22690; low 22680.1).
  - UX Δ−1,554 (−30%), λ 48. GC: **CAN'T CHECK ("GC band + 12:25 bar adhoora")** → "1 tape".
  - **Who:** OI −1.4k, moved → **"Long nikal rahe (ya roll) · 1 tape"**.
- **12:30:3x:** price trades below 22676 → **"Trend toota ↓ 22676"**, live, by price. This is "somebody gave up" on the flow side, at a level that is not the obvious stop.
- **FLOW:**
  - for the zone short (triggered 12:18, entry 22729.1): **Saath**;
  - for any long: **Khilaaf** (the origin 22676 is broken).
- **With GC alive, it would have said the same, two tapes:** GC Δ−816, and the leg at 12:33 ended at GC −1,815 / UX −1,969, λ 73 / 67, "Dono tape ek".

### 14:00 (as it really was; GC silent since 12:26)
- **Auction:** **RANGE 22633–22723**.
  - Chain: TREND ▼ confirmed 12:35 (structure broken at 22633), PAUSE 12:56 (the 22670 low held), RANGE declared 13:03.
  - 4 legs since 12:33.
- **Leg:** ▲ Leg 14 forming from 22642 (13:40), +37 (high 22697). UX Δ+938 (share 36%), λ 40 vs the last up leg (12:46–12:57) at 107; **rank 1 of 9 on UX (the lowest)**. GC: CAN'T CHECK.
- **Range window (12:33→):**
  - price +46 from the low; UX Δ+3,932 (41% of 9,560 lots);
  - Sep OI −537 (−0.4%, **flat** by 3σ√n: the bar was ±1,035);
  - OFI +121.
  - Who: **"Sirf ghumaav · kharid dab rahi · OI flat · 1 tape"**, i.e. buyers pressing inside a range, no new positions, little progress.
- **Level:** 22706–22723 visited 3 times (12:41, 12:57, 13:05); UX Δ+472 net in the zone; nothing traded above → **"Upar kharid dabi · Δ+472 · 3 baar (1 tape)"**.
- **R-12 shape (as of 14:00):** D, not P.
- **R18 check, a hypothetical long CE entered at 13:45:**
  - FLOW **Saath** (Leg 14 ▲, buyers);
  - WHO (context) "sirf ghumaav, OI flat": no new longs behind it;
  - the ZONE row would get the level: "under the absorbing ceiling 22706–22723";
  - VPIN is fold's, with its caption;
  - nothing waits for a bar close.
- **With GC alive:** the range window reads GC Δ+1,559 / UX Δ+3,932 → "Dono tape ek".

### 15:00–15:40
- **15:00:** range window price +50; GC Δ+2,965 / UX Δ+5,227 (with GC alive).
  - **Sep OI −4.3k (−3.6%), moved; −3.2k in the last 30 minutes = 2× today's pace (−55/min)**; OFI −1,986.
  - WHO turns: **"Short cover (ya roll) · kharid dab rahi · OI −4.3k"**. The first time the reader says covering on the afternoon, and it says why: OI moved.
  - Level: 4 visits, UX Δ+529 in the zone; **range OFI −2.0k: "offers refill ho rahe"**.
- **15:00:33 block:** **"Ek bada sauda · 2,030 @22684"** (3 prints, 59% of the 15:00 bar); excluded. OI +1.2k then −2.2k.
  - Her A at 15:00 is a block bar → it says "block", not A, under the same-print rule.
  - Her As at 15:10 and 15:15 stand. The 15:15 level, 849 lots in 23 prints, is **not** a block.
- **15:10:** 5th visit (22714.8). Leg ▲ 15:02–15:10 +61: UX λ 38 → **"Mehnat zyada, fayda kam · 38/1k"**.
- **From 15:15:** clause **"cash closing auction 15:15–15:35 · futures flow expiry-distorted"**.
- **15:20–15:22:** a poke to 22616.
  - 15:20 minute: 1,514 lots, UX Δ−514.
  - 17 below the band = δ/2, so **not a breakout** (δ = 34). Logged: "band edge 22616".
  - R-08: CVD higher on both tapes (GC 13.9k vs 7.5k; UX 14.6k vs 5.0k) → **subsumed**: "CVD ulta ▲ (subsumed: kharid dab rahi)". No standalone bullish call.
  - Her C at 15:20 stands. Her P at 15:20 (22705) is not in the edge zone → demoted.
- **15:22–15:29:** ▲ +98 back to 22714, the 6th visit. UX λ 122. **Sep OI −3.3k in the 15:29 minute alone.**
- **15:30–15:40** (from the GC export; the Upstox recorders cut at 15:30, a bug; §4.5):
  - 1,800 lots traded, price pinned 22713.8–22716, Δ−196 GC, OI −486.
  - Chip **"15:30–15:40 · 22714–22716 pe ruka · settlement window"** [secondary: the 15:10–15:40 VWAP window per the circular summaries].

**At 15:40, the afternoon read (the R3 pass case):**

> **EN:** Range 22616/22633–22723 since 12:33. Buyers Δ+6,117 GC / Δ+8,381 UX (block-excluded; both tapes, shares 18% / 25%) for +81 pts from the low (+40 from 13:30). Sep OI −11.2k (−9.3%, 12:30 to 15:35), of which −9.9k came after 14:30. Short covering (or roll) into expiry, absorbed under 22706–22723 (6 visits, nothing accepted above; offers refilled, range OFI −1.3k). Not new buying. Sep closing flow, not direction. Oct not recorded: rolled vs closed CAN'T CHECK.
>
> **Chip:** Short cover (ya roll) · kharid dabi 22706–22723 · OI −11.2k · Oct record nahi

For comparison: the supervisor's window (13:30–15:30) gives GC Δ+7,483 raw / +5,453 ex-block, UX Δ+6,064 ex-block, OI −10,761, +39 pts. The same read.

### The day story at 15:40

> Sep expiry, all day below 28 Sep's value.
> - **Morning:** drive ▼ −181 (09:15–09:38; sellers on both tapes; OI −2.8k: liquidation or roll).
> - **Base 22580–22643** (09:38–11:06): both sides closing (OI −8.6k), no aggressor once the 10:07 block (4,528) is out.
> - **Breakout ▲ at 11:11:** short covering (or roll), 114 pts/1k.
> - **Grind to 22765** (11:18–12:01): covering at 43–88 pts/1k, "mehnat zyada". No divergence.
> - **Reversal ▼ −132** (12:01–12:33): sellers efficient, trend broken at 22676.
> - **Afternoon:** the range above, covering absorbed.
> - **Rollover % and roll-vs-close:** CAN'T CHECK (Oct/Nov not recorded).
> - **Feed:** GoCharting silent 12:26–16:08 (ticks stalled 11:32–11:39 and from 12:25:51). The afternoon's GC numbers were added at 16:08 (not live).

---

## 7. Validation

### 7.1 Descriptive replay protocol (no edge; checks the reader tells the truth about the tape)

**Days:**
- **NIFTY Tier A**, GC + book: 22, 23, 24, 25 (GC to 13:35), 28 and 29 Sep.
- **NIFTY Tier B**, GC only: 11, 18 and 21 Sep. Legs are cut on GC 5-minute prices as the declared fallback; UX is "not recorded".
- **Tier C** exports: 7, 8, 9, 10, 15 and 17 Sep.
- **BANKNIFTY and SENSEX:** 22–29 Sep, Upstox only ("1 tape").
- **Also required:** one non-expiry day judged first (28 Sep) and one expiry day (29 Sep).

| # | Check | Pass bar (pre-registered) |
|---|---|---|
| 1 | Determinism: two replays of each day | Byte-equal event logs |
| 2 | As-of integrity | No event has `at` earlier than `data_asof`; no event rewritten; revisions append with `why` |
| 3 | Anytime start: restart at 10:00, 12:00 and 14:00, with 30 minutes of UX side removed | Legs, auctions and levels equal the uninterrupted log outside the labelled gap; inside it, only the labelled differences |
| 4 | Churn | ≤ 12 auction changes per day and ≤ 20 FLOW-row changes per day (NIFTY), each with a named reason. Replay today: 4–7 auction state changes per day |
| 5 | Misdescription audit: 60 random reads per day | Each sentence's [M] numbers re-derived from the raw files. Every "buyers/sellers" claim holds on the tapes it names. Every "absorbed" has < 1 BK beyond. Every rank shows n ≥ 3. Count of contradictions reported (a count, not a rate) |
| 6 | Blocks | Every block the rule flags is listed, with its OI step. None enters a leg's Δ |
| 7 | Feed health, replayed from `frame_*.jsonl` arrival times and GC-vs-UX volumes | Flags 29 Sep 12:26–16:08 SILENT, and every short bar in audit §3d (22 Sep 12:10, 13:15, 13:20, 14:55; 23 Sep 11:20, 12:10, 12:30, 14:25; 24 Sep 10:25, 10:35, 11:20, 13:30, 14:00; 25 Sep 10:20, 12:20; 28 Sep 14:50; 29 Sep 11:30, 11:35 (below the stall bar; listed as short), 12:25). Zero GC reads drawn live inside a flagged span |
| 8 | Expiry and roll | Roll mode on from the 5th session before each front expiry; expiry mode on 29 Sep from 09:15; no "OI ↓" state without "(ya roll)" in the window |
| 9 | K sensitivity (3 ± 0.5) | The named structure is the same at 3 and 3.5 on at least 6 of 9 GC days True today on 28 and 29 Sep; **not** on 22 Sep, where K = 3.5 loses the 13:00 breakout |

### 7.2 Shadow run, from the next session (30 Sep: Oct front, first post-roll day)

- The reader runs live and writes `data/reader/`.
- It is drawn **only** on a "shadow" toggle on the Trade tab. The GoCharting chart and panel are unchanged, except for the **FEED banner**, which ships at once. It is a data-integrity alarm, not a read.
- fold's FLOW row stays fold's. The reader's R-13 word is logged beside it every minute, for her to compare.
- **After 10 sessions** (including the 27 Oct expiry if it falls inside; otherwise the clock extends to cover it): the judge runs §7.1 on the shadow logs and shows her side-by-side days.
- **She decides** whether the reader goes on the chart and whether R-13 feeds FLOW.

**Kill conditions** (any one, over 30 sessions):
- any repaint;
- the churn bar missed on 5 or more sessions;
- 3 or more misdescriptions of a [M] number found in the audit sample;
- she calls it noise.

### 7.3 What would falsify each read (as a description)

| Read | Falsified when |
|---|---|
| R-01 feed | A GC silence of 15 s or more in session is not flagged, or a flagged span had live POSTs |
| R-02 leg / auction | Two replays differ; a restart differs outside the labelled gap; a confirmation time precedes the trade that crossed δ |
| R-03 effort | The stated λ does not recompute from the stated numbers; "mehnat zyada" appears on a leg not in the bottom third and not ≤ ½ of the last same-way leg |
| R-04 who | The OI sign or significance is wrong vs `book` OI; an aggressor is named on a SPLIT leg; "or roll" is missing in the roll window; after the close, REST Oct OI shows the opposite of a resolved ROLLED/CLOSED |
| R-05 expiry | Roll or expiry mode on the wrong sessions (from the dump); any number without its contract |
| R-06 absorbed | ≥ 1 BK traded beyond the edge while the level still reads "holding"; fewer than 3 visits |
| R-07 E | An E fired on a short bar; a re-fire without the δ and lower-Δ conditions |
| R-08 divergence | Checked at a pivot that is neither extending nor an edge re-test; a divergence claimed where the tape's CVD does not show it |
| R-09 tapes | AGREE shown when the signs differ |
| R-10 block | A flagged print fails the rule, or an unflagged print passes it |
| R-11 extremes | The printed bid × ask at the extreme does not match the ladder |
| R-12 value | Prior value used across a contract change |
| R-13 FLOW | A change without a named event; WITH shown while the tapes are SPLIT |

### 7.4 Pre-registration sheet (for her signature; nothing ships on the face before it)

**Thresholds, all (h):**
- K = 3;
- aggressor share 0.10, thin 0.05;
- OI 3σ√n;
- block 100× the median print size and 25% of its bar;
- level zone δ/2, 3 visits, acceptance 1 BK;
- extreme row 1.0 pt;
- rank warm-up 3;
- low/easy = bottom/top third, or ½ of the last same-way leg;
- GC silent 15 s, stall 80% and BK/3;
- roll window 5 sessions.

**Amendments to signed engines:**
- (a) fold's FLOW row sourced from R-13;
- (b) fold's OI watch labels the expiring series on expiry afternoons (the "22650 PE off, −36.5%" misread);
- (c) THE DAY replaced by R-14;
- (d) the `fire` tolerance in B points, not chart rows (her choice).

**Owed separately:**
- session end 15:40 (P0);
- Oct subscription;
- `tape_log` revisions.

---

## 8. Self-score, honestly

| Item | Score | Why |
|---|---|---|
| R1 leg segmentation | **Pass** | δ = 3B, volatility-scaled, deterministic; 29 Sep names the afternoon as a range with named sub-legs. **But it starts at 12:33, not 13:30.** That is the honest structure; the 13:30 window sits inside it |
| R2 effort vs result | **Pass** | Per leg, both tapes, block-excluded; vs the last same-way leg; rank with n |
| R3 who | **Pass** | "Short covering (or roll) into expiry, absorbed; not new buying" with −11.2k OI. Never "bullish". The "or roll" cannot be dropped on 29 Sep (Oct not recorded), and it says so |
| R4 expiry / roll | **Partial** | Calendar mode, 15:40, combined OI, rollover % and cost are designed. **On 29 Sep Oct was not recorded**, so rolled vs closed and rollover % are CAN'T CHECK. Pass from the next roll window, if the capture is built |
| R5 absorption at a level | **Pass** | 22706–22723, buyers, Δ+704 GC / +848 UX, 6 visits, OFI evidence, "not a reversal" |
| R6 CVD divergence | **Pass** | None at the top (said); 15:22 subsumed; structure-only |
| R7 auction completeness | **Pass (row choice is h)** | Bid × ask at the extremes; unfinished 22723 labelled Sep and dead at 15:40 |
| R8 initiative / responsive | **Pass on 29 Sep** | All day below prior value; contract-checked; "tulna nahi" after a roll |
| R9 stacked imbalances | **Partial** | Evidence-only via `prints.py` at a fixed row; I did not verify stack placement on the 29 Sep afternoon in the replay |
| R10 profile shape | **Partial** | Names D (POC 22685 at about 58–64% of the range), not P. Honest, but the shape rule is coarse |
| R11 options side | **Partial / weak** | fold's named walls plus the expiring-series label. **Next week's series was not in the 29 Sep chain**, so "carries forward" cannot be read. No synthetic-forward read designed here |
| R12 VPIN | **Pass** | fold's row, captioned, never flips a read |
| R13 self-calibration | **Pass** | No lot counts; ranks with n; warm-up said; B and σ from fold's rule |
| R14 persistence | **Pass** | Append-only log, stable IDs, named-reason changes, same-print rule, P negation |
| R15 sequence over bars | **Pass** | Blocks screened; demotion inside a RANGE. Standalone traps in the 13:30–15:30 base that the leg read does not support: 0 |
| R16 tapes | **Pass** | Per leg; SPLIT removes the aggressor; GC-down → "1 tape" |
| R17 day story | **Pass** | §6 |
| R18 position-relative | **Pass** | 13:45 hypothetical long: FLOW WITH, WHO "no new longs", ZONE under the ceiling, VPIN captioned, no candle close |
| H1 no edge claims | **Pass** | Counts with n only; no rate anywhere |
| H2 observed vs inferred | **Pass** | Δ-prefixed numbers + legend on the face; tags in the wire |
| H3 holes visible | **Pass** | R-01; short bars; hatched spans; REST-filled minutes tagged |
| H4 warm-up | **Pass** | "Garam ho raha k/3" |
| H5 as-of | **Pass** | `at` / `data_asof` on every event; append-only |
| H6 contract identity | **Pass** | Contract on every number and level; the automatic expiry caveat |
| H7 "no read" | **Pass** | SPLIT, CAN'T CHECK, "dono taraf barabar" |
| H8 anytime start | **Pass, with a labelled gap** | UX side and OFI cannot be rebuilt for a server-down gap; labelled |

**What our data can never reach** (the design does not pretend otherwise):
- the true aggressor on any trade;
- GoCharting's side method;
- icebergs, spoofing, and cancels vs fills;
- who opened or closed (participant identity);
- separating spread/roll prints from directional prints inside the near month (only Oct OI, after the fact, can split them);
- the cash closing auction;
- SENSEX depth parity;
- the exact derivatives settlement formula (sources disagree).

A single-day story also cannot validate any threshold. The (h) numbers above are pre-registered and replayed only for truthfulness, never for edge.

---

## Rev 2 (2026-09-29, night): after the Oct candles and the cross-critique

**Status.** This is an addendum; §0–§8 above stay as written, for the record. Where Rev 2 disagrees, **Rev 2 wins**.

**Sources.**
- Oct and Sep 1-minute candles: `docs/reader/data-2026-09-29/fut_{SEP,OCT}_1m.json`.
- Replays: `...\scratchpad\designB\octs.py`, `volcmp.py`, `unfin.py`.
- The critique of the other design: `5-critique-by-opus.md`.

### R2.1 Retractions: what Rev 1 said that the Oct data falsifies

| Rev 1 said | Where | Why it was wrong | Now |
|---|---|---|---|
| "Not new buying. Sep closing flow, not direction." "It never says bullish." | §0 item 12, §6 at 15:40 | It is true **for Sep only**. Over 13:30–15:29 Oct shows +69 pts and OI +25,726 lots. The Oct−spot basis went 149 → 162, peaking at 189 at 14:30. Combined Sep + Oct OI was +14,935. On the ordinary OI table that is **new longs in Oct**. | The curve line (R2.2) names it. |
| At 14:00: "Sirf ghumaav · OI flat" (rotation, flat OI) | §6 14:00 | That is flat for Sep (−537), but from 12:34 to 13:59 Oct added +9,658 lots with price +32. | "Oct mein naye long · +9.7k" at 14:00 |
| "22706–22723: kharid dabi … absorbed here" read as supply over the market | R-06, §6 | Correct as a **Sep-tape** description. The same level in Oct terms (22720 + the 12:57 spread of 146 ≈ 22866) was exceeded in Oct: 22905.5 at 15:32. The cap was Sep-only. | R2.4 |
| The afternoon's "heavy buying, little progress", read as all passive supply | R-03, R-04 | Sep−spot went 14.2 → −1.9 over 13:30–15:29. About **16 of the missing points are expiry convergence**: spot rose +56.5, Oct +68, Sep +46 close-to-close. | R2.3 |
| The 10:07 block: "a position opened in one print" | R-10, §6 10:10 | The print is absent from the exchange's regular 1-minute candle (684 lots, vs 5,990 in `vtt`). Oct OI stepped +5,134 in the same minute as Sep's +4,651. It is a spread/roll-type print [I]. | R2.5 |
| The ROLLED/CLOSED rule needed "Oct delta negative" | R-05 | The only Oct source we have (REST) carries no side. The rule also imagined only shorts rolling or closing. | R2.2 |
| Finished = "one side is 0" at the extreme row | R-11 | Not the research's wording, which is: finished iff the **losing** side is 0. My version called 44 of 76 extremes (6 days) "finished" where the losing side traded. | R2.7 |
| δ = 3 × B(t), moving with the day | R-02, D5 | It rose to 50 at 09:42 on the wide open, which declared the morning base late (11:02). | R2.6 |

**Vocabulary stays.** No adjective "bullish" or "bearish" is added. But the curve sentence must now say what Oct's own OI table says. Rev 1 would have left it at CAN'T CHECK even with Oct captured, because its rule had no word for this case.

### R2.2 R-05 rewritten: the curve read, without next-month delta

**Inputs:**
- Sep and Oct 1-minute price, volume and OI [M].
  - Live: the `futs[1]` subscription in the roll window.
  - Fallback and anytime start: the Upstox REST 1-minute candles, polled once a minute and pulled at the close. They are proven to exist for the current day (the 29 Sep pull; 385 bars each).
- Spot from the chain (`spot` field), for the next month's basis.

**Per window** (each leg, each auction, and on expiry day fixed 30-minute blocks):

| Quantity | Definition | Tag |
|---|---|---|
| ΔSep, ΔOct, **Net** = ΔSep + ΔOct | Lots, each against its own contract's 3σ₁√n | [M] |
| **Oct state** | Oct's own price × OI table, with no aggressor: OI↑ price↑ new longs; OI↑ price↓ new shorts; OI↓ price↑ covering; OI↓ price↓ liquidation. Price within δ counts as "price flat → positions added / removed". | [I] |
| **Roll-side witness** | Change in Oct−spot basis. Use Oct−Sep only when spot is missing; on expiry day it is contaminated by Sep's convergence. **Richening** = Oct bought against the index (long roll or new Oct demand). **Cheapening** = Oct sold (short roll or new Oct supply). Threshold: ≥ 2 × the robust σ of today's 30-minute basis changes (h). On 29 Sep the 30-minute spread σ was 9.5 pts, so the bar was 19. | [I] |
| **Rolled** ≈ min(−ΔSep, ΔOct) when both moved; **Net new** = Net | | [I] / [M] |

**Classes:**

| Class | When | 29 Sep example |
|---|---|---|
| **PURE ROLL** | Net within noise, both legs moved | 15:01–15:29: Sep −7,972 → Oct +8,476; Net +504. "Positions moved to Oct, none added." |
| **ROLL + BUILD** | Net significantly > 0. The side comes from the Oct state, and the basis confirms or contradicts. | 13:30–15:29: Net +14,935; Oct new longs (+69, +25,726); basis 149 → 162, and 189 at 14:30: confirms. |
| **ROLL + CUT** | Net significantly < 0 | 09:15–09:38: Net −483 (within noise) → PURE ROLL |
| **CLOSED** | Sep down, Oct flat | Not seen on 29 Sep |
| **MIXED** | The Oct state and the basis witness disagree. Said so, with no side. | 09:15–09:38: Oct −133 on OI +3,406 (new shorts by the table), yet Sep sold harder (spread 116 → 143). |

**Output (13:30–15:29):**
> **EN:** Sep: shorts covering, absorbed on the Sep tape (closing flow; expiry convergence 16 pts). Oct: new longs, OI +25.7k, +69 pts; basis 149 → 162 (189 at 14:30): Oct was bought. Combined +14.9k: about 10.8k moved out of Sep, 14.9k net added. Positions were built long into October [I].
>
> **Chip:** Oct mein naye long · +25.7k · Sep sirf cover

**Rollover %:**
- (Oct + Nov) ÷ (Sep + Oct + Nov).
- Nov is not pulled yet, so today it prints **"Oct share 60.5% → 70.9% (09:15 → 15:39), Nov not included"**.

**On a hole:**
- A missing Oct minute makes that window **CAN'T CHECK ("Oct 1-min missing hh:mm")**.
- The Oct side is **never** inferred. The REST candles carry none, and the table needs none.

**Where it shows:** on roll and expiry days the contract line on every face becomes this curve line. Sep's who-state stays in the leg line, scoped "Sep".

### R2.3 Expiry convergence in effort vs result

- On expiry day, the expiring contract's progress in R-03 is **spot progress** = ΔSep − Δ(Sep−spot). The sentence states the convergence.
- 13:30–15:29: Sep +46.1, spot +56.5, convergence 16.1. Efficiency uses 56.5, not 46.1.
- The afternoon is still the least efficient stretch of the day on both tapes, but less extreme than Rev 1 said.

### R2.4 Expiring-contract levels, checked in next-month terms

- A level on the expiring contract carries "Sep-only".
- The reader translates it with the live Oct−Sep spread. If Oct trades beyond the translated level while Sep is held, it appends **"cap sirf Sep ka hai (roll / convergence)"**.
- 29 Sep: 22723 Sep at 12:57 (spread 146.1) translates to about 22866 Oct. Oct traded 22905.5 at 15:32 while Sep held 22714–22716.

### R2.5 Spread-leg witness, and blocks

- **Per minute:** spread-leg volume estimate = `vtt` volume − exchange candle volume [I].
- **29 Sep:**
  - 16,568 lots over the day, 22% of `vtt`, median 20 lots a minute;
  - 10:07 alone: 5,306 lots.
- **A block is a spread/roll print** when either:
  - (a) the print is absent from the exchange candle; or
  - (b) the next month's OI steps by at least half the print within 2 minutes.
- Such a block is labelled **"spread/roll print · disha nahi"** and excluded from Δ (by print, not by bar; see `5-critique` W9).
- The 15:00 block (2,002 lots) **is** in the candle (2,245 of 2,302 lots): a regular-market print, excluded from Δ but labelled a plain block.
- **Hypothesis:** the 22% share is the spread book [I]. It is verified on one day only. Pull the candles for the next five sessions before any read relies on it.

### R2.6 δ frozen at the open (adopted from the other design)

- δ = 3 × PRIOR_B (fold's prior-session median 1-minute range), stamped at 09:15 and **never moved intraday**. 29 Sep: 29.4.
- **Replay on the recorded minutes:**
  - 29 Sep:
    - the morning base is declared at **10:02**, not 11:02;
    - a top range 22713.5–22748 (12:00) breaks down at **12:27**, three minutes before Rev 1's trend break;
    - the afternoon range is declared at 13:02;
    - 29 legs.
  - 28 Sep: unchanged (TREND ▼ → PAUSE → RANGE → breakdown 14:18).
  - 22 Sep: breakdown 12:55 (was 13:00).
- **Supersedes** R-02's "self-calibration" cell and D5's first bullet. B(t) still drives fold's own units, untouched.

### R2.7 R-11 corrected: finished / unfinished

- The research's wording applies: **finished iff the losing side** (buyers at a high, sellers at a low) is 0 within 1.0 pt of the extreme.
- On six Tier-A days that marks **64 of 76** extremes unfinished. It does not discriminate.
- **Drawn:** only **"two-way at the extreme"**, i.e. both sides > 0 (20 of 76). Chip **"Do-taraf high 22723 · Sep"**.
- Everything else lives in the leg table only. No carried level lines otherwise.
- R7 → **partial**.

### R2.8 Adopted from `4-design-fable.md`

- **Extension heartbeat** in every POST: `{tab_visible, ctx_alive, last_tick_ms}`. R-01 names the cause: discarded / orphaned / stalled. The Upstox-volume cross-check stays as the independent witness.
- **Sub-δ pullback named while it happens:** "Pullback · −18 / δ 29 · bikri nahi aayi" on the forming with-leg. It stays WITH for the FLOW row.
- **P/A/E/C computed in TapeMap**, with the extension drawing only. The parity gate is by **event id** (bar t, kind, price) on the seven `ofd_marks` days, with every difference listed for her. This supersedes §4.1's "keep board.js in the page".
- **Options confirmation (R11):** per-strike ΔOI at 2 strikes around the window, and the synthetic forward vs the future; the expiring series labelled.
  - Verified 13:30→15:29: 22600 PE −224,463 lots, 22800 CE −120,463, 22700 PE +45,448.
- **A regime test that swaps the dump's expiry date. Backfilled marks drawn hollow** (`.b`).

### R2.9 29 Sep: corrected walk-through lines (additions to §6)

| As of | Curve line added (Rev 2) |
|---|---|
| 09:35 | Oct −133 on OI +3.4k (new shorts by the table), but Sep sold harder (spread 116 → 143) → **MIXED**. Net −0.5k → **PURE ROLL** during the drive. |
| 11:10 | Base 09:39–11:09: Sep OI −8.6k, Oct +12.8k at +37 pts, Net +4.2k → **ROLL + BUILD**, Oct price flat-to-up (within δ) → "positions added in Oct". Basis flat (143 → 140). |
| 12:05 | Grind 11:15–12:01: Oct +65 on OI +4.2k → **new longs in Oct**; spread 131 → 142. The Sep read "short cover · mehnat zyada" stays, scoped Sep. |
| 12:30 | Reversal 12:02–12:33: Oct −109 on OI +5.1k → **new shorts in Oct**, Net +3.8k. |
| 14:00 | 12:34–13:59: Sep OI −0.5k; **Oct +9.7k at +32 → new longs in Oct**; Net +9.1k; basis flat (144 → 143) → the side is from the table only. Rev 1's "OI flat" was Sep-only. |
| 15:00 | 12:34–14:59: Oct +22.3k at +56, Net +18.0k, spread 144 → 165 (above the 19-pt bar) → **ROLL + BUILD, new longs in Oct, basis confirms**. |
| 15:01–15:29 | **PURE ROLL** (Sep −8.0k / Oct +8.5k). |
| 15:40 | See the curve sentence in R2.2. Sep's line: "short covering, absorbed on the Sep tape; 16 pts of convergence; the 22723 cap was Sep-only (Oct 22905.5 at 15:32)". |

**Day story, final clause:**
- **Rev 1:** "rolled vs closed CAN'T CHECK".
- **Rev 2:** "Oct OI +58.5k on the day against Sep −26.7k (combined +31.8k). The morning built both ways in Oct; the afternoon built longs in Oct with the basis richening, while Sep's shorts covered into a convergence-capped expiry."

### R2.10 Self-score changes

| Item | Rev 1 | Rev 2 | Why |
|---|---|---|---|
| R3 | Pass | **Pass on Sep; partial on the curve** | Rev 1 called the market from Sep. R2.2 fixes it where Oct is captured. |
| R4 | Partial | **Pass-able** | REST Oct candles make the curve read, anytime-start and rollover-without-Nov possible. Live subscription is still owed for Oct side and depth. |
| R5 | Pass | **Pass, with the Sep-only qualifier** (R2.4) | |
| R7 | Pass | **Partial** | R2.7 |
| R11 | Partial / weak | **Partial** | R2.8 |
| H6 | Pass | **Pass** | Every number and level now names Sep or Oct, and the curve line never splices the two. |

**New owed item:** pull the Sep/Oct/Nov 1-minute candles for the next five sessions, to test the spread-leg hypothesis (R2.5) on more than one day.
