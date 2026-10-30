# RAFTAAR — Fable, round 1 (blind) · 27 Oct 2026

Files here: `raftaar.py` (the engine + causal replay, stdlib), `replay_all.py` → `replay/<IDX>_<day>.txt` + `replay/SUMMARY.txt`
(30 index-days), `survey.py` / `explore.py` / `timeline.py` (the exploration that decided the definitions), `mockup.html` (LIGHT, the
26 Oct 10:00 state). Nothing outside this folder was written. Every number below is [M] from the chain record unless tagged [I].

## 1. The trader's question

1. Is a MOVE happening now — which way, are the writers WITH it or FIGHTING it, is it starting / pressing / tiring?
2. Or is price CHOPPING (legs both ways, nothing building), or PINNED / being LOADED at a strike (writers taking turns)?
3. If nothing cleared the noise bar, say that in one line and shut up; stamp a line only when the graded story changes.

## 2. What the record said before anything was defined (do not skip)

- **Size is calendar-driven, so no fixed lakh floor can work:** BANKNIFTY's nine-strike OI change at the close was 0.3–4 L on
  non-expiry weeks and **64 L on its monthly (27 Oct)**; SENSEX builds on Thursdays (196 L on 22 Oct) and is thin on Tuesdays
  (14 L on 27 Oct); NIFTY expiry days run 2× the %-turnover of other days (`explore.py`). Floors must be the day's own.
- **The writers' lean does not predict the next 5 min** (lean(t) vs spot(t..t+5), both above their medians): 8 Oct 37 with /
  57 against; 22 Oct 31 / 59; 26 Oct 57 / 33; 30 Sep 56 / 36. Coin-flip to inverted. Consistent with oi-lab (OI speed does not
  separate holds from breaks). **RAFTAAR is a state read of now. It is never sold as hold/break.**
- **Coincident agreement differs by day kind:** trend-down days 70/106 (8 Oct) and 72/109 (21 Oct) agree; chop 47/104 (22 Oct);
  the up day 26 Oct **inverts, 34/108**: in the afternoon grind up, CE writers ADDED into the rise and PE writers booked (12:25–13:00
  CE +10/+11/+20 L with PE −10/−9/−29 L, spot +22/+19/+16) until the **14:10 squeeze (CE −116 L, +32 pts)**. So a signed lean
  cannot name the state; the writers' flow must be split into WITH the move (losers covering + winners chasing) and AGAINST it
  (adding into the move), and read by zone across strikes.
- **The textbook leg exists and is loud:** 26 Oct 09:55–10:10 CE −60/−121/−75 L and PE +26/+107/+56 L per 5 min with spot
  +84/+90/+52. **Effort without result exists:** 25 Sep 09:40–10:05 CE +30/+30/+25 L per 5 min while spot sat at 23,050 → 10:10
  reversal (CE −33 L, PE +23 L). **Her roll exists:** 27 Oct 12:42 CE 22700 covering while 22850 CE added, spot +56 (cap rolled up).

## 3. Measures (per minute, the /api/oihist grid, causal)

| name | definition | tag |
|---|---|---|
| nine, atm | §1d's 9 strikes nearest spot; atm = nearest | §1d |
| zones | CE **near** = strikes ≤ atm (call writers at / under water if price rises), CE **wall** = > atm; PE near = ≥ atm, PE wall = < atm | [I] |
| d(k, s, w) | OI change of strike k side s over w min (5 and 15; 45 for PIN). Strikes absent at t−w: skipped, counted | [M] |
| zone net, votes | Σ d over the zone; a strike votes up/down when \|d\| ≥ §1d stall rate × w × its own OI (5 % per 15 marks) | [M] / §1d |
| adds, cuts | the side's gross writing / covering over w on the nine | [M] |
| floors f | per side, medians over the **last 60 marks** of \|zone net15\|, adds15, \|zone net5\|, adds5 — "the day's distribution at that time" | [I] |
| bar, BADA | a flow clears the bar at **1.5 × its floor**; BADA at **3 ×** | [I] |
| P | "a move" = **0.18 % of the first spot** (effort.py / oi-lab THR_PCT): NIFTY ≈ 41, BNF ≈ 99, SENSEX ≈ 132 pts | [I] |
| LEG | a mark with \|m15\| ≥ P, carrying its direction | [M] |
| with / against | with = losing-side cuts + winning-side adds; against = losing-side adds (winning-side cuts = booking: a number, decides nothing) | [I] |

