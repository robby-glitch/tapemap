"""export.py -- READ-ONLY: 28 Oct NIFTY breakout replay data -> index.html (the motion graphic, template replay.html).

Minute by minute from START: spot + NIFTY Nov fut (Upstox REST 1-min, complete even while the laptop slept), the strike
OI grid (/api/oihist minutes, the live record: missing minutes stay missing), every handshake push (handshake.read at the
last minute, with the minute its FLOW line really reached the screen), the message stream at its real write time, the
zone log and the footprint marks. Writes nothing under data/.

    python docs/speed/breakout/export.py            (server on 8765 must be up)
"""
import datetime
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import handshake  # noqa: E402
import upstox_feed  # noqa: E402
import upstox_instruments  # noqa: E402
import upstox_rest  # noqa: E402

DAY, IDX, START = "2026-10-28", "NIFTY", "11:20"
STRIKES = list(range(22500, 22851, 50))
LOT = 65


def hms(epoch):
    return datetime.datetime.fromtimestamp(epoch).strftime("%H:%M:%S")


def rows(path):
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    except FileNotFoundError:
        return


def bars(key, tok):
    return {str(c[0])[11:16]: c for c in upstox_rest.intraday(key, tok) or [] if str(c[0])[:10] == DAY}


tok = upstox_feed.read_token()
S, F = bars(upstox_instruments.index_key(IDX), tok), bars(upstox_instruments.fut_key(IDX), tok)
mins = [m for m in sorted(F) if m >= START and m in S]
grid = json.load(urllib.request.urlopen(f"http://127.0.0.1:8765/api/oihist?idx={IDX}", timeout=30))["minutes"]

L = lambda x: round(x / 1e5, 1)                                    # noqa: E731
ce = {k: [] for k in STRIKES}
pe = {k: [] for k in STRIKES}
gap = []
for i, m in enumerate(mins):
    g = grid.get(m)
    if g is None:
        gap.append(i)
    for k in STRIKES:
        c, p = g["k"].get(str(k), [None, None]) if g else (None, None)
        ce[k].append(None if c is None else L(c))
        pe[k].append(None if p is None else L(p))
pre = {"ce": {}, "pe": {}}                                         # each wall's peak before START (the ghost's start)
for m, g in grid.items():
    if m < START:
        for k in STRIKES:
            c, p = g["k"].get(str(k), [0, 0])
            pre["ce"][k] = max(pre["ce"].get(k, 0), L(c))
            pre["pe"][k] = max(pre["pe"].get(k, 0), L(p))

o0 = F[mins[0]][6]
fut = [F[m][4] for m in mins]
spot = [S[m][4] for m in mins]
foi = [round((F[m][6] - o0) / LOT) for m in mins]
vol = [round(F[m][5] / LOT) for m in mins]
fhi = [F[m][2] for m in mins]

# the book's holes (the laptop slept 12:54:12-13:00:20, Windows: "Critical Battery Trigger Met" 12:53:51)
holes, prev = [], None
for r in rows(f"data/book/book_{IDX}_{DAY}.jsonl"):
    t = r.get("t") or r.get("ts")
    if not isinstance(t, (int, float)):
        continue
    t = t / 1000 if t > 1e12 else t
    if prev and t - prev > 60:
        holes.append([hms(prev), hms(t)])
    prev = t

msgs = [r for r in rows(f"data/messages/msg_{DAY}.jsonl") if hms(r["at"]) >= START + ":00"]
shown = {r.get("key"): hms(r["at"]) for r in msgs if r.get("kind") == "FLOW"}


def _m(hm):
    return int(hm[:2]) * 60 + int(hm[3:5])


pushes = []
for r in handshake.read(handshake.load(DAY, IDX), handshake.LAST_M + 2):
    if r["t"] < START:
        continue
    pm = _m(r["t"])
    # a push whose 2-min window starts inside a hole carries the hole's missed trades: the catch-up, not a push
    artifact = any(_m(a) <= pm and pm - 2 <= _m(b) for a, b in holes)
    pushes.append({"t": r["t"], "am": r.get("am"), "dir": r["dir"], "lots": r["lots"], "k": r.get("k"), "side": r.get("side"),
                   "ans": r.get("ans"), "chg": r.get("chg"), "bar": r.get("bar"), "who": r.get("who"), "behind": r.get("behind"),
                   "fut": r.get("fut"), "x": (r.get("effort") or {}).get("x"), "shown": shown.get(r.get("key")),
                   "artifact": artifact})


def fnum(s):
    return float(s.replace(",", ""))


