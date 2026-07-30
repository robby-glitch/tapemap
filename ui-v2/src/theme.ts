import { useState } from 'react'

// Design tokens. Colour carries exactly one meaning each: brass is STRUCTURE
// (levels, walls, pins, σ-bands, ATM, positive GEX), green/red are DIRECTION
// only. Before that rule, purple meant "spring" while green/red also meant
// up/down, so hue resolved to neither.
export const T = {
  bg: '#0B0E14',
  card: '#141926',
  inset: '#1B2130',
  border: 'rgba(255,255,255,0.07)',
  textPrimary: '#E8EDF5',
  textSecondary: '#9AA7BD',
  textMuted: '#5D6B84',
  bull: '#2EC27E',          // direction only
  bear: '#FF5F6B',          // direction only
  caution: '#FFBF00',
  accent: '#E0A852',        // structure: levels, walls, pins, regime
} as const

/**
 * Light palette — copied verbatim from the approved mockup ("Contract Tape —
 * narration on the chart", artifact 53ed3308, published 2026-07-29). Same
 * keys as `T` so components can hold either. `bull`/`bear`/`accent` use the
 * mockup's darkened up/down/brass values — the dark palette's #2EC27E /
 * #FF5F6B / #E0A852 fail against this white surface. `caution` borrows the
 * mockup's dimmer brass variant since the mockup gives no separate amber.
 */
export const TL = {
  bg: '#F7F8FA',
  card: '#FFFFFF',
  inset: '#FBFCFD',
  border: '#E3E7ED',
  textPrimary: '#141A22',
  textSecondary: '#5C6675',
  textMuted: '#98A2B0',
  bull: '#1B8A38',
  bear: '#C42B30',
  caution: '#B98F45',
  accent: '#A9762A',
} as const

export type Mode = 'light' | 'dark'

/** Look up the active palette by mode — the only place a component should
 *  branch on mode to reach a colour. */
export function palette(m: Mode) {
  return m === 'light' ? TL : T
}

/** For the chart engine's `setSettings` — candle up/down colour per mode. */
export const CHART_UP = { light: '#1B8A38', dark: '#2EC27E' } as const
export const CHART_DOWN = { light: '#C42B30', dark: '#FF5F6B' } as const

/** Persisted mode toggle, defaulting to light: the operator reads charts in
 *  Kite on the light theme and reported the dark build as unreadable. */
export function useMode(): [Mode, (m: Mode) => void] {
  const [mode, setMode] = useState<Mode>(() =>
    (localStorage.getItem('tape.mode') as Mode) || 'light')
  const set = (m: Mode) => { localStorage.setItem('tape.mode', m); setMode(m) }
  return [mode, set]
}

/** Tabular monospace, so digits do not jitter as prices tick. */
export const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
