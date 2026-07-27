/* TapeMap V2 — "Replay Dashboard": narrative rail · trap radar + momentum · annotated ladder. */

const COL = { OPENING:"#5d6b84", BALANCE:"#5d6b84", COILING:"#ffbf00",
              ARMED:"#8b5cf6", "TREND-UP":"#2ec27e", "TREND-DOWN":"#ff5f6b" };
const LOUD = new Set(["ARMED","SPRING","IGNITION","CLIMAX","TRAP","CARRY","SQUEEZE-RELEASE",
                      "TRAP-SPRUNG","SPRING-FAIL","OI-PEAK-LAG",
                      "BAND-REVERSAL","BAND-BREAK"]);
const GAMMA_COL = { PINNED:"#5d6b84", FLOOR:"#2ec27e", CEILING:"#ff5f6b",
                    "AMPLIFIED-UP":"#2ec27e", "AMPLIFIED-DOWN":"#ff5f6b", NEUTRAL:"#8090a8" };
const GAMMA_TXT = {
  PINNED:"two-sided walls — dealers dampen both ways, fade extremes toward strike",
  FLOOR:"put wall below — dips absorbed, upside NOT capped",
  CEILING:"call wall above — rallies sold, downside NOT supported",
  "AMPLIFIED-UP":"dealer hedging chases price UP — momentum regime",
  "AMPLIFIED-DOWN":"dealer hedging chases price DOWN — momentum regime",
  NEUTRAL:"no dominant dealer positioning near strike" };
const EVC = { IGNITION:"#ffbf00", CLIMAX:"#ffbf00", ARMED:"#8b5cf6", SPRING:"#8b5cf6",
              TRAP:"#ff5f6b", DIVERGENCE:"#ff5f6b", PRESS:"#4aa8ff", CAMPAIGN:"#4aa8ff",
              "BUYER-BUILD":"#4aa8ff", ABSORPTION:"#4aa8ff", BREAK:"#8090a8",
              "FLIP-TEST":"#2ec27e", CARRY:"#2ec27e", STATE:"#3a465c",
              "GAMMA-PIN":"#3fc1c9", "SQUEEZE-RISK":"#3fc1c9",
              "SQUEEZE-RELEASE":"#3fc1c9", "TRAP-SETTING":"#ffbf00",
              "TRAP-SPRUNG":"#ff5f6b", "SPRING-FAIL":"#ff5f6b",
              "OI-PEAK-LAG":"#ffbf00", "BAND-REVERSAL":"#8b5cf6",
              "BAND-BREAK":"#ff5f6b", CHOP:"#c9a24a" };

const S = { data:null, day:null, i:0, playing:false, timer:null,
            feedPtr:0, states:[], whys:[], tIdx:{}, index:"NIFTY" };
const $ = id => document.getElementById(id);

// multi-index: append the active index to any data/chain URL
function IDXQ(url){ return url + (url.includes("?") ? "&" : "?") + "idx=" + S.index; }

// --- localStorage persistence (private-mode safe) ---
function lsGet(k){ try{ return localStorage.getItem("tapemap." + k); }catch(e){ return null; } }
function lsSet(k,v){ try{ localStorage.setItem("tapemap." + k, v); }catch(e){} }

// --- status banner (amber; green when ok=true) with 5-min mute-after-dismiss ---
function showBanner(msg, ok=false){
  const b = $("liveBanner");
  if(!b) return;
  const m = S.bannerMuted;
  if(!ok && m && m.msg === msg && Date.now() < m.until) return;
  const tokBtn = /token/i.test(msg) ? `<button id="tokBannerBtn">⟳ capture token</button>` : "";
  b.innerHTML = `<span class="bmsg">${msg}</span>${tokBtn}<span class="bx" title="dismiss">✕</span>`;
  b.classList.remove("hidden");
  b.classList.toggle("ok", ok);
  b.querySelector(".bx").onclick = () => { S.bannerMuted = {msg, until: Date.now() + 300000}; hideBanner(); };
  const tb = $("tokBannerBtn");
  if(tb) tb.onclick = () => { if(typeof captureToken === "function") captureToken(); };
}
function hideBanner(){ const b = $("liveBanner"); if(b) b.classList.add("hidden"); }

// --- bar-builder heartbeat: a stale tape must never look live ---
// (2026-07-27: the bar builder hung for an hour while the UI kept rendering
// the last payload as if it were current). Server stamps built_at (epoch s);
// same machine, so client-clock skew is negligible.
function staleCheck(nd){
  if(!nd || !nd.built_at) return false;          // old server: no heartbeat
  const age = Date.now()/1000 - nd.built_at;
  if(age <= 90) return false;                    // healthy: builds every ~15-40s
  const t = new Date(nd.built_at*1000).toLocaleTimeString("en-GB");
  showBanner(`TAPE STALE — bars last built ${t} (${Math.round(age/60)} min ago); ` +
             `chain view may still be live — check the server window / tapemap.log`);
  return true;
}

// --- one-click Dhan token capture (clipboard first, paste fallback) ---
const JWT_RE = /^eyJ[\w-]+\.[\w-]+\.[\w-]+$/;   // fast client sanity; server re-validates
async function captureToken(){
  let raw = "";
  try{ raw = (await navigator.clipboard.readText()).trim(); }catch(e){ raw = ""; }
  if(JWT_RE.test(raw)){ await postToken(raw); raw = ""; return; }
  tokenPastePrompt();                            // empty/denied/not-a-JWT -> manual paste
}
async function postToken(tok){
  try{
    const r = await fetch("/api/token", {method:"POST",
      headers:{"Content-Type":"application/json"}, body: JSON.stringify({token: tok})});
    const j = await r.json();
    if(j.ok){
      S.bannerMuted = null;
      showBanner("token captured — " + j.msg + "; live data resuming…", true);
      pollUntilLive();                       // pull the tape in as soon as the server rebuilds
    }
    else showBanner("token rejected — " + j.msg);
  }catch(e){ showBanner("token save failed — is the server running?"); }
}
// after a fresh token, poll /api/data a few times until the server has bars
function pollUntilLive(tries = 8){
  if(tries <= 0) return;
  setTimeout(async () => {
    try{
      const nd = await (await fetch(IDXQ("/api/data"))).json();
      if(nd.days && nd.days.length){
        S.data = nd; setDay(nd.days.length - 1); seek(S.day.bars.length - 1);
        hideBanner();
        return;
      }
    }catch(e){ /* keep trying */ }
    pollUntilLive(tries - 1);
  }, 4000);
}
function tokenPastePrompt(){
  const b = $("liveBanner");
  if(!b) return;
  b.classList.remove("hidden", "ok");
  b.innerHTML = `<span class="bmsg">clipboard unavailable — paste the Dhan token:</span>` +
    `<input type="password" id="tokPaste" placeholder="paste token" autocomplete="off">` +
    `<button id="tokGo">GO</button><span class="bx" title="dismiss">✕</span>`;
  b.querySelector(".bx").onclick = hideBanner;
  const inp = $("tokPaste"), go = $("tokGo");
  inp.focus();
  const submit = async () => { const v = inp.value.trim(); inp.value = ""; if(v) await postToken(v); };
  go.onclick = submit;
  inp.addEventListener("keydown", e => { if(e.key === "Enter"){ e.preventDefault(); submit(); } });
}

async function boot(){
  try{                                   // Stage-2 GEX overlay (optional file)
    const r = await fetch("/api/gex");
    if(r.ok){
      S.gex = await r.json();
      S.gexIdx = Object.fromEntries(S.gex.t.map((t,i)=>[t,i]));
    }
  }catch(e){ /* no GEX data — ladder simply omits FLIP/WALL rungs */ }
  $("playBtn").onclick = togglePlay;
  $("scrub").oninput = e => { seek(+e.target.value); };
  $("tokBtn").onclick = captureToken;
  // restore persisted prefs BEFORE loading data
  const savedIdx = lsGet("index");
  if(savedIdx && [...$("idxTabs").children].some(c => c.dataset.idx === savedIdx)){
    S.index = savedIdx;
    [...$("idxTabs").children].forEach(c => c.classList.toggle("active", c.dataset.idx === savedIdx));
  }
  const savedSpeed = lsGet("speed");
  if(savedSpeed && [...$("speed").options].some(o => o.value === savedSpeed)) $("speed").value = savedSpeed;
  $("speed").addEventListener("change", () => lsSet("speed", $("speed").value));
  try{
    await bootData();                     // load the active index's payload
  }catch(e){
    showBanner("server unreachable — is the TapeMap server running?");
    return;
  }
  // restore view/sub-tab AFTER data is loaded
  if(lsGet("view") === "data") $("vData").click();
  const savedSub = lsGet("chsub");
  if(savedSub && document.body.classList.contains("dataMode")) setChainSub(savedSub);
  if(S.data.live || S.data.index){        // live mode (bars may be pending pre-market)
    document.getElementById("brand").innerHTML = "TAPE<span>MAP</span> ●LIVE";
    setInterval(async () => {
      try{
        const nd = await (await fetch(IDXQ("/api/data"))).json();
        if(!nd.days || !nd.days.length){ staleCheck(nd); return; }
        const atEnd = S.i >= (S.day ? S.day.bars.length - 1 : 0);
        const keep = S.i;
        S.data = nd;
        setDay(nd.days.length - 1);
        seek(atEnd ? S.day.bars.length - 1
                   : Math.min(keep, S.day.bars.length - 1));
        if(!staleCheck(nd)) hideBanner();
      }catch(e){ showBanner("live refresh failing — showing last good data"); }
    }, 60000);
  }
}

// (re)load the current index's /api/data payload and rebuild the day tabs.
// Called on first boot and on every header index switch.
async function bootData(){
  S.data = await (await fetch(IDXQ("/api/data"))).json();
  const tabs = $("dayTabs");
  tabs.innerHTML = "";
  (S.data.days || []).forEach((d, idx) => {
    const b = document.createElement("button");
    b.textContent = d.day;
    b.onclick = () => setDay(idx);
    tabs.appendChild(b);
  });
  if(!S.data.days || !S.data.days.length){   // market closed / live_error: notice, no bars
    S.day = null;
    $("stkLbl").textContent = "";
    showBanner(S.data.live_error || "no data for this index yet");
    return;
  }
  if(!staleCheck(S.data)) hideBanner();
  setDay(S.data.days.length - 1);
  seek(S.day.bars.length - 1);           // open on the newest bar
}

function setDay(idx){
  S.day = S.data.days[idx];
  [...$("dayTabs").children].forEach((b,j)=>b.classList.toggle("active", j===idx));
  S.tIdx = Object.fromEntries(S.day.bars.map((b,i)=>[b.t,i]));
  const stEv = S.day.events.filter(e=>e.kind==="STATE");
  S.states = []; S.whys = [];
  let cur="OPENING", why="", p=0;
  for(let i=0;i<S.day.bars.length;i++){
    while(p<stEv.length && S.tIdx[stEv[p].t]<=i){
      const m = stEv[p].msg.split(" — "); cur=m[0]; why=m[1]||""; p++;
    }
    S.states.push(cur); S.whys.push(why);
  }
  const stk = Math.round(S.day.strike);
  $("stkLbl").textContent = "STRIKE " + stk +
    (S.data.expiry ? " · EXP " + S.data.expiry : "");
  $("bCE").children[0].textContent = stk + " CE";
  $("bPE").children[0].textContent = stk + " PE";
  $("scrub").max = S.day.bars.length - 1;
  $("feed").innerHTML = ""; S.feedPtr = 0;
  S.i = 0;
  render();
}

function togglePlay(){
  S.playing = !S.playing;
  $("playBtn").textContent = S.playing ? "❚❚" : "▶";
  clearInterval(S.timer);
  if(S.playing) S.timer = setInterval(()=>{
    if(S.i >= S.day.bars.length-1){ togglePlay(); return; }
    seek(S.i+1);
  }, 1000 / +$("speed").value);
}

function seek(i){
  if(i < S.i){ $("feed").innerHTML=""; S.feedPtr=0; }
  S.i = i;
  $("scrub").value = i;
  render();
}

/* ---------- helpers over engine events ---------- */

function eventsUpTo(i){ return S.day.events.filter(e => S.tIdx[e.t] !== undefined && S.tIdx[e.t] <= i); }
function minutesAgo(i, t){ return i - S.tIdx[t]; }
function parseLevel(msg){
  const m = msg.match(/at (R\d|S\d|P) (\d+)/);
  return m ? { name:m[1], px:+m[2] } : null;
}
function parseRank(msg){
  const m = msg.match(/rank (0\.\d+)/);
  return m ? +m[1] : null;
}
function splitMsg(msg){
  const parts = msg.split(" — ");
  return { head: parts[0], rest: parts.slice(1).join(" — ") };
}

/* ---------- render ---------- */

let _rafPending = false;
function render(){                       // coalesce bursts into one paint/frame
  if(_rafPending) return;
  _rafPending = true;
  requestAnimationFrame(() => { _rafPending = false; _render(); });
}
function _render(){
  const i = S.i, bar = S.day.bars[i], st = S.states[i];
  $("clock").textContent = bar.t;
  const sn = $("stName");
  sn.textContent = st; sn.style.color = COL[st] || "#dbe6f5";
  $("stWhy").textContent = S.whys[i] || "";

  for(const [k,id] of [["fut","bFUT"],["ce","bCE"],["pe","bPE"]]){
    const b = bar[k], node = $(id);
    node.children[1].textContent = b.c.toFixed(k==="fut"?2:1);
    const oi = (b.oi_slope>0?"+":"") + Math.round(b.oi_slope/1000) + "k OI";
    node.children[2].textContent =
      `${b.z>=0?"+":""}${b.z.toFixed(1)}σ · ${oi} · vol ${Math.round(b.vol_r*100)}%`;
    node.children[2].style.color = b.oi_slope>0 ? "#2ec27e" : "#ff5f6b";
  }

  const c = bar.ctx;
  if(c){
    const VC = { GO:"#2ec27e", READY:"#8b5cf6", WAIT:"#ffbf00",
                 "STAND ASIDE":"#5d6b84", CAUTION:"#8090a8", SPENT:"#ff8c5a" };
    const BC = c.breadth.includes("BULL") ? "#2ec27e" :
               c.breadth.includes("BEAR") ? "#ff5f6b" : "#5d6b84";
    const v = $("verdict");
    v.textContent = c.verdict; v.style.color = VC[c.verdict] || "#dbe6f5";
    v.title = c.vwhy;
    const b = $("breadth");
    b.textContent = c.breadth; b.style.color = BC;
    $("ctxLine").textContent = c.line + " — " + c.vwhy;
    $("flips").innerHTML = (c.flips || [])
      .map(f => `<span>Δ ${f}</span>`).join("");
    const pc = $("pinChip");
    if(pc){
      if(c.pin){
        const d = c.pin.dist;
        pc.textContent = `◎ PIN ${c.pin.k} · px ${d>=0?"+":""}${d}`;
        pc.title = `dealer pin / defended strike ${c.pin.k} — price is ` +
          `${Math.abs(d)} pts ${d>=0?"above":"below"} the magnet (${c.pin.regime})`;
        pc.style.color = c.pin.regime === "PINNED" ? "#c98bd6"
          : /CEIL|FLOOR/.test(c.pin.regime) ? "#3fc1c9" : "#7d8aa3";
      } else pc.textContent = "";
    }
  }

  const g = bar.gamma;
  if(g){
    const col = GAMMA_COL[g.regime] || "#8090a8";
    const rg = $("mmRegime");
    rg.textContent = g.regime; rg.style.color = col;
    $("mmWhat").textContent = GAMMA_TXT[g.regime] || "";
    for(const [w, id] of [[g.w_ce,"wCE"],[g.w_pe,"wPE"]]){
      const el = $(id), pct = Math.min(1, Math.abs(w)) * 50;
      el.style.left = w >= 0 ? "50%" : (50 - pct) + "%";
      el.style.width = pct + "%";
      el.style.background = w >= 0 ? "#3fc1c9" : "#ff5f6b";
    }
  } else {
    $("mmRegime").textContent = "—"; $("mmWhat").textContent = "";
  }

  renderVol(bar.ctx, bar.gamma);
  renderExpiry(bar.ctx);
  renderRibbon(i);
  renderStory(i, bar);
  renderRead(i, bar);
  renderTrap(i, bar, st);
  renderMomentum(i, bar, st);
  renderLadder(i, bar);
  renderFeed(i);
  renderCarry(i);
  if(document.body.classList.contains("dataMode") &&
     $("dataView").classList.contains("legacy")) renderData(i, bar);
}

/* ---------- DATA view: every datapoint as a clickable widget ---------- */

