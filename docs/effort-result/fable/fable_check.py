"""Fable's independent re-derivation for the EFFORT / RESULT review (31 Oct). Read-only on data/. Counts only, never a
rate. Everything here is in-sample and descriptive. Writes nothing outside docs/effort-result/fable/.

A. the 120 band-signal stalls: the 10-bucket window's span, a pullback during the stall, unique episodes, and a
   "since the extreme" signed read as the alternative to a fixed 10-bucket window.
B. the same shape on a DIFFERENT population: the first pause of every leg (>= 40 pts) on 25 NIFTY days.
C. tick vs quote vs Dext, my own code, plus the share of volume the quote rule hands back to the tick rule.
D. live vpin_fast.jsonl holes per day vs the buckets the book can rebuild.
E. the 77 touches: TURN / BREAK measured against the band FIXED at the touch, not the moving band.
"""
import collections
import contextlib
import gzip
import io
import json
import os
import statistics
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
ATLAS = os.path.join(ROOT, "docs", "kahani", "review", "scripts", "atlas")
sys.path.insert(0, ATLAS)
sys.path.insert(0, ROOT)
with contextlib.redirect_stdout(io.StringIO()):
    import band_turns as bt                     # the atlas's own signal set, so the population is identical
import dext_log                                  # noqa: E402

dext_log.DIR = os.path.join(ROOT, "data", "dext")
JA = os.path.join(tempfile.gettempdir(), "jarvis_atlas")
BUCKET, ONE, LEAD, WIN = 20_000, 0.5, 2, 10
STALL_MIN, NEW_U = 6, 0.25
OUT = open(os.path.join(HERE, "fable_check_out.txt"), "w", encoding="utf-8")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.write(s + "\n")


def ist_s(t_ms):
    return int(t_ms / 1000 + 19800) % 86400


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def book(day, idx="NIFTY"):
    for p in (f"book_{idx}_{day}.jsonl", f"book_{idx}_{day}.jsonl.gz"):
        f = os.path.join(ROOT, "data", "book", p)
        if os.path.exists(f):
            op = gzip.open if f.endswith(".gz") else open
            with op(f, "rt", encoding="utf-8") as h:
                rows = [json.loads(x) for x in h if x.strip()]
            return sorted((r for r in rows if isinstance(r.get("t"), (int, float)) and r.get("ltp")), key=lambda r: r["t"])
    return []


def signed(rows):
    """[(t_s, ltp, dv, tick, quote, inside)] -- my own signing, written without looking at vpin_lab's loop."""
    out, tick, prev = [], 0, None
    for r in rows:
        if prev is not None:
            p, q = r["ltp"], prev["ltp"]
            if p > q:
                tick = 1
            elif p < q:
                tick = -1
            dv = (r.get("vtt") or 0) - (prev.get("vtt") or 0)
            if dv > 0:
                ask = (prev.get("a") or [[None]])[0][0]
                bid = (prev.get("b") or [[None]])[0][0]
                inside = False
                if ask is not None and p >= ask:
                    qs = 1
                elif bid is not None and p <= bid:
                    qs = -1
                else:
                    qs, inside = tick, True
                out.append((ist_s(r["t"]), p, dv, tick, qs, inside, r))
        prev = r
    return out


def buckets(T, rule):
    """fixed 20k buckets: [(t0, t1, p0, p1, buy, sell)]; rule 'tick' | 'quote'."""
    out, cur = [], None
    for t, p, dv, s1, s2, _, r in T:
        s = s1 if rule == "tick" else s2
        while dv > 0:
            if cur is None:
                cur = [t, None, p, None, 0.0, 0.0]
            take = min(dv, BUCKET - cur[4] - cur[5])
            if s > 0:
                cur[4] += take
            elif s < 0:
                cur[5] += take
            else:
                cur[4] += take / 2
                cur[5] += take / 2
            dv -= take
            if cur[4] + cur[5] >= BUCKET - 1e-6:
                cur[1], cur[3] = t, p
                out.append(tuple(cur))
                cur = None
    return out


