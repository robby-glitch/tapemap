"""export.py -- RAFTAAR v3 (Opus). The converged engine (../final/raftaar.py, untouched) run minute by minute over five NIFTY
days in lockstep with BANKNIFTY and SENSEX (the official replay's loop), plus four face layers, every one CAUSAL (minute t uses
minutes <= t only):

  SAHMATI   the engine's grade checks + two face checks (OI trend saath, fuel aage) -> an agreement score 0-100. Never odds.
  FUEL      per strike and side: OI written today and whether its writers are underwater (option ltp above their basis).
            Basis = tapemap/trapped_inventory.Ledger (today's adds x the premium they were added at); when the record starts after
            09:20 the ledger never saw the morning, so the exchange's day VWAP ('avg') is the basis and the page says so.
  ZOR       upar = PUT adds + CALL cuts, neeche = CALL adds + PUT cuts, over the nine and the engine's F window, lakh per minute.
  FRONTS    §1d top-2 per side AT EACH MINUTE (fronts.read on the grid cut there, ranked by open + running high like
            board.first_fold), board._fronts for unwind_at; 'phir' = the low after the peak once building again >= 5 % under it.

Copied from ../sonnet/export.py and kept as is: lockstep(), debounce(), trend() (OI trend 15/30/60) and the Hinglish sentence
(say() + its hold). Read-only on tapemap/data; writes only into this folder. Stdlib only.

    python export.py            -> RAFTAAR-v3.html (data gzipped inside) + the self-check
    python export.py --check    -> the self-check only
    python export.py --page     -> rebuild the page from live.html + data.b64 (template change only)
"""
import base64
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TAPEMAP = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "final"))
sys.path.insert(0, TAPEMAP)
import board  # noqa: E402
import chainio  # noqa: E402
import fronts  # noqa: E402
import raftaar as R  # noqa: E402
import refbuild  # noqa: E402
import trapped_inventory  # noqa: E402

DAYS = [("2026-10-26", "26 Oct · trend ▲"), ("2026-10-21", "21 Oct · trend ▼"), ("2026-10-22", "22 Oct · chop"),
        ("2026-10-06", "6 Oct · expiry pin"), ("2026-10-27", "27 Oct · expiry")]
# replay helpers only: the minutes worth jumping to on each day (never shown as a read)
LOOK = {"2026-10-26": ["09:45", "09:55", "10:05", "11:35", "14:09"], "2026-10-21": ["09:58", "10:10", "10:40", "12:00"],
        "2026-10-22": ["10:01", "11:16", "12:21", "14:00"], "2026-10-06": ["09:40", "11:39", "13:30"],
        "2026-10-27": ["09:27", "09:45", "10:21", "12:03", "14:00"]}
WINDOW = 6                     # strikes either side of the day's spot range kept for the ladder
PAIN_STEPS = 6                 # writers' pain is shipped only for strikes within 6 steps of spot at that minute
PHIR = 0.05                    # Board.tsx UNDER: building but >= 5 % under its own peak = "phir likh rahe"
FUEL_SHARE = 0.25              # [I] face check "fuel aage": >= 25 % of the hurt side's today-written OI (nine) is underwater
AGLA_SHARE = 0.25              # [I] the next wall ahead: a strike holding >= 25 % of its side's biggest today-written OI in the nine
LATE = "09:20"                 # a record starting after this cannot build the writers' basis -> day VWAP
TREND_W, TREND_TAU, TREND_MIN_L = (15, 30, 60), 0.40, 5.0
NEED, WIN = 3, 4
SENT_CAP = 14


# ---- copied from ../sonnet/export.py --------------------------------------------------------------------------------------

def lockstep(d):
    engines, grids = {}, {}
    for idx in chainio.IDXS:
        grid, opens, kind = chainio.load_chain(idx, d)
        if grid:
            engines[idx] = R.Engine(idx, d, R.Ref(refbuild.load(idx)), kind, opens, chainio.load_fut(idx, d), read_words=chainio.load_read(idx, d))
            grids[idx] = (grid, opens)
    outs = {idx: [] for idx in engines}
    for t in sorted({t for g, _o in grids.values() for t in g}):
        for idx, eng in engines.items():
            if t in grids[idx][0]:
                peers = {o: R._peer_at(e.pic_hist, t) for o, e in engines.items() if o != idx}
                rw = R._read_word_at(eng.read_words, t) if eng.read_words else None
                outs[idx].append((t, eng.step(t, grids[idx][0][t], peers=peers, read_word=rw)))
    return outs, engines, grids


