# 8. The shadow leg engine: build report (R-a, R-b, R-c on the front contract)

**Status:** SHADOW. The thresholds are unsigned, and nothing reaches her chart.
**Built:** 2026-09-29 night, to `7-final-design.md` §3.2 items 1–4 as ruled by `6-judgement.md`.
**Sources:** every number below comes from `tools/reader_replay.py`. The per-day outputs are in `docs/reader/replays/`.

**No outcome is scored anywhere.** There is no hit rate, and no "next leg".

## 1. What was built

| File | What |
|---|---|
| `reader.py` | Pure functions, with no I/O and no clock:<br>• the canonical minute (exchange candle when given, else the book) with book Δ at the **rupee** tick;<br>• the ruler, frozen at the open;<br>• the leg cut on 1-minute closes;<br>• TREND / RANGE / BREAKOUT;<br>• effort vs result on two tapes;<br>• blocks and spread prints, excluded by print;<br>• the batched-OI screen;<br>• WHO with a one-update tolerance;<br>• one English sentence and one Hinglish chip per leg;<br>• the day story;<br>• a flat `x` row per leg for the cross-index layer (`idx, t0, t1` ms, `dir, px0, px1, pts, d_ux, d_gc, doi, oi_state, who, absorbed, thin, expiring, rank_ux, rank_gc`). |
| `test_reader.py` | 22 tests: frozen ruler, determinism, restart equivalence with no repaint (a rebuild at every minute equals the live engine), each WHO class, absorbed, expiring "or roll", the roll window, the batched-OI screen, the one-update tolerance, spread-print exclusion on both tapes, warm-up silence, a data hole → CAN'T CHECK, a thin tape → price × OI, the cross-index row, the rupee-tick side, and the sheet. |
| `tools/reader_replay.py` | Replays any recorded day as-of, read-only, for NIFTY, BANKNIFTY and SENSEX. It writes `<IDX>_<day>.txt` (story, counts, integrity audit) and `<IDX>_<day>.json` (legs and events). |

**Rules kept:**
- Session constants unchanged (09:15–15:30). The 15:40 change was dropped by her.
- No curve or next-month read: it waits for next-month capture.
- GoCharting (GC) is read only on NIFTY, only as of its arrival (from the frame log), and only on legs holding two or more whole GC bars.
- The same code runs on all three indices, with lot, tick and expiry per index from the instrument master.
- The expiry is taken from the book's own contract stamp when present (29 Sep). Otherwise it comes from the current dump, and is labelled unverified.

## 2. The threshold sheet (one place: `reader.SHEET`; for her signature)

| Key | Value | Reason |
|---|---|---|
| K | 3 | Ruler = K × fold's prior-session median 1-minute range, frozen at the open (judge §3.1) |
| PRIOR_N | 5 | Prior sessions pooled for the unit (fold.PRIOR_N) |
| SELF_N | 15 | No prior session on disk: the ruler comes from the day's first 15 minutes, and says it is not causal before that |
| THIN_UNIT | 0.5 | fold's 1-minute unit gives way to the 5-minute range ÷ √5 only when it is under half of it (a thin book) |
| SPREAD_X | 2 | The ruler is never under 2 × the median bid-ask spread |
| MIN_PRINTS | 30 | A tape names a side or an efficiency only on ≥ 30 traded frames in the leg |
| SHARE | 0.10 | A tape names the aggressor at \|net Δ\| ÷ its own volume ≥ 0.10 |
| THIN | 0.05 | Opposite-signed tapes both at or above this = SPLIT |
| UX_COVER | 0.90 | UX Δ needs book minutes carrying ≥ 90% of the leg's volume |
| OI_Z | 3 | OI moved when the whole one-update tolerance range is beyond 3σ√updates (fold.OI_Z) |
| OI_SIGMA_N | 15 | Screened OI updates needed before σ is today's own |
| PUB_SHARE | 0.5 | One publication step carrying ≥ half a leg's OI change is not read as positioning |
| BLOCK_X / BLOCK_BAR | 100 / 0.25 | A print ≥ 100 × today's Σlots/Σtrades and ≥ 25% of its 5-minute bar |
| SPREAD_WIT / SPREAD_MIN | 0.5 / 2 | Spread witness: ≥ half the print missing from the exchange candle, or mirrored in the other month's OI within 2 minutes (and beyond that month's own OI noise) |
| WARM_N | 3 | Ranks are mute until 3 completed legs have an efficiency on that tape |
| LOW / PAIR | ⅓ / 0.5 | Low = bottom third of today's legs, or at most half the last same-way leg |
| ABSORB_MAX_R | 2 | "Heavy effort, little progress" needs a low progress-per-lot rank AND a leg under 2 rulers: a big move is never "little" (supervisor, 2026-09-29) |
| PAID_R | 3 | A leg of ≥ 3 rulers is never ABSORBED by effort. With a low rank it reads "heavy effort, move paid" / "zor laga, move mila". The against-the-aggressor form of ABSORBED is about sign and stays at any size |
| EDGE / BREAK | 0.5 / 1 | RANGE at a failed extension of δ/2; BREAKOUT at a trade δ beyond the band |
| GC_SHORT / GC_SHORT_LOTS | 0.97 / 10 | GC short bar (audit §3d) |
| GC_MIN_BARS | 2 | GC effort only on legs holding ≥ 2 whole GC bars |
| ROLL_SESSIONS | 5 | The expiring contract's roll window (weekdays; holidays not modelled in this repo) |

