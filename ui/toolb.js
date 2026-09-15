/* ===========================================================================
   toolb.js -- the operator's tool.

   THREE LAWS THIS FILE OBEYS
   1. STABLE LAYOUT. The DOM is built once. Every poll writes values into
      elements that already exist. Lists diff by key and reuse their rows.
      Nothing is ever innerHTML'd wholesale on a timer, so nothing jumps.
   2. THE ANSWER NEVER CHANGES SILENTLY. Every gear/direction/conviction/
      structure change between polls is timestamped, explained from the API's
      own `why` fields, appended to a visible log and persisted per-date.
   3. ABSENCE HAS A REASON. "checked, nothing found", "could not check" and
      "not shown here" are three different renderings and never collapse.
   =========================================================================== */
'use strict';

const API = '';                 // same origin -- the server static-serves ui/
const POLL_MS = 5000;
const CLOSED_POLL_MS = 30000;   // market shut: nothing moves, so stop hammering
const FLOW_MS = 60000;          // per-strike OI timelines move every 5 min
const DWELL_FULL = 300;         // the siege clock's denominator, from the API

/* ------------------------------------------------------------------ utils */
const $ = id => document.getElementById(id);

/* write only on change: an unchanged node is never touched, so no repaint,
   no flicker, no scroll jump. This is the whole of Law 1. */
function setText(el, v){ if(el && el.textContent !== String(v)) el.textContent = String(v); }
function setClass(el, c){ if(el && el.className !== c) el.className = c; }

const IST = { timeZone:'Asia/Kolkata', hour12:false };
const istNow = () => new Date().toLocaleTimeString('en-GB', {...IST, hour:'2-digit', minute:'2-digit', second:'2-digit'});
const istHM  = () => new Date().toLocaleTimeString('en-GB', {...IST, hour:'2-digit', minute:'2-digit'});
const istDate= () => new Date().toLocaleDateString('en-CA', {timeZone:'Asia/Kolkata'});

const hm2min = s => { const m=/^(\d{1,2}):(\d{2})/.exec(s||''); return m ? (+m[1])*60 + (+m[2]) : null; };

function num(v, d=2){
  if(v===null||v===undefined||Number.isNaN(v)) return '—';
  const n = Number(v);
  return n.toLocaleString('en-IN', {minimumFractionDigits:d, maximumFractionDigits:d});
}
function px(v){ return v===null||v===undefined ? '—' : Number(v).toLocaleString('en-IN',{maximumFractionDigits:2}); }
function compact(v){
  if(v===null||v===undefined) return '—';
  const n = Math.abs(v), s = v<0?'-':'';
  if(n>=1e7) return s+(n/1e7).toFixed(2)+'Cr';
  if(n>=1e5) return s+(n/1e5).toFixed(2)+'L';
  if(n>=1e3) return s+(n/1e3).toFixed(1)+'k';
  return s+n.toFixed(0);
}
function oiC(v){ // OI is big; walls read better in M
  if(v===null||v===undefined) return '—';
  const n=Math.abs(v), s=v<0?'−':'';
  if(n>=1e6) return s+(n/1e6).toFixed(1)+'M';
  if(n>=1e3) return s+(n/1e3).toFixed(0)+'k';
  return s+n.toFixed(0);
}
function pct(v,d=0){ return v===null||v===undefined ? '—' : (v*100).toFixed(d)+'%'; }

