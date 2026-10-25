// validate_app_harness.cjs -- boots the Validate face's app.js (ui-v2/public/validate2/app.js) in node with its browser globals
// stubbed, for test_validate_app.py (25 Oct review F9 / F10). As shell.mjs does with main.js, a test seam is appended to the
// source as it is loaded (globalThis.__app); the shipped file is not changed. argv[2] names the scenario; stdout is its JSON.
const fs = require("fs"), vm = require("vm"), path = require("path");
const SRC = fs.readFileSync(path.join(__dirname, "..", "ui-v2", "public", "validate2", "app.js"), "utf8")
  .replace(/boot\(\);\s*\}\)\(\);\s*$/, "boot(); globalThis.__app = { S, voiceStop, protoSub, engineWord, poll, pollTrades, pollFold, pollFlat, pollDecode, markTrade, exitTrade, check, E };\n})();\n");
const TRADE = { id: "NIFTY-23000PE-long-100000", idx: "NIFTY", k: 23000, side: "PE", role: "long", t0: "10:00:00", p0: 100, exit_t: null };
const DATA = { ok: true, live: true, day: "2026-10-26", now: 37000, idx: { NIFTY: { t: [36000] }, BANKNIFTY: { t: [36000] }, SENSEX: { t: [36000] } } };
const wait = () => new Promise((r) => setTimeout(r, 20));

// a route answers a body, a promise of one (a slow reply the scenario lets go), or "hang": a request that answers only when its
// signal fires (and never, with no signal)
const routes = (over = {}) => (url, opts) => {
  for (const [p, b] of Object.entries(over)) if (url.startsWith(p)) return typeof b === "function" ? b(url, opts) : b;
  return url.startsWith("/api/v2/data") ? DATA : url.startsWith("/api/hold/trades") ? { ok: true, trades: [TRADE] } : { ok: true };
};

