// THE FLOATING WINDOW on the rev 6 engine (her order 2026-09-29: "the old hold window needs to be replaced by this one ...
// it follows the pro.html logic"). The chrome of the old window (drag, collapse, ✕, pop out over the broker, the word in the
// tab title) around the panel's top three lines (2026-10-04 split: the engine's word, give-up / out-if, the decoder's count):
// an iframe of /pro.html?float=<id> (Desk.tsx FloatBody), on every tab, the Validate tab too -- the DESK no longer draws the
// in-trade face. It exists only while she is in a trade; the tone is the DESK poller's (sound_id). No order path.
import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { createPortal } from 'react-dom'
import { Guard, Ico } from '../hold/parts'
import { hms, isDown, tradeOp, useStore, type Trade } from './api'

const W = 440
const WORDS = ['HOLD', 'PAST GIVE-UP', 'FOLD', "CAN'T CHECK"]
const VCLS: Record<string, string> = { HOLD: 'v-HOLD', 'PAST GIVE-UP': 'v-WATCH', FOLD: 'v-FOLD', "CAN'T CHECK": 'v-PATA', '?': 'v-PATA' }
const RANK: Record<string, number> = { FOLD: 0, 'PAST GIVE-UP': 1, "CAN'T CHECK": 2, '?': 2, HOLD: 3 }
const VSTATE: Record<string, string> = { HOLD: 'v-HOLD', TIGHTEN: 'v-HOLD', WARN: 'v-WATCH', EXIT: 'v-FOLD' }   // the voice's word, collapsed
const ls = (k: string, v?: string) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v) } catch { /* private window */ } return null }
const contract = (t: Trade) => `${t.k} ${t.side}`
// F8 (25 Oct): the read's age off its own clock (/api/fold's asof, HH:MM:SS today), beside l1
const ageOf = (asof: string | undefined, now: number) => {
  const q = /^(\d\d):(\d\d):(\d\d)/.exec(asof ?? '')
  if (!q) return '?'
  const d = new Date(now)
  d.setHours(+q[1], +q[2], +q[3], 0)
  const s = Math.round((now - d.getTime()) / 1000)
  return s < 0 ? '?' : s < 90 ? `${s}s` : `${Math.round(s / 60)} min`
}

export default function Float() {
  return <Guard name="floating window"><Win /></Guard>
}

