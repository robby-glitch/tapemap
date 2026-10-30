"""Read-only: one day's NIFTY session 09:15-15:25 per 5-min bar -- the extension's footprint (OHLC, buy/sell/delta),
fut OI at the bar's close (3-min session bars), the 3-min bands, the writers' lead (l5), the chart marks -- and the zone
machine's entries on 3-min bands (run_states at d2 / u2, as decode._zone_read calls it), dumped to JSON for the
live-chart mockup. Usage: python move_facts.py YYYY-MM-DD. Writes only move_facts_<day>.json beside this file."""
import json
import os
import sys

TAPE = r"C:\Users\kaam\Desktop\operator mode\tapemap"
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(TAPE)
sys.path.insert(0, TAPE)
import band_rotation  # noqa: E402
import confluence  # noqa: E402
import confluence_log  # noqa: E402
import contract_bars  # noqa: E402
import decode  # noqa: E402
import server  # noqa: E402

DAY, IDX = sys.argv[1], "NIFTY"
band_rotation.ZONE3_FROM = DAY
cap = {}
_dec = decode.decode
def spy(g, peers, fade_in=None, ride_in=None):
    if g.get("idx") == IDX:
        cap["g"] = g
    return _dec(g, peers, fade_in, ride_in)
decode.decode = spy
server._decode_all(DAY, 15 * 3600 + 30 * 60, False)
g = cap.get("g") or {}

def sec(t):
    return int(t // 1000 + 19800) % 86400

def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"

def mins(s):
    return int(s[:2]) * 60 + int(s[3:5])

tape = [json.loads(x) for x in open(f"data/tape/tape_{IDX}_{DAY}.jsonl", encoding="utf-8")]
sess = (confluence_log.session(IDX, DAY) or {}).get("bars") or []
z = contract_bars.with_bands(sess, contract_bars.bands_on(sess))
m3 = {mins(b["t"]): b for b in z}
marks = [json.loads(x) for x in open(f"data/tape/ofd_marks2_{IDX}_{DAY}.jsonl", encoding="utf-8")]

spot = []                                                      # (sec of day, spot) from the chain's own snapshots
for x in open(f"data/chain/chain_{IDX}_{DAY}.jsonl", encoding="utf-8"):
    r = json.loads(x)
    if r.get("spot") and r.get("sec"):
        spot.append((r["sec"], r["spot"]))
spot.sort()

out, seen = [], {}
for b in tape:
    m = sec(b["t"]) // 60
    if not (9 * 60 + 15 <= m <= 15 * 60 + 25):
        continue
    if hm(m) in seen:                                          # a re-written bar: keep the last copy
        out.pop(seen.pop(hm(m)))
        seen = {r["t"]: k for k, r in enumerate(out)}
    close = m + 5
    k3 = max((k for k in m3 if k + 3 <= close), default=None)    # the last 3-min bar closed by this 5-min close
    q = m3.get(k3) or {}
    out.append({"t": hm(m), "o": b.get("o") if b.get("o") is not None else q.get("o"), "h": b["h"], "l": b["l"],
                "c": b.get("c") if b.get("c") is not None else q.get("c"), "buy": b["buy"], "sell": b["sell"],
                "delta": b["delta"], "vol": b["vol"], "oi": q.get("oi"),
                "bands": {k: round(q[k], 1) for k in ("vwap", "u1", "u2", "u3", "d1", "d2", "d3") if q.get(k) is not None},
                "lead": (g.get("l5") or {}).get(close),
                "spot": next((v for s, v in reversed(spot) if s <= close * 60), None)})
    seen[hm(m)] = len(out) - 1

# the zone machine's entries, both sides: the touch (first arm), the entry bar's close = E, the machine's stop
zones = []
for side, band in (("BUY", "d2"), ("SELL", "u2")):
    st = band_rotation.run_states(z, stop_pts=band_rotation.OPERATOR_STOP_PTS, side=side, band=band, span=confluence.INTERVAL)
    for s in st:
        e = s["entry"]
        if not e:
            continue
        a = st[e["ref_i"]]["arm"]
        first = st[a["first_i"]] if a else st[e["ref_i"]]
        zones.append({"side": side, "band": band, "touch_t": first["t"], "touch_p": first.get("level"),
                      "entry_t": e["t"], "E": confluence.flat(z[e["i"]]).get("c"), "stop": e["stop"]})
zones.sort(key=lambda x: x["entry_t"])

mk = [{k: r.get(k) for k in ("t", "kind", "name", "p", "lots", "winner", "rank", "status", "trapped")}
      for r in marks if 9 * 3600 + 15 * 60 <= sec(r["t"]) <= 15 * 3600 + 25 * 60]
for r in mk:
    r["t"] = hm(sec(r["t"]) // 60)
p = os.path.join(HERE, f"move_facts_{DAY}.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump({"day": DAY, "idx": IDX, "bars": out, "marks": mk, "basis": g.get("basis"), "zones": zones}, f,
              ensure_ascii=False, default=str)
print("wrote", p, len(out), "bars", len(mk), "marks", len(zones), "zone entries; basis", g.get("basis"))
