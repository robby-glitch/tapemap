# The better-trade read: rules, written before any replay

**Written 2026-09-25 00:50 IST (read from the system clock, 00:49:37), before
this read was computed at any minute of any day.** DRAFT. Nothing here is
registered, and nothing here is live.

**What I had already seen when I wrote this.**
- 2026-09-24 was a falling trend day on SENSEX, and 2026-09-23 was a range day.
- The board's 15:29 payload for SENSEX on 09-24 read "REGIME NOT AGREED,
  STRONG NEITHER".
- Both HOLD/FOLD windows' replays, including Fable's 5m / 15m / 1h trend words.
- Her trades and their P&L.

I have **not** computed REGIME, STRONG, the mirror or this read at any
minute. No rule below was chosen by looking at a row.

## 0. What she asked for, in her words, and what it becomes

> "tell me if i have entered into the wrong trade already. second best trade
> suggestion from both and which index and why … the day like to be selling or
> buying option"

It becomes five plain questions, answered for NIFTY, BANKNIFTY and SENSEX at
every finished minute:

1. **What kind of day is it:** a day to BUY options, to SELL them, or neither
   clean? And why.
2. **Which side:** CE or PE.
3. **Which index is cleanest, and why.**
4. **Is the engine's current trade a good call?** Checked against the facts.
5. **What is the best trade and the second best**, as buyer or writer, and on
   which index.

When she is **in** a trade, the panel sits next to the HOLD/FOLD window and
first answers **"did you enter into the wrong trade?"** When she is flat, it
stands alone.

It never places, sizes, or prices an order. It never gives a probability, a
score, or a hit rate. It counts agreeing facts, and a count is all it prints.

## 1. Inputs: all existing, all cut to the finished minute `t`

| input | source (existing code, unchanged) | tag |
|---|---|---|
| the trend rows 1m to D; STRONG (BULLS / BEARS / NEITHER); REGIME (TREND UP / TREND DOWN / PIN / CHOP / NOT AGREED) | `trendbox.rows`, `trendbox.strong`, `trendbox.regime(tr, board.oi_read(fronts, spot))` — the board's own reads, fixed before either reference day | [I] |
| the nearer of each side's §1d top 2 and its state | `fronts.read` + `board.nearer` | [M] |
| sized folds, stamped in the last 15 min and still folded | `fronts.folds`, `board.still_folded` | [M] |
| 15-min CVD (with rank and divergence) and prints of size | `grounds.facts` | [I] |
| the ATM mirror: ATM CE and ATM PE premium against **their own** session VWAP ±σ | `/api/contract`'s VWAP (`contract_bars.vwap_sigma`); the ATM strike is spot rounded to the step | [M] |
| the engine's trade: the zone machine's latest arm or entry, with its §1d gate as logged | `data/trigger_log.jsonl` (forward-logged) | [I] |
| the engine's verdict and its grounding (BACKED / THIN / CONTRADICTED / PATA NAHI) | `/api/calls`, i.e. `data/calls/calls_<day>.jsonl` | [I] |

## 2. Q1: buying day, selling day, or neither

The day word is **the board's REGIME, turned into a trader's sentence**:

- **TREND UP** is a **BUYING day, calls**.
  - Price agrees on 5m, 15m and 1h, and on OI the call side has stopped
    while the put side writes.
  - Someone is being forced, so a buyer gets paid.
- **TREND DOWN** is a **BUYING day, puts**, the same mirrored.
- **PIN / CHOP** is a **SELLING day**.
  - Two of 5m, 15m and 1h read RANGE, and both sides' nearer fronts are writing.
  - Nobody is forced, so premium decays and the writer gets paid.
- **NOT AGREED, or a row still forming**, is **NEITHER is clean**. Both halves
  are printed ("price says TREND DOWN, OI says both sides leaving").

