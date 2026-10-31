"""VPIN from first principles (her ask, 31 Oct: "refine vpin completely and check from first principle and what metrics it
uses ... how they interact ... effort vs result ... at support ... absorption, big limit order, trapped traders, aggressive
traders, change in delta, vwap bands and its expansion or contraction, ib range, price discovery"). §1k terms: a look at
the past on her request, counts only, never a rate, no rule; thresholds fixed below BEFORE the first run, never tuned.

Inputs (all read-only): the 1-second NIFTY futures book (data/book/book_NIFTY_<day>.jsonl[.gz]: t ms, ltp, vtt, oi, tbq,
tsq, b / a = 5 levels [price, qty]); the Dext footprint (data/dext, Dhan's own buy / sell per minute: the reference for
"who was the aggressor"); the cached Jarvis frames (VWAP, sigma per minute).

  1. THE INPUT. VPIN signs volume by the TICK rule. Is that who was aggressive? Tick vs QUOTE rule (trade at or above the
     previous best ask = buy, at or below the best bid = sell, inside: tick) vs Dext, per minute.
  2. THE MISSING HALF. VPIN keeps |buy - sell| per 20k bucket and throws away the price move, the time and the sign. Put
     them back: each bucket's effort (fixed volume) vs result (points the aggressor got) -> PUSH / ABSORB / GRIND /
     VACUUM / BALANCE / MIXED, and what the next 15 min did after each.
  3. HER CHECKLIST AT THE BAND. Every first touch of 2 sigma after 09:45: which items were present, and did the touch TURN
     (1 sigma back first) or BREAK (0.5 sigma further first) within 60 min.
"""
import collections
import gzip
import json
import os
import statistics
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, *[".."] * 5))
sys.path.insert(0, ROOT)
import dext_log  # noqa: E402

dext_log.DIR = os.path.join(ROOT, "data", "dext")            # its DIR is relative to the server's cwd

FR = os.path.join(tempfile.gettempdir(), "jarvis_atlas", "frames")
BUCKET = 20_000            # vpin.FAST_BUCKET_V, the fast line her panel shows
ONE, TWO = 0.5, 0.2        # one-sided at |imb| >= 0.5 (fold.ONE_SIDED); two-sided below 0.2
BIG = 0.25                 # a "result" = 0.25U in the bucket (legs.py's NEW_U); U = max(sigma, 0.1 % of price)
NEXT_MIN, MOVE = 15, 0.5   # after a bucket: which comes first in 15 min, +0.5U or -0.5U


def ist_m(t_ms):
    return int(t_ms / 1000 + 19800) % 86400 // 60


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def book(day):
    for p in (f"book_NIFTY_{day}.jsonl", f"book_NIFTY_{day}.jsonl.gz"):
        f = os.path.join(ROOT, "data", "book", p)
        if os.path.exists(f):
            op = gzip.open if f.endswith(".gz") else open
            with op(f, "rt", encoding="utf-8") as h:
                rows = [json.loads(x) for x in h if x.strip()]
            return sorted((r for r in rows if isinstance(r.get("t"), (int, float)) and r.get("ltp")), key=lambda r: r["t"])
    return []


def trades(rows):
    """[(t, m, ltp, dv, tick_sign, quote_sign, row)] -- volume between consecutive rows, signed both ways."""
    out, tick, prev = [], 0, None
    for r in rows:
        if prev is not None:
            if r["ltp"] > prev["ltp"]:
                tick = 1
            elif r["ltp"] < prev["ltp"]:
                tick = -1
            dv = (r.get("vtt") or 0) - (prev.get("vtt") or 0)
            if dv > 0:
                b, a = prev.get("b") or [], prev.get("a") or []
                q = tick
                if a and r["ltp"] >= a[0][0]:
                    q = 1
                elif b and r["ltp"] <= b[0][0]:
                    q = -1
                out.append((r["t"], ist_m(r["t"]), r["ltp"], dv, tick, q, r))
        prev = r
    return out


def dext_minutes(day, ik):
    if not ik:
        return {}
    tag = "NSE-" + ik.split("|")[1]
    out = {}
    for c in dext_log.read_candles(tag, day):
        if c.get("time") and c.get("buy_volume") is not None and c.get("sell_volume") is not None:
            h, m = map(int, c["time"][11:16].split(":"))
            out[h * 60 + m] = (c["buy_volume"], c["sell_volume"])
    return out


days = [os.path.basename(f)[6:16] for f in sorted(os.listdir(FR)) if f.startswith("NIFTY_")]

