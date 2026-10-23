"""v2feed.py -- the VALIDATE face's feed: the day files, tailed by byte offset, as one compact payload.

GET /api/v2/data?day=YYYY-MM-DD[&since=<sec>] (server.py) -> serve(). The first call is the whole day in the shape
ui-v2/public/validate2/engine.js loads (the shape docs/validate2/app/build_data.py wrote for the 2026-10-06
prototype); a call with since=<sec of day> is a delta the face merges with merge() below (the same rule, in
Python, so a test can prove delta + earlier payload == full).

Read-only. Every number is the recorder's own [M]: data/chain/chain_<IDX>_<day>.jsonl (a row every ~10 s),
data/book/book_<IDX>_<day>.jsonl (futures ticks -> 1-s bars with a signed volume: a trade at/above the prior best
ask is a buy, at/below the prior best bid a sell, else the tick rule), data/vpin_fast.jsonl (NIFTY buckets). A day
daylog.py has gzipped (<name>.jsonl.gz) is read whole once. Anytime-start: the state is rebuilt from the files
whenever the process starts, so a server started at 11:00 answers 09:17 onward; a file that shrank (rotation)
rebuilds from byte 0. Nothing here invents a fresher row than the recorder wrote.

LATE START (the anytime-start rule, 2026-10-07: the server came up 13:06, the chain file starts 13:07). The morning
chain_backfill.py rebuilt from REST -- data/chain_backfill/backfill_<IDX>_<day>.jsonl, one mark per minute with
`oi_chg` = OI(t) minus OI at the day's first candle and `px` = LTP -- is PREPENDED before the first recorded row,
tagged: the first `bf` rows are [I]. Absolute OI for a rebuilt minute = the first recorded row's OI minus its own
oi_chg (both "since the open", the same base) plus the minute's oi_chg; a strike the recorded window never carried has
no anchor and stays None. Recorded rows always win: no rebuilt minute at or after the first recorded row's minute.
What cannot be rebuilt is said, not faked: the futures ticks before the start are gone (a minute candle has no
aggressor side), so bars / CVD / VWAP begin at `flowFrom`; delta, day-avg, IV and greeks of rebuilt minutes are None.
"""
import bisect
import copy
import datetime
import gzip
import json
import os
import threading

IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
LOTS = {"NIFTY": 65, "BANKNIFTY": 30, "SENSEX": 20}       # ponytail: lot sizes as of 2026-10; instruments.py when it carries them
EACH_SIDE = 8                                               # ATM +/- 8 strikes kept (the recorder's own window)
SLOW_EVERY = 6                                              # delta and day-avg kept every 6th chain row (~1 min)
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
KEEP_DAYS = 3                                               # days held in memory at once


def sec_of(ts):
    h, m, s = str(ts).split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def today():
    return datetime.datetime.now(IST).strftime("%Y-%m-%d")


def now_sec():
    d = datetime.datetime.now(IST)
    return d.hour * 3600 + d.minute * 60 + d.second


