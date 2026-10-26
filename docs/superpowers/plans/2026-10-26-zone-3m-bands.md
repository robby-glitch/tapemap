# ZONE-3M Bands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the registration draft `docs/setup-review/ZONE-3M-PREREG.md` (NOTEPAD A110, reopened 26 Oct 15:08). Her words: "Yes, reopen my 15 Aug call: compute the zone machine's bands on 3-minute bars like my chart, as a new registration starting from a date you name. Plan it after close." The plan delivers:
- a twin of the zone machine (§1b's d2/u2 arms) whose VWAP and σ are computed on its own 3-min bars, published beside the 1-min-σ zone at interval 3 (`bands3`, `zone3_state`, `zone3_state_sell`, `zone3_on`);
- its own forward population in trigger_log (`rule: "zone3"`, `bands_on: "3m"`), scored on its own bands and never pooled;
- a `ZONE` chip in DECODE's setups. Its MATCH is one SETUP line on the stream and on Telegram, with its own entry and stop;
- on a 3-min chart, the Trade tab's d2→d3 / u2→u3 pockets, its zone entry markers, the machine strip and the browser-tab title, all on the 3-min machine and bands.

**One switch, one date** (amended 26 Oct: Claude decided as the trader, per Mary's standing rule):
- Everything zone3 she can see or receive waits for `band_rotation.ZONE3_FROM = "2026-10-28"`: the record, the chip, the SETUP line, Telegram, the Trade tab's pockets and markers, the machine strip and the tab title. Every zone3 alert she acts on is then also in the record.
- Before it the payload still computes `bands3` / `zone3_state`, as display data that nothing shows.

**Architecture:**
- **`band_rotation.py`** holds the one date (`ZONE3_FROM`) and gains `span` on `run_states` for the 09:25 anchor (default 1 = today's rule).
- **`contract_bars.py`** gains the pure helper pair: `bands_on` (bands on the rows' own H/L/C/V, through the existing `_Vwap` recurrence) and `with_bands` (a copy carrying them).
- **Consumers:** `live._at_interval` (the 3-min payload and its `zone3_on` switch), `trigger_log` (log + score), `decode` (the chip) and ui-v2 (pockets + markers) each call those pieces. The published `bars` and every existing machine are untouched.

**Tech Stack:** Python 3.13 stdlib + pytest (repo root `C:\Users\kaam\Desktop\operator mode\tapemap`, branch `feature/operator-objects`); React 19 + TypeScript in `ui-v2` (no test runner: the gates are `tsc --noEmit` and `vite build`). No new dependency.

## Global Constraints

- Display only. No order path, ever (CLAUDE.md rule 10).
- Never print a hit rate, win rate, expectancy or % confidence (rule 4). zone3 is published as counts only, and under 15 per side is inconclusive.
- Every level is tagged spot (`s`) or fut (`f`). The ZONE plan goes through `decode._plan` → `"E 22,468s|22,534f · stop 22,359s|22,425f"`, or `f` alone when the basis is unknown.
- A missing value is `None`/`"?"` with a reason, never 0. An unreadable bar's 3-min bands are `None`, and in the UI `NaN` (a hole), never the sampled value.
- Populations never pool: `5c`, `zone`, `zone3` and untagged legacy are four (rule 5). Every split below lists `zone3` on its own.
- Registered rules §1i–§1q are unchanged. ZONE-3M is draft §1r and unsigned: this plan anchors nothing and computes no sha.
- Unchanged (D1): `run_state`/`run_state_sell` (5c, d3/u3), `rotation`, the trap width, the engine's ctx/plays/§1d veto, `confluence.py` (FADE §1i, hash-checked), `validate.pick`, `visit.py`/`signals.py` ballot arms, `frame._setup`, and `out["bars"]` with its sampled bands.
- The 1-min zone (`rule: "zone"`) keeps computing and logging byte for byte (D2). Its arms are replayed on the d3 machine by `trigger_log._arm_trigger` (no `band=`): that is NOTEPAD A111, NOT fixed here, a separate fix on Mary's word.
- **One switch, one date.**
  - `ZONE3_FROM = "2026-10-28"` is defined ONCE, in `band_rotation.py`. band_rotation imports only `math`, and trigger_log, decode and live already import it, so there is no cycle.
  - Every reader writes `band_rotation.ZONE3_FROM` at call time, never `from band_rotation import ZONE3_FROM`: a monkeypatch (or a later change) then moves them all together. Task 7's test asserts no other module defines the name.
  - Before the date: nothing zone3 is logged. The `ZONE` chip is absent (not even "—"), so there is no SETUP line and no Telegram. The Trade tab, the machine strip and the title show the 1-min zone exactly as today, and the payload's `zone3_on` is false.
- **The day each reader compares** against the date:
  - trigger_log: today's ISO date (`time.strftime`), as it stamps rows;
  - decode: `g["day"]`, which `server._decode_all` sets from its own `day`, live or replay;
  - the payload: the session's own `date`, which `live.build_session` stamps.
  - A missing day is never late enough: no chip, `zone3_on: false`.
- **Her screen (decisions 2 and 3): everything follows the pockets.**
  - On a 3-min chart from `ZONE3_FROM` (`zone3_on` true), one switch (`Zone3.z3`) moves four readers onto the same machine and bands:
    - the Trade tab's pockets (`bands3`);
    - its entry markers (`zone3_state(_sell)`), Task 8;
    - the machine strip (App.tsx:986–993: its state, and its WAITING `d2 … · u2 …` line at :719–722 from `lastBar`), Task 8b;
    - the browser-tab title (App.tsx:858), Task 8b.
  - Before the date, and on 1/5/15-min charts, all four stay on today's `zone_state` and sampled bands.
- **Field name.** The row tag is `bands_on: "3m"`, not D2's `bands: "3m"`. `bands` is already the scorer's outcome dict:
  - `trigger_log._outcome` writes `"bands": _reached(win, sell)` at :936;
  - `score` merges it with `r.update(out)` at :1039;
  - `_line` reads it at :1082;
  - SignalsTab reads `r.bands.side` at SignalsTab.tsx:885.
  
  The draft already says `bands_on` (edited by the coordinator), so this plan does not touch the draft.
- Known measurement to carry, not reopen: `squeeze_score.load`'s docstring records the 3-min-bar order matching her Kite export worse (median ratio 0.948 vs 0.972, Jul 15–17), and research-findings §1c says one of those two measurements is wrong. The prereg's "calibration against her chart on two sessions is owed" stands.
- Tests write only under `tmp_path`. conftest redirects `trigger_log.PATH`. Never write under `data/`, and never read or print anything under `telegr/`.
- No restart in market hours (09:15–15:40 IST weekdays). Never start or stop the server (8765) or Vite (5173): she restarts. ui-v2 edits (Task 8) happen only after 15:40 IST or on a weekend, because her Vite hot-reloads them.
- Commit only on Mary's word, never push. Stage files by name. Every message ends `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- The Fact-Forcing Gate hook asks for facts before the first Bash/Edit on each file. The executor states:
  - the file's importers (each task's **Gate facts** line);
  - the API it affects;
  - the data schema (trigger_log rows / the payload keys);
  - Mary's words, quoted from the Goal.
- The working tree carries A108's uncommitted edits (`decode.py`, `messages.py`, `test_decode.py`, `test_messages.py`, `CLAUDE.md`, `docs/live/NOTEPAD.md`). Every line number below was read on that tree on 26 Oct.
- Baseline: `python -m pytest -q` = 2048 collected: 2046 pass, 1 skipped, 1 known flaky (`test_v2feed.py::test_serve_caches_full_and_answers_delta`, NOTEPAD A49). After this plan: **2070 collected** (+22, all in `test_zone3.py`).
- Line endings, measured by bytes on 26 Oct. Edit preserves them; check each file after every edit:

  | Endings | Files |
  |---|---|
  | LF | `band_rotation.py`, `contract_bars.py`, `live.py`, `ui-v2/src/data.ts`, `ui-v2/src/trade/zone3.ts`, `ui-v2/src/signals/SignalsTab.tsx`, new `test_zone3.py` |
  | CRLF | `trigger_log.py`, `server.py`, `decode.py`, `ui-v2/src/trade/TradeTab.tsx`, `ui-v2/src/App.tsx`, `CLAUDE.md`, `docs/live/NOTEPAD.md`, `context/research-findings.md` |

  `python -c "import sys;b=open(sys.argv[1],'rb').read();print(b.count(b'\r\n'),b.count(b'\n'))" <file>`: the two numbers are equal for a CRLF file, and the first is 0 for an LF file.
- **Pre-verified** on scratch copies of the repo (never the repo):
  - **Staged red/green:** for each task, its tests ran against Tasks 1..k−1 (red, with the failures stated below) and then with Task k (green). All 22 pass after Task 7.
  - **Full suite:** its failure list was identical before and after the patch.
  - **ui-v2:** `tsc` is clean and `vite build` succeeds, with Tasks 8 + 8b. The Task 8 red check was measured too.

---

### Task 1: The one date, and the 09:25 anchor learns a bar's span

**Files:**
- Create: `test_zone3.py` (LF)
- Modify `band_rotation.py` (LF):
  - `:227-228`: `ZONE3_FROM` after the anchor constants.
  - `:969`: the `run_states` signature.
  - `:1017-1021`: the end of the docstring.
  - `:1107-1108`: the anchor test.

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `band_rotation.ZONE3_FROM: str = "2026-10-28"`, the only definition.
  - `band_rotation.run_states(bars, days=None, stop_pts=None, side="BUY", band=None, span=1) -> list[dict]`. A bar may ARM when `minute + span > ANCHOR_MINUTE`, and `span=1` is exactly today's `minute >= ANCHOR_MINUTE`. `detect_index_run` is unchanged and passes no span.

**Gate facts:** importers of band_rotation are confluence.py, confluence_log.py, faded.py, live.py, server.py, squeeze_score.py, tools/xindex_replay.py and trigger_log.py. The API is additive (a constant, and a keyword with a default). No data schema changes.

- [ ] **Step 1: Write the failing test.** Create `test_zone3.py`:

```python
"""ZONE-3M (docs/setup-review/ZONE-3M-PREREG.md, draft §1r): the zone machine on bands computed on its own 3-minute bars,
beside the 1-minute-sigma zone. Pure: the 26 Oct NIFTY candles are a literal below; nothing here reads data/."""
import json
import os

import band_rotation
import contract_bars
from band_rotation import run_states

# ---- Task 1: the 09:25 anchor's span, and the one date ---------------------------------------------------------------

VWAP, SD = 100.0, 5.0
D2, D3, U2, U3 = VWAP - 2 * SD, VWAP - 3 * SD, VWAP + 2 * SD, VWAP + 3 * SD


def _bar(t, low, high, close):
    """One flat bar on fixed bands: VWAP 100, sigma 5 (d2 90, d3 85, u2 110, u3 115)."""
    return {"t": t, "o": close, "h": high, "l": low, "c": close, "vwap": VWAP, "u1": VWAP + SD, "d1": VWAP - SD,
            "u2": U2, "d2": D2, "u3": U3, "d3": D3}


def test_span_one_is_the_label_rule_byte_for_byte():
    """Every existing caller passes no span: the default must be the old `minute >= 09:25`, on every machine."""
    bars = [_bar("09:18", 84.0, 116.0, 100.0), _bar("09:21", 84.0, 116.0, 100.0), _bar("09:24", 84.0, 116.0, 100.0),
            _bar("09:25", 84.0, 116.0, 100.0), _bar("09:27", 84.0, 116.0, 100.0), _bar("09:30", 95.0, 117.0, 116.5),
            _bar("09:33", 83.0, 105.0, 84.0), _bar("09:36", 90.0, 99.0, 98.0)]
    for kw in ({}, {"band": "d2"}, {"side": "SELL"}, {"side": "SELL", "band": "u2"}):
        for stop in (None, band_rotation.OPERATOR_STOP_PTS):
            old = run_states(bars, stop_pts=stop, **kw)
            assert json.dumps(old) == json.dumps(run_states(bars, stop_pts=stop, span=1, **kw)), kw
    assert [s["entry"] for s in run_states(bars)] == band_rotation.detect_index_run(bars)


def test_span_three_lets_the_0924_bar_arm_and_span_one_does_not():
    """Rule 4: a bar is eligible when it holds a minute at or after 09:25 (label + 3 > 09:25)."""
    bars = [_bar("09:21", 95.0, 99.0, 97.0), _bar("09:24", 89.5, 93.0, 91.0), _bar("09:27", 92.0, 96.0, 95.5)]
    one = run_states(bars, stop_pts=20.0, band="d2")
    three = run_states(bars, stop_pts=20.0, band="d2", span=3)
    assert [s["state"] for s in one] == ["WAITING", "WAITING", "WAITING"]
    assert [s["state"] for s in three] == ["WAITING", "ARMED", "TRIGGERED"]
    assert three[1]["arm"] == {"rearm": False, "band": "d2", "extreme": 89.5, "first_i": 1, "first_t": "09:24"}
    assert three[2]["entry"]["stop"] == D2 - 20.0


def test_the_0921_bar_never_arms_even_at_span_three():
    """09:21 + 3 = 09:24: the bar holds no minute at or after 09:25."""
    assert run_states([_bar("09:21", 89.0, 93.0, 91.0)], band="d2", span=3)[0]["state"] == "WAITING"


def test_zone3_from_is_the_one_date_the_first_november_session():
    """One switch, one date (27 Oct is NIFTY's monthly expiry and the roll)."""
    assert band_rotation.ZONE3_FROM == "2026-10-28"
```

- [ ] **Step 2: Run it and watch it fail.**
Run: `python -m pytest -q test_zone3.py`
Expected: `4 failed`:
- three with `TypeError: run_states() got an unexpected keyword argument 'span'`;
- one with `AttributeError: module 'band_rotation' has no attribute 'ZONE3_FROM'`.

- [ ] **Step 3: Minimal implementation (4 edits in `band_rotation.py`, LF).**

Edit 1, lines 227–228. Replace:
```python
ANCHOR_HHMM = "09:25"
ANCHOR_MINUTE = 9 * 60 + 25
```
with:
```python
ANCHOR_HHMM = "09:25"
ANCHOR_MINUTE = 9 * 60 + 25

# ZONE-3M (docs/setup-review/ZONE-3M-PREREG.md, draft §1r): ONE switch, ONE
# date. From this session on -- Wed 28 Oct 2026, the first on the November
# future -- the zone machine on its own 3-minute bands is logged (trigger_log,
# rule "zone3"), alerted (decode's ZONE chip -> SETUP line, Telegram) and drawn
# (the Trade tab's pockets and markers, via the payload's `zone3_on`). Before
# it live.py still computes it, and nothing shows, sends or logs it. Every
# reader refers to THIS name, so the date can never differ between them.
ZONE3_FROM = "2026-10-28"
```

Edit 2, line 969. Replace:
```python
def run_states(bars, days=None, stop_pts=None, side="BUY", band=None):
```
with:
```python
def run_states(bars, days=None, stop_pts=None, side="BUY", band=None, span=1):
```

Edit 3, lines 1017–1022 (the docstring's last paragraph and the first code line). Replace:
```python
    An unreadable bar (`readable: False`) reports the state it is still IN, not
    WAITING. A missing read is not evidence the setup went away, and rendering
    it as WAITING would blink a live reference off the screen.
    """
    if not isinstance(bars, (list, tuple)) or not bars:
```
with:
```python
    An unreadable bar (`readable: False`) reports the state it is still IN, not
    WAITING. A missing read is not evidence the setup went away, and rendering
    it as WAITING would blink a live reference off the screen.

    `span` is how many minutes one bar holds, read by the 09:25 anchor only: a
    bar may ARM when it holds a minute at or after 09:25, `minute + span >
    ANCHOR_MINUTE`. The default 1 is the label rule every caller has always
    run (`minute >= ANCHOR_MINUTE`), unchanged. ZONE-3M
    (docs/setup-review/ZONE-3M-PREREG.md, rule 4) passes its bar width, 3, so
    the 09:24 bar -- closing 09:27, its bands computed then -- is eligible.
    """
    if not isinstance(bars, (list, tuple)) or not bars:
```

Edit 4, lines 1107–1108. Replace:
```python
                    if (tagged and minute is not None
                            and minute >= ANCHOR_MINUTE):
```
with:
```python
                    if (tagged and minute is not None
                            and minute + span > ANCHOR_MINUTE):
```

- [ ] **Step 4: Run and watch it pass.**
Run: `python -m pytest -q test_zone3.py`, which gives `4 passed`.
Then run the unchanged suites: `python -m pytest -q test_band_rotation_run.py test_zone_state.py test_sell_mirror.py test_frame_zone.py test_visit.py test_confluence.py test_trigger_log.py`. They all pass, with no edits to them.
Byte check: `band_rotation.py` prints `0 1290`.

- [ ] **Step 5: Commit, ONLY on Mary's word (house rule).** Stage these files by name: `git add band_rotation.py test_zone3.py` and `git commit -m "ZONE-3M: ZONE3_FROM (one date) + run_states span for the 09:25 anchor" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 2: Bands computed on the bars themselves (`contract_bars.bands_on` / `with_bands`)

**Files:**
- Modify: `contract_bars.py:204-207`. Insert after `vwap_bands`, at its last line `return _carry(out, bars)`.
- Modify: `test_zone3.py`. Append.

**Interfaces:**
- Consumes: `contract_bars._Vwap` (the `vwap_sigma` recurrence), `_num`, `BAND_KEYS`.
- Produces:
  - `contract_bars.bands_on(rows) -> list[dict | None]`: one `{"vwap","u1","d1","u2","d2","u3","d3"}` per row, computed on the rows' own h/l/c/v. A composite row is read off its `fut` leg, a flat bar off itself. An unreadable row gives `None` and adds nothing to the sums.
  - `contract_bars.with_bands(rows, bands) -> list`: a copy with the index leg's band keys replaced. A `None` slot sets every band key to `None`. `fut: None` rows are left as they are. The input is not mutated.
- Why not `vwap_sigma` directly (D3): it takes `(h, l, c, v)` tuples with no `None` guard (contract_bars.py:181–188). `bands_on` uses the same `_Vwap().push`, and the test pins it equal to `vwap_sigma` on readable rows.

**Gate facts:** importers of contract_bars are confluence_log.py, eod_capture.py, frame_v2.py, live.py, squeeze_score.py and trigger_log.py (decode.py too after Task 7). The API adds two functions and no existing function changes. No data schema changes.

- [ ] **Step 1: Write the failing test.** Append to `test_zone3.py`:

```python


# ---- Task 2: bands computed on the bars themselves -------------------------------------------------------------------

def _row(t, h, l, c, v):
    """A composite 3-min index row (resample_index's shape), sampled 1-min bands deliberately WRONG (999)."""
    return {"t": t, "fut": {"o": c, "h": h, "l": l, "c": c, "v": v, "oi": None,
                            **{k: 999.0 for k in contract_bars.BAND_KEYS}}, "ce": None, "pe": None}


def test_bands_on_is_the_session_recurrence_on_the_rows_own_hlcv():
    rows = [_row("09:15", 110.0, 100.0, 105.0, 300.0), _row("09:18", 108.0, 98.0, 99.0, 200.0),
            _row("09:21", 101.0, 95.0, 96.0, 100.0)]
    want = contract_bars.vwap_sigma([(r["fut"]["h"], r["fut"]["l"], r["fut"]["c"], r["fut"]["v"]) for r in rows])
    assert contract_bars.bands_on(rows) == want
    flat = [dict(r["fut"], t=r["t"]) for r in rows]                       # resample's flat shape, same numbers
    assert contract_bars.bands_on(flat) == want


def test_an_unreadable_row_is_none_and_adds_nothing():
    rows = [_row("09:15", 110.0, 100.0, 105.0, 300.0), {"t": "09:18", "fut": None, "ce": None, "pe": None},
            _row("09:21", 101.0, 95.0, 96.0, 100.0)]
    got = contract_bars.bands_on(rows)
    assert got[1] is None
    assert got[2] == contract_bars.vwap_sigma([(110.0, 100.0, 105.0, 300.0), (101.0, 95.0, 96.0, 100.0)])[1]
    assert contract_bars.bands_on([{"t": "09:15", "h": None, "l": 1.0, "c": 1.0, "v": 1.0}]) == [None]


def test_with_bands_replaces_only_the_band_keys_on_a_copy():
    rows = [_row("09:15", 110.0, 100.0, 105.0, 300.0), {"t": "09:18", "fut": None, "ce": None, "pe": None},
            _row("09:21", 101.0, 95.0, 96.0, 100.0)]
    before = json.dumps(rows)
    b = contract_bars.bands_on(rows)
    out = contract_bars.with_bands(rows, b)
    assert json.dumps(rows) == before                                       # not mutated
    assert {k: out[0]["fut"][k] for k in contract_bars.BAND_KEYS} == b[0]
    assert out[0]["fut"]["h"] == 110.0 and out[0]["ce"] is None
    assert out[1] == rows[1]                                                # the future did not print: left as it is
    flat = contract_bars.with_bands([{"t": "09:15", "h": None, "l": 1.0, "c": 1.0, "v": 1.0, "d2": 5.0}], [None])
    assert flat[0]["d2"] is None and flat[0]["l"] == 1.0                     # unreadable: None, never the old value
```

- [ ] **Step 2: Run it and watch it fail.**
Run: `python -m pytest -q test_zone3.py`
Expected: `3 failed, 4 passed`. The failures are `AttributeError: module 'contract_bars' has no attribute 'bands_on'`.

- [ ] **Step 3: Minimal implementation.** In `contract_bars.py` (LF), replace lines 204–207:
```python
        band = dict(b)
        band.update(st.push(b["h"], b["l"], b["c"], b["v"]))
        out.append(band)
    return _carry(out, bars)
```
with:
```python
        band = dict(b)
        band.update(st.push(b["h"], b["l"], b["c"], b["v"]))
        out.append(band)
    return _carry(out, bars)


def bands_on(rows):
    """ZONE-3M (docs/setup-review/ZONE-3M-PREREG.md, rule 2): one band dict per
    row, VWAP + sigma computed ON these rows' own H/L/C/V -- the 3-minute bars
    themselves, as her chart does -- through the same `_Vwap` recurrence.

    A composite index row (`resample_index`'s shape) is read off its `fut`
    leg, a flat bar (`resample`'s) off itself. A row with no readable H/L/C/V
    gets None and adds nothing to the session sums, like `vwap_bands`' None
    bar. The interval-invariant bands `resample` samples are not touched:
    nothing but ZONE-3M reads these.
    """
    st, out = _Vwap(), []
    for r in rows:
        b = r.get("fut") if isinstance(r, dict) and "fut" in r else r
        hlcv = ([_num(b.get(k)) for k in ("h", "l", "c", "v")]
                if isinstance(b, dict) else [None])
        out.append(None if None in hlcv else st.push(*hlcv))
    return out


def with_bands(rows, bands):
    """A COPY of `rows` whose index-leg band keys are `bands` (one per row,
    from `bands_on`). A None slot sets every band key to None -- an unreadable
    band, never a zero and never the sampled value. A composite row whose
    `fut` is None stays as it is. `rows` is not mutated."""
    out = []
    for r, bd in zip(rows, bands):
        if not isinstance(r, dict):
            out.append(r)
            continue
        new = bd if bd is not None else dict.fromkeys(BAND_KEYS)
        if "fut" not in r:
            out.append(dict(r, **new))
        elif isinstance(r["fut"], dict):
            out.append(dict(r, fut=dict(r["fut"], **new)))
        else:
            out.append(dict(r))
    return out
```

- [ ] **Step 4: Run and watch it pass.**
Run: `python -m pytest -q test_zone3.py`, which gives `7 passed`.
Then run the unchanged suites: `python -m pytest -q test_contract_bars.py test_index_interval.py`. They all pass. (The interval-invariance pins at test_contract_bars.py ~292–319 and test_index_interval.py families 2 and 4 stay as they are.)
Byte check: `contract_bars.py` prints `0 406`.

- [ ] **Step 5: Commit, ONLY on Mary's word (house rule).** Stage these files by name: `git add contract_bars.py test_zone3.py` and `git commit -m "ZONE-3M: contract_bars.bands_on / with_bands (bands on the bars' own HLCV)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 3: The 3-min payload publishes `bands3`, `zone3_state(_sell)` and its switch `zone3_on`, with the 26 Oct acceptance

**Files:**
- Modify `live.py` (LF):
  - `:1105-1108`: the end of `_at_interval`, after `out["zone_state_sell"]` and before `return out`.
  - `:1215-1216`: `build_session`, after `js = session_json(s)`, which stamps the session's ISO `date`.
- Modify: `test_zone3.py`. Append. The fixture is the 26 Oct NIFTY 1-min futures candles 09:15–09:32, read once from the scratchpad's `nifty_1m.json` (`days[-1].bars[i].fut`, `t`) and embedded as a literal.

**Interfaces:**
- Consumes:
  - `contract_bars.bands_on`, `contract_bars.with_bands` (Task 2);
  - `band_rotation.run_states(..., span=)` and `band_rotation.ZONE3_FROM` (Task 1);
  - `band_rotation.SCORED_INTERVAL` (3), `band_rotation.OPERATOR_STOP_PTS` (20.0).
- Produces:
  - `build_session`'s `day` dict gains `date: "YYYY-MM-DD"`, on every interval's `days[-1]` (`out = dict(day)`). It is additive, and no reader of a `date` key exists today.
  - At interval 3 ONLY:
    - `bands3: list[dict | None]`, 1:1 with `bars`;
    - `zone3_state` (BUY, `"d2"`, span 3) and `zone3_state_sell` (SELL, `"u2"`, span 3): `run_states` lists 1:1 with `bars`, computed whatever the date;
    - `zone3_on: bool` = `str(day.get("date") or "") >= band_rotation.ZONE3_FROM`. With no date it is False.
  - At 1/5/15 the four keys are absent.
  - `out["bars"]` are NOT modified. Every existing key is byte-identical.
- The tests that inspect `_at_interval`'s source (test_band_rotation_run.py:495–525) keep passing.

**Gate facts:** importers of live are server.py only. The API adds `date` to every `/api/data` day, and four keys to the interval-3 day. The data schema is that same payload (not a file). trigger_log reads it in Task 4, and ui-v2 in Task 8.

- [ ] **Step 1: Write the failing test.** Append to `test_zone3.py`:

```python


# ---- Task 3: the 3-min payload, its switch, and the 26 Oct acceptance ------------------------------------------------

# 26 Oct 2026 NIFTY near-month futures, the exchange's 1-min candles 09:15-09:32: (t, o, h, l, c, v). From
# /api/data?idx=NIFTY&interval=1 read that afternoon (scratchpad nifty_1m.json, days[-1].bars[i].fut). [M]
OCT26_NIFTY_FUT_1M = [
    ("09:15", 22560.0, 22570.0, 22530.0, 22535.0, 75075.0),
    ("09:16", 22531.0, 22575.0, 22525.6, 22575.0, 17420.0),
    ("09:17", 22576.0, 22579.3, 22520.0, 22520.0, 24180.0),
    ("09:18", 22520.0, 22525.6, 22505.6, 22505.6, 16445.0),
    ("09:19", 22510.0, 22519.0, 22500.0, 22500.0, 14430.0),
    ("09:20", 22495.0, 22501.8, 22480.8, 22495.1, 12675.0),
    ("09:21", 22496.4, 22498.0, 22470.0, 22476.3, 21840.0),
    ("09:22", 22474.6, 22475.0, 22462.0, 22470.0, 17485.0),
    ("09:23", 22473.2, 22490.1, 22465.0, 22465.0, 9555.0),
    ("09:24", 22465.0, 22474.8, 22454.0, 22470.0, 20150.0),
    ("09:25", 22474.3, 22475.0, 22447.0, 22450.0, 27365.0),
    ("09:26", 22447.8, 22480.0, 22440.0, 22475.0, 39520.0),
    ("09:27", 22473.1, 22475.4, 22459.7, 22470.4, 12220.0),
    ("09:28", 22472.0, 22497.2, 22462.1, 22488.0, 35555.0),
    ("09:29", 22494.0, 22538.8, 22488.0, 22534.1, 25805.0),
    ("09:30", 22532.1, 22549.0, 22520.0, 22524.1, 32955.0),
    ("09:31", 22530.0, 22540.0, 22512.0, 22524.5, 10465.0),
    ("09:32", 22525.0, 22535.0, 22497.3, 22501.0, 12870.0),
]


def _flat1():
    """The candles as flat 1-min bars with their 1-min session bands (vwap_bands: the engine's own recurrence)."""
    return contract_bars.vwap_bands([{"t": t, "o": o, "h": h, "l": l, "c": c, "v": v, "oi": None}
                                     for t, o, h, l, c, v in OCT26_NIFTY_FUT_1M])


def _ones():
    """engine.session_json's 1-min rows: the fut leg with its 1-min bands, no option legs."""
    return [{"t": b["t"], "fut": b, "ce": None, "pe": None} for b in _flat1()]


def _out(interval=3, **day):
    import live
    return live._at_interval(dict({"bars": _ones(), "events": []}, **day), interval)


def test_the_3m_payload_carries_zone3_beside_zone_and_leaves_its_bars_alone():
    out = _out()
    n = len(out["bars"])
    assert len(out["bands3"]) == len(out["zone3_state"]) == len(out["zone3_state_sell"]) == n
    assert out["bars"] == list(contract_bars.resample_index(_ones(), 3))     # sampled 1-min bands, untouched
    assert out["zone_state"] == run_states(out["bars"], stop_pts=band_rotation.OPERATOR_STOP_PTS, band="d2")
    for k in (1, 5, 15):                                                     # a 3-minute rule: published at 3 only
        other = _out(k)
        assert not {"bands3", "zone3_state", "zone3_state_sell", "zone3_on"} & set(other)


def test_zone3_on_is_the_sessions_date_against_the_one_switch():
    """The screens' one switch: computed always, shown only from band_rotation.ZONE3_FROM. A session with no date is
    not shown -- never assumed late enough. A live session carries its ISO date from build_session."""
    import inspect
    import live
    assert _out(date="2026-10-27")["zone3_on"] is False
    assert _out(date="2026-10-28")["zone3_on"] is True
    assert _out()["zone3_on"] is False
    assert any(s["entry"] for s in _out(date="2026-10-27")["zone3_state"])  # computed before its date all the same
    assert 'js["date"] = today' in inspect.getsource(live.build_session)


def test_acceptance_26_oct_nifty_zone3_arms_0924_and_enters_0927():
    """The registration's acceptance (in-sample, described only): on 3-min bands the 09:24 bar's low 22,440.0 reached
    d2 22,445.1 and armed; the 09:27 close 22,534.1 beat the arm bar's high 22,480.0; stop 22,425.1. The 1-min-sigma
    zone armed nothing there: its d2 at that bar was 22,434.1."""
    out = _out()
    t = [b["t"] for b in out["bars"]]
    i24, i27 = t.index("09:24"), t.index("09:27")
    f24, f27 = out["bars"][i24]["fut"], out["bars"][i27]["fut"]
    assert f24["l"] == 22440.0 and round(out["bands3"][i24]["d2"], 1) == 22445.1
    assert out["zone3_state"][i24]["arm"] == {"rearm": False, "band": "d2", "extreme": 22440.0,
                                             "first_i": i24, "first_t": "09:24"}
    e = out["zone3_state"][i27]["entry"]
    assert e["side"] == "BUY" and e["band"] == "d2" and e["ref_high"] == 22480.0 and f27["c"] == 22534.1
    assert round(e["level"], 1) == 22445.1 and round(e["stop"], 1) == 22425.1
    assert round(f24["d2"], 1) == 22434.1                                     # the sampled 1-min d2
    assert all(s["arm"] is None and s["entry"] is None for s in out["zone_state"])
    assert all(s["arm"] is None for s in out["zone3_state_sell"])
```

Verified numbers (a throwaway read-only run on 26 Oct, the scratchpad's `nifty_1m.json`, [M]). The fixture's `vwap_bands` reproduces the payload's 1-min fut bands to 0.01.

| 3-min bar | o | h | l | c | v | sampled d2 | 3-min VWAP | 3-min d2 | 3-min d3 |
|---|---|---|---|---|---|---|---|---|---|
| 09:21 | 22,496.4 | 22,498.0 | 22,462.0 | 22,465.0 | 48,880 | 22,462.93 | 22,516.45 | 22,468.62 | 22,444.71 |
| 09:24 | 22,465.0 | 22,480.0 | 22,440.0 | 22,475.0 | 87,035 | 22,434.07 | 22,501.33 | 22,445.05 | 22,416.92 |
| 09:27 | 22,473.1 | 22,538.8 | 22,459.7 | 22,534.1 | 73,580 | 22,436.42 | 22,503.23 | 22,452.40 | 22,426.99 |

On 3-min bands with span 3:
- **09:24:** ARMED (extreme 22,440.0 ≤ d2 22,445.05).
- **09:27:** TRIGGERED, E = close 22,534.1 > the arm bar's high 22,480.0. Stop 22,425.05 = 22,445.05 − 20.
- **09:21:** its low 22,462.0 is under its 3-min d2 22,468.62, but the anchor holds it (09:21 + 3 = 09:24).
- **The sampled 1-min zone:** WAITING on every bar.

- [ ] **Step 2: Run it and watch it fail.**
Run: `python -m pytest -q test_zone3.py`
Expected: `3 failed, 7 passed`, with `KeyError: 'bands3'` (two tests) and `KeyError: 'zone3_on'` (the switch test).

- [ ] **Step 3: Minimal implementation (2 edits in `live.py`, LF).**

Edit 1, lines 1105–1108. Replace:
```python
    out["zone_state_sell"] = band_rotation.run_states(
        out["bars"], stop_pts=band_rotation.OPERATOR_STOP_PTS, side="SELL",
        band="u2")
    return out
```
with:
```python
    out["zone_state_sell"] = band_rotation.run_states(
        out["bars"], stop_pts=band_rotation.OPERATOR_STOP_PTS, side="SELL",
        band="u2")
    # ZONE-3M (docs/setup-review/ZONE-3M-PREREG.md, draft §1r): the SAME zone
    # machine on bands computed ON these 3-minute bars, her chart's -- beside
    # the 1-minute-sigma zone above, never in place of it. A 3-minute rule, so
    # published at 3 only. `out["bars"]` keep their sampled bands: 5c, the
    # rotation, the trap, FADE and the zone above all read those, unchanged.
    # `zone3_on` is the one switch the screens read: the session's own date
    # (build_session's `date`) at or after band_rotation.ZONE3_FROM. No date
    # on the session -> False: not shown, never assumed late enough.
    if interval == band_rotation.SCORED_INTERVAL:
        out["bands3"] = contract_bars.bands_on(out["bars"])
        z3 = contract_bars.with_bands(out["bars"], out["bands3"])
        out["zone3_state"] = band_rotation.run_states(
            z3, stop_pts=band_rotation.OPERATOR_STOP_PTS, band="d2",
            span=interval)
        out["zone3_state_sell"] = band_rotation.run_states(
            z3, stop_pts=band_rotation.OPERATOR_STOP_PTS, side="SELL",
            band="u2", span=interval)
        out["zone3_on"] = (str(day.get("date") or "")
                           >= band_rotation.ZONE3_FROM)
    return out
```
(The zone3 entries' `trap` reads 3-min band widths, because they ride the copy. Every existing machine's trap is unchanged.)

Edit 2, lines 1215–1216 (in `build_session`). Replace:
```python
    s.run()
    js = session_json(s)
```
with:
```python
    s.run()
    js = session_json(s)
    js["date"] = today      # the session's ISO date: ZONE-3M's switch reads it
```
(`today` is `build_session`'s own `datetime.now(IST).strftime("%Y-%m-%d")` (live.py:1161), the date it fetched. `server._session_payload`'s close cut (server.py:1007, `dict(day, bars=...)`) keeps it.)

- [ ] **Step 4: Run and watch it pass.**
Run: `python -m pytest -q test_zone3.py`, which gives `10 passed`.
Then run the unchanged suites: `python -m pytest -q test_index_interval.py test_band_rotation_run.py test_zone_state.py test_contract_bars.py test_confluence.py test_frame_zone.py test_visit.py test_signals.py`. They all pass.
Byte check: `live.py` prints `0 1291`.

- [ ] **Step 5: Commit, ONLY on Mary's word (house rule).** Stage these files by name: `git add live.py test_zone3.py` and `git commit -m "ZONE-3M: 3-min payload publishes bands3 + zone3_state(_sell) + zone3_on; 26 Oct acceptance" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 4: trigger_log logs zone3 under its own rule, from the one date

**Files:**
- Modify `trigger_log.py` (CRLF):
  - `:367`: `_entries` before `log_new`.
  - `:491-507`: the zone3 arm block, and the zone/zone3 entry lists through the loop header.
  - `:540-543`: the `bands_on` tag on entry rows.
- No constant in trigger_log: it reads `band_rotation.ZONE3_FROM`.
- Modify: `test_zone3.py`. Append.

**Interfaces:**
- Consumes: the Task 3 payload keys `zone3_state` / `zone3_state_sell`; `band_rotation.ZONE3_FROM`; the existing `_arm_rows(..., keys=, rule=, gate_at=)`, `_dedupe`, `_key` (identity includes `rule`, so zone3 never collides with zone).
- Produces:
  - `trigger_log._entries(day_js, buy_key, sell_key) -> list[dict | None]`: the slot rule, BUY wins. It is behaviour-identical to the inline zone block it replaces.
  - Arm rows `{"kind": "arm", "rule": "zone3", "band": "d2"|"u2", ..., "bands_on": "3m"}` and entry rows `{"rule": "zone3", "px", "level", ..., "bands_on": "3m"}`, only when today ≥ `band_rotation.ZONE3_FROM`. 5c and zone rows are byte-identical (no `bands_on` key).

**Gate facts:** importers of trigger_log are confluence_log.py and server.py. The API is `log_new`, whose signature is unchanged. The data schema is `data/trigger_log.jsonl`: new rows with `rule: "zone3"` + `bands_on: "3m"`, and no existing row is touched. Mary's words: as in the Goal.

- [ ] **Step 1: Write the failing test.** Append to `test_zone3.py`:

```python


# ---- Task 4: trigger_log logs zone3 under its own rule, from the one date --------------------------------------------

def _payload():
    return {"interval": 3, "days": [_out()]}


def _fresh(tmp_path):
    import trigger_log
    trigger_log._seen = None
    return str(tmp_path / "log.jsonl")


def test_zone3_is_logged_under_its_own_rule_with_its_bands_tag(tmp_path, monkeypatch):
    import trigger_log
    path = _fresh(tmp_path)
    monkeypatch.setattr(band_rotation, "ZONE3_FROM", "2000-01-01")
    assert trigger_log.log_new("NIFTY", _payload(), None, ones=_ones(), path=path) == 2
    arm, entry = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert (arm["kind"], arm["rule"], arm["bands_on"], arm["t"], arm["side"], arm["band"]) == \
        ("arm", "zone3", "3m", "09:24", "BUY", "d2")
    assert arm["extreme"] == 22440.0 and arm["ref_high"] == 22480.0 and round(arm["level"], 1) == 22445.1
    assert arm["t_1m"] == "09:26" and arm["interval"] == 3
    assert "kind" not in entry and (entry["rule"], entry["bands_on"], entry["t"], entry["px"]) == \
        ("zone3", "3m", "09:27", 22534.1)
    assert round(entry["level"], 1) == 22445.1
    assert trigger_log.log_new("NIFTY", _payload(), None, ones=_ones(), path=path) == 0      # written once


def test_before_its_date_zone3_is_computed_but_never_logged(tmp_path, monkeypatch):
    import trigger_log
    path = _fresh(tmp_path)
    monkeypatch.setattr(band_rotation, "ZONE3_FROM", "2999-01-01")
    pl = _payload()
    assert any(s["entry"] for s in pl["days"][0]["zone3_state"])            # computed
    assert trigger_log.log_new("NIFTY", pl, None, ones=_ones(), path=path) == 0
    assert not os.path.exists(path)
```
Notes:
- On this tape the 1-min 5c and zone machines arm nothing, so exactly two rows are written, both zone3.
- `log_new` stamps `day` from today's clock, which is why the tests move `band_rotation.ZONE3_FROM`, the one name, rather than the clock.

- [ ] **Step 2: Run it and watch it fail.**
Run: `python -m pytest -q test_zone3.py`
Expected: `1 failed, 11 passed`.
- `test_zone3_is_logged_under_its_own_rule_with_its_bands_tag` fails with `assert 0 == 2`.
- The before-date test already passes, because nothing logs zone3 yet. It pins the date once the logging exists.

- [ ] **Step 3: Minimal implementation (3 edits, CRLF: check bytes after each).**

Edit 1, line 367. Replace:
```python
def log_new(index, payload, chain_state=None, ones=None, path=PATH):
```
with:
```python
def _entries(day_js, buy_key, sell_key):
    """One entry record (or None) per bar off a BUY / SELL state-list pair. A
    BUY wins a bar both sides land on -- the chart's tie-break -- so the log
    and the screen can never disagree about which record existed."""
    buy = [s.get("entry") if isinstance(s, dict) else None
           for s in day_js.get(buy_key) or []]
    sell = [s.get("entry") if isinstance(s, dict) else None
            for s in day_js.get(sell_key) or []]
    if len(sell) == len(buy):
        return [b if b is not None else s_ for b, s_ in zip(buy, sell)]
    return sell if sell and not buy else buy


def log_new(index, payload, chain_state=None, ones=None, path=PATH):
```

Edit 2, lines 491–507 (the end of the zone arms' try, the zone entry lists, and the loop header). Replace:
```python
                               rule="zone", gate_at=gate_at)))
                wrote = len(out)
        except Exception:
            pass

        # Zone ENTRIES ride the same loop as §5c's under their own tag —
        # one row shape, two populations. Same slot rule per list: buy wins.
        zrot = [s.get("entry") if isinstance(s, dict) else None
                for s in day_js.get("zone_state") or []]
        zsell = [s.get("entry") if isinstance(s, dict) else None
                 for s in day_js.get("zone_state_sell") or []]
        if len(zsell) == len(zrot):
            zrot = [b if b is not None else s_ for b, s_ in zip(zrot, zsell)]
        elif zsell and not zrot:
            zrot = zsell

        for rule_tag, rec_list in (("5c", rot), ("zone", zrot)):
```
with:
```python
                               rule="zone", gate_at=gate_at)))
                wrote = len(out)
        except Exception:
            pass

        # ZONE-3M (rule "zone3", `bands_on: "3m"`): the same row builder, its
        # own try and its own rule, only from band_rotation.ZONE3_FROM -- the
        # one date its chip, its alerts and its marks also wait for.
        z3on = day >= band_rotation.ZONE3_FROM
        try:
            interval = payload.get("interval")
            if interval == band_rotation.SCORED_INTERVAL and z3on:
                out.extend(json.dumps(dict(r, bands_on="3m")) for r in
                           _dedupe(_arm_rows(
                               index, day_js, bars, last, day,
                               oi_at,
                               ones, interval, time.time(),
                               keys=(("zone3_state", False),
                                     ("zone3_state_sell", True)),
                               rule="zone3", gate_at=gate_at)))
                wrote = len(out)
        except Exception:
            pass

        # Zone ENTRIES ride the same loop as §5c's under their own tag —
        # one row shape, two populations. Same slot rule per list: buy wins.
        zrot = _entries(day_js, "zone_state", "zone_state_sell")
        z3rot = (_entries(day_js, "zone3_state", "zone3_state_sell")
                 if z3on else [])

        for rule_tag, rec_list in (("5c", rot), ("zone", zrot),
                                   ("zone3", z3rot)):
```

Edit 3, lines 540–543. Replace:
```python
                   "closed_bar": True}
            if oi_why:                  # appended only when the OI is null,
                row["oi_why"] = oi_why  # so a normal row is byte-identical
            # §1d, the same stamp the arm rows carry, and with the same
```
with:
```python
                   "closed_bar": True}
            if rule_tag == "zone3":     # ZONE-3M: bands on its own 3-min bars
                row["bands_on"] = "3m"  # (absent on every other row)
            if oi_why:                  # appended only when the OI is null,
                row["oi_why"] = oi_why  # so a normal row is byte-identical
            # §1d, the same stamp the arm rows carry, and with the same
```

- [ ] **Step 4: Run and watch it pass.**
Run: `python -m pytest -q test_zone3.py`, which gives `12 passed`.
Then run the unchanged suites: `python -m pytest -q test_trigger_log.py test_zone_state.py test_confluence.py`. They all pass. (The interval refusal at test_trigger_log.py:537 and the live-band read at :726 are unchanged.)
Byte check: `trigger_log.py` prints `1207 1207`.

- [ ] **Step 5: Commit, ONLY on Mary's word (house rule).** Stage these files by name: `git add trigger_log.py test_zone3.py` and `git commit -m "ZONE-3M: trigger_log logs rule zone3 (bands_on 3m) from band_rotation.ZONE3_FROM" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 5: zone3 is scored on its own bands and shown apart

**Files:**
- Modify `trigger_log.py` (CRLF; line numbers on the pre-Task-4 file, so after Task 4 locate each by its quoted text):
  - `:809-812`: `_arm_trigger`'s `run_states` call.
  - `:993` and `:1003-1005`: score admits `zone3`.
  - `:1029-1031`: re-band zone3's cached bars.
  - `:1111-1113` and `:1146-1148`: show.
- Modify: `test_zone3.py`. Append.

**Interfaces:**
- Consumes:
  - `contract_bars.bands_on` / `with_bands` (Task 2) on `_session_bars`' flat 3-min cache bars (`squeeze_score.load`: `resample(vwap_bands(...), 3)`, sampled bands);
  - `run_states(..., band=, span=)` (Task 1);
  - `band_rotation.ZONE3_FROM`.
- Produces:
  - zone3 rows get the same outcome fields as zone rows (`mfe`, `mae`, `stop_px`, `bands`, and on arms `triggered` / `trigger_t`), measured on the 3-min bands;
  - `_arm_trigger` passes `band=row["band"], span=SCORED_INTERVAL` for zone3 only;
  - `show()` prints a ZONE-3M block and keeps zone3 out of the entry and arm tables;
  - `score`'s printed refusal still counts 5c only.

**Gate facts:** importers of trigger_log are confluence_log.py and server.py. The API is `score` / `show` (CLI, `eod_capture`), signatures unchanged. The data schema adds outcome fields on zone3 rows only. A111 (zone arms replayed on d3) is deliberately left alone, with a comment pointing at it.

- [ ] **Step 1: Write the failing test.** Append to `test_zone3.py`:

```python


# ---- Task 5: scored on its own bands, shown apart ---------------------------------------------------------------------

def _rows():
    lvl = run_states(contract_bars.with_bands(_out()["bars"], _out()["bands3"]), band="d2", span=3)[4]["entry"]["level"]
    base = {"at": 1.0, "day": "2026-10-26", "index": "NIFTY", "side": "BUY", "band": "d2", "rule": "zone3",
            "bands_on": "3m", "level": lvl, "closed_bar": True}
    return [dict(base, kind="arm", interval=3, t="09:24", ref_high=22480.0, extreme=22440.0, rearm=False,
                 first_t="09:24"),
            dict(base, t="09:27", px=22534.1)]


def _cached(monkeypatch):
    """The scorer's own cache shape: squeeze_score.load's `resample(vwap_bands(...), 3)` -- sampled 1-min bands."""
    import trigger_log
    flat3 = contract_bars.resample(_flat1(), 3)
    monkeypatch.setattr(trigger_log, "_load_sessions",
                        lambda idx: {"2026-10-26": {"bars": flat3}} if idx == "NIFTY" else {})
    return flat3


def test_a_zone3_row_is_scored_on_its_own_bands_and_its_arm_replayed_with_its_span(tmp_path, monkeypatch):
    import trigger_log
    path = _fresh(tmp_path)
    flat3 = _cached(monkeypatch)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in _rows()) + "\n")
    changed, skipped = trigger_log.score(path, quiet=True)
    arm, entry = [json.loads(x) for x in open(path, encoding="utf-8")]
    assert skipped == 0 and changed == 2
    assert arm["triggered"] is True and arm["trigger_t"] == "09:27" and arm["trigger_why"] is None
    assert round(arm["stop_px"], 1) == round(entry["stop_px"], 1) == 22425.1
    assert arm["bands_on"] == entry["bands_on"] == "3m"                       # the tag survives the scorer
    b3 = contract_bars.bands_on(flat3)[-1]                                   # the 09:30 bar, on 3-min bands
    assert entry["bands"]["u1"] == "09:30"
    assert entry["bands"]["sigma"] == round((22549.0 - b3["vwap"]) / (b3["vwap"] - b3["d1"]), 2)


def test_show_prints_zone3_apart_from_the_zone_and_arm_tables(tmp_path, capsys):
    import trigger_log
    path = _fresh(tmp_path)
    five = {"kind": "arm", "day": "2026-10-26", "index": "NIFTY", "t": "09:40", "side": "BUY", "band": "d3",
            "rule": "5c", "level": 22400.0, "extreme": 22399.0, "closed_bar": True}
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in _rows() + [five]) + "\n")
    trigger_log.show(path)
    out = capsys.readouterr().out
    assert "ZONE-3M (bands on 3-min bars, logged from 2026-10-28" in out and "1 entry, 1 arm row." in out
    assert "\n1 ARM rows" in out                                             # the 5c arm only
```
(On the cache's sampled bands the 09:24 bar never arms. A replay without `band=`/`span=` or without re-banding reads "NOT re-derived", so `triggered is True` pins all three.)

- [ ] **Step 2: Run it and watch it fail.**
Run: `python -m pytest -q test_zone3.py`
Expected: `2 failed, 12 passed`. The score test fails at `assert skipped == 0` (`2 == 0`: zone3 is quarantined as a foreign rule). The show test fails at `assert "ZONE-3M ..." in out`.

- [ ] **Step 3: Minimal implementation (6 replacements: Edits 1–4, 5a, 5b; CRLF).**

Edit 1, `_arm_trigger` (pre-Task-4 lines 809–812). Replace:
```python
    states = band_rotation.run_states(
        bars, stop_pts=band_rotation.OPERATOR_STOP_PTS,
        side="SELL" if sell else "BUY")
    i = next(
```
with:
```python
    # ZONE-3M replays its own machine: the band it armed on and its 3-minute
    # anchor span (its bars arrive re-banded, see `score`). Every other row
    # keeps this call exactly as it was; the zone rows' missing band= (they
    # replay on d3) is NOTEPAD A111, a separate fix on Mary's word.
    kw = ({"band": row.get("band"), "span": band_rotation.SCORED_INTERVAL}
          if row.get("rule") == "zone3" else {})
    states = band_rotation.run_states(
        bars, stop_pts=band_rotation.OPERATOR_STOP_PTS,
        side="SELL" if sell else "BUY", **kw)
    i = next(
```

Edit 2 (pre-Task-4 line 993). Replace:
```python
        if r.get("rule") not in ("5c", "zone"):
```
with:
```python
        if r.get("rule") not in ("5c", "zone", "zone3"):
```

Edit 3 (pre-Task-4 lines 1003–1005). Replace:
```python
            # it is a SEPARATE population: every count, table and refusal
            # downstream reads the rule tag and never pools it with 5c.
            skipped += 1
```
with:
```python
            # it is a SEPARATE population: every count, table and refusal
            # downstream reads the rule tag and never pools it with 5c.
            # "zone3" (ZONE-3M, from band_rotation.ZONE3_FROM) likewise.
            skipped += 1
```

Edit 4 (pre-Task-4 lines 1029–1031). Replace:
```python
            out = None
            if bars is not None:
                out, why = _outcome(r, bars)
```
with:
```python
            out = None
            if bars is not None:
                if r.get("rule") == "zone3":
                    # ZONE-3M is measured on ITS bands, re-derived on the
                    # cached 3-min bars by live.py's own helper: the stop,
                    # the other side's bands and the arm replay it logged on.
                    bars = contract_bars.with_bands(
                        bars, contract_bars.bands_on(bars))
                out, why = _outcome(r, bars)
```

Edit 5a, `show` (pre-Task-4 lines 1111–1113). Replace:
```python
    arms = [r for r in rows if r.get("kind") == "arm"]
    rows = [r for r in rows if r.get("kind") != "arm"]
    print(f"{'':<2}{'day':<12}
```
with:
```python
    # ZONE-3M is its own population: out of both tables, printed apart below.
    z3 = [r for r in rows if r.get("rule") == "zone3"]
    rows = [r for r in rows if r.get("rule") != "zone3"]
    arms = [r for r in rows if r.get("kind") == "arm"]
    rows = [r for r in rows if r.get("kind") != "arm"]
    print(f"{'':<2}{'day':<12}
```
(The old string ends mid-line, at `{'day':<12}`. Match it as written, and the rest of that `print` line stays.)

Edit 5b, `show` (pre-Task-4 lines 1146–1148). Replace:
```python
              f"operator's to state BEFORE reading these.")
    if not arms:
        return
```
with:
```python
              f"operator's to state BEFORE reading these.")
    if z3:
        ne = sum(1 for r in z3 if r.get("kind") != "arm")
        na = len(z3) - ne
        print(f"ZONE-3M (bands on 3-min bars, logged from "
              f"{band_rotation.ZONE3_FROM}; separate population, never pooled "
              f"with zone or 5c): {ne} entr{'y' if ne == 1 else 'ies'}, {na} "
              f"arm row{'' if na == 1 else 's'}. Same refusal applies.")
        for r in z3:
            print(f"{'':<2}{r.get('day', '')} {r.get('t', '')} "
                  f"{r.get('index', '')} {r.get('side', '')} "
                  f"{r.get('band', '')} {r.get('kind') or 'entry'}")
            if r.get("mfe") is not None:
                print(f"{'':<2}  {_line(r)}")
            elif r.get("unscored"):
                print(f"{'':<2}  not scored — {r['unscored']}")
    if not arms:
        return
```

- [ ] **Step 4: Run and watch it pass.**
Run: `python -m pytest -q test_zone3.py`, which gives `14 passed`.
Then run the unchanged suites: `python -m pytest -q test_trigger_log.py test_zone_state.py test_confluence.py`. They all pass.
Byte check: `trigger_log.py` prints `1238 1238`.

- [ ] **Step 5: Commit, ONLY on Mary's word (house rule).** Stage these files by name: `git add trigger_log.py test_zone3.py` and `git commit -m "ZONE-3M: score zone3 on its own bands + span; show it apart (A111 left for her word)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 6: `/api/signals` gives zone3 its own bucket

**Files:**
- Modify: `server.py:5373-5374` (the population lists) and `server.py:5425` (the response's `zone` line), both CRLF.
- Modify: `test_zone3.py`. Append.

**Interfaces:**
- Consumes: the trigger_log rows from Task 4.
- Produces in `GET /api/signals`:
  - `"zone3": {"n": <zone3 entries>, "arms": <zone3 arm rows>}`.
  - `arms` (every count in that block) now excludes zone3. It is unchanged for every row on disk today, since none is zone3.
  - `legacy` excludes zone3.
  - `rows` with `?rule=all` carries zone3 rows; the default `?rule=5c` hides them as before.

**Gate facts:** server.py is the entry point (no importers). The API adds one key to `/api/signals`, read by `ui-v2/src/signals/SignalsTab.tsx`, whose Payload type ignores unknown keys. The data schema is read-only on `data/trigger_log.jsonl`.

- [ ] **Step 1: Write the failing test.** Append to `test_zone3.py`:

```python


# ---- Task 6: /api/signals gives zone3 its own bucket -----------------------------------------------------------------

def test_api_signals_counts_zone3_apart_and_never_as_legacy():
    import server
    import trigger_log
    from test_senses_api import _Cap
    rows = _rows() + [
        {"kind": "arm", "day": "2026-10-26", "index": "NIFTY", "t": "09:40", "side": "BUY", "band": "d3", "rule": "5c"},
        {"day": "2026-10-26", "index": "NIFTY", "t": "09:45", "side": "BUY", "band": "d2", "rule": "zone", "px": 1.0},
        {"day": "2026-08-04", "index": "NIFTY", "t": "09:45", "side": "BUY", "band": "d3", "px": 1.0}]
    with open(trigger_log.PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(r) for r in rows) + "\n")
    cap = _Cap("/api/signals?rule=all")
    server.Handler.do_GET(cap)
    j = cap.sent
    assert j["zone3"] == {"n": 1, "arms": 1}
    assert j["zone"] == {"n": 1} and j["legacy"] == {"n": 1} and j["arms"]["n"] == 1
    assert j["matched"] == 5
```
(`trigger_log.PATH` is conftest's tmp path, and `ROOT / <absolute>` resolves to it.)

- [ ] **Step 2: Run it and watch it fail.**
Run: `python -m pytest -q test_zone3.py`
Expected: `1 failed, 14 passed`, with `KeyError: 'zone3'`.

- [ ] **Step 3: Minimal implementation (2 edits, CRLF).**

Edit 1, lines 5373–5374. Replace:
```python
            zone = [r for r in entries if r.get("rule") == "zone"]
            legacy = [r for r in entries if r.get("rule") not in ("5c", "zone")]
```
with:
```python
            zone = [r for r in entries if r.get("rule") == "zone"]
            # ZONE-3M (rule "zone3", logged from band_rotation.ZONE3_FROM): its own bucket, entries and arms both --
            # never legacy, never inside `arms` below.
            zone3 = [r for r in rows if r.get("rule") == "zone3"]
            arms = [r for r in arms if r.get("rule") != "zone3"]
            legacy = [r for r in entries if r.get("rule") not in ("5c", "zone", "zone3")]
```

Edit 2, line 5425. Replace:
```python
                "zone": {"n": len(zone)},     # counted apart, never summed into five_c or legacy
```
with:
```python
                "zone": {"n": len(zone)},     # counted apart, never summed into five_c or legacy
                "zone3": {"n": sum(1 for r in zone3 if r.get("kind") != "arm"),     # ZONE-3M, apart from both
                          "arms": sum(1 for r in zone3 if r.get("kind") == "arm")},
```

- [ ] **Step 4: Run and watch it pass.**
Run: `python -m pytest -q test_zone3.py`, which gives `15 passed`.
Then run the unchanged suites: `python -m pytest -q test_senses_api.py test_index_interval.py test_trigger_log.py`. They all pass.
Byte check: `server.py` prints `6766 6766`.

- [ ] **Step 5: Commit, ONLY on Mary's word (house rule).** Stage these files by name: `git add server.py test_zone3.py` and `git commit -m "ZONE-3M: /api/signals counts zone3 in its own bucket" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 7: The `ZONE` chip in DECODE, gated by the one date, its SETUP line and Telegram

**Files:**
- Modify `decode.py` (CRLF):
  - `:42-43`: imports.
  - `:587-591`: add `_zone3` before `setups` and append it to `setups`' list.
- Modify: `server.py:1914-1916` (CRLF): `_decode_all` hands DECODE its day (`g["day"] = day`) before `decode.decode`.
- Modify: `test_zone3.py`. Append.
- Read only, no edit:
  - `messages.py` (`build` at :138–147 already turns a chip leaving `—`/`ARMED` into a SETUP line carrying its `plan`; `OFF` at :28);
  - `telegram_out.py` (`wants` at :79–86 sends every SETUP);
  - `server.py:1798-1812` (`_decode_bars3` already hands DECODE the 3-min payload's closed bars, live, or `confluence_log.session(...)["bars"]` for a past day, as `fade_in["bars3"]`).

**Interfaces:**
- Consumes:
  - `g["day"]` (ISO, from `server._decode_all`'s own `day`, live or replay);
  - `fin["bars3"]`;
  - `contract_bars.bands_on` / `with_bands`;
  - `band_rotation.run_states(..., span=confluence.INTERVAL)`, `band_rotation.ZONE3_FROM`;
  - `decode._plan`, `confluence.close_of`, `confluence.flat`, `faded.BAR` (5).
- Produces:
  - `decode._zone3(g, fin) -> dict | None`:
    - `None` when `g["day"]` < `band_rotation.ZONE3_FROM` or absent (no chip at all, so no SETUP line and no Telegram), or when there are no bars or no side to show;
    - `{"name": "ZONE", "side": "BUY"|"SELL", "checks": {}, "state": "MATCH", "plan": "E …s|…f · stop …s|…f"}` when an entry's bar closed in `(now − 5 min, now]`;
    - `{..., "state": "ARMED"}` while the last closed bar's state is ARMED;
    - `{..., "state": "—"}` on the leg's fade side.
  - `decode.setups` order: FADE, RIDE, FADE-D, ZONE.
- Equivalence: the chip re-derives on the closed bars, where `zone3_state` was computed on the whole session. Both are causal, and a test pins them equal on the prefix.
- Not a registered-threshold copy: no float literal, and none of the guarded names is assigned. So test_decode.py:221's guard passes unchanged.
- The test_decode contract tests pass unchanged: their `g` carries no `day`, so there is no ZONE chip.

**Gate facts:** importers of decode are server.py and tools/decode_now.py (which goes through `server._decode_all`, so it gets the day too). The API adds one more chip in `/api/read`'s and the frame's `decode.setups`, from 28 Oct only. The data schema puts ZONE chips in `data/decode/decode_<day>.jsonl` rows, from 28 Oct, display only.

- [ ] **Step 1: Write the failing test.** Append to `test_zone3.py`:

```python


# ---- Task 7: the ZONE chip, its date, its SETUP line, Telegram -------------------------------------------------------

def _b3(at):
    """The zone machine's closed 3-min bars at `at` (minute of day), cut the way server._decode_bars3 cuts them."""
    import confluence
    return [b for b in contract_bars.resample_index(_ones(), 3) if confluence.close_of(b["t"]) <= at]


M = lambda hhmm: int(hhmm[:2]) * 60 + int(hhmm[3:])        # noqa: E731


def _g(at, leg=None, basis=None, day="2026-10-28"):
    """DECODE's facts as `_zone3` reads them. The candles are 26 Oct's; `day` is the date the server stamps
    (`g["day"]`), set to the first ZONE-3M session unless a test says otherwise."""
    return {"idx": "NIFTY", "bars5": [], "now": M(at) * 60, "leg": leg, "basis": basis, "day": day}


def test_the_zone_chip_matches_at_the_close_holding_the_zone3_entry():
    import decode
    assert decode._zone3(_g("09:30"), {"bars3": _b3(M("09:30"))}) == {
        "name": "ZONE", "side": "BUY", "checks": {}, "state": "MATCH", "plan": "E 22,534f · stop 22,425f"}
    s = decode._zone3(_g("09:30", basis=65.95), {"bars3": _b3(M("09:30"))})
    assert s["plan"] == "E 22,468s|22,534f · stop 22,359s|22,425f"


def test_the_zone_chip_is_armed_while_armed_and_dash_after():
    import decode
    assert decode._zone3(_g("09:27"), {"bars3": _b3(M("09:27"))}) == {
        "name": "ZONE", "side": "BUY", "checks": {}, "state": "ARMED"}
    assert decode._zone3(_g("09:35", leg={"d": 1}), {"bars3": _b3(M("09:35"))}) == {
        "name": "ZONE", "side": "SELL", "checks": {}, "state": "—"}
    assert decode._zone3(_g("09:35"), {"bars3": _b3(M("09:35"))}) is None    # no leg, no side to show
    assert decode._zone3(_g("09:30"), None) is None                          # no bars, no chip


def test_the_zone_chip_waits_for_its_date_so_nothing_alerts_before_the_record(monkeypatch):
    """One switch, one date: on 27 Oct no ZONE chip at all (not even "—"), so no SETUP line and no Telegram; on 28 Oct
    the same tape gives its MATCH. A day not stated is not shown. The server hands DECODE its day."""
    import inspect
    import decode
    import server
    fin = {"bars3": _b3(M("09:30"))}
    assert decode._zone3(_g("09:30", leg={"d": 1}, day="2026-10-27"), fin) is None
    assert decode._zone3(_g("09:30", day="2026-10-28"), fin)["state"] == "MATCH"
    assert decode._zone3(_g("09:30", leg={"d": 1}, day=None), fin) is None
    for fn in ("_fade", "_ride", "_fade_d"):
        monkeypatch.setattr(decode, fn, lambda *a, **k: None)
    assert decode.setups(_g("09:30", leg={"d": 1}, day="2026-10-27"), fin) == []
    assert 'g["day"] = day' in inspect.getsource(server._decode_all)


def test_zone3_from_lives_in_one_place():
    import decode
    import live
    import trigger_log
    assert not any(hasattr(m, "ZONE3_FROM") for m in (trigger_log, decode, live, contract_bars))


def test_the_chip_equals_the_payloads_zone3_state_cut_at_the_close():
    """The chip re-derives on the closed bars; the payload computed on the whole session. Causal: the same machine."""
    full = _out()
    k = len(_b3(M("09:27")))
    z = contract_bars.with_bands(_b3(M("09:27")), contract_bars.bands_on(_b3(M("09:27"))))
    assert run_states(z, stop_pts=band_rotation.OPERATOR_STOP_PTS, band="d2", span=3) == full["zone3_state"][:k]


def test_setups_lists_the_zone_chip_after_the_registered_three(monkeypatch):
    import decode
    for fn in ("_fade", "_ride", "_fade_d"):
        monkeypatch.setattr(decode, fn, lambda *a, **k: None)
    assert [s["name"] for s in decode.setups(_g("09:30"), {"bars3": _b3(M("09:30"))})] == ["ZONE"]


def test_a_zone_match_is_one_setup_line_with_its_own_entry_and_stop_and_reaches_telegram():
    import decode
    import messages
    import telegram_out
    row = {"idx": "NIFTY", "T": "09:30", "call": {"text": "x", "kind": "JAARI", "d": 0, "c": 4, "of": 7, "signs": []},
           "leg": {"d": 1, "ext": {"t": "09:30", "fut": 22549.0, "spot": None}}, "onesided": {"type": None},
           "setups": [decode._zone3(_g("09:30"), {"bars3": _b3(M("09:30"))})]}
    ms = [m for m in messages.build([], [row]) if m["kind"] == "SETUP"]
    assert [m["line"] for m in ms] == ["09:30  NIFTY  ZONE BUY · 4/7 saath · E 22,534f · stop 22,425f"]
    assert telegram_out.wants(ms[0])
    armed = dict(row, T="09:27", setups=[decode._zone3(_g("09:27"), {"bars3": _b3(M("09:27"))})])
    assert not [m for m in messages.build([], [armed]) if m["kind"] == "SETUP"]      # an arm is never sent
```
(The basis 65.95 is that afternoon's payload `basis`. With it, 22,534.1 − 65.95 = 22,468s and 22,425.05 − 65.95 = 22,359s.)

- [ ] **Step 2: Run it and watch it fail.**
Run: `python -m pytest -q test_zone3.py`
Expected: `5 failed, 17 passed`.
- Four fail with `AttributeError: module 'decode' has no attribute '_zone3'`: matches, armed, waits, and the SETUP line.
- `test_setups_lists_…` fails with `AssertionError: assert [] == ['ZONE']`.
- `test_zone3_from_lives_in_one_place` and `test_the_chip_equals_…` already pass.

- [ ] **Step 3: Minimal implementation (3 edits, CRLF).**

Edit 1, `decode.py` lines 42–43. Replace:
```python
import confluence
import effort
```
with:
```python
import band_rotation
import confluence
import contract_bars
import effort
```

Edit 2, `decode.py` lines 587–591. Replace:
```python
def setups(g, fade_in=None, ride_in=None):
    """FADE, RIDE, FADE-D in that order, each live at the current close or "—"; one that cannot be read is dropped
    (no side to show). Each part fails soft on its own."""
    out = []
    for fn in (lambda: _fade(g, fade_in), lambda: _ride(g, ride_in), lambda: _fade_d(g, ride_in)):
```
with:
```python
def _zone3(g, fin):
    """ZONE (ZONE-3M, docs/setup-review/ZONE-3M-PREREG.md, draft §1r; display only): the zone machine
    (band_rotation.run_states at d2 / u2, called) on bands computed on its own closed 3-min bars -- `fin["bars3"]`,
    re-banded by contract_bars.bands_on, the helper live.py publishes `zone3_state` with; both are causal, so this is
    the payload's machine cut at the close. MATCH: an entry whose bar closed since the last 5-min close, with its plan
    (E = the entry bar's close, stop = the machine's); ARMED: a live reference on the last closed bar; else "—" on
    the leg's fade side. ABSENT (None, not even "—") before band_rotation.ZONE3_FROM or on a day not stated
    (g["day"], set by server._decode_all), so no SETUP line and no Telegram before the record starts. No bars, no chip."""
    if str(g.get("day") or "") < band_rotation.ZONE3_FROM:
        return None
    b3 = (fin or {}).get("bars3")
    if not b3:
        return None
    z = contract_bars.with_bands(b3, contract_bars.bands_on(b3))
    armed = None
    for side, band in (("BUY", "d2"), ("SELL", "u2")):
        st = band_rotation.run_states(z, stop_pts=band_rotation.OPERATOR_STOP_PTS, side=side, band=band,
                                      span=confluence.INTERVAL)
        for s in st:
            e = s["entry"]
            c = confluence.close_of(e["t"]) if e else None
            if c is not None and g["now"] - faded.BAR * 60 < c * 60 <= g["now"]:
                return {"name": "ZONE", "side": side, "checks": {}, "state": "MATCH",
                        **_plan({"E": confluence.flat(z[e["i"]]).get("c"), "stop": e["stop"]}, g["basis"])}
        if armed is None and st[-1]["state"] == "ARMED":
            armed = side
    leg = g["leg"]
    side = armed or (("SELL" if leg["d"] > 0 else "BUY") if leg else None)
    return {"name": "ZONE", "side": side, "checks": {}, "state": "ARMED" if armed else "—"} if side else None


def setups(g, fade_in=None, ride_in=None):
    """FADE, RIDE, FADE-D, ZONE in that order, each live at the current close or "—"; one that cannot be read is
    dropped (no side to show). Each part fails soft on its own."""
    out = []
    for fn in (lambda: _fade(g, fade_in), lambda: _ride(g, ride_in), lambda: _fade_d(g, ride_in),
               lambda: _zone3(g, fade_in)):
```

Edit 3, `server.py` lines 1914–1916 (in `_decode_all`, after the EFFORT read). Replace:
```python
            g["effort"] = effort.blank(f"could not check — {type(e).__name__}: {e}")
        try:
            res[i] = decode.decode(g, peers, fin, rin)
```
with:
```python
            g["effort"] = effort.blank(f"could not check — {type(e).__name__}: {e}")
        g["day"] = day                           # ZONE-3M: decode._zone3 waits for band_rotation.ZONE3_FROM
        try:
            res[i] = decode.decode(g, peers, fin, rin)
```

- [ ] **Step 4: Run and watch it pass.**
Run: `python -m pytest -q test_zone3.py`, which gives `22 passed`.
Then run the unchanged suites: `python -m pytest -q test_decode.py test_messages.py test_messages_server.py test_messages_replay.py test_telegram_out.py test_confluence.py`. They all pass.
Byte check: `decode.py` prints `699 699`, and `server.py` prints `6767 6767`.

Read-only render checks:
- **The extension panel** (`C:\Users\kaam\Desktop\Go charting\orderflow-desk\src\shell\panel.js`, `decodeBlock` :164, the `su` chips at :179) renders any `x.name` escaped. `ckOrder({})` (:137) gives no checks, MATCH takes the `match` class, ARMED `armed`, and "—" `off`. It shows `ZONE BUY · ` with no rebuild.
- **ui-v2 ReadTab** (`ui-v2/src/read/ReadTab.tsx` :303–311) renders `u.name`, `Object.entries(u.checks)` and `u.state`, with `key={u.name}` unique. `DecodeSetup.name`'s union (:58) is compile-time only and is left as is (D6: read only).

- [ ] **Step 5: Commit, ONLY on Mary's word (house rule).** Stage these files by name: `git add decode.py server.py test_zone3.py` and `git commit -m "ZONE-3M: DECODE ZONE chip from band_rotation.ZONE3_FROM (MATCH -> SETUP line with E/stop, Telegram)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 8: ui-v2: on a 3-min chart from the date, the Trade tab's pockets AND entry markers ride ZONE-3M; Signals lists zone3 apart

Only after 15:40 IST or on a weekend: her Vite hot-reloads ui-v2 into her open 5173.

**What draws the zone today** (read on 26 Oct):
- **The hook.** `ui-v2/src/trade/zone3.ts` `useZone3` (:46–70) gives `Zone3 {bars, buy, sell}`:
  - on a 3m chart, from the chart's own payload (`tape.bars`, `tape.zoneState(Sell)`, :68);
  - otherwise, from one extra `/api/data?interval=3` read through `mapZone3` (:24–44, `day.zone_state(_sell)`).
- **The pockets.** `TradeTab.tsx:179-182` maps `zone3.bars` to `PocketBar`s, drawn by `LevelsOverlay.drawZone` (:136–161).
- **The entry markers.** `TradeTab.tsx:183-201` walks `zone3.buy` / `zone3.sell` entries into `ZoneEntry`s, drawn by `LevelsOverlay.drawEntries` (:176–). The Trade tab draws no arm marker.
- **Other readers of `zone3.buy/sell/bars`:** the machine strip (`App.tsx:986-993`) and the browser-tab title (`App.tsx:858`, `liveMachine`). Task 8b moves them onto the same `z3` switch.

**Files:**
- Modify `ui-v2/src/data.ts` (LF):
  - `:242-246`: `Bands3` after `TapeBar`.
  - `:477-480`: `TapeView` fields.
  - `:1404-1405`: the empty view.
  - `:1505-1506`: align the three arrays.
  - `:1522-1523`: return them and `zone3On`.
- Modify `ui-v2/src/trade/zone3.ts` (LF):
  - `:6-7`: imports.
  - `:16-18`: `Zone3.z3`.
  - `:20`: `HOLE`.
  - `:68`: the own-interval return gains `z3`.
- Modify `ui-v2/src/trade/TradeTab.tsx` (CRLF):
  - `:179-182`: pockets.
  - `:187`: the markers' machine.
  - `:201`: deps.
- Modify `ui-v2/src/signals/SignalsTab.tsx` (LF):
  - `:308-310`: row groups.
  - `:548`: the zone3 section, before the Arms section.
- Unchanged: `LevelsOverlay.ts` (`drawZone` skips non-finite values; `entryPlan` :90–101 accepts BUY d2 / SELL u2 at ≥ 09:25) and `mapZone3` (other chart intervals stay on the zone).

**Interfaces:**
- Consumes `days[-1].bands3`, `zone3_state`, `zone3_state_sell` and `zone3_on` (Task 3), and `/api/signals` rows with `rule: "zone3"` (Tasks 4, 6).
- Produces:
  - `export interface Bands3 { vwap, u1, d1, u2, d2, u3, d3: number }`;
  - `TapeView.bands3: (Bands3 | null)[] | null`;
  - `TapeView.zone3State: RunState[] | null`;
  - `TapeView.zone3StateSell: RunState[] | null`;
  - `TapeView.zone3On: boolean`;
  - `Zone3.z3?: { bars: TapeBar[]; buy: RunState[]; sell: RunState[] } | null`, non-null only on a 3m chart with `zone3_on` true and all three arrays aligned.
- Behaviour:
  - The Trade tab's pockets and entry markers read `z3` when it is there, both or neither.
  - Before 28 Oct, on 1/5/15m charts, and on an older backend, they draw exactly as today.

**Gate facts:** importers of data.ts are every tab. zone3.ts is imported by App.tsx and TradeTab.tsx, TradeTab.tsx by App, and SignalsTab.tsx by App. The API is read only. No data schema changes.

- [ ] **Step 1: The check that must fail first.** ui-v2 has no test runner, and none is added (house pattern, plan 2026-10-25 phase 2). The gate is `tsc`. After Edit A below alone, `cd "/c/Users/kaam/Desktop/operator mode/tapemap/ui-v2" && ./node_modules/.bin/tsc --noEmit -p .` fails with exactly three errors (measured on a scratch copy):
  - `src/data.ts(484,12): error TS2304: Cannot find name 'Bands3'.`
  - `src/data.ts(1406,7): error TS2739: Type '{ day: string; bars: never[]; … }' is missing the following properties from type 'TapeView': bands3, zone3State, zone3StateSell, zone3On`
  - `src/data.ts(1516,5): error TS2739: Type '{ day: any; bars: TapeBar[]; … }' is missing the following properties from type 'TapeView': bands3, zone3State, zone3StateSell, zone3On`

  Edits B–E clear all three.

- [ ] **Step 2: Edits in `ui-v2/src/data.ts`.**

Edit A, lines 477–480. Replace:
```ts
  zoneState: RunState[] | null
  zoneStateSell: RunState[] | null
  zoneStateWhy: string
}
```
with:
```ts
  zoneState: RunState[] | null
  zoneStateSell: RunState[] | null
  zoneStateWhy: string
  /** ZONE-3M (draft §1r), published on the 3-minute payload only: the bands computed on the 3-minute bars and the zone
   *  machine on them (`bands3`, `zone3_state`, `zone3_state_sell`), one slot per bar, null when absent or misaligned.
   *  `zone3On` is the one switch (`zone3_on`: the session's date at or after band_rotation.ZONE3_FROM); false when the
   *  payload does not say. Display only: the Trade tab's pockets and entry markers read them (./trade/zone3). */
  bands3: (Bands3 | null)[] | null
  zone3State: RunState[] | null
  zone3StateSell: RunState[] | null
  zone3On: boolean
}
```

Edit B, lines 242–246. Replace:
```ts
  ce?: BarLeg | null
  pe?: BarLeg | null
}

// ── SMC / ICT structure layer (Phase 3.5)
```
with:
```ts
  ce?: BarLeg | null
  pe?: BarLeg | null
}

/** ZONE-3M (draft §1r): one bar's VWAP and sigma bands computed ON the 3-minute bars themselves (`bands3`). */
export interface Bands3 { vwap: number; u1: number; d1: number; u2: number; d2: number; u3: number; d3: number }

// ── SMC / ICT structure layer (Phase 3.5)
```
(The old string's last line continues `──…` on the file. Match the prefix as written, and the rest of the line stays.)

Edit C, lines 1404–1405. Replace:
```ts
        zoneState: null, zoneStateSell: null, zoneStateWhy: '',
      }
```
with:
```ts
        zoneState: null, zoneStateSell: null, zoneStateWhy: '',
        bands3: null, zone3State: null, zone3StateSell: null, zone3On: false,
      }
```

Edit D, lines 1505–1506. Replace:
```ts
    const [zoneStateSell] =
      alignPerBar<RunState>(day.zone_state_sell, bars.length, skipped, 'sell-side zone state')
```
with:
```ts
    const [zoneStateSell] =
      alignPerBar<RunState>(day.zone_state_sell, bars.length, skipped, 'sell-side zone state')
    const [bands3] = alignPerBar<Bands3 | null>(day.bands3, bars.length, skipped, '3-minute bands')
    const [zone3State] = alignPerBar<RunState>(day.zone3_state, bars.length, skipped, 'ZONE-3M state')
    const [zone3StateSell] = alignPerBar<RunState>(day.zone3_state_sell, bars.length, skipped, 'ZONE-3M sell-side state')
```

Edit E, lines 1522–1523. Replace:
```ts
      zoneState, zoneStateSell, zoneStateWhy,
    }
```
with:
```ts
      zoneState, zoneStateSell, zoneStateWhy,
      bands3, zone3State, zone3StateSell, zone3On: day.zone3_on === true,
    }
```

- [ ] **Step 3: Edits in `ui-v2/src/trade/zone3.ts`.**

Edit F, lines 6–7. Replace:
```ts
import { useEffect, useState } from 'react'
import type { IndexKey, RunState, TapeBar, TapeView } from '../data'
```
with:
```ts
import { useEffect, useMemo, useState } from 'react'
import type { Bands3, IndexKey, RunState, TapeBar, TapeView } from '../data'
```

Edit G, lines 16–18. Replace:
```ts
  /** The session day of those bars. */
  day: string
}
```
with:
```ts
  /** The session day of those bars. */
  day: string
  /** ZONE-3M (draft §1r): on a 3-minute chart from band_rotation.ZONE3_FROM (the payload's `zone3_on`), the bars on
   *  the bands computed on the 3-minute bars and the zone machine on those same bands -- one switch, read by the Trade
   *  tab's pockets and entry markers and by the machine strip and tab title (App.tsx `zm`), so nothing on her screen
   *  disagrees with the pockets. Absent or null otherwise, and every reader keeps bars / buy / sell above. */
  z3?: { bars: TapeBar[]; buy: RunState[]; sell: RunState[] } | null
}
```

Edit H, line 20. Replace:
```ts
const POLL_MS = 5000  // the main tape poll's cadence: this is her live ARMED signal
```
with:
```ts
const POLL_MS = 5000  // the main tape poll's cadence: this is her live ARMED signal
/** A bar whose 3-minute bands could not be computed: a hole (NaN, drawZone skips it), never the sampled value. */
const HOLE: Bands3 = { vwap: NaN, u1: NaN, d1: NaN, u2: NaN, d2: NaN, u3: NaN, d3: NaN }
```

Edit I, line 68. Replace:
```ts
  if (own) return { bars: tape.bars, buy: tape.zoneState, sell: tape.zoneStateSell, why: tape.zoneStateWhy, day: tape.day }
```
with:
```ts
  const z3 = useMemo(() => {
    const { zone3On, bands3, zone3State, zone3StateSell } = tape
    if (!zone3On || !bands3 || !zone3State || !zone3StateSell) return null
    return { bars: tape.bars.map((b, i) => ({ ...b, ...(bands3[i] ?? HOLE) })), buy: zone3State, sell: zone3StateSell }
  }, [tape])
  if (own) return { bars: tape.bars, buy: tape.zoneState, sell: tape.zoneStateSell, why: tape.zoneStateWhy, day: tape.day, z3 }
```
Notes:
- The `useMemo` sits before the conditional return, so the hook order is fixed.
- `tape` is memoised per payload (`App.tsx:835`, `useMemo(() => tapeBars(activeIndex), …)`), so `z3` keeps its identity between renders.
- `bands3` is aligned to `bars` by `alignPerBar`, and a null slot is a hole.
- On a 3m chart, `tape` IS the 3-minute payload. On other charts `own` is false and `mapZone3` sets no `z3`.

- [ ] **Step 4: Edits in `ui-v2/src/trade/TradeTab.tsx` (CRLF: check bytes after).**

Edit J, lines 179–182. Replace:
```tsx
  const pockets = useMemo<PocketBar[] | null>(() => {
    if (!zone3.bars.length) return null
    return zone3.bars.map((b) => ({ t: base + hm(b.t) * 60_000, d2: b.d2, d3: b.d3, u2: b.u2, u3: b.u3 }))
  }, [zone3.bars, base])
```
with:
```tsx
  const pockets = useMemo<PocketBar[] | null>(() => {
    const pk = zone3.z3?.bars ?? zone3.bars          // ZONE-3M on a 3m chart from its date (./zone3), else the zone
    if (!pk.length) return null
    return pk.map((b) => ({ t: base + hm(b.t) * 60_000, d2: b.d2, d3: b.d3, u2: b.u2, u3: b.u3 }))
  }, [zone3.z3, zone3.bars, base])
```

Edit K, line 187. Replace:
```tsx
    for (const states of [zone3.buy, zone3.sell]) {
```
with:
```tsx
    // the markers ride the SAME switch as the pockets above: one machine, one set of bands
    for (const states of zone3.z3 ? [zone3.z3.buy, zone3.z3.sell] : [zone3.buy, zone3.sell]) {
```

Edit L, line 201. Replace:
```tsx
  }, [zone3.buy, zone3.sell, bars, publishedInterval, base, chipsOn])
```
with:
```tsx
  }, [zone3.z3, zone3.buy, zone3.sell, bars, publishedInterval, base, chipsOn])
```

- [ ] **Step 5: Edits in `ui-v2/src/signals/SignalsTab.tsx`.**

Edit M, lines 308–310. Replace:
```ts
  const zoneRows = rows.filter(r => r.kind !== 'arm' && r.rule === 'zone')
  const legacyRows = rows.filter(r => r.kind !== 'arm' && r.rule !== '5c' && r.rule !== 'zone')
  const armRows = rows.filter(r => r.kind === 'arm')
```
with:
```ts
  const zoneRows = rows.filter(r => r.kind !== 'arm' && r.rule === 'zone')
  // ZONE-3M (rule "zone3", bands on 3-minute bars, logged from 28 Oct): its own section, arms and entries both --
  // never Void, never in the arm section below.
  const zone3Rows = rows.filter(r => r.rule === 'zone3')
  const legacyRows = rows.filter(r => r.kind !== 'arm' && r.rule !== '5c' && r.rule !== 'zone' && r.rule !== 'zone3')
  const armRows = rows.filter(r => r.kind === 'arm' && r.rule !== 'zone3')
```

Edit N, line 548. Replace:
```tsx
          {/* Arms — their own section, so nothing here can read as an entry. */}
```
with:
```tsx
          {/* ZONE-3M — the zone on bands computed on 3-minute bars (your chart's), its own population. */}
          {zone3Rows.length > 0 && (
            <Section
              title={`Zone 3m — bands on 3-min bars · ${zone3Rows.length} row${zone3Rows.length === 1 ? '' : 's'} shown`}
              note={'The same zone machine on bands computed on the 3-minute bars, as on your chart, logged from 28 Oct. '
                + 'Arms and entries both, each marked; a separate population, never added to the zone rows above.'}
            >
              {zone3Rows.map((r, i) => (r.kind === 'arm'
                ? <ArmRow key={keyOf(r, i)} r={r}
                    open={!!open[keyOf(r, i)]}
                    onToggle={() => setOpen(o => ({ ...o, [keyOf(r, i)]: !o[keyOf(r, i)] }))} />
                : <Row key={keyOf(r, i)} r={r} legacy={false}
                    open={!!open[keyOf(r, i)]}
                    onToggle={() => setOpen(o => ({ ...o, [keyOf(r, i)]: !o[keyOf(r, i)] }))} />))}
            </Section>
          )}

          {/* Arms — their own section, so nothing here can read as an entry. */}
```

- [ ] **Step 6: Run the checks and watch them pass.**
Run: `cd "/c/Users/kaam/Desktop/operator mode/tapemap/ui-v2" && ./node_modules/.bin/tsc --noEmit -p . && ./node_modules/.bin/vite build`
Expected: `tsc` prints nothing, and `vite build` ends `✓ built in …` (its >500 kB chunk warning is pre-existing). `vite build` writes `ui-v2/dist`, which is gitignored and not served.
Byte checks:
- `data.ts` `0 1544`
- `zone3.ts` `0 102`
- `TradeTab.tsx` `413 413`
- `SignalsTab.tsx` `0 1066`

Render check, after her restart and after 15:40 on or after 28 Oct: on the Trade tab at 3m the pocket's d2 edge and the `Zone BUY d2` marker's triangle sit on the same 3-min band. On a 5m chart, or any day before 28 Oct, both are exactly today's.

- [ ] **Step 7: Commit, ONLY on Mary's word (house rule).** Stage these files by name: `git add ui-v2/src/data.ts ui-v2/src/trade/zone3.ts ui-v2/src/trade/TradeTab.tsx ui-v2/src/signals/SignalsTab.tsx` and `git commit -m "ZONE-3M: Trade-tab pockets + entry markers on zone3 (3m chart, from ZONE3_FROM); Signals lists zone3 apart" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 8b: The machine strip and the browser-tab title ride the same `z3` switch

Only after 15:40 IST or on a weekend (her Vite hot-reloads ui-v2). This task runs after Task 8, which supplies `Zone3.z3`.

**What it changes:**
- **The strip.** `MachineStrip` (App.tsx:693–) shows its state through `liveMachine(runState, runStateSell)` (:703). Its WAITING line `d2 … · u2 … · price …` (:719–722) and its TRADE MEIN `VWAP …` read `lastBar`.
- **The title.** The tab-title effect (:855–871) reads `liveMachine(zone3.buy, zone3.sell)`.
- **The switch.** One alias, `zm = zone3.z3 ?? zone3`, feeds the strip's `runState` / `runStateSell` / `lastBar` and the title's `liveMachine`. On a 3-min chart with `zone3_on` true, both read `zone3_state(_sell)` and the bar's 3-min bands. Otherwise they read today's zone, unchanged.
- **The reason line.** `runStateWhy` stays `zone3.why`: the aligned arrays share one skip guard, so `z3` is null exactly when they could not be lined up.

**Files:**
- Modify `ui-v2/src/App.tsx` (CRLF):
  - `:836`: add `zm` after `useZone3`.
  - `:858`: the title's `liveMachine`.
  - `:871`: the effect deps.
  - `:987-990`: the strip's props.

**Interfaces:**
- Consumes: `Zone3.z3?: { bars: TapeBar[]; buy: RunState[]; sell: RunState[] } | null` (Task 8).
- Produces: `const zm = zone3.z3 ?? zone3` in `App`. That is `{bars, buy, sell}` of ZONE-3M or of today's zone. `MachineStrip`'s props and `liveMachine`'s signature (`machine.ts:21`) are unchanged.

**Gate facts:** App.tsx is the root (imported by `main.tsx`). The API is read only. No data schema changes.

- [ ] **Step 1: The check that must fail first.** ui-v2 has no test runner, and none is added. The check is the wiring itself.
Run: `cd "/c/Users/kaam/Desktop/operator mode/tapemap/ui-v2" && grep -n "zm\." src/App.tsx`
Expected now: no output (exit 1). The strip and title still read `zone3.buy` / `zone3.sell` / `zone3.bars`.

- [ ] **Step 2: Edits in `ui-v2/src/App.tsx` (CRLF: check bytes after).**

Edit O, line 836. Replace:
```tsx
  const zone3 = useZone3(activeIndex, interval, tape)   // the strip, the title and Trade read THIS, never a 5m re-run
```
with:
```tsx
  const zone3 = useZone3(activeIndex, interval, tape)   // the strip, the title and Trade read THIS, never a 5m re-run
  // ZONE-3M (draft §1r): one switch, one date. On a 3m chart from band_rotation.ZONE3_FROM (zone3.z3) the strip and the
  // title read the SAME machine and bands as the Trade tab's pockets and markers; otherwise today's zone.
  const zm = zone3.z3 ?? zone3
```

Edit P, line 858. Replace:
```tsx
      const { st } = liveMachine(zone3.buy, zone3.sell)     // the zone: her setup (rule 3), always the 3-minute machine
```
with:
```tsx
      const { st } = liveMachine(zm.buy, zm.sell)           // the zone: her setup (rule 3), always the 3-minute machine
```

Edit Q, line 871. Replace:
```tsx
  }, [zone3, error, idxDead])
```
with:
```tsx
  }, [zm, error, idxDead])
```

Edit R, lines 987–990. Replace:
```tsx
        runState={zone3.buy}
        runStateWhy={zone3.why}
        runStateSell={zone3.sell}
        lastBar={zone3.bars.length ? zone3.bars[zone3.bars.length - 1] : null}
```
with:
```tsx
        runState={zm.buy}
        runStateWhy={zone3.why}
        runStateSell={zm.sell}
        lastBar={zm.bars.length ? zm.bars[zm.bars.length - 1] : null}
```

- [ ] **Step 3: Run the checks and watch them pass.**
Run: `cd "/c/Users/kaam/Desktop/operator mode/tapemap/ui-v2" && grep -n "zm\." src/App.tsx && ./node_modules/.bin/tsc --noEmit -p . && ./node_modules/.bin/vite build`
Expected:
- `grep` prints 4 lines (the title's `liveMachine(zm.buy, zm.sell)`, and `runState={zm.buy}`, `runStateSell={zm.sell}`, `lastBar={zm.bars…}`);
- `tsc` prints nothing;
- `vite build` ends `✓ built in …` (measured on a scratch copy with Tasks 8 + 8b).

Byte check: `App.tsx` prints `1124 1124`.

Render check, after her restart and after 15:40 on or after 28 Oct: on a 3m chart, the strip's WAITING `d2 …` equals the pocket's d2 edge, and the tab title's ARMED / TRIGGERED matches the Trade tab's marker. On a 5m chart, or before 28 Oct, all three are exactly today's.

- [ ] **Step 4: Commit, ONLY on Mary's word (house rule).** Stage this file by name: `git add ui-v2/src/App.tsx` and `git commit -m "ZONE-3M: machine strip + tab title ride the same z3 switch as the pockets" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`

---

### Task 9: Docs: test count, NOTEPAD statuses, the §1c pointer

Nothing is anchored here: she signs the draft first (its §Signature). No sha is computed and no §1r is added to research-findings. The draft itself (`docs/setup-review/ZONE-3M-PREREG.md`) is NOT edited by this plan: it already says `bands_on: "3m"`, and the coordinator owns its timing line.

**Files:**
- Modify: `CLAUDE.md:87` (CRLF), the test-count line.
- Modify: `docs/live/NOTEPAD.md:120` (CRLF), A110's status; then add the A111 row after it.
- Modify: `context/research-findings.md:360-364` (CRLF), §1c's "A fix, if it is ever wanted" paragraph. A dated pointer note is appended, and the old text is kept.

**Interfaces:** documentation only. Consumes the final suite count.

**Gate facts:**
- No importers.
- Affected readers: every session's CLAUDE.md read, and the NOTEPAD at session start (memory: live-notepad).
- research-findings gets a note, not a rewrite.

- [ ] **Step 1: Run the full suite (the "failing test" of a docs task is the stale count).**
Run: `python -m pytest -q`
Expected: `2070` collected: 2068 passed, 1 skipped, 1 known flaky (`test_v2feed.py::test_serve_caches_full_and_answers_delta`, NOTEPAD A49; passes alone). If the flaky one fails, run `python -m pytest -q test_v2feed.py::test_serve_caches_full_and_answers_delta` alone, and it passes. CLAUDE.md still says 2048, which is stale.

- [ ] **Step 2: `CLAUDE.md` line 87.** Replace:
```
python -m pytest -q            # 2048 collected: 2046 pass, 1 skipped, 1 known flaky (test_v2feed serve-cache, NOTEPAD A49), as of 2026-10-26 (A108 SETUP entry/stop)
```
with:
```
python -m pytest -q            # 2070 collected: 2068 pass, 1 skipped, 1 known flaky (test_v2feed serve-cache, NOTEPAD A49), as of 2026-10-26 (ZONE-3M bands, A110)
```

- [ ] **Step 3: `docs/live/NOTEPAD.md`, A110's status cell (line 120 ends with it).** Replace:
```
trigger_log rows before 28 Oct stay as recorded, on 1-min bands. Plan: after 15:40 today |
```
with:
```
trigger_log rows before 28 Oct stay as recorded, on 1-min bands. Plan: after 15:40 today. BUILT (uncommitted) per `docs/superpowers/plans/2026-10-26-zone-3m-bands.md`: ONE switch, ONE date, `band_rotation.ZONE3_FROM` = 2026-10-28. From it: trigger_log `rule: "zone3"`, `bands_on: "3m"` (scored on its own bands); the DECODE `ZONE` chip → one SETUP line + Telegram with its own E / stop; on a 3m chart (`zone3_on`), the Trade tab's pockets AND entry markers, the machine strip and the tab title, all on one switch. Before it nothing zone3 is logged, shown or sent; the 3-min payload still computes `bands3` + `zone3_state(_sell)`. `/api/signals` `zone3`. Acceptance on 26 Oct NIFTY reproduced (arm 09:24 low 22,440 ≤ d2 22,445.1, entry 09:27 22,534.1, stop 22,425.1; the 1-min-σ zone armed nothing). Draft §1r unsigned: live at her restart only after she signs and says commit |
```
Then insert this row on the line after A110's (a new line 121, before the A105 row):
```
| A111 | 26 Oct (ZONE-3M plan) | **The zone's ARM rows are replayed on the d3 machine when scored.** `trigger_log._arm_trigger` calls `band_rotation.run_states(bars, stop_pts=…, side=…)` with no `band=`, so a `rule: "zone"` arm (armed at d2) is looked for on the d3 machine: `triggered` reads "NOT re-derived" (or a d3 arm's fate) instead of the zone setup's own | `trigger_log.py` `_arm_trigger` (≈ line 809 before ZONE-3M) | Pass `band=row["band"]` for zone rows, as ZONE-3M's rows already do. It re-scores existing zone arm rows' `triggered`, so it waits for her word | OPEN |
```

- [ ] **Step 4: `context/research-findings.md` §1c, lines 360–364.** Replace:
```
**A fix, if it is ever wanted**, is one line: `live.py:522` reads
`resample(vwap_bands(one), interval)`; column B is `vwap_bands(resample(one,
interval))`. It **contradicts HANDOFF §6's** recorded "band pipeline order
✅ 0.972; reversed order 0.948" — one of those two measurements is wrong, and
that must be settled before the swap is trusted.
```
with:
```
**A fix, if it is ever wanted**, is one line: `live.py:522` reads
`resample(vwap_bands(one), interval)`; column B is `vwap_bands(resample(one,
interval))`. It **contradicts HANDOFF §6's** recorded "band pipeline order
✅ 0.972; reversed order 0.948" — one of those two measurements is wrong, and
that must be settled before the swap is trusted.

*(Pointer, 26 Oct: `live.py:522` has moved; that `resample(vwap_bands(...))` is
now the OPTION-leg path, live.py ~566. The index / zone path is
`live._at_interval`'s `contract_bars.resample_index` (~1045), which samples the
engine's 1-min bands. ZONE-3M (draft, `docs/setup-review/ZONE-3M-PREREG.md`)
does not swap it: it adds the 3-min bands beside it (`contract_bars.bands_on`).
The 0.972 / 0.948 question above is still open.)*
```

- [ ] **Step 5: Check the bytes.** `CLAUDE.md`, `docs/live/NOTEPAD.md` and `context/research-findings.md` each print two equal numbers.

- [ ] **Step 6: Commit, ONLY on Mary's word (house rule).** Stage these files by name: `git add CLAUDE.md docs/live/NOTEPAD.md context/research-findings.md docs/superpowers/plans/2026-10-26-zone-3m-bands.md` and `git commit -m "docs: ZONE-3M built (A110), A111 opened, §1c pointer" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. The draft (`docs/setup-review/ZONE-3M-PREREG.md`, untracked) is committed by whoever owns its text. When she signs, the §1r anchor (sha256 of the signed text in research-findings, effective 28 Oct 09:15) is a separate step on her word.

---

## Self-review

**Spec coverage** (ZONE-3M-PREREG.md, decisions D1–D10 and the two amendments → task):

| Clause | Where |
|---|---|
| Rule 1 BARS: 3-min on the 09:15 grid via `resample_index` | Task 3 (`out["bars"]` are those bars; `_buckets` anchors on the first bar, 09:15) |
| Rule 2 BANDS: VWAP/σ on the 3-min bars, hlc3×v, `_Vwap` / `vwap_sigma` | Task 2 (`bands_on`, pinned equal to `vwap_sigma`), Task 3 |
| Rule 2: d1/d2/d3, u1/u2/u3 at each bar's close | Task 2 (`_Vwap.push` per bar), Task 3 (`bands3`) |
| Rule 3 ARM: low ≤ d2 BUY / high ≥ u2 SELL | Task 3 (`band="d2"` / `"u2"`, the unchanged machine) |
| Rule 4 the 09:25 anchor, label + 3 > 09:25 | Task 1 (`span`), Task 3/5/7 pass 3 |
| Rule 5: entry, re-arm, 10-bar window, stop ∓ 20, re-fire lock unchanged | Task 1 (only the anchor line changes), Task 3 (`OPERATOR_STOP_PTS`) |
| New rows `rule: "zone3"`, arms + entries, `bands_on: "3m"` | Task 4 |
| From Wed 28 Oct; nothing logged before | Task 1 (`band_rotation.ZONE3_FROM`), Task 4 (both tests) |
| **Amendment 1: one switch, one date** for record, chip, SETUP, Telegram and Trade-tab marks; payload may compute | Task 1 (the one constant), Task 3 (`zone3_on`, `date`), Task 4 (log gate), Task 7 (chip absent before; 27 Oct vs 28 Oct test; `g["day"]`; one-place test), Task 8 (pockets + markers on `zone3On`) |
| **Amendment 2: Trade-tab markers follow the pockets** (3m chart, from the date; else today's) | Task 8 (Edits I–L; one `z3` for both) |
| **Amendment 3: the machine strip (incl. its WAITING d2/u2 line) and the tab title follow the same switch** | Task 8b (Edits O–R; `zm = zone3.z3 ?? zone3`) |
| The 1-min zone keeps running and logging; FADE §1i keeps reading it | Task 3 (`out["bars"]`, `zone_state` unchanged), Task 4 (zone rows byte-identical) |
| Unchanged on 1-min bands: 5c, rotation, trap, ctx/plays/§1d, Validate pick, Signals ballot | Global Constraints D1. Only `out["bars"]` feed them, and Task 3 asserts those are untouched |
| Scoring separate, never with zone rows; no hit rate | Task 5 (own re-banded bars, `show` block, refusal unchanged), Task 6 (own bucket) |
| Trade tab at 3-min: band lines and pockets are the 3-min bands | Task 8 (the Trade tab draws its bands only as the pockets' edges) |
| A zone3 entry = a `ZONE` chip + one SETUP line + Telegram with E / stop | Task 7 |
| An arm shows ARMED on the chip, never sent to Telegram | Task 7 (`messages.OFF`, test) |
| Every level spot/fut | Task 7 (`decode._plan` → `s\|f`) |
| Acceptance 26 Oct: arm 09:24 (22,440 ≤ 22,445.1), entry 09:27 22,534.1 > 22,480.0, stop 22,425.1; 1-min d2 22,434.1 | Task 3 (acceptance test), Task 4 (logged rows), Task 5 (scored), Task 7 (chip and line) |
| Known differences reported, not tuned | Global Constraints (0.948 / 0.972; calibration owed), Task 9 (§1c note) |
| Signature / §1r anchor | Task 9 (explicitly not done; her word) |
| D5: `_arm_trigger` must pass band + span for zone3; A111 noted, not fixed | Task 5 Edit 1, Task 9 (A111 row) |
| D5: `legacy` must not swallow zone3 (server + UI) | Task 6, Task 8 Edit M |
| D6: extension panel / ReadTab render an unknown chip | Task 7 Step 4 (read-only, lines cited) |
| D9: interval-invariance suites unchanged | Tasks 1–7 Step 4 (named suites, no edits to them) |
| D10: CLAUDE.md count, NOTEPAD statuses, §1c stale pointer | Task 9 |

**Placeholder scan:**
- No "TBD", "TODO", "handle edge cases" or "similar to Task N".
- Every code step carries its full code, and every run step its command and the measured expected result: the staged red/green counts per task, and the three `tsc` errors.

**Name consistency:**
- Python names: `ZONE3_FROM` (band_rotation only, always read as `band_rotation.ZONE3_FROM`), `span`, `bands_on`, `with_bands`, `bands3`, `zone3_state`, `zone3_state_sell`, `zone3_on`, `date`, `g["day"]`, `_entries`, `_zone3`, `rule "zone3"`, `bands_on: "3m"`, chip `name "ZONE"`.
- TS names: `Bands3`, `TapeView.bands3`, `zone3State`, `zone3StateSell`, `zone3On`, `Zone3.z3`, `HOLE`, `zm`, `zone3Rows`.
- Each name is spelled the same in every task, test and doc step.
- `bands` (the outcome dict) is never used as the tag.
- `ZONE` (chip name) and `zone3` (rule tag) are deliberately different.

**Line numbers:**
- All verified on the 26 Oct working tree, including the lines new in the amendments: `band_rotation.py:227-228`, `live.py:1215-1216`, `server.py:1914-1916` and `App.tsx:836/858/871/987-990`.
- Task 5's trigger_log numbers are stated on the pre-Task-4 file, so after Task 4 the executor locates each by its quoted text.
- The `tsc` errors' line/columns in Task 8 Step 1 are from a scratch copy with Edit A alone.
