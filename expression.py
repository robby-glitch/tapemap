"""expression.py -- THE EXPRESSION: BUY THE OPTION, OR SELL THE OTHER SIDE, and THE WRITER'S GO / WAIT / NO.

THE SPEC is docs/hold/EXPRESSION-PREREG.md rev e (sha256 45d8d369...fc1e, anchored in
context/research-findings.md §1h), signed by the operator 2026-09-26 20:48. Built here: §A (the read at each
3-minute close: five facts, each leg's refusals R1-R6, the word and its grading), §B (the writer's four facts and
word, amending VALIDATE rev 2 for writers only; the buyer's word is validate.py, untouched) and §B.3 / §E.2's
outcomes. §C changes nothing: the window is hold.py as it stands.

PORTED, NOT REINVENTED: the disclosure code that produced §D (docs/hold/scratch-2026-09-25/expr/: expr.py's
straddle15 / straddle / leg_read, expr_a.expression_a and r_mults, expr_c.grade, expr_d's ATM sale and writer
word, expr_e's wall gate). test_expression.py reproduces §D's rows from THIS file on the frozen fixtures.

INPUT `D`, one index-day as the fixtures and the server both give it:
    {idx, step, minutes (hold.py's records, each with `fr` = the §1d top two per side), pivots,
     px(k, side, i) -> the chain record's minute close or None,
     gk(k, side, i) -> (delta, gamma) the broker's [M] or None, late (rev 5 §A.0.4) or None}

Pure: no I/O, no clock. It gates nothing, and there is no order path. Never a size, never odds.
"""
from __future__ import annotations

import hold
import trendbox
import validate

CC, NONE, NOT_SHOWN = hold.CC, hold.NONE, hold.NOT_SHOWN
PREREG = "expr-e"
REV_W = "2W"              # §E.3: a writer press row
QUIET = hold.QUIET        # §A.3 fact 5: the straddle fixed at t - 15 (fronts.SLOPE_MARKS)
HORIZON = validate.HORIZON  # §B.3 / §E.2: 30 finished minutes, judged
FIRST_UNIT = "09:44"      # §E.2: the 10th close, then every 10th
AFTER = "15:00"           # §E.3: after_1500, descriptive only
NAMES = ("SPEED", "ROOM", "WALL", "REGIME", "PREMIUM")
W_NAMES = ("Right now", "Your wall", "Cushion", "Time is paying")
TAG = {"SPEED": "M on I", "ROOM": "M", "WALL": "M", "REGIME": "I", "PREMIUM": "M"}
DRAFT = ("DRAFT — pre-registered 2026-09-26 (docs/hold/EXPRESSION-PREREG.md rev e, signed 20:48), untested; "
         "each word stays DRAFT until §E.2 judges it on forward rows")
NOT_SHOWN_LINES = [NOT_SHOWN + "a size", NOT_SHOWN + "an order", NOT_SHOWN + "odds: the count is a count"]
S4_ROW = "S4 expiry flush — logged, not traded · expiry afternoon → neither (the desk's setup table)"
R_TEXT = {"R1": "the short leg's entry check reads FOLD",
          "R2": "your side is leaving under a squeeze — never sell into a squeeze",
          "R3": "OI is blind — a writer does not sell a wall she cannot see",
          "R4": "the straddle is being bid on both legs — never sell into a bid straddle",
          "R4cnc": "could not check",
          "R5": "you would enter a broken setup",
          "R6": "no wall behind the sale"}
R_ORDER = ("R1", "R2", "R3", "R4", "R4cnc", "R5", "R6")
mm, hm = hold.mm, hold.hm


def after_1500(t):
    """§E.3: true at 15:00 or later. Descriptive only: no word, fact, refusal, fold or falsifier reads it."""
    return t >= AFTER


def is_unit(t):
    """§E.2's units: the closes at 09:44, 10:14 … 15:14."""
    return hold.is_close(t) and t >= FIRST_UNIT and (mm(t) - mm(FIRST_UNIT)) % HORIZON == 0


def _spot(m):
    """Spot: the chain mark's (server._hold_tick's side log reads it for atm.k); the index close when a mark has none."""
    return m.get("spot") if m.get("spot") is not None else (m.get("ix") or [None])[0]


def leg_spot(m):
    """The spot the legs' ATM strike (§A.5, "spot rounded to the step; the side log's atm.k") and the wall behind the
    sale (§A.3 fact 3, "at or beyond spot") are read against: the chain mark's, as the text names it. The §D
    disclosure read the index close here (and the chain spot for fact 5); test_expression proves both readings."""
    return _spot(m)


