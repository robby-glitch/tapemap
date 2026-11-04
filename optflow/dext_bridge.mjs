// dext_bridge.mjs -- option order flow from the Dext DESKTOP app into TapeMap (POST /api/dext/candles).
//
// Dext (Electron, backgroundThrottling off) must be started with the debugging port 127.0.0.1:9229 (start-v2.bat does
// it) and needs ONE chart open: its frame is the logged-in place the bridge asks from. Why and how: docs/optflow/README.md.
//   1. LISTEN: every getOrderFlow/v2 and getData response the app loads on its own is forwarded as it arrives.
//   2. ASK (her "Yes, once a minute" and "Build the bridge to follow ATM ±5 on NIFTY and SENSEX by itself", 3 Nov):
//      in market hours, from the live chain: NIFTY and SENSEX ATM ±5 strikes, CE and PE, plus any chart open in Dext.
//      Inner ±3 and open charts every minute, outer ±4..5 every 3rd minute (about 33 requests a minute).
//      First ask of a contract today: from 09:15; after that: the last 15 minutes.
// Conversion is the Chrome extension's own parser (lib/parsers.js orderFlowV2 / dhanOHLC), so TapeMap gets one shape.
// Only closed minutes are sent; TapeMap's door appends only lines that changed. Nothing is stored here.
//     node dext_bridge.mjs          node dext_bridge.mjs --now   (one round now, any hour: the after-close check)
//     node dext_bridge.mjs --now 2026-11-02 [more days]   (one round per past day: 09:15-15:30, every strike its spot touched ±5)
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
// the Chrome extension's own parser (the one conversion TapeMap's Dext record already holds): lives outside tapemap
const PARSERS = "C:/Users/kaam/Desktop/dext extension/dext-decoder/dext-decoder/lib/parsers.js";
const P = createRequire(import.meta.url)(PARSERS);

const DATA = fileURLToPath(new URL("../data", import.meta.url));      // tapemap/optflow -> tapemap/data
const CDP = "http://127.0.0.1:9229/json/version", DOOR = "http://127.0.0.1:8765/api/dext/candles";
const OF = /\/orderflow\/getOrderFlow\/v2/i, OHLC = /ticks\.dhan\.co\/getData/i, ASK_MS = 60000, RECENT_S = 900;
const IDX = [{ name: "NIFTY", exch: "NSE", step: 50 }, { name: "SENSEX", exch: "BSE", step: 100 }];
const INNER = 3, OUTER = 5, NOW_FLAG = process.argv.includes("--now"), TARGETS_FLAG = process.argv.includes("--targets");
const NO_COPY = /^(content-length|host|origin|referer|user-agent|cookie|connection|accept-encoding|sec-|:)/i;
const log = (...a) => console.log(new Date().toTimeString().slice(0, 8), ...a);
const istNow = () => new Date(Date.now() + 19800e3);
const DAYS = NOW_FLAG || TARGETS_FLAG ? process.argv.filter(a => /^\d{4}-\d{2}-\d{2}$/.test(a)) : [];    // --now YYYY-MM-DD ...: past days
let DAY = DAYS.shift();
const today = () => DAY || istNow().toISOString().slice(0, 10);
const dayAt = (h, m) => { const d = DAY ? new Date(`${DAY}T00:00:00Z`) : istNow(); d.setUTCHours(h, m, 0, 0); return Math.floor(d.getTime() / 1000) - 19800; };
const todayOpen = () => dayAt(9, 15);
const inSession = () => { const hm = istNow().toISOString().slice(11, 16); return hm >= "09:15" && hm <= "15:45"; };
const iso = s => new Date(s * 1000).toISOString();      // the app's own START_TIME / END_TIME style: 2026-11-03T03:45:00.000Z

