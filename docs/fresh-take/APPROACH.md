# APPROACH — how I would trade a day, and what the tool is for

Voice: an intraday index-options trader. Numbers marked (data) were measured on the 12 recorded sessions (22 Sep – 8 Oct 2026); everything else is a rule of thumb I would write down *before* the session.

## 0. Stance
I don't predict the day. I ask five questions in a fixed order and trade only when the answers line up. When they don't, "no trade" is the position.

## 1. Where my eyes go — five looks, ~20 seconds, always this order
| # | Look | What I read | Source |
|---|---|---|---|
| 1 | **WHERE** | Futures vs VWAP and ±1σ/±2σ (my zones); vs yesterday's value (VAL/VAH/POC, HVN/LVN); share of last 30 min on one side of VWAP | futures ticks |
| 2 | **WHO IS WRITING** | OTM call vs OTM put OI change, last 30 min (and 10), at strikes near spot — never total OI. One side only = conviction; both = range; neither = dry | chain |
| 3 | **IS FLOW REAL** | Futures delta last 15 min; futures OI vs price (new shorts / short-cover / new longs / long exit); VPIN rising against me | ticks, 5-min bars |
| 4 | **CHEAP OR RICH** | Market move in 30 min ÷ what ATM IV priced for 30 min. ≥0.8 options cheap (buyer's edge); ≤0.5 rich (seller's edge) | chain IV + ticks |
| 5 | **CLOCK & COST** | Minutes to 15:00, ATM spread, premium per lot, does an index expire today | chain |

Looks 1 and 2 are never optional. Without them there is no day type, only noise.

## 2. Pre-open (before 09:15) — two minutes, three facts
1. Yesterday's value area, POC and close per index (futures), and the OI walls at yesterday's close.
2. Who expires today. From the chain `expiry` field: NIFTY Tuesday, SENSEX Thursday, BANKNIFTY monthly only (29 Sep both NIFTY and BANKNIFTY expired). Expiry = most gamma.
3. The news/event of the day. **I** write it; the tool cannot know it.

One decision only: where must the open be for me to care? Outside yesterday's value and holding there = trend candidate. Inside = rotation, VWAP±σ work. Gap size is known only at 09:15; the tool must not guess it.

## 3. The open (09:15–09:45): can't wait, can't know — so split it honestly
What is knowable when (data: recorder and chain start at 09:17; first 2 minutes are missing):

| Time | Becomes known |
|---|---|
| 09:17 | price, 5-min delta, futures OI, option premiums |
| ~09:27 | 10 minutes of OI flow → "who is writing" for the first time |
| ~09:47 | σ bands, VWAP side-time, VWAP crossings (30 min) |
| 10:15 | PIN test (before this, "range used" lies) |

"Waiting till 09:45 means missing the drive" is true for the *full read*. So there is one **early lane**: move from the first print ≥ **1.0× what IV priced for 30 min**, *and* 5-min delta in the same direction. Half size. Fold when delta flips or price is back at the open print for 3 minutes. It is rare (fires on 1–3 of 33 index-days at 09:22–09:32, data) and that is correct: if the drive isn't loud, there is nothing I can honestly trade yet. Between 09:27 and 09:47 the read is allowed to say JHUKAAV (lean), never TREND.

## 4. Pin, chop, trend — how I check, and how early
All thresholds are in the day's own units (σ, expected move-to-date = mean range of the last 3 sessions × √(minutes/375), own OI base) — never index points.

- **TREND ↓/↑** — price on one side of VWAP ≥ 80% of last 30 min **and** writers one-sided with it (weak side ≤ 40% of strong) **and** price ≥ 0.6× expected move-to-date from the open. This is Mary's rule: "almost no put writing, call writing all day".
- **JHUKAAV (lean)** — price on one side, writers mixed or move small. Trade only that side, half size.
- **CHOP** — ≥ 2 VWAP crossings in 45 min (dead zone ±0.25σ), |z| < 1.25σ now, bands formed.
- **PIN** — after 10:15: range-to-date < 0.6 of expected, spot within half a strike of the strike with the biggest two-sided OI, crossing VWAP. Rare in this data (0.8% of minutes) — the rule I trust least.
- **PALAT? (TURN)** — price still on the old side of VWAP but only the *other* side is writing. Mary's "first flip sign": the supporting side's writing stops. I treat it as a *watch*; it is confirmed only when price holds across VWAP 3 minutes.
- **SAAF NAHI (unclear)** — anything else, or any ingredient missing.

Earliest honest call: lean ≈ 09:27, trend ≈ 09:47, pin ≥ 10:15.

## 5. Best way to make money, by kind of market (buy *and* sell, CE *and* PE)
| Market | Best expression | Why | Not |
|---|---|---|---|
| TREND ↓, moving faster than priced (≥0.8) | **Buy PE** ATM/ITM on a bounce | options cheap, convexity | selling PE, buying CE |
| TREND ↓, grinding (≤0.5) | **Sell CE** ATM/ITM on a bounce to VWAP / −1σ | theta + trend, options rich | buying PE late (decay) |
| TREND ↑ | mirror: Buy CE / Sell PE | | |
| JHUKAAV | same two expressions, **half size**, only the lean side | bias, not proof | counter-lean |
| CHOP | **Sell the rejected side at ±1σ**, target VWAP (sell CE at +1σ, sell PE at −1σ) | range pays the seller | buying breakouts of 1σ |
| PIN | **Sell** near the pin strike, or nothing | only the seller is paid for decay | any buying |
| PALAT? | nothing against the old trend until VWAP is reclaimed 3 min; then the new side, half | writers changed, price hasn't | fading it early |
| SAAF NAHI | **nothing** | | everything |

Buy-vs-sell between two same-direction expressions = look 4.

