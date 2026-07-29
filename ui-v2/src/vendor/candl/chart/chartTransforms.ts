/**
 * Price-series transforms for the re-binned and derived chart types.
 *
 * Two families live here:
 *  - toHeikinAshi: a 1:1 OHLC smoothing (same bar count as the source, so it
 *    renders on the normal time axis exactly like candles).
 *  - toRenko / toLineBreak / toKagi: RE-BINNED series whose element count is
 *    independent of time. Each produces a synthetic `Candle[]` (Renko /
 *    Line Break) or a polyline (Kagi). The engine draws these on the bar-INDEX
 *    axis — one synthetic element per index slot — and the time axis only
 *    approximates: each synthetic bar carries the `time` of the SOURCE candle
 *    that completed it, so crosshair time labels stay roughly meaningful.
 *
 * All functions are pure and O(n) in the source length, so callers can simply
 * re-transform the whole loaded array on every setData / updateLast.
 */
import type { Candle } from '../core/types'

/**
 * Heikin-Ashi candles, 1:1 with the source. The classic recurrence:
 *   haClose = (o + h + l + c) / 4
 *   haOpen  = (prevHaOpen + prevHaClose) / 2  (seed: (o + c) / 2 for bar 0)
 *   haHigh  = max(h, haOpen, haClose)
 *   haLow   = min(l, haOpen, haClose)
 * Volume/time are carried through unchanged so indicators and the time axis
 * stay aligned bar-for-bar.
 */
export function toHeikinAshi(candles: Candle[]): Candle[] {
  const n = candles.length
  if (n === 0) return []
  const out: Candle[] = new Array(n)
  let prevOpen = (candles[0].open + candles[0].close) / 2
  let prevClose = candles[0].close
  for (let i = 0; i < n; i++) {
    const c = candles[i]
    const haClose = (c.open + c.high + c.low + c.close) / 4
    const haOpen = i === 0 ? (c.open + c.close) / 2 : (prevOpen + prevClose) / 2
    const haHigh = Math.max(c.high, haOpen, haClose)
    const haLow = Math.min(c.low, haOpen, haClose)
    out[i] = { time: c.time, open: haOpen, high: haHigh, low: haLow, close: haClose, volume: c.volume }
    prevOpen = haOpen
    prevClose = haClose
  }
  return out
}

/** Simple ATR(period) on close-to-close-aware true range; used to size Renko boxes. */
function atr(candles: Candle[], period: number): number {
  const n = candles.length
  if (n === 0) return 0
  let sum = 0
  let count = 0
  for (let i = 1; i < n; i++) {
    const c = candles[i]
    const prevClose = candles[i - 1].close
    const tr = Math.max(c.high - c.low, Math.abs(c.high - prevClose), Math.abs(c.low - prevClose))
    if (isFinite(tr)) {
      sum += tr
      count++
    }
  }
  if (count === 0) return 0
  // Average of the last `period` true ranges (or all if fewer).
  let tail = 0
  let taken = 0
  for (let i = n - 1; i >= 1 && taken < period; i--) {
    const c = candles[i]
    const prevClose = candles[i - 1].close
    const tr = Math.max(c.high - c.low, Math.abs(c.high - prevClose), Math.abs(c.low - prevClose))
    if (isFinite(tr)) {
      tail += tr
      taken++
    }
  }
  return taken > 0 ? tail / taken : sum / count
}

/**
 * Auto box size for Renko: 0.5 x ATR(14), floored to a small fraction of price
 * so flat/degenerate series still produce a sane, finite box. Never returns 0.
 */
export function autoRenkoBoxSize(candles: Candle[]): number {
  const n = candles.length
  if (n === 0) return 1
  const lastClose = candles[n - 1].close
  const priceFloor = Math.abs(lastClose) * 0.005 || 1 // ~0.5% of price as a safety floor
  const a = atr(candles, 14) * 0.5
  const box = a > 0 ? a : priceFloor
  return box > 0 ? box : priceFloor
}

/**
 * Renko bricks as synthetic candles. Each brick spans exactly `boxSize` in
 * price; up bricks have close > open, down bricks close < open. A reversal
 * needs 2 boxes (standard Renko). `time` on each brick is the source candle's
 * time that produced it. Returns [] when there's no data or a non-finite box.
 */
