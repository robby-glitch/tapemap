# VALIDATE 2 — build plan (one long evening; build only after PREREG-DRAFT.md is signed)

Reuse beats rebuild: two new pure modules, three routes, one new face. Nothing in fold.py's rules, hold.py, validate.py,
expression.py, story.py, grounds.py, daytype.py, fronts.py or the logs they write is changed.

## 0. Files

| file | change | size |
|---|---|---|
| `validate2.py` (new, pure, stdlib) | the ten checks (`checks(view, facts)`), the word (`word(checks, own)`), the rank key and slots (`board(cands, hers)`), the ledger (`ledger(entry_snap, view, facts)`), `zone_alone(view)`, `pullback_gaveup(view, bleed, fights)`, `bleed(W_watch)`; every function hands back `{state, text, absence}` rows | ~350 lines |
| `read2.py` (new, pure, stdlib) | `compose(packet)` → the sections of §2 of DESIGN.md; `pin(chain)`, `pcr9(grid, t)`, `level_lines(levels, statics, basis_ix, fut)`, `falsifiers(packet)`; the packet's number set for the later polish layer | ~300 lines |
| `fold.py` | `flat_view` adds `vwap`, `cvd` (per-minute cumulative b − s off `self.bars`), `sess` ({hi, hi_t, lo, lo_t}); `_OIWatch` gains `off_pct()` and `n_since_peak()` (two one-liners on fields it already keeps) | +25 lines |
| `fold_live.py` | `READ_EVERY_S` → per index: 1 s when the index has an open marked trade, else 3 s; `Engine.ask_board(atm, step)` asks the six candidate keys through `ask_ifin` (the existing 10-s / 60-s cache); `Engine.entry_snap[tid]` frozen at `sync()` when a trade is first built | +40 lines |
| `server.py` | three GET routes (§1); a per-minute writer for `data/validate2/intrade_<day>.jsonl` inside `_hold_tick`; `check_<day>.jsonl` written by the check route only with `log=1` | +120 lines |
| `ui-v2/src/pro/Validate2.tsx` + `validate2.css` (new) | the face (§3); mounted as the `Validate` tab in `App.tsx` in place of the current Validate tab body; the DESK (`/pro.html`) and the Float untouched | ~450 + 120 lines |
| `test_validate2.py`, `test_read2.py` (new) | §4 | ~250 lines |

## 1. Endpoints (all GET, all served from caches; no request reads a day file)

- `GET /api/validate2?idx=` — the in-trade read every second: `{ok, idx, asof, ages{book_s, chain_s, vpin_s, gc}, trade, engine: <the /api/fold reply's view>, ledger[], zone_alone, pullback, bleed, reversal (validate_live's when the frame is alive), theta, practice_1500, tag}`; flat: `{in_trade:false, flat: <fold/flat>, ages, …}`.
- `GET /api/validate2/check?idx=&k=&ty=&side=[&p0=][&log=1]` — the ten checks + word + levels + the board for that index (six candidates) and the two other indices' boards if their engines are up (18); `log=1` writes the press row and the top-of-board row.
- `GET /api/read?idx=[&all=1]` — the market read: `{packet, sections[{name, lines[{text, tag, absence}]}], best[], falsifiers[]}`. `all=1` adds the other two indices' §2.1 lines and their boards.

Inputs each route composes from (already cached in the process): `fold_live` (flat, ifin, trade replies, entry snaps), `_SENSES["frame"]` (validate / story when the extension posts), `_daytype_reply`, `_expr_reply`, `board.read` (fronts), `_calls_for` facts, `xindex_live.read()`, the VPIN gauge state, `_feed_read`, the senses rows of the day, `levels` statics from the warmap's cache, `trade_record` timers.

## 2. The 1-second loop

Already there: `fold_live.run(period=1.0)` feeds rows 2 s after their key and refreshes `flat_read` / trade replies every `READ_EVERY_S`. Change: `refresh()` uses 1 s for an index in `{t.idx for t in trades if not t.exit_t}`, 3 s otherwise. `/api/validate2` is a dict assembly over those caches (< 5 ms). The face polls it every 1,000 ms with a 900-ms timeout and shows *"could not check — the engine is not answering (hh:mm:ss)"* on a miss, keeping the last read greyed. The ages strip is computed from each source's own last timestamp (book `t`, chain `ts`, VPIN `at`, feed_health `last_post`), never from a timer.

