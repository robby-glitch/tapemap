# tapemap/receipts.py
"""receipts.py -- the RECEIPTS of her trades (Mary's validate-tab-spec.md §7, her "go" 2026-10-04): what each closed trade
left behind, and the one KPI the spec names -- the average hold of WINNERS against the hold of LOSERS.

Per closed trade:
  * post-track: the held leg's premium at +10 / +20 / +30 min after the exit, the most favourable premium in those 30 min,
    and `left_on_table_pts` (that best minus her exit, her side's sign) -- premium points, never rupees;
  * re-entry tax: the same direction re-entered on the same index within 15 min, as a premium delta (same leg only);
  * adds dumped: an add (an entry fill after the first) whose size was sold within 2 bars (10 min of 5-min bars);
  * fear exit: tagged FEAR_EXIT on the record, or by the spec's clock -- green at exit before typical/3 -- with the
    flow lamp at exit recorded and not red; with no lamp recorded it is counted apart, "by the clock only";
  * amber exit: tagged AMBER_EXIT, or the engine's word at exit HOLD with the reversal count recorded < 2; with no
    reversal count recorded it is counted apart.
Scoreboard (today / this week / all time): avg hold winners vs losers, fear exits and their points left, re-entry tax,
amber exits, adds dumped. Counts and averages of her own rows, never a hit rate, never a percentage.

THE IMPORT: her Zerodha tradebook CSV (symbol, trade_date, trade_type, quantity, price, trade_id, order_id,
order_execution_time, expiry_date) -> flat-to-flat round trips per symbol and day, grouped and named exactly as
server._hold_trips names them (the 3 Oct import into day_2026-10-01.json), so a re-import matches what is there; every
fill is kept on the trip with its trade_id, so re-importing the same file adds nothing. Within a trip the lots are
matched FIFO for the hold of each lot.

Pure, stdlib only. The only I/O is `chain_series` (streams one chain day file) and `scan_days` / `import_write` (the
day_state files, with a backup written before any change). No clock: `now_s` / `today` are handed in.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import os
import re
import shutil
import statistics
import time
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

BAR_S = 300                    # her working timeframe, 5 minutes (spec §8)
ADD_DUMP_S = 2 * BAR_S         # an add sold within 2 bars was dumped (spec §6.3, §7.1)
REENTRY_S = 15 * 60            # the same direction re-entered within 15 min (spec §7)
POST_MIN = (10, 20, 30)        # post-track (spec §7, post_track_minutes: 30)
TYPICAL_SEED_S = 20 * 60       # typical_time_to_target seed (spec §5.1)
CC = "could not check"
SYM = re.compile(r"^(NIFTY|SENSEX|BANKNIFTY)\d{2}[0-9A-Z]{3}(\d+)(CE|PE)$")      # server._HOLD_SYM, the same contract names
T = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")


def sec(t: Optional[str]) -> Optional[int]:
    """'HH:MM[:SS]' -> seconds since midnight; None for anything else."""
    if not t or not T.match(str(t)):
        return None
    p = [int(x) for x in str(t).split(":")]
    return p[0] * 3600 + p[1] * 60 + (p[2] if len(p) > 2 else 0)


def own(tr: dict) -> int:
    """+1 she bought the leg (long), -1 she wrote it (short)."""
    return 1 if tr.get("role") == "long" else -1


def direction(tr: dict) -> int:
    """the underlying direction the trade wants: long CE / short PE = up (+1), long PE / short CE = down (-1)."""
    return own(tr) * (1 if tr.get("side") == "CE" else -1)


# ---- THE IMPORT --------------------------------------------------------------------------------------------------------
def read_csv(text: str) -> Tuple[List[dict], List[str]]:
    """Her tradebook -> fills, and the rows it could not read (with the reason)."""
    fills, skipped = [], []
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        m = SYM.match((r.get("symbol") or "").strip())
        t = (r.get("order_execution_time") or "")[11:19]
        bs = (r.get("trade_type") or "").strip().lower()
        try:
            q, p = int(float(r["quantity"])), float(r["price"])
        except (KeyError, TypeError, ValueError):
            q = p = None
        day = (r.get("trade_date") or "").strip()
        if not m or bs not in ("buy", "sell") or sec(t) is None or not q or p is None or not re.match(r"^\d{4}-\d\d-\d\d$", day):
            skipped.append(f"{r.get('symbol') or '?'} {day} {t}: not an index option fill this import reads")
            continue
        fid = (r.get("trade_id") or "").strip() or f"{(r.get('order_id') or '').strip()}:{t}:{q}:{p}"
        fills.append({"day": day, "t": t, "sym": r["symbol"].strip(), "idx": m.group(1), "k": float(m.group(2)),
                      "side": m.group(3), "bs": bs, "q": q, "p": p, "expiry": (r.get("expiry_date") or "").strip() or None,
                      "fid": fid})
    return fills, skipped


def trips(fills: List[dict]) -> List[dict]:
    """Flat-to-flat round trips per (day, symbol), as server._hold_trips groups them: long when the first fill buys,
    short when it sells; t0 the first fill, exit_t the fill that makes it flat (None: still open at the file's end).
    p0 / exit_px are size-weighted averages of the entry / exit fills."""
    out, book = [], {}
    for f in sorted(fills, key=lambda f: (f["day"], f["t"], f["fid"])):
        key = (f["day"], f["sym"])
        st = book.get(key)
        if st is None or st["pos"] == 0:
            st = book[key] = {"day": f["day"], "idx": f["idx"], "k": f["k"], "side": f["side"],
                              "role": "long" if f["bs"] == "buy" else "short", "t0": f["t"], "pos": 0,
                              "exit_t": None, "expiry": f["expiry"], "fills": []}
        sg = 1 if f["bs"] == "buy" else -1
        st["fills"].append([f["t"], f["bs"], f["q"], f["p"], f["fid"]])
        st["pos"] += sg * f["q"]
        if (st["role"] == "long") != (sg > 0):
            st["exit_t"] = f["t"]
        if st["pos"] == 0:
            out.append(st)
    out += [st for st in book.values() if st["pos"] != 0]
    for st in out:
        ins = [(q, p) for _, bs, q, p, _ in st["fills"] if (bs == "buy") == (st["role"] == "long")]
        outs = [(q, p) for _, bs, q, p, _ in st["fills"] if (bs == "buy") != (st["role"] == "long")]
        qi, qo = sum(q for q, _ in ins), sum(q for q, _ in outs)
        st["qty"] = qi
        st["p0"] = round(sum(q * p for q, p in ins) / qi, 2) if qi else None
        st["exit_px"] = round(sum(q * p for q, p in outs) / qo, 2) if qo and st["pos"] == 0 else None
        if st["pos"] != 0:
            st["exit_t"] = None
        st["id"] = f"{st['idx']}-{st['k']:g}{st['side']}-{st['role']}-{st['t0'].replace(':', '')}"
        st["src"] = "import"
        del st["pos"]
    return sorted(out, key=lambda s: (s["day"], s["t0"]))


def fifo_hold_s(tr: dict) -> Optional[float]:
    """The size-weighted hold of the trip's lots, entries matched to exits first-in first-out (seconds)."""
    fl = tr.get("fills") or []
    if not fl or not tr.get("exit_t"):
        return None
    q_in, tot, w = [], 0.0, 0
    for t, bs, q, p, _ in fl:
        if (bs == "buy") == (tr["role"] == "long"):
            q_in.append([sec(t), q])
            continue
        left = q
        while left and q_in:
            take = min(left, q_in[0][1])
            tot += take * (sec(t) - q_in[0][0])
            w += take
            left -= take
            q_in[0][1] -= take
            if not q_in[0][1]:
                q_in.pop(0)
    return tot / w if w else None


# ---- PER TRADE ---------------------------------------------------------------------------------------------------------
def hold_s(tr: dict) -> Optional[int]:
    """Her hold, entry to flat (seconds)."""
    a, b = sec(tr.get("t0")), sec(tr.get("exit_t"))
    return None if a is None or b is None else b - a


def exit_px(tr: dict, series: Optional[List[Tuple[int, float]]] = None) -> Tuple[Optional[float], str]:
    """Her exit premium: the tradebook's (import), else her roles' size-weighted exit_px, else the chain's last premium
    at or before the exit -- not her fill, and the source says so."""
    if tr.get("exit_px") is not None:
        return float(tr["exit_px"]), "her fill"
    rs = [r for r in tr.get("roles") or [] if r.get("exit_px") is not None]
    if rs:
        lots = sum(int(r.get("lots") or 1) for r in rs)
        return round(sum(float(r["exit_px"]) * int(r.get("lots") or 1) for r in rs) / lots, 2), "her roles' exits"
    s = sec(tr.get("exit_t"))
    if series and s is not None:
        before = [p for t, p in series if t <= s]
        if before:
            return before[-1], "the chain at her exit (not her fill)"
    return None, f"{CC} — no exit premium (no fill, no role exit, no chain row before {tr.get('exit_t')})"


def post_track(tr: dict, px: Optional[float], series: Optional[List[Tuple[int, float]]]) -> dict:
    """+10 / +20 / +30 min premiums after the exit, the most favourable in 30 min and the points left on the table."""
    s = sec(tr.get("exit_t"))
    if s is None:
        return {"why": "not shown — the trade is still open"}
    if not series:
        return {"why": f"{CC} — no chain premium for {tr.get('k', 0):g} {tr.get('side')} on {tr.get('day')}"}
    at = {}
    for m in POST_MIN:
        upto = [p for t, p in series if s < t <= s + m * 60]
        at[f"p{m}"] = upto[-1] if upto else None
    win = [(t, p) for t, p in series if s < t <= s + POST_MIN[-1] * 60]
    if not win:
        return {**at, "why": f"{CC} — no chain row in the 30 min after {tr['exit_t']}"}
    o = own(tr)
    bt, bp = max(win, key=lambda x: o * x[1])
    left = None if px is None else round(max(0.0, o * (bp - px)), 2)
    return {**at, "max_fav": bp, "max_fav_t": _hms(bt), "left_on_table_pts": left,
            "complete": win[-1][0] >= s + POST_MIN[-1] * 60 - 120, "why": None if px is not None else f"{CC} — no exit premium"}


def adds_dumped(tr: dict) -> List[dict]:
    """Adds (entry fills after the first) whose size was sold within 2 bars."""
    fl = tr.get("fills") or []
    ins = [f for f in fl if (f[1] == "buy") == (tr["role"] == "long")]
    outs = [f for f in fl if (f[1] == "buy") != (tr["role"] == "long")]
    t_first = sec(ins[0][0]) if ins else None
    out = []
    for t, _, q, p, _ in ins:
        ta = sec(t)
        if ta is None or ta <= t_first:
            continue
        sold, when = 0, None
        for to, _, qo, _, _ in outs:
            s = sec(to)
            if s is not None and ta < s <= ta + ADD_DUMP_S:
                sold += qo
                if sold >= q and when is None:
                    when = to
        if when:
            out.append({"t": t, "q": q, "p": p, "dumped_t": when, "after_s": sec(when) - ta})
    # her roles (marked live): an ADD role exited within 2 bars of its entry
    for r in tr.get("roles") or []:
        a, b = sec(r.get("entry_t")), sec(r.get("exit_t"))
        if r.get("role") == "ADD" and a is not None and b is not None and 0 <= b - a <= ADD_DUMP_S:
            out.append({"t": r["entry_t"], "q": r.get("lots"), "p": r.get("entry_px"), "dumped_t": r["exit_t"], "after_s": b - a})
    return out


def reentries(trs: List[dict]) -> List[dict]:
    """The same direction re-entered on the same index within 15 min of a full exit: the tax is her side's premium
    delta, re-entry minus exit, on the same leg; another leg is counted with its delta not compared."""
    out = []
    done = sorted((t for t in trs if t.get("exit_t")), key=lambda t: (t["day"], sec(t["exit_t"])))
    for a in done:
        ea = sec(a["exit_t"])
        nxt = [b for b in trs if b["day"] == a["day"] and b["idx"] == a["idx"] and b["id"] != a["id"]
               and direction(b) == direction(a) and sec(b.get("t0")) is not None and 0 <= sec(b["t0"]) - ea <= REENTRY_S]
        if not nxt:
            continue
        b = min(nxt, key=lambda b: sec(b["t0"]))
        same = b["k"] == a["k"] and b["side"] == a["side"] and b["role"] == a["role"]
        pa = a.get("_exit_px")
        tax = round(own(a) * (b["p0"] - pa), 2) if same and pa is not None and b.get("p0") is not None else None
        out.append({"from": a["id"], "to": b["id"], "day": a["day"], "gap_s": sec(b["t0"]) - ea, "same_leg": same,
                    "exit_px": pa, "reentry_px": b.get("p0"), "tax": tax,
                    "why": None if tax is not None else ("not shown — another leg, premiums not comparable" if not same
                                                         else f"{CC} — no exit premium")})
    return out


def word_at_exit(words: Optional[List[dict]], exit_t: Optional[str]) -> Optional[str]:
    """The engine's headline word at her exit: the last word logged while she was in."""
    ins = [w for w in words or [] if not w.get("after_exit") and (exit_t is None or str(w.get("t")) <= str(exit_t))]
    if not ins:
        return None
    h = str(ins[-1].get("headline") or "").upper()
    return next((w for w in ("PAST GIVE-UP", "FOLD", "CAN'T CHECK", "HOLD") if h.startswith(w)), None)


def receipt(tr: dict, series: Optional[List[Tuple[int, float]]], words: Optional[List[dict]], typical_s: float) -> dict:
    """One closed trade's receipt."""
    px, px_src = exit_px(tr, series)
    tr["_exit_px"] = px
    h = hold_s(tr)
    pts = None if px is None or tr.get("p0") is None else round(own(tr) * (px - float(tr["p0"])), 2)
    tags = set(tr.get("tags") or []) | {r.get("exit_reason") for r in tr.get("roles") or [] if r.get("exit_reason")}
    lamps = tr.get("lamps_at_exit") if isinstance(tr.get("lamps_at_exit"), dict) else None
    flow = (lamps or {}).get("flow")
    flow = flow.get("state") if isinstance(flow, dict) else flow
    w = word_at_exit(words, tr.get("exit_t"))
    rev = tr.get("reversal_at_exit")
    clock_fear = pts is not None and pts > 0 and h is not None and h < typical_s / 3
    fear = "FEAR_EXIT" in tags or (clock_fear and flow is not None and str(flow).upper() not in ("RED", "R"))
    amber = "AMBER_EXIT" in tags or (w == "HOLD" and isinstance(rev, (int, float)) and rev < 2)
    pt = post_track(tr, px, series)
    return {"id": tr["id"], "day": tr["day"], "hold_s": h, "fifo_hold_s": fifo_hold_s(tr), "pts": pts,
            "exit_px": px, "exit_px_src": px_src,
            "result": None if pts is None else "win" if pts > 0 else "loss" if pts < 0 else "flat",
            "post": pt, "left_on_table_pts": pt.get("left_on_table_pts"),
            "adds_dumped": adds_dumped(tr), "engine_at_exit": w, "reversal_at_exit": rev, "lamps_at_exit": lamps,
            "tags": sorted(t for t in tags if t), "fear": fear, "fear_clock_only": clock_fear and not fear and flow is None,
            "amber": amber, "amber_unverified": not amber and w == "HOLD" and rev is None, "src": tr.get("src") or "marked"}


# ---- THE KPI AND THE SCOREBOARD ----------------------------------------------------------------------------------------
def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


def scoreboard(rs: List[dict], re_: List[dict]) -> dict:
    """The spec's §7.1 board over a set of receipts: counts and averages of her rows, never a rate."""
    win = [r for r in rs if r["result"] == "win"]
    loss = [r for r in rs if r["result"] == "loss"]
    fear = [r for r in rs if r["fear"]]
    clock = [r for r in rs if r["fear_clock_only"]]
    taxed = [x for x in re_ if x["tax"] is not None]
    return {"n": len(rs), "n_win": len(win), "n_loss": len(loss), "n_flat": len([r for r in rs if r["result"] == "flat"]),
            "n_unpriced": len([r for r in rs if r["result"] is None]),
            "avg_hold_win_s": _avg([r["hold_s"] for r in win]), "avg_hold_loss_s": _avg([r["hold_s"] for r in loss]),
            "median_hold_win_s": statistics.median([r["hold_s"] for r in win]) if win else None,
            "fear_exits": len(fear), "fear_left_pts": round(sum(r["left_on_table_pts"] or 0 for r in fear), 2),
            "fear_clock_only": len(clock), "fear_clock_only_left_pts": round(sum(r["left_on_table_pts"] or 0 for r in clock), 2),
            "reentries": len(re_), "reentry_tax_events": len([x for x in taxed if x["tax"] > 0]),
            "reentry_tax_pts": round(sum(x["tax"] for x in taxed if x["tax"] > 0), 2),
            "amber_exits": len([r for r in rs if r["amber"]]), "amber_unverified": len([r for r in rs if r["amber_unverified"]]),
            "adds_dumped": sum(len(r["adds_dumped"]) for r in rs),
            "left_on_table_pts": round(sum(r["left_on_table_pts"] or 0 for r in rs), 2)}


def typical(rs: List[dict], trs: Dict[str, dict]) -> Tuple[float, str]:
    """typical_time_to_target (spec §5.1): the median time from entry to the leg's best premium in [entry, exit + 30 min]
    over her trades whose best was favourable -- what the move took, not what she held. Under 5 such trades: the seed."""
    xs = []
    for r in rs:
        tr, pt = trs.get(r["id"]) or {}, r.get("post") or {}
        a, b = sec(tr.get("t0")), sec(pt.get("max_fav_t"))
        if a is not None and b is not None and r.get("left_on_table_pts") and r["left_on_table_pts"] > 0:
            xs.append(b - a)
    if len(xs) < 5:
        return float(TYPICAL_SEED_S), f"seed 20 min (only {len(xs)} trades with a favourable best; 5 needed)"
    return float(statistics.median(xs)), f"median of {len(xs)} trades: entry to the leg's best within 30 min of exit"


def week_of(day: str) -> str:
    d = date.fromisoformat(day)
    return (d - timedelta(days=d.weekday())).isoformat()


# ---- I/O: chain premiums, the day files ----------------------------------------------------------------------------------
def _hms(s: int) -> str:
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def chain_series(path: str, legs: List[Tuple[float, str]]) -> Dict[Tuple[float, str], List[Tuple[int, float]]]:
    """Stream one chain day file (jsonl or .gz) -> {(k, 'CE'|'PE'): [(sec, ltp)]} for the legs asked. A torn line is
    skipped; a missing file is no series."""
    p = path if os.path.exists(path) else path + ".gz" if os.path.exists(path + ".gz") else None
    out: Dict[Tuple[float, str], List[Tuple[int, float]]] = {lg: [] for lg in legs}
    if p is None or not legs:
        return out
    want = {float(k) for k, _ in legs}
    op = gzip.open if p.endswith(".gz") else open
    with op(p, "rt", encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            s = sec(r.get("ts"))
            if s is None:
                continue
            for x in r.get("strikes") or []:
                k = x.get("k")
                if k is None or float(k) not in want:
                    continue
                for ty in ("CE", "PE"):
                    if (float(k), ty) in out:
                        v = (x.get(ty.lower()) or {}).get("ltp")
                        if isinstance(v, (int, float)) and v > 0:
                            out[(float(k), ty)].append((s, float(v)))
    return out


def scan_days(dir_: str) -> List[str]:
    """Every day with a day_state file, oldest first."""
    try:
        names = os.listdir(dir_)
    except OSError:
        return []
    return sorted(m.group(1) for m in (re.match(r"^day_(\d{4}-\d\d-\d\d)\.json$", n) for n in names) if m)


def _load(dir_: str, day: str) -> dict:
    try:
        with open(os.path.join(dir_, f"day_{day}.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


_CACHE: Dict[tuple, dict] = {}


def build(day_dir: str, chain_dir: str, today: str, words_fn=None, extra_today: Optional[List[dict]] = None) -> dict:
    """Every closed trade in the day files -> receipts, re-entries and the scoreboard for today / this week / all time.
    `words_fn(day) -> {trade_id: [words]}` hands in the engine's words (fold_live.past_record); `extra_today` is the
    server's live list for today (the file lags it). Chain reads are cached per (file, mtime, legs)."""
    trs = []
    for d in scan_days(day_dir):
        ts = list(extra_today) if d == today and extra_today is not None else _load(day_dir, d).get("hold_trades") or []
        trs += [dict(t, day=d) for t in ts if isinstance(t, dict) and t.get("id") and t.get("t0")]
    rs, by_id = [], {t["id"] + t["day"]: t for t in trs}
    typ, typ_src = float(TYPICAL_SEED_S), "seed 20 min"
    series_of: Dict[tuple, list] = {}
    for d in sorted({t["day"] for t in trs}):
        legs: Dict[str, set] = {}
        for t in trs:
            if t["day"] == d:
                legs.setdefault(t["idx"], set()).add((float(t["k"]), t["side"]))
        for idx, lg in legs.items():
            path = os.path.join(chain_dir, f"chain_{idx}_{d}.jsonl")
            p = path if os.path.exists(path) else path + ".gz"
            try:
                mt = int(os.path.getmtime(p) // 120)     # a growing day file is re-read at most every 2 min
            except OSError:
                mt = None
            key = (p, mt, tuple(sorted(lg)))
            if key not in _CACHE:
                _CACHE[key] = chain_series(path, sorted(lg)) if mt is not None else {}
            for (k, ty), s in _CACHE[key].items():
                series_of[(d, idx, k, ty)] = s
    words = {}
    for d in sorted({t["day"] for t in trs}):
        try:
            words[d] = (words_fn(d) if words_fn else {}) or {}
        except Exception:                        # the engine's words are additive: a failure costs the amber read only
            words[d] = {}
    for t in trs:
        if not t.get("exit_t"):
            continue
        rs.append(receipt(t, series_of.get((t["day"], t["idx"], float(t["k"]), t["side"])), words[t["day"]].get(t["id"]), typ))
    typ, typ_src = typical(rs, {r["id"]: by_id[r["id"] + r["day"]] for r in rs})
    if typ != TYPICAL_SEED_S:                      # the fear clock reads the typical: one more pass with it
        rs = [receipt(by_id[r["id"] + r["day"]], series_of.get((r["day"], by_id[r["id"] + r["day"]]["idx"],
              float(by_id[r["id"] + r["day"]]["k"]), by_id[r["id"] + r["day"]]["side"])),
              words[r["day"]].get(r["id"]), typ) for r in rs]
    re_ = reentries([t for t in trs])
    wk = week_of(today)
    pick = lambda f: ([r for r in rs if f(r["day"])], [x for x in re_ if f(x["day"])])   # noqa: E731
    return {"ok": True, "today": today, "typical_s": typ, "typical_src": typ_src, "receipts": rs, "reentries": re_,
            "scoreboard": {"today": scoreboard(*pick(lambda d: d == today)),
                           "week": scoreboard(*pick(lambda d: week_of(d) == wk)),
                           "all": scoreboard(*pick(lambda d: True))},
            "tag": {"M": ["hold_s", "exit_px (her fill)", "post"], "I": ["fear", "amber", "typical_s", "exit_px (the chain)"]}}


# ---- the import's write: backup first, idempotent -----------------------------------------------------------------------
def import_plan(text: str, day_dir: str, door=None) -> dict:
    """The preview: trips per day, which are new and which are already there (same trip id, or every fill's trade_id
    already on a trip). `door(trip) -> (trade, why)` is server._hold_trade, so an import is checked like a mark."""
    fills, skipped = read_csv(text)
    plan: Dict[str, dict] = {}
    for st in trips(fills):
        d = plan.setdefault(st["day"], {"new": [], "have": [], "refused": []})
        have = _load(day_dir, st["day"]).get("hold_trades") or []
        ids = {t.get("id") for t in have}
        fids = {f for t in have for f in (t.get("fill_ids") or [])}
        mine = [f[4] for f in st["fills"]]
        if st["id"] in ids or (mine and all(f in fids for f in mine)):
            d["have"].append(st["id"])
            continue
        if door is not None:
            tr, why = door({**st, "qty": st["qty"]}, "import")
            if tr is None:
                d["refused"].append(f"{st['id']}: {why}")
                continue
        d["new"].append(st)
    return {"ok": True, "fills": len(fills), "skipped": skipped, "days": plan}


def import_write(plan: dict, day_dir: str, today: str, stamp: Optional[str] = None) -> dict:
    """Write the plan's new trips into the day files (never today's: the live server owns it -- the caller appends those
    under its lock). Each touched file is copied to day_<d>.json.bak-import-<stamp> first."""
    stamp = stamp or time.strftime("%Y%m%d-%H%M%S")
    wrote, backups, for_today = {}, [], []
    for d, x in sorted((plan.get("days") or {}).items()):
        new = [_slim(t) for t in x["new"]]
        if not new:
            continue
        p = os.path.join(day_dir, f"day_{d}.json")
        if os.path.exists(p):
            b = f"{p}.bak-import-{stamp}"
            shutil.copy2(p, b)
            backups.append(b)
        if d == today:
            for_today += new
            continue
        doc = _load(day_dir, d)
        have = doc.get("hold_trades") or []
        doc.update(day=d, hold_trades=have + new, saved_at=time.time())
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        os.replace(tmp, p)
        wrote[d] = [t["id"] for t in new]
    return {"wrote": wrote, "backups": backups, "for_today": for_today}


def _slim(st: dict) -> dict:
    """A trip as a hold_trades record: the door's fields + the fills and her exit fill (the receipts read them)."""
    return {"id": st["id"], "idx": st["idx"], "k": st["k"], "side": st["side"], "role": st["role"], "t0": st["t0"],
            "p0": st["p0"], "qty": st["qty"], "exit_t": st["exit_t"], "src": "import", "expiry": st.get("expiry"),
            "exit_px": st.get("exit_px"), "fills": st["fills"], "fill_ids": [f[4] for f in st["fills"]]}
