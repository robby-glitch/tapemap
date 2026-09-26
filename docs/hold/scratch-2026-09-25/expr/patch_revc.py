# Applies REVISION c's rule-text edits to the draft (absolute path). Every replacement must match exactly once.
# Nothing else in the repo is touched. §D, §H and §G's post-run lines are written after the run, not here.
P = r"C:\Users\kaam\Desktop\operator mode\tapemap\docs\hold\EXPRESSION-PREREG-DRAFT.md"
s = open(P, encoding="utf-8").read()
T = "14:37"


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


# ---- title and header
rep("REVISION b (rev 0 written 2026-09-26 00:16 IST; rev a 01:25; rev b written 01:47 IST by the clock, before its run; NOT SIGNED, UNTESTED)",
    f"REVISION c (rev 0 written 2026-09-26 00:16 IST; rev a 01:25; rev b 01:47; rev c written {T} IST by the clock, before its run; NOT SIGNED, UNTESTED)")
rep("""  - the word shows its margin: BUY / SELL, LEANS BUY / LEANS SELL, EITHER, STAND ASIDE (§A.4).

**Decisions""", f"""  - the word shows its margin: BUY / SELL, LEANS BUY / LEANS SELL, EITHER, STAND ASIDE (§A.4).
- **Rev c ({T})** registers two things, and is fingerprinted before its run (§D.0):
  - **Mary's answer to §C.7, NO:** on the sold option's expiry day a line break folds her as today, and the reach is not
    read (§C.7);
  - **one trader decision on the word:** a tie with one leg refused names the open leg as LEANS, by refusal (§A.4).
  - It also adds one descriptive log flag, `after_1500`, that gates nothing (§E.3), and discloses her current practice of
    trading nothing after 15:00, which is not a rule (§D).

**Decisions""")
rep("""- **rev b, after rev a's rows were seen:** the strike rule with rev 5 B's buffer; the word's strength shown as LEANS.
""", """- **rev b, after rev a's rows were seen:** the strike rule with rev 5 B's buffer; the word's strength shown as LEANS.
- **rev c, after rev b's rows were seen:** a tie with one leg refused names the open leg as LEANS, by refusal.
""")
rep("""**One decision is left to her, and asked as one yes/no question in §C.7:** does the reach apply on expiry day?""",
    """**Her one decision, §C.7, is answered** (2026-09-26): *"No, fold as today"*. On the sold option's expiry day the reach is
not read, and a line break folds her as today. **With it, §C is complete and can be signed.**""")
rep("""  - **rev 4 §2 / §3 rule 3**, with the reach, rule 3r and rule 3s;""",
    """  - **rev 4 §2 / §3 rule 3**, with the reach (off her option's expiry day only), rule 3r and rule 3s;""")

# ---- §A.4 the word
rep("""   - a tie: **STAND ASIDE · tie, selling refused**: "the facts tie {b}–{s}, and selling is refused: nothing leads to
     buying";""", """   - a tie (rev c): **LEANS BUY {CE|PE} · selling refused**: "the facts tie {b}–{s}; selling is refused, so the open leg
     is named, weakly";""")
rep("""4. **only BUY refused:** mirrored (SELL / LEANS SELL · buying refused; STAND ASIDE · tie; STAND ASIDE · led);""",
    """4. **only BUY refused:** mirrored (SELL / LEANS SELL · buying refused; a tie, LEANS SELL · buying refused; STAND ASIDE ·
   led);""")
