Locked in: **modern fintech minimal**, **two-tier (glance + deep)**, with **all four** improvements baked in. Here's a detailed, paste-ready brief for Figma's AI. I've populated every component with **real values from today's tape** so it generates meaningful screens, not lorem-ipsum.

---

# Figma AI Brief — TapeMap Dashboard (v2, "elegant gem")

## 1. What this product is
TapeMap is a **real-time intraday dashboard for Indian index options traders** (NIFTY, BANKNIFTY, SENSEX). It reads live order-flow and tells the trader, in plain language, **which index is worth trading, which direction it's leaning, and whether now is the moment to act**. It never places orders — it's a signal/read tool. The user is a focused, fast-moving trader who needs to grasp the state of three markets in one glance and drill into one when it matters.

**Design mission:** calm, confident, elegant. Turn a dense trading terminal into a modern, minimal app where the *most important signal is the biggest thing on screen*, and detail is one click away.

## 2. Visual direction — modern fintech minimal (dark)
Reference the calm confidence of **Linear, Mercury, Ramp, Arc**. Spacious, rounded, quiet — color appears *only* when it carries meaning (direction/urgency). Everything else is grayscale hierarchy.

**Color tokens (dark theme):**
- Background: `#0B0E14` (deep navy-black) · Card surface: `#141926` · Inset: `#1B2130`
- Borders/dividers: `rgba(255,255,255,0.07)` (hairline)
- Text: primary `#E8EDF5` · secondary `#9AA7BD` · muted `#5D6B84`
- **Semantic only:** Bull/Up `#2EC27E` · Bear/Down `#FF5F6B` · Caution `#FFBF00` · Accent/"look here" `#8B5CF6` (violet, used sparingly for the trending highlight and GO/READY)
- Signals may carry a **soft glow** (12–20px blur, low opacity) when active — that's the one moment of flourish.

**Typography:**
- UI + labels: **Inter**. Section micro-labels are `11px`, UPPERCASE, `+0.08em` letter-spacing, muted.
- All prices/numbers: **tabular figures / monospace** (Roboto Mono or Inter tabular) so columns align.
- Headline read: `28–34px`, weight 600.

**Shape & spacing:** cards `14px` radius, soft 1px borders, subtle elevation. Generous `24px` gutters, whitespace *between* groups. No heavy gridlines. Desktop-first (1440px), cards reflow gracefully.

## 3. Layout — two tiers

### TIER 1 — GLANCE BAR (always visible, sticky top, full width)
Three regions left→right:

**(a) Brand** — small: `TAPEMAP ●LIVE` (the ● pulses green when live).

**(b) CROSS-INDEX TREND SCANNER** — the heart of the redesign. Three compact cells, one per index. Each shows: symbol · last price · % change · a trend arrow (▲▼〰) · one-word state. **The most-tradeable/trending index is highlighted** (violet border + soft glow + a small `LOOK HERE` tag). Clicking a cell switches the deep panel below to that index. Populate with today's real state:

| | | | |
|---|---|---|---|
| **BANKNIFTY** | 56,624 | ▼ −0.71% | *recovering — biggest mover* ← **highlighted** |
| **NIFTY** | 23,860 | ▼ −0.25% | *heavy, capped* |
| **SENSEX** | 76,360 | 〰 −0.04% | *rolled over* |

**(c) THE READ** — the selected index's plain-English headline + two **clearly labeled** chips:
- Headline: **"Down-leg exhausted — relief bounce under resistance"**
- `TIMING` chip → **WAIT** (amber) · `DIRECTION` chip → **BEARISH** (red)
- (The labels are essential — "WAIT" beside "BEARISH" must never read as a contradiction. One is *when*, one is *which way*.)
- Sub-line, muted: *"Reclaim VWAP 23,909 to confirm a turn."*

### TIER 2 — DEEP PANEL (switchable, fills the rest)
A quiet tab switcher: **[ Tape ]  Chain  ·  Events  ·  Validate  ·  Map**. Selected tab shown; others are muted text.

**TAB: TAPE (default)** — three columns:
- **Center — Price chart:** clean line/candles + VWAP line + a soft-filled ±2σ envelope band; small colored dots mark key events. Dim the "future" area beyond the current bar. No busy gridlines — just a faint VWAP reference and the band fill.
- **Left rail — KEY LEVELS** (ladder, nearest-to-price emphasized), each with distance in points:
  - `CAP  23,900  CE wall 7M   ▲ +40`
  - `VWAP 23,909  reclaim = turn`
  - `LOW  23,808  session low  ▼ −52`
- **Right rail — ORDER FLOW** (plain-English running readout, the new synthesized line):
  > **Selling dried up.** Futures discount refilled, call-writers covering (supportive). *But NIFTY OI is rebuilding — shorts may re-press.* **Move: decelerating.**
  
  Below it, a small **MM PERSPECTIVE** line in plain words (`Dealers still cap rallies (negative-gamma)`) and 3 mini volatility stats (Realized σ, 30m range + percentile, ATM IV).

**TAB: CHAIN** — option-chain analyser: big stat tiles (PCR 0.82 · Max Pain 24,000 · GEX +positive · Squeeze fuel) + a strike ladder with a subtle heat treatment showing walls (`23,900 ▼ put wall`, `24,200 ▲ call wall`) and where price sits.

**TAB: EVENTS** — the narrative feed in **plain English** (not jargon), newest on top, each row timestamped, tinted by direction, click-to-jump:
- `14:33  Fake low sprung — late shorts trapped, small bounce likely`
- `14:09  New low but puts aren't confirming — selling not fully paid for`
- `13:53  Call-writers being squeezed — supportive of a bounce`
- (Keep an optional small "jargon" tag on hover for learners, e.g. *BEAR-TRAP SPRUNG*.)

**TAB: VALIDATE** — a trade-checker: pick strike + side (CE/PE, long/short), get a confidence score (0–100) with a short list of *gates* that raised or lowered it ("method verdict is WAIT — size down", "negative gamma — trade with the move"). Clean form, one primary button.

**TAB: MAP** — the levels map (pivots, walls, flipped levels) on a vertical price axis.

## 4. States & motion (subtle)
- Verdict/bias chips recolor by value (GO/READY green-violet, WAIT amber, CAUTION/STAND-ASIDE muted, BEAR red).
- Scanner: when an index **newly flips into a clean trend**, its cell does a one-time soft glow-pulse to draw the eye (this is the "don't miss BANKNIFTY" feature).
- The exhaustion cue in Order Flow shows as a small badge: `● decelerating` / `● building`.
- Hover reveals tooltips with the underlying numbers. Transitions are gentle (150–200ms), never bouncy.

## 5. Screens to generate
1. **Main dashboard — Tape tab** (default), NIFTY selected, populated as above.
2. **Same, BANKNIFTY selected** via scanner (shows the highlight moving).
3. **Chain tab** and **Events tab** variants.
4. A **light-mode** counterpart of the main screen (same tokens inverted) — optional but nice for the system.

**Guiding principle for the AI:** one dominant signal per screen (THE READ), a scannable three-index strip, and *quiet* supporting detail. Elegance = restraint, hierarchy, whitespace, and semantic color — not decoration.

---

That's the full brief — you can paste it whole into Figma Make/First Draft. Want me to **save it as `design/figma-brief-v2.md`** in the repo so it's version-controlled alongside the punch-list, and/or produce a **tightened one-paragraph prompt** version in case Figma's input works better with something shorter?