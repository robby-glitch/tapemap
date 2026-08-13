# TapeMap v2 — handoff

**Point a new session at this file first.** It is the entry point; work that was
found, measured and consciously postponed is in **`context/DEFERRED.md`** — read
it before starting anything new, it exists so nobody re-derives a finding that
already has numbers. The rules themselves are consolidated in
**`context/CHECKLIST.md`** (every rule with its
source, plus a chart checklist showing what currently passes and fails); every
strategy verdict is in `context/research-findings.md`, and the deep UI
history is in `context/ui-v2-dashboard.md`, and the operator's own edge is
specified in `docs/superpowers/specs/2026-07-31-operator-band-rotation-setup.md`.

Last updated: 2026-08-13. **576 tests pass, none fail** (`pytest -q`, run
2026-08-13 — the four date-rollover failures noted on 2026-08-09 are gone).
Branch: `feature/dashboard-v2`, **pushed to `origin`** at `daa2d51`; four files
sit uncommitted, listed at the end of the 2026-08-13 entry.

### 2026-08-13 — 3-minute is canonical, and the live record is seven rows

**THE TAPE PUBLISHES 3-MINUTE CANDLES, and until 2026-08-12 it did not.**
`1002d52` splits `live.build_session` from `live.derive_payload`, `/api/data`
takes `?interval=`, `band_rotation.SCORED_INTERVAL = 3` names the one interval
§5c's 68.4% was ever measured at, and the Trade tab carries a switcher. Before
that the tape published 1-minute bars — so `RUN_WINDOW = 10` meant **ten
minutes live against the thirty the backtest measured**, and the arm and
trigger tests read 1-minute lows and closes. *Live was not running the rule
that was scored.* `band_rotation.py:850-862` states the standing rule: at any
other interval it is a different setup carrying no measured number.

**Signals differ by interval — asserted, NOT verifiable here.** The claim
carried into this session is that NIFTY on 2026-08-12 produced one SELL entry
at 1-minute (09:29, u3 24551.25, ref_low 24540.00, stop 24571.25) and none at
3m/5m/15m. Nothing in the repo holds it: `trigger_log.jsonl` has no NIFTY §5c
row at all, and `data/backtest/` has no August bars to re-derive from. Treat it
as an observation from a screen, not a record.

**What the live §5c record actually is** — counted 2026-08-13 from
`data/trigger_log.jsonl`:

| | |
|---|---|
| rows on disk | **263** |
| carrying `rule: "5c"` | **7** — 5 entries, 2 arms (`kind: "arm"`) |
| quarantined §1 one-candle rows | **256**, days 2026-08-04/05/06/07 |
| §5c days | 2026-08-10 (3 entries) · 2026-08-13 (2 entries, 2 arms) |
| §5c indices | SENSEX ×6, BANKNIFTY ×1 — **not one NIFTY row exists** |

**Nothing is scored.** `f15`/`f30` were never filled, and neither were the
outcome measures `69d3da0` added. The three 2026-08-10 rows carry their own
`unscored` sentence — *"no cached … session for 2026-08-10 in `data/backtest/`,
so no bar after this row could be read — this row is UNMEASURED, not flat"* —
and it is correct: the cache ends **2026-07-31** (NIFTY `fut_`/`opt_`
2026-04-01→2026-07-31; BANKNIFTY and SENSEX `fut_` 2026-06-01→2026-07-31). The
two 2026-08-13 entries carry no measure either.

**The operator's scoring spec, given 2026-08-13, is built** (`trigger_log.py`,
`score`): `anchor`/`anchor_px`/`anchor_t` name which price everything is
measured from; `mfe`/`mae` with their clocks are the max favourable and adverse
moves; `stop_px`/`stop_hit`/`stop_t` record whether the 20-point stop broke —
**recorded, not obeyed**, measurement continues past it; `bands` says how far
the OPPOSITE side's u1/u2/u3 (or d1/d2/d3) was reached, **read LIVE off each
arriving bar, never off the anchor bar's frozen numbers**, window to 15:15. The
rationale is the operator's: they hold when OI is heavy that side.

**`exit_why` is the RE-FIRE LOCK clearing — not a trade exit.** §5c point 7:
after an entry the next setup may arm immediately if stopped out, otherwise not
until VWAP is touched. `run_states` implements it as `lock` and its own
docstring calls `exit_why` "the bar the re-fire lock cleared". The operator
manages the trade and TRAILS; the tool records entry and stop only and has no
idea where they left. **This correction is only half landed:**
`trade/SetupCheck.tsx:868-877` was fixed on 2026-08-12 and now reads *"Re-fire
lock khula"* — but `App.tsx:2051` still renders `nikal gaye — VWAP par`,
`App.tsx:2217` puts `BAAHAR` in `document.title`, `GlassBoard.tsx:232-234`
still heroes `VWAP / par nikle / "the run is closed"`, and `machine.ts:37` is
the shared word that feeds both. **Owed: BAAHAR out of the machine strip and
the Glass board.**

**Arms are logged, and only since 2026-08-12** (`69d3da0`). `_arm_rows` writes
BOTH sides, d3 BUY and u3 SELL, at `interval: 3` **and no other interval**,
never off a forming bar, with `t_1m`/`extreme_1m` naming the minute inside the
bucket that made the extreme (`t_1m: null` plus `t_1m_why` on any doubt) and
`rearm` separating a moved reference from a fresh one. Earlier sessions hold no
arms by construction. **On disk: two arms, both 2026-08-13, both SENSEX d3 BUY,
both `rearm: false` — 09:33 (level 78072.89) and 11:06 (level 78061.59).**
*Correction to what was believed going in:* 2026-08-13 was **not** armless. It
is **NIFTY** that has never armed — zero NIFTY arm rows exist, and 2026-08-11
and 2026-08-12 have no arms of any kind because the logger did not exist yet.

