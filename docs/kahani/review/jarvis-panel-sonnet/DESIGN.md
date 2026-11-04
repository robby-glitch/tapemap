# Jarvis right panel: two directions

Mockup: `panel-mockup.html` (double-click; light; no dependencies). Data: `calls_3nov.json`, the five 3 Nov moments, nothing invented. Both directions are shown at 350 px (330 and 360 also work) at 590 px high (1366x768 laptop) or 700 px (1440x900).

## What both directions share, and why

The three complaints all sit in one place: the nine reads and their words. So both directions keep the same shell and differ only in how the nine reads are drawn.

1. **One freshness strip, always the top 30 px, plus a coloured left edge.** It is the only place that says how fresh the page is, and its colour is readable in peripheral vision:
   - LIVE (green, pulsing dot): "read 12:12 · 18s ago · next 0:42", with a 60-second progress hairline.
   - REPLAY (violet, dashed frame): "3 Nov · read 12:12 · recorded, not today". No pulse and no countdown.
   - STALE (red): "26 MIN OLD · last read 14:04 · now 14:30:07". The minutes keep counting.
   - NO FRAME YET (grey): "08:50:24 · opens 09:15 · in 24:36".
2. **Answer first:** the call word, its state pill, since-time, and one number line (`LEG ▲ 214 pts · 2.3σ   23,533f → 23,747f`).
3. **Four states, never three.** Every read is one of four, and each has its own shape, colour and Hinglish gloss:
   - ✓ **with** the call (green, solid);
   - ✕ **against** the call (red, solid);
   - ○ **flat**: checked, found nothing (grey, plain, "dekha, kuch nahi");
   - ? **blind**: could not check (amber, hatched, dashed edge, "dekh nahi paaye").

   A fifth look, plain dashed grey, means "not shown on purpose" (stale or pre-open). That makes CLAUDE.md rule 6 literal: found nothing, could not check and not showing you never look alike.
4. **Plan rows:** BUY CE / SELL PE (mirrored when the lean is down), one line of at most six words, then fact chips. Every level carries `s` or `f`. Inferred numbers carry a small `I`. A blind fact ("needs ?", "IV ?", "fold ?") uses the same amber hatch as a blind read. One `ENDS` line sits under them.
5. **Bottom bar:** READS (with an amber `?n` badge when something is blind), MORE, STREAM (blue badge = events since the last moment), ⌘.
6. **The sheet:** one tap on any lamp, count, or bar button slides up a 330 px sheet over the lower half. It keeps the strip and the call visible.
   - READS lists all nine engine sentences verbatim, grouped as with / against / flat / blind. Each group header says in words what it means, so "what 6 could not check" is answered where she asks it.
   - MORE holds the verbatim leg, pause, day, buyer, seller and ends sentences. It ends with "engine sent nothing for: how much · no-trade · self · missing".
   - STREAM and the command box live here too.

The classifier behind the 4 states is deliberately dumb: a "?" is *blind* only if the engine's text starts with "could not check", else *flat*. At 09:29 it gives 4 flat + 1 blind, which is what you found by hand. The mockup checks itself against the engine's own with / against / unread counts at load.

## Direction A, LAMPS (recommended)

**Principle:** nine fixed slots, same place every minute, so she learns the board and reads it as a picture. All numbers on screen, almost no sentences.

- Four count cells double as the legend (`✓ 3 with ▲ · ✕ 1 against ▲ · ○ 4 flat · ? 1 blind`). Under them, a single legend line appears only for the states present (`flat = dekha, kuch nahi · blind = dekh nahi paaye`).
- Each lamp is name, the one number that matters, and a Hinglish chip (`PE likh rahe`, `deewar ghat rahi`, `phanse`, `30m OI chahiye`). A blue dot marks "changed since the previous moment".
- **Removes:** the eight to ten one-line sentences, the "WITH n · AGAINST m · k could not check" line, the grey "?" row, and the LAST TRIGGER box (it is the ZONE lamp).

## Direction B, SCALE (alternative)

