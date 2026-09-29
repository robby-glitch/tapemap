# The professional tool: Fable's blueprint

**Written:** 2026-09-28, after the close. Read-only: nothing edited, started or posted.
**Chair:** twenty years in NIFTY / SENSEX options, building the tool I would hand my son.
**Read:** redesign A–H (H-changes-v3 included), TRADER-AUDIT (its correction first), PONYTAIL-REVIEW, BUGFIX-2026-09-28, her doctrine files, and the code behind every claim I make.
**Replayed, read-only:** `scratchpad/fb/reader7.py` (H's `reader6.py` with two trader variants added) on 8 trades over 5 recorded days, 22–28 Sep. Tags: [M] measured, [I] inferred, (h) hand-picked.

---

## 0. The answer in six lines

1. **One engine, `fold.py`, for the Validate tab and the GoCharting panel.** It is H v3 (fights on a volume clock, a frozen give-up, her wall's OI event, acceptance not touch), plus three things a professional does that v3 does not: **fold on location alone when the breach is held**, **name the wall she played for**, **show what she has given back**.
2. **Her hold/fold is four reads and one word.** ZONE · FLOW · OI · VPIN as chips; the word is BEHIND YOU / PULLBACK / TIRING / AT THE WALL / FAILED / PAST GIVE-UP / GAVE UP. Only GAVE UP sounds, once.
3. **No GO / WAIT / NO.** Direction is hers. Before entry the tool shows the same face for "if you enter now": the four reads, the give-up it would set, the premium there, the room to the wall ahead. It refuses (NO) for one reason only: the room ahead is less than the give-up behind.
4. **One screen for the day (DESK), one for OI over time (WAR), one for the record.** Eleven tabs go.
5. **Moneyness, ATM and walls are read against the options' own forward, everywhere.** One wall rule (the plan rung's) replaces five.
6. **Nothing changes a signed rule without her signature:** rev 5, VALIDATE 2, EXPRESSION e and PLAN 3 close as they stand; §9 is the one amendment.

---

## 1. The trader's day, and the screen that answers each moment

| moment | what a pro needs, in one glance | screen |
|---|---|---|
| **Pre-open (08:45–09:15)** | Yesterday's close, high, low, POC. The two biggest OTM walls each side of the forward, carried from yesterday's last snapshot. Expiry today? Roll today? Feeds alive? | DESK · FLAT, header + THE DAY |
| **The open (09:15–09:30)** | Which side is trapped by the gap [I]. The first fight and who won it. Chain, book and VPIN reading from their first mark: "n of 5 bars" never "blind until 09:35". | DESK · FLAT |
| **Flat** | "Next fight: 22901 above · 22885 below", what each level is, what would confirm a put or a call there, VPIN now. | DESK · FLAT (§4) |
| **Entering** | The four reads at this level, the give-up the engine would set and the premium there, room to the wall ahead and the premium there, buy or sell the other side. | DESK · IF YOU ENTER NOW (§3) |
| **In a trade** | The word. The give-up price and P&L at it. The four chips. What the newest fight did. The wall she played for and whether its writers are still there. Given back since the peak. | DESK · IN A TRADE, and the extension panel (§2, §5) |
| **Exiting** | GAVE UP with the reason and the two facts behind it, or AT THE WALL · holding. Never a size. | same |
| **After a trade** | Who is trapped now and where, the new next fight, the trade's word history. | DESK · FLAT / AFTER A MOVE, RECORD |
| **End of day** | Her marked trades with the engine's words beside them; nothing scored, nothing rated. | RECORD |
| **Any time** | When did each wall get built, is it still held, which front is retreating. | WAR |

**Cuts, by moment.** Glass (a launcher for tabs that go), Heat (spike radar: no moment above needs it), Tape (the 09-19 spec already called it a fossil), Flow (a time-axis chart of events: her broker chart shows this), Chain (the 40-strike dump the seller doctrine excludes), OI Flow (merges into WAR), Map (levels on a ruler: DESK's 3+3 levels replace it), Events (merges into RECORD), Board rev 3 (its regime / trapped / plays lines become DESK-FLAT's line one and THE DAY), VPIN tab (the chip and one detail line replace it; the gauge's forward log continues unseen), Trade (hidden from the strip; the chart files stay by her order). Nine of App.tsx's fourteen tabs answer no moment.

---

## 2. The exit / hold decision, as a professional makes it

### 2.1 What I check before I change my mind

I entered at a level for a reason: a floor that absorbed, writers loading under it, initiative flow my way. Before I fold I ask, in this order:

1. **Has price been accepted beyond the point where I am wrong?** Not touched: accepted. A stop-run touches; a real breach trades there for a while.
2. **At the level, is the flow against me initiative or absorbed?** Sellers hitting my floor and price not following is a pullback. Sellers hitting it and price following is the other side winning.
3. **Did the side defending me give up after I entered?** The wall that sets my give-up: is its OI still building, has it stopped, or is it off its peak by more than that strike's own noise? Only after entry counts; a peak from 10:20 says nothing about a trade taken at 10:40.
4. **Am I at the wall I played for, and is it holding?** Price at the wall ahead with its writers adding is where professionals bank. The wall giving way is the next leg.
5. **Is the tape tiring?** No new extreme my way, no fight won by me, for a full window. Tiring is not an exit; it lowers what I expect and tightens my give-up.
6. **Is informed flow with me?** VPIN, signed, from the same fills the ladder books.
7. **How much of the open profit have I given back, and what time is it?** Past 14:30 on expiry eve the premium bleeds; she is flat by 15:00.

Her sentence — "somebody gave up and OI stopped building or off from the peak" — is checks 1+3. Checks 2, 4, 5, 7 are what stop a pro from folding a winner on one red candle, and from sitting in a loser waiting for OI to agree.

### 2.2 The engine: `fold.py` (rev 6), one instance per marked trade

**Clock and noise (H §3, kept).** Bucket = 3 (h) × pooled median 1-minute volume over ≤ 5 prior sessions. B = today's median 1-minute range so far. θ = 2B (a full swing), w = B/2 (noise). Every threshold below is a count on the volume clock, a ratio, a multiple of B, or a multiple of the strike's own OI noise — never points, lots or lakhs, so NIFTY, BANKNIFTY and SENSEX run the same code.

**Fights, levels, traps (H §4).** One-sided bucket = sure imbalance ≥ ½ and |b − s| > 2G (G the guessed volume). A sweep with G > ½ is signed by price only if |Δp| ≥ θ, tagged "by price [I]". Fights fix on the next bucket of another kind; words change only on fixed fights.

**The give-up G (H §7.2).** Seeded at the mark from the newest fight her side won (winners' VWAP + θ, pushed w beyond the farthest level of hers), else the defending wall + w. Re-set only when her side wins. Locked once touched: it tightens, never loosens.

**Her wall W (H §6.1).** The defending-side strike with the most OI between the forward and G, chosen only when G is set, so it cannot hop.

**The OI event (H §6.2).** On W, after entry: drop from the since-entry peak ≥ 3σ√n, σ = 1.4826 × median |ΔOI| over the 15 updates before the peak. Withdrawn when W rebuilds above that peak or her side sets a new G. Its known ceiling, stated on the face: a slow bleed never fires.

**Acceptance (H §7.3).** One bucket of business at or beyond G over at least the median bucket duration, no print w back inside. A print w back inside withdraws it.

**Three trader additions, replay-checked:**

| addition | rule | why | evidence (`scratchpad/fb/*.txt`) |
|---|---|---|---|
| **A. Held breach folds alone** | An acceptance that stands **2 (h) more bucket closes and ≥ 2 × the median bucket duration**, with no win by her side and no print w back inside → GAVE UP · location. | Check 1. A loser is wrong on location; a pro does not wait for OI to agree. The time floor keeps a fast open (two buckets in 40 s) from folding on a flush. | 28 Sep call: **10:18 at −25%** (v3: no fold, −61% at 15:00). 22 Sep put: the 11:28 flow whipsaw is not taken (withdrawn in 2 min); held fires 14:24 at +70% (flow+OI: +77%). 24 Sep put: 14:39 at +98% (flow+OI 14:56 at +81%). Her put: never; +71% at 15:00. 25 Sep put +7% (same), 25 Sep call −21% (v3 −19%), 23 Sep −14% (v3 −12%). |
| **B. AT THE WALL** | Business within θ of the wall ahead A (the §1d wall on the far side, in futures terms) for 2 bucket closes. Clause: **holding** (A building or stopped) or **giving** (A off its peak). Leaves at 2 closes beyond θ. No sound. | Check 4: the level she played for, named, with its defenders' state. | Her put: at 22850 PE 10:42–13:16, **giving** all along [M]; it broke at 14:28 and the put went to 236.95. 28 Sep call: at 22900 CE 10:27–11:41 **holding**: the lid held and the call died. 24 Sep: at 23200 PE 13:05–13:25 holding, then it broke. So it is a fact and a word, never a fold. |
| **C. Given back** | Line: "peak +92% 14:38 · now +71%", from chain LTP [M]. | Check 7. No rule reads it. | Her put: peak +92% at 14:38, +71% at 15:00. |

**Precedence of the word:** GAVE UP > PAST GIVE-UP > FAILED LOW/HIGH > PULLBACK > AT THE WALL > TIRING > BEHIND YOU > NO READ. Words are computed once per event batch, so none lives for zero seconds.

| word | what moves it | style · sound |
|---|---|---|
| **BEHIND YOU** | her side won the newest fixed fight | ink · none |
| **PULLBACK · since hh:mm** | the other side won it, G not accepted; names what they did and where | amber tint · none |
| **AT THE WALL · holding / giving** | business within θ of the wall ahead, 2 closes | ink, clause amber · none |
| **TIRING · n min** | 2 stalled closes (no new extreme ≥ w her way, no win) in a 5-bucket window; out after 2 | amber clause · none |
| **FAILED LOW / HIGH** | a new extreme ≥ w beyond the old, in no bucket one-sided her way, rejected ≥ w within one bucket | ink · none |
| **PAST GIVE-UP** | G accepted; neither the OI event nor the hold has come | amber · none |
| **GAVE UP · flow + OI / location · hh:mm** | acceptance and a live OI event in one epoch, or a held acceptance (A) | ink block · two low tones, once per epoch |

**The four chips** (H §2, kept): ZONE (nearest strong level behind her is hers / trading within w of the other side's), FLOW (fights only), OI (W building / off-peak event / stopped), VPIN (10 buckets, lead ≥ 2 in, crossing 0 out). Event-born changes show at once; condition-born ones need 2 bucket closes.

**Trailing and banking, in words on the face, never in size:** G steps only on wins. AT THE WALL · holding prints "pros bank into a holding wall". A writer runs the same engine with d flipped; her short strike against the forward is always a level.

**Falsifiers, logged and scored at 30 sessions, never shown as rates:** a fold is noise if trading comes back through G by w within 20 min or W rebuilds above the event's peak within 20 min; PULLBACK wrong if G is reached; TIRING / FAILED wrong on a new extreme by θ.

**Does it hold a winner through a pullback and not hand most of one back?** Her put (28 Sep): held through the 09:48–10:17 pullback and the 11:56 failed low, no fold, +71% at 15:00 of a +97% best. 24 Sep trend: +98% of +154%. 22 Sep expiry put: +70% of +264% (the top was a 14:00 spike that reversed within minutes; nothing live holds that). The losers: −25%, −21%, −14%, −45% (22 Sep call, a −61% low). Eight trades describe; they do not rank. The forward log ranks.

---

## 3. Entry

**No GO / WAIT / NO word.** She said direction is never her problem, and VALIDATE rev 2's word was decided by the line and the trend, the two inputs she does not use. The entry check is the in-trade face run for a trade not yet marked, headed IF YOU ENTER NOW:

- the four chips at this level, each with its sentence;
- **give-up:** where G would sit and why (which fight, which wall), and the premium there [I] as her P&L;
- **room:** the wall ahead in futures terms, its OI and state, the premium there [I];
- **what falsifies it:** "wrong if 22925 is accepted and 22900 CE comes off its peak";
- **premium / theta:** her strike's premium against its own day VWAP (σ, printed, never counted), days to expiry, "expiry eve" flag.

**The one refusal:** NO when the room to the wall ahead is less than the distance to G, or when no level defends her (G cannot be set). Both are [M] point distances; a professional does not buy a 15-point target against a 40-point give-up.

**The expression (buy the option, or sell the other side) is kept and simplified:** BUY when the newest fight her way was INITIATIVE (a pushed fight; the buyer wants gamma and a move). SELL the opposite side ATM when both walls are building and VPIN is quiet (a box; the seller wants theta), unless R2 (never sell into a squeeze) or R4 (never sell a bid straddle) refuses. ROOM and REGIME come out with the line and the trend; the read runs every minute on her strike against the forward, not at 3-minute closes on the chain's spot.

---

## 4. Flat

Line one: **"Next fight: 22901 above · 22885 below"**, the two nearest strong levels (walls, held levels, trapped shelves, the prior day) with hysteresis w. Within w of one: "At 22899 (22900 CE wall) · 22919 above · 22885 below".
Rows: ZONE what each level is and what lies beyond; FLOW what confirms which trade ("above: buyers absorbed again confirms a put; pushed through, a call"); OI the wall at or behind each level in state words with the time it was named; VPIN as in a trade.
AFTER A MOVE: from a trap's birth until the next fight is fixed: the nearest shelf each side, the newest marked new, lots trapped.
THE DAY: one paragraph, ≤ 6 numbers: fights won by each side, value migration, the box, unreleased shelves. Expiry-day and roll-day lines live here.

---

## 5. The faces

**One frame, both screens.** The Validate tab becomes DESK; the extension panel is the same five blocks at 400 px. Both read one poller (`hold/store.ts` today; `/api/hold?id=` and the `fold` object inside `/api/frame`), so they cannot disagree.

```
│ NIFTY OCT FUT · read 11:42ᴹ · chart: placed   │ header, feeds, chart trust
│ long 23000 PE · 120.4 · 09:30   [ I'M OUT ]   │ her trade, or MARK TRADE
│ AT THE WALL · giving   ZONE▪ FLOW▫ OI▫ VPIN▫  │ line one: word + 4 chips
│ gives up above 22925 · at it ≈ 136 (+13%)     │ line two: G, P&L at G
│ PE 174.7 (+45%) · peak +46% 11:14 · flat by 15:00 │ premium, given back, her practice
│ 22850 PE, the wall you played for: writers    │ line three: why the word
│   leaving since 10:42 (−12.3L off peak) [M]   │
│ ZONE · FLOW · OI · VPIN  one sentence each    │ four rows, fixed height, one tag per row
│ THE DAY  one paragraph                        │
│ ▸ detail                                      │ lists only; stays open once opened
```

**Budgets (hard):** ≤ 24 numbers with detail closed; 5 colours (blue helps buyers, red helps sellers, amber watch, ink hers, grey reference/absence); 5 fixed blocks; ≤ 480 px above detail; 3 + 3 levels on the chart; 7 glyphs; one sound per event id, kept across reloads.
**No flicker:** events frozen at birth (price, side, time, words never change); condition-born chips 2 closes; a named wall stays until a new choice holds 2 closes or the forward is w through it; the give-up is a staircase that steps on wins only.
**Marks on the chart (D §4, kept):** ▲▼ pushed, △▽ pressing, ▬ absorbed, ●/○ trapped/released, ‖ tiring, ▸ her entry, solid coloured level lines, dotted reference lines, dashed give-up staircase. Placed once from the event log at event time and price; F5 redraws identical marks; a 5 px glyph floor at 6 px/bar, nothing removed at any zoom.
**Chart trust:** price fit, time fit, fitted date = feed date, fitted latest bar = feed's within one bar, **and bar OI = TapeMap's future OI** (contract match). Any failure: one amber line "chart position not trusted since hh:mm; marks paused, panel live". All marks pause together.
**Mark my trade, both screens:** Mark trade → CE/PE → MARK (ITM/SHORT one more click); the entry premium is frozen when the row opens; strike steps read the same frozen snapshot. Restarts never lose it (`/api/hold/trades`, `data/day_state/`).
**Light only. No candle words anywhere.** "flat by 15:00" is a reminder line, never a rule.

---

## 6. What to remove, and what is missing

### 6.1 Remove (as a trader, with the reason)

| what | where | why |
|---|---|---|
| The session-high line, 3-min close, Noise B | `hold.py` line(), rev 5 B | She exits on levels, flow, OI, VPIN; never a close. It also drove Room, Cushion, the plan's ₹ risk. |
| Trend as a fold family and as WATCH | `hold.py` trend(), `trendbox` in hold/validate/expression | Not one of her four; the 1h row at 09:30 is yesterday. |
| The quiet clock (rule 5), PERSIST = 3, the FOLD latch and heal | `hold.py` | Time rules and lag on top of a lagging read; the latch froze a wrong FOLD all day on 28 Sep. |
| 15-mark OI warm-up, 4-bar flow warm-up, 3-min expression cadence | `fronts.py`, `grounds.py`, `expression.py`, server | Everything reads live from its first mark, "n of 5". |
| Five wall rules | fade gate, board.nearer, board headline, plan rung, expression WALL | One rule: the nearer of the top two OTM strikes by day-high OI beyond the forward by w. |
| Spot as the moneyness reference | `board.itm/nearer`, plan, hold ITM/OTM, expression ATM | Off by 35–45 pts (28 Sep) [M]; the forward is strike + CE − PE. |
| GO / WAIT / NO, the Room and Paying facts | `validate.py` | §3. |
| `gate.py` (always PATA NAHI), `senses`/`ivrv` None fields, the ballot, `watch.py`, breadth footer, ROUND, both WRONG IFs, the event strip, σ bands drawn flat | frame.py, panel.js, overlay.js | Fields that can never fill, or duplicate her chart. |
| The tabs named in §1 | `App.tsx` | No moment needs them. |
| `/api/calls` as a screen | grounds.py, calls_log | Its subject, the engine's event stream, is on the dead list. The forward log rows stay. |
| `runs.py`'s name for fights | | `runs` already means three big fills; fights are fights. |

Kept by her order and untouched: Dhan/Upstox fallback, `structure.py`, `band_rotation.py`, `contract_pair.py`, the Trade chart files, `/api/surface`, `/api/drag`, `/api/paper_fill`, the zone's 09:25 anchor, `trigger_log.jsonl`.

### 6.2 Missing, that a professional would demand

1. **Resting liquidity at the give-up and at the wall ahead.** The book rows already carry five levels each side (`b`, `a` in `book_NIFTY_*.jsonl`) [M]. Read: offers stacked or pulled within w of G and of A over the last bucket ("offers at 22925 pulled 3× this bucket"). The best give-up tell on Bookmap; nothing here reads it.
2. **Big prints by size [M], side [I].** A fill ≥ the 99th percentile of today's fill sizes so far, at a level, with its side if the ladder signed it. One line in FLOW.
3. **Failed auction / excess** at a day extreme: a new extreme in a two-sided bucket, back inside by w within a bucket. FAILED LOW already covers this in a trade; add it to FLAT.
4. **The roll and expiry** (§7).
5. **SENSEX policy:** its future prints a median 7–10 lots per 5-min bar [M]. FLOW and VPIN read CAN'T CHECK with the lot count; no fights, no traps; ZONE and OI as NIFTY; in a trade the word is NO FLOW READ or GAVE UP (OI + held location by the future's own thin bucket, flagged). It never borrows NIFTY's tape.
6. **The tick post from GoCharting** (`adapter.js:133-151` has sides) so the second-tape rule is causal, and **tape agreement** printed in THE DAY detail.
7. **A persisted event log** `data/fold/events_<IDX>_<day>.jsonl` with every threshold in force, so a restart replays to byte-equal state.

---

## 7. Data truth

| defect | how the design handles it |
|---|---|
| **Spot vs forward:** the chain's spot prints 20–45 pts under strike + CE − PE (09-24: 23233 v 23268; 09-28: 22835 v 22880) [M] | Forward\* = future − 15-min median basis over strikes with \|Δ\| > 0.3, everywhere moneyness, ATM or a wall is judged. The chain's `spot` is never a reference. |
| **Guessed-side volume 24–59%** of lots (36% on 28 Sep) [M] | The one-sided bound \|b − s\| > 2G; sweeps signed by price only at θ; the side tagged [I], the price [M]; "could not check: n of 270 guessed" when neither holds. |
| **Three tapes disagree** (ladder, VPIN tick rule, GoCharting: 63–65% bar-sign agreement) [M] | VPIN is fed from the ladder's fills, not a second classifier. GoCharting's tick sides are posted and used only to dispute a fight (withhold the side, let price decide). Kill: > 1 fight in 3 disputed over 30 sessions → FLOW stops printing sides. |
| **Book starts 09:17** (09:17:01 on 09-24, 09:17:19 on 09-28) [M]; chain's first mark 09:17 [M] | Subscribe before 09:15; centre strikes on the previous close. Until built: the open reads "blind before 09:17:19, 1,639 lots unseen", and the 09:15 bar is never scored. |
| **The futures roll 09-29 → Oct** | The date filter is in (BUGFIX #6). Bucket, B and prior-day levels come from the Oct future's own 09-29 record, which the recorder must write on the front month's expiry day; until then, Oct's first 15 minutes (h), flagged, and prior-day levels "could not check", never Sep's shifted by carry. Every chain, book, ux and VPIN row gets an `expiry` / `instrument_key` stamp; no tail is carried across two contracts. `fut_oi` breadth is blind for the near contract in expiry week. |
| **Expiry day** (09-29 is NIFTY weekly + Sep future + BANKNIFTY monthly) | The OI event runs on the expiring series against its own closing pace (σ from its own recent updates); the OI row says so. The next weekly chain is recorded on expiry days so the walls ahead can be read there. |
| **OI baseline = the 09:15 candle**, hiding the gap's covering (28 Sep: 23100 PE −26L) [M] | Baseline = the previous session's last snapshot, same expiry only; else the 09:15 candle, and it says so. A missing baseline is "could not check", never 0. |
| **Rows 2 minutes late** (REST 1-min candle) [M] | The 1-minute index candle is built from the socket's ticks; REST reconciles later, tagged. |
| **fit.js session jump:** with no date tick every loaded day is a candidate (`fit.js:191-198`) [M] | A time fit needs a date tick or a single loaded day; otherwise not trusted. Plus the contract match (bar OI = future OI). One test: a chart with no date tick whose margin time exists on Friday must show "not trusted", not Friday's marks. |
| **Restart** | Replay the event log and `data/book` from the last logged event with the same code; the test diffs a whole rebuilt day against the live log. |

---

## 8. Build order (nothing in market hours; she starts the server; commits on her word)

**Phase 0 — done today, live at her restart:** BUGFIX #1–6 (rank, ladder minute, [I] tags, "adding again", "paid", the expired-future filter). Before Wednesday's open nothing else touches the live path.

**Phase 1 — the engine and the amendment (this week, after close).** `fold.py` (pure, stdlib, fixture-first from `scratchpad/fb/reader7.py`), `fold_log.py` (the event log), `/api/hold?id=` served from it, `fold` inside `/api/frame`. Rev 5 closes; rev 6 is the one amendment (§9). Ships with the DESK IN A TRADE face on the Validate tab and the panel's five blocks; marks unchanged. Live first because it is the piece that cost her money.

**Phase 2 — data truth (next week).** Pre-open subscribe, tick-built candles, previous-close baseline, contract stamps, VPIN from ladder fills, the next-weekly chain on expiry days, the Oct record on roll day, the GoCharting tick post, chart trust with contract match. Each is a recorder change verified on the next day's files before the reads switch to it.

**Phase 3 — the cuts and the faces.** Tabs to three (DESK, WAR, RECORD); DESK FLAT / AFTER A MOVE; the chart marks from the event log; resting liquidity and big prints; the compact ±6 WAR with a time axis (her redesign brief).

**Phase 4 — entry and expression.** IF YOU ENTER NOW, the one refusal, the simplified expression; SENSEX policy. Each forward-logged from day one.

---

## 9. The amendment she signs once (rev 6)

Rev 4 §1–§8 and §10, rev 5 §A–§G, VALIDATE 2 §1.2–§5, EXPRESSION e §A.2–§A.5, §B, §C, §E, PLAN 3 §2–§6 close as they stand; their rows stay in their own populations. Rev 6 registers: the four chips, the words and their precedence, G / W / the OI event / acceptance / the held breach, AT THE WALL, the forward\* reference, the one wall rule, the entry face and its one refusal, the simplified expression, every threshold in §2 with its (h) mark, the falsifiers, and the fields each row logs. `FOLD_NEEDS` stays as H's one named switch (default flow_and_oi, with A on top). Her two numbers: the held-breach closes (2) and whether AT THE WALL should ever sound (no).

*Ceiling, stated:* eight trades on five days is a description. Thirty forward sessions decide; the tool prints counts, never rates.
