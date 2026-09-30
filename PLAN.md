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


## Owner validation and next sequence

- [x] Complete the manual owner smoke test: initialize, create three Issues, list as text/JSON, and view Issue #1.
- [x] Complete the real Copilot smoke test without MCP; the agent successfully used `github-local` plus native Git from terminal access alone.
- [x] Capture the LLM debrief and convert product gaps into Issues #3–#7.
- [x] Keep Assignees and milestones out of current scope.
- [ ] After PR #2 is owner-approved and squash-merged, onboard `github-local` with ContextCanon and compose the reusable GitHub / Development Workflow context.
- [ ] Resolve #3's branch/worktree semantics before expanding persisted workflow state.
- [ ] Implement #4 immediately afterwards: complete the Issue lifecycle and automatic close for explicitly referenced accepted/merged work, before broader workflow testing.
- [ ] Continue with #5 Change ↔ Issue linking, then #6 backlog ergonomics and #7 help examples.

Owner-test conclusion: the CLI-first integration mechanism is validated. The remaining work is product semantics, not proof that Copilot can call local tools.


## Active Fast Track: runtime development provenance — Issue #8

**Fast Track status — CLOSED**

Purpose: make `github-local --version` identify both the stable release baseline and the exact Git checkout being tested, following inherited CCW-014.

- [x] Keep `pyproject.toml` as the single canonical release-version source.
- [x] Add dependency-free runtime branch/ref + short commit + dirty provenance for source/editable checkouts.
- [x] Keep installed artifacts without Git metadata on the plain release version.
- [x] Add top-level `github-local --version` on stdout.
- [x] Add focused release/provenance/CLI regression tests.
- [x] Run the complete deterministic suite and repository consistency checks.
- [x] Keep PR #9 unmerged until explicit owner approval.

Checkpoint: the owner ran the complete deterministic suite successfully with `uv run python -m unittest discover -s tests -v`, `contextcanon check --all .` passed, and `github-local --version` reported the expected branch/SHA/dirty provenance. PR #9 was squash-merged to `main` as `14034cd`; Issue #8 is closed.

Issue #3 remains separate and will handle project-wide Issue identity/numbering across branches and worktrees.


## Active Fast Track: project-wide Issue state — Issue #3

**Fast Track status — ACTIVE**

Purpose: make one local Issue backlog authoritative across ordinary Git branches and linked worktrees without moving canonical Issue content into a database or making Git branches own workflow state.

- [x] Make all worktrees resolve one canonical visible `issues/` directory in the primary worktree.
- [x] Move runtime repository configuration and Issue locking onto the shared Git common directory so linked worktrees use one identity and one allocator.
- [x] Keep `issues/` outside ordinary branch tracking and add a shared Git exclude rule.
- [x] Fail clearly when tracked `issues/` would make project-wide semantics unsafe; do not silently rewrite the Git index.
- [x] Preserve existing Issue Markdown format, stable IDs, URLs, and monotonic numbering.
- [x] Add real-Git regression coverage for branch switches, linked worktrees, shared numbering, and tracked-Issue refusal.
- [x] Document the KISS storage semantics before Issue lifecycle expansion.
- [ ] Run the complete deterministic suite and ContextCanon consistency check.
- [ ] Keep the review PR unmerged until explicit owner approval.

Checkpoint: focused real-Git tests pass for ordinary branch switching, linked worktree discovery, cross-worktree concurrent numbering, legacy config migration, tracked-Issue refusal, and the CLI create/list/view slice. Full owner suite + ContextCanon regeneration/check remain the merge-gate steps.

Exit: one Git repository has one visible local Issue backlog and one number allocator regardless of which ordinary branch/worktree invokes `github-local`.