**No rule contains a lot count.** `PRINT_KEEP` = 25 lots is only a storage cut for block candidates. It sits far under any block threshold (100 × a median print).

## 3. Replays: 3 indices × 6 recorded days

**Legend:**
- **WHO** = new longs / short covering / new shorts / long liquidation / rotation / OI can't check.
- **CC** = legs where UX / GC was CAN'T CHECK.
- **Excluded** = prints removed from Δ.
- **OI pub** = OI updates flagged as publication steps.

| Index | Day | Ruler | Legs | Auction changes | WHO | Absorbed | Δ thin | CC ux/gc | Excluded | OI pub | Integrity violations |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY | 09-22 | 33.0 (self) | 6 | 4 | 0/1/3/0/1/1 | 3 | 0 | 0/2 | 0 | 24 of 341 | 0 |
| NIFTY | 09-23 | 34.8 | 5 | 2 | 0/1/0/1/3/0 | 0 | 1 | 0/3 | 0 | 26 of 364 | 0 |
| NIFTY | 09-24 | 28.5 | 10 | 5 | 0/0/1/0/9/0 | 1 | 3 | 0/3 | 0 | 22 of 362 | 0 |
| NIFTY | 09-25 | 29.7 | 9 | 4 | 0/2/0/0/6/1 | 1 | 2 | 0/4 | 0 | 64 of 352 | 0 |
| NIFTY | 09-28 | 27.6 | 10 | 3 | 0/3/0/3/4/0 | 1 | 3 | 0/2 | 0 | 37 of 360 | 0 |
| NIFTY | 09-29 | 27.3 | 27 | 5 | 0/3/0/6/13/5 | 9 | 3 | 0/6 | 5 | 57 of 361 | 0 |
| BANKNIFTY | 09-22 | 73.8 (self) | 14 | 5 | 1/2/2/1/7/1 | 3 | 5 | 0/0 | 0 | 51 of 316 | 0 |
| BANKNIFTY | 09-23 | 55.2 | 16 | 4 | 0/2/0/3/11/0 | 3 | 5 | 0/0 | 0 | 47 of 298 | 0 |
| BANKNIFTY | 09-24 | 49.2 | 34 | 8 | 2/2/2/2/24/2 | 10 | 4 | 0/0 | 0 | 45 of 316 | 0 |
| BANKNIFTY | 09-25 | 58.2 | 19 | 4 | 1/0/1/0/15/2 | 5 | 1 | 0/0 | 0 | 50 of 329 | 0 |
| BANKNIFTY | 09-28 | 57.0 | 23 | 6 | 1/1/0/6/13/2 | 8 | 4 | 0/0 | 0 | 39 of 341 | 0 |
| BANKNIFTY | 09-29 | 58.8 | 41 | **14** | 0/1/0/4/31/5 | 11 | 13 | 0/0 | 0 | 29 of 338 | 0 |
| SENSEX | 09-22 | 89.2 (self) | 5 | 4 | 0/0/0/0/4/1 | 1 | 2 | 0/0 | 0 | 5 of 66 | 0 |
| SENSEX | 09-23 | 68.7 (spread) | 10 | 4 | 0/2/0/2/6/0 | 1 | 6 | 0/0 | 0 | 17 of 102 | 0 |
| SENSEX | 09-24 | 52.7 (spread) | 34 | 10 | 0/0/0/0/34/0 | 3 | 26 | 0/0 | 0 | 2 of 79 | 0 |
| SENSEX | 09-25 | 49.6 | 28 | 10 | 1/0/0/1/26/0 | 0 | 25 | 0/0 | 0 | 9 of 97 | 0 |
| SENSEX | 09-28 | 48.8 | 22 | 6 | 1/0/2/0/18/1 | 1 | 19 | 0/0 | 0 | 12 of 98 | 0 |
| SENSEX | 09-29 | 49.3 (spread) | 43 | 12 | 0/1/0/1/41/0 | 3 | 38 | 0/0 | 0 | 12 of 101 | 0 |

