// THE DESK's faces after the 2026-10-04 split (orderflow-desk docs/PANEL-DESIGN-2026-10-04/DESIGN.md §1, "one job per
// screen"): IF YOU WERE IN (four legs, before she clicks), the Float's three lines (in a trade, when the chart is hidden), and
// the out-of-the-ordinary grammar both share. The in-trade face lives on the GoCharting panel and is not drawn here, so
// HOLD / FOLD never shows in two big places. Presentation only: every word and number is the engine's or the decoder's; the
// screen counts the engine's own chips and nothing else. Styles: ./pro.css.
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { cc, FIXTURE, LEGS, legKey, type Feed, type FoldRead, type Hi, type Ifin, type Rows, type Story, type Tier, type Trade, type View } from './api'

export const f2 = (x: number | null | undefined) => x == null ? '—' : x.toFixed(2)
export const pct = (x: number | null | undefined) => x == null ? '' : `${x > 0 ? '+' : ''}${x}%`
export const L = (oi: number | null | undefined) => oi == null ? '—' : `${(oi / 1e5).toFixed(1)}L`
export const tradeLabel = (t: Trade) => `${t.role === 'long' ? 'long' : 'short'} ${t.k} ${t.side}`

/** the three absences never collapse: checked-and-nothing (ink) · could not check, with its reason (grey italic) · not
 *  showing you (grey). A missing read is 'none', never a zero. */
export function absence(text?: string | null, chip?: string | null): 'read' | 'cant' | 'notshown' | 'none' {
  if (!text) return 'none'
  const t = text.toLowerCase()
  if (chip === "CAN'T CHECK" || t.startsWith('could not check')) return 'cant'
  if (t.startsWith('not showing you') || t.startsWith('not shown')) return 'notshown'
  return 'read'
}
export const Abs = ({ text }: { text: string }) => <span className={`abs ${absence(text)}`}>{text}</span>

const WORDS = ['HOLD', 'PAST GIVE-UP', 'FOLD', "CAN'T CHECK"] as const
export const wordOf = (h?: string | null) => h == null ? "CAN'T CHECK" : WORDS.find(w => h.toUpperCase().startsWith(w)) ?? h
export const WCLS: Record<string, string> = { HOLD: 'hold', 'PAST GIVE-UP': 'past', FOLD: 'fold', "CAN'T CHECK": 'cant' }
const ROWS: [keyof Rows, string][] = [['zone', 'ZONE'], ['flow', 'FLOW'], ['oi', 'OI'], ['vpin', 'VPIN']]
/** the engine's four chips as a count, never a %: behind you / against you / could not check */
export function rowCount(rows?: Rows | null) {
  const of = (c: string) => ROWS.filter(([k]) => rows?.[k]?.chip === c).map(([, n]) => n)
  return { with: of('WITH'), against: of('AGAINST'), cant: ROWS.filter(([k]) => !rows?.[k]?.chip || rows[k].chip === "CAN'T CHECK").map(([, n]) => n) }
}

// ---- KYA BADLA: the out-of-the-ordinary grammar (the same table the panel reads). RED act now · AMBER look now · BLUE in
// your favour. A highlight carries "kya badla · HH:MM · what", stays 3 minutes or until clicked, then fades. Never blinks.
const HOLD_MS = 180000
const RANK: Record<Tier, number> = { red: 0, amber: 1, blue: 2 }
const hkey = (h: Hi) => `${h.tier}|${h.kind}|${h.time}|${h.what}`
/** the clock highlights age on: the wall clock live; in the fixture viewer, the fixture's own moment */
export const clockOf = (st?: Story | null) => FIXTURE && st?.now_ms ? st.now_ms : Date.now()
/** the decoder's read is current when the extension posted in the last 90 s; older is "could not check", never a stale count */
export const storyStale = (st: Story | null | undefined, now: number) => !!st?.now_ms && now - st.now_ms > 90000

