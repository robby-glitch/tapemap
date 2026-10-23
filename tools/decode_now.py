"""tools/decode_now.py -- Claude's live read instrument: the TRAJECTORIES, not just the levels, for NIFTY / BANKNIFTY /
SENSEX at now, or at a past minute of today cut causally. Read-only and terminal-only: it reads the recorders' files,
never calls the server (no localhost) and writes nothing.

    python tools/decode_now.py              now
    python tools/decode_now.py --at 09:58   exactly what the files held at 09:58:00 today: 5-min bars closed by then,
                                            chain rows recorded before then, zone rows whose 3-min bar had closed, log
                                            rows written by then

FACTS ONLY: no verdict word, no probability, no hit rate. Every read is the stack's own: faded.py (delta against the
leg, CVD, the PE / CE lead, FADE-D's conditions), read.py READ-2 (word, src, JAGAH, FUEL), hold2.pushes, trigger_log's
zone rows (non-outcome fields), the forward log's FADE / RIDE / FADE-D rows. PDH / PDL live only in the server's memory,
so JAGAH here is computed without them (and says so).

ONE SOURCE OF TRUTH (2026-10-22): the reads are decode.py's, gathered by server._decode_all -- the very code behind the
app's DECODE block on /api/read and frame.decode -- at now's last 5-min close; the block (call, lines, setups) is printed
last. FADE's live state needs the zone machine's 3-min band bars: a past minute of TODAY has none until the end-of-day
cache (data/backtest) exists, so FADE reads "—" there; --day replays have it.
"""
import argparse
import bisect
import datetime
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # tapemap/
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import confluence_log    # noqa: E402
import decode            # noqa: E402
import faded             # noqa: E402
import read              # noqa: E402

INDICES = ("NIFTY", "BANKNIFTY", "SENSEX")
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
OPEN_S, CLOSE_S = 33300, 55800
hm = faded.hm
ARROW = {1: "▲", -1: "▼", 0: "", None: ""}


def _f(x, nd=1, sign=True):
    return "?" if x is None else f"{x:+,.{nd}f}" if sign else f"{x:,.{nd}f}"


# ---- the reads: decode.py's (one source of truth with the app's DECODE block) -----------------------------------------

delta_rows, cvd_read, leg_of, lead_minutes, lead_read, fade_now = (decode.delta_rows, decode.cvd_read, decode.leg_of,
                                                                   decode.lead_minutes, decode.lead_read, decode.fade_now)
read_min = decode._min


def _px_at(X, now):
    bars = X.get("bars") or []
    j = bisect.bisect_right([b[0] for b in bars], now) - 1
    return (bars[j][1] / 10, read.hm(bars[j][0])) if j >= 0 else (None, None)


