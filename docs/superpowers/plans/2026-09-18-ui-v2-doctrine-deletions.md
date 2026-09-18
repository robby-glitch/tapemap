# ui-v2 doctrine deletions — parked 2026-09-18, to do later

Mary accepted these when she chose `ui-v2` as the shell ("ok do that"), then parked them: "wait keep in a file will do it later". Nothing here is a build. All three are deletions.

## Why they matter

`toolb.html` was thrown out at 18/40 partly because a BULL/BEAR verdict rode the header of every screen. The same verdict is in `ui-v2` today, derived from the weakest input in the stack, and it is the first thing on the page.

## 1. The direction verdict

`ui-v2/src/data.ts:736-752` reads `ctx.breadth` — the string `engine.py:1004-1020` builds — and turns it into a direction:

    const direction = breadth.includes('BULL') ? 'BULLISH'
                    : breadth.includes('BEAR') ? 'BEARISH' : 'NEUTRAL'

That breadth sums four signs: futures z, ATM call premium change, ATM put premium change inverted, and the dealer regime lean. **Three of those four are the same fact** — the index moved — read through the index, its calls and its puts. Only the regime lean is independent. Its own author's comment records it printing STRONG BEAR while price sat above VWAP on a 53M put wall. The 2026-09-18 signal-layer spec ruled this verdict must not be ported, and the new `breadth` object was built with **no direction field at all**, so that no banner can be rendered from it.

On screen this surfaces as the red "BEARISH" chip and the narrative line, for example "MOVE SPENT — DOWN leg 23414 to 23347 was bought back (49% retraced)".

**Delete:** the `direction` derivation and every element that renders it. Keep the descriptive clauses that state what happened; drop the ones that say what it means.

## 2. Max pain, PCR and GEX as numbers with a verdict

Rendered in the header strip beside spot: `MAX PAIN 24000 · +140`, `GEX Negative · in book zone`, `PCR 0.82 · SQUEEZE Low`. The seller-desk doctrine excludes aggregate OI, PCR and max pain **as signals**. Max pain may survive as a grey level tick on a price axis — the War tab already draws it that way — never as a number with a delta and a word.

**Delete:** the three header chips. The War tab keeps max pain as a level.

## 3. The chain-stale banner's blast radius

The banner reads: "CHAIN STALE — last option-chain snapshot 15:29:55 (12m old). Max pain, GEX, PCR and the chain-derived chart levels below are from that moment, not now." The sentence is honest and should stay. But once (2) is done, two thirds of what it warns about no longer exists, so it should be rewritten to name only what remains.

## Acceptance

Nothing in `ui-v2` prints a direction word, a PCR, a GEX verdict or a max-pain delta. Grep `src/` for BULLISH, BEARISH, NEUTRAL, pcr, gex and maxPain, and confirm each remaining hit is a level tick or a field name, never a rendered verdict. All 13 tabs still build and render.

Related memory notes: `toolb-critique-and-new-desk-decision`, `seller-desk-doctrine`, `signal-layer-built`, `operator-desk-design`.
