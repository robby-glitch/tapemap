# RAFTAAR — OPUS round 1 design (blind), 27 Oct 2026

Files in this folder: `DESIGN.md` (this), `raftaar.py` (the rule, run causally; stdlib; `--check` is its self-check),
`replay/<day>.txt` (7 days × 3 indices, every stamped line with its numbers). Every threshold below is **[I]**, fixed
before the replay rows were read. Every OI number is **[M]** off the chain record. No %, no hit rate, anywhere.

---

## 1. The trader's question

1. In the last 15 minutes, is price **moving with writers behind it**, and is that getting stronger or weaker?
2. If price is not going anywhere: are writers **taking turns (CHOP)**, **building both sides (PIN)**, or **pushing one
   side while price refuses (ATKA)**?
3. And when none of it clears the noise bar: **say "kuch khaas nahi"**, once, and nothing else.

---

## 2. The states

### 2.0 Inputs (all from `/api/oihist`'s minute grid + its `open`, i.e. absolute OI per strike-side per minute)

| item | definition | tag |
|---|---|---|
| window | read.writers' nine: ATM ± m strikes, m ≤ 4, symmetric, both OIs present (narrowed at a window edge; m < 2 → `?`) | M |
| zones | **CE**: ANDAR = strikes ≤ ATM (the calls price is at / through), BAHAR = strikes > ATM (the cap). **PE**: ANDAR = ≥ ATM, BAHAR = < ATM (the floor) | I |
| S (story window) | 15 min (SENSEX 16): each zone's OI change, one strike set (the strikes at t, both ends) | I |
| F (speed window) | 5 min (SENSEX 8) per side, and the 5 min before it ("pehle") | I |
| unit | every flow as % of the window's OI (scale-free across NIFTY / BNF / SENSEX); printed in lakh (the Board's unit) | M |
| net pressure Z | ΔPE − ΔCE over S: > 0 pushes up (put writing, call covering), < 0 pushes down | M |
| price D | spot change over S, in strike steps | M |
| fut leg (optional) | §1o's own fut_oi vote (|fut OI Δ15m| ≥ 0.10 % → sign of the fut price move); SENSEX uses NIFTY's fut (§1q) | M→I |

Why S = 15 and F = 5: NIFTY / BNF OI steps every ~63 s, so 5 min is ~5 updates. **SENSEX OI steps every ~160 s**
(2–3 min, measured on 22 Oct and 8 Oct), so its windows are 8 / 16 and its hold is 6 min: a 5-min SENSEX speed holds
1 or 2 updates and would flip on the clock, not on the market.

### 2a. Each side's STRUCTURE (the zones read together — her "covering 22,600 / 22,700 but adding 22,800" read)

A side is RUKE unless its gross zone flow (|ANDAR| + |BAHAR|) is ≥ notable (§3). Then each zone counts when it carries
≥ 25 % of that gross, with its sign:

| ANDAR | BAHAR | CE words (cap) | PE words (floor) | what a trader reads | push ▲ CE / PE |
|---|---|---|---|---|---|
| + | + | CALL likh rahe | PUT likh rahe | building the wall everywhere | −2 / +2 |
| + | 0 | CALL ATM/ITM likh rahe | PUT ATM/ITM likh rahe | writing AT price: aggressive, pressing | −2 / +2 |
| 0 | + | upar deewar moti | neeche deewar moti | thickening the wall ahead: defensive | −1 / +1 |
| − | + | **CALL roll UP** | **PUT roll DOWN** | wall moved away, **still short** (not fuel) | +1 / −1 |
| + | − | CALL roll DOWN | PUT roll UP | wall pulled onto price: pressing | −2 / +2 |
| − | − | CALL bhaag rahe | PUT bhaag rahe | full retreat: fuel | +2 / −2 |
| − | 0 | CALL ITM cover | PUT ITM cover | the trapped ones at price buying back: fuel | +2 / −2 |
| 0 | − | upar deewar hat rahi | neeche deewar hat rahi | wall ahead thinning: path opening | +1 / −1 |
| 0 | 0 | ruke | ruke | holding | 0 |

