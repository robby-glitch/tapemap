/* app.js — the VALIDATE workspace face. Preact + htm (CDN), one store, one render per replay second.
   Panels: menubar · outliner · viewport (OI ladder) · inspector · console/timeline · status bar · command palette. */
(() => {
  const { h, render } = preact, { useRef, useEffect, useLayoutEffect } = preactHooks, html = htm.bind(h);
  const E = Engine, { fmt, sgn, pct, L, hm, hms, IDX, OPEN, CLOSE, PRACTICE } = E;

  // ---------- icons: Lucide from the CDN, a small inline fallback if it did not load ----------
  const FALLBACK = { "arrow-up": ["m5 12 7-7 7 7", "M12 19V5"], "arrow-down": ["M12 5v14", "m19 12-7 7-7-7"], check: ["M20 6 9 17l-5-5"], x: ["M18 6 6 18", "m6 6 12 12"], minus: ["M5 12h14"], play: ["M6 3 20 12 6 21z"], pause: ["M14 4h4v16h-4z", "M6 4h4v16H6z"], "circle-help": ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z", "M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3", "M12 17h.01"], "eye-off": ["m2 2 20 20", "M6.7 6.7A10.9 10.9 0 0 0 2 12s3 7 10 7a9.7 9.7 0 0 0 5.3-1.5"], search: ["m21 21-4.3-4.3", "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z"] };
  const ICONS = {};
  function icon(name, cls = "") {
    if (!ICONS[name]) {
      let body = "";
      const pas = name.split("-").map(p => p[0].toUpperCase() + p.slice(1)).join("");
      const node = window.lucide && window.lucide.icons && (window.lucide.icons[pas] || window.lucide.icons[name]);
      if (node) { const kids = Array.isArray(node) && Array.isArray(node[0]) ? node : (node[2] || []); body = kids.map(([tag, at]) => `<${tag} ${Object.entries(at || {}).filter(([k]) => k !== "key").map(([k, v]) => `${k}="${v}"`).join(" ")}/>`).join(""); }
      else if (FALLBACK[name]) body = FALLBACK[name].map(d => `<path d="${d}"/>`).join("");
      else body = `<circle cx="12" cy="12" r="3"/>`;
      ICONS[name] = `<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
    }
    return html`<span class=${"ico " + cls} dangerouslySetInnerHTML=${{ __html: ICONS[name] }}></span>`;
  }

  // ---------- store ----------
  const DAY = new URLSearchParams(location.search).get("day");     // ?day=YYYY-MM-DD replays that day; else today, live
  const S = { T: OPEN, playing: false, speed: 1, mode: "read", focus: "NIFTY", slip: { idx: "NIFTY", K: 22600, ty: "CE", side: "BUY", px: "" },
    pressed: null, trades: [], feed: "boot", feedWhy: "", feedSince: null, consoleMin: false, pal: null, oiRef: "15m", about: false, loaded: false, sel: "NIFTY", follow: true, win: 6,
    day: DAY, live: false, liveFollow: true, srvNow: null, srvAt: 0, closed: false, fold: {}, foldWords: {}, flat: {}, arm: null, apiWhy: "",
    vpath: {},                                                        // A56 trade id -> GET /api/voice_path's reply
    vOpen: (() => { try { return localStorage.getItem("v2.vdet") === "1"; } catch (e) { return false; } })() };   // A52 the voice's detail
  const feedT = () => S.T;                                          // the data is whatever the feed delivered; its age is printed, never faked
  const nowSec = () => S.srvNow == null ? S.T : Math.min(CLOSE, Math.round(S.srvNow + (performance.now() - S.srvAt) / 1000));
  const secOf = v => { const [h, m, x] = String(v).split(":").map(Number); return h * 3600 + m * 60 + (x || 0); };
  let raf = 0; const up = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; draw(); }); };

  // ---------- value with a 600 ms meaning-colour flash on change ----------
  function Val({ v, tone = "n", cls = "" }) {
    const ref = useRef(), prev = useRef(v);
    useLayoutEffect(() => { if (prev.current !== v && ref.current) { const el = ref.current; el.classList.remove("fl"); void el.offsetWidth; el.classList.add("fl"); } prev.current = v; }, [v]);
    return html`<span ref=${ref} class=${`v t-${tone} ${cls}`}>${v}</span>`;
  }
  const TONE = { WITH: "b", AGAINST: "r", NEITHER: "g", CNC: "g", NS: "g", PR: "g", QUIET: "g", GO: "b", WAIT: "a", NO: "r", HOLD: "b", FOLD: "r", OUT: "g", "GAVE UP": "r", "PAST GIVE-UP": "a" };
  const pnlOf = (t, r) => +((r.prem - r.e.prem) * (t.side === "BUY" ? 1 : -1)).toFixed(2);   // her P&L sign: a short gains when the premium falls
  const Chip = ({ st, text, tip, lg }) => html`<span class=${`ch ch-${st === "PR" ? "NS" : st} ${lg ? "lg" : ""}`} data-tip=${tip}>${st === "CNC" ? icon("circle-help") : st === "NS" ? icon("eye-off") : st === "PR" ? icon("eye") : st === "WITH" ? icon("check") : st === "AGAINST" ? icon("x") : st === "NEITHER" || st === "QUIET" ? icon("minus") : null}${text || (st === "CNC" ? "can't check" : st === "NS" ? "not shown" : st === "PR" ? "printed" : st.toLowerCase())}</span>`;

  const Pill = ({ p, tip }) => html`<span class=${`ch ch-pill ch-${p.tone}`} data-tip=${tip}>${p.tone === "CNC" ? icon("circle-help") : null}${p.t}</span>`;

  // ---------- frame ----------
  function frame() {
    const T = S.T, ft = feedT();
    const snaps = {}; for (const i of IDX) snaps[i] = E.snap(i, T, ft);
    const trades = S.trades.filter(t => t.t0 <= T).map(t => { const r = E.inTrade(t, T, ft); return { t, r, open: r.ok && !r.folded }; });
    const open = trades.find(x => x.open) || null, lastTrade = trades[trades.length - 1] || null;
    const slip = S.slip, K = Number(slip.K), px = slip.px === "" ? null : Number(slip.px);
    const val = S.mode === "validate" ? E.validate(slip.idx, K, slip.ty, slip.side, px, T, ft) : null;
    const board = val && val.ok ? E.board(T, ft, val) : null;
    const read = S.mode === "read" ? E.read(S.focus, T, ft) : null;
    const s = snaps[S.focus];
    const ages = { chain: s.ages.chain, book: s.ages.book, vpin: snaps.NIFTY.vpin ? snaps.NIFTY.vpin.age : null };
    const stale = (ages.chain != null && ages.chain > 180) || (ages.book != null && ages.book > 30) || s.i < 0;
    return { T, ft, snaps, s, trades, open, lastTrade, val, board, read, ages, stale, closed: T >= CLOSE || (S.live && S.closed && S.liveFollow) };
  }

  // ---------- menubar ----------
  const MODES = [["read", "1", "MARKET READ"], ["validate", "2", "VALIDATE"], ["trade", "3", "IN TRADE"]];
  function Menubar({ F }) {
    return html`<div class="menubar">
      <div class="brand"><span class="dot"></span>TapeMap <span class="f">· Validate</span></div>
      ${["Workspace", "View", "Replay", "Feed"].map(m => html`<button class="menu" key=${m} onClick=${() => openPal(m.toLowerCase() === "feed" ? "feed " : m.toLowerCase() === "replay" ? "go " : "")}>${m}</button>`)}
      <a class="menu" href="/pro.html" target="_blank" rel="noopener" data-tip="the old DESK: RECORD, scoreboard, tradebook import">Record</a>
      <button class="menu" onClick=${() => { S.about = !S.about; up(); }} data-tip="what is real data and what is prototype logic · the keyboard map">About</button>
      <span class="sp"></span>
      <div class="modes">${MODES.map(([m, k, l]) => html`<button key=${m} class=${S.mode === m ? "on" : ""} onClick=${() => setMode(m)}><kbd>${k}</kbd>${l}</button>`)}</div>
      <button class="kbtn" onClick=${() => openPal("")}>${icon("command")} <span>Command</span> <kbd class="k">Ctrl K</kbd></button>
    </div>`;
  }
  function FeedBand({ F }) {
    const nx = E.data && E.data.idx[S.focus], bf = nx && nx.bf ? nx : null;
    if (S.feed !== "dead" && S.live && (S.late || bf)) return html`<div class="band on slow" data-tip=${bf ? bf.bfWhy : "the server came up late; nothing before it was rebuilt"}>${icon("clock")}<b>LATE START ${S.late ? S.late.up : (bf.chainFrom || "").slice(0, 5)}</b><span>${bf ? `OI + spot backfilled ${bf.bfFrom}–${bf.bfTo} [I] · order flow from ${(bf.flowFrom || "—").slice(0, 5)} (ticks before it are lost)` : `server came up ${S.late.min} min after the open · this view's day starts ${S.late.from} · high/low, VWAP, CVD and OI-since-open miss 09:15–${S.late.up}`}</span></div>`;
    if (S.feed !== "dead") return html`<div class="band"></div>`;
    return html`<div class="band on dead">${icon("wifi-off")}<b>FEED DEAD</b><span>/api/v2/data not answering since ${S.feedSince ? hms(S.feedSince) : "—"} · ${S.feedWhy} · reads stand at ${hms(F.ft)}, ages printed</span><span class="fix" data-tip="the server is the fix, not the screen: .\\stop.bat ; .\\start-v2.bat, then check the Upstox token in its log">fix: .\\stop.bat ; .\\start-v2.bat</span><span class="sp"></span><button onClick=${() => { poll(true); }}>retry now</button></div>`;
  }
  const fmtAge = a => a == null ? "—" : a < 60 ? a.toFixed(0) + " s" : `${Math.floor(a / 60)}:${String(Math.floor(a % 60)).padStart(2, "0")}`;

  // ---------- outliner ----------
  function Outliner({ F }) {
    const dayWord = s => !s.ok ? "no chain" : s.day.type === "TREND" ? (s.day.dir > 0 ? "TREND ▲" : "TREND ▼") : s.day.type;
    return html`<div class="pane">
      <div class="pane-h">Outliner<span class="sp"></span><span class="r">${hms(F.T)}</span></div>
      <div class="pane-b">
        <div class="ol-sec">${icon("layers")} Indices</div>
        ${IDX.map(i => { const s = F.snaps[i]; return html`<button key=${i} class=${`ol-row ${S.sel === i ? "on" : ""}`} onClick=${() => selectIdx(i)} data-tip=${s.ok ? `${i} · spot ${fmt(s.spot, 1)} / fut ${fmt(s.fut, 1)} · basis ${fmt(s.basis, 1)} [M] · ${s.day.type} since ${hm(s.day.since)} · ${s.whose.text} · ${s.dte === 0 ? "expiry today" : s.dte + " DTE"}${s.thin ? " · thin tape: witness" : ""}` : `${i}: no chain row yet`}>
          <div class="t"><span class="nm">${i}</span>${s.ok ? html`<span class="n f">${sgn(Math.round(s.basis))}</span>` : null}<span class="px n"><${Val} v=${s.ok ? fmt(s.spot) : "—"} tone="n"/></span></div>
          <div class="m">${s.ok ? html`<${Val} v=${dayWord(s)} tone=${s.day.type === "TREND" ? "a" : "n"} cls="b"/><span class="n" data-tip="futures last [M]">${fmt(s.fut)}<span class="f">f</span></span>${s.last && F.T - s.last.t <= 1800 ? html`<span class="n" data-tip=${`${s.last.who} won ${hm(s.last.t)} at ${fmt(s.last.vw)} fut`}>${s.last.who === "buyers" ? icon("arrow-up") : icon("arrow-down")}${hm(s.last.t)}</span>` : html`<span class="n f">quiet</span>`}${s.pcr.now && s.pcr.now.r != null ? html`<span class="n" data-tip="PCR over the nine around ATM [M]">${s.pcr.now.r.toFixed(2)}<span class="f">p</span></span>` : null}` : html`<span class="f">chain not posted yet</span>`}</div>
        </button>`; })}
        <div class="ol-sec">${icon("flag")} Trades</div>
        ${F.trades.length ? F.trades.map(({ t, r, open }) => html`<button key=${t.id} class=${`ol-row ${S.sel === t.id ? "on" : ""}`} onClick=${() => open ? selectTrade(t.id) : replayTrade(t)} data-tip=${`${t.side} ${t.idx} ${t.K} ${t.ty} @${fmt(r.ok ? r.e.prem : t.px, 2)} marked ${hms(t.t0)}${!open && r.ok ? ` · closed ${hm(r.foldT)} · ${t.exitWhy || "prototype FOLD"} · click: replay from ${hms(t.t0)} at 1×` : ""}`}>
          <div class="t"><span class="nm">${t.side === "BUY" ? "LONG" : "SHORT"} ${t.K} ${t.ty}</span><span class="f">${t.idx}</span><span class="px n"><${Val} v=${r.ok ? fmt(r.prem, 2) : "—"} tone=${r.ok ? (pnlOf(t, r) >= 0 ? "b" : "r") : "n"}/></span></div>
          <div class="m">${r.ok ? html`<${Val} v=${engineWord(t, F.T, r).headline} tone=${TONE[engineWord(t, F.T, r).key] || "n"} cls="b"/><span class=${`n ${pnlOf(t, r) >= 0 ? "cb" : "cr"}`}>${sgn(pnlOf(t, r))}</span><span class="n f">${open ? `${hm(t.t0)} → ${fmtAge(r.tInTrade)}` : `closed ${hm(r.foldT)}`}</span>${!open ? html`<span class="f">${icon("play")} replay</span>` : null}` : null}</div>
        </button>`) : html`<div class="ol-empty">${S.live ? html`no trade marked today · <kbd class="k">M</kbd> marks the slip` : `no trade in the record for ${S.day || E.data.day}`}${S.apiWhy ? html`<div class="ca">${S.apiWhy}</div>` : null}</div>`}
      </div>
    </div>`;
  }

  // ---------- viewport: the OI ladder ----------
  function Ladder({ F }) {
    const s = F.s, x = s.x;
    const center = s.ok ? s.atm : x.ks[Math.floor(x.ks.length / 2)];
    const ks = x.ks.filter(K => Math.abs(K - center) <= S.win * x.step).reverse(), N = ks.length, Ktop = ks[0], step = x.step;
    const yOf = p => { const r = ((Ktop - p) / step + 0.5) / N * 100; return Math.max(0.4, Math.min(99.6, r)); };
    const off = p => p > Ktop + step / 2 || p < ks[N - 1] - step / 2;
    const i = s.i, iRef = s.ok ? Math.max(0, S.oiRef === "15m" ? lastLEidx(x.t, F.ft - 900) : 0) : 0;
    const fronts = s.ok ? [...s.fronts.ce, ...s.fronts.pe] : [];
    const g = F.val && F.val.ok && F.val.idx === S.focus ? F.val.g : F.open && F.open.r.ok && F.open.t.idx === S.focus ? F.open.r.g : null;
    const tagsFor = K => { const t = []; if (s.pin && s.pin.k === K) t.push(["pin", "PIN", `expiry pin: largest CE+PE inside the nine, both legs ≥ ½ their side [M]`]); if (g && g.W && g.W.k === K) t.push(["w", "W", `the wall behind you: ${g.W.k} ${g.W.leg.toUpperCase()} writers defend your trade`]); if (g && g.A && g.A.k === K) t.push(["a", "A", `the wall ahead: ${g.A.k} ${g.A.leg.toUpperCase()} writers your target must break`]); if (g && g.K === K) t.push(["own", g.ty, "your strike"]); if (!t.length) { if (s.fronts.ce.some(f => f.k === K)) t.push(["ceil", "CEIL", "ceiling: a top-2 CE front above spot by peak OI [M]"]); else if (s.fronts.pe.some(f => f.k === K)) t.push(["floor", "FLOOR", "floor: a top-2 PE front below spot by peak OI [M]"]); } return t; };
    let maxC = 1, maxP = 1; if (s.ok) for (let k = 0; k < x.nk; k++) { maxC = Math.max(maxC, x.ce.peakV[i][k] || 0); maxP = Math.max(maxP, x.pe.peakV[i][k] || 0); }
    const wallTone = (leg, K) => { if (!g) return ""; const f = g.W && g.W.k === K && g.W.leg === leg ? g.W : g.A && g.A.k === K && g.A.leg === leg ? g.A : null; if (!f) return ""; return f.state === "BUILDING" ? (f === g.W ? "w-b" : "w-r") : f.state === "UNWINDING" ? (f === g.W ? "w-r" : "w-b") : "w-a"; };
    const side = (leg, K, ki) => {
      if (!s.ok) return html`<div class=${`lside ${leg}`}></div>`;
      const oi = x[leg].oi[i][ki], peak = x[leg].peakV[i][ki], ref = x[leg].oi[iRef][ki], d = oi != null && ref != null ? oi - ref : null, mx = leg === "ce" ? maxC : maxP;
      const fr = fronts.find(f => f.leg === leg && f.k === K) || (g && ((g.W && g.W.k === K && g.W.leg === leg) ? g.W : (g.A && g.A.k === K && g.A.leg === leg) ? g.A : null));
      const bfRef = x.bf && iRef < x.bf, bfNow = x.bf && i < x.bf;
      const tip = oi == null ? "not in the chain window" : `${K} ${leg.toUpperCase()} writers ${L(oi)} ${bfNow ? "[I · rebuilt minute]" : "[M]"} · peak ${L(peak)} ${fr ? hm(fr.peakT) : ""} · ${S.oiRef === "15m" ? "15 min" : "since open"} ${d == null ? "—" : sgn(Math.round(d / 100)) + "L"}${bfRef ? " [I: the open row is a rebuilt minute]" : ""} · ltp ${fmt(x[leg].ltp[i][ki] / 20, 2)}${fr ? ` · ${fr.state} (${pct(fr.off)} off, ${fr.upd} updates since peak) · ${E.HI[fr.state]}` : ""}`;
      const wp = peak / mx * 62, wo = (oi || 0) / mx * 62;
      const bar = html`<div class="bar" data-tip=${tip}><i class="pk" style=${`transform:scaleX(${(wp / 100).toFixed(4)})`}></i><i class=${wallTone(leg, K)} style=${`transform:scaleX(${(wo / 100).toFixed(4)})`}></i>${fr ? html`<em class=${`st ${fr.state}`} style=${leg === "ce" ? `right:calc(${Math.max(wp, wo)}% + 5px)` : `left:calc(${Math.max(wp, wo)}% + 5px)`}>${fr.state === "UNWINDING" ? "leaving" : fr.state === "STALLED" ? "flat" : "building"}</em>` : null}</div>`;
      const num = html`<div class="oi"><${Val} v=${oi == null ? "—" : L(oi)} tone="n"/></div>`;
      const dL = d == null ? null : Math.round(d / 100) || 0;
      const dd = html`<div class=${`d ${dL > 0 ? "up" : dL < 0 ? "dn" : ""}`}><${Val} v=${dL == null ? "" : sgn(dL)} tone=${dL < 0 ? "a" : "n"}/></div>`;
      return leg === "ce" ? html`<div class="lside ce">${bar}${dd}${num}</div>` : html`<div class="lside pe">${num}${dd}${bar}</div>`;
    };
    const lines = [];
    if (s.ok) {
      lines.push({ k: "spot", y: yOf(s.spot), side: "R", a: `SPOT ${fmt(s.spot)}`, b: `fut ${fmt(s.fut)} · ${sgn(Math.round(s.basis))}`, off: off(s.spot) });
      lines.push({ k: "vwap", y: yOf(s.vwap - s.basis), side: "L", a: `VWAP ${fmt(s.vwap - s.basis)}`, b: `fut ${fmt(s.vwap)}`, off: off(s.vwap - s.basis) });
      const ff = s.lateFlow ? ` ${s.flowFrom.slice(0, 5)}+` : "";          // the futures high/low only since the ticks began
      lines.push({ k: "hi", y: yOf(s.sHi), side: "L", a: `HI ${fmt(s.sHi)} ${hm(s.sHiT)}`, b: `${ff ? "f" : "fut"} ${fmt(s.fHi)}${ff}`, off: off(s.sHi) });
      lines.push({ k: "lo", y: yOf(s.sLo), side: "L", a: `LO ${fmt(s.sLo)} ${hm(s.sLoT)}`, b: `${ff ? "f" : "fut"} ${fmt(s.fLo)}${ff}`, off: off(s.sLo) });
      if (F.val && F.val.ok && F.val.idx === S.focus && S.mode === "validate") for (const lv of F.val.levels) if (lv.spot != null) lines.push({ k: lv.name === "STOP" ? "stop" : lv.name === "PULLBACK" || lv.name === "KEEP ALL" ? "t1" : "t2", y: yOf(lv.spot), side: "R", a: `${lv.name} ${fmt(lv.spot)}`, b: `fut ${fmt(lv.fut)}`, off: off(lv.spot) });
      if (F.open && F.open.t.idx === S.focus && S.mode === "trade") { const r = F.open.r, vs = voiceStop(F.open.t, F.T);   // A55 + F9 (25 Oct): the voice's stop, or no STOP line
        lines.push({ k: "entry", y: yOf(r.e.spot), side: "R", a: `ENTRY ${fmt(r.e.spot)} ${hm(r.e.t0)}`, b: `fut ${fmt(r.e.fut)}`, off: off(r.e.spot) }); if (vs.s != null) lines.push({ k: "g", y: yOf(vs.s), side: "R", a: `STOP ${fmt(vs.s)}`, b: `fut ${fmt(vs.f)}`, off: off(vs.s) }); }
      // labels: nudge apart per side so none overlap (the line itself stays at its true price)
      const gap = 29 / Math.max(300, innerHeight - (S.consoleMin ? 120 : 254)) * 100;
      for (const sd of ["ALL"]) { const ls = lines.slice().sort((p, q) => p.y - q.y); for (const l of ls) l.ly = l.y; for (let n = 1; n < ls.length; n++) if (ls[n].ly - ls[n - 1].ly < gap) ls[n].ly = ls[n - 1].ly + gap; for (let n = ls.length - 1; n >= 0; n--) { if (ls[n].ly > 100 - gap / 2) ls[n].ly = 100 - gap / 2; if (n < ls.length - 1 && ls[n + 1].ly - ls[n].ly < gap) ls[n].ly = ls[n + 1].ly - gap; } }
    }
    return html`<div class="pane">
      <div class="vp-tools">
        <div class="seg">${IDX.map(i => html`<button key=${i} class=${S.focus === i ? "on" : ""} onClick=${() => selectIdx(i)}>${i}</button>`)}</div>
        <span class="f" style="margin-left:6px" data-tip="the Δ column: OI change against 15 minutes ago, or against the open [M]">Δ vs</span>
        <div class="seg">${[["15m", "15 min"], ["open", "open"]].map(([k, l]) => html`<button key=${k} class=${S.oiRef === k ? "on" : ""} onClick=${() => { S.oiRef = k; up(); }}>${l}</button>`)}</div>
        <span class="f" style="margin-left:6px" data-tip="strikes shown around the ATM; the recorder keeps ±8">window</span>
        <div class="seg">${[[6, "±6"], [8, "±8"]].map(([k, l]) => html`<button key=${k} class=${S.win === k ? "on" : ""} onClick=${() => { S.win = k; up(); }}>${l}</button>`)}</div>
        <span class="sp"></span>
        <div class="lg"><span data-tip="CE writers' OI, bar grows left from the strike"><i style="background:var(--ce)"></i>CE</span><span data-tip="PE writers' OI, bar grows right from the strike"><i style="background:var(--pe)"></i>PE</span><span data-tip="dashed outline = the strike's day-peak OI; the gap is what left"><i style="border:1px dashed var(--ghost);background:none"></i>peak</span>${g ? html`<span data-tip="a wall building for you"><i style="background:var(--blue)"></i>with</span><span data-tip="a wall against you (behind you leaving, or ahead building)"><i style="background:var(--red)"></i>against</span><span data-tip="a wall that stopped"><i style="background:var(--amber)"></i>flat</span>` : null}</div>
        ${F.stale && s.ok ? html`<span class="ch ch-r" style="margin-left:8px">frozen ${hms(F.ft)}</span>` : null}
      </div>
      <div class="ladder-wrap">
        <div class="lhead"><div class="ce">CE writers · OI [M] · Δ</div><div class="k">strike</div><div class="pe">OI [M] · Δ · PE writers</div><div class="lane" data-tip="level labels live here so they never cover a bar or a number; the line crosses the ladder at its true price">levels</div></div>
        <div class="ladder">
          ${ks.map((K, r) => { const ki = x.ks.indexOf(K); const tags = tagsFor(K); return html`<div key=${K} class=${`lrow ${s.ok && K === s.atm ? "atm" : ""}`}>
            ${side("ce", K, ki)}
            <div class="k" data-tip=${`${K} · ${s.ok ? (K === s.atm ? "ATM" : K > s.spot ? `${fmt(K - s.spot)} above spot` : `${fmt(s.spot - K)} below spot`) : ""} · fut-frame ${s.ok ? fmt(K + s.basis) : "—"}`}><span class="kv">${fmt(K)}</span>${tags.length ? html`<span style="display:flex;gap:2px">${tags.map(([c, l, t]) => html`<span key=${c} class=${`tag ${c}`} data-tip=${t}>${l}</span>`)}</span>` : null}</div>
            ${side("pe", K, ki)}
            <div class="lane"></div>
          </div>`; })}
          ${lines.map(l => html`<div key=${l.k} class=${`lline ${l.k}`} style=${`top:${l.y}%`}><s></s><b style=${`top:${(l.ly - l.y) / 100 * Math.max(300, innerHeight - (S.consoleMin ? 120 : 254)) - 12}px`} data-tip=${`${l.a} spot · ${l.b}${l.off ? " · off the ladder window" : ""}`}><span>${l.off ? (l.y < 50 ? "↑ " : "↓ ") : ""}${l.a}</span><span>${l.b}</span></b></div>`)}
          ${!s.ok ? html`<div class="ladder-empty"><div class="big">chain not posted yet</div><div>first row at ${x.t.length ? hms(x.t[0]) : "—"} · the recorder starts ~2 min after the open</div></div>` : null}
        </div>
      </div>
    </div>`;
  }
  const lastLEidx = (arr, v) => { let lo = 0, hi = arr.length - 1, r = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (arr[m] <= v) { r = m; lo = m + 1; } else hi = m - 1; } return r; };

  // ---------- inspector ----------
  function Inspector({ F }) {
    const title = S.about ? "About" : S.mode === "read" ? `Market read · ${S.focus}` : S.mode === "validate" ? "Validate" : "In trade";
    return html`<div class="pane">
      <div class="pane-h">${title}<span class="sp"></span><span class="r">${S.mode === "read" ? html`<kbd class="k">R</kbd> press` : S.mode === "validate" ? html`<kbd class="k">Enter</kbd> validate · <kbd class="k">M</kbd> mark` : html`${F.open ? "every second" : "no trade"}`}</span></div>
      <div class="pane-b scroll insp">${S.about ? html`<${About}/>` : S.mode === "read" ? html`<${ReadPanel} F=${F}/>` : S.mode === "validate" ? html`<${ValidatePanel} F=${F}/>` : html`<${TradePanel} F=${F}/>`}</div>
    </div>`;
  }
  function About() {
    return html`<div style="padding:10px 12px;display:grid;gap:8px;line-height:1.45">
      <div><b>Prototype logic over real data.</b> Every number is [M] from TapeMap's recorder for 2026-10-06 (chain every ~10 s, futures ticks, VPIN buckets). Every state word is [I] prototype logic that mirrors DESIGN.md §2–§6: fronts.py's BUILDING / STALLED / UNWINDING, fold's chips and give-up, daytype's IB, xindex's TOOK / FAILED. The live engine's own words are not wired here — see NOTES.md.</div>
      <div class="sec" style="padding:0">Keyboard</div>
      <div class="n" style="display:grid;grid-template-columns:auto 1fr;gap:3px 12px;font-size:10.5px">
        <kbd class="k">Ctrl K</kbd><span>command palette</span><kbd class="k">1 2 3</kbd><span>market read · validate · in trade</span><kbd class="k">Space</kbd><span>play / pause</span><kbd class="k">← →</kbd><span>step 1 s (Shift: 1 min)</span><kbd class="k">[ ]</kbd><span>speed 1× · 10× · 60×</span><kbd class="k">R</kbd><span>press the market read</span><kbd class="k">Enter</kbd><span>validate the slip</span><kbd class="k">M</kbd><span>mark the slip as a trade now</span><kbd class="k">\`</kbd><span>console</span><kbd class="k">Esc</kbd><span>close</span></div>
      <div class="sec" style="padding:0">Colour</div>
      <div><span class="ch ch-WITH">with</span> saath · <span class="ch ch-AGAINST">against</span> khilaaf · act now · <span class="ch ch-a">look</span> out of the ordinary · <span class="ch ch-NEITHER">nothing</span> checked, found nothing · <span class="ch ch-CNC">can't check</span> · <span class="ch ch-NS">not shown</span></div>
      <button class="btn" onClick=${() => { S.about = false; up(); }}>${icon("x")} close</button>
    </div>`;
  }
  // -- market read
  function ReadPanel({ F }) {
    const r = F.read; if (!r || !r.ok) return html`<div class="notrade"><div class="big">${r ? r.word : "—"}</div><div>${F.s.x.t.length ? `first chain row ${hms(F.s.x.t[0])}` : ""}</div></div>`;
    const pressed = S.pressed && S.pressed.idx === r.idx ? S.pressed : null;
    const changed = pressed ? r.rows.filter(row => { const p = pressed.rows.find(q => q.k === row.k); return p && p.cell !== row.cell; }) : [];
    const chg = new Set(changed.map(c => c.k));
    return html`<div>
      <div class="word"><span class=${`w ${r.word.split(" ")[0]}`}><${Val} v=${r.word} tone=${/TREND|PRESSING/.test(r.word) ? "a" : "n"}/></span><span class="sub"><${Val} v=${r.sub} tone="n"/></span></div>
      <div class="counts"><span class="f">${pressed ? `pressed ${hms(pressed.T)} · ` : "not pressed yet · "}</span><button class="btn" style="height:20px;padding:0 8px" onClick=${press}>${icon("radio")} press</button><span class="f" style="margin-left:auto">${F.stale ? html`<span class="ch ch-CNC">can't check · feed</span>` : "live · 1 s"}</span></div>
      <div class="rows">${r.rows.map(row => html`<div key=${row.k} class=${`rd ${row.abs === "cnc" ? "cnc" : ""} ${chg.has(row.k) ? "chg" : ""}`} data-tip=${row.tip + (row.abs === "cnc" ? " · check nahi" : row.abs === "checked" ? " · checked, kuch nahi" : "")}><span class="l">${row.k}</span><div class="rc">
        ${row.fronts ? (row.fronts.length ? row.fronts.map(f => html`<span key=${f.text} class="fr" data-tip=${f.tip}><span class="n"><${Val} v=${f.text}/></span><${Pill} p=${f.pill}/></span>`) : html`<${Chip} st="NEITHER" text="checked · none"/>`) : null}
        ${row.pill ? html`<${Pill} p=${row.pill}/>` : null}${row.cells.map((cx, n) => html`<span key=${n} class="n"><${Val} v=${cx} tone=${row.pill && row.pill.tone === "a" ? "a" : "n"}/></span>`)}
        ${row.k === "DAY" && S.flat[r.idx] && typeof S.flat[r.idx].day === "string" ? html`<span class="n" data-tip="the engine's own day line (GET /api/fold/flat · fold.State.flat_view.day): fights won, value, where price sits" style="color:var(--ink2)">${icon("radio")} ${S.flat[r.idx].day}</span>` : null}
      </div></div>`)}</div>
      <div class="sec">Levels to watch <span class="r">spot / fut · confirms · denies</span></div>
      ${r.levels.map((l, n) => html`<div key=${n} class="lw" data-tip=${`${l.what} · ${fmt(l.spot)} spot / ${fmt(l.fut)} fut [M] · confirms: ${l.conf[1]} · denies: ${l.deny[1]}`}><span class="ar">${l.spot > r.s.spot ? icon("arrow-up") : icon("arrow-down")}</span><div><div class="px"><${Val} v=${fmt(l.spot)}/><span class="f">s</span> · <${Val} v=${fmt(l.fut)}/><span class="f">f</span> <span class="wh" style="margin-left:6px">${l.what}</span></div><div class="cd"><span class="ok">${icon(l.conf[0])}${l.conf[1]}</span><span class="no">${icon(l.deny[0])}${l.deny[1]}</span></div></div></div>`)}
      <div class="sec">Yeh read badlega agar</div>
      <div style="padding:0 12px;display:grid;gap:2px">${r.falsifiers.map((f, n) => html`<div key=${n} class="n" style="font-size:10.5px;display:flex;gap:6px;align-items:center">${icon("flag")}${f}</div>`)}</div>
      ${pressed ? html`<div class=${`diff ${changed.length ? "" : "none"}`}><span class="l">changed since ${hms(pressed.T)} press</span>${changed.length ? changed.map(c => html`<div key=${c.k}><b>${c.k}</b> <span class="n">${c.cell}</span> <span class="f">was</span> <span class="n">${pressed.rows.find(q => q.k === c.k).cell}</span></div>`) : html`<div>nothing moved</div>`}</div>` : null}
    </div>`;
  }
  // -- validate
  function Slip({ F }) {
    const sl = S.slip, s = F.snaps[sl.idx];
    const ks = s.ok ? s.x.ks : [];
    const set = (k, v) => { S.slip = Object.assign({}, S.slip, { [k]: v }); if (k !== "px") S.slip.px = ""; up(); };
    return html`<div class="slip">
      <div class="fld sel"><label>index</label><select value=${sl.idx} onChange=${e => set("idx", e.target.value)}>${IDX.map(i => html`<option key=${i} value=${i}>${i}</option>`)}</select></div>
      <div class="fld sel"><label>strike</label><select value=${String(sl.K)} onChange=${e => set("K", Number(e.target.value))}>${(ks.includes(Number(sl.K)) ? ks : [Number(sl.K), ...ks]).map(k => html`<option key=${k} value=${k}>${k}${s.ok && k === s.atm ? " ATM" : ""}</option>`)}</select></div>
      <div class="fld"><label>type</label><div class="tg" style="flex:1;height:100%">${["CE", "PE"].map(t => html`<button key=${t} class=${sl.ty === t ? "on" : ""} onClick=${() => set("ty", t)}>${t}</button>`)}</div></div>
      <div class="fld"><label>side</label><div class="tg" style="flex:1;height:100%">${["BUY", "SELL"].map(t => html`<button key=${t} class=${sl.side === t ? "on" : ""} onClick=${() => set("side", t)}>${t}</button>`)}</div></div>
      <div class="fld" style="grid-column:1/-1"><label>price</label><input type="text" inputmode="decimal" value=${sl.px} placeholder=${F.val && F.val.ltp != null ? `LTP ${fmt(F.val.ltp, 2)}` : "LTP"} onInput=${e => { S.slip.px = e.target.value.replace(/[^0-9.]/g, ""); up(); }} onKeyDown=${e => { if (e.key === "Enter") { e.preventDefault(); e.target.blur(); } }}/><span class="f" style="padding:0 6px">${sl.px === "" ? "defaults to LTP" : ""}</span></div>
      <div class="go"><button class="pri" onClick=${() => up()}>${icon("check")} VALIDATE <kbd class="k" style="color:#fff;border-color:rgba(255,255,255,.4)">Enter</kbd></button><button class="sec2" onClick=${markTrade} data-tip="mark this slip as a trade at the replay time">${icon("flag")} mark <kbd class="k">M</kbd></button></div>
    </div>`;
  }
  function ValidatePanel({ F }) {
    const v = F.val;
    return html`<div>
      <${Slip} F=${F}/>
      ${!v || !v.ok ? html`<div class="notrade"><div class="big">—</div><div>${v ? v.why : ""}</div></div>` : html`
        <div class="word"><span class=${`w ${F.stale ? "" : v.word}`}><${Val} v=${F.stale ? "CAN'T CHECK" : v.word} tone=${TONE[v.word]}/></span><span class="hi">${F.stale ? "check nahi" : v.hi}</span><span class="sub"><${Val} v=${v.why} tone="n"/></span></div>
        <div class="counts" data-tip="a count, not odds · with = saath · against = khilaaf · neither = checked, found nothing · could not check">
          <span class="c w">${icon("check")}<span class="n"><${Val} v=${v.counts.w} tone="b"/></span> with</span><span class="c a">${icon("x")}<span class="n"><${Val} v=${v.counts.a} tone="r"/></span> against</span><span class="c nn">${icon("minus")}<span class="n"><${Val} v=${v.counts.n} tone="g"/></span> neither</span><span class="c cc">${icon("circle-help")}<span class="n"><${Val} v=${v.counts.c} tone="g"/></span> can't</span><span class="of">of ${v.counts.of}</span>
        </div>
        ${v.word === "GO" || v.strongest ? html`<div class=${`strong ${v.strongest ? "" : "none"}`}><span class="l">${v.strongest ? "strongest against" : "against"}</span><span class="n" style="min-width:0">${v.strongest ? `${v.strongest.name} · ${v.strongest.cell}` : `nothing · ${v.counts.c} could not check`}</span></div>` : null}
        <div class="sec" data-tip=${`VALIDATE rev ${v.rev || "?"} (docs/hold/VALIDATE-PREREG-rev3.md): VPIN printed, never counted · GO needs 6 with, 0 against, ≤ 1 can't`}>Checks · rev ${(v.rev || "?").split(" ")[0]} <span class="r">${v.counts.of} counted${v.role === "sell" ? " (writer)" : ""} · VPIN printed · [M]/[I] in hover</span></div>
        <div class="rows">${v.checks.map(c => html`<div key=${c.name} class=${`row ${c.st === "CNC" ? "cnc" : c.st === "NS" || c.st === "PR" ? "ns" : ""} ${c.flag ? "flag-" + c.flag : ""}`} data-tip=${c.tip}><span class="l">${c.name}</span><span class="c"><${Val} v=${c.cell} tone=${TONE[c.st]}/></span><${Chip} st=${F.stale ? "CNC" : c.st}/></div>`)}</div>
        <div class="sec">Printed, never counted</div>
        <div class="rows">
          <div class="row" data-tip=${v.printed.moneyness ? `delta ${v.printed.moneyness.delta.toFixed(2)} · intrinsic ${fmt(v.printed.moneyness.intrinsic, 1)} · time value ${fmt(v.printed.moneyness.tv, 1)} [I from the chain's delta]${v.printed.moneyness.deep ? " · deep ITM = a futures position in option's clothing" : ""}` : "could not check: no delta on this row"}><span class="l">moneyness</span><span class="c">${v.printed.moneyness ? html`<${Val} v=${`δ ${v.printed.moneyness.delta.toFixed(2)} · TV ${fmt(v.printed.moneyness.tv, 1)} of ${fmt(v.ltp, 2)}`} tone=${v.printed.moneyness.deep ? "a" : "n"}/>` : "—"}</span>${v.printed.moneyness ? (v.printed.moneyness.deep ? html`<span class="ch ch-a" data-tip="deep ITM: a futures position in option's clothing — |δ| ≥ 0.85">deep ITM</span>` : html`<span class="ch ch-n">${Math.abs(v.printed.moneyness.delta) >= 0.6 ? "ITM" : Math.abs(v.printed.moneyness.delta) >= 0.4 ? "ATM" : "OTM"}</span>`) : html`<${Chip} st="CNC"/>`}</div>
          <div class="row" data-tip=${`${hms(v.printed.clock.T)} · ${v.s.dte === 0 ? "expiry day: time value burns to 0 by 15:30" : "expiry " + v.s.expiry} · your 15:00 practice is a reminder, it blocks nothing`}><span class="l">clock</span><span class="c"><${Val} v=${`${v.s.dte === 0 ? "0DTE" : v.s.dte + " DTE"} · ${Math.max(0, Math.round((CLOSE - F.T) / 60))} min · ${F.T >= PRACTICE ? "past 15:00" : `15:00 in ${Math.round((PRACTICE - F.T) / 60)} min`}`} tone=${F.T >= 14 * 3600 + 45 * 60 ? "a" : "n"}/></span><span class="ch ch-n">${v.s.dte === 0 ? "theta" : "time"}</span></div>
          <div class="row" data-tip="ltp ≥ 1.3 × the day's traded average = writers under water; ≤ 0.8 × = comfortable [I: avg is the day's average, chain_metrics' proxy] · the side in pain must move"><span class="l">who is in pain</span><span class="c ui">${v.printed.pain.map(p => html`<span key=${p.k + p.leg} style="margin-right:8px">${p.k} ${p.leg} <span class="n">${fmt(p.ltp, 1)}/${fmt(p.avg)}</span> <span class=${p.word === "under water" ? "cr" : p.word === "comfortable" ? "cb" : "f"}>${p.word}</span></span>`)}</span><span></span></div>
          <div class="row" data-tip="PE / CE OI over the nine strikes around ATM [M] · now · an hour ago · at 09:30"><span class="l">PCR(9)</span><span class="c"><${Val} v=${v.printed.pcr.now && v.printed.pcr.now.r != null ? `${v.printed.pcr.now.r.toFixed(2)} · ${v.printed.pcr.h1 && v.printed.pcr.h1.r != null ? v.printed.pcr.h1.r.toFixed(2) + " 1h ago" : "—"}` : "—"}/></span><span></span></div>
        </div>
        <div class="sec">Levels <span class="r">spot · fut · premium [I]</span></div>
        <div class="lv h"><span></span><span>spot</span><span>fut</span><span>prem ≈</span></div>
        ${v.levels.map(l => html`<div key=${l.name} class="lv" data-tip=${l.absence ? `checked, found nothing: ${l.why}` : `${l.name} · ${l.why}${l.who ? " · " + l.who : ""} · ${l.pts != null ? (l.pts > 0 ? "+" : "") + fmt(l.pts) + " pts fut" : ""} · premium there ≈ ${l.prem == null ? "—" : fmt(l.prem, 1)} [I: delta-interpolated]`}><span class=${`nm ${l.name === "STOP" ? "stop" : "t"}`}>${l.name}</span>${l.absence ? html`<span class="abs" style="grid-column:2/-1"><${Chip} st="NEITHER" text="checked · none"/> ${l.why}</span>` : html`<span><${Val} v=${fmt(l.spot)}/></span><span><${Val} v=${fmt(l.fut)}/></span><span><${Val} v=${l.prem == null ? "—" : fmt(l.prem, 1)}/></span><span class="why ell">${l.why}${l.pts != null ? ` · ${l.pts > 0 ? "+" : ""}${fmt(l.pts)} pts` : ""}</span>`}</div>`)}
        <${Board} F=${F}/>`}
    </div>`;
  }
  function Board({ F }) {
    const b = F.board, v = F.val; if (!b) return null;
    const better = b.better;
    return html`<div>
      <div class="sec">Better trade <span class="r">18 candidates · word, more with, fewer against, fewer can't</span></div>
      <div class=${`better ${better ? "" : "none"}`} data-tip=${better ? `${better.side} ${better.idx} ${better.K} ${better.ty} @${fmt(better.ltp, 2)} · ${better.word} ${better.counts.w} with · ${better.counts.a} against · ${better.counts.n} neither · ${better.counts.c} can't · against: ${better.checks.filter(c => c.st === "AGAINST").map(c => c.name).join(", ") || "nothing"}` : b.verdict}>
        <span class="l">${better ? "better" : "board"}</span>
        <span class="b"><${Val} v=${better ? `${better.side} ${better.idx} ${fmt(better.K)} ${better.ty} @${fmt(better.ltp, 1)} · ${better.word}` : b.verdict} tone=${better ? "b" : "g"}/></span>
        <span class="f" style="color:inherit"><${Val} v=${better ? E.reason(better) : `your rank ${b.herRank} of ${b.cands.length}`} tone="n"/></span>
      </div>
      <div class="rows">${b.cands.slice(0, 8).map((c, n) => html`<div key=${c.idx + c.K + c.ty + c.side} class=${`brd ${c.idx === v.idx && c.K === v.K && c.ty === v.ty && c.side === v.side ? "hers" : ""}`} data-tip=${`${c.side} ${c.idx} ${c.K} ${c.ty} ${c.m} @${fmt(c.ltp, 2)} · ${c.word} · against: ${c.checks.filter(q => q.st === "AGAINST").map(q => q.name).join(", ") || "nothing"} · ${E.HI[c.word]}`}><span class="rk">${n + 1}</span><${Chip} st=${c.word} text=${c.word}/><span class="nm">${c.side} ${c.idx} ${fmt(c.K)} ${c.ty} <span class="f">${c.m}</span></span><span class="cnt">${c.counts.w}w ${c.counts.a}a ${c.counts.n}n ${c.counts.c}c</span></div>`)}
        ${b.herRank > 8 ? html`<div class="brd hers"><span class="rk">${b.herRank}</span><${Chip} st=${v.word} text=${v.word}/><span class="nm">${v.side} ${v.idx} ${fmt(v.K)} ${v.ty} <span class="f">yours</span></span><span class="cnt">${v.counts.w}w ${v.counts.a}a ${v.counts.n}n ${v.counts.c}c</span></div>` : null}
      </div>
      ${b.slots ? html`<div class="sec">Named slots</div><div class="rows">${[["same thesis, better expression", b.slots.same], ["opposite thesis", b.slots.opp], ["other index", b.slots.oth]].map(([l, c]) => html`<div key=${l} class="row" data-tip=${c ? `${c.side} ${c.idx} ${c.K} ${c.ty} @${fmt(c.ltp, 2)} · against: ${c.checks.filter(q => q.st === "AGAINST").map(q => q.name).join(", ") || "nothing"}` : "checked: no candidate fits this slot"}><span class="l" style="font-size:9px">${l}</span><span class="c">${c ? html`<${Val} v=${`${c.side} ${c.idx} ${fmt(c.K)} ${c.ty} · ${c.counts.w}w/${c.counts.a}a`}/>` : html`<${Chip} st="NEITHER" text="none"/>`}</span>${c ? html`<${Chip} st=${c.word} text=${c.word}/>` : html`<span></span>`}</div>`)}</div>` : null}
    </div>`;
  }
  // -- in trade
  function TradePanel({ F }) {
    const o = F.open;
    if (!o) {
      const last = F.lastTrade;
      if (!(last && last.r.ok)) return html`<div class="notrade">
        <div class="big">no trade</div>
        <div>${S.live ? "Mark the slip (the same door the DESK uses) and this panel reads it every second: the engine's word, the four reads, the W-bleed meter, distance to stop, and KYA BADLA SINCE ENTRY." : `No marked trade in the record for ${S.day || E.data.day}.`}${S.apiWhy ? html`<div class="ca" style="margin-top:4px">${S.apiWhy}</div>` : null}</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn pri" onClick=${() => { S.mode = "validate"; up(); }}>${icon("check")} open the slip</button><button class="btn" onClick=${markTrade}>${icon("flag")} mark now <kbd class="k">M</kbd></button></div>
      </div>`;
      const t = last.t, ft = F.ft, ex = E.inTrade(t, last.r.foldT, Math.max(ft, last.r.foldT)), evs = E.tradeEvents(t, 1e9), gu = evs.find(e => /^GAVE UP/.test(e.text)), bl = evs.find(e => /^W-bleed/.test(e.text));
      const pnl = pnlOf(t, ex);
      return html`<div class="notrade" style="padding-top:10px">
        <div class="big">flat <span class="f" style="font-size:12px;font-weight:500">· last trade, recap</span></div>
        <div class="recap">
          <div class="hd"><span class="nm">${t.side === "BUY" ? "LONG" : "SHORT"} ${t.idx} ${fmt(t.K)} ${t.ty}</span><span class="n">${hms(t.t0)} @${fmt(ex.e.prem, 2)} → ${hm(last.r.foldT)} @${fmt(ex.prem, 2)}</span><span class=${`n b ${pnl >= 0 ? "cb" : "cr"}`}>${sgn(pnl)}</span></div>
          <div class="rr"><span class="l">word at exit</span><span class="n">${(() => { const ew = engineWord(t, last.r.foldT - 1, ex); return html`<${Chip} st=${ew.key === "FOLD" ? "FOLD" : ew.key === "HOLD" ? "WITH" : "NEITHER"} text=${ew.src === "prototype" && ew.key === "OUT" ? "—" : ew.headline.split(" · ")[0]}/> ${ew.src} · ${(t.exitWhy || ew.sub || "").replace(/^FOLD · /, "")}`; })()}</span></div>
          <div class="rr"><span class="l">reads at exit</span><span class="pills">${["ZONE", "FLOW", "OI", "VPIN"].map(k => html`<span key=${k} class=${`ch ch-${ex.chips[k]}`}>${k} ${ex.chips[k] === "CNC" ? "can't" : ex.chips[k].toLowerCase()}</span>`)}</span></div>
          <div class="rr"><span class="l">premium</span><span class="n">peak ${fmt(ex.peakP.v, 2)} at ${hm(ex.peakP.t)} · gave back ${fmt(ex.peakP.v - ex.prem, 2)} · out ${fmt(ex.prem, 2)}</span></div>
          <div class="rr"><span class="l">gave up said</span><span class="n">${gu ? `${hm(gu.t)} · ${gu.text.replace(/^GAVE UP · /, "")}` : "never printed"}${bl ? html`<br/><span class="ca">${hm(bl.t)} · ${bl.text}</span>` : null}</span></div>
          <div class="rr"><span class="l">wall at exit</span><span class="n">${ex.W ? `${ex.W.k} ${ex.W.leg.toUpperCase()} ${L(ex.W.oi)} · ${pct(ex.W.off)} off its ${L(ex.W.peak)} peak` : "—"}</span></div>
          ${(() => { const rc = S.fold[t.id] && S.fold[t.id].receipt; return rc && rc.text ? html`<div class="rr" data-tip="A52: the three HOLD v3 shadow lines (holdshadow.py, shadow, never a rule), shown only after you are out · from data/hold/shadow_<day>.jsonl"><span class="l">receipt</span><span class="n">${rc.text}${rc.why ? html`<br/><span class="ca">${rc.why}</span>` : null}</span></div>` : null; })()}
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn pri" onClick=${() => replayTrade(t)} data-tip=${`jump the clock to ${hms(t.t0)} at 1× and read the trade live`}>${icon("play")} Replay this trade</button><button class="btn" onClick=${() => { S.mode = "validate"; up(); }}>${icon("check")} open the slip</button><button class="btn" onClick=${markTrade}>${icon("flag")} mark now <kbd class="k">M</kbd></button></div>
      </div>`;
    }
    const r = o.r, t = o.t, W = r.W, offPct = W ? W.off : 0;
    const chipTip = { ZONE: "zone: your side's last win, intact or accepted against you", FLOW: "order flow: who won the last fight (30 min)", OI: "the wall behind you: building / off / stopped", VPIN: "toxic one-sided flow in the last 10 buckets (NIFTY-only, shadow)" };
    // A52 THE ONE VOICE (server voice.py, on /api/fold?id=): one word, one stop, one reason on top; [detail ▸] opens the rest.
    // A56: off the live clock it is the replayed path's latest minute ≤ T (GET /api/voice_path), what she saw live
    const vc = voiceAt(t, F.T), vp = !(S.live && S.liveFollow) && S.vpath[t.id];
    const voiceEl = vc ? html`<div class=${`voice v-${vc.state}`} data-tip=${(vc.active || []).map(a => `${a.t} ${a.state} · ${a.reason}`).join(" | ") || vc.note}>
      <div class="v1 n">${vc.l1}</div><div class="v2 n"><b class="vw">${vc.state}</b>${vc.l2}</div>
      <div class="v3">${vc.l3}${vc.trig_t && vc.state !== "HOLD" ? ` · ${vc.trig_t}` : ""}</div>${vc.l4 ? html`<div class="v3 v4">${vc.l4}</div>` : null}${vc.l5 ? html`<div class="v3 v5">${vc.l5}</div>` : null}
      <button class="vd" onClick=${() => { S.vOpen = !S.vOpen; try { localStorage.setItem("v2.vdet", S.vOpen ? "1" : "0"); } catch (e) { /* storage blocked */ } up(); }}>detail ${S.vOpen ? "▾" : "▸"}</button></div>` : null;
    const mapEl = vc && vc.detail && vc.detail.length ? html`<div class="rows">${vc.detail.map(x => html`<div key=${x.text} class="row" data-tip=${x.tip || "the trade map [I] · display only"}><span class="c" style="grid-column:1/-1">${x.text}</span></div>`)}</div>` : null;
    const vWhy = !vc && vp && !vp.ok ? html`<div class="counts" data-tip="A56: the voice replayed over this trade, GET /api/voice_path"><span class="ca">voice: ${vp.why || "could not check — no replay yet"}</span></div>` : null;
    const actions = html`<div style="display:flex;gap:6px;padding:8px 12px 0"><button class="btn" onClick=${() => setMode("read")}>${icon("radio")} market read</button><button class="btn" onClick=${() => setMode("validate")}>${icon("check")} validate another</button>${S.live && !S.closed ? html`<button class=${`btn ${S.arm === t.id ? "pri" : ""}`} onClick=${() => exitTrade(t)} data-tip="I'M OUT: two presses 5 s apart · the same /api/hold/trades door the DESK uses · a record of what you did on your broker, never an order">${icon("flag-off")} ${S.arm === t.id ? "press again: I'm out" : "I'm out"}</button>` : null}</div>`;
    if (vc && !S.vOpen) return html`<div>${voiceEl}${actions}</div>`;   // I'M OUT and the two buttons stay one press away
    return html`<div>${voiceEl}${mapEl}${vWhy}
      ${(() => { const ew = engineWord(t, F.T, r); return html`
      <div class="word"><span class=${`w ${ew.key}`}><${Val} v=${F.stale ? "CAN'T CHECK" : ew.headline} tone=${TONE[ew.key]}/></span><span class="hi" data-tip=${ew.tip}>${ew.src}${E.HI[ew.key] ? " · " + E.HI[ew.key] : ""}</span><span class="sub"><${Val} v=${ew.sub} tone="n"/></span></div>
      <div class="counts" data-tip="the prototype's own reads (engine.js, labelled [I]): never the decision, printed beside the engine's word"><span class="f">prototype:</span><${Chip} st=${r.word === "GAVE UP" ? "AGAINST" : r.word === "FOLD" ? "FOLD" : r.word === "HOLD" ? "WITH" : "NEITHER"} text=${r.word === "OUT" ? "OUT · her exit" : r.word}/><span class="n f">${protoSub(t, F.T, r)}</span></div>`; })()}
      <div class="counts" style="font-size:12.5px"><span class="n b">${t.side === "BUY" ? "LONG" : "SHORT"} ${t.idx} ${fmt(t.K)} ${t.ty}</span><span class="n">@${fmt(r.e.prem, 2)} → <${Val} v=${fmt(r.prem, 2)} tone=${pnlOf(t, r) >= 0 ? "b" : "r"}/> <span class=${pnlOf(t, r) >= 0 ? "cb" : "cr"}><${Val} v=${sgn(pnlOf(t, r))} tone=${pnlOf(t, r) >= 0 ? "b" : "r"}/></span></span><span class="n f">peak ${fmt(r.peakP.v, 2)} ${hm(r.peakP.t)}</span><span class="n f">${hm(t.t0)} · ${fmtAge(r.tInTrade)}</span></div>
      <div class="fr">${["ZONE", "FLOW", "OI", "VPIN"].map(k => html`<div key=${k} class=${`cell ${r.chips[k]}`} data-tip=${`${chipTip[k]} · ${E.HI[r.chips[k]] || ""}`}><span class="l">${k === "FLOW" && r.flowSrc ? `${r.flowSrc} FLOW` : k}</span><span class="b" style="font-size:11px"><${Val} v=${r.chips[k] === "CNC" ? "can't" : r.chips[k].toLowerCase()} tone=${TONE[r.chips[k]]}/></span></div>`)}</div>
      ${(() => { const f = S.fold[t.id], h2 = S.live && f && f.ok ? f.hold2 : null; if (!h2) return null;
        // A52: the CHOP / POP / EFFORT shadow lines are not shown while she is in (logged, then on the receipt after her exit)
        return html`<div class="sec" data-tip="HOLD v2 (§1m, display only)">HOLD v2 <span class="r">display only</span></div>
        <div class="rows"><div class="row" data-tip=${h2.why || h2.note || ""}><span class="l">HOLD v2</span><span class="c">${h2.ok && h2.text ? h2.text.replace(/^HOLD v2 · /, "") : (h2.why || "could not check — no HOLD v2 line yet")}</span><span></span></div></div>`; })()}
      ${r.zoneAlone ? html`<div class="zone" data-tip="the zone is the only thing behind you: OI quiet and flow not with you for 2+ buckets · shown, never a fold (DESIGN §5.3) · losers held here and winners ran from here · your call"><span class="l">zone alone</span><span style="min-width:0">only the zone behind you · OI ${r.chips.OI.toLowerCase()} · ${r.flowSrc ? `${r.flowSrc} flow` : "flow"} ${r.chips.FLOW.toLowerCase()} · the engine's fold has not come</span></div>` : null}
      <div class="sec">W off peak <span class="r">${W ? `${W.k} ${W.leg.toUpperCase()} · peak ${L(W.peak)} ${hm(W.peakT)}` : "no wall"}</span></div>
      <div class="meter" data-tip=${W ? `${W.k} ${W.leg.toUpperCase()} writers ${L(W.oi)} vs peak ${L(W.peak)} at ${hm(W.peakT)} · ${pct(W.off)} off · ${W.upd} updates since · amber at ≥ 10 % with ≥ 15 updates: the slow leak the z/√n event misses [M]` : "no wall behind"}><span class="l">${W ? `${W.k} ${W.leg.toUpperCase()}` : "—"}</span><div class="trk"><i class=${W && W.bleed ? "a" : W && W.state === "UNWINDING" ? "r" : ""} style=${`transform:scaleX(${Math.min(1, offPct / 0.25).toFixed(4)})`}></i><b style="left:40%"></b></div><span class="v2"><${Val} v=${W ? `−${(offPct * 100).toFixed(1)} %` : "—"} tone=${W && W.bleed ? "a" : "n"}/> <span class="f">${W ? `${W.upd} upd` : ""}</span></span></div>
      ${(() => { const vs = voiceStop(t, F.T);   // A55 + F9 (25 Oct): one stop, the voice's; without it the screen says why, never engine.js's G
        if (vs.f == null) return html`<div class="counts" data-tip="F9: the stop is the voice's (voice.py); engine.js's give-up is never shown as one"><span class="ca">stop: ${vs.why}</span></div>`;
        if (vs.s == null) { const df = Math.abs(r.s.fut - vs.f); return html`<div class="counts" data-tip=${`the voice's stop (${vs.src}) is in futures only: no spot line, none made up · one candle B = ${fmt(r.s.B, 1)}`}><span class="ca">${vs.txt}</span><span class="n f">to stop · fut <${Val} v=${fmt(Math.round(df))} tone=${df <= r.s.B ? "r" : "n"}/></span></div>`; }
        const gf = vs.f, gs = vs.s, df = Math.abs(r.s.fut - gf), ds = Math.abs(r.s.spot - gs), who = `the voice's stop: ${vs.src} line`;
        return html`<div class="dist">
        <div class="cell" data-tip=${`${who} ${fmt(gf)} fut / ${fmt(gs)} spot`}><div class="l">to stop · spot</div><div class="n"><${Val} v=${fmt(Math.round(ds))} tone=${ds <= r.s.B ? "r" : "n"}/> <span class="f" style="font-size:10px">→ ${fmt(gs)}</span></div></div>
        <div class="cell" data-tip=${`${who} ${fmt(gf)} fut · one candle B = ${fmt(r.s.B, 1)}`}><div class="l">to stop · fut</div><div class="n"><${Val} v=${fmt(Math.round(df))} tone=${df <= r.s.B ? "r" : "n"}/> <span class="f" style="font-size:10px">→ ${fmt(gf)}</span></div></div>
      </div>`; })()}
      <div class="sec">Kya badla since entry <span class="r">${hm(t.t0)} → now</span></div>
      <div class="ledg h"><span>fact · at entry → now</span><span>read</span></div>
      ${r.ledger.map(l => html`<div key=${l.fact} class=${`ledg ${l.st}`} data-tip=${l.tip + " · " + (E.HI[l.st] || "")}><span class="fa ell">${l.fact}</span><${Chip} st=${l.st} text=${l.st === "NEITHER" ? "—" : null}/><span class="vals"><span class="e">${l.entry}</span> <span class="f">→</span> <${Val} v=${l.now} tone=${TONE[l.st]}/></span></div>`)}
      ${r.theta != null ? html`<div class="rows" style="margin-top:4px"><div class="row" data-tip="expiry-day theta: time value left ÷ 15-min slots to the close [I]"><span class="l">theta / 15 min</span><span class="c"><${Val} v=${`−${fmt(r.theta, 1)} · TV ${fmt(r.g.tv, 1)} left`} tone="n"/></span><span class="ch ch-n">0DTE</span></div></div>` : null}
      ${actions}
    </div>`;
  }

  // ---------- console + timeline ----------
  function Console({ F }) {
    const logRef = useRef();
    const evs = allEvents().filter(e => e.t <= F.T).slice(-250);
    useEffect(() => { const el = logRef.current; if (el && S.follow) el.scrollTop = el.scrollHeight; });
    const ticks = allEvents().filter(e => e.tone !== "n");
    return html`<div class=${`console ${S.consoleMin ? "min" : ""}`}>
      <div class="pane-h"><button class="menu" style="padding:1px 4px;margin-left:-6px" onClick=${() => { S.consoleMin = !S.consoleMin; up(); }}>${icon(S.consoleMin ? "chevron-right" : "chevron-down")}</button>Console <span class="r">fights · walls · prints · reads · your trade</span><span class="sp"></span>
        <span class="r">${evs.length} events ≤ ${hms(F.T)}</span><span class="r"><kbd class="k">\`</kbd></span></div>
      <div class="body">
        <div class="log" ref=${logRef} onScroll=${e => { const el = e.target; S.follow = el.scrollHeight - el.scrollTop - el.clientHeight < 24; }}>
          ${evs.map((e, n) => html`<div key=${e.t + e.idx + n} class=${`ev t-${e.tone} ${F.T - e.t < 60 ? "now" : ""}`} data-tip=${`${hms(e.t)} · ${e.idx} · ${e.kind}`}><span class="t">${hms(e.t)}</span>${icon(e.icon || "circle-dot")}<span class="i">${e.idx}</span><span class="x ell">${e.text}</span></div>`)}
        </div>
        <${Timeline} F=${F} ticks=${ticks}/>
      </div>
    </div>`;
  }
  function Timeline({ F, ticks }) {
    const span = CLOSE - OPEN, pos = t => (t - OPEN) / span * 100;
    const onPt = e => { const r = e.currentTarget.getBoundingClientRect(); const f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)); goTo(Math.round(OPEN + f * span)); };
    return html`<div class="tl">
      <div class="ctl">
        <button class="ib" onClick=${() => step(-1)} data-tip="back 1 s (←) · Shift ← = 1 min">${icon("chevron-left")}</button>
        <button class=${`ib ${S.playing ? "on" : ""}`} onClick=${togglePlay} data-tip="play / pause (Space)">${icon(S.playing ? "pause" : "play")}</button>
        <button class="ib" onClick=${() => step(1)} data-tip="forward 1 s (→) · Shift → = 1 min">${icon("chevron-right")}</button>
        <div class="seg" style="margin-left:4px">${[1, 10, 60].map(sp => html`<button key=${sp} class=${S.speed === sp ? "on" : ""} onClick=${() => { S.speed = sp; up(); }}>${sp}×</button>`)}</div>
        ${S.live ? html`<button class=${`ib ${S.liveFollow ? "on" : ""}`} style="width:auto;padding:0 8px;font-weight:700;letter-spacing:.04em" onClick=${goLive} data-tip="follow the clock (L) · scrub back any time within today">LIVE</button>` : null}
        <span class="clock"><${Val} v=${hms(F.T)} tone="n"/></span>
      </div>
      <div class="scrub" onPointerDown=${e => { e.currentTarget.setPointerCapture(e.pointerId); onPt(e); }} onPointerMove=${e => { if (e.buttons & 1) onPt(e); }} data-tip="scrub 09:15 → 15:30 · ticks: amber look-now · red act · blue your trade">
        <div class="trk"></div><div class="fill" style=${`width:${pos(F.T)}%`}></div>
        ${ticks.map((e, n) => html`<i key=${n} class=${`tk ${e.tone}`} style=${`left:${pos(e.t)}%`}></i>`)}
        ${["09:15", "11:00", "13:00", "15:30"].map(l => { const [hh, mm] = l.split(":").map(Number); return html`<span key=${l} class="lab" style=${`left:${pos(hh * 3600 + mm * 60)}%`}>${l}</span>`; })}
        <div class="th" style=${`left:${pos(F.T)}%`}></div>
      </div>
      <div class="foot"><span>${S.live ? (S.liveFollow ? (S.closed ? "live · closed · last 15:30" : "live · following the clock") : `today · behind by ${fmtAge(Math.max(0, nowSec() - F.T))} · ${S.speed}× ${S.playing ? "playing" : "paused"}`) : (S.preopen ? `pre-open · last session ${E.data.day} · live from 09:15` : `replay · ${E.data.day} · ${S.speed}× ${S.playing ? "playing" : "paused"}`)}</span><span>${F.closed ? "closed · frame = last snapshot" : `${Math.round((CLOSE - F.T) / 60)} min to close`}</span></div>
    </div>`;
  }
  let EVS = null;
  function allEvents() { EVS = IDX.flatMap(i => E.events(i)).sort((a, b) => a.t - b.t); /* E.events refreshes per index on live deltas: never freeze the console at boot */ const te = S.trades.flatMap(t => E.tradeEvents(t, 1e9)); return te.length ? [...EVS, ...te].sort((a, b) => a.t - b.t) : EVS; }

  // ---------- status bar ----------
  function Status({ F }) {
    const dot = (a, slow, dead) => a == null ? "g" : a > dead ? "r" : a > slow ? "a" : "";
    const s = F.s, toClose = Math.max(0, CLOSE - F.T), toPr = PRACTICE - F.T;
    return html`<div class="status">
      <span class="ag" data-tip="age of the last futures tick [M] · amber > 10 s · red > 30 s"><span class=${`dot ${dot(F.ages.book, 10, 30)}`}></span>book <${Val} v=${fmtAge(F.ages.book)} tone=${dot(F.ages.book, 10, 30) === "r" ? "r" : dot(F.ages.book, 10, 30) === "a" ? "a" : "n"}/></span>
      <span class="ag" data-tip="age of the last chain row [M] · amber > 60 s · red > 180 s"><span class=${`dot ${dot(F.ages.chain, 60, 180)}`}></span>chain <${Val} v=${fmtAge(F.ages.chain)} tone=${dot(F.ages.chain, 60, 180) === "r" ? "r" : dot(F.ages.chain, 60, 180) === "a" ? "a" : "n"}/></span>
      <span class="ag" data-tip="age of the last VPIN bucket (NIFTY, shadow) · a bucket closes every 2–5 min"><span class=${`dot ${dot(F.ages.vpin, 300, 900)}`}></span>VPIN <${Val} v=${fmtAge(F.ages.vpin)} tone="n"/></span>
      <span class="ag" data-tip="GoCharting frame: not part of this replay (could not check)"><span class="dot g"></span>GC <span class="ch ch-CNC" style="height:13px;font-size:8.5px">n/a</span></span>
      ${s.bf ? html`<span class="ag" data-tip=${s.x.bfWhy}><span class="ch ch-a" style="height:13px;font-size:8.5px">${s.inBf ? "rebuilt minute [I]" : `morning ${s.bfFrom}–${s.bfTo} rebuilt [I]`}</span></span>` : null}
      <span class="sp"></span>
      ${F.closed ? html`<span class="pr">${S.live ? "MARKET CLOSED · last 15:30" : `REPLAY ${E.data.day} · closed`}</span>` : toPr > 0 && toPr <= 15 * 60 ? html`<span class="pr" data-tip="your practice: close before 15:00, no new trades after · a reminder, blocks nothing">${icon("timer")} 15:00 practice in ${Math.ceil(toPr / 60)} min</span>` : toPr <= 0 ? html`<span class="f">past the 15:00 practice</span>` : null}
      <span class="ag" data-tip=${`${S.focus} expiry ${s.expiry} · ${s.dte === 0 ? "today" : s.dte + " days"}`}>${icon("clock")}${S.focus} ${s.dte === 0 ? "0DTE" : s.dte + " DTE"} · <${Val} v=${`${Math.floor(toClose / 60)} min`} tone="n"/></span>
      <span class="ag"><${Val} v=${hms(F.T)} tone="n" cls="b"/></span>
      <span class="hint"><kbd class="k">Ctrl K</kbd><kbd class="k">1</kbd><kbd class="k">2</kbd><kbd class="k">3</kbd><kbd class="k">Space</kbd><kbd class="k">←</kbd><kbd class="k">→</kbd></span>
      <span class="f" data-tip="every number [M] from the recorder (GET /api/v2/data); the engine's word from /api/fold; every other word [I] prototype logic">${S.live ? "live" : S.preopen ? "pre-open · last session" : "replay"} · ${E.data.day} [M] · reads [I]</span>
    </div>`;
  }

  // ---------- command palette ----------
  const CMDS = [
    { k: "read", l: "Market read — press", d: "R", run: () => { setMode("read"); press(); } },
    { k: "validate", l: "Validate <index> <strike> <ce|pe> <buy|sell> [price]", d: "e.g. nifty 22600 ce buy 111", run: a => { if (a) { Object.assign(S.slip, a); } setMode("validate"); } },
    { k: "mark", l: "Mark the slip as a trade now", d: "M", run: markTrade },
    { k: "out", l: "I'm out — exit the open marked trade (two presses)", d: "", run: () => { const o = openTrade(); if (o) exitTrade(o); } },
    { k: "mode read", l: "Mode: market read", d: "1", run: () => setMode("read") },
    { k: "mode validate", l: "Mode: validate", d: "2", run: () => setMode("validate") },
    { k: "mode trade", l: "Mode: in trade", d: "3", run: () => setMode("trade") },
    { k: "select nifty", l: "Select NIFTY", d: "", run: () => selectIdx("NIFTY") },
    { k: "select banknifty", l: "Select BANKNIFTY", d: "", run: () => selectIdx("BANKNIFTY") },
    { k: "select sensex", l: "Select SENSEX", d: "", run: () => selectIdx("SENSEX") },
    { k: "go", l: "Go to time HH:MM[:SS]", d: "e.g. go 14:57", run: a => { if (a && a.t != null) goTo(a.t); } },
    { k: "live", l: "LIVE — follow the clock", d: "L", run: goLive },
    { k: "replay day", l: "Replay a day: replay day YYYY-MM-DD", d: "e.g. replay day 2026-10-06", run: a => { if (a && a.day) location.search = "?day=" + a.day; } },
    { k: "go 14:57", l: "Go to the 14:57 read", d: "", run: () => goTo(14 * 3600 + 57 * 60) },
    { k: "play", l: "Play", d: "Space", run: () => { S.playing = true; } }, { k: "pause", l: "Pause", d: "Space", run: () => { S.playing = false; } },
    { k: "speed 1", l: "Speed 1×", d: "", run: () => { S.speed = 1; } }, { k: "speed 10", l: "Speed 10×", d: "", run: () => { S.speed = 10; } }, { k: "speed 60", l: "Speed 60×", d: "", run: () => { S.speed = 60; } },
    { k: "feed retry", l: "Feed: retry /api/v2/data now", d: "", run: () => poll(true) },
    { k: "console", l: "Toggle the console", d: "`", run: () => { S.consoleMin = !S.consoleMin; } },
    { k: "about", l: "About: real data vs prototype logic, keyboard", d: "", run: () => { S.about = !S.about; } },
  ];
  const IDXAL = { n: "NIFTY", nifty: "NIFTY", bn: "BANKNIFTY", banknifty: "BANKNIFTY", bnf: "BANKNIFTY", sx: "SENSEX", sensex: "SENSEX" };
  function parseQ(q) {
    const t = q.trim().toLowerCase().split(/\s+/).filter(Boolean); if (!t.length) return null;
    const rd = q.trim().match(/^replay\s+day\s+(\d{4}-\d{2}-\d{2})$/i); if (rd) return { cmd: CMDS.find(c => c.k === "replay day"), arg: { day: rd[1] }, label: `Replay ${rd[1]}` };
    const m = q.trim().match(/^go\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$/i); if (m) return { cmd: CMDS.find(c => c.k === "go"), arg: { t: (+m[1]) * 3600 + (+m[2]) * 60 + (+(m[3] || 0)) }, label: `Go to ${m[1]}:${m[2]}${m[3] ? ":" + m[3] : ""}` };
    const w = t[0] === "validate" || t[0] === "mark" ? t.slice(1) : t; let idx = null, K = null, ty = null, side = null, px = "";
    for (const x of w) { if (IDXAL[x]) idx = IDXAL[x]; else if (/^\d{4,6}$/.test(x)) K = Number(x); else if (x === "ce" || x === "pe") ty = x.toUpperCase(); else if (x === "buy" || x === "sell") side = x.toUpperCase(); else if (/^\d+(\.\d+)?$/.test(x)) px = x; }
    if (K && ty) { const a = { idx: idx || S.slip.idx, K, ty, side: side || S.slip.side, px }; const isMark = t[0] === "mark"; return { cmd: isMark ? { k: "mark", l: "", run: () => { Object.assign(S.slip, a); markTrade(); } } : CMDS.find(c => c.k === "validate"), arg: a, label: `${isMark ? "Mark" : "Validate"} ${a.side} ${a.idx} ${a.K} ${a.ty}${px ? " @" + px : " @LTP"}` }; }
    return null;
  }
  function Palette() {
    const p = S.pal, q = p.q, parsed = parseQ(q);
    const items = []; if (parsed) items.push({ l: parsed.label, d: "parsed", run: () => parsed.cmd.run(parsed.arg) });
    const ql = q.trim().toLowerCase(); for (const c of CMDS) if (!ql || c.k.includes(ql) || c.l.toLowerCase().includes(ql)) items.push(c);
    const sel = Math.min(p.i, items.length - 1);
    const run = it => { S.pal = null; if (it) it.run(); up(); };
    return html`<div class="pal-bg" onMouseDown=${e => { if (e.target === e.currentTarget) { S.pal = null; up(); } }}>
      <div class="pal" role="dialog" aria-label="command palette">
        <div class="in">${icon("search")}<input autofocus placeholder="validate nifty 22600 ce buy 111 · read · mark · go 14:57 · feed dead" value=${q} ref=${el => el && !el.dataset.f && (el.dataset.f = 1, el.focus())} onInput=${e => { S.pal.q = e.target.value; S.pal.i = 0; up(); }} onKeyDown=${e => { e.stopPropagation(); if (e.key === "ArrowDown") { S.pal.i = Math.min(items.length - 1, sel + 1); up(); e.preventDefault(); } else if (e.key === "ArrowUp") { S.pal.i = Math.max(0, sel - 1); up(); e.preventDefault(); } else if (e.key === "Enter") { run(items[sel]); e.preventDefault(); } else if (e.key === "Escape") { S.pal = null; up(); } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); S.pal = null; up(); } }}/><kbd class="k">Esc</kbd></div>
        <div style="max-height:320px;overflow:auto">${items.slice(0, 14).map((it, n) => html`<div key=${it.k || it.l} class=${`it ${n === sel ? "on" : ""}`} onMouseEnter=${() => { S.pal.i = n; up(); }} onMouseDown=${e => { e.preventDefault(); run(it); }}>${icon(n === sel ? "chevron-right" : "circle-dot")}<span>${it.l}</span><span class="k2">${it.d}</span></div>`)}${!items.length ? html`<div class="it"><span></span><span class="d">nothing matches — try "nifty 22700 ce sell"</span></div>` : null}</div>
        <div class="ft"><span>↑↓ choose</span><span>Enter run</span><span>typing a strike + CE/PE validates it</span></div>
      </div>
    </div>`;
  }

  // ---------- actions ----------
  function setMode(m) { S.mode = m; S.about = false; if (m === "trade") { const o = S.trades.find(t => t.t0 <= S.T); if (o) S.sel = o.id; } else S.sel = S.focus; up(); }
  function selectIdx(i) { S.focus = i; S.sel = i; if (S.mode === "trade") S.mode = "read"; if (S.mode === "validate") { S.slip = Object.assign({}, S.slip, { idx: i, K: E.snap(i, S.T, feedT()).atm || S.slip.K, px: "" }); } up(); }
  function selectTrade(id) { S.sel = id; S.mode = "trade"; const t = S.trades.find(x => x.id === id); if (t) S.focus = t.idx; up(); }
  function press() { const r = E.read(S.focus, S.T, feedT()); if (r.ok) S.pressed = { T: S.T, idx: r.idx, rows: r.rows.map(x => ({ k: x.k, cell: x.cell })) }; S.mode = "read"; up(); }
  function openTrade() { return S.trades.find(t => t.t0 <= S.T && !t.exitT) || null; }
  async function markTrade() {
    if (!S.live || S.closed) { toast("marks only on the live day, before the close"); return; }
    if (openTrade()) { toast("one open trade at a time — I'm out first"); return; }
    const v = E.validate(S.slip.idx, Number(S.slip.K), S.slip.ty, S.slip.side, S.slip.px === "" ? null : Number(S.slip.px), nowSec(), feedT()); if (!v.ok) { toast("no chain row yet"); return; }
    // the same door the DESK's Mark.tsx uses: {op: mark, idx, k, side, role, t0, p0} — a record of her trade, never an order
    const body = { op: "mark", idx: S.slip.idx, k: Number(S.slip.K), side: S.slip.ty, role: S.slip.side === "BUY" ? "long" : "short", t0: hms(nowSec()), p0: v.px,
                   validate: { rev: v.rev, word: v.word, w: v.counts.w, a: v.counts.a, n: v.counts.n, c: v.counts.c, of: v.counts.of } };   // rev 3 §3: the entry stamp
    const r = await post("/api/hold/trades", body);
    if (!r.ok) { toast(r.why || "the mark did not land"); return; }
    await refreshTrades(); S.mode = "trade"; S.focus = S.slip.idx; const o = openTrade(); if (o) S.sel = o.id; up();
  }
  async function exitTrade(t) {
    if (!S.live || S.closed) return;
    if (S.arm !== t.id) { S.arm = t.id; setTimeout(() => { if (S.arm === t.id) { S.arm = null; up(); } }, 5000); up(); return; }
    S.arm = null;
    const r = await post("/api/hold/trades", { op: "exit", id: t.id });
    if (!r.ok) toast(r.why || "the exit did not land"); else await refreshTrades(); up();
  }
  async function post(url, body) { try { const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); return await r.json(); } catch (e) { return { ok: false, why: "the server is not answering" }; } }
  function replayTrade(t) { S.T = t.t0; S.speed = 1; S.playing = true; S.liveFollow = false; S.mode = "trade"; S.about = false; S.sel = t.id; S.focus = t.idx; S.follow = true; up(); }
  function goLive() { if (!S.live) return; S.liveFollow = true; S.playing = !S.closed; S.speed = 1; S.T = Math.max(OPEN, nowSec()); S.follow = true; up(); }
  function goTo(t) { const cap = S.live ? Math.max(OPEN, nowSec()) : CLOSE; S.T = Math.max(OPEN, Math.min(cap, t)); S.liveFollow = S.live && S.T >= cap; S.follow = true; up(); }
  function step(d) { goTo(S.T + d); }
  function togglePlay() { if (S.live && S.liveFollow) { S.liveFollow = false; S.playing = false; up(); return; } if (S.T >= CLOSE && !S.playing && !S.live) S.T = OPEN; S.playing = !S.playing; up(); }
  function openPal(q) { S.pal = { q, i: 0 }; up(); }
  let toastT = 0; function toast(msg) { const el = document.getElementById("toast"); el.textContent = msg; el.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => { el.hidden = true; }, 2400); }

  // ---------- A56: the voice at T -- live from /api/fold?id= while following the clock, else the replayed path's latest minute ≤ T ----------
  function voiceAt(t, T) {
    if (S.live && S.liveFollow) { const f = S.fold[t.id]; return f && f.voice && f.voice.ok ? f.voice : null; }
    const p = S.vpath[t.id]; if (!p || !p.ok) return null;
    const v = (pathAt(p, T) || {}).voice;
    return v && v.ok ? v : null;
  }
  function pathAt(p, T) { let e = null; for (const x of (p && p.path) || []) { if (secOf(x.at || x.t) <= T) e = x; else break; } return e; }   // x.at: the read's own second

  // F9 (25 Oct): THE stop is the voice's -- {f, s, src} -- or why there is none; never engine.js's own give-up G (with the voice
  // refused, the three faces showed three different stops: DEV-FACES F03)
  function voiceStop(t, T) {
    const v = voiceAt(t, T);
    if (v && v.stop_f != null) return v.stop_s != null ? { f: v.stop_f, s: v.stop_s, src: v.stop_src } : { f: v.stop_f, s: null, src: v.stop_src, txt: `stop ${fmt(v.stop_f)}f · spot ?` };   // fut only: the voice has no spot stop; none is made up
    const live = S.live && S.liveFollow, r = live ? S.fold[t.id] : S.vpath[t.id], e = live ? r : pathAt(r, T);
    const w = String((e && e.voice && e.voice.why) || (r && !r.ok && r.why) || (v ? "the voice has no stop yet" : "TapeMap ki voice nahi aayi"));
    return { why: /^could not check/.test(w) ? w : "could not check — " + w };
  }

  // the prototype row's sub-line. Its old "out if G fut accepted" was a second stop beside the voice's: never printed (F9, DEV-FACES F12)
  function protoSub(t, T, r) {
    return r.folded ? (t.exitWhy || "give-up accepted") : r.pb ? `${r.pb} · fut ${sgn(Math.round(r.s.fut - r.e.fut))} vs entry` : "";
  }

  // ---------- ONE TRUTH: the engine's word (GET /api/fold?id= view.headline, or the record's headline history) ----------
  function engineWord(t, T, r) {
    const proto = { headline: r && r.ok ? r.word : "—", key: r && r.ok ? r.word.split(" ")[0] : "", src: "prototype", sub: r && r.ok ? protoSub(t, T, r) : "", tip: "engine.js prototype logic [I] — the live engine has not answered for this trade" };
    const f = S.fold[t.id];
    const words = (S.foldWords[t.id] || []).filter(w => secOf(w.t) <= T);
    const frozen = t.exitT != null && T >= t.exitT;                  // after her exit the engine's view is frozen there
    if (S.live && (S.liveFollow || frozen) && f && f.ok && f.view && f.view.headline && !(words.length && !frozen && !S.liveFollow)) return { headline: f.view.headline, key: f.view.headline.split(" ")[0].replace(/[^A-Z-]/g, ""), src: "engine", sub: [f.view.clause, f.view.line2].filter(Boolean).join(" · "), tip: "GET /api/fold?id= · fold.py rev 6 · the decision, verbatim" };
    if (words.length) { const w = words[words.length - 1]; return { headline: w.headline, key: w.headline.split(" ")[0].replace(/[^A-Z-]/g, ""), src: S.live ? "engine · logged" : "engine · record", sub: [w.clause, `since ${w.t}`].filter(Boolean).join(" · "), tip: "the engine's own headline history (fold_log) at this second" }; }
    if (f && !f.ok) return Object.assign(proto, { tip: `engine: ${f.why || "not answering"} — prototype shown` });
    return proto;
  }

  // ---------- keyboard ----------
  document.addEventListener("keydown", e => {
    const inField = /^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName);
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); S.pal ? (S.pal = null, up()) : openPal(""); return; }
    if (S.pal) return;
    if (e.key === "Escape") { if (S.about) { S.about = false; up(); } else if (inField) e.target.blur(); else { S.mode = "validate"; up(); } return; }
    if (inField) { if (e.key === "Enter") { e.preventDefault(); S.mode = "validate"; up(); } return; }
    const k = e.key;
    if (k === "1") setMode("read"); else if (k === "2") setMode("validate"); else if (k === "3") setMode("trade");
    else if (k === " ") { e.preventDefault(); togglePlay(); }
    else if (k === "ArrowLeft") { e.preventDefault(); step(e.shiftKey ? -60 : -1); } else if (k === "ArrowRight") { e.preventDefault(); step(e.shiftKey ? 60 : 1); }
    else if (k === "[") { S.speed = S.speed === 60 ? 10 : 1; up(); } else if (k === "]") { S.speed = S.speed === 1 ? 10 : 60; up(); }
    else if (k.toLowerCase() === "r") press(); else if (k.toLowerCase() === "m") markTrade(); else if (k.toLowerCase() === "l") goLive(); else if (k === "`") { S.consoleMin = !S.consoleMin; up(); }
    else if (k === "Enter") { S.mode = "validate"; up(); }
  });
  // tooltips: one element, event delegation, never a native title
  const tipEl = document.getElementById("tip");
  document.addEventListener("mouseover", e => { const t = e.target.closest && e.target.closest("[data-tip]"); if (!t || !t.dataset.tip) { tipEl.hidden = true; return; } const txt = t.dataset.tip; tipEl.innerHTML = txt.replace(/\[(M|I)[^\]]*\]/g, m => `<span class="tg">${m}</span>`).replace(/ · (saath|khilaaf|ruko|mat lo|le lo|likh rahe|bhag rahe|check nahi|nahi dikha|kuch nahi|nikal lo|chhod diya|zone gaya|pullback|tay nahi|ruke hue|shaant|checked, kuch nahi)\s*$/, (m, w) => ` <span class="hi">${w}</span>`); tipEl.hidden = false; place(e); });
  document.addEventListener("mousemove", e => { if (!tipEl.hidden) place(e); });
  document.addEventListener("mouseout", e => { if (!e.relatedTarget || !(e.relatedTarget.closest && e.relatedTarget.closest("[data-tip]"))) tipEl.hidden = true; });
  function place(e) { const w = tipEl.offsetWidth, hgt = tipEl.offsetHeight; let x = e.clientX + 14, y = e.clientY + 16; if (x + w > innerWidth - 8) x = e.clientX - w - 10; if (y + hgt > innerHeight - 8) y = e.clientY - hgt - 10; tipEl.style.left = x + "px"; tipEl.style.top = y + "px"; }

  // ---------- app ----------
  function App() {
    const F = frame();
    return html`<div class="app">
      <${Menubar} F=${F}/>
      <${FeedBand} F=${F}/>
      <div class="main"><${Outliner} F=${F}/><${Ladder} F=${F}/><${Inspector} F=${F}/></div>
      <${Console} F=${F}/>
      <${Status} F=${F}/>
      ${S.pal ? html`<${Palette}/>` : null}
    </div>`;
  }
  function draw() { document.body.className = `m-${S.mode}${S.live ? " live" : " replay"}`; render(html`<${App}/>`, document.getElementById("app")); }
  function tick() {
    if (!S.loaded) return;
    if (S.live && S.liveFollow) { const n = Math.max(OPEN, nowSec()); if (n >= CLOSE) { S.closed = true; S.playing = false; } S.T = Math.min(CLOSE, n); draw(); return; }
    if (S.playing && S.T < CLOSE) { const cap = S.live ? Math.max(OPEN, nowSec()) : CLOSE; S.T = Math.min(cap, S.T + S.speed); if (S.live && S.T >= cap) { S.liveFollow = true; } if (S.T >= CLOSE) S.playing = false; draw(); }
  }
  // F10 (25 Oct): each poller keeps ONE request in flight and gives up after 8 s (ui-v2 hold/store.ts j()'s bound): a wedged
  // server turns FEED DEAD / "not answering" instead of stacking ~5 requests a second, and a late reply never overwrites a newer one
  const TIMEOUT_MS = 8000, FULL_TIMEOUT_MS = 20000;                // loadFull reads the whole day, so it gets longer
  let polling = false, lastPoll = 0, tradesP = null, foldBusy = false, flatBusy = false;
  async function poll(force) {
    if (!S.loaded || polling) return;
    if (!S.live && !force) return;                                   // a past day is complete: nothing to tail
    if (S.closed && !force && performance.now() - lastPoll < 10000) return;   // after the close: a heartbeat every 10 s
    polling = true; lastPoll = performance.now();
    try {
      const since = Math.min(...IDX.map(i => { const x = E.data.idx[i]; return x.t.length ? x.t[x.t.length - 1] : 0; }));
      const r = await fetch(`/api/v2/data?day=${E.data.day}&since=${since}`, { signal: AbortSignal.timeout(TIMEOUT_MS) }); if (!r.ok) throw new Error("HTTP " + r.status);
      const d = await r.json(); if (!d.ok) throw new Error(d.why || "not ok");
      if (E.apply(d) === "reload") { await loadFull(); } else { S.srvNow = d.now; S.srvAt = performance.now(); }
      if (S.feed !== "ok") { S.feed = "ok"; S.feedWhy = ""; S.feedSince = null; }
    } catch (e) { if (S.feed !== "dead") { S.feed = "dead"; S.feedSince = nowSec(); } S.feedWhy = String(e.message || e); } finally { polling = false; }
    up();
  }
  async function loadFull() {
    const r = await fetch(`/api/v2/data${S.day ? "?day=" + S.day : ""}`, { signal: AbortSignal.timeout(FULL_TIMEOUT_MS) }); if (!r.ok) throw new Error("HTTP " + r.status);
    const d = await r.json(); if (!d.ok) throw new Error(d.why || "not ok");
    E.load(d); decSeen.clear(); decLive = 0; S.srvNow = d.now; S.srvAt = performance.now(); S.live = !!d.live; S.day = d.day; return d;
  }
  const mapTrade = t => ({ id: t.id, idx: t.idx, K: Number(t.k), ty: t.side, side: t.role === "long" ? "BUY" : "SELL", px: t.p0 == null ? null : Number(t.p0), t0: secOf(t.t0), exitT: t.exit_t ? secOf(t.exit_t) : null, exitWhy: t.exit_t ? `her exit ${t.exit_t} (record)` : null, label: t.src || "marked" });
  // one read of the trade list in flight. A tick that finds one out drops; a mark / exit (refreshTrades) waits for it and reads
  // again -- that read began after their write, so it shows the new trade / the exit, never the stale reply that was in flight
  function pollTrades() { return tradesP || (tradesP = readTrades().finally(() => { tradesP = null; })); }
  async function refreshTrades() { if (tradesP) await tradesP; return pollTrades(); }
  async function readTrades() {
    try {
      if (S.live) { const r = await fetch("/api/hold/trades", { signal: AbortSignal.timeout(TIMEOUT_MS) }); const d = await r.json(); if (!d.ok) throw new Error(d.why || "not ok"); S.trades = (d.trades || []).map(mapTrade); S.apiWhy = ""; }
      else { const r = await fetch(`/api/fold/record?day=${E.data.day}`, { signal: AbortSignal.timeout(TIMEOUT_MS) }); const d = await r.json(); if (!d.ok) throw new Error(d.why || "not ok");
        S.trades = (d.trades || []).map(x => { const tr = x.trade || x; const id = x.id || tr.id || `${tr.idx}-${tr.k}${tr.ty || tr.side}-${tr.entry_t || tr.t0}`; if (x.words) S.foldWords[id] = x.words; return x.trade && x.trade.entry_t ? { id, idx: tr.idx, K: Number(tr.k), ty: tr.ty, side: tr.side, px: tr.p0 == null ? null : Number(tr.p0), t0: secOf(tr.entry_t), exitT: tr.exit_t ? secOf(tr.exit_t) : null, exitWhy: tr.exit_t ? `her exit ${tr.exit_t} (record)` : null, label: "record" } : mapTrade(tr); }); S.apiWhy = ""; }   // a past day's record carries her day_state mark (t0, side = CE|PE, role): mapTrade's shape
    } catch (e) { S.apiWhy = `trades: ${e.message || e} (GET ${S.live ? "/api/hold/trades" : "/api/fold/record?day=" + E.data.day})`; }
    up();
  }
  async function pollFold() {
    if (!S.live || foldBusy) return;
    foldBusy = true;
    try {
      const o = openTrade();
      // the open trade every second; a closed trade once (its view is frozen at her exit, fold_live), plus its headline history
      const want = S.trades.filter(t => t === o || !(S.fold[t.id] && S.fold[t.id].ok));
      for (const t of want) {
        try { const r = await fetch(`/api/fold?id=${encodeURIComponent(t.id)}`, { signal: AbortSignal.timeout(TIMEOUT_MS) }); const d = await r.json(); S.fold[t.id] = d; if (d && d.words) S.foldWords[t.id] = d.words; } catch (e) { S.fold[t.id] = { ok: false, why: "not answering" }; }
      }
    } finally { foldBusy = false; }
    up();
  }
  async function pollVpath() {
    if (!S.loaded || (S.live && S.liveFollow)) return;
    for (const t of S.trades.filter(x => x.t0 <= S.T)) {
      const p = S.vpath[t.id]; if (p && (p.ok || performance.now() - p.at < (p.busy ? 10000 : 60000))) continue;
      S.vpath[t.id] = { ok: false, busy: true, at: performance.now(), why: "could not check — asking for the replay" };
      try { S.vpath[t.id] = Object.assign(await (await fetch(`/api/voice_path?id=${encodeURIComponent(t.id)}&day=${E.data.day}`)).json(), { at: performance.now() }); }
      catch (e) { S.vpath[t.id] = { ok: false, busy: true, at: performance.now(), why: "could not check — /api/voice_path not answering" }; }
    }
    up();
  }
  const decSeen = new Set(); let decBusy = false, decLive = 0;
  async function pollDecode() {
    if (!S.loaded || decBusy) return;
    let url;
    if (S.live && S.liveFollow) { if (performance.now() - decLive < 20000) return; decLive = performance.now(); url = "/api/decode"; }
    else { const c = Math.floor((S.T - 60) / 300) * 300; if (c <= OPEN) return; const key = `${E.data.day}|${c}`; if (decSeen.has(key)) return; decSeen.add(key); url = `/api/decode?day=${E.data.day}&at=${hm(c)}`; }
    decBusy = true;
    try { const d = await (await fetch(url, { signal: AbortSignal.timeout(TIMEOUT_MS) })).json(); if (d.ok) { for (const i of Object.keys(d.indices || {})) E.setDecode(i, d.indices[i]); S.decWhy = d.why || ""; } else S.decWhy = d.why || "not ok"; }
    catch (e) { S.decWhy = `GET ${url}: ${e.message || e}`; } finally { decBusy = false; }
    up();
  }
  async function pollFlat() {
    if (flatBusy) return;
    flatBusy = true;
    const i = S.focus;                                                // the index asked for, even if she switches mid-request
    try { const r = await fetch(`/api/fold/flat?idx=${i}`, { signal: AbortSignal.timeout(TIMEOUT_MS) }); const d = await r.json(); S.flat[i] = d; } catch (e) { S.flat[i] = { ok: false }; } finally { flatBusy = false; }
    up();
  }
  const lastDataSec = d => Math.max(OPEN, ...IDX.map(i => { const x = d.idx[i]; return x.t.length ? x.t[x.t.length - 1] : 0; }));

  // ---------- boot: LIVE today, or ?day= replay; a feed that does not answer is said so, never sampled ----------
  async function boot() {
    try {
      let d = await loadFull();
      // pre-open: today has no rows yet -- show the last session (up to 7 days back), reload when today's first row lands
      if (d.live && IDX.every(i => !d.idx[i].t.length)) {
        const today = d.day;
        for (let k = 1; k <= 7; k++) {
          const x = new Date(today + "T12:00:00"); x.setDate(x.getDate() - k); const day = x.toISOString().slice(0, 10);
          const r = await fetch(`/api/v2/data?day=${day}`); const p = r.ok ? await r.json() : null;
          if (p && p.ok && IDX.some(i => p.idx[i].t.length)) { E.load(p); decSeen.clear(); d = p; S.day = day; S.live = false; S.preopen = today; break; }
        }
        setInterval(async () => { try { const q = await (await fetch(`/api/v2/data?day=${today}&since=0`)).json(); if (q.ok && IDX.some(i => q.idx[i].t.length)) location.reload(); } catch (e) {} }, 10000);
      }
      S.loaded = true; S.feed = "ok"; document.title = `TapeMap Validate · ${d.day}${S.live ? " · live" : " · replay"}`;
      if (S.live) { const n = d.now; S.closed = n >= CLOSE; S.T = Math.max(OPEN, Math.min(CLOSE, S.closed ? Math.max(lastDataSec(d), CLOSE) : n)); S.liveFollow = true; S.playing = !S.closed; }
      else { S.T = Math.min(CLOSE, Math.max(OPEN, lastDataSec(d))); S.closed = true; S.playing = false; S.liveFollow = false; }
      setTimeout(() => { for (const i of IDX) E.events(i); }, 50);
      draw(); setInterval(tick, 1000); setInterval(() => poll(false), 1000); setInterval(pollTrades, 5000); setInterval(pollFold, 1000); setInterval(pollVpath, 2000); setInterval(pollFlat, 3000); setInterval(pollDecode, 1000);
      pollTrades(); pollFlat();
      const health = async () => { try { const h = await (await fetch("/api/health")).json(); const c = h.coverage || {}; const fr = c.book && c.book.from ? Object.values(c.book.from).sort()[0] : null;
        S.late = c.late_min > 0 ? { up: c.server_up, min: c.late_min, from: fr ? fr.slice(0, 5) : c.server_up } : null; up(); } catch (e) {} };
      if (S.live) { health(); setInterval(health, 60000); }
    } catch (e) {
      const m = document.querySelector(".boot .msg");
      if (m) m.innerHTML = `<b style="color:var(--red-ink)">FEED DEAD</b>&nbsp; /api/v2/data not answering (${String(e.message || e)}) · fix: start the TapeMap server (.\\start-v2.bat) · retrying in 5 s`;
      setTimeout(boot, 5000);
    }
  }
  boot();
})();