## 4. The combination table (all states, definitions, grades)

### 4a. Side patterns over 15 min (fall back to 5 min against the 5-min floors when both sides read QUIET: a sharp turn, flagged "abhi")

Read on the side that LOSES if the move continues (CE when price ▲, PE when ▼), T = 1.5 × f_net:

| losing side | near | wall | trader's name | what it means to her |
|---|---|---|---|---|
| ROLL | ≤ −T | ≥ ½ \|near\| | cap rolled up / floor rolled down | still short, wall moved; the new wall is named (her 22600/22700 → 22800 example) |
| RETREAT | ≤ −T | < ½ \|near\| | bhaag rahe | covering at / under water with no new wall: forced fuel |
| ABSORB | ≥ +T | any | ulta likh rahe | writing into the move at / under spot: a wall if price stalls, fuel if it does not |
| WALL BUILD | inside | ≥ +T | deewar ban rahi | a cap / floor ahead, named |
| WALL LIFT | inside | ≤ −T | deewar hati | the wall ahead is leaving: open road |
| QUIET | inside | inside | chup | — |

On the side that WINS: **PRESS** (adds15 ≥ 1.5 × f_add: saath likh rahe), **BOOK** (near ≤ −T: munafa booking), **QUIET**.

### 4b. Price ▲ (m15 ≥ +P) × CE pattern × PE pattern → the story (mirror every row for ▼ with PE losing, CE winning)

| CE (losing) | PE (winning) | story on the face | qualifier (by with/against) | grade inputs |
|---|---|---|---|---|
| RETREAT | PRESS | CHAL RAHA ▲ · CE bhaag rahe k · PE saath likh rahe k | SAATH | both zone sizes, both strike votes |
| RETREAT | QUIET / BOOK | CHAL RAHA ▲ · sirf CE bhaag rahe (short-covering leg) | SAATH | CE near size, CE votes |
| ROLL | PRESS | CHAL RAHA ▲ · cap k1→k2 · PE saath | MILA-JULA or SAATH | near cut + wall add agreement |
| ROLL | QUIET / BOOK | CHAL RAHA ▲ · cap k1→k2, koi saath nahi (writers managing it) | MILA-JULA | as above |
| ABSORB | PRESS | CHAL RAHA ▲ · ladai: CE ulta k vs PE saath | MILA-JULA / ULTA | both sizes |
| ABSORB | QUIET / BOOK | CHAL RAHA ▲ **ULTA** · writers fading the rise (26 Oct 12:25–13:00) | ULTA | CE near size |
| WALL BUILD | PRESS | CHAL RAHA ▲ · PE saath, cap ban rahi k (room till k) | SAATH / MILA-JULA | wall size |
| WALL BUILD | QUIET | CHAL RAHA ▲ · cap ban rahi k, koi saath nahi | MILA-JULA | wall size |
| WALL LIFT | any | CHAL RAHA ▲ · cap hati k, upar khula | SAATH | wall size |
| QUIET | PRESS | CHAL RAHA ▲ · PE likh rahe, CE chup | SAATH | PE adds size |
| QUIET | BOOK | CHAL RAHA ▲ · PE booking, koi nahi lad raha | MILA-JULA | PE near size |
| QUIET | QUIET | CHAL RAHA ▲ **BINA OI** · price akela — if an opposite LEG sat inside 30 min → **CHOP** (a chop leg) | BINA OI | price only (\|m15\|/P) |

Qualifier rule: BINA OI when both QUIET; ULTA when against ≥ with; SAATH when with ≥ 2 × against; else MILA-JULA.
**Phase** on with5 (the WITH flow over the last 5 min): SHURU (first 3 marks) · **TEZ** (with5 ≥ 1.5 × with5 five marks ago, at a new
15-min extreme) · **THAK RAHA** (3 marks of with5 ≤ ½ the move's peak with5, or m5 against the move while against5 ≥ with5 = effort
without result) · else BARABAR. Only TEZ and THAK RAHA re-stamp.

### 4c. Price flat (|m15| < P)