S.openWg = new Set();
const clamp1 = x => Math.max(-1, Math.min(1, x));

function leanBar(lean, conf){
  const w = Math.abs(lean) * 50;
  const neutral = Math.abs(lean) < 0.05;
  const bull = lean > 0;
  const fill = neutral ? "" : bull
    ? `<i style="left:50%;width:${w}%;background:#2ec27e"></i>`
    : `<i style="right:50%;width:${w}%;background:#ff5f6b"></i>`;
  const cls = neutral ? "flat" : bull ? "bull" : "bear";
  const dir = neutral ? "NEUTRAL" : bull ? "BULLISH" : "BEARISH";
  const arw = neutral ? "•" : bull ? "▲" : "▼";
  return `<div class="leanrow">` +
         `<span class="verdict ${cls}">${arw} ${dir} ${conf}%</span>` +
         `<span class="pole bear">PE·BEAR</span>` +
         `<div class="leanbar"><span class="mid"></span>${fill}</div>` +
         `<span class="pole bull">CE·BULL</span></div>`;
}

function wgCard(id, label, head, sub, lean, det){
  const conf = Math.round(Math.abs(lean) * 100);
  const ac = Math.abs(lean) < 0.05 ? "var(--edge)" : lean > 0 ? "#2ec27e" : "#ff5f6b";
  return `<div class="wg${S.openWg.has(id) ? " open" : ""}" data-id="${id}" ` +
    `style="border-left:3px solid ${ac}">` +
    `<div class="wh"><label>${label}</label><b>${head}</b></div>` +
    `<div class="sub">${sub}</div>` + leanBar(clamp1(lean), conf) +
    `<div class="det">${det}</div></div>`;
}

function rr(...cells){
  return `<div class="rr">${cells.map(x => `<span>${x}</span>`).join("")}</div>`;
}

function oiEpisodes(bars, i, k){
  const eps = [];
  for(let j = 10; j <= i; j++){
    eps.push({t: bars[j].t, d: bars[j][k].oi - bars[j-10][k].oi,
              pd: bars[j][k].c - bars[j-10][k].c, px: bars[j].fut.c});
  }
  eps.sort((a,b) => Math.abs(b.d) - Math.abs(a.d));
  const top = [], seen = [];
  for(const e of eps){
    if(top.length >= 5) break;
    if(seen.some(t => Math.abs(S.tIdx[t] - S.tIdx[e.t]) < 10)) continue;
    seen.push(e.t); top.push(e);
  }
  top.sort((a,b) => S.tIdx[a.t] - S.tIdx[b.t]);
  const cls = e => e.d > 0 ? (e.pd < 0 ? "writers add" : "buyers add")
                           : (e.pd > 0 ? "writers cover" : "longs bail");
  return top.map(e => rr(e.t, (e.d/1e6).toFixed(1)+"M", "@FUT "+e.px.toFixed(0), cls(e))).join("");
}

function renderData(i, bar){
  renderMap(i, bar);
  const bars = S.day.bars.slice(0, i + 1);
  const g = bar.gamma || {}, c = bar.ctx || {}, F = bar.fut.c;
  const stk = Math.round(S.day.strike);
  const cell = (l, h, s) => `<div class="cell"><label>${l}</label><b>${h}</b><span>${s}</span></div>`;
  const iv = x => x == null ? "—" : (x*100).toFixed(1) + "%";
  const ago = bars[Math.max(0, i-60)].gamma || {};
  const dIv = (n, a) => (n != null && a != null)
    ? ((n-a) >= 0 ? "+" : "") + ((n-a)*100).toFixed(1) + " vs 1h ago" : "flat";
  const MMV = {PINNED:"pin it to "+stk, FLOOR:"defend "+stk+" from below",
               CEILING:"cap it at "+stk, "AMPLIFIED-UP":"chasing price UP",
               "AMPLIFIED-DOWN":"chasing price DOWN", NEUTRAL:"no agenda near "+stk};
  $("dvTop").innerHTML =
    cell("IMPLIED VOL", `CE ${iv(g.iv_ce)} · PE ${iv(g.iv_pe)}`,
         `CE ${dIv(g.iv_ce, ago.iv_ce)} · PE ${dIv(g.iv_pe, ago.iv_pe)}`) +
    cell("GAMMA", g.regime || "—",
         `strike pull ${g.proxy ?? "—"} · writer CE ${g.w_ce ?? "—"} / PE ${g.w_pe ?? "—"}`) +
    cell("MM THINKING", MMV[g.regime] || "—", GAMMA_TXT[g.regime] || "") +
    cell("EXPECTED VIEW", c.verdict || "—",
         `${c.breadth || ""} · ${(c.episode || c.vwhy || "").slice(0, 96)}`);

  const W = [];
  // OI widgets
  for(const [k, nm, wsc] of [["ce","CE", g.w_ce ?? 0], ["pe","PE", g.w_pe ?? 0]]){
    const cur = bar[k], first = bars[0][k];
    const pk = bars.reduce((m,b) => b[k].oi > m.oi ? {oi:b[k].oi, t:b.t} : m, {oi:-1, t:""});
    const who = wsc > 0.25 ? "WRITERS" : wsc < -0.25 ? "BUYERS" : "MIXED";
    const lean = k === "ce" ? -wsc : wsc;
    W.push(wgCard("oi"+k, `${stk} ${nm} OPEN INTEREST`, (cur.oi/1e6).toFixed(1)+"M",
      `${who}-built (score ${wsc >= 0 ? "+" : ""}${wsc}) · Δsession ${((cur.oi-first.oi)/1e6).toFixed(1)}M · ` +
      `peak ${(pk.oi/1e6).toFixed(1)}M @${pk.t} · flow ${(cur.oi_slope/1000).toFixed(0)}k/10m`,
      lean, `<div class="rr"><span>largest 10-min episodes:</span></div>` + oiEpisodes(bars, i, k)));
  }
  // build map — who built WHERE
  const bm = {};
  for(const k of ["ce","pe"]){
    let bo=0, bpx=0, uo=0, upx=0;
    for(let j=1; j<=i; j++){
      const d = bars[j][k].oi - bars[j-1][k].oi, px = bars[j].fut.c;
      if(d > 0){ bo += d; bpx += d*px; } else { uo -= d; upx += (-d)*px; }
    }
    bm[k] = {bo, bavg: bo ? bpx/bo : 0, uo, uavg: uo ? upx/uo : 0};
  }
  const rng = Math.max(...bars.map(b=>b.fut.h)) - Math.min(...bars.map(b=>b.fut.l)) || 1;
  const bmLean = clamp1((F - bm.ce.bavg)/rng) * 0.5 + clamp1((F - bm.pe.bavg)/rng) * 0.5;
  W.push(wgCard("bmap", "BUILD MAP — WHO BUILT WHERE", "FUT " + F.toFixed(0),
    `CE built ${(bm.ce.bo/1e6).toFixed(1)}M avg@${bm.ce.bavg.toFixed(0)} · ` +
    `PE built ${(bm.pe.bo/1e6).toFixed(1)}M avg@${bm.pe.bavg.toFixed(0)}`,
    bmLean,
    rr("CE", "built "+(bm.ce.bo/1e6).toFixed(1)+"M @"+bm.ce.bavg.toFixed(0),
       "unwound "+(bm.ce.uo/1e6).toFixed(1)+"M @"+bm.ce.uavg.toFixed(0)) +
    rr("PE", "built "+(bm.pe.bo/1e6).toFixed(1)+"M @"+bm.pe.bavg.toFixed(0),
       "unwound "+(bm.pe.uo/1e6).toFixed(1)+"M @"+bm.pe.uavg.toFixed(0)) +
    rr("price ABOVE a book's avg build px = its writers are underwater (squeeze fuel)")));
  // volume
  const last30 = bars.slice(-30);
  let vs=0, vd=0;
  for(const b of last30){ vs += b.fut.v; vd += b.fut.v * Math.sign(b.fut.c - b.fut.o); }
  const vLean = vs ? clamp1(vd/vs) : 0;
  const cvol = last30.reduce((s,b)=>s+b.ce.v,0), pvol = last30.reduce((s,b)=>s+b.pe.v,0);
  const topv = [...bars].sort((a,b)=>b.fut.v-a.fut.v).slice(0,5)
    .sort((a,b)=>S.tIdx[a.t]-S.tIdx[b.t]);
  W.push(wgCard("vol", "VOLUME", "rank " + bar.fut.vol_r.toFixed(2),
    `30m flow ${vd>=0?"up":"down"}-weighted ${(Math.abs(vLean)*100).toFixed(0)}% · ` +
    `CE:PE vol ${(cvol/1e6).toFixed(1)}M:${(pvol/1e6).toFixed(1)}M`,
    vLean, `<div class="rr"><span>biggest FUT bars:</span></div>` +
    topv.map(b => rr(b.t, Math.round(b.fut.v/1000)+"k", b.fut.o.toFixed(0)+"→"+b.fut.c.toFixed(0))).join("")));
  // vwap & bands
  const l60 = bars.slice(-60);
  const above = l60.filter(b => b.fut.c > b.fut.vwap).length / l60.length;
  const touches = {u2:0, d2:0, u3:0, d3:0};
  for(const b of bars){ if(b.fut.h > b.fut.u2) touches.u2++; if(b.fut.l < b.fut.d2) touches.d2++;
                        if(b.fut.h > b.fut.u3) touches.u3++; if(b.fut.l < b.fut.d3) touches.d3++; }
  W.push(wgCard("vwap", "VWAP & BANDS", "z " + bar.fut.z.toFixed(2),
    `VWAP ${bar.fut.vwap.toFixed(0)} · ${(above*100).toFixed(0)}% of last hour above · ` +
    `bandwidth p${Math.round(bar.fut.bw_r*100)}`,
    clamp1(bar.fut.z/2),
    rr("last hour above VWAP", (above*100).toFixed(0)+"%") +
    rr("bars beyond +2σ / −2σ", touches.u2 + " / " + touches.d2) +
    rr("bars beyond +3σ / −3σ", touches.u3 + " / " + touches.d3)));
  // levels / box
  const fl = c.floor, cp = c.cap;
  let lvLean = 0, lvSub = "no box yet";
  if(fl && cp){
    const pos = (F - fl[1]) / Math.max(cp[1] - fl[1], 1e-9);
    lvLean = clamp1((0.5 - pos) * 1.2);
    lvSub = `box ${fl[1]}–${cp[1]} · position ${(pos*100).toFixed(0)}% up the box`;
  }
  const lvEv = eventsUpTo(i).filter(e => e.kind==="BREAK" || e.kind==="FLIP-TEST").slice(-6);
  W.push(wgCard("lvl", "LEVELS & BOX", fl && cp ? `${fl[1]} / ${cp[1]}` : "—", lvSub, lvLean,
    (fl ? rr("floor", fl[1], fl[0]) : "") + (cp ? rr("cap", cp[1], cp[0]) : "") +
    lvEv.map(e => rr(e.t, e.kind, e.msg.slice(0, 42))).join("")));
  // setup / momentum
  const su = bar.setup;
  let suLean = 0, suHead = "—", suSub = "no spring seen yet";
  if(su){
    const wgt = {FIRED:1, ARMED:0.8, LOADING:0.6}[su.status] || 0.15;
    suLean = (su.dir === "UP" ? 1 : -1) * wgt;
    suHead = su.status;
    suSub = `${su.dir} from ${su.t0} · ref ${su.ref} · compression ${(su.comp*100).toFixed(0)}% · intensity ${(su.intensity*100).toFixed(0)}%`;
  }
  W.push(wgCard("setup", "MOMENTUM SETUP", suHead, suSub, suLean,
    su ? Object.entries(su).map(([k,v]) => rr(k, String(v))).join("") : ""));
  // traps
  const trapEv = eventsUpTo(i).filter(e => e.kind.startsWith("TRAP") || e.kind==="OI-PEAK-LAG");
  const lastTrap = trapEv[trapEv.length-1];
  let trLean = 0;
  if(lastTrap && minutesAgo(i, lastTrap.t) <= 35){
    const s = (lastTrap.data || {}).side || "";
    trLean = s.includes("BULL") || s === "UP" ? -0.7 : s.includes("BEAR") || s === "DN" ? 0.7 : 0;
  }
  W.push(wgCard("traps", "TRAPS & LATE CONVICTION", trapEv.length + " events",
    lastTrap ? `${lastTrap.t} ${lastTrap.kind}` : "none yet", trLean,
    trapEv.slice(-6).map(e => rr(e.t, e.kind, e.msg.slice(0, 44))).join("")));

  $("dvGrid").innerHTML = W.join("");
}

/* ---------- THE MAP: plain-language battle map (DATA -> MAP sub-view) ---------- */

const CONV = s => { s = Math.abs(s); return s > 0.8 ? "near-certain" : s > 0.5 ? "likely"
                                          : s > 0.25 ? "leaning" : "mixed"; };

function hotspotHTML(d){
  const shell = inner => `<div class="fc" id="hotCell"><label>STRIKE HOTSPOTS · today</label>${inner}</div>`;
  if(!d) return shell(`<b>—</b><span>reading the chain…</span>`);
  if(d.dead || !d.strikes) return shell(`<b>—</b><span>chain offline (replay mode)</span>`);
  const fmt = v => Math.abs(v) >= 1e6 ? (v/1e6).toFixed(1) + "M" : Math.round(v/1e3) + "k";
  const rows = [];
  for(const s of d.strikes){
    if(s.ce && s.ce.oi_chg) rows.push({ k: s.k, side: "CE", chg: s.ce.oi_chg, w: s.ce_w || 0 });
    if(s.pe && s.pe.oi_chg) rows.push({ k: s.k, side: "PE", chg: s.pe.oi_chg, w: s.pe_w || 0 });
  }
  rows.sort((a, b) => Math.abs(b.chg) - Math.abs(a.chg));
  const html = rows.slice(0, 3).map(r => {
    const who = r.chg < 0 ? "unwinding" : r.w > 0.25 ? "writers" : r.w < -0.25 ? "buyers" : "adding";
    const bull = r.chg > 0
      ? (r.side === "CE" ? r.w < -0.25 : r.w > 0.25)          // CE buyers / PE writers = bullish
      : (r.side === "PE");                                     // PE unwind = bear pressure off
    const col = r.chg === 0 ? "#93a3bd" : bull ? "#2ec27e" : "#ff5f6b";
    return `<span style="color:${col}">${r.k} ${r.side} ${r.chg > 0 ? "+" : "−"}${fmt(Math.abs(r.chg))} · ${who}</span>`;
  }).join("");
  const m = d.metrics || {};
  return shell(html +
    `<span>walls ${m.wall_dn ?? "—"} / ${m.wall_up ?? "—"} · max pain ${m.max_pain ?? "—"}</span>`);
}
const VOLW = r => r < 0.33 ? "QUIET" : r < 0.66 ? "NORMAL" : "LOUD";

function mapBannerTxt(bar, stk){
  const g = bar.gamma || {}, wce = g.w_ce ?? 0, wpe = g.w_pe ?? 0;
  const head = {
    CEILING: `SELLERS IN CONTROL AT ${stk}`,
    FLOOR: `BUYERS DEFENDING ${stk}`,
    PINNED: `PINNED TO ${stk} — BOTH SIDES SELL PREMIUM`,
    "AMPLIFIED-UP": "DEALERS CHASING PRICE UP",
    "AMPLIFIED-DOWN": "DEALERS CHASING PRICE DOWN",
  }[g.regime] || `TWO-SIDED AT ${stk} — NO ONE IN CONTROL`;
  const parts = [];
  if(wce > 0.25) parts.push(`call sellers cap rallies (${CONV(wce)})`);
  else if(wce < -0.25) parts.push(`call buyers bet on a rally (${CONV(wce)})`);
  if(wpe < -0.25) parts.push(`put buyers press lower (${CONV(wpe)})`);
  else if(wpe > 0.25) parts.push(`put sellers hold the floor (${CONV(wpe)})`);
  const z = bar.fut.z;
  parts.push(`price ${z > 0.5 ? "above" : z < -0.5 ? "below" : "near"} fair price ` +
             `on ${VOLW(bar.fut.vol_r).toLowerCase()} volume`);
  return { head, sub: parts.join(" · "), col: GAMMA_COL[g.regime] || "#8090a8" };
}

