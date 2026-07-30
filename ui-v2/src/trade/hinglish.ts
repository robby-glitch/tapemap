/**
 * Hinglish glosses for the engine's event KINDS.
 *
 * The operator reads the tape in Hinglish, and "TRAP-SPRUNG" / "DIVERGENCE"
 * carry no instant meaning at a glance — least of all a direction. This file
 * maps each kind the engine can emit to (a) a short pill caption for the chart
 * balloons and (b) a one-line plain explanation for the hover callout.
 *
 * WHAT THIS IS NOT. It is not a translation of the engine's message. Every
 * gloss below describes the KIND only — the category of thing that happened —
 * and the engine's own sentence, with its own numbers, is always rendered
 * alongside it verbatim (see Callout). Nothing here strengthens, softens or
 * re-interprets a claim, and no gloss states a number: numbers live in the
 * receipt, which is the one place allowed to state them.
 *
 * DIRECTION comes from `tone`, which the payload mapper derives in `evDir`
 * (data.ts) — v1's rule, and the authority. This file only puts a Hinglish
 * word on the direction that was already decided; it never infers one from the
 * kind. A kind whose direction the engine did not resolve says so plainly
 * ("direction saaf nahi") rather than picking a side.
 *
 * An unknown kind returns null and the UI falls back to the engine's own kind
 * string. A future event type therefore appears untranslated — never
 * mistranslated, and never silently dropped.
 */
import type { Narration } from './narration'

export interface Gloss {
  /** Balloon caption. Kept short — it sits in a pill over the candles. */
  short: string
  /** One line for the callout: what this kind of event means, in plain terms. */
  line: string
}