type Snap = { word: string; rows: Rows | null; feed: string | null }
/** what changed on the engine's own read between two polls, in the grammar's words (the decoder's changes come from the
 *  server, story.highlights). FOLD / PAST GIVE-UP are RED even on the first read: she must see them on arrival. */
function engineDiff(p: Snap | undefined, n: Snap, at: number, time: string, inTrade: boolean, why: string): Hi[] {
  const out: Hi[] = [], hi = (tier: Tier, kind: string, what: string) => out.push({ tier, kind, what, t_ms: at, time })
  if (n.word !== p?.word) {
    if (n.word === 'FOLD') hi('red', 'FOLD', 'FOLD — get out of your trade')
    else if (n.word === 'PAST GIVE-UP') hi('red', 'PAST GIVE-UP', 'PAST GIVE-UP')
    else if (n.word === "CAN'T CHECK" && p && p.word !== "CAN'T CHECK") hi('amber', 'CANT CHECK', `read ab CAN'T CHECK — ${why}`)
  }
  if (p && n.word !== "CAN'T CHECK") {
    const a = rowCount(p.rows), b = rowCount(n.rows)
    const lost = b.cant.filter(r => !a.cant.includes(r))
    if (lost.length) hi('amber', 'CANT CHECK', `${lost.join(', ')} ab check nahi`)
    if (b.with.length > a.with.length) hi('blue', 'ENGINE BEHIND', `saath badha: ${b.with.join(', ')} (${b.with.length} saath)`)
  }
  if (inTrade && (n.feed === 'DEAD' || n.feed === 'STALLED') && n.feed !== p?.feed) hi('red', 'FEED', `feed ${n.feed} — GoCharting ka read ruka`)
  return out
}

/** One block's highlights: the engine's changes (kept here across polls) + the server's (story.highlights, for the blocks
 *  named), the newest of a kind wins, aged off `at` (the clock: re-read every 15 s); clicking the block clears what shows. */
export function useKya(snap: Snap | null, at: number, time: string, inTrade: boolean, why: string, server: Hi[] = []): [Hi[], () => void] {
  const prev = useRef<Snap | undefined>(undefined)
  const [mine, setMine] = useState<Hi[]>([])
  const [gone, setGone] = useState<string[]>([])
  const [, tick] = useState(0)
  useEffect(() => { const t = window.setInterval(() => tick(x => x + 1), 15000); return () => window.clearInterval(t) }, [])
  const sig = JSON.stringify(snap)
  useEffect(() => {
    if (!snap) return
    const d = engineDiff(prev.current, snap, at, time, inTrade, why)
    prev.current = snap
    if (d.length) setMine(m => [...d, ...m].slice(0, 12))
  }, [sig]) // eslint-disable-line react-hooks/exhaustive-deps
  const now = at
  const seen = new Set<string>()
  const live = [...server, ...mine]
    .filter(h => now - h.t_ms <= HOLD_MS && now - h.t_ms >= -60000 && !gone.includes(hkey(h)))
    .filter(h => { const k = `${h.tier}|${h.kind}`; if (seen.has(k)) return false; seen.add(k); return true })
    .sort((a, b) => RANK[a.tier] - RANK[b.tier] || b.t_ms - a.t_ms)
  return [live, () => setGone(g => [...g, ...live.map(hkey)])]
}

/** a block with its highlight: the left bar and wash of the top tier, a "kya badla" line per change (three at most) */
export function Block({ hs, clear, className = '', children, onClick }: { hs: Hi[]; clear: () => void; className?: string; children: ReactNode; onClick?: () => void }) {
  return <div className={`blk ${className} ${hs[0] ? `hi-${hs[0].tier}` : ''}`} onClick={() => { if (hs.length) clear(); onClick?.() }}
    title={hs.length ? 'click: seen — the highlight clears' : undefined}>
    {hs.slice(0, 3).map(h => <p key={hkey(h)} className={`kya ${h.tier}`}><b>kya badla</b> · <span className="num">{h.time}</span> · {h.what}</p>)}
    {children}
  </div>
}

