# Plan

## Active Fast Track: CLI-first github.local MVP — bootstrap Issue #1

**Fast Track status — CLOSED**

Purpose: determine whether current official GitHub CLI (`gh`) is a proportionate agent-facing interface for a tiny local forge, then implement the smallest durable local Issue workflow using the simpler branch if the compatibility burden is too high.

Scope and exit condition:

- [x] Reconstruct the reusable ContextCanon GitHub Local and Development Workflow contracts before implementation.
- [x] Inspect current `gh` 2.101.0 host routing and Issue command implementation from official sources.
- [x] Perform a short market check for existing local/offline issue/workflow tools.
- [x] Record the architecture decision: native `github-local` CLI first; keep `gh` compatibility as a measured optional adapter.
- [x] Establish the repository bootstrap Issue, project context, README skeleton, and durable spike evidence.
- [x] Implement atomic Markdown Issue storage with deterministic numbering and cross-process locking.
- [x] Implement `github-local init`, `issue create`, `issue list`, and `issue view`, including stable JSON output.
- [x] Add focused tests for restart, rapid/concurrent creation, UTF-8, Windows-safe filenames, corrupt metadata, and explicit unsupported commands.
- [x] Add a reproducible `gh` trace/fake server for running the real CLI outside this restricted build environment.
- [x] Run the complete local deterministic test suite and smoke test.
- [x] Prepare the coherent review candidate on feature branch `issue-1-cli-first-mvp`.
- [x] Create `SomeSunlight/github-local`, publish the review branch, and open a Draft PR after the owner supplied the empty repository.

Exit: the local repository contains a tested Issue create → list → view vertical slice, evidence explaining the `gh` decision, and no merge has occurred.

Checkpoint: implementation and local verification are complete; remote publication is now possible because the project owner created the empty GitHub repository. `python -m unittest discover -s tests -v` passes 12 tests; `compileall` passes; a wheel builds without runtime dependencies; installing that wheel into a fresh venv and running init → create → list → view against a disposable Git repository succeeds. Real-`gh` black-box execution remains intentionally unclaimed and reproducible via `spike/README.md`.

Fast Track closure: the bounded implementation/research block is complete and locally verified. The candidate remains unmerged for owner review. The remote repository now exists and this checkpoint is being published through Issue #1 and a Draft PR.
