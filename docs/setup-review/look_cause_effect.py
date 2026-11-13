"""look_cause_effect.py -- a read-only look, 13 Nov 2026 (NOTEPAD A302, A303).

Her order: "think from first principle basis what is cause and what is effect ... what piece of data can we used
before the trade what can be used during the trade what can be used to hold the trade aur target we can aim for".

v2 (her "Yes, run it"): every session with a saved day frame (22 Sep -> 12 Nov), one day at a time. Her zone is REPLAYED
on her 3-min bands for every day by the machine's own loop (band_rotation.run_states), so the days before 28 Oct, which
the trigger log does not hold on those bands, are read the same way. Added: the footprint marks at the band
(ofd_marks2, 21 Oct on) and a day read made from what could be known at the trigger. Every claim is shown on the days it
was FOUND on (28 Oct -> 12 Nov, the first look) beside the days it was not (FRESH).

Part A  every 3-min bar: does X go with price in the SAME bar, lead it, or follow it?
Part B  every zone trigger, walked with HER stop (beyond the setup's extreme) to 15:00: the day, the band, the trigger,
        the first 9 minutes (only trades still alive, against what came AFTER), the hold, the end.

  python -X utf8 docs/setup-review/look_cause_effect.py              the look
  python -X utf8 docs/setup-review/look_cause_effect.py --rows       + one line per trigger
  python -X utf8 docs/setup-review/look_cause_effect.py --build DAY  build that day's frame offline into
        docs/jarvis-panel/scratch, exactly as build_jarvis3.get_frame's offline branch does. Refuses under 600 MB free.

The look reads the frames, data/trigger_log.jsonl (to check the replay) and data/tape/ofd_marks2_NIFTY_<day>.jsonl, and
writes nothing. Counts, points and correlations only; no rates.
"""
import glob
import json
import math
import os
import statistics as st
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
SCRATCH = os.path.join(ROOT, "docs", "jarvis-panel", "scratch")
import band_rotation as br  # noqa: E402   the zone machine
import ruler  # noqa: E402   her 3-min bands (the ZONE-3M recurrence)
import tape_log  # noqa: E402   the extension's marks

FOUND_FROM = "2026-10-28"                 # the first look's days; everything before is fresh to tonight's claims
OPEN, LAST = 9 * 60 + 15, 15 * 60        # flat by 15:00 (her practice)
REFUSED, BROKE = ("NAHI", "TIKI"), ("TOOT", "PHANS")
LOCK_R = 2.0                              # the second way to say "it worked": 2x her risk (hold2.LOCK_R, §1m)
TURN_S = 2.0                              # the first: 2 of her sigmas from the entry (a VWAP trip's worth from the band)
ONEWAY_CLOSES, ONEWAY_TOUCH = 96 / 115, 4  # hindsight day label: the weakest of the four days LOOK §7 named [M]
HER_MARKS = ("exhaustion", "absorption")  # decode.ZONE_MARKS, her piece 2
TURN_MARKS = HER_MARKS + ("trap", "climax", "E3", "E6")
GO_MARKS = ("initiative", "E2", "E4")


def M(t):
    return int(t[:2]) * 60 + int(t[3:5])