# ---------------------------------------------------------------- 1. the input
print("== 1. who was the aggressor? per minute, vs Dext (Dhan's footprint) ==")
agree = collections.Counter()
C = {"tick": [], "quote": []}
BK, TR, FRM = {}, {}, {}
for day in days:
    rows = book(day)
    if not rows:
        continue
    T = trades(rows)
    TR[day] = T
    FRM[day] = json.load(open(os.path.join(FR, f"NIFTY_{day}.json"), encoding="utf-8"))
    dx = dext_minutes(day, rows[-1].get("ik"))
    if not dx:
        continue
    agree["days"] += 1
    per = collections.defaultdict(lambda: [0.0, 0.0, 0.0])          # m -> [vol, tick delta, quote delta]
    for t, m, p, dv, s1, s2, _ in T:
        per[m][0] += dv
        per[m][1] += s1 * dv
        per[m][2] += s2 * dv
    for m, (bu, se) in dx.items():
        if m not in per or bu + se <= 0 or not per[m][0]:
            continue
        d_ref = bu - se
        clear = abs(d_ref) >= 0.2 * (bu + se)
        for k, i in (("tick", 1), ("quote", 2)):
            C[k].append((per[m][i] / per[m][0], d_ref / (bu + se)))
            if clear:
                agree[(k, "n")] += 1
                agree[(k, "same")] += (per[m][i] > 0) == (d_ref > 0) and per[m][i] != 0
        agree["vol_n"] += 1
        agree["vol_x100"] += round(100 * per[m][0] / (bu + se))
print(f"  Dext days matched to the book's contract: {agree['days']}")
for k in ("tick", "quote"):
    xs = C[k]
    if len(xs) > 2:
        r = statistics.correlation([a for a, _ in xs], [b for _, b in xs])
        print(f"  {k:<5} rule: minutes {len(xs)} · clear Dext minutes (|delta| >= 20 % of volume) same sign "
              f"{agree[(k, 'same')]} of {agree[(k, 'n')]} · correlation of minute imbalance {r:.2f}")
if agree["vol_n"]:
    print(f"  volume check: book / Dext per minute, mean {agree['vol_x100'] / agree['vol_n']:.0f} %")

# ---------------------------------------------------------------- 2. the missing half
ok = all(len(C[k]) > 2 for k in C)
SIGN = 5 if ok and statistics.correlation(*zip(*C["quote"])) >= statistics.correlation(*zip(*C["tick"])) else 4


def buckets(T, rule):
    out, cur = [], None
    for t, m, p, dv, s1, s2, r in T:
        s = (s1, s2)[rule - 4]
        while dv > 0:
            if cur is None:
                cur = {"t0": t, "p0": p, "buy": 0.0, "sell": 0.0, "oi0": r.get("oi")}
            take = min(dv, BUCKET - cur["buy"] - cur["sell"])
            if s > 0:
                cur["buy"] += take
            elif s < 0:
                cur["sell"] += take
            else:
                cur["buy"] += take / 2
                cur["sell"] += take / 2
            dv -= take
            if cur["buy"] + cur["sell"] >= BUCKET - 1e-6:
                cur.update(t1=t, p1=p, m1=m, oi1=r.get("oi"),
                           bid5=sum(q for _, q in (r.get("b") or [])), ask5=sum(q for _, q in (r.get("a") or [])))
                out.append(cur)
                cur = None
    return out


def state(b, U):
    imb = (b["buy"] - b["sell"]) / BUCKET
    a = 1 if imb > 0 else -1
    dp = b["p1"] - b["p0"]
    if abs(imb) >= ONE:
        r = a * dp
        return ("PUSH" if r >= BIG * U else "ABSORB" if r <= 0 else "GRIND"), a
    if abs(imb) < TWO:
        return ("VACUUM", 1 if dp > 0 else -1) if abs(dp) >= BIG * U else ("BALANCE", 0)
    return "MIXED", a


def at_min(d, m):
    k = hm(m)
    return d["mins"].index(k) if k in d["mins"] else None


