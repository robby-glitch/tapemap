"""jarvis.py -- J2, THE JARVIS BRAIN (spec docs/superpowers/specs/2026-10-28-kahani-design.md §14-§17; plan
docs/superpowers/plans/2026-10-29-j2-jarvis-brain.md; inputs and order GAPS-AND-LIVE-CHECKLIST.md §3-§5).

`build(day, idx, upto)` -> the whole Jarvis frame for one index at one minute, from the record only (no network, no
clock, nothing written). Causal: it reads minutes < upto only (a minute m is complete at m + 1); upto None = the whole
session. One brain: the face (jarvis2.html) and the evening replay (export_mockup.py) render this dict, never their own.

Task 1 MOVED export_mockup.py's body here, rules unchanged (ROUND1-ANSWERS: handshake-2 hold, partial-minute hole,
publish clock, lots from start-5, direction stamp + re-stamp, PHANSE / KHISAK / WAPSI, PALAT two forms, context (b) until
the fight ends, FUEL (a) 30-min memory). Its sources, no REST and no HTTP:
  fut bars  Dext 0.8.1's 1-minute OHLC + OI where it has the minute, else the minute built from the 1-second book; each
            minute tagged in `f_src` (dext / book)
  spot      the chain record's spot, else chain_backfill's, carried over a minute with no chain at all
  Sides     sides.read on the saved chain (the same read /api/sides serves), the previous session's scale from
            sides_log.kal_scale (one copy with the server)
Every threshold is [I]. DISPLAY ONLY: no order path, no gate, no rate.
"""
from __future__ import annotations

import datetime
import functools
import math
import os

import chain_backfill
import chain_live
import confluence_log
import dext_log
import fronts
import handshake as H
import tailread
import v2feed

START = "09:15"
P5_MIN = {"NIFTY": 5, "BANKNIFTY": 15}       # the |p5| floor (spec §14 row 8); another index reads BANKNIFTY's [I]
SAID = ("TOOT", "PHANS", "TIKI")
MSG_DIR = os.path.join("data", "messages")   # the stream's record: the real shown-at of each push line
REV = "jarvis-1 (J2): the exporter's rules moved, the face's reads ported (not the engine)"
hm, mod = H.hm, H.mod


def _m(s):
    return int(s[:2]) * 60 + int(s[3:5])


def L(x):
    return None if x is None else round(x / 1e5, 1)


def _rows(path):
    """A day file's rows (its .gz once daylog has compressed it), followed incrementally (tailread); missing -> []."""
    return tailread.rows(path)


def _fut_tag(brows):
    """The book record's own contract as Dext names it (dext_parity's rule, handshake.load_flow): NSE_FO|61471 -> NSE-61471."""
    ik = next((r.get("ik") for r in brows if r.get("ik")), None)
    return f"NSE-{ik.split('|')[1]}" if isinstance(ik, str) and ik.startswith("NSE_FO|") else None


TAPE_DIR = os.path.join("data", "tape")


def tape_path(day, idx):
    return os.path.join(TAPE_DIR, f"fut1m_{idx}_{day}.json")


def save_tape(idx, session, now_ms=None):
    """P0 (30 Oct, JARVIS-DAY review): the server's 1-minute futures tape (live.build_session re-fetches the whole session
    from Upstox REST every cycle, so a reconnect brings every minute back) saved per day as {"HH:MM": [o, h, l, c, v, oi,
    seen_ms]}. `seen_ms` is the FIRST time a bar was saved and never moves: a replay at minute m uses only the bars live
    Jarvis had by then, so an outage stays blind in the replay too. 30 Oct lost 78 minutes for good without this. Atomic
    replace; the caller is fail-soft."""
    import json
    import time
    day_ = (session or {}).get("day") or {}
    day, bars = day_.get("date"), day_.get("bars") or []
    if not day or not bars:
        return 0
    now_ms = now_ms or int(time.time() * 1000)
    path = tape_path(day, idx)
    try:
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = {}
    out = {}
    for b in bars:
        f_ = b.get("fut") or {}
        if b.get("t") and f_.get("c") is not None:
            seen = (old.get(b["t"]) or [None] * 7)[6] or now_ms
            out[b["t"]] = [f_.get("o"), f_.get("h"), f_.get("l"), f_.get("c"), f_.get("v") or 0, f_.get("oi") or 0, seen]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))
    os.replace(tmp, path)
    return len(out)


def _tape_bars(day, idx, upto, fill=False):
    """The saved tape's bars known by minute `upto` (first seen at or before it), minutes < upto -> {"HH:MM": bar}.
    fill=True (her backtest replay, 31 Oct): every saved bar regardless of when it was first seen -- the day with its holes
    filled, which live Jarvis did NOT have; the frame's health says so."""
    import json
    try:
        with open(tape_path(day, idx), encoding="utf-8") as f:
            tape = json.load(f)
    except (OSError, ValueError):
        return {}
    return {k: b for k, b in tape.items() if _m(k) < upto and b[6] and (fill or mod(b[6]) <= upto)}


def _fut_bars(tag, day, brows, upto, idx=None, fill=False):
    """({"HH:MM": [iso, o, h, l, c, v, oi]}, {"HH:MM": "dext" | "book" | "tape"}) for the minutes < upto.
    Dext 0.8.1's getData rows where it has the minute -- a row is a 1-minute bar only when another row sits 60 s from it
    (29 Oct's file holds 5-minute bars, which are not minutes) -- else the minute from the 1-second book: ltp open / high
    / low / close, the vtt volume traded in it, its last OI -- else (P0, 30 Oct) the server's saved Upstox tape for a minute
    the book never saw, once that bar had reached the tape. A minute in none is absent (never a zero)."""
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    F, src = {}, {}
    rows = dext_log.read_ohlc(tag, day) if tag else []
    ts = {r["t"] for r in rows}
    for r in rows:
        d = datetime.datetime.fromtimestamp(r["t"], ist)
        if d.strftime("%Y-%m-%d") == day and r["t"] % 60 == 0 and (r["t"] - 60 in ts or r["t"] + 60 in ts) \
                and mod(r["t"] * 1000) < upto:
            F[d.strftime("%H:%M")] = [d.isoformat(), r["o"], r["h"], r["l"], r["c"], r.get("v") or 0, r.get("oi") or 0]
            src[d.strftime("%H:%M")] = "dext"
    prev, bars = None, {}
    for r in brows:                                   # time order, < upto (the caller cut them)
        p = r.get("ltp")
        if p is None:
            continue
        k = hm(mod(r["t"]))
        b = bars.get(k)
        if b is None:
            b = bars[k] = [None, p, p, p, p, 0, 0]
        b[2], b[3], b[4] = max(b[2], p), min(b[3], p), p
        if prev is not None and (r.get("vtt") or 0) > (prev.get("vtt") or 0):
            b[5] += r["vtt"] - prev["vtt"]
        if r.get("oi"):
            b[6] = r["oi"]
        prev = r
    for k, b in bars.items():
        if k not in F and b[6]:
            F[k], src[k] = b, "book"
    for k, b in (_tape_bars(day, idx, upto, fill) if idx else {}).items():
        if k not in F and b[5]:
            F[k], src[k] = [None, b[0], b[1], b[2], b[3], b[4], b[5]], "tape"
    return F, src


@functools.lru_cache(maxsize=8)
def _kal(chain_dir, idx, day):
    """The previous session's Sides scale (sides_log.kal_scale, the server's one copy), once per (dir, index, day): that
    session's file no longer changes."""
    import sides_log
    return sides_log.kal_scale(chain_dir, idx, day)


def _sides(day, idx, upto, live_from):
    """The Sides read of the saved chain as /api/sides serves it (sides.read on ChainState.oi_flow), each closed 5-min slot
    as known at its end, minutes < upto -> [{t, c, p, word, fuel_side, uw}] (export_mockup's shape), or None (no chain)."""
    import chain_metrics
    import sides
    import sides_log
    p = confluence_log._chain_path(idx, day)
    p = p if os.path.exists(p) else p + ".gz"
    if not os.path.exists(p):
        return None
    minutes, opens, book = {}, {}, {}
    for snap in _rows(p):
        if (snap.get("ts") or "")[:5] < hm(upto):
            sides_log.take(snap, minutes, opens, book)
    for t, rec in chain_backfill.read_grid(day, idx).items():   # the REST walk's marks, as the server's warm start reads them
        if t < hm(upto):
            minutes.setdefault(t, rec)
    g = chain_metrics.ChainState()
    g.minutes = minutes
    slots = sides.read(g.oi_flow(interval=sides.INTERVAL), minutes, now=hm(upto), live_from=live_from, opens=opens,
                       book=book, kal=_kal(str(chain_live.CHAIN_DIR), idx, day))
    return [{"t": s.get("slot_to") or s.get("t"), "c": s.get("c_state"), "p": s.get("p_state"), "word": s.get("word"),
             "fuel_side": s.get("fuel_side"), "uw": s.get("fuel_top2_underwater")} for s in slots]