rep("""**The tie with one leg refused is STAND ASIDE** (rev b).
- **Rev a named the open leg at a tie** ("BUY · selling refused" at b = s). The review singled that out as "the word to
  worry about".
- Under rev b's rule that the margin shows in the word, a tie cannot be EITHER when one leg is closed. The open leg leads by
  nothing, so the word is STAND ASIDE · tie.
- **This is the drafter's reading** of the decision "STAND ASIDE when refused". It is flagged in §G and §H for the trader to
  confirm.""", """**The tie with one leg refused names the open leg, as LEANS** (rev c, the trader's decision).
- **"STAND ASIDE when refused" means both legs refused.** When one expression is open and the facts tie, the word is LEANS
  {BUY|SELL} "· {other} refused".
- *Principle:* she has a direction and one expression is open. The word should say so, weakly and plainly, and not go
  silent.
- **It is named by refusal** (`named_by: "refusal"`, `strength: "leans"`, `lead: 0`). It is its own population: never pooled
  with LEANS on the count, and judged on its own (§E.2).
- **The history:** rev a named the open leg at a tie as a full BUY / SELL, and the review singled that out as "the word to
  worry about". Rev b read the tie as STAND ASIDE · tie (the drafter's reading). Rev c names the open leg, but only as LEANS,
  because nothing leads.
- **Unchanged: when the refused leg leads, the word is STAND ASIDE · led.** The facts favour the closed leg, so naming the
  open one would be a vote the count does not give.""")
rep("""- a refused leg's lead, or a tie, makes STAND ASIDE, never a vote for the other leg;""",
    """- a refused leg's lead makes STAND ASIDE, never a vote for the other leg;
- a tie with one leg refused names the open leg as LEANS, by refusal;""")

# ---- §A.8
rep("""in every session until about 09:30 (R3 and R4). Those closes can read only BUY or STAND ASIDE.""",
    """in every session until about 09:30 (R3 and R4). Those closes can read only BUY or LEANS BUY, by refusal, or STAND ASIDE.""")

# ---- §C.1
rep("""- **Her own words set the ATM straddle aside on expiry day:** *"since today was sensex expiry so that why otherwise atm
  straddle is ideal"*. §C.7 asks her about that directly.""",
    """- **Her own words set the ATM straddle aside on expiry day:** *"since today was sensex expiry so that why otherwise atm
  straddle is ideal"*. §C.7 asked her directly, and she answered NO: on the sold option's expiry day the reach is not read.""")
rep("""- **It binds only when her strike is farther than one straddle out.** Off expiry, S was 250–600 pts on the index-days the
  review checked, so nearly every sale sits inside it and the line decides exactly as today.
- **Its domain is far-out-of-the-money sales on an expiry afternoon.** On the record that was two breaks, both SENSEX 09-24
  after 14:38, held seven minutes each.""",
    """- **It binds only off her option's expiry day, and only when her strike is farther than one straddle out** (her answer,
  §C.7). Off expiry, S was 250–600 pts on the index-days the review checked, so nearly every sale sits inside it and the line
  decides exactly as today. **It will rarely bind.**
- **On the sold option's expiry day it is not read:** a line break folds her exactly as today. Every held break on the
  record was SENSEX 09-24 after 14:38, its expiry afternoon (rev b's §D.6), where her answer folds at the line.""")

# ---- §C.2
rep("""2. **At a close that rule 3 reads as a break** (rev 5 option B):
   - S unreadable: **FOLD, rule 3** ("could not check the reach: {why} — the line decides");""",
    """2. **At a close that rule 3 reads as a break** (rev 5 option B):
   - **on the sold option's expiry day** (her answer, §C.7): **FOLD, rule 3, as today.** The reach is not read. The reach row
     says "expiry today — the reach is not read: the line decides (your answer, 26 Sep)";
   - S unreadable: **FOLD, rule 3** ("could not check the reach: {why} — the line decides");""")
rep("""**The expiry-day switch** is her answer to §C.7. Until she answers, §C cannot be signed.""",
    """**The expiry-day switch is her answer to §C.7: NO.**
- "Expiry day" is a session whose date is her sold option's own expiry date, from the chain record
  (`upstox_instruments.resolve`), not the index's weekly calendar. A sale of a later expiry, made on an index's expiry day,
  is read off expiry.
- With the answer in, §C is complete and can be signed.""")

# ---- §C.3
rep("""- **Decay is inside S.** The straddle shrinks with time, so on an expiry afternoon the same strike becomes farther in
  straddles.""",
    """- **Decay is inside S.** The straddle shrinks with time, so the same strike becomes farther in straddles as expiry nears.
  **On her option's expiry day the reach is not read** (§C.7), so an expiry afternoon's collapsing straddle cannot hold her
  through a line break.""")

