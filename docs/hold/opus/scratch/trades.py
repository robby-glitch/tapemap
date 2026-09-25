"""Her fills -> flat-to-flat round trips (FIFO P&L), plus the examples chosen
before any replay (REPORT.md says how each was chosen). Read-only -> trades.json."""
import csv
import json
import os
import re
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
ORDERS = r"C:\Users\kaam\Downloads\orders.csv"
BOOK = r"C:\Users\kaam\Downloads\tradebook-ZVP031-FO (2).csv"
SYM = re.compile(r"^(NIFTY|SENSEX|BANKNIFTY)\d{2}[0-9A-Z]{3}(\d+)(CE|PE)$")


def mm(t):
    return int(t[:2]) * 60 + int(t[3:5])


def hm(n):
    return f"{n // 60:02d}:{n % 60:02d}"


def fills():
    out = []
    with open(ORDERS, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Status"] != "COMPLETE":
                continue
            out.append((r["Time"][:10], r["Time"][11:19], r["Instrument"], r["Type"].lower(),
                        int(r["Qty."].split("/")[0]), float(r["Avg. price"]), "orders.csv"))
    with open(BOOK, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            day = r["trade_date"]
            if day == "2026-09-24":          # 09-24 comes from orders.csv (the brief's source)
                continue
            out.append((day, r["order_execution_time"][11:19], r["symbol"], r["trade_type"],
                        int(float(r["quantity"])), float(r["price"]), "tradebook"))
    return sorted(out)


def round_trips():
    trips, open_ = [], {}
    for day, t, sym, bs, q, px, src in fills():
        m = SYM.match(sym)
        idx, k, side = m.group(1), int(m.group(2)), m.group(3)
        key = (day, sym)
        st = open_.get(key)
        if st is None:
            st = open_[key] = {"day": day, "idx": idx, "k": k, "side": side, "sym": sym, "src": src,
                               "buys": [], "sells": [], "lots": deque(), "pos": 0, "maxpos": 0, "pnl": 0.0}
        if bs == "buy":
            st["buys"].append((t, q, px))
            st["lots"].append([q, px])
            st["pos"] += q
            st["maxpos"] = max(st["maxpos"], st["pos"])
        else:
            st["sells"].append((t, q, px))
            left = q
            while left:
                lot = st["lots"][0]
                take = min(left, lot[0])
                st["pnl"] += take * (px - lot[1])
                lot[0] -= take
                left -= take
                if not lot[0]:
                    st["lots"].popleft()
            st["pos"] -= q
        if st["pos"] == 0:
            b, s = st["buys"], st["sells"]
            p0 = sum(q * p for _, q, p in b) / sum(q for _, q, _ in b)
            t0, tx = b[0][0], s[-1][0]
            trips.append({"id": f"{day[5:]} {t0[:5]} {idx} {k}{side}", "day": day, "idx": idx, "k": k, "side": side,
                          "role": "long", "sym": sym, "src": st["src"], "mine": True,
                          "t0": t0, "p0": round(p0, 2), "qty": st["maxpos"], "tx": tx,
                          "px": round(sum(q * p for _, q, p in s) / sum(q for _, q, _ in s), 2),
                          "pnl": round(st["pnl"], 2), "buys": b, "sells": s,
                          # the window reads the minute FINISHED before each fill
                          "read_from": hm(mm(t0) - 1), "exit_read": hm(mm(tx) - 1),
                          "exits": sorted({hm(mm(x[0]) - 1) for x in s}),
                          "read_to": hm(min(mm("15:29"), mm(tx) - 1 + 30))})
            del open_[key]
    return trips


# Chosen BEFORE any replay, by a rule that does not look at outcomes (REPORT.md §1):
# the zone machine's first 09-23 BUY entries as logged forward (one gate-legal, one
# not), its 09-23 NIFTY u2 SELL entry read as a call writer, and two fixed-time
# 09-24 SENSEX writers (one with the day's direction, one against it). A zone entry is
# read at its 3-min bar's last minute (fronts.bar_last_minute); a fixed time at the minute before.
EXAMPLES = [
    {"id": "EX 09-23 09:57 SENSEX zone BUY (gate legal) · long ATM CE", "day": "2026-09-23", "idx": "SENSEX",
     "side": "CE", "role": "long", "at": "09:57", "read": "09:59", "lots": 1},
    {"id": "EX 09-23 09:57 NIFTY zone BUY (gate illegal) · long ATM CE", "day": "2026-09-23", "idx": "NIFTY",
     "side": "CE", "role": "long", "at": "09:57", "read": "09:59", "lots": 1},
    {"id": "EX 09-23 11:15 NIFTY zone u2 SELL · WRITER short ATM CE", "day": "2026-09-23", "idx": "NIFTY",
     "side": "CE", "role": "short", "at": "11:15", "read": "11:17", "lots": 1},
    {"id": "EX 09-24 10:30 SENSEX · WRITER short ATM CE", "day": "2026-09-24", "idx": "SENSEX",
     "side": "CE", "role": "short", "at": "10:30", "read": "10:29", "lots": 1},
    {"id": "EX 09-24 09:45 SENSEX · WRITER short ATM PE", "day": "2026-09-24", "idx": "SENSEX",
     "side": "PE", "role": "short", "at": "09:45", "read": "09:44", "lots": 1},
]

if __name__ == "__main__":
    tr = round_trips()
    json.dump({"mine": tr, "examples": EXAMPLES}, open(os.path.join(HERE, "trades.json"), "w"), indent=1)
    for x in tr:
        print(f"{x['id']:<32} {x['t0']}->{x['tx']} x{x['qty']:<3} in {x['p0']:>7} out {x['px']:>7} pnl {x['pnl']:>+9.2f}  exits {x['exits']}")
    print(len(tr), "round trips; 09-24:", sum(1 for x in tr if x["day"] == "2026-09-24"),
          "net 09-24", round(sum(x["pnl"] for x in tr if x["day"] == "2026-09-24"), 2))