**Principle:** show only what takes a side, count the rest. A 9-pip beam (`against | flat | with`, with blind set apart because it is not on the opinion axis), two columns of chips, then one shelf for flat (names only) and one for blind (the engine's reason inline).

- Strength: lopsidedness is visible at once. 7 | 0 on 13:20 and 0 | 4 on 10:11 read before any number does, and the blind reason needs no tap.
- Weakness: positions move, so there is no board to memorise. It is taller on a 7-with day (the middle band scrolls by 2 px at 330 px / 590 px).
- **Removes:** the same as A, plus the fixed grid.

## The three complaints

- **Cramped:** the right panel goes from about 12 text rows (most clipped with "…") to 5 always-visible zones with 3 text-ish rows. All the sentences still exist behind READS and MORE, one tap away. Nothing needs "…" any more: the sweep found no clipped text and no wrapped fact rows at 330 / 350 / 360 px.
- **Not live:** the strip carries age, a countdown to the next read and a pulse, so a quiet minute still moves. Live, replay, stale and waiting each have a different strip colour and frame edge. In STALE the plan and evidence are hidden, not greyed, because a 26-minute-old "AGAINST 2" is more dangerous than no number.
- **"Could not check":** it is split into flat and blind everywhere (count, lamp, legend, sheet, plan facts). The words are Hinglish and plain: "dekha, kuch nahi" versus "dekh nahi paaye".

## Where today's rows went

| Today | Now |
|---|---|
| THE CALL word + state + since | always visible (call card) |
| "at HH:MM" | the strip: "read 12:12 · 18s ago" |
| WITH · AGAINST · "k could not check" | the 4-count; the sentence sits in READS |
| the nine piece sentences / "?" row | lamps (A) or chips + shelves (B); verbatim in READS |
| leg | one number line on the call; the full sentence in MORE |
| pause, day, how much | MORE |
| buyer / seller | always visible as BUY / SELL rows (six words + chips); full text in MORE |
| "ends:" | always visible as ENDS (short); full text in MORE |
| LAST TRIGGER box | gone; it is the ZONE lamp. The static "d2→d3 buy · u2→u3 sell" line is gone. |
| no-trade | when present, a full-width band replaces the BUY / SELL rows (not in these five moments) |
| missing | merged into the blind count and the blind lamps |
| self, notes | MORE (self) or disappear (notes) when null |
| event stream | STREAM sheet with an unread badge |
| command box | ⌘ sheet; disabled with "commands are off in replay" |
| demo text | gone from the panel. The page header must be fed from the same mode and frame state. |

## What I am least sure of

1. **The engine has to emit the state.** The glance forms (big number, six-word plan, short ENDS, Hinglish chips) are hand-written here. In production the engine should send `state: with | against | flat | blind` and a short `why` per piece, plus the short plan / ends fields. Parsing "could not check" is a stand-in.
2. **Edge cases I classified by reading.**
   - "no 30-min story" counts as flat, since 30 minutes exist by 12:12.
   - "TRAPPED: Sides … reads under water on its fuel side only" counts as blind, since the engine itself says "could not check". It is really "partial", which may deserve its own wording.
   - "writers ±7 RISK … PE −202L" is a flat tile carrying the loudest number on the page. A flat read can be alarming. I kept the engine's vote and did not re-judge it.
3. **Hiding the plan when stale.** I hid it. She may want the last stop level kept visible in grey with its age. I did not show it because the 14:04 frame is not in the data file, and I would not invent it.
4. **Hinglish chips** (`teeno neeche`, `likhna ruka`, `ek side hi dikhi`) are my phrasing of her vocabulary. She should rewrite any that are off.
5. **Live feel is simulated.** The age counter loops every 60 seconds in the mock. A real feed needs a "late" amber step between live and stale (for example older than 90 s). I did not pick the thresholds.
6. **Tap on a touch-less laptop.** Everything is one click, but she may prefer keyboard keys for READS and STREAM. Left and right arrows already step the moments in the mock.
