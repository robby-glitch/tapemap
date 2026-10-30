# KAHANI round 2 — how it should look and move, live (Fable, 28 Oct 2026)

**Mockup:** `docs/kahani/review/mockup/index.html` (standalone; data `mockup/data_28oct.json` from `scripts/export_mockup.py`, read-only). Serve the folder (`.claude/launch.json` → `kahani-mockup`, port 8787, or `python -m http.server` inside `mockup/`; on `file://` the page offers a file picker for the JSON). It replays **28 Oct NIFTY 11:07–13:40 with the recorded numbers**: play / pause / scrub / speed, space and ← → keys, a motion toggle, and `prefers-reduced-motion` honoured. No scripts are loaded at all (no CDN needed): SVG + CSS transitions only.

## 1. What she asked for, read as a trader

"3D websites kind of motion … show this real time what we expecting, what happening in the data." The useful half of that sentence is **expected vs actual**. The decorative half (3D) is the part to refuse unless depth carries a number. On a trading screen every motion is a claim: *this changed, by this much, now*. A motion that does not carry a number is noise she will learn to ignore, and then she ignores the one that mattered.

So the instrument has five moving things, each tied to one measured quantity:

| Thing | Motion | The number it carries | Duration |
|---|---|---|---|
| **Push** | a ◆ travels from the price line to the attacked wall's bar, on the push's side (▲ right into CE, ▼ left into PE) | `▲ +434 lots` on the diamond | 0.9 s, once, when the push becomes known (m+1) |
| **Answer** | TOOT: the wall bar loses a chunk and a cracked chip pops `TOOT −3.7L`; TIKI: the bar flashes and grows `TIKI +4.3L`; NAHI: nothing moves, the ◆ stays as a small stamp and the counter ticks `dastak ×5 · jawab 0`; TOOT? shows grey until it holds (`wapas` if it does not) | the chip's L and the minute | 0.8 s at the answer's known minute; the hold stamp at the next |
| **Wall** | bar length = OI now; a dotted ghost = today's peak; the gap between them is THAKAN in pixels | `27.8L · −24L peak se` | 0.5 s ease on each chain minute |
| **Fuel** | a tank fills (down for COVER, up for FRESH) toward the 2,500-lot top; the 500 bar is a dashed line; three dots fill as publishes pass with no new extreme; at KHATAM the tank caps and the chip goes grey | `−2,146 lots · shorts cover` · `2/3 publish` | 0.6 s per minute |
| **Verdict** | three pieces light ✓ / ✗ / ?; the word changes colour; a ribbon under the path strip paints one cell per minute | `CHALEGA 0/2 · 1 ?` and the piece texts | instant (a word must not animate) |

And one **ghost**: from the current price, two dotted paths curve to the two scenario targets (▲ the next CE wall, ▼ the NAYA FLOOR or PE front); the actual spot line draws over them as minutes pass. That is "expected vs actual" with no candles and no premium chart: price is a marker and a line against strikes (allowed by her rule), never a bar.

## 2. The options, and the pick

