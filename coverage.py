"""coverage.py -- COVERAGE (decode-loop spec §5.1): for one index, what each source could and could not see today, and why.

One row per finding: {"src", "kind", "text", "tag"}. `kind` is one of THREE ABSENCES, never merged (CLAUDE.md rule 6),
plus what was seen:
    ok      seen -- and how (e.g. "chain 09:15-10:10 REST-rebuilt [I]")
    none    checked, nothing there ("GC: no bar missing")
    cnc     could not check ("GC 11:15 bar nahi aaya", "fut ticks begin 10:11")
    hidden  not shown, on purpose ("PDH/PDL: not shown in a replay")
Anything that depends on a missing input shows "?" on its own number, never zero; this list says where the holes are.
Pure: the caller hands in THE READ's arrays (read.from_v2), the card, the day's bar rows and `now`.
"""
from __future__ import annotations

import read

OPEN_S, CLOSE_S, BAR = 33300, 55800, 300
CHAIN_GAP, TICK_GAP = 120, 120               # seconds without a chain row / a futures tick that count as a hole
CC = read.CC
hm = read.hm


def _row(src, kind, text, tag="M"):
    return {"src": src, "kind": kind, "text": text, "tag": tag}


def _holes(secs, lo, hi, gap):
    """[(from, to)] stretches longer than `gap` with no timestamp, inside [lo, hi]."""
    out, prev = [], lo
    for s in secs:
        if s < lo:
            continue
        if s > hi:
            break
        if s - prev > gap:
            out.append((prev, s))
        prev = s
    if hi - prev > gap:
        out.append((prev, hi))
    return out


def _spans(slots):
    """Consecutive 5-min slot starts -> "11:15" / "11:15–11:25" strings."""
    out, run = [], []
    for s in sorted(slots):
        if run and s - run[-1] != BAR:
            out.append(run)
            run = []
        run.append(s)
    if run:
        out.append(run)
    return [hm(r[0]) if len(r) == 1 else f"{hm(r[0])}–{hm(r[-1])}" for r in out]


