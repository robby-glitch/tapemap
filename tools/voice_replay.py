"""tools/voice_replay.py -- THE ONE VOICE (voice.py, NOTEPAD A52) replayed over a real trade path, minute by minute,
through the live code: fold.State fed in 1-minute batches (fold_replay.resume_check's loop), fold_live's reply facts,
hold2.live on the rows so far, voice.ladder, and holdshadow for the receipt at her exit. Read-only on data/; writes only
<out.json>.   python -I -X utf8 tools/voice_replay.py <out.json>   (prints each trade's state changes and receipt)"""
import json
import os
import sys

OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath("voice_replay.json")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import book_log, confluence_log, fold, fold_live, hold2, holdshadow, tape_log, ux_log, voice  # noqa: E401,E402
import fold_replay as FR  # noqa: E402

TRADES = [
    # her 21 Oct mark, verbatim from data/day_state/day_2026-10-21.json
    dict(name="21oct", day="2026-10-21", lot=65, tr={"id": "NIFTY-23000PE-long-100730", "idx": "NIFTY", "k": 23000.0, "side": "PE",
         "role": "long", "t0": "10:07:30", "p0": 174.85, "exit_t": "13:05:04", "thesis": {"inval": 23052}}, end="13:20:00"),
    # 22 Oct: NOT marked (hold_trades = [], NOTEPAD A22); rebuilt from docs/live/DAY-2026-10-22.md §4f: 13:00 in, 13:25 out
    dict(name="22oct", day="2026-10-22", lot=20, tr={"id": "SENSEX-73400CE-long-130000", "idx": "SENSEX", "k": 73400.0, "side": "CE",
         "role": "long", "t0": "13:00:00", "p0": None, "exit_t": "13:25:00"}, end="13:40:00"),
]


def rows(p):
    return FR.rows(p) if p else []


def run(c):
    day, tr, idx = c["day"], dict(c["tr"]), c["tr"]["idx"]
    book = list(book_log.read_rows(day, idx))
    chain = rows(FR._p(os.path.join(ROOT, "data", "chain", f"chain_{idx}_{day}.jsonl")))
    tape = [b for b in tape_log.read_bars(day, idx) if b.get("t") is not None]
    vpin = [r for r in rows(os.path.join(ROOT, "data", "vpin_fast.jsonl")) if r.get("day") == day]
    if tr["p0"] is None:                       # her fill unknown: the chain's LTP at the first snapshot at/after 13:00
        te = fold.ms(day, tr["t0"])
        snap = next(x for x in chain if fold.ms(day, x["ts"]) >= te)
        tr["p0"] = next(x for x in snap["strikes"] if x["k"] == tr["k"])[tr["side"].lower()]["ltp"]
    days, _ = tape_log.prior_pool(day, idx, fold.PRIOR_N, after="2026-09-29")
    prior = [fold.session_from_book(list(book_log.read_rows(d, idx)), lot=c["lot"], idx=idx, day=d) for d in reversed(days)]
    inp = dict(day=day, idx=idx, lot=c["lot"], prior=prior, expiry=chain[-1].get("expiry") if chain else None)
    live = dict(tr, exit_t=None)               # the voice speaks while she is IN: read the trade as open to its exit
    st = fold.State(fold_live.fold_trade(live), inp)
    st.feed(vpin=vpin, tape=tape)
    keys = sorted([(r["t"], 1, r) for r in book] + [(fold.ms(day, r["ts"]), 0, r) for r in chain], key=lambda x: (x[0], x[1]))
    refs, rwhy = confluence_log.push_refs(idx, day)
    ux = ux_log.read_bars(day, idx)
    bars5_all = confluence_log.push_bars(idx, day, gc_rows=tape, ux_rows=ux)
    t0, t_end = fold.ms(day, tr["t0"]), fold.ms(day, c["end"])
    t_exit = fold.ms(day, tr["exit_t"])
    mem, cache, out, i, seen_chain = {}, {}, [], 0, []
    t = keys[0][0]
    shadow_cache, dec = {}, holdshadow.dec_rows(confluence_log._rows(os.path.join(ROOT, "data", "decode", f"decode_{day}.jsonl")), idx)
    while t <= t_end and i < len(keys):
        b, ch = [], []
        while i < len(keys) and keys[i][0] < t + 60000:
            (b if keys[i][1] else ch).append(keys[i][2])
            i += 1
        seen_chain += ch
        now = t + 60000
        fold.step(st, dict(book=b, chain=ch), now=now)
        t = now
        if now < t0 + 60000:
            continue
        v = fold_live._trim(st.view(now))
        if v.get("headline") is None:
            continue
        fold_live._voice_facts(st, v)
        rep = dict(ok=True, id=tr["id"], trade=fold_live.api_trade(tr), view=v, words=fold_live._words(st, {}))
        m = ((now // 1000 + 19800) % 86400) // 60
        b5 = [x for x in bars5_all if x["e"] // 60 <= m]
        h2 = hold2.live(live, v, m, st.bars, seen_chain, b5, refs, rwhy, cache)
        vc = voice.ladder(rep, h2, now, mem, lambda px: st._prem_at(px, st.last_key))
        sh = None
        if h2.get("ok"):
            sh = holdshadow.live(live, v, h2, m, st.bars, seen_chain, b5, dec, shadow_cache)
        out.append(dict(t=fold.hm(now), voice=vc, headline=v.get("headline"), clause=v.get("clause"), chips=v.get("chips"),
                        W=v.get("W"), hold2_text=h2.get("text"), shadow=sh, view=v, words=rep["words"]))
        if now >= t_exit and "receipt" not in c:
            rows_ = [holdshadow.row(day, tr, L, 0) for L in sh or ()]
            c["receipt"] = voice.receipt(tr, (v.get("prem") or {}).get("now"), rows_)
    return out


if __name__ == "__main__":
    res = {}
    for c in TRADES:
        path = run(c)
        seq, last = [], None
        for p in path:
            vc = p["voice"]
            if not vc.get("ok"):
                continue
            if vc["state"] != last:
                aft = " [after her exit]" if p["t"] > c["tr"]["exit_t"][:5] else ""
                seq.append(f"{p['t']} {vc['state']}" + (f" ({vc['reason']})" if vc.get("reason") else "") + aft)
                last = vc["state"]
        print(c["name"], c["tr"]["id"], "p0", c["tr"]["p0"])
        print("  " + "\n  → ".join(seq))
        print("  receipt:", (c.get("receipt") or {}).get("text"))
        res[c["name"]] = dict(trade=c["tr"], receipt=c.get("receipt"), seq=seq,
                              path=[{k: p[k] for k in ("t", "voice", "headline", "clause", "chips", "W", "hold2_text")} for p in path],
                              frames={p["t"]: {"view": p["view"], "words": p["words"]} for p in path})
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, default=str)
