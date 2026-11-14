"""build_jarvis3.py -- builds docs/jarvis-panel/jarvis3-mockup.html: a self-contained copy of her Jarvis page
(docs/kahani/review/mockup/jarvis2.html, never modified) with the day's frame inlined and six layers added:
move bands, option order flow, the sync lane, the five-block right panel, the movable Jarvis window, the DEMO trade.

    python docs/jarvis-panel/build_jarvis3.py [YYYY-MM-DD] [--fresh]

  frame     the NIFTY replay frame exactly as the page asks for it (GET /api/jarvis?idx=NIFTY&day=..&fill=1). Order:
            the scratch copy of an earlier GET (unless --fresh) -> ONE GET to the running server on 8765 -> offline, what
            server._jarvis_reply does (jarvis.build + jarvis.calls). Never starts or stops anything.                 [M]
  pushes    HOLD v2's PUSH, unchanged: ruler.push_bars / ruler.push_ref / hold2.pushes (ruler.main's `push` branch)  [M]
  bands     a run from the OPEN of a PUSH bar; line = origin - d x hold2.TRAIL_U x U; a later same-side PUSH moves the
            line toward price only; over at the first 1-min futures bar after the first push bar's close that trades
            through the line, or at the close of an opposite PUSH bar. Named from Dext delta x futures OI over its bars.
  legs      each PUSH of a band is a LEG: the same reads (name, delta, OI, the two speeds) taken from that push bar's
            open to the next same-side push bar's open. On 11 Nov the 09:50 band's line (25,444.8f) was never traded
            (the high was 25,439.0f at 11:48), so the 12:10 push EXTENDS it; the "12:10 NEW SHORTS" read is its 2nd leg.
  forming   hold2.state on the still-open 5-min bar (open, this minute's close, delta and volume so far), per minute.
  opt       optflow/optladder.build: WHO per strike ATM +-3 and the cap / floor word at each 3-min close.            [I thresholds are optladder's]
  sync      one cell per 3-min bar: the sign of each index's move, pale under that index's own median so far (causal).
            The frame carries NIFTY futures but BANKNIFTY and SENSEX as SPOT; the lane says so.
  trade     DEMO only: the day's first zone trigger as if she were in it; the stop is the latest with-side push's line.

No threshold lives in this file. Read-only on the repo: it writes the HTML and the scratch copy of the frame."""
import glob
import json
import os
import re
import statistics
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "docs", "kahani", "review", "mockup", "jarvis2.html")
OUT = os.path.join(HERE, "jarvis3-mockup.html")
OUT_LIVE = os.path.join(ROOT, "docs", "kahani", "review", "mockup", "jarvis3.html")   # --live: beside her live page, served on 8787
NOT_LIVE = "not live yet: the server does not send this layer to the page"
SCRATCH = os.path.join(HERE, "scratch")
IDX, OPEN = "NIFTY", 9 * 60 + 15
NAMES = {(1, -1): "SHORT COVERING", (1, 1): "NEW LONGS", (-1, 1): "NEW SHORTS", (-1, -1): "LONG EXIT"}   # (delta, OI) signs


def m_of(s):
    return int(s[:2]) * 60 + int(s[3:5])


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def sgn(x):
    return (x > 0) - (x < 0)


def arr(d):
    return "▲" if d > 0 else "▼"


# ---- the frame -----------------------------------------------------------------------------------------------------------
def get_frame(day, fresh=False):
    path = os.path.join(SCRATCH, f"frame_{IDX}_{day}.json")
    if not fresh and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f), "the scratch copy of GET /api/jarvis"
    why = None
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:8765/api/jarvis?idx={IDX}&day={day}&fill=1", timeout=120) as r:
            raw = r.read()
        d = json.loads(raw)
        if d.get("ok") and d.get("mins"):
            os.makedirs(SCRATCH, exist_ok=True)
            with open(path, "wb") as f:
                f.write(raw)
            return d, "one GET to the running server"
        why = d.get("why")
    except Exception as e:                                          # server down or refusing: build what it would build
        why = f"{type(e).__name__}: {e}"
    print(f"the server did not give the frame ({why}); building it offline as server._jarvis_reply does")
    import jarvis
    d = dict(jarvis.build(day, IDX, None, True), live=False, asof=time.strftime("%H:%M:%S"))
    if d.get("ok"):
        d["calls"] = jarvis.calls(d)
        if d.get("mins") and d.get("call") is not None:
            d["call"]["xstate"] = {"t": d["mins"][-1], "sync": None, "day": None, "alert": None,
                                   "why": ["cross: not read — a replay builds one index"]}
    return json.loads(json.dumps(d, default=str)), "built offline (jarvis.build + jarvis.calls)"


# ---- move bands (ruler.py + hold2.py) ------------------------------------------------------------------------------------
def pct_of(q, x):
    """The percentile (0-100) of x in a 101-point quantile list (rank_build.quant's shape); None when either is missing."""
    import bisect
    if x is None or not isinstance(q, list) or len(q) < 101:
        return None
    return max(0, min(100, bisect.bisect_right(q, x) - 1))


def part_of(m):
    """rank.PARTS in minutes of the day: 09:15-10:00, 10:00-12:00, 12:00-13:30, 13:30 on."""
    return 0 if m < 600 else 1 if m < 720 else 2 if m < 810 else 3


def oi5(ones, lot):
    """(part of the day, abs 5-minute futures OI change in lots) for each 5-min bar of one day's 1-min tape."""
    oi = {m_of(b["t"]): b.get("oi") for b in ones}
    out = []
    for s in range(OPEN, OPEN + 375, 5):
        a, b = oi.get(s - 1) or oi.get(s), oi.get(s + 4)
        if a and b:
            out.append((part_of(s), abs(b - a) / lot))
    return out


WIN5 = 8                                                            # rank.WIN: 8 x 5 min = 40 minutes, her READ's window


def rank_in(vals, x):
    """STRENGTH v2's rank: the share (0-100) of the sorted past windows `vals` no larger than x. Under 15 windows = not read."""
    import bisect
    if x is None or not vals or len(vals) < 15:
        return None
    return round(100 * bisect.bisect_right(vals, x) / len(vals))


def win_key(s, k):
    """The rank table a window belongs to: its own length while it is still filling (1-7 bars), else its part of the day."""
    return k if k < WIN5 else 10 + part_of(s)


