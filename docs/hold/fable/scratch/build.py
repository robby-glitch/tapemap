"""Read-only replay builder for the HOLD/FOLD prototype (docs/hold/fable).

GET only, no orders. Reuses the tool's own readers: fronts.read (§1d),
grounds._oi/_cvd/_flow (the grounding), trendbox.rows (the trend box),
prints.with_cvd + bar_flags on ux_log's ladder record. The chain minute grid
is rebuilt from data/chain/chain_<IDX>_<day>.jsonl exactly as ChainState keeps
it: the LAST snapshot of each minute, oi_chg since the open, ltp per strike.
Peak OI is the RUNNING peak as of the minute (causal), never the day's end.

Writes docs/hold/fable/data.js. Nothing else is written anywhere.
"""
import csv
import json
import os
import sys
from collections import defaultdict

TAPEMAP = r"C:\Users\kaam\Desktop\operator mode\tapemap"
OUT = os.path.join(TAPEMAP, "docs", "hold", "fable", "data.js")
TRADEBOOK = r"C:\Users\kaam\Downloads\tradebook-ZVP031-FO (2).csv"
sys.path.insert(0, TAPEMAP)
os.chdir(TAPEMAP)

import board                       # noqa: E402
import daylog                      # noqa: E402
import fronts                      # noqa: E402
import grounds                     # noqa: E402
import prints                      # noqa: E402
import trendbox                    # noqa: E402
import upstox_feed                 # noqa: E402
import upstox_instruments          # noqa: E402
import upstox_rest                 # noqa: E402
import ux_log                      # noqa: E402

TOK = upstox_feed.read_token()     # never printed
ROW, ANCHOR = 5.0, 0.0             # /api/tape's default ladder row when no GoCharting record [I]
RUNS_WHY = "fill runs need the live book; the day record holds bars, not fills"
CLOSE = "15:29"


def mm(t):
    return int(t[:2]) * 60 + int(t[3:5])


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


# ------------------------------------------------------------------ the chain grid
def grid_from_chain(idx, day):
    """(minutes, opens) shaped like ChainState.minutes / _board_opens."""
    path = f"data/chain/chain_{idx}_{day}.jsonl"
    minutes, opens = {}, {}
    try:
        fh = daylog.open_text(path)
    except OSError:
        return None, None, f"no chain record for {idx} on {day}"
    with fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            t = str(r.get("ts", ""))[:5]
            if not t or r.get("spot") is None:
                continue
            k, px = {}, {}
            for s in r.get("strikes") or []:
                ce, pe = s.get("ce") or {}, s.get("pe") or {}
                if not isinstance(ce.get("oi"), (int, float)) or not isinstance(pe.get("oi"), (int, float)):
                    continue
                kk = int(s["k"])
                k[kk] = (float(ce.get("oi_chg") or 0), float(pe.get("oi_chg") or 0))
                px[kk] = (ce.get("ltp"), pe.get("ltp"))
                for side, leg in (("ce", ce), ("pe", pe)):
                    opens.setdefault((float(kk), side), float(leg["oi"]) - float(leg.get("oi_chg") or 0))
            if k:
                minutes[t] = {"spot": float(r["spot"]), "k": k, "px": px}
    return minutes, opens, None


def peak_asof(opens, ks, S_RP, j):
    """{(k, 'ce'|'pe'): running-high absolute OI at mark j} -- what fronts.read ranks by."""
    times, spots, strikes, S, RP = S_RP
    out = {}
    for kk in strikes:
        for sd in ("CE", "PE"):
            o = opens.get((kk, sd.lower()))
            if o is not None:
                out[(kk, sd.lower())] = o + RP[(kk, sd)][j]
    return out


# ------------------------------------------------------------------ the ladder
def ladder(idx, day):
    raw = [b for b in ux_log.read_bars(day, idx) if isinstance(b.get("t"), (int, float))]
    if not raw:
        return [], f"no ux ladder record for {idx} on {day}"
    out = []
    for b in prints.with_cvd(raw):
        f = prints.bar_flags(b, ROW, ANCHOR) or {}
        out.append({k: b.get(k) for k in ("t", "o", "h", "l", "c", "vol", "buy", "sell", "delta", "cvd", "oi")}
                   | {"stacks": f.get("stacks") or []})
    return out, None


