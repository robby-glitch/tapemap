"""Score the SLOW VPIN line on the terms of docs/live/VPIN-KILL-CONDITION-DRAFT.md (25 Oct, unsigned), applied AS WRITTEN
to the sessions already logged (her ask, 31 Oct: "Yes, score VPIN"). A look-back, not the registered verdict: the draft
says nothing counts until she signs and the clock starts forward. Counts only; the bar's own arithmetic, never a rate.

Draft terms: alarm = bucket pct >= 0.90, the first after >= 15 min with none, at 09:45-14:30 · window = the 30 min after
(the 30 one-minute bars from the minute after the bucket's `at` [I]) · expansion = window high - low >= 1.5x the median of
the same clock slot over the prior 20 sessions · base = blocks 09:45, 10:15 ... 14:15, same test · session = VPIN rows
covering 10:00 -> 14:30.
Bars: data/backtest/fut_<day>.json (NIFTY fut 1-min; the draft names data/backtest/NIFTY/, which does not exist), else the
1-second book's minute high / low (data/book, 22 Sep on). "Prior 20 sessions" = the 20 latest earlier sessions WITH bars [I].
--spot: the same test on the chain recorder's NIFTY spot (~15 s samples) for every session, a coverage check only.
"""
import collections
import gzip
import json
import os
import statistics
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SPOT = "--spot" in sys.argv
D = lambda *p: os.path.join(ROOT, "data", *p)


def m_of(hms):
    return int(hms[:2]) * 60 + int(hms[3:5])


def bars_fut(day):
    """{minute: (high, low)} for NIFTY fut, or {}."""
    f = D("backtest", f"fut_{day}.json")
    if os.path.exists(f):
        b = json.load(open(f, encoding="utf-8"))
        return {int(t + 19800) % 86400 // 60: (h, l) for t, h, l in zip(b["timestamp"], b["high"], b["low"])
                if h is not None and l is not None}
    for p in (D("book", f"book_NIFTY_{day}.jsonl"), D("book", f"book_NIFTY_{day}.jsonl.gz")):
        if os.path.exists(p):
            op = gzip.open if p.endswith(".gz") else open
            out = {}
            with op(p, "rt", encoding="utf-8") as h:
                for x in h:
                    r = json.loads(x)
                    if isinstance(r.get("t"), (int, float)) and r.get("ltp"):
                        m = int(r["t"] / 1000 + 19800) % 86400 // 60
                        hi, lo = out.get(m, (r["ltp"], r["ltp"]))
                        out[m] = (max(hi, r["ltp"]), min(lo, r["ltp"]))
            return out
    return {}


def bars_spot(day):
    p = D("chain", f"chain_NIFTY_{day}.jsonl.gz")
    if not os.path.exists(p):
        p = p[:-3]
        if not os.path.exists(p):
            return {}
    op = gzip.open if p.endswith(".gz") else open
    out = {}
    with op(p, "rt", encoding="utf-8") as h:
        for x in h:
            r = json.loads(x)
            if r.get("spot") and r.get("ts"):
                m = m_of(r["ts"])
                hi, lo = out.get(m, (r["spot"], r["spot"]))
                out[m] = (max(hi, r["spot"]), min(lo, r["spot"]))
    return out


bars = bars_spot if SPOT else bars_fut


def rng(B, m0):
    w = [B[m] for m in range(m0, m0 + 30) if m in B]
    return max(h for h, _ in w) - min(l for _, l in w) if len(w) >= 25 else None    # 25 of 30 minutes, else no read [I]


# --- the VPIN sessions and their alarms
by = collections.defaultdict(list)
for x in open(D("vpin_log.jsonl"), encoding="utf-8"):
    if x.strip():
        r = json.loads(x)
        if r.get("inst") == "NIFTY-FUT" and not r.get("backfill"):
            by[r["day"]].append(r)
sessions, skipped = [], []
for day in sorted(by):
    R = by[day]
    a, z = m_of(R[0]["at"]), m_of(R[-1]["at"])
    (sessions if a <= 600 and z >= 870 else skipped).append(day)

# every day that has bars, for the prior-20 medians (sessions or not: a median of the market, not of VPIN)
cands = sorted({f[4:14] for f in os.listdir(D("backtest")) if f.startswith("fut_") and f.endswith(".json")} |
               {f[11:21] for f in os.listdir(D("book")) if f.startswith("book_NIFTY_")} |
               ({f[12:22] for f in os.listdir(D("chain")) if f.startswith("chain_NIFTY_")} if SPOT else set()))
BAR = {}


def B_of(day):
    if day not in BAR:
        BAR[day] = bars(day)
    return BAR[day]


def threshold(day, m0):
    prior = [d for d in cands if d < day and B_of(d)][-20:]
    xs = [x for x in (rng(B_of(d), m0) for d in prior) if x is not None]
    return (1.5 * statistics.median(xs), len(xs)) if len(xs) >= 10 else (None, len(xs))


al_n = al_x = base_n = base_x = 0
rows, nobars = [], []
for day in sessions:
    B = B_of(day)
    if not B:
        nobars.append(day)
        continue
    last_hot, alarms = None, []
    for r in by[day]:
        if (r.get("pct") or 0) >= 0.90:
            t = m_of(r["at"]) + int(r["at"][6:8]) / 60
            if (last_hot is None or t - last_hot >= 15) and 585 <= t <= 870:
                alarms.append((r["at"], int(t) + 1))
            last_hot = t
    for at, m0 in alarms:
        x, (th, n) = rng(B, m0), threshold(day, m0)
        if x is None or th is None:
            rows.append((day, at, None, None, n))
            continue
        al_n += 1
        al_x += x >= th
        rows.append((day, at, round(x, 1), round(th, 1), n))
    for m0 in range(585, 870, 30):                                  # 09:45, 10:15 ... 14:15
        x, (th, _) = rng(B, m0), threshold(day, m0)
        if x is not None and th is not None:
            base_n += 1
            base_x += x >= th

src = "NIFTY SPOT (chain, ~15 s) -- coverage check, not the draft's input" if SPOT else "NIFTY FUT 1-min (the draft's input)"
print(f"== the slow VPIN line on the draft's terms · bars: {src} ==")
print(f"sessions logged {len(by)} · covering 10:00-14:30 {len(sessions)} · skipped (late start / early end) {len(skipped)}: {' '.join(skipped)}")
print(f"counted sessions with no bars on disk {len(nobars)}: {' '.join(nobars)}")
print(f"scored sessions {len(sessions) - len(nobars)}")
print(f"alarms scored {al_n} · their 30-min windows that expanded {al_x}")
print(f"base blocks {base_n} · expanded {base_x}")
exp = al_n * base_x / base_n if base_n else None
if exp is not None:
    print(f"base-expected expanded alarms = {al_n} x {base_x} / {base_n} = {exp:.1f} · KEEP needs >= {exp + 5:.1f} and >= 15 alarms")
    verdict = ("KILL (< 15 alarms)" if al_n < 15 else "KEEP" if al_x >= exp + 5 else "KILL" if al_x <= exp else "EXTEND once")
    print(f"the draft's bar reads: {verdict}")
print("\nalarms (day, bucket at, window range, 1.5x prior median, prior sessions in the median):")
for r in rows:
    print("  " + " · ".join("-" if v is None else str(v) for v in r))
