# RAFTAAR build plan — Fable's review (28 Oct 2026, morning, before her restart)

Read: her profile + thesis notes, BUILD-PLAN.md, NOTEPAD A128–A130, coil/BRAINSTORM.md, handshake/fable/CRITIQUE.md, DESIGN.md,
oi-lab/README.md, `palat.py` + `server._palat_pass` as they stand this morning (Phase 0, mid-build). One read-only replay was run:
Phase 0's own `palat.py`, unchanged, over the 23 NIFTY days that have P marks (`scratchpad/palat_days.py` → `palat_out.txt`).
Rows, not rates. Nothing edited. Nothing under `data/` or `telegr/` touched.

---

## 0. THE PAGE (act on this; the evidence is below)

| | What | Why (one line) |
|---|---|---|
| **KEEP** | **ZONE alert + din chip** (Phase 0) | one line, already gated from today; `din TREND … fade khatra` is the only chip that would have warned on 1 / 19 Oct |
| **KEEP** | **flow1m + handshake** = THE core | the only read here with a forcing mechanism (push → the wall must answer); oi-lab's two survivors (fut leg, effort) ride on it |
| **KEEP** | fut-OI leg per push (FRESH / COVER / FLAT), WHO OPENED, effort per point | the three qualifiers that give a push a meaning |
| **KEEP** | the `data/raftaar/` forward log, replay-from-record at restart | anytime-start, honestly |
| **CUT** | **coil** | n = 2 coils; 6 of 24 legs started from one; "lean" names the fuel (hunt.py already does) not the timing |
| **CUT** | **shikaar as a module** | it is `hunt.runways` (live in /api/warmap) + `trademap` l5 "the wall ahead" + `levels.py`; at most a 20-line join |
| **CUT** | engine phase lines (SHURU / TEZ / RUKA / PHIR CHAL PADA / THAK / KHATAM) and side events as stamps | they are the 6–20 lines/day she called noise; keep them as face phases only |
| **CUT** | the Speed tab's price × time panel | "no charts, reads only" (standing); she has price on GoCharting |
| **CUT** | a second alert kind tonight (**BAN SAKTA as coded**) | the replay: 42 alerts on 23 days, duplicates, −20σ at the open, and the trend-day losers it was built to block **pass at 3/4 and 4/4** (§2) |
| **ADD** | **the handshake into `voice.py`** (in-trade): push against her + NAHI = PULLBACK · HOLD; TOOT at her defending wall + fut FRESH = INVALIDATION · WARN | her stated problem is holding winners; this is the one read the plan builds and leaves her trade blind to |
| **ADD** | a **per-day Telegram budget** in `telegram_out` (one counter per kind) | today CAP is 6 per MINUTE only; zone arms × 3 indices + palat duplicates can flood her phone |
| **ADD** | the handshake as **one line in the message stream** for ANSWERED pushes only | zero new UI; NAHI stays off the stream |
| **ADD** | morning checklist line: **Dext chart → NIFTY NOV FUT** | the Dext record has NEVER held a Nov future (§4); today the book carries the day unless she moves the chart |
| **CHANGE** | the fut check in palat: **FLAT or COVER passes, FRESH fails** | A129's own words are "fut OI FLAT / COVER"; `palat.py` codes FLAT only, so the 27 Oct 12:45 top reads 3/4 with fut ✗ (−2,860 lots = COVER) |
| **CHANGE** | thakan's "other side wrote ≥ max(3L, 4 %)" clause: **drop it** | it is Y on 102 of 127 rows: a check that cannot be N is not a confirmation and must not count toward 3 |
| **CHANGE** | palat trigger: **the server's running extreme**, the P a chip | the P comes from the extension relay (orphans on reload), NIFTY only (no BNF / SENSEX marks exist), and is "a coin" by A130 |
| **CHANGE ORDER** | 0 ZONE+din → **1 handshake module + voice hook + stream line** → 2 chart overlay (◆ ✓ ✗ + the two absolute walls on the deewar lines) → 3 /api/raftaar with the engine demoted to a context word + palat 0–5 at the running extreme → 4 the tab, hero = handshake v2 (the face she said "yes this is it" to) | most edge per hour, least risk to a live day; the faces she rejected go last |
| **ONE BRAIN** | Phase 1 must **lift** `dext_flow / book_flow / pushes / answer` out of `palat.py` into `handshake.py` and import it back; never a second copy | the §1d lesson: one pure function, one language, or the rule disagrees with itself |

