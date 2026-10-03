"""analyze7.py -- reads replays_*.json (replay7.py's output) and prints the 7-review tables. Pure; no tapemap I/O."""
import bisect
import glob
import json
import os
import sys

HERE = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
R, ZSKIP = [], []
for p in sorted(glob.glob(os.path.join(HERE, "replays_*.json"))):
    js = json.load(open(p, encoding="utf-8"))
    R += js["res"]
    ZSKIP += js["zskip"]
ORDER = {"marked": 0, "design": 1, "zone": 2}
R.sort(key=lambda r: (ORDER[r["kind"]], r["day"], r["entry"]))
DAY0 = {}


def ms_of(day, hhmm):
    import datetime
    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    y, m, d = map(int, day.split("-"))
    h, mi, *x = map(int, hhmm.split(":"))
    return int(datetime.datetime(y, m, d, h, mi, x[0] if x else 0, tzinfo=IST).timestamp() * 1000)


def hm(day, t):
    import datetime
    IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    return datetime.datetime.fromtimestamp(t / 1000, IST).strftime("%H:%M")


def pct(r, p, p0=None, own=None):
    p0 = r["p0"] if p0 is None else p0
    own = r["own"] if own is None else own
    return None if p is None else round(100 * own * (p - p0) / p0)


def at(path, t):
    i = bisect.bisect_right([x[0] for x in path], t) - 1
    return path[i][1] if i >= 0 else None


def extremes(r, path, t0, t1=None, own=None):
    own = r["own"] if own is None else own
    seg = [x for x in path if x[0] >= t0 and (t1 is None or x[0] <= t1)]
    if not seg:
        return None, None
    lo = min(seg, key=lambda x: own * x[1])
    hi = max(seg, key=lambda x: own * x[1])
    return lo, hi


def after(r, t, path=None, p0=None, own=None):
    """premium story after time t: pct then, worst after (pct, hh:mm), best after, +20, +40, 15:00"""
    path = r["path"] if path is None else path
    if t is None or not path:
        return None
    lo, hi = extremes(r, path, t, own=own)
    f = lambda p: pct(r, p, p0, own)  # noqa: E731
    return dict(now=f(at(path, t)), lo=(f(lo[1]), hm(r["day"], lo[0])), hi=(f(hi[1]), hm(r["day"], hi[0])),
                p20=f(at(path, t + 20 * 60000)), p40=f(at(path, t + 40 * 60000)), end=f(path[-1][1]))


def first(evs, cond):
    for e in evs:
        if cond(e):
            return e
    return None


def nag(ch):
    return sum(1 for v in ch.values() if v == "AGAINST")


def against_px(e):
    return e["E"] is not None and e["fut"] is not None and e["w"] is not None and \
        (1 if e["d"] > 0 else -1) * (e["fut"] - e["E"]) <= -e["w"]


def candidates(r):
    d = r["d"]
    evs = []
    for e in r["events"]:
        e = dict(e, d=d)
        if e["ts"] > "15:00:00":
            break
        evs.append(e)
    f6 = first(evs, lambda e: e["kind"] == "fold")
    t6 = f6["t"] if f6 else None
    pre = [e for e in evs if t6 is None or e["t"] <= t6]
    oi_ok = lambda e: e["oi_ev"] and e["chips"].get("O") != "CAN'T CHECK"  # noqa: E731
    c1 = first(pre, lambda e: e["mode"] == "at entry" and oi_ok(e) and against_px(e))
    c4 = first(pre, lambda e: e["mode"] == "at entry" and oi_ok(e) and against_px(e)
               and ("AGAINST" in (e["chips"].get("F"), e["chips"].get("V"))))
    c2 = first(pre, lambda e: (e["head"] or "").startswith("HOLD") and nag(e["chips"]) >= 2 and against_px(e))
    out = dict(rev6=f6, i=c1, ii=c2, iv=c4)
    for vn in ("capG", "nostep"):
        ve = [e for e in r["variants"][vn]["events"] if e["ts"] <= "15:00:00"]
        out[vn] = first(ve, lambda e: e["kind"] == "fold")
        out[vn + "_seedG"] = next((e["G"] for e in ve if e["kind"] in ("seed",) and e["G"] is not None), None)
    return out


def spells_at_risk(r):
    """(ii) on the minute rows: spells of HOLD + >=2 AGAINST + future against her by >= w."""
    n, mins, on = 0, 0, False
    for s in r["snaps"]:
        if s["t"] > "15:00":
            break
        c = s["head"].startswith("HOLD") and sum(1 for k in "ZFOV" if s[k] == "AGAINST") >= 2 and s["dE"] is not None and s["w"] and s["dE"] <= -s["w"]
        if c:
            mins += 1
            if not on:
                n += 1
        on = c
    return n, mins


if __name__ == "__main__":
    for r in R:
        c = candidates(r)
        e6 = c["rev6"]
        lo, hi = extremes(r, r["path"], r["path"][0][0]) if r["path"] else (None, None)
        s0 = r["snaps"][0] if r["snaps"] else {}
        print(f"\n## {r['name']} [{r['kind']}] {r['day']} {'long' if r['own'] > 0 else 'short'} {r['k']}{r['ty']} @ {r['p0']} {r['entry']} E={r['E']} exit={r['exit_t']}")
        print(f"   seed G {s0.get('G')} ({s0.get('dG')} pts) atG engine {s0.get('atG_engine')} true {s0.get('atG_true')} ({pct(r, s0.get('atG_true'))}%) bas {s0.get('bas')} w {s0.get('w')}")
        print(f"   low {pct(r, lo[1])}% {hm(r['day'], lo[0])}  high {pct(r, hi[1])}% {hm(r['day'], hi[0])}  15:00 {pct(r, r['path'][-1][1])}%")
        if r["exit_t"]:
            te = ms_of(r["day"], r["exit_t"])
            print(f"   HER EXIT {r['exit_t']}: {after(r, te)}")
        for key in ("rev6", "i", "iv", "ii", "capG", "nostep"):
            e = c[key]
            print(f"   {key:6} " + (f"{e['ts']} {e['kind']} {e['text'][:70]!r} | {after(r, e['t'])}" if e else "none"))
        print(f"   at-risk spells/min {spells_at_risk(r)}; capG seed G {c['capG_seedG']}")
    print("ZSKIP", ZSKIP)
