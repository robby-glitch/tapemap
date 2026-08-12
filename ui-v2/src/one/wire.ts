import { useEffect, useState } from 'react'
import type { IndexKey } from '../data'

/* ── The fields the typed layer drops ────────────────────────────────────────
 *
 * `data.ts` maps /api/chain into the app's `Chain` type, and that mapping is
 * lossy in exactly the place this board cannot afford it to be:
 *
 *   gex: gexR === 'POSITIVE' ? 'Positive' : gexR === 'NEGATIVE' ? 'Negative'
 *                                                              : 'Neutral'
 *
 * Three different wire values collapse into the word "Neutral": a genuinely
 * balanced book, `OUT-OF-ZONE` (spot has walked outside the heavy books, so
 * the total says nothing about here), and `null` (no strike had a solvable
 * IV, so nothing was computed at all). "Balanced" and "we could not look" are
 * the two sentences honesty rule A1 exists to keep apart, and the typed layer
 * renders them identically.
 *
 * The backend already publishes the distinction — `flip_status` carries a
 * comment in gamma.py saying so in as many words — and PRODUCT.md lists it,
 * `gex_spot_band` and `basis_why` as published-but-never-drawn. So this hook
 * reads them straight off the wire.
 *
 * It does NOT re-derive anything. Every field below is copied, not computed;
 * where the wire says null this says null, and the widget that wanted it
 * prints the reason instead of a number.
 *
 * ── Frame ──────────────────────────────────────────────────────────────────
 * Everything here is INDEX frame, verbatim as the chain publishes it. This is
 * the one deliberate difference from `data.ts`, which adds `basis` to
 * `max_pain` and `flip_px` to move them onto the futures tape it draws them
 * on. This board draws them next to `mp_dist` — a spot-to-strike distance,
 * which is index-frame by construction — so converting one and not the other
 * is precisely the "same number, two frames, one screen" bug data.ts's own
 * comment records. Index frame throughout, badged IDX, and the FUT−IDX spread
 * shown on its own card so the two scales are never silently mixed.
 *
 * ── Cadence ────────────────────────────────────────────────────────────────
 * /api/chain is 80KB and carries everything except `basis`; /api/data is 1MB
 * and carries nothing this board needs BUT `basis`. So they are polled apart:
 * chain on the 15s cadence the OI Flow tab already uses, basis on 60s. Basis
 * is a carry to expiry — it moves in points per hour, not per second — and a
 * megabyte every 15s to re-read one slow float is not a trade worth making.
 */

/** Why there is no gamma flip level, in the backend's own vocabulary
 *  (gamma.py `gex_profile`). Empty string = the field was not published. */
export type FlipStatus = 'FOUND' | 'NO_CROSSING' | 'ONE_STRIKE' | 'NO_IV' | ''

export interface ChainWire {
  /** False until the first response lands, or when the fetch failed. */
  ok: boolean
  /** Why there is no wire at all. '' when fine. */
  why: string
  /** The chain's own note about itself — e.g. "market closed - polling
   *  resumes 09:15 IST". Not an error: the snapshot is still real. */
  note: string

  ts: string
  spot: number | null
  atm: number | null

  gexRegime: 'POSITIVE' | 'NEGATIVE' | 'OUT-OF-ZONE' | null
  gexTotal: number | null
  gexSpot: number | null
  /** Half-width, in points, of the near-money window `gexSpot` was summed
   *  over. A near-money GEX means nothing without knowing how near. */
  gexSpotBand: number | null
  flipPx: number | null
  flipStatus: FlipStatus

  wallUp: number | null
  wallDn: number | null
  bookZone: [number, number] | null
  inBookZone: boolean | null

  maxPain: number | null
  /** Signed spot→max-pain distance. Positive = the pin sits above spot. */
  mpDist: number | null
  pcrOi: number | null
  pcrVol: number | null

  squeezeScore: number | null
  squeezeSide: string | null
  squeezeVerdict: string

  /** Futures minus index, as the backend measured and sanity-checked it. */
  basis: number | null
  /** The sentence that comes with a null basis. '' when basis is fine —
   *  "we checked and it is plausible", which is not the same as silence. */
  basisWhy: string
  /** False until the basis fetch has answered once. Distinguishes "not read
   *  yet" from "read, and it was null". */
  basisRead: boolean
}

const EMPTY: ChainWire = {
  ok: false, why: '', note: '',
  ts: '', spot: null, atm: null,
  gexRegime: null, gexTotal: null, gexSpot: null, gexSpotBand: null,
  flipPx: null, flipStatus: '',
  wallUp: null, wallDn: null, bookZone: null, inBookZone: null,
  maxPain: null, mpDist: null, pcrOi: null, pcrVol: null,
  squeezeScore: null, squeezeSide: null, squeezeVerdict: '',
  basis: null, basisWhy: '', basisRead: false,
}

