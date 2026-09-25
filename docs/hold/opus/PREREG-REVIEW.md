# Review of `docs/hold/PREREG-merged.md` (Opus)

Written 2026-09-25 01:03 IST (clock). I read the registration line by line. Then I
implemented its §3 and §4 **literally**, as a probe
(`scratch/xreview/prereg_probe.js`), to see how the rules interact.

The probe runs on the same four frozen days. It checks the **text**, not the
market. Where the text can be read two ways, I ran both readings.

## Verdict

**Close, and the right design, but not registrable as written.**

- It matches the merged design and both of her decisions:
  - the quiet clock is a FOLD;
  - buyers and writers are registered together.
- Every parameter is inherited or was fixed before replay.
- **Five defects must be fixed before it is signed.** Two of them change verdicts
  on her own rows. Seven smaller points should also be fixed.
- Nothing in it is a hidden score. It never gives a probability, a size or a
  price.

## Does it match what she decided and what was merged?

| item | in the text | verdict |
|---|---|---|
| Fable's window as the base (quiet face, the line and its room, Document PiP) | §2, §5 | ✓ |
| Opus's OI read: the nearer of the top 2, folds as events, "both sides leaving" said out loud | §2 | ✓ |
| the quiet clock is a **FOLD** (her call) | rule 3.5 | ✓, and the cost she accepted is recorded in the hazards |
| buyer and writer registered **together** | §4, §7 as two populations | ✓, but see M2 |
| a lone CVD divergence or a lone print never counts | §2, strict flow via `board.aggression` | ✓, but see S2 |
| PATA NAHI when blind; "structure only" instead of a plain HOLD with OI blind | rule 3.1 | ✓, but see M1 |
| the entry check says "you entered into a broken setup" | §3 | ✓ in wording. See M5 for the example |
| the holders' fold kept at WATCH, the 09-24 dilemma stated as unsolved | §2, §9.1 | ✓, honest |

## Must fix before signing

**M1. Rule order breaks the latch.**
- Rule 3.1 (PATA NAHI when the line is blind) comes **before** rule 3.2 (FOLD,
  latched).
- So a minute without an index candle, after a FOLD, would show PATA NAHI and
  then FOLD again: the flip-flop the latch exists to prevent.
- It is latent on these four days: no candle was missing after a FOLD. It will
  happen on the first REST gap.
- **Fix:** the latch first, then PATA NAHI.

**M2. The writer's OI can never fold her.**
- §4 says that for a writer, "payers adding … is **not** a WATCH". Read
  literally, payers-against then counts nowhere for a writer, so:
  - **rule 3.4** (positioning flipped = payers against AND holders against)
    can never fire for a writer;
  - **rule 3.6's OI family** is "payers against" only, so it can never be
    against for a writer either.
- A writer can then FOLD only on the line, or on FLOW plus TREND. Her own side
  being squeezed, her doctrine's core, reaches WATCH at most.
- The probe, reading it literally:
  - the 09-24 short ATM PE sold against the trend (09:44, @182.6) folds at
    **10:17, −26.3**, on the line;
  - read the other way (payers adding is not a WATCH **on its own**, but still
    counts in 3.4 and 3.6), it folds **at entry, 0.0**, and it later expired at
    619.9.
  - The with-trend short CE: 10:52 on the line (−38.3) literally, 10:43 (−3.5)
    the other way.
