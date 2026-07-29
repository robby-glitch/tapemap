import type { Candle } from '../core/types'
import type { IndicatorDef, IndicatorOutput } from './types'

/**
 * Volume Weighted Average Price, accumulated from the first loaded candle:
 * vwap[i] = sum(typicalPrice * volume) / sum(volume), typical = (H+L+C)/3.
 *
 * Note for integrators: because accumulation starts at the first candle in
 * the array, prepending older history (pagination) shifts every value —
 * recompute after each setData, which the standard flow already does.
 */
export const vwap: IndicatorDef = {
  id: 'vwap',
  label: 'Volume Weighted Average Price',
  shortLabel: 'VWAP',
  placement: 'overlay',
  params: [],
  compute(candles: Candle[], _params: Record<string, number>): IndicatorOutput[] {
    const values: (number | null)[] = new Array(candles.length).fill(null)
    let cumPV = 0
    let cumVol = 0
    for (let i = 0; i < candles.length; i++) {
      const c = candles[i]
      const typical = (c.high + c.low + c.close) / 3
      cumPV += typical * c.volume
      cumVol += c.volume
      // Guard zero cumulative volume (e.g. synthetic/illiquid data).
      values[i] = cumVol > 0 ? cumPV / cumVol : null
    }
    return [{ name: 'vwap', values, color: '#E91E63' }]
  },
}