## 4. Pre-registered bars (stated before these numbers were read, per the judge §3.10; for her signature)

- **Churn:** at most **12 auction state changes per index per day.** Range-edge widenings are appended events, not state changes.
  - Met on 17 of 18 index-days.
  - **Missed on BANKNIFTY 29 Sep (14).** That was a volatile expiry day against a ruler frozen from calmer prior days (58.8 pts, while that day's median 1-minute range was 30).
  - Kept as a miss, not re-tuned.
  - The FLOW-row bar (≤ 20 changes a day) is for R-e, which is not built.
- **Misdescription (automatic):** the integrity audit re-derives every confirmed leg's words from its own numbers:
  - extreme = the leg's true high or low;
  - continuity;
  - confirmed after its extreme minute closed;
  - WHO class = its OI and price signs;
  - "moved" only beyond the whole tolerance range;
  - ABSORBED only with its conditions (against the aggressor, or a low rank on a leg under 2 rulers), and never "little progress" on a leg of 3 rulers or more;
  - no rank before warm-up;
  - UX Δ recomputes from the minutes minus the excluded prints.

  **Bar: 0 violations. Result: 0 on all 18 index-days** (356 legs).
- **Misdescription (manual, owed in shadow):** 60 random reads per day, checked against the raw files by a reader who did not write them. Bar: 0 contradictions of an [M] number.
- **No repaint:** tested (`test_restart_equivalence_and_no_repaint`). A rebuild at every minute equals the incremental engine, and confirmed legs never change.

## 5. What the replays say (description, not verdict)

**NIFTY 29 Sep:**
- **The cut:**
  - drive ▼ −182 (09:15–09:38);
  - RANGE 22579–22643 at 10:29;
  - BREAKOUT ▲ 11:12;
  - trend broken ↓ at 12:27 (below the 22713.5 higher low);
  - RANGE 22631–22723 at 12:55;
  - the 15:22 low at 22616 logged as a poke, not a break.
- **The 10:07 print (4,523 lots on UX, 4,528 on GC) is excluded on both tapes as a spread print.** 5,306 lots of that minute are missing from the exchange candle.
- **The OI publication step** at 10:12 (−5,021 lots) is not read as positioning.
- **GoCharting reads go to CAN'T CHECK from the 12:25 bar**, because they arrived at 16:08. The afternoon is read on UX alone, as it would have been live.
- **The afternoon range's down legs read "ABSORBED (price moved against the aggressor)"** on UX. Price fell while buyers lifted; this is Sep only. The Oct read is not built.
- **The 12:01→12:33 flush (▼ −133.8 pts, 4.9 rulers)** has the day's least progress per lot (68 pts/1k, 1 of 9). It now reads "long liquidation (expiring: or roll) · heavy effort, move paid", no longer "ABSORBED (heavy effort, little progress)".
  - This follows the supervisor's size gate (ABSORB_MAX_R, PAID_R).
  - Across the 18 index-days, ABSORBED fell from 86 legs to 64, and 11 big legs now read "move paid".
  - The rank now says its direction: "least progress per lot, 1 of 9", not "rank 1 of 9".

**Across the three indices:**
- **The batched-OI screen is not rare.** 6–18% of NIFTY and BANKNIFTY OI updates are publication steps; NIFTY 25 Sep has 64 of 352.
- **Most legs read "rotation, OI flat".** The 3σ√n floor on minute-batched OI is strict for legs of a few minutes. That is honest silence, not a miss.
- **SENSEX is thin, and it says so.**
  - The future prints one price or none in 35–47% of minutes, with a median spread of 25–38 pts.
  - fold's 1-minute unit was 0–2 pts on a 73,000 index. The ruler therefore comes from the 5-minute range ÷ √5, or from 2 × the spread.
  - Δ is "too thin to name a side" on 19–38 legs a day, so WHO falls back to price × OI and says "Δ patla".
  - SENSEX legs describe a thin future's prints. The cross-index layer should weigh them that way.

## 6. Known limits and deviations (said, not hidden)

1. **Canonical minute.** Exchange candles exist on disk only for 29 Sep (the after-close pull). Every other day uses book-built minutes, labelled `src: book`. Live, the hook uses the book until a REST candle poll exists; that poll is P2a, not this job.
2. **The ruler is 27.3 on NIFTY 29 Sep, not "about 29.4".** fold's unit is built from *traded* frames (`ladder.Ladder`), and the pooled median is 9.10.
3. **Three rules added for the thin SENSEX book** (THIN_UNIT, SPREAD_X, MIN_PRINTS). On NIFTY they never fire. On BANKNIFTY they never fire after the THIN_UNIT guard (fold's unit is kept).
4. **The OI mirror witness must also beat the other month's own OI noise.** On a roll day Oct moved hundreds of lots a minute, and ½ × a 300-lot print was no witness.
5. **A reversal is confirmed only by a later minute's close.** The order inside a minute is unknown, so there are no zero-length legs; the cost is at most 60 s.
6. **PAUSE is dropped** (judge §3.8). RANGE is declared at the first failed extension, when the trend side misses by δ/2.
7. **Contract identity.** Book rows carry `ik`/`expiry` only from 29 Sep. For 22–28 Sep the expiry comes from today's instrument dump.
   - **SENSEX's Sep future is no longer in the dump.** 22–25 Sep SENSEX may be the Sep contract read as "not expiring". The story says "unverified for a past day".
8. **GoCharting arrival** is taken from frame-log minutes (a row is written when the frame changes). That is conservative by up to a few minutes.
9. **Holidays are not modelled** in the roll window, as elsewhere in this repo.

## 7. Step 4: live, shadow (built on the coordinator's go)

| File | What |
|---|---|
| `reader_live.py` | Its own thread, one pass every 15 s, per index (NIFTY, BANKNIFTY, SENSEX):<br>• tails today's book file (the recorder's own, read-only);<br>• steps each closed minute (5 s after it ends) into one `reader.Engine`;<br>• NIFTY: stamps each GoCharting bar with the time it was first seen in `tape_log`'s file;<br>• appends new events to `data/reader/reader_<IDX>_<day>.jsonl`, append-only, with the frozen leg on each leg row;<br>• caches one reply.<br><br>**On restart:** the book is re-read from its first row; events already logged are never written twice; the reply serves the logged legs (no repaint).<br>**Isolation:** every failure is try-guarded per index and served as "could not check — the reader failed: …". Nothing is called from the frame door, fold or the feed alarm. |
| `server.py` (4 surgical edits) | • `import reader_live`;<br>• `GET /api/reader?idx=`, read-only, O(1) from the cache;<br>• the thread starts beside fold's, live runs only;<br>• `reader_live.DIR` added to `_isolate_mock_writers`. |
| `conftest.py` | `reader_live.DIR` → tmp. The leak guard covers it. |
| `test_reader_live.py` | Reads once and logs once; a restart repaints nothing; fails soft; no book yet is said, not zero. |
| `ui-v2/src/trade/legs.tsx`, `TradeTab.tsx` | A **"LEGS · shadow"** toggle, **off by default**, stored per browser. It shows `/api/reader` for the active index:<br>• a header ("unsigned thresholds · describes the tape, decides nothing", ruler, auction state, expiring, as of);<br>• the leg table (# · time · ▲▼ · pts [M] · min · UX Δ [I] with pts/1k and rank · GC · OI [M] · who chip; hover = the English sentence);<br>• the forming leg as "abhi";<br>• the auction chips.<br>It computes nothing. |

**Smoke run on 29 Sep's recorded files** (read-only, log redirected to scratch):
- The first pass (priors and the whole book, three indices) took 8.7 s; a steady pass took about 0.01 s.
- Legs from book-only minutes: NIFTY 27, BANKNIFTY 41, SENSEX 43.

**Checks:**
- `python -m pytest -q`: **1492 passed**.
- `tsc --noEmit`: **clean**.

**Not done:** the server was not started, and the Trade tab was not looked at in a browser. The live server is hers to start.