**The NIFTY chain outage of 2026-08-12 — root cause found, fixed, uncommitted.**
`chain_live`'s reload trigger matched the substring `"token"`, and
`upstox_chain.poll`'s warming-up error ends with *"check the token first: python
upstox_auth.py"*. A socket that had merely not finished connecting therefore
forced a reload, the outer loop tore the socket down and rebuilt it, and
because the poller is a **round-robin** the FIRST index polled straight into the
next connect and tripped it again. **NIFTY was dead all session while BANKNIFTY
and SENSEX, polled 3.5s and 7s later, were fine on the same socket.** Fixed at
both ends: `chain_live.is_auth_error` matches 401 / unauthorized / invalid token
— the failure, never the advice — and `UpstoxChainSource.start` now waits up to
`upstox_chain.CONNECT_WAIT_S` (10.0s) for the socket instead of handing back a
feed still dialling. Covered by `test_chain_auth_error.py`.

**⚠️ THE d2/d3 READING TRAP — it cost two rounds of argument, 2026-08-11 and
2026-08-13.** The outer σ wash spans d2→d3, so a candle entering the blue reads
as touching the extreme when it has only reached **d2**; both times the low was
6–10 pts short of d3 with d2 tagged, and both times it was called a missed
signal. The chart now draws **d3 and u3 only** as solid 2.5px brass lines with
filled chips (`d3 · ARMS THE BUY` / `u3 · ARMS THE SELL`) — deliberately unlike
the 1px dashes every other level uses, because the first cut drew them as dashes
and they became the fifth indistinguishable dashed line. No other band edge is
drawn: `ba76dab` took the VWAP polyline and σ band edge strokes off, `12bae52`
dropped VWAP/±1σ from the chart's level list.

**Also landed 2026-08-11/12:** `8d85b7e` machine strip at shell level with a
`document.title` mirror · `ae76a05` a wall strike is compared in its own frame,
so call/put wall marks draw again (they never had) · `8760d15` the stop travels
with the level (`band_rotation._stop_px`) · `3dd9977` glance-bar scanner shrink
· `12bae52` the §5c SELL finally draws (`runDrawPlan` had rejected SELL/u3 as
"unexpected") · `f2c6c46` the day's §5c signals stay on the setup panel ·
`aedbd51` `/api/oiflow` publishes `chain_ok`/`chain_why` · `b2bf31d`
signal_review JSON snapshot · `69d3da0` Signals tab, `/api/signals`, ARM logging
and the scorer · `ba4be66` the Glass board · `daa2d51` critique and comps
committed, run logs gitignored.

**Uncommitted in the working tree** (`git status`, 2026-08-13): `chain_live.py`,
`upstox_chain.py`, `test_chain_auth_error.py` (the chain fix above) and
`ui-v2/src/trade/LevelsOverlay.ts` (the d3/u3 arming lines). `data/trigger_log.jsonl`
is also dirty — that is the live log appending, not an edit.

### 2026-08-09 — live collection is ARMED, and unverified until Monday

**The server was restarted 03:12 IST.** `/api/health` answers, broker `upstox`,
all three indices, uptime confirmed at 2.4 min so it is a fresh process on the
current code.

**What is NOT yet verified, and must not be called verified:** that a live
payload actually carries `rotation_run_sell`, and that a sell fire reaches the
log. Both need bars, and 2026-08-09 is a Sunday. A fresh process makes it very
likely; likely is not measured, and the last `trigger_log` bug lived in exactly
that gap.

**MONDAY, after 09:15 — run this first:**

```bash
python -c "import json,urllib.request as u;d=(json.load(u.urlopen('http://127.0.0.1:8765/api/data?idx=NIFTY')).get('days') or [{}])[-1];print({k:(len(d[k]) if isinstance(d.get(k),list) else d.get(k)) for k in ('rotation_run','rotation_run_sell','run_state','run_state_sell')})"
```

All four keys must return numbers. **`rotation_run_sell` missing = the server
is on old code and collection is half-blind.** After the close: `python trigger_log.py`.

**An empty table is NOT a failure.** The setup fires 1–2× a week. Whether
collection works is answered by the key check, never by the row count.

The 256 rows already on disk are quarantined (`rule != "5c"`) — they were
logged from `rotation`, §1's one-candle TOUCH, not the entry the chart draws.
The new sample starts at zero.

### The numbers that changed today, and one correction

`trail_score.simulate` is side-aware now (BUY proved byte-identical against a
pre-edit baseline, md5 `4a24a97f…`). Under the ADOPTED management on the
current §5c entries, NIFTY:

| | n | mean | median | hit |
|---|---|---|---|---|
| BUY d3 | 19 | +0.32 | **+6.90** | **63.2%** |
| SELL u3 | 18 | +10.18 | **−0.75** | 44.4% |

**Neither mean survives its own tail.** Strip one winner and BUY → −6.99,
SELL → +0.65. BUY's top two are +177.5 against a +6.0 net. Full table: §5f.

**CORRECTION worth carrying forward:** §1's "+4.8 mean / 56% hit" is from the
VOID one-candle trigger and was quoted twice today as if current. On the real
entries the buy's mean is +0.32. **The scored edge's case rests on median and
hit rate, not mean** — any surface quoting a mean for it quotes the wrong
statistic.

**C13 (new):** the fixed 30-minute exit is REFUSED. §1's own table measured it
and did not adopt it; it has no stop, so it is not a trade. It reappeared twice
today as a scoring bar because the refusal had never been written down.

### 2026-08-08 — the rail is full, and the sell side exists

- **SETUP CHECK panel** fills the 260px rail (`trade/SetupCheck.tsx`). Two
  tallies that are NEVER summed — TRIGGER (scored) and SAATH (unscored) —
  because C7 and C11 both measured "more conditions = better" as false. Three
  tick marks, not two: brass = the tool measured it, ink = the operator's hand,
  dashed amber = could not be checked. Ticks are keyed by session day, so the
  daily reset needs no clock.
