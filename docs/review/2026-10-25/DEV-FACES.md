# DEV-FACES: a blind review of the three faces (25 Oct 2026, market closed, read-only)

Scope:
- `tapemap/ui-v2/src` and `ui-v2/public/validate2`;
- the extension `orderflow-desk` (`src/`, `build.mjs`, `test/`, `dist-v2`);
- the face → server wire, matched against `server.py`.

Paths:
- `main.js`, `panel.js`, `boot.js` and `sw.js` are `orderflow-desk/src/shell/`;
- `v2.js`, `adapter.js` and `session.js` are `orderflow-desk/src/engine/`;
- `app.js` and `engine.js` are `ui-v2/public/validate2/`;
- `.tsx` and `.ts` files are under `ui-v2/src/`.

Not read: `docs/review/` (earlier), `docs/live/NOTEPAD.md`, `~/.claude`.

## 1. Verdict

1. **When the server's one voice answers, all three faces show it word for word.** That path is sound.
2. **It is not one brain.** The extension runs its own trading reads: walls, marks, flow, the FADE KILL and the FOLD-board rule. Validate runs a complete second engine in browser JS, and VALIDATE rev 3 exists only there.
3. **The P0s are all failure paths.**
   - When the voice is refused, the three faces show three different stops.
   - When the frame goes stale, the panel drops to a flat face in the middle of a trade.
   - When the server stops answering, the Float keeps showing its last HOLD as if it were live.

## 2. Scorecard

| Area | /10 | Why |
|---|---|---|
| One brain | 3 | Both the extension and Validate compute trading logic. Three LOCKED reads (§1i, §1l, §1p/§1q) are computed in the browser. |
| Consistency across faces | 4 | The voice matches on all three faces. The stop, the word, the spot basis, the sound and which trade is shown can each differ. |
| Dead weight | 4 | 15 tabs are mounted. About 1,900 lines of UI are unreachable. `App.tsx` is 2,032 lines with 8 tabs written inline. |
| Stale / missing / error | 3 | The panel's "?" block keeps the three absences apart. The in-trade faces collapse or lie when stale. |
| Fast market | 5 | Polling is bounded but duplicated. Some pollers have no timeout and no in-flight guard. The frame POST is 140 KB/s. |
| Glanceability | 6 | The coloured word sits on line 2 of every face. Voice lines l4 and l5 break the ≤6-word rule. The panel shows about 170 items in a trade. |
| Build / release / tests | 4 | The extension's suites are real. ui-v2 has no tests. The live UI is the HMR dev server. Validate loads from a CDN. |

## 3. Findings