def debounce(seq, need=NEED, win=WIN, hold=NEED, slow=None):
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
    cur = None
    for _start, known, x in segs:
        if known <= j:
            cur = x
        else:
            break
    return cur


def trend(grid, opens, times):
    """OI trend (Sonnet's, unchanged): per window w, R = (PUT net - CALL net) / gross over the nine; |R| >= 0.40 with >= 5 L gross
    votes; verdict ▲ / ▼ when >= 2 of 3 vote that way and none the other, else RANGE; held 3-of-4 in, 6-of-8 back to RANGE."""
    zz, votes = [[], [], []], []
    for t in times:
        v = []
        for wi, w in enumerate(TREND_W):
            m = R.measures(grid, t, w, opens)
            if not m or m.get("why"):
                zz[wi].append(None)
                v.append(None)
                continue
            ce, pe = m["CE"], m["PE"]
            gross = ce["adds"] + ce["cuts"] + pe["adds"] + pe["cuts"]
            z = pe["net"] - ce["net"]
            r = z / max(gross, 1.0)
            zz[wi].append(round(z / 1e5))
            v.append(0 if gross < TREND_MIN_L * 1e5 else (1 if r >= TREND_TAU else -1 if r <= -TREND_TAU else 0))
        votes.append(v)
    verd = []
    for v in votes:
        if all(x is None for x in v):
            verd.append(None)
            continue
        up, dn = sum(1 for x in v if x == 1), sum(1 for x in v if x == -1)
        verd.append(1 if (up >= 2 and dn == 0) else -1 if (dn >= 2 and up == 0) else 0)
    segs = debounce(verd, slow={0: (6, 8)}, hold=6)
    return {"z": zz, "vote": votes, "verdict": [at_known(segs, j) for j in range(len(times))]}


def nm(k):
    return f"{int(k):,}"


def nwords(s):
    return len(s.replace("·", " ").split())


def fit(parts, order, cap=SENT_CAP):
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
        if "PHANS RAHE" in story or "ROK RAHE" in story:
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


def held(seq, need=8, win=10):
    segs = debounce(seq, need=need, win=win, hold=need)
    return [at_known(segs, j) for j in range(len(seq))]


def sentences(outs):
    """The sentence, held (Sonnet's rule): it changes only when word/dir (3 of 4) or a side's behaviour class / the zor sign (8 of 10)
    changed, and the text is the one said at the commit minute."""
    raw = [say(o) for _t, o in outs]
    wd, cl, zs = [], [], []
    for _t, out in outs:
        p, sd, nb = out.get("picture") or {}, out.get("sides") or {}, out.get("numbers") or {}
        wd.append((p.get("word"), p.get("dir")))
        cl.append((CLS.get((sd.get("CE") or {}).get("structure")), CLS.get((sd.get("PE") or {}).get("structure"))))
        z = nb.get("Z_pct")
        zs.append((1 if z > 0 else -1) if (z and nb.get("Z_level") in ("NOTABLE", "BADA")) else 0)
    segs = debounce(list(zip(wd, held(cl), held(zs))))
    shown = []
    for j in range(len(raw)):
        cur = None
        for _s, known, _x in segs:
            if known <= j:
                cur = known
        # the hold keeps strike numbers from flickering; it must never let the line speak of a picture the word no longer shows
        # (the engine already holds the word 3 min): a new word or direction speaks its own line at once
        shown.append(raw[cur] if cur is not None and wd[cur] == wd[j] else raw[j])
    return shown


# ---- the record's premiums (for the writers' basis) and each index's own future (for the s / f tag) -------------------------