def atm(m, step, s=None):
    """The ATM strike: spot rounded to the step."""
    s = _spot(m) if s is None else s
    return None if s is None or not step else round(s / step) * step


# ---------------------------------------------------------------- the straddles (§A.3 fact 5, §A.4 R4)
def straddle15(D, i):
    """§A.3 fact 5: the straddle of the strike ATM at t - 15, CE + PE at t against at t - 15 -- one contract,
    never re-centred. -> (read | None, why)."""
    mins = D["minutes"]
    if i < QUIET:
        return None, CC + f"the fixed straddle needs t − {QUIET} (from 09:30)"
    m0 = mins[i - QUIET]
    K = atm(m0, D["step"])
    if K is None:
        return None, CC + f"no spot at {m0['t']}"
    px = D["px"]
    ce0, pe0, ce1, pe1 = px(K, "CE", i - QUIET), px(K, "PE", i - QUIET), px(K, "CE", i), px(K, "PE", i)
    if None in (ce0, pe0, ce1, pe1):
        return None, CC + f"a premium of the {K:,.0f} straddle is missing at {m0['t']} or {mins[i]['t']}"
    a, b = round(ce0 + pe0, 2), round(ce1 + pe1, 2)
    st = "both rose" if ce1 > ce0 and pe1 > pe0 else "rose" if b > a else "fell" if b < a else "flat"
    return {"state": st, "K": K, "from": a, "to": b, "t0": m0["t"]}, None


def straddle(D, i):
    """S: the ATM straddle at t of the chain's resolved expiry (§A.4 R4, §A.5). -> (pts | None, K)."""
    K = atm(D["minutes"][i], D["step"])
    if K is None:
        return None, None
    ce, pe = D["px"](K, "CE", i), D["px"](K, "PE", i)
    return (None if ce is None or pe is None else round(ce + pe, 2)), K


def wall_behind(fr, side, spot, step):
    """§A.3 fact 3 = §B.1 fact 2: the nearest to spot of `side`'s §1d top two at or beyond spot on its
    out-of-the-money side ("at" = within half a step). None: no such wall."""
    beyond = (lambda k: k <= spot + step / 2) if side == "PE" else (lambda k: k >= spot - step / 2)
    c = [f for f in fr or [] if f["side"] == side and beyond(f["k"])]
    return min(c, key=lambda f: abs(f["k"] - spot)) if c else None


def _not_building(side, wall):
    """A wall behind the sale that is not BUILDING with a build today: a read, said as what it is."""
    return (f"{side} {wall['k']:,.0f} building, but with no build today — not counted" if wall["state"] == hold.BLD else
            f"{side} {wall['k']:,.0f} {wall['state'].lower()} — not building")


def leg(D, i, side, role, k):
    """One leg's window read at close i, entered at i (the entry check with the latch removed is rows[0])."""
    m = D["minutes"][i]
    tr = {"side": side, "role": role, "t0": hm(mm(m["t"]) + 1), "k": k, "p0": None, "qty": 1}
    return hold.read(tr, D["minutes"], D["pivots"], upto=m["t"], idx=D.get("idx"), late=D.get("late"))


def _fact(name, state, text, absence=None):
    return [name, state, absence, text]


def _move(D, i, j, d):
    a, b = (D["minutes"][i].get("ix") or [None])[0], (D["minutes"][j].get("ix") or [None])[0]
    if a is None or b is None:
        return None
    return round((b - a) * d, 1)


# ---------------------------------------------------------------- §A.4 the word
def grade(nb, ns, ref_b, ref_s, bs, ss):
    """§A.4 (rev b's margin, rev c's refused tie). -> (word, named_by, lead, strength)."""
    if ref_b and ref_s:
        return "STAND ASIDE · both refused", "refusal", None, None
    if ref_s:                                   # only SELL refused
        lead = nb - ns
        if lead >= 2:
            return f"BUY {bs} · selling refused", "refusal", lead, "lead"
        if lead >= 0:                           # a one-fact lead, or the tie (rev c): LEANS, by refusal
            return f"LEANS BUY {bs} · selling refused", "refusal", lead, "leans"
        return "STAND ASIDE · led", "refusal", lead, None
    if ref_b:                                   # only BUY refused: mirrored
        lead = ns - nb
        if lead >= 2:
            return f"SELL {ss} · buying refused", "refusal", lead, "lead"
        if lead >= 0:
            return f"LEANS SELL {ss} · buying refused", "refusal", lead, "leans"
        return "STAND ASIDE · led", "refusal", lead, None
    lead = nb - ns                              # neither refused: on the count
    if lead >= 2:
        return f"BUY {bs}", "count", lead, "lead"
    if lead == 1:
        return f"LEANS BUY {bs}", "count", 1, "leans"
    if lead <= -2:
        return f"SELL {ss}", "count", -lead, "lead"
    if lead == -1:
        return f"LEANS SELL {ss}", "count", 1, "leans"
    return "EITHER", "count", 0, "tie"


