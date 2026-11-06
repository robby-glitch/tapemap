# Jarvis market state: trend memory, volatility state and the zone card (design, 6 Nov 2026)

**Status:** DRAFT for Mary's review. Nothing is built.

**Her words (6 Nov):**
- "it should know if markets are forming hh hl lh ll, we are in trend or not";
- "market top and bottom is going to be in these bands … small stoplosses, big trade";
- "yes this it … jarvis should be able to see all this".

**Evidence:**
- docs/kahani/review/JARVIS-DAY-2026-11-05.md (Jarvis 5/10: 23 SENSEX word changes, PALAT? at the 14:24 pullback low);
- NOTEPAD section B, 2026-11-05 (her zone rule; the 72 zone3 rows from 28 Oct to 5 Nov).

## 1. The problem in one line
Jarvis re-votes 9 pieces every minute and remembers one leg. So one quiet minute can flip the word, and its raw zone trigger
votes against a trend the writers back. A trader carries the day's story, and reads her zone as a location that the
market's state makes legal or not.

## 2. The four layers (approved in conversation, 6 Nov)

| Layer | Question | Decides | Changes only when |
|---|---|---|---|
| **1. Market state** (per index, with memory) | Trend or range? Expanding or contracting? | TREND ▲ / TREND ▼ / RANGE, and EXPANDING / CONTRACTING | Structure breaks or writers flip (trend); several bars confirm (volatility) |
| **2. Legal trades** | Which zone trades does this state allow, and as buy or sell? | the legality table (§5) | Layer 1 changes |
| **3. Her zone** (§1b, locked, unchanged) | Where? | u2–u3 / d2–d3 location; stop beyond the trigger candle; target VWAP, then the next band | the zone machine |
| **4. Signs at the zone** | Strong, take-smaller, or skip? | a COUNT of the signs present (never a %) | every 3-min close at the band |

The **state word leads the screen**. The zone card sits under it. Zone triggers **never vote** in the trend count again.

## 3. Layer 1a: trend memory (structure is the skeleton)

**Swings:**
- 3-minute closes on the frame's price (§1q: SENSEX on spot, with NIFTY's flow).
- Reversal size: the existing `decode.py` sizing (max of 50 NIFTY-equivalent points, 0.5 × the IV-priced 30-min sigma) [I].
- An **ordered day list** of pivots, each with its time and price: HH, HL, LH, LL.

**Reuse:**
- `reader.py`'s auction already keeps `ext` (the trend extreme) and `ctr` (the last HL or LH), and breaks live below the last HL (`reader.py:802-852`).
- Run it on Jarvis's frame. Don't write a fourth leg engine; that was the 31 Oct review, P0 #4.

**States:**
- **TREND ▲** starts when a prior swing high breaks **and** the next pullback holds above the last HL. TREND ▼ mirrors it.
- **RANGE** is everything else: overlapping swings.
- **A trend ends** (the first of these):
  - **structure:** a 3-min close beyond the defining HL (or LH) by more than one median 1-min candle. That is her §1e close rule;
  - **writers flip:** her §1m "gave up". The front is UNWINDING and price is on the writers' losing side by 0.25U. Otherwise it is "munafa booking", not a turn.
- Nothing else ends a trend. Flow, effort, VPIN and the 9 pieces **grade** it as healthy / tired / blind. They never flip it.

**Efficiency** (net move ÷ path over the last 45 min [I]):
- Shown beside the state.
- It helps call RANGE when structure is ambiguous: low efficiency plus repeated VWAP returns.

**Cross-index tiebreak:**
- All three indices in the same state plus writers covering in all three: **TREND DAY**.
- One index leading while the others don't follow: **ROTATION**, so fade the extremes.
- This uses `xindex.py` (X1, X4) plus the new writers-sync piece (§4).

**Unconfirmed trend:**
- A leg that qualifies under `legs.py` (TREND size, before or after 10:00), with no pullback yet, shows **TREND ▲ (leg, unconfirmed)**.
- It becomes **TREND ▲** once the first pullback holds above the last HL.
- On 5 Nov the engine had a qualifying leg at 09:44. So: no more silent OPENING over a +439 drive.
- The opening's zone touches stay out (§5).

