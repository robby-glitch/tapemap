# The decoder: an order-flow reader for her GoCharting chart, designed from first principles — Fable, 2026-10-04

Read-only in both repos. The only file written is this one. Probes ran in my scratch area (`decoder.py`). **[M]** measured on
recorded bars; **[I]** inferred. Rows and narrative, never a rate.

**Reading order, stated for honesty.** Before drafting §1–4 I read: the root-cause note (`orderflow-desk/docs/ROOTCAUSE-big-
prints-2026-10-04.md`), the capture side (`src/engine/adapter.js`, `src/engine/session.js`, the POST lines of `src/shell/main.js`),
`frame.py`'s docstring and tape fields, and the raw bars in `tapemap/data/tape/`. I did **not** read `board.js`, `overlay.js`,
`taps.js` or `decode.js` before §1–4 existed. I had read, earlier today in a different task, the first section of
`docs/reader/7-final-design.md`, `reader.py`'s docstring and a grep of `1-research.md`; §5 says where that may have coloured me.

**What exists to decode (from the capture code, [M]):** per closed 5-minute bar of NIFTY-I: `o h l c`, `vol buy sell delta` in
lots, `oi` in contracts (joined from GoCharting's OHLC stream), and the ladder `[{p, b, s, bt, st}]`: per price, buy lots, sell
lots, buy trades, sell trades. `maxDelta`, `minDelta`, `buyTrades`, `sellTrades` are captured and dropped at the POST (one line
to keep). Bars built from ticks replace snapshots; a bar joined late is `partial` and not closed. Volume agrees with Upstox
within 0.1% on every checked bar. The side is GoCharting's own classification (method undisclosed; closer to a quote rule).
Beside it, TapeMap holds: the chain (per-strike OI, ltp, avg, iv), the warmap level stamps, her zone machine, the index spot
(basis), and for 30 Sep / 1 Oct the reader's legs. **Not available:** the exchange-tagged aggressor, order-level data
(icebergs, cancels), SENSEX / BANKNIFTY futures flow worth reading, and — the finding below — a futures OI change that can be
trusted at the bar it prints.

---

## 1. What an experienced order-flow trader reads, in order

The order is not optional. Each step narrows what the next one can mean; read out of order, "absorption" and "positioning"
look identical, which is exactly the inversion that happened.

**0. Before the bar — where am I.** Band position (her d2–d3 / u2–u3 ring; I use σ of the session hlc3 VWAP), the nearest
previous-day level (PDH / PDL / PDC / OPEN / PWH / PWL / major round) **in futures space** (index level + basis), time of day
(the first 30 minutes are their own regime; 15:15 freezes spot), the DTE of the options book, and what the session has been:
balance (closes inside ±1σ, the leg rotating) or imbalance (closes beyond ±2σ with initiative). A print at a level is a
different object from the same print in the middle of nowhere.

**1. The bar's result.** Range against the session's median range; where the close sits in the range (upper third, middle,
lower third); did it close through the level. Result first, because effort is judged against it.

**2. Aggression — who crossed the spread.** Delta against the session's median |delta|; **big prints** (one cell far above the
session's median cell, one-sided, a large share of the bar, with its **trade count**: one to six trades is one hand, thirty
trades is a crowd); **stacked imbalances** (three or more diagonal 3:1 rows in a run, each row at least a median cell); and
where in the bar the aggression sat (top rows or bottom rows). Aggression says who was impatient. It says nothing yet about
who is right.

**3. Commitment — did positions open or close.** The OI quadrant on the bar: aggressive buying with OI up = new longs (and a
passive new short on the other side); aggressive selling with OI up = new shorts; buying with OI down = short covering;
selling with OI down = long liquidation; |delta| small with OI up a lot = **two-sided build** (a fight, both committed); OI
flat = rotation. **This is the step that tells absorption from positioning**, and it has a guard: when a bar's |ΔOI| exceeds
the bar's own volume, the exchange has published a step, not positioning — the bar reads **"OI: publication step, can't
check"** and the quadrant is taken over the window from the last clean bar to the next clean bar. On the two prints she
asked about, this guard fires on the very next bar: 29 Sep 10:05 **+269,425 contracts** then 10:10 **−336,505 on a bar of
32,565 contracts**; 30 Sep 12:50 **+192,660** then 13:00 **−190,840 on 12,090 contracts** [M]. The two-bar net is ≈ 0 both
times. So "new longs / new shorts" was **not confirmable from the futures OI at the print bar**, and a decoder that prints
"naye short" there is guessing with a confident face. What *is* [M] at the bar: the size, the side, the hand count, the
location. The direction is earned by step 6.