def build(day: str, idx: str = "NIFTY", upto: int | None = None, fill: bool = False) -> dict:
    """The Jarvis frame for (day, idx) as known at minute `upto` (minutes < upto; None = the whole session). fill=True: book
    holes filled from the saved tape whenever it was saved (a backtest replay, not what live Jarvis saw)."""
    import trigger_log
    upto = H.LAST_M + 2 if upto is None else upto
    LOT, BAR = v2feed.LOTS[idx], H.FUT_LOTS[idx]
    P5 = P5_MIN.get(idx, P5_MIN["BANKNIFTY"])

    # ---- the book (causal), the fut bars, the spot -----------------------------------------------------------------------
    brows = sorted((r for r in H.book_rows(day, idx) if mod(r["t"]) < upto), key=lambda r: r["t"])
    tag = _fut_tag(brows)
    F, f_src = _fut_bars(tag, day, brows, upto, idx, fill)
    S = {}
    cp = confluence_log._chain_path(idx, day)
    for r in _rows(cp):                              # the index from the chain's own spot (recorded, else the backfill's)
        if r.get("spot") and START <= (r.get("ts") or "")[:5] <= "15:30" and _m(r["ts"]) < upto:
            S[r["ts"][:5]] = [None, r["spot"], r["spot"], r["spot"], r["spot"], 0, 0]
    bf = {ts: rec for ts, rec in chain_backfill.read_grid(day, idx).items() if _m(ts) < upto}
    for ts, rec in bf.items():
        if ts not in S and rec.get("spot"):
            S[ts] = [None, rec["spot"], rec["spot"], rec["spot"], rec["spot"], 0, 0]
    for mm in F:                                     # a minute with no chain at all (12:55-12:59) carries the last spot seen
        if mm not in S:
            prev = max((k for k in S if k < mm), default=None)
            if prev:
                S[mm] = S[prev]
    mins = [m for m in sorted(F) if START <= m and _m(m) < upto and m in S]
    if not mins:
        return {"ok": False, "day": day, "idx": idx, "upto": hm(upto),
                "why": "could not check — no futures minute and spot on the record before " + hm(upto)}
    MI = [_m(m) for m in mins]
    ks0 = H._ks(next(iter(r for r in _rows(cp) if r.get("strikes")), None))
    STEP = H._step(ks0) or 50
    sp = [S[m][4] for m in mins]
    STRIKES = list(range(int(round(min(sp) / STEP) * STEP - STEP), int(round(max(sp) / STEP) * STEP + STEP) + 1, STEP))

    # ---- the book: oim (lots), last LTP, holes, partial minutes ----------------------------------------------------------
    book_oi, book_px, last_sec, holes, prev = {}, {}, {}, [], None
    for r in brows:
        m = mod(r["t"])
        if r.get("oi"):
            book_oi[m] = r["oi"] / LOT
        if r.get("ltp") is not None:
            book_px[m] = r["ltp"]
        last_sec[m] = int(r["t"] / 1000) % 60
        if prev is not None and r["t"] - prev > 60_000:
            holes.append([hm(mod(prev)) + f":{int(prev / 1000) % 60:02d}", hm(m) + f":{int(r['t'] / 1000) % 60:02d}",
                          mod(prev), m])
        prev = r["t"]

    def hole_minute(m):
        """Finding 5: a minute whose last book row comes before :50 s, or that sits inside a > 60 s gap, is a hole."""
        if m not in book_oi or last_sec.get(m, 0) < 50:
            return True
        return any(a < m <= b for _, _, a, b in holes)

    oim, px, src = {}, {}, {}
    for mm, m in zip(mins, MI):
        if not hole_minute(m):
            oim[m], px[m], src[m] = book_oi[m], book_px.get(m, F[mm][4]), "book"
        else:
            oim[m], px[m], src[m] = F[mm][6] / LOT, F[mm][4], "rest"   # the bar's own OI (Dext / book: f_src says which)
    for mm, c in F.items():                          # the run rule needs the 5 minutes before START too
        m = _m(mm)
        if MI[0] - 6 <= m < MI[0]:
            oim[m], px[m], src[m] = (book_oi[m], book_px.get(m, c[4]), "book") if not hole_minute(m) else (c[6] / LOT, c[4], "rest")

    # ---- RASAD: the RUN rule as amended ---------------------------------------------------------------------------------
    def p5sign(m):
        if m - 5 not in px or m not in px:
            return "?"
        d = px[m] - px[m - 5]
        return "▲" if d >= P5 else "▼" if d <= -P5 else "?"

    def meaning(kind, d):
        return {("COVER", "▲"): "shorts cover", ("COVER", "▼"): "longs nikal rahe", ("FRESH", "▲"): "naye long",
                ("FRESH", "▼"): "naye short"}.get((kind, d), "disha ?")

    runs, run, last_ext_m, fuel = [], None, None, {}
    for m in sorted(oim):
        if m - 5 not in oim or m - 5 < H.FIRST_M + 1:
            fuel[m] = {"state": "?", "why": "5-min window mein hole"}
            continue
        w = oim[m] - oim[m - 5]
        if run is None:
            if abs(w) >= BAR:
                base = m - 5 if last_ext_m is None or m - 5 >= last_ext_m else last_ext_m
                d = p5sign(m)
                run = {"kind": "COVER" if w < 0 else "FRESH", "sgn": -1 if w < 0 else 1, "start": m, "base": base,
                       "ext": oim[m], "ext_m": m, "pub": 0, "dir": d, "dirs": [(m, d)], "opp": 0, "khatam": None}
                runs.append(run)
            fuel[m] = {"state": "LIVE", "run": len(runs) - 1} if run else {"state": "-"}
            continue
        if run["sgn"] * (oim[m] - run["ext"]) > 0:
            run["ext"], run["ext_m"], run["pub"] = oim[m], m, 0
        elif oim[m] != oim.get(m - 1):                              # finding 6: an unchanged minute is no publish
            run["pub"] += 1
        d = p5sign(m)
        if d != "?" and d != run["dir"]:
            run["opp"] += 1
            if run["opp"] >= 3:
                run["dir"], run["opp"] = d, 0
                run["dirs"].append((m, d))
        else:
            run["opp"] = 0
        if run["pub"] >= 3:
            run["khatam"] = m
            last_ext_m = run["ext_m"]
            fuel[m] = {"state": "KHATAM", "run": len(runs) - 1}
            run = None
        else:
            fuel[m] = {"state": "LIVE", "run": len(runs) - 1}
    for r in runs:
        r["lots"] = round(r["ext"] - oim[r["base"]])
        r["meaning"] = meaning(r["kind"], r["dir"])
        r["fuel_dir"] = r["dir"]
    RUNS = [{"kind": r["kind"], "start": hm(r["start"]), "base": hm(r["base"]), "last_ext": hm(r["ext_m"]),
             "khatam": None if r["khatam"] is None else hm(r["khatam"]), "lots": r["lots"], "dir": r["dir"],
             "dirs": [[hm(a), b] for a, b in r["dirs"]], "meaning": r["meaning"]} for r in runs]

    def run_at(m):
        """The run live at minute m (or just KHATAM'd at m), with lots so far."""
        for i, r in enumerate(runs):
            if r["start"] <= m <= (r["khatam"] if r["khatam"] is not None else 10 ** 6):
                so_far = round((min(oim[j] for j in oim if r["start"] <= j <= m) if r["sgn"] < 0
                                else max(oim[j] for j in oim if r["start"] <= j <= m)) - oim[r["base"]])
                d = next((b for a, b in reversed(r["dirs"]) if a <= m), r["dirs"][0][1])
                return {"i": i, "kind": r["kind"], "dir": d, "lots": so_far, "khatam": r["khatam"] == m,
                        "start": r["start"], "meaning": meaning(r["kind"], d)}
        return None

    # ---- the chain grid, the §1d fronts per minute (causal), the ladder -------------------------------------------------
    snaps = {}
    for s in _rows(cp):
        ts = (s.get("ts") or "")[:5]
        if ts and START <= ts <= "15:30" and s.get("spot") and _m(ts) < upto:
            snaps[ts] = s                                            # the last snapshot of each minute
    inp = H.load(day, idx)
    for k in ("R", "F", "src", "oim", "fm"):                         # causal: the handshake sees minutes < upto only
        inp[k] = {m: v for m, v in (inp.get(k) or {}).items() if m < upto}
    inp["ms"] = [m for m in inp["ms"] if m < upto]
    R, MS = inp["R"], inp["ms"]
    # J1b (29 Oct): the REST morning (chain_backfill) joins the walls as if we had been there -- an observed minute always
    # wins; absolute OI from handshake.with_backfill (the day's base seen live + the change); tagged src backfill.
    for ts, rec in bf.items():
        if ts not in snaps and rec.get("spot") and START <= ts <= "15:30":
            r = R.get(_m(ts)) or {}
            snaps[ts] = {"ts": ts + ":00", "spot": rec["spot"], "src": "backfill",
                         "strikes": [{"k": k, "ce": {"oi": H._leg(r, k, "ce").get("oi"), "oi_chg": c[0]},
                                      "pe": {"oi": H._leg(r, k, "pe").get("oi"), "oi_chg": c[1]}} for k, c in rec["k"].items()]}
    grid, peak, FR, ladder = {}, {}, {}, {}
    END = mins[-1]
    for ts in sorted(snaps):
        s = snaps[ts]
        grid[ts] = {"spot": s["spot"], "k": {float(r["k"]): ((r["ce"].get("oi_chg") or 0.0), (r["pe"].get("oi_chg") or 0.0))
                                            for r in s["strikes"]}}
        for r in s["strikes"]:
            for side in ("ce", "pe"):
                if isinstance(r[side].get("oi"), (int, float)):
                    peak[(float(r["k"]), side)] = max(peak.get((float(r["k"]), side), 0.0), r[side]["oi"])
        if ts < START or ts > END:
            continue
        FR[_m(ts)] = [{"k": f["k"], "side": f["side"], "state": f["state"], "chg": L(f["chg"]), "peak": L(f["peak"]),
                       "peak_at": f["peak_at"], "slope": L(f["slope"]), "oi": L(f["oi"])} for f in fronts.read(grid, dict(peak))]
        ladder[ts] = {"spot": s["spot"],
                      "ce": {k: L(H._leg(s, k, "ce").get("oi")) for k in STRIKES},
                      "pe": {k: L(H._leg(s, k, "pe").get("oi")) for k in STRIKES},
                      "ce_pk": {k: L(peak.get((float(k), "ce"))) for k in STRIKES},
                      "pe_pk": {k: L(peak.get((float(k), "pe"))) for k in STRIKES}}
    chain_missing = [mm for mm in mins if mm not in ladder]

    def front_state(m, side, k):
        """The §1d state of (side, k) as of minute m, with a 3-minute hold for UNWINDING (Q17)."""
        j = max((x for x in FR if x <= m), default=None)
        if j is None:
            return None
        return next((f for f in FR[j] if f["side"] == side and f["k"] == k), None)

    def unwinding_held(m, side, k):
        return all((front_state(j, side, k) or {}).get("state") == "UNWINDING" for j in (m, m - 1, m - 2) if j in FR)

    # ---- pushes: the handshake rows, the hold rule, the artifact flag ----------------------------------------------------
    HS = H.read(inp, upto)
    PUSH = []
    for row, p in zip(HS, inp["pushes"]):
        m, d = p["m"], p["dir"]
        a1 = H.answer(R, MS, p, upto)
        a4 = H.answer(R, MS, p, upto, first=False)
        held, held_at = None, None
        if a1 and a1["ans"] in SAID:
            # handshake-2 already confirmed it (its "held" minute), or it was read at m+4 (final). The brain used to re-read
            # the one strike here, which turned every band answer (G1) into a false "wapas".
            held, held_at = a1["ans"], a1.get("held", a1["am"])
        artifact = any(a <= m and m - 2 <= b for _, _, a, b in holes)
        PUSH.append({"t": row["t"], "m": m, "dir": d, "lots": row["lots"], "norm": row["norm"], "src": row["src"],
                     "k": row["k"], "side": row["side"], "oi_L": row["oi_L"], "ans": row["ans"], "chg": row["chg"],
                     "bar": row["bar"], "am": row["am"], "am_m": None if a1 is None else a1["am"],
                     "ans4": None if a4 is None else a4["ans"], "chg4": None if a4 is None else a4["chg"],
                     "held": held, "held_at": None if held_at is None else hm(held_at), "held_m": held_at,
                     "who": row["who"], "behind": row["behind"], "floor_cap": row["floor_cap"], "fut": row["fut"],
                     "effort": row["effort"], "p15": row.get("p15"), "p30": row.get("p30"), "artifact": artifact,
                     "key": row["key"], "via": row.get("via")})

    shown = {}                                       # the stream's real shown-at (the lag she lived with), as of upto
    for r in _rows(os.path.join(MSG_DIR, f"msg_{day}.jsonl")):
        if r.get("kind") == "FLOW" and r.get("key") and isinstance(r.get("at"), (int, float)) \
                and datetime.datetime.fromtimestamp(r["at"]).strftime("%Y-%m-%d") == day and mod(r["at"] * 1000) < upto:
            shown[r["key"]] = datetime.datetime.fromtimestamp(r["at"]).strftime("%H:%M:%S")
    for p in PUSH:
        p["shown"] = shown.get(p["key"])

    def final_ans(p, at):
        """What the push's answer reads at minute `at` (causal): None (pending), 'TOOT?' (crossed, hold pending), the held
        word, 'wapas', 'NAHI', or '?'. G4: a TIKI whose OI BUYERS opened reads 'GHUSE' (buyers in): not a defended wall,
        so no rule that counts a TIKI as the wall holding counts it."""
        if p["artifact"]:
            return "artifact"
        if p["am_m"] is None or p["am_m"] > at - 1:
            return None
        if p["ans"] in SAID:
            w = "GHUSE" if p["ans"] == "TIKI" and p.get("who") == "KHAREEDAR" else p["ans"]
            if p["held_m"] is not None and p["held_m"] <= at - 1:
                return w if p["held"] == p["ans"] else p["held"]
            return w + "?"
        return p["ans"] if p["ans"] is not None else "?"

    # ---- KAHANI: the fight, its chapters, per minute (causal) -----------------------------------------------------------
    def wall_ahead(m, d, spot):
        j = max((x for x in FR if x <= m), default=None)
        if j is None:
            return None
        side = "CE" if d > 0 else "PE"
        lo, hi = (spot - STEP / 2, spot + 2 * STEP) if d > 0 else (spot - 2 * STEP, spot + STEP / 2)
        for f in FR[j]:                                              # fronts.read is ranked: rank 1 first
            if f["side"] == side and lo <= f["k"] <= hi:
                return f
        return None

    def spot_at(m):
        j = max((x for x in R if x <= m), default=None)
        return None if j is None else R[j]["spot"]

    fight, fights, timeline = None, [], []
    asof = {}       # causal: the fight's KHATAM and latest TOOT as known at each minute (the verdict reads these, never the
                    # fight's end-of-window state; found by test_causal_prefix, J2)
    for mm, m in zip(mins, MI):
        spot = spot_at(m)
        known = [p for p in PUSH if p["m"] < m and not p["artifact"]]
        if fight is None or (fight.get("ended") and fight["ended_m"] < m):
            d = (known[-1]["dir"] if known else None)
            if d is None:
                s0 = spot_at(m - 15)
                d = 1 if (spot or 0) >= (s0 or 0) else -1
            w = wall_ahead(m, d, spot) if spot is not None else None
            fight = {"id": len(fights), "d": d, "side": "CE" if d > 0 else "PE", "k": None if w is None else w["k"],
                     "born": mm, "dastak": [], "toot": None, "floor": None, "naya_floor": None, "khatam": None,
                     "ending": None, "ended": False, "ended_m": None, "chips": [], "stamps": []}
            fights.append(fight)
        # re-target in the DEEWAR / KHISAK stage: the fight is where the first knock lands
        if not fight["dastak"] and known and fight["toot"] is None:
            lp = known[-1]
            if lp["dir"] != fight["d"] or fight["k"] is None:
                w = wall_ahead(m, lp["dir"], spot)
                if w is not None:
                    fight.update(d=lp["dir"], side=w["side"], k=w["k"])
        # the knocks: pushes into the fight's side whose attacked strike is the wall or nearer to price
        for p in known:
            if p["dir"] == fight["d"] and p["m"] >= _m(fight["born"]) - 1 and p not in [q["p"] for q in fight["dastak"]]:
                if fight["k"] is None or p["k"] is None or (p["k"] <= fight["k"] if fight["d"] > 0 else p["k"] >= fight["k"]):
                    fight["dastak"].append({"p": p})
        # the answers as known now
        for q in fight["dastak"]:
            q["ans"] = final_ans(q["p"], m)
            if q["ans"] in ("TOOT", "PHANS") and not q.get("stamped"):
                q["stamped"] = True
                fight["toot"] = fight["toot"] or {"t": q["p"]["t"], "ans": q["ans"], "chg": q["p"]["chg"], "known": hm(m), "m": m}
                fight["latest_toot"] = q["p"]["t"]                      # NEXT / ULTA PUSH count from the LATEST toot
                fight["stamps"].append([mm, "TOOT" if q["ans"] == "TOOT" else "PHANSE", f"{q['p']['t']} {q['p']['chg']:+.1f}L"])
        wf = front_state(m, fight["side"], fight["k"]) if fight["k"] is not None else None
        wstate = None if wf is None else wf["state"]
        unw = fight["k"] is not None and unwinding_held(m, fight["side"], fight["k"])
        ru = run_at(m)
        # the opposite pushes: ulta dastak, NAYA FLOOR (flip), PALAT wall form
        opp = [p for p in known if p["dir"] == -fight["d"] and p["m"] >= _m(fight["born"]) - 1]
        for p in opp:
            a = final_ans(p, m)
            if a == "TIKI" and p.get("who") == "WRITERS" and fight["toot"] and fight["naya_floor"] is None:
                other = front_state(m, fight["side"], p["k"])          # the same strike's other side (the wall's side)
                flip = (fight["k"] == p["k"]) or (other or {}).get("state") == "UNWINDING"
                if flip:
                    fight["naya_floor"] = {"k": p["k"], "side": p["side"], "chg": p["chg"], "t": p["t"], "known": hm(m)}
                    fight["stamps"].append([mm, "NAYA FLOOR" if fight["d"] > 0 else "NAYA CAP",
                                            f"{p['k']:,.0f}s {p['side']} {p['chg']:+.1f}L (flip)"])
        # P2 (30 Oct, NOISE-DECODER §4.6): a fight price has LEFT BEHIND -- more than FIGHT_AWAY steps from its wall for
        # FIGHT_AWAY_MIN minutes -- ends; the next minute a new fight is born at the wall ahead. 29 Oct kept 22,700s PE all
        # day (315 of 361 minutes > 2 steps away); 30 Oct kept 23,000s CE with price three hours above 23,100s.
        if not fight["ending"] and fight["k"] is not None and spot is not None and abs(spot - fight["k"]) > FIGHT_AWAY * STEP:
            fight.setdefault("away_since", m)
            if m - fight["away_since"] >= FIGHT_AWAY_MIN:
                fight["ending"], fight["ended"], fight["ended_m"] = "PEECHHE CHHOOTA", True, m
                fight["stamps"].append([mm, "PEECHHE CHHOOTA",
                                        f"{fight['k']:,.0f}s {fight['side']} · price {FIGHT_AWAY}+ steps away for {FIGHT_AWAY_MIN} min"])
        else:
            fight.pop("away_since", None)
        # chapter
        if fight["ending"]:
            chap = fight["ending"]
        elif fight["toot"] is None:
            n = len(fight["dastak"])
            if any(q["ans"] in ("TOOT?", "PHANS?") for q in fight["dastak"]):
                chap = "TOOT?"
            elif n == 0:
                chap = "KHISAK" if unw else "DEEWAR"
            else:
                chap = "THAKAN" if unw else f"DASTAK ×{n}"
            if n and ru and fight["toot"] is None:
                chap += " · RASAD bina toot"
        else:
            if fight["khatam"] is None:
                if ru and ru["khatam"]:
                    fight["khatam"] = {"t": mm, "lots": ru["lots"], "kind": ru["kind"], "dir": ru["dir"]}
                    fight["stamps"].append([mm, "KHATAM", f"{ru['kind'].lower()} {ru['lots']:+,} lots"])
                    chap = "KHATAM"
                elif ru:
                    chap = f"RASAD {ru['kind'].lower()} {ru['dir']}"
                else:
                    chap = "TOOT · RASAD ?" if fight["toot"]["ans"] == "TOOT" else "PHANSE"
            else:
                chap = "KHATAM"
                kh = _m(fight["khatam"]["t"])
                after = [p for p in known if p["m"] > kh]
                if ru and ru["start"] > kh:
                    if ru["dir"] == ("▲" if fight["d"] > 0 else "▼"):
                        fight["ending"], chap = "CHAL", "CHAL"
                    elif ru["dir"] == ("▼" if fight["d"] > 0 else "▲"):
                        fight["ending"], chap = "PALAT (eendhan)", "PALAT (eendhan)"
                if not fight["ending"]:
                    opp_toot = [p for p in after if p["dir"] == -fight["d"] and final_ans(p, m) in ("TOOT", "PHANS")
                                and fight["naya_floor"] and p["k"] == fight["naya_floor"]["k"]]
                    if opp_toot:
                        fight["ending"], chap = "PALAT (deewar)", "PALAT (deewar)"
                    else:
                        ok = ("NAHI", "TIKI", "wapas")
                        up = any(p["dir"] == fight["d"] and final_ans(p, m) in ok for p in after)
                        dn = any(p["dir"] == -fight["d"] and final_ans(p, m) in ok for p in after)
                        if up and dn:
                            fight["ending"], chap = "PIN", "PIN"
                        elif not after and m - kh >= 20:
                            fight["ending"], chap = "KHAMOSH", "KHAMOSH"
                if fight["ending"]:
                    fight["ended"], fight["ended_m"] = True, m
                    fight["stamps"].append([mm, fight["ending"], ""])
        # WAPSI: the broken strike rebuilt by >= the bar after its TOOT
        if fight["toot"] and fight["k"] is not None and wf and fight["toot"]["ans"] == "TOOT":
            tq = next((q for q in fight["dastak"] if q["ans"] in ("TOOT", "PHANS")), None)
            if tq and tq["p"]["bar"] and wf["chg"] is not None:
                at_toot = front_state(_m(tq["p"]["am"]), fight["side"], fight["k"])
                if at_toot and at_toot["chg"] is not None and wf["chg"] - at_toot["chg"] >= tq["p"]["bar"] \
                        and not any(s[1] == "WAPSI" for s in fight["stamps"]):
                    fight["stamps"].append([mm, "WAPSI", f"{fight['k']:,.0f}s {fight['side']} +{wf['chg'] - at_toot['chg']:.1f}L"])
        if fight["stamps"] and not any(s[1] in ("DEEWAR", "KHISAK") for s in fight["stamps"]) and fight["k"] is not None:
            fight["stamps"].insert(0, [fight["born"], "KHISAK" if unw else "DEEWAR", f"{fight['k']:,.0f}s {fight['side']}"])
        last_chap = timeline[-1]["chapter"] if timeline else None
        if chap != last_chap and chap.split(" ·")[0].startswith(("DASTAK", "THAKAN", "TOOT?", "RASAD", "KHATAM", "DEEWAR", "KHISAK")):
            if not fight["stamps"] or fight["stamps"][-1][1] != chap.split(" ·")[0]:
                fight["stamps"].append([mm, chap.split(" ·")[0], ""])
        timeline.append({"t": mm, "fight": fight["id"], "wall": fight["k"], "side": fight["side"], "wall_state": wstate,
                         "wall_chg": None if wf is None else wf["chg"], "wall_peak": None if wf is None else wf["peak"],
                         "chapter": chap,
                         # a pending answer's attacked strike is not known yet at m (the handshake returns it with the answer)
                         "dastak": [[q["p"]["t"], q["ans"], q["p"]["lots"], q["p"]["k"] if q["ans"] is not None else None]
                                    for q in fight["dastak"]],
                         "ulta": [[p["t"], a, p["lots"], p["k"] if a is not None else None] for p, a in ((p, final_ans(p, m)) for p in opp)],
                         "fuel": None if ru is None else {k: v for k, v in ru.items() if k != "i"},
                         "fuel_state": fuel.get(m, {}).get("state"), "fuel_src": src.get(m),
                         "naya_floor": fight["naya_floor"], "khatam": fight["khatam"], "ending": fight["ending"],
                         "fronts": FR.get(max((x for x in FR if x <= m), default=-1), [])})
        asof[mm] = (fight["khatam"], fight.get("latest_toot"))

    # ---- the band verdict per minute, both sides (SELL: defender CE, wants fuel ▼; BUY: mirror) --------------------------
    def verdict(m, tside):
        want = "▼" if tside == "SELL" else "▲"
        band_d = 1 if tside == "SELL" else -1                        # the band side's push direction (into the defender)
        dside = "CE" if tside == "SELL" else "PE"
        tl = next((x for x in timeline if x["t"] == hm(m)), None)
        if tl is None:
            return None
        ru = tl["fuel"]
        fstate = tl["fuel_state"]
        known = [p for p in PUSH if p["m"] < m and not p["artifact"]]
        f = fights[tl["fight"]]
        f_khatam, f_latest = asof[tl["t"]]
        b = f["side"] == dside and f["toot"] is not None and f["toot"]["m"] <= m and not (f["ended"] and f["ended_m"] < m)
        pieces = {}
        if fstate == "?":
            pieces["FUEL"] = ["?", "hole"]
        elif ru and not ru["khatam"]:
            pieces["FUEL"] = (["?", f"{ru['kind'].lower()} disha ?"] if ru["dir"] == "?" else
                              ["✓", f"{ru['kind'].lower()} {ru['dir']} {ru['lots']:+,}"] if ru["dir"] == want else
                              ["✗", f"{ru['kind'].lower()} {ru['dir']} {ru['lots']:+,} chal raha"])
        else:
            if b:
                pieces["FUEL"] = ["✓", "KHATAM" if f_khatam else "koi run nahi"]
            else:
                recent = [r for r in runs if r["khatam"] is not None and m - 30 <= r["khatam"] <= m and r["dir"] != "?"]
                against = [r for r in recent if r["dir"] != want]
                opp_since = any(r["khatam"] > against[-1]["khatam"] and r["dir"] == want for r in recent) if against else False
                pieces["FUEL"] = (["✗", f"run {against[-1]['dir']} {hm(against[-1]['khatam'])} tak (30 min)"]
                                  if against and not opp_since else ["✓", "koi run nahi"])
        if not b:
            w = wall_ahead(m, band_d, spot_at(m)) if spot_at(m) is not None else None
            if w is None:
                pieces["WALL"] = ["✗", "koi deewar nahi (2 step)"]
            else:
                pieces["WALL"] = (["✓", f"{w['k']:,.0f}s {w['side']} {w['state'].lower()}"] if w["state"] in ("BUILDING", "STALLED")
                                  else ["✗", f"{w['k']:,.0f}s {w['side']} unwinding {w['chg'] - w['peak']:+.1f}L"])
            last = [p for p in known if p["dir"] == band_d and p["m"] >= m - 15]
            if not last:
                pieces["DASTAK"] = ["?", "15 min mein push nahi"]
            else:
                a = final_ans(last[-1], m)
                pieces["DASTAK"] = (["✓", f"{last[-1]['t']} {a}"] if a in ("NAHI", "TIKI", "wapas") else
                                    ["✗", f"{last[-1]['t']} {a}"] if a in ("TOOT", "PHANS") else ["?", f"{last[-1]['t']} {a or 'jawab baaki'}"])
        else:
            lt = _m(f_latest or f["toot"]["t"])
            nxt = [p for p in known if p["dir"] == band_d and p["m"] > lt]
            if not nxt:
                pieces["NEXT PUSH"] = ["?", "abhi push nahi"]
            else:
                a = final_ans(nxt[0], m)
                pieces["NEXT PUSH"] = (["✓", f"{nxt[0]['t']} {a}"] if a in ("NAHI", "TIKI", "wapas") else
                                       ["✗", f"{nxt[0]['t']} {a}"] if a in ("TOOT", "PHANS") else ["?", f"{nxt[0]['t']} {a or 'jawab baaki'}"])
            ul = [p for p in known if p["dir"] == -band_d and p["m"] > lt]
            if not ul:
                pieces["ULTA PUSH"] = ["?", "abhi push nahi"]
            else:
                a = final_ans(ul[0], m)
                pieces["ULTA PUSH"] = (["✓", f"{ul[0]['t']} TOOT {ul[0]['k']:,.0f}s"] if a in ("TOOT", "PHANS") else
                                       ["✗", f"{ul[0]['t']} TIKI {ul[0]['k']:,.0f}s"] if a == "TIKI" else
                                       ["·", f"{ul[0]['t']} NAHI"] if a in ("NAHI", "wapas") else ["?", f"{ul[0]['t']} {a or 'jawab baaki'}"])
        marks = [v[0] for v in pieces.values()]
        n_ok, n_bad, N = marks.count("✓"), marks.count("✗"), marks.count("✓") + marks.count("✗")
        if pieces["FUEL"][0] == "✗" or (not b and pieces["WALL"][0] == "✗" and pieces["DASTAK"][0] == "✗") or \
                (b and pieces["NEXT PUSH"][0] == "✗"):
            word = "CHALEGA"
        elif n_ok >= 2 and n_bad == 0:
            word = "GHUMEGA"
        else:
            word = "SAAF NAHI"
        return {"ctx": "b" if b else "a", "word": word, "n": n_ok, "N": N, "q": marks.count("?"), "pieces": pieces}

    VERD = {s: {} for s in ("SELL", "BUY")}
    for mm, m in zip(mins, MI):
        for s in VERD:
            v = verdict(m, s)
            if v:
                VERD[s][mm] = v

    # ---- the zone rows (trigger_log, zone3, today) ----------------------------------------------------------------------
    ZONE = []
    for r in _rows(trigger_log.PATH):
        if r.get("day") == day and r.get("index") == idx and r.get("rule") == "zone3" and START <= str(r.get("t", ""))[:5] \
                and _m(str(r["t"])) < upto:
            ZONE.append({k: r.get(k) for k in ("t", "kind", "side", "px", "level", "stop", "entry", "band", "u2", "d2", "bands_on")
                         if r.get(k) is not None})

    data = {"ok": True, "day": day, "idx": idx, "lot": LOT, "bar": BAR, "step": STEP, "start": START, "end": END,
            "upto": hm(upto), "fill": fill, "mins": mins,
            "spot": [S[m][4] for m in mins], "fut": [F[m][4] for m in mins], "fhi": [F[m][2] for m in mins],
            "flo": [F[m][3] for m in mins], "f_src": [f_src[m] for m in mins],
            "oi": [round(oim[m], 1) for m in MI], "oi_src": [src[m] for m in MI], "vol": [round(F[m][5] / LOT) for m in mins],
            "runs": RUNS, "strikes": STRIKES, "ladder": ladder, "chain_missing": chain_missing,
            "holes": [[a, b] for a, b, _, _ in holes],
            "pushes": PUSH, "timeline": timeline, "verdict": VERD, "zone": ZONE,
            "fights": [{"id": f["id"], "k": f["k"], "side": f["side"], "born": f["born"], "stamps": f["stamps"],
                        "ending": f["ending"]} for f in fights],
            "rev": "mockup reading of ROUND1-ANSWERS rules (not the engine)", "brain": REV}
    # Her asks, 29 Oct ~01:45 (speed, candle-vs-delta at the top, absorption / exhaustion, her VWAP bands to trail, all 3 in
    # sync): the true 1-min open, Dext 0.8.1's footprint delta and volume per minute (lots), the session VWAP (hlc3) and its
    # SD from the 1-min bars (matches her zone's logged u2 within ~1 pt), and BANKNIFTY / SENSEX spot (chain + backfill, carried).
    fp = {c["time"][11:16]: c for c in (dext_log.read_candles(tag, day) if tag else [])}
    data["fo"] = [F[m][1] for m in mins]
    data["delta"] = [round(fp[m]["delta"] / LOT) if m in fp else None for m in mins]
    data["fvol"] = [round(fp[m]["total_volume"] / LOT) if m in fp else None for m in mins]
    sv = spv = 0.0
    xs, data["vwap"], data["sd"] = [], [], []
    for m in mins:
        p, v = (F[m][2] + F[m][3] + F[m][4]) / 3, F[m][5] or 0
        sv, spv = sv + v, spv + p * v
        xs.append((p, v))
        w = spv / sv if sv else p
        data["vwap"].append(round(w, 1))
        data["sd"].append(round(math.sqrt(sum(v * (q - w) ** 2 for q, v in xs) / sv), 1) if sv else 0.0)

    def other_spot(i):
        got = {}
        for r in _rows(confluence_log._chain_path(i, day)):
            if r.get("spot") and START <= (r.get("ts") or "")[:5] <= "15:30":
                got[r["ts"][:5]] = r["spot"]
        for ts, rec in chain_backfill.read_grid(day, i).items():
            if ts not in got and rec.get("spot"):
                got[ts] = rec["spot"]
        out, last = [], None
        for m in mins:
            last = got.get(m, last)
            out.append(last)
        return out

    data["bnf"], data["sx"] = other_spot("BANKNIFTY"), other_spot("SENSEX")
    data["live_from"] = hm(mod(brows[0]["t"])) if brows else None
    # Her catch, 29 Oct 10:45: the Board's Sides read (sides.py, /api/sides) is the options-side fuel; each 5-min slot as
    # known at its end. Her ask, 29 Oct 11:00: WRITER FLOW ±7 -- the 3-min OI change summed over ATM ±7 strikes, per side
    # (L), per minute.

    def wflow(m, side, w=7):
        a, b = snaps.get(m), snaps.get(hm(_m(m) - 3))
        if not a or not b or not a.get("spot"):
            return None
        atm = round(a["spot"] / STEP) * STEP
        tot, n = 0.0, 0
        for k in range(int(atm - w * STEP), int(atm + w * STEP) + 1, STEP):
            x, y = H._leg(a, k, side).get("oi"), H._leg(b, k, side).get("oi")
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                tot, n = tot + (x - y), n + 1
        return round(tot / 1e5, 1) if n >= 2 * w else None

    data["wf_ce"], data["wf_pe"] = [wflow(m, "ce") for m in mins], [wflow(m, "pe") for m in mins]
    data["sides"] = _sides(day, idx, upto, data["live_from"])
    for s in data["sides"] or ():
        s["fuel"] = sides_fuel(s)                    # the face draws the brain's fuel slots, never its own rule
    # the flow the reads use: Dext's footprint delta, else the book's own (handshake.book_flow, src B) -- a minute in
    # neither stays None (Dext missing AND the book blind), never a zero
    data["flow"] = [x if x is not None else (inp["F"].get(m) if inp["src"].get(m) == "B" else None)
                    for x, m in zip(data["delta"], MI)]
    data["flow_src"] = ["D" if x is not None else ("B" if y is not None else None) for x, y in zip(data["delta"], data["flow"])]
    data["reads"] = reads(data)
    data["health"] = health(data, _readable(day, "BANKNIFTY", upto, 100))
    data["legs"] = _legs(data, R, day, idx)
    data["call"] = call(data)
    return data


