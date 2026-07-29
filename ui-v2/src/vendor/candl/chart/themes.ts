import type { Theme } from '../core/types'

/** Resolved color palette used by the renderers. */
export interface ChartColors {
  bg: string
  text: string
  mutedText: string
  grid: string
  separator: string
  axisLine: string
  up: string
  down: string
  /** Default series/accent color (line + area chart, new drawings). */
  accent: string
  crosshair: string
  crosshairTagBg: string
  crosshairTagText: string
  /** Dashed guide lines (e.g. RSI 30/70). */
  guide: string
}

export const THEMES: Record<Theme, ChartColors> = {
  dark: {
    bg: '#0e1117',
    text: '#d1d4dc',
    mutedText: '#787b86',
    grid: 'rgba(255, 255, 255, 0.06)',
    separator: 'rgba(255, 255, 255, 0.14)',
    axisLine: 'rgba(255, 255, 255, 0.14)',
    up: '#26a69a',
    down: '#ef5350',
    accent: '#4361ee',
    crosshair: 'rgba(149, 152, 161, 0.9)',
    crosshairTagBg: '#4c525e',
    crosshairTagText: '#ffffff',
    guide: 'rgba(120, 123, 134, 0.5)',
  },
  light: {
    bg: '#ffffff',
    text: '#131722',
    mutedText: '#6a6d78',
    grid: 'rgba(0, 0, 0, 0.06)',
    separator: 'rgba(0, 0, 0, 0.14)',
    axisLine: 'rgba(0, 0, 0, 0.14)',
    up: '#26a69a',
    down: '#ef5350',
    accent: '#4361ee',
    crosshair: 'rgba(105, 109, 120, 0.9)',
    crosshairTagBg: '#5d606b',
    crosshairTagText: '#ffffff',
    guide: 'rgba(120, 123, 134, 0.5)',
  },
}

/** Single font used everywhere on the canvas. */
export const FONT =
  '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'

export const SMALL_FONT =
  '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