// ---- THE FLOAT'S BODY: the panel's top three lines, when the chart is hidden. /api/fold first (it works with the extension
// dead: the engine's word and the give-up are Upstox reads), /api/story for the decoder's sentence and count when present.
export function FloatBody({ t, r, story, feed, why }: { t: Trade; r?: FoldRead; story: Story | null; feed: Feed | null; why: string | null }) {
  const v: View | undefined = r?.ok ? r.view : undefined
  const word = wordOf(v?.headline)
  const reason = why ?? (!r ? 'checking…' : r.ok ? cc(v?.why, 'no view yet') : cc(r.why, 'the engine gave no reason'))
  const now = clockOf(story), stale = storyStale(story, now)
  const server = !stale ? (story?.highlights ?? []).filter(h => ['trade', 'feed', 'abhi', 'ledger'].includes(h.block ?? 'trade')) : []
  const at = FIXTURE ? now : Date.now()
  const [hs, clear] = useKya(r ? { word, rows: v?.rows ?? null, feed: feed?.state ?? null } : null, at, (v?.ts ?? '').slice(0, 5) || new Date(at).toTimeString().slice(0, 5), true, reason, server)
  const rest = v?.headline ? v.headline.slice(word.length).replace(/^\s*·\s*/, '') : ''
  const p = v?.prem
  const tr = story?.trade_read
  const dec = !story ? 'could not check — /api/story not read yet'
    : stale ? `could not check — the decoder last posted ${new Date(story.now_ms!).toTimeString().slice(0, 5)} (the GoCharting extension is not posting)`
    : tr ? null
    : cc(story.trade_read_why ?? (story.ok ? '/api/story carries no trade_read yet (the server predates the panel round)' : story.sentence_why), 'no decoder read')
  return <Block hs={hs} clear={clear} className="fbody">
    <p className="tradeline"><b>{t.idx} {tradeLabel(t)}</b> · in at {f2(t.p0)} · {t.t0.slice(0, 5)}{v?.ts ? <> · read {v.ts.slice(0, 8)}</> : null}</p>
    <div className={`f1 ${WCLS[word] ?? 'hold'}`}><span className="word">{word}</span>
      <span className="clause">{v ? <>{rest && <b>{rest}{v.clause ? ' · ' : ''}</b>}{v.clause}</> : <Abs text={reason} />}</span></div>
    {v && <p className="f2"><span>{v.line2 || <Abs text="could not check — no give-up line yet" />}</span>
      {p && <span className="num prem"><b>{f2(p.now)}</b> <span className={(p.pct ?? 0) > 0 ? 'up' : (p.pct ?? 0) < 0 ? 'dn' : ''}>{pct(p.pct)}</span>
        {p.peak != null && <span className="muted"> · peak {f2(p.peak)}{p.peak_t ? ` ${p.peak_t}` : ''}</span>}</span>}</p>}
    <p className="f3"><b className="k">DECODER</b>{dec ? <Abs text={dec} /> : <>
      <span className="dcnt"><b className="num a">{tr!.against}</b> khilaaf · <b className="num w">{tr!.behind}</b> saath{tr!.since ? <span className="muted"> · since {tr!.since}</span> : null}
        {' '}<span className="tag" title="the decoder's read, beside the engine's word; it changes no HOLD / FOLD (P1–P7 unsigned)">I</span></span>
      {tr!.word && <span className={`dw ${tr!.word === 'GAVE UP' ? 'red' : 'blue'}`}>{tr!.word}{tr!.word_t ? ` ${tr!.word_t}` : ''}</span>}
      {tr!.word_why && <span className="muted why">{tr!.word_why}</span>}</>}</p>
    {story?.sentence && !stale && <p className="f4">{story.asof ? <span className="num muted">{story.asof} · </span> : null}{story.sentence}</p>}
  </Block>
}

// ---- IF YOU WERE IN: the four at-the-money legs, bought and sold, at her strike. The engine's own read for a mark made now
// at the chain's premium (/api/fold/ifin); the count is the engine's four chips; no size, no odds, no GO / NO.
const dirOf = (ty: string, side: string) => (ty === 'CE') === (side === 'BUY') ? 1 : -1