for rule in (4, 5):
    NX = collections.defaultdict(collections.Counter)
    mech = []
    for day, T in TR.items():
        d = FRM[day]
        B = buckets(T, rule)
        if rule == SIGN:
            BK[day] = B
        k0 = 0
        for b in B:
            j = at_min(d, b["m1"])
            if j is None or not d["sd"][j] or not ("09:30" <= hm(b["m1"]) < "15:00"):
                continue
            U = max(d["sd"][j], 0.001 * b["p1"])
            mech.append(((b["buy"] - b["sell"]) / BUCKET, (b["p1"] - b["p0"]) / U))
            st, a = state(b, U)
            b["st"], b["a"], b["U"] = st, a, U
            if not a:
                NX[st]["no direction"] += 1
                continue
            while k0 < len(T) and T[k0][0] <= b["t1"]:
                k0 += 1
            out = "neither"
            for t, m, p, *_ in T[k0:]:
                if t - b["t1"] > NEXT_MIN * 60000:
                    break
                if a * (p - b["p1"]) >= MOVE * U:
                    out = "on"
                    break
                if a * (b["p1"] - p) >= MOVE * U:
                    out = "back"
                    break
            NX[st][out] += 1
    json.dump({day: [(int(b["t1"] / 1000 + 19800) % 86400, b["buy"], b["sell"]) for b in buckets(T, rule)]
               for day, T in TR.items()},
              open(os.path.join(tempfile.gettempdir(), "jarvis_atlas", f"buckets_{'tick' if rule == 4 else 'quote'}.json"), "w"))
    print(f"\n== 2. effort vs result per {BUCKET:,} bucket, signed by the {'TICK (live VPIN)' if rule == 4 else 'QUOTE'} rule ==")
    print(f"  how much the bucket's imbalance is just its own price move: correlation {statistics.correlation(*zip(*mech)):.2f}")
    print("  the bucket's word -> next 15 min, in the AGGRESSOR's direction (VACUUM: price's): on = +0.5U first, back = -0.5U first")
    for st in ("PUSH", "GRIND", "ABSORB", "MIXED", "VACUUM", "BALANCE"):
        c = NX[st]
        print(f"  {st:<8} n {sum(c.values()):>5}: " + " · ".join(f"{k} {c[k]}" for k in ("on", "back", "neither", "no direction") if c[k]))
print(f"\n(section 3 uses the {'quote' if SIGN == 5 else 'tick'} rule's buckets: the closer match to Dext in section 1)")
dur = sorted((b["t1"] - b["t0"]) / 1000 for B in BK.values() for b in B)
print(f"  bucket length: median {statistics.median(dur):.0f} s, p10 {dur[len(dur) // 10]:.0f} s, p90 {dur[len(dur) * 9 // 10]:.0f} s"
      f" · buckets {len(dur)} over {len(BK)} days")

# ---------------------------------------------------------------- 3. her checklist at the band
print("\n== 3. her checklist at every first 2-sigma touch after 09:45 (NIFTY fut, 60 min after) ==")
touches = []
for day, d in FRM.items():
    M, fut, vw, sd = d["mins"], d["fut"], d["vwap"], d["sd"]
    armed = {1: True, -1: True}
    for j in range(len(M)):
        if M[j] < "09:45" or M[j] >= "15:00" or not sd[j] or fut[j] is None or vw[j] is None:
            continue
        z = (fut[j] - vw[j]) / sd[j]
        for s in (1, -1):
            if s * z < 1.5:
                armed[s] = True
            if armed[s] and s * z >= 2:
                armed[s] = False
                touches.append((day, j, s))                    # s = +1 a top touch (u2), -1 a bottom touch (d2)
ITEMS = ("1 absorption: outward aggression, no result (>= 1 ABSORB bucket of the last 5)",
         "2 aggressors winning: >= 2 outward PUSH buckets of the last 5",
         "2b urgency: buckets filling in < 0.5x the day's median time",
         "3 big resting limits: holding side's 5-level depth >= 1.5x the other side",
         "4 trapped fuel: fut OI rose in the 15 min into the touch (fresh positions; the pre-set 0.5 % was never met)",
         "5 delta change: 3-min delta against the push after 10 min with it (book delta)",
         "6 bands expanding: sigma now >= 1.2x sigma 30 min ago",
         "7 outside the IB: beyond the 09:15-10:15 high / low (after 10:15)")
