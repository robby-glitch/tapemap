"""Per-minute, trade-independent facts for the HOLD/FOLD prototype. Read-only.

Every fact comes from TapeMap's own pure functions, called exactly as the server
calls them (fronts.read / board.nearer / fronts.folds / board.still_folded /
grounds.facts / trendbox.rows), on inputs CUT to each finished minute. Sources are
the day files under data/ (read, never written) plus REST candles frozen tonight.
The HOLD/FOLD rule itself is NOT here -- it lives once, in verdict.js.

Run from anywhere: python build_facts.py  ->  facts_<IDX>_<DAY>.json.gz
"""
import gzip
import json
import os
import sys

TM = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, TM)
os.chdir(TM)                     # the modules resolve data/ relative to here

import board          # noqa: E402
import book_log       # noqa: E402
import contract_bars  # noqa: E402
import daylog         # noqa: E402
import fronts         # noqa: E402
import grounds        # noqa: E402
import ladder         # noqa: E402
import prints         # noqa: E402
import runs as runs_mod   # noqa: E402
import tape_log       # noqa: E402
import trendbox       # noqa: E402
import upstox_feed    # noqa: E402
import upstox_instruments  # noqa: E402
import upstox_rest    # noqa: E402
import ux_log         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STEP = {"NIFTY": 50.0, "SENSEX": 100.0, "BANKNIFTY": 100.0}
JOBS = [(i, d) for d in ("2026-09-22", "2026-09-23", "2026-09-24") for i in ("NIFTY", "BANKNIFTY", "SENSEX")]
SESSION = [f"{h:02d}:{m:02d}" for h in range(9, 16) for m in range(60) if "09:15" <= f"{h:02d}:{m:02d}" < "15:30"]


def mm(t):
    return int(t[:2]) * 60 + int(t[3:5])


def hh(ms):
    return grounds._hh(ms)


def read_chain(idx, day):
    """The poller's own record -> ChainState.minutes shape, running peak per minute,
    and per-minute premium o/h/l/c/v per strike-side (from snapshot LTPs)."""
    minutes, peak_at, peak = {}, {}, {}
    prem, last_vol, spot1 = {}, {}, {}
    path = f"data/chain/chain_{idx}_{day}.jsonl"
    if not daylog.exists(path):
        return None
    with daylog.open_text(path) as f:
        for line in f:
            try:
                s = json.loads(line)
            except ValueError:
                continue
            m = (s.get("ts") or "")[:5]
            if not ("09:15" <= m < "15:30") or s.get("spot") is None:
                continue
            ks = {}
            for st in s.get("strikes") or []:
                k = float(st["k"])
                ks[k] = ((st["ce"].get("oi_chg") or 0.0), (st["pe"].get("oi_chg") or 0.0))
                for side in ("ce", "pe"):
                    leg = st.get(side) or {}
                    if isinstance(leg.get("oi"), (int, float)):
                        peak[(k, side)] = max(peak.get((k, side), 0.0), float(leg["oi"]))
                    ltp, vol = leg.get("ltp"), leg.get("vol")
                    if isinstance(ltp, (int, float)) and ltp > 0:
                        key = f"{int(k)}{side.upper()}"
                        b = prem.setdefault(key, {}).get(m)
                        dv = 0.0
                        if isinstance(vol, (int, float)):
                            dv = max(0.0, vol - last_vol.get(key, vol))
                            last_vol[key] = vol
                        if b is None:
                            prem[key][m] = [ltp, ltp, ltp, ltp, dv]
                        else:
                            b[1], b[2], b[3] = max(b[1], ltp), min(b[2], ltp), ltp
                            b[4] += dv
            minutes[m] = {"spot": s["spot"], "k": ks}
            peak_at[m] = dict(peak)
            o = spot1.get(m)
            x = float(s["spot"])
            spot1[m] = [x, x, x, x] if o is None else [o[0], max(o[1], x), min(o[2], x), x]
    # the server's own backfill marks (REST-rebuilt minutes the socket never saw),
    # frozen tonight from /api/oihist, so 09-24 reads exactly what the server read
    fz = os.path.join(HERE, f"frozen_oihist_{idx}_{day}.json.gz")
    if os.path.exists(fz):
        srv = json.load(gzip.open(fz, "rt"))
        for m in srv.get("backfill_marks") or []:
            if m not in minutes and "09:15" <= m < "15:30":
                r = srv["minutes"][m]
                minutes[m] = {"spot": r["spot"], "k": {float(k): tuple(v) for k, v in r["k"].items()}}
                peak_at[m] = {}
    return minutes, peak_at, prem, spot1


