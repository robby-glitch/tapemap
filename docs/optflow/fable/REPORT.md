# 3 Nov 2026 — Jarvis, the day, and option flow × OI (Fable, after the close)

Conventions: **[M]** measured from `data/` as named, **[I]** inferred or a threshold I chose · *s* spot · *f* futures · L = lakh
quantity (NIFTY lot 75, SENSEX lot 20) · counts, never a rate · every read at minute t uses data ≤ t (windows named).
Scripts and the embedded data: `load.py`, `study.py`, `day.json`, `make_mockup.py` in this folder; `NOTES.md` has the
decisions and the clean-room declaration (one accidental exposure, declared there and in (e)).

**The day in one line [M]:** NIFTY fut 23,525 → 23,780 (+255), low 23,522 at 09:15, high 23,800 at 13:40; futures OI
−9,500 lots (short-covering day, like 30 Oct); VIX 15.51 → 16.22 at 13:17 → 15.66 (rose WITH the index); NIFTY weekly
expiry; she marked no trade (`day_state.hold_trades = []`). SENSEX fut 76,301 → 76,898 (+597), high 76,957 at 13:38.

---

## (a) Jarvis on 3 Nov

### Timeline (NIFTY; the ACTION word as logged in `jarvis/call_2026-11-03.jsonl`, fut at the word, what followed [M])

| said | word | WITH/AGAINST | fut | +15 | +30 | best / worst in 30 | verdict |
|---|---|---|---|---|---|---|---|
| 09:18 | OPENING (lean ▲) | 1/1 | 23,595 | +68 | +84 | +84 / 0 | lean right from minute 3; no word by rule |
| 10:00 | HOLD ▲ | 3/2 | 23,669 | +6 | +21 | +21 / −28 | first word, 45 min after the leg qualified ("fuelled 09:26") |
| 10:11 | WATCH ▲ | 0/5 | 23,641 | +39 | +54 | +64 / 0 | **wrong, at the pullback low** (the 10:00–10:14 low was 23,640) |
| 10:29 | HOLD ▲ | 3/2 | 23,680 | +8 | +24 | +25 / 0 | fine |
| 10:35 | TREND ▲ | 5/1 | 23,705 | −6 | −35 | 0 / −35 | **late: said at the leg's extreme** (23,715 at 10:35) |
| 10:41 | HOLD ▲ | 2/1 | 23,695 | +5 | −15 | +9 / −25 | fine for a holder |
| 11:08 | WATCH ▲ | 0/6 | 23,670 | +29 | +30 | +30 / −8 | **wrong, at the pullback low** (11:00–11:14 low 23,661) |
| 11:23 | HOLD ▲ | 2/2 | 23,699 | +1 | +21 | +24 / −37 | fine |
| 11:59 | TREND ▲ | 5/0 | 23,735 | −31 | −18 | +9 / −51 | **late: 14 min after the break, 6 min before the top** (23,747 at 12:05) |
| 12:12 | WATCH ▲ | 1/3 | 23,702 | +15 | −4 | +18 / −18 | right to be cautious (the 12:10 flush) |
| 12:44 | HOLD ▲ | 1/0 | 23,704 | +32 | +48 | +48 / −12 | fine |
| 13:20 | TREND ▲ | 7/0 | 23,767 | +21 | +21 | +28 / −12 | 4 min after the break; +28 was all there was |
| 13:27 | HOLD ▲ | 4/1 | 23,755 | +40 | +12 | +40 / 0 | fine |
| 14:04 | WATCH ▲ | 0/4 | 23,755 | −15 | −6 | +14 / −31 | right |
| 14:22–15:20 | *silence* | | | | | | **A214: no call for 58 min; the 14:04 WATCH sat on the screen with no age** |
| 15:23 | HOLD ▲ | 1/0 | 23,775 | | | | after the chain's end; fine |

Counts [M]: 15 word changes (vs 52–79 on 21 / 29 / 30 Oct — the v3 two-close rule works), lean ▲ from 09:18 and
**0 flips**, PALAT? 0. SENSEX: 14 changes, lean ▲ from 09:17, 0 flips, **never TREND on a +597 day** — its count never
exceeded WITH 4, because 7 of its pieces read "could not check" all day (`missing` lists "flow from NIFTY (§1q)": G13 is
still open live on 3 Nov; THE READ / DECODE / BADA have no SENSEX rows).

### Right / wrong / late / silent / flicker

- **Right:** the lean. ▲ from the third minute, never flipped, PALAT? never cried. A holder of a CE bought at the open or
  a PE sold at the open was never told to leave. WATCH 12:12 and 14:04 were the two real pullbacks.
- **Late:** every TREND stamp came at or near an extreme: 10:35 (the 10:35 high), 11:59 (6 min before the 12:05 top),
  13:20 (23,767; the day's high 23,800 came 20 min later, +28 at best). The count's pieces (Sides 5-min slot, ±7
  writers, speed) are confirmations of a move that has already printed.
- **Wrong:** WATCH 10:11 and WATCH 11:08, both at the exact pullback low with AGAINST 5–6 and WITH 0. The option flow at
  those minutes (c) said the opposite: ITM call writers covering into the dip and put longs giving up, i.e. the dip
  was being bought by writers, not sold by them.
- **Silent / hidden:** (1) the first-hour TREND — the atlas's one tell (positive on 9 of 11 days when called
  09:27–09:56, 0 of 9 at or after 10:00) — qualified at 09:26 ("fuelled 09:26", 2.3σ, 0 flips) and was hidden by the
  OPENING rule until 10:00, then HOLD (WITH 3 < AGAINST 2 + 2). The best-trade shape appeared and the word did not.
  (2) 14:22–15:20 (A214): no call, no age on the last word; `blind` is false on every row because the pass that
  checks the clock was itself the thing starved. (3) No PIN word on an expiry afternoon: from 13:14 the call writers
  pressed at 23,750–23,800 while put writers wrote 23,700–23,750; price pinned 23,723–23,800f for 2 h 15 min while
  Jarvis said TREND/HOLD/WATCH ▲.
- **Flicker:** none worth the name (15 changes). The remaining HOLD ↔ WATCH toggles track the count, which tracks
  price.
- **Against her other voices:** 7 distinct SELL setup alerts went to the stream on a ▲ day (NIFTY 09:45 ZONE+FADE,
  10:45 ZONE, 13:45 ZONE; SENSEX 10:25 FADE-D, 12:15, 13:55, 14:05 ZONE), each stamped MATCH while Jarvis's lean was ▲.
  Three were under water by +30 to +101 pts within 15 min (09:45, 10:25, 10:45); four worked (12:15 SENSEX after
  +100 against first, 13:45 NIFTY −26, 13:55 SENSEX −119, 14:05 SENSEX −127). What separated them is in (b).
- **Pushes:** 24 on NIFTY, `who` null on 22. The option flow answers `who` on every one (c).

### Ranked improvements (what would have made 3 Nov better; none changes a registered rule)

