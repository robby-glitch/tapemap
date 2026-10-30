# COIL → PUSH → RUN: how OI is decoded, and what RAFTAAR is missing (27 Oct 2026, evening)

Her question: "is it able to detect squeeze and big push candle where running started so one know its getting coiled
and can blast can happen which side is leaning . just brainstrom different scenior ask youself how you exactly decode oi"

Short answer: **not yet.** RAFTAAR sees a move once it runs (CHAL RAHA SHURU), loading at a level (ATKA), and pins.
It has no COIL state, no PUSH mark, no LEAN of a coil, and it reads every OI add as writers.

Evidence: `coil_scan.py`, 24 real NIFTY legs (≥ 0.35 %, ~80 pts) on the 11 recorded days, the 30 min before each one
and its first 5 min. Strikes are pinned at the leg's start. These are rows, not rates. The legs come from a whole-day zigzag,
i.e. a description of what happened, not a signal.

## What the record says (NIFTY, 24 legs)

1. **A coil before a blast is the minority case.** Only 6 of 24 legs started from a squeezed range (30-min range under
   0.8× the day's typical 30-min range). Most legs started as a turn out of the previous move (a V), not out of a coil. A
   coil detector will catch some blasts, not most.
2. **The two textbook coils both broke AGAINST the heavier writers:**

   | Coil | Range | Writers near ATM | Straddle | IV | Then |
   |---|---|---|---|---|---|
   | 29 Sep 10:21 | 42 pts (day typical 104) | CALL +149L, PUT +77L | −8.9 | −1.8 | +176 ▲ |
   | 27 Oct 10:03 | — | CALL +70L, PUT +133L | −23.6 | −3.7 | −99 ▼ |

   That is only n = 2.
3. **Lean: 21 of 24 legs ran against the side that wrote more near ATM in the 30 min before.** That is mostly by
   construction:
   - a leg starts at a swing extreme;
   - writers write WITH the move that just happened;
   - so at every turn, the heavier writer is the one who gets trapped.

   This says WHO the fuel is (her thesis: trapped inventory is the fuel). It does not say WHEN the turn comes; the same
   picture sits at every minute of a trend that does not turn (oi-lab: OI state at an extreme did not separate holds from
   breaks).
4. **The push bar:**
   - It is the first 3-min bar ≥ 2× the coil's median bar.
   - It came 0–24 min after the leg's start.
   - 6 of 24 legs had none within 30 min: those were grinding legs with no ignition candle.
5. **In the first 5 min of a run, the run-over side's OI near ATM went UP on almost every leg.** It did not go down: the
   squeeze-by-covering comes later, if at all. Premium vs what delta explains says who opened it:

   | Leg | Who opened | Premium vs delta | Size |
   |---|---|---|---|
   | 27 Oct 14:16 ▲ | buyers chasing calls | +1 to +3.5 | +132 |
   | 26 Oct 10:08 ▼ | buyers chasing puts | +1.7 to +1.9 | −163 |
   | 23 Oct 12:51 ▲ | writers adding into it | −2 to −3 | +204 |
   | 26 Oct 11:34 ▲ | writers adding into it | −3 | +217 |
   | 22 Oct 12:54 ▼ | writers adding into it | −1 | −132 |

   Both kinds ran. **"OI up = writers" is wrong about half the time near ATM in a fast move.**

## How I decode OI, step by step (what the screen should do in this order)

1. **Map:** where is price against the walls (biggest CALL build above, biggest PUT build below), in points, s | f?
2. **Who is moving:** at the near strikes (ATM ± 2) and at the walls, is OI being added or removed? How fast, and is it
   speeding up?
3. **WHO opened it:** writers or buyers? For each add, compare the option's premium move with what delta explains:
   - premium beats delta (IV up) = buyers paying up;
   - premium lags delta = writers selling into it.

   For each cut, compare the last price with the day's average traded price (`avg`):
   - writers under water and cutting = forced (fuel);
   - writers in profit and cutting = booking.
4. **Effort vs result:** how much OI moved per point of price. A lot of OI for no points means absorbing or loading; points
   with no OI means nobody is behind the move.
5. **Stored energy:**
   - range squeeze against the day's own normal;
   - the ATM straddle and IV falling while both sides write = sellers loading the spring.
6. **Ignition:** the first bar ≥ 2× the coil's bar, with the straddle or IV popping.
7. **Fuel:**
   - the trapped side's OI near price, and how far price is from it;
   - "jala": how much of it has already been bought back.
8. **Confirmation outside the chain:**
   - the futures leg (fut OI with price: fresh longs vs short covering; oi-lab's surviving read: fut OI flat + buyers
     hitting);
   - order-flow delta;
   - effort per point at the extreme (effort.py, the one flow read that survived);
   - the other two indices.
9. **Time:** the open (no history), midday (pins), after 14:30 on expiry (gamma: small OI moves make big price moves).

## The scenarios (what each looks like on OI, and what the screen should say)

| Scenario | OI + price signature | Lean / fuel | Screen word |
|---|---|---|---|
| **COIL / spring loading** | 30-min range < 0.8× the day's normal; both sides writing near ATM; straddle and IV falling | the heavier near-ATM writer is the fuel if price breaks against it; which side is already under water (ltp > avg) | **COIL ▲? / ▼?** (energy, lean side, fuel L at pts) |
| **IGNITION (push candle)** | first 3-min bar ≥ 2× the coil's; straddle or IV pops; the run-over side's OI reacts | buyers chasing (premium > delta) or writers adding (premium < delta) | **◆ PUSH ▲/▼** at its bar, time and price |
| **SQUEEZE** | the trapped side cutting, under water, faster each minute; the wall rolls with price; the other side writes behind | the fuel is burning: "jala" grows | **SQUEEZE ▲/▼ · TEZ** |
| **ABSORB → bigger squeeze** | writers add into the push (premium < delta) and price still goes through them | fuel is being BUILT, not burnt: the next leg has more to cover | **PHANS RAHE** (getting trapped), fuel rising |
| **BUYER RUN** | buyers chasing (premium > delta), writers stepping aside | needs fresh buying every minute; fades when IV stops rising | **KHAREEDAR DAUD** (buyers' run), IV ↑ |
| **FAKE BREAK** | push bar, but the run-over side adds and is NOT under water, the other side does not follow, the straddle does not pop | none; snaps back into the range | **TOOTA NAHI** (no break) |
| **EXHAUSTION** | covering slows; price stalls at the next wall; new writing there; effort per point up | the fuel is spent | **THAK RAHA** |
| **PIN** | both sides writing about equally at one strike; the straddle collapses; range < 1 step | none until one side flinches | **PIN @ k** |
| **CHOP** | legs both ways; writers re-write at each extreme (baari-baari); no wall rolls | none | **CHOP** |
| **GRIND** | no push bar; slow and steady one-sided rolls of the walls; low speed but persistent (6 Oct) | the slow roll IS the lean | **DHEEMI CHAAL ▲/▼** |
| **EXPIRY GAMMA** | after 14:30 on expiry: tiny OI moves, big price moves; the ATM straddle is tiny | the side short ATM gamma | **GAMMA ZONE** |

## What to add to RAFTAAR (display only, judged forward; nothing claimed as a prediction)

1. **COIL state:** the squeeze ratio, the straddle and IV falling, both sides writing, and the stored energy in L.
2. **PUSH ◆:** the ignition bar, marked at its time and price.
3. **LEAN of the coil:** the heavier near-ATM writer, how much of it is already under water (ltp vs avg), and the points to
   their strike. Phrased as "agar toota to fuel ▲ 120L at 22,750s", never "it will break up".
4. **WHO OPENED:** each near-ATM add split into buyers vs writers by premium vs delta. This changes the story words
   (PHANS RAHE vs KHAREEDAR DAUD) and fixes "OI up = writers".
5. **Leg-start rows:** keep the 24 rows above growing forward; judge on forward days, never on these.

## THE HANDSHAKE: order flow pushes, OI must answer (27 Oct, her ask: "something pushed there something will definitely move here in oi as well as vice versa and we can see if walls are breaking and floors are getting created")

Evidence: `handshake.py`, NIFTY fut Dext 1-min delta (lots) lined up every 2 min with OI at the CALL wall and the PUT
floor. 27 Oct afternoon has no Dext flow (all zero): a gap, not a reading.

**26 Oct 09:44–10:30, a real move: the push, the answer, the new floor, the new cap, the turn.**

| time | spot | fut Δ 2m | what OI did in the same / next 2 min |
|---|---|---|---|
| 09:46 | 22,486 | +283 | nothing yet |
| 09:52 | 22,503 | **+458** | price crosses the 22,500 CALL wall (+94.7L written there today) |
| 09:54 | 22,545 | **+653** | **22,500 CE −15.5L**: the wall breaks, 2 min after the push |
| 09:56 | 22,591 | +530 | 22,500 CE −15.5L again · **22,550 PE +10.3L**: a floor starts under the new price |
| 09:58 | 22,645 | +308 | 22,500 CE −15.5L again (−46.5L in 6 min) · **22,600 PE +14.8L** |
| 10:00–10:04 | 22,649 → 22,630 | +50, −241, −128 | flow fades · 22,600 PE keeps adding (+12.9, +10.2, +5.2: the floor gets set at 22,600) · **22,800 CE +6.4, +4.0**: a NEW CAP is written |
| 10:06–10:08 | 22,667 → 22,699 | +579, +268 | the last 22,500 CE writers cut −10.1L · the high of the leg |
| 10:10–10:26 | 22,684 → 22,649 | mixed, small | **22,700 PE +11.0, +5.7**: puts written AT THE TOP · **22,700 CE +7.3, +3.0**: the cap ROLLS DOWN from 22,800 to 22,700 |
| 10:28–10:30 | 22,646 → 22,640 | **−289, −204** | the selling arrives; the 22,700 put writers from the top are now the fuel down |

What this shows, in one chain:
1. **The flow pushes first.** The OI at the attacked strike answers within about 2 min.
2. **While the flow keeps pushing, the wall keeps cutting.** Each 2-min push got another −15.5L.
3. **A new floor gets written right under the new price** (22,550 → 22,600): the move is being BACKED.
4. **When the flow fades, a new cap gets written** above (22,800).
5. **At the top, puts get written at the top and calls roll the cap DOWN.** When the flow flips, those top put writers are the next fuel.

**22 Oct 12:09–12:51, the fake (the 12:21 "chop se bahar ▼" at 22,595 that gave back 98).**

| Piece | What happened |
|---|---|
| Flow | Small: largest 2-min push −252 lots at 12:19 |
| 22,600 PUT floor | Never cut: −0.9L, −1.0L |
| New CALL wall below price | None written |
| Every 2-min OI change on both sides | Under ±5L |
| Result | **No handshake.** The flow nudged, OI didn't answer, and price went back up |

### The cause → effect map (what to expect, and what each answer means)

| Flow does | OI must answer at the attacked strike within ~2–4 min | Meaning | Screen |
|---|---|---|---|
| big buy push into a CALL wall | the wall's CE OI CUTS, again with each push | **wall breaking** (writers forced out) | DEEWAR TOOT RAHI ▲ |
| big buy push into a CALL wall | the wall's CE OI ADDS, and price stalls under it | **wall defending** (absorbing) | DEEWAR TIKI ▲✗ |
| big buy push into a CALL wall | CE OI adds AND price goes through anyway | **writers getting trapped**: fuel building | PHANS RAHE ▲ |
| buy push, price up | PUT OI added at the strike just under the new price | **floor being built**: the move is backed | NAYA FLOOR 22,600s |
| buy push, price up | NO put writing under it | a move on air: nobody behind it | BINA FLOOR (careful) |
| flow fades after a run | new CALL writing at a higher strike | **new cap**: THAK risk | NAYA CAP 22,800s |
| flow flips at the top | puts written at the top + the cap rolled down | **the top's floor is the next fuel** | PALAT KA FUEL ▼ |
| a small flow nudge | no OI answer anywhere | **noise / fake** | kuch nahi |
| (the mirror of every row for a sell push into a PUT floor: the floor breaks, a cap gets written over the new price, etc.) | | | |

| OI does first | Flow should follow | Meaning |
|---|---|---|
| writers at the attacked strike cut hard while flow is quiet | buy flow should arrive (their hedges and option buybacks move price) | a squeeze starting from the OI side |
| fresh writing on BOTH sides at one strike, flow small | none | a pin being set |
| a floor added under price with no push | dips should get bought there | support being placed; fade the dips |

### The test the screen runs, every time

1. **PUSH:** a 2-min fut delta ≥ 2× its recent normal, into a strike. Mark ◆ at once, as "PUSH ▲ · OI ka jawab dekho".
2. **ANSWER within 4 min:** did the attacked strike CUT (✓ toot rahi), ADD with price stalling (✗ tiki), ADD with price
   through (phans rahe), or do nothing (✗ jawab nahi)? Did a floor or cap get written behind price?
3. **SAHMATI** moves with the answers. Several confirmed handshakes in the last 15 min means a real move. A push with no
   answer means noise.

Open point: n is small (one clean real move with flow, one clean fake). Judged forward. The 2× and 4-min numbers are
[I], read off 26 Oct.
