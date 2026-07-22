# Multi-Index TapeMap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## ✅ IMPLEMENTATION STATUS — 2026-07-23 (all code shipped)

Executed inline this session. Files created/modified: **`instruments.py`** (new), **`test_instruments.py`** (new, 4 tests pass), **`live.py`**, **`chain_live.py`**, **`server.py`**, **`ui/index.html`**, **`ui/app.js`**, **`ui/style.css`** (pill + `?v` bumps to `app.js?v=15`/`style.css?v=12`).

| Task | State | Evidence |
|---|---|---|
| 0 Discovery | ✅ done | IDs confirmed live; see spec "Resolved facts". |
| 1 `instruments.py` | ✅ done + verified | `pytest test_instruments.py` = 4 passed; `resolve_dynamic` returns fut_ids 61093/61088/1144507 live. |
| 2 `live.py` | ✅ code done; ⏳ bar-path verify pending market hours | payload shape + `"index"` field + clean "no bars yet" verified for all 3; **`_atm_ids` was generalized to the detailed CSV / nearest-strike (SENSEX `BSXOPT`) — an addition beyond the original Task 2 steps.** |
| 3 `chain_live.py` | ✅ done + verified live | all 3 indices publish `ok`; 3-min round-robin soak, zero throttle; per-index isolation shown. |
| 4 `server.py` | ✅ done + verified live | `/api/data?idx=` & `/api/chain?idx=` keyed; no-`idx`→NIFTY. |
| 5 UI switcher | ✅ done + verified in browser | pill switches all 3, chain analyser renders per index, zero console errors, no leaked pollers. |
| 6 Soak/correctness | ⏳ partial | chain soak + isolation ✅; validator/SCAN/MAP/TAPE correctness awaits a market-hours session (bars only exist 9:15–15:30 IST). |

**Deviations from the written plan (intentional, verified better):**
- **`_atm_ids` generalized** (Task 2): SENSEX options carry the generic symbol `BSXOPT`, so leg resolution matches on `UNDERLYING_SYMBOL`/`OPTION_TYPE`/`STRIKE_PRICE` from the detailed scrip CSV and picks the nearest listed strike. Not in the original Task 2 step list.
- **`chain_seg` is unused** — `option_chain` takes only `(under_id, under_seg, expiry)`; kept in the registry for documentation only.
- **Live-mode detection** in `ui/app.js` uses `S.data.live || S.data.index` (not just `live`) so the 60s refresh + ●LIVE badge arm even when the server starts pre-market (no bars yet).
- **No git commits** (not a repo).

**To finish Task 6 at the next open:** load `http://localhost:8767/`, switch the pill to BANKNIFTY then SENSEX, and confirm each index's TAPE view, VALIDATE popup (±6 strikes, T1/T2/T3, market-view read), and SCAN populate from that index's own bars with zero console errors; break one index's `under_id` temporarily to reconfirm the others keep serving (isolation).

**Goal:** Add BANKNIFTY (NSE) and SENSEX (BSE) alongside NIFTY, switchable from a header pill, all served by one backend via `?idx=` on `/api/data` and `/api/chain`.

**Architecture:** The engine, chain metrics, gamma math, and all UI validator/scan/MAP/chain logic are index-agnostic and stay untouched. A new `instruments.py` registry parameterizes the feed; `live.py` and `chain_live.py` take an instrument config; `server.py` serves per-index keyed payloads; the UI gains an `S.index` switcher that threads `?idx=` through every fetch.

**Tech Stack:** Python 3 stdlib + `dhanhq` SDK (backend), vanilla JS single-file UI, Dhan REST (intraday charts + option_chain).

## Global Constraints