| word | definition | her meaning |
|---|---|---|
| **CHOP** | a LEG ▲ and a LEG ▼ both inside the last 30 min, and no LEG with OI behind it now | upar-neeche, kuch nahi ban raha |
| **PIN k** | both sides net adding over 45 min ≥ 3 × T each, spot range45 < 2 P; k = biggest CE+PE add. "balanced" when CE/PE OI at k within 25 %. "dono deewar CE k1 / PE k2" when the adds sit at the walls, not at spot | dono likh rahe, equal |
| **PIN k · baari-baari** | a LOAD of one side, then a LOAD of the other within 45 min at the same strike (±1 step), range45 < 2 P, both sides net adding over 45 | writers taking turns at one strike (27 Oct 22750) |
| **UNWIND** | both sides net15 ≤ −T | dono nikal rahe; after 15:00 "band ka unwind" |
| **LOAD side k** | one side net15 ≥ 3 × f_net (BADA), the other < T | dwell-and-load / a wall absorbing with price flat |
| **KHAMOSH** | nothing above | kuch khaas nahi |
| SOCH RAHA | fewer than 10 marks of 15-min history, or a hole in the lookback: the reason is printed | could not check |

### 4d. GRADE = a count of checks, never a %

size ≥ bar · size ≥ BADA · held ≥ 3 marks · held ≥ 9 marks · strikes agree (≥ 2/3 of the voting strikes in the story's zones go its
way) · peers agree (both other indices showed the same word + direction within 3 marks). **5–6 PAKKA · 3–4 THEEK · 1–2 HALKA.** CHOP
has no strike check (/5). KHAMOSH has no grade. SENSEX is graded on its own OI (§1q: its flow is NIFTY's, not used here).

## 5. Significance: when a line is stamped

- The **story key** = (word, direction, ULTA / BINA OI / with, TEZ / THAK RAHA). Side patterns, strikes and grades are the key's
  explanation and may update live without a stamp (PRESS ↔ QUIET flickers minute to minute on every real move; keying on it starved
  the 25 Sep 10:10 reversal of its 3-mark hold).
- A new key must **hold 3 one-minute marks** (her bar) and is stamped at its first mark. Full-day replays stamp **20–37 lines**
  (10–19 on the half day); the face shows the current story big and the last 3 stamps, the rest under "sab".
- **Front stamps** = §1d's own BUILDING / STALLED / UNWINDING on the top-2 per side (`fronts.read`'s rule, verbatim), held 3 marks,
  entering the top-2 is not a change; "phir BUILDING" = her "again started building"; UNWINDING while the same side's next strike
  outward is BUILDING reads **SHIFT → k2**. 36–90 changes a day: shown as the 4 fronts' current state + each one's last change,
  the list under "sab".
- Three absences are three sentences: KHAMOSH (checked, nothing cleared the bar) · SOCH RAHA + reason (could not check) · the
  "sab" fold (not showing). A strike missing from the record at t−w is skipped and counted, never a zero.

## 6. The one-glance screen (LIGHT; `mockup.html` is the 26 Oct 10:00 state with real numbers)

```
RAFTAAR · NIFTY   10:00   spot 22,649s · fut 22,752f   15m +167 · 60m +227 · din +197   DIN(§1o) MIXED 9 bars   floors CE 6.1L PE 7.4L/15m
┌─ ABHI ──────────────────────────────┬─ CALL WRITERS · losing side ─────┬─ PUT WRITERS · winning side ─────┐
│  CHAL RAHA ▲            (34 px)     │  RETREAT · bhaag rahe            │  PRESS · saath likh rahe         │
│  SAATH · BARABAR · since 09:57      │  22500 −48L  22600 −31L  22700 −12L│  22600 +52L  22500 +33L  22400 +9L│
│  PAKKA 5/6  size 11× ✓✓ held 4 ✓    │  near ≤22650  −91L/15m  −60L/5m 4/4▼│  near ≥22650 +58L  +31L  3/4▲    │
│  strikes 4/4 ✓  BNF ✓ SENSEX ✓      │  wall >22650   +2L       +1L  1/4▲ │  wall <22650 +94L  +41L  4/5▲    │
│  with ▓▓▓▓▓▓▓▓▓▓ +323L  against 0   │  speed: 60L vs 71L 5m ago BARABAR │  speed: 72L vs 48L 5m ago TEZ    │
│  READ: RANGE · RAFTAAR: CHAL RAHA ▲ SAATH — CE 22500 −48L / PE 22600 +52L in 15m, +167 pts                 │
├─ KRAM · jab kahani badli (newest first) ────────────────────────────────┬─ §1d FRONTS · abhi ─────────────┤
│ 09:57 22,634s CHAL RAHA ▲ SAATH shuru  CE RETREAT 22500 −20L/5m · +190/15m  THEEK 4/6 │ CE 22500 UNWINDING 09:54 −48L│
│ 09:41 22,480s KHAMOSH  kuch khaas nahi · floors read from 09:41              —        │ CE 22800 UNWINDING 09:56 −11L│
│ ▸ sab (2) · front changes (6) ▸                                                       │ PE 22600 BUILDING  09:58 +45L│
│                                                                                       │ PE 22400 STALLED   10:01  −2L│
└───────────────────────────────────────────────────────────────────────────────────────┴──────────────────────────────┘
```
Big: the word, its arrow, SAATH/ULTA, the grade word. Medium: the two side patterns with their strikes and the with/against bars.
Small: zone tables, speed line, the KRAM rows. Hidden until asked: the full KRAM, all §1d front changes, the floors' history, the
peers' own words. No price chart. Every level is s (spot); the header carries fut and the measured basis. Hinglish chips carry every
glyph (▲ = upar, bhaag rahe, likh rahe, deewar, baari-baari). 3 columns at 1229 px, no page scroll.

