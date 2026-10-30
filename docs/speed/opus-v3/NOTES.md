# RAFTAAR v3 — what I would put on my own screen (Opus, 27 Oct 2026)

Open `RAFTAAR-v3.html` (one file, data inside). Rebuild: `python export.py` (`--check` = self-check only, `--page` = template only).
Engine untouched (`../final/raftaar.py`); fronts = `tapemap/fronts.py` + `board._fronts`; trapped writers = `tapemap/trapped_inventory.Ledger`.

## 1. What I would build for myself, and why

At 10:05 on a fast morning I ask four things, in this order, and I want each answered by a shape, not a paragraph:

1. **What is it doing?** One word, huge, coloured: CHAL RAHA ▲ / CHOP / PIN / KUCH KHAAS NAHI. Phase and age beside it.
2. **How sure is the read?** One number that MOVES: SAHMATI 82, i.e. 9 of 11 checks agree. If it is draining, I see it before the word changes.
3. **Where is the fuel?** Writers who sold today and are now underwater. Which side has more of it, how much, and how far price is from it.
   That is the only part of OI that *has* to trade. A wall where writers are in profit is a wall. The same wall with writers underwater is fuel.
4. **Is the push speeding up or dying?** Speed is a shape over time: the upar-zor and neeche-zor areas. Two fat equal areas = both sides
   writing = PIN / CHOP. One area filling the panel = a move. Both thin = nothing. Growing = accelerating, shrinking = tiring.

Then, on demand, the Board's question: which front stopped first, when it began giving back, and when it restarted.

## 2. Keep / kill

| from | keep | kill |
|---|---|---|
| v1 | colour as state, the strike ladder, tug-of-war, speed feel | the ladder alone (no time), the effort-vs-result quad (no one reads a scatter at speed), the day ribbon (the price path carries the colour now) |
| v2 | price × time with the ladder sharing the y axis, the one-line Hinglish sentence, OI trend 15/30/60, Board stamps | the colour-segment lanes (hatches + 4 states = the "messy bottom"), the KRAM strip, the trend heat rows, the ribbon, the three gauges, the faint future of the day (a live tool has no future), lanes picked from the whole day |
| new | — | **SAHMATI** (agreement score, never odds), **FUEL** (trapped-writer OI by side + distance + what the leg burned), **ZOR areas** (speed over time), **fronts as OI curves** (the build hump, the peak, the give-back are visible, no debounce needed), cross-index tiles |

## 3. Three sketches

```
A  ONE BIG CANVAS                        B  COCKPIT (picked)                               C  TWO COLUMNS, NO TIME
+----------------------------------+    +--------------------------------------------+    +-----------------+------------------+
| word | sahmati                   |    | NIFTY ▲82 | BNF CHOP — | SNX ▲64    day ▶ |    | word, sahmati   | fuel ladder      |
+----------------------------------+    +----------------+-------+--------+---------+    | sentence        | (strikes, now)   |
| price path + fuel bars inside    |    | WORD  phase    |SAHMATI| FUEL   |OI TREND |    | fronts 4 rows   |                  |
| the plot at each strike, zor     |    | sentence       |  82   | ▲ ███  | 15 30 60|    | zor gauges      |                  |
| as a band under the path,        |    | kya badla      | ~~~~  | ▼ █    |         |    +-----------------+------------------+
| fronts as marks                  |    +----------------+-------+-+------+---------+    fast to read, but no time:
+----------------------------------+    | price x time (s)          | FUEL LADDER      |    "accelerating / tiring" and
everything on one plot: unreadable  |    |   ◆ stamps, path = state  | same y as price  |    "when did they stop" have
at speed, chips collide             |    +---------------------------+------------------+    nowhere to live
                                    |    | ZOR upar / neeche (L/min) | abhi + raftaar   |
                                    |    +---------------------------+------------------+
                                    |    | 4 fronts: OI curves       | state · since ·  |
                                    |    |  ● ruka ○ chhod ▲ phir     | pts against      |
                                    |    +---------------------------+------------------+
```

**B.** The left column is TIME (one x axis: a vertical line through price, zor and the fronts is one minute), the right column is NOW
(the same rows read at the latest minute). The hero row answers the four questions before the eye reaches the charts. The x axis runs
from the open to now + 25 min, so the latest minute is always near the right edge and the past compresses as the day goes on.

## 4. Definitions (all display [I] on [M] records; no %, no hit rate)

