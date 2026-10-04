"""Rebuild /api/oihist + /api/board-shaped payloads for a past day from data/chain.
Read-only on the repo. Usage: python replay.py NIFTY 2026-09-24 12:30 [out.json]"""
import gzip, json, os, sys
ROOT = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, ROOT)
import fronts, board  # noqa

def load(idx, day):
    p = os.path.join(ROOT, "data", "chain", f"chain_{idx}_{day}.jsonl")
    op = open
    if not os.path.exists(p):
        p += ".gz"; op = gzip.open
    snaps = []
    with op(p, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                snaps.append(json.loads(line))
            except Exception:
                pass
    return snaps

def build(idx, day, asof):
    minutes, peak, last = {}, {}, None
    for s in load(idx, day):
        ts = (s.get("ts") or "")[:5]
        if not ts or ts > asof or ts < "09:15":
            continue
        minutes[ts] = {"spot": s["spot"], "k": {str(r["k"]): [r["ce"].get("oi_chg") or 0.0, r["pe"].get("oi_chg") or 0.0] for r in s["strikes"]}}
        for r in s["strikes"]:
            for side in ("ce", "pe"):
                key = (float(r["k"]), side)
                peak[key] = max(peak.get(key, 0.0), r[side]["oi"])
        last = s
    opens = {}
    for r in (last or {}).get("strikes") or []:
        for side in ("ce", "pe"):
            leg = r[side]
            opens[(float(r["k"]), side)] = float(leg["oi"]) - float(leg.get("oi_chg") or 0)
    return minutes, peak, opens

def payloads(idx, day, asof):
    minutes, peak, opens = build(idx, day, asof)
    m2 = {t: {"spot": v["spot"], "k": {float(k): tuple(c) for k, c in v["k"].items()}} for t, v in minutes.items()}
    g = fronts.grid(m2)
    evs = fronts.folds(m2, g)
    first = board.first_fold(m2, evs, opens, peak, g)
    doc = board.read(m2, peak, opens, None, None, None, first=first, idx=idx, g=g, evs=evs,
                     trend_why="replay: no candles", levels=None)
    doc.update(idx=idx, day=day)
    rows = fronts.read(m2, peak)
    oih = {"ok": True, "idx": idx, "why": None, "fronts": rows or None, "broke": fronts.broke(rows),
           "minutes": minutes,
           "peak": [{"k": k, "side": s, "oi": v} for (k, s), v in sorted(peak.items())],
           "open": [{"k": k, "side": s, "oi": v} for (k, s), v in sorted(opens.items())],
           "folds": evs, "first": first}
    return doc, oih

if __name__ == "__main__":
    idx, day, asof = sys.argv[1], sys.argv[2], sys.argv[3]
    doc, oih = payloads(idx, day, asof)
    if len(sys.argv) > 4:
        json.dump({"board": doc, "oihist": oih}, open(sys.argv[4], "w"), default=str)
    print("asof", doc.get("asof"), "spot", doc.get("spot"), "step", doc.get("step"))
    print("HEAD:", doc["headline"]["text"])
    for f in doc.get("fronts") or []:
        print(f"  {f['side']} {f['k']:.0f} #{f['rank']} {f['state']:9s} peak_at {f['peak_at']} unwind_at {f['unwind_at']} "
              f"itm {f['itm']} built {f['built_label']} chg {f['chg']/1e5:.1f}L peak {f['peak']/1e5:.1f}L | {f['words']}")
    print("BROKE:", oih["broke"] and {k: oih['broke'][k] for k in ('k', 'side', 'state', 'peak_at')})
    print("FIRST:", doc.get("first"))
    print("folds:", len(doc.get("folds") or []), [(e['side'], e['k'], e['t']) for e in (doc.get('folds') or [])][-6:])
    sq = doc.get("squares") or {}
    for n in ("up", "dn"):
        p = sq.get(n)
        print(" ", n, p and [(x['px'], x['labels']) for x in p['sq']], p and p['paying'])