**Calm.** A new day word shows only after the underlying REGIME word has held
**3 finished minutes** (`PERSIST`, the window's own number). Until then the
old word stays, marked "changing to …".

**The evidence under the word, counted: n for · m against · k could not check.**

| | a **BUYING day in direction D** is backed by | … and is against by |
|---|---|---|
| a | STRONG agrees (BULLS for up, BEARS for down) | STRONG says the opposite |
| b | a **payer-side** fold (CE for up, PE for down) in the last 15 min, still folded | a **holder-side** fold in the last 15 min, still folded |
| c | CVD strong (rank ≥ 0.50) in D, with no divergence against D | CVD strong against D, or a divergence against D |
| d | the ATM mirror: the D-side ATM option above its own VWAP, the other side below | the mirror the other way round |

| | a **SELLING day** is backed by | … and is against by |
|---|---|---|
| a | STRONG = NEITHER | STRONG = BULLS or BEARS |
| b | no still-folded fold on either side in the last 15 min | any still-folded fold in the last 15 min |
| c | CVD rank < 0.50 (nobody pressing) | CVD rank ≥ 0.80 (one side pressing, grounds' ONE_SIDED) |
| d | both ATM options below their own session VWAP (decay on both sides) | either ATM option at or above +1σ over its own VWAP |

A NEITHER day prints both halves of the REGIME and the four facts as facts,
with no count.

## 3. Q2: which side

- **BUYING, calls:** buy CE. **BUYING, puts:** buy PE.
- **SELLING:** write the side or sides whose **nearer front is BUILDING**,
  named with the wall strike and its distance from spot. In a PIN both are,
  so it reads "both sides".
- **NEITHER:** no side, and it says why.
- **No strike, no size, no price.** The walls are named as facts.

## 4. Q3: the cleanest index

- Only indices whose day word is not NEITHER can be cleanest. Order them:
  1. **zero against** first;
  2. then **more "for"**;
  3. then **fewer "could not check"**.
- A tie is named as a tie. When no index is clear: "none is clean right now",
  with each index's reason.
- **BANKNIFTY context** (research-findings §3): it trends and inverts every
  reversion test, and the fade gate caps it at soft. This is printed beside
  it and never counted.

## 5. Q4: is the engine's current trade a good call?

**The engine's trade** is the zone machine's latest arm or entry on that index
in the **last 15 min**. If there is none: "checked, none — no zone arm or
entry in the last 15 minutes". Three facts, printed together:

1. **The §1d gate as logged on that row.** LEGAL or ILLEGAL, and why.
2. **Agreement with Q1.**
   - A zone BUY (fading a fall at d2) agrees with a BUYING-calls day, or with
     a SELLING day where the PE front is building.
   - It is **against** a BUYING-puts day.
   - A zone SELL is mirrored.
3. **The engine verdict's grounding at `t`**, from the calls log, with its OI /
   CVD / FLOW facts. Before 2026-09-24: "could not check — the calls log
   starts on 2026-09-24".

**The call in words:**
- **"a good call"**: gate LEGAL, agrees with the day, grounding not
  CONTRADICTED;
- **"a bad call"**: gate ILLEGAL, **or** against the day, **or** CONTRADICTED;
- **"thin"**: anything else.

It always prints which facts decided it.

## 6. Q5: the best trade and the second best

Each index with a clear day offers **expressions** of the same view:

- **BUYING in D:**
  - the primary is the buy (CE for up, PE for down);
  - the secondary is the **writer's** version: write the opposite side (CE on
    a puts day, PE on a calls day), **only if that side's nearer front is
    BUILDING**, i.e. its writers are holding the wall.
- **SELLING:** the primary is "write the building side(s)". There is no
  secondary.

Order all expressions from all three indices:
1. zero against;
2. more "for";
3. primary before secondary;
4. fewer "could not check".

**Best** is the first, **second best** the next. Fewer than two gives "no
second best — why". Ties are named.

## 7. "Did I enter into the wrong trade?" (only when she is in a trade)

Her trade (index, CE/PE, long/short) is read against **her index's** day word:

- **AGREES:**
  - a buyer in the day's direction on a BUYING day;
  - a writer of the opposite side on a BUYING day, while that side's front is
    building;
  - a writer on a SELLING day, on a side whose front is building.
- **AGAINST:**
  - a buyer against the direction;
  - **a buyer on a SELLING day** ("you are paying time on a writers' day");
  - a writer on the side the BUYING day is running into.
- **UNCLEAR:** a NEITHER day. It says so, and does not guess.

It is joined with the HOLD/FOLD window's own **entry read**. "Entered into
FOLD" is said as **"you entered into a broken setup"**.

- **The panel opens beside the window** when the check is AGAINST or the
  entry read is FOLD.
- Otherwise it stays one line: "your trade agrees with today's read".
- Either way it shows the best and second-best trades, so she can see what
  the facts favour instead.

## 8. The face

- **Light, and no charts.**
- **At most 5 lines when open:**
  1. the day word;
  2. the side;
  3. the cleanest index;
  4. the engine check;
  5. best and second best.
- **Each line** is followed by its facts, tagged [M] or [I].
- **Collapsed**, it is one line.
- **No sound.** The window already owns the one tone.
- **Absence** is always one of three sentences: "checked, none" / "could not
  check — why" / "not showing you — why".

## 9. Parameters (none is new)

- `PERSIST = 3` and `RECENT = 15` (the window's numbers).
- `STRONG = 0.50` and `ONE_SIDED = 0.80` (grounds).
- ±1σ (the contract bands).
- The board's REGIME and STRONG as they are.
- Not grid-searched. Changing one is a new registration.

## 10. Predictions and falsifier (committed now)

**Predictions:**
- **P1.** The same rule reads a range day and a trend day differently. On
  2026-09-23 SELLING or NEITHER covers most minutes on NIFTY. On 2026-09-24
  BUYING-puts covers most SENSEX minutes after 10:15. If the two days read
  alike, the read is noise.
- **P2.** At her 09-23 NIFTY call re-entries, the check reads AGAINST or
  UNCLEAR more often than AGREES.
- **P3.** On a clear day, the best expression's ATM premium moves her way over
  the next 30 minutes more than the second best's does, and the second best
  more than the opposite expression.

**Falsifier:** over ≥ 15 forward stamps of each day word (house rule: under 15
is inconclusive), the read is deleted, not tuned, if any of these holds:
- the best expression's 30-min favourable excursion is **not** larger than
  the opposite expression's; **or**
- the read gives a clear day word on **fewer than 1 in 10** minutes over 10
  sessions (a rule that never binds, as in §1d); **or**
- the result collapses once the single best day is removed.

## 11. Changes after seeing data

(The old text stays above. Any change goes here, with its time read from the
clock and its reason.)

**11.1 — 2026-09-25 00:56 IST (clock). A PROPOSAL MADE AFTER SEEING DATA. NOT
applied.** The draft is unchanged, and the prototype shows this only as a
labelled toggle.

**What the replay showed.** The draft's day word is the board's REGIME, and
REGIME needs price **and** OI to agree. It gave a clear word on **6 to 8 % of
readable minutes on every index-day**. For example:
- NIFTY 09-23 was SELLING for 30 of 360 readable minutes;
- SENSEX 09-24 was BUYING puts for 27 of 361.

The reason: the OI half (`board.oi_read`, the nearer fronts' BUILDING state)
reads **BOTH LEAVING on about half of every day's minutes**, and flips between
TREND UP and TREND DOWN on most of the rest. The price half alone is
steadier:
- SENSEX 09-24 read TREND DOWN on 172 minutes;
- NIFTY 09-23 read CHOP on 228.

So at 21 of her 26 readable entries the draft said "NEITHER is clean". **By
its own falsifier (§10, "fewer than 1 in 10 minutes") it is heading for
deletion.** That is the result, and it is recorded, not hidden.

**The proposal (B-11.1):**
- take the day word from **REGIME's price half** (5m / 15m / 1h all one way
  = BUYING; two RANGE = SELLING; otherwise NEITHER);
- **count the OI half as fact (e)** instead of letting it gate:
  - on a BUYING day, OI reading the same trend is "for" and the opposite
    trend is "against";
  - on a SELLING day, PIN is "for" and a trend is "against".
- Seen on these three days only, it binds on about half the minutes, and it
  reads 09-23 (SELLING) and 09-24 (BUYING puts) differently.
- But it **lags at the turns**:
  - on 09-22 at 10:32 it still read BUYING calls into the fall;
  - on 09-24 at 14:23 it still read BUYING puts at the low.
- It must be registered with its own falsifier before it is used.
