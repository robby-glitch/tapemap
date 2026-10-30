"""tailread.py -- ONE incremental reader for the append-only day files (A175: the afternoon handshake pass re-read the
whole day every minute, 10-40 s). book_log / dext_log / confluence_log read a file whole each call; sides_log.BookTail
follows one chain file but folds it into the Sides grid. This keeps the parsed rows themselves.

rows(path) -> the file's JSON object rows, kept per path: a file that grew is read from the last offset only (a torn last
line is held until its newline lands, and returned meanwhile only if it already parses, as a full read would); a file
that shrank, or was rewritten in place at the same size, is read again from the start; another day is another path. A
day file daylog has gzipped (path + ".gz") is read whole, again only when its size changes. Missing -> []. Each call
returns a NEW list; the rows are shared, so a caller never mutates one. Used by handshake.load and jarvis.build. Stdlib
only, no clock.

ponytail: one process-wide lock, and at most KEEP files held (the least recently read is dropped); a NIFTY day is ~50 MB
of chain rows and ~65 MB of book rows parsed -- per-file locks or a reduced row if the server's memory ever says so.
"""
from __future__ import annotations

import collections
import gzip
import json
import os
import threading

KEEP = 16
_LOCK = threading.Lock()
_FILES: "collections.OrderedDict[str, dict]" = collections.OrderedDict()


def _parse(lines, out):
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if isinstance(r, dict):
            out.append(r)


def rows(path: str) -> list:
    p = path if os.path.exists(path) else path + ".gz" if os.path.exists(path + ".gz") else None
    if p is None:
        return []
    with _LOCK:
        try:
            st = os.stat(p)
        except OSError:
            return []
        size = st.st_size
        f = _FILES.pop(p, None)
        if f is None or size < f["off"] or (size == f["off"] and st.st_mtime_ns != f["mtime"]) or \
                (p.endswith(".gz") and size != f["off"]):
            f = {"off": 0, "rest": b"", "rows": [], "mtime": None}       # new, shrunk, or rewritten in place: from the start
        try:
            if p.endswith(".gz"):
                if f["off"] != size:
                    with gzip.open(p, "rb") as fh:
                        _parse(fh.read().split(b"\n"), f["rows"])
                    f["off"] = size
            elif size > f["off"]:
                with open(p, "rb") as fh:
                    fh.seek(f["off"])
                    chunk = fh.read()
                f["off"] += len(chunk)
                lines = (f["rest"] + chunk).split(b"\n")
                f["rest"] = lines.pop()
                _parse(lines, f["rows"])
        except OSError:
            return []
        f["mtime"] = st.st_mtime_ns
        _FILES[p] = f
        while len(_FILES) > KEEP:
            _FILES.popitem(last=False)
        out = list(f["rows"])
        _parse([f["rest"]], out)                       # a last line with no newline yet: only if it already parses
        return out
