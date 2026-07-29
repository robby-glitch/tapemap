// CandL Charts — a data-agnostic canvas charting library.
//
// Bring your own data: create the engine, feed it a Candle[] (and live ticks),
// and you get a high-performance canvas chart with 19 chart types, a large
// drawing-tool registry, technical indicators, and the experimental CandLlabs
// tools. The library NEVER fetches data — your code supplies it (from any
// exchange, broker, CSV, or the optional DataProvider contract below).

// ----- chart engine -----
export { createChartEngine } from './chart/engine'
export type { IChartEngine, ChartEngineOptions } from './chart/types'
export type { Converters, DrawEnv } from './drawings/types'

// ----- drawing tools (registry + render / hit-test) -----
export * from './drawings'

// ----- technical indicators -----
export * from './indicators'

// ----- CandLlabs experimental tools (Echoes, Oracle, Market Clock, sonifier) -----
export * as lab from './lab'

// ----- alerts + chart settings -----
// Alerts are a data-agnostic primitive: `checkAndFireAlerts` evaluates the
// alerts for ONE symbol against its latest price. Call it per symbol you have a
// price for, so alerts fire for any number of symbols at once — there's no
// single "active" symbol baked in.
export * from './alerts/types'
export { checkAndFireAlerts, ensureNotificationPermission, type CheckAndFireOpts } from './alerts/notify'
export { playTune, ALERT_TUNES } from './alerts/tunes'

// ----- core value types -----
export type { Candle, Interval, SymbolInfo, Theme, NamedWatchlist } from './core/types'
export { INTERVALS, INTERVAL_MS, INTERVAL_LABELS } from './core/types'

// ----- data-provider contract (optional — implement with your own feed) -----
export type {
  DataProvider,
  TradeEvent,
  TickerUpdate,
  TickerStat,
  DepthSnapshot,
} from './data/types'
