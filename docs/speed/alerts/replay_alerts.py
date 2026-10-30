"""replay_alerts.py -- READ-ONLY causal replay of the two A131 Telegram alerts over recorded days (NOTEPAD A131).

ALERT 1  the ZONE line with its day type: messages.build over DECODE rows recomputed by server._decode_all at every
         5-min close, band_rotation.ZONE3_FROM moved in-process only (A116's replay; the live date is untouched).
ALERT 2  TOP / BOTTOM BAN SAKTA: palat.judge on each footprint P, on the record files (palat.load) and DECODE's row at
         the P's close (recomputed the same way).
Points after: spot (the chain record) at c + 15 / c + 30 minus spot at c, in the alert's way (TOP / SELL = down).
Rows, not rates. Writes REPLAY.md beside this file and, with --cache, the recomputed DECODE rows there; never data/.

    python docs/speed/alerts/replay_alerts.py                      the default days, REPLAY.md
    python docs/speed/alerts/replay_alerts.py --decode 2026-10-27  only build that day's DECODE cache (--cache DIR)
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)                                 # the server's record paths are relative to tapemap/

import band_rotation  # noqa: E402
import messages       # noqa: E402
import palat          # noqa: E402

FULL = ["2026-10-01", "2026-10-19", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-26", "2026-10-27"]
PALAT_ONLY = ["2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30",
              "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12", "2026-10-16"]
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
CLOSES = [33300 + 300 * k for k in range(1, 76)]          # 09:20 .. 15:30


def decode_at(day, T):
    """DECODE's rows at the close T (sec of day), every index, as the log writes them (server._decode_log)."""
    import server
    band_rotation.ZONE3_FROM = "2000-01-01"   # in-process only: the ZONE chip on a past day (A116's replay)
    out = server._decode_all(day, T, False)
    t = palat.hm(T // 60)
    return [json.loads(json.dumps(dict(b, day=day, idx=i, T=t), ensure_ascii=False, default=str))
            for i, b in out.items() if isinstance(b, dict) and "call" in b]


def decode_rows(day, closes, cache):
    """The recomputed DECODE rows at `closes`, from --cache when it has them."""
    p = os.path.join(cache, f"decode_{day}.jsonl") if cache else None
    have = {}
    if p and os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            have.setdefault(r["T"], []).append(r)
    rows = []
    for T in closes:
        t = palat.hm(T // 60)
        if t not in have:
            have[t] = decode_at(day, T)
            if p:
                with open(p, "a", encoding="utf-8") as f:
                    f.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in have[t]))
        rows += have[t]
    return rows


def p_closes(loads):
    """The 5-min closes of the day's P marks (a day replayed for ALERT 2 only needs DECODE there)."""
    return sorted({palat.close(P) * 60 for inp in loads.values() for P in inp["marks"] if palat.close(P) * 60 <= CLOSES[-1]})


def spot(R, ms, m):
    j = palat._last(ms, m)
    return None if j is None else R[j]["spot"]


def after(R, ms, c, way):
    s0 = spot(R, ms, c - 1)
    out = []
    for w in (15, 30):
        s1 = spot(R, ms, c - 1 + w) if c - 1 + w <= 930 else None
        out.append(None if s0 is None or s1 is None or palat._last(ms, c - 1 + w) < c - 1 + w - 3 else round(way * (s1 - s0)))
    return out


def _p(x):
    return "?" if x is None else f"{x:+d}".replace("-", "−")


def day_rows(day, full, cache):
    """-> (palat rows, zone rows, counts) for one day."""
    pal, zon, cnt = [], [], {"P": 0, "extreme": 0, "alert": 0, "sent": 0, "zone": 0}
    loads, msgs = {}, []
    for idx in palat.IDXS:                    # BAN SAKTA: NIFTY only (the one index with P marks)
        inp = palat.load(day, idx)
        if inp["marks"]:
            loads[idx] = inp
    rows = decode_rows(day, CLOSES if full else p_closes(loads), cache)
    at = {(r["idx"], r["T"]): r for r in rows}
    for idx, inp in loads.items():
        for P in inp["marks"]:
            cnt["P"] += 1
            j = palat.judge(idx, P, inp, at.get((idx, palat.hm(palat.close(P)))))
            if j["swing"] is None:
                continue
            cnt["extreme"] += 1
            way = -1 if j["swing"] == "TOP" else 1
            row = {"day": day, "idx": idx, "P": palat.hm(palat.mod(P["t"])), "c": palat.hm(j["c"]), "p": P["p"],
                   "swing": j["swing"], "n": j["n"], "need": j.get("need"), "unk": j["unk"], "checks": j["checks"],
                   "din": ((at.get((idx, palat.hm(j["c"]))) or {}).get("onesided") or {}).get("type"),
                   "after": after(inp["R"], inp["ms"], j["c"], way), "line": None, "tg": False, "key": None}
            if j["msg"]:
                msgs.append(j["msg"])
                row["key"] = j["msg"]["key"]
            pal.append(row)
    for m in palat.budget(msgs):              # the day budget, as server._palat_pass applies it
        r = next(r for r in pal if r["key"] == m["key"])
        r["line"], r["tg"] = m["line"], not m.get("quiet")
        cnt["alert"] += 1
        cnt["sent"] += r["tg"]
    if full:
        R = {i: palat.load(day, i) for i in IDXS}
        for m in messages.build([], rows):
            if m["kind"] == "SETUP" and m["word"].startswith("ZONE ") and " + " not in m["word"]:
                cnt["zone"] += 1
                c = palat._hm2m(m["t"])
                zon.append({"day": day, "idx": m["idx"], "t": m["t"], "line": m["line"],
                            "after": after(R[m["idx"]]["R"], R[m["idx"]]["ms"], c, m["dir"])})
    return pal, zon, cnt