def base(word):
    """The word in large type: BUY / LEANS BUY / EITHER / LEANS SELL / SELL / STAND ASIDE / could not check."""
    if not word:
        return "could not check"
    if word.startswith("STAND"):
        return "STAND ASIDE"
    for p in ("LEANS BUY", "LEANS SELL", "BUY", "SELL"):
        if word.startswith(p):
            return p
    return word


# ---------------------------------------------------------------- §A THE EXPRESSION READ
def read(D, i, d):
    """§A at close i for direction d (+1 UP, -1 DOWN). -> the read; `word` None = could not check."""
    mins, step = D["minutes"], D["step"]
    m = mins[i]
    t = m["t"]
    x = m.get("ix")
    bs, ss = ("CE", "PE") if d > 0 else ("PE", "CE")
    out = {"t": t, "d": d, "word": None, "named_by": None, "lead": None, "strength": None, "refusal": [],
           "unit": is_unit(t), "after_1500": after_1500(t)}
    if not x:                                   # §A.4 step 1: the line cannot be set at the close
        return {**out, "why": CC + f"no {D.get('idx') or 'index'} candle for {t}; the line can't be set"}
    spot = leg_spot(m)
    k = atm(m, step, spot)
    L = leg(D, i, bs, "long", k)
    if not L.get("ok"):
        return {**out, "why": L.get("why")}
    lr = L["rows"][0]
    if lr["line"].get("blind"):
        return {**out, "why": lr["line"]["blind"]}
    facts, ref_b, ref_s, why = [], [], [], {}
    oi_blind = m.get("blind")
    # 1 SPEED -- the window's "paid" at t (VALIDATE rev 2 §1.4, read for the long leg)
    P, H = lr["payers"], lr["holders"]
    if P["state"] == "blind" and H["state"] == "blind":
        facts.append(_fact("SPEED", "neither", CC + "OI " + (hold._strip(oi_blind) or "not read"), "blind"))
    elif lr["clock"].get("paid_last") == t:
        # name what actually paid: "flow with you" was printed at 09:38 on 2026-09-28 when the pay was the
        # payers' fold and flow read against (trader audit, bug 6)
        what = (hold._lc(P["fact"]) if P["state"] == "for" else
                f"the payers' fold of {P['fold_t']}" if P.get("fold_t") else
                "flow with you" if lr["flow"]["state"] == "with" else hold._lc(P["fact"]))
        facts.append(_fact("SPEED", "buy", f"paid at {t}: {what} — a forced move is a fast move, and speed beats the rent"))
    else:
        facts.append(_fact("SPEED", "neither", NONE + f"nothing paying at {t}", "none"))
    # 2 ROOM -- VALIDATE rev 2 §1.3's own order, the line against its noise, then the target
    g = validate.geometry(mins, i, d, lr["line"], D.get("late"))
    tg = g["target"]
    if g["line"] is None or g["noise"] is None:
        facts.append(_fact("ROOM", "neither", CC + ("the line could not be set" if g["line"] is None
                                                     else f"{g['n']} of {QUIET} candles for the noise"), "blind"))
    elif g["line"] <= g["noise"]:
        facts.append(_fact("ROOM", "neither", f"your line is {g['line']} pts away, inside one candle's range "
                                              f"({hold._pts(g['noise'])} pts [M]) — the reward comparison is not read"))
    elif tg.get("blind"):
        facts.append(_fact("ROOM", "neither", tg["blind"], "blind"))
    elif tg["src"] == "none" or tg["pts"] >= g["line"]:
        facts.append(_fact("ROOM", "buy", "room to run — " + (
            f"no wall in the way (price discovery); your line is {g['line']} pts away" if tg["src"] == "none" else
            f"{validate._target_name(tg)} is {tg['pts']} pts away, your line {g['line']}")))
    else:
        facts.append(_fact("ROOM", "sell", f"the move is capped at {tg['k']:,.1f}, {tg['pts']} pts away, nearer than "
                                           f"your line at {g['line']}; a buyer's reward is shorter than her risk, and a "
                                           "writer does not need the move"))
    # 3 WALL -- the wall behind the sale (rev d); a wall is where writers are adding, not a bound on price
    wall = wall_behind(m.get("fr"), ss, spot, step) if spot is not None else None
    if oi_blind:
        facts.append(_fact("WALL", "neither", CC + "OI " + hold._strip(oi_blind), "blind"))
        ref_s.append("R3")
        why["R3"] = CC + "OI " + hold._strip(oi_blind)
    elif wall is None:
        facts.append(_fact("WALL", "neither", NONE + f"no {ss} wall at or beyond spot among the top two", "none"))
        ref_s.append("R6")
        why["R6"] = f"the {ss} wall is already behind price"
    elif wall["state"] == hold.BLD and wall["built"]:
        facts.append(_fact("WALL", "sell", f"{ss} {wall['k']:,.0f} building, with a build today — writers are adding "
                                           "behind the sale"))
    else:
        facts.append(_fact("WALL", "neither", _not_building(ss, wall)))
    # 4 REGIME -- rev 4 §10.1's side vote on the 5m / 15m / 1h rows, price-led
    sd, swhy = hold.side_of(m)
    mine = "CALLS" if d > 0 else "PUTS"
    facts.append(_fact("REGIME", "neither", CC + (hold._strip(swhy) or "the rows"), "blind") if sd is None else
                 _fact("REGIME", "buy", f"{swhy} — {sd}: a trend pays a buyer's gamma; a writer's best case is the "
                                        "premium she sold") if sd == mine else
                 _fact("REGIME", "sell", f"{swhy}: the rows read range; time pays a writer while a buyer pays rent "
                                         "waiting") if sd == "no side" else
                 _fact("REGIME", "neither", f"{swhy} — {sd}: the rows trend against your direction"))
    # 5 PREMIUM -- whose rent won over the last 15 minutes, on one fixed straddle; unreadable fails closed (R4)
    sq, sqwhy = straddle15(D, i)
    if sq is None:
        facts.append(_fact("PREMIUM", "neither", sqwhy, "blind"))
        ref_s.append("R4cnc")
        why["R4cnc"] = sqwhy
    else:
        mv = _move(D, i - QUIET, i, d)
        mvt = ("could not check the index's move" if mv is None else
               f"the index moved {abs(mv)} pts {'with' if mv > 0 else 'against' if mv < 0 else 'neither with nor against'} "
               "your direction [M]")
        x_ = round(abs(sq["to"] - sq["from"]), 2)
        if sq["state"] == "both rose":
            facts.append(_fact("PREMIUM", "neither", f"both legs of the {sq['K']:,.0f} straddle rose since {sq['t0']} "
                                                     f"({sq['from']} → {sq['to']}) — the straddle is being bid"))
            ref_s.append("R4")
            why["R4"] = f"both legs of the {sq['K']:,.0f} straddle rose since {sq['t0']}"
        elif sq["state"] == "rose":
            facts.append(_fact("PREMIUM", "buy", f"a straddle bought at {sq['t0']} is up {x_} pts [M]: the move paid "
                                                 f"more than time took — {mvt}"))
        elif sq["state"] == "fell":
            facts.append(_fact("PREMIUM", "sell", f"a straddle sold at {sq['t0']} is up {x_} pts [M]: time took more "
                                                  f"than the move paid — {mvt}"))
        else:
            facts.append(_fact("PREMIUM", "neither", f"the {sq['K']:,.0f} straddle is unchanged since {sq['t0']}"))
    S, _SK = straddle(D, i)
    if S is None and "R4cnc" not in ref_s:      # rev d: the sale is one leg of the ATM pair at t
        ref_s.append("R4cnc")
        why["R4cnc"] = CC + f"the ATM straddle at {t} cannot be read"
    # the legs' own entry checks and the squeeze (R1, R2 on the short leg at the ATM strike; R5 on the long)
    Sr = leg(D, i, ss, "short", k)
    sr = Sr["rows"][0] if Sr.get("ok") else None
    if lr["unlatched"] == "FOLD":
        ref_b.append("R5")
        why["R5"] = f"the long leg's entry check reads FOLD (rule {lr['fold_rule'] or L['entry'].get('fold_rule')})"
    if sr and sr["unlatched"] == "FOLD":
        ref_s.append("R1")
        why["R1"] = f"the short leg's entry check reads FOLD (rule {Sr['entry'].get('fold_rule')})"
    if sr and sr["holders"]["state"] == "against":
        ref_s.append("R2")
        why["R2"] = "your side is leaving under a squeeze (held 3 min)"
    nb = sum(1 for f in facts if f[1] == "buy")
    ns = sum(1 for f in facts if f[1] == "sell")
    w, named, lead, strength = grade(nb, ns, ref_b, ref_s, bs, ss)
    codes = sorted(ref_b + ref_s, key=R_ORDER.index)
    gk = D.get("gk") or (lambda *a: None)
    return {**out, "word": w, "named_by": named, "lead": lead, "strength": strength, "refusal": codes,
            "ref_b": ref_b, "ref_s": ref_s, "why_ref": {c: why.get(c) for c in codes},
            "nb": nb, "ns": ns, "nn": 5 - nb - ns, "facts": facts,
            "count": f"{nb} for buy · {ns} for sell · {5 - nb - ns} neither — of 5, a count, not odds",
            "buy": {"side": bs, "k": k, "px": D["px"](k, bs, i), "greeks": gk(k, bs, i), "entry": lr["unlatched"]},
            "sell": {"side": ss, "k": k, "px": D["px"](k, ss, i), "greeks": gk(k, ss, i),
                     "entry": sr["unlatched"] if sr else None,
                     "wall": {"k": wall["k"], "state": wall["state"]} if wall and not oi_blind else None},
            "S": S, "spot": spot, "L": g["L"], "line": g["line"], "noise": g["noise"],
            "sq": sq, "_short": Sr, "_long": L}