def ux_facts_inputs(idx, day):
    """Ladder bars as /api/tape serves them, and fill runs rebuilt from the book
    record the way a restart rebuilds them (server._ux_drain), without writing."""
    raw = tape_log.read_bars(day, idx)
    row = float((raw[0].get("rowSize") if raw else None) or 5)
    anchor = float((raw[0].get("rowAnchor") if raw else None) or 0)
    bars = []
    for b in prints.with_cvd([b for b in ux_log.read_bars(day, idx) if tape_log.bar_t(b) is not None]):
        f = prints.bar_flags(b, row, anchor)
        bars.append({**{k: b.get(k) for k in ("t", "o", "h", "l", "c", "vol", "buy", "sell", "delta", "cvd", "oi")},
                     "stacks": (f or {}).get("stacks") or []})
    lot, tick = upstox_instruments.lot_tick(idx)
    lad = ladder.Ladder(lot=lot, tick=tick, idx=idx, day=day, lot_src="dump")
    R = runs_mod.Runs(lot=lot)
    why_at = {}
    n_rows = 0
    for r in book_log.read_rows(day, idx):
        n_rows += 1
        _closed, fills = lad.step(r)
        for f in fills:
            R.on_fill(f)
        why_at[hh(r["t"])] = R.why()
    return bars, list(R.events), why_at, n_rows


def premium_series(idx, day, chain_prem):
    """{leg: {"src", "o","c","vw","sd"} aligned to SESSION}. REST candles frozen
    tonight are [M]; the chain record's LTP snapshots are [I] (reconstructed)."""
    out = {}
    fz = os.path.join(HERE, f"rest_opt_{idx}_{day}.json.gz")
    if os.path.exists(fz):
        rest = json.load(gzip.open(fz, "rt"))
        for leg, cs in rest.items():
            rows = {str(c[0])[11:16]: (float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])) for c in cs
                    if str(c[0])[:10] == day}
            out[leg] = ("M", rows)
    for leg, rows in chain_prem.items():
        if leg not in out:
            out[leg] = ("I", {m: tuple(v) for m, v in rows.items()})
    res = {}
    for leg, (src, rows) in out.items():
        seq = [rows.get(m) for m in SESSION]
        bands = contract_bars.vwap_sigma([(r[1], r[2], r[3], r[4]) if r else (0, 0, 0, 0) for r in seq])
        o, c, vw, sd = [], [], [], []
        for r, b in zip(seq, bands):
            if r is None:
                o.append(None), c.append(None), vw.append(None), sd.append(None)
                continue
            o.append(round(r[0], 2)), c.append(round(r[3], 2))
            vw.append(round(b["vwap"], 2)), sd.append(round(b["u1"] - b["vwap"], 2))
        if any(x is not None for x in c):
            res[leg] = {"src": src, "o": o, "c": c, "vw": vw, "sd": sd}
    return res


