"""Round 7: each strike against its OWN day-normal (prints.pct_rank), change and rate of change, at its OWN premium VWAP
bands; absorption / exhaustion / climax / ignition at the band with controls. NIFTY, 5 days, her 3-min grid, causal.
Definitions fixed in NOTES.md ("Round 7 definitions") before counting. Run from tapemap/:
    python -I -X utf8 docs/optflow/fable/round7.py"""
import json, os, sys, statistics as st
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
TM = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE); sys.path.insert(0, TM); sys.path.insert(0, os.path.join(HERE, "..", "brainstorm"))
from load import hm, m_of
import load as _load
import prints
from round4 import closes, fut_after
from round5 import wall, ORDER, bands

DAYS = json.load(open(os.path.join(HERE, "days.json"), encoding="utf-8"))
READ_FROM = 584          # 09:44, the bands readable (§1s C6)
RANK_MIN = 6             # prints: "first six bars: nothing to rank against"
P90, P95 = 0.90, 0.95
PULLBACKS = {"2026-11-02": [("09:46", 1, "CONT"), ("10:55", 1, "FAIL"), ("12:56", -1, "CONT"), ("13:09", -1, "CONT"), ("13:17", -1, "CONT"), ("14:39", 1, "CONT"), ("14:50", 1, "CONT")],
             "2026-11-03": [("10:36", 1, "CONT"), ("12:07", 1, "CONT"), ("13:22", 1, "CONT"), ("13:43", 1, "PIN")]}
COVERS = {"2026-10-28": [("12:44", 1)], "2026-10-29": [("10:17", 1), ("14:11", 1)], "2026-10-30": [("11:05", 1), ("11:44", 1)],
          "2026-11-02": [("09:32", 1), ("12:59", -1), ("14:29", 1)], "2026-11-03": []}


def series(day, x, B):
    """{(k, side): [per close dict: t, i, vol, delta, adel, doi, rng, chg, h, l, c, bands..., who, pcts, loc]} causal."""
    dx = _load.dext(day)["NIFTY"]
    out = {}
    for key, rows in dx.items():
        q = x["strikes"].index(list(key))
        bl = B.get(key) or {}
        ser, prev_c, prev_oi, hist = [], None, None, defaultdict(list)
        prev = None
        for i in closes(x):
            e = x["mins"][i]
            ms = [m for m in (e - 2, e - 1, e) if m in rows]
            b = bl.get(e)
            oi = x["oi"][q][i]
            if not ms or not b:
                prev_oi = oi if oi is not None else prev_oi
                continue
            vol = sum(rows[m]["total_volume"] for m in ms); dl = sum(rows[m]["delta"] for m in ms)
            doi = (oi - prev_oi) if oi is not None and prev_oi is not None else None
            r = {"t": e, "i": i, "vol": vol, "delta": dl, "adel": abs(dl), "doi": doi, "rng": b["h"] - b["l"], "h": b["h"], "l": b["l"], "c": b["c"],
                 "u2": b["u2"], "u3": b["u3"], "d2": b["d2"], "d3": b["d3"], "chg": (b["c"] - prev_c) if prev_c is not None else None,
                 "who": x["who"][i][q] if x["who"][i] else None, "n": len(hist["vol"])}
            for m_ in ("vol", "adel", "rng"):
                r["p_" + m_] = prints.pct_rank(hist[m_], r[m_]) if len(hist[m_]) >= RANK_MIN else None
            r["med_rng"] = st.median(hist["rng"]) if len(hist["rng"]) >= RANK_MIN else None
            # change and rate of change of effort and of dOI
            if prev:
                r["d_vol"] = vol - prev["vol"]; r["d_adel"] = r["adel"] - prev["adel"]
                r["d_doi"] = (doi - prev["doi"]) if doi is not None and prev.get("doi") is not None else None
                r["r_vol"] = (r["d_vol"] - prev["d_vol"]) if prev.get("d_vol") is not None else None
            r["loc"] = "BEYOND_U" if b["h"] >= b["u3"] else "AT_U" if b["h"] >= b["u2"] else "BEYOND_D" if b["l"] <= b["d3"] else "AT_D" if b["l"] <= b["d2"] else "IN"
            r["hi6"] = max((p["h"] for p in ser[-6:]), default=None)
            r["lo6"] = min((p["l"] for p in ser[-6:]), default=None)
            ser.append(r)
            for m_ in ("vol", "adel", "rng"):
                hist[m_].append(r[m_])
            prev_c, prev, prev_oi = b["c"], r, (oi if oi is not None else prev_oi)
        out[key] = ser
    return out