Per minute (inside `_hold_tick`, which already runs per index per minute): write the in-trade row (zone_alone, pullback word, bleed, the engine's word, chips) — write-once, keyed (trade_id, minute).

## 3. The face — `Validate2.tsx`

One column, light, `pro.css` tokens, no charts.
1. **ABHI strip** (always): three index cells — spot / fut (basis), daytype word + since, whose day, Z/F/O/V flat chips with Hinglish tags, next fight above / below; the ages strip; expiry chips; the 15:00 practice from 14:45; `FeedBand`.
2. **Mode card**: flat → the slip (reuse `Mark.Slip`) + VALIDATE + MARKET READ (Enter = read when the slip is empty, validate when filled); after a read → sections 2.1–2.10 as cards, numbers tabular, every chip with its Hinglish tag; after a check → the word (big, DRAFT tag), the count line, the ten checks as rows (counted first, printed under a rule), the levels block (spot | fut columns), the BETTER TRADE card (three slots + top three); in a trade → the in-trade face (DESIGN §5.2) with the two buttons in a row.
3. **LEVELS TO WATCH** (always): six lines for the focused index from `/api/read`'s `level_lines` (re-read every 10 s; the ABHI strip's 1-s read stamps a level amber when price prints within w of it).
4. **Footer**: the three absences, always three lines.
Keyboard: `Enter` press, `Esc` back to the slip, `1/2/3` focus index. No sound beyond the engine's existing tone.

## 4. Tasks, in order (with the check that proves each)

| # | task | proves it |
|---|---|---|
| 1 | `fold.py`: `flat_view` adds `vwap`, `cvd`, `sess`; `_OIWatch.off_pct / n_since_peak` | `test_fold.py` still green; one new test: a synthetic day's `cvd` equals the ladder sum |
| 2 | `validate2.py`: checks + word + board rank on frozen fixtures = the eight REPLAY rows (`scratch/v2_*.txt` as JSON fixtures) | `test_validate2.py::test_replay_rows` reproduces every word and count |
| 3 | `validate2.py`: ledger, zone_alone, pullback_gaveup, bleed | tests on today's 22650 PE path (`scratch/path_1006_pe.txt`): bleed amber first at 10:42, ZONE ALONE from 11:06, GAVE UP from 11:21 |
| 4 | `read2.py`: compose on a packet with every absence kind; pin, pcr9, level_lines | `test_read2.py`: three absences never collapse; every number in the text is in the packet |
| 5 | `fold_live.py`: 1-s read cache in a trade; `ask_board`; entry snaps | `test_fold_live.py` + one test: the entry snap is frozen at the first build and survives `sync()` |
| 6 | `server.py` routes + the per-minute writer | `test_validate2_route.py`: a check without `log=1` writes nothing; with it, one press row and one board-top row; `/api/read` answers with the engine down (every section an absence) |
| 7 | `Validate2.tsx` + mount | Vite build green; the fixture viewer `?fixture=1` renders the three states (read / check / in-trade) from `scratch/` JSON |
| 8 | docs: DESIGN → `docs/validate2/`, PREREG signed + hashed, `context/research-findings.md` §1i, `START-HERE.md` pointer | `test_docs_claims.py` |

Time: 1 (0.5 h) · 2 (1.5 h) · 3 (1 h) · 4 (1.5 h) · 5 (0.5 h) · 6 (1 h) · 7 (2.5 h) · 8 (0.5 h) ≈ one long evening. The LLM polish (`read2_llm.py`, number-locked) and T2's premium interpolation past the chain's edge are the next evening.

## 5. What stays untouched
fold.py's rules and events; fold_log; hold.py / hold_log / plan.py / validate.py (rev 2 keeps its clock and its `check_<day>.jsonl`); expression.py; story.py; grounds.py; daytype.py; fronts.py; sides / trap / xindex; the DESK (`Pro.tsx`, `Desk.tsx`, `Float.tsx`); the GoCharting extension; every recorder; `data/trigger_log.jsonl`. No new dependency. No order path. CRLF in `server.py` kept. Commit on her word.

## 6. Anytime start
`/api/read` and `/api/validate2` are assemblies over caches that the anytime-start rule already covers (fold_live rebuilds from the day files; daytype / fronts / xindex rebuild from their logs). Entry snaps for a trade marked before a restart are rebuilt from the engine's own `seed` event row (fold_log keeps it); the ledger says `src: rebuilt`. The in-trade minute log is write-once, so a restart never double-writes.
