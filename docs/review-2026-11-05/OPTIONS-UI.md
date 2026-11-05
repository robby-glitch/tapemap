# Option-flow screen: review and a new map (5 Nov 2026, after the close)

Her words: *"check the option trade and see how we can make it better the ui wise take inspiration from volume lens
https://volumelens.com/sector-map"* and *"most of thing was kind of sleeping in the ui ... make sure things get hightlighted
when something big happens."*

Reviewed as a trader:
- `optflow/map.html`, the Option Battlefield on 8790 `/`;
- `optflow/ladder.html` + `optladder.py`, the ladder on 8790 `/ladder`;
- `optflow/structures.py`;
- the earlier designs in `docs/optflow/`: the rejected front-line mockups, Fable's mockup v1/v2, Sonnet's mockup v1/v2, and the §1s
  pre-registration.

Nothing live was touched and no server was called. Today's data was read from files on disk after 15:35, one streamed
Python process.

Mockup: `docs/review-2026-11-05/option-map.html`, standalone, light, no CDN. Its data is built by
`option_map_export.py` (`python -I option_map_export.py 2026-11-05`, then `--page` to embed the snapshot).

---

## 1. The current board: 4 / 10

| part | score | why |
|---|---|---|
| The WHO logic (OI change × the strike's own order flow) | 7 | This is the right question, and the tool asks it honestly. OI says a position opened or closed. The Dext delta says who did it. Grey "not writers" is the 3 Nov 11:55 lesson built in. It also keeps three separate states: a value, *kuch nahi* (checked, found nothing) and *nahi dekha* (could not check). |
| Glance (3 seconds, mid-trade) | 3 | The map is a whole-day picture: strikes down the side, 5-minute blocks across. "Now" is its thinnest column. The ladder is a wall of tiles with 10–11 px text, a structure card and a list of blocked trades. Neither answers "is anything breaking right now?" at a glance. |
| Loudness of big events | 2 | Nothing pulses, nothing is time-stamped, and there is no list of events. A wall breaking is one hollow outline in one 5-minute cell. It weighs the same as a 1.5L wobble, because the block alpha has a floor of 0.2. The only text event is "Last big hit", which is overwritten by the next hit. |
| Trader usefulness | 4 | It answers *who is writing* well. It cannot answer *who is trapped*, *where the fuel is* or *what just changed*. |

## 2. The five biggest problems, as a trader

1. **Big moves are silent.** No event can be louder than any other. Breaking the call wall, three strikes covering together, a
   BADA print and an OI jump all draw as small cells or dots on a 20-row grid. There is no "abhi kya hua" line with a time.
   On a day like today the afternoon becomes a slow change of colour. *(Today's afternoon: §4.)*
2. **The board is late, and it is a day map.** A 5-minute block appears only once its 5 minutes are done. Dext lands 1–2
   minutes late on top of that, so a wall that breaks at 13:41 shows at about 13:46–13:47. That is too late for a 3-minute
   trader. The page also reloads itself every 30 s (`location.reload`), which blanks the screen and loses the scroll
   position.
3. **Trapped writers are not shown at all.** Trapped inventory is the fuel. Her thesis is "trapped inventory is the fuel,
   forced flow is the edge". Call writers who sold strikes that are now under spot (ITM) are the squeeze fuel, and neither
   page shows them as a group. The map has CAP / FLOOR only. The ladder computes ITM_CE / ITM_PE groups in `optladder.py`
   and never draws them.
4. **"Big hit" is not her BADA.** The map's big hit is a quantity floor (5L qty). A wing option at ₹8 clears 5L far more
   easily than an ATM option at ₹120. Fable's round 6 measured this on 3 Nov: 1,311 qty-big cells in the wings, 16 of them
   big by delta-lots [M]. The ladder uses delta-lots, the map uses quantity, so the two pages on one server disagree about
   what "big" is.
5. **Two screens, two grammars, nothing on one glance.**
   - The map uses 5-minute blocks, thresholds scaled to the day's p90, and a LEAN pill (UP / DOWN / RANGE / WIDE).
   - The ladder uses her 3-minute closes, a fixed 1.5L, and the said word (UP FUEL / LID / ...).
   - The same minute can read differently on the two pages.
   - The ladder spends its best space on a structure card (legs, credit, breakevens, a blocked list). That is useful
     after a decision, not in the 3 seconds before it.
   - Smaller points: the canvas is 40 px per strike, so far strikes take as much room as the ATM; the fonts load from
     Google, which fails offline; a printed glyph has no chip.

## 3. The new design: the option map

Taken from VolumeLens's Sector Map:
- one stage that shows at a glance where money is moving and how big;
- a drill from the centre to a group to a member;
- labels on everything, so nothing needs a legend.

What is not taken: their price/% framing. She has charts. This screen reads **positioning and flow**.

**The stage (radial, light):**
- **Centre disc = the index.** NIFTY spot (s), today's move in points, futures (f), Jarvis's word in grey. Under it is a
  pill with the options' *said* word, in `optladder`'s grammar (UP FUEL / LID BREAKING / PIN ...) with a Hinglish chip
  (*upar ka indhan*, *dhakkan khul raha* ...). The disc pulses when the word changes.
- **Four hubs on the diagonals, which are the option chain folded in two:**
  - **left column = calls, right column = puts; top row = strikes above spot, bottom row = strikes below spot.**
  - **One diagonal is the walls:** CAP (calls above spot, top-left) and FLOOR (puts below spot, bottom-right).
  - **The other diagonal is the trapped writers:** ITM CALL (calls below spot, bottom-left: call writers under water, the
    up-fuel) and ITM PUT (puts above spot, top-right: the down-fuel).
  - A trader reads the shape at once. Walls are on one line and fuel is on the other. Whatever is lit tells her which
    one is moving.
  - I chose these hubs over "CE writers / PE writers / CE buyers / PE buyers". With the latter, a strike would jump hubs
    every close as its WHO changed. The strike geometry is stable, and it is her own map: the walls (§1d) and the trapped
    inventory.
- **Hub** = a white disc with an arc gauge. The arc is the group's OI change over the window, coloured by what it does to
  price (green pushes up, red pushes down, amber = writers covering). Inside: the change in lakh, the group's word
  (*likh rahe / bhaag rahe / kharid rahe / nikal rahe / shaant*) and its order-flow delta. Click the hub to drill
  (*‹ NIFTY · CAP · 6 strikes · OI 512L · 15 min: bhaag rahe −31L*). The other hubs dim and the members open wider with
  their OI.
- **Bubbles = strikes, ATM ±5.**
  - Size = OI, which is the wall's size.
  - Fill = who did it in the window (red = bearish writers / buyers, green = bullish), intensity = the size of the OI
    change.
  - **Amber thick ring = writers covering (*bhaag rahe*), the one state that breaks a wall.**
  - Black ring + `DEEWAR` = the biggest OI on that side.
  - Dashed = OI but no Dext flow; hatched = no OI.
  - Every bubble carries its strike, side, Hinglish word and number (`24600 CE · DEEWAR` / `bhaag rahe −18L`).
  - `+n aur` = strikes of that group outside ±5.
- **Roads** from the centre to each hub. Width = the group's traded volume in the window. **The dots run out to the hub
  when positions open and back to the centre when they close.** Covering literally flows back into the index. That is the
  VolumeLens "money moving" cue with an options meaning.
- **Window toggle 3 min / 15 min / Din**, like their Today / 1 week / 1 month. The default is 15 min. 3 min flickers the
  way the Jarvis word did (52–79 word changes a day, 31 Oct review); 15 min is the leg. Events still fire on her 3-minute
  closes whatever the toggle says.
- **Search** a strike (`24600`, `24400 pe`) to open its card.

**LOUD, so the second half cannot sleep:**
- **Events** (her 3-minute closes from 09:23, ATM ±3/±5; every threshold [I], shadow):
  - **DEEWAR TOOTI / FARSH TOOTA (LOUD):** spot goes ≥ 5 pts through the last close's wall, or that wall's writers cover
    ≥ 3L. Wording when they cover: *DEEWAR HIL RAHI*.
  - **CE / PE BHAAG RAHE ×n (LOUD):** 3 or more strikes on one side covering in one close. This is the ladder's cover
    alarm, R3 SQUEEZE ON.
  - **PHANSE CALL / PUT WRITERS BHAAG RAHE (LOUD):** the ITM group covering ≥ 4L. Trapped writers paying, which is fuel.
  - **BADA BUYER / SELLER (NOTABLE; LOUD from 4,000 δ-lots):** one price cell in one minute ≥ 2,000 delta-lots (qty ×
    the chain's |delta| ÷ 65), as Fable's §1s-A proposed (unsigned). Shown one minute after its minute, because Dext
    lands late.
  - **OI JHATKA (NOTABLE):** one strike moves ≥ 8L in one close (today's p99 of 3-minute moves was 6.0L, §4).
  - **KHISKI (NOTABLE):** the wall strike moves.
  - **OPTIONS word change (INFO).**
- **How an event shows:**
  - **Pulse:** two expanding rings on the bubble, or on the hub for squeeze / trapped events, for 6 minutes.
  - **The LOUD band:** a full-width band under the header, green / red / amber, with three flashes. It reads
    `13:4x · ABHI · DEEWAR TOOTI · 24600 CE · spot 24,61x upar nikla · ...`.
    - When nothing has happened for 6 minutes it says so: *shaant · pichhle 6 min mein kuch bada nahi · aakhri LOUD
      13:4x (n min pehle)*. This is "checked, found nothing", never a blank.
  - **KYA HUA strip:** every event with its time, newest first, LOUD rows tinted, the last 6 minutes outlined. Click a row
    to jump there.
  - **The time track:** a tick per event above the slider. LOUD ticks are tall, NOTABLE ticks short, coloured by
    direction (blue = BADA). The whole day's loud moments are visible before she presses play.
  - **Controls:** ⏮ LOUD / LOUD ⏭ (P / N) jump from one loud moment to the next; ← → step a minute, Shift 3 minutes, Space
    plays.
- **Below the stage, tabs:**
  - **Strikes:** a CE | strike | PE grid, ATM ±6: OI, ΔOI, δ flow, a WHO chip, CAP / FLOOR tags.
  - **Deewar:** the top two walls per side, with 15-min state (*badh rahi / ruki / ghat rahi*), WHO and distance from
    spot.
  - **Strike card:** the last 10 closes of one strike: ΔOI, δ, WHO, premium vs its day average, the biggest cell and
    whether it was BADA.
  - **Chips ka matlab:** the vocabulary, one line each.

**Kept from the house rules:** light only; counts, points and lakh, never a rate; every threshold tagged [I]; three
states never merge; no candles; no order path. SENSEX is not in the mockup. The same page would take SENSEX's own OI for
the hubs. Using SENSEX's option flow for WHO is a §1q change, hers to sign.

## 4. Today on the map (5 Nov, NIFTY, from the files)

**Snapshot [M].** Built with `option_map_export.py`, streamed, after 15:35:
- 14 strikes, 24,100–24,750, every one with a Dext file (28 of 28 sides). Expiry 9 Nov. Minutes 09:15–15:29.
- 3-minute |ΔOI| per strike: p90 1.6L, p95 2.6L, p99 6.0L, max 38.9L. So JHATKA is set at 8L [I], above the p99.
- 115 cells were ≥ 1,000 delta-lots. **5 were ≥ 2,000**, so the BADA floor stays rare, as it should.

**The day [M].** Futures 24,320 → 24,617 (14:15) → 24,573 (15:00).
- The morning ranged around 24,400.
- 11:30: the first push.
- 13:00–13:50: the trend leg.
- 14:15–14:30: a 50-point dip.
- Then back to 24,600.

**What the map shouts, from 12:30 (engine output, every number [M], every rule [I]):**

| close | band | event | the numbers |
|---|---|---|---|
| 12:50 | LOUD | CE BHAAG RAHE ×3 + PHANSE CALL WRITERS BHAAG RAHE | −7.5L at 24,400 / 24,450 / 24,500 CE; ITM call writers −5.0L |
| 13:01 | notable | BADA BUYER 3.01L @232.9, 24,300 CE | 3,231 delta-lots, bullish |
| 13:14 | LOUD | CE BHAAG RAHE ×3 + PHANSE CALL WRITERS | −7.2L; ITM −8.3L with δ +10L |
| **13:38** | **LOUD** | **DEEWAR TOOTI · 24,500 CE** | spot 24,527 through the day's biggest call wall (~98–101L at 13:30) |
| | | | the 24,500 PE writers built +17L in 15 minutes behind price (a new floor) |
| | | | same close: **CE BHAAG RAHE ×6** (−15L, 24,400 → 24,700) and PHANSE CALL WRITERS (−12L, δ +28L) |
| | | | 24,500 CE OI went 101.5L (13:30) → 81.3L (13:48) → 77L (14:06) |
| 13:47 | LOUD | DEEWAR HIL RAHI · 24,600 CE + CAP KHISKI 24,600 → 24,700 | the next cap's writers ran (−4.7L, δ +12L) and the wall stepped up a strike |
| 14:03 | notable | BADA BUYER 2.01L @327.65, 24,300 CE | 2,327 delta-lots |
| **14:23** | **LOUD** | **FARSH HIL RAHA · 24,400 PE + PE BHAAG RAHE ×3** | put writers ran at 24,400 / 24,500 / 24,600 (−7.9L) as spot fell to 24,506 |
| | | | 24,500 PE, the floor built at 13:38: 87.4L (14:03) → 75.1L (14:30) |
| 14:35 | LOUD | DEEWAR HIL RAHI · 24,600 CE + PHANSE CALL WRITERS | the dip bought back; call writers ran again (−3.3L; ITM −4.3L) |
| 15:26 | LOUD + notable | DEEWAR HIL RAHI · 24,600 CE · OI JHATKA −8.5L at 24,500 CE | the close |

**Counts for the whole day:** 22 LOUD, 9 notable and 22 word changes [M]. 13 of the LOUD events came after 12:30 [M].
Today's afternoon on the current board would have shown:
- a few amber-outlined 5-minute cells;
- a dot or two;
- a LEAN pill.

On the map it is the band flashing green at 13:38, the CAP hub ringing amber, dots pouring back from the ITM CALL hub into
the centre, and a tall tick on the time track at 13:38 and at 14:23.

**Two honest gaps:**
- **The morning had LOUD events too.** 09:44 and 11:32 were squeeze closes. The map does not know that a morning squeeze in
  a range is smaller news than an afternoon break. A later version should weight a wall break above a squeeze inside a
  range. The `RANK` order on the band already does part of that.
- **"DEEWAR HIL RAHI · 24,600 CE" fired 3 times (13:47, 14:35, 15:26)** while that wall held all afternoon. Its OI rose from
  48.8L to 76.4L. Covering of −3 to −5L at a wall that is net building is a shake, not a break. The next version should
  check the wall's own 15-minute change before calling it HIL RAHI. The Deewar tab already shows that change.

## 5. What it would take to build (for her word, not built)

- **One brain.** The events engine sits in the page today for the mockup. It belongs in `optladder.py`, beside the closes
  it already computes, so the map, the ladder, Jarvis and Telegram fire the same events. The four groups are already
  there.
- **Serve it.** Add `/map2` on 8790 next to `/` and `/ladder`. Keep the old map until she says cut. Polling with a fetch
  replaces `location.reload`.
- **Telegram.** LOUD events only (TOOTI, BHAAG RAHE ×n, PHANSE, BADA ≥ 4,000), one line each, behind the same
  15-minute dedup.
- **Still owed:** the pass bar for §1s, the §1s-A BADA definition (her signature), and the SENSEX decision.