// NIFTY / SENSEX option ids from TapeMap's scrip master: "EXCH|SYM|expiry|strike|CE" -> SEC_ID
// ponytail: read once per start; restart the bridge each morning (the start script does) to pick up new contracts
const IDS = new Map();
for (const f of ["scrip_archive.csv", "scrip_master.csv"]) {     // A226: the archive keeps expired contracts (--now <past day>)
  if (f !== "scrip_master.csv" && !fs.existsSync(`${DATA}/${f}`)) continue;
  for (const line of fs.readFileSync(`${DATA}/${f}`, "utf8").split("\n")) {
    if (!/^(NSE|BSE),D,/.test(line)) continue;
    const r = line.split(",");
    if ((r[6] === "NIFTY" || r[6] === "SENSEX") && (r[14] === "CE" || r[14] === "PE"))
      IDS.set(`${r[0]}|${r[6]}|${r[12]}|${Math.round(+r[13])}|${r[14]}`, r[2]);
  }
}

// the chain recorder's last snapshot for an index: {spot, expiry} (read from the file's tail, not the whole day)
function chainNow(idx) {
  const p = `${DATA}/chain/chain_${idx}_${today()}.jsonl`;
  try {
    const fd = fs.openSync(p, "r"), size = fs.fstatSync(fd).size, n = Math.min(size, 262144), buf = Buffer.alloc(n);
    fs.readSync(fd, buf, 0, n, size - n); fs.closeSync(fd);
    const lines = buf.toString("utf8").trim().split("\n");
    for (let i = lines.length - 1; i >= 1; i--) { try { const r = JSON.parse(lines[i]); if (r.spot && r.expiry) return r; } catch { } }
  } catch { }
  return null;
}

// a past day: its whole spot range from its chain file, so every strike the day touched gets asked
function dayRange(idx, day = DAY) {
  let lo = Infinity, hi = -Infinity, expiry = null;
  try {
    for (const l of fs.readFileSync(`${DATA}/chain/chain_${idx}_${day}.jsonl`, "utf8").split("\n")) {
      try { const r = JSON.parse(l); if (r.spot) { lo = Math.min(lo, r.spot); hi = Math.max(hi, r.spot); expiry = r.expiry || expiry; } } catch { }
    }
  } catch { }
  return expiry && { lo, hi, expiry };
}

// the contracts to ask this minute: ATM ±INNER always, ±(INNER+1..OUTER) every 3rd minute (a past day: all, low-5..high+5)
function autoTargets(minute) {
  const out = [];
  for (const ix of IDX) {
    const c = DAY ? dayRange(ix.name) : chainNow(ix.name); if (!c) continue;
    const lo = Math.round((DAY ? c.lo : c.spot) / ix.step), hi = Math.round((DAY ? c.hi : c.spot) / ix.step);
    for (let k = lo - OUTER; k <= hi + OUTER; k++) {
      if (!DAY && Math.abs(k - lo) > INNER && minute % 3) continue;
      for (const t of ["CE", "PE"]) {
        const sid = IDS.get(`${ix.exch}|${ix.name}|${c.expiry}|${k * ix.step}|${t}`);
        if (sid) out.push({ sid, EXCH: ix.exch, SEG: "D", idx: ix.name });
      }
    }
  }
  return out;
}

// Anytime start (her standing rule; 4 Nov "whenever i turn on the computer everything ... should be able to backfill"):
// every strike today's spot has touched, ±OUTER, is asked once from 09:15 -- the morning a late start missed, the whole
// day if the bridge starts after the close, the gap a crash left. The range: the server's chain backfill (09:15 to its
// start, small, re-read each round) plus the chain's tail as the day goes.
function backfillSpots(idx, day) {
  const out = [];
  try {
    for (const l of fs.readFileSync(`${DATA}/chain_backfill/backfill_${idx}_${day}.jsonl`, "utf8").split("\n")) {
      try { const r = JSON.parse(l); if (r.spot) out.push(r.spot); } catch { }
    }
  } catch { }
  return out;
}
const span = {};       // idx -> { day, lo, hi }: today's spot range so far
function catchUpTargets() {
  const out = [], day = today();
  for (const ix of IDX) {
    const c = chainNow(ix.name); if (!c) continue;
    let s = span[ix.name];
    if (!s || s.day !== day) {       // the day's first catch-up: the whole chain file once (a bridge restarted after the server)
      const r = dayRange(ix.name, day);
      s = span[ix.name] = { day, lo: r ? r.lo : Infinity, hi: r ? r.hi : -Infinity };
    }
    for (const p of [c.spot, ...backfillSpots(ix.name, day)]) { s.lo = Math.min(s.lo, p); s.hi = Math.max(s.hi, p); }
    for (let k = Math.round(s.lo / ix.step) - OUTER; k <= Math.round(s.hi / ix.step) + OUTER; k++)
      for (const t of ["CE", "PE"]) {
        const sid = IDS.get(`${ix.exch}|${ix.name}|${c.expiry}|${k * ix.step}|${t}`);
        if (sid && asked.get(sid) !== day) out.push({ sid, EXCH: ix.exch, SEG: "D", idx: ix.name });
      }
  }
  return out;
}

