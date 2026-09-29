// THE HINGLISH CHIPS (docs/trade-tab/2-hinglish-chips.md). Her ask: every symbol on the chart readable without the
// key. One place for every chip's words, so the chart, the hover card and the glossary can never disagree.
//
// Sides are read the way each SOURCE defines them, never guessed:
//   engine (fold.py)      won: the winner · absorbed: the ABSORBED party (the holder is the other side; the engine's
//                         own level text says "N lots of buyers held") · trapped: the trapped party
//   extension (board.js)  trap +1: bought at the high, price below → trapped buyers → a possible TOP
//                         absorption: the DEFENDER · exhaustion: −(the leg's direction), so −1 = buyers tired at a high
// An engine chip is built from `side` only when the engine's own text names the same party; otherwise the chip is the
// engine's words, unchanged.
//
// HER WORDS FIRST (2026-09-29): "the chip it used to produce earlier was good all that you find will find in event tab".
// The captions are the Events tab's own (hinglish.ts: MAAL KHAPAYA, THAKAN, TRAP, DUM NAHI), read through glossOf so the
// two tabs can never word one thing two ways; words are invented only where the Events tab has none.
//
// SIDES, VERIFIED (2026-09-29): a footprint mark's `side` here is board.js's RAW side, what /api/tape stores (the tape
// posts `m.local.events`, main.js:220 → :269). trap +1 = "bought at the prior bar's high, price now below them" = BUYERS
// trapped; absorption = the defender; exhaustion = −(the leg's direction). GoCharting PAINTS a trap by the flipped side,
// the side that won there (main.js:169), so a buyers-trapped P is red on her chart: paintSide does that flip for the
// colour only. Never flip the words.
import type { EngMark } from './engine'
import type { FootEvent } from './footprint'
import { glossOf } from './hinglish'

/** The Events tab's caption for an engine kind (upper case, as it renders there). */
const cap = (kind: string, fallback: string) => glossOf(kind)?.short ?? fallback

export const BUY_C = '#0f7b6c'
export const SELL_C = '#c0392b'
export const NEUT_C = '#4a5568'
export const sideColor = (s: number | null | undefined) => (s != null && s > 0 ? BUY_C : s != null && s < 0 ? SELL_C : NEUT_C)

const WHO: Record<string, string> = { '1': 'Buyers', '-1': 'Sellers' }
const who = (s: number | null | undefined) => (s != null && s !== 0 ? WHO[String(Math.sign(s))] : null)

/** W's state vocabulary (fold `_OIWatch.state`) in her words. */
export function wallState(state: string | null | undefined): string {
  return state === 'building' ? 'badh rahi' : state === 'stopped' ? 'ruk gayi' : state === 'off' ? 'hat rahi' : ''
}

export interface ChipText { text: string; color: string }

/** The side GoCharting paints a footprint mark in: a trap flipped (main.js:169, as posted at :269 unflipped), the rest
 *  as they are. For the colour only. */
export const paintSide = (e: FootEvent) => (e.kind === 'trap' && e.side != null ? -e.side : e.side)

/** An engine mark's chip. `held` is coloured by the HOLDER, so the colour and the words agree ("Buyers ne roka"
 *  is the engine's own "N lots of buyers held"). Built from `side` only when the engine's text names the same party. */
