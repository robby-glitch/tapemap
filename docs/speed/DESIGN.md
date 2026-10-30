# RAFTAAR — the converged design, after the fix round (Fable, 27 Oct 2026)

Engine `final/raftaar.py` (pure, stdlib, causal, no I/O; `--check`), reference builder `final/refbuild.py` → `final/ref/<IDX>.json`,
replay `final/replay.py` → `final/replay/<IDX>_<day>.txt` + `SUMMARY.txt` (11 days × 3 indices, 27 Oct full day), `final/judge.py` →
`replay/NEQ.txt` (every ≠ line with points after), `final/moment.py` (one minute's JSON), `final/chart_data.py` → `chart_data.js`,
screen `final/mockup.html`, chart layer `final/chart_mockup.html` (both LIGHT, four real moments from this engine). Round-1 designs,
critiques and Opus's review stay in `fable/` and `opus/`. Every number is [M] off the chain record unless tagged [I]. No %, no hit rate.

## 1. The trader's question

1. Is a MOVE happening now — which way, are the writers WITH it or FIGHTING it, is it starting / pressing / pausing / tiring, and is
   it a pullback against the day (WAPSI) or the day's own move?
2. If price is not going anywhere: are writers taking turns (CHOP), building both sides at one strike (PIN), pushing one side while
   price refuses (ATKA), or both leaving (UNWIND)?
3. When nothing clears the noise bar, say "kuch khaas nahi" once; when it cannot read, say why; stamp a line only when the picture
   changes; contradict THE READ only on a young, big, moving leg — and never on noise.

## 2. Measures (per minute, off the /api/oihist grid; S = 15 min, F = 5; SENSEX 16 / 8; hold 3 everywhere)

| name | definition | tag |
|---|---|---|
| nine, atm | the 9 strikes nearest spot (§1d); spot outside the recorded strikes or at their edge, or < 7 of the nine at t−S → **?** | §1d |
| kinare pe | fewer than 3 of the nine on one side of spot (S4): grade capped THEEK, no ≠ line | [I] |
| zones | CE **near** = strikes ≤ atm (calls at / under water if price rises), CE **wall** = > atm; PE near = ≥ atm, PE wall = < atm | [I] |
| zone net | Σ OI change over the zone over S, in % of the side's nine OI (an internal unit; the face prints lakh); a strike **votes** when \|d\| ≥ §1d's stall rate × S × its OI | [M] |
| adds, cuts, net | side gross writing / covering; **net = netPE − netCE over S, printed in L** (> 0 pushes up); Z is its % form, internal only | [M] |
| D, D5 | spot change over S / F; P = 0.18 % of the day's first spot (effort.py's yardstick); D counts only if ranked and ≥ P/2 | [I] |
| fast | side gross over F and the F before it; the last hour's own median is the speed reference (TEZ / DHEEMA / RUK / SHURU) | [I] |
| fut | the fut book per minute: \|ΔOI15\| ≥ 0.10 % → the sign of the fut price move, else quiet (SENSEX reads NIFTY's fut, §1q); the face's basis is the **3-min median** of fut − spot (fold.BIX_MS) | §1o / A60 |

**The noise bar.** rank.py's cut-offs against the prior sessions of the same index, day kind (NORMAL / EXPIRY) and day part
(09:15–10:00, 10:00–12:00, 12:00–13:30, 13:30–15:30): < p70 noise, ≥ p70 NOTABLE, ≥ p90 BADA, on the last 20 prior sessions of the
kind (median of their per-session p70 / p90); fewer than 5 → today's own minutes (≥ 30), the face says "aaj ke minute", **the grade is
capped THEEK and no ≠ line prints (M4)**; neither → **? PAIMANA NAHI**. **Absolute clause:** a flow ≥ 2× the index's all-session median,
or ≥ 1.5× today's own median, is NOTABLE whatever the part says (6 Oct 09:34: CE +235L / PE +396L per 15 m at the expiry open).

## 3. The combination table

### 3a. One side's structure over S (RUKE unless max(|near|, |wall|) is NOTABLE; a zone counts at ≥ 25 % of the side's gross)

| near | wall | code | chip | means |
|---|---|---|---|---|
| + | + | LIKH RAHE | likh rahe · deewar sab taraf | writing everywhere |
| + | 0 | ATM LIKH | price pe likh rahe | writing at price: absorbing / pressing |
| 0 | + | DEEWAR MOTI | aage deewar moti ho rahi | the wall ahead thickens |
| − | + (≥ ½ the cut) | ROLL | roll · abhi bhi short | **cap upar / floor neeche shift**: still short, wall moved (her example) |
| + | − | DEEWAR PRICE PE | deewar price pe kheench li | wall pulled onto price |
| − | − | BHAAG RAHE | poora bhaag rahe · fuel | full retreat |
| − | 0 | ITM COVER | price pe phanse buy back · fuel | the trapped at price buying back |
| 0 | − | DEEWAR HAT RAHI | aage deewar hat rahi | the wall ahead thins |
| 0 | 0 | RUKE | ruke | holding |

**PHANSE** tags a covering side when the covered strikes' OI peaked inside the last 60 min and built ≥ half the cover since.
**ROLL TOOTA**: a ROLL followed within 3 min by the same side covering everywhere on a new extreme (printed with the roll's minute).

### 3b. The minute story (first match; L = the side the move hurts, W = the side it pays)

| # | when | story (▲ shown; ▼ mirrors) | qualifier |
|---|---|---|---|
| 1 | D, Z = −D, price still moving over F, L writing | L LIKHAI INTO RALLY · PHANS RAHE — **never starts a leg (S2)** | ULTA |
| 2 | D, Z = −D, price stalled over F, L writing | L LIKHAI INTO RALLY · ROK RAHE — never starts a leg | ULTA |
| 3 | D, L covering, W writing | **L BHAAG + W LIKHAI** (dono engine) | SAATH |
| 4 | D, L covering | **L BHAAG RAHE** (+ PHANSE) | SAATH |
| 5 | D, L rolled away | **L CAP UPAR / FLOOR NEECHE SHIFT** | MILA-JULA |
| 6 | D, W writing | **W FLOOR / CAP SAATH** | with ≥ 2× against SAATH · against ≥ with ULTA · else MILA-JULA |
| 7 | D, both RUKE, Z = 0 | **BINA OI ▲** | BINA OI |
| 8 | D, else | **OI SAATH ▲** | by the ratio |
| 9 | no D, Z notable | **ATKA ▲/▼ · \<lead\> likh rahe, price nahi** | — |
| 10 | no D, both adds NOTABLE and within 1:2, range30 ≤ 1 step | **PIN BAN RAHA @ k** (line prints the 15-min adds) | — |
| 11 | no D, range30 ≤ 0.6 step, spot within ½ step of the most two-sided strike (OI ratio ≥ 0.6) | **PIN TIKA @ k** (line prints CE / PE OI at k) | — |
| 12 | no D, both sides net cutting NOTABLE | **UNWIND · dono nikal rahe** (after 15:00 "band ka unwind") | — |
| 13 | else | **KUCH KHAAS NAHI** | — |

**PIN BAARI-BAARI @ k**: an ATKA of one side, then of the other, inside 45 min at one strike (± 1 step), both sides net adding over
45 min and within 1:2, range45 < 2 P (line prints the 45-min adds and range). with = L's cuts + W's adds; against = L's adds.

### 3c. The held picture (the big word)

| picture | starts | inside | ends |
|---|---|---|---|
| **CHAL RAHA ▲/▼** | a D-story 3–6 / 8 held 3 marks with OI behind it (Z = D notable, or stories 3–6) or D BADA, and never Z = −D; inside CHOP only with OI | **SHURU** (5 min) · **TEZ** (with-flow over F ≥ 1.5× the F before, new extreme ≤ 3 min, on a minute that is itself a move) · **JAARI** · **RUKA** (no new extreme ≥ 20 min or 10 min KAMZOR: a pause, the leg stays the picture) · **PHIR CHAL PADA** (a same-direction OI-backed minute inside 30 min of the pause: the same leg goes on, one line) · **THAK** (fading fuel AND a price stall ≥ 5 min) | **KHATAM** (held 2 min; a picture that follows inside 2 min absorbs it): half the leg given back (min 1 step) · an OI-backed opposite leg held 3 · 50 min without a new extreme · 40 min KAMZOR · 10 min of CHOP / PIN story. A line only for a leg that was MAZBOOT |
| **WAPSI ▲/▼** | a leg against the day's run (day high − open or open − day low ≥ 3 P) that has retraced < ½ of it | the same phases | → CHAL RAHA once the retrace from the day's extreme ≥ ½ the day's run for 3 marks; never back; no ≠ line |
| **CHOP** | NOTABLE legs both ways inside 30 min, where a counter-leg counts when it is ≥ ½ the previous leg (22 Oct's dips 56 %, 8 Oct's bounces 14–31 %) | the current leg is a **swing**: shown small, capped THEEK, no line, no ≠; CHOP re-stamps at most once an hour | lapses 60 min after the last opposite leg; a swing leaves it ("chop se bahar") only on a minute moving with OI (D = Z = its direction), its size ≥ max(3 P, 1.5× the 60-min range at its birth), spot beyond the range standing at its birth, before 15:00 |
| **PIN @ k** | story 10 / 11 / baari-baari held 3 — a PIN beats CHOP | k in spot | the story changes |
| **ATKA ▲/▼** | story 9 held 3; a line only at MAZBOOT | lead side named | the story changes |
| **UNWIND** | story 12 held 3, once per 30 min | — | — |
| **BINA OI** / **KHAMOSH** | story 7 / 13 held 3 | the last real change | — |
| **?** | PADH RAHE (< S min of record; never a line) · PADH NAHI SAKE (window edge, missing strikes) · PAIMANA NAHI (no size reference) | the reason | — |

### 3d. The grade = n/N over the checks that could be read (never a %)

size (own defining flow NOTABLE) · aaj (≥ today's own p70) · BADA · 5 min tika · 15 min tika · 2+ strikes (and ≥ 2/3 of the defining
zone's voters) · price (leg: still moving over F; ATKA: stopped; CHOP / PIN: range in band) · fut (leg / ATKA: with it; PIN: quiet) ·
each other index (same word + direction within 3 min) · chop ke bahar. **n/N ≥ 0.6 MAZBOOT · ≥ 0.4 THEEK · else KAMZOR.** Caps: KAMZOR
unless the picture's own OI flow is NOTABLE; THEEK for a swing inside CHOP, a WAPSI, a PATLA nine (< 100 L), a today's-own reference
(M4), or a lopsided nine (S4). Printed at the stamp; the face updates it live.

## 4. Stamps — a stamp, once written, is never edited (M1)

1. A picture at the first minute it reaches THEEK (KAMZOR lives on the face, never a line); ATKA only at MAZBOOT; no swing lines inside
   CHOP; CHOP at most once an hour.
2. Inside a stamped leg: TEZ as a new line only ≥ 5 min after the picture line (else nothing), PHIR CHAL PADA once per pause,
   WAPSI → CHAL RAHA, "chop se bahar", KHATAM (held 2 min, for a MAZBOOT leg). THAK and RUKA are face phases, not lines.
3. KHAMOSH / BINA OI once, after a real picture, after 10 held minutes, at most once an hour, never inside 10 min of a KHATAM.
4. `?` only for PADH NAHI SAKE / PAIMANA NAHI (the morning PADH RAHE carries no news).
5. Side events, once per side per 30 min (ROLL once per hour unless the wall moved to a new strike): **CAP UPAR / FLOOR NEECHE SHIFT**,
   **ROLL TOOTA**, **PHIR LIKHNE LAGE (N min ruk ke)**.
6. **≠ READ** — the most dangerous line this screen can print — only when ALL hold: the picture is CHAL RAHA at MAZBOOT; not a WAPSI, not a
   swing, not a swing promoted by a chop lapse; the leg is ≤ 15 min old or this is its breakout minute; this minute moves with OI (D = Z =
   its direction); \|m15\| ≥ 1.5 P with D BADA; m5 ≥ ½ step its way; THE READ's word is RANGE / TREND / LEAN and disagrees; the reference
   is history (not today's own); the nine are not lopsided; before 15:00; **not on the index's own expiry day**; once per 30 min. It
   prints with numbers: `READ: RANGE · RAFTAAR: CHAL RAHA ▲ 8/9 — CE BHAAG + PE LIKHAI · spot +137/15m · net +79.5L`.

## 5. Replay — the union of both day sets, all three indices (`final/replay/`, rows not rates)

Stamps per index-day after the fix round (pictures in brackets) — NIFTY / BANKNIFTY / SENSEX:

| day | kind | NIFTY | BNF | SENSEX | what NIFTY read |
|---|---|---|---|---|---|
| 23 Sep | range (NIFTY expiry wk) | 15 (10) | 8 (7) | 19 (13) | KHAMOSH 158 min, CHOP 64 |
| 25 Sep | range / pin | 10 (8) | 10 (9) | 11 (9) | CHOP 193, **PIN 64 @ 23100** |
| 29 Sep | NIFTY + BNF expiry | 9 (7) | 15 (7) | 13 (9) | CHOP 133, KHAMOSH 45; BNF PIN 61 |
| 30 Sep | chop | 8 (6) | 8 (7) | 11 (5) | CHOP 192, ▼ 133 |
| 6 Oct | expiry grind +0.8 % | 19 (13) | 9 (8) | 15 (10) | **PIN 102 @ 22700 (TIKA)**, KHAMOSH 118, CE CAP UPAR SHIFT ×4 (the cap rolled up all day) |
| 8 Oct | clean trend ▼ | 17 (9) | 8 (7) | 8 (5) | **CHAL RAHA ▼ 151**, CHOP 112 (the morning range), SENSEX ? 126 (window edge from 12:54) |
| 21 Oct | top 09:58, −470 | 16 (9) | 9 (8) | 11 (7) | **CHAL RAHA ▼ 208**: 10:04 chop se bahar 9/11 + ≠ READ RANGE (THE READ: LEAN ▼ at 10:10) |
| 22 Oct | her chop day | **6 (5)** | 7 (7) | 13 (6) | **CHOP 315 min**, six lines all day, no ≠ |
| 23 Oct | ▼ then two-way | 9 (6) | 11 (7) | 7 (6) | CHOP 257, ▼ 88 |
| 26 Oct | bottom, +300 | 13 (7) | 7 (5) | 10 (8) | 09:52 ▲ 5/8 → **09:55 ≠ READ RANGE 8/9** → TEZ; WAPSI ▼ 28 min with no line; ▲ 117, CHOP 117 |
| 27 Oct | monthly expiry (full day) | 20 (10) | 13 (7) | 9 (6) | CHOP 174, ▲ 63 / ▼ 69, CE CAP UPAR SHIFT 09:58 / 12:03 / 12:42, PIN @ 22700 14:00; no ≠ (expiry) |

Range: **NIFTY 6–20, BANKNIFTY 7–15, SENSEX 7–19.** The ≤ 15 target holds on every BANKNIFTY day, 10 of 11 SENSEX days, 7 of 11 NIFTY
days. Over it: NIFTY 6 Oct 19 (PIN @ 22700 re-stamped 4×, ROLL ×4), 27 Oct 20 (ROLL ×3, 6 phases/ends), 8 Oct 17 and 21 Oct 16 (3–5
KHATAM / PHIR CHAL PADA lines on 4–5 pushes), SENSEX 23 Sep 19. **What would reach ≤ 15 everywhere:** a PIN at the same strike once per
2 hours (−3 on 6 Oct), ROLL events once per 2 hours unless the wall moves (−2 on 6 Oct, −2 on 27 Oct), KHATAM only for legs that ran ≥ 20
min (−2 on 8 / 21 / 27 Oct). Not applied: each removes a line she asked for (the roll, the end). Her call.

**S1 "phir chal pada"** (a stale or weak leg stays RUKA for 30 min and resumes as the same leg) is in: 23 Oct's six ▼ restarts became
one leg from 09:34 with resumes; 8 Oct 17 lines are 4 legs + their ends, not 6 restarts + 3 quiet lines.

## 6. The ≠ READ lines that survive (`final/replay/NEQ.txt`, points along the line's direction)

| day · time | line | +15 min | +30 min | best / worst in 30 |
|---|---|---|---|---|
| 21 Oct NIFTY 10:04 | READ RANGE · CHAL RAHA ▼ 9/11 · PE BHAAG + CE LIKHAI · chop se bahar | **+54** | **+8** | +63 / +2 |
| 26 Oct NIFTY 09:55 | READ RANGE · CHAL RAHA ▲ 8/9 · CE BHAAG + PE LIKHAI · +137/15m · net +79.5L | **+125** | **+103** | +140 / +32 |

Killed by the fix round, with the rule that killed each: 22 Oct 11:16 and 12:21 NIFTY (M2: the chop no longer lapses under a 160-pt
swing; the breakout needs the birth range cleared on a moving minute); 26 Oct 13:50 and 27 Oct 15:18 (M3: a flat minute, after 15:00);
26 Oct 11:13 (a flat picture never contradicts); 26 Oct 14:09 (the leg was 4 min old but m5 had stalled); 27 Oct 13:22 and 10:21 (expiry
day); BANKNIFTY 27 Oct ×4 (M4: today's-own reference); SENSEX 22 Oct 11:49 and 12:19 (expiry day; the breakout test). Two departures from
the letter of the review, each with its evidence: (a) **a counter-leg counts toward CHOP only when it is ≥ ½ the previous leg** — under
literal M2 ("every notable D-minute counts") 8 Oct read CHOP 255 min, 23 Oct 279, 26 Oct 218, a trend day as chop; with the ½ rule 22 Oct
still reads CHOP 315 min and 21 Oct reads CHAL RAHA ▼ 208; (b) **no ≠ line on the index's own expiry day** — the two expiry-day lines left
after M3 were −36 / −59 (27 Oct 10:21) and −41 / +44 (SENSEX 22 Oct 11:49): pin and unwind mechanics on a 5–8-session reference.

## 7. The one-glance screen (`final/mockup.html`, LIGHT, 1229 px border-box, no sideways scroll)

Header: `RAFTAAR · NIFTY · 09:58 · spot 22,645s · fut 22,726f · basis +81 (3-min median) · 15m +191 · din +193 · DIN (§1o) · size ref ·
BNF / SNX words`. Three cards: **the picture** (the word at 36 px with its arrow, the grade pill MAZBOOT green / THEEK amber / KAMZOR grey,
phase · qualifier · since, the one-line story with two numbers — points and net L, the with / against bars, the check chips, the ≠ line as
one row of cells when it exists) · **call writers** · **put writers** (structure code + Hinglish chip, the two biggest strikes per sign in
L, near / wall table with votes, speed word and L/min, level). Below: **kram** (stamped lines only, newest first) and **§1d fronts verbatim**
(or **din** on a flat picture). Hidden until clicked: every minute's story, the 18 strike-sides, all §1d changes, side events older than
the last 3, the reference sessions. On KHAMOSH the side cards collapse to one row. Units on her screen: lakh (2 decimals under 1 L) and
points; no % and no k anywhere. The four moments are this engine's: 26 Oct 09:58 (move), 22 Oct 10:01 (chop), 6 Oct 11:39 (pin), 23 Sep
12:30 (quiet); `final/moment.py NIFTY <day> <HH:MM>` prints the same JSON.

## 8. Beside §1d, §1o and THE READ — one voice

- **§1d** stays verbatim as small chips. RAFTAAR adds the whole side's zones, the roll and PHANSE; where they differ it is one line with
  numbers (27 Oct 09:58 `§1d CE22700 U · RAFTAAR: CE CAP UPAR SHIFT 22700 −14L / 22650 −7.5L → 22800 +21.8L / 22900 +19.9L`). Never edits §1d.
- **§1o** is the day; RAFTAAR is the last 15–60 min. The header shows DIN beside ABHI; a PIN abhi inside a TREND din is a pause.
- **THE READ** is the held thesis; RAFTAAR prints ≠ READ under §4.6 only. Both survivors were right (§6); none printed on 22 Oct.
- **oi-lab**: no hold / break claim; the fut leg is a grade check, not a name; SENSEX reads its own OI.

## 9. Build target

**`GET /api/raftaar?idx=NIFTY|BANKNIFTY|SENSEX`** — one `Engine` per index inside the chain poller, `step(t, row, peers, read_word)` at
each finished minute off the same `ChainState.minutes` + `open` that `/api/oihist` serves, the fut book's last row per minute from the
feed, §1o's day type and THE READ's current word from the server. Reference table from `tools/raftaar_ref.py` (refbuild.py ported),
rebuilt by `eod_capture`. Forward log `data/raftaar/raftaar_<day>.jsonl`: every stamp, appended once, never rewritten. Display only.

Every minute carries every key (S5); `picture.word` is one of `CHAL RAHA · WAPSI · CHOP · PIN · ATKA · UNWIND · BINA OI · KHAMOSH · ?`,
the pending minute story sits in `picture.pending`, a swing inside CHOP in `picture.swing`, a `?` reason in `picture.why`:

```json
{"idx":"NIFTY","t":"09:58","spot":22645.15,"ref":"20 pichhle normal din","day_drift":193.1,
 "picture":{"word":"CHAL RAHA","dir":1,"phase":"TEZ","since":"09:50","held":true,"in_chop":false,"swing":null,"pending":null,"why":null,
            "grade":{"n":8,"N":9,"word":"MAZBOOT","checks":{"size":true,"bada":true,"aaj":true,"tika5":true,"tika15":false,
                     "strikes":true,"price":true,"fut":true,"chop_bahar":true}},
            "story":"CE BHAAG + PE LIKHAI","qual":"SAATH","read":"losers covering, winners chasing","k":null},
 "numbers":{"m15":190.9,"m5":114.5,"net_L":"+79.5L","Z_pct":20.125,"D_level":"BADA","Z_level":"BADA","patla":false,"edge":false,
            "aaj_ref":false,"nine_oi_L":"+1328.1L","P":40.4},
 "sides":{"CE":{"structure":"ITM COVER","chip":"price pe phanse buy back · fuel","strikes":[{"k":22500,"d":-4632355,"L":"−46.3L"},
                {"k":22450,"d":-2577055,"L":"−25.8L"}],"near_L":"−112.5L","wall_L":"−32.7L","adds_L":"0","cuts_L":"−145.2L",
                "votes":[0,4,0,2],"phanse":[],"speed":"SHURU","speed_now_L_min":"−31.9L","level":{"zone":"BADA","adds":"NOISE","cuts":"BADA","fast":"BADA"}},
          "PE":{"structure":"DEEWAR MOTI","chip":"aage deewar moti ho rahi","strikes":[{"k":22500,"d":3727100,"L":"+37.3L"},{"k":22600,"d":3226600,"L":"+32.3L"}],
                "near_L":"+24.3L","wall_L":"+97.7L","adds_L":"+122.1L","cuts_L":"0","votes":[2,0,5,0],"phanse":[],"speed":"SHURU","speed_now_L_min":"+18.8L",
                "level":{"zone":"BADA","adds":"NOTABLE","cuts":"NOISE","fast":"BADA"}}},
 "contradiction":"READ: RANGE · RAFTAAR: CHAL RAHA ▲ 8/9 — CE BHAAG + PE LIKHAI · spot +137/15m · net +79.5L",
 "stamps":[{"t":"09:55","spot":22559.3,"kind":"neq","word":"≠ READ","title":"≠ READ","grade":"8/9 MAZBOOT","why":"READ: RANGE · RAFTAAR: …","extra":{}}]}
```
`Z_pct` stays in the JSON for the engine's own checks; the face shows `net_L`. The **ui-v2 face** replaces the Speed tab: the mockup's
layout fed by `/api/raftaar` (poll 15 s), `speed.ts` deleted — the brain lives once, in Python. Telegram gets stamps of kinds picture /
end / ≠ READ only, on her word.

### 9a. RESTART — her anytime-start rule

Grades depend on the other two indices, THE READ's word at the minute and the fut book, so one index cannot be rebuilt alone. On any
start or restart inside the day the server: (1) loads the three chain records of the day (the same minute grid, last row per minute, with
`open`), the fut book per minute for NIFTY and BANKNIFTY (SENSEX takes NIFTY's), THE READ's log for the day and the §1o type; (2) builds
the three `Engine`s with the prior-session reference and runs them **in lockstep, minute by minute, from 09:15 to now**, each minute
passing the other two engines' current pictures as peers and THE READ's word as it stood then (exactly `final/replay.py`'s loop); (3)
compares the replayed stamps with `data/raftaar/raftaar_<day>.jsonl`: stamps already in the journal are kept as written (never
recomputed, never edited — M1); stamps the replay produces that the journal lacks (the gap while the server was down) are appended, tagged
`backfilled: true`; a stamp in the journal that the replay would not reproduce is left in place and tagged in the next line, never
deleted; (4) resumes live stepping. A read that cannot be reconstructed (a missing fut minute, a READ word not logged) is a dropped check
(N shrinks), which is what a never-stopped run would also have done; it is never a miss. The replay over the record is causal by
construction, so the grades and stamps match a run that never stopped except where the journal says otherwise.

## 10. ON HER CHART — the layer through the extension's overlay (BRIEF §9)

The overlay draws only what `main.js`'s `face()` decides, inside its grammar: a line budget (2 flat / 5 in a trade), ≤ 6 chips of ≤ 4
words, fut | spot chips, KHEL shading under bars, ranked marks in the bar gutter, the deewar lines. RAFTAAR adds four things and nothing else
(`final/chart_mockup.html` draws them at the four moments on 5-min bars built from the record):

1. **The ribbon** — one cell per closed bar in the KHEL shading band under the bars, coloured by the big word (CHAL ▲ green · CHAL ▼ /
   WAPSI red · CHOP amber · PIN teal · ATKA blue · UNWIND grey · ? light grey · **KHAMOSH blank**), its height the grade (MAZBOOT full ·
   THEEK half · KAMZOR a sliver); a swing inside CHOP is a small coloured tick on the amber cell. It is `face().raftaar.ribbon[bar]`.
2. **The marks** — one ◆ in the bar gutter at the bar where a stamped line was written (picture, phase, KHATAM, event, ≠), coloured like
   the ribbon, with a chip of ≤ 4 Hinglish words and its number: `CHAL ▼ 9/11`, `CHAL ▲ 8/9 tez`, `WAPSI ▼ 5/11`, `PIN 22,700s`,
   `CAP UPAR 22,800`, `FLOOR NEECHE 22,600`, `ROLL TOOTA`, `CE phir likhe`, `KHATAM ▼`, `≠ READ`. At most 6 chips, newest first; older
   marks keep the ◆ and show their chip on hover. The marks are placed when their bar closes and never move (the overlay's own rule).
3. **The walls on price** — RAFTAAR owns no lines. The existing deewar lines are tagged by it: the CE wall strike (cap) and the PE wall
   strike (floor), `s` with the `f` chip from the 3-min basis; when a side ROLLs the line moves to the new strike and the old level stays
   dotted for 30 min with the chip `cap tha 22,700s`. Flat = the 2 lines are these two; in a trade = the trade's 5 lines own the budget and
   the walls stay only as ticks on the price axis. Never a second set of lines.
4. **Hover** on a ◆ or a ribbon cell: the full one-line story with its numbers, and the ≠ line if one was written at that bar.

Build path: `/api/raftaar` → the extension's existing TapeMap poll → `face()` returns `raftaar: {ribbon, marks, cap, floor, cap_was, floor_was,
hover}` → overlay draws ribbon cells in the shading band, ◆ + chips in the gutter, and re-tags the deewar lines. The same JSON feeds the
ui-v2 tab; the brain stays in Python.

## 11. What it cannot check, and what is left

- **§1o side by side**: the meter needs the 5-min tape bars the server builds; its log starts 23 Oct. The header's DIN is a build-time join.
- **Live**: no request went to :8765; the replay reads the recorded chain, the same grid `/api/oihist` serves. Not verified against the server.
- **The first 15 minutes** are `?` by construction (S = 15); no line is written for them.
- **BANKNIFTY's monthly expiry** (< 5 prior expiry sessions) grades at most THEEK on today's own reference and prints no ≠ line; **SENSEX after a
  big move** loses the window (8 Oct from 12:54: 126 ? minutes) — the recorder's strike window, not the rule.
- **Volume**: 4 NIFTY index-days sit at 16–20 lines (§5 says what would cut them); 22 Oct is 6.
- **Least sure of:** the two departures in §6 — the ½-of-the-previous-leg rule for what counts as a chop leg, and no ≠ line on an expiry
  day. Each was chosen on the days that broke the literal rule (8 / 23 / 26 Oct for the first; 27 Oct and SENSEX 22 Oct for the second).
  They leave exactly two ≠ lines on eleven days, both right; whether they are too tight will show only on days not yet recorded.