| ID | Sev | Finding | Evidence | Action | Size |
|---|---|---|---|---|---|
| F01 | P0 | In a trade, a frame older than 15 s turns the panel into the FLAT face. The voice block and the chart's STOP / ENTRY / PULLBACK lines vanish, and the MARK buttons return priced off the last frame's chain. | `main.js:404` (`F=null`); `main.js:335` (`inTrade` needs `F.fold`); `panel.js:372-381`; `panel.js:418` (chain kept); `panel.js:387-394` | FIX | S |
| F02 | P0 | The Float shows the last voice (word, stop, ₹) indefinitely once the server stops answering. A failed poll keeps the old read and nulls the feed band, and the Float never renders `engineWhy` or the read's age. | `pro/api.ts:142,145,155,190`; `pro/Float.tsx:50` (`vc` from `st.fold`); no `engineWhy` anywhere in `Float.tsx` | FIX | S |
| F03 | P0 | When the voice is not ok (e.g. before the mark seeds, or when fold refuses), each face shows a different stop. Panel: KILL = `validate.level.inval`, else the engine's G. Validate: engine.js's own G. Float detail: `inval`. | `voice.py:125-127`; `main.js:342`; `app.js:138,319` + `engine.js:688`; `pro/Desk.tsx:134` | FIX | S |
| F04 | P1 | The GoCharting panel cannot see SENSEX or BANKNIFTY trades, nor a second NIFTY trade. The frame carries `fold` only for the first open trade on the frame's index, and that index is always NIFTY. While she holds a SENSEX leg the panel reads FLAT and offers NIFTY MARK buttons. | `fold_live.py:653-655`; `server.py:4684`; `main.js:455` (idx from the session key) | FIX | S |
| F05 | P1 | The main 5173 poll has no timeout and no in-flight guard. A wedged server, as opposed to a dead one, freezes every number with no NOT LIVE banner, because `error` is set only when `fetch` rejects, and the requests stack up. | `data.ts:1263-1271`; `data.ts:1349-1350` | FIX | S |
| F06 | P1 | `boot.js` maps ANY missing reply to "extension context gone": a service worker killed mid-fetch, a closed port, or a slow server. The panel then says "Extension reload hua · F5", which is the wrong remedy for a server problem. | `boot.js:8-9`; `panel.js:423-424` | FIX | S |
| F07 | P1 | The Float never plays the voice ladder (the TIGHTEN tick, the WARN pair, EXIT with its 10 s re-ring). It chimes only on the engine's `sound_id`. The ladder lives in `hold/store.ts` and is wired only to the unmounted `HoldWindow`. | `pro/api.ts:123-133,154`; `hold/store.ts:66-68,106-117` | FIX | S |
| F08 | P1 | One state has four names. The voice says WARN, the panel's FOLD board says WATCH, the Float says PAST GIVE-UP, and Validate says "zone gaya". Float detail also paints PAST GIVE-UP as a red "kya badla", although the v2.9 review fix set HOLD v2's GAVE UP to WARN, never EXIT. | `panel.js:362`; `pro/Float.tsx:13-16`; `engine.js:14`; `pro/Desk.tsx:52`; ext `V2-BUILD-REPORT.md:2076` | FIX | S |
| F09 | P1 | An unknown engine headline renders as **HOLD** on the Float, as `?` on the panel and verbatim on the DESK. On the Float a missing value becomes the safe-looking word. | `pro/Float.tsx:28` (`?? 'HOLD'`); `panel.js:362`; `pro/Desk.tsx:26` | FIX | S |
| F10 | P1 | One trade is priced in spot off three bases: the voice's 3-min median, the frame's `read.basis` (rounded to tens on the panel and chart), and Validate's instantaneous fut−spot. On one screen the block says stop **22,965s** while the chart's STOP label says **≈22,970s**. | `voice.py:157`; `panel.js:242`; `v2.js:273` (`fs2`); `app.js:91-92,132-139`; shot `orderflow-desk/docs/v2-shots/v210/2026-10-21_1121_after.png` | FIX | M |
| F11 | P1 | Float detail prints `T1 … pts` and `inval` from `validate_live` next to the voice's PULLBACK and stop, even though v2.10 retired T1-as-target on the chart. | `pro/Desk.tsx:133-134`; ext `V2-BUILD-REPORT.md:2153` | FIX | S |
| F12 | P1 | When `/api/fold` refuses, Validate puts engine.js's "prototype" word (HOLD / FOLD / GAVE UP) in the headline slot. Only small text says "prototype". | `app.js:482-490,308` | FIX | S |
| F13 | P1 | Validate decides "in a trade" from the browser engine, not from the record. If engine.js has no chain row for her strike, the open trade renders as "no trade" or a recap, and the server's voice is never shown. | `app.js:51-52`; `engine.js:653-658,412` | FIX | S |
| F14 | P1 | VALIDATE rev 3 / 3.1 (§1p / §1q) exists only in browser JS, with a mutable `R31.ON` flag, and is tested through a node harness. The server still computes rev 2 for `/api/hold/check`, whose only caller is the unmounted `HoldTab`. | `engine.js:17-24`; `test/validate3_harness.cjs`; `server.py:66,3759`; `hold/HoldTab.tsx:99` | LOCKED (+CUT the rev-2 route) | M |
| F15 | P1 | The FADE KILL (§1i) is computed in the page from 5-min GoCharting bands. The page prefers the 5-min chart, while 3-min is canonical. It is shown as the plan's KILL. | `main.js:166,220-234`; `panel.js:337-340` | LOCKED | M |
| F16 | P1 | READ-2 JAGAH (§1l) takes the "last big push" from the page's own computation (`v2.pushes`), so a locked server read depends on extension logic. | `main.js:469-472` | LOCKED | M |
| F17 | P2 | The extension re-derives reads the server also owns: wall / deewar ranks, mark tiers and TIKA / TOOTA, flow state, VWAP / σ, crosses, fuel, khilaaf, the FOLD board's n/4 with its own VPIN gate, and a forward-record tally in localStorage. Its header says "it decides nothing". | `main.js:4,189-195,240-259`; `panel.js:355-360` | STOP-BUILDING | L |
| F18 | P2 | Between 09:45 and 10:15 the panel shows two VWAP-cross counts: the browser's day card and the server's meter. | `panel.js:262` vs `panel.js:164` | FIX | S |
| F19 | P2 | The frame is POSTed every 1 s whether or not the last one came back, and the service worker's `fetch` has no timeout. Each post is the full-day ladders, about 140 KB. A wedge queues posts that then replay as a burst. | `main.js:453-460`; `sw.js:4-7` | FIX | S |
| F20 | P2 | Validate fires about 5 requests a second. `pollFold`, `pollTrades` and `pollFlat` have no in-flight guard, so an out-of-order reply can overwrite a newer voice. | `app.js:554-596,617` | FIX | S |
| F21 | P2 | The same trade is polled three times: by the Float, by the Float's own `pro.html` iframe (a second realm), and by Validate. The 5173 main poll sends 10 requests per 5 s for all three indices with no `document.hidden` gate, which Board, Flow and War do have. | `pro/api.ts:198`; `pro/Float.tsx:144`; `app.js:617`; `data.ts:1349` | FIX | M |
| F22 | P2 | The extension re-renders up to 4×/s while ticks flow, because every ingest sets `dirty`. Each render stringifies the 120-day record and flat-maps every loaded day's bars. | `main.js:156,170,435,252,430` | FIX | S |
| F23 | P2 | The GoCharting origin's localStorage grows: full-ladder tick bars every 30 s, the 120-day record, and per-trade `ofd.voice.*` / `ofd.fold.*` keys that are never pruned. Quota errors are swallowed. | `session.js:86-92`; `main.js:122-128,240` | FIX | S |
| F24 | P1 | Validate loads Preact, htm and lucide from unpkg.com at runtime, so with no CDN there is no Validate face. Its boot text still says "the recorded 2026-10-06 session". | `validate2/index.html:29-32,26` | FIX | S |
| F25 | P2 | Her live UI is the Vite HMR dev server bound to 0.0.0.0 with `/api` proxied. Any LAN host can POST to `/api/hold/trades` or `/api/token`, and any file save during market hours hot-swaps her screen. | `start-v2.bat:116`; `ui-v2/package.json` (`dev`); `vite.config.ts:17-22` | FIX | S |
| F26 | P2 | `vite build` does not emit `pro.html` (single-page input), so a built app's Float iframe would 404. `ui-v2/dist` is from 19 Oct and is not served. | `vite.config.ts`; `ui-v2/dist/` (no `pro.html`) | FIX | S |
| F27 | P2 | Dead UI: `hold/HoldTab.tsx` (635 lines), `hold/MarketNow.tsx` (104), the `HoldWindow` component (kept only for its types) and `BoardRev3.tsx` (892, of which only `useBoardGlance` is used). The ui-v2 voice work for v2.9 landed in the unmounted `HoldWindow`. | `App.tsx:12,1692`; ext `V2-BUILD-REPORT.md:2125-2127` | CUT | M |
| F28 | P2 | `App.tsx` is 2,032 lines. Eight tabs are written inline: Tape (466), Chain (656), Events (780), Map (878), Heat (964), OI Flow (1119, her keeper) and others. Also inline: GlanceBar (377), AnswerBand (1400), MachineStrip (1573) and the replay transport. | `App.tsx:1694` (15 tabs) | FIX | M |
| F29 | P2 | 5173 has two meanings of "in a trade". The MachineStrip and the tab title say "TRADE MEIN" for the zone machine's run, while the Float means her marked trade, and the Float rewrites the same title every 2 s. | `App.tsx:1774,1875`; `pro/Float.tsx:55-59` | FIX | S |
| F30 | P2 | The legacy AnswerBand verdict still renders on the Tape, Flow, Chain, OI Flow, War and other tabs, next to the Float's voice. | `App.tsx:1866-1868` | CUT | S |
| F31 | P3 | In a trade the panel shows about 170 words and numbers. Voice lines l4 and l5 are 12 and 16 tokens, so they break the ≤6-word cell rule and wrap to 9 visual lines at 360 px. | shot `v210/2026-10-21_1121_after.png` | FIX | S |
| F32 | P3 | The version is kept by hand in 3 places. The manifest description still says "v2.8 (23 Oct)". `package.json` says 0.2.0 and the README says "v0.3.0, load dist". `npm run build` writes the retired `dist/`. | `manifest.src.json`; `recorder.js:39`; `v2.js:12`; `build.mjs:13` | FIX | S |
| F33 | P3 | ui-v2 has no test runner, and `app.js` and the Float are untested. The extension suites never test: a trade with a stale frame, a SENSEX trade under a NIFTY chart, or the boot / service-worker relay. | `ui-v2/package.json`; `test/shell.mjs:244-257` (flat stale only) | FIX | M |
| F34 | P3 | The relay uses `postMessage` with a `*` target. Any GoCharting page script can post `__ofdHold`, which reaches the mark / exit door, and can read every frame. | `boot.js:2-9`; `main.js:55-58` | FIX | S |
| F35 | P3 | The root's `minHeight:100vh` never constrains its `overflowY:auto` child, so the page scrolls instead of the pane. The Validate iframe is sized `calc(100vh-190px)` and overflows whenever a banner shows. | `App.tsx:1798,1981,2021` | FIX | S |
| F36 | P3 | `panel.js` defines `fs2` and never uses it. `ui-v2/AGENTS.md` is Figma Make boilerplate ("dev server on 8443"), and the package is named `figma-make-app`. | `panel.js:114`; `ui-v2/AGENTS.md` | CUT | S |