**PHANSE tag [M→I]:** when a covering side's covered strikes were *written in the last 60 min* (OI peaked inside the
hour, built ≥ half the amount now covered), the line says so: "PHANSE: 22700PE +123L 12:26 tak likha" (29 Sep 12:32).
That separates writers caught on today's move from old positions being booked.

### 2b. Each side's SPEED CHANGE (F now vs the F before; "raftaar" on the face)

| word | rule | trader read |
|---|---|---|
| SHURU | notable now, < ¼ of now before | started |
| TEZ | same sign, ≥ 1.5× before | accelerating |
| BARABAR | same sign, within 1.5× | steady |
| DHEEMA | same sign, ≤ ⅔ before | slowing |
| PALTA | sign flipped | turned (writing ↔ covering) |
| RUK | now noise, before > 2× now | stopped |
| — | noise both | nothing |

Size of "notable" here: the side's 5-min flow against its own reference (§3, metric `side_f`).

### 2c. The MINUTE STORY — every combination, top-down, the first row that matches wins (exhaustive by construction)

D = price move over S if ≥ notable for that index / day kind / day-part (§3), else 0. Z = net pressure, same rule.
L = the side the move hurts (CE on ▲, PE on ▼), W = the side it pays.

| # | when | name (▲ shown; ▼ mirrors) | trader read | defining flow (graded) |
|---|---|---|---|---|
| 0 | spot at the window edge / < S min of record / no size reference | `?` PADH NAHI SAKE / PADH RAHE / PAIMANA NAHI | could not check: never "quiet" | — |
| 1 | D ≠ 0, Z = −D, price still moving over F | CALL LIKHAI INTO RALLY · **PHANS RAHE** | writers adding while price runs through them: inventory getting trapped | Z |
| 2 | D ≠ 0, Z = −D, price stalled over F | CALL LIKHAI INTO RALLY · **ROK RAHE** | writers absorbing the move | Z |
| 3 | D ≠ 0, L covering and W writing | **CALL BHAAG + PUT LIKHAI ▲** | both engines: the strongest move | max(L, W) side size |
| 4 | D ≠ 0, L covering | **CALL BHAAG RAHE ▲** (+ PHANSE) | short covering: fuel | L side size |
| 5 | D ≠ 0, L rolled away | **CALL CAP UPAR SHIFT ▲** | the cap moved up, still short: move has a new ceiling | L side size |
| 6 | D ≠ 0, W writing | **PUT FLOOR SAATH ▲** | the floor follows price up | W side size |
| 7 | D ≠ 0, Z = 0 | **KHAALI CHAAL ▲** | price moving, no writer behind it | 0 (never graded above KAMZOR) |
| 8 | D ≠ 0, else | OI SAATH ▲ | net with the move, structure mixed | Z |
| 9 | D = 0, ≥ 2 turns of notable fast pressure in 30 min, 30-min range ≥ 1 step, net ≤ ½ range | **CHOP · BAARI BAARI** | both sides writing in turns, nothing building | fast Z |
| 10 | D = 0, Z ≠ 0 | **ATKA ▲ · ZOR HAI, PRICE NAHI** (lead side named) | effort without result: someone is absorbing, or it is loading | Z |
| 11 | D = 0, Z = 0, both sides adding (each ≥ ⅓ of the other), gross notable, 30-min range ≤ 1 step | **PIN BAN RAHA @ k s** | a pin being built | gross |
| 12 | D = 0, Z = 0, 30-min range ≤ 0.6 step, spot ≤ ½ step from k, k the most two-sided strike, CE/PE OI ≥ 0.6 | **PIN TIKA @ k s** | both sides holding equal size at the strike | (no flow; stock) |
| 13 | otherwise | **KUCH KHAAS NAHI** | checked: nothing above noise | — |