def lead(B, t_s, s, win=WIN):
    """(chip, n_with, n_against, span_s, n_buckets) of the last `win` buckets closed by t_s, for direction s."""
    b = [x for x in B if x[1] <= t_s][-win:]
    if len(b) < win or t_s - b[-1][1] > 15 * 60:
        return None
    one = [1 if bu > se else -1 for _, _, _, _, bu, se in b if abs(bu - se) / (bu + se) >= ONE]
    nw, na = sum(1 for x in one if x == s), sum(1 for x in one if x == -s)
    net = nw - na
    return ("WITH" if net >= LEAD else "AGAINST" if net <= -LEAD else "QUIET", nw, na, t_s - b[0][0], len(b))


def since(T, rule, t0_s, t1_s, s):
    """signed volume between two clock times, direction s: (net share, volume)."""
    i = 3 if rule == "tick" else 4
    v = sum(x[2] for x in T if t0_s < x[0] <= t1_s)
    d = sum(x[2] * x[i] for x in T if t0_s < x[0] <= t1_s)
    return (s * d / v if v else None), v


# ------------------------------------------------------------------ load every NIFTY book once, sign it, bucket it
days = sorted(f[6:16] for f in os.listdir(os.path.join(JA, "frames")) if f.startswith("NIFTY_"))
TR, BQ, BT, FRM = {}, {}, {}, {}
for day in days:
    rows = book(day)
    if not rows:
        continue
    TR[day] = signed(rows)
    BQ[day] = buckets(TR[day], "quote")
    BT[day] = buckets(TR[day], "tick")
    FRM[day] = json.load(open(os.path.join(JA, "frames", f"NIFTY_{day}.json"), encoding="utf-8"))
P(f"NIFTY days with a book: {len(TR)} · quote buckets {sum(map(len, BQ.values()))} · tick buckets {sum(map(len, BT.values()))}")

# ------------------------------------------------------------------ A. the 120 stalls, re-traced with more fields
P("\n== A. the band-signal stalls (band_turns.py's own signals; 3 indices read NIFTY's buckets) ==")


def retrace(d, close, s, E=None):
    """band_turns.trace, plus: last_new (the minute of the last favourable extreme), the pullback during the stall."""
    M = [bt.m2i(t) for t in d["mins"]]
    c = bt.m2i(close)
    i0 = next((i for i, m in enumerate(M) if m >= c - 1), None)
    if i0 is None or M[i0] > c + 2:
        return None
    E = E if E is not None else d["fut"][i0]
    sd = d["sd"][i0] or None
    if not sd:
        return None
    U = max(sd, 0.001 * E)
    end = next((j for j in range(i0, len(M)) if M[j] - M[i0] > 60 or d["mins"][j] >= "15:20"), len(M) - 1)
    best, last_new, stall = 0.0, M[i0], None
    for j in range(i0 + 1, end + 1):
        fav = s * ((d["fhi"][j] if s > 0 else d["flo"][j]) - E)
        if fav >= best + NEW_U * U or (best == 0 and fav > 0 and fav >= NEW_U * U):
            best, last_new = fav, M[j]
        if stall is None and best > 0 and M[j] - last_new >= STALL_MIN:
            # the pullback from the extreme during the stall minutes (last_new .. j)
            ext = E + s * best
            pb = max(s * (ext - (d["flo"][k] if s > 0 else d["fhi"][k])) for k in range(i0, j + 1) if M[k] >= last_new)
            stall = {"t": d["mins"][j], "m": M[j], "last_new": last_new, "best": best, "pb_U": pb / U, "j": j,
                     "left": 60 - (M[j] - M[i0])}
    if not stall:
        return None
    j = stall["j"]
    more = max(s * ((d["fhi"][k] if s > 0 else d["flo"][k]) - E) for k in range(j, end + 1))
    stall["went_on"] = (more - stall["best"]) >= 0.5 * sd
    return stall


