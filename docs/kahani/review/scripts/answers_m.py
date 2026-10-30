"""READ-ONLY measurements for Fable's round-1 questions (Q1, Q2, Q7, Q8, Q15, Q17, Q23, Q24, Q29, Q32, Q45, Q56, Q57, Q81).
Prints only; never writes under data/. Usage: python answers_m.py"""
import collections, gzip, json, os, statistics, sys
ROOT = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, ROOT); os.chdir(ROOT)
import book_log, fronts, handshake as H, v2feed

DAYS = ["2026-10-01", "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12", "2026-10-13",
        "2026-10-16", "2026-10-19", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28"]
END = H.LAST_M + 2
hm = H.hm
UP, DN = "\u25b2", "\u25bc"


def runs(oim, bar):
    """The spec's RUN rule on {minute: OI lots}: start |w5| >= bar; lives while a new extreme comes within 3 min; KHATAM
    at the 3rd minute with none. -> [(kind, start, last_ext, khatam, lots from start-5, lots from start)]."""
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
            s = run["s"]
            out.append(("FRESH" if run["d"] > 0 else "COVER", s, run["at"], m,
                        round(run["ext"] - oim[s - 5]), round(run["ext"] - oim[s])))
            run = None
    if run:
        s = run["s"]
        out.append(("FRESH" if run["d"] > 0 else "COVER", s, run["at"], None,
                    round(run["ext"] - oim[s - 5]), round(run["ext"] - oim[s])))
    return out


print("== Q23/63: futures OI publish cadence (NIFTY book) ==")
for day in ("2026-10-27", "2026-10-28"):
    rows = sorted((r for r in book_log.read_rows(day, "NIFTY") if isinstance(r.get("t"), (int, float)) and r.get("oi")),
                  key=lambda r: r["t"])
    per, chg, prev = collections.defaultdict(set), [], None
    for r in rows:
        per[H.mod(r["t"])].add(r["oi"])
        if prev is not None and r["oi"] != prev["oi"]:
            chg.append(r["t"])
        prev = r
    gaps = [(b - a) / 1000 for a, b in zip(chg, chg[1:])]
    d = sorted(len(v) for v in per.values())
    print(f"{day}: rows {len(rows)}, minutes {len(per)}, distinct OI values/min median {statistics.median(d)} "
          f"(min {d[0]}, max {d[-1]}); OI changes {len(chg)}, gap between changes median {statistics.median(gaps):.1f}s "
          f"p90 {sorted(gaps)[int(len(gaps) * .9)]:.1f}s; gaps > 60s: {sum(g > 60 for g in gaps)} (longest {max(gaps):.0f}s)")

print("\n== Q1/Q2/Q7/Q12: pushes, answers, first push, un-crossing, flow source, per day (NIFTY) ==")
unx, tot_ans = [], 0
for day in DAYS:
    try:
        inp = H.load(day, "NIFTY")
    except Exception as e:
        print(day, "load failed", e)
        continue
    if not inp["ms"]:
        print(day, "no chain")
        continue
    rows = H.read(inp, END)
    sp = [inp["R"][m]["spot"] for m in inp["ms"]]
    c = collections.Counter(((UP if r["dir"] > 0 else DN), str(r["ans"])) for r in rows)
    src = collections.Counter(r["src"] for r in rows)
    bm = sorted(H.mod(r["t"]) for r in book_log.read_rows(day, "NIFTY") if isinstance(r.get("t"), (int, float)))
    print(f"{day}: open {sp[0]:.0f}s close {sp[-1]:.0f}s range {max(sp) - min(sp):.0f} | book from {hm(bm[0]) if bm else '-'}"
          f" | pushes {len(rows)} first {rows[0]['t'] if rows else '-'} | src {dict(src)} | "
          + " ".join(f"{k[0]}{k[1]}:{v}" for k, v in sorted(c.items())))
    for r, p in zip(rows, inp["pushes"]):
        if r["ans"] in ("TOOT", "PHANS", "TIKI"):
            tot_ans += 1
            a4 = H.answer(inp["R"], inp["ms"], p, END, first=False)
            if (a4 or {}).get("ans") != r["ans"]:
                unx.append(f"{day} {r['t']}{H.ARROW[r['dir']]} first {r['ans']} {r['chg']}L@{r['am']} -> m4 "
                           f"{(a4 or {}).get('ans')} {(a4 or {}).get('chg')}L")
print(f"Q7 un-crossing: {len(unx)} of {tot_ans} answered pushes read differently at m+4:")
for u in unx:
    print("  ", u)

print("\n== Q8: 28 Oct 12:40-12:56 pushes and the 22,700s PE add ==")
inp = H.load("2026-10-28", "NIFTY")
rows = H.read(inp, END)
for r in rows:
    if "12:40" <= r["t"] <= "12:56":
        print(" ", r["t"], H.ARROW[r["dir"]], r["lots"], r["ans"], r["k"], r["chg"], "am", r["am"], "behind", r["behind"],
              "fut", r["fut"])
R = inp["R"]
for m0, m1 in ((769, 771), (769, 772), (769, 773)):
    a, b = H._leg(R.get(m0), 22700, "pe"), H._leg(R.get(m1), 22700, "pe")
    if a and b and R.get(m0) and R.get(m1):
        ds = R[m1]["spot"] - R[m0]["spot"]
        x = (b["ltp"] - a["ltp"]) - a["delta"] * ds
        print(f"  {hm(m0)}->{hm(m1)}: spot {ds:+.1f}s, PE ltp {a['ltp']}->{b['ltp']}, delta {a['delta']}, residual {x:+.2f} "
              f"(2 ticks = 0.10); iv {a.get('iv')}->{b.get('iv')}, vega {a.get('vega')}, oi {a.get('oi')}->{b.get('oi')}")

print("\n== Q15/Q17/THAKAN: the section-1d fronts, 28 Oct NIFTY, printed when a state changes ==")
p = os.path.join(ROOT, "data", "chain", "chain_NIFTY_2026-10-28.jsonl")
fh = open(p, encoding="utf-8") if os.path.exists(p) else gzip.open(p + ".gz", "rt", encoding="utf-8")
snaps = list({(s.get("ts") or "")[:5]: s for s in (json.loads(l) for l in fh if l.strip())}.values())  # last per minute
minutes, peak, last_state = {}, {}, {}
for s in snaps:
    ts = (s.get("ts") or "")[:5]
    if not ts or ts < "09:15" or ts > "13:35":
        continue
    minutes[ts] = {"spot": s["spot"], "k": {float(r["k"]): (r["ce"].get("oi_chg") or 0.0, r["pe"].get("oi_chg") or 0.0)
                                           for r in s["strikes"]}}
    for r in s["strikes"]:
        for side in ("ce", "pe"):
            peak[(float(r["k"]), side)] = max(peak.get((float(r["k"]), side), 0.0), r[side]["oi"])
    if ts < "10:30":
        continue
    fr = fronts.read(minutes, peak)
    st = {(f["side"], f["k"]): f["state"] for f in fr}
    if st != last_state or ts in ("12:06", "12:12", "12:44", "12:49", "13:03", "13:15"):
        print(f"  {ts} {s['spot']:.1f}s | " + " | ".join(
            f"{f['k']:.0f}{f['side']} {f['state'][:5]} {f['chg'] / 1e5:+.1f}L pk {f['peak'] / 1e5:+.1f}L@{f['peak_at']} sl {f['slope'] / 1e5:+.1f}"
            for f in fr))
    last_state = st

print("\n== Q24/Q29/Q32: the RUN rule on the book's own futures OI, every recorded day (lots from start-5 / from start) ==")
for idx in ("NIFTY", "BANKNIFTY", "SENSEX"):
    lot = v2feed.LOTS.get(idx) or 1
    for day in DAYS:
        try:
            br = [r for r in book_log.read_rows(day, idx) if isinstance(r.get("t"), (int, float)) and r.get("oi")]
        except Exception:
            br = []
        if not br:
            continue
        ik = next((r.get("ik") for r in br if r.get("ik")), "?")
        oim = {m: v / lot for m, v in H.fut_minutes(sorted((r["t"], r["oi"]) for r in br)).items()}
        rr = runs(oim, H.FUT_LOTS[idx])
        print(f"  {idx} {day} {ik} {len(oim)}min: {len(rr)} runs | " + "; ".join(
            f"{k} {hm(s)}-{hm(a)} K{hm(kh) if kh else '..'} {t5:+}/{t0:+}" for k, s, a, kh, t5, t0 in rr))

print("\n== Q45/Q81: trigger_log rows by (day, idx, rule, kind) since 19 Oct, and 27 Oct NIFTY ==")
cnt, z27, keys = collections.Counter(), [], None
with open(os.path.join(ROOT, "data", "trigger_log.jsonl"), encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
        except Exception:
            continue
        keys = keys or sorted(r)
        day = str(r.get("day") or r.get("date") or r.get("ts") or "")[:10]
        ix = r.get("idx") or r.get("index") or r.get("symbol")
        if day >= "2026-10-19":
            cnt[(day, ix, r.get("rule"), r.get("kind"))] += 1
        if day == "2026-10-27" and ix == "NIFTY":
            z27.append(r)
print("  keys of a row:", keys)
for k, v in sorted(cnt.items(), key=lambda x: [str(y) for y in x[0]]):
    print("  ", k, v)
for r in z27:
    s = json.dumps(r)
    if any(h in s for h in ('"12:3', '"12:4', '"12:5', '"14:0', '"14:1', 'T12:3', 'T12:4', 'T12:5', 'T14:0', 'T14:1', ' 12:4', ' 12:5')):
        print("   27Oct:", s[:300])

print("\n== Q56/Q57: BANKNIFTY / SENSEX pushes over the recorded days, and 28 Oct 12:30-12:55 ==")
for idx in ("BANKNIFTY", "SENSEX"):
    n = 0
    for day in DAYS:
        try:
            inp = H.load(day, idx)
            n += len(H.read(inp, END)) if inp["ms"] else 0
        except Exception:
            pass
    inp = H.load("2026-10-28", idx)
    rr = H.read(inp, 12 * 60 + 56)
    print(f"  {idx}: {n} pushes over the recorded days; 28 Oct 12:30-12:55:",
          [(r["t"], H.ARROW[r["dir"]], r["ans"], r["k"], r["chg"], r["oi_L"]) for r in rr if r["t"] >= "12:30"])
