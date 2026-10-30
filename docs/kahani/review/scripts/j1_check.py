"""READ-ONLY J1 check: handshake-2 + the hole rule on every recorded NIFTY book day -> per day the holes, the pushes, the
answered ones, the wapas ones, and every 28 Oct row. Prints only."""
import os, sys
ROOT = r"C:\Users\kaam\Desktop\operator mode\tapemap"
sys.path.insert(0, ROOT); os.chdir(ROOT)
import handshake as H
DAYS = ["2026-10-01", "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12", "2026-10-13",
        "2026-10-16", "2026-10-19", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28"]
for day in DAYS:
    inp = H.load(day, "NIFTY")
    if not inp["ms"]:
        continue
    rows = H.read(inp, H.LAST_M + 2)
    print(day, "holes", [(H.hm(H.mod(a)), round((b - a) / 1000)) for a, b in inp["holes"]], "| pushes", len(rows),
          "| answered", sum(r["ans"] in ("TOOT", "PHANS", "TIKI") for r in rows), "| wapas", sum(r["wapas"] for r in rows))
    if day == "2026-10-28":
        for r in rows:
            print("   ", r["t"], H.ARROW[r["dir"]], r["lots"], r["ans"], r["chg"], "am", r["am"], "held", r["held"],
                  "wapas", r["wapas"])
