// The ONLY reason this file exists: in MV3 a content-script fetch is treated as
// coming from the page origin, so kite.zerodha.com -> 127.0.0.1:8765 is blocked
// by CORS. A service-worker fetch runs with the extension's host_permissions and
// is not. So the panel asks, and this fetches.
//
// No polling loop here on purpose -- the content script owns the cadence, so a
// backgrounded tab is not still hammering the server.

const BASE = 'http://127.0.0.1:8765/api/data'

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg?.kind !== 'tape') return
  const idx = ['NIFTY', 'BANKNIFTY', 'SENSEX'].includes(msg.idx) ? msg.idx : 'NIFTY'
  fetch(`${BASE}?idx=${idx}`, { cache: 'no-store' })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
    .then((data) => reply({ ok: true, data }))
    // The panel must be able to say WHY it is blank. A silent failure here
    // looks identical to a quiet market, which is the one thing it must never
    // look like.
    .catch((e) => reply({ ok: false, error: String(e.message || e) }))
  return true
})
