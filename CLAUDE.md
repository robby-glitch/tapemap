# CLAUDE.md

**Read [START-HERE.md](START-HERE.md) in full before doing anything in this
repo — and if your task touches the DESK, read [HANDOFF-DESK.md](HANDOFF-DESK.md)
in full too.** Everything else is history or detail. Verified 2026-08-22.

## Current state (2026-10-24): read these before anything newer than 19 Oct

- **`docs/live/NOTEPAD.md`** is the live backlog. Every gap A1–A49 has a status, there are day observations, and it lists the decisions pending on Mary's word. Read it first.
- **Locked setups and registrations:** `context/research-findings.md`:
  - §1i FADE, §1j RIDE, §1l READ-2, §1m HOLD v2, §1n FADE-D, §1o One-Sided Meter, §1p VALIDATE rev 3, §1q SENSEX reads NIFTY's
    order flow (VALIDATE rev 3.1 + HOLD v2 Amendment 3, `sensex_flow.py`, signed 25 Oct);
  - full texts in `docs/setup-review/` and `docs/read/`, with sha256 anchors in §1.
  - Never change one; a change is a new registration.
- **The live read stack:** `read.py` (THE READ), `decode.py` (the DECODE block: swing legs, 7 signs, lines incl. EFFORT), `onesided.py` (day type), `effort.py` (effort per point, Fable's tested definition, [I]), `confluence*.py` / `ride.py` / `faded.py` / `hold2.py`. Forward logs: `data/read/`, `data/decode/`, `data/onesided/`, `data/confluence_log.jsonl`, `data/grade/`.
- **Market facts that changed:**
  - **The CAS closing auction (3 Aug 2026)** freezes the cash index at ~15:15. PD levels come from bars ≤ 15:15 (`levels.fetch_daily`), not the auction print.
  - **F&O trades until 15:40.** The futures recorders stop at 15:40; the option chain still stops at 15:30.
  - **SENSEX futures are too thin** for order-flow reads ("patla" stamps).
- **In a trade (24 Oct):** her open marked trade gets ONE block, display only, computed once in the server and rendered verbatim on the panel, the floating window (`ui-v2/src/pro/Float.tsx`; `hold/HoldWindow.tsx`'s window is not mounted) and Validate.
  - **`voice.py`** is THE ONE VOICE: the ladder EXIT > WARN > TIGHTEN > HOLD, with one stop (HOLD v2's line).
  - **`trademap.py`** adds two lines and a detail list:
    - l4: push, ulta push, and the day's range used in EM;
    - l5: the pullback zone (the wall ahead, never a "target"), plus a survivor EFFORT read and her BADA PRINT when at it;
    - [detail]: fuel pinned at entry, levels, R, a sale's premium path and the W-BLEED gauge.
  - **Where it runs:** `server._hold2_run` and `_in_trade`; forward log `data/hold/map_<day>.jsonl`.
  - **Replay:** `voice_path.py` and `GET /api/voice_path` replay it over a past marked trade, never in market hours.
  - **Docs:** `docs/trade-map/` (Fable's critique and the build report), the spec `docs/superpowers/specs/2026-10-24-trade-map-design.md`, and NOTEPAD A52–A63. Her display basis `fold.BIX_MS` is a 3-min median (A60).
- **The face:** the GoCharting extension v2.12 (0.5.12) in `C:\Users\kaam\Desktop\Go charting\orderflow-desk\dist-v2`. See its `docs/V2-BUILD-REPORT.md`.
- **Clean-room research:** `C:\Users\kaam\Desktop\operator mode\oi-lab\` (Fable): the OI and order-flow world maps, the flow AUDIT (291 variants, two holdouts), and the Edge Reader weave. Its conclusions:
  - only effort per point survived;
  - CVD divergence at highs is inverted;
  - OI speed at extremes does not separate holds from breaks.
- **The end-of-day job** (`eod_capture.bat`, 15:35): capture, the trigger_log scorer, then `tools/mark_grade.py`. The move to 15:45 awaits her OK.

## Which of the two instruments are you working on?

They share one server and one repo and answer opposite questions. Confusing
them is the fastest way to waste a session.

- **THE TAPE** — *when is a move coming*, a buyer's question. `engine.py`,
  `band_rotation.py`, the zone machine, `data/trigger_log.jsonl`.
  START-HERE.md is its document. (`/console.html` was cut 25 Oct, review C9.)
- **THE DESK** — *which instrument, and which structure*, a seller's desk.
  `surface.py`, `direction.py`, `drag.py`, the war map (`warmap.py` +
  friends). HANDOFF-DESK.md is its document. **Deleted 2026-09-28** (the
  ponytail cleanup, `docs/review/PONYTAIL-REVIEW-2026-09-28.md`): `desk.py`,
  the paper desk (`trader.py`, `book.py`, `quoting.py`, `hedge.py`) and the
  old `/desk.html` and `/toolb.html` screens. The live UI is ui-v2 on 5173.

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
python -m pytest -q            # 1993 collected: 1991 pass, 1 skipped, 1 known flaky (test_v2feed serve-cache, NOTEPAD A49), as of 2026-10-25 (review Phase 4, the cuts)
```

**Launch the server DETACHED, never as a child of an assistant/terminal
session** (2026-08-25: a host-process restart killed a child server mid-market
and cost 30 minutes of every forward log):
`Start-Process -FilePath '...\start-v2.bat' -WorkingDirectory '...\tapemap' -WindowStyle Minimized`

Screens: ui-v2 on `http://127.0.0.1:5173/` (the live UI; `/` redirects there).
APIs: `/api/surface` · `/api/drag` (both read by her PaperDesk extension) ·
`/api/chain` · `/api/vpin` · `/api/oiflow` · `/api/warmap` ·
`/api/paper_fill` (PaperDesk's POST) · `/api/health` (its `coverage` says what this process can
and cannot know about today — render it, never paper over it).

**The anytime-start rule (operator, 2026-08-25, standing):** every module must
be correct no matter WHEN the server or UI is started — backfill exactly
(tagged, never blended with observed), persist day state across restarts, and
whatever genuinely cannot be reconstructed must say so with the reason.

**`data/trigger_log.jsonl` is the one irreplaceable artefact in this repo** and
is deliberately NOT committed on this branch — see HANDOFF-OPERATOR.md §6
before touching it.