1. **Say the first-hour candidate before 10:00.** OPENING keeps its no-arrow rule, but when the leg already qualifies
   (TREND quality, ≥ 1.5σ, 0 flips) and the writers' pieces are unanimous, show `OPENING · TREND ▲ forming since 09:26 ·
   writers 3/3`. On 3 Nov that line was true from 09:27. [I: the atlas's own window 09:27–09:56]
2. **Add the option-flow WHO to the count, writers first** (the weave in (d)): two pieces, `cap` and `floor`. At
   10:11 and 11:08 they would have read WITH (ITM calls covering, puts dumped), turning WATCH into HOLD; at 13:14–14:04
   they read AGAINST (cap WRITE pressing five windows in a row), which would have blocked TREND ▲ 13:20 and kept HOLD.
3. **G13 for SENSEX, now.** SENSEX's count is starved; it cannot say TREND. Its own option flow (c) also reads at
   5-min with scaled thresholds — but that is a §1q change, hers (f).
4. **A PIN word on expiry day after 13:00:** both sides WRITE at the same or adjacent strikes for 2 closes → `PIN
   23,700–23,750s`. For a seller that is the trade of the afternoon; for a buyer it is the no-trade.
5. **Age the word on the face.** The card carries `asof`; the face must print `WATCH ▲ · 20 min old · server starved`
   when `asof` lags the clock by more than BLIND_MIN, independent of the server's own blind check (which cannot run
   when the server is the thing that stalled).
6. **One voice for fades:** a SELL fade alert carries the cap's WHO at the band; WRITE (writers pressing) = legal,
   COVER / BUY = illegal, OI? = PATA NAHI. The §1d gate reads OI slope only; on 3 Nov the 09:45 and 10:45 SELLs
   passed "CE likh rahe" by OI while the flow said the calls were being bought (c).
7. **`who` on every push** from the strike's own flow (G5): TOOT by COVER (writers running) vs TOOT by DUMP (buyers
   leaving). On 3 Nov the three TOOT-by-DUMP pushes all reversed within 30 min; two of four TOOT-by-COVER ran (b).

---

## (b) Patterns (descriptive; n stated; nothing here is a rule)

1. **A TOOT is two different things.** 24 NIFTY pushes; at the handshake's answer minute the attacked strike's flow was:
   TOOT + COVER (writers buying back) 4 — 10:34 (+30 min: −25), 11:45 (−21), 12:10 ▼ (−20, with the push), 13:16
   (+20); TOOT + DUMP (option longs leaving, writers passive) 3 — 11:55 (−30), 13:41 (−39), 14:24 ▼ (−14 i.e. against
   a ▼ push: price rose); TOOT + QUIET 1 — 13:35 (−28). **All three TOOT-by-DUMP were taken back; the OI-only TOOT
   cannot tell them apart.** n = 7. INCONCLUSIVE. Pre-register: *a TOOT whose strike shows DUMP is a buyers' exit,
   not a wall breaking; expect it to be retraced within 30 min more often than a TOOT by COVER.*
2. **NAHI with WRITE = the wall pressed, and held.** NAHI + WRITE 5 (10:18 +21, 13:08 +44, 14:02 −38, 14:06 −3,
   14:41 ▼ then flat); NAHI + BUY 3 (10:38, 11:05 ▼, 11:41: the push went on +29 / −23 / +29 at 15). n = 8.
   INCONCLUSIVE; the 30 Oct note ("NAHI in a trend = wall absorbing, fuel still running") now has a direct test: NAHI
   + BUY (calls lifted, writers posting) continued, NAHI + WRITE did not.
3. **SELL fades and the cap's WHO.** 7 distinct SELL alerts. Cap WRITE (call writers pressing) at the alert: 4 — 12:15
   SENSEX (+100 against first, −54 later), 13:45 NIFTY (−26 at 30, worst against +2), 13:55 SENSEX (−119), 14:05
   SENSEX (−127 min); 3 of 4 lower at +30. Cap BUY / QUIET / MIXED at the alert: 3 — 09:45 NIFTY (+30 against,
   worst +34), 10:25 SENSEX (+101 against), 10:45 NIFTY (+15 then −26); 0 of 3 lower at +15. n = 7. INCONCLUSIVE.
   This is §1d's clause ("the defending front still building") read with the aggressor instead of the OI slope.
4. **Put writers pressing before a cap break (the lead, if there is one).** FLOOR WRITE for ≥ 2 consecutive 3-min
   windows (aligned): 8 episodes. Followed within 15 min by ≥ +20f: 09:18–09:27 (+40), 10:27–10:36 (TOOT 10:34, +10
   then stall), 11:39–11:45 (+35), 12:36–12:42 (+19); by nothing: 09:42–09:51 (−2), 11:18–11:27 (+8); by the opposite:
   10:54–11:00 (−40). n = 8, 4 with. INCONCLUSIVE, and the writers' pressing coincided with the first 15-min drive
   rather than preceding it. **Option flow is a WHO read, not a timer** — the README's own line, and 3 Nov agrees.
5. **Put writers covering was a shake every time on 3 Nov.** FLOOR COVER ≥ 10L: 11:30–11:33 (−11.6L; +28 in 3 min),
   12:09–12:12 (−115L, the day's biggest; the floor was rewritten +53L in the next window, +14 at 15), 14:15–14:18
   (23,700 PE −41L; +41 by 14:38), 14:36–14:39 (−119L at 23,500/23,600 PE: the expiry unwind, G9, not a break).
   n = 4, 0 breaks. Her "a stop is usually a PAUSE" with the tell she named: **the writers came back in the next
   window.** Pre-register: *a COVER on the floor/cap is a BREAK only if the next window is not WRITE on the same side.*
6. **Call longs dumping at a high = the top, twice.** CAP DUMP ≥ 25L: 11:54–11:57 (−48.6L; top 12:05, −45 by 12:12),
   14:15–14:18 (−62.8L; low 23,723 ten minutes later, then the 14:38 push). 10:33–10:36 (−25L, mixed) → stall. n = 3.
7. **Flow lean vs Jarvis lean, 125 three-minute closes [M]:** both ▲ 56; flow ▼ while Jarvis ▲ 42 (all in 11:56–12:12
   and 13:14–14:44); flow flat 26. The flow lean flipped sign 8 times in the day; Jarvis's 0. The flow lean is the
   faster and noisier instrument; Jarvis's lean is the slower and right one on a trend day. Neither replaces the other.
8. **Cross-index:** SENSEX's own option flow (05 NOV, 2 DTE, ~1/65 of NIFTY's volume) printed the same turns within one
   5-min window: 10:10–10:15 FLOOR WRITE + cap COVER before the 10:17–10:36 leg; 12:05–12:10 CAP DUMP (4× its median
   aggression) at the 76,780 top; 12:50–12:55 cap COVER + floor WRITE before the 12:55–13:38 leg; 13:30–13:35 76,700
   PE WRITE BADA (the floor moving to ATM) at the high. "When the indices move in sync the move is real" held in
   option flow too. n = 1 day.
9. **VIX rose with the index** (+0.71 to 13:17) on a short-covering day with CAP BUY (calls lifted) windows in the
   morning: call demand, not fear. One day; a note, not a read.
10. **Trapped inventory (the chain's day-VWAP vs ltp, OI built today):** by 12:00 the 23,700 CE writers had written
    ~31 and saw 47 (−52 %, +200L built) — the wall that was run over four times (TOOT 10:34, 11:45, 11:55, 13:16);
    every put strike's buyers were under water by 40–60 % from 11:00 on (expiry theta), which is why every dip
    printed FLOOR DUMP (put longs leaving), not FLOOR COVER: **the puts' pain was the buyers', so the dips had no
    writer fuel.** That is the one-sentence explanation of the day's shape, and it was readable from 10:00.

---

## (c) The 3 Nov option-flow × OI read, minute-true

Method (in full in `NOTES.md`): per strike, per 3-min window ending at t, dOI from the chain's last snapshot ≤ t vs the
one ≤ t−3, and Dext's delta (lifted − hit) summed over the three closed minutes. **WRITE** = OI up, sellers hitting
(writers pressing, *likh rahe*); **BUY** = OI up, buyers lifting (writers posting, *kharid rahe*); **COVER** = OI down,
buyers lifting (writers buying back, *bhaag rahe*); **DUMP** = OI down, sellers hitting (option longs leaving, *nikal
rahe*); MIXED when |delta| < 0.2 × |dOI|; QUIET under 1.5L (NIFTY) / 2,500 qty (SENSEX); OI? when the chain is more
than 2 min old. CAP = calls at/above spot, FLOOR = puts at/below spot, ITM = the other two. The word is from (d).
Everything below is NIFTY unless marked; "next" is hindsight and marked so.

| at | the option flow said (data ≤ this minute) | Jarvis said | next [hindsight] |
|---|---|---|---|
| **09:21** | FLOOR WRITE +155L in 3 min (23,450–23,600 PE, sellers hitting −45.6L): put writers pressing under a +90f open. CAP MIXED +126L. | NO LEG → OPENING ▲ (09:18) | 23,614 → 23,665 by 09:27 |
| **09:24–09:27** | CAP BUY +112L then +32L with delta +48L / **+203L** (call buyers lifting, 23,800 CE BADA +31L), FLOOR WRITE +124L / +91L (delta −158L), **ITM CE COVER** 23,600 CE −19L BADA (yesterday's call writers buying back as spot crossed 23,600). Word: **UP FUEL** from the first close. | OPENING ▲, no word | the day's low was already in; +148f in 15 min |
| **09:27–09:39** | CAP WRITE +78.5L (delta −88L), +45.5L, +38.9L, +22.4L (−53.6L): call writers pressing at 23,650–23,700 → **LID 23,650–23,700s**; floor keeps writing. | OPENING ▲ | fut 23,640–23,680 for the next 2 h |
| **10:00–10:03** | CAP WRITE +30.7L, delta **−111L** (23,800 CE BADA +12.5L, 23,650/23,700 CE): writers lean on the dip. | HOLD ▲ (10:00) | 23,650 → 23,641 (10:11) |
| **10:12–10:15** | **ITM CE COVER** 23,600 CE −13.6L BADA, 23,650 CE −7.9L BADA; FLOOR DUMP −8.9L (23,600 PE −7.8L BADA: put longs give up). The dip is bought by call writers, not sold by put writers. | **WATCH ▲ 10:11, WITH 0 AGAINST 5** | 23,641 → 23,690 by 10:29 |
| **10:27–10:33** | FLOOR WRITE +27L, +34L (23,600 / 23,650 PE pressing, delta −58L / −57L): the floor rises to 23,650. | HOLD ▲ 10:29 | TOOT 10:34 |
| **10:33–10:36** | the 10:34 push (+583 lots): 23,600 CE −32.7L and 23,650 CE −31.5L, both MIXED (bought back AND sold), 23,750 CE DUMP −13.3L. Then **10:36–10:39 CAP WRITE +27.7L**: 23,700 CE +11.8L BADA, 23,750 CE +7.9L — the cap re-forms one strike up (her G6 strike shift). | TREND ▲ 10:35 at 23,705 | 23,715 top at 10:35; 23,690–23,715 for an hour |
| **11:03–11:09** | CAP WRITE +14L with delta **−135L** then +16.7L (−55.7L): writers pressing hard at 23,650–23,700 CE; floor DUMP −18.8L (put longs selling into the dip). Word: LID. | WATCH ▲ 11:08, 0/6 | low 23,661 at 11:08; back to 23,700 by 11:33 |
| **11:30–11:36** | 11:30–11:33 FLOOR COVER −11.6L (23,600 PE −16.4L BADA, 23,700 PE −12.7L) and CAP DUMP −33.7L: DOWN FUEL for one window. **11:33–11:36 CAP BUY +19.6L (delta +75.8L, 23,700 CE +11.9L BADA) and FLOOR DUMP −19.9L (delta −181L)**: the shake is over in three minutes, the puts bought on the dip are dumped. | HOLD ▲ 11:23 | 23,671 → 23,699 inside the window |
| **11:39–11:45** | FLOOR WRITE +24L / +16L (23,650 PE +9.2L BADA, 23,600 PE), delta −58L: put writers press at 23,650 with spot 23,670. | HOLD ▲ | push 11:45 |
| **11:45–11:48** | **CAP COVER −24.1L** (23,650 CE −23.9L BADA, 23,700 CE −12.5L BADA, delta +53.8L: writers buying back), **23,700 PE WRITE +10.7L BADA** (the floor moves to 23,700), FLOOR DUMP −22.9L (23,500 PE −12.9L). Word: **UP FUEL · writers**. | HOLD ▲ (TREND only at 11:59) | 23,720 → 23,743 by 12:00 |
| **11:51–11:57** | 11:51–11:54 CAP BUY +15.4L (delta +77L, 23,700 CE BADA): buyers chase. **11:54–11:57 CAP DUMP −48.6L** (23,650 CE −30.9L, 23,700 CE −23.6L, 23,600 CE −15.7L, sellers hitting): call longs take profit. The 11:55 push (+492 lots) was answered TOOT by OI; by flow it was DUMP. | TREND ▲ 11:59, 5/0 | top 23,747 at 12:05 |
| **12:00–12:09** | FLOOR BUY +4.7L / +5.8L (23,700 PE +17.7L BUY: puts lifted at the top), CAP QUIET → DUMP. Lean turns ▼ at 12:02, **DOWN FUEL at 12:08**. | TREND ▲ | the 12:10 flush |
| **12:09–12:12** | **FLOOR COVER −115L** (23,700 PE −58.3L BADA, 23,650 PE −44.8L BADA, 23,600 PE −44.7L BADA: put writers run), CAP DUMP −32.7L (delta −259L). Push ▼ 12:10 TOOT. | WATCH ▲ 12:12, 1/3 | 23,730 → 23,702 in the window |
| **12:12–12:15** | FLOOR +53L straight back (23,500 PE BUY +12.3L, 23,600 PE +12.2L BADA), CAP WRITE +16L (23,700 CE +15.2L BADA). **The floor is rewritten in the next window: a shake, not a break** (her "writers return"). | WATCH ▲ | 23,680–23,720 for 45 min |
| **12:54–13:03** | ITM CE COVER (23,650 CE −13.7L BADA, 23,600 CE −6.8L), **23,700 PE WRITE +8.6L BADA then +19.5L BADA** (put writers at the money, spot 23,684). | HOLD ▲ 12:44 | push 13:08 (NAHI), 13:16 (TOOT) |
| **13:15–13:18** | the day's biggest window: **23,700 CE COVER −66.6L BADA**, 23,650 CE −35L BADA (delta +33L), **23,700 PE WRITE +38.6L BADA**, FLOOR DUMP −44L (23,600 PE −30.2L: put longs leave). Word: UP FUEL · writers. | TREND ▲ 13:20, 7/0 | 23,753 → 23,777; high 23,800 at 13:40 |
| **13:18–13:24** | **CAP WRITE +45L, +31.5L** (23,750 CE +16.5L BADA, 23,800 CE +11.6L / +13.5L BADA, delta −48L both windows): the cap re-forms at 23,750–23,800 within 3 min of breaking 23,700. From here to 14:04 CAP WRITE in 9 of 15 windows (delta −89L, −71L, −82L, −70L at 13:42–13:57). **LID 23,750–23,800s; lean ▼.** | TREND ▲ → HOLD ▲ 13:27 | 23,754–23,800 for 60 min, then 23,723 |
| **13:30–13:42** | 23,700 PE WRITE +19.2L, **23,750 PE WRITE +15.6L BADA / +12.5L / +18.4L**, 23,700 PE +24.2L BADA: put writers write ATM and above with spot 23,735–23,742 on expiry day, while call writers press 23,750–23,800. **PIN 23,700–23,750s** (both sides writing the same strikes). Pushes 13:35 and 13:41 at 23,800 CE: TOOT by OI, QUIET / DUMP by flow — no writer ran. | HOLD ▲ | 23,800 was the high; −39 and −28 at +30 |
| **13:45** | ZONE SELL alert 2/4 at 23,771f with cap WRITE pressing for the third window running. | (the setup stream) | −26 at +30, worst against +2 [the one NIFTY SELL that worked] |
| **14:15–14:18** | **CAP DUMP −62.8L** (23,750 CE −28.7L, 23,800 CE −18L, 23,850 CE −13.3L, delta −222L: call longs capitulate), 23,700 PE COVER −41.1L BADA. DOWN FUEL. | WATCH ▲ 14:04 | low 23,723 at 14:25 |
| **14:18–14:21** | CAP BUY +18.9L (23,700 CE BUY +20.8L BADA: buyers lift at the dip), 23,650 PE WRITE +12L BADA. | WATCH ▲ | the 14:38 push +1,801 lots |
| **14:27–14:36, 14:45–14:54, 15:00–15:30** | **OI? — the chain stopped (A214).** Flow only: 14:33–14:36 calls delta **+206L**, puts **−294L** (the 14:38 push was buyers lifting calls and hitting puts, 23,700 CE then WRITE +17.6L at the answer: writers met them — Jarvis's TIKI / KHAREEDAR agrees). 14:36–14:42 with the chain back: 23,500 / 23,600 PE COVER −29L / −20L (expiry unwind, G9), **23,700 PE WRITE +26.2L BADA and 23,700 CE WRITE +19.7L, 23,750 CE BUY +25.4L**: the pin fight at 23,700–23,750 into the close. | no call 14:22–15:20 (A214); WATCH ▲ on screen | spot 23,700s at 14:59; fut close 23,780f |

**SENSEX (its own 05 NOV option flow, 5-min, scaled thresholds; §1q unchanged — this is a study, not a read for her screen):**
10:10–10:15 FLOOR WRITE +0.8L (delta −1.7L) + 76,300 / 76,600 CE COVER → leg 76,597 → 76,715 (10:36); 12:05–12:10 CAP
DUMP (delta −5.7L, 4× its median) at 76,780 → −150 in 5 min; 12:50–12:55 cap COVER −0.5L + floor WRITE → 76,737 →
76,900 (13:30); 13:30–13:35 76,700 PE WRITE +1.6L BADA (floor to ATM) + ITM CE COVER → high 76,957 at 13:38 then 76,750
by 14:26; 14:15–14:20 CAP DUMP −1.0L (delta −2.9L) → 76,735. Jarvis on SENSEX said WATCH/HOLD ▲ with WITH ≤ 4 all day.

**What the flow could not do on 3 Nov:** time the first-hour stall (it said UP FUEL / FLOOR UP from 09:20 to 10:53 while
fut went nowhere for two hours — writers pressing is support, not a trigger); and tell a shake from a break inside
its own window (11:32, 12:11 and 14:23 were all "DOWN FUEL" for one window and then taken back). The second is fixed
by the next-window rule in (d); the first is the honest limit: **it is a WHO read.**

*(c-end, owed): the comparison with README "The reads behind it" — not yet read (NOTES.md "Open").*

---

## (d) The weave — the algo design

**One principle:** nothing new decides on its own. Option flow × OI is **two more pieces in Jarvis's existing count,
writers first (GAPS §4), plus `who` on every push and a gate on fade alerts.** Display words are English for the
engine, Hinglish chips with numbers on the face. No %, no rate, no order path.

### D1. The per-strike WHO (new module `options_flow.py`, pure functions, the README's plan)

Inputs per strike per minute: chain OI (last snapshot in the minute, `oi_stale` when > 2 min), Dext closed-minute
`buy_volume / sell_volume / delta` and the biggest price cell. Output per strike per 3-min window ending at every
minute: `doi, delta, vol, who ∈ {WRITE, BUY, COVER, DUMP, MIXED, QUIET, OI?, FLOW?}, big`.

| threshold | value | why [I] |
|---|---|---|
| `OI_MOVE` | NIFTY 1.5L qty (2,000 lots) / strike / 3 min; SENSEX 2,500 qty (125 lots) | the smallest change a trader would call a wall moving; Jarvis's own "readable" bar for a strike is 3L / 3 min; SENSEX's ATM option volume measured ~1/65 of NIFTY's on 3 Nov, rounded to a sayable number |
| `AGG_X` | \|delta\| ≥ 0.2 × \|dOI\| | at least one contract in five that opened or closed was crossed by that side; a volume-based cut (15 % of volume) called everything MIXED because ATM option \|delta\| is ~11 % of volume at the median |
| `BIG` | one price, one minute ≥ 5L qty NIFTY (6,667 lots) / 8,000 qty SENSEX (400 lots) | scaled like the decoder's BADA PRINT, per price cell; 23,700 CE's biggest cell of the day was 33L |
| `OI_STALE` | 2 min | the chain's own cadence (~10 s); A214's holes must read OI?, never 0 |
| window | 3 min, rolling per minute, said at her 3-min closes | §1b's canonical bar; the ladder animates per minute, the word changes at closes |

Kill: if, over 20 sessions, the aggressor rule disagrees with a tick-rule check on the chain's own bid/ask (Upstox
ltp vs bid/ask at the same second) on more than 1 in 5 of the windows sampled, the WHO is unreliable → fall back to
OI-only words (Sides as today) and say so.

### D2. The four groups and the one word (`cap`, `floor`, `itm_ce`, `itm_pe`)

Group = sum of its strikes' dOI and delta; the group word by the same rule as a strike (floor 2 × `OI_MOVE`). The one
word from the cap and the floor, with its lean:

| cap \ floor | WRITE | DUMP | BUY | COVER |
|---|---|---|---|---|
| **COVER** | UP FUEL ▲ (writers) | UP FUEL ▲ | LID BREAKING ▲ | SQUEEZE — |
| **BUY** | UP FUEL ▲ (buyers chase into a rising floor) | UP BUYERS ▲ | QUIET — | DOWN BUYERS ▼ |
| **DUMP** | FLOOR UP ▲ | BUYERS OUT — | DOWN BUYERS ▼ | DOWN FUEL ▼ |
| **WRITE** | **PIN —** | LID ▼ | DOWN FUEL ▼ | DOWN FUEL ▼ (writers) |

(score: cap COVER +2 / BUY +1 / DUMP −1 / WRITE −2; floor WRITE +2 / DUMP +1 / BUY −1 / COVER −2; |S| ≥ 3 FUEL, 2 from
one side named by that side, 1 BUYERS, 0 by the pair.) The said lean needs **2 consecutive 3-min closes** (Jarvis's
`ACT_CLOSES`), so a FUEL word is never said off one window — a COVER taken back by WRITE in the next window is a
**SHAKE** (b-5), and a FUEL word spoken at once would have been wrong at 11:32, 12:11 and 14:23 on 3 Nov.

**PIN (expiry day only, after 13:00 [I]):** both sides WRITE at the same strike or adjacent strikes for 2 closes →
`PIN 23,700–23,750s`. Kill: over 10 expiries, if the pinned pair is left by more than one step before 15:15 as often
as it holds, drop the word, keep the cell.

### D3. Into Jarvis's count (jarvis.count, PIECES), writers first

Two new pieces after `sides` and before `wf7`: **`cap`** and **`floor`**, each with / against / "?" for the leg's lean:

- lean ▲: `floor` WITH on WRITE, AGAINST on COVER, "?" otherwise; `cap` WITH on COVER or BUY, AGAINST on WRITE, "?"
  on DUMP (buyers leaving the cap says nothing about the writers).
- lean ▼: mirror.
- OI? / FLOW? → "could not check — chain stale 3 min" / "no Dext footprint at 23,700 CE" (three sentences, never one).

On 3 Nov [M, replayed by hand from the table in (c)]: 10:11 the pieces read floor "?" (DUMP), cap WITH (ITM COVER
counts as cap COVER when the covering is at the strike just below spot) → WITH 1 instead of 0, AGAINST 5: still
WATCH by the rule; so **the count's other pieces also need the fix in (a)-2**: Sides' 5-min slot said CAPPED (ADD /
ADD) at 10:10 because OI rose on both sides — with the aggressor it was call writers pressing AND being covered
one strike down. The honest statement: the flow pieces alone do not flip 10:11; they flip 13:20 (cap AGAINST on
WRITE ×3 closes → WITH 7 − 1, AGAINST 0 + 1: TREND still said by the +2 rule). So the count change that matters is
**a veto, not a vote:** TREND is not said while `cap` (for ▲) or `floor` (for ▼) reads AGAINST at 2 consecutive closes.
[I] On 3 Nov that veto holds TREND ▲ 13:20 at HOLD (+28 best, −49 worst followed) and leaves 10:35 / 11:59 as they
were.

### D4. `who` on every push (handshake-2, G5)

At the answer minute, the attacked strike's WHO: TOOT + COVER = `TOOT · writers bhaag rahe −24L`; TOOT + DUMP =
`TOOT? · kharidar nikal rahe −23L` (OI fell, nobody ran: not counted as fuel); TIKI / NAHI + WRITE = `deewar tiki ·
likh rahe +15L`; NAHI + BUY = `kharidar ghuse +10L · writers posting`. The existing `who` (premium-vs-delta mirror) is
replaced by this where the footprint exists, kept where it does not, and the source named.
Kill (pre-registered, b-1): over 15 TOOT-by-DUMP and 15 TOOT-by-COVER, if the 30-min retrace counts do not separate,
the distinction is display only.

### D5. The fade gate's flow clause (a new registration beside §1d, never an edit of it)

A FADE / ZONE SELL arm carries `cap_who` at the band (BUY arm: `floor_who`). Stamped alongside, like §1d's `gate`,
never suppressing a row: LEGAL on WRITE, ILLEGAL on COVER / BUY / DUMP, PATA NAHI on OI? / FLOW?. Pre-registered
prediction: the ILLEGAL set's MAE is worse than the LEGAL set's over 10 sessions; falsifier as §1d's (no worse, or
never binds, or collapses without the worst leg). 3 Nov's 7 rows (b-3) are the first rows, not evidence.

### D6. The face's words and alerts

- **Jarvis card:** one new line `OPTIONS: UP FUEL · 23,700 CE bhaag rahe −24L · 23,700 PE likh rahe +11L` with its
  since-time; `PIN 23,700–23,750s` on expiry afternoons; `OI? since 14:27` when stale.
- **Telegram (her budget, write-once keys):** only BREAK (a FUEL word said, i.e. 2 closes), SHAKE (a FUEL word taken
  back), PIN, and TOOT? (a TOOT by DUMP). Nothing per minute.
- **The forward log:** `data/optflow/flow_<day>.jsonl`, one row per index per close: cap / floor / word / lean / the
  top strike each side / pushes' who. The evening scores the screen, never a recomputation (her rule).

### D7. What would kill the whole idea
- Dext stops (13:05 on 3 Nov live, before the after-close refetch): the WHO reads FLOW? and Jarvis falls back to OI-only
  — the Upstox option-tick backup in the README's "Open" is the real fix.
- The word flips more than 15 times a day at 3-min over 20 sessions → 5-min windows or a higher `OI_MOVE`; if still
  noisy, the per-strike WHO stays as a display and the word goes.
- SENSEX: fewer than 6 non-MIXED windows a day → too thin to read; its screen shows NIFTY's flow (§1q) with SENSEX's
  own OI, as today.
- Any version of this that shows a %, a probability, or an entry button.

### D8. Pre-register before Monday (counts only, 20 sessions, n ≥ 15 per side before anyone reads them)
1. TOOT-by-COVER vs TOOT-by-DUMP: 30-min continuation counts (b-1).
2. FUEL word said (2 closes) → fut at +15 / +30 with the lean, by day type (§1o).
3. SELL / BUY fade arms stamped LEGAL vs ILLEGAL by `cap_who` / `floor_who`: MAE distributions (D5).
4. PIN on expiry afternoons: held / left counts (D2).
5. SHAKE: COVER followed by WRITE on the same side in the next window → fut at +15 (b-5).

---

## (e) The UI/UX design — `mockup.html`

**What it is:** one light screen, answer first. The ONE word big (`▲ UP · writers`), the plain-English sentence under it
(`cap 23,700s: writers covering −24.1L · floor 23,650s: writers pressing +9.2L`), the two Hinglish chips with their
numbers (`calls bhaag rahe −24.1L` · `puts likh rahe +9.2L`), the since-time, and Jarvis's word beside it in grey
for comparison. One line of numbers: fut (f), spot (s), basis, VIX and its change since open, futures OI since open
with its quadrant word. Then the ladder, and a right column.

**The ladder (left, the thing she reads in 3 seconds):** 13 strikes around ATM, highest on top, calls on the left,
puts on the right, the strike in the middle with both OIs in lakh. Each side is a bar = the wall now (OI). The last
3 minutes are drawn ON the bar at its outer tip: a solid dark segment growing outward = writers pressing (`likh rahe
+19L`, with a small arrow pushing into the wall); a hatched segment = buyers lifting while writers post (`kharid
rahe`); a dashed hollow box just beyond the tip = what writers covered (`bhaag rahe −24L`, the wall visibly shrank,
and the row flashes once when it happens within two steps of spot — the attack); a grey dashed box = option longs
leaving (`nikal rahe`). `BADA 8.8k lots` on a row whose biggest price cell crossed the floor; `ITM` on walls behind
spot. The spot line moves between rows; the fut number rides on it. No price candles, no premium candles: she has
those. Motion only where it means something: walls grow, shrink, get hit, and spot crosses them.

**The right column:** (1) *pichle 30 min* — the last ten 3-min closes as word cells with the fut change in each
(the sequence, which a single-minute view cannot give); (2) *pushes → the wall's answer in option flow* — the
handshake's TOOT / TIKI / NAHI beside what the strike's own flow said (`23,700 CE bhaag rahe −12.5L`), the G5
answer; (3) *phanse hue* — who is under water by 25 % with OI built today (`23,700 CE writers wrote ~29.6 → now
41.6 · phanse 29 % · fuel ▲ if they cover`); (4) what TapeMap said (Jarvis word changes, setups, flow lines) up to
this minute; (5) health: chain stale / ended (A214), Dext state, the thresholds in lots, "every number here is from
data up to HH:MM only".

**Replay:** NIFTY / SENSEX switch, ◀ ▶, play (one minute per 0.3 s), a slider over the day, ← → space. "What came
next" is OFF by default; on, it adds a dashed grey `+15 min: +35f (hindsight)` beside the word and `+15` on pushes —
hindsight is never drawn in the same ink as the read. Opens at 11:48, the first writers' break with the push.

**Why this and not a heat-map:** a map of the whole day is for the evening; in the session she needs the state NOW,
at the strikes, in words with numbers, and the last half hour as a sequence. A 13-row ladder is what an order-flow
trader already reads (depth, footprint), so the shape costs her nothing to learn; the only new vocabulary is four
Hinglish words she already uses in the stream (`likh rahe`, `bhaag rahe`, `kharid rahe`, `nikal rahe`).

**Clean-room note:** my first `sed` of the README over-ran into lines 44–66 ("How to read the Battlefield") before I
could stop it; I did not open any mockup, replay or `map.html`, and the ladder-at-one-minute design above is
deliberately the opposite shape of a strikes × time grid. Declared in NOTES.md.

**Verified:** `node --check` on the page script passes; opened in the browser pane at 1380 px, stepped, played,
switched to SENSEX, toggled hindsight, scrubbed to 15:27 (reads `CAN'T SEE OI · chain ended 14:59 (A214) · flow
only`): zero console messages. Standalone, 953 KB, no external file, scripts in an IIFE, no global named `top`.

**Not done / not sure:** the play speed, the 13-strike height and whether the chips should also carry lots (they carry
lakh) are my guesses; the SENSEX page reads SENSEX's own flow, which is a study view, not her §1q screen.

---

## (f) Five questions only she can answer

1. **SENSEX's own option flow:** on 3 Nov it printed the same turns as NIFTY's within one 5-min window at 1/65 the
   volume. Do you want it as a piece beside NIFTY's flow on the SENSEX screen (a §1q change, your signature), or
   kept as a study view only?
2. **The first-hour word:** before 10:00, may OPENING show `TREND ▲ forming since 09:26 · writers 3/3` when the leg
   already qualifies (no arrow announced, the candidate shown), or does "nothing is announced before 10:00" stay?
3. **TOOT by DUMP:** when a wall's OI falls because buyers left (not writers running), should the push still say
   TOOT (with `kharidar nikal rahe`), or a new word (`TOOT?`), or NAHI?
4. **PIN on expiry afternoons:** is `PIN 23,700–23,750s` a word you want on the card and on Telegram, and from what
   time (13:00 is my guess)?
5. **The fade gate's flow clause (D5):** register it now beside §1d as a stamp (never suppressing a row), or wait
   for 20 forward sessions of the OPTIONS line first?

---
---

# Round 2 (same evening, after the coordinator's six attacks)

Every correction below names the line it fixes. Nothing above was rewritten. `study.py`'s aligned print was off by one
minute from her grid (it printed bars `hh:mm+1 … hh:mm+3` and labelled them `hh:mm–hh:mm+3`); fixed in `main()` (bars
now `09:15–09:17`, closing at the end of 09:17, exactly Jarvis's `(m − 555) % 3 == 2`). **The export, `day.json`, both
mockups and every count in (b)-1/2/3/7 used the rolling windows at her closes and are unaffected. Sections (a)-2, (a)-6,
(b)-4, (b)-5, (b)-6, (c)'s row labels and D3 were affected and are corrected here.**

## R2.1 The README comparison ("The reads behind it", read after (c) was written)

Agree, minute-true:
- 09:15–09:50 put writers at every strike, ITM call writers covering (mine: FLOOR WRITE +155L at the 09:20 close,
  23,600 CE COVER −19L at 09:26).
- 10:25–10:35: 23,600 CE OI down with buys, put writers chasing up (mine: 10:32 floor WRITE +36.9L, 10:35 cap COVER
  −26.8L), then "the trap": sellers took over, put buyers in (mine: 10:38 cap WRITE +30.7L d−110L, floor BUY +14.8L).
- 11:00 "failed break", 23,650 PE writers covered (mine: 11:05 close floor COVER −24.3L d+52L, raw FLOOR BREAKING).
  **I under-read this in (c)**: my row "11:03–11:09" called the floor DUMP; on her grid the 11:05 close was COVER −24L
  (writers), the 11:08 close MIXED. The README is right.
- 11:30 trapped put buyers (mine: 11:33–11:36 floor DUMP, delta −181L).
- 11:59 "my wrong call … the order flow showed sellers": the same read, independently (mine: 11:59 close cap DUMP −31L
  d−60L; the 11:55 push was TOOT by OI, DUMP by flow).
- 13:18 the real break: 23,700 CE OI down with buyers lifting, 23,700 PE writers piling in (mine: 13:17 close 23,700 CE
  COVER −46L [−66.6L over 13:16–13:18], 23,700 PE WRITE +17.3L [+38.6L]).
- 14:44 the pin fight at 23,700 (mine: 14:39–14:42 23,700 CE WRITE +19.7L, 23,700 PE WRITE +26.2L).
- "A WHO tool, not a timer" (the 9-day put check) — (b)-4 says the same from 3 Nov.

Disagree, and why:
1. **"13:55–14:19 … call writers came back to 23700 (+31L)" as the cap.** On her grid from 13:20 the pressing was at
   23,750–23,800 CE (13:20 cap WRITE +22.5L d−83L; 13:26 +8.4L; 14:11 +13.3L; 14:17 +12.3L d−193L) while 23,700 PE was
   written +24L (13:38) — 23,700 was the floor and the pin, 23,750–23,800 the lid. Same market, different naming; mine
   gives the seller two strikes to sell, theirs one.
2. **"Read the flow first and OI second."** On 3 Nov the aggressor is ~11 % of volume at the median and its sign flips
   minute to minute; the OI change says something happened, the delta says who. Neither first: the label needs both,
   and (R2.3) a third of per-strike labels move when the OI window shifts one minute.
3. **"Biggest prints at the extreme followed by a flip = trapped traders"** is read after the flip. Causal version: a
   BADA cell at a new extreme is a chip, the trap is confirmed by the next close's DUMP (11:59, 14:20 on her grid).
4. **"23600 CE buyers +140L at the open."** OI 134L → 235L by 10:12 is [M]; the aggressor in my 3-min windows at the
   09:20 / 09:23 closes was MIXED (+27L / +22L with |delta| under a fifth of the change). Buyers lifted, writers posted:
   OI built, no one pressed. The README reads a longer block; mine reads 3 min.
5. **The per-premium wall ("the 80 wall on the 23600 CE", prints absorbed at 79.7–80.8).** This is a footprint-level
   read my 3-min WHO does not make and my ladder does not draw. A real gap in mine, not in theirs: effort at one
   premium is the option's own "absorption". It belongs as a chip on the strike row (`80 wall · 5 prints absorbed`),
   computed from Dext's per-price cells, not as a new panel.
6. 2 Nov's "the options moved one block before the futures did" (12:30): n = 1, not checked here.

## R2.2 Timing audit of every "would have" (her grid; a close at hh:mm = minutes hh:mm−2 … hh:mm, knowable at its end)

| claim | the closes that carry it | verdict | fix |
|---|---|---|---|
| (a)-2 "at 10:11 and 11:08 the flow pieces would have read WITH, turning WATCH into HOLD" | **10:11 close: cap WRITE +6.7L d−43.5L, floor QUIET → LID (AGAINST)**; the ITM covering is at the **10:14** close (cap BUY +6.5L d+44.9L, floor WRITE +6.5L d−105L: raw UP FUEL), held from 10:17. **11:08 close: cap WRITE +28.6L → LID (AGAINST)**; UP FUEL held again at 11:20. | **WRONG.** The flow agreed with both WATCHes at the minute they were said. With the flow pieces WITH from 10:14, the count is W2 A5: still WATCH by the pause rule. | (a)-2 is withdrawn as a word change; it stays as `who` and the sentence. Ranking below. |
| (a)-1 "that line was true from 09:27" | Jarvis's own count W4 A1 at 09:26 (leg "fuelled 09:26", 2.3σ); flow 09:26 close UP FUEL (cap BUY +30L d+125L, floor WRITE +92L d−102L) | knowable at 09:26; the count fell to W1 A1 by 09:38 | stands, as "09:26–09:37" |
| (a)-6 "the 09:45 and 10:45 SELLs … the flow said the calls were being bought" | 09:44 close cap MIXED +35.6L, floor WRITE; 09:47 cap BUY +40.8L d+48.7L. **10:44 close cap WRITE +10.0L d−13.6L (!), 10:41 BUY +12L, 10:47 COVER −4.4L** | 09:45: calls lifted (BUY) at 09:47, MIXED at 09:44 — "being bought" holds one close late. **10:45: the 10:44 close was cap WRITE** — the flow did NOT say "bought"; (b)-3 placed it under "QUIET" from the off-by-one print. | (a)-6 and (b)-3 corrected: 10:45 moves to the cap-WRITE group → cap WRITE at the alert **5** (12:15 SX, 13:45, 13:55 SX, 14:05 SX, **10:45**), lower at +30: 3 of 5 (10:45 was −26 at +30 after +15 against); not-WRITE **2** (09:45, 10:25 SX): 0 of 2. n = 7, inconclusive. |
| D3 "the veto holds TREND ▲ 13:20 at HOLD" | 13:14 LID (cap WRITE +5.2L) · **13:17 cap COVER −20.1L (WITH)** · **13:20 cap WRITE +22.5L d−83.4L (AGAINST)** — the bar 13:18–13:20, complete at the end of 13:20, the same data Jarvis's 13:20 row used (shown 13:21:28) · **13:23 cap MIXED +45.8L d+4.6L (not AGAINST)** · 13:26 WRITE +8.4L (AGAINST) | **WRONG as written.** A 2-consecutive-close veto never fires in 13:17–13:29 (13:23 breaks the pair). A 1-close veto would have held 13:20 at HOLD — and also 10:38 (cap WRITE +30.7L d−110L, one close after TREND 10:35) — but a 1-close veto is the flicker the two-close rule exists to stop. | D3 corrected: **no word change now**; both forms logged forward (R2.6). "−66.6L at 13:15→13:18" was the off-by-one bar; on her grid 23,700 CE −46.0L at the 13:17 close. |
| (c) "14:15–14:18 CAP DUMP −62.8L … DOWN FUEL → low 23,723 at 14:25" | 14:17 close cap WRITE +12.3L d−193L (LID) · **14:20 close cap DUMP −60.1L, floor WRITE +26.6L → raw UP BUYERS** · 14:23 DOWN FUEL (floor COVER −10.9L) · low 14:25 | the DUMP is knowable at 14:20; the DOWN FUEL word at 14:23, two minutes before the low: **coincident, not leading** | (c) row corrected |
| (c) 11:45–11:48 / 12:09–12:12 / 13:15–13:18 | 11:47 cap COVER −24.2L d+91.8L · 12:11 floor COVER −45.9L, cap DUMP −40.5L · 13:17 cap COVER −20.1L, floor DUMP −41.1L | all knowable at the close named; the (c) labels are one minute late | labels only |
| (b)-1 / D4 push `who` | the rolling window ending at the handshake's answer minute `am` (data ≤ am), the same minute Jarvis's answer used | causal; not on the 3-min grid (a per-push read) | stands |
| (c) 12:02 "lean turns ▼ 2 min before the flush" | 11:59 raw DOWN BUYERS, 12:02 raw DOWN BUYERS → held ▼ at 12:02; 12:05 raw UP FUEL; 12:08 DOWN FUEL; flush 12:09–12:11 | knowable at 12:02; contested at 12:05 | stands, with the 12:05 close named |

**(b)-4, (b)-5, (b)-6 recounted on her grid (closes only):**
- (b)-4 FLOOR WRITE at ≥ 2 consecutive closes: 7 episodes; fut +15 from the second close: 09:29 −16, 09:47 −22, 09:59
  −28, 10:08 +20, 10:17 +30 (the 8-close run 10:14–10:35), 11:26 +1, 11:41 +33. 3 of 7 ≥ +20, 3 negative. Not a timer.
- (b)-5 FLOOR COVER ≥ 10L at a close: 8 (11:05 −24L, 12:11 −46L, 13:11 −14L, 13:53 −14L, 14:23 −11L, 14:26 −27L,
  14:44 −25L, 14:59 −16L). **The next close was WRITE on the floor in 0 of 8** (MIXED, QUIET, COVER, OI?) — the
  "+53L rewrite in the next window" I reported sat across her 12:14 / 12:17 bars (12:13–12:15). **The "writers came
  back" tell is withdrawn as stated.** What holds: fut at +15 was higher in 6 of 8 (+23, +12, +19, −4, +30, +53, −26,
  +12); on an expiry afternoon most of this covering was OTM put writers booking (23,500 / 23,550 at 14:26–14:59).
- (b)-6 CAP DUMP ≥ 25L at a close: 5 — 11:32 (**+61** at +15, at the low), 11:59 (−31, the top), 12:11 (+12), 14:20
  (+11, min −20), 14:59 (+12). **1 of 5 was a top. Withdrawn as a top sign;** stays as `who` (buyers leaving).

**Ranking of (a)'s improvements, corrected:** 1 the first-hour candidate (09:26) · 2 PIN on expiry afternoons · 3 `who`
on every push (TOOT by DUMP, 3 of 3 retraced) · 4 age the word on the face (A214) · 5 G13 SENSEX · 6 the fade stamp
(R2.2 row 3: 3 of 5 vs 0 of 2) · 7 the flow pieces as sentence and `who` only — **no veto, no vote, until the forward
log says otherwise.**

## R2.3 OI cadence (the quant check) [M, `chain_NIFTY_2026-11-03.jsonl`, ATM ±3]

- The chain is polled every 11 s (median; p90 11 s; one 695-s hole at 14:26). **The OI value changes every 63 s
  (median; p90 68 s)** on every one of the 14 contracts; 2 distinct OI values per minute (median), 3 at most; a minute
  with no change in 24–29 of 319. The exchange publishes OI about once a minute, so a 3-min window's OI change can carry
  the trades of the minute before it.
- Test: the same WHO with the OI window pushed one minute (equivalently the delta window pulled one minute, both
  knowable at the close): **of 1,498 strike-windows at ATM ±3, 396 labels change (26 %)**, mostly across the QUIET floor
  (DUMP↔QUIET 82, WRITE↔QUIET 93, BUY↔QUIET 57, COVER↔QUIET 47); sign flips WRITE↔DUMP 39, BUY↔COVER 12.
- At the six moments: **the group words and the headline strikes do not move** — 11:47 (23,650 CE COVER −11 / −24L,
  23,700 CE COVER −10 / −12L, 23,700 PE WRITE +4 / +11L), 11:56 (23,650 CE COVER, 23,700 PE WRITE), 12:11 (23,600 /
  23,650 / 23,700 PE COVER −24 / −34 / −48L vs −45 / −45 / −58L), 13:17 (23,700 CE COVER −46 / −67L, 23,700 PE WRITE
  +17 / +39L). The margins move: 10:11 (5 of 9 strike labels change, all near the floor), 14:20 (23,700 PE DUMP −53L vs
  −9L: the 14:18–14:20 trades' OI landed in the next minute).
- **Rule change (applied in `study.py` and `mockup-v2`):** a per-strike label is **FIRM** only when it is the same under
  both alignments (delta over the bar, and delta over the bar one minute earlier, against the bar's OI); **624 of 972
  non-QUIET strike labels at closes are firm.** Non-firm labels are drawn faint with a "?" and never carry a chip. The
  group words (cap / floor) stay on the aligned window because their sums were stable at every key moment. The window
  stays 3 min: a 4-min OI span would hide her bar.

## R2.4 Aggressor validity (the D1 kill check, attempted)

The chain carries `bid / ask / ltp` per strike every 11 s. Quote rule per snapshot whose ltp changed (ltp ≥ ask → buy,
≤ bid → sell, else by mid), majority per minute, against the sign of Dext's minute delta, ATM ±2, 3 Nov: **agree 1,112 ·
disagree 885 · undecided 1,261** (3,258 minutes). **The data cannot support the check:** one sampled trade per 11 s
against hundreds of trades a minute, with 39 % of minutes undecided, is not a tick rule; 56 : 44 on that proxy says
nothing either way. The kill check needs option ticks (the Upstox option-tick backup in the README's "Open"). Until
then the WHO is Dext's classification, said as such on the health line.

## R2.5 Design answers (as the UI/UX designer)

**(i) What she does with "▲ UP · writers".** Added under the word, in her EXPRESSION's terms (§1h: buy the option in the
direction, or sell the other side at the ATM strike), two cells, never an order and never the registered word:
`for a buyer: CE · fuel = call writers covering 23,700s` · `for a seller: sell PE · put writers pressing 23,650s behind
you`. The whole table: UP FUEL → CE / sell PE with the floor behind; LID BREAKING → CE / no fresh sale, wait for the
floor; FLOOR UP → no fuel yet / sell PE, writers with you; UP BUYERS → CE, buyers chasing (fades more) / sell PE only
with a wall behind; DOWN FUEL and LID mirror; PIN → no trade / the seller's afternoon, both sides writing k₁–k₂;
SQUEEZE → direction not clear / **refused: never sell into a squeeze**; BUYERS OUT → no trade / nothing to defend;
OI? → could not check / **refused: a writer does not sell a wall she cannot see** (her R3). The registered EXPRESSION
word (BUY / LEANS / EITHER / SELL / STAND ASIDE) is the engine's and is not imitated here.

**(ii) The Float-sized version** (`Float.tsx` is W = 440; the button "Float 440" in mockup-v2 renders it). Survives:
the word and since; the buyer / seller cells; the two chips; fut / spot / basis; a 5-strike ladder (ATM ±2) at 30 px
rows with labels only on moved, firm rows; the last-10-closes strip; one health line. Goes: pushes, phanse hue, the
alerts log, VIX, fut OI, the legend — the Float IS the message window, so the OPTIONS line and TOOT? / PIN / SHAKE go
into the stream as lines (D6), not as panels.

**(iii) The cut list, applied in v2:** no per-row "no footprint" / "OI?" (one health line says it); labels only on rows
that moved (WRITE / BUY / COVER / DUMP ≥ the floor), faint with "?" when not firm; BADA only on a moved row, written
`BADA 10k`; 13 strikes → 9 (ATM ±4) on the page, 5 on the Float; minimum text 12 px everywhere (labels, cells, strike
OIs, spot chip, legend). What earns its place live: the word, the two cells, the chips, the bars with their last-3-min
tip, the spot line, the strip. Everything else is evening.

**(iv) One rule: no % on this screen.** "phanse 29 %" / "doobe 49 %" → `wrote ~29.6 → now 41.6 · phanse 12.0 against
them` / `paid ~49.8 → now 25.2 · doobe 24.6 against them` (premium points). Applied in v2; the only remaining "%"
in the folder is in this report's measurements.

**(v) 0DTE or the next expiry on an expiry afternoon.** What 3 Nov's data can say [M]: the bridge asked only the 03 NOV
contracts; the one 09 NOV footprint on disk (23,650 CE, a chart open in Dext) runs 09:15–11:29 only, at **1 % of the
0DTE's volume** in every half hour it covers (16.5L vs 1,621L in the first half hour); the chain recorder also followed
the 03 NOV expiry all day, so the 09 NOV OI was not recorded either. So the afternoon cannot be argued from 3 Nov's
data, only from what the 0DTE showed: from 13:30 both sides wrote 23,700–23,750 (PIN), which is the seller's read and
a buyer's no-trade. Design: **follow the 0DTE to 13:00; from 13:00 show the 0DTE as one PIN line (the pair and its
writers) and switch the ladder to the next weekly for direction.** That needs the bridge to ask the next expiry's ATM
±5 from 13:00 (about 22 more requests a minute) and the chain recorder to carry a second expiry — both are her calls;
without them the ladder stays on the 0DTE and says so.

## R2.6 What changed in (d)

- D3 → **no veto, no vote now.** The flow pieces enter the count as "?" with a sentence (`cap: writers pressing
  +22.5L`, `floor: buyers leaving −41L`) and `who` on pushes; the forward log (D6) records, per close, what a 1-close
  veto and a 2-close veto would have said. Pre-registered (D8-6): over 20 sessions, count the TREND stamps each form
  would have held at HOLD and fut at +15 / +30 after them; a form that holds more losers than winners by count, n ≥ 15,
  earns a word; otherwise it stays a sentence.
- D1 adds FIRM (R2.3) and the health line names Dext as the aggressor's source until ticks exist (R2.4).
- (b)-5's SHAKE rule is withdrawn (0 of 8 on her grid); D8-5 becomes "FLOOR / CAP COVER ≥ 10L at a close → fut at +15,
  by whether the next close is COVER again".
- 5(v) adds two asks for her: the second expiry in the bridge and the chain recorder from 13:00 on expiry days.

## R2.7 Files

`mockup-v2.html` (built from `mockup-v2.tpl.html` + the same `day.json`, now with `firm`), `mockup.html` kept as v1
(rebuilt on the new `day.json`, unchanged in look). `study.py`: `window_lag`, `firm` in the export, the aligned print
on her grid. `make_mockup.py` takes the template name.

---
---

# Round 3 (2 Nov): the second day

Same method, same thresholds, her 3-min grid, data ≤ each close. **This is a recorded day looked at after the ideas were
formed on 3 Nov. It is a second look, not the pre-registered forward test.** The two days are two columns and are never
pooled. Script: `secondlook.py` (runs both days from `days.json`); the mockup-v2 day switch shows 2 Nov minute by minute.

## R3.1 2 Nov in brief

**Shape [M]:** NIFTY fut 23,245 → 23,400 in the first 30 min (short covering, −3,350 lots), then a range 23,360–23,426
to 12:30 (the high 23,426 at 10:45–10:59), a down-leg 12:45–13:14 to 23,260 (spot low 23,214.6 at 13:15), a base
23,250–23,320 to 14:15, an up-leg to 23,385 (14:44) and 23,415 at the close (spot high 23,440.8 at 15:29). Fut OI
−2,460 lots on the day. VIX 15.32 → 15.90 at 13:39 (the low) → 15.43. 1 DTE. No trade marked. The atlas's "rotation
day": a first-hour leg that went nowhere, a late afternoon leg.

**Jarvis (NIFTY, 23 changes, 2 lean flips, PALAT? 5 — its own sheet says 2 came true):**

| said | word | fut | +30 / best / worst | verdict |
|---|---|---|---|---|
| 09:17 | OPENING ▲ | 23,314 | +92 / +93 / 0 | lean right; silent by rule — and on this day silence was right |
| 10:00 | WATCH ▲ (1/2) | 23,382 | +18 / +22 / −20 | the range |
| 10:47 | HOLD ▲ (3/0) | 23,405 | −13 / +20 / −15 | at the range top |
| 11:44 | PALAT? ▲ (0/4) | 23,367 | +32 / +41 / −17 | cried wolf (the 12:00 bounce) |
| 12:11 | HOLD ▲ (6/0) | 23,408 | −41 / +15 / −55 | **wrong: HOLD with 6/0 at the range top, 9 min before the down-leg** |
| 12:35 | PALAT? ▲ (2/3) | 23,378 | −48 / +2 / −50 | right |
| 12:55 | PALAT ▼ | 23,335 | −42 / +25 / −70 | right, 91 pts off the top |
| 13:08 | TREND ▼ (7/0) | 23,310 | −47 / +5 / −47 | right; the leg was already 119 pts (the atlas's "called late") and the low came 6 min later |
| 13:20 | PALAT? ▼ (2/2) | 23,315 | −36 / 0 / −59 | wrong (the leg went on) |
| 13:50 | WATCH ▼ (1/3) | 23,279 | +56 / +56 / 0 | the low; right as a warning |
| 14:02 | HOLD ▼ (1/1) | 23,290 | +56 / +56 / 0 | **wrong: HOLD ▼ at the low** |
| 14:21 | PALAT ▲ | 23,344 | +22 / +41 / −21 | right, 93 pts off the low |
| 14:35 | TREND ▲ (4/0) | 23,355 | +2 / +30 / 0 | late: +30 was all there was before 15:00 |

SENSEX: 31 changes, 6 lean flips, PALAT? 6 ("came true 6×" by its sheet) — on a range-then-drop-then-rally day the
SENSEX lean flipped every 25 minutes. The pattern of 3 Nov repeats in the mirror: both lean flips were right in
direction and ~90 pts late; the two HOLDs at extremes (12:11 top, 14:02 low) were the wrong words.

**Her other voices:** SELL fades at the open drive's top (NIFTY 10:00 / 10:05, SENSEX 09:50 / 10:00 / 10:05): 2 of 5
were lower at +30 (SENSEX 09:50 −100; the rest +18 / +20 / +51 / +108). BUY fades at the 13:25–13:55 low (NIFTY 13:25
4/4, 13:45, 13:55; SENSEX 13:25, 13:45, 13:50 FADE-D): 4 of 6 higher at +30 (13:25's retested to 23,251 first, −13 / −15).

**Option flow × OI at the key moments (her closes; "next" is hindsight):**

| close | the flow said | Jarvis | next |
|---|---|---|---|
| 09:20 | FLOOR WRITE +67.9L (d−45.9L), CAP BUY +59.3L: **UP FUEL** — the same open-drive signature as 3 Nov | OPENING ▲ | +66 by 09:47; the 09:35 TOOT at 23,300 CE was COVER −31L |
| 09:53–09:59 | CAP WRITE ×3 (d−52L, −19L, −14L) + FLOOR BUY: **DOWN FUEL at 09:59**, fut 23,392 | OPENING ▲ | the drive's top (23,416); then a range, not a drop: +5 at +15 |
| 10:56–10:59 | cap QUIET, FLOOR BUY → DOWN BUYERS; the 10:54 push (+618 lots) was TOOT by OI, **DUMP** by flow at 23,400 CE | HOLD ▲ | the day's high; −29 at +30 |
| 11:47–11:50 | CAP WRITE +13L (d−21L) + FLOOR COVER −10L / −6L: DOWN FUEL at 11:50 (23,358) | PALAT? ▲ | **taken back in 12 min**: 11:53 cap COVER, 12:02 UP BUYERS, the bounce to 23,420 |
| **12:53** | CAP WRITE +10.7L (d−38.7L) + FLOOR BUY +11.1L (d+25.7L): **DOWN FUEL held at 12:53**, fut 23,360 | PALAT? ▲ (PALAT ▼ at 12:55, TREND ▼ 13:08) | **2 min before PALAT, 15 before TREND ▼**: 23,360 → 23,267 by 13:14 (−93) |
| 12:56 | CAP DUMP −24.7L (d−64L) + **FLOOR COVER −42.1L (d+24.9L: put writers buying back)** — the 12:54 ▼ push TOOT by COVER at 23,300 PE | PALAT ▼ | −50 at +15 |
| 13:05 / 13:11 | FLOOR COVER −21.8L, then **−42.5L (d+55.8L)** with CAP DUMP −15.9L (d−71L); the 13:09 push −383 lots: 23,200 PE COVER −40.4L | TREND ▼ 13:08 | the low 23,260 at 13:14 |
| 13:14 → 13:20 | 13:14 CAP WRITE +26.1L (d−65L) + floor COVER −15L (DOWN FUEL **at the low**); **13:17 FLOOR WRITE +12.8L (d−48L): the put writers came back**; 13:20 CAP BUY +22.9L (d+82L) + floor DUMP: UP BUYERS held | TREND ▼ → PALAT? ▼ 13:20 | 23,267 → 23,315; the ZONE BUY 13:25 (4/4) came 8 min after the floor's return; the retest to 23,251 at 13:41 |
| 13:35–13:38 | CAP WRITE ×2 (d−25L, −27L), FLOOR WRITE +3.4L: LID / PIN at the retest | HOLD ▼ | 23,263 low 13:38, then 13:44 cap BUY, 13:47 UP FUEL (23,290): +0 at +15 (chop) |
| 14:32–14:44 | 14:32 CAP COVER −10.2L (d+33L); 14:35 FLOOR WRITE; **14:38 CAP COVER −33.4L (d+40L): UP FUEL held**, fut 23,375; 14:44 CAP COVER −27.5L (d+62L) | TREND ▲ 14:35 (3 min earlier this time) | 23,385 by 14:44, flat to 15:00, 23,411 by 15:29 on four more CAP COVER closes |

**SENSEX's own flow (3 DTE)** printed the same turns within a window (not detailed; the mockup shows it).

## R3.2 The second look (two columns, never pooled; "held" = the 3 Nov reading repeated)

| finding | 2 Nov (second look) | 3 Nov (where it was formed) | verdict |
|---|---|---|---|
| TOOT by COVER vs TOOT by DUMP (30-min continuation with the push) | COVER 8 rows, **2** with (09:35 +24, 13:03 +41; 09:41 +7 flat; 12:09, 12:33, 12:54, 13:09, 14:36 against); DUMP 4 rows, **2** with (11:51 ▼ −50, 13:38 ▼ −34; 10:54 ▲ −29, 12:19 ▲ −47 against) | COVER 4, 2 with; DUMP 3, **1** with (**correction to Round 1/2: 14:24 ▼ −14 was WITH its ▼ push; "0 of 3" was my sign error**) | **did not hold.** `who` stays a fact on the push line; the TOOT? word is dropped |
| NAHI + WRITE vs NAHI + BUY | 1 row each (13:42 ▼ WRITE −28 with; 09:45 ▲ BUY −5) | 4 / 3 | **not testable** |
| fade alerts: the wall WRITE at the last close ≤ alert | WRITE **4 rows, 1** the fade's way at +30 (NI 10:00 SELL +18, NI 09:55 SELL +5, SE 10:00 SELL +51, SE 13:55 BUY +75 ✓); not WRITE **9 rows, 5** the fade's way (SE 09:50 SELL −100 ✓, 13:45 / 13:50 / 13:55 BUYs ✓, 13:25 BUYs ✗, 10:05 SELLs ✗) | WRITE 4 rows, 4 the fade's way; not WRITE 3 rows, 0 (**the Round 2 count "3 of 5 / 0 of 2" used the alert minute's rolling window; at the last close ≤ alert it is 4 of 4 / 0 of 3**) | **did not hold.** D5 stays a log stamp, never an alert |
| the first-hour candidate (leg qualifies before 10:00 AND the writers' count unanimous) | leg qualified 09:36 (117 pts, 2.3σ) with **W2 A2 — not unanimous: the line would have stayed silent.** A bare "qualified" rule would have said TREND ▲ 09:36 at 23,365 → PALAT 12:55 at 23,335 (−30; best +61 at 10:45) | qualified 09:26 at W4 A1; shown; +125 to 15:20 | **the condition did its job (n = 1 + 1).** Keep W ≥ 3 and A ≤ 1 at the qualifying minute [I] |
| PIN (expiry afternoon, 2 closes after 13:00) | 1 DTE: **not applicable.** Raw PIN closes 4 (09:32, 09:53, 11:38, 13:38), none consecutive, 2 in the open drive (+66 after 09:32) | 9 raw PIN closes; 13:44 in the afternoon | **not testable**; the "expiry day, after 13:00" fence stands (a morning PIN is not a pin) |
| FLOOR COVER ≥ 10L at a close → the next close | 4: 12:56 −42L → QUIET (+15: **−63**); 13:05 −22L → DUMP (−15); 13:11 −42L → COVER (0); 13:14 −15L → **WRITE (+20, the low)** | 8, next close never WRITE; +15 higher in 6 | **the mirror holds in a real down-leg** (3 of 4 followed by lower or flat); "writers return = the pause" is 1 of 1 here — **not testable** |
| CAP COVER ≥ 10L at a close → the next close | 10: 12:17 −13L → **WRITE → −41** (the lid re-formed at the top); 14:38 −33L → WRITE → +3; 15:08 / 15:20 / 15:23 / 15:26 → COVER (the close rally) | 5, next WRITE ×4 | no pattern either day |
| flow lean vs Jarvis lean | same ▲ 62 · same ▼ 14 · flow ▲ / J ▼ 15 · flow ▼ / J ▲ 29 · flat 5; **flow flips 16, Jarvis 2** | 56 · 0 · 0 · 42 · 27; flips 8 vs 0 | **held:** the flow's lean is the fast, noisy one (8× Jarvis's flips both days); it led in the one real leg (12:53) and flipped in the range |
| OI cadence · FIRM share | poll 11 s; **OI changes every 63 s** (p90 64 s); FIRM **574 of 899** | 11 s; 63 s (p90 68); 624 of 972 | **held** |
| held-word changes | 46 (lean flips 16) | 48 (8) | the word changes at most closes on both days: it is a STATE line, not a word she acts on |

## R3.3 New on 2 Nov: the mirror in a real down-leg

- **DOWN FUEL behaves as designed where it matters:** 12:53 (cap WRITE, puts bid) → 12:56 (cap DUMP, **floor COVER with
  buyers lifting puts**, d+24.9L) → 13:11 (floor COVER −42.5L, d+55.8L) → the low. Put writers running with buyers
  lifting the puts is the mirror of 3 Nov's 13:17 (call writers covering with calls lifted). The floor's writers
  returning (13:17 FLOOR WRITE +12.8L, d−48L) marked the low; the bounce printed as CAP BUY (calls lifted), not as
  put covering — the same asymmetry as 3 Nov's dips (buyers leave, writers do not run).
- **DOWN FUEL in a range is as wrong as UP FUEL in a range:** of 9 DOWN FUEL closes, 3 came in the morning range
  (09:59 +5, 10:20 **+31**, 11:50 +7) and 5 in the leg (−22, −14, −50, −15, −15). 3 Nov's UP FUEL in the 09:30–11:00
  range: −22, −28, −42. The word is a WHO, not a timer, in both directions.
- **The lead, when it exists, is 2–15 minutes** (12:53 vs PALAT 12:55 / TREND 13:08; 14:38 vs TREND 14:35 is the other
  way). Two legs, two days: n = 3.
- **LID BREAKING at a range top is a trap:** 12:17 CAP COVER −13L → next close WRITE → −41. On 3 Nov 11:56 LID
  BREAKING → −48. n = 2, both at a top that had already printed.
- **The 10:54 push** (+618 lots, the day's biggest ▲): TOOT by OI, DUMP by flow at 23,400 CE, the day's high. Same shape
  as 3 Nov's 11:55 / 13:41. Across both days, TOOT-by-DUMP ▲ pushes at a high: 4 rows, all 4 lower at +30 (10:54,
  12:19; 11:55, 13:41); the ▼ ones (11:51, 13:38; 14:24) went on. **A hypothesis for the forward log, not a rule:**
  the DUMP read may separate by direction (call longs leaving at a high), not by itself. n = 4 + 3.
- **The open drive's words flicker** on both days (PIN / UP FUEL / QUIET / LID inside 09:20–09:40): the first 25
  minutes' OI builds on both sides at once. The first-hour candidate should read Jarvis's count, not the flow's word.

## R3.4 Design consequences (applied where cheap)

- **Thresholds unchanged.** OI_MOVE 1.5L / 3 min, AGG_X 0.2, BIG 5L: the cadence (63 s) and the FIRM share (≈ 64 %)
  replicate, the group words at the leg turns are firm on both days.
- **Arrows only on FUEL words** (mockup-v2): UP FUEL / DOWN FUEL keep ▲ / ▼; LID, FLOOR RISING, CAP BREAKING, FLOOR
  BREAKING, BUYERS · calls, BUYERS · puts are WHO facts and are drawn flat. Reason: 2 Nov's 16 flow-lean flips were
  mostly BUYERS / LID words in the range; the forward log measures whether the FUEL-only lean flips less.
- **TOOT? dropped** as a word; `who` stays on the push line (R3.2 row 1).
- **D5 stays a stamp in the forward log, never an alert** (R3.2 row 3). Its two-day record is written here as two columns.
- **The first-hour line keeps the unanimity condition** (W ≥ 3, A ≤ 1 at the qualifying minute [I]); 2 Nov is the
  reason it exists.
- **held():** the first word is now said at a close, never mid-bar (the 09:18 "PIN" was a non-close window). Both
  exports rebuilt; 3 Nov's counts unchanged except the first 2 minutes.
- **mockup-v2** has a day switch (Mon 2 Nov | Tue 3 Nov), both indices, same page (2.3 MB, one file). v1 untouched.
- **Corrections to Round 1 / 2 carried here:** TOOT-by-DUMP on 3 Nov is 1 of 3 with the push, not 0 of 3 (14:24's
  sign); the fade count at the last close ≤ alert is 4 of 4 / 0 of 3, not 3 of 5 / 0 of 2.
- **For the forward log (D8), two rows added:** every COVER ≥ 10L at a close carries the next close's word on that
  side (the "writers return" tell, 1 of 1 so far); every TOOT carries `who` and the push's direction (R3.3's
  direction split).

---
---

# Round 4: pullback anatomy, the signal × option-flow matrix, one currency, writer gamma

NIFTY, 2 and 3 Nov, her 3-min grid, every read at a close uses data ≤ that close; "+15 / +30 / mfe / mae" are hindsight
and say so. Two days = two columns, never pooled. Script `round4.py` (output kept in `round4_out.txt`); it reuses
`docs/optflow/brainstorm/strike_bands.py` (A218) for the premium and index VWAP bands. No server touched.

## R4.A Pullback anatomy

**Source of the pullback list:** 2 Nov = Jarvis's own pause log (8 rows). 3 Nov has no pause file; I took the call log's
leg state (`state`) and started a pullback at the first HOLD / WATCH / PALAT? minute after a TREND minute (legs.py's own
rule, re-read from its output), 4 rows. Depth and duration are measured on the 1-min futures closes from the pause's
first minute until a new leg extreme (CONT) or Jarvis's lean flip (FAIL), capped at 60 min (UNRESOLVED). "ITM writers"
= the leg's own ITM options (an up-leg's calls below spot): C covering, D buyers leaving, W being written, B being bought.
"Implied 9-min" = R4.C's option-implied delta over the last three closes.

| day · start | leg | depth (share) · dur · outcome | defending side · attacked side (closes) | ITM writers | ATM premium vs its VWAP | implied 9-min · fut 9-min | VPIN pct |
|---|---|---|---|---|---|---|---|
| 2 Nov 09:46 ▲ | 164 | 52 (0.32) · 58 min · **CONT** (new high 10:45) | floor WRITE 8 · BUY 8 · cap BUY 6 / WRITE 5 | C 5 · B 7 · D 11 · W 3 | > VWAP 13 of 20 | +62,849 · +816 | p0.39 |
| 2 Nov 10:55 ▲ | 176 | 76 (0.43) · 60+ · **FAIL** (PALAT 12:55: the top) | floor BUY 4 · WRITE 4 · DUMP 5 · **COVER 2** · cap QUIET 7 / WRITE 5 | **W 8** · D 5 · B 4 | **< VWAP 10 of 20**, ≤ d2 1 | **−11,611 (against)** · +149 | **p0.13** |
| 2 Nov 12:56 ▼ | 99 | 33 (0.33) · 10 min · CONT | cap DUMP 2 / WRITE 1 · floor COVER 2 | C 6 | > VWAP 3 of 4 (the put) | −88,168 · −530 | p0.82 |
| 2 Nov 13:09 ▼ | 152 | 20 (0.13) · 5 min · CONT | cap WRITE 1 / DUMP 1 · floor COVER 2 | C 7 | ≥ u2 2 of 2 | −45,487 · −519 | p0.84 |
| 2 Nov 13:17 ▼ | 166 | 55 (0.33) · 22 min · CONT (new low 13:41) | **cap WRITE 5** · floor WRITE 3 / BUY 2 | D 8 · B 3 | > VWAP 6 of 8 | −132,216 · −601 | p0.83 |
| 2 Nov 14:39 ▲ | 124 | 15 (0.12) · 4 min · CONT | floor BUY 1 · cap WRITE 1 | D 1 · W 1 | < VWAP 1 of 1 | +192,243 · +641 | p0.73 |
| 2 Nov 14:50 ▲ | 139 | 33 (0.24) · 31 min · CONT | floor DUMP 6 · cap COVER 5 / DUMP 5 | D 10 · C 9 | > VWAP 6 of 11 | +13,506 · +249 | p0.45 |
| 3 Nov 10:36 ▲ | 182 | 53 (0.29) · 89 min to the new high 12:05 | floor WRITE 6 · BUY 4 · DUMP 4 · COVER 2 · cap BUY 9 / WRITE 6 | D 11 · B 9 · C 5 · W 5 | > VWAP 13 of 20 | +144,436 · +809 | p0.34 |
| 3 Nov 12:07 ▲ | 214 | 63 (0.30) · 93 min to the new high 13:40 (the 12:10 flush inside) | floor WRITE 6 · BUY 4 · DUMP 4 · cap WRITE 7 / BUY 8 | D 13 · **W 9** · B 5 · C 5 | > VWAP 12 of 20 | **−85,827 (against, the flush)** · +68 | p0.64 |
| 3 Nov 13:22 ▲ | 252 | 30 (0.12) · 13 min · CONT | floor DUMP 3 · cap WRITE 2 / BUY 2 | **C 7** · B 2 | ≥ u2 5 of 5 | +26,122 · +595 | p0.76 |
| 3 Nov 13:43 ▲ | 267 | 76 (0.28) · 60+ · **no new high (the PIN)** | floor WRITE 4 · DUMP 5 · COVER 4 · **cap WRITE 12 of 17** | **W 10** · D 6 | > VWAP 11 of 20 | +72,184 · +147 | p0.58 |

(2 Nov 09:43: 9 pts, 2 min, trivial, omitted.)

**What a healthy pullback looked like (CONT, 9 of 12 rows):** the defending writers kept writing (floor WRITE ≥ BUY
closes), the leg's **ITM writers were covering or ITM buyers leaving (C / D)**, the **option-implied delta stayed with
the leg**, and the **ATM option held above its own VWAP** in most closes (09:46: 13 of 20; 13:17 ▼: 6 of 8; 13:22: ≥ u2
5 of 5). Depth 0.12–0.33 of the leg; resolved in 4–31 min when speed was ≥ 3 pts/min at the first close.

**What the start of a reversal looked like (2 Nov 10:55, the only clean FAIL):** the leg's **ITM options being WRITTEN
against it (W 8 closes)**, the **option-implied 9-min delta against the leg (−11.6k) while the futures delta still read
with it (+149)**, the ATM call **below its VWAP in 10 of 20 closes**, floor COVER appearing (2), the lowest VPIN
percentile of the day (p0.13), speed 1.7 pts/min, effort 21 lots/pt. **The pin start (3 Nov 13:43) looked different
from a reversal:** implied delta still with the leg (+72k) but **cap WRITE in 12 of 17 closes and ITM calls WRITTEN
(W 10)** — writers pressing on both sides, no one running. Two kinds of "no new extreme": a reversal (implied delta
turns) and a pin (writers press both sides). n = 1 + 1.

**Against legs.py's pause read ("at a pause writers lag, k1 loading = continuation"):** "loading" is OI growing at k1
and has no side. On 2 Nov 09:46 the 23,350 CE loading (+10.1L / 9 min) was **BUY** (buyers lifting, writers posting)
and the leg continued; at 10:55 the 23,400 CE loading (+3.5L / 9 min) was **WRITE** (writers pressing) and the leg
failed. The aggressor turns one "alive" item into two: `k1 loading · kharidar` (alive) vs `k1 loading · likh rahe`
(risk). n = 2.

## R4.B The signal × option-flow matrix

| signal (rows on the two days) | what option flow adds | 2 Nov counts | 3 Nov counts | verdict |
|---|---|---|---|---|
| **1. Band rotation** (trigger_log zone3 arms, NIFTY; the wall's WHO at the last close ≤ arm; mae ≤ −30 = stopped) | the attacked wall's WHO; the ATM option's own band | SELL arms 9, all 09:24–09:51 with the index ≥ u2: stopped 6 of 9 — by wall: WRITE 2 of 2, BUY 3 of 4, MIXED 1 of 2, DUMP 0 of 1. BUY arms 3 (13:09–13:39): mfe ≥ 40 all 3 (wall COVER / DUMP / WRITE) | SELL arms 9: stopped 6 — by wall: WRITE 2 of 4 (09:33, 09:36 stopped; **13:15, 13:33 worked**), BUY 2 of 2, COVER 1 of 1, MIXED 1 of 1, DUMP 0 of 1 | **adds nothing at the open drive** (the first-25-min SELL arms stopped 7 of 8 across both days whatever the WHO); **in the afternoon wall WRITE 2 of 2 worked, COVER / BUY 0 of 2** (n = 4). The §1d gate pointed the wrong way at the open on both days: LEGAL arms stopped 6 of 6 (2 Nov) and 4 of 4 (3 Nov) |
| 1b. **A218's index-band finding** ("premium at u2+ with writers COVERING while the index sits at its band → stall; mid-band → continues"), re-read from its own touch table | — | at the band: 13:11 (23,150 / 23,200 / 23,250 PE COVER, index ≤ d2) → 0 / −15 **stalled**; mid-band: 12:56 23,300 PE COVER → −63 **continued**; **12:11 23,350 CE COVER, index > VWAP → −3 / −41: reversed** | at the band: 10:35 23,650 / 23,700 CE COVER → −6 / −35 stalled; 13:17 23,750 CE → 0 / +3 stalled; **09:26 23,600 CE COVER, index ≥ u2 → +4 / +17 continued**; mid-band: 11:47 23,700 CE COVER → +10 / −30 reversed; **11:56 23,800 CE COVER → −48 / −36 reversed** | "at the band → stall" **3 of 4**; "mid-band → continues" **1 of 4** (the other three reversed). The first half may be a read; the second is not. n = 8 |
| **2. FADE-D / ZONE / FADE alerts** (msg stream; the wall's WHO; R3.2 counts) + fronts.py legality (trigger_log `gate`) | the wall's WHO beside the OI slope | wall WRITE 1 of 4 the fade's way; not WRITE 5 of 9. Gate LEGAL SELL arms 6: stopped 6 | wall WRITE 4 of 4; not WRITE 0 of 3. Gate LEGAL 4: stopped 4 | **inconsistent across the two days → adds nothing yet;** stays a stamp in the log (D5). The gate's "building = legal" is the open drive's own writing and failed 10 of 10 there |
| **3. Handshake** push → answer, with the strike's WHO and the answer's speed | `who` (writers ran vs buyers left) | 25 pushes; answered in 1–2 min: 09:41, 12:09, 12:33, 12:54, 13:09, 14:36 TOOT (+7, −20, +22▼, +21▼, +10▼, −4 at +30); in 4 min: 09:35 TOOT +24, the NAHIs | 24; 1–2 min: 10:34, 11:55, 12:10, 13:16, 14:38; 3–4 min: the rest | speed does not separate (n 6 vs 5); **`who` is a fact the answer lacked** (null on 22 of 24), not an edge (R3.2) |
| **4. Speed / ROC** (fut pts/min at the pause's first close; the defending side's OI rate; the ATM premium's band) | the premium's own band position and ROC | CONT pullbacks began at 2.3–6.7 pts/min; the FAIL at **1.7**; premium < VWAP 10 of 20 at the FAIL | CONT 3.3–3.6; the pin start **−1.2**; the cap's OI rate +45L, +31L then +8L (13:18–13:27): the deceleration preceded the pin, not a break | the premium's band is the add (ATM > VWAP in healthy pullbacks, < VWAP at the FAIL); speed by itself repeats what the leg already says. n = 12 |
| **5. Futures delta / CVD / effort / VPIN** | the option-implied delta as a second CVD with WHO inside it | fut 9-min delta with the leg at every pause start incl. the FAIL (+149); **implied delta against the leg only at the FAIL (−11.6k)**; VPIN p0.13 at the FAIL vs p0.39–0.84 elsewhere; effort 21 at the FAIL vs 36–61 early | fut delta ~0 at 12:07 (+68), implied −85.8k (the flush); at the pin start both with the leg (+147 / +72k); effort 50 at the pin | **the implied delta separated the one reversal that the futures delta did not** (n = 1); VPIN's lowest percentile sat on the same row (n = 1). Not an edge, a row |
| **6. Sides** (5-min 2×2) × the flow word at the same close × Sides' own f15 | the aggressor inside Sides' ADD / COV | CAPPED+UP FUEL 4: up 4; REAL+UP FUEL 3: up 3; **SQUEEZE+UP FUEL 3: down 3**; CAPPED+UP BUYERS 6: 3 / 3; FLAT+UP BUYERS 5: 2 / 3 | CAPPED+UP FUEL 7: up 5 / down 2; **REAL+UP FUEL 3: down 3**; REAL+DOWN BUYERS 3: down 3; FLAT+LID 4: up 3; WALL+DOWN FUEL 2: up 2 | REAL (Sides' own fuel word) + UP FUEL: up 3 of 3 on 2 Nov, **down 3 of 3 on 3 Nov** — the two days contradict; SQUEEZE+UP FUEL down 3 of 3 (2 Nov only). Nothing to carry; every cell < 15 |
| trap / fronts rows | — | not crossed (trap rows are level states, no outcome field) | — | not testable here |

## R4.C One currency: option-implied directional flow vs the futures' own delta

Definition: per minute, Σ over the recorded strikes of (lifted − hit) × the chain's delta for that strike at that minute
(the chain carries delta on 22,731 of 23,072 near-ATM side-rows; forward-filled inside a minute), divided by 75 → futures-
lot equivalents. Calls lifted add, puts lifted subtract (their delta is negative), writers hitting either side do the
reverse. Straddle writing nets to ~0, so this measures directional aggression net of two-sided writing. The futures'
delta is Dext's own footprint of the NOV future (`dext_NSE-61471`), in lots.

| | 2 Nov | 3 Nov |
|---|---|---|
| Σ \|implied\| vs Σ \|fut delta\| over the day | 5.77M vs 17.3k lots (×330) | 11.6M vs 18.6k (×620) |
| 9-min sums at closes: same sign / opposite | 93 / 32 | 90 / 33 |
| corr(implied 3-min at close c, fut 3-min at c+L) | L=−2 +0.04 · **L=−1 +0.21** · L=0 **+0.49** · L=+1 +0.06 · L=+2 +0.13 | L=−2 +0.19 · L=−1 +0.12 · L=0 **+0.32** · L=+1 0.00 · L=+2 +0.04 |
| at the lean flips: when each 9-min sum turned and stayed | 12:55 ▼: implied from **12:53**, fut delta from **12:32** · 14:21 ▲: implied from 14:11, fut from **14:05** | no flip |
| divergence implied ▼ / fut ▲ (both ≥ 200 lots in 9 min) → fut +15 | 12 closes: up 7 · down 5 | 5 closes: up 1 · **down 4** |
| divergence implied ▲ / fut ▼ → fut +15 | 3: up 2 · down 0 | 1: down 1 |

**Who leads:** on these two days, **neither — they are coincident (the strongest correlation is at lag 0 on both days),
with the futures slightly first** (L=−1 beats L=+1 on both days, and at both 2 Nov lean flips the futures' delta turned
6 and 21 minutes before the option-implied delta). "Options lead the futures by a block" (the README's 2 Nov 12:30 note)
is not what the whole day shows. **Divergence as a warning:** implied ▼ while fut ▲ was followed by a fall in 4 of 5 on
3 Nov and 5 of 12 on 2 Nov — not a warning yet (n = 17). **What the option currency does give** that the futures' delta
cannot: the WHO (R4.A's one reversal, and the pin), and the size: the option side carries 330–620× the futures' aggressor
volume in delta terms, which is where "options matter more" is true — in the fuel, not in the timing.

## R4.D Writer gamma: feasible, one view

Feasibility: the chain has delta and gamma on 98.5 % of near-ATM side-rows (null on deep ITM calls), and the WHO windows
give who opened today's OI. Writer-short-gamma per strike = (Σ dOI in WRITE windows − Σ dOI in BUY windows) × the chain's
gamma at the minute (positive = writers short gamma there). Yesterday's OI is not sided (unknown who holds it): the
profile is today's only.

- **2 Nov 13:17** (spot 23,231, the low): writers shortest gamma at **23,250 CE (+16k)**, 23,200 / 23,250 PE (+6k / +5k).
  Price based 23,250–23,320 for an hour, then at 14:29 (23,250 CE +17k, 23,400 CE **−7k** = buyers hold it) **went
  through 23,250 CE**: 23,331 → 23,385 by 14:44 on CAP COVER −33L / −28L (the short-gamma writers buying back).
  **Accelerated through.**
- **3 Nov 12:59 / 13:29 / 14:23** (spot 23,691 / 23,724 / 23,701): writers shortest gamma on the **put side below spot**
  — 23,650 PE +57k → +74k, 23,600 PE +40k, 23,700 PE +19k → +46k; the call side never led. Spot sat **above** the cluster
  all afternoon (23,700–23,750) and never tested it: **pinned above it.**

n = 2 views. A profile the ladder can carry as a strip ("writers shortest gamma: 23,650 PE · 23,700 PE · spot above");
whether price goes through or pins is for the forward log, not for two days.

## R4.E My own 3D ideas, ranked by what she would use live

1. **The pullback card at every HOLD / WATCH** (she already gets the pause): three chips — `ITM writers: covering / being
   written`, `option delta 9 min: with / against the leg`, `ATM premium: above / below its VWAP`. On the two days the
   healthy pullbacks carried C/D · with · above; the one reversal carried W · against · below; the pin carried W · with ·
   above with the cap WRITE count. Display only; the forward log counts it.
2. **"Loading" gets its side** in legs.py's alive / risk items: `k1 CE loading +10L · kharidar` stays alive; `k1 CE
   loading +3.5L · likh rahe` moves to risk (R4.A, n = 2).
3. **The band-touch cell** for her ZONE lines: at a u2/u3 (d2/d3) touch of the index, the ATM / NEAR option's own band
   and its WHO in one chip — `prem u2 · writers covering` read "stall" 3 of 4 (A218's half that held). A stamp beside
   the ZONE SELL line, never a gate, logged with the row.
4. **The open-drive fence as a count, not a rule:** band SELL arms in the first 25 minutes stopped 7 of 8 across both
   days, LEGAL by §1d in 10 of 10 of those rows. Her own open question in §1b ("does u2 SELL survive at all") now has
   two more days of rows; nothing here decides it.
5. **One currency on the Float:** `fut Δ 9 min +147 · options Δ 9 min +72k · with / against` — the implied delta next
   to the futures' delta, so a divergence is seen the minute it starts; a warning only when the forward log earns it.
6. **The writer-gamma strip** under the ladder: the three strikes where today's writers are shortest gamma and whether
   spot is above, below or at them. Through on 2 Nov, pinned above on 3 Nov; counts forward.
7. **Size prints by delta, not by qty** (A218's note): a 0DTE wing print of 20L qty at ₹5 is 20L × 0.05 = 1,000 lots of
   delta; the BADA chip should carry delta-lots (the chain's delta is there every minute), so a 5L ATM print and a 20L
   wing print rank honestly.

What I would not build from this: any timing claim from the option flow (R4.C), any gate from R4.B (every cell < 15), a
third fuel.

---
---

# Round 5: the anatomy of short covering, five days (28, 29, 30 Oct, 2, 3 Nov)

NIFTY, the 03 NOV weekly's option flow on every day (6 / 5 / 4 / 1 / 0 DTE), her 3-min grid, causal at every close;
"next" columns are hindsight and say so. Five recorded days, described; nothing here is a rule. Script `round5.py`,
output `round5_out.txt`. Futures: `fut1m` on 30 Oct, 2 and 3 Nov; **28 Oct** = Dext's 1-min OHLC + OI (`dext_ohlc_NSE-61471`);
**29 Oct** = Dext's 1-min footprint with the close taken as the minute's (high + low) / 2 and OI from the 5-min OHLC file
(no 1-min closes exist for that day). The chain on **28 Oct starts at 11:08** (its first two events have no option leg).
On 28 Oct the 03 NOV contracts were the next weekly (the 28 OCT weekly expired that day), so their flow is thin; the
same floors were used anyway (no tuning). Jarvis call logs exist for 2 and 3 Nov only.

## R5.0 Definitions, fixed before any outcome was read

- **Event:** for each day, the 3 largest |15-min futures moves| ending at a close, non-overlapping (greedy); start = the
  window's first minute. 15 events, both directions as they fall.
- **Mechanism** from the two legs over the window: the futures OI change (≥ 300 lots either way counts [I: Jarvis's
  fuel run is 500 lots / 5 min; 15 min, a modest bar]) and the group words at the window's five closes. ▲: SHORT COVERING
  when the cap read COVER at ≥ 2 of 5 closes [I: writers buying back at two closes is a cascade, not one print] **or**
  futures OI fell ≥ 300 lots; FRESH LONGS when futures OI rose ≥ 300 and the cap was not covering; else MIXED. ▼ mirror:
  PUT-WRITER COVERING (floor COVER ≥ 2 closes), LONG UNWIND (futures OI down ≥ 300, floor not covering), FRESH SHORTS,
  MIXED.
- **The wall:** ▲ the CE with the largest OI at/above spot; ▼ the PE with the largest OI at/below spot.
- **Lead-in pieces at a close (each causal):** (a) TRAPPED: the wall's ltp ≥ 1.10 × its day VWAP [I: a tenth of the
  premium is what a writer notices] on OI built today ≥ 6L [I: the trapped panel's floor]; (b) STALLED: the wall's dOI
  under 1.5L at two consecutive closes after ≥ 1.5L at one of the five before (built, then stopped; §1d's "stalls first");
  (c) NEAR: spot within 2 steps of the wall [I: jarvis.AHEAD_STEPS]; GAMMA UP: the wall's chain gamma higher than three
  minutes earlier; (d) COVER: the wall's own WHO = COVER (the first covering print); PREM u2: the wall's premium at/above
  its own u2 (strike_bands); FUT-OI TREND: futures OI down ≥ 300 lots over 30 min (▲); BOTH Δ: the option-implied and
  the futures' 9-min delta both with the direction; FAST: the 3-min move ≥ 2 × the day's running median [Jarvis's
  FAST]; VPIN ≥ p0.70 [I]. "Minutes ahead" = start minus the first close in the 30 min before at which the piece held.
- **The signature S** (counted at every close of the five days, both directions, before looking): TRAPPED and STALLED
  and NEAR at the same close; **S4** = S and COVER. "Fast move after" = |fut| ≥ 40 pts in the next 15 min [I: her leg
  minimum], with or against the signature's direction.

## R5.1 The events (15) — mechanism, lead-in, inside

| day | start → end | dir | pts | fut OI (lots) · option leg | mechanism | lead-in: piece (min ahead) | inside the move |
|---|---|---|---|---|---|---|---|
| 28 Oct | 09:32→09:47 | ▲ | +82 | +2,209 · no option leg (chain from 11:08) | FRESH LONGS | — | — |
| 28 Oct | 09:53→10:08 | ▼ | −81 | +1,685 · no option leg | FRESH SHORTS | — | — |
| 28 Oct | 12:44→12:59 | ▲ | +76 | −949 · cap COVER 1 of 5 | **SHORT COVERING** (futures) | stalled 6 · **cover 3** · prem u2 30 · fut-OI↓ 30 · both Δ 30 · fast 9 · VPIN70 30 | 22,800–23,000 CE (5 strikes) covered **at the same close 12:47** (−2 to −7L); wall 23,000 did not move; no u3 |
| 29 Oct | 09:59→10:14 | ▲ | +45 | −152 · cap mixed | MIXED | trapped 6 · stalled 21 · gamma 30 · prem u2 30 · both Δ 6 · fast 6 · VPIN70 30 | 22,750–23,000 CE at 10:08; wall premium ≥ u3 at 10:08 |
| 29 Oct | 10:17→10:32 | ▲ | +63 | −570 · floor WRITE 3, cap COVER 1 | **SHORT COVERING** (futures; put writers pressing) | **trapped 24 · stalled 30 · cover 9 · prem u2 24** · both Δ 24 · fast 24 · VPIN p1.0 at start | 23,100 CE 10:20, then 22,800–23,000 at 10:26 (−9L at 23,000); ≥ u3 at 10:20 |
| 29 Oct | 14:11→14:26 | ▲ | +61 | −263 · cap COVER 2 | **SHORT COVERING** (option) | **trapped 30 · stalled 6 (both true at the start)** · prem u2 6 · fut-OI↓ 30 · fast 15 · VPIN70 6; implied 9-min **−13.6k against** | 22,900 CE 14:23, then 22,950–23,100 at 14:26; ≥ u3 at 14:26 |
| 30 Oct | 09:26→09:41 | ▲ | +61 | +124 · cap BUY 2 | MIXED | near 9 · prem u2 9 · fast 0 · VPIN p1.0; implied **−65k against** | no covering; ≥ u3 at 09:29 |
| 30 Oct | 11:05→11:20 | ▲ | +58 | −24 · cap COVER 3 | **SHORT COVERING** (option) | near 30 · gamma 6 · fut-OI↓ 21 · both Δ 27 · fast 9 · VPIN70 12; implied −7k against | **23,000 / 23,050 / 23,100 / 23,200 / 23,250 CE all at 11:08** (−11L first); **wall 23,100 → 23,400 by 11:20** (3 steps in 12 min) |
| 30 Oct | 11:44→11:59 | ▲ | +62 | −388 · cap COVER 2 | **SHORT COVERING** (both) | **trapped 30 · stalled 27 · near 30** · gamma 15 · prem u2 9 · fut-OI↓ 9 · both Δ 30 · VPIN70 30 | 23,200 11:47, 23,050 / 23,350 11:50, 23,300 11:59; wall 23,400 ↔ 23,500; ≥ u3 at 11:50 |
| 2 Nov | 09:32→09:47 | ▲ | +66 | −516 · cap BUY 4 | **SHORT COVERING** (futures; buyers lifting calls) | gamma 12 · prem u2 15 · both Δ 15; VPIN p0.25 | 23,250 09:38, 23,300 / 23,450 09:44, 23,500 09:47; ≥ u3 at 09:35 |
| 2 Nov | 12:59→13:14 | ▼ | −83 | −184 · floor COVER 3 | **PUT-WRITER COVERING** | stalled 12 · near 30 · both Δ 27 · fast 27 · VPIN70 3; Jarvis PALAT ▼ at the start; implied −115k with | 23,000 / 23,100 / 23,200 PE 13:05, 23,150 13:08, 23,050 / **23,250 (−30L) 13:11** |
| 2 Nov | 14:29→14:44 | ▲ | +54 | −10 · cap COVER 3 | **SHORT COVERING** (option) | near 30 · gamma 27 · **cover 12** · fut-OI↓ 30 · both Δ 24 · fast 24 · VPIN70 30; implied **−40k against**; Jarvis ROTATION ▲ | 23,250–23,350 14:32 → 23,400 / 23,500 14:38 → 23,450 / 23,550 14:44; **wall 23,300 → 23,400 → 23,500** (two steps in 12 min) |
| 3 Nov | 09:17→09:32 | ▲ | +66 | +566 · cap BUY 2 | FRESH LONGS | everything at 0 (the open) | 23,600 CE 09:26; wall 23,600 → 23,800 by 09:32; ≥ u3 at 09:26 |
| 3 Nov | 11:32→11:47 | ▲ | +61 | +49 · cap BUY 3, COVER 1 | MIXED | trapped 30 · near 30 · gamma 15 · **cover 6** · fut-OI↓ 30 · both Δ 30 · fast 27; implied **−180k against** (writers pressing); Jarvis HOLD ▲ | 23,650 11:38 (−10L), 23,700–23,950 at 11:47 |
| 3 Nov | 12:05→12:20 | ▼ | −59 | −822 · floor COVER 1 (the −115L close at 12:11), BUY 2 | LONG UNWIND (by the fixed rule; one covering close) | near 30 · gamma 30 · fast 30 · VPIN70 9; Jarvis **TREND ▲** at the start | 23,500–23,650 PE all at 12:11 (−20 / −11 / −24 / −34L) |

**Mechanism count:** SHORT COVERING (incl. the put mirror) **8 of 15** (8 of the 13 with an option leg); FRESH 3; LONG
UNWIND 1; MIXED 3. Of the 12 ▲ events, futures OI fell in 9 (−10 to −949 lots) — her instinct that the fastest moves
are covering holds as a description of these five days.

## R5.2 What came before the speed (the 13 readable events)

| piece | held within 30 min before the start | held at the start close | typical lead |
|---|---|---|---|
| NEAR (≤ 2 steps from the wall) | 8 of 13 | 5 | 30 min (it is a state, not a trigger) |
| wall premium ≥ u2 | 8 of 13 | ≥ u3 at 4 | 6–30 min |
| VPIN ≥ p0.70 | 10 of 13 | 7 | 3–30 min |
| futures OI down ≥ 300 over 30 min (▲) | 7 of 11 ▲ | 7 | 9–30 min |
| both deltas with the direction | 11 of 13 | 7 (**against at 5**: 29 Oct 14:11, 30 Oct 09:26 / 11:05, 2 Nov 14:29, 3 Nov 11:32 — writers pressing right before being run over) | 6–30 |
| FAST (the previous 3-min bar) | 10 of 13 | — | the leg before |
| TRAPPED (a) | 5 of 13 | 3 | 6–30 |
| STALLED (b) | 6 of 13 | 1 | 6–30 |
| gamma rising | 7 of 13 | — | 6–30 |
| the first COVER at the wall (d) | **4 of 13** (3, 9, 12, 6 min ahead) | 0 | 3–12 |
| **S = (a) and (b) and (c) together** | **0 of 13** | 0 | — |
| Jarvis's word (2–3 Nov only) | OPENING, PALAT ▼ (right), ROTATION ▲ (right), NO LEG, HOLD ▲, **TREND ▲ into the 12:05 ▼** | | |

**Inside the move (the 8 covering events):** the cascade is **near-simultaneous at 3-min resolution** — in 5 of 8 three
to five strikes covered at the same close (28 Oct 12:47, 30 Oct 11:08, 2 Nov 13:05 / 13:11, 3 Nov 11:47 and 12:11);
sequential outward covering over 6–12 min in 3 (29 Oct 10:20→10:26, 14:23→14:26, 2 Nov 14:32→14:38→14:44). **The wall
migrated 1–3 steps inside the window in 4 of 8** (30 Oct 11:05: 3 steps in 12 min; 2 Nov 14:29: 2 steps; 30 Oct 11:44
and 3 Nov 09:17 ↔ 1–2 steps); it did not move in 4. **The wall's premium broke its u3** inside or at the window's first
close in 7 of 13 (10:08, 10:20, 14:26, 09:29, 11:50, 09:35, 09:26) — a confirmation at the first or second close, not a
lead.

## R5.3 False alarms (every close of the five days, 625 per direction; "with" = ≥ 40 pts the piece's way in 15 min)

| piece (UP, the cap) | closes | with | against | flat | | piece (DOWN, the floor) | closes | with | against | flat |
|---|---|---|---|---|---|---|---|---|---|---|
| **S** (trapped · stalled · near) | **2** | 0 | 0 | 2 | | S | 1 | 0 | 0 | 1 |
| S4 (S · cover) | 0 | | | | | S4 | 0 | | | |
| trapped | 131 | 16 | 7 | 108 | | trapped | 20 | 0 | 1 | 19 |
| stalled | 63 | 7 | 2 | 54 | | stalled | 72 | 4 | **14** | 54 |
| near | 243 | 16 | 13 | 214 | | near | 240 | 9 | 30 | 201 |
| the first cover | 30 | 3 | 3 | 24 | | cover | 20 | 0 | 3 | 17 |
| premium ≥ u2 | 115 | 20 | 6 | 89 | | prem u2 | 16 | 0 | 3 | 13 |
| VPIN ≥ p0.70 | 191 | 30 | 9 | 152 | | VPIN70 | 191 | 9 | 30 | 152 |
| implied Δ against the direction | 133 | 9 | 9 | 115 | | imp against | 177 | 5 | 19 | 153 |
| FAST | 64 | 5 | 3 | 56 | | fast | 64 | 3 | 5 | 56 |
| trapped · cover | 13 | 0 | 3 | 10 | | | | | | |
| near · cover | 17 | 0 | 2 | 15 | | | | | | |
| trapped · near | 57 | 3 | 3 | 51 | | | | | | |

(Per-day rows are in `round5_out.txt`. Four of the five days closed up, which is why every DOWN piece reads "against"
more than "with" — the pieces are reading the days' drift, not a squeeze.)

**The signature never fired before any of the 15 events and fired three times in 1,250 closes, all flat.** The pieces
alone fire 30–240 times a direction; each was followed by a ≥ 40-pt move its way in 3–30 of those closes and against it
in 3–13. The best single piece by count, premium ≥ u2 (20 with vs 6 against of 115), is also the most ordinary: a cap
already being paid up is what every rally looks like from the inside.

## R5.4 Verdict, honestly

**Short covering can be seen happening, not coming.** On these five days the fastest moves were covering in 8 of 15
(9 of 12 ▲ with futures OI falling), and inside each one the option flow named the strike that broke, the cascade (3–5
strikes at one close in 5 of 8) and the wall's migration (4 of 8) — within the first or second 3-min close. Before the
start, every piece in the first-principles lead-in was either common (near, VPIN, premium ≥ u2, futures OI already
falling: 100–240 closes a direction) or rare and non-leading (the first cover 4 of 13, S never). The cleanest thing before
the speed was the opposite of the brief's (a)–(d): **in 5 of 12 ▲ events the option-implied delta was strongly against
the coming move at the start** — call writers pressing the cap hard (3 Nov 11:32: −180k lots-equivalent; 30 Oct 09:26:
−65k) just before being run over — and even that read fired 133 times with 9 with / 9 against. n = 13 readable events,
INCONCLUSIVE by the house rule, and the five days are four up-days and an expiry.

Attacks on the first principles, from the rows: (1) the cap's writers were TRAPPED by 10 % before only 5 of 13 events
and at 131 closes without one — being under water does not make them cover; being run through does. (2) "Stalls first
= fuel" held at the start in 1 of 13. (3) NEAR with gamma rising is the normal state of a trending day (243 closes).
(4) The first covering print preceded the start in 4 of 13 by 3–12 min and was the better of the four; but 30 closes
carried it and 3 went on. The cascade order the brief expects (one strike, then the next, then the wall moves) appeared
in 3 of 8; the other 5 covered a whole band at one close.

## R5.5 Design: SQUEEZE, a state line, not a forecast

Given R5.3, a SQUEEZE WATCH that fires before the move would be the compression/trap filter again (pre-registered,
then harmful). What the data supports is **SQUEEZE ON**, said at the first close that shows it, inside the HOLD /
WATCH line and the pullback card (R4.E-1), never alone:

- `SQUEEZE ON ▲ · 23,000 CE bhaag rahe −11L · 4 strikes ek saath · deewar 23,100 → 23,400 · fut OI −240` — said when the
  wall's WHO is COVER with ≥ 2 more CE strikes at/above spot covering at the same close [I: the cascade as seen, 5 of 8],
  or the wall COVER at 2 consecutive closes [I: the sequential kind, 3 of 8].
- `SQUEEZE ▼` mirror on the floor (2 Nov 12:59).
- Before it, no WATCH word; the ingredients are shown as plain chips on the wall's row and the card, as they already
  are: `likh rahe / bhaag rahe`, `phanse 12 pts`, `1 step door`, `prem u3`, `fut OI −547`, `VPIN p0.80`, `options Δ −40k vs
  fut +16` — facts, no arrow.
- Telegram: SQUEEZE ON only (it is a state change that happens 1–2 times a day).

**Kills:** forward, counts only, both directions, 20 sessions: SQUEEZE ON said → fut at +15 / +30 with and against; if
the "with" count does not exceed "against" by at least 2 : 1 at n ≥ 15 per direction, the word goes back to being the
chips. A second kill: if SQUEEZE ON is said more than 4 times a day on 5 of 20 days, the cascade bar rises to 3 strikes.

**Pre-registration (to be signed before Monday's open, as a stamp beside the HOLD / WATCH line, never a gate):**
> SQUEEZE ON ▲ is stamped at a 3-min close when the cap (the CE with the largest OI at/above spot) reads COVER and at
> least two other CE strikes at/above spot read COVER at the same close, or the cap reads COVER at two consecutive closes;
> SQUEEZE ON ▼ mirror on the floor. Thresholds: OI_MOVE 1.5L / 3 min, AGG_X 0.2, fixed. Predictions: (1) it is stamped
> 1–3 times a day; (2) fut at +15 after a stamp is ≥ +20 its way more often than ≤ −20 by count; (3) the stamp lands at
> or before the second close of each day's three largest 15-min moves that are covering. Falsifiers: (2) fails at n ≥ 15
> per direction; or (1) exceeds 4 a day on a quarter of days; or the result collapses once the best day is removed. No
> forecast version (a WATCH before the first cover) is registered: on five recorded days its signature fired 3 times in
> 1,250 closes and preceded none of 15 fast moves.

---
---

# Round 6: TapeMap's own footprint reads on the option strikes (five days)

`prints.py` (rebin, imbalances, bar_flags, profile, with_cvd, tm_marks) run unchanged on the Dext option ladders, NIFTY,
28–30 Oct + 2–3 Nov, her 3-min bars (per-price cells merged over the bar; o / c = the chain's ltp at the previous / this
close). Script `round6.py`, output `round6_out.txt` (it also carries strike_bands' import-time tables). Recorded days,
described; every cell under 15 is INCONCLUSIVE. No server touched.

**Scale, fixed in `round6.py` before counting (NOTES.md "Round 6 scale"):** option row = 1 % of the bar's close premium
rounded to the 0.05 tick (a ₹80 option in ₹0.80 rows, a ₹8 one in ₹0.10: the same ten rows a point of futures gives);
one "lot" fed to `imbalances` = 7,500 qty, so IMB_MIN_LOTS 5 = 37,500 qty = 500 lots at one row (a tenth of a wall
move); big cells three ways: qty ≥ 5L (as before), **₹ ≥ 2 crore of premium at one cell** (5L × ₹40, an ATM-sized print),
**delta-lots ≥ 2,000** (qty × |chain delta| / 75: the size of a wall move in index terms). `rank.py`'s BADA (≥ p90 of the
futures reference) is not transferable to options and was not used.

## R6.1 The table

| read | what it marks on an option | 28 Oct | 29 Oct | 30 Oct | 2 Nov | 3 Nov | verdict |
|---|---|---|---|---|---|---|---|
| **big prints, three classes** (Q qty / R ₹ / D delta-lots; cells meeting any) | which prints are big *in index terms* | R 143 only | R 90 · Q 2 | R 566 · RD 44 · Q 6 · QRD 1 | R 632 · RD 304 · QRD 39 · Q 20 · D 19 | **Q-only 2,723** · D 2,451 · QD 1,213 · RD 910 · QRD 743 · R 232 | **class changes are the finding:** on 3 Nov the WING 3–5 zone held **1,311 qty-big cells, 16 of them delta-big and 0 ₹-big**; ATM held D 1,454 · RD 362 · QRD 488 · R 1xx. BADA by delta-lots keeps the ATM / NEAR / ITM prints and drops the ₹5–30 wings; by ₹ it keeps ITM and ATM only. Qty-big alone is a wing counter |
| **absorption** (tm_marks: \|delta\| top quarter, range ≤ median) at wall / ATM±1 strikes; fut +15 ≥ +20 / ≤ −20 | the premium ate size without moving | 5 (2 / 2) | 9 (2 / 0) | 24 (2 / **11**: 23,050 / 23,100 PE 12:44–13:26) | 2 (1 / 0) | 31 (**15** / 0: 23,650 / 23,700 PE 13:59–15:26) | marks cluster on the PUT side of ranges and pins; the index went the put-writers' way after (30 Oct down 11, 3 Nov up 15: opposite signs, both "puts absorbed"). Direction is not in the mark; **does not separate** as a bar read. **The 3 Nov 09:48–10:15 "80 wall" on 23,600 CE got no absorption mark** (exhaustion at 09:50 and 10:11): the bar's range was wide (64–76), so tm_marks' range gate fails where the per-print wall lived |
| **stacked BUY imbalance at the cap** (3 rows at ≥ 3 : 1, ≥ 37.5k qty a row); closes carrying one; fut +15 ≥ +40 | buyers lifting the cap row after row | 0 | 1 (0) | 3 (0) | 9 (1) | 7 (2) | 20 closes in 625; 3 followed by ≥ +40, 0 by ≤ −40. **Before the first COVER close in R5's 8 covering events: 2 of 8** (30 Oct 11:05: a stack at 10:44, 24 min ahead; 2 Nov 09:32: stacks at 09:17 / 09:35, 30 min ahead, the open); none in the other 6 (28 Oct 12:44, 29 Oct 10:17 / 14:11, 30 Oct 11:44, 2 Nov 12:59 ▼ / 14:29). **Does not lead covering** |
| **climax / exhaustion** at the cap and ATM strikes, by the premium's band (band = ≥u2/u3 or ≤d2/d3) → fut RUN / TURN / flat with the mark's side | the premium's own buying/selling climax | climax band 3 / 3 / 8 · mid 5 / 4 / 7; exh band 3 / 4 / 6 | climax band 0 / 2 / 10 · mid 5 / 1 / 23; exh band 1 / 4 / 1 | climax band 2 / 4 / 4 · mid 8 / 10 / 20; exh band 4 / 5 / 3 | climax band 6 / 2 / 6 · mid 5 / 2 / 19; exh band 2 / 2 / 9 | climax band 8 / 4 / 10 · mid 19 / 12 / 20; exh band 4 / 2 / … | the known case is caught (**23,650 CE climax at 10:35 on 3 Nov**, fut −35 at +30), but across the days RUN ≥ TURN after band climaxes on 3 of 5 days and most are flat: **does not separate** STALL/TURN from RUN |
| **per-strike CVD divergence** (cap strike: premium at a 30-min high, CVD not) → fut +15 | buyers paying up without aggression | up 18 / dn 18 | up 52 / dn 0 / flat 117 | up 32 / dn 12 / flat 36 | up 32 / dn 36 / flat 70 | up 32 / dn 47 / flat 39 | **inverted on 29–30 Oct (up after a divergence at a high), the other way on 2–3 Nov**: oi-lab's warning holds on options too. Does not separate |
| **volume profile POC** (the strike's own, day so far) vs a 3-row placebo: next-3-bar reversal | the trapped side's average fill | poc rev 5 / cont 4 · placebo 4 / 6 | 1 / 1 · 1 / 2 | 2 / 5 · 2 / 0 | 4 / 5 · 4 / 17 | 2 / 5 · 3 / 3 | every cell < 15; **not testable**; nothing visible against the placebo |
| pullbacks (R4) × absorption at the defending strike | — | — | — | — | — | — | **not done this round** (budget); the marks' clustering on the put side of pins says the answer would need the direction attached |

## R6.2 The stacked-imbalance-before-COVER answer

Two of the eight covering events had a stacked buy imbalance at the cap before the first COVER close — 24 minutes
ahead (30 Oct 10:44 → 11:08) and 30 minutes ahead at the open (2 Nov 09:17 / 09:35 → 09:47). The other six had none in
the 30 minutes before. Over all 625 closes, 20 carried a stacked buy at the cap and 3 were followed by ≥ +40 in 15 min.
**Covering is not seen earlier by stacked imbalances at this scale.** (The scale is one choice; a smaller row or a lower
row minimum would create more stacks and more false alarms, and was not tried — the stop rule.)

## R6.3 What the footprint reads add on an option, honestly

- The one thing that moves her tool: **BADA by delta-lots.** It removes the wing noise (1,311 → 16 on 3 Nov) and keeps
  the prints that carry index exposure; it needs only the chain's delta, which is there every minute.
- Absorption / climax / exhaustion at bar level mark the pin side (puts on 3 Nov, puts on 30 Oct) and catch the famous
  moments (10:35), but as populations they do not separate what follows; the per-print "wall at a premium" the README
  read (80 on 23,600 CE) is a different object from tm_marks' bar absorption and was not reproduced by it.
- CVD divergence on a strike is as unreliable as on futures, and inverted on two of five days.
- The premium POC does not beat a placebo at n < 15.

## R6.4 What I would pre-register as a §1s amendment

> **§1s-A (BADA on options).** A big option print is counted by delta-lots: qty × |the chain's delta at that minute| /
> 75 ≥ 2,000, with its qty and ₹ value shown beside it; a qty-big print under 2,000 delta-lots is a wing print and carries
> no chip. Shadow, display only; the forward log counts chips per zone (ITM / ATM / NEAR / WING) per day. Falsifier: if
> over 20 sessions the delta-lots chips in the WING zone exceed those in ATM + NEAR, the floor is wrong.
>
> **§1s-B (not registered).** Stacked imbalances, bar absorption, climax / exhaustion and CVD divergence on option
> strikes are logged as marks in the forward record (prints.py unchanged, the Round 6 scale), never shown as words,
> until 20 sessions of marks exist; on five recorded days none separated RUN from TURN or led a covering close.

---
---

# Round 7: each strike against its own day-normal, at its own premium bands (her correction)

NIFTY, five days, her 3-min grid, causal; definitions fixed in NOTES.md ("Round 7 definitions") before counting; script
`round7.py`, output `round7_out.txt`. No server touched. **Data note:** today's 09:17 scrip-master download dropped the
expired 03 NOV contracts, so the Dext files had no names; `load.recover_map` rebuilt file → strike by matching each
file's 3-min delta at her closes against `days.json` (exported while the names existed), exact on ≥ 20 closes
(`scrip_recovered.json`: 40 / 43 / 41 / 32 / 25 contracts; one 3 Nov file did not reach 20 matching closes).

## R7.1 Signatures at the band — HOLD / RUN at +30 min, per day

| signature | at the band: HOLD / RUN (28 Oct · 29 · 30 · 2 Nov · 3 Nov) | control: touches with no signature | control: the same effort inside the bands (HOLD / RUN) | verdict |
|---|---|---|---|---|
| **ABSORPTION** | 39/9 · 18/11 · 22/3 · 42/3 · 51/0 | 252/73 · 166/67 · 262/112 · 159/42 · 136/26 | 37/6 · 119/15 · 78/22 · 26/24 · 98/39 | **holds more than a bare touch on 4 of 5 days** (28 Oct 39/9 vs 252/73, 30 Oct 22/3 vs 262/112, 2 Nov 42/3 vs 159/42, 3 Nov 51/0 vs 136/26; 29 Oct 18/11 vs 166/67 alike). Part of that is the definition (it requires the next close to hold); the +30 outcome is one bar further. Inside the bands the same effort ran more (in_ABSORPTION RUN 6–39): **the band is what makes it mean something.** Cells ≥ 15 on four days |
| **EXHAUSTION** | 18/5 · 6/8 · 11/2 · 16/0 · 6/1 | same | — | 28 Oct and 2 Nov hold-heavy, 29 Oct 6/8: mixed, cells < 15 on three days: **inconclusive** |
| **CLIMAX** (beyond u3/d3, p95 effort, delta flips) | 10/7 · 6/8 · 5/0 · 4/0 · 7/1 | same | 38/4 · 60/13 · 53/19 · 51/34 · 73/35 | every cell < 15: **inconclusive**; inside, "climax" without a band runs as often as not (2–3 Nov) |
| **IGNITION** (p90 effort, closes beyond u2 and stays, writers covering) | 8/2 · 9/6 · 1/1 · 3/3 · 5/0 | same | 0/0 · 1/3 · 2/1 · 4/9 · 8/0 | **did not run more**: the premium was still beyond u2 and higher 30 min later in 12 of 38; the move it marks is mostly over at the mark (see the covers) |

## R7.2 The four named cases, by minute (the strike's own numbers)

- **3 Nov 09:47–10:17, 23,600 CE "about 80":** every close INSIDE its bands (u2 83–86); vol p0.0–0.55, |Δ| p0.09–0.80 —
  **nothing abnormal by its own day-normal**; the highs stopped at 80.1 / 79.6 / 79.7 (09:50, 09:53, 10:02) with sellers
  (who D, DUMP) and the premium fell to 64 by 10:11, then 74–76 at 10:14–10:17 (who B → C). **No ABSORPTION by the fixed
  definition**: the "80 wall" was a per-print event inside normal effort, not an abnormal-effort-small-result bar.
- **3 Nov 10:35, the buying climax:** 23,650 CE at 10:35: AT u2 (h 68.2, u2 62.2, u3 70.2), **vol p0.96, |Δ| p0.96, Δ
  +23.3L, dOI −27.3L, writers covering**, then 10:38 Δ −22.6L (the flip) and the close back inside (56.9 < u2 62.9).
  23,600 CE: 10:35 AT u2, |Δ| p0.88, +19.2L, dOI −24.8L; 10:38 −25.3L. **It is her climax exactly, and the fixed
  definition missed it** (CLIMAX needs BEYOND u3; the bar stopped 2 points short of u3, so it reads only "AT u2 + p96
  effort + flip"). IGNITION failed too because the next close fell back inside. Noted, not retuned.
- **3 Nov 13:15–13:18, the 23,700 CE break:** 13:17 close: **BEYOND u3 (c 54.1, u3 52.6), vol p1.0, |Δ| p0.97, Δ +53.5L,
  dOI −46.0L, writers covering → CLIMAX + IGNITION**; 23,750 CE the same (IGNITION, vol p1.0, dOI −12.4L); **23,700 PE
  at its own d2 (AT_D) with writers pressing (W, dOI +17.3L, Δ −33.7L)** — the pair A218 described. 13:20: 23,700 CE
  still beyond u3 but who D (call buyers taking profit), CLIMAX again; +30 outcome HOLD (the premium 52 → 45 by 13:47).
  **Ignition read at the break close, not before it.**
- **2 Nov 12:56–13:14, the down-leg on the PE side:** 23,250 PE 12:56 and 13:05: vol p1.0 / p0.99 inside its bands
  (in_CLIMAX); **13:11: BEYOND u3 (h 126.1, u3 122.4), vol p1.0, |Δ| p1.0, Δ +17.5L, dOI −30.1L, writers covering →
  CLIMAX + IGNITION**; 13:14 Δ flat, still beyond; the low in the index was 13:14. 23,300 PE 13:14 BEYOND u3, who C.
  **The PE side did read ignition — at 13:11, six minutes after the floor wall's first COVER close (13:05) and three
  minutes before the low.**

## R7.3 Ignition vs the eight covering moves (R5)

| event | first COVER close at the wall | first IGNITION close (any strike that side, start −30 … end) | minutes |
|---|---|---|---|
| 28 Oct 12:44 ▲ | 12:41 | 12:41 (22,650 / 22,700 / 23,000 CE) | **0** |
| 29 Oct 10:17 ▲ | 10:08 | 10:08 (22,600–23,000 CE, five strikes) | **0** |
| 29 Oct 14:11 ▲ | 14:26 | 14:26 (22,750–23,050 CE, six strikes) | **0** |
| 30 Oct 11:05 ▲ | 11:08 | none | — (the biggest cascade had no ignition: effort was not abnormal for those strikes' own day) |
| 30 Oct 11:44 ▲ | none in the window | 11:56 / 11:59 | after |
| 2 Nov 09:32 ▲ | 09:47 | none (bands unreadable before 09:44) | — |
| 2 Nov 12:59 ▼ | 13:05 | 13:11 (23,150–23,400 PE, six strikes) | **−6 (after)** |
| 2 Nov 14:29 ▲ | 14:17 | none | — |

**Ignition is coincident with the first cover in 3 of 8 and after it in 2; it never led.** It is the squeeze's
confirmation at the strike's own band, with the day-normal attached — a better SQUEEZE ON stamp than R5.5's (it names
the strike, the effort rank and the band), not an earlier one.

## R7.4 Pullbacks × absorption (the owed check)

In all 11 of R4's pullbacks the defending wall strike (the floor PE in an up-leg: 23,000 / 23,300 / 23,600 PE; the cap
CE in a down-leg) showed **no signature at its band** — because the wall strike never reached its own u2 inside the
pullback (a deep OTM wall's premium does not reach its bands on a 30–70-pt dip). **Not testable as defined.** The ATM
strike's band is where a pullback shows; R4.A already had that read (ATM premium above / below its VWAP) and it separated
the one FAIL.

## R7.5 What, if anything, to pre-register

> **§1s-C (ABSORPTION at the strike's own band), shadow.** At each 3-min close, for ATM ±3 and the wall strikes: effort
> at the strike's own p90 (vol or |delta|, ranked from the 7th close), a small result (range ≤ its own median, or the
> close back inside u2 / d2), at AT or BEYOND its own premium band, and the band held at the next close → a chip
> `23,650 CE absorb · effort p96 · u2 held`. Counted forward: HOLD / RUN at +30 beside bare touches, per day, both
> sides. Falsifier: HOLD does not exceed the bare touch's HOLD by count on at least 15 of 20 sessions; or fewer than 15
> rows a side in 20 sessions.
>
> **Not registered:** EXHAUSTION, CLIMAX (its fixed form missed 10:35 by two points of u3 — a definition that reads AT
> u2 as well would be a retune and is written here only as a note), IGNITION as a lead (it is a confirmation; it goes
> into the SQUEEZE ON stamp of R5.5 as its strike-level form: `23,700 CE ignition · effort p100 · beyond u3 · writers
> bhaag rahe −46L`).
