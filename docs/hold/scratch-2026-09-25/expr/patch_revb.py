# Applies REVISION b's rule-text edits to the draft (the repo's docs/hold/EXPRESSION-PREREG-DRAFT.md, absolute path).
# Every replacement must match exactly once; nothing else in the repo is touched.
P = r"C:\Users\kaam\Desktop\operator mode\tapemap\docs\hold\EXPRESSION-PREREG-DRAFT.md"
s = open(P, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:80])
    s = s.replace(a, b)


# ---- title and header
rep("THE SELLER IN THE WINDOW — REVISION a (rev 0 written 2026-09-26 00:16 IST; rev a written 01:25 IST by the clock, before its run; NOT SIGNED, UNTESTED)",
    "THE SELLER IN THE WINDOW — REVISION b (rev 0 written 2026-09-26 00:16 IST; rev a 01:25; rev b written 01:47 IST by the clock, before its run; NOT SIGNED, UNTESTED)")
rep("""- §G lists every edit to the rules made after a fingerprint, including the three that rev 0a left out (review M5).
""", """- §G lists every edit to the rules made after a fingerprint, including the three that rev 0a left out (review M5).
- **Rev b (01:47)** takes two trader decisions made **after rev a's rows were seen**, on principle, and is fingerprinted
  before its run (§D.0):
  - the strike rule inherits rev 5 option B's one-candle buffer (§C.2);
  - the word shows its margin: BUY / SELL, LEANS BUY / LEANS SELL, EITHER, STAND ASIDE (§A.4).
""")
rep("""- the far-strike rule (Q3).
""", """- the far-strike rule (Q3).
- **rev b, after rev a's rows were seen:** the strike rule with rev 5 B's buffer; the word's strength shown as LEANS.
""")
rep("- the signed reach, and a close at or through the strike always folds (M7);",
    "- the signed reach, and a close through the strike always folds (M7); rev b adds rev 5 B's one-candle buffer to it;")

# ---- §A.4 the word
old_word = s[s.index("**The word**, in this order, with `b` and `s` the FOR BUY and FOR SELL counts:"):s.index("### A.5 Which strike")]
new_word = """**The word (rev b)**, in this order. `b` and `s` are the FOR BUY and FOR SELL counts, and the **lead** is the named leg's
count minus the other's.
1. **could not check** when the line cannot be set at the close (no index candle, or the close not landed);
2. **both refused: STAND ASIDE · both refused**, naming each refusal;
3. **only SELL refused:**
   - a lead of 2 or more: **BUY {CE|PE} · selling refused**, with the codes;
   - a lead of exactly 1: **LEANS BUY {CE|PE} · selling refused**;
   - a tie: **STAND ASIDE · tie, selling refused**: "the facts tie {b}–{s}, and selling is refused: nothing leads to
     buying";
   - selling leads: **STAND ASIDE · led**: "the facts favour selling, {s} to {b}, but selling is refused: {why}";
4. **only BUY refused:** mirrored (SELL / LEANS SELL · buying refused; STAND ASIDE · tie; STAND ASIDE · led);
5. **neither refused (on the count):**
   - a lead of 2 or more: **BUY** or **SELL**;
   - a lead of exactly 1: **LEANS BUY** or **LEANS SELL**;
   - a tie: **EITHER**: "EITHER — the facts split {b}–{s}" (review S2). At 0–0 it reads "nothing separates them".

**The word's strength is in the word** (rev b, the trader's decision after rev a's rows):
- **There is no threshold number.** "Exactly 1" means a single fact decides the word, and "2 or more" means more than one
  does.
- **LEANS is a word of its own:** on screen, in the log (`strength: "lead" | "leans" | "tie"`, `lead: n`), and in the
  falsifiers, where LEANS and BUY / SELL are separate populations, never pooled (§E.2).

**The tie with one leg refused is STAND ASIDE** (rev b).
- **Rev a named the open leg at a tie** ("BUY · selling refused" at b = s). The review singled that out as "the word to
  worry about".
- Under rev b's rule that the margin shows in the word, a tie cannot be EITHER when one leg is closed. The open leg leads by
  nothing, so the word is STAND ASIDE · tie.
- **This is the drafter's reading** of the decision "STAND ASIDE when refused". It is flagged in §G and §H for the trader to
  confirm.

**The split is kept everywhere** (review M2): on screen, in the log (`named_by: "count" | "refusal"`, `refusal: [codes]`) and in
the falsifiers (§E.2).
- A word named because the other leg is refused is **never** dressed as, pooled with, or judged as a word on the count.
- *Why:* a word on the count compares two live legs. A word by refusal had one leg that was never an alternative, so it
  tests the refusal, not the facts.

**Named choices, none of them a number:**
- a leg is refused by its own rules, not outvoted;
- a refused leg's lead, or a tie, makes STAND ASIDE, never a vote for the other leg;
- a tie of live legs is EITHER;
- one fact's lead is LEANS;
- the word is read at the 3-minute close.

"""
s = s.replace(old_word, new_word)