function renderMap(i, bar){
  if(!$("mapWrap")) return;
  const bars = S.day.bars.slice(0, i + 1);
  const g = bar.gamma || {}, c = bar.ctx || {}, F = bar.fut.c;
  const stk = Math.round(S.day.strike);

  const bn = mapBannerTxt(bar, stk);
  $("mapBanner").innerHTML =
    `<b style="color:${bn.col}">${bn.head}</b><span>${bn.sub}</span>` +
    `<i class="push">PUSH ${VOLW(bar.fut.vol_r)} · ${(bar.fut.vol_r*100).toFixed(0)}%</i>`;
  renderValidator(i, bar);

  // ----- collect the facts, then ZOOM to the action zone (not the whole day) -----
  let lo = 1e18, hi = -1e18, loT = "", hiT = "";
  for(const b of bars){
    if(b.fut.h > hi){ hi = b.fut.h; hiT = b.t; }
    if(b.fut.l < lo){ lo = b.fut.l; loT = b.t; }
  }
  const fl = c.floor, cp = c.cap;
  const wce = g.w_ce ?? 0, wpe = g.w_pe ?? 0;
  const ceM = (bar.ce.oi/1e6).toFixed(1), peM = (bar.pe.oi/1e6).toFixed(1);
  const drift = F - bars[Math.max(0, i-15)].fut.c;
  const drTxt = drift > 3 ? " · drifting up" : drift < -3 ? " · drifting down" : " · going nowhere";
  const trsAll = [];
  for(const e of eventsUpTo(i).filter(e => e.kind === "TRAP-SPRUNG" ||
      e.kind === "TRAP-SETTING" || e.kind === "SPRING-FAIL").slice(-6)){
    const bi = S.tIdx[e.t];
    if(bi != null && bars[bi]) trsAll.push({ p: bars[bi].fut.c, t: e.t, kind: e.kind });
  }
  const trs = [];                       // one flag per price area — keep the LATEST
  for(const t of trsAll.reverse()){
    if(trs.length < 3 && !trs.some(x => Math.abs(x.p - t.p) < 3)) trs.push(t);
  }
  const bm = {};
  for(const k of ["ce","pe"]){
    let bo = 0, bpx = 0;
    for(let j = 1; j <= i; j++){
      const d = bars[j][k].oi - bars[j-1][k].oi;
      if(d > 0){ bo += d; bpx += d * bars[j].fut.c; }
    }
    bm[k] = bo ? bpx / bo : 0;
  }
  // domain = where the fight is NOW: price, strike, walls, traps, fair zone,
  // last ~2h of trade. A far-away morning spike must NOT crush the map.
  const rec = bars.slice(-120);
  const pts = [F, stk, bar.fut.vwap, bar.fut.u1, bar.fut.d1,
               Math.min(...rec.map(b => b.fut.l)), Math.max(...rec.map(b => b.fut.h))];
  if(fl) pts.push(fl[1]);
  if(cp) pts.push(cp[1]);
  for(const t of trs) pts.push(t.p);
  if(bm.ce) pts.push(bm.ce);
  if(bm.pe) pts.push(bm.pe);
  let dLo = Math.min(...pts), dHi = Math.max(...pts);
  const pad = (dHi - dLo) * 0.12 || 1; dLo -= pad; dHi += pad;

  const box = $("mapSvg");                        // 1 viewBox unit = 1 CSS px
  const W = box.clientWidth || 780, H = box.clientHeight || 540;
  const GX = W - 250, XL = 10, PX = GX - 10;      // GX..W = label gutter
  const Y = v => 14 + (dHi - v) / (dHi - dLo) * (H - 28);
  const el = [];
  const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
  const txt = (x, y, s, col, size=10, bold=0) =>
    el.push(`<text x="${x}" y="${y}" fill="${col}" font-size="${size}" ` +
            `font-family="Consolas,monospace"${bold ? ' font-weight="700"' : ""}>${esc(s)}</text>`);

  // background zones
  const yU = Y(bar.fut.u1), yD = Y(bar.fut.d1);
  el.push(`<rect x="${XL}" y="${yU}" width="${PX-XL}" height="${Math.max(yD-yU,1)}" fill="rgba(74,168,255,.07)"/>`);
  const yS = Y(stk), maxOI = Math.max(bar.ce.oi, bar.pe.oi, 1);
  const thC = Math.min(24, Math.max(9, 24 * bar.ce.oi / maxOI));
  const thP = Math.min(24, Math.max(9, 24 * bar.pe.oi / maxOI));
  const ceCol = wce > 0.25 ? "255,95,107" : wce < -0.25 ? "46,194,126" : "102,116,140";
  const peCol = wpe > 0.25 ? "46,194,126" : wpe < -0.25 ? "255,95,107" : "102,116,140";
  el.push(`<rect x="${XL}" y="${yS-thC-1}" width="${PX-XL}" height="${thC}" fill="rgba(${ceCol},.18)"/>`);
  el.push(`<rect x="${XL}" y="${yS+1}" width="${PX-XL}" height="${thP}" fill="rgba(${peCol},.18)"/>`);
  if(thC >= 13) txt(XL+6, yS - thC/2 + 2,
      wce > 0.25 ? `SELLERS' WALL — ${ceM}M calls sold (${CONV(wce)})`
    : wce < -0.25 ? `call buyers ${ceM}M — betting on a rally`
    : `calls ${ceM}M — mixed hands`, `rgb(${ceCol})`, 10, 1);
  if(thP >= 13) txt(XL+6, yS + thP/2 + 5,
      wpe > 0.25 ? `PUT SELLERS' FLOOR — ${peM}M puts sold (${CONV(wpe)})`
    : wpe < -0.25 ? `put buyers ${peM}M — pressing for a fall (${CONV(wpe)})`
    : `puts ${peM}M — mixed hands`, `rgb(${peCol})`, 10, 1);

  // features: one price line + one gutter label each — labels can NEVER overlap
  const feats = [];
  const F8 = (p, t, col, o) => feats.push(Object.assign({ p, t, col }, o || {}));
  F8(bar.fut.vwap, `fair price ${bar.fut.vwap.toFixed(0)}`, "#4aa8ff", {dash:"4 4"});
  F8(stk, `strike ${stk}`, "#e8c15a", {w:1.4, size:10.5, bold:1});
  if(cp) F8(cp[1], `ceiling ${cp[1]} — ${cp[0]}`, "#ff5f6b", {dash:"6 3"});
  if(fl) F8(fl[1], `floor ${fl[1]} — ${fl[0]}`, "#2ec27e", {dash:"6 3"});
  if(hi <= dHi) F8(hi, `session high ${hi.toFixed(0)} @${hiT}`, "#8fa0bb", {dash:"2 3"});
  if(lo >= dLo) F8(lo, `session low ${lo.toFixed(0)} @${loT}`, "#8fa0bb", {dash:"2 3"});
  for(const t of trs)
    F8(t.p, `⚑ ${{ "TRAP-SPRUNG":"trap sprung", "TRAP-SETTING":"trap being set",
                   "SPRING-FAIL":"breakout failed" }[t.kind]} @${t.t}`, "#ffbf00", {dash:"1 3"});
  if(bm.ce) F8(bm.ce, `◆ call money in avg ${bm.ce.toFixed(0)}`, "#c98a90", {nol:1});
  if(bm.pe) F8(bm.pe, `◆ put money in avg ${bm.pe.toFixed(0)}`, "#7fae95", {nol:1});
  F8(F, `YOU ARE HERE ${F.toFixed(1)}${drTxt}`, "#e6edf7", {w:1.2, size:11, bold:1, you:1});

  // merge features sitting on the same price (e.g. strike == ceiling)
  feats.sort((a, b) => b.p - a.p);
  const merged = [];
  for(const f of feats){
    const m = merged[merged.length-1];
    if(m && !m.you && !f.you && !m.nol && !f.nol &&
       Math.abs(Y(m.p) - Y(f.p)) < 3){ m.t += ` = ${f.t}`; continue; }
    merged.push(f);
  }
  // lane-resolve the gutter: top-down min 13px apart, then pull back inside the box
  let prevLy = -1e9;
  for(const f of merged){
    f.y = Y(f.p);
    f.ly = Math.max(f.y, prevLy + 13, 12);
    prevLy = f.ly;
  }
  for(let j = merged.length - 1; j >= 0; j--){
    const maxLy = (j === merged.length - 1) ? H - 6 : merged[j+1].ly - 13;
    if(merged[j].ly > maxLy) merged[j].ly = maxLy;
  }
  for(const f of merged){
    if(f.t.length > 42) f.t = f.t.slice(0, 41) + "…";
    if(!f.nol) el.push(`<line x1="${XL}" y1="${f.y}" x2="${PX}" y2="${f.y}" stroke="${f.col}" ` +
      `stroke-width="${f.w || 1}"${f.dash ? ` stroke-dasharray="${f.dash}"` : ""}/>`);
    el.push(`<polyline points="${PX},${f.y} ${GX-4},${f.ly-3} ${GX},${f.ly-3}" fill="none" ` +
            `stroke="${f.col}" stroke-width="1" opacity=".4"/>`);
    if(f.you) el.push(`<circle cx="${PX-9}" cy="${f.y}" r="4.5" fill="#e6edf7"/>`);
    txt(GX+4, f.ly, f.t, f.col, f.size || 10, f.bold || 0);
  }
  // off-map extremes become edge chips instead of dead space
  if(hi > dHi) txt(XL+6, 13,
    `▲ session high ${hi.toFixed(0)} @${hiT} — ${(hi-F).toFixed(0)} pts above`, "#8fa0bb", 9.5);
  if(lo < dLo) txt(XL+6, H-5,
    `▼ session low ${lo.toFixed(0)} @${loT} — ${(F-lo).toFixed(0)} pts below`, "#8fa0bb", 9.5);

  $("mapSvg").innerHTML =
    `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${el.join("")}</svg>`;

  // ----- FLOW: what changed in the LAST 10 MINUTES (the pulse of the tape) -----
  const j0 = Math.max(0, i - 10);
  const fmtK = v => Math.abs(v) >= 1e6 ? (v/1e6).toFixed(1) + "M" : Math.round(v/1e3) + "k";
  const fcell = (nm, b0, b1, rank) => {
    const dOI = b1.oi - b0.oi, dPr = b1.c - b0.c;
    const who = dOI > 0 ? (dPr <= 0 ? "writers adding" : "buyers adding")
                        : (dPr >= 0 ? "writers covering" : "longs bailing");
    const MEAN = nm === "CALL"
      ? { "writers adding":   ["sellers cap upside — bearish", "#ff5f6b"],
          "buyers adding":    ["bulls betting on a rally — bullish", "#2ec27e"],
          "writers covering": ["call shorts forced out — bullish fuel", "#2ec27e"],
          "longs bailing":    ["bulls giving up — bearish", "#ff5f6b"] }
      : { "writers adding":   ["sellers defend downside — bullish", "#2ec27e"],
          "buyers adding":    ["bears betting on a fall — bearish", "#ff5f6b"],
          "writers covering": ["put shorts forced out — bearish fuel", "#ff5f6b"],
          "longs bailing":    ["bears cashing out — relief", "#8fa0bb"] };
    const [meaning, mcol] = MEAN[who];
    const hot = (rank ?? 0) > 0.85 || Math.abs(dPr) / Math.max(b1.c, 1) > 0.10;
    return `<div class="fc${hot ? " hot" : ""}">` +
      `<label>${nm} FLOW · 10m${hot ? " ⚡" : ""}</label>` +
      `<b style="color:${mcol}">${dOI >= 0 ? "▲" : "▼"} ${fmtK(Math.abs(dOI))} ` +
      `${dOI >= 0 ? "added" : "dropped"} · ${who}</b>` +
      `<span>${meaning} · premium ${dPr >= 0 ? "+" : ""}${dPr.toFixed(1)}</span></div>`;
  };
  const straddle = bar.ce.c + bar.pe.c;
  $("flowStrip").innerHTML =
    fcell("CALL", bars[j0].ce, bar.ce, bar.ce.oi_r) +
    fcell("PUT",  bars[j0].pe, bar.pe, bar.pe.oi_r) +
    `<div class="fc"><label>EXPECTED MOVE</label>` +
    `<b>±${straddle.toFixed(0)} pts by expiry</b>` +
    `<span>straddle-implied · 30m range ${c.rng30 != null ? Number(c.rng30).toFixed(0) : "—"} pts</span></div>` +
    `<div class="fc plan"><label>PLAN</label>` +
    ((c.plays && c.plays.length)
      ? `<div class="plays">${c.plays.slice(0, 2).map(playChip).join("")}</div>`
      : `<b style="color:${COL[S.states[i]] || "#8fa0bb"}">${c.verdict || "—"}</b>` +
        `<span>${(c.vwhy || "waiting for a setup").slice(0, 70)}</span>`) +
    `</div>` +
    hotspotHTML(S.mapChain);

  // keep the hotspots fresh: poll the chain every ~15s while the map is up
  if(!S.mapChainT || Date.now() - S.mapChainT > 15000){
    S.mapChainT = Date.now();
    fetch(IDXQ("/api/chain")).then(r => r.status === 404 ? {dead:1} : r.json())
      .then(d => {
        S.mapChain = (d && d.strikes) ? d : (d && d.dead ? {dead:1} : S.mapChain);
        const hc = $("hotCell");
        if(hc) hc.outerHTML = hotspotHTML(S.mapChain);
        if(S.day && S.mapChain && S.mapChain.strikes)   // populate strike dropdowns + refresh
          renderValidator(S.i, S.day.bars[S.i]);
      }).catch(() => {});
  }

  // the five questions
  const q = (id, ql, ans, ansCol, det) =>
    `<div class="mq${S.openWg.has(id) ? " open" : ""}" data-id="${id}">` +
    `<label>${ql}</label><b style="color:${ansCol || "#e6edf7"}">${ans}</b>` +
    `<div class="det">${det || ""}</div></div>`;
  const trapEv = eventsUpTo(i).filter(e => e.kind.startsWith("TRAP") || e.kind === "OI-PEAK-LAG");
  const lastTrap = trapEv[trapEv.length-1];
  const topv = [...bars].sort((a,b) => b.fut.v - a.fut.v).slice(0,4)
    .sort((a,b) => S.tIdx[a.t] - S.tIdx[b.t]);
  $("mapRail").innerHTML =
    q("q1", "WHO'S IN CONTROL?", bn.head.toLowerCase(), bn.col,
      `<div class="rr"><span>call book — biggest builds:</span></div>` + oiEpisodes(bars, i, "ce") +
      `<div class="rr"><span>put book — biggest builds:</span></div>` + oiEpisodes(bars, i, "pe")) +
    q("q2", "WHERE ARE THE WALLS?",
      `${cp ? cp[1] + " above" : "no ceiling yet"} · ${fl ? fl[1] + " below" : "no floor yet"}`, null,
      (cp ? rr("ceiling", cp[1], cp[0]) : "") + (fl ? rr("floor", fl[1], fl[0]) : "") +
      rr("strike " + stk, ceM + "M calls", peM + "M puts")) +
    q("q3", "HOW HARD IS THE PUSH?",
      `${VOLW(bar.fut.vol_r)} — ${(bar.fut.vol_r*100).toFixed(0)}% of normal${drTxt}`,
      bar.fut.vol_r > 0.66 ? "#ffbf00" : null,
      `<div class="rr"><span>biggest minutes:</span></div>` +
      topv.map(b => rr(b.t, Math.round(b.fut.v/1000)+"k", b.fut.o.toFixed(0)+"→"+b.fut.c.toFixed(0))).join("")) +
    q("q4", "ANY TRAPS?",
      lastTrap ? `${lastTrap.kind.replace(/-/g," ").toLowerCase()} @${lastTrap.t} · ${minutesAgo(i, lastTrap.t)}m ago`
               : "none today", lastTrap ? "#ffbf00" : null,
      trapEv.slice(-5).map(e => rr(e.t, e.kind, e.msg.slice(0,40))).join("")) +
    q("q5", "WHAT'S THE PLAY?", c.verdict || "—", COL[S.states[i]] || null,
      ((c.plays && c.plays.length)
        ? c.plays.map(p => `<div class="rr"><span>${p}</span></div>`).join("")
        : `<div class="rr"><span>no play offered — ${c.vwhy || "wait"}</span></div>`));
}

$("mapRail").onclick = e => {
  const m = e.target.closest(".mq"); if(!m) return;
  const id = m.dataset.id;
  S.openWg.has(id) ? S.openWg.delete(id) : S.openWg.add(id);
  m.classList.toggle("open");
};
$("rawBtn").onclick = () => $("legacyView").classList.toggle("raw");

