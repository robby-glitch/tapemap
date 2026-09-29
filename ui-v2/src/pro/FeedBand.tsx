// THE FEED BAND (P3, feed_health.py): is the GoCharting tape alive? One component on every TapeMap face (DESK, the floating
// window's body, the Trade tab). DEAD is inverse ink and names the fix; SLOW and STALLED are amber and quieter; LIVE draws
// nothing; NOT OPEN TODAY and AFTER CLOSE are one grey line (an absence with its reason, never an alarm). No sound: off
// until she signs N after the hidden-tab measurement. The words are the server's; this file computes nothing.
import type { Feed } from './api'

/** Her Chrome setting, not ours (7-final-design §3.1 P3): the hover on the DEAD band. */
export const MEMORY_SAVER_HINT = 'Your Chrome setting, not ours: Settings > Performance > Memory Saver > "Always keep these sites active" > add gocharting.com'

export default function FeedBand({ feed, compact = false }: { feed: Feed | null | undefined; compact?: boolean }) {
  if (!feed || !feed.state || feed.state === 'LIVE') return null
  const s = feed.state
  if (s === 'NOT OPEN TODAY' || s === 'AFTER CLOSE')
    return compact ? null : <p className="feedline" title={feed.why ?? ''}>{feed.chip ?? s}</p>
  const dead = s === 'DEAD'
  const title = dead ? [feed.why, feed.do, MEMORY_SAVER_HINT].filter(Boolean).join('\n') : (feed.why ?? '')
  return <div className={`feedband ${dead ? 'dead' : 'amber'}`} role="alert" title={title}>
    <b>{feed.chip ?? s}</b>
    {!compact && dead && <span className="sub">GoCharting reads: could not check (last GoCharting bar {feed.last_bar ?? '?'}) · Upstox reads continue</span>}
    {!compact && !dead && feed.why && <span className="sub">{feed.why}</span>}
  </div>
}