**4. Effort versus result.** Points moved per 1,000 lots of |delta|, ranked against today's earlier bars (the Kyle-style
rank; Amihud for unsigned volume). A hard bar (bottom decile) at a level means one of two things, and only step 3 separates
them: positioning (OI up: someone is building at the level and the passive side is committed) or absorption (OI flat or
down: the aggressor's prints were met by closers and the aggressor is spending, not building). A hard bar in the middle of
the range is just a quiet market.

**5. The extremes of the bar.** Finished or unfinished auction at the high / low (the extreme row one-sided = finished;
both sides printed with at least a median cell = unfinished, the market will likely come back to it); **exhaustion** (the
two rows at the extreme in the bar's direction carry ≤ 25% of the bar's POC row while delta was large: the move ran out of
participants). Only on the bar that made the leg's extreme, or at a band / level; everywhere else these are noise.

**6. Across bars — the sequence, and what became of the last print.** CVD against price **at swings only** (a new 6-bar high
with CVD not making a new high); the trap sequence from the framework (LEVEL reached → DWELL with effort-without-result and
the options book loading → INDUCE, the break with aggression → FAILURE, the close back through with the other side's OI
quadrant → RELEASE, the forced side covering with the tape one-sided → TARGET); and the ledger of **open prints**: a big
print becomes a level with two exits — "the printer is trapped if price closes beyond his price by more than the session's
median range; the passive side is trapped if price leaves the other way" — and the decoder keeps saying **"confirm baaki"**
until one exit fires. This is where the 29 Sep buyer (level 22,599, tested to 22,590 for 15 minutes, confirmed at 10:40 when
ROUND 22,600 was reclaimed) and the 30 Sep seller (level 22,905, price sat 0–9 points above him for 15 minutes, confirmed
only when 22,834 printed at 13:40) are decided — **after the fact**, and said so in real time.

**7. The options book.** The sides read: which writers are the fuel, covering at POWER, forced (`ltp > avg`), first sign or
continuation, how much fuel is left. On 1 Oct the 12:05 bar's print (S 475, 3 trades, new shorts) and the options slot (PE
writers covering at POWER, forced 2/2) are the same event seen from two books; on 30 Sep 12:50 the options book was FLAT —
the seller was alone, which is also information.

**8. Cross-index — price extremes only.** Did NIFTY, SENSEX and BANKNIFTY each take their own previous swing at this push
(TOOK / EQUAL / FAILED)? Never cross-index delta: SENSEX's future printed 4 lots a minute on 1 Oct; BANKNIFTY's effort per
result runs 10× NIFTY's. A lone new high in one index at a level (BN at 10:36 on 1 Oct) is the induce's signature.

**Noise on NIFTY-I 5-minute, said plainly:** a single bar's delta sign (the two tapes disagree on 31% of bars, and the side is
a vendor inference); bar-level delta divergence (price up on negative delta happens every few bars as passives lift it);
imbalances and stacks away from a level or band; unfinished auctions on extreme rows of one or two lots; exhaustion flags
on ordinary bars (my probe flags one on about half the bars until gated to band / level); "absorption" judged by the move
inside the print's own bar — the inversion itself; the OI change of a single bar without the publication guard; naked
POCs older than yesterday; VPIN as an entry (it confirmed 15–20 minutes late on every leg I checked); the opening 30 minutes
read against the session's own scale (every ratio is "warm", and the 09:15 bar's OI change is against yesterday's close);
anything from the SENSEX or BANKNIFTY futures tape; max / min delta (not posted, and a chase signal at best).

---

## 2. The decoder

Five layers, each pure, each with a stated absence. The face formats; the decoder decides. One sentence in English for the
engine, chips in Hinglish for the screen.

### 2.1 Raw cells

Per closed bar: the ladder rows (price, buy lots, sell lots, buy trades, sell trades), the bar totals, the OI. Derived once:
session running medians of the non-zero cell, the bar volume, the bar range, |delta|, and the effort-per-result series; the
session hlc3 VWAP and σ; the session profile (volume at price → POC, 70% value area, HVN / LVN); CVD. Warm-up = 6 closed
bars; before it every ratio prints `warm`, never a reading.

### 2.2 Events — exact, scale-free definitions (every number is the session's own)

| event | chip | definition | needs | can be confirmed only after |
|---|---|---|---|---|
| **E1 BIG PRINT** | `BADA BUYER / SELLER <K> @<p> · <n> haath` | one cell: `max(b,s) ≥ 50 × median non-zero cell`, `≥ 25%` of the bar's volume, one-sided `≥ 0.80`. Side = the aggressor (the larger of b, s). Carries lots, trades, price, bar ΔOI with its guard state, z, nearest level | ladder, OI | the two exits (step 6): printer trapped = close beyond his price by ≥ median range; passive side trapped = price leaves the other way by ≥ median range. Until then `confirm baaki` |
| **E2 INITIATIVE** | `PEHAL ▲/▼ · naye / covering` | `|delta| ≥ 2 × median |delta|`, `range ≥ median range`, close in the directional third; OI quadrant names it `naye` (ΔOI same sign ≥ 0.5 × |delta| in contracts) or `covering` (opposite sign) or `rotation` | bar, OI | the leg's next bar (a close back inside the bar's range within 2 bars = failed initiative) |
| **E3 EFFORT WITHOUT RESULT** | `DABAAV · positioning` or `DABAAV · absorbed` | `|delta| ≥ 2 × median |delta|` and (`range ≤ median range` or close in the opposite third). Then **by OI only**: ΔOI same sign ≥ 0.5 × |delta| → *positioning at the level* (the passive side is the trapped candidate); otherwise → *absorbed* (the aggressor is spending). Never from the move alone | bar, OI with guard | the next clean OI bar (publication step) and the level test |
| **E4 STACK** | `DHER ▲/▼ <rows>` | ≥ 3 consecutive diagonal imbalances, each `≥ 3 : 1` against the row diagonally opposite, each row `≥ median cell`; **emitted only at a band (|z| ≥ 1.5) or within one row of a level, or on the leg's extreme bar** | ladder | the next bar closes beyond the stack (held) or back through it (trapped) |
| **E5 UNFINISHED** | `KHULA upar / neeche` | the bar's extreme row printed both sides with total `≥ median cell`; **only on the bar that set the leg's extreme** | ladder | revisit of the extreme |
| **E6 EXHAUSTION** | `THAKAAN ▲/▼` | the two rows at the extreme in the bar's direction `≤ 25%` of the bar's POC row, with `|delta| ≥ median |delta|`; **only at a band or level** | ladder | the next bar fails to extend |
| **E7 CVD DIVERGENCE** | `CVD ulta` | a new 6-bar swing close beyond the previous swing while CVD is not beyond its value at that previous swing; **only at a band or level** | bars | the swing holds for 2 bars |
| **E8 OI QUADRANT** | `naye long / naye short / covering / liquidation / dono taraf / rotation` | per bar in contracts: `|ΔOI| > volume` → **publication step, can't check** (and the quadrant is read over the window to the next clean bar); `|ΔOI| ≥ 0.5 × |delta|` same sign → naye long/short; opposite → covering/liquidation; `|delta| < 0.1 × vol` and `ΔOI ≥ 0.3 × vol` → **dono taraf naye** (two-sided build); else rotation | bar OI | the next clean bar |
| **E9 LEVEL STATE** | `PDC 22620 · toota / FAILED / ruka` | the warmap sequence at PDH/PDL/PDC/OPEN/PWH/PWL/major rounds, in futures space via the basis | warmap, basis | FAILED is by definition after the fact |
| **E10 BOOK** | `PE writers kaat ×9 · forced 2/2 · pehla` | the sides-3 slot: fuel side state, POWER, forced, first sign / continuation, fuel left | chain | the slot closes 1–3 min after the trades |
| **E11 PROFILE** | `POC 22650 · LVN 22620–22635` | session POC, 70% value, HVN/LVN from the cumulative ladder; yesterday's POC naked until straddled | ladders | context only, never an event |
| **E12 SAATH** | `BN naya high akela` | xindex X2 per-index TOOK/EQUAL/FAILED at the push | spot of the three | the bar close |