/* ---------- TRADE VALIDATOR: score our method's confluence into one call ---------- */
const clamp01 = x => Math.max(0, Math.min(1, x));
function _pivAbove(piv, px){
  const v = Object.values(piv||{}).filter(x=>typeof x==="number" && x>px).sort((a,b)=>a-b);
  return v.length ? v[0] : px + 30;
}
function _pivBelow(piv, px){
  const v = Object.values(piv||{}).filter(x=>typeof x==="number" && x<px).sort((a,b)=>b-a);
  return v.length ? v[0] : px - 30;
}
function _sessFracLeft(t){                 // NSE 09:15–15:30 = 375 min
  const p = String(t||"09:15").split(":"), mins = (+p[0])*60 + (+p[1]);
  return clamp01((930 - mins) / 375);
}

function computeValidator(i, bar, opts){
  opts = opts || {};
  const vStrike = opts.strike !== undefined ? opts.strike : S.valStrike;
  const vSide   = opts.side   !== undefined ? opts.side   : S.valSide;
  const c = bar.ctx || {}, g = bar.gamma || {}, su = bar.setup || null;
  const st = S.states[i] || "", F = bar.fut.c;
  const regime = g.regime || "NEUTRAL";
  const wce = g.w_ce ?? 0, wpe = g.w_pe ?? 0, netw = wce + wpe;
  const br = c.breadth || "";
  const ch = (S.mapChain && S.mapChain.metrics) ? S.mapChain.metrics : null;

  // ---- directional bias (auto candidate) ----
  let B = 0;
  if(st === "TREND-UP") B += 2; else if(st === "TREND-DOWN") B -= 2;
  if(su && ["ARMED","FIRED","LOADING"].includes(su.status))
    B += (su.dir === "UP" ? 1 : -1) * (1 + (su.intensity || 0));
  if(regime === "FLOOR" || regime === "AMPLIFIED-UP") B += 1;
  else if(regime === "CEILING" || regime === "AMPLIFIED-DOWN") B -= 1;
  if(wpe > 0.25) B += 1;
  if(wce > 0.25) B -= 1;
  if(br.includes("STRONG BULL")) B += 2; else if(br.includes("LEAN BULL")) B += 1;
  else if(br.includes("STRONG BEAR")) B -= 2; else if(br.includes("LEAN BEAR")) B -= 1;
  if(ch){
    if(ch.pcr_oi != null){ if(ch.pcr_oi > 1.1) B += 0.5; else if(ch.pcr_oi < 0.9) B -= 0.5; }
    const sq = ch.squeeze || {};
    if(sq.side === "UP") B += 0.5; else if(sq.side === "DOWN") B -= 0.5;
    const sk = ch.iv && ch.iv.skew != null ? ch.iv.skew : null;
    if(sk != null){ if(sk > 0.005) B -= 0.5; else if(sk < -0.005) B += 0.5; }
  }
  const autoDir = B > 0.5 ? "LONG" : B < -0.5 ? "SHORT" : "NONE";
  const forced = vSide && vSide !== "AUTO" ? vSide : null;
  const dir = forced || autoDir;
  const bull = dir === "LONG", sgn = bull ? 1 : -1;

  // ---- weighted confidence for `dir` ----
  const checks = [];
  let score = 0;
  const add = (label, a, weight, detail) => {
    const got = a * weight; score += got;
    checks.push({label, ok: a >= 0.6, got: Math.round(got), weight, detail});
  };
  if(dir !== "NONE"){
    // 1 state/trend (20)
    let a = 0;
    if((bull && st==="TREND-UP") || (!bull && st==="TREND-DOWN")) a = 1;
    else if(st==="ARMED" && su && ((bull&&su.dir==="UP")||(!bull&&su.dir==="DOWN"))) a = 0.7;
    else if(st==="COILING") a = 0.35;
    else if(st==="BALANCE" || st==="OPENING") a = 0.15;
    add("Tape state", a, 20, st || "—");
    // 2 verdict (15)
    const V = c.verdict || "";
    let av = {GO:1, READY:0.8, WAIT:0.4, CAUTION:0.25, "STAND ASIDE":0.1, SPENT:0.05}[V];
    add("Verdict", av==null ? 0.2 : av, 15, V || "—");
    // 3 momentum setup (15)
    let am = 0, mwhy = "no setup";
    if(su){
      const aligned = (bull&&su.dir==="UP")||(!bull&&su.dir==="DOWN");
      if(aligned){ am = ({FIRED:1, ARMED:0.85, LOADING:0.5}[su.status]||0) * (0.6 + 0.4*(su.intensity||0));
        mwhy = `${su.status} ${su.dir} · intensity ${Math.round((su.intensity||0)*100)}%`; }
      else if(["FIRED","ARMED"].includes(su.status)) mwhy = `${su.status} ${su.dir} (against)`;
    }
    add("Momentum setup", am, 15, mwhy);
    // 4 gamma regime (12)
    let ag = 0.3;
    if(bull && (regime==="FLOOR"||regime==="AMPLIFIED-UP")) ag = 1;
    else if(!bull && (regime==="CEILING"||regime==="AMPLIFIED-DOWN")) ag = 1;
    else if(regime==="PINNED") ag = 0.2; else if(regime==="NEUTRAL") ag = 0.4; else ag = 0.1;
    add("Dealer gamma", ag, 12, regime);
    // 5 writer walls (10)
    const aw = bull ? clamp01(0.5 + 0.5*wpe - 0.5*Math.max(0,wce))
                    : clamp01(0.5 + 0.5*wce - 0.5*Math.max(0,wpe));
    add("Writer walls", aw, 10, `call cap ${wce.toFixed(2)} · put floor ${wpe.toFixed(2)}`);
    // 6 breadth (10)
    let bv = 0;
    if(br.includes("STRONG BULL")) bv = 2; else if(br.includes("LEAN BULL")) bv = 1;
    else if(br.includes("STRONG BEAR")) bv = -2; else if(br.includes("LEAN BEAR")) bv = -1;
    add("Breadth", clamp01(0.5 + sgn*bv*0.25), 10, br || "MIXED");
    // 7 volume (8)
    const vr = bar.fut.vol_r ?? 0;
    add("Volume", clamp01(vr), 8, `${Math.round(vr*100)}% of day`);
    // 8 chain confirm (10)
    if(ch){
      let v = 0, parts = [];
      if(ch.pcr_oi!=null){ v += sgn*(ch.pcr_oi>1.1?1:ch.pcr_oi<0.9?-1:0); parts.push(`PCR ${ch.pcr_oi}`); }
      const sq = ch.squeeze||{}; if(sq.side){ v += sgn*(sq.side==="UP"?1:-1)*(sq.score>=0.3?1:0.5); parts.push(`squeeze ${sq.side}`); }
      const sk = ch.iv && ch.iv.skew!=null ? ch.iv.skew : null;
      if(sk!=null){ v += sgn*(sk>0.005?-1:sk<-0.005?1:0); parts.push(`skew ${(sk*100).toFixed(1)}`); }
      add("Chain confirm", clamp01(0.5 + v*0.2), 10, parts.join(" · ") || "—");
    } else add("Chain confirm", 0.5, 10, "chain not loaded — neutral");
  }

  // ---- method gates / vetoes ----
  const gates = [];
  let conf = score;
  const V = c.verdict || "";
  if(V==="STAND ASIDE" || V==="SPENT"){ conf *= 0.4; gates.push(`method verdict is ${V} — size down or skip`); }
  if(netw < -0.3 && (regime==="AMPLIFIED-UP"||regime==="AMPLIFIED-DOWN")){
    const ampDir = regime==="AMPLIFIED-UP" ? "LONG" : "SHORT";
    if(dir !== ampDir && dir !== "NONE"){ conf *= 0.5; gates.push("negative gamma — don't fade, trade WITH the move"); }
  }
  if(regime==="PINNED" && dir!=="NONE"){ conf *= 0.8; gates.push("pinned — dealers fade extremes, expect chop"); }

  // ---- optional: manual strike fit (validate a specific strike's option) ----
  let strikeInfo = null;
  if(vStrike && dir !== "NONE"){
    const rows = S.mapChain && S.mapChain.strikes;
    if(rows && rows.length){
      let row = null, best = 1e9;
      for(const s of rows){ const d = Math.abs(s.k - vStrike); if(d < best){ best = d; row = s; } }
      const spot = S.mapChain.spot || F;
      const optKey = bull ? "ce" : "pe";              // long view → call, short → put
      const opt = (row && row[optKey]) || {};
      const w = bull ? (row.ce_w ?? 0) : (row.pe_w ?? 0);   // writers at THIS strike, your side
      const otm = bull ? (row.k - spot) : (spot - row.k);   // >0 OTM, <0 ITM
      const otmPct = Math.abs(otm) / Math.max(spot, 1);
      const delta = opt.delta != null ? Math.abs(opt.delta) : null;
      let fit = 1;
      if(otm > 0) fit *= clamp01(1 - otmPct / 0.02);   // deep OTM needs a big move
      else fit *= 0.9;                                  // ITM: fine, just costlier
      if(w > 0.3) fit *= (1 - 0.35 * clamp01(w));       // heavy same-side writers cap you
      if(delta != null) fit *= clamp01(0.45 + delta);   // very low delta = lottery ticket
      fit = clamp01(fit);
      const oppo = (bull ? row.pe : row.ce) || {};        // the other side at this strike
      strikeInfo = {
        k: row.k, opt: optKey.toUpperCase(),
        moneyness: otm > 3 ? `${Math.abs(otm).toFixed(0)} pts OTM`
                 : otm < -3 ? `${Math.abs(otm).toFixed(0)} pts ITM` : "ATM",
        prem: opt.ltp, delta, iv: opt.iv, oi: opt.oi, oiChg: opt.oi_chg, w, fit,
        vol: opt.vol, avg: opt.avg,                        // for the market-activity read
        oppW: bull ? (row.pe_w ?? 0) : (row.ce_w ?? 0),
        oppOiChg: oppo.oi_chg,
        fitLbl: fit >= 0.7 ? "GOOD" : fit >= 0.4 ? "OK" : "POOR",
        wallNote: w > 0.3 ? `${bull ? "call" : "put"} writers heavy here — resistance to your ${bull ? "CE" : "PE"}`
                : w < -0.3 ? `${bull ? "call" : "put"} buyers here — flow with you` : "neutral book here"
      };
      conf = conf * (0.6 + 0.4 * fit);                  // strike fit nudges the score
    } else strikeInfo = { noChain: true };
  }

  if(dir==="NONE") conf = Math.min(conf, 20);
  conf = Math.max(0, Math.min(100, Math.round(conf)));
  const band = conf>=70 ? "STRONG" : conf>=50 ? "MODERATE" : conf>=30 ? "WEAK" : "NO-TRADE";

  // ---- entry + laddered targets (T1/T2/T3) & structural stop ----
  // sources: VWAP σ bands (u/d 1-3), day pivots (P,R,S), engine wall box (cap/floor)
  const fl = c.floor, cp = c.cap, piv = S.day.pivots || {}, entry = F, ft = bar.fut;
  const sref = su && ["ARMED","FIRED","LOADING"].includes(su.status) ? su.ref : null;
  let targets = [], stop=null, stopName="";
  if(dir !== "NONE"){
    const cand = [];
    const push = (px,name,rank) => { if(px!=null && isFinite(px)) cand.push({px,name,rank}); };
    if(bull){                                         // rank: wall 0 > pivot 1 > σ-band 2
      push(ft.u1,"+1σ",2); push(ft.u2,"+2σ",2); push(ft.u3,"+3σ",2);
      for(const [k,v] of Object.entries(piv)) if(typeof v==="number" && v>entry) push(v,k,1);
      if(cp && cp[1]>entry) push(cp[1],cp[0],0);
    } else {
      push(ft.d1,"−1σ",2); push(ft.d2,"−2σ",2); push(ft.d3,"−3σ",2);
      for(const [k,v] of Object.entries(piv)) if(typeof v==="number" && v<entry) push(v,k,1);
      if(fl && fl[1]<entry) push(fl[1],fl[0],0);
    }
    const beyond = cand.filter(x => bull ? x.px > entry+1 : x.px < entry-1)
                       .sort((a,b) => Math.abs(a.px-entry) - Math.abs(b.px-entry));
    const picked = [];
    for(const x of beyond){                           // dedupe within ~5 pts, keep stronger source
      const dup = picked.find(p => Math.abs(p.px - x.px) <= 5);
      if(dup){ if(x.rank < dup.rank){ dup.px = x.px; dup.name = x.name; dup.rank = x.rank; } continue; }
      picked.push({...x});
      if(picked.length >= 3) break;
    }
    targets = picked.map(p => ({px:p.px, name:p.name}));
    // stop = nearest protective level against the trade
    const scand = [];
    const spush = (px,name) => { if(px!=null && isFinite(px)) scand.push({px,name}); };
    if(bull){
      spush(sref,"setup invalidation"); if(fl && fl[1]<entry) spush(fl[1],fl[0]);
      spush(ft.d1,"−1σ"); spush(_pivBelow(piv,entry),"pivot");
      const below = scand.filter(x=>x.px<entry-1).sort((a,b)=> b.px-a.px);
      if(below[0]){ stop=below[0].px; stopName=below[0].name; }
    } else {
      spush(sref,"setup invalidation"); if(cp && cp[1]>entry) spush(cp[1],cp[0]);
      spush(ft.u1,"+1σ"); spush(_pivAbove(piv,entry),"pivot");
      const above = scand.filter(x=>x.px>entry+1).sort((a,b)=> a.px-b.px);
      if(above[0]){ stop=above[0].px; stopName=above[0].name; }
    }
    if(stop==null){ stop = bull ? _pivBelow(piv,entry) : _pivAbove(piv,entry); stopName="pivot"; }
  }
  const t1 = targets.length ? targets[0].px : null;
  const straddle = (bar.ce.c||0) + (bar.pe.c||0);
  const em = straddle * Math.sqrt(Math.max(_sessFracLeft(bar.t), 0.02));
  const rr = (t1!=null && stop!=null && Math.abs(entry-stop) > 1e-6)
    ? Math.abs(t1-entry) / Math.abs(entry-stop) : null;

  return { dir, autoDir, forced: !!forced, conf, band, checks, gates,
           entry, targets, tgt:t1, tgtName: targets.length?targets[0].name:"", stop, stopName, rr,
           em, emUp: entry+em, emDn: entry-em, straddle, regime, verdict: V, strikeInfo };
}

function _expShort(x){
  if(!x) return "—";
  const m = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const p = String(x).split("-");
  return p.length === 3 ? (+p[2]) + " " + m[(+p[1]) - 1] : x;
}
function _nearestK(ks, v){ let b = ks[0], d = 1e9; for(const k of ks){ const e = Math.abs(k-v); if(e < d){ d = e; b = k; } } return b; }
function fillStrikeSelects(){
  const ce = $("valCeSel"), pe = $("valPeSel"), ex = $("valExpSel");
  if(!ce || !pe) return;
  if(ex){
    const xp = (S.mapChain && S.mapChain.expiry) || (S.data && S.data.expiry) || "";
    if(ex.dataset.xp !== xp){ ex.dataset.xp = xp; ex.innerHTML = `<option>${_expShort(xp)}</option>`; }
  }
  const rows = S.mapChain && S.mapChain.strikes;
  if(!rows || !rows.length) return;
  let ks = rows.map(s => s.k).sort((a,b) => a-b);
  const atm = S.mapChain.atm;                        // clamp to ATM ±6 strikes
  if(atm != null && ks.length){
    let ci = 0, best = Infinity;
    ks.forEach((k, idx) => { const d = Math.abs(k - atm); if(d < best){ best = d; ci = idx; } });
    ks = ks.slice(Math.max(0, ci - 6), ci + 7);
  }
  const sig = ks.length + ":" + ks[0] + ":" + ks[ks.length-1];
  if(ce.dataset.sig === sig) return;                 // already built for this chain
  ce.dataset.sig = sig; pe.dataset.sig = sig;
  const opts = `<option value="">—</option>` + ks.map(k => `<option value="${k}">${k}</option>`).join("");
  ce.innerHTML = opts; pe.innerHTML = opts;
  if(S.valStrike && S.valSide === "LONG") ce.value = String(_nearestK(ks, S.valStrike));
  if(S.valStrike && S.valSide === "SHORT") pe.value = String(_nearestK(ks, S.valStrike));
}