- **The structure layer narrowed.** FVG, BOS and CHOCH are no longer drawn;
  SWING_H/SWING_L are, for the first time. Withheld kinds are COUNTED and
  disclosed in the `Chhupa hua:` line even with the toggle on.
- **Levels light up by proximity**, in σ so it self-scales across indices. Only
  ONE level takes a directional hue — the next one price is moving toward — and
  trap levels are excluded so their red keeps meaning "trap", not "down".
- **The u3 SELL mirror ships** (`band_rotation.run_states(..., side="SELL")`),
  built over C3's rejection at the operator's explicit instruction. `BUY 19 /
  SELL 18` over the 65-session NIFTY cache; the 19 matches the scored rule's
  own n exactly, which is the proof the buy path did not move. A `run_score`
  baseline was taken BEFORE the edit (`md5 50846ca6…`) and is unchanged.
- **The Trade tab speaks Hinglish** — chrome only. Every string the BACKEND
  authored and the UI quotes verbatim is deliberately untranslated.

**Read `context/DEFERRED.md`** for what was found, measured and postponed.

---

## 1. Boot sequence

Run BOTH in your own terminal windows. **Do not let the assistant start them** —
assistant-spawned processes die when its tool session recycles, which caused two
mid-session "disconnects" on 2026-08-03. The backend the operator started at
09:16 that day ran until close, untouched.

```bash
python server.py live 8765
```
```bash
corepack pnpm --dir "C:\Users\kaam\Desktop\new tool nifty\ui-v2" dev
```

### Running on Upstox instead (2026-08-05)

Dhan's **Data API subscription lapsed** on 2026-08-05 (401 / DH-902) and the
tape went dark. Upstox drives the whole stack for free, and both the chain and
the bars are wired behind one switch:

```bash
python upstox_auth.py          # once each morning; token dies 03:30 IST
```
```bash
TAPEMAP_BROKER=upstox python server.py live 8765
```

PowerShell: `$env:TAPEMAP_BROKER = "upstox"` on its own line first.

**The desktop shortcut does all of that now (2026-08-06).** `start-v2.bat` — the
`TapeMap v2` shortcut — sets `TAPEMAP_BROKER=upstox` itself and runs
`upstox_auth.py` whenever `.upstox_token` was not written today. Until this it
set **nothing**, so the shortcut launched both halves on Dhan, and the only
symptom would have been an empty chart. The commands above remain the manual
path; the shortcut is the one-click one.

Three things that were still reaching for Dhan on the Upstox path, all closed
the same day (`test_upstox_only.py`, 5 tests):

- `live._token()` opened `.dhan_token` **unconditionally**, so deleting a file
  the Upstox path never transmits would have killed the whole tape. It now
  returns `""` on Upstox — and still raises on Dhan, because a missing Dhan
  token there is a real misconfiguration, not something to paper over.
- `POST /api/token` (the **⟳ TOKEN button**) validated a Dhan JWT and wrote
  `.dhan_token` while the running tape and chain read `.upstox_token` — an
  "accepted" that changed nothing the operator could see. It now refuses on
  Upstox and names `upstox_auth.py`. The button itself is Dhan-only; there is
  no Upstox equivalent to click.
- A server **already up on 8765** has its broker fixed at *its* startup, not by
  the launcher. On the very first run of the fixed launcher this fired: a Dhan
  server from the previous afternoon (started 05-08 14:16) still held 8765, the
  launcher reused it, and the whole dashboard was placeholder data. Warning
  about it was not enough, so the launcher now **asks the server** via
  `GET /api/health` and offers to stop it. Verified against that exact stale
  process: the probe exits 1 (no such route), both Y and N branches correct.

**`GET /api/health` (2026-08-06).** Answers whatever the tape is doing —
`{ok, broker, started_at, indices}`. It exists because every other route
conflates two different failures: `/api/data` returns a `live_error` body BOTH
when the broker is dead and when the market simply has not opened. Two callers
need them apart — `start-v2.bat` before reusing a port, and the UI banner.

**The NOT LIVE banner was lying (2026-08-06).** At 02:50 it read *"the backend
is unreachable… An expired Dhan token is the usual cause"* while the backend
was up, answering, and correct — it had said `no bars yet for 2026-08-06`,
because the market had not opened. `data.ts`'s `fetchIdx` collapsed every
failure into one `null`, so "we checked and found nothing" and "we could not
check" rendered identically (§9 A1). It now returns `{reachable, why}`: only a
rejected `fetch` means unreachable; any HTTP answer means reachable, and the
backend's own sentence is shown verbatim. The ⟳ TOKEN button now appears only
where it can change something — never on Upstox, never when nothing answers.

- **Dhan stays the default.** Anything not exactly `upstox` runs Dhan, so a
  typo fails safe rather than moving the tool to another source while the tape
  keeps printing plausible numbers (`test_broker_switch.py`).
- `.upstox_app.json` holds the api key/secret (gitignored); `upstox_auth.py`
  writes `.upstox_token` and preserves the old one at `.upstox_token.bak`.
- **`oi_chg` means "since 09:15", not "since prior close"** — it will not match
  the OI Chg column on a broker chain. Deliberate: the 09:15 bar includes the
  pre-open auction, and today's positioning is what the writer score wants.
- Startup costs ~9s (34 throttled baseline fetches + resolve + connect); a poll
  touches **no network at all**.
- A connected-but-silent socket **raises** past 30s rather than re-serving its
  last snapshot — the 2026-07-27 frozen-tape lesson.
- `UDAPI100050` from Upstox means the WRONG TOKEN CLASS, not an expired one.
  An Analytics Token opens history only.

