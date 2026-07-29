# Vendored libraries

## candl/ — CandL Charts

- Upstream: https://github.com/rahulsangam7/Candl (`@candllabs/charts`)
- Commit: 538938105834d9231860d639e4b03956e5f3dd67 (vendored 2026-07-30)
- License: Apache-2.0 — LICENSE and NOTICE are inside `candl/` as the licence requires.
- Why from source: the package is not on npm (`@candllabs/charts` 404s) and its
  `files` field ships only `dist`, so a git-URL install would depend on their
  build running. Vite compiles the source with our app instead.

**This tree is pristine.** Never edit a file under `candl/`. Any change we need
goes in a sibling file under `ui-v2/src/trade/`, so we can still diff against
upstream when it releases. To re-vendor: clone upstream, check out the new
commit, re-copy `src/` + LICENSE + NOTICE, update this file.
