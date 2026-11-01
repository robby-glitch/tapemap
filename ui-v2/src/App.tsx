import { useState, useEffect, useMemo, useRef, useCallback, createContext, useContext } from 'react'
import { useLiveData, chainAgeS, CHAIN_STALE_S } from './data'
import type { IndexKey, IndexInfo, Dataset, Chain, FlowRow, RunState, TapeBar, Interval } from './data'
import { usePalette, rgbOf } from './theme'
import TradeTab from './trade/TradeTab'
import { useZone3 } from './trade/zone3'   // her zone is the 3-minute machine on every interval
import SignalsTab from './signals/SignalsTab'
import FlowTab from './flow/FlowTab'
// THE BOARD, overhaul 2026-10-03 (docs/board/BOARD-OVERHAUL-2026-10-03.md).
import Board from './board/Board'
// THE READ (read.py, /api/read; docs/review/DAY-TEST-2026-10-08.md): one held read per index, OI first -- the first
// tab and the landing screen; its one-row form heads the ANSWER band on every other tab.
import ReadTab, { ReadLine, useRead } from './read/ReadTab'
import VpinTab from './vpin/VpinTab'
import WarTab from './war/WarTab'
// RAFTAAR (27 Oct): how fast each near-money strike's writers add or cut OI, and when that changed. See src/speed/speed.ts.
import SpeedTab from './speed/SpeedTab'
import AlgoTab from './algo/AlgoTab'      // 1 Nov: the evening paper shadow of the demo + v2 algos (GET /api/algo)
// THE HOLD / FOLD WINDOW (docs/hold/PREREG-merged.md rev 4): mounted once, below, so it floats on every tab.
import Float from './pro/Float'   // her order 2026-09-29: the floating window runs the DESK's engine (rev 6), not /api/hold
// The five-state machine read — see machine.ts.
import { liveMachine, machineWord, MACHINE_WORDS, lockNote } from './machine'

// THE GlanceBar's one line per index on the Board tab, off /api/board's headline. Moved here from board/BoardRev3.tsx, the
// unmounted rev 3 board, when it was deleted (25 Oct review C8); unchanged: one gentle poll of all three, only while the Board
// tab shows; a failed poll keeps the last good line for that index and retries.
type GlanceRead = { line: string; title: string }
type BoardHead = { ok: boolean; why?: string; idx?: string; asof?: string | null; spot?: number
                   headline?: { text: string; fold: { k: number; side: string; t: string } | null } }
const GLANCE_CC = 'could not check — '
function glanceLine(b: BoardHead | null): GlanceRead {
  const f0 = (x: number) => Math.round(x).toLocaleString('en-IN')
  if (!b) return { line: GLANCE_CC + 'the backend did not answer', title: '' }
  if (!b.ok || typeof b.spot !== 'number' || !Number.isFinite(b.spot))
    return { line: GLANCE_CC + String(b.why ?? 'no board read yet').replace(/^could not check — /, ''), title: b.why ?? '' }
  const f = b.headline?.fold
  return {
    // "writers left", never "fold": on the DESK, FOLD means get out of your trade.
    line: `idx ${f0(b.spot)} · ${f ? `${f.side} writers left ${f0(f.k)} ${f.t}` : 'no writers leaving near spot'}`,
    title: `${b.idx} at ${b.asof} (the last finished minute) [I]: ${b.headline?.text ?? ''}`,
  }
}
function useBoardGlance(on: boolean): Partial<Record<IndexKey, GlanceRead>> {
  const [reads, setReads] = useState<Partial<Record<IndexKey, GlanceRead>>>({})
  useEffect(() => {
    if (!on) return
    let alive = true, retry = 0
    const load = async () => {
      // one after another, not a burst: the dev proxy drops the odd request
      // when several land at once (a 502 with an empty body, measured 23:20)
      let failed = false
      for (const k of ['NIFTY', 'BANKNIFTY', 'SENSEX'] as IndexKey[]) {
        let r: GlanceRead, bad = false
        try {
          const res = await fetch(`/api/board?idx=${k}`)
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          r = glanceLine((await res.json()) as BoardHead)
        } catch { r = glanceLine(null); bad = failed = true }
        if (!alive) return
        // a failed poll keeps the last good line for that index, and retries soon
        setReads((p) => (bad && p[k] ? p : { ...p, [k]: r }))
      }
      if (failed && alive) retry = window.setTimeout(load, 5000)
    }
    load()
    const id = window.setInterval(() => { if (!document.hidden) load() }, 60000)
    return () => { alive = false; window.clearInterval(id); window.clearTimeout(retry) }
  }, [on])
  return reads
}

// ── Tokens ───────────────────────────────────────────────────────────────────
// Colour carries exactly one meaning each. Before this, hue did two jobs at
// once — purple meant "spring", cyan meant "gamma", while green and red ALSO
// meant up and down — so it resolved to neither. Now brass is structure
// (levels, walls, pins, dealer regime) and green/red are direction only.

// ── Types ─────────────────────────────────────────────────────────────────────
// IndexKey now comes from ./data (single source of truth for the live layer).
// Nine tabs since the 25 Oct review (C2): Heat, Glass, Tape, Events, Map and Chain are cut (the 3 Oct cut list, F28).
// 'Signals' is the accumulating live RECORD — every row trigger_log.py has
// written, served by /api/signals. It is a log, not a read: it shows what
// fired and the context it fired in, and deliberately computes nothing from
// them, because no row has an outcome until `python trigger_log.py score`
// fills one. See src/signals/SignalsTab.tsx.
// 'Flow' draws the day's ORDER FLOW on a time axis — the tape events at their
// own time and price, from /api/day/record: the shape of what already
// happened. Its axis is the SESSION
// (09:15–15:30), not the record's first row: the extension replays the chart's
// loaded footprint, so events reach back before the server started.
// See src/flow/FlowTab.tsx.
// 'War' is the OI battlefield drawn over TIME — every strike a band at its own
// price, thick with what the writers added since the open, from /api/oihist. It
// sits beside OI Flow because it answers the question a ladder cannot: WHEN a
// wall was built, and whether it is still held. A front that peaked at 11.5M
// and holds 1.1M reads as a ruin here and as an ordinary small wall everywhere
// else in this app. See src/war/WarTab.tsx.
export type Tab = 'Read' | 'Board' | 'Trade' | 'Flow' | 'VPIN' | 'OI Flow' | 'War' | 'Speed' | 'Validate' | 'Signals' | 'Algo'