def frozen_index(idx, day):
    """After midnight Upstox serves neither `intraday` nor `historical` for the session
    just closed. I did not freeze the index 1-min candles on 09-24 night; Fable did
    (Upstox REST, [M]), and on NIFTY 09-22 / 09-23 their per-minute close equals mine
    exactly. So a day REST no longer serves is read from their frozen record, and says
    so. Open is not stored there and trendbox never reads it (trow uses h / l / c)."""
    fz = os.path.join(HERE, "..", "..", "fable", "data.js")
    if not os.path.exists(fz):
        return [], "could not check — index candles no longer served by REST"
    txt = open(fz, encoding="utf-8").read()
    d = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])["days"].get(f"{idx}|{day}")
    if not d:
        return [], f"could not check — index candles for {idx} {day} not frozen (REST no longer serves them)"
    rows = [[f"{day}T{m['t']}:00+05:30", m["px"], m["hi"], m["lo"], m["px"], 0] for m in d["minutes"] if m.get("px") is not None]
    return list(reversed(rows)), None


def zone_rows(idx, day):
    """The zone machine's arms and entries for this index-day, as logged forward
    (data/trigger_log.jsonl, read-only), each visible at its 3-min bar's last minute."""
    out = []
    with open("data/trigger_log.jsonl", encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("day") != day or r.get("index") != idx or r.get("rule") != "zone":
                continue
            g = r.get("gate") or {}
            out.append({"kind": r.get("kind", "entry"), "t": r["t"], "vis": fronts.bar_last_minute(r["t"], 3),
                        "side": r.get("side"), "band": r.get("band"), "legal": g.get("legal"), "gate_why": g.get("why"),
                        "ctx": r.get("ctx") or {}, "px": r.get("px")})
    return out


def _ctx(c):
    """trigger_log stores ctx values as strings; grounds wants the engine's shapes."""
    import ast
    out = dict(c)
    for k in ("plays", "pin", "floor", "cap"):
        v = c.get(k)
        if isinstance(v, str):
            try:
                out[k] = ast.literal_eval(v)
            except (ValueError, SyntaxError):
                out[k] = None
    return out


def ground_zone(z, fr, bt, rt, rw, spot):
    """grounds.ground on the engine's own context at the zone row's bar -- what /api/calls
    would have shown then. Short form: [source, text, status] per call."""
    g = grounds.ground(_ctx(z["ctx"]), z.get("px") or spot, bt, rt, fr, runs_why=rw)
    return [[c["source"], c["text"][:90], c["status"]] for c in g["calls"]]


def calls_log(idx, day):
    """The engine's grounded calls as the face was served them (data/calls, 2026-09-24 on)."""
    import time as _t
    p = f"data/calls/calls_{day}.jsonl"
    if not daylog.exists(p):
        return {}, "could not check — the calls log starts on 2026-09-24"
    by = {}
    with daylog.open_text(p) as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("idx") != idx or not r.get("at"):
                continue
            m = _t.strftime("%H:%M", _t.localtime(r["at"]))
            by[m] = [[c["source"], c["text"][:90], c["status"],
                      c["oi"]["state"], c["cvd"]["state"], c["flow"]["state"]] for c in r.get("calls") or []]
    out, last = {}, None
    for t in SESSION:
        last = by.get(t, last)
        out[t] = last
    return out, None


def pivots(m1, day):
    """Confirmed 5-min swing highs/lows of today, ported rule for rule from Fable's
    scratch/build.py (trendbox PIV=2, 09:15-aligned closed bars, strict comparisons;
    `confirm` = the last minute of the second bar after the pivot). Feeds only the
    post-data STRUCTURE proposal (RULES 9.4)."""
    rows = [r for r in trendbox.candles(m1) if r[0] == day]
    bars = trendbox.agg(rows, 5)
    P = trendbox.PIV
    out = []
    for i in range(P, len(bars) - P):
        hi = all(bars[i][4] > bars[x][4] for x in range(i - P, i)) and all(bars[i][4] > bars[x][4] for x in range(i + 1, i + 1 + P))
        lo = all(bars[i][5] < bars[x][5] for x in range(i - P, i)) and all(bars[i][5] < bars[x][5] for x in range(i + 1, i + 1 + P))
        e = trendbox.slot_end(bars[i + P][1], 5)
        conf = f"{e // 60:02d}:{e % 60:02d}"
        if hi:
            out.append({"kind": "H", "price": bars[i][4], "bar": bars[i][1], "confirm": conf})
        if lo:
            out.append({"kind": "L", "price": bars[i][5], "bar": bars[i][1], "confirm": conf})
    return out


def front_row(f):
    if not f:
        return None
    return {"k": f["k"], "state": f["state"], "built": f["peak"] > 0, "chg": round(f["chg"]),
            "peak": round(f["peak"]), "peak_at": f["peak_at"], "words": board.state_words(f)}


def build(idx, day):
    got = read_chain(idx, day)
    if got is None:
        return {"idx": idx, "day": day, "why": f"could not check — no chain record for {idx} on {day}"}
    minutes, peak_at, cprem, spot1 = got
    step = STEP[idx]
    g = fronts.grid(minutes)
    times, spots, ks, S, RP = g
    jx = {t: j for j, t in enumerate(times)}
    evs = fronts.folds(minutes, g)
    # causal: folds on the full grid == folds on a grid cut at t, for events <= t
    # (checked 2026-09-25 on SENSEX 09-24 and NIFTY 09-23 at seven cuts each, 0 mismatches)
    bars, runs, why_at, n_book = ux_facts_inputs(idx, day)
    tok = upstox_feed.read_token()
    try:
        daily = trendbox.fetch_daily(idx, day, tok)
        key = upstox_instruments.index_key(idx)
        # the server reads today off `intraday`; `historical` serves only finished sessions
        m1 = (upstox_rest.intraday(key, tok) if day == __import__("time").strftime("%Y-%m-%d")
              else upstox_rest.historical(key, tok, day, "1minute"))
        tr_why = None
    except Exception as e:                               # noqa: BLE001
        daily, m1, tr_why = None, None, f"could not check — trend candles: {type(e).__name__}"
    tr_src = "Upstox index candles (REST)"
    if not m1:
        m1, why = frozen_index(idx, day)
        tr_src = "Upstox index candles [M], frozen 09-24 night in docs/hold/fable/data.js (REST no longer serves the day)"
        if not m1:
            # last resort: the chain record's own index spot, snapshot by snapshot, as 1-min OHLC [I]
            m1 = [[f"{day}T{t}:00+05:30", *v, 0] for t, v in sorted(spot1.items(), reverse=True)]
            tr_src = ("[I] index 1-min candles rebuilt from the chain record's spot snapshots "
                      "(REST no longer serves the day; highs/lows between snapshots are missed)")
            why = None
        tr_why = tr_why or why
    zones = zone_rows(idx, day)
    calls_at, calls_why = calls_log(idx, day)
    rows = []
    last_why = None
    ix = {r[1]: r[2:] for r in trendbox.candles(m1 or []) if r[0] == day}     # HH:MM -> (o, h, l, c)
    for t in SESSION:
        cut = fronts.cut(minutes, t)
        rec = {"t": t}
        marks = sorted(cut)
        if not marks:
            rec["blind"] = "could not check — no chain mark yet today"
            rows.append(rec)
            continue
        rec["spot"] = round(cut[marks[-1]]["spot"], 2)
        sw = fronts.stale(cut, t)
        if sw:
            rec["blind"] = "could not check — " + sw
        elif len(marks) < fronts.SLOPE_MARKS:
            rec["blind"] = (f"could not check — fronts forming: the build → stall → unwind sequence needs "
                            f"{fronts.SLOPE_MARKS} one-minute marks, {len(marks)} so far")
        pk = peak_at.get(marks[-1])
        fr = fronts.read(cut, pk)
        s = cut[marks[-1]]["spot"]
        if not fr:
            rec.setdefault("blind", "could not check — near-ATM fronts not read")
        rec["CE"] = front_row(board.nearer(fr, "CE", s)) if fr else None
        rec["PE"] = front_row(board.nearer(fr, "PE", s)) if fr else None
        j = jx.get(marks[-1])
        live = []
        for e in evs:
            age = mm(t) - mm(e["t"])
            if 0 <= age <= 15 and j is not None:
                live.append({"k": e["k"], "side": e["side"], "t": e["t"], "off": e["off"], "high_at": e["high_at"],
                             "still": board.still_folded(e, j, S, RP, jx)})
        rec["folds"] = live
        # grounds' CVD / FLOW, as _board_facts builds them for `asof`
        bt = [b for b in bars if b.get("t") is not None and mm(hh(b["t"])) + 5 <= mm(t)]
        rt = [r for r in runs if r.get("from_t") is None or hh(r["from_t"]) <= t]
        rw = why_at.get(t, last_why)
        last_why = rw
        if n_book == 0:
            rw = f"no book record for {idx} on {day}"
        F = grounds.facts(bt, rt, fr, runs_why=rw)
        c = F.get("cvd")
        rec["cvd"] = ({"d": round(c["d"]), "rank": c["rank"], "dpx": c["dpx"], "since": c["since"],
                       "dt": c["div_top"], "db": c["div_bottom"]} if c else None)
        rec["cvd_why"] = None if c else ("could not check — " + (F.get("cvd_why") or "no ladder bars"))
        fl = F.get("flow")
        rec["flow"] = {"b": fl["buy"], "s": fl["sell"], "rw": fl.get("runs_why")} if fl else None
        rec["flow_why"] = None if fl else ("could not check — " + (F.get("flow_why") or "no prints"))
        if daily and m1:
            trr = trendbox.rows(daily["m1_prior"], m1, daily["m30"], daily["d1"], day, t)
            rec["tr"] = {k: trr["rows"][k]["word"] for k in ("5m", "15m", "1h")} if trr else None
            if trr:
                sg = trendbox.strong(trr)
                oi = board.oi_read(fr, s) if fr else ("NOT READ", "fronts not read")
                rg = trendbox.regime(trr, oi)
                rec["strong"] = [sg["word"], *sg["n"]]
                rec["reg"] = [rg["word"], *rg["price"], *rg["oi"]]
        else:
            rec["tr"] = None
        if rec["tr"] is None:
            rec["tr_why"] = tr_why or "could not check — no index candle yet"
        # the index's own 1-min candle labelled t [M] -- only for the post-data STRUCTURE
        # proposal (RULES 9.4, Fable's line); the registered-draft verdict never reads it
        c1 = ix.get(t)
        rec["ix"] = [c1[3], c1[1], c1[2]] if c1 else None
        rec["eng"] = calls_at.get(t)
        for z in zones:
            if z["vis"] == t:
                z["ground"] = ground_zone(z, fr, bt, rt, rw, s)
        rows.append(rec)
    for z in zones:
        z.pop("ctx", None)
    return {"idx": idx, "day": day, "step": step, "zones": zones, "calls_why": calls_why, "lot": upstox_instruments.lot_tick(idx)[0],
            "minutes": rows, "prem": premium_series(idx, day, cprem), "pivots": pivots(m1 or [], day),
            "src": {"grid": f"data/chain/chain_{idx}_{day}.jsonl ({len(times)} marks)",
                    "ladder": f"data/tape/ux_{idx}_{day}.jsonl ({len(bars)} bars), runs rebuilt from "
                              f"data/book ({n_book} rows, {len(runs)} runs)",
                    "trend": tr_src if not tr_why else tr_why},
            "folds_all": evs}


if __name__ == "__main__":
    only = sys.argv[1:]
    for idx, day in JOBS:
        if only and f"{idx}_{day}" not in only:
            continue
        out = build(idx, day)
        p = os.path.join(HERE, f"facts_{idx}_{day}.json.gz")
        with gzip.open(p, "wt", encoding="utf-8") as f:
            json.dump(out, f, default=str)
        print(idx, day, len(out.get("minutes") or []), "minutes,", len(out.get("prem") or {}), "legs",
              out.get("why") or out.get("src"))
