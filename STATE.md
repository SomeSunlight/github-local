# Current State

The first Fast Track implementation block is complete locally and remains backed by bootstrap Issue #1.

Architecture decision: **CLI-first native provider for the MVP**. Official `gh` remains a valuable vocabulary/reference and a possible later adapter, but current `gh` 2.101.0 Issue operations impose a GitHub Enterprise-shaped HTTPS/GraphQL contract that is disproportionate for the first local slice. See `docs/gh-compatibility.md` and `docs/architecture.md`.

The project owner has created `SomeSunlight/github-local` as the public development repository. The first verified candidate is being published there through GitHub Issue #1 and branch `issue-1-cli-first-mvp`. No merge is permitted without explicit project-owner approval.

## Implementation checkpoint

The native Issue MVP is implemented on local branch `issue-1-cli-first-mvp`:

- `github-local init` creates repository-local configuration;
- `issue create` writes one canonical Markdown Issue atomically;
- `issue list` and `issue view` reload state from disk, including after restart;
- `--json` provides stable selected-field output for agent use;
- issue numbering is protected by an OS-level cross-process lock (`msvcrt` on Windows, `flock` on POSIX);
- the test suite covers restart, concurrent creation, UTF-8, Windows-reserved filename slugs, corrupt metadata, stable error exits, JSON validation, and the trace server;
- the installable wheel has no runtime dependencies.

Verification: 12/12 deterministic tests pass, Python compilation passes, wheel build passes, and an installed-wheel smoke test successfully performs init → create → list → view in a fresh Git repository.

The remote delivery gap is closed: the repository now exists. The first candidate is published for review and remains deliberately unmerged. v0.1.0 supports Issue init/create/list/view; close/edit/comment and explicit machine-readable Change ↔ Issue links remain future slices rather than hidden assumptions.