**Build first:** `handshake.py` (lifted from palat.py, ~120 lines already written and replayable) + its forward log + the one line into
`voice.py`. Everything else stands on it.

---

## 1. Where her money comes from → core / nice / noise

Her edge, in her words and the thesis: writers near ATM (top-2 absolute OI per side) get trapped; the trapped side's forced buyback is
the flow; forced flow is the only thing retail can follow; a stop cluster is liquidity. The smallest set of reads that captures that:

| Read | Core? | What it measures of the mechanism |
|---|---|---|
| **flow push** (2-min fut delta ≥ 2× normal) | **core** | the aggression (who is forcing) |
| **OI answer at the attacked absolute-OI strike** (TOOT / PHANS / TIKI / NAHI) | **core** | whether inventory is being forced out (TOOT), built (PHANS), or absorbing (TIKI) |
| **fut-OI leg** (FRESH / COVER / FLAT) | **core** | fresh money vs covering: the one OI read oi-lab kept for timing |
| **WHO OPENED** (writers vs buyers) | core qualifier | a buyer's add is protection, not a wall; fixes "OI up = writers" (wrong about half the time near ATM) |
| **effort per point** | core qualifier | the one order-flow read that survived 291 variants |
| **running extreme + her band** | core context | where the forcing matters (A129: PALAT only at a fresh extreme or u2 / d2) |
| **§1d fronts, §1o day type, THE READ** | already live | the held thesis; RAFTAAR may only disagree with numbers shown |
| engine composition words (CHOP / PIN / ROLL / CHAL RAHA) | **nice** | context across strikes; OI speed alone does not time (oi-lab, 1,982 episodes) and it read ▲ 8/11 at the 27 Oct top |
| engine phases + side events as stamps | **noise** | 6–20 lines a day, the flip noise she rejected twice |
| shikaar | **exists** | hunt.py runways + trademap l5 + levels; a join, not a module |
| coil / lean | **noise** | n = 2; 18 of 24 legs started as a V, not a coil |
| P label | coin | A130; see §2 |

---

## 2. Phase 0 checked against its own code (the replay)

`palat.py` as written this morning, over every NIFTY day with P marks (22 Sep – 27 Oct, 23 days, 127 swing-P rows, 42 alerts).
Send time = close + 2 min (`PALAT_WAIT_S`) = 7 min after the P's bar opened. Points at +15 / +30 / +60 are from the SEND minute,
along the fade. Full rows: `scratchpad/palat_out.txt`.

**The four, as coded, on 127 rows:** zone Y 66 · band Y 45 · **thakan Y 102 / N 7 / ? 18** · fut Y 34. Thakan is near-free because its
second clause (the other side wrote ≥ max(3L, 4 %) at the extreme strike in 10 min) is ordinary ATM writing. So "3 of 4" is in practice
"zone + band + free" — the ZONE alert she already gets, plus a σ chip.

**The rows the plan said it would block, and did not:**

