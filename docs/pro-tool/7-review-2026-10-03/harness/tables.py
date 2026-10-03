import io, contextlib, sys
import analyze7 as A, analyze8 as B
with contextlib.redirect_stdout(io.StringIO()):
    import analyze10 as G
P = print
def ex(r, e):
    p, t = B.exit_pct(r, e); return f"{p:+d} {t}"
def first_of(r, e):
    e6 = A.candidates(r)["rev6"]
    return e if (e and (e6 is None or e["t"] < e6["t"])) else e6
P("| # | replay | trade @ p0, mark | G at mark: pts away / premium there [I] | her exit | rev 6 first FOLD | low | high | 15:00 |")
P("|---|---|---|---|---|---|---|---|---|")
for i, r in enumerate(A.R, 1):
    s0 = r["snaps"][0]; c = A.candidates(r); e6 = c["rev6"]
    lo, hi = A.extremes(r, r["path"], r["path"][0][0])
    her = "-"
    if r["exit_t"]:
        te = A.ms_of(r["day"], r["exit_t"]); her = f"{A.pct(r, A.at(r['path'], te)):+d} {r['exit_t'][:5]}"
    f6 = f"{A.pct(r, A.at(r['path'], e6['t'])):+d} {e6['ts'][:5]} {e6['why']}" if e6 else "none"
    nm = r["name"].replace("NIFTY-", "").replace("-long-", " ")
    P(f"| {i} | {nm} | {r['day'][5:]} {'long' if r['own']>0 else 'short'} {r['k']}{r['ty']} @ {r['p0']}, {r['entry'][:5]} | {s0['G']}: {s0['dG']:.0f} / {A.pct(r, s0['atG_true']):+d} % | {her} | {f6} | {A.pct(r, lo[1]):+d} {A.hm(r['day'], lo[0])} | {A.pct(r, hi[1]):+d} {A.hm(r['day'], hi[0])} | {A.pct(r, r['path'][-1][1]):+d} |")
P()
P("| # | replay | rev 6 | (i) OI + price | (ii-F) 2 of 4 | (iii) cap -25 % | **(iv-g) GAVE UP** | (iv-b) no flow guard | (iv-a) (i)+flow | (v) no step | 15:00 |")
P("|---|---|---|---|---|---|---|---|---|---|---|")
for i, r in enumerate(A.R, 1):
    c = A.candidates(r)
    cells = [ex(r, c["rev6"]), ex(r, first_of(r, c["i"])), ex(r, first_of(r, G.lit(r))), ex(r, c["capG"]),
             ex(r, first_of(r, G.ivg(r))), ex(r, first_of(r, B.cand_ivb(r))), ex(r, first_of(r, c["iv"])), ex(r, c["nostep"])]
    base = cells[0]
    cells = [cells[0]] + [x if x != base else "=" for x in cells[1:]]
    nm = r["name"].replace("NIFTY-", "").replace("-long-", " ")
    P(f"| {i} | {nm} | " + " | ".join(cells) + f" | {A.pct(r, r['path'][-1][1]):+d} |")