def since(series, j):
    """§A.2: 'since HH:MM · was {word} until HH:MM' over a day's closes (a list of reads, oldest first) at j."""
    lab = lambda e: e.get("word") or "could not check"
    s, was = series[j]["t"], None
    for a in range(j - 1, -1, -1):
        if lab(series[a]) == lab(series[j]):
            s = series[a]["t"]
        else:
            was = {"word": lab(series[a]), "until": s}
            break
    return s, was


# ---------------------------------------------------------------- §B THE WRITER'S GO / WAIT / NO
def writer(D, i, d, side, k, Sr=None, P=None):
    """§B at minute i for a sale of `side` at strike k with danger direction d (a short PE is d = +1).
    `Sr`: that short leg's read at i, if already made. `P`: the premium collected; the chain's minute close
    at i by default. -> {word, facts, ...}; word None when the short leg cannot be read."""
    mins, step = D["minutes"], D["step"]
    m = mins[i]
    t = m["t"]
    Sr = Sr or leg(D, i, side, "short", k)
    if not Sr.get("ok") or k is None:
        return {"word": None, "why": Sr.get("why") or CC + "no strike", "rev": REV_W}
    r = Sr["rows"][0]
    rn = r["unlatched"]
    facts, cnc = [], []
    ent = (Sr["entry"].get("text") or "").split(" — ", 1)[-1].rstrip(".")
    facts.append(["Right now", "for" if rn == "HOLD" else "against" if rn == "FOLD" else "neither",
                  None if rn in ("HOLD", "FOLD", "WATCH") else "blind",
                  (f"you would enter into HOLD — {ent}" if rn == "HOLD" else
                   f"you would enter a broken setup — {ent}" if rn == "FOLD" else
                   f"you would enter into {rn} — {ent}")])
    spot = leg_spot(m) if m.get("ix") else None
    wall = wall_behind(m.get("fr"), side, spot, step) if spot is not None else None
    if m.get("blind"):
        facts.append(["Your wall", "neither", "blind", CC + "OI " + hold._strip(m["blind"])])
        cnc.append("Your wall")
    elif wall is None:
        facts.append(["Your wall", "neither", "none", NONE + f"no {side} wall at or beyond spot among the top two (R6)"])
    elif wall["state"] == hold.BLD and wall["built"]:
        facts.append(["Your wall", "for", None, f"{side} {wall['k']:,.0f} building, with a build today — writers are "
                                                "adding behind your sale [M]"])
    else:
        facts.append(["Your wall", "neither", None, _not_building(side, wall) + " [M]"])
    g = validate.geometry(mins, i, d, r["line"], D.get("late"))
    c0 = D["px"](k, side, i) if P is None else P
    gk = (D.get("gk") or (lambda *a: None))(k, side, i)
    otm = None if spot is None else ((k - spot) if side == "CE" else (spot - k))
    beyond = bool(g["line"] is not None and otm is not None and g["line"] >= otm)
    X = None
    if g["line"] is None or g["noise"] is None:
        facts.append(["Cushion", "neither", "blind", CC + ("the line could not be set" if g["line"] is None
                                                           else f"{g['n']} of {QUIET} candles for the noise")])
        cnc.append("Cushion")
    elif g["line"] <= g["noise"]:
        facts.append(["Cushion", "against", None, f"your danger line is {g['line']} pts away — inside one candle's "
                                                  f"range ({hold._pts(g['noise'])} pts [M])"])
    elif gk is None or c0 is None:
        facts.append(["Cushion", "neither", "blind", CC + ("no greeks for your strike and expiry" if gk is None
                                                           else "no premium for your strike")])
        cnc.append("Cushion")
    else:
        X = abs(gk[0]) * g["line"] + 0.5 * gk[1] * g["line"] ** 2       # PLAN §2.1's writer formula
        flag = (" [I] — your line lies beyond your strike, where this second-order estimate is least trustworthy "
                "(PLAN §7)") if beyond else " [I]"
        facts.append(["Cushion", "against" if X > c0 else "for", None,
                      f"your line is worth {X:,.2f} of premium{flag}; you collect {c0:,.2f} [M]"
                      + ("" if X > c0 else f"; your danger line is {g['line']} pts away, outside one candle")])
    sq, sqwhy = straddle15(D, i)
    if sq is None:
        facts.append(["Time is paying", "neither", "blind", sqwhy])
        cnc.append("Time is paying")
    elif sq["state"] == "fell":
        facts.append(["Time is paying", "for", None, f"the {sq['K']:,.0f} straddle fell since {sq['t0']} "
                                                     f"({sq['from']} → {sq['to']}) [M]: time won"])
    elif sq["state"] == "both rose":
        facts.append(["Time is paying", "against", None, f"both legs of the {sq['K']:,.0f} straddle rose since "
                                                         f"{sq['t0']} [M]: the straddle is being bid"])
    else:
        facts.append(["Time is paying", "neither", None,
                      f"the move out-paid time for 15 minutes ({sq['from']} → {sq['to']}) [M]: selling pays only if it "
                      "stops" if sq["state"] == "rose" else f"the {sq['K']:,.0f} straddle is unchanged since {sq['t0']}"])
    st = [f[1] for f in facts]
    na, nn, nf = st.count("against"), st.count("neither"), st.count("for")
    if st[0] == "against":
        word = "NO"
    elif st[0] == "for" and na == 0 and nn <= 1 and not cnc and wall is not None:
        word = "GO"                              # rev d: no could-not-check; rev e: a wall behind the sale
    else:
        word = "WAIT"
    needs = ([f"could not check {c}" for c in cnc] + (["no wall behind the sale (R6)"] if wall is None and not m.get("blind") else [])
             + [f[0] for f in facts if f[1] == "against" and f[0] != "Right now"]
             + [f[0] for f in facts if f[1] == "neither" and f[2] != "blind" and f[0] != "Your wall"])
    stratum = bool(X is not None and g["line"] and g["noise"] and g["line"] > g["noise"] and c0 >= X)
    return {"word": word, "rev": REV_W, "facts": facts, "cnc": cnc, "no_wall": wall is None and not m.get("blind"),
            "wall": {"k": wall["k"], "state": wall["state"]} if wall else None,
            "count": f"{nf} with · {na} against · {nn} neither — of 4, a count, not odds",
            "n_for": nf, "n_against": na, "n_neither": nn, "needs": needs,
            "sentence": ("Right now reads FOLD for this sale." if word == "NO" else
                         f"Nothing is against the sale; {nf} of 4 line up." if word == "GO" else
                         "Not there yet: " + "; ".join(needs) + "." if needs else "Not there yet."),
            "X": None if X is None else round(X, 2), "P": c0, "greeks": gk, "line": g["line"], "noise": g["noise"],
            "L": g["L"], "otm": None if otm is None else round(otm, 1), "beyond_strike": beyond, "stratum": stratum,
            "k": k, "side": side, "t": t, "entry": rn}


