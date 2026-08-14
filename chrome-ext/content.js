// The TapeMap panel, injected beside the Kite chart.
//
// IT DRAWS NOTHING ON THE CHART, and that is a decision, not a shortcut:
//   1. Kite already draws the sigma bands -- that is the operator's own SDVWAP
//      study, the thing the whole setup is read off.
//   2. Our bands DO NOT MATCH THEIRS (research-findings.md 1c: our sigma runs
//      1.02-1.08 wider, ~5 pts at 3-sigma in the afternoon). Overlaying ours
//      would put two sets of blue bands on one screen a few points apart, and
//      the operator would be staring at a known bug all day.
// So this shows only what Kite CANNOT compute: everything downstream of the
// option chain. Zero overlap, nothing to disagree about.

const POLL_MS = 15000 // the server itself refreshes at 15s
const STALE_S = 150 // older than this and the tape is frozen, not quiet

const $ = (t, c, txt) => {
  const e = document.createElement(t)
  if (c) e.className = c
  if (txt != null) e.textContent = txt
  return e
}

let idx = localStorage.getItem('tapemap.idx') || 'NIFTY'

function build() {
  const p = $('div', 'tm-panel')
  const head = $('div', 'tm-head')
  head.appendChild($('span', 'tm-brand', 'TAPEMAP'))
  const right = $('span', 'tm-right')
  const sel = document.createElement('select')
  sel.className = 'tm-idx'
  for (const n of ['NIFTY', 'BANKNIFTY', 'SENSEX']) {
    const o = document.createElement('option')
    o.value = n
    o.textContent = n
    sel.appendChild(o)
  }
  sel.value = idx
  sel.addEventListener('change', () => {
    idx = sel.value
    localStorage.setItem('tapemap.idx', idx)
    tick()
  })
  right.appendChild(sel)
  right.appendChild($('span', 'tm-age', '--'))
  head.appendChild(right)

  const body = $('div', 'tm-body')
  body.appendChild($('div', 'tm-msg', 'connecting...'))
  p.appendChild(head)
  p.appendChild(body)
  document.body.appendChild(p)
  drag(p, head)
  return p
}

// Drag by the header. Position persists -- the operator puts it where their
// chart is not, and it must stay there across reloads.
function drag(panel, handle) {
  let saved = null
  try {
    saved = JSON.parse(localStorage.getItem('tapemap.pos') || 'null')
  } catch (e) {
    saved = null
  }
  if (saved && saved.t && saved.l) {
    panel.style.top = saved.t
    panel.style.left = saved.l
    panel.style.right = 'auto'
  }
  let sx = 0
  let sy = 0
  let ox = 0
  let oy = 0
  let on = false
  handle.addEventListener('mousedown', (e) => {
    if (e.target.tagName === 'SELECT') return
    on = true
    sx = e.clientX
    sy = e.clientY
    const r = panel.getBoundingClientRect()
    ox = r.left
    oy = r.top
    e.preventDefault()
  })
  window.addEventListener('mousemove', (e) => {
    if (!on) return
    panel.style.left = ox + e.clientX - sx + 'px'
    panel.style.top = oy + e.clientY - sy + 'px'
    panel.style.right = 'auto'
  })
  window.addEventListener('mouseup', () => {
    if (!on) return
    on = false
    localStorage.setItem(
      'tapemap.pos',
      JSON.stringify({ t: panel.style.top, l: panel.style.left })
    )
  })
}

function cell(label, value) {
  const c = $('div', 'tm-cell')
  c.appendChild($('div', 'tm-k', label))
  c.appendChild($('div', 'tm-v', value))
  return c
}

