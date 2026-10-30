"""dream_build.py -- THE BRAIN of the dream-tool mockup: from facts_<day>.json (the record, dream_facts.py) it decides, CAUSALLY
at every 5-min close and every minute, what the screen says; dream.tpl.html only draws it.
Usage: python dream_build.py <day> [<day> ...]   -> dream.html beside this file (data inlined, no network).

Every rule here is written once and run over every replayed day (BRIEF §7 "never design off one day"). What each rule is,
whether it is [M] measured or [I] inferred, and how it grades noise from real, is DESIGN.md's job; the code is the port.
No hit rate, no win rate, no % confidence: agreement is a COUNT. No order path. Light theme. Every price says s or f.

  LEG      decode.swing_of on the closed 5-min bars (the production DECODE leg, 50-pt zigzag scaled by price); leg_of
           (the session-extreme leg) until the zigzag's first reversal                                                [I]
  TAKAT    per bar, a COUNT of price / delta / fut OI / likh siding with the leg (0..4; OI not counted in roll week)  [I]
  GRADE    every number against the DAY'S OWN distribution so far (prints.pct_rank, strict, six samples before any rank):
           NOISE < p70, HALKA < p90, ASLI < max, ZOR = above every earlier value                                       [M]
  ARM      at the zone's first arm (3-min, HER bands): 12 pieces checked at or before that minute, n saath / N checked  [I]
  FIRE     at the entry: STOP = the machine's (never changed) · SL POOL = the nearest real level beyond the extreme, 0.25 sigma
           past it · T1 = VWAP (§1i) or the next level · T2 / T3 = the next levels, each named with its frame          [I]
  TRADE    every close: EXIT (stop traded / front gave up on the losing side (§1m A1+A2) / 15:20) > SOCHO (a real change
           named) > HOLD, with the phase (chal raha / zor badh raha / pullback · koi badlaav nahi / thak raha)          [I]
  AAGE     every close: pools above and below (levels, walls, session extremes, unbroken marks), the corridor past the
           wall ahead, who is running (fut OI x price), spike risk n/5                                                  [I]
"""
import bisect
import json
import os
import statistics
import sys
from datetime import date

TAPE = r"C:\Users\kaam\Desktop\operator mode\tapemap"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TAPE)
import decode    # noqa: E402  (swing_of / leg_of / zz_thr: the production leg, read-only)
import prints    # noqa: E402  (pct_rank)

DAYS = sys.argv[1:]
OPEN_M, CLOSE_M, LAST_ENTRY, HOLD_END = 9 * 60 + 15, 15 * 60 + 30, 15 * 60, 15 * 60 + 20
LEAD_IN, LEAD_MOVE = 15, 10           # §1o's writers / writers15 thresholds (lead %, 15-min change)
SHARE = 0.05                          # §1o's delta share
FADE_FRAC = 0.25                      # FADE-D 2a: a new extreme on <= 25% of the leg's biggest same-side bar
BUF = 0.25                            # the stack's standard break distance, in sigma (HOLD v2 A2, marks TOOTA)
PB0, PB1 = 0.236, 0.618               # pullback: 23.6% .. 61.8% of the leg
ABS_PTS = 3.0                         # absorb: < 3 points bought per 100 lots against the leg
POOL_MAX_R = 2.5                      # the SL pool is looked for within 2.5x the machine's risk
TOX, CALM = 0.8, 0.5                  # VPIN session percentile: toxic / calm
GRADES = ("NOISE", "HALKA", "ASLI", "ZOR")
STALE = 3                             # minutes: a chain read older than this is "could not check" (fronts.STALE_MIN)


def hm(m):
    return f"{int(m) // 60:02d}:{int(m) % 60:02d}"


def mins(s):
    return int(s[:2]) * 60 + int(s[3:5])


def f0(p):
    return f"{p:,.0f}"


def last_at(d, m):
    """The value of a {minute: v} dict at the last key <= m (keys may be strings after JSON), or None."""
    k = None
    for x in d:
        xi = int(x)
        if xi <= m and (k is None or xi > k):
            k = xi
    return None if k is None else d[str(k)] if str(k) in d else d[k]


def grade(prior, x):
    """(grade word, pct) against the day's own earlier values; ('?', None) before six samples."""
    if x is None:
        return "?", None
    pr = [abs(v) for v in prior if v is not None]
    pct = prints.pct_rank(pr, abs(x))
    if pct is None:
        return "?", None
    if pr and abs(x) > max(pr):
        return "ZOR", pct
    return ("NOISE" if pct < 0.70 else "HALKA" if pct < 0.90 else "ASLI"), pct


