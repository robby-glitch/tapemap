// THE TRADE TAB: the one screen where TapeMap draws a chart, the NIFTY / BANKNIFTY / SENSEX future, and on it only
// "where we are, our setup, what we look at now" (docs/trade-tab/1-inventory-and-plan.md §C). One engine, one verdict:
// every level, fight and word is the rev 6 engine's (fold.py) or her own record's; this tab positions them and
// computes nothing that decides. LIGHT only.
import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import ContractChart from './ContractChart'
import FeedBand from '../pro/FeedBand'
import LegsPanel from './legs'
import Side from './Side'
import { useFootprint, withSide } from './footprint'
import { useTape } from './tape'
import { dayBase } from './indicators'
import type { EngineLayer, PocketBar, TradeLayer, ValueLayer, ZoneEntry } from './LevelsOverlay'
import { entryPlan, markCounts } from './LevelsOverlay'
import { TRADEVIEW, useFlat, useStore, useTradeView } from './engine'
import type { EngMark, TradeView } from './engine'
import { usePivots } from './zone3'
import type { Zone3 } from './zone3'
import { wallState } from './chips'
import { palette, MONO } from '../theme'
import type { Mode } from '../theme'
import type { TapeBar, IndexKey, Interval, RotationSignal } from '../data'
import { INTERVALS } from '../data'

/** The panel down the left of the chart, in px: wide enough for the four rows without wrapping the chips. */
const CHART_SIDE_W = 270

interface Props {
  index: IndexKey
  day: string
  bars: TapeBar[]
  cursor: number | null
  stale: boolean
  loading: boolean
  /** FOCUS mode (App-owned): hides the glance bar and ANSWER band while this tab is active. */
  focus: boolean
  onFocusToggle: () => void
  onIndexChange: (k: IndexKey) => void
  /** The interval being requested (what the switcher lights up). */
  interval: Interval
  /** The interval the backend says these bars ARE; null = unknown. */
  publishedInterval: number | null
  onIntervalChange: (n: Interval) => void
  /** Her zone: the 3-minute machine, whatever this chart's interval (./zone3). */
  zone3: Zone3
}

const INDEX_KEYS: IndexKey[] = ['NIFTY', 'BANKNIFTY', 'SENSEX']

function IntervalSwitch({ pal, interval, onChange }: {
  pal: ReturnType<typeof palette>; interval: Interval; onChange: (n: Interval) => void
}) {
  return (
    <div style={{ display: 'flex', border: `1px solid ${pal.border}`, borderRadius: 4, overflow: 'hidden', width: 'fit-content' }}>
      {INTERVALS.map((n) => (
        <button key={n} onClick={() => onChange(n)} title={`${n}-minute candles`} aria-pressed={interval === n}
          style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', padding: '3px 8px', cursor: 'pointer', border: 'none',
            backgroundColor: interval === n ? pal.accent : 'transparent', color: interval === n ? pal.card : pal.textMuted,
          }}>{n}m</button>
      ))}
    </div>
  )
}

function Toggle({ pal, on, onClick, label, title }: {
  pal: ReturnType<typeof palette>; on: boolean; onClick: () => void; label: string; title: string
}) {
  return (
    <button onClick={onClick} title={title} aria-pressed={on} style={{
      fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', padding: '3px 9px', cursor: 'pointer',
      border: `1px solid ${pal.border}`, borderRadius: 4,
      backgroundColor: on ? pal.textPrimary : 'transparent', color: on ? pal.card : pal.textMuted,
    }}>{label}</button>
  )
}

/** A toggle remembered per browser. A private window keeps it for the page only. */
function useStored(key: string, dflt: boolean): [boolean, () => void] {
  const [on, setOn] = useState<boolean>(() => {
    try { const v = localStorage.getItem(key); return v == null ? dflt : v === 'on' } catch { return dflt }
  })
  const flip = () => {
    const next = !on
    try { localStorage.setItem(key, next ? 'on' : 'off') } catch { /* private window */ }
    setOn(next)
  }
  return [on, flip]
}

const hm = (t: string) => { const m = /^(\d{1,2}):(\d{2})/.exec(t); return m ? +m[1] * 60 + +m[2] : NaN }

