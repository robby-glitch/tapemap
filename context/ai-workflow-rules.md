# AI Workflow Rules

## Approach

Spec-driven, incremental, regression-gated. The `context/` files define what
to build, how, and current state. Implement strictly against them — never
invent product behavior. Every unit of work ends with a verification step
(replay regression, API validation, or UI screenshot) before the next unit
starts. `progress-tracker.md` is updated after every meaningful change.

The prime directive from the operator: no AI slop. Check, recheck, then
build. When uncertainty exists about market mechanics or data semantics,
verify against real data (the 3 ground-truth days, or a Dhan fetch) before
coding on top of an assumption.

## Scoping Rules

- Work on one unit at a time (e.g., "GammaLayer Stage 1 in engine.py" is one
  unit; its UI strip is a second unit).
- Prefer small, verifiable increments over large speculative changes.
- Never combine engine-logic changes and UI changes in one step — the engine
  regression gate must pass before the UI touches new fields.

## When to Split Work

Split an implementation step if it combines:

- Engine analytics changes and UI rendering changes.
- Dhan API fetching and engine feature computation.
- Base-signal logic and gamma-layer logic (these must never mix — see
  architecture invariant 3).

If a change cannot be verified end to end quickly, the scope is too broad —
split it.

## Handling Missing Requirements

- Do not invent trading logic not defined in context files or the approved
  plan (`before-you-run-any-hashed-bubble.md`).
- If a requirement is ambiguous, resolve it in the relevant context file
  first (ask the operator if it's a product decision).
- If a requirement is missing, add it to Open Questions in
  `progress-tracker.md` before continuing.

## Protected Files

Do not modify unless explicitly instructed:

- `data/*_3day.csv` — ground-truth TradingView exports (immutable).
- `.dhan_token` — operator-supplied credential.
- `gan-harness/*`, `ui/variant-*.html`, `ui/redesign.html` — design history.
- `context/ai-workflow-rules.md` — this file (operator's process contract).

## Keeping Docs in Sync

Update the relevant context file whenever implementation changes:

- New engine fields/events → `architecture.md` boundaries + README event
  grammar.
- New UI tokens/panels → `ui-context.md`.
- Every completed/started unit → `progress-tracker.md`.

## Before Moving to the Next Unit

1. The current unit works end to end within its defined scope.
2. No invariant in `architecture.md` violated — specifically: run
   `python engine.py data 24200 > replay_new.txt` and diff against the
   previous replay output; base events must be byte-identical unless the
   unit intentionally changed them (record intent in progress tracker).
3. `python -c "import engine, analyze"` passes (syntax gate) and
   `python analyze.py` produces valid JSON.
4. If UI changed: reload `localhost:8765`, screenshot, verify the specific
   change visually.
5. `progress-tracker.md` reflects the completed work.