## 4. Layer 1b: volatility state and the big-move warning

| Gauge | Source | Status |
|---|---|---|
| 3-min bar range vs the median for the **same time of day** over the last 10 sessions | futures / spot bars on the record | to build [I] |
| ATM straddle: decaying, or rising while spot moves (net of time decay) | chain record, every minute (ATM CE + PE LTP) | exists, to derive |
| India VIX: change over 15 min | `vix_log.py`, `data/vix/` (live since 4 Nov) | exists |
| IV at ATM | chain record `iv` | exists |
| RAFTAAR: one-sided covering speed | `handshake.py`, ±7 writer flow | exists |

- **EXPANDING** needs 2 of the gauges above for 2 consecutive 3-min closes [I]. **CONTRACTING** needs 2 of them below.
- **Writers-sync (new):** the call (or put) front UNWINDING in ≥2 of the 3 indices within 5 min. Today `all3` checks price only, and its SENSEX "N" slot reads the frame's own future. Fix that while here.
- **COIL → ESCAPE warning (display only):** compression (contracting, both sides adding near ATM), then one side's writers running in ≥2 indices. Wording: "box ban gaya, writers bhaag rahe — bada move ho sakta hai".
  - **Guardrail, from the 27 Oct coil study (docs/speed/coil/BRAINSTORM.md):** a coil before a blast is the minority case (6 of 24 legs); "OI up = writers" is wrong about half the time near ATM in a fast move.
  - So the warning is never a prediction, never a gate, and who opened the move uses premium vs delta.
- **0 DTE mode:** on expiry day after 14:00 the state shows "EXPIRY: gamma both ways". After 15:00 premium beats trend, so the card reads "no hold for the close". Her no-trades-after-15:00 reminder stays display only.

## 5. Layer 2: which zone trades the state makes legal

| State | Zone trades allowed | Expression (both ways) |
|---|---|---|
| TREND + EXPANDING | **with-trend pullback band**; a top fade **only when the band has stopped expanding AND the writers at it are holding** (amended 6 Nov from her words: "if expanding … not a trigger, but if market reverses from there, absolutely I take it"), target VWAP only | buy the trend side |
| TREND + CONTRACTING | pullback bands; **top fades only when the tired signs show**, target VWAP only, trend word unchanged | buy pullbacks; a fade may be a sell |
| RANGE + CONTRACTING | both bands, band to band | sell premium at the edges |
| RANGE + EXPANDING | stand aside | — |
| before 09:45, or 0 DTE after 15:00 | none (shown greyed, with the reason) | — |

## 6. Layer 4: signs at the zone (a count, never a %)

These signs are counted at the band, on the trigger's 3-min close:
1. The band stopped expanding, and the candle rejected it (wick, close back inside).
2. Writers **at that band's strike** are holding or adding. This is the wall being defended, not a strike that gave up hours ago.
3. Effort without result: big delta, small move (`effort.py`, the one flow read that survived oi-lab), or CVD stalled.
4. Sync broke: one index makes the new extreme and the others don't.
5. A mature leg: a later push of the day, far from VWAP.

The card reads:
- **STRONG:** a with-trend band plus writers behind.
- **TAKE · smaller target:** a counter-trend fade with N of 5 signs.
- **SKIP:** with the reason.

It always shows the stop (beyond the trigger candle) and the target (VWAP, then the next band).

### 6a. Managing an open zone trade (added 6 Nov from her 09:57 → 10:33 NIFTY sells; display only, she decides)

**WIDEN** (one chip on the open card):
- When it shows: price is approaching the trigger-candle stop **slowly and weakly**. That means at least 6 min [I] without crossing it, plus sign 2 (the writers at the band not leaving) or sign 3 (effort without result) still true.
- What it says: "stop → beyond u3 {level}". The trend state must not be EXPANDING against the trade.
- When it is hidden: if the stop was reached fast, or the writers at the band are leaving. In that case the card says "stop hua — yeh trade nahi tha".

**ADD** (once per leg):
- When it shows: a second same-side zone3 trigger in the same leg while the first is open and the WIDEN line still stands.
- What it shows: "ADD 1 · avg {price} · stop beyond u3 {level}".