**`/api/contract` moved too, 2026-08-05.** The leg charts were the last thing
wired to Dhan — `chain_live.read_token`, a `dhanhq` client for the expiry, and
`dhan_fetch.rest_intraday` per option bar — so with the subscription gone the
CE/PE panes were a 500, not an empty pane. `build_contract` now branches on the
same `TAPEMAP_BROKER` switch (`test_contract_upstox.py`, 16 tests, offline).
Verified live 2026-08-05: NIFTY 24600 both legs, 129 3-min bars, no gaps, OI
7.98M / 5.13M, index series resolved to `NSE_FO|58072` from the dump.

Three things about that path that are NOT the same as Dhan's, and are disclosed
rather than smoothed over:

- **The pair needs the poller's snapshot.** On Upstox the chain arrives over
  the websocket `ChainPoller` owns, and this route will not open a second one.
  `server.py` already passes `chain_rows`; a direct call without one gets a
  refusal sentence, not a guessed strike.
- **Backfill charts the CURRENT front contract.** Upstox's dump carries live
  instruments only — an expired weekly is *absent*, not merely unresolvable —
  so `day != today` publishes `expiry_why` saying the bars are real but belong
  to a different instrument than the one that was front that day. Today is the
  only faithful reproduction.
- **The session is 10 minutes longer.** Measured 2026-08-05: Upstox serves
  **385** 1-min bars (09:15→**15:39**, with real volume — 424,385 on the 15:39
  CE bar) where Dhan served **375** (09:15→15:29). Nothing is wrong with either;
  the consequence is that the VWAP/σ tail differs between brokers. The operator
  is flat by 15:15, so it does not touch the d3 rule — but do not compare a
  Dhan-era band print against an Upstox one at the close and call it a bug.

Still on Dhan: everything in `dhan_fetch.py` (backtest tooling).

- UI at `http://localhost:5173`; Vite proxies `/api` → `127.0.0.1:8765`.
- **The Dhan token expires daily** — first click of the day is **⟳ TOKEN**.
- `corepack pnpm`, never bare `pnpm` (not on PATH).
- **"The app stopped" → check BOTH ports:**
  `netstat -ano | grep -E ":(8765|5173)"`. Backend alive + Vite dead is the
  common case; no data is lost, just restart Vite.
- For maximum stability during a live session, `pnpm --dir ui-v2 preview`
  serves the built `dist/` (own proxy block, no HMR to fall over). Trade-off:
  code edits need a rebuild.

## 2. Gates — all three before any commit

```bash
corepack pnpm --dir ui-v2 exec tsc --noEmit
corepack pnpm --dir ui-v2 build
python -m pytest -q
```
**432 tests as of 2026-08-07.** `vite build` does **not** typecheck — run `tsc` too.

---

## 2026-08-07 — the chart marks the entry now, and the morning survives a restart

Four things landed. Read this before touching the rotation layer or the chain.

**The chart was marking the wrong bar, and no longer is.** `rotation` is §1's
one-candle rule, which `research-findings` marks **VOID** — it fires when a bar
tags d3 and reverses inside that same bar, so every pill sat on the **touch**.
The operator enters on the **close that breaks the touching bar's high**, one or
more bars later. `live.py` now publishes, additively:

    rotation_run   §5c's two-candle ENTRIES, 1:1 with bars
    run_state      the same machine per bar — WAITING / ARMED / TRIGGERED /
                   IN_TRADE, plus ref_high, candles_left, exit_why

`rotation` is still published and still read by v1's `ui/app.js`. The two mark
different bars, so **neither is a fallback for the other**; the UI says so when
`rotation_run` is missing rather than substituting.

`band_rotation.run_states` is the one loop; `detect_index_run` is a one-line
view of it. The refactor was proven byte-identical over the whole cached corpus
(152 sessions, 39 signals, same sha256 before and after — the baseline was
captured BEFORE the edit, which is the only reason it proves anything), and
`run_score.py` still reproduces every published figure.

**The 09:25 and first-of-run filters left the frontend.** They were in the
scorer AND hand-written in `LevelsOverlay` — one rule in two languages, which
is how the original gap opened. Both now live in `run_states`. `rotDrawPlan`
became `runDrawPlan` and no longer filters: it VERIFIES, counting anything §5c
cannot legally emit as a *backend disagreement*. That count should never print.

**`chain_backfill` rebuilds the morning.** The chain is only ever recorded live
— Upstox's socket has no history and `_warm_start` replays only this tool's own
file — so a poller starting at 12:18 had no morning while the chart beside it
showed 09:15 onward. It now refills `ChainState.minutes` from REST after the
first successful poll, on a daemon thread, writing **only marks earlier than
anything recorded**. Verified against the socket's own file: 122 overlapping
marks, per-strike `oi_chg` exact on 82% of 4,148 values, aggregate within a
median 1.45%. **It fills `minutes` and nothing else** — REST candles carry no
IV or greeks, so GEX and anything gamma-weighted stay honestly absent.

**The OI pane says what happened.** It was one grey line of the LEVEL, which
answers "how much" — a question nobody asks mid-session, and explicitly not
what the operator's rule uses (*"oi is lagging so we need to prempt by the
change"*). The pane label is now a sentence:

    PE 24600 · SHORT COVERING — writers covered 4.57 L · 79.78 L open · -5.37 L today

Four states, and the noun follows the contract: **writers/buyers** on an
option, **shorts/longs** on the future. A flat close or flat OI says "no read"
instead of guessing one of four directions.

### Settled — no longer to be asked

- **Stop is 20 points; targets +2σ and +3σ**; the operator manages the exit by
  hand (this closes CHECKLIST D6). One definition: `OPERATOR_STOP_PTS`.
- **Draw the setup on BANKNIFTY too.** Told that C4 measures d3 there at 37.5%
  hit / median −75.90 (n=8), the operator said do it anyway. That stands — do
  not re-litigate. What must not happen is the screen implying BANKNIFTY d3
  carries NIFTY's 68.4%.
