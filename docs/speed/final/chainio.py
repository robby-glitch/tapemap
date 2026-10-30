"""chainio.py -- the I/O around the pure engine: chain record -> /api/oihist-shaped grid + opens; fut book; THE READ's words.
Read-only on tapemap/data. stdlib only. Shared by refbuild.py and replay.py."""
import datetime
import gzip
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TAPEMAP = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(TAPEMAP, "data")
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
EXPIRY_WD = {"NIFTY": 1, "SENSEX": 3}     # weekday fallback when the record carries no expiry field


def _open(path):
    if os.path.exists(path):
        return open(path, encoding="utf-8")
    if os.path.exists(path + ".gz"):
        return gzip.open(path + ".gz", "rt", encoding="utf-8")
    return None


def days(idx):
    d = os.path.join(DATA, "chain")
    return sorted(f[len(f"chain_{idx}_"):][:10] for f in os.listdir(d) if f.startswith(f"chain_{idx}_"))


def load_chain(idx, day):
    """(grid, opens, kind): grid = {"HH:MM": {"spot", "k": {str(k): [ce_chg, pe_chg]}}} (last row per minute, the server's
    rule), opens = {str(k): [ce_open, pe_open]} = oi - oi_chg at the strike's first row, kind = EXPIRY / NORMAL."""
    f = _open(os.path.join(DATA, "chain", f"chain_{idx}_{day}.jsonl"))
    if f is None:
        return None, None, None
    grid, opens, expiry = {}, {}, None
    with f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict) or r.get("spot") is None or not r.get("strikes") or not r.get("ts"):
                continue
            t = r["ts"][:5]
            if t < "09:15" or t > "15:30":
                continue
            expiry = expiry or r.get("expiry")
            k = {}
            for s in r["strikes"]:
                ce, pe = s.get("ce") or {}, s.get("pe") or {}
                cc, pc = float(ce.get("oi_chg") or 0.0), float(pe.get("oi_chg") or 0.0)
                k[str(int(s["k"]))] = [cc, pc]
                if str(int(s["k"])) not in opens:
                    opens[str(int(s["k"]))] = [float(ce.get("oi") or 0.0) - cc, float(pe.get("oi") or 0.0) - pc]
            grid[t] = {"spot": float(r["spot"]), "k": k}
    if expiry:
        kind = "EXPIRY" if expiry[:10] == day else "NORMAL"
    else:
        wd = datetime.date.fromisoformat(day).weekday()
        kind = "EXPIRY" if EXPIRY_WD.get(idx) == wd else "NORMAL"
    return grid, opens, kind


def load_fut(idx, day):
    """{"HH:MM": {"oi", "c"}} from the futures book (last row per minute). SENSEX reads NIFTY's book (§1q)."""
    src = "NIFTY" if idx == "SENSEX" else idx
    f = _open(os.path.join(DATA, "book", f"book_{src}_{day}.jsonl"))
    if f is None:
        return {}
    out = {}
    with f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict) or r.get("ltp") is None or not r.get("oi") or not isinstance(r.get("t"), (int, float)):
                continue
            m = int(r["t"] / 1000 + 19800) % 86400 // 60
            out["%02d:%02d" % divmod(m, 60)] = {"oi": float(r["oi"]), "c": float(r["ltp"])}
    return out


def load_read(idx, day):
    """[(t, word, dir)] from THE READ's forward log, sorted; [] when the day has none."""
    p = os.path.join(DATA, "read", f"read_{day}.jsonl")
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("idx") != idx or not r.get("word") or not r.get("t"):
                continue
            out.append((r["t"][:5], r["word"], r.get("dir") or None))
    out.sort()
    return out