def render(days, res):
    L = ["# A131 replay: ZONE line + day type, and TOP / BOTTOM BAN SAKTA (3 of 4)", "",
         f"Built {time.strftime('%Y-%m-%d %H:%M')} by `docs/speed/alerts/replay_alerts.py` (read-only, causal). Rows, not rates.",
         "Points after = spot at the close + 15 / + 30 min minus spot at the close, in the alert's way (TOP / SELL = down).",
         "DECODE (day type, ZONE chip) is recomputed by `server._decode_all` at each close with `band_rotation.ZONE3_FROM` moved",
         "in-process only (live it starts 28 Oct). Band = faded.vwaps + hold2.sigmas on the GoCharting 5-min fut bars.", "",
         "BAN SAKTA (Fable's review, 28 Oct): writers at the extreme strike = WHO OPENED writers + the day's biggest 10-min add",
         "there; fut OI FLAT or COVER passes, FRESH fails; sigma only after 30 min; one per bar and side; NIFTY only; on a",
         "§1o TREND against the call it needs 4/4; the first 3 a day go to Telegram, the rest to the window.", "",
         "## Per day", "", "| day | P marks (one per bar + side) | P at the extreme | BAN SAKTA lines | to Telegram | ZONE alerts |",
         "|---|---|---|---|---|---|"]
    for d in days:
        c = res[d][2]
        L.append(f"| {d} | {c['P']} | {c['extreme']} | {c['alert']} | {c['sent']} | {c['zone'] if d in FULL else 'not replayed'} |")
    L += ["", "## ALERT 2 · every TOP / BOTTOM BAN SAKTA line (TG = sent to Telegram, window = past the day budget)", "",
          "| day | P | | line | +15 | +30 |", "|---|---|---|---|---|---|"]
    for d in days:
        for r in res[d][0]:
            if r["line"]:
                L.append(f"| {d} | {r['P']} | {'TG' if r['tg'] else 'window'} | `{r['line']}` | {_p(r['after'][0])} | "
                         f"{_p(r['after'][1])} |")
    L += ["", "## P at the extreme that did NOT reach its bar (3 of 4, or 4 of 4 on a trend against it): not sent", "",
          "| day | idx | P | swing | n / need | ? | zone | band | thakan | fut OI | din | +15 | +30 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    mk = {True: "✓ ", False: "✗ ", None: "? "}
    for d in days:
        for r in res[d][0]:
            if not r["line"]:
                ck = [mk[r["checks"][k][0]] + r["checks"][k][1] for k in palat.ORDER]
                L.append(f"| {d} | {r['idx']} | {r['P']} @ {r['p']:,.0f}f | {r['swing']} | {r['n']} / {r['need']} | {r['unk']} | "
                         + " | ".join(ck) + f" | {r['din'] or '?'} | {_p(r['after'][0])} | {_p(r['after'][1])} |")
    L += ["", "## ALERT 1 · every ZONE SETUP line, with its day type", "",
          "| day | line (as Telegram gets it) | +15 | +30 |", "|---|---|---|---|"]
    for d in days:
        for z in res[d][1]:
            L.append(f"| {d} | `{z['line']}` | {_p(z['after'][0])} | {_p(z['after'][1])} |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", default=",".join(FULL + PALAT_ONLY))
    ap.add_argument("--cache", default=None)
    ap.add_argument("--decode", default=None, help="only build this day's DECODE cache")
    a = ap.parse_args()
    if a.cache:
        os.makedirs(a.cache, exist_ok=True)
    if a.decode:
        loads = {i: palat.load(a.decode, i) for i in IDXS}
        decode_rows(a.decode, CLOSES if a.decode in FULL else p_closes({i: x for i, x in loads.items() if x["marks"]}), a.cache)
        return 0
    days = sorted(a.days.split(","))
    res = {}
    for d in days:
        t0 = time.time()
        res[d] = day_rows(d, d in FULL, a.cache)
        print(d, res[d][2], f"{time.time() - t0:.0f}s", flush=True)
    out = os.path.join(HERE, "REPLAY.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(days, res))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