function Win() {
  const st = useStore()
  const wordOf = (t: Trade) => {
    const r = st.fold[t.id], h = r?.ok ? r.view?.headline : null
    return h == null ? "CAN'T CHECK" : WORDS.find(w => h.toUpperCase().startsWith(w)) ?? '?'   // F8 (25 Oct, F09): an unknown word is ?, never the safe-looking HOLD
  }
  const open = st.trades.filter(t => !t.exit_t).sort((a, b) => RANK[wordOf(a)] - RANK[wordOf(b)] || b.t0.localeCompare(a.t0))
  const [pick, setPick] = useState<string | null>(null)
  const folded = open.filter(t => wordOf(t) === 'FOLD')
  const cur = folded.length && !folded.some(t => t.id === pick) ? folded[0] : open.find(t => t.id === pick) ?? open[0]
  // ✕ closes it for the trades open now; a new trade, or one turning FOLD, brings it back. Closing is not exiting.
  const ck = (t: Trade) => t.id + (wordOf(t) === 'FOLD' ? ':FOLD' : '')
  const [closed, setClosed] = useState<string[]>(() => { try { return JSON.parse(ls('pro.float.closed') || '[]') } catch { return [] } })
  const show = open.some(t => !closed.includes(ck(t)))
  const [min, setMinS] = useState(() => ls('pro.float.min') === '1')
  const [pos, setPos] = useState<{ x: number; y: number } | null>(() => { try { return JSON.parse(ls('pro.float.pos') || 'null') } catch { return null } })
  const [pip, setPip] = useState<Window | null>(null)
  const [arm, setArm] = useState<string | null>(null), [busy, setBusy] = useState(false), [msg, setMsg] = useState<string | null>(null)
  const [h, setH] = useState(420)
  const [now, setNow] = useState(() => Date.now())                     // F8: the age ticks while the poller is quiet
  useEffect(() => { const t = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(t) }, [])
  const frame = useRef<HTMLIFrameElement>(null)
  // THE ONE VOICE (A52) + the TRADE MAP (A53-A62) on top, as on the panel and Validate; [detail ▸] opens the DESK's face below
  const [vOpen, setVOpenS] = useState(() => ls('pro.float.vdet') === '1')
  const setVOpen = (x: boolean) => { ls('pro.float.vdet', x ? '1' : '0'); setVOpenS(x) }

  const word = cur ? wordOf(cur) : null
  const v = cur && st.fold[cur.id]?.ok ? st.fold[cur.id].view : undefined
  const vc = cur && st.fold[cur.id]?.ok && st.fold[cur.id].voice?.ok ? st.fold[cur.id].voice! : null
  const red = word === 'FOLD' || vc?.state === 'EXIT'
  // F8 (25 Oct, F02): api.ts keeps the last read when a poll fails; say so -- NOT LIVE since the first failure (Pro.tsx:35's isDown)
  const down = isDown(st.engineWhy), since = /\((\d\d:\d\d:\d\d)\)$/.exec(st.engineWhy ?? '')?.[1] ?? '?'
  const liveEl = cur && <span className={`vage${down ? ' dead' : ''}`}>{down ? `NOT LIVE since ${since}` : ageOf(st.fold[cur.id]?.asof, now)}</span>
  const setMin = (x: boolean) => { ls('pro.float.min', x ? '1' : '0'); setMinS(x); try { pip?.resizeTo(pip.outerWidth, x ? 110 : 640) } catch { /* the OS keeps its size */ } }

  // the word in the browser tab title (and the pop-out's), so the taskbar carries it behind the broker window
  const head = show && cur && word ? `[${vc ? vc.state : word} ${contract(cur).replace(' ', '')}] ` : ''
  useEffect(() => {
    const put = () => { document.title = head + document.title.replace(/^\[[^\]]*\] /, '') }
    put()
    const t = setInterval(put, 2000)                                  // the app rewrites the title on each tape update
    return () => { clearInterval(t); document.title = document.title.replace(/^\[[^\]]*\] /, '') }
  }, [head])
  useEffect(() => { if (pip) pip.document.title = head || 'DESK' }, [pip, head])
  useEffect(() => { if (!show && pip) pip.close() }, [show, pip])

  // the face's own height, so the window is as tall as the read (capped by the screen)
  useEffect(() => {
    const f = frame.current
    if (!f) return
    let ro: ResizeObserver | null = null
    const hook = () => {
      const b = f.contentDocument?.body
      if (!b) return
      ro?.disconnect()
      ro = new ResizeObserver(() => setH(b.scrollHeight))
      ro.observe(b)
    }
    f.addEventListener('load', hook); hook()
    return () => { f.removeEventListener('load', hook); ro?.disconnect() }
  }, [cur?.id, min, pip, vOpen])

  // drag by the bar (the in-tab float only; the OS moves a pop-out); double-click re-docks it
  const drag = useRef<{ dx: number; dy: number } | null>(null)
  const box = useRef<HTMLDivElement>(null)
  const grip = {
    onPointerDown: (e: React.PointerEvent) => {
      if (pip || (e.target as HTMLElement).closest('button')) return
      const r = box.current!.getBoundingClientRect()
      drag.current = { dx: e.clientX - r.left, dy: e.clientY - r.top }
      ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    },
    onPointerMove: (e: React.PointerEvent) => {
      if (drag.current) setPos({ x: Math.min(Math.max(0, e.clientX - drag.current.dx), window.innerWidth - 160),
                                 y: Math.min(Math.max(0, e.clientY - drag.current.dy), window.innerHeight - 48) })
    },
    onPointerUp: () => { if (drag.current) { drag.current = null; ls('pro.float.pos', JSON.stringify(pos)) } },
    onDoubleClick: () => { setPos(null); ls('pro.float.pos', 'null') },
  }

  const popOut = async () => {
    const dp = (window as unknown as { documentPictureInPicture?: { requestWindow: (o: object) => Promise<Window> } }).documentPictureInPicture
    if (!dp) { setMsg('This browser cannot pop out (it needs Chrome 116 or later) — the window stays in the tab.'); return }
    try {
      const w = await dp.requestWindow({ width: W, height: min ? 110 : 640 })
      w.document.body.style.margin = '0'
      for (const ss of Array.from(document.styleSheets)) {        // the pop-out is a new document: carry the styles over
        try { const s = w.document.createElement('style'); s.textContent = Array.from(ss.cssRules).map(r => r.cssText).join('\n'); w.document.head.append(s) }
        catch { if (ss.href) { const l = w.document.createElement('link'); l.rel = 'stylesheet'; l.href = ss.href; w.document.head.append(l) } }
      }
      w.addEventListener('pagehide', () => setPip(null))
      setPip(w)
    } catch (e) { setMsg(`Could not pop out — ${(e as Error).message}`) }
  }

  // I'M OUT is two presses 5 s apart, as on the DESK: the record is hers, a slip of the hand is not
  const out = async (t: Trade) => {
    if (arm !== t.id) { setArm(t.id); window.setTimeout(() => setArm(a => a === t.id ? null : a), 5000); return }
    setArm(null); setBusy(true); setMsg(null)
    const r = await tradeOp({ op: 'exit', id: t.id, exit_t: hms() })
    setBusy(false)
    if (!r.ok) setMsg(r.why || 'the exit did not land')
  }
  const closeIt = () => { const ids = open.map(ck); ls('pro.float.closed', JSON.stringify(ids)); setClosed(ids) }

  if (!show || !cur) return null

  const others = open.filter(t => t.id !== cur.id)
  const btns = <span className="fl-btns">
    <button type="button" className={`btn btn-sm ${red ? 'btn-out' : ''}`} disabled={busy} onClick={() => out(cur)}>{arm === cur.id ? 'CONFIRM OUT' : "I'M OUT"}</button>
    {!pip ? <button type="button" className="icon-btn" title="Pop out on top of every window" aria-label="Pop out" onClick={popOut}><Ico n="PiP" /></button>
          : <button type="button" className="icon-btn" title="Back into the tab" aria-label="Back into the tab" onClick={() => pip.close()}><Ico n="Undo" /></button>}
    <button type="button" className="icon-btn" title={min ? 'Open' : 'Collapse to one line'} aria-label={min ? 'Open' : 'Collapse'} onClick={() => setMin(!min)}><Ico n={min ? 'ChevronUp' : 'ChevronDown'} /></button>
    <button type="button" className="icon-btn" title="Close the window — it comes back for a new trade, or if an open trade turns FOLD; the trade stays watched" aria-label="Close" onClick={closeIt}><Ico n="X" /></button>
  </span>
  // one line: the word · the contract · the engine's clause (never the P&L here); open: the same line over the DESK's face
  const line = <div className="fl-line" {...grip}>
    {vc && min ? <span className={`word fw ${VSTATE[vc.state]}`}>{vc.state}</span> : <span className={`word fw ${VCLS[word!]}`}>{word}</span>}
    {(!vc || min) && liveEl}
    {st.feed?.alarm && <span className="fl-feed" title={[st.feed.why, st.feed.do].filter(Boolean).join('\n')}>{st.feed.chip}</span>}
    <span className="mid"><span className="c">{contract(cur)}</span><span className="dot">·</span>{cur.role} · in {cur.t0.slice(0, 5)}
      {min && (vc ? <><span className="dot">·</span>{vc.l3.replace(/^why: /, '')}</>                  // collapsed: the voice's own reason, one voice
                  : v?.clause && <><span className="dot">·</span>{v.clause}</>)}{/* open: the body's first line carries it */}
      {others.map(t => <span key={t.id}><span className="dot">·</span><button type="button" className="link" onClick={() => setPick(t.id)} title="show this trade">
        <b className={VCLS[wordOf(t)]}>{wordOf(t)}</b> {contract(t)}</button></span>)}</span>
    {btns}
  </div>
  const cls = `hv float ${min ? 'col' : 'open'}${red ? ' red' : ''}${pip ? ' in-pip' : ''}`
  const style: CSSProperties | undefined = pip ? undefined
    : pos ? { left: Math.max(0, Math.min(pos.x, window.innerWidth - W - 8)), top: pos.y, right: 'auto', bottom: 'auto', ...(min ? {} : { width: W, maxHeight: 'calc(100vh - 32px)' }) }
    : min ? undefined : { width: W, maxHeight: 'calc(100vh - 32px)' }
  const src = new URL(`/pro.html?float=${encodeURIComponent(cur.id)}`, location.href).href   // absolute: a pop-out document has no base
  const voiceEl = vc && <div className={`voice v-${vc.state}`} {...grip}
      title={(vc.active ?? []).map(a => `${a.t} ${a.state} · ${a.reason}`).join(String.fromCharCode(10)) || vc.note}>
    <div className="v1">{vc.l1}{liveEl}</div>
    <div className="v2"><span className="vw">{vc.state}</span>{vc.l2}</div>
    <div className="v3">{vc.l3}{vc.trig_t && vc.state !== 'HOLD' ? ` · ${vc.trig_t}` : ''}</div>
    {vc.l4 && <div className="v3 v4">{vc.l4}</div>}
    {vc.l5 && <div className="v3 v5">{vc.l5}</div>}
    {!vOpen && <span className="vbtns">{btns}</span>}{/* open: the DESK's line below carries them */}
    <button type="button" className="vd" onClick={() => setVOpen(!vOpen)}>detail {vOpen ? '▾' : '▸'}</button>
  </div>
  const mapEl = vc && !!vc.detail?.length && <div className="fl-sec">{vc.detail.map(x => <p className="sm" key={x.text} title={x.tip ?? undefined}>{x.text}</p>)}</div>
  const win = <div ref={box} className={cls} style={style}>
    {vc && !min ? voiceEl : line}
    {msg && <p className="fine" style={{ padding: '4px 12px' }}>{msg} <button type="button" className="link" onClick={() => setMsg(null)}>dismiss</button></p>}
    {!min && (!vc || vOpen) && <>{vc && mapEl}{vc && line}
      <iframe ref={frame} key={cur.id} src={src} title="DESK" style={{ display: 'block', width: '100%', border: 0, height: pip ? 'calc(100vh - 44px)' : Math.min(h, window.innerHeight - 90) }} /></>}
  </div>
  if (pip) return <>{createPortal(win, pip.document.body)}{<div className="hv-back">The DESK is popped out on top <button type="button" onClick={() => pip.close()}>bring it back</button></div>}</>
  return win
}
