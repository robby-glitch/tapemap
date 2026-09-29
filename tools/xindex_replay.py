"""tools/xindex_replay.py -- replay the SHADOW cross-index read (xindex.py) over recorded days, read-only, as-of.

    python tools/xindex_replay.py                      # every day with a book file for all three indices
    python tools/xindex_replay.py 2026-09-29
    python tools/xindex_replay.py --out docs/reader/replays

Per day, per 3-minute bar close, xindex.step() gets exactly what it would have had live:
  * the reader's legs, forming leg and auction for NIFTY, BANKNIFTY and SENSEX: reader.Engine stepped minute by minute
    on the same inputs tools/reader_replay.py uses (book, the 29 Sep exchange candle, GoCharting as of arrival);
  * her zone machine's state from data/trigger_log.jsonl (rule "zone" only; never pooled with 5c). An arm row makes
    ARMED until its trigger or RUN_WINDOW bars; a trigger row makes "trigger hua"; after it the trade's exit is not in
    the log, so the zone reads CAN'T CHECK until that side arms again. A day with no zone rows for an index is WAITING
    only where verified live (BANKNIFTY 29 Sep, supervisor 2026-09-29); otherwise CAN'T CHECK. Never a reconstruction;
  * the option chain (data/chain/) for the walls, now vs WRITE_MIN minutes before.
Writes docs/reader/replays/xindex_<day>.txt: the LOOK HERE timeline, notes, counts against the pre-registered bars,
and the automatic misdescription audit. Nothing under data/ is written. No outcome is scored: no hit rate.
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import band_rotation  # noqa: E402
import reader  # noqa: E402
import reader_replay as rr  # noqa: E402
import xindex  # noqa: E402

VERIFIED_EMPTY = {("BANKNIFTY", "2026-09-29"): "WAITING verified live on 125 served bars (supervisor, 2026-09-29): "
                                               "every band touch was before the 09:25 anchor"}
BARS = {"awards": 10, "changes": 16, "flips6": 0, "word_changes": 12}      # pre-registered in 9-cross-index-design §4.4


def engine_for(idx, day):
    """The reader engine and its minutes, set up exactly as tools/reader_replay.replay() does (not run)."""
    key, lot, tick, expiry = rr.master(idx, day)
    if not lot:
        return None, None, None
    ik, exp_stamp = rr.stamp(idx, day)
    if exp_stamp:
        key, expiry = ik or key, exp_stamp
    mins, other, _ = rr.day_minutes(idx, day, lot, tick, key)
    prior = [d for d in rr.book_days(idx) if d < day][-int(reader.TH["PRIOR_N"]):]
    pm = []
    for d in prior:
        _, l2, t2, _ = rr.master(idx, d)
        pm.append(rr.day_minutes(idx, d, l2 or lot, t2 or tick, with_candles=False)[0])
    gc, _ = rr.gc_bars(day) if idx == "NIFTY" else ([], None)
    eng = reader.Engine(idx=idx, day=day, lot=lot, unit=reader.prior_unit(pm) if pm else None, expiry=expiry, gc=gc,
                        gc_expected=(idx == "NIFTY"), other_oi=other,
                        prior_sigma=reader.oi_sigma(pm[-1]) if pm else None, contract=key,
                        spread=reader.prior_spread(pm) if pm else None)
    return eng, mins, lot


def zone_track(idx, day, rows):
    """label -> (zone for xindex or None, why). Her machine's logged zone rows only; never a reconstruction."""
    mine = [r for r in rows if r.get("rule") == "zone" and r.get("day") == day and r.get("index") == idx]
    if not mine:
        ok = VERIFIED_EMPTY.get((idx, day))
        why = ok or f"no {idx} zone rows today, and WAITING is not verified for this day"
        waiting = {"buy": {"state": "WAITING"}, "sell": {"state": "WAITING"}}
        return lambda label: (waiting if ok else None, why)
    ev = defaultdict(list)
    for r in mine:
        ev[r["side"]].append(r)

    def side_at(side, k):
        st, info, arm_m = "WAITING", {}, None
        for r in sorted(ev[side], key=lambda r: r["t"]):
            m = int(r["t"][:2]) * 60 + int(r["t"][3:])
            if m > k:
                break
            if r.get("kind") == "arm":
                arm_m = m
                st, info = "ARMED", {"level": r.get("level"),
                                     "ref": r.get("ref_high") if side == "BUY" else r.get("ref_low")}
            else:
                st, info, arm_m = ("TRIGGERED" if m == k else "CANT"), {"level": r.get("level")}, None
        if st == "ARMED" and (k - arm_m) // 3 > band_rotation.RUN_WINDOW:
            st, info = "WAITING", {}
        if st in ("ARMED", "TRIGGERED") and info.get("level") is not None:
            info["stop"] = round(info["level"] + (-1 if side == "BUY" else 1) * band_rotation.OPERATOR_STOP_PTS, 2)
        return {"state": st, **info}

    def at(label):
        k = int(label[:2]) * 60 + int(label[3:])
        z = {"buy": side_at("BUY", k), "sell": side_at("SELL", k)}
        active = any(z[s]["state"] in xindex.ZWORD for s in z)
        if not active and any(z[s]["state"] == "CANT" for s in z):
            return None, "her trade's exit is not in the log (zone rows record arms and triggers only)"
        return z, None
    return at


