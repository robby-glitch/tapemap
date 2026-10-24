"""VALIDATE rev 2 vs rev 3 on her real trades -- descriptive, in-sample, no hit rates (VALIDATE-PREREG-rev3.md §6).

    python -X utf8 docs/hold/validate3/replay.py [OUT_DIR]

For each trade: the day's /api/v2/data payload (v2feed.serve, read-only) and the DECODE blocks the face would have had
at the entry (server._decode_all at the latest close readable then: close + 60 s <= entry), then replay.cjs runs the
rev 2 engine (git 5b9ed44) and the rev 3 engine (the working tree) on the same payload at the entry second. Nothing is
written outside OUT_DIR (default: a temp folder). The table is printed as Markdown."""
import json
import logging
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

# her trades: the fold records' marked / imported trades (data/fold/fold_*.jsonl, src != ifin) and the 22 Oct SENSEX CE
# (not marked: NOTEPAD 22 Oct 13:00, "spot 73,443, CE 191")
TRADES = [
    ("2026-10-22", "SENSEX", 73400, "CE", "BUY", 191.0, "13:00:00", "NOTEPAD 22 Oct 13:00"),
    ("2026-10-21", "NIFTY", 23000, "PE", "BUY", 174.85, "10:07:30", "marked"),
    ("2026-10-06", "NIFTY", 22600, "CE", "SELL", 65.8, "09:35:50", "marked"),
    ("2026-10-06", "NIFTY", 22650, "PE", "SELL", 55.9, "10:02:51", "marked"),
    ("2026-10-06", "NIFTY", 22650, "PE", "BUY", 55.0, "10:03:21", "marked"),
    ("2026-10-06", "NIFTY", 22600, "CE", "BUY", 133.0, "14:12:07", "marked"),
    ("2026-10-05", "NIFTY", 22600, "CE", "BUY", 94.25, "09:28:13", "marked"),
    ("2026-10-05", "NIFTY", 22550, "CE", "BUY", 134.95, "09:35:06", "marked"),
    ("2026-10-05", "NIFTY", 22550, "PE", "BUY", 174.75, "12:09:58", "marked"),
    ("2026-10-05", "NIFTY", 22650, "PE", "SELL", 131.35, "13:41:38", "marked"),
    ("2026-10-01", "NIFTY", 22600, "PE", "BUY", 142.4, "09:21:04", "import"),
    ("2026-10-01", "NIFTY", 22600, "PE", "BUY", 149.75, "09:26:45", "import"),
    ("2026-10-01", "SENSEX", 72400, "CE", "BUY", 209.4, "09:30:46", "import"),
    ("2026-10-01", "SENSEX", 72400, "CE", "BUY", 237.25, "10:00:48", "import"),
    ("2026-10-01", "SENSEX", 72400, "CE", "BUY", 276.05, "10:02:20", "import"),
    ("2026-10-01", "SENSEX", 72400, "PE", "BUY", 223.97, "12:06:38", "import"),
    ("2026-10-01", "SENSEX", 72400, "PE", "BUY", 281.45, "12:10:13", "import"),
    ("2026-10-01", "SENSEX", 72300, "PE", "BUY", 224.1, "12:10:20", "import"),
    ("2026-10-01", "SENSEX", 72300, "PE", "BUY", 232.0, "12:19:41", "import"),
    ("2026-10-01", "SENSEX", 72300, "PE", "BUY", 246.4, "12:22:35", "import"),
    ("2026-10-01", "SENSEX", 72300, "PE", "BUY", 296.9, "12:27:39", "import"),
    ("2026-09-30", "NIFTY", 22750, "CE", "BUY", 164.7, "10:10:12", "marked"),
    ("2026-09-29", "NIFTY", 22800, "PE", "BUY", 113.95, "09:18:07", "marked"),
]


TRADEBOOK = os.path.join("data", "fixtures-private", "tradebook_2026-09-21_24.csv")   # her broker fills, private: read if here


def tradebook_entries(path=TRADEBOOK):
    """Her opening fills from the broker tradebook: a buy (sell) while flat in that contract opens a long (short); adds and
    exits are not entries. [(day, idx, K, ty, side, price, HH:MM:SS, src)]"""
    import csv
    import re
    if not os.path.exists(path):
        return []
    net, out = {}, []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m = re.match(r"^(NIFTY|BANKNIFTY|SENSEX)\w*?(\d{5})(CE|PE)$", r["symbol"])
            if not m:
                continue
            key, q = (r["trade_date"], r["symbol"]), float(r["quantity"]) * (1 if r["trade_type"] == "buy" else -1)
            if net.get(key, 0) == 0:
                out.append((r["trade_date"], m.group(1), int(m.group(2)), m.group(3), "BUY" if q > 0 else "SELL",
                            float(r["price"]), r["order_execution_time"][11:19], f"tradebook exp {r['expiry_date']}"))
            net[key] = net.get(key, 0) + q
    return out


def sec(t):
    return int(t[:2]) * 3600 + int(t[3:5]) * 60 + int(t[6:8] or 0)


def main(out_dir):
    logging.disable(logging.CRITICAL)
    import server
    import v2feed
    os.makedirs(out_dir, exist_ok=True)
    trades = TRADES + [t for t in tradebook_entries() if t[0] >= "2026-09-22"]     # 21 Sep has no recorded chain
    days = sorted({t[0] for t in trades})
    for day in days:
        b = v2feed.serve(day)
        with open(os.path.join(out_dir, f"data_{day}.json"), "wb") as f:
            f.write(b if isinstance(b, bytes) else json.dumps(b, default=str).encode())
    dec = {}
    for day, idx, *_rest in trades:
        T = sec(_rest[4])
        c = (T - 60) // 300 * 300                    # the latest close readable at the entry (the server's grace)
        if (day, c) not in dec:
            dec[(day, c)] = server._decode_all(day, c, False)
    with open(os.path.join(out_dir, "decode.json"), "w", encoding="utf-8") as f:
        json.dump({f"{d}|{c}": v for (d, c), v in dec.items()}, f, ensure_ascii=False, default=str)
    rev2 = subprocess.run(["git", "show", "5b9ed44:ui-v2/public/validate2/engine.js"], capture_output=True, check=True).stdout
    with open(os.path.join(out_dir, "engine_rev2.js"), "wb") as f:
        f.write(rev2)
    with open(os.path.join(out_dir, "trades.json"), "w", encoding="utf-8") as f:
        json.dump([{"day": d, "idx": i, "K": k, "ty": ty, "side": sd, "p0": p, "t": t, "src": s} for d, i, k, ty, sd, p, t, s in trades], f)
    r = subprocess.run(["node", os.path.join(HERE, "replay.cjs"), out_dir, os.path.join(ROOT, "ui-v2", "public", "validate2", "engine.js")],
                       capture_output=True, text=True, encoding="utf-8")
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="validate3_")))