// plain-English read of what participants are doing with THIS option at THIS strike
function _optMarket(s){
  const isCall = s.opt === "CE", k = s.k, w = s.w ?? 0, oc = s.oiChg;
  const num = x => x==null ? "—" : Math.abs(x)>=1e5 ? (x/1e5).toFixed(1)+"L"
                 : Math.abs(x)>=1e3 ? Math.round(x/1e3)+"k" : ""+Math.round(x);
  const side = isCall ? "call" : "put";
  const barrier = isCall ? "ceiling (resistance)" : "floor (support)";
  const beyond = isCall ? "above" : "below";
  let head, col;
  if(w > 0.25){                                        // net writing = someone selling this option
    col = isCall ? "var(--dn)" : "var(--up)";
    head = `${side} writers are SELLING ${k}` +
      (oc>0 ? ` and adding — building a ${barrier} here` :
       oc<0 ? ` but easing — the ${barrier} is thinning` : ` — a ${barrier} sits here`);
  } else if(w < -0.25){                                // net buying of this option
    col = isCall ? "var(--up)" : "var(--dn)";
    head = `${side}s are being BOUGHT at ${k}` +
      (oc>0 ? ` on rising OI — fresh bets on a break ${beyond} ${k}` :
       oc<0 ? ` as OI falls — likely short-covering` : ` — leaning for a move ${beyond} ${k}`);
  } else {
    col = "#c6d2e4";
    head = oc>0 ? `two-way flow at ${k}, OI building — no clear control yet`
         : oc<0 ? `OI unwinding at ${k} — positions being closed` : `quiet at ${k} — little activity`;
  }
  const det = [];
  if(oc!=null) det.push(`OI ${oc>=0?"+":""}${num(oc)}`);
  if(s.vol!=null && s.oi){
    const churn = s.vol / Math.max(s.oi,1);
    det.push(`${num(s.vol)} traded on ${num(s.oi)} OI ${churn>1?"(heavy churn)":churn>0.3?"(active)":"(light)"}`);
  }
  if(s.prem!=null && s.avg)
    det.push(s.prem > s.avg*1.02 ? "premium bid up vs day-avg (buyers lifting)"
           : s.prem < s.avg*0.98 ? "premium offered below day-avg (sellers pressing)"
           : "premium near its day-avg");
  const oppSide = isCall ? "put" : "call", ow = s.oppW ?? 0, ooc = s.oppOiChg;
  let ctx = "";
  if(ow > 0.25) ctx = `meanwhile ${oppSide} writers are active${ooc>0?" & adding":""} — a ${isCall?"floor":"ceiling"} is forming at ${k} too`;
  else if(ow < -0.25) ctx = `meanwhile ${oppSide}s are being bought${ooc>0?" (fresh)":""} at ${k}`;
  else if(ooc!=null) ctx = `other side (${oppSide}): OI ${ooc>=0?"+":""}${num(ooc)}`;
  return { head, col, det, ctx };
}

function renderValidator(i, bar){
  const box = $("validatorCard"); if(!box) return;
  const modal = $("valModal");                       // only work while the popup is open
  if(modal && modal.classList.contains("hidden")) return;
  const body = $("valBody") || box;
  fillStrikeSelects();
  const r = computeValidator(i, bar);
  const met = (S.mapChain && S.mapChain.metrics) || {};
  const bandCol = r.band==="STRONG" ? "var(--up)" : r.band==="MODERATE" ? "#e8c15a"
                : r.band==="WEAK" ? "#e0975a" : "#8fa0bb";
  const px = v => v==null ? "—" : v.toFixed(0);
  const rrTxt = r.rr==null ? "—" : r.rr.toFixed(2);
  const rrCol = r.rr==null ? "#8fa0bb" : r.rr>=1.5 ? "var(--up)" : r.rr>=1 ? "#e8c15a" : "var(--dn)";
  const dirEnglish = d => d==="LONG" ? "BULLISH" : d==="SHORT" ? "BEARISH" : "NO CLEAR EDGE";

  // ===== SECTION 1: what to do with THIS option (or the method read if none picked) =====
  const s = r.strikeInfo;
  let actionHTML;
  if(s && !s.noChain){
    const isCall = s.opt === "CE";
    const optName = `${s.k} ${isCall ? "CE · call" : "PE · put"}`;
    const betWord = isCall ? "bullish" : "bearish";
    const betCol  = isCall ? "var(--up)" : "var(--dn)";
    const agrees  = r.dir === r.autoDir;           // buying it agrees with the method's read
    let verb, verbCol, oneLine, altLine = "";
    if(agrees && r.conf >= 45){
      verb = "BUY IT"; verbCol = "var(--up)";
      oneLine = `go <b>LONG the ${isCall?"call":"put"}</b> (buy it) — you profit if NIFTY ${isCall?"rises":"falls"}, which is what the method reads.`;
    } else if(agrees){
      verb = "BUY — SMALL"; verbCol = "#e8c15a";
      oneLine = `a ${betWord} bet that lines up with the method, but confluence is thin (${r.conf}/100) — keep size small.`;
    } else {
      verb = "DON'T BUY"; verbCol = "var(--dn)";
      oneLine = `buying this ${isCall?"call":"put"} is a ${betWord} bet, but the method leans ${dirEnglish(r.autoDir)} — you'd be fighting the tape.`;
      altLine = `<div class="valt">↳ aligned play: <b>WRITE / SHORT</b> this ${isCall?"call":"put"} instead (sell it, collect ${s.prem!=null?"≈₹"+s.prem.toFixed(0):"premium"} — advanced, needs margin), or simply buy a ${isCall?"PUT":"CALL"}.</div>`;
    }
    actionHTML =
      `<div class="vaction">` +
        `<div class="vact-l"><span class="vverb" style="color:${verbCol}">${verb}</span>` +
          `<b class="vopt">${optName}</b><em style="color:${betCol}">${betWord} bet</em></div>` +
        `<div class="vconf"><b style="color:${bandCol}">${r.conf}</b><i>/100 · ${r.band}</i></div>` +
      `</div>` +
      `<div class="voneline">${oneLine}</div>${altLine}`;
  } else {
    const dCol = r.autoDir==="LONG" ? "var(--up)" : r.autoDir==="SHORT" ? "var(--dn)" : "#8fa0bb";
    const guide = r.autoDir==="LONG" ? "favour <b>buying CALLS</b> (or writing puts)"
                : r.autoDir==="SHORT" ? "favour <b>buying PUTS</b> (or writing calls)"
                : "stand aside — no side has the edge";
    actionHTML =
      `<div class="vaction">` +
        `<div class="vact-l"><span class="vverb" style="color:${dCol}">METHOD READ</span>` +
          `<b class="vopt" style="color:${dCol}">${dirEnglish(r.autoDir)}</b></div>` +
        `<div class="vconf"><b style="color:${bandCol}">${r.conf}</b><i>/100 · ${r.band}</i></div>` +
      `</div>` +
      `<div class="voneline">${guide}. Pick a <b>CE</b> or <b>PE</b> above to validate that exact option.</div>`;
  }

  // ===== SECTION 2: the option's own numbers =====
  let optHTML = "";
  if(s && !s.noChain){
    const fitCol = s.fitLbl==="GOOD" ? "var(--up)" : s.fitLbl==="OK" ? "#e8c15a" : "var(--dn)";
    const oiTxt = s.oiChg!=null ? (s.oiChg>=0?"+":"")+Math.round(s.oiChg/1000)+"k" : "—";
    const oiWord = s.oiChg==null ? "" : s.oiChg>0 ? "OI being ADDED here — fresh positions building. "
                 : s.oiChg<0 ? "OI being CUT here — positions unwinding. " : "";
    const cell = (lbl,val,col) => `<div><i>${lbl}</i><b${col?` style="color:${col}"`:""}>${val}</b></div>`;
    optHTML =
      `<div class="vsec"><div class="vsecH">THE OPTION</div><div class="voi">` +
        cell("premium", s.prem!=null?"₹"+s.prem.toFixed(1):"—") +
        cell("moneyness", s.moneyness) +
        cell("delta", s.delta!=null?s.delta.toFixed(2):"—") +
        cell("IV", s.iv!=null?(s.iv*100).toFixed(1)+"%":"—") +
        cell("OI change", oiTxt) +
        cell("strike fit", s.fitLbl, fitCol) +
      `</div><div class="vnote">${oiWord}${s.wallNote}.</div></div>`;
  } else if(s && s.noChain){
    optHTML = `<div class="vsec warn">strike validation needs the live CHAIN feed — not loaded yet</div>`;
  }

  // ===== SECTION 2b: what the market is doing with this option, right now =====
  let mktHTML = "";
  if(s && !s.noChain){
    const m = _optMarket(s);
    mktHTML =
      `<div class="vsec"><div class="vsecH">WHAT THE MARKET IS DOING HERE</div>` +
      `<div class="vmkt" style="color:${m.col}">${m.head}.</div>` +
      (m.det.length ? `<div class="vnote">${m.det.join(" · ")}</div>` : "") +
      (m.ctx ? `<div class="vnote ctx">${m.ctx}.</div>` : "") +
      `</div>`;
  }

  // ===== SECTION 3: structural method — laddered T1/T2/T3 + stop =====
  const tgs = r.targets || [];
  const tSpans = tgs.map((t,ix) =>
    `<span class="tlv">T${ix+1} <b style="color:var(--up)">${px(t.px)}</b> <em>${t.name||""}</em>` +
    ` <u>${r.entry!=null?(Math.round(Math.abs(t.px-r.entry)))+"p":""}</u></span>`).join("");
  const structHTML =
    `<div class="vsec"><div class="vsecH">STRUCTURAL METHOD <em>— levels on NIFTY futures</em></div>` +
    `<div class="vlevels vladder">` +
      `<span>ENTRY <b>${px(r.entry)}</b></span>` + tSpans +
      `<span class="stp">STOP <b style="color:var(--dn)">${px(r.stop)}</b> <em>${r.stopName||""}</em></span>` +
      `<span>R:R <b style="color:${rrCol}">${rrTxt}</b> <em>to T1</em></span>` +
    `</div>` +
    `<div class="vem">expected move ±${r.em.toFixed(0)} pts → ${px(r.emDn)}–${px(r.emUp)} by close (ATM straddle ${r.straddle.toFixed(0)})</div>` +
    r.gates.map(g => `<div class="vgate">⚠ ${g}</div>`).join("") +
    `</div>`;

  // ===== SECTION 4: OI & positioning (who is defending where) =====
  let oiSecHTML = "";
  const skew = met.iv && met.iv.skew!=null ? met.iv.skew : null;
  const sq = met.squeeze || {};
  const rows = [];
  const orow = (lbl,val,note) => `<div><i>${lbl}</i><b>${val}</b><u>${note}</u></div>`;
  if(met.pcr_oi!=null) rows.push(orow("PCR (put ÷ call OI)", met.pcr_oi,
    met.pcr_oi<0.9 ? "call-heavy — sellers defending upside (leans bearish)"
    : met.pcr_oi>1.1 ? "put-heavy — buyers defending downside (leans bullish)" : "balanced book"));
  if(met.max_pain!=null) rows.push(orow("max pain", met.max_pain, "where most options expire worthless — price often drifts here into expiry"));
  if(met.wall_up!=null) rows.push(orow("call wall", met.wall_up, "biggest overhead supply — resistance"));
  if(met.wall_dn!=null) rows.push(orow("put wall", met.wall_dn, "biggest downside cushion — support"));
  if(sq.side) rows.push(orow("squeeze", sq.side,
    sq.side==="UP" ? "trapped call writers may cover → fuel a pop UP" : "trapped put writers may cover → fuel a flush DOWN"));
  if(skew!=null) rows.push(orow("IV skew", (skew*100).toFixed(1),
    skew>0.005 ? "puts pricier — paying up for downside protection (fear)"
    : skew<-0.005 ? "calls pricier — chasing upside (greed)" : "flat — no directional fear"));
  if(rows.length)
    oiSecHTML = `<div class="vsec"><div class="vsecH">OI &amp; POSITIONING</div><div class="voiList">${rows.join("")}</div></div>`;

  // ===== SECTION 5: the scorecard (always shown — every method condition) =====
  const checksHTML = r.checks.map(c =>
    `<div class="vck"><span class="${c.ok?"y":"n"}">${c.ok?"✓":"○"}</span>` +
    `<span class="vl">${c.label}</span><span class="vd">${c.detail}</span>` +
    `<span class="vp">+${c.got}/${c.weight}</span></div>`).join("");
  const scoreHTML = r.checks.length
    ? `<div class="vsec"><div class="vsecH">WHY THIS SCORE <em>— method conditions, weighted to 100</em></div>` +
      `<div class="vchecks open">${checksHTML}</div></div>` : "";

  box.className = r.band==="STRONG" ? "hotv" : "";
  body.innerHTML = actionHTML + optHTML + mktHTML + structHTML + oiSecHTML + scoreHTML;
}

$("validatorCard").onclick = e => {
  if(e.target.closest(".vwhy")){
    S.openWg.has("val") ? S.openWg.delete("val") : S.openWg.add("val");
    if(S.day) renderValidator(S.i, S.day.bars[S.i]);
  }
};
// picking a strike only STAGES it — arm the VALIDATE button, don't score yet
function _armVal(){ const g = $("valGo"); if(g) g.classList.add("armed"); }
$("valCeSel").onchange = e => { if(e.target.value) $("valPeSel").value = ""; _armVal(); };
$("valPeSel").onchange = e => { if(e.target.value) $("valCeSel").value = ""; _armVal(); };
$("valGo").onclick = () => {
  const cv = parseFloat($("valCeSel").value), pv = parseFloat($("valPeSel").value);
  if(isFinite(cv)){ S.valSide = "LONG"; S.valStrike = cv; }
  else if(isFinite(pv)){ S.valSide = "SHORT"; S.valStrike = pv; }
  else return;                                  // nothing picked — nothing to validate
  $("valGo").classList.remove("armed");
  if(S.day) renderValidator(S.i, S.day.bars[S.i]);
};
$("valAtm").onclick = () => {
  S.valSide = "AUTO"; S.valStrike = null;
  const ce = $("valCeSel"), pe = $("valPeSel");
  if(ce) ce.value = ""; if(pe) pe.value = "";
  const g = $("valGo"); if(g) g.classList.remove("armed");
  if(S.day) renderValidator(S.i, S.day.bars[S.i]);
};

/* ---------- VALIDATE-A-TRADE popup: open from the DATA bar, stays live ---------- */
async function refreshValModal(){
  try{
    const d = await (await fetch(IDXQ("/api/chain"), {cache:"no-store"})).json();
    if(d && d.strikes){ S.mapChain = d; S.mapChainT = Date.now(); }
  }catch(e){ /* keep last snapshot */ }
  const body = $("valBody");
  if(!S.day){ if(body) body.innerHTML = `<div class="vstrike warn">load a session first</div>`; return; }
  renderValidator(S.i, S.day.bars[S.i]);
}
function openValModal(){
  const m = $("valModal"); if(!m) return;
  m.classList.remove("hidden");
  refreshValModal();
  if(!S.valModalTimer) S.valModalTimer = setInterval(refreshValModal, 5000);
}
function closeValModal(){
  const m = $("valModal"); if(m) m.classList.add("hidden");
  if(S.valModalTimer){ clearInterval(S.valModalTimer); S.valModalTimer = null; }
}
$("openVal").onclick = openValModal;
$("valClose").onclick = closeValModal;
$("valModalBack").onclick = closeValModal;
document.addEventListener("keydown", e => {
  if(e.target.matches?.("input, select, textarea")) return;   // don't hijack typing
  if(e.key === "Escape"){
    if(!$("valModal").classList.contains("hidden")) closeValModal();
    return;
  }
  if(!$("valModal").classList.contains("hidden")) return;    // modal owns the keys
  if(!S.day) return;
  const last = S.day.bars.length - 1;
  if(e.key === " "){ e.preventDefault(); togglePlay(); }
  else if(e.key === "ArrowLeft" && !e.shiftKey){ seek(Math.max(0, S.i - 1)); }
  else if(e.key === "ArrowRight" && !e.shiftKey){ seek(Math.min(last, S.i + 1)); }
  else if(e.key === "ArrowLeft" && e.shiftKey){ seekEvent(-1); }
  else if(e.key === "ArrowRight" && e.shiftKey){ seekEvent(+1); }
  else if(e.key === "Home"){ seek(0); }
  else if(e.key === "End"){ seek(last); }
});

// jump to the nearest LOUD event before (dir<0) or after (dir>0) the cursor
function seekEvent(dir){
  const here = S.i;
  let best = null;
  for(const ev of S.day.events){
    if(!LOUD.has(ev.kind)) continue;
    const j = S.tIdx[ev.t];
    if(j === undefined) continue;
    if(dir < 0 && j < here && (best === null || j > best)) best = j;
    if(dir > 0 && j > here && (best === null || j < best)) best = j;
  }
  if(best !== null) seek(best);
}

$("vTape").onclick = () => {
  document.body.classList.remove("dataMode");
  $("vTape").classList.add("active"); $("vData").classList.remove("active");
  lsSet("view", "tape");
  chainStop();
};
$("vData").onclick = () => {
  document.body.classList.add("dataMode");
  $("vData").classList.add("active"); $("vTape").classList.remove("active");
  lsSet("view", "data");
  chainStart();
};