- **SAHMATI** = round(100 × agreeing ÷ checkable) over the engine's own grade checks (size, aaj, bada, tika5, tika15, strikes, price, fut,
  each other index, chop ke bahar) **plus two face checks**: *OI trend saath* (the 15/30/60 verdict points the picture's way; RANGE for
  PIN / CHOP) and *fuel aage* (a move: ≥ 25 % of the hurt side's today-written OI in the nine is underwater). Colour = the engine's own
  grade word (MAZBOOT / THEEK / KAMZOR, caps unchanged). No picture (KHAMOSH, BINA OI, ?, a swing inside CHOP) = "—". It counts
  agreement; it is never a chance of being right.
- **FUEL** (per side, at the minute) = OI written today (oi_chg > 0) at the nine strikes nearest spot whose writers are underwater:
  option ltp above the writers' basis. Basis = `trapped_inventory.Ledger` (today's adds × the premium they were added at) when the record
  starts by 09:20, else the exchange's day VWAP (`avg`), and the page says which. **Up-fuel = CALL writers, down-fuel = PUT writers.**
  Distance = strike − spot (s). **Jala** = OI the hurt side gave back since the current leg began.
- **ZOR** = per minute, over the nine and the last 5 min (the engine's own `measures`, F window): upar = PUT adds + CALL cuts,
  neeche = CALL adds + PUT cuts, in lakh per minute.
- **Fronts** = §1d's top-2 per side AT THAT MINUTE (`fronts.read` on the grid cut there, ranked by open + running high, as
  `board.first_fold` does), `board._fronts` for unwind_at; *phir* = the low after the peak when the front is building again ≥ 5 % under its
  high (Board.tsx's PHIR LIKH RAHE). Rows change only when the top-2 changes: nothing is picked from the whole day.

## 5. Checked (27 Oct 2026, the page in Chrome at 1231 × 732 css px, no scroll either way)

- **5,546 minute draws** (5 days × NIFTY / BANKNIFTY / SENSEX, every minute), 0 console errors, no NaN / undefined / Infinity on the page,
  ~9 ms a draw. Played at 16 min/s on 27 Oct SENSEX: clean. File 872 KB (data gzip + base64 inside, unpacked by the browser's
  `DecompressionStream`).
- **27 Oct NIFTY vs the Board:** CALL 22,700 **ruka 09:27 · chhoda 09:42**, the Board's own `fronts.read` + `board._fronts` (asserted in
  `export.py`). At 09:50 the BOARD chip reads "CALL WRITERS CHHOD RAHE HAIN · ▲ fuel upar · 09:27".
- **22 Oct NIFTY:** CHOP 315 of 372 minutes, 6 engine stamps all day, no ≠ READ; SAHMATI shows "—" through the swings (the engine grades
  no swing), the hero never pulses outside those 6 stamps.
- **26 Oct NIFTY 09:52 move and its fuel:** 09:45 = CALL 22,500s has **94 L written today, writers +16 pts underwater, 18 pts above
  spot** (the fuel). 09:52 CHAL ▲ 5/10 → 09:55 ≠ READ → 09:58 TEZ 10/11. At 10:05 the fuel tile reads **jala: CALL −207 L since 09:50**;
  the ladder shows the burned CALL 22,400–22,500 as dashed ghosts, every PUT bar pale (PUT writers in profit: the floor), SAHMATI 92
  (12/13), OI trend ▲ 2/3, 3/3 indices saath, and the zor panel's upar area already shrinking ("upar ka zor ghat raha").

## 6. What I would still change

- **The writers' basis on a late start** (26 Oct starts 09:33) falls back to the day VWAP, which marks every CALL "underwater" on a day that
  bottomed early. The ladder shades by pain (pale → dark around break-even) so the binary line does not flicker, but the server should run
  the ledger from 09:15 every day; then this fallback never fires.
- **Thresholds that are mine, by eye on these five days** [I]: fuel aage ≥ ¼ of the hurt side underwater, the "agla" strike ≥ ¼ of the
  biggest, the zor speed words (1.5× / 30 L-per-min floor), the front word held 2 minutes. They want her feel on live days, not a backtest.
- **SAHMATI on a CHOP / swing is "—"** because the engine does not grade a swing. If she wants a number there, the engine needs a CHOP
  grade of its own; the face should not invent one.
- **Live wiring:** this is a replay; `export.py`'s per-minute pieces (`fronts_by_minute`, the ledger, `trend`, the zor) are all causal and
  map 1:1 onto `/api/raftaar` (DESIGN §9). The ladder needs `ltp` / `avg` per strike-side, which the chain record already carries.