## 7. Replay: what it would have said, and when (rows, not rates)

`replay/` holds all 30 timelines; `replay/SUMMARY.txt` the minute census per word. Stamped lines, abridged (full text in the files):

**NIFTY 8 Oct — trend down, −1.4 %** (23 stamps, 71 front changes)
```
09:45 22459s CHAL RAHA ▼ SAATH shuru   PE RETREAT 22500 (abhi) CE PRESS 22500  with15 +53L against15 +27L  m15 −63   THEEK 3/6 peers 2/2
10:14 22487s PIN 22500 balanced        net45 CE +133L PE +46L  r45 74                                           HALKA 2/6
11:22 22405s CHAL RAHA ▼ SAATH shuru   PE RETREAT 22450 (abhi)                  with15 +15L against15 +2L   m15 −42   THEEK 3/6
11:26 22359s CHAL RAHA ▼ SAATH TEZ     PE RETREAT 22500 CE PRESS 22400         with15 +90L against15 +32k  m15 −85   THEEK 4/6 peers 2/2
11:40 22362s LOAD CE likh rahe 22350   net15 +67L  m15 +2  (the cap re-laid on the pause)                        THEEK 4/6 peers 2/2
13:52 22237s CHAL RAHA ▼ SAATH shuru   PE RETREAT 22200                         with15 +22L  m15 −42                 THEEK 3/6 peers 2/2
15:13 22203s UNWIND band ka unwind     CE −26L PE −12L
minutes: KHAMOSH 240 · LOAD 49 · CHAL RAHA ▼ SAATH 30 · UNWIND 17 · PIN 6 · CHOP 5
```
**NIFTY 21 Oct — top at 09:58, then −470** (24 stamps). THE READ: RANGE 09:50, LEAN ▼ 10:10, TREND ▼ 15:20.
```
09:57 23033s CHAL RAHA ▼ SAATH   PE QUIET (abhi) CE PRESS 23100   with15 +46L against15 +7L  m15 −73    THEEK 3/6 peers 2/2
10:05 22972s CHAL RAHA ▼ SAATH   PE RETREAT 23100 (abhi)          with15 +66L               m15 −78    THEEK 3/6 peers 2/2
10:13 22927s CHAL RAHA ▼ SAATH   PE RETREAT 23000                 with15 +83L               m15 −104   THEEK 3/6 peers 2/2
11:19 / 11:31 THAK RAHA / 11:40 / 12:12  four more ▼ SAATH legs, PE RETREAT 23000→22950→22800, CE PRESS 22950/22900
13:11 22727s CHAL RAHA ▼ ULTA    PE WALL BUILD 22700 (puts laid under the fall) → 13:17 PIN 22700 baari-baari (CE +20L / PE +15L over 45) → 13:50 LOAD CE 22700
15:12 22734s CHAL RAHA ▲ SAATH   CE RETREAT 22900 (the close bounce)
minutes: CHAL RAHA ▼ SAATH 65 · KHAMOSH 180 · LOAD 31 · CHOP 18 · PIN 18
```
**NIFTY 22 Oct — her "range day, chop on both sides"** (37 stamps): **CHOP 128 min**, the most of any day; legs 10:23 ▲ SAATH (CE
RETREAT 22600, +103), 10:30 THAK RAHA, 10:48 **▼ ULTA · PE ABSORB 22700 · CE BOOK** (the dip bought by put writers — it held),
11:43 ▼ SAATH, 11:55 THAK RAHA, 12:52 ▲ SAATH, 13:24 ▼ MILA-JULA, 14:40 ▲ SAATH; CHOP re-stamped 7×.
**NIFTY 26 Oct — late start 09:33, bottom then +1.3 %** (28 stamps). THE READ: RANGE 09:45–10:05, TREND ▲ 10:10.
```
09:57 22634s CHAL RAHA ▲ SAATH shuru   CE RETREAT 22500 PE QUIET   with15 +183L against15 0   m15 +190  THEEK 4/6 peers 2/2   (first eligible minute)
10:00 22649s   … PAKKA 5/6 (CE RETREAT 22500 PE PRESS 22600, with15 +323L)                      — READ: RANGE
10:06 22667s CHAL RAHA ▲ SAATH THAK RAHA (with5 fell under ½ its 10:00 peak; the leg topped 10:08 at 22,699)
10:30 22640s CHOP · 11:37 ▼ SAATH PE RETREAT 22600 · 12:17 LOAD PE 22600 · 13:21 ▲ SAATH · 13:27 LOAD PE 22600 · 13:49 LOAD PE 22700
14:11 22699s CHAL RAHA ▲ SAATH shuru   CE RETREAT 22700 (the squeeze, −116L/5m)                            THEEK 4/6 peers 2/2
15:06 UNWIND band ka unwind
```
**NIFTY 25 Sep — range / pin, 23,040–23,130** (21 stamps): 10:02 PIN 23100 balanced (net45 CE +233L PE +187L), 11:14 PIN 23100
baari-baari, then LOAD CE 23100 / LOAD PE 23000 in turns, 14:00 ▲ SAATH CE RETREAT 23000, 14:05 CE −310L/5m (the squeeze),
14:59 UNWIND. **PIN 22 min, CHAL RAHA 18 min, zero CHOP legs with OI.** 23 Sep (expiry range): KHAMOSH 248 · LOAD 54 · PIN 20 ·
no CHAL RAHA at all.
**NIFTY 27 Oct — today, monthly expiry, to 12:5x** (11 stamps). THE READ: LEAN ▲ from 09:50.
```
09:42 KHAMOSH · 10:20 22696s CHAL RAHA ▼ SAATH PE RETREAT 22650 (abhi) with15 +72L m15 −94 (the flush) · 10:30 CHOP
11:01 22766s LOAD PE likh rahe 22750 +142L · 11:24 22739s PIN 22750 · baari-baari balanced (net45 CE +28L PE +227L, r45 57)
12:42 22812s CHAL RAHA ▲ SAATH shuru   CE ROLL 22700→22850  PE PRESS 22800   with15 +129L against15 +36L  m15 +56   (her example, live)
```
**BANKNIFTY 8 Oct** (24 stamps, numbers in thousands on a non-expiry week): 11:25 54780s ▼ SAATH PE RETREAT 54800 + CE PRESS 55000,
m15 −143, THEEK 4/6 peers 2/2 — the same minute as NIFTY's 11:22–11:29 leg; 13:51 and 14:04 ▼ SAATH CE PRESS 55000/54500; 10:02
PIN · dono deewar CE 55000 / PE 54800 (the walls, not spot), 11:10 PIN 55000 baari-baari. **SENSEX 22 Oct** (expiry, 34 stamps): 09:46 ▲ SAATH **CE ROLL 73200→73300 (abhi)**; CHOP 82 min;
11:54 ▼ SAATH THAK RAHA PE RETREAT 73500 + CE PRESS 73200, with15 +139L, m15 −340 (the expiry flush). **NIFTY 23 Oct**: 09:53 ▼ SAATH,
**10:02 TEZ** (with15 +156L, −103), 10:22 LOAD CE 22500 +105L, **13:42 ▲ SAATH TEZ** (CE RETREAT 22500 + PE PRESS 22500, +154).

