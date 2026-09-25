"""Build war-compact-2026-09-24.html from the 2026-09-23 session. Read-only.

    python docs/mockups/gen_war_compact.py [PAYLOAD_DIR]

PAYLOAD_DIR holds oihist_<IDX>.json and warmap_<IDX>.json, saved by GET from
http://127.0.0.1:8765 at 00:47 IST 2026-09-24 (the server still held 2026-09-23).
Absolute OI per minute is not on any route yet, so it is read from
data/chain/chain_<IDX>_2026-09-23.jsonl, the poller's own 10-second log.

The fronts are NOT re-implemented: every front, state and `broke` below comes
from `fronts.read` / `fronts.cut` / `fronts.broke`, the server's one copy of
research-findings section 1d.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import fronts  # noqa: E402

DAY = "2026-09-23"
IDXS = ("NIFTY", "BANKNIFTY", "SENSEX")
FROZEN = "13:36"
LEVEL_KINDS = {"OPEN", "PDH", "PDL", "PDC", "PWH", "PWL"}
PAY = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.environ.get("TEMP", "."), "claude",
    "C--Users-kaam-Desktop-operator-mode",
    "f1b3e1c1-1ed6-48af-adf8-96866d72f980", "scratchpad", "war")


def snaps_of(idx):
    with open(os.path.join(ROOT, "data", "chain", f"chain_{idx}_{DAY}.jsonl")) as f:
        return [json.loads(line) for line in f if line.strip()]


def peak_asof(snaps, asof):
    """What ChainState.peak held at `asof`: session-high ABSOLUTE OI per leg."""
    pk = {}
    for r in snaps:
        if r["ts"][:5] > asof:
            break
        for s in r["strikes"]:
            for side in ("ce", "pe"):
                key = (float(s["k"]), side)
                pk[key] = max(pk.get(key, 0), s[side]["oi"] or 0)
    return pk


def rebase(snaps):
    """First minute at which a leg's 09:15 baseline (oi - oi_chg) changed."""
    base, hits = {}, []
    for r in snaps:
        for s in r["strikes"]:
            for side in ("ce", "pe"):
                b = s[side]["oi"] - (s[side]["oi_chg"] or 0)
                key = (s["k"], side)
                if key in base and base[key] != b:
                    hits.append((r["ts"][:5], key, b - base[key]))
                base[key] = b
    if not hits:
        return None
    return {"at": min(h[0] for h in hits), "n": len(hits),
            "legs": len(base), "max": max(abs(h[2]) for h in hits)}


def first_unwinding(minutes, k, side, after, end):
    """First minute after `after` at which section 1d read this leg UNWINDING.

    fronts.read on a grid holding only this strike returns this strike's own
    rows, so the state is the server's function, not a copy of it.
    ponytail: O(n^2) over one session; the server version should roll it once.
    """
    ts = sorted(t for t in minutes if after < t <= end)
    key = str(int(k))
    one = {}
    for t in sorted(t for t in minutes if t <= end):
        one[t] = {"spot": minutes[t]["spot"], "k": {key: minutes[t]["k"].get(key, [0, 0])}}
    for t in ts:
        rows = fronts.read(fronts.cut(one, t))
        f = next((r for r in rows if r["side"] == side), None)
        if f and f["state"] == fronts.UNWINDING:
            return t
    return None


def near_of(minutes, end):
    """The strikes fronts.read ranks among (its NEAR nearest spot at `end`)."""
    last = minutes[max(t for t in minutes if t <= end)]
    ks = [float(k) for k in last["k"]]
    return sorted(sorted(ks, key=lambda k: abs(k - last["spot"]))[:fronts.NEAR])


def cadence(minutes, strikes):
    """How often a near-ATM leg's OI actually changes, minute to minute."""
    ts = sorted(minutes)
    mm = [int(t[:2]) * 60 + int(t[3:]) for t in ts]
    trans = changed = 0
    gaps = Counter()
    for k in strikes:
        key = str(int(k))
        for i in (0, 1):
            last = lastm = None
            for j, t in enumerate(ts):
                c = minutes[t]["k"].get(key)
                if c is None:
                    last = None
                    continue
                if last is not None:
                    trans += 1
                    if c[i] != last:
                        changed += 1
                        if lastm is not None:
                            gaps[mm[j] - lastm] += 1
                        lastm = mm[j]
                last = c[i]
    return {"trans": trans, "changed": changed, "gaps": dict(sorted(gaps.items()))}


def view(idx, minutes, snaps, end, served_peak=None):
    cut = fronts.cut(minutes, end)
    peak = served_peak if served_peak is not None else peak_asof(snaps, end)
    rows = fronts.read(cut, peak)
    brk = fronts.broke(rows)
    out = []
    for f in rows:
        pa = f["peak_at"]
        uw = first_unwinding(minutes, f["k"], f["side"], pa, end)
        out.append({**f, "peak_spot": cut[pa]["spot"],
                    "unwind_at": uw, "unwind_spot": cut[uw]["spot"] if uw else None,
                    "broke": bool(brk and brk["k"] == f["k"] and brk["side"] == f["side"])})
    pk_abs = {}
    for (k, side), v in peak.items():
        pk_abs.setdefault(str(int(k)), [None, None])[0 if side == "ce" else 1] = v
    return {"end": max(t for t in cut), "fronts": out or None,
            "fronts_why": None if out else "no minute carries a spot and a strike grid yet",
            "near": near_of(minutes, end), "peak_abs": pk_abs}


