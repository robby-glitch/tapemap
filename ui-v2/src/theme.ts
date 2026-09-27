// Design tokens. Colour carries exactly one meaning each: brass is STRUCTURE
// (levels, walls, pins, σ-bands, ATM, positive GEX), green/red are DIRECTION
// only. Before that rule, purple meant "spring" while green/red also meant
// up/down, so hue resolved to neither. LIGHT only: the operator's rule.

/**
 * Light palette — from the approved mockup ("Contract Tape — narration on the
 * chart", artifact 53ed3308, published 2026-07-29). `bull`/`bear`/`accent`
 * use the mockup's darkened up/down/brass values.
 *
 * Two values are NOT the mockup's, and each says why inline: `textMuted` and
 * `caution`. The mockup was a chart, so it only ever exercised those two on
 * chart chrome; once the whole shell went light they had to carry banner text
 * and tab labels, and both were measured in the browser at ~2.5:1 there.
 */
export const TL = {
  bg: '#F7F8FA',
  card: '#FFFFFF',
  inset: '#FBFCFD',
  border: '#E3E7ED',
  textPrimary: '#141A22',
  textSecondary: '#5C6675',
  // Deliberate deviation from the mockup, which used '#98A2B0'. Measured in
  // the browser that is 2.6:1 on white, and textMuted is not a garnish here —
  // it carries the inactive tab labels, every micro-label, the column headers
  // and the ANSWER band's chips, 37 elements on the first screen alone. The
  // previous '#6B7482' was 4.7:1 on a white card but only 4.4:1 on the
  // #F7F8FA page itself, where the tab labels actually sit. This value is
  // 5.0:1 on the page, 5.3:1 on white, and still ranks below textSecondary's
  // 6.6:1, so the primary → secondary → muted hierarchy survives.
  textMuted: '#636C7A',
  bull: '#1B8A38',
  bear: '#C42B30',
  // Was '#B98F45', the mockup's dimmer brass standing in for an amber the
  // mockup never gave. Measured on the surface it actually paints — CAUTION
  // text over its own 12% wash, i.e. #F0E9DC — that was 2.5:1, and the two
  // banners that carry it (NO <IDX> TAPE, CHAIN STALE) are the screen's
  // staleness disclosures. This amber is 5.0:1 on white and 4.0:1 on the
  // wash, and it reads orange rather than brass, so caution and accent stay
  // two different colours instead of two shades of one.
  caution: '#B45309',
  accent: '#A9762A',
  ink: '#141A22',           // = textPrimary, so washes read as ink, not soot
  strike: '#9A7A22',
} as const

/** The chart stack (ContractChart, LegChart, LevelsOverlay, Callout, Ribbon)
 *  still takes a `mode` and keys tables by it, so the type keeps both names.
 *  Nothing passes 'dark' any more. */
export type Mode = 'light' | 'dark'

/** What a component may hold: the palette's keys, values widened to
 *  `string` (`as const` would make each hex its own literal type). */
export type Palette = { readonly [K in keyof typeof TL]: string }

/** The palette. `mode` is accepted for the chart stack's calls and ignored:
 *  there is one palette, the light one. */
export function palette(_m?: Mode): Palette {
  return TL
}

/** Split a palette hex into the `r,g,b` triplet an `rgba()` wash needs. Only
 *  ever called on a palette value: a colour that is not in the palette has no
 *  business acquiring an alpha channel here. */
export function rgbOf(hex: string): string {
  const n = parseInt(hex.slice(1), 16)
  return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`
}

/** For the chart engine's `setSettings` — candle up/down colour.
 *  Kite/TradingView default pair, operator request 2026-07-30 — the operator
 *  reads the real tape in Kite, so the candles must be the same green/red
 *  there and here. The `dark` key only satisfies the chart stack's
 *  `Mode`-indexed lookups; it is never read. */
export const CHART_UP = { light: '#26a69a', dark: '#2EC27E' } as const
export const CHART_DOWN = { light: '#ef5350', dark: '#FF5F6B' } as const

/** The palette, as a hook, for the components that already call it. */
export function usePalette(): Palette {
  return TL
}

/** Tabular monospace, so digits do not jitter as prices tick. */
export const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
