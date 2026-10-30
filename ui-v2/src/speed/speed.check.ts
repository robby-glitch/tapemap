// The one check for speed.ts. Run: node --experimental-strip-types src/speed/speed.check.ts (from ui-v2/)
import assert from 'node:assert/strict'
import { read, accelOf, resultOf } from './speed.ts'
import type { Minutes } from './speed.ts'

const hm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
// CE 22700 writes 1L a minute to 09:30, holds to 09:40, cuts 1L a minute to 09:50, then writes again; spot +1 a minute
const ce = (m: number) => (m <= 570 ? m - 555 : m <= 580 ? 15 : m <= 590 ? 15 - (m - 580) : 5 + (m - 590)) * 1e5
const grid: Minutes = {}
for (let m = 555; m <= 600; m++) grid[hm(m)] = { spot: 22700 + (m - 555), k: { '22700': [ce(m), 0], '22750': [0, 0] } }

const r = read(grid)!
const st = r.stamps.filter((s) => s.side === 'CE' && s.k === 22700).reverse().map((s) => `${s.t} ${s.word}`)
assert.deepEqual(st, ['09:20 likhne lage', '09:35 ruk gaye', '09:41 chhodne lage', '09:53 phir likhne lage'])
const c = r.cells.find((x) => x.side === 'CE' && x.k === 22700)!
assert.equal(c.flow, 'W'); assert.equal(c.since, '09:53'); assert.equal(c.spd, 1e5); assert.equal(c.vs, 5)  // writing into a rise
assert.equal(resultOf(c.flow, c.vs, r.step), 'price ruka')                                                // 5 pts < 0.2 x 50

// a hole in the record gives no speed for the minutes that would read across it, and nothing crashes
const holed: Minutes = { ...grid }
delete holed['09:55']                                                       // the mark 5 minutes before the last
const h = read(holed)!.cells.find((x) => x.side === 'CE' && x.k === 22700)!
assert.equal(h.spd, null); assert.equal(h.before, null); assert.equal(h.vs, null)

assert.equal(accelOf(3, 1, 0.1), 'tez'); assert.equal(accelOf(1, 1, 0.1), 'barabar'); assert.equal(accelOf(0.5, 1, 0.1), 'dheema')
assert.equal(accelOf(-1, 1, 0.1), 'palta'); assert.equal(accelOf(1, 0.05, 0.1), 'shuru'); assert.equal(accelOf(0.05, 0.05, 0.1), null)
assert.equal(resultOf('W', 20, 50), 'ulta likh rahe'); assert.equal(resultOf('W', -20, 50), 'saath')
assert.equal(resultOf('C', 20, 50), 'bhaag rahe'); assert.equal(resultOf('C', -20, 50), 'booking'); assert.equal(resultOf('R', 20, 50), null)
assert.equal(read({}), null)
console.log('speed.check ok')