def HM(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def f(x, w=0, p=1):
    return " " * max(w - 1, 0) + "-" if x is None else f"{x:{w}.{p}f}"


def cnt(xs, test):
    return f"{sum(1 for x in xs if x is not None and test(x))} of {sum(x is not None for x in xs)}"


# ---------------------------------------------------------------- frames

def free_mb():
    import ctypes

    class MS(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
            (n, ctypes.c_ulonglong) for n in ("ullTotalPhys", "ullAvailPhys", "ullTotalPageFile", "ullAvailPageFile",
                                              "ullTotalVirtual", "ullAvailVirtual", "ullAvailExtendedVirtual")]
    ms = MS()
    ms.dwLength = ctypes.sizeof(MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
    return ms.ullAvailPhys / 1e6


def build_frame(day, idx="NIFTY"):
    """One day's Jarvis frame, built offline (no server), saved where build_jarvis3.get_frame keeps its copies."""
    import ctypes
    path = os.path.join(SCRATCH, f"frame_{idx}_{day}.json")
    if os.path.exists(path):
        print(f"{day}: already saved")
        return 0
    if free_mb() < 600:
        print(f"{day}: REFUSED, {free_mb():.0f} MB free (needs 600)")
        return 3
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)   # below normal
    t0 = time.time()
    import jarvis
    d = dict(jarvis.build(day, idx, None, True), live=False, asof=time.strftime("%H:%M:%S"))
    if d.get("ok"):
        d["calls"] = jarvis.calls(d)
        if d.get("mins") and d.get("call") is not None:
            d["call"]["xstate"] = {"t": d["mins"][-1], "sync": None, "day": None, "alert": None,
                                   "why": ["cross: not read — a replay builds one index"]}
    if not (d.get("ok") and len(d.get("mins") or []) >= 300):
        print(f"{day}: no frame ({d.get('why') or len(d.get('mins') or [])} minutes) · {time.time() - t0:.0f}s")
        return 1
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(json.loads(json.dumps(d, default=str)), fh, separators=(",", ":"))
    src = {}
    for s in d.get("flow_src") or []:
        src[s] = src.get(s, 0) + 1
    print(f"{day}: saved · {len(d['mins'])} minutes · flow source {src} · ladder minutes {len(d.get('ladder') or {})}"
          f" · {time.time() - t0:.0f}s · {free_mb():.0f} MB free after")
    return 0


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    if len(d.get("mins") or []) < 300:
        return None
    d["ix"] = {t: i for i, t in enumerate(d["mins"])}
    # The exchange's 1-min futures candles, the ones her zone machine itself reads (ruler.ones_of). The frame's own candles
    # are not usable on the older days (no volume before 30 Sep, book-built through 26 Oct), so bands, replay and the price
    # walk all take the exchange's. A day without them has no Part B.
    ex = [b for b in ruler.ones_of(d["day"]) if b.get("c") is not None]
    d["exch"] = len(ex) >= 300
    if d["exch"]:
        for b in ex:
            i = d["ix"].get(b["t"])
            if i is not None:
                d["fo"][i], d["fhi"][i], d["flo"][i], d["fut"][i], d["fvol"][i] = b["o"], b["h"], b["l"], b["c"], b["v"]
    d["blist"] = ruler.bands(ex, 3) if d["exch"] else []
    d["bars"] = {b["t"]: b for b in d["blist"]}
    fs = d.get("flow_src") or []
    d["dext"] = (sum(1 for s in fs if s == "D") / len(fs)) if fs else 0.0          # share of minutes whose delta is Dext's
    return d


def oi_chg(d, ta, tb, side, strikes=None):
    """Option OI change ta -> tb in lakh, summed over the strikes readable at both minutes; None if none."""
    A, B = d["ladder"].get(ta), d["ladder"].get(tb)
    if not A or not B:
        return None
    tot, n = 0.0, 0
    for k, a in A[side].items():
        b = B[side].get(k)
        if a is None or b is None or (strikes is not None and int(float(k)) not in strikes):
            continue
        tot, n = tot + (b - a), n + 1
    return tot if n else None


def pearson(xs, ys):
    p = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    n = len(p)
    if n < 20:
        return None, n
    mx, my = sum(x for x, _ in p) / n, sum(y for _, y in p) / n
    sxx, syy = sum((x - mx) ** 2 for x, _ in p), sum((y - my) ** 2 for _, y in p)
    if not sxx or not syy:
        return None, n
    return sum((x - mx) * (y - my) for x, y in p) / math.sqrt(sxx * syy), n


# ---------------------------------------------------------------- Part A

def bars_of(d):
    """One row per her 3-min bar (None where a minute is missing): bar-over-bar changes."""
    rows, prev, step, dx = [], None, d.get("step") or 50, d["dext"] >= 0.9
    for m0 in range(OPEN, 15 * 60 + 30, 3):
        ts = [HM(m0 + k) for k in range(3)]
        if any(t not in d["ix"] for t in ts):
            rows.append(None)
            prev = None
            continue
        i = d["ix"][ts[2]]
        cur = {"last": ts[2], "p": d["fut"][i], "bn": d["bnf"][i], "sx": d["sx"][i],
               "delta": sum(d["delta"][d["ix"][t]] or 0 for t in ts) if dx else None}
        if prev and cur["p"] is not None and prev["p"] is not None and d["spot"][i] is not None:
            atm = round(d["spot"][i] / step) * step
            near = {atm + j * step for j in range(-2, 3)}
            ce, pe = oi_chg(d, prev["last"], ts[2], "ce"), oi_chg(d, prev["last"], ts[2], "pe")
            cn, pn = oi_chg(d, prev["last"], ts[2], "ce", near), oi_chg(d, prev["last"], ts[2], "pe", near)
            rows.append({"r": cur["p"] - prev["p"], "nr": (cur["p"] / prev["p"] - 1) * 1e4, "delta": cur["delta"],
                         "lead": None if None in (ce, pe) else pe - ce, "lead_near": None if None in (cn, pn) else pn - cn,
                         "bnr": None if None in (cur["bn"], prev["bn"]) else (cur["bn"] / prev["bn"] - 1) * 1e4,
                         "sxr": None if None in (cur["sx"], prev["sx"]) else (cur["sx"] / prev["sx"] - 1) * 1e4})
        else:
            rows.append(None)
        prev = cur
    return rows


LAGS = (("same bar", 0, 0), ("X a bar ahead", 0, 1), ("X a bar after", 1, 0), ("X two after", 2, 0))


def lead_lag(series, x, r):
    """series = {day: rows}. Pair x[i + a] with r[i + b]: a = 0, b = 1 is 'X a bar ahead of price'."""
    out = []
    for _, a, b in LAGS:
        xs, ys, per = [], [], []
        for rows in series.values():
            X = [None if row is None else row.get(x) for row in rows]
            R = [None if row is None else row.get(r) for row in rows]
            n = len(rows) - max(a, b)
            px, py = [X[i + a] for i in range(n)], [R[i + b] for i in range(n)]
            xs, ys = xs + px, ys + py
            per.append(pearson(px, py)[0])
        c, n = pearson(xs, ys)
        same = sum(1 for v in per if v is not None and c is not None and (v > 0) == (c > 0))
        out.append((c, n, same, sum(v is not None for v in per)))
    return out


def part_a(B, label):
    print(f"\n  {label}: X against the NIFTY futures move, per 3-min bar ('d' = days whose own sign agrees)")
    print(f"    {'X':36s} " + " ".join(f"{n:>18s}" for n, _, _ in LAGS) + "    bars")
    for x, r, name in (("delta", "r", "futures delta (Dext days only)"), ("lead", "r", "writers: PE added - CE added"),
                       ("lead_near", "r", "writers near the money (ATM +/- 2)"), ("bnr", "nr", "BANKNIFTY"), ("sxr", "nr", "SENSEX")):
        res = lead_lag(B, x, r)
        print(f"    {name:36s} " + " ".join(f"{f(c, 6, 2)} ({s:2d}/{t:2d} d)   " for c, _, s, t in res) + f" {res[0][1]:5d}")


# ---------------------------------------------------------------- Part B: the rows

def replay(d):
    """Her zone on her 3-min bands, by the machine's own loop: [{t, side, px, level, ext, xb, first, narm}]."""
    out = []
    for side, band in (("BUY", "d2"), ("SELL", "u2")):
        cur = []
        for s in br.run_states(d["blist"], stop_pts=br.OPERATOR_STOP_PTS, side=side, band=band, span=3):
            a = s.get("arm")
            if a:
                if not a["rearm"]:
                    cur = []
                cur.append((s["t"], a["extreme"], s["level"]))
            if s.get("entry") and cur:
                ref = cur[-1]                                   # the reference bar: the setup's last new extreme
                out.append({"t": s["t"], "side": side, "px": d["blist"][s["i"]]["c"], "level": ref[2], "ext": ref[1],
                            "xb": M(ref[0]), "first": cur[0][0], "narm": len(cur)})
                cur = []
    return sorted(out, key=lambda r: r["t"])


def logged(days):
    out = set()
    with open(os.path.join(ROOT, "data", "trigger_log.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            if "zone3" not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("rule") == "zone3" and r.get("index") == "NIFTY" and r.get("day") in days and r.get("kind") is None \
                    and r.get("px") is not None:
                out.add((r["day"], str(r["t"])[:5], r["side"]))
    return out


def marks_of(day):
    """The extension's marks that day: [{m: minute of day, kind, w: side it favours, rank}], or None (no file)."""
    rows = tape_log._read(tape_log.marks2_path(day, "NIFTY"))
    seen, out = set(), []
    for m in rows:
        if m.get("id") in seen or m.get("t") is None:
            continue
        seen.add(m["id"])
        out.append({"m": (int(m["t"] // 1000 + 19800) % 86400) // 60, "kind": m.get("kind"), "w": m.get("winner"),
                    "rank": m.get("rank")})
    return out or None


def day_label(d):
    """Hindsight, whole day (what the first look used): +1 / -1 one-way, 0 two-sided, with its numbers."""
    if not d["blist"]:
        return 0, "no exchange candles"
    first = [b for b in d["blist"] if b["t"] < "09:30"]
    after = [b for b in d["blist"] if "09:30" <= b["t"] < "15:15"]
    if len(first) < 5 or not after:
        return 0, None
    hi, lo = max(b["h"] for b in first), min(b["l"] for b in first)
    up, dn = sum(b["c"] > hi for b in after), sum(b["c"] < lo for b in after)
    touch = sum(1 for b in after if b["t"] >= "10:00" and b.get("vwap") is not None and b["l"] <= b["vwap"] <= b["h"])
    lab = 1 if up >= ONEWAY_CLOSES * len(after) and touch <= ONEWAY_TOUCH else \
        -1 if dn >= ONEWAY_CLOSES * len(after) and touch <= ONEWAY_TOUCH else 0
    return lab, f"{up}/{dn} of {len(after)} closes above/below the first 15 min · VWAP touched in {touch} bars after 10:00"


def so_far(d, t0, S):
    """What could be known at the trigger bar's close: minutes price has stayed beyond the first-15-minute range without
    a close back inside, minutes since a bar last held VWAP, and whether the trade is against that."""
    first = [b for b in d["blist"] if b["t"] < "09:30"]
    upto = [b for b in d["blist"] if "09:30" <= b["t"] <= t0]
    if len(first) < 5 or not upto:
        return {"dirn": 0, "sus": None, "vw": None, "against": False}
    hi, lo = max(b["h"] for b in first), min(b["l"] for b in first)
    c = upto[-2]["c"] if len(upto) > 1 else upto[-1]["c"]       # the bar before the trigger bar: the leg, not the reversal
    dirn = 1 if c > hi else -1 if c < lo else 0
    sus = 0
    for b in reversed(upto[:-1]):
        if (dirn > 0 and b["c"] > hi) or (dirn < 0 and b["c"] < lo):
            sus += 1
        else:
            break
    vw = next((3 * k for k, b in enumerate(reversed(upto)) if b.get("vwap") is not None and b["l"] <= b["vwap"] <= b["h"]),
              3 * len(upto))
    return {"dirn": dirn, "sus": 3 * sus if dirn else 0, "vw": vw, "against": dirn != 0 and dirn == -S}


def win(d, a, b):
    """Frame indexes of clock minutes a..b inclusive that exist."""
    return [d["ix"][HM(m)] for m in range(a, b + 1) if HM(m) in d["ix"]]


def measure(d, js, S, kd, sd_, opp, so_, dx):
    """One window: with-trade price, delta; defender wall and the other side's near-money writers (lakh); futures OI; peers."""
    if len(js) < 2:
        return {}
    a, b = (js[0] - 1 if js[0] > 0 else js[0]), js[-1]
    ta, tb = d["mins"][a], d["mins"][b]
    g = lambda k: None if None in (d[k][a], d[k][b]) else S * (d[k][b] / d[k][a] - 1) * 1e4   # noqa: E731
    return {"px": S * (d["fut"][b] - d["fut"][a]), "delta": S * sum(d["delta"][j] or 0 for j in js) if dx else None,
            "wall": oi_chg(d, ta, tb, sd_, {kd}), "opp": oi_chg(d, ta, tb, so_, opp),
            "foi": None if None in (d["oi"][a], d["oi"][b]) else d["oi"][b] - d["oi"][a], "bn": g("bnf"), "sx": g("sx")}


def fresh(d, key, i0, i1, hi):
    now = [d[key][j] for j in range(i0, i1 + 1)]
    was = [d[key][j] for j in range(max(0, i0 - 30), i0)]
    if None in now or None in was or len(was) < 10:
        return None
    return max(now) > max(was) if hi else min(now) < min(was)


def trig_rows(d, marks, lab):
    rows, step, dx, done = [], d.get("step") or 50, d["dext"] >= 0.9, {"BUY": [], "SELL": []}
    for e in replay(d):
        t0, side = e["t"], e["side"]
        S, top = (-1 if side == "SELL" else 1), side == "SELL"
        ie = d["ix"].get(HM(M(t0) + 2))
        if ie is None or M(t0) + 2 >= LAST or d["spot"][ie] is None:
            continue
        ext, xb, px = e["ext"], e["xb"], e["px"]
        out, jo, best, jb, heat, hot, js = "OPEN", None, 0.0, ie, 0.0, 0.0, None
        for j in range(ie + 1, len(d["mins"])):
            if M(d["mins"][j]) > LAST:
                break
            hi, lo = d["fhi"][j], d["flo"][j]
            if hi is None or lo is None:
                continue
            if (top and hi > ext) or (not top and lo < ext):
                js = j                                          # the minute her stop is hit
                if out == "OPEN":
                    out, jo = "STOP", j
                break
            hot = max(hot, (hi - px) if top else (px - lo))
            fav = (px - lo) if top else (hi - px)
            if fav > best:
                best, jb, heat = fav, j, hot
            bar = d["bars"].get(HM(OPEN + ((M(d["mins"][j]) - OPEN) // 3 - 1) * 3))
            if out == "OPEN" and bar and bar.get("vwap") is not None and (
                    (top and lo <= bar["vwap"]) or (not top and hi >= bar["vwap"])):
                out, jo = "VWAP", j
        basis = d["fut"][ie] - d["spot"][ie]
        kd = (math.ceil((e["level"] - basis) / step) if top else math.floor((e["level"] - basis) / step)) * step
        atm = round(d["spot"][ie] / step) * step
        opp = {atm - j * step for j in range(3)} if top else {atm + j * step for j in range(3)}
        sd_, so_ = ("ce", "pe") if top else ("pe", "ce")
        W = {"PUSH": win(d, xb - 6, xb + 2), "TURN": win(d, xb + 3, M(t0) + 2), "A1": win(d, M(t0) + 3, M(t0) + 11)}
        Ms = {k: measure(d, w, S, kd, sd_, opp, so_, dx) for k, w in W.items()}
        bd = [(-S) * sum(d["delta"][j] or 0 for j in win(d, xb - 6 + 3 * k, xb - 4 + 3 * k)) for k in range(3)] if dx else None
        lastp = next((p for p in reversed(d.get("pushes") or [])
                      if p.get("dir") == -S and M(t0) + 2 - 15 <= p["m"] <= M(t0) + 2), None)
        i0, i1 = d["ix"].get(HM(xb - 6)), d["ix"].get(HM(xb + 2))
        okw = i0 is not None and i1 is not None
        tbar = d["bars"].get(t0) or {}
        sig = (tbar["u1"] - tbar["vwap"]) if tbar.get("u1") and tbar.get("vwap") is not None else None
        bb = d["bars"].get(HM(OPEN + ((M(d["mins"][jb]) - OPEN) // 3) * 3)) or {}
        endpx = px + S * best
        zb = S * (endpx - bb["vwap"]) / (bb["u1"] - bb["vwap"]) if bb.get("vwap") is not None and bb.get("u1") else None
        L = d["ladder"].get(d["mins"][ie]) or {}
        cand = [(v, int(float(k))) for k, v in (L.get(so_) or {}).items() if v is not None
                and ((top and int(float(k)) <= atm) or (not top and int(float(k)) >= atm))]
        wallk = max(cand)[1] if cand else None
        i9 = d["ix"].get(HM(M(t0) + 11))
        alive9 = i9 is not None and (js is None or js > i9) and M(t0) + 11 < LAST and d["fut"][i9] is not None
        p9 = fwd = None
        if alive9:
            p9, fwd = S * (d["fut"][i9] - px), 0.0
            for j in range(i9 + 1, len(d["mins"]) if js is None else js):
                if M(d["mins"][j]) > LAST or d["fhi"][j] is None:
                    break
                fwd = max(fwd, (d["fut"][i9] - d["flo"][j]) if top else (d["fhi"][j] - d["fut"][i9]))

        def later_opp(k):
            ik = d["ix"].get(HM(M(t0) + 2 + k))
            ok = ik is not None and (js is None or js > ik) and M(t0) + 2 + k <= LAST
            return oi_chg(d, d["mins"][ie], d["mins"][ik], so_, opp) if ok else None
        # 30 minutes in: where it stands, and what came after that (does the writers' cut add anything to price?)
        i30 = d["ix"].get(HM(M(t0) + 32))
        p30 = f30 = None
        if i30 is not None and (js is None or js > i30) and M(t0) + 32 < LAST and d["fut"][i30] is not None:
            p30, f30 = S * (d["fut"][i30] - px), 0.0
            for j in range(i30 + 1, len(d["mins"]) if js is None else js):
                if M(d["mins"][j]) > LAST or d["fhi"][j] is None:
                    break
                f30 = max(f30, (d["fut"][i30] - d["flo"][j]) if top else (d["fhi"][j] - d["fut"][i30]))
        mk = {"her": None, "near": None, "near90": None, "go": None}
        if marks is not None:
            inw = lambda m, a, b: a <= m["m"] and m["m"] + 5 <= b + 1          # noqa: E731   its 5-min bar closed by b
            a_her, a_near, b_ = M(e["first"]) - 15, xb - 6, M(t0) + 2
            mk = {"her": sum(1 for m in marks if m["kind"] in HER_MARKS and m["w"] == S and inw(m, a_her, b_)),
                  "near": sum(1 for m in marks if m["kind"] in TURN_MARKS and m["w"] == S and inw(m, a_near, b_)),
                  "near90": sum(1 for m in marks if m["kind"] in TURN_MARKS and m["w"] == S and inw(m, a_near, b_)
                                and (m.get("rank") or 0) >= 90),
                  "go": sum(1 for m in marks if m["kind"] in GO_MARKS and m["w"] == -S and inw(m, a_near, b_))}
        sf = so_far(d, t0, S)
        prior = done[side]
        rows.append({
            "day": d["day"], "t": t0, "side": side, "S": S, "px": px, "risk": abs(ext - px), "out": out, "best": best,
            "sig": sig, "bs": best / sig if sig else None, "turn": bool(sig) and best / sig >= TURN_S,
            "ran": best >= LOCK_R * abs(ext - px), "heat": heat, "to_best": M(d["mins"][jb]) - (M(t0) + 2), "zend": zb,
            "wall_to_end": None if wallk is None else S * ((wallk + basis) - endpx), "M": Ms,
            "fade": (bd[2] / max(bd)) if bd and max(bd) > 0 else None,
            "tb": S * sum(d["delta"][j] or 0 for j in win(d, M(t0), M(t0) + 2)) if dx else None,
            "ans": None if not lastp else ("refused" if lastp.get("ans") in REFUSED else "broke" if lastp.get("ans") in BROKE else "?"),
            "signs": sum(1 for s in (d.get("reads") or {}).get("signs") or []
                         if s.get("isHigh") == top and M(t0) - 9 <= M(s["at"]) <= M(t0) + 2),
            "bnx": fresh(d, "bnf", i0, i1, top) if okw else None, "sxx": fresh(d, "sx", i0, i1, top) if okw else None,
            "alive9": alive9, "p9": p9, "fwd": fwd, "fwd_s": fwd / sig if fwd is not None and sig else None,
            "stop_later": js is not None, "opp30": later_opp(30), "opp60": later_opp(60), "p30": p30, "f30": f30,
            "f30_s": f30 / sig if f30 is not None and sig else None,
            "loaded": sum(x for x in (Ms["PUSH"].get("opp"), Ms["TURN"].get("opp")) if x is not None),
            "against_h": (lab == 1 and top) or (lab == -1 and not top), "against": sf["against"], "sus": sf["sus"],
            "vw": sf["vw"], "try": len(prior) + 1, "failed_before": sum(1 for p in prior if p), "mk": mk,
            # the entry itself (13 Nov, her 10:18 against 10:54): how late after the extreme, how far from VWAP, how wide the stop
            "waited": (M(t0) - xb) // 3, "zent": (-S) * (px - tbar["vwap"]) / sig if sig else None,
            "risk_s": abs(ext - px) / sig if sig else None,
            "half": "FOUND" if d["day"] >= FOUND_FROM else "FRESH", "narm": e["narm"]})
        done[side].append(out == "STOP")
    return rows


# ---------------------------------------------------------------- Part B: the claims

def claims(rows, label):
    T, O = [r for r in rows if r["turn"]], [r for r in rows if not r["turn"]]
    g = lambda rs, w, k: [r["M"][w].get(k) for r in rs]   # noqa: E731
    two = lambda fn: f"{fn(T)}  /  {fn(O)}"   # noqa: E731
    print(f"\n  ===== {label}: {len(rows)} triggers on {len({r['day'] for r in rows})} days · turns {len(T)} / others {len(O)}"
          f" (by {LOCK_R:g}x risk: {sum(r['ran'] for r in rows)}; on both lists: {sum(r['turn'] and r['ran'] for r in rows)})"
          f" · best median {f(med([r['best'] for r in T]), 0, 0)} / {f(med([r['best'] for r in O]), 0, 0)} pts =====")
    print("    (every line: turns / others)")
    print(f"    DAY, hindsight      against a one-way day: {two(lambda rs: cnt([r['against_h'] for r in rs], bool))}")
    print(f"    DAY, at the trigger against a move sustained beyond the first 15 min: {two(lambda rs: cnt([r['against'] for r in rs], bool))}"
          f" · minutes it had been sustained, median: {two(lambda rs: f(med([r['sus'] for r in rs if r['against']]), 0, 0))}")
    print(f"                        minutes since a bar last held VWAP, median: {two(lambda rs: f(med([r['vw'] for r in rs]), 0, 0))}"
          f" · 120 or more: {two(lambda rs: cnt([r['vw'] for r in rs], lambda x: x >= 120))}"
          f" · under 60: {two(lambda rs: cnt([r['vw'] for r in rs], lambda x: x < 60))}")
    print(f"                        try number that day, median: {two(lambda rs: f(med([r['try'] for r in rs]), 0, 0))}"
          f" · after an earlier same-side stop: {two(lambda rs: cnt([r['failed_before'] for r in rs], lambda x: x > 0))}")
    print(f"    THE ENTRY           bars from the extreme to the trigger, median: {two(lambda rs: f(med([r['waited'] for r in rs]), 0, 0))}"
          f" · 3 bars or fewer: {two(lambda rs: cnt([r['waited'] for r in rs], lambda x: x <= 3))}"
          f" · 5 bars or more: {two(lambda rs: cnt([r['waited'] for r in rs], lambda x: x >= 5))}"
          f" · entry still 1 sigma or more from VWAP: {two(lambda rs: cnt([r['zent'] for r in rs], lambda x: x >= 1))}"
          f" · stop distance in sigmas, median: {two(lambda rs: f(med([r['risk_s'] for r in rs]), 0, 1))}")
    print(f"    AT THE BAND         push refused: {two(lambda rs: f'{sum(r['ans'] == 'refused' for r in rs)} of {len(rs)}')}"
          f" · last bar's share of the push, median: {two(lambda rs: f(med([r['fade'] for r in rs]), 0, 2))}"
          f" · a top / bottom sign: {two(lambda rs: f'{sum(r['signs'] > 0 for r in rs)} of {len(rs)}')}")
    print(f"                        wall adding in the push: {two(lambda rs: cnt(g(rs, 'PUSH', 'wall'), lambda x: x > 0))}"
          f" · BANKNIFTY made the same extreme: {two(lambda rs: cnt([r['bnx'] for r in rs], bool))}"
          f" · re-arms in the setup, median: {two(lambda rs: f(med([r['narm'] for r in rs]), 0, 0))}")
    print(f"    MARKS AT THE BAND   THAKAN / ROKA on her side, her window: {two(lambda rs: cnt([r['mk']['her'] for r in rs], lambda x: x > 0))}"
          f" · any turn mark near the extreme: {two(lambda rs: cnt([r['mk']['near'] for r in rs], lambda x: x > 0))}"
          f" · ranked 90+: {two(lambda rs: cnt([r['mk']['near90'] for r in rs], lambda x: x > 0))}"
          f" · a ZOR / PEHAL mark against her: {two(lambda rs: cnt([r['mk']['go'] for r in rs], lambda x: x > 0))}")
    print(f"    THE TRIGGER         trigger bar's delta with her: {two(lambda rs: cnt([r['tb'] for r in rs], lambda x: x > 0))}"
          f" · other side's writers already cutting: {two(lambda rs: cnt(g(rs, 'TURN', 'opp'), lambda x: x < 0))}"
          f" · loaded in the push and turn, median: {two(lambda rs: f(med([r['loaded'] for r in rs]), 0, 1) + 'L')}")
    al = [r for r in rows if r["alive9"]]
    up, dn = [r for r in al if r["p9"] > 0], [r for r in al if r["p9"] <= 0]
    more = lambda rs: f"{len(rs)} -> {sum(1 for r in rs if r['fwd_s'] is not None and r['fwd_s'] >= TURN_S)} gave 2 sigma more (median {f(med([r['fwd'] for r in rs]), 0, 0)} pts more, stop hit later {sum(r['stop_later'] for r in rs)})"   # noqa: E731
    both = [r for r in up if r["M"]["A1"].get("bn") is not None and r["M"]["A1"].get("sx") is not None]
    print(f"    FIRST 9 MINUTES     ({len(al)} still alive; against what came after) in profit: {more(up)} · under water: {more(dn)}")
    print(f"                        in profit, not against a sustained move: {more([r for r in up if not r['against']])}"
          f" · in profit, against one: {more([r for r in up if r['against']])}")
    print(f"                        when in profit, BANKNIFTY and SENSEX both with her: {sum(1 for r in both if r['M']['A1']['bn'] > 0 and r['M']['A1']['sx'] > 0)} of {len(both)}")
    print(f"    HOLD                other side's writers cutting by +30 min: {two(lambda rs: cnt([r['opp30'] for r in rs], lambda x: x < 0) + ' (median ' + f(med([r['opp30'] for r in rs]), 0, 1) + 'L)')}")
    print(f"                        by +60 min: {two(lambda rs: cnt([r['opp60'] for r in rs], lambda x: x < 0) + ' (median ' + f(med([r['opp60'] for r in rs]), 0, 1) + 'L)')}")
    a30 = [r for r in rows if r["p30"] is not None and r["p30"] > 0 and r["opp30"] is not None]
    m30 = lambda rs: f"{len(rs)} -> median {f(med([r['f30'] for r in rs]), 0, 0)} pts more, 1 sigma more: {sum(1 for r in rs if r['f30_s'] is not None and r['f30_s'] >= 1)}, stop hit later {sum(r['stop_later'] for r in rs)}"   # noqa: E731
    print(f"    HOLD, the test      alive and in profit 30 min in · writers cutting: {m30([r for r in a30 if r['opp30'] < 0])}"
          f" · writers still adding: {m30([r for r in a30 if r['opp30'] >= 0])}")
    zz = [r["zend"] for r in T if r["zend"] is not None]
    wl = [r["wall_to_end"] for r in T if r["wall_to_end"] is not None]
    print(f"    THE TURNS           came back before the best point: median {f(med([r['heat'] for r in T]), 0, 0)} pts, most {f(max([r['heat'] for r in T], default=None), 0, 0)}"
          f" (stop median {f(med([r['risk'] for r in T]), 0, 0)}) · more than her stop's half: {sum(1 for r in T if r['heat'] > r['risk'] / 2)} of {len(T)}"
          f" · minutes to the best point median {f(med([r['to_best'] for r in T]), 0, 0)}")
    print(f"                        ended at or past the far 2 sigma: {sum(z >= 2 for z in zz)} of {len(zz)} · between VWAP and it: {sum(0 <= z < 2 for z in zz)} · short of VWAP: {sum(z < 0 for z in zz)}"
          f" · biggest opposite wall: short {sum(w > 25 for w in wl)}, at it {sum(abs(w) <= 25 for w in wl)}, through {sum(w < -25 for w in wl)}")


def main(argv):
    if "--build" in argv:
        return max([build_frame(x) for x in argv[argv.index("--build") + 1:]] or [0])
    if "--low" in argv:                                       # market hours: below-normal priority, and only with memory to spare
        import ctypes
        if free_mb() < 600:
            print(f"REFUSED: {free_mb():.0f} MB free (needs 600)")
            return 3
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    B, rows, meta = {}, [], []
    paths = sorted(glob.glob(os.path.join(SCRATCH, "frame_NIFTY_*.json")))
    for p in paths:
        d = load(p)
        if not d:
            continue
        lab, why = day_label(d)
        marks = marks_of(d["day"])
        tr = trig_rows(d, marks, lab)
        B[d["day"]] = bars_of(d)
        rows += tr
        meta.append((d["day"], len(d["mins"]), d["dext"], marks is not None, lab, why, {(r["day"], r["t"], r["side"]) for r in tr}, d["exch"]))
        del d
    days = [m[0] for m in meta]
    print(f"{len(days)} sessions: {days[0]} .. {days[-1]} · FRESH (before {FOUND_FROM}): {sum(x < FOUND_FROM for x in days)} · FOUND: {sum(x >= FOUND_FROM for x in days)}")
    print(f"exchange candles (so her bands and her zone can be read) on {sum(m[7] for m in meta)}: "
          f"FRESH {sum(m[7] and m[0] < FOUND_FROM for m in meta)} · FOUND {sum(m[7] and m[0] >= FOUND_FROM for m in meta)}"
          f" · without: {', '.join(m[0][5:] for m in meta if not m[7]) or 'none'} (Part A only)")
    print(f"delta is Dext's on {sum(m[2] >= 0.9 for m in meta)} of them (the others: delta reads left out) · footprint marks on {sum(m[3] for m in meta)}")
    print("one-way days by the hindsight label: " + (", ".join(f"{m[0][5:]} {'up' if m[4] > 0 else 'down'}" for m in meta if m[4]) or "none"))
    lg = logged(set(days))
    mine = set().union(*[m[6] for m in meta]) if meta else set()
    chk = {x for x in mine if x[0] >= FOUND_FROM and int(x[1][:2]) * 60 + int(x[1][3:]) + 2 < LAST}
    lgc = {x for x in lg if int(x[1][:2]) * 60 + int(x[1][3:]) + 2 < LAST}
    print(f"the replay against the trigger log (28 Oct on, before 15:00): both {len(chk & lgc)} · only the replay {len(chk - lgc)} · only the log {len(lgc - chk)}")
    if "--days" in argv:
        for m in meta:
            print(f"   {m[0]} · {m[1]} min · Dext delta {m[2]:.0%} · marks {'yes' if m[3] else 'no'} · {m[5]}")

    print("\nPART A  what moves first")
    part_a({k: v for k, v in B.items() if k >= FOUND_FROM}, "FOUND days")
    part_a({k: v for k, v in B.items() if k < FOUND_FROM}, "FRESH days")

    print("\nPART B  her zone triggers, walked with her stop to 15:00. A turn = best point at least 2 of her sigmas from the entry.")
    if "--rows" in argv:
        for r in rows:
            print(f"   {r['day']} {r['t']} {r['side']:4s} at {r['px']:,.0f}f try {r['try']} · risk {r['risk']:.0f} · {r['out']:4s} · best {r['best']:.0f} = {f(r['bs'], 0, 1)} sigma"
                  f" · {'TURN' if r['turn'] else '    '} · VWAP untouched {r['vw']} min · {'against ' + str(r['sus']) + ' min' if r['against'] else 'not against'}"
                  f" · marks her/near/90/go {r['mk']['her']}/{r['mk']['near']}/{r['mk']['near90']}/{r['mk']['go']}")
    if "--html" in argv:                                      # the list for her own eyes: every trigger, by day
        why = {m[0]: (m[4], m[5]) for m in meta}
        out = ["<!doctype html><meta charset='utf-8'><title>Zone triggers · 30 Sep to 12 Nov</title><style>"
               "body{font:13px/1.4 'Segoe UI',system-ui,sans-serif;background:#f4f5f7;color:#111827;margin:16px;font-variant-numeric:tabular-nums}"
               "table{border-collapse:collapse;background:#fff;width:100%;max-width:1100px}th{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;"
               "color:#566072;text-align:left;border-bottom:2px solid #111827;padding:5px 8px}td{border-bottom:1px solid #eef0f4;padding:4px 8px;white-space:nowrap}"
               "tr.d td{background:#eef0f4;font-weight:650;white-space:normal}tr.t td{background:#e3f4e8}.s{color:#be185d;font-weight:650}.b{color:#166534;font-weight:650}"
               ".m{color:#566072}</style><h1 style='font-size:18px;margin:0 0 4px'>Your zone triggers, 30 Sep to 12 Nov</h1>"
               "<p class='m' style='max-width:1000px'>NIFTY futures, 3-minute bars, your VWAP bands. The time is the start of the trigger bar; it closes 3 minutes later and the entry is that close. "
               "Stop = beyond the high / low made in the band. Green rows went at least 2 of your sigmas from the entry before the stop or 15:00. "
               "Replayed by the zone machine's own loop on the exchange's candles; on 28 Oct to 12 Nov it matches the trigger log on all 44.</p>"
               "<table><tr><th>Bar</th><th>Side</th><th>Entry</th><th>Stop away</th><th>Try</th><th>VWAP untouched for</th><th>What came first</th>"
               "<th>Best after</th><th>In sigmas</th><th>Min to best</th><th>Came back first</th></tr>"]
        last = None
        for r in rows:
            if r["day"] != last:
                last = r["day"]
                lab, txt = why[last]
                out.append(f"<tr class='d'><td colspan='11'>{last} · {'one-way up (seen afterwards)' if lab > 0 else 'one-way down (seen afterwards)' if lab < 0 else 'two-sided'} · {txt}</td></tr>")
            out.append(f"<tr{' class=t' if r['turn'] else ''}><td>{r['t']}</td><td class='{'s' if r['side'] == 'SELL' else 'b'}'>{r['side']}</td><td>{r['px']:,.0f}f</td>"
                       f"<td>{r['risk']:.0f} pts</td><td>{r['try']}</td><td>{'-' if r['vw'] is None else str(r['vw']) + ' min'}</td>"
                       f"<td>{ {'VWAP': 'reached VWAP', 'STOP': 'stopped', 'OPEN': 'neither by 15:00'}[r['out']] }</td><td>{r['best']:.0f} pts</td>"
                       f"<td>{f(r['bs'], 0, 1)}</td><td>{r['to_best']}</td><td>{r['heat']:.0f} pts</td></tr>")
        with open(argv[argv.index("--html") + 1], "w", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "</table>")
    claims([r for r in rows if r["half"] == "FOUND"], "FOUND (28 Oct - 12 Nov)")
    claims([r for r in rows if r["half"] == "FRESH"], "FRESH (before 28 Oct)")
    claims(rows, "ALL")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