/* the [M]/[I] tag rides every number the API tags */
function tagHTML(t){
  if(!t) return '';
  const c = String(t).replace(/[^MI]/g,'') || 'I';
  // brackets are not decoration: a bare "M" badge after a number collides with
  // the M-for-millions used on every OI figure ("±57.5M" read as 57 million).
  return `<span class="tag ${c}">[${c}]</span>`;
}
const esc = s => String(s===null||s===undefined?'':s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

/* the three absences -- deliberately three different renderings */
function absNone(what){ return `<span class="abs none">dekh liya — ${esc(what)} nahi mila</span>`; }
function absUnchecked(why){ return `<span class="abs unchecked">check nahi kar paye<span class="w"> — ${esc(why)}</span></span>`; }
function absHidden(where){ return `<span class="abs hidden">yahan nahi dikhaya — ${esc(where)}</span>`; }

/* -------------------------------------------------------------- app state */
const S = {
  idx: 'NIFTY',
  screen: 'desk',
  desk:null, health:null, warmap:null, surface:null, drag:null,
  senses:null, paper:null, tape:null,
  flow:{},            // strike -> oiflow rows, for the per-wall timeline
  flowAt:0, flowIdx:null,
  book:null,          // book-wide oiflow (all strikes summed)
  prem:{},            // strike -> [{t,ce,pe}] premium, accumulated from /api/chain
  openStruct:new Set(),
  err:{},             // endpoint -> could not reach
  thin:{},            // endpoint -> reached, but it had nothing for this session
  lastOK:{},
  vpinDay:[],         // client-accumulated until a /api/vpin day endpoint exists
  vpinSrc:'client',
  polls:0
};

async function getJSON(path, key){
  try{
    const r = await fetch(API+path, {cache:'no-store'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const j = await r.json();
    delete S.err[key]; S.lastOK[key]=Date.now();
    absorbCoverage(j);            // health/drag/vpin/oiflow all carry it
    return j;
  }catch(e){
    S.err[key] = e.message || String(e);
    return null;   // NEVER null out the caller's last-good copy
  }
}

/* ---- last-good payloads survive a reload -------------------------------
   A failed poll already keeps the in-RAM copy (getJSON returns null and the
   caller skips the assignment). That is not enough: a refresh while the
   server is down would still open blank. So the payloads themselves are
   snapshotted, with the wall-clock they were true at, and restored on boot.
   ponytail: throttled to every 6th poll (~30s) + pagehide -- stringifying
   ~130KB every 5s is waste; worst case is a 30s-older snapshot, and the
   banner always states the age so nothing is passed off as fresh. */
const SNAP_KEYS = ['desk','warmap','surface','drag','senses','paper','tape','book','vpinsrv','cov'];

/* The snapshot is a HIGH-WATER MARK of the best data this browser ever saw,
   not a mirror of the current state. A restarted server serves an empty day;
   mirroring that would quietly overwrite the good copy and lose the session --
   the exact failure this whole mechanism exists to prevent. So a key is only
   written when the value we hold for it is usable; otherwise the stored one
   stands. */
function persistSnapshot(){
  const prev = loadLS('snap', null) || {};
  const snap = {ts:Date.now(), at:istNow(), idx:S.idx};
  let anyFresh = false;
  for(const k of SNAP_KEYS){
    const cur = S[k];
    const good = cur && (!USABLE[k] || USABLE[k](cur));
    if(good){ snap[k]=cur; anyFresh = true; }
    else if(prev[k]) snap[k]=prev[k];             // keep the better memory
  }
  // if nothing we hold is usable, do not move the timestamp either
  if(!anyFresh && prev.ts){ snap.ts = prev.ts; snap.at = prev.at; }
  saveLS('snap', snap);
  if(Object.keys(S.flow||{}).length) saveLS('flow', S.flow, S.idx);
  if(Object.keys(S.prem||{}).length) saveLS('prem', S.prem, S.idx);
}

function restoreSnapshot(){
  const snap = loadLS('snap', null);
  if(!snap) return false;
  for(const k of SNAP_KEYS) if(snap[k]) S[k]=snap[k];
  S.flow    = loadLS('flow', {}, S.idx) || {};
  S.flowIdx = Object.keys(S.flow).length ? S.idx : null;
  S.restoredAt = snap.at;
  S.lastGoodAt = snap.ts;
  return true;
}

/* one clock for "how old is what you are looking at" */
function staleSeconds(){
  return S.lastGoodAt ? Math.round((Date.now()-S.lastGoodAt)/1000) : null;
}

/* ==========================================================================
   SESSION COVERAGE -- the server's own late-start honesty.
   It publishes when it started, how late that was, what it rebuilt and what
   has no morning and never will. None of that was on screen before. Its
   sentences are rendered VERBATIM: they are the server's claim, and softening
   them into our own words would be us making a different claim.
   ========================================================================== */
function absorbCoverage(o){
  if(o && o.coverage && typeof o.coverage === 'object') S.cov = o.coverage;
}

/* Pick the coverage line that actually explains THIS panel's gap. */
const COV_TOPIC = {
  warmap : /war[- ]map|dwell|sequence/i,
  drag   : /drag meter|buyer's-tax|buyer.s tax/i,
  vpin   : /toxicity|vpin/i,
  surface: /IV, greeks|fitted surface|gamma flip/i,
  paper  : /paper desk/i,
  oiflow : /per-strike OI|minute grid/i
};
function covReason(topic){
  const c = S.cov; if(!c) return '';
  const re = COV_TOPIC[topic]; if(!re) return '';
  const lost = (c.not_reconstructable||[]).filter(x=>re.test(x));
  const back = (c.reconstructed||[]).filter(x=>re.test(x));
  if(!lost.length && !back.length) return '';
  const say = lost.length ? lost[0] : back[0];
  return `<span class="cov-src">${lost.length?'is session me nahi mila':'wapas banaya gaya'} —
    <i>${esc(say)}</i>${lost.length?'':tagHTML('I')}</span>`;
}

function renderCoverage(){
  const c = S.cov, bar = $('coverage');
  if(!bar) return;
  const late = c && Number(c.late_min) > 0;
  if(!c || !late){ bar.setAttribute('hidden',''); return; }
  bar.removeAttribute('hidden');
  setText($('covHd'), `SESSION COVERAGE — server ${c.server_up} se, open (${c.session_open}) ke ${c.late_min} min baad`);
  setText($('covWhy'), c.why || '');
  const li = (arr, cls) => (arr||[]).map(x=>`<li class="${cls}">${esc(x)}</li>`).join('');
  const html =
    ((c.not_reconstructable||[]).length
      ? `<h5>jo gaya, wapas nahi aayega</h5><ul>${li(c.not_reconstructable,'lost')}</ul>` : '') +
    ((c.reconstructed||[]).length
      ? `<h5>jo wapas banaya gaya [I]</h5><ul>${li(c.reconstructed,'back')}</ul>` : '');
  if($('covDetail').innerHTML !== html) $('covDetail').innerHTML = html;
}

/* ---- THE THIRD CASE ------------------------------------------------------
   A restarted server answers HTTP 200 with an EMPTY day: desk ok:false with a
   null view, warmap "no war map yet". Assigning that over a good restored
   snapshot is how "server restart ho gaya to sab gayab" actually happens --
   not through a failed request, but through a successful one carrying
   nothing. So a payload must prove it is usable before it may replace what we
   already hold, and the three states stay distinct:
     err[k]        -> could not reach it
     thin[k]       -> reached it, it has nothing for this session
     neither       -> real data
   ------------------------------------------------------------------------- */
const USABLE = {
  desk:   d => !!(d && d.indices) && Object.values(d.indices)
                .some(v => v && (v.view || (v.regime && v.regime.spot!=null))),
  warmap: w => !!(w && w.indices) && Object.values(w.indices).some(v => v && v.ok !== false),
  surface:s => !!(s && s.indices) && Object.keys(s.indices).length>0,
  drag:   g => !!(g && g.indices) && Object.keys(g.indices).length>0,
  senses: s => !!(s && s.vpin),
  vpinsrv:v => !!(v && Array.isArray(v.series) && v.series.length),
  data:   t => !!(t && t.days && t.days[0] && (t.days[0].bars||[]).length),
  book:   b => !!(b && Array.isArray(b.rows) && b.rows.length),
  paper:  p => !!(p && p.desk)
};

/* Accept into state only if usable. Returns the value actually kept. */
function accept(key, val, cur){
  if(val === null) return cur;                    // request failed -> keep
  const ok = USABLE[key] ? USABLE[key](val) : !!val;
  if(ok){ delete S.thin[key]; return val; }
  S.thin[key] = true;                             // reached, but empty
  return cur !== undefined && cur !== null ? cur : val;
}

/* ==========================================================================
   FLIP TRACKING -- Law 2.
   A signature is the answer. When any field of it moves between polls we
   write a line saying exactly what moved and, from the API's own why fields,
   what moved it. Persisted per date so a reload never loses the day's story.
   ========================================================================== */
/* Keyed by date, and by index where the thing being stored is per-index.
   Her stated worst case is "refresh kare aur chala jaye / server restart ho
   gaya to sab gayab". So nothing the client accumulated may live only in RAM:
   every series, every counter and the last-good payloads all land here. */
/* ---- WHICH SESSION AM I LOOKING AT? -------------------------------------
   The calendar date and the trading session are not the same thing. Between
   15:30 and midnight the screen still shows TODAY's session. Before 09:15 the
   newest thing that exists is YESTERDAY's, and it must be labelled as such
   rather than silently presented as today. Storage follows the SESSION date,
   so opening at 08:00 restores the previous session instead of a blank day. */
const OPEN_MIN = 9*60+15, CLOSE_MIN = 15*60+30, WRAP_MIN = 15*60+40;

function prevDateStr(){
  const d = new Date(Date.now() - 864e5);
  return d.toLocaleDateString('en-CA', {timeZone:'Asia/Kolkata'});
}
/* newest session we actually hold anything for -- survives weekends and
   holidays without a calendar, because it asks storage instead of guessing */
function latestStoredDate(){
  let best=null;
  try{
    for(let i=0;i<localStorage.length;i++){
      const m = /^toolb\.snap\.(\d{4}-\d{2}-\d{2})$/.exec(localStorage.key(i));
      if(m && (!best || m[1]>best)) best=m[1];
    }
  }catch(e){}
  return best;
}
function sessionDate(){
  const now = hm2min(istHM());
  if(now===null || now >= OPEN_MIN) return istDate();
  return latestStoredDate() || prevDateStr();   // pre-open: the previous session
}
function sessionPhase(){
  const now = hm2min(istHM());
  const sd = sessionDate(), today = istDate();
  if(now===null) return {phase:'LIVE', label:'', date:sd};
  if(now < OPEN_MIN)  return {phase:'PREV',   label:`PICHHLA SESSION · ${sd}`, date:sd};
  if(now < CLOSE_MIN) return {phase:'LIVE',   label:'LIVE', date:today};
  if(now < WRAP_MIN)  return {phase:'CLOSING',label:'CLOSING · 15:30–15:40', date:today};
  return {phase:'CLOSED', label:'MARKET CLOSED · aaj ka poora session', date:today};
}

const LSK = (k, idx) => `toolb.${k}.${sessionDate()}` + (idx ? '.'+idx : '');

function loadLS(k, dflt, idx){
  try{ const v = localStorage.getItem(LSK(k, idx)); return v ? JSON.parse(v) : dflt; }
  catch(e){ return dflt; }
}
function saveLS(k, v, idx){
  try{ localStorage.setItem(LSK(k, idx), JSON.stringify(v)); }
  catch(e){ /* quota or private mode: the UI still runs, it just forgets */
    S.lsFail = (e && e.name) || 'write failed'; }
}

/* Merge a local (remembered) series with the server's own, keyed on time.
   THE SERVER WINS where both have a stamp -- its log is authoritative. The
   local copy only fills stamps the server no longer has, which is exactly the
   restart case: the drag day-ring resets in memory but the browser saw it. */
function mergeByT(local, server, key){
  key = key || 't';
  const m = new Map();
  for(const p of (local||[]))  if(p && p[key]!=null) m.set(String(p[key]), p);
  for(const p of (server||[])) if(p && p[key]!=null) m.set(String(p[key]), p);
  return [...m.values()].sort((a,b)=>(hm2min(a[key])??0)-(hm2min(b[key])??0));
}

let FLIPS = loadLS('flips', {});   // idx -> [{ts,kind,text}]
let SIG   = loadLS('sig', {});     // idx -> {bias,gear,conviction,struct,since:{...}}
let TRANS = loadLS('trans', {});   // idx -> count of single-poll flickers
let DAYT  = loadLS('dayt', {});    // idx -> {type, since, ev[]}  market character
const DPEND = {};                  // idx -> {type, n} -- day-type confirmation
const PEND = {};                   // idx -> {sig, val, n} -- awaiting confirmation

/* A change must survive TWO consecutive polls before it is called a flip.
   The desk's DEPLOYABLE set flickers on single ticks; logging that churn would
   pin the stability meter at UNSTABLE all day and destroy the one signal she
   needs. Flicker is NOT swallowed -- it is counted and shown separately, so
   "the answer never silently changes" still holds. */
const sigOf = c => `${c.bias}|${c.gear}|${c.conviction}|${c.struct}`;

/* `best` is a STRING (the structure's name) or null -- it is NOT a candidate
   object, so it must be resolved against candidates[] before use. Treating it
   as an object manufactures phantom "structure" flips (undefined:undefined)
   and corrupts the stability meter. */
function topStructure(d){
  if(!d || !Array.isArray(d.candidates)) return null;
  const dep = d.candidates.find(c => c.status === 'DEPLOYABLE');
  if(dep) return dep;
  if(typeof d.best === 'string'){
    return d.candidates.find(c => c.name === d.best) || null;
  }
  return (d.best && typeof d.best === 'object') ? d.best : null;
}

function trackFlips(deskJSON){
  if(!deskJSON || !deskJSON.indices) return;
  const t = istHM();
  let changed = false;

  for(const ix of Object.keys(deskJSON.indices)){
    const d = deskJSON.indices[ix];
    const v = d.view || {};
    const st = topStructure(d);
    const cur = {
      bias: v.bias ?? 'UNKNOWN',
      gear: v.gear ?? 'UNKNOWN',
      conviction: v.conviction ?? 'UNKNOWN',
      struct: (st && st.name) ? `${st.name}:${st.status||'?'}` : 'none',
      worst: v.worst_leg ?? null
    };
    const prev = SIG[ix];
    FLIPS[ix] = FLIPS[ix] || [];

    if(!prev){
      // First sight this session. That is NOT a flip -- log it as the baseline
      // so the log never opens with a phantom change.
      SIG[ix] = {...cur, since:{bias:t, gear:t, conviction:t, struct:t}};
      FLIPS[ix].unshift({ts:t, kind:'seed',
        text:`session shuru — <b>${esc(cur.bias)}</b> · gear ${esc(cur.gear)} · ${esc(cur.conviction)}`});
      changed = true;
      continue;
    }

    // --- two-poll confirmation gate -------------------------------------
    if(sigOf(cur) === sigOf(prev)){
      if(PEND[ix]){                       // a change appeared and reverted
        TRANS[ix] = (TRANS[ix]||0) + 1;
        delete PEND[ix];
        changed = true;
      }
      SIG[ix] = {...cur, since:prev.since};
      continue;
    }
    if(!PEND[ix] || PEND[ix].sig !== sigOf(cur)){
      PEND[ix] = {sig:sigOf(cur), val:cur, n:1};
      continue;                            // wait one more poll before believing it
    }
    PEND[ix].n++;
    if(PEND[ix].n < 2) continue;
    delete PEND[ix];                       // confirmed -- now log what moved

    const since = {...prev.since};
    const add = (kind, text) => { FLIPS[ix].unshift({ts:t, kind, text}); changed = true; };

    if(cur.bias !== prev.bias){
      const pain = (prev.worst && cur.worst && prev.worst !== cur.worst)
        ? ` <span class="quiet">(pain ${esc(prev.worst)}<span class="arrow">→</span>${esc(cur.worst)})</span>` : '';
      add('dir', `direction <b>${esc(prev.bias)}</b><span class="arrow">→</span><b>${esc(cur.bias)}</b>${pain}`);
      since.bias = t;
    }
    if(cur.gear !== prev.gear){
      add('gear', `gear <b>${esc(prev.gear)}</b><span class="arrow">→</span><b>${esc(cur.gear)}</b>`);
      since.gear = t;
    }
    if(cur.conviction !== prev.conviction){
      add('gear', `conviction ${esc(prev.conviction)}<span class="arrow">→</span><b>${esc(cur.conviction)}</b>`);
      since.conviction = t;
    }
    if(cur.struct !== prev.struct){
      const why = st && st.why && st.why[0] ? ` <span class="quiet">${esc(String(st.why[0]).slice(0,90))}</span>` : '';
      add('struct-f', `structure <b>${esc(prev.struct)}</b><span class="arrow">→</span><b>${esc(cur.struct)}</b>${why}`);
      since.struct = t;
    }
    SIG[ix] = {...cur, since};
    if(FLIPS[ix].length > 300) FLIPS[ix].length = 300;
  }
  if(changed){ saveLS('flips', FLIPS); saveLS('sig', SIG); saveLS('trans', TRANS); }
}

/* flips in the trailing 60 minutes -- seeds excluded, they are not flips */
function flipsLastHour(ix){
  const now = hm2min(istHM());
  return (FLIPS[ix]||[]).filter(f => {
    if(f.kind === 'seed') return false;
    const m = hm2min(f.ts);
    return m !== null && now !== null && (now - m) <= 60 && (now - m) >= 0;
  }).length;
}

function ageStr(sinceHM){
  const a = hm2min(sinceHM), now = hm2min(istHM());
  if(a===null||now===null) return '';
  const d = Math.max(0, now-a);
  return d < 60 ? `${d} min` : `${Math.floor(d/60)}h ${d%60}m`;
}

/* ==========================================================================
   "KAISA DIN HAI" -- the day's character, from signals that already exist.

   Rules-based and nothing else. Each rule is a conjunction of measured
   conditions; a rule fires only when ALL of its conditions are TRUE, and a
   condition whose input is missing makes the rule UNFIRABLE (never "probably").
   Exactly one fires -> that is the day. Two or more -> MIXED, both named.
   None -> "ABHI TAY NAHI" with the nearest rule's unmet conditions listed.
   Tagged [I] end to end: this is an inference over measurements, never a
   measurement, and it licenses nothing.
   ========================================================================== */
function dayInputs(ix){
  const dk = S.desk && S.desk.indices && S.desk.indices[ix];
  const wm = S.warmap && S.warmap.indices && S.warmap.indices[ix];
  const sf = S.surface && S.surface.indices && S.surface.indices[ix];
  const bars = S.tape && S.tape.days && S.tape.days[0] && S.tape.days[0].bars;
  const ctx = (S.tape && S.tape.index===ix && bars && bars.length) ? bars[bars.length-1].ctx : null;

  const vpsrc = (S.senses && S.senses.vpin) ? S.senses.vpin[ix+'-FUT'] : null;
  const vp = vpsrc && vpsrc.pct!==null && vpsrc.pct!==undefined ? vpsrc.pct : null;

  const day = sf && sf.day;
  const ivChg = (day && day.open && day.now && day.open.a!=null && day.now.a!=null)
    ? day.now.a - day.open.a : null;

  const spot = wm ? wm.spot : (dk && dk.regime ? dk.regime.spot : null);
  const maxPain = wm ? wm.max_pain : (dk && dk.regime ? dk.regime.max_pain : null);
  const em = dk && dk.regime ? dk.regime.expected_move : null;

  // near-spot wall pressure: are BOTH sides adding, or is one side bailing out
  let ceChg=null, peChg=null;
  if(wm && wm.heat && wm.heat.length && spot!=null){
    const near = wm.heat.filter(h=>Math.abs(h.k-spot) <= (em||100)*1.5);
    if(near.length){
      ceChg = near.reduce((a,h)=>a+(h.ce_chg||0),0);
      peChg = near.reduce((a,h)=>a+(h.pe_chg||0),0);
    }
  }
  // deepest retreat off peak among the walls we hold timelines for
  let maxRetreat=null, retreatAt=null;
  for(const k of Object.keys(S.flow)){
    const f = wallFlow(Number(k)); if(!f) continue;
    for(const side of ['ce','pe']){
      const s=f[side]; if(!s || !(s.peak>0)) continue;
      // clamped at source: OI added-since-open can go negative, which would
      // otherwise yield "184% off peak" everywhere this value is read
      const r = Math.min(1, (s.peak - s.now)/s.peak);
      if(maxRetreat===null || r>maxRetreat){ maxRetreat=r; retreatAt=`${px(Number(k))}${side.toUpperCase()}`; }
    }
  }
  return {
    vp, ivChg, spot, maxPain, em, ceChg, peChg, maxRetreat, retreatAt,
    z: ctx ? ctx.z : null,
    rng_r: ctx ? ctx.rng_r : null,
    inside1: ctx ? ctx.inside1 : null,
    line: ctx ? ctx.line : null,
    episode: ctx ? ctx.episode : null,
    dwell: wm ? wm.dwell : null,
    richer: wm && wm.runways ? wm.runways.richer : null,
    ctxOK: !!ctx
  };
}

/* one condition = {ok:true|false|null(unknown), txt}. null blocks the rule. */
const cond = (ok, txt) => ({ok, txt});

function dayRules(I){
  const pinDist = (I.spot!=null && I.maxPain!=null) ? Math.abs(I.spot-I.maxPain) : null;
  const emHalf  = I.em!=null ? I.em*0.5 : null;
  const up = I.z!=null ? I.z>0 : null;

  return [
    {name:'SQUEEZE', hi:'SQUEEZE — koi phans gaya, bhaag raha hai', conds:[
      cond(I.vp==null?null:I.vp>=0.75, `VPIN ${I.vp==null?'—':pct(I.vp,0)} of day ≥ 75%`),
      cond(I.maxRetreat==null?null:I.maxRetreat>=0.15,
        `deewar gir rahi hai: ${I.retreatAt||'—'} ${I.maxRetreat==null?'—':pct(I.maxRetreat,0)} off peak`),
      cond(I.rng_r==null?null:I.rng_r>=0.85, `range rank ${num(I.rng_r,2)} ≥ 0.85 — box toot gaya`)
    ]},
    {name:'TREND', hi:'TREND DAY — ek taraf ka din', conds:[
      cond(I.z==null?null:Math.abs(I.z)>=1.0, `bands pe chal raha hai (z ${num(I.z,2)})`),
      cond(I.rng_r==null?null:I.rng_r>=0.6, `range rank ${num(I.rng_r,2)} ≥ 0.60`),
      cond(I.inside1==null?null:I.inside1<=0.35, `sirf ${I.inside1==null?'—':pct(I.inside1,0)} bars ±1σ ke andar`),
      cond((up==null||I.richer==null)?null:(up ? I.richer==='UP' : I.richer==='DOWN'),
        `fuel bhi ${I.richer||'—'} taraf — move ke saath`)
    ]},
    {name:'PIN', hi:'PIN / EXPIRY — max pain ka magnet', conds:[
      cond((pinDist==null||emHalf==null)?null:pinDist<=emHalf,
        `spot max-pain se sirf ${pinDist==null?'—':num(pinDist,0)} pts (½ EM ${emHalf==null?'—':num(emHalf,0)})`),
      cond((I.ceChg==null||I.peChg==null)?null:(I.ceChg>0 && I.peChg>0),
        `dono deewarein ban rahi hain (CE ${oiC(I.ceChg)} / PE ${oiC(I.peChg)})`),
      cond(I.rng_r==null?null:I.rng_r<=0.5, `range rank ${num(I.rng_r,2)} ≤ 0.50 — dabaa hua`)
    ]},
    {name:'ROTATION', hi:'ROTATION — do taraf ka, box ke andar', conds:[
      cond(I.vp==null?null:I.vp<=0.5, `VPIN ${I.vp==null?'—':pct(I.vp,0)} ≤ 50% — flow zehreela nahi`),
      cond(I.inside1==null?null:I.inside1>=0.55, `${I.inside1==null?'—':pct(I.inside1,0)} bars ±1σ ke andar`),
      cond(I.rng_r==null?null:I.rng_r<=0.6, `range rank ${num(I.rng_r,2)} ≤ 0.60 — box saabut`),
      cond(I.maxRetreat==null?null:I.maxRetreat<0.15, `koi deewar giri nahi`)
    ]},
    {name:'QUIET', hi:'QUIET — kuch nahi ho raha, baith ke dekh', conds:[
      cond(I.ivChg==null?null:Math.abs(I.ivChg)<=0.005,
        `ATM vol din bhar me sirf ${I.ivChg==null?'—':(I.ivChg*100).toFixed(2)} pts hila`),
      cond(I.vp==null?null:I.vp<=0.35, `VPIN ${I.vp==null?'—':pct(I.vp,0)} ≤ 35%`),
      cond(I.rng_r==null?null:I.rng_r<=0.4, `range rank ${num(I.rng_r,2)} ≤ 0.40`),
      cond(I.dwell==null?null:!I.dwell.holding, `kisi level pe ruka nahi hua`)
    ]}
  ];
}

function computeDayType(ix){
  const I = dayInputs(ix);
  const rules = dayRules(I);
  const fired = rules.filter(r=>r.conds.every(c=>c.ok===true));
  const blocked = rules.filter(r=>r.conds.some(c=>c.ok===null));

  if(fired.length===1){
    const r=fired[0];
    return {type:r.name, hi:r.hi, ev:r.conds.map(c=>c.txt), missing:[], mixed:false};
  }
  if(fired.length>1){
    return {type:'MIXED', hi:'MIXED — signals ladd rahe hain',
      ev:fired.map(r=>`${r.name}: ${r.conds.map(c=>c.txt).join(' · ')}`),
      missing:[], mixed:true, names:fired.map(r=>r.name)};
  }
  // nothing fired: name the closest rule and exactly what it is short of
  let best=null, bestN=-1;
  for(const r of rules){
    const n=r.conds.filter(c=>c.ok===true).length;
    if(n>bestN){ bestN=n; best=r; }
  }
  const unmet = best ? best.conds.filter(c=>c.ok!==true) : [];
  return {type:'UNDECIDED', hi:'ABHI TAY NAHI — din ka character abhi nahi bana',
    ev: best ? best.conds.filter(c=>c.ok===true).map(c=>c.txt) : [],
    missing: unmet.map(c=>(c.ok===null?'check nahi kar paye: ':'abhi nahi: ')+c.txt),
    near: best?best.name:null, blockedCount:blocked.length, mixed:false};
}

/* Day character is logged with the same discipline as the answer -- two polls
   before it counts -- but into its own stream. A day changing character is
   information; it is NOT a reason to distrust the desk's answer, so it must
   never inflate the answer's stability meter. */
function trackDayType(ix, dt){
  const t = istHM();
  const prev = DAYT[ix];
  if(!prev){
    DAYT[ix] = {type:dt.type, since:t, ev:dt.ev};
    saveLS('dayt', DAYT);
    return;
  }
  if(prev.type === dt.type){
    if(DPEND[ix]) delete DPEND[ix];
    DAYT[ix] = {...prev, ev:dt.ev};
    saveLS('dayt', DAYT);
    return;
  }
  if(!DPEND[ix] || DPEND[ix].type !== dt.type){ DPEND[ix]={type:dt.type, n:1}; return; }
  if(++DPEND[ix].n < 2) return;
  delete DPEND[ix];
  FLIPS[ix] = FLIPS[ix]||[];
  FLIPS[ix].unshift({ts:t, kind:'day',
    text:`din ka character <b>${esc(prev.type)}</b><span class="arrow">→</span><b>${esc(dt.type)}</b>` +
         (dt.ev[0]?` <span class="quiet">${esc(String(dt.ev[0]).slice(0,80))}</span>`:'')});
  DAYT[ix] = {type:dt.type, since:t, ev:dt.ev};
  saveLS('dayt', DAYT); saveLS('flips', FLIPS);
}

function renderDayTile(){
  const dt = computeDayType(S.idx);
  trackDayType(S.idx, dt);
  const st = DAYT[S.idx] || {};
  const big = $('dtType'), sub = $('dtSub');

  setText(big, dt.type==='UNDECIDED' ? 'TAY NAHI' : dt.type);
  big.className = 'dt-'+dt.type;
  $('dtHi').innerHTML = esc(dt.hi)+tagHTML('I');
  setText($('dtAge'), st.since ? `${st.since} se · ${ageStr(st.since)}` : '');

  const ev = dt.ev.slice(0,3).map(e=>`<li>${esc(e)}</li>`).join('');
  const miss = (dt.missing||[]).slice(0,3).map(m=>`<li class="dt-miss">${esc(m)}</li>`).join('');
  sub.innerHTML =
    (ev ? `<ul class="why">${ev}</ul>` : '') +
    (miss ? `<ul class="why">${miss}</ul>` : '') +
    (dt.near ? `<div class="quiet">sabse kareeb: ${esc(dt.near)}</div>` : '') +
    (dt.mixed ? `<div class="quiet">jhagda: ${esc((dt.names||[]).join(' vs '))}</div>` : '');
}

/* ==========================================================================
   SVG time series. Gap-aware on purpose: the feed can die, and a line drawn
   straight through a dead half-hour is a lie. Points more than 2.5x the
   median spacing apart break the path and the hole is hatched + counted.
   ========================================================================== */
function lineChart(host, pts, opt){
  opt = opt || {};
  const W=600, H=opt.h||150, L=44, R=10, T=12, B=18;
  if(!pts || pts.length === 0){
    host.innerHTML = `<div class="pb">${opt.empty || absNone('points')}</div>`;
    return {gaps:0};
  }
  const xs = pts.map(p => hm2min(p.t)).filter(v=>v!==null);
  const vs = pts.map(p => p.v).filter(v => v!==null && !Number.isNaN(v));
  if(!xs.length || !vs.length){
    host.innerHTML = `<div class="pb">${opt.empty || absNone('kaam ke points')}</div>`;
    return {gaps:0};
  }
  let lo = opt.lo!==undefined ? opt.lo : Math.min(...vs);
  let hi = opt.hi!==undefined ? opt.hi : Math.max(...vs);
  if(hi===lo){ hi=lo+1e-9; }
  const pad=(hi-lo)*0.12; lo-=pad; hi+=pad;
  const x0=Math.min(...xs), x1=Math.max(...xs);
  const sx = m => L + (x1===x0?0:(m-x0)/(x1-x0))*(W-L-R);
  const sy = v => T + (1-(v-lo)/(hi-lo))*(H-T-B);

  // median spacing -> gap threshold
  const gaps=[]; const sorted=[...xs].sort((a,b)=>a-b);
  const diffs=[]; for(let i=1;i<sorted.length;i++) diffs.push(sorted[i]-sorted[i-1]);
  const med = diffs.length ? diffs.slice().sort((a,b)=>a-b)[Math.floor(diffs.length/2)] : 0;
  const thr = Math.max((med||1)*2.5, 6);

  let d='', prevM=null, seg=0;
  for(const p of pts){
    const m=hm2min(p.t); if(m===null||p.v===null||Number.isNaN(p.v)) continue;
    if(prevM!==null && (m-prevM)>thr){ gaps.push([prevM,m]); prevM=null; }
    d += (prevM===null ? `M${sx(m).toFixed(1)},${sy(p.v).toFixed(1)}` : `L${sx(m).toFixed(1)},${sy(p.v).toFixed(1)}`);
    if(prevM===null) seg++;
    prevM=m;
  }
  const ticks=[lo+(hi-lo)*0.05, (lo+hi)/2, hi-(hi-lo)*0.05];
  const fm = opt.fmt || (v=>v.toFixed(2));

  const gapRects = gaps.map(([a,b])=>
    `<rect x="${sx(a).toFixed(1)}" y="${T}" width="${(sx(b)-sx(a)).toFixed(1)}" height="${H-T-B}"
       fill="url(#gapHatch)"></rect>
     <text x="${((sx(a)+sx(b))/2).toFixed(1)}" y="${T+10}" fill="#E0A32E" font-size="8"
       text-anchor="middle" font-family="monospace">FEED GAP</text>`).join('');

  const marks = (opt.marks||[]).map(mk=>{
    const m=hm2min(mk.t); if(m===null) return '';
    return `<line x1="${sx(m).toFixed(1)}" y1="${T}" x2="${sx(m).toFixed(1)}" y2="${H-B}"
      stroke="${mk.color||'#63738C'}" stroke-width="1" stroke-dasharray="2 3"></line>
      <text x="${sx(m).toFixed(1)}" y="${H-B-3}" fill="${mk.color||'#63738C'}" font-size="8"
      text-anchor="middle" font-family="monospace">${esc(mk.label||'')}</text>`;
  }).join('');

  host.innerHTML =
`<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">
  <defs><pattern id="gapHatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="6" height="6" fill="rgba(224,163,46,.05)"></rect>
    <line x1="0" y1="0" x2="0" y2="6" stroke="rgba(224,163,46,.35)" stroke-width="1.5"></line>
  </pattern></defs>
  ${ticks.map(v=>`<line x1="${L}" y1="${sy(v).toFixed(1)}" x2="${W-R}" y2="${sy(v).toFixed(1)}"
      stroke="#151D28" stroke-width="1"></line>
    <text x="${L-5}" y="${(sy(v)+3).toFixed(1)}" fill="#63738C" font-size="9" text-anchor="end"
      font-family="monospace">${fm(v)}</text>`).join('')}
  ${gapRects}${marks}
  ${opt.zero!==undefined && opt.zero>lo && opt.zero<hi
     ? `<line x1="${L}" y1="${sy(opt.zero).toFixed(1)}" x2="${W-R}" y2="${sy(opt.zero).toFixed(1)}"
          stroke="#3E4B60" stroke-width="1"></line>` : ''}
  <path d="${d}" fill="none" stroke="${opt.color||'#8B7BF0'}" stroke-width="1.6"
        stroke-linejoin="round"></path>
  <text x="${L}" y="${H-4}" fill="#63738C" font-size="9" font-family="monospace">${esc(pts[0].t)}</text>
  <text x="${W-R}" y="${H-4}" fill="#63738C" font-size="9" text-anchor="end"
        font-family="monospace">${esc(pts[pts.length-1].t)}</text>
</svg>`;
  return {gaps:gaps.length, segments:seg};
}

/* tiny inline sparkline for a single wall's intraday build */
function spark(vals, w=90, h=18, color='#8B7BF0'){
  const v = vals.filter(x=>x!==null && !Number.isNaN(x));
  if(v.length<2) return '';
  const lo=Math.min(...v), hi=Math.max(...v), rng=(hi-lo)||1;
  const pts = v.map((x,i)=>`${(i/(v.length-1)*w).toFixed(1)},${(h-((x-lo)/rng)*h).toFixed(1)}`).join(' ');
  const peakI = v.indexOf(hi);
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.2"></polyline>
    <circle cx="${(peakI/(v.length-1)*w).toFixed(1)}" cy="${(h-((hi-lo)/rng)*h).toFixed(1)}"
      r="1.8" fill="#DCE5F2"></circle></svg>`;
}

/* ==========================================================================
   HEADER -- the answer rides here on every screen
   ========================================================================== */
function renderHeader(){
  setText($('clockT'), istNow());

  /* session framing. After the close the tool stops pretending to be live and
     starts answering "aaj kya hua" instead. */
  const sess = sessionPhase();
  const chip = $('sessChip');
  setText(chip, sess.label || sess.phase);
  setClass(chip, sess.phase==='LIVE' ? 'live' : sess.phase==='CLOSING' ? 'closing'
                : sess.phase==='PREV' ? 'prev' : 'closed');
  document.body.classList.toggle('closed', sess.phase==='CLOSED' || sess.phase==='PREV');
  setText($('dtLabel'), (sess.phase==='LIVE'||sess.phase==='CLOSING')
    ? 'KAISA DIN HAI' : 'KAISA DIN THA');

  const h = S.health, fd = $('feedDot');
  if(!h){ setClass(fd,''); setText($('feedTxt'), 'feed — check nahi kar paye'); }
  else{
    const f = h.feed || {};
    const dead = !f.connected || f.healthy === false;
    setClass(fd, dead ? 'dead' : 'ok');
    setText($('feedTxt'), dead
      ? `feed BAND${h.feed_why?' — '+h.feed_why:''}`
      : `feed chalu · ${f.instruments||0} inst · ${(f.age_s??0).toFixed(1)}s`);
  }

  const d = S.desk && S.desk.indices ? S.desk.indices[S.idx] : null;
  if(!d){
    setText($('acDir'), '—'); setText($('acGear'), '—');
    setText($('acAge'), S.err.desk ? 'check nahi kar paye' : 'garam ho raha hai');
    setText($('spotVal'), '—');
    return;
  }
  const v = d.view||{}, since = (SIG[S.idx]||{}).since || {};
  const dir = v.bias || 'UNKNOWN';
  setText($('acDir'), dir);
  $('acDir').style.color = dir==='BULL' ? 'var(--bull)' : dir==='BEAR' ? 'var(--bear)' : 'var(--flat)';

  // gear UNKNOWN is real information, but it must not shout -- presence law
  const gear = v.gear || 'UNKNOWN';
  setText($('acGear'), gear);
  $('acGear').style.color = gear==='UNKNOWN' ? 'var(--muted)' : 'var(--amber)';
  $('acGear').style.opacity = gear==='UNKNOWN' ? '.7' : '1';

  setText($('acAge'), `${since.bias||'—'} se · ${ageStr(since.bias)}`);

  const n = flipsLastHour(S.idx), st = $('acStab');
  setClass(st, n>=3 ? 's3' : n===2 ? 's2' : 's0');
  setText(st, n>=3 ? `BHAROSA MAT KAR · ${n} flips/60m`
    : n===2 ? `badal raha hai · 2 flips/60m` : `sthir · ${n} flip/60m`);

  const sp = d.regime && d.regime.spot;
  setText($('spotVal'), px(sp));
}

/* ==========================================================================
   DESK -- the answer, then what it would build, then what changed
   ========================================================================== */

/* ==========================================================================
   ROUND 6 -- THE SELLER'S FIVE QUESTIONS
   Direction is a servant of the escape alarm, never the headline. Everything
   here is either measured, derived-and-tagged [I], or a stated hole. No tile
   is allowed to invent a number to look complete.
   ========================================================================== */

function deskIdx(){ return (S.desk && S.desk.indices) ? S.desk.indices[S.idx] : null; }
function vpinPct(){
  const v = S.senses && S.senses.vpin ? S.senses.vpin[S.idx+'-FUT'] : null;
  return (v && v.pct!==null && v.pct!==undefined) ? v.pct : null;
}

/* ---- realized vol from the tape's own FUT bars ------------------------- */
function realizedVol(){
  const tp = S.tape, day = tp && tp.days && tp.days[0];
  const bars = (day && day.bars) || [];
  const c = bars.map(b=>b.fut && b.fut.c).filter(x=>x>0);
  if(c.length < 12) return {rv:null, why:'kaafi FUT bars nahi'};
  const r = [];
  for(let i=1;i<c.length;i++) r.push(Math.log(c[i]/c[i-1]));
  const n = r.length, mean = r.reduce((a,b)=>a+b,0)/n;
  const v = r.reduce((a,b)=>a+(b-mean)*(b-mean),0)/(n-1);
  const iv = tp.interval || 3;
  const perYear = (375/iv)*252;          // 375 trading minutes, 252 sessions
  return {rv: Math.sqrt(v*perYear), n, mins: n*iv, interval: iv};
}

/* The server now ships a real 5-session RV (fit.rv5). It wins over the
   client's intraday estimate; both stay on screen, labelled, because they
   answer slightly different questions (5-day regime vs today's tape).
   NOTE the basis mismatch the server itself declares: RV annualizes on 252
   TRADING days, this repo's IV uses 365 CALENDAR. We show the ratio as-is and
   put the warning next to it -- silently "fixing" it would be inventing a
   number the server refused to invent. */
function ivVsRv(){
  const sf = S.surface && S.surface.indices ? S.surface.indices[S.idx] : null;
  const fit = (sf && sf.fit) || {};
  const atm = fit.atm_iv;
  const R = realizedVol();                       // today, client-computed [I]
  const rv5 = fit.rv5 || null;                   // 5 sessions, server [M]
  const rvUse = rv5 && rv5.rv!==null && rv5.rv!==undefined ? rv5.rv : R.rv;
  const rvSrc = (rv5 && rv5.rv!==null && rv5.rv!==undefined) ? 'rv5' : 'today';
  const base = {iv:atm ?? null, rv:rvUse, rv5, rvToday:R.rv, rvSrc, R,
                rv5_why: fit.rv5_why || null};
  if(atm===null || atm===undefined)
    return {...base, ratio:null, why:'ATM IV nahi (surface fit nahi)'};
  if(rvUse===null || rvUse===undefined)
    return {...base, ratio:null, why: (fit.rv5_why || R.why || 'RV nahi')};
  return {...base, ratio: atm/rvUse};
}

/* ---- THE GATE ----------------------------------------------------------
   Boring on purpose. It answers "aaj naya risk lena bhi chahiye?" and it is
   allowed to say only three things. */
function gateState(){
  const reasons = [], holes = [];
  let level = 'TRADE', lead = null;
  const RANK = {TRADE:0,'HALF SIZE':1,'NO NEW RISK':2};
  /* the headline reason must be the one that CAUSED the level -- showing an
     expiry note next to NO NEW RISK when a VPIN burst is what closed the gate
     tells her the wrong thing about why she is standing down. */
  const worse = (l, why) => {
    reasons.push(why);
    if(RANK[l] > RANK[level]){ level = l; lead = why; }
  };

  const x = ivVsRv();
  if(x.ratio !== null){
    if(x.ratio < 1.0) worse('NO NEW RISK','vol saste — becho mat');
    else if(x.ratio < 1.1) worse('HALF SIZE','IV mushkil se RV upar');
  } else holes.push('IV vs RV: ' + (x.why||'naapa nahi gaya'));

  const d = deskIdx();
  const exp = d && d.expiry;
  if(exp){ if(String(exp) === istDate()) worse('HALF SIZE','expiry din — gamma tez'); }
  else holes.push('expiry date: desk ne di nahi');

  const vp = vpinPct();
  if(vp !== null){ if(vp >= 0.8) worse('NO NEW RISK','VPIN burst — flow zehreela'); }
  else holes.push('VPIN: abhi naapa nahi gaya');

  const dt = computeDayType(S.idx);
  if(dt.type === 'SQUEEZE') worse('NO NEW RISK','SQUEEZE din — haath peeche');
  else if(dt.type === 'MIXED' && (dt.names||[]).includes('SQUEEZE'))
    worse('HALF SIZE','SQUEEZE ka shak hai');

  // There is no event calendar anywhere in this backend. Guessing one would be
  // the single most dangerous invention on this screen.
  holes.push('event calendar wired nahi hai');

  return {level, reason: lead || 'koi rok nahi dikhti',
          reasons: reasons.filter(r=>r!==lead), holes, x, dt};
}

/* ---- the book we are actually reasoning about --------------------------
   Live paper positions if there are any; otherwise the desk's best candidate
   at its own suggested size, clearly labelled as hypothetical. */
function activeBook(){
  const p = S.paper && S.paper.desk;
  const open = (p && p.open) || [];
  const marks = new Map(((p && p.marks) || []).map(m=>[m.pid, m]));
  if(open.length){
    let nd=0, ng=0, nv=0, vegaKnown=false;
    const legs=[];
    for(const o of open){
      const m = marks.get(o.pid) || {};
      nd += m.net_delta || 0;
      ng += m.net_gamma || 0;
      for(const l of (o.legs||[])){
        const sgn = l.side==='SELL' ? -1 : 1;
        if(l.vega0!==null && l.vega0!==undefined){ nv += sgn*l.vega0*(l.qty||0); vegaKnown=true; }
        legs.push({strike:l.strike, right:l.right, side:l.side, qty:l.qty,
                   delta:l.delta0, px:l.entry_px});
      }
    }
    const r = (p && p.risk) || {};
    return {src:'paper', label:'abhi khuli positions', legs, netDelta:nd, netGamma:ng,
            netVega: vegaKnown?nv:null, marginUsed:r.margin_used, headroom:r.headroom,
            lots:p.lots, risk:r};
  }
  // fallback: what the desk would put on
  const d = deskIdx();
  const cand = d ? (d.candidates||[]).find(c=>c.status==='DEPLOYABLE') : null;
  if(!cand) return {src:null, why:'paper book khaali hai aur koi deployable structure bhi nahi'};
  const lot = d.lot_size || 1, lots = cand.lots || 0;
  const units = lot*lots;
  let nd=0, nv=0, vegaKnown=false;
  const legs=[];
  for(const l of (cand.legs||[])){
    const sgn = l.side==='SELL' ? -1 : 1;
    if(l.delta!==null && l.delta!==undefined) nd += sgn*l.delta*units;
    if(l.vega!==null && l.vega!==undefined){ nv += sgn*l.vega*units; vegaKnown=true; }
    legs.push({strike:l.strike, right:l.right, side:l.side, qty:units,
               delta:l.delta, px:l.ltp, bid:l.bid, ask:l.ask});
  }
  const r = (S.paper && S.paper.desk && S.paper.desk.risk) || {};
  return {src:'candidate', label:`agar yeh lagaya to — ${cand.name} @ ${lots} lots`,
          legs, netDelta:nd, netGamma:null, netVega:vegaKnown?nv:null,
          marginUsed:(cand.margin_per_lot||0)*lots,
          headroom:(r.capital||0) - (cand.margin_per_lot||0)*lots,
          lots, cand, lot};
}

/* P&L of the book for a spot move, second order. Gamma is what kills a
   seller, so a book without a gamma number says so rather than pretending
   the curve is a straight line. */
function bookPnl(bk, ds){
  if(!bk || bk.netDelta===null || bk.netDelta===undefined) return null;
  const g = bk.netGamma;
  return bk.netDelta*ds + (g ? 0.5*g*ds*ds : 0);
}

/* the move at which free margin reaches zero */
function squareOffDistance(bk, spot){
  if(!bk || !spot) return null;
  const H = bk.headroom;
  if(H===null || H===undefined) return null;
  const out = {};
  for(const dir of [1,-1]){
    let found=null;
    for(let pct=0.1; pct<=15; pct+=0.1){       // ponytail: 0.1% scan, closed form
      const ds = dir*spot*pct/100;             // is not worth it for a 150-step loop
      const pnl = bookPnl(bk, ds);
      if(pnl===null) return null;
      if(H + pnl <= 0){ found=pct; break; }
    }
    out[dir>0?'up':'down'] = found;
  }
  return out;
}


const rs0 = v => (v===null||v===undefined||Number.isNaN(v)) ? '\u2014'
  : (v<0?'\u2212':'') + '\u20b9' + Math.abs(Math.round(v)).toLocaleString('en-IN');

/* 1 ---- THE GATE ------------------------------------------------------- */
function renderGate(){
  const g = gateState();
  const el = $('gateLevel');
  setText(el, g.level);
  setClass(el, 'gate-'+g.level.replace(/ /g,''));
  setText($('gateReason'), g.reason);
  const holes = g.holes.length
    ? g.holes.map(h=>`<span class="hole">${esc(h)}</span>`).join('')
    : '';
  if($('gateHoles').innerHTML !== holes) $('gateHoles').innerHTML = holes;
  const extra = g.reasons.slice(1);
  setText($('gateMore'), extra.length ? extra.join(' \u00b7 ') : '');
}

/* 2 ---- SURVIVAL ------------------------------------------------------- */

/* margin at a shifted spot, straight from the server's own model */
function marginShift(){
  const p = S.paper && S.paper.desk;
  const m = p && p.margin_shift;
  if(!m) return {at:null, why:'margin_shift is payload me nahi hai'};
  const why = m.why || m.no_base_why || null;
  if(!m.at || m.base===null || m.base===undefined)
    return {at:null, why, model:m.model, note:m.note};
  // ponytail: the key shape is not observable while the book is flat, so try
  // the plausible spellings rather than guess one and render blanks tomorrow
  const lookup = pctMove => {
    if(pctMove === 0) return m.base;
    for(const k of [`${pctMove}%`, `${pctMove>0?'+':''}${pctMove}%`,
                    String(pctMove), `${pctMove>0?'+':''}${pctMove}`]){
      if(m.at[k]!==undefined && m.at[k]!==null) return m.at[k];
    }
    return null;
  };
  return {at:m.at, base:m.base, lookup, why, model:m.model, note:m.note,
          priced:m.positions_priced};
}

const GAPS = [-2,-1,0,1,2];
function renderSurvival(){
  const bk = activeBook();
  const d = deskIdx();
  const spot = d && d.regime && d.regime.spot;
  setText($('svLabel'), bk.src ? bk.label : '');
  setClass($('survival'), bk.src==='candidate' ? 'panel hypo' : 'panel');

  if(!bk.src){
    $('svBody').innerHTML = `<span class="abs none">${esc(bk.why)}</span>`;
    $('svBig').innerHTML = ''; return;
  }
  if(!spot){ $('svBody').innerHTML = absUnchecked('spot nahi \u2014 gap table nahi ban sakti');
    $('svBig').innerHTML=''; return; }

  const MS = marginShift();
  const cap = (S.paper && S.paper.desk && S.paper.desk.risk && S.paper.desk.risk.capital) || null;
  const rows = GAPS.map(p=>{
    const ds = spot*p/100;
    const pnl = bookPnl(bk, ds);
    // real shifted margin when the server can price it; else the old constant
    const mg = MS.at ? MS.lookup(p) : null;
    let free = null, marginSrc = 'const';
    if(mg!==null && cap!==null && pnl!==null){ free = cap - mg + pnl; marginSrc='shift'; }
    else if(bk.headroom!==null && bk.headroom!==undefined && pnl!==null) free = bk.headroom + pnl;
    return {p, ds, pnl, free, mg, marginSrc};
  });
  $('svBody').innerHTML =
    `<table class="t"><thead><tr><th>SPOT</th><th>MOVE</th><th>P&amp;L</th>
      <th>MARGIN</th><th>FREE MARGIN</th><th></th></tr></thead><tbody>` +
    rows.map(r=>{
      const bad = r.free!==null && r.free<=0;
      return `<tr class="${r.p===0?'now':''}${bad?' dead':''}">
        <td class="n">${px(spot + r.ds)}</td>
        <td class="n">${r.p>0?'+':''}${r.p}%</td>
        <td class="n ${r.pnl<0?'neg':'pos'}">${r.pnl===null?'\u2014':rs0(r.pnl)}</td>
        <td class="n ${r.marginSrc==='shift'?'':'quiet'}">${r.mg===null?'\u2014':rs0(r.mg)}</td>
        <td class="n">${r.free===null?'\u2014':rs0(r.free)}</td>
        <td class="quiet">${bad?'margin khatam':''}</td></tr>`;
    }).join('') + '</tbody></table>' +
    `<div class="quiet" style="margin-top:5px">P&amp;L = netΔ×move ${
      bk.netGamma?'+ ½·netΓ·move²':'(gamma nahi mila \u2014 curve seedhi maani gayi)'}${tagHTML('I')}
      \u00b7 ${rows.some(r=>r.marginSrc==='shift')
        ? 'free margin = capital \u2212 <b>us spot ka apna margin</b> + P&amp;L'
        : 'free margin = headroom + P&amp;L (margin constant maana \u2014 shifted margin abhi nahi mila)'}</div>` +
    (MS.note ? `<div class="cov-src"><i>${esc(MS.note)}</i></div>` : '') +
    (MS.model ? `<div class="cov-src"><i>${esc(MS.model)}</i></div>` : '') +
    (MS.why ? `<div style="margin-top:4px">${absUnchecked(MS.why)}</div>` : '');

  const so = squareOffDistance(bk, spot);
  const theta = dailyTheta();
  $('svBig').innerHTML =
    `<div class="big"><i>SQUARE-OFF DOORI</i>
       <b>${so && (so.up||so.down)
         ? `${so.down?'\u2212'+so.down.toFixed(1)+'%':'\u2014'} / ${so.up?'+'+so.up.toFixed(1)+'%':'\u2014'}`
         : '\u2014'}</b>
       <span class="q">${so && (so.up||so.down) ? 'itna hila to free margin zero'
         : 'is book pe \u00b115% tak margin zero nahi hota'}${tagHTML('I')}</span></div>
     <div class="big"><i>KITNE DIN KI KAMAI DAAO PE</i>
       <b>${theta.perDay ? (Math.abs(rows[0].pnl||0)/theta.perDay).toFixed(1)+' din' : '\u2014'}</b>
       <span class="q">${theta.perDay
         ? `worst-case \u00f7 rozana theta ${rs0(theta.perDay)}${tagHTML('I')}`
         : absUnchecked(theta.why)}</span></div>`;
}

/* the paper book logs fills and realised P&L but never a theta series, so a
   real "average daily income" needs history the API does not keep */
/* the server now models per-day theta from the book's own legs */
function dailyTheta(){
  const p = S.paper && S.paper.desk;
  if(!p) return {perDay:null, why:'paper desk nahi mila'};
  const t = p.theta_day_est;
  if(!t) return {perDay:null, why:'theta_day_est is payload me nahi hai'};
  if(t.rupees===null || t.rupees===undefined)
    return {perDay:null, legs:t.legs, method:t.method, tag:t.tag,
            why: t.why || t.no_legs_why || 'theta nikala nahi ja saka'};
  return {perDay:t.rupees, legs:t.legs, method:t.method, tag:t.tag};
}

/* 3 ---- AM I BEING PAID ------------------------------------------------- */
function renderPaid(){
  const x = ivVsRv();
  const el = $('paidRatio');
  if(x.ratio===null){
    setText(el, '\u2014'); setClass(el,'');
    $('paidVerdict').innerHTML = absUnchecked(x.why||'naapa nahi gaya');
  }else{
    setText(el, x.ratio.toFixed(2)+'\u00d7');
    const v = x.ratio>=1.3 ? 'PAID' : x.ratio>=1.1 ? 'PATLA' : 'STOP';
    setClass(el, 'paid-'+v);
    setText($('paidVerdict'), v==='PAID' ? 'PAID \u2014 bech sakte ho'
      : v==='PATLA' ? 'PATLA \u2014 aadhe size me' : 'STOP \u2014 vol saste, mat becho');
  }
  const R = x.R || {}, r5 = x.rv5;
  $('paidDetail').innerHTML =
    `<div class="kv"><i>ATM IV</i><b>${x.iv===null?'\u2014':pct(x.iv,2)}${tagHTML('M')}</b></div>
     <div class="kv"><i>RV \u00b7 5 session</i><b>${r5&&r5.rv!=null?pct(r5.rv,2):'\u2014'}${
       tagHTML(r5&&r5.tag||'M')} ${x.rvSrc==='rv5'?'<span class="used">ratio isi se</span>':''}</b></div>
     <div class="kv"><i>RV \u00b7 aaj tak</i><b>${x.rvToday===null?'\u2014':pct(x.rvToday,2)}${
       tagHTML('I')} ${x.rvSrc==='today'?'<span class="used">ratio isi se</span>':''}</b></div>
     <div class="kv"><i>base</i><b>${r5&&r5.sessions?`${r5.sessions} session \u00b7 ${r5.n_returns} returns`
       :(R.n?`${R.n} bars \u00b7 ${R.mins}m`:'\u2014')}</b></div>` +
    (x.rv5_why ? `<div style="margin-top:5px">${absUnchecked(x.rv5_why)}</div>` : '') +
    (r5 && r5.basis_note
      ? `<div class="basis-warn"><b>dhyan:</b> ${esc(r5.basis_note)}</div>`
      : '') +
    (r5 && r5.method ? `<div class="cov-src"><i>${esc(r5.method)}</i></div>` : '');

  // VEGA ATTACK: vol bid while spot stands still is the seller's ambush
  const sf = S.surface && S.surface.indices ? S.surface.indices[S.idx] : null;
  const ser = (sf && sf.day && sf.day.series) || [];
  const box = $('vegaAlert');
  if(ser.length < 6){ box.setAttribute('hidden',''); return; }
  const last = ser[ser.length-1], ref = ser[Math.max(0, ser.length-11)];
  const dIv = (last.a!=null && ref.a!=null) ? last.a-ref.a : null;
  const bars = (S.tape && S.tape.days && S.tape.days[0] && S.tape.days[0].bars) || [];
  let dSpot = null;
  if(bars.length>4){
    const c=bars.map(b=>b.fut&&b.fut.c).filter(Boolean);
    if(c.length>4) dSpot = Math.abs(c[c.length-1]-c[Math.max(0,c.length-11)])/c[c.length-1];
  }
  if(dIv!==null && dIv>0.004 && dSpot!==null && dSpot<0.002){
    box.removeAttribute('hidden');
    setText($('vegaTxt'), `VEGA ATTACK \u2014 spot khada hai (${(dSpot*100).toFixed(2)}%) par ATM IV ` +
      `+${(dIv*100).toFixed(2)} vol points chadh gaya. Short vega pe seedha vaar.`);
  }else box.setAttribute('hidden','');
}

/* 4 ---- WHERE AM I ------------------------------------------------------ */
function renderWhere(){
  const bk = activeBook(), d = deskIdx();
  const spot = d && d.regime && d.regime.spot;
  const em = d && d.regime && d.regime.expected_move;
  setText($('whLabel'), bk.src ? bk.label : '');
  if(!bk.src){ $('whBody').innerHTML = `<span class="abs none">${esc(bk.why)}</span>`; return; }
  const shorts = bk.legs.filter(l=>l.side==='SELL');
  if(!shorts.length){ $('whBody').innerHTML = absNone('koi short leg'); return; }
  if(!em) { $('whBody').innerHTML = absUnchecked('expected move nahi \u2014 sigma me doori nahi nikal sakte'); return; }
  $('whBody').innerHTML =
    `<table class="t"><thead><tr><th>STRIKE</th><th>DOORI</th><th>σ</th><th>DELTA</th><th></th></tr></thead><tbody>` +
    shorts.map(l=>{
      const dist = spot!=null ? Math.abs(l.strike-spot) : null;
      const sig = dist!==null ? dist/em : null;
      const ad = l.delta===null||l.delta===undefined ? null : Math.abs(l.delta);
      const lamp = ad===null ? 'na' : ad<0.20 ? 'g' : ad<=0.30 ? 'a' : 'r';
      return `<tr><td class="n">${px(l.strike)}${esc(l.right)}</td>
        <td class="n">${dist===null?'\u2014':num(dist,0)}</td>
        <td class="n">${sig===null?'\u2014':sig.toFixed(2)+'σ'}</td>
        <td class="n">${ad===null?'\u2014':num(ad,3)}</td>
        <td><span class="lamp l-${lamp}">${lamp==='g'?'safe':lamp==='a'?'dhyan':lamp==='r'?'khatra':'\u2014'}</span></td>
      </tr>`;}).join('') + '</tbody></table>' +
    `<div class="quiet" style="margin-top:4px">σ = front straddle ka expected move ${num(em,1)}${tagHTML('M')}
      \u00b7 lamp: &lt;0.20 safe, 0.20\u20130.30 dhyan, &gt;0.30 khatra</div>` +
    spreadRead(bk);
}

/* the operator POSTS. The spread is her revenue on entry, and a tax only if
   she has to cross. Two different sentences, never one. */
function spreadRead(bk){
  const withQ = bk.legs.filter(l=>l.bid!=null && l.ask!=null && l.ask>l.bid);
  if(!withQ.length) return `<div style="margin-top:5px">${absNone('bid/ask \u2014 spread ka hisaab')}</div>`;
  const lot = bk.lot || 1;
  return `<div class="spread"><i>EXECUTION</i>` + withQ.map(l=>{
    const sp = l.ask-l.bid, mid=(l.ask+l.bid)/2, pctSp = mid? sp/mid : null;
    const rev = sp*lot;
    const warn = pctSp!==null && pctSp>0.03;
    return `<div class="sp-row"><span class="n">${px(l.strike)}${esc(l.right)}</span>
      <span class="sp-post">post karke: revenue ${rs0(rev)}/lot</span>
      <span class="sp-cross${warn?' warn':''}">cross karna pade to: tax ${
        pctSp===null?'\u2014':(pctSp*100).toFixed(1)+'%'}${warn?' \u26a0 mehnga':''}</span></div>`;
  }).join('') + `<div class="quiet">spread entry pe kamai hai jab tum quote lagati ho; nuksan sirf tab jab cross karna pade</div></div>`;
}

/* 5 ---- MONEY GREEKS ---------------------------------------------------- */
function renderMoney(){
  const bk = activeBook();
  setText($('mgLabel'), bk.src ? bk.label : '');
  if(!bk.src){ $('mgBody').innerHTML = `<span class="abs none">${esc(bk.why)}</span>`;
    $('mgHoles').innerHTML=''; return; }
  const TH = dailyTheta();
  const d100 = bookPnl(bk, 100), d200 = bookPnl(bk, 200);
  const second = (d100!==null && d200!==null) ? d200-d100 : null;
  const vega2 = bk.netVega===null ? null : bk.netVega*2;
  $('mgBody').innerHTML =
    `<div class="mg"><i>spot +100</i><b class="${d100<0?'neg':'pos'}">${rs0(d100)}</b></div>
     <div class="mg"><i>IV +2 vol pts</i><b class="${vega2<0?'neg':'pos'}">${
       vega2===null?'\u2014':rs0(vega2)}</b></div>
     <div class="mg"><i>ek din nikal jaye</i><b class="${TH.perDay>=0?'pos':'neg'}">${
       TH.perDay===null?'\u2014':rs0(TH.perDay)}</b>
       <span class="q">${TH.perDay===null?esc(TH.why||''):`${TH.legs} legs${tagHTML(TH.tag||'I')}`}</span></div>
     <div class="mg wide"><i>agla 100 (gamma)</i><b class="${second<0?'neg':'pos'}">${
       second===null?'\u2014':rs0(second)}</b>
       <span class="q">${bk.netGamma
         ? 'pehle 100 se ' + (second!==null && d100!==null && Math.abs(second)>Math.abs(d100) ? 'zyada' : 'kam') + ' \u2014 yahi gamma hai'
         : 'gamma nahi mila, isliye dono 100 barabar dikh rahe \u2014 asliyat me nahi hote'}${tagHTML('I')}</span></div>`;
  $('mgHoles').innerHTML =
    (bk.netVega===null ? `<div>${absUnchecked('vega: legs pe vega nahi aaya')}</div>` : '') +
    (TH.method ? `<div class="cov-src"><i>${esc(TH.method)}</i></div>` : '') +
    `<div class="quiet">netΔ ${num(bk.netDelta,1)} \u00b7 netΓ ${bk.netGamma===null?'\u2014':num(bk.netGamma,3)}${tagHTML('I')}</div>`;
}

/* 6 ---- HISAAB ---------------------------------------------------------- */
function renderHisaab(){
  const p = S.paper && S.paper.desk;
  if(!p){ $('hsBody').innerHTML = absUnchecked('/api/paperdesk nahi mila'); return; }
  const cl = p.closed_today || [];
  // [I] split: this desk names premium-selling strategies SELL_*, adjustments BUY_*
  let sold=0, adj=0, soldN=0, adjN=0;
  for(const c of cl){
    if(/^SELL/.test(c.strategy||'')){ sold += c.realized||0; soldN++; }
    else { adj += c.realized||0; adjN++; }
  }
  const refusals = (p.decisions||[]).filter(x=>x.kind==='refusal').length;
  const Hh = hedgeOf();
  const nv = (Hh && Hh.per && Hh.per.net_variance!==undefined) ? Hh.per.net_variance : null;
  $('hsBody').innerHTML =
    `<div class="hs"><i>PREMIUM SE (SELL_*)</i><b class="${sold<0?'neg':'pos'}">${rs0(sold)}</b>
       <span class="q">${soldN} band hui</span></div>
     <div class="hs"><i>ADJUSTMENT KA KHARCHA</i><b class="${adj<0?'neg':'pos'}">${rs0(adj)}</b>
       <span class="q">${adjN} band hui</span></div>
     <div class="hs"><i>AAJ KA NET</i><b class="${p.day_pnl<0?'neg':'pos'}">${rs0(p.day_pnl)}</b></div>
     <div class="hs"><i>ASLI VARIANCE CAPTURE</i><b class="${nv!==null&&nv<0?'neg':'pos'}">${
       nv===null?'\u2014':rs0(nv)}</b>
       <span class="q">${nv===null?'hedge ledger idle':'theta \u2212 hedge bill'}${tagHTML('I')}</span></div>
     <div class="hs"><i>MANA KIYA</i><b>${refusals}</b>
       <span class="q">${refusals?'refusals hi product hain':'aaj koi refusal log nahi hua'}</span></div>`;
  $('hsNote').innerHTML =
    `<span class="quiet">theta vs adjustment ka batwara strategy ke naam se kiya gaya (SELL_* = premium)${tagHTML('I')}
     \u2014 API in dono ko alag se nahi ginti</span>` +
    (refusals===0 ? covReason('paper') : '');
}

function renderDesk(){
  renderGate();
  renderSurvival();
  renderPaid();
  renderWhere();
  renderMoney();
  renderHisaab();
  renderMachine();
}

/* the old headline, demoted: still exact, still logged, just not the lead */
function renderMachine(){
  const dk = S.desk;
  if(!dk || !dk.indices){
    $('acWhy').innerHTML = S.err.desk ? absUnchecked('/api/desk: '+S.err.desk) : absNone('desk answer yet');
    return;
  }
  const d = dk.indices[S.idx];
  if(!d){ $('acWhy').innerHTML = absUnchecked(`${S.idx} not in /api/desk`); return; }

  const v = d.view||{}, r = d.regime||{}, since = (SIG[S.idx]||{}).since || {};
  const dir = v.bias||'UNKNOWN';

  setClass($('answerCard'), dir==='BULL'?'bull':dir==='BEAR'?'bear':'');
  const huge=$('acHuge'); setText(huge, dir);
  setClass(huge, dir==='BULL'?'bull':dir==='BEAR'?'bear':'flat');

  $('dGear').innerHTML   = esc(v.gear||'UNKNOWN')+tagHTML(v.tag);
  $('dConv').innerHTML   = esc(v.conviction||'—');
  $('dRegime').innerHTML = esc(r.state||'—')+tagHTML(r.tag);
  $('dGame').innerHTML   = esc(d.game||v.game||'—');
  $('dTrapped').innerHTML= v.trapped_side ? esc(String(v.trapped_side).toUpperCase())+' writers' : absNone('trapped side');
  $('dWorst').innerHTML  = v.worst_leg ? esc(v.worst_leg) : '—';
  $('dFuel').innerHTML   = v.fuel_rank!==undefined&&v.fuel_rank!==null ? num(v.fuel_rank,3)+tagHTML('I') : '—';
  $('dEM').innerHTML     = r.expected_move!==undefined&&r.expected_move!==null
                            ? '±'+num(r.expected_move,1)+tagHTML(r.tag) : '—';

  setText($('dSince'), `${dir} — ${since.bias||'—'} se · ${ageStr(since.bias)}`);
  setText($('dExpiry'), `expiry ${d.expiry||'—'} · lot ${d.lot_size||'—'} (${d.lot_size_src||'?'})`);
  setText($('dCap'), `capital ₹${compact(dk.capital)} · fit ${d.fit_ok?'ok':'FAILED'} n=${d.fit_n??'—'} rmse ${num(d.fit_rmse,4)}`);

  // why: regime + view + desk, kept as the API wrote them
  const whys = [].concat(r.why||[], v.why||[], d.why||[]);
  const miss = (v.missing||[]);
  $('acWhy').innerHTML = whys.length
    ? `<ul class="why">${whys.map(w=>`<li>${esc(w)}</li>`).join('')}</ul>` +
      (miss.length ? `<div style="margin-top:5px">${absUnchecked('yeh nahi hai: '+miss.join(', '))}</div>` : '')
    : absNone('koi wajah batayi gayi');

  // the other two indices, compact -- present but never crammed into the answer
  const others = Object.keys(dk.indices).filter(k=>k!==S.idx);
  $('otherIdx').innerHTML = others.map(k=>{
    const o=dk.indices[k], ov=o.view||{};
    const ob=ov.bias||'UNKNOWN';
    const col = ob==='BULL'?'var(--bull)':ob==='BEAR'?'var(--bear)':'var(--flat)';
    const dep=(o.candidates||[]).filter(c=>c.status==='DEPLOYABLE').length;
    return `<div class="oi-card"><b>${esc(k)}</b>
      <div class="d" style="color:${col}">${esc(ob)}</div>
      <div class="q">${esc(ov.gear||'UNKNOWN')} · ${dep} lagane laayak</div></div>`;
  }).join('');

  renderStructures(d);
  renderStability();
  renderFlipLog();
}

/* Every candidate is openable, not just the deployable ones. Most of the book
   is BLOCKED, and "why is THIS one blocked" is a question a seller asks all
   day; burying 17 of 19 in a flat table answered it badly. DEPLOYABLE sorts
   first and opens itself; the rest stay shut until asked for. */
function renderStructures(d){
  // NOT sorted by status. The API's order is already a ranking, and re-sorting
  // on status made the whole list reshuffle every time one structure flipped
  // DEPLOYABLE->BLOCKED (which happens every few polls) -- 21 of 22 rows moved
  // under the cursor. Stable row identity beats "deployable first"; the
  // deployable ones announce themselves by colour, auto-open and the verdict.
  const cands = d.candidates||[];
  const dep = cands.filter(c=>c.status==='DEPLOYABLE');
  const blocked = cands.filter(c=>c.status==='BLOCKED').length;
  const aside = cands.filter(c=>c.status==='STAND_ASIDE').length;
  setText($('structCount'), `${dep.length} lagane laayak \u00b7 ${blocked} blocked \u00b7 ${aside} stand aside`);

  $('structVerdict').innerHTML = dep.length
    ? `<span style="color:var(--green);font-weight:700">${dep.length} structure lagane laayak</span>
       <span class="quiet"> \u2014 legs, margin aur wajah ke liye row kholo</span>`
    : `<div class="abs none" style="font-size:12px">sab ${cands.length} structures dekhe \u2014 ek bhi lagane laayak nahi</div>
       ${(d.why||[])[0] ? `<ul class="why" style="margin-top:6px"><li>${esc(d.why[0])}</li></ul>` : ''}`;

  // Open state lives in S.openStruct so a poll never snaps a drawer shut under
  // her hand. Edge ticks constantly and must NOT force a rebuild -- it is written in
  // place below. Only the set of names/statuses justifies new DOM.
  const sig = cands.map(c=>`${c.name}:${c.status}`).join('|');
  const body = $('structBody');
  if(body.dataset.sig !== sig){
    body.dataset.sig = sig;
    body.innerHTML = buildCands(cands);
  }
  for(const c of cands){
    const row = body.querySelector(`.cand[data-name="${CSS.escape(c.name)}"]`);
    if(!row) continue;
    setText(row.querySelector('.ce-edge'),
      (c.edge!==null&&c.edge!==undefined) ? 'edge ₹'+num(c.edge,2) : 'no edge');
  }
}

function buildCands(cands){
  return cands.map(c=>{
    const open = S.openStruct.has(c.name) || c.status==='DEPLOYABLE';
    const legs = (c.legs||[]).length
      ? `<table class="t"><thead><tr><th>STRIKE</th><th>SIDE</th><th>LTP</th><th>IV</th>
           <th>DELTA</th><th>OI</th><th>Z</th></tr></thead><tbody>` +
        c.legs.map(l=>`<tr><td class="n">${px(l.strike)}${esc(l.right||'')}</td>
          <td style="color:${l.side==='SELL'?'#7FD2CE':'#E0B96E'}">${esc(l.side)}</td>
          <td class="n">${num(l.ltp,2)}</td><td class="n">${pct(l.iv,2)}</td>
          <td class="n">${num(l.delta,3)}</td><td class="n">${oiC(l.oi)}</td>
          <td class="n">${num(l.z,2)}</td></tr>`).join('') + '</tbody></table>'
      : `<div style="margin-bottom:6px">${absNone('legs \u2014 banane ko kuch nahi')}</div>`;
    const cells = [
      ['RISK', c.risk||'\u2014'],
      ['MAX LOSS', c.max_loss!==null&&c.max_loss!==undefined ? '\u20b9'+num(c.max_loss,2) : absNone('tay max loss')],
      ['LOTS', c.lots!==null&&c.lots!==undefined ? String(c.lots) : '\u2014'],
      ['LOTS / CR', c.lots_per_cr??'\u2014'],
      ['MARGIN/LOT', c.margin_per_lot ? '\u20b9'+compact(c.margin_per_lot) : '\u2014'],
      ['BREAKEVEN', (c.breakevens||[]).map(b=>px(b)).join(' / ')||'\u2014'],
      ['NET DELTA', c.net_delta!==null&&c.net_delta!==undefined ? num(c.net_delta,4) : '\u2014'],
      ['THINNEST OI', oiC(c.thinnest_oi)]
    ];
    return `<div class="cand ${esc(c.status)}${open?' open':''}" data-name="${esc(c.name)}">
      <div class="ch">
        <span class="cn">${esc(c.name)}</span>
        <span class="ce-edge">${c.edge!==null&&c.edge!==undefined?'edge \u20b9'+num(c.edge,2):'no edge'}</span>
        <span class="cc">${esc(c.case||'')}</span>
        <span class="cs">${esc(c.status)}</span>
      </div>
      <div class="cb">
        ${legs}
        <div class="sgrid">${cells.map(([k,v])=>`<div class="kv"><i>${k}</i><b>${v}</b></div>`).join('')}</div>
        ${(c.why||[]).length
          ? `<ul class="why" style="margin-top:6px">${c.why.map(w=>`<li>${esc(w)}</li>`).join('')}</ul>` : ''}
        ${/* BLOCKED structures carry their blocker in `missing`, never in `why`
              -- that is the reasoning/absence split, and rendering only `why`
              made all 13 blocked rows say "no reason given" when the backend
              had in fact told us exactly what was absent. */''}
        ${(c.missing||[]).length
          ? `<div style="margin-top:6px">${c.missing.map(m=>
              `<div style="margin-bottom:3px">${absUnchecked(m)}</div>`).join('')}</div>` : ''}
        ${(!(c.why||[]).length && !(c.missing||[]).length)
          ? `<div style="margin-top:6px">${absNone('koi wajah')}</div>` : ''}
        ${c.hedge_note?`<div class="quiet" style="margin-top:4px">${esc(c.hedge_note)}</div>`:''}
        ${c.liquidity_note?`<div class="quiet">${esc(c.liquidity_note)}</div>`:''}
        <div class="quiet" style="margin-top:4px">${esc(c.margin_model||'')}</div>
      </div></div>`;
  }).join('');
}

/* one delegated listener, bound once -- survives every re-render */
document.addEventListener('click', e=>{
  const h = e.target.closest && e.target.closest('.cand > .ch');
  if(!h) return;
  const row = h.parentElement, name = row.dataset.name;
  if(row.classList.toggle('open')) S.openStruct.add(name); else S.openStruct.delete(name);
});

function renderStability(){
  const n = flipsLastHour(S.idx);
  setText($('stabCount'), `${n} in trailing 60 min`);
  const segs = $('stabBar').children;
  for(let i=0;i<segs.length;i++) setClass(segs[i], i<Math.min(n,5) ? 'on' : '');
  const note=$('stabNote');
  if(n>=3){
    setClass(note,'loud');
    setText(note, `UNSTABLE — is answer pe bharosa mat karo abhi (60 min me ${n} flips)`);
  }else if(n===2){
    setClass(note,''); note.style.color='var(--amber)';
    setText(note, 'badal raha hai — is ghante do flips, answer ko pakka mat maano');
  }else{
    setClass(note,''); note.style.color='var(--muted)';
    setText(note, n===1 ? 'sthir — is ghante ek flip' : 'sthir — is ghante koi flip nahi');
  }
  // flicker is counted, never hidden: a reader must be able to tell a quiet
  // tape from a noisy one that was merely debounced
  const tr = TRANS[S.idx]||0;
  const tn = $('stabTrans');
  if(tn){
    setText(tn, tr
      ? `+${tr} transient — ek hi 5s poll me aaya aur wapas chala gaya, flip nahi gina`
      : 'koi transient churn nahi — har badlaav do poll tak tika');
  }
}

function renderFlipLog(){
  const list = FLIPS[S.idx]||[];
  setText($('logMeta'), `aaj ${list.length}`);
  const host=$('flipLog');
  if(!list.length){ host.innerHTML = `<div class="pb">${absNone('aaj ka koi badlaav')}</div>`; return; }
  // keyed by ts+text so unchanged rows are never re-created
  const want = list.slice(0,150);
  const sigStr = want.map(f=>f.ts+f.text).join('|');
  if(host.dataset.sig === sigStr) return;
  host.dataset.sig = sigStr;
  host.innerHTML = want.map(f=>
    `<div class="flip ${esc(f.kind)}"><span class="t">${esc(f.ts)}</span><span class="m">${f.text}</span></div>`
  ).join('');
}

/* ==========================================================================
   WAR MAP -- the battlefield. Fronts advance and retreat, every wall carries
   its own intraday build, peaks are stamped with the time AND the price they
   happened at, the spot is the contested line, stop zones are minefields.
   ========================================================================== */
function wallFlow(k){
  const rows = S.flow[k];
  if(!rows || rows.length<2) return null;
  const ce = rows.map(r=>r.call), pe = rows.map(r=>r.put);
  const mk = (arr) => {
    let pi=0; for(let i=1;i<arr.length;i++) if(arr[i]>arr[pi]) pi=i;
    return {now:arr[arr.length-1], peak:arr[pi], peakRow:rows[pi], series:arr};
  };
  return {ce:mk(ce), pe:mk(pe), rows};
}


/* ==========================================================================
   ROUND 4 -- THE BATTLEFIELD ENGINE
   Six readings, all derived from endpoints already polled. Every estimate is
   [I] and names its method; every absence says which input is missing and why.
   ========================================================================== */

/* ---- the 4-state paint -------------------------------------------------
   OI alone is half the story. Joined with premium over the SAME window it
   separates the four things that actually happen at a strike. This is a
   CATEGORICAL axis with its own hues -- deliberately not the grey/amber/
   green/red state grammar, so the two can never be read as one another. */
const PAINT = {
  WRITE : {cls:'p-write', hi:'writers building \u2014 deewar chinai ho rahi hai'},
  BUY   : {cls:'p-buy',   hi:'buyers loading \u2014 kharidar ghus rahe hain'},
  COVER : {cls:'p-cover', hi:'SHORT COVERING \u2014 fuel jal raha hai'},
  LIQ   : {cls:'p-liq',   hi:'longs liquidating \u2014 kharidar nikal rahe hain'},
  FLAT  : {cls:'p-flat',  hi:'kuch khaas nahi hua'}
};
/* noise floors: a wall is not "building" because 0.3% of it twitched */
const OI_FLOOR = 0.01, PREM_FLOOR = 0.02;

function paintState(dOI, dPrem, baseOI, basePrem){
  if(dOI===null||dOI===undefined) return {st:null, why:'OI delta nahi'};
  if(dPrem===null||dPrem===undefined) return {st:null, why:'premium history nahi'};
  const oiMove   = baseOI   ? Math.abs(dOI)/Math.abs(baseOI)     : 0;
  const premMove = basePrem ? Math.abs(dPrem)/Math.abs(basePrem) : 0;
  if(oiMove < OI_FLOOR && premMove < PREM_FLOOR) return {st:'FLAT'};
  if(dOI > 0) return {st: dPrem < 0 ? 'WRITE' : 'BUY'};
  return {st: dPrem > 0 ? 'COVER' : 'LIQ'};
}

/* Premium per strike. /api/chain is the only source that covers EVERY strike
   and it is shut outside market hours, so the accumulator fills during the
   session and is persisted. The tape's own ATM strike is a second, always
   available source for exactly one strike. */
function premSeries(k, side){
  /* Priority: the server's own marks first. /api/oiflow now rides a `px` map on
     the SAME rows as the OI -- {"24200":[ce_level, pe_level]}, keys are STRINGS
     and the values are LEVELS, so the caller differences them. Same rows means
     same timestamps and one shared `backfill` tag for both axes. The client
     chain accumulator survives only as the fallback for strikes we never asked
     for by name, and loses to the server wherever they overlap. */
  const idx = side==='ce' ? 0 : 1;
  const rows = S.flow[k] || [];
  const srv = [];
  for(const r of rows){
    const cell = r.px && (r.px[String(k)] ?? r.px[k]);
    if(Array.isArray(cell) && cell[idx]!==null && cell[idx]!==undefined)
      srv.push({t:r.time, v:cell[idx]});
  }
  const acc = (S.prem && S.prem[k] || []).map(p=>({t:p.t, v:side==='ce'?p.ce:p.pe}))
    .filter(p=>p.v!==null && p.v!==undefined);
  if(srv.length && acc.length) return mergeByT(acc, srv, 't');   // server wins
  if(srv.length) return srv;
  if(acc.length>1) return acc;

  const tp = S.tape;
  if(tp && Number(tp.strike)===Number(k) && tp.days && tp.days[0]){
    const bars = tp.days[0].bars||[];
    return bars.filter(b=>b[side]).map(b=>({t:b.t, v:b[side].c}));
  }
  return null;
}
/* premium change over the same window the OI delta was taken across */
function premDelta(k, side, minsBack){
  const ser = premSeries(k, side);
  if(!ser || ser.length<2) return {d:null, base:null, why:'premium history nahi'};
  const lastT = hm2min(ser[ser.length-1].t);
  if(lastT===null) return {d:null, base:null, why:'premium timestamps padhe nahi gaye'};
  if(minsBack===null){                       // whole day
    return {d: ser[ser.length-1].v - ser[0].v, base: ser[0].v};
  }
  const target = lastT - minsBack;
  let ref=null;
  for(const p of ser){ const m=hm2min(p.t); if(m!==null && m<=target) ref=p; }
  if(!ref) return {d:null, base:null, why:`${minsBack}m peeche ka premium nahi`};
  return {d: ser[ser.length-1].v - ref.v, base: ref.v};
}

/* OI delta for a strike-side across a window, from the per-wall timelines */
function oiDelta(k, side, minsBack){
  const rows = S.flow[k];
  if(!rows || rows.length<2) return {d:null, base:null, why:'is strike ki OI timeline nahi'};
  const key = side==='ce' ? 'call' : 'put';
  const last = rows[rows.length-1];
  if(minsBack===null) return {d:(last[key]||0) - (rows[0][key]||0), base:Math.abs(last[key]||0)};
  const lastT = hm2min(last.time);
  if(lastT===null) return {d:null, base:null, why:'OI timestamps padhe nahi gaye'};
  let ref=null;
  for(const r of rows){ const m=hm2min(r.time); if(m!==null && m<=lastT-minsBack) ref=r; }
  if(!ref) return {d:null, base:null, why:`${minsBack}m peeche ki OI nahi`};
  return {d:(last[key]||0) - (ref[key]||0), base:Math.abs(last[key]||0), backfill:!!(last.backfill||ref.backfill)};
}

const WINDOWS = [{lbl:'5m', m:5}, {lbl:'15m', m:15}, {lbl:'day', m:null}];

function paintCells(k, side){
  return WINDOWS.map(w=>{
    const o = oiDelta(k, side, w.m);
    const p = premDelta(k, side, w.m);
    const r = paintState(o.d, p.d, o.base, p.base);
    return {w:w.lbl, st:r.st, why:r.why || (o.why||p.why), dOI:o.d, dPrem:p.d,
            backfill:o.backfill};
  });
}

/* ---- FUEL TANK ---------------------------------------------------------
   "kaun kitna phasa hai". The server already runs a volume-weighted basis
   ledger per contract (trapped_inventory.py): pain = price - basis, where
   basis is the VWAP premium of the OI it watched build this session. So
   pain x OI is trapped rupees directly, and runways.*.items carry the
   forward-looking version -- pain ADDED along the path to a target. We use
   the server's model rather than re-estimating entry premium worse. */
function fuelTank(m){
  if(!m) return null;
  const rw = m.runways||{}, heat = m.heat||[], spot = m.spot;
  const side = (r)=> r ? {
    fuel: r.fuel, target: r.target, dist: r.dist, perPoint: r.per_point,
    items: (r.items||[]).slice(0,5), stop: r.stop_zone, why: r.why
  } : null;
  // already-underwater, right now, from the ledger's pain
  let ceNow=0, peNow=0, painKnown=0;
  /* The ledger now says how much of each build it actually WATCHED. These are
     four different facts and stay four different sentences:
       session -> saw most of the build, full strength
       low     -> saw under half, the basis is a rough guess
       none    -> ledger was watching and saw NO build (an absence it observed)
       null    -> no ledger for this leg at all (never checked)
     Collapsing the last two into "0" would invent a measurement. */
  const conf = {session:0, low:0, none:0, missing:0};
  for(const h of heat){
    for(const sd of ['ce','pe']){
      const oi = h[sd+'_oi'];
      if(!oi) continue;
      const c = h[sd+'_conf'];
      if(c===undefined || c===null) conf.missing++;
      else if(c==='session' || c==='low' || c==='none') conf[c]++;
      else conf.missing++;
    }
    if(h.ce_pain){ ceNow += h.ce_pain*(h.ce_oi||0); painKnown++; }
    if(h.pe_pain){ peNow += h.pe_pain*(h.pe_oi||0); painKnown++; }
  }
  const graded = conf.session + conf.low;
  return {up:side(rw.up), down:side(rw.down), richer:rw.richer, spot,
          ceNow, peNow, painKnown, heatN:heat.length, note:rw.note, conf, graded};
}

/* ---- MIGRATION: did the front MOVE, or just shrink? --------------------
   An unwind at one strike paired with a build at a neighbour inside the same
   window is one army walking, not two events. */
function migrations(m, minsBack){
  const spot = m && m.spot, out=[];
  const ks = Object.keys(S.flow).map(Number).sort((a,b)=>a-b);
  if(ks.length<2) return out;
  const step = ks.length>1 ? Math.min(...ks.slice(1).map((k,i)=>Math.abs(k-ks[i]))) : 50;
  for(const side of ['ce','pe']){
    const d = ks.map(k=>({k, ...oiDelta(k, side, minsBack)})).filter(x=>x.d!==null);
    const outs = d.filter(x=>x.d < 0), ins = d.filter(x=>x.d > 0);
    for(const o of outs){
      let best=null;
      for(const i of ins){
        const gap = Math.abs(i.k-o.k);
        if(gap===0 || gap > step*2) continue;
        if(!best || gap < Math.abs(best.k-o.k)) best=i;
      }
      if(!best) continue;
      const size = Math.min(Math.abs(o.d), best.d);
      if(size <= 0) continue;
      const toward = spot!=null && Math.abs(best.k-spot) < Math.abs(o.k-spot);
      out.push({side, from:o.k, to:best.k, size, toward});
    }
  }
  return out.sort((a,b)=>b.size-a.size).slice(0,6);
}

/* ---- ACCELERATION: bhagdad, ya dheere-dheere adjustment? --------------- */
function acceleration(k, side){
  const rows = S.flow[k];
  if(!rows || rows.length<5) return null;
  const key = side==='ce' ? 'call' : 'put';
  const last = rows[rows.length-1], first = rows[0];
  const tLast = hm2min(last.time), tFirst = hm2min(first.time);
  if(tLast===null || tFirst===null || tLast<=tFirst) return null;
  const recent = oiDelta(k, side, 15);
  if(recent.d===null) return null;
  const dayRate15 = ((last[key]||0) - (first[key]||0)) / ((tLast-tFirst)/15);
  /* A near-zero day rate makes the ratio meaningless (917x is not a reading).
     A wall that sat flat all day and is only moving NOW is a different
     sentence, not a bigger number -- so say that sentence instead. */
  if(Math.abs(dayRate15) < Math.abs(recent.d)*0.05)
    return {recent:recent.d, dayRate15, ratio:null,
            note:'din bhar shaant tha, ab achanak chal raha hai'};
  return {recent:recent.d, dayRate15, ratio: recent.d/dayRate15};
}

/* ---- PAIN CURVE --------------------------------------------------------
   Not just max pain's minimum -- the whole expiry-payoff transfer curve.
   At terminal price K writers owe the intrinsic on every ITM contract:
     owed(K) = SUM_k ce_oi[k]*max(0, K-k) + SUM_k pe_oi[k]*max(0, k-K)
   The minimum is max pain; the GRADIENT at spot is the direction the book
   is being dragged. [I]: assumes today's OI is the expiry OI and that OI is
   writer-side symmetric -- it is a transfer estimate, not a forecast. */
function painCurve(m){
  const heat = (m && m.heat) || [];
  if(heat.length < 3) return null;
  const ks = heat.map(h=>h.k).sort((a,b)=>a-b);
  const lo = ks[0], hi = ks[ks.length-1];
  const N = 80, step = (hi-lo)/N;
  const pts = [];
  for(let i=0;i<=N;i++){
    const K = lo + i*step;
    let owed = 0;
    for(const h of heat){
      if(K > h.k) owed += (h.ce_oi||0) * (K - h.k);
      if(K < h.k) owed += (h.pe_oi||0) * (h.k - K);
    }
    pts.push({k:K, owed});
  }
  let min = pts[0];
  for(const p of pts) if(p.owed < min.owed) min = p;
  // gradient at spot: which way does the book want price to go
  const spot = m.spot;
  let grad = null;
  if(spot!=null){
    const h = step*2;
    const f = x => {
      let o=0; for(const q of heat){ if(x>q.k) o+=(q.ce_oi||0)*(x-q.k); if(x<q.k) o+=(q.pe_oi||0)*(q.k-x); }
      return o;
    };
    grad = (f(spot+h) - f(spot-h)) / (2*h);
  }
  return {pts, min, spot, grad, lo, hi};
}

/* ---- FUT PATTI: the second army --------------------------------------- */
const FUT_STATE = {
  LONG_BUILD : {hi:'long buildup \u2014 naye kharidar', cls:'p-buy'},
  SHORT_BUILD: {hi:'short buildup \u2014 naye sellers',  cls:'p-write'},
  LONG_UNWIND: {hi:'long unwinding \u2014 kharidar nikal rahe', cls:'p-liq'},
  SHORT_COVER: {hi:'SHORT COVERING \u2014 sellers bhaag rahe', cls:'p-cover'},
  FLAT       : {hi:'kuch khaas nahi', cls:'p-flat'}
};
function futState(dPx, dOI){
  if(dPx===null||dOI===null) return null;
  if(dPx===0 && dOI===0) return 'FLAT';
  if(dOI > 0) return dPx > 0 ? 'LONG_BUILD' : 'SHORT_BUILD';
  return dPx > 0 ? 'SHORT_COVER' : 'LONG_UNWIND';
}
function futPatti(){
  const tp = S.tape, day = tp && tp.days && tp.days[0];
  const bars = (day && day.bars) || [];
  if(bars.length < 3) return null;
  const iv = tp.interval || 3;
  const at = i => bars[Math.max(0, bars.length-1-i)];
  const last = bars[bars.length-1];
  const mk = (backBars, lbl) => {
    const ref = at(backBars);
    if(!ref || !ref.fut || !last.fut) return {lbl, st:null, why:'fut bars nahi'};
    const dPx = last.fut.c - ref.fut.c, dOI = last.fut.oi - ref.fut.oi;
    return {lbl, st:futState(dPx, dOI), dPx, dOI};
  };
  const firstFut = bars[0].fut;
  const dayCell = firstFut && last.fut
    ? {lbl:'day', st:futState(last.fut.c-firstFut.c, last.fut.oi-firstFut.oi),
       dPx:last.fut.c-firstFut.c, dOI:last.fut.oi-firstFut.oi}
    : {lbl:'day', st:null, why:'fut bars nahi'};
  return {cells:[mk(Math.round(5/iv)||1, `${iv*(Math.round(5/iv)||1)}m`),
                 mk(Math.round(15/iv)||1, `${iv*(Math.round(15/iv)||1)}m`), dayCell],
          px:last.fut.c, oi:last.fut.oi, oiSlope:last.fut.oi_slope, interval:iv};
}


/* ==========================================================================
   ROUND 4 renderers
   ========================================================================== */
const cr = v => (v===null||v===undefined) ? '\u2014' : '\u20b9'+(Math.abs(v)/1e7).toFixed(2)+' cr';

function paintCellHTML(c){
  // even a blank cell must admit when the half it DID get was reconstructed
  if(!c.st) return `<i class="pc p-none${c.backfill?' bf':''}" title="${esc(c.w)}: ${
    esc(c.why||'data nahi')}${c.backfill?' \u00b7 OI backfilled [I]':''}">\u00b7</i>`;
  const p = PAINT[c.st];
  const t = `${c.w}: ${p.hi} \u00b7 OI ${c.dOI>0?'+':''}${oiC(c.dOI)} \u00b7 premium ${
    c.dPrem>0?'+':''}${num(c.dPrem,2)}` + (c.backfill ? ' \u00b7 backfilled [I]' : '');
  return `<i class="pc ${p.cls}${c.backfill?' bf':''}" title="${esc(t)}">${esc(c.w[0])}</i>`;
}

/* ---- FUEL TANK ---- */
/* 96 empty squares with no explanation is the "wall of UNKNOWN" she rejected.
   The paint legend says once, plainly, which half of the story is missing and
   when it arrives -- so the blanks read as a stated absence, not a bug. */
function renderPaintNote(){
  const el = $('paintNote'); if(!el) return;
  const legend = `<span><i class="sw p-write"></i>writers</span>
    <span><i class="sw p-buy"></i>buyers</span>
    <span><i class="sw p-cover"></i>covering</span>
    <span><i class="sw p-liq"></i>liquidating</span>`;
  // count what actually has server marks vs what is still blank, and say why
  const tracked = Object.keys(S.flow||{});
  const withPx = tracked.filter(k=>(S.flow[k]||[]).some(r=>r.px && (r.px[String(k)]??r.px[k])));
  const ladderN = (S.warmap && S.warmap.indices && S.warmap.indices[S.idx]
    && (S.warmap.indices[S.idx].heat||[]).length) || 0;
  const blank = Math.max(0, ladderN - withPx.length);
  el.innerHTML = legend +
    (withPx.length
      ? `<span class="quiet">${withPx.length} strikes ka premium server ke apne marks se${tagHTML('M')}</span>`
      : '') +
    (blank
      ? `<span class="quiet">baaki ${blank} strikes khaali: premium sirf naam se maange gaye strikes
         par aata hai (<code>oiflow&amp;strikes=</code>), aur har poll pe utne hi maange jaate hain</span>`
      : '');
}

function renderFuelTank(m){
  const f = fuelTank(m);
  const host = $('ftBody');
  if(!f){ host.innerHTML = absNone('fuel ka hisaab (warmap heat nahi)'); return; }
  const line = (r, dir, hiWord) => {
    if(!r) return `<div class="ft-side"><i>${dir}</i>${absNone('is taraf runway')}</div>`;
    const items = (r.items||[]).map(i=>
      `<span class="ft-it">${px(i.k)}${esc(i.side||'')} <b>${cr(i.fuel)}</b></span>`).join('');
    return `<div class="ft-side ${r===f.up?'up':'down'}">
      <i>${dir}</i>
      <b class="ft-big">${cr(r.fuel)}</b>
      <span class="ft-tr">trigger ${r.target?esc(r.target.kind)+' '+px(r.target.px):'\u2014'}
        ${r.dist!=null?`\u00b7 ${num(r.dist,0)} pts door`:''}</span>
      <div class="ft-items">${items || absNone('fuel legs')}</div>
      ${r.stop?`<div class="ft-mine">\u26a0 barudi surang ${px(r.stop.lo)}\u2013${px(r.stop.hi)}</div>`:''}
    </div>`;
  };
  host.innerHTML = line(f.up,'UPAR \u2014 trapped CE shorts') + line(f.down,'NEECHE \u2014 trapped PE shorts');
  setText($('ftRicher'), f.richer ? `zyada fuel ${f.richer} taraf` : '');

  /* How much of this estimate the ledger actually watched being built. */
  const c = f.conf, bar = $('ftConf');
  if(bar){
    if(!f.heatN){ bar.innerHTML=''; }
    else if(c.session && !c.low && !c.none && !c.missing){
      bar.innerHTML = `<span class="cf cf-session">poora bharosa</span>
        <span class="quiet">${c.session} legs ka build ledger ne khud dekha${tagHTML('M')}</span>`;
    }else{
      bar.innerHTML =
        (c.session?`<span class="cf cf-session">${c.session} session</span>`:'') +
        (c.low?`<span class="cf cf-low">${c.low} low \u2014 aadha hi dekha hai, andaza kachcha</span>`:'') +
        (c.none?`<span class="cf cf-none">${c.none} pe ledger ne koi build nahi dekha \u2014 trapped ka andaza nahi (zero nahi)</span>`:'') +
        (c.missing?`<span class="cf cf-miss">${c.missing} legs ka ledger hi nahi \u2014 check nahi kar paye</span>`:'');
    }
  }
  $('ftMethod').innerHTML =
    `<div class="why"><b>Method [I]</b> \u2014 server ka volume-weighted basis ledger
      (trapped_inventory.py): har contract ka <i>basis</i> = us OI ka VWAP premium jo is session
      me banta dekha gaya; <i>pain</i> = price \u2212 basis. Runway ka <b>fuel</b> = OI \u00d7 pain
      jo target tak jaate hue <i>add</i> hoti hai \u2014 yaani "yahan tak gaya to kitna jalega",
      abhi ka nuksan nahi.</div>
     <div class="why">Abhi already underwater [I]: CE writers ${cr(f.ceNow)} \u00b7
       PE writers ${cr(f.peNow)} \u00b7 ${f.painKnown} strike-side pe ledger ka basis maujood
       (${f.heatN} strikes me se).</div>
     <ul class="why">
       <li>maani hui baat: exits proportional decay se nikalte hain \u2014 kaun sa lot band hua, dikhta nahi</li>
       <li>maani hui baat: sirf intraday build dikhta hai; overnight inventory ka basis invisible hai</li>
       <li>maani hui baat: ATM ke paas ka build writer-dominated hai</li>
       ${f.note?`<li>${esc(f.note)}</li>`:''}
     </ul>`;
}

/* ---- MIGRATION ---- */
function renderMigration(m){
  const host = $('migBody');
  const mig = migrations(m, 15);
  if(!mig.length){
    host.innerHTML = Object.keys(S.flow).length
      ? absNone('pichhle 15m me koi front sarakta hua')
      : absUnchecked('per-strike OI timelines abhi nahi aayi');
    drawMigrationArrows([]); return;
  }
  host.innerHTML = mig.map(x=>
    `<div class="mig ${x.toward?'press':'retreat'}">
       <span class="ms">${esc(x.side.toUpperCase())}</span>
       <span class="mk">${px(x.from)}</span>
       <span class="ma">\u2192</span>
       <span class="mk">${px(x.to)}</span>
       <b>${oiC(x.size)}</b>
       <span class="mw">${x.toward?'spot ki taraf \u2014 press kar rahe hain':'spot se door \u2014 peeche hat rahe hain'}</span>
     </div>`).join('');
  drawMigrationArrows(mig);
}

/* Arrows drawn over the ladder itself: the front WALKING is the picture.
   Row geometry is read live so the overlay cannot drift from the rows. */
function drawMigrationArrows(mig){
  const host = $('wmLadder'), svg = $('migLayer');
  if(!svg || !host) return;
  const hb = host.getBoundingClientRect();
  if(!mig.length || hb.height===0){ svg.innerHTML=''; return; }
  const yOf = k => {
    const row = host.querySelector(`.lrow[data-k="${k}"]`);
    if(!row) return null;
    const r = row.getBoundingClientRect();
    return r.top - hb.top + r.height/2;
  };
  svg.setAttribute('viewBox', `0 0 100 ${Math.round(hb.height)}`);
  svg.setAttribute('preserveAspectRatio','none');
  svg.style.height = hb.height+'px';
  const max = Math.max(...mig.map(x=>x.size), 1);
  svg.innerHTML = mig.map(x=>{
    const y1=yOf(x.from), y2=yOf(x.to);
    if(y1===null||y2===null) return '';
    const w = 1 + 2.5*(x.size/max);
    const col = x.toward ? '#FF8A2B' : '#7E8FA8';
    const bend = 24 + 10*(x.size/max);
    return `<path d="M50,${y1.toFixed(1)} Q${bend},${((y1+y2)/2).toFixed(1)} 50,${y2.toFixed(1)}"
      fill="none" stroke="${col}" stroke-width="${w.toFixed(1)}" opacity=".85"
      marker-end="url(#mgArrow)"></path>`;
  }).join('') +
  `<defs><marker id="mgArrow" markerWidth="6" markerHeight="6" refX="4" refY="3" orient="auto">
     <path d="M0,0 L6,3 L0,6 z" fill="#FF8A2B"></path></marker></defs>`;
}

/* ---- PAIN CURVE ---- */
function renderPainCurve(m){
  const host = $('pcChart'), pc = painCurve(m);
  if(!pc){ host.innerHTML = `<div class="pb">${absNone('pain curve (chain OI nahi)')}</div>`;
    $('pcLegend').innerHTML=''; return; }
  const W=600,H=150,L=8,R=8,T=10,B=20;
  const owed = pc.pts.map(p=>p.owed);
  const lo=Math.min(...owed), hi=Math.max(...owed);
  const sx = k => L + (k-pc.lo)/((pc.hi-pc.lo)||1)*(W-L-R);
  const sy = v => T + (1-(v-lo)/((hi-lo)||1))*(H-T-B);
  const d = pc.pts.map((p,i)=>`${i?'L':'M'}${sx(p.k).toFixed(1)},${sy(p.owed).toFixed(1)}`).join('');
  const spotX = pc.spot!=null ? sx(pc.spot) : null;
  host.innerHTML =
`<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">
  <path d="${d}" fill="none" stroke="#C9A227" stroke-width="1.8"></path>
  <line x1="${sx(pc.min.k).toFixed(1)}" y1="${T}" x2="${sx(pc.min.k).toFixed(1)}" y2="${H-B}"
    stroke="#C9A227" stroke-dasharray="3 3" stroke-width="1"></line>
  <text x="${sx(pc.min.k).toFixed(1)}" y="${T+9}" fill="#C9A227" font-size="9"
    text-anchor="middle" font-family="monospace">max pain ${px(Math.round(pc.min.k))}</text>
  ${spotX!==null?`<line x1="${spotX.toFixed(1)}" y1="${T}" x2="${spotX.toFixed(1)}" y2="${H-B}"
    stroke="#DCE5F2" stroke-width="1.6"></line>
    <text x="${spotX.toFixed(1)}" y="${H-B-4}" fill="#DCE5F2" font-size="9"
    text-anchor="middle" font-family="monospace">spot</text>`:''}
  <text x="${L}" y="${H-4}" fill="#63738C" font-size="9" font-family="monospace">${px(Math.round(pc.lo))}</text>
  <text x="${W-R}" y="${H-4}" fill="#63738C" font-size="9" text-anchor="end"
    font-family="monospace">${px(Math.round(pc.hi))}</text>
</svg>`;
  const pull = pc.grad===null ? null : (pc.grad > 0 ? 'NEECHE' : 'UPAR');
  $('pcLegend').innerHTML =
    `<span>max pain <b>${px(Math.round(pc.min.k))}</b> \u00b7 wahan writers <b>${cr(pc.min.owed)}</b> dete</span>
     <span>spot pe writers <b>${cr(pc.pts.reduce((a,p)=>Math.abs(p.k-(pc.spot??p.k))<Math.abs(a.k-(pc.spot??a.k))?p:a).owed)}</b> dete</span>
     ${pull?`<span>dhalaan <b>${pull}</b> ki taraf \u2014 book ko udhar kheenchne ka dabaav${tagHTML('I')}</span>`:''}
     <span class="quiet">expiry-transfer estimate: aaj ka OI hi expiry OI maana; writer-side symmetric. Forecast nahi.</span>`;
}

/* ---- FUT PATTI ---- */
function renderFutPatti(){
  const f = futPatti(), host = $('fpBody');
  if(!f){ host.innerHTML = absUnchecked('/api/data ke fut bars nahi'); setText($('fpMeta'),''); return; }
  setText($('fpMeta'), `${px(f.px)} \u00b7 OI ${oiC(f.oi)}`);
  host.innerHTML = f.cells.map(c=>{
    if(!c.st) return `<div class="fp-cell"><i>${esc(c.lbl)}</i>
      <span class="abs none">${esc(c.why||'data nahi')}</span></div>`;
    const st = FUT_STATE[c.st];
    return `<div class="fp-cell"><i>${esc(c.lbl)}</i>
      <b class="fp ${st.cls}">${esc(c.st.replace('_',' '))}</b>
      <span class="q">px ${c.dPx>0?'+':''}${num(c.dPx,1)} \u00b7 OI ${c.dOI>0?'+':''}${oiC(c.dOI)}</span>
      <span class="q">${esc(st.hi)}</span></div>`;
  }).join('') + `<div class="quiet" style="padding:4px 0 0">
    doosri fauj: options ki jung se alag${tagHTML('M')}</div>`;
}

/* ---- CAMPAIGN TIMELINE: the day, left to right ---- */
function renderCampaign(m){
  const host = $('cmpChart');
  const ks = Object.keys(S.flow).map(Number);
  if(!ks.length){ host.innerHTML = `<div class="pb">${absUnchecked('per-strike timelines nahi \u2014 campaign nahi bann sakti')}</div>`;
    setText($('cmpMeta'),''); return; }
  // one shared time axis across every wall we track
  const times = [...new Set([].concat(...ks.map(k=>(S.flow[k]||[]).map(r=>r.time))))]
    .filter(Boolean).sort((a,b)=>hm2min(a)-hm2min(b));
  if(times.length<2){ host.innerHTML = `<div class="pb">${absNone('kaafi time points')}</div>`; return; }
  const rows = ks.map(k=>{
    const heat=(m&&m.heat||[]).find(h=>h.k===k)||{};
    const ceDom=(heat.ce_oi||0)>=(heat.pe_oi||0);
    return {k, side: ceDom?'ce':'pe'};
  }).sort((a,b)=>b.k-a.k).slice(0,8);

  const W=900, RH=17, LW=62, T=26, H=T+rows.length*RH+34;
  const t0=hm2min(times[0]), t1=hm2min(times[times.length-1]);
  const sx = t => LW + ((hm2min(t)-t0)/((t1-t0)||1))*(W-LW-10);

  // per-cell interval deltas -> build/retreat bands
  let cells='';
  rows.forEach((row,ri)=>{
    const series=(S.flow[row.k]||[]);
    const key=row.side==='ce'?'call':'put';
    let mx=1;
    for(let i=1;i<series.length;i++) mx=Math.max(mx, Math.abs((series[i][key]||0)-(series[i-1][key]||0)));
    for(let i=1;i<series.length;i++){
      const d=(series[i][key]||0)-(series[i-1][key]||0);
      if(!d) continue;
      const x1=sx(series[i-1].time), x2=sx(series[i].time);
      const a=Math.min(1, Math.abs(d)/mx);
      const col=d>0 ? `rgba(84,188,182,${(0.15+0.75*a).toFixed(2)}）`.replace('）',')')
                    : `rgba(255,138,43,${(0.15+0.75*a).toFixed(2)})`;
      cells += `<rect x="${x1.toFixed(1)}" y="${(T+ri*RH+2).toFixed(1)}"
        width="${Math.max(1,(x2-x1)).toFixed(1)}" height="${RH-4}" fill="${col}"
        ${series[i].backfill?'stroke="#63738C" stroke-dasharray="2 2" stroke-width=".6"':''}>
        <title>${esc(series[i].time)} ${px(row.k)}${row.side.toUpperCase()} ${d>0?'+':''}${oiC(d)}${
          series[i].backfill?' (backfilled [I])':''}</title></rect>`;
    }
    cells += `<text x="4" y="${(T+ri*RH+RH/2+3).toFixed(1)}" fill="#93A3BC" font-size="9"
      font-family="monospace">${px(row.k)}${row.side.toUpperCase()}</text>`;
  });

  // spot across the top
  const anyRows = S.flow[ks[0]]||[];
  const sp = anyRows.filter(r=>r.ltp!=null);
  let spotPath='';
  if(sp.length>1){
    const lo=Math.min(...sp.map(r=>r.ltp)), hi=Math.max(...sp.map(r=>r.ltp));
    spotPath = sp.map((r,i)=>`${i?'L':'M'}${sx(r.time).toFixed(1)},${(4+(1-(r.ltp-lo)/((hi-lo)||1))*18).toFixed(1)}`).join('');
  }
  // event flags from the tape
  const evs = (S.tape && S.tape.days && S.tape.days[0] && S.tape.days[0].events) || [];
  const LOUD = /SQUEEZE|TRAP-SPRUNG|IGNITION|CLIMAX|BREAK|CAMPAIGN/;
  const flags = evs.filter(e=>LOUD.test(e.kind||'') && hm2min(e.t)>=t0 && hm2min(e.t)<=t1)
    .slice(0,40).map(e=>`<line x1="${sx(e.t).toFixed(1)}" y1="${T-4}" x2="${sx(e.t).toFixed(1)}"
      y2="${(T+rows.length*RH).toFixed(1)}" stroke="#E0A32E" stroke-width=".7" opacity=".5"></line>
      <circle cx="${sx(e.t).toFixed(1)}" cy="${T-6}" r="2.2" fill="#E0A32E">
        <title>${esc(e.t)} ${esc(e.kind)} \u2014 ${esc(e.msg||'')}</title></circle>`).join('');

  const ticks = times.filter((_,i)=>i%Math.ceil(times.length/8)===0).map(t=>
    `<text x="${sx(t).toFixed(1)}" y="${H-6}" fill="#63738C" font-size="9" text-anchor="middle"
      font-family="monospace">${esc(t)}</text>`).join('');

  host.innerHTML =
`<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">
  ${spotPath?`<path d="${spotPath}" fill="none" stroke="#DCE5F2" stroke-width="1.2" opacity=".9"></path>
  <text x="4" y="12" fill="#63738C" font-size="9" font-family="monospace">spot</text>`:''}
  ${flags}${cells}${ticks}
</svg>`;
  const flagged = evs.filter(e=>LOUD.test(e.kind||'') && hm2min(e.t)>=t0 && hm2min(e.t)<=t1).length;
  setText($('cmpMeta'), `${rows.length} deewarein \u00b7 ${times.length} slots \u00b7 ${flagged} bade events`);
}

function renderWar(){
  const w = S.warmap;
  const m = (w && w.indices) ? w.indices[S.idx] : null;
  if(!m || m.ok===false){
    // Every panel on this screen is downstream of the war map. Returning early
    // would leave them holding the LAST map's numbers with nothing saying so --
    // stale figures presented as current. Each one states the absence instead.
    const why = !w || !w.indices
      ? (S.err.warmap ? absUnchecked('/api/warmap: '+S.err.warmap) : absNone('war map'))
      : absUnchecked(`${S.idx}: ` + ((m && m.why) || 'is index ka war map server ne abhi banaya nahi'));
    const covWar = covReason('warmap');
    for(const id of ['wmLadder','ftBody','migBody','peakList','pcChart','cmpChart'])
      if($(id)) $(id).innerHTML = `<div class="pb">${why}${covWar}</div>`;
    for(const id of ['ftRicher','peakMeta','cmpMeta','pcLegend','ftMethod'])
      if($(id)) $(id).innerHTML = '';
    drawMigrationArrows([]);
    renderFutPatti();   // the futures strip is fed by /api/data, not the map
    return;
  }

  /* -- top strip -------------------------------------------------------- */
  const dr = m.driver||{};
  $('wDriver').innerHTML = esc(dr.lean||'—')+tagHTML(dr.tag);
  $('wDriver').style.color = dr.lean==='UNCLEAR' ? 'var(--muted)' : 'var(--amber)';
  setText($('wDriverWhy'), dr.why||'');

  const rw = m.runways||{};
  $('wRicher').innerHTML = rw.ok===false ? '—' : esc(rw.richer||'—');
  $('wRicher').style.color = rw.richer==='UP' ? 'var(--bull)' : rw.richer==='DOWN' ? 'var(--bear)' : 'var(--muted)';
  setText($('wRicherS'), rw.ok===false ? (rw.why||'nikala nahi gaya') : 'is taraf zyada majboori ki covering');

  $('wPain').innerHTML = px(m.max_pain);
  setText($('wFlip'), m.flip_px ? `gamma flip ${px(m.flip_px)}` : 'gamma flip: range me crossing nahi');

  const fired = m.seq_fired||[];
  setText($('wSeq'), fired.length ? String(fired.length) : '0');
  $('wSeq').style.color = fired.length ? 'var(--amber)' : 'var(--muted)';
  setText($('wSeqS'), fired.length ? fired.map(f=>f.kind||f).join(', ')
    : 'aaj koi level sequence poora nahi hua');

  /* -- siege clock ------------------------------------------------------ */
  const dw = m.dwell||{};
  const held = dw.held_s||0, frac = Math.min(1, held/DWELL_FULL);
  const C = 2*Math.PI*22;
  $('siegeArc').setAttribute('stroke-dashoffset', String(C*(1-frac)));
  $('siegeArc').setAttribute('stroke', dw.holding ? '#E0A32E' : '#1B2432');
  setText($('siegeSec'), dw.holding ? `${held}s` : '—');
  setClass($('siege'), dw.holding ? 'holding' : '');
  if(dw.holding && dw.level){
    setText($('siegeLevel'), `${dw.level.kind} ${px(dw.level.px)}`);
    $('siegeWhy').innerHTML = esc(dw.why||'')+tagHTML(dw.tag)+
      ` <span class="quiet">band ±${num(dw.band,2)}</span>`;
  }else{
    setText($('siegeLevel'), 'kisi level pe nahi ruka');
    $('siegeWhy').innerHTML = absNone('abhi kisi level pe dwell');
  }
  const ce=dw.oi_added_ce||0, pe=dw.oi_added_pe||0, tot=ce+pe;
  $('siegeCE').style.width = tot? (ce/tot*100).toFixed(1)+'%' : '0%';
  $('siegePE').style.width = tot? (pe/tot*100).toFixed(1)+'%' : '0%';
  setText($('siegeCEv'), 'CE '+oiC(ce));
  setText($('siegePEv'), 'PE '+oiC(pe));
  setText($('siegeShare'), dw.loaded_side
    ? `${String(dw.loaded_side).toUpperCase()} ${dw.side_share!==null?pct(dw.side_share):''}`
    : (tot? '' : 'kuch load nahi hua'));
  const bx = dw.buyers_crossing;
  $('siegeX').style.width = bx!==null&&bx!==undefined ? (bx*100).toFixed(0)+'%' : '0%';
  setText($('siegeXv'), bx!==null&&bx!==undefined ? pct(bx) : '—');

  /* -- runways ---------------------------------------------------------- */
  const maxFuel = Math.max(rw.up&&rw.up.fuel||0, rw.down&&rw.down.fuel||0, 1);
  const fillRunway = (side, node) => {
    const r = rw[side];
    const pre = side==='up' ? 'rwUp' : 'rwDn';
    if(!r){ setText($(pre+'T'),'—'); $(pre+'Why').innerHTML=absNone('runway'); return; }
    setText($(pre+'T'), r.target ? `${r.target.kind} ${px(r.target.px)}` : '—');
    setText($(pre+'D'), r.dist!==null&&r.dist!==undefined ? `${num(r.dist,1)} pts door` : '');
    $(pre+'Bar').style.width = ((r.fuel||0)/maxFuel*100).toFixed(1)+'%';
    $(pre+'Why').innerHTML = `${esc(r.why||'')}${tagHTML(r.tag)}
      <div class="quiet">fuel ${compact(r.fuel)} · ${compact(r.per_point)}/pt</div>`;
    // WHICH legs are the fuel -- an aggregate number cannot be acted on, a
    // named strike can: these are the writers who get squeezed on the way
    const items = (r.items||[]).slice(0,5);
    const mx = Math.max(...items.map(i=>i.fuel||0), 1);
    $(pre+'Items').innerHTML = items.length
      ? items.map(i=>`<div class="fi"><span class="fk">${px(i.k)}${esc(i.side||'')}</span>
          <span class="ft"><i style="width:${((i.fuel||0)/mx*100).toFixed(0)}%"></i></span>
          <span class="fv">${compact(i.fuel)}</span></div>`).join('')
      : absNone('is taraf fuel legs');
    const sz=r.stop_zone;
    $(pre+'Mine').innerHTML = sz ? `⚠ barudi surang ${px(sz.lo)}–${px(sz.hi)}${tagHTML(sz.tag)}`
                                 : absNone('stop zone');
    setClass(node, 'runway'+(rw.richer===side.toUpperCase()?' richer':''));
  };
  fillRunway('up', $('rwUp')); fillRunway('down', $('rwDn'));

  renderLadder(m);
  renderPeaks(m);
  renderBookFlow();
  renderPaintNote();
  renderFuelTank(m);
  renderMigration(m);
  renderPainCurve(m);
  renderFutPatti();
  renderCampaign(m);
}

/* Book-wide OI flow: the per-wall sparklines say what each front did, this
   says what the WHOLE book did and when it turned. Peak carries its time and
   the spot at that moment, same contract as the per-wall stamps. */
function renderBookFlow(){
  const bf = S.book;
  const host = $('bfChart');
  if(!bf || !Array.isArray(bf.rows) || !bf.rows.length){
    host.innerHTML = `<div class="pb">${S.err.oiflowbook
      ? absUnchecked('/api/oiflow: '+S.err.oiflowbook)
      : (bf && bf.chain_ok===false ? absUnchecked('chain: '+(bf.chain_why||'taiyaar nahi'))
                                   : absNone('book flow rows'))}</div>`;
    setText($('bfMeta'),''); $('bfLegend').innerHTML=''; return;
  }
  const rows = bf.rows.filter(r=>!r.baseline);
  if(!rows.length){ host.innerHTML=`<div class="pb">${absNone('non-baseline rows')}</div>`; return; }
  const pts = rows.map(r=>({t:r.time, v:r.diff}));
  const g = lineChart(host, pts, {color:'#5B9BD5', h:120, zero:0, fmt:v=>oiC(v)});
  const peak = rows.reduce((a,b)=>(b.diff!==null && (!a || b.diff>a.diff))?b:a, null);
  const trough = rows.reduce((a,b)=>(b.diff!==null && (!a || b.diff<a.diff))?b:a, null);
  const last = rows[rows.length-1];
  setText($('bfMeta'), `${rows.length} interval · ${bf.interval||5}m`);
  $('bfLegend').innerHTML =
    `<span>now <b>${esc(last.sentiment||'—')}</b> · diff ${oiC(last.diff)} · pcr ${num(last.pcr,2)}</span>
     ${peak?`<span>PE-heavy peak <b>${oiC(peak.diff)}</b> @${esc(peak.time)} · spot ${px(peak.ltp)}</span>`:''}
     ${trough?`<span>CE-heavy peak <b>${oiC(trough.diff)}</b> @${esc(trough.time)} · spot ${px(trough.ltp)}</span>`:''}
     ${g.gaps?`<span style="color:var(--amber)">${g.gaps} feed gap(s)</span>`:''}
     <span class="quiet">diff = put OI juda − call OI juda, poori chain${tagHTML('M')}</span>`;
}

/* map the sequence dict onto strike rows: a level that has been assaulted 16
   times and held is the single most useful thing on a battlefield */
function seqByPrice(m){
  const out=[];
  for(const key of Object.keys(m.sequence||{})){
    const s=m.sequence[key];
    if(s && s.px!==undefined) out.push(s);
  }
  return out;
}

function renderLadder(m){
  const heat = (m.heat||[]).slice().sort((a,b)=>b.k-a.k);   // high price on top
  const host = $('wmLadder');
  if(!heat.length){
    host.innerHTML = `<div class="pb">${absNone('heat map me strikes')}</div>`;
    return;
  }
  const spot = m.spot;
  const maxOI = Math.max(...heat.map(h=>Math.max(h.ce_oi||0, h.pe_oi||0)), 1);
  const levels = m.levels||[];
  const seqs = seqByPrice(m);
  const rw = m.runways||{};
  const mines = [rw.up&&rw.up.stop_zone, rw.down&&rw.down.stop_zone].filter(Boolean);

  // step between strikes, to decide which chips/levels belong to which row
  const step = heat.length>1 ? Math.abs(heat[0].k-heat[1].k) : 50;

  const rowsWanted = [];
  let spotPlaced = false;
  for(const h of heat){
    if(!spotPlaced && spot!==undefined && spot!==null && h.k < spot){
      rowsWanted.push({spotRow:true, k:'spot'});
      spotPlaced = true;
    }
    rowsWanted.push({k:h.k, h});
  }
  if(!spotPlaced) rowsWanted.push({spotRow:true, k:'spot'});

  // diff by key: reuse rows, never rebuild the ladder wholesale
  const have = new Map();
  for(const el of Array.from(host.children)) have.set(el.dataset.k, el);
  const frag = document.createDocumentFragment();

  for(const rwn of rowsWanted){
    const key = String(rwn.k);
    let el = have.get(key);
    if(rwn.spotRow){
      if(!el){ el=document.createElement('div'); el.dataset.k=key; el.className='spotrow';
        el.innerHTML='<div class="sl"></div><div class="sp"></div>'; }
      const sp=el.querySelector('.sp');
      setText(sp, `SPOT ${px(spot)}`);
      have.delete(key); frag.appendChild(el); continue;
    }
    const h = rwn.h;
    if(!el){
      el=document.createElement('div'); el.dataset.k=key;
      el.innerHTML =
        `<div class="lc ce"><span class="paint"></span><span class="chg"></span>
           <span class="bar"></span>
           <span class="peak" style="display:none"></span><span class="num"></span></div>
         <div class="lk"><span class="kpx"></span><span class="dist"></span>
           <span class="chips"></span><span class="seq"></span><span class="accel"></span></div>
         <div class="lc pe"><span class="bar"></span><span class="peak" style="display:none"></span>
           <span class="num"></span><span class="chg"></span><span class="paint"></span></div>
         <div class="lspark"></div>`;
    }
    have.delete(key);

    const near = spot!==null && Math.abs(h.k-spot) <= step*1.5;
    const myLevels = levels.filter(l=>Math.abs(l.px-h.k) < step/2);
    const isWall = myLevels.some(l=>l.kind==='CE_WALL'||l.kind==='PE_WALL');
    const inMine = mines.some(z=>h.k>=z.lo-step/2 && h.k<=z.hi+step/2);
    setClass(el, 'lrow'+(inMine?' mine':'')+(isWall?' wall':'')+(near?' near':''));

    const flow = wallFlow(h.k);

    // CE front (left) and PE front (right)
    const sides=[['ce', h.ce_oi, h.ce_chg, flow&&flow.ce], ['pe', h.pe_oi, h.pe_chg, flow&&flow.pe]];
    for(const [side, oi, chg, f] of sides){
      const c = el.querySelector('.lc.'+side);
      const bar = c.querySelector('.bar');
      const wPct = Math.min(100, (oi||0)/maxOI*100);
      if(bar.style.width !== wPct.toFixed(1)+'%') bar.style.width = wPct.toFixed(1)+'%';
      setText(c.querySelector('.num'), oiC(oi));

      // the high-water mark this front has fallen back from.
      // peakAbs = current absolute OI + everything unwound since the peak.
      const pk = c.querySelector('.peak');
      if(f && f.peak > f.now){
        const peakAbs = (oi||0) + (f.peak - f.now);
        const pPct = Math.min(100, peakAbs/maxOI*100);
        pk.style.display='block';
        pk.style[side==='ce'?'right':'left'] = 'auto';
        pk.style[side==='ce'?'left':'right'] = `calc(${(100-pPct).toFixed(1)}% - 1px)`;
        pk.title = `peak ${oiC(peakAbs)} at ${f.peakRow.time} · spot ${px(f.peakRow.ltp)}`;
      }else if(pk.style.display!=='none'){ pk.style.display='none'; }

      const cg = c.querySelector('.chg');
      setText(cg, chg ? (chg>0?'+':'−')+oiC(Math.abs(chg)) : '·');
      setClass(cg, 'chg '+(chg>0?'up':chg<0?'dn':'flat'));

      // 4-state paint: OI joined with premium over the same window
      const pnt = c.querySelector('.paint');
      const html = paintCells(h.k, side).map(paintCellHTML).join('');
      if(pnt.innerHTML !== html) pnt.innerHTML = html;
    }

    setText(el.querySelector('.kpx'), px(h.k));
    // how far this front sits from the contested line, in points
    const dd = (spot!==null && spot!==undefined && !Number.isNaN(spot)) ? (h.k-spot) : null;
    setText(el.querySelector('.dist'), dd===null ? '' : (dd>0?'+':'')+dd.toFixed(0));
    const chips = myLevels
      .filter(l=>l.kind!=='ROUND' || l.major)
      .map(l=>`<span class="chip ${esc(l.kind)}" title="${esc(l.label||'')}">${esc(l.kind.replace('_',' '))}</span>`)
      .join('');
    const chipEl = el.querySelector('.chips');
    if(chipEl.innerHTML !== chips) chipEl.innerHTML = chips;

    // acceleration: bhagdad vs adjustment
    const acEl = el.querySelector('.accel');
    const domSide = (h.ce_oi||0) >= (h.pe_oi||0) ? 'ce' : 'pe';
    const ac = acceleration(h.k, domSide);
    if(ac && (ac.note || Math.abs(ac.ratio) >= 2)){
      const r = ac.ratio===null ? null : Math.min(Math.abs(ac.ratio), 20);
      setText(acEl, ac.ratio===null ? 'NEW'
        : (r>=20 ? '20×+' : r.toFixed(1)+'×'));
      acEl.title = ac.note
        ? `${ac.note} — pichhle 15m me ${oiC(ac.recent)} [I]`
        : `${ac.recent<0?'utarna':'banna'} TEZ ho raha hai — pichhle 15m me ` +
          `${oiC(ac.recent)}, din ki 15m raftaar ${oiC(ac.dayRate15)} [I]`;
      setClass(acEl, 'accel on'+(ac.recent<0?' down':''));
    }else{ setText(acEl,''); setClass(acEl,'accel'); }

    const sq = seqs.find(s=>Math.abs(s.px-h.k) < step/2);
    const sqEl = el.querySelector('.seq');
    if(sq && sq.tests){
      setText(sqEl, `${sq.state} ×${sq.tests}${sq.last_outcome?' '+sq.last_outcome:''}`);
      setClass(sqEl, 'seq '+esc(sq.state));
    }else{ setText(sqEl,''); setClass(sqEl,'seq'); }

    // per-wall intraday build -- the time dimension she asked for
    const spEl = el.querySelector('.lspark');
    if(flow){
      const dom = (h.ce_oi||0) >= (h.pe_oi||0) ? flow.ce : flow.pe;
      const col = (h.ce_oi||0) >= (h.pe_oi||0) ? '#E0864A' : '#5B9BD5';
      const html = spark(dom.series, 90, 18, col);
      if(spEl.innerHTML !== html) spEl.innerHTML = html;
      spEl.title = `peak ${oiC(dom.peak)} at ${dom.peakRow.time}, spot ${px(dom.peakRow.ltp)}`;
    }else if(spEl.innerHTML !== ''){ spEl.innerHTML=''; }

    frag.appendChild(el);
  }
  for(const [,el] of have) el.remove();
  host.appendChild(frag);
}

/* the fronts board: which walls are advancing, which are in retreat, and the
   peak stamped with time AND the price it happened at */
function renderPeaks(m){
  const host=$('peakList');
  const ks = Object.keys(S.flow).map(Number).sort((a,b)=>b-a);
  if(!ks.length){
    setText($('peakMeta'), '');
    host.innerHTML = `<div class="pb">${S.flowIdx===S.idx
      ? absUnchecked('per-strike OI timeline abhi load nahi hui')
      : absNone('is index ki timelines')}</div>`;
    return;
  }
  setText($('peakMeta'), `${ks.length} par nazar · 5-min`);
  const heat = m.heat||[];
  const rows = ks.map(k=>{
    const f = wallFlow(k); if(!f) return '';
    const h = heat.find(x=>x.k===k)||{};
    const ceDom = (h.ce_oi||0) >= (h.pe_oi||0);
    const s = ceDom ? f.ce : f.pe;
    const side = ceDom ? 'CE' : 'PE';
    /* `call`/`put` are OI added SINCE THE OPEN, so they can go negative when a
       strike unwinds past where it started. Then "% off peak" blows past 100
       and "added" reads as a negative addition -- both nonsense on screen.
       Below zero is its own state and gets its own sentence. */
    const retreat = s.peak - s.now;
    const rp = s.peak > 0 ? Math.min(1, retreat/s.peak) : null;
    const state = s.now < 0
      ? `<span class="rt">POORI UTAR GAYI — ab subah se bhi ${oiC(Math.abs(s.now))} neeche</span>`
      : (rp !== null && rp > 0.03)
        ? `<span class="rt">DEEWAR UTAR RAHI HAI −${oiC(retreat)} (peak se ${pct(rp,0)} neeche)</span>`
        : `<span class="ad">DEEWAR TIKI HAI — peak ke paas</span>`;
    const nowLine = s.now < 0
      ? `abhi ${oiC(Math.abs(s.now))} — subah se ghata`
      : `abhi ${oiC(s.now)} — subah se juda`;
    // per-wall: how much of THIS leg's build the ledger watched
    const cv = h[(ceDom?'ce':'pe')+'_conf'];
    const cf = cv==='session' ? `<span class="cf cf-session">session</span>`
      : cv==='low' ? `<span class="cf cf-low">low — aadha dekha</span>`
      : cv==='none' ? `<span class="cf cf-none">build nahi dekha</span>`
      : `<span class="cf cf-miss">ledger nahi</span>`;
    return `<div class="pk">
      <div class="k">${px(k)}<div class="quiet">${side}</div>${cf}</div>
      <div class="d">${state}
        <div>peak ${oiC(s.peak)} @ <b>${esc(s.peakRow.time)}</b> · spot ${px(s.peakRow.ltp)}</div>
        <div class="quiet">${nowLine}${tagHTML('M')}</div>
      </div></div>`;
  }).join('');
  if(host.innerHTML !== rows) host.innerHTML = rows;
}

/* which strikes deserve their own timeline: the walls plus everything near
   spot. Capped -- one HTTP call per strike, refreshed on a slow clock. */
function flowStrikes(m){
  if(!m) return [];
  const want = new Set();
  for(const l of (m.levels||[])) if(l.kind==='CE_WALL'||l.kind==='PE_WALL'||l.kind==='MAX_PAIN') want.add(Math.round(l.px));
  const heat=(m.heat||[]).slice().sort((a,b)=>Math.abs(a.k-m.spot)-Math.abs(b.k-m.spot));
  for(const h of heat.slice(0,6)) want.add(h.k);
  const byOI=(m.heat||[]).slice().sort((a,b)=>Math.max(b.ce_oi,b.pe_oi)-Math.max(a.ce_oi,a.pe_oi));
  for(const h of byOI.slice(0,4)) want.add(h.k);
  // every strike the ladder draws: each named request now returns premium too
  // (rows carry `px`), so the cap directly bounds how much of the 4-state
  // paint can resolve. 18 x one small request per minute is nothing locally.
  for(const h of (m.heat||[])) want.add(h.k);
  return [...want].slice(0,18);
}

async function refreshFlow(force){
  const m = S.warmap && S.warmap.indices ? S.warmap.indices[S.idx] : null;
  if(!m) return;
  if(!force && S.flowIdx===S.idx && Date.now()-S.flowAt < FLOW_MS) return;
  const ks = flowStrikes(m);
  if(!ks.length) return;
  if(S.flowIdx !== S.idx){ S.flow={}; S.flowIdx=S.idx; }
  S.flowAt = Date.now();
  // ponytail: one request per strike (the endpoint SUMS a multi-strike list,
  // so it cannot return them separately). 12 calls a minute on localhost is
  // nothing; if it ever matters, ask the backend for a per-strike mode.
  for(const k of ks){
    const j = await getJSON(`/api/oiflow?idx=${encodeURIComponent(S.idx)}&interval=5&strikes=${k}`, 'oiflow');
    // server wins on overlap; the remembered rows cover what a restart lost,
    // which is what keeps a wall's morning build and its peak stamp alive
    if(j && j.ok && Array.isArray(j.rows)) S.flow[k] = mergeByT(S.flow[k], j.rows, 'time');
  }
  saveLS('flow', S.flow, S.idx);
  if(S.screen==='war') renderWar();
}

/* ==========================================================================
   TAPE -- toxicity, the read, and what the tape actually did
   ========================================================================== */
function renderTape(){
  /* VPIN ---------------------------------------------------------------- */
  const sn = S.senses;
  const vp = sn && sn.vpin ? sn.vpin[S.idx+'-FUT'] : null;
  const pctEl=$('vpPct'), bar=$('vpBar');

  if(!sn){
    pctEl.innerHTML = '—<small>check nahi kar paye</small>';
    $('vpPills').innerHTML = absUnchecked('/api/senses: '+(S.err.senses||'no response'));
    bar.style.width='0%';
  }else if(!vp){
    pctEl.innerHTML = '—<small>naapa nahi gaya</small>';
    $('vpPills').innerHTML = absNone(`${S.idx}-FUT ki VPIN series (sirf NIFTY-FUT pe lagi hai)`);
    bar.style.width='0%';
  }else if(vp.pct===null || vp.vpin===null){
    // warmup is NOT "no data" -- it is "not yet", and it has a progress number
    pctEl.innerHTML = `—<small>garam ho raha hai</small>`;
    bar.style.width='0%';
    $('vpPills').innerHTML =
      `<span class="pill amber">GARAM HO RAHA — ${vp.buckets}/10 buckets</span>` +
      `<span class="pill">bucket fill ${pct(vp.fill,1)}</span>` +
      `<span class="pill">bucket ${compact(vp.bucket_v)} contracts</span>` +
      `<span class="pill grey">shadow${vp.tag?' '+esc(vp.tag):''}</span>` +
      `<div style="width:100%;margin-top:4px">${absUnchecked('percentile banne se pehle 10 volume buckets chahiye')}</div>`;
  }else{
    pctEl.innerHTML = `${(vp.pct*100).toFixed(0)}<small>pct of day</small>`;
    bar.style.width = Math.min(100, vp.pct*100).toFixed(0)+'%';
    setClass(bar, vp.pct>=0.8 ? 'hot' : '');
    $('vpPills').innerHTML =
      `<span class="pill ${vp.pct>=0.8?'amber':''}">VPIN ${num(vp.vpin,4)}</span>` +
      `<span class="pill">${vp.buckets} buckets</span>` +
      `<span class="pill">fill ${pct(vp.fill,1)}</span>` +
      `<span class="pill grey">shadow ${esc(vp.tag||'')}</span>`;
  }

  // Plain-language interpretation strip for VPIN state
  const vr = $('vpRead');
  if(vr){
    if(!sn || !vp){
      vr.style.display = 'none';
    }else if(vp.pct===null || vp.vpin===null){
      vr.style.display = 'block';
      vr.className = 'vr-quiet';
      vr.innerHTML =
        `<div class="vr-head">WARMUP PHASE (${vp.buckets||0}/10 buckets)</div>` +
        `<div class="vr-body">VPIN percentile calculate karne ke liye kam se kam 10 volume buckets (60,000 contracts each) chahiye. Market open ke 20-30 min baad percentile active hota hai.</div>`;
    }else{
      vr.style.display = 'block';
      const p = vp.pct;
      if(p >= 0.80){
        vr.className = 'vr-hot';
        vr.innerHTML =
          `<div class="vr-head">⚠️ DANGER: HIGH TOXICITY / FLOW ZEHER (${(p*100).toFixed(0)}% of day)</div>` +
          `<div class="vr-body"><b>One-sided aggressive flow:</b> Market makers bleed kar rahe hain. Volatility / range breakout aane ke high chances hain. <b>Desk Gate rule:</b> NO NEW RISK.</div>` +
          `<div class="vr-note">Aaj ke saare VPIN readings me se ${(p*100).toFixed(0)}% readings isse kam the.</div>`;
      }else if(p >= 0.65){
        vr.className = 'vr-elevated';
        vr.innerHTML =
          `<div class="vr-head">ELEVATED IMBALANCE (${(p*100).toFixed(0)}% of day)</div>` +
          `<div class="vr-body">Imbalance badh raha hai. Informed aggressive flow book ko pressure me laa raha hai. Tight stoploss aur low size rakhna chahiye.</div>`;
      }else if(p <= 0.35){
        vr.className = 'vr-quiet';
        vr.innerHTML =
          `<div class="vr-head">CALM / TWO-SIDED FLOW (${(p*100).toFixed(0)}% of day)</div>` +
          `<div class="vr-body"><b>Balanced order flow:</b> Buyers aur sellers spread provide kar rahe hain. Market maker comfortable hain (Pin / Range-bound / Option selling favorable).</div>`;
      }else{
        vr.className = 'vr-normal';
        vr.innerHTML =
          `<div class="vr-head">NORMAL FLOW (${(p*100).toFixed(0)}% of day)</div>` +
          `<div class="vr-body">Ordinary trading conditions. Flow me koi abnormal toxicity ya aggressive selection nahi hai.</div>`;
      }
    }
  }

  // accumulation + server reconciliation both live in syncVpinDay(); this
  // function only draws what is already merged and persisted
  const g = lineChart($('vpChart'), S.vpinDay, {
    color:'#E0A32E', h:130, lo:0, hi:1, fmt:v=>(v*100).toFixed(0)+'%',
    empty: (vp && vp.pct===null)
      ? absUnchecked('VPIN dobara garam ho raha hai — abhi plot karne ko percentile nahi')
      : absNone('VPIN percentile points')
  });
  $('vpLegend').innerHTML =
    `<span>percentile of day · <b>${S.vpinDay.length}</b> pts · source <b>${S.vpinSrc}</b></span>` +
    (g.gaps ? `<span style="color:var(--amber)">${g.gaps} feed gap — line todi hai, jodi nahi</span>` : '') +
    `<span class="quiet">server ka log jeetta hai jahan overlap ho; browser sirf wahi bharta hai jo server ke paas nahi</span>` +
    // the vpin endpoint states its own gap position; that sentence is the truth
    (S.vpinsrv && S.vpinsrv.why ? `<span class="cov-src"><i>${esc(S.vpinsrv.why)}</i></span>` : '') +
    covReason('vpin');

  /* the read ------------------------------------------------------------ */
  const tp = S.tape, day = tp && tp.days && tp.days[0];
  const bars = day && day.bars || [];
  const lastBar = bars[bars.length-1];
  const ctx = lastBar && lastBar.ctx;
  setText($('tpMeta'), tp ? `${tp.index} · ${bars.length} bars · ${tp.interval}m` : '');

  if(!tp){
    $('tpRead').innerHTML = S.err.data ? absUnchecked('/api/data: '+S.err.data) : absNone('tape');
  }else if(!ctx){
    $('tpRead').innerHTML = absNone('aakhri bar pe context');
  }else{
    const vcol = ctx.verdict==='CAUTION' ? 'var(--grey)' : 'var(--amber)';
    $('tpRead').innerHTML =
      `<div style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap">
         <b style="font-size:15px;letter-spacing:1.5px;color:${vcol}">${esc(ctx.verdict||'—')}</b>
         <span class="quiet">${esc(ctx.vwhy||'')}</span>
         <span class="pill ${/BULL/.test(ctx.breadth||'')?'bull':/BEAR/.test(ctx.breadth||'')?'bear':''}">${esc(ctx.breadth||'')}</span>
       </div>
       <div class="quiet" style="margin-top:6px;font-family:var(--mono)">${esc(ctx.line||'')}</div>
       ${ctx.episode?`<div style="margin-top:6px;color:var(--amber)">${esc(ctx.episode)}</div>`:''}
       <div style="margin-top:6px" class="why">${esc(ctx.loc||'')}</div>
       ${(ctx.plays||[]).length?`<ul class="why" style="margin-top:4px">${ctx.plays.map(p=>`<li>${esc(p)}</li>`).join('')}</ul>`:''}
       <div class="pillrow" style="padding:8px 0 0">
         ${(ctx.flips||[]).map(f=>`<span class="pill amber">${esc(f)}</span>`).join('') || `<span class="quiet">${absNone('is bar pe flips')}</span>`}
       </div>`;
  }

  const setup = lastBar && lastBar.setup;
  $('tpSetup').innerHTML = setup
    ? `<div style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap">
         <b style="font-size:14px;letter-spacing:1.5px;color:var(--amber)">${esc(setup.kind||'')} ${esc(setup.dir||'')}</b>
         <span class="pill amber">${esc(setup.status||'')}</span>
         <span class="quiet">from ${esc(setup.t0||'')}</span>
       </div>
       <div class="sgrid" style="margin-top:8px">
         <div class="kv"><i>LEVEL</i><b>${esc(setup.level_name||'')} ${px(setup.level_px)}</b></div>
         <div class="kv"><i>INTENSITY</i><b>${num(setup.intensity,2)}${tagHTML('I')}</b></div>
         <div class="kv"><i>COMPOSITE</i><b>${num(setup.comp,2)}${tagHTML('I')}</b></div>
         <div class="kv"><i>CONFLICT</i><b>${setup.conflict?'YES':'no'}</b></div>
       </div>`
    : (tp ? absNone('aakhri bar pe koi setup taiyaar') : absUnchecked('tape load nahi hui'));

  /* narrative ----------------------------------------------------------- */
  const evs = (day && day.events) || [];
  setText($('evMeta'), evs.length ? `${evs.length} events` : '');
  const host=$('evList');
  if(!evs.length){
    host.innerHTML = `<div class="pb">${tp?absNone('aaj ke narrative events'):absUnchecked('tape load nahi hui')}</div>`;
  }else{
    const want = evs.slice().reverse();
    const sig = want.length+':'+(want[0].t||'')+(want[0].msg||'').slice(0,20);
    if(host.dataset.sig !== sig){
      host.dataset.sig = sig;
      host.innerHTML = want.map(e=>{
        const loud=/CAMPAIGN|SQUEEZE|TRAP|BREAK|STATE/.test(e.kind||'');
        return `<div class="evrow${loud?' loud':''}"><span class="t">${esc(e.t||'')}</span>
          <span class="k">${esc(e.kind||'')}</span><span class="m">${esc(e.msg||'')}</span></div>`;
      }).join('');
    }
  }
}

/* ==========================================================================
   SURFACE -- the vol day story and the buyer's tax
   ========================================================================== */
function renderSurface(){
  const sf = S.surface && S.surface.indices ? S.surface.indices[S.idx] : null;

  /* ATM vol through the day --------------------------------------------- */
  if(!sf){
    $('ivChart').innerHTML = `<div class="pb">${S.err.surface?absUnchecked('/api/surface: '+S.err.surface)
      :absNone('surface fit')}${covReason('surface')}</div>`;
    $('ivLegend').innerHTML=''; $('fitBody').innerHTML=''; $('rcBody').innerHTML='';
  }else{
    const day = sf.day||{};
    const pts = (day.series||[]).map(p=>({t:p.t, v:p.a}));
    setText($('ivMeta'), day.n ? `${day.n} samples · ${pts.length} plot hue` : '');
    const marks=[];
    if(day.hi&&day.hi.t) marks.push({t:day.hi.t, label:'HI', color:'#C9A227'});
    if(day.lo&&day.lo.t) marks.push({t:day.lo.t, label:'LO', color:'#6FB3C9'});
    const g = lineChart($('ivChart'), pts, {color:'#8B7BF0', h:150,
      fmt:v=>(v*100).toFixed(1)+'%', marks,
      empty: absNone('ATM vol samples')});

    const o=day.open, n=day.now;
    const dv = (o&&n) ? (n.a-o.a) : null;
    $('ivLegend').innerHTML =
      `<span>open <b>${o?pct(o.a,2):'—'}</b> @${esc(o&&o.t||'')}</span>
       <span>now <b>${n?pct(n.a,2):'—'}</b></span>
       <span style="color:${dv>0?'var(--bear)':'var(--bull)'}">${dv!==null?(dv>0?'+':'')+(dv*100).toFixed(2)+' vol pts':'—'}</span>
       <span>hi <b>${day.hi?pct(day.hi.a,2):'—'}</b> @${esc(day.hi&&day.hi.t||'')}</span>
       <span>lo <b>${day.lo?pct(day.lo.a,2):'—'}</b> @${esc(day.lo&&day.lo.t||'')}</span>` +
      (g.gaps?`<span style="color:var(--amber)">${g.gaps} feed gap(s)</span>`:'');

    /* skew gets its own block: it is a second question ("which side is being
       paid for") and does not belong squashed into the ATM legend */
    const so = o && o.b, sn2 = n && n.b;
    const smove = (so!==null&&so!==undefined&&sn2!==null&&sn2!==undefined) ? sn2-so : null;
    $('skewBody').innerHTML =
      `<div class="sgrid">
        <div class="kv"><i>OPEN</i><b>${num(so,3)} <span class="quiet">@${esc(o&&o.t||'')}</span></b></div>
        <div class="kv"><i>NOW</i><b>${num(sn2,3)} <span class="quiet">@${esc(n&&n.t||'')}</span></b></div>
        <div class="kv"><i>MOVE</i><b style="color:${smove>0?'var(--bear)':smove<0?'var(--bull)':'var(--muted)'}">${
          smove===null?'—':(smove>0?'+':'')+num(smove,3)}</b></div>
        <div class="kv"><i>FIT SKEW</i><b>${num((sf.fit||{}).skew,4)}${tagHTML(sf.tag)}</b></div>
       </div>
       <div style="margin-top:6px">${absHidden('skew ki day series nahi — /api/surface sirf open/now pe b deta hai, isliye move ka shape banaya nahi ja sakta')}</div>`;

    /* fit quality ------------------------------------------------------- */
    const fit=sf.fit||{};
    setText($('fitMeta'), fit.ok?'fit ok':'FIT FAILED');
    $('fitBody').innerHTML =
      `<div class="sgrid">
        <div class="kv"><i>ATM IV</i><b>${pct(fit.atm_iv,2)}${tagHTML(sf.tag)}</b></div>
        <div class="kv"><i>SKEW</i><b>${num(fit.skew,4)}</b></div>
        <div class="kv"><i>CONVEXITY</i><b>${num(fit.convexity,1)}</b></div>
        <div class="kv"><i>RMSE</i><b>${num(fit.rmse,5)}</b></div>
        <div class="kv"><i>POINTS USED</i><b>${fit.n??'—'}</b></div>
        <div class="kv"><i>EXCLUDED</i><b>${fit.excluded??'—'}</b></div>
        <div class="kv"><i>FORWARD</i><b>${px(sf.f)} <span class="quiet">${esc(sf.f_src||'')}</span></b></div>
        <div class="kv"><i>PARITY GAP</i><b>${num(sf.parity_gap,4)}</b></div>
       </div>
       <ul class="why" style="margin-top:8px">${(sf.why||[]).map(w=>`<li>${esc(w)}</li>`).join('')}</ul>
       ${sf.disagreed?`<div class="quiet">${sf.disagreed} point(s) disagreed CE vs PE</div>`:''}`;

    /* rich / cheap ------------------------------------------------------ */
    const rows = (list,cls)=> (list||[]).map(p=>`<tr>
      <td class="n">${px(p.k)}</td><td>${esc(p.right)}</td>
      <td class="n">${pct(p.iv,2)}</td>
      <td class="n ${cls}">${p.fit_resid!==undefined?num(p.fit_resid,4):num(p.resid,4)}</td>
      <td class="n">${oiC(p.oi)}</td><td class="n">${num(p.ltp,2)}</td></tr>`).join('');
    $('rcBody').innerHTML =
      `<table class="t"><thead><tr><th>STRIKE</th><th>R</th><th>IV</th><th>RESID</th><th>OI</th><th>LTP</th></tr></thead>
       <tbody>${rows(sf.richest,'neg')}${rows(sf.cheapest,'pos')}</tbody></table>`;
  }

  /* the tax -------------------------------------------------------------- */
  const dg = S.drag && S.drag.indices ? S.drag.indices[S.idx] : null;
  if(!dg){
    $('dgChart').innerHTML = `<div class="pb">${S.err.drag?absUnchecked('/api/drag: '+S.err.drag)
      :absNone('drag board')}${covReason('drag')}</div>`;
    $('dgLegend').innerHTML=''; $('dgNow').innerHTML='';
    return;
  }
  const day=dg.day||{};
  // frac blows up on tiny denominators -- plot only the sane band, and say so
  const all=(day.series||[]).filter(p=>p.frac!==null&&p.frac!==undefined);
  const sane=all.filter(p=>Math.abs(p.frac)<=1);
  const suspect=all.length-sane.length;
  const g=lineChart($('dgChart'), sane.map(p=>({t:p.t, v:p.frac})), {
    color:'#D9706A', h:150, zero:0, fmt:v=>(v*100).toFixed(0)+'%',
    empty: absNone('kaam ke tax samples')});
  setText($('dgMeta'), day.n?`${day.n} samples`:'');

  const hiSus = day.hi && Math.abs(day.hi.frac)>1;
  $('dgLegend').innerHTML =
    `<span>abhi <b>${dg.frac!==null&&dg.frac!==undefined?pct(dg.frac,1):'—'}</b> move ka udhaar</span>
     <span>side <b>${esc(String(dg.right_side||'—').toUpperCase())}</b></span>
     <span>day hi ${hiSus
        ? `<span class="susp" title="denominator collapsed — server fix queued">${num(day.hi.frac,1)}×</span>
           <span style="color:var(--amber)">suspect</span>`
        : `<b>${day.hi?pct(day.hi.frac,0):'—'}</b> @${esc(day.hi&&day.hi.t||'')}`}</span>` +
    (suspect?`<span style="color:var(--amber)">${suspect} sample &gt;100% — shaqi maan ke hataye</span>`:'') +
    (g.gaps?`<span style="color:var(--amber)">${g.gaps} feed gap(s)</span>`:'');

  const sideBox = (label, s) => s
    ? `<div class="kv"><i>${label}</i><b>owed ${num(s.owed,2)} · paid ${num(s.paid,2)} ·
        drag <span style="color:var(--risk)">${num(s.drag,2)}</span> (${pct(s.frac,1)})${tagHTML(s.tag)}</b></div>`
    : `<div class="kv"><i>${label}</i><b>${absNone('is taraf anchor')}</b></div>`;
  $('dgNow').innerHTML =
    `<div class="sgrid" style="grid-template-columns:1fr">
      <div class="kv"><i>ANCHOR</i><b>${px(dg.strike)} @ ${esc(dg.anchored_at||'—')} · underlying ${num(dg.d_under,2)} hila</b></div>
      ${sideBox('CE', dg.ce)}${sideBox('PE', dg.pe)}
     </div>
     <div class="quiet" style="margin-top:6px">${esc((S.drag&&S.drag.note)||'')}</div>`;
}

/* ==========================================================================
   PAPER -- the 2-lot self-trading test book. Never an order path.
   ========================================================================== */

/* ==========================================================================
   ROUND 7 -- THE HEDGE LEDGER (paper futures against a paper option book)
   The decomposition is the point: theta collected is gross, the hedge bill is
   what realized vol actually charged, and the difference is what the seller
   really kept. hedge_cost is normally NEGATIVE -- that is not an error, it IS
   the bill, so it is never shown as a loss to be explained away.
   ========================================================================== */
function hedgeOf(){
  const p = S.paper && S.paper.desk;
  const hg = p && p.hedge;
  if(!hg) return null;
  const per = (hg.indices && hg.indices[S.idx]) || null;
  return {hg, per};
}

function renderHedge(){
  const H = hedgeOf();
  const host = $('hgBody');
  if(!host) return;
  if(!H){
    host.innerHTML = S.err.paperdesk
      ? absUnchecked('/api/paperdesk: '+S.err.paperdesk)
      : absNone('hedge ledger (/api/paperdesk.hedge)');
    $('hgFills').innerHTML=''; $('hgNote').innerHTML=''; setText($('hgMeta'),''); return;
  }
  const {hg, per} = H;
  setText($('hgMeta'), `${hg.paper?'PAPER':''}${hg.shadow?' \u00b7 SHADOW':''}`);

  if(!per){
    // idle is a real state, not an error: no option position => nothing to hedge
    const n = Object.keys(hg.indices||{}).length;
    host.innerHTML =
      `<div class="abs none" style="font-size:12px">${S.idx} pe hedger khaali baitha hai \u2014 ` +
      `koi option position nahi, to hedge bhi nahi${n?` (abhi ${n} aur index pe chal raha hai)`:''}</div>` +
      `<div class="quiet" style="margin-top:5px">ab tak ka kul hedge kharcha ${
        rs0(hg.cumulative_hedge_cost)}${tagHTML(hg.tag)}</div>`;
    $('hgFills').innerHTML = fillsTable(hg.fills_today);
    $('hgNote').innerHTML = hedgeNote(hg, null);
    return;
  }

  /* 1 -- the decomposition */
  const th = per.theta_collected, hc = per.hedge_cost_today, nv = per.net_variance;
  host.innerHTML =
    `<div class="hg-eq">
       <span class="hg-t"><i>THETA JAMA</i><b class="pos">${rs0(th)}</b></span>
       <span class="hg-op">\u2212</span>
       <span class="hg-t"><i>HEDGE KA BILL</i><b class="neg">${rs0(Math.abs(hc||0))}</b></span>
       <span class="hg-op">=</span>
       <span class="hg-t big"><i>ASLI VARIANCE CAPTURE</i>
         <b class="${nv<0?'neg':'pos'}">${rs0(nv)}</b></span>
     </div>` +

  /* 5 -- the hedger refusing is the product; it goes ABOVE the numbers */
    (per.delta_why
      ? `<div class="hg-refuse"><i>HEDGER MANA KAR RAHA HAI</i>${esc(per.delta_why)}</div>` : '') +

  /* 2 -- delta state against the band */
    `<div class="hg-delta">
       <span class="dl"><i>OPTION DELTA</i><b>${num(per.option_delta_lots,2)}</b><span>lots</span></span>
       <span class="dl"><i>HEDGE</i><b>${num(per.hedge_lots,2)}</b><span>lots</span></span>
       <span class="dl net"><i>NET</i><b class="${
         Math.abs(per.net_delta_lots||0) > Math.abs(per.band_lots||0) ? 'out':''}">${
         num(per.net_delta_lots,2)}</b><span>band \u00b1${num(per.band_lots,2)}</span></span>
       <span class="dl"><i>HEDGES</i><b>${per.hedges_used ?? '\u2014'}/${per.hedges_max ?? '\u2014'}</b>
         <span>aaj</span></span>
       ${per.brake_hit
         ? `<span class="hg-brake">BRAKE LAGA \u2014 ${esc(per.brake_why||'aur hedge nahi')}</span>`
         : `<span class="dl"><i>BRAKE</i><b class="ok">nahi</b><span>chalu hai</span></span>`}
     </div>` +

  /* 3 -- the honesty: hedging stops at the closing bell */
    (per.gap_exposure
      ? `<div class="hg-gap"><i>RAAT KA GAP HEDGE KE BAHAR HAI</i>
           <b>${rs0(per.gap_exposure.rupees)}</b>
           <span>at \u00b1${num(per.gap_exposure.move,0)}${
             per.gap_exposure.em_x!=null?` \u00b7 ${num(per.gap_exposure.em_x,2)}\u00d7 expected move`:''}</span>
           ${per.gap_exposure.why?`<span class="q">${esc(per.gap_exposure.why)}</span>`:''}
           ${per.gap_exposure.note?`<span class="q">${esc(per.gap_exposure.note)}</span>`:''}
         </div>`
      : `<div class="hg-gap">${absNone('gap exposure ka hisaab')}</div>`);

  $('hgFills').innerHTML = fillsTable(per.fills_today && per.fills_today.length
    ? per.fills_today : hg.fills_today);
  $('hgNote').innerHTML = hedgeNote(hg, per);
}

function fillsTable(f){
  if(!Array.isArray(f) || !f.length)
    return `<div class="pb">${absNone('aaj ke hedge fills')}</div>`;
  const cols = [...new Set(f.flatMap(r=>Object.keys(r)))].slice(0,7);
  return `<table class="t"><thead><tr>${cols.map(c=>`<th>${esc(c.toUpperCase())}</th>`).join('')}</tr></thead><tbody>` +
    f.slice(-25).reverse().map(r=>`<tr>${cols.map(c=>{
      const v = r[c];
      const numeric = typeof v === 'number';
      return `<td class="${numeric?'n':''}">${v===null||v===undefined?'\u2014'
        :numeric?num(v, Math.abs(v)>=100?0:2):esc(String(v))}</td>`;
    }).join('')}</tr>`).join('') + '</tbody></table>';
}

/* the fill model's optimism, stated once, in the server's own words */
function hedgeNote(hg, per){
  return `<div class="quiet">hedge cost ek <b>lower bound</b> hai \u2014 na spread, na slippage
      maana gaya${tagHTML('I')}</div>` +
    (per && per.fill_model ? `<div class="cov-src"><i>${esc(per.fill_model)}</i></div>` : '') +
    (hg.note ? `<div class="cov-src"><i>${esc(hg.note)}</i></div>` : '') +
    (hg.ledger ? `<div class="quiet">ledger: ${esc(hg.ledger)}</div>` : '');
}


/* ==========================================================================
   ROUND 9 -- THE DAY'S TRADES: kya / kab / kyu / kitna, per index.
   Built against /api/paperdesk.day_trades (complete, restart-proof). Until
   that lands we degrade to closed_today and SAY that it truncates on restart
   -- a shorter list presented as the whole day would be the lie here.
   ========================================================================== */
function hms2s(t){
  const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?/.exec(t||'');
  return m ? (+m[1])*3600 + (+m[2])*60 + (+(m[3]||0)) : null;
}
function holdStr(sec){
  if(sec===null || sec===undefined) return '—';
  if(sec < 60) return sec+' sec';
  if(sec < 3600) return Math.floor(sec/60)+' min '+(sec%60?(sec%60)+'s':'');
  return (sec/3600).toFixed(1)+' ghante';
}
/* stable colour per strategy without a lookup table to maintain */
function stratHue(name){
  let h=0; for(let i=0;i<(name||'').length;i++) h = (h*31 + name.charCodeAt(i)) % 360;
  return h;
}

function dayTrades(){
  const p = S.paper && S.paper.desk;
  if(!p) return {rows:[], src:null, why:'paper desk nahi mila'};
  if(Array.isArray(p.day_trades)){
    return {rows: p.day_trades.map(t=>({
      pid:t.pid, idx:t.idx, strategy:t.strategy, instrument:t.instrument, side:t.side,
      qty:t.qty, entry_ts:t.entry_ts, entry_px:t.entry_px, exit_ts:t.exit_ts,
      exit_px:t.exit_px, realized:t.realized, mode:t.mode, why:t.why,
      hold_s: t.hold_s!==null && t.hold_s!==undefined ? t.hold_s
              : (hms2s(t.exit_ts)!==null && hms2s(t.entry_ts)!==null
                 ? hms2s(t.exit_ts)-hms2s(t.entry_ts) : null)
    })), src:'day_trades', complete:true};
  }
  // fallback: the truncated in-memory list
  const ct = p.closed_today || [];
  return {rows: ct.map(c=>({
    pid:c.pid, idx:c.idx, strategy:c.strategy, instrument:null, side:null, qty:null,
    entry_ts:c.opened, entry_px:null, exit_ts:c.closed, exit_px:null,
    realized:c.realized, mode:null, why:c.forced_who,
    hold_s: (hms2s(c.closed)!==null && hms2s(c.opened)!==null)
            ? hms2s(c.closed)-hms2s(c.opened) : null
  })), src:'closed_today', complete:false};
}

function renderPaperDay(){
  const D = dayTrades();
  const p = S.paper && S.paper.desk;

  /* ---- all-index strip: the whole desk before drilling into one ---- */
  const perIdx = {};
  for(const t of D.rows){
    const k = t.idx || '?';
    (perIdx[k] = perIdx[k] || {net:0, n:0}).net += (t.realized||0);
    perIdx[k].n++;
  }
  const idxs = ['NIFTY','BANKNIFTY','SENSEX'].filter(k=>perIdx[k]).concat(
    Object.keys(perIdx).filter(k=>!['NIFTY','BANKNIFTY','SENSEX'].includes(k)));
  $('pdSummary').innerHTML = idxs.length
    ? idxs.map(k=>`<button class="ix ${k===S.idx?'on':''}" data-ix="${esc(k)}">
        <i>${esc(k)}</i><b class="${perIdx[k].net<0?'neg':'pos'}">${rs0(perIdx[k].net)}</b>
        <span>${perIdx[k].n} trades</span></button>`).join('')
    : `<span class="quiet">${esc(D.why||'aaj koi band trade nahi')}</span>`;

  const mine = D.rows.filter(t=>(t.idx||'') === S.idx);
  setText($('pdMeta'), `${S.idx} \u00b7 ${mine.length} trades` +
    (D.src==='day_trades' ? ' \u00b7 poora din' : ''));

  /* the honesty that decides whether these numbers are the day */
  $('pdSrcNote').innerHTML = D.src==='day_trades'
    ? `<span class="quiet">trades.jsonl se \u2014 restart ke baad bhi poora din${tagHTML('M')}</span>`
    : `<span class="abs unchecked">closed_today se \u2014 yeh list server restart pe kat jaati hai,
       isliye <b>poore din ki nahi</b> ho sakti. day_trades aane par apne aap poora ho jayega.</span>`;

  /* ---- per-strategy accounting: rupees and counts ONLY ---- */
  const byS = {};
  for(const t of mine){
    const k = t.strategy || '?';
    (byS[k] = byS[k] || {net:0, n:0}).net += (t.realized||0);
    byS[k].n++;
  }
  const ks = Object.keys(byS).sort((a,b)=>byS[b].n-byS[a].n);
  $('pdAcct').innerHTML = ks.length
    ? ks.map(k=>`<div class="sacc"><span class="sdot" style="background:hsl(${stratHue(k)} 60% 55%)"></span>
        <span class="sn">${esc(k)}</span>
        <b class="${byS[k].net<0?'neg':'pos'}">${rs0(byS[k].net)}</b>
        <span class="q">${byS[k].n} trades</span></div>`).join('') +
      `<div class="quiet" style="margin-top:5px">sirf hisaab \u2014 kitne jeete/haare wo yahan
        jaan-boojh kar nahi likha; pass-bar tum khud tay karogi ~30 session baad</div>`
    : `<div>${absNone(`${S.idx} ki aaj koi band trade`)}</div>`;

  /* ---- the story rows ---- */
  const host = $('pdTrades');
  if(!mine.length){
    host.innerHTML = `<div class="pb">${absNone(`${S.idx} ki aaj koi band trade`)}</div>`;
  }else{
    const sorted = mine.slice().sort((a,b)=>(hms2s(b.exit_ts)||0)-(hms2s(a.exit_ts)||0));
    const sig = sorted.map(t=>t.pid+':'+t.realized).join('|');
    if(host.dataset.sig !== sig){
      host.dataset.sig = sig;
      host.innerHTML = sorted.map(t=>{
        const hue = stratHue(t.strategy);
        const kya = t.instrument
          ? `${t.side?`<span class="sd ${esc(t.side)}">${esc(t.side)}</span>`:''}
             <b>${esc(t.instrument)}</b>${t.qty?`<span class="q">\u00d7${t.qty}</span>`:''}`
          : `<b class="quiet">${esc(t.pid||'')}</b>
             <span class="q">${absNone('instrument')}</span>`;
        return `<div class="tr" data-pid="${esc(t.pid)}">
          <div class="c-kya"><span class="strat" style="border-color:hsl(${hue} 60% 45%);
            color:hsl(${hue} 60% 62%)">${esc(t.strategy||'?')}</span>
            ${kya}${t.mode?`<span class="mk">${esc(t.mode)}</span>`:''}</div>
          <div class="c-kab"><span class="n">${esc(t.entry_ts||'\u2014')}</span>
            <span class="ar">\u2192</span><span class="n">${esc(t.exit_ts||'\u2014')}</span>
            <span class="hold">${holdStr(t.hold_s)}</span></div>
          <div class="c-kyu">${t.why ? esc(t.why)
            : `<span class="abs none">wajah likhi nahi gayi</span>`}</div>
          <div class="c-kitna ${t.realized<0?'neg':'pos'}">${rs0(t.realized)}</div>
        </div>`;
      }).join('');
    }
  }

  renderDayTimeline(mine);

  /* ---- refusals, first-class ---- */
  const refs = Array.isArray(p && p.day_refusals) ? p.day_refusals
             : ((p && p.decisions) || []).filter(x=>x.kind==='refusal');
  setText($('pdRefMeta'), `${refs.length}`);
  $('pdRefs').innerHTML = refs.length
    ? refs.slice().reverse().slice(0,80).map(r=>`<div class="rf">
        <span class="t">${esc(String(r.ts||r.t||'').slice(-8))}</span>
        <span class="k">${esc(r.idx||'')} ${esc(r.strategy||'')}</span>
        <span class="m">${esc(r.detail||r.why||r.reason||'')}</span></div>`).join('')
    : `<div class="pb">${absNone('aaj ke refusals')}${
        Array.isArray(p && p.day_refusals) ? '' : covReason('paper')}</div>`;
}

/* ---- the day's shape: when did she actually trade ---- */
function renderDayTimeline(rows){
  const host = $('pdTimeline');
  const pts = rows.filter(t=>hms2s(t.exit_ts)!==null);
  if(pts.length < 2){ host.innerHTML = `<div class="pb">${absNone('timeline ke liye kaafi trades')}</div>`; return; }
  const W=900, H=54, L=8, R=8, T=16;
  const t0 = 9*3600+15*60, t1 = 15*3600+30*60;      // the session, fixed axis
  const sx = sec => L + Math.max(0, Math.min(1,(sec-t0)/(t1-t0)))*(W-L-R);
  const marks = pts.map(t=>{
    const x = sx(hms2s(t.exit_ts)), hue = stratHue(t.strategy);
    const up = (t.realized||0) >= 0;
    return `<line x1="${x.toFixed(1)}" y1="${T}" x2="${x.toFixed(1)}" y2="${T+(up?-9:9)}"
      stroke="hsl(${hue} 60% 58%)" stroke-width="1.6" opacity=".9"><title>${esc(t.exit_ts)} ${
      esc(t.strategy||'')} ${rs0(t.realized)} \u00b7 ${holdStr(t.hold_s)}${
      t.why?' \u00b7 '+esc(t.why):''}</title></line>`;
  }).join('');
  const ticks = [];
  for(let h=10; h<=15; h++){
    const x = sx(h*3600);
    ticks.push(`<line x1="${x.toFixed(1)}" y1="${T-12}" x2="${x.toFixed(1)}" y2="${T+12}"
      stroke="#151D28" stroke-width="1"></line>
      <text x="${x.toFixed(1)}" y="${H-4}" fill="#63738C" font-size="9" text-anchor="middle"
      font-family="monospace">${h}:00</text>`);
  }
  host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">
    ${ticks.join('')}
    <line x1="${L}" y1="${T}" x2="${W-R}" y2="${T}" stroke="#26312F" stroke-width="1"></line>
    ${marks}
    <text x="${L}" y="${H-4}" fill="#63738C" font-size="9" font-family="monospace">09:15</text>
    <text x="${W-R}" y="${H-4}" fill="#63738C" font-size="9" text-anchor="end"
      font-family="monospace">15:30</text></svg>
    <div class="clegend"><span class="quiet">upar = faayda, neeche = nuksan \u00b7 rang = strategy
      \u00b7 exit ke time pe nishaan</span></div>`;
}


function renderPaper(){
  const p = S.paper && S.paper.desk;
  if(!p){
    $('pbOpen').innerHTML = `<div class="pb">${S.err.paperdesk?absUnchecked('/api/paperdesk: '+S.err.paperdesk):absNone('paper desk')}</div>`;
    renderHedge(); renderPaperDay();
    return;
  }
  setText($('pbMeta'), `${(p.open||[]).length} khuli · ${p.lots} lots · aaj ${p.day_pnl>=0?'+':''}${num(p.day_pnl,2)}`);

  const marks = new Map((p.marks||[]).map(m=>[m.pid,m]));
  const open = p.open||[];
  $('pbOpen').innerHTML = open.length
    ? `<table class="t"><thead><tr><th>PID</th><th>IDX</th><th>STRATEGY</th><th>LEGS</th>
        <th>UNREAL</th><th>Δ</th><th>Γ</th><th>ATTRIBUTION</th></tr></thead><tbody>` +
      open.map(o=>{
        const m=marks.get(o.pid)||{}, a=m.attribution||{};
        const legs=(o.legs||[]).map(l=>`${l.side} ${px(l.strike)}${l.right}@${num(l.entry_px,2)}`).join('<br>');
        const u=m.unrealized;
        return `<tr><td class="n">${esc(o.pid)}</td><td>${esc(o.idx)}</td>
          <td>${esc(o.strategy)}<div class="quiet">${esc(o.opened_ts||'')}</div></td>
          <td class="quiet" style="font-family:var(--mono)">${legs}</td>
          <td class="n ${u>=0?'pos':'neg'}">${num(u,2)}</td>
          <td class="n">${num(m.net_delta,1)}</td><td class="n">${num(m.net_gamma,3)}</td>
          <td class="quiet n">δ${num(a.delta,0)} ν${num(a.vega,0)} r${num(a.theta_gamma_resid,0)}${tagHTML(a.tag)}</td>
        </tr>`;
      }).join('') + '</tbody></table>'
    : `<div class="pb">${absNone('khuli paper positions')}</div>`;

  const r=p.risk||{};
  $('pbRisk').innerHTML =
    `<div class="sgrid" style="grid-template-columns:1fr">
      <div class="kv"><i>CAPITAL</i><b>₹${compact(r.capital)}</b></div>
      <div class="kv"><i>MARGIN USED</i><b>₹${compact(r.margin_used)}${tagHTML(r.tag)}</b></div>
      <div class="kv"><i>HEADROOM</i><b>₹${compact(r.headroom)}</b></div>
      <div class="kv"><i>STRESSED NEED</i><b>₹${compact(r.stressed_need)} (×${num(r.stress_margin_x,1)})</b></div>
      <div class="kv"><i>FORCED RATIO</i><b>${num(r.forced_ratio,2)}</b></div>
      <div class="kv"><i>DAY P&amp;L</i><b class="${p.day_pnl>=0?'pos':'neg'}" style="color:${p.day_pnl>=0?'var(--bull)':'var(--bear)'}">${num(p.day_pnl,2)}</b></div>
      <div class="kv"><i>REALIZED TOT</i><b style="color:${p.realized_total>=0?'var(--bull)':'var(--bear)'}">${num(p.realized_total,2)}</b></div>
      <div class="kv"><i>STOPPED</i><b>${p.day_stopped?'YES':'no'}</b></div>
     </div>
     ${r.forced_why?`<div class="quiet" style="margin-top:6px">${esc(r.forced_why)}</div>`:''}
     <div class="quiet" style="margin-top:6px">${esc(r.note||'')}</div>
     <div class="quiet" style="margin-top:6px;color:var(--amber)">${esc(p.note||'')}</div>`;

  // the day's closed trades now render as story rows in renderPaperDay()
  // refusals: the book saying no is the most informative thing it does
  renderHedge();
  renderPaperDay();

}

/* ========================================================================== */
function renderAll(){
  renderHeader();
  renderCoverage();
  renderDayTile();
  if(S.screen==='desk') renderDesk();
  else if(S.screen==='war') renderWar();
  else if(S.screen==='tape') renderTape();
  else if(S.screen==='surface') renderSurface();
  else if(S.screen==='paper') renderPaper();

  /* Offline banner. Nothing is cleared -- what she sees is the last good read,
     and the banner says exactly how old it is. */
  const off = $('offline');
  const thinKeys = Object.keys(S.thin);
  if(S.err.desk || thinKeys.length){
    off.removeAttribute('hidden');
    document.body.classList.add('stale');
    setText($('offTxt'), S.err.desk
      ? 'server se sampark nahi \u2014 data mita nahi, purana dikha rahe hain'
      : 'server chalu hai par is session ka data uske paas nahi ('+thinKeys.join(', ')+
        ') \u2014 jo browser ne dekha wahi dikha rahe hain');
    setText($('offAge'), S.lastGoodAt
      ? 'aakhri update ' + new Date(S.lastGoodAt).toLocaleTimeString('en-GB',
          {timeZone:'Asia/Kolkata', hour12:false}) + ' \u00b7 ' + staleSeconds() + 's pehle'
      : (S.restoredAt ? 'browser me sanjoya gaya ' + S.restoredAt : 'abhi tak koi update nahi'));
  }else{
    off.setAttribute('hidden','');
    document.body.classList.remove('stale');
  }

  const errs = Object.keys(S.err);
  setText($('footMeta'),
    'poll ' + S.polls + ' \u00b7 ' + istNow() + ' \u00b7 ' +
    (errs.length ? 'DEGRADED: ' + errs.join(', ') : 'sab endpoints jawab de rahe hain') +
    (S.lsFail ? ' \u00b7 localStorage: ' + S.lsFail : ''));
  $('footMeta').style.color = errs.length ? 'var(--amber)' : 'var(--muted)';
}

/* Has this endpoint gone stale enough to be worth re-asking for? Keeps the day
   tile fed on every screen without re-fetching what the active screen just
   pulled. */
const stale = (key, ms) => !S.lastOK[key] || (Date.now() - S.lastOK[key]) > ms;
const CTX_MS = 15000;   // the day's character does not turn over in 5s

async function poll(){
  S.polls++;
  const [dk, hl] = await Promise.all([
    getJSON('/api/desk?capital=50000000','desk'),
    getJSON('/api/health','health')
  ]);
  const dkOK = dk && USABLE.desk(dk);
  S.desk = accept('desk', dk, S.desk);
  if(dkOK){ trackFlips(dk); S.lastGoodAt = Date.now(); }
  if(hl) S.health = hl;

  const onWar = S.screen==='war', onTape = S.screen==='tape', onSurf = S.screen==='surface';
  const jobs = [];

  // warmap / surface / senses / tape feed BOTH their own screen and the day
  // tile, so they refresh at 5s when visible and at 15s when not.
  if(onWar || stale('warmap', CTX_MS))
    jobs.push(getJSON('/api/warmap','warmap').then(w=>{ S.warmap = accept('warmap', w, S.warmap); }));
  if(onWar || stale('oiflowbook', CTX_MS))
    jobs.push(getJSON('/api/oiflow?idx='+encodeURIComponent(S.idx)+'&interval=5','oiflowbook')
      .then(b=>{ S.book = accept('book', b && mergeBook(b), S.book); }));
  if(onSurf || stale('surface', CTX_MS))
    jobs.push(getJSON('/api/surface','surface').then(x=>{ S.surface = accept('surface', x, S.surface); }));
  if(onSurf || stale('drag', CTX_MS))
    jobs.push(getJSON('/api/drag','drag').then(x=>{ S.drag = accept('drag', x && mergeDrag(x), S.drag); }));
  if(onTape || stale('senses', CTX_MS))
    jobs.push(getJSON('/api/senses?n=1','senses').then(x=>{ S.senses = accept('senses', x, S.senses); }));
  if(onTape || stale('vpinsrv', CTX_MS))
    jobs.push(getJSON('/api/vpin','vpinsrv').then(x=>{ S.vpinsrv = accept('vpinsrv', x, S.vpinsrv); }));
  if(onTape || stale('data', CTX_MS))
    jobs.push(getJSON('/api/data?idx='+encodeURIComponent(S.idx),'data').then(x=>{ S.tape = accept('data', x, S.tape); }));
  /* paperdesk feeds the PAPER screen AND four DESK tiles (survival, money
     greeks, hisaab, theta), so it cannot be fetched only when PAPER is open --
     the desk would read an ever-staler book. Same 5s-visible / 15s-background
     rule as every other shared feed. */
  if(S.screen==='paper' || stale('paperdesk', CTX_MS))
    jobs.push(getJSON('/api/paperdesk','paperdesk').then(x=>{ S.paper = accept('paper', x, S.paper); }));

  // premium per strike exists ONLY on /api/chain, and that endpoint is shut
  // outside market hours. Accumulate while it answers; persist so the 4-state
  // paint has a yesterday to compare against.
  if(sessionPhase().phase==='LIVE' || sessionPhase().phase==='CLOSING'){
    if(stale('chain', CTX_MS))
      jobs.push(getJSON('/api/chain?idx='+encodeURIComponent(S.idx),'chain')
        .then(c=>{ if(c && c.ok!==false) absorbChain(c); }));
  }

  await Promise.all(jobs);
  if(onWar) refreshFlow(false);
  syncVpinDay();
  renderAll();

  // ponytail: snapshot on the first good read and then every 6th poll (~30s)
  if(S.desk && (S.polls === 1 || S.polls % 6 === 0)) persistSnapshot();
}

/* One premium sample per strike per minute, kept small on purpose: this is a
   shape record for the 4-state paint, not a tick store. */
function absorbChain(c){
  const rows = c.rows || c.strikes || c.chain || [];
  if(!Array.isArray(rows) || !rows.length) return;
  const t = istHM();
  let touched = false;
  for(const r of rows){
    const k = r.k ?? r.strike ?? r.strike_price;
    if(k===undefined || k===null) continue;
    const ce = (r.ce && (r.ce.ltp ?? r.ce.last_price)) ?? r.ce_ltp ?? null;
    const pe = (r.pe && (r.pe.ltp ?? r.pe.last_price)) ?? r.pe_ltp ?? null;
    if(ce===null && pe===null) continue;
    const arr = S.prem[k] = S.prem[k] || [];
    const last = arr[arr.length-1];
    if(last && last.t===t){ last.ce=ce; last.pe=pe; }
    else { arr.push({t, ce, pe}); touched = true; }
    if(arr.length > 400) arr.shift();
  }
  if(touched) saveLS('prem', S.prem, S.idx);
}

/* ---- reconciliation: server logs win, the browser fills what the server lost -- */
function mergeBook(server){
  const localRows = (S.book && S.book.rows) || [];
  return {...server, rows: mergeByT(localRows, server.rows||[], 'time')};
}

function mergeDrag(server){
  // The drag day-ring lives in server memory and resets on restart; the
  // browser's remembered copy is often the only record of the morning.
  const out = {...server, indices:{...(server.indices||{})}};
  for(const ix of Object.keys(out.indices||{})){
    const prev = S.drag && S.drag.indices && S.drag.indices[ix];
    const sv = out.indices[ix];
    if(prev && prev.day && sv && sv.day){
      sv.day = {...sv.day, series: mergeByT(prev.day.series, sv.day.series, 't')};
    }
  }
  return out;
}

/* VPIN day series: the backend now serves one (/api/vpin). It is authoritative
   where it overlaps; the client accumulation survives only to cover stamps the
   server never wrote, or lost to a restart. */
function syncVpinDay(){
  const vp = S.senses && S.senses.vpin ? S.senses.vpin[S.idx+'-FUT'] : null;
  if(vp && vp.pct!==null && vp.pct!==undefined){
    const t = istHM(), last = S.vpinDay[S.vpinDay.length-1];
    if(!last || last.t!==t) S.vpinDay.push({t, v:vp.pct, raw:vp.vpin});
    else { last.v = vp.pct; last.raw = vp.vpin; }
  }
  const srv = S.vpinsrv;
  if(srv && srv.inst === S.idx+'-FUT' && Array.isArray(srv.series)){
    const sv = srv.series
      .filter(p=>p.pct!==null && p.pct!==undefined)
      .map(p=>({t:String(p.t).slice(0,5), v:p.pct, raw:p.vpin}));
    S.vpinDay = mergeByT(S.vpinDay, sv, 't');
    S.vpinSrc = 'server /api/vpin + browser';
  }else{
    S.vpinSrc = srv ? ('server has no '+S.idx+'-FUT series \u2014 browser only') : 'browser only';
  }
  saveLS('vpin', S.vpinDay, S.idx);
}

/* A screen switch just re-polls: poll() already fetches exactly what the
   active screen needs, so there is one code path instead of two. */
async function primeScreen(){ renderAll(); await poll(); }

function init(){
  restoreSnapshot();
  S.vpinDay = loadLS('vpin', [], S.idx) || [];
  S.prem = loadLS('prem', {}, S.idx) || {};

  // One-time purge of flips produced by the `best`-is-a-string bug. These were
  // never real answer changes, so leaving them in would keep the stability
  // meter screaming at a defect instead of at the market.
  let dirty = false;
  for(const ix of Object.keys(FLIPS)){
    const keep = FLIPS[ix].filter(f => !/undefined/.test(f.text||''));
    if(keep.length !== FLIPS[ix].length){ FLIPS[ix] = keep; dirty = true; }
  }
  for(const ix of Object.keys(SIG)){
    if(/undefined/.test(SIG[ix] && SIG[ix].struct || '')){ delete SIG[ix]; dirty = true; }
  }
  if(dirty){ saveLS('flips', FLIPS); saveLS('sig', SIG); }

  for(const b of document.querySelectorAll('#tabs button')){
    b.addEventListener('click', ()=>{
      for(const x of document.querySelectorAll('#tabs button')) setClass(x, x===b?'active':'');
      S.screen = b.dataset.scr;
      for(const s of document.querySelectorAll('.screen'))
        setClass(s, 'screen'+(s.id==='scr-'+S.screen?' active':''));
      primeScreen();
    });
  }
  for(const b of document.querySelectorAll('#idxTabs button')){
    b.addEventListener('click', ()=>{
      for(const x of document.querySelectorAll('#idxTabs button')) setClass(x, x===b?'active':'');
      persistSnapshot();                       // keep the outgoing index's work
      S.idx = b.dataset.idx;
      S.flow = loadLS('flow', {}, S.idx) || {};
      S.flowIdx = Object.keys(S.flow).length ? S.idx : null;
      S.vpinDay = loadLS('vpin', [], S.idx) || [];
      S.prem = loadLS('prem', {}, S.idx) || {};
      S.tape = null; S.book = null; S.openStruct.clear();
      renderAll(); primeScreen();
    });
  }

  $('covToggle').addEventListener('click', ()=>{
    saveLS('covopen', $('coverage').classList.toggle('open'));
  });
  if(loadLS('covopen', false)) $('coverage').classList.add('open');

  $('ftToggle').addEventListener('click', ()=>{
    saveLS('ftopen', $('fuelTank').classList.toggle('open'));
  });
  if(loadLS('ftopen', false)) $('fuelTank').classList.add('open');

  // the all-index strip doubles as a selector: clicking one scopes the screen
  document.addEventListener('click', e=>{
    const b = e.target.closest && e.target.closest('#pdSummary .ix');
    if(!b) return;
    const t = document.querySelector(`#idxTabs button[data-idx="${b.dataset.ix}"]`);
    if(t) t.click();
  });

  $('dtToggle').addEventListener('click', ()=>{
    saveLS('dtopen', $('dayTile').classList.toggle('open'));
  });
  if(loadLS('dtopen', false)) $('dayTile').classList.add('open');

  // never lose the tail of a session to a close or a refresh
  addEventListener('pagehide', persistSnapshot);
  document.addEventListener('visibilitychange', ()=>{ if(document.hidden) persistSnapshot(); });

  // must target the inner span: writing textContent on #clock itself would
  // delete the span and the IST label with it
  setInterval(()=>setText($('clockT'), istNow()), 1000);
  renderAll();          // paint the restored snapshot before the first fetch

  /* self-scheduling loop rather than a fixed interval: once the market is shut
     the numbers stop moving, so hammering the server every 5s buys nothing.
     It keeps polling slowly so a server-side backfill still lands on screen. */
  (async function loop(){
    await poll();
    const p = sessionPhase().phase;
    setTimeout(loop, (p==='LIVE'||p==='CLOSING') ? POLL_MS : CLOSED_POLL_MS);
  })();
}

document.addEventListener('DOMContentLoaded', init);
