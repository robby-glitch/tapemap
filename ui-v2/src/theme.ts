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

/** Tabular monospace, so digits do not jitter as prices tick. */
export const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