def _legs(d, R, day, idx):
    """THE LEG (legs.py; NOISE-DECODER-BRAINSTORM.md, merged decision 30 Oct) on this frame, with its two extras: the ATM
    premium + delta per chain minute (near ATM, +/- 5 steps) and her footprint marks (NIFTY's chart only: SENSEX reads
    NIFTY's flow, §1q, but a NIFTY mark's price means nothing on SENSEX). Fail-soft: a decoder error leaves the frame and
    the old call standing, and says so."""
    import legs
    import tape_log
    try:
        step = d.get("step") or 50
        chain = {}
        for m, r in R.items():
            sp = r.get("spot")
            if not sp:
                continue
            row = {"spot": sp, "ce": {}, "pe": {}}
            for s in r.get("strikes") or ():
                if isinstance(s.get("k"), (int, float)) and abs(s["k"] - sp) <= 5 * step:
                    for side in ("ce", "pe"):
                        leg = s.get(side) or {}
                        if leg.get("ltp") is not None and leg.get("delta") is not None:
                            row[side][s["k"]] = {"ltp": leg["ltp"], "delta": leg["delta"]}
            chain[hm(m)] = row
        marks = list(_rows(os.path.join(tape_log.DIR, f"ofd_marks2_{idx}_{day}.jsonl"))) if idx == "NIFTY" else None
        return legs.read(d, chain=chain, marks=marks)
    except Exception as e:                                    # display only: never take the frame down
        return {"error": f"{type(e).__name__}: {e}", "rows": [], "pauses": [], "day": {}, "missing": ["the leg read failed"]}