function render(panel, payload) {
  const body = panel.querySelector('.tm-body')
  body.textContent = ''

  const days = payload.days || []
  const day = days[days.length - 1]
  const bars = (day && day.bars) || []
  if (!bars.length) {
    body.appendChild($('div', 'tm-msg', 'no bars in the payload yet'))
    return
  }

  const b = bars[bars.length - 1]
  const ctx = b.ctx || {}

  const v = $('div', 'tm-verdict')
  const word = String(ctx.verdict || '').split(' ')[0].toLowerCase()
  v.appendChild($('span', 'tm-badge tm-' + word, ctx.verdict || '--'))
  if (ctx.vwhy) v.appendChild($('span', 'tm-why', ctx.vwhy))
  body.appendChild(v)

  if (ctx.line) body.appendChild($('div', 'tm-line', ctx.line))

  const grid = $('div', 'tm-grid')
  grid.appendChild(cell('dealer', (b.gamma && b.gamma.regime) || '--'))
  const pin = ctx.pin
    ? ctx.pin.k + ' ' + (ctx.pin.dist > 0 ? '+' : '') + ctx.pin.dist
    : '--'
  grid.appendChild(cell('pin', pin))
  body.appendChild(grid)

  // The zone. Newest signal wins; the backend's own trigger text is quoted
  // VERBATIM so it can be checked against the candle rather than trusted.
  const sigs = ((day && day.rotation) || []).filter(Boolean)
  const s = sigs[sigs.length - 1]
  const z = $(
    'div',
    'tm-zone ' + (s ? (s.side === 'BUY' ? 'tm-buy' : 'tm-sell') : 'tm-none')
  )
  if (s) {
    const h = $('div', 'tm-zhead')
    h.appendChild($('span', null, 'ZONE - ' + (s.side === 'BUY' ? 'lower' : 'upper')))
    h.appendChild($('span', 'tm-tag', s.side + ' ' + s.band))
    z.appendChild(h)
    z.appendChild($('div', 'tm-trig', s.t + ' - ' + s.trigger))
    z.appendChild($('div', 'tm-flags', 'trap ' + s.trap + ' - confirm ' + s.confirm))
  } else {
    z.appendChild($('div', 'tm-zhead', 'ZONE - no signal today'))
  }
  body.appendChild(z)

  const lv = $('div', 'tm-levels')
  if (ctx.cap) lv.appendChild($('div', 'tm-row', 'cap   ' + ctx.cap[1] + '  ' + ctx.cap[0]))
  if (ctx.floor) lv.appendChild($('div', 'tm-row', 'floor ' + ctx.floor[1] + '  ' + ctx.floor[0]))
  if (lv.children.length) body.appendChild(lv)

  if (b.ce && b.pe) {
    const m = (n) => (n / 1e6).toFixed(2) + 'M'
    body.appendChild(
      $('div', 'tm-oi', 'OI ' + payload.strike + '   CE ' + m(b.ce.oi) + '   PE ' + m(b.pe.oi))
    )
  }
}

function tick() {
  const panel = document.querySelector('.tm-panel') || build()
  const body = panel.querySelector('.tm-body')
  const age = panel.querySelector('.tm-age')
  chrome.runtime.sendMessage({ kind: 'tape', idx: idx }, (res) => {
    if (chrome.runtime.lastError || !res) {
      body.textContent = ''
      body.appendChild($('div', 'tm-msg tm-bad', 'could not reach the extension worker'))
      return
    }
    if (!res.ok) {
      // Name the real cause: nine times in ten the server is simply not running.
      body.textContent = ''
      body.appendChild($('div', 'tm-msg tm-bad', 'no tape - ' + res.error))
      body.appendChild($('div', 'tm-msg', 'is the TapeMap server up on 127.0.0.1:8765?'))
      age.textContent = '--'
      age.className = 'tm-age tm-bad'
      return
    }
    const secs = Math.round(Date.now() / 1000 - (res.data.built_at || 0))
    render(panel, res.data)
    age.textContent = secs + 's'
    age.className = 'tm-age' + (secs > STALE_S ? ' tm-bad' : '')
    if (secs > STALE_S) {
      body.prepend($('div', 'tm-msg tm-bad', 'tape is ' + secs + 's old - frozen, not quiet'))
    }
  })
}

build()
tick()
setInterval(tick, POLL_MS)
