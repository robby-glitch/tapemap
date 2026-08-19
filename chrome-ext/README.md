# TapeMap v2 — Kite panel

> **SUPERSEDED (2026-08-15).** The TapeMap read now lives inside PaperDesk
> (the operator's own extension) painted directly on the Kite chart — zone
> state, WHY ribbon, absorption/fuel marks, premium-chart strips — via the
> same 127.0.0.1:8765 server. This panel still works and stays until the
> hybrid is verified on a live session; then this folder goes. Do not add
> features here.

A read-only Chrome extension that puts the TapeMap read beside the Kite chart,
so the options layer sits where the operator's eyes already are.

**It never places an order.** It has no broker permissions, no order code, and
no write path of any kind. The only network call it can make is a GET to
`http://127.0.0.1:8765` — that is the whole of `host_permissions`.

## Load it

1. TapeMap server must be running (**`start-v2.bat`**, port **8765** — not
   `start.bat`, which brings it up on Dhan, the dead source the panel's own
   broker banner warns about).
2. Chrome → `chrome://extensions` → turn on **Developer mode** (top right).
3. **Load unpacked** → pick this `chrome-ext/` folder.
4. Open `kite.zerodha.com`. The panel appears top-right; drag it by its header
   and the position sticks.

Reload the extension from `chrome://extensions` after editing any file here.

## Why it draws nothing on the chart

Two reasons, and the second is the real one.

1. **Kite already draws the bands.** That is the operator's own SDVWAP study —
   the sky-blue 2σ→3σ shading *is* the setup (`research-findings.md` §1b).
2. **Our bands do not match theirs.** `research-findings.md` §1c: TapeMap's σ
   runs **1.02–1.08 wider**, about 5 points at 3σ in the afternoon. Drawing ours
   on top would put two sets of blue bands on one screen a few points apart —
   a known bug, on screen, all day.

So the panel shows only what Kite **cannot compute**: everything downstream of
the option chain — verdict and why, the context line, dealer/gamma regime, pin,
the zone signal with its trigger quoted verbatim, cap/floor, and OI build.
Zero overlap with the chart, nothing to disagree about.

If `DEFERRED.md` §0f is ever fixed and the bands agree, drawing them becomes an
option. Until then it would be drawing a falsehood.

## What it shows, and what it refuses to hide

- The **trigger text is quoted verbatim** from `band_rotation`, not summarised,
  so a signal can be checked against the candle instead of trusted.
- `trap` and `confirm` are shown **even when they read SUSPECT / UNKNOWN**.
  On 2026-08-14 `trap` was SUSPECT on all ten signals and discriminated nothing.
  Hiding a filter that is not working would make the panel look more certain
  than the data is.
- A stale payload says **"frozen, not quiet"** and a dead server names itself.
  Silence must never be mistaken for a calm market.
- **The broker is in the header on every poll.** `start.bat` does not set
  `TAPEMAP_BROKER`, so it brings the server up on Dhan — whose Data API lapsed
  2026-08-05 — and the only symptom is an empty chart, indistinguishable from a
  quiet market. Anything other than `upstox` turns red and the panel says to
  restart with `start-v2.bat`. It is re-read every 15s rather than cached,
  because the case worth catching is a server restarted onto another broker
  mid-session. A server too old to serve `/api/health` shows `?` rather than a
  guess.

## Files

| file | what it does |
|---|---|
| `manifest.json` | MV3. Content script scoped to `kite.zerodha.com`; localhost is the only host permission. |
| `background.js` | Does the fetch. Required: an MV3 content-script fetch is treated as page-origin, so Kite → localhost would be CORS-blocked. |
| `content.js` | Builds, drags and renders the panel. Polls every 15s (the server refreshes at 15s). |
| `panel.css` | All `.tm-*`. Injected into someone else's page, so it inherits nothing and leaks nothing. |

## Status

**Unproven against a live tape.** Syntax checked and every field path it reads
was confirmed present in the live payload on 2026-08-14, but the panel itself
has not yet rendered during market hours. First real test is the next session.

## Not built yet

- **Option-leg charts.** The operator runs the same band study on legs
  (e.g. `NIFTY 18th AUG 24500 PE`). The panel always shows the index read; it
  does not notice which symbol the chart is on.
- **TradingView.** Not needed — `tapemap_bandreversal.pine` draws natively there.
  Kite cannot run Pine, which is exactly why this exists for Kite.