S = []
for r in bt.T:
    d = bt.frame(r["idx"], r["day"])
    s = 1 if r["side"] == "BUY" else -1
    st = retrace(d, r["t"], s, r["E"])
    if st:
        S.append({**r, "s": s, "st": st})
P(f"stalls re-traced: {len(S)} (band_turns has {sum(1 for x in bt.T if x['stall'])})")
same = sum(1 for x in S if x["stall"] and x["st"]["went_on"] == (x["stall"]["went_on"] >= 0.5 * x["sd"]))
P(f"went_on agrees with band_turns on {same} of {len(S)}")

for rule, B in (("quote", BQ), ("tick", BT)):
    P(f"\n-- {rule} rule, 10-bucket lead at the stall minute's close --")
    C = collections.defaultdict(collections.Counter)
    span, nb_sig = collections.defaultdict(list), collections.defaultdict(list)
    ep = collections.defaultdict(set)
    for x in S:
        t_s = (x["st"]["m"] + 1) * 60
        v = lead(B[x["day"]], t_s, x["s"]) if x["day"] in B else None
        chip = v[0] if v else "no read"
        x[f"chip_{rule}"] = chip
        C[chip]["n"] += 1
        C[chip]["on"] += x["st"]["went_on"]
        C[chip]["pullback>=0.25U"] += x["st"]["pb_U"] >= 0.25
        C[chip]["pullback>=0.5U"] += x["st"]["pb_U"] >= 0.5
        C[chip]["left>=30"] += x["st"]["left"] >= 30
        C[chip]["on & left>=30"] += x["st"]["went_on"] and x["st"]["left"] >= 30
        ep[chip].add((x["day"], x["st"]["m"] // 5))          # one episode = same day, same 5-min slot of the stall
        if v:
            span[chip].append(v[3] / 60)
            nb = sum(1 for b in B[x["day"]] if bt.m2i(x["t"]) * 60 <= b[1] <= t_s)
            nb_sig[chip].append(nb)
    for chip in ("WITH", "QUIET", "AGAINST", "no read"):
        c = C[chip]
        if not c["n"]:
            continue
        P(f"  {chip:<8} n {c['n']:>3} · went on {c['on']:>2} · unique episodes (day, 5-min slot) {len(ep[chip]):>2}"
          f" · pullback >= 0.25U during the stall {c['pullback>=0.25U']:>2} · >= 0.5U {c['pullback>=0.5U']:>2}"
          f" · >= 30 min left {c['left>=30']:>2} (went on {c['on & left>=30']})")
        if span[chip]:
            P(f"           window span: median {statistics.median(span[chip]):.0f} min (p10 {sorted(span[chip])[len(span[chip]) // 10]:.0f},"
              f" p90 {sorted(span[chip])[len(span[chip]) * 9 // 10]:.0f}) · buckets closed signal -> stall: median {statistics.median(nb_sig[chip]):.0f}")
    # the split by whether price pulled back during the stall, regardless of the chip
    P("  pullback during the stall (any chip): " + " · ".join(
        f"{lbl} n {len(X)} went on {sum(x['st']['went_on'] for x in X)}" for lbl, X in (
            ("< 0.25U", [x for x in S if x["st"]["pb_U"] < 0.25]), (">= 0.25U", [x for x in S if x["st"]["pb_U"] >= 0.25]))))
    # WITH split by pullback
    for chip in ("WITH", "AGAINST"):
        X = [x for x in S if x[f"chip_{rule}"] == chip]
        P(f"  {chip}: pullback < 0.25U n {sum(1 for x in X if x['st']['pb_U'] < 0.25)} went on "
          f"{sum(1 for x in X if x['st']['pb_U'] < 0.25 and x['st']['went_on'])} · pullback >= 0.25U n "
          f"{sum(1 for x in X if x['st']['pb_U'] >= 0.25)} went on {sum(1 for x in X if x['st']['pb_U'] >= 0.25 and x['st']['went_on'])}")

# the alternative: who hit SINCE the last favourable extreme (clock-anchored on the pause, not a fixed bucket count)
P("\n-- alternative read: signed volume SINCE the last favourable extreme (quote rule), direction = the trade --")
for lbl, lo, hi in (("your side >= +0.2", 0.2, 9), ("flat", -0.2, 0.2), ("other side <= -0.2", -9, -0.2)):
    X = []
    for x in S:
        if x["day"] not in TR:
            continue
        sh, v = since(TR[x["day"]], "quote", x["st"]["last_new"] * 60, (x["st"]["m"] + 1) * 60, x["s"])
        if sh is not None and lo <= sh < hi:
            X.append(x)
    P(f"  {lbl:<20} n {len(X):>3} · went on {sum(x['st']['went_on'] for x in X):>2}"
      f" · unique episodes {len({(x['day'], x['st']['m'] // 5) for x in X})}")

# ------------------------------------------------------------------ B. leg pauses on 25 NIFTY days (a different population)
P("\n== B. the first pause of every leg >= 40 pts (atlas_legs.json), NIFTY, 25 days: the 10-bucket lead in the LEG's direction ==")
legs = json.load(open(os.path.join(JA, "atlas_legs.json"), encoding="utf-8"))
PZ = []
for L in legs:
    day, dr = L["day"], L["dir"]
    d = FRM.get(day)
    if not d or day not in BQ:
        continue
    M = [bt.m2i(t) for t in d["mins"]]
    i0 = d["mins"].index(L["birth"]) if L["birth"] in d["mins"] else None
    if i0 is None or L["birth"] < "09:45" or L["birth"] > "14:30":
        continue
    o = L["origin"]
    ext, last_new, pause = None, None, None
    for j in range(i0, len(M)):
        sd = d["sd"][j] or 0
        U = max(sd, 0.001 * d["fut"][j])
        x = d["fhi"][j] if dr > 0 else d["flo"][j]
        if ext is None or dr * (x - ext) >= NEW_U * U:
            ext, last_new = x, M[j]
        if M[j] - last_new >= STALL_MIN:
            pause = j
            break
    if pause is None or not d["sd"][pause]:
        continue
    j, sd = pause, d["sd"][pause]
    U = max(sd, 0.001 * d["fut"][j])
    end = next((k for k in range(j, len(M)) if M[k] - M[j] > 60 or d["mins"][k] >= "15:20"), len(M) - 1)
    more = max(dr * ((d["fhi"][k] if dr > 0 else d["flo"][k]) - ext) for k in range(j, end + 1))
    back = max(dr * (ext - (d["flo"][k] if dr > 0 else d["fhi"][k])) for k in range(j, end + 1))
    pb = max(dr * (ext - (d["flo"][k] if dr > 0 else d["fhi"][k])) for k in range(i0, j + 1) if M[k] >= last_new)
    v = lead(BQ[day], (M[j] + 1) * 60, dr)
    sh, vol = since(TR[day], "quote", last_new * 60, (M[j] + 1) * 60, dr)
    PZ.append({"day": day, "t": d["mins"][j], "dir": dr, "pts": L["pts"], "chip": v[0] if v else "no read",
               "went_on": more >= 0.5 * sd, "back_1U": back >= U, "pb": pb / U, "since": sh})
P(f"leg pauses: {len(PZ)} on {len({p['day'] for p in PZ})} days")
for chip in ("WITH", "QUIET", "AGAINST", "no read"):
    X = [p for p in PZ if p["chip"] == chip]
    if X:
        P(f"  lead {chip:<8} n {len(X):>3} · went on >= 0.5 sigma {sum(p['went_on'] for p in X):>2}"
          f" · gave back >= 1U {sum(p['back_1U'] for p in X):>2} · pullback >= 0.25U during the pause {sum(p['pb'] >= 0.25 for p in X)}")
P("  since-the-extreme share (quote): " + " · ".join(
    f"{lbl} n {len(X)} on {sum(p['went_on'] for p in X)} back {sum(p['back_1U'] for p in X)}" for lbl, X in (
        ("leg side >= +0.2", [p for p in PZ if p["since"] is not None and p["since"] >= 0.2]),
        ("flat", [p for p in PZ if p["since"] is not None and -0.2 <= p["since"] < 0.2]),
        ("other side <= -0.2", [p for p in PZ if p["since"] is not None and p["since"] < -0.2]))))
P("  by direction: " + " · ".join(f"{'up' if dr > 0 else 'down'} legs: " + ", ".join(
    f"{chip} {sum(1 for p in PZ if p['dir'] == dr and p['chip'] == chip)}/{sum(1 for p in PZ if p['dir'] == dr and p['chip'] == chip and p['went_on'])}"
    for chip in ("WITH", "QUIET", "AGAINST")) for dr in (1, -1)))
P("  (format: n / went on)")

# ------------------------------------------------------------------ C. tick vs quote vs Dext, my own code
P("\n== C. who was the aggressor: tick vs quote vs Dext per minute (my code) ==")
agree, corr = collections.Counter(), {"tick": [], "quote": []}
inside_v, all_v = 0.0, 0.0
mech = {"tick": [], "quote": []}
for day, T in TR.items():
    ik = next((r.get("ik") for _, _, _, _, _, _, r in reversed(T) if r.get("ik")), None)
    if not ik:
        agree["days without ik (skipped)"] += 1
        continue
    tag = "NSE-" + ik.split("|")[1]
    dx = {}
    for c in dext_log.read_candles(tag, day):
        if c.get("time") and c.get("buy_volume") is not None and c.get("sell_volume") is not None:
            h, m = map(int, c["time"][11:16].split(":"))
            dx[h * 60 + m] = (c["buy_volume"], c["sell_volume"])
    if not dx:
        agree["days with ik but no Dext file"] += 1
        continue
    agree["days"] += 1
    per = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
    for t, p, dv, s1, s2, ins, _ in T:
        m = t // 60
        per[m][0] += dv
        per[m][1] += s1 * dv
        per[m][2] += s2 * dv
        all_v += dv
        inside_v += dv if ins else 0
    for m, (bu, se) in dx.items():
        if m not in per or bu + se <= 0:
            continue
        ref = (bu - se) / (bu + se)
        for k, i in (("tick", 1), ("quote", 2)):
            x = per[m][i] / per[m][0]
            corr[k].append((x, ref))
            if abs(ref) >= 0.2:
                agree[(k, "n")] += 1
                agree[(k, "same")] += (x > 0) == (ref > 0) and x != 0
            if abs(ref) >= 0.5:
                agree[(k, "n50")] += 1
                agree[(k, "same50")] += (x > 0) == (ref > 0) and x != 0
    for rule, B in (("tick", BT), ("quote", BQ)):
        sdm = {bt.m2i(t): s for t, s in zip(FRM[day]["mins"], FRM[day]["sd"]) if s}
        for t0, t1, p0, p1, bu, se in B[day]:
            sd = sdm.get(t1 // 60)
            if sd:
                mech[rule].append(((bu - se) / BUCKET, (p1 - p0) / max(sd, 0.001 * p1)))
P(f"  days matched to a Dext file by the book's own ik: {agree['days']} · skipped: no ik {agree['days without ik (skipped)']},"
  f" no Dext {agree['days with ik but no Dext file']}")
for k in ("tick", "quote"):
    xs = corr[k]
    P(f"  {k:<5}: same sign on clear minutes (|Dext delta| >= 20 % of volume) {agree[(k, 'same')]} of {agree[(k, 'n')]}"
      f" · at >= 50 %: {agree[(k, 'same50')]} of {agree[(k, 'n50')]} · corr {statistics.correlation(*zip(*xs)):.2f} (minutes {len(xs)})")
P(f"  volume the quote rule could not place (inside the previous spread -> tick fallback): {inside_v / all_v * 100:.0f} % of all book volume")
for rule in ("tick", "quote"):
    xs = mech[rule]
    P(f"  {rule:<5}: corr(bucket imbalance, the bucket's own price move) {statistics.correlation(*zip(*xs)):.2f} on {len(xs)} buckets")

# ------------------------------------------------------------------ D. the live log's holes
P("\n== D. live vpin_fast.jsonl (NIFTY-FUT:fast) rows per day vs buckets the book rebuilds ==")
live = collections.Counter()
for x in open(os.path.join(ROOT, "data", "vpin_fast.jsonl"), encoding="utf-8"):
    r = json.loads(x)
    if r.get("inst") == "NIFTY-FUT:fast":
        live[r["day"]] += 1
for day in days:
    if day in BT:
        P(f"  {day}: live {live.get(day, 0):>3} · rebuilt (tick) {len(BT[day]):>3} · {'HOLE' if live.get(day, 0) < 0.8 * len(BT[day]) else 'ok'}")

# ------------------------------------------------------------------ E. the 77 touches against FIXED levels
P("\n== E. the 77 first 2-sigma touches: outcome against the band FIXED at the touch (vpin_lab moves the band) ==")
touches = json.load(open(os.path.join(JA, "touches.json"), encoding="utf-8"))
P(f"  vpin_lab touches: {len(touches)} · its words: " + " · ".join(f"{w} {sum(1 for r in touches if r['out'] == w)}" for w in ("TURN", "BREAK", "WALK")))
fixed = collections.Counter()
rows = []
for r in touches:
    d = FRM[r["day"]]
    j = d["mins"].index(r["t"])
    s = 1 if r["side"] == "top" else -1
    sd, vw, px = d["sd"][j], d["vwap"][j], d["fut"][j]
    one, three = vw + s * sd, vw + s * 3 * sd                # the 1-sigma and 3-sigma lines AT the touch
    out = "WALK"
    for k in range(j + 1, min(len(d["mins"]), j + 61)):
        if d["fhi"][k] is None or d["flo"][k] is None:
            continue
        if s * ((d["fhi"][k] if s > 0 else d["flo"][k]) - three) >= 0:
            out = "BREAK"
            break
        if s * ((d["flo"][k] if s > 0 else d["fhi"][k]) - one) <= 0:
            out = "TURN"
            break
    fixed[(r["out"], out)] += 1
    rows.append({**r, "fixed": out, "sd": sd, "early": r["t"] < "10:15"})
P("  moving-band word -> fixed-band word: " + " · ".join(f"{a}->{b} {n}" for (a, b), n in sorted(fixed.items())))
P("  fixed-band words: " + " · ".join(f"{w} {sum(1 for r in rows if r['fixed'] == w)}" for w in ("TURN", "BREAK", "WALK")))
for lbl, X in (("touch before 10:15", [r for r in rows if r["early"]]), ("after 10:15", [r for r in rows if not r["early"]])):
    P(f"  {lbl}: n {len(X)} · sigma at the touch median {statistics.median(r['sd'] for r in X):.0f} pts"
      f" · moving: turn {sum(r['out'] == 'TURN' for r in X)} · fixed: turn {sum(r['fixed'] == 'TURN' for r in X)}"
      f" break {sum(r['fixed'] == 'BREAK' for r in X)} walk {sum(r['fixed'] == 'WALK' for r in X)}")
ITEMS = [k for k in touches[0] if k[0].isdigit()]
for k in ITEMS:
    parts = []
    for v in ("yes", "no"):
        X = [r for r in rows if r.get(k) == v]
        if X:
            parts.append(f"{v} {len(X)}: fixed turn {sum(r['fixed'] == 'TURN' for r in X)} / break {sum(r['fixed'] == 'BREAK' for r in X)}"
                         f" / walk {sum(r['fixed'] == 'WALK' for r in X)}")
    P(f"  {k[:60]:<60} " + " · ".join(parts))
OUT.close()