const G: Record<string, Gloss> = {
  // --- effort / result -----------------------------------------------------
  ABSORPTION: {
    short: 'MAAL KHAPAYA',
    line: 'Bhaari volume aaya par bhaav hila nahi — koi saara maal khapa raha hai.',
  },
  CLIMAX: {
    short: 'THAKAN',
    line: 'Move ke aakhir mein sabse tez volume — chaal thak rahi hai.',
  },
  IGNITION: {
    short: 'AAG LAGI',
    line: 'Ek hi bar mein volume aur range dono phati — naya move shuru hua.',
  },
  DIVERGENCE: {
    short: 'DUM NAHI',
    line: 'Bhaav naya level bana raha hai par flow saath nahi de raha — dum nahi hai.',
  },

  // --- traps and springs ---------------------------------------------------
  TRAP: { short: 'TRAP', line: 'Ek taraf ke log phas rahe hain.' },
  'TRAP-SETTING': {
    short: 'TRAP BUN RAHA',
    line: 'Trap ban raha hai — abhi chala nahi hai, sirf taiyari dikh rahi hai.',
  },
  'TRAP-SPRUNG': {
    short: 'TRAP LAGA',
    line: 'Trap chal gaya — jo log ek taraf ghuse the, unke ulta bhaav gaya.',
  },
  SPRING: {
    short: 'SPRING UCHHAAL',
    line: 'Level ke paar jaakar turant wapsi — jhoota breakdown/breakout tha.',
  },
  'SPRING-FAIL': {
    short: 'SPRING FAIL',
    line: 'Jis level se spring uchhla tha, bhaav usi ke paar band ho gaya — spring fail.',
  },

  // --- levels and bands ----------------------------------------------------
  BREAK: { short: 'LEVEL TOOTA', line: 'Ek asli level toot gaya.' },
  'BAND-BREAK': {
    short: 'BAND TOOTA',
    line: 'Bhaav sigma band ke bahar nikal gaya — extension chal raha hai.',
  },
  'BAND-REVERSAL': {
    short: 'BAND SE PALTA',
    line: 'Band ke extreme se bhaav wapas mud gaya — fade hua, follow-through nahi.',
  },
  'FLIP-TEST': {
    short: 'FLIP TEST',
    line: 'Toota hua level dobara test ho raha hai — ab wo ulta kaam karega ya nahi, wahi dekhna hai.',
  },

  // --- book / positioning --------------------------------------------------
  PRESS: { short: 'DABAAV', line: 'Ek taraf se lagatar dabaav pad raha hai.' },
  CAMPAIGN: {
    short: 'BADE KA KHEL',
    line: 'Lambe samay se ek hi taraf position ban rahi hai — ek soch ke saath khel chal raha hai.',
  },
  'BUYER-BUILD': {
    short: 'KHARIDDAR BADHE',
    line: 'Naye khariddar position bana rahe hain, premium bhi saath de raha hai.',
  },
  'OI-PEAK-LAG': {
    short: 'OI PEAK PICHHE',
    line: 'Bhaav to nikal gaya par OI apne peak se peeche hai — sab ne saath nahi diya.',
  },
  'SQUEEZE-RELEASE': {
    short: 'SQUEEZE KHULA',
    line: 'Dabi hui position chhoot gayi — jo phase the wo bhaag rahe hain.',
  },
  'SQUEEZE-RISK': {
    short: 'SQUEEZE RISK',
    line: 'Ek taraf itni position phansi hai ki nikalne ki bhagdad ho sakti hai.',
  },
  'WALL-MIGRATION': {
    short: 'WALL KHISKI',
    line: 'Sabse badi OI wall apni jagah se khisak gayi — writers ne apna level badla.',
  },
  'ROLE-FLIP': {
    short: 'ROLE PALTA',
    line: 'Us strike ka role palat gaya — jo rok raha tha wo ab sahara hai (ya ulta).',
  },
  // Deliberately regime-neutral: this kind fires as FLOOR, CEILING or PINNED,
  // and the direction chip beside it now carries which one (evDir reads the
  // regime off the message). A line saying "dono taraf dabti hai" would be
  // describing PINNED only, and would contradict the chip on the other two.
  'GAMMA-PIN': {
    short: 'PIN — CHIPKA',
    line: 'Dealer hedging bhaav ko strike ke aas-paas rok rahi hai — kis taraf, wo aage ki line batati hai.',
  },

  // --- end of day ----------------------------------------------------------
  // engine.py's carry_verdict: how much of the day's OI build each book KEPT
  // into the close (and, on expiry day, that nothing carries at all). It is a
  // next-session note, not an intraday event — hence no direction word here;
  // the engine's own line says which way the retained OI leans.
  CARRY: {
    short: 'RAAT BHAR KA CARRY',
    line: 'Din bhar bana OI band hone tak kitna tika — yeh agli session ka jhukaav batata hai.',
  },

  // --- setup lifecycle and regime -----------------------------------------
  ARMED: {
    short: 'TAIYAAR',
    line: 'Setup taiyaar hai — trigger abhi baaki hai.',
  },
  CHOP: {
    short: 'CHOP — RUKO',
    line: 'Bekaar aage-peeche — is mein haath dalne ka faayda nahi.',
  },
  STATE: { short: 'HAALAT', line: 'Session ki haalat badli.' },
  'TREND-UP': { short: 'TREND UPAR', line: 'Bhaav lagatar VWAP ke upar chal raha hai.' },
  'TREND-DOWN': { short: 'TREND NEECHE', line: 'Bhaav lagatar VWAP ke neeche chal raha hai.' },
  BALANCE: { short: 'BALANCE', line: 'Dono taraf barabari — sirf kinare par scalp banta hai.' },
  COILING: { short: 'COILING', line: 'Bands sikud rahe hain — energy jama ho rahi hai.' },
  CONFLICT: {
    short: 'ULTA-PULTA',
    line: 'Ek hi minute mein ulte signal — abhi koi ek taraf nahi hai.',
  },
}

/** The gloss for an engine kind, or null when we have never seen that kind.
 *  Null is deliberate: the UI then shows the engine's own kind string, so a
 *  new event type reads as untranslated rather than as something else. */