| day · P | n/4 | the four | fut leg | +15 / +30 / +60 |
|---|---|---|---|---|
| 1 Oct 12:30 BOTTOM (A130's loser) | **3/4 ALERT** | zone armed · −2.5σ · push −198 NAHI + call likhai +6.7L · fut ✗ | **FRESH +1,064** | −108 / −103 / −140 |
| 19 Oct 11:45 BOTTOM (A130's loser) | **4/4 ALERT** | zone armed · −2.2σ · call likhai 23,000 +54.4L · fut flat | FLAT +210 | −21 / −64 / −62 |
| 19 Oct 12:20 BOTTOM | 3/4 ALERT | zone armed · −2σ · call likhai +47.4L · fut flat | FLAT +24 | −10 / −36 / −82 |
| 5 Oct 10:30 BOTTOM | 3/4 ALERT | zone trigger · −3σ · push −746 NAHI + call +22.0L | FRESH +365 | −27 / −11 / −21 |
| 5 Oct 11:00 BOTTOM | 3/4 ALERT | zone trigger · −2.6σ · push −261 NAHI | FRESH +343 | −19 / −10 / −90 |
| 24 Sep 13:30 BOTTOM | 4/4 ALERT | zone trigger · −2.9σ · push NAHI + call +7.8L · fut flat | FLAT +133 | −64 / −86 / −56 |
| 6 Oct 10:05 TOP (expiry grind) | 3/4 ALERT | zone trigger · +1.8σ ✗ · push NAHI + put +17.4L · fut flat | FLAT −217 | −10 / −33 / −43 |

**The rows it got right, and what they share:**

| day · P | n/4 | fut leg | +15 / +30 / +60 |
|---|---|---|---|
| 27 Oct 12:45 TOP (her trade) | 3/4 (fut ✗ as coded) | **COVER −2,860** | +28 / +94 / +86 |
| 22 Oct 11:15 TOP | 3/4 | FLAT +37 | +52 / +136 / +172 |
| 22 Oct 10:25 TOP | 3/4 | COVER −1,055 | +39 / +11 / +15 |
| 30 Sep 10:20 TOP | 3/4 | COVER −584 | +51 / +64 / +70 |
| 5 Oct 12:00 / 12:10 BOTTOM | 3/4 · 4/4 | FRESH +540 · FLAT | +37 / +42 / +56 · +19 / +39 / +37 |

Alerts by fut leg, +30 sign (rows): COVER 5 up / 1 down · FLAT 11 up / 7 down · FRESH 10 up / 7 down. Six COVER rows is a hypothesis,
not a finding; but note that **the one leg that leaned the plan's way is the one `palat.py` marks ✗** (FLAT-only). A129's text says
"FLAT / COVER". Code the spec.

**Bugs in Phase 0 as it stands (fix before it reaches her phone):**
1. **Duplicate alerts**: the extension stamps a P on adjacent rows (22 Sep 09:30 ×3, 30 Sep 10:00 / 11:00 / 11:20 / 12:40 / 12:50 ×2).
   `pid` = t + price, so each is a separate SETUP line. Key one alert per (side, bar).
2. **σ at the open**: 22 Sep 09:30 reads **−20.2σ** (three bars of VWAP). Band needs ≥ 6 closed bars (30 min) or says `σ ?`.
3. **fut check**: FLAT-only; A129 says FLAT / COVER (above).
4. **thakan**: the "other side wrote ≥ 3L" clause is free (102 / 127). Keep only the push-answer clause; a row with no push in 15 min is
   `?`, not Y.
5. **The claim in "What I decided"** ("the losing tops / bottoms on trend days had none of them behind it") is false against the code:
   1 Oct 12:30 had three, 19 Oct 11:45 had four.
6. **Latency, say it**: the 27 Oct alert goes at ~12:52 from 22,789; the top was 22,824.5 at 12:43, the zone triggered 12:51 at
   22,784.9. The alert lands with the zone trigger, 36 pts off the top. Log the SEND minute and measure points from it, never from the P.
7. **Volume**: 30 Sep alone would have sent 9 distinct BAN SAKTA lines (14 with duplicates) on top of the zone arms. No day budget exists.
8. **NIFTY only**: `ofd_marks_*` files exist for NIFTY alone; BANKNIFTY / SENSEX cannot alert. The plan does not say so.

**The chip that would have helped on the trend days** is the one the ZONE line already carries from today: `din TREND ▼: price discovery
ho sakti hai · fade khatra` (`messages.din_line`). §1o's log starts 23 Oct, so this is a forward claim, not a measured one.

**Verdict for tonight:** ship the ZONE + din line. Ship BAN SAKTA only with fixes 1–4, keyed per bar, NIFTY only, under a day budget;
otherwise hold it one day and let the ZONE alert carry the σ and fut-leg chips.

---

## 3. Mechanism and kill condition per read (forward; she states the bar before reading)

| Read | Who is forced, why it should work | Falsifier on forward days (rows, ≥ 15 per side before any verdict) |
|---|---|---|
| **push → TOOT** | writers at the attacked absolute-OI strike buy back under aggression; their buyback is the next leg's fuel | TOOT pushes' +15-min points along the push, listed beside the same day's NAHI pushes; if the TOOT column does not sit above the NAHI column on 15 per side, the answer carries nothing |
| **push → PHANS** (add + through) | writers sell into the move and are under water: fuel being built; the next leg has more to cover | the PHANS strike's OI 30 min later: if it is not cut (no buyback) on most rows, "fuel" was not fuel |
| **push → TIKI** (add + held) | the wall absorbed; the pusher is the one trapped | points against the push at +15; if they do not show, TIKI is just a slow TOOT |
| **fut leg COVER at an extreme** | a covering-only rally runs out when the shorts are done (oi-lab's surviving read) | extremes with COVER vs FRESH, held / broken at +30, as rows per side |
| **WHO OPENED = buyers behind price** | protection, not a floor: nobody must defend it | buyer-opened "floors" broken within 30 min vs writer-opened; if they break alike, the chip is noise |
| **effort ≥ 2× at an extreme** | lots of OI / flow per point = absorbing; price is being paid for | oi-lab's pass bar (effort.PASS_BAR) stands |
| **PALAT at a running extreme** (A129's 0–5) | the last same-side push answered by heavy covering + fut COVER, then the next push NAHI, then the first opposite push answered | the five counted per extreme; extremes that held vs broke at +30, per count value, rows per side |
| **engine ≠ READ** | a young, big, moving, OI-backed leg THE READ has not seen | 15 lines; +30 points per line; both survivors came with a TOOT inside 3 min: a line without one is dead at 15 |
| **COIL** | — (cut) | — |

---

## 4. What a desk would not trade without, against this plan

| Desk input | In the plan? | Verdict |
|---|---|---|
| **Gamma / dealer positioning** | no | correct to leave out: oi-lab found signed GEX / vanna / charm noise for India; `gamma.py` exists if ever wanted. ONE chip matters: **GAMMA ZONE after 14:30 on the index's own expiry** (CRITIQUE S10): answers there are pin mechanics, not walls. Add the chip to the handshake line; the engine already refuses ≠ on expiry. |
| **IV and skew at extremes** | only inside coil (cut) and WHO OPENED | keep ONE number in the header: the **ATM straddle** per minute (it is her premium when she sells ATM; it is in the chain already). Straddle falling in a chop = her sale working; popping on a push = buyers chasing. No module. |
| **Time of day, expiry** | day parts in the engine's reference; S2 | right. Add the day kind to every push line on expiry (S2: an answered push is not continuation on expiry / grind days: 6 Oct, 19 Oct). The 15:00 reminder stays a reminder. |
| **Cross-index lead-lag** | a grade check | enough. Her words: "in sync = real". The handshake is NIFTY-flow only (BNF: book; SENSEX: NIFTY's flow + own OI, §1q): show the three indices' last answer side by side in the stream, nothing more. |
| **Futures basis** | 3-min median (A60) | right. The palat line prints `P 22,840f` and `zone 22,820s` on one line: carry both units on the alert (standing rule: key levels say both). |
| **Bid / ask and depth at her strikes** | no | not a hold / fold input of hers; trading is free and she posts. The one upgrade it buys: **option trades at bid / ask = WHO OPENED measured, not inferred** (the CRITIQUE's least-sure test). Upstox `full` on the nine × 3 indices is the path (oi-lab's open item). Defer; name it. |
| **How she exits** | **absent** | the plan's biggest hole. Her hold / fold is ZONE · ORDER FLOW · OI · VPIN behind her; her problem is holding through pullbacks. The handshake IS the pullback-vs-invalidation test she asked for on 28 Sep: a push against her with NO answer at her defending wall = PULLBACK (HOLD, say so); a TOOT at her wall with fut FRESH against her = somebody gave up (WARN). One line into `voice.py`'s ladder (WARN rules), display only, keeps rev 6 / §1m untouched. |
| **VPIN** | not mentioned | leave on its kill clock; it is already one of her four. |

---

## 5. Phase order

The plan's order puts the server engine (Phase 1, 1,165 lines, 3 engines in lockstep at restart) before anything reaches her chart,
and the tab (a face she rejected three times) before the overlay (her standing direction, 27 Oct). Edge per hour, least live-day risk:

| # | Build | Touches | Her risk |
|---|---|---|---|
| 0 | ZONE + din on Telegram; BAN SAKTA only fixed (§2) | messages / palat | notification |
| **1** | **`handshake.py` lifted from palat.py** (flow1m inside it: Dext near month, else the book) · forward log `data/raftaar/hs_<day>.jsonl` (push, answer, who, fut leg, effort, sources, +15 / +30 filled later) · **one stream line per ANSWERED push** · **the voice.py hook** | server; her restart after close | one module, replayable from the record (palat.load already does it) |
| 2 | chart overlay: ◆ at the push bar → ✓ / ✗ at the answer; the two **absolute** walls re-tag the deewar lines (S5); the n/5 chip at an extreme | extension build + reload | reload orphans the relay (F5): do it after close, verify the next morning |
| 3 | `/api/raftaar`: the engine demoted (CHOP / PIN / CHAL RAHA / ? + ROLL as the context word; phases on the face only; ≠ gated by an answered push); **palat 0–5 at the running extreme** replaces the P alert; shikaar = `hunt.runways` + levels joined in, no module | server; restart | engine words change: replay all days first (the plan says so) |
| 4 | the tab, if still wanted: hero = handshake v2 (strike map + three flow strips + the chain); picture word as a chip; **no price × time panel** | UI only | none |
| — | coil | cut | — |

Restart-safe lockstep replay (DESIGN §9a) is right and is the cost of the anytime-start rule; it is Phase-3 risk now, not Phase-1.

---

## 6. "What I decided as the trader" — agree / disagree

| Decision | Verdict | Reason |
|---|---|---|
| Real time over confirmation | **agree, with one guard** | an answer "the first minute it crosses its bar" is one ~63-s OI step; a step can un-cross. Show it live as a chip; **stamp** it when it holds 2 steps or at +4 min. GoCharting's 5-min bar is never a wait. |
| A push with no OI answer blocks breakout lines | **agree** (my gating answer) | required, not sufficient: 2 right lines had a TOOT, 4 of 7 wrong had none, 3 wrong had one. Keep young-leg / moving-minute / no-expiry. n = 2 / 7. |
| Floors only when writers opened them | **agree on mechanism, hold the word** | a buyer's add is protection and needs no defence. The 1-min premium-vs-delta test is the least-sure piece (54 / 44 / 3): print `writers` / `kharidar` / `?` as a label for forward days before it changes "NAYA FLOOR" to anything stronger. |
| The P label alone is a coin | **agree; the fix as coded is not a fix** | §2: the 3-of-4 passes the trend-day losers; one of the four is free; the source is the extension relay, NIFTY only. Trigger on the server's running extreme; the P is a chip. |
| Grades stay counts | **agree, one rule added** | a check that cannot be N (thakan's write clause, 102 / 127) is not a check and does not count. N must only include checks that were N somewhere on the record. |

---

## 7. Traps

| Trap | Where it bites here | What to do |
|---|---|---|
| **Overfitting to 11 days** | the ≠ gate went **14 → 2 lines by six rules fitted to the same days** (DESIGN §6); ~50 decimal constants in `final/raftaar.py`; the ½-leg CHOP rule and the no-≠-on-expiry rule were each chosen on the days that broke the literal rule | freeze the constants in a dated file, log every line forward, judge at 15 per side; demote the engine until then (§5 Phase 3) |
| **Too many alerts** | zone arms: NIFTY 4–23, BNF 2–23, SENSEX 6–31 trigger_log rows a day (19–27 Oct); 30 Sep: 9 BAN SAKTA lines; CAP is per minute | per-day budget per kind in `telegram_out`; ZONE sends on ARMED → MATCH per episode only (A116 already); BAN SAKTA one per bar |
| **One voice vs many screens** | palat.py carries its own handshake; Phase 1 builds another; the tab, the overlay and Telegram would each re-word it | one `handshake.py`, one JSON, faces render verbatim (the voice.py pattern) |
| **Restart / replay** | three engines + READ word + fut book in lockstep from 09:15 at every restart | the handshake replays from the record in ~2 s (measured: `palat.load` 0.4–3.0 s a day). The engine's replay is Phase 3. Never re-read 9-MB book files per pass once per pending P for 6 min (`_palat_pass` does: load is called every 20 s while a P waits) — cache per minute. |
| **Data dying mid-day** | Dext blank from **12:02** on 27 Oct (167 minutes with volume), 14–15 Oct whole days; 22–25 Sep carried entirely by the book; **no Nov future ever posted** (see below); the P mark dies with the extension relay | the book is source #1 (1-s, quote rule, validated 288–321 same-sign per minute); Dext is #2; GoCharting #3. Say `sources n/3` with the book first. `/api/health` names the dead one. |

**Correction to my CRITIQUE M2 (28 Oct 00:10):** `data/dext/instruments.json` says **NSE-2885 = RELIANCE** (equity) and **NSE-51345 =
NIFTY 27 OCT 22800 PUT**, not the Sep and Nov futures. The fix stands (near month only, never sum; 48704 was the Oct future), the
"roll cross" story was wrong: 21 Oct's 168M was the put's volume. Consequence for today: the Oct future expired yesterday; the book's
`ik` is now the Nov future and `palat.load` will look for `dext_NSE-<Nov token>_2026-10-28.jsonl`, which exists only if her Dext chart
is on NIFTY NOV FUT. Otherwise the book carries the whole day (it can: 22–25 Sep). Put it on her morning checklist.

---

## 8. Smaller points

- `palat.py` reads `oi_chg`-free absolute OI (A125): right.
- `MIN_PUSH` BANKNIFTY 45 is [I] off three days; BNF has no Dext and no marks: the alert is NIFTY-only today whatever the loop says.
- The plan's "sources agree per minute on Dext + the book" needs the book's quote-rule delta per minute, which `book_flow` already
  computes; agreement = same sign, printed as `2/2` or `1/2`, never a named outlier (S1).
- `SAHMATI` as `round(100 × agreeing ÷ checkable)` (Opus v3) is a percentage on the face; the plan says counts. Keep `8/10`.
- The Opus v3 FUEL basis (VWAP when the record starts late) marks almost every CALL losing; the live server must track sale prices from
  09:15 (`trapped_inventory` does) or print `fuel ?` with the reason.
- Telegram "≤ 6 lines per index per day" is a sentence in the plan, not code.

**Least sure of:** the COVER rows (six) and the pullback-vs-invalidation hook (no forward row yet). Both are to be logged, not believed.
