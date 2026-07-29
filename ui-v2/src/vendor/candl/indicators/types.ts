import type { Candle } from '../core/types'

/** 'overlay' renders on the price pane; 'pane' gets its own sub-pane below. */
export type IndicatorPlacement = 'overlay' | 'pane'

export type PlotStyle = 'line' | 'histogram'

export interface IndicatorOutput {
  name: string // e.g. "basis", "upper", "signal"
  values: (number | null)[] // MUST be aligned 1:1 with the input candles array
  color: string // CSS color
  style?: PlotStyle // default 'line'
}

export interface IndicatorParam {
  key: string
  label: string
  default: number
  min?: number
  max?: number
  step?: number
}

export interface IndicatorDef {
  id: string // e.g. "rsi"
  label: string // e.g. "Relative Strength Index"
  shortLabel: string // e.g. "RSI"
  placement: IndicatorPlacement
  params: IndicatorParam[]
  /** Fixed y-range for pane indicators (e.g. [0, 100] for RSI). Omit for auto. */
  range?: [number, number]
  compute(candles: Candle[], params: Record<string, number>): IndicatorOutput[]
}