def build(idx):
    pay = json.load(open(os.path.join(PAY, f"oihist_{idx}.json")))
    wm = json.load(open(os.path.join(PAY, f"warmap_{idx}.json")))
    minutes = pay["minutes"]
    ts = sorted(t for t in minutes if "09:15" <= t <= "15:29")
    snaps = snaps_of(idx)
    rb = rebase(snaps)

    # Absolute OI per minute: the LAST snapshot of each minute, as ChainState does for `k`.
    abs_min = {}
    for r in snaps:
        abs_min[r["ts"][:5]] = {str(s["k"]): [s["ce"]["oi"], s["pe"]["oi"]] for s in r["strikes"]}

    strikes = sorted({int(float(k)) for t in ts for k in minutes[t]["k"]})
    K, OI = {}, {}
    for k in strikes:
        key = str(k)
        K[key] = [[(minutes[t]["k"].get(key) or [None, None])[i] if key in minutes[t]["k"] else None
                   for t in ts] for i in (0, 1)]
        OI[key] = [[(abs_min.get(t, {}).get(key) or [None, None])[i] for t in ts] for i in (0, 1)]

    served = {(float(p["k"]), p["side"]): p["oi"] for p in pay["peak"]}
    close_end = ts[-1]
    note = None
    if rb and rb["at"] <= close_end:
        # A restart re-read the open baseline: minutes from rb.at are on another zero.
        close_end = max(t for t in ts if t < rb["at"])
        note = rb
    views = {
        "live": view(idx, minutes, snaps, FROZEN),
        "close": view(idx, minutes, snaps, close_end,
                      served_peak=None if note else served),
    }
    if not note:
        # The close view must be exactly what the server served.
        got = [(f["side"], f["k"], f["state"], f["peak_at"]) for f in views["close"]["fronts"]]
        want = [(f["side"], f["k"], f["state"], f["peak_at"]) for f in pay["fronts"]]
        assert got == want, (idx, got, want)

    step = min(b - a for a, b in zip(strikes, strikes[1:]))
    lv = [{"kind": l["kind"], "px": l["px"], "label": l.get("label")}
          for l in (wm.get("indices", {}).get(idx, {}).get("levels") or [])
          if l.get("kind") in LEVEL_KINDS]
    cad = cadence({t: minutes[t] for t in ts}, views["close"]["near"])
    return {"idx": idx, "day": DAY, "step": step, "t": ts,
            "spot": [minutes[t]["spot"] for t in ts],
            "src": [1 if minutes[t].get("src") == "backfill" else 0 for t in ts],
            "k": K, "oi": OI, "levels": lv, "views": views, "rebase": note,
            "cadence": cad, "feed_start": [min(float(s["k"]) for s in snaps[0]["strikes"]),
                                           max(float(s["k"]) for s in snaps[0]["strikes"]),
                                           snaps[0]["ts"][:5]]}


