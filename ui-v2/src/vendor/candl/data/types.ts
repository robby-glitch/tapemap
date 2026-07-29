import type { Candle, Interval, SymbolInfo } from '../core/types'

export interface TickerUpdate {
  symbol: string
  price: number
  changePct: number // 24h change, percent (e.g. -1.23)
}

export interface TradeEvent {
  time: number // epoch ms
  price: number
  qty: number // base-asset quantity
  side: 'buy' | 'sell' // taker side
}

/** 24h market statistics for one symbol (for the market heatmap). */
export interface TickerStat {
  symbol: string
  base: string // e.g. "BTC"
  lastPrice: number
  changePct: number // 24h percent change
  quoteVolume: number // 24h quote-asset (USDT) volume — heatmap tile size
}

/** A partial order-book snapshot (top levels), for the liquidity heatmap. */
export interface DepthSnapshot {
  bids: [price: number, qty: number][] // descending by price
  asks: [price: number, qty: number][] // ascending by price
}

/**
 * A market data source. Implementations must be usable directly from the
 * browser with no API key (public endpoints only).
 */
export interface DataProvider {
  name: string

  /** Search tradable symbols by free-text query (matches base/quote/symbol). */
  searchSymbols(query: string): Promise<SymbolInfo[]>

  /** Resolve full info for one symbol (precision etc). */
  getSymbolInfo(symbol: string): Promise<SymbolInfo>

  /**
   * Fetch up to `limit` candles ending at `endTime` (exclusive, epoch ms).
   * Omit `endTime` for the most recent candles. Returned ascending by time.
   */
  fetchCandles(symbol: string, interval: Interval, limit?: number, endTime?: number): Promise<Candle[]>

  /**
   * Subscribe to live candle updates for one symbol+interval.
   * `onUpdate` fires with the current (possibly still-open) candle.
   * Returns an unsubscribe function.
   */
  subscribeCandles(symbol: string, interval: Interval, onUpdate: (candle: Candle) => void): () => void

  /**
   * Subscribe to lightweight ticker updates (last price + 24h change)
   * for a set of symbols. Returns an unsubscribe function.
   */
  subscribeTickers(symbols: string[], onTick: (update: TickerUpdate) => void): () => void

  /**
   * Subscribe to live (aggregated) individual trades for one symbol.
   * Returns an unsubscribe function.
   */
  subscribeTrades(symbol: string, onTrade: (trade: TradeEvent) => void): () => void

  /** One-shot 24h stats for all tradable USDT spot pairs (market heatmap). */
  getAllTickers(): Promise<TickerStat[]>

  /**
   * Subscribe to partial order-book depth (top levels, refreshed live) for one
   * symbol — for the liquidity heatmap. Returns an unsubscribe function.
   */
  subscribeDepth(symbol: string, onDepth: (depth: DepthSnapshot) => void): () => void
}