def _readable(day, idx, upto, step):
    """Is this index's chain OI big enough to read? A strike within ATM ±7 moved >= the handshake's bar (CUT_L, 3L) in 3
    min at least once before upto [I]. BANKNIFTY's biggest 3-min strike move was 0.24L (28 Oct) / 0.52L (29 Oct) against
    NIFTY's 8.8L / 18.1L: it never can. None = no chain on the record (could not check)."""
    R = H.chain_minutes(_rows(confluence_log._chain_path(idx, day)))
    R = {m: r for m, r in R.items() if m < upto}
    if not R:
        return None
    for m, a in R.items():
        b = R.get(m - 3)
        if not b:
            continue
        atm = round(a["spot"] / step) * step
        for k in range(int(atm - 7 * step), int(atm + 7 * step) + 1, step):
            for s in ("ce", "pe"):
                x, y = H._leg(a, k, s).get("oi"), H._leg(b, k, s).get("oi")
                if x is not None and y is not None and abs(x - y) >= H.CUT_L * 1e5:
                    return True
    return False


# GAPS §3 rows this frame does not read (GAPS §5: named, never dropped). The first five have no source anywhere yet.
NOT_READ = ("book depth: pulls / stacking at the level (recorded, not read)",
            "points per minute, acceleration / decay",
            "IV per strike: bid vs crush, premium decay vs the move",
            "expiry: max pain / pin, gamma after 14:30",
            "India VIX direction",
            "not in this frame yet (their own modules read them): CVD divergence (decode), effort per point (effort.py), "
            "BADA PRINT, footprint events, VPIN, dwell, PCR change, wall migration, day type (onesided), THE READ word, "
            "DECODE lines, Board agreement, PDH / PDL / PDC, range used vs EM")