rep("""- **The word is close to a coin flip at its margin.** Many words are named by one fact (§D.2). The count and the since-clock
  are printed so she can see a 3–2 that is new from one that has stood.""",
    """- **The word is close to a coin flip at its margin.** Many words are named by one fact (§D.2).
  - Rev b says so **in the word**: LEANS BUY / LEANS SELL.
  - The since-clock shows whether a 3–2 is new or has stood.""")

# ---- §C: the strike rule inherits rev 5 B's buffer
rep("- **Rule 3s adds one hard stop for every writer, always:** a 3-minute close at or through her strike folds her.",
    "- **Rule 3s adds one hard stop for every writer, always:** a 3-minute close through her strike by **more than one frozen\n"
    "  median 1-minute candle** folds her. That is rev 5 option B's own buffer (rev b).")
rep("""  short CE, and close − k for a short PE. R ≤ 0 means the close is at or through her strike.""",
    """  short CE, and close − k for a short PE. R ≤ 0 means the close is at or through her strike.
- **B_k** (rev b): **exactly rev 5 §A.2's B**, with its measure, window, freeze, clamp and fallback, read for the strike's line.
  - It is the median high − low of the index's own 1-minute candles over the 15 finished minutes ending at the minute the
    strike's line is set, which is her entry read. All 15 must be present.
  - It is frozen. The strike never trails, so B_k is read once, and rev 5's clamp (never away) can never bind.
  - Fewer than 15 candles at entry: buffer 0 until B_k can be read, at the first later minute with its own 15, then frozen.
    That is rev 5's named fallback and its one move away.
  - The strike's break level is **k + B_k** for a short CE and **k − B_k** for a short PE, printed from entry beside the
    strike.""")
rep("""1. **Rule 3s — the strike, always** (coordinator item 4). At any close, broken line or not, held or not: **R ≤ 0 → FOLD,
   rule 3s**. "{IDX} closed {|R|} pts through your strike {k} [M]". A sale made in the money folds at its first close, and
   the entry check says so at entry.""",
    """1. **Rule 3s — the strike, always, with rev 5 B's buffer** (rev b). At any close, broken line or not, held or not: a close
   **beyond the strike's break level** (R < −B_k, strict) → **FOLD, rule 3s**. "{IDX}'s {bar} bar closed {|R|} pts through
   your strike {k} — {|R| − B_k} past one candle ({B_k} pts [M], read {B_at})".
   - *Principle:* her line rule, signed as rev 5 B, says a close inside one normal candle is noise. The strike is a line, so
     the same rule applies. **A zero-buffer strike stop (rev a) contradicted signed rev 5.**
   - A sale made more than one candle in the money folds at its first close, and the entry check says so at entry.""")
rep("""     > first 3-min close with your strike within one straddle, or at or through your strike.\"""",
    """     > first 3-min close with your strike within one straddle, or through your strike by more than one candle.\"""")
rep("  - a close at or through her strike folds her whatever S says (3s).",
    "  - a close through her strike by more than one candle folds her whatever S says (3s).")