def _hm(s):
    return None if s is None else "%02d:%02d" % (s // 3600, s % 3600 // 60)


def _hms(s):
    return None if s is None else "%02d:%02d:%02d" % (s // 3600, s % 3600 // 60, s % 60)


def _parse(line):
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except ValueError:                      # a torn line while the recorder writes it; the next read completes it
        return None


class Reset(Exception):
    """The file shrank under us (rotation): rebuild from byte 0."""


class Tail:
    """One day file read by byte offset; its .jsonl.gz twin (daylog.py) is read whole, once."""

    def __init__(self, path):
        self.path, self.off, self.buf, self.gz_done = path, 0, b"", False

    def signature(self):
        for p in (self.path, self.path + ".gz"):
            if os.path.exists(p):
                return os.path.getsize(p)
        return -1

    def rows(self):
        """New complete rows since the last call (a partial last line waits for its newline)."""
        p = self.path
        if os.path.exists(p):
            size = os.path.getsize(p)
            if size < self.off:
                raise Reset()
            if size == self.off:
                return []
            with open(p, "rb") as fh:
                fh.seek(self.off)
                chunk = fh.read()
            self.off += len(chunk)
            lines = (self.buf + chunk).split(b"\n")
            self.buf = lines.pop()
            return [r for r in (_parse(ln) for ln in lines) if r is not None]
        gz = p + ".gz"
        if os.path.exists(gz) and not self.gz_done:
            self.gz_done = True
            with gzip.open(gz, "rb") as fh:
                data = fh.read()
            return [r for r in (_parse(ln) for ln in data.split(b"\n")) if r is not None]
        return []

    def restart(self):
        self.off, self.buf, self.gz_done = 0, b"", False


def _leg():
    return {"oi": [], "ltp": [], "d": [], "avg": [], "iv": []}


WIRE = ("oi", "ltp", "d", "avg")                            # the leg fields the VALIDATE face reads; "iv" stays in memory


class IdxState:
    """One index's day: the chain rows (ATM +/- 8, every row) and the futures 1-s bars, grown row by row."""

    slow_every = SLOW_EVERY                                   # read.from_v2 reads the slow rows' stride off the state

    def __init__(self, idx, day, data_dir):
        self.idx, self.day = idx, day
        self.chain = Tail(os.path.join(data_dir, "chain", f"chain_{idx}_{day}.jsonl"))
        self.book = Tail(os.path.join(data_dir, "book", f"book_{idx}_{day}.jsonl"))
        self.bf_path = os.path.join(data_dir, "chain_backfill", f"backfill_{idx}_{day}.jsonl")
        self.gen, self.bf_rebuilt = 0, False
        self.reset()

    def reset(self):
        self.bf, self.bf_from, self.bf_to, self.bf_tried, self.chain_from = 0, None, None, False, None
        self.step = self.expiry = self.fut_expiry = None
        self.ks, self.pos = [], {}
        self.base = {"ce": {}, "pe": {}}                      # strike -> OI at yesterday's close, thousands (read.py's aaj likha)
        self.t, self.spot, self.atm = [], [], []
        self.ce, self.pe = _leg(), _leg()
        self.bars, self.futoi = [], []
        # [sec, high x 10, low x 10] beside each 1-s bar: every tick's extreme, so the day's high / low is the ticks',
        # never a grid's (decode-loop D6). In memory only, like the legs' "iv"; the wire is unchanged.
        self.hl = []
        self.prev, self.last_side, self.cur = None, 1, None
        self.n = 0                                            # self.gen bumps when the row layout changes: clients reload full

    def refresh(self):
        try:
            crows, brows = self.chain.rows(), self.book.rows()
        except Reset:
            self._rebuild()
            crows, brows = self.chain.rows(), self.book.rows()
        for r in crows:
            self._chain_row(r)
        for r in brows:
            self._tick(r)
        # the backfill file landed after recorded rows were already out (the server writes it a minute or two after it
        # starts): rebuild once from byte 0 so the morning is prepended, and every client reloads (gen)
        if self.n and not self.bf and not self.bf_rebuilt and os.path.exists(self.bf_path):
            self.bf_rebuilt = True
            self._rebuild()
            for r in self.chain.rows():
                self._chain_row(r)
            for r in self.book.rows():
                self._tick(r)

    def _rebuild(self):
        self.gen += 1
        self.reset()
        self.chain.restart()
        self.book.restart()

    # -- chain --
    def _chain_row(self, r):
        strikes = r.get("strikes") or []
        if len(strikes) < 2 or "atm" not in r or "spot" not in r:
            return
        if self.step is None:
            self.step = strikes[1]["k"] - strikes[0]["k"]
            self.expiry = r.get("expiry")
        if self.n == 0 and not self.bf_tried:
            self.bf_tried = True
            self._prepend_backfill(r)
            self.chain_from = r.get("ts") or _hms(r.get("sec"))
        atm = r["atm"]
        want = [s for s in strikes if abs(s["k"] - atm) <= EACH_SIDE * self.step]
        new = sorted({s["k"] for s in want} - set(self.pos))
        if new:
            self._widen(new)
        i = self.n
        self.n += 1
        self.t.append(r["sec"] if "sec" in r else sec_of(r["ts"]))
        self.spot.append(round(r["spot"], 1))
        self.atm.append(atm)
        slow = i % SLOW_EVERY == 0
        nk = len(self.ks)
        for leg, L in (("ce", self.ce), ("pe", self.pe)):
            oi, ltp, d, avg, iv = [None] * nk, [None] * nk, [None] * nk, [None] * nk, [None] * nk
            for s in want:
                k = self.pos[s["k"]]
                g = s.get(leg) or {}
                if "oi" not in g or "ltp" not in g:
                    continue
                if g.get("oi_chg") is not None and s["k"] not in self.base[leg]:
                    self.base[leg][s["k"]] = round((g["oi"] - g["oi_chg"]) / 1000)   # oi_chg is vs yesterday's close
                oi[k] = round(g["oi"] / 1000)                  # OI in thousands (309.1L = 30910)
                ltp[k] = round(g["ltp"] * 20)                  # price in 0.05 ticks
                d[k] = round((g.get("delta") or 0) * 100)      # delta x100
                avg[k] = round(g.get("avg") or 0)              # day's traded average, whole rupees
                if isinstance(g.get("iv"), (int, float)):
                    iv[k] = round(g["iv"] * 10000)             # IV in basis points of vol (0.1660 -> 1660); None when not given
            L["oi"].append(oi)
            L["ltp"].append(ltp)
            if slow:
                L["d"].append(d)
                L["avg"].append(avg)
                L["iv"].append(iv)

    def _prepend_backfill(self, first):
        """The rebuilt morning (chain_backfill.py) before the first recorded row, tagged [I]; recorded wins the minute."""
        rows = []
        for p in (self.bf_path, self.bf_path + ".gz"):
            if os.path.exists(p):
                opener = gzip.open if p.endswith(".gz") else open
                with opener(p, "rb") as fh:
                    rows = [x for x in (_parse(ln) for ln in fh.read().split(b"\n")) if x is not None]
                break
        first_sec = first["sec"] if "sec" in first else sec_of(first["ts"])
        marks = {}
        for x in rows:
            if not x.get("backfilled") or x.get("spot") is None or not isinstance(x.get("t"), str):
                continue
            try:
                m = sec_of(x["t"] + ":00")
            except ValueError:
                continue
            if m + 60 <= first_sec:                              # the whole minute lies before the first recorded row
                marks[m] = x
        if not marks:
            return
        anchor = {}                                              # (k, leg) -> (OI_first, oi_chg_first): both "since the open"
        for st in first["strikes"]:
            for leg in ("ce", "pe"):
                g = st.get(leg) or {}
                if g.get("oi") is not None and g.get("oi_chg") is not None:
                    anchor[(float(st["k"]), leg)] = (g["oi"], g["oi_chg"])
        ks = sorted({float(k) for x in marks.values() for k in (x.get("k") or {})} | {k for k, _ in anchor})
        new = [k for k in ks if k not in self.pos]
        if new:
            self.ks = sorted(set(self.ks) | set(new))
            self.pos = {k: i for i, k in enumerate(self.ks)}
        nk = len(self.ks)
        for i, m in enumerate(sorted(marks)):
            x = marks[m]
            self.t.append(m)
            self.spot.append(round(x["spot"], 1))
            self.atm.append(int(round(x["spot"] / self.step) * self.step))
            slow = i % SLOW_EVERY == 0
            for li, (leg, L) in enumerate((("ce", self.ce), ("pe", self.pe))):
                oi, ltp = [None] * nk, [None] * nk
                for k_s, chg in (x.get("k") or {}).items():
                    k = float(k_s)
                    a = anchor.get((k, leg))
                    if a is not None and chg is not None and chg[li] is not None:
                        oi[self.pos[k]] = round((a[0] - a[1] + chg[li]) / 1000)   # [I]: OI_first - oi_chg_first + oi_chg(t)
                for k_s, px in (x.get("px") or {}).items():
                    k = float(k_s)
                    if k in self.pos and px is not None and px[li] is not None:
                        ltp[self.pos[k]] = round(px[li] * 20)
                L["oi"].append(oi)
                L["ltp"].append(ltp)
                if slow:                                         # a REST candle has no delta, day-avg or IV: None, said
                    L["d"].append([None] * nk)
                    L["avg"].append([None] * nk)
                    L["iv"].append([None] * nk)
            self.n += 1
        self.bf, self.bf_from, self.bf_to = len(marks), _hm(min(marks)), _hm(max(marks))

    def _widen(self, new):
        """A strike outside the union appeared (the ATM walked): re-align every row kept so far."""
        old = self.ks
        self.ks = sorted(set(old) | set(new))
        self.pos = {k: i for i, k in enumerate(self.ks)}
        if old and self.n:
            idx = [self.pos[k] for k in old]
            nk = len(self.ks)
            for L in (self.ce, self.pe):
                for f in ("oi", "ltp", "d", "avg", "iv"):
                    for n, row in enumerate(L[f]):
                        out = [None] * nk
                        for j, v in zip(idx, row):
                            out[j] = v
                        L[f][n] = out
            self.gen += 1

    # -- book --
    def _tick(self, r):
        if "t" not in r or "ltp" not in r or "vtt" not in r:
            return
        self.fut_expiry = self.fut_expiry or r.get("expiry")
        sec = int(r["t"] // 1000 + 19800) % 86400
        ltp, prev = r["ltp"], self.prev
        if prev is None:
            vol, side = 0, 1
        else:
            vol = max(0, r["vtt"] - prev["vtt"])
            ask = prev["a"][0][0] if prev.get("a") else None
            bid = prev["b"][0][0] if prev.get("b") else None
            if ask is not None and ltp >= ask:
                side = 1
            elif bid is not None and ltp <= bid:
                side = -1
            elif ltp > prev["ltp"]:
                side = 1
            elif ltp < prev["ltp"]:
                side = -1
            else:
                side = self.last_side
        self.last_side = side
        if self.cur is None or self.cur[0] != sec:
            self.cur = [sec, round(ltp * 10), 0, 0]
            self.bars.append(self.cur)                         # the open second is visible at once; it grows in place
            self.hl.append([sec, round(ltp * 10), round(ltp * 10)])
        self.cur[1] = round(ltp * 10)
        self.hl[-1][1], self.hl[-1][2] = max(self.hl[-1][1], self.cur[1]), min(self.hl[-1][2], self.cur[1])
        self.cur[2] += vol
        if side > 0:
            self.cur[3] += vol
        m = sec - sec % 60
        if not self.futoi or self.futoi[-1][0] != m:
            self.futoi.append([m, r.get("oi")])
        else:
            self.futoi[-1][1] = r.get("oi")
        self.prev = r

    # -- payloads --
    def full(self):
        return {"step": self.step, "expiry": self.expiry, "lot": LOTS.get(self.idx), "ks": self.ks, "slowEvery": SLOW_EVERY,
                "gen": self.gen, "t": self.t, "spot": self.spot, "atm": self.atm,
                "ce": {f: self.ce[f] for f in WIRE}, "pe": {f: self.pe[f] for f in WIRE},
                "bars": self.bars, "futoi": self.futoi, "futExpiry": self.fut_expiry,
                "bf": self.bf, "bfFrom": self.bf_from, "bfTo": self.bf_to, "chainFrom": self.chain_from,
                "flowFrom": _hms(self.bars[0][0]) if self.bars else None,
                "bfWhy": None if not self.bf else ("the first %d rows (%s-%s) are chain_backfill.py's REST minutes [I]: OI = first recorded OI - its oi_chg + "
                                                   "the minute's oi_chg; LTP from the candle; no delta / day-avg; futures ticks before flowFrom are lost" % (self.bf, self.bf_from, self.bf_to))}

    def delta(self, since):
        """Rows after `since`: chain rows with t > since, the bars from the second of `since` on (that bar may have
        grown), the minute of `since` on for the futures OI. i0 / d0 say where the client truncates before appending."""
        i0 = bisect.bisect_right(self.t, since)
        d0 = (i0 + SLOW_EVERY - 1) // SLOW_EVERY
        j0 = bisect.bisect_left([b[0] for b in self.bars], since)
        m0 = bisect.bisect_left([m[0] for m in self.futoi], since - since % 60)
        return {"gen": self.gen, "i0": i0, "d0": d0, "t": self.t[i0:], "spot": self.spot[i0:], "atm": self.atm[i0:],
                "ce": {"oi": self.ce["oi"][i0:], "ltp": self.ce["ltp"][i0:], "d": self.ce["d"][d0:], "avg": self.ce["avg"][d0:]},
                "pe": {"oi": self.pe["oi"][i0:], "ltp": self.pe["ltp"][i0:], "d": self.pe["d"][d0:], "avg": self.pe["avg"][d0:]},
                "bars": self.bars[j0:], "futoi": self.futoi[m0:]}


class VpinState:
    """data/vpin_fast.jsonl is one file across days: the rows of this day, tailed."""

    def __init__(self, day, data_dir):
        self.day = day
        self.tail = Tail(os.path.join(data_dir, "vpin_fast.jsonl"))
        self.rows = []

    def refresh(self):
        try:
            new = self.tail.rows()
        except Reset:
            self.rows = []
            self.tail.restart()
            new = self.tail.rows()
        for r in new:
            if r.get("day") != self.day or "at" not in r:
                continue
            v = (r.get("buy") or 0) + (r.get("sell") or 0)
            self.rows.append([sec_of(r["at"]), r.get("bucket"), round(((r.get("buy") or 0) - (r.get("sell") or 0)) / v, 4) if v else 0,
                              r.get("vpin"), r.get("pct")])

    def since(self, s):
        return [r for r in self.rows if r[0] > s]


class Day:
    def __init__(self, day, data_dir=DATA):
        self.day = day
        self.idx = {i: IdxState(i, day, data_dir) for i in IDXS}
        self.vpin = VpinState(day, data_dir)

    def refresh(self):
        for s in self.idx.values():
            s.refresh()
        self.vpin.refresh()

    def signature(self):
        return tuple(s.chain.signature() for s in self.idx.values()) + tuple(s.book.signature() for s in self.idx.values()) \
            + (self.vpin.tail.signature(),)

    def full(self, now=None, live=None):
        return {"ok": True, "day": self.day, "live": self.day == today() if live is None else live,
                "now": now_sec() if now is None else now, "source": "data/chain + data/book + data/vpin_fast, recorder rows [M]",
                "idx": {i: s.full() for i, s in self.idx.items()}, "vpin": self.vpin.rows}

    def delta(self, since, now=None, live=None):
        return {"ok": True, "day": self.day, "delta": True, "since": since, "live": self.day == today() if live is None else live,
                "now": now_sec() if now is None else now,
                "idx": {i: s.delta(since) for i, s in self.idx.items()}, "vpin": self.vpin.since(since)}


def merge(full, delta):
    """The face's merge rule, in Python: full + delta(since) == a later full. A widened strike union (gen) means reload."""
    out = copy.deepcopy(full)
    for i, d in delta["idx"].items():
        x = out["idx"][i]
        if d["gen"] != x.get("gen", 0):
            raise ValueError(f"{i}: strike union changed (gen {x.get('gen', 0)} -> {d['gen']}), reload full")
        i0, d0 = d["i0"], d["d0"]
        for f in ("t", "spot", "atm"):
            x[f][i0:] = d[f]
        for leg in ("ce", "pe"):
            for f in ("oi", "ltp"):
                x[leg][f][i0:] = d[leg][f]
            for f in ("d", "avg"):
                x[leg][f][d0:] = d[leg][f]
        if d["bars"]:
            t0 = d["bars"][0][0]
            x["bars"] = [b for b in x["bars"] if b[0] < t0] + d["bars"]
        if d["futoi"]:
            m0 = d["futoi"][0][0]
            x["futoi"] = [m for m in x["futoi"] if m[0] < m0] + d["futoi"]
    if delta["vpin"]:
        s0 = delta["vpin"][0][0]
        out["vpin"] = [v for v in out["vpin"] if v[0] < s0] + delta["vpin"]
    out["now"], out["live"] = delta["now"], delta["live"]
    return out


# -- the server's door: one Day per date, kept warm; the full payload's bytes cached per (day, file sizes) --
_DAYS, _FULL, _LOCK = {}, {}, threading.Lock()


def with_day(day, fn, data_dir=DATA):
    """fn(Day) on the refreshed day, under the one lock: /api/read reads the same rows the VALIDATE face does."""
    with _LOCK:
        D = _DAYS.get(day)
        if D is None:
            D = _DAYS[day] = Day(day, data_dir)
            for old in sorted(_DAYS)[:-KEEP_DAYS]:
                _DAYS.pop(old, None)
                _FULL.pop(old, None)
        D.refresh()
        return fn(D)


def serve(day, since=None, data_dir=DATA):
    """bytes (the cached full JSON) when since is None, else the delta dict. Never raises for a missing day: an
    empty day is a valid payload (no rows), which the face shows as feed-dead / no chain yet."""
    with _LOCK:
        D = _DAYS.get(day)
        if D is None:
            D = _DAYS[day] = Day(day, data_dir)
            for old in sorted(_DAYS)[:-KEEP_DAYS]:
                _DAYS.pop(old, None)
                _FULL.pop(old, None)
        D.refresh()
        now, live = now_sec(), day == today()
        if since is None or str(since) == "" or not str(since).lstrip("-").isdigit():
            sig = D.signature()
            c = _FULL.get(day)
            if c is None or c[0] != sig:
                c = _FULL[day] = (sig, json.dumps(D.full(now, live), separators=(",", ":")).encode())
            return c[1]
        return D.delta(int(since), now, live)