def _stretches(flags, mins):
    """[[from, to]] of the runs of True in `flags`."""
    out, i = [], 0
    while i < len(flags):
        if flags[i]:
            j = i
            while j + 1 < len(flags) and flags[j + 1]:
                j += 1
            out.append([mins[i], mins[j]])
            i = j + 1
        else:
            i += 1
    return out


def health(d: dict, bnf_readable=None) -> dict:
    """GAPS §3 A: every source's state as of the frame's last minute, each gap named with its span (rule 6: could not
    check is its own sentence, never a zero)."""
    mins = d["mins"]
    no_dx = [x is None for x in d["delta"]]
    missing = _stretches(no_dx, mins)
    tail = 0
    for x in reversed(no_dx):
        if not x:
            break
        tail += 1
    notes = []
    for a, b in missing:
        if tail and b == mins[-1]:
            src = d.get("flow_src") or []
            book = sum(1 for s in src[-tail:] if s == "B")
            notes.append(f"Dext footprint missing since {a} · newest {tail} min "
                         + (f"from the book" if book == tail else f"from the book {book}, blind {tail - book}"))
        else:
            notes.append(f"Dext footprint missing {a}–{b}" + (" (flow from the book)" if a != b else ""))
    for a, b in d.get("holes") or ():
        notes.append(f"book hole {a}–{b}: no 1-second book; "
                     + ("FILL replay: fut from the saved tape" if d.get("fill") else "answers there unread"))
    for a, b in _stretches([m in set(d.get("chain_missing") or ()) for m in mins], mins):
        notes.append(f"chain missing {a}–{b}: walls and answers there not read")
    fs = d.get("f_src") or []
    if fs.count("book"):
        notes.append(f"fut 1-min bars from the book for {fs.count('book')} min (Dext has no 1-minute bars there)")
    if fs.count("tape"):
        notes.append(f"fut 1-min bars rebuilt from the Upstox tape for {fs.count('tape')} min (the book was empty there)"
                     + (" · FILL replay: live Jarvis did not have these minutes" if d.get("fill") else ""))
    if d.get("live_from") and d["live_from"] > mins[0]:
        notes.append(f"recorded live from {d['live_from']}: {mins[0]}–{d['live_from']} rebuilt (chain backfill, Dext)")
    if d.get("sides") is None:
        notes.append("Sides: could not check — no saved chain")
    if bnf_readable is False:
        notes.append("BANKNIFTY chain OI too small to read (no strike near ATM moved 3L in 3 min)")
    elif bnf_readable is None:
        notes.append("BANKNIFTY chain: could not check — no chain on the record")
    return {"dext": {"minutes": no_dx.count(False), "missing": missing, "book_only_tail": tail},
            "holes": d.get("holes") or [], "chain_missing": d.get("chain_missing") or [], "bnf_chain_readable": bnf_readable,
            "f_src": {k: fs.count(k) for k in ("dext", "book", "tape")}, "live_from": d.get("live_from"), "notes": notes,
            "not_read": list(NOT_READ)}