export function glossOf(kind: string): Gloss | null {
  if (!kind) return null
  return G[kind.trim().toUpperCase()] ?? null
}

/** The caption a chart balloon carries: the Hinglish short when we have one,
 *  otherwise the engine's own kind, unchanged. */
export function pillText(kind: string): string {
  return glossOf(kind)?.short ?? kind
}

/**
 * How STRONG a claim a kind is making, which is a different question from
 * which way it points. Read off each kind's own emit text in engine.py:
 *
 *   'call'  the engine is saying the market DID something directional —
 *           "BULL TRAP SPRUNG", "band reversal", "spring". A read.
 *   'risk'  a warning about what could happen NEXT, explicitly not yet:
 *           "upside squeeze RISK BUILDING", a trap being SET, a setup ARMED
 *           but untriggered.
 *   'lean'  positioning or structure that tilts one way without predicting a
 *           move: "PE writers pressing … → BULLISH", a gamma FLOOR whose text
 *           says dips get absorbed, a book that is "reversal fuel".
 *
 * This exists because the direction chip was wording all three identically as
 * "ishaara" (a read). On 2026-07-30 the 'call' kinds ran 15/18 at +30m while
 * the 'lean' and 'risk' kinds ran 11/27 — a warning dressed as a read is the
 * kind of thing that gets acted on. One session proves nothing about the hit
 * rates, but it is reason enough not to let a risk warning borrow a read's
 * wording.
 */
export type Claim = 'call' | 'risk' | 'lean'

const CLAIM: Record<string, Claim> = {
  ABSORPTION: 'call',
  CLIMAX: 'call',
  IGNITION: 'call',
  DIVERGENCE: 'call',
  'TRAP-SPRUNG': 'call',
  SPRING: 'call',
  'SPRING-FAIL': 'call',
  'BAND-REVERSAL': 'call',
  'BAND-BREAK': 'call',

  'SQUEEZE-RISK': 'risk',
  'TRAP-SETTING': 'risk',
  TRAP: 'risk',
  ARMED: 'risk',

  CAMPAIGN: 'lean',
  'BUYER-BUILD': 'lean',
  'GAMMA-PIN': 'lean',
  'OI-PEAK-LAG': 'lean',
  PRESS: 'lean',
  'WALL-MIGRATION': 'lean',
  'ROLE-FLIP': 'lean',
  CARRY: 'lean',
}

/** Defaults to the WEAKEST claim. An unknown kind cannot have a direction
 *  anyway (evDir returns 0 for anything it does not name), so this is
 *  unreachable in practice — but if that ever changes, understating a new
 *  event beats promoting it to a read nobody wrote. */
export function claimOf(kind: string): Claim {
  return CLAIM[kind?.trim().toUpperCase()] ?? 'lean'
}

/** Which way this event points, in the operator's own words, worded to match
 *  what the kind actually claims. `tone` is decided upstream by evDir
 *  (data.ts) — this only names it, and never upgrades a warning into a read.
 *  'structure' is a level event: it has a side on the chart but the engine
 *  called no direction from it, and saying otherwise would invent one. */
export function dirText(
  tone: Narration['tone'], kind = '',
): { arrow: string; text: string } {
  if (tone === 'structure') return { arrow: '◆', text: 'level ki baat — direction nahi' }
  if (tone !== 'bull' && tone !== 'bear') return { arrow: '—', text: 'direction saaf nahi' }
  const up = tone === 'bull'
  const arrow = up ? '▲' : '▼'
  const side = up ? 'UPAR' : 'NEECHE'
  const claim = claimOf(kind)
  if (claim === 'risk') return { arrow, text: `${side} ka RISK — abhi hua nahi` }
  if (claim === 'lean') return { arrow, text: `jhukaav ${side} — ishaara nahi` }
  return { arrow, text: `${side} ka ishaara` }
}
