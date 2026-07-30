// Tape Chart Phase 2 — the day-shape ribbon (spec §6: "the ribbon beneath
// the chart (one tick per candle, height by tier) so the day's shape reads
// at a glance"). Presentation only: tier and tone are read straight off the
// `Narration` the engine already produced (trade/narration.ts); nothing here
// computes a market analytic.
import { palette } from '../theme'
import type { Mode } from '../theme'
import type { Narration, Tier } from './narration'

interface Props {
  mode: Mode
  narrs: (Narration | null)[]
  cursor: number | null
  hover: number | null
  onHover: (i: number | null) => void
  onScrub?: (i: number) => void
}

// Fixed track height so the row's own box never reflows as tiers change —
// only the tick inside it grows, anchored to the bottom.
const TRACK_H = 20
const TIER_H: Record<Tier, number> = { 0: 3, 1: 6, 2: 11, 3: 16 }

// Bars after the replay cursor are the hidden future — dimmed like every
// other future element in this app (ContractChart's own candles, per Task 5).
const FUTURE_OPACITY = 0.25
// Tier-0 (no event) ticks stay visible but recede, so a quiet stretch of the
// day still reads as "quiet" rather than disappearing outright.
const QUIET_OPACITY = 0.45

function tickColor(pal: ReturnType<typeof palette>, narr: Narration | null): string {
  if (!narr) return pal.textMuted
  switch (narr.tone) {
    case 'bull': return pal.bull
    case 'bear': return pal.bear
    case 'structure': return pal.accent
    default: return pal.textMuted
  }
}

export default function Ribbon({ mode, narrs, cursor, hover, onHover, onScrub }: Props) {
  const pal = palette(mode)

  return (
    <div
      style={{ display: 'flex', alignItems: 'flex-end', height: TRACK_H, gap: 1, width: '100%' }}
      onMouseLeave={() => onHover(null)}
    >
      {narrs.map((narr, i) => {
        const tier: Tier = narr ? narr.tier : 0
        const isFuture = cursor != null && i > cursor
        const isCursor = cursor != null && i === cursor
        const isHover = hover === i

        // Causality wins over hover: a hidden future bar must never render
        // at full strength, brightened or not.
        const opacity = isFuture ? FUTURE_OPACITY : isHover ? 1 : tier === 0 ? QUIET_OPACITY : 1

        return (
          <div
            key={i}
            onMouseEnter={() => onHover(i)}
            onClick={onScrub ? () => onScrub(i) : undefined}
            title={narr ? narr.kind : 'no event on this bar'}
            style={{
              flex: '1 1 0', minWidth: 1,
              height: TIER_H[tier],
              backgroundColor: tickColor(pal, narr),
              opacity,
              outline: isCursor ? `1px solid ${pal.accent}` : 'none',
              outlineOffset: 0,
              cursor: onScrub ? 'pointer' : 'default',
            }}
          />
        )
      })}
    </div>
  )
}