function boot(route) {
  const calls = [], fired = [], flags = {}, el = () => ({ hidden: true, style: {}, textContent: "", innerHTML: "" });
  const ctx = {
    console, URLSearchParams, performance, setTimeout: (f, ms) => setTimeout(f, ms).unref(), clearTimeout, setInterval: () => 0, requestAnimationFrame: () => 0,
    innerHeight: 900, innerWidth: 1600, location: { search: "" }, localStorage: { getItem: () => null, setItem() {} },
    document: { addEventListener() {}, getElementById: el, querySelector: () => null, body: {}, title: "" },
    preact: { h() {}, render() {} }, preactHooks: { useRef: () => ({}), useEffect() {}, useLayoutEffect() {} }, htm: { bind: () => () => null },
    Engine: { fmt: String, sgn: String, pct: String, L: String, hm: String, hms: (s) => new Date(s * 1000).toISOString().slice(11, 19), IDX: ["NIFTY", "BANKNIFTY", "SENSEX"],
              OPEN: 33300, CLOSE: 55800, PRACTICE: 54000, data: null, load(d) { this.data = d; }, events: () => [], setDecode() {},
              apply: () => (flags.reload ? "reload" : "ok"), validate: () => ({ ok: true, px: 100, rev: 3, word: "OK", counts: { w: 0, a: 0, n: 0, c: 0, of: 0 } }),
              snap: () => ({ ages: { chain: 5, book: 5 }, i: 0, vpin: null }), inTrade: () => ({ ok: false }), board: () => null },   // what frame() reads (check() uses it)
    // the bound as app.js asks for it: a signal this harness fires, carrying the ms it was asked for
    AbortSignal: { timeout: (ms) => { const ac = new AbortController(); ac.signal.ms = ms; fired.push(ac); return ac.signal; } },
    fetch: (url, opts) => {
      const sig = opts && opts.signal, body = route(url, opts);
      calls.push({ url, ms: sig ? sig.ms : null, body: opts && opts.body ? JSON.parse(opts.body) : null });
      if (body === "hang") return new Promise((_, no) => { if (sig) sig.addEventListener("abort", () => no(new Error("timed out"))); });
      return Promise.resolve(body).then((b) => ({ ok: true, status: 200, json: async () => b }));
    },
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { app: () => ctx.__app, calls, flags, timeout: () => fired.splice(0).forEach((ac) => ac.abort()) };
}

const SCEN = {
  // F12 (25 Oct review, A75): her VALIDATE press posts engine.js's word, once per press, on the live clock only
  async press() {
    const b = boot(routes());
    await wait();
    const A = b.app(), sent = () => b.calls.filter((c) => c.url === "/api/validate/log").map((c) => c.body);
    A.E.validate = () => ({ ok: true, rev: "3.1 (SENSEX-NIFTY-FLOW 9e2831b5)", idx: "NIFTY", K: 23000, ty: "PE", side: "BUY", px: 96.2, word: "WAIT",
      counts: { w: 4, a: 1, n: 2, c: 2, of: 9 }, checks: [{ name: "RIGHT NOW", st: "WITH", cell: "flow saath", tip: "a long hover" }] });
    Object.assign(A.S, { live: true, liveFollow: true, closed: false, T: 36312, slip: { idx: "NIFTY", K: 23000, ty: "PE", side: "BUY", px: "" } });
    A.check();
    await wait();
    const live = sent();
    A.E.snap = () => ({ ages: { chain: 200, book: 5 }, i: 0, vpin: null });   // the chain is 200 s old: the face reads CAN'T CHECK
    A.check();
    await wait();
    const stale = sent().slice(1);
    A.S.liveFollow = false;                                        // scrubbed back: a replay press is not forward evidence
    A.check();
    await wait();
    return { live, stale, after: sent().length, mode: A.S.mode };
  },
  // F10 (DEV-FACES F20): each poller keeps one request in flight, bounded at 8 s; a request that timed out frees its poller
  async pollers() {
    let nT = 0;
    const b = boot(routes({ "/api/hold/trades": () => (++nT === 1 ? { ok: true, trades: [TRADE] } : "hang"),
                            "/api/fold?id=": "hang", "/api/fold/flat": "hang", "/api/v2/data?": "hang" }));
    await wait();                                                  // boot: its pollTrades answered, its pollFlat hangs
    const A = b.app(), n = (p) => b.calls.filter((c) => c.url.startsWith(p)).length;
    A.pollFold(); A.pollFold(); A.pollFlat(); A.pollTrades(); A.pollTrades(); A.poll(false); A.poll(false);
    await wait();
    const inFlight = { fold: n("/api/fold?id="), flat: n("/api/fold/flat"), trades: n("/api/hold/trades"), data: n("/api/v2/data?") };
    b.timeout();                                                   // the 8 s bound fires on every request still out
    await wait();
    A.pollFold(); A.pollFlat(); A.pollTrades();
    await wait();
    return { inFlight, after: { fold: n("/api/fold?id="), flat: n("/api/fold/flat"), trades: n("/api/hold/trades") },
             bounded: b.calls.filter((c) => /^\/api\/(fold|hold\/trades|v2\/data\?)/.test(c.url)).map((c) => c.ms),
             feed: A.S.feed, fold: A.S.fold[TRADE.id] };
  },
  // F10 round 1: a mark or an exit refreshes the trade list with a read that began AFTER the write, even with the 5 s poll's read in flight
  async refresh_after_write() {
    const phase = async (seed, act) => {
      const srvT = seed ? [{ ...TRADE }] : [], copy = () => JSON.parse(JSON.stringify(srvT));
      let hold = false, release = null, nGet = 0;
      const b = boot(routes({ "/api/hold/trades": (u, o) => {
        if (o && o.method === "POST") {
          if (JSON.parse(o.body).op === "mark") srvT.push({ ...TRADE, id: "NIFTY-22600CE-long-100000", k: 22600, side: "CE" }); else srvT[0].exit_t = "10:05:00";
          return { ok: true, trades: copy() };
        }
        nGet++;
        const snap = { ok: true, trades: copy() };
        return hold ? (hold = false, new Promise((ok) => { release = () => ok(snap); })) : snap;      // the held read answers what the server said when it was asked
      } }));
      await wait();                                                // boot's read answered
      const A = b.app();
      hold = true; A.pollTrades();                                 // the 5 s poll: a slow read, it will land stale
      const w = act(A);
      await wait();
      const during = nGet;
      release(); await w; await wait();
      return { during, gets: nGet, sel: A.S.sel, exitTs: A.S.trades.map((t) => t.exitT) };
    };
    return { mark: await phase(false, (A) => A.markTrade()),
             exit: await phase(true, (A) => { const t = A.S.trades[0]; A.exitTrade(t); return A.exitTrade(t); }) };   // arm, then confirm
  },
  // F10 round 1: the full reload poll() falls back to is bounded too (20 s: it is the whole day); a hung one frees `polling`, FEED DEAD shows
  async full_reload() {
    let full = 0;
    const b = boot(routes({ "/api/v2/data": (u) => (/since=/.test(u) || ++full === 1 ? DATA : "hang") }));
    await wait();                                                  // boot's loadFull answered
    const A = b.app(), n = () => b.calls.filter((c) => c.url.startsWith("/api/v2/data")).length;
    b.flags.reload = true;
    A.poll(false); await wait();                                   // the tail answers, Engine.apply says reload, loadFull hangs
    const ms = b.calls.filter((c) => /^\/api\/v2\/data\?day=[^&]*$/.test(c.url)).map((c) => c.ms);
    b.timeout(); await wait();
    const dead = A.S.feed, before = n();
    b.flags.reload = false; A.poll(false); await wait();           // polling is free again: the tail asks, and answers
    return { ms, dead, again: n() - before, feed: A.S.feed };
  },
  // F10 round 1: the decode poll's read is bounded at 8 s and frees its flag like the others
  async decode() {
    const b = boot(routes({ "/api/decode": "hang" }));
    await wait();
    const A = b.app(), reads = () => b.calls.filter((c) => c.url.startsWith("/api/decode"));
    A.S.liveFollow = false;                                        // off the live clock: one read per five-minute chart
    A.S.T = 36000; A.pollDecode(); A.S.T = 36400; A.pollDecode();  // two charts; the second waits for the first
    await wait();
    const inFlight = reads().length;
    b.timeout(); await wait();
    A.S.T = 36700; A.pollDecode(); await wait();
    return { inFlight, ms: reads().map((c) => c.ms), why: A.S.decWhy };
  },
  // F9: the stop is the voice's, or why there is none -- never engine.js's own give-up G
  async voice_stop() {
    const b = boot(routes());
    await wait();
    const A = b.app(), t = { id: TRADE.id }, at = (f) => { A.S.fold[t.id] = f; return A.voiceStop(t, A.S.T); };
    return { refused: at({ ok: false, id: t.id, why: "could not check — the engine is catching up (12 of 40 rows)" }),
             mute: at({ ok: true, voice: { ok: false, why: "could not check — HOLD v2 has no line yet" } }),
             none: at({ ok: true }),
             spoke: at({ ok: true, voice: { ok: true, stop_f: 23050, stop_s: 23010, stop_src: "HOLD v2" } }) };
  },
  // F9 round 1: the voice spoke with a futures stop and no spot one -- the stop in fut only, `spot ?`, never "voice nahi aayi"
  async fut_only() {
    const b = boot(routes());
    await wait();
    const A = b.app(), t = { id: TRADE.id };
    A.S.fold[t.id] = { ok: true, voice: { ok: true, stop_f: 22640, stop_s: null, stop_src: "fold engine" } };
    return A.voiceStop(t, A.S.T);
  },
  // F9 round 1: off the live clock the stop's why is the replayed entry's own voice why, else the path's, else the default
  async path_why() {
    const b = boot(routes());
    await wait();
    const A = b.app(), t = { id: TRADE.id }, at = (p, T) => { A.S.live = true; A.S.liveFollow = false; A.S.vpath[t.id] = p; return A.voiceStop(t, T); };
    const mute = (hms, why) => ({ at: hms, voice: { ok: false, why } });
    const p = { ok: true, why: "could not check — path why", path: [mute("10:01:00", "could not check — first"), mute("10:02:00", "could not check — second"), mute("10:03:00", "could not check — later")] };
    return { entry: at(p, 10 * 3600 + 2 * 60 + 30), first: at(p, 10 * 3600 + 90),
             refused: at({ ok: false, why: "could not check — replay refused" }, 37000), bare: at({ ok: true, path: [{ at: "10:01:00" }] }, 37000) };
  },
  // F9 round 1: the prototype row's "out if G fut accepted" is a stop; with no voice stop (fold refused) it is not printed
  async proto_row() {
    const b = boot(routes());
    await wait();
    const A = b.app(), t = { id: TRADE.id }, r = { ok: true, word: "HOLD", folded: false, pb: null, dist: { G: 23000 }, s: { fut: 23100 }, e: { fut: 23050 } };
    A.S.live = true; A.S.liveFollow = true;
    const at = (f) => { A.S.fold[t.id] = f; return { sub: A.protoSub(t, A.S.T, r), ew: A.engineWord(t, A.S.T, r) }; };
    const out = {};
    for (const [k, f] of [["refused", { ok: false, why: "could not check — the engine is catching up" }],
                          ["mute", { ok: true, voice: { ok: false, why: "could not check — HOLD v2 has no line yet" } }],
                          ["nostop", { ok: true, voice: { ok: true, stop_f: null, stop_s: null } }],
                          ["spoke", { ok: true, voice: { ok: true, stop_f: 23050, stop_s: 23010, stop_src: "HOLD v2" } }]]) {
      const o = at(f); out[k] = { sub: o.sub, ewSub: o.ew.sub, src: o.ew.src, headline: o.ew.headline };
    }
    return out;
  },
};

SCEN[process.argv[2]]().then((o) => process.stdout.write(JSON.stringify(o)),
  (e) => process.stdout.write(JSON.stringify({ err: String((e && e.stack) || e) })));
