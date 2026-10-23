# THE READ v2 — entry zone, flip test, yesterday's value (PRE-REGISTERED)

Fixed **2026-10-08 ~21:00 IST, before the 2026-10-09 session exists.** Build after the 9 Oct close, so 9 Oct is the
first session these rules never saw. A change after today is a new rev with its date (read.py docstring rule).

Her words (2026-10-08 evening): *"my vwap + std deviation is my entry and zones … people use volume profile of
previous day to mark hvn or lvn … flip test, the first indication we can get is the first time the oi stop building
like by 09:25 or 9:45 the pe writing stopped completely."*

---

## 1. What her own chart says (Kite 3-min NIFTY OCT FUT, 6–8 Oct, her VWAP ±1/2/3σ)

| Day | READ | VWAP crosses after 09:30 | 3-min closes by band | Deepest pullback after 09:45 |
|---|---|---|---|---|
| 6 Oct | TREND ▲ | **0** | +1..+2σ 75 · VWAP..+1σ 42 · +2..+3σ 3 | −0.35σ (one bar under VWAP) |
| 7 Oct | RANGE/WAIT | **13** | every band, both sides | — |
| 8 Oct | TREND ▼ | **0** | −2..−1σ 97 · −1σ..VWAP 18 · −3..−2σ 5 | −0.08σ (never reached VWAP) |

**A trend day rides the 1σ–2σ lane on one side of VWAP.** On 8 Oct her d2→d3 BUY zone lay *inside* that lane, which
is why the zone machine armed BUY all day.

| Rule tried on her bands | 6 Oct | 8 Oct | 7 Oct |
|---|---|---|---|
| Trend side: enter at the 1σ line toward VWAP, stop = VWAP touch, target = 2σ | 6 to +2σ · 2 stopped (09:54, 10:03) · 2 open | **9 of 9 to −2σ** · 2 open | — |
| Range: fade a 2σ touch back to VWAP, stop = 3σ | — | — | VWAP first on most touches after 10:20; 3σ first at 10:00–10:18 |

Row counts, three days, in-sample. Not an edge claim.

**Our bands = her bands:** VWAP/σ rebuilt at 3 min from the recorded futures ticks matched Kite within 1–2.5 pts
(VWAP) and ~2 pts (σ) all of 8 Oct (ticks start 09:17, not 09:15).

## 2. "The PE writing stopped by 09:45" — checked on the chain record

The nine strikes nearest spot, aaj likha per side, first time it made no new high for 15 minutes:

| Day | Stopped first | The other side kept building to | Day |
|---|---|---|---|
| 8 Oct NIFTY | **PE 09:44** (+99L) | CE 10:12 | ▼ ✓ |
| 8 Oct SENSEX | **PE 09:45** | CE 10:11 | ▼ ✓ |
| 6 Oct NIFTY | **CE 09:48** | PE 10:59 | ▲ ✓ |
| 6 Oct SENSEX | **CE 09:34** | PE 10:08 | ▲ ✓ |
| 1 Oct NIFTY | CE 10:01 | PE 10:23 | ▼ ✗ |
| 28 Sep SENSEX | CE 09:59 | PE 11:10 | ▼ ✗ |
| 28 Sep NIFTY | CE 10:04 / PE 10:06 | — | ▼ tie |
| 7 Oct, 29 Sep | one side first | — | flat |

Right on the clean days, wrong on two of eight trend index-days. So it is an **event and a warning, never a vote.**

## 3. Yesterday's value (prints.profile / prints.nodes, already in the repo)

| Day | Open vs yesterday's value | Then |
|---|---|---|
| 6 Oct | at 5 Oct POC / HVN 22,650–22,670 | broke above VAH 22,729 → trend up |
| 7 Oct | below 6 Oct VAL 22,742 | rallied to 6 Oct POC 22,777 (high 22,782), rejected → range |
| 8 Oct | below 7 Oct VAL ~22,603 (profile partial: server from 13:05) | first 30 min high 22,614 = VAL from below, rejected → trend down |