async function post(inst, candles, ohlc) {
  const nowS = Date.now() / 1000;
  candles = candles.filter(c => c && c.t + 60 <= nowS - 5);                  // closed minutes only
  for (let i = 0; i < Math.max(candles.length, ohlc.length); i += 1500) {       // TapeMap takes <= 2000 of each per POST
    const body = { inst, name: null, candles: candles.slice(i, i + 1500), ohlc: ohlc.slice(i, i + 1500) };
    try {
      const r = await fetch(DOOR, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!r.ok) log("TapeMap refused", inst.SEC_ID, r.status, (await r.text()).slice(0, 120));
    } catch (e) { log("TapeMap not reachable:", e.message); return 0; }
  }
  return candles.length;
}

function forward(url, reqBody, text) {
  let payload, q;
  try { payload = JSON.parse(text); q = JSON.parse(reqBody || "{}"); } catch { return 0; }
  const inst = { EXCH: String(q.EXCH || "NSE"), SEG: String(q.SEG || "D"), SEC_ID: String(q.SEC_ID || "") };
  if (!/^\d+$/.test(inst.SEC_ID)) return 0;
  if (OF.test(url)) return post(inst, (P.orderFlowV2(payload).data || {}).candles || [], []);
  if (OHLC.test(url) && P.isDhanOHLC(url, payload))
    return post(inst, [], (P.dhanOHLC(payload) || []).map(r => ({ ...r, t: Math.round(r.t / 1000) })));
  return 0;
}

const charts = new Map();      // SEC_ID -> { session, url, headers, body } of the app's own last order-flow request
const bars = new Map();        // SEC_ID -> the same for the app's own last getData (OI / price bars) request (A240)
const asked = new Map();       // SEC_ID -> day it was first asked from 09:15 (later asks fetch the last 15 minutes)
const mine = new Map();        // request body the bridge sent itself -> ms sent (CDP may report it twice)
let ws = null, id = 0, minute = 0, ownLoads = 0;
const pend = new Map();
const call = (method, params = {}, sessionId, ms = 30000) => new Promise(res => {
  const i = ++id; pend.set(i, res); ws.send(JSON.stringify({ id: i, method, params, sessionId }));
  setTimeout(() => { if (pend.has(i)) { pend.delete(i); res({ error: "timeout" }); } }, ms);
});

// one POST from inside a chart frame, with the app's own headers (no credentials mode, like the app's own fetch:
// "include" against a wildcard CORS reply failed on 3 Nov)
const askIn = (session, url, headers, body) => call("Runtime.evaluate", { expression: `Promise.race([fetch(${JSON.stringify(url)}, {method: "POST", headers: ${JSON.stringify(Object.fromEntries(Object.entries(headers).filter(([k]) => !NO_COPY.test(k))))}, body: ${JSON.stringify(JSON.stringify(body))}}).then(r => r.ok ? r.text() : Promise.reject("HTTP " + r.status)), new Promise((_, no) => setTimeout(() => no("no reply in 12 s"), 12000))])`, awaitPromise: true, returnByValue: true }, session, 15000);

let asking = false;
async function ask() {
  if (asking) return;                                // one round at a time; a slow round never overlaps the next
  asking = true;
  try { await askRound(); } finally { asking = false; }
}

