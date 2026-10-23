# Right panel v3: design draft (20 Oct 2026, for the mockup and the critique; not yet approved by Mary)

**Inputs:**
- `EXTERNAL.md`: what the best tools measure.
- `INTERNAL.md`: what our data can honestly measure.
- The rules in `../superpowers/specs/2026-10-19-extension-v2-design.md` §1.

**Mary's ask:** "measure the rate of change and speed of change of both side buyers or sellers in terms of order flow
reading, and goes for OI changes as well, rate of change of OI and the speed by which they have been building, gives a
clear understanding of trend, and we need an eye at other index as well."

## The reading order: four questions, top to bottom
The header stays. Then come four blocks of 1–3 rows each. SIRF BADE, PLAN and ? stay below and get shorter.

```
NIFTY  RIDE ▼ 13:15 se                 22,888f | 22,860s        14:30
P phase · R roka · T thakan · Z zor · B bada · ✕ toota

KAUN DABA RAHA        pace (5m vs is waqt ka normal)   speed (5m vs 30m)
  BECHNE WALE         2.4×  ▮▮▮▮▯                       tez ↑   peak 14:12
  KHARIDNE WALE       0.9×  ·                           ·
  EK-TARFA (15m)      sellers 68%                       GC+UX ✓

KAUN LIKH RAHA        build (15m, ATM±2)    speed (15m vs 60m)   sabse tez strike
  CALL                +18L  ▮▮▮▮▯           tez ↑                23,000  +9L
  PUT                 −3L   ·               nikal rahe           22,900  −4L
  FUT OI              +4L · price ↓  →  naye short

TREND                 ▼ price  ▼ flow  ▼ call likh  ▼ fut   4/4 saath · 13:15 se

DOOSRE INDEX
  BANKNIFTY           ▼ −1.1σ   pace 1.3×   call likh tez    saath ✓
  SENSEX (15m)        ▼ −0.4σ   pace ·      OI flat          low confirm nahi ✗
```

## Rules (each one exists because of a finding)
1. **Noise stays silent.** A cell below p70 for its slot prints a grey `·`, with no words and no arrow. (Mary: "a small
   +ve or −ve change doesn't matter.")
2. **The unit is "× normal".** A side's 5-min lots are divided by the median of the same 5-min slot on prior days of the
   same day kind. The bar fill and colour carry the rank; the p-number shows only on hover. A provisional reference
   (N < 30 days) shows a small grey `kam data`, never `N6`.
3. **Speed is a ratio, not a difference.** Speed = the 5-min rate ÷ today's own 30-min rate. "Rate now minus rate 5
   minutes ago" keeps its sign only 38% of the time; the ratio keeps its side 62% of the time.
   - The ratio is within the day, so a high-volume day doesn't light everything (day-volume correlation 0.76–0.90).
   - Words: `tez ↑` (≥ 1.5×), `dheema ↓` (≤ 0.67×), otherwise `·`.
   - **Peak marker** (Jigsaw): the time of the highest 5-min pace in the last 30 min. Once pace is below 0.6 × peak, it
     reads `peak se neeche`.
   - The speed column starts at 09:47 and reads `09:47 se` until then.
4. **Pace is never shorter than 5 minutes.** A 3-min rate is about 74% noise on NIFTY, 80% on BANKNIFTY and 92% on SENSEX.
   SENSEX pace and speed are 15 min.
5. **EK-TARFA** = (buys − sells) ÷ (buys + sells) over 15 min, printed as the winning side's share. It takes the
   two-source rule:
   - `GC+UX ✓` when both agree and are ≥ p70;
   - `GC only` when Upstox is absent;
   - `sources ulte` when they disagree. That happens on 29% of bars, so it caps the cell at grey.
6. **OI build** = the 15-min change summed over ATM±2 per side, ranked against the same slot and day kind. Expiry days are
   ranked separately.
   - OI speed = 15 min ÷ today's 60 min, with the same words as flow.
   - A negative build beyond p70 reads `nikal rahe` (QUIT).
   - "Sabse tez strike" is the strike whose 15-min change is largest against its own normal.
   - The OI grain is 1 min on NSE and 3 min on BSE, never finer.
7. **FUT OI × price** has a dead-band: a word (`naye long`, `naye short`, `covering`, `long nikal`) only when both the
   OI change and the price change are ≥ p70. Otherwise it reads `flat`.
8. **TREND** is the count of agreeing arrows (price, flow, OI side, fut OI) plus the READ's since-time. It is a count,
   never a probability.
9. **DOOSRE INDEX** is one row per index:
   - the move from the open in that index's own σ;
   - pace × normal (Upstox);
   - the OI state;
   - a confirm flag: if NIFTY made a session high or low in the last 15 min and the peer is not within 0.25σ of its own,
     it reads `high/low confirm nahi ✗`; otherwise `saath ✓`.
10. **The rest of the panel shrinks.** SIRF BADE becomes ≤ 3 one-line rows. PLAN is ≤ 2 rows. `?` is one line plus `…`.
    The whole panel fits 820 px with no scroll.
11. **No look-ahead.** Every number at time T uses data ≤ T and references from days before.

## Backend needed (from INTERNAL.md gaps)
- G7: one Upstox side rule everywhere.
- G5: split the references by day kind.
- G8: `frame.peers`.
- New frame keys: `frame.flowpace` and `frame.oispeed`.
- G1: the server writes per-minute GC forming-bar snapshots, building history for a later 1-min GC pace.
- G10: find out why the recorders start at 09:17.
