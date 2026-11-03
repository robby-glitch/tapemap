"""Scratch study (not repo code): NIFTY option strikes by distance from spot, the walls, and her VWAP sigma bands on each
option's own premium, with the option order flow at each band touch. Her grid: 3-min bars closing at (m-555)%3==2.
Causal: a bar's numbers use data up to its close; "next" columns are hindsight and labelled so. Counts only, no rates."""
import collections, glob, json, os, sys
TM = r"C:/Users/kaam/Desktop/operator mode/tapemap"
sys.path.insert(0, TM); sys.path.insert(0, TM + "/optflow")
import optflow as O
from contract_bars import _Vwap

OI_MOVE, AGG_X, BIG = 1.5e5, 0.2, 5e5          # Fable's [I] thresholds (qty), kept identical
hm = lambda m: "%02d:%02d" % divmod(m, 60)


def load(day):
    ch = O.load_chain(day, "NIFTY")
    exp = ch[max(ch)]["expiry"]
    snap, cur, spot = {}, {}, {}
    for m in range(555, 931):
        r = ch.get(m)
        if r:
            spot[m] = r.get("spot") or spot.get(m - 1)
            for s in r.get("strikes") or []:
                for sd in ("ce", "pe"):
                    x = s.get(sd) or {}
                    if x.get("oi") is not None:
                        cur[(s["k"], sd)] = (x.get("oi"), x.get("ltp"))
        else:
            spot[m] = spot.get(m - 1)
        snap[m] = dict(cur)
    flow = {}
    for p in glob.glob(f"{TM}/data/dext/dext_NSE-*_{day}.jsonl"):
        r = O.scrip().get(os.path.basename(p).split("_")[1])
        if r and r[6] == "NIFTY" and r[12] == exp and r[14] in ("CE", "PE"):
            flow[(int(float(r[13])), r[14].lower())] = O.rows(p)
    fut = json.load(open(f"{TM}/data/tape/fut1m_NIFTY_{day}.json", encoding="utf-8"))
    return exp, snap, spot, flow, fut


def bars3(day):
    exp, snap, spot, flow, fut = load(day)
    closes = list(range(557, 930, 3))
    out = {}
    for key, rows in flow.items():
        st, bl, prev_oi = _Vwap(), [], None
        for e in closes:
            ms = [m for m in (e - 2, e - 1, e) if m in rows]
            s = snap.get(e, {}).get(key)
            if not ms or not s or s[1] is None:
                prev_oi = s[0] if s else prev_oi
                continue
            h = max(rows[m]["high"] for m in ms); l = min(rows[m]["low"] for m in ms)
            v = sum(rows[m]["total_volume"] for m in ms); d = sum(rows[m]["delta"] or 0 for m in ms)
            big = max([(lv.get("buy_volume") or 0, "B", lv["price"]) for m in ms for lv in rows[m]["levels"]]
                      + [(lv.get("sell_volume") or 0, "S", lv["price"]) for m in ms for lv in rows[m]["levels"]], default=(0, "B", None))
            c = s[1]; bd = st.push(h, l, c, v)
            doi = None if prev_oi is None else s[0] - prev_oi
            prev_oi = s[0]
            bl.append(dict(e=e, h=h, l=l, c=c, v=v, d=d, oi=s[0], doi=doi, big=big, **bd))
        out[key] = bl
    fb, st = {}, _Vwap()
    for e in closes:
        ms = [hm(m) for m in (e - 2, e - 1, e) if hm(m) in fut]
        if not ms:
            continue
        h, l, c, v = max(fut[x][1] for x in ms), min(fut[x][2] for x in ms), fut[ms[-1]][3], sum(fut[x][4] for x in ms)
        fb[e] = dict(h=h, l=l, c=c, **st.push(h, l, c, v))
    return exp, spot, out, fb


def who(doi, d):
    if doi is None: return "OI?"
    if abs(doi) < OI_MOVE: return "QUIET"
    if abs(d) < AGG_X * abs(doi): return "MIXED"
    return ("WRITE" if d < 0 else "BUY") if doi > 0 else ("COVER" if d > 0 else "DUMP")


def zone(k, sd, sp):
    s = round(((k - sp) if sd == "ce" else (sp - k)) / 50)       # + = OTM steps, - = ITM
    return "ITM" if s <= -1 else "ATM" if s == 0 else "NEAR 1-2" if s <= 2 else "WING 3-5" if s <= 5 else "FAR 6+"


def pos(b):
    return None if not b else ("≥u3" if b["h"] >= b["u3"] else "≥u2" if b["h"] >= b["u2"] else "≤d3" if b["l"] <= b["d3"]
                               else "≤d2" if b["l"] <= b["d2"] else ">vwap" if b["c"] > b["vwap"] else "<vwap")