async function askRound() {
  const via = [...charts.values()].at(-1);
  // the bridge borrows the app's own login, which only shows in the app's own order-flow request (a chart frame
  // cannot be reloaded over CDP: "only top-level targets"), so with none seen yet it waits and says what to do
  if (!via) { log("waiting for Dext to load a chart - change one chart's timeframe in Dext once"); return; }
  const targets = new Map(), t0 = Date.now(), nowS = Math.floor(t0 / 1000), per = {};
  for (const [sid, c] of charts) targets.set(sid, { sid, EXCH: c.body.EXCH, SEG: c.body.SEG, idx: "chart" });
  if (inSession() || NOW_FLAG) for (const t of autoTargets(minute)) if (!targets.has(t.sid)) targets.set(t.sid, t);
  if (!DAY && istNow().toISOString().slice(11, 16) >= "09:15") for (const t of catchUpTargets()) if (!targets.has(t.sid)) targets.set(t.sid, t);
  minute++;
  let n = 0, sent = 0, failed = 0, nbars = 0;
  for (const t of targets.values()) {
    const start = asked.get(t.sid) === today() ? nowS - RECENT_S : todayOpen(), end = DAY ? Math.min(nowS, dayAt(15, 30)) : nowS;
    const body = { ...via.body, EXCH: t.EXCH, SEG: t.SEG, SEC_ID: Number(t.sid), START: start, END: end, START_TIME: iso(start), END_TIME: iso(end) };
    for (const [k, ms] of mine) if (Date.now() - ms > 60000) mine.delete(k);
    mine.set(JSON.stringify(body), Date.now());      // the listener must not count this request as the app's own
    // A240: a chart's 1-minute OI / price bars too (the half the Chrome extension sent and the bridge did not), on the
    // app's own getData request for that chart with INTERVAL "1" (Dext's 1m code); the chart's own timeframe stays as it is
    const g = t.idx === "chart" && bars.get(t.sid);
    if (g) {
      const gb = { ...g.body, START: start, END: end, START_TIME: iso(start), END_TIME: iso(end), INTERVAL: "1" };
      mine.set(JSON.stringify(gb), Date.now());
      const gr = await askIn(g.session, g.url, g.headers, gb);
      if (typeof (gr && gr.result && gr.result.value) === "string") { await forward(g.url, JSON.stringify(gb), gr.result.value); nbars++; }
      else if (/Session with given id not found/.test(JSON.stringify(gr))) bars.delete(t.sid);    // that frame reloaded
    }
    const r = await askIn(via.session, via.url, via.headers, body);
    const text = r && r.result && r.result.value;
    if (typeof text !== "string") {
      const why = String((r && r.exceptionDetails && ((r.exceptionDetails.exception || {}).description || r.exceptionDetails.text)) || (r && r.message) || (r && r.error) || "no reply");
      failed++;
      if (/Session with given id not found/.test(why)) {      // that chart's frame reloaded: ask from another next round
        for (const [sid, c] of charts) if (c.session === via.session) charts.delete(sid);
        log("Dext chart frame reloaded; the next round asks from another chart"); break;
      }
      if (failed <= 3) log("ask failed", t.sid, why.slice(0, 140));
      continue;
    }
    n++; per[t.idx] = (per[t.idx] || 0) + 1; asked.set(t.sid, today());
    sent += await forward(via.url, JSON.stringify(body), text);
  }
  log(`asked ${n}/${targets.size} (${Object.entries(per).map(([k, v]) => k + " " + v).join(", ")}) · ${sent} closed candles · OI/price ${nbars}/${charts.size} charts` +
    (nbars < charts.size ? " (a chart with none: change its timeframe in Dext once)" : "") + ` · ${ownLoads} own Dext loads · ${((Date.now() - t0) / 1000).toFixed(0)} s` + (failed ? ` · ${failed} failed` : ""));
  ownLoads = 0;
  if (NOW_FLAG && DAYS.length) { DAY = DAYS.shift(); asked.clear(); return askRound(); }     // the next past day, same login
  if (NOW_FLAG) process.exit(0);
}

