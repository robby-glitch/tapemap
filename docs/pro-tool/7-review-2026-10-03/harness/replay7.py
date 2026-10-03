"""replay7.py -- 7-review harness. READ-ONLY on tapemap code and data/: imports fold.py and steps fold.State
exactly as fold_live.Engine._build feeds it (vpin + tape first, then book/chain rows in key order), but in
1-minute chunks so a snapshot can be taken at every minute boundary. Writes only to the folder given by OUT.

    python replay7.py            # every replay -> OUT/replays.json, OUT/minutes.csv
"""
import bisect
import csv
import datetime
import json
import os
import sys

ROOT = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, ROOT)
import book_log  # noqa: E402
import fold  # noqa: E402
import fold_live  # noqa: E402
import tape_log  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
IDX, LOT = "NIFTY", 65
D = os.path.join(ROOT, "data")
DAYS = ["2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01"]
EXPIRY = {"2026-09-22": "2026-09-22"}          # tools/fold_replay.py's convention; 29 Sep comes from the chain's own field
END = "15:00:00"
CAP_X = 0.25                                    # (h) candidate (iii): G no further than where the premium is -25 %
_cache = {}


def load(day):
    if day in _cache:
        return _cache[day]
    book = list(book_log.read_rows(day, IDX))
    chain = fold_live._jsonl(os.path.join(D, "chain", f"chain_{IDX}_{day}.jsonl"), lambda r: r.get("ts") and r.get("strikes"))
    vpin = fold_live._jsonl(os.path.join(D, "vpin_fast.jsonl"), lambda r: r.get("day") == day)
    tape = [b for b in tape_log.read_bars(day, IDX) if b.get("t") is not None]
    days, _ = tape_log.prior_pool(day, IDX, fold.PRIOR_N)            # what fold_live._engine pools
    prior = []
    for p in reversed(days):
        k = ("prior", p)
        if k not in _cache:
            _cache[k] = fold.session_from_book(list(book_log.read_rows(p, IDX)), lot=LOT, idx=IDX, day=p)
        prior.append(_cache[k])
    expiry = EXPIRY.get(day) or (chain[-1].get("expiry") if chain else None)
    keys = sorted([(r["t"], 1, r) for r in book] + [(fold.ms(day, r["ts"]), 0, r) for r in chain], key=lambda x: (x[0], x[1]))
    _cache[day] = dict(book=book, chain=chain, vpin=vpin, tape=tape, prior=prior, expiry=expiry, keys=keys,
                       prior_days=list(reversed(days)))
    return _cache[day]


def ltp(row, k, ty):
    x = next((x for x in row["strikes"] if x["k"] == k), None)
    return x[ty].get("ltp") if x else None


def prem_path(day, k, ty, t0, t1):
    out = []
    for c in load(day)["chain"]:
        t = fold.ms(day, c["ts"])
        if t0 <= t <= t1:
            p = ltp(c, k, ty.lower())
            if p:
                out.append((t, p))
    return out


def prem_at(path, t):
    i = bisect.bisect_right([x[0] for x in path], t) - 1
    return path[i][1] if i >= 0 else None


def atm(day, t):
    """The strike nearest the options' own forward at the last chain row <= t: min |CE - PE|."""
    rows = [c for c in load(day)["chain"] if fold.ms(day, c["ts"]) <= t]
    c = rows[-1]
    xs = [(abs(x["ce"]["ltp"] - x["pe"]["ltp"]), x["k"]) for x in c["strikes"] if x["ce"].get("ltp") and x["pe"].get("ltp")]
    return min(xs)[1], c


# ---- premium at a futures-chart level, the corrected way: the strike now with the same moneyness the trade's
# strike would have with the future at px is K' = K + (fut - px) = K + F* + basis - px. fold._prem_at uses
# K + F* - px, which mixes F* (options' forward) with a futures-chart px: off by the basis.
def _interp(st, kp):
    xs = sorted(((x["k"], x[st.ty]["ltp"]) for x in st.rc["strikes"] if x[st.ty].get("ltp")), key=lambda z: z[0])
    i = bisect.bisect_left([z[0] for z in xs], kp)
    if i == 0 or i >= len(xs):
        return None
    (k0, p0), (k1, p1) = xs[i - 1], xs[i]
    return round(p0 + (p1 - p0) * (kp - k0) / (k1 - k0), 1)


def prem_at_true(st, px, t):
    if st.rc is None or st.F is None or px is None or t - st.rc_t > fold.PREM_STALE_MS:
        return None
    return _interp(st, st.k + st.F + st.bas - px)


def level_for_prem(st, target):
    """The futures-chart level where the trade's own strike would price at `target` (inverse of prem_at_true)."""
    xs = sorted(((x["k"], x[st.ty]["ltp"]) for x in st.rc["strikes"] if x[st.ty].get("ltp")), key=lambda z: z[0])
    for (k0, p0), (k1, p1) in zip(xs, xs[1:]):
        if min(p0, p1) <= target <= max(p0, p1) and p0 != p1:
            kp = k0 + (target - p0) * (k1 - k0) / (p1 - p0)
            return st.k + st.F + st.bas - kp
    return None