- **Not a git repository.** Do NOT run `git` commit steps; each task ends at a live/functional verification. (Offer `git init` separately if the user wants it.)
- **Never regenerate/authenticate the Dhan token.** `.dhan_token` is the user's own JWT, refreshed manually daily. Read it, never write it.
- **Dhan rate limit:** ~1 unique `option_chain` request per 3s — the multi-index chain poller must round-robin, never fire 3 chain requests inside 3s.
- **Reuse verbatim, do not modify:** `engine.py`, `chain_metrics.py`, `gamma.py`, and the validator/scan/MAP/chain-analyser logic in `ui/app.js`.
- **GateGuard hook** is active: every first Bash and every Edit/Write requires the 4 facts (importers, affected functions, data schema, verbatim instruction) then a retry. Budget for it.
- **Cache-buster:** `index.html` references `app.js?v=N` / `style.css?v=N`; a hook auto-bumps on edit.
- Live server config `tapemap-live` runs on port **8767**. Backend (Python) edits require a server restart; frontend edits do not.

---

### Task 0: Discovery — resolve real Dhan identifiers (spike)

Confirm the volatile facts the registry needs. This is a read-only investigation against live Dhan; its output populates Task 1's config. No code ships.

**Files:** none (scratch script only, in the scratchpad dir).

- [ ] **Step 1: Fetch the Dhan scrip master and locate index + futures rows**

Download the detailed instrument master and inspect rows for the three underlyings:

```bash
curl -s "https://images.dhan.co/api-data/api-scrip-master-detailed.csv" -o "$SCRATCH/dhan_scrip.csv"
python - <<'PY'
import csv, os
p=os.path.join(os.environ["SCRATCH"],"dhan_scrip.csv")
rows=list(csv.DictReader(open(p,encoding="utf-8")))
print("cols:", list(rows[0].keys()))
for u in ("BANKNIFTY","SENSEX","NIFTY"):
    fut=[r for r in rows if u in (r.get("UNDERLYING_SYMBOL","") or r.get("SM_SYMBOL_NAME","")) and "FUT" in (r.get("INSTRUMENT","")+r.get("INSTRUMENT_TYPE",""))]
    print(u, "futures rows:", len(fut))
    for r in sorted(fut, key=lambda x:x.get("SM_EXPIRY_DATE",""))[:3]:
        print("  ", {k:r[k] for k in list(r)[:8]})
PY
```

Expected: the exact column names for security-id, exchange segment, instrument type, expiry, and underlying; the nearest-expiry FUTIDX security-id for BANKNIFTY (NSE) and SENSEX (BSE), plus their index underlying security-ids and segments.

- [ ] **Step 2: Verify `option_chain` + `expiry_list` work per index**

Using the existing SDK client (`chain_live._client`, `chain_live._inner`), confirm the underlying id/segment that returns a valid chain for each index — especially SENSEX (BSE): test whether `under_seg` is `"IDX_I"` or a BSE-specific value.

```bash
cd "/c/Users/kaam/Desktop/new tool nifty"
python - <<'PY'
from chain_live import _client, _inner, read_token
d=_client(read_token())
for name,uid,seg in [("BANKNIFTY",25,"IDX_I"),("SENSEX",51,"IDX_I")]:  # ids are guesses to confirm
    try:
        exp=_inner(d.expiry_list(uid,seg))
        print(name,"expiry_list OK ->", (exp.get("data") if isinstance(exp,dict) else exp)[:2])
    except Exception as e:
        print(name,"FAIL", e)
PY
```

Expected: for each index, the correct `(under_id, under_seg)` pair that returns an expiry list; note the working values.

- [ ] **Step 3: Record findings**

Write the confirmed values (per index: `under_id`, `under_seg`, `chain_seg`, `fut_seg`, `fut_id` for nearest expiry, `expiry`, `step`, `window`) into the scratchpad as `multi_index_ids.md`. These feed Task 1 directly.

Expected deliverable: a table of confirmed identifiers. If SENSEX (BSE) access fails here, stop and report — BANKNIFTY can still proceed; SENSEX becomes a later config drop-in.

---

### Task 1: Instrument registry — `instruments.py`

**Files:**
- Create: `instruments.py`
- Test: `test_instruments.py`

