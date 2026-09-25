"""Build war-compact-rev2-2026-09-24.html (WAR rev 2). Read-only.

    python docs/mockups/gen_war_compact_rev2.py [PAYLOAD_DIR]

Reuses rev 1's data pass (gen_war_compact.build: the minute grid, absolute OI,
fronts via fronts.read, the 15:27 re-baseline cut) and adds three facts, each
taken from the server's own code or record, never re-derived here:

  first  -- the first minute fronts.broke() named an UNWINDING front, with peak
            OI as the poller held it at that minute. Stamped once.
  under  -- a BUILDING front at least fronts.UNWIND_FRAC under its own high
            (the same test fronts.fade_gate words as "adding again").
  dwells -- APPROACH->DWELL->exit from data/warmap/warmap_2026-09-23.jsonl, the
            war map's forward log (dwell.py + sequence.py), observed rows only.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_war_compact as rev1  # noqa: E402  (also puts ROOT on sys.path)
import fronts                    # noqa: E402
import dwell as dwell_mod        # noqa: E402  (constants only)

DWELL_LOG = os.path.join(rev1.ROOT, "data", "warmap", f"warmap_{rev1.DAY}.jsonl")


def first_stop(minutes, ts, snaps):
    """(named_at, front) for the first minute broke() named an UNWINDING front."""
    pk, j = {}, 0
    for t in ts:
        while j < len(snaps) and snaps[j]["ts"][:5] <= t:
            for s in snaps[j]["strikes"]:
                for side in ("ce", "pe"):
                    key = (float(s["k"]), side)
                    pk[key] = max(pk.get(key, 0), s[side]["oi"] or 0)
            j += 1
        b = fronts.broke(fronts.read(fronts.cut(minutes, t), dict(pk)))
        if b and b["state"] == fronts.UNWINDING:
            return t, b
    return None, None


def dwells_of(idx):
    rows = [json.loads(line) for line in open(DWELL_LOG) if line.strip()]
    rows = [r for r in rows if r.get("idx") == idx and not r.get("backfill")]
    out = []
    for i, r in enumerate(rows):
        if r.get("to") != "DWELL":
            continue
        ex = next((x for x in rows[i + 1:] if x["level"] == r["level"] and x["px"] == r["px"]
                   and x.get("from") == "DWELL"), None)
        t_dw = r["ts"][11:19]
        h, m, s = (int(x) for x in t_dw.split(":"))
        t0 = h * 3600 + m * 60 + s - dwell_mod.DWELL_MIN_S
        out.append({"kind": r["level"], "px": r["px"], "band": r["band"],
                    "t0": f"{t0 // 3600:02d}:{t0 % 3600 // 60:02d}", "t_dwell": t_dw[:5],
                    "t_exit": ex["ts"][11:16] if ex else None, "exit_to": ex["to"] if ex else None,
                    "oi_ce": r.get("oi_ce"), "oi_pe": r.get("oi_pe")})
    return out


def loaded(minutes, ts, px, step, t0, t1):
    """OI change per leg within dwell.NEAR_STEPS strikes of the level, t0 -> t1 [M]."""
    a = max((t for t in ts if t <= t0), default=None)
    b = max((t for t in ts if t <= t1), default=None)
    if a is None or b is None:
        return []
    legs = []
    for key, cell in minutes[b]["k"].items():
        k = float(key)
        if abs(k - px) > dwell_mod.NEAR_STEPS * step + 1e-6:
            continue
        c0 = minutes[a]["k"].get(key)
        if c0 is None:
            continue
        for i, side in ((0, "CE"), (1, "PE")):
            legs.append({"side": side, "k": k, "dk": cell[i] - c0[i]})
    return sorted(legs, key=lambda x: -abs(x["dk"]))


def main():
    data = {}
    for idx in rev1.IDXS:
        d = rev1.build(idx)
        pay = json.load(open(os.path.join(rev1.PAY, f"oihist_{idx}.json")))
        minutes = pay["minutes"]
        ts = d["t"]
        snaps = rev1.snaps_of(idx)
        named_at, b = first_stop(minutes, ts, snaps)
        dw = dwells_of(idx)
        for vk, v in d["views"].items():
            end = v["end"]
            for f in v["fronts"] or []:
                f["under"] = bool(f["state"] == fronts.BUILDING and
                                  -f["from_peak"] >= fronts.UNWIND_FRAC * max(abs(f["peak"]), 1.0))
            v["first"] = None
            if b and named_at <= end:
                key = str(int(b["k"]))
                ser = [(t, minutes[t]["k"][key][0 if b["side"] == "CE" else 1])
                       for t in ts if t <= end and key in minutes[t]["k"]]
                hi_t, hi = max(ser, key=lambda p: p[1])
                v["first"] = {"named_at": named_at, "side": b["side"], "k": b["k"],
                              "peak_at": b["peak_at"], "peak": b["peak"],
                              "peak_spot": minutes[b["peak_at"]]["spot"],
                              "unwind_at": named_at, "now": ser[-1][1],
                              "hi": hi, "hi_at": hi_t}
            vd = []
            for x in dw:
                if x["t_dwell"] > end:
                    continue
                active = x["t_exit"] is None or x["t_exit"] > end
                t1 = end if active else x["t_exit"]
                vd.append({**x, "active": active, "t_end": t1,
                           "legs": loaded(minutes, ts, x["px"], d["step"], x["t0"], t1)[:4]})
            v["dwells"] = vd
        data[idx] = d
        print(idx, "first", named_at, b and (b["side"], b["k"], b["peak_at"]),
              "dwells", [(x["t0"], x["t_exit"], x["px"]) for x in dw])
    html = TEMPLATE.replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    out = os.path.join(HERE, "war-compact-rev2-2026-09-24.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", out, len(html) // 1024, "KB")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>War, compact rev 2</title>
<style>
/* LIGHT ONLY (her call, 2026-09-24). Hue = SIDE only (coral CE, teal PE). State = GEOMETRY: solid =
   added, hatched = below its open, ring = its high, dashed = as it stands / at the cursor. Brass =
   structure (levels, dwell boxes, cursor). Amber = could not check. Rebuilt = WEIGHT, never hue.
   Rank = WEIGHT too: the four fronts full ink, the rest of §1d's nine half, outside the nine faint. */
:root {
  --bg:#F5F6F8; --card:#FFFFFF; --inset:#F0F2F5; --line:#E3E7ED; --line2:#C9D0DA;
  --text:#141A22; --text2:#4D5766; --muted:#636C7A; --ink:#141A22;
  --coral:#C4452C; --teal:#0B8277; --brass:#A9762A; --caution:#B45309;
}
* { box-sizing:border-box; }
html,body { margin:0; background:#E9ECF0; color:var(--text);
  font-family:Inter,"Segoe UI",system-ui,-apple-system,sans-serif; -webkit-font-smoothing:antialiased; }
.num { font-family:"JetBrains Mono","Cascadia Mono",Consolas,ui-monospace,monospace; font-variant-numeric:tabular-nums; }
.s11 { font-size:11px; line-height:14px; } .s12 { font-size:12px; line-height:15px; }
.s13 { font-size:13px; line-height:17px; } .s17 { font-size:16px; line-height:21px; }
.muted { color:var(--muted); } .t2 { color:var(--text2); }
.ce { color:var(--coral); } .pe { color:var(--teal); } .brass { color:var(--brass); } .amber { color:var(--caution); }
.tag { white-space:nowrap; font-size:10.5px; color:var(--muted); font-family:"JetBrains Mono",Consolas,monospace; }
/* mockup controls live OUTSIDE the tab frame; the frame is the app's real tab area at 1:1 */
.ctl { width:1600px; display:flex; align-items:center; gap:8px; padding:8px 0; font-size:12px; color:var(--muted); }
.btn { border:1px solid var(--line2); background:#fff; color:var(--text2); border-radius:6px; padding:3px 9px;
  cursor:pointer; font:inherit; font-size:12px; }
.btn.on { color:var(--text); border-color:var(--text2); font-weight:600; }
.btn:focus-visible { outline:2px solid var(--text2); outline-offset:1px; }
#tab { width:1600px; height:690px; background:var(--bg); outline:1px dashed #9AA3B0; position:relative; overflow:hidden; }
.war { padding:12px 24px; display:flex; flex-direction:column; gap:6px; }
.panel { background:var(--card); border:1px solid var(--line); border-radius:8px; }
.answer { display:grid; grid-template-columns:1fr 360px; column-gap:18px; padding:6px 14px 7px; }
.answer .a1 { font-weight:600; }
.answer .meta { text-align:right; min-width:0; }
.meta div { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.main { display:flex; gap:12px; align-items:stretch; }
.mapp, .ladp { padding:3px; }
svg { display:block; }
#rail { width:322px; display:flex; flex-direction:column; gap:5px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:3px 10px 4px; }
.card.first { border-color:var(--text2); }
.card .hd { display:flex; align-items:baseline; gap:5px; white-space:nowrap; overflow:hidden; }
.card .hd .rk { margin-left:auto; font-size:10.5px; }
.card .ln { font-size:11.5px; line-height:13.5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.slot { margin-top:1px; font-size:10.5px; line-height:12px; color:var(--muted); border:1px dashed var(--line2);
  border-radius:3px; padding:0 5px; font-style:italic; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.st { font-size:10px; font-weight:700; letter-spacing:.04em; }
.chip { font-size:10px; font-weight:700; letter-spacing:.05em; border:1px solid var(--text); color:var(--text);
  border-radius:3px; padding:0 4px; }
.park { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:4px 10px 5px; flex:1; min-height:0; }
.park .ln { font-size:11.5px; line-height:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
#legend { display:flex; flex-wrap:nowrap; gap:0 14px; align-items:center; color:var(--text2); padding:0 4px; white-space:nowrap; }
#legend span { display:inline-flex; align-items:center; gap:5px; }
#prov { padding:0 4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.below { width:1600px; padding:6px 0; font-size:12px; color:var(--muted); }
</style>
</head>
<body>
<div style="padding:0 12px">
<div class="ctl">
  <b style="color:var(--text)">Mockup controls</b> (not part of the tab):
  <span id="idxSeg" style="display:flex;gap:3px"></span>
  <span id="viewSeg" style="display:flex;gap:3px">
    <button class="btn" data-v="live">Live read at 13:36</button>
    <button class="btn" data-v="close">After close</button>
  </span>
  <span>· real data 2026-09-23 · light only · the dashed frame below is the app's tab area, 1600×690, drawn at 1:1</span>
</div>
<div id="tab">
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
</div>
<div class="below" id="below"></div>
</div>

<script>
const D = /*DATA*/null;
const OPEN = 555, CLOSE = 930, SPAN = CLOSE - OPEN, NB = 75, CW = 12;
const GL = 44, PW = NB * CW, LGW = 44, MAPW = GL + PW + LGW, LADW = 206, PT = 6, NEAR_N = 6;
const PLOT_MAX = 450;                      // 15 rows x 30 px: the most the 690 px tab area allows
const S = { idx: 'NIFTY', view: 'live', cursor: null, hover: null };
let G = null, META = '';

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

/* ── The model: geometry only. Fronts, states, ranks, the first stamp and the dwells come from the server. ── */
function model() {
  const d = D[S.idx], v = d.views[S.view], endM = mm(v.end), T = d.t.map(mm);
  let last = -1; T.forEach((m, i) => { if (m <= endM) last = i; });
  const at = new Map(); for (let i = 0; i <= last; i++) at.set(T[i], i);
  const step = d.step, atm = d.spot.map(s => s == null ? null : Math.round(s / step) * step);
  let aLo = Infinity, aHi = -Infinity;
  for (let i = 0; i <= last; i++) if (atm[i] != null) { aLo = Math.min(aLo, atm[i]); aHi = Math.max(aHi, atm[i]); }
  // THE WINDOW: every strike within ±6 of the ATM at ANY minute so far. Rows are only ever added at an edge.
  const hi = aHi + NEAR_N * step, lo = aLo - NEAR_N * step, rows = [];
  for (let k = hi; k >= lo - 1e-6; k -= step) rows.push(Math.round(k * 100) / 100);
  // 12 px lanes when there are 15 rows or fewer (30 px a strike: 12 CE + 1 strike line + 12 PE + 5 gap);
  // more rows than that thin the lanes so the plot never passes PLOT_MAX.
  // the event row stacks its labels; each label row past four comes out of the plot budget
  const evx = []; (v.fronts || []).forEach(f => { evx.push(mm(f.peak_at)); if (f.unwind_at) evx.push(mm(f.unwind_at)); });
  const evRows = stackRows(evx.map(m => xOf(m) + 1.2)), budget = PLOT_MAX - Math.max(0, evRows - 4) * 10;
  const P = rows.length <= 15 && budget >= 450 ? 30 : Math.max(12, Math.floor(budget / rows.length));
  const H = P === 30 ? 12 : Math.max(4, Math.floor((P - 5) / 2));
  const yP = p => PT + (hi - p) / step * P + P / 2, plotH = rows.length * P;
  const key = k => String(Math.round(k));
  const ser = (k, s) => (d.k[key(k)] || [null, null])[s];
  const oiS = (k, s) => (d.oi[key(k)] || [null, null])[s];
  const near = (k, i) => atm[i] != null && Math.abs(k - atm[i]) <= NEAR_N * step + 1e-6;
  const F = {};
  (v.fronts || []).forEach(f => {
    const s = f.side === 'CE' ? 0 : 1;
    F[key(f.k) + s] = { ...f, s, rank: v.fronts.filter(x => x.side === f.side).indexOf(f) + 1 };
  });
  const nine = new Set((v.near || []).map(key));
  // Rank is weight: the four fronts own the ink, the rest of §1d's nine half, outside the nine faint.
  const wt = (k, s) => F[key(k) + s] ? 1 : nine.has(key(k)) ? 0.5 : 0.2;
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
  return { d, v, endM, T, last, at, atm, step, hi, lo, rows, P, H, yP, plotH, key, ser, oiS, near, vmax, st, F, nine, wt };
}
const LW = 31;
function stackRows(xs) {  // first-free-row placement: a label never overlaps another
  const lanes = []; for (const x of [...xs].sort((a, b) => a - b)) { let r = 0; while (r < lanes.length && lanes[r] > x - LW / 2) r++; if (r === lanes.length) lanes.push(0); lanes[r] = x + LW / 2; }
  return lanes.length;
}
const alphaOf = (g, x) => x <= 0 || g.vmax <= 0 ? 0 : 0.1 + 0.8 * Math.sqrt(Math.min(1, x / g.vmax));
const laneY = (g, k, s) => s === 0 ? g.yP(k) - 0.5 - g.H : g.yP(k) + 0.5;
const valAt = (arr, i) => { if (!arr) return null; for (let j = i; j >= 0; j--) if (arr[j] != null) return [arr[j], j]; return null; };

/* ── The map ── */
function drawMap() {
  const g = G, o = [DEFS], xEnd = xOf(g.endM + 1), H = g.H;
  // §1d's nine, shaded in the gutter exactly as the ladder shades them
  for (const k of g.rows) if (g.nine.has(g.key(k))) o.push(R(0, g.yP(k) - g.P / 2, GL - 2, g.P, 'fill:var(--ink);fill-opacity:.06'));
  for (const k of g.rows) for (const s of [0, 1]) o.push(R(xOf(OPEN), laneY(g, k, s), xEnd - xOf(OPEN), H, `fill:var(--ink);fill-opacity:${(0.045 * (g.wt(k, s) > 0.3 ? 1 : 0.6)).toFixed(3)}`));
  const cells = [], runs = [], rings = [];
  for (const k of g.rows) for (const s of [0, 1]) {
    const a = g.ser(k, s), y = laneY(g, k, s), w0 = g.wt(k, s); let run = null, ring = null;
    const rm = []; let hiw = null;
    if (a) for (let i = 0; i <= g.last; i++) { if (a[i] != null && (hiw == null || a[i] > hiw)) hiw = a[i]; rm.push(hiw); }
    const flush = () => { if (run) runs.push({ ...run, y, w0 }); run = null; };
    const flushRing = () => { if (ring) rings.push({ ...ring, y, s, w0 }); ring = null; };
    for (let b = 0; b < NB; b++) {
      const m0 = OPEN + 5 * b; if (m0 > g.endM) break;
      const m1 = Math.min(m0 + 4, g.endM), x0 = xOf(m0), x1 = xOf(m1 + 1);
      let i = -1; for (let m = m1; m >= m0; m--) if (g.at.has(m)) { i = g.at.get(m); break; }
      let type = null, val = null;
      if (i < 0) type = 'nc';
      else if (!g.near(k, i)) type = 'far';
      else if (!a || a[i] == null) type = 'nc';
      else val = a[i];
      if (type) { flushRing(); if (run && run.type === type) run.x1 = x1; else { flush(); run = { type, x0, x1 }; } continue; }
      flush();
      const w = (g.d.src[i] ? 0.45 : 1) * w0, high = rm[i];
      if (val > 0) {
        const h = Math.max(1, H * (high > 0 ? val / high : 1));
        cells.push(R(x0, s === 0 ? y + H - h : y, x1 - x0, h, `fill:${HUE(s)};fill-opacity:${(alphaOf(g, val) * w).toFixed(3)}`));
      } else if (val < 0) cells.push(R(x0, y, x1 - x0, H, `fill:url(#h${s});opacity:${((0.3 + 0.6 * Math.min(1, -val / (g.vmax || 1))) * w).toFixed(3)}`));
      if (high > 0 && val < high) {
        const gone = Math.min(1, (high - Math.max(0, val)) / high);
        if (ring) { ring.x1 = x1; ring.hi = Math.max(ring.hi, high); ring.gone = Math.max(ring.gone, gone); } else ring = { x0, x1, hi: high, gone };
      } else flushRing();
    }
    flush(); flushRing();
  }
  o.push(...cells);
  for (const r of runs) o.push(r.type === 'far'
    ? R(r.x0, r.y, r.x1 - r.x0, H, `fill:url(#hn);opacity:${r.w0 > 0.3 ? 1 : 0.55}`)
    : R(r.x0 + 0.5, r.y + 0.5, r.x1 - r.x0 - 1, H - 1, `fill:none;stroke:var(--caution);stroke-opacity:${(0.55 * Math.max(r.w0, 0.35)).toFixed(2)};stroke-dasharray:2 3;stroke-width:1`));
  if (S.view === 'close' && g.d.rebase) for (const k of g.rows) for (const s of [0, 1])
    o.push(R(xEnd + 0.5, laneY(g, k, s) + 0.5, xOf(CLOSE) - xEnd - 1, H - 1, 'fill:none;stroke:var(--caution);stroke-opacity:.5;stroke-dasharray:2 3;stroke-width:1'));
  for (const r of rings) { const op = alphaOf(g, r.hi) * r.gone * r.w0; if (op > 0.02) o.push(R(r.x0 + 0.5, r.y + 0.5, r.x1 - r.x0 - 1, H - 1, `fill:none;stroke:${HUE(r.s)};stroke-opacity:${op.toFixed(3)};stroke-width:1`)); }
  // named levels (brass); codes in the level gutter
  const tags = [];
  for (const l of g.d.levels) {
    const y = g.yP(l.px); if (y < PT || y > PT + g.plotH) continue;
    o.push(LN(GL, y, GL + PW, y, 'stroke:var(--brass);stroke-opacity:.55;stroke-dasharray:3 4;stroke-width:1'));
    tags.push({ y, s: l.kind, st: 'fill:var(--brass);font-size:9.5px' });
  }
  // DWELL BOXES: where price parked at a known level (dwell.py), and for how long
  for (const w of g.v.dwells || []) {
    const x0 = xOf(mm(w.t0)), x1 = xOf(mm(w.t_end) + 1), y0 = g.yP(w.px + w.band), y1 = g.yP(w.px - w.band);
    const mins = mm(w.t_end) - mm(w.t0) + 1;
    o.push(R(x0, y0, x1 - x0, y1 - y0, `fill:var(--brass);fill-opacity:.12;stroke:var(--brass);stroke-width:1.3;${w.active ? 'stroke-dasharray:3 2' : ''}`, 'rx="2"'));
    o.push(TX((x0 + x1) / 2, y0 - 3, `${mins}m`, 'fill:var(--brass);font-size:9.5px;font-weight:700', 'middle', 'num'));
  }
  // spot, broken on holes
  let seg = [], pts = [];
  for (let i = 0; i <= g.last; i++) {
    const sp = g.d.spot[i]; if (i > 0 && g.T[i] - g.T[i - 1] > 5) { if (seg.length > 1) pts.push(seg); seg = []; }
    if (sp == null) { if (seg.length > 1) pts.push(seg); seg = []; continue; }
    seg.push(`${(xOf(g.T[i]) + 1.2).toFixed(1)},${g.yP(sp).toFixed(1)}`);
  }
  if (seg.length > 1) pts.push(seg);
  for (const p of pts) o.push(`<polyline points="${p.join(' ')}" style="fill:none;stroke:var(--ink);stroke-width:1.7;stroke-opacity:.9;stroke-linejoin:round"/>`);
  const spNow = g.d.spot[g.last];
  if (spNow != null) tags.push({ y: g.yP(spNow), s: '◂' + inr(spNow, 0), st: 'fill:var(--ink);font-size:9.5px;font-weight:600' });
  tags.sort((a, b) => a.y - b.y); let lastY = -1e9;
  for (const t of tags) { const y = Math.max(t.y + 3.3, lastY + 10.5); lastY = y; o.push(TX(GL + PW + 4, y, t.s, t.st, 'start', 'num')); }
  // the fronts: ink tick at the high (minute-exact), dashed ink tick where §1d first read it unwinding
  for (const id in g.F) {
    const f = g.F[id], y = laneY(g, f.k, f.s), xp = xOf(mm(f.peak_at)) + 1.2;
    o.push(LN(xp, y - 1.5, xp, y + H + 1.5, 'stroke:var(--ink);stroke-width:2'));
    if (f.unwind_at) { const xu = xOf(mm(f.unwind_at)) + 1.2; o.push(LN(xu, y - 1, xu, y + H + 1, 'stroke:var(--ink);stroke-width:1.3;stroke-dasharray:2 1.5')); }
  }
  // strike labels: fronts in ink with their side mark; the nine in text2; outside the nine faint
  const atmNow = g.atm[g.last];
  for (const k of g.rows) {
    const fc = g.F[g.key(k) + 0], fp = g.F[g.key(k) + 1], inNine = g.nine.has(g.key(k));
    const st = Math.abs(k - atmNow) < 1e-6 ? 'fill:var(--brass);font-weight:700' : (fc || fp) ? 'fill:var(--text);font-weight:700' : inNine ? 'fill:var(--text2)' : 'fill:var(--muted);fill-opacity:.6';
    o.push(TX(GL - 6, g.yP(k) + 3.4, inr(k, 0), st + ';font-size:10px', 'end', 'num'));
    if (fc) o.push(R(1, laneY(g, k, 0), 3, H, 'fill:var(--coral)'));
    if (fp) o.push(R(1, laneY(g, k, 1), 3, H, 'fill:var(--teal)'));
  }
  // time axis
  const ay = PT + g.plotH;
  o.push(LN(GL, ay + 0.5, GL + PW, ay + 0.5, 'stroke:var(--line2)'));
  const special = [g.endM + 1]; if (S.cursor != null) special.push(S.cursor);
  for (const m of [OPEN, 600, 660, 720, 780, 840, 900, CLOSE]) {
    o.push(LN(xOf(m), ay, xOf(m), ay + 4, 'stroke:var(--line2)'));
    if (special.every(s => Math.abs(xOf(s) - xOf(m)) > 30)) o.push(TX(xOf(m), ay + 14, hhmm(m), 'fill:var(--muted);font-size:10px', 'middle', 'num'));
  }
  o.push(LN(xEnd, PT, xEnd, ay + 4, 'stroke:var(--ink);stroke-opacity:.5;stroke-width:1'));
  o.push(TX(xEnd, ay + 14, S.view === 'live' ? hhmm(g.endM) + ' now' : hhmm(g.endM), 'fill:var(--text);font-size:10px;font-weight:700', 'middle', 'num'));
  // EVENT ROW: ◆ stopped adding (its high), ◇ §1d first read unwinding. Labels stack into the first free
  // row at their own x, so three stops in six minutes never print on top of each other.
  const ey = ay + 23, evs = [];
  for (const id in g.F) {
    const f = g.F[id];
    evs.push({ x: xOf(mm(f.peak_at)) + 1.2, t: f.peak_at, s: f.s, kind: 'stop' });
    if (f.unwind_at) evs.push({ x: xOf(mm(f.unwind_at)) + 1.2, t: f.unwind_at, s: f.s, kind: 'unw' });
  }
  evs.sort((a, b) => a.x - b.x);
  const lanesR = [];
  for (const e of evs) {
    let r = 0; while (r < lanesR.length && lanesR[r] > e.x - LW / 2) r++;
    if (r === lanesR.length) lanesR.push(-1e9);
    lanesR[r] = e.x + LW / 2; e.row = r;
  }
  for (const e of evs) {
    const dm = `M${e.x} ${ey - 5}L${e.x + 4} ${ey}L${e.x} ${ey + 5}L${e.x - 4} ${ey}Z`;
    const ly = ey + 15 + e.row * 10;
    if (e.row > 0) o.push(LN(e.x, ey + 5, e.x, ly - 8, `stroke:${HUE(e.s)};stroke-opacity:.45;stroke-width:1`));
    o.push(e.kind === 'stop' ? `<path d="${dm}" style="fill:${HUE(e.s)}"/>` : `<path d="${dm}" style="fill:var(--card);stroke:${HUE(e.s)};stroke-width:1.2"/>`);
    o.push(TX(e.x, ly, e.t, `fill:${HUE(e.s)};font-size:9.5px;${e.kind === 'stop' ? 'font-weight:700' : ''}`, 'middle', 'num'));
  }
  o.push('<g id="mapov"></g>');
  const svgH = ey + 15 + Math.max(1, lanesR.length) * 10 - 6;
  G.svgH = svgH;
  const svg = document.getElementById('map');
  svg.setAttribute('width', MAPW); svg.setAttribute('height', svgH); svg.setAttribute('viewBox', `0 0 ${MAPW} ${svgH}`);
  svg.setAttribute('aria-label', `${g.d.idx} open-interest change since the open by strike and time, within six strikes of the ATM`);
  svg.innerHTML = o.join('');
}

function dwellAt(m) { return (G.v.dwells || []).find(w => m >= mm(w.t0) && m <= mm(w.t_end)); }
function dwellLine(w) {
  const lg = (w.legs || []).filter(x => x.dk !== 0);
  const top = lg[0] ? `<b class="${lg[0].side === 'CE' ? 'ce' : 'pe'}">${lg[0].side} ${inr(lg[0].k, 0)}</b> <b class="num">${sL(lg[0].dk)}</b>` : 'no change in the near legs';
  const mins = mm(w.t_end) - mm(w.t0) + 1;
  return `${w.kind === 'ROUND' ? '' : w.kind + ' '}<b class="num">${inr(w.px, 0)}</b> <span class="num">${w.t0}–${w.active ? 'now' : w.t_exit}</span> <b class="num">${mins}m</b>${w.active ? ' holding' : ' → ' + w.exit_to.toLowerCase()} · ${top}`;
}

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

/* ── The ladder: self-contained (the BOARD reuses it). The book NOW, CE | strike | PE. ── */
function drawLadder() {
  const g = G, o = [DEFS], svgH = Math.max(G.svgH, PT + G.plotH + 58), cx0 = 76, cx1 = 130, BW = 72, bh = Math.min(14, g.P - 8);
  const iEnd = g.last, iCur = S.cursor != null ? (() => { let j = -1; g.T.forEach((m, i) => { if (m <= S.cursor && i <= g.last) j = i; }); return j; })() : -1;
  const pk = g.v.peak_abs;
  let amax = 0;
  for (const k of g.rows) for (const s of [0, 1]) {
    const n = valAt(g.oiS(k, s), iEnd), p = (pk[g.key(k)] || [])[s];
    amax = Math.max(amax, n ? n[0] : 0, p || 0);
  }
  const len = x => amax > 0 ? x / amax * BW : 0;
  for (const k of g.rows) if (g.nine.has(g.key(k))) o.push(R(cx0 + 2, g.yP(k) - g.P / 2, cx1 - cx0 - 4, g.P, 'fill:var(--ink);fill-opacity:.06'));
  const atmNow = g.atm[g.last], sp = g.d.spot[g.last];
  for (const k of g.rows) {
    const y = g.yP(k), inNine = g.nine.has(g.key(k));
    for (const s of [0, 1]) {
      const n = valAt(g.oiS(k, s), iEnd), p = (pk[g.key(k)] || [])[s], f = g.F[g.key(k) + s];
      const dir = s === 0 ? -1 : 1, base = s === 0 ? cx0 : cx1, op = f ? 0.75 : inNine ? 0.45 : 0.2;
      if (!n) { o.push(R(s === 0 ? base - 18 : base, y - bh / 2, 18, bh, 'fill:none;stroke:var(--caution);stroke-dasharray:2 3;stroke-opacity:.45')); continue; }
      const w = len(n[0]);
      o.push(R(s === 0 ? base - w : base, y - bh / 2, w, bh, `fill:${HUE(s)};fill-opacity:${op}`));
      if (p) { const xp = base + dir * len(p); o.push(LN(xp, y - bh / 2 - 2, xp, y + bh / 2 + 2, `stroke:var(--ink);stroke-width:1.5;stroke-opacity:${f || inNine ? 1 : 0.35}`)); }
      if (iCur >= 0) {
        const c = valAt(g.oiS(k, s), iCur);
        if (c) { const wc = len(c[0]); o.push(R(s === 0 ? base - wc : base, y - bh / 2 + 0.5, wc, bh - 1, 'fill:none;stroke:var(--brass);stroke-width:1.1;stroke-dasharray:2.5 1.5')); }
      }
      if (f) {
        const far = Math.max(w, p ? len(p) : 0) + 3;
        o.push(R(s === 0 ? base - far : base - 1, y - bh / 2 - 3, far + 1, bh + 6, 'fill:none;stroke:var(--text);stroke-width:1.2'));
        o.push(TX(s === 0 ? base - far - 4 : base + far + 4, y + 3.5, String(f.rank), `fill:${HUE(s)};font-size:10.5px;font-weight:700`, s === 0 ? 'end' : 'start', 'num'));
      }
    }
    const isF = g.F[g.key(k) + 0] || g.F[g.key(k) + 1];
    const st = Math.abs(k - atmNow) < 1e-6 ? 'fill:var(--brass);font-weight:700' : isF ? 'fill:var(--text);font-weight:700' : inNine ? 'fill:var(--text2)' : 'fill:var(--muted);fill-opacity:.6';
    o.push(TX((cx0 + cx1) / 2, y + 3.4, inr(k, 0), st + ';font-size:10px', 'middle', 'num'));
  }
  // spot across the book: CE bars below the line and PE bars above it are in the money
  if (sp != null) o.push(LN(0, g.yP(sp), LADW, g.yP(sp), 'stroke:var(--ink);stroke-width:1;stroke-dasharray:4 3;stroke-opacity:.6'));
  const ay = PT + g.plotH;
  o.push(TX(cx0 - 2, ay + 14, 'CE', 'fill:var(--coral);font-size:10px;font-weight:700', 'end'));
  o.push(TX(cx1 + 2, ay + 14, 'PE', 'fill:var(--teal);font-size:10px;font-weight:700', 'start'));
  o.push(TX((cx0 + cx1) / 2, ay + 14, 'OI now', 'fill:var(--muted);font-size:9.5px', 'middle'));
  o.push(TX((cx0 + cx1) / 2, ay + 27, `full bar ${L(amax)} · │ = session high`, 'fill:var(--muted);font-size:9.5px', 'middle', 'num'));
  o.push(TX((cx0 + cx1) / 2, ay + 40, `box = top two by peak OI · shade = §1d's 9`, 'fill:var(--muted);font-size:9.5px', 'middle'));
  o.push(TX((cx0 + cx1) / 2, ay + 53, iCur >= 0 ? `dashed = OI at ${hhmm(S.cursor)} · - - = spot` : '- - - = spot', `fill:${iCur >= 0 ? 'var(--brass)' : 'var(--muted)'};font-size:9.5px`, 'middle', 'num'));
  const svg = document.getElementById('lad');
  svg.setAttribute('width', LADW); svg.setAttribute('height', svgH); svg.setAttribute('viewBox', `0 0 ${LADW} ${svgH}`);
  svg.setAttribute('aria-label', `${g.d.idx} open interest now, calls left and puts right, the top two per side boxed`);
  svg.innerHTML = o.join('');
}

/* ── The rail ── */
function drawRail() {
  const g = G, el = document.getElementById('rail'), v = g.v, res = resolution(g.d), fst = v.first;
  if (!v.fronts) { el.innerHTML = `<div class="card s12 amber">Near-ATM fronts could not be read: ${v.fronts_why}. This is not "no fronts"; nothing was checked.</div>`; return; }
  const fs = [...v.fronts].sort((a, b) => (a.state === 'BUILDING') - (b.state === 'BUILDING') || (a.peak_at < b.peak_at ? -1 : 1));
  const smax = Math.max(...fs.map(f => f.peak), 1), W = 300, SH = 12;
  const cards = fs.map(f => {
    const s = f.side === 'CE' ? 0 : 1, a = g.ser(f.k, s), rank = g.F[g.key(f.k) + s].rank;
    // the chip marks the SAME stop the stamp names; a front that re-built past it is a later stop
    const isFirst = fst && fst.side === f.side && fst.k === f.k && fst.peak_at === f.peak_at;
    const X = m => (m - OPEN) / SPAN * W, Y = x => SH - Math.max(0, x) / smax * (SH - 2);
    let area = '', crest = '', run = -Infinity, seg = [], cseg = []; const segs = [], csegs = [];
    for (let i = 0; i <= g.last; i++) {
      const x = a ? a[i] : null, m = g.T[i];
      if (x == null || (i > 0 && m - g.T[i - 1] > 5)) { if (seg.length) { segs.push(seg); csegs.push(cseg); } seg = []; cseg = []; if (x == null) continue; }
      run = Math.max(run, x); seg.push([X(m), Y(x)]); cseg.push([X(m), Y(run)]);
    }
    if (seg.length) { segs.push(seg); csegs.push(cseg); }
    for (const sg of segs) area += `<path d="M${sg[0][0].toFixed(1)},${SH}${sg.map(p => `L${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('')}L${sg[sg.length - 1][0].toFixed(1)},${SH}Z" style="fill:${HUE(s)};fill-opacity:.4"/>`;
    for (const sg of csegs) crest += `<path d="M${sg.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join('L')}" style="fill:none;stroke:${HUE(s)};stroke-width:1"/>`;
    const xp = X(mm(f.peak_at)) + 0.4, xu = f.unwind_at ? X(mm(f.unwind_at)) + 0.4 : null, xn = X(g.endM + 1);
    const glyph = f.state === 'BUILDING' ? `<rect x="0" y="0" width="9" height="9" style="fill:${HUE(s)}"/>`
      : f.state === 'STALLED' ? `<rect x="0.5" y="0.5" width="8" height="8" style="fill:${HUE(s)};fill-opacity:.35;stroke:${HUE(s)}"/>`
      : `<rect x="0.5" y="0.5" width="8" height="8" style="fill:url(#h${s});stroke:${HUE(s)}"/>`;
    const off = f.peak - f.chg;
    const line1 = f.state === 'BUILDING' && !f.under
      ? `adding · high so far <b class="num">${f.peak_at}</b> @ spot <span class="num">${inr(f.peak_spot, 0)}</span>`
      : `stopped adding <b class="num">${f.peak_at}</b> @ spot <span class="num">${inr(f.peak_spot, 0)}</span>`;
    const line1b = f.unwind_at ? `→ §1d: unwinding <b class="num">${f.unwind_at}</b> @ <span class="num">${inr(f.unwind_spot, 0)}</span>` + (f.under ? ' · adding again now' : '')
      : f.state === 'BUILDING' ? '' : '→ §1d: not read unwinding yet';
    const line2 = `now <span class="num">${sL(f.chg)}</span> · ` + (off > 0 ? `<b class="num">${L(off)}</b> under its <span class="num">${sL(f.peak)}</span> high` : 'at its high') + ` <span class="tag">[M] ±${res}m</span>`;
    return `<div class="card${isFirst ? ' first' : ''}">
      <div class="hd"><svg width="9" height="9" style="align-self:center">${DEFS}${glyph}</svg>
        <b class="s13 ${s === 0 ? 'ce' : 'pe'}">${f.side}</b><b class="s13 num">${inr(f.k, 0)}</b>
        <span class="st ${s === 0 ? 'ce' : 'pe'}" title="§1d state: ${f.state}">${f.under ? 'ADDING AGAIN' : f.state}</span>${isFirst ? `<span class="chip" title="the first front §1d named giving back today; stamped ${fst.named_at}, never re-decided">1ST</span>` : ''}
        <span class="rk s11 muted num" title="rank basis: session-PEAK absolute OI (server), not OI at the minute">#${rank} peak OI ${f.oi != null ? L(f.oi) : 'n/a'}</span></div>
      <svg width="${W}" height="${SH + 2}" style="margin:2px 0 1px">${DEFS}
        ${R(0, 0, xn, SH, 'fill:var(--ink);fill-opacity:.04')}${area}${crest}
        ${LN(xp, 0, xp, SH, 'stroke:var(--ink);stroke-width:2')}
        ${xu != null ? LN(xu, 0, xu, SH, 'stroke:var(--ink);stroke-width:1.2;stroke-dasharray:2 1.5') : ''}
        ${LN(xn, 0, xn, SH, 'stroke:var(--ink);stroke-opacity:.4')}</svg>
      <div class="ln t2">${line1}</div>${line1b ? `<div class="ln t2">${line1b}</div>` : ''}<div class="ln t2">${line2}</div>
      <div class="slot" title="Her §1d addendum (forced = giving back while price runs at the strike; released = while price moves away) is being drafted for her approval. Not pre-registered, so not computed.">forced / released: pending §1d addendum</div></div>`;
  }).join('');
  const dw = [...(v.dwells || [])].reverse();
  const park = `<div class="park"><div class="s11 muted" style="letter-spacing:.06em;font-weight:700">PARKED <span style="font-weight:400;letter-spacing:0">· dwell.py · biggest OI change within 2 strikes [M]</span></div>` +
    (dw.length ? dw.slice(0, 2).map(w => `<div class="ln t2">${dwellLine(w)}</div>`).join('') + (dw.length > 2 ? `<div class="ln muted">${dw.length - 2} earlier, boxed on the map (hover for the numbers)</div>` : '')
      : `<div class="ln muted">checked: price has not parked at a known level yet today</div>`) + `</div>`;
  el.innerHTML = cards + park;
}

function resolution(d) { const gp = d.cadence.gaps; let best = 1, n = -1; for (const k in gp) if (gp[k] > n) { n = gp[k]; best = +k; } return best; }

/* ── The sentences ── */
function drawText() {
  const g = G, d = g.d, v = g.v, res = resolution(d), fst = v.first;
  const a1 = document.getElementById('ans1'), a2 = document.getElementById('ans2');
  const nm = (side, k) => `<span class="${side === 'CE' ? 'ce' : 'pe'}">${side} ${inr(k, 0)}</span>`;
  // Line 1: THE FIRST STOP, stamped once. Never re-decided from the current minute's state.
  if (!fst) a1.innerHTML = `No front has been read giving back yet today — §1d has named no first stop.`;
  else {
    const gone = fst.hi - fst.now;
    const tail = fst.hi > fst.peak ? ` — a <span class="num">${sL(fst.peak)}</span> build, re-built to <span class="num">${sL(fst.hi)}</span> (${fst.hi_at}), now <span class="num">${sL(fst.now)}</span>.`
      : fst.now < 0 ? ` — all <span class="num">${L(fst.hi)}</span> gone, now <span class="num">${L(-fst.now)}</span> below its open.`
      : ` — <span class="num">${L(gone)}</span> of its <span class="num">${L(fst.hi)}</span> build gone.`;
    a1.innerHTML = `First stop today: ${nm(fst.side, fst.k)} stopped adding <span class="num">${fst.peak_at}</span> @ <span class="num">${inr(fst.peak_spot, 0)}</span>, named by §1d <span class="num">${fst.named_at}</span>${tail} <span class="tag">[M] stamped once</span>`;
  }
  // Line 2: the latest stop and the count, in the rule's own words. Stalled is not "off".
  if (!v.fronts) a2.innerHTML = `<span class="amber">Near-ATM fronts could not be read — ${v.fronts_why}.</span>`;
  else {
    const stops = v.fronts.filter(f => f.state !== 'BUILDING' || f.under).sort((x, y) => (x.peak_at < y.peak_at ? 1 : -1));
    const lat = stops[0];
    const cnt = st => v.fronts.filter(f => f.state === st).length;
    const again = v.fronts.filter(f => f.under).length;
    a2.innerHTML = (lat ? `Latest stop: ${nm(lat.side, lat.k)} <span class="num">${lat.peak_at}</span> @ <span class="num">${inr(lat.peak_spot, 0)}</span>, ${lat.state === 'UNWINDING' ? 'unwinding since ' + lat.unwind_at : lat.state === 'STALLED' ? 'stalled' : 'adding again under its high'}. ` : '') +
      `Top four now: ${cnt('UNWINDING')} unwinding, ${cnt('STALLED')} stalled, ${cnt('BUILDING') - again} adding${again ? `, ${again} adding again under its high` : ''}.`;
  }
  const sp = d.spot[g.last];
  META = `<div><b class="s13" style="color:var(--text)">${d.idx}</b> · <span class="num">${S.view === 'live' ? hhmm(g.endM) + ' live read' : 'after close, as of ' + hhmm(g.endM)}</span></div>` +
    `<div>spot <span class="num">${inr(sp)}</span> · ATM <span class="num brass">${inr(g.atm[g.last], 0)}</span> · rows <span class="num">${inr(g.lo, 0)}–${inr(g.hi, 0)}</span></div>` +
    `<div>±6 of every ATM · shaded = §1d's nine · hover a row · click to pin</div>`;
  const sw = (inner, w = 22) => `<svg width="${w}" height="10">${DEFS}${inner}</svg>`;
  document.getElementById('legend').innerHTML = [
    `<span>${sw(R(0, 1, 10, 8, 'fill:var(--coral);fill-opacity:.9') + R(11, 1, 10, 8, 'fill:var(--teal);fill-opacity:.35'))}added since the open (√ shade, full = <b class="num">${L(g.vmax)}</b>)</span>`,
    `<span>${sw(R(0.5, 0.5, 21, 9, 'fill:none;stroke:var(--coral);stroke-opacity:.9') + R(1, 6.5, 20, 3, 'fill:var(--coral);fill-opacity:.5'))}ring = its high, height = share still held</span>`,
    `<span>${sw(R(0, 1, 22, 8, 'fill:url(#h0)'))}below its open</span>`,
    `<span>${sw(LN(6, 0, 6, 10, 'stroke:var(--ink);stroke-width:2') + LN(15, 0, 15, 10, 'stroke:var(--ink);stroke-width:1.3;stroke-dasharray:2 1.5'))}stopped · §1d unwinding (±${res}m)</span>`,
    `<span>${sw(R(1, 1, 20, 8, 'fill:var(--brass);fill-opacity:.12;stroke:var(--brass);stroke-width:1.2'))}parked (dwell)</span>`,
    `<span>${sw(R(0, 1, 22, 8, 'fill:url(#hn)'))}outside ±6 then</span>`,
    `<span>${sw(R(0.5, 1.5, 21, 7, 'fill:none;stroke:var(--caution);stroke-dasharray:2 3'))}could not check</span>`,
    `<span>${sw(R(0, 1, 10, 8, 'fill:var(--coral);fill-opacity:.9') + R(12, 1, 10, 8, 'fill:var(--coral);fill-opacity:.2'))}faint = outside §1d's nine</span>`,
  ].join('');
  const n = g.last + 1, rebuilt = d.src.slice(0, n).filter(Boolean).length;
  let holes = 0; for (let i = 1; i < n; i++) if (g.T[i] - g.T[i - 1] > 5) holes++;
  let nc = 0;
  for (const k of g.rows) for (const s of [0, 1]) { const a = g.ser(k, s); for (let i = 0; i < n; i++) { if (!g.near(k, i)) continue; if (!a || a[i] == null) nc++; } }
  const c = d.cadence, pct = Math.round(100 * c.changed / c.trans), fs = d.feed_start;
  let p = `Record ${d.t[0]}–${hhmm(g.endM)} · ${rebuilt} rebuilt min (lighter) · ${holes ? holes + ' holes' : 'no holes'} · OI moved on ${pct}% of minutes, mostly every ${res}m → stamps ±${res}m [M] · feed ${inr(fs[0], 0)}–${inr(fs[1], 0)} from ${fs[2]}` +
    (nc ? `, ${nc} near-ATM strike-min not carried (amber)` : '') + ` · dwell boxes from the war map's log, opened 5 min before the DWELL stamp`;
  if (S.view === 'close' && d.rebase) p += ` · <span class="amber">drawn to ${hhmm(g.endM)}: the ${d.rebase.at} restart re-read the open baseline (${d.rebase.n}/${d.rebase.legs} legs, ≤${L(d.rebase.max)})</span>`;
  document.getElementById('prov').innerHTML = p;
  readout(null);
}

function readout(h) {
  const g = G, el = document.getElementById('meta');
  if (!h) { el.innerHTML = META; return; }
  const { k, m } = h; let i = -1; g.T.forEach((t, j) => { if (t <= m && j <= g.last) i = j; });
  if (i < 0) { el.textContent = `${inr(k, 0)} · ${hhmm(m)}: no record at or before this minute.`; return; }
  const part = s => {
    const a = g.ser(k, s), q = g.st[g.key(k) + s], x = a ? a[i] : null;
    const now = x == null ? (g.near(k, i) ? '<span class="amber">not carried</span>' : '—') : `<span class="num">${sL(x)}</span>`;
    const hi = q.pk != null && q.pk > 0 ? ` (high <span class="num">${sL(q.pk)}</span> at <span class="num">${hhmm(g.T[q.pkI])}</span>)` : '';
    return `<b class="${s === 0 ? 'ce' : 'pe'}">${SIDE(s)}</b> ${now}${hi}`;
  };
  const w = dwellAt(g.T[i]);
  el.innerHTML = `<div><b class="num" style="color:var(--text)">${inr(k, 0)}</b> at <b class="num" style="color:var(--text)">${hhmm(g.T[i])}</b> · spot <span class="num">${inr(g.d.spot[i])}</span> · ${g.near(k, i) ? 'within ±6' : 'outside ±6'} · ${g.nine.has(g.key(k)) ? "in §1d's nine" : "outside the nine"}</div>` +
    `<div class="t2">${part(0)} · ${part(1)} <span class="tag">since open [M]</span></div>` +
    `<div class="t2">${w ? 'parked at ' + dwellLine(w) + ' during it' : 'not parked at a known level at this minute'}</div>`;
}

function render() {
  G = model(); S.hover = null;
  drawMap(); drawMapOverlay(); drawLadder(); drawRail(); drawText();
  document.querySelectorAll('#idxSeg .btn').forEach(b => b.classList.toggle('on', b.dataset.i === S.idx));
  document.querySelectorAll('#viewSeg .btn').forEach(b => b.classList.toggle('on', b.dataset.v === S.view));
  const war = document.getElementById('war');
  document.getElementById('below').innerHTML = `WAR content: <b>${Math.round(war.getBoundingClientRect().height)} px</b> of the 690 px tab area, at 1:1 (rev 1 was 519–523 px of a scaled 900 px stage; today's WarTab ≈ 890 px and scrolls).`;
}

document.getElementById('idxSeg').innerHTML = Object.keys(D).map(i => `<button class="btn" data-i="${i}">${i}</button>`).join('');
document.getElementById('idxSeg').addEventListener('click', e => { const b = e.target.closest('.btn'); if (!b) return; S.idx = b.dataset.i; S.cursor = S.view === 'close' ? 816 : null; render(); });
document.getElementById('viewSeg').addEventListener('click', e => { const b = e.target.closest('.btn'); if (!b) return; S.view = b.dataset.v; S.cursor = S.view === 'close' ? 816 : null; render(); });
const mapEl = document.getElementById('map');
function hit(e) {
  const r = mapEl.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
  if (x < GL || x > GL + PW || y < PT || y > PT + G.plotH) return null;
  const m = Math.min(G.endM, Math.floor(OPEN + (x - GL) / PW * SPAN));
  const k = G.rows[Math.min(G.rows.length - 1, Math.max(0, Math.floor((y - PT) / G.P)))];
  return { k, m };
}
mapEl.addEventListener('mousemove', e => { const h = hit(e); S.hover = h; drawMapOverlay(); readout(h); });
mapEl.addEventListener('mouseleave', () => { S.hover = null; drawMapOverlay(); readout(null); });
mapEl.addEventListener('click', e => { const h = hit(e); if (!h) return; S.cursor = S.cursor === h.m ? null : h.m; drawMapOverlay(); drawLadder(); });
addEventListener('keydown', e => { if (e.key === 'Escape') { S.cursor = null; drawMapOverlay(); drawLadder(); } });
render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