- ~~**The hover callout is theirs.**~~ **LIFTED 2026-08-08.** The hands-off was
  always conditional — *"i am thinking of modifying it in some way but later"* —
  and the operator has now called that later: *"dusre session m hum apne dynamic
  callout jo h uspe kaam karunga and the other thing like wall khiski trap
  sprung band se palta everyhting"*. It is the next session's subject. Do not
  refuse to touch it on the strength of the old rule.

### Next session starts here

**FIRST, and only if it is a trading day after 09:15 — the collection check.**
It takes ten seconds and it is time-boxed in a way the rest of this is not.
The command and what a failure looks like are in the 2026-08-09 section at the
top of this file. If `rotation_run_sell` is missing, stop and fix that before
anything else: collection is half-blind and every session that passes is a
session of evidence lost. An empty log is fine; a missing key is not.

**Then, the actual subject — the callout and the event vocabulary.**


The operator's own words, 2026-08-08: *"dusre session m hum apne dynamic
callout jo h uspe kaam karunga and the other thing like wall khiski trap sprung
band se palta everyhting i m gonna work on it"*. This is a DESIGN session with
them, not a build-it-and-show-them one — ask before building, three designs
have been rejected before.

**Where it lives.** `trade/Callout.tsx` renders it; `trade/narration.ts` joins
the engine's event stream to bars and tiers it; `trade/hinglish.ts` holds every
gloss (`WALL KHISKI`, `TRAP LAGA`, `BAND SE PALTA`, 25 kinds) plus the
`call | risk | lean` claim table; `LevelsOverlay.drawBalloons` draws the pills.
The kinds themselves are emitted by `engine.py` and `chain_metrics.py`.

**Four things that constrain any redesign — none of them are style.**

1. **A gloss describes the KIND only.** It states no number and never infers a
   direction. Direction comes from `tone`, decided upstream in `data.ts`'s
   `evDir`; the gloss only puts a Hinglish word on a direction already decided.
   An unrecognised kind returns null and the UI shows the engine's own string —
   untranslated, never mistranslated, never silently dropped.
2. **The three claim strengths are load-bearing, not decoration.** `call` (the
   market DID something), `risk` (could happen NEXT, explicitly not yet),
   `lean` (positioning tilts, no prediction). They exist because the direction
   chip once worded all three identically as "ishaara", and on 2026-07-30 the
   `call` kinds ran 15/18 at +30m while `lean` and `risk` ran 11/27. A warning
   dressed as a read is the thing that gets acted on.
3. **STORY is default OFF on measurement, not taste.** `signal_review.py`
   scored the engine's directional events at −0.1 pts (`risk`, n=16) and −6.2
   (`lean`, n=16) at +30m against a +4.1 control — two of three buckets did
   worse than doing nothing, at ~83 events a session drawn at equal weight.
   Any redesign that turns the layer back on by default is re-opening that.
4. **The engine's own sentence is quoted verbatim beside every gloss.** Nothing
   in the callout may strengthen, soften or re-word a claim the engine made.

**Already fixed, so do not "discover" them again:** wall migrations have
hysteresis (`WALL_HOLD = 3`, P2) after 12 headlines in one hour on 2026-08-04;
`GAMMA-PIN`'s gloss is deliberately regime-neutral because the kind fires as
FLOOR, CEILING and PINNED alike.

### ~~The left panel~~ — DONE 2026-08-08

The three questions below were answered: the panel was FILLED (the watchlist
idea dropped — the three indices already render in App's glance bar off the
same payload), scroll-snap was not needed once the chart took a screenful, and
the level labels remain open in `DEFERRED.md §3`. Kept for the reasoning.

### The original note

The Trade tab now has Kite's shape: a 260px panel down the left
(`CHART_SIDE_W` in `TradeTab.tsx`), the chart owning the rest, leg charts off
by default (`LEGS OFF` cycles OFF → SPLIT → STACKED). The chart takes a full
screenful — 76% of the viewport, measured — and anything above it is one
scroll up.

**The panel is empty and says so.** That is where the work resumes. The
operator's words when it was sized: *"left side m watchlist k liye space h."*

Three things to settle there, none of them guessed yet:

1. **Fill it or drop it.** The three indices already render in the glance bar
   at the top of `App.tsx` — same data, so a watchlist here would be a second
   view of it, not a new fetch. If it stays empty, 260px of dead space is worse
   than no panel at all and the chart should take the width back.
2. **Scroll-snap.** The height is right but the landing is approximate; the
   operator asked for *"1 scroll k baad"*. CSS `scroll-snap-type: y proximity`
   would land it exactly. Deliberately NOT added — a snap that feels wrong is
   worse than none, so it wants trying, not assuming.
3. **The level labels still overlap** at the chart's left edge — MAX PAIN, ±1σ,
   S2, S3, TRAP stacked on each other. Open in `ui-audit.md` under Readability,
   and it is the single ugliest thing next to Kite's clean scale.

Layout rules that now apply: **E6b** — the chart owns a screenful, do not
"reclaim" it by subtracting the header again. **E7** — a side rail is safe
where a row below the chart is not, and E4 says verify by measuring the canvas,
not by eye.

### Still open

Phase 5 — the state machine ON the pills. `run_state` is published and unread:
the ARMED countdown, the `ref_high` line to beat, the stop at d3 − 20. Then
`ui-audit.md`'s P1s (contrast, focus indicators). And the OI Flow header still
reads "since the open", which is true once the backfill runs and a lie when it
fails.