# ---- §C.4
rep("""It dies if **either** judged population fails. **When:** ≥ 15 held breaks in a population and ≥ 10 sessions, by 30 at the
latest. Short of that, inconclusive and DRAFT.""",
    """It dies if **either** judged population fails. **When:** ≥ 15 held breaks in a population and ≥ 10 sessions, by 30 at the
latest. Short of that, inconclusive and DRAFT.
- **Held breaks come off expiry only** (§C.7), so they will be rare. If fewer than 15 arrive by 30 sessions, W-R is
  inconclusive and the reach stays DRAFT. The count is not lowered to reach a verdict.""")

# ---- §C.6
rep("""- **W-R judges it on forward rows only.**

### C.7""", """- **W-R judges it on forward rows only.**
- **The expiry-day answer is hers**, given 2026-09-26 and relayed by the coordinator. It was asked after rev b's §D.6 had
  set the YES and NO rows side by side.

### C.7""")

# ---- §C.7
rep("""### C.7 THE ONE QUESTION FOR MARY: the reach on expiry day""",
    """### C.7 THE ONE QUESTION FOR MARY: the reach on expiry day — ANSWERED 2026-09-26: NO""")
rep("""- **If YES:** the reach applies on expiry day as on any other day.
  - This is where it does nearly all its work. On the record it bound only on SENSEX 09-24 after 14:38.
  - A sale outside one straddle rides a line break (WATCH · LINE BROKEN · HELD), with the held loss on screen.
  - It folds at the first 3-min close with the strike inside one straddle (3r), at any close more than one candle through
    the strike (3s), or by rules 4 / 6.
- **If NO:** on the sold option's expiry day, a line break folds her exactly as today (rev 5 option B, rule 3). Rule 3s still
  applies. The reach applies only off expiry, where on her days S was 250–600 pts and nearly every sale sits inside it, so it
  will rarely bind.
- **Until she answers,** §C is unsigned, and the draft recommends neither answer.""",
    """**Her answer, 2026-09-26** (her choice in the question tool, verbatim, relayed by the coordinator): *"No, fold as today"*.

**What it does, registered:**
- **On the sold option's expiry day, a line break FOLDs a writer exactly as today:** rev 5 option B, rule 3. The reach is not
  read that day, and there is no WATCH · LINE BROKEN · HELD.
- **Still in force on expiry day:** rule 3s (a close through her strike by more than one frozen candle), rules 4 and 6, and
  the entry check.
- **Off expiry, the reach applies as §C.2 says.** There S was 250–600 pts on her days, so nearly every sale sits inside one
  straddle, and **the reach will rarely bind.**
- **On 09-24 (SENSEX expiry)** the 74,100 call folds at 14:38 by rule 3, at 47.55, as today. A YES would have held it to
  14:45 (rule 4 at 42.45, with a high of 53.25 while held).
- **The YES branch is not registered.** Its figures stay in §D.6 as the road not taken.

**§C is complete:** the signed-distance strike rule with rev 5 B's buffer (3s), S of her own option's expiry or FOLD, the
held loss printed, W-R, and this answer. It can be signed.""")

# ---- §E.1
rep("""a tie EITHER, a tie with a leg refused STAND ASIDE; `named_by` and `strength` kept apart | **named choices** (M2; rev b) |""",
    """a tie EITHER, a tie with a leg refused LEANS on the open leg, by refusal; `named_by` and `strength` kept apart | **named choices** (M2; rev b; rev c) |""")
rep("""| the reach | signed R against S of her expiry, scale 1× | **named choice**; seller-desk design's unit; ≈ 0.2 Δ [I] |""",
    """| the reach | signed R against S of her expiry, scale 1×; **not read on her option's expiry day** | **named choice**; seller-desk design's unit; ≈ 0.2 Δ [I]; **her answer, §C.7** |""")

