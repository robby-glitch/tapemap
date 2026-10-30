"""hs_check.py -- the handshake's data truth and its definitions on every day with flow. Read-only on data/. Rows, not rates.

A. sources: Dext (last row per minute, all NIFTY contracts summed), GoCharting 5-min, Upstox 5-min, and a 1-min delta
   rebuilt from the Upstox 1-second book by the quote rule (trade at/above the ask = buy, at/below the bid = sell, else by
   tick) -- per day: 5-min sign agreement counts D/G/U, D vs book per-minute sign counts and median |difference|.
B. pushes and answers per day under two attacked-strike rules: today's build (the mockup) and absolute OI.
C. the handshake status in the 10 min before every ≠ READ / chop-se-bahar minute of the final replay, right and wrong.

    python hs_check.py
"""
import glob
import json
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "data"))
sys.path[:0] = [os.path.normpath(os.path.join(HERE, "..", "..", "coil")), os.path.normpath(os.path.join(HERE, "..", "..", "final"))]
import coil_scan as C   # noqa: E402

LOT = 65
NORM, PUSH_X, MIN_PUSH, ANSWER, QUIET, CUT_L, CUT_FRAC = 30, 2.0, 150, 4, 4, 3.0, 0.04


def hm(m):
    return "%02d:%02d" % divmod(m, 60)