Everything else the footprint literature offers (delta-flip bars, "trapped traders" from one bar's close, POC migration
inside a bar, min/max delta) is left out on purpose: either not posted, or noise at this resolution, or an inference the OI
already makes honestly.

### 2.3 Context

Per bar, attached to every event: `z` (hlc3 VWAP σ), her ring (`d2–d3` / `u2–u3` from the extension's bands), the nearest level
in futures space with its state, time band (`subah` ≤ 10:30, `dopahar`, `band hone wala` ≥ 14:30, `15:15 se check nahi`),
the DTE of the options book and its expiry-day tag, the profile location (at POC / in value / at an LVN), and the auction
state (balance / imbalance, from the last 6 closes against ±1σ / ±2σ).

### 2.4 Participants

From E1 + E8 + E10, in these words only: **naye** (new, from the quadrant), **phanse** (trapped: the passive side of a
positioning print once price leaves against them; the aggressors of an induce once FAILED stamps), **forced** (option writers
underwater and covering, from the book; futures holders by a stop run through a level), **spent** (an aggressor whose prints
were absorbed: OI flat with effort and no result). Each participant word carries the number it came from (lots, contracts,
strikes) and a `[I]`.

### 2.5 The story

The framework's sequence runs as a small state machine per level: `LEVEL → DWELL → INDUCE → FAILURE → RELEASE → TARGET`,
advanced only by events above (DWELL by E3/E8 two-sided + E10 loading; INDUCE by E9 BREAK with E2/E4; FAILURE by E9 FAILED
or the E1/E4 exit; RELEASE by E10 POWER forced + E2/E1 the same way; TARGET by E9 RUN → HIT with the E8 class on the leg).
The open-print ledger rides beside it: every E1 stays a level until an exit fires.

### 2.6 One sentence, three chips

The engine's sentence (English, logged): *"Big seller 198K at 22,905 in 6 trades at the upper band above PDH; OI +193K on the
bar, reversed next bar (publication step) — new shorts unconfirmed; price holding 0–9 pts above him; options book flat."*
The screen: at most **one line and three chips**, newest event first, ranked by (level proximity, size × median, confirm
state): `BADA SELLER 198K @22,905 · 6 haath · upar band` · `OI confirm baaki` · `book chup`. When an exit fires the chips
change, never the history: `seller ka level hold · neeche 22,834 (13:40)` or `seller phansa · 22,925 ke upar close`.

### 2.7 Saying "unconfirmed" honestly

Three states on every event, carried as a field and a chip: **LIVE** (just printed, [M] facts only), **CONFIRM BAAKI**
(the direction read depends on a later bar — the OI step, the level test, the swing holding), **CONFIRMED / FAILED** (the
exit fired, with the bar that fired it). The decoder never upgrades a chip silently: the sentence that said "confirm baaki"
at 12:50 is still in the ledger when 13:40 confirms it. Which events are after-the-fact by nature: every E1 direction, every
E3 split (needs the next clean OI bar), E4/E5/E6 (need the next bar), E7 (needs the swing to hold), E9 FAILED, E10 (the slot
closes late). Only the raw facts of E1/E2/E8 are LIVE at the bar.

---

## 3. The face on GoCharting

**Line budget (strict): at most 7 drawn objects on the chart at any time, excluding GoCharting's own bands and the feed
band.**
1. The nearest previous-day level in play (one line, its chip: `PDC 22,620 · ruka 70 min`).
2. The newest **open big-print level** per side, at most one above and one below price (a short horizontal from the print bar
   to now, in the **aggressor's** colour, never the defender's; chip `BADA SELLER 198K · confirm baaki`).
3. One **active stack box** at the current leg's extreme (removed when the leg ends).
4. **At most three event glyphs**, only for events that are at a band / level or OI-confirmed, newest three; older glyphs
   leave the chart and live in the panel ledger.
5. The feed band (DEAD/SLOW), which is integrity, not a read.
No arrows on price, no redrawn candles, no time stamps on the chart (the panel ledger carries times), no text longer than a
chip. Glyph grammar: ▮ print, ≡ stack, ⌐ unfinished, ∧ exhaustion, ◇ level state; two hues plus grey (blue buyers, vermilion
sellers, grey reference / unconfirmed); light theme. **Chips toggle** (her rule: every glyph carries a Hinglish chip with its
number; off, the glyph alone; on, the chip). The panel holds the sentence, the three chips, the open-print ledger with
states, the OI quadrant of the last 6 bars as six small words, and the trap state line. The DESK gets the two lines it already
owns from the trap framework (fuel side / forced / weekly) plus one: `upar: 22,905 bada seller baitha (confirm baaki)`.

---

## 4. Tested on recorded bars (rows from `decoder.py`; definitions fixed before the rows were read)

Each line is what the decoder would have **said at that bar's close**, with its state. `×c` = multiples of the session median
cell; `lam` = points per 1,000 lots of |delta| and its rank among today's earlier bars (0 = hardest); `z` = hlc3 VWAP σ. The
options slot is the analysis `sides.py` word for the 5-minute mark closing that bar.

### 4.1 1 Oct 09:15–13:00 (gap −36; PDL 22,601 / PDC 22,620 index = ~22,712 / ~22,731 futures)

- **09:15–09:40** `warm` on every ratio. Facts only: 09:20 delta −357 with OI +237 lots → *naye short on the drive to the
  low*; 09:25 +187 / OI +138 → *naye long on the bounce*; 09:30–09:40 rotation. Sentence: "Opening drive to 22,606, new
  shorts, bought back by new longs; scale warming."
- **09:45–09:55** `z +1.6 → +2.2`, small bars, OI +126 / +188 with negative delta → *naye short at the upper band*; **09:55
  exhaustion ▲** (top rows thin) with lam rank 0.83. Sentence: "Price at the upper band on thin buying; shorts opening."
- **10:00** vol 1.6×, delta +291 (2.0×), **stacks B3**, close 22,694 at the previous day's low in futures space, `z +2.87`,
  **OI +42 → rotation**, lam rank 0.29, exhaustion ▲. Sentence: *"Buy stacks into PDL/PDC at the upper band on no new OI —
  a covering push, exhausted at the top; book: call writers covering, puts adding (REAL)."* State: CONFIRM BAAKI (an
  initiative that opened nothing). Chips: `DHER ▲ 3 · OI nahi (rotation)` · `upar band z+2.9 · PDL/PDC` · `THAKAAN ▲`.