Census across the 30 index-days: trend days 30–87 min of one-direction CHAL RAHA SAATH; 22/23 Oct 60–128 min CHOP; range days
PIN 12–54 min and no CHAL RAHA; KHAMOSH is the majority word on every day (78–296 min). Stamped lines 10–37.

## 8. Where it meets §1d, §1o and THE READ (one voice, contradiction allowed with numbers)

- **§1d** is reused, not copied: the front stamps call `fronts.read`'s rule on §1d's own fronts and add the two things the Board lacks
  (STALLED → "phir BUILDING", and SHIFT → k2). RAFTAAR's zone read contradicts §1d exactly where her addendum says it should: a front
  reading UNWINDING while its side's next strike out is BUILDING prints **"§1d: 22700 CE UNWINDING · RAFTAAR: SHIFT → 22800, cap
  rolled, still short"** (27 Oct 09:44 CE 22700 → 22750; SENSEX 22 Oct 09:46). No §1d number is changed; `fade_gate` is untouched.
- **§1o** answers a different clock: a whole-day type (A37: cumulative, CHOP for good after 4 crosses). RAFTAAR is a 15/30/45-min
  state. The header shows **DIN (§1o)** beside **ABHI (RAFTAAR)**; both can be true (23 Oct: DIN CHOP by the close, ABHI CHAL RAHA ▼
  SAATH at 09:53–10:05 and ▲ TEZ at 13:42). What OI speed adds that §1o lacks: the writers' WITH/AGAINST split, the roll, the strike,
  and a read that starts at 09:41 instead of after 10 one-sided bars. Where RAFTAAR disagrees it prints the line with numbers; it never
  prints a second day type.
