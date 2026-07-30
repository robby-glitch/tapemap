import { createContext, createElement, useContext, useState } from 'react'
import type { ReactNode } from 'react'

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
  // The ink an rgba() wash is mixed from — hairlines, hover borders, faint
  // gridlines. On a dark surface those washes are white; on a white surface
  // they must be dark or they vanish entirely. Each call site still chooses
  // its own alpha, which is what gives every hairline its own weight.
  ink: '#FFFFFF',
  // A strike price is structure, but a *different* structure from a wall or a
  // pin, so it carries its own paler brass. Was an inline '#E8C15A' in two
  // places; on white that hue reads as highlighter, hence the light variant.
  strike: '#E8C15A',
} as const

/**
 * Light palette — from the approved mockup ("Contract Tape — narration on the
 * chart", artifact 53ed3308, published 2026-07-29). Same keys as `T` so
 * components can hold either. `bull`/`bear`/`accent` use the mockup's
 * darkened up/down/brass values — the dark palette's #2EC27E / #FF5F6B /
 * #E0A852 fail against this white surface.
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
  // and the ANSWER band's chips, 37 elements on the first screen alone. This
  // value is 4.7:1 and still ranks below textSecondary's 6.6:1, so the
  // primary → secondary → muted hierarchy survives.
  textMuted: '#6B7482',
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

export type Mode = 'light' | 'dark'

/** What a component may hold: either palette, keys only, values widened to
 *  `string`. `typeof T` will not do — `as const` makes every value a literal
 *  type, so the dark palette's own hexes would be the only assignable ones. */
export type Palette = { readonly [K in keyof typeof T]: string }

/** Look up the active palette by mode — the only place a component should
 *  branch on mode to reach a colour. */
export function palette(m: Mode): Palette {
  return m === 'light' ? TL : T
}

/** Split a palette hex into the `r,g,b` triplet an `rgba()` wash needs. Only
 *  ever called on a palette value: a colour that is not in the palette has no
 *  business acquiring an alpha channel here. */
export function rgbOf(hex: string): string {
  const n = parseInt(hex.slice(1), 16)
  return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`
}

/** For the chart engine's `setSettings` — candle up/down colour per mode.
 *  Light pair: Kite/TradingView default pair, operator request 2026-07-30 —
 *  the operator reads the real tape in Kite, so the candles must be the same
 *  green/red there and here. Dark pair stays on this app's own palette. */
export const CHART_UP = { light: '#26a69a', dark: '#2EC27E' } as const
export const CHART_DOWN = { light: '#ef5350', dark: '#FF5F6B' } as const

/* ── Mode: one value for the whole app ──────────────────────────────────────
   This was a plain hook, so every caller got its OWN copy of the state. With
   only TradeTab calling it that was invisible; the moment the shell needed the
   mode too, two independent copies would drift and the toggle would repaint
   the chart while leaving the page around it dark. A context is the honest
   fix: one state, mounted once, every consumer reading the same value.      */

const ModeCtx = createContext<[Mode, (m: Mode) => void] | null>(null)

/** Light unless 'dark' was explicitly stored. Reads a corrupt value as light
 *  rather than passing it through as a Mode it is not. */
function storedMode(): Mode {
  return localStorage.getItem('tape.mode') === 'dark' ? 'dark' : 'light'
}

/** Mirror the mode onto <html data-mode> so index.css — which owns the page
 *  background, the body text colour and the scrollbar — can follow it. Applied
 *  during render as well as on change, so the first paint is already correct
 *  and dark never flashes behind a light app. */
function applyMode(m: Mode) {
  document.documentElement.setAttribute('data-mode', m)
}

/** Mount once, above everything that paints. Owns the persisted mode. */
export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>(() => { const m = storedMode(); applyMode(m); return m })
  const set = (m: Mode) => { localStorage.setItem('tape.mode', m); applyMode(m); setMode(m) }
  return createElement(ModeCtx.Provider, { value: [mode, set] }, children)
}

/** Persisted mode toggle, defaulting to light: the operator reads charts in
 *  Kite on the light theme and reported the dark build as unreadable. */
export function useMode(): [Mode, (m: Mode) => void] {
  const ctx = useContext(ModeCtx)
  if (!ctx) throw new Error('useMode() outside <ModeProvider> — mount it in main.tsx')
  return ctx
}

/** The active palette. What most components actually want. */
export function usePalette(): Palette {
  return palette(useMode()[0])
}

/** Tabular monospace, so digits do not jitter as prices tick. */
export const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
