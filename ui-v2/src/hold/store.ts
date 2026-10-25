// The two fetch pieces the faces share since the 25 Oct review (C8): j(), an 8 s bound on every fetch (pro/api.ts,
// trade/engine.ts, data.ts's TIMEOUT_MS), and tone(). The hold poller that lived here (/api/hold?id=, for the deleted hold/*
// windows) is gone with its route.
export const TIMEOUT_MS = 8000   // the one fetch bound: j() below, and data.ts's 5 s poll (25 Oct review F10)

/** fetch with an 8 s abort: a slow server never stacks polls or hangs a button (REVIEW P1-18). */
export async function j<T>(url: string, body?: unknown, raw?: string): Promise<T> {
  const ac = new AbortController(), t = setTimeout(() => ac.abort(), TIMEOUT_MS)
  try {
    const r = await fetch(url, {
      signal: ac.signal, ...(body === undefined && raw === undefined ? {} : {
        method: 'POST', headers: { 'Content-Type': raw !== undefined ? 'text/csv' : 'application/json' },
        body: raw !== undefined ? raw : JSON.stringify(body) }) })
    return await r.json()
  } finally { clearTimeout(t) }
}
// one tone on a transition into FOLD, default ON (REVIEW P1-13); one AudioContext, unlocked by her first click
let ctx: AudioContext | null = null
if (typeof window !== 'undefined') window.addEventListener('pointerdown', () => { try { ctx ??= new AudioContext(); ctx.resume() } catch { /* no audio */ } }, { once: true })
export function tone(hz = 520, ms = 450) {
  try {
    ctx ??= new AudioContext()
    const o = ctx.createOscillator(), g = ctx.createGain()
    o.frequency.value = hz; g.gain.value = 0.08
    o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime + ms / 1000)
  } catch { /* no audio: the red header still says it */ }
}