export function toRenko(candles: Candle[], boxSize: number): Candle[] {
  const n = candles.length
  if (n === 0 || !(boxSize > 0) || !isFinite(boxSize)) return []
  const bricks: Candle[] = []
  // Anchor the brick lattice to the first close.
  let base = candles[0].close
  let dir = 0 // 0 unknown, +1 last brick up, -1 last brick down
  for (let i = 0; i < n; i++) {
    const c = candles[i]
    const price = c.close
    // Emit as many bricks as the move crosses, in the appropriate direction.
    if (dir >= 0) {
      // Upward continuation (1 box) or initial move.
      while (price >= base + boxSize) {
        bricks.push({ time: c.time, open: base, high: base + boxSize, low: base, close: base + boxSize, volume: c.volume })
        base += boxSize
        dir = 1
      }
    }
    if (dir <= 0) {
      while (price <= base - boxSize) {
        bricks.push({ time: c.time, open: base, high: base, low: base - boxSize, close: base - boxSize, volume: c.volume })
        base -= boxSize
        dir = -1
      }
    }
    // Reversal: when trending one way, a move of 2 boxes the other way starts
    // the opposite color from the brick lattice.
    if (dir === 1) {
      while (price <= base - 2 * boxSize) {
        const top = base - boxSize
        bricks.push({ time: c.time, open: top, high: top, low: top - boxSize, close: top - boxSize, volume: c.volume })
        base = top - boxSize
        dir = -1
      }
    } else if (dir === -1) {
      while (price >= base + 2 * boxSize) {
        const bottom = base + boxSize
        bricks.push({ time: c.time, open: bottom, high: bottom + boxSize, low: bottom, close: bottom + boxSize, volume: c.volume })
        base = bottom + boxSize
        dir = 1
      }
    }
  }
  return bricks
}

/**
 * Three-Line-Break (default lines=3) blocks as synthetic candles. A new block
 * appears when price closes beyond the extreme of the prior `lines` blocks
 * (continuation needs only the last block; a reversal needs to break the
 * extreme of the last `lines` blocks). Up blocks close > open, down close < open.
 */
export function toLineBreak(candles: Candle[], lines = 3): Candle[] {
  const n = candles.length
  if (n === 0) return []
  const blocks: Candle[] = []
  for (let i = 0; i < n; i++) {
    const c = candles[i]
    const price = c.close
    if (blocks.length === 0) {
      // Seed from the first candle's own open->close direction.
      const up = c.close >= c.open
      const lo = Math.min(c.open, c.close)
      const hi = Math.max(c.open, c.close)
      blocks.push({ time: c.time, open: up ? lo : hi, high: hi, low: lo, close: up ? hi : lo, volume: c.volume })
      continue
    }
    const last = blocks[blocks.length - 1]
    const lastUp = last.close >= last.open
    // Extremes over the trailing `lines` blocks (for reversals).
    let hiN = -Infinity
    let loN = Infinity
    const start = Math.max(0, blocks.length - lines)
    for (let k = start; k < blocks.length; k++) {
      hiN = Math.max(hiN, blocks[k].high)
      loN = Math.min(loN, blocks[k].low)
    }
    const lastTop = Math.max(last.open, last.close)
    const lastBottom = Math.min(last.open, last.close)
    if (price > lastTop) {
      // Up continuation (break the last block's top) — one new up block.
      blocks.push({ time: c.time, open: lastTop, high: price, low: lastTop, close: price, volume: c.volume })
    } else if (price < lastBottom) {
      blocks.push({ time: c.time, open: lastBottom, high: lastBottom, low: price, close: price, volume: c.volume })
    } else if (lastUp && price < loN) {
      // Reversal down: break the low of the last `lines` blocks.
      blocks.push({ time: c.time, open: lastBottom, high: lastBottom, low: price, close: price, volume: c.volume })
    } else if (!lastUp && price > hiN) {
      blocks.push({ time: c.time, open: lastTop, high: price, low: lastTop, close: price, volume: c.volume })
    }
    // Otherwise no new block (price stayed inside the break range).
  }
  return blocks
}

/**
 * Auto box size for Point & Figure: identical sizing to Renko (0.5 x ATR(14)
 * with a ~0.5% price floor) so the two re-binned price-quantizing types share a
 * consistent scale. Never returns 0.
 */
export function autoPnfBoxSize(candles: Candle[]): number {
  return autoRenkoBoxSize(candles)
}

/**
 * Point & Figure columns as synthetic candles, one element per COLUMN. Each
 * column quantizes price into `boxSize` boxes: an X (rising) column grows up
 * while price keeps making new box highs; an O (falling) column grows down;
 * a `reversal`-box counter-move starts a new column of the opposite kind.
 *
 * Encoded so it slots into the re-binned `Candle[]` pipeline exactly like Renko:
 *   - `open`  = the column's bottom box edge
 *   - `close` = the column's top box edge
 *   - X (up) columns have close > open; O (down) columns have close < open
 *     (a single-box column nudges close/open by `boxSize` to preserve direction)
 *   - `high`/`low` mirror the top/bottom edges; `time` is the source candle's
 *     time that last extended the column.
 * The renderer turns each column into a stack of X or O glyphs spanning
 * open..close. Returns [] for no data or a non-finite box.
 */
