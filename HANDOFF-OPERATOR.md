# Operator layer — handoff

**Written 2026-08-20 evening. Branch `feature/operator-objects`, off
`feature/dashboard-v2`.** Read `START-HERE.md` first; this covers only what was
added on 2026-08-20 and the traps found while adding it.

Everything here is **forward-logged and gates nothing.** No module has a track
record. The clock starts at the next open.

---

## 0. The thesis, in one sentence

Books force hedging → hedging is the flow → **trapped inventory is the fuel** →
forced flow is the only edge retail can reliably follow → flat until the machine
shows its gear.

Three conditions, and they are a **sequence, not a state** — the covering that
prints DRAIN also relieves the pain that was the FUEL, so they never co-occur on
one bar:

| condition | meaning | who supplies it |
|---|---|---|
| FUEL | writers trapped and in pain | `chainside` (needs the chain) |
| IGNITION | aggression arriving at extreme size | `fuse` (from the book) |
| DRAIN | the trapped side actually leaving | `chainside` (needs the chain) |

---

## 1. What was built

All pure computation, stdlib only, no I/O, born with tests. **No live-path file
imports any of them** — `engine.py`, `live.py`, `band_rotation.py`,
`chain_metrics.py` and `trigger_log.py` are untouched. Only `server.py` imports
them, deliberately.

| module | answers |
|---|---|
| `trapped_inventory.py` | is the inventory behind this OI comfortable or in pain? |
| `forcing.py` | fuel+ignition ARM a window; drain confirming inside it FIRES |
| `sweep.py` | levels consumed — `swept` / `pulled` / `unknown` |
| `absorption.py` | a level that ate more than it ever showed |
| `depth_pull.py` | size leaving a side with nothing traded against it |
| `pools.py` | terrain: shelves, vacuums, and wall-vs-cluster |
| `drag.py` | the buyer's tax, on real delta |
| `fuse.py` | where a magnitude becomes a verdict (ranking lives here) |
| `chainside.py` | fuel and drain, which the book cannot see |
| `regime.py` | PIN / TRANSITION / CASCADE — **shadow only** |
| `senses.py` | runs the book detectors, forward-logs them (**the only one touching disk**) |

Plus `upstox_adapter.depth_ladder()` (the full book, previously discarded) and
`ui/console.html`.

---

## 2. Traps found the hard way — do not rediscover these

1. **Upstox sends TEN price levels, five a side.** Its docs count `Quote`
   structs ("5 market level quotes"); Kite counts prices ("10 depth entries").
   Same book. `full_d30` is the only deeper mode (30 structs = 60 prices,
   Upstox Plus, 50-key cap).

2. **Upstox pairs a bid AND an ask inside ONE `Quote`.** Slicing that array
   removes levels from *both* ladders — a two-sided collapse, not an aggressor.
   A test fixture that did this simulated the wrong event entirely.

3. **`host_permissions` does NOT exempt a content script from CORS.** The
   bridge's fetch carries `kite.zerodha.com` as its Origin, so the manifest
   looks perfectly correct while every POST fails. Fixed with `do_OPTIONS` +
   `Access-Control-Allow-Origin` scoped to that one host. **Never a wildcard** —
   this server accepts market data that feeds a reading, and any page the
   browser visits could otherwise hand it fabricated depth.

4. **A percentile-so-far scores every new maximum at 1.00.** A rising series
   therefore reads as ignition that never switches off. `fuse` takes the MOST
   RECENT sweep, not the window's maximum, and the test fixtures are
   deliberately non-monotonic because a monotonic warm-up hides this exactly.

5. **`Sweep.kind` collided with the log envelope's row identity** and silently
   overwrote it, making every row look alike. The envelope now wins and the
   field is `det`. Caught before a single row was written; a forward log cannot
   be repaired after the fact.

6. **Volume scoping matters.** Watching every subscribed leg produced 2,186
   rows in 73 seconds across 101 instruments (~170MB/session) — and the loudest
   were deep-OTM strikes 700+ points from spot, where thin books make every
   flicker look like a five-level sweep. Now: the future plus
   `SENSES_EACH_SIDE=3` strikes either side of spot.