- **10:05** rotation, OPEN HIT behind; **10:10** delta −297, **OI +325 → naye short**, lam rank **0.00**, `z +0.33`:
  **E3 DABAAV · positioning** — heavy selling, price barely moved, OI up: shorts built at the top, the passive longs are
  the trapped candidates. Chips: `DABAAV ▼ · naye short 325 lots` · `confirm baaki` · `book: CE likh rahe (BACKED)`.
- **10:15–10:25** small bars, OI up each (+149, +102, +212) with flat delta → *dono taraf / rotation*: the dwell loading.
- **10:30** delta +200 (2.2×), **OI +139 → naye long**, stacks B2, `z +1.51`, high 22,697 against 10:00's 22,702:
  **second push, equal high, this time with new longs** — the induce's takers. Sentence: *"Second push to the same high
  with new longs and buy stacks; the first push had none — buyers now committed at the top."* Chips: `PEHAL ▲ naye long` ·
  `dohri choti 22,700` · `book SQUEEZE (CE kaat)`.
- **10:35** rotation; **10:40** `OI publication step: can't check`; **10:45** delta −218 (2.8×), **OI +194 → naye short**,
  lam rank 0.00, exhaustion ▼, `z −0.14`: **E3 positioning again, now below VWAP** — "the new longs of 10:30 are 40 points
  underwater; shorts adding into them". **CVD −932 while price is back where it was at 09:45: effort without result for an
  hour.** Chips: `DABAAV ▼ naye short` · `10:30 ke long phanse (−40)` · `book FAKE`.
