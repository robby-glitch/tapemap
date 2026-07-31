// ZONE READ — everything the tool knows about the price the tape is sitting
// at, assembled in one place. The operator's brief, verbatim: "if the market
// is down there, it should, with the help of OI, [say] how our books are
// looking, what GEX is saying, whether it supports trading in that zone…
// think everything as a whole."
//
// Always on: smart money positions during the noise, so the build-up must be
// watchable BEFORE the touch, not only at it. When the shown bar actually
// tags ±2σ/±3σ (the bar's own fields — a tag, not a proximity heuristic) or
// the band-rotation detector fired, the panel escalates its border and says
// which band.
//
// Discipline (the Validate-tab lesson): every line is a sourced fact rendered
// verbatim; nothing is tallied, scored or tagged for/against. "We found
// nothing", "we could not check" and "this is live, not replay-aligned" are
// three different sentences and each group says the one that is true.
import type { TapeBar, Chain, MapLevel, RotationSignal, Structure, FlowRow } from '../data'
import type { palette } from '../theme'

type Pal = ReturnType<typeof palette>

interface Props {
  pal: Pal
  bar: TapeBar
  chain: Chain
  levels: MapLevel[]
  rot: RotationSignal | null
  structures: Structure[] | null
  structuresWhy: string
  flow: FlowRow | null
  /** Why `flow` is null (fetch error / no rows yet). Empty when it isn't. */
  flowWhy: string
  /** Replay cursor set: chain + flow are live snapshots and must say so. */
  replaying: boolean
}

/** Indian-market compact units: crores / lakhs. Sign always shown — these are
 *  day CHANGES, and +0 vs -0 is a real distinction the operator reads.
 *  Exported: the OI strip in TradeTab formats the same row the same way. */
