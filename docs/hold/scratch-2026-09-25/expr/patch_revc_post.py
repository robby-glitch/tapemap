# Rev c's post-run text: the header's record line, three §D fixes, §G's post-run lines and §H. No rule text moves.
P = r"C:\Users\kaam\Desktop\operator mode\tapemap\docs\hold\EXPRESSION-PREREG-DRAFT.md"
s = open(P, encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


rules_before = s[:s.index("## D. DISCLOSURE")] + s[s.index("## E. PARAMETERS"):s.index("**Rev c, 2026-09-26 14:37 IST (clock).**")]

# ---- header record (not rule text)
rep("""(§D.0), and so was rev b's. §D is
  rev b's disclosure, written after rev b's run.""", """(§D.0), and so were rev b's and
  rev c's. §D is rev c's disclosure, written after rev c's run.""")

# ---- §D fixes
rep("""- **LEANS BUY is now the biggest word, and more than half of it is named by refusal:** 270 of 516.""",
    """- **LEANS BUY is now the most frequent directional word, and more than half of it is named by refusal:** 270 of 516.""")
rep("""### D.3 Facts, refusals, co-occurrence and the sell strike — rev a's, unchanged in rev b""",
    """### D.3 Facts, refusals, co-occurrence and the sell strike — rev a's, unchanged in rev b and rev c""")
rep("""  - a new `docs/hold/scratch-2026-09-25/` (14:41:52–58), a copy of this session's scratchpad folders made by another
    process during the run.""", """  - a new `docs/hold/scratch-2026-09-25/` (14:41:52–58), a copy of this session's scratchpad folders made by another
    process during the run.
- **At 14:43, commit `54dc72c`** (not rev c's) took this draft exactly at the rev c fingerprint (`64ad9d7f…`, checked),
  together with those files and that folder. The folder holds a partial `revc_run_out.txt`, copied mid-run.
- This section, §G's post-run lines and §H are edits on top of that commit, in the working tree, uncommitted.""")
rep("""  - Measured against 14:59, the 14:38 line folds gave up 14.0 (74,100), 17.55 (74,000), 19.8 (73,900) and 21.9 (73,800)
    points, not 47–133 as against 15:29.""", """  - The 14:38 line folds bought back 14.0 (74,100), 17.55 (74,000), 19.8 (73,900) and 21.9 (73,800) points above the
    14:59 premium, not 47–133 above the 15:29 one.""")

# ---- §G post-run
rep("""   - Her practice is disclosed in §D ("Her practice, not a rule"), with the evidence in this draft that falls after 15:00.

**Fingerprinted before its run** (§D.0).
""", """   - Her practice is disclosed in §D ("Her practice, not a rule"), with the evidence in this draft that falls after 15:00.

**Fingerprinted before its run** (§D.0).

**14:39–14:42, rev c's run** (`run_c.py`, after `expr_c.py`'s self-check). It wrote only inside `expr/revc/`.

**14:43, not rev c's.** Commit `54dc72c` took this draft at the rev c fingerprint, with other files and a copy of this
session's scratchpad (§D.0). Nothing of rev c's run was committed by rev c.

**18:43, §D rewritten for rev c, after the run** (`gen_D_c.py`). The session had paused between 14:42 and 18:43.
- Before §D went in, the text outside §D was checked identical to the fingerprinted copy.
- **One claim was fixed after it went in:** LEANS BUY is the most frequent *directional* word, not the most frequent word
  (STAND ASIDE is 586).
- **No rule moved after rev c's run.**
""")

# ---- §H
rep("""1. **The expiry-day question (§C.7)** is hers. §C cannot be signed without it.
2. **The word's margin: decided in rev b.** A one-fact lead reads LEANS, with no threshold number (§A.4).
   - Still open: the tie with one leg refused reads STAND ASIDE. That is the drafter's reading of "STAND ASIDE when refused",
     for the trader to confirm.
3. **Rule 3s's scope: decided in rev b.** Rev 5 B's own buffer, at every close (§C.2). §D.6 shows rev a's zero-buffer cost and
   rev b's re-run side by side.
   - **Still true under rev b:** the 09-24 74,000 sales fold at 13:05. That close was 25.4 pts through the strike against a
     candle of 18–19, so it was not noise by her own line rule.""",
    """1. **The expiry-day question (§C.7): answered NO, 2026-09-26.** §C is complete and can be signed.
   - **Still hers:** the answer is registered for the window's fold only. Fact 5 (PREMIUM) and the sale's placement unit
     (§A.5) still read the ATM straddle on expiry day, while her quote sets the ATM straddle aside on expiry day. Whether
     that exception reaches them is hers to say. Nothing here changes them.
2. **The word: its margin decided in rev b, the refused tie in rev c** (LEANS on the open leg, by refusal).
   - **Still open, for the trader: STAND ASIDE · led stays silent.** That is 226 closes, entry #9 and 09-25 09:36, where the
     refused leg leads. A literal "STAND ASIDE only when both legs are refused" would name the open leg there too, against
     the count. It is kept silent on rev 0's named choice, which was not revoked.
3. **Rule 3s's scope: decided in rev b.** Rev 5 B's own buffer, at every close (§C.2).
   - **Still true under rev c:** the 09-24 74,000 sales fold at 13:05. That close was 25.4 pts through the strike against a
     candle of 18–19, so it was not noise by her own line rule.
   - **The reach will rarely bind, and W-R may never reach its count.** Under her answer no held break exists on the four
     days (§D.6). If fewer than 15 arrive by 30 sessions, the reach stays DRAFT. The count is not lowered.""")
rep("""   - the writer rows' `reach` / `held` / `3r` / `3s` keys, and the expiry-day answer;""",
    """   - the writer rows' `reach` / `held` / `3r` / `3s` keys, and `expiry_day` (her NO: the reach is not read that day);
   - `after_1500` on expression, outcome, press and hold rows (descriptive; it gates nothing);""")
rep("""     - the word order and `named_by`;""", """     - the word order and `named_by`, including the refused tie read as LEANS by refusal;
     - the expiry-day fold at a line break, with 3s still in force;
     - `after_1500` changing no word, fold or falsifier;""")
s = s.rstrip("\n") + """
10. **Her 15:00 practice is disclosed, not registered** (§D.8). If CAS changes it, nothing here has to move. The flag lets the
    forward record be read either way.
"""

after = s[:s.index("## D. DISCLOSURE")] + s[s.index("## E. PARAMETERS"):s.index("**Rev c, 2026-09-26 14:37 IST (clock).**")]
# the only rule-region change allowed here is the header record line
assert after.replace("and so were rev b's and\n  rev c's. §D is rev c's disclosure, written after rev c's run.",
                     "and so was rev b's. §D is\n  rev b's disclosure, written after rev b's run.") == rules_before
open(P, "w", encoding="utf-8", newline="\n").write(s)
print("post-run text written")