def chain_by_minute(idx, day):
    out = {}
    for r in rr.rows(os.path.join(rr.DATA, "chain", f"chain_{idx}_{day}.jsonl")):
        ts = r.get("ts")
        if isinstance(ts, str) and len(ts) >= 5:
            out[int(ts[:2]) * 60 + int(ts[3:5])] = r
    return out


def at_or_before(d, m):
    ks = [k for k in d if k <= m]
    return d[max(ks)] if ks else None


def replay_day(day, out_dir):
    trig = rr.rows(os.path.join(rr.DATA, "trigger_log.jsonl"))
    E, M, LOT, Z, ZWHY, CH, it = {}, {}, {}, {}, {}, {}, {}
    for i in xindex.IDXS:
        E[i], M[i], LOT[i] = engine_for(i, day)
        if E[i] is None or not M[i]:
            return None
        Z[i] = zone_track(i, day, trig)
        ZWHY[i] = Z[i]("09:15")[1]          # a day-level reason (no rows for this index today), else None
        CH[i] = chain_by_minute(i, day)
        it[i] = 0
    base = rr.day_ms(day, "00:00")
    state, outs, bad = None, [], []
    for close in range(555 + 3, 15 * 60 + 31, 3):
        asof = base + close * 60000
        snaps = {}
        for i in xindex.IDXS:
            ms = M[i]
            while it[i] < len(ms) and ms[it[i]]["t"] + 60000 <= asof:
                E[i].step(ms[it[i]])
                it[i] += 1
            e = E[i]
            if e.delta is None or not e.m:
                snaps[i] = {"ok": False, "why": "reader warming: no ruler yet"}
                continue
            label = f"{(close - 3) // 60:02d}:{(close - 3) % 60:02d}"
            zone, zwhy = Z[i](label)
            px = e.m[-1]["c"]
            now_c, then_c = at_or_before(CH[i], close - 1), at_or_before(CH[i], close - 1 - int(xindex.TH["WRITE_MIN"]))
            stale = now_c is None or close - 1 - int(now_c["ts"][:2]) * 60 - int(now_c["ts"][3:5]) > 3
            w = None if stale else xindex.walls(now_c, then_c, px, e.delta, LOT[i], day)
            snaps[i] = {"ok": True, "ruler": e.delta, "legs": e.legs, "forming": e.forming(), "auction": e.auction_state(),
                        "t_last": e.m[-1]["t"], "px": px, "zone": zone, "zone_why": zwhy,
                        "walls": w}
        out, state = xindex.step(asof, snaps, state)
        outs.append(out)
        bad += xindex.audit(out)
    return report(day, outs, state, bad, ZWHY, out_dir)