// header index switcher: reload the chosen index from scratch
$("idxTabs").onclick = e => {
  const b = e.target.closest("button[data-idx]"); if(!b) return;
  const idx = b.dataset.idx; if(idx === S.index) return;
  S.index = idx;
  lsSet("index", idx);
  [...$("idxTabs").children].forEach(c => c.classList.toggle("active", c === b));
  // drop every piece of per-index state before reloading
  S.mapChain = null; S.mapChainT = 0;
  S.valStrike = null; S.valSide = "AUTO";
  if(idx !== "NIFTY") S.gex = null;             // GEX overlay is a NIFTY-only file
  chainStop(); scanStop(); closeValModal();
  bootData().then(() => {                        // reload data, then resume the DATA poll if open
    if(document.body.classList.contains("dataMode")) chainStart();
  });
};
$("dvGrid").onclick = e => {
  const w = e.target.closest(".wg");
  if(!w) return;
  const id = w.dataset.id;
  S.openWg.has(id) ? S.openWg.delete(id) : S.openWg.add(id);
  w.classList.toggle("open");
};
// click a narrative-log row to scrub to that minute
$("feed").onclick = e => {
  const row = e.target.closest(".ev");
  if(row && row.dataset.t && S.tIdx[row.dataset.t] !== undefined)
    seek(S.tIdx[row.dataset.t]);
};

/* ---------- today-so-far briefing (render-only digest of the payload) ---------- */

const STORY_KINDS = new Set(["ARMED","IGNITION","CLIMAX","TRAP-SPRUNG","SPRING-FAIL",
                             "SQUEEZE-RELEASE","GAMMA-PIN","SQUEEZE-RISK","CARRY",
                             "OI-PEAK-LAG","BAND-REVERSAL","BAND-BREAK"]);

function renderStory(i, bar){
  const el = $("storyBody"); if(!el) return;
  const bars = S.day.bars.slice(0, i + 1);
  const evs = eventsUpTo(i);

  // range so far + where price sits in it
  let hi=-1e18, lo=1e18, hiT="", loT="";
  for(const b of bars){
    if(b.fut.h > hi){ hi = b.fut.h; hiT = b.t; }
    if(b.fut.l < lo){ lo = b.fut.l; loT = b.t; }
  }
  const c = bar.fut.c;
  const pos = (c - lo) / Math.max(hi - lo, 1e-9);
  const posTxt = pos > 0.7 ? "top of range" : pos < 0.3 ? "bottom of range" : "mid-range";

  // opening context vs the pivot map
  const o = bars[0].fut.o, P = S.day.pivots.P;
  const gap = o - P;
  const openLine = `${bars[0].t} open ${o.toFixed(0)} — ${Math.abs(gap).toFixed(0)} pts ` +
                   `${gap >= 0 ? "above" : "below"} pivot P ${P.toFixed(0)}`;

  // major beats (the loud, decided moments — verbatim engine heads)
  const beats = evs.filter(e => STORY_KINDS.has(e.kind));
  const shown = beats.slice(-7);
  const beatHtml = (beats.length > shown.length
      ? `<div class="beat"><span class="t">…</span>${beats.length - shown.length} earlier beats</div>` : "")
    + shown.map(e => {
        const head = splitMsg(e.msg).head;
        return `<div class="beat" title="${e.msg.replace(/"/g,"&quot;")}">` +
               `<span class="t">${e.t}</span>` +
               `<span class="k" style="color:${EVC[e.kind]||"#8090a8"}">${e.kind}</span>` +
               `${head}</div>`;
      }).join("");

  // day character: what has the tape been PUNISHING vs REWARDING so far
  const n = k => evs.filter(e => e.kind === k).length;
  const traps = n("TRAP-SPRUNG"), fails = n("SPRING-FAIL");
  const fires = n("IGNITION") + n("SQUEEZE-RELEASE"), climax = n("CLIMAX");
  let ch;
  if(fires === 0 && traps + fails > 0)
    ch = `${traps} trap${traps===1?"":"s"} sprung, ${fails} spring${fails===1?"":"s"} died, ` +
         `zero ignitions — breakouts are being punished. Expect fades, keep size small, ` +
         `don't chase until something actually detonates.`;
  else if(fires > 0 && traps > fires)
    ch = `traps outnumber ignitions ${traps}:${fires} — follow-through is unreliable today; ` +
         `take profits fast, honour invalidations.`;
  else if(fires > 0)
    ch = `${fires} detonation${fires===1?"":"s"} vs ${traps} trap${traps===1?"":"s"}` +
         `${climax ? `, ${climax} climax` : ""} — moves have carried today; ` +
         `momentum deserves respect, pullbacks are entries.`;
  else
    ch = `quiet tape — no traps sprung, nothing fired. The day hasn't picked a character ` +
         `yet; the first real detonation or failure will set the tone.`;

  $("storyPos").textContent = `${bars.length}m`;
  el.innerHTML =
    `<div class="open">${openLine}</div>` +
    beatHtml +
    `<div class="rng">RANGE ${lo.toFixed(0)} (${loT}) – ${hi.toFixed(0)} (${hiT}) · ` +
    `now ${c.toFixed(0)} · ${posTxt}</div>` +
    `<div class="char">${ch}</div>`;
}

/* ---------- THE READ: episode + box + playbook (engine words, no parsing) ---------- */

function renderRead(i, bar){
  const el = $("readBody"); if(!el) return;
  const c = bar.ctx || {};
  const ep = c.episode || `${S.states[i] || ""} — ${S.whys[i] || ""}`;
  const epCol = ep.startsWith("MOVE RUNNING") ? "#2ec27e"
              : ep.startsWith("MOVE SPENT") || ep.startsWith("TRAP") ? "#ffbf00"
              : ep.startsWith("MOVE STALLING") ? "#ff8c5a"
              : ep.startsWith("FIGHT") ? "#4aa8ff" : "#9fb0c8";
  el.innerHTML =
    `<div class="ep" style="color:${epCol}">${ep}</div>` +
    (c.loc ? `<div class="loc">${c.loc}</div>` : "") +
    ((c.plays && c.plays.length)
      ? `<div class="plays">${c.plays.map(playChip).join("")}</div>`
      : "");
}

const BAND_TIER = { HIGH:"#2ec27e", MED:"#ffbf00", LOW:"#5d6b84" };
function playChip(p){
  const m = p.match(/^\[(HIGH|MED|LOW)\]\s*/);
  if(m){
    const col = BAND_TIER[m[1]];
    return `<span>▸ <b class="tier" style="color:${col};border-color:${col}">`
         + `${m[1]}</b> ${p.slice(m[0].length)}</span>`;
  }
  return `<span>▸ ${p}</span>`;
}

/* ---------- trap radar ---------- */

function renderTrap(i, bar, st){
  const body = $("trapBody");
  const evs = eventsUpTo(i);
  const mm = bar.gamma ? ` · MM ${bar.gamma.regime}` : "";
  const last = (k, w) => {
    const a = evs.filter(e => e.kind===k && minutesAgo(i, e.t) <= w);
    return a[a.length-1];
  };
  const sprung  = last("TRAP-SPRUNG", 35);
  const setting = last("TRAP-SETTING", 25);
  const opening = last("TRAP", 35);
  const div     = last("DIVERGENCE", 20);
  if(sprung){
    const d = sprung.data || {};
    const { head, rest } = splitMsg(sprung.msg);
    body.innerHTML =
      `<div class="card trap"><div class="hl">⚠ ${d.side||""} TRAP SPRUNG</div>` +
      `<div class="zone">${sprung.t} · failed break at ${d.ref_px ?? "—"}${mm}</div>` +
      `<div class="quote">${head}${rest ? " — " + rest : ""}</div>` +
      `<div class="meta"><span>PLAY <b>${d.side==="BULL"
        ? "trapped longs sell rallies — fade bounces"
        : "trapped shorts buy dips — fade flushes"}</b></span></div></div>`;
  } else if(setting){
    const d = setting.data || {}; const votes = d.votes || [];
    const { head, rest } = splitMsg(setting.msg);
    body.innerHTML =
      `<div class="card trap"><div class="hl">⚠ ${d.side||""} TRAP SETTING · ${votes.length} TELLS</div>` +
      `<div class="zone">${setting.t} · near ${d.ref_px ?? bar.fut.c.toFixed(0)}${mm}</div>` +
      `<div class="quote">${head}${rest ? " — " + rest : ""}</div>` +
      `<div class="meta">${votes.map(v => `<span>✓ <b>${v.toUpperCase()}</b></span>`).join("")}</div></div>`;
  } else if(opening){
    const { head, rest } = splitMsg(opening.msg);
    body.innerHTML =
      `<div class="card trap"><div class="hl">⚠ OPENING TRAP — TWO-SIDED</div>` +
      `<div class="zone">${opening.t} · near FUT ${bar.fut.c.toFixed(0)} · FADE EXTREMES${mm}</div>` +
      `<div class="quote">${head}${rest ? " — " + rest : ""}</div></div>`;
  } else if(div){
    const d = div.data || {};
    const { head, rest } = splitMsg(div.msg);
    body.innerHTML =
      `<div class="card calm"><div class="hl">WATCH — ${d.side||""} TRAP TELL (1 of 2 needed)</div>` +
      `<div class="zone">${div.t} · ${d.side==="BULL" ? "highs" : "lows"} not being paid for · one more tell arms the radar${mm}</div>` +
      `<div class="quote">${head}${rest ? " — " + rest : ""}</div></div>`;
  } else if(st === "BALANCE" || st === "OPENING"){
    body.innerHTML =
      `<div class="card calm"><div class="hl">BALANCE — NO TRAP DETECTED</div>` +
      `<div class="zone">two-sided tape around VWAP · scalp edges only, no chasing</div></div>`;
  } else {
    body.innerHTML =
      `<div class="card calm"><div class="hl">NO ACTIVE TRAP SIGNAL</div>` +
      `<div class="zone">state ${st} · watching book confirmation at each new extreme</div></div>`;
  }
}

/* ---------- momentum windows ---------- */

function renderMomentum(i, bar, st){
  const body = $("moBody");
  const su = bar.setup;
  const alive = su && (su.status==="LOADING" || su.status==="ARMED" || su.status==="FIRED");
  if(alive){
    const bull = su.dir==="UP";
    const fired = su.status==="FIRED";
    const src = eventsUpTo(i).filter(e =>
      e.t===su.t0 && (e.kind==="SPRING" || e.kind==="ARMED")).pop();
    const cls = fired ? "fired" : "mo";
    const title = fired ? `◆ MOMENTUM FIRED ${su.fired||""} — SPRING RELEASED`
                : su.status==="ARMED" ? "◆ MOMENTUM ARMED — SPRING AT LEVEL"
                : "◆ MOMENTUM LOADING";
    body.innerHTML =
      `<div class="card ${cls}"><div class="hl">${title}</div>` +
      `<div class="zone">${su.t0} · ${bull?"UPSIDE":"DOWNSIDE"} bias · ${su.level_name} ${su.level_px}</div>` +
      (src ? `<div class="quote">${src.msg}</div>` : "") +
      `<div class="meta"><span>COMPRESSION <b>${Math.round(su.comp*100)}%</b></span>` +
      `<span>SPRING INTENSITY <b>${Math.round(su.intensity*100)}%</b></span>` +
      `<span>CONFIRMS <b>hold ${bull?"above":"below"} ${su.ref}</b></span>` +
      `<span>INVALIDATES <b>close ${bull?"below":"above"} ${su.ref}</b></span></div>` +
      `<div class="ebar"><i style="width:${Math.round(su.comp*100)}%"></i></div></div>`;
  } else if(su && su.status==="INVALIDATED" && su.died && minutesAgo(i, su.died) <= 15){
    body.innerHTML =
      `<div class="card calm"><div class="hl">✕ SETUP INVALIDATED ${su.died}</div>` +
      `<div class="zone">${su.dir==="UP"?"bullish":"bearish"} spring ${su.t0} died — ` +
      `FUT closed ${su.dir==="UP"?"below":"above"} ${su.ref} · stand down, wait for the next coil</div></div>`;
  } else if(st === "COILING"){
    body.innerHTML =
      `<div class="card mo"><div class="hl">◆ ENERGY STORING</div>` +
      `<div class="zone">bands compressing (bandwidth rank ${bar.fut.bw_r.toFixed(2)}) · volume quiet · watch for the spring</div></div>`;
  } else if(st === "TREND-UP" || st === "TREND-DOWN"){
    body.innerHTML =
      `<div class="card ${st==="TREND-UP"?"fired":"trap"}"><div class="hl">◆ MOMENTUM LIVE — ${st}</div>` +
      `<div class="zone">${S.whys[S.i]} · pullbacks to VWAP/flipped levels are entries, not exits</div></div>`;
  } else {
    body.innerHTML =
      `<div class="card calm"><div class="hl">NO WINDOW OPEN</div>` +
      `<div class="zone">no spring armed in the last 50m · wait for compression or a level test</div></div>`;
  }
}

/* ---------- level ladder ---------- */

function renderLadder(i, bar){
  const notes = {};
  for(const e of eventsUpTo(i)){
    if(e.kind === "BREAK"){
      const m = e.msg.match(/closes (above|below) (\w+) /);
      if(m) notes[m[2]] = `broken ${m[1]==="above"?"↑":"↓"} ${e.t}`;
    }
    if(e.kind === "FLIP-TEST"){
      const m = e.msg.match(/^(\w+) .*from (above|below)/);
      if(m) notes[m[1]] = `flipped · now ${m[2]==="above"?"SUPPORT":"RESISTANCE"} (${e.t})`;
    }
  }
  const piv = S.day.pivots;
  const rows = [["R3",piv.R3],["R2",piv.R2],["R1",piv.R1],["STK",S.day.strike],
                ["P",piv.P],["S1",piv.S1],["S2",piv.S2]];
  if(S.gex && S.day.day === "Jul 17"){   // GEX file covers 2026-07-17 only
    const gi = S.gexIdx[bar.t];
    if(gi !== undefined){
      if(S.gex.wall_up[gi] != null) rows.push(["WALL", S.gex.wall_up[gi]]);
      if(S.gex.wall_dn[gi] != null) rows.push(["WALL", S.gex.wall_dn[gi]]);
      if(S.gex.flip[gi] != null)    rows.push(["FLIP", S.gex.flip[gi]]);
    }
  }
  rows.sort((a,b)=>b[1]-a[1]);
  const px = bar.fut.c;
  let html = "", placed = false;
  const liveRow = () => {
    const near = rows.reduce((best,r)=>Math.abs(r[1]-px)<Math.abs(best[1]-px)?r:best, rows[0]);
    return `<div class="lrow live"><div class="r1"><span class="nm">LIVE</span>` +
      `<span class="px">${px.toFixed(2)}</span></div>` +
      `<div class="note">${px>near[1]?"above":"below"} ${near[0]} ${near[1].toFixed(0)} · z ${bar.fut.z>=0?"+":""}${bar.fut.z.toFixed(1)}σ</div></div>`;
  };
  for(const [nm,p] of rows){
    if(!placed && px > p){ html += liveRow(); placed = true; }
    const gx = nm==="WALL" || nm==="FLIP";           // gamma-layer rungs: cyan
    const note = nm==="STK" ? "defended strike"
               : nm==="WALL" ? "dealer gamma wall (GEX)"
               : nm==="FLIP" ? "gamma flip — dealer sign change"
               : (notes[nm] || "—");
    html += `<div class="lrow ${nm==="STK"?"stk":""}"><div class="r1">` +
      `<span class="nm"${gx?' style="color:#3fc1c9"':''}>${nm}</span>` +
      `<span class="px">${p.toFixed(2)}</span></div>` +
      `<div class="note">${note}</div></div>`;
  }
  if(!placed) html += liveRow();
  $("ladder").innerHTML = html;
}

/* ---------- expiry master-regime ---------- */

