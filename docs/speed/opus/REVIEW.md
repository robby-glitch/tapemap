# RAFTAAR converged design: round 3 adversarial review (OPUS), 27 Oct 2026

**What I ran.** `opus/review_run.py` imports `final/` read-only. It runs with `python -B`, so no cache file lands in
`final/`, and it writes only to `opus/review/`. I re-ran all 11 days × 3 indices on the shipped `final/raftaar.py`.
27 Oct is now the full day, because the record grew after 14:10. Price after a line is given in points along the line's
own direction: + means price went its way. No rates anywhere.

**Verdict: ship after fixes.** The core holds up. It is causal, its reference uses only prior sessions, it is pure and
cheap, and it reads her roll example correctly. What would mislead her sits in four places: the stamp record, the chop
logic, the ≠ READ gate, and the volume.

---

## MUST-FIX

| # | minute · engine output | why a trader is misled | fix |
|---|---|---|---|
| M1 | **23 Oct NIFTY 11:20.** At 11:20 the line read `WAPSI ▲ · JAARI 7/11`; the replay prints `WAPSI ▲ · SHURU→TEZ 8/11`. **BNF 23 Oct 13:38** read `SHURU 6/11` at its minute; the replay prints `SHURU→TEZ 10/11`. Found by cutting the day at T and re-running. | The TEZ merge (`_stamp_leg`, `stamps[i_]` rewritten up to 5 min later) puts a later grade and phase on an earlier minute. In the replay that is look-ahead. Live, a line she already saw, or Telegram already sent, changes underneath her, and the forward log then disagrees with the face. | Never edit a stamp. Write the TEZ line, or nothing. |
| M2 | **22 Oct NIFTY (her stop-loss day).** CHOP was on until 11:09. At 11:10 `legs_seen` held only ▲, although ▼ D-minutes printed 10:45–10:56. Then came `11:14 CHAL RAHA ▲ · SHURU 5/11` and **`11:16 ≠ READ RANGE · CHAL RAHA ▲ 7/11` at 22,771. Price did −15 by 15 min and −130 by 30 min.** | The 10:45–10:56 dips were classed as WAPSI: the day had run 174 ≥ 3 P from the open and the dip had retraced < ½. WAPSI minutes are excluded from the chop legs, so CHOP lapsed at the top of a 160-pt swing and the next swing became a "real" leg plus a contradiction line. Any chop day that opens with a ≥ 3 P drift loses its CHOP the same way. | Every notable D-minute counts toward CHOP. WAPSI is a name for a leg, not an exemption from chop. |
| M3 | **≠ READ and "chop se bahar" fire when price is not moving.** `26 Oct 13:50 CHAL RAHA ▲ · RUKA · chop se bahar 7/11 + ≠ READ RANGE` (story ATKA, spot +6/15m). `27 Oct 15:18 CHAL RAHA ▲ · THAK · chop se bahar 8/11 + ≠ READ RANGE` (story UNWIND, spot +2/15m, Z −2.19 %, its own OI pointing down, after 15:00). `22 Oct 12:19 ▼ chop se bahar + ≠ READ` (spot −22/15m, at the low; +48 against it in 30 min). `SENSEX 22 Oct 12:19 ≠` (−106/16m, < P; +154 against it in 30 min). | The chop exit tests the rolling 60-min range, so a swing's own old move "breaks" it later at any new extreme, even during a pause. The ≠ line then fires on that minute. A contradiction of THE READ printed on a flat or reversing minute is disagreement on noise, which the brief forbids. | A ≠ line or a chop exit needs **this minute moving**: \|m15\| ≥ P, a D-story, and Z with the leg at ≥ NOTABLE. The break must clear the range that stood at the swing's birth. No ≠ line after 15:00. |
| M4 | **BANKNIFTY 27 Oct: four ≠ lines, size reference "aaj ke minute"** (1 prior expiry). 10:22 ▼ vs READ LEAN ▲: −50 at 15 min, −54 at 30 (price went up). 11:15: −31 / +2. 12:21: −44 / −101 (up 101). 13:22: +40 / +3. | Today's-own reference makes about 30 % of minutes NOTABLE by construction. That is weak evidence, yet it is allowed to grade MAZBOOT and overrule THE READ. | When the reference is today's own, cap the grade at THEEK and print no ≠ line. |
| M5 | **The docs and mockup are not this engine.** DESIGN §5/§7 says `26 Oct 09:52 5/8 → TEZ 8/9` and `27 Oct 13:16 ≠ 9/11`. The engine says 09:52 5/10 THEEK, ≠ at 09:53 6/10 (Z +0.52 %), TEZ 10/11, and 27 Oct ≠ at 13:22 7/11. The mockup's ≠ line reads `RAFTAAR: CHAL RAHA ▲ 5/8 … Z −0.71 %` with `with +53L against +64L`: its own evidence points down. §7 never shows the second 26 Oct line (the 13:50 ATKA one, M3). | She will check the screen against the doc and will not reproduce it. The one line the doc highlights is printed on evidence that contradicts its arrow. | Regenerate DESIGN §5/§7, the replay files and the mockup from the final engine after M1–M4. |
| M6 | **Volume.** Fresh counts per index-day: NIFTY 17–30 (27 Oct full day 30, 23 Oct 29, 22 Oct 24), BNF 11–30, SENSEX 14–35. | She rejected the first build for exactly this. | The cut below brings NIFTY to 7–26 (≤ 18 on 9 of 11 days). The trend-day resume rule (S1) takes the rest. |

