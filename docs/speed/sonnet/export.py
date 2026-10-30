"""export.py -- RAFTAAR v2 (Sonnet's face). Runs the converged engine (../final/raftaar.py) minute by minute over 5 real NIFTY
days, in lockstep with BANKNIFTY / SENSEX (the official replay's loop), and adds what the v1 face lacked:

  * WRITER TIMELINE  the §1d fronts (tapemap/fronts.py, read-only, imported as is) re-read CAUSALLY at every minute on the grid
                     cut at that minute, with the session-high OI ranking board.first_fold uses. One lane per front that was top-2 for >= 45 min of the day. The raw §1d
                     state flickers (27 Oct: CE 22,700 reads B S B S U S U ... around its turn), so a lane's state only
                     commits when it fills >= 3 of the last 4 minutes (debounce()), and the commit is back-dated to the first
                     of those minutes. RUKA is stamped at the front's own high (peak_at), exactly as Board.tsx's kramOf does.
  * OI TREND         net writing near ATM (PUT build - CALL build, the nine strikes nearest spot, same strike set at both ends
                     of the window = raftaar.measures) over 15 / 30 / 60 min. See trend() for the vote and the verdict.
  * WALLS            CAP / FLOOR per minute = the day's biggest CALL / PUT build on the ladder (v1's capFloor), 3-of-4 held, so
                     the bands on the price panel step when writers roll and do not twitch.
  * THE SENTENCE     one plain Hinglish line <= 14 words per minute, built by template from the engine's fields (say()), and
                     held: it only changes when the picture changed (3-of-4 minutes).

    python export.py            -> data.js and RAFTAAR-v2.html (data inside), plus a printed self-check
    python export.py --check    -> the self-check only (no files written)
Read-only on tapemap/data. Stdlib only. Everything computed here sees only minutes <= t when it speaks of minute t.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TAPEMAP = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "final"))
sys.path.insert(0, TAPEMAP)
import chainio  # noqa: E402
import fronts  # noqa: E402
import raftaar as R  # noqa: E402
import refbuild  # noqa: E402

DAYS = [("NIFTY", "2026-10-26", "trend ▲"), ("NIFTY", "2026-10-21", "trend ▼"), ("NIFTY", "2026-10-22", "chop · stop-loss din"),
        ("NIFTY", "2026-10-06", "expiry grind / pin"), ("NIFTY", "2026-10-27", "Oct expiry")]

NEED, WIN = 3, 4              # a state commits when it fills >= 3 of the last 4 minutes (her 3-min bar; the engine's HOLD = 3)
PAUSE = (7, 9)               # a lane's ruke / likh turn must fill >= 7 of the last 9 minutes (~3 of her 3-min bars): short pauses are noise
LANE_MIN = 45                 # minutes a strike-side must have been a §1d top-2 front today to get a lane
TREND_W = (15, 30, 60)        # OI-trend windows, minutes
TREND_TAU = 0.40              # [I] |net / gross| >= 0.40 = one side does >= 70 % of the window's writing activity -> a vote
TREND_MIN_L = 5.0             # [I] a window with < 5 L gross activity in the nine is "could not read", never a vote
SENT_CAP = 14                 # words


# ---- small things --------------------------------------------------------------------------------------------------------

def L(x):
    """'+267.3L' / '−46.3L' / '0' / a number -> lakh as a float, None when absent."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return round(x / 1e5, 1)
    s = str(x).replace("−", "-").replace("L", "").replace("+", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def side(s):
    s = s or {}
    return {"x": s.get("structure"), "sp": s.get("speed"), "v": L(s.get("speed_now_L_min"))}


def lockstep(d):
    """All three indices stepped together, each seeing the others' picture as it stood (replay.run_day's loop), so the
    grades and stamps here are the official replay's. -> ({idx: [(t, out)]}, {idx: engine}, {idx: grid})"""
    engines, grids = {}, {}
    for idx in chainio.IDXS:
        grid, opens, kind = chainio.load_chain(idx, d)
        if grid:
            engines[idx] = R.Engine(idx, d, R.Ref(refbuild.load(idx)), kind, opens, chainio.load_fut(idx, d), read_words=chainio.load_read(idx, d))
            grids[idx] = grid
    outs = {idx: [] for idx in engines}
    for t in sorted({t for g in grids.values() for t in g}):
        for idx, eng in engines.items():
            if t in grids[idx]:
                peers = {o: R._peer_at(e.pic_hist, t) for o, e in engines.items() if o != idx}
                rw = R._read_word_at(eng.read_words, t) if eng.read_words else None
                outs[idx].append((t, eng.step(t, grids[idx][t], peers=peers, read_word=rw)))
    return outs, engines, grids


# ---- the debounce (lanes, walls, verdict, sentence all use this one) ----------------------------------------------------------

def debounce(seq, need=NEED, win=WIN, hold=NEED, slow=None):
    """[(start, known, state)] over a per-minute list of hashable states (None = absent counts as a state).
    `state` commits at minute `known` once it fills >= `need` of the last `win` minutes (3 of 4); `start` is the earliest minute
    of that window holding it (back-dated). `slow` = {state: (need, win)} overrides the bar for the states that flicker on noise
    (a pause, a restart): they must hold longer. A turn also needs `start` >= the last turn's start + `hold`, so no segment is
    shorter than 3 minutes and a replay never has to un-draw one: a segment is KNOWN at `known`, its colour starts at `start`."""
    slow = slow or {}
    segs, cur = [], object()
    for j in range(len(seq)):
        for x in set(seq[max(0, j - 8):j + 1]):
            nd, wn = (slow.get(x) or (need, win)) if segs else (need, win)
            j0 = max(0, j - wn + 1)
            w = seq[j0:j + 1]
            if x != cur and w.count(x) >= nd:
                start = j0 + w.index(x)
                if segs and start - segs[-1][0] < hold:
                    continue
                segs.append((start, j, x))
                cur = x
                break
    return segs


def at_known(segs, j):
    """The state committed as of minute j (known <= j), or None."""
    cur = None
    for start, known, x in segs:
        if known <= j:
            cur = x
        else:
            break
    return cur


# ---- WRITER TIMELINE ----------------------------------------------------------------------------------------------------

def front_lanes(grid, opens):
    """One lane per (side, strike) that was a §1d top-2 front for >= 10 minutes. Causal: fronts.read on the grid cut at each
    minute. -> (lanes, infos) ; each lane: {side, k, seg: [[start, known, state]], ev: [[i, known, kind, spot, ...]]}
    state: B likh rahe (at its high) · P phir likh rahe (building again, under its high) · S ruke · U chhod rahe · N never
    built today · None absent.  kinds: ruka (at the front's high) · chhod (first minute of the confirmed UNWINDING) · phir."""
    times, spots, _ks, _S, RP = fronts.grid(grid)
    jx = {t: j for j, t in enumerate(times)}
    info = {}
    for j, t in enumerate(times):
        if j < fronts.SLOPE_MARKS:                      # §1d needs its 15 marks; before that the Board itself says "forming"
            continue
        pk = {}
        for (k, sd), rp in RP.items():
            o = opens.get(str(int(k)))
            if o is not None:
                pk[(k, sd.lower())] = o[0 if sd == "CE" else 1] + rp[j]
        for f in fronts.read(fronts.cut(grid, t), pk):
            code = "N" if f["peak"] <= 0 else f["state"][0]
            info.setdefault((f["side"], f["k"]), {})[j] = (code, jx.get(f["peak_at"], j), f["peak"], f["chg"])
    lanes = []
    for (sd, k), inf in info.items():
        if len(inf) < LANE_MIN:          # a front that was top-2 for under 45 minutes of the day is a flash, not a lane
            continue
        seq = [inf[j][0] if j in inf else None for j in range(len(times))]
        segs, prev = [], None                              # segs: dicts {start, known, st, ev}
        for start, known, x in debounce(seq, slow={"B": PAUSE, "S": PAUSE}):
            ev = []
            if x is None:
                segs.append({"start": start, "known": known, "st": None, "ev": ev})
                continue
            _, pidx, peak, chg = inf[known]
            lastseg = segs[-1] if segs and segs[-1]["st"] in ("B", "P") else None
            if x in ("S", "U") and peak > 0 and prev in (None, "B", "N"):
                # RUKA: the first stop since a build, stamped at the front's own high (pidx), as Board.tsx's kramOf does. A
                # restart that stalls again without a new high of its own stops at ITS local high (argmax of the lane's chg).
                ei = pidx
                if prev == "B" and lastseg and lastseg["st"] == "P":
                    ei = max(range(lastseg["start"], known + 1), key=lambda j: inf[j][3] if j in inf else float("-inf"))
                ev.append([ei, known, "ruka", spots[ei], round((inf[ei][3] if ei in inf else peak) / 1e5, 1), round(chg / 1e5, 1)])
                if prev == "B" and lastseg:
                    # repaint: the build ended at its high, so the minutes since it were already "ruke"
                    ri = max(ei, lastseg["start"])
                    if x == "S":
                        start = ri
                    elif ri < start:
                        segs.append({"start": ri, "known": known, "st": "S", "ev": []})
            if x == "U" and prev == "S":
                # the Board's ruka is the front's LAST high before the give-back: a pause that still set a new high moves the stop to it
                host = next((sg for sg in reversed(segs) if sg["st"] == "S" and any(e[2] == "ruka" for e in sg["ev"])), None)
                e0 = next((e for e in host["ev"] if e[2] == "ruka"), None) if host else None
                if e0 and e0[0] < pidx < start:
                    e0[0], e0[3], e0[4] = pidx, spots[pidx], round(peak / 1e5, 1)
                    host["start"] = pidx
            if x == "U" and prev != "U":
                ev.append([start, known, "chhod", spots[start], round((peak - chg) / 1e5, 1), round(chg / 1e5, 1)])
            if x == "B" and prev in ("S", "U"):
                ev.append([start, known, "phir", spots[start], round((peak - chg) / 1e5, 1), round(chg / 1e5, 1)])
                segs.append({"start": start, "known": known, "st": "P", "ev": ev})
            else:
                segs.append({"start": start, "known": known, "st": x, "ev": ev})
            prev = x
        # a repainted stop can leave the build before it (or itself) with no minutes: drop those, and the stamps they carried
        changed = True
        while changed:
            changed = False
            for n in range(len(segs) - 1):
                if segs[n]["start"] >= segs[n + 1]["start"] and segs[n]["st"] is not None:
                    del segs[n]
                    changed = True
                    break
        # a restart reads "phir likh rahe" until it makes a new high of its own, then plain "likh rahe"
        fixed = []
        for n, sg in enumerate(segs):
            fixed.append([sg["start"], sg["known"], sg["st"]])
            if sg["st"] == "P":
                end = segs[n + 1]["start"] if n + 1 < len(segs) else len(times)
                hi = next((j for j in range(sg["start"], end) if j in inf and inf[j][1] >= sg["start"] and inf[j][0] == "B"), None)
                if hi is not None and hi > sg["start"]:
                    fixed.append([hi, hi, "B"])
        ev = sorted((e for sg in segs for e in sg["ev"]), key=lambda e: e[0])
        lanes.append({"side": sd, "k": int(k), "seg": fixed, "ev": ev, "n": len(inf)})
    # keep the three longest-lived per side, top of the price axis first (CALL high strikes ... PUT low strikes)
    keep = []
    for sd in ("CE", "PE"):
        keep += sorted([l for l in lanes if l["side"] == sd], key=lambda l: -l["n"])[:3]
    keep.sort(key=lambda l: (0 if l["side"] == "CE" else 1, -l["k"]))
    return keep, info, times, spots


def board_unwind_at(grid, side_, k, peak_at):
    """Board.py's unwind_at, rule for rule: the first §1d UNWINDING read after the high (no debounce). For the cross-check."""
    times, _spots, _ks, S, RP = fronts.grid(grid)
    v, jx = S[(k, side_)], {t: j for j, t in enumerate(times)}
    pj = jx.get(peak_at)
    if pj is None:
        return None
    for j in range(max(pj + 1, fronts.SLOPE_MARKS), len(v)):
        if fronts._state(v[j], RP[(k, side_)][j], v[j] - v[j - fronts.SLOPE_MARKS]) == fronts.UNWINDING:
            return times[j]
    return None


# ---- WALLS ---------------------------------------------------------------------------------------------------------------

def walls(grid, times, keep):
    """CAP = the strike with the day's biggest CALL build on the kept ladder, FLOOR = same for PUT (v1's capFloor, ties to the
    lower strike); 3-of-4 held. -> (cap_segs, floor_segs) as [[start, known, strike]]."""
    cap, flo = [], []
    for t in times:
        c, p, cm, pm = None, None, 0.0, 0.0
        for k in keep:
            ce, pe = (grid[t]["k"].get(str(int(k))) or [0.0, 0.0])
            if ce > cm:
                c, cm = k, ce
            if pe > pm:
                p, pm = k, pe
        cap.append(c)
        flo.append(p)
    return ([list(s) for s in debounce(cap)], [list(s) for s in debounce(flo)])


# ---- OI TREND ------------------------------------------------------------------------------------------------------------

def trend(grid, opens, times):
    """Per minute and per window w (15/30/60): Z_w = (PUT net OI change - CALL net OI change) over the nine strikes nearest spot
    at t, SAME strikes at both ends (raftaar.measures, so w=15 is the engine's own net_L). R_w = Z_w / (gross adds + cuts of both
    sides) in [-1, 1]: how one-sided the writing was. A window VOTES  +1 (PUT build dominates: ▲)  or  -1 (CALL build dominates: ▼)
    when |R_w| >= 0.40 and its gross >= 5 L; else 0 (balanced: both sides writing about alike, or nothing happening).
    VERDICT  ▲ when >= 2 of 3 windows vote up and none votes down; ▼ mirror; else RANGE  (1/3 up = "halka ▲", up AND down = "mila-jula",
    no votes = "barabar").  The verdict is held 3-of-4 to enter a trend and 6-of-8 to fall back to RANGE (hysteresis). Display only [I]; a count of windows, never a %.
    -> {r: [[x100 per minute] per w], z: [[lakh] per w], pn30, cn30, vote: [[-1/0/1, ...]], verdict: segs [[start, known, v]]}"""
    rr, zz, pn30, cn30, votes = [[], [], []], [[], [], []], [], [], []
    for t in times:
        v = []
        for wi, w in enumerate(TREND_W):
            m = R.measures(grid, t, w, opens)
            if not m or m.get("why"):
                rr[wi].append(None)
                zz[wi].append(None)
                v.append(None)
                if w == 30:
                    pn30.append(None)
                    cn30.append(None)
                continue
            ce, pe = m["CE"], m["PE"]
            gross = ce["adds"] + ce["cuts"] + pe["adds"] + pe["cuts"]
            z = pe["net"] - ce["net"]
            r = z / max(gross, 1.0)
            rr[wi].append(round(100 * r))
            zz[wi].append(round(z / 1e5))
            v.append(0 if gross < TREND_MIN_L * 1e5 else (1 if r >= TREND_TAU else -1 if r <= -TREND_TAU else 0))
            if w == 30:
                pn30.append(round(pe["net"] / 1e5))
                cn30.append(round(ce["net"] / 1e5))
        votes.append(v)
    verd = []
    for v in votes:
        if all(x is None for x in v):
            verd.append(None)
            continue
        up, dn = sum(1 for x in v if x == 1), sum(1 for x in v if x == -1)
        verd.append(1 if (up >= 2 and dn == 0) else -1 if (dn >= 2 and up == 0) else 0)
    # the vote counts the verdict was made of (for the box: "3/3", "1/3 halka ▲", "mila-jula")
    cnt = [[sum(1 for x in v if x == 1), sum(1 for x in v if x == -1)] if any(x is not None for x in v) else None for v in votes]
    return {"r": rr, "z": zz, "pn30": pn30, "cn30": cn30, "cnt": cnt, "verdict": [list(s) for s in debounce(verd, slow={0: (6, 8)}, hold=6)]}


# ---- THE SENTENCE --------------------------------------------------------------------------------------------------------

def nm(k):
    return f"{int(k):,}"


def nwords(s):
    return len(s.replace("·", " ").split())


def fit(parts, order, cap=SENT_CAP):
    """parts: [[alt0 (longest), alt1, ...], ...]; order: which part to shorten next when over the cap. -> the text."""
    pick = [0] * len(parts)

    def text():
        return " ".join(a[i] for a, i in zip(parts, pick) if a[i]).replace("  ", " ").strip()
    for p in order:
        if nwords(text()) <= cap:
            break
        if pick[p] < len(parts[p]) - 1:
            pick[p] += 1
    return text()


def clause(sd, d):
    """One side's structure as a short Hinglish clause (<= 5 words) naming the strike the engine itself named."""
    S = "CALL" if sd == "CE" else "PUT"
    x, st = d.get("structure"), d.get("strikes") or []
    kc = next((s["k"] for s in st if s["d"] < 0), None)
    ka = next((s["k"] for s in st if s["d"] > 0), None)
    if x in ("BHAAG RAHE", "ITM COVER"):
        return f"{S} {nm(kc)} se bhaag rahe" if kc else f"{S} bhaag rahe"
    if x == "ROLL" and kc and ka:
        return f"{S} {'cap' if sd == 'CE' else 'floor'} {nm(kc)}→{nm(ka)} {'upar' if sd == 'CE' else 'neeche'}"
    if x in ("LIKH RAHE", "DEEWAR MOTI"):
        return f"{S} {nm(ka)} pe likh rahe" if ka else f"{S} likh rahe"
    if x in ("ATM LIKH", "DEEWAR PRICE PE"):
        return f"{S} price ke paas likh rahe"
    if x == "DEEWAR HAT RAHI":
        return f"{S} deewar hat rahi"
    return f"{S} ruke"


def say(out):
    """The engine's picture, in one plain Hinglish line, from its fields only (no AI). <= 14 words, first things first."""
    pic, sides, nb = out.get("picture") or {}, out.get("sides"), out.get("numbers") or {}
    w, d = pic.get("word"), pic.get("dir")
    if w == "?" or not sides:
        return "Abhi padh rahe hain · pehle thoda record chahiye"
    ce, pe = sides["CE"], sides["PE"]
    z = nb.get("Z_pct")
    zd = (1 if z > 0 else -1 if z < 0 else 0) if (nb.get("Z_level") in ("NOTABLE", "BADA") and z is not None) else 0
    zor = {1: "upar ka zor", -1: "neeche ka zor", 0: ""}[zd]
    zshort = {1: "upar zor", -1: "neeche zor", 0: ""}[zd]
    story = pic.get("story") or ""
    if w in ("CHAL RAHA", "WAPSI") and d:
        up = d == 1
        Ls, Ws = ("CE", "PE") if up else ("PE", "CE")
        cl, cw = clause(Ls, sides[Ls]), clause(Ws, sides[Ws])
        price = ("price saath" if zd == d else "price ulta") if zd else {"SAATH": "price saath", "ULTA": "price ulta", "MILA-JULA": "price mila-jula"}.get(pic.get("qual"), "")
        pre = (f"Wapsi {'upar' if up else 'neeche'} ·" if w == "WAPSI" else "")
        if "PHANS RAHE" in story or "ROK RAHE" in story:           # the hurt side writes INTO the move
            mv = "chadh raha" if up else "gir raha"
            end = "phans rahe" if "PHANS" in story else "rok rahe"
            return fit([[pre, ""], [f"{cl}, price {mv} · {end}"], [f"· {zor}" if zor else ""]], [2, 0])
        return fit([[pre, ""], [f"{cl}, {cw}"], [f"· {zor}", f"· {zshort}", ""] if zor else [""],
                    [f"· {price}", ""] if price else [""]], [2, 3, 2, 0])
    if w == "BINA OI" and d:
        return f"Price akela {'chadh' if d == 1 else 'gir'} raha · writers peeche nahi · bina OI"
    if w == "CHOP":
        return fit([[f"CHOP · {clause('CE', ce)} · {clause('PE', pe)}"], ["· price dono taraf", ""]], [1, 0])
    if w == "PIN":
        k = pic.get("k")
        pk = f"{nm(k)}s" if k else ""
        if "BAARI" in story:
            return f"PIN {pk} · CALL aur PUT baari-baari ruk rahe · price tika"
        if "TIKA" in story:
            return f"PIN {pk} · CALL PUT dono barabar baithe · price tika"
        return f"PIN {pk} ban raha · CALL aur PUT dono likh rahe · price tika"
    if w == "ATKA":
        lead = "PE" if d == 1 else "CE"
        way = "upar" if d == 1 else "neeche"
        return fit([[f"ATKA · {clause(lead, sides[lead])}"], [f"· {way} ka zor, price nahi chal raha", f"· {way} zor, price nahi"]], [1, 1])
    if w == "UNWIND":
        return "UNWIND · CALL aur PUT dono position kaat rahe"
    if w == "KHAMOSH":
        return "Kuch khaas nahi · writers noise se upar nahi"
    return "Abhi padh rahe hain · pehle thoda record chahiye"


CLS = {"BHAAG RAHE": "cover", "ITM COVER": "cover", "DEEWAR HAT RAHI": "cover", "LIKH RAHE": "write", "DEEWAR MOTI": "write",
       "ATM LIKH": "write", "DEEWAR PRICE PE": "write", "ROLL": "roll", "RUKE": "ruke"}
HELD = (8, 10)                # a side's behaviour class / the zor sign must fill >= 8 of the last 10 minutes to enter the headline's key


def held(seq, need=HELD[0], win=HELD[1]):
    """seq smoothed causally: at minute j, the value committed by then (debounce, 8 of 10), None before the first commit."""
    segs, out = debounce(seq, need=need, win=win, hold=need), []
    for j in range(len(seq)):
        cur = None
        for _s, known, x in segs:
            if known <= j:
                cur = x
        out.append(cur)
    return out


# ---- one day -------------------------------------------------------------------------------------------------------------

class Tab:
    """A string table: the rows store small ints, the page holds each distinct string once (keeps the file under ~1 MB)."""

    def __init__(self):
        self.t, self.ix = [], {}

    def __call__(self, s):
        if s is None:
            return -1
        if s not in self.ix:
            self.ix[s] = len(self.t)
            self.t.append(s)
        return self.ix[s]


def day(idx, d, label, T):
    outs, engines, grids = lockstep(d)
    grid, eng, kind = grids[idx], engines[idx], engines[idx].kind
    ts = sorted(grid)
    spots = [grid[t]["spot"] for t in ts if grid[t].get("spot")]
    ks = sorted({float(k) for t in ts for k in grid[t]["k"]})
    step = min(b - a for a, b in zip(ks, ks[1:]) if b > a)
    keep = [k for k in ks if min(spots) - 4 * step <= k <= max(spots) + 4 * step]
    jx = {t: j for j, t in enumerate(ts)}
    # raw pieces
    lanes, _info, _times, _spots = front_lanes(grid, chainio.load_chain(idx, d)[1])
    cap, flo = walls(grid, ts, keep)
    tr = trend(grid, chainio.load_chain(idx, d)[1], ts)
    # columns
    C = {k: [] for k in ("m", "s", "w", "d", "ph", "si", "gn", "gN", "gw", "st", "q", "pk", "ch", "cx", "m15", "cxx", "cxs", "cxv",
                         "pxx", "pxs", "pxv", "sent")}
    oi = []
    sent_raw, shown = [], []
    for t, out in outs[idx]:
        p, nb = out.get("picture") or {}, out.get("numbers") or {}
        g = p.get("grade") or {}
        sd = out.get("sides") or {}
        c, pe_ = side(sd.get("CE")), side(sd.get("PE"))
        C["m"].append(R.mins(t))
        C["s"].append(out.get("spot"))
        C["w"].append(T(p.get("word")))
        C["d"].append(p.get("dir") or 0)
        C["ph"].append(T(p.get("phase")))
        C["si"].append(T(p.get("since")))
        C["gn"].append(g.get("n") if g else -1)
        C["gN"].append(g.get("N") if g else -1)
        C["gw"].append(T(g.get("word")))
        C["st"].append(T(p.get("story")))
        C["q"].append(T(p.get("qual")))
        C["pk"].append(int(p["k"]) if p.get("k") else 0)
        C["ch"].append(1 if p.get("in_chop") else 0)
        C["cx"].append(T(out.get("contradiction")))
        C["m15"].append(round(nb["m15"], 1) if isinstance(nb.get("m15"), (int, float)) else None)
        C["cxx"].append(T(c["x"]))
        C["cxs"].append(T(c["sp"]))
        C["cxv"].append(c["v"])
        C["pxx"].append(T(pe_["x"]))
        C["pxs"].append(T(pe_["sp"]))
        C["pxv"].append(pe_["v"])
        cell = grid[t]["k"]
        for k in keep:
            pr = cell.get(str(int(k))) or cell.get(str(k)) or [None, None]
            oi += [None if pr[0] is None else round(pr[0] / 1e5), None if pr[1] is None else round(pr[1] / 1e5)]
        sent_raw.append(say(out))
    # the sentence is held: it changes only when the picture changed -- word / direction (3 of 4 minutes), or a side's behaviour class
    # (covering / writing / rolling / still) or the zor sign (8 of 10) -- and its text, strikes included, is the one said at the commit
    # minute, so a strike that flickers never rewrites it
    wd, cl, zs = [], [], []
    for t, out in outs[idx]:
        p, sd, nb = out.get("picture") or {}, out.get("sides") or {}, out.get("numbers") or {}
        wd.append((p.get("word"), p.get("dir")))
        cl.append((CLS.get((sd.get("CE") or {}).get("structure")), CLS.get((sd.get("PE") or {}).get("structure"))))
        z = nb.get("Z_pct")
        zs.append((1 if z > 0 else -1) if (z and nb.get("Z_level") in ("NOTABLE", "BADA")) else 0)
    segs = debounce(list(zip(wd, held(cl), held(zs))))
    for j in range(len(sent_raw)):
        cur = None
        for start, known, x in segs:
            if known <= j:
                cur = known
        shown.append(sent_raw[cur] if cur is not None else "Abhi padh rahe hain · pehle thoda record chahiye")
    C["sent"] = [T(s) for s in shown]
    stamps = []
    for s in eng.stamps:
        i = jx.get(s["t"])
        if i is not None:
            stamps.append({"i": i, "t": s["t"], "s": s.get("spot"), "kind": s.get("kind"), "title": s.get("title"), "why": s.get("why"), "g": s.get("grade")})
    return {"idx": idx, "day": d, "label": label, "kind": kind, "step": step, "strikes": [int(k) for k in keep], "n": len(ts), "c": C, "oi": oi,
            "stamps": stamps, "lanes": lanes, "cap": cap, "floor": flo, "trend": tr, "sent_raw_n": len(set(shown))}, grid, eng


# ---- the self-check ---------------------------------------------------------------------------------------------------------

def check(days_out):
    """Prints and asserts: sentence length, monotone segments, and the 27 Oct stamps against the Board's own rules."""
    for dd, grid, eng in days_out:
        T = dd["_T"]
        mx = max((nwords(T[i]) for i in dd["c"]["sent"] if i >= 0), default=0)
        assert mx <= SENT_CAP, (dd["day"], "sentence too long", mx)
        ch = sum(1 for a, b in zip(dd["c"]["sent"], dd["c"]["sent"][1:]) if a != b)
        for ln in dd["lanes"]:
            st = [s[0] for s in ln["seg"]]
            assert st == sorted(st), (dd["day"], ln["side"], ln["k"], "segments not monotone")
        print(f"{dd['day']}: {dd['n']} min · max sentence {mx} words · {ch} sentence changes ({dd['sent_raw_n']} distinct lines) · "
              f"{len(dd['lanes'])} lanes · {len(dd['stamps'])} stamps · {len(dd['cap'])} cap / {len(dd['floor'])} floor segs · "
              f"{len(dd['trend']['verdict'])} verdict segs")
    # 27 Oct vs the Board: at several clock times, run the Board's own code (fronts.read on the grid cut there, plus board.py's
    # unwind_at rule) and compare with what the lanes had committed by then.
    dd, grid, _eng = next(x for x in days_out if x[0]["day"] == "2026-10-27")
    times, spots, ks, S, RP = fronts.grid(grid)
    jx = {t: j for j, t in enumerate(times)}
    tally = [0, 0, 0, 0]
    print("\n27 Oct NIFTY — the Board's §1d read at T vs the lanes' stamps known by T  (ruka = the front's peak_at; chhod = unwind_at)")
    for T_ in ("10:00", "11:00", "12:00", "13:00", "14:00", "15:00"):
        j = jx[T_]
        cut = fronts.cut(grid, T_)
        pk = {}
        for (k, sd), rp in RP.items():
            o = chainio.load_chain("NIFTY", "2026-10-27")[1].get(str(int(k)))
            if o is not None:
                pk[(k, sd.lower())] = o[0 if sd == "CE" else 1] + rp[j]
        print(f"  {T_}")
        for f in fronts.read(cut, pk):
            ln = next((l for l in dd["lanes"] if l["side"] == f["side"] and l["k"] == int(f["k"])), None)
            bu = board_unwind_at(cut, f["side"], f["k"], f["peak_at"])
            mine = [e for e in (ln["ev"] if ln else []) if e[1] <= j]
            segs = [s for s in (ln["seg"] if ln else []) if s[1] <= j]
            st = segs[-1][2] if segs else None
            r = [times[e[0]] for e in mine if e[2] == "ruka"][-1:] or ["-"]
            c = [times[e[0]] for e in mine if e[2] == "chhod"][-1:] or ["-"]
            rk = [times[e[0]] for e in mine if e[2] == "ruka"]
            ch_ = [times[e[0]] for e in mine if e[2] == "chhod"]
            atp = f["state"] == "BUILDING" and f["peak"] - f["chg"] < 0.05 * f["peak"]      # Board.tsx atPeak: kramOf stamps only fronts that are off their high
            has_r = f["peak"] > 0 and not atp and ln is not None
            m_r = has_r and f["peak_at"] in rk
            m_c = (bu is not None and any(abs(R.mins(x) - R.mins(bu)) <= 2 for x in ch_))
            tally[0] += has_r; tally[1] += m_r; tally[2] += (bu is not None and ln is not None); tally[3] += m_c
            print(f"    Board {f['side']} {f['k']:.0f} {f['state']:9s} peak_at {f['peak_at']} unwind_at {bu or '-':5s} | lanes: state {st} last ruka {r[0]} last chhod {c[0]}"
                  f"{'' if ln else '  (no lane: front was top-2 < 45 min today)'}{'  [ruka = peak_at]' if m_r else ''}{'  [chhod = unwind_at ±2]' if m_c else ''}")
    print(f"  -> of the Board's fronts that have a lane: ruka stamp present {tally[1]}/{tally[0]} · chhod stamp within 2 min {tally[3]}/{tally[2]} "
          "(a miss = the Board's single day-peak cycle vs the lane's later cycle, or the 7-of-9 restart bar)")


def page():
    """live.html + data.js -> RAFTAAR-v2.html, one self-contained file (the data inside), so it opens anywhere."""
    js = open(os.path.join(HERE, "data.js"), encoding="utf-8").read()
    html = open(os.path.join(HERE, "live.html"), encoding="utf-8").read().replace('<script src="data.js"></script>', "<script>" + js + "</script>")
    with open(os.path.join(HERE, "RAFTAAR-v2.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote RAFTAAR-v2.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    if "--page" in sys.argv:           # the template changed, the data did not
        page()
        sys.exit(0)
    T = Tab()
    days_out = []
    for x in DAYS:
        dd, grid, eng = day(*x, T)
        dd["_T"] = T.t
        days_out.append((dd, grid, eng))
    check(days_out)
    if "--check" not in sys.argv:
        data = {"T": T.t, "days": [{k: v for k, v in dd.items() if k not in ("_T", "sent_raw_n")} for dd, _g, _e in days_out]}
        js = "window.RAFTAAR = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
        with open(os.path.join(HERE, "data.js"), "w", encoding="utf-8") as f:
            f.write(js)
        page()
