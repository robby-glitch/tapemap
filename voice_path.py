"""voice_path.py -- THE ONE VOICE (voice.py, A52) and its TRADE MAP (trademap.py, A53-A59) replayed over a marked trade,
minute by minute, through the live code (NOTEPAD A56): fold.State fed in 1-minute batches (fold_replay.resume_check's
loop), fold_live's reply facts, hold2.live on the rows so far, voice.ladder, trademap.read + into, and holdshadow for the
receipt at her exit. Used by tools/voice_replay.py and by GET /api/voice_path (server._voice_path). Read-only on data/.

The DECODE block's effort (the map's survivor read) comes from data/decode/decode_<day>.jsonl, what the app said. A day
recorded before that log began (23 Oct) has none: its effort is rebuilt at each 5-min close by the server's own recipe
(server._decode_effort: effort.read on the futures book and the chain spot), and `dec_src` says "rebuilt". The shadow
lines keep the log alone, as before. PDH / PDL come from the prior recorded session's chain spot up to 15:15 (CAS)."""
import os
from datetime import date, timedelta

import book_log
import confluence
import confluence_log
import decoder_log
import effort
import fold
import fold_live
import hold2
import holdshadow
import tape_log
import trademap
import ux_log
import v2feed
import voice

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")


def rows(path):
    return list(confluence_log._rows(path))


def roll(day):
    """The last monthly futures expiry before `day` (the last Tuesday of a month; holidays not removed [I]): prior days on
    or before it traded the previous contract (tape_log.prior_pool's `after`)."""
    d = date.fromisoformat(day)

    def last_tue(y, m):
        e = date(y + m // 12, m % 12 + 1, 1) - timedelta(1)
        return e - timedelta((e.weekday() - 1) % 7)
    t = last_tue(d.year, d.month)
    if t >= d:
        p = d.replace(day=1) - timedelta(1)
        t = last_tue(p.year, p.month)
    return t.isoformat()


def prior_levels(idx, day):
    """PDH / PDL from the prior recorded session's chain spot up to 15:15 (the CAS freeze) [M], else None."""
    ds = sorted({f[len(f"chain_{idx}_"):][:10] for f in os.listdir(os.path.join(DATA, "chain"))
                 if f.startswith(f"chain_{idx}_") and f[len(f"chain_{idx}_"):][:10] < day})
    for d in reversed(ds):
        sp = [r["spot"] for r in rows(os.path.join(DATA, "chain", f"chain_{idx}_{d}.jsonl"))
              if r.get("spot") is not None and str(r.get("ts") or "") <= "15:15:59"]
        if sp:
            return {"PDH": max(sp), "PDL": min(sp), "from": d}
    return None


def effort_dec(idx, book, chain, lot):
    """{close minute: {"effort": ...}} at every 5-min close, server._decode_effort's recipe on the record."""
    if idx not in effort.STEP:
        return {}
    fm = effort.minutes(book, lot)
    spot = {int(m[:2]) * 60 + int(m[3:5]): r["spot"] for m, r in confluence.chain_grid(chain)[0].items()}
    return {c: {"effort": effort.read(idx, fm, spot, c - 1), "T": hold2.hm(c)} for c in range(9 * 60 + 20, 15 * 60 + 31, 5)}


def run(c):
    """c = {day, tr (her day_state record), lot?, end "HH:MM:SS"} -> the path [{t "HH:MM", at "HH:MM:SS" (the read's own
    second: everything fed is before it), voice, headline, clause, chips, W, hold2_text, shadow, map, view, words}];
    c["receipt"] at her exit, c["dec_src"] "log" | "rebuilt"."""
    day, tr, idx = c["day"], dict(c["tr"]), c["tr"]["idx"]
    lot = c.get("lot") or v2feed.LOTS.get(idx)
    book = list(book_log.read_rows(day, idx))
    chain = rows(os.path.join(DATA, "chain", f"chain_{idx}_{day}.jsonl"))
    tape = [b for b in tape_log.read_bars(day, idx) if b.get("t") is not None]
    vpin = [r for r in rows(os.path.join(DATA, "vpin_fast.jsonl")) if r.get("day") == day]
    if tr.get("p0") is None:                   # her fill unknown: the chain's LTP at the first snapshot at/after entry
        te = fold.ms(day, tr["t0"])
        snap = next(x for x in chain if fold.ms(day, x["ts"]) >= te)
        tr["p0"] = next(x for x in snap["strikes"] if x["k"] == tr["k"])[tr["side"].lower()]["ltp"]
    days, _ = tape_log.prior_pool(day, idx, fold.PRIOR_N, after=c.get("after") or roll(day))
    prior = [fold.session_from_book(list(book_log.read_rows(d, idx)), lot=lot, idx=idx, day=d) for d in reversed(days)]
    inp = dict(day=day, idx=idx, lot=lot, prior=prior, expiry=chain[-1].get("expiry") if chain else None)
    live = dict(tr, exit_t=None)               # the voice speaks while she is IN: read the trade as open to its exit
    st = fold.State(fold_live.fold_trade(live), inp)
    st.feed(vpin=vpin, tape=tape)
    keys = sorted([(r["t"], 1, r) for r in book] + [(fold.ms(day, r["ts"]), 0, r) for r in chain], key=lambda x: (x[0], x[1]))
    refs, rwhy = confluence_log.push_refs(idx, day)
    ux = ux_log.read_bars(day, idx)
    bars5_all = confluence_log.push_bars(idx, day, gc_rows=tape, ux_rows=ux)
    t0, t_end = fold.ms(day, tr["t0"]), fold.ms(day, c["end"])
    t_exit = fold.ms(day, tr["exit_t"]) if tr.get("exit_t") else None
    mem, cache, out, i, seen_chain = {}, {}, [], 0, []
    t = keys[0][0]
    shadow_cache, dec = {}, holdshadow.dec_rows(rows(os.path.join(DATA, "decode", f"decode_{day}.jsonl")), idx)
    mdec, c["dec_src"] = (dec, "log") if dec else (effort_dec(idx, book, chain, lot), "rebuilt")
    lv = c["levels"] if "levels" in c else prior_levels(idx, day)
    prints = decoder_log.read_events(day, idx)                  # A61: her BADA PRINTs (logged from 5 Oct, GoCharting tab open)
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
        gc_t = max((x["t"] for x in tape if x["t"] + 300000 <= now), default=None)    # the GoCharting bars closed by now
        mp = trademap.read(live, v, seen_chain, b5, refs, mdec, lv, m, prints, gc_t)
        trademap.into(vc, mp)
        sh = None
        if h2.get("ok"):
            sh = holdshadow.live(live, v, h2, m, st.bars, seen_chain, b5, dec, shadow_cache)
        out.append(dict(t=fold.hm(now), at=fold.hms(now), voice=vc, headline=v.get("headline"), clause=v.get("clause"), chips=v.get("chips"),
                        W=v.get("W"), hold2_text=h2.get("text"), shadow=sh, map=mp, view=v, words=rep["words"]))
        if t_exit is not None and now >= t_exit and "receipt" not in c:
            rows_ = [holdshadow.row(day, tr, L, 0) for L in sh or ()]
            c["receipt"] = voice.receipt(tr, (v.get("prem") or {}).get("now"), rows_)
    return out