def abnormal(r, p=P90):
    return (r.get("p_vol") is not None and r["p_vol"] >= p) or (r.get("p_adel") is not None and r["p_adel"] >= p)


def signatures(ser):
    """Per close: the set of signatures (upper or lower band) and the inside controls."""
    out = []
    for j, r in enumerate(ser):
        nx = ser[j + 1] if j + 1 < len(ser) else None
        sig = set()
        if r["t"] < READ_FROM or r.get("p_vol") is None or nx is None:
            out.append(sig); continue
        up, dn = r["loc"] in ("AT_U", "BEYOND_U"), r["loc"] in ("AT_D", "BEYOND_D")
        small = (r["med_rng"] is not None and r["rng"] <= r["med_rng"]) or (up and r["c"] < r["u2"]) or (dn and r["c"] > r["d2"])
        holds = (up and nx["c"] <= nx["u2"]) or (dn and nx["c"] >= nx["d2"])
        if (up or dn) and abnormal(r) and small and holds:
            sig.add("ABSORPTION")
        eff_falling = r.get("d_vol") is not None and r["d_vol"] < 0 and r.get("d_adel") is not None and r["d_adel"] < 0 and (r.get("d_doi") is None or r["d_doi"] < 0)
        if ((up and r["hi6"] is not None and r["h"] > r["hi6"]) or (dn and r["lo6"] is not None and r["l"] < r["lo6"])) and eff_falling:
            sig.add("EXHAUSTION")
        if r["loc"] in ("BEYOND_U", "BEYOND_D") and abnormal(r, P95) and nx["delta"] * r["delta"] < 0:
            sig.add("CLIMAX")
        if abnormal(r) and r["c"] >= r["u2"] and nx["c"] >= nx["u2"] and r["who"] == "C":
            sig.add("IGNITION")
        # inside controls: the same effort/result conditions with no band
        if r["loc"] == "IN":
            if abnormal(r) and small:
                sig.add("in_ABSORPTION")
            if abnormal(r) and r["who"] == "C" and nx["c"] >= r["c"]:
                sig.add("in_IGNITION")
            if abnormal(r, P95) and nx["delta"] * r["delta"] < 0:
                sig.add("in_CLIMAX")
        out.append(sig)
    return out


def outcome(ser, j, side):
    """+30 min (10 closes): HOLD / RUN for an upper ('U') or lower ('D') touch; inside: RUN if up by a median range."""
    r = ser[j]
    k = next((n for n in range(j + 1, len(ser)) if ser[n]["t"] >= r["t"] + 30), None)
    if k is None:
        return None
    z = ser[k]
    if side == "U":
        return "RUN" if (z["c"] > r["c"] and z["c"] >= z["u2"]) else "HOLD"
    if side == "D":
        return "RUN" if (z["c"] < r["c"] and z["c"] <= z["d2"]) else "HOLD"
    return "RUN" if (r["med_rng"] and z["c"] - r["c"] >= r["med_rng"]) else "HOLD"