# ---- variants of the engine (scratch only; fold.py is not touched)
class CapG(fold.State):
    """(iii): at the mark, G no further than the future level where the premium would be -CAP_X (+CAP_X short)."""
    capL = None

    def _cap(self, t):
        if not self.seeded or self.G is None or self.rc is None or self.F is None:
            return
        if self.capL is None:
            self.capL = level_for_prem(self, self.p0 * (1 - self.own * CAP_X)) or False
        if self.capL and self.d * (self.capL - self.G) > 0:
            self.G, self.G_t = round(self.capL), t
            self.G_src = f"premium cap -{int(CAP_X * 100)} % at the mark"
            self._pick_W(t)

    def _seed(self, t):
        super()._seed(t)
        self._cap(t)

    def _on_chain(self, t):
        super()._on_chain(t)
        self._cap(t)

    def _on_run(self, r, t):
        super()._on_run(r, t)
        self._cap(t)


class NoStepUnderWater(fold.State):
    """(v): at entry and under water on the future, a win by her side does not move G (no new epoch)."""

    def _on_run(self, r, t):
        if (r["winner"] == self.d and self.G is not None and not self._trailed() and self.entry_px is not None
                and self.last_p is not None and self.d * (self.last_p - self.entry_px) < 0):
            self.newest_win, self.latest, self.failed = r, "WIN", None
            return
        super()._on_run(r, t)


