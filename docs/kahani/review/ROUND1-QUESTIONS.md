# KAHANI spec — trader's review, round 1: reaction and questions (Fable, 28 Oct 2026, after close)

Read: `docs/superpowers/specs/2026-10-28-kahani-design.md`, NOTEPAD A129–A142, `handshake.py`, `fronts.py` (header), `docs/speed/BUILD-PLAN.md`, `BUILD-PLAN-FABLE.md`, `docs/speed/breakout/export.py`, §1b / §1d / §1r. Nothing edited, nothing under `data/` touched, no secrets opened. Numbers below are from those files: [M] where they were measured there, [I] where I infer. Levels say s / f. Rows, never rates.

---

## 1. First reaction (a desk's)

1. **Yes, a desk would run it, as the one screen for "are the shorts done".** The story is the right unit: a wall fight read as a sequence (DASTAK ×5 · jawab 0 → TOOT → RASAD → KHATAM) is how a desk talks about a squeeze, and nothing on her screen said it on 28 Oct.
2. **Strongest:** RASAD as a RUN rule. KHATAM at 13:02f, 2 min after the 22,875.5f high [M, n = 1], is the first fuel read in this repo that *timed* an extreme instead of describing it. Second: NAHI as a count, never a line.
3. **Weakest, and it decides whether the verdict is worth her phone:** the band verdict is five rows from two days, and in context (b) its two confirming pieces (NEXT PUSH, ULTA PUSH) arrive *after* a typical trigger, so the trigger-time verdict is SAAF NAHI by construction (28 Oct 13:03, 13:15). The verdict confirms the rotation after it started.
4. **Second weakness:** BANKNIFTY and SENSEX have no answer bar, so their fights can never reach TOOT and their verdicts can never reach GHUMEGA in (b). The spec says "fuel + wall only" but not that GHUMEGA is then unreachable.
5. **Third:** the fight's wall (the §1d front ≤ 2 steps ahead) and the push's attacked strike (biggest absolute OI in the band) are two different selections; the DASTAK count can be counting pushes at a different strike from the chapter's wall.
6. **Data truth first is right.** The sleep artifact and the 2–3 min answer lag are bigger than any rule here; the one thing I would measure before anything else is the exchange's OI publish cadence inside the book (Q63), because both the "first crossing" answer and the 3-minute KHATAM clock stand on it.
7. Nothing here touches §1b / §1d / §1r; where a question brushes her definitions I say "hers to sign".

---

## 2. Questions (★ = the answer would change the design)

### A. The handshake: push, answer, timing, who opened