function renderExpiry(c){
  const el = $("expiryBar"); if(!el) return;
  // only on expiry day / 0DTE (real days-to-expiry from the engine)
  if(!c || c.t_exp == null || c.t_exp > 1.0 || !c.pin){ el.innerHTML = ""; return; }
  const dte = c.t_exp <= 0.5 ? "0DTE" : "EXPIRY";
  const k = c.pin.k, d = c.pin.dist;
  const ivv = c.iv_pe || c.iv_ce;
  const iv = ivv ? (ivv*100).toFixed(1) + "%" : "—";
  const ivrs = [c.ivr_ce, c.ivr_pe].filter(x => x != null);
  const ivr = ivrs.length ? Math.round(ivrs.reduce((a,b)=>a+b,0)/ivrs.length*100) : null;
  const crush = ivr != null && ivr <= 25 ? " crushed" : "";
  const side = d > 0 ? "above" : "below";
  el.innerHTML =
    `<span class="xb">◉ ${dte}</span>` +
    `<span class="xp">PIN ${k} · px ${d>=0?"+":""}${d}</span>` +
    `<span class="xi">ATM IV ${iv}${ivr!=null?" · p"+ivr:""}${crush}</span>` +
    `<span class="xr">SELL PREMIUM · fade extremes to pin · price ${Math.abs(d)} ${side} ` +
    `magnet · trend labels unreliable — theta rules</span>`;
}

/* ---------- volatility strip ---------- */

function renderVol(c, g){
  const set = (id, txt, col) => { const e = $(id); if(!e) return;
    e.textContent = txt; if(col) e.style.color = col; };
  if(!c){ ["volZ","volRng","volBw","volIn","volIV"].forEach(id=>set(id,"—","#cdd9ec"));
          set("volReg","",""); return; }

  // realized: how stretched from VWAP (|z|), colored by extremity
  const z = c.z ?? 0, az = Math.abs(z);
  set("volZ", `${z>=0?"+":""}${z.toFixed(1)}σ`,
      az>=3 ? "#ff5f6b" : az>=2 ? "#ffbf00" : "#cdd9ec");

  // 30m realized range + its percentile-so-far
  const rp = Math.round((c.rng_r ?? 0)*100);
  const rtag = rp<=15 ? " COIL" : rp>=80 ? " WIDE" : "";
  set("volRng", `${(c.rng30??0).toFixed(0)} pts · p${rp}${rtag}`,
      rp<=15 ? "#7aa2c8" : rp>=80 ? "#ff8c5a" : "#cdd9ec");

  // band width percentile (compression / expansion of the σ envelope)
  const bp = Math.round((c.bw_r ?? 0)*100);
  set("volBw", `p${bp} ${bp<45?"compress":bp>65?"expand":"neutral"}`,
      bp<45 ? "#7aa2c8" : bp>65 ? "#ff8c5a" : "#cdd9ec");

  set("volIn", `${Math.round((c.inside1 ?? 0)*100)}%`, "#cdd9ec");

  // implied: ATM IV (CE/PE) + IV rank of the day, forward-held from 5m solve
  if(c.iv_ce || c.iv_pe){
    const ce = c.iv_ce ? (c.iv_ce*100).toFixed(1) : "–";
    const pe = c.iv_pe ? (c.iv_pe*100).toFixed(1) : "–";
    const ivrs = [c.ivr_ce, c.ivr_pe].filter(x=>x!=null);
    const ivr = ivrs.length ? "p"+Math.round(ivrs.reduce((a,b)=>a+b,0)/ivrs.length*100) : "—";
    set("volIV", `${ce}/${pe}% · IVr ${ivr}`, "#cdd9ec");
  } else set("volIV", "—", "#5d6b84");

  // combined regime read: coil vs expansion, tinted by gamma damp/amplify
  const coil = rp<=20 && bp<45, wide = rp>=75 || bp>70;
  const amp = g && /AMPLIF/.test(g.regime), damp = g && /PIN|CEIL|FLOOR/.test(g.regime);
  let txt, col;
  if(coil){ txt = amp ? "COILED · break amplifies" : "COILED · expansion pending"; col = "#ffbf00"; }
  else if(wide){ txt = damp ? "EXPANDED · dealers dampen" : "EXPANDED · move live"; col = "#ff8c5a"; }
  else { txt = damp ? "NORMAL · mean-reverting" : amp ? "NORMAL · trend-prone" : "NORMAL"; col = "#7aa2c8"; }
  set("volReg", txt, col);
}

/* ---------- feed + carry ---------- */

function renderFeed(i){
  const feed = $("feed");
  let added = false;
  while(S.feedPtr < S.day.events.length &&
        (S.tIdx[S.day.events[S.feedPtr].t] ?? 1e9) <= i){
    const ev = S.day.events[S.feedPtr++];
    if(ev.kind === "STATE"){ continue; }
    const div = document.createElement("div");
    div.className = "ev" + (LOUD.has(ev.kind) ? " loud" : "");
    div.style.borderLeftColor = EVC[ev.kind] || "#5d6b84";
    div.dataset.t = ev.t;                       // click-to-seek target
    if(ev.data?.times?.length > 1)              // ×N collapsed events: list them
      div.title = "repeats: " + ev.data.times.join(", ");
    div.innerHTML = `<span class="t">${ev.t}</span>` +
      `<span class="k" style="color:${EVC[ev.kind]||"#dbe6f5"}">${ev.kind}</span>` +
      `<span class="m">${ev.msg}</span>`;
    feed.appendChild(div);
    added = true;
  }
  if(added) feed.scrollTop = feed.scrollHeight;
}

function renderCarry(i){
  const carryEv = S.day.events.find(e => e.kind === "CARRY");
  if(carryEv && S.tIdx[carryEv.t] !== undefined && S.tIdx[carryEv.t] <= i){
    const m = carryEv.msg.match(/→ (.+)$/);
    $("carry").innerHTML = carryEv.msg.replace(/→ .+$/,"") +
      (m ? `→ <b>${m[1]}</b>` : "");
  } else {
    $("carry").textContent = "";
  }
}

/* ---------- price ribbon (TAPE view): FUT close + VWAP + ±2σ + event dots ---------- */

function renderRibbon(i){
  const rib = $("ribbon");
  if(!rib || !S.day) return;
  const bars = S.day.bars, W = bars.length, H = 64;
  const sig = S.day.day + ":" + W;
  if(S._ribbonSig !== sig){                    // (re)build the static SVG once per day
    S._ribbonSig = sig;
    let lo = Infinity, hi = -Infinity;
    for(const b of bars){ if(b.fut.l < lo) lo = b.fut.l; if(b.fut.h > hi) hi = b.fut.h; }
    const pad = (hi - lo) * 0.02 || 1; lo -= pad; hi += pad;
    const y = v => (H - (v - lo) / (hi - lo) * H).toFixed(1);
    const cls = [], vwap = [], up = [], dn = [];
    bars.forEach((b,x) => {
      cls.push(x + "," + y(b.fut.c)); vwap.push(x + "," + y(b.fut.vwap));
      up.push(x + "," + y(b.fut.u2)); dn.push(x + "," + y(b.fut.d2));
    });
    const env = up.concat(dn.reverse()).join(" ");
    const dots = S.day.events
      .filter(e => LOUD.has(e.kind) && S.tIdx[e.t] !== undefined)
      .map(e => { const x = S.tIdx[e.t];
        return `<circle cx="${x}" cy="${y(bars[x].fut.c)}" r="2.5" ` +
               `fill="${EVC[e.kind]||"#8090a8"}"><title>${e.t} ${e.kind}</title></circle>`; })
      .join("");
    rib.innerHTML =
      `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">` +
      `<polygon points="${env}" fill="#1a2336"></polygon>` +
      `<polyline points="${vwap.join(" ")}" fill="none" stroke="var(--slate)" ` +
        `stroke-width="1" vector-effect="non-scaling-stroke"></polyline>` +
      `<polyline points="${cls.join(" ")}" fill="none" stroke="var(--ink)" ` +
        `stroke-width="1" vector-effect="non-scaling-stroke"></polyline>` +
      dots +
      `<rect id="ribMask" x="${i+1}" y="0" width="${Math.max(0,W-i-1)}" height="${H}" ` +
        `fill="rgba(10,13,20,.7)"></rect>` +
      `<line id="ribCursor" x1="${i}" y1="0" x2="${i}" y2="${H}" stroke="var(--amber)" ` +
        `stroke-width="1" vector-effect="non-scaling-stroke"></line>` +
      `</svg>`;
  } else {                                     // cheap per-frame: move cursor + mask
    const mask = $("ribMask"), cur = $("ribCursor");
    if(mask){ mask.setAttribute("x", i+1); mask.setAttribute("width", Math.max(0, W-i-1)); }
    if(cur){ cur.setAttribute("x1", i); cur.setAttribute("x2", i); }
  }
}

(function(){                                   // drag anywhere on the ribbon to scrub
  const rib = $("ribbon");
  if(!rib) return;
  let dragging = false;
  const toSeek = e => {
    if(!S.day) return;
    const W = S.day.bars.length, rect = rib.getBoundingClientRect();
    const x = Math.round((e.clientX - rect.left) / rect.width * (W - 1));
    seek(Math.max(0, Math.min(W - 1, x)));
  };
  rib.addEventListener("mousedown", e => { dragging = true; toSeek(e); });
  window.addEventListener("mousemove", e => { if(dragging) toSeek(e); });
  window.addEventListener("mouseup", () => { dragging = false; });
})();

/* ---------- DATA view: option chain analyser (/api/chain, 5s poll) ---------- */

S.ch = { timer:null, el:{}, sig:"", dead:false, sub:"chain" };
S.scan = { timer:null };

$("chsChain").onclick = () => setChainSub("chain");
$("chsWidgets").onclick = () => setChainSub("widgets");
$("chsScan").onclick = () => setChainSub("scan");

function setChainSub(sub){
  S.ch.sub = sub;
  lsSet("chsub", sub);
  $("chsChain").classList.toggle("active", sub==="chain");
  $("chsWidgets").classList.toggle("active", sub==="widgets");
  $("chsScan").classList.toggle("active", sub==="scan");
  chainStart();
}
function chainStart(){                         // apply the selected DATA sub-view
  const dv = $("dataView");
  if(S.ch.sub === "scan"){                      // trade scanner (own 5s poll)
    chainStop();
    dv.classList.remove("chain","legacy"); dv.classList.add("scan");
    scanStart();
    return;
  }
  scanStop();
  if(S.ch.sub === "widgets"){
    chainStop();                               // widgets are scrub-driven, no poll
    dv.classList.remove("chain","scan"); dv.classList.add("legacy");
    $("lgNote").textContent = "";
    if(S.day) renderData(S.i, S.day.bars[S.i]);
    return;
  }
  if(S.ch.dead){ legacyChain(); return; }      // chain endpoint absent -> fallback
  dv.classList.add("chain");
  dv.classList.remove("legacy","scan");
  fetchChain();
  if(!S.ch.timer) S.ch.timer = setInterval(fetchChain, 5000);
}
function chainStop(){
  clearInterval(S.ch.timer); S.ch.timer = null;
}

/* ---------- SCAN: rank the method-aligned option buys, top 3 ---------- */
function scanStart(){
  scanRefresh();
  if(!S.scan.timer) S.scan.timer = setInterval(scanRefresh, 5000);
}
function scanStop(){
  clearInterval(S.scan.timer); S.scan.timer = null;
}
async function scanRefresh(){
  try{
    const d = await (await fetch(IDXQ("/api/chain"), {cache:"no-store"})).json();
    if(d && d.strikes){ S.mapChain = d; S.mapChainT = Date.now(); }
  }catch(e){ /* keep last snapshot */ }
  renderScan();
}
function renderScan(){
  const head = $("scanHead"), list = $("scanList");
  if(!head || !list) return;
  if(!S.day){ head.innerHTML = `<div class="skwait">load a session first</div>`; list.innerHTML = ""; return; }
  const bar = S.day.bars[S.i];
  const met = (S.mapChain && S.mapChain.metrics) || {};
  const strikes = (S.mapChain && S.mapChain.strikes) || null;
  const px = v => v==null ? "—" : v.toFixed(0);
  const bandCol = b => b==="STRONG" ? "var(--up)" : b==="MODERATE" ? "#e8c15a"
                     : b==="WEAK" ? "#e0975a" : "#8fa0bb";

  const base = computeValidator(S.i, bar, {strike:null, side:"AUTO"});
  const dir = base.autoDir;
  const dCol = dir==="LONG" ? "var(--up)" : dir==="SHORT" ? "var(--dn)" : "#8fa0bb";
  const dWord = dir==="LONG" ? "BULLISH" : dir==="SHORT" ? "BEARISH" : "STAND ASIDE";
  const guide = dir==="LONG" ? "favour buying CALLS"
              : dir==="SHORT" ? "favour buying PUTS"
              : "no directional edge — nothing clean to buy";
  const chips = [];
  if(met.pcr_oi!=null) chips.push(`PCR ${met.pcr_oi}`);
  if(met.squeeze && met.squeeze.side) chips.push(`squeeze ${met.squeeze.side}`);
  if(met.max_pain!=null) chips.push(`max pain ${met.max_pain}`);
  head.innerHTML =
    `<div class="skRead"><span class="skLbl" style="color:${dCol}">METHOD READ</span>` +
    `<b style="color:${dCol}">${dWord}</b>` +
    `<span class="skConf"><b style="color:${bandCol(base.band)}">${base.conf}</b>/100 · ${base.band}</span></div>` +
    `<div class="skGuide">${guide}.${chips.length?` <em>${chips.join(" · ")}</em>`:""} ` +
    `<u>tap a trade for the full read</u></div>`;

  if(!strikes){ list.innerHTML = `<div class="skwait">waiting for the live chain…</div>`; return; }

  // aligned buy side (call if bullish, put if bearish); scan both when no edge
  const sides = dir==="LONG" ? [["ce","LONG"]] : dir==="SHORT" ? [["pe","SHORT"]]
              : [["ce","LONG"], ["pe","SHORT"]];
  const atm = (S.mapChain && S.mapChain.atm) || bar.fut.c;
  const cands = [];
  for(const s of strikes)
    for(const [, side] of sides){
      const r = computeValidator(S.i, bar, {strike:s.k, side});
      if(r.strikeInfo && !r.strikeInfo.noChain) cands.push({k:s.k, side, r});
    }
  // rank by confidence BUCKET (5-pt bands) then nearest-the-money, so comparable strikes
  // prefer the tradeable ATM one instead of deep ITM edging ahead on delta alone
  const bkt = x => Math.round(x.r.conf / 5);
  cands.sort((a,b) => (bkt(b) - bkt(a)) || (Math.abs(a.k-atm) - Math.abs(b.k-atm)));
  const top = cands.slice(0, 3);
  if(!top.length){ list.innerHTML = `<div class="skwait">no strikes to rank yet</div>`; return; }

  list.innerHTML = top.map((c, ix) => {
    const r = c.r, si = r.strikeInfo, isCall = si.opt === "CE";
    const tgs = (r.targets || []).map((t, j) => `T${j+1} ${px(t.px)}`).join(" · ");
    const rrTxt = r.rr==null ? "—" : r.rr.toFixed(2);
    const fitCol = si.fitLbl==="GOOD" ? "var(--up)" : si.fitLbl==="OK" ? "#e8c15a" : "var(--dn)";
    return `<div class="scanRow" data-k="${c.k}" data-side="${c.side}">` +
      `<div class="skRank">${ix+1}</div>` +
      `<div class="skMain">` +
        `<div class="skTop"><b class="skBuy">BUY ${c.k} ${isCall?"CE":"PE"}</b>` +
          `<span class="skBand" style="color:${bandCol(r.band)}">${r.conf} · ${r.band}</span></div>` +
        `<div class="skMeta">prem ₹${si.prem!=null?si.prem.toFixed(1):"—"} · Δ${si.delta!=null?si.delta.toFixed(2):"—"} · ` +
          `<span style="color:${fitCol}">fit ${si.fitLbl}</span> · ${si.moneyness}</div>` +
        `<div class="skLevels">ENTRY ${px(r.entry)} · ${tgs||"—"} · STOP ${px(r.stop)} · R:R ${rrTxt}</div>` +
      `</div><div class="skGo">▸</div></div>`;
  }).join("");
}
$("scanList").onclick = e => {
  const row = e.target.closest(".scanRow"); if(!row) return;
  S.valStrike = +row.dataset.k; S.valSide = row.dataset.side;
  openValModal();
};
function legacyChain(msg){
  const dv = $("dataView");
  dv.classList.remove("chain"); dv.classList.add("legacy");
  $("lgNote").textContent = msg ||
    "chain analyser offline — start the server in live mode (or --mock-chain). Showing legacy widgets.";
  if(S.day) renderData(S.i, S.day.bars[S.i]);
}
async function fetchChain(){
  let r;
  try{ r = await fetch(IDXQ("/api/chain")); }
  catch(e){ return; }                       // transient: keep last view
  if(r.status === 404){                     // no poller on this server: final
    S.ch.dead = true; chainStop(); legacyChain(); return;
  }
  let j; try{ j = await r.json(); }catch(e){ return; }
  if(S.ch.sub !== "chain") return;             // user switched to widgets mid-flight
  const dv = $("dataView");
  dv.classList.add("chain"); dv.classList.remove("legacy");
  if(!j.ok){
    $("chTop").innerHTML = `<div class="cell" style="grid-column:1/-1">` +
      `<label>CHAIN</label><b>WAITING</b><span>${j.error||""}</span></div>`;
    if(j.error) showBanner("chain: " + j.error);   // surfaces token-expired etc.
    return;                                 // recoverable: token/warmup — keep polling
  }
  hideBanner();
  renderChain(j);
}

