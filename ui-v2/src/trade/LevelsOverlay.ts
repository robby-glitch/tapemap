// Levels the engine already knows, drawn over the chart. The ONLY file that
// touches CandL's coordinate system: converters are live objects and must be
// re-queried every frame (their docs say so — zoom/pan invalidates them).
import type { IChartEngine } from '../vendor/candl/chart/types'
import type { MapLevel } from '../data'

// One-meaning colour: brass = structure; red is reserved for trap risk.
const STRUCT = 'rgba(224,168,82,0.85)'
const TRAP = 'rgba(255,95,107,0.85)'

// Minimum vertical gap between two drawn labels, for a 10px font.
const LABEL_GAP = 11

// The chart engine draws its own OHLC legend across the top-left of the main
// pane. A label landing in that band would overprint it and both become
// illegible, so labels start below it — the level's LINE is still drawn.
const LEGEND_BAND_PX = 26

export function startLevelsOverlay(
  canvas: HTMLCanvasElement,
  host: HTMLElement,
  engine: IChartEngine,
  getLevels: () => MapLevel[],
): () => void {
  const ctx = canvas.getContext('2d')!
  let raf = 0

  const draw = () => {
    raf = requestAnimationFrame(draw)
    const dpr = window.devicePixelRatio || 1
    const w = host.clientWidth, h = host.clientHeight
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr
      canvas.height = h * dpr
      // A canvas is a REPLACED element: with position:absolute and inset:0 it
      // takes its intrinsic size from these width/height attributes instead of
      // stretching to the parent, so the CSS size must be set explicitly or the
      // overlay renders dpr× too large and every level line misaligns.
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)

    const conv = engine.getMainConverters()
    const pane = engine.getMainPaneRect()
    if (!conv || !pane) return // engine not laid out yet — draw nothing, never guess

    ctx.font = '10px ui-monospace, SFMono-Regular, Menlo, monospace'
    ctx.textBaseline = 'bottom'

    // Copy before sorting — getLevels() may return the live MAP.levels array,
    // and mutating it would corrupt whatever else reads it (e.g. Task 6's rail).
    const visible = getLevels()
      .filter((lvl) => lvl.kind !== 'now') // the tape itself is the price
      .map((lvl) => ({ lvl, y: conv.priceToY(lvl.value) }))
      .filter(({ y }) => y >= pane.y + 4 && y <= pane.y + pane.height - 4)
      .sort((a, b) => a.y - b.y)

    let lastLabelY = -Infinity // last *drawn label's* y, not the last level's y
    for (const { lvl, y } of visible) {
      const color = lvl.kind === 'trap' ? TRAP : STRUCT
      ctx.strokeStyle = color
      ctx.fillStyle = color

      // Always draw the line — suppressing it would hide a real price level.
      ctx.setLineDash(lvl.kind === 'band' ? [2, 4] : [6, 4])
      ctx.beginPath()
      ctx.moveTo(pane.x, y)
      ctx.lineTo(pane.x + pane.width, y)
      ctx.stroke()
      ctx.setLineDash([]) // reset so dash state never leaks into the next stroke/fill

      // Draw the label only if it clears the last *drawn* label by the min gap
      // AND clears the engine's own OHLC legend in the top-left of the pane.
      if (y - lastLabelY >= LABEL_GAP && y >= pane.y + LEGEND_BAND_PX) {
        ctx.fillText(`${lvl.label} ${lvl.value.toFixed(1)}`, pane.x + 6, y - 2)
        lastLabelY = y
      }
    }
  }

  raf = requestAnimationFrame(draw)
  return () => cancelAnimationFrame(raf)
}