# ---- §E.2
rep("""- **Refusal units** are their own rows, with their codes and their strength, never pooled with count units:
  - BUY / LEANS BUY · selling refused;
  - SELL / LEANS SELL · buying refused.
- **STAND ASIDE · led** and **STAND ASIDE · tie** are judged, each on its own count. **STAND ASIDE · both refused** is shown,
  not judged: it re-tests rev 4 B4 and VALIDATE P2 (the entry FOLD), which judge it already.""",
    """- **Refusal units** are their own populations, with their codes and their strength, never pooled with count units, and
  **each is judged on its own count** (rev c):
  - **BUY · selling refused**; **LEANS BUY · selling refused**;
  - the mirror, **SELL · buying refused**; **LEANS SELL · buying refused**.
  - A LEANS by refusal is one word whether its lead is 1 or a tie, so it is one population. The tie units (`lead: 0`) are
    shown apart, not judged apart.
- **STAND ASIDE · led** is judged on its own count. **STAND ASIDE · both refused** is shown, not judged: it re-tests rev 4 B4
  and VALIDATE P2 (the entry FOLD), which judge it already.""")
rep("""- **STAND ASIDE · led and STAND ASIDE · tie, each on its own:** the median of max(long R, short R), the better leg, is lower
  at its units than at count units.""",
    """- **Each word named by refusal, on its own** (rev c): the claim of its count twin, against the same count units. For BUY
  and LEANS BUY · selling refused, the median G is **larger** than at the count units that do not point to buying; for SELL
  and LEANS SELL · buying refused, **smaller** than at those that do not point to selling. It asks whether naming the open
  leg beat the reads that did not point to it.
- **STAND ASIDE · led, on its own:** the median of max(long R, short R), the better leg, is lower at its units than at count
  units.""")
rep("""- **STAND ASIDE · led or · tie:** the refusals are re-registered; until then the word carries "its falsifier failed on
  {date}".""",
    """- **A word named by refusal:** withdrawn. Where it would have been named, the read says "STAND ASIDE — {word} withdrawn on
  {date}", with its count.
- **STAND ASIDE · led:** the refusals are re-registered; until then the word carries "its falsifier failed on {date}".""")

# ---- §E.3
rep(""" S, line, noise, regime_board, drag, expiry_line, blind: [...], word_1m, unit: bool, prereg: "expr-b", tag: "I"}
```""", """ S, line, noise, regime_board, drag, expiry_line, blind: [...], word_1m, unit: bool, after_1500: bool, prereg: "expr-c", tag: "I"}
```

A tie with one leg refused logs `strength: "leans"`, `lead: 0`, `named_by: "refusal"` (rev c).""")
rep(""" G, G_pts_over_S, move: {pts, split: "with"|"against"|"flat"}, short_window: bool, co_timed: [...],""",
    """ G, G_pts_over_S, move: {pts, split: "with"|"against"|"flat"}, short_window: bool, after_1500: bool, co_timed: [...],""")
rep("""- the outcome key gains `role` (§B.3).
""", """- the outcome key gains `role` (§B.3);
- every press and outcome row gains `after_1500` (below).
""")
rep("""- `writer_clause: "reach-b"`;
- `expiry_day: her §C.7 answer`.""", """- `writer_clause: "reach-c"`;
- `expiry_day: true | false`: her option's expiry is the session date. When true the reach is not read (her answer,
  2026-09-26);
- `after_1500` (below).

**`after_1500: true` (rev c), descriptive only.** It is written on every expression, outcome, press and hold row whose own
minute is 15:00 or later, and `false` before.
- **It gates nothing.** It changes no word, no fact, no refusal, no fold and no falsifier. §E.2's existing check with the
  `short` units removed is unchanged.
- **Why it exists:** Mary's current practice is to hold nothing and open nothing after 15:00 (§D, "Her practice"). The flag
  lets the forward record be read with and without those rows.
- An outcome row's window end is derivable from its `t`, so a window that crosses 15:00 can be read off too.""")

# ---- §E.4
rep("""| the expression, §E.2 | new | Starts at its first session after the code (`prereg: "expr-b"`). |""",
    """| the expression, §E.2 | new | Starts at its first session after the code (`prereg: "expr-c"`). |""")