export function toPointAndFigure(candles: Candle[], boxSize: number, reversal = 3): Candle[] {
  const n = candles.length
  if (n === 0 || !(boxSize > 0) || !isFinite(boxSize)) return []
  const rev = reversal >= 1 ? Math.floor(reversal) : 3
  // Box index lattice anchored at 0 = first close; box k spans [k*box, (k+1)*box).
  const anchor = candles[0].close
  const boxOf = (price: number): number => Math.floor((price - anchor) / boxSize)
  interface Col {
    dir: 1 | -1
    top: number // top box index occupied (inclusive)
    bottom: number // bottom box index occupied (inclusive)
    time: number
  }
  const cols: Col[] = []
  let dir: 0 | 1 | -1 = 0
  let top = boxOf(candles[0].close)
  let bottom = top
  let time = candles[0].time
  for (let i = 0; i < n; i++) {
    const c = candles[i]
    const hiBox = boxOf(c.high)
    const loBox = boxOf(c.low)
    if (dir === 0) {
      // Seed direction from the first box-sized move beyond the opening box.
      if (hiBox > top) {
        dir = 1
        top = hiBox
        time = c.time
      } else if (loBox < bottom) {
        dir = -1
        bottom = loBox
        time = c.time
      }
      continue
    }
    if (dir === 1) {
      if (hiBox > top) {
        top = hiBox // extend the X column upward
        time = c.time
      } else if (loBox <= top - rev) {
        // Reversal down: close the X column, start an O column one box below the top.
        cols.push({ dir: 1, top, bottom, time })
        dir = -1
        bottom = loBox
        top = top - 1
        time = c.time
      }
    } else {
      if (loBox < bottom) {
        bottom = loBox // extend the O column downward
        time = c.time
      } else if (hiBox >= bottom + rev) {
        cols.push({ dir: -1, top, bottom, time })
        dir = 1
        top = hiBox
        bottom = bottom + 1
        time = c.time
      }
    }
  }
  if (dir !== 0) cols.push({ dir, top, bottom, time })
  // Materialize each column as a synthetic candle on the price (not box-index)
  // axis. A single-box column would have open === close, so nudge by the box to
  // keep the up/down direction (and a non-degenerate body) intact.
  return cols.map((col) => {
    const lo = anchor + col.bottom * boxSize
    const hi = anchor + (col.top + 1) * boxSize
    const open = col.dir === 1 ? lo : hi
    const close = col.dir === 1 ? hi : lo
    return { time: col.time, open, high: hi, low: lo, close, volume: 0 }
  })
}

/**
 * Auto range size for Range bars: same scale as a single Renko box
 * (0.5 x ATR(14) with a ~0.5% price floor). Never returns 0.
 */
export function autoRangeSize(candles: Candle[]): number {
  return autoRenkoBoxSize(candles)
}

/**
 * Range bars as synthetic candles: a new bar completes each time price travels a
 * fixed `rangeSize` from the forming bar's OPEN. Each completed bar spans exactly
 * `rangeSize` high-to-low and closes at the breakout edge (top for an up move,
 * bottom for a down move); the next bar opens there. `time` is the source
 * candle's time that completed it. The final, still-forming bar is emitted with
 * its running extremes so the latest price is always visible.
 *
 * Intra-candle price is modelled as a monotone walk from the candle's open
 * toward its close, touching the far extreme first (low before close on an up
 * candle, high before close on a down candle). This makes the bar count strictly
 * bounded — every completed bar consumes >= `rangeSize` of one-directional travel
 * — so the loop always terminates. Returns [] for no data or a non-finite range.
 */
