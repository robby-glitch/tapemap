// Host page for the /proto spike. THROWAWAY — delete with the directory.
//
// Step 1 deliberately renders NO CHART. Before a single candle is drawn, the
// page has to prove it is holding the bars it thinks it is holding, and that
// the time stamps handed to lightweight-charts read as true IST. Every number
// below is printed verbatim from the payload so the axis check (once the chart
// lands in Step 2) is a comparison against something on screen, not a memory.
//
// The whole rubric lives in the plan; the two rows this file serves are:
//   - "time axis reads true IST all session, machine-timezone independent"
//   - rotation anchoring, via the named-signal line

import { useCallback, useMemo, useState } from 'react'
import { MONO, useMode, usePalette } from '../theme'
import { dayPrecision } from '../trade/indicators'
import { ascentWhy, firstStampIso, toUtcTimes } from './protoTime'
import { readFixture, type FixtureView } from './protoFixture'
import ProtoChart from './ProtoChart'
import ProtoDraw from './ProtoDraw'
import type { MapLevel, RotationSignal, TapeBar } from '../data'

interface Props {
  day: string
  bars: TapeBar[]
  rotation: (RotationSignal | null)[] | null
  rotationWhy: string
  /** Verbatim from App.tsx's `tradeLevels` — the same array TradeTab passes to
   *  ContractChart, so it is already futures-frame. A fixture carries no MAP
   *  layer, so levels stay LIVE even when bars come from a file; the header
   *  says so rather than letting the mismatch pass silently. */
  levels: MapLevel[]
}