rep("""  back inside the bar. On an expiry afternoon a single bar can be as wide as the straddle: SENSEX 09-24 at 15:29 had S 20.05
  against a 139.3-pt bar (review M7). The held loss and P_max (§C.4) are printed and logged for that reason.""",
    """  back inside the bar. On an expiry afternoon a single bar can be as wide as the straddle: SENSEX 09-24 at 15:29 had S 20.05
  against a 139.3-pt bar (review M7). The held loss and P_max (§C.4) are printed and logged for that reason.
- **What the buffer costs** (rev b): a close up to one candle through her strike does not fold her by 3s. That is the price of
  not folding on noise, the same price rev 5 B already pays at the line.""")
rep("  strike 58–78 OTM. **Rule 3s closes it:** a close through the strike folds her.",
    "  strike 58–78 OTM. **Rule 3s closes it:** a close through the strike by more than one candle folds her.")
rep("- 3s and the signed R were decided as the trader after the review showed the holes.",
    "- 3s and the signed R were decided as the trader after the review showed the holes. **3s's buffer (rev b) was decided\n"
    "  after rev a's rows showed the zero-buffer stop's cost.**")
rep("""  - It folds at the first 3-min close with the strike inside one straddle (3r), at any close at or through the strike (3s),
    or by rules 4 / 6.""",
    """  - It folds at the first 3-min close with the strike inside one straddle (3r), at any close more than one candle through
    the strike (3s), or by rules 4 / 6.""")

# ---- §E.1
rep("| the word | refusals, then the count; a tie EITHER; `named_by` kept apart | **named choice** (M2) |",
    "| the word | refusals, then the count; a lead of 2 or more BUY / SELL, of exactly 1 LEANS, a tie EITHER, a tie with a leg refused STAND ASIDE; `named_by` and `strength` kept apart | **named choices** (M2; rev b) |")
rep("| the reach | signed R against S of her expiry, scale 1×; 3s at R ≤ 0, always | **named choice**; seller-desk design's unit; ≈ 0.2 Δ [I] |",
    "| the reach | signed R against S of her expiry, scale 1× | **named choice**; seller-desk design's unit; ≈ 0.2 Δ [I] |\n"
    "| rule 3s (rev b) | a close beyond k ± B_k, always; B_k = rev 5 §A.2's B read at her entry, frozen, with its fallback | rev 5 option B, signed |")

# ---- §E.2 populations and claims
rep("""- **Count units** are those where neither leg was refused: BUY, SELL and EITHER on the count.
- **Refusal units** (BUY · selling refused; SELL · buying refused) are their own rows, with their codes, never pooled with
  count units.
- **STAND ASIDE · led** is judged. **STAND ASIDE · both refused** is shown, not judged: it re-tests rev 4 B4 and VALIDATE P2
  (the entry FOLD), which judge it already.""",
    """- **Count units** are those where neither leg was refused. Rev b splits them into five words, each its own population:
  **BUY**, **LEANS BUY**, **EITHER**, **LEANS SELL**, **SELL**. LEANS is never pooled with BUY / SELL.
- **Refusal units** are their own rows, with their codes and their strength, never pooled with count units:
  - BUY / LEANS BUY · selling refused;
  - SELL / LEANS SELL · buying refused.
- **STAND ASIDE · led** and **STAND ASIDE · tie** are judged, each on its own count. **STAND ASIDE · both refused** is shown,
  not judged: it re-tests rev 4 B4 and VALIDATE P2 (the entry FOLD), which judge it already.""")
