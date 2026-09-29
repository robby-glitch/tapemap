"""fold_log.py -- the rev 6 event log (docs/pro-tool/6-amendment.md §5), in shadow.

  data/fold/fold_<IDX>_<day>.jsonl   one row per engine event and one per bucket close per marked trade,
                                     never one per batch; an `outcome` row 20 minutes after each falsifiable
                                     read; a `diverged` row where a restart's recompute disagrees with a row
                                     already on disk.

Every row carries rev "6", `shadow` (true until the face is in force), `thresholds_sha` (fold.THRESHOLDS)
and `code_sha` (fold.py's bytes). A row is written ONCE, keyed (trade_id, seq, event) -- the hold_log
discipline: a restart reads what is on disk and appends only what is missing.

RESUME (§10): the server recomputes the day causally with fold.start() over the recorded rows, then calls
resume(): rows already logged are never re-emitted (their keys are on disk), a recomputed event that reads
differently writes a `diverged` row, and words(view, res) puts the logged words back on the screen -- the
logged words win. DIR is read at call time, so tests point it at tmp_path.
"""
import hashlib
import json
import os
import threading

import fold

DIR = os.path.join("data", "fold")
SHADOW = True                       # 6-amendment §2: rev 6 rows before the in-force date are their own population
FALSIFIABLE = ("fold", "past_give_up", "clause")
_lock = threading.Lock()
_seen = {}                          # {(idx, day): {key}} -- that file, read once
_code_sha = None


def path(idx, day):
    return os.path.join(DIR, f"fold_{idx}_{day}.jsonl")


def thresholds_sha():
    return hashlib.sha256(json.dumps(fold.THRESHOLDS, sort_keys=True).encode()).hexdigest()[:16]


def code_sha():
    global _code_sha
    if _code_sha is None:
        with open(fold.__file__, "rb") as f:
            _code_sha = hashlib.sha256(f.read()).hexdigest()[:16]
    return _code_sha


def key(r):
    return r.get("trade_id"), r.get("seq"), r.get("event")


def seen(idx, day):
    """The keys already on disk for (idx, day). Call under _lock."""
    s = _seen.get((idx, day))
    if s is None:
        s = set()
        for r in read(idx, day):
            s.add(key(r))
        for k in [k for k in _seen if k[1] != day]:
            del _seen[k]
        _seen[(idx, day)] = s
    return s


def read(idx, day):
    out = []
    try:
        with open(path(idx, day), encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def append(idx, day, rows):
    """Write each row whose key is not on disk yet. Returns how many were written."""
    with _lock:
        s = seen(idx, day)
        new = [r for r in rows if key(r) not in s]
        if not new:
            return 0
        os.makedirs(DIR, exist_ok=True)
        with open(path(idx, day), "a", encoding="utf-8") as f:
            for r in new:
                f.write(json.dumps(r, default=str) + "\n")
                s.add(key(r))
        return len(new)


def row(state, e, src="marked", exit_t=None):
    """One engine event -> one §5 row (the event and the state it left)."""
    s, tr = e["row"], state.trade
    role = "long" if state.own > 0 else "short"
    return dict(rev=fold.REV, shadow=SHADOW, day=state.day, ts=e["ts"], t=e["t"], idx=state.idx,
                ik=tr.get("ik"), expiry=tr.get("expiry"), trade_id=state.trade_id, src=src,
                after_exit=bool(exit_t is not None and e["t"] > exit_t),
                side=str(tr.get("ty")).upper(), role=role, d=state.d, strike=state.k, qty=tr.get("qty"),
                entry_t=fold.hms(state.entry_t), E=state.entry_px, p0=state.p0,
                units=s["units"], mode=s["mode"], expiry_pm=s["expiry_pm"], G=s["G"], W=s["W"], A=s["A"],
                event=e["kind"], seq=e["seq"], epoch=e["epoch"], text=e["text"],
                headline=s["headline"], clause=s["clause"], line2=s["line2"], chips=s["chips"], sentences=s["sentences"],
                prem=s["prem"], alt=s["alt"], acc=s["acc"], oi_event=s["oi_event"], tally=s["tally"],
                sound_id=e.get("sound_id"), thresholds_sha=thresholds_sha(), code_sha=code_sha(), tag=s["tag"])


def _outcome_row(state, e, o, src):
    return dict(rev=fold.REV, shadow=SHADOW, day=state.day, ts=fold.hms(state.last_key), t=state.last_key, idx=state.idx,
                trade_id=state.trade_id, src=src, event="outcome", seq=e["seq"], ref_id=f"{state.trade_id}:{e['seq']}",
                ref_event=e["kind"], ref_ts=e["ts"], read=o["read"], verdict=o["verdict"], why=o["why"],
                thresholds_sha=thresholds_sha(), code_sha=code_sha())


def write(state, src="marked", exit_t=None):
    """Append the rows for every engine event not on disk yet, and the outcome rows now due. Call after each
    fold.step(); rows are per event, never per call, so a call with nothing new writes nothing."""
    with _lock:
        s = seen(state.idx, state.day)
    rows = [row(state, e, src, exit_t) for e in state.events if (state.trade_id, e["seq"], e["kind"]) not in s]
    for e in state.events:
        if e["kind"] not in FALSIFIABLE or (state.trade_id, e["seq"], "outcome") in s:
            continue
        o = fold.outcome(state, e)
        if o is not None:
            rows.append(_outcome_row(state, e, o, src))
    return append(state.idx, state.day, rows)


def resume(state, src="marked"):
    """After a restart's causal recompute: compare its events with the rows on disk; a difference writes a
    `diverged` row (once, keyed on the event's seq). Returns {diverged, last_seq, words} -- `words` are the
    last logged headline / clause / line2, which win on screen (words())."""
    logged = {r["seq"]: r for r in read(state.idx, state.day)
              if r.get("trade_id") == state.trade_id and r.get("event") not in ("outcome", "diverged")}
    div = []
    for e in state.events:
        r = logged.get(e["seq"])
        if r is None:
            continue
        mine = (e["kind"], e["ts"], e["text"], e["row"]["headline"], e["row"]["line2"])
        theirs = (r["event"], r["ts"], r["text"], r["headline"], r["line2"])
        if mine != theirs:
            d = row(state, e, src)
            d.update(event="diverged", ref_seq=e["seq"], recomputed=dict(zip(("event", "ts", "text", "headline", "line2"), mine)),
                     logged=dict(zip(("event", "ts", "text", "headline", "line2"), theirs)))
            div.append(d)
    append(state.idx, state.day, div)
    last = max(logged.values(), key=lambda r: r["seq"]) if logged else None
    return dict(diverged=len(div), last_seq=last["seq"] if last else 0,
                words=dict(headline=last["headline"], clause=last["clause"], line2=last["line2"]) if last else None)


def words(view, res):
    """The screen after a resume: while the recompute has produced no event past the last logged one, the
    logged words are shown, never the recomputed ones."""
    if not res or not res.get("words") or not view or view.get("headline") is None:
        return view
    ev = view.get("events") or []
    if ev and ev[-1]["seq"] > res["last_seq"]:
        return view
    out = dict(view)
    out.update(res["words"], resumed=True)
    return out