def main():
    grand = defaultdict(Counter)
    for day in ORDER:
        _load.CUR["day"] = day
        x = DAYS[day]["NIFTY"]; C = closes(x)
        B = bands(day, x)
        S = series(day, x, B)
        SIG = {key: signatures(ser) for key, ser in S.items()}
        # the universe per close: ATM±3 + walls
        def universe(i):
            sp = x["spot"][i]
            if sp is None: return set()
            atm = round(sp / 50) * 50
            u = {(atm + d, s) for d in range(-150, 151, 50) for s in ("CE", "PE")}
            for s in ("CE", "PE"):
                w = wall(x, i, s)
                if w is not None: u.add(tuple(x["strikes"][w]))
            return u
        cnt = Counter()
        for key, ser in S.items():
            for j, r in enumerate(ser):
                if r["t"] < READ_FROM or key not in universe(r["i"]): continue
                sig = SIG[key][j]
                side = "U" if r["loc"] in ("AT_U", "BEYOND_U") else "D" if r["loc"] in ("AT_D", "BEYOND_D") else "IN"
                oc = outcome(ser, j, side)
                if oc is None: continue
                if side in ("U", "D"):
                    names = [s for s in sig if not s.startswith("in_")] or ["touch, no signature"]
                    for nm in names:
                        cnt[(nm, oc)] += 1
                else:
                    for nm in [s for s in sig if s.startswith("in_")]:
                        cnt[(nm, oc)] += 1
        print(f"\n################ {day}")
        for k in sorted(cnt): grand[k[0]][(day, k[1])] = cnt[k]
        print("  " + " · ".join(f"{k[0]} {k[1]} {v}" for k, v in sorted(cnt.items())))
        # ignition vs the covering events
        for t0, dirn in COVERS.get(day, []):
            s = x["mins"].index(m_of(t0)); e = s + 15
            side = "CE" if dirn > 0 else "PE"
            first_cov = next((i for i in C if s - 30 <= i <= e and wall(x, i, side) is not None and x["who"][i][wall(x, i, side)] == "C"), None)
            ign = []
            for key, ser in S.items():
                if key[1] != side: continue
                for j, r in enumerate(ser):
                    if s - 30 <= r["i"] <= e and "IGNITION" in SIG[key][j]:
                        ign.append((r["t"], key[0]))
            ign.sort()
            print(f"  cover event {t0}: first COVER at the wall {hm(x['mins'][first_cov]) if first_cov is not None else 'none'} · IGNITION closes {[(hm(t), k) for t, k in ign][:6] or 'none'}"
                  + (f" → first ignition {x['mins'][first_cov] - ign[0][0]:+d} min before the first cover" if ign and first_cov is not None else ""))
        # pullbacks x absorption at the defending wall's upper band
        for t0, dirn, oc in PULLBACKS.get(day, []):
            i0 = x["mins"].index(m_of(t0)); i1 = min(i0 + 60, len(x["mins"]) - 1)
            side = "PE" if dirn > 0 else "CE"
            got = Counter()
            for i in C:
                if not (i0 <= i <= i1): continue
                w = wall(x, i, side)
                if w is None: continue
                key = tuple(x["strikes"][w]); ser = S.get(key, [])
                j = next((n for n, r in enumerate(ser) if r["i"] == i), None)
                if j is None: continue
                for sg in SIG[key][j]:
                    if not sg.startswith("in_"): got[sg] += 1
            print(f"  pullback {t0} {'▲' if dirn > 0 else '▼'} {oc}: defending {side} wall signatures in the window: {dict(got) or 'none'}")
        # named cases
        def show(key, lo, hi):
            ser = S.get(key, []);
            for j, r in enumerate(ser):
                if lo <= r["t"] <= hi:
                    print(f"    {hm(r['t'])} {key[0]}{key[1]} c {r['c']:.1f} h {r['h']:.1f} u2 {r['u2']:.1f} u3 {r['u3']:.1f} | vol p{r['p_vol'] if r['p_vol'] is None else round(r['p_vol'], 2)} |Δ| p{r['p_adel'] if r['p_adel'] is None else round(r['p_adel'], 2)} Δ {r['delta'] / 1e5:+.1f}L dOI {'?' if r['doi'] is None else round(r['doi'] / 1e5, 1)}L rng {r['rng']:.1f} (med {r['med_rng'] and round(r['med_rng'], 1)}) · {r['loc']} · who {r['who']} · {sorted(SIG[key][j]) or '-'}")
        if day == "2026-11-03":
            print("  named: 23,600 CE 09:47–10:17"); show((23600, "CE"), 587, 617)
            print("  named: 10:35 climax, 23,600 / 23,650 CE 10:29–10:41"); show((23600, "CE"), 629, 641); show((23650, "CE"), 629, 641)
            print("  named: 23,700 CE break 13:11–13:23"); show((23700, "CE"), 671, 683)
        if day == "2026-11-02":
            print("  named: the down-leg, 23,300 / 23,250 PE 12:53–13:14"); show((23300, "PE"), 773, 794); show((23250, "PE"), 773, 794)
    print("\n################ SUMMARY (signature → per day: HOLD / RUN)")
    for nm in sorted(grand):
        print(f"  {nm:22} " + " · ".join(f"{d[-5:]} {grand[nm].get((d, 'HOLD'), 0)}/{grand[nm].get((d, 'RUN'), 0)}" for d in ORDER))


if __name__ == "__main__":
    main()
