"""READ-ONLY: 27 Oct (the Oct contract's expiry day) -- the NIFTY pushes 11:30-14:20 and the fuel runs on the near month
alone vs near + next (Nov, Upstox REST historical). For Fable's Q29 / Q45 / Q67. Prints only."""
import os, sys
ROOT = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, ROOT); os.chdir(ROOT)
import book_log, handshake as H, upstox_feed, upstox_rest

DAY, LOT, NOV = "2026-10-27", 65, "NSE_FO|61471"


def runs(oim, bar):
    out, run = [], None
    for m in sorted(oim):
        if m - 5 not in oim:
            continue
        w = oim[m] - oim[m - 5]
        if run is None:
            if abs(w) >= bar:
                run = {"d": 1 if w > 0 else -1, "s": m, "ext": oim[m], "at": m}
            continue
        if run["d"] * (oim[m] - run["ext"]) > 0:
            run["ext"], run["at"] = oim[m], m
        elif m - run["at"] >= 3:
            out.append((("FRESH" if run["d"] > 0 else "COVER"), H.hm(run["s"]), H.hm(run["at"]), H.hm(m),
                        round(run["ext"] - oim[run["s"] - 5])))
            run = None
    return out


inp = H.load(DAY, "NIFTY")
for r in H.read(inp, H.LAST_M + 2):
    if "11:30" <= r["t"] <= "14:20":
        print(r["t"], H.ARROW[r["dir"]], r["lots"], r["ans"], r["k"], r["chg"], r["oi_L"], "am", r["am"], "fut", r["fut"],
              "behind", r["behind"])
near = {m: v / LOT for m, v in inp["oim"].items()}
nov = {}
for c in upstox_rest.historical(NOV, upstox_feed.read_token(), DAY) or []:
    t = str(c[0])
    nov[int(t[11:13]) * 60 + int(t[14:16])] = c[6] / LOT
both = {m: near[m] + nov[m] for m in near if m in nov}
print("near (Oct) runs:", runs(near, 500))
print("next (Nov) runs:", runs(nov, 500))
print("near + next runs:", runs(both, 500))
for hhmm in ("12:30", "12:42", "12:51", "14:03", "14:15", "14:18"):
    m = int(hhmm[:2]) * 60 + int(hhmm[3:])
    f = lambda d: None if m not in d or m - 5 not in d else round(d[m] - d[m - 5])
    print(f"{hhmm} w5 near {f(near)} next {f(nov)} sum {f(both)}")
