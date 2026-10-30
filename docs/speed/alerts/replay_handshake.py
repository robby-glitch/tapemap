"""replay_handshake.py -- READ-ONLY causal replay of the A132 handshake stream (handshake.py) over recorded days.

Walks the day minute by minute exactly as server._hs_pass does (handshake.read(inp, upto), upto = each minute), prints
each FLOW stream line at the minute it would first have been written, then every push of the day as the forward log
would hold it (NAHI included: they never reach the stream). Rows, not rates. Writes nothing.

    python docs/speed/alerts/replay_handshake.py                       26 + 27 Oct, NIFTY
    python docs/speed/alerts/replay_handshake.py 2026-10-27 BANKNIFTY
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)                                 # the record paths are relative to tapemap/

import handshake  # noqa: E402


def replay(day, idx):
    inp = handshake.load(day, idx)
    said, lines = set(), []
    for upto in range(handshake.FIRST_M + 1, handshake.LAST_M + 3):
        for r in handshake.read(inp, upto):
            m = handshake.message(r)
            if m and m["key"] not in said:
                said.add(m["key"])
                lines.append((handshake.hm(upto), m["line"]))
    final = handshake.read(inp, handshake.LAST_M + 2)
    print(f"\n=== {day} {idx} · flow {inp['flow_of']} · Dext minutes {sum(v == 'D' for v in inp['src'].values())}, "
          f"book {sum(v == 'B' for v in inp['src'].values())} · {len(final)} pushes, {len(lines)} on the stream")
    print("-- the stream (written at  ·  the line)")
    for at, ln in lines:
        print(f"{at}  {ln}")
    print("-- every push (the forward log): t dir lots src · k side OI · answer @minute (+min) chg/bar · behind · fut · effort · +15/+30")
    for r in final:
        b = r["behind"]
        back = "—" if b is None else "{k} {side} {add:+} {who}".format(**b)
        print(f"{r['t']} {handshake.ARROW[r['dir']]} {r['lots']:+5} {r['src']:>2} · {r['side']} {r['k']} {r['oi_L']}L · "
              f"{r['ans']} @{r['am']} (+{r['after']}) {r['chg']}/{r['bar']} · {back} · "
              f"{(r['fut'] or {}).get('leg')} {(r['fut'] or {}).get('lots')} · {(r['effort'] or {}).get('x')}x · {r['p15']}/{r['p30']}")


if __name__ == "__main__":
    a = sys.argv[1:]
    for day, idx in ([(a[0], a[1] if len(a) > 1 else "NIFTY")] if a else [("2026-10-26", "NIFTY"), ("2026-10-27", "NIFTY")]):
        replay(day, idx)