def call(d: dict) -> dict:
    """THE ONE CALL at the frame's last minute, in GAPS §4's order: health -> location -> flow + speed -> writers ->
    futures OI -> cross-index -> her setup -> one word, its wrong-line, two scenarios, both expressions. The word:
    UP / DOWN only when the writers (Sides REAL / BACKED, or ±7 pushing) and at least one more of {a fut run, speed FAST,
    ALL 3} agree; RANGE when both sides add; NO TRADE when blind, quiet, or nothing agrees. Counts, never %. Guidance only."""
    r, h, mins = d["reads"], d["health"], d["mins"]
    i = len(mins) - 1
    tl, sp, sy, w = d["timeline"][i], r["speed"][i], r["sync"][i], r["writers"][i]
    fut = d["fut"][i]
    bs = sorted(a - b for a, b in zip(d["fut"][-5:], d["spot"][-5:]) if a is not None and b is not None)
    basis = bs[len(bs) // 2] if bs else 0.0

    def lv(k):
        return f"{_fmt(k)}s ({_fmt(k + basis)}f)"

    # P0 (30 Oct): BLIND live. The frame's newest minute trails the clock (the futures trade to 15:39): no book, no tape --
    # her internet or Upstox is down. 30 Oct 14:30-14:45 read UP off 14:26's data while price fell 38; now it says so.
    up_m = _m(d["upto"]) if d.get("upto") else None
    lag = None if up_m is None else (up_m - 1) - _m(mins[i])
    blind = lag is not None and lag > BLIND_MIN and up_m - 1 <= H.LAST_M + 9
    missing = ([f"BLIND since {mins[i]}: no market data for {lag} min (internet or Upstox)"] if blind else []) + list(h["notes"])
    why = ["health: " + ("every source live" if not missing else f"{len(missing)} gap{'s' if len(missing) > 1 else ''}: "
                         + " · ".join(missing))]
    vw, sd = d["vwap"][i], d["sd"][i]
    why.append(f"location: {_fmt(fut)}f · VWAP {_fmt(vw)}f" + (f" · {(fut - vw) / sd:+.1f}σ" if sd else "")
               + f" · day {_fmt(min(d['flo']))}–{_fmt(max(d['fhi']))}f")
    why.append(f"flow: speed {ARR[sp['dir']]} ×{sp['x']:.1f} {sp['word']} · 3-min delta {_sgn(sp['d3'])}" if sp["x"] is not None
               else f"flow: speed ? ({sp['why']})")
    s = None
    for x in d.get("sides") or ():
        if x.get("t") and x["t"] <= mins[i]:
            s = x
    fr = tl.get("fronts") or []
    spot = d["spot"][i]
    ce = sorted((f for f in fr if f["side"] == "CE" and f["k"] > spot - 5), key=lambda f: f["k"])
    pe = sorted((f for f in fr if f["side"] == "PE" and f["k"] < spot + 5), key=lambda f: -f["k"])
    answered = [p for p in d["pushes"] if p.get("ans") not in (None, "?") and p.get("am") and p["am"] <= mins[i]]
    wtxt = (f"±7 {w['state']} (CE {H._l(w['ce'])} · PE {H._l(w['pe'])} / 3 min)" if w["state"] and w["ce"] is not None
            else f"±7 {w['state'] or 'quiet'}" + (" (chain not read this minute)" if w["ce"] is None else ""))
    stxt = ("Sides: could not check" if d.get("sides") is None else "Sides: no closed slot yet" if s is None else
            f"Sides {s['t']} {s['word'] or '?'}" + (f" ({'call' if s['fuel_side'] == 'ce' else 'put'} writers covering"
                                                     + (f", top-2 under water {s['uw']}/2" if s.get("uw") else "") + ")"
                                                     if sides_fuel(s) else ""))
    why.append("writers: " + " · ".join([wtxt, stxt,
                                         f"wall above {lv(ce[0]['k'])} CE {ce[0]['oi']:.0f}L {ce[0]['state'].lower()}"
                                         if ce and ce[0].get("oi") is not None else "no CE wall above in range",
                                         f"wall below {lv(pe[0]['k'])} PE {pe[0]['oi']:.0f}L {pe[0]['state'].lower()}"
                                         if pe and pe[0].get("oi") is not None else "no PE wall below in range"]
                                        + ([f"last answer {answered[-1]['t']} {answered[-1]['k'] and _fmt(answered[-1]['k'])}s "
                                            f"{answered[-1]['side']}{' ±2' if answered[-1].get('via') == 'band' else ''} "
                                            + ("GHUSE (buyers' add, not a defence)" if answered[-1]['ans'] == "TIKI"
                                               and answered[-1].get("who") == "KHAREEDAR" else answered[-1]['ans'])]
                                           if answered else [])))
    fu, fst = tl.get("fuel"), tl.get("fuel_state")
    why.append("fut OI: " + (f"{MEAN.get(fu['meaning'], fu['meaning'])} {_sgn(fu['lots'])} lots "
                             + ("LIVE" if fst == "LIVE" else "SPENT" if fst == "KHATAM" else "") if fu else
                             "could not check (a hole in the 5-min window)" if fst == "?" else "no run (bar 500 lots / 5 min)"))
    why.append("cross-index: " + ("could not check" if not sy or sy["dir"] is None else
                                  f"all 3 {ARR[sy['dir']]} in sync" if sy["dir"] else "3 indices mixed")
               + (f" (N {_sgn(sy['ch'][0])} · BN {_sgn(sy['ch'][1])} · SX {_sgn(sy['ch'][2])} / 5 min)"
                  if sy and sy["dir"] is not None else ""))
    tr = r["trade"][i]
    vb, vs = d["verdict"]["BUY"].get(mins[i]), d["verdict"]["SELL"].get(mins[i])
    pts_s = H._sg(f"{tr['pts']:+.0f}") if tr else ""
    why.append("her setup: " + (f"last trigger {tr['t']} {tr['side']} {_fmt(tr['px'])}f · {pts_s} pts"
                                + (f" · {tr['st']}" if tr["st"] else "") if tr else "no trigger yet")
               + f" · band verdict BUY {(vb or {}).get('word', '?')} / SELL {(vs or {}).get('word', '?')}")
    if mins[i] >= "15:00":
        why.append("after 15:00: her practice is no new trades (a reminder, not a rule)")
    ri = next((j for j in range(i, -1, -1) if r["writers"][j]["ev"] == "RISK"), None) if w["state"] == "RISK" else None
    if ri is not None:
        risk = r["writers"][ri]
        up_ = risk["dir"] > 0
        why.append(f"{'TOP' if up_ else 'BOTTOM'} RISK since {mins[ri]}: writers stopped pushing and {'sellers' if up_ else 'buyers'} hit — "
                   f"3-min delta {_sgn(risk['d3'])}, ×{risk['x']} normal")

    # the word
    s_dir = sides_fuel(s) or 0
    w_dirs = {w["dir"] if w["state"] in ("UP", "DOWN", "BACK") else 0, w.get("push") or 0}   # the leg's state, or this minute's push

    def more(dr):
        way = "▲" if dr > 0 else "▼"
        return [lbl for ok, lbl in ((fst == "LIVE" and fu and fu["dir"] == way, "fut run"),
                                    (sp["word"] == "FAST" and sp["dir"] == dr, "speed FAST"),
                                    (bool(sy) and sy["dir"] == dr, "all 3")) if ok]
    nt = next((x for x in r["notrade"] if x["from"] <= mins[i] <= x["to"]), None)
    both_add = (s is not None and s.get("c") == "ADD" and s.get("p") == "ADD") or \
        (w["ce"] is not None and w["ce"] >= WF_L and w["pe"] >= WF_L)
    agree = {dr: ([x for x, ok in (("Sides", s_dir == dr), ("writers ±7", dr in w_dirs)) if ok], more(dr)) for dr in (1, -1)}
    ok = [dr for dr in (1, -1) if agree[dr][0] and agree[dr][1]]
    if blind:
        word, reason = "CAN'T SEE", f"blind since {mins[i]} ({lag} min) — the last read is not carried"
    elif nt and nt["why"] == "can't see":
        word, reason = "NO TRADE", f"can't see: {nt['from']}–{nt['to']} not on the record"
    elif len(ok) == 1:
        word, reason = ("UP" if ok[0] > 0 else "DOWN"), " + ".join(agree[ok[0]][0] + agree[ok[0]][1]) + " agree"
    elif both_add:
        word, reason = "RANGE", "call and put writers both adding"
    elif nt:
        word, reason = "NO TRADE", f"quiet since {nt['since']}"
    else:
        lean = [f"{'▲' if dr > 0 else '▼'}: " + (" + ".join(agree[dr][0] + agree[dr][1]) or "nothing") for dr in (1, -1)]
        word, reason = "NO TRADE", "unclear — writers and flow do not agree (" + " · ".join(lean) + ")"
    v1 = {"word": word, "reason": reason}           # the 29 Oct vote, kept beside the leg for the evening comparison

    # THE LEG (legs.py, merged decision 30 Oct): the word is the leg's state, its lean changes only at PALAT. The vote
    # above flickered UP <-> NO TRADE 8 times in 30 Oct's 11:00-12:10 leg; the leg did not change once.
    LG = d.get("legs") or {}
    row = (LG.get("rows") or [None])[-1] if not LG.get("error") else None
    if row and row.get("t") != mins[i]:
        row = None
    lean = (row or {}).get("lean") or 0
    if not blind and row:
        word = row["word"] + (f" {ARR[lean]}" if lean else "")
        reason = row.get("line") or row["word"]
    why.append(f"call: {word} — {reason}" + (f" · (the vote: {v1['word']})" if row and not blind else ""))
    leg_line = day_line = None
    if row and row.get("leg"):
        g = row["leg"]
        leg_line = (f"leg {ARR.get(g['dir'], '?')} {g.get('quality') or ''} {g['pts']} pts · {g.get('sigma_max') or 0:.1f}σ"
                    + (f" · TOOT {g['toot']}" if g.get("toot") else "") + (f" · fuelled {g['fuelled']}" if g.get("fuelled") else "")
                    + f" · origin {_fmt(g['origin'])}f {g['origin_t']} · extreme {_fmt(g['extreme'])}f {g['extreme_t']}")
        why.insert(1, leg_line)
    if row is not None:
        dd = LG.get("day") or {}
        fl = (dd.get("flips") or [None])[-1]
        fo = (dd.get("fut_oi") or [None])[-1]
        day_line = (f"day: legs flipped {fl} time{'s' if fl != 1 else ''} so far" if fl is not None else "day: flips ?") + \
            (f" · fut OI {fo['word']} {_sgn(fo['lots'])} lots / 30 min" if fo else " · fut OI: no 30-min story yet")
        why.insert(2 if leg_line else 1, day_line)
    elif LG.get("error"):
        why.append(f"leg: could not check — {LG['error']}")

    # the wrong-line, the two scenarios, both expressions (levels s / f)
    nb = [("d2", vw - 2 * sd), ("d1", vw - sd), ("VWAP", vw), ("u1", vw + sd), ("u2", vw + 2 * sd)]
    below = next((x for x in reversed(nb) if x[1] < fut - 3), None)
    above = next((x for x in nb if x[1] > fut + 3), None)
    up_s = (f"▲ if {lv(ce[0]['k'])} CE breaks (BROKEN) with writers ±7 ▲ → " + (lv(ce[1]["k"]) if len(ce) > 1 else "open space"))\
        if ce else "▲ open: no CE wall above in range"
    dn_s = (f"▼ if {lv(pe[0]['k'])} PE breaks (BROKEN) with writers ±7 ▼ → " + (lv(pe[1]["k"]) if len(pe) > 1 else "open space"))\
        if pe else "▼ open: no PE wall below in range"
    g = (row or {}).get("leg") if row and not blind else None
    lines = None
    if g and row["word"] in ("TREND", "HOLD", "WATCH", "PALAT?") and lean:
        import legs as _lg
        U = max(sd or 0, 0.001 * fut)
        q35 = g["extreme"] - lean * _lg.DEEP * g["pts"]
        half = g["extreme"] - lean * max(_lg.REV_FRAC * g["pts"], _lg.REV_U * U)
        lines = {"q35": round(q35, 2), "half": round(half, 2)}     # the faces draw these, never their own copy (Dext 0.9)
        opt, other = ("CE", "PE") if lean > 0 else ("PE", "CE")
        wall = (pe[0] if pe else None) if lean > 0 else (ce[0] if ce else None)
        if row["word"] == "PALAT?":
            wrong = f"back to HOLD on a real new {'high' if lean > 0 else 'low'} past {_fmt(g['extreme'])}f; PALAT at {_fmt(half)}f"
            buyer = f"no new {opt}; a {opt} held tightens to {_fmt(half)}f (the PALAT line)"
            seller = f"no new {other} sale until it holds again"
        else:
            wrong = f"PALAT? if back past {_fmt(q35)}f (0.35 of the leg) · PALAT at {_fmt(half)}f: the lean ends there"
            buyer = (f"hold the {opt}, no new one while WATCH · stop = the PALAT line {_fmt(half)}f" if row["word"] == "WATCH"
                     else f"buy the {opt} on the pullback, not chased · stop = the PALAT line {_fmt(half)}f")
            seller = (f"sell the {other} at / beyond {lv(wall['k'])}: its writers are the leg's floor · same stop" if wall
                      else f"sell the {other}: its writers are the leg's floor · same stop")
    elif row and not blind and row["word"] in ("PALAT", "ROTATION", "OPENING", "NO LEG"):
        wrong = ("ends: a leg that qualifies — after 10:00 ≥ 80 pts with 1.5σ, a TOOT or fuel; before 10:00 ≥ 100 pts and a TOOT")
        buyer = "no lean: buy only at her bands (the zone), never mid-range"
        seller = "no lean: sell outside the band, both sides"
    elif word == "UP":
        wrong = f"wrong if: below {lv(pe[0]['k'])} (the floor) or call writers adding again" if pe else \
            "wrong if: call writers adding again or a 3-min delta >= 2x normal against"
        buyer = f"buy the CE on a pullback to {below[0]} {_fmt(below[1])}f, not chased" if below else "buy the CE on a pullback, not chased"
        seller = f"sell the PE at / below {lv(pe[0]['k'])}: put writers are writing it" if pe else "sell the PE: put writers are writing"
    elif word == "DOWN":
        wrong = f"wrong if: above {lv(ce[0]['k'])} (the cap) or put writers adding again" if ce else \
            "wrong if: put writers adding again or a 3-min delta >= 2x normal against"
        buyer = f"buy the PE on a pullback to {above[0]} {_fmt(above[1])}f, not chased" if above else "buy the PE on a pullback, not chased"
        seller = f"sell the CE at / above {lv(ce[0]['k'])}: call writers are writing it" if ce else "sell the CE: call writers are writing"
    elif word == "RANGE":
        lo_, hi_ = (lv(pe[0]["k"]) if pe else "?"), (lv(ce[0]["k"]) if ce else "?")
        wrong = f"wrong if: a 3-min close outside {lo_} – {hi_}"
        buyer = "no buyer trade mid-range"
        seller = f"sell outside the range: CE at / above {hi_}, PE at / below {lo_} (both sides writing)"
    elif word == "CAN'T SEE":
        wrong = "ends: market data back on the record (book or the saved tape)"
        buyer, seller = "wait: blind, no new trade", "wait: blind, no new sale"
    else:
        wrong = "ends: " + (nt["ends"] if nt else "the writers and one more read agree (FUEL, speed FAST, ALL 3)")
        buyer, seller = "wait: no buyer trade", "wait: no new sale"
    return {"at": mins[i], "word": word, "why": why, "wrong_line": wrong, "up": up_s, "dn": dn_s, "buyer": buyer,
            "seller": seller, "missing": missing, "note": "guidance only: she places every trade herself",
            "lean": lean, "leg": leg_line, "day": day_line, "pause": None if row is None or blind else
            {"line": row.get("line"), "alive": row.get("alive"), "risk": row.get("risk"), "notes": row.get("notes"),
             "missing": row.get("missing")}, "v1": v1, "lines": lines,
            "walls": {"ce": None if not ce else {"k": ce[0]["k"], "f": round(ce[0]["k"] + basis, 2), "oi": ce[0].get("oi"),
                                                 "state": ce[0].get("state")},
                      "pe": None if not pe else {"k": pe[0]["k"], "f": round(pe[0]["k"] + basis, 2), "oi": pe[0].get("oi"),
                                                 "state": pe[0].get("state")}}}


# ---- Task 2: the face's reads, in the brain (jarvis2.html / jarvis2_live.html JS, ported; DAY-2026-10-29 §8 corrections)

ARR = {1: "▲", -1: "▼"}
MEAN = {"shorts cover": "shorts covering", "naye short": "fresh shorts", "naye long": "fresh longs",
        "longs nikal rahe": "longs closing"}
FAST, SLOW = 2.0, 0.5                         # SPEED: x its own median [I]
SYNC_PTS = (10, 25, 35)                       # ALL 3: NIFTY fut / BANKNIFTY / SENSEX in 5 min [I]
WF_L, WF_STOP = 10.0, -2.0                    # WRITER FLOW ±7: a leg's 3-min L; the covering side "stopped" at >= -2L [I]
RISK_X, RISK_WIN = 2.0, 9                     # TOP / BOTTOM RISK: 3-min delta >= 2x its day median against, within 9 min [I]
RISK_HOLD, RISK_CONF = 9, 0.3                 # G2: RISK lasts 9 min unless price went 0.3 step against the leg since [I]
BLIND_MIN = 2                                 # P0: the newest minute more than 2 min behind the clock = blind [I]
FIGHT_AWAY, FIGHT_AWAY_MIN = 2, 15            # P2: a fight's wall > 2 steps from price for 15 min is left behind [I]
MANAGE_PTS, MANAGE_WIN, MANAGE_GAP = 15, 46, 6
QUIET_MIN = 20


def days() -> dict:
    """Her replay calendar (31 Oct): the days a replay can build, per index -- the 1-second book AND the chain both on the
    record (plain or gzipped); file names only, no build. A day can still be partial (16 Oct: 32 min): the replay names
    its own span."""
    import glob
    import re
    import book_log

    def have(pat):
        return {m.group(1) for p in glob.glob(pat) if (m := re.search(r"_(\d{4}-\d\d-\d\d)\.jsonl", p))}
    return {i: sorted(have(os.path.join(book_log.DIR, f"book_{i}_*.jsonl*"))
                      & have(os.path.join(str(chain_live.CHAIN_DIR), f"chain_{i}_*.jsonl*"))) for i in ("NIFTY", "SENSEX")}


def calls(d: dict) -> list:
    """Her backtest replay (31 Oct): THE ONE CALL as it stood at every minute -- call() on the frame cut at minute i (the
    per-minute series, reads and leg rows to i; holes and health as known then), so a scrubbed replay shows what Jarvis
    said at 11:14, not the close's call. The card's fields only. A replay has no clock, so CAN'T SEE never shows here: a
    minute missing from the record is simply absent (health names the hole)."""
    mins, N = d["mins"], len(d["mins"])

    def cut(v, i):
        return v[:i + 1] if isinstance(v, list) and len(v) == N else v

    lg, out = d.get("legs") or {}, []
    for i in range(N):
        v = {k: cut(x, i) for k, x in d.items()}
        v["reads"] = {k: cut(x, i) for k, x in d["reads"].items()}
        v["legs"] = dict(lg, rows=cut(lg.get("rows") or [], i),
                         day={k: cut(x, i) for k, x in (lg.get("day") or {}).items()})
        v["holes"] = [h for h in d.get("holes") or () if h[0][:5] <= mins[i]]
        v["upto"] = hm(_m(mins[i]) + 1)
        v["health"] = health(v, d["health"].get("bnf_chain_readable"))
        c = call(v)
        out.append({k: c[k] for k in ("at", "word", "lean", "leg", "day", "wrong_line", "buyer", "seller")}
                   | {"pause": c["pause"] and {"line": c["pause"].get("line")}})
    return out


def sides_fuel(s):
    """The writers' fuel direction of one Sides slot -> 1 / -1 / None: REAL / BACKED by its fuel side, and SQUEEZE (the
    move's own writers covering) only while the other side is FLAT -- call writers covering with puts flat = ▲, the
    mirror ▼ (A176, decided as the trader: 29 Oct's afternoon driver, DAY §1). Both sides covering is not counted."""
    if not s or s.get("fuel_side") not in ("ce", "pe"):
        return None
    dr = 1 if s["fuel_side"] == "ce" else -1
    if s.get("word") in ("REAL", "BACKED"):
        return dr
    if s.get("word") == "SQUEEZE" and (s.get("p") if dr > 0 else s.get("c")) == "FLAT":
        return dr
    return None


def wf_push(ce, pe):
    """WRITER FLOW ±7 as writers' fuel -> 1 / -1 / None: a covering side <= -10L / 3 min while the other side is not
    covering against it (>= -2L), which holds DAY §5's two-leg UP (CE <= -10L with PE >= +10L) and adds the covering side
    alone (A176). Fuel only: the ±7 STATES (UP / PAUSED / BACK / RISK) keep the two-leg rule."""
    if ce is None or pe is None:
        return None
    return 1 if ce <= -WF_L and pe >= WF_STOP else -1 if pe <= -WF_L and ce >= WF_STOP else None


def _med(xs):
    """The face's median (jarvis2.html `med`): the sorted values' element at len // 2."""
    s = sorted(x for x in xs if x is not None and math.isfinite(x))
    return s[len(s) // 2] if s else None


def _fmt(x):
    """Math.round(x).toLocaleString("en-IN"): 1,23,456."""
    n = int(math.floor(x + 0.5))
    s = str(abs(n))
    if len(s) > 3:
        h, s = s[:-3], s[-3:]
        while len(h) > 2:
            h, s = h[:-2], h[-2:] + "," + s
        s = h + "," + s
    return ("-" if n < 0 else "") + s


def _sgn(x):
    return ("+" if x >= 0 else "−") + _fmt(abs(x))


def reads(d: dict) -> dict:
    """The per-minute reads of one frame (causal: minute i reads minutes <= i only) -> {speed, signs, sync, writers,
    manage, trade, notrade}. The face renders these; its own JS reads are only the fallback for old JSON files."""
    mins, N = d["mins"], len(d["mins"])
    fut, fo, fhi, flo, tl = d["fut"], d["fo"], d["fhi"], d["flo"], d["timeline"]
    flow = d.get("flow") or d["delta"]
    vol = [f if f is not None else v for f, v in zip(d["fvol"], d.get("vol") or [None] * N)]
    bar = d.get("bar") or 500
    ix = {m: i for i, m in enumerate(mins)}

    def s3(k):
        """The signed 3-min flow ending at minute k; None when any of its minutes is missing (never a zero)."""
        xs = flow[k - 2:k + 1] if k >= 2 else [None]
        return None if any(x is None for x in xs) else sum(xs)

    # SPEED: |3-min delta| against its own median so far [I]
    speed, hist = [], []
    for i in range(N):
        x3 = s3(i)
        m = _med(hist) if len(hist) >= 10 else None
        x = abs(x3) / m if x3 is not None and m else None
        speed.append({"x": None if x is None else round(x, 2), "dir": None if x3 is None else (1 if x3 >= 0 else -1),
                      "word": "?" if x is None else "FAST" if x >= FAST else "SLOW" if x <= SLOW else "NORMAL", "d3": x3,
                      "why": None if x is not None else ("flow missing (Dext and the book)" if x3 is None and i >= 2
                                                          else "warming up: needs 10 bars of history")})
        if x3 is not None:
            hist.append(abs(x3))

    # ALL 3 IN SYNC: the three moved >= 10 / 25 / 35 pts the same way in 5 min [I]
    def sync_at(i):
        if i < 5 or not d.get("bnf"):
            return None
        ch = [None if a[i] is None or a[i - 5] is None else round(a[i] - a[i - 5], 2) for a in (fut, d["bnf"], d["sx"])]
        if None in ch:
            return {"dir": None, "ch": ch}
        up, dn = all(c >= n for c, n in zip(ch, SYNC_PTS)), all(c <= -n for c, n in zip(ch, SYNC_PTS))
        return {"dir": 1 if up else -1 if dn else 0, "ch": ch}
    sync = [sync_at(i) for i in range(N)]

    # Sides (the Board's options-side fuel) and WRITER FLOW ±7 (her 29 Oct asks), reused as the face read them
    def sides_at(i):
        s = None
        for x in d.get("sides") or ():
            if x.get("t") and x["t"] <= mins[i]:
                s = x
            elif x.get("t") and x["t"] > mins[i]:
                break
        return s

    def opt_fuel(i):
        s = sides_at(i)
        return s if sides_fuel(s) else None

    def wf(i):
        c, p = (d.get("wf_ce") or [None] * N)[i], (d.get("wf_pe") or [None] * N)[i]
        return None if c is None or p is None else (c, p)

    def wf_fuel(i):
        w = wf(i)
        return None if not w else 1 if w[0] <= -WF_L and w[1] >= WF_L else -1 if w[1] <= -WF_L and w[0] >= WF_L else None

    def wf_leg(i):
        """G3 (30 Oct): the ±7 leg's direction and the side that drives it -> (dir, "both" | "calls" | "puts") or None.
        Both: DAY §5's two-leg rule (CE <= -L with PE >= +L, mirror ▼). One side alone: its covering (CE <= -L while PE
        neither builds a leg nor covers against it) or its building (PE >= +L while CE neither covers a leg nor adds
        against it); mirror ▼. 29 Oct (+236 pts) had 18 two-leg minutes and the state read UP for 33 in all."""
        w = wf(i)
        if not w:
            return None
        c, p = w
        if c <= -WF_L and p >= WF_L:
            return 1, "both"
        if p <= -WF_L and c >= WF_L:
            return -1, "both"
        if c <= -WF_L and WF_STOP <= p < WF_L:
            return 1, "calls"                                    # call writers covering, puts not covering against
        if p <= -WF_L and WF_STOP <= c < WF_L:
            return -1, "puts"
        if p >= WF_L and -WF_L < c <= -WF_STOP:
            return 1, "puts"                                     # put writers adding, calls not adding against
        if c >= WF_L and -WF_L < p <= -WF_STOP:
            return -1, "calls"
        return None

    # WRITER FLOW ±7 states (DAY §5): UP / DOWN when a leg starts (>= 6 min after the last), PAUSED when its driving
    # side(s) stop -- the covering side back over -2L, the building side under half its leg peak -- BACK when the fuel
    # returns, RISK when the pause meets a 3-min delta >= 2x its day median against within 9 min. `legs` says which side
    # drives (G3). G2 (30 Oct): RISK is an event, not a state for the rest of the day (29 Oct it sat 10:38-12:50 on a day
    # that closed +236; 28 Oct from 13:19 to the close). It ends ("RISK OFF", back to PAUSED) at a new extreme the leg's
    # way, or after RISK_HOLD minutes unless price has gone RISK_CONF of a strike step against the leg since.
    writers, seen = [], []
    on, legs, peak, last_on, paused, paused_at, warned, state = None, None, 0.0, -99, False, -99, False, None
    ext, risk_at, risk_px, risk_ext = None, None, None, None
    step = d.get("step") or 50
    for i in range(N):
        dd, w, ev = s3(i), wf(i), None
        if dd is not None:
            seen.append(abs(dd))
        row = {"state": None, "dir": None, "ce": None if w is None else w[0], "pe": None if w is None else w[1], "ev": None,
               "push": None if w is None else wf_push(*w), "legs": legs}
        hi_, lo_ = fhi[i] if fhi[i] is not None else fut[i], flo[i] if flo[i] is not None else fut[i]
        if on and hi_ is not None and lo_ is not None:
            ext = (max(ext, hi_) if on > 0 else min(ext, lo_)) if ext is not None else (hi_ if on > 0 else lo_)
        if state == "RISK" and risk_at is not None:
            new_ext = risk_ext is not None and ext is not None and on * (ext - risk_ext) > 0
            held_against = fut[i] is not None and risk_px is not None and on * (fut[i] - risk_px) <= -RISK_CONF * step
            if new_ext or (i - risk_at >= RISK_HOLD and not held_against):
                state, ev, risk_at = "PAUSED", "RISK OFF", None
        if i < 3 or w is None:
            row.update(state=state, dir=on, ev=ev)
            writers.append(row)
            continue
        lg = wf_leg(i)
        f, up = (lg[0] if lg else None), (on or 0) > 0
        if f and on != f and i - last_on >= 6:
            on, legs, peak, last_on, paused, warned = f, lg[1], (w[1] if f > 0 else w[0]), i, False, False
            state = ev = "UP" if f > 0 else "DOWN"
            ext, risk_at = (hi_ if f > 0 else lo_), None
        elif on:
            if f == on and paused:                             # a new pause after this may warn again: RISK expires now
                paused, warned, ev, legs, risk_at = False, False, "BACK", lg[1], None
                state = "UP" if on > 0 else "DOWN"
            else:
                if not paused and lg and lg[0] == on and lg[1] == "both":
                    legs = "both"                                # the other side joined: a two-leg push from here
                build, cover = (w[1], w[0]) if up else (w[0], w[1])
                peak = max(peak, build)
                med = sorted(seen)[len(seen) // 2] if len(seen) >= 10 else None
                hit = dd is not None and bool(med) and on * dd <= -RISK_X * med
                covers = legs == "both" or legs == ("calls" if up else "puts")     # the leg's covering side drives it
                builds = legs == "both" or legs == ("puts" if up else "calls")     # its building side drives it
                stopped = (not covers or cover >= WF_STOP) and (not builds or build < peak / 2)
                if not paused and stopped and (dd is None or on * dd <= 0):
                    paused, paused_at = True, i
                    if not hit or warned:                    # (a hit already warned of reads as the pause it is)
                        state = ev = "PAUSED"
                if paused and not warned and i - paused_at <= RISK_WIN and hit:
                    warned, state, ev = True, "RISK", "RISK"
                    risk_at, risk_px, risk_ext = i, fut[i], ext
                    row.update(d3=dd, x=round(abs(dd) / med, 1))
        row.update(state="BACK" if ev == "BACK" else state, dir=on, ev=ev, legs=legs)
        writers.append(row)

    # TOP / BOTTOM SIGNS n/3 at a fresh 30-min extreme, on her 3-min bars from 09:15; spoken at 2/3, noted (not called)
    # while ANY fuel still drives into the extreme (DAY §8 item 3)
    def bar3(b):
        a = b - 2
        if a < 0:
            return None
        ds, vs = flow[a:b + 1], vol[a:b + 1]
        h, lo = max(fhi[a:b + 1]), min(flo[a:b + 1])
        v = None if None in vs else sum(vs)
        return {"a": a, "b": b, "o": fo[a], "c": fut[b], "h": h, "l": lo, "d": None if None in ds else sum(ds), "v": v,
                "eff": None if v is None else v / max(h - lo, 0.5)}

    def known_at(p):
        """The minute index from which a push's answer is known (the face's ix(held_at || am) + 1), or None."""
        k = ix.get(p.get("held_at") or p.get("am") or "")
        return None if k is None else k + 1

    miss = set(d.get("chain_missing") or ())

    def break_at(p):
        """From when a BROKEN counts as fuel (A176, decided as the trader): its push minute when the answer was read late
        through a chain hole (a chain-missing minute between the push and its confirmation), else the minute it became
        known -- the market broke it then; only our reading was late."""
        conf = p.get("held_at") or p.get("am")
        if conf and p["t"] in ix and any(p["t"] < m_ <= conf for m_ in miss):
            return ix[p["t"]] + 1
        return known_at(p)

    pushes = [p for p in d.get("pushes") or () if not p.get("artifact")]
    signs, effs = [], []
    for b in range(2, N, 3):
        B = bar3(b)
        m = _med(effs) if len(effs) >= 6 else None
        if B["eff"] is not None:
            effs.append(B["eff"])
        lo0 = max(0, B["a"] - 30)
        if B["a"] - lo0 < 10:
            continue
        hi30, lo30 = max(fhi[lo0:B["a"]]), min(flo[lo0:B["a"]])
        for is_high in (True, False):
            if (B["h"] < hi30) if is_high else (B["l"] > lo30):
                continue
            sg, P = [], [q for q in (bar3(b - 6), bar3(b - 3)) if q]
            if B["d"] is not None and ((B["c"] < B["o"] and B["d"] > 0) if is_high else (B["c"] > B["o"] and B["d"] < 0)):
                sg.append(f"{'red candle, green delta' if is_high else 'green candle, red delta'} {_sgn(B['d'])}")
            if m and B["eff"] is not None and B["eff"] >= 2 * m:
                sg.append(f"absorption: {_fmt(B['v'])} lots / {B['h'] - B['l']:.0f} pts (effort ×{B['eff'] / m:.1f})")
            pk = max([(1 if is_high else -1) * q["d"] for q in P if q["d"] is not None] + [0])
            if pk > 0 and B["d"] is not None and (B["d"] if is_high else -B["d"]) < pk / 2:
                sg.append("exhaustion: delta " + " → ".join(_sgn(q["d"]) for q in P if q["d"] is not None) + f" → {_sgn(B['d'])}")
            if len(sg) < 2:
                continue                                  # one sign alone is noise: it speaks at 2 of 3
            way, sd = ("▲" if is_high else "▼"), (1 if is_high else -1)
            row, drive = tl[b] or {}, []
            fu = row.get("fuel")
            spent = any(r.get("khatam") and r["dir"] == way and abs(r["lots"]) >= 2 * bar and r["khatam"] in ix
                        and 0 <= b - ix[r["khatam"]] <= 10 for r in d.get("runs") or ())
            if row.get("fuel_state") == "LIVE" and fu and (fu["dir"] == "▲") == is_high and not spent:
                drive.append(f"fut {MEAN.get(fu['meaning'], fu['meaning'])} {_sgn(fu['lots'])}")
            of = opt_fuel(b)
            if of and (of["fuel_side"] == "ce") == is_high:
                drive.append(f"{'call' if of['fuel_side'] == 'ce' else 'put'} writers covering · Sides {of['word']}")
            w = wf(b)
            if wf_fuel(b) == sd:
                drive.append(f"writers ±7 {way}: CE {H._l(w[0])} · PE {H._l(w[1])}")
            elif w and wf_push(*w) == sd:
                drive.append(f"{'call' if is_high else 'put'} writers covering ±7: {'CE' if is_high else 'PE'} "
                             f"{H._l(w[0] if is_high else w[1])} / 3 min")
            elif w and (w[1] if is_high else w[0]) >= WF_L:
                drive.append(f"{'put writers lifting the floor: PE' if is_high else 'call writers lowering the cap: CE'} "
                             f"{H._l(w[1] if is_high else w[0])} / 3 min")
            brk = [p for p in pushes if p["dir"] == sd and p.get("held") == "TOOT" and known_at(p) is not None
                   and known_at(p) <= b + 1 and 0 <= b + 1 - break_at(p) <= 10]
            if brk:
                drive.append(f"BROKEN {_fmt(brk[-1]['k'])}s {brk[-1]['side']} ({brk[-1].get('held_at') or brk[-1]['am']})")
            signs.append({"b": b, "t": mins[b], "at": mins[b + 1] if b + 1 < N else hm(_m(mins[b]) + 1), "isHigh": is_high,
                          "n": len(sg), "items": sg, "driving": bool(drive), "drive": drive, "px": B["h"] if is_high else B["l"],
                          "speed": speed[b]})

    # MANAGE: after each of her triggers, at her 3-min closes for 45 min; on change, >= 6 min apart; at most 4 lines.
    # Judged against price FIRST (GAPS §1, the -120 pts HOLD): AGAINST YOU at <= -15 pts whatever else says.
    def band(i):
        w_, s_ = d["vwap"][i], d["sd"][i]
        return [("d2", w_ - 2 * s_), ("d1", w_ - s_), ("VWAP", w_), ("u1", w_ + s_), ("u2", w_ + 2 * s_)]

    def trail_band(i, dr):
        bs = band(i)
        got = next((x for x in bs if x[1] > fut[i] + 3), None) if dr < 0 else \
            next((x for x in reversed(bs) if x[1] < fut[i] - 3), None)
        return None if got is None else [got[0], round(got[1], 1)]

    def judge(pts, withm, against):
        if pts <= -MANAGE_PTS or (pts < 0 and len(against) >= 2):
            return "AGAINST YOU"
        if pts >= MANAGE_PTS and against:
            return "BOOK / TRAIL TIGHT"
        if pts >= MANAGE_PTS and withm:
            return "HOLD"
        return None

    def sides_of(b, dr):
        withm, against = [], []
        sp, sy, row = speed[b], sync[b], tl[b] or {}
        if sp["word"] == "FAST":
            (withm if sp["dir"] == dr else against).append(f"speed {ARR[sp['dir']]} ×{sp['x']:.1f}")
        if sy and sy["dir"]:
            (withm if sy["dir"] == dr else against).append(f"all 3 {ARR[sy['dir']]}")
        fu = row.get("fuel")
        if row.get("fuel_state") == "LIVE" and fu:
            (withm if (fu["dir"] == "▲") == (dr > 0) else against).append(f"fuel {MEAN.get(fu['meaning'], fu['meaning'])}")
        wff = wf_push(*wf(b)) if wf(b) else None
        if wff:
            (withm if wff == dr else against).append(f"writers ±7 {ARR[wff]}")
        of = opt_fuel(b)
        if of:
            (withm if (of["fuel_side"] == "ce") == (dr > 0) else against).append(
                f"{'call' if of['fuel_side'] == 'ce' else 'put'} writers covering")
        sg = next((s for s in signs if not s["driving"] and s["b"] == b and s["isHigh"] == (dr > 0)), None)
        if sg:
            against.append(f"{'top' if sg['isHigh'] else 'bottom'} signs {sg['n']}/3")
        return withm, against

    triggers = [z for z in d.get("zone") or () if not z.get("kind") and z.get("px") is not None and z["t"][:5] in ix]
    manage = []
    for z in triggers:
        ti, dr = ix[z["t"][:5]], (-1 if z["side"] == "SELL" else 1)
        was, last_at, n = None, -99, 0
        for b in range(ti + 2, min(N, ti + MANAGE_WIN)):
            if n >= 4:
                break
            if (b + 1) % 3:
                continue                                  # read at her 3-min closes
            pts = dr * (fut[b] - z["px"])
            withm, against = sides_of(b, dr)
            st = judge(pts, withm, against)
            if not st or st == was or b - last_at < MANAGE_GAP:
                continue
            was, last_at, n = st, b, n + 1
            manage.append({"at": mins[b + 1] if b + 1 < N else hm(_m(mins[b]) + 1), "b": b, "t": z["t"][:5],
                           "side": z["side"], "px": z["px"], "st": st, "pts": round(pts, 1), "trail": trail_band(b, dr),
                           "with": withm, "against": against, "note": "guidance only: you place and move your own stop"})

    # the LAST TRIGGER card, per minute: the points now, the last MANAGE word said, re-judged against price now
    trade = []
    for i in range(N):
        z = next((q for q in reversed(triggers) if ix[q["t"][:5]] <= i), None)
        if z is None:
            trade.append(None)
            continue
        dr = -1 if z["side"] == "SELL" else 1
        pts, age = dr * (fut[i] - z["px"]), i - ix[z["t"][:5]]
        said = next((m_ for m_ in reversed(manage) if m_["t"] == z["t"][:5] and m_["side"] == z["side"] and m_["b"] + 1 <= i), None)
        st = "AGAINST YOU" if pts <= -MANAGE_PTS else (said or {}).get("st")
        trade.append({"t": z["t"][:5], "side": z["side"], "px": z["px"], "band": z.get("band"), "pts": round(pts, 1), "age": age,
                      "st": st, "said": (said or {}).get("st"), "window": age < MANAGE_WIN, "trail": trail_band(i, dr)})

    # NO TRADE: 20 quiet minutes (no break, no fuel, no trigger, writers not pushing) -> quiet; a data hole -> can't see
    loud = {1}
    for p in pushes:
        if p.get("ans") in SAID and known_at(p) is not None:
            loud.add(known_at(p))
    big = set()                                   # a run speaks once its lots so far reach 2x the bar, and at its KHATAM
    for i in range(N):
        fu = (tl[i] or {}).get("fuel")
        if fu and abs(fu["lots"]) >= 2 * bar and (fu["start"] not in big or fu["khatam"]):
            big.add(fu["start"])
            loud.add(i + 1)
    for f in d.get("fights") or ():
        for t, word, _ in f["stamps"]:
            if t in ix and (word.startswith(("NAYA", "PIN")) or (word == "DEEWAR" and f["id"] > 0)):
                loud.add(ix[t] + 1)
    loud.update(ix[z["t"][:5]] + 1 for z in triggers)
    loud.update(s["b"] + 1 for s in signs if not s["driving"])
    loud.update(m_["b"] + 2 for m_ in manage if m_["st"] != "HOLD")
    loud.update(i + 1 for i, w in enumerate(writers) if w["ev"] in ("UP", "DOWN", "RISK"))
    was = None
    for i in range(N):
        s = opt_fuel(i)
        on_ = s["fuel_side"] if s else None
        if on_ and on_ != was:
            loud.add(i + 1)
        was = on_
    blind = set()
    fs = d.get("flow_src") or [None] * N
    for a, b_ in d.get("holes") or ():               # a fill replay (31 Oct) has a hole's minutes back -- fut from the tape,
        blind.update(i for i, m_ in enumerate(mins)   # OI from the chain backfill: blind there only if the flow is gone too
                     if a[:5] <= m_ <= b_[:5] and not (d.get("fill") and fs[i]))
    blind.update(ix[m_] for m_ in d.get("chain_missing") or () if m_ in ix)
    nt, last_loud = [None] * N, 0
    for i in range(N):
        if i in blind:
            nt[i] = ("can't see", mins[i])
        if i in loud:
            last_loud = i
            continue
        if nt[i] is None and (tl[i] or {}).get("fuel_state") != "LIVE" and writers[i]["state"] not in ("UP", "DOWN", "BACK") \
                and i - last_loud >= QUIET_MIN:
            nt[i] = ("quiet", mins[last_loud])
    notrade, i = [], 0
    while i < N:
        if nt[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < N and nt[j + 1] is not None and nt[j + 1][0] == nt[i][0]:
            j += 1
        notrade.append({"from": mins[i], "to": mins[j], "why": nt[i][0], "since": nt[i][1],
                        "ends": "FUEL >= 500 lots / 5 min, writers ±7 pushing, or a BREAK" if nt[i][0] == "quiet"
                        else "the record resumes"})
        i = j + 1
    return {"speed": speed, "signs": signs, "sync": sync, "writers": writers, "manage": manage, "trade": trade,
            "notrade": notrade}