def study(day):
    exp, spot, B, fb = bars3(day)
    print(f"\n######## {day}  NIFTY {exp} expiry  ({len(B)} contracts)")
    agg = collections.defaultdict(collections.Counter)
    for (k, sd), bl in B.items():
        for b in bl:
            a = agg[(zone(k, sd, spot[b["e"]]), sd)]
            a["vol"] += b["v"]; a["absd"] += abs(b["d"]); a["net"] += b["d"]
            if b["doi"] is not None: a["oi+"] += max(0, b["doi"]); a["oi-"] += min(0, b["doi"])
            a[who(b["doi"], b["d"])] += 1
            if b["big"][0] >= BIG: a["big"] += 1
    print("zone       side | vol L  |delta| L  net L | OI+ L  OI- L | WRITE BUY COVER DUMP MIXED | big hits")
    for z in ("ITM", "ATM", "NEAR 1-2", "WING 3-5", "FAR 6+"):
        for sd in ("ce", "pe"):
            a = agg[(z, sd)]
            if a["vol"]:
                print(f"{z:9} {sd:>4} | {a['vol']/1e5:6.0f} {a['absd']/1e5:7.0f} {a['net']/1e5:+7.0f} | {a['oi+']/1e5:5.0f} {a['oi-']/1e5:6.0f} |"
                      f" {a['WRITE']:5} {a['BUY']:3} {a['COVER']:5} {a['DUMP']:4} {a['MIXED']:5} | {a['big']}")
    print("\nwalls (max CE OI above spot / max PE OI below spot), when they move:")
    last = {}
    for e in sorted({b["e"] for bl in B.values() for b in bl}):
        sp = spot[e]
        for sd in ("ce", "pe"):
            c = [(b["oi"], k) for (k, s2), bl in B.items() if s2 == sd for b in bl if b["e"] == e and (k > sp if sd == "ce" else k < sp)]
            if not c: continue
            oi, k = max(c)
            if last.get(sd) != k:
                bb = next(b for b in B[(k, sd)] if b["e"] == e)
                ob = next((b for b in B.get((last.get(sd), sd), []) if b["e"] == e), None)
                print(f"  {hm(e)} {'CAP  ' if sd == 'ce' else 'FLOOR'} {last.get(sd)} -> {k} ({abs(k - sp) / 50:.1f} steps away, {oi / 1e5:.0f}L)"
                      f" new: {who(bb['doi'], bb['d'])}" + (f" · old: {who(ob['doi'], ob['d'])} {ob['doi'] / 1e5:+.0f}L" if ob and ob['doi'] is not None else "")
                      + f" · fut {fb[e]['c']:.0f}" if e in fb else "")
                last[sd] = k
    print("\npremium band touches (ATM / NEAR, after 09:25; flow at the touch bar; +15/+30 = hindsight):")
    print("  at    contract  zone touch   prem   band | who    delta L | other leg | fut   | prem +15  +30 | fut +15 +30")
    ev = collections.Counter()
    for (k, sd), bl in sorted(B.items()):
        armed = {"d2": False, "u2": False}
        for i, b in enumerate(bl):
            if b["e"] < 565: continue
            z = zone(k, sd, spot[b["e"]])
            for t, hit in (("d2", b["l"] <= b["d2"]), ("u2", b["h"] >= b["u2"])):
                if z in ("ATM", "NEAR 1-2") and hit and not armed[t]:
                    armed[t] = True
                    other = next((x for x in B.get((k, "pe" if sd == "ce" else "ce"), []) if x["e"] == b["e"]), None)
                    f = fb.get(b["e"])
                    nx = lambda n: next((x["c"] for x in bl[i + 1:] if x["e"] >= b["e"] + n), None)
                    fx = lambda n: (fb.get(b["e"] + n) or {}).get("c")
                    p15, p30, w = nx(15), nx(30), who(b["doi"], b["d"])
                    ev[(t, w)] += 1
                    print(f"  {hm(b['e'])} {k}{sd.upper()} {z[:4]:>4} {pos(b):>5} {b['c']:6.1f} {b[t]:6.1f} | {w:5} {b['d'] / 1e5:+7.1f} | {str(pos(other)):>6} | {str(pos(f)):>5} |"
                          f" {('%+.1f' % (p15 - b['c'])) if p15 is not None else '-':>6} {('%+.1f' % (p30 - b['c'])) if p30 is not None else '-':>6} |"
                          f" {('%+.0f' % (fx(15) - f['c'])) if f and fx(15) else '-':>4} {('%+.0f' % (fx(30) - f['c'])) if f and fx(30) else '-':>4}")
                if (t == "d2" and b["c"] > b["vwap"]) or (t == "u2" and b["c"] < b["vwap"]):
                    armed[t] = False              # back through its VWAP: the next touch is a new episode
    print("  touches by flow at the touch:", dict(sorted(ev.items())))


for day in sys.argv[1:] or ("2026-11-02", "2026-11-03"):
    study(day)