// ── Empty dataset (first paint, and any index never read this session) ──────
// Nothing in it is invented: a live read replaces it within one poll. Until
// then every consumer renders "not shown" — never a zero standing in for a
// price, never a placeholder read or signal (CLAUDE.md rule 6).
const NOT_SHOWN = 'not shown — no live read from the backend yet'
const EMPTY_CHAIN: Chain = {
  pcr: '—', maxPain: 0, gex: '—', squeeze: '—', strikes: [],
  mpDist: 0, gexSpot: 0, bookZone: null, inBookZone: true,
  spot: 0, expiry: '', atmStraddle: 0, aligned: true, flipPx: null, ts: '', builtAt: null,
}
const perIndex = <V,>(make: () => V): Record<IndexKey, V> =>
  ({ NIFTY: make(), BANKNIFTY: make(), SENSEX: make() })
const EMPTY: Dataset = {
  INDICES: perIndex(() => ({ price: 0, change: 0, pct: 0, state: 'not shown', arrow: '' })),
  READS: perIndex(() => ({ headline: NOT_SHOWN, timing: '', direction: '', sub: '' })),
  KEY_LEVELS: perIndex(() => []),
  ORDER_FLOW: perIndex(() => ({ main: '', mm: '', stats: [] })),
  CHAIN_DATA: perIndex(() => ({ ...EMPTY_CHAIN })),
  EVENTS_BY_IDX: perIndex(() => []),
  FOCUS_BY_IDX: perIndex(() => []),
  CHART_DATA: perIndex(() => []),
  HEAT: perIndex(() => []),
  PRESSURE: perIndex(() => []),
  MAP: perIndex(() => ({ now: 0, zoneLo: 0, zoneHi: 0, levels: [] })),
}

/** Has this index been read at all? A live price is the futures close, which
 *  is never 0 — only the empty dataset carries 0. */
const hasRead = (i: IndexInfo) => i.price > 0

const DataCtx = createContext<Dataset>(EMPTY)
function useData(): Dataset {
  return useContext(DataCtx)
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = (n: number) => n.toLocaleString('en-IN')
/** `rgba()` from a palette token — the only route by which a colour in this
 *  file acquires an alpha channel. */
const wash = (token: string, alpha: number | string) => `rgba(${rgbOf(token)},${alpha})`

// ── Sub-components ────────────────────────────────────────────────────────────

function IndexCell({ idx, data, active, onClick, read }: {
  idx: IndexKey
  data: IndexInfo
  active: boolean
  onClick: () => void
  /** The Board tab's one-line read of this index (/api/board), Board tab only. */
  read?: GlanceRead
}) {
  const pal = usePalette()
  const isUp = data.pct >= 0
  const color = Math.abs(data.pct) < 0.1 ? pal.textSecondary : isUp ? pal.bull : pal.bear
  // THE READ's held word heads each index cell; the engine's own word only when the read is not there (one headline).
  const rd = useRead().data?.indices?.[idx]
  const word = rd?.ok ? `${rd.word}${rd.arrow ? ` ${rd.arrow}` : ''}${rd.src === 'flow+fuel' ? ' · flow+fuel' : ''}` : data.state
  const wordCol = rd?.ok && rd.dir ? (rd.dir < 0 ? pal.bear : pal.bull) : rd?.ok && rd.word === 'RANGE' ? pal.accent : pal.textMuted

  return (
    <button
      onClick={onClick}
      style={{
        // #1B2130 / #141926 were the dark palette's inset and card, inlined.
        backgroundColor: active ? pal.inset : pal.card,
        // C7 (25 Oct review): no LOOK HERE and no glow -- the active cell is the only one marked
        border: active ? `1px solid ${wash(pal.ink, 0.12)}` : `1px solid ${pal.border}`,
        borderRadius: 10,
        padding: '8px 14px',
        cursor: 'pointer',
        minWidth: 180,
        textAlign: 'left',
        position: 'relative',
        transition: 'border-color 150ms, background 150ms',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: pal.textPrimary }}>{idx}</span>
        <span style={{ fontSize: 10, color: wordCol, fontWeight: rd?.ok ? 700 : 400 }}
          title={rd?.ok ? `THE READ since ${rd.since} [I]` : 'the engine word (the read is not there)'}>{word}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span className="mono" style={{ fontSize: 15, fontWeight: 600, color: pal.textPrimary }}>
          {hasRead(data) ? fmt(data.price) : '—'}
        </span>
        {hasRead(data) && (
          <span className="mono" style={{ fontSize: 11, color, fontWeight: 600 }}>
            {data.arrow} {data.pct > 0 ? '+' : ''}{data.pct.toFixed(2)}%
          </span>
        )}
      </div>
      {read && (
        <div className="mono" title={read.title} style={{
          fontSize: 10.5, lineHeight: '13px', color: read.line.startsWith('could not check') ? pal.caution : pal.textSecondary,
          maxWidth: 230, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{read.line}</div>
      )}
    </button>
  )
}

/* ── Dhan token capture ────────────────────────────────────────────────────
   Without this, an expired token means the tape stops and the only recovery
   is a terminal. Clipboard first, password field as fallback.

   The token is never logged, never echoed back, and never put in the DOM as
   text: the input is type=password, its value is cleared immediately after
   posting, and the only thing displayed is the server's own validity message.
   server.py validates it, writes .dhan_token and hot-reloads the poller.   */
const JWT_RE = /^eyJ[\w-]+\.[\w-]+\.[\w-]+$/    // client sanity; server re-validates

function TokenCapture({ tone = 'quiet' }: { tone?: 'quiet' | 'loud' }) {
  const pal = usePalette()
  const [mode, setMode] = useState<'idle' | 'busy' | 'paste'>('idle')
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const post = async (tok: string) => {
    setMode('busy')
    try {
      const r = await fetch('/api/token', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: tok }),
      })
      const j = await r.json()
      setMsg({ ok: !!j.ok, text: j.ok ? `accepted — ${j.msg}` : `rejected — ${j.msg}` })
    } catch {
      setMsg({ ok: false, text: 'could not reach the server — is it running on 8765?' })
    }
    setMode('idle')
  }

  const capture = async () => {
    let raw = ''
    try { raw = (await navigator.clipboard.readText()).trim() } catch { raw = '' }
    if (JWT_RE.test(raw)) { await post(raw); raw = ''; return }
    setMsg(null)
    setMode('paste')
    setTimeout(() => inputRef.current?.focus(), 0)
  }

  const submitPaste = async () => {
    const el = inputRef.current
    if (!el) return
    const v = el.value.trim()
    el.value = ''                    // clear before any await
    if (!v) return
    setMode('idle')
    await post(v)
  }

  const btnStyle = {
    fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em', padding: '4px 10px',
    borderRadius: 3, cursor: 'pointer', background: 'transparent',
    border: `1px solid ${tone === 'loud' ? pal.caution : pal.border}`,
    color: tone === 'loud' ? pal.caution : pal.textMuted,
  } as const

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      {mode === 'paste' ? (
        <>
          <input
            ref={inputRef} type="password" autoComplete="off" spellCheck={false}
            placeholder="paste Dhan token"
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); submitPaste() } }}
            style={{
              background: pal.inset, border: `1px solid ${pal.border}`, borderRadius: 3,
              padding: '4px 8px', color: pal.textPrimary, fontSize: 11.5, width: 190,
              outline: 'none', fontFamily: 'inherit',
            }}
          />
          <button onClick={submitPaste} style={{ ...btnStyle, borderColor: pal.accent, color: pal.accent }}>SAVE</button>
          <button onClick={() => setMode('idle')} style={btnStyle}>CANCEL</button>
        </>
      ) : (
        <button onClick={capture} disabled={mode === 'busy'} style={btnStyle}
          title="Copy the token to your clipboard and click. If the browser blocks clipboard access you get a paste field instead.">
          {mode === 'busy' ? '⟳ SAVING…' : '⟳ TOKEN'}
        </button>
      )}
      {msg && (
        <span style={{ fontSize: 11, color: msg.ok ? pal.bull : pal.bear, maxWidth: 340 }}>
          {msg.text}
        </span>
      )}
    </span>
  )
}