Speed (2b) and structure (2a) of both sides ride on every row; the futures leg and the other indices enter the grade
(§3), not the name.

### 2d. The HELD PICTURE (what the big word says; this is what kills the 18-cell noise)

| picture | starts | inside it | ends |
|---|---|---|---|
| **CHAL RAHA ▲ / ▼** (a LEG) | a story-1…8 move held 3 min (SENSEX 6) that is either BADA in price, or notable with Z = D (OI behind it). Inside a chop: both (a breakout) | phase: **SHURU** (first 5 min) · **TEZ** (fast Z with the leg, ≥ 1.5× the 5 min before, new extreme ≤ 3 min) · **JAARI** (moving with OI) · **RUKA** (price paused, OI not against: a pause is not a turn) · **THAK** (writers into the move, or pressure against while price stalls, or a new extreme with OI silent) | half the leg given back (min 1 step) · an OI-backed opposite move held · 2 flips of swings since it began · 30 min with no new extreme and Z not with it |
| **CHOP** | the SEQUENCE: ≥ 2 direction changes among the swings of the last 60 min, 60-min range ≥ 2 steps, net ≤ ½ range — or story 9 held | the current swing is shown small | the condition stops holding |
| **ATKA ▲ / ▼** | story 10 (or 1–2 below leg size) held | lead side named | held story changes |
| **PIN @ k** | story 11 / 12 held | k in spot (s) | held story changes |
| **KHAALI CHAAL ▲ / ▼** | story 7 below leg size, held | — | — |
| **KHAMOSH · kuch khaas nahi** | story 13 held | the time of the last real change | — |
| **?** | story 0 held: never shown as quiet | the reason | — |

**Chop day context:** a leg that starts right after two legs in a row were given back in alternating directions (within
120 min) is tagged **[CHOP ke andar: swing]** and fails the grade's "chop ke bahar" check. On 22 Oct this is the
difference between "a move" and "the next swing that will stop you out".

### 2e. Side events (stamped on their own, at most once per side per 30 min, only when 2+ strikes carry them)

| event | rule | why |
|---|---|---|
| CALL CAP UPAR SHIFT / PUT FLOOR NEECHE SHIFT (roll) | side = roll-away, notable | her example: the wall moved, writers still short |
| CALL / PUT BHAAG RAHE (price unke against) | side covering, BADA, price moving against it notable, and not already the leg's own story | a side starts covering into price, with its time |
| CALL / PUT PHIR LIKHNE LAGE (N min ruk ke) | side writing again, BADA, after ≥ 20 min RUKE | the side that stopped starts again |

---

## 3. Significance: how noise is decided, and when a line is stamped