1. ★ The push needs ≥ 10 of the last 30 minutes' |2-min deltas| (NORM 30). So 09:15–09:45 and the 30 min after any restart or hole have **no pushes**, and the day's biggest attacks (28 Oct 09:40–09:50, +1,592 vacuum, hand-read in A134) never become DASTAK. What does the fight show then: DEEWAR forever, or "push padh nahi sakte: 30 min history nahi"?
2. ★ The 2× median normalisation adapts: after a trend afternoon of one-way flow the median rises and pushes go quiet exactly while the hunt runs. What was the DASTAK count on a trend day (1 Oct, 19 Oct) by this rule? If it is 0–1, the (a) DASTAK piece is "?" on the days that hurt.
3. The answer bar max(3L, 4 %) is 5 % of a 57L wall and 15–30 % of a 10–20L wall (the day after expiry, Q68). Is a per-wall floor (no fight on a wall under X L) intended, or is every strike a deewar?
4. ★ The chapter's wall is the §1d front ≤ 2 steps ahead; the push's attacked strike is the biggest absolute OI in spot−½ step … +2 steps. When they differ (22,650s CE biggest in band, 22,700s CE the front), which strike does DASTAK count at, and does the chapter read the answer at the chapter's wall (`answer(..., k=wall)` as `defend` does) or at the attacked one?
5. A push whose +1…+4 chain minutes are missing reads `ans = None` ("?"). Does DASTAK n count it, show it as "·", or drop it? Three sentences applies inside the count.
6. PHANS needs price through 0.3 step at the crossing minute. If price goes through at m+2 and is back under at m+4, the stamp says PHANS forever. Is a chapter ever re-read, or is "stamped once" absolute even against the next chain minute?
7. ★ Un-crossing: an OI step can cross −3L at m+1 and read −1L at m+2 (chain noise or the exchange's publish cadence). The spec stamps TOOT at first crossing. My earlier guard (chip live, stamp when it holds 2 steps or at +4) is not in the spec: dropped on purpose, or should TOOT be a chip until it holds?
8. WHO OPENED uses r0's delta over a 3–4 minute, 30–60 pt move, ignoring gamma and vega. On a breakout the attacked side's IV moves; a +4.3L PE add at 12:49 read WRITERS: was the premium-vs-delta residual bigger than a plausible IV move (say 1 vol pt), or is NAYA FLOOR resting on a 2-tick test? What did the residual measure there [M]?
9. The floor behind a ▲ push at 22,700s CE can be 22,700s **PE** (the same strike, both sides writing = pin / straddle writing). On 28 Oct the NAYA FLOOR was exactly that. Does KAHANI distinguish "both sides writing at one strike" (pin) from "a floor built behind price" (support)? They tell opposite stories for a SELL.
10. The per-push fut leg uses the index's **own** book OI (`handshake.load`), but §5 gives SENSEX NIFTY's fuel. Which one sits on a SENSEX push row and in its RASAD: own (thin, bar 10) or NIFTY's?
11. QUIET = 4 makes an 8-minute buy drive at most 2 pushes. Is the push the right unit of attack, or should a drive (consecutive same-sign minutes ≥ X lots) count as one DASTAK with its total? DASTAK ×5 over 75 min and ×5 over 10 min are different stories.
12. `flow()` is Dext-first, book-fill. When she moves her Dext chart mid-day the source flips D→B inside the 30-min median; are Dext's footprint delta and the quote-rule delta on the same scale per minute [M: the 288–321 same-sign check was sign, not size]? Can a source flip manufacture or hide a push?

### B. The fight and its chapters

13. ★ In a range both walls sit ≤ 2 steps away (12:06: 22,600s / 22,700s CE and 22,600s PE round spot 22,643s). The fight follows "the direction of the last push", so a ▼ push at 12:49 moves the fight to the PE wall and resets the chain, unless it is inside RASAD (then NAYA FLOOR). What is the rule when the ▼ push comes during DASTAK, before any TOOT: new fight (count reset) or a chip on the CE fight?
14. ★ No §1d top-2 front within 2 steps (price mid-range, walls 3+ steps off): no fight. What does the hero show, and what is the verdict's WALL piece then ("?", or the nearest front regardless of distance)?
15. The fight only lives on a §1d top-2 front. A push attacks the biggest OI in its band, which may be a non-front strike (22,750s CE at 12.3L). Those fights are invisible. Was 22,700s PE (the 12:49 floor) a §1d front at 12:49 [M]? If not, NAYA FLOOR already lives off-front and the fight rule is inconsistent with itself.
16. A wall that is already UNWINDING when the fight begins (no push yet) has no chapter: DEEWAR needs BUILDING / STALLED, THAKAN needs DASTAK. Name it, or is it DEEWAR with a "−24L peak se" chip?
17. THAKAN is §1d UNWINDING = ≥ 15 % off peak **and** a falling 15-min slope. 22,700s CE was ~40 % off its peak at 12:06 and read STALLED (slope flat) [M, A136]. So a wall that collapsed and then sat still is "standing" for the WALL piece. Would KAHANI read "off-peak ≥ 15 %" as its own ✗ regardless of slope (a KAHANI definition, §1d untouched), or is that hers to sign? §1d's own text already says the face "names the distance instead".
18. ★ Why do TOOT and PHANS share one chapter? TOOT = the wall is cut (fuel released now). PHANS = writers added **under water** (fuel stored for later; price often gets pulled back first). A desk treats them as opposite near-term stories. Should PHANS be its own chapter (PHANSE), with its own ending?
19. After TOOT the wall can rebuild (22,700s CE +15.4L → +31.7L 13:05–15:00 [M, A139]) — the pin mechanic. Is there a WAPSI (rebuilt) chapter, or does the fight re-open as a new DEEWAR at the same strike after PIN?
20. Two CE fronts unwound together from 10:37–10:39 [M]. The fight holds one wall; "both CE walls unwinding" is the stronger read. Does the chapter carry the second front's state as a chip?
21. A run that starts with no TOOT after it (COVER 12:10–12:11, −775, KHATAM 12:14 [M]) is in the verdict (12:12 FUEL ✗) but in no chapter (RASAD is "after a TOOT"). Does the fight show a run outside RASAD, and under what name?
22. NAYA FLOOR requires WHO = WRITERS. `who` is "?" inside ±2 ticks or with a missing premium. Is a "?" add behind price a chapter ("peeche +4.3L · kaun ?") or nothing? If nothing, the floor's existence depends on a 2-tick test (Q8).

### C. The fuel run rule (w5, KHATAM, direction)

23. ★ What is the OI update cadence inside the 1-second book: how many **distinct** OI values per minute does the futures row show [M]? If the exchange publishes OI in bursts every few minutes, "3 minutes with no new extreme" can be a publish gap, and the first-crossing answer is the publish minute. This decides whether KHATAM is a market fact or a feed fact.
24. ★ A run KHATAMs at minute 3; a new run starts when |w5| ≥ 500 again. The new run's w5 window overlaps the old run's tail, so the old run's last lots are counted again in the new run's start. Is the run's "total lots" from the start minute's OI or from OI(start−5)? On 28 Oct that is the −608 (12:35→12:40) question.
25. Direction = sign of p5 **each minute**, so a run reads ▲ then ▼ as price wiggles inside 5 min (the window flicker, moved from kind to direction). Which direction is stamped: at start, latest, or majority? On a V (FRESH with price down then up), what does the chip say?
26. |p5| < 5 pts = "?". On SENSEX 5 pts is one tick of noise; is the threshold per index? On NIFTY, a run at a pin (price ±5) is "?": a FRESH +2,000 lots at a flat top (the next squeeze's fuel) shows as "fuel ?" and the verdict drops it. Is that intended?
27. Hole rule: a missing minute inside the window → "?". Live, the REST backfill cannot arrive before the server wakes. Is REST fetched on the first pass after the hole is seen, and does it fill 12:55–12:59 retroactively so the run's KHATAM stamp is re-computed (then stamped once at which minute: the true 13:02, or the wake-up minute)?
28. If REST has the same hole (an Upstox outage, not a laptop sleep), does the run stay "?" until a clean 5-min window, or is it KHATAM-by-hole? The spec says never KHATAM; so the fight can sit in RASAD "?" for the rest of the day?
29. ★ Roll week: near-month fut OI unwinds mechanically into the next month for 3–4 sessions before monthly expiry (27 Oct's Oct contract; the server still held it on 28 Oct, A133). Every afternoon then reads COVER. Does RASAD read near-month only, near+next summed, or go "?" from T−3? And the bar: NIFTY lot 65 today (`export.py LOT = 65`) — does `FUT_LOTS` follow the contract's own lot when it changes?
30. The morning: FRESH 09:20–09:53 +9,887 [M]. Is w5(09:20) = OI(09:20) − OI(09:15) legal (the 09:15 minute carries the pre-open)? Where does the first run that is allowed to start, start?
31. Which futures price feeds p5: the book's last LTP in the minute, or the REST 1-min close? They differ by a tick; near the 5-pt cut they differ in sign.
32. BANKNIFTY bar 200 is [I] from one day's 5-min |ΔOI| (A132 note). How many runs a day does the rule give on BANKNIFTY over the recorded days, versus NIFTY's five on 28 Oct? If 15, the bar is a flicker.
33. Confirm the book row's `oi` is the contract's total OI (a level), not a depth quantity, and that `fut_minutes` takes the **last** value of the minute (a late-publish inside the minute moves the whole minute).

### D. The endings (CHAL / PIN / PALAT)

34. ★ CHAL = "a new run in the move's direction". After a COVER ▲ rally, a FRESH ▼ run (new shorts at the top) is neither CHAL nor PALAT nor PIN — it is the classic top. Which ending, or which chapter, names "fresh positions against the move after KHATAM"?
35. PIN's second clause (both top fronts within 1 step and BUILDING / STALLED) is the resting state of every range. Does PIN then end most fights by default, and is a PIN that fires without a single push each way worth a stamp?
36. PALAT reads "an opposite push answered TOOT at the floor behind". The `answer` rule reads the biggest OI in the band, which below a new high is often 22,600s PE, not the 22,700s PE floor. Is PALAT's answer read **at the floor strike** (`k=floor`) like `defend`, or at the attacked strike? If the latter, the floor can break unseen.
37. After PALAT, does a new fight open at the opposite wall already in TOOT (the floor just broke), and does its RASAD read the reversed run? The spec ends the story at PALAT without the next first chapter.
38. The endings are known late (PIN "by 13:30" on 28 Oct, from the 13:26 push's answer). Are they live stamps (a stream line) or evening labels only? If live, what does a trader do with "PIN" 30 minutes after she needed it?
39. A run that never KHATAMs before 15:30 (an expiry-afternoon cover into the close): "KHATAM at close" or open until tomorrow? The ended-fight list needs a close rule.

### E. The band verdict

40. ★ Between ARM and TRIGGER (one to several 3-min bars) answers land and runs change. Is the verdict recomputed every minute (so it flips on screen — the flicker she rejected) or stamped twice only (ARM, TRIGGER) with everything in between invisible?
41. ★ Context (b) lasts 30 min after a TOOT, then (a) returns while the wall that broke and the spent fuel are still the story. Why a 30-min clock and not "until the fight ends (CHAL / PIN / PALAT)"?
42. ★ In (a) FUEL ✓ includes "no live run". On a trend day the pauses between FRESH runs are "no run" → FUEL ✓, WALL STALLED ✓, last push NAHI ✓ → GHUMEGA 3/3 for the fade into the trend. Should the **last** run's direction count against the trade for N minutes after its KHATAM (a cooling rule), or is that a context (c)?
43. After the trigger, a FRESH run in the break's direction = CHAL = the fade is wrong. Does the verdict update live post-trigger (a second line "ab CHALEGA"), or is the wrong-line (l6 in a trade) the only post-trigger voice?
44. ★ In (b), NEXT PUSH is "?" until a push into the new extreme happens, and ULTA PUSH is "?" until the floor is tested. Both come **after** most triggers, so (b) verdicts at the trigger are SAAF NAHI 1/1 by construction (28 Oct 13:03, 13:15 [M]). Should "no push into the extreme for ≥ N min while price sits within 1 step of it" be a soft ✓ (nobody is pushing = exhaustion), with N stated now?
45. ULTA PUSH ✓ is PALAT's own condition: by the time it is ✓ the floor broke and the rotation has started. 27 Oct 12:51 GHUMEGA worked because 12:40 TOOT, 12:44 NAHI and 12:49 ULTA TOOT all came before the trigger [M]. What did the 12:42 **ARM** read by these rules — SAAF NAHI? If so, the ARM verdict is the honest one and the trigger verdict is the late one; say which she is meant to act on.
46. ★ BANKNIFTY / SENSEX: no answer → only FUEL and WALL checkable in (a); only FUEL in (b). GHUMEGA needs 2 ✓, so it is unreachable in (b) and needs both in (a). State it on the face, or let WALL count in (b) for those indices?
47. "GHUMEGA 2/2" with a third piece "?" reads as full agreement. Her rule: checked-and-nothing, could-not-check and not-shown never collapse. Show "2/2 · 1 ?" so the N is honest?
48. "Rotation target: the nearer of NAYA FLOOR / CAP and u1 / VWAP". Her standing word is "the wall ahead, never a target" (trademap l5). Rename? And why the nearer: the nearer is the first obstacle; the rotation she trades runs to VWAP.
49. The wrong-line is "fut OI phir −500/5m" (a new COVER). For a SELL after a cover rally a FRESH ▲ run (new longs) is equally wrong. Is the wrong-line "any run driving against the trade", printed with the sign that matches the direction rule for that side?
50. ★ §1r keeps "the ∓20 stop"; A141's 13:03 SELL had an 8-pt stop (E 22,821f, stop 22,829f) [M]. Which stop is the zone's, and which does the evening score use for "stop-hit"? A right read scored as a loss on a 9-pt poke will retire GHUMEGA for the wrong reason. Add a "max adverse before +30" column?
51. If the ARM verdict is CHALEGA and the trigger still comes, does the Telegram ZONE line carry CHALEGA (a "don't") to her phone? Does she want CHALEGA triggers on the phone at all, or only GHUMEGA / SAAF NAHI with CHALEGA silent?
52. Define the evening column per verdict word before day one: GHUMEGA is "right" when +30 along the fade or when price reached VWAP? CHALEGA when the stop hit or when price cleared the wall by 1 step? State the bar, hers, before rows are read.
53. Zone arms run 4–23 a day per index (BUILD-PLAN-FABLE §7). A verdict at every ARM is 4–23 screen lines per index; 28 Oct NIFTY had ≥ 7 triggers (09:42, 09:54, 10:24, 12:12, 13:03, 13:11, 13:15) [M], already above the 6-per-index Telegram budget. Which six, and does an ARM verdict count against the stream's Float cap (10 non-FLOW lines)?

### F. Indices

54. ★ SENSEX = NIFTY's pushes, SENSEX's walls, no answer bar: its fights stop at DASTAK n forever ("jawab padh nahi sakte"). She trades SENSEX often (1 Oct). Is the SENSEX story worth a tab in that state, or should SENSEX borrow the twin's chapter (NIFTY's TOOT / RASAD) with SENSEX's own walls as the chip, until its bar is set?
55. BANKNIFTY: book-only flow, MIN_PUSH 45 [I], bar 200 [I], no Dext, no marks, no answer bar. Same question; plus its step is 100 (2 steps = 200 pts ≈ 0.4 %, NIFTY 100 pts ≈ 0.44 %): fine, but the ANSWER band in points is set by step, so confirm the band for BNF is not 4 steps by accident.
56. The BNF / SENSEX answer bar "owed from logged rows": how many rows exist (27–28 Oct) [M]? A pure 4 % gives BNF ~0.9L and SENSEX ~0.24L on their median walls; is the option-chain OI for SENSEX granular enough at 0.24L (= 1,200 lots of 20) to cross honestly, or will it be a rounding artefact?
57. Step 6 "do the other indices agree" is a row in the reading order with no rule. Same chapter on the twin within N minutes? Same verdict? One chip "NIFTY TOOT · BNF DASTAK ×3 · SENSEX ?"? On 28 Oct all three made the 13:00 high together [M] — what would the sync chip have read at 12:45?
58. On NIFTY's expiry day SENSEX is not expiring: NIFTY's flow and fuel are pin-driven while SENSEX's walls are normal. Is NIFTY's fuel still SENSEX's fuel that day, or does SENSEX go "fuel ? (NIFTY expiry)"?

### G. Data truth

59. ★ The sleep fix drops the minute after a > 60 s book gap. A 25-min outage leaves < 10 samples in NORM and silences pushes for 30 min after; does the screen say so (three sentences), and does the coverage box name the cause ("laptop soya", from the Windows event) rather than only "book gap 374 s"?
60. Chain holes (oihist lacked 12:55–12:59 [M]): is there any backfill for per-strike option OI, or do answers inside a chain hole stay "?" forever and `fronts.read`'s 15-mark slope run over a gap? What does `fronts.read` do with missing marks today?
61. The lag target "TOOT on screen ≤ 30 s after its chain minute lands": the pass runs once per new minute with a 20 s grace, and a chain minute lands ~63 s after its start, so the structural floor is ~80 s from the OI change, before any load cost. Is the 30 s measured from the chain minute's landing (achievable) or from the push minute (not)? Say which, or the target fails on day one.
62. On wake-up, does the server immediately run the REST backfill for the hole (fut OI and, if any, chain), or wait for the next minute pass? Six minutes of the breakout's last leg were seen by nothing; the first read after wake is the one she will act on.
63. ★ (The same as Q23, asked as data truth.) Measure before building: distinct OI values per minute in the futures book, and the median gap between OI changes. If it is ≥ 60 s, the "first crossing" answer and KHATAM's 3-minute clock are both reading the feed's clock.
64. `flow()` is Dext-first; Dext re-posts a bar as it fills (M1) and the pass has a 20 s grace. Can a half-filled Dext minute be read as the minute's flow before the book's complete minute, and then un-read? Is the book the primary source in KAHANI (the plan's "book is source #1") or Dext (as `flow()` codes)?
65. The replay at restart reproduces "known at", not "shown at" (that lives in `msg_*.jsonl`). Will the kahani log carry both per stamp (`known_m`, `shown_at`) so the evening review can show the lag she lived with?
66. ★ Which price presses the wall: spot (the chain's `spot`, the strike's unit) or fut (the book)? On 28 Oct the basis was +62…+75 [M, A134], more than a step. 22,712f "broke 22,700" while spot was 22,643s mid-box (A136). The 2-step "ahead", the 0.3-step "through" and the DASTAK band all need one declared price, tagged s or f.

### H. Expiry, gaps, news, the open, the last hour, roll

67. ★ Expiry day (NIFTY weekly; SENSEX 29 Oct, tomorrow): ATM walls run 100L+ and after ~14:30 a TOOT is writers closing winners, not being forced (CRITIQUE S10's GAMMA ZONE). Does every chapter and verdict carry the day kind, and is the verdict suppressed or only tagged after 14:30 on the index's own expiry?
68. The day after expiry: near-ATM walls of 10–20L, every strike BUILDING from near zero, no peak to be off (THAKAN impossible), the 3L bar = 15–30 % of the wall (TOOT rare, TIKI / PHANS easy). Does the fight need a minimum wall (X L) to exist, or is every 5L strike a deewar that morning?
69. Gap open (150 pts): price opens 3 steps from yesterday's walls; `fronts` ranks by session-peak, so at 09:16 everything is "BUILDING" from zero. Which wall is the morning fight, and does KAHANI read absolute OI (yesterday's walls still carried) for the first 30 min?
70. ★ The first 30 min have no pushes (Q1) and the day's largest run (FRESH +9,887). The 09:54 SELL (fresh shorts +378 with price −17.8f) went +133 / −10 [M] and reads SAAF NAHI 1/1 (FUEL ✓ alone). Should the open be its own context (c): fuel + 09:15-baseline walls only, with GHUMEGA / CHALEGA allowed on FUEL alone when |run| ≥ 2× bar?
71. A news jhatka (a 100-pt minute): push 10× norm, both sides TOOT, OI drops both ways, p5 = the spike's sign → "TOOT · RASAD cover ▲" reads as a squeeze. Any velocity guard (push > 5× norm = "jhatka", story paused 10 min), and does §1o's day type ride on the chapter?
72. Last hour: CAS freezes spot ~15:15 (CLAUDE.md), the chain stops 15:30, fut trades to 15:40. Spot-based pieces (through, band, s-tags) run on a frozen spot for 15 min. Does KAHANI freeze its spot pieces at 15:15 and carry fuel on fut to 15:40, and does a verdict after 15:00 carry "3 baje ke baad"?
73. Roll week (Q29 again, as operations): which contract is `fut_key` on T−3 … T−1, and on the morning after expiry when the book's `ik` rolls — does the story carry over, or is the run history "?" because the OI series changed contract?

### I. What the trader sees and hears

74. ★ Her standing direction (27 Oct): the read lives ON her chart. The build order puts the GoCharting ribbon last (step 5) and the LADAI tab third. Is the ribbon last because of the line budget (2 flat / 5 in a trade), and could one ribbon line (chapter chip + DASTAK count + fuel arrow) ship at step 3 instead?
75. Stream volume: 2–4 fights × 4–6 chapters + 4–23 ARM verdicts + triggers, × 3 indices = 40–80 lines a day; the Float keeps 10 non-FLOW. KAHANI lines will push ZONE / READ / TRADE lines out. A per-kind cap in the Float, or verdicts at ARM kept off the stream (hero only)?
76. Sound: which KAHANI events may ring, if any — a TOOT at her defending wall in a trade, KHATAM, a verdict? "Two bells a day by construction" is her standing bar for signals.
77. The hero's ABHI line and the two scenario lines: fixed sentences per (chapter × fuel state × side) = ~48 templates, or composed? Who writes them, and is that the "tool, not essay" risk in a new form?
78. Thirteen new Hinglish words (DEEWAR … SAAF NAHI). She cannot remember glyphs (standing). Will every chip carry its number so the word is secondary, and in the ladder's ◆ ✓ / ✗ — ✓ from whose side, the pusher's or the wall's?
79. Colour (light mode): TOOT is good for the pusher and bad for the writer; she is both on different days. Colour by side (CE / PE) rather than good / bad?
80. Replay mode: replays what she **saw** (the logged stamps) or what the **rule** says now (recomputed)? After any fix the two differ; the evening review needs both, side by side.

### J. Anything else, first principles

81. ★ `replay_zone.py` runs "every recorded day's zone3 triggers", but zone3 rows exist only from 28 Oct (§1r: nothing zone3 before). Is the replay one day, or the 1-min `zone` population (a band she no longer trades, never to be pooled)? Which rows feed it?
82. The kill condition for the verdict: after how many rows per word, and what row pattern, retires GHUMEGA (e.g., GHUMEGA rows' +30 along the fade not sitting above SAAF NAHI rows' at 15 per side)? Stated before day one, hers.
83. §6.6.3 says the l6 line is a "WARN line" / "PULLBACK · HOLD line". WARN is a ladder state in `voice.py`. Is it the ladder's word (she reads it as EXIT > WARN) or a line under the ladder with "khatra" / "pullback lagta hai" as today? Name collision.
84. Two fuels on one screen: THE READ's rank-pool fuel ("could not check" all 28 Oct [M]) and KAHANI's RASAD (COVER −2,153). Which does she trust when they differ, and should THE READ's fuel cite RASAD when its own is "?"?
85. In a trade, her defending wall is the fold engine's W; the fight's wall is the §1d front ahead. When they are different strikes, two walls are on screen with two answers. Which one is the fight's when she is in?
86. "Price leaves the wall by > 2 steps without a TOOT = ghoom gaya" also covers price going **through** the wall by 2 steps with no TOOT (writers ran over, under water, never cut). That is not ghoom gaya, it is trapped writers ahead = fuel. A chapter for it (PHANSE, Q18) or an ending?
87. Both-ways expression (standing, 25 Sep): a GHUMEGA on a SELL zone is sell CE at a standing wall, or buy PE when the CE wall is UNWINDING (the squeeze reinflates CE). Does KAHANI's defender read feed the expression pick, or is that §1h's and left alone?
88. The 2-step geometry is 100 pts on NIFTY ≈ a σ3m day's whole range, and 5 minutes on a 2 % day. Is "2 steps" a step count on purpose (hers, strikes) or a stand-in for a σ-scaled distance?
89. §8 test 3 (causality) checks `story(upto=m)` equals the full-day prefix. With REST backfill tagged `rest`, a replay with REST present and a live run without it (not yet fetched) differ by construction. Which is the test's truth, and does the log record which source each fuel minute used?
90. What is the one number a desk would print at the top of the LADAI hero that the spec does not have: the **open shorts under water** [I] (A139: ~10K lots from the morning at 22,570–22,690f, still open at 22,775f). That is the fuel that has not run yet. Is it in scope (it needs a price-at-build ledger for fut OI), or owed?

---

*Round 2 (scenarios and the motion design) after the answers. The scenario work will walk each rule through: trend day, range day, expiry, gap, news minute, open, last hour, roll week, laptop sleep, feed hole, and the BNF / SENSEX no-answer case.*