function GlanceBar({ active, setActive, lastUpdated, error, reads }: {
  active: IndexKey
  setActive: (k: IndexKey) => void
  lastUpdated: Date | null
  error: string | null
  /** Board tab only: each index's one-line read, under its cell. */
  reads?: Partial<Record<IndexKey, GlanceRead>>
}) {
  const { INDICES } = useData()
  const pal = usePalette()
  return (
    <div style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      backgroundColor: pal.card,
      borderBottom: `1px solid ${pal.border}`,
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      gap: 24,
      minHeight: 72,
      flexWrap: 'wrap',
    }}>
      {/* Brand. flexShrink 0 so the wordmark never compresses; the scanner
          beside it is the thing that gives way. */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 8, flexShrink: 0 }}>
        <span style={{ fontSize: 13, fontWeight: 800, letterSpacing: '0.12em', color: pal.textPrimary }}>
          TAPEMAP
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: pal.bull }}>
          <span className="live-dot" style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: pal.bull, display: 'inline-block' }} />
          LIVE
        </span>
        {lastUpdated && (
          <span className="mono" style={{ fontSize: 10, color: pal.textMuted }}>
            updated {lastUpdated.toLocaleTimeString('en-GB')}
          </span>
        )}
        {error && (
          <span style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.06em',
            color: pal.caution,
            backgroundColor: wash(pal.caution, 0.1),
            border: `1px solid ${wash(pal.caution, 0.2)}`,
            borderRadius: 4,
            padding: '1px 6px',
          }}>
            reconnecting…
          </span>
        )}
      </div>

      {/* Index scanner.
          DEFECT FIX — this group had no `flex`/`min-width`, so its min-content
          was the full 556px of three 180px-min cards and it could not give a
          pixel. The bar's own `flexWrap:'wrap'` therefore broke the LINE first:
          below ~850px CSS the whole scanner dropped to a second row at x=24,
          i.e. the price and change block landed directly under the TAPEMAP
          wordmark. `flex: 1 1 auto` + `minWidth: 0` lets the group shrink so
          its OWN inner wrap re-flows the three cards instead — the bar grows a
          row of cards rather than dumping them beneath the logo.

          The basis is 200px, not `auto`: flexbox chooses LINE BREAKS from each
          item's hypothetical main size, and with `auto` that is still the
          group's 556px max-content — so the bar kept wrapping at ~810px no
          matter how shrinkable the group was afterwards. A 200px basis holds
          the first line down to ~610px, below which a stacked bar is the right
          answer anyway. */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', flex: '1 1 200px', minWidth: 0 }}>
        {(Object.entries(INDICES) as [IndexKey, typeof INDICES[IndexKey]][]).map(([k, d]) => (
          <IndexCell key={k} idx={k} data={d} active={active === k} onClick={() => setActive(k)}
            read={reads ? reads[k] ?? { line: 'reading the board…', title: '' } : undefined} />
        ))}
      </div>

      <div style={{ marginLeft: 'auto' }}>
        <TokenCapture />
      </div>

      {/* THE READ used to be repeated here. It now lives once, in the ANSWER
          band directly below, at a scale that actually ranks it. Saying the
          same thing in four places is what made the old screen unreadable. */}
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
/* ── Trending OI ───────────────────────────────────────────────────────────
   One row per clock mark: how much call and put OI has been ADDED across the
   selected strikes since the day opened, and which way that is tilting.
   Aggregated server-side (/api/oiflow) — the minute grid behind it is a few
   hundred KB while the raw chain is ~180 MB a day. Row shape (`FlowRow`) is
   shared with the Trade tab's OI strip + zone read and lives in data.ts. */

const inr = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 0 })