rep("""**Reset for writers only** (`writer_clause: "reach-b"`).""", """**Reset for writers only** (`writer_clause: "reach-c"`).""")
rep("""| §C.4 W-R | new | Starts with the writer reset, **after her §C.7 answer**. |""",
    """| §C.4 W-R | new | Starts with the writer reset. Her §C.7 answer is in (NO), so held breaks come off expiry only. |""")

# ---- §F
rep("""   - **STAND ASIDE says which:** both refused; "the facts favour selling, 3 to 0, but selling is refused: …"; or "the facts
     tie 1–1, and selling is refused: nothing leads to buying".""",
    """   - **STAND ASIDE says which:** both refused, or "the facts favour selling, 3 to 0, but selling is refused: …".
   - **A tie with selling refused** (rev c) reads **LEANS / BUY CE**, with "selling refused (R4 — …) · the facts tie 1–1" in
     the caution ink.""")
rep("""  - inside: "… — inside: the line decides";""", """  - inside: "… — inside: the line decides";
  - on her option's expiry day: "expiry today — the reach is not read: a line break folds you (your answer, 26 Sep)";""")

# ---- §G, rev c's pre-run entry
rep("""**01:53, §D rewritten for rev b, after the run.**""", """**01:53, §D rewritten for rev b, after the run.**""")
s = s.replace("""- **No rule moved after rev b's run.**

---

## H.""", f"""- **No rule moved after rev b's run.**

**Rev c, 2026-09-26 {T} IST (clock).** Written after rev b's rows were seen. All of it was conveyed by the coordinator.
1. **§C.7 answered by Mary: NO.** Her choice in the question tool, verbatim: *"No, fold as today"*.
   - **Registered:** on the sold option's expiry day, a line break folds a writer exactly as today, and the reach is not
     read. Rule 3s, rules 4 and 6 and the entry check still apply that day.
   - **Consequential edits:** §C.1, §C.2 (a new first branch at a break, and what "expiry day" means), §C.3, §C.4 (held breaks
     off expiry only; the count is not lowered), §C.6, §C.7, §E.1, §E.3 (`expiry_day`, `reach-c`), §E.4 and §F.2 (the reach
     row on expiry day).
   - §C's other clauses are rev b's, unchanged. **§C is complete.**
2. **The tie with one leg refused, decided by the trader:** "STAND ASIDE when refused" means both legs refused. A tie with one
   leg refused names the open leg as LEANS {{BUY|SELL}} "· {{other}} refused", named by refusal.
   - **Principle:** she has a direction and one expression is open. The word should say so, weakly and plainly, and not go
     silent.
   - **What had been seen:** rev b's §D, where these ties were 170 of 756 STAND ASIDE closes, and 09-25 12:01 read STAND
     ASIDE · tie.
   - **Consequential edits:** §A.4 (the word, the history, the named choices), §A.8, §E.1, §E.2 (every refusal-named word is
     now judged on its own count, with its count twin's claim, and STAND ASIDE · tie is gone), §E.3 and §F.1.
   - **Kept, and flagged:** STAND ASIDE · led stays silent. The decision's text addressed the tie, and rev 0's named choice
     ("a refused leg's lead … never a vote for the other leg") was not revoked (§H.2).
3. **`after_1500`, a descriptive log flag (§E.3).** Mary, 2026-09-26, verbatim: *"we gonna close our position before 3
   because due to new cas system is highly volatile i dont want to get into that no trade buying or selling after 3 om to be
   on safe side dont make any new rules but just telling you so that you know because maybe it change in future (cas
   system)"*.
   - **Not a rule, a refusal or a gate.** The flag gates nothing and changes no word or falsifier. It lets the forward record
     be read with and without rows at 15:00 or later.
   - Her practice is disclosed in §D ("Her practice, not a rule"), with the evidence in this draft that falls after 15:00.

**Fingerprinted before its run** (§D.0).

---

## H.""", 1)
assert "**Rev c, 2026-09-26" in s
open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