def writer_outcome(D, i, d, k, side, w, end):
    """§B.3: premium falls to P − X (the chain's minute close) before the index's 1-min high (short CE) / low
    (short PE) reaches the static L, over the finished minutes to `end` (HH:MM). -> 'target' | 'stop' |
    'same minute' | 'neither' | 'not scored — why'; None while the window has not finished and nothing resolved."""
    mins = D["minutes"]
    if w.get("X") is None or w.get("L") is None or w.get("P") is None:
        why = ("the line not set" if w.get("L") is None else
               "the line inside one candle" if (w.get("line") is not None and w.get("noise") is not None
                                                and w["line"] <= w["noise"]) else "no greeks")
        return "not scored — " + why
    tgt, L, e = w["P"] - w["X"], w["L"], mm(end)
    for j in range(i + 1, len(mins)):
        mj = mins[j]
        if mm(mj["t"]) > e:
            return "neither"
        xx = mj.get("ix")
        cj = D["px"](k, side, j)
        hs = xx is not None and ((xx[1] >= L) if d < 0 else (xx[2] <= L))
        ht = cj is not None and cj <= tgt
        if hs or ht:
            return "same minute" if hs and ht else "stop" if hs else "target"
    return "neither" if mins and mm(mins[-1]["t"]) >= e else None