export default function ProtoTab({ day, bars, rotation, rotationWhy, levels }: Props) {
  const pal = usePalette()
  const [mode] = useMode()
  const [fixture, setFixture] = useState<FixtureView | null>(null)
  // Bar index under the crosshair. Verification plumbing for time-axis check
  // #2: the payload's own "HH:MM" for the hovered bar, printed where it can be
  // compared against the axis label the library drew.
  const [hover, setHover] = useState<{ i: number | null; t: number | null }>({ i: null, t: null })

  // Live unless a fixture has been loaded. The source is named in the header
  // because a screenshot of one must never be mistaken for the other — the
  // whole point of the exercise is a decision made on evidence.
  const src: FixtureView = fixture ?? { day, bars, rotation, rotationWhy }

  const times = useMemo(() => toUtcTimes(src.day, src.bars), [src.day, src.bars])
  const ascent = useMemo(() => ascentWhy(times, src.bars), [times, src.bars])

  // The most recent signal, not the first: it is the one nearest the right
  // edge, so it stays on screen at the default zoom and can be eyeballed
  // without panning. Named explicitly so the anchor check is falsifiable.
  const anchor = useMemo(() => {
    if (!src.rotation) return null
    for (let i = src.rotation.length - 1; i >= 0; i--) {
      const r = src.rotation[i]
      if (r) return r
    }
    return null
  }, [src.rotation])

  const onPick = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) setFixture(await readFixture(f))
  }, [])

  const n = src.bars.length
  const rotN = src.rotation ? src.rotation.reduce((a, r) => a + (r ? 1 : 0), 0) : 0
  const anchorLevel = anchor ? src.bars[anchor.i]?.[anchor.band] : undefined

  const line = (label: string, value: string, tone?: string) => (
    <div style={{ display: 'flex', gap: 10, padding: '2px 0' }}>
      <span style={{ color: pal.textMuted, minWidth: 132 }}>{label}</span>
      <span style={{ color: tone ?? pal.textPrimary }}>{value}</span>
    </div>
  )

  return (
    <div style={{ padding: 16, fontFamily: MONO, fontSize: 12, color: pal.textPrimary }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <strong style={{ color: pal.accent, letterSpacing: 0.5 }}>PROTO — lightweight-charts spike</strong>
        <span style={{ color: pal.textMuted }}>throwaway; delete src/proto/ when the verdict is recorded</span>
      </div>

      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14,
        padding: '8px 10px', border: `1px solid ${pal.border}`, borderRadius: 4,
      }}>
        <span style={{ color: fixture ? pal.caution : pal.bull }}>
          SOURCE {fixture ? 'FIXTURE' : 'LIVE'}
        </span>
        <input type="file" accept=".json,application/json" onChange={onPick}
               style={{ color: pal.textSecondary, fontFamily: MONO, fontSize: 11 }} />
        {fixture && (
          <button onClick={() => setFixture(null)}
                  style={{
                    fontFamily: MONO, fontSize: 11, cursor: 'pointer',
                    color: pal.textPrimary, background: pal.inset,
                    border: `1px solid ${pal.border}`, borderRadius: 3, padding: '3px 8px',
                  }}>
            back to live
          </button>
        )}
      </div>

      {n === 0 ? (
        <div style={{ color: pal.caution }}>
          no bars — {fixture ? 'this fixture carried none' : 'the live tape has not arrived yet'}
        </div>
      ) : (
        <>
          {line('bars', String(n))}
          {line('payload clock', `${src.bars[0].t} → ${src.bars[n - 1].t}`)}
          {line('day', `"${src.day}" (${dayPrecision(src.day)})`)}
          {/* THE axis proof. For a 09:15 first bar this must read ...T09:15:00.000Z.
              Anything else and lightweight-charts will render the axis in the
              wrong frame — the 5:30 bug protoTime.ts exists to prevent. */}
          {line('stamp[0] as ISO', firstStampIso(times),
                firstStampIso(times).includes(`T${src.bars[0].t}:00.000Z`) ? pal.bull : pal.bear)}
          {line('ascent', ascent || 'OK', ascent ? pal.bear : pal.bull)}
          {/* Levels come from the LIVE MAP layer, which a cached bar payload
              has no counterpart for. Drawing today's pivots over a fixture's
              bars would be a quiet lie, so a fixture withholds them and says
              so — the same bargain every other panel makes. */}
          {line('levels', fixture
            ? 'withheld — a fixture carries bars but no MAP layer'
            : `${levels.length} drawn (${levels.filter((l) => l.kind === 'pivot').length} pivots)`,
            fixture ? pal.caution : pal.textPrimary)}
          {line('rotation', src.rotation
            ? `${rotN} / ${n} bars`
            : `withheld — ${src.rotationWhy || 'no reason given'}`,
            src.rotation ? pal.textPrimary : pal.caution)}
          {anchor && line('anchor check',
            `rot[i=${anchor.i}] t=${anchor.t ?? '—'} ${anchor.side} ${anchor.band}`
            + ` @ ${Number.isFinite(anchorLevel) ? anchorLevel : 'level missing on that bar'}`,
            pal.accent)}
          {/* Time-axis check #2, and the one that actually closes the frame
              question. The left half is the payload's own clock for the bar
              under the crosshair; the right half is the timestamp
              lightweight-charts holds for that same point — the value it
              formats onto its axis. They must name the same minute. */}
          {line('hover', hover.i == null
            ? 'move the crosshair over a candle'
            : `i=${hover.i} · payload says ${src.bars[hover.i]?.t ?? '—'}`
              + ` · LWC holds ${hover.t == null ? '—' : new Date(hover.t * 1000).toISOString()}`,
            hover.i == null ? pal.textMuted
              : (hover.t != null && src.bars[hover.i]
                  && new Date(hover.t * 1000).toISOString().includes(`T${src.bars[hover.i].t}:00`))
                ? pal.bull : pal.bear)}
        </>
      )}

      {n > 0 && !ascent && (
        <div style={{ marginTop: 14, border: `1px solid ${pal.border}`, borderRadius: 4 }}>
          <ProtoChart bars={src.bars} times={times} rotation={src.rotation}
                      levels={fixture ? [] : levels} mode={mode}
                      onHover={(i, t) => setHover({ i, t })} />
        </div>
      )}
      {n > 0 && !!ascent && (
        <div style={{ marginTop: 14, color: pal.bear }}>
          chart withheld — the stamps are not plottable ({ascent})
        </div>
      )}

      {n > 0 && (
        <div style={{ marginTop: 22 }}>
          <div style={{ marginBottom: 8, color: pal.accent }}>
            CANDL — drawing toolbar
            <span style={{ color: pal.textMuted, marginLeft: 10 }}>
              the other engine, for the one thing lightweight-charts cannot do at all
            </span>
          </div>
          <ProtoDraw day={src.day} bars={src.bars} mode={mode} />
        </div>
      )}

      <div style={{ marginTop: 18, color: pal.textMuted, lineHeight: 1.6 }}>
        Step 2: candles + VWAP only. The OI pane, the σ envelope and the
        rotation pill are Proofs 2, 1 and 3 and land one at a time, so a failure
        can be attributed to one thing. Nothing here is trustworthy unless the
        ISO stamp matches the payload clock and hover matches the axis label.
      </div>
    </div>
  )
}
