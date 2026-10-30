"""survey.py -- one line per (index, day) so replay days are picked by KIND, not memory. stdlib only, read-only.

Builds the same minute grid the server builds (last ~10 s snapshot per minute; oi_chg = OI minus the 09:15 open)
and prints: rows, first/last minute, holes (minutes with no row), open, range % of open, close-open %, the number
of times the minute spot crossed its own running session mean (a cheap stand-in for VWAP crosses: §1o is not
re-run here), and the nine-strike net OI change on each side at the close in lakh.

    python survey.py            # all indices, all days
    python survey.py NIFTY      # one index
"""
import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHAIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "data", "chain"))
NEAR = 9


def rows(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("ts") and r.get("spot") is not None and r.get("strikes"):
                yield r


def grid(path):
    """{"HH:MM": {"spot", "atm", "k": {strike: (ce_chg, pe_chg)}, "oi": {strike: (ce_oi, pe_oi)}}}, last row per minute."""
    g = {}
    for r in rows(path):
        m = r["ts"][:5]
        if m < "09:15" or m > "15:30":
            continue
        g[m] = {"spot": float(r["spot"]), "atm": r.get("atm"),
                "k": {int(s["k"]): (float(s["ce"].get("oi_chg") or 0.0), float(s["pe"].get("oi_chg") or 0.0)) for s in r["strikes"]},
                "oi": {int(s["k"]): (float(s["ce"].get("oi") or 0.0), float(s["pe"].get("oi") or 0.0)) for s in r["strikes"]}}
    return g


def mins(hm):
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def nine(ks, spot):
    return sorted(ks, key=lambda k: (abs(k - spot), k))[:NEAR]


def survey(path):
    g = grid(path)
    if not g:
        return None
    ts = sorted(g)
    spots = [g[t]["spot"] for t in ts]
    o, hi, lo, c = spots[0], max(spots), min(spots), spots[-1]
    holes = (mins(ts[-1]) - mins(ts[0]) + 1) - len(ts)
    # running-mean crosses
    run, n, side = 0.0, 0, 0
    x = 0
    for s in spots:
        n += 1
        run += (s - run) / n
        sd = 1 if s > run else -1 if s < run else 0
        if sd and side and sd != side:
            x += 1
        if sd:
            side = sd
    last = g[ts[-1]]
    nk = nine(list(last["k"]), c)
    ce = sum(last["k"][k][0] for k in nk) / 1e5
    pe = sum(last["k"][k][1] for k in nk) / 1e5
    return {"rows": len(ts), "first": ts[0], "last": ts[-1], "holes": holes, "open": o,
            "range_pct": 100 * (hi - lo) / o, "drift_pct": 100 * (c - o) / o, "xmean": x, "ce9L": ce, "pe9L": pe}


def main():
    want = sys.argv[1:] or ["NIFTY", "BANKNIFTY", "SENSEX"]
    for idx in want:
        print(f"== {idx} ==")
        print(f"{'day':<11}{'rows':>5}{'first':>7}{'last':>7}{'holes':>6}{'open':>10}{'rng%':>6}{'drift%':>7}{'xmean':>6}{'CE9 L':>8}{'PE9 L':>8}")
        for p in sorted(glob.glob(os.path.join(CHAIN, f"chain_{idx}_*.jsonl*"))):
            day = os.path.basename(p).split("_")[2][:10]
            s = survey(p)
            if not s:
                print(f"{day:<11} (unreadable)")
                continue
            print(f"{day:<11}{s['rows']:>5}{s['first']:>7}{s['last']:>7}{s['holes']:>6}{s['open']:>10.0f}{s['range_pct']:>6.2f}"
                  f"{s['drift_pct']:>+7.2f}{s['xmean']:>6}{s['ce9L']:>+8.1f}{s['pe9L']:>+8.1f}")


if __name__ == "__main__":
    main()
