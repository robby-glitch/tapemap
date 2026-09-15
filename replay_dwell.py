"""Replay captured chain logs through oi_dwell and score the calls.

    python replay_dwell.py 2026-08-20 2026-08-21 2026-08-24
    python replay_dwell.py --sweep 2026-08-24

Reads data/chain/chain_<IDX>_<day>.jsonl. Scores each durable direction call
by the FAVOURABLE and ADVERSE excursion of spot after it -- the same
MFE/MAE grammar trigger_log already uses, so the two can be read together.
No hit rate, no expectancy: that criterion is the operator's to set
(research-findings 5e), and a rate over this few calls is a number about
noise.
"""
import json
import os
import sys

import oi_dwell

IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")


def load(idx, day):
    p = os.path.join("data", "chain", f"chain_{idx}_{day}.jsonl")
    if not os.path.exists(p):
        return None
    out = []
    for ln in open(p, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        out.append(r)
    return out


def calls(snaps, confirm, min_base, dead):
    g = oi_dwell.Gate(confirm)
    out = []
    for r in snaps:
        d, s, base = oi_dwell.direction(r["strikes"], min_base, dead)
        before = g.held
        after = g.update(d)
        if after != before and after is not None:
            # `before` is oi_dwell._UNSET on the first acquisition; render it
            # as "-" rather than leaking a sentinel's repr into a report.
            before = "-" if before is oi_dwell._UNSET else before
            out.append({"ts": r["ts"], "spot": r["spot"], "from": before,
                        "to": after, "strength": s, "base": base})
    return out


def score(snaps, c):
    after = [r for r in snaps if r["ts"] >= c["ts"]]
    if not after:
        return None
    lo = min(r["spot"] for r in after)
    hi = max(r["spot"] for r in after)
    fav = (c["spot"] - lo) if c["to"] == "BEARISH" else (hi - c["spot"])
    adv = (hi - c["spot"]) if c["to"] == "BEARISH" else (c["spot"] - lo)
    return fav, adv, after[-1]["spot"] - c["spot"]


def report(days, confirm=oi_dwell.CONFIRM, min_base=oi_dwell.MIN_BASE,
           dead=oi_dwell.DEAD):
    tot_calls = tot_fav = tot_adv = 0
    for day in days:
        print(f"\n{'='*72}\n{day}   confirm={confirm} min_base={min_base:,} "
              f"dead={dead}\n{'='*72}")
        for idx in IDXS:
            snaps = load(idx, day)
            if not snaps:
                print(f"  {idx:<10} no chain log")
                continue
            cs = calls(snaps, confirm, min_base, dead)
            head = (f"  {idx:<10} {len(snaps):>5} snapshots  "
                    f"-> {len(cs)} durable call(s)")
            if len(snaps) < 200:
                head += "   [PARTIAL DAY -- read with care]"
            print(head)
            for c in cs:
                sc = score(snaps, c)
                if not sc:
                    continue
                fav, adv, net = sc
                tot_calls += 1
                tot_fav += fav
                tot_adv += adv
                print(f"      {c['ts']}  {str(c['from']):<7} -> {c['to']:<8}"
                      f" @{c['spot']:>9.1f}  s={c['strength']:+.3f}")
                print(f"         favourable {fav:>8.1f}   adverse "
                      f"{adv:>8.1f}   to close {net:>+8.1f}")
    if tot_calls:
        print(f"\n{'-'*72}\n{tot_calls} calls across {len(days)} session(s): "
              f"favourable {tot_fav:,.0f} pts, adverse {tot_adv:,.0f} pts "
              f"(sum of excursions, NOT a P&L and NOT a hit rate)")


def sweep(days):
    print("MIN_BASE sweep -- calls and total excursions per setting\n")
    print(f"{'min_base':>12} {'calls':>6} {'favourable':>12} {'adverse':>10}")
    for mb in (0, 1_000_000, 2_500_000, 5_000_000, 10_000_000, 20_000_000):
        n = f = a = 0
        for day in days:
            for idx in IDXS:
                snaps = load(idx, day)
                if not snaps:
                    continue
                for c in calls(snaps, oi_dwell.CONFIRM, mb, oi_dwell.DEAD):
                    sc = score(snaps, c)
                    if sc:
                        n += 1
                        f += sc[0]
                        a += sc[1]
        print(f"{mb:>12,} {n:>6} {f:>12,.0f} {a:>10,.0f}")


def main(argv):
    if argv and argv[0] == "--sweep":
        return sweep(argv[1:])
    report(argv or ["2026-08-24"])


if __name__ == "__main__":
    main(sys.argv[1:])
