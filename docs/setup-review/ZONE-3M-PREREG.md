# PRE-REGISTERED (SIGNED 2026-10-26 18:13): ZONE-3M, the zone on her chart's 3-minute bands (UNTESTED)

## Origin (verbatim)
- **Mary, 26 Oct ~14:50**, with her chart's screenshot: "and how you saying that it didnt touch the lower band look it
  clearly touched i have attached the screenshot"
- **Mary, 26 Oct 15:08:** "Yes, reopen my 15 Aug call: compute the zone machine's bands on 3-minute bars like my chart,
  as a new registration starting from a date you name. Plan it after close."
- **What it reopens:** research-findings §1c, 15 Aug: "thats not required the difference is small we can manage with
  out it." That was measured mid and late session ("bounded at ~5 pts at 3σ").
- **Her anchor rule** (`band_rotation.py:220`): "by 9:25 we have the values for vwap standard deviation and from there
  we judge wheather they are expanding or narrowing."
- **26 Oct is in-sample:** it motivated this registration.

## The rule: only the bands change
1. **BARS.** Each index's near-month futures 3-min bars on the 09:15 grid, folded from the exchange's 1-min candles
   (`contract_bars.resample_index`). These are the bars the zone machine already reads.
2. **BANDS.** VWAP and σ are computed **on those 3-min bars**: hlc3 × volume from the session's first bar (09:15),
   through the tape's own recurrence (`contract_bars._Vwap`, via `vwap_sigma`).
   - d1/d2/d3 = VWAP − 1/2/3σ; u1/u2/u3 = VWAP + 1/2/3σ.
   - Each is the bar's own value at its close.
   - The zone in use until now reads the last 1-min bar's bands (1-min σ, "interval invariance"). This is the only
     change.
3. **ARM, unchanged from §1b.** BUY when a bar's low ≤ its d2; SELL when a bar's high ≥ its u2.
4. **THE 09:25 ANCHOR, read on the bar's close.**
   - A bar is eligible when it holds a minute at or after 09:25 (its label + 3 min > 09:25).
   - On the 3-min grid the first eligible bar is the 09:24 bar. It closes at 09:27, and its bands are computed at
     09:27, so "by 9:25 we have the values".
   - The rule in use until now reads the label, so the 09:24 bar never counted.
5. **Unchanged, exactly as `band_rotation.run_states` runs today:**
   - the entry: a later close beyond the arm bar's high (BUY) or low (SELL);
   - the re-arm on a new extreme, and the 10-bar window;
   - the stop at the armed band level ∓ 20 pts (`OPERATOR_STOP_PTS`);
   - the re-fire lock (stop or VWAP).

## Populations (CLAUDE.md rule 5: never pooled)
- **New rows:** trigger_log `rule: "zone3"` (arm rows `kind: "arm"`, and entries), with `bands_on: "3m"`. (`bands` is
  already the scorer's outcome field.)
  - From **Wed 28 Oct 2026, 09:15**: the first session on the November future (27 Oct is NIFTY's monthly expiry and
    the roll).
  - **One switch, one date:** before 28 Oct nothing zone3 is logged, shown as a chip, marked on the Trade tab or sent
    to Telegram, so every zone3 alert she acts on is also in the record.
- **The 1-min zone (`rule: "zone"`, §1b)** keeps running and logging exactly as before, beside it. FADE §1i
  (CONFLUENCE-PREREG, hash-checked) keeps reading it. Its record is not touched.
- **Unchanged, on 1-min bands:**
  - 5c (`rule: "5c"`, d3/u3; its 68.4 % on n = 19 was measured on sampled 1-min bands);
  - `rotation`, the trap width, the engine's ctx/plays and the §1d veto;
  - Validate's pick;
  - the Signals ballot's arms.
- **Scoring:** separate, never with `zone` rows. No hit rate is printed (rule 4); the pass bar is hers to state before
  reading (§5e); under 15 per side is inconclusive.

## What she sees (display only)
- **Trade tab at 3-min:** the band lines, the d2→d3 / u2→u3 pockets and the zone's arm and entry markers are the 3-min
  machine's, her chart's, so a pocket touch and its marker never disagree.
- **A zone3 entry** is a `ZONE` chip in DECODE's setups and one SETUP line on the stream and Telegram, with its own entry
  and stop (A108), e.g. `09:30  NIFTY  ZONE BUY · … · E …s|22,534f · stop …s|22,425f`.
- **An arm** shows on the chip as ARMED and is never sent to Telegram.

## Known differences from her chart [M], reported, never tuned silently
- **research-findings §1c** (15 Aug, one day): 3-min-bar σ was within 0.1–0.3 % of Kite's after 13:45 but 8.6 % off at
  10:30; VWAP was 1.83 pts out (a volume mismatch is suspected). A calibration against her chart on two sessions is owed.
- **GoCharting's bands** (the extension's) are on the chart's own bars: 5-min on a 5m chart, a different interval.
  ZONE-3M is 3-min (rule 3: "3-minute is canonical").

## Acceptance (26 Oct NIFTY, in-sample, described only)
- **ZONE-3M,** on the exchange's 1-min candles folded to 3-min:
  - **BUY arm** at the 09:24 bar: low 22,440.0 ≤ d2 22,445.1;
  - **entry** at the 09:27 bar's close, 22,534.1, above the arm bar's high of 22,480.0;
  - **stop** 22,425.1.
- **The 1-min-σ zone** armed nothing there: its d2 at that bar was 22,434.1.

## Signature
**SIGNED by Mary, 26 Oct 2026 18:13, verbatim:** "commit — I sign ZONE-3M as written. Build it tonight, commit locally,
don't push."
- Anchored in research-findings §1r: the sha256 of this file as signed.
- Effective Wed 28 Oct 2026, 09:15.
