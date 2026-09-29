// THE FLOATING WINDOW on the rev 6 engine (her order 2026-09-29: "the old hold window needs to be replaced by this one ...
// it follows the pro.html logic"). The chrome of the old window (drag, collapse, ✕, pop out over the broker, the word in the
// tab title) around the DESK's own face: an iframe of /pro.html?float=<id>, so the words, rows and premium are the DESK's,
// never a second rendering. It exists only while she is in a trade; the tone is the DESK poller's (sound_id). No order path.
import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { createPortal } from 'react-dom'
import { Guard, Ico } from '../hold/parts'
import { hms, tradeOp, useStore, type Trade } from './api'

const W = 440
const WORDS = ['HOLD', 'PAST GIVE-UP', 'FOLD', "CAN'T CHECK"]
const VCLS: Record<string, string> = { HOLD: 'v-HOLD', 'PAST GIVE-UP': 'v-WATCH', FOLD: 'v-FOLD', "CAN'T CHECK": 'v-PATA' }
const RANK: Record<string, number> = { FOLD: 0, 'PAST GIVE-UP': 1, "CAN'T CHECK": 2, HOLD: 3 }
const ls = (k: string, v?: string) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v) } catch { /* private window */ } return null }
const contract = (t: Trade) => `${t.k} ${t.side}`

export default function Float(p: { hidden?: boolean }) {
  return <Guard name="floating window"><Win {...p} /></Guard>
}

function Win({ hidden = false }: { hidden?: boolean }) {
  const st = useStore()
  const wordOf = (t: Trade) => {
    const r = st.fold[t.id], h = r?.ok ? r.view?.headline : null
    return h == null ? "CAN'T CHECK" : WORDS.find(w => h.toUpperCase().startsWith(w)) ?? 'HOLD'
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
  const frame = useRef<HTMLIFrameElement>(null)

  const word = cur ? wordOf(cur) : null
  const v = cur && st.fold[cur.id]?.ok ? st.fold[cur.id].view : undefined
  const red = word === 'FOLD'
  const setMin = (x: boolean) => { ls('pro.float.min', x ? '1' : '0'); setMinS(x); try { pip?.resizeTo(pip.outerWidth, x ? 110 : 640) } catch { /* the OS keeps its size */ } }

  // the word in the browser tab title (and the pop-out's), so the taskbar carries it behind the broker window
  const head = show && cur && word ? `[${word} ${contract(cur).replace(' ', '')}] ` : ''
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
  }, [cur?.id, min, pip])

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

  if (!show || !cur || (hidden && !pip)) return null            // on the Validate tab the DESK itself is the full read

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
    <span className={`word fw ${VCLS[word!]}`}>{word}</span>
    <span className="mid"><span className="c">{contract(cur)}</span><span className="dot">·</span>{cur.role} · in {cur.t0.slice(0, 5)}
      {v?.clause && <><span className="dot">·</span>{v.clause}</>}
      {others.map(t => <span key={t.id}><span className="dot">·</span><button type="button" className="link" onClick={() => setPick(t.id)} title="show this trade">
        <b className={VCLS[wordOf(t)]}>{wordOf(t)}</b> {contract(t)}</button></span>)}</span>
    {btns}
  </div>
  const cls = `hv float ${min ? 'col' : 'open'}${red ? ' red' : ''}${pip ? ' in-pip' : ''}`
  const style: CSSProperties | undefined = pip ? undefined
    : pos ? { left: Math.max(0, Math.min(pos.x, window.innerWidth - W - 8)), top: pos.y, right: 'auto', bottom: 'auto', ...(min ? {} : { width: W, maxHeight: 'calc(100vh - 32px)' }) }
    : min ? undefined : { width: W, maxHeight: 'calc(100vh - 32px)' }
  const src = new URL(`/pro.html?float=${encodeURIComponent(cur.id)}`, location.href).href   // absolute: a pop-out document has no base
  const win = <div ref={box} className={cls} style={style}>
    {line}
    {msg && <p className="fine" style={{ padding: '4px 12px' }}>{msg} <button type="button" className="link" onClick={() => setMsg(null)}>dismiss</button></p>}
    {!min && <iframe ref={frame} key={cur.id} src={src} title="DESK" style={{ display: 'block', width: '100%', border: 0, height: pip ? 'calc(100vh - 44px)' : Math.min(h, window.innerHeight - 90) }} />}
  </div>
  if (pip) return <>{createPortal(win, pip.document.body)}{!hidden && <div className="hv-back">The DESK is popped out on top <button type="button" onClick={() => pip.close()}>bring it back</button></div>}</>
  return win
}