def gather_all(day, now, cut_epoch):
    """Every index's facts and DECODE block, exactly as the server computes them (server._decode_all, from the files,
    at now's 5-min close), plus this tool's extras at `now` itself: the lead at every minute, the futures price, the
    forward log's and the read log's rows written by then."""
    import server
    import v2feed
    res = server._decode_all(day, now, False, keep=True)
    G = res.pop("_facts")

    def extra(D):
        for i in INDICES:
            if isinstance(G.get(i), dict):
                Xf = read.from_v2(D.idx[i])
                G[i]["lead"] = lead_read(lead_minutes(Xf, now), G[i]["l5"], now)
                G[i]["px"], G[i]["px_t"] = _px_at(Xf, now)
    v2feed.with_day(day, extra)
    for i in INDICES:
        g = G.get(i)
        if not isinstance(g, dict):
            G[i] = {"idx": i, "bars5": [], "error": g, "decode": res.get(i)}
            continue
        g["decode"] = res.get(i)
        g["log"] = [r for r in confluence_log._rows(confluence_log.PATH)
                    if r.get("day") == day and r.get("index") == i and (r.get("at") or 0) <= cut_epoch]
        rlog = [r for r in confluence_log._rows(os.path.join("data", "read", f"read_{day}.jsonl"))
                if r.get("idx") == i and r.get("kind") == "mark" and isinstance(r.get("t"), str) and r["t"] <= hm(now // 60)]
        g["rlog"] = rlog[-1] if rlog else None
        g["src"] = {k: sum(1 for b in g["bars5"] if b.get("src") == k) for k in ("gc", "ux")}
    return G


# ---- printing ---------------------------------------------------------------------------------------------------------------

def show(g, out=print):
    idx, bars5 = g["idx"], g["bars5"]
    if not bars5:
        out(f"\n════ {idx}: no closed 5-min bar yet")
        return
    b, leg = bars5[-1], g["leg"]
    vw = g["vwap"]
    side = "?" if vw is None else f"{'above' if b['c'] > vw else 'below'}, {b['c'] - vw:+,.1f}"
    hi = max((x["h"], x["s"]) for x in bars5 if x.get("h") is not None)
    lo = min((x["l"], -x["s"]) for x in bars5 if x.get("l") is not None)
    out(f"\n════ {idx} ═══ fut {_f(g['px'], sign=False)} @{g['px_t']} · last 5-min close {g['c_last'] and hm(g['c_last'])} "
        f"{b['c']:,.1f} · VWAP {_f(vw, sign=False)} ({side}) · "
        f"session H {hi[0]:,.1f} ({hm(hi[1] // 60)} bar) L {lo[0]:,.1f} ({hm(-lo[1] // 60)} bar) · bars gc {g['src']['gc']} "
        f"ux {g['src']['ux']}{'' if faded.opened(bars5) is None else ' · ' + faded.opened(bars5)}")
    dl = g.get("dleg")
    swing = bool(dl and dl.get("how") == "swing")
    for name, lg, how in (("LEG", dl, f"swing, reversal {dl['thr']:,.1f}" if swing else "session extreme"),
                          ("FADE-D LEG", leg if swing else None, "§1n's own, session extreme")):
        if lg:
            out(f"  {name}  {ARROW[lg['d']]} from the {lg['from_bar']} bar {lg['from']:,.1f} to the {lg['to_bar']} bar "
                f"{lg['to']:,.1f}; last close {b['c'] - lg['to']:+,.1f} from that extreme ({how})")
    out("  DELTA  last 8 closed 5-min bars (% of the leg's biggest same-direction bar)")
    for r in g["deltas"]:
        pct = "  -" if r["pct"] is None else f"{r['pct']:>3}%"
        big = "" if r["big"] is None else f" of {r['big']:+,} ({r['big_bar']})"
        out(f"    {r['bar']}  {r['c']:>10,.1f}  {r['delta']:>+8,}  {pct}{big:<20} {r['ext']:<1} {r['src']}"
            + (f"  effort fading: new {'high' if r['ext'] == 'H' else 'low'} at {round(r['fading']['ratio'] * 100) if r['fading']['ratio'] is not None else '?'}%"
               f" of {'?' if r['fading']['big'] is None else format(r['fading']['big'], '+,')} ({r['fading']['big_bar']})"
               if r["fading"] else ""))
    c = g["cvd"]
    out(f"  CVD    now {c['now']:+,} · session peak {c['peak']:+,} after {c['peak_t']} · trough {c['trough']:+,} after "
        f"{c['trough_t']} · {c['dd']:,} under the peak, {c['up']:,} over the trough")
    L = g["lead"]
    out(f"  LEAD   PE lead (9 strikes, aaj likha; CE lead = its negative): now {_f(L['now'])} ({L['t']}) · 15m ago "
        f"{_f(L['a15'])} · 30m ago {_f(L['a30'])} · Δ15 {_f(L['chg15'])} · Δ30 {_f(L['chg30'])} · minute peak "
        f"{_f(L['peak'])} @{L['peak_t']} · 5-min-close peak {_f(L['peak5'])} @{L['peak5_t']}"
        + (f" · {L['why']}" if L["why"] else ""))
    fu = g["fuel"]
    out("  FUEL   40-min fut OI x price (READ-2): " + (
        fu.get("why") or f"{fu.get('kind') or 'below p80'} · rank p{fu.get('rank'):.0f} (n {fu.get('n')}) · OI "
                         f"{fu.get('oi_pct'):+.2f}% · px {fu.get('px'):+,.1f} · vote {ARROW[fu.get('vote')] or '0'}"))
    out(f"  ZONE   today, trigger_log non-outcome fields ({len(g['zone'])}):")
    for z in g["zone"]:
        gt = z.get("gate") or {}
        what = "arm" if z.get("kind") == "arm" else f"ENTRY px {_f(z.get('px'), sign=False)}"
        out(f"    {z['t']} bar (closed {hm(read_min(z['t']) + 3)}) {z.get('side')} {what} {z.get('band')} "
            f"lvl {_f(z.get('level'), sign=False)} · gate {'✓' if gt.get('legal') else '✗' if gt else '?'} {gt.get('why') or ''}")
    out(f"  LOG    confluence_log rows written by the cut ({len(g['log'])}):")
    for r in g["log"]:
        e = r.get("entry")
        if r.get("setup") == "FADE-D":
            out(f"    FADE-D {r['side']} {r['t']}-{r.get('end')} locs {', '.join(x['bar'] for x in r.get('locs') or ())}"
                f" · entry {e['t'] + ' E ' + format(e['E'], ',.1f') + ' stop ' + format(e['stop'], ',.1f') if e else 'none'}")
            continue
        loc = "zone" if r.get("setup") == "FADE" else "loc"
        chk = " | ".join(f"{x['t']} {loc[0].upper()}{'✓' if (x.get(loc) or {}).get('ok') else '✗'} "
                         f"OI{'✓' if x['oi'].get('ok') else '✗' if x['oi'].get('ok') is False else '?'} "
                         f"F{'✓' if x['flow'].get('ok') else '✗' if x['flow'].get('ok') is False else '?'}"
                         for x in r.get("bars") or ())
        who = f"{r.get('side')} {r.get('kind')}" if r.get("setup") == "FADE" else ARROW.get(r.get("d"), "")
        en = (f"entry {e.get('close') or e.get('t')} E {e['E']:,.1f} "
              f"{'stop ' + format(e['stop'], ',.1f') if e.get('stop') else 'line ' + format(e.get('line0') or 0, ',.1f')}"
              if e else "no entry")
        out(f"    {r.get('setup')} {who} {r['t']} (written {time.strftime('%H:%M', time.localtime(r['at']))}): {chk} · {en}")
    cd = g["card"]
    if cd.get("ok"):
        j = (cd.get("jagah") or {}).get("text")
        lg = g["rlog"]
        out(f"  READ   {cd.get('word')} {cd.get('arrow') or ''} · src {cd.get('src') or '-'} · since {cd.get('since')} · "
            f"JAGAH {j or '-'} (recomputed READ-2, no PDH/PDL)"
            + (f" · read log {lg['t']}: {lg.get('word')} {ARROW.get(lg.get('dir'), '')} ({lg.get('rev')})" if lg else ""))
    else:
        out(f"  READ   {cd.get('why')}")
    P = g["pushes"]
    if P is None:
        out(f"  PUSH   {g['push_why']}")
    else:
        last = {d: next((p for p in reversed(P) if p["d"] == d), None) for d in (1, -1)}
        out("  PUSH   " + " · ".join(f"last {ARROW[d]} " + (f"{p['t']} bar origin {p['origin']:,.1f} (U {p['U']:,.1f}, "
                                                             f"{p['src']})" if p else "none") for d, p in last.items()))
    fd = g["fd"]
    if fd:
        oi = fd["oi"]
        out(f"  FADE-D at the {fd['close']} close, {fd['side']} side: 2a {'✓' if fd['a_ok'] else '✗'} · 2b "
            f"{'✓' if fd['b']['ok'] else '✗'} (δ {fd['b']['delta']:+,}, CVD {fd['b']['dd']:,} off) · 3 "
            f"{'✓' if oi['ok'] else '✗' if oi['ok'] is False else '?'} ({oi['side']} {_f(oi['now'])} vs peak "
            f"{_f(oi['peak'])} @{oi['peak_t']}, Δ15 {_f(oi['chg15'])}) · VWAP {'far' if fd['px_ok'] else 'across'} (stamp only)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--at", metavar="HH:MM", help="a past minute of today, cut causally (default: now)")
    ap.add_argument("--day", help=argparse.SUPPRESS)                      # another recorded day (checks only)
    a = ap.parse_args(argv)
    os.chdir(HERE)
    t0 = time.time()
    nowdt = datetime.datetime.now(IST)
    day = a.day or nowdt.strftime("%Y-%m-%d")
    now = read_min(a.at) * 60 if a.at else nowdt.hour * 3600 + nowdt.minute * 60 + nowdt.second
    now = min(now, CLOSE_S)
    if now <= OPEN_S:
        print(f"{day} {hm(now // 60)}: the session has not opened (09:15)")
        return 0
    y, mo, dd = map(int, day.split("-"))
    cut_epoch = datetime.datetime(y, mo, dd, now // 3600, now % 3600 // 60, now % 60, tzinfo=IST).timestamp()
    G = gather_all(day, now, cut_epoch)
    print(f"DECODE · {day} at {hm(now // 60)}:{now % 60:02d} IST · cut causally (bars closed, rows recorded / written by "
          f"then) · files only, no server · facts, no verdict")
    for i in INDICES:
        if G[i].get("error") is not None:
            print(f"\n════ {i}: could not check — {G[i]['error']}")
            continue
        show(G[i])
    print("\nTHE APP'S DECODE BLOCK (decode.py, at the last 5-min close; the call is a COUNT of signs, never a %). Signs: "
          "effort, delta, CVD, the winning lead vs its peak, VWAP, the last push in the leg, peers -- each decel or its "
          "continuation mirror.")
    for i in INDICES:
        d = G[i].get("decode") or decode.empty("no block")
        print(f"  {i:<9} @{d['t'] or '?'}  {d['call']['text']}   (thak {d['call']['d']} · jaari {d['call']['c']} of "
              f"{d['call']['of']})")
        for x in d["call"]["signs"]:
            print(f"      · {x}")
        for ln in d["lines"]:
            print(f"    {ln}")
        print("    " + "   ".join(f"{u['name']} {u['side']} " + " ".join(
            f"{k}{'✓' if v else '✗' if v is False else '?'}" for k, v in u["checks"].items()) + f" [{u['state']}]"
            for u in d["setups"]))
        o = d.get("onesided") or {}
        print(f"    DIN {o.get('type')} · ▲{o.get('up')} ▼{o.get('down')} · mila-jula "
              f"{o.get('mix')} · ? {o.get('unk')} · disha {o.get('dom')}% · palte {o.get('flips')} · VWAP cross "
              f"{o.get('crosses')} · range {o.get('range_pct')}% · @{o.get('last')}"
              + (f" · patla: {o['thin']} bars < 20 lots, median {o.get('lots_med')}" if o.get("thin") else "")
              + f"\n        {o.get('strip')}"
              if o.get("type") else f"    DIN ? — {o.get('why')}")
    print(f"\n({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