const fmtOI = x => x==null ? "—" : Math.abs(x)>=1e6 ? (x/1e6).toFixed(1)+"M"
             : Math.abs(x)>=1e3 ? Math.round(x/1e3)+"k" : ""+Math.round(x);
const fmtSgn = x => (x>=0?"+":"") + fmtOI(x);
const wTint = w => w==null ? "#5d6b84" : w>=0.25 ? "#3fc1c9" : w<=-0.25 ? "#ff5f6b" : "#5d6b84";
const CH_ROWH = 22;                          // .crow 21px + 1px border
const CH_WIN = 5;                            // ladder shows ATM ± this many strikes
                                             // (metrics stay full-chain server-side)

function renderChain(j){
  const m = j.metrics, ks = j.strikes.slice().sort((a,b)=>b.k-a.k);
  renderChainTop(j, m);
  renderChainOI(j);
  renderChainLadder(j, m, ks);
  renderChainPain(j, m);
  renderChainSpark(j);
}

/* total CE vs PE OI strength, sampled every 5 min from the open */
function renderChainOI(j){
  const box = $("chOI"); if(!box) return;
  const se = (j.series || []).filter(p => p.ce_oi != null && p.pe_oi != null);
  if(!se.length){
    box.innerHTML = `<div class="oiNote">OI-strength history needs the upgraded chain ` +
      `poller — restart the live server (it now warm-starts from today's saved snapshots, ` +
      `so a restart keeps the day).</div>`;
    return;
  }
  const bk = new Map();                              // last sample per 5-min bucket
  for(const p of se) bk.set(Math.floor(p.sec/300), p);
  const rows = [...bk.values()].sort((a,b)=>a.sec-b.sec);
  const M = v => (v/1e6).toFixed(2);
  const dM = d => (d>=0?"+":"") + (d/1e6).toFixed(2);
  let prev=null, prevDom=null, body="";
  for(const r of rows){
    const tot = r.ce_oi + r.pe_oi, putShare = tot ? r.pe_oi/tot : 0.5;
    const pcr = r.pe_oi/Math.max(r.ce_oi,1);
    const cross = putShare>=0.583 || putShare<=0.417;   // one side 40%+ heavier
    const dom = putShare>=0.583 ? "PUT" : putShare<=0.417 ? "CALL" : "BAL";
    const domCol = dom==="PUT" ? "#2ec27e" : dom==="CALL" ? "#ff5f6b" : "#8fa0bb";
    const verdict = dom==="PUT" ? `puts +${((pcr-1)*100).toFixed(0)}% heavier — support / bullish`
                  : dom==="CALL" ? `calls +${((1/pcr-1)*100).toFixed(0)}% heavier — resistance / bearish`
                  : "balanced — no side dominates";
    const flip = prevDom && dom!=="BAL" && dom!==prevDom;
    const ivR = (r.iv_ce!=null && r.iv_pe!=null)
      ? (r.iv_pe > r.iv_ce*1.05 ? "put fear" : r.iv_ce > r.iv_pe*1.05 ? "call chase" : "even")
      : "";
    const gR = r.greg==="POSITIVE" ? "pin (dampen)" : r.greg==="NEGATIVE" ? "trend (amplify)" : "—";
    const dCe = prev ? dM(r.ce_oi-prev.ce_oi) : "—", dPe = prev ? dM(r.pe_oi-prev.pe_oi) : "—";
    const iv = x => x==null ? "—" : (x*100).toFixed(1);
    body += `<tr class="${cross?"cross":""}${flip?" flip":""}">` +
      `<td>${r.ts.slice(0,5)}</td>` +
      `<td class="num">${M(r.ce_oi)}</td><td class="num d ${dCe[0]==="+"?"up":"dn"}">${dCe}</td>` +
      `<td class="num">${M(r.pe_oi)}</td><td class="num d ${dPe[0]==="+"?"up":"dn"}">${dPe}</td>` +
      `<td class="pcell"><div class="pbar"><span class="mid"></span>` +
      `<i style="width:${(putShare*100).toFixed(0)}%"></i></div></td>` +
      `<td style="color:${domCol}">${flip?"⇄ ":""}${verdict}</td>` +
      `<td class="num">${iv(r.iv_ce)}/${iv(r.iv_pe)}${ivR?" "+ivR:""}</td>` +
      `<td>${gR}</td></tr>`;
    prev = r; if(dom!=="BAL") prevDom = dom;
  }
  const last = rows[rows.length-1];
  box.innerHTML =
    `<div class="oiHd">OI STRENGTH — total CE vs PE, every 5 min` +
    `<span>green bar = put-heavy (support) · row glows amber when one side is 40%+ heavier · ⇄ dominance flip</span>` +
    `<em>now: CE ${M(last.ce_oi)}M · PE ${M(last.pe_oi)}M</em></div>` +
    `<div class="oiScroll"><table class="oiT"><thead><tr>` +
    `<th>TIME</th><th>CE OI</th><th>Δ5m</th><th>PE OI</th><th>Δ5m</th><th>PUT◄►CALL</th>` +
    `<th>VERDICT</th><th>IV ce/pe</th><th>γ</th></tr></thead><tbody>${body}</tbody></table></div>`;
  const sc = box.querySelector(".oiScroll"); if(sc) sc.scrollTop = sc.scrollHeight;
}

function renderChainTop(j, m){
  const iv = m.iv || {};
  const pct = v => v==null ? "—" : (v*100).toFixed(1);
  const sq = m.squeeze || {score:0};
  const sqCol = sq.score>=0.5 ? "#ff5f6b" : sq.score>=0.2 ? "#ffbf00" : "#5d6b84";
  const gxCol = m.gex_regime==="POSITIVE" ? "#2ec27e"
              : m.gex_regime==="NEGATIVE" ? "#ff5f6b" : "#5d6b84";
  const d = (px) => px==null ? "—" :
    `${px>=j.spot?"+":""}${(px-j.spot).toFixed(0)} pts`;
  const cell = (l, b, s, col) =>
    `<div class="cell"><label>${l}</label><b style="color:${col||"#dbe6f5"}">${b}</b><span>${s}</span></div>`;
  $("chTop").innerHTML =
    cell("SPOT", j.spot.toFixed(1),
         `${j.ts} · ${j.mode==="mock"?"MOCK":"LIVE"} · exp ${j.expiry||"—"}`) +
    cell("PUT/CALL OI", m.pcr_oi ?? "—",
         m.pcr_oi==null ? "" : m.pcr_oi>1.1 ? "more puts open — support building below"
         : m.pcr_oi<0.9 ? "more calls open — resistance building above" : "puts & calls balanced",
         m.pcr_oi>1.1 ? "#2ec27e" : m.pcr_oi<0.9 ? "#ff5f6b" : "#dbe6f5") +
    cell("MAX PAIN", m.max_pain ?? "—",
         m.max_pain==null ? "" : `price sellers want at expiry · ${d(m.max_pain)}`, "#ffbf00") +
    cell("DEALER GAMMA",
         m.gex_regime==="POSITIVE" ? "▲ CUSHIONED" : m.gex_regime==="NEGATIVE" ? "▼ AMPLIFIED" : "—",
         m.gex_regime==="POSITIVE" ? "dealers sell rallies & buy dips — price sticks, FADE the extremes"
         : m.gex_regime==="NEGATIVE" ? "dealers chase the move — swings accelerate, GO WITH trend not against" : "",
         gxCol) +
    cell("FLIP LEVEL", m.flip_px==null ? "—" : m.flip_px.toFixed(0),
         m.flip_px==null ? "" :
         `cushion turns to chase if price falls to ${m.flip_px.toFixed(0)} · ${Math.abs(m.flip_px-j.spot).toFixed(0)} pts ${m.flip_px<j.spot?"below":"above"}`,
         "#3fc1c9") +
    cell("ATM IV", `${pct(iv.atm_ce)} / ${pct(iv.atm_pe)}`,
         iv.skew==null ? "call / put implied vol" :
         iv.skew>0.005 ? "puts costlier — market paying up for downside protection"
         : iv.skew<-0.005 ? "calls costlier — market chasing upside" : "call & put vol balanced") +
    cell("SQUEEZE", `${Math.round(sq.score*100)}%` + (sq.side?` ${sq.side==="UP"?"▲":"▼"}`:""),
         sq.side ? `trapped ${sq.side==="UP"?"call":"put"} writers may fuel a ${sq.side==="UP"?"pop UP":"drop DOWN"}`
                 : "no trapped writers — no squeeze fuel", sqCol);
}

function renderChainLadder(j, m, ks){
  const lad = $("chLadder");
  const ai = ks.findIndex(s => s.k === j.atm);
  if(ai >= 0) ks = ks.slice(Math.max(0, ai - CH_WIN), ai + CH_WIN + 1);
  const sig = ks.map(s=>s.k).join(",");
  if(sig !== S.ch.sig){                     // strike set changed: rebuild rows
    S.ch.sig = sig; S.ch.el = {};
    $("chHead").innerHTML =
      `<span>CE OI</span><span>ΔOI</span><span>IV</span><span>LTP</span>` +
      `<span class="c-k">STRIKE</span><span>LTP</span><span>IV</span>` +
      `<span>ΔOI</span><span>PE OI</span><span>DEALER GEX</span>`;
    lad.innerHTML = "";
    for(const s of ks){
      const row = document.createElement("div");
      row.className = "crow"; row.dataset.k = s.k;
      row.innerHTML =
        `<span class="obar ce"><i></i><em></em></span><span class="doi"></span>` +
        `<span class="iv"></span><span class="px"></span>` +
        `<span class="k"><b>${s.k}</b><span class="kch mp" style="display:none">MP</span>` +
        `<span class="kch wall" style="display:none">WALL</span></span>` +
        `<span class="px"></span><span class="iv"></span><span class="doi"></span>` +
        `<span class="obar pe"><i></i><em></em></span>` +
        `<span class="gx"><span class="mid"></span><i></i></span>`;
      lad.appendChild(row);
      S.ch.el[s.k] = row;
    }
    for(const cls of ["spot","flip"]){
      const ln = document.createElement("div");
      ln.className = "pxline " + cls;
      ln.innerHTML = `<label></label>`;
      ln.dataset.role = cls;
      lad.appendChild(ln);
    }
  }
  const maxOI = Math.max(1, ...ks.map(s=>Math.max(s.ce.oi, s.pe.oi)));
  const maxGx = Math.max(1e-9, ...ks.map(s=>Math.abs(s.gex||0)));
  for(const s of ks){
    const row = S.ch.el[s.k]; if(!row) continue;
    const el = row.children;
    for(const [side, barEl, doiEl, ivEl, pxEl] of
        [["ce", el[0], el[1], el[2], el[3]], ["pe", el[8], el[7], el[6], el[5]]]){
      const b = s[side], w = s[side+"_w"];
      const bar = barEl.children[0];
      bar.style.width = (b.oi/maxOI*100).toFixed(1) + "%";
      bar.style.background = wTint(w);
      barEl.children[1].textContent = fmtOI(b.oi);
      doiEl.textContent = fmtSgn(b.oi_chg);
      doiEl.className = "doi " + (b.oi_chg>0 ? "up" : b.oi_chg<0 ? "dn" : "");
      ivEl.textContent = b.iv==null ? "—" : (b.iv*100).toFixed(1);
      pxEl.textContent = b.ltp.toFixed(1);
    }
    const kEl = el[4];
    kEl.children[1].style.display = s.k===m.max_pain ? "" : "none";
    kEl.children[2].style.display =
      (s.k===m.wall_up || s.k===m.wall_dn) ? "" : "none";
    row.classList.toggle("atm", s.k===j.atm);
    const gx = el[9].children[1], gv = (s.gex||0)/maxGx;
    gx.style.background = gv>=0 ? "#2ec27e" : "#ff5f6b";
    if(gv>=0){ gx.style.left = "50%"; gx.style.right = ""; }
    else{ gx.style.right = "50%"; gx.style.left = ""; }
    gx.style.width = (Math.abs(gv)*50).toFixed(1) + "%";
  }
  for(const ln of lad.querySelectorAll(".pxline")){
    const px = ln.dataset.role==="spot" ? j.spot : m.flip_px;
    if(px==null || px>ks[0].k || px<ks[ks.length-1].k){ ln.style.display="none"; continue; }
    let y = CH_ROWH/2;
    for(let i=0;i<ks.length-1;i++){
      if(ks[i].k >= px && px >= ks[i+1].k){
        const f = (ks[i].k - px)/Math.max(ks[i].k - ks[i+1].k, 1e-9);
        y = (i + 0.5 + f) * CH_ROWH; break;
      }
    }
    ln.style.display = ""; ln.style.top = y.toFixed(0) + "px";
    ln.children[0].textContent = ln.dataset.role==="spot"
      ? "SPOT " + px.toFixed(1) : "FLIP " + px.toFixed(0);
  }
}

function renderChainPain(j, m){
  const sq = m.squeeze || {score:0, rows:[]};
  const col = sq.score>=0.5 ? "#ff5f6b" : sq.score>=0.2 ? "#ffbf00" : "#5d6b84";
  let html = "";
  if(j.error) html += `<div class="verdict" style="color:#ffbf00">${j.error}</div>`;
  html += `<div class="sqbar"><i style="width:${Math.round(sq.score*100)}%;background:${col}"></i></div>`;
  if(sq.side){
    html += `<div class="verdict"><b style="color:${col}">${sq.side==="UP"?"▲":"▼"} ` +
      `SQUEEZE ${Math.round(sq.score*100)}%</b> — ${sq.verdict}</div>`;
    for(const r of sq.rows||[]){
      html += `<div class="prow"><b>${r.k} ${r.side}</b>` +
        `<span>trapped ${fmtOI(r.uw_oi)}</span>` +
        `<span>unwound ${fmtOI(r.unwind_5m)}/5m</span>` +
        `<span>prem ${(r.prem_vel*100).toFixed(1)}%</span></div>`;
    }
  } else {
    html += `<div class="calm">${sq.verdict || "no writer book under pressure"} — ` +
      `writer walls are holding; squeeze fuel builds only when a written strike goes underwater.</div>`;
  }
  $("chPain").innerHTML = html;
}

function chSpk(label, sets, last){
  let all = [];
  for(const s of sets) all = all.concat(s.v.filter(x=>x!=null));
  if(!all.length) return "";
  const lo = Math.min(...all), hi = Math.max(...all), rng = Math.max(hi-lo, 1e-9);
  const lines = sets.map(s=>{
    const pts = [];
    s.v.forEach((x,i)=>{ if(x!=null)
      pts.push(`${(i/(s.v.length-1||1)*100).toFixed(1)},${(31-(x-lo)/rng*28).toFixed(1)}`); });
    return `<polyline points="${pts.join(" ")}" fill="none" stroke="${s.c}" ` +
           `stroke-width="1.2" vector-effect="non-scaling-stroke"/>`;
  }).join("");
  return `<div class="spk"><label>${label}<b>${last}</b></label>` +
    `<svg viewBox="0 0 100 34" preserveAspectRatio="none">${lines}</svg></div>`;
}

function renderChainSpark(j){
  const se = j.series || []; if(!se.length){ $("chSpark").innerHTML=""; return; }
  const v = k => se.map(p=>p[k]);
  const lastv = k => { const a = v(k).filter(x=>x!=null); return a.length?a[a.length-1]:null; };
  const gexLast = lastv("gex");
  $("chSpark").innerHTML =
    chSpk("PCR (OI)", [{v:v("pcr"), c:"#8b5cf6"}], lastv("pcr") ?? "—") +
    chSpk("GEX TOTAL", [{v:v("gex"), c:"#3fc1c9"}],
          gexLast==null ? "—" : gexLast.toExponential(1)) +
    chSpk("SPOT · FLIP · MAXPAIN",
          [{v:v("spot"), c:"#dbe6f5"},{v:v("flip"), c:"#3fc1c9"},{v:v("mp"), c:"#ffbf00"}],
          j.spot.toFixed(0)) +
    chSpk("SQUEEZE", [{v:v("sq"), c:"#ff5f6b"}],
          Math.round((lastv("sq")||0)*100) + "%");
}

boot();