def dext(day):
    """{minute: lots} -- the LAST row per minute (rows are re-written as the bar fills), every NIFTY contract summed."""
    out = {}
    near = "NSE-2885" if day <= "2026-09-30" else "NSE-48704"       # the near month: GoCharting's NIFTY-I and Upstox's key
    for p in glob.glob(os.path.join(DATA, "dext", f"dext_{near}_{day}.jsonl")):
        last = {}
        for line in open(p, encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            m = int(r["time"][11:13]) * 60 + int(r["time"][14:16])
            if m not in last or (r.get("total_volume") or 0) >= (last[m].get("total_volume") or 0):
                last[m] = r
        for m, r in last.items():
            out[m] = out.get(m, 0) + r["delta"] / LOT
    return out


def bars5(path):
    out = {}
    for line in open(path, encoding="utf-8") if os.path.exists(path) else ():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        m = int((r["t"] / 1000 + 19800) % 86400 // 60)
        if r.get("delta") is not None:
            out[m] = (r["delta"], r.get("oi"), r.get("vol"))
    return out


def book_delta(day):
    """{minute: (delta lots, vol lots, high, low, oi)} from the 1-second book by the quote rule."""
    p = os.path.join(DATA, "book", f"book_NIFTY_{day}.jsonl")
    import gzip
    f = open(p, encoding="utf-8") if os.path.exists(p) else gzip.open(p + ".gz", "rt", encoding="utf-8") if os.path.exists(p + ".gz") else None
    if f is None:
        return {}
    out, prev = {}, None
    with f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("ltp") is None or not r.get("b") or not r.get("a") or not isinstance(r.get("t"), (int, float)):
                continue
            m = int(r["t"] / 1000 + 19800) % 86400 // 60
            cell = out.setdefault(m, [0.0, 0.0, r["ltp"], r["ltp"], r.get("oi")])
            cell[2], cell[3], cell[4] = max(cell[2], r["ltp"]), min(cell[3], r["ltp"]), r.get("oi")
            if prev is not None:
                v = (r.get("vtt") or 0) - (prev.get("vtt") or 0)
                if v > 0:
                    bid = prev["b"][0]["p"] if isinstance(prev["b"][0], dict) else prev["b"][0][0]
                    ask = prev["a"][0]["p"] if isinstance(prev["a"][0], dict) else prev["a"][0][0]
                    sgn = 1 if r["ltp"] >= ask else -1 if r["ltp"] <= bid else (1 if r["ltp"] > prev["ltp"] else -1 if r["ltp"] < prev["ltp"] else 0)
                    cell[0] += sgn * v / LOT
                    cell[1] += v / LOT
            prev = r
    return {m: tuple(v) for m, v in out.items()}


def sign_counts(a, b):
    same = opp = 0
    for k in a:
        if k in b and a[k] and b[k]:
            if (a[k] > 0) == (b[k] > 0):
                same += 1
            else:
                opp += 1
    return same, opp


def pushes(day, R, D, absolute):
    ms = sorted(m for m in R if 555 <= m <= 930)
    sp = {m: R[m]["spot"] for m in ms}
    ks = sorted({s["k"] for s in R[ms[-1]]["strikes"]})
    step = min(b - a for a, b in zip(ks, ks[1:]))

    def d2(m):
        a, b = D.get(m - 1), D.get(m)
        return None if a is None or b is None else a + b

    def oi(r, k, side, abs_):
        g = C.leg_of(r, k, side)
        return g.get("oi") if abs_ else g.get("oi_chg")
    out, last = [], {1: -99, -1: -99}
    for m in ms:
        x = d2(m)
        hist = [abs(d2(j)) for j in range(m - NORM, m) if d2(j) is not None]
        if x is None or len(hist) < 10:
            continue
        norm = st.median(hist)
        sgn = 1 if x > 0 else -1
        if abs(x) < max(MIN_PUSH, PUSH_X * norm) or m - last[sgn] < QUIET:
            continue
        last[sgn] = m
        r0, s0 = R[m], sp[m]
        side = "ce" if sgn > 0 else "pe"
        band = [k for k in ks if (s0 - step / 2 <= k <= s0 + 2 * step if sgn > 0 else s0 - 2 * step <= k <= s0 + step / 2)]
        att = max(band, key=lambda k: oi(r0, k, side, absolute) or 0) if band else None
        ev = {"m": m, "dir": sgn, "lots": round(x), "norm": round(norm), "k": att, "ans": "?", "print": abs(x) >= 10 * norm}
        m4 = next((j for j in ms if j >= m + ANSWER), None)
        if att is not None and m4 is not None:
            o0, o4 = oi(r0, att, side, False), oi(R[m4], att, side, False)
            base = oi(r0, att, side, True) if absolute else o0
            if None not in (o0, o4, base):
                chg = (o4 - o0) / 1e5
                bar = max(CUT_L, CUT_FRAC * max(base, 0) / 1e5)
                through = sgn * (sp[m4] - s0) >= 0.3 * step
                ev["chg"] = round(chg, 1)
                ev["ans"] = "TOOT" if chg <= -bar else "PHANS" if chg >= bar and through else "TIKI" if chg >= bar else "NAHI"
                ev["moved"] = round(sgn * (sp[m4] - s0))
                # the fut's next 15 / 30 min along the push (points): did the push go anywhere?
                for w in (15, 30):
                    mw = next((j for j in ms if j >= m + w), None)
                    ev[f"p{w}"] = None if mw is None else round(sgn * (sp[mw] - s0))
        out.append(ev)
    return out, step


def main():
    days = sorted({f[-16:-6] for f in os.listdir(os.path.join(DATA, "dext")) if f.startswith("dext_NSE") and "ohlc" not in f})
    print("A. SOURCES per day: 5-min sign counts (same/opp) Dext~GoC, Dext~Upx, GoC~Upx · Dext vs book per-minute same/opp · median |D-book| lots · book minutes")
    sumtab = {}
    for day in days:
        D = dext(day)
        G = bars5(os.path.join(DATA, "tape", f"tape_NIFTY_{day}.jsonl"))
        U = bars5(os.path.join(DATA, "tape", f"ux_NIFTY_{day}.jsonl"))
        D5 = {}
        for m, v in D.items():
            s = m - ((m - 555) % 5)
            if all(j in D for j in range(s, s + 5)):
                D5[s] = sum(D[j] for j in range(s, s + 5))
        g = {m: v[0] for m, v in G.items()}
        u = {m: v[0] for m, v in U.items()}
        dg, du, gu = sign_counts(D5, g), sign_counts(D5, u), sign_counts(g, u)
        B = book_delta(day)
        b1 = {m: v[0] for m, v in B.items() if v[1] > 0}
        db = sign_counts(D, b1)
        diffs = [abs(D[m] - b1[m]) for m in D if m in b1]
        med = round(st.median(diffs)) if diffs else None
        print(f"  {day}  D~G {dg[0]:>3}/{dg[1]:<3} D~U {du[0]:>3}/{du[1]:<3} G~U {gu[0]:>3}/{gu[1]:<3} | D~book {db[0]:>3}/{db[1]:<3} med|diff| {str(med):>4} lots | book min {len(b1):>3} | Dext min {len(D):>3}")
        sumtab[day] = (D, B)
    print("\nB. PUSHES per day (Dext summed contracts): n pushes · answers TOOT/PHANS/TIKI/NAHI · prints · mean pts +15 along the push for answered vs NAHI")
    print("   build-attacked | absolute-OI-attacked")
    gate_rows = []
    for day in days:
        try:
            R = C.minutes(day)
        except FileNotFoundError:
            continue
        if not R:
            continue
        D = sumtab[day][0]
        line = f"  {day}"
        for absolute in (False, True):
            ev, step = pushes(day, R, D, absolute)
            cnt = {k: sum(1 for e in ev if e["ans"] == k) for k in ("TOOT", "PHANS", "TIKI", "NAHI", "?")}
            prints = sum(1 for e in ev if e["print"])
            def mean(xs):
                xs = [x for x in xs if x is not None]
                return None if not xs else round(sum(xs) / len(xs))
            yes = mean([e.get("p15") for e in ev if e["ans"] in ("TOOT", "PHANS")])
            no = mean([e.get("p15") for e in ev if e["ans"] == "NAHI"])
            line += f" | n {len(ev):>2} T{cnt['TOOT']} P{cnt['PHANS']} K{cnt['TIKI']} N{cnt['NAHI']} ?{cnt['?']} ★{prints} +15: ans {str(yes):>4} nahi {str(no):>4}"
            if absolute:
                gate_rows.append((day, ev))
        print(line)
    print("\nC. the handshake in the 10 min before each ≠ READ / chop-se-bahar minute of the final replay (NIFTY), absolute-OI rule")
    stamps = []
    for p in sorted(glob.glob(os.path.normpath(os.path.join(HERE, "..", "..", "final", "replay", "NIFTY_*.txt")))):
        day = os.path.basename(p)[6:16]
        for line in open(p, encoding="utf-8"):
            mt = re.match(r"^(\d\d:\d\d)\s+(\d+)s\s+(.*)$", line.strip())
            if mt and ("≠ READ" in mt.group(3) or "chop se bahar" in mt.group(3)):
                stamps.append((day, mt.group(1), mt.group(3)[:60]))
    # the review's killed lines too, for the contrast
    stamps += [("2026-10-22", "11:16", "killed: ≠ ▲ (−130 in 30)"), ("2026-10-22", "12:21", "killed: ≠ ▼ (+48 against)"),
               ("2026-10-26", "13:50", "killed: ≠ ▲ ATKA minute"), ("2026-10-26", "14:09", "killed: ≠ ▲ (−33/−24)"),
               ("2026-10-27", "13:22", "killed: ≠ ▼ (0/−8)"), ("2026-10-27", "10:21", "killed: ≠ ▼ expiry (−36/−59)"),
               ("2026-10-23", "14:45", "killed: ≠ ▼ (−30/−30)")]
    evs = dict(gate_rows)
    for day, t, what in stamps:
        m = int(t[:2]) * 60 + int(t[3:5])
        ev = [e for e in evs.get(day, []) if m - 10 <= e["m"] <= m]
        desc = ", ".join(f"{hm(e['m'])} {'▲' if e['dir'] > 0 else '▼'}{e['lots']} {e['ans']}{'' if e.get('chg') is None else ' ' + ('%+.1f' % e['chg']) + 'L'}" for e in ev) or "no push in 10 min"
        print(f"  {day} {t}  {what:<34} | {desc}")


if __name__ == "__main__":
    main()