## 4. Answers, with the numbers behind them

**Q1. Where the browser re-derives logic.**
- **Extension:**
  - walls and ranks, mark tiers and status, flow state, VWAP / σ bands (posted to the server as `bands`);
  - the FADE KILL, the last push (feeds READ-2), the FOLD board's n/4 and its VPIN gate;
  - crosses, fuel, khilaaf, the 09:45 card, the record tally;
  - ≈spot rounding.
- **Validate (`engine.js`):** the GO / WAIT / NO word (rev 3 / 3.1), fronts, W-BLEED, the ZONE / FLOW / OI / VPIN chips, give-up G, the prototype word, the KYA BADLA ledger, basis, the IB day type, PIN, cross-index.
- **ui-v2:** the Float's word parsed from the headline prefix (`?? HOLD`) and its rank sort; Desk's `engineDiff` red / amber / blue tiers; `machine.ts` picks the machine side.
- **The server's own view of it:** it reads the extension's walls, events, push and decoder events as inputs.

**Q2. Where the three faces can disagree.**

| What | Panel | Float | Validate |
|---|---|---|---|
| Word (voice ok) | voice | voice | voice |
| Word (voice not ok) | FOLD board, its own n/4 | engine prefix, unknown → HOLD | engine.js prototype |
| Stop (voice not ok) | `validate.level.inval` → engine G | `inval` | engine.js G |
| Spot basis | `read.basis` | voice `stop_s` | engine.js fut−spot |
| SENSEX trade | not shown (F04) | shown | shown |
| Sound | voice ladder | engine FOLD chime only | none |

