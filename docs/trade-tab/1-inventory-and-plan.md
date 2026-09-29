# Trade tab: 1. Inventory and plan (phase 1)

**Written:** 2026-09-29, after the close.
**What was done:**
- read every file in `ui-v2/src/trade/`, the Trade tab mount in `App.tsx`, the levels builder in `data.ts`, the DESK files (read-only), `docs/pro-tool/6-blueprint.md`, `API-v3.md` and `docs/review/TRADER-AUDIT-2026-09-28.md`;
- read-only GETs on the running server at about 16:30;
- rendered the tab's text on 5173.

**What was not done:** no code was edited, no server was started or restarted, nothing under `data/` was touched, and nothing was committed.

**Files written:**
- this plan;
- `mockup-2026-09-29.html`: the proposed face drawn from today's real numbers, LIGHT. Its generator is in the session scratchpad, not in the repo.

**Tags:** [M] measured, [I] inferred.

---

## What was checked today

These are the facts every verdict below rests on. All are [M] from GETs unless tagged otherwise.

| # | check | result |
|---|---|---|
| E1 | `/api/data?idx=NIFTY&interval=3`: `zone_state` and `zone_state_sell` (her machine: d2 to d3 buy, u2 to u3 sell) | **Her setup fired twice today.** BUY d2 triggered 09:39 (level 22585.7). SELL u2 triggered 12:18 (level 22758.64). |
| E2 | the same payload: `run_state`, `rotation_run`, `rotation_run_sell` (the §5c d3 line machine) | WAITING on all 125 of 125 bars. 0 entries. **This is the machine the Trade tab's SETUP CHECK and chart markers read.** At 3m, the tab printed "Aaj is timeframe par ek bhi entry nahi bani" (no entry today on this timeframe) on a day her zone fired twice. |
| E3 | `zone_state` at `interval=5` | A different machine: no BUY at all, and SELL at 12:20. The zone machine is recomputed per interval. Only 3-minute is her setup (CLAUDE.md rule 3; `server._hold_machine` reads it at `SCORED_INTERVAL`). |
| E4 | page text at 3m, and screenshot `5.png` at 5m | The tab renders hit-rate text: "68.4% hit at +30m, n=19" (`SetupCheck.tsx:916`), "68.4% (n=19)" (`:914`), "68.4% ise haasil nahi hai" (68.4% does not apply to this) (`:908`), "d3 BUY wali 68.4%" (the d3 BUY's 68.4%) (`TradeTab.tsx:1008`). **House-rule violation.** |
| E5 | `/api/fold/flat?idx=NIFTY` | `next_fight` above 22728 ("429 lots of buyers trapped at 11:40"), below 22701. The four rows are ZONE QUIET, FLOW QUIET, OI QUIET, VPIN BUYERS. The day: "sellers' day (20 fights to 19) · value 22685 (22615–22710) [I] · boxed in value". `marks`: 124 (30 wall, 30 won of which 6 by price, 28 trapped, 27 released, 9 absorbed, 0 disputed). |
| E6 | pairing `trapped` with `released` by (px, side) | 27 of 27 released marks match a trapped mark. 1 is still live at the close: 429 lots of buyers trapped at 22727.9 since 12:28, which is the NEXT FIGHT above. |
| E7 | the newest `wall` mark per side | 22750 CE named at 22752 (15:28:34), and 22650 PE named at 22652 (15:27:19). The px is already K + basis. |
| E8 | `/api/hold/trades` and `/api/fold?id=NIFTY-22800PE-long-091807` | One trade: long 22800 PE, 113.95, entered 09:18:07, exited 09:35:26. The view is frozen at the exit: HOLD, "against you: zone since 09:34, flow since 09:34 · behind you: OI". G 22711 (set 09:32, trailed); W 22700 CE 208.8L `state: building`; A 22600 PE at px 22604, 180.6L, peak 09:34, 21 pts; E 22721.5; `units.basis` 3.5. |
| E9 | the same view: `A` compared with `W`; `events` | `W` has `state` but no `px`. `A` has `px` but no `state`. `events` is trimmed to the last 12 (`fold_live.EVENTS_SHOWN`). The `seed` and `reset` events that move G carry no px, so no G history can be read from the view. |
| E10 | `/api/fold/flat` for BANKNIFTY and SENSEX | "could not check — the engine has not started on this index". `fold_live.ALWAYS = ("NIFTY",)`: another index is read only while it has a marked trade. |
| E11 | `/api/data` `basis` compared with fold's `basis` | `/api/data` basis = −1.0: future minus the chain's index spot. `data.ts:798` `toTape` uses it for the CALL/PUT walls, PIN, STK, MAX PAIN and GEX FLIP. fold's basis = 2.8–3.5: future minus the options' forward. They agree today only because the future and the options expired together. The audit measured spot 33–49 pts below the forward on 28 Sep, so those lines sit that far off on a normal day [M, audit], [I] for any given day. |
| E12 | `/api/tape?idx=NIFTY`, session value area | The GoCharting record has POC 22598.8 (VAL 22580.5, VAH 22691.1). The Upstox ux family has POC 22682.5 (VAL 22612.5, VAH 22712.5). **The two POCs are 84 pts apart on one chart.** The day is bimodal: both families have HVNs at 22600 and 22685. The engine's value is 22685 (22615–22710), which agrees with ux. `prior` is `[]` with `prior_why` "earlier days' contract was not recorded (before the contract stamp)", so the roll guard is live. |
| E13 | `/api/tape` marks | ux runs: 215, all drawn (these are the green/red "$" circles; the glyph is a lowercase `s` in a ring). tm: 9. ofd: 57, **each with `side`**. Stacks: 8–9. Unfinished auctions: 1. |
| E14 | `/api/day/record?idx=NIFTY` (the P/A/E/C source) | 33 events: trap 4, absorption 8, exhaustion 5, climax 1, initiative 10, vacuum 5. 17 carry `at`. No `side`. All 33 join a `/api/tape` ofd mark on (HH:MM, kind, p), so `side` is available for 33 of 33. |
| E15 | the extension's own draw rule (`Go charting/orderflow-desk/src/shell/overlay.js:294`, read only) | It skips an absorption or exhaustion that is **not** at a named level, and it colours every mark by `side` (`sideC`, :117). The Trade tab draws all 18, in neutral grey. By the extension's rule, 6 of today's 18 would not appear on GoCharting. |
| E16 | legacy engine (`engine.py` via `bar.ctx`) on the tab | ENGINE KA READ (the engine's read) printed SPENT, a SPRING LOADING setup, and plays such as "FADE a test of 22762" and "BREAK of 22700 … needs vol rank >0.9". The MAP levels CAP 22762.2 and FLR 22700 come from the same `ctx`. **A second engine on the screen**, beside rev 6's verdict. |
| E17 | FUT OI | 8.80M at 09:15 to 7.44M at 15:15: the Sep future's roll in expiry week. The pane's words "SHORT COVERING — shorts covered" read the roll as positioning (audit §7 says to blind it). |
| E18 | TypeScript baseline | `node_modules/.bin/tsc --noEmit -p .` exits 0 today. Every build step keeps it at 0. |

---

## A. Inventory: everything the tab produces

The source is `file:line`, plus the endpoint and field read. "Live today" says whether it is correct and live on 29 Sep, and how that was checked.

### A1. The price pane (chart layers)

| # | element | source | what it claims | live today? |
|---|---|---|---|---|
| C1 | Candles (Kite colours) | `ContractChart.tsx:236-260`, `indicators.ts:130`; `/api/data` `bars[].fut` | the future's OHLC | Yes. 5m closes match the ofd and ux bars at 10 sampled times. |
| C2 | OHLC legend, A/L buttons, grid, crosshair | `vendor/candl` | the chart engine's own | Yes |
| C3 | ±1σ core wash (pink) | `LevelsOverlay.ts:1871`; `bars[].u1/d1` | distance from VWAP | Drawn. It is context, not her setup. |
| C4 | 1σ to 2σ shoulder wash (green) | `:1869-1870`; `u2/u1`, `d1/d2` | same | Drawn |
| C5 | 2σ to 3σ outer wash (blue) | `:1867-1868`; `u3/u2`, `d2/d3` | same | Drawn. **This is exactly her zone pocket (d2 to d3, u2 to u3)**, but nothing names it as such. |
| C6 | d3 and u3 arming lines (the brown envelope) and the chips "d3 · ARMS THE BUY" / "u3 · ARMS THE SELL" | `:1873-1915` | "the only bands §5c reads" | **Wrong machine.** Her zone machine arms at d2 and u2 (E1). d3 arms nothing she trades. |
| C7 | CALL and PUT wall lines | `App.tsx:1636` → `data.ts:1061-1062`, `toTape` `:798`; `/api/data` `map.wall_up/wall_dn` + `basis` | the chain's walls | Absent after the close ("no call wall in the chain profile"). On a normal day they are misplaced by the spot error (E11). A different wall rule from the engine's. |
| C8 | PIN 22699.0 | `data.ts:1068`; `ctx.pin.k` via `toTape` | dealer magnet (legacy) | Drawn. Legacy engine; spot basis. |
| C9 | Floor pivots P, R1–R3, S1–S3 (S2 22579.4 in the screenshot) | `data.ts:1071`; `day.pivots` | prior-session pivots | Drawn. The same brass and the same proximity glow as the real levels. |
| C10 | FLR 22700 and CAP 22762.2 | `data.ts:1073-1074`; `ctx.floor/cap` | legacy engine floor and cap | Drawn (E16) |
| C11 | STK | `data.ts:1077` | ATM strike, via the spot basis | Deduped out today; misplaced by E11 |
| C12 | HI and LO | `data.ts:1078-1079` | session high and low | Drawn when not deduped. The candles already show it. |
| C13 | TRAP 22728.5 | `data.ts:1095`; legacy `TRAP-SPRUNG`/`TRAP-SETTING`/`SPRING-FAIL` events, at the bar close | legacy trap levels | Drawn. It sits by coincidence 1 pt from the engine's real trapped shelf (E6). |
| C14 | MAX PAIN | `App.tsx:1642`; `chain.maxPain` via `toTape` | chain | Live when the chain is live; spot basis |
| C15 | GEX FLIP | `App.tsx:1644`; `chain.flipPx` | chain | "no flip price" today |
| C16 | Right-axis chips and left labels for every level | `LevelsOverlay.ts:1800-1837, 1992-2040` | the level's price | Drawn for C7–C15 |
| C17 | Proximity emphasis: lines glow as price nears; the "target" turns solid green or red | `:1922-2019` | "price is here", in σ | Drawn. It turns a legacy line green or red, one step from reading as a call (the code's own comment). |
| C18 | §5c entry markers (a triangle on the band, a square pill "▲ BUY d3") | `:855-971`, `runDrawPlan` `:257-301`; `rotation_run(_sell)` | her setup fired here | **0 drawn today; wrong machine** (E2). `runDrawPlan` rejects d2 and u2, so zone entries could not draw even if fed. |
| C19 | STORY condition track | `:411-469`; `bars[].ctx.verdict` | legacy verdict runs | Off by default; 25 withheld today |
| C20 | STORY balloons | `:985-1060`; `/api/data` events | legacy events | Off; 38 withheld |
| C21–C25 | SMC: OB boxes, EQH and EQL pools, swing ticks, PDH/PDL/PDC, PREMIUM/DISCOUNT/EQ | `:539-789`; `day.structures` | structure.py | Off; 128 withheld. She said "i dont like smc". |
| C26 | Her footprint marks: P (trap disc), A (absorption shelf), E (exhaustion chevron), C (climax diamond) | `:1411-1568`, `markCounts` `:1175`; `/api/day/record` `events[]` | the extension's own marks, at their own time and price | 18 drawn, 10 at a level, all neutral grey. The extension paints them by side and hides light A and E (E15). |
| C27 | tm family (hollow a, e, c) | `:1343-1407`; `/api/tape` `marks.tm` | TapeMap's own marks | 9 drawn. A second reader of the same events. |
| C28 | ux run rings (the "$" circles) | `:1353-1357, 1397`; `/api/tape` `ux.marks.runs` | "3 prints, one press" | **215 drawn today** (E13). They bury the candles. |
| C29 | Stacked-imbalance brackets | `:1315-1332`; `bars[].stacks` | footprint cells | 8–9 drawn |
| C30 | Unfinished-auction ticks | `:1333-1340` | footprint cells | 1 drawn |
| C31 | HVN wash and LVN box | `:1270-1283`; `levels.nodes` (ofd) | volume nodes | 7 drawn |
| C32 | Session POC / VAH / VAL (ofd) | `:1285-1289` | value area | POC 22598.8, **84 pts from C33** (E12) |
| C33 | Session POC / VAH / VAL "ux" | `:1292-1297` | value area | POC 22682.5, which agrees with the engine's value |
| C34 | Prior-day VA / POC | `:1298-1303` | prior days | None: the roll guard (E12) |
| C35 | Naked POCs | `:1304-1313` | untouched prior POCs | None |

### A2. The hover callout (`Callout.tsx`)

| # | element | source | claims | live today? |
|---|---|---|---|---|
| H1 | Date and time, OHLC, volume, OI (the OI change in "k") | `:139-179`; the bar | the bar | Yes |
| H2 | §5c block: trigger sentence, "squeeze pehle" (the squeeze before), trap, "confirm — UNKNOWN" | `:185-230`; `rotation[i]` (the one-candle rule) | her setup on this bar | The one-candle §1 rule, a third population. `confirm` is always UNKNOWN by construction. |
| H3 | Engine narration: Hinglish gloss, then the engine's own words | `:232-277`; `narration.ts`, `hinglish.ts` | legacy events | Live (legacy engine) |
| H4 | "prints · is bar ke marks" (this bar's marks): ofd, tm and ux runs with their `why` | `:278-297` | marks at this bar | Live; 215 runs feed it |
| H5 | ux residual and partial warnings | `:298-306` | ladder quality | Live |

### A3. Sub-panes (`indicators.ts:276-312`)

| # | element | source | claims | live today? |
|---|---|---|---|---|
| P1 | "FUT · SHORT COVERING — shorts covered 2.49 L · 71.52 L open · −16.44 L today" | `:285-292`, `oiLabel` `:63-89`; `bars[].fut.oi` | who moved the future's OI | Reads the roll as positioning (E17) |
| P2 | "Δ prints [M] · CVD … · Δ ux [I]" histogram and lines | `:294-310`, `alignDelta` `:247-274`; `/api/tape` `bars[].delta` and `ux.bars[].delta` | order flow | Draws at 5m and 15m only. Two delta families on one pane; they agree on sign on 69% of bars (`ux.agree.delta_sign_agree`). |

### A4. The left panel (`SetupCheck.tsx`, mounted at `TradeTab.tsx:931-943`)

| # | element | source | claims | live today? |
|---|---|---|---|---|
| L1 | "SETUP CHECK · Sep 29 LIVE" and RESET | `:807-816` | — | — |
| L2 | State block "WAITING · BUY · d3", reference sentence, "Todna hai >" (must break above) and "Stop <" lines, re-fire lock | `:820-897`; `run_state[at]` | where her setup stands | **Wrong machine** (E2) |
| L3 | "Doosri taraf bhi armed hai…" (the other side is armed too) | `:836-841` | both sides armed; "score sirf usi ka hai" (only that side has a score) | Wording ranks the sides by a score |
| L4 | "Is bar ka read nahi mila" (no read for this bar) | `:842-847` | unreadable bar | Rare |
| L5 | TRIGGER header and note, with "68.4% (n=19)" | `:900-918` | a hit rate | **Violation** (E4) |
| L6 | TRIGGER rows: "d3 chhua" (d3 touched), "Window abhi khula hai" (window still open), "Close ne reference high toda" (a close broke the reference high) | `:287-321` | a candle-close checklist | Wrong machine; the candle-close framing she banned |
| L7 | AAJ KE SIGNAL (today's signals): §5c entries, SCORE NAHI (no score) badge, stop, re-fire lock | `:620-743`; `rotation_run(_sell)`, `run_state(_sell)` | today's entries | **"0" today** (E1, E2) |
| L8 | SAATH DE RAHA HAI (what supports the trade) header, "0 / 7" | `:745-749` | an unscored tally | — |
| L9 | "Reference ke neeche koi khapa raha hai" (someone absorbing under the reference) | `:343-350`, `footprint.lookUnder` `:133` | footprint under the §5c reference candle | Always "no live reference" (E2) |
| L10 | Gamma regime | `:366-378`; `bar.gamma` | legacy gamma | "CEILING", legacy |
| L11 | "Index pehle sikud raha tha" (the index was compressing first) | `:383-395`; `entry.trap` | compression | No entry, so unknown |
| L12 | "Doosri leg ne confirm kiya" (the other leg confirmed) | `:397-409`; `entry.confirm` | confirmation | UNKNOWN by construction |
| L13 | "OI ka jhukaav mere haq mein" (OI tilts my way), a manual tick | `:415-424`; `/api/oiflow` | the aggregate CALL/PUT tilt | Manual; aggregate, not at levels |
| L14 | "OI banne ki raftaar dheemi" (OI build slowing), a manual tick | `:425-437` | OI deceleration | Manual |
| L15 | "Doosri leg apne +2σ se ghoom rahi hai" (the other leg is turning off its +2σ), a manual tick | `:438-443` | pair rotation | "ye chart is payload mein nahi hai" (not in this payload) |
| L16 | MERA READ (my read): custom rules and "+ Rule jodo" (add a rule) | `:751-803`; `localStorage tape.check.rules` | her rules | 0 rules on this browser |
| L17 | Tallies "TRIGGER 0/3 · SAATH 0/7" and their explanation | `:928-949` | two tallies | — |

### A5. The strip, controls and disclosure lines (`TradeTab.tsx`)

| # | element | source | live today? |
|---|---|---|---|
| S1 | CONTRACT "NIFTY FUT" | `:702-709` | Yes |
| S2 | Session "Sep 29 LIVE" in amber, with a year-precision tooltip | `:710-715`, `indicators.dayPrecision` | The live day key never has a year, so it shows every live day |
| S3 | Bar "15:27" | `:716` | Yes |
| S4 | "Band bhaav" (closing price) 22714.3 | `:717` | Yes |
| S5 | Open interest 7.15M | `:718` | Yes (the roll, E17) |
| S6 | Volume | `:719` | Yes |
| S7 | Bars 125 / 125 | `:720` | Yes |
| S8 | Interval 1m / 3m / 5m / 15m | `:130-153, 729` | Yes |
| S9 | FOCUS | `:734-744` (App `:1576-1583`) | Yes |
| S10 | SMC | `:751-765` | Off |
| S11 | STORY | `:771-783` | Off |
| S12 | LEGS OFF / SPLIT / STACKED | `:789-803` | Off |
| S13 | Index switcher under FOCUS | `:807-823` | Yes |
| S14 | LIVE / REPLAY / STALE dot | `:830-839` | Yes |
| S15 | One disclosure line: stale · date precision · chain stale | `:853-866` | Shows "Session key mein saal nahi hai" (the session key has no year) every day |
| S16 | "Structure layer nahi mila" (structure layer not found) | `:875-880` | Off |
| S17 | "Setup ke markers nahi mile" (setup markers not found) | `:886-893` | — |
| S18 | Loading and no-tape states (Hinglish) | `:630-665` | Yes |

### A6. Below the chart (`TradeTab.tsx`)

| # | element | source | live today? |
|---|---|---|---|
| U1 | "OI 15:25 · CALL +3.94Cr · PUT +3.64Cr · DIFF −30.3L CALL-heavy 8% · PCR 0.92 · Δ ▼18.5L" | `:983`, `flow.FlowLine` `:70`; `/api/oiflow` | Live. Aggregate OI, not at levels. |
| U2 | Ribbon: the day's shape in legacy engine-event ticks | `:986`, `Ribbon.tsx` | Live (legacy) |
| U3 | Legend "σ wash ±1σ gulabi…" (pink) plus the d3 entries, the u3 SELL "ISKA KOI SCORE NAHI" (this has no score) text, and "68.4%" | `:988-1017` | **Violation** (E4) |
| U4 | Order-flow marks legend paragraph ("P = trap … sab neutral hain", all are neutral) | `:1022-1041` | Says the marks are neutral because side is missing; E14 shows side is available |
| U5 | Prints legend ("POC 22598.8 VAH … tm 9 of 9 … 9 stacks …") | `:1043-1063` | Live |
| U6 | Upstox legend (ux vs ofd agreement, runs 215 of 215, λ) | `:1065-1069`, `tape.uxLegend` `:89` | Live |
| U7 | "Chhupa hua" (hidden): STORY 38 events, 25 bands; STRUCTURE 128 | `:1077-1102` | Live |
| U8, U9 | ATM CE and PE leg charts (off by default) | `:1114-1123`, `LegChart.tsx` | Off. A premium chart, which she does not want. |
| U10 | ZONE READ panel: Kahan (where), Books, GEX, Flow, Gamma, Structure, Setup | `:1124-1130`, `ZoneRead.tsx:66` | Live. A legacy wall rule; "no put wall" after the close. |
| U11 | ENGINE KA READ (the engine's read) panel | `:219-349, 1131` | **The legacy engine's verdict and plays** (E16) |

### A7. Feeds and props

| # | element | source | live today? |
|---|---|---|---|
| F1 | `useFootprint`: `/api/day/record`, every 30 s | `footprint.ts:69` | Yes. Carries `at`. |
| F2 | `useTape`: `/api/tape`, every 30 s | `tape.ts:106` | Yes. Carries ofd `side`. |
| F3 | `useFlow`: `/api/oiflow`, every 15 s | `flow.tsx:32` | Yes. Feeds only U1, L13, L14 and U10 here. |
| F4 | The `events` prop, feeding narration and zones | `App.tsx:1900`, `narration.ts`, `zones.ts` | Legacy |
| F5 | Props `chain`, `strike`, `optPivots`, `optExpiry`, `structures*`, `rotation*`, `rotationRun*`, `runState*` | `App.tsx:1897-1917` | These feed the cut layers. `zoneState*` exists on `tape` (`data.ts:464-466`) and is **not passed**. |
| F6 | The `levels` prop (MAP levels) | `App.tsx:1636-1647` | Feeds C7–C15 |

---

## B. Trader verdict per element

**Counts: KEEP 11 · MOVE 6 · MERGE 4 · FIX 10 · CUT 63** (94 elements).

| # | verdict | why, in her terms |
|---|---|---|
| C1 | KEEP | The futures chart is the playground; candles in Kite colours, as she reads them. |
| C2 | KEEP | The engine's own furniture |
| C3 | CUT | ±1σ is not her setup, and a wash over the candles says nothing about zone, flow, OI or VPIN. |
| C4 | CUT | Same |
| C5 | FIX | Keep **only** d2 to d3 and u2 to u3, named as her zone. A faint azure pocket with a thin line on the d2 and u2 edges, where her machine arms. |
| C6 | CUT | It names the wrong bands. Her machine arms at d2 and u2, so the "ARMS THE BUY" chip on d3 is a false instruction. |
| C7 | CUT | The chain's walls, on the spot basis. The engine's walls (at K + basis, with their OI state) replace them: one wall rule. |
| C8 | CUT | Legacy dealer magnet, spot basis, not one of her four |
| C9 | MOVE | Behind "Pivots", grey hairlines, no glow. Reference only, as she said of reference lines. Her own S1–S4 lines live on GoCharting. |
| C10 | CUT | The legacy engine's floor and cap. A second engine. |
| C11 | CUT | ATM strike on the spot basis; nothing to read |
| C12 | CUT | The candles show the day's high and low. |
| C13 | CUT | Legacy trap levels at bar closes. The engine's trapped shelves (E6) replace them. |
| C14 | CUT | Not her method; spot basis |
| C15 | CUT | Not her method |
| C16 | FIX | Chips and labels only on the lines that remain. Short names ("22750 CE", "NEXT ↑ 22728"). |
| C17 | CUT | A glow that turns lines green or red reads as a call. Only the engine's levels get weight. |
| C18 | FIX | The same shape (a triangle on the band, a square pill), fed by her **zone** machine's entries at 3m (E1). `runDrawPlan` accepts BUY d2/d3 and SELL u2/u3 after 09:25. |
| C19–C20 | CUT | Legacy engine, never scored, off already |
| C21–C25 | CUT | SMC, which she rejected. Off already. The engine's NEXT FIGHT already brings in the contract's prior day when it matters. |
| C26 | FIX | Her marks "really work great". Paint them **as GoCharting does**: coloured by `side` (joined from `/api/tape` ofd, 33 of 33), A and E only at a named level (the extension's rule), heavy when at a level. The hover names the level and the side. |
| C27 | CUT | A second reader of the same events. The engine's fights and her marks cover it. |
| C28 | CUT | 215 rings a day bury the candles, and the engine's fights are built from the same book. |
| C29 | CUT | Footprint-cell detail. GoCharting has the footprint. |
| C30 | CUT | Same |
| C31 | MOVE | Behind "Value", ux family only |
| C32 | CUT | Two POCs 84 pts apart on one chart. Keep one family: ux, which is the same one the engine's day sentence uses. |
| C33 | MOVE | Behind "Value" (grey band plus a POC line), tagged [I] |
| C34 | MOVE | Behind "Value"; prints `prior_why` when empty |
| C35 | MOVE | Behind "Value" |
| H1 | KEEP | The bar's OHLC and volume. Drop the FUT OI line (the roll). |
| H2 | FIX | The zone entry's own trigger sentence, verbatim, only on its bar. No trap or confirm rows (always UNKNOWN). |
| H3 | CUT | Legacy engine narration |
| H4 | FIX | This bar's engine fights (text verbatim) and her P/A/E/C (kind · side · level). No tm or runs. |
| H5 | CUT | Goes with the runs |
| P1 | CUT | Her OI is option OI at levels. This pane reads the roll as short covering (E17). |
| P2 | MOVE | Behind "Flow pane", off by default. **One** family, ux, the book the engine's fights come from. Tagged [I]. |
| L1–L4 | CUT | The §5c d3 line machine, not her setup. The app's MACHINE strip (always on, even under FOCUS) already carries the zone machine's state; the chart carries its entries. |
| L5 | CUT | A hit rate on screen |
| L6 | CUT | A candle-close checklist. "I don't care about candle close." |
| L7 | CUT | It read 0 on a day her zone fired twice. The entries move to the chart as pills. The stop is not how she exits. |
| L8–L15 | CUT | An unscored tally built on the §5c reference candle, legacy gamma, always-UNKNOWN confirms, aggregate OI, and manual ticks. The four rows (ZONE, FLOW, OI, VPIN) answer the same questions from the one engine. |
| L16 | CUT | Unused (0 rules). Her rules are the four reads. The `localStorage` key is left in place, not deleted. |
| L17 | CUT | Tallies |
| S1 | KEEP | Which contract |
| S2 | CUT | A year disclosure every live day, for nothing |
| S3–S4 | MERGE | One stat: "15:27 · 22,714.3" |
| S5–S7 | CUT | Noise on the chart's own strip |
| S8 | KEEP | Her choice of candle; it persists |
| S9 | KEEP | More chart |
| S10–S12 | CUT | Their layers are cut. |
| S13 | KEEP | Needed under FOCUS |
| S14 | KEEP | LIVE, REPLAY or STALE must be visible. |
| S15 | FIX | Keep the stale sentence. Drop date precision. Chain age is the OI row's own "could not check: chain N min old". |
| S16 | CUT | Its layer is gone. |
| S17 | FIX | Becomes one absence: "zone entries: 3-minute machine, not shown on this 5m chart", or the backend's why. |
| S18 | KEEP | Translated to English, like the DESK |
| U1 | CUT | Aggregate OI. Her OI is read at levels (the OI row and the wall lines). |
| U2 | CUT | Legacy events |
| U3 | CUT | A hit rate plus a paragraph |
| U4 | MERGE | Into one glyph key line under the chart |
| U5–U6 | CUT | Engineering legends. "Value" states its own source and why. |
| U7 | MERGE | Into one "not on the chart" line (below) |
| U8–U9 | CUT | "No chart of the premium" |
| U10 | CUT | A legacy wall rule, GEX, gamma, SMC. The four rows replace it. |
| U11 | CUT | A second engine's verdict and plays next to rev 6's. One engine, one verdict. |
| F1 | KEEP | `at` for her marks |
| F2 | KEEP | `side` for her marks, Value, and the Flow pane |
| F3 | CUT | No consumer left. `useFlow` stays exported for GlassBoard. |
| F4 | CUT | Legacy |
| F5 | FIX | The mount passes `zoneState`, `zoneStateSell` and `zoneStateWhy` and drops the rest. |
| F6 | FIX | Only `kind === 'pivot'` is read, for the Pivots toggle. |

---

## C. The new face

A trader's eye asks three things: **Where are we?** **Is our setup on?** **What do we watch next?** In a trade it asks one more: **is this a pullback or has somebody given up?** Everything on the face answers one of those. Everything else is gone or behind a toggle.

### C1. The chart at a glance (default, no toggles)

| layer | draws | source | tag |
|---|---|---|---|
| Candles | as now | `/api/data` | [M] |
| **Her zone** | A faint azure pocket d2 to d3 and u2 to u3, with a thin line on the d2 and u2 edges. No labels. The MACHINE strip above prints the d2 and u2 numbers. | `bars[].fut.d2/d3/u2/u3` | [M] |
| **Zone entries** | "▲ BUY d2 09:39" / "▼ SELL u2 12:18": a triangle on the band and a square pill. Drawn **only at 3m**. At any other interval the absence line says why. | `zone_state(_sell)[i].entry` | [M] |
| **Fights** | ▲ buyers won (teal) and ▼ sellers won (red) at their own (t, px). A white dot means won by price. A hatched glyph means disputed. | `/api/fold/flat` `marks[kind=won]` | [M] or [I] (by price) |
| **Absorbed** | A short bar (▬) at (t, px), coloured by the side named | `marks[kind=absorbed]` | [M] |
| **Trapped, not yet released** | A thick translucent line from the trap time to now, labelled "trapped buyers 429". It disappears when the release mark lands. | `marks[kind=trapped]` minus `released` (E6) | [M] |
| **Her P/A/E/C** | The extension's shapes and colours. A and E only at a named level. Heavy (with a halo) at a level. | `/api/day/record` + `/api/tape` ofd side | [I] (the extension's read) |
| **Flat: NEXT FIGHT** | Two solid ink lines, "NEXT ↑ 22728" and "NEXT ↓ 22701", with right chips. When price is within w of a level, one "AT 22899" line instead. | `next_fight.above/below.px`, `at.px` | [M] |
| **Flat: the walls** | The newest named wall each side: a dotted line at K + basis with the chip "22750 CE" | the newest `marks[kind=wall]` per `ty` | [M] |
| **Flat: GAVE UP** | When present: a frozen pill "SELLERS GAVE UP AT 22907 · 11:42" | `gave_up` | [M] |
| **In a trade** | See C4 | `/api/fold?id=` | [M] |
| **Today's closed trades** | A hairline at the entry and exit clock with "in 22800 PE 09:18 · out 09:35" at the top edge | `/api/hold/trades` | [M] |

**Colours.**
- Chart glyphs use the extension's LIGHT pair: buyers teal `#0f7b6c`, sellers red `#c0392b`. They are the same glyphs she reads on GoCharting, and blueprint §7.4 puts the engine's fights there too.
- The left panel's chips copy the DESK's colours exactly (WITH/BUYERS blue, AGAINST/SELLERS red, QUIET and CAN'T CHECK grey), because the floating DESK window sits beside it and shows the same rows.
- Ink means hers (her entry, G, NEXT FIGHT). Grey means reference or absence. Amber means watch.

**Budget:**
- Flat: 4–6 horizontal lines (2 NEXT FIGHT, 2 walls, 0–2 shelves). Today it is about 20.
- Glyphs today: about 39 fights and absorptions plus 12 P/A/E/C. Today's chart has about 300.

### C2. Behind one toggle each (all off by default, the choice kept per browser)

- **Value**: the ux POC line, a VAL-to-VAH grey band, HVN washes, prior-day VA/POC and naked POCs. It prints `prior_why` when empty (the roll). Tagged [I].
- **Pivots**: P, R1–R3, S1–S3 as grey hairlines with small right chips. No glow and no colour.
- **Flow pane**: a Δ histogram plus a CVD line, **ux family only**, at 5m and 15m. At 1m and 3m it reads "not shown: the record is 5-minute". Tagged [I].

### C3. Gone

Everything marked CUT in §B. In one breath:
- **Chart:** the σ core and shoulder washes, the d3/u3 envelope and its chips, the legacy MAP levels and the proximity glow, SMC, STORY, tm, the 215 run rings, stacks, the ofd value area, and the FUT OI pane.
- **Screen:** the leg charts, ZONE READ, ENGINE KA READ, the OI strip, the ribbon, the four legend paragraphs, and the whole SETUP CHECK with its hit rate, candle-close checklist, tallies and manual ticks.

The language is English, as on the DESK. The engine's own sentences are shown verbatim.

### C4. Her trade on the chart

**When she has an open marked trade on this index** (the newest one, if more than one; the others are named in the panel):
- **Entry ▸** in ink at (entry_t, E), labelled "in 22800 PE 113.95 · 09:18".
- **G, her give-up:** a dashed ink line from `G.set_t` to now, labelled "give-up 22711 · set 09:32". **Its colour follows the engine's headline and nothing else:**
  - ink for HOLD;
  - amber for PAST GIVE-UP;
  - red with ■ at the fold for FOLD.

  This is the pullback-versus-invalidation picture: price poking G while it stays ink is a pullback, and amber means G has been accepted. Once the server sends G's history (§D.0) the line becomes the staircase, with older steps at 55%.
- **W, the wall behind her:** dotted at K + basis, with the chip "22700 CE 208.8L · building". `W.state` is published. The px is K + `units.basis`, the rule the engine publishes.
- **A, the wall ahead:** dotted at `A.px`, with the chip "22600 PE 180.6L · peak 09:34 · 21 pts".
  - **This is today's lesson on the chart.** Price sat on A for about 90 minutes, and the chip says whether its OI is still at its peak.
  - The word "building" needs `A.state` (§D.0). Until then the chip shows the numbers only, as the DESK does.
- **OI event live** (the writers behind her gave up): a small mark on the W line at its time, "22700 CE writers left 11:42 (−4.1%)", verbatim from `oi_event`.
- NEXT FIGHT and the flat walls are hidden while a trade is open. G, W and A are her levels.

**When flat:** C1's flat layers.

**After an exit:** the trade's entry and exit hairlines stay. The frozen view is not drawn; it lives in the DESK's RECORD.

### C5. The left panel (260 px, top to bottom)

1. **NOW.**
   - *In a trade:* "long 22800 PE · in 113.95 · 09:18", then the **headline** (HOLD / PAST GIVE-UP / FOLD / CAN'T CHECK), then the clause, then line 2, all verbatim from `/api/fold?id=`.
   - *Flat:* "FLAT", then "NEXT FIGHT 22728 above · 22701 below". Under each: its `what` and "confirms: …", verbatim. Then `gave_up` and the re-entry read (marked unproven), when present.
2. **THE FOUR ROWS:** ZONE, FLOW, OI, VPIN, each with its chip and sentence and its [M]/[I] tag, as on the DESK.
3. **LEVELS (in a trade):** give-up, W and A in numbers. They are the legend for the three chart lines.
4. **THE DAY (flat):** the engine's one sentence.
5. **The glyph key**, one line.
6. **"Not on the chart"**: one line, only the entries that apply. For example:
   - "engine: could not check — the engine has not started on this index";
   - "zone entries: 3-minute machine, not shown at 5m";
   - "live levels not shown while replaying";
   - "Value, Pivots, Flow pane: off".

The in-trade word is read through the DESK's own shared poller (`pro/api.ts` `useStore`, imported, never edited). The tab, the floating window and the DESK therefore show one word from one poll and cannot disagree. The flat read is fetched per index every 10 s, because the DESK's poller is fixed to NIFTY.

### C6. Replay, other indices, and anytime start

- **Replay.**
  - Candles, the zone pockets, zone entries, fights, shelves and her marks are cut at the cursor by their own time. A shelf is drawn if it was trapped before the cursor and released after it.
  - NEXT FIGHT, the walls and G/W/A are live-only. They are **not shown** while replaying, and the absence line says so.
- **BANKNIFTY and SENSEX:** the engine is not read there (E10). The NOW block and the rows read "could not check — the engine has not started on this index". The chart keeps candles, the zone, zone entries and her marks, if the extension is on that index.
- **Anytime start:** every source is a poll of a server cache, so a reload at any time redraws the same face. The first-poll state reads "checking…", never "none".

### C7. Sketches

The HTML mockup at `docs/trade-tab/mockup-2026-09-29.html` is LIGHT and built from today's real numbers:
- **Flat at the close:** NEXT FIGHT 22728/22701, the walls 22750 CE and 22650 PE, the live trapped shelf, the BUY d2 09:39 and SELL u2 12:18 pills, the fights, and 12 P/A/E/C.
- **In a trade:** her 22800 PE with E, G, W and A from the frozen 09:35 view, and the candles run on to 11:05, sitting on A.

```
┌ NIFTY FUT · 15:27 · 22,714.3 · ● LIVE ─────────── [1m 3m 5m 15m] [Value] [Pivots] [Flow pane] [FOCUS] ┐
├── 260 ───────────────────────────┬──────────────────────────────────────────────────── chart ─────────┤
│ FLAT · NIFTY                      │ ░░░░░░░░░░░░░░░ u2→u3 pocket ░░░░░░░░░░░░ ▼SELL u2 12:18           │
│ NEXT FIGHT 22728 above · 22701 below│ ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ [22750 CE]  │
│ above 22728 429 lots buyers trapped │ NEXT ↑ 22728 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ [22728]  │
│   confirms: lifts at 22728–22733 …  │           ▼  A   ▬▲      ═══ trapped buyers 429 ═══════════      │
│ below 22701 165 lots buyers held …  │ NEXT ↓ 22701 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ [22701]  │
│ ZONE  QUIET   between 22701–22728   │   ▼                          P                                   │
│ FLOW  QUIET   no fight in 10 buckets│ ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈ [22650 PE]  │
│ OI    QUIET   22750 CE off since … │   ▲ ▬   ▲                                                         │
│ VPIN  BUYERS  4 of 10, buyers' way  │ ░░░░░ d2→d3 pocket ░░░░ ▲BUY d2 09:39                              │
│ THE DAY sellers' day (20 to 19) …   │                                                                    │
│ key · not on the chart: …           │ ▲▼ won · ▬ absorbed · ═ trapped · P A E C yours · ━ next fight    │
└─────────────────────────────────────┴────────────────────────────────────────────────────────────────────┘
in a trade:  ▸ in 22800 PE 09:18 · - - give-up 22711 (ink HOLD / amber PAST GIVE-UP / red FOLD) - -
             ┈ W 22700 CE 208.8L building ┈  ·  ┈ A 22600 PE 180.6L = peak 09:34 · 21 pts ┈  ← price stuck here
```

---

## D. Build steps

**Rules for every step:**
- **After 15:30 or before 09:00 only.** Vite hot-reloads into her open tab, so an edit during the session changes her live screen.
- Never touch the Python server. No git writes: no stash, reset, checkout or clean; she commits.
- Each step leaves `node_modules/.bin/tsc --noEmit -p .` at exit 0, the baseline today.
- Each step is checked on 5173 → Trade: NIFTY at 3m and at 5m, BANKNIFTY, and one replay scrub. Nothing may draw past the cursor.
- **Untouched throughout:**
  - `band_rotation.py` and the zone machine's rules;
  - `data/`;
  - signed docs;
  - `src/pro/*` (imported, never edited);
  - every other tab;
  - `App.tsx` outside the Trade mount;
  - `useFlow` and `crl` (GlassBoard imports them);
  - `useTape` (VpinTab imports it);
  - the exports of `hinglish.ts` (App imports them);
  - `vendor/candl`.

### D.0 Server fields: named here, not built in phase 2

The face works without any of these; each is a smaller or truer version of something the plan does in the UI.

| field | why | needed for |
|---|---|---|
| **`view.A.state`** (same vocabulary as `W.state`) | To say "building" on the wall ahead: today's lesson in one word | Recommended |
| **`view.G_steps: [{t, px, why}]`**, all steps, untrimmed, including refused loosenings | The G staircase. The 12-event trim and the px-less `seed`/`reset` events leave no history (E9). | Recommended |
| `view.W.px` | Symmetry with `A.px`. The UI otherwise places W at K + `units.basis`, the engine's published rule. | Optional |
| `side` on `/api/day/record` events | Drops the client join (33 of 33 match today) and could drop one poll of a 514 KB, 1.8 s cold read | Optional |
| `released_t` on `trapped` marks | Drops the (px, side) pairing (27 of 27 match today) | Optional |
| `flat.walls[{k, ty, px, oi, peak, state}]` | A state word on the flat wall chips; today the state is only in the OI row's sentence | Optional |
| Live `rows.zone.machine` | The slot exists (`fold.py:1133, 1265`) but `fold_live` never passes `inputs["zone"]`, so the DESK's ZONE row lacks the machine sentence too | Optional, and it would also fix the DESK |
| The engine on BANKNIFTY and SENSEX all day (`fold_live.ALWAYS`) | So the face is not blind off NIFTY | A server-load decision for the supervisor |

### D.1 Below the chart

- **Change:** remove LegChart ×2, ZoneRead, EngineReadPanel, Ribbon, FlowLine and legend lines U3–U6 from `TradeTab.tsx`. Keep U7 for now.
- **Check:** the page ends just under the chart.
- **Untouched:** the overlay and the left panel.

### D.2 The strip and disclosure lines

- **Change:**
  - remove S2, S5–S7, the SMC/STORY/LEGS buttons and their state, and S16;
  - S15 keeps only the stale sentence;
  - merge S3 and S4;
  - English text;
  - ContractChart gets `smc={false} story={false}` until D.3 removes the props.
- **Check:** the strip reads contract · time · last · interval · FOCUS · live dot.
- **Untouched:** the index switcher and FOCUS behaviour.

### D.3 Overlay cuts and the zone pocket

- **Change:**
  - in `LevelsOverlay.ts`, delete `drawZones`, `drawStructures`, `drawBalloons`, the proximity block, the σ core and shoulder rings, the d3/u3 arming lines and chips, and `drawPrints`' tm, runs, stacks, unfinished ticks and ofd value area;
  - keep the d2→d3 and u2→u3 rings; add the d2 and u2 edge strokes;
  - the MAP level pass draws nothing for now;
  - narrow ContractChart's props.
- **Check:** candles, two pockets and her marks, nothing else.
- **Untouched:** `drawMarks` and `drawRotation`.

### D.4 Her P/A/E/C, painted as GoCharting paints them

- **Change:**
  - `drawMarks` takes `side` from `/api/tape` `marks.ofd`, joined on (HH:MM, kind, p);
  - apply the extension's rule: absorption and exhaustion only when `at`;
  - colours are the extension's LIGHT BUY and SELL pair;
  - `markCounts` counts the same set, and the hover row names the kind, side and level.
- **Check:** today at 3m, 12 marks (trap 4, climax 1, A 4, E 3), coloured. A mark whose side is missing stays neutral, never guessed.

### D.5 Sub-panes

- **Change:**
  - `buildIndicators` drops the FUT OI pane;
  - the Δ/CVD pane is ux-only and draws only when the "Flow pane" toggle is on (`localStorage` key `trade.flowpane`);
  - dead code goes: `oiLabel`, `legRender`, `LEG_BAND_LINES`, `PIV_LINE`.
- **Check:** by default there is no sub-pane. With the toggle on at 5m, one pane.

### D.6 The engine's flat read on the chart

- **Change:**
  - a new `trade/engine.ts`, about 60 lines:
    - `useFlat(index)` polls `/api/fold/flat?idx=` every 10 s and keeps the last read plus `why`;
    - it re-exports `useStore` from `../pro/api` for trades and in-trade views;
  - the overlay adds four passes:
    - `drawFights` (won and absorbed, cut at the cursor);
    - `drawShelves` (trapped minus released);
    - `drawWalls` (the newest wall mark per `ty`);
    - `drawNextFight` (above, below and at, plus the `gave_up` pill; live only);
  - each pass skips drawing on a `why`.
- **Check:** NIFTY after the close matches the mockup's flat chart. BANKNIFTY shows no engine layers, and the absence line quotes the engine's why.

### D.7 The left panel and her zone entries

- **Change:**
  - replace `SetupCheck` with `trade/Side.tsx`, about 150 lines: NOW, the four rows, THE DAY, the key, and the "not on the chart" line;
  - the App.tsx Trade mount passes `zoneState`, `zoneStateSell` and `zoneStateWhy` and drops the F5 props;
  - the entries for C18 come from `zoneState*[i].entry`;
  - `runDrawPlan` accepts BUY d2/d3 and SELL u2/u3 after 09:25 and draws only at `publishedInterval === 3`.
- **Check:**
  - at 3m: ▲ BUY d2 09:39 and ▼ SELL u2 12:18 on 29 Sep;
  - at 5m: none, with the absence line;
  - no hit rate anywhere (`grep -n "68\.4\|n=19" src/trade` returns nothing).

### D.8 Her trade

- **Change:**
  - the overlay adds `drawTrade`: E ▸; G coloured by the headline; W at K + `units.basis`; A at `A.px`; the `oi_event` mark on W;
  - flat layers are hidden while a trade on this index is open;
  - closed trades today draw entry and exit hairlines;
  - the NOW block renders the in-trade face from the same `useStore` read the floating window uses.
- **Check:** **never POST a test trade into her record** (`/api/hold/trades` persists to `data/day_state/`).
  - Add a GET-only review read, `?tradeview=<id>` on the Trade tab, that draws a closed trade's frozen view. Today's `NIFTY-22800PE-long-091807` must show E 22721.5, G 22711, W 22700 CE and A 22600 PE at 22604.
  - On the next live trade she marks, the word on the tab, the floating window and the DESK must be identical.

### D.9 Toggles Value and Pivots

- **Change:**
  - Value draws the ux session VA/POC, ux nodes, prior VA and naked POCs, and prints `prior_why` when empty;
  - Pivots draws the `kind === 'pivot'` levels as grey hairlines;
  - both default off, remembered in `localStorage`.
- **Check:** Value on NIFTY shows POC 22682.5 and "earlier days' contract was not recorded".

### D.10 The hover

- **Change:** Callout keeps OHLC and volume. It shows the zone entry's trigger sentence on its bar, and this bar's fights and marks (verbatim, with tags). Narration, the rotation block, tm, runs and the ux residual go.
- **Check:** hovering on 09:39 at 3m shows the trigger sentence.

### D.11 Delete dead code

- **Change:**
  - delete `SetupCheck.tsx`, `LegChart.tsx`, `Ribbon.tsx`, `zones.ts` and `narration.ts`; `hinglish.ts` gets its tone type inline, one line, exports unchanged;
  - `ZoneRead.tsx` shrinks to `export const crl`;
  - `flow.tsx` loses `FlowLine`;
  - `tape.ts` loses `uxLegend`;
  - `footprint.ts` loses `lookUnder`.
- **Check:**
  - tsc exits 0;
  - GlassBoard, VpinTab and the Events rendering in App still work;
  - rough size: `src/trade` goes from about 7,000 lines to about 2,500 [I].

### D.12 End-to-end checks

- Replay: scrub to 11:00. Nothing from after 11:00 is drawn, and live levels read "not shown while replaying".
- Anytime start: reload at any time.
- **30 Sep, the first Oct session:**
  - the contract is Oct;
  - Value's `prior_why` names the roll;
  - fights start from the engine's first mark.
- A stale backend reads STALE plus the engine's "could not check".

### D.13 When the D.0 fields land

- the G staircase with refused loosenings;
- the "building" or "off its peak" word on the A chip;
- the state word on the flat wall chips;
- drop the client joins.

---

## Findings outside this tab's scope (flag only; nothing changed)

1. **The app's MACHINE strip reads the zone machine at whatever interval the chart is on** (`App.tsx:1774` `tape.zoneState`; the Glass board does the same at `:1889`). At 5m it shows a different machine from her 3-minute setup (E3).
2. **`data.ts` `toTape` places every chain level with future − index spot** (E11): MAX PAIN, GEX FLIP, walls, PIN and STK on other tabs too. The engine's rule is K + (future − forward).
3. **The DESK's ZONE row never carries the zone machine sentence live** (D.0, `rows.zone.machine`).
4. **The engine reads NIFTY only** (E10). Every face is blind on BANKNIFTY and SENSEX unless a trade is marked there.

## Her call

None of this needs her. It is all a trader's call, made above with reasons. One FYI to tell her:
- zone entries draw only on the 3-minute chart, because that is where her machine lives;
- on 5m the chart says so rather than showing a 5-minute machine that is not her setup.

---

## Build record, 2026-09-29 after the close

Built D.1 → D.12 and D.14 on the supervisor's approval, with the supervisor's changes:
- Pivots are on by default, as grey hairlines with small right chips. They are read from the payload's `day.pivots`, because the MAP levels had deduped S1 22697.2 under PIN 22699.
- The Flow pane is on by default (ux family, [I], 5m and 15m only).
- Her zone is always the 3-minute machine, on every interval. `trade/zone3.ts` fetches `/api/data?interval=3` when the chart is not 3m. Entries are labelled "BUY d2 09:39 · 3m" on the bar that contains their time.
- The MACHINE strip, the tab title and the Glass board read the same 3-minute source (`App.tsx`: the hook call, the title effect, the strip props, the Glass props and the Trade mount; nothing else).
- The key names the two absorption sources apart: "▬ held (book, engine)" and "A absorption (footprint, yours)".

**Server (D.14), output fields only, no rule changed:**
- `fold.py` `_snap` now carries `W.px`, `A.state` (W's vocabulary) and `G_steps` (about 7 lines).
- There is a new test in `test_fold.py`.
- `pytest test_fold.py test_fold_live.py test_fold_log.py`: 33 passed.
- The running server picks the fields up only after her restart. The face works with and without them.

**Size:** `src/trade` went from 6,524 lines to 2,394.
- Deleted: `SetupCheck.tsx`, `LegChart.tsx`, `Ribbon.tsx`, `zones.ts`, `narration.ts`. All were tracked, so git can restore them.
- New: `Side.tsx`, `engine.ts`, `zone3.ts`.

**Left as found (outside the allowed diff):** `App.tsx` `tradeLevels` (lines 1636–1647) now has no reader. Screenshots are in `shots/`.