**Interfaces:**
- Produces:
  - `INSTRUMENTS: dict[str, dict]` — static config per index.
  - `ENABLED: list[str]`, `DEFAULT: str`.
  - `get(idx: str) -> dict` — returns a shallow copy of the config for `idx` (raises `KeyError` on unknown).
  - `resolve_futures_id(rows: list[dict], under_sym: str, today: str) -> tuple[str, str]` — pure function: given parsed scrip-master rows, an underlying symbol, and today's `YYYY-MM-DD`, returns `(fut_security_id, fut_expiry)` for the nearest non-expired monthly future. Column names come from Task 0.
  - `resolve_dynamic(cfg: dict, tok: str, today: str) -> dict` — returns `cfg` augmented with `fut_id`, `expiry`, `prev_day` (fetches scrip master + `expiry_list`; calls `resolve_futures_id`).

- [ ] **Step 1: Write the failing test for the pure resolver**

```python
# test_instruments.py
from instruments import resolve_futures_id, get, INSTRUMENTS, DEFAULT

def test_resolve_futures_id_picks_nearest_unexpired():
    # column names per Task 0 findings; adjust keys to the real scrip-master schema
    rows = [
        {"SECURITY_ID": "111", "UNDERLYING_SYMBOL": "BANKNIFTY", "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-07-29"},
        {"SECURITY_ID": "222", "UNDERLYING_SYMBOL": "BANKNIFTY", "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-08-26"},
        {"SECURITY_ID": "333", "UNDERLYING_SYMBOL": "NIFTY",     "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-07-29"},
    ]
    sid, exp = resolve_futures_id(rows, "BANKNIFTY", "2026-07-23")
    assert sid == "111" and exp == "2026-07-29"

def test_resolve_futures_id_skips_expired():
    rows = [
        {"SECURITY_ID": "111", "UNDERLYING_SYMBOL": "SENSEX", "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-07-20"},
        {"SECURITY_ID": "222", "UNDERLYING_SYMBOL": "SENSEX", "INSTRUMENT": "FUTIDX", "SM_EXPIRY_DATE": "2026-08-28"},
    ]
    sid, exp = resolve_futures_id(rows, "SENSEX", "2026-07-23")
    assert sid == "222"

def test_get_returns_copy_with_defaults():
    cfg = get(DEFAULT)
    assert cfg["under_id"] == 13 and cfg["step"] == 100
    cfg["step"] = 999
    assert get(DEFAULT)["step"] == 100     # get() must return a copy
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python -m pytest test_instruments.py -v`
Expected: FAIL (`ModuleNotFoundError: instruments`).

- [ ] **Step 3: Implement `instruments.py`**

Use the confirmed column names / IDs from Task 0. Skeleton (fill IDs from Task 0):

