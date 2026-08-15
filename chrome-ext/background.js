// The ONLY reason this file exists: in MV3 a content-script fetch is treated as
// coming from the page origin, so kite.zerodha.com -> 127.0.0.1:8765 is blocked
// by CORS. A service-worker fetch runs with the extension's host_permissions and
// is not. So the panel asks, and this fetches.
//
// No polling loop here on purpose -- the content script owns the cadence, so a
// backgrounded tab is not still hammering the server.

const ROOT = 'http://127.0.0.1:8765/api'

const get = (path) =>
  fetch(`${ROOT}${path}`, { cache: 'no-store' }).then((r) =>
    r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))
  )

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg?.kind !== 'tape') return
  const idx = ['NIFTY', 'BANKNIFTY', 'SENSEX'].includes(msg.idx) ? msg.idx : 'NIFTY'
  // /api/health rides along on every poll rather than being cached once,
  // because the thing it catches is a server RESTARTED onto another broker
  // mid-session. A cached broker would be right at load and wrong exactly
  // when it matters. Two localhost GETs per 15s is not a cost worth saving.
  // Health failing alone must NOT blank the panel, hence the inner catch:
  // an older server with no /api/health still serves a perfectly good tape.
  Promise.all([get(`/data?idx=${idx}`), get('/health').catch(() => null)])
    .then(([data, health]) => reply({ ok: true, data, health }))
    // The panel must be able to say WHY it is blank. A silent failure here
    // looks identical to a quiet market, which is the one thing it must never
    // look like.
    .catch((e) => reply({ ok: false, error: String(e.message || e) }))
  return true
})