**Q3. What is mounted, and what is dead.**
- **Landing tab:** Read (`App.tsx:1673`).
- **Mounted (15 tabs):** Read, Board, Glass, Heat, Trade, Tape, Flow, VPIN, Chain, OI Flow, War, Events, Validate (an iframe of `/validate2/`), Map, Signals.
- **On every tab:** the Float, plus its `/pro.html?float=` iframe.
- **Dead:** listed in F27.
- **Duplicates:** the voice block is written 4 times (`panel.js:372`, `Float.tsx:144`, `app.js:298`, the dead `HoldWindow`), and the sound ladder twice (`main.js:130`, `hold/store.ts:106`).
- **Wire:** every endpoint the faces call exists in `server.py`; none is orphaned. `/api/hold?id=`, `/api/hold/check` and `/api/hold/expr` are called only by the dead `hold/*`.

**Q4. Stale, missing and error states.**

| Face | Server down | Value stale | Fetch failed |
|---|---|---|---|
| Panel | GC / TapeMap dots go red, "? could not check", and the trade face is lost (F01) | 0–15 s of stale frame drawn normally; amber dot from 5 s | a refusal's `why` is kept; every no-reply is mis-blamed on an extension reload (F06) |
| Float | last voice shown as live (F02) | no age on the voice block | same as stale |
| 5173 tabs | NOT LIVE banner only when `fetch` rejects; a wedged server gets none (F05) | CHAIN STALE banner exists (`App.tsx:1852`) | — |
| Validate | FEED DEAD retry at boot; data ages turn the word into CAN'T CHECK after 30 s (`app.js:59`) | as left | `/api/fold` refusal → prototype word (F12) |

