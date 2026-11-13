# -*- coding: utf-8 -*-
"""THE EDGE WALK (13 Nov 2026, on her "do you consider this as my edge ... how should i execute it"; NOTEPAD A313).

Every zone trigger on the saved NIFTY sessions, taken by HER rules, ONE position at a time:
  enter at the trigger bar's close · stop beyond the high / low made in the band · nothing new from 15:00 · flat at 15:00.
Five plain exits, none tuned, to show what holding is worth:
  1R    book at one times her risk             (a stand-in for booking early)
  VWAP  book at VWAP
  FAR   book at the far 2-sigma band           (the playbook's target for a turn)
  FLIP  hold until her own setup triggers the other way, then take that one
  HOLD  hold to 15:00
A same-side trigger while a trade is open is not taken (no adding). The stop is checked before the target in a minute.

Read-only. Futures points; no option premium; fills at the stop / target level (a real stop sits a little beyond).
Counts and points only; no rates.
    python -X utf8 docs/setup-review/look_edge_walk.py [--rows]
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import look_cause_effect as L  # noqa: E402

M, HM, OPEN, LAST = L.M, L.HM, L.OPEN, L.LAST
RULES = ("1R", "VWAP", "FAR", "FLIP", "HOLD")


def walk(d, rule):
    ent = {}
    for e in L.replay(d):
        ie = d["ix"].get(HM(M(e["t"]) + 2))
        if ie is not None and M(e["t"]) + 2 < LAST:
            ent.setdefault(ie, []).append(e)
    pos, out, tries, lastj = None, [], {"BUY": 0, "SELL": 0}, None

    def close(j, px, why):
        nonlocal pos
        out.append({"day": d["day"], "t": pos["t"], "side": pos["side"], "px": pos["px"], "risk": pos["risk"], "try": pos["try"],
                    "x": d["mins"][j], "why": why, "pts": pos["S"] * (px - pos["px"]), "against": pos["against"], "vw": pos["vw"]})
        pos = None

    for j, t in enumerate(d["mins"]):
        m = M(t)
        if m > LAST:
            break
        hi, lo, c = d["fhi"][j], d["flo"][j], d["fut"][j]
        if c is not None:
            lastj = j
        if pos and hi is not None and lo is not None:
            S, top = pos["S"], pos["S"] < 0
            bar = d["bars"].get(HM(OPEN + ((m - OPEN) // 3 - 1) * 3)) or {}        # the last closed 3-min bar's bands
            tgt = (pos["px"] + S * pos["risk"]) if rule == "1R" else bar.get("vwap") if rule == "VWAP" else \
                bar.get("d2" if top else "u2") if rule == "FAR" else None
            if (top and hi > pos["stop"]) or (not top and lo < pos["stop"]):
                close(j, pos["stop"], "STOP")
            elif tgt is not None and ((top and lo <= tgt) or (not top and hi >= tgt)):
                close(j, tgt, rule)
            elif m >= LAST and c is not None:
                close(j, c, "15:00")
        for e in ent.get(j, []):
            S = -1 if e["side"] == "SELL" else 1
            if pos and rule == "FLIP" and pos["S"] == -S and c is not None:
                close(j, c, "FLIP")
            if pos is None:
                tries[e["side"]] += 1
                sf = L.so_far(d, e["t"], S)                    # known at the trigger: her first-15-minute read, minutes since VWAP was held
                pos = {"t": e["t"], "side": e["side"], "S": S, "px": e["px"], "stop": e["ext"], "risk": abs(e["ext"] - e["px"]),
                       "try": tries[e["side"]], "against": sf["against"], "vw": sf["vw"]}
    if pos and lastj is not None:
        close(lastj, d["fut"][lastj], "15:00")
    return out


def main(argv):
    if L.free_mb() < 600:
        print(f"REFUSED: {L.free_mb():.0f} MB free (needs 600)")
        return 3
    paths = sorted(glob.glob(os.path.join(L.SCRATCH, "frame_NIFTY_*.json")) + glob.glob(os.path.join(L.SCRATCH, "live_NIFTY_*.json")),
                   key=lambda p: os.path.basename(p)[-15:])
    days, res, seen = [], {r: [] for r in RULES}, set()
    for p in paths:
        d = L.load(p)
        if not d or not d["exch"] or d["day"] in seen:
            continue
        seen.add(d["day"])
        lab, _ = L.day_label(d)
        days.append((d["day"], lab, sum(1 for e in L.replay(d) if M(e["t"]) + 2 < LAST)))
        for r in RULES:
            for x in walk(d, r):
                x["lab"] = lab
                res[r].append(x)
        del d
    tot = lambda xs: sum(x["pts"] for x in xs)                                    # noqa: E731
    print(f"{len(days)} sessions {days[0][0]} .. {days[-1][0]} · zone triggers before 15:00: {sum(x[2] for x in days)} "
          f"(per day: {min(x[2] for x in days)} to {max(x[2] for x in days)}, median {L.med([x[2] for x in days]):.0f}) · "
          f"days with none: {sum(1 for x in days if not x[2])} · one-way days by the hindsight label: {sum(1 for x in days if x[1])}")
    for r in RULES:
        T = res[r]
        w, l = [x for x in T if x["pts"] > 0], [x for x in T if x["pts"] <= 0]
        by, dayp = {}, {x[0]: 0.0 for x in days}
        for x in T:
            by[x["why"]] = by.get(x["why"], 0) + 1
            dayp[x["day"]] += x["pts"]
        dv = sorted(dayp.items(), key=lambda kv: kv[1])
        print(f"\n{r:5s} {len(T)} trades · exits {' · '.join(f'{k} {v}' for k, v in sorted(by.items()))}")
        print(f"      total {tot(T):+,.0f} pts = gains {tot(w):+,.0f} on {len(w)} · losses {tot(l):+,.0f} on {len(l)}"
              f" · stop away: median {L.med([x['risk'] for x in T]):.0f} pts · a gain: median {L.med([x['pts'] for x in w]):.0f}, biggest {max(x['pts'] for x in w):.0f}"
              f" · biggest loss {min(x['pts'] for x in l):.0f}")
        print(f"      days: up {sum(1 for v in dayp.values() if v > 0)} · down {sum(1 for v in dayp.values() if v < 0)} · no trade {sum(1 for x in days if not any(t['day'] == x[0] for t in T))}"
              f" · worst {dv[0][0][5:]} {dv[0][1]:+,.0f} · best {dv[-1][0][5:]} {dv[-1][1]:+,.0f}")
        print(f"      before {L.FOUND_FROM[5:]}: {tot([x for x in T if x['day'] < L.FOUND_FROM]):+,.0f} on {sum(1 for x in T if x['day'] < L.FOUND_FROM)}"
              f" · from then: {tot([x for x in T if x['day'] >= L.FOUND_FROM]):+,.0f} on {sum(1 for x in T if x['day'] >= L.FOUND_FROM)}"
              f" · one-way days: {tot([x for x in T if x['lab']]):+,.0f} on {sum(1 for x in T if x['lab'])} · two-sided: {tot([x for x in T if not x['lab']]):+,.0f} on {sum(1 for x in T if not x['lab'])}")
        print(f"      SELL {tot([x for x in T if x['side'] == 'SELL']):+,.0f} on {sum(1 for x in T if x['side'] == 'SELL')} · BUY {tot([x for x in T if x['side'] == 'BUY']):+,.0f} on {sum(1 for x in T if x['side'] == 'BUY')}"
              f" · first try of a side {tot([x for x in T if x['try'] == 1]):+,.0f} on {sum(1 for x in T if x['try'] == 1)} · later tries {tot([x for x in T if x['try'] > 1]):+,.0f} on {sum(1 for x in T if x['try'] > 1)}")
        ag, far = [x for x in T if x["against"]], [x for x in T if x["vw"] is not None and x["vw"] >= 120]
        top = sorted((x["pts"] for x in w), reverse=True)
        print(f"      LIVE at the trigger: against the first-15-minute side {tot(ag):+,.0f} on {len(ag)} · not against {tot([x for x in T if not x['against']]):+,.0f} on {len(T) - len(ag)}"
              f" · VWAP untouched 2 h or more {tot(far):+,.0f} on {len(far)} · under 2 h {tot([x for x in T if x not in far]):+,.0f} on {len(T) - len(far)}")
        print(f"      the biggest gains: {' '.join(f'{p:.0f}' for p in top[:6])} · total without the best two: {tot(T) - sum(top[:2]):+,.0f}")
        if "--rows" in argv and r in ("1R", "FAR"):
            for day, lab, n in days:
                tt = [x for x in T if x["day"] == day]
                print(f"        {day[5:]} {'one-way' if lab else 'two-sided':9s} {dayp[day]:+7.0f} · " +
                      " | ".join(f"{x['t']} {x['side'][0]} {x['why']} {x['pts']:+.0f}" for x in tt))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