rep("""- **BUY (count):** the median G at BUY-count units is **larger** than at the other count units (SELL-count and EITHER).
- **SELL (count):** the median G at SELL-count units is **smaller** than at the other count units (BUY-count and EITHER).
- **EITHER:** the median |G| at EITHER units is smaller than at BUY-count units, **and** smaller than at SELL-count units,
  each separately (S2).
- **STAND ASIDE · led:** the median of max(long R, short R), the better leg, is lower at STAND ASIDE · led units than at count
  units.""",
    """- **BUY and LEANS BUY, each on its own:** the median G at its units is **larger** than at the count units that do not
  point to buying (EITHER, LEANS SELL and SELL).
- **SELL and LEANS SELL, each on its own:** the median G at its units is **smaller** than at the count units that do not
  point to selling (EITHER, LEANS BUY and BUY).
- **Shown, not judged:** the medians in order, BUY ≥ LEANS BUY ≥ EITHER ≥ LEANS SELL ≥ SELL. That shows whether the strength
  the word prints is real.
- **EITHER:** the median |G| at EITHER units is smaller than at BUY units, **and** smaller than at SELL units, each separately
  (S2). The same against LEANS is shown.
- **STAND ASIDE · led and STAND ASIDE · tie, each on its own:** the median of max(long R, short R), the better leg, is lower
  at its units than at count units.""")
rep("""- **BUY or SELL:** withdrawn. Where it would have been named, the read says "EITHER — {word} withdrawn on {date}", with its
  count.""",
    """- **BUY, SELL, LEANS BUY or LEANS SELL:** withdrawn. Where it would have been named, the read says "EITHER — {word}
  withdrawn on {date}", with its count.""")
rep("- **STAND ASIDE · led:** the refusals are re-registered; until then the word carries \"its falsifier failed on {date}\".",
    "- **STAND ASIDE · led or · tie:** the refusals are re-registered; until then the word carries \"its falsifier failed on\n"
    "  {date}\".")

# ---- §E.3 logs
rep("""{kind: "expr", day, t, idx, d, word, named_by: "count"|"refusal", refusal: [codes], since, was: {word, until},""",
    """{kind: "expr", day, t, idx, d, word, strength: "lead"|"leans"|"tie", lead, named_by: "count"|"refusal", refusal: [codes],
 since, was: {word, until},""")
rep(""" S, line, noise, regime_board, drag, expiry_line, blind: [...], word_1m, unit: bool, prereg: "expr-a", tag: "I"}""",
    """ S, line, noise, regime_board, drag, expiry_line, blind: [...], word_1m, unit: bool, prereg: "expr-b", tag: "I"}""")
rep("{kind: \"expr_outcome\", day, t, idx, d, word, named_by, refusal,",
    "{kind: \"expr_outcome\", day, t, idx, d, word, strength, lead, named_by, refusal,")
rep("- `fold_rule: \"3r\" | \"3s\"`;", "- `fold_rule: \"3r\" | \"3s\"`, and `strike: {k, B_k, B_at, level}` from entry (rev b);")
rep("- `writer_clause: \"reach-a\"`;", "- `writer_clause: \"reach-b\"`;")
rep("| the window, writers (W1, W2, the writer clauses 1–7) | yes: rule 3 for writers, plus 3r and 3s | **Reset for writers only** (`writer_clause: \"reach-a\"`). Rev 5's writer rows stay rev 5's record. |",
    "| the window, writers (W1, W2, the writer clauses 1–7) | yes: rule 3 for writers, plus 3r and 3s | **Reset for writers only** (`writer_clause: \"reach-b\"`). Rev 5's writer rows stay rev 5's record. |")
rep("| the expression, §E.2 | new | Starts at its first session after the code (`prereg: \"expr-a\"`). |",
    "| the expression, §E.2 | new | Starts at its first session after the code (`prereg: \"expr-b\"`). |")

# ---- §F
rep("1. **THE EXPRESSION**, one word at 88 px: **BUY CE** · **SELL PE** · **EITHER** · **STAND ASIDE**.",
    "1. **THE EXPRESSION**, one word at 88 px: **BUY CE** · **SELL PE** · **LEANS BUY CE** · **LEANS SELL PE** · **EITHER** ·\n"
    "   **STAND ASIDE**.\n"
    "   - **LEANS is part of the word, not a caption.** It is set in the same Barlow at half the size, on the line above the leg\n"
    "     (\"LEANS / BUY CE\"), so a one-fact word can never be read as a lead.")
rep("   - **STAND ASIDE says which:** both refused, or \"the facts favour selling, 3 to 0, but selling is refused: …\".",
    "   - **STAND ASIDE says which:** both refused; \"the facts favour selling, 3 to 0, but selling is refused: …\"; or \"the facts\n"
    "     tie 1–1, and selling is refused: nothing leads to buying\".")