| Option | What it would show | Verdict as a trader |
|---|---|---|
| **3D battlefield (three.js)**: walls as towers on a strike axis, price as a sphere, pushes as projectiles | depth = time or OI; camera orbits | **No.** Depth carries nothing length does not; a camera means a viewpoint she has to manage; GPU load on the laptop that slept at 12:54; a dark-theme idiom. "3D" here would be a show. |
| **2.5D SVG ladder (CSS transitions)**: strikes vertical, PE left / CE right, bars + ghosts, ◆ travelling, price lines | every number readable at a glance, light theme, 2-second read | **Yes — the core.** It is her OI Flow ladder (the one tab she likes) made to move. |
| **Strike × time heat ribbon** | OI change per strike per minute as colour | good for the evening replay; on the live screen it is a chart, and she has charts | Replay mode only (a later panel). |
| **Fuel reservoir (tank)** | the run as a level, the bar as a line, KHATAM as a cap | the one picture a run needs; the publish clock as three dots is the KHATAM rule made visible | **Yes.** |
| **Verdict scale / gauge** | a needle between GHUMEGA and CHALEGA | a needle implies a continuum and a %; the verdict is three words and counts | **No.** Pieces + word + ribbon. |
| **Expected-vs-actual ghost path** | dotted scenario curves vs the actual line against strikes | the only honest "animation of expectation": it is scored (ADDITIONS #6) | **Yes.** |
| **Chapter chain** | pills with stamps, the current one filled | the story in one line; the chain *is* the evening review | **Yes.** |

**The pick:** 2.5D SVG ladder + fuel tank + chapter chain + verdict pieces + ghost-path strip, in that visual order (left to right, the reading order of the method: walls → pushes/answers → fuel → verdict). Light theme, system fonts, no library. Motion only on events, 0.5–0.9 s, off under `prefers-reduced-motion` and by the toggle.

## 3. The layout (the LADAI tab, live and replay are one face)

```
[ KAHANI · NIFTY · 12:50 ]  ⏮ ▶ ⏭  ───scrub───  speed  motion
┌ LADAI · chapter chain ──────────────────────────────┐ ┌ DIKH NAHI RAHA ─────────┐
│ DEEWAR 11:07 → DASTAK ×3 → THAKAN 12:13 → TOOT 12:44 │ │ push: book se 11:07     │
│ → RASAD cover ▲ 12:49 → NAYA FLOOR 12:54 → ...       │ │ book hole 12:54–13:00   │
│ toot 12:44 · rasad cover ▲ −1,215 · shorts cover     │ │ chain nahi 12:55–12:59  │
│ ▲ jab tak run chale → 22,800s CE  ▼ KHATAM pe → 22,700s PE  lag: pata 12:47 · screen 12:49:50 │
├ DEEWAR LADDER ───────────┬ RASAD ──────────┬ BAND VERDICT · SELL ─────────────────┤
│ PE ◀ bars │ CE bars ▶     │ [tank]  −1,215  │ CHALEGA  0/1 · 2 ?                    │
│  22,800   ░░░░░ 22.5L     │ cover ▲ · 12:41 │ ✗ FUEL  cover ▲ −1,215 chal raha      │
│  22,700 ━━━━━ ▓▓▓▓ 27.8L │ ●●○ 2/3 publish │ ? NEXT PUSH  abhi push nahi           │
│        ◆◆◆◆◆ dastak ×5    │ ▁▂▁▁▇▆▅ 30 min  │ ? ULTA PUSH  abhi push nahi           │
│  22,600 ▓▓▓▓▓ 22.0L       │                 │ zone  ARM  TRIGGER  +5  +10  +15/+30  │
├ RAASTA · spot vs strikes · ummeed (ghost) vs asal ───────────────────────────────────┤
│ 22,800 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ·····▲ 22,800s │
│ 22,700 ▒▒▒▒▒▒▒▒▒▒▒▒▒▒ wall band ▒▒▒▒▒▒▒▒▒ ◆ ◆ ▽SELL ◆ ◆ ◆ ◆ ╱━━━╮              │
│ 22,600 ─ ─ ─ ─ ─ ━━━━━━━╯╰━━━━╯ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ·····▼ 22,700s │
│ ribbon: ▓▓▓░░▓░▓░▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ (verdict per minute)                           │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

Rules the face keeps: every symbol has a Hinglish chip with its number; ≤ 6 words per line plus numbers; s / f on every level; no %; three sentences (checked-nothing / could-not-check / not-shown) kept apart in the coverage box; colour by **side** on the ladder (CE rust, PE blue), by **meaning** only on the verdict word (green / red / grey).

## 4. What the mockup shows that the spec did not

Running it end to end over 28 Oct surfaces, in motion, the findings the rows gave:

- **11:40–11:51:** the ribbon alternates green / grey six times while nothing on the ladder moves: §1d's STALL↔UNWIND flicker reaching the verdict (D1). You see why the WALL piece must use the held state.
- **12:09 → 12:12:** ARM GHUMEGA 2/2 turns TRIGGER CHALEGA 0/2 in three minutes: the −775 cover run starts (the tank fills down) and the wall turns UNWINDING. The zone row's two cells side by side are the whole 12:12 lesson.
- **12:44 → 12:49:** the ◆ lands, the chip reads `TOOT? −3.7L` grey at 12:48, turns red `TOOT` at 12:49; the lag line says `pata 12:47 · screen 12:49:50`. Three different times for one event, all visible.
- **12:54–13:00:** the coverage box grows a line (`laptop soya`), the chain's bars freeze (`chain nahi`), the tank keeps filling from REST (dashed strip cells). The fuel is the one thing that moved while the laptop slept.
- **13:03:** the tank caps (`KHATAM −2,146`), the verdict goes (b) SAAF NAHI 1/1 · 2 ?: the two "?" pieces are visibly empty — the honest trigger.
- **13:31 → 13:37:** PIN stamps, GHUMEGA 2/2, then the new fight reads CHALEGA 2/3 on a dead run's memory, then SAAF NAHI, then GHUMEGA (D2). Six minutes of words on a pinned market.

## 5. From mockup to the LADAI tab

- The mockup's JSON is the shape `/api/kahani` should return: `timeline[]` (one row per minute: chapter, wall, fuel, fronts, dastak, ulta, naya_floor, khatam, ending), `pushes[]`, `runs[]`, `verdict{side}{minute}`, `zone[]`, `holes`, `chain_missing`, `fights[].stamps`. The face renders `timeline[i]`; LIVE is `i = last`, REPLAY is the scrub.
- The templates in the hero (`drawHero`) are the ≤ 6-word sentences per chapter (decided Q77); they belong in `kahani.py` with `test_kahani.py` checking each, not in the face.
- Motion: the five events above only; on each new minute the bars ease (0.5 s), nothing else moves unless an event happened that minute. A screen that moves once a minute, for under a second, is readable in 2 seconds.
- The GoCharting ribbon (step 3, decided Q74) is one line of this: the current chapter pill + `dastak ×n · jawab j` + the fuel arrow with lots.

## 6. Known limits of the mockup

- It applies the rules as `export_mockup.py` reads them (causal, per minute). It is a reading, not the engine; `test_kahani.py` must reproduce its stamps before any of them is trusted.
- The ▲ / ▼ scenario targets are the next CE front / the NAYA FLOOR or PE front; `pehla padav` (VWAP / u1) is not in the export (the zone3 bands are not in the record's rows I read). Add when `/api/kahani` carries them.
- SELL verdicts only are drawn (all three 28 Oct triggers were SELLs); the BUY series is in the JSON.
- The chain's 10:37 peak is not in the live record (finding 7), so the ladder's ghost for 22,700s CE starts at 11:08's +49.8L.