# ---------------------------------------------------------------- §E.2 the outcome, R-multiples on the shared line
def risk_to_L(D, i, k, side, role, R):
    """PLAN §2.1's two formulas with the broker's Δ, Γ: a buyer |Δ|R − ½ΓR² clamped to [0, premium], a writer
    |Δ|R + ½ΓR² (flagged, never refused, when the line lies beyond the strike). -> (risk | None, why)."""
    g = (D.get("gk") or (lambda *a: None))(k, side, i)
    p = D["px"](k, side, i)
    if g is None or p is None or R is None:
        return None, "no greeks"
    dl, gm = abs(g[0]), g[1]
    if role == "long":
        r = max(0.0, min(p, dl * R - 0.5 * gm * R * R))
        return (r, None) if r > 0 else (None, "the buyer's clamp at 0")
    return dl * R + 0.5 * gm * R * R, None


def r_mults(D, i, d, e, n=HORIZON):
    """§E.2 at unit i: each leg's P&L over the next n finished minutes / its premium at risk to L; G = long R −
    short R; the index's move against d; each leg's % of its own premium, MFE and MAE (points)."""
    mins = D["minutes"]
    j = min(i + n, len(mins) - 1)
    R = e.get("line")
    out = {}
    for lg, role in (("buy", "long"), ("sell", "short")):
        k, side = e[lg]["k"], e[lg]["side"]
        p0, p1 = D["px"](k, side, i), D["px"](k, side, j)
        risk, why = risk_to_L(D, i, k, side, role, R)
        if p0 is None or p1 is None or risk is None:
            out[lg] = {"side": side, "k": k, "why": why or "no premium"}
            continue
        sg = 1 if role == "long" else -1
        path = [sg * (q - p0) for q in (D["px"](k, side, x) for x in range(i + 1, j + 1)) if q is not None]
        pnl = sg * (p1 - p0)
        out[lg] = {"side": side, "k": k, "p0": p0, "p30": p1, "pnl": round(pnl, 2), "risk": round(risk, 2),
                   "r_mult": round(pnl / risk, 2), "pct": round(pnl / p0 * 100, 1) if p0 else None,
                   "mfe": round(max(path), 2) if path else None, "mae": round(min(path), 2) if path else None}
    mv = _move(D, i, j, d)
    out["move"] = {"pts": mv, "split": None if mv is None else "with" if mv > 0 else "against" if mv < 0 else "flat"}
    if "r_mult" in out["buy"] and "r_mult" in out["sell"]:
        out["G"] = round(out["buy"]["r_mult"] - out["sell"]["r_mult"], 2)
        S = e.get("S")
        out["G_pts_over_S"] = round((out["buy"]["pnl"] - out["sell"]["pnl"]) / S, 3) if S else None
    return out


