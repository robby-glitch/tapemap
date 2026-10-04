"""daylog.py -- the four big daily records, compressed once a day is well past.

WHY (operator, 2026-09-23: "it's my personal laptop with like 120 GB left").
Each trading day writes ~400 MB -- senses ~240, frame ~100, chain ~37, book ~25
-- and nothing was ever pruned: ~8 GB a month. JSON lines compress 7-14x
(measured on 2026-09-22's own files), so an old day is kept WHOLE, byte for
byte, as <name>.jsonl.gz.

WHAT IS NEVER TOUCHED: today, and every day inside KEEP_PLAIN_DAYS. Before
09:15 GoCharting still shows the previous session and the extension posts
frames stamped with that day; a compressed yesterday would be shadowed by the
fresh plain file those posts create. A week covers any weekend or holiday gap.
data/trigger_log.jsonl lives in none of these folders.

SAFETY: the original is deleted only after the .gz decompresses back to the
same bytes (length + sha256). An interrupted run leaves both files identical;
readers prefer the plain one, and the next run finishes the job.

Readers go through `open_text` / `exists` with the PLAIN name and get either
form -- a caller never learns which one it read. Stdlib only.
"""
from __future__ import annotations

import gzip
import hashlib
import os
import re
from datetime import date, timedelta

DIRS = tuple(os.path.join("data", d) for d in ("senses", "frame", "book", "chain", "calls", "hold", "sides", "trap"))
KEEP_PLAIN_DAYS = 7
_DAY = re.compile(r"_(\d{4}-\d{2}-\d{2})\.jsonl$")


def exists(path: str) -> bool:
    return os.path.exists(path) or os.path.exists(path + ".gz")


def open_text(path: str):
    """The day file as text: the plain file while it exists, else its .gz.
    Raises FileNotFoundError (an OSError) when neither exists, like open()."""
    if os.path.exists(path):
        return open(path, encoding="utf-8")
    return gzip.open(path + ".gz", "rt", encoding="utf-8")


def _digest(fh):
    h, n = hashlib.sha256(), 0
    for chunk in iter(lambda: fh.read(1 << 20), b""):
        h.update(chunk)
        n += len(chunk)
    return h.hexdigest(), n


def compress_old(today: str, dirs=DIRS, keep_days: int = KEEP_PLAIN_DAYS, log=None):
    """gzip every `*_<day>.jsonl` older than `keep_days` before `today`.
    Returns (files, bytes_before, bytes_after). Never raises."""
    say = log or (lambda *_a: None)
    cutoff = (date.fromisoformat(today) - timedelta(days=keep_days)).isoformat()
    done = before = after = 0
    for d in dirs:
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for name in names:
            m = _DAY.search(name)
            if not m or m.group(1) >= cutoff:
                continue
            src = os.path.join(d, name)
            dst, tmp = src + ".gz", src + ".gz.tmp"
            try:
                with open(src, "rb") as fi, gzip.open(tmp, "wb", compresslevel=6) as fo:
                    for chunk in iter(lambda: fi.read(1 << 20), b""):
                        fo.write(chunk)
                with open(src, "rb") as a, gzip.open(tmp, "rb") as b:
                    if _digest(a) != _digest(b):
                        raise OSError("the .gz does not decompress to the original bytes")
                os.replace(tmp, dst)
                n0, n1 = os.path.getsize(src), os.path.getsize(dst)
                os.remove(src)
                done, before, after = done + 1, before + n0, after + n1
            except Exception as e:                     # noqa: BLE001 -- the original stays
                say(f"daylog: {src} left as it is -- {type(e).__name__}: {e}")
                try:
                    os.remove(tmp)
                except OSError:
                    pass
    if done:
        say(f"daylog: compressed {done} file(s) older than {cutoff}: "
            f"{before / 1e6:,.0f} MB -> {after / 1e6:,.0f} MB")
    return done, before, after


if __name__ == "__main__":
    import sys
    import tempfile
    if sys.argv[1:] == ["compress"]:                   # by hand: python daylog.py compress
        print(compress_old(date.today().isoformat(), log=print))
        raise SystemExit(0)
    with tempfile.TemporaryDirectory() as t:
        body = "".join('{"t": %d, "x": "%s"}\n' % (i, "y" * 50) for i in range(2000))
        for day in ("2026-09-01", "2026-09-20", "2026-09-23"):
            with open(os.path.join(t, f"frame_{day}.jsonl"), "w", encoding="utf-8") as f:
                f.write(body)
        n, b0, b1 = compress_old("2026-09-23", dirs=(t,))
        assert n == 1 and b1 < b0                                      # only the day older than a week
        assert sorted(os.listdir(t)) == ["frame_2026-09-01.jsonl.gz", "frame_2026-09-20.jsonl",
                                         "frame_2026-09-23.jsonl"]
        old = os.path.join(t, "frame_2026-09-01.jsonl")
        assert exists(old) and not exists(os.path.join(t, "frame_2026-08-01.jsonl"))
        with open_text(old) as fh:
            assert fh.read() == body                                   # byte for byte, read by the plain name
        assert compress_old("2026-09-23", dirs=(t,))[0] == 0           # idempotent
    print("daylog demo ok")