**GateGuard hook:** the first Write/Edit per file, and the first Bash call per
session, are denied with a request for facts (importers, affected API, data
schemas, the user's verbatim instruction). State them, retry the identical call.
Not a permission failure.

## 3. What is on screen (Trade tab, top to bottom)

| region | file | notes |
|---|---|---|
| stat strip + toggles | `trade/TradeTab.tsx` | LIGHT/DARK, FOCUS, SMC, STORY, LEGS, index switcher |
| disclosure lines | `TradeTab.tsx` | stale tape, date precision, chain stale, layer unavailable |
| **index chart** | `trade/ContractChart.tsx` + `trade/LevelsOverlay.ts` | candles, VWAP+σ ribbons, MAP levels, rotation pills |
| **OI strip** | `TradeTab.tsx` | latest `/api/oiflow` mark; 15s tab-local poll, no Dhan cost |
| ribbon + legend + "Hidden:" line | `TradeTab.tsx` | the Hidden line reports what the toggles withhold |
| **CE / PE premium panes** | `trade/LegChart.tsx` | own VWAP+σ, own OI pane, own prior-day pivots |
| **ZONE READ** | `trade/ZoneRead.tsx` | WHERE / BOOKS / GEX / FLOW / GAMMA / STRUCTURE / SETUP |
| ENGINE READ | `TradeTab.tsx` (`EngineReadPanel`) | verdict, setup, plays, floor/cap |

**localStorage keys:** `tape.mode`, `tape.focus`, `tape.smc` (default **OFF**),
`tape.story` (default **OFF**), `tape.legstack` (default OFF = side by side).
SMC and STORY default off deliberately — see §6.

## 4. ⚠️ The layout trap — read before touching TradeTab (cost two bad edits on 2026-08-03)

`TradeTab`'s root column **must** keep a definite `height: availH`, because
`ContractChart`'s root is `height:100%` and a percentage cannot resolve against
an auto-height flex container. Switching it to `minHeight` collapses the index
chart to **zero** (measured: `CANVAS 0 → DIV 0 → DIV 0` inside a 420px box).
The leg panes survive that, because they size from a real pixel `minHeight`.

Consequence: the column cannot grow, so **anything added after the chart goes in
the section BELOW the column**, never inside it. Rows inside compete for the
chart's pixels and, once the chart hits its floor, spill out and paint over the
CE pane. Current guards: chart `minHeight: 180`, column `overflow: hidden`.

**If you add a row under the chart, verify the index chart still renders** — not
just that your new row looks right. That is exactly the check that was skipped.

## 5. Backend map

| file | role |
|---|---|
| `server.py` | routes: `/api/data`, `/api/chain`, `/api/oiflow`, `/api/contract` |
| `live.py` | `build_payload`, `_nearest_opt_expiry`, `_floor_pivots`, `_opt_pivots`, `_atm_ids`, `_pivots`, `build_contract` |
| `engine.py` | `Session` / `session_json` — per-bar `ctx`, `gamma`, `setup`, and `fut`/`ce`/`pe` legs |
| `chain_metrics.py` | `ChainState`, `oi_flow` (minute grid; no Dhan call) |
| `structure.py` | SMC layer (FVG/OB/BOS/CHOCH/EQH/EQL/PDH/PDL/PREMIUM/DISCOUNT) |
| `band_rotation.py` | **the operator's own setup** — `detect_index` + two-leg `detect` |
| `contract_bars.py` / `contract_pair.py` | premium bars + σ bands; the 09:20 pair picker |
| `backfill.py` / `squeeze_score.py` | extend `data/backtest/`; score the squeeze hypothesis |
| `signal_review.py` | the scoring harness — **underused, see §7** |
| `trigger_log.py` | **live trigger logger (2026-08-04)** — server.py's refresh thread appends every NEW band-rotation record to `data/trigger_log.jsonl` with the bar's gamma/ctx + chain OI strength at that moment (fail-soft: can never stall the tape). `python trigger_log.py` = table, `score` = fill f15/f30 later. **Needs a server restart to activate.** Scores checklist items #17 (gamma regime) and #18 (ΔCE/ΔPE ratio) after ~20-25 live signals. |

**Ops gotchas:**
- Dhan `toDate` is exclusive for the newest session but INCLUSIVE for older
  ones — always slice with `_one_session`.
- `FUT_ID "61093"` in `dhan_fetch.py` is stale; the resolver gives 58072.
- **Dhan serves nothing before 2026-06-01** — expired contracts drop out of the
  scrip master, and `resolve_dynamic` silently returns the CURRENT contract for
  any historical date rather than failing.
- Contract OI ramps mechanically through rollover week (1.2M → 18M). Never
  compare front-month and far-month captures on OI *level*.
- `data/backtest/`: NIFTY flat (`fut_<ISO>.json`), other indices in
  subdirectories. An index PREFIX would corrupt eight readers that slice the
  date with `basename(p)[4:14]`.
- The Bash tool is Git Bash, not PowerShell: `@'…'@` here-strings mangle commit
  messages. Use `git commit -F - <<'MSG'`.

## 6. Verified vs unverified — the honest table

| claim | status |
|---|---|
| σ bands match the operator's Kite export | ✅ VWAP 0.078 pts median, ±3σ ratio 0.981 |
| backfilled Dhan == operator's Kite CSV | ✅ close diff 0.00, OI ratio 1.0000 |
| band pipeline order (`vwap_bands` → `resample`) | ✅ 0.972; reversed order 0.948 |
| option legs on the current weekly expiry | ✅ live 2026-08-03, held through a 24600→24700 strike hop |
| leg pivots vs Kite on the same contracts | ❌ **never cross-checked — do this first** |
| SMC layer | ❌ 4× over-fires vs LuxAlgo; ~⅔ UNKNOWN by construction → default OFF |
| engine event stream | ❌ `risk` −0.1, `lean` −6.2 vs a +4.1 control → default OFF |
| squeeze + falling OI = fade | ❌ **tested and REJECTED** — BANKNIFTY inverts the sign |
| d3 reversal on F&O STOCK futures | ❌ **REJECTED 2026-08-04** — pooled 47% hit, med 0.000% (n=47, 7 names + operator's own ADANIGREEN/RELIANCE TV exports). `stock_score.py`. Why, and the σ-scale arithmetic: **`research-findings.md` §3** |
| overnight gap-fade | ❌ **REJECTED 2026-08-03** — NIFTY fade ≈ 0 and below its own long control; reversion is intraday-only. `gap_score.py`. Detail: **`research-findings.md` §2** |
| classic 15-min ORB | ❌ **REJECTED 2026-08-03** — NIFTY breakouts *fade* (39% hit, −21.1 to close). `orb_score.py`. Detail: **`research-findings.md` §2** |
| **`band_rotation` — the operator's edge** | ⚠️ **SCORED — the one surviving edge.** NIFTY d3 buy: 72% hit, med +21 @30m vs +0.3 control (n=18). d2 = noise, selling = dead, compression filter = harmful. Management measured too (`trail_score.py`): **hold the stop until VWAP, never breakeven**. Two-leg confirm scored (`confirm_score.py`): does not help buys. **Full rule + numbers: `research-findings.md` §1** |
| ZONE READ confluence | ❌ makes no claim by design; unvalidated as a read |

## 6b. 2026-08-04 — the frame-bug day, and where v3 starts

**One class of bug produced most of what felt broken.** The tape is the MONTHLY
future; the option legs are the NEAREST WEEKLY. The carry between them ran
59→104 points that day — more than a strike step — and it was reaching both the
maths and the pixels. Fixed end to end (commit `67b9e6a`, `19ab6df`, `32e1db0`):
the engine's option forward and strike pick, `ctx.pin.dist`, `ctx.cap/floor`,
and on the UI side the walls, PIN, STK, max pain and gamma flip. The rule now
is one sentence: **anything DRAWN on the chart is futures-frame; any DISTANCE
to a strike is index-frame; `basis` is published in the payload and a level
whose frame is unknown is not drawn at all.**

Also fixed: `trigger_log` was logging forming bars (5 of 12 rows that morning
did not survive their own bar's close); `flip_px` conflated three kinds of
missing; `gex_regime` labelled off `gex_total` while the near-money book said
the opposite.

**A verdict went VOID.** `confirm_score.py` measured the two-leg confirm on
**monthly ATM** legs. The operator does not trade ATM — they take
**premium-matched legs, both above ₹100, within ±₹25 of each other**, going deep
ITM when the near strike gets cheap (see the `operator-trading-style` memory).
On 2026-08-04 the ₹11 ATM CE tagged no band all session — no entry signal and,
worse, no exit — while their real 24500 CE gave both. So "confirm does not help
buys" was measured on the wrong instrument: **void, not disproven.** Re-run it.

**✅ ALL SEVEN FIXED, 2026-08-05.** The table below is kept as the record of
what was wrong and where. Each row now names its fix; each has tests.

| | fix |
|---|---|
| D2 | writer score classifies PER BAR (chain_metrics' rule) and saturates against W_SAT of the CURRENT book, so pegging must be earned. `test_writer_score.py` |
| D3 | the IV gate is one shared `_sane_iv`, used by the GEX computation as well as the display. `test_chain_metrics.py` |
| D5 | `gex_spot` widened to `GEX_SPOT_STEPS = 2` and publishes `gex_spot_band`. Deliberately not wider — it earns its keep by disagreeing with `gex_total` |
| D7 | the floor lives in one place (`GAMMA_T_FLOOR`) and `t_real`/`t_floored` travel beside it. `test_expiry_clock.py` |
| D8 | engine imports chain_metrics' rule and constants instead of restating them; `w_bars_ce`/`w_bars_pe` publish the confidence. **Correction:** there were **two** producers, not three — the third was a display-side read |
| P2 | a wall must hold `WALL_HOLD = 3` readings before it announces. Flicker resets the candidate, so it can never accumulate |
| basis | implausible carry → `basis: null` + `basis_why`, never a fabricated 0.0. Band is asymmetric (−0.15%..+1.0%) because futures trade above the index. `test_option_frame.py` |

**Two things these fixes deliberately did NOT do**, so nobody reads them as
finished:
- The **UI discloses none of it.** `basis_why`, `t_floored`, `w_bars_*` and
  `gex_spot_band` are all published and all unread. The backend tells the
  truth; the screen is still silent. v3's job.
- When `basis` is null the engine still runs at `basis=0.0`, so `ctx.pin.dist`,
  `cap` and `floor` are computed as if carry were zero. Teaching the engine
  "basis unknown" is a larger change and was not folded in.

**Still broken** (the original independent audit, 2026-08-04) — none of these
were cosmetic:

| | what |
|---|---|
| D2 | `engine.py` writer score self-scales off its own running max and reads direction from cumulative premium vs open with a 2% floor — on expiry day theta alone trips it, so `w_ce` pegs at 1.0 and the regime carries no information |
| D3 | raw Dhan IV feeds GEX with no clamp; the sanity gates exist but only on the display path |
| D5 | `gex_spot` sums ±1 strike (2 strikes) — too narrow to be stable |
| D7 | `t_days` floors at 0.25 and freezes through expiry afternoon |
| D8 | three independent writer-score methodologies feed three panels, with no confidence anywhere |
| P2 | wall migrations have no hysteresis — 12 "headlines" in one hour on 2026-08-04 |
| new | no sanity guard on `basis`; the post-close chain print gave −52.9 |

**UI audit** (`/impeccable audit`, scored 7/20): both P0s fixed. Seven left —
zero `@media` queries anywhere, no focus indicators, no `prefers-reduced-motion`,
`transition: width`, four side-tab accent borders, Inter/Roboto (a terminal needs
tabular figures), and ~30 hard-coded colours outside `theme.ts`.

**v3, agreed 2026-08-04.** Not a dashboard — a **state machine**: WAITING →
ARMED → TRIGGERED → IN TRADE → OUT, where the screen is mostly EMPTY because the
setup fires 1-2× a week. It is a **new frontend on this same backend**; if v3
touches the backend it is not v3, it is a third unfinished app. Order agreed:
commit (done) → D2 + basis guard → whale/`confirm_score` measurement → v3.
**Charting foundation — SETTLED 2026-08-05. Keep `candl`.** The throwaway
`/proto` spike ran. lightweight-charts **passed all three** pre-registered
proofs (σ envelope with `drawRibbon` reused at a one-line diff, OI pane from a
bare `paneIndex`, pills anchored with no rAF loop) — and the answer is still
candl, because the rubric missed the axis that decides it: **drawing tools.**
`candl` ships **61** with a full lifecycle API; lightweight-charts ships
**zero**. Full scoring, and the three things worth salvaging from the spike:
**`research-findings.md` §6.**

**The live finding underneath it:** ui-v2 turns **none** of those 61 tools on.
The entire app-side reference to candl's drawings module is
`LevelsOverlay.ts:5` importing the `Converters` *type*. The operator has never
been able to draw on their own chart, and the fix is a toolbar, not an engine —
`setActiveTool` / `setDrawings` / `onDrawingsChange` / `setMagnet` are already
on `IChartEngine`. Verified working 2026-08-05 (`ui-v2/src/proto/ProtoDraw.tsx`,
11 of the 61 exercised, drawings surviving a refresh via localStorage).

**So v3's first chart task is exposing that toolbar, not replacing the engine.**
Mind §4 when it lands in TradeTab — a row under the chart is exactly what
collapsed it twice.

`ui-v2/src/proto/` is a **throwaway**: delete the directory, revert the five
`App.tsx` lines, `corepack pnpm --dir ui-v2 remove lightweight-charts`. Kept
for now only as the evidence behind this verdict.

**Whale/volume-anomaly layer** (operator's TradingView indicator, source read
2026-08-04): buy/sell volume split by close position in the bar's range
(`(close-low)/range × volume`), flagged at 3/4.5/6σ over a 5-bar rolling mean.
Fully reproducible from data we already cache — no tick data needed — and better
on futures than on the index, where volume is synthetic. Two caveats: it is not
real delta (close position ≠ aggression), and a 5-bar σ window makes it fire in
clusters. Score it as a **d3 co-condition**, pre-registered, before it draws.

## 7. Open work, in priority order

**Read `context/research-findings.md` first** — it holds every verdict, the
surviving rule in full, and the stop-rule below.

1. **Collect live triggers.** `trigger_log.py` is wired into `server.py`'s
   refresh loop and needs a **server restart** to activate. It records every
   band-rotation fire with the bar's gamma/ctx and the chain's OI strength —
   the two conditions the operator watches that the cache cannot test.
   `python trigger_log.py score` fills outcomes once the day is cached.
   ~20-25 signals settles both. **This is the only source of new evidence.**
2. **🛑 STOP re-cutting `data/backtest/`.** Seven consecutive negative or
   falsified tests outside NIFTY/SENSEX d3 (2026-08-03/04), and two mid-search
   "findings" that evaporated on the next dataset. More slices will manufacture
   a false positive. Any new hypothesis must be **pre-registered in
   `research-findings.md` before the run**. See §5 there.
3. **The 20-pt stop is a RISK decision owed by the operator** — it sits exactly
   at the typical adverse swing (−20.7). Deliberately not grid-searched.
4. **Capture weekly option legs forward.** Expired weeklies vanish from Dhan's
   scrip master, so this data is unrecoverable later. Needed for the premium
   sell-side test (the only expression never fairly tested) and for the
   two-leg confirm on the expiry the operator actually trades.
5. **Cross-check the leg pivots against Kite** — one session, five minutes.
6. **The `/api/contract` pair chart** — premium-matched pair across strikes
   with the two-leg `confirm`. Still unbuilt.
7. **UI/UX overhaul** (dual review 2026-08-03, consensus 5/10): boot into
   Trade, delete the 7 fossil tabs, ZONE READ → price ladder on the chart's own
   axis, real type/spacing system, keyboard. Detail in `ui-v2-dashboard.md`.
8. **SWEEP/FILL events** in `structure.py`; **SUPPORTS/AGAINST** tagging in
   ZONE READ (rules belong in the engine and must be scored first).

## 8. Decisions still owed by the operator — do not guess

**Still owed:** compression as context vs co-condition (`CONFIRMED`+`CLEAR` = 0
of 64; they describe different phases of a move) · the expiry-day rule · a
seller's stop and decay target · Setup B's expression · whether the ±1σ interior
is no-trade with the edges as the working zones. Three more sit in
`DEFERRED.md §0`.

**SETTLED 2026-08-05, corrected here 2026-08-13** — this list carried both of
these as open for eight days after they were answered, and `PRODUCT.md` copied
the stale version:

- **The 09:25 trigger gate.** `research-findings.md §5c` specifies "after
  **09:25**"; `band_rotation.ANCHOR_MINUTE` (line 228) is that minute and
  `run_states` branch 4 refuses to arm before it — and refuses to assume a bar
  with no readable clock is late enough.
- **Re-fire suppression on the same level.** §5c point 7: after an entry, if
  stopped out the next setup may arm immediately, otherwise not until VWAP is
  touched. `run_states` implements it as `lock`, cleared by stop or VWAP, and
  the bar that clears it may still arm the next setup within the same bar —
  which is why OUT is not one of the state words. `exit_why` is that clearing
  and **nothing else**; see the 2026-08-13 entry for where the UI still reads it
  as a trade exit.

## 9. Working agreement that has held up

- Honesty rules are load-bearing: *"we checked and found nothing"*, *"we could
  not check"*, and *"we are not showing you"* are three different sentences and
  must never collapse into one rendering. Every panel follows this.
- Never invent a level, a greek, or a pivot. An absence gets a reason.
- Score before trusting. The one hypothesis that got that treatment died — which
  is the argument for doing it more, not less.
- Answer the operator's trading questions straight; no "not a licensed advisor"
  deflection.
- Ship a thin visible slice early. Weeks of backend-only work landed with
  nothing on their screen, and the chart they finally saw was unreadable.
