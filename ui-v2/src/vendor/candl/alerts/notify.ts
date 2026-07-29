// Browser-side alert firing: permission, crossing detection, notification +
// in-DOM toast fallback, and the chosen alert tune (synthesized in ./tunes).
// This module owns the Notification + DOM APIs for alerts (sound is delegated
// to ./tunes); it holds no React and is driven by the host (ChartView) per tick.

import type { Alert } from './types'
import { playTune } from './tunes'
import { formatPrice } from '../components/format'

/**
 * Request the browser Notification permission. Resolves to whether we can show
 * notifications: true only when permission is (or becomes) 'granted'. Safe to
 * call repeatedly — once 'denied'/'granted' the browser answers without a prompt.
 */
export async function ensureNotificationPermission(): Promise<boolean> {
  if (typeof Notification === 'undefined') return false
  if (Notification.permission === 'granted') return true
  if (Notification.permission === 'denied') return false
  try {
    const result = await Notification.requestPermission()
    return result === 'granted'
  } catch {
    // Some browsers throw on the legacy callback form — treat as not granted.
    return false
  }
}

/** Human-readable fire message, e.g. "BTCUSDT crossed above 64,000 — take profit". */
function fireMessage(alert: Alert): string {
  const base = `${alert.symbol} crossed ${alert.condition} ${formatPrice(alert.price)}`
  return alert.message && alert.message.trim() !== '' ? `${base} — ${alert.message.trim()}` : base
}

/** Show a native notification if permission is granted; returns whether it was shown. */
function showNotification(alert: Alert): boolean {
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return false
  try {
    new Notification('CandL price alert', { body: fireMessage(alert), tag: alert.id })
    return true
  } catch {
    return false
  }
}

/** Transient in-DOM toast used when notifications aren't available. Auto-removes after ~6s. */
function showToast(alert: Alert): void {
  if (typeof document === 'undefined') return
  const el = document.createElement('div')
  el.className = 'alert-toast'
  el.setAttribute('role', 'status')
  el.textContent = fireMessage(alert)
  document.body.appendChild(el)
  // Trigger the enter transition on the next frame.
  requestAnimationFrame(() => el.classList.add('show'))
  const remove = () => {
    el.classList.remove('show')
    // Wait out the fade before detaching.
    window.setTimeout(() => el.remove(), 250)
  }
  window.setTimeout(remove, 6000)
  el.addEventListener('click', remove)
}

export interface CheckAndFireOpts {
  /** The chart's current symbol — only alerts for this symbol are evaluated. */
  symbol: string
  /** The latest price (live candle close). */
  price: number
  /** The previous price tick, or null on the first tick after a (re)load. */
  prevPrice: number | null
  /** All alerts (any symbol); this fn filters to `symbol` + untriggered. */
  alerts: Alert[]
  /** Whether to play the alert tune on fire. */
  soundOn: boolean
  /** Which of the 10 tunes to play (0-based index). */
  tune: number
  /** How long the tune plays, in seconds. */
  tuneDurationSec: number
  /** Called once per fired alert with the firing timestamp (epoch ms). */
  onTriggered: (id: string, triggeredAt: number) => void
}

/**
 * Evaluate alerts against the latest price and fire any that just crossed.
 * Crossing semantics (per alert, only while triggered === false):
 *   above: prevPrice < price && price >= alert.price   (or prev null && price >= alert.price)
 *   below: prevPrice > price && price <= alert.price    (or prev null && price <= alert.price)
 * Each fired alert shows a notification (or toast fallback), optionally beeps,
 * and is reported via onTriggered so the store marks it triggered (coalescing
 * to exactly one fire). Call this on every live price tick.
 */
export function checkAndFireAlerts(opts: CheckAndFireOpts): void {
  const { symbol, price, prevPrice, alerts, soundOn, tune, tuneDurationSec, onTriggered } = opts
  if (!Number.isFinite(price)) return

  for (const alert of alerts) {
    if (alert.symbol !== symbol || alert.triggered) continue

    let crossed: boolean
    if (alert.condition === 'above') {
      crossed = prevPrice === null ? price >= alert.price : prevPrice < alert.price && price >= alert.price
    } else {
      crossed = prevPrice === null ? price <= alert.price : prevPrice > alert.price && price <= alert.price
    }
    if (!crossed) continue

    if (!showNotification(alert)) showToast(alert)
    if (soundOn) playTune(tune, tuneDurationSec)
    // Report the fire — the store flips triggered=true, so the next tick skips it.
    onTriggered(alert.id, Date.now())
  }
}