def report(day, outs, state, bad, zwhy, out_dir):
    L = [f"xindex {day} · {xindex.REV} · SHADOW (unsigned sheet) · counts of lines, never a %",
         "Sources: reader.py legs (futures; SENSEX = a thin tape: flow/WHO never vote), her zone from trigger_log "
         "(arms/triggers; after a trigger the exit is not logged -> CAN'T CHECK), chain walls. [M] price/OI, [I] side/WHO.",
         "Cash auction: bars after 15:15 read CAN'T CHECK and LOOK HERE is released."]
    for i, w in zwhy.items():
        if w:
            L.append(f"zone {i}: {w}")
    L += ["", "== LOOK HERE changes"]
    prev = None
    for o in outs:
        h = o["look"]["idx"]
        if h != prev:
            L.append(f"{o['t']}  {o['look']['line']}")
            prev = h
    L += ["", "== Every bar: LOOK · per index D n_for/n_check (against) word · sync"]
    for o in outs:
        parts = []
        for i, r in o["idx"].items():
            parts.append(f"{i[:4]} {xindex.ARROW[r['D']]} {r['n_for']}/{r['n_check']} ({r['n_against']}) {r['word']}")
        L.append(f"{o['t']} {(o['look']['idx'] or '-'):9s} | " + " | ".join(parts) + f" | {o['sync'].get('state')}")
    L += ["", "== Notes: confirmed / divergent / equal extremes, and sync state changes (not size changes)"]
    last = {}
    for o in outs:
        for k in ("high", "low"):
            ev = o["extremes"][k]
            if not ev or ev["verdict"] not in ("CONFIRMED", "DIVERGENT", "BARABAR"):
                last[k] = None
                continue
            key = ev["verdict"] + str(sorted((i, p["status"]) for i, p in ev["per"].items()))
            if key != last.get(k):
                ends = ev.get("ends")
                ld = xindex.lead(ev)
                L.append(f"{o['t']}  {ev['chip']}" + (" · khatam: " + ", ".join(
                    f"{i} {v:,.1f} ke {'upar' if k == 'high' else 'neeche'}" for i, v in ends.items()) if ends else "")
                    + (f" · {ld['chip']}" if ld else ""))
            last[k] = key
        sk = o["sync"].get("key") or o["sync"]["state"]
        if sk != last.get("sync"):
            L.append(f"{o['t']}  {o['sync']['chip']}")
            last["sync"] = sk
    c = {k: state[k] for k in ("changes", "awards", "switches", "releases", "flips6")}
    shown = sum(1 for o in outs if o["look"]["idx"])
    wc = state["word_changes"]
    L += ["", "== Counts against the pre-registered bars (9-cross-index-design §4.4; stated before these replays)",
          f"awards {c['awards']} (bar <= {BARS['awards']}) · changes {c['changes']} (bar <= {BARS['changes']}) · "
          f"switches {c['switches']} · releases {c['releases']} · flips inside 6 min {c['flips6']} (bar {BARS['flips6']})",
          "state-word changes per index: " + ", ".join(f"{i} {n}" for i, n in wc.items()) + f" (bar <= {BARS['word_changes']})",
          f"bars with a LOOK HERE: {shown} of {len(outs)}",
          f"misdescription audit (automatic): {len(bad)} violations (bar 0)"] + [f"  {b}" for b in bad[:40]]
    txt = "\n".join(L) + "\n"
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"xindex_{day}.txt"), "w", encoding="utf-8") as f:
            f.write(txt)
    return {"day": day, **c, "shown": shown, "bars": len(outs), "word_changes": dict(wc), "violations": len(bad)}


def main(argv):
    out = os.path.join(ROOT, "docs", "reader", "replays")
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    days = [a for a in argv if a[:2] == "20"]
    if not days:
        days = sorted(set.intersection(*[set(rr.book_days(i)) for i in xindex.IDXS]))
    for d in days:
        r = replay_day(d, out)
        print(json.dumps(r))


if __name__ == "__main__":
    main(sys.argv[1:])