rows = []
for day, j, s in touches:
    d, B = FRM[day], BK.get(day, [])
    M, fut, sd = d["mins"], d["fut"], d["sd"]
    m = int(M[j][:2]) * 60 + int(M[j][3:5])
    # HER ZONE's own edges, on the live band (what she sees): back inside 1 sigma first = TURN (the zone worked), 3 sigma
    # first = BREAK (beyond d3 / u3, the zone failed), neither in 60 min = WALK (price lives out on the band: a trend).
    # (The first run used "0.5 sigma further = break", wrong for her setup: entry is anywhere in 2-3 sigma.)
    out = "WALK"
    for k in range(j + 1, min(len(M), j + 61)):
        if None in (d["flo"][k], d["fhi"][k], d["vwap"][k]) or not sd[k]:
            continue
        if s * ((d["fhi"][k] if s > 0 else d["flo"][k]) - d["vwap"][k]) / sd[k] >= 3:
            out = "BREAK"
            break
        if s * ((d["flo"][k] if s > 0 else d["fhi"][k]) - d["vwap"][k]) / sd[k] <= 1:
            out = "TURN"
            break
    last = [b for b in B if b["m1"] <= m and "st" in b][-5:]
    fresh = bool(last) and m - last[-1]["m1"] <= 5                       # the book was live into the touch
    yn = lambda c: "yes" if c else "no"
    v = {}
    if fresh:
        v[ITEMS[0]] = yn(sum(b["st"] == "ABSORB" and b["a"] == s for b in last) >= 1)
        v[ITEMS[1]] = yn(sum(b["st"] == "PUSH" and b["a"] == s for b in last) >= 2)
        med = statistics.median([(b["t1"] - b["t0"]) / 1000 for b in B if b["m1"] <= m])
        v[ITEMS[2]] = yn(statistics.median([(b["t1"] - b["t0"]) / 1000 for b in last]) < 0.5 * med)
        lb = last[-1]
        hold, hit = (lb["bid5"], lb["ask5"]) if s < 0 else (lb["ask5"], lb["bid5"])
        v[ITEMS[3]] = yn(hold >= 1.5 * hit) if hold and hit else None
        oi0 = next((b["oi0"] for b in B if b["m1"] >= m - 15 and b.get("oi0")), None)
        v[ITEMS[4]] = yn(lb["oi1"] > oi0) if oi0 and lb.get("oi1") else None
        dl = collections.Counter()
        for t, mm, p, dv, s1, s2, _ in TR[day]:
            if m - 12 <= mm <= m:
                dl[mm] += (s1, s2)[SIGN - 4] * dv
        d3, d10 = sum(dl[x] for x in range(m - 2, m + 1)), sum(dl[x] for x in range(m - 12, m - 2))
        v[ITEMS[5]] = yn(s * d10 > 0 and s * d3 < 0)
    v[ITEMS[6]] = yn(sd[j] >= 1.2 * sd[j - 30]) if j >= 30 and sd[j - 30] else None
    ib = [k for k, t in enumerate(M) if t < "10:15" and d["fhi"][k] is not None]
    if M[j] >= "10:15" and ib:
        ibh, ibl = max(d["fhi"][k] for k in ib), min(d["flo"][k] for k in ib)
        v[ITEMS[7]] = yn(fut[j] > ibh if s > 0 else fut[j] < ibl)
    rows.append({"day": day, "t": M[j], "side": "top" if s > 0 else "bottom", "out": out, **v})
print(f"touches {len(rows)} · TURN {sum(r['out'] == 'TURN' for r in rows)} · BREAK {sum(r['out'] == 'BREAK' for r in rows)}"
      f" · WALK {sum(r['out'] == 'WALK' for r in rows)} · days {len({r['day'] for r in rows})}")
tb = lambda X: (f"turn {sum(r['out'] == 'TURN' for r in X)} / break {sum(r['out'] == 'BREAK' for r in X)}"
                f" / walk {sum(r['out'] == 'WALK' for r in X)}")
for n in range(0, 6):
    X = [r for r in rows if sum(r.get(k) == "yes" for k in ITEMS) == n]
    if X:
        print(f"  items present {n}: n {len(X)}: {tb(X)}")
for k in ITEMS:
    print(f"  {k}\n      " + " · ".join(f"{v or 'cannot check'} {len(X)}: {tb(X)}" for v in ("yes", "no", None)
                                       for X in [[r for r in rows if r.get(k) == v]] if X))
both = [r for r in rows if r.get(ITEMS[0]) == "yes" and r.get(ITEMS[7]) == "no"]
print(f"  absorption AND inside the IB: n {len(both)}: {tb(both)}")
both = [r for r in rows if r.get(ITEMS[0]) == "yes" and r.get(ITEMS[1]) == "no"]
print(f"  absorption AND aggressors NOT winning: n {len(both)}: {tb(both)}")
disc = [r for r in rows if r.get(ITEMS[7]) == "yes" and r.get(ITEMS[6]) == "yes" and r.get(ITEMS[1]) == "yes"]
print(f"  price discovery set (outside IB + bands expanding + aggressors winning): n {len(disc)}: {tb(disc)}")
json.dump(rows, open(os.path.join(tempfile.gettempdir(), "jarvis_atlas", "touches.json"), "w"), indent=0)