- **Fix:** say so explicitly. For a writer, "payers adding" is not a WATCH by
  itself, but it **is** her OI family's "against" in 3.4 and 3.6, together with
  the own-side squeeze clause. W2 ("a short against the trend gets FOLD within
  15 minutes") **fails on its own example** under the literal reading.

**M3. Which minutes the quiet clock counts is undefined, and it decides the 09-24
afternoon.**
- "Minutes the window could not read do not count as unpaid" leaves two cases
  open:
  - **(a)** is a minute with OI blind "readable" when the line reads?
  - **(b)** is a **both-sides-leaving** minute (OI "cannot say which way", by
    rule) a readable, unpaid minute?
- The probe ran both answers to (b) for the 09-24 13:26–13:57 puts:
  - counted as unpaid, the clock folds all six at **14:08–14:10**, before the
    14:24 low. Premium at the FOLD: +204.9 / +129.2 / +112.6 / +88.8 / +40.3 /
    −11.3 points from their entries;
  - not counted, they ride to the line at **14:35**: +176.9 / +95.9 / +79.3 /
    +55.4 / +8.4 / −47.9.
  - On this day the literal reading was better. That is exactly §9.1's own
    observation ("the payers' side had gone quiet").
- **Fix:** register one answer explicitly for (a) and for (b). I would count
  both-leaving minutes, because that matches §9.1 and her "nothing is paying"
  intent. But it must be decided **now**, not read off the rows later.

**M4. The falsifier cannot be computed as written.**
1. **Units.**
   - "After FOLD" has to mean the **first FOLD stamp of each trade**. Latched
     minutes after it are not new events, and would swamp the count.
   - "HOLD · noise" minutes are strongly autocorrelated. Use the **first**
     noise minute per trade, or per 15-minute block.
2. **"On trend days FOLD fires on the majority of in-trade minutes."**
   - Latched, this is true of any trade that folds early. It has to be the
     **unlatched** state, as Fable's own report used it.
   - **"Trend day" has to be defined before the data.** I suggest the price
     rows: 5m, 15m and 1h all one way for at least half the session. Otherwise
     it is a post-hoc label.
3. **Her quiet-clock FOLD has no kill clause of its own.** Add: if "reason gone"
   stamps are followed by larger favourable excursions than HOLD · noise
   stamps, the clock reverts to WATCH. It is the one rule chosen by preference,
   not evidence, so it needs its own exit.
4. **No time bound.**
   - "≥ 15 stamps" with no session limit means a rarely-used population (writers
     on this account) can never be killed. Add a bound, such as grounds' 30
     sessions: inconclusive at 30 sessions = not signed live.
   - Also say what the window shows until then: DRAFT.
5. **B1** ("first FOLD late in the leg … not on a holders' fold") cannot fail on
   its second half, because a holders' fold cannot FOLD under this registration.
   Drop that half, or turn it into a count of WATCH stamps.

**M5. The entry-check example contradicts the rules.**
- The example sentence reads "the reason was already gone at 13:39, because CE
  74,200 folded at spot and put writers were adding in its way". That is Opus's
  rule 3A, which this registration **removes**: a holders' fold is WATCH-only.
- Under these rules a FOLD at entry can only come from rule 3.4 or 3.6. (The
  line is set beyond price at entry, and the clock starts at entry.)
- **Fix:** replace the example with one this map can produce. The probe found
  two: 09-22 09:42 and 09-23 09:47, both "two families against".

## Should fix

**S1. The writer clause was created after data, and W1 cannot see the known
failure.**
- §4's own-side clause is Fable RULES §10 G, proposed after seeing the 09-24
  with-trend short CE. The header's "neither was moved after data" is true.
  "Designed after seeing one writer row" should be said too, and W1 judged on
  forward rows only.
- More importantly, the known writer failure came from **the line** (a 29-point
  break with 16 points of room), not from OI. W1 ("not folded by an own-side
  unwind") would pass while the writer still gets folded by the line. §9.2 says
  so, but the prediction should test the whole window: "not folded **at all**
  while spot moves away from her strike".

**S2. Strict flow on a thin ladder is a dead family.**
- "CVD strong AND prints dominant" had a side on these minutes (of 355 readable):
  - SENSEX 09-23: **0**;
  - SENSEX 09-24: 33;
  - NIFTY: 79 on 09-23 and 164 on 09-24.
- On SENSEX, FLOW is therefore flat almost all day. Three consequences:
  - rule 3.6 is OI + TREND only;
  - the quiet clock is an OI-only clock;
  - "flow with her" almost never pays.
- That is a property of the index's feed, not of the market. **Register the
  choice:** thin prints are flat (as written), or "could not check — too thin
  to read" (`board.aggression`'s own sentence). The words must say which.

**S3. Fold liveness.** "Kept while `board.still_folded` holds and for 15 minutes
after the stamp" reads as either AND or OR. Both prototypes used **AND**: within
15 minutes **and** still folded. Write "and".

**S4.** "THE LINE [M] — never blind" contradicts "no index candle at `t` → the
line is blind". Keep the second.

**S5. Selection bias in the forward log.**
- Only trades she marks get rows. She will remember to mark some and not
  others.
- Since every read is causal and REST-exact (the anytime-start rule), add an
  **end-of-day import of the tradebook** through the same route. Every trade is
  then logged, not only the remembered ones. Mark imported rows as `src: import`.

**S6.** "Printed at the head of the window for the trade's first minutes": say
how many. I suggest until the first 5-minute ladder bar closes after entry, or
3 minutes.

**S7. Clock provenance.**
- Fable's RULES §10 carries "2026-09-25 01:50" on an entry the files show was
  written earlier.
- My RULES §9 had the same kind of estimated times. Corrected, and admitted in
  my RULES §9.
- The registration should carry a time **read from the clock**, and the
  commit's time is the proof.

## Are the parameters principled?

**Yes.** Every number is inherited:
- from §1d: NEAR, TOP, UNWIND, STALL, SLOPE, STALE_MIN;
- from grounds: W, STRONG, ONE_SIDED, dominance;
- from trendbox: PIV, N, the rows;
- from `board.nearer` and `board.aggression`.

Three choices were fixed in a RULES file before any replay:
- **buffer 0** and **2 of 3**: Fable RULES §2.1 and §3;
- **15 readable minutes**: Opus RULES §8.

The quiet clock as a FOLD is her decision, and it is recorded with its known
cost. **The one post-data element is the writer clause (S1).** No parameter was
moved after data.

## Would the falsifier kill it if it were wrong?

**Once M4 is fixed, yes, for buyers.** "HOLD · noise is followed by larger
favourable excursions than FOLD, per trade, forward, ≥ 15 each" is the right test
of a window whose whole job is to separate noise from a break. The entry-minute
and trend-day clauses stop it from passing by folding everything, and the
drop-the-best-day clause stops one day from carrying it.

**For writers, not yet.** Two reasons:
- under the literal §4 a writer's OI cannot fold her (M2), so a broken writer
  rule would look quiet rather than wrong;
- writers will take months to reach 15 stamps on this account.

W2 has to be judged on what the rules can actually do, and the time bound in
M4.4 has to apply.

## Is the writer side right?

- **Right:**
  - her own side labelled "your side";
  - no quiet clock (time pays the writer);
  - payers adding is not a WATCH on its own;
  - the danger-side line with its room;
  - two separate populations.
- **Not yet right:** M2 (payers-against missing from 3.4 and 3.6), and S1 (the
  line is the actual cause of the known writer failure, with no writer-specific
  room clause). §9.2 leaves the room clause to her, which is correct. But until
  she registers one, **the prediction W1 must include the line.**

## Does the entry check say "you entered into a broken setup" clearly?

**Yes, in wording.** "You entered into a broken setup — the reason was already
gone at HH:MM, because <fact>" is the sentence she asked for. The WATCH and HOLD
entry lines are good.

Two notes:
1. **The example is impossible under the rules (M5).**
2. **Under this map, a broken setup at entry is rare.**
   - The probe found 2 of her 28 readable entries.
   - Her worst 09-23 re-entry (10:00, −₹507) is **"entered into WATCH"**, and it
     folds at 10:05.
   - That is honest. The better-trade read (`BETTER-RULES.md` §7, a separate
     registration) is what says "you are a buyer on a writers' day" at that
     minute. The two together answer her "have I entered into the wrong trade
     already".
