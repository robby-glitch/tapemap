# HANDSHAKE — Fable's critique and the v2 (28 Oct 2026, 00:10)

Files here: `hs_check.py` (data truth, the definitions on every day with flow, the gating rows), `export_v2.py` → `data_v2.js` +
**`RAFTAAR-handshake-v2.html`** (self-contained, 8 days: 26 · 22 · 23 · 27 · 21 · 8 · 6 Oct · 29 Sep), `handshake-v2.html` (template).
Nothing outside this folder was touched. Every number [M] off the record; thresholds [I]. Rows, not rates; points after a line are points.

## MUST-FIX

| # | minute · evidence | what misleads | fix (in v2) |
|---|---|---|---|
| M1 | **Dext rows are re-written as the bar fills, not repeated.** 6 Oct: 223 duplicate rows DIFFER from each other; 19 Oct 12; 27 Oct 15 (hs_check A). `export.py` keeps whichever row comes last in the file. | On the rewritten minutes the delta shown can be the partial bar, not the closed one. | Keep the row with the largest `total_volume` per minute (`dext()` in export_v2). |
| M2 | **Three contracts in `data/dext`.** NSE-2885 is the Sep future, NSE-48704 Oct, NSE-51345 Nov. On 21 Oct Nov did 168M contracts, Oct 17M; summing them made "pushes" of −5,150 / +8,535 lots in 2 min at 10:01–10:03 (roll crosses). The Sep-contract files (24–28 Sep) disagree with Upstox 17/45 by sign and sit 140–200 lots/min off the book. | A roll cross is not a push; a Sep file is not Sep flow. | Near month only, the contract GoCharting's NIFTY-I and Upstox's key track: 2885 to 30 Sep, 48704 1–27 Oct. The mockup already used 48704 — keep it; never sum; do not use the Sep files. |
| M3 | **The answer bar is 4 % of today's build, not of the wall.** A wall built yesterday has a big OI and a small build, so it "answers" at 3L; a wall built today needs more. 26 Oct 09:52 CE 22500: absolute OI 182L → bar 7.3L (still TOOT −31L); on 27 Oct the absolute rule turns 3 of 5 TIKI into NAHI. | The strike a push hits is its whole OI, not what was written since 09:15. | Attacked strike = the biggest **absolute** OI in the band; bar = max(3L, 4 % of that OI). |
| M4 | **"NAYA FLOOR = the move is backed" is true only when writers opened it.** 26 Oct 09:52: the 22550 PE add (+15.2L) had premium beating delta by 5.6 ticks — put BUYERS; 09:56 22600 PE +27.7L, +5.9 ticks, buyers again. Over the 8 days the OI added behind price was opened by writers 54 times, buyers 44, unclear 3 (export_v2 census). | A buyer-opened add is protection being bought, not a floor being laid. | v2 computes WHO OPENED (premium move − delta × spot move; > +2 ticks buyers, < −2 writers) for the attacked strike's adds and for the add behind price, and prints it on step 3 and on the floor / cap label. |
| M5 | **Dext is blank on the 27 Oct afternoon (and all of 14–15 Oct; 13 and 16 Oct partial).** The mockup shows amber and stops reading. | The expiry afternoon is where the book was busiest: 14:35 ▲213 lots → CE 22700 −96.4L TOOT, fut OI −1,698 lots COVER, +39 / +65 pts after. | The 1-second book, quote rule (trade at/above the ask = buy, at/below the bid = sell, else by tick), as the fallback: on October days it agrees with Dext per minute 288–321 same-sign vs 33–84 opposite, median difference 4–22 lots (hs_check A). On 27 Oct 20 of 30 pushes come from the book; shaded on the strip, tagged in the panel. |
| M6 | **A small look-ahead in the panel.** Step 1 prints `GoCharting ▲ · Upstox ▲ · 3/3 SAATH` at the push minute from the 5-min bar of the push's slot — a bar that closes up to 4 min later. | The agreement shown at 09:52 uses the 09:50–09:55 bar. | v2 shows the three sources on the push's bar only at the answer, once `slot + 5 ≤ answer minute`, as a count n/3. |
| M7 | **A push whose strike has no OI at +4 stays "?" forever** (27 Oct one push). | "?" reads as pending, not as could-not-check. | After 4 min with no reading print "could not check" (the ? reason), never a pending mark. |