```python
"""Instrument registry: one config per tradable index. Static fields here;
volatile fields (futures security-id, current expiry, prior trading day)
resolved at startup from the Dhan scrip master + expiry_list."""
import csv, io, urllib.request
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
SCRIP_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"

# under_id / under_seg / chain_seg / fut_seg confirmed in Task 0
INSTRUMENTS = {
    "NIFTY":     {"under_id": 13, "under_seg": "IDX_I", "chain_seg": "NSE_FNO",
                  "fut_seg": "NSE_FNO", "step": 100, "window": 1500, "under_sym": "NIFTY"},
    "BANKNIFTY": {"under_id": 25, "under_seg": "IDX_I", "chain_seg": "NSE_FNO",
                  "fut_seg": "NSE_FNO", "step": 100, "window": 2000, "under_sym": "BANKNIFTY"},
    "SENSEX":    {"under_id": 51, "under_seg": "IDX_I", "chain_seg": "BSE_FNO",
                  "fut_seg": "BSE_FNO", "step": 100, "window": 2500, "under_sym": "SENSEX"},
}
DEFAULT = "NIFTY"
ENABLED = ["NIFTY", "BANKNIFTY", "SENSEX"]

# column keys per Task 0 findings
COL_SID, COL_UND, COL_INSTR, COL_EXP = "SECURITY_ID", "UNDERLYING_SYMBOL", "INSTRUMENT", "SM_EXPIRY_DATE"

def get(idx):
    return dict(INSTRUMENTS[idx])

def _load_scrip():
    with urllib.request.urlopen(SCRIP_URL, timeout=30) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8", "ignore"))))

def resolve_futures_id(rows, under_sym, today):
    cands = [r for r in rows
             if r.get(COL_UND) == under_sym and "FUT" in (r.get(COL_INSTR) or "")
             and (r.get(COL_EXP) or "") >= today]
    if not cands:
        raise RuntimeError(f"no unexpired future for {under_sym}")
    r = min(cands, key=lambda x: x.get(COL_EXP))
    return r[COL_SID], r[COL_EXP]

def _prev_trading_day(today):
    d = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=IST) - timedelta(days=1)
    while d.weekday() >= 5:                      # skip Sat/Sun
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")

def resolve_dynamic(cfg, tok, today):
    rows = _load_scrip()
    cfg["fut_id"], cfg["expiry"] = resolve_futures_id(rows, cfg["under_sym"], today)
    cfg["prev_day"] = _prev_trading_day(today)
    return cfg
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m pytest test_instruments.py -v`
Expected: 3 passed. (Adjust `COL_*` constants to match Task 0's real column names until green.)

- [ ] **Step 5: Verify live resolution end-to-end**

Run: `python -c "import instruments as I; c=I.resolve_dynamic(I.get('BANKNIFTY'), open('.dhan_token').read().strip(), '2026-07-23'); print(c['fut_id'], c['expiry'], c['prev_day'])"`
Expected: a numeric fut_id, a future expiry date, and the prior weekday. Repeat for SENSEX. **Deliverable:** registry resolves all three indices.

---

### Task 2: Parameterize the live feed — `live.py`

**Files:**
- Modify: `live.py` (module globals → `build_payload(cfg)`; `_pick_strike` per-index; `_intraday` segment from cfg)

**Interfaces:**
- Consumes: `instruments.get`, `resolve_dynamic`; a resolved `cfg` dict with `fut_id, fut_seg, expiry, prev_day, step, under_sym`.
- Produces: `build_payload(cfg: dict) -> bytes` — same JSON shape as today plus `"index": cfg["under_sym"]`. `_pick_strike(F, cfg)` keyed by `cfg["under_sym"]`.

- [ ] **Step 1: Make `_intraday` segment-aware**

`live.py` currently hardcodes `exchangeSegment="NSE_FNO"`. Change `_intraday(tok, sec_id, instrument, day, oi=True, seg="NSE_FNO")` and pass `seg=cfg["fut_seg"]` at each futures/option call site. Show the edited signature and every call updated.

- [ ] **Step 2: Key the sticky-ATM state per index**

Replace the module-level `_stick = {"strike": None, "drift": 0}` with `_stick = {}` and make `_pick_strike(F, cfg)` read/write `_stick.setdefault(cfg["under_sym"], {"strike": None, "drift": 0})`, using `cfg["step"]` for the grid. Show the full rewritten `_pick_strike`.

- [ ] **Step 3: Convert `build_payload()` to `build_payload(cfg)`**

Replace uses of the `FUT_ID / EXPIRY / PREV_DAY / STEP` globals with `cfg["fut_id"] / cfg["expiry"] / cfg["prev_day"] / cfg["step"]`. Thread `cfg` into `_pivots`, `_bars`, `_pick_strike`, and the intraday calls. Add `"index": cfg["under_sym"]` to the returned JSON. Keep the standalone `__main__` working by resolving NIFTY: `cfg = resolve_dynamic(get("NIFTY"), _token(), <today>)`.

- [ ] **Step 4: Verify the NIFTY payload is unchanged in shape**

Run: `python -c "import instruments as I, json; from live import build_payload; c=I.resolve_dynamic(I.get('NIFTY'), open('.dhan_token').read().strip(), '2026-07-23'); p=json.loads(build_payload(c)); print(p['index'], p['strike'], p['expiry'], len(p.get('days',[]) or [p]))"`
Expected: `NIFTY <atm-strike> <expiry> ...` with a non-empty bar series — i.e. same content as before plus the `index` field.

- [ ] **Step 5: Verify BANKNIFTY payload builds**

Run the same one-liner with `'BANKNIFTY'`. Expected: `BANKNIFTY` with a plausible ATM (multiple of 100 near the BANKNIFTY spot) and bars. **Deliverable:** `build_payload(cfg)` works for ≥2 indices.

---

### Task 3: Multi-index chain poller — `chain_live.py`

**Files:**
- Modify: `chain_live.py` (`ChainPoller` takes a list of configs; per-index state/boxes; round-robin `_run_live`; per-index warm-start file)

**Interfaces:**
- Consumes: resolved config list; existing `ChainState`, `normalize`, `_client`, `_inner`, `token_status`.
- Produces: `ChainPoller(configs: list[dict], mock=False)` with `self.boxes: dict[str, dict]` (one `{"payload": ...}` per `cfg["under_sym"]`). `.start()` unchanged.

- [ ] **Step 1: Per-index state in `__init__`**

```python
def __init__(self, configs, mock=False):
    super().__init__(daemon=True)
    self.mock = mock
    self.configs = configs                       # list of resolved cfg dicts
    self.boxes = {c["under_sym"]: {"payload": None} for c in configs}
    self.states = {c["under_sym"]: ChainState() for c in configs}
    self.prevs = {c["under_sym"]: None for c in configs}
```

- [ ] **Step 2: Make `_publish` / `_fail` / `normalize` index-aware**

`_publish(self, idx, snap, metrics, expiry, mode, error=None)` writes to `self.boxes[idx]["payload"]` and reads `self.states[idx].series`. `normalize(data, now, window)` takes the per-index `window` (replace the module `WINDOW_PTS` use). Show both edited signatures and bodies.

- [ ] **Step 3: Round-robin `_run_live`**

Rewrite the live loop: resolve each cfg's expiry once (via `expiry_list(cfg["under_id"], cfg["under_seg"])`), warm-start each index from `data/chain/chain_<IDX>_<today>.jsonl`, then loop forever iterating `self.configs`, issuing ONE `option_chain(cfg["under_id"], cfg["under_seg"], expiry)` per index per outer pass, sleeping `max(0.5, 3.5 - elapsed)` **between indices** (not per full pass) so no two chain requests fire within ~3.5s. Persist per index to `chain_<IDX>_<today>.jsonl`. On per-index exception, tag that index's box and continue to the next index. Show the full rewritten `_run_live`.

- [ ] **Step 4: Mock mode per index**

`_run_mock` publishes the fixture to every enabled index's box (same fixture, keyed per idx) so the UI switcher works offline. Show the edited `_run_mock`.

- [ ] **Step 5: Verify the poller publishes all indices**

Temporary harness:
```bash
cd "/c/Users/kaam/Desktop/new tool nifty"
python - <<'PY'
import time, json, instruments as I
from chain_live import ChainPoller
tok=open(".dhan_token").read().strip()
cfgs=[I.resolve_dynamic(I.get(x), tok, "2026-07-23") for x in I.ENABLED]
p=ChainPoller(cfgs); p.start()
time.sleep(20)
for idx,box in p.boxes.items():
    d=json.loads(box["payload"]) if box["payload"] else {}
    print(idx, "ok" if d.get("ok") else d.get("error"), "atm", d.get("atm"), "strikes", len(d.get("strikes",[])))
PY
```
Expected: each of NIFTY/BANKNIFTY/SENSEX prints `ok`, a plausible ATM, and a non-empty strike list, with no Dhan rate-limit errors. **Deliverable:** one poller feeds all three.

---

### Task 4: Per-index serving — `server.py`

**Files:**
- Modify: `server.py` (`Handler` takes dicts; `do_GET` parses `?idx=`; `live` branch builds per-index payloads + one `ChainPoller`)

**Interfaces:**
- Consumes: `instruments.ENABLED/DEFAULT/get/resolve_dynamic`, `live.build_payload`, `chain_live.ChainPoller`.
- Produces: `/api/data?idx=<IDX>` and `/api/chain?idx=<IDX>` keyed responses; default `idx=NIFTY`.

- [ ] **Step 1: Handler holds per-index dicts + idx parsing**

Change `Handler.__init__(..., payloads=None, chains=None)`. Add a helper to parse the `idx` query param (via `urllib.parse.urlsplit`/`parse_qs`), defaulting to `instruments.DEFAULT`, clamped to `ENABLED`. In `do_GET`, `/api/data` → `payloads[idx]["payload"]`, `/api/chain` → `chains[idx]` (same warming/None handling as today). Show the edited `__init__`, the `_idx()` helper, and the two routed branches.

- [ ] **Step 2: `live` branch builds all indices**

```python
if argv and argv[0] == "live":
    import threading, time as _t
    from live import REFRESH_S, build_payload
    import instruments as I
    port = int(argv[1]) if len(argv) > 1 else 8765
    today = _t.strftime("%Y-%m-%d")
    tok = open(ROOT / ".dhan_token").read().strip()
    cfgs = {x: I.resolve_dynamic(I.get(x), tok, today) for x in I.ENABLED}
    payloads = {x: {"payload": build_payload(c)} for x, c in cfgs.items()}
    from chain_live import ChainPoller
    poller = ChainPoller(list(cfgs.values()), mock=mock_chain); poller.start()
    chains = poller.boxes

    def refresh():
        while True:
            _t.sleep(REFRESH_S)
            for x, c in cfgs.items():
                try: payloads[x]["payload"] = build_payload(c)
                except Exception as e: print("live refresh failed", x, e)

    threading.Thread(target=refresh, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", port),
                        partial(Handler, payloads=payloads, chains=chains)).serve_forever()
    return
```

- [ ] **Step 3: Restart the live server and verify routing**

Restart the `tapemap-live` config on 8767. Then:
```bash
for x in NIFTY BANKNIFTY SENSEX; do
  echo "== $x =="; curl -s "http://127.0.0.1:8767/api/data?idx=$x" | python -c "import sys,json;d=json.load(sys.stdin);print(d.get('index'),d.get('strike'),d.get('expiry'))"
  curl -s "http://127.0.0.1:8767/api/chain?idx=$x" | python -c "import sys,json;d=json.load(sys.stdin);print('chain',d.get('ok'),d.get('atm'),len(d.get('strikes',[])))"
done
```
Expected: each index returns its own `index`/`strike`/`expiry` and a keyed chain with a plausible ATM. `/api/data` with no `idx` returns NIFTY. **Deliverable:** backend serves three indices.

---

### Task 5: UI index switcher — `ui/index.html` + `ui/app.js`

**Files:**
- Modify: `ui/index.html` (header pill `#idxTabs`; bump `app.js?v`)
- Modify: `ui/app.js` (`S.index`, `IDXQ()` param helper threaded into every fetch, switch handler)
- Modify: `ui/style.css` (`#idxTabs` segmented pill)

**Interfaces:**
- Consumes: `/api/data?idx=` and `/api/chain?idx=` from Task 4.
- Produces: `S.index` state; `IDXQ(url)` → appends `?idx=${S.index}` (or `&idx=` if the URL already has a query).

- [ ] **Step 1: Add the header pill**

In `ui/index.html` `<header>`, after `#brand`, add:
```html
<nav id="idxTabs">
  <button data-idx="NIFTY" class="active">NIFTY</button>
  <button data-idx="BANKNIFTY">BANKNIFTY</button>
  <button data-idx="SENSEX">SENSEX</button>
</nav>
```

- [ ] **Step 2: Add `S.index` + the query helper in `ui/app.js`**

Add `S.index = "NIFTY";` to state init. Add:
```javascript
function IDXQ(url){ return url + (url.includes("?") ? "&" : "?") + "idx=" + S.index; }
```

- [ ] **Step 3: Thread `IDXQ()` through every fetch**

Wrap every data/chain fetch URL: the `/api/data` boot/refresh fetch, the chain poll in `renderMap` (`fetch("/api/chain")`), `refreshValModal`, `fetchChain`, and `scanRefresh`. Each becomes `fetch(IDXQ("/api/data"))` / `fetch(IDXQ("/api/chain"))`. List each call site with its edit.

- [ ] **Step 4: Add the switch handler**

```javascript
$("idxTabs").onclick = e => {
  const b = e.target.closest("button[data-idx]"); if(!b) return;
  const idx = b.dataset.idx; if(idx === S.index) return;
  S.index = idx;
  [...$("idxTabs").children].forEach(c => c.classList.toggle("active", c === b));
  // reset per-index state, then reload
  S.mapChain = null; S.mapChainT = 0; S.valStrike = null; S.valSide = "AUTO";
  chainStop && chainStop(); scanStop && scanStop();
  closeValModal && closeValModal();
  bootData();                      // re-fetch /api/data?idx= and re-render from scratch
};
```
Identify the existing initial-load function (the one that fetches `/api/data` and populates `S.day`) and expose/call it as `bootData()`; if the current subview is CHAIN/SCAN, restart its poll after load.

- [ ] **Step 5: Style the pill** in `ui/style.css` — segmented look matching `#viewTabs`/`#chSub`; active = accent. Show the CSS block.

- [ ] **Step 6: Verify in the browser (live)**

Reload `http://localhost:8767/`. Using the browser tools:
- Click BANKNIFTY → `S.index==="BANKNIFTY"`, `/api/data?idx=BANKNIFTY` fetched, header/book strip shows BANKNIFTY spot & ATM, chain analyser + validator (±6 strikes around BANKNIFTY ATM) + scanner all render.
- Click SENSEX → same for SENSEX.
- Click back to NIFTY → restored.
- `read_console_messages` → zero errors. No leaked pollers (only the active subview's timer runs).
**Deliverable:** the switcher works end-to-end for all three indices.

---

### Task 6: End-to-end + rate-limit soak

**Files:** none (verification only).

- [ ] **Step 1: Three-index soak**

Leave the live server running ~3 minutes. Confirm via `preview_logs` / server stdout that the round-robin chain poller shows no Dhan throttle/`poll failed` rate errors, and each index's `/api/chain?idx=` timestamp advances (~every ≤12s).

- [ ] **Step 2: Cross-index correctness spot-check**

For each index, open the VALIDATE popup, pick a strike, confirm the option numbers (premium/Δ/IV/OIΔ) and the T1/T2/T3 ladder + market-view read match that index's own chain (not NIFTY's). Confirm SCAN shows that index's method-aligned buys.

- [ ] **Step 3: Degradation check**

Confirm that if one index errors (e.g. temporarily break SENSEX's id), NIFTY and BANKNIFTY keep serving and switching — per-index isolation holds. Restore the id afterward.
**Deliverable:** all three indices live, correct, and isolated.

---

## Self-Review

- **Spec coverage:** registry (Task 1) ✓, feed params (Tasks 2–3) ✓, per-index serving (Task 4) ✓, UI switcher (Task 5) ✓, rate-limit round-robin (Task 3 step 3 + Task 6) ✓, error isolation (Task 6 step 3) ✓, untouched engine/metrics ✓ (no task modifies them). Unknowns → Task 0 ✓.
- **Placeholders:** the only intentional unknowns (real IDs / scrip-master column names) are resolved in Task 0 and threaded into Task 1; every other step has concrete code/commands.
- **Type consistency:** `build_payload(cfg)`, `ChainPoller(configs)`/`self.boxes`, `Handler(payloads=, chains=)`, `S.index`/`IDXQ()` names are used consistently across tasks.
- **Note:** git commit steps intentionally omitted (not a repo); each task ends at a live/functional verification instead.
