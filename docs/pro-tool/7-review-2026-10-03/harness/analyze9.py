"""analyze9.py -- the four diagnoses, the premium-at-G check, and the marked trades' compact minute tables. Pure."""
import statistics as st
import sys

import analyze7 as A
import analyze8 as B

P = print


def snaps(r):
    return [s for s in r["snaps"] if s["t"] <= "15:00"]


# ---- 0. premium at G: predicted v realized (the premium when the future later traded within 3 pts of that G, <= 30 min)
def prem_check():
    P("\n## premium-at-G check: predicted at a minute v the premium when the future later traded within 3 pts of that G (<= 30 min later)")
    byday = {}
    for r in A.R:
        ss = snaps(r)
        for i, s in enumerate(ss):
            if s["G"] is None or s["atG_engine"] is None or s["atG_true"] is None:
                continue
            for s2 in ss[i + 1:i + 31]:
                if s2["G"] == s["G"] and s2["fut"] is not None and abs(s2["fut"] - s["G"]) <= 3 and s2["prem"]:
                    byday.setdefault(r["day"], []).append((abs(s["atG_engine"] - s2["prem"]), abs(s["atG_true"] - s2["prem"]), s["bas"], r["name"]))
                    break
    for d, xs in sorted(byday.items()):
        P(f"   {d}: {len(xs)} minute rows (from {len(set(x[3] for x in xs))} replays), basis {st.median(x[2] for x in xs):.0f} pts; "
          f"median |error| engine {st.median(x[0] for x in xs):.1f}, corrected {st.median(x[1] for x in xs):.1f} premium pts")


# ---- 1. HOLD while >= 2 reads against, future >= w against her entry, premium below entry
def d1():
    P("\n## D1: HOLD shown while >= 2 of the four reads AGAINST, the future >= w against her entry and the premium below entry")
    tot_m, tot_t = 0, 0
    for r in A.R:
        rows = [s for s in snaps(r) if s["head"].startswith("HOLD") and sum(1 for k in "ZFOV" if s[k] == "AGAINST") >= 2
                and s["dE"] is not None and s["w"] and s["dE"] <= -s["w"] and s["pct"] is not None and s["pct"] < 0]
        if not rows:
            continue
        tot_m += len(rows)
        tot_t += 1
        worst = min(rows, key=lambda s: s["pct"])
        c = A.candidates(r)
        e6 = c["rev6"]
        P(f"   {r['name']:28} {len(rows):3} min, first {rows[0]['t']} at {rows[0]['pct']:+.0f} %, worst {worst['pct']:+.0f} % {worst['t']}, "
          f"against: {','.join(k for k in 'ZFOV' if rows[0][k] == 'AGAINST')}; rev 6 FOLD {e6['ts'][:5] + ' ' + format(A.pct(r, A.at(r['path'], e6['t'])), '+d') + ' %' if e6 else 'none'}")
    P(f"   total: {tot_m} minute rows on {tot_t} of {len(A.R)} replays")


# ---- 2. the give-up so far that the premium there is a -30 %+ loss at the mark
def d2():
    P("\n## D2: give-up at the mark, distance and premium there (engine as shown / corrected) [I]")
    n = 0
    for r in A.R:
        s = snaps(r)[0] if snaps(r) else None
        if not s or s["atG_true"] is None:
            continue
        pt = A.pct(r, s["atG_true"])
        pe = A.pct(r, s["atG_engine"])
        flag = pt <= -30
        n += flag
        P(f"   {'**' if flag else '  '} {r['name']:28} G {s['G']} {s['dG']:.0f} pts away, basis {s['bas']:.0f}: shown {s['atG_engine']} ({pe:+d} %), corrected {s['atG_true']} ({pt:+d} %)")
    P(f"   {n} of {len(A.R)} replays seed a give-up whose corrected premium is -30 % or worse")


# ---- 3. FOLD landing at the low
def d3():
    P("\n## D3: each rev 6 FOLD -- premium then, worst in the next 30 min, best in the next 60 min, back inside G by w within 20 min (minute rows)")
    for r in A.R:
        c = A.candidates(r)
        e = c["rev6"]
        if not e:
            continue
        p = A.pct(r, A.at(r["path"], e["t"]))
        lo, _ = A.extremes(r, r["path"], e["t"], e["t"] + 30 * 60000)
        _, hi = A.extremes(r, r["path"], e["t"], e["t"] + 60 * 60000)
        G = e["G"]
        back = next((s["t"] for s in snaps(r) if e["ts"][:5] < s["t"] <= A.hm(r["day"], e["t"] + 20 * 60000)
                     and s["fut"] is not None and s["w"] and r["d"] * (s["fut"] - G) >= s["w"]), None)
        low = A.pct(r, lo[1]) >= p - 3 and A.pct(r, hi[1]) >= p + 10
        P(f"   {'LOW' if low else '   '} {r['name']:28} {e['ts'][:5]} {e['why'] or '':9} {p:+4d} % | worst 30 min {A.pct(r, lo[1]):+d} % | best 60 min {A.pct(r, hi[1]):+d} % {A.hm(r['day'], hi[0])} "
              f"| back inside G {G} by w: {back or 'no'}")