export function IfinCards({ legs, k, story, pick, onPick, why }: { legs: Record<string, Ifin> | null; k: number | null; story: Story | null
                                                                   pick: { ty: string; side: string } | null; onPick: (ty: 'CE' | 'PE', side: 'BUY' | 'SELL') => void; why: string | null }) {
  const now = clockOf(story), stale = storyStale(story, now)
  const ch = !stale ? story?.chapters?.items?.filter(c => c.current).pop() : undefined
  if (k == null) return <p className="legs-none"><Abs text={why ?? 'could not check — no strike yet (the chain has not loaded; the picker on the right says why)'} /></p>
  return <div className="legs">
    {LEGS.map(([ty, side]) => <Leg key={`${legKey(ty, side)}:${k}`} ty={ty} side={side} k={k} r={legs?.[legKey(ty, side)] ?? null} ch={ch} now={now}
      on={pick?.ty === ty && pick?.side === side} onPick={() => onPick(ty, side)} why={why} />)}
  </div>
}

function Leg({ ty, side, k, r, ch, now, on, onPick, why }: { ty: 'CE' | 'PE'; side: 'BUY' | 'SELL'; k: number | null; r: Ifin | null
                                                             ch?: { name: string; start: string; side: number }; now: number; on: boolean; onPick: () => void; why: string | null }) {
  const v = r?.ok ? r.view : undefined
  const word = wordOf(v?.headline)
  const reason = why ?? (!r ? (k == null ? 'could not check — no strike yet (the chain has not loaded)' : 'checking…') : cc(r.why ?? v?.why, 'no read'))
  const at = FIXTURE ? now : Date.now()
  const [hs, clear] = useKya(r ? { word, rows: v?.rows ?? null, feed: null } : null, at, (v?.ts ?? '').slice(0, 5) || new Date(at).toTimeString().slice(0, 5), false, reason)
  const c = rowCount(v?.rows), d = dirOf(ty, side)
  const p0 = (v as (View & { p0?: number }) | undefined)?.p0 ?? v?.prem.now
  return <Block hs={hs} clear={clear} className={`leg ${on ? 'on' : ''}`} onClick={onPick}>
    <div className="lh"><b>{side === 'BUY' ? 'buy' : 'sell'} {k ?? '—'} {ty}</b>{p0 != null && <span className="num"> @{f2(p0)}</span>}
      <span className="role">{side === 'BUY' ? 'kharidaar' : 'likhne wala'} · {d > 0 ? 'upar chahiye' : 'neeche chahiye'}</span></div>
    {!v || v.headline == null ? <p className="lw cant"><span className="word">CAN'T CHECK</span> <Abs text={reason} /></p> : <>
      <p className={`lw ${WCLS[word] ?? 'hold'}`}><span className="word">{word}</span> {v.clause}</p>
      <p className="l2"><span>{v.line2 || <Abs text="could not check — no give-up yet" />}</span>
        {v.prem.at_G != null && <span className="num muted">premium there ≈ <b>{f2(v.prem.at_G)}</b> <span className="tag">I</span></span>}</p>
      <p className="cnt" title="the engine's four rows (ZONE, FLOW, OI, VPIN) as a count, never a %">
        <span className="w"><b className="num">{c.with.length}</b> saath</span><span className="a"><b className="num">{c.against.length}</b> khilaaf</span>
        {c.cant.length > 0 && <span className="c"><b className="num">{c.cant.length}</b> check nahi ({c.cant.join(', ')})</span>}
        {ch && ch.side !== 0 && <span className={`ch ${ch.side === d ? 'w' : 'a'}`} title={`abhi ka chapter ${ch.start}: ${ch.name}`}>chapter {ch.side > 0 ? '▲' : '▼'} {ch.side === d ? 'saath' : 'khilaaf'}</span>}
        {v.W && <span className="muted num">wall {v.W.k} {v.W.side} {L(v.W.oi)}</span>}</p></>}
  </Block>
}