function OiFlowTab({ index }: { index: IndexKey }) {
  const pal = usePalette()
  // 5, not 15: a bucket only exists once the session has run long enough to
  // produce it. Measured 2026-08-10 at 09:37 — a 15-minute grid was TWO rows,
  // and the first of those is the 09:15 baseline, which is zero by
  // construction (call/put are cumulative day OI CHANGE, so at the opening
  // bell nothing has changed yet). The table therefore read as empty for the
  // first hour of every session. Operator request; the selector still offers
  // 15/30/60 for anyone who wants the coarser read.
  const [mins, setMins] = useState(5)
  const [rows, setRows] = useState<FlowRow[]>([])
  const [avail, setAvail] = useState<number[]>([])
  const [sel, setSel] = useState<number[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  /** Why the CHAIN cannot be read, in the backend's own words. Null when it is
   *  healthy. Separate from `err`, which is this endpoint failing: the flow
   *  endpoint answers fine while the chain behind it is dead, and those are
   *  two different sentences. */
  const [chainWhy, setChainWhy] = useState<string | null>(null)

  useEffect(() => { setSel(null) }, [index])   // strike sets differ per index

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const q = `idx=${index}&interval=${mins}`
          + (sel?.length ? `&strikes=${sel.join(',')}` : '')
        const r = await fetch('/api/oiflow?' + q)
        const j = await r.json()
        if (!alive) return
        if (!j.ok) { setErr(j.error || 'unavailable'); setRows([]); return }
        setErr(null)
        // The chain's own health, published alongside the rows. An empty
        // `rows` with a DEAD chain is "we could not check", not "nothing
        // yet" — see the empty state below.
        setChainWhy(j.chain_ok === false ? (j.chain_why || 'the chain is unavailable') : null)
        setAvail(j.strikes || [])
        setRows(j.rows || [])
      } catch { if (alive) setErr('backend unreachable') }
    }
    load()
    const id = setInterval(load, 15000)
    return () => { alive = false; clearInterval(id) }
  }, [index, mins, sel])

  const toggle = (k: number) => {
    const base = sel ?? avail
    const next = base.includes(k) ? base.filter(x => x !== k) : [...base, k].sort((a, b) => a - b)
    setSel(next.length ? next : null)
  }

  const th: React.CSSProperties = {
    textAlign: 'right', padding: '7px 10px', fontSize: 10.5, fontWeight: 600,
    letterSpacing: '0.09em', textTransform: 'uppercase', color: pal.textMuted,
    borderBottom: `1px solid ${pal.border}`, whiteSpace: 'nowrap',
  }
  const td: React.CSSProperties = {
    textAlign: 'right', padding: '6px 10px', fontSize: 12,
    borderBottom: `1px solid ${wash(pal.ink, 0.035)}`, whiteSpace: 'nowrap',
  }

  return (
    <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
        <span className="micro-label">Trending OI — {index}</span>
        <select value={mins} onChange={e => setMins(+e.target.value)} style={{
          background: pal.inset, color: pal.textSecondary, fontSize: 11,
          border: `1px solid ${pal.border}`, borderRadius: 3, padding: '4px 7px',
        }}>
          {[5, 15, 30, 60].map(m => <option key={m} value={m}>{m} min</option>)}
        </select>
        <span style={{ fontSize: 11, color: pal.textMuted }}>
          {rows.length} mark{rows.length === 1 ? '' : 's'} · OI added since the open,
          summed over {(sel ?? avail).length || '—'} strikes
        </span>
        {sel && (
          <button onClick={() => setSel(null)} style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', padding: '3px 9px',
            borderRadius: 3, cursor: 'pointer', background: 'transparent',
            border: `1px solid ${pal.border}`, color: pal.textMuted,
          }}>ALL STRIKES</button>
        )}
      </div>

      {avail.length > 0 && (
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
          {avail.map(k => {
            const on = (sel ?? avail).includes(k)
            return (
              <button key={k} onClick={() => toggle(k)} className="mono" style={{
                fontSize: 10.5, padding: '3px 8px', borderRadius: 3, cursor: 'pointer',
                background: on ? wash(pal.accent, 0.12) : 'transparent',
                border: `1px solid ${on ? wash(pal.accent, 0.45) : pal.border}`,
                color: on ? pal.accent : pal.textMuted,
              }}>{k}</button>
            )
          })}
        </div>
      )}

      {err ? (
        <div style={{
          background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 12,
          padding: 20, fontSize: 13, color: pal.caution,
        }}>Trending OI unavailable — {err}. It needs the chain poller running.</div>
      ) : !rows.length && chainWhy ? (
        /* COULD NOT CHECK. The rows are empty because the chain feed behind
           them is down, so no mark is coming at the next boundary or any
           other. Saying "no marks yet" here is the lie this branch exists to
           prevent: on 2026-08-12 NIFTY's socket was dead from the open and
           this tab sent the operator away to wait for a 09:20 row that could
           never exist. The backend's own sentence is quoted, not paraphrased. */
        <div style={{
          background: pal.card, border: `1px solid ${pal.caution}`, borderRadius: 12,
          padding: 20, fontSize: 13, color: pal.caution,
        }}>
          Trending OI padha hi nahi ja saka — {index} ka chain feed neeche hai.
          <div style={{ marginTop: 6, color: pal.textSecondary, fontSize: 12.5 }}>
            {chainWhy}
          </div>
          <div style={{ marginTop: 6, color: pal.textMuted, fontSize: 12 }}>
            Ye "abhi tak koi mark nahi" nahi hai — jab tak feed wapas nahi aata,
            agle boundary par bhi koi row nahi banegi.
          </div>
        </div>
      ) : !rows.length ? (
        /* CHECKED, NOTHING YET. Only reachable with a HEALTHY chain, so the
           "wait for the boundary" promise is one this screen can keep. */
        <div style={{
          background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 12,
          padding: 20, fontSize: 13, color: pal.textMuted,
        }}>No marks yet — the first row appears at the next {mins}-minute boundary.</div>
      ) : (
        <div style={{
          background: pal.card, border: `1px solid ${pal.border}`, borderRadius: 12,
          overflowX: 'auto',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ ...th, textAlign: 'left' }}>Time</th>
                {/* Frame discipline: this LTP is the index print the chain
                    poller logs, not the futures tape the glance bar shows —
                    the two can sit 70+ points apart, so the frame is named. */}
                <th style={th}>LTP · IDX</th>
                <th style={{ ...th, textAlign: 'center' }}>Break</th>
                <th style={th}>Call OI added</th>
                <th style={th}>Put OI added</th>
                <th style={th}>Diff</th>
                <th style={{ ...th, textAlign: 'center' }}>Strength</th>
                <th style={th}>Chg in dir</th>
                <th style={th}>Dir %</th>
                <th style={th}>PCR</th>
                <th style={{ ...th, textAlign: 'center' }}>Sentiment</th>
              </tr>
            </thead>
            <tbody>
              {[...rows].reverse().map(r => {
                const bull = r.sentiment === 'BULLISH'
                const bear = r.sentiment === 'BEARISH'
                // `baseline` is the ENGINE saying this mark is the session's
                // zero point rather than a reading (chain_metrics.oi_flow):
                // call/put are cumulative day OI change, so the first mark is
                // zero by construction. The UI must not infer that from 0/0 —
                // mid-session that is a real reading of "nothing was added".
                //
                // Muted, never green/red: theme.ts reserves those for
                // DIRECTION, and the absence of a reading has no direction.
                // That also fixes NEUTRAL, which fell to the bear branch and
                // so painted red on a red wash — the one row that means "no
                // signal" was the one shouting bearish.
                const sTone = r.baseline || !(bull || bear) ? pal.textMuted
                  : bull ? pal.bull : pal.bear
                const sCol = r.diff > 0 ? pal.bull : r.diff < 0 ? pal.bear : pal.textMuted
                const dCol = (r.chg_dir ?? 0) > 0 ? pal.bull : (r.chg_dir ?? 0) < 0 ? pal.bear : pal.textMuted
                return (
                  <tr key={r.time}>
                    <td className="mono" style={{ ...td, textAlign: 'left', color: pal.textSecondary }}>{r.time}</td>
                    <td className="mono" style={td}>{r.ltp?.toFixed(2) ?? '—'}</td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      {r.brk ? (
                        <span className="mono" style={{
                          fontSize: 9.5, fontWeight: 700, padding: '2px 6px', borderRadius: 3,
                          color: r.brk === 'DHB' ? pal.bull : pal.bear,
                          background: r.brk === 'DHB' ? wash(pal.bull, 0.12) : wash(pal.bear, 0.12),
                        }}>{r.brk} {r.brk_px}</span>
                      ) : <span style={{ color: pal.textMuted }}>·</span>}
                    </td>
                    <td className="mono" style={td}>{inr(r.call)}</td>
                    <td className="mono" style={td}>{inr(r.put)}</td>
                    <td className="mono" style={{ ...td, color: sCol, fontWeight: 600 }}>{inr(r.diff)}</td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      <span className="mono" style={{
                        fontSize: 10.5, fontWeight: 700, padding: '2px 7px', borderRadius: 10,
                        color: sCol, border: `1px solid ${sCol}55`,
                      }}>{r.strength > 0 ? '+' : ''}{Math.round(r.strength * 100)}%</span>
                    </td>
                    <td className="mono" style={{ ...td, color: dCol }}>
                      {r.chg_dir == null ? '—' : (r.chg_dir > 0 ? '▲ ' : '▼ ') + inr(Math.abs(r.chg_dir))}
                    </td>
                    <td className="mono" style={{ ...td, color: dCol }}>
                      {r.chg_dir_pct == null ? '—' : `${(r.chg_dir_pct * 100).toFixed(1)}%`}
                    </td>
                    <td className="mono" style={td}>{r.pcr?.toFixed(2) ?? '—'}</td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      <span
                        title={r.baseline
                          ? 'The session’s zero point, not a reading — call and put '
                            + 'are cumulative OI change since the open, so the first mark '
                            + 'is zero by construction.'
                          : undefined}
                        style={{
                          fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                          padding: '2px 8px', borderRadius: 3,
                          color: sTone, background: wash(sTone, 0.12),
                        }}>{r.baseline ? 'BASELINE' : r.sentiment}</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      <div style={{ fontSize: 11, color: pal.textMuted, maxWidth: '78ch' }}>
        Each row is the chain <b>as at</b> that mark, not an average of the
        interval after it. Diff = put minus call; strength divides it by the
        larger leg; "chg in dir" is how far Diff moved since the previous mark.
      </div>
    </div>
  )
}

/* ANSWER band: above the tabs on every tab but Read, Board, Validate and Trade -- the price and THE READ's one row (read.py).
   Since the 25 Oct review (C1 + C4, A74) nothing else: the engine's verdict said GO up, CONTRADICTED, at 13:00 on 22 Oct into
   her 73400 CE, so the verdict, its timing and direction chips and headline, MAX PAIN / PCR / GEX / SQUEEZE, AAJ KA DIN and
   max pain as a chart level are cut. The `calls` forward log keeps writing (calls_log.py); DIN (§1o) is the day type kept. */
function AnswerBand({ index, stale }: { index: IndexKey; stale: boolean }) {
  const { INDICES } = useData()
  const pal = usePalette()
  const info = INDICES[index]
  const has = hasRead(info)
  const dirCol = info.change > 0 ? pal.bull : info.change < 0 ? pal.bear : pal.textSecondary

  return (
    <div style={{ backgroundColor: pal.bg, borderBottom: `1px solid ${pal.border}`, flexShrink: 0 }}>
      {/* Grid lives in index.css (.answer-band) because it needs a breakpoint
          and an inline style cannot carry one — see the note there. */}
      <div className="answer-band">
        <div style={{ whiteSpace: 'nowrap' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <div className="mono" style={{
              fontSize: 32, lineHeight: 1, fontWeight: 600, letterSpacing: '-0.02em',
              // a price you cannot trust must not look like one you can
              color: stale ? pal.textMuted : pal.textPrimary,
              textDecoration: stale ? 'line-through' : 'none',
            }}>
              {has ? info.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}
            </div>
            {/* Frame discipline: this is the futures tape, and OI Flow's LTP
                column is the index print — 70+ points apart some afternoons.
                Both carry their frame so neither reads as the other. */}
            <span title="Futures frame — the tape this app draws"
              style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: pal.textMuted }}>
              FUT
            </span>
          </div>
          <div className="mono" style={{ fontSize: 12, color: stale ? pal.textMuted : dirCol, marginTop: 5 }}>
            {!has ? 'not shown' : stale ? 'not live' : `${info.change > 0 ? '+' : ''}${info.change.toFixed(2)} · ${info.pct > 0 ? '+' : ''}${info.pct.toFixed(2)}%`}
          </div>
        </div>

        <div style={{ minWidth: 0 }}>
          {stale && (
            <div style={{
              fontSize: 11, letterSpacing: '0.15em', textTransform: 'uppercase',
              color: pal.bear, fontWeight: 700, marginBottom: 4,
            }}>
              No live data — do not trade from this screen
            </div>
          )}
          <ReadLine index={index} />
        </div>
      </div>
    </div>
  )
}

/* ── Machine strip ──────────────────────────────────────────────────────────
   PRODUCT.md's five-state machine, surfaced at SHELL level. Until now the
   machine's current state lived only inside Trade → SetupCheck, so from any
   other tab — or any other window — an ARM changed nothing glanceable. This
   strip renders on every tab, under the ANSWER band, and document.title
   mirrors it (see App) so the browser tab itself announces ARMED.

   It READS `run_state`; it does not run a second copy of the machine — the
   same contract SetupCheck states at its top. Side pick is SetupCheck's rule
   verbatim: the side with something happening wins, BUY (the scored side)
   wins ties, and a shown SELL is named so it can never borrow the buy rule's
   measured hit rate. All prices here are futures-frame — the same frame as
   the chart these levels are drawn on. */

/* `liveMachine`, `MACHINE_WORDS` and `machineWord` moved to ./machine.ts —
   unchanged — so every reader gets the machine the same single way this
   strip does. */

function MachineStrip({ runState, runStateWhy, runStateSell, lastBar, stale, replaying }: {
  runState: RunState[] | null
  runStateWhy: string
  runStateSell: RunState[] | null
  lastBar: TapeBar | null
  stale: boolean
  replaying: boolean
}) {
  const pal = usePalette()
  const f1 = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(1))
  const { st, showSell, bothLive } = liveMachine(runState, runStateSell)
  const current = st ? machineWord(st) : null

  // The one advancing number per state. WAITING's is the number this screen
  // has never printed: how far price is from d3.
  let detail: string
  if (stale) {
    // Distinct sentence #2: could not check. Placeholder bars must not be
    // read as a machine state.
    detail = 'koi live tape nahi — machine padh nahi sakte'
  } else if (!st) {
    // SetupCheck's own words for the same absence — one sentence, two panels.
    detail = `Setup ki haalat nahi aa rahi${runStateWhy ? ` — ${runStateWhy}` : ''}`
  } else if (current === 'BAAHAR') {
    // The LOCK opened, not a trade. See machine.ts's lockNote.
    detail = `re-fire lock khula — ${lockNote(st)} · agla setup arm ho sakta hai`
  } else if (current === 'WAITING') {
    detail = lastBar
      ? `d2 ${f1(lastBar.d2)} · u2 ${f1(lastBar.u2)} · price ${f1(lastBar.c)}`
      : 'd2 — · koi bar nahi'
  } else if (current === 'ARMED') {
    detail = `todna ${showSell ? '<' : '>'} ${f1(showSell ? st.ref_low : st.ref_high)}`
      + ` · ${st.candles_left != null ? `${st.candles_left} candle baaki` : 'window —'}`
  } else if (current === 'TRIGGERED') {
    detail = `entry hui · stop ${f1(st.stop)}`
  } else {
    // TRADE MEIN — VWAP is the first milestone, then band-to-band.
    detail = `pehla milestone VWAP ${f1(lastBar?.vwap)} · stop ${f1(st.stop)}`
  }

  const unreadable = !stale && st != null && !st.readable

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      padding: '6px 24px', backgroundColor: pal.bg,
      borderBottom: `1px solid ${pal.border}`,
    }}>
      <span className="micro-label" style={{ whiteSpace: 'nowrap' }} title="THE ZONE machine: d2→d3 buy, u2→u3 sell (CLAUDE.md rule 3) — the setup VALIDATE reads">Zone machine</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }} aria-live="polite">
        {MACHINE_WORDS.map((w, i) => {
          const lit = !stale && w === current
          return (
            <span key={w} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {i > 0 && <span aria-hidden="true" style={{ color: pal.textMuted, opacity: 0.45, fontSize: 10 }}>→</span>}
              <span style={{
                fontSize: 11, fontWeight: lit ? 700 : 500, letterSpacing: '0.07em',
                padding: '2px 8px', borderRadius: 4, whiteSpace: 'nowrap',
                // Brass, not green/red: a machine state is structure, not a
                // directional call. WAITING lights quietly — context, not
                // signal.
                color: lit ? (w === 'WAITING' ? pal.textPrimary : pal.accent) : pal.textMuted,
                border: `1px solid ${lit ? (w === 'WAITING' ? wash(pal.ink, 0.18) : wash(pal.accent, 0.55)) : 'transparent'}`,
                backgroundColor: lit && w !== 'WAITING' ? wash(pal.accent, 0.10) : 'transparent',
                opacity: lit ? 1 : 0.75,
              }}>{w}</span>
            </span>
          )
        })}
      </div>
      {showSell && st && (
        <span title="zone SELL (u2→u3) — unscored, pre-registered; no rate of any kind belongs next to it" style={{
          fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', padding: '1px 7px',
          borderRadius: 4, border: `1px solid ${pal.border}`, color: pal.textSecondary,
        }}>SELL · u2→u3</span>
      )}
      {bothLive && (
        <span style={{ fontSize: 10.5, color: pal.textSecondary }}>· SELL side bhi live hai — Trade tab dekho</span>
      )}
      <span className="mono" style={{
        fontSize: 11.5, whiteSpace: 'nowrap',
        color: stale ? pal.caution : !st ? pal.caution : current === 'WAITING' ? pal.textSecondary : pal.textPrimary,
      }}>{detail}</span>
      {unreadable && (
        <span style={{ fontSize: 10.5, color: pal.caution }}>· is bar ka read nahi mila</span>
      )}
      {replaying && (
        <span title="Replay chal raha hai — ye strip phir bhi LIVE tape padhti hai, scrub nahi" style={{
          marginLeft: 'auto', fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
          padding: '1px 7px', borderRadius: 4,
          border: `1px solid ${wash(pal.accent, 0.5)}`, color: pal.accent,
        }}>LIVE</span>
      )}
    </div>
  )
}

