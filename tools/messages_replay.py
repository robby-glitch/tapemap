"""tools/messages_replay.py -- READ-ONLY: a day's MESSAGE STREAM rebuilt from its READ and DECODE logs by the server's own
builder (messages.build), oldest first; the lines Telegram would have sent are marked TG (telegram_out.wants -- the 10-min
freshness gate is live-only). TRADE and HEALTH exist only in the live record, data/messages/msg_<day>.jsonl: they are listed
after the stream when the server ran that day, never rebuilt. Writes nothing.

    python tools/messages_replay.py 2026-10-23
    python tools/messages_replay.py 2026-10-23 --json      the /api/messages reply shape (now + msgs), for a face check
"""
import gzip
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import messages  # noqa: E402
import telegram_out  # noqa: E402

DATA = os.path.join(HERE, "data")
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")        # instruments.ENABLED


def _rows(path):
    """A day file's rows (its .gz once daylog compressed it); a torn line is skipped; missing -> nothing."""
    for p in (path, path + ".gz"):
        if os.path.exists(p):
            with (gzip.open if p.endswith(".gz") else open)(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(r, dict):
                        yield r
            return


def main(day, as_json=False, data=DATA):
    rr = list(_rows(os.path.join(data, "read", f"read_{day}.jsonl")))
    dr = list(_rows(os.path.join(data, "decode", f"decode_{day}.jsonl")))
    if not rr and not dr:
        print(f"{day}: no READ or DECODE log on disk -- nothing to rebuild")
        return 1
    ms, now = messages.build(rr, dr), messages.now_rows(rr, dr, IDXS)
    if as_json:                                    # `at` = the order, so a face sorts them as the server would
        print(json.dumps({"ok": True, "day": day, "asof": "15:31:00", "now": now,
                          "msgs": [dict(m, at=i + 1) for i, m in enumerate(ms)]}, ensure_ascii=False))
        return 0
    for m in ms:
        print(("TG " if telegram_out.wants(m) else "   ") + m["line"])
    n = Counter(m["kind"] for m in ms)
    print(f"READ {n['READ']} · LEG {n['LEG']} · SETUP {n['SETUP']} · DIN {n['DIN']} · TG {sum(map(telegram_out.wants, ms))}"
          " (rebuilt; TRADE and HEALTH are live-only)")
    for r in _rows(os.path.join(data, "messages", f"msg_{day}.jsonl")):
        if r.get("kind") in ("TRADE", "HEALTH"):
            print(("TG " if telegram_out.wants(r) else "   ") + str(r.get("line")) + "   [live record]")
    print("NOW at the day's last mark:")
    for r in now:
        print("    " + r["line"])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if a != "--json"]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], "--json" in sys.argv[1:]))