### The stamp cut (M6), counted on the fresh replays

Six rules, each read in trader terms:
1. **No morning `? PADH RAHE`.** It prints every day by construction, so it carries no news.
2. **No swing lines inside CHOP.** CHOP already said "swings"; the face shows the swing small.
3. **CHOP at most once an hour.** On 22 Oct it was re-stamped 9 times.
4. **KHATAM merged** with a picture that follows within 2 min, and a quiet line within 10 min of a KHATAM merged into it.
5. **ATKA only at MAZBOOT.** Every ATKA line in the replay sits at 4/10 THEEK.
6. **No KAMZOR line.** 26 Oct 11:34 `CHAL RAHA ▼ 6/11 KAMZOR` breaks the engine's own rule.

| NIFTY | 23 Sep | 25 Sep | 29 Sep | 30 Sep | 6 Oct | 8 Oct | 21 Oct | 22 Oct | 23 Oct | 26 Oct | 27 Oct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| now → after | 22→18 | 21→11 | 17→10 | 20→11 | 21→14 | 22→18 | 24→17 | **24→7** | **29→26** | 23→15 | 30→22 |

BANKNIFTY after the cut is 5–21 and SENSEX 9–21. The NIFTY days still above 15 are trend days cut into many legs (S1).

---

## Every ≠ READ line, judged (points over the next 15 / 30 min, along the line's direction)

| day · idx · time | line | +15 | +30 | best / worst | verdict |
|---|---|---|---|---|---|
| 21 Oct NIFTY 10:04 | READ RANGE · ▼ 9/11 · PE BHAAG + CE LIKHAI · −70 · Z −7.94 % | +55 | +8 | +64 / 0 | **right**: the top of the −470 day |
| 22 Oct NIFTY 11:16 | READ RANGE · ▲ 7/11 · CE BHAAG + PE LIKHAI · +40 | −15 | −130 | +6 / −130 | **wrong**: the top of a 160-pt swing (M2) |
| 22 Oct NIFTY 12:19 | READ RANGE · ▼ 7/11 · CE CAP SAATH · −22 | −28 | −48 | +8 / −48 | **wrong**: at the low (M3) |
| 23 Oct NIFTY 14:45 | READ RANGE · ▼ 8/11 · PE BHAAG RAHE · −63 | −30 | −30 | +4 / −30 | **wrong** |
| 26 Oct NIFTY 09:53 | READ RANGE · ▲ 6/10 · PE FLOOR SAATH · +99 · **Z +0.52 %** | +168 | +146 | +168 / 0 | **right, on thin evidence** (the real flow came at 09:58) |
| 26 Oct NIFTY 13:50 | READ RANGE · ▲ 7/11 · story **ATKA**, spot +6 | +9 | +18 | +58 / −11 | **noise** (M3) |
| 27 Oct NIFTY 13:22 | READ RANGE · ▼ 7/11 · PE BHAAG + CE LIKHAI · −66 | 0 | −8 | +5 / −19 | **noise**: came after the move |
| 27 Oct NIFTY 15:18 | READ RANGE · ▲ 8/11 · story **UNWIND**, +2, Z −2.19 % | 0 | −11 | 0 / −11 | **noise**, after 15:00 (M3) |
| 27 Oct BNF 10:22 | READ LEAN ▲ · ▼ 7/11 · −136 | −50 | −54 | +18 / −63 | **wrong** (M4) |
| 27 Oct BNF 11:15 | READ RANGE · ▼ 7/11 · −109 | −31 | +2 | +24 / −62 | **noise** (M4) |
| 27 Oct BNF 12:21 | READ RANGE · ▼ 7/11 · −112 | −44 | −101 | +5 / −133 | **wrong** (M4) |
| 27 Oct BNF 13:22 | READ RANGE · ▼ 9/11 · −176 · Z −20.9 % | +40 | +3 | +40 / −33 | right for 15 min, then gave it back |
| 22 Oct SENSEX 11:49 | READ RANGE · ▼ 9/11 · −371/16m (after the flush) | −41 | +44 | +65 / −90 | **noise**: a whipsaw |
| 22 Oct SENSEX 12:19 | READ RANGE · ▼ 8/11 · −106/16m | −98 | −154 | +19 / −154 | **wrong**: before the 12:52 short-covering pop |