## SHOULD-FIX

| # | evidence | fix |
|---|---|---|
| S1 | **Upstox is not wrong-signed.** October 5-min sign counts, same/opposite: Dext~GoCharting 55–65 / 9–22, Dext~Upstox 49–67 / 6–25, GoCharting~Upstox 35–62 / 12–37. On 22 Oct itself Dext~Upstox 52/23 beat Dext~GoCharting 40/35. A122's 09:30 bar is one bar. | Never name an outlier source on the screen; show the count (v2: `2/3 ▲ · ek alag bol raha`). |
| S2 | **An answered push is not a continuation read on every day.** Mean points +15 min along the push, answered vs no answer: 26 Oct +60 vs +2, 21 Oct +56 vs +4, 22 Oct +39 vs −14, 1 Oct +57 vs +1 — but 6 Oct −5 vs −7, 8 Oct −8 vs −1, 19 Oct −18 vs +2, 27 Oct −1 vs +1, 5 Oct −13 vs −5 (hs_check B). On expiry / grind days a TOOT is a pin filling. | Carry the day kind (EXPIRY) and the engine's picture into step 2's wording: "deewar toot rahi · expiry: pin bhar raha?". |
| S3 | **A TOOT at a leg's top:** 26 Oct 14:08 ▲387 → CE 22700 −19.5L, then −17 / −8; 23 Oct 14:36 and 14:40 TOOT ×2, then −30. The handshake confirms the push, not the room left. | Print "kitna chal chuka" (points since the leg's start, from the engine's picture) beside the answer. |
| S4 | 26–39 pushes a day, 16–28 of them NAHI (every day; 22 Oct 23 of 26). The pending ◆? pile up on a chop day. | Keep NAHI as dots (done); drop the pending diamond for a push whose 2-min delta is under 1.5× once a newer push exists. |
| S5 | The strike map draws today's build; the push hits the absolute wall. | Draw the top-2 absolute walls per side as the chart layer's deewar lines, s-tagged, moving when they roll. |
| S6 | Effort per point ≥ 2× at an answered push is rare (0–3 a day). | A chip, not a step (v2). |
| S7 | Labels overlap when answers come 2 min apart (26 Oct 09:52 / 09:56 / 09:58). | Label lanes (v2 shifts a label up / down until free). |
| S8 | BANKNIFTY / SENSEX: no Dext (MCX-569900 is a commodity file). | BANKNIFTY gets the same book fallback from `book_BANKNIFTY`; SENSEX takes NIFTY's flow with its own OI (§1q). Not built here. |
| S9 | Her levels (PDH / PDL / weekly) are not in what the mockup reads; the only level is the attacked strike. | Add `levels.py`'s lines to the strike map so a push "into PDH" reads as such. Not built here. |
| S10 | Expiry after 14:30: 27 Oct 14:35 −96L on +48 pts; 15:20 CE 22800 +25L TIKI with the premium 24 ticks under delta. | Label GAMMA ZONE after 14:30 on expiry (the brainstorm's scenario) and read answers there as gamma, not walls. |
| S11 | The 26 Oct 12:40 block (7,414 lots in 2 min; Dext +6,559, GoCharting +7,880, Upstox −9,703; fut OI +1,654 FRESH; price −18): the day before expiry, both legs crossing. | ★ "BLOCK · roll?" with the fut OI, never a push (v2). Upstox's sign on a cross is the one not to trust. |

## FINE (checked, holds)

- **Causality of the display:** a push exists at its minute; its answer, the floor / cap behind, and the points after are drawn only once those minutes have passed (`am ≤ now`, `now ≥ m + 15`). The 5-min bars are drawn only after they close. The future is masked.
- **Alignment:** Dext `time` is the bar's start, complete at the end of that minute; the chain's minute is its last snapshot; both are "end of minute m". GoCharting and Upstox `t` is the bar start; a bar at `m` is used only from `m + 5`. One lot = 65 (the book's `ltq`).
- **The push test** (2-min delta ≥ 2× the last-30-min median and ≥ 150 lots) found 26 Oct 09:52 (+458, normal ~100) and 09:56 (+530), and the 22 Oct 12:18 nudge (−369, no answer, +98 after).
- **The 6-step chain** reads the way she described it: push → answer at the strike → floor / cap behind → flow now → new wall ahead → reversal fuel. v2 keeps the order and adds who / fut / effort / sources as one row.
- The engine word (lockstep, all three indices) is the replay's own, not recomputed.

## What v2 adds, and why

1. **Book fallback** (M5) — validated on 8 October days against Dext; shaded on the strip and tagged in the push line.
2. **Absolute-OI attacked strike** (M3) and its bar.
3. **WHO OPENED** (M4) on the attacked strike's adds (PHANS / TIKI) and on the add behind price: KHAREEDAR / WRITERS / ?.
4. **The futures leg** per push (oi-lab's surviving read): fut OI with the push ≥ 500 lots = FRESH, against = COVER (26 Oct 09:52 COVER −763: short covering under the break), else FLAT.
5. **Effort per point** per push (effort.py's rule on the flow used, vs the day's median of 5-min blocks).
6. **Three sources at the answer**, as a count n/3, causal (M6).
7. **Points after** (+15 / +30) in the log, shown only once passed — the evening review of every push.
8. **Basis** in the header as the 3-min median of fut − spot (A60); spot `s`, fut `f`.
9. **Label lanes**, lakh everywhere (2 decimals under a lakh), no `%` on the face (the "4 %" is a size bar in the footnote, not a rate).
10. **Four more days** (21 Oct top, 8 Oct trend ▼, 6 Oct pin grind, 29 Sep Sep-expiry round trip).

## The gating question — should "no OI answer" gate the engine's "chop se bahar" / ≠ READ lines?

Rows (hs_check C, near-month flow, absolute-OI rule; the 10 min before each line):

| line | pushes in the 10 min before | verdict |
|---|---|---|
| 21 Oct 10:04 ≠ READ / chop se bahar (**right**, +54 / +8) | 10:03 ▼ −257 → PE 22950 **TOOT −10.0L** | answered |
| 26 Oct 09:55 ≠ READ (**right**, +125 / +103) | 09:52 ▲ +458 → CE 22500 **TOOT −31.0L** | answered |
| 21 Oct 11:40 chop se bahar (right direction) | 11:31 ▼ −203 TOOT −4.5L; 11:36, 11:40 NAHI | answered (9 min before) |
| 22 Oct 11:16 killed ≠ (−130 in 30) | no push | no answer |
| 22 Oct 12:21 killed ≠ (+48 against) | 12:13 ▲ NAHI, 12:18 ▼ −369 NAHI | no answer |
| 26 Oct 13:50 killed ≠ (ATKA minute) | 13:49 ▼ −185 NAHI | no answer |
| 27 Oct 13:22 killed ≠ (0 / −8) | no push | no answer |
| 26 Oct 14:09 killed ≠ (−33 / −24) | 14:08 ▲ +387 TOOT −19.5L | answered, and wrong |
| 27 Oct 10:21 killed ≠ expiry (−36 / −59) | 10:20 ▼ −221 TOOT −15.3L | answered, and wrong |
| 23 Oct 14:45 killed ≠ (−30 / −30) | 14:36, 14:40 ▼ TOOT ×2 | answered, and wrong |

**Answer: yes as a required check, no as a sufficient one.** An answered push inside the last 10 min was present at both right lines
and absent at four of the seven wrong ones; three wrong lines had one (a squeeze top, an expiry flush, a late-day TOOT). So: a ≠ READ
line and a "chop se bahar" need an answered push (TOOT / PHANS at the attacked strike, writer-opened if it is a floor / cap) inside the
last 10 min — on these days that blocks nothing right and nothing the current rules do not already block — and the handshake rides
as one more grade check on every CHAL RAHA. It must not replace the rules that killed the other three (this minute moving, young leg,
no expiry day): those are what separate 26 Oct 14:09 from 26 Oct 09:55. n is 2 right and 7 wrong; judged forward.

## Least sure of

The WHO-OPENED test at 1-minute resolution (premium move minus delta × spot move, 2 ticks): it is the brainstorm's own method and
it splits the behind-price adds 54 / 44, but the chain's `delta` is Upstox's and the premium is one minute's last trade. It changes
the words on the screen (floor vs protection), so it should be read beside the straddle / IV for a few forward days before the chip
is trusted.
