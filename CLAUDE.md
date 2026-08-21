# CLAUDE.md

**Read [START-HERE.md](START-HERE.md) in full before doing anything in this
repo — and if your task touches the DESK, read [HANDOFF-DESK.md](HANDOFF-DESK.md)
in full too.** Everything else is history or detail. Verified 2026-08-22.

## Which of the two instruments are you working on?

They share one server and one repo and answer opposite questions. Confusing
them is the fastest way to waste a session.

- **THE TAPE** — *when is a move coming*, a buyer's question. `engine.py`,
  `band_rotation.py`, the zone machine, `data/trigger_log.jsonl`,
  `/console.html`. START-HERE.md is its document.
- **THE DESK** — *which instrument, and which structure*, a seller's desk.
  `surface.py`, `desk.py`, `direction.py`, `drag.py`, `/desk.html`.
  HANDOFF-DESK.md is its document.

## The rules that survive even if you read nothing else

1. **Upstox, not Dhan.** Dhan's Data API lapsed 2026-08-05. Dhan code in the
   tree is a documented fallback, not the live path.
2. **No new backtests, no cache-slicing for edges.** `context/research-findings.md`
   §5 is a stop rule. Nine hypotheses are dead; the live question is answered by
   forward collection, which is already running.
3. **The setup is a ZONE:** d2→d3 buy, u2→u3 sell. Reaching d2 IS the event.
   3-minute is canonical.
4. **Never print a hit rate / win rate / expectancy / confidence score.** §5e
   records the pass bar as owed by the operator, stated before the numbers are
   read; under 15 per side is inconclusive. Describe rows; leave the verdict to
   them.
5. **Keep populations apart:** `5c`, `zone`, and quarantined legacy rows are
   three different things. Never pool them.
6. **Three sentences, never one.** "We checked and found nothing", "we could not
   check", and "we are not showing you" must never collapse into a single
   rendering. Absence gets a reason. A missing value is never a zero.
7. **Every number is `[M]` measured or `[I]` inferred**, and says which.
8. **TRADING IS FREE ON THIS DESK.** Zero brokerage; statutory charges rebated
   on any position closing at least ₹1 positive. `desk.STATUTORY_PCT = 0.0` is
   deliberate — do not "fix" it back. `STATUTORY_PCT_IF_CHARGED` holds the old
   0.0014 for the day the arrangement ends. Never reason from a retail frame:
   this is prop scale (₹1–10cr) and she POSTS rather than crosses, so the
   bid-ask is revenue, not cost.
9. **A passing test suite is not evidence the model is right.** Every serious
   defect in the desk was found by live data or an adversarial reader, never by
   pytest. Before reporting that anything works, ask: *would a desk take this
   trade?*
10. **No order path, ever.** This stack is advisory. It has never placed an
    order and must not learn how.

## Running it

```bash
.\stop.bat; .\start-v2.bat     # THE way to start. Upstox, port 8765.
python -m pytest -q            # 842 tests, green as of 2026-08-22
```

Screens: `/desk.html` (the desk) · `/console.html` (the tape detectors).
APIs: `/api/desk?capital=<rupees>` · `/api/surface` · `/api/drag` ·
`/api/chain` · `/api/senses` · `/api/health`.

**`data/trigger_log.jsonl` is the one irreplaceable artefact in this repo** and
is deliberately NOT committed on this branch — see HANDOFF-OPERATOR.md §6
before touching it.