export const crl = (n: number): string => {
  const a = Math.abs(n)
  const s = n < 0 ? '-' : '+'
  if (a >= 1e7) return `${s}${(a / 1e7).toFixed(2)}Cr`
  if (a >= 1e5) return `${s}${(a / 1e5).toFixed(1)}L`
  return `${s}${a.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

const pts = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(1)}`

function Group({ pal, title, children }: { pal: Pal; title: string; children: React.ReactNode }) {
  return (
    <div style={{ flex: '1 1 200px', minWidth: 180, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <div style={{
        fontSize: 9, fontWeight: 700, letterSpacing: '0.1em',
        textTransform: 'uppercase', color: pal.textMuted,
      }}>{title}</div>
      <div style={{ fontSize: 11, lineHeight: 1.55, color: pal.textSecondary }}>{children}</div>
    </div>
  )
}

const Absent = ({ pal, children }: { pal: Pal; children: React.ReactNode }) => (
  <span style={{ color: pal.textMuted, fontStyle: 'italic' }}>{children}</span>
)

export default function ZoneRead({
  pal, bar, chain, levels, rot, structures, structuresWhy, flow, flowWhy, replaying,
}: Props) {
  const c = bar.c

  // ── the zone tag: the bar's own fields, nothing derived ────────────────
  const tags: string[] = []
  if (bar.l <= bar.d3) tags.push('d3')
  else if (bar.l <= bar.d2) tags.push('d2')
  if (bar.h >= bar.u3) tags.push('u3')
  else if (bar.h >= bar.u2) tags.push('u2')
  const inZone = tags.length > 0 || rot != null

  // Nearest ±2/3σ edge to the close, for the WHERE line.
  const edges: [string, number][] = [
    ['u3', bar.u3], ['u2', bar.u2], ['d2', bar.d2], ['d3', bar.d3],
  ]
  const nearest = edges.reduce((a, b) => (Math.abs(c - b[1]) < Math.abs(c - a[1]) ? b : a))

  // ── books: the walls in MAP + their ladder rows' off-peak state ────────
  const wallRow = (value: number) => chain.strikes.find((s) => s.strike === value) ?? null
  const callWall = levels.find((l) => l.kind === 'wall' && l.label === 'CALL') ?? null
  const putWall = levels.find((l) => l.kind === 'wall' && l.label === 'PUT') ?? null
  const offPeak = (oi: number, pk: number) =>
    pk > 0 ? `${Math.max(0, (1 - oi / pk) * 100).toFixed(0)}% off its session peak` : 'peak unknown'

  // ── gex: bracket strikes around the close ──────────────────────────────
  const sorted = [...chain.strikes].sort((a, b) => a.strike - b.strike)
  const below = [...sorted].reverse().find((s) => s.strike <= c) ?? null
  const above = sorted.find((s) => s.strike >= c) ?? null

  // ── structure: nearest pools + prior-day levels + range side ───────────
  const eqh = structures
    ?.filter((s) => s.kind === 'EQH' && s.hi > c)
    .reduce<Structure | null>((a, s) => (!a || s.hi < a.hi ? s : a), null) ?? null
  const eql = structures
    ?.filter((s) => s.kind === 'EQL' && s.lo < c)
    .reduce<Structure | null>((a, s) => (!a || s.lo > a.lo ? s : a), null) ?? null
  const latestOf = (kind: string) => structures
    ?.filter((s) => s.kind === kind)
    .reduce<Structure | null>((a, s) => (!a || s.born > a.born ? s : a), null) ?? null
  const pdh = latestOf('PDH')
  const pdl = latestOf('PDL')
  const prem = latestOf('PREMIUM')
  const disc = latestOf('DISCOUNT')
  const rangeSide = prem && c >= prem.lo && c <= prem.hi
    ? 'PREMIUM (upper half of the working range)'
    : disc && c >= disc.lo && c <= disc.hi
      ? 'DISCOUNT (lower half of the working range)'
      : null

  const liveNote = replaying
    ? <div><Absent pal={pal}>live snapshot — not aligned to the replay cursor</Absent></div>
    : null

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 10, padding: '12px 16px',
      borderRadius: 6, backgroundColor: pal.card,
      border: `1px solid ${inZone ? pal.accent : pal.border}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: pal.textMuted,
        }}>ZONE READ — WHAT SITS AT THIS PRICE</span>
        {inZone && (
          <span style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
            padding: '2px 8px', borderRadius: 3,
            backgroundColor: pal.accent, color: pal.card,
          }}>
            IN ZONE{tags.length ? ` — ${tags.join(' & ')}` : ''}{rot ? ' · SETUP FIRED' : ''}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
        <Group pal={pal} title="Where">
          <div>close {c.toFixed(1)} · VWAP {bar.vwap.toFixed(1)} ({c >= bar.vwap ? 'above' : 'below'}, {pts(c - bar.vwap)})</div>
          <div>nearest band edge {nearest[0]} {nearest[1].toFixed(1)} ({pts(c - nearest[1])} pts)</div>
          {bar.ctx ? (
            <div>band width rank {bar.ctx.bw_r.toFixed(2)} · {(bar.ctx.inside1 * 100).toFixed(0)}% of last 30m inside ±1σ</div>
          ) : (
            <div><Absent pal={pal}>engine context unavailable for this bar</Absent></div>
          )}
        </Group>

        <Group pal={pal} title="Books">
          {putWall ? (
            <div>
              PUT wall {putWall.value.toFixed(0)}
              {(() => { const r = wallRow(putWall.value); return r ? ` — book ${offPeak(r.peOI, r.pePk)}` : '' })()}
            </div>
          ) : <div><Absent pal={pal}>no put wall in the chain profile</Absent></div>}
          {callWall ? (
            <div>
              CALL wall {callWall.value.toFixed(0)}
              {(() => { const r = wallRow(callWall.value); return r ? ` — book ${offPeak(r.ceOI, r.cePk)}` : '' })()}
            </div>
          ) : <div><Absent pal={pal}>no call wall in the chain profile</Absent></div>}
          {chain.bookZone ? (
            <div>
              heavy books {chain.bookZone[0].toFixed(0)}–{chain.bookZone[1].toFixed(0)} —{' '}
              {chain.inBookZone ? 'price inside' : 'price OUTSIDE the books — snap-back risk'}
            </div>
          ) : <div><Absent pal={pal}>book zone unavailable</Absent></div>}
          {liveNote}
        </Group>

        <Group pal={pal} title="GEX">
          <div>regime {chain.gex} · at-spot {crl(chain.gexSpot)}</div>
          {chain.flipPx != null ? (
            <div>flip {chain.flipPx.toFixed(0)} ({pts(chain.flipPx - c)} pts from close)</div>
          ) : (
            <div><Absent pal={pal}>no flip price — the chain could not compute one</Absent></div>
          )}
          {below && above && below.strike !== above.strike ? (
            <div>{below.strike.toFixed(0)} gex {crl(below.gex)} · {above.strike.toFixed(0)} gex {crl(above.gex)}</div>
          ) : below || above ? (
            <div>{(below ?? above)!.strike.toFixed(0)} gex {crl((below ?? above)!.gex)}</div>
          ) : (
            <div><Absent pal={pal}>no ladder strikes around this price</Absent></div>
          )}
          {liveNote}
        </Group>

        <Group pal={pal} title="Flow">
          {flow ? (
            <>
              <div>{flow.time} mark · CALL {crl(flow.call)} · PUT {crl(flow.put)}</div>
              <div>
                DIFF {crl(flow.diff)} {flow.diff >= 0 ? 'PUT' : 'CALL'}-heavy {Math.abs(flow.strength * 100).toFixed(0)}%
                {flow.pcr != null && ` · PCR ${flow.pcr.toFixed(2)}`}
                {flow.chg_dir != null && ` · Δ ${flow.chg_dir >= 0 ? '▲' : '▼'}${crl(Math.abs(flow.chg_dir)).slice(1)}`}
              </div>
              {flow.brk && <div>{flow.brk} {flow.brk_px != null ? flow.brk_px.toFixed(1) : ''} — day {flow.brk === 'DHB' ? 'high' : 'low'} broke inside this mark</div>}
              {liveNote}
            </>
          ) : (
            <div><Absent pal={pal}>{flowWhy || 'no flow rows yet'}</Absent></div>
          )}
        </Group>

        <Group pal={pal} title="Gamma">
          {bar.gamma ? (
            <div>regime {bar.gamma.regime} · writer weight CE {bar.gamma.w_ce.toFixed(2)} / PE {bar.gamma.w_pe.toFixed(2)}</div>
          ) : (
            <div><Absent pal={pal}>gamma read unavailable for this bar</Absent></div>
          )}
        </Group>

        <Group pal={pal} title="Structure">
          {structures ? (
            <>
              {eqh ? <div>EQH pool at {eqh.hi.toFixed(1)} ({pts(eqh.hi - c)}) — formed; sweep not tracked</div>
                : <div><Absent pal={pal}>no EQH pool above</Absent></div>}
              {eql ? <div>EQL pool at {eql.lo.toFixed(1)} ({pts(eql.lo - c)}) — formed; sweep not tracked</div>
                : <div><Absent pal={pal}>no EQL pool below</Absent></div>}
              {(pdh || pdl) && (
                <div>
                  {pdh && `PDH ${pdh.hi.toFixed(1)} (${pts(pdh.hi - c)})`}
                  {pdh && pdl && ' · '}
                  {pdl && `PDL ${pdl.lo.toFixed(1)} (${pts(pdl.lo - c)})`}
                </div>
              )}
              {rangeSide && <div>price in {rangeSide}</div>}
            </>
          ) : (
            <div><Absent pal={pal}>{structuresWhy || 'structure layer unavailable'}</Absent></div>
          )}
        </Group>

        <Group pal={pal} title="Setup">
          {rot ? (
            <>
              <div style={{ fontWeight: 700 }}>{rot.side} {rot.band} — fired on this bar</div>
              <div>{rot.trigger}</div>
              <div>trap {rot.trap}{rot.trap_why ? `: ${rot.trap_why}` : ''}</div>
            </>
          ) : (
            <div><Absent pal={pal}>no band-rotation signal on this bar</Absent></div>
          )}
        </Group>
      </div>

      <div style={{ fontSize: 9.5, color: pal.textMuted }}>
        descriptive, not advice — every line names its source · signals only, orders never
      </div>
    </div>
  )
}