**Hard line:**
- A 3-min close beyond u3 ends both lots.
- There is no third adjustment, and no ADD after a WIDEN that has been broken.

**Target:** VWAP for both lots, then the next band.

**Data:** u3 and VWAP must be logged on every zone3 row. Today they are not (`bands: null`, 6 Nov), so this is the first build item of §6a.

**Honesty:** this enlarges the risk of a small, defined loss. The card shows the combined risk to the u3 line in points. It never shows a % and never claims an edge.

**Her gate (§1d fade gate):** today it cites a stale strike ("24500 / 78800 gave up") for the rest of the day. On 5 Nov that blocked all five top-band sells: +64 to +185 pts to the pullback [M]. Making it read the wall **at the band being touched** changes how her registered rule is applied. **This is hers to sign as a new registration.** Until she signs, the card shows both the current gate and the at-band read, side by side.

## 7. The screen (light mode, terminal grammar, Hinglish chips with numbers)

The mockup below shows the layout only. Its stop, target, efficiency and VWAP numbers are made up, not from the record.

```
SENSEX  TREND ▲ · EXPANDING        since 12:26 · line 78,858 (HL 10:55) · eff 0.62 · 3 idx in sync
        fuel: call writers 79000 running · flow light on dips        [Hinglish chips per symbol]
ZONE    d2 79,250 · TAKE (STRONG) · stop 79,190 · target VWAP 79,330 → u2
ALERT   —                                                        (COIL → ESCAPE when it fires)
```

- One word per index. It changes only on the §3 break rules, and the change is spoken by the voice word first.
- WATCH / PALAT? become chips under the word, never the word itself.
- HOLD with nothing voting for it is not allowed. It reads "TREND ▲ · fuel blind".
- **BANKNIFTY gets rows.** On 5 Nov it had none.

## 8. Rules this design keeps
- **No order path.** Display only.
- **No %, win rate or confidence.** Counts of signs only.
- **Every threshold [I]** in `jarvis_thresholds.json`, each with a NOTEPAD line.
- **§1b–§1s untouched.** The gate change is a separate registration she signs.
- **Anytime-start:** the state is rebuilt causally from 09:15 bars on any start. Backfilled rows are tagged `src: backfill` and never pooled with observed rows. A missing input says "could not check" plus the reason, never a zero.
- **SENSEX:** NIFTY's flow, its own OI (§1q). The A247 chain-window fix (committed 5 Nov) must be live for SENSEX writers above 78,900.

## 9. How we know it works (behaviour checks, not an edge test)

Replay the new layers over 28 Oct–5 Nov with `voice_path`-style replay, never in market hours. Check that on 5 Nov:

| Check | Expected |
|---|---|
| 09:36–10:00 | Speaks TREND ▲ once the leg qualifies, not OPENING |
| 12:30 NIFTY u2 sell | SKIP (trend + expanding) |
| 13:51 / 14:09 sells | TAKE · smaller target **if** the band stopped and the writers at it held, else SKIP with the reason (the replay reports which; no expectation is forced) |
| 10:55 SENSEX d2 | TAKE (RANGE, band to band) or STRONG if a trend was confirmed; the state was RANGE at 10:55, so TAKE is the honest read. Also flag that this row was WRITTEN at 13:48 (late zone row) |
| 14:24 SENSEX | The word stays TREND ▲; at most a "pullback" chip |
| Word changes per index | Far fewer than 23. Report the count; no target number is set in advance |

After that, forward log `data/jarvis/state_<day>.jsonl`. Evening review only, never a gate.

## 10. Build order (each phase is one commit, on her word)
1. **State layer:** swings / trend memory on Jarvis's frame (reuse `reader.py`), efficiency, the volatility state; the state word leads; zone triggers stop voting.
2. **Zone card:** the legality table, the signs count, and stop/target from the trigger candle and VWAP.
3. **Cross-index:** writers-sync, the `all3` fix, the COIL → ESCAPE warning, BANKNIFTY rows, and 0 DTE mode.
4. **Gate at the band:** only after her signature.

## 11. Out of scope
- New setups or zone changes.
- Any order path.
- Tuning thresholds on the replay days beyond the [I] values above.
- The Claude voice key: separate, and hers.