def windows(ones, flow5, lot):
    """Per closed 5-min bar of one day (keyed by its open minute): THE WINDOW ending at it (the last WIN5 bars, or the bars since
    the open) -> net Dext delta (lots; None if a bar of it is blind), futures OI change (lots; None if unread), futures price change."""
    O = {m_of(b["t"]): b for b in ones}
    D = {f["s"]: f["delta"] for f in flow5}
    out = {}
    for s in sorted(D):
        k = min(WIN5, (s - OPEN) // 5 + 1)
        ws = s - 5 * (k - 1)
        a, b = O.get(ws), O.get(s + 4)
        if a is None or b is None:
            continue
        ds = [D.get(x) for x in range(ws, s + 1, 5)]
        base, end = (O.get(ws - 1) or a).get("oi"), b.get("oi")
        out[s] = {"k": k, "ws": ws, "wd": None if any(x is None for x in ds) else sum(ds),
                  "woi": None if not base or not end else (end - base) / lot,
                  "wpx": None if a.get("o") is None or b.get("c") is None else b["c"] - a["o"]}
    return out


def meter2_layer(frame, mv, opt):
    """STRENGTH v2, exactly as written in docs/jarvis-panel/STRENGTH-METER-DEFINITION-v2.md BEFORE this ran: v1's five families,
    each read over THE WINDOW, the plain average of the families read, shown to the nearest 10. Shadow, display only."""
    import math
    mins, tl = frame["mins"], frame.get("timeline") or []
    W = {w["si"]: w for w in mv["win5"]}
    C = sorted(opt.get("closes") or [], key=lambda x: x["i"])
    G = {"BUILDING": 100, "STALLED": 50, "UNWINDING": 0}
    r10 = lambda v: int(10 * math.floor(v / 10 + 0.5))                                                   # noqa: E731
    fut, fo, spots = frame["fut"], frame.get("fo"), [frame.get("bnf"), frame.get("sx")]
    rows = []
    for c in range(2, len(mins), 3):
        s5 = ((c + 1) // 5) * 5 - 5                                 # the last 5-min bar closed by this read
        if s5 < 0:
            continue
        k = min(WIN5, s5 // 5 + 1)
        ws, we = s5 - 5 * (k - 1), s5 + 4                           # the window's minutes [ws .. we]
        w = W.get(s5)
        f1 = f2 = f3 = f4 = f5 = None
        if w and w["wdp"] is not None and w["wpx"] is not None:                      # F1 flow over the window, with a result
            s = sgn(w["wd"])
            v = w["wdp"] if s and sgn(w["wpx"]) == s else 0
            f1 = [v if s > 0 else 0, v if s < 0 else 0]
        if w and w["woip"] is not None and w["wpx"] is not None:                     # F2 positions over the window: new money only
            s = sgn(w["wpx"])
            v = w["woip"] if w["woi"] > 0 else 0
            f2 = [v if s > 0 else 0, v if s < 0 else 0]
        fr = ((tl[c] or {}).get("fronts") or []) if c < len(tl) else []              # F3 writers: unchanged from v1
        top = {sd: max((x for x in fr if x.get("side") == sd and x.get("state") in G), key=lambda x: x.get("peak") or 0, default=None)
               for sd in ("CE", "PE")}
        up, dn = [], []
        if top["CE"]:
            g = G[top["CE"]["state"]]
            dn.append(g)
            up.append(100 - g)
        if top["PE"]:
            g = G[top["PE"]["state"]]
            up.append(g)
            dn.append(100 - g)
        if up:
            f3 = [sum(up) / len(up), sum(dn) / len(dn)]
        lastc = next((x for x in reversed(C) if x["i"] <= c), None)                  # F4 option flow: settled lean + the cover rule in the window
        if lastc and lastc["said"] != "OI?":
            cov = {-1 if x["cover"]["side"] == "PE" else 1 for x in C if ws <= x["i"] <= c and x.get("cover")}
            fuel = 1 if lastc["said"] == "UP FUEL" else -1 if lastc["said"] == "DOWN FUEL" else 0
            f4 = [100 if s in cov or fuel == s else 50 if lastc["lean"] == s else 0 for s in (1, -1)]
        ch = []                                                                      # F5 all three over the window: direction only
        o = fo[ws] if fo and fo[ws] is not None else fut[ws - 1] if ws else fut[ws]
        if o is not None and fut[we] is not None:
            ch.append(fut[we] - o)
        for sp in spots:
            if sp and sp[we] is not None and sp[ws - 1 if ws else ws] is not None:
                ch.append(sp[we] - sp[ws - 1 if ws else ws])
        if ch:
            f5 = [100 * sum(1 for x in ch if x * s > 0) / len(ch) for s in (1, -1)]
        fam = {"flow": f1, "pos": f2, "wr": f3, "opt": f4, "all3": f5}
        read = [v for v in fam.values() if v is not None]
        if not read:
            continue
        rows.append({"i": c, "ki": c + 1, "t": mins[c], "n": len(read), "k": k,
                     "up": r10(sum(v[0] for v in read) / len(read)), "dn": r10(sum(v[1] for v in read) / len(read)),
                     "fam": {key: None if v is None else [round(v[0]), round(v[1])] for key, v in fam.items()}})
    return {"rows": rows, "v": 2}


def meter_words(rows, fixed=0):
    """Definition v2 §4, the STICKY word at each row for the side in play (`fixed` = her trade's side; 0 = the larger number)."""
    last = {1: [0, -1, -1], -1: [0, -1, -1]}                        # per side: [direction of its most recent change, that row, the row of its most recent rise]
    out, side, prev = [], 0, None
    for n, r in enumerate(rows):
        for s, key in ((1, "up"), (-1, "dn")):
            if prev is not None and r[key] != prev[key]:
                d = 1 if r[key] > prev[key] else -1
                last[s][0], last[s][1] = d, n
                if d > 0:
                    last[s][2] = n
        side = fixed or (1 if r["up"] > r["dn"] else -1 if r["dn"] > r["up"] else side)
        if not side:
            out.append(None)
        else:
            me, ot = (r["up"], r["dn"]) if side > 0 else (r["dn"], r["up"])
            lm, lo = last[side], last[-side]
            out.append("TURNING" if ot > me else "CONTESTED" if lo[0] > 0 and lo[1] > lm[2] else
                       "BUILDING" if lm[0] > 0 else "RESTING" if lm[0] < 0 else "STEADY")
        prev = r
    return out


def meter2_stats(rows, events):
    """What v2's shadow run counts (definition v2 §5): the word's changes against the day's own events (PUSH bars + confirmed
    swings), the number's moves, the unread families. Nothing else."""
    ws = [w for w in meter_words(rows) if w]
    wc = sum(1 for a, b in zip(ws, ws[1:]) if a != b)
    nm = sum(1 for a, b in zip(rows, rows[1:]) if (a["up"], a["dn"]) != (b["up"], b["dn"]))
    return {"closes": len(rows), "number_moves": nm, "word_changes": wc, "events": events, "pass1": wc <= events,
            "full_reads": sum(1 for r in rows if r["n"] == 5),
            "unread": {k: sum(1 for r in rows if r["fam"][k] is None) for k in ("flow", "pos", "wr", "opt", "all3")}}


def voices_md(day, frame, t):
    """The record (BOOK-TRAIL-V2-DEFINITION.md §3): every line each of the three voices said on the trade, in time order,
    with the futures price and the trade's points then. Rows only: no rate, no verdict."""
    mins, fut, d = frame["mins"], frame["fut"], t["d"]
    rows, was = [], None
    for v in t["voice"]:
        if v["w"] != was:
            rows.append((min(v["i"], len(mins) - 1), 0, "HOLD voice", f"{v['w']} · {v['why']}"))
        was = v["w"]
    for m in t.get("old") or []:
        rows.append((min(m["b"] + 1, len(mins) - 1), 1, "book / trail, old",
                     m["st"] + (f" · trail {m['trail'][0]} {m['trail'][1]:,.1f}f" if m.get("trail") else "")
                     + (f" · against: {', '.join(m['against'])}" if m.get("against") else "") + (f" · with: {', '.join(m['with'])}" if m.get("with") else "")))
    for b in t.get("book") or []:
        rows.append((b["i"], 2, "book / trail, new", f"{b['w']} · {b['why']}"))
    rows.sort()
    out = [f"# The three voices on the DEMO trade — {day}", "",
           f"Trade: {t['t']} {t['side']} at {t['px']:,.1f}f, entered at the trigger bar's close ({mins[t['ei']]})."
           + (f" Exit: {t['exit']['t']} at {t['exit']['stop']:,.1f}f, {t['exit']['pts']:+.1f} pts (a trade through the HOLD v2 line)."
              if t.get("exit") else " Open at the day's last minute."), "",
           "Written by `build_jarvis3.py`. Rows only: what each voice said, when, the futures price and the trade's points at that minute. "
           "No rate, no verdict. Display only: nothing was placed.", "",
           "| Time | Voice | It said | Futures | Points |", "|---|---|---|---|---|"]
    for i, _, who, said in rows:
        out.append(f"| {mins[i]} | {who} | {said} | {fut[i]:,.1f}f | {d * (fut[i] - t['px']):+.1f} |")
    with open(os.path.join(HERE, f"voices_{day}.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    return len(rows)


def meter_layer(frame, mv, opt, sync):
    """STRENGTH v1, exactly as written in docs/jarvis-panel/STRENGTH-METER-DEFINITION.md BEFORE this ran: at each 3-min close a
    0-100 score per side from five families, the plain average of the families read. Shadow, display only."""
    import math
    N, tl, res = len(frame["mins"]), frame.get("timeline") or [], mv.get("res_min") or 0.25
    B5 = {b["si"]: b for b in mv["bars5"]}
    OC = {c["i"]: c for c in opt.get("closes") or []}
    SB = {b["a"]: b for b in sync["bars"]}
    G = {"BUILDING": 100, "STALLED": 50, "UNWINDING": 0}
    r5 = lambda v: int(5 * math.floor(v / 5 + 0.5))                                                      # noqa: E731
    rows = []
    for c in range(2, N, 3):
        b = B5.get(((c + 1) // 5) * 5 - 5)                          # the 5-min bar that had closed by this read
        f1 = f2 = f3 = f4 = f5 = None
        if b and b.get("pct") is not None and b.get("R") is not None:                # F1 futures flow: effort that got a result
            v = b["pct"] if b["R"] >= res else 0
            f1 = [v if b["d"] > 0 else 0, v if b["d"] < 0 else 0]
        if b and b.get("oip") is not None:                                           # F2 futures positions: new money only
            v = b["oip"] if b["doi"] > 0 else 0
            f2 = [v if b["pc"] > 0 else 0, v if b["pc"] < 0 else 0]
        fr = ((tl[c] or {}).get("fronts") or []) if c < len(tl) else []              # F3 writers: the §1d front per side
        top = {s: max((x for x in fr if x.get("side") == s and x.get("state") in G), key=lambda x: x.get("peak") or 0, default=None)
               for s in ("CE", "PE")}
        up, dn = [], []
        if top["CE"]:
            g = G[top["CE"]["state"]]
            dn.append(g)
            up.append(100 - g)
        if top["PE"]:
            g = G[top["PE"]["state"]]
            up.append(g)
            dn.append(100 - g)
        if up:
            f3 = [sum(up) / len(up), sum(dn) / len(dn)]
        r = OC.get(c)                                                                # F4 option flow: this close's own read
        if r and r["raw"] != "OI?":
            cv = r.get("cover")
            cs = 0 if not cv else (-1 if cv["side"] == "PE" else 1)
            fuel = 1 if r["raw"] == "UP FUEL" else -1 if r["raw"] == "DOWN FUEL" else 0
            f4 = [100 if s in (cs, fuel) else 50 if r["lr"] == s else 0 for s in (1, -1)]
        sb = SB.get(c - 2)                                                           # F5 all three indices
        vs = [x for x in (sb["v"] if sb else []) if x is not None]
        if vs:
            f5 = [100 * sum((0.5 if x[1] else 1) if x[0] * s > 0 else 0 for x in vs) / len(vs) for s in (1, -1)]
        fam = {"flow": f1, "pos": f2, "wr": f3, "opt": f4, "all3": f5}
        read = [v for v in fam.values() if v is not None]
        if not read:
            continue
        rows.append({"i": c, "ki": c + 1, "t": frame["mins"][c], "n": len(read),
                     "up": r5(sum(v[0] for v in read) / len(read)), "dn": r5(sum(v[1] for v in read) / len(read)),
                     "fam": {k: None if v is None else [round(v[0]), round(v[1])] for k, v in fam.items()}})
    return {"rows": rows}


def meter_stats(rows):
    """What the shadow run counts (definition §6): how often the shown numbers and the word move in a day. Nothing else."""
    num = word = 0
    side, was, pw = 0, None, None
    for r in rows:
        if was and (r["up"], r["dn"]) != (was["up"], was["dn"]):
            num += 1
        side = 1 if r["up"] > r["dn"] else -1 if r["dn"] > r["up"] else side
        w = None
        if side and was:
            me, ot, pm, po = (r["up"], r["dn"], was["up"], was["dn"]) if side > 0 else (r["dn"], r["up"], was["dn"], was["up"])
            w = "TURNING" if ot > me else "CONTESTED" if ot > po else "BUILDING" if me > pm else "RESTING" if me < pm else "STEADY"
        if w and pw and w != pw:
            word += 1
        pw, was = w or pw, r
    return {"closes": len(rows), "number_moves": num, "word_changes": word,
            "full_reads": sum(1 for r in rows if r["n"] == 5), "unread": {k: sum(1 for r in rows if r["fam"][k] is None) for k in ("flow", "pos", "wr", "opt", "all3")}}


def name_of(dl, oi):
    return None if dl is None or oi is None else NAMES.get((sgn(dl), sgn(oi)))


def move_layer(day, M0, last):
    import dext_log
    import handshake
    import hold2
    import ruler
    import v2feed
    lot = v2feed.LOTS[IDX]
    ones = ruler.ones_of(day, IDX)
    O = {m_of(b["t"]): b for b in ones}
    tag = ruler.dext_tag(day, IDX)
    cand = dext_log.read_candles(tag, day) if tag else []
    prior = sorted({os.path.basename(p)[-16:-6] for p in glob.glob(os.path.join(dext_log.DIR, "dext_NSE-*_*.jsonl"))
                    if "ohlc" not in os.path.basename(p)} - {day})
    days, oi_hist, tabD, tabO = {}, [], {}, {}
    for d in prior:                                                 # ruler.main's `push` branch, one day at a time
        t = ruler.dext_tag(d) if d < day else None
        if t:
            od, cd = ruler.ones_of(d), dext_log.read_candles(t, d)
            days[d] = ruler.push_bars(od, cd, lot)
            oi_hist += oi5(od, lot)                                 # STRENGTH F2: the yardstick for a 5-min futures OI change, by part of the day
            for s, w in windows(od, ruler.flow(cd, lot, 5), lot).items():           # STRENGTH v2: the yardsticks of THE WINDOW
                if w["wd"] is not None:
                    tabD.setdefault(win_key(s, w["k"]), []).append(abs(w["wd"]))
                if w["woi"] is not None:
                    tabO.setdefault(win_key(s, w["k"]), []).append(abs(w["woi"]))
    for tab in (tabD, tabO):
        for v in tab.values():
            v.sort()
    oi_q = {}
    for part in range(4):
        v = sorted(x for pp, x in oi_hist if pp == part)
        oi_q[part] = [v[k * (len(v) - 1) // 100] for k in range(101)] if len(v) >= 101 else None
    ref = ruler.push_ref(days)
    P = hold2.pushes(ruler.push_bars(ones, cand, lot, last + 1), ref)
    for p in P:
        p["line"] = p["origin"] - p["d"] * hold2.TRAIL_U * p["U"]
    F = ruler.flow(cand, lot, 5, last + 1)
    D = {f["s"]: d for f, d in zip(F, ruler.noise(F))}
    W5 = []                                                         # STRENGTH v2: today's windows, each ranked against the past days' windows
    for s, w in sorted(windows(ones, F, lot).items()):
        key = win_key(s, w["k"])
        W5.append({"si": s - M0, "k": w["k"], "wsi": w["ws"] - M0, "wd": None if w["wd"] is None else round(w["wd"]),
                   "woi": None if w["woi"] is None else round(w["woi"]), "wpx": None if w["wpx"] is None else round(w["wpx"], 1),
                   "wdp": rank_in(tabD.get(key), None if w["wd"] is None else abs(w["wd"])),
                   "woip": rank_in(tabO.get(key), None if w["woi"] is None else abs(w["woi"]))})
    q1 = {m: v for m, v in handshake.dext_flow(cand, 1).items() if m >= OPEN}        # Dext delta, contracts per minute

    by_close, bands, live = {p["close"]: p for p in P}, [], None
    for m in range(OPEN, last + 1):
        p = by_close.get(m)                                         # the 5-min bar that closed as minute m opened
        if p and live and p["d"] == live["d"]:                      # same side: the band goes on; the line only tightens
            new = min(live["line"], p["line"]) if p["d"] < 0 else max(live["line"], p["line"])
            live["ps"].append(p)
            if new != live["line"]:
                live["line"] = new
                live["steps"].append([m, new])
        elif p:
            if live:
                live.update(e=m - 1, why="an opposite PUSH bar closed")
                bands.append(live)
            live = {"d": p["d"], "s": p["s"] // 60, "c": m, "line": p["line"], "steps": [[m, p["line"]]], "ps": [p]}
        b = O.get(m)
        if live and m >= live["c"] and b and (b["h"] >= live["line"] if live["d"] < 0 else b["l"] <= live["line"]):
            live.update(e=m, why="traded through the line")
            bands.append(live)
            live = None
    if live:
        live.update(e=None, why="still open at the replay's last minute")
        bands.append(live)

    out = []
    for n, b in enumerate(bands):
        end, legs = (last if b["e"] is None else b["e"]), []
        for p in b["ps"]:                                           # one LEG per push of the band: the same reads, from that push bar's open
            s = p["s"] // 60
            base = (O.get(s - 1) or O.get(s) or {}).get("oi")
            cq, blind, dl, oi, nm = 0, False, [], [], []
            for m in range(s, end + 1):
                blind = blind or m not in q1                        # a minute Dext has not sent: the total is not readable
                cq += q1.get(m, 0)
                o = (O.get(m) or {}).get("oi")
                dl.append(None if blind else round(cq / lot))
                oi.append(None if o is None or base is None else round((o - base) / lot))
                nm.append(name_of(dl[-1], oi[-1]))
            legs.append({"si": s - M0, "ci": p["close"] - M0, "t": p["t"], "origin": p["origin"], "U": round(p["U"], 1),
                         "line": round(p["line"], 1), "size": round(p["size"], 2), "R": round(p["R"], 2),
                         "dl": dl, "oi": oi, "nm": nm, "D0": D.get(s)})
        w = legs[0]                                                 # the first leg's running totals are the whole band's
        out.append({"id": n, "d": b["d"], "si": b["s"] - M0, "ci": b["c"] - M0, "ei": None if b["e"] is None else b["e"] - M0,
                    "why": b["why"], "steps": [[m - M0, round(v, 1)] for m, v in b["steps"]], "legs": legs,
                    "name": w["nm"][-1], "delta": w["dl"][-1], "oich": w["oi"][-1], "n": len(w["dl"])})

    forming, Fd, full, B5 = {}, ref.get("dext"), set(), []
    qs = ((Fd or {}).get("size") or {}).get("q")
    need = qs[hold2.BIG] if isinstance(qs, list) and len(qs) > hold2.BIG else None      # the size a 5-min bar needs to be a PUSH (the table's p90)
    for s in range(OPEN, last + 1, 5):                              # hold2.state on the bar as it stood at each minute's close
        for k in range(5):
            ms = range(s, s + k + 1)
            if not Fd or s + k > last or any(x not in O or x not in q1 for x in ms):
                continue
            bar = {"s": s * 60, "o": O[s]["o"], "h": max(O[x]["h"] for x in ms), "l": min(O[x]["l"] for x in ms),
                   "c": O[s + k]["c"], "vol": sum(O[x]["v"] or 0 for x in ms) / lot,
                   "delta": round(sum(q1[x] for x in ms) / lot), "src": "dext"}
            f = hold2.state(bar, Fd)
            if k == 4:                                              # v3: every closed 5-min bar's own size and R: "is this bar a PUSH against my trade?"
                o0, o1 = (O.get(s - 1) or O[s]).get("oi"), O[s + 4].get("oi")
                doi = None if not o0 or not o1 else (o1 - o0) / lot
                B5.append({"si": s - M0, "d": f["dir"], "pc": sgn(bar["c"] - bar["o"]), "st": f["state"],
                           "size": None if f["size"] is None else round(f["size"], 2), "R": None if f["R"] is None else round(f["R"], 2),
                           "pct": pct_of(qs, f["size"]), "doi": None if doi is None else round(doi),
                           "oip": None if doi is None else pct_of(oi_q.get(part_of(s)), abs(doi))})
            if f["state"] == "PUSH" and f["dir"]:
                if k == 4:
                    full.add(s)
                else:
                    forming[s + k - M0] = {"d": f["dir"], "si": s - M0, "size": round(f["size"], 2), "R": round(f["R"], 2)}
    assert full == {p["s"] // 60 for p in P}, "the closed-bar state and hold2.pushes disagree"     # the one self-check
    return {"lot": lot, "tag": tag, "ref_days": len((ref.get("dext") or {}).get("days") or []), "trail_u": hold2.TRAIL_U,
            "pushes": [{"t": p["t"], "ci": p["close"] - M0, "d": p["d"], "origin": p["origin"], "U": round(p["U"], 1),
                        "line": round(p["line"], 1), "size": round(p["size"], 2), "R": round(p["R"], 2)} for p in P],
            "bands": out, "forming": forming, "bars5": B5, "need": None if need is None else round(need, 2),
            "res_min": (Fd or {}).get("res_min") if (Fd or {}).get("res_min") is not None else hold2.RES_MIN,
            "oi_days": len(days), "oi_n": [sum(1 for pp, _ in oi_hist if pp == k) for k in range(4)],
            "win5": W5, "win_n": {str(k): len(v) for k, v in sorted(tabD.items())}}, P, O


# ---- option order flow (optflow/optladder.py) ----------------------------------------------------------------------------
def opt_layer(day, frame, M0, last):
    sys.path.insert(0, os.path.join(ROOT, "optflow"))
    import optladder
    d = optladder.build(day, IDX, upto=last)
    if not d.get("ok"):
        return {"ok": False, "why": d.get("why") or "no option flow for this day", "closes": [], "changes": [],
                "up": optladder.UP, "first": optladder.hm(optladder.FIRST_WHO)}
    closes = []
    for k in sorted(d["closes"], key=int):
        r, m = d["closes"][k], int(k)
        g = {x: {y: r["groups"][x][y] for y in ("word", "doi", "delta", "known", "n")} for x in ("CAP", "FLOOR")}
        closes.append({"t": r["t"], "i": m - M0, "ki": m + 1 - M0, "said": r["said"], "lean": r["lean_said"], "raw": r["word"],
                       "lr": r["lean"], "cover": r.get("cover"),    # v2: this close's own lean, and optladder's ">= COVER_N strikes covering"
                       "cap": g["CAP"], "floor": g["FLOOR"], "atm": r["atm"], "why": " · ".join(r.get("why") or []),
                       "walls": {s: w and {"k": w["k"], "oi": w["oi"], "state": w["state"], "who": w.get("who")}
                                 for s, w in r["walls"].items()},
                       "st": {kk: [w["who"], w["firm"], w["doi"], w["delta"], w["oi"]] for kk, w in r["strikes"].items()}})
    changes, prev = [], None
    for c in closes:                                                # the said word (optladder's own two-close rule) changed
        if c["said"] != prev:
            sc = {s: abs(optladder.UP[g].get(c[key]["word"], 0)) for s, g, key in (("ce", "CAP", "cap"), ("pe", "FLOOR", "floor"))}
            near = sorted((s for s in ("ce", "pe") if c["walls"].get(s)),
                          key=lambda s: abs(c["walls"][s]["k"] - (frame["spot"][c["i"]] or 0)))
            side = "ce" if sc["ce"] > sc["pe"] else "pe" if sc["pe"] > sc["ce"] else (near[0] if near else None)
            w = c["walls"].get(side) if side else None              # the wall of the group that carries the word; a tie: the nearer
            changes.append({"t": c["t"], "i": c["i"], "ki": c["ki"], "said": c["said"], "lean": c["lean"], "raw": c["raw"],
                            "k": w and w["k"], "ws": side and side.upper(), "capw": c["cap"]["word"], "floorw": c["floor"]["word"]})
        prev = c["said"]
    return {"ok": True, "expiry": d.get("expiry"), "thresholds": d.get("thresholds"), "first": optladder.hm(optladder.FIRST_WHO),
            "up": optladder.UP, "closes": closes, "changes": changes, "shadow": d.get("shadow")}


# ---- the sync lane -------------------------------------------------------------------------------------------------------
def sync_layer(frame):
    N, bars, hist = len(frame["mins"]), [], ([], [], [])
    series = ((frame["fut"], frame.get("fo")), (frame.get("bnf") or [None] * N, None), (frame.get("sx") or [None] * N, None))
    for a in range(0, N - 2, 3):
        row = []
        for n, (cl, op) in enumerate(series):
            o = op[a] if op else cl[a - 1] if a else cl[a]          # a spot series opens at the minute before's last print
            c = cl[a + 2]
            if o is None or c is None:
                row.append(None)                                    # could not read: never a zero
                continue
            ch, med = c - o, statistics.median(hist[n]) if hist[n] else None
            row.append([round(ch, 1), bool(med is not None and abs(ch) < med), None if med is None else round(med, 1)])
            hist[n].append(abs(ch))
        s = [None if c is None else sgn(c[0]) for c in row]
        bars.append({"a": a, "v": row, "all": None if None in s else s[0] if s[0] and s[0] == s[1] == s[2] else 0})
    lead = next((k for k in ("xindex", "x2", "x3", "X2", "X3") if k in frame), None)
    return {"bars": bars, "lead": f"lead / lag: frame field `{lead}` present, not drawn" if lead else "lead / lag: not in this frame",
            "rows": ["N f", "BN s", "SX s"]}


# ---- the DEMO trade ------------------------------------------------------------------------------------------------------
def trade_layer(frame, mv, P, O, opt, M0, last):
    zs = [z for z in frame.get("zone") or [] if not z.get("kind")]
    if not zs:
        return None
    z = zs[0]                                                       # the day's first zone trigger (11 Nov: the 09:48 SELL)
    d, px = (-1 if z["side"] == "SELL" else 1), z["px"]
    zc = next((c for c in frame.get("zone_cards") or [] if c.get("t") == z["t"] and c.get("side") == z["side"]), None) or {}
    e = m_of(zc.get("close") or hm(m_of(z["t"]) + 2))               # entry = the trigger bar's close (its px is that close)
    stop = zc.get("stop")
    stops = [[e + 1 - M0, stop, "the zone machine's stop"]] if stop is not None else []
    voice, exit_, said = [], None, stop
    for m in range(e + 1, last + 1):
        p = next((p for p in P if p["close"] == m and p["d"] == d), None)
        if p:                                                       # a with-side push closed after entry: its line, toward price only
            new = p["line"] if stop is None else min(stop, p["line"]) if d < 0 else max(stop, p["line"])
            if new != stop:
                stop = new
                stops.append([m - M0, round(stop, 1), f"HOLD v2 line · the {p['t']} push"])
        b = O.get(m)
        if stop is not None and b and (b["h"] >= stop if d < 0 else b["l"] <= stop):
            exit_ = {"i": m - M0, "t": hm(m), "stop": round(stop, 1), "pts": round(d * (stop - px), 1)}
            voice.append({"i": m + 1 - M0, "t": hm(m), "w": "EXIT", "why": f"traded through {stop:,.1f}f at {hm(m)}"})
            break
        if (m - OPEN) % 3 != 2 or b is None:
            continue
        i, warn = m - M0, None                                      # her 3-min close: EXIT > WARN > TIGHTEN > HOLD
        f = mv["forming"].get(i)
        ab = next((x for x in mv["bands"] if x["d"] == -d and x["ci"] <= i + 1 and (x["ei"] is None or x["ei"] >= i)), None)
        r = next((c for c in reversed(opt["closes"]) if c["i"] <= i), None)
        if f and f["d"] == -d:
            warn = f"against-side band {arr(-d)} forming since {frame['mins'][f['si']]}"
        elif ab:
            warn = f"against-side band {arr(-d)} live since {frame['mins'][ab['si']]}"
        elif r and r["lean"] == -d:
            warn = f"option flow {r['said']} against · as of {r['t']}"
        w = "WARN" if warn else "HOLD" if stop == said else "TIGHTEN"
        pts = d * (b["c"] - px)
        voice.append({"i": i + 1, "t": hm(m), "w": w, "why": warn or (
            f"with-side push moved the stop to {stop:,.1f}f" if w == "TIGHTEN" else
            f"stop {stop:,.1f}f · {pts:+.0f} pts" if stop is not None else "no stop on the record yet")})
        said = stop
    atm = int(round(frame["spot"][e - M0] / frame.get("step", 50)) * frame.get("step", 50)) if frame["spot"][e - M0] else None
    try:                                                            # v3: her zone machine's own stop distance, the "tight trail" the hold strip counts
        import band_rotation
        trail_pts = band_rotation.OPERATOR_STOP_PTS
    except Exception:
        trail_pts = None
    # ---- the BOOK / TRAIL line v2 (docs/jarvis-panel/BOOK-TRAIL-V2-DEFINITION.md, written before this ran), and the old line as it is
    mins, fut, hi, lo, spot = frame["mins"], frame["fut"], frame["fhi"], frame["flo"], frame["spot"]
    vw, sd, tl = frame.get("vwap"), frame.get("sd"), frame.get("timeline") or []
    ei, xi = e - M0, (exit_["i"] if exit_ else last - M0)
    book, seen, best, armed, hits = [], set(), px, True, 0
    climax = {b["si"] + 5: b for b in mv["bars5"] if b["st"] == "CLIMAX" and b["d"] == d}
    trail_at = {s[0]: s for s in stops[1:]}
    far = (("VWAP", 0), ("u1", 1), ("u2", 2), ("u3", 3)) if d > 0 else (("VWAP", 0), ("d1", -1), ("d2", -2), ("d3", -3))

    def say(i, w, why, **kw):
        book.append(dict({"i": i, "t": mins[i], "w": w, "why": why, "px": fut[i], "pts": round(d * (fut[i] - px), 1)}, **kw))

    for i in range(ei + 1, min(xi, len(mins) - 1) + 1):
        if hi[i] is None or lo[i] is None or fut[i] is None:
            continue
        fav, adv = (hi[i], lo[i]) if d > 0 else (lo[i], hi[i])
        was_best = best                                              # "ahead" = beyond the trade's best price BEFORE this minute (a place it has not been to)
        if (fav - best) * d > 0:
            best, armed = fav, True
        if trail_pts is not None and armed and (best - adv) * d >= trail_pts:
            hits, armed = hits + 1, False
        band_ok = bool(vw and sd and vw[i] is not None and sd[i])
        if band_ok:
            for name, k in far:                                      # B1: VWAP first, then band to band
                lv = vw[i] + k * sd[i]
                if name not in seen and (lv - px) * d > 0 and (fav - lv) * d >= 0:      # a band is a moving level: "reached" is the event (§2 B1)
                    seen.add(name)
                    say(i, "BOOK", f"{name} reached", place=name, lvl=round(lv, 1))
        bs = None if spot[i] is None else fut[i] - spot[i]
        for f in (((tl[i] or {}).get("fronts") or []) if bs is not None and i < len(tl) else []):       # B2: a wall ahead
            if f.get("side") != ("CE" if d > 0 else "PE"):
                continue
            lv, key = f["k"] + bs, f"{int(f['k'])}{f['side']}"
            if key not in seen and (lv - px) * d > 0 and (lv - was_best) * d >= 0 and (fav - lv) * d >= 0:
                seen.add(key)
                say(i, "BOOK", f"at the wall {int(f['k']):,}s {f['side']} ({str(f.get('state') or '?').lower()})", place=key, lvl=round(lv, 1))
        c = climax.get(i)                                            # B3: her side's effort stopped getting a result
        if c:
            say(i, "BOOK", f"your side's CLIMAX bar {mins[c['si']]}: size x{c['size']}, price did not follow (R {c['R']})", place="climax")
        s = trail_at.get(i)                                          # TRAIL: a new push on her side gives a new line; two choices
        if s:
            tight = None
            if band_ok:
                bands = [(n, vw[i] + k * sd[i]) for n, k in (("d2", -2), ("d1", -1), ("VWAP", 0), ("u1", 1), ("u2", 2))]
                tight = next((b for b in bands if b[1] > fut[i] + 3), None) if d < 0 else next((b for b in reversed(bands) if b[1] < fut[i] - 3), None)
            say(i, "TRAIL", f"structure line {s[1]:,.1f}f, {abs(s[1] - fut[i]):.0f} pts away"
                + (f" · tight choice {tight[0]} {tight[1]:,.1f}f, {abs(tight[1] - fut[i]):.0f} pts away" if tight else "")
                + (f" · a {trail_pts:.0f}-pt trail hit {hits}x so far, the line 0x" if trail_pts is not None else ""), line=s[1])
    old = [{"b": m["b"], "at": m["at"], "st": m["st"], "pts": m["pts"], "trail": m.get("trail"), "against": m.get("against") or [], "with": m.get("with") or []}
           for m in (frame.get("reads") or {}).get("manage") or [] if m.get("t") == z["t"][:5] and m.get("side") == z["side"]]
    return {"t": z["t"], "side": z["side"], "d": d, "px": px, "band": z.get("band"), "ei": e - M0, "stops": stops, "exit": exit_, "trail_pts": trail_pts,
            "book": book, "old": old,
            "voice": voice, "strike": None if atm is None else {"k": atm, "side": "CE" if d < 0 else "PE"}}


# ---- the page ------------------------------------------------------------------------------------------------------------
CSS = r"""
/* ================= JARVIS 3 mockup (build_jarvis3.py): one type scale 10 / 11 / 13 / 16 / 22 (canvas 9 / 10), one chip,
   four meaning colours (up, down, amber = warn / forming, ink) + the Jarvis accent, an 8 px grid (4 px half-steps). LIGHT only. */
:root{--warn:#b7791f;--warnbg:#fdf3dc;--ce:#e5484d;--pe:#0f9d76;--you:#d97757;--band:#6b7280;--f1:10px;--f2:11px;--f3:13px;--f4:16px;--f5:22px}
html,body{font:var(--f3)/1.4 var(--sans);font-variant-numeric:tabular-nums}
button{font-size:var(--f2);padding:4px 8px;border-radius:6px}
.num,.clock,.qt .v,.cell .v,.cell .s{font-variant-numeric:tabular-nums}
.bar{gap:4px 16px;padding:4px 16px;flex-wrap:wrap;min-height:48px}
.brand{font-size:var(--f3);gap:8px} .brand small{font-size:var(--f2)}
.clock{font:700 var(--f5)/1 var(--mono)}
.ctl{gap:8px;flex-wrap:wrap} .ctl .grp{border-radius:6px} .ctl .grp button{padding:4px 8px}
.quotes{gap:16px;font-size:var(--f2)} .qt .k{font-size:var(--f1)} .qt .v{font:700 var(--f3) var(--mono)} .qt .v small{font:500 var(--f2) var(--mono)}
#demoT.on{background:var(--warn);border-color:var(--warn);color:#fff}
#walk.on{background:var(--ai);border-color:var(--ai)}
main{gap:8px;padding:8px}
.left{grid-template-rows:auto auto minmax(0,1fr) auto auto;gap:8px}
#stage{min-height:300px;border-radius:8px} #tl{border-radius:8px}
/* the top strip: equal cards, three ONE-LINE rows (label / value / sub-line), as on the live page: the height goes to the chart; the whole text is on hover */
.strip,.strip.h7{display:grid;grid-template-columns:none;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr);gap:8px}
.cell{border-radius:8px;padding:4px 8px 7px;display:grid;grid-template-rows:auto auto auto;align-content:start}
.cell[hidden]{display:none}
.cell .k{font-size:var(--f1)}
.cell .v{font:700 var(--f3)/1.25 var(--mono);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cell .s{font:500 var(--f1)/1.3 var(--mono);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cell .meter{position:absolute;left:8px;right:8px;bottom:2px;height:3px;margin:0}
.cell .v .pill{display:inline-block;max-width:100%;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:0 6px;font-size:var(--f1);vertical-align:bottom}
#b1 .pa{font:600 var(--f2)/1.35 var(--mono);margin-top:4px;overflow-wrap:anywhere} #b1 .pa .lab{margin-right:8px}
#b1 .word small{font:600 var(--f2)/1.2 var(--mono);color:var(--mut);white-space:nowrap}
.tgrid .up{color:var(--up)} .tgrid .dn{color:var(--dn)}
/* v3, HOLD mode: the strip that answers "is anything broken?" */
.strip[hidden]{display:none} .left{grid-template-rows:auto auto minmax(0,1fr) auto auto}
#layers{order:0} .strip.hold{order:-1}
.strip.hold .cell{border-color:#d9d5cb;box-shadow:inset 0 2px 0 var(--ink)}
.strip.hold .cell .s{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;min-height:26px}   /* the hold strip never hides its reason: two lines */
.strip.hold .cell:first-child{box-shadow:inset 0 2px 0 var(--warn)}
.strip.hold .v small{font:500 var(--f1) var(--mono);color:var(--mut)} .strip.hold .v small.dn{color:var(--dn)}
.strip.hold .v.up{color:var(--up)} .strip.hold .v.dn{color:var(--dn)} .strip.hold .v.wn{color:var(--warn)} .strip.hold .v.q{color:var(--ink)}
.hw{font:700 var(--f4)/1.1 var(--mono)} .hw.up{color:var(--up)} .hw.wn{color:var(--warn)} .hw.dn{color:var(--dn)}
.zl{font:600 var(--f2)/1.35 var(--mono);margin-top:2px;overflow-wrap:anywhere} .zl.q{font-weight:500;color:var(--mut)} .zl .up{color:var(--up)} .zl .dn{color:var(--dn)}
#b4 .zl{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}   /* one row a line, so the block's height never pushes the log out; the whole text is on hover */
/* ONE chip */
.chip,.pill,.rtag,.badge,.tag,.c1,.rp{font:600 var(--f2)/1.3 var(--mono);padding:2px 8px;border-radius:6px;border:1px solid var(--line);background:#f6f4ef;color:var(--ink);letter-spacing:0;display:inline-block}
.chip.ok,.pill.ok,.rtag.ok,.c1.ok,.badge.live{color:var(--up);border-color:#bfe6d8;background:#effaf5}
.chip.bad,.pill.bad,.rtag.bad,.c1.bad,.badge.stale{color:var(--dn);border-color:#f6c9cb;background:#fdf1f1}
.chip.warn,.pill.warn,.rtag.warn,.c1.warn,.badge.back{color:var(--warn);border-color:#ecd9a8;background:var(--warnbg)}
.chip.q,.pill.q,.rtag.q,.c1.q,.badge.blind,.badge.replay,.badge{color:var(--mut);border-color:var(--line);background:#f6f4ef}
.chip.you,.rtag.you{color:var(--ink);border-color:var(--line);background:#f1eee7}
.c1[hidden]{display:none}
.rc .chip{font-size:var(--f1)} .phead .who{font-size:var(--f2)}
.rp{color:#a8a59d;background:#fff;cursor:pointer}
.rp.lit{color:var(--ink);border-color:var(--ai);box-shadow:0 0 0 2px rgba(217,119,87,.12)} .rp.now{background:var(--ai);color:#fff;border-color:var(--ai)}
@media (prefers-reduced-motion: reduce){.chip{opacity:1;transform:none}}
/* the mark-layer switches and the log filter */
#layers{display:flex;align-items:center;gap:4px 8px;flex-wrap:wrap;min-height:24px}
.lk{font:700 var(--f1)/1.3 var(--sans);letter-spacing:.09em;color:var(--mut)}
.lg{font:500 var(--f1)/1.3 var(--mono);color:var(--mut)}
.sw{font:600 var(--f1)/1.3 var(--mono);padding:2px 6px;border-radius:6px;color:var(--mut)}
.sw.on{background:var(--ink);color:#fff;border-color:var(--ink)}
#rail{gap:4px;font-size:var(--f2)} .legend{font-size:var(--f1)}
#tip{border-radius:8px;padding:8px;font-size:var(--f2);max-width:340px;z-index:14}
.tg{display:grid;grid-template-columns:auto minmax(0,1fr);gap:0 12px;font:500 var(--f2)/1.45 var(--mono);margin-top:4px}
.tg span:nth-child(odd){color:var(--mut)}
/* the Jarvis window: drag by its header, pin, resize, collapse to a one-line pill */
.bubble{padding:8px 12px 12px;border-radius:12px;display:flex;flex-direction:column}
.bubble::before{border-radius:13px}
.bubble.drag{transition:none}
.bhead{cursor:grab;gap:8px;margin-bottom:4px;user-select:none;touch-action:none}
.bubble.drag .bhead{cursor:grabbing}
.bhead .orb,.bhead .who{flex:none} .bhead .tag{min-width:0;overflow:hidden;text-overflow:ellipsis}
.who{font-size:var(--f2)} .who .tm{font:600 var(--f2) var(--mono)}
.bbtn{display:flex;gap:4px;flex:none} .bbtn button{padding:0 6px;font:600 var(--f1)/18px var(--mono);height:20px}
.bbtn button.on{background:var(--ai);border-color:var(--ai);color:#fff}
.bbody{min-height:0;flex:1 1 auto} .bubble.sized .bbody{overflow:auto}
.bline{font:600 var(--f2)/1.35 var(--mono);padding:4px 8px;border-radius:6px;margin-bottom:4px;background:var(--soft);border-left:3px solid var(--ink)}
.bline[hidden]{display:none}
.bline.up{border-left-color:var(--up)} .bline.dn{border-left-color:var(--dn)} .bline.warn{border-left-color:var(--warn);background:var(--warnbg)}
.btext{font-size:var(--f3)} .bubble.quiet .btext{font-size:var(--f3)}
.bnext,.rn{font-size:var(--f2)}
.bpill{display:none;font:600 var(--f2)/1.3 var(--mono);white-space:nowrap}
.bubble.pillm{width:max-content!important;height:auto!important;padding:4px 8px}
.bubble.pillm .bbody,.bubble.pillm .bgrip,.bubble.pillm .tag{display:none}
.bubble.pillm .bhead{margin:0} .bubble.pillm .bpill{display:inline} .bubble.pillm .orb{width:20px;height:20px}
.bgrip{position:absolute;right:3px;bottom:3px;width:12px;height:12px;cursor:nwse-resize;touch-action:none;border-right:2px solid var(--ai2);border-bottom:2px solid var(--ai2);border-radius:0 0 8px 0}
/* the right panel: five fixed blocks, never wider than before (372 px) */
.panel{display:flex;flex-direction:column;border-radius:8px;overflow:hidden auto}
.phead{padding:4px 12px;gap:8px;flex:none}
.blk{padding:6px 12px;border-bottom:1px solid var(--line);min-width:0;flex:none}
.blk[hidden]{display:none}
.blk>.k{font:700 var(--f1)/1.3 var(--sans);letter-spacing:.09em;color:var(--mut);display:flex;justify-content:space-between;align-items:center;gap:8px}
.blk>.k i{font-style:normal;font-weight:500;letter-spacing:0}
.lab{font:700 var(--f1)/1.3 var(--sans);letter-spacing:.09em;color:var(--mut)}
#b1 .word{font:700 var(--f5)/1.15 var(--mono);margin-top:2px;overflow-wrap:anywhere}
#b1 .act{display:flex;align-items:baseline;gap:8px;margin-top:2px;flex-wrap:wrap}
#b1 .act b{font:700 var(--f4)/1.2 var(--mono)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.two .v{font:700 var(--f4)/1.25 var(--mono);overflow-wrap:anywhere} .two .s{font:500 var(--f1)/1.3 var(--mono);color:var(--mut);overflow-wrap:anywhere}
.agree{display:grid;grid-template-columns:auto 56px minmax(0,1fr);gap:2px 8px;align-items:baseline;margin-top:2px}
.agree .n{font:600 var(--f2)/1.3 var(--sans)}
.pw{font:700 var(--f1)/1.3 var(--mono);text-align:center;padding:1px 0;border-radius:6px;border:1px solid var(--line);color:var(--mut)}
.pw.ok{color:var(--up);border-color:#bfe6d8;background:#effaf5} .pw.bad{color:var(--dn);border-color:#f6c9cb;background:#fdf1f1}
.pw.warn{color:var(--warn);border:1px dashed #d9bd77;background:var(--warnbg)}
.agree .t{font:500 var(--f2)/1.3 var(--mono);overflow-wrap:anywhere} .agree .t b{font-weight:700} .agree .t i{font-style:normal;font-size:var(--f1);color:var(--mut)}
#b4{background:var(--soft)}
.tgrid{display:grid;grid-template-columns:1fr 1fr;gap:4px 8px;margin-top:2px}
.tgrid .w{grid-column:1 / -1}
.tgrid .n{display:block;font:700 var(--f1)/1.3 var(--sans);letter-spacing:.09em;color:var(--mut);text-transform:uppercase}
.tgrid .t{display:block;font:600 var(--f2)/1.35 var(--mono);overflow-wrap:anywhere}
.tgrid .t i{font-style:normal;font-weight:500;font-size:var(--f1);color:var(--mut)} .tgrid .big{font:700 var(--f4)/1.1 var(--mono)}
.det>summary{cursor:pointer;font:700 var(--f1)/1.3 var(--sans);letter-spacing:.09em;color:var(--mut);list-style:none}
.det>summary::-webkit-details-marker{display:none}
.det .ar{display:inline-block} .det[open] .ar{transform:rotate(90deg)}
.detb{max-height:36vh;overflow:auto;margin-top:8px}
.det .trade{padding:0 0 8px;border:0;background:none}
#callc .big,.trade .cnt,.trade .s.clip,.trade .s.clip2{white-space:normal;overflow:visible;text-overflow:clip;display:block;-webkit-line-clamp:unset;line-clamp:unset;overflow-wrap:anywhere}
.trade .big{font:700 var(--f4)/1.2 var(--mono)} .trade .big small{font:600 var(--f2) var(--mono)} .trade .v,.trade .cnt{font:700 var(--f3) var(--mono)}
.trade .s{font:500 var(--f2)/1.35 var(--mono)} .trade .k{font-size:var(--f1)}
.feedh{display:flex;align-items:center;gap:4px 8px;flex-wrap:wrap;padding:6px 12px 4px;flex:none}
.feed{flex:1 0 96px;min-height:96px;display:block;padding:0 8px 4px}
.row{display:block;padding:3px 8px;border:0;border-left:3px solid transparent;border-bottom:1px solid var(--grid);border-radius:0;animation:none;background:none;line-height:1.45}
.row:hover{background:var(--soft)}
.row.major{border-left:3px solid var(--ai)} .row.bad{border-left-color:var(--dn)} .row.ok{border-left-color:var(--up)} .row.warn{border-left-color:var(--warn)} .row.q{border-left-color:#c7c7c7}
.row.you{background:var(--soft);border:0;border-left:3px solid var(--ink);border-bottom:1px solid var(--grid)}
.rt{font:700 var(--f2)/1.45 var(--mono);margin-right:6px} .row .rtag{font-size:var(--f1);padding:0 6px;margin-right:6px}
.rx{font:500 var(--f2)/1.45 var(--mono);white-space:normal;overflow-wrap:anywhere}
.row .ex{display:inline-flex;gap:4px;margin-left:6px;vertical-align:baseline} .row .ex .c1{font-size:var(--f1);padding:0 6px}
.rsrc{margin:0;font:500 var(--f1) var(--mono)}
#feed[data-f="moves"] .row:not([data-cat="moves"]),#feed[data-f="walls"] .row:not([data-cat="walls"]),
#feed[data-f="opt"] .row:not([data-cat="opt"]),#feed[data-f="trade"] .row:not([data-cat="trade"]){display:none}
.cmd{padding:4px 8px;gap:8px;flex:none} .cmd input{font:500 var(--f2) var(--mono);padding:6px 8px;border-radius:6px}
/* the walk and the overlays, on the same scale and colours */
#walkp{border:1px solid rgba(217,119,87,.45);border-top:3px solid var(--ai);border-radius:8px;padding:8px 12px}
.wtabs button{font:600 var(--f2) var(--mono)} .wtabs button.cur{background:#fdf0e8;border-color:var(--ai);color:var(--ai)}
.wbody{border-left-color:var(--ai);padding:8px} .wtext{font-size:var(--f3)} .wteach{font-size:var(--f2);padding:8px} .wteach .h{font:700 var(--f2) var(--mono);color:var(--ai)}
.wq button{border-radius:6px;font-size:var(--f2);color:var(--ai);border-color:#f2d3c4;background:#fdf6f2}
.wans{font-size:var(--f2);background:#fdf6f2;padding:8px} .wfoot,#wCnt{font:500 var(--f1) var(--mono)} .wprog i{background:var(--ai)}
.card{border-radius:16px;padding:24px 32px} .card h1{font-size:var(--f5)} .card p{font-size:var(--f3)}
.card .go{font-size:var(--f3);padding:8px 24px;border-radius:8px} .card .keys{font:500 var(--f2) var(--mono)}
.review h1{font-size:var(--f4)} .review h1 small{font:500 var(--f2) var(--mono)} .story{font:600 var(--f2) var(--mono)}
.rsec h3{font-size:var(--f1)} .endtab{font:500 var(--f2) var(--mono)} .endtab th{font-size:var(--f1)} .review .foot{font-size:var(--f2)}
@media (max-width:1180px){.strip,.strip.h7{grid-template-columns:none}}
"""

LAYERS = """    <div id="layers"><span class="lk">MARKS</span>
      <button class="sw" data-ly="pa" title="price action: the confirmed swings (H · HL · LH · LL), the running leg, and each break of the last swing">Price action</button><button class="sw" data-ly="zones" title="her VWAP bands, the d2-d3 / u2-u3 zones and the trigger marks">Zones</button><button class="sw" data-ly="walls" title="the writers' walls and their axis tags">Walls</button><button class="sw" data-ly="marks" title="pushes and the wall's answers: HELD · DEFENDED · TRAPPED · BROKEN">Marks</button><button class="sw" data-ly="bands" title="move bands: a run from a PUSH bar's open until price trades through its line">Move bands</button><button class="sw" data-ly="opt" title="option order flow: WHO per strike, CE | PE (a solid chip = FIRM), and the cap / floor word on the chart">Option flow</button><button class="sw" data-ly="sync" title="N · BN · SX, one cell per 3-min bar">Sync lane</button><button class="sw" data-ly="str" title="STRENGTH v2 (shadow): a 0-100 number for buyers and for sellers from five kinds of evidence, each measured over the last 40 minutes. Not a chance of winning.">Strength %</button><button class="sw" data-ly="hist" title="off = the NOW view: only the marks of the swing in play. On = every mark of the day, the older ones quieter (HELD chips included)">History</button>
      <span class="lg">NOW view: marks of the swing in play · the rest is on the day map and in the log</span></div>
    <div class="strip hold" id="hstrip" hidden></div>
"""

BUBBLE_OLD = """      <div id="bubble" class="bubble">
        <div class="bhead"><div class="orb" id="orb"></div><div class="who">JARVIS<span class="tm" id="btm">09:15</span></div><span class="tag" id="btag">LIVE</span></div>
        <div class="btext" id="btext"></div>
        <div class="bchips" id="bchips"></div>
        <div class="bnext" id="bnext"></div>
      </div>
"""
BUBBLE_NEW = """      <div id="bubble" class="bubble">
        <div class="bhead" id="bhead" title="drag to move"><div class="orb" id="orb"></div><div class="who">JARVIS<span class="tm" id="btm">09:15</span></div><span class="tag" id="btag">LIVE</span><span class="bpill" id="bpill"></span>
          <span class="bbtn"><button id="bPin" title="follow the candle / stay where I put it">follow</button><button id="bCol" title="collapse to one line">–</button></span></div>
        <div class="bbody" id="bbody">
          <div class="bline" id="bmeter" hidden></div>
          <div class="bline" id="bvoice" hidden></div>
          <div class="bline" id="bline" hidden></div>
          <div class="btext" id="btext"></div>
          <div class="bchips" id="bchips"></div>
          <div class="bnext" id="bnext"></div>
        </div>
        <div class="bgrip" id="bGrip" title="drag to resize · double-click to reset"></div>
      </div>
"""

PANEL_OLD = """    <div class="trade" id="callc" hidden></div>
    <div class="trade" id="trade"><div class="k">LAST TRIGGER <i>guidance only</i></div><div class="v" id="tV">no trigger yet</div><div class="big" id="tP">—</div><div class="s" id="tS">zone: d2→d3 buy · u2→u3 sell · 3-min bands</div></div>
    <div class="feed" id="feed"></div>
"""
PANEL_NEW = """    <div class="blk" id="b1"><div class="k"><span>THE WORD</span><i id="s1"></i></div><div class="word" id="w1">—</div>
      <div class="act"><span class="lab">ACTION</span><b id="a1">—</b><span class="c1 q" id="a1s" hidden></span></div>
      <div class="pa" id="pa1" title="price action: the last two confirmed swings, a break of the last swing, and where price sits on your bands"></div></div>
    <div class="blk" id="b2" title="two prices · f = futures · s = spot">
      <div class="two"><div><div class="lab">WRONG IF</div><div class="v" id="p1">—</div><div class="s" id="p1s"></div></div>
        <div><div class="lab">ROOM TO</div><div class="v" id="p2">—</div><div class="s" id="p2s"></div></div></div></div>
    <div class="blk" id="b3"><div class="k"><span>WHO AGREES <i id="g0"></i></span><span class="c1 q" id="gAll">ALL 3 —</span></div><div class="agree" id="agree"></div></div>
    <div class="blk" id="b4" hidden></div>
    <details class="blk det" id="det"><summary>detail <span class="ar">▸</span> the full call card · last trigger</summary><div class="detb">
      <div class="trade" id="callc" hidden></div>
      <div class="trade" id="trade"><div class="k">LAST TRIGGER <i>guidance only</i></div><div class="v" id="tV">no trigger yet</div><div class="big" id="tP">—</div><div class="s" id="tS">zone: d2→d3 buy · u2→u3 sell · 3-min bands</div></div>
    </div></details>
    <div class="feedh" title="click a line to jump the replay to it"><span class="lk">EVENT LOG</span><span id="fchips"><button class="sw" data-f="all">all</button> <button class="sw" data-f="moves">moves</button> <button class="sw" data-f="walls">walls</button> <button class="sw" data-f="opt">option flow</button> <button class="sw" data-f="trade">trade</button></span></div>
    <div class="feed" id="feed"></div>
"""

JS = r"""
/* ================================================================== JARVIS 3 mockup layers (build_jarvis3.py) ==
   Added to a copy of jarvis2.html; the page's own code above is its own, with a hook call where a layer plugs in.
   window.J3DATA.frame = the /api/jarvis replay frame, inlined; .x = move bands (ruler.py + hold2.py), option flow
   (optflow/optladder.py), the sync lane and the DEMO trade, all computed from the record by the build script.
   A read made at a minute's close shows one minute later (causal). Advisory only: nothing here places or simulates an order. */
const J3 = window.J3DATA.x;
const LS = {
  get(k, d) { try { const v = localStorage.getItem("jarvis3." + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem("jarvis3." + k, JSON.stringify(v)); } catch (e) { /* no storage: the page still works */ } }
};
const LY = Object.assign({pa: true, zones: true, walls: true, marks: true, bands: true, opt: true, sync: true, str: false, hist: false}, LS.get("layers", null) || {});   // str off: STRENGTH v1 failed its own shadow count (it moved at 118 of 125 closes); the switch shows it
const NOLIVE = J3.live ? {bands: J3.opt.why, opt: J3.opt.why, str: "shadow only: the strength % failed its written test twice; it stays on the mockup"} : {};   // the live page: layers the server does not send yet
for (const k in NOLIVE) LY[k] = false;
const WIN = Object.assign({pin: false, x: null, y: null, w: null, h: null, col: false}, LS.get("win", null) || {});
let DEMO = false, FILT = LS.get("filt", "all"), sTop = 0, pillTxt = null;
const WHOW = 74, LADR = WHOW + 18, LBL = [], HIT = [], BOX = new Map();
const laneH = () => LY.sync || LY.opt || LY.str ? 14 + (LY.str ? 12 : 0) + (LY.opt ? 10 : 0) + (LY.sync ? 30 : 0) : 0;   // the lanes under the candles: STR + OPT + N / BN / SX
/* ---- STRENGTH v1 (shadow): docs/jarvis-panel/STRENGTH-METER-DEFINITION.md, written before it ran. The build script computes it; the page only shows it. */
const MR = (J3.meter && J3.meter.rows) || [], FAMN = {flow: "flow", pos: "positions", wr: "writers", opt: "options", all3: "all three"};
function meterAt(i) { let n = -1; for (let k = 0; k < MR.length && MR[k].ki <= i; k++) n = k; return n < 0 ? null : {r: MR[n], p: n ? MR[n - 1] : null}; }
function meterSay(i) {              // the side in play (her trade's side in HOLD mode, else the larger number): its number, the arrow, the word, the high
  const m = meterAt(i); if (!m) return null;
  const last = {"1": [0, -1, -1], "-1": [0, -1, -1]}; let side = 0;   // v2 §4, the sticky word: per side [direction of its last change, that row, the row of its last rise]
  for (let k = 0; k < MR.length && MR[k].ki <= i; k++) { const r = MR[k], p = k ? MR[k - 1] : null;
    if (p) for (const [s, key] of [[1, "up"], [-1, "dn"]]) if (r[key] !== p[key]) { const dd = r[key] > p[key] ? 1 : -1; last[s][0] = dd; last[s][1] = k; if (dd > 0) last[s][2] = k; }
    side = r.up > r.dn ? 1 : r.dn > r.up ? -1 : side; }
  const d = HOLDM ? J3.trade.d : side;
  if (!d) return {d: 0, c: "", t: `STRENGTH · buyers ${m.r.up}% · sellers ${m.r.dn}% · even`, fam: ""};
  const me = d > 0 ? m.r.up : m.r.dn, ot = d > 0 ? m.r.dn : m.r.up, pm = m.p ? (d > 0 ? m.p.up : m.p.dn) : null, po = m.p ? (d > 0 ? m.p.dn : m.p.up) : null;
  const lm = last[d], lo = last[-d], w = ot > me ? "TURNING" : lo[0] > 0 && lo[1] > lm[2] ? "CONTESTED" : lm[0] > 0 ? "BUILDING" : lm[0] < 0 ? "RESTING" : "STEADY";
  const from = HOLDM ? J3.trade.ei + 1 : HIST; let hi = me; for (const r of MR) if (r.ki > from && r.ki <= i) hi = Math.max(hi, d > 0 ? r.up : r.dn);
  const arrow = pm == null || me === pm ? "" : me > pm ? ` ▲ from ${pm}%` : ` ▼ from ${pm}%`;
  return {d, me, ot, w, hi, c: w === "TURNING" ? "dn" : w === "CONTESTED" ? "warn" : d > 0 ? "up" : "dn",
    t: `${d > 0 ? "BUYERS" : "SELLERS"} ${me}%${arrow} · ${d > 0 ? "sellers" : "buyers"} ${ot}% · ${w} · high ${hi}%`,
    fam: Object.entries(m.r.fam).map(([k, v]) => `${FAMN[k]} ${v == null ? "not read" : v[d > 0 ? 0 : 1]}`).join(" · ") + (m.r.n < 5 ? ` · ${m.r.n} of 5 read` : "")};
}
const meterTip = r => `<b>${r.t} close · strength v2 (shadow) · over the last ${r.k * 5} min</b>` + tg([["buyers", `${r.up}%`], ["sellers", `${r.dn}%`]]
  .concat(Object.entries(r.fam).map(([k, v]) => [FAMN[k], v == null ? "not read" : `buyers ${v[0]} · sellers ${v[1]}`]), [["read", `${r.n} of 5 families · the plain average`]]));
const f1 = v => v.toLocaleString("en-IN", {minimumFractionDigits: 1, maximumFractionDigits: 1});
const sg1 = v => (v >= 0 ? "+" : "−") + Math.abs(v).toLocaleString("en-IN", {maximumFractionDigits: 1});
const sL = v => v == null ? "?" : (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(1) + "L";
const escA = s => esc(s).replace(/"/g, "&quot;");
const plainT = s => String(s == null ? "" : s).replace(/\*\*/g, "");
const MARKP = e => e.push || e.toot || e.zone || e.tag === "BLIND" || e.floor || e.chap === "FUEL" || e.chap === "FUEL SPENT" || (e.signs && !e.signs.driving) || e.chap === "NEW FIGHT" || e.chap === "MANAGE";
const tg = rows => `<div class="tg">${rows.filter(Boolean).map(([k, v]) => `<span>${esc(k)}</span><span>${esc(v)}</span>`).join("")}</div>`;
function place(xs, y, w, h, up) {   // a chart label never sits on another: the nearest free spot, row by row above and below (each of the
  // offered x positions tried in a row), inside the price pane. Never dropped: when the pane is full it takes the spot that covers least
  const hit = (x, yy) => LBL.reduce((a, r) => a + Math.max(0, Math.min(x + w + 2, r.x + r.w) - Math.max(x - 2, r.x)) * Math.max(0, Math.min(yy + h + 1, r.y + r.h) - Math.max(yy - 1, r.y)), 0);
  let best = {x: xs[0], y}, least = Infinity;
  for (let n = 0; n < 41; n++) { const yy = y + (n ? (n % 2 ? 1 : -1) * (up ? -1 : 1) * ((n + 1) >> 1) * (h + 2) : 0);
    if (yy < pTop + 1 || yy + h > pBot - 1) continue;
    for (const x of xs) { const a = hit(x, yy); if (a < least) { least = a; best = {x, y: yy}; } if (!a) break; }
    if (!least) break; }
  LBL.push({x: best.x, y: best.y, w, h}); return best;
}
const nudge = (x, y, w, h, up) => place([x], y, w, h, up).y;      // the page's own labels (trigger pills, the wall's answers)
function j3Chip(x, y, txt, col, o) {  // one label in the page's own language (the HELD / DEFENDED chip): white, a coloured rule, 10 px
  o = o || {}; ctx.font = "700 10px " + MONO; const w = ctx.measureText(txt).width + 10, h = 16, cx = v => Math.max(padL + 1, Math.min(Wd - padR - w - 1, v));
  const at = place([x].concat(o.alt ? o.alt(w) : []).map(cx), Math.max(pTop + 1, Math.min(pBot - h - 1, y)), w, h, o.up), yy = at.y; x = at.x;
  ctx.save(); if (o.dim) ctx.globalAlpha = 0.5; ctx.fillStyle = o.fill || "#fff"; rr(x, yy, w, h, 5); ctx.fill(); ctx.strokeStyle = col; ctx.lineWidth = 1.2; if (o.dash) ctx.setLineDash([3, 2]); ctx.stroke();
  ctx.setLineDash([]); ctx.fillStyle = col; ctx.fillText(txt, x + 5, yy + 12); ctx.restore();
  if (o.html) HIT.push({x, y: yy, w, h, html: o.html});
  return {x, y: yy, w, h};
}

/* ---- move bands */
function bandAt(b, i) {            // what was known of band b at replay minute i; null before its first push bar closed
  if (b.ci > i) return null;        // a band is one run (line, end); each push of it is a LEG with its own name and numbers
  const frozen = b.ei != null && b.ei + 1 <= i, kEnd = frozen ? b.ei : Math.min(i - 1, N - 1), known = b.legs.filter(g => g.ci <= i);
  let line = b.steps[0][1]; for (const [j, v] of b.steps) if (j <= i) line = v;
  const legs = known.map((g, n) => { const nx = known[n + 1], k = Math.max(g.si, Math.min(nx ? nx.si - 1 : kEnd, g.si + g.dl.length - 1)), o = k - g.si, cnt = o + 1, dl = g.dl[o], oi = g.oi[o];
    return {b, g, no: n + 1, a: g.si, k, n: cnt, dl, oi, name: g.nm[o], bar: Math.floor(o / 5) + 1, live: !frozen && !nx, frozen, line,
      cvdx: dl != null && g.D0 ? Math.abs(dl) / (cnt / 5) / g.D0 : null, oispd: oi != null ? oi / cnt : null}; });
  return {b, frozen, kEnd, line, legs, cur: legs[legs.length - 1]};
}
const formingAt = i => J3.forming[i - 1] || null;    // hold2.state said PUSH on the open bar at the last closed minute
function arrows3(a, k) {            // the three indices over minutes a..k, from the frame's own arrays (N futures; BN, SX spot)
  const mv = (cl, op) => { const o = op ? op[a] : a > 0 ? cl[a - 1] : cl[a], c = cl[k]; return o == null || c == null ? null : c - o; };
  const ch = [mv(D.fut, D.fo), mv(D.bnf), mv(D.sx)], s = ch.map(v => v == null ? null : Math.sign(v));
  return {ch, s, all: s.some(v => v == null) ? null : s[0] && s[0] === s[1] && s[1] === s[2] ? s[0] : 0};
}
function a3Text(a, k) { const r = arrows3(a, k); return r.all ? `ALL 3 ${ARR(r.all)}` : r.s.map((v, n) => `${["N", "BN", "SX"][n]} ${v == null ? "?" : v > 0 ? "▲" : v < 0 ? "▼" : "·"}`).join(" "); }
function withTxt(d, a, k) { const r = arrows3(a, k), n = r.s.filter(v => v === d).length, q = r.s.filter(v => v == null).length;
  return r.all === d ? "all three with it" : `${n} of 3 with it` + (q ? ` · ${q} not read` : ""); }
function optAt(i) { let r = null; for (const c of J3.opt.closes) { if (c.ki <= i) r = c; else break; } return r; }
function wayWord(d, r) {            // the option-flow word at the wall in the way of a band going d
  if (!r) return {t: `no option-flow read yet (first ${J3.opt.first})`, c: "q"};
  if (r.said === "OI?") return {t: "option flow could not be read (OI?)", c: "warn"};
  const w = (d > 0 ? r.cap : r.floor).word;
  if (w === "COVER") return {t: d > 0 ? "lid breaking (real)" : "floor breaking (real)", c: d > 0 ? "ok" : "bad"};
  if (w === "WRITE") return {t: d > 0 ? "into a lid" : "into a floor", c: "warn"};
  return {t: r.said, c: r.lean > 0 ? "ok" : r.lean < 0 ? "bad" : "q"};
}
function demoSide(d, a, e) {        // "with you" / "against you" for something going d over minutes a..e, while the DEMO trade is open
  const T = J3.trade; if (!DEMO || !T || !d) return "";
  const out = T.exit ? T.exit.i : N; if (e < T.ei || a > out) return "";
  return d === T.d ? "with you" : "against you";
}
function bandLine(i) {             // ONE line in the Jarvis window while a band is live (or forming)
  const s = J3.bands.map(b => bandAt(b, i)).filter(v => v && !v.frozen).pop(), g = s && s.cur, f = formingAt(i);
  if (g) { const b = s.b, sp = speedAt(clampI(i - 1)), wd = sp && sp.dir === b.d && sp.word && sp.word !== "?" ? sp.word : "MOVE";
    return {c: b.d > 0 ? "up" : "dn", t: `${wd} ${ARR(b.d)} ${(g.name || "no name: delta or OI not read").toLowerCase()} · bar ${g.bar} · ${withTxt(b.d, g.a, g.k)} · over ${b.d > 0 ? "below" : "above"} ${fmt(s.line)}f`
      + (f ? ` · ${f.d === b.d ? "same-side" : "opposite"} PUSH forming ${ARR(f.d)}` : "")}; }
  return f ? {c: "warn", t: `forming ${ARR(f.d)} · the open ${D.mins[f.si]} bar already reads PUSH · a band only when it closes`} : null;
}
function bandTip(g) {               // one leg's numbers (the label's hover): Dext delta, futures OI, the two speeds, the three indices, the wall in the way
  const b = g.b, L = g.g, r = optAt(g.live ? cur() : g.k + 1), ww = wayWord(b.d, r), you = demoSide(b.d, g.a, g.k);
  return `<b>${D.mins[g.a]}–${g.live ? "now" : D.mins[g.k]} · ${ARR(b.d)} ${esc(g.name || "no name")}</b>` + tg([
    ["state", g.live ? `live · bar ${g.bar}` : g.frozen && g.k === b.ei ? `over ${D.mins[b.ei]} · ${b.why}` : `closed by the next same-side PUSH`],
    ["Dext delta", g.dl == null ? "could not read: a Dext minute is missing" : `${sgn(g.dl)} lots`],
    ["futures OI", g.oi == null ? "could not read" : `${sgn(g.oi)} lots`],
    ["CVD speed", g.cvdx == null ? (L.D0 == null ? "no earlier bar today to compare with" : "could not read") : `×${g.cvdx.toFixed(1)} today's normal (${fmt(L.D0)} lots / 5 min)`],
    ["OI speed", g.oispd == null ? "could not read" : `${sg1(g.oispd)} lots / min`],
    ["indices", `${a3Text(g.a, g.k)} · N fut · BN, SX spot`],
    ["option flow", ww.t + (r && r.said !== "OI?" ? ` · as of ${r.t}` : "")],
    ["this push", `${L.t} from ${f1(L.origin)}f · size ×${L.size} · its line ${f1(L.line)}f`],
    ["band", `${D.mins[b.si]}–${b.ei != null && g.frozen ? D.mins[b.ei] : "open"} · push ${g.no} of ${b.legs.length} · line now ${f1(g.line)}f · ${fmt(g.line - bas[clampI(g.k)])}s`],
    you && ["DEMO trade", you]]);
}
function j3Box(a, k, d, dashed, faded) {
  let hi = -Infinity, lo = Infinity;
  for (let j = a; j <= k; j++) { const q = live(j); hi = Math.max(hi, q.h); lo = Math.min(lo, q.l); }
  const half = plotW() / N / 2, x0 = X(a) - half, x1 = X(k) + half, y0 = Math.max(pTop, Y(hi) - 5), y1 = Math.min(pBot, Y(lo) + 5);
  ctx.save(); ctx.fillStyle = d > 0 ? "rgba(15,157,118,.09)" : "rgba(229,72,77,.08)"; ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  ctx.strokeStyle = d > 0 ? COL.up : COL.dn; ctx.globalAlpha = faded ? 0.45 : 0.9; ctx.lineWidth = 1; if (dashed) ctx.setLineDash([4, 3]);
  ctx.strokeRect(x0 + 0.5, y0 + 0.5, Math.max(1, x1 - x0 - 1), Math.max(1, y1 - y0 - 1)); ctx.restore();
  return {x0, x1, y0, y1};
}
function j3Under(now, end) {        // under the candles: the tinted spans (none in HOLD mode; in the NOW view only the swing in play's)
  BOX.clear(); if (!LY.bands || HOLDM) return;
  for (const b of J3.bands) { const s = bandAt(b, end); if (s) for (const g of s.legs) if (g.live || !OLD(g.k)) BOX.set(b.id + ":" + g.no, j3Box(g.a, g.live ? end : g.k, b.d, false, !g.live)); }
  const f = formingAt(end); if (f) BOX.set("f", j3Box(f.si, end, f.d, true, false));
}
function j3Over(now, end) {         // over the candles: the band's line and name, the option-flow marks, the DEMO trade's two lines
  const i = end;
  if (LY.bands && !HOLDM) {
    for (const b of J3.bands) {
      const s = bandAt(b, i); if (!s || (s.frozen && OLD(b.ei))) continue;
      const col = b.d > 0 ? COL.up : COL.dn, kEnd = s.frozen ? b.ei : i;
      ctx.save(); ctx.strokeStyle = col; ctx.lineWidth = 1; ctx.setLineDash([2, 3]); ctx.globalAlpha = s.frozen ? 0.55 : 1; ctx.beginPath();
      b.steps.forEach(([j, v], n) => { if (j > i) return; const nx = b.steps[n + 1], j1 = nx && nx[0] <= i ? Math.min(kEnd, nx[0]) : kEnd;
        ctx.moveTo(X(n ? j : b.si), Y(v)); ctx.lineTo(X(j1), Y(v)); });
      ctx.stroke(); ctx.restore();
      for (const g of s.legs) { const bx = BOX.get(b.id + ":" + g.no); if (!bx) continue;
        const you = demoSide(b.d, g.a, g.k);
        const txt = `${ARR(b.d)} ${g.name || "MOVE · no name"}` + (g.live ? ` · bar ${g.bar}` : g.dl == null ? "" : ` ${sgn(g.dl)}`) + (you ? ` · ${you}` : "");
        const q = j3Chip(bx.x0, bx.y0 - 18, txt, col, {html: bandTip(g), up: true, dim: !g.live && g.k < HIST, alt: w => [bx.x1 - w, bx.x1 + 4, bx.x0 - w - 4, bx.x1 + w / 2, bx.x0 - 1.5 * w]});
        if (Math.abs(q.y - (bx.y0 - 18)) > 20 || q.x > bx.x1) {   // moved off its box by the no-overlap rule: a thin leader ties it back
          ctx.save(); ctx.strokeStyle = col; ctx.globalAlpha = 0.45; ctx.beginPath(); ctx.moveTo(Math.min(bx.x1, Math.max(bx.x0, q.x + 6)), q.y > bx.y0 ? bx.y1 : bx.y0); ctx.lineTo(q.x + 6, q.y > bx.y0 ? q.y : q.y + q.h); ctx.stroke(); ctx.restore(); } }
      if (!s.frozen) axisTag(Y(s.line), `MOVE line ${f1(s.line)}f`, col, b.d > 0 ? "#e6f6f0" : "#fdecec");
    }
    const f = formingAt(i), fx = BOX.get("f");
    if (f && fx) j3Chip(fx.x0, fx.y0 - 18, `forming ${ARR(f.d)}`, COL.warn, {dash: true, fill: "#fdf3dc",
      html: `<b>forming ${ARR(f.d)} · as of ${D.mins[i - 1]}</b>` + tg([["read", "hold2.state on the open 5-min bar says PUSH"], ["bar opened", D.mins[f.si]], ["size", `×${f.size} its slot's median`], ["R", String(f.R)], ["then", "a band only if the bar closes a PUSH"]])});
  }
  if (LY.opt && !HOLDM) for (const c of J3.opt.changes) {
    if (c.ki > i) break;
    if (c.said === "QUIET" || c.said === "OI?" || OLD(c.i)) continue;   // not a chart event (nothing happened / could not read), or older than the swing in play: on the OPT row and in the log
    // v2: a lean AGAINST the live move band is a warning (amber, and it says so), never a green light; a wall off the scale is marked at the price of its minute
    const lb = J3.bands.map(b => bandAt(b, c.ki)).filter(v => v && !v.frozen).pop(), vs = lb && c.lean && lb.b.d !== c.lean ? lb.b.d : 0;
    const cant = c.said === "OI?", col = cant || vs ? COL.warn : c.lean > 0 ? COL.up : c.lean < 0 ? COL.dn : COL.mut, x = X(c.i);
    let y = c.k != null ? Y(lvl(c.k, c.i)) : Y(D.fut[c.i]), off = "";
    if (y < pTop + 4) { y = Y(D.fut[c.i]); off = "↑"; } else if (y > pBot - 4) { y = Y(D.fut[c.i]); off = "↓"; }
    const txt = (cant ? `opt: could not read ${c.t}` : `opt: ${c.said} ${c.t}`) + (vs ? ` · against ${ARR(vs)}` : "");   // the wall and its arrow are in the hover
    ctx.font = "700 10px " + MONO; const w = ctx.measureText(txt).width + 10;
    const q = j3Chip(x - w / 2, y + (y < (pTop + pBot) / 2 ? 8 : -24), txt, col, {dash: cant, dim: c.i < HIST, html: optTip(c), up: y >= (pTop + pBot) / 2, alt: ww => [x + 6, x - ww - 6, x + ww / 2 + 12, x - 1.5 * ww - 12]});
    ctx.save(); ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, 2.5, 0, 7); ctx.fill();
    ctx.strokeStyle = col; ctx.globalAlpha = 0.5; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(Math.max(q.x, Math.min(q.x + q.w, x)), q.y > y ? q.y : q.y + q.h); ctx.stroke(); ctx.restore();
  }
  if (LY.opt && !HOLDM) for (const c of J3.opt.closes) {   // v2: writers RUNNING on three or more strikes at one close (optladder's own cover rule), whatever the settled word says
    if (c.ki > i) break; if (!c.cover || OLD(c.i)) continue;
    const pe = c.cover.side === "PE", col = pe ? COL.dn : COL.up, x = X(c.i), y = Y(D.fut[c.i]), txt = `opt: ${pe ? "PUT" : "CALL"} WRITERS RUN ×${c.cover.n} ${sL(c.cover.doi)} ${c.t}`;
    ctx.font = "700 10px " + MONO; const w = ctx.measureText(txt).width + 10;
    const q = j3Chip(x - w / 2, y + (pe ? 10 : -26), txt, col, {dim: c.i < HIST, up: !pe, html: laneTip(c), alt: ww => [x + 6, x - ww - 6]});
    ctx.save(); ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, 2.5, 0, 7); ctx.fill();
    ctx.strokeStyle = col; ctx.globalAlpha = 0.5; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(Math.max(q.x, Math.min(q.x + q.w, x)), q.y > y ? q.y : q.y + q.h); ctx.stroke(); ctx.restore();
  }
  const T = J3.trade, dm = demoAt(i);
  if (dm && !dm.wait) {
    const kEnd = dm.out ? T.exit.i : i, yE = Y(T.px);
    ctx.save(); ctx.strokeStyle = COL.ink; ctx.lineWidth = 1.2; ctx.setLineDash([6, 3]); ctx.beginPath(); ctx.moveTo(X(T.ei), yE); ctx.lineTo(X(kEnd), yE); ctx.stroke();
    ctx.strokeStyle = COL.warn; ctx.lineWidth = 1.6; ctx.setLineDash([]); ctx.beginPath();
    const st = T.stops.filter(s => s[0] <= i);
    ctx.save(); ctx.fillStyle = "rgba(229,72,77,.07)";       // v3: the only place the trade is wrong is beyond the line; everything this side of it is room
    st.forEach(([j, v], n) => { const j1 = st[n + 1] ? st[n + 1][0] - 1 : kEnd, x0 = X(Math.max(j - 1, T.ei)), x1 = X(Math.min(j1, kEnd)), y = Y(v);
      if (T.d < 0) ctx.fillRect(x0, pTop, Math.max(1, x1 - x0), Math.max(0, y - pTop)); else ctx.fillRect(x0, y, Math.max(1, x1 - x0), Math.max(0, pBot - y)); });
    ctx.restore();
    st.forEach(([j, v], n) => { const j1 = st[n + 1] ? st[n + 1][0] : kEnd, x0 = X(Math.max(j - 1, T.ei));
      if (n) ctx.lineTo(x0, Y(v)); else ctx.moveTo(x0, Y(v)); ctx.lineTo(X(Math.min(j1 - (st[n + 1] ? 1 : 0), kEnd)), Y(v)); });
    ctx.stroke(); ctx.restore();
    j3Chip(X(T.ei) + 4, yE + (T.d < 0 ? 4 : -20), `DEMO ${T.side} ${f1(T.px)}f`, COL.ink, {fill: "#eeece6", up: T.d > 0,
      html: `<b>DEMO · ${T.side} ${f1(T.px)}f</b>` + tg([["entry", `the ${T.t} trigger bar's close, ${D.mins[T.ei]}`], ["spot then", `${fmt(T.px - bas[T.ei])}s`], ["note", "display only: nothing was placed"]])});
    if (dm.stop != null && !dm.out) j3Chip(X(kEnd) - 150, Y(dm.stop) + (T.d < 0 ? -20 : 4), `wrong only ${T.d < 0 ? "above" : "below"} ${f1(dm.stop)}f`, COL.warn, {fill: "#fdf3dc", up: T.d < 0,
      html: `<b>DEMO STOP ${f1(dm.stop)}f · ${fmt(dm.stop - bas[clampI(i)])}s</b>` + tg([["from", dm.why], ["exit", "a TRADE through this line, never a candle close"]])});
    for (const bk of T.book || []) { if (bk.i > i) break; if (bk.w !== "BOOK") continue;   // the new line's places, marked where price met them
      const what = bk.place === "climax" ? "climax" : /^\d/.test(bk.place) ? "wall " + bk.place.replace(/^(\d+)(CE|PE)$/, (m0, k, sd) => `${fmt(+k)} ${sd}`) : bk.place;
      j3Chip(X(bk.i) + 4, Y(bk.lvl != null ? bk.lvl : bk.px) + (T.d < 0 ? 4 : -20), `BOOK · ${what}`, COL.ink, {fill: "#eeece6", up: T.d > 0,
        html: `<b>${bk.t} · BOOK (new line)</b>` + tg([["why", bk.why], ["points then", sg1(bk.pts)], ["note", "a place to take some off; the hold voice decides the rest"]])}); }
    if (dm.out) j3Chip(X(T.exit.i) + 6, Y(T.exit.stop) - 8, `DEMO EXIT ${T.exit.t} · ${sg1(T.exit.pts)} pts`, COL.warn, {fill: "#fdf3dc",
      html: `<b>DEMO EXIT ${T.exit.t}</b>` + tg([["why", `a trade through the stop ${f1(T.exit.stop)}f`], ["points", `${sg1(T.exit.pts)} at the line`], ["note", "display only: nothing was placed"]])});
  }
  const mv = mtVoice();             // the live page: her marked trade's line (HOLD v2's, as the server's voice gives it), on the chart and the axis
  if (mv && mv.v.ok && typeof mv.v.stop_f === "number") { const y = Y(mv.v.stop_f);
    if (y > pTop && y < pBot) { ctx.save(); ctx.strokeStyle = COL.warn; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.moveTo(X(Math.max(0, i - 30)), y); ctx.lineTo(X(i), y); ctx.stroke(); ctx.restore(); }
    axisTag(y, `YOUR LINE ${f1(mv.v.stop_f)}f`, COL.warn, "#fdf3dc"); }
}
function optTip(c) {
  const r = J3.opt.closes.find(v => v.i === c.i) || {}, w = c.ws && r.walls ? r.walls[c.ws.toLowerCase()] : null;
  return `<b>option flow · as of ${c.t}</b>` + tg([
    ["word", c.said === "OI?" ? "could not read: OI not on the record at this close" : c.said + (c.raw !== c.said ? ` (this close alone: ${c.raw})` : "")],
    ["cap", r.cap ? `${r.cap.word} ${sL(r.cap.doi)} · ${r.cap.known} of ${r.cap.n} strikes read` : "?"],
    ["floor", r.floor ? `${r.floor.word} ${sL(r.floor.doi)} · ${r.floor.known} of ${r.floor.n} strikes read` : "?"],
    ["marked at", w ? `${fmt(w.k)}s ${c.ws} wall · ${w.oi}L ${w.state}` : "the price: no wall on the record"]]);
}

/* ---- the OI ladder's WHO chips (ATM ±3, as of the latest 3-min close) */
function j3WhoHead(i) {
  if (!LY.opt) return; const r = optAt(i);
  ctx.font = "600 9px " + MONO; ctx.fillStyle = r && r.said === "OI?" ? COL.warn : COL.mut;
  const s = !J3.opt.ok ? "WHO · not read" : r ? `WHO CE | PE · as of ${r.t}` : `WHO · first read ${J3.opt.first}`;
  ctx.fillText(s, Wd - 4 - ctx.measureText(s).width, pTop - 8);
}
function j3Who(k, y, i) {           // two chips on the strike's own line: CE left, PE right; a solid chip = FIRM (the word is in its hover)
  if (!LY.opt) return; const r = optAt(i); if (!r) return;
  ["CE", "PE"].forEach((sd, n) => {
    const w = r.st[k + sd]; if (!w) return;                // outside ATM ±3 at this close: no chip, never a QUIET
    const [who, firm, doi, dl, oi] = w, cant = who === "OI?" || who === "FLOW?", v = (J3.opt.up[sd === "CE" ? "CAP" : "FLOOR"] || {})[who] || 0;
    const col = cant ? COL.warn : v > 0 ? COL.up : v < 0 ? COL.dn : COL.mut, w0 = WHOW / 2 - 1, x = Wd - 4 - WHOW + n * (w0 + 2), yy = y - 5.5;
    ctx.save(); ctx.font = "600 9px " + MONO; ctx.fillStyle = firm === true ? col : "#fff"; rr(x, yy, w0, 11, 3); ctx.fill();
    ctx.strokeStyle = col; ctx.globalAlpha = firm === true ? 1 : 0.55; ctx.lineWidth = 1; if (cant) ctx.setLineDash([2, 2]); ctx.stroke();
    ctx.globalAlpha = 1; ctx.fillStyle = firm === true ? "#fff" : col; ctx.textAlign = "center"; ctx.fillText(who, x + w0 / 2, yy + 8.5, w0 - 3); ctx.restore();
    HIT.push({x, y: yy, w: w0, h: 11, html: `<b>${fmt(k)}s ${sd} · as of ${r.t}</b>` + tg([
      ["who", cant ? `could not read (${who === "OI?" ? "OI missing or stale" : "no Dext footprint"})` : who + (firm === true ? " · FIRM (the lagged window agrees)" : firm === false ? " · not firm" : "")],
      ["OI", `${sL(doi)} in 3 min · now ${oi == null ? "?" : oi + "L"}`], ["flow delta", `${sL(dl)} in 3 min`]])});
  });
}

const laneTip = c => `<b>option flow · the ${c.t} close</b>` + tg([
  ["this close", c.raw === "OI?" ? "could not read: OI not on the record" : c.raw],
  ["settled word", `${c.said} (changes only after two closes the same way)`],
  ["cap", `${c.cap.word} ${sL(c.cap.doi)}`], ["floor", `${c.floor.word} ${sL(c.floor.doi)}`],
  c.cover && ["writers running", `${c.cover.side} writers covering on ${c.cover.n} strikes · ${sL(c.cover.doi)}`]]);

/* ================================================================== v2 (12 Nov, her mark-up of the first mockup) ==
   the price scale fits the day so far · every zone mark carries HER verdict (the zone card + the §1d fade gate), never the old band read ·
   the swings are on the chart · an OI cut INTO the move is not called a push */
let HIST = 0, PAC = null, HOLDM = false, SYNC = null, MT = null;   // MT: her marked trade's voice as the server sent it (live page only)
const mtVoice = () => MT && D && MT.idx === String(D.idx).toUpperCase() && cur() >= N - 2 ? MT : null;   // shown at the live edge only: the voice is "now", never a replay
const OLD = i => i < HIST && !LY.hist;      // v3, the NOW view: a mark older than the swing in play is not drawn (it is on the day map and in the log; History brings it back)
// cardOf / zoneSay / lastZone now live in jarvis2.html itself (A279, the live page's fix): the mockup uses the page's own.
function zoneTip(z, zs, v) {
  return `<b>${z.side} zone · ${fmt(z.px)}f · ${z.band || "?"} · ${String(z.t).slice(0, 5)}</b>`   // A294: the three reads, each with its number
    + tg([["PLAN", zs.plan ? zs.plan.line : zs.why[0]]].concat(zs.plan ? [["checks", zs.plan.checks.join(" · ")]] : [])   // 14 Nov: the plan's word
      .concat(zs.reads.map(r => [(r.yes === true ? "✓ " : r.yes === false ? "✗ " : "? ") + "info · " + r.k, r.t]),   // the old reads: information, not votes
        zs.c ? zs.c.signs.map(s => ["sign · " + s.k, (s.ok === true ? "✓ " : s.ok === false ? "✗ " : "? ") + s.text]) : []));
}
function yFit(end) {                // the price scale: what has traded so far, her outer bands now, and one strike beyond the money each side.
  let lo = Infinity, hi = -Infinity; // A far wall is pinned to the pane's edge with an arrow instead of flattening the candles
  for (let i = 0; i <= end; i++) { const q = live(i); if (q.l < lo) lo = q.l; if (q.h > hi) hi = q.h; }
  if (D.vwap && end > 10 && D.sd[end] != null) { lo = Math.min(lo, D.vwap[end] - 3 * D.sd[end]); hi = Math.max(hi, D.vwap[end] + 3 * D.sd[end]); }
  const st = D.strikes.length > 1 ? D.strikes[1] - D.strikes[0] : 50, k = clampI(end), atm = Math.round((D.fut[k] - bas[k]) / st) * st;
  lo = Math.min(lo, lvl(atm - st, k)); hi = Math.max(hi, lvl(atm + st, k));
  const pad = Math.max(18, (hi - lo) * 0.06), a = lo - pad, b = hi + pad;
  if (RM || !playing || a < Y0 || Math.abs(Y0 - a) > 150) Y0 = a; else { Y0 += (a - Y0) * 0.2; if (Math.abs(Y0 - a) < 0.3) Y0 = a; }   // the scale opens at once
  if (RM || !playing || b > Y1 || Math.abs(Y1 - b) > 150) Y1 = b; else { Y1 += (b - Y1) * 0.2; if (Math.abs(Y1 - b) < 0.3) Y1 = b; }   // (price is never off the pane) and closes gently
}
function histFrom(end) {            // "now" = the swing in play: it starts at the last confirmed swing. Older marks leave the chart (History brings them back, quieter)
  const K = pa().P.filter(p => p.ki <= end); return K.length ? K[K.length - 1].i : 0;
}

/* ---- v3, HOLD mode: while a trade is open the page answers ONE question: is anything broken? ----------------------------------
   Her words (28 Sep): "if the oder flow is with me oi and flow is behind i like to hold"; price against her with the defending wall still
   holding and weak flow against is a PULLBACK. So: a candle against the trade is GREY while it is only a pullback, and AMBER when its
   5-min bar is (or is forming as) a PUSH against her, the signed §1m PUSH and nothing looser. Everything that is not the trade leaves the chart. */
const bar5At = i => { const s = i - i % 5; return (J3.bars5 || []).find(b => b.si === s) || null; };
function threatAt(i, end) {
  const T = J3.trade, s = i - i % 5;
  if (s + 5 <= end) { const b = bar5At(i); return !!(b && b.st === "PUSH" && b.d === -T.d); }
  const f = J3.forming[end - 1]; return !!(f && f.si === s && f.d === -T.d);
}
function holdCol(i, k, end) {       // with her = the candle's own colour · against = grey (pullback) or amber (a PUSH against)
  if (!HOLDM || i < J3.trade.ei + 1 || (k.c - k.o) * J3.trade.d >= 0) return null;
  return {col: threatAt(i, end) ? COL.warn : "#b3b8c0"};
}
function holdStats(i) {             // this trade so far: the best price, the move against it now, the deepest one it sat through, and how many a tight trail would have taken
  const T = J3.trade, d = T.d, k = clampI(i), tp = T.trail_pts; let best = T.px, deep = 0, n = 0, armed = true;
  for (let j = T.ei + 1; j <= k; j++) { const q = live(j), fav = d > 0 ? q.h : q.l, adv = d > 0 ? q.l : q.h;
    if ((fav - best) * d > 0) { best = fav; armed = true; }
    const pb = (best - adv) * d; if (pb > deep) deep = pb;
    if (tp != null && armed && pb >= tp) { n++; armed = false; } }
  return {best, now: Math.max(0, (best - D.fut[k]) * d), deep, n, tp};
}
function j3Hold(i) {                // the HOLD strip replaces the seven status cards: voice · wrong only if · against you now · still behind you · ahead · this trade
  const hs = $("#hstrip"); hs.hidden = !HOLDM; $("#strip").hidden = HOLDM; if (!HOLDM) { $("#b2").hidden = $("#b3").hidden = false; return; }
  const T = J3.trade, d = T.d, k = clampI(i), dm = demoAt(i), st = holdStats(i), b = bas[k], side = d < 0 ? "above" : "below";
  const away = dm.stop == null ? null : (dm.stop - D.fut[k]) * -d, w = dm.v ? dm.v.w : "HOLD", wc = w === "EXIT" ? "dn" : w === "WARN" ? "wn" : "up";
  const lb = (J3.bars5 || []).filter(x => x.si + 5 <= i).pop() || null, f = J3.forming[i - 1], fa = f && f.d === -d ? f : null, need = J3.need;
  const ag = fa ? [`PUSH forming against`, `the open ${D.mins[fa.si]} bar reads ×${fa.size} · a push needs ×${need}`, "wn"]
    : lb && lb.st === "PUSH" && lb.d === -d ? [`PUSH against closed`, `${D.mins[lb.si]} bar ×${lb.size} · R ${lb.R}`, "dn"]
    : st.now >= 1 ? [`pullback ${st.now.toFixed(0)} pts`, !lb || lb.pc !== -d ? "the last 5-min bar is with you"
        : lb.st === "CLIMAX" ? `big ${lb.d > 0 ? "buying" : "selling"} ×${lb.size} but price did not follow (R ${lb.R}): absorbed, not a push`
        : `last bar against you ×${lb.size == null ? "?" : lb.size} · a push needs ×${need}: a pullback`, "q"]
    : ["nothing", "price is at the trade's best", "q"];
  const dw = nearWall(k, d < 0 ? "CE" : "PE"), aw = nearWall(k, d < 0 ? "PE" : "CE"), r = optAt(i), z = D.vwap && D.sd && D.sd[k] ? (D.fut[k] - D.vwap[k]) / D.sd[k] * d : null;
  const reads = [["flow", !lb ? null : lb.d === d ? 1 : lb.st === "PUSH" && lb.d === -d ? -1 : 0, !lb ? "not read" : lb.d === d ? "with you" : lb.st === "PUSH" ? "PUSH against" : "weak against"],
    ["OI", !dw ? null : dw.state === "UNWINDING" ? -1 : dw.state === "BUILDING" ? 1 : 0, !dw ? "no wall read" : `${fmt(dw.k)} ${dw.side} ${dw.state === "UNWINDING" ? "gave up" : dw.state === "BUILDING" ? "building" : "holding"}`],
    ["zone", z == null ? null : z > -1 ? 1 : z <= -2 ? -1 : 0, z == null ? "bands forming" : z > -1 ? "your side of the bands" : z <= -2 ? "back through your zone" : "between"],
    ["options", !r || r.raw === "OI?" ? null : r.lr === d ? 1 : r.lr === -d ? -1 : 0, !r || r.raw === "OI?" ? "not read" : r.lr === d ? "with you" : r.lr === -d ? `${r.raw} against` : "quiet"]];
  const nb = reads.filter(x => x[1] === 1).length, na = reads.filter(x => x[1] === -1).length;
  const cell = (k0, v, s, cls, tip) => `<div class="cell" title="${escA(tip || s)}"><div class="k">${k0}</div><div class="v ${cls || ""}">${v}</div><div class="s">${esc(s)}</div></div>`;
  $("#b2").hidden = $("#b3").hidden = true;                // the panel's market blocks step back: the strip says "wrong only if" and "broken" for the trade itself
  const sm = LY.str ? meterSay(i) : null;
  hs.innerHTML = cell("YOUR TRADE · VOICE", `<span class="hw ${wc}">${w}</span> <small>${sg1(dm.pts)} pts</small>`, `${T.side} ${f1(T.px)}f · ${dm.v ? dm.v.why : "speaks at the next 3-min close"}`, "", "the one voice: EXIT > WARN > TIGHTEN > HOLD. It says EXIT only when price trades through the line.")
    + (sm ? cell("STRENGTH · your side", `${sm.me}% <small>${sm.w.toLowerCase()} · ${sm.d > 0 ? "sellers" : "buyers"} ${sm.ot}%</small>`, `high ${sm.hi}% · ${sm.fam}`,
        sm.w === "TURNING" ? "dn" : sm.w === "CONTESTED" ? "wn" : "q", "STRENGTH v2, shadow: the plain average of five kinds of evidence, each measured over the last 40 minutes against its own normal. Not a chance of winning.") : "")
    + cell("WRONG ONLY IF", dm.stop == null ? "no line yet" : `${side} ${f1(dm.stop)}f`, dm.stop == null ? "no stop on the record yet" : `a trade through it · ${away.toFixed(0)} pts away · ${fmt(dm.stop - b)}s · or a PUSH bar against you`, "", dm.why)
    + cell("AGAINST YOU NOW", ag[0], ag[1], ag[2], "a move against you is a pullback until a 5-min bar is a PUSH against you (size ≥ the table's p90, R ≥ 0.25) or price trades through the line")
    + cell("IS ANYTHING BROKEN", na ? `${na} of 4 broken` : "nothing broken" + (nb ? ` <small>· ${nb} with you</small>` : ""), reads.map(x => `${x[0]}: ${x[2]}`).join(" · "), na ? "dn" : "up",
        "your reads, asked the holding way: is the flow a PUSH against you, has the wall defending you given up, is price back through your zone, are options leaning against you. A read that is merely quiet is not broken. (VPIN is not in this replay frame; the option flow stands in its row.)")
    + cell("AHEAD", aw ? `${fmt(lvl(aw.k, k))}f · ${Math.abs(lvl(aw.k, k) - D.fut[k]).toFixed(0)} pts` : "open", aw ? `pullback zone ${fmt(aw.k)}s ${aw.side} ${aw.oi != null ? aw.oi.toFixed(0) + "L" : ""} · not a target` : "no wall in 2 steps", "", "the wall ahead is where a first leg usually pauses: a pullback zone, never a target")
    + cell("THIS TRADE SO FAR", `sat through ${st.deep.toFixed(0)} pts`, st.tp != null ? `a ${st.tp.toFixed(0)}-pt trail would have been hit ${st.n}× · the line: 0×` : "no trail distance on the record", "", "counted on this trade only, from its own candles; the trail distance is your zone machine's stop distance");
}
function pa() {                     // price action from the frame's own swing pivots (causal by `known`): a break = the first 1-min close beyond the last confirmed swing
  if (PAC) return PAC;
  const P = (D.pivots || []).map(p => Object.assign({i: ix(p.t), ki: ix(p.known)}, p)).filter(p => p.i >= 0 && p.ki >= 0), br = [];
  let lo = null, hi = null, n = 0;
  for (let i = 0; i < N; i++) {
    while (n < P.length && P[n].ki <= i) { const p = P[n++]; if (p.kind === "L") lo = {p}; else hi = {p}; }
    const c = D.fut[i]; if (c == null) continue;
    if (lo && !lo.done && c < lo.p.px) { lo.done = true; br.push({i, d: -1, p: lo.p}); }
    if (hi && !hi.done && c > hi.p.px) { hi.done = true; br.push({i, d: 1, p: hi.p}); }
  }
  return PAC = {P, br};
}
function j3PA(end) {                // the swings (H · HL · LH · LL) as dark pills, the running leg dashed, each break of the last swing as a line to the bar that closed through it
  if (!LY.pa) return; const {P, br} = pa(), K = P.filter(p => p.ki <= end); if (!K.length) return;
  ctx.save(); ctx.strokeStyle = COL.ink; ctx.globalAlpha = 0.4; ctx.lineWidth = 1.2; ctx.beginPath();
  K.forEach((p, n) => n ? ctx.lineTo(X(p.i), Y(p.px)) : ctx.moveTo(X(p.i), Y(p.px))); ctx.stroke();
  const L = K[K.length - 1]; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(X(L.i), Y(L.px)); ctx.lineTo(X(end), Y(live(end).c)); ctx.stroke(); ctx.restore();
  for (const b of br) { if (b.i > end) break; if (OLD(b.i)) continue; const col = b.d > 0 ? COL.up : COL.dn, y = Y(b.p.px);
    ctx.save(); ctx.strokeStyle = col; ctx.lineWidth = 1; ctx.setLineDash([5, 3]); ctx.globalAlpha = b.i < HIST ? 0.4 : 0.85; ctx.beginPath(); ctx.moveTo(X(b.p.i), y); ctx.lineTo(X(b.i), y); ctx.stroke(); ctx.restore();
    j3Chip(X(b.i) + 4, y + (b.d > 0 ? -18 : 3), `broke ${b.p.lab} ${ARR(b.d)}`, col, {dim: b.i < HIST, up: b.d > 0, alt: w => [X(b.i) - w - 4],
      html: `<b>${D.mins[b.i]} · structure broke ${ARR(b.d)}</b>` + tg([["what", `a 1-min close ${b.d > 0 ? "above" : "below"} the last confirmed swing ${b.d > 0 ? "high" : "low"}`], ["swing", `${b.p.lab} ${f1(b.p.px)}f · made ${b.p.t} · known ${b.p.known}`], ["the close", `${f1(D.fut[b.i])}f`]])}); }
  ctx.font = "700 9px " + MONO;
  for (const p of K) { if (!LY.hist && K.indexOf(p) < K.length - 3) continue;   // NOW view: the last three confirmed swings keep their pill; the line still runs through all of them
    const up = p.kind === "H", w = ctx.measureText(p.lab).width + 8, x = X(p.i) - w / 2;
    const at = place([x, x + w / 2 + 3, x - w / 2 - 3], Math.max(pTop + 1, Math.min(pBot - 14, Y(p.px) + (up ? -17 : 4))), w, 13, up);
    ctx.save(); ctx.font = "700 9px " + MONO; ctx.globalAlpha = p.i < HIST ? 0.5 : 1; ctx.fillStyle = COL.ink; rr(at.x, at.y, w, 13, 4); ctx.fill(); ctx.fillStyle = "#fff"; ctx.fillText(p.lab, at.x + 4, at.y + 10); ctx.restore();
    HIT.push({x: at.x, y: at.y, w, h: 13, html: `<b>swing ${p.lab} · ${f1(p.px)}f · ${fmt(p.px - bas[clampI(p.i)])}s</b>` + tg([["made", p.t], ["known", `${p.known} · a swing is known only after price turns away from it`]])}); }
}
function paLine(i) {                // the panel's PRICE ACTION line: the last two confirmed swings, a break since, and where price sits on her bands
  const {P, br} = pa(), K = P.filter(p => p.ki <= i), k = clampI(i), z = D.vwap && D.sd && D.sd[k] ? (D.fut[k] - D.vwap[k]) / D.sd[k] : null, s = z == null ? "" : z >= 0 ? "u" : "d";
  const at = z == null ? "bands forming" : `${z >= 0 ? "above" : "below"} VWAP · ` + (Math.abs(z) < 1 ? `inside ${s}1` : Math.abs(z) < 2 ? `${s}1–${s}2` : Math.abs(z) < 3 ? `${s}2–${s}3, your ${z >= 0 ? "sell" : "buy"} zone` : `beyond ${s}3`);
  if (K.length < 2) return `no swing confirmed yet · ${at}`;
  const H = K.filter(p => p.kind === "H").pop(), L = K.filter(p => p.kind === "L").pop(), b = br.filter(x => x.i <= i).pop(), lastP = Math.max(...K.map(p => p.i));
  return K.slice(-2).map(p => p.lab).join(" → ") + " · " + (b && b.i > lastP ? `broke ${b.p.lab} ${f1(b.p.px)}f ${ARR(b.d)} at ${D.mins[b.i]}` : H && L ? `inside ${L.lab} ${f1(L.px)}f – ${H.lab} ${f1(H.px)}f` : "one side only so far") + ` · ${at}`;
}

/* ---- the sync lane: N · BN · SX, one cell per closed 3-min bar */
function syncOf() {                 // the mockup: the build script's sync layer. The live page: the same rule computed here from the frame, once per frame
  if (J3.sync) return J3.sync; if (SYNC) return SYNC;
  const ser = [[D.fut, D.fo], [D.bnf, null], [D.sx, null]], hist = [[], [], []], bars = [];
  const med = a => { const s = a.slice().sort((x, y) => x - y), n = s.length; return n % 2 ? s[n >> 1] : (s[n / 2 - 1] + s[n / 2]) / 2; };
  for (let a = 0; a < N - 2; a += 3) {
    const row = ser.map(([cl, op], n) => { if (!cl) return null;
      const o = op ? op[a] : a ? cl[a - 1] : cl[a], c = cl[a + 2]; if (o == null || c == null) return null;      // could not read: never a zero
      const ch = Math.round((c - o) * 10) / 10, m = hist[n].length ? med(hist[n]) : null; hist[n].push(Math.abs(c - o));
      return [ch, m != null && Math.abs(c - o) < m, m == null ? null : Math.round(m * 10) / 10]; });
    const s = row.map(c => c ? Math.sign(c[0]) : null);
    bars.push({a, v: row, all: s.includes(null) ? null : s[0] && s[0] === s[1] && s[1] === s[2] ? s[0] : 0});
  }
  return SYNC = {bars, lead: "lead / lag: not in this frame", rows: ["N f", "BN s", "SX s"]};
}
function j3Lane(end) {
  if (!LY.sync && !LY.opt && !LY.str) return;
  const S = syncOf(), half = plotW() / N / 2, rh = 9, lx = Wd - padR + 6;
  let y0 = sTop;
  ctx.font = "600 9px " + MONO;
  if (LY.str) {                     // STRENGTH (shadow): one cell per 3-min close; the deeper the green (buyers) or the red (sellers), the higher that side's number
    ctx.fillStyle = COL.mut; ctx.fillText("STR", lx, y0 + 7.5); ctx.fillText("strength % · green buyers · red sellers", lx + 38, y0 + 7.5);
    for (const r of MR) { if (r.ki > end) break;
      const x0 = X(r.i - 2) - half + 0.5, w = X(r.i) + half - x0 - 0.5;
      ctx.save(); ctx.fillStyle = COL.up; ctx.globalAlpha = r.up / 100; ctx.fillRect(x0, y0, w, 5); ctx.fillStyle = COL.dn; ctx.globalAlpha = r.dn / 100; ctx.fillRect(x0, y0 + 5, w, 5); ctx.restore();
      HIT.push({x: x0, y: y0, w, h: 10, html: meterTip(r)}); }
    y0 += 12;
  }
  if (LY.opt) {                     // v2: the option-flow word of EACH 3-min close (the settled word waits for two closes the same way, and
    // so read QUIET through the 13:32 dump); a stretch of closes with the same word is one segment
    ctx.fillStyle = COL.mut; ctx.fillText("OPT", lx, y0 + 7.5); ctx.fillText("option flow, each 3-min close · grey QUIET", lx + 38, y0 + 7.5);
    const C = J3.opt.closes; let a = 0;
    while (a < C.length && C[a].ki <= end) {
      let b = a; while (b + 1 < C.length && C[b + 1].ki <= end && C[b + 1].raw === C[a].raw) b++;
      const c = C[a], nx = C[b + 1], e = Math.min(end, nx ? nx.ki - 1 : end), cant = c.raw === "OI?", x0 = X(c.ki) - half, w = Math.max(2, X(e) + half - x0);
      ctx.save();
      if (cant) { ctx.strokeStyle = COL.warn; ctx.globalAlpha = 0.6; ctx.setLineDash([2, 2]); ctx.strokeRect(x0 + 0.5, y0 + 0.5, Math.max(1, w - 1), rh - 1); }
      else { ctx.fillStyle = c.lr > 0 ? COL.up : c.lr < 0 ? COL.dn : COL.q; ctx.globalAlpha = c.lr ? 0.85 : 0.3; ctx.fillRect(x0, y0, Math.max(1, w - 1), rh); }
      ctx.restore();
      if (!cant && ctx.measureText(c.raw).width + 6 <= w) { ctx.fillStyle = c.lr ? "#fff" : COL.mut; ctx.fillText(c.raw, x0 + 3, y0 + 7.5); }
      HIT.push({x: x0, y: y0, w, h: rh, html: laneTip(C[b])});
      a = b + 1;
    }
    y0 += rh + 1;
  }
  if (!LY.sync) return;
  ctx.fillStyle = COL.mut;
  S.rows.forEach((s, r) => ctx.fillText(s, lx, y0 + r * (rh + 1) + 7.5));
  ctx.fillText("sync · 3-min · box = stretch all 3 agree", lx + 38, y0 + 7.5);
  ctx.fillText("pale = under its own median so far", lx + 38, y0 + 17.5);
  ctx.fillText(S.lead, lx + 38, y0 + 27.5);
  let run = null;                   // ONE box around a stretch of bars where all three agree the same way (a box per bar read as a barcode)
  const box = r => { ctx.save(); ctx.strokeStyle = COL.ink; ctx.globalAlpha = 0.65; ctx.lineWidth = 1; ctx.strokeRect(r.x0 - 0.5, y0 - 1.5, r.x1 - r.x0 + 1, 3 * rh + 5); ctx.restore(); };
  for (const b of S.bars) {
    if (b.a + 3 > end) break;
    const x0 = X(b.a) - half + 0.5, w = X(b.a + 2) + half - x0 - 0.5;
    b.v.forEach((c, r) => { const y = y0 + r * (rh + 1);
      if (!c) { ctx.save(); ctx.strokeStyle = COL.warn; ctx.globalAlpha = 0.6; ctx.setLineDash([2, 2]); ctx.strokeRect(x0 + 0.5, y + 0.5, Math.max(1, w - 1), rh - 1); ctx.restore(); return; }
      ctx.fillStyle = c[0] > 0 ? COL.up : c[0] < 0 ? COL.dn : COL.q; ctx.globalAlpha = c[1] ? 0.25 : 0.9; ctx.fillRect(x0, y, w, rh); ctx.globalAlpha = 1; });
    if (b.all && run && run.d === b.all && run.next === b.a) { run.x1 = x0 + w; run.next = b.a + 3; }
    else { if (run) box(run); run = b.all ? {d: b.all, x0, x1: x0 + w, next: b.a + 3} : null; }
    const cell = (c, u) => !c ? "could not read" : `${sg1(c[0])}${u}` + (c[2] == null ? " · no earlier bar to compare" : c[1] ? ` · small (median ${c[2]})` : ` · median ${c[2]}`);
    HIT.push({x: x0, y: y0 - 2, w, h: 3 * (rh + 1) + 2, html: `<b>${D.mins[b.a]}–${D.mins[b.a + 2]}</b>` + tg([
      ["NIFTY fut", cell(b.v[0], "f")], ["BANKNIFTY spot", cell(b.v[1], "s")], ["SENSEX spot", cell(b.v[2], "s")],
      ["all 3", b.all ? `agree ${ARR(b.all)}` : b.all === 0 ? "do not agree" : "could not check"], ["lead / lag", S.lead.replace(/^lead \/ lag: /, "")]])});
  }
  if (run) box(run);
}

/* ---- the timeline rail: one segment per band; a click on it jumps to the band's start */
function j3Rail() {
  if (!LY.bands) return; const i = cur();
  for (const b of J3.bands) {
    const known = b.ci <= i, frozen = b.ei != null && b.ei + 1 <= i, e = b.ei != null ? b.ei : N - 1, x0 = TX(b.si) - 1, x1 = TX(known && !frozen ? Math.min(i, e) : e) + 1;
    tctx.globalAlpha = !known ? 0.3 : frozen ? 1 : 0.7; tctx.fillStyle = b.d > 0 ? COL.up : COL.dn; tctx.fillRect(x0, 1, Math.max(2, x1 - x0), 4);
    tctx.globalAlpha = 1; tctx.fillStyle = "#fff"; for (const g of b.legs.slice(1)) tctx.fillRect(TX(g.si) - 1.5, 1, 1, 4);   // a notch where a same-side push begins
  }
  tctx.globalAlpha = 1;
}
function j3RailHit(q) {             // the band (and the push of it) under the pointer, on the rail's top strip
  if (!LY.bands || !q || q.y > 8) return null;
  const b = J3.bands.find(v => q.x >= TX(v.si) - 2 && q.x <= TX(v.ei != null ? v.ei : N - 1) + 2); if (!b) return null;
  let g = b.legs[0]; for (const v of b.legs) if (TX(v.si) - 2 <= q.x) g = v;
  return {b, g, si: g.si};
}
function j3RailTip(h) {
  const b = h.b, e = b.ei != null ? b.ei : N - 1, n = b.legs.indexOf(h.g), k = (b.legs[n + 1] ? b.legs[n + 1].si - 1 : e) - h.g.si;
  return `<b>${D.mins[h.g.si]}–${D.mins[h.g.si + k]} · ${ARR(b.d)} ${esc(h.g.nm[k] || "no name")}</b>` + tg([
    ["Dext delta", h.g.dl[k] == null ? "could not read" : `${sgn(h.g.dl[k])} lots`], ["futures OI", h.g.oi[k] == null ? "could not read" : `${sgn(h.g.oi[k])} lots`],
    ["band", `${D.mins[b.si]}–${b.ei != null ? D.mins[b.ei] : "open"} · push ${n + 1} of ${b.legs.length}`],
    ["whole band", `${b.name || "no name"} · Δ ${b.delta == null ? "?" : sgn(b.delta)} · OI ${b.oich == null ? "?" : sgn(b.oich)} lots`],
    ["ended", b.why], ["click", `jump to ${D.mins[h.g.si]}`]]);
}
function j3Hover(mx, my, tip) {
  let h = null; for (const r of HIT) if (mx >= r.x && mx <= r.x + r.w && my >= r.y && my <= r.y + r.h) h = r;
  if (!h) return false;
  tip.innerHTML = h.html; tip.style.left = Math.max(4, Math.min(Wd - 350, mx + 10)) + "px"; tip.style.opacity = 1;
  tip.style.top = (stage.offsetTop + (my + tip.offsetHeight + 24 > Ht ? my - tip.offsetHeight - 10 : my + 14)) + "px";
  return true;
}

/* ---- the events the new layers add to the log (band start / line move / end, option-flow word changes, the DEMO voice) */
function j3Events() {
  PAC = null; SYNC = null;          // a new frame (the live page: every poll): the swing and sync caches are rebuilt from it
  const E = (i, o) => { if (i >= 0 && i <= N - 1 + 0.99) ev.push(Object.assign({i, j3: true}, o)); };
  for (const e of ev) if (!e.j3 && e.zone) {               // the page itself now words a zone trigger by her verdict (A279); the log only needs its one short line
    const z = e.zone, zs = zoneSay(z, null); e.short = `${fmt(z.px)}f ${z.band || ""} · ${zs.short}`; }   // A294: the three reads in one line
  for (const c of J3.opt.closes) { if (!c.cover) continue; const pe = c.cover.side === "PE";
    E(c.ki + 0.031, {tag: "OPTION FLOW", tagc: pe ? "bad" : "ok", opt: c, dir: pe ? -1 : 1, cat: "opt", major: true,
      short: `${pe ? "put" : "call"} writers running ×${c.cover.n} ${sL(c.cover.doi)} · as of ${c.t}`,
      text: `**${pe ? "Put" : "Call"} writers running** · covering on ${c.cover.n} strikes, ${sL(c.cover.doi)} in 3 min · this close reads ${c.raw} · as of ${c.t}.`,
      chips: [{t: `as of ${c.t}`}, {t: "3-min close"}]}); }
  for (const b of J3.bands) {
    const side = b.d > 0 ? "below" : "above", e = b.ei != null ? b.ei : N - 1, q = v => v == null ? "?" : sgn(v);
    const way = i => { const r = optAt(i), w = wayWord(b.d, r); return {t: `option flow: ${w.t}` + (r && r.said !== "OI?" ? ` · as of ${r.t}` : ""), c: w.c}; };
    b.legs.forEach((g, n) => {
      const line = (b.steps.filter(s => s[0] <= g.ci).pop() || b.steps[0])[1], pv = b.legs[n - 1], pk = pv ? g.si - 1 - pv.si : 0;
      if (!n) E(g.ci + 0.02, {tag: `MOVE ${ARR(b.d)}`, band: b, dir: b.d, jump: g.si, cat: "moves", major: true, short: `from ${D.mins[g.si]} · line ${f1(line)}f · over ${side} it`,
        text: `**MOVE ${ARR(b.d)} from ${D.mins[g.si]}** · a PUSH bar closed (size ×${g.size}) · line **${f1(line)}f** · over ${side} it.`,
        chips: [{t: `origin ${f1(g.origin)}f`}, {t: `line ${f1(line)}f`}, way(g.ci)], wr: `over if: a trade ${side} ${f1(line)}f, or an opposite PUSH bar`});
      else E(g.ci + 0.02, {tag: `MOVE ${ARR(b.d)} +PUSH`, band: b, dir: b.d, jump: g.si, cat: "moves", major: true,
        short: `from ${D.mins[g.si]} · line ${f1(line)}f · before: ${pv.nm[pk] || "no name"} ${q(pv.dl[pk])} lots`,
        text: `**MOVE ${ARR(b.d)} goes on from ${D.mins[g.si]}** · a same-side PUSH closed (size ×${g.size}) · line **${f1(line)}f** · before it: ${pv.nm[pk] || "no name"} Δ ${q(pv.dl[pk])} lots · OI ${q(pv.oi[pk])}.`,
        chips: [{t: `line ${f1(line)}f`}, {t: `${D.mins[pv.si]}–${D.mins[g.si - 1]} ${pv.nm[pk] || "no name"}`}, way(g.ci)], wr: `over if: a trade ${side} ${f1(line)}f, or an opposite PUSH bar`});
    });
    const lg = b.legs[b.legs.length - 1], lk = e - lg.si;
    if (b.ei != null) E(b.ei + 1.01, {tag: `MOVE ${ARR(b.d)} OVER`, band: b, dir: b.d, jump: lg.si, cat: "moves",
      short: `${lg.nm[lk] || "no name"} ${D.mins[lg.si]}–${D.mins[b.ei]} · Δ ${q(lg.dl[lk])} · OI ${q(lg.oi[lk])} lots`,
      text: `**${lg.nm[lk] || "MOVE"} ${ARR(b.d)} over** · ${D.mins[lg.si]}–${D.mins[b.ei]} · Δ **${q(lg.dl[lk])} lots** · fut OI **${q(lg.oi[lk])} lots** · ${b.why}`
        + (b.legs.length > 1 ? ` · whole band ${D.mins[b.si]}–${D.mins[b.ei]}: ${b.name || "no name"} Δ ${q(b.delta)} · OI ${q(b.oich)}.` : "."),
      chips: [{t: lg.nm[lk] || "no name: delta or OI not read"}, {t: `${b.legs.length} push${b.legs.length > 1 ? "es" : ""} in the band`}, way(b.ei + 1)]});
  }
  for (const c of J3.opt.changes) { const cant = c.said === "OI?";
    E(c.ki + 0.03, {tag: "OPTION FLOW", tagc: cant ? "warn" : c.lean > 0 ? "ok" : c.lean < 0 ? "bad" : "q", opt: c, dir: c.lean, cat: "opt",
      short: cant ? `could not read · OI missing at the ${c.t} close` : `${c.said} · cap ${c.capw} · floor ${c.floorw} · as of ${c.t}`,
      text: cant ? `**option flow could not be read** · OI not on the record at the ${c.t} close.`
        : `**option flow: ${c.said}** · cap ${c.capw} · floor ${c.floorw} · as of ${c.t}.`,
      chips: [{t: `as of ${c.t}`}, {t: "3-min close"}]}); }
  const T = J3.trade;
  if (DEMO && T) { let was = null;
    E(T.ei + 1.0, {tag: "DEMO IN", tagc: "warn", cat: "trade", major: true, demo: true, short: `${T.side} ${f1(T.px)}f · the ${T.t} bar's close · display only`, text: `**DEMO · in the ${T.t} ${T.side} at ${f1(T.px)}f** · stop ${T.stops.length ? f1(T.stops[0][1]) + "f, " + T.stops[0][2] : "not on the record"} · display only.`, chips: [{t: "DEMO", c: "warn"}]});
    for (const bk of T.book || []) E(bk.i + 0.05, {tag: bk.w, tagc: bk.w === "BOOK" ? "warn" : "q", cat: "trade", demo: true, short: bk.why,   // the new book / trail line
      text: `**${bk.w}** (new line) · ${bk.why} · ${sg1(bk.pts)} pts then.`, chips: [{t: "book / trail, new"}, {t: "DEMO", c: "warn"}]});
    for (const v of T.voice) { if (v.w === was) continue; was = v.w;
      E(v.i + 0.04, {tag: `DEMO ${v.w}`, tagc: v.w === "HOLD" ? "ok" : v.w === "TIGHTEN" ? null : v.w === "WARN" ? "warn" : "bad", cat: "trade", major: v.w === "EXIT", demo: true, short: v.why,
        text: `**${v.w}** · ${v.why}.`, chips: [{t: "DEMO", c: "warn"}, {t: `said at the ${v.t} close`}]}); } }
  ev.sort((a, b) => a.i - b.i);
}
function catOf(e) {
  if (e.cat) return e.cat;
  if (e.zone || e.mz || /TRIGGER|MANAGE/.test(e.tag)) return "trade";
  if (e.ans || e.crack || e.toot || e.floor || /^(HELD|BROKEN|BREAK|DEFENDED|BUYERS IN|TRAPPED|NEW FIGHT|WEAKENING|RETREATING|NEW FLOOR|PINNED|CAN'T SEE)/.test(e.tag)) return "walls";
  if (e.push || e.signs || /^(PUSH|FUEL|WRITERS|OPTIONS FUEL|TOP|BOTTOM)/.test(e.tag)) return "moves";
  return "other";
}
function shortOf(e) {               // the log's one line: whole clauses of the event's own text, ten words at most, nothing cut with "…"
  if (e.short) return e.short;
  if (e.zone) return `${fmt(e.zone.px)}f ${e.zone.band} · read ${vword(e.verdict)}`;
  let s = plainT(e.text).replace(/\s+/g, " ").trim();
  s = s.replace(new RegExp("^" + e.tag.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*[·:.]?\\s*", "i"), "");
  const cnt = v => v.split(/\s+/).filter(w => /[A-Za-z0-9]/.test(w)).length, out = [];
  let n = 0;
  for (const p of s.split(/ · |\. | — |, /)) { const w = cnt(p); if (out.length && n + w > 10) break; out.push(p.trim()); n += w; if (n >= 10) break; }
  let r = out.join(" · ").replace(/[.:]$/, "");
  if (cnt(r) > 10) { const ws = r.split(/\s+/); let c = 0, k = 0; for (; k < ws.length; k++) if (/[A-Za-z0-9]/.test(ws[k]) && ++c > 10) break; r = ws.slice(0, k).join(" "); }
  return r || e.tag;
}
function rowHTML(e, n) {            // one line per event: time · tag · ≤ 10 words; the whole sentence on hover; a chat line keeps its text
  const hmm = D.mins[clampI(e.i)], cls = `${e.major ? "major" : ""} ${e.tagc || ""} ${e.you ? "you" : ""}`;
  if (n < 0) return `<div class="row ${cls}" data-n="-1" data-i="${e.i}" data-cat="chat"><span class="rt">${hmm}</span><span class="rtag ${e.tagc || ""}">${esc(e.tag)}</span><span class="rx">${mark(e.text)}</span></div>`;
  const d = e.dir != null ? e.dir : e.push ? e.push.dir : /▲/.test(e.tag) ? 1 : /▼/.test(e.tag) ? -1 : 0, you = e.demo ? "" : demoSide(d, e.i, e.i);
  const ex = (you ? `<span class="c1 ${you === "with you" ? "ok" : "bad"}">${you}</span>` : "") + (e.src ? `<span class="rsrc">${esc(e.src)}</span>` : "");
  return `<div class="row ${cls}" data-n="${n}" data-i="${e.i}"${e.jump != null ? ` data-j="${e.jump}"` : ""} data-cat="${catOf(e)}" title="${escA(plainT(e.text))}"><span class="rt">${hmm}</span><span class="rtag ${e.tagc || ""}">${esc(e.tag)}</span><span class="rx">${esc(shortOf(e))}</span>${ex ? `<span class="ex">${ex}</span>` : ""}</div>`;
}

/* ---- the DEMO trade (display only): the day's real first zone trigger as if she were in it */
function demoAt(i) {
  const T = J3.trade; if (!DEMO || !T) return null;
  if (i < T.ei + 1) return {wait: true};
  const out = !!T.exit && T.exit.i + 1 <= i, k = clampI(i);
  let stop = null, why = "no stop on the record yet"; for (const [j, v, w] of T.stops) if (j <= i) { stop = v; why = w; }
  let v = null; for (const s of T.voice) { if (s.i <= i) v = s; else break; }
  return {out, stop, why, v, pts: out ? T.exit.pts : T.d * (D.fut[k] - T.px)};
}
const VC = {HOLD: "ok", TIGHTEN: "q", WARN: "warn", EXIT: "bad"};

/* ---- the right panel's five fixed blocks (the old card lives on behind "detail") */
function j3Panel(i) {
  const k = clampI(i), c = D.calls ? D.calls[k] : D.call, S = c && c.mstate, P = (c && c.count && c.count.pieces) || [], pc = q => P.find(p => p.k === q);
  // 1 · THE WORD and ONE action
  const word = c ? (S && S.word) || c.word : null, act = c && c.action ? c.action.said : null, dir = S ? S.dir : 0, lean = c ? c.lean || 0 : 0, cant = !word || word === "CAN'T SEE";
  const wq = (word || "no call: could not check").match(/^(.*?)(\s*\(.*\))?$/);   // the word big, its qualifier small on the same line
  $("#w1").innerHTML = esc(wq[1]) + (wq[2] ? ` <small>${esc(wq[2].trim())}</small>` : ""); $("#w1").style.color = cant ? COL.mut : dir > 0 ? COL.up : dir < 0 ? COL.dn : COL.ink;
  $("#a1").textContent = act || "—"; $("#a1").style.color = /▲/.test(act || "") ? COL.up : /▼/.test(act || "") ? COL.dn : COL.ink;
  const as = c && c.action && c.action.since; $("#a1s").hidden = !as; $("#a1s").textContent = as ? "since " + as : "";
  $("#s1").textContent = c ? [c.at && "at " + c.at, c.since && "since " + c.since, S && S.vol && S.vol.word && "vol " + S.vol.word].filter(Boolean).join(" · ") : "";
  $("#b1").title = c ? [c.action_why, S && S.why].filter(Boolean).join("\n") : "";
  $("#pa1").innerHTML = `<span class="lab">PRICE ACTION</span>${esc(paLine(i))}`;
  // 2 · TWO PRICES, each futures with spot beside, from the call's own wrong-line and its wall ahead
  const b = bas[k], num = s => +String(s).replace(/,/g, ""), wl = (c && c.wrong_line) || "";
  const fs = (v, tag) => tag === "f" ? [`${fmt(v)}f`, `${fmt(v - b)}s`] : [`${fmt(v + b)}f`, `${fmt(v)}s`];
  const rg = wl.match(/outside ([\d,.]+)s \(([\d,.]+)f\)\s*[–-]\s*([\d,.]+)s \(([\d,.]+)f\)/), pal = wl.match(/PALAT at ([\d,.]+)([fs])/), lv = [...wl.matchAll(/(\d[\d,]*(?:\.\d+)?)([fs])(?![A-Za-z])/g)];
  let p1 = "—", p1s = c ? "the call names no line here" : "no call: could not check";
  if (rg) { p1 = `${rg[2]}f–${rg[4]}f`; p1s = `${rg[1]}s–${rg[3]}s · a 3-min close outside`; }
  else if (pal) { const v = fs(num(pal[1]), pal[2]); p1 = v[0]; p1s = `${v[1]} · PALAT: the lean ends`; }
  else if (lv.length) { const m = lv[lv.length - 1], v = fs(num(m[1]), m[2]); p1 = v[0]; p1s = `${v[1]} · ${(wl.match(/back to [▲▼]|new (?:low|high)/) || ["the call's line"])[0]}`; }
  $("#p1").textContent = p1; $("#p1s").textContent = p1s; $("#p1").parentNode.title = wl;
  const wa = pc("wall_ahead"), wm = wa && wa.text.match(/wall ahead ([\d,]+)s (CE|PE)(?: ([\d.]+L))?(?: (\w+))?/);
  let p2 = "—", p2s = wa ? wa.text.replace(/^could not check — /, "could not check: ") : c ? "the call names no wall ahead" : "no call: could not check";
  if (wm) { const kk = num(wm[1]), f = lvl(kk, k); p2 = `${fmt(f)}f`; p2s = `${fmt(kk)}s ${wm[2]} ${wm[3] || "?"} ${(wm[4] || "").toLowerCase()} · ${sgn(f - D.fut[k])} pts`; }
  $("#p2").textContent = p2; $("#p2s").textContent = p2s; $("#p2").parentNode.title = wa ? wa.text : "";
  // 3 · WHO AGREES, against the lean the call's own count is taken on; BLIND when the read is missing
  const PW = {with: ["WITH", "ok"], against: ["AGAINST", "bad"], flat: ["FLAT", "q"], blind: ["BLIND", "warn"]};
  const row = (name, st, words, nums, tip) => `<span class="n">${name}</span><span class="pw ${PW[st][1]}">${PW[st][0]}</span><span class="t" title="${escA(tip || "")}"><b>${esc(words)}</b>${nums ? ` <i>${esc(nums)}</i>` : ""}</span>`;
  const piece = (name, q, re, f) => { const p = pc(q);
    if (!p) return row(name, "blind", "no call at this minute", "", "");
    if (p.state === "blind") return row(name, "blind", p.text.replace(/^could not check — /, ""), "", p.text);
    const m = p.text.match(re), v = m ? f(m) : [p.text, ""]; return row(name, PW[p.state] ? p.state : "flat", v[0], v[1], p.text); };
  const r = optAt(i), sp = D.reads && D.reads.speed ? D.reads.speed[k] : null;
  // v2: OI coming off while price goes the OTHER way is not writers being pushed out (13:31: CE −12.0L while price fell 40 pts was read "▲")
  const wfp = pc("wf7"), wfm = wfp && wfp.state !== "blind" && wfp.text.match(/writers ±7 (.+?) \((.+?) \/ 3 min\)/), wdir = wfm ? (/UP|▲/.test(wfm[1]) ? 1 : /DOWN|▼/.test(wfm[1]) ? -1 : 0) : 0, pm3 = k >= 3 ? D.fut[k] - D.fut[k - 3] : 0;
  let h = wdir && pm3 * wdir < 0
    ? row("Writers (OI)", "flat", `${wdir > 0 ? "calls" : "puts"} cut INTO the ${pm3 < 0 ? "fall" : "rise"}: no push`, `${wfm[2]} · price ${sg1(Math.round(pm3))}`,
        `the brain read: ${wfp.text}. OI came off while price went the other way: longs out or writers booking, not writers pushed out. The option-flow close names who.`)
    : piece("Writers (OI)", "wf7", /writers ±7 (.+?) \((.+?) \/ 3 min\)/, m => [`±7 ${m[1]}`, m[2]]);
  h += !J3.opt.ok ? row("Option flow", "blind", J3.live ? "not live yet" : "not on the record", "", J3.opt.why) : !r ? row("Option flow", "blind", `first read ${J3.opt.first}`, "", "no 3-min close yet")
    : r.raw === "OI?" ? row("Option flow", "blind", "OI not read", `as of ${r.t}`, r.why)
    : row("Option flow", !lean || !r.lr ? "flat" : r.lr === lean ? "with" : "against", r.raw,
        `cap ${sL(r.cap.doi)} · floor ${sL(r.floor.doi)}${r.cover ? ` · ${r.cover.side} writers run ×${r.cover.n}` : ""} · as of ${r.t}`,
        `this close: ${r.raw} · settled word: ${r.said} · cap ${r.cap.word} · floor ${r.floor.word}`);
  h += piece(`<span title="Futures flow (Dext)">Fut flow (Dext)</span>`, "speed", /speed (.+)/, m => [m[1], sp && sp.d3 != null ? `${sgn(sp.d3)} lots` : ""]);
  h += piece("Futures OI", "fut_oi", /fut OI (.+?) ([+−-][\d,]+ lots).*/, m => [m[1], m[2]]);
  $("#agree").innerHTML = h; $("#g0").textContent = lean ? `vs the ${ARR(lean)} lean` : "";
  const a3 = pc("all3"), ga = $("#gAll"), am = a3 && a3.text.match(/all 3 ([▲▼])/);
  ga.className = "c1 " + (!a3 || a3.state === "blind" ? "warn" : a3.state === "with" ? "ok" : a3.state === "against" ? "bad" : "q");
  ga.textContent = !a3 || a3.state === "blind" ? "ALL 3 not read" : am ? `ALL 3 ${am[1]} · ${a3.state}` : "3 mixed"; ga.title = a3 ? a3.text : "";
  // 4 · IN TRADE: only while a trigger is live or the DEMO trade is on
  const b4 = $("#b4"), T = J3.trade, dm = demoAt(i), cell = (n, v, wide) => `<div${wide ? ' class="w"' : ""}><span class="n">${n}</span><span class="t">${v}</span></div>`;
  const mv = mtVoice();
  if (mv) {                         // the live page, her MARKED trade: the server's one voice (voice.py + the trade map), every line as it came
    const v = mv.v, lines = v.ok ? [v.l1, v.l2, (v.l3 || "") + (v.trig_t && v.state !== "HOLD" ? ` · ${v.trig_t}` : ""), v.l4, v.l5, v.l6].filter(Boolean) : [v.why || "could not check: no reason given"];
    b4.hidden = false;
    b4.innerHTML = `<div class="k"><span>YOUR TRADE · the one voice</span><span class="c1 ${v.ok ? VC[v.state] || "q" : "warn"}">${esc(v.ok ? v.state : "could not check")}</span></div>`
      + lines.map((s, n) => `<div class="zl${n ? " q" : ""}">${esc(s)}</div>`).join("")
      + `<div class="zl q">as of ${mv.at} · display only: you place and move your own stop</div>`;
  } else if (dm) {
    const st = T.strike, w = r && st ? r.st[st.k + st.side] : null;
    const mine = !st ? "could not read the spot at entry" : !r ? `${fmt(st.k)} ${st.side} · no option-flow read yet (first ${J3.opt.first})`
      : !w ? `${fmt(st.k)} ${st.side} · outside ATM ±3 at ${r.t}: not read` : w[0] === "OI?" || w[0] === "FLOW?" ? `${fmt(st.k)} ${st.side} · could not read (${w[0]}) · as of ${r.t}`
      : `<b>${fmt(st.k)} ${st.side} ${w[0]}${w[1] === true ? " FIRM" : ""}</b> · OI ${sL(w[2])} · Δ ${sL(w[3])} · as of ${r.t}`;
    b4.hidden = false;
    b4.innerHTML = `<div class="k"><span>IN TRADE</span><span class="c1 warn">DEMO · display only</span></div><div class="tgrid">`
      + (dm.wait ? cell("waiting", `the ${T.t} ${T.side} trigger · entry at its bar's close ${D.mins[T.ei]}`, true)
        : cell("side · entry", `<b>${T.side} ${f1(T.px)}f</b> · ${fmt(T.px - bas[T.ei])}s <i>· ${T.t} bar's close</i>`)
          + cell(dm.out ? "points at exit" : "points now", `<span class="big ${dm.pts >= 0 ? "up" : "dn"}">${sg1(dm.pts)}</span>`)
          + cell("stop", dm.stop == null ? "no stop on the record yet" : `<b>${f1(dm.stop)}f</b> · ${fmt(dm.stop - b)}s <i>· ${esc(dm.why)}</i>`)
          + cell("voice", dm.v ? `<span class="c1 ${VC[dm.v.w]}">${dm.v.w}</span> <i>${dm.v.t} close</i><br>${esc(dm.v.why)}` : "speaks at the next 3-min close")
          + cell("book / trail · new", (nb => nb ? `<b>${nb.w}</b> · ${esc(nb.why)} <i>· ${nb.t}</i>` : "nothing yet: no place reached, no new line")((T.book || []).filter(q => q.i <= i).pop()), true)
          + cell("book / trail · old", (ob => ob ? `<b>${esc(ob.st)}</b> <i>· ${ob.at} · ${sg1(ob.pts)} pts${ob.trail ? ` · trail ${ob.trail[0]} ${fmt(ob.trail[1])}f` : ""}${ob.against.length ? ` · against: ${esc(ob.against.join(", "))}` : ""}</i>` : "nothing yet")((T.old || []).filter(q => q.b + 1 <= i).pop()), true)
          + cell("your strike", `${mine} <span class="c1 warn">DEMO</span>`, true)) + `</div>`;
  } else {
    const lt = lastTrigger(i), q = D.reads && D.reads.trade ? D.reads.trade[k] : null, on = lt && (!q || q.window !== false), zs = lt ? zoneSay(lt.z, i) : null;
    b4.hidden = !on;
    const rd = (r, k, s) => `<b class="${r.yes === true ? "up" : r.yes === false ? "dn" : ""}">${r.yes === true ? "✓" : r.yes === false ? "✗" : "?"} ${k}</b> ${esc(s)}`;   // the panel's lines are a few words; the whole read is in the hover and the log
    const cs = zs ? (zs.c ? zs.v + (zs.c.kind === "fade" ? ` ${zs.c.n}/${zs.c.N}` : "") + (zs.bm != null ? ` · band ${sg1(zs.bm)} pts` : "") : zs.reads[1].s) : "";
    if (on && !zs.clean) b4.innerHTML = `<div class="k"><span>LAST ZONE · ${zs.skip ? "not a trade" : zs.wait ? "plan could not check" : "in a trade already"}</span><span class="c1 ${zs.cls}">${esc(zs.label)}</span></div>`   // A294: SKIP only when none of the
      + `<div class="zl"><b>${lt.z.side} ${fmt(lt.z.px)}f</b> · ${fmt(lt.z.px - bas[clampI(ix(lt.z.t))])}s · ${String(lt.z.t).slice(0, 5)} ${lt.z.band || ""} · price since <span class="${lt.pts >= 0 ? "up" : "dn"}">${sg1(lt.pts)}</span></div>`   // three reads says take; else the three, each with its number
      + `<div class="zl q" title="${escA(zs.why.join("\n"))}">info: ${rd(zs.reads[0], "old", zs.reads[0].s)} · ${rd(zs.reads[1], "card", cs)}</div>`   // two lines, a few words a read; the whole of each on hover
      + `<div class="zl q" title="${escA(zs.why.join("\n"))}">${rd(zs.reads[2], "gate", zs.reads[2].s.replace(" of the wall", "").replace(/[()]/g, ""))}${zs.atBand ? ` · <b>at band</b> ${esc(zs.atBand.s)}` : ""}</div>`
      + (zs.split && lt.st ? `<div class="zl q">manage · ${esc(lt.st)}${lt.trail ? ` · trail ${lt.trail[0]} ${fmt(lt.trail[1])}f` : ""}</div>` : "");
    else if (on) b4.innerHTML = `<div class="k"><span>IN TRADE · last trigger</span><span class="c1 ${zs.cls}">${esc(zs.label)}</span></div><div class="tgrid">`
      + cell("side · entry", `<b>${lt.z.side} ${fmt(lt.z.px)}f</b> · ${fmt(lt.z.px - bas[clampI(ix(lt.z.t))])}s <i>· ${lt.z.t} ${lt.z.band}</i>`)
      + cell("points now", `<span class="big ${lt.pts >= 0 ? "up" : "dn"}">${sg1(lt.pts)}</span> <i>· ${lt.age} min</i>`)
      + cell("manage", lt.st ? `<span class="c1 ${lt.st === "HOLD" ? "ok" : "bad"}">${esc(lt.st)}</span>` : "reading at 3-min closes")
      + cell("trail", lt.trail ? `${lt.trail[0]} <b>${fmt(lt.trail[1])}f</b> · ${fmt(lt.trail[1] - b)}s` : "no trail on the record") + `</div>`;
  }
  // the Jarvis window's two standing lines: the DEMO voice, the live band
  const bv = $("#bvoice"), bl = $("#bline"), ln = LY.bands ? bandLine(i) : null;
  bv.hidden = !(mv || (dm && !dm.wait));
  if (mv) { const w = mv.v.ok ? mv.v.state : null; bv.className = "bline " + (w === "EXIT" ? "dn" : w === "WARN" || !w ? "warn" : "");
    bv.textContent = w ? `YOUR TRADE · ${w} · ${String(mv.v.l3 || "").replace(/^why: /, "")}` : `YOUR TRADE · ${mv.v.why || "could not check: no reason given"}`; }
  else if (!bv.hidden) { const w = dm.v ? dm.v.w : "IN"; bv.className = "bline " + (w === "EXIT" ? "dn" : w === "WARN" ? "warn" : ""); bv.textContent = `DEMO ${w} · ${dm.v ? dm.v.why : "stop " + (dm.stop == null ? "not on the record" : f1(dm.stop) + "f")}`; }
  bl.hidden = !ln; if (ln) { bl.className = "bline " + ln.c; bl.textContent = ln.t; }
  document.querySelectorAll("#strip .v, #strip .s").forEach(el => { el.title = el.textContent; });   // one-line cards: the whole text on hover
  HOLDM = !!(dm && !dm.wait && !dm.out); j3Hold(i);          // v3: in a trade the seven status cards give way to the HOLD strip
  const ms = LY.str ? meterSay(i) : null, bm = $("#bmeter");   // STRENGTH (shadow): one line at the top of the Jarvis window, no raw lots in it
  bm.hidden = !ms; if (ms) { bm.className = "bline " + ms.c; bm.textContent = ms.t; bm.title = ms.fam; }
  fitDet();
}
function fitDet() {                 // the open detail never squeezes the log out: it takes what is left above the log's floor, and scrolls
  const d = $("#det"); if (!d.open) return;
  const p = d.parentNode, used = [...p.children].filter(c => c !== d && c.id !== "feed").reduce((a, c) => a + c.offsetHeight, 0);
  d.querySelector(".detb").style.maxHeight = Math.max(72, p.clientHeight - used - 34 - 96) + "px";
}
$("#det").addEventListener("toggle", fitDet); addEventListener("resize", fitDet);
function j3Tick() {                 // the collapsed pill's one line
  if (!WIN.col || !D) return;
  const i = cur(), dm = demoAt(i), ln = LY.bands ? bandLine(i) : null, e = curMsg;
  const ms = LY.str ? meterSay(i) : null;
  const mv = mtVoice();
  const s = mv && mv.v.ok ? `YOUR TRADE · ${mv.v.state} · ${String(mv.v.l3 || "").replace(/^why: /, "")}`
    : dm && !dm.wait && dm.v ? `DEMO ${dm.v.w} · ${dm.v.why}` + (ms ? ` · ${ms.t}` : "") : ms ? ms.t : ln ? ln.t : e ? shortOf(e) : "";
  if (s !== pillTxt) { pillTxt = s; $("#bpill").textContent = s; }
}

/* ---- the Jarvis window: drag by the header, pin (stay) / follow (the candle), resize, collapse; remembered */
function winApply(save) {
  bubble.classList.toggle("pillm", !!WIN.col); bubble.classList.toggle("sized", !!WIN.h && !WIN.col);
  bubble.style.width = WIN.w && !WIN.col ? WIN.w + "px" : ""; bubble.style.height = WIN.h && !WIN.col ? WIN.h + "px" : "";
  $("#bPin").textContent = WIN.pin ? "pinned" : "follow"; $("#bPin").classList.toggle("on", !!WIN.pin);
  $("#bPin").title = WIN.pin ? "pinned: stays where you put it · click to follow the candle" : "following the candle · click to pin it here";
  $("#bCol").textContent = WIN.col ? "+" : "–"; $("#bCol").title = WIN.col ? "expand" : "collapse to one line";
  if (save !== false) LS.set("win", WIN);
  placeBubble(true);
}
function dragOn(el, start, move, done) {
  el.addEventListener("pointerdown", m => {
    if (m.button || m.target.closest("button")) return;
    const s = start(m); if (s === false) return; m.preventDefault();
    try { el.setPointerCapture(m.pointerId); } catch (e) { /* no capture: the listeners below still follow inside the element */ }
    const EV = ["pointerup", "pointercancel", "lostpointercapture"];
    const mv = q => q.buttons === 0 ? up() : move(q, s);      // the button was let go outside the window: the drag is over
    const up = () => { el.removeEventListener("pointermove", mv); EV.forEach(k => el.removeEventListener(k, up)); done(); };
    el.addEventListener("pointermove", mv); EV.forEach(k => el.addEventListener(k, up));
  });
}
dragOn($("#bhead"), m => { const sr = stage.getBoundingClientRect(); bubble.classList.add("drag"); return {sr, ox: m.clientX - sr.left - bpos.x, oy: m.clientY - sr.top - bpos.y}; },
  (q, s) => { WIN.pin = true; WIN.x = q.clientX - s.sr.left - s.ox; WIN.y = q.clientY - s.sr.top - s.oy; placeBubble(true); },
  () => { bubble.classList.remove("drag"); winApply(); });
dragOn($("#bGrip"), m => { bubble.classList.add("drag"); return {x: m.clientX, y: m.clientY, w: bubble.offsetWidth, h: bubble.offsetHeight}; },
  (q, s) => { WIN.w = Math.round(Math.max(240, Math.min(640, s.w + q.clientX - s.x))); WIN.h = Math.round(Math.max(96, Math.min(Ht - 16, s.h + q.clientY - s.y)));
    bubble.style.width = WIN.w + "px"; bubble.style.height = WIN.h + "px"; },
  () => { bubble.classList.remove("drag"); winApply(); });
$("#bGrip").ondblclick = () => { WIN.w = WIN.h = null; winApply(); };
$("#bPin").onclick = () => { WIN.pin = !WIN.pin; if (WIN.pin) { WIN.x = bpos.x; WIN.y = bpos.y; } winApply(); };
$("#bCol").onclick = () => { WIN.col = !WIN.col; pillTxt = null; winApply(); j3Tick(); };

/* ---- the switches */
document.querySelectorAll("#layers .sw").forEach(el => { const k = el.dataset.ly, set = () => { el.classList.toggle("on", !!LY[k]); el.setAttribute("aria-pressed", String(!!LY[k])); };
  set(); if (NOLIVE[k]) { el.disabled = true; el.style.opacity = 0.45; el.title = NOLIVE[k]; return; }   // the live page says why a layer is not there
  el.onclick = () => { LY[k] = !LY[k]; set(); LS.set("layers", LY); if (k === "sync" || k === "opt" || k === "str") fit(); if (D) j3Panel(cur()); }; });
function setFilt(f) { FILT = ["all", "moves", "walls", "opt", "trade"].includes(f) ? f : "all"; $("#feed").dataset.f = FILT;
  document.querySelectorAll("#fchips .sw").forEach(el => el.classList.toggle("on", el.dataset.f === FILT)); LS.set("filt", FILT); }
$("#fchips").onclick = m => { const el = m.target.closest("button"); if (el) setFilt(el.dataset.f); };
setFilt(FILT);
$("#demoT").onclick = () => {
  if (!J3.trade) return;
  DEMO = !DEMO; $("#demoT").textContent = `DEMO TRADE · ${DEMO ? "on" : "off"}`; $("#demoT").classList.toggle("on", DEMO); $("#demoT").setAttribute("aria-pressed", String(DEMO));
  ev = ev.filter(e => !e.j3); j3Events(); marks = ev.filter(MARKP); if (D) seek(t);
};
if (!J3.trade) { $("#demoT").disabled = true; $("#demoT").title = "no zone trigger on this day's record: nothing to show"; }
winApply(false);
/* ---- the live page only: her MARKED trade's one voice, exactly what the server already serves her floating window
   (GET /api/hold/trades, then GET /api/fold?id=). Read every 20 s with the frame; nothing is sent, nothing is placed. */
function pollTrade() {
  const o = new URL(API, location.href).origin, idx = pageIdx(), j = u => fetch(o + u).then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)));
  j("/api/hold/trades").then(r => {
    const tr = ((r && r.trades) || []).filter(x => !x.exit_t && String(x.idx || "").toUpperCase() === idx).sort((a, b) => String(b.t0 || "").localeCompare(String(a.t0 || "")))[0];
    if (!tr) { MT = null; return null; }
    return j("/api/fold?id=" + encodeURIComponent(tr.id)).then(f => { MT = {idx, id: tr.id, at: new Date().toTimeString().slice(0, 8),
      v: f && f.ok ? f.voice || {ok: false, why: "could not check: the server sent no voice for this trade"} : {ok: false, why: (f && f.why) || "could not check: no reply for this trade"}}; });
  }).catch(e => { if (MT) MT.v = {ok: false, why: `could not check: ${e.message}`}; }).then(() => { if (D) j3Panel(cur()); });
}
if (window.J3DATA.frame) init(window.J3DATA.frame);         // the mockup: its one inlined day. The live page: its own loader (loadFrame, the 20-s poll) runs init / swapFrame
else if (LIVE) { pollTrade(); setInterval(pollTrade, 20000); }
// the strip's cards wrap instead of clipping, so the chart's box can change height: the canvas follows its box
if (typeof ResizeObserver !== "undefined") { let was = ""; new ResizeObserver(() => { const r = stage.getBoundingClientRect(), k = Math.round(r.width) + "x" + Math.round(r.height); if (k !== was) { was = k; fit(); } }).observe(stage); }
"""


def patch(html, old, new, count=1):
    n = html.count(old)
    if n != count:
        raise SystemExit(f"PATCH FAILED: anchor found {n}x (want {count}): {old[:90]!r}")
    return html.replace(old, new)


def build_html(src, data, label, live=False):
    h = src
    mpatch = (lambda h, *a, **k: h) if live else patch              # the mockup-only patches (one inlined day, nothing fetched): skipped on the live page
    # ---- head: no network (the fonts fall back to the system's), the mockup's styles after the page's own
    h = mpatch(h, '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
                 '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">\n', "")
    h = patch(h, "<title>JARVIS · chart decode</title>", "<title>JARVIS 3 · live</title>" if live else f"<title>JARVIS 3 · mockup · {label}</title>")
    h = patch(h, "</style>\n</head>", CSS + "</style>\n</head>")
    # ---- body
    h = mpatch(h, '<span class="badge" id="mode">DEMO</span> <small>NIFTY Nov fut · 28 Oct · replay from recorded + backfilled numbers</small>',
              '<span class="badge" id="mode">REPLAY</span> <small>mockup · loading</small>')
    h = mpatch(h, '<div class="pickw"><div class="grp pick" title="replay a recorded day (after 15:40) · today = live"><button id="pDay">—</button>'
                 '<select id="pIdx"><option>NIFTY</option><option>SENSEX</option><option>BANKNIFTY</option></select></div><div id="cal" hidden></div></div>',
              f'<div class="pickw"><span class="c1 warn" title="this file holds one recorded day, inlined; nothing is fetched">mockup · {label} only</span>'
              '<span hidden><button id="pDay">—</button><select id="pIdx"><option>NIFTY</option></select></span><div id="cal" hidden></div></div>')
    h = patch(h, '<button id="walk" title="walk me through the day: the moments that mattered, spoken (W)">🎓 walk</button>\n',
              '<button id="walk" title="walk me through the day: the moments that mattered, spoken (W)">🎓 walk</button>\n'
              '    <button id="demoT" aria-pressed="false" title="DEMO: shows the day\'s real first zone trigger as if you were in it. Display only: nothing is placed, sent or simulated at a broker.">DEMO TRADE · off</button>\n')
    h = patch(h, '    <div id="stage"><canvas id="cv"></canvas><div id="fx"></div>', LAYERS + '    <div id="stage"><canvas id="cv"></canvas><div id="fx"></div>')
    h = patch(h, BUBBLE_OLD, BUBBLE_NEW)
    h = patch(h, PANEL_OLD, PANEL_NEW)
    if live:                                                        # no DEMO trade on the live page: her MARKED trade's voice takes its place
        h = patch(h, '<button id="demoT" aria-pressed="false"', '<button id="demoT" style="display:none" aria-pressed="false"')
    h = patch(h, "no-trade stretches. Jarvis never places an order.</p>",
              "no-trade stretches. Jarvis never places an order.</p>\n"
              + ("  <p>New on this page: the five-block panel · a movable window · the NOW view · swings · the sync lane · your marked trade's voice. "
                 "Move bands and option flow are not live yet.</p>" if live else
                 f"  <p>Mockup · {label} only. New: move bands · option flow · sync lane · five-block panel · a movable window · DEMO TRADE.</p>"))
    # ---- script: one inlined day, nothing fetched
    h = mpatch(h, 'const loadDays = () => fetch("http://localhost:5173/api/jarvis_days").then(r => r.json())\n'
                 '  .then(d => { if (d && d.ok) { DAYS = d.days; if (!$("#cal").hidden) cal(); } }).catch(() => {});\nloadDays();\n',
              "const loadDays = () => {};                             // mockup: one inlined day, nothing is fetched\n")
    h = mpatch(h, 'const fetchFrame = u => fetch(u + (u.includes("?") ? "&" : "?") + "v=" + Date.now())\n'
                 "  .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)));\n",
              'const fetchFrame = u => Promise.reject(new Error("mockup: nothing is fetched"));\n')
    h = mpatch(h, "\nloadFrame(0);\n", "\n// mockup: the frame is inlined; init() runs at the end of this script\n")
    h = mpatch(h, 'const API = QS.get("api") || (DAY ? `http://localhost:5173/api/jarvis?idx=${QS.get("idx") || "NIFTY"}&day=${DAY}&fill=${QS.get("fill") ?? "1"}` : null);',
              "const API = null;                                      // mockup: one inlined day")
    h = mpatch(h, 'const MODE = LIVE ? "LIVE" : API || QS.get("d") ? "REPLAY" : "DEMO";', 'const MODE = "REPLAY";')
    # ---- the top bar and the strip say it once, in few words (the badge carries the day; the whole note stays on hover)
    h = mpatch(h, '`${D.idx} fut · ${D.day} · ${LIVE ? "live from the brain" : D.fill ? "replay · holes filled from the tape" : "replay"} · to ${D.mins[N - 1]}`',
              '`${D.idx} fut` + (D.fill ? " · holes filled from the tape" : "")')
    h = patch(h, '$("#sHealth2").textContent = h.notes[0] || `Dext ${h.dext.minutes} min · chain whole`;',
              '$("#sHealth2").textContent = (h.notes[0] || "").split(": ")[0] || `Dext ${h.dext.minutes} min · chain whole`;')
    h = patch(h, '`3-min delta ${sgn(sp.d3)} · FAST ≥ ×2 · SLOW ≤ ×0.5`', '`3-min Δ ${sgn(sp.d3)} · FAST ≥ ×2 · SLOW ≤ ×0.5`')
    h = patch(h, "T/B signs · dots on top = notes (hover) · bars at right = OI by strike (ghost = day peak)</span>",
              "T/B signs · dots on top = notes (hover) · bars at right = OI by strike (ghost = day peak) · box = move band, number = Dext delta lots, dashed = forming · "
              "solid WHO = FIRM · hover a label</span>")
    # ---- colours: CE / PE and her own lines move onto the four meaning colours
    h = patch(h, 'const COL = {up:"#0f9d76", dn:"#e5484d", ce:"#c2410c", pe:"#2563eb", ai:"#d97757", grid:"#eeebe4", mut:"#6b7280", ink:"#15181e", q:"#9aa0a6", band:"#7c5cbf", you:"#7c3aed", line:"#e3e0d7"};',
              'const COL = {up:"#0f9d76", dn:"#e5484d", ce:"#e5484d", pe:"#0f9d76", ai:"#d97757", grid:"#eeebe4", mut:"#6b7280", ink:"#15181e", q:"#9aa0a6", band:"#6b7280", you:"#15181e", line:"#e3e0d7", warn:"#b7791f"};')
    h = patch(h, 'side === "CE" ? "#fdf0e8" : "#eaf1fe"', 'side === "CE" ? "#fdecec" : "#e6f6f0"')
    h = patch(h, '"rgba(124,58,237,.07)"', '"rgba(217,119,87,.08)"')
    h = patch(h, '"rgba(124,58,237,.08)"', '"rgba(21,24,30,.05)"')
    h = patch(h, '"#f3ecfd"', '"#eeece6"', 2)
    h = patch(h, '  el.style.background = c === "bad" ? "#fdeaea" : c === "ok" ? "#e8f7f1" : c === "you" ? "#efe6fd" : "#f3efe8";\n'
                 '  el.style.color = c === "bad" ? COL.dn : c === "ok" ? COL.up : c === "q" ? COL.mut : c === "you" ? COL.you : COL.ink;',
              '  el.style.background = c === "bad" ? "#fdf1f1" : c === "ok" ? "#effaf5" : c === "warn" ? "#fdf3dc" : "#f6f4ef";\n'
              '  el.style.color = c === "bad" ? COL.dn : c === "ok" ? COL.up : c === "warn" ? COL.warn : c === "q" ? COL.mut : COL.ink;')
    # ---- the hooks
    h = patch(h, "  buildEvents();\n  marks = ev.filter(e => e.push || e.toot || e.zone || e.tag === \"BLIND\" || e.floor || e.chap === \"FUEL\" || e.chap === \"FUEL SPENT\" || (e.signs && !e.signs.driving) || e.chap === \"NEW FIGHT\" || e.chap === \"MANAGE\");",
              "  buildEvents(); j3Events();\n  marks = ev.filter(MARKP);")
    h = patch(h, "const padL = 8, padR = 198, AXW = 60;", "const padL = 8, padR = 280, AXW = 60;")
    h = patch(h, "  const inner = Ht - pTop - 24; pBot = pTop + Math.round(inner * 0.78); dTop = pBot + 10; dBot = Ht - 24;",
              "  const lane = laneH(), inner = Ht - pTop - 24 - lane; pBot = pTop + Math.round(inner * 0.78); sTop = pBot + 13; dTop = pBot + 10 + lane; dBot = Ht - 24;")
    h = patch(h, "  draw(now); tlDraw(); placeBubble(); requestAnimationFrame(loop);", "  draw(now); tlDraw(); placeBubble(); j3Tick(); requestAnimationFrame(loop);")
    h = patch(h, "function placeBubble(force) {\n  if (!D) return;\n",
              "function placeBubble(force) {\n  if (!D) return;\n"
              "  if (WIN.pin && WIN.x != null) {                     // pinned: stays where she put it (kept inside the chart)\n"
              "    const x = Math.max(4, Math.min(Wd - bubble.offsetWidth - 4, WIN.x)), y = Math.max(4, Math.min(Ht - bubble.offsetHeight - 4, WIN.y));\n"
              "    if (force || x !== bpos.x || y !== bpos.y) { bpos = {x, y}; bubble.style.transform = `translate(${x}px,${y}px)`; }\n"
              "    return;\n  }\n")
    h = patch(h, "  renderTrade(i);\n}\nfunction renderTrade(i) {", "  renderTrade(i); j3Panel(i);\n}\nfunction renderTrade(i) {")
    h = patch(h, "  ctx.clearRect(0, 0, Wd, Ht); tagYs.length = 0;", "  ctx.clearRect(0, 0, Wd, Ht); tagYs.length = 0; LBL.length = 0; HIT.length = 0;")
    h = patch(h, "  zoneFills(end); bands(end); walls(now, end);", "  if (LY.zones) { zoneFills(end); bands(end); } if (LY.walls) walls(now, end); j3Under(now, end);")
    h = patch(h, "  deltaPane(end); inventory(end); userDraw(end);\n  zones(now); pushes(now); aipins(); link(now);",
              "  deltaPane(end); inventory(end); userDraw(end); j3Lane(end);\n  if (LY.zones) zones(now); if (LY.marks) pushes(now); j3Over(now, end); aipins(); link(now);")
    h = patch(h, "  const x0 = Wd - padR + AXW + 46, wmax = Wd - x0 - 8;", "  const x0 = Wd - padR + AXW + 46, wmax = Wd - x0 - 8 - LADR;")
    h = patch(h, '  ctx.font = "600 9.5px " + MONO; ctx.fillStyle = COL.mut; ctx.fillText("OI by strike · L", Wd - padR + AXW + 4, pTop - 8);',
              '  ctx.font = "600 9.5px " + MONO; ctx.fillStyle = COL.mut; ctx.fillText("OI by strike · L", Wd - padR + AXW + 4, pTop - 8); j3WhoHead(i);')
    h = patch(h, "    ctx.fillStyle = COL.pe; ctx.fillText(pe.toFixed(0), x0 + Math.max(pe, ppk) / MAXOI * wmax + 3, y + 6.5);",
              "    ctx.fillStyle = COL.pe; ctx.fillText(pe.toFixed(0), x0 + Math.max(pe, ppk) / MAXOI * wmax + 3, y + 6.5); j3Who(k, y, i);")
    # the page's own labels join the no-overlap rule (a vertical nudge; none is dropped)
    h = patch(h, 'ctx.fillText("BACKFILLED · Upstox chain + Dext flow", X(0) + 4, pTop + 12); }',
              'ctx.fillText("BACKFILLED · Upstox chain + Dext flow", X(0) + 4, pTop + 12); LBL.push({x: X(0) + 4, y: pTop + 2, w: 226, h: 12}); }')
    h = patch(h, 'ctx.fillText("BLIND · laptop asleep", X(h0) + 4, pTop + 12); if (t > h1) ctx.fillText("flow refilled · chain blind", X(h0) + 4, pTop + 26); }',
              'const by = nudge(X(h0) + 4, pTop + 2, 162, 26); ctx.fillText("BLIND · laptop asleep", X(h0) + 4, by + 10); if (t > h1) ctx.fillText("flow refilled · chain blind", X(h0) + 4, by + 24); }')
    h = patch(h, "ctx.fillText(`NEW FLOOR ${fmt(e.floor.k)}s`, X(f0) + 4, Y(lvl(e.floor.k, f0)) + 13); }",
              "ctx.fillText(`NEW FLOOR ${fmt(e.floor.k)}s`, X(f0) + 4, nudge(X(f0) + 4, Y(lvl(e.floor.k, f0)) + 4, 112, 12) + 9); }")
    h = patch(h, "const w = ctx.measureText(lab).width + 12, yy = sell ? y - 30 : y + 12;\n"
                 '    ctx.fillStyle = "#fff"; rr(X(i) - w / 2, yy, w, 18, 9); ctx.fill(); ctx.strokeStyle = col; ctx.stroke(); ctx.fillStyle = col; ctx.fillText(lab, X(i) - w / 2 + 6, yy + 13); ctx.restore();',
              "const w = ctx.measureText(lab).width + 12, at = place([X(i) - w / 2, X(i) + 8, X(i) - w - 8], sell ? y - 30 : y + 12, w, 18), yy = at.y;\n"
              '    ctx.fillStyle = "#fff"; rr(at.x, yy, w, 18, 9); ctx.fill(); ctx.strokeStyle = col; ctx.stroke(); ctx.fillStyle = col; ctx.fillText(lab, at.x + 6, yy + 13); ctx.restore();')
    h = patch(h, "      ctx.save(); ctx.translate(X(i), wy + (p.dir > 0 ? -13 : 13)); ctx.scale(0.6 + 0.4 * g, 0.6 + 0.4 * g); ctx.globalAlpha = g;\n"
                 '      ctx.font = "700 10px " + MONO; const w = ctx.measureText(lab).width + 10;',
              '      ctx.save(); ctx.font = "700 10px " + MONO; const w = ctx.measureText(lab).width + 10, at = place([X(i) - w / 2, X(i) + 6, X(i) - w - 6], wy + (p.dir > 0 ? -13 : 13) - 8, w, 16);\n'
              "      ctx.translate(at.x + w / 2, at.y + 8); ctx.scale(0.6 + 0.4 * g, 0.6 + 0.4 * g); ctx.globalAlpha = g;")
    # the event log: one line per event; a band's line jumps to the band's start
    h = patch(h, "function rowHTML(e, n) {\n  const chips = (e.chips || [])", "function rowHTML0(e, n) {\n  const chips = (e.chips || [])")
    h = patch(h, "seek(+el.dataset.i + 0.01); } };", "seek(+(el.dataset.j != null ? el.dataset.j : el.dataset.i) + 0.01); } };")
    # the timeline: band segments, a click on one jumps to its start; tooltips sit on the stage, whole
    h = patch(h, "  const px = TX(t); tctx.fillStyle = COL.ai; tctx.fillRect(px - 1, 3, 2, TH - 6);", "  j3Rail();\n  const px = TX(t); tctx.fillStyle = COL.ai; tctx.fillRect(px - 1, 3, 2, TH - 6);")
    h = patch(h, 'tl.addEventListener("mousedown", m => { scrubbing = true; seek(Math.max(0, TXI(tlPos(m).x))); });',
              'tl.addEventListener("mousedown", m => { const q = tlPos(m), hb = j3RailHit(q); if (hb) { setPlay(false); seek(hb.si + 0.01); return; } scrubbing = true; seek(Math.max(0, TXI(q.x))); });')
    h = patch(h, "  if (near.length) { const e = near[0];",
              "  const hb = j3RailHit(tlHover);\n"
              "  if (hb) { tip.innerHTML = j3RailTip(hb); tip.style.left = Math.max(4, Math.min(stage.getBoundingClientRect().width - 350, tlHover.x)) + \"px\"; tip.style.opacity = 1; tip.style.top = (tl.offsetTop - tip.offsetHeight - 6) + \"px\"; }\n"
              "  else if (near.length) { const e = near[0];")
    h = patch(h, '.slice(0, 220)}`;', '}`;')
    h = patch(h, "(tr.top - sr.top - 70)", "(tl.offsetTop - 78)")
    h = patch(h, "(tr.top - sr.top - 34)", "(tl.offsetTop - 34)")
    h = patch(h, 'tip.style.top = (my + 14) + "px"; tip.style.opacity = 1; }\n  else tip.style.opacity = 0; });',
              'tip.style.top = (stage.offsetTop + my + 14) + "px"; tip.style.opacity = 1; }\n  else if (!j3Hover(mx, my, tip)) tip.style.opacity = 0; });')
    # the canvas on the same type scale: 9 and 10 px only
    h = re.sub(r'(10\.5|9\.5|8\.5)px " \+ MONO', lambda m: {"10.5": "10", "9.5": "9", "8.5": "9"}[m.group(1)] + 'px " + MONO', h)
    # ---- v2 (12 Nov, her mark-up of the first mockup) --------------------------------------------------------------------
    # the price scale fits the day so far (yFit); nothing off the scale paints outside the pane; a far wall's tag is pinned to the edge
    h = patch(h, '  const end = cur();\n  ctx.font = "10px " + MONO;\n  // price grid + axis',
              '  const end = cur(); yFit(end); HIST = histFrom(end);\n  ctx.font = "10px " + MONO;\n  // price grid + axis')
    h = patch(h, "  if (LY.zones) { zoneFills(end); bands(end); } if (LY.walls) walls(now, end); j3Under(now, end);",
              "  ctx.save(); ctx.beginPath(); ctx.rect(0, pTop - 1, Wd, pBot - pTop + 2); ctx.clip();\n"
              "  if (LY.zones) { zoneFills(end); bands(end); } if (LY.walls) walls(now, end); j3Under(now, end);")
    h = patch(h, "  deltaPane(end); inventory(end); userDraw(end); j3Lane(end);\n  if (LY.zones) zones(now); if (LY.marks) pushes(now); j3Over(now, end); aipins(); link(now);",
              "  userDraw(end); j3PA(end); if (LY.zones && !HOLDM) zones(now); if (LY.marks && !HOLDM) pushes(now); j3Over(now, end);\n  ctx.restore();\n"
              "  deltaPane(end); inventory(end); j3Lane(end); aipins(); link(now);")
    h = patch(h, "function axisTag(y, text, col, fill, bold) {\n",
              "function axisTag(y, text, col, fill, bold) {\n"
              '  const off = y < pTop + 9 ? -1 : y > pBot - 9 ? 1 : 0; if (off) { text = (off < 0 ? "▲ " : "▼ ") + text; y = off < 0 ? pTop + 9 : pBot - 9; }\n')
    h = patch(h, "  while (tagYs.some(q => Math.abs(q - y) < 17)) y += 17;", "  while (tagYs.some(q => Math.abs(q - y) < 17)) y += off > 0 ? -17 : 17;")
    # the zone mark's verdict (zone card + the §1d gate) is in jarvis2.html itself since A279; here: the NOW view, the quieter history, the hover
    h = patch(h, '    const i = ix(z.t); if (i < 0 || i > t) continue;\n    if (z.kind === "arm")',
              '    const i = ix(z.t); if (i < 0 || i > t || OLD(i)) continue;\n    if (z.kind === "arm")')
    h = patch(h, "    const e = ev[n];\n    if (e.push) {", "    const e = ev[n];\n    if (OLD(e.i)) continue;\n    if (e.push) {")
    h = patch(h, "      const p = e.ans, i = clampI(ix(p.held_at || p.am)), wy = Y(lvl(p.k, i)), g = ease(grow(e, now, 450));",
              "      const p = e.ans, i = clampI(ix(p.held_at || p.am)), wy = Y(lvl(p.k, i)), g = ease(grow(e, now, 450));\n"
              "      if (!LY.hist && /^HELD/.test(ansWord(p))) continue;   // a wall that simply held is not a chart event: the log has it, History shows it")
    # HOLD mode: a candle against the trade is grey (a pullback) or amber (a PUSH against), never just red
    h = patch(h, "      const k = live(i), col = k.c >= k.o ? COL.up : COL.dn;",
              "      const k = live(i), hc = holdCol(i, k, end), col = hc ? hc.col : k.c >= k.o ? COL.up : COL.dn;")
    h = patch(h, '    ctx.save(); ctx.globalAlpha = g; ctx.font = "700 10px " + MONO; const w = ctx.measureText(lab).width + 12, at = place(',
              '    ctx.save(); ctx.globalAlpha = g * (i < HIST ? 0.5 : 1); ctx.font = "700 10px " + MONO; const w = ctx.measureText(lab).width + 12, at = place(')
    h = patch(h, "ctx.fillText(lab, at.x + 6, yy + 13); ctx.restore();",
              "ctx.fillText(lab, at.x + 6, yy + 13); ctx.restore(); HIT.push({x: at.x, y: yy, w, h: 18, html: zoneTip(z, zs, v)});")
    h = patch(h, "      ctx.translate(at.x + w / 2, at.y + 8); ctx.scale(0.6 + 0.4 * g, 0.6 + 0.4 * g); ctx.globalAlpha = g;",
              "      ctx.translate(at.x + w / 2, at.y + 8); ctx.scale(0.6 + 0.4 * g, 0.6 + 0.4 * g); ctx.globalAlpha = g * (i < HIST ? 0.5 : 1);")
    # the day map and the chapter rail say what they are
    h = patch(h, 'else if (e.zone) { const s = e.zone.side === "SELL"; tctx.fillStyle = s ? COL.dn : COL.up;',
              'else if (e.zone) { const s = e.zone.side === "SELL"; tctx.fillStyle = zoneSay(e.zone, cur()).skip ? COL.q : s ? COL.dn : COL.up;')
    h = patch(h, "  j3Rail();\n  const px = TX(t);",
              '  tctx.font = "600 9px " + MONO; tctx.fillStyle = COL.mut;\n'
              '  ["DAY MAP · click to jump · top bar = move band", "▼ ▲ your zone (grey = skipped) · ◆ push", "● options fuel · T B top / bottom sign"].forEach((s, n) => tctx.fillText(s, TW - padR + 8, 13 + n * 12));\n'
              "  j3Rail();\n  const px = TX(t);")
    h = patch(h, '  const r = $("#rail");\n  CHAPS.forEach(',
              '  const r = $("#rail");\n'
              '  r.insertAdjacentHTML("beforeend", \'<span class="lk" title="the fight at the wall, chapter by chapter: outlined = happened today · filled = now · click a chapter to jump to it">WALL STORY</span>\');\n'
              "  CHAPS.forEach(")
    h, n = re.subn(r"""r\.insertAdjacentHTML\("beforeend", '<span class="legend">.*?</span>'\);""",
                   lambda m: """r.insertAdjacentHTML("beforeend", '<span class="legend">hover any mark for its numbers · click the day map or a log line to jump</span>');""",
                   h, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("PATCH FAILED: the rail legend")
    # an OI cut while price goes the OTHER way is not writers being pushed out (11 Nov 13:31: CE -12.0L into a 40-pt fall was read "WRITERS ▲")
    h = patch(h, "    const up = w.dir > 0, c = L(w.ce), p = L(w.pe), ch = [{t: `CE ${c}`}, {t: `PE ${p}`}];\n",
              "    const up = w.dir > 0, c = L(w.ce), p = L(w.pe), ch = [{t: `CE ${c}`}, {t: `PE ${p}`}];\n"
              "    const pm = i >= 3 ? D.fut[i] - D.fut[i - 3] : 0;\n"
              '    if ((w.ev === "UP" || w.ev === "DOWN" || w.ev === "BACK") && pm * w.dir < 0) {\n'
              '      E(i + 0.35, {tag: `±7 ${up ? "CALLS" : "PUTS"} CUT · price ${pm < 0 ? "▼" : "▲"}`, tagc: "warn", major: true,\n'
              '        text: `**Not a push ${up ? "▲" : "▼"}**: ±7 OI CE **${c}** · PE **${p}** in 3 min while price ${pm < 0 ? "fell" : "rose"} **${Math.abs(pm).toFixed(0)} pts**. '
              '${up ? "Calls" : "Puts"} came off INTO the move: longs out or writers booking, not writers pushed out. The option-flow close names who.`,\n'
              '        chips: ch.concat([{t: `price ${pm < 0 ? "−" : "+"}${Math.abs(pm).toFixed(0)} / 3 min`, c: "warn"}, {t: "±7 strikes · 3 min"}])});\n'
              "      return;\n    }\n")
    # ---- the data (one <script> before the page's) and the layers (appended inside the page's own script)
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    h = patch(h, '<script>\n"use strict";', f"<script>window.J3DATA = {blob};</script>\n<script>\n\"use strict\";")
    h = patch(h, "</script>\n</body>", JS + "</script>\n</body>")
    return h


def main(argv):
    day = next((a for a in argv[1:] if len(a) == 10 and a[4] == "-"), "2026-11-11")
    if "--live" in argv:                                            # the LIVE page beside jarvis2.html: the page's own loader, no inlined day.
        # No layer is computed from the tapes: the server does not send them yet, and the page says so (never an empty that looks like "nothing happened")
        x = {"live": True, "idx": IDX, "bands": [], "pushes": [], "bars5": [], "forming": {}, "need": None, "sync": None, "trade": None, "meter": None,
             "opt": {"ok": False, "why": NOT_LIVE, "closes": [], "changes": [], "first": None, "up": {}}}
        with open(SRC, encoding="utf-8") as f:
            src = f.read()
        with open(OUT_LIVE, "w", encoding="utf-8", newline="\n") as f:
            f.write(build_html(src, {"x": x}, "live", live=True))
        print(f"JARVIS 3 live page written: {OUT_LIVE}\n  open http://localhost:8787/jarvis3.html?api=http://localhost:5173/api/jarvis?idx=NIFTY")
        return
    os.chdir(ROOT)                                                  # dext_log.DIR and the recorders' paths are relative
    sys.path.insert(0, ROOT)
    frame, how = get_frame(day, "--fresh" in argv)
    if not frame.get("ok") or not frame.get("mins"):
        raise SystemExit(f"no frame for {IDX} {day}: {frame.get('why')}")
    M = [m_of(x) for x in frame["mins"]]
    if M != list(range(M[0], M[0] + len(M))):
        raise SystemExit("the frame's minutes are not contiguous: the layers index by minute")
    M0, last = M[0], M[-1]
    mv, P, O = move_layer(day, M0, last)
    opt = opt_layer(day, frame, M0, last)
    sy = sync_layer(frame)
    x = dict(mv, day=day, idx=IDX, frame_src=how, opt=opt, sync=sy, trade=trade_layer(frame, mv, P, O, opt, M0, last),
             meter=meter2_layer(frame, mv, opt))
    ms = meter_stats(meter_layer(frame, mv, opt, sy)["rows"])        # v1, kept for the record: it failed (definition v1 §8)
    print(f"STRENGTH v1 · {day} · {ms['closes']} closes · the shown numbers moved {ms['number_moves']}x · the word changed {ms['word_changes']}x · "
          f"all five read at {ms['full_reads']} closes · unread: {ms['unread']} · F2 table: {mv['oi_days']} days, bars per part {mv['oi_n']}")
    rows2 = x["meter"]["rows"]
    m2 = meter2_stats(rows2, len(mv["pushes"]) + len(frame.get("pivots") or []))
    print(f"STRENGTH v2 · {day} · {m2['closes']} closes · the word changed {m2['word_changes']}x against {m2['events']} events "
          f"({len(mv['pushes'])} pushes + {len(frame.get('pivots') or [])} swings): {'PASS' if m2['pass1'] else 'FAIL'} · the shown numbers moved "
          f"{m2['number_moves']}x · all five read at {m2['full_reads']} closes · unread: {m2['unread']} · window tables: {mv['win_n']}")
    t = x["trade"]
    if t:                                                           # her side through the DEMO trade (the v1 failure case is 11 Nov 11:50)
        print(f"VOICES · {day} · {voices_md(day, frame, t)} rows written to docs/jarvis-panel/voices_{day}.md · "
              f"new line: {sum(1 for b in t['book'] if b['w'] == 'BOOK')} BOOK, {sum(1 for b in t['book'] if b['w'] == 'TRAIL')} TRAIL · old line: {len(t['old'])}")
        wd = meter_words(rows2, t["d"])
        inn = [(r, w) for r, w in zip(rows2, wd) if r["i"] > t["ei"] and (not t["exit"] or r["i"] <= t["exit"]["i"])]
        runs, was = [], None
        for r, w in inn:
            if w != was:
                runs.append(f"{r['t']} {w} {r['up' if t['d'] > 0 else 'dn']}/{r['dn' if t['d'] > 0 else 'up']}")
            was = w
        print(f"  v2 through the {t['t']} {t['side']} (her side / other side at each change of the word): " + " · ".join(runs))
        print(f"  TURNING closes inside the trade: {sum(1 for _, w in inn if w == 'TURNING')} of {len(inn)}")
    if "--stats-only" in argv:                                      # the shadow count on another day: nothing is written
        return
    y, mo, dd = day.split("-")
    label = f"{int(dd)} {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(mo) - 1]}"
    with open(SRC, encoding="utf-8") as f:
        src = f.read()
    html = build_html(src, {"frame": frame, "x": x}, label)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    mins = frame["mins"]
    print(f"JARVIS 3 mockup · {IDX} {day} · frame: {how} ({mins[0]}–{mins[-1]}, {len(mins)} min) · Dext {mv['tag']} · "
          f"push table from {mv['ref_days']} earlier Dext days · lot {mv['lot']}")
    print("\nPUSH (HOLD v2, unchanged) [M]")
    for p in mv["pushes"]:
        print(f"  {p['t']}  {arr(p['d'])}  origin {p['origin']:,.1f}f  size {p['size']:.2f}  R {p['R']:.2f}  U {p['U']:.1f}  line {p['line']:,.1f}f")
    print("\nMOVE BANDS [M] (a band = the brief's run; a leg = one push of it, the same reads from that push bar's open)"
          "\n  start  end    side  name            delta lots   OI lots   line        ended")
    f = lambda v: "      ?" if v is None else f"{v:>+7,}"                                                       # noqa: E731
    for b in mv["bands"]:
        e = len(mins) - 1 if b["ei"] is None else b["ei"]
        print(f"  {mins[b['si']]}  {mins[b['ei']] if b['ei'] is not None else 'open '}  {arr(b['d'])}     {(b['name'] or 'no name'):<15} "
              f"{f(b['delta'])}    {f(b['oich'])}   {b['steps'][-1][1]:>9,.1f}f  {b['why']}"
              + (f" · line moved {len(b['steps']) - 1}x" if len(b["steps"]) > 1 else ""))
        for j, g in enumerate(b["legs"] if len(b["legs"]) > 1 else []):
            k = (b["legs"][j + 1]["si"] - 1 if j + 1 < len(b["legs"]) else e) - g["si"]
            print(f"    leg {mins[g['si']]}  {mins[g['si'] + k]}  {arr(b['d'])}   {(g['nm'][k] or 'no name'):<15} {f(g['dl'][k])}    {f(g['oi'][k])}   "
                  f"{g['line']:>9,.1f}f  (the push's own line)")
    print(f"\nFORMING minutes (hold2.state says PUSH on the open bar): {len(mv['forming'])} · "
          + " ".join(f"{mins[int(k)]}{arr(v['d'])}" for k, v in sorted(mv["forming"].items(), key=lambda kv: int(kv[0]))))
    print(f"\nOPTION FLOW · {len(opt['closes'])} 3-min closes · first ten word changes (optladder's said word) [I]"
          if opt["ok"] else f"\nOPTION FLOW: not read — {opt['why']}")
    for c in opt["changes"][:10]:
        print(f"  {c['t']}  {c['said']:<14} lean {c['lean']:+d}  cap {c['capw']:<6} floor {c['floorw']:<6} "
              f"marked at {str(c['k']) + 's ' + c['ws'] if c['k'] else 'the price (no wall read)'}")
    t = x["trade"]
    if t:
        print(f"\nDEMO TRADE · {t['t']} {t['side']} {t['px']:,.1f}f · entry at the bar's close {mins[t['ei']]} · strike {t['strike']}")
        for i, v, w in t["stops"]:
            print(f"  stop from {mins[min(i, len(mins) - 1)]}  {v:,.1f}f  {w}")
        was = None
        for v in t["voice"]:
            if v["w"] != was:
                print(f"  voice {v['t']}  {v['w']:<7} {v['why']}")
            was = v["w"]
        print(f"  exit: {t['exit'] or 'none: open at the replay end'}")
    s = x["sync"]
    print(f"\nSYNC LANE · {len(s['bars'])} bars · all-3 columns {sum(1 for b in s['bars'] if b['all'])} · "
          f"unreadable cells {sum(1 for b in s['bars'] for c in b['v'] if c is None)} · {s['lead']}")
    print(f"\nwrote {OUT} ({len(html) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