- **10:50–11:30** vol 0.2–1.4×; OI +126, +39, +79, **+181 (11:05, naye short)**, +89, +29, **+177 (11:20, naye short, z −1.68)**,
  +124, +81. Sentence repeated with the count: *"Dwell: shorts adding on every down bar, longs rotating; nobody has
  released; book: call writers adding every slot (CAPPED/BACKED)."* The trap machine: `DWELL · PDL/OPEN ke beech · CE likh
  rahe 6 slots`.
- **11:35–11:40** two up bars, **OI +72 / +65 → naye long**, **CVD divergence ▲ flagged on both** (new 6-bar high close,
  CVD −1,233 vs −1,083 at the previous swing), `z +1.06`, lam rank 0.86 (easy): *"Push to a new swing high with less CVD and
  small new longs — divergence at the band; book REAL ▲ small."* State: CONFIRM BAAKI (the swing must hold 2 bars).
- **11:45** delta −106 (2.1×), **OI +133 → naye short**, lam rank **1.00** (the easiest result per effort of the day: price
  fell 24 pts on 106 lots — no bids): **the divergence confirms, FAILED**. Chips: `CVD ulta confirm` · `asar aasaan (rank 1.0)` ·
  `11:40 ke long phanse`.
- **11:50–12:00** rotation, then **12:00 short covering** (+30, OI −158) into the 12:00 high 22,673 = the third push, on
  covering only. Sentence: *"Third push to the high is shorts covering, not buying."*
- **12:05** vol 3.2×, delta −383 (**7.5×**), **BIG PRINT S 475 @22,613 · 3 trades · 119×c · 44% of the bar**, **OI +325 →
  naye short**, `z −1.87` (her lower ring), lam rank 0.12, stacks S2; options slot **REAL: PE writers covering at POWER**.
  Sentence: *"Big seller 475 lots at 22,613 in three trades at the lower band, new shorts on the bar, put writers covering at
  power — release."* Chips: `BADA SELLER 31K @22,613 · 3 haath · naye short` · `neeche band z−1.9` · `PE kaat ×power forced`.
  State: LIVE facts; direction CONFIRM BAAKI → confirmed at 12:15 (close 22,590 < print − median range).
- **12:10** vol 5.0×, **BIG PRINT S 470 @22,581.6 · 1 trade · 118×c**, OI +336 naye short, stacks B2/S1, OPEN BREAK → HIT,
  exhaustion ▼ (the bottom rows thin at 22,575: a pause, not a turn). *"One-hand seller 470 at 22,582 through OPEN; new
  shorts; bottom rows thin — pause likely."*
- **12:15–12:20** delta −346 / −348 (5–6×), **OI +373 / +529 naye short**, **stacks S2 then S4**, `z −2.5`: *"Sell stacks
  below the lower band with new shorts every bar; CVD −2,522."* **12:25** rotation (ROUND 22,500 BREAK). **12:30** delta +162,
  **OI +462 → naye long**, exhaustion ▲, `z −2.07`: *"Bounce bought with new longs at the lower band — these are the trapped
  candidates if the lows go."* (They went: 12:40.) State: CONFIRM BAAKI.
- **12:40** delta −402 (4.9×), OI +234 naye short, **stacks S4**, ROUND 22,500 HIT. **12:45** vol **11.3×**, delta −1,266
  (14.8×), **OI +2,073 → naye short**, stacks B5/S6 (a fight), ROUND 22,400 BREAK, lam rank 0.24. *"Climax bar: 5,062 lots,
  new shorts 2,073, both sides stacked — the stops under 22,500 are being run into the 22,400 round."* **12:50 / 12:55** delta
  −1 / +1 with **OI +1,541 / +637 → dono taraf naye** at ROUND 22,400 HIT: *"Two-sided build at 22,400: a battle, nobody
  winning the bar."* **13:00** delta +797 (9.7×), **OI +818 → naye long**, stacks B5, exhaustion ▲, `z −0.99`, options FAKE
  (CE adding into the bounce): *"Bounce bought with new longs and buy stacks off 22,400; call writers selling it — the
  bounce's buyers are the next trapped candidates."* State: CONFIRM BAAKI (it failed: 13:30–14:04).

**What it caught that the old face did not:** the 12:05 and 12:10 prints as **sellers** at the lower band with OI up (the
board had recorded "buyers defended" ×5 and a climax); the 10:10 / 10:45 positioning bars as shorts building into trapped
longs (the board had absorptions in the buyers' colour); the 11:35–11:45 divergence and its confirmation; the 12:30 and
13:00 bounces as **new longs** (the trapped candidates), not reversals.

### 4.2 29 Sep 09:15–11:30 (NIFTY+BN expiry; gap −67; PDL 22,765 / PDC 22,780 index, far above)

- **09:15–09:40** `warm`. Facts: 09:20 OI −751, 09:25 delta −235 / OI −247 → *long liquidation*, 09:30 OI −956, 09:35 OI
  −1,171 (the 22,580 low), 09:40 +138 / OI −389: *"Longs liquidating on every bar of the drive; nobody opening shorts."*
- **09:45** delta +354 (3.8×), **OI −888 → short covering**, exhaustion ▼ at 22,608, ROUND 22,600 DWELL: *"First covering
  bar; liquidation slowing (−888 vs −1,171)."* **09:50–09:55** rotation, OI −460 / −299. **10:00** `OI publication step
  (−1,559 on 399 lots): can't check`.
