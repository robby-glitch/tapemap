"""tools/mstate_replay.py -- the market state's behaviour check (spec 2026-11-06 §9), on the record, never in market hours.

    python tools/mstate_replay.py 2026-10-28 2026-11-05                     # every recorded day between, all 3 indices
    python tools/mstate_replay.py 2026-11-05 2026-11-05 --json C:\\tmp\\x.json # the rows as JSON too (its own path)

Per day and index: jarvis.build(day, idx) as live saw it (fill off), then COUNTS -- the state word's changes and the
ACTION word's changes (the old word, separately), the zone rows (raw and de-duplicated), the cards by verdict, how many
were logged late, and the zone rows with no card ("not carded -- close beyond the record": card() is None when the close
is past the frame's end). Per day, when all three indices built, the cross-index read at every NIFTY minute. For 5 Nov it
prints spec §9's table as OBSERVED, one line each (minute, card line, state word): no row is asserted, no target is set,
no threshold is tuned on it (spec §11). Never a rate, never an outcome: no mfe / mae / stop_hit is read.
Refused 09:15-15:40 IST on a weekday. Read-only: nothing under data/ is written (only --json's own path).

De-duplication: the record holds one touch more than once (shifted `t`, rewrite batches). Rows and cards of the same
side and band whose `t` is within 3 minutes of the last one kept are ONE touch."""
import argparse
import datetime
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

VERDICTS = ("STRONG", "TAKE", "TAKE · smaller target", "SKIP")
from mstate import DUP_MIN  # noqa: E402  one touch, the same rule as mstate.trade's ADD (I1)


def refused(now=None):
    """True in market hours (weekday 09:15-15:40 IST): a replay never runs beside the live server's builds."""
    import fold
    now = now or datetime.datetime.now(fold.IST)
    return now.weekday() < 5 and "09:15" <= now.strftime("%H:%M") < "15:40"


def changes(xs):
    return sum(1 for a, b in zip(xs, xs[1:]) if a != b)


def _m(t):
    return int(t[:2]) * 60 + int(t[3:5])


def dedup(xs):
    """One touch once: same side + band, `t` within DUP_MIN of one kept. Order of the record kept."""
    kept = []
    for x in sorted(xs, key=lambda x: str(x["t"])[:5]):
        if not any(k.get("side") == x.get("side") and k.get("band") == x.get("band")
                   and 0 <= _m(str(x["t"])) - _m(str(k["t"])) <= DUP_MIN for k in kept):
            kept.append(x)
    return kept


def _triggers(d):
    return [z for z in d.get("zone") or () if not z.get("kind") and z.get("px") is not None]


def _acts(d):
    """The ACTION word per minute as said, or None when the frame has no ACTION series (named by the caller)."""
    import jarvis
    a = (d.get("reads") or {}).get("action") or []
    return [jarvis.said(x["word"], x["lean"]) for x in a] if len(a) == len(d["mins"]) else None


def tally(d, idx):
    """Counts for one built frame (no verdict beyond the engine's own words, no rate)."""
    zr, cr = _triggers(d), d.get("zone_cards") or []
    zd, cd = dedup(zr), dedup(cr)
    carded = {c["t"] for c in cr}
    acts = _acts(d)
    return {"day": d["day"], "idx": idx, "minutes": len(d["mins"]),
            "state_changes": changes([r["word"] for r in d.get("mstate") or ()]),
            "action_changes": None if acts is None else changes(acts),
            "zone_raw": len(zr), "zone_dedup": len(zd), "cards_raw": len(cr), "cards_dedup": len(cd),
            "cards": {v: sum(c["verdict"] == v for c in cd) for v in VERDICTS},
            "late_cards": sum(bool(c["late"]) for c in cd),
            "not_carded": [(str(z["t"])[:5], z["side"], z.get("band")) for z in zd if str(z["t"])[:5] not in carded],
            "failed": [x for x in d["health"]["notes"] if "market state failed" in x]}