async function connect() {
  let ver;
  try { ver = await (await fetch(CDP)).json(); } catch { log("Dext not reachable on 9229 - start it with start-dext-debug.bat; retrying in 15 s"); return setTimeout(connect, 15000); }
  ws = new WebSocket(ver.webSocketDebuggerUrl);
  const reqs = new Map();
  // new frames wait for the bridge (waitForDebuggerOnStart) until it listens to them, so a reloaded chart's first
  // order-flow request is never missed; each is released with runIfWaitingForDebugger (Chrome releases all on disconnect)
  const AUTO = { autoAttach: true, waitForDebuggerOnStart: true, flatten: true };
  ws.onopen = () => { log("connected to Dext", ver.Browser, `· ${IDS.size} NIFTY/SENSEX option ids loaded`); call("Target.setAutoAttach", AUTO); };
  ws.onclose = () => { log("Dext connection closed; retrying in 15 s"); charts.clear(); setTimeout(connect, 15000); };
  ws.onmessage = async ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result || m.error || {}); pend.delete(m.id); return; }
    if (m.method === "Target.attachedToTarget") {
      const s = m.params.sessionId;
      (async () => {
        await call("Network.enable", {}, s, 5000);
        await call("Target.setAutoAttach", AUTO, s, 5000);
        call("Runtime.runIfWaitingForDebugger", {}, s, 5000);
      })();
    }
    if (m.method === "Network.requestWillBeSent" && m.params.request.method === "POST" && m.params.request.postData && (OF.test(m.params.request.url) || OHLC.test(m.params.request.url))) {
      const r = m.params.request, frames = ((m.params.initiator || {}).stack || {}).callFrames || [];
      // the bridge's own asks: same body, or started from Runtime.evaluate (no script url) -- askRound forwards those
      if (mine.has(r.postData) || (frames.length && frames.every(f => !f.url))) return;
      reqs.set(m.params.requestId, { url: r.url, body: r.postData });
      if (OF.test(r.url)) {
        try {
          const b = JSON.parse(r.postData), sid = String(b.SEC_ID || "");
          if (/^\d+$/.test(sid)) {
            if (!charts.has(sid)) log("chart open in Dext:", sid);
            charts.set(sid, { session: m.sessionId, url: r.url, headers: r.headers || {}, body: b });
          }
        } catch { /* not JSON: ignore */ }
      }
      if (OHLC.test(r.url)) {
        try {
          const b = JSON.parse(r.postData), sid = String(b.SEC_ID || "");
          if (/^\d+$/.test(sid) && b.INTERVAL) bars.set(sid, { session: m.sessionId, url: r.url, headers: r.headers || {}, body: b });
        } catch { /* not JSON: ignore */ }
      }
    }
    if (m.method === "Network.loadingFinished" && reqs.has(m.params.requestId)) {
      const q = reqs.get(m.params.requestId); reqs.delete(m.params.requestId);
      const b = await call("Network.getResponseBody", { requestId: m.params.requestId }, m.sessionId);
      if (b && typeof b.body === "string") {
        await forward(q.url, q.body, b.base64Encoded ? Buffer.from(b.body, "base64").toString("utf8") : b.body);
        if (OF.test(q.url)) ownLoads++;
      }
    }
  };
}

// one bridge at a time: a second copy (the start script double-clicked) would ask Dhan twice and re-ask the first
// copy's requests. Holding a local port is the lock; the OS frees it when this process ends.
// --targets YYYY-MM-DD: print what a start at that day's end would catch up, then exit (no Dext, no ask): the check.
if (TARGETS_FLAG) {
  const t = catchUpTargets(), by = {};
  for (const x of t) by[x.idx] = (by[x.idx] || 0) + 1;
  console.log(`${today()}: catch-up would ask ${t.length} contracts`, by, JSON.stringify(span));
  process.exit(0);
}
// A --now check may run beside it: the live copy never re-asks requests sent from Runtime.evaluate (no script url).
const start = () => {
  connect();
  setInterval(() => { if (ws && ws.readyState === 1) ask().catch(e => log("ask error", e.message)); }, ASK_MS);
};
import("node:net").then(({ createServer }) => createServer().once("error", () => {
  if (NOW_FLAG) return start();
  log("another dext bridge is already running - this copy stops"); process.exit(1);
}).listen(9230, "127.0.0.1", start));
if (NOW_FLAG) setTimeout(() => ask().catch(e => log("ask error", e.message)), 20000);
