# RAFTAAR round 2 — Fable's critique of Opus (27 Oct 2026)

Both engines were run on the same record. Opus's lines are quoted from `opus/replay/<day>.txt`; for 6 Oct and 25 Sep (which
Opus did not replay) I ran a scratchpad copy of `opus/raftaar.py` with only its data path changed (nothing written under `opus/`).
Mine are `fable/replay/<IDX>_<day>.txt` and `python raftaar.py NIFTY <day> --all hh:mm hh:mm`. All numbers [M] off the chain record.

## 1. STEAL — what Opus got right that I missed or did worse

| # | Opus | evidence | what I had |
|---|---|---|---|
| S1 | **Size ranked against prior sessions** (same index, day kind, day part; p70 / p90; today's own minutes as fallback) | first word 09:20–09:34 vs my 09:41 (SOCH RAHA till the floors exist). **27 Oct 10:04**: Opus `CHAL ▲ 5/10 THEEK · CALL BHAAG + PUT LIKHAI · net +196L` on CE 22700/22750 **−98L near** and PE **+103L** [M]; mine read it at 10:02–10:03 (CE RETREAT 22700, THEEK 3/6) then **KHAMOSH 10:04–10:06** because m15 fell +57 → **+40 vs P = 41**, and the LOAD bar (3× an opening-inflated floor ≈ 120L) was above +103L | a fixed P (0.18 %) and a rolling-hour floor that the open inflates |
| S2 | **The leg is an object** with end rules and a `MOVE KHATAM` line carrying the reason | mine on **21 Oct 11:37 / 11:39** stamped `LOAD CE 22900` twice *inside* the ▼ trend leg because m15 dipped to −39 / −35 for single minutes; **26 Oct 10:37–10:49** flickered ▼ / CHOP / ▼ / CHOP every minute (nothing stamped, nothing held) | the word is re-derived every minute; a leg has no memory |
| S3 | **THAK needs price**: writers into the move, or pressure against while price stalls, or a new extreme with OI silent; **RUKA** = a pause is not a turn | **21 Oct 11:31** mine: `THAK RAHA` (with5 ≤ ½ the 11:25 burst while spot paused 22,878–22,889 for 3 min) → spot then fell to 22,823 by 11:40 and 22,745 by 12:15; Opus **11:34 TEZ 8/10** | THAK on flow fading alone |
| S4 | **PIN TIKA** (stock: both sides *holding* about equal size at the strike, range ≤ 0.6 step) beside PIN BAN RAHA (flow) | 26 Oct 15:12 `PIN TIKA @ 22700 · CE +127L PE +155L baithe`; 21 Oct 14:42; 25 Sep 11:43 / 12:13 / 12:29 / 15:08 @ 23100; 6 Oct 11:41 / 11:54 / 13:18 / 14:55 @ 22700 — her "holding equal amount of position so its pin" | flow-only PIN, "balanced" as a flag |
| S5 | **PHANSE** tag: the covered strikes were written in the last 60 min | 27 Oct 10:21 `PUT BHAAG RAHE · PHANSE: 22700PE +91L 10:15 tak likha · 22800PE +72L 10:16` — today's writers trapped, not old positions booked | nothing separates trapped-today from booking |
| S6 | **Grade with a size gate**, unreadable checks dropped from N, printed "at the stamp → 10 min later" | the 27 Oct 10:20 flush (PE −172L net) is **6/10 MAZBOOT** for Opus and **HALKA 2/6** for me: my `held ≥ 3` and `held ≥ 9` are false at every birth by construction, and peers lag 2–3 min, so my stamps are structurally HALKA | a fixed /6 with two dead checks at the stamp |
| S7 | **`?` with its reason** when spot leaves the recorded strike window | 8 Oct NIFTY 14:56 `? PADH NAHI SAKE`; SENSEX 8 Oct `?` 12:54 → close | I skipped and counted missing strikes (`miss`) and never surfaced it |
| S8 | **Stamp only at THEEK**, KAMZOR shown live not stamped, KHAMOSH once after ≥ 5 min | Opus 7–29 lines (NIFTY 11–26). Mine 20–37; under Opus's rule mine become **23 / 22 / 29 / 28 / 21 / 17 / 18 / 9 / 26 / 12** on the ten NIFTY days [M] | every key change held 3 marks, HALKA included |
| S9 | Hinglish structure words and **ATKA ▲/▼ · zor hai, price nahi** (lead side named) | `CALL ITM cover`, `cap upar shift`, `deewar moti / hat rahi`, `PUT bhaag rahe` read as she talks; ATKA says the same as my LOAD and better | English pattern names (RETREAT, WALL BUILD); LOAD |
| S10 | Fut leg and the other indices as **grade checks, not names**; SENSEX on NIFTY's fut (§1q) | evidence row `fut ✓ · BNF ✗ SNX ✗` | peers only; no fut |

## 2. WRONG — where Opus would mislead her (same day, same minute, both outputs)

**W1 · 26 Oct 10:40 — a pullback stamped as a MAZBOOT move that contradicts THE READ.** Day +300 (22,452 → 22,753), the 09:55 leg topped
10:08 at 22,699.
- Opus 10:40 22,619s: `CHAL RAHA ▼ · SHURU 6/10 MAZBOOT · PUT BHAAG RAHE ▼ · spot −43 pts/15m · net −64L · ≠ READ TREND▲ · RAFTAAR CHAL RAHA ▼`
  → 10:50 `MOVE ▼ KHATAM · price ne 51 pts wapas diye (leg 98 pts)`. Same again 12:11 `CHAL ▲ 6/10→3/10 ≠ READ RANGE` on +33 pts/15m.
- Mine 10:30 `CHOP · dono taraf legs r30 76` → 10:50 `KHAMOSH`; the ▼ never held 3 marks (10:37 ▼, 10:38 CHOP, 10:40 ▼, 10:41 CHOP).
- A MAZBOOT "≠ READ TREND ▲" at the low of a 10-minute pullback is the line that takes her out of the long she is trying to hold
  (how-she-sells: "my problem is holding trades for longer"). Spot: 22,619 → 22,690 by 14:11 → 22,753 close.

**W2 · 27 Oct 10:43 — 26 points called a move on expiry.** Spot stuck 22,716–22,766 from 10:30 to 12:25.
- Opus 10:43 22,754s: `CHAL RAHA ▲ · SHURU 4/10→6/10 MAZBOOT · PUT FLOOR SAATH ▲ · spot +26 pts/15m · net +103L` → 11:21 `KHATAM · 54 pts
  wapas (leg 74)`; then 11:32 `ATKA ▼ 5/9 · CALL likh rahe 22750/22800 +80L · PUT bhaag`.
- Mine 10:30 `CHOP` → 11:01 `LOAD PE 22750 +142L` → **11:24 `PIN 22750 · baari-baari balanced · net45 CE +28L PE +227L · r45 57`**.
- +26 pts with puts +103L at 22,750 on expiry is the pin being built, not a leg. The ranked D cuts both ways: it rescued 10:04 (S1) and
  invented 10:43.

**W3 · 6 Oct 09:43 — the morning's biggest put writing labelled "nothing special".**
- Opus 09:43 22,621s: `KHAMOSH · KUCH KHAAS NAHI · net +301L · PUT likh rahe [22600PE +104L 22500PE +65L]` (expiry open day-part: the
  p70 of 5 prior expiry sessions is enormous). 09:34 it had `PIN BAN RAHA @ 22600 4/7` on CE +235L / PE +396L per 15 m.
- Mine: `KHAMOSH` all morning (the rolling floor normalised the same flows). **Both bars fail at the open, in mirror image**; see D1.

**W4 · 22 Oct — her "range day, chop on both sides" never says CHOP.** Opus admits it (DESIGN §5): CHOP was the big word ~15 min and
was never stamped. Six swings were stamped as CHAL RAHA (four with `[CHOP ke andar]`), e.g. 10:24 `CHAL ▲ 7/10 → 3/10 KAMZOR · CALL
BHAAG · [CHOP ke andar]` → 10:49 `KHATAM · 85 of 152 back`; 11:48 `CHAL ▼ 7/10 MAZBOOT`; 13:27 `CHAL ▼ 7/10→8/10`. On her stop-loss day
the screen said "a move" six times, three of them MAZBOOT. Mine: `CHOP` 128 min, stamped 7×, first at 10:07.

**W5 · SENSEX cadence.** Opus: "OI steps every ~160 s", hence F = 8, S = 16, hold 6. Measured on the ATM strike, rows 09:30–15:00 [M]:
NIFTY changes every 52–56 s median (mean 43–52), BANKNIFTY 45–54 s, **SENSEX 53–64 s median (mean 75–82 s)** on 22 Oct, 8 Oct, 27 Oct.
SENSEX is ~1.7× slower, not 2.7×; a 6-min hold delays every SENSEX stamp 3 min against NIFTY's for no reason.

**W6 · The 30-min stale end is slow.** 26 Oct first leg: top 10:08 at 22,699; Opus `MOVE ▲ KHATAM · 30 min se naya high nahi` at **10:38**
(spot 22,609, −90 from the top). Mine: `THAK RAHA` 10:06, `KHAMOSH` 10:15. Opus's 21 Oct 10:42 and 12:53 ends are 30 min late the same way.

## 3. THE DECISIONS — my vote, the other case, the evidence

**D1 · Noise bar.** *Vote: Opus's prior-session rank (index × day kind × day part, p70 / p90) for "notable / BADA", with one absolute
clause: a side flow ≥ 2× that index's all-session median (any day part) is never noise.* Keep my rolling-hour medians only for the
speed change (TEZ / DHEEMA against the last hour's pace), never for "is this a story". Other case: mine needs no cache and no day-kind
table (anytime-start is trivial). Evidence: S1 (27 Oct 10:04, mine missed a −98L / +103L event), 6 Oct (Opus PIN BAN RAHA 09:34, CHAL
▲ 09:58, PIN TIKA ×4; mine KHAMOSH 296 min), W3 (Opus's 09:43 +301L "nothing" — the clause fixes it), W2 (a ranked D made 26 pts a move:
so D keeps a floor of 0.5 P in points as well).

**D2 · When a move ends; trend day as one move or swings.** *Vote: Opus's leg object and KHATAM line, with three changes: THAK requires
a price stall (no new extreme ≥ 5 min) AND flow against or fading; stale end at 15–20 min, not 30; a leg against the day's drift that
has retraced < ½ of the prior leg is **WAPSI ▼/▲ (din ▲/▼)** — a pullback — and never prints a ≠ READ line.* Both engines read 26 Oct
as swings; the day belongs to §1o / THE READ (header DIN). Evidence: W1 (Opus's ≠ on the 10:40 pullback), S3 (my 11:31 THAK with 60
pts left), W6 (Opus's 10:38 end, 30 min after the top), S2 (my LOAD flicker inside the 21 Oct leg).

**D3 · CHOP vs PIN vs alternating moves (22 Oct).** *Vote: CHOP is the big word when legs both ways sit inside 30 min and the current
leg has no OI of its own (my trigger); the current swing is shown small with its OI story (Opus's `[CHOP ke andar]`); a swing with OI
behind it inside a chop is stamped at most THEEK, never MAZBOOT, and never prints ≠ READ.* PIN takes all three readings: Opus's PIN
TIKA (stock) and PIN BAN RAHA (flow), my **baari-baari** (one side loads, then the other, same strike, 45 min, range < 2 P). ATKA
replaces my LOAD. Evidence: W4 (six "moves" on her stop-loss day, CHOP never stamped), W2 (27 Oct 22,750: mine PIN 11:24, Opus ATKA
▼ 11:32 — both true; PIN first, ATKA as its qualifier "CE pressing"), 25 Sep (both read PIN 23100; Opus from 11:43, mine from 10:02).

**D4 · The grade.** *Vote: Opus's n/N with the size gate and unreadable checks dropped from N; drop my `held ≥ 3 / ≥ 9` (dead at the
stamp); keep my strikes-agree (≥ 2/3 of the voting strikes in the defining zone) and Opus's chop-ke-bahar and fut leg; print "at the
stamp → 10 min later"; words MAZBOOT / THEEK / KAMZOR.* Other case: a fixed /6 is simpler to read. Evidence: S6 (27 Oct 10:20 flush:
6/10 vs 2/6), Opus's own "→" column shows which stamps faded (22 Oct 10:24 7/10 → 3/10).

**D5 · Stamp volume.** *Vote: Opus's rule — a picture is stamped at the first minute it reaches THEEK, KAMZOR is shown live and never
stamped, KHAMOSH once after ≥ 5 min, KHATAM only for a stamped leg; WAPSI legs stamp without a ≠ line.* Measured on my rows: 20–37 →
9–29 a day; Opus 7–29. A normal day should land ≤ 20. Evidence: S8, W1 (the ≠ lines are the costly stamps), W4.

**D6 · SENSEX cadence, BANKNIFTY thin OI.** *Vote: SENSEX F = 8 / S = 16 (fine, cheap), hold 3 not 6 (W5: 1.7× slower, not 2.7×);
SENSEX reads its own OI and NIFTY's fut leg (§1q, Opus did it). BANKNIFTY: on non-expiry weeks the nine hold a few lakh (ATM 1.7L vs
NIFTY 44L on 8 Oct, Opus [M]); my relative floor graded a **+50k** flow `LOAD PE 54800 THEEK 3/6` at 09:59 — wrong scale. Tag BNF
"patla" when the nine's OI is under an absolute floor, cap its grade at THEEK, and show NIFTY's word beside it in the header (her own
§1q habit).* Other case (Opus Q2): read NIFTY's OI speed for BNF — no: BNF trends where NIFTY reverts (house rules); its own OI, capped.

**D7 · One vocabulary (what she sees).** *Vote: Opus's words, plus two of mine.* Big: **CHAL RAHA ▲/▼** (SHURU · TEZ · JAARI · RUKA ·
THAK) · **WAPSI ▲/▼ (din ▼/▲)** · **CHOP** · **PIN** (TIKA / BAN RAHA / baari-baari) · **ATKA ▲/▼ · zor hai, price nahi** · **KHAALI
CHAAL** · **UNWIND · dono nikal rahe** (both sides net cutting; expiry afternoons — Opus has no word for it) · **KHAMOSH · kuch khaas
nahi** · **?** (padh nahi sake / padh rahe / paimana nahi). Under the big word, the qualifier is mine — **SAATH / ULTA / MILA-JULA**
(writers with or against the move) — because Opus's stories 1–2 carry "against" only as PHANS RAHE / ROK RAHE and lose it elsewhere.
Structures: Opus's (`CALL likh rahe · ITM cover · bhaag rahe · roll UP / DOWN · deewar moti / hat rahi · ruke`) with **PHANSE**. Grade
words MAZBOOT / THEEK / KAMZOR. One more read both engines produced and neither named: **27 Oct 12:42 → 12:43**, the cap rolled
(CE near −41L, wall +28L at 22850–22950) and one minute later the roll failed (near −153L, wall −34L, +70 pts) — "roll toota" is the
squeeze read itself and deserves its own line.

## 4. Where we already agree (no decision needed)

The nine strikes and the two zones (ANDAR / BAHAR = my near / wall, identical cut at ATM); the roll read (`CALL roll UP` = my ROLL,
same ½ test in spirit); 15-min story + 5-min speed; 3-mark hold; the day type is §1o's and the day call is THE READ's; the ≠ line
needs numbers and a strong grade; §1d fronts shown verbatim; no %, no fut-leg naming, light theme, no price chart. Both engines put the
same minute on the same leg on 8 Oct (TEZ at 11:26, both), 23 Oct, 21 Oct 09:57 / 10:00 and 26 Oct 09:56 / 09:57.