def load_prem(idx, d):
    """{"HH:MM": {k: ((ce_oi, ce_ltp, ce_avg), (pe_oi, pe_ltp, pe_avg))}} -- last row per minute, chainio's rule."""
    f = chainio._open(os.path.join(chainio.DATA, "chain", f"chain_{idx}_{d}.jsonl"))
    out = {}
    if f is None:
        return out
    with f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict) or r.get("spot") is None or not r.get("strikes") or not r.get("ts"):
                continue
            t = r["ts"][:5]
            if t < "09:15" or t > "15:30":
                continue
            row = {}
            for s in r["strikes"]:
                legs = []
                for sd in ("ce", "pe"):
                    x = s.get(sd) or {}
                    legs.append((x.get("oi"), x.get("ltp"), x.get("avg")))
                row[float(s["k"])] = legs
            out[t] = row
    return out


def load_fut_own(idx, d):
    """{"HH:MM": fut ltp} from this index's own futures book (a price for the f tag only; SENSEX's flow is still NIFTY's, §1q)."""
    f = chainio._open(os.path.join(chainio.DATA, "book", f"book_{idx}_{d}.jsonl"))
    out = {}
    if f is None:
        return out
    with f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("ltp") and isinstance(r.get("t"), (int, float)):
                m = int(r["t"] / 1000 + 19800) % 86400 // 60
                out["%02d:%02d" % divmod(m, 60)] = float(r["ltp"])
    return out


# ---- fronts at each minute (the Board's read, causal) -------------------------------------------------------------------------

STATE = {fronts.BUILDING: "B", fronts.STALLED: "S", fronts.UNWINDING: "U"}


def fronts_by_minute(grid, opens, times, spots, S, RP):
    """[None | [(side, k, code, peak_j, unwind_j, phir_j, peak_L, chg_L)] x 4] per minute. code: L likh rahe (at its high) · P phir likh
    rahe · S ruk gaye · U chhod rahe · N aaj nahi bana. Same call chain as the Board: fronts.read + board._fronts on the grid cut at t."""
    jx = {t: j for j, t in enumerate(times)}
    opT = {(float(k), sd): v[i] for k, v in opens.items() for i, sd in enumerate(("ce", "pe"))}
    out = []
    for j, t in enumerate(times):
        if j < fronts.SLOPE_MARKS:
            out.append(None)
            continue
        pk = {(k, sd.lower()): opT[(k, sd.lower())] + rp[j] for (k, sd), rp in RP.items() if (k, sd.lower()) in opT}
        rows = fronts.read(fronts.cut(grid, t), pk)
        keys = {(f["k"], f["side"]) for f in rows}
        ext = board._fronts(rows, spots[j], opT, times[:j + 1], spots[:j + 1],
                            {kk: S[kk][:j + 1] for kk in keys}, {kk: RP[kk][:j + 1] for kk in keys})
        cur = []
        for f in ext:
            pj, v = jx.get(f["peak_at"]), S[(f["k"], f["side"])]
            if f["peak"] <= 0:
                code = "N"
            elif f["state"] == fronts.BUILDING:
                code = "L" if f["peak"] - f["chg"] < PHIR * f["peak"] else "P"
            else:
                code = STATE[f["state"]]
            phir = None
            if code == "P" and pj is not None:
                phir = min(range(pj, j + 1), key=lambda i: v[i])
            cur.append((f["side"], int(f["k"]), code, pj, jx.get(f["unwind_at"]), phir, round(f["peak"] / 1e5, 2), round(f["chg"] / 1e5, 2)))
        out.append(cur)
    return out


def board_word(fr, times):
    """Board.tsx readOf(), ported word for word: the side that stopped first and is giving back is the fuel."""
    if not fr:
        return None, None
    built = [f for f in fr if f[6] > 0]
    if not built:
        return "AAJ KOI FRONT NAHI BANA", None
    pt = lambda f: times[f[3]] if f[3] is not None else ""  # noqa: E731
    unw = sorted((f for f in built if f[2] == "U"), key=pt)
    stl = sorted((f for f in built if f[2] == "S"), key=pt)
    lead = (unw or stl or [None])[0]
    if not lead:
        return "DONO TARAF LIKH RAHE HAIN", "koi nahi toota"
    who = lambda s: "CALL" if s == "CE" else "PUT"  # noqa: E731
    way = "neeche" if lead[0] == "PE" else "upar"
    step = unw if lead[2] == "U" else stl
    then = next((f for f in step if f[0] != lead[0]), None)
    both = f"pehle {who(lead[0])} {pt(lead)} · phir {who(then[0])} {pt(then)}" if then else None
    if lead[2] == "U":
        return ("DONO TARAF CHHOD RAHE" if then else f"{who(lead[0])} WRITERS CHHOD RAHE HAIN",
                both or f"{'▼' if lead[0] == 'PE' else '▲'} fuel {way} · {pt(lead)}")
    return ("DONO TARAF RUK GAYE" if then else f"{who(lead[0])} WRITERS RUK GAYE", both or f"dekho · wapas dein to fuel {way}")


