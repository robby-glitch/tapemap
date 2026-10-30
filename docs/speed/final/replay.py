"""replay.py -- the converged engine run causally over the chosen days, all three indices in lockstep (peers causal), with the
prior-session reference, the fut book and THE READ's words where recorded. Writes replay/<IDX>_<day>.txt and replay/SUMMARY.txt.

    python replay.py                       # the union of both round-1 day sets
    python replay.py 2026-10-22 ...        # chosen days
    python replay.py 2026-10-22 --all      # every minute's picture, not only the stamps
"""
import os
import sys

import chainio
import refbuild
import raftaar as R

OUT = os.path.join(chainio.HERE, "replay")
DAYS = ["2026-09-23", "2026-09-25", "2026-09-29", "2026-09-30", "2026-10-06", "2026-10-08", "2026-10-21", "2026-10-22",
        "2026-10-23", "2026-10-26", "2026-10-27"]
NOTE = {"2026-09-23": "NIFTY expiry · range", "2026-09-25": "range / pin", "2026-09-29": "NIFTY + BNF expiry, round trip",
        "2026-09-30": "chop", "2026-10-06": "NIFTY expiry · slow grind up", "2026-10-08": "clean trend down · SENSEX expiry",
        "2026-10-21": "top at 09:58 then -470", "2026-10-22": "her chop / stop-loss day · SENSEX expiry",
        "2026-10-23": "down day, §1o TREND ▼ 11:30 → CHOP", "2026-10-26": "late start 09:33, bottom then +300",
        "2026-10-27": "TODAY · Oct monthly expiry (NIFTY + BNF)"}


def run_day(day, show_all=False):
    engines, grids = {}, {}
    for idx in chainio.IDXS:
        grid, opens, kind = chainio.load_chain(idx, day)
        if not grid:
            continue
        ref = R.Ref(refbuild.load(idx))
        engines[idx] = R.Engine(idx, day, ref, kind, opens, chainio.load_fut(idx, day), read_words=chainio.load_read(idx, day))
        grids[idx] = grid
    minutes = sorted({t for g in grids.values() for t in g})
    pics = {idx: [] for idx in engines}
    for t in minutes:
        for idx, eng in engines.items():
            if t not in grids[idx]:
                continue
            peers = {o: R._peer_at(e.pic_hist, t) for o, e in engines.items() if o != idx}
            rw = R._read_word_at(eng.read_words, t) if eng.read_words else None
            pics[idx].append(eng.step(t, grids[idx][t], peers=peers, read_word=rw))
    summary = []
    for idx, eng in engines.items():
        lines = [f"== RAFTAAR (converged) · {idx} · {day} · {eng.kind} · {NOTE.get(day, '')} · size ref: {eng.ref.source()} · "
                 f"fut leg: {'yes' if eng.fut else 'no'} · READ log: {'yes' if eng.read_words else 'no'}", ""]
        strip = "".join(_glyph(p) for i, p in enumerate(pics[idx]) if i % 5 == 0)
        lines.append("strip (5 min): " + strip)
        lines.append("")
        for s in eng.stamps:
            g = f"  {s['grade']}" if s.get("grade") else ""
            lines.append(f"{s['t']}  {'' if s['spot'] is None else f'{s[chr(115)+chr(112)+chr(111)+chr(116)]:>8.0f}s'}  {s['title']:<34}{g:<16}  {s['why']}")
            if s.get("extra", {}).get("phanse"):
                ph = s["extra"]["phanse"]
                lines.append(" " * 20 + "PHANSE: " + ", ".join(f"{k:.0f} {R.lakh(b)} {tt} tak likha" for k, b, tt in ph))
        census = {}
        for p in pics[idx]:
            w = p["picture"]["word"] if p.get("picture") else "?"
            if p.get("picture") and p["picture"].get("dir") and w in ("CHAL RAHA", "WAPSI", "BINA OI"):
                w += " " + (R.UP if p["picture"]["dir"] > 0 else R.DN)
            census[w] = census.get(w, 0) + 1
        npic = sum(1 for s in eng.stamps if s["kind"] in ("picture", "quiet", "q"))
        nall = len(eng.stamps)
        lines += ["", "-- minutes: " + ", ".join(f"{k} {v}" for k, v in sorted(census.items(), key=lambda kv: -kv[1])),
                  f"-- stamps: {nall} (pictures / quiet / ? {npic}, phases + ends {sum(1 for s in eng.stamps if s['kind'] in ('phase', 'end'))}, "
                  f"side events {sum(1 for s in eng.stamps if s['kind'] == 'event')}, ≠ READ {sum(1 for s in eng.stamps if s['kind'] == 'neq')})"]
        if show_all:
            lines += ["", "-- every minute:"]
            for p in pics[idx]:
                lines.append(_minute(p))
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, f"{idx}_{day}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        summary.append(f"{day} {idx:<9} {eng.kind:<6} stamps {nall:>2} (pictures {npic:>2}) ≠READ {sum(1 for s in eng.stamps if s['kind'] == 'neq')}  | "
                       + ", ".join(f"{k} {v}" for k, v in sorted(census.items(), key=lambda kv: -kv[1])[:6]))
    return summary


def _glyph(p):
    pic = p.get("picture") or {}
    w = pic.get("word")
    if w == "?":
        return "?"
    if w in ("CHAL RAHA",):
        return R.UP if pic.get("dir", 0) > 0 else R.DN
    if w == "WAPSI":
        return "w"
    return {"CHOP": "~", "PIN": "P", "ATKA": "a", "UNWIND": "u", "BINA OI": "k", "KHAMOSH": "·"}.get(w, "·")


def _minute(p):
    pic = p.get("picture") or {}
    if pic.get("word") == "?":
        return f"{p['t']}  ?  {pic.get('why')}"
    g = pic.get("grade")
    gs = f"{g['n']}/{g['N']} {g['word']}" if g else "—"
    sd = p.get("sides") or {}
    return (f"{p['t']}  {p['spot']:>8.0f}s  {pic.get('word', ''):<10} {('' if not pic.get('dir') else (R.UP if pic['dir'] > 0 else R.DN)):<2} "
            f"{(pic.get('phase') or ''):<6} {gs:<14} {pic.get('story', ''):<34} CE {sd.get('CE', {}).get('structure', ''):<14} PE {sd.get('PE', {}).get('structure', ''):<14} "
            f"m15 {p['numbers']['m15']:+5.0f} Z {p['numbers']['Z_pct']:+6.2f}%")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_all = "--all" in sys.argv
    days = args or DAYS
    summary = ["RAFTAAR converged replay — stamps per index-day (rows, not rates). Reference: prior sessions of the same kind, "
               "rank.py cut-offs + the absolute clause.", ""]
    for d in days:
        summary += run_day(d, show_all)
        summary.append("")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "SUMMARY.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