def run(name, day, k, ty, side, p0, entry, exit_t=None, cls=fold.State, kind="", end=END, minutes=True):
    L = load(day)
    trade = dict(k=k, ty=ty, side=side, p0=p0, entry_t=entry, trade_id=name)
    st = cls(trade, dict(day=day, idx=IDX, lot=LOT, prior=L["prior"], expiry=L["expiry"]))
    st.feed(vpin=L["vpin"], tape=L["tape"])
    keys = L["keys"]
    T_end, t_e = fold.ms(day, end), st.entry_t
    snaps, i, tb = [], 0, (t_e // 60000 + 1) * 60000
    while tb <= T_end:
        j = bisect.bisect_left(keys, (tb, -1))          # every row with key < tb
        part = keys[i:j]
        st.feed(book=[r for _, kd, r in part if kd], chain=[r for _, kd, r in part if not kd])
        i = j
        if minutes and st.seeded:
            snaps.append(snap(st, tb))
        tb += 60000
    path = prem_path(day, k, ty, t_e, T_end)
    return dict(name=name, kind=kind, day=day, k=k, ty=ty, side=side, p0=p0, entry=entry, exit_t=exit_t, d=st.d,
                own=st.own, E=st.entry_px, snaps=snaps, events=[ev_slim(e, st) for e in st.events], path=path,
                units=dict(BK=st.BK, prior_n=st.prior_n, bk_src=st.bk_src), expiry_day=st.expiry_day,
                holes=[(fold.hms(a), fold.hms(b), w) for a, b, w in st.holes])


def snap(st, t):
    G = st.G
    w = st.B_at(t) / 2 if st.B_at(t) else None
    pn = st.prem_now()
    live_h, live_c = st._headline(t, live=True)
    frozen_h, _ = st._headline(t)
    pe = st._prem_at(G, t)[0] if G is not None else None
    return dict(t=fold.hms(t)[:5], fut=st.last_p, prem=pn, pct=None if pn is None else round(100 * st.own * (pn - st.p0) / st.p0, 1),
                Z=st.shown["ZONE"], F=st.shown["FLOW"], O=st.shown["OI"], V=st.shown["VPIN"],
                head=frozen_h, live=live_h, clause=live_c, G=G, mode=("trailed" if st._trailed() else "at entry") if G is not None else None,
                dG=None if G is None or st.last_p is None else round(st.d * (st.last_p - G), 1),
                atG_engine=pe, atG_true=prem_at_true(st, G, t), w=w,
                dE=None if st.entry_px is None else round(st.d * (st.last_p - st.entry_px), 1),
                W=st.W, Wst=st.Ww.state() if st.Ww else None, oi_ev=st.oi_ev is not None, acc=st.acc is not None,
                folds=len(st.folds), F_star=None if st.F is None else round(st.F, 1), bas=None if st.bas is None else round(st.bas, 1))


def ev_slim(e, st):
    r = e["row"]
    return dict(t=e["t"], ts=e["ts"], kind=e["kind"], text=e["text"], why=e.get("why"),
                fut=r["fut"], prem=r["prem"]["now"], pct=r["prem"]["pct"], atG=r["prem"]["at_G"],
                chips=r["chips"], head=r["headline"], clause=r["clause"], G=r["G"]["px"], mode=r["mode"],
                oi_ev=r["oi_event"] is not None, w=r["units"]["w"], E=r["E"])


# ---- the replays
MARKED = []
for p in sorted(os.listdir(os.path.join(D, "day_state"))):
    js = json.load(open(os.path.join(D, "day_state", p), encoding="utf-8"))
    for tr in js.get("hold_trades") or []:
        if tr["idx"] == IDX:
            MARKED.append((tr["id"], p[4:14], int(float(tr["k"])), tr["side"], "BUY" if tr["role"] == "long" else "SELL",
                           tr["p0"], tr["t0"], tr.get("exit_t")))

sys.path.insert(0, os.path.join(ROOT, "tools"))
import fold_replay  # noqa: E402  (only its DESIGN table; nothing is run at import)

DESIGN = [(n, d, k, ty, s, p0, e, None) for n, d, k, ty, s, p0, e, _x in fold_replay.DESIGN]


def zone_triggers():
    rows = [json.loads(x) for x in open(os.path.join(D, "trigger_log.jsonl"), encoding="utf-8") if x.strip()]
    out, seen = [], set()
    for r in rows:
        if r.get("index") != IDX or r.get("day") not in DAYS or r.get("kind") == "arm" or r.get("rule") != "zone":
            continue
        out.append(r)
    return out


def zone_trades(only=None):
    """IF YOU WERE IN at each zone trigger: marked at the trigger bar's close (t + 3 min), ATM by min |CE - PE|,
    long CE on BUY (d2->d3) and long PE on SELL (u2->u3), p0 = the chain LTP of the last row at or before the mark.
    A row whose index price is nowhere near that day's future (a mis-dated duplicate) is reported and skipped."""
    out, skipped = [], []
    for r in zone_triggers():
        day = r["day"]
        if only and day not in only:
            continue
        h, m = map(int, r["t"].split(":"))
        mm = h * 60 + m + 3
        entry = f"{mm // 60:02d}:{mm % 60:02d}:00"
        if entry >= END:
            skipped.append((day, r["t"], r["side"], "after 15:00 (her practice)"))
            continue
        te = fold.ms(day, entry)
        at = datetime.datetime.fromtimestamp(r["at"], fold.IST)
        if at.strftime("%Y-%m-%d") != day or at.strftime("%H:%M") < "09:15":
            skipped.append((day, r["t"], r["side"], f"written {at:%m-%d %H:%M:%S}, outside that session: a mis-dated copy"))
            continue
        k, c = atm(day, te)
        ty = "CE" if r["side"] == "BUY" else "PE"
        oty = "PE" if ty == "CE" else "CE"
        p0 = ltp(c, k, ty.lower())
        mp0 = ltp(c, k, oty.lower())
        out.append((f"Z {day[5:]} {r['t']} {r['side']}", day, k, ty, "BUY", p0, entry, None, dict(mirror=(oty, mp0), trig=r)))
    return out, skipped


if __name__ == "__main__":
    import time
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else set(DAYS)
    tag = sys.argv[3] if len(sys.argv) > 3 else "all"
    zt, zskip = zone_trades(only)
    jobs = [(n, d, k, ty, s, p0, e, x, "marked", {}) for n, d, k, ty, s, p0, e, x in MARKED] + \
           [(n, d, k, ty, s, p0, e, x, "design", {}) for n, d, k, ty, s, p0, e, x in DESIGN] + \
           [(n, d, k, ty, s, p0, e, x, "zone", meta) for n, d, k, ty, s, p0, e, x, meta in zt]
    res = []
    for n, d, k, ty, s, p0, e, x, kind, meta in jobs:
        if d not in only:
            continue
        t0 = time.time()
        r = run(n, d, k, ty, s, p0, e, exit_t=x, kind=kind)
        r["variants"] = {}
        for vn, cls in (("capG", CapG), ("nostep", NoStepUnderWater)):
            v = run(n, d, k, ty, s, p0, e, exit_t=x, cls=cls, kind=kind, minutes=False)
            r["variants"][vn] = dict(events=[ev for ev in v["events"] if ev["kind"] in ("fold", "seed", "reset", "accepted", "oi_event")])
        if meta.get("mirror"):
            oty, mp0 = meta["mirror"]
            r["mirror"] = dict(ty=oty, p0=mp0, path=prem_path(d, k, oty, fold.ms(d, e), fold.ms(d, END)))
            r["trig"] = {kk: meta["trig"].get(kk) for kk in ("t", "side", "band", "px", "level", "trigger")}
        res.append(r)
        print(f"{n:28} {d} {k}{ty} {s} p0 {p0} {e} -> {len(r['events'])} ev, {time.time() - t0:.1f}s", flush=True)
    json.dump(dict(res=res, zskip=zskip, prior={d: load(d)["prior_days"] for d in only}, expiry={d: load(d)["expiry"] for d in only}),
              open(os.path.join(OUT, f"replays_{tag}.json"), "w", encoding="utf-8"))
    with open(os.path.join(OUT, f"minutes_{tag}.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        cols = ["t", "fut", "prem", "pct", "Z", "F", "O", "V", "head", "live", "G", "mode", "dG", "atG_engine", "atG_true", "dE", "W", "Wst", "oi_ev", "acc"]
        wr.writerow(["trade", "day"] + cols)
        for r in res:
            for s in r["snaps"]:
                wr.writerow([r["name"], r["day"]] + [s.get(c) for c in cols])
    print("skipped zone rows:", zskip)