def bar_gaps(rows, end):
    """For a source's 5-min bar rows: (missing slot starts from 09:15 to the last slot closed by `end`, slots whose
    bar carries no open/close, partial slots). `end` = sec of day."""
    have, noprice, part = set(), set(), set()
    for r in rows or ():
        t = r.get("t") if isinstance(r, dict) else None
        if not isinstance(t, (int, float)) or isinstance(t, bool):
            continue
        s = int(t // 1000 + 19800) % 86400
        if not OPEN_S <= s < CLOSE_S or s + BAR > end:
            continue
        have.add(s)
        if r.get("o") is None or r.get("c") is None:
            noprice.add(s)
        if r.get("partial"):
            part.add(s)
    want = set(range(OPEN_S, min(end, CLOSE_S) - BAR + 1, BAR))
    return sorted(want - have), sorted(noprice), sorted(part)


def build(idx, X, card, ux_rows, gc_rows=None, now=None, live=False, ref=None, ref_why=None, basis=None,
          levels=None, kind=None, kind_n=None):
    """COVERAGE rows for one index. gc_rows None = GoCharting does not exist for this index (the extension reads
    NIFTY only). now = sec of day (None = the recorded day: the last chain row)."""
    out = []
    ts = X.get("t") or []
    end = now if now is not None else (ts[-1] if ts else OPEN_S)
    end = min(end, CLOSE_S)
    # ---- the chain (OI, writers) ----
    if not ts:
        out.append(_row("CHAIN", "cnc", CC + "no chain row recorded yet today"))
    else:
        bf = X.get("bf") or 0
        first_rec = ts[bf] if bf < len(ts) else None
        if bf:
            out.append(_row("CHAIN", "ok", f"OI {hm(ts[0])}–{hm(ts[bf - 1])} REST-rebuilt, recorded from "
                                            f"{hm(first_rec) if first_rec is not None else '—'}", "I"))
        elif ts[0] > OPEN_S + 180:
            out.append(_row("CHAIN", "cnc", CC + f"chain rows begin {hm(ts[0])} and no REST rebuild landed"))
        holes = [h for h in _holes(ts[bf:], first_rec if first_rec is not None else OPEN_S, end, CHAIN_GAP)
                 if h[0] >= (first_rec or OPEN_S)]
        if holes:
            out.append(_row("CHAIN", "cnc", CC + "chain gap " + " · ".join(f"{hm(a)}–{hm(b)}" for a, b in holes[:3])))
        if live and now is not None and now - ts[-1] > CHAIN_GAP and now < CLOSE_S:
            out.append(_row("CHAIN", "cnc", CC + f"last chain row {hm(ts[-1])}, {(now - ts[-1]) // 60} min ago"))
        e = (card.get("w") or {}).get("edge")
        if e is not None:
            out.append(_row("CHAIN", "cnc", CC + f"strike window edge: the nine read ATM ±{max(e, 0)} only"))
    # ---- the future's ticks (FLOW, basis, the day's fut high / low) ----
    secs = [b[0] for b in X.get("bars") or ()]
    if not secs:
        out.append(_row("FUT", "cnc", CC + "no futures tick yet (they begin when the server does)"))
    else:
        if secs[0] > OPEN_S + BAR:
            pre = (card.get("f") or {}).get("gc")
            out.append(_row("FUT", "cnc", CC + f"fut ticks begin {hm(secs[0])}" +
                            (f"; FLOW to {pre} from GoCharting bars" if pre else "; nothing from 09:15")))
        holes = _holes(secs, secs[0], end, TICK_GAP)
        if holes:
            out.append(_row("FUT", "cnc", CC + "fut ticks missing " + " · ".join(f"{hm(a)}–{hm(b)}" for a, b in holes[:3])))
        elif secs[0] <= OPEN_S + BAR:
            out.append(_row("FUT", "none", "fut ticks: checked, no gap over 2 min"))
    # ---- GoCharting (NIFTY only) ----
    if gc_rows is None:
        out.append(_row("GC", "cnc", CC + "GoCharting reads NIFTY only: this index's flow is one source (Upstox)"))
    elif not gc_rows:
        out.append(_row("GC", "cnc", CC + "no GoCharting bar recorded today (tab closed?)"))
    else:
        miss, noprice, _ = bar_gaps(gc_rows, end)
        last = max(int(r["t"] // 1000 + 19800) % 86400 for r in gc_rows if isinstance(r.get("t"), (int, float)))
        inside = [s for s in miss if s < last]
        after = [s for s in miss if s > last]
        if inside:
            out.append(_row("GC", "cnc", CC + "GC " + " · ".join(_spans(inside)) + " bar nahi aaya"))
        if after:
            out.append(_row("GC", "cnc", CC + f"GC bars end {hm(last)} (tab band?)"))
        if noprice:
            out.append(_row("GC", "cnc", CC + "GC " + " · ".join(_spans(noprice)[:3]) + " open/close nahi (footprint only)",
                            "M"))
        if not miss and not noprice:
            out.append(_row("GC", "none", "GC: checked, no bar missing"))
    # ---- Upstox 5-min bars (the ranks' second source; PRICE's bars) ----
    miss, _, part = bar_gaps(ux_rows, end)
    part = [s for s in part if s != OPEN_S]                     # the 09:15 bar is partial every day (start ~09:17)
    if not ux_rows:
        out.append(_row("UX", "cnc", CC + "no Upstox 5-min bar yet"))
    else:
        if miss:
            out.append(_row("UX", "cnc", CC + "UX " + " · ".join(_spans(miss)[:3]) + " bar nahi"))
        if part:
            out.append(_row("UX", "cnc", CC + "UX " + " · ".join(_spans(part)[:3]) + " adhoora (partial)"))
        if not miss and not part:
            out.append(_row("UX", "none", "UX: checked, no bar missing"))
    # ---- the rank reference ----
    if ref is None:
        out.append(_row("RANK", "cnc", CC + (ref_why or "no rank reference for today")))
    else:
        R = ref.get("read") or {}
        nd = {k: len(v.get("days") or ()) for k, v in (R.get("marks") or {}).items()}
        txt = f"rank ref < {ref.get('before')} · " + " · ".join(f"{k} {n} din" for k, n in nd.items())
        out.append(_row("RANK", "ok" if R else "cnc", txt if R else CC + "the reference has no read section (old build)"))
        if ref.get("stale_from"):
            out.append(_row("RANK", "cnc", CC + f"reference is {ref['stale_from']}'s while today's builds"))
        if kind and kind != "NORMAL":
            out.append(_row("RANK", "ok", f"{kind} din: ranked only against {kind} days"
                                          + (f" ({kind_n} din)" if kind_n is not None else "")))
    # ---- the basis (fut | spot) ----
    if basis is not None:
        if not basis.get("ok"):
            out.append(_row("BASIS", "cnc", CC + (basis.get("why") or "basis implausible") + " -- fut levels ?", "I"))
        elif basis.get("unusual"):
            out.append(_row("BASIS", "ok", basis.get("why") or "basis unusual, options confirm", "M"))
    # ---- levels (yesterday's) ----
    if not live:
        out.append(_row("LEVELS", "hidden", "not shown -- kal ke PDH/PDL/PDC replay mein nahi"))
    elif not levels:
        out.append(_row("LEVELS", "cnc", CC + "yesterday's levels have not landed (war map daily candles)"))
    # ---- writing vs buying (D2) ----
    wb = card.get("wb") or {}
    if wb.get("why"):
        out.append(_row("D2", "cnc", wb["why"], "I"))
    # ---- QUIT events ----
    if not [e for e in card.get("events") or () if e.get("kind") == "QUIT"]:
        out.append(_row("QUIT", "none", "QUIT: checked, aaj koi strike nahi bhaga"))
    return out