export function toRangeBars(candles: Candle[], rangeSize: number): Candle[] {
  const n = candles.length
  if (n === 0 || !(rangeSize > 0) || !isFinite(rangeSize)) return []
  const bars: Candle[] = []
  // The forming bar tracks the lowest/highest price seen since it opened. A move
  // of `rangeSize` from its FLOOR (up) or CEILING (down) completes it.
  let open = candles[0].open
  let lo = open // running low of the forming bar
  let hi = open // running high of the forming bar
  let time = candles[0].time

  // Push a single price point into the forming bar, emitting completed bars when
  // the span first reaches `rangeSize`. Each completed bar advances `open`/`lo`/
  // `hi` to the breakout edge, so the forming span resets to <= rangeSize and the
  // while-loops below are bounded by |price - open| / rangeSize.
  const push = (price: number, t: number, vol: number): void => {
    if (price > hi) hi = price
    if (price < lo) lo = price
    // Up breakouts: price ran `rangeSize` above the forming low.
    while (price - lo >= rangeSize) {
      const top = lo + rangeSize
      bars.push({ time: t, open: lo, high: top, low: lo, close: top, volume: vol })
      open = top
      lo = top
      hi = price > top ? price : top
    }
    // Down breakouts: price ran `rangeSize` below the forming high.
    while (hi - price >= rangeSize) {
      const bottom = hi - rangeSize
      bars.push({ time: t, open: hi, high: hi, low: bottom, close: bottom, volume: vol })
      open = bottom
      hi = bottom
      lo = price < bottom ? price : bottom
    }
  }

  for (let i = 0; i < n; i++) {
    const c = candles[i]
    time = c.time
    // Walk open -> far extreme -> close so a single candle can complete multiple
    // bars in the realistic order (the spike before the settle).
    const upCandle = c.close >= c.open
    push(c.open, c.time, c.volume)
    push(upCandle ? c.low : c.high, c.time, c.volume)
    push(upCandle ? c.high : c.low, c.time, c.volume)
    push(c.close, c.time, c.volume)
  }

  // Emit the in-progress bar so the live price edge stays on screen, unless it's
  // a flat zero-height seed with no completed bars (degenerate single point).
  if (hi > lo || bars.length === 0) {
    const up = candles[n - 1].close >= open
    bars.push({ time, open, high: hi, low: lo, close: up ? hi : lo, volume: candles[n - 1].volume })
  }
  return bars
}

/** One Kagi vertex: a price turning point plus whether the segment INTO it is "thick" (yang). */
export interface KagiPoint {
  /** Approximate source time of the candle that formed this vertex. */
  time: number
  price: number
  /** Thick (above the prior shoulder) vs thin line for the segment ending here. */
  thick: boolean
}

/**
 * Kagi line vertices. The line continues in its current direction while price
 * extends the running extreme, and only reverses after a counter-move of at
 * least `reversalPct` (fraction, e.g. 0.04 = 4%) from that extreme — at which
 * point a new vertex (a "shoulder" at a top, a "waist" at a bottom) is fixed.
 *
 * Thickness (yang/yin): the line turns THICK once price rises above the
 * PREVIOUS shoulder (the prior up-leg's high) and THIN once it falls below the
 * PREVIOUS waist (the prior down-leg's low); otherwise it keeps its thickness.
 * The check is continuous (re-evaluated as each leg extends), and each emitted
 * vertex carries the thickness of the segment ending at it.
 */
export function toKagi(candles: Candle[], reversalPct: number): KagiPoint[] {
  const n = candles.length
  if (n === 0) return []
  const pct = reversalPct > 0 && isFinite(reversalPct) ? reversalPct : 0.04
  const pts: KagiPoint[] = []
  let dir = 0 // +1 rising leg, -1 falling leg, 0 unknown (pre-first-move)
  let extreme = candles[0].close // running high (rising) or low (falling) of the current leg
  // Prior shoulder / waist: the high of the last completed up-leg and the low
  // of the last completed down-leg. Seeded wide so thickness starts neutral and
  // the first genuine break flips it. `thick` is the current line thickness.
  let prevShoulder = Infinity
  let prevWaist = -Infinity
  let thick = true
  pts.push({ time: candles[0].time, price: candles[0].close, thick })

  // Re-evaluate the current thickness against the prior shoulder/waist, then
  // write the live endpoint at the running extreme so the last leg tracks price.
  const sync = (time: number): void => {
    if (extreme >= prevShoulder) thick = true
    else if (extreme <= prevWaist) thick = false
    pts[pts.length - 1] = { time, price: extreme, thick }
  }

  for (let i = 1; i < n; i++) {
    const c = candles[i]
    const price = c.close
    if (dir === 0) {
      if (price >= extreme * (1 + pct)) {
        dir = 1
        extreme = price
      } else if (price <= extreme * (1 - pct)) {
        dir = -1
        extreme = price
      } else {
        continue
      }
      // First committed leg: append its endpoint (seed vertex stays at index 0).
      pts.push({ time: c.time, price: extreme, thick })
      sync(c.time)
    } else if (dir === 1) {
      if (price > extreme) {
        extreme = price // extend the up-leg
        sync(c.time)
      } else if (price <= extreme * (1 - pct)) {
        // Reversal down: the up-leg's high becomes the new prior shoulder; start
        // a fresh down-leg with its own endpoint vertex.
        prevShoulder = extreme
        extreme = price
        dir = -1
        pts.push({ time: c.time, price: extreme, thick })
        sync(c.time)
      }
    } else {
      // dir === -1
      if (price < extreme) {
        extreme = price // extend the down-leg
        sync(c.time)
      } else if (price >= extreme * (1 + pct)) {
        prevWaist = extreme
        extreme = price
        dir = 1
        pts.push({ time: c.time, price: extreme, thick })
        sync(c.time)
      }
    }
  }
  return pts
}