export default function TradeTab({
  index, day, bars, cursor, stale, loading, focus, onFocusToggle, onIndexChange,
  interval, publishedInterval, onIntervalChange, zone3,
}: Props) {
  const mode: Mode = 'light'
  const pal = palette(mode)
  const footprint = useFootprint(index)
  const tape = useTape(index)
  const [flowPane, toggleFlowPane] = useStored('trade.flowpane', true)
  const [pivotsOn, togglePivots] = useStored('trade.pivots', true)     // her reference lines: seen, never deciding
  const [valueOn, toggleValue] = useStored('trade.value', false)
  const [chipsOn, toggleChips] = useStored('trade.chips', true)     // her ask: every symbol readable without the key
  const [legsOn, toggleLegs] = useStored('trade.legs', false)       // the SHADOW leg engine (/api/reader): off by default

  // ── THE ENGINE (rev 6). The flat read for this index, and the open marked trade on it from the DESK's own poller.
  const { flat, why: flatWhy } = useFlat(index)
  const desk = useStore()
  const openTrade = useMemo(() => desk.trades
    .filter((t) => t.idx === index && !t.exit_t)
    .sort((a, b) => b.t0.localeCompare(a.t0))[0] ?? null, [desk.trades, index])
  // `?tradeview=<id>`: a GET-only review of one marked trade (frozen at her exit). It never writes to her record.
  const reviewRead = useTradeView(TRADEVIEW)
  const reviewTrade = useMemo(() => desk.trades.find((t) => t.id === TRADEVIEW && t.idx === index) ?? null, [desk.trades, index])
  const shownTrade = reviewTrade ?? openTrade
  const shownFold = reviewTrade ? reviewRead : openTrade ? desk.fold[openTrade.id] ?? null : null

  // The engine stamps epoch ms; the chart's axis is the session's local midnight plus the IST clock (toCandles).
  const base = useMemo(() => dayBase(day), [day])
  const engine = useMemo<EngineLayer | null>(() => {
    if (!flat?.marks) return null
    const toChart = (ms: number) => base + ((ms + 19_800_000) % 86_400_000)
    const marks: EngMark[] = flat.marks.map((m) => ({ ...m, t: toChart(m.t) }))
    const live = cursor == null && !flatWhy && !shownTrade
    const nf = flat.next_fight
    const gu = flat.gave_up
    const gt = gu ? /^(\d{1,2}):(\d{2})(?::(\d{2}))?/.exec(gu.t) : null
    return {
      marks, walls: !shownTrade,
      flat: live ? {
        above: nf?.above?.px ?? null, below: nf?.below?.px ?? null, at: flat.at?.px ?? null,
        gaveUp: gu && gt ? { t: base + ((+gt[1] * 60 + +gt[2]) * 60 + +(gt[3] ?? 0)) * 1000, px: gu.px,
                             text: /^(BUYERS|SELLERS) GAVE UP/.test(gu.text)
                               ? `${gu.text.startsWith('BUYERS') ? 'Buyers' : 'Sellers'} ne haar maani · ${gu.px} · ${gu.t.slice(0, 5)}` : gu.text } : null,
      } : null,
    }
  }, [flat, flatWhy, cursor, shownTrade, base])

  // ── HER TRADE: the engine's view of the open marked trade on this index (or the review). The G line's colour is the
  // engine's word; W sits at W.px when the server sends it, else at K + units.basis, the rule the engine publishes.
  const trade = useMemo<TradeLayer | null>(() => {
    const hms = (t: string | null | undefined) => {
      const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?/.exec(t ?? '')
      return m ? base + ((+m[1] * 60 + +m[2]) * 60 + +(m[3] ?? 0)) * 1000 : NaN
    }
    const others = desk.trades.filter((t) => t.idx === index && t.id !== shownTrade?.id)
    const ticks = others.flatMap((t) => [
      { t: hms(t.t0), text: `Entry ${t.k} ${t.side} · ${t.t0.slice(0, 5)}` },
      ...(t.exit_t ? [{ t: hms(t.exit_t), text: `Nikle · ${t.exit_t.slice(0, 5)}` }] : []),
    ]).filter((x) => Number.isFinite(x.t))
    const v = shownFold?.ok ? (shownFold.view as TradeView | undefined) : undefined
    if (!shownTrade || !v || v.headline == null) return ticks.length ? { entry: null, G: null, steps: [], W: null, A: null, oiEvent: null, fold: null, ticks } : null
    const word = v.headline.toUpperCase()
    const color = word.startsWith('FOLD') ? '#C42B30' : word.startsWith('PAST GIVE-UP') ? '#B45309' : word.startsWith("CAN'T CHECK") ? '#8A93A1' : '#141A22'
    const basis = v.units?.basis ?? null
    const W = v.W, A = v.A
    const wpx = W ? (W.px ?? (basis != null ? W.k + basis : null)) : null
    const steps = (v.G_steps ?? []).filter((g) => !g.refused)
    const fold = (v.events ?? []).filter((e) => e.kind === 'fold' && (e as { px?: number }).px != null).pop() as ({ ts: string; px: number } | undefined)
    const oe = v.oi_event
    const st = (x: string | null | undefined) => (wallState(x) ? ` · ${wallState(x)}` : '')
    return {
      entry: v.E != null ? { t: hms(shownTrade.t0), px: v.E, chip: `Aapki entry · ${shownTrade.p0 ?? '—'}`, num: String(shownTrade.p0 ?? '') } : null,
      G: v.G && v.G.px != null ? { px: v.G.px, from: v.G.set_t ? hms(v.G.set_t) : hms(shownTrade.t0), color,
                                     chip: `Yahan galat · ${v.G.px}`, num: String(v.G.px) } : null,
      steps: steps.slice(0, -1).map((g, i) => ({ px: g.px, from: hms(g.t), to: hms(steps[i + 1].t) })),
      W: W && wpx != null ? { px: wpx, chip: `Peeche ki deewar (sahara) · ${W.k} ${W.side}${st(W.state)}`, num: `${W.k} ${W.side}` } : null,
      A: A && A.px != null ? { px: A.px, chip: `Aage ki deewar · ${A.k} ${A.side}${A.pts != null ? ` · ${A.pts} pts` : ''}${st(A.state)}`,
                               num: `${A.k} ${A.side}` } : null,
      oiEvent: oe && wpx != null ? { t: hms(oe.t), px: wpx,
                                     chip: `${oe.k ?? W?.k ?? ''} ${oe.side ?? W?.side ?? ''} writers hat gaye · ${oe.t.slice(0, 5)} (−${oe.pct}%)` } : null,
      fold: fold ? { t: hms(fold.ts), px: fold.px, chip: `FOLD yahan · ${fold.ts.slice(0, 5)}` } : null,
      ticks,
    }
  }, [shownTrade, shownFold, desk.trades, index, base])

  // ── HER ZONE: the 3-minute machine's bands and entries, on any chart interval.
  const pockets = useMemo<PocketBar[] | null>(() => {
    if (!zone3.bars.length) return null
    return zone3.bars.map((b) => ({ t: base + hm(b.t) * 60_000, d2: b.d2, d3: b.d3, u2: b.u2, u3: b.u3 }))
  }, [zone3.bars, base])
  const entries = useMemo<ZoneEntry[]>(() => {
    const out: ZoneEntry[] = []
    const chartMins = bars.map((b) => hm(b.t))
    const own = publishedInterval === 3
    for (const states of [zone3.buy, zone3.sell]) {
      for (const st of states ?? []) {
        const e = st?.entry as RotationSignal | null | undefined
        if (!e?.t) continue
        const m = hm(e.t)
        // the chart bar that contains the entry's own time
        let i = -1
        for (let k = 0; k < chartMins.length && chartMins[k] <= m; k++) i = k
        if (i < 0) continue
        out.push({ i, sig: e, label: chipsOn ? `Zone ${e.side} ${e.band} · ${e.t} · 3m` : `${e.side} ${e.band} ${e.t}${own ? '' : ' · 3m'}`,
                   known: base + (m + 3) * 60_000 })
      }
    }
    return out
  }, [zone3.buy, zone3.sell, bars, publishedInterval, base, chipsOn])

  // Reference layers. Pivots: the MAP levels' floor pivots only. Value: the ux family's session value area and HVNs
  // [I], plus the ladder record's prior days and naked POCs when this contract has them.
  const pivots = usePivots(index, day, pivotsOn)
  const value = useMemo<ValueLayer | null>(() => {
    const r = tape.reply
    if (!valueOn || !r) return null
    const u = r.ux && !r.ux.why ? r.ux : null
    const toChart = (ms: number) => base + ((ms + 19_800_000) % 86_400_000)
    return {
      poc: u?.levels.session?.poc ?? null, vah: u?.levels.session?.vah ?? null, val: u?.levels.session?.val ?? null,
      hvn: (u?.levels.nodes ?? []).filter((n) => n.kind === 'HVN').map((n) => n.p),
      prior: r.levels.prior.map((p) => ({ day: p.day, poc: p.poc })),
      naked: r.levels.naked.map((n) => ({ day: n.day, poc: n.poc, to: n.touched_t != null ? toChart(n.touched_t) : null })),
    }
  }, [valueOn, tape.reply, base])

  // Her P / A / E / C with the side the extension paints them in (joined from /api/tape's ofd marks).
  const marks = useMemo(() => {
    const ev = withSide(footprint.events, tape.reply?.marks.ofd)
    const row = tape.reply?.rowSize ?? null
    if (!ev || row == null) return ev
    const iv = publishedInterval ?? 5
    return ev.map((e) => {
      if (e.kind !== 'trap' || e.p == null || !e.side) return e
      // Labelling, not a verdict, and no look-ahead: only the chart's bars already CLOSED at the P's time (the up-to-12
      // before it, at least 3). A buyers' P is "top ban sakta" within max(2 × rowSize, 0.25 × their range) of their
      // highest high; a sellers' P, of their lowest low. Anywhere else it is a "chhota trap".
      const prior = bars.filter((b) => hm(b.t) + iv <= hm(e.t)).slice(-12)
      if (prior.length < 3) return { ...e, swing: null }
      const hi = Math.max(...prior.map((b) => b.h)), lo = Math.min(...prior.map((b) => b.l))
      const tol = Math.max(2 * row, 0.25 * (hi - lo))
      const swing = e.side > 0 ? (hi - e.p <= tol ? 'top' : null) : (e.p - lo <= tol ? 'bottom' : null)
      return { ...e, swing } as typeof e
    })
  }, [footprint.events, tape.reply, bars, publishedInterval])

  // ── WHAT IS NOT ON THE CHART, one line, only what applies (three absences, never one).
  const notShown = useMemo(() => {
    const out: string[] = []
    if (!zone3.buy && !zone3.sell) out.push(`your zone: could not check — ${zone3.why || 'no 3-minute machine'}`)
    const plan = entryPlan(entries)
    if (plan.unexpected) out.push(`zone entries: ${plan.unexpected} withheld — the backend sent ${plan.why}, which the zone machine cannot emit`)
    if (!flat) out.push(`engine levels and fights: ${flatWhy ?? 'could not check'}`)
    else if (cursor != null) out.push('NEXT FIGHT and your trade\'s G / W / A: live only, not shown while replaying')
    // P3: with the GoCharting tape DEAD or STALLED, everything read off it is CAN'T CHECK with that reason; what is drawn is the
    // record up to the last GoCharting bar, never live. Upstox-based layers (value, the engine's levels) keep working and say so.
    const feed = flat?.feed
    if (feed?.alarm) {
      out.push(`your P A E C: could not check — ${feed.chip ?? feed.state} · drawn only up to the last GoCharting bar ${feed.last_bar ?? '?'}, not live`)
      out.push(`GoCharting bars, stacks and the Flow pane: could not check — ${feed.chip ?? feed.state} · Upstox reads continue`)
    } else if (footprint.events == null) out.push(`your P A E C: ${footprint.why}`)
    else {
      const mc = markCounts(marks)
      if (!footprint.events.length) out.push(footprint.why ? `your P A E C: could not check — ${footprint.why}` : 'your P A E C: checked, none in the record')
      else if (mc.offLevel) out.push(`${mc.offLevel} A/E away from a named level (not drawn, as on GoCharting)`)
    }
    if (flowPane && publishedInterval !== 5 && publishedInterval !== 15) out.push(`Flow pane: not shown at ${publishedInterval ?? '?'}m — the record is 5-minute`)
    if (!flowPane) out.push('Flow pane: off')
    if (!pivotsOn) out.push('Pivots: off')
    else if (pivots && !pivots.length) out.push('Pivots: could not check — the payload carries none')
    if (!valueOn) out.push('Value: off')
    else if (!tape.reply) out.push(`Value: ${tape.why}`)
    else {
      if (!tape.reply.ux || tape.reply.ux.why) out.push(`Value: could not check — ${tape.reply.ux?.why ?? 'no ux family in the reply'}`)
      if (!tape.reply.levels.prior.length) out.push(`Value, prior days: ${tape.reply.levels.prior_why ?? 'checked, none'}`)
    }
    return out
  }, [zone3, entries, flat, flatWhy, cursor, footprint, marks, flowPane, publishedInterval, pivotsOn, pivots, valueOn, tape])

  const at = cursor == null ? bars.length - 1 : Math.max(0, Math.min(cursor, bars.length - 1))
  const [hover, setHover] = useState<number | null>(null)
  const handleHover = (i: number | null) => {
    if (i == null || !bars.length) { setHover(null); return }
    const maxIdx = bars.length - 1
    let idx = Math.max(0, Math.min(i, maxIdx))
    if (cursor != null) idx = Math.min(idx, Math.max(0, Math.min(cursor, maxIdx)))
    setHover(idx)
  }

  // The chart column is a full screenful (the page scrolls); the height is a pure function of the window, so a
  // measure taken mid-scroll can never latch (CHECKLIST E6). It MUST be a definite height: ContractChart resolves its
  // own height as a percentage of it.
  const rootRef = useRef<HTMLDivElement>(null)
  const [availH, setAvailH] = useState<number | null>(null)
  useLayoutEffect(() => {
    const el = rootRef.current
    if (!el) return
    const measure = () => {
      const next = Math.max(320, window.innerHeight - 12)
      setAvailH((prev) => (prev != null && Math.abs(prev - next) < 2 ? prev : next))
    }
    measure()
    window.addEventListener('resize', measure)
    const parent = el.parentElement
    const ro = parent ? new ResizeObserver(measure) : null
    if (parent && ro) ro.observe(parent)
    return () => { window.removeEventListener('resize', measure); ro?.disconnect() }
  }, [index, bars.length === 0])

  // No tape: say so at full width and chart nothing. Before the first poll a healthy index also has no bars, and
  // that must read as loading, not as no session.
  if (!bars.length) {
    return (
      <div style={{ padding: 16, backgroundColor: pal.bg }}>
        {!loading && <IntervalSwitch pal={pal} interval={interval} onChange={onIntervalChange} />}
        <div style={{
          padding: '14px 18px', borderRadius: 6, marginTop: loading ? 0 : 10, backgroundColor: pal.card,
          border: `1px solid ${loading ? pal.border : pal.caution}`, color: loading ? pal.textMuted : pal.caution,
          fontSize: 12.5, fontWeight: 600,
        }}>
          {loading ? `Loading the ${index} tape…`
            : `NO ${index} TAPE: the backend has no session for this index, so there is nothing to chart. No candles is better than invented ones.`}
        </div>
      </div>
    )
  }

  const b = bars[at]
  const live = cursor == null
  const modeLabel = stale ? 'STALE' : live ? 'LIVE' : 'REPLAY'
  const modeColor = stale || !live ? pal.caution : pal.bull

  return (
    <div ref={rootRef} style={{
      display: 'flex', flexDirection: 'column', height: availH ?? 420, padding: '16px 16px 12px', gap: 8,
      overflow: 'hidden', backgroundColor: pal.bg,
    }}>
      <FeedBand feed={flat?.feed} />
      <div style={{
        display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap', padding: '7px 14px',
        backgroundColor: pal.card, border: `1px solid ${pal.border}`, borderRadius: 6,
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 9.5, letterSpacing: '0.07em', color: pal.textMuted }}>CONTRACT</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: pal.textPrimary }}>{index} FUT</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 9.5, letterSpacing: '0.07em', color: pal.textMuted }}>LAST</span>
          <span style={{ fontFamily: MONO, fontSize: 13, fontWeight: 600, color: b.c >= b.o ? pal.bull : pal.bear }}>
            {b.t} · {b.c.toFixed(1)}
          </span>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <IntervalSwitch pal={pal} interval={interval} onChange={onIntervalChange} />
          <Toggle pal={pal} on={chipsOn} onClick={toggleChips} label="CHIPS"
                  title="Har nishaan ke saath Hinglish chip: wo kya bata raha hai, number ke saath" />
          <Toggle pal={pal} on={pivotsOn} onClick={togglePivots} label="PIVOTS"
                  title="Floor pivots as grey reference lines: seen, never deciding" />
          <Toggle pal={pal} on={valueOn} onClick={toggleValue} label="VALUE"
                  title="Session value area, POC and high-volume nodes, ux family [I]; prior days when this contract has them" />
          <Toggle pal={pal} on={flowPane} onClick={toggleFlowPane} label="FLOW PANE"
                  title="Delta and CVD under the chart, ux family [I]; 5m and 15m only (the record is 5-minute)" />
          <Toggle pal={pal} on={legsOn} onClick={toggleLegs} label="LEGS · shadow"
                  title="The leg engine's record (docs/reader/8-shadow-build.md): shadow, unsigned thresholds, decides nothing" />
          <button onClick={onFocusToggle} title="Hide the glance bar and the ANSWER band on this tab, so the chart gets the height"
            style={{
              fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', padding: '3px 9px', cursor: 'pointer',
              border: `1px solid ${pal.border}`, borderRadius: 4,
              backgroundColor: focus ? pal.accent : 'transparent', color: focus ? pal.card : pal.textMuted,
            }}>FOCUS</button>
          {focus && (
            <div style={{ display: 'flex', gap: 4 }}>
              {INDEX_KEYS.map((k) => (
                <button key={k} onClick={() => onIndexChange(k)} style={{
                  fontSize: 10, fontWeight: 700, padding: '3px 8px', cursor: 'pointer', borderRadius: 4,
                  border: `1px solid ${k === index ? pal.accent : pal.border}`, backgroundColor: 'transparent',
                  color: k === index ? pal.accent : pal.textMuted,
                }}>{k}</button>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', backgroundColor: modeColor }} />
            <span style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em', color: modeColor }}>{modeLabel}</span>
          </div>
        </div>
      </div>

      {stale && (
        <div style={{ fontSize: 11, paddingLeft: 2, color: pal.caution }}>
          This index stopped updating: the chart is the last tape received, not live. Its last bar is {b.t}.
        </div>
      )}

      <div style={{ flex: 1, minHeight: 180, overflow: 'hidden', display: 'flex', gap: 10 }}>
        <div style={{
          width: CHART_SIDE_W, flexShrink: 0, borderRadius: 6, border: `1px solid ${pal.border}`, backgroundColor: pal.card,
          padding: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0,
        }}>
          <Side pal={pal} index={index}
                trade={shownTrade} fold={shownFold} review={!!reviewTrade}
                flat={flat} flatWhy={flatWhy} replaying={cursor != null} notShown={notShown} />
        </div>
        <div style={{
          flex: 1, minWidth: 0, borderRadius: 6, overflow: 'hidden', border: `1px solid ${pal.border}`, backgroundColor: pal.card,
        }}>
          <ContractChart
            index={index} day={day} bars={bars} cursor={cursor}
            mode={mode} hover={hover} onHover={handleHover} interval={publishedInterval}
            pockets={pockets} entries={entries} marks={marks}
            prints={tape.reply} flowPane={flowPane} engine={engine} trade={trade} pivots={pivots} value={value}
            chipsOn={chipsOn}
          />
        </div>
      </div>
      {legsOn && <LegsPanel pal={pal} index={index} />}
    </div>
  )
}
