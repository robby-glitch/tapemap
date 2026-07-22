# Brief: TapeMap redesign — "redesign, i didn't like any of this"

## Product
TapeMap: an intraday session tape-reader for Indian index options. It replays
(later: live-streams) one trading session across three synchronized books —
NIFTY futures (FUT), a call (CE) and a put (PE) at one strike — and narrates
the session as a story: states (BALANCE, COILING, ARMED, TREND-UP/DOWN),
and events (TRAP, DIVERGENCE, PRESS, SPRING, ARMED, IGNITION, CLIMAX,
ABSORPTION, BREAK, FLIP-TEST, CARRY).

## Data (already served, do not build a backend)
`GET /api/data` → `{ strike, days: [ { day, strike, pivots: {P,R1,R2,R3,S1,S2,S3},
bars: [ { t: "HH:MM", fut: {o,h,l,c,vwap,u1,d1,u2,d2,u3,d3,oi,v,z,vol_r,oi_slope,oi_r,prem_d,bw_r},
ce: {…same}, pe: {…same} } ],  events: [ { t, kind, msg } ] } ] }`
375 one-minute bars per day, 3 days. `z` = distance from VWAP in σ-band units.
`vol_r`/`oi_r` = percentile ranks 0..1. Use days[2] (Jul 17) as the hero day.

## The UI must let a trader answer in one glance
1. Where are we in the day's story right now (state + why)?
2. What is each book doing (price vs VWAP/σ, OI building or dumping, volume)?
3. Where is price relative to the levels that matter (pivots + the strike)?
4. What has happened so far (event narrative with hierarchy — ARMED /
   IGNITION / CLIMAX / CARRY are the money calls; BREAK/etc. are minor)?
5. Time control: a scrubber/replay affordance (can be minimal but present).

## Hard constraints
- Single self-contained file: `ui/redesign.html` (vanilla JS + inline CSS,
  no external fonts/libs/CDNs — must work offline).
- Fetch the real `/api/data`; no fabricated numbers.
- Dark theme (used during market hours), target 1280×720 and larger.
- Dense enough for daily professional use; this is an instrument, not a poster.

## Rejected directions — do NOT repeat these
1. Radial "mental map" with orbiting circle nodes — felt gimmicky.
2. Plain stacked thin-line lanes — information-complete but debug-tool flat.
3. Generic monospace amber terminal — severe, no identity.
4. Light paper editorial with serif headlines — wrong energy for live trading.
5. Glassy glow cockpit dashboard with gauge cards — generic "AI dashboard".

## What "great" means here
A creative leap in *composition* — how the story, the three books, the levels
and time relate spatially — not a reskin of a stacked-panel dashboard. Visual
excellence first: a distinctive, coherent, confident design language with real
typographic hierarchy and disciplined color (state colors carry meaning:
balance/neutral, coiling/amber, armed/violet, trend/green-red). It should look
like a purpose-built professional instrument with a strong point of view —
something a trader would screenshot and show off.
