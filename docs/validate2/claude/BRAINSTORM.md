# Validate, rebuilt — Claude's blind brainstorm (2026-10-06, 15:05)

Written before reading the Fable design in `../fable/`. Its job is to be a second, independent mind;
the two are merged after.

## What a trader actually asks, in order

1. **"What is the market doing right now, and since when?"** — the Market Read.
2. **"Is my idea right for THIS market?"** — the Validate.
3. **"Is there something better?"** — the Better Trade.
4. **"I'm in. Is it still right? What changed?"** — the In-Trade loop.
5. **"Was I right?"** — the evening receipt, with rows only and no rates.

Today's tab answers only #4, and it answered it with one rule (the price line). That is why it feels
one-dimensional.

## 1. Market Read (the button)

Shown in the same order I used at 14:57. Every line carries a number, and every level is tagged spot/fut.

- **DAY** — open, low/high with their times, net move, buyers' or sellers' day (fights won, which
  already exists), and the box it is in now and since when.
- **SYNC** — the three indices: did their highs and lows land on the same minute? Name the one that
  did not confirm.
- **OI** — the pin (the largest writers on both sides, near ATM). The ceiling and floor walls, each
  with "building / flat / leaving since HH:MM" against its OWN peak, not a z/√n test. The PCR shift
  over 60 minutes. Which side is leaving.
- **FLOW** — CVD at each swing high/low (divergence = lower high with price at the high), VWAP
  acceptance (fut), the last fight won, big prints at levels, absorption ("53K sold, price held").
- **VPIN** — one line, shadow-tagged until its record qualifies.
- **TIME** — minutes to close, expiry or not, the ATM straddle (the market's own move estimate),
  and her 15:00 reminder.
- **LEVELS TO WATCH** — at most 4. Each says spot+fut, what it is (wall / day high / VWAP), what
  CONFIRMS the break (the OI leaving + flow through), and what DENIES it (absorption, wall building).
- **IDEAS** — the best buy and the best sell across all three indices, or "nothing clean". Each idea
  carries its invalidation and targets (below), plus one line: "what would flip this read".

**Generator:** deterministic facts first, every one [M]/[I]. Prose comes from templates that read like
the 14:57 read. An optional LLM pass (Claude API) may rewrite the prose only if a key is configured,
and every number in its output is regex-checked against the facts packet. Any line with an unchecked
number is dropped. The screen must be complete without the LLM.

## 2. Validate a trade

Input: index, strike, CE/PE, buy/sell. The price is optional and defaults to the LTP.

Checks, each one a line FOR / AGAINST / CAN'T CHECK:

- **Direction fit** — does the idea's direction match the day (fights), the box (where in it), and
  the last 30 minutes of flow?
- **The wall in the way** — is there a wall between price and T1, and is it building or leaving?
- **The wall behind** — is the defending wall at the invalidation building or leaving? This is the
  check today's 22650 PE failed: its wall had been bleeding since 10:32.
- **Flow** — CVD direction since the last swing, a divergence at the current swing, VWAP side.
- **Sync** — do the other two indices agree?
- **Expression** — delta and time value. A deep-ITM buy is a futures long. On expiry it is time value
  vs minutes left. A sale's premium vs the distance to its invalidation.
- **Time** — minutes left, the 15:00 reminder, the expiry-afternoon pin.
- **Liquidity** — bid/ask spread vs premium.

**Levels:**
- INVALID = where somebody gives up: the defending wall's strike + basis, or the swing the flow
  defended.
- T1 / T2 = the next walls or levels, with the premium there [I], the points to each, and the points
  to invalid.

**Verdict:** GO / WAIT / NO from counts (n FOR, n AGAINST) plus two vetoes:
- the wall behind is already leaving;
- the target is behind a building wall with no flow through it.

No %. It must be pre-registered before it shows live.

## 3. Better Trade

Enumerate about 12 candidates: 3 indices × {buy ATM CE, buy ATM PE, sell ATM CE, sell ATM PE} (ITM
for a sale with the trend). Run each through the same checks, then rank:
- fewest AGAINST, with no veto;
- then the most points to T1 per point to invalid;
- then the most time value working for a seller / the least theta against a buyer.

Show the top one and the runner-up, with why it beats hers in one line. Say "yours is the best on
the board" when it is, and "nothing clean — stand aside" when every candidate has a veto.

## 4. In trade, every second

- Server: one loop per index each second, over the newest book tick + the newest chain (shown with
  its age). The UI polls 1 s.
- **Rows:** her four (zone, flow, OI, VPIN) plus "the wall behind: building / flat / −x% off peak
  since HH:MM" (C1 + C2, the honest OI) and the distance to invalid, in spot and fut.
- **Zone-alone:**
  - When zone is the only thing behind her, the word stays the engine's, but goes AMBER:
    "HOLD · sirf zone".
  - The at-the-line FOLD runs in shadow until her forward record decides. The replay showed the
    hard rule cuts the 09-24 winner.
- **Pullback vs gave-up:** spell it out using her own definition, every time the price moves against
  her.
- **What changed since entry:** a short diff of the read then vs now ("22650 CE writers 200.7L →
  169.9L, −15%", "PUT OI +113L under you").

## 5. Unique

- **"The other trader"**: who is trapped if her trade works, and who is trapped if it fails, named
  by strike and OI. It tells her whose pain fuels the move.
- **Read diff**: press Market Read twice and the second read leads with what changed since the first.
  This is cheap and very useful.
- **Devil's advocate line**: every GO carries the single strongest fact against it.
- **Evening receipt**: every press is logged. After close, each read's levels are marked
  "held / broke at HH:MM" — rows, so she learns which reads to trust.

## What I would NOT build

- No odds, and no ML.
- No new charts.
- No second engine beside fold.py for the in-trade word, because two engines on one trade gave her a
  false FOLD on 09-28.
- Reuse story.py / expression.py / fronts.py / xindex for the facts. What is genuinely new is the
  checker, the ranker and the read composer.