# ---------------------------------------------------------------- printed, not counted
def regime_board(rec):
    """§A.3 fact 4 / §A.7: the board's REGIME (price AND OI, both halves), printed, never counted -- trendbox.regime
    on this minute's rows and board.oi_read of the nearer fronts (hold.oi_half), as /api/board reads it."""
    tr = rec.get("tr")
    if not tr:
        return {"word": None, "why": CC + (hold._strip(rec.get("tr_why")) or "no index candle yet")}
    v = {"UP": 1, "DOWN": -1, "RANGE": 0}
    return trendbox.regime({"rows": {k: {"v": v.get(tr.get(k))} for k in hold.ROWS}}, hold.oi_half(rec))


def row(D, e, day, idx, series_j=None, drag=None, expiry_line=None):
    """§E.3's `expr` row for one read (e from read()); `series_j` = (series, j) for since / was."""
    s, was = since(*series_j) if series_j else (e["t"], None)
    m = D["minutes"][hold.SESSION.index(e["t"])]
    gk = lambda lg: e[lg]["greeks"] or (None, None)
    return {"kind": "expr", "day": day, "t": e["t"], "idx": idx, "d": e["d"], "word": e["word"],
            "strength": e["strength"], "lead": e["lead"], "named_by": e["named_by"], "refusal": e["refusal"],
            "since": s, "was": was, "nb": e.get("nb"), "ns": e.get("ns"), "facts": e.get("facts"),
            "buy": e.get("buy") and {**{x: e["buy"][x] for x in ("side", "k", "px", "entry")},
                                     "delta": gk("buy")[0], "gamma": gk("buy")[1], "expiry": (expiry_line or {}).get("text")},
            "sell": e.get("sell") and {**{x: e["sell"][x] for x in ("side", "k", "px", "entry", "wall")},
                                       "delta": gk("sell")[0], "gamma": gk("sell")[1], "expiry": (expiry_line or {}).get("text")},
            "S": e.get("S"), "line": e.get("line"), "noise": e.get("noise"), "regime_board": regime_board(m),
            "drag": drag, "expiry_line": (expiry_line or {}).get("text"),
            "blind": [b for b in (e.get("why"), m.get("blind"), m.get("tr_why")) if b], "word_1m": e["word"],
            "unit": e["unit"], "after_1500": e["after_1500"], "prereg": PREREG, "tag": "I"}