export function engChip(m: EngMark): ChipText | null {
  const party = who(m.side)
  if (m.kind === 'won') {
    const ok = party && m.text.toLowerCase().startsWith(`${party.toLowerCase()} won`)
    if (!ok) return { text: m.text, color: sideColor(m.side) }
    return { text: `${party} jeete · ${Math.round(m.px)}${m.by === 'price' ? ' (sirf price se)' : ''}`, color: sideColor(m.side) }
  }
  if (m.kind === 'absorbed') {
    const r = /^(\d+) lots of (buyers|sellers) absorbed/.exec(m.text)
    if (!r || !party || r[2] !== party.toLowerCase()) return { text: m.text, color: sideColor(m.side) }
    return { text: `${who(-m.side)} ne roka · ${r[1]} lots`, color: sideColor(-m.side) }
  }
  if (m.kind === 'trapped') {
    const r = /^(\d+) lots of (buyers|sellers) trapped/.exec(m.text)
    if (!r || !party || r[2] !== party.toLowerCase()) return { text: m.text, color: sideColor(m.side) }
    return { text: `${party} phase · ${r[1]} lots`, color: sideColor(m.side) }
  }
  if (m.kind === 'released') {                  // "sellers at 22612 released": the trap opened (Events: SQUEEZE KHULA)
    const ok = party && m.text.toLowerCase().startsWith(`${party.toLowerCase()} at`)
    return { text: ok ? `${party} ka trap khula · ${Math.round(m.px)}` : m.text, color: sideColor(m.side) }
  }
  if (m.kind === 'wall' && m.k != null && m.ty) return { text: `${m.k} ${m.ty} writers ki deewar`, color: '#5C6675' }
  return null
}

/** Her footprint mark's chip, in the Events tab's words where it has them, read off board.js's raw side: A +1 =
 *  buyers defended; E −1 = the buyers' up-leg had no dum left (board.js:112); P +1 = BUYERS trapped. A P's fact comes
 *  first ("Buyers phase (P)"); "top / bottom ban sakta" is added only when it sits at the swing extreme of the bars
 *  before it (`swing`, set in TradeTab), else "(chhota trap)". A named level makes the glyph heavy, never the words. */
export function footChip(e: FootEvent): ChipText | null {
  const p = e.p == null ? '' : ` · ${Math.round(e.p)}`
  const s = e.side ?? 0
  if (e.kind === 'trap') {
    const color = sideColor(paintSide(e))
    if (s > 0) return { text: `Buyers phase (P)${p}${e.swing === 'top' ? ' · top ban sakta' : ' (chhota trap)'}`, color }
    if (s < 0) return { text: `Sellers phase (P)${p}${e.swing === 'bottom' ? ' · bottom ban sakta' : ' (chhota trap)'}`, color }
    return { text: `${cap('TRAP', 'TRAP')} (P)${p}`, color }
  }
  if (e.kind === 'absorption') {
    return { text: s ? `${who(s)} ne maal khapaya (A)${p}` : `${cap('ABSORPTION', 'MAAL KHAPAYA')} (A)${p}`, color: sideColor(s) }
  }
  if (e.kind === 'exhaustion') {
    const dn = cap('DIVERGENCE', 'DUM NAHI')
    return { text: s < 0 ? `Buyers ka ${dn} (E)${p}` : s > 0 ? `Sellers ka ${dn} (E)${p}` : `${dn} (E)${p}`, color: sideColor(s) }
  }
  if (e.kind === 'climax') return { text: `${cap('CLIMAX', 'THAKAN')} (C)${p}`, color: sideColor(s) }
  return null
}

/** The left panel's key, one line each, in the Events tab's words where it has them. */
export const GLOSSARY: [string, string][] = [
  ['▲ ▼', 'ladai kisne jeeti (engine) · "sirf price se" = [I]'],
  ['▬', 'roka: ek taraf ka bada order doosri taraf ne khapa liya (engine, book)'],
  ['═', 'phase hue log, abhi nikle nahi (engine)'],
  ['P', `${cap('TRAP', 'TRAP')}: kaun phasa · top / bottom ban sakta sirf pichhle 12 bar ke high / low par, warna chhota trap (footprint)`],
  ['A', `${cap('ABSORPTION', 'MAAL KHAPAYA')}: kisne saara maal khapaya, bhaav hila nahi (footprint, aapka)`],
  ['E', `${cap('DIVERGENCE', 'DUM NAHI')}: naya high / low, flow saath nahi (footprint)`],
  ['C', `${cap('CLIMAX', 'THAKAN')}: move ke aakhir mein sabse tez volume (footprint)`],
  ['━', 'agli ladai: upar / neeche'],
  ['┈', 'writers ki deewar (strike + basis) · peeche = sahara, aage = rok'],
  ['░', 'aapka zone, 3-min: d2→d3 buy · u2→u3 sell'],
  ['▸ ╌', 'aapki entry · yahan galat (give-up)'],
]
