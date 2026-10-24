"""The one voice, HOLD v2's line and the trade map over her 10 SENSEX trades, sensex_flow.ON False vs True
(docs/hold/SENSEX-NIFTY-FLOW-PREREG.md §6, a DRAFT) -- descriptive, in-sample, no hit rates.

    python -I -X utf8 docs/hold/validate3/replay31_voice.py OUT.json      (prints Markdown; writes only OUT.json)

Trades: the 9 SENSEX marks of 1 Oct (data/day_state/day_2026-10-01.json, verbatim) and 22 Oct 13:00 (not marked; rebuilt
as tools/voice_replay.py does). Each runs through voice_path.run to her exit + 15 min (rows after it are labelled). Then
the 22 Oct sanity check (§c): every NIFTY push of the day beside the SENSEX bar it was translated onto, and the NIFTY
engine's fights around her trade."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import confluence_log  # noqa: E402
import fold  # noqa: E402
import hold2  # noqa: E402
import sensex_flow  # noqa: E402
import ux_log  # noqa: E402
import voice_path  # noqa: E402

TRADES = [dict(day="2026-10-01", lot=20, tr=t) for t in json.load(open(os.path.join("data", "day_state", "day_2026-10-01.json"),
                                                                       encoding="utf-8"))["hold_trades"] if t["idx"] == "SENSEX"]
TRADES.append(dict(day="2026-10-22", lot=20, tr={"id": "SENSEX-73400CE-long-130000", "idx": "SENSEX", "k": 73400.0, "side": "CE",
                                                 "role": "long", "t0": "13:00:00", "p0": None, "exit_t": "13:25:00"}))


def side(c, on):
    sensex_flow.ON = on
    try:
        ex = c["tr"]["exit_t"]
        end = min(hold2.MARK, int(ex[:2]) * 60 + int(ex[3:5]) + 15)
        cc = dict(c, end=hold2.hm(end) + ":00")
        return voice_path.run(cc), cc
    finally:
        sensex_flow.ON = False


def digest(path, ex):
    """State changes, line moves, FLOW chip changes, l4 at entry / midpoint / her exit."""
    st, fl, last_s, last_f, moves = [], [], None, None, []
    for p in path:
        vc, aft = p["voice"], " [after her exit]" if p["t"] > ex[:5] else ""
        if vc.get("ok") and vc["state"] != last_s:
            st.append(f"{p['t']} {vc['state']}" + (f" ({vc['reason']})" if vc.get("reason") else "") + aft)
            last_s = vc["state"]
        f = ((p.get("chips") or {}).get("F"), ((p.get("view") or {}).get("sentences") or {}).get("F"))
        if f != last_f:
            fl.append(f"{p['t']} {f[0]} — {f[1]}{aft}")
            last_f = f
    h = (path[-1].get("hold2") or {}) if path else {}
    seen = set()                       # every frame re-runs the line from the engine's G of that minute: moves from all frames
    for p in path:
        for m in (p.get("hold2") or {}).get("moves") or ():
            k = (m["at"], m["t"], m["from"], m["to"])
            if k not in seen:
                seen.add(k)
                moves.append(f"{m['at']} {m['from']:,.1f} → {m['to']:,.1f}f (push {m['t']} {m.get('src')}, origin {m['origin']:,.2f}, "
                             f"U {m['U']}; seen at {p['t']})" + (" [after her exit]" if m["at"] > ex[:5] else ""))
    pre = [p for p in path if p["t"] <= ex[:5]] or path[:1]
    pick = {"entry": path[0] if path else None, "midpoint": pre[len(pre) // 2] if pre else None,
            "exit": next((p for p in path if p["t"] >= ex[:5]), path[-1] if path else None)}
    l4 = {k: (f"{p['t']} " + str((p["voice"] or {}).get("l4") or (p.get("map") or {}).get("why") or "—")) if p else "—"
          for k, p in pick.items()}
    skips = sorted({s.strip() for p in path for s in str(p.get("hold2_text") or "").split(" · NIFTY push ")[1:]})
    frames = [{"t": p["t"], "state": (p["voice"] or {}).get("state"), "reason": (p["voice"] or {}).get("reason"),
               "l3": (p["voice"] or {}).get("l3"), "stop_f": (p["voice"] or {}).get("stop_f"), "F": (p.get("chips") or {}).get("F"),
               "F_s": ((p.get("view") or {}).get("sentences") or {}).get("F"), "l4": (p["voice"] or {}).get("l4"),
               "G": ((p.get("view") or {}).get("G") or {}).get("px"), "fut": (p.get("view") or {}).get("fut"),
               "h2": p.get("hold2_text"), "line0": (p.get("hold2") or {}).get("line0")} for p in path]
    return dict(states=st, flow=fl, moves=moves, l4=l4, h2_last=h.get("text") or h.get("why"), skips=skips,
                v2_exit=h.get("v2_exit"), how=h.get("how"), frames=frames)


def sanity_22oct():
    """§c: every NIFTY push of 22 Oct beside its SENSEX bar, and the NIFTY engine's fixed fights 12:30-13:40."""
    day = "2026-10-22"
    nb5 = confluence_log.push_bars("NIFTY", day)
    nrefs, nwhy = confluence_log.push_refs("NIFTY", day)
    sb5 = confluence_log.push_bars("SENSEX", day, ux_rows=ux_log.read_bars(day, "SENSEX"))
    P = hold2.pushes(nb5, nrefs) if nrefs else []
    tr, skip = sensex_flow.translate(P, sb5)
    raw = json.load(open(os.path.join("data", "backtest", "SENSEX", f"fut_{day}.json"), encoding="utf-8"))
    one = {}
    for i, ts in enumerate(raw["timestamp"]):
        s = (int(ts if ts > 1e11 else ts * 1000) // 1000 + 19800) % 86400 if isinstance(ts, (int, float)) else \
            int(str(ts)[11:13]) * 3600 + int(str(ts)[14:16]) * 60
        one[s] = (raw["open"][i], raw["close"][i])
    nx = voice_path.nifty_side(day, voice_path.roll(day))
    cut = fold.ms(day, "13:40:00")
    nx["st"].feed(book=[k[2] for k in nx["keys"] if k[1] and k[0] < cut], chain=[k[2] for k in nx["keys"] if not k[1] and k[0] < cut])
    runs = [r for r in nx["st"].runs if "fixed_t" in r and fold.ms(day, "12:30:00") <= r["t1"] <= cut]
    flow = {t: nx["st"].flat_view(fold.ms(day, t))["rows"]["flow"] for t in ("12:56:00", "13:01:00", "13:06:00", "13:11:00",
                                                                              "13:16:00", "13:21:00", "13:25:00")}
    return dict(nifty_pushes=[{k: p[k] for k in ("t", "close", "d", "origin", "c", "src", "size", "R")} for p in P],
                translated=[{k: p[k] for k in ("t", "d", "origin", "c", "U", "n_origin", "n_src")} for p in tr],
                skipped=[p["t"] for p in skip],
                sensex_ux=[{"t": hold2.hm(b["s"] // 60), "o": b["o"], "c": b["c"]} for b in sb5 if 12 * 3600 + 30 * 60 <= b["s"] <= 13 * 3600 + 40 * 60],
                sensex_1m={hold2.hm(s // 60): one[s] for s in sorted(one) if 12 * 3600 + 30 * 60 <= s <= 13 * 3600 + 40 * 60},
                nifty_why=nwhy, nifty_refs={k: len(v.get("days") or ()) for k, v in (nrefs or {}).items()},
                nifty_fights=[{"t1": fold.hm(r["t1"]), "fixed": fold.hm(r["fixed_t"]), "winner": r["winner"], "vw": round(r["vw"], 1)} for r in runs],
                nifty_flow=flow)


if __name__ == "__main__":
    out = {}
    for c in TRADES:
        tid, ex = c["tr"]["id"], c["tr"]["exit_t"]
        res = {}
        for on in (False, True):
            path, cc = side(c, on)
            res["ON" if on else "OFF"] = digest(path, ex)
        res["p0"] = cc["tr"].get("p0")
        out[f"{c['day']} {tid}"] = res
        print(f"\n### {c['day']} {tid} (in {c['tr']['t0']}, out {ex})")
        for k in ("OFF", "ON"):
            r = res[k]
            print(f"- **{k}** states: " + " → ".join(r["states"]))
            print(f"  - line moves: {'; '.join(r['moves']) or 'none'}" + (f" · skipped: {', '.join(r['skips'])}" if r["skips"] else ""))
            print(f"  - FLOW chip: {' | '.join(r['flow'])}")
            print(f"  - l4: entry {r['l4']['entry']} | mid {r['l4']['midpoint']} | exit {r['l4']['exit']}")
            print(f"  - HOLD v2 last: {r['h2_last']} · v2 exit {r['v2_exit']}")
    out["sanity_22oct"] = sanity_22oct()
    with open(sys.argv[1] if len(sys.argv) > 1 else "replay31_voice.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("\n## sanity 22 Oct\n" + json.dumps(out["sanity_22oct"], ensure_ascii=False, indent=1, default=str))