def measure(day):
    """-> (one row per index, the frames built, the day's cross row)."""
    import jarvis
    import mstate
    rows, fr = [], {}
    for idx in mstate.IDXS:
        d = jarvis.build(day, idx)
        if not d.get("ok"):
            rows.append({"day": day, "idx": idx, "why": d.get("why")})
            continue
        fr[idx] = d
        rows.append(tally(d, idx))
    x = {"day": day, "trend_day_min": None, "rotation_min": None, "alerts": None}
    if len(fr) == 3:
        xs = [mstate.cross(fr, t, day) for t in fr["NIFTY"]["mins"]]
        x.update(trend_day_min=sum(bool(a["day"] and a["day"].startswith("TREND DAY")) for a in xs),
                 rotation_min=sum(bool(a["day"] and a["day"].startswith("ROTATION")) for a in xs),
                 alerts=sum(1 for a, b in zip([None] + xs, xs) if b["alert"] and not (a and a["alert"])))
    return rows, fr, x


def _state_at(d, t):
    return next((r["word"] for r in d.get("mstate") or () if r["t"] == t), None)


def checks(fr):
    """Spec §9's 5 Nov table as observed -> [(check, what the engine said)]."""
    def words(idx, a, b):
        d = fr.get(idx)
        return " / ".join(sorted({r["word"] for r in d.get("mstate") or () if a <= r["t"] <= b})) if d else "not built"

    def card(idx, t):
        d = fr.get(idx) or {}
        c = next((c for c in d.get("zone_cards") or () if c["t"] == t), None)
        if c:
            try:
                import mstate
                line = mstate.card_line(c)
            except Exception:                       # a hand-made card in a test: no signs / targets to print
                line = ""
            return f"{c['verdict']} — {c['why']}" + (f" | {line}" if line else "") + f" · state {_state_at(d, c['close'])}"
        if any(str(z["t"])[:5] == t for z in _triggers(d)):
            return "not carded — close beyond the record"
        return "no card (no trigger at that time on the record)"

    def at(idx, t):
        d = fr.get(idx)
        if not d:
            return "not built"
        acts = _acts(d)
        a = ("could not check — no ACTION series" if acts is None else
             acts[d["mins"].index(t)] if t in d["mins"] else "minute not on the record")
        return f"state {_state_at(d, t)} · action {a}"
    return [("09:36–10:00 NIFTY word", words("NIFTY", "09:36", "10:00")),
            ("09:36–10:00 SENSEX word", words("SENSEX", "09:36", "10:00")),
            ("12:30 NIFTY u2 sell", card("NIFTY", "12:30")),
            ("13:51 NIFTY sell", card("NIFTY", "13:51")),
            ("14:09 NIFTY sell", card("NIFTY", "14:09")),
            ("10:55 SENSEX d2 buy (late)", card("SENSEX", "10:55"))] + \
           [(f"14:24 {i} words", at(i, "14:24")) for i in ("NIFTY", "SENSEX", "BANKNIFTY")]


def line(r):
    ac = "could not check" if r["action_changes"] is None else r["action_changes"]
    nc = (f" · not carded — close beyond the record: {len(r['not_carded'])} "
          + ", ".join(f"{t} {s} {b}" for t, s, b in r["not_carded"])) if r["not_carded"] else ""
    return (f"{r['minutes']} min · state changes {r['state_changes']} · ACTION changes {ac} · "
            f"zone rows {r['zone_raw']} raw / {r['zone_dedup']} de-duplicated · cards {r['cards_raw']} raw / "
            f"{r['cards_dedup']} de-duplicated: " + " / ".join(f"{k} {v}" for k, v in r["cards"].items())
            + f" · late {r['late_cards']}" + nc + (f" · FAILED {r['failed']}" if r["failed"] else ""))


def main(argv=None, now=None):
    ap = argparse.ArgumentParser(description="the market state's behaviour check (spec §9)")
    ap.add_argument("start")
    ap.add_argument("end")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    if refused(now):
        print("refused: a replay never runs 09:15-15:40 IST on a weekday (spec §9)")
        return 2
    os.chdir(ROOT)
    import jarvis
    out = []
    for day in [x for x in jarvis.days()["NIFTY"] if a.start <= x <= a.end]:
        rows, fr, x = measure(day)
        out.append({"rows": rows, "cross": x, "checks": checks(fr) if day == "2026-11-05" else None})
        for r in rows:
            print(r["day"], r["idx"], r["why"] if "why" in r else line(r))
        print(day, "cross:", "could not check — fewer than 3 indices built" if x["trend_day_min"] is None else
              f"TREND DAY {x['trend_day_min']} min · ROTATION {x['rotation_min']} min · COIL → ESCAPE {x['alerts']}×")
        for k, v in out[-1]["checks"] or ():
            print("   ", k, "→", v)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