def judge(r):
    """A NIFTY line against the fut path after it reached the screen (the record, not a rate)."""
    at = hms(r["at"])[:5]
    line, word = r.get("line") or "", r.get("word") or ""
    after = [m for m in mins if m > at]
    if r.get("kind") == "FLOW":
        mt = re.search(r"PUSH [▲▼] (\d\d:\d\d)", line)
        if mt:
            return "late", f"push {mt.group(1)} → screen {hms(r['at'])} · {_m(at) - _m(mt.group(1))} min baad"
    if "BAN SAKTA" in word or "BAN SAKTA" in line:
        p = re.search(r"P ([\d,]+(?:\.\d+)?)f", line)
        if p and after:
            P, hi = fnum(p.group(1)), max(F[m][2] for m in after[:60])
            return ("wrong", f"galat · P {P:,.0f}f ke baad +{hi - P:,.0f}f upar gaya") if hi - P > 20 else ("right", "sahi")
    stop = re.search(r"stop (?:[\d,]+s\|)?([\d,]+)f", line)
    if r.get("kind") == "SETUP" and "SELL" in word and stop and after:
        st = fnum(stop.group(1))
        hit = next((m for m in after if F[m][2] >= st), None)
        return ("wrong", f"galat · stop {st:,.0f}f {hit} pe hit") if hit else ("right", "stop nahi laga")
    if "likhne wale bhage" in line:
        return "right", "CE writers bhag rahe (sach)"
    return "info", ""


stream = []
for r in msgs:
    if r.get("kind") == "HEALTH" or r.get("idx") != IDX:
        continue
    tag, note = judge(r)
    stream.append({"at": hms(r["at"]), "kind": r.get("kind"), "line": r.get("line"), "tag": tag, "note": note})

zone = [{"t": r["t"], "kind": r.get("kind") or "trig", "side": r.get("side"), "lvl": round(r.get("px") or r.get("level") or 0, 1)}
        for r in rows("data/trigger_log.jsonl")
        if r.get("day") == DAY and r.get("index") == IDX and r.get("rule") == "zone3" and r.get("t", "") >= START]
marks = []
for r in rows(f"data/tape/ofd_marks_{IDX}_{DAY}.jsonl"):
    t = datetime.datetime.fromtimestamp(r["t"] / 1000).strftime("%H:%M")
    if t >= START:
        marks.append({"t": t, "kind": r["kind"], "side": r["side"], "p": r["p"], "size": r["size"]})

chapters = [
    ["11:20", "Range. 22,600s aur 22,700s CE = deewar (cap). 11:25 push ▲ +213 lots → 22,700 CE ne jawab nahi diya (NAHI). Peeche 22,600 PE writers ne floor banaya (+3.3L)."],
    ["11:57", "Fut ne 22,700f chhua, spot 22,643s = range ke beech. 11:57 aur 12:08 ke push → NAHI. Fut OI flat. Breakout nahi tha."],
    ["12:12", "Screen ne SELL bola: ZONE SELL 3/4 (12:15) + TOP BAN SAKTA 4/4 (12:20). Par 22,600 / 22,700 CE deewar 10:37 se ghat rahi thi — ye contradiction screen pe nahi tha."],
    ["12:25", "Har push pe CE writers thoda aur bhaage. 12:40 push +542: wall ne abhi bhi jawab nahi diya, par fut OI −542 lots = shorts cover kar rahe. 12:39 SELL ka stop 22,745f hit."],
    ["12:44", "12:44 DEEWAR TOOTI: 22,700 CE −3.7L in 3 min. 12:49 sellers ne dabaya (−571) → 22,700 PE writers ne pakda (TIKI +4.3L). 12:53 phir TOOT (−6.6L, effort 22×)."],
    ["12:54", "LAPTOP SO GAYA (12:53:51 battery critical). 6 min kuch live nahi: na book, na OI, na GoCharting. Isi beech fut 22,800 → 22,875f, 12:59–13:00 me ~2,100 lots."],
    ["13:01", "Jaage to high ho chuka tha: 22,778s / 22,875f. Naya floor 22,700 PE (+20L). 13:01 ka '+3,534 lots' push = 6 min ka chhoota hua volume ek minute me, asli push nahi."],
]

data = {"day": DAY, "idx": IDX, "mins": mins, "spot": spot, "fut": fut, "fhi": fhi, "foi": foi, "vol": vol,
        "strikes": STRIKES, "ce": ce, "pe": pe, "pre": pre, "gap": gap, "holes": holes, "pushes": pushes,
        "stream": stream, "zone": zone, "marks": marks, "chapters": chapters}
html = open(os.path.join(HERE, "replay.html"), encoding="utf-8").read().replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
print(f"{len(mins)} minutes {mins[0]}-{mins[-1]} · grid gaps {len(gap)} · {len(pushes)} pushes · {len(stream)} lines · holes {holes}")
for p in pushes:
    print(" push", p["t"], p["dir"], p["lots"], p["k"], p["side"], p["ans"], p["am"], "shown", p["shown"], "ARTIFACT" if p["artifact"] else "")
for s in stream:
    if s["tag"] != "info":
        print(" ", s["at"], s["tag"], s["note"])
