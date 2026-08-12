import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import ContractChart from '../trade/ContractChart'
import SetupCheck from '../trade/SetupCheck'
import { useFlow, FlowLine } from '../trade/flow'
import { buildNarration } from '../trade/narration'
import { palette, useMode } from '../theme'
import type { TapeBar, MapLevel, IndexKey, EventItem, RotationSignal, RunState } from '../data'

/**
 * ONE SCREEN — the trial tab.
 *
 * PRODUCT.md's claim is that this tool answers two questions: am I in a trade,
 * and what has to happen next. The shell already answers the first (the machine
 * strip, on every tab). This tab is an experiment in answering the second with
 * three things and nothing else:
 *
 *   1. the chart, as big as the viewport allows — candles, VWAP, σ bands,
 *      levels, and the §5c entry markers;
 *   2. the TRIGGER block — the same SetupCheck the Trade tab mounts, with its
 *      unscored half folded behind one disclosure;
 *   3. one line of Trending OI.
 *
 * Everything else the Trade tab carries — the stat strip, the leg panes, the
 * ZONE READ, the engine's plays, the ribbon, the legend paragraphs — is absent
 * BY DESIGN, not by omission. The setup fires once or twice a week; the
 * majority state of this screen is "nothing is happening", and that state has
 * to look calm rather than busy or the operator stops glancing at it.
 *
 * ── Nothing here is forked ─────────────────────────────────────────────────
 * Every component on this screen is the Trade tab's own, mounted with
 * different furniture around it. There is no second chart, no second flow
 * formatter and no second reading of `run_state`. That is the whole reason
 * this tab is cheap to trial and cheap to delete.
 *
 * ── The layout trap ────────────────────────────────────────────────────────
 * ContractChart's root is `height:100%`, which cannot resolve against a flex
 * item whose container is auto-height — that collapses the canvas to zero, and
 * it has done so twice. The chart column below therefore carries a DEFINITE
 * pixel height and the chart row inside it a real `minHeight`. Anything added
 * to this screen goes ABOVE the column (the thin toolbar) or BELOW it (the
 * flow line) — never inside it after the chart.
 */

interface Props {
  index: IndexKey
  day: string
  bars: TapeBar[]
  levels: MapLevel[]
  events: EventItem[]
  cursor: number | null
  stale: boolean
  loading: boolean
  runState: RunState[] | null
  runStateWhy: string
  runStateSell: RunState[] | null
  rotationRun: (RotationSignal | null)[] | null
  rotationRunWhy: string
  rotationRunSell: (RotationSignal | null)[] | null
}

/** The trigger rail, in px.
 *
 *  LEFT, and the same side the Trade tab puts SetupCheck on. The panel is the
 *  one thing both tabs share on screen, and the operator will be flipping
 *  between them to judge this trial — a panel that jumps sides on every flip
 *  turns an A/B about CONTENT into an A/B about where things moved.
 *
 *  300, not the Trade tab's 260: compact drops the two-tally footer, so the
 *  reference/stop prices are the widest thing left and 260 wrapped
 *  "Todna hai > 24,412.5" onto two lines at the 10.5px mono size. */
const RAIL_W = 300

/** Height the flow line and its disclosure need under the chart column, so the
 *  column can be sized to leave room for them rather than pushing them off. */
const BELOW_RESERVE = 62