# ---- 4. G stepping toward price while she is losing at entry
def d4():
    P("\n## D4: G re-set by a win of her side while at entry and the future below her entry (losing)")
    for r in A.R:
        evs = B.evs_of(r)
        for i, e in enumerate(evs):
            if e["kind"] != "reset" or e["E"] is None or r["d"] * (e["fut"] - e["E"]) >= 0:
                continue
            prev_G = next((x["G"] for x in reversed(evs[:i]) if x["G"] != e["G"]), None)
            if e["mode"] != "at entry":
                continue
            same = [x for x in evs if x["t"] == e["t"]]
            oiw = any(x["kind"] == "oi_withdrawn" for x in same)
            chip = next((x["text"] for x in same if x["kind"] == "chip" and x["text"].startswith("OI ")), None)
            f = next((x for x in evs if x["kind"] == "fold" and x["t"] >= e["t"]), None)
            P(f"   {r['name']:28} {e['ts'][:5]} G {prev_G} -> {e['G']} at {A.pct(r, e['prem']):+d} % (future {e['fut']} v entry {e['E']}); "
              f"OI event withdrawn: {'yes' if oiw else 'no'}; {chip or ''}; next FOLD {f['ts'][:5] + ' ' + format(A.pct(r, A.at(r['path'], f['t'])), '+d') + ' %' if f else 'none'}")


def table(r):
    """compact minute table: every 5 min to exit+30, every 15 min after, plus any minute where a chip, G or the headline changed"""
    ss = snaps(r)
    c = A.candidates(r)
    e6 = c["rev6"]
    import analyze10 as G10
    iv = G10.ivg(r)
    lo, hi = A.extremes(r, r["path"], r["path"][0][0])
    ex = r["exit_t"][:5] if r["exit_t"] else None
    marks = {}
    if ex:
        marks.setdefault(A.hm(r["day"], A.ms_of(r["day"], r["exit_t"]) + 60000), []).append(f"(a) her exit {r['exit_t']}")
    if e6:
        marks.setdefault(A.hm(r["day"], e6["t"] + 60000), []).append(f"(b) rev 6 {e6['text'][:40]}")
    if iv:
        marks.setdefault(A.hm(r["day"], iv["t"] + 60000), []).append(f"(iv-g) GAVE UP {iv['ts'][:8]}")
    marks.setdefault(A.hm(r["day"], lo[0] + 60000), []).append(f"(c) low {A.pct(r, lo[1]):+d} % {A.hm(r['day'], lo[0])}")
    marks.setdefault(A.hm(r["day"], hi[0] + 60000), []).append(f"(c) high {A.pct(r, hi[1]):+d} % {A.hm(r['day'], hi[0])}")
    ab = lambda v: {"WITH": "W", "AGAINST": "A", "QUIET": "q", "CAN'T CHECK": "?", None: "-"}[v]  # noqa: E731
    out, prev = [], None
    cut = A.hm(r["day"], A.ms_of(r["day"], r["exit_t"]) + 30 * 60000) if ex else "11:00"
    for i, s in enumerate(ss):
        key = (s["Z"], s["F"], s["O"], s["V"], s["G"], s["head"][:4])
        mm = int(s["t"][3:])
        early = s["t"] <= cut
        step = 5 if early else 30
        chg = key != prev if early else (prev is not None and (key[4], key[5]) != (prev[4], prev[5]))
        if i == 0 or chg or mm % step == 0 or s["t"] in marks or s["t"] == "15:00":
            h = "HOLD" if s["head"].startswith("HOLD") else "FOLD" if s["head"].startswith("FOLD") else s["head"][:10]
            pg = A.pct(r, s["atG_true"]) if s["atG_true"] is not None else None
            out.append(f"| {s['t']} | {s['fut']:.0f} | {s['prem']} ({s['pct']:+.0f}) | {ab(s['Z'])}{ab(s['F'])}{ab(s['O'])}{ab(s['V'])} | {h} | {s['G']} | "
                       f"{s['dG']:+.0f} | {s['atG_engine']} / {s['atG_true']}{f' ({pg:+d})' if pg is not None else ''} | {s['W']} {s['Wst'] or ''} | {'; '.join(marks.get(s['t'], []))} |")
        prev = key
    return out


if __name__ == "__main__":
    prem_check()
    d1()
    d2()
    d3()
    d4()
    for r in A.R:
        if r["kind"] != "marked":
            continue
        P(f"\n### {r['name']} {r['day']} p0 {r['p0']} entry {r['entry']} E {r['E']}")
        P("| min | fut | prem (% entry) | Z F O V | head | G | to G pts | at G shown / corrected (%) | W | marks |")
        P("|---|---|---|---|---|---|---|---|---|---|")
        for x in table(r):
            P(x)