## 6. What makes me take a trade, what makes me wait
Take = one direction passes all five: **PLACE** (a level I trade from: retest of VWAP within −0.3…0.8σ on my side; *or* a bounce ≥ 0.4σ off the extreme while still ≥ 0.4σ from VWAP; *or* a break of the extreme with 15-min flow and move ≥ 1.0× priced), **OI** (writers on my side), **FLOW** (15-min delta with me), **PREMIUM** (buy when cheap, sell when rich), **CLOCK** (> 45 min to 15:00 green, 15–45 amber, < 15 no). All green: full size in TREND; half in JHUKAAV / PALAT / PIN / early / partial data.

Wait, and name the missing thing, when: writers are against me (that is a "no", not a "wait"); I'm extended > 0.8σ past VWAP with no bounce; chop with nothing at a band; nothing on the screen agrees; < 15 minutes to 15:00. (Data: on 8 Oct, the cleanest trend day, a VWAP-retest rule alone qualified in 1 of 271 trend-down minutes after 10:30 — price rode −1σ to −2σ all day. Hence "bounce" and "break" entries exist.)

## 7. What makes me hold, what makes me fold
Entry is a contract: the tool stores the reasons I entered on (place / OI / flow). While I'm in, only four things are watched — my own: **ZONE** (VWAP side; 3 minutes beyond 0.25σ against = gone), **FLOW** (15-min delta), **OI** (writers vs at entry), **VPIN** (NIFTY futures only; +0.06 with flow against).
- **FOLD** = zone gone, or two of the other three against, for 3 minutes. Never a candle close.
- **WATCH** = one against / two weak. **HOLD** = all with me.
- Holding through a pause is a rule, not courage: 8 Oct 12:10, sold CE, flow turned against but zone and OI intact → WATCH, not FOLD.
- Fold example: 30 Sep 13:46, bought CE at 13:11 (half size), zone slid, flow and OI both flipped → FOLD.
After a fold the opposite side must pass the same entry test; the tool never "flips" me.

## 8. What decides the index
1. **Clearest state** — not unclear; location and writers agree. The three indices agree on price side only 25 of 33 times (data), so direction is rarely the choice; clarity is.
2. Two clean → the **leader** (first out of VWAP±1σ, larger |z|).
3. **Cost**: lots 65 / 30 / 20 (data, tick quantity); ATM premium per lot ≈ ₹9k NIFTY, ₹22–29k BANKNIFTY (monthly), ₹3–10k SENSEX (lowest on its expiry day); ATM spreads ≈ 0.1–0.35% of premium on all three — rarely decisive.
4. **Expiry today** = most gamma: buyers get more per point; sellers get decay but whip. On the expiring contract the OI read degrades after ~13:30 (NIFTY 6 Oct: put OI −604L in the afternoon while price was flat/up, data) and ATM IV is unreliable (29 Sep: 28%).
5. **Disagreement** (e.g. BANKNIFTY ↑ while NIFTY ↓) → trade the clean one or none, never average.

## 9. Both sides in one day
CE in the morning, PE late morning, CE again in the afternoon = three independent entry tests. The tool doesn't know about my last trade except as a thesis to monitor.

## 9b. Through the day to 15:00, and how I actually use the tool
- **09:00** pre-open card (3 facts, my event note). **09:17–09:47** index strip + "Kaisa din" only; act only on DRIVE, half size. **After 09:47** one loop, ~20 s, whenever I'm flat: strip (which index) → Kaisa din (what kind of day, six ticks) → Kya karna hai (is anything KARO/AADHA, and what is missing) → Kahan (distance to the level I'd trade from). If the answer is RUKO I look away; the screen tells me the one thing that would change that.
- **In a trade** I look at one panel only: the fold board against *my* entry reasons, plus the first target.
- **11:30–13:30** gets no special rule — I have no evidence for a lunch effect, so the tool shows none. **From 14:15** the clock light is amber (15–45 min left), **14:45** red; I close by 15:00 and take nothing new after it. That is my practice, so the tool only shows the countdown; it never blocks.

## 10. The tool's job — and what it must not try
**Job:** keep the question order; measure every look in one unit (futures, spot/strike tagged); say plainly which ingredient is missing; remember my entry reasons and watch only those; say what would change its mind.
**Must not:** predict; show a win rate, hit rate or confidence score; redraw the price chart I already have; size positions; place orders; pretend to know the first two minutes, the news, or the order book; fill a gap with a guess.

## 11. A day nobody has seen — and the unclear minutes
- No rule names a day or a price. Thresholds are in the day's own units; default is SAAF NAHI. Missing ingredient → "?" light, never an estimate (7 Oct has no morning: VWAP-from-open, range and open-relative tests go grey, TREND/PIN are disallowed).
- Unclear is a first-class state with a job: say *what would resolve it* (e.g. "price ±1σ ten minutes **and** one side writes"), and that is the whole instruction.
- Stability audit (not an accuracy test), 33 full index-days, 1-min steps: UNCLEAR median 14% of minutes (5–32%), longest unclear run median 37 min (max 72); state changes median 8 per day (4–13; 27 without the 10-min hold). The screen does not flicker, and it does not claim clarity all day.
- How I'd know it works *without fitting*: (a) **facts are checkable** — tick VWAP and σ match the broker's own export within ~3 pts / ~1–4 pts of σ after 10:15 (data); (b) **blind call**: Mary writes her own day-type and side at 09:30, 10:30, 12:00, 14:00 *before* looking; disagreements are logged and discussed, nothing is scored as P&L; (c) **constants frozen** (RISKS.md lists every one) and changed only with a dated note, never retroactively; (d) **forward only**: no past-day mining for edges, no win rate until the forward pass bar is set by Mary in advance; (e) a light that Mary overrides the same way repeatedly is cut, by her.