def build(F):
    day, roll = F["day"], F["roll"]
    B = F["bars5"]
    n = len(B)
    spot1 = {int(k): v for k, v in F["spot"]["NIFTY"].items()}
    W = {int(k): v for k, v in F["writers"]["NIFTY"].items()}
    WP = {p: {int(k): v for k, v in F["writers"][p].items()} for p in ("BANKNIFTY", "SENSEX")}
    FR = {int(k): v for k, v in F["fronts"]["NIFTY"].items()}
    ones = {x["m"]: x for x in F["ones"]}
    flow1 = {int(k): v for k, v in F["flow1"].items()}
    vp = F["vpin"]
    lam = {int(k): v for k, v in F["effort"]["lam"].items()}
    eff_ev = F["effort"]["events"]
    xi = F["xi"]
    legs_r = F["legs"]
    marks = F["marks"]
    dec_ev = F["events"]
    ones_t = {o["c"]: o for o in F["onesided"]}
    LV = F["levels"]
    bars3 = F["bars3"]
    b3 = {mins(b["t"]): b for b in bars3}

    # ---- per-minute series the face draws: basis, lead, vpin ----------------------------------------------------------------
    def raw_basis(m):
        o = ones.get(m)
        s = spot1.get(m)
        return (o["c"] - s) if o and s is not None else None

    BIX_S = 3 * 60                                # fold.BIX_MS = 3 * 60000: her display basis, the 3-min median (A60)
    bsnap = F.get("basis_snap") or []
    bsecs = [x[0] for x in bsnap]

    def basis_at(m):
        """The median of the raw per-snapshot basis samples (fut LTP - chain spot, same second) in the 3 minutes ending with
        minute m; the per-minute approximation when the book has no sample there."""
        end = (m + 1) * 60
        i0, i1 = bisect.bisect_left(bsecs, end - BIX_S), bisect.bisect_right(bsecs, end)
        xs = [x[1] for x in bsnap[i0:i1]]
        if not xs:
            xs = [v for v in (raw_basis(k) for k in range(m - 2, m + 1)) if v is not None]
        return round(statistics.median(xs), 1) if xs else None

    def lead_at(m):
        w = last_at(W, m)
        return w["lead"] if w else None

    def writers_at(m):
        k = max((x for x in W if x <= m), default=None)
        return (W[k], k) if k is not None else (None, None)

    def fronts_at(m):
        k = max((x for x in FR if x <= m), default=None)
        return (FR[k], k) if k is not None else (None, None)

    def vpin_at(m):
        rows = [r for r in vp if r["m"] <= m]
        return rows[-1] if rows else None

    def xi_at(m):
        rows = [r for r in xi if r.get("at") is not None and r["at"] <= m * 60]
        return rows[-1] if rows else None

    def sigma3(m):
        """1 sigma of HER 3-min bands at the last 3-min bar closed by m (u1 - vwap), in futures points."""
        k = max((x for x in b3 if x + 3 <= m), default=None)
        b = b3.get(k) or {}
        return (b["u1"] - b["vwap"]) if b.get("u1") is not None and b.get("vwap") is not None else None

    def ftos(px, m):
        bs = basis_at(m)
        return f"{px:,.0f}f" + (f"|{px - bs:,.0f}s" if bs is not None else "")

    def stof(px, m):
        bs = basis_at(m)
        return px + bs if bs is not None else None

    # ---- the bars: cvd, vwap, leg, takat, grades, oi read -------------------------------------------------------------------
    ob = [{"s": b["m"] * 60, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "vol": b["vol"], "delta": b["delta"], "oi": b["oi"]} for b in B]
    cvd, pv, pvv, rows = 0, 0.0, 0.0, []
    leg = None
    for i, b in enumerate(B):
        c = b["m"] + 5
        cvd += b["delta"] or 0
        pv += (b["h"] + b["l"] + b["c"]) / 3 * (b["vol"] or 0)
        pvv += b["vol"] or 0
        vwap = pv / pvv if pvv else None
        # the leg (the production DECODE leg, causal on bars closed by c)
        try:
            L = decode.swing_of(ob[:i + 1], decode.ZZ_PCT * b["c"]) or decode.leg_of(ob[:i + 1])
        except Exception:
            L = None
        flipped = bool(leg and L and L["d"] != leg["d"])
        leg = L
        D = L["d"] if L else 0
        pc = B[i - 1]["c"] if i else b["o"]
        dp = (b["c"] - pc) if b["c"] is not None and pc is not None else 0
        doi = (b["oi"] - B[i - 1]["oi"]) if i and b.get("oi") and B[i - 1].get("oi") else None
        prior = B[:i]
        g_d, p_d = grade([x["delta"] for x in prior], b["delta"])
        g_v, p_v = grade([x["vol"] for x in prior], b["vol"])
        g_oi, p_oi = grade([(x["oi"] - prior[j - 1]["oi"]) if j and x.get("oi") and prior[j - 1].get("oi") else None for j, x in enumerate(prior)], doi)
        g_big, _ = grade([(x.get("big") or {}).get("lots") for x in prior], (b.get("big") or {}).get("lots"))
        # the OI x price read [I]: a graded OI change with a graded price move
        g_dp, _ = grade([(x["c"] - prior[j - 1]["c"]) if j else 0 for j, x in enumerate(prior)], dp)
        oi_read = None
        if doi is not None and g_oi in ("HALKA", "ASLI", "ZOR") and g_dp != "NOISE" and g_dp != "?":
            oi_read = ("SL KAT RAHE" if doi < 0 else "NAYE KHARIDAR") if dp > 0 else ("LONG NIKAL RAHE" if doi < 0 else "NAYE BECHNE WALE")
        oi_dir = {"SL KAT RAHE": 1, "NAYE KHARIDAR": 1, "LONG NIKAL RAHE": -1, "NAYE BECHNE WALE": -1}.get(oi_read, 0)
        lead, lead15 = lead_at(c), None
        l0 = lead_at(c - 15)
        if lead is not None and l0 is not None:
            lead15 = round(lead - l0, 1)
        votes = {"price": (dp * D > 0) if D else None, "delta": ((b["delta"] or 0) * D > 0) if D else None,
                 "oi": None if roll or not oi_read else (oi_dir * D > 0),
                 "likh": None if lead15 is None else (lead15 * D >= LEAD_MOVE) if D else None}
        takat = sum(1 for v in votes.values() if v is True)
        takat_n = sum(1 for v in votes.values() if v is not None)
        size = (L["to"] - L["from"]) * D if L else 0
        r = ((L["to"] - b["c"]) * D / size) if L and size > 0 else 0
        phase = "PULLBACK" if r >= PB0 else "CHAL"
        rows.append({"i": i, "m": b["m"], "t": b["t"], "c": c, "o": b["o"], "h": b["h"], "l": b["l"], "cl": b["c"], "delta": b["delta"], "vol": b["vol"],
                     "buy": b["buy"], "sell": b["sell"], "oi": b["oi"], "doi": doi, "spot": b.get("spot"), "basis": b.get("basis"),
                     "cvd": cvd, "vwap": round(vwap, 1) if vwap else None, "leg": ({"d": D, "from": L["from"], "to": L["to"], "k0": L["k0"], "from_bar": L["from_bar"]} if L else None),
                     "flipped": flipped, "takat": takat, "takat_n": takat_n, "votes": votes, "phase": phase, "r": round(r, 3),
                     "oi_read": oi_read, "lead": lead, "lead15": lead15, "g": {"delta": g_d, "vol": g_v, "oi": g_oi, "big": g_big, "dp": g_dp},
                     "stacks": b.get("stacks"), "unf_hi": b.get("unf_hi"), "unf_lo": b.get("unf_lo"), "big": b.get("big"),
                     "ux_delta": b.get("ux_delta"), "oc_fill": b.get("oc_fill"), "bins": b.get("bins")})

    # ---- levels in the futures frame at a minute ----------------------------------------------------------------------------------
    def levels_f(m):
        """Every level with its NATIVE number (px0, fr) and its futures value NOW (px, with the 3-min basis)."""
        out = []
        for l in LV:
            px = l["px"] if l["fr"] == "f" else stof(l["px"], m)
            if px is not None:
                out.append({"kind": l["kind"], "px": px, "fr": l["fr"], "src": l.get("src"), "px0": l["px"]})
        w, _ = writers_at(m)
        bs = basis_at(m)
        if w and bs is not None:
            out.append({"kind": "PE WALL", "px": w["floor"] + bs, "fr": "s", "src": f"{w['floor_oi']:,} lots", "px0": w["floor"]})
            out.append({"kind": "CE WALL", "px": w["ceil"] + bs, "fr": "s", "src": f"{w['ceil_oi']:,} lots", "px0": w["ceil"]})
            out.append({"kind": "MAX PAIN", "px": w["maxpain"] + bs, "fr": "s", "src": "chain", "px0": w["maxpain"]})
        return out

    def native(ls):
        for l in ls:
            l.setdefault("px0", l["px"])
        return ls

    def merge_frames(ls):
        """One kind seen in both frames: one row when the two fall within 5 pts after conversion (both natives kept),
        else two rows whose kind names its frame ('PDL s' / 'PDL f')."""
        by = {}
        for l in ls:
            by.setdefault(l["kind"], []).append(l)
        out = []
        for kind, group in by.items():
            fs_ = [l for l in group if l["fr"] == "f"]
            ss_ = [l for l in group if l["fr"] == "s"]
            if fs_ and ss_ and len(group) == 2 and abs(fs_[0]["px"] - ss_[0]["px"]) <= 5:
                out.append(dict(fs_[0], s0=ss_[0]["px0"], f0=fs_[0]["px0"], name=kind))
            elif fs_ and ss_:
                for l in group:
                    out.append(dict(l, name=f"{kind} {l['fr']}"))
            else:
                for l in group:
                    out.append(dict(l, name=kind))
        return out

    def rounds(m, px):
        bs = basis_at(m) or 0
        base = int((px - bs) // 50) * 50
        return [{"kind": "ROUND", "px": k + bs, "fr": "s", "src": "", "px0": k} for k in range(base - 150, base + 200, 50)]

    # ---- events (graded) ----------------------------------------------------------------------------------------------------------
    ev = []

    def add(m, k, p, side, chip, sub, gr, num=None, **kw):
        ev.append(dict({"m": m, "k": k, "p": p, "side": side, "chip": chip, "sub": sub, "grade": gr, "num": num}, **kw))

    for r in rows:
        c, L, D = r["c"], r["leg"], (r["leg"] or {}).get("d", 0)
        if r["flipped"] and L:
            add(c, "PALTA", L["from"], D, "PALTA " + ("▲" if D > 0 else "▼"), f"leg {'upar' if D > 0 else 'neeche'} se {f0(L['from'])}f", "ASLI")
        d = r["delta"] or 0
        if D and r["g"]["delta"] in ("ASLI", "ZOR") and d * D < 0:
            pts = -(r["cl"] - (rows[r["i"] - 1]["cl"] if r["i"] else r["o"])) * D
            no_ext = (r["l"] > L["from"] + 1) if D > 0 else (r["h"] < L["from"] - 1)
            if L and (r["l"] > L["to"] if D > 0 else r["h"] < L["to"]) and pts <= ABS_PTS * abs(d) / 100:
                add(c, "ABSORB", r["l"] if D > 0 else r["h"], D, ("BECHNE WALE" if D > 0 else "KHARIDAR") + " ABSORB",
                    f"Δ {d:+,} · {'low' if D > 0 else 'high'} {f0(r['l'] if D > 0 else r['h'])}f tika", r["g"]["delta"], d)
        if r["oi_read"]:
            k = {"SL KAT RAHE": "SL", "LONG NIKAL RAHE": "SL", "NAYE KHARIDAR": "OI", "NAYE BECHNE WALE": "OI"}[r["oi_read"]]
            side = 1 if r["oi_read"] in ("SL KAT RAHE", "NAYE KHARIDAR") else -1
            who = {"SL KAT RAHE": "shorts ke SL", "LONG NIKAL RAHE": "longs nikle", "NAYE KHARIDAR": "naye long", "NAYE BECHNE WALE": "naye short"}[r["oi_read"]]
            add(c, k, r["h"] if side > 0 else r["l"], side, r["oi_read"] + (" · kachcha" if roll else ""),
                f"{who} · OI {r['doi'] / 1000:+,.0f}k", "HALKA" if roll else r["g"]["oi"], r["doi"], roll=roll)
        if r["big"] and r["g"]["big"] in ("ASLI", "ZOR"):
            add(c, "BADA", r["big"]["p"], r["big"]["side"], "BADA PRINT " + ("▲" if r["big"]["side"] > 0 else "▼"),
                f"{r['big']['lots']:,} lot ek price {f0(r['big']['p'])}f", r["g"]["big"], r["big"]["lots"])
        st = [s for s in (r["stacks"] or []) if isinstance(s, dict)]
        if st and D:
            same = [s for s in st if (s.get("side") or 0) * D > 0]
            if same:
                add(c, "STACK", same[0].get("p") or r["cl"], D, "STACK " + ("▲" if D > 0 else "▼"),
                    f"{len(same)} stacked imbalance ({same[0].get('n')} rows) leg ki taraf", "HALKA" if len(same) == 1 else "ASLI", len(same))
    # the extension's marks, placed when their bar closed; their break known only from its time
    for mk in marks:
        chip = (mk["name"] or mk["kind"]).replace("·", "").replace("  ", " ").strip()
        chip = chip[2:] if chip[:1] in "▲▼" else chip
        add(mk["m"] + 5, {"absorption": "ROKA", "exhaustion": "THAKAN", "initiative": "ZOR", "vacuum": "KHALI", "trap": "PHANSE", "climax": "CLIMAX"}.get(mk["kind"], mk["kind"]),
            mk["p"], mk["side"], chip.upper(), f"{mk['lots']:,} lot · {f0(mk['p'])}f", grade([x["delta"] for x in B[:max(0, (mk['m'] - OPEN_M) // 5)]], mk["lots"])[0],
            mk["lots"], broke=mk.get("broke_m"), src=mk.get("src"))
    for e in dec_ev:
        if e.get("at") is None:
            continue
        add(e["at"] // 60 + 1, e["kind"], e["p"], e["side"], (e["name"] or e["kind"]).upper(), e.get("chip") or "", "ASLI" if e["kind"] in ("E1", "E6", "E7") else "HALKA", e.get("lots"))
    last_e = {}
    for e in eff_ev:
        w = {("H", "HI"): "MEHENGA HIGH · palat?", ("L", "LO"): "SASTA LOW · aur girega?"}.get((e["ext"], e["band"]))
        if w and e["m"] - last_e.get(e["ext"], -99) > 10:
            add(e["m"] + 1, "EFFORT", (ones.get(e["m"]) or {}).get("h" if e["ext"] == "H" else "l"), -1 if e["ext"] == "H" else 1, w,
                "lots/pt " + ("≥ 2× din median" if e["band"] == "HI" else "≤ ½ din median"), "ASLI")
        if w:
            last_e[e["ext"]] = e["m"]
    # VPIN crossings (re-armed only after the percentile falls under 0.6)
    prev, armed_v = None, False
    for v in vp:
        p = v.get("pct")
        if p is None:
            continue
        if prev is not None and prev < TOX <= p and not armed_v:
            add(v["m"], "VPIN", None, 0, "VPIN TOXIC", f"p{int(p * 100)} · books ek taraf", "ASLI", p)
            armed_v = True
        if p < 0.6:
            armed_v = False
        prev = p
    # writers: the defending / attacking front changes state
    emitted, run = {}, {}
    for m in sorted(FR):
        for side in ("CE", "PE"):
            f = next((x for x in FR[m] if x["side"] == side), None)
            if not f:
                continue
            key = (side, f["k"])
            st_, n_ = run.get(key, (None, 0))
            run[key] = (f["state"], n_ + 1 if st_ == f["state"] else 1)
            if run[key][1] >= 3 and emitted.get(key) != f["state"] and f["state"] in ("UNWINDING", "BUILDING"):
                if key in emitted:                        # the first state is the baseline, never an event
                    add(m, "LIKH", None, 1 if side == "PE" else -1,
                        f"{side} {f0(f['k'])} " + {"UNWINDING": "CHHOD RAHE", "BUILDING": "LIKH RAHE"}[f["state"]],
                        f"{f['chg'] / 65 / 1000:+,.0f}k lot aaj · peak {f['peak_at']}", "ASLI" if f["state"] == "UNWINDING" else "HALKA", f["chg"])
                emitted[key] = f["state"]
    # cross-index: a divergence at an extreme, and the sync changing
    last_div, seen_sync, pend = None, None, None
    for x in xi:
        if x.get("at") is None:
            continue
        m = x["at"] // 60 + 1
        e = x.get("ext")
        if e and e.get("verdict") == "DIVERGENT":
            per = e.get("per") or {}
            failed = [i[:3] for i, v in per.items() if (v or {}).get("status") == "FAILED"]
            key = (e["type"], tuple(failed))
            if key != last_div:
                add(m, "XDIV", None, 1 if e["type"] == "low" else -1, f"{' '.join(failed) or 'peer'} NE {'LOW' if e['type'] == 'low' else 'HIGH'} NAHI LIYA",
                    e.get("chip") or "", "ASLI")
            last_div = key
        elif e and e.get("verdict") == "CONFIRMED":
            last_div = None
        key = (x.get("sync") or {}).get("key")
        if key and key.startswith("SAATH"):
            if key == pend and key != seen_sync:              # held two rows in a row, and new
                add(m, "SYNC", None, 1 if "▲" in key else -1, key, (x.get("sync") or {}).get("chip") or "", "HALKA")
                seen_sync = key
            pend = key
        else:
            pend = None
    # reader auction events
    for a in F["auction"]:
        if a.get("at") is None or not a.get("state"):
            continue
        s = a["state"]
        if s.startswith("BREAKOUT") or s.startswith("TREND"):
            add(a["at"] // 60 + 1, "AUCTION", None, 1 if "UP" in s else -1, s.split(":")[0], a.get("chip") or "", "ASLI")
    ev.sort(key=lambda e: e["m"])

    # ---- ARM CHECK (12 pieces at the arm minute) ------------------------------------------------------------------------------
    def closed(m):
        return [r for r in rows if r["c"] <= m]

    def piece(k, ok, txt, tag="M"):
        return {"k": k, "ok": ok, "txt": txt, "tag": tag}

    def arm_check(side, m):
        """side +1 BUY / -1 SELL at minute m: the pieces that agree (True), fight (False), neutral (0) or cannot be read (None)."""
        S = side
        P = []
        w, wk = writers_at(m)
        fr, fk = fronts_at(m)
        stale_w = w is None or m - wk > STALE
        lead = None if stale_w else w["lead"]
        if lead is None:
            P.append(piece("LIKH", None, "chain purana" if w else "chain nahi", "M"))
        else:
            P.append(piece("LIKH", True if lead * S >= LEAD_IN else False if lead * S <= -LEAD_IN else 0,
                           f"{'PE' if lead > 0 else 'CE'} aage {abs(lead):.0f}% · PE {w['pe'] / 1000:+,.0f}k · CE {w['ce'] / 1000:+,.0f}k", "M"))
        l0 = lead_at(m - 15)
        if lead is None or l0 is None:
            P.append(piece("LIKH 15m", None, "15 min pehle ka read nahi", "M"))
        else:
            ch = lead - l0
            P.append(piece("LIKH 15m", True if ch * S >= LEAD_MOVE else False if ch * S <= -LEAD_MOVE else 0, f"lead {ch:+.0f} in 15 min", "M"))
        dside, aside = ("PE", "CE") if S > 0 else ("CE", "PE")
        if not fr or m - fk > STALE:
            P.append(piece(f"{dside} FRONT", None, "fronts nahi pade", "M"))
            P.append(piece(f"{aside} FRONT", None, "fronts nahi pade", "M"))
        else:
            d1 = next((f for f in fr if f["side"] == dside), None)
            a1 = next((f for f in fr if f["side"] == aside), None)
            if d1:
                P.append(piece(f"{dside} FRONT", True if d1["state"] == "BUILDING" else 0 if d1["state"] == "STALLED" else False,
                               f"{f0(d1['k'])} {d1['state'].lower()} · peak {d1['peak_at']}", "M"))
            if a1:
                P.append(piece(f"{aside} FRONT", True if a1["state"] == "UNWINDING" else 0 if a1["state"] == "STALLED" else False,
                               f"{f0(a1['k'])} {a1['state'].lower()} · peak {a1['peak_at']}", "M"))
        cl = closed(m)
        if len(cl) >= 3:
            w3 = cl[-3:]
            v3 = sum(x["vol"] or 0 for x in w3)
            d3 = sum(x["delta"] or 0 for x in w3)
            sh = d3 / v3 if v3 else 0
            P.append(piece("CVD 15m", True if sh * S >= SHARE else False if sh * S <= -SHARE else 0, f"Δ {d3:+,} / {v3:,} lot", "M"))
            lb = cl[-1]
            L = lb["leg"]
            if L:
                k0 = L["k0"]
                same = [abs(x["delta"] or 0) for x in cl[k0:] if (x["delta"] or 0) * L["d"] > 0]
                big = max(same) if same else 0
                dl = lb["delta"] or 0
                against = dl * S < 0
                if big and against and abs(dl) <= FADE_FRAC * big:
                    P.append(piece("Δ THAK", True, f"Δ {dl:+,} = {abs(dl) / big * 100:.0f}% of big {big:,}", "M"))
                elif big and against and abs(dl) >= 0.75 * big:
                    P.append(piece("Δ THAK", False, f"Δ {dl:+,} = {abs(dl) / big * 100:.0f}% of big {big:,}", "M"))
                elif not against and dl * S > 0:
                    P.append(piece("Δ THAK", True, f"Δ {dl:+,} already {'kharidar' if S > 0 else 'bechne wale'}", "M"))
                else:
                    P.append(piece("Δ THAK", 0, f"Δ {dl:+,} · big {big:,}", "M"))
        else:
            P.append(piece("CVD 15m", None, "3 closed bars nahi", "M"))
            P.append(piece("Δ THAK", None, "leg nahi", "M"))
        v = vpin_at(m)
        if not v or v.get("pct") is None:
            P.append(piece("VPIN", None, "pct abhi nahi · 10 buckets chahiye", "I"))
        else:
            P.append(piece("VPIN", True if v["pct"] <= CALM else False if v["pct"] >= TOX else 0, f"p{int(v['pct'] * 100)} · {v['vpin']:.2f}", "I"))
        rec = [e for e in eff_ev if m - 30 <= e["m"] <= m]
        if not rec:
            lm = last_at(lam, m)
            P.append(piece("EFFORT", None, "taaza high/low nahi" + (f" · {lm['lpp']} lots/pt" if lm else ""), "I"))
        else:
            e = rec[-1]
            if S > 0 and e["ext"] == "L":
                P.append(piece("EFFORT", False if e["band"] == "LO" else 0, "sasta low · aur girega?" if e["band"] == "LO" else "mehenga low (read nahi)", "I"))
            elif S < 0 and e["ext"] == "H":
                P.append(piece("EFFORT", True if e["band"] == "HI" else 0, "mehenga high · palat?" if e["band"] == "HI" else "sasta high (read nahi)", "I"))
            else:
                P.append(piece("EFFORT", 0, f"{'high' if e['ext'] == 'H' else 'low'} {e['band'].lower()} · ulti taraf", "I"))
        if len(cl) >= 4 and cl[-1].get("oi") and cl[-4].get("oi"):
            doi, dp = cl[-1]["oi"] - cl[-4]["oi"], cl[-1]["cl"] - cl[-4]["cl"]
            q = ("naye short" if doi > 0 else "longs nikle") if dp < 0 else ("naye long" if doi > 0 else "shorts ke SL")
            fuel = (dp * S < 0 and doi > 0)                  # fresh positions against the fade = fuel for it
            if roll:
                P.append(piece("FUT OI 15m", None, f"{q} {doi / 1000:+,.0f}k · roll, kachcha", "M"))
            else:
                P.append(piece("FUT OI 15m", True if fuel else False if (dp * S < 0 and doi < 0) else 0, f"{q} · OI {doi / 1000:+,.0f}k · {dp:+.0f} pts", "M"))
        else:
            P.append(piece("FUT OI 15m", None, "15 min ka OI nahi", "M"))
        x = xi_at(m)
        e = (x or {}).get("ext")
        want = "low" if S > 0 else "high"
        if x is None:
            P.append(piece("X PRICE", None, "xindex row nahi", "M"))
        elif e and e.get("type") == want:
            per = e.get("per") or {}
            took = [i[:3] for i, v in per.items() if (v or {}).get("status") == "TOOK" and i != "NIFTY"]
            failed = [i[:3] for i, v in per.items() if (v or {}).get("status") == "FAILED"]
            P.append(piece("X PRICE", True if e.get("verdict") == "DIVERGENT" else False if e.get("verdict") == "CONFIRMED" else 0,
                           (f"{' '.join(failed)} ne {want} nahi liya" if failed else f"{' '.join(took) or 'sab'} ne {want} liya"), "M"))
        else:
            dots = ((x.get("sync") or {}).get("dots") or {})
            agree = [i[:3] for i, v in dots.items() if i != "NIFTY" and (v or {}).get("dir") == -S]
            P.append(piece("X PRICE", 0 if not agree else False, (x.get("sync") or {}).get("key") or "koi taaza extreme nahi", "M"))
        pl = [v["lead"] for v in (last_at(WP[p], m) for p in ("BANKNIFTY", "SENSEX")) if v and v.get("lead") is not None]
        if not pl:
            P.append(piece("X OI", None, "BNF/SNX chain nahi", "M"))
        else:
            mean = sum(pl) / len(pl)
            P.append(piece("X OI", True if mean * S >= LEAD_IN else False if mean * S <= -LEAD_IN else 0,
                           "BNF/SNX PE lead " + " ".join(f"{v:+.0f}%" for v in pl), "M"))
        ot = ones_t.get(max((cc for cc in ones_t if cc <= m), default=-1))
        ty = (ot or {}).get("type")
        if not ty:
            P.append(piece("DIN", None, (ot or {}).get("why") or "din type nahi", "I"))
        elif ty.startswith("TREND"):
            with_ = ("▲" in ty) == (S > 0)
            P.append(piece("DIN", True if with_ else False, ty + (" · saath" if with_ else " · khilaaf"), "I"))
        else:
            P.append(piece("DIN", True if ty in ("CHOP", "PIN") else 0, ty, "I"))
        n = sum(1 for p in P if p["ok"] is True)
        N = sum(1 for p in P if p["ok"] is not None)
        against = sum(1 for p in P if p["ok"] is False)
        return {"pieces": P, "n": n, "N": N, "against": against}

    def before(m):
        """What came before, in numbers: the last 15 min."""
        cl = closed(m)
        if len(cl) < 4:
            return None
        a, b = cl[-4], cl[-1]
        return {"pts": round(b["cl"] - a["cl"], 1), "delta": sum(x["delta"] or 0 for x in cl[-3:]),
                "doi": (b["oi"] - a["oi"]) if a.get("oi") and b.get("oi") else None, "lead0": lead_at(a["c"]), "lead1": lead_at(b["c"]),
                "cvd": b["cvd"], "cvd0": a["cvd"]}

    # ---- FIRE: stop, SL pool, targets --------------------------------------------------------------------------------------------
    def plan(side, E, stop_rule, extreme, m):
        S = side
        sg = sigma3(m) or 20.0
        risk = abs(E - stop_rule)
        lv = levels_f(m) + rounds(m, E)
        cl = closed(m)
        sess_lo, sess_hi = min(r["l"] for r in cl), max(r["h"] for r in cl)
        lv.append({"kind": "DIN LOW", "px": sess_lo, "fr": "f", "src": "", "px0": sess_lo})
        lv.append({"kind": "DIN HIGH", "px": sess_hi, "fr": "f", "src": "", "px0": sess_hi})
        for e in ev:
            if e["m"] <= m and e["k"] in ("ROKA", "THAKAN", "PHANSE", "KHALI") and e.get("p") and (e.get("broke") is None or e["broke"] > m):
                lv.append({"kind": e["k"], "px": e["p"], "fr": "f", "src": e["chip"], "px0": e["p"]})
        # the SL pool: the nearest level beyond the extreme, within POOL_MAX_R x risk, 0.25 sigma past it
        bad_wall = "CE WALL" if S > 0 else "PE WALL"
        beyond = [l for l in lv if (l["px"] < extreme - 1 if S > 0 else l["px"] > extreme + 1) and abs(l["px"] - E) <= POOL_MAX_R * risk and l["kind"] not in ("ROUND", "MAX PAIN", "pLVN", "LVN", bad_wall)]
        beyond = beyond or [l for l in lv if (l["px"] < extreme - 1 if S > 0 else l["px"] > extreme + 1) and abs(l["px"] - E) <= POOL_MAX_R * risk]
        pool = None
        if beyond:
            near = min(beyond, key=lambda l: abs(l["px"] - extreme))
            pool = {"px": round(near["px"] - BUF * sg * S, 1), "level": near["kind"], "level_px": round(near["px"], 1), "fr": near["fr"],
                    "px0": near["px0"], "off": round(-BUF * sg * S, 1),
                    "why": f"{near['kind']} {near['fr']} {f0(near['px0'])} · {BUF}σ ({BUF * sg:.0f} pts) beyond = SL pool"}
        # targets: VWAP first (§1i), then the next levels in the direction
        vw = cl[-1]["vwap"]
        native(lv)
        bad_wall = "PE WALL" if S > 0 else "CE WALL"
        ahead = [l for l in lv if (l["px"] > E + 5 if S > 0 else l["px"] < E - 5) and l["kind"] not in (bad_wall, "pLVN", "LVN")]
        if vw and (vw - E) * S > 5:
            ahead.append({"kind": "VWAP", "px": vw, "fr": "f", "src": "§1i target", "px0": vw})
        ahead.sort(key=lambda l: abs(l["px"] - E))
        tg, seen = [], set()
        ahead = [l for l in ahead if abs(l["px"] - E) >= max(0.5 * risk, 10)]      # a target under half the risk is not a target
        ahead = merge_frames(ahead)
        ahead.sort(key=lambda l: abs(l["px"] - E))
        for l in ahead:
            if l["kind"] in ("ROUND", "DIN LOW", "DIN HIGH", "MAX PAIN") and len(tg) < 2:
                continue
            key = round(l["px"] / 5)
            if key in seen or any(abs(t["px"] - l["px"]) < 8 for t in tg):
                continue
            seen.add(key)
            tg.append({"px": round(l["px"], 1), "kind": l["name"], "fr": l["fr"], "px0": l.get("px0", l["px"]), "s0": l.get("s0"), "f0": l.get("f0"),
                       "why": (f"{l['name']} {f0(l['px0'])}" if l["fr"] == "f" or l.get("s0") is None else f"{l['name']} s {f0(l['px0'])}") + (f" · {l['src']}" if l.get("src") else "")})
            if len(tg) >= 3:
                break
        for j, t in enumerate(tg):
            t["R"] = round(abs(t["px"] - E) / risk, 1) if risk else None
            t["name"] = f"T{j + 1}"
        # the wall ahead and the corridor past it
        return {"E": E, "stop": stop_rule, "risk": round(risk, 1), "sigma": round(sg, 1), "pool": pool, "targets": tg}

    # ---- AAGE: pools, corridor, who runs, spike ----------------------------------------------------------------------------------
    def aage(i):
        r = rows[i]
        m = r["c"]
        px = r["cl"]
        D = (r["leg"] or {}).get("d", 0)
        cl = rows[:i + 1]
        lv = levels_f(m)
        sess_lo, sess_hi = min(x["l"] for x in cl), max(x["h"] for x in cl)
        lv += [{"kind": "DIN LOW", "px": sess_lo, "fr": "f", "src": "stops neeche"}, {"kind": "DIN HIGH", "px": sess_hi, "fr": "f", "src": "stops upar"}]
        for e in ev:
            if e["m"] <= m and e["k"] in ("ROKA", "THAKAN", "PHANSE", "KHALI") and e.get("p") and (e.get("broke") is None or e["broke"] > m):
                lv.append({"kind": e["k"], "px": e["p"], "fr": "f", "src": e["chip"]})
        # today's developing profile nodes (5-pt bins over the closed bars) [M]
        bins = {}
        for x in cl:
            for p, v in (x.get("bins") or []):
                bins[p] = bins.get(p, 0) + v
        vals = sorted(bins.values())
        med = vals[len(vals) // 2] if vals else 1
        tops = set(sorted(bins, key=lambda k: -bins[k])[:3])
        for p, v in bins.items():
            if p in tops:
                lv.append({"kind": "HVN", "px": p, "fr": "f", "src": f"{v:,} lot aaj"})
            elif v <= 0.35 * med and abs(p - px) <= 120:
                lv.append({"kind": "LVN", "px": p, "fr": "f", "src": f"{v:,} lot aaj"})
        native(lv)
        above = sorted((l for l in lv if l["px"] > px + 2 and l["kind"] != "LVN"), key=lambda l: l["px"])
        below = sorted((l for l in lv if l["px"] < px - 2 and l["kind"] != "LVN"), key=lambda l: -l["px"])
        lv_all = lv

        def pack(ls):
            out, last = [], None
            for l in ls:
                if last is not None and abs(l["px"] - last) < 8:
                    tag = f"{l['kind']} {l['fr']} {f0(l['px0'])}"
                    if tag not in out[-1]["more"]:
                        out[-1]["more"].append(tag)
                    continue
                out.append({"kind": l["kind"], "name": l.get("name", l["kind"]), "px": round(l["px"], 1), "px0": l["px0"], "fr": l["fr"],
                            "dist": round(l["px"] - px), "src": l.get("src", ""), "more": []})
                last = l["px"]
            return out
        above = sorted(merge_frames(above), key=lambda l: l["px"])
        below = sorted(merge_frames(below), key=lambda l: -l["px"])
        A, Bl = pack(above), pack(below)
        floor = 20.0
        # the wall ahead in the leg's direction, and the corridor past it (to the next shelf, through any LVN)
        corr = None
        ahead = [l for l in (A if D > 0 else Bl) if not l["kind"].startswith("LVN")]
        if D and len(ahead) >= 2:
            wall = ahead[0]
            nxt = next((l for l in ahead[1:] if abs(l["px"] - wall["px"]) >= floor), None)      # a corridor under 20 pts is not one
            if nxt:
                lv_in = [l for l in lv_all if l["kind"] in ("LVN", "pLVN") and (wall["px"] < l["px"] < nxt["px"] if D > 0 else nxt["px"] < l["px"] < wall["px"])]
                corr = {"wall": wall, "to": nxt, "pts": round(abs(nxt["px"] - wall["px"])), "lvn": bool(lv_in), "d": D}
        # who is running (fut OI x price, 15 min)
        who = None
        if i >= 3 and r.get("oi") and rows[i - 3].get("oi"):
            doi, dp = r["oi"] - rows[i - 3]["oi"], r["cl"] - rows[i - 3]["cl"]
            q = ("NAYE SHORT aa rahe" if doi > 0 else "LONGS NIKAL rahe") if dp < 0 else ("NAYE LONG aa rahe" if doi > 0 else "SHORTS BHAAG rahe (SL)")
            who = {"txt": q, "doi": doi, "dp": round(dp, 1), "roll": roll, "g": grade([(rows[j]["oi"] - rows[j - 3]["oi"]) if j >= 3 and rows[j].get("oi") and rows[j - 3].get("oi") else None for j in range(i)], doi)[0]}
        # spike risk: flow heavier / delta rising on the moving side / stacks on the moving side / VPIN toxic / LVN ahead
        sp = []
        sp.append(("flow bhaari", r["g"]["vol"] in ("ASLI", "ZOR")))
        d3 = [abs(x["delta"] or 0) for x in cl[-3:]]
        sp.append(("Δ badh raha", len(d3) == 3 and d3[0] < d3[1] < d3[2] and ((r["delta"] or 0) * D > 0)))
        st = [s for s in (r["stacks"] or []) if isinstance(s, dict) and (s.get("side") or 0) * D > 0]
        sp.append(("stack leg ki taraf", bool(st)))
        v = vpin_at(m)
        sp.append(("VPIN toxic", bool(v and v.get("pct") is not None and v["pct"] >= TOX)))
        sp.append(("LVN aage", bool(corr and corr["lvn"])))
        return {"above": A[:5], "below": Bl[:5], "corr": corr, "who": who, "spike": {"n": sum(1 for _, ok in sp if ok), "N": len(sp), "pieces": sp}}

    # ---- episodes: arm -> check -> fire -> trade -> exit ----------------------------------------------------------------------------
    episodes = []
    for z in F["zone"]:
        S = 1 if z["side"] == "BUY" else -1
        arm_m = mins(z["first_t"])                       # the 3-min bar's END is the minute the arm is known
        ep = {"side": S, "band": z["band"], "arm_m": arm_m, "arm_px": z["arms"][0]["level"], "arms": z["arms"], "until": z.get("until"),
              "check": arm_check(S, arm_m), "before": before(arm_m), "rearms": []}
        for a in z["arms"][1:]:
            ep["rearms"].append({"m": mins(a["t"]), "level": a["level"], "check": arm_check(S, mins(a["t"]))})
        e = z["entry"]
        if e and e["E"] is not None:
            em = mins(e["t"])
            extreme = min(a["extreme"] for a in z["arms"]) if S > 0 else max(a["extreme"] for a in z["arms"])
            ep["entry"] = {"m": em, "E": e["E"], "stop": e["stop"], "extreme": extreme, "check": arm_check(S, em),
                           "plan": plan(S, e["E"], e["stop"], extreme, em)}
        episodes.append(ep)
    episodes.sort(key=lambda x: x["arm_m"])
    # an episode ends at the next entry of either side, at its stop, or at 15:20
    for k, ep in enumerate(episodes):
        if not ep.get("entry"):
            ep["end_m"] = min([x["arm_m"] for x in episodes[k + 1:]] + [HOLD_END, mins(ep["until"]) + 3 if ep.get("until") else HOLD_END])
            ep["exit"] = {"m": ep["end_m"], "px": None, "kind": "EXPIRED", "chip": "ARM KHATAM", "why": "machine's 10-candle window ran out"}
            continue
        E, S, em = ep["entry"]["E"], ep["side"], ep["entry"]["m"]
        stop = ep["entry"]["stop"]
        nxt = min([x["entry"]["m"] for x in episodes[k + 1:] if x.get("entry")] + [HOLD_END])
        trade, exit_, line, mfe, locked = [], None, stop, 0.0, False
        pk_oi_spot = None
        risk = abs(E - stop) or 1.0
        leg_big = 0
        for r in rows:
            if r["c"] <= em:
                continue
            m = r["c"]
            if m > nxt:
                break
            # intrabar: the stop (or the trailed line) traded on the 1-min candles of this bar
            hit = None
            for mm in range(max(r["m"], em), r["m"] + 5):
                o = ones.get(mm)
                if o and ((o["l"] <= line) if S > 0 else (o["h"] >= line)):
                    hit = mm
                    break
            if hit is not None:
                exit_ = {"m": hit, "px": line, "kind": "STOP", "chip": "STOP LAGA" if line == stop else "LINE LAGI", "why": f"{ftos(line, hit)} traded {hm(hit)}"}
                break
            if m >= HOLD_END:
                exit_ = {"m": m, "px": r["cl"], "kind": "TIME", "chip": "15:20 BAND", "why": "hold window band"}
                break
            # reads at this close
            mfe = max(mfe, (r["h"] - E) * S if S > 0 else (E - r["l"]))
            R = (r["cl"] - E) * S / risk
            fr, fk = fronts_at(m)
            dside = "PE" if S > 0 else "CE"
            d1 = next((f for f in (fr or []) if f["side"] == dside), None) if fr and m - fk <= STALE else None
            gave = False
            if d1 and d1["state"] == "UNWINDING":
                pk_spot = last_at(spot1, mins(d1["peak_at"]))
                sg = sigma3(m) or 20
                sp_now = last_at(spot1, m)
                if pk_spot is not None and sp_now is not None and (pk_spot - sp_now) * S >= BUF * sg:
                    gave = True
            if gave:
                exit_ = {"m": m, "px": r["cl"], "kind": "GAVE UP", "chip": f"{dside} {f0(d1['k'])} CHHOD GAYE", "why": f"front unwinding, price losing side (§1m)"}
                trade.append({"m": m, "state": "EXIT", "head": exit_["chip"], "sub": exit_["why"], "R": round(R, 2), "takat": r["takat"], "takat_n": r["takat_n"], "phase": r["phase"]})
                break
            # the trade's own leg: bars since entry in its direction
            since = [x for x in rows if em <= x["c"] <= m]
            same = [abs(x["delta"] or 0) for x in since if (x["delta"] or 0) * S > 0]
            leg_big = max(same) if same else leg_big
            against_d = (r["delta"] or 0) * S < 0
            # decel signs against the trade (FADE-D's family), a COUNT
            dec = []
            ext_new = (r["h"] >= max(x["h"] for x in since)) if S > 0 else (r["l"] <= min(x["l"] for x in since))
            dec.append(("effort", ext_new and leg_big and (r["delta"] or 0) * S >= 0 and abs(r["delta"] or 0) <= FADE_FRAC * leg_big))
            dec.append(("Δ ulta", against_d and r["g"]["delta"] in ("ASLI", "ZOR")))
            cv = [x["cvd"] for x in since]
            dec.append(("CVD peak se neeche", (r["cvd"] < max(cv) - 0.25 * (max(cv) - min(cv) or 1)) if S > 0 else (r["cvd"] > min(cv) + 0.25 * (max(cv) - min(cv) or 1))))
            dec.append(("likh peak se neeche", d1 is not None and d1["state"] != "BUILDING"))
            nd = sum(1 for _, ok in dec if ok)
            big_against = r["big"] and r["big"]["side"] * S < 0 and r["g"]["big"] in ("ASLI", "ZOR")
            # HOLD v2 push trail (port of the idea: a PUSH bar in the trade's direction moves the line to its origin + 0.25U)
            pushed = False
            if (r["delta"] or 0) * S > 0 and r["g"]["delta"] in ("ASLI", "ZOR") and (r["cl"] - r["o"]) * S > 0:
                U = sigma3(m) or 20
                new = r["o"] - BUF * U * S
                if (new - line) * S > 0 and (r["cl"] - new) * S > 0:
                    line, pushed = round(new, 1), True
            if mfe >= 2 * risk and not locked and (E - line) * S > 0:
                line, locked, pushed = E, True, True
            # the phase and the voice
            pulled = r["phase"] == "PULLBACK" and (r["leg"] or {}).get("d") == S
            changed = []
            if big_against:
                changed.append(f"BADA PRINT ulta {r['big']['lots']:,} lot")
            if against_d and leg_big and abs(r["delta"] or 0) > 0.5 * leg_big:
                changed.append(f"Δ ulta {r['delta']:+,} > ½ leg")
            if d1 and d1["state"] == "UNWINDING":
                changed.append(f"{dside} {f0(d1['k'])} chhod rahe (munafa booking)")
            if r["flipped"] and (r["leg"] or {}).get("d") == -S:
                changed.append("PALTA ulta")
            if r["oi_read"] and not roll and {"SL KAT RAHE": 1, "NAYE KHARIDAR": 1}.get(r["oi_read"], -1) != S:
                changed.append(r["oi_read"].lower())
            if pulled:
                if changed:
                    state, head = "SOCHO", "PULLBACK · " + changed[0]
                else:
                    state, head = "HOLD", "PULLBACK · koi badlaav nahi"
            elif changed and nd >= 2:
                state, head = "SOCHO", "THAK RAHA · " + changed[0]
            elif r["takat"] >= 3:
                state, head = "HOLD", "ZOR BADH RAHA"
            elif r["takat"] >= 2:
                state, head = "HOLD", "CHAL RAHA"
            elif nd >= 2:
                state, head = "SOCHO", "THAK RAHA"
            else:
                state, head = "HOLD", "RUK RAHA"
            if pushed and state == "HOLD":
                state, head = "TIGHTEN", ("LOCK · breakeven" if locked and line == E else f"LINE UPAR {ftos(line, m)}" if S > 0 else f"LINE NEECHE {ftos(line, m)}")
            sub = f"takat {r['takat']}/{r['takat_n']} · thak {nd}/4 · Δ {r['delta']:+,} · OI {r['doi'] / 1000:+,.0f}k" if r.get("doi") is not None else f"takat {r['takat']}/{r['takat_n']} · thak {nd}/4 · Δ {r['delta']:+,}"
            if lead_at(m) is not None:
                sub += f" · lead {lead_at(m):+.0f}"
            t_hit = [t["name"] for t in ep["entry"]["plan"]["targets"] if (r["h"] >= t["px"] if S > 0 else r["l"] <= t["px"])]
            trade.append({"m": m, "state": state, "head": head, "sub": sub, "R": round(R, 2), "takat": r["takat"], "takat_n": r["takat_n"],
                          "phase": r["phase"], "dec": [k for k, ok in dec if ok], "line": line, "t_hit": t_hit, "mfe_R": round(mfe / risk, 2)})
        if exit_ is None:
            exit_ = {"m": nxt, "px": None, "kind": "NEXT", "chip": "NAYA SETUP", "why": "next zone entry replaced it"}
        if exit_["kind"] == "NEXT":
            nx = next((x for x in episodes[k + 1:] if x.get("entry") and x["entry"]["m"] == nxt), None)
            if nx and nx["side"] != S:
                exit_["chip"], exit_["why"] = "ULTA ZONE ENTRY", f"zone {'SELL' if S > 0 else 'BUY'} fired {hm(nxt)}"
        ep["trade"], ep["exit"], ep["end_m"] = trade, exit_, exit_["m"]
    rec_from = min(spot1) if spot1 else None
    for ep in episodes:
        cs = {r["c"] for r in rows if ep["arm_m"] < r["c"] <= ep.get("end_m", HOLD_END)}
        if ep.get("entry"):
            cs.add(ep["entry"]["m"])
        ep["checks"] = [{"m": c, **arm_check(ep["side"], c)} for c in sorted(cs)]
        ep["rec_from"] = rec_from
    # the per-close AAGE map; in a trade the corridor floor is max(half the risk, 20 pts)
    for r in rows:
        r["aage"] = aage(r["i"])
        ep = next((e for e in episodes if e.get("entry") and e["entry"]["m"] <= r["c"] <= e["end_m"]), None)
        a = r["aage"]
        if ep and a.get("corr") and a["corr"]["pts"] < max(0.5 * ep["entry"]["plan"]["risk"], 20):
            a["corr"] = None
    # the state of the screen at every minute: FLAT / ARMED / IN TRADE / DONE
    jumps = []
    for ep in episodes:
        jumps.append([ep["arm_m"], f"{hm(ep['arm_m'])} ARM {'BUY' if ep['side'] > 0 else 'SELL'} {ep['check']['n']}/{ep['check']['N']}"])
        if ep.get("entry"):
            jumps.append([ep["entry"]["m"], f"{hm(ep['entry']['m'])} FIRE {'BUY' if ep['side'] > 0 else 'SELL'}"])
            held = [t for t in ep["trade"] if t["head"].startswith("PULLBACK · koi")]
            if held:
                jumps.append([held[0]["m"], f"{hm(held[0]['m'])} pullback hold"])
            so = [t for t in ep["trade"] if t["state"] == "SOCHO"]
            if so:
                jumps.append([so[0]["m"], f"{hm(so[0]['m'])} socho"])
            if ep["exit"] and ep["exit"]["kind"] != "NEXT":
                jumps.append([ep["exit"]["m"], f"{hm(ep['exit']['m'])} {ep['exit']['chip'].lower()}"])
    jumps.sort()
    # strip bins from rows (the face does not need them after aage)
    for r in rows:
        r.pop("bins", None)
        r.pop("votes", None)
    dt = date.fromisoformat(day)
    lead1 = {m: lead_at(m) for m in range(OPEN_M, CLOSE_M + 1)}
    basis1 = {m: basis_at(m) for m in range(OPEN_M, CLOSE_M + 1)}
    return {"day": day, "label": dt.strftime("%d %b · %a"), "roll": roll, "expiry": F.get("expiry"), "rows": rows, "ev": ev, "eps": episodes,
            "ones": F["ones"], "flow1": {str(k): v for k, v in flow1.items()}, "spot1": {str(k): v for k, v in spot1.items()},
            "lead1": {str(k): v for k, v in lead1.items() if v is not None}, "basis1": {str(k): v for k, v in basis1.items() if v is not None},
            "vpin": vp, "bands3": [{k: b.get(k) for k in ("t", "vwap", "u1", "u2", "u3", "d1", "d2", "d3")} for b in bars3],
            "levels": LV, "levels_why": F["levels_why"], "xi": [{"t": x["t"], "at": x["at"], "sync": (x.get("sync") or {}).get("key"),
                                                                 "ext": ((x.get("ext") or {}).get("verdict")), "idx": {i: v.get("D") for i, v in (x.get("idx") or {}).items()}} for x in xi],
            "onesided": F["onesided"], "jumps": jumps[:14], "peers": {p: [{k: b.get(k) for k in ("m", "c", "delta", "oi")} for b in F["peers5"][p]] for p in ("BANKNIFTY", "SENSEX")},
            "peer_lead": {p: {str(k): v["lead"] for k, v in F["writers"][p].items() if v.get("lead") is not None} for p in ("BANKNIFTY", "SENSEX")},
            "fronts": {str(k): v for k, v in FR.items()}, "legs": legs_r, "prev_tape": F.get("prev_tape"), "rec_from": rec_from}


out = {}
for day in DAYS:
    F = json.load(open(os.path.join(HERE, f"facts_{day}.json"), encoding="utf-8"))
    x = build(F)
    out[day] = x
    from collections import Counter
    c = Counter(e["k"] for e in x["ev"])
    lo, hi = min(r["l"] for r in x["rows"]), max(r["h"] for r in x["rows"])
    print(day, f"range {lo:,.0f}-{hi:,.0f} ({hi - lo:.0f})", "events", len(x["ev"]), dict(c))
    for ep in x["eps"]:
        e = ep.get("entry")
        print("  ", "BUY " if ep["side"] > 0 else "SELL", "arm", hm(ep["arm_m"]), f"{ep['check']['n']}/{ep['check']['N']} ({ep['check']['against']} khilaaf)",
              "| entry", (hm(e["m"]), e["E"], "stop", e["stop"], "pool", (e["plan"]["pool"] or {}).get("why"), "T", [(t["kind"], t["px"]) for t in e["plan"]["targets"]]) if e else "-",
              "| exit", (hm(ep["exit"]["m"]), ep["exit"]["chip"]) if ep.get("exit") else "-", "| trade", [t["state"][0] for t in ep.get("trade", [])])
    print("   jumps", [j[1] for j in x["jumps"]])
tpl = open(os.path.join(HERE, "dream.tpl.html"), encoding="utf-8").read()
html = tpl.replace("/*DATA*/", json.dumps(out, ensure_ascii=False, separators=(",", ":")))
open(os.path.join(HERE, "dream.html"), "w", encoding="utf-8", newline="\n").write(html)
print(len(html) // 1024, "KB written")