**Q5. Fan-out and lifetime.**
- **Load in a trade:**
  - extension: POST every 1 s at about 140 KB;
  - 5173 main poll: 10 requests per 5 s;
  - zone3 and read polls: one request every 5 s each;
  - Float: 5 requests per 10 s, doubled when its iframe is open;
  - Validate tab: about 5 requests a second.
- **Memory over 6 hours:**
  - ui-v2 stores are replaced or capped (Desk highlights 12; Validate's memo is pruned at `engine.js:62`);
  - the extension's adapter `ohlc` Map is never pruned (`adapter.js:29,50`);
  - `diffs` are capped at 50k (`session.js:43`) and `fired` at 300 (`main.js:65`).
- **Service-worker lifetime:** posts every 1 s keep the service worker awake.
- **Relay orphaning:** an extension reload orphans the relay while the MAIN-world `main.js` keeps running. The banner for that exists (`panel.js:424`), but it is also raised for failures that are not reloads (F06).

**Q6. Glanceability in a trade** (screenshot plus code; ±10%).
- **Panel:** about 170 items, about 45 of them numbers. The voice block alone is 34 items.
- **Float, detail shut:** about 38 items. It is the cleanest of the three.
- **Validate:** the voice sits in the right-hand Inspector, after the Outliner and a 9-strike Ladder, with the Console below. That is 150+ items, and the answer is not first.
- **The one-second read:** yes on all three while the voice is ok (bold, coloured, on line 2). No once it falls back (F03, F12).

**Q7. Build, release and tests.**
- **Extension:**
  - the release path: `node build.mjs --out dist-v2` (or `npm run verify`), then Reload in `chrome://extensions`, then F5 the tab;
  - rollback is a hand copy from `.baseline/`;
  - both `dist/` and `dist-v2/` are committed;
  - suites (from `docs/V2-BUILD-REPORT.md`; not re-run here, the review is read-only): engine 116 checks, fit 46, shell 139 (boots the built bundle, a real check), overlay 39, panel 99, decoder 21.
- **ui-v2:** a file save goes straight through HMR. There are no tests; the gates are `tsc` and `vite build`.
- **Validate:** the engine is checked through `test_validate3.py` (14 tests); `app.js` has none.

## 5. Top 10 actions, ranked

1. **F01 + F02 + F03 — a stale or refused voice must never change what she sees into something else.**
   - Keep the last block on screen, labelled `STALE hh:mm:ss` or `could not check — why`.
   - Keep the chart's STOP line.
   - Print `stop: could not check`, never a fallback stop.
   - (S–M)
2. **F04 — the frame carries her open trade on any index.** A SENSEX leg must show on the NIFTY panel. (S)
3. **F05 + F19 + F20 — every poller gets a timeout and an in-flight guard.**
   - Reuse `hold/store.ts` `j()` (8 s abort) in `data.ts` and Validate.
   - The extension skips a post while one is still in flight. (S)
4. **F06 — tell "context gone" apart from "no reply".** Check `chrome.runtime.id` in `boot.js` before blaming a reload. (S)
5. **F07 + F08 + F09 — one vocabulary and one sound path.**
   - The voice's state word everywhere.
   - Float rings the ladder from `api.ts`.
   - An unknown headline is `?`, never HOLD. (S)
6. **F10 — one live basis from the server** (A60). The faces print the server's spot and stop computing ≈spot. (M)
7. **F12 + F13 + F11 — Validate and the Float detail show the server's state or "could not check".**
   - Never a prototype word.
   - Never an "is she in a trade" decided by engine.js.
   - No T1. (S)
8. **F24 + F25 + F26 — make the delivery boring.**
   - Vendor Preact, htm and lucide.
   - Bind Vite to 127.0.0.1.
   - Add `pro.html` to the build inputs.
   - Freeze ui-v2 edits during market hours. (S)
9. **F27 + F28 + F30 + F14 — cut and untangle.**
   - Cut: the `hold/*` UI, `BoardRev3` (move `useBoardGlance` out first), the AnswerBand, and the server's rev-2 `/api/hold/check`.
   - Move OI Flow and the other inline tabs out of `App.tsx`. (M)
10. **F14 + F15 + F16 + F17 — STOP-BUILDING trading logic in the browser.**
    - New reads go in the server.
    - The three LOCKED browser computations stay exactly as signed until a new registration moves them. (L)