**Size [I].** Every flow is ranked against **the same index, the same day kind (NORMAL / EXPIRY, rank.day_kind),
the same day-part (rank.PARTS)**, on up to 20 prior recorded sessions; rank.py's cut-offs: < p70 noise, p70–89
notable, ≥ p90 BADA. Fewer than 5 such sessions (BANKNIFTY's monthly expiry has 1) → **today's own minutes so far**
(≥ 30), the face says "aaj ke minute"; neither → `?`. Why each part of that:
- *day-part:* the open runs 3–10× midday (NIFTY gross 5-min flow p50 9.9 % of the window OI at 09:15–09:30 vs 1.0 % at
  12:30) [M];
- *day kind:* at the same day-part, expiry sessions' |net 15m| p50 runs NIFTY ×1.0–1.8 (biggest at the open),
  SENSEX ×1.6–2.7, BANKNIFTY ×2–8 (one expiry on record) [M]; pooling them would make every expiry minute BADA;
- *% of window OI:* BANKNIFTY's ATM strike held 1.7L each side on 8 Oct vs NIFTY's 44L [M]; only a relative unit lets
  one rule read both.
This is rank.py's machinery; in the build it becomes four more rank metrics (`side`, `z_s`, `z_f`, `d_s`), not a new
scheme.

**The size gate.** No story is graded above KAMZOR unless **its own defining OI flow** (table 2c) clears notable.
Persistence and agreement grade a flow; they never replace one. (Found in the replay: price-only moves were reading
MAZBOOT on persistence + peers alone.)

**The grade = an agreement COUNT n/N** over the checks that could be read (a check that could not be read is dropped
from N, never counted as a miss):

| check | CHAL (leg) | ATKA | CHOP / PIN |
|---|---|---|---|
| size ≥ notable · size BADA | defining flow | Z | fast Z / gross (PIN TIKA: none) |
| 5 min tika · 15 min tika | ✓ | ✓ | ✓ |
| 2+ strikes carry it | the defining zone | the defining zone | — |
| price | still moving now (F) | really stopped (F) | 30-min range in band |
| fut leg | same direction | same direction | fut quiet |
| BNF / SNX / NIFTY (the other two) | same direction | same direction | also without direction |
| chop ke bahar | not a chop-day swing | — | — |

Words: **n ≥ 6 MAZBOOT · 4–5 THEEK · ≤ 3 KAMZOR.** Printed as "6/10 MAZBOOT", and in the replay as
"at the stamp → 10 min later" (e.g. 26 Oct 09:56 "6/9→9/10").

**When a line is stamped (and only then):**
1. a held picture (leg / ATKA / CHOP / PIN) at the **first minute its grade reaches THEEK** — at its birth if born
   strong, later if the evidence arrives later (27 Oct: leg born 10:37, stamped 10:43 when it reached 4/10; 8 Oct:
   born 11:21, stamped 11:24, TEZ 10/10 at 11:26), **never** if it stays KAMZOR (shown live, small, not stamped);
2. inside a stamped leg: **TEZ** (grade ≥ THEEK) and the **first THAK**; its **END** with the reason;
3. **KHAMOSH / KHAALI** once, only after a stamped picture, only if it lasts ≥ 5 min; **?** whenever it lasts ≥ 5 min
   (could-not-check is its own sentence, never folded into quiet);
4. the side events of 2e.
A new picture must hold 3 min (SENSEX 6) before it exists at all.

Result over the 21 index-days replayed: **7–29 lines per index per day** (NIFTY 11–26), each with its numbers; the
rejected build stamped every flow flip of 18 strike-sides.

---

## 4. The one-glance screen (LIGHT; real minute: NIFTY 27 Oct 12:43, from the replay)

```
┌─ RAFTAAR · NIFTY · 12:43 · spot 22,824.5s | fut 22,840f · size ref: 8 pichhle expiry din ──────────────────────┐
│                                                                                                                 │
│   CHAL RAHA ▲  · SHURU                                   6/10 MAZBOOT                       [ ABHI · last 15m ] │  ← BIG (one word + phase), grade pill
│   CALL BHAAG + PUT LIKHAI ▲ — dono engine                                                                       │  ← medium: the story
│   spot +70 pts/15m · net +221L                                                                                  │
│                                                                                                                 │
├─ CALL (cap) ───────────────────────────────────┬─ PUT (floor) ───────────────────────────────────────────────────┤
│ CALL ITM cover        [chip: phanse call cover] │ PUT roll UP                     [chip: floor upar laaye]      │  ← 2a word + Hinglish chip
│ 22750CE −55L · 22800CE −48L  | 22950CE +4.5L   │ 22600PE −25L 22650PE −23L | 22800PE +43L 22750PE +30L        │  ← the strikes, cover | add
│ raftaar −36.0 L/min  SHURU   ▁▁▂▁▁▁▃▇          │ raftaar +3.6 L/min  —        ▃▄▃▂▂▂▂▂                         │  ← speed + OI-speed sparkline (no price)
│ §1d: CE22800 U · CE23000 U                     │ §1d: PE22700 U · PE22600 U                                    │  ← small: the registered fronts, verbatim
├────────────────────────────────────────────────┴───────────────────────────────────────────────────────────────┤
│ evidence 6/10: size ✓ BADA ✓ · 5m ✗ 15m ✗ · 2+ strikes ✓ · price ✓ · fut ✓ · BNF ✗ SNX ✗ · chop ke bahar ✓      │  ← small, one row
│ READ: LEAN ▲ (saath — no ≠ line)        DIN (§1o): ? (not replayed)                                            │  ← a ≠ line only on disagreement
├─ KRAM (stamped only, newest first) ───────────────────────────────────────────────────────────────────────────────┤
│ 12:43  CHAL RAHA ▲ SHURU   6/10  CALL BHAAG + PUT LIKHAI · 22750/22800CE −103L                                  │
│ 12:35  ATKA ▼              4/9   CALL likhai into rally · rok rahe · 22800CE +27L                               │
│ 11:46  KHAMOSH                   kuch khaas nahi                                                                │
│ 11:32  ATKA ▼              5/9   CALL likh rahe +80L, PUT bhaag, price ruka                                     │
│ 10:21  CHAL RAHA ▼ SHURU   6/10  PUT BHAAG RAHE · 22700/22800PE −66L · ≠ READ LEAN▲                            │
│ 10:03  · CALL CAP UPAR SHIFT     22700/22750CE −45L → 23000/22950CE +21L                                        │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Big:** the picture word + phase, its direction arrow, the grade pill (MAZBOOT green · THEEK amber · KAMZOR grey).
  When nothing clears noise it reads only `KHAMOSH · kuch khaas nahi · last real change 11:46` and the side panels
  collapse to one row each.
- **Medium:** the story name and its two numbers (spot pts/15m, net L).
- **Small:** the two side panels (structure word with a Hinglish chip, the strikes, speed word, an OI-speed sparkline:
  no price — the sparklines drawn above are illustrative, every other number is the replay's), the evidence row, the
  §1d chips verbatim, the one disagreement line.
- **Hidden until asked:** the per-strike 15-min grid (the old 18 cells), the reference tables (which sessions, which
  day-part), the full minute-by-minute list, the other two indices' panels (a 3-index strip of their big words sits in
  the header: `BNF KHAMOSH · SNX CHAL ▲`).
- Every level is spot (s) or fut (f); the basis is the live 3-min median (fold.BIX_MS), never a stored number.

---

## 5. Replay — causal, minute by minute, 7 days × 3 indices (rows, not rates)

`python -X utf8 raftaar.py 2026-10-08 2026-10-22 2026-09-23 2026-09-29 2026-10-21 2026-10-26 2026-10-27`
(about 30 s; a minute reads only minutes ≤ it; the size reference reads only sessions before the day). Full rows,
with each stamp's story line, both sides' strikes and the §1d fronts at that minute: `replay/<day>.txt`.
Strip legend (one char per 5 min): ▲ ▼ leg · a ATKA · ~ CHOP · P PIN · k KHAALI · · KHAMOSH · ? could not check.

**8 Oct — clean trend down (NIFTY 22,543 → 22,232).** NIFTY stamps (18): `09:47 CHAL ▼ SHURU 4/9 CALL CAP SAATH` ·
10:17 end (30 min no new low) · `10:42 CHAL ▼ 4/10→3/10` (faded) · 11:12 end · `11:24 CHAL ▼ 5/10→8/10` · `11:26 TEZ 9/10→10/10 PUT BHAAG + CALL LIKHAI, −114 pts,
net −112L` · 11:41 PUT floor rolled DOWN (22500/22450PE −13L → 22200/22350PE +19L) · `12:24 CHAL ▼ 4/10→8/10` ·
`13:19 TEZ 8/9` · 14:44 CALL cap rolled UP · 14:51 end · `14:56 ?` PADH NAHI SAKE (spot left the subscribed window): could not check, said
as such. No ▲ leg stamped
all day. BANKNIFTY: OI near ATM is thin (ATM 1.7L), most of its morning moves read **KHAALI**; its OI-backed ▼ legs
start 11:27 (PUT BHAAG 7/10). SENSEX (its expiry): `11:26 CHAL ▼ PUT BHAAG + CALL LIKHAI 7/10→8/10`; **`?` from 12:54
to the close: spot fell out of the 17-strike window** — said as "could not check", never as quiet.
`strip NIFTY ????··▼▼▼▼▼▼·kkka▼▼▼▼▼▼··▼▼▼▼▼▼▼·kk·k▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼·??????`

**22 Oct — the chop / stop-loss day (NIFTY 22,589 → 22,688, range 224).** NIFTY stamps (20): `10:24 CHAL ▲ 7/10→3/10
CALL BHAAG [CHOP ke andar]` · 10:29 CALL CAP UPAR SHIFT (22600/22650CE −15L → 22750/22900CE +12L) · `10:30 THAK 3/10
KHAALI` · 10:49 end (85 of 152 back) · `10:50 ATKA ▲ 4/9 PUT likhai into the fall · rok rahe` · `11:16 CHAL ▲ THAK
4/10→5/10 [CHOP ke andar]` · 11:33 end · `11:48 CHAL ▼ 7/10 PUT BHAAG RAHE [CHOP ke andar]` · `12:54 CHAL ▲ 6/10→8/10
CALL BHAAG` · `13:27 CHAL ▼ 7/10→8/10 PUT BHAAG [CHOP ke andar]` · `14:45 CHAL ▲ 7/10` · end 14:51. Each swing was a
real 80–150 pt OI-backed move; four of six carry the chop tag and its failed check. **Not good enough:** the 09:42 and
10:02 swings came before there was chop history to tag them, and CHOP itself was the big word only ~15 min of the day
and never reached THEEK, so it was never stamped. The day-scale "two-way" read belongs to §1o / THE READ (RANGE all
day); RAFTAAR says "swing" rather than contradicting it.
SENSEX (expiry): six swings 200–400 pts, 9/10 MAZBOOT each, with `≠ READ RANGE` at 12:57 and 13:27.

**23 Sep — range day (NIFTY 23,373 → 23,447, range 111).** NIFTY stamps (11): `09:36 CHAL ▼ 4/9→3/10` (faded) ·
`10:25 CHAL ▲ 4/10→3/10` · `12:05 TEZ 7/10 CALL BHAAG` · 12:49 end · KHAMOSH · `13:42 CHAL ▼ 4/10→3/10` · end ·
`14:52 ATKA ▼ 5/9` · KHAMOSH. Mostly KAMZOR and KHAMOSH — what a quiet day should look like. SENSEX: `10:30 CHAL ▲
6/10→8/10 CALL BHAAG + PUT LIKHAI, PHANSE 74700CE +11L 10:15 tak likha`.

**29 Sep — NIFTY + BANKNIFTY expiry (NIFTY 22,713 → 22,716).** NIFTY: `10:33 PIN TIKA @ 22600s 4/6` · `11:12 CHAL ▲
5/10→8/10 CALL BHAAG, PHANSE 22600CE +47L 11:07 tak likha` · `11:31 TEZ 8/10` · 11:46 CALL roll UP (22650/22600CE
−80L → 22750/22800CE +53L) · 12:28 end · `12:32 CHAL ▼ 8/10 PUT BHAAG, PHANSE 22700PE +123L 12:26 tak likha` · 12:41
end · ATKA ▼ ×3 · **`15:09 PIN TIKA @ 22700s`** (closed 22,716). BANKNIFTY expiry used "aaj ke minute" (one prior
expiry session).

**21 Oct — big trend down (NIFTY 23,053 → 22,738, range 461).** NIFTY: `10:00 CHAL ▼ THAK 8/10 CALL CAP SAATH`
with **`≠ READ RANGE · RAFTAAR CHAL ▼ 8/10: −84 pts/15m, net −57L`** — the morning THE READ read RANGE at the top
(memory: read-changes-not-levels) · 10:18 PUT floor rolled DOWN (23000/23100PE −37L → 22950/22900PE +15L) · 10:42
end · `11:20 CHAL ▼ 6/10→8/10 PUT BHAAG` · `11:34 TEZ 8/10` · `12:15 TEZ 8/10 PUT BHAAG + CALL LIKHAI` · 12:53 end ·
`13:16 CHAL ▼ 5/10→3/10` · 14:42 PIN TIKA @ 22700s · `15:15 CHAL ▲ 6/10 CALL BHAAG`. SENSEX `09:57 CHAL ▼ 7/10→10/10`
with `≠ READ TREND▲`.

**26 Oct — trend up (NIFTY 22,452 → 22,753).** NIFTY: `09:56 CHAL ▲ 6/9→9/10` (`≠ READ RANGE`) · `09:58 TEZ 8/9→10/10 CALL BHAAG +
PUT LIKHAI` · 10:22 CALL roll UP (22500/22600CE −25L → 22900/22700CE +19L) · ends 10:38 ·
`10:40 CHAL ▼ 6/10 PUT BHAAG` (`≠ READ TREND▲`) · `11:35 CHAL ▼ 6/10→7/10` · 11:49 PUT roll DOWN · `12:11 CHAL ▲
6/10→3/10` · `13:24 CHAL ▲ [CHOP ke andar]` · `14:11 CHAL ▲ 6/10→7/10 CALL BHAAG (22700/22600CE −44L)` ·
`15:12 PIN TIKA @ 22700s`. **Honest limit:** RAFTAAR reads a trend day as its swings (▲ legs, two ▼ pullback legs
that ended by retrace); it does not hold "the day is up". That is §1o's and THE READ's job, by design (§6).

**27 Oct — Oct monthly expiry, today (to ~12:45).** NIFTY (12): `10:03 CALL CAP UPAR SHIFT (22700/22750CE −45L →
23000/22950CE +21L)` · `10:04 CHAL ▲ 5/10 CALL BHAAG + PUT LIKHAI, net +196L` · 10:18 end · `10:21 CHAL ▼ 6/10→7/10
PUT BHAAG (22700/22800PE −66L)` with `≠ READ LEAN▲` · 10:36 end · `10:43 CHAL ▲ 4/10→6/10 PUT FLOOR SAATH [CHOP ke
andar]` · 11:21 end · `11:32 ATKA ▼ 5/9 CALL likh rahe 22750/22800CE +80L, PUT bhaag, price ruka` · 11:46 KHAMOSH ·
`12:35 ATKA ▼ 4/9 CALL likhai into rally · rok rahe (22800CE +27L)` · `12:43 CHAL ▲ 6/10 CALL BHAAG + PUT LIKHAI —
22750CE −55L, 22800CE −48L`: the very strikes written at 11:32 now buying back. PHANSE did **not** tag it: the build
peaked ~70 min earlier, outside its 60-min window (a window I would widen to 90 min after her look). SENSEX `12:45
CHAL ▲ 9/10` (`≠ READ RANGE`).

Disagreement lines printed over the 4 days with a READ log (21, 22, 26, 27 Oct): **23**, all at MAZBOOT, none on a
chop-day swing; listed in the replay files under their stamps.

---

## 6. Where it meets §1d, §1o and THE READ — one voice

| voice | scale / question | RAFTAAR's relation |
|---|---|---|
| **§1d fronts** | the top-2 strikes per side: BUILDING / STALLED / UNWINDING vs their own peak | shown **verbatim** as small chips on every stamp (`§1d fronts: CE22800:U …`). RAFTAAR adds what §1d cannot: the *whole* side's zones and the roll. Where they read differently it is one line with numbers, e.g. 27 Oct 10:03–10:04: §1d `CE22800 U` (gave up) · RAFTAAR: **roll UP, 23000/22950CE +21L — the cap moved, it did not go**. Never edits §1d. |
| **§1o day type** | the session so far, per-5-min votes: TREND / PIN / CHOP / MIXED | RAFTAAR is **not a day type**. Its CHOP / PIN are labelled **ABHI (last 15–60 min)** on the face, §1o sits beside it as **DIN**. "PIN abhi" inside a TREND din is not a contradiction; it is a pause. A line only if RAFTAAR's opposite picture holds MAZBOOT ≥ 30 min. (Could not replay: §1o needs the 5-min tape bars; its log has 23 Oct only.) |
| **THE READ** | one held thesis per index, from 09:45, until its own line breaks | RAFTAAR is the swing-scale speed read under it. It prints **`≠ READ <word> · RAFTAAR <picture> n/N: <numbers>`** only when its picture is MAZBOOT (n ≥ 6), never for a chop-day swing against RANGE (both true at their scale), never on noise. 21 Oct 10:00 is the case it exists for: READ RANGE, RAFTAAR CHAL ▼ 8/10, −84 pts, net −57L. |
| **DECODE** | 7 signs on the swing leg at 5-min closes | DECODE's leg and RAFTAAR's leg are different objects (DECODE: zigzag on 5-min closes; RAFTAAR: OI-backed held move). Build note: RAFTAAR's verdict can be offered to DECODE as one more sign later — a registration, not a silent merge. |

---

## 7. What I could not check, and three questions

Could not check:
- **§1o and DECODE side by side**: both need the 5-min tape bars (GoCharting / Upstox) the server builds; I replayed
  chain + book only. THE READ's words came from its forward log (9 Oct onward).
- **Live**: I made no request to :8765. The replay reads the recorded chain files, which are the same minute grid
  /api/oihist serves (last row per minute), so the live read should match; not verified against the running server.
- **Today's NIFTY before 11:12** is the A125-repaired file; the replay trusts the repair.
- **SENSEX after a big move** loses its read when spot leaves the opening strike window (8 Oct from 12:54); the
  recorder's window, not this design, decides that.
- Whether the PIN rules are too tight or too loose: PIN TIKA was stamped on 3 of 21 index-days (all NIFTY: 29 Sep
  10:33 @22600 and 15:09 @22700, 21 Oct 14:42 @22700, 26 Oct 15:12 @22700); PIN BAN RAHA (both sides writing) never
  reached THEEK. I found no recorded day she called a pin to check them against.

Questions for her (the only three not answerable from the records):
1. On a chop day like 22 Oct, do you want each 80–150 pt OI-backed swing stamped as `CHAL RAHA · [CHOP ke andar]`
   (current design), or suppressed entirely once two swings have been given back?
2. BANKNIFTY's near-ATM OI is thin outside expiry week (ATM ~1.7L a side on 8 Oct); its moves mostly read KHAALI.
   Should BNF's panel read NIFTY's OI speed beside its own (as SENSEX reads NIFTY's flow, §1q), or stay its own?
3. Is 15 minutes the right "abhi" for you, or do you think of the speed in 5-minute pieces (faster, noisier) when
   you are in a trade?

### Least sure of
**The leg end rules** (half given back · opposite OI move · 2 flips · 30 min stale). They decide whether a trend day
reads as one move or as swings (26 Oct reads as swings), and whether a chop day reads as CHOP or as alternating moves
(22 Oct reads mostly as moves with a chop tag). The minute story underneath is solid on every day; the held picture
on top of it is the part that needs her eye.

---

## 8. Known ceilings (build notes, not for her screen)

- `raftaar.py` recomputes features per day in-process (~30 s for 7 days); the build is one pass per minute in the
  server off the live grid, ported to Python next to `fronts.py`, display only, its own forward log `data/speed/`
  (journal, never a gate). It feeds no gate, no setup, no Telegram until she says so.
- The size reference is built on the fly from prior chain files; the build folds it into `tools/rank_build.py`.
- 7–29 stamps per index-day is still more than she will read on a swing day; the KRAM shows the newest 6.