def outcome_row(D, e, w, day, idx, co_timed=()):
    """§E.3's `expr_outcome` row at a unit read `e` (with the grid writer word `w`, §B.3 population ii), or None
    while it is not complete: its 30 finished minutes (to 15:29), and the writer's first passage to 15:29 known."""
    mins, t, d = D["minutes"], e["t"], e["d"]
    i = hold.SESSION.index(t)
    end = hm(min(mm(t) + HORIZON, mm(hold.SESSION[-1])))
    if not mins or mm(mins[-1]["t"]) < mm(end):
        return None
    if not e.get("word"):                       # the read could not check: nothing to score, said so
        why = "not scored — the read could not check: " + hold._strip(e.get("why") or "")
        return {"kind": "expr_outcome", "day": day, "t": t, "idx": idx, "d": d, "word": None, "long": why,
                "short": why, "G": None, "short_window": mm(t) + HORIZON > mm(hold.SESSION[-1]),
                "after_1500": after_1500(t), "co_timed": sorted(co_timed), "writer": None, "prereg": PREREG, "tag": "M"}
    k, side = e["sell"]["k"], e["sell"]["side"]
    f30 = writer_outcome(D, i, d, k, side, w, end) if w and w.get("word") else "not scored — the sale could not be read"
    f1529 = writer_outcome(D, i, d, k, side, w, hold.SESSION[-1]) if w and w.get("word") else f30
    if f30 is None or f1529 is None:
        return None
    r = r_mults(D, i, d, e)
    return {"kind": "expr_outcome", "day": day, "t": t, "idx": idx, "d": d, "word": e["word"],
            "strength": e["strength"], "lead": e["lead"], "named_by": e["named_by"], "refusal": e["refusal"],
            "long": r["buy"], "short": r["sell"] if "r_mult" in r["sell"] else f"not scored — {r['sell']['why']}",
            "G": r.get("G"), "G_pts_over_S": r.get("G_pts_over_S"), "move": r["move"],
            "short_window": mm(t) + HORIZON > mm(hold.SESSION[-1]), "after_1500": after_1500(t),
            "co_timed": sorted(co_timed),
            "writer": {"facts": w and w.get("facts"), "X": w and w.get("X"), "word": w and w.get("word"),
                       "beyond_strike": bool(w and w.get("beyond_strike")), "stratum": bool(w and w.get("stratum")),
                       "first_30": f30, "first_1529": f1529},
            "prereg": PREREG, "tag": "M"}
