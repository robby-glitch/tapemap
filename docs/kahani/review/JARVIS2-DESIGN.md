# JARVIS2: the professional redesign of the chart-decode replay (29 Oct 2026)

`mockup/jarvis2.html`, served at `http://localhost:8787/jarvis2.html?v=N`. `jarvis.html` is untouched; the data (`data_28oct.json`) and `export_mockup.py` are unchanged. Every line is still generated from the data, with the same rules as the demo she approved (pushes → the wall's answer, fuel, chapters, her triggers with the band verdict, blind / back, NO TRADE, SPEED, TOP / BOTTOM SIGNS, MANAGE).

## What changed, and why (as the trader)

| Change | Why a trader wants it |
|---|---|
| **State strip above the chart**: FIGHT (wall · OI · tested ×n · broke n · state), FUEL meter, SPEED meter, ALL 3, VERDICT for **both sides at this minute**, ROOM | The 2-second read. The old page made her wait for the next bubble; now the state is always on screen. VERDICT is continuous (the exporter has it per minute), not only when a trigger fires. |
| **ROOM** cell: "▲ 50f → 22,700s CE 100L · ▼ 50f → 22,600s PE 79L" | The first question in a trade: how far to the next wall each way, in futures points, with the wall's size. "open · no CE wall in 2 steps" when there is none (as after 12:51). |
| **§16 right panel: JARVIS** = LAST TRIGGER card (pts now, MANAGE state, trail band), the **feed** (every line, newest on top, click to jump), the **command box** | Her approved layout. The bubble keeps only the latest line; nothing it said is lost. |
| **Commands** (deterministic, screen only): `line 22750f` / `line 22700s`, `zone 22680-22720f`, `watch 22800s` (fires on touch with the read at that minute + "Telegram sent (simulated)"), `remove`, `clear`, `list`, `go 12:47`, `why?`, `what next?`, `status`, `wrong when?`; any order word → "I don't place orders." | §15.3's grammar, in English, answered from the frame. Max 10 watches. |
| **Pro chart**: 25-pt grid, 15-min ticks, crosshair with time + `f · s` price label, OHLC + Δ + V + VWAP + basis readout, live-price tag on the axis, **delta pane** (Dext footprint, per minute or per 3-min bar), **1m / 3m toggle** | 3-minute is her frame; the signs are computed on it. The s/f tag on every level is her standing rule. |
| **Her zones shaded**: d2→d3 green, u2→u3 red, plus d3 / u3 lines | The setup drawn as a setup, not as five lines. |
| **OI by strike** glued to the price axis (CE above the strike, PE below, ghost = the day's peak, numbers in L; "chain blind · as of HH:MM" when missing) | Walls with OI, minute by minute, without a separate ladder tab. One glance says which wall is the big one. |
| **Every §1d front drawn** (building solid, stalled thin, unwinding dashed) with an axis tag carrying **that wall's own record** (×tested·broke); the strip's FIGHT count follows the exporter's DASTAK stamps | Two different objects, two labelled counts: the fight, and the wall. |
| **Motion that means something**: a probe travels from the push ◆ to the wall and **pulses there until the answer**; BREAK? draws a crack; BROKEN shatters; NEW FLOOR draws in; fuel and speed meters fill | "Answer pending" is now visible on the chart, not only in a chip. |
| **Timeline scrubber** with markers (◆ pushes, red = BROKEN, ▲▼ triggers, T/B signs, fuel, blind band, backfilled tint, quiet stretches), hover to read, click or drag to jump; `[` `]` step between major lines | Evening review in seconds: jump to any event. |
| **NO TRADE as a state** (quiet since · what ends it; "can't see" in the hole): the strip cell lights, the chart veils, the bubble shrinks to one line | §15.2. |
| **BACK line carries the catch-up** ("While blind: high · low · FUEL SPENT 12:58"); lines inside the hole are tagged "backfilled on wake" | §16.6 J1b, as the replay. |
| **Evening review end card**: story chain; her triggers with verdict, every MANAGE line and the next-30-min path; walls tested / broke / defended; fuel runs with price start → spent; signs with the next 15 min; day numbers; coverage (real / rebuilt / blind / can't see) | Rows, not rates. |
| Light theme, Inter + JetBrains Mono, numbers first, short lines, `prefers-reduced-motion` honoured, voice toggle (off by default; speaks the major lines) | Her rules. |

Not done (deliberately): no CVD line (the oi-lab finding: CVD divergence at highs is inverted); no % anywhere; no order path.

## What I would add next
1. **A real "position" instead of the zone trigger**: her marked trade (voice.py's) drives the LAST TRIGGER card and MANAGE, as §17 says for J2.
2. **Big single-price prints at a wall** (her 198K / 300K misses, NOTEPAD) as a chip on the push line and a mark on the delta pane; the exporter needs the footprint rows.
3. **Watches that outlive the page**: `data/jarvis/jarvis_<day>.jsonl` (§15.6), so a watch set at 12:40 survives a restart.
4. **SENSEX / BANKNIFTY mini-rows** under the delta pane (their own OI walls, NIFTY's flow, per §1q).
5. **Hover on a chip** gives the plain meaning (§16.2 "a plain meaning on hover"): a title attribute per word.