**Rows:** right 2, right-then-gave-back 1, wrong 6, noise 5.
- Every wrong or noise line came after the 15-min move was already printed, at a swing extreme, or on a minute with no move.
- **22 Oct (her chop day):** both NIFTY lines and both SENSEX lines were wrong or noise.
- **BANKNIFTY:** its four lines rest on today's-own sizing. On normal weeks its PATLA cap (nine OI < 100 L) correctly blocks MAZBOOT and ≠.

**With M3 and M4 applied**, 21 Oct 10:04 survives. So do 23 Oct 14:45, 27 Oct 13:22 and SENSEX 11:49. 26 Oct 09:53 drops, because its Z of +0.52 % was not NOTABLE.

---

## The rules she will see: fit or mislead

| rule | fits | misleads |
|---|---|---|
| **chop exit** (Fable's least-sure) | 21 Oct 10:04: a fresh −70/15m break, +55 in 15 min | 22 Oct 12:19, 26 Oct 13:50, 27 Oct 15:18: the "break" is a stale rolling-60 extreme during a pause (M3) |
| **PIN 1:2** | 21 Oct 14:14 `PIN @ 22700s · CE +14.4L PE +13.0L` on the 22,680–22,700 afternoon | 27 Oct 11:32 `PIN · dono baari-baari likh rahe · CE adds +144L PE adds 0`, and 6 Oct 13:11 `PIN · dono barabar · CE +74.2L PE +4.6L`: the printed numbers deny the word (S3) |
| **WAPSI** | 26 Oct 10:28 `WAPSI ▼` with no ≠ line against TREND ▲. The pullback took 163 of the day's 247; the trend resumed 14:11 | as a chop exemption, 22 Oct (M2). 21 Oct 10:37 `WAPSI ▲` was born on `CE LIKHAI INTO RALLY · PHANS RAHE, with +2L against +26L` (S2) |
| **ATKA** | 8 Oct 09:39 `ATKA ▼ · CE likh rahe, Z −7.1 %`, then 09:46 ▼ −51. 26 Oct 13:57 `ATKA ▲`, then 14:11 ▲ +52 | BNF 27 Oct 11:05 `ATKA ▲ · PE likh rahe`, then 11:14 ▼ −123 |
| **UNWIND** | 26 Oct 15:00, 23 Oct 15:15, 27 Oct 15:21 (`CE −165L PE −95L`): the close | — (except as the story under M3's 15:18 ≠) |
| **ROLL / CAP UPAR SHIFT** | 27 Oct 09:58 `22700 −14L, 22650 −7.5L → 22800 +21.8L, 22900 +19.9L` (her example). 6 Oct the cap rolled up ×4 on a +190 grind | — |

---

## SHOULD-FIX

| # | evidence | fix |
|---|---|---|
| S1 | **A trend day is cut into restarts.** 23 Oct NIFTY: 6 ▼ legs (09:34, 09:55, 10:58, 11:39, 11:59, 12:54), 5 KHATAM ("20 min se naya low nahi" / "10 min KAMZOR"), 3 KHAMOSH between them, 29 lines | A same-direction leg within 30 min of a stale or weak end, with < ½ retraced, is **"phir chal pada"** on the old leg. No KHATAM for the stale end, and no KHAMOSH between. |
| S2 | A leg starts on price alone while the writers are against it: 21 Oct 10:37 `WAPSI ▲ 6/11 · CE LIKHAI INTO RALLY · PHANS RAHE` | A leg needs Z ≠ −D. Otherwise the picture is ATKA or ULTA. |
| S3 | PIN lines print 15-min adds under a 45-min or stock verdict (above) | Print the evidence that made the word: 45-min adds for BAARI-BAARI, CE/PE OI at k for TIKA. |
| S4 | A lopsided nine read as normal: **NIFTY 8 Oct 116 min from 13:18** with ≤ 2 of the nine below spot; SENSEX 8 Oct 68 min. A put roll-down below the window shows only as "PE BHAAG · fuel" (8 Oct 14:10 `▼ 7/11 MAZBOOT PE BHAAG + CE LIKHAI`) | Tag "kinare pe", cap THEEK, no ≠ line, when < 3 strikes sit on one side. |
| S5 | JSON: 17 `?` minutes a day lack `numbers` / `day_drift`. `picture.word` carries free text (`"abhi: CE CAP SAATH"`, `"abhi: BINA OI ▼"`) | Every key present (null when unknown). `word` is an enum; the pending story goes in its own field. |
| S6 | Anytime-start: grades depend on peers, THE READ's word and the fut book. Re-running one index after a restart changes grades, and so changes which lines print | On start, replay all three in lockstep with the READ log and the book. Persist the stamps to the journal and never recompute them. |
| S7 | Units and % on her face: BNF lines read `54600 −65k, 54100 +85k` beside lakh. Z is shown as `+20.1 %` | Lakh everywhere, 2 decimals under 1 L (speed.ts already did this). Net in L instead of Z %, so no % appears on her screen at all. |
| S8 | Mockup: `basis +103 [M]` is a 1-minute pair (A121: 1-min noise up to 72 pts); use fold.BIX_MS's 3-min median. `.wrap` is 1229 px + 24 px padding, content-box, so it scrolls sideways at her width. The ≠ line is ~150 characters with a parenthesis | 3-min basis · `box-sizing:border-box` · the ≠ line as one row of ≤ 6-word cells |
| S9 | `ROLL TOOTA` text prints `roll 10:21 se pehle` at 10:21: the current minute, not the roll's (BNF 27 Oct) | Print `roll_mark`'s minute. |
| S10 | `day_hi` / `day_lo` are not updated on `?` minutes, so the 09:15–09:30 extremes are missing from WAPSI's "day's run" | Update them in `push`. |

---

## FINE (checked, holds)

- **Look-ahead, reference:**
  - `Ref.for_day` reads only sessions < day: NIFTY 22 Oct uses 20 sessions, newest 21 Oct; NIFTY 27 Oct EXPIRY uses 7, newest 19 Oct; BNF 27 Oct has 1, so it falls back to "aaj ke minute".
  - `ref/<IDX>.json` holds today, but `for_day` excludes it. The absolute clause's all-session median is also prior-only.
- **Look-ahead, within the day:** I truncated 22 Oct (4 cuts), 26 Oct (2) and 23 Oct (4) × 3 indices, re-ran, and compared the picture at T. All pictures were identical. Stamps were identical except the M1 rewrite.
- **Drop-in:** pure (no I/O, stdlib only); about 1 ms a step (worst 12 ms) per index; about 4 KB per response; the whole day held in memory is trivial.
- **Kept right:** 21 Oct 10:04 (the line THE READ needed), 26 Oct 10:28 WAPSI with no contradiction, the roll reads, UNWIND at the close, LIGHT theme, no price chart, s/f tags, grades as n/N counts.

Files: `opus/review_run.py` (the harness: replay · trunc · refs · cost) and `opus/review/<IDX>_<day>.txt` (fresh stamps plus every minute).
