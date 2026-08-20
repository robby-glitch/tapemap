# CLAUDE.md

**Read [START-HERE.md](START-HERE.md) in full before doing anything in this
repo.** It is the single current-state document; everything else is history or
detail. Verified 2026-08-20.

The five rules that survive even if you read nothing else:

1. **Upstox, not Dhan.** Dhan's Data API lapsed 2026-08-05. Dhan code in the tree
   is a documented fallback, not the live path.
2. **No new backtests, no cache-slicing for edges.** `context/research-findings.md`
   §5 is a stop rule. Nine hypotheses are dead; the live question is answered by
   forward collection, which is already running.
3. **The setup is a ZONE:** d2→d3 buy, u2→u3 sell. Reaching d2 IS the event.
   3-minute is canonical.
4. **Never print a hit rate / win rate / expectancy.** §5e records the pass bar as
   owed by the operator, stated before the numbers are read; under 15 per side is
   inconclusive. Describe rows; leave the verdict to them.
5. **Keep populations apart:** `5c`, `zone`, and quarantined legacy rows are three
   different things. Never pool them.