/** A finite number, or null. Never `?? 0` — a zero that means "absent" is the
 *  exact lie this file exists to prevent (see data.ts's own ATM-IV note). */
const num = (v: unknown): number | null =>
  typeof v === 'number' && Number.isFinite(v) ? v : null

const str = (v: unknown): string => (typeof v === 'string' ? v : '')

const FLIP: readonly FlipStatus[] = ['FOUND', 'NO_CROSSING', 'ONE_STRIKE', 'NO_IV']
const REGIMES = ['POSITIVE', 'NEGATIVE', 'OUT-OF-ZONE'] as const

export function useChainWire(index: IndexKey): ChainWire {
  const [w, setW] = useState<ChainWire>(EMPTY)

  // Chain — 15s, the OI Flow tab's cadence.
  useEffect(() => {
    let alive = true
    setW(EMPTY)
    const load = async () => {
      try {
        const r = await fetch(`/api/chain?idx=${index}`)
        const j = await r.json()
        if (!alive) return
        if (!j || j.ok === false) {
          setW((p) => ({ ...p, ok: false, why: str(j?.error) || 'chain unavailable' }))
          return
        }
        const m = j.metrics ?? {}
        const sq = m.squeeze ?? {}
        const fs = str(m.flip_status) as FlipStatus
        const reg = str(m.gex_regime)
        const bz = m.book_zone
        setW((p) => ({
          ...p,
          ok: true,
          why: '',
          // The chain answers ok:true and still carries an `error` note after
          // the close. That is a real snapshot with a real reason it is not
          // advancing — it is a caption, not a failure.
          note: str(j.error),
          ts: str(j.ts),
          spot: num(j.spot),
          atm: num(j.atm),
          gexRegime: (REGIMES as readonly string[]).includes(reg)
            ? (reg as ChainWire['gexRegime']) : null,
          gexTotal: num(m.gex_total),
          gexSpot: num(m.gex_spot),
          gexSpotBand: num(m.gex_spot_band),
          flipPx: num(m.flip_px),
          flipStatus: FLIP.includes(fs) ? fs : '',
          wallUp: num(m.wall_up),
          wallDn: num(m.wall_dn),
          bookZone: Array.isArray(bz) && bz.length === 2
            && num(bz[0]) != null && num(bz[1]) != null
            ? [bz[0] as number, bz[1] as number] : null,
          inBookZone: typeof m.in_book_zone === 'boolean' ? m.in_book_zone : null,
          maxPain: num(m.max_pain),
          mpDist: num(m.mp_dist),
          pcrOi: num(m.pcr_oi),
          pcrVol: num(m.pcr_vol),
          squeezeScore: num(sq.score),
          // Deliberately null when no book qualifies, and always null inside
          // the expiry squaring window. "null 0.00" is worse than silence.
          squeezeSide: typeof sq.side === 'string' && sq.side ? sq.side : null,
          squeezeVerdict: str(sq.verdict),
        }))
      } catch {
        if (alive) setW((p) => ({ ...p, ok: false, why: 'backend unreachable' }))
      }
    }
    load()
    const id = setInterval(load, 15000)
    return () => { alive = false; clearInterval(id) }
  }, [index])

  // Basis — 60s, and only ever these two fields out of a 1MB payload.
  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const r = await fetch(`/api/data?idx=${index}`)
        const j = await r.json()
        if (!alive) return
        setW((p) => ({
          ...p, basis: num(j?.basis), basisWhy: str(j?.basis_why), basisRead: true,
        }))
      } catch {
        // Leave basisRead false: a failed read is "we could not check", which
        // the widget renders differently from a null basis the backend
        // deliberately published with a reason.
        if (alive) setW((p) => ({ ...p, basis: null, basisWhy: '', basisRead: false }))
      }
    }
    load()
    const id = setInterval(load, 60000)
    return () => { alive = false; clearInterval(id) }
  }, [index])

  return w
}

/** The backend's reason, as a sentence an operator can act on. Never invents
 *  one: an unpublished status returns '' and the caller says so its own way. */
export function flipReason(s: FlipStatus): string {
  return s === 'NO_IV'
    ? 'could not look — no strike had a solvable IV, so no gamma profile was built'
    : s === 'NO_CROSSING'
    ? 'looked, and found none — dealer gamma never changes sign across the strike range'
    : s === 'ONE_STRIKE'
    ? 'could not look — only one strike was usable, so there was nothing to scan across'
    : ''
}