def main():
    data = {idx: build(idx) for idx in IDXS}
    for idx, d in data.items():
        c = d["cadence"]
        print(idx, "rebase", d["rebase"], "cadence changed", c["changed"], "/", c["trans"],
              "gaps", c["gaps"])
        for vk, v in d["views"].items():
            print("  ", vk, v["end"], [(f["side"], f["k"], f["state"], f["peak_at"],
                                        f["unwind_at"]) for f in v["fronts"] or []])
    html = TEMPLATE.replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    out = os.path.join(HERE, "war-compact-2026-09-24.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", out, len(html) // 1024, "KB")


TEMPLATE = r"""<!doctype html>
<html lang="en" data-mode="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>War, compact</title>
<style>
/* Same tokens as board-chess-2026-09-24.html. Hue = SIDE only (coral CE, teal PE).
   State = GEOMETRY: solid = added, hatched = below its open / giving back, dashed = as it stood
   then. Brass = structure (levels, cursor). Amber = could not check. Rebuilt = WEIGHT, never hue. */
:root, :root[data-mode="dark"] {
  --bg:#0B0E14; --card:#131824; --inset:#1A2030; --line:rgba(255,255,255,.08); --line2:rgba(255,255,255,.16);
  --text:#E8EDF5; --text2:#A3AFC2; --muted:#67748C; --ink:#E8EDF5;
  --coral:#FF7A63; --teal:#2EC4B4; --brass:#E0A852; --caution:#FFBF00;
}
:root[data-mode="light"] {
  --bg:#F5F6F8; --card:#FFFFFF; --inset:#F0F2F5; --line:#E3E7ED; --line2:#C9D0DA;
  --text:#141A22; --text2:#4D5766; --muted:#636C7A; --ink:#141A22;
  --coral:#C4452C; --teal:#0B8277; --brass:#A9762A; --caution:#B45309;
}
* { box-sizing:border-box; }
html,body { margin:0; height:100%; background:var(--bg); color:var(--text); overflow:hidden;
  font-family:Inter,"Segoe UI",system-ui,-apple-system,sans-serif; -webkit-font-smoothing:antialiased; }
.num { font-family:"JetBrains Mono","Cascadia Mono",Consolas,ui-monospace,monospace; font-variant-numeric:tabular-nums; }
.s11 { font-size:11px; line-height:14px; } .s12 { font-size:12px; line-height:15px; }
.s13 { font-size:13px; line-height:17px; } .s17 { font-size:17px; line-height:23px; }
.muted { color:var(--muted); } .t2 { color:var(--text2); }
.ce { color:var(--coral); } .pe { color:var(--teal); } .brass { color:var(--brass); } .amber { color:var(--caution); }
.tag { font-size:10.5px; color:var(--muted); font-family:"JetBrains Mono",Consolas,monospace; }
#stage { position:absolute; left:0; top:0; width:1600px; height:900px; transform-origin:0 0; }
.app { width:1600px; height:900px; padding:8px 24px 10px; display:flex; flex-direction:column; gap:8px; }
.top { height:34px; display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--line); padding-bottom:6px; }
.brand { font-weight:700; letter-spacing:.08em; font-size:13px; }
.chrome { color:var(--muted); font-size:11px; white-space:nowrap; }
.chrome b { color:var(--text); border-bottom:2px solid var(--brass); padding-bottom:2px; font-weight:600; }
.seg { display:flex; gap:3px; }
.btn { border:1px solid var(--line); background:transparent; color:var(--text2); border-radius:6px; padding:3px 9px;
  cursor:pointer; font:inherit; font-size:12px; }
.btn.on { color:var(--text); border-color:var(--line2); background:var(--card); }
.btn:focus-visible { outline:2px solid var(--text2); outline-offset:1px; }
.sp { flex:1; }
.war { display:flex; flex-direction:column; gap:6px; }
.panel { background:var(--card); border:1px solid var(--line); border-radius:8px; }
.answer { display:grid; grid-template-columns:1fr 360px; column-gap:18px; padding:7px 14px 8px; }
.answer .a1 { font-weight:600; }
.answer .meta { text-align:right; min-width:0; }
.main { display:flex; gap:12px; align-items:stretch; }
.mapp { padding:3px; } .ladp { padding:3px; }
svg { display:block; }
#rail { width:328px; display:flex; flex-direction:column; gap:6px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:4px 10px 5px; flex:1; min-height:0; }
.card .ln { font-size:11.5px; line-height:14px; }
.card.first { border-color:var(--line2); }
.card .hd { display:flex; align-items:baseline; gap:7px; white-space:nowrap; }
.card .hd .rk { margin-left:auto; }
.st { font-size:10.5px; font-weight:700; letter-spacing:.06em; }
.chip { font-size:10px; font-weight:700; letter-spacing:.05em; border:1px solid var(--text2); color:var(--text);
  border-radius:3px; padding:0 4px; }
.card .ln { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.meta div { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
#legend { display:flex; flex-wrap:wrap; gap:4px 16px; align-items:center; color:var(--text2); padding:0 4px; }
#legend span { display:inline-flex; align-items:center; gap:5px; }
#prov { padding:0 4px; }
.freed { flex:1; border:1px dashed var(--line2); border-radius:8px; display:flex; flex-direction:column;
  align-items:center; justify-content:center; gap:4px; color:var(--muted); text-align:center; min-height:0; }
</style>
</head>
<body>
<div id="stage"><div class="app">
  <div class="top">
    <span class="brand">TAPEMAP</span>
    <span class="chrome">Board · Glass · Heat · Trade · Tape · Flow · VPIN · Chain · OI Flow · <b>War</b> · Events</span>
    <span class="sp"></span>
    <div class="seg" id="idxSeg"></div>
    <div class="seg" id="viewSeg">
      <button class="btn" data-v="live">Live read at 13:36</button>
      <button class="btn" data-v="close">After close</button>
    </div>
    <button class="btn" id="mode">dark</button>
    <span class="chrome">mockup · real data 2026-09-23 · nothing live</span>
  </div>

  <section class="war" id="war">
    <div class="panel answer">
      <div><div class="a1 s17" id="ans1"></div><div class="s13 t2" id="ans2"></div></div>
      <div class="meta s11 muted" id="meta"></div>
    </div>
    <div class="main">
      <div class="panel mapp"><svg id="map" role="img"></svg></div>
      <div class="panel ladp"><svg id="lad" role="img"></svg></div>
      <div id="rail"></div>
    </div>
    <div class="s11" id="legend"></div>
    <div class="s11 muted" id="prov"></div>
  </section>
  <div class="freed s12" id="freed"></div>
</div></div>

<script>
const D = /*DATA*/null;
const OPEN = 555, CLOSE = 930, SPAN = CLOSE - OPEN, NB = 75, CW = 12;
const GL = 44, PW = NB * CW, LGW = 44, MAPW = GL + PW + LGW, LADW = 206, PT = 6, NEAR_N = 6;
const S = { idx: 'NIFTY', view: 'live', cursor: null, hover: null };
let G = null;

const mm = t => +t.slice(0, 2) * 60 + +t.slice(3, 5);
const hhmm = m => String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');
const xOf = m => GL + (m - OPEN) / SPAN * PW;
const inr = (n, f = 1) => Number(n).toLocaleString('en-IN', { maximumFractionDigits: f });
const L = n => { const a = Math.abs(n); return a >= 1e5 ? (n / 1e5).toFixed(1) + 'L' : a >= 1e3 ? (n / 1e3).toFixed(1) + 'K' : String(Math.round(n)); };
const sL = n => (n > 0 ? '+' : n < 0 ? '−' : '') + L(Math.abs(n));
const HUE = s => s === 0 ? 'var(--coral)' : 'var(--teal)';
const SIDE = s => s === 0 ? 'CE' : 'PE';
const R = (x, y, w, h, st, extra = '') => `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(0, w).toFixed(1)}" height="${Math.max(0, h).toFixed(1)}" style="${st}" ${extra}/>`;
const LN = (x1, y1, x2, y2, st) => `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" style="${st}"/>`;
const TX = (x, y, s, st, a = 'start', cls = '') => `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" text-anchor="${a}" style="${st}" class="${cls}">${s}</text>`;
const DEFS = `<defs>
 <pattern id="h0" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="4" style="stroke:var(--coral);stroke-width:1.5"/></pattern>
 <pattern id="h1" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="4" style="stroke:var(--teal);stroke-width:1.5"/></pattern>
 <pattern id="hn" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><line x1="0" y1="0" x2="0" y2="5" style="stroke:var(--muted);stroke-width:1;stroke-opacity:.45"/></pattern>
</defs>`;

/* ── The model: geometry only. Every front, state and rank comes from the server (fronts.py). ── */
function model() {
  const d = D[S.idx], v = d.views[S.view], endM = mm(v.end), T = d.t.map(mm);
  let last = -1; T.forEach((m, i) => { if (m <= endM) last = i; });
  const at = new Map(); for (let i = 0; i <= last; i++) at.set(T[i], i);
  const step = d.step, atm = d.spot.map(s => s == null ? null : Math.round(s / step) * step);
  let aLo = Infinity, aHi = -Infinity;
  for (let i = 0; i <= last; i++) if (atm[i] != null) { aLo = Math.min(aLo, atm[i]); aHi = Math.max(aHi, atm[i]); }
  // THE WINDOW: every strike that was within ±6 of the ATM at ANY minute so far. Rows only
  // ever get added at an edge; a strike's row never moves off the screen once it is on it.
  const hi = aHi + NEAR_N * step, lo = aLo - NEAR_N * step, rows = [];
  for (let k = hi; k >= lo - 1e-6; k -= step) rows.push(Math.round(k * 100) / 100);
  // 22 px a strike: 8 px CE lane above the strike line, 8 px PE lane below, 5 px between strikes so a
  // strike's two halves pair with each other and not with the neighbour. Never taller than 340 px.
  const P = Math.max(12, Math.min(22, Math.floor(340 / rows.length))), H = Math.max(4, Math.floor((P - 5) / 2));
  const yP = p => PT + (hi - p) / step * P + P / 2, plotH = rows.length * P;
  const key = k => String(Math.round(k));
  const ser = (k, s) => (d.k[key(k)] || [null, null])[s];
  const oiS = (k, s) => (d.oi[key(k)] || [null, null])[s];
  const near = (k, i) => atm[i] != null && Math.abs(k - atm[i]) <= NEAR_N * step + 1e-6;
  let vmax = 0; const st = {};
  for (const k of rows) for (const s of [0, 1]) {
    const a = ser(k, s); let pk = null, pkI = -1, now = null, nowI = -1;
    if (a) for (let i = 0; i <= last; i++) {
      const x = a[i]; if (x == null) continue;
      if (pk == null || x > pk) { pk = x; pkI = i; }
      now = x; nowI = i; if (near(k, i) && x > vmax) vmax = x;
    }
    st[key(k) + s] = { pk, pkI, now, nowI };
  }
  const F = {};
  (v.fronts || []).forEach(f => {
    const s = f.side === 'CE' ? 0 : 1;
    F[key(f.k) + s] = { ...f, s, rank: v.fronts.filter(x => x.side === f.side).indexOf(f) + 1 };
  });
  return { d, v, endM, T, last, at, atm, step, hi, lo, rows, P, H, yP, plotH, key, ser, oiS, near, vmax, st, F };
}
// Square-root colour scale, one scale for the whole map: order and zero are kept, the middle is lifted
// so a 30L front is not lost next to a 127L one. The exact numbers live in the rail and the readout.
const alphaOf = (g, x) => x <= 0 || g.vmax <= 0 ? 0 : 0.08 + 0.82 * Math.sqrt(Math.min(1, x / g.vmax));
const laneY = (g, k, s) => s === 0 ? g.yP(k) - 0.5 - g.H : g.yP(k) + 0.5;
const valAt = (arr, i) => { if (!arr) return null; for (let j = i; j >= 0; j--) if (arr[j] != null) return [arr[j], j]; return null; };

/* ── The map: OI added since the open, strike × 5-minute cell, spot drawn over. ── */
function drawMap() {
  const g = G, o = [DEFS], xEnd = xOf(g.endM + 1), H = g.H;
  const svgH = PT + g.plotH + 46;
  // lanes: a lane that exists was checked; an empty lane is a checked zero
  for (const k of g.rows) for (const s of [0, 1]) o.push(R(xOf(OPEN), laneY(g, k, s), xEnd - xOf(OPEN), H, 'fill:var(--ink);fill-opacity:.035'));
  // cells, absence runs merged per lane
  const cells = [], runs = [], rings = [];
  for (const k of g.rows) for (const s of [0, 1]) {
    const a = g.ser(k, s), y = laneY(g, k, s); let run = null, ring = null;
    const rm = []; let hiw = null;                          // running max: the high so far, minute by minute
    if (a) for (let i = 0; i <= g.last; i++) { if (a[i] != null && (hiw == null || a[i] > hiw)) hiw = a[i]; rm.push(hiw); }
    const flush = () => { if (run) runs.push({ ...run, y }); run = null; };
    const flushRing = () => { if (ring) rings.push({ ...ring, y, s }); ring = null; };
    for (let b = 0; b < NB; b++) {
      const m0 = OPEN + 5 * b; if (m0 > g.endM) break;
      const m1 = Math.min(m0 + 4, g.endM), x0 = xOf(m0), x1 = xOf(m1 + 1);
      let i = -1; for (let m = m1; m >= m0; m--) if (g.at.has(m)) { i = g.at.get(m); break; }
      let type = null, val = null;
      if (i < 0) type = 'nc';                               // no record in this bin: a hole
      else if (!g.near(k, i)) type = 'far';                 // not near ATM then: not shown, by rule
      else if (!a || a[i] == null) type = 'nc';             // near ATM, feed did not carry it
      else val = a[i];
      if (type) { flushRing(); if (run && run.type === type) run.x1 = x1; else { flush(); run = { type, x0, x1 }; } continue; }
      flush();
      const w = g.d.src[i] ? 0.45 : 1;                      // provenance is weight
      const high = rm[i];
      // colour = how much is held (one scale); HEIGHT = the share of its own high still held,
      // anchored on the strike line. A front giving back collapses toward its strike.
      if (val > 0) {
        const h = Math.max(1, H * (high > 0 ? val / high : 1));
        cells.push(R(x0, s === 0 ? y + H - h : y, x1 - x0, h, `fill:${HUE(s)};fill-opacity:${(alphaOf(g, val) * w).toFixed(3)}`));
      } else if (val < 0) cells.push(R(x0, y, x1 - x0, H, `fill:url(#h${s});opacity:${((0.3 + 0.6 * Math.min(1, -val / (g.vmax || 1))) * w).toFixed(3)}`));
      // the ring marks the high wherever the lane sits below it
      if (high > 0 && val < high) {
        const gone = Math.min(1, (high - Math.max(0, val)) / high);
        if (ring) { ring.x1 = x1; ring.hi = Math.max(ring.hi, high); ring.gone = Math.max(ring.gone, gone); } else ring = { x0, x1, hi: high, gone };
      }
      else flushRing();
    }
    flush(); flushRing();
  }
  o.push(...cells);
  for (const r of runs) o.push(r.type === 'far'
    ? R(r.x0, r.y, r.x1 - r.x0, H, 'fill:url(#hn)')
    : R(r.x0 + 0.5, r.y + 0.5, r.x1 - r.x0 - 1, H - 1, 'fill:none;stroke:var(--caution);stroke-opacity:.75;stroke-dasharray:2 2;stroke-width:1'));
  // after close on a re-baselined day: the minutes past the re-read are not comparable
  if (S.view === 'close' && g.d.rebase) for (const k of g.rows) for (const s of [0, 1])
    o.push(R(xEnd + 0.5, laneY(g, k, s) + 0.5, xOf(CLOSE) - xEnd - 1, H - 1, 'fill:none;stroke:var(--caution);stroke-opacity:.75;stroke-dasharray:2 2;stroke-width:1'));
  // the ruin: the ring is the high, the fill inside it is what is still held
  // ring strength = how bright the high was x how much of it is gone: a 2% dip leaves no visible
  // ring, a ruin keeps its walls standing. Continuous, so no threshold is invented here.
  for (const r of rings) { const op = alphaOf(g, r.hi) * r.gone; if (op > 0.02) o.push(R(r.x0 + 0.5, r.y + 0.5, r.x1 - r.x0 - 1, H - 1, `fill:none;stroke:${HUE(r.s)};stroke-opacity:${op.toFixed(3)};stroke-width:1`)); }
  // named levels (brass) — codes live in the level gutter
  const tags = [];
  for (const l of g.d.levels) {
    const y = g.yP(l.px); if (y < PT || y > PT + g.plotH) continue;
    o.push(LN(GL, y, GL + PW, y, 'stroke:var(--brass);stroke-opacity:.55;stroke-dasharray:3 4;stroke-width:1'));
    tags.push({ y, s: l.kind, st: 'fill:var(--brass);font-size:9.5px', pri: 0 });
  }
  // spot, broken on holes
  let seg = [], pts = [];
  for (let i = 0; i <= g.last; i++) {
    const sp = g.d.spot[i]; if (i > 0 && g.T[i] - g.T[i - 1] > 5) { if (seg.length > 1) pts.push(seg); seg = []; }
    if (sp == null) { if (seg.length > 1) pts.push(seg); seg = []; continue; }
    seg.push(`${(xOf(g.T[i]) + 1.2).toFixed(1)},${g.yP(sp).toFixed(1)}`);
  }
  if (seg.length > 1) pts.push(seg);
  for (const p of pts) o.push(`<polyline points="${p.join(' ')}" style="fill:none;stroke:var(--ink);stroke-width:1.7;stroke-opacity:.92;stroke-linejoin:round"/>`);
  const spNow = g.d.spot[g.last];
  if (spNow != null) tags.push({ y: g.yP(spNow), s: '◂' + inr(spNow, 0), st: 'fill:var(--ink);font-size:9.5px;font-weight:600', pri: 1 });
  tags.sort((a, b) => a.y - b.y); let lastY = -1e9;
  for (const t of tags) { const y = Math.max(t.y + 3.3, lastY + 10.5); lastY = y; o.push(TX(GL + PW + 4, y, t.s, t.st, 'start', 'num')); }
  // the fronts: minute-exact high tick, dashed tick where §1d first read it unwinding
  for (const id in g.F) {
    const f = g.F[id], y = laneY(g, f.k, f.s);
    const xp = xOf(mm(f.peak_at)) + 1.2;
    o.push(LN(xp, y - 1.5, xp, y + H + 1.5, 'stroke:var(--ink);stroke-width:2'));
    if (f.unwind_at) { const xu = xOf(mm(f.unwind_at)) + 1.2; o.push(LN(xu, y - 1, xu, y + H + 1, 'stroke:var(--ink);stroke-width:1.3;stroke-dasharray:2 1.5')); }
    o.push(R(0, y, 3, H, `fill:${HUE(f.s)}`));
  }
  // strike labels
  const atmNow = g.atm[g.last];
  for (const k of g.rows) {
    const isF = g.F[g.key(k) + 0] || g.F[g.key(k) + 1];
    const st = Math.abs(k - atmNow) < 1e-6 ? 'fill:var(--brass);font-weight:700' : isF ? 'fill:var(--text);font-weight:600' : 'fill:var(--muted)';
    o.push(TX(GL - 5, g.yP(k) + 3.4, inr(k, 0), st + ';font-size:10px', 'end', 'num'));
  }
  // time axis
  const ay = PT + g.plotH;
  o.push(LN(GL, ay + 0.5, GL + PW, ay + 0.5, 'stroke:var(--line2)'));
  const special = [g.endM + 1]; if (S.cursor != null) special.push(S.cursor);
  const hours = [OPEN, 600, 660, 720, 780, 840, 900, CLOSE];
  for (const m of hours) {
    o.push(LN(xOf(m), ay, xOf(m), ay + 4, 'stroke:var(--line2)'));
    if (special.every(s => Math.abs(xOf(s) - xOf(m)) > 30)) o.push(TX(xOf(m), ay + 14, hhmm(m), 'fill:var(--muted);font-size:10px', 'middle', 'num'));
  }
  o.push(LN(xEnd, PT, xEnd, ay + 4, 'stroke:var(--ink);stroke-opacity:.55;stroke-width:1'));
  o.push(TX(xEnd, ay + 14, S.view === 'live' ? hhmm(g.endM) + ' now' : hhmm(g.endM), 'fill:var(--text);font-size:10px;font-weight:700', 'middle', 'num'));
  // event row: ◆ where a front stopped adding (its high), ◇ where §1d first read it unwinding
  const ey = ay + 27, evs = [];
  for (const id in g.F) {
    const f = g.F[id];
    evs.push({ x: xOf(mm(f.peak_at)) + 1.2, t: f.peak_at, s: f.s, kind: 'stop' });
    if (f.unwind_at) evs.push({ x: xOf(mm(f.unwind_at)) + 1.2, t: f.unwind_at, s: f.s, kind: 'unw' });
  }
  for (const e of evs) {
    const dm = `M${e.x} ${ey - 5}L${e.x + 4} ${ey}L${e.x} ${ey + 5}L${e.x - 4} ${ey}Z`;
    o.push(e.kind === 'stop' ? `<path d="${dm}" style="fill:${HUE(e.s)}"/>` : `<path d="${dm}" style="fill:var(--card);stroke:${HUE(e.s)};stroke-width:1.2"/>`);
  }
  const lab = evs.filter(e => e.kind === 'stop').sort((a, b) => a.x - b.x); let lx = -1e9;
  for (const e of lab) { const x = Math.max(e.x, lx + 31); lx = x; o.push(TX(x, ey + 16, e.t, `fill:${HUE(e.s)};font-size:9.5px`, 'middle', 'num')); }
  o.push('<g id="mapov"></g>');
  const svg = document.getElementById('map');
  svg.setAttribute('width', MAPW); svg.setAttribute('height', svgH); svg.setAttribute('viewBox', `0 0 ${MAPW} ${svgH}`);
  svg.setAttribute('aria-label', `${g.d.idx} open-interest change since the open by strike and time, within six strikes of the ATM`);
  svg.innerHTML = o.join('');
}

/* ── The overlay: hover row, pinned cursor. Never rebuilds the cells. ── */
function drawMapOverlay() {
  const g = G, o = [], ay = PT + g.plotH;
  if (S.hover) {
    const { k, m } = S.hover;
    o.push(R(0.5, g.yP(k) - g.P / 2 + 0.5, MAPW - 1, g.P - 1, 'fill:none;stroke:var(--text2);stroke-opacity:.6;stroke-width:1'));
    for (const s of [0, 1]) {
      const q = g.st[g.key(k) + s]; if (q.pk == null || q.pk <= 0 || g.F[g.key(k) + s]) continue;
      const x = xOf(g.T[q.pkI]) + 1.2, y = laneY(g, k, s);
      o.push(LN(x, y - 1, x, y + g.H + 1, 'stroke:var(--ink);stroke-width:1.4;stroke-opacity:.8'));
    }
    o.push(LN(xOf(m) + 1.2, PT, xOf(m) + 1.2, ay, 'stroke:var(--text2);stroke-opacity:.35'));
  }
  if (S.cursor != null) {
    const x = xOf(S.cursor) + 1.2;
    o.push(LN(x, PT - 2, x, ay + 4, 'stroke:var(--brass);stroke-width:1.4'));
    o.push(TX(x, ay + 14, hhmm(S.cursor), 'fill:var(--brass);font-size:10px;font-weight:700', 'middle', 'num'));
  }
  document.getElementById('mapov').innerHTML = o.join('');
}

/* ── The ladder: the book NOW, mirrored CE | strike | PE, top two per side boxed by the server. ── */
function drawLadder() {
  const g = G, o = [DEFS], svgH = PT + g.plotH + 46, cx0 = 76, cx1 = 130, BW = 72, bh = Math.min(12, g.P - 6);
  const iEnd = g.last, iCur = S.cursor != null ? (() => { let j = -1; g.T.forEach((m, i) => { if (m <= S.cursor && i <= g.last) j = i; }); return j; })() : -1;
  const pk = g.v.peak_abs;
  let amax = 0;
  for (const k of g.rows) for (const s of [0, 1]) {
    const n = valAt(g.oiS(k, s), iEnd), p = (pk[g.key(k)] || [])[s];
    amax = Math.max(amax, n ? n[0] : 0, p || 0);
  }
  const len = x => amax > 0 ? x / amax * BW : 0;
  const nearSet = new Set((g.v.near || []).map(k => g.key(k)));
  for (const k of g.rows) if (nearSet.has(g.key(k))) o.push(R(cx0 + 2, g.yP(k) - g.P / 2, cx1 - cx0 - 4, g.P, 'fill:var(--ink);fill-opacity:.06'));
  const atmNow = g.atm[g.last];
  for (const k of g.rows) {
    const y = g.yP(k);
    for (const s of [0, 1]) {
      const n = valAt(g.oiS(k, s), iEnd), p = (pk[g.key(k)] || [])[s];
      const dir = s === 0 ? -1 : 1, base = s === 0 ? cx0 : cx1;
      if (!n) { o.push(R(s === 0 ? base - 18 : base, y - bh / 2, 18, bh, 'fill:none;stroke:var(--caution);stroke-dasharray:2 2;stroke-opacity:.7')); continue; }
      const w = len(n[0]);
      o.push(R(s === 0 ? base - w : base, y - bh / 2, w, bh, `fill:${HUE(s)};fill-opacity:.55`));
      if (p) { const xp = base + dir * len(p); o.push(LN(xp, y - bh / 2 - 2, xp, y + bh / 2 + 2, 'stroke:var(--ink);stroke-width:1.5')); }
      if (iCur >= 0) {
        const c = valAt(g.oiS(k, s), iCur);
        if (c) { const wc = len(c[0]); o.push(R(s === 0 ? base - wc : base, y - bh / 2 + 0.5, wc, bh - 1, `fill:none;stroke:var(--brass);stroke-width:1;stroke-dasharray:2.5 1.5`)); }
      }
      const f = g.F[g.key(k) + s];
      if (f) {
        const far = Math.max(w, p ? len(p) : 0) + 3;
        o.push(R(s === 0 ? base - far : base - 1, y - bh / 2 - 3, far + 1, bh + 6, 'fill:none;stroke:var(--text);stroke-width:1'));
        o.push(TX(s === 0 ? base - far - 4 : base + far + 4, y + 3.5, String(f.rank), `fill:${HUE(s)};font-size:10px;font-weight:700`, s === 0 ? 'end' : 'start', 'num'));
      }
    }
    const isF = g.F[g.key(k) + 0] || g.F[g.key(k) + 1];
    const st = Math.abs(k - atmNow) < 1e-6 ? 'fill:var(--brass);font-weight:700' : isF ? 'fill:var(--text);font-weight:600' : 'fill:var(--muted)';
    o.push(TX((cx0 + cx1) / 2, y + 3.4, inr(k, 0), st + ';font-size:10px', 'middle', 'num'));
  }
  const ay = PT + g.plotH;
  o.push(TX(cx0 - 2, ay + 14, 'CE', 'fill:var(--coral);font-size:10px;font-weight:700', 'end'));
  o.push(TX(cx1 + 2, ay + 14, 'PE', 'fill:var(--teal);font-size:10px;font-weight:700', 'start'));
  o.push(TX((cx0 + cx1) / 2, ay + 14, 'OI now', 'fill:var(--muted);font-size:9.5px', 'middle'));
  o.push(TX((cx0 + cx1) / 2, ay + 27, `full bar ${L(amax)} · │ = session high`, 'fill:var(--muted);font-size:9.5px', 'middle', 'num'));
  o.push(iCur >= 0 ? TX((cx0 + cx1) / 2, ay + 40, `dashed = OI at ${hhmm(S.cursor)}`, 'fill:var(--brass);font-size:9.5px', 'middle', 'num')
    : TX((cx0 + cx1) / 2, ay + 40, `box = top two · shade = §1d's 9`, 'fill:var(--muted);font-size:9.5px', 'middle'));
  const svg = document.getElementById('lad');
  svg.setAttribute('width', LADW); svg.setAttribute('height', svgH); svg.setAttribute('viewBox', `0 0 ${LADW} ${svgH}`);
  svg.setAttribute('aria-label', `${g.d.idx} open interest now, calls left and puts right, the top two per side boxed`);
  svg.innerHTML = o.join('');
}

/* ── The rail: the four fronts, in the order they stopped. Every word on this screen lives here. ── */
function drawRail() {
  const g = G, el = document.getElementById('rail'), v = g.v;
  if (!v.fronts) { el.innerHTML = `<div class="card s12 amber">Near-ATM fronts could not be read: ${v.fronts_why}. This is not "no fronts"; nothing was checked.</div>`; return; }
  const fs = [...v.fronts].sort((a, b) => (a.state === 'BUILDING') - (b.state === 'BUILDING') || (a.peak_at < b.peak_at ? -1 : 1));
  const smax = Math.max(...fs.map(f => f.peak), 1), W = 306, SH = 16;
  const res = resolution(g.d);
  el.innerHTML = fs.map(f => {
    const s = f.side === 'CE' ? 0 : 1, a = g.ser(f.k, s), rank = g.F[g.key(f.k) + s].rank;
    const X = m => (m - OPEN) / SPAN * W, Y = x => SH - Math.max(0, x) / smax * (SH - 2);
    let area = '', crest = '', run = -Infinity, seg = [], cseg = [];
    const segs = [], csegs = [];
    for (let i = 0; i <= g.last; i++) {
      const x = a ? a[i] : null, m = g.T[i];
      if (x == null || (i > 0 && m - g.T[i - 1] > 5)) { if (seg.length) { segs.push(seg); csegs.push(cseg); } seg = []; cseg = []; if (x == null) continue; }
      run = Math.max(run, x); seg.push([X(m), Y(x)]); cseg.push([X(m), Y(run)]);
    }
    if (seg.length) { segs.push(seg); csegs.push(cseg); }
    for (const sg of segs) area += `<path d="M${sg[0][0].toFixed(1)},${SH}${sg.map(p => `L${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('')}L${sg[sg.length - 1][0].toFixed(1)},${SH}Z" style="fill:${HUE(s)};fill-opacity:.45"/>`;
    for (const sg of csegs) crest += `<path d="M${sg.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('L')}" style="fill:none;stroke:${HUE(s)};stroke-width:1"/>`;
    const xp = X(mm(f.peak_at)) + 0.4, xu = f.unwind_at ? X(mm(f.unwind_at)) + 0.4 : null, xn = X(g.endM + 1);
    const glyph = f.state === 'BUILDING' ? `<rect x="0" y="0" width="9" height="9" style="fill:${HUE(s)}"/>`
      : f.state === 'STALLED' ? `<rect x="0.5" y="0.5" width="8" height="8" style="fill:${HUE(s)};fill-opacity:.35;stroke:${HUE(s)}"/>`
      : `<rect x="0.5" y="0.5" width="8" height="8" style="fill:url(#h${s});stroke:${HUE(s)}"/>`;
    const off = f.peak - f.chg, under = f.state === 'BUILDING' && f.peak > 0 && off >= 0.15 * f.peak;
    const line1 = f.state === 'BUILDING' && !under
      ? `adding · high so far <b class="num">${f.peak_at}</b> @ spot <span class="num">${inr(f.peak_spot, 0)}</span>`
      : `stopped adding <b class="num">${f.peak_at}</b> @ spot <span class="num">${inr(f.peak_spot, 0)}</span>`;
    const line1b = f.unwind_at ? `→ §1d: unwinding <b class="num">${f.unwind_at}</b> @ <span class="num">${inr(f.unwind_spot, 0)}</span>` + (under ? ' · adding again now' : '')
      : f.state === 'BUILDING' ? '' : '→ §1d: not read unwinding yet';
    const line2 = `now <span class="num">${sL(f.chg)}</span> · ` +
      (off > 0 ? `<b class="num">${sL(-off)}</b> off its <span class="num">${sL(f.peak)}</span> high` : 'at its high') +
      ` <span class="tag">[M] ±${res}m</span>`;
    return `<div class="card${f.broke ? ' first' : ''}">
      <div class="hd"><svg width="9" height="9" style="align-self:center">${DEFS}${glyph}</svg>
        <b class="s13 ${s === 0 ? 'ce' : 'pe'}">${f.side}</b><b class="s13 num">${inr(f.k, 0)}</b>
        <span class="st ${s === 0 ? 'ce' : 'pe'}">${f.state}</span>${f.broke ? '<span class="chip" title="the front that stopped adding first and is giving back (server: broke)">FIRST</span>' : ''}
        <span class="rk s11 muted num" title="rank by session-high absolute OI (server)">#${rank} · ${f.oi != null ? L(f.oi) : 'no OI high'}</span></div>
      <svg width="${W}" height="${SH + 2}" style="margin:2px 0 1px">${DEFS}
        ${R(0, 0, xn, SH, 'fill:var(--ink);fill-opacity:.035')}${area}${crest}
        ${LN(xp, 0, xp, SH, 'stroke:var(--ink);stroke-width:2')}
        ${xu != null ? LN(xu, 0, xu, SH, 'stroke:var(--ink);stroke-width:1.2;stroke-dasharray:2 1.5') : ''}
        ${LN(xn, 0, xn, SH, 'stroke:var(--ink);stroke-opacity:.4')}</svg>
      <div class="s12 t2 ln">${line1}</div>${line1b ? `<div class="s12 t2 ln">${line1b}</div>` : ''}<div class="s12 t2 ln">${line2}</div></div>`;
  }).join('');
}

function resolution(d) {
  // The measured step between OI changes on this feed, as the error bar on every stamp.
  const gp = d.cadence.gaps; let best = 1, n = -1;
  for (const k in gp) if (gp[k] > n) { n = gp[k]; best = +k; }
  return best;
}

/* ── The sentences ── */
function drawText() {
  const g = G, d = g.d, v = g.v, res = resolution(d);
  const a1 = document.getElementById('ans1'), a2 = document.getElementById('ans2');
  if (!v.fronts) { a1.innerHTML = `<span class="amber">Near-ATM fronts could not be read — ${v.fronts_why}.</span>`; a2.textContent = ''; }
  else {
    const b = v.fronts.find(f => f.broke);
    const nm = f => `<span class="${f.side === 'CE' ? 'ce' : 'pe'}">${f.side} ${inr(f.k, 0)}</span>`;
    if (!b) a1.innerHTML = `All four top fronts are still adding — none has stopped.`;
    else a1.innerHTML = `${nm(b)} stopped adding first — <span class="num">${b.peak_at}</span>, spot <span class="num">${inr(b.peak_spot, 0)}</span> — and has given back <span class="num">${L(b.peak - b.chg)}</span> of its <span class="num">${L(b.peak)}</span> build` +
      (b.unwind_at ? `; unwinding by §1d since <span class="num">${b.unwind_at}</span>.` : '.') + ` <span class="tag">[M]</span>`;
    if (b && b.chg < 0) a1.innerHTML = `${nm(b)} stopped adding first — <span class="num">${b.peak_at}</span>, spot <span class="num">${inr(b.peak_spot, 0)}</span> — gave back all <span class="num">${L(b.peak)}</span> and sits <span class="num">${L(-b.chg)}</span> below its open` +
      (b.unwind_at ? `; unwinding by §1d since <span class="num">${b.unwind_at}</span>.` : '.') + ` <span class="tag">[M]</span>`;
    const rest = v.fronts.filter(f => !f.broke).sort((x, y) => (x.state === 'BUILDING') - (y.state === 'BUILDING') || (x.peak_at < y.peak_at ? -1 : 1));
    const bits = rest.map(f => f.state === 'BUILDING'
      ? `${nm(f)} still adding (<span class="num">${sL(f.chg)}</span>)`
      : `${nm(f)} stopped <span class="num">${f.peak_at}</span> @ <span class="num">${inr(f.peak_spot, 0)}</span>, <span class="num">${L(f.peak - f.chg)}</span> off`);
    const adding = v.fronts.filter(f => f.state === 'BUILDING').length;
    a2.innerHTML = (adding === 0 ? 'None of the four top fronts is adding. ' : `${adding} of the four top fronts ${adding === 1 ? 'is' : 'are'} adding. `) +
      (bits.length ? 'Then: ' + bits.join(' · ') + '.' : '');
  }
  const sp = d.spot[g.last];
  META = 
    `<b class="s13" style="color:var(--text)">${d.idx}</b> · <span class="num">${S.view === 'live' ? hhmm(g.endM) + ' live read' : 'after close, as of ' + hhmm(g.endM)}</span><br>` +
    `spot <span class="num">${inr(sp)}</span> · ATM <span class="num brass">${inr(g.atm[g.last], 0)}</span> · rows <span class="num">${inr(g.lo, 0)}–${inr(g.hi, 0)}</span><br>` +
    `±6 of every ATM since 09:15 · hover a row · click to pin a cursor`;
  // legend
  const sw = (inner, w = 22) => `<svg width="${w}" height="10">${DEFS}${inner}</svg>`;
  document.getElementById('legend').innerHTML = [
    `<span>${sw(R(0, 1, 10, 8, 'fill:var(--coral);fill-opacity:.9') + R(11, 1, 10, 8, 'fill:var(--teal);fill-opacity:.35'))}added since the open (√ colour, one scale, full = <b class="num">${L(g.vmax)}</b>)</span>`,
    `<span>${sw(R(0.5, 0.5, 21, 9, 'fill:none;stroke:var(--coral);stroke-opacity:.9') + R(1, 6.5, 20, 3, 'fill:var(--coral);fill-opacity:.5'))}ring = its high, fill height = share still held</span>`,
    `<span>${sw(R(0, 1, 22, 8, 'fill:url(#h0)'))}below its open</span>`,
    `<span>${sw(LN(6, 0, 6, 10, 'stroke:var(--ink);stroke-width:2') + LN(15, 0, 15, 10, 'stroke:var(--ink);stroke-width:1.3;stroke-dasharray:2 1.5'))}stopped · first read unwinding (±${res} min)</span>`,
    `<span>${sw(R(0, 1, 22, 8, 'fill:url(#hn)'))}outside ±6 of ATM then (not shown)</span>`,
    `<span>${sw(R(0.5, 1.5, 21, 7, 'fill:none;stroke:var(--caution);stroke-dasharray:2 2'))}could not check</span>`,
    `<span>${sw(R(0, 1, 22, 8, 'fill:var(--coral);fill-opacity:.3'))}rebuilt minute (lighter)</span>`,
  ].join('');
  // provenance: three absences kept apart
  const n = g.last + 1, rebuilt = d.src.slice(0, n).filter(Boolean).length;
  let holes = 0; for (let i = 1; i < n; i++) if (g.T[i] - g.T[i - 1] > 5) holes++;
  let nc = 0, farN = 0;
  for (const k of g.rows) for (const s of [0, 1]) { const a = g.ser(k, s); for (let i = 0; i < n; i++) { if (!g.near(k, i)) { farN++; continue; } if (!a || a[i] == null) nc++; } }
  const c = d.cadence, pct = Math.round(100 * c.changed / c.trans);
  const fs = d.feed_start;
  const lv = d.levels.filter(l => { const y = g.yP(l.px); return y >= PT && y <= PT + g.plotH; }).map(l => `${l.kind} ${inr(l.px)}`).join(' · ');
  let p = `Record ${d.t[0]}–${hhmm(g.endM)}: ${n} minutes, ${rebuilt} rebuilt (drawn lighter), ${holes ? holes + ' holes (amber)' : 'no holes'}. ` +
    `OI on this feed changed on ${pct}% of minute-to-minute reads, most often every ${res} min, so every stamp is ±${res} min [M]. ` +
    `The feed subscribed ${inr(fs[0], 0)}–${inr(fs[1], 0)} at ${fs[2]} (±8 of that ATM); ` +
    (nc ? `${nc} near-ATM strike-minutes it never carried are amber: could not check.` : 'it carried every near-ATM strike-minute.');
  if (S.view === 'close' && d.rebase) p += ` <span class="amber">Drawn to ${hhmm(g.endM)} only: a restart at ${d.rebase.at} re-read the 09:15 OI baseline and ${d.rebase.n} of ${d.rebase.legs} legs moved (up to ${L(d.rebase.max)}) with no trade behind it, so ${d.rebase.at}–15:29 cannot be compared with the morning.</span>`;
  if (lv) p += ` Brass: ${lv}.`;
  document.getElementById('prov').innerHTML = p;
  readout(null);
}

let META = '';
function readout(h) {
  const g = G, el = document.getElementById('meta');
  if (!h) { el.innerHTML = META; return; }
  const { k, m } = h; let i = -1; g.T.forEach((t, j) => { if (t <= m && j <= g.last) i = j; });
  if (i < 0) { el.textContent = `${inr(k, 0)} · ${hhmm(m)}: no record at or before this minute.`; return; }
  const part = s => {
    const a = g.ser(k, s), q = g.st[g.key(k) + s], x = a ? a[i] : null;
    const now = x == null ? (g.near(k, i) ? '<span class="amber">not carried</span>' : '—') : `<span class="num">${sL(x)}</span>`;
    const hi = q.pk != null && q.pk > 0 ? ` (high <span class="num">${sL(q.pk)}</span> at <span class="num">${hhmm(g.T[q.pkI])}</span>, spot <span class="num">${inr(g.d.spot[q.pkI], 0)}</span>)` : '';
    return `<b class="${s === 0 ? 'ce' : 'pe'}">${SIDE(s)}</b> ${now}${hi}`;
  };
  el.innerHTML = `<div><b class="num" style="color:var(--text)">${inr(k, 0)}</b> at <b class="num" style="color:var(--text)">${hhmm(g.T[i])}</b> · spot <span class="num">${inr(g.d.spot[i])}</span> · ` +
    (g.near(k, i) ? 'within ±6 of ATM' : 'outside ±6 of ATM') + `</div><div class="t2">${part(0)}</div><div class="t2">${part(1)} <span class="tag">since open [M]</span></div>`;
}

function render() {
  G = model(); S.hover = null;
  drawMap(); drawMapOverlay(); drawLadder(); drawRail(); drawText();
  document.querySelectorAll('#idxSeg .btn').forEach(b => b.classList.toggle('on', b.dataset.i === S.idx));
  document.querySelectorAll('#viewSeg .btn').forEach(b => b.classList.toggle('on', b.dataset.v === S.view));
  const hWar = document.getElementById('war').getBoundingClientRect().height / scale;
  document.getElementById('freed').innerHTML =
    `<b style="color:var(--text2)">This WAR: ${Math.round(hWar)} px tall, no scroll.</b>` +
    `<span>Today's WAR at this width: a 1220×820 map (740 px plot) beside a 300 px rail ≈ 890 px tall; in the ~690 px tab area of a 1600×900 laptop it scrolls.</span>` +
    `<span>Everything below this line is screen handed back.</span>`;
}

let scale = 1;
function fit() { scale = Math.min(innerWidth / 1600, innerHeight / 900); document.getElementById('stage').style.transform = `scale(${scale})`; }
addEventListener('resize', fit);

document.getElementById('idxSeg').innerHTML = Object.keys(D).map(i => `<button class="btn" data-i="${i}">${i}</button>`).join('');
document.getElementById('idxSeg').addEventListener('click', e => { const b = e.target.closest('.btn'); if (!b) return; S.idx = b.dataset.i; S.cursor = S.view === 'close' ? 816 : null; render(); });
document.getElementById('viewSeg').addEventListener('click', e => { const b = e.target.closest('.btn'); if (!b) return; S.view = b.dataset.v; S.cursor = S.view === 'close' ? 816 : null; render(); });
document.getElementById('mode').addEventListener('click', e => {
  const r = document.documentElement, m = r.dataset.mode === 'dark' ? 'light' : 'dark';
  r.dataset.mode = m; e.target.textContent = m === 'dark' ? 'light' : 'dark';
});
const mapEl = document.getElementById('map');
function hit(e) {
  const r = mapEl.getBoundingClientRect(), x = (e.clientX - r.left) / scale, y = (e.clientY - r.top) / scale;
  if (x < GL || x > GL + PW || y < PT || y > PT + G.plotH) return null;
  const m = Math.min(G.endM, Math.floor(OPEN + (x - GL) / PW * SPAN));
  const k = G.rows[Math.min(G.rows.length - 1, Math.max(0, Math.floor((y - PT) / G.P)))];
  return { k, m };
}
mapEl.addEventListener('mousemove', e => { const h = hit(e); S.hover = h; drawMapOverlay(); readout(h); });
mapEl.addEventListener('mouseleave', () => { S.hover = null; drawMapOverlay(); readout(null); });
mapEl.addEventListener('click', e => { const h = hit(e); if (!h) return; S.cursor = S.cursor === h.m ? null : h.m; drawMapOverlay(); drawLadder(); });
addEventListener('keydown', e => { if (e.key === 'Escape') { S.cursor = null; drawMapOverlay(); drawLadder(); } });
fit(); render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