---

## 4. THE RULES (fixed now)

All prices in the **futures** frame (her chart), with spot beside them. Bands = session VWAP ±kσ on **3-min** bars
built from the futures ticks (`contract_bars.vwap_sigma`, the same recurrence as the tape).

### E. ENTRY ZONE — by the READ's word
| READ | Zone | Trigger (closed 3-min bar) | Stop | Targets |
|---|---|---|---|---|
| TREND ▼ / LEAN ▼ | SELL **−1σ … VWAP** | high ≥ −1σ, close < −1σ, bar delta < 0 | a 3-min close > VWAP | T1 −2σ · T2 the nearer of −3σ / READ's PE wall |
| TREND ▲ / LEAN ▲ | BUY **VWAP … +1σ** | low ≤ +1σ, close > +1σ, bar delta > 0 | a 3-min close < VWAP | T1 +2σ · T2 the nearer of +3σ / READ's CE wall |
| RANGE | her zone machine: BUY d2→d3 · SELL u2→u3 | her machine's own trigger, unchanged | her machine's | VWAP |
| WAIT / BAN RAHA | none | — | — | — |

- No zone before **09:45**. Re-arm after price reaches **1.5σ** beyond VWAP on the trend side.
- After 15:00 the zone shows with "15:00 ke baad naya trade nahi" (her practice; display only).
- LEAN carries "chhota size".
- On a TREND day the zone machine's arm *against* the READ shows as "read ke khilaaf · chup". The machine itself is
  untouched.

### F. FLIP TEST — the writers
- **WRITERS STOP** event, per side: the nine-strike aaj likha makes no new high for **15 minutes** → "PE likhna ruka
  09:44 (+99L) · CE abhi likh rahe". It re-arms on a new high. The first stop of each side is kept as "pehla ruka".
- **Before 09:45 (BAN RAHA):** one side stopped while the other still makes new highs → hint chip
  "jhukav ▼: PE ruka, CE likh rahe". A hint, never the word.
- **While a TREND ▼ is held:** CE writing stopped *and* the last 30 min PE add > 0 → amber "FLIP test: CE ruka, PE
  likh rahe". A warning, never a break (breaks stay read-1's: FLIP close, writers flip or fade, price turns). Mirror for ▲.

### V. YESTERDAY'S VALUE — location
- `prints.profile` on yesterday's futures ladder bars → **POC, VAH, VAL** plus the top HVN. LINES gets a KAL VALUE row.
- JAGAH chip: open inside / above / below yesterday's value.
  - From 09:45, if the open was outside value:
    - no 3-min close back inside → "value ke bahar accept" (trend-friendly);
    - a close back inside → "value mein wapas · POC {p} tak ja sakta" (range-friendly).
- A partial profile (late start) says so: "kal ka profile adhoora (13:05 se)". Never a silent number.

### D. ORDER-FLOW EVENTS read in the READ's direction (decoder rules, unchanged)
| Event | On TREND ▼ | On TREND ▲ |
|---|---|---|
| PEHAL in the read's direction | "dabav jaari" (confirm) | same |
| DABAAV / CVD ulta at the extreme | "bounce aa sakta — upar bechna" | "dip aa sakta — neeche kharidna" |
| BADA PRINT against the read at FLIP | amber "FLIP pe bada kharidar" | mirror |

---

## 5. How it is judged
- `tools/day_test.py` gains three sections: each zone trigger (stop first or T1 first), each WRITERS STOP event
  (the day it preceded), and the open-vs-value read. Row counts only.
- Her pass bar is stated by her before 20 sessions of rows are read.
- Kill: a rule whose rows go against it over 20 sessions goes grey on the face.
- Nothing here gates the engine, the zone machine, the fade gate, signals or trigger_log.