def bar_min(b):
    return (int(b["t"]) // 1000 + 19800) % 86400 // 60


# ------------------------------------------------------------------ the index
OLD = {}
try:
    _s = open(OUT, encoding="utf-8").read()
    OLD = json.loads(_s[len("window.HOLD_DATA = "):].rstrip().rstrip(";")).get("days") or {}
except (OSError, ValueError):
    OLD = {}


def index_candles(idx, day):
    """(candles newest-first as Upstox sends them, source note). REST first [M]; else the
    earlier frozen record's per-minute close/high/low (REST, frozen the same night) [M];
    else the chain's per-minute spot with high = low = close [I]. Never silent."""
    key = upstox_instruments.index_key(idx)
    c = upstox_rest.historical(key, TOK, day, "1minute")
    if not c:
        c = [x for x in upstox_rest.intraday(key, TOK, "1minute") if str(x[0])[:10] == day]
    if c:
        return c, "Upstox REST 1-min index candles [M]"
    old = (OLD.get(f"{idx}|{day}") or {}).get("minutes")
    if old and all(m.get("px") is not None for m in old):
        out, prev = [], None
        for m in old:
            o = prev if prev is not None else m["px"]
            out.append([f"{day}T{m['t']}:00+05:30", o, m["hi"], m["lo"], m["px"], 0, 0])
            prev = m["px"]
        return list(reversed(out)), "index candles re-read from the record frozen from REST on 2026-09-24 night [M]; opens = prior close"
    minutes, _o, why = grid_from_chain(idx, day)
    if minutes:
        out = [[f"{day}T{t}:00+05:30", r["spot"], r["spot"], r["spot"], r["spot"], 0, 0] for t, r in sorted(minutes.items())]
        return list(reversed(out)), "index candles RECONSTRUCTED from the chain's per-minute spot [I]: highs and lows are closes, so swings are weaker; REST had no candles for this day at build time"
    return [], f"could not check — no index candles for {idx} on {day} from REST, the frozen record or the chain"


def pivots(m1, day):
    """Confirmed 5-min swing highs/lows of TODAY (trendbox PIV=2, 09:15-aligned
    closed bars): [{kind, price, bar, confirm}] where `confirm` is the last
    minute of the second bar after the pivot -- the first minute the pivot is
    known. Strict comparisons, as trendbox.trow does."""
    rows = [r for r in trendbox.candles(m1) if r[0] == day]
    bars = trendbox.agg(rows, 5)          # (day, start, end, o, h, l, c)
    P = trendbox.PIV
    out = []
    for i in range(P, len(bars) - P):
        hi = all(bars[i][4] > bars[x][4] for x in range(i - P, i)) and all(bars[i][4] > bars[x][4] for x in range(i + 1, i + 1 + P))
        lo = all(bars[i][5] < bars[x][5] for x in range(i - P, i)) and all(bars[i][5] < bars[x][5] for x in range(i + 1, i + 1 + P))
        conf = hm(trendbox.slot_end(bars[i + P][1], 5))
        if hi:
            out.append({"kind": "H", "price": bars[i][4], "bar": bars[i][1], "confirm": conf})
        if lo:
            out.append({"kind": "L", "price": bars[i][5], "bar": bars[i][1], "confirm": conf})
    return out


FAM_FOR = ("NIFTY", "SENSEX")          # the HOLD window's four combos; BANKNIFTY has no premium in the record


def load_frame(idx, day):
    """[(ts, setup)] for idx from data/frame/frame_<day>.jsonl, or None."""
    p = f"data/frame/frame_{day}.jsonl"
    try:
        fh = daylog.open_text(p)
    except OSError:
        return None
    out = []
    with fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("idx") == idx and r.get("ts"):
                out.append((r["ts"][:5], r.get("setup")))
    return out or None


def load_calls(idx, day):
    p = f"data/calls/calls_{day}.jsonl"
    try:
        fh = daylog.open_text(p)
    except OSError:
        return None
    out = []
    with fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("idx") == idx and r.get("t"):
                out.append(r)
    return out or None


# ------------------------------------------------------------------ one index-day
def build_day(idx, day):
    print(f"-- {idx} {day}")
    minutes, opens, grid_why = grid_from_chain(idx, day)
    bars, lad_why = ladder(idx, day)
    m1, trend_src = index_candles(idx, day)
    print("   index candles:", trend_src)
    daily = trendbox.fetch_daily(idx, day, TOK)
    closes = {r[1]: {"o": r[2], "h": r[3], "l": r[4], "c": r[5]} for r in trendbox.candles(m1) if r[0] == day}
    if not closes:
        raise RuntimeError(f"{idx} {day}: no index candles")
    g = fronts.grid(minutes) if minutes else None
    all_folds = fronts.folds(minutes, g) if minutes else []
    jx = {t: j for j, t in enumerate(g[0])} if g else {}
    strikes = g[2] if g else []
    out_minutes = []
    tcache = {}
    chain_marks = sorted(minutes) if minutes else []
    def marks_upto(t):
        return sum(1 for m in chain_marks if m <= t)
    frame_rows = load_frame(idx, day)
    def setup_at(t):
        if frame_rows is None:
            return {"why": f"could not check — no frame record for {idx} on {day}"}
        prior = [r for r in frame_rows if r[0] <= t]
        if not prior:
            return {"why": "could not check — no frame row yet"}
        ts, su = prior[-1]
        if not su or not su.get("side") or su.get("state") in (None, "IDLE", "WAITING"):
            return {"t": ts, "why": "checked, none — nothing armed"}
        px = closes.get(t, {}).get("c")
        lvl = su.get("level")
        ctx = {"plays": [f"FADE a test of {lvl:.0f} (zone {su['side']} {su.get('state')})"]} if lvl is not None else {}
        closed = [b for b in bars if bar_min(b) <= mm(t) - 4]
        g = grounds.ground(ctx, px, closed, None, fr_for_ground(t), runs_why=RUNS_WHY) if ctx else {"calls": []}
        call = g["calls"][0] if g["calls"] else None
        return {"t": ts, "side": su["side"], "state": su.get("state"), "level": lvl, "fire": su.get("fire"),
                "visit": su.get("visit"), "status": call["status"] if call else None,
                "fam": {k: call[k] for k in ("oi", "cvd", "flow")} if call else None, "tag": "I"}
    calls_rows = load_calls(idx, day)
    def calls_at(t):
        if calls_rows is None:
            return {"why": f"could not check — the calls log begins 2026-09-24 (none for {idx} on {day})"}
        prior = [r for r in calls_rows if r["t"] <= t]
        if not prior:
            return {"why": "could not check — no engine bar yet"}
        r = prior[-1]
        return {"t": r["t"], "calls": [{k: c.get(k) for k in ("source", "text", "kind", "dir", "status", "oi", "cvd", "flow")} for c in r.get("calls") or []]}
    _fr_cache = {}
    def fr_for_ground(t):
        return _fr_cache.get(t, [])
    for t in sorted(closes):
        if t < "09:15" or t > CLOSE:
            continue
        rec = {"t": t, "px": closes[t]["c"], "hi": closes[t]["h"], "lo": closes[t]["l"]}
        # trend rows (the three REGIME reads), forming rows kept as null
        tr = trendbox.rows(daily["m1_prior"], m1, daily["m30"], daily["d1"], day, t)
        rec["trend"] = {k: (tr["rows"][k]["v"] if tr else None) for k in ("5m", "15m", "1h")}
        # fronts as of t (causal peak) and folds up to t
        fr, fr_why = [], None
        if minutes and t in jx:
            cut = fronts.cut(minutes, t)
            fr = fronts.read(cut, peak_asof(opens, strikes, g, jx[t]))
            fr_why = None if fr else "no minute carries a spot and a strike grid yet"
        elif minutes:
            # no chain mark this minute: use the newest mark at or before t if within STALE_MIN
            prior = [m for m in g[0] if m <= t]
            if prior and mm(t) - mm(prior[-1]) <= fronts.STALE_MIN:
                cut = fronts.cut(minutes, prior[-1])
                fr = fronts.read(cut, peak_asof(opens, strikes, g, jx[prior[-1]]))
            else:
                fr_why = f"chain grid stale since {prior[-1]}" if prior else "chain record starts later than this minute"
        else:
            fr_why = grid_why
        rec["spot"] = (minutes.get(t) or {}).get("spot") if minutes else None
        _fr_cache[t] = fr
        rec["fronts"] = [{k: f[k] for k in ("k", "side", "oi", "chg", "peak", "peak_at", "from_peak", "slope", "state")} for f in fr]
        rec["fronts_why"] = fr_why
        rec["folds"] = [{k: e[k] for k in ("k", "side", "t", "high_at", "off", "spot_fold")} for e in all_folds if e["t"] <= t]
        # closed ladder bars as of t
        closed = [b for b in bars if bar_min(b) <= mm(t) - 4]
        F = grounds.facts(closed, None, fr, runs_why=RUNS_WHY) if not lad_why else {
            "cvd": None, "flow": None, "cvd_why": lad_why, "flow_why": lad_why,
            "oi": ({"ce": next((f for f in fr if f["side"] == "CE"), None), "pe": next((f for f in fr if f["side"] == "PE"), None)} if fr else None),
            "oi_why": None if fr else (fr_why or "near-ATM fronts not read")}
        if fr_why and not fr:
            F["oi"], F["oi_why"] = None, fr_why
        rec["facts"] = {"cvd": F.get("cvd"), "flow": F.get("flow"), "fut_oi": F.get("fut_oi"),
                        "cvd_why": F.get("cvd_why"), "flow_why": F.get("flow_why"), "oi_why": F.get("oi_why")}
        # the four (role, want) combos, straight from grounds
        fam = {}
        for role in ("buyer", "writer"):
            for want in (1, -1):
                kind, d = ("move", want) if role == "buyer" else ("exhaust", -want)
                fam[f"{role}{'+' if want > 0 else '-'}"] = {
                    "oi": grounds._oi(kind, d, F), "cvd": grounds._cvd(kind, d, F), "flow": grounds._flow(kind, d, F)}
        rec["fam"] = fam if idx in FAM_FOR else None
        # ---- BETTER-RULES §1: the board's own reads at this minute
        s_now = rec["spot"] if rec["spot"] is not None else closes[t]["c"]
        try:
            rec["oi_read"] = list(board.oi_read(fr, s_now)) if fr else ["NOT READ", fr_why or "fronts not read"]
        except Exception as e:  # noqa: BLE001
            rec["oi_read"] = ["NOT READ", f"could not check — {type(e).__name__}"]
        rg = trendbox.regime(tr, tuple(rec["oi_read"]))
        rec["regime"] = rg
        ag = board.aggression(F) if not lad_why else (0, None, None, board.CC + lad_why)
        rec["aggr"] = {"dir": ag[0], "word": ag[1], "fact": ag[2], "why": ag[3]}
        near = {}
        for sd in ("CE", "PE"):
            nf = board.nearer(fr, sd, s_now) if fr else None
            near[sd] = {k: nf[k] for k in ("k", "state", "chg", "peak", "peak_at")} if nf else None
        rec["near"] = near if fr else None
        rec["marks"] = marks_upto(t)
        rec["setup"] = setup_at(t)
        rec["calls"] = calls_at(t)
        out_minutes.append(rec)
    # premiums per strike-side per minute, from the grid (the chain's expiry)
    px = {}
    if minutes:
        for t, r in minutes.items():
            for kk, (ce, pe) in (r.get("px") or {}).items():
                if ce is not None:
                    px.setdefault(f"{int(kk)}CE", {})[t] = ce
                if pe is not None:
                    px.setdefault(f"{int(kk)}PE", {})[t] = pe
    return {"idx": idx, "day": day, "minutes": out_minutes, "pivots": pivots(m1, day),
            "px": px, "px_why": grid_why, "ladder_why": lad_why, "chain_why": grid_why, "trend_src": trend_src,
            "session_hi": max(c["h"] for c in closes.values()), "session_lo": min(c["l"] for c in closes.values())}


# ------------------------------------------------------------------ her trades, flat-to-flat
def round_trips():
    fills = defaultdict(list)
    with open(TRADEBOOK, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fills[(r["trade_date"], r["symbol"])].append(r)
    out = []
    for (day, sym), rows in fills.items():
        rows.sort(key=lambda r: r["order_execution_time"])
        idx = "SENSEX" if sym.startswith("SENSEX") else "BANKNIFTY" if sym.startswith("BANKNIFTY") else "NIFTY"
        side, strike = sym[-2:], int(sym[-7:-2])
        pos, buys, sells = 0.0, [], []
        for r in rows:
            q, p, ts = float(r["quantity"]), float(r["price"]), r["order_execution_time"][11:19]
            if r["trade_type"] == "buy":
                buys.append((ts, q, p))
                pos += q
            else:
                sells.append((ts, q, p))
                pos -= q
            if pos == 0 and buys and sells:
                bq, sq = sum(b[1] for b in buys), sum(s[1] for s in sells)
                out.append({"idx": idx, "day": day, "strike": strike, "side": side, "role": "buyer",
                            "qty": int(bq), "entry_ts": buys[0][0], "exit_ts": sells[-1][0],
                            "entry": round(sum(b[1] * b[2] for b in buys) / bq, 2),
                            "exit": round(sum(s[1] * s[2] for s in sells) / sq, 2),
                            "expiry": rows[0]["expiry_date"], "src": "tradebook"})
                buys, sells = [], []
    out.sort(key=lambda x: (x["day"], x["entry_ts"]))
    return out


def main():
    trades = round_trips()
    days = sorted({(i, d) for d in {t["day"] for t in trades} for i in ("NIFTY", "BANKNIFTY", "SENSEX")})
    data = {}
    for idx, day in days:
        data[f"{idx}|{day}"] = build_day(idx, day)
    # writer examples, chosen by RULE, not by outcome: the #1 CE front by
    # session-peak OI at the stated minute, sold at the grid's LTP then.
    for idx, day, at in (("SENSEX", "2026-09-24", "11:00"), ("NIFTY", "2026-09-23", "10:30")):
        d = data[f"{idx}|{day}"]
        rec = next((m for m in d["minutes"] if m["t"] == at), None)
        ce = next((f for f in (rec or {}).get("fronts") or [] if f["side"] == "CE"), None)
        if ce:
            k = int(ce["k"])
            p = (d["px"].get(f"{k}CE") or {}).get(at)
            trades.append({"idx": idx, "day": day, "strike": k, "side": "CE", "role": "writer", "qty": 20 if idx == "SENSEX" else 65,
                           "entry_ts": at + ":00", "exit_ts": None, "entry": p, "exit": None, "expiry": None,
                           "src": f"example: short the #1 CE front by peak OI at {at}"})
    for t in trades:
        t["id"] = f"{t['day']}_{t['idx']}_{t['strike']}{t['side']}_{t['entry_ts'].replace(':', '')}_{t['role']}"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.HOLD_DATA = ")
        json.dump({"days": data, "trades": trades, "built": "2026-09-24 after close",
                   "params": {"PIV": trendbox.PIV, "W": grounds.W, "STRONG": grounds.STRONG, "ONE_SIDED": grounds.ONE_SIDED,
                              "NEAR": fronts.NEAR, "TOP": fronts.TOP_PER_SIDE, "UNWIND": fronts.UNWIND_FRAC,
                              "STALL": fronts.STALL_FRAC, "SLOPE": fronts.SLOPE_MARKS, "STALE": fronts.STALE_MIN}},
                  f, default=str, separators=(",", ":"))
        f.write(";\n")
    print("trades", len(trades), "days", list(data), "->", OUT, os.path.getsize(OUT) // 1024, "KB")


if __name__ == "__main__":
    main()