7. **A 7-point touch on the NIFTY future** appeared in a live absorption
   window. That breaks the module's proof (trades could have happened inside
   the spread), which is why `spread` rides on every absorption event.

---

## 3. Where things write

| what | where | note |
|---|---|---|
| book detector rows | `data/senses/senses_YYYY-MM-DD.jsonl` | **gitignored**, one file per day, ~80MB/session |
| the forward record | `data/trigger_log.jsonl` | **NOT committed on this branch** — see §6 |
| live frame fixture | `data/feed_frame_2026-08-20.json` | committed; four tests pin the ladder against it |

A senses row is `{day, t, inst, key, det}` plus the event's own fields. `det` is
`sweep` / `absorption` / `pull`. **It is a measurement, not a signal** — no
direction, no outcome. Scoring means asking later what followed, and that
question cannot be asked unless the rows exist first.

---

## 4. Running it

```bash
cd "C:\Users\kaam\Desktop\operator mode\tapemap"
TAPEMAP_BROKER=upstox python server.py live      # or start-v2.bat
```

- Console: **http://127.0.0.1:8765/console.html**
- API: `/api/senses?n=200` — rows, `read` (gear + evidence), `pools`,
  `orders_bridge`, `pending`
- Extension: **load unpacked** `operator mode\paperdesk\v1.21.1`
  (a folder, never a zip). Diagnostic in the Kite console: `__pdBridge()`.

**As of 2026-08-20 19:16, port 8765 runs THIS sandbox copy.** The process that
had held it since 2026-08-19 12:16 was the original repo and was stopped.
Restore with `cd "new tool nifty" && start-v2.bat`.

---

## 5. What is NOT done

- **Nothing has a track record.** One afternoon of rows. `regime`'s kill
  condition: deleted, not tuned, if ~30 scored sessions do not show that
  blocking would have helped.
- **The Kite bridge has never carried live data.** Built and wired after the
  close; CORS was fixed at 19:45 with the market shut. First real test is
  09:15. Until then every shelf reads "wall vs cluster needs the kite bridge".
- **`chainside` has never seen a live chain** — built after close, when
  `/api/chain` returns "market closed".
- ~~**`drag` is not wired into anything.**~~ **WIRED 2026-08-22.** `drag.Board` is fed by the senses loop and published at `/api/drag`; the desk screen carries it as "the tax on being right".
- **The §5e pass bar is still owed by the operator.** 22 `5c` and 39 `zone`
  scored rows sit unread because nobody has stated the bar. **Never print a
  hit rate.**

---

## 6. The one thing to be careful with

**`data/trigger_log.jsonl` is deliberately NOT committed on this branch.**

Row counts in the sandbox and the live original are identical (256 legacy · 22
`5c` + 47 arms · 39 `zone` + 93 arms) but the files are **not byte-identical**.
Committing one over the other risks corrupting the only irreplaceable artefact
in the project. Treat `new tool nifty\data\trigger_log.jsonl` as authoritative.

**And the operational split to resolve before the next open:** `eod_capture` is
a Windows scheduled task pointing at the ORIGINAL folder, while the server now
running on 8765 is this sandbox copy. So tomorrow the sandbox logs the signals
and the original gets scored. Either repoint the task, or run the original on
8765 and this copy elsewhere. **Decide this before 09:15.**

---

## 7. First moves next session

1. **Before the open** — resolve §6's split. It is the only thing that can lose
   a day of the forward record.
2. **At 09:15** — watch `/console.html`. Confirm `kite bridge: N books` appears
   and shelves start classifying wall/cluster. That is the last unproven link.
3. **After the close** — read one day of `data/senses/` and ask the only
   question that matters: does anything follow a sweep, an absorption, a pull?
   Not "is the code right" — it is — but "does this measure anything".
4. Wire `drag` into the console; it is the meter that says whether being right
   is even payable today.
