"""replay_all.py -- RAFTAAR over the chosen days, all three indices, written to replay/<IDX>_<day>.txt plus SUMMARY.txt.
Causal, rows not rates. stdlib only, read-only on the record; writes only inside this folder.

    python replay_all.py
"""
import os

import raftaar

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "replay")
DAYS = {
    "2026-10-08": "Thu · clean trend down (NIFTY -1.4 %, BNF -0.6 %, SENSEX -1.2 %) · SENSEX weekly expiry",
    "2026-10-21": "Wed · morning top then 470-pt break (NIFTY -1.4 %) · the day THE READ called RANGE at the top",
    "2026-10-22": "Thu · her 'range day, chop on both sides', a stop-loss day · SENSEX expiry",
    "2026-10-23": "Fri · down day (-0.8 %), §1o TREND ▼ at 11:30, CHOP by the close",
    "2026-10-26": "Mon · late start 09:33, bottom then rally (+1.3 %); THE READ said RANGE until 10:05",
    "2026-09-25": "Fri · range / pin day (0.49 % range, 23,040-23,130)",
    "2026-09-23": "Tue · NIFTY weekly expiry, range (0.47 %)",
    "2026-10-06": "Tue · NIFTY weekly expiry, trend up (+0.8 %, 2 mean crosses)",
    "2026-09-30": "Wed · chop (0.9 % range, round trip), her 198K seller at 12:50",
    "2026-10-27": "Tue · TODAY, Oct monthly expiry (NIFTY + BNF), record to ~12:14",
}
IDX = ("NIFTY", "BANKNIFTY", "SENSEX")


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = ["RAFTAAR replay summary -- minutes per word, stamped state lines, §1d front stamps (rows, not rates)", ""]
    for day, what in DAYS.items():
        rows_by = {}
        for idx in IDX:
            g = raftaar.load(idx, day)
            if g:
                rows_by[idx] = raftaar.read_day(g)[0]
        for idx in IDX:
            if idx not in rows_by:
                summary.append(f"{day} {idx}: no record")
                continue
            raftaar.peers(rows_by[idx], [rows_by[o] for o in IDX if o != idx and o in rows_by])
            lines = []
            raftaar.replay(idx, day, with_peers=False, out=lines.append, fronts=200)
            # re-print with the peers already attached (replay recomputed rows without peers; patch the stamped lines)
            rows = rows_by[idx]
            text = [lines[0], f"-- {what}", ""]
            text += [raftaar.line(r) for r in raftaar.stamped(rows)]
            text += [l for l in lines if l.startswith("--")]
            text += ["", "-- §1d front stamps (top-2 per side, changes only):"]
            text += [l for l in lines if l.startswith("   ")]
            with open(os.path.join(OUT, f"{idx}_{day}.txt"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(text) + "\n")
            census = [l for l in lines if l.startswith("-- minutes")][0][len("-- minutes: "):]
            st = len(raftaar.stamped(rows))
            fs = len([l for l in lines if l.startswith("   ")])
            summary.append(f"{day} {idx:<9} stamped {st:>2}  fronts {fs:>3}  | {census}")
        summary.append("")
    with open(os.path.join(OUT, "SUMMARY.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(summary) + "\n")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
