"""Three doc claims that a script caught wrong on 2026-08-14, pinned so they
cannot go wrong quietly again.

NOT a documentation linter. Only claims that are (a) mechanically checkable and
(b) stable are here. The live record's counts -- rows, entries, arms -- change
every trading day and are deliberately NOT asserted: a test that fails every
afternoon teaches people to ignore it, which is worse than no test.

Each of these was a real error, not a hypothetical:

1. Both docs said 584 tests while the suite reported 585 -- stale inside the
   very commit that wrote them. The audit missed it because it checked
   `"584" in docs`, proving the number was WRITTEN rather than TRUE.
2. HANDOFF's header named the commit it was pushed at. Any hash a doc states
   is stale the moment that doc is committed.
3. PRODUCT and HANDOFF both said all three screens render the re-fire lock
   through `machine.ts`'s `lockNote`. SetupCheck.tsx does not import it.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _full_run(config):
    """Is this the whole suite, or a subset?

    `testscollected` is only the repo's test count when nothing was filtered.
    Under `pytest test_foo.py` or `-k something` it is a smaller number, and
    asserting the docs against it would fail for a reason that has nothing to
    do with the docs.
    """
    if config.option.keyword or config.option.markexpr:
        return False
    named = [a for a in config.args if not a.startswith("-")]
    return all(a in ("", ".", ROOT, str(getattr(config, "rootpath", "")))
               for a in named)


def test_stated_test_count_matches_reality(request):
    """Every "N tests pass" in the docs must equal what pytest just collected.

    Checked against the RUN, never against the presence of a string -- that
    distinction is the whole reason this test exists.
    """
    if not _full_run(request.config):
        pytest.skip("subset run; testscollected is not the repo's test count")

    actual = request.session.testscollected
    docs = {p: _read(*p.split("/")) for p in
            ("context/HANDOFF.md", "context/DEFERRED.md", "PRODUCT.md",
             "README.md", "context/research-findings.md")}

    claims = {}
    for path, text in docs.items():
        found = [int(n) for n in re.findall(r"\*\*(\d+) tests pass", text)]
        found += [int(n) for n in
                  re.findall(r"[Tt]est count is now \*?\*?(\d+)", text)]
        if found:
            claims[path] = found

    assert claims, ("no doc states a test count any more — if that was "
                    "deliberate, delete this test; otherwise the claim was "
                    "silently dropped")
    wrong = {p: n for p, n in claims.items() if any(x != actual for x in n)}
    assert not wrong, (
        f"pytest collected {actual}, but these docs claim otherwise: {wrong}. "
        f"A stale count is how a reader learns to distrust the whole file.")


def test_handoff_header_names_no_commit_hash():
    """The status header must not state a commit — it invalidates itself.

    Hashes elsewhere in the file are fine and wanted: the dated entries cite
    the commits they describe, and those citations stay true. Only the "where
    is this branch right now" line rots, because the commit that writes it does
    not exist yet when it is written.
    """
    text = _read("context", "HANDOFF.md")
    header = text[:text.index("###")]
    hits = re.findall(r"pushed to `origin`[^\n]*?`([0-9a-f]{7,40})`", header)
    assert not hits, (
        f"HANDOFF's header names commit(s) {hits}. Whatever hash goes there is "
        f"stale as soon as this file is committed — say `git log --oneline -1` "
        f"instead.")


def test_setupcheck_lock_wording_exception_still_holds_and_is_documented():
    """SetupCheck renders the re-fire lock WITHOUT `lockNote`, on purpose.

    `lockNote`'s docstring promises one definition "so a fourth screen cannot
    invent a fifth wording". SetupCheck predates it and renders from its own
    `lockWhy` prop. That is correct today and is a documented exception -- this
    pins BOTH halves, so the code and the docs cannot drift apart in either
    direction. If SetupCheck is ever routed through `lockNote`, this test fails
    and the docs get corrected in the same change.
    """
    sc = _read("ui-v2", "src", "trade", "SetupCheck.tsx")
    machine = _read("ui-v2", "src", "machine.ts")

    assert "export function lockNote" in machine, (
        "machine.ts no longer exports lockNote; the docs describe it as the "
        "shared definition for App.tsx and GlassBoard.tsx")
    for f in ("App.tsx", "one/GlassBoard.tsx"):
        assert "lockNote" in _read("ui-v2", "src", *f.split("/")), (
            f"{f} no longer uses lockNote — the docs say it does")

    assert "lockNote" not in sc, (
        "SetupCheck.tsx now uses lockNote. That is an IMPROVEMENT, not a "
        "failure — update PRODUCT.md and HANDOFF.md, which both record it as "
        "the standing exception, then delete this assertion.")
    assert "lockWhy" in sc, (
        "SetupCheck.tsx no longer has its own lockWhy prop, so the docs' "
        "description of how it renders the lock is wrong")

    assert "SetupCheck.tsx` does NOT" in _read("context", "HANDOFF.md"), (
        "HANDOFF no longer records the SetupCheck exception; without it a "
        "reader concludes all three screens share one definition")
    assert "lockWhy" in _read("PRODUCT.md"), (
        "PRODUCT.md no longer records how SetupCheck renders the lock")