rep("    FOLD at the first 3-min close with your strike within one straddle, or at or through your strike\".",
    "    FOLD at the first 3-min close with your strike within one straddle, or through your strike by more than one candle\".")
rep("- **The strike row, always, for writers:** \"a 3-min close at or through {k} folds you (rule 3s) — {R} pts out\".",
    "- **The strike row, always, for writers:** \"your strike {k} · breaks on a 3-min close {above / below} {k ± B_k} — one\n"
    "  median candle, {B_k} pts [M], read {B_at} (rule 3s) — {R} pts out\".")

# ---- §H
rep("""2. **The word's margin.** Read at the 3-minute close, the word still carries many one-fact margins (§D.2). The since-clock
   and the count show it; nothing hides it. Whether a one-fact margin should read EITHER is **not** registered: it would
   invent a threshold.""",
    """2. **The word's margin: decided in rev b.** A one-fact lead reads LEANS, with no threshold number (§A.4).
   - Still open: the tie with one leg refused reads STAND ASIDE. That is the drafter's reading of "STAND ASIDE when refused",
     for the trader to confirm.""")
old3 = s[s.index("3. **Rule 3s's scope is a trader decision"):s.index("4. **ROOM leans BUY**")]
rep(old3, """3. **Rule 3s's scope: decided in rev b.** Rev 5 B's own buffer, at every close (§C.2). Rev a's cost is in §D's rev a history,
   and rev b's re-run is in §D.6 and §D.7.
""")
rep("""5. **Rule 3s folds a sale made in the money at its first close.** §A.5 never places one, but a press at an in-the-money
   strike is her own. A deliberate in-the-money sale is not supported by this window; hers to say if it should be.""",
    """5. **Rule 3s folds a sale made more than one candle in the money at its first close.** §A.5 never places one, but a press
   at an in-the-money strike is her own. A deliberate in-the-money sale is not supported by this window; hers to say if it
   should be.""")

# ---- §G entry for rev b (appended after the last §G paragraph)
anchor = "No rule moved after the run. **Rule 3s's cost (§D.6, §D.7) is disclosed, not tuned; its scope is raised in §H.3.**"
rep(anchor, anchor + """

**Rev b, 2026-09-26 01:47 IST (clock). Two trader decisions, made on her standing delegation, on principle, and made after
rev a's rows were seen.** Both were conveyed by the coordinator.

1. **The strike rule inherits rev 5 option B's buffer.**
   - **The rule:** a writer is FOLDed on a 3-min close through her strike by more than one frozen median 1-minute candle, at
     every close, held or not. It uses exactly rev 5 §A.2's B: its measure, window, freeze, clamp (which never binds, since
     the strike never trails) and fallback. No new number.
   - **Principle:** the line rule she signed says a close inside one candle is noise. The strike is a line. A zero-buffer
     strike stop contradicted signed rev 5.
   - **What had been seen:** rev a's §D.6 / §D.7, where the zero-buffer 3s folded the 09-24 74,000 sales on a 25-pt poke, and
     at-the-money sales on their first close past the strike.
2. **The word shows its margin.** The words are BUY / SELL for a lead of 2 or more, LEANS BUY / LEANS SELL for a lead of
   exactly 1, EITHER on a tie, and STAND ASIDE when refused.
   - LEANS is its own word in the logs and the falsifiers, a separate population never pooled with BUY / SELL.
   - **What had been seen:** rev a's §D.2, where half the BUY / SELL words stood on a single fact.
   - **The drafter's reading, flagged:** a tie with one leg refused reads STAND ASIDE · tie. Rev a named the open leg there.
     It is for the trader to confirm (§H.2).

**Rev b also fixes the scratch folder's defect:** `expr.py` no longer changes its working directory, and every script writes to
absolute paths inside `expr/`. Nothing can land in the repo again.

**Fingerprinted before its run** (§D.0). §C.7 stays the question, unanswered.""")

open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
