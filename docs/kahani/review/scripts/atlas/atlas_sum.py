"""Summarise atlas_legs.json: counts "n of N" per group, never a rate (house rule 4)."""
import tempfile
import collections
import json
import os

HERE = os.path.join(tempfile.gettempdir(), "jarvis_atlas")
L = json.load(open(os.path.join(HERE, "atlas_legs.json"), encoding="utf-8"))
ARR = {1: "▲", -1: "▼"}

RAN = [x for x in L if x["trend"] and x["pts"] >= 120]
SMALL = [x for x in L if x["trend"] and x["pts"] < 120]
DIED = [x for x in L if not x["trend"]]
print(f"legs {len(L)}: RAN (TREND, >=120 pts) {len(RAN)} · TREND <120 {len(SMALL)} · DIED (never TREND) {len(DIED)}")

BOOL = ["w_with", "w_against", "sides_with", "fuel_with", "fuel_against", "fast_with", "fast_against", "all3_with"]


def table(title, groups, tag):
    print(f"\n== {title} (snapshot at {tag}) ==")
    print("feature".ljust(26) + "".join(g.ljust(16) for g in groups))
    S = {g: [x[tag + "_snap"] for x in xs if x.get(tag + "_snap")] for g, xs in groups.items()}
    for b in BOOL:
        print(b.ljust(26) + "".join(f"{sum(1 for s in ss if s.get(b))} of {len(ss)}".ljust(16) for ss in S.values()))
    for b, f in (("push_with>=1", lambda s: s["push_with"] >= 1), ("push_against>=1", lambda s: s["push_against"] >= 1),
                 ("TOOT/PHANS with", lambda s: any(a in ("TOOT", "PHANS") for a in s["ans_with"])),
                 ("TIKI/NAHI with", lambda s: any(a in ("TIKI", "NAHI") for a in s["ans_with"])),
                 ("TOOT/PHANS against", lambda s: any(a in ("TOOT", "PHANS") for a in s["ans_against"])),
                 ("effort_with>=2", lambda s: (s["effort_with"] or 0) >= 2),
                 ("z>=1 (stretched)", lambda s: (s["z"] or 0) >= 1), ("z<=0 (from VWAP)", lambda s: (s["z"] or 0) <= 0),
                 ("before 10:00", lambda s: s["t"] < "10:00"), ("after 13:30", lambda s: s["t"] >= "13:30")):
        print(b.ljust(26) + "".join(f"{sum(1 for s in ss if f(s))} of {len(ss)}".ljust(16) for ss in S.values()))
    for cat in ("writers", "ahead_state", "behind_state", "fut_oi_word", "sides", "speed"):
        print(f"  {cat}:")
        keys = collections.Counter(s.get(cat) for ss in S.values() for s in ss)
        for k, _ in keys.most_common(7):
            print(("    " + str(k)).ljust(26) + "".join(f"{sum(1 for s in ss if s.get(cat) == k)} of {len(ss)}".ljust(16)
                                                     for ss in S.values()))


table("Moves when first visible: RAN vs SMALL vs DIED", {"RAN": RAN, "SMALL": SMALL, "DIED": DIED}, "birth")

T = [x for x in L if x.get("trend_snap")]
KEPT = [x for x in T if x["trend_snap"]["captured"] >= 40]
GAVE = [x for x in T if x["trend_snap"]["captured"] < 0]
MID = [x for x in T if 0 <= x["trend_snap"]["captured"] < 40]
table(f"At Jarvis's TREND call: kept >=40 pts ({len(KEPT)}) vs 0-40 ({len(MID)}) vs gave back <0 ({len(GAVE)})",
      {"KEPT>=40": KEPT, "0-40": MID, "GAVE<0": GAVE}, "trend")

print("\n== the best moves (pts), with the TREND-call trade ==")
for x in sorted(L, key=lambda x: -x["pts"])[:22]:
    b, t = x["birth_snap"], x.get("trend_snap")
    print(f"{x['day']} {ARR[x['dir']]} {x['pts']:>4} pts  origin {x['origin_t']} -> ext {x['extreme_t']}  born {x['birth']}"
          f"  TREND {x['trend'] or '-':>5}  end {x['end']} {x['exit_t']}  toot {x['toot'] or '-'} fuel {x['fuelled'] or '-'} "
          f"σ{x['sigma']:.1f}" + (f"  | in@TREND {t['entry']:.0f} kept {t['captured']:+.0f} mfe {t['mfe']:+.0f} mae {t['mae']:.0f}" if t else ""))