export default function App() {
  const pal = usePalette()
  const [activeIndex, setActiveIndex] = useState<IndexKey>('NIFTY')
  const [activeTab, setActiveTab] = useState<Tab>('Read')
  // FOCUS: while on and the Trade tab is active, hide the glance bar + ANSWER
  // band so the chart reclaims that ~417px of chrome (Kite gives the chart
  // nearly the whole viewport; this dashboard didn't). Persisted in
  // localStorage — defaults OFF so nothing changes for anyone who hasn't
  // opted in.
  const [focus, setFocusState] = useState<boolean>(() => localStorage.getItem('tape.focus') === '1')
  const setFocus = (v: boolean) => { localStorage.setItem('tape.focus', v ? '1' : '0'); setFocusState(v) }
  const focusHidesChrome = focus && activeTab === 'Trade'
  // BOARD rev 3's shell (notes §8 step 1), the Board tab ONLY: the board is
  // its own answer, so the global ANSWER band, the MACHINE strip and the
  // tape's replay bar (the board never follows it) step aside for its
  // 1536 × 577, and the GlanceBar carries each index's one-line board read.
  // Every other tab keeps all three exactly as before.
  const onBoard = activeTab === 'Board'
  // The Validate tab is its own answer too: the hold window's check never shows the engine's
  // headline (docs/hold/PREREG-merged.md §5), so the ANSWER band and the replay bar step aside
  // there, as on the Board. The MACHINE strip stays: it is her setup.
  const onValidate = activeTab === 'Validate'
  const boardReads = useBoardGlance(onBoard)
  const onRead = activeTab === 'Read'      // THE READ is its own answer: the ANSWER band steps aside there too
  const tabs: Tab[] = ['Read', 'Board', 'Trade', 'Flow', 'VPIN', 'OI Flow', 'War', 'Speed', 'Validate', 'Signals', 'Algo']
  const { data: liveData, loading, error, errorWhy, broker, intake, lastUpdated, barCount, at, dead, tapeBars,
          interval, setInterval: setInterval_ } = useLiveData(EMPTY)
  const idxDead = dead.includes(activeIndex)

  // ── Replay. scrub === null means live. Re-maps stored payloads; no refetch.
  const [scrub, setScrub] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(8)
  const nBars = barCount(activeIndex)
  /** Switching interval rebuilds the tape with a different number of bars, so
   *  a scrub index from the old one names a different minute (bar 200 of 385
   *  is 12:35; of 129 it does not exist). Drop back to live rather than
   *  silently re-point it: a replay frame that moved without being asked to is
   *  the same lie as a marker drawn one bar off. */
  const changeInterval = useCallback((n: Interval) => {
    setScrub(null)
    setPlaying(false)
    setInterval_(n)
  }, [setInterval_])
  const data = useMemo(() => at(scrub), [scrub, liveData])
  const tape = useMemo(() => tapeBars(activeIndex), [tapeBars, activeIndex, liveData])
  const zone3 = useZone3(activeIndex, interval, tape)   // the strip, the title and Trade read THIS, never a 5m re-run
  // ZONE-3M (draft §1r): one switch, one date. On a 3m chart from band_rotation.ZONE3_FROM (zone3.z3) the strip and the
  // title read the SAME machine and bands as the Trade tab's pockets and markers; otherwise today's zone.
  const zm = zone3.z3 ?? zone3
  const barTime = data.CHART_DATA[activeIndex]?.slice(-1)[0]?.time ?? '--:--'

  // A stale chain is a separate failure from a dead tape or an unreachable
  // backend: the futures tape can keep ticking normally while the option
  // poller is hung, and MAX PAIN/GEX/PCR quietly render minutes-old numbers
  // as if current. `builtAt` is the trustworthy signal for that — `null`
  // means an older backend never sent it, which must read as "unknown", not
  // "fresh", so the banner only fires once age is actually known and past
  // the threshold.
  const activeChain = data.CHAIN_DATA[activeIndex]
  const chainAge = chainAgeS(activeChain)
  const chainStale = chainAge != null && chainAge > CHAIN_STALE_S

  // Mirror the machine into the browser tab title, so ARMED is visible from
  // Kite or TradingView without TapeMap being the front window. Same state
  // pick as the strip (liveMachine — one definition). A dead tape or a dead
  // backend must NOT title-flash a placeholder machine, so those fall back to
  // the plain title.
  useEffect(() => {
    let title = 'TapeMap — Live'
    if (!error && !idxDead) {
      const { st } = liveMachine(zm.buy, zm.sell)           // the zone: her setup (rule 3), always the 3-minute machine
      if (st) {
        const w = machineWord(st)
        if (w === 'ARMED') title = `● ARMED · ${st.candles_left != null ? `${st.candles_left} baaki` : 'window —'} — TapeMap`
        else if (w === 'TRIGGERED') title = '●● TRIGGERED — TapeMap'
        else if (w === 'TRADE MEIN') title = '● TRADE MEIN — TapeMap'
        // Not "BAAHAR (vwap)" — from a browser tab that read as "you are out
        // at VWAP". The lock opening is the fact; the exit is the operator's.
        else if (w === 'BAAHAR') title = `LOCK OPEN · ${st.exit_why} — TapeMap`
      }
    }
    document.title = title
    return () => { document.title = 'TapeMap — Live' }
  }, [zm, error, idxDead])

  useEffect(() => {
    if (!playing || scrub == null) return
    const id = setInterval(() => {
      setScrub((s) => {
        if (s == null) return s
        if (s >= nBars - 1) { setPlaying(false); return s }
        return s + 1
      })
    }, Math.max(40, 1000 / speed))
    return () => clearInterval(id)
  }, [playing, speed, scrub == null, nBars])

  return (
    <DataCtx.Provider value={data}>
    <div style={{ minHeight: '100vh', backgroundColor: pal.bg, display: 'flex', flexDirection: 'column' }}>
      {/* FOCUS hides only the glance bar + ANSWER band, and only on the Trade
          tab — every safety banner below (NOT LIVE / NO {index} TAPE / CHAIN
          STALE) still renders unconditionally: buying chart pixels by hiding
          a staleness disclosure is the one trade this tool refuses to make. */}
      {!focusHidesChrome && (
        <GlanceBar active={activeIndex} setActive={setActiveIndex} lastUpdated={lastUpdated} error={error}
          reads={onBoard ? boardReads : undefined} />
      )}

      {/* A trading screen must never present stale numbers as live. The
          moment every index fails, say so at full width instead of showing a
          small "reconnecting" chip beside believable-looking prices. */}
      {error && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.bear, 0.12),
          borderBottom: `1px solid ${pal.bear}`, color: pal.bear,
          fontSize: 12.5, fontWeight: 600, letterSpacing: '0.02em',
          display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap',
        }}>
          <span style={{ marginRight: 12 }}>
            {error === 'unreachable'
              ? 'NOT LIVE — no answer from the backend on 8765, so nothing below is live '
                + '(the last good read, or not shown). Run stop.bat, then the TapeMap v2 shortcut again.'
              : `NOT LIVE — the backend is up${broker ? ` on ${broker}` : ''} but has no `
                + `session yet${errorWhy ? `: ${errorWhy}` : ''}. Nothing below is live `
                + '(the last good read, or not shown).'}
          </span>
          {/* The button only appears where it can actually change something.
              It cannot reach a backend that is not answering; and on Upstox
              server.py refuses the write outright, because the running tape
              and chain read .upstox_token and only `python upstox_auth.py`
              refreshes it. Offering it anyway is how a screen at 02:50 came
              to blame an expired Dhan token for a market that had not opened. */}
          {error === 'no-data' && broker !== 'upstox' && <TokenCapture tone="loud" />}
        </div>
      )}

      {/* One index can be down while the others are fine — say which. */}
      {!error && idxDead && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.caution, 0.12),
          borderBottom: `1px solid ${pal.caution}`, color: pal.caution,
          fontSize: 12.5, fontWeight: 600,
        }}>
          NO {activeIndex} TAPE — the backend has no session for this index, so the
          figures below are not live (the last good read, or not shown). {dead.length < 3 && 'The other indices are live.'}
        </div>
      )}

      {/* The tape can be perfectly live while the option-chain poller hangs —
          that gap is invisible unless it is called out on its own, separate
          from the "backend unreachable" banner above (which already covers
          this ground when it fires, so this stays silent then). */}
      {!error && chainStale && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.caution, 0.12),
          borderBottom: `1px solid ${pal.caution}`, color: pal.caution,
          fontSize: 12.5, fontWeight: 600,
        }}>
          CHAIN STALE — last option-chain snapshot {activeChain.ts || '--:--:--'} ({Math.floor((chainAge as number) / 60)}m old).
          OI and the chain-derived reads below are from that moment, not now.
          Candles, VWAP and the σ bands are unaffected.
        </div>
      )}

      {/* F13 (25 Oct review, A76): the record must be written. /api/health's two checks, the server's words verbatim: from 09:20
          a log with no row today (RECORDING NAHI: book, chain, ...), and after 15:30 a recorded day with no tradebook import,
          linked to the import door (pro.html's RECORD tab). On the Validate tab Validate's own band says the second. */}
      {intake?.recording && !intake.recording.ok && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.bear, 0.12),
          borderBottom: `1px solid ${pal.bear}`, color: pal.bear,
          fontSize: 12.5, fontWeight: 700, letterSpacing: '0.02em',
        }}>
          {intake.recording.text}
        </div>
      )}
      {intake?.tradebook?.due && !onValidate && (
        <div style={{
          padding: '9px 24px', backgroundColor: wash(pal.caution, 0.12),
          borderBottom: `1px solid ${pal.caution}`, color: pal.caution,
          fontSize: 12.5, fontWeight: 600,
        }}>
          tradebook aaj import nahi · <a href="/pro.html?tab=record" target="_blank" rel="noopener" style={{ color: pal.caution }}>import karo</a>
        </div>
      )}

      {/* not on Trade either (2026-09-29): its left panel is the rev 6 engine's read, and the legacy
          engine's SPENT / DON'T CHASE beside it would be a second verdict on one screen */}
      {!focusHidesChrome && !onBoard && !onValidate && !onRead && activeTab !== 'Trade' && (
        <AnswerBand index={activeIndex} stale={!!error || idxDead} />
      )}

      {/* The machine strip renders on every tab, and even under FOCUS. It is
          the product's spine, and the one row that must never be traded away
          for chart pixels. The one exception is the Board tab, by her own
          spec (BOARD rev 3 §8 step 1); the browser-tab title still mirrors
          the machine there. */}
      {!onBoard && <MachineStrip
        runState={zm.buy}
        runStateWhy={zone3.why}
        runStateSell={zm.sell}
        lastBar={zm.bars.length ? zm.bars[zm.bars.length - 1] : null}
        stale={!!error || idxDead}
        replaying={scrub != null}
      />}

      {/* Tab bar */}
      <div role="tablist" aria-label="TapeMap panels" style={{
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        padding: '0 24px',
        backgroundColor: pal.card,
        borderBottom: `1px solid ${pal.border}`,
      }}>
        {tabs.map(tab => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '12px 16px',
              fontSize: 13,
              fontWeight: activeTab === tab ? 600 : 400,
              color: activeTab === tab ? pal.textPrimary : pal.textMuted,
              backgroundColor: 'transparent',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              borderBottom: `2px solid ${activeTab === tab ? pal.accent : 'transparent'}`,
              cursor: 'pointer',
              transition: 'all 150ms',
              letterSpacing: '0.01em',
            }}
          >
            {tab}
          </button>
        ))}
        <div style={{ marginLeft: 'auto', fontSize: 11, color: pal.textMuted }}>
          <span className="mono">{lastUpdated ? lastUpdated.toLocaleTimeString('en-GB') : '—'}</span> IST
        </div>
      </div>

      {/* Replay transport. Hidden until there are bars to scrub. */}
      {nBars > 1 && !onBoard && !onValidate && !onRead && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '8px 24px',
          borderBottom: `1px solid ${pal.border}`,
          backgroundColor: scrub == null ? pal.bg : wash(pal.accent, 0.07),
        }}>
          <button
            onClick={() => {
              if (scrub == null) { setScrub(Math.max(0, nBars - 60)); setPlaying(true) }
              else setPlaying(!playing)
            }}
            title={scrub == null ? 'Replay the last hour' : playing ? 'Pause' : 'Play'}
            style={{
              width: 30, height: 26, borderRadius: 3, cursor: 'pointer',
              background: 'transparent', border: `1px solid ${pal.border}`,
              color: pal.textPrimary, fontSize: 12,
            }}
          >{playing ? '❚❚' : '▶'}</button>

          <select value={speed} onChange={(e) => setSpeed(+e.target.value)}
            style={{
              background: pal.inset, color: pal.textSecondary, fontSize: 11,
              border: `1px solid ${pal.border}`, borderRadius: 3, padding: '4px 6px',
            }}>
            {[1, 3, 8, 25].map(s => <option key={s} value={s}>{s}×</option>)}
          </select>

          <span className="mono" style={{
            fontSize: 12, color: scrub == null ? pal.textMuted : pal.accent,
            minWidth: 46, fontWeight: 600,
          }}>{barTime}</span>

          <input
            type="range" min={0} max={Math.max(0, nBars - 1)}
            value={scrub == null ? nBars - 1 : scrub}
            onChange={(e) => { setScrub(+e.target.value); setPlaying(false) }}
            aria-label="Replay position"
            style={{ flex: 1, accentColor: pal.accent, cursor: 'pointer' }}
          />

          {scrub == null ? (
            <span className="mono" style={{ fontSize: 10.5, color: pal.textMuted, letterSpacing: '0.06em' }}>
              LIVE
            </span>
          ) : (
            <button
              onClick={() => { setScrub(null); setPlaying(false) }}
              style={{
                fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
                padding: '4px 10px', borderRadius: 3, cursor: 'pointer',
                background: 'transparent', border: `1px solid ${pal.accent}`, color: pal.accent,
              }}
            >RETURN TO LIVE</button>
          )}
        </div>
      )}

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {activeTab === 'Trade'    && <TradeTab key={activeIndex} index={activeIndex} day={tape.day} bars={tape.bars}
                                              cursor={scrub}
                                              stale={idxDead || !!error} loading={loading}
                                              focus={focus} onFocusToggle={() => setFocus(!focus)}
                                              onIndexChange={setActiveIndex}
                                              interval={interval} publishedInterval={tape.interval}
                                              onIntervalChange={changeInterval}
                                              zone3={zone3} />}
        {/* Mounted only while active, which is also what stops its 30s poll:
            the tab unmounts and the interval is cleared with it. */}
        {activeTab === 'Read'     && <ReadTab reads={data.READS} />}
        {activeTab === 'Board'    && <Board key={activeIndex} index={activeIndex} />}
        {activeTab === 'Flow'     && <FlowTab index={activeIndex} />}
        {activeTab === 'VPIN'     && <VpinTab key={activeIndex} index={activeIndex} />}
        {activeTab === 'OI Flow'  && <OiFlowTab index={activeIndex} />}
        {/* Mounted only while active, which is also what stops its 30s poll. */}
        {activeTab === 'War'      && <WarTab index={activeIndex} />}
        {activeTab === 'Speed'    && <SpeedTab key={activeIndex} index={activeIndex} />}
        {/* her order 2026-09-29: Validate is the rev 6 DESK (pro.html). A frame, because pro.css styles html/body/:root. */}
        {activeTab === 'Validate' && <iframe src="/validate2/index.html" title="VALIDATE" style={{ width: '100%', height: 'calc(100vh - 190px)', minHeight: 560, border: 0, display: 'block' }} />}
        {/* No `index` prop, deliberately: the log spans all three indices and
            the operator tracks the strategy, not one tape. The tab carries its
            own index filter, which starts on ALL. */}
        {activeTab === 'Signals'  && <SignalsTab />}
        {/* No `index` prop: the algo trades both indices as one market (algo-lab/shadow/panel.json). */}
        {activeTab === 'Algo'     && <AlgoTab />}
      </div>
      <Float intake={intake} />{/* every tab, Validate too: the DESK no longer draws the in-trade face (2026-10-04) */}
    </div>
    </DataCtx.Provider>
  )
}