# ---- one index-day ------------------------------------------------------------------------------------------------------------

class Tab:
    def __init__(self):
        self.t, self.ix = [], {}

    def __call__(self, s):
        if s is None:
            return -1
        if s not in self.ix:
            self.ix[s] = len(self.t)
            self.t.append(s)
        return self.ix[s]


def numL(x):
    """'+79.5L' / '−46.3L' / '0' -> lakh x 100 as an int (None when absent)."""
    if x is None:
        return None
    try:
        return round(100 * float(str(x).replace("−", "-").replace("L", "").replace("+", "")))
    except ValueError:
        return None


def columns(flat, width):
    """minute-major flat list -> one delta-coded series per column (strike-side): first value, then differences; null stays null
    (absent is absent, never a zero) and the next value is coded against the last one present. The page undoes it (undelta)."""
    out = []
    for c in range(width):
        prev, col = None, []
        for x in flat[c::width]:
            if x is None:
                col.append(None)
            else:
                col.append(x if prev is None else x - prev)
                prev = x
        out.append(col)
    return out


def L100(x):
    return None if x is None else round(x / 1e3)          # lakh x 100 as an int (2 decimals: BANKNIFTY's small books)


def index_day(idx, d, outs, eng, grid, opens, T):
    times, spots, ks_all, S, RP = fronts.grid(grid)
    assert [t for t, _o in outs] == times, (idx, d, "engine minutes and grid minutes differ")
    n = len(times)
    step = eng.step_ or 50
    keep = [k for k in ks_all if min(spots) - WINDOW * step <= k <= max(spots) + WINDOW * step]
    kx = {k: i for i, k in enumerate(keep)}
    prem = load_prem(idx, d)
    fut = load_fut_own(idx, d)
    vwap = times[0] > LATE
    # the writers' basis per strike-side (trapped_inventory.Ledger, fed every minute in order)
    led = {(k, i): trapped_inventory.Ledger(side="short") for k in keep for i in (0, 1)}
    tr = trend(grid, opens, times)
    sent = sentences(outs)
    frs = fronts_by_minute(grid, opens, times, spots, S, RP)
    C = {x: [] for x in ("w", "d", "ph", "si", "gn", "gN", "gw", "ck", "sn", "sN", "st", "q", "pk", "sw", "swg", "pd", "why", "cx",
                         "sent", "m15", "net", "cxx", "pxx", "cch", "pch", "cph", "pph", "csp", "psp", "cv", "pv", "up", "dn", "tv", "tz",
                         "bx", "fut", "bw", "bc", "fu")}
    oi, pn = [], []
    fut_basis = []
    for j, (t, out) in enumerate(outs):
        row, s = grid[t], spots[j]
        p, nb, sd = out.get("picture") or {}, out.get("numbers") or {}, out.get("sides") or {}
        g = p.get("grade") or {}
        # --- ladder: OI written today and pain per strike-side
        pr = prem.get(t) or {}
        pains = {}
        for k in keep:
            cell = (row["k"].get(str(int(k))) if float(k).is_integer() else row["k"].get(str(k))) or [None, None]
            legs = pr.get(k) or [(None, None, None)] * 2
            for i in (0, 1):
                o_, ltp, avg = legs[i]
                L_ = led[(k, i)]
                if o_ is not None and ltp is not None:
                    L_.feed(t, float(o_), float(ltp))
                basis = (avg if vwap else (L_.basis if L_.basis is not None else avg))
                pain = None if (ltp is None or basis is None) else round(float(ltp) - float(basis))
                pains[(k, i)] = pain
                oi.append(L100(cell[i]))
                pn.append(pain if abs(k - s) <= PAIN_STEPS * step else None)     # pain is only drawn near price
        # --- fuel (the nine nearest spot, §1d's window)
        nine = fronts.nine([k for k in keep if (str(int(k)) in row["k"])], s)
        fu = []
        share = {}
        for i, sgn in ((0, 1), (1, -1)):
            built = {k: max(0.0, (row["k"].get(str(int(k))) or [0, 0])[i]) for k in nine}
            tot = sum(built.values())
            ph = {k: b for k, b in built.items() if b > 0 and (pains.get((k, i)) or 0) > 0}
            phs = sum(ph.values())
            share[i] = (phs / tot) if tot > 0 else None
            top = max(ph, key=lambda k: ph[k]) if ph else None
            big = max(built.values()) if built else 0
            ahead = sorted((k for k in nine if (k - s) * sgn > 0 and built[k] >= AGLA_SHARE * big and big > 0
                            and (pains.get((k, i)) or 0) <= 0), key=lambda k: abs(k - s))
            agla = ahead[0] if ahead else None
            # the nearest trapped strike still AHEAD of price (or at it) that carries >= 25 % of the side's biggest trapped build
            near = min((k for k in ph if (k - s) * sgn >= -step / 2 and ph[k] >= AGLA_SHARE * max(ph.values())),
                       key=lambda k: abs(k - s), default=None)
            fu += [L100(phs), int(top) if top else 0, L100(ph[top]) if top else 0, round((top - s) * sgn) if top else 0,
                   pains.get((top, i)) if top else 0, int(agla) if agla else 0, L100(built[agla]) if agla else 0,
                   round((agla - s) * sgn) if agla else 0, L100(tot),
                   int(near) if near else 0, L100(ph[near]) if near else 0, round((near - s) * sgn) if near else 0,
                   pains.get((near, i)) if near else 0]
        # burned during the current leg: OI the hurt side gave back since the picture began
        burn = None
        if p.get("word") in ("CHAL RAHA", "WAPSI") and p.get("dir") and p.get("since") in grid:
            i = 0 if p["dir"] == 1 else 1
            j0 = times.index(p["since"])
            ks_ = set(nine) | set(fronts.nine([k for k in keep if str(int(k)) in grid[p["since"]]["k"]], spots[j0]))
            sv = lambda k: S.get((k, ("CE", "PE")[i])) or [0.0] * n  # noqa: E731
            burn = sum(max(0.0, sv(k)[j0] - sv(k)[j]) for k in ks_)
        fu.append(L100(burn))
        C["fu"].append(fu)
        # --- SAHMATI: the engine's checks + the two face checks
        checks = dict(g.get("checks") or {}) if g else {}
        word, dr = p.get("word"), p.get("dir")
        if g:
            v = tr["verdict"][j]
            if v is not None and word in ("CHAL RAHA", "WAPSI", "ATKA") and dr:
                checks["trend"] = v == dr
            elif v is not None and word in ("PIN", "CHOP"):
                checks["trend"] = v == 0
            if word in ("CHAL RAHA", "WAPSI") and dr:
                sh = share[0 if dr == 1 else 1]
                if sh is not None:
                    checks["fuel"] = sh >= FUEL_SHARE
            elif word == "PIN" and share[0] is not None and share[1] is not None:
                checks["fuel"] = share[0] < FUEL_SHARE and share[1] < FUEL_SHARE
        sn, sN = sum(1 for x in checks.values() if x), len(checks)
        C["sn"].append(sn if g else -1)
        C["sN"].append(sN if g else -1)
        C["ck"].append(T("|".join(f"{k}:{int(bool(x))}" for k, x in checks.items())) if g else -1)
        # --- the engine's picture, verbatim
        C["w"].append(T(word))
        C["d"].append(dr or 0)
        C["ph"].append(T(p.get("phase")))
        C["si"].append(T(p.get("since")))
        C["gn"].append(g.get("n", -1) if g else -1)
        C["gN"].append(g.get("N", -1) if g else -1)
        C["gw"].append(T(g.get("word")) if g else -1)
        C["st"].append(T(p.get("story")))
        C["q"].append(T(p.get("qual")))
        C["pk"].append(int(p["k"]) if p.get("k") else 0)
        sw = p.get("swing") or {}
        C["sw"].append(sw.get("dir") or 0)
        sg = sw.get("grade") or {}
        C["swg"].append(T(f"{sg['n']}/{sg['N']}") if sg else -1)
        C["pd"].append(T(p.get("pending")))
        C["why"].append(T(p.get("why")))
        C["cx"].append(T(out.get("contradiction")))
        C["sent"].append(T(sent[j]))
        C["m15"].append(nb.get("m15"))
        C["net"].append(numL(nb.get("net_L")))
        for side, a, b, c_, d_, e_ in (("CE", "cxx", "cch", "cph", "csp", "cv"), ("PE", "pxx", "pch", "pph", "psp", "pv")):
            x = sd.get(side) or {}
            C[a].append(T(x.get("structure")))
            C[b].append(T(x.get("chip")))
            ph_ = x.get("phanse") or []
            C[c_].append(T(", ".join(f"{nm(z['k'])} {z['built_L']} {z['till']} tak" for z in ph_)) if ph_ else -1)
            C[d_].append(T(x.get("speed")))
            C[e_].append(numL(x.get("speed_now_L_min")))
        # --- ZOR over the engine's F window (lakh per minute x 100)
        mF = R.measures(grid, t, eng.F, opens)
        if mF and not mF.get("why"):
            C["up"].append(round((mF["PE"]["adds"] + mF["CE"]["cuts"]) / eng.F / 1e3))
            C["dn"].append(round((mF["CE"]["adds"] + mF["PE"]["cuts"]) / eng.F / 1e3))
        else:
            C["up"].append(None)
            C["dn"].append(None)
        C["tv"].append(tr["verdict"][j])
        C["tz"].append([tr["z"][w][j] for w in range(3)] + [tr["vote"][j][w] for w in range(3)])
        # --- basis (3-min median of fut - spot), for the f tag
        fp = fut.get(t)
        fut_basis.append(None if fp is None else fp - s)
        xs = sorted(x for x in fut_basis[-3:] if x is not None)
        C["bx"].append(round(xs[len(xs) // 2]) if xs else None)
        C["fut"].append(fp)
        bw, bc = board_word(frs[j], times)
        C["bw"].append(T(bw))
        C["bc"].append(T(bc))
    # peak / now are not shipped: the page reads them off the strike's own OI series (oiS), so the two can never disagree
    fr_out = [None if f is None else [[0 if x[0] == "CE" else 1, kx.get(float(x[1]), -1), x[2], -1 if x[3] is None else x[3],
                                       -1 if x[4] is None else x[4], -1 if x[5] is None else x[5]] for x in f] for f in frs]
    # a front outside `keep` cannot be drawn: it would be > 7 strikes from the day's range, never inside the nine
    assert all(x[1] >= 0 for f in fr_out if f for x in f), (idx, d, "a front outside the kept strikes")
    jx = {t: j for j, t in enumerate(times)}
    stamps = [{"i": jx[s_["t"]], "k": s_["kind"], "ti": T(s_["title"]), "wy": T(s_.get("why")), "g": s_.get("grade"), "s": s_.get("spot")}
              for s_ in eng.stamps if s_["t"] in jx]
    return {"idx": idx, "kind": eng.kind, "step": step, "ks": [int(k) if float(k).is_integer() else k for k in keep],
            "m": [R.mins(t) for t in times], "s": spots, "c": C, "oiS": columns(oi, len(keep) * 2), "pnS": columns(pn, len(keep) * 2),
            "fr": fr_out, "stamps": stamps,
            "basis": "VWAP" if vwap else "LEDGER", "start": times[0]}


def build():
    T = Tab()
    days = []
    for d, label in DAYS:
        outs, engines, grids = lockstep(d)
        dd = {"day": d, "label": label, "look": LOOK.get(d, []), "ix": {}}
        for idx in chainio.IDXS:
            if idx in engines:
                dd["ix"][idx] = index_day(idx, d, outs[idx], engines[idx], grids[idx][0], grids[idx][1], T)
        days.append(dd)
        print(d, "done", {i: len(x["m"]) for i, x in dd["ix"].items()})
    return {"T": T.t, "days": days}


# ---- self-check ---------------------------------------------------------------------------------------------------------------

def check(data):
    T = data["T"]
    tx = lambda i: T[i] if i >= 0 else None  # noqa: E731
    by = {dd["day"]: dd for dd in data["days"]}

    def at(dd, idx, hhmm):
        x = dd["ix"][idx]
        return x, x["m"].index(R.mins(hhmm))

    # 27 Oct NIFTY: the Board's CE 22,700 high at 09:27
    x, j = at(by["2026-10-27"], "NIFTY", "09:50")
    times = [R.hm(m) for m in x["m"]]
    rows = [(("CE", "PE")[f[0]], x["ks"][f[1]], f[2], times[f[3]] if f[3] >= 0 else None, times[f[4]] if f[4] >= 0 else None) for f in x["fr"][j]]
    print("27 Oct NIFTY 09:50 fronts:", rows)
    ce27 = next(r for r in rows if r[0] == "CE" and r[1] == 22700)
    assert ce27[3] == "09:27" and ce27[4] == "09:42", ce27
    print("  board:", tx(x["c"]["bw"][j]), "|", tx(x["c"]["bc"][j]))
    # 22 Oct NIFTY: chop, calm
    x = by["2026-10-22"]["ix"]["NIFTY"]
    words = [tx(w) for w in x["c"]["w"]]
    from collections import Counter
    cnt = Counter(words)
    print("22 Oct NIFTY words:", dict(cnt), "stamps", len(x["stamps"]), [(R.hm(x["m"][s["i"]]), tx(s["ti"])) for s in x["stamps"]])
    assert cnt["CHOP"] > len(words) / 2, "22 Oct should read CHOP most of the day"
    assert sum(1 for s in x["stamps"] if s["k"] == "neq") == 0
    # 26 Oct NIFTY: the 09:52 up-move and the fuel it burned
    for hhmm in ("09:45", "09:52", "10:05"):
        x, j = at(by["2026-10-26"], "NIFTY", hhmm)
        fu = x["c"]["fu"][j]
        print(f"26 Oct NIFTY {hhmm}: {tx(x['c']['w'][j])} {x['c']['d'][j]} sahmati {x['c']['sn'][j]}/{x['c']['sN'][j]} · "
              f"fuel▲ CALL phanse {fu[0] / 100}L mota {fu[1]} {fu[2] / 100}L {fu[3]} pts (+{fu[4]}) paas {fu[9]} {fu[10] / 100}L {fu[11]} pts · "
              f"fuel▼ PUT phanse {fu[13] / 100}L mota {fu[14]} · jala {None if fu[26] is None else fu[26] / 100}L")
    x, j = at(by["2026-10-26"], "NIFTY", "10:05")
    assert tx(x["c"]["w"][j]) == "CHAL RAHA" and x["c"]["d"][j] == 1 and (x["c"]["fu"][j][26] or 0) > 0
    # causal by construction: every per-minute series has one entry per minute
    for dd in data["days"]:
        for idx, x in dd["ix"].items():
            n = len(x["m"])
            assert all(len(v) == n for v in x["c"].values()), (dd["day"], idx)
            assert len(x["oiS"]) == len(x["ks"]) * 2 == len(x["pnS"]) and all(len(c) == n for c in x["oiS"])


def page(b64=None):
    if b64 is None:
        b64 = open(os.path.join(HERE, "data.b64"), encoding="ascii").read()
    html = open(os.path.join(HERE, "live.html"), encoding="utf-8").read().replace("__DATA__", b64)
    with open(os.path.join(HERE, "RAFTAAR-v3.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote RAFTAAR-v3.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    if "--page" in sys.argv:
        page()
        sys.exit(0)
    data = build()
    check(data)
    if "--check" not in sys.argv:
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        b64 = base64.b64encode(gzip.compress(raw, 9)).decode("ascii")
        print("data", len(raw) // 1024, "KB raw ->", len(b64) // 1024, "KB gz+b64")
        with open(os.path.join(HERE, "data.b64"), "w", encoding="ascii") as f:
            f.write(b64)
        page(b64)