- **THE READ / DECODE**: the contradiction line sits under the word, numbers first. Replayed cases: **26 Oct 10:00** "READ: RANGE ·
  RAFTAAR: CHAL RAHA ▲ SAATH PAKKA 5/6 — CE 22500 −48L / PE 22600 +52L in 15 m, +167 pts" (READ turned TREND ▲ at 10:10, after the
  10:05 high); **21 Oct 09:57** "READ: RANGE · RAFTAAR: CHAL RAHA ▼ SAATH — CE PRESS 23100 +46L, −73 pts" (READ: LEAN ▼ at 10:10);
  **27 Oct 11:24** "READ: LEAN ▲ · RAFTAAR: PIN 22750 baari-baari, CE +28L / PE +227L over 45 m, range 57". Silent disagreement is
  impossible by construction: the line prints whenever the words differ and RAFTAAR's grade is ≥ THEEK; on HALKA it prints nothing
  against THE READ (disagreement on noise is forbidden).
- **oi-lab** is honoured: no hold/break claim, no %, the futures leg is not pretended (see §9).

## 9. What I could not check, and 3 questions for her

Could not check: (a) the **futures leg** (fut OI × price) and the tape are not in this round — the brief allowed them as optional and
I kept the read to the chain so SENSEX reads identically on its own OI (§1q); (b) the **first 15 minutes after the first word
(~09:41–09:56)** under-read: the floors are still the opening's own churn, so 25 Sep 09:46 (CE +60L / PE −43L) printed BINA OI; a
previous-session seed would fix it but breaks the anytime-start rule's simplicity — left open; (c) **slow grinds**: 6 Oct (+0.8 %
expiry, 2 mean crosses) never moved ≥ P in any 15 min and the adaptive floor normalised the all-day put writing (+924L), so the day
read KHAMOSH / PIN 22700 / UNWIND — RAFTAAR reads pace changes, the steady state is §1o's and the header's din/60m numbers; (d) days
with holes (12 Oct, 16 Oct, 18 Sep) were not replayed; (e) `onesided_log` holds only 23 Oct onward, so §1o's word is quoted from the
NOTEPAD for earlier days; (f) nothing was fetched from the live server (one GET budget unused: the record on disk was enough).

Questions:
1. **PIN at spot vs PIN at the walls** — today's 11:34 "PIN 22800" and BANKNIFTY 8 Oct 10:02 "dono deewar CE 55000 / PE 54800": one
   word for both, or is only the at-spot straddle her PIN?
2. **LOAD on the face or under the fold?** It is her dwell-and-load (one side writing ≥ 3× its floor with price flat) and the most
   frequent non-quiet word (30–67 min a day); if it reads as "likh rahe" noise to her, it goes under the fold and only PIN surfaces.
3. **THAK RAHA by flow fading vs by price stalling** — 26 Oct 10:06 fired on the covering burst fading (the leg topped at 10:08);
   should the bell ring only when price also stalls (effort without result), or on either?

Least sure of: the **1.5× / 3× rolling-hour floors** — they are the simplest "day's own distribution at that time" and they separated the
days, but they also make a steady regime invisible after an hour (6 Oct), and I chose them from these 30 index-days, not from a rule
she wrote.