- **10:05** vol 4.2×, delta +4,483 (**44.8×**), **BIG PRINT B 4,528 @22,598.8 · ONE trade · 377×c · 70% of the bar**, bar OI
  **+4,145 lots (+269K)**, `z −0.75` (my σ; the extension's −0.94; her chart's lower ring), lam **1 pt per 1,000 lots, rank
  0.00**, exhaustion ▼ (the bottom rows under the print are thin), options slot FLAT. Sentence at the close: *"Big buyer
  4,528 lots at 22,598.8 in one trade at the lower band after four bars of long liquidation; OI +269K on the bar; price did
  not move — positioning or absorbed: OI confirm pending."* Chips: `BADA BUYER 294K @22,599 · ek haath` · `neeche band ·
  liquidation ke baad` · `OI confirm baaki`.
- **10:10** `OI publication step: −5,177 lots on 501` → *"OI: step, can't check; two-bar net ≈ −1,000 lots: new longs not
  confirmed."* Low 22,590 — **9 points under the buyer**, close 22,597 (not through by the median range ~18): *"Buyer's
  level tested, holding on close."* **10:15** +58, OI −323 → short covering: *"Shorts covering above the buyer."* **10:20**
  step. **10:25** +223 (2.2×), OI −398 → **short covering**, exhaustion ▲, lam rank 0.27: *"Covering drive to 22,618; the
  buyer has not been taken out."*
- **10:30** −80 / OI −412 liquidation (small), **10:35** rotation, **10:40** +92 / OI −168 covering, close 22,628, **ROUND
  22,600 FAILED (index)**: *"The break under 22,600 failed; the buyer's level 22,599 confirmed held — shorts covering, no new
  buyers yet."* State for the 10:05 print: **CONFIRMED (held)** at 10:40.
- **10:45** unfinished high at 22,628 (`KHULA upar`), 10:50 rotation, **10:55** +237 (2.8×), OI −315 covering, lam rank 0.07
  (hard): *"Covering into 22,640, absorbed — the auction above 22,628 is unfinished."* **11:00** −148 / OI −315 liquidation,
  exhaustion ▼. **11:05** +92, OI step, stacks B1, options **SQUEEZE: call writers covering at POWER** (CE ×8.9 on NIFTY,
  the 11:15 PUSHTI on all three).
- **11:10** vol 3.7×, delta +1,671 (**18.2×**), **BIG PRINT B 729 @22,651.6 · one trade · 81×c · 31%**, **OI −470 → rotation /
  covering**, stacks B3, `z +1.73`, exhaustion ▲ (the top rows thin at 22,718). Sentence: *"Release ▲: 1,671 lots bought,
  one-hand buyer 729 at 22,652, call writers covering at power on all three indices; OI flat to down — this is covering, not
  new longs; it travels to the next level and should be read as finished there."* Chips: `PEHAL ▲ covering (OI −470)` ·
  `BADA BUYER 47K @22,652` · `CE kaat ×9 · teeno`.
- **11:15–11:20** +107 / +104 with OI −245 / −140 → covering continues, exhaustion ▼ on the pullbacks. **11:25** +465 (4.7×),
  **OI +281 → naye long** (the first new longs of the day), ROUND 22,700 next. **11:30** +219, OI −45 rotation, `z +2.14`,
  ROUND 22,700 BREAK → HIT, exhaustion ▲: *"At the upper band on covering; only 11:25 opened longs; the next level is OPEN
  22,732 (index) — covering-only releases stop there."* (It did: OPEN BREAK 12:07 → FAILED 12:20.)

**What it caught:** the 300K buyer as a **buyer at the low after liquidation**, as a level with a pending confirmation, and
the confirmation at 10:40; the 11:10 release as **covering**, which is why the leg stopped at OPEN.

### 4.3 30 Sep 12:30–13:05 (the 198K seller)

- **12:30** +87 / OI −213 covering, `z +1.91`, PDH 22,753 (index) in play. **12:35** +306 (3.2×), OI −127 rotation, PDH BREAK,
  options PRESSURE ▲ (CE covering POWER). **12:40** rotation, stacks B1/S2. **12:45** +774 (8.1×), OI −349 → **covering**,
  stacks B3, `z +2.63`, exhaustion ▲, PDH HIT, options REAL (CE ×4.3 covering): *"Push through PDH on 774 lots of buying with
  OI down — short covering into the previous day's high, top rows thin, call writers covering at power. A covering release
  at the band."*
- **12:50** vol 6.0×, delta −3,007 (**30.7×**), **BIG PRINT S 3,025 @22,905 · 6 trades · 504×c · 90% of the bar**, bar OI
  **+2,964 lots (+193K)**, `z +1.92`, lam **1 pt per 1,000 lots, rank 0.00**, exhaustion ▼, close 22,914 (**9 pts above the
  seller**), options slot FLAT. Sentence at the close: *"Big seller 3,025 lots at 22,905 in six trades at the upper band above
  PDH, into a covering rally; OI +193K on the bar; price closed 9 points above him — positioning or absorbed: OI confirm
  pending; options book flat (he is alone)."* Chips: `BADA SELLER 197K @22,905 · 6 haath` · `upar band · PDH ke upar` · `OI
  confirm baaki`. **Never** "buyers defended".
- **12:55** −9, OI −85 rotation, close 22,914, high 22,923 (18 above the seller, under his bar's range + median): *"Seller's
  level tested from above, not broken; nobody chased the high (delta −9)."* **13:00** `OI publication step: −2,936 on 186
  lots`: *"OI step: the +193K is not confirmed; two-bar net ≈ 0 — new shorts unconfirmed."* **13:05** rotation, close 22,912.
  State for the print at 13:05: **CONFIRM BAAKI; level held; exits 22,925 (seller trapped) / 22,885 (longs trapped)**.
  Confirmed at 13:40 (22,834) — 50 minutes later, as the framework's exhaustion row (12:50 3/3 ▲ continuation) said.

### 4.4 Where the decoder would be wrong, on these same rows

1. **It would not have said "naye short / naye long" at either marquee print.** The OI step guard fires on the next bar both
   times (§1 step 3). It says the size, the hand count, the location and `confirm baaki`. That is right, and it is less than
   what she read off her chart by eye — her eye used the next 50 minutes.
2. **29 Sep 10:10–10:20:** the buyer's level was 9 points under water for three bars. A trader with a 20-point stop below
   the print survives; the decoder's "holding on close" is correct on closes and silent on the intrabar test. It must show
   the test (`22,590 chhua`) rather than only "held".
3. **1 Oct 12:30 and 13:00:** "bounce bought with new longs, stacks B5" reads bullish if the chips are read alone. The story
   layer (RELEASED ▼ in force, PE covering continuing, CE adding into the bounce) is what says *trapped candidates*; a face
   that shows E8 without the story would mislead. Hence the one-sentence rule.
4. **Exhaustion** flagged on about half of all bars before the band / level gate (1 Oct 09:55, 10:00, 10:25, 10:40–11:00,
   11:10–11:15 …). Gated, it survives at 10:00, 12:10, 12:30, 13:00 and 29 Sep 10:05, 11:10; ungated it is noise.
5. **Stacks B3 at 1 Oct 10:00** look like buyers in control at the top; only the OI (flat) and z (+2.9) turn them into a
   chase. A face that draws stacks without the OI word repeats the old error with a different glyph.
6. **The first 30 minutes are blind** (`warm`): 1 Oct's 09:20 new shorts and 09:25 new longs are facts the OI shows, but every
   ratio is unavailable. The previous session's same-window medians (the sides-3 fix) would unblind it; not done here.
7. **1 Oct 10:30 "second push with new longs"** read as "buyers now committed" — true, and they were the trapped side; the
   decoder's chip says `naye long` without judgement, and the judgement arrived at 10:45 (`phanse −40`). That is the honest
   15-minute lag.
8. **Divergence (E7) fires rarely** (twice on 1 Oct) because of the strict 6-bar swing rule; on a trend day with no swings it
   says nothing, which is correct but leaves her without a "tiring" read for an hour at a time (10:50–11:30 on 1 Oct). The
   E3 count ("DABAAV ×3 in 6 bars") fills that gap better than a looser divergence.

---

## 5. The earlier designs, read after the draft

Read after §1–4 were written: `1-research.md` (rubric R1–R18, gates H1–H8), `4-design-fable.md`, `4-design-opus.md`,
`6-judgement.md`, `8-shadow-build.md`, `reader.py` (the shipped shadow leg engine), and the shipped extension detectors
`board.js`, `decode.js`, `taps.js`, `overlay.js`. **Where I was already coloured:** before drafting I knew, from this morning,
the leg as the unit, the WHO vocabulary (new longs / short covering / new shorts / long liquidation / rotation), effort per
1,000 lots, and that minute OI is batched. §1–2 use all four. What §1–4 add that none of those documents had is listed last.

**What they got right, and I keep:**
- The leg as the unit of *story*, ranked against today's own completed legs with n shown and an explicit warm-up (R1, R2,
  R13, H4); the ruler frozen at the open so nothing recuts the day (H5).
- WHO = delta × OI × price (R3) — the right triple, and the five words.
- **The batched-OI screen** (judge 5b; `reader.screen_oi`, `PUB_SHARE`): an OI update larger than the minute's volume is a
  publication step. The tool had the right instrument. It was never applied to the two prints, and today's root-cause note
  took +269K and +193K at face value. §1 step 3 applies it at the bar: both steps reverse on the next clean bar.
- Absorption as a **state at a location**, never a reversal (D2 in both designs; R5 "at a named level, multi-bar").
- Two tapes with SPLIT, feed health first, the roll window, no rates anywhere, [M]/[I] on every number, the three absence
  sentences.
- The judge's finished/unfinished convention (ATAS: a finished extreme has zero on one side). My E5 matches it.

**What they missed, and why her chart still read the prints backwards:**
1. **Blocks were screened out by design, with no replacement read.** `reader.py`: *"Blocks and spread prints are excluded BY
   PRINT"* (`BLOCK_X` 100, `BLOCK_BAR` 0.25); Design B line 7: *"One print can never become a leg's story again."* The
   instinct was right for 29 Sep 10:05's spread-leg suspicion, and it was generalised into deleting the one object she
   asked for. A 198K seller in six trades at the upper band on 30 Sep (Oct was the front month; nothing to mirror) was
   removed from the leg's delta, and the leg read *"rotation, OI flat"* over 56 minutes. The decoder keeps a print **out of
   the leg's effort number** (that part was right) and **in as a first-class event with its own level and confirmation**.
2. **The shadow reader never reached her chart; the face kept the old detector.** The debate designed `reader.py`, built it
   in shadow in TapeMap on the Upstox tape (GoCharting only on legs ≥ 2 GC bars), and listed "what happens to every current
   detector" — but the shipped extension still runs `board.js`: *"sold at p and the bar closed above it: buyers defended"*
   (`board.js:84-87`), and *"big effort, no result in this bar: absorbed, side = −delta"* (`board.js:88-89`). That is the
   in-bar-move rule the research's own R5 rejected. `MARK_KINDS` draws absorption / trap / climax / exhaustion and **never
   initiative**, so even a correct directional read had no glyph; and the mark's colour is the *defender's* side, so a
   correct detection would still have been drawn in the wrong colour. Her question was answered in a shadow log she does
   not see, and her screen kept the inversion.
3. **No OI quadrant per bar.** WHO is per leg; a 56-minute leg nets the print to nothing. Between the page's single-bar marks
   and the reader's leg stories there was no bar-level "did positions open or close", which is the resolution at which a
   print is judged. E8 fills it, with the publication guard and a fifth class (`dono taraf`).
4. **Location was tagged for value, not for her ring.** R8 (initiative / responsive against prior value) and R5 (absorption
   at a named level) exist; the extension's ±2σ taps exist in `taps.js` for the zone visits; **no object joins "a big print"
   to "at the band / at the level"**. The 30 Sep seller sat at z +1.9 above PDH in futures space; the 1 Oct 12:05 seller at
   z −1.9; nothing said so.
5. **Trade count is posted and read by nobody.** `bt`/`st` per row distinguish one hand (29 Sep: one trade of 4,528 lots;
   30 Sep: six trades) from a crowd (1 Oct 15:10: 18 trades). It is the cheapest participant read on this feed.
6. **Effort vs result was ranked per leg only.** The bar-level number on both prints — **1 point per 1,000 lots, rank 0.00** —
   is the "effort without result" witness that, with the OI quadrant, splits positioning from absorption. Inside a leg it
   disappears.
7. **"Big" in `board.js` is scale-free but not selective**: a one-sided cluster in the top 20% of the session's clusters, then
   "closed on the other side" → absorption. Sixteen of the 27 outlier bars in the root-cause scan got that label. One event
   = one mark (R14) was in the rubric and not on the page: the same print became A and then P after reloads.
8. **The confirm state was never a field.** Both designs have `t` and `asof`; neither has LIVE / CONFIRM BAAKI / CONFIRMED /
   FAILED on an event, so a read is either shown as a fact or not shown. §2.7 makes the pending state a first-class word,
   because every direction read on a print is after the fact.
9. **The judge's own two-bar check was not run on prints.** Judge item 5b found −5,021 lots at 10:12:32 on 29 Sep "on almost
   no volume" — the publication step that cancels the 10:05 OI rise — and read it as a data fact for the leg engine, not as
   what it also is: the reason the 300K buyer's "new longs" cannot be confirmed at the bar.

**Not converged quietly:** I keep the leg for the story layer and drop it as the unit of *events*; events are per bar and per
cell, confirmed across bars. I keep the block exclusion from effort and reverse the deletion of the print. I keep absorption
as a state and add the OI split that the state needs to be true. I add the ring and the futures-space levels as the gate for
every single-bar event, the trade count, the per-bar quadrant with its guard, the confirm state, the open-print ledger, the
story machine, the one-sentence rule and the seven-object line budget.

---

## 6. Validation and build order

### 6.1 What each event logs forward (one row per closed bar, append-only, beside the frame)

`day t idx bar{o h l c vol delta oi doi doi_guard} medians{cell vol range delta} z ring level{name px_fut state} time_band dte
events[{kind side p lots trades xcell share quadrant state(LIVE/BAAKI/CONFIRMED/FAILED) confirm_at exit_px_up exit_px_dn}]
quadrant lam lam_rank cvd div stacks{up dn} ext{hi lo} exh profile{poc va_lo va_hi} book{fuel_side power forced first fuel_left}
story{state level since} sentence chips[3] shown(bool) why` + the outcome fields filled by the same process at +6 and +12
bars (points from the bar's close, max favourable / adverse excursion), never recomputed from a re-cut cache.

### 6.2 Kill conditions, pre-registered now, bars for Mary to sign later (≥ 15 rows per cell; seen rows never count)

- **E1 big print:** rows CONFIRMED-held vs CONFIRMED-trapped, each listed with the +12-bar move from the print price in the
  printer's direction. Bar (hers): if held rows do not travel at least the session's median 12-bar range in the printer's
  direction in most of the first 15, the direction chip is dropped and E1 stays a **level only**.
- **E3 positioning vs absorbed (the OI split):** the two cells' +6-bar moves listed; if they are indistinguishable at 15 each,
  the split is deleted and E3 reads `DABAAV` with no attribution.
- **E8 quadrant with the publication guard:** count of bars where the guard fired against bars where the 2-bar net kept ≥ 50%
  of the step; if the guard fires on most big-print bars, the futures OI is declared unusable at bar level and the quadrant is
  computed only over 15-minute windows.
- **E4 / E5 / E6 at band or level:** each listed with "the next bar extended / did not"; at 15 rows, an event whose rows split
  evenly is removed from the chart (it may stay in the panel ledger).
- **E7:** divergence rows with "swing held 2 bars"; same rule.
- **The sentence:** her after-close mark on 15 sessions — "would I have said this?" yes / no per sentence shown; a sentence
  class she marks "no" on most rows is rewritten or removed.
- **Line budget:** counted per session; a session over 7 objects is a bug, not a parameter.

### 6.3 Build order, smallest first

| step | what | where | needs |
|---|---|---|---|
| 1 | **E1 big print** with the OI guard and the open-print ledger; the ▮ glyph in the aggressor's colour; the chip; stop emitting the cell-absorption for a cell that qualifies as a print | extension `engine/` + `shell/` | extension reload only |
| 2 | **E8 quadrant** per bar with the publication guard and `dono taraf`; six-word strip in the panel | extension | extension reload only |
| 3 | **E3 split by OI** replacing "absorbed by in-bar move"; **E2 naye / covering** | extension | extension reload only |
| 4 | **The line budget and the chips toggle**; glyphs only at band / level or OI-confirmed; the panel ledger with states | extension `shell/` | extension reload only |
| 5 | **E4 / E5 / E6 gated** to band / level / leg extreme | extension | extension reload only |
| 6 | **Context**: level in futures space via basis (needs the chain spot: already on the frame), time band, DTE | extension reading the frame it already receives | extension reload only |
| 7 | **E10 book** and **E9 level state** on the chips (sides-3 and warmap are server objects: carry them on `/api/frame`) | `frame.py` composition + panel | server restart (after the close) |
| 8 | **The story machine and the sentence** (English, logged) | `frame.py` or a new pure module beside `trap.py` | server restart |
| 9 | **Forward log** (§6.1) and the after-close "would I have said this?" mark on RECORD | server + ui-v2 | server restart |
| 10 | **E12 cross-index extremes** on the chip (xindex already computes them) | `frame.py` + panel | server restart |
| 11 | Post `maxDelta/minDelta/buyTrades/sellTrades` (one line) — for the record, not for a read | extension | extension reload |

Steps 1–6 put both of her prints on the chart, with honest chips, at the next session without touching the server.