export default function OneTab({
  index, day, bars, levels, events, cursor, stale, loading,
  runState, runStateWhy, runStateSell,
  rotationRun, rotationRunWhy, rotationRunSell,
}: Props) {
  const [mode, setMode] = useMode()
  const pal = palette(mode)

  const { last: lastFlow, why: flowWhy } = useFlow(index)

  // Same clamp the Trade tab uses: a negative cursor would index bars[-1] and
  // throw on the first field read. Computed before the no-tape bail so the
  // memos below can depend on it unconditionally; bars.length === 0 yields
  // at === -1, which is never read once the bail has returned.
  const at = cursor == null
    ? bars.length - 1
    : Math.max(0, Math.min(cursor, bars.length - 1))

  // Both sides in one array, exactly as the Trade tab merges them — the
  // overlay already branches on `sig.side`, and a BUY wins a slot outright if
  // both ever land on one bar rather than one silently replacing the other.
  const rotationDraw = useMemo(() => {
    if (!rotationRun && !rotationRunSell) return null
    const n = bars.length
    const out: (RotationSignal | null)[] = new Array(n).fill(null)
    for (let i = 0; i < n; i++) out[i] = rotationRun?.[i] ?? rotationRunSell?.[i] ?? null
    return out
  }, [rotationRun, rotationRunSell, bars.length])

  // The hover Callout reads these. The STORY layer is off on this tab, so no
  // balloon is painted — but an on-demand read of the bar under the cursor is
  // not clutter, and dropping it would remove information rather than noise.
  const narrs = useMemo(() => buildNarration(bars, events), [bars, events])

  const [hover, setHover] = useState<number | null>(null)
  const handleHover = (i: number | null) => {
    if (i == null || !bars.length) { setHover(null); return }
    const maxIdx = bars.length - 1
    let idx = Math.max(0, Math.min(i, maxIdx))
    // Hovering must never reveal a bar the replay cursor is hiding.
    if (cursor != null) idx = Math.min(idx, Math.max(0, Math.min(cursor, maxIdx)))
    setHover(idx)
  }

  /* Height. The Trade tab sizes its column to `innerHeight - 12` on purpose —
     it WANTS to overflow, because the operator asked for a full-screen chart
     with the rest of the page one scroll below. This tab's whole claim is the
     opposite: one screen, no scroll. So it measures the chrome above instead.

     The measurement is taken on our PARENT (App's `flex:1; overflow-y:auto`
     tab-content box), not on ourselves. That matters twice over:

       · the parent's own top is fixed by the banners, ANSWER band, machine
         strip, tab row and transport above it — none of which depend on our
         height — so there is no feedback loop, which is what froze the page
         when a dep-less layout effect measured its own box here;
       · the parent is the SCROLLER, so its rect.top does not move when its
         content scrolls. That kills the latching bug (CHECKLIST E6) where a
         measure taken mid-scroll set a huge height that then stuck. */
  const rootRef = useRef<HTMLDivElement>(null)
  const [availH, setAvailH] = useState<number | null>(null)
  useLayoutEffect(() => {
    const el = rootRef.current
    if (!el) return
    const measure = () => {
      const node = rootRef.current
      const parent = node?.parentElement
      if (!node) return
      const top = parent ? Math.max(0, parent.getBoundingClientRect().top) : 0
      const next = Math.max(320, window.innerHeight - top - BELOW_RESERVE)
      setAvailH((prev) => (prev != null && Math.abs(prev - next) < 2 ? prev : next))
    }
    measure()
    window.addEventListener('resize', measure)
    const parent = el.parentElement
    const ro = parent ? new ResizeObserver(measure) : null
    if (parent && ro) ro.observe(parent)
    return () => {
      window.removeEventListener('resize', measure)
      ro?.disconnect()
    }
  }, [index, bars.length === 0])

  // Honesty rule 1: no tape = say so, and chart nothing. A fallback must never
  // occupy the space live data goes in. Before the first poll resolves a
  // healthy index also has zero bars, and that must read as "loading", not as
  // "no session". Same two sentences the Trade tab uses, verbatim — one
  // condition must not get two different explanations across two tabs.
  if (!bars.length) {
    return (
      <div style={{ padding: 16, backgroundColor: pal.bg }}>
        <div style={{
          padding: '14px 18px', borderRadius: 6, backgroundColor: pal.card,
          border: `1px solid ${loading ? pal.border : pal.caution}`,
          color: loading ? pal.textMuted : pal.caution,
          fontSize: 12.5, fontWeight: 600, letterSpacing: '0.02em',
        }}>
          {loading
            ? `${index} ka tape aa raha hai…`
            : `${index} KA TAPE NAHI — backend ke paas is index ka koi session hi nahi,`
              + ' toh chart banane ko kuch nahi hai. Nakli candles dikhane se behtar hai'
              + ' ek bhi na dikhana.'}
        </div>
      </div>
    )
  }

  const b = bars[at]
  const live = cursor == null
  const modeLabel = stale ? 'STALE' : live ? 'LIVE' : 'REPLAY'
  const modeColor = stale || !live ? pal.caution : pal.bull

  return (
    <div style={{ backgroundColor: pal.bg }}>
      <div ref={rootRef} style={{
        display: 'flex', flexDirection: 'column',
        // DEFINITE height, never minHeight — see the header note on the trap.
        height: availH ?? 420, padding: '10px 16px 0', gap: 8,
        // With a fixed height, anything that does not fit is CLIPPED rather
        // than allowed to paint over the line below it.
        overflow: 'hidden',
      }}>
        {/* Toolbar — ABOVE the chart, one line, three things.
            The contract name is not decoration: it is the frame. Everything
            drawn on the canvas below is FUTURES-frame, and the ANSWER band's
            distances-to-strike are index-frame, so the two must never be read
            as one scale. LIGHT/DARK is here because it is otherwise
            unreachable from this tab and the operator reads charts light. */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
          paddingLeft: 2,
        }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: pal.textPrimary, letterSpacing: '0.02em' }}>
            {index} FUT
          </span>
          <span style={{ fontSize: 10.5, color: pal.textMuted }}>
            chart ke saare bhaav futures ke hain
          </span>
          <span className="mono" style={{ fontSize: 10.5, color: pal.textMuted }}>
            {day || '—'} · {b.t}
          </span>

          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ display: 'flex', border: `1px solid ${pal.border}`, borderRadius: 4, overflow: 'hidden' }}>
              {(['light', 'dark'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  style={{
                    fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                    padding: '3px 9px', cursor: 'pointer', border: 'none',
                    backgroundColor: mode === m ? pal.accent : 'transparent',
                    color: mode === m ? pal.card : pal.textMuted,
                  }}
                >{m === 'light' ? 'LIGHT' : 'DARK'}</button>
              ))}
            </div>
            {/* Amber for REPLAY and for STALE alike: in this family amber means
                "not the data you would assume". Brass stays structure. */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <span style={{ width: 7, height: 7, borderRadius: '50%', backgroundColor: modeColor }} />
              <span style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em', color: modeColor }}>
                {modeLabel}
              </span>
            </div>
          </div>
        </div>

        {/* Chart row. `flex:1` with a real minHeight is the shock absorber for
            a column whose height is fixed: on a very short viewport the chart
            floors here instead of overflowing the column and painting over the
            flow line. Both children get a definite height from the row's
            default `align-items: stretch` — which is exactly what
            ContractChart's `height:100%` needs and what minHeight cannot give. */}
        <div style={{ flex: 1, minHeight: 180, overflow: 'hidden', display: 'flex', gap: 10 }}>
          <div style={{
            width: RAIL_W, flexShrink: 0, borderRadius: 6,
            border: `1px solid ${pal.border}`, backgroundColor: pal.card,
            padding: 12, overflow: 'hidden',
            display: 'flex', flexDirection: 'column', minHeight: 0,
          }}>
            <SetupCheck
              compact
              pal={pal} day={day} bar={b}
              runState={runState?.[at] ?? null} runStateWhy={runStateWhy}
              runStateSell={runStateSell?.[at] ?? null}
              entry={rotationRun?.[at] ?? null}
              entrySell={rotationRunSell?.[at] ?? null}
              flow={lastFlow} flowWhy={flowWhy}
            />
          </div>
          <div style={{
            // minWidth:0, or the flex item refuses to shrink below its content
            // and the chart shoulders the rail off the left edge when narrow.
            flex: 1, minWidth: 0, borderRadius: 6, overflow: 'hidden',
            border: `1px solid ${pal.border}`, backgroundColor: pal.card,
          }}>
            <ContractChart
              index={index} day={day} bars={bars} levels={levels} cursor={cursor}
              mode={mode} hover={hover} onHover={handleHover} narrs={narrs}
              // Hard off on this tab, and DISCLOSED below rather than silently
              // absent. Rotation is not gated by `story` (LevelsOverlay's own
              // rule), so the operator's own setup markers still draw.
              structures={null} smc={false} story={false}
              rotation={rotationDraw}
            />
          </div>
        </div>
      </div>

      {/* Below the fixed-height column, where growth is safe. */}
      <div style={{
        padding: '8px 16px 12px', display: 'flex', flexDirection: 'column', gap: 5,
      }}>
        <FlowLine pal={pal} flow={lastFlow} flowWhy={flowWhy} replaying={cursor != null} />

        {/* "We are not showing you" must never be indistinguishable from "we
            checked and found nothing" (A1). This screen switches two layers off
            by design and has no toggles to say so, so it says so in words —
            once, quietly, and only after a session has loaded so an empty first
            paint never claims anything is being withheld. */}
        {day && (
          <div style={{ fontSize: 11, color: pal.textMuted, paddingLeft: 2, lineHeight: 1.45, opacity: 0.85 }}>
            Is screen par sirf setup ke markers hain — STORY aur STRUCTURE layers yahan
            jaan-bujh kar band hain, mile nahi aisa nahi; Trade tab par on ho jaati hain.
            {!rotationRun && ` Setup ke markers bhi nahi mile${rotationRunWhy ? ` — ${rotationRunWhy}` : ''}.`}
          </div>
        )}
      </div>
    </div>
  )
}
