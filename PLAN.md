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
- [x] After PR #2 is owner-approved and squash-merged, onboard `github-local` with ContextCanon and compose the reusable GitHub / Development Workflow context.
- [x] Resolve #3's branch/worktree semantics before expanding persisted workflow state.
- [x] Implement #4 immediately afterwards: complete the Issue lifecycle and automatic close for explicitly referenced accepted/merged work, before broader workflow testing.
- [x] Continue with #5 Change ↔ Issue linking.
- [x] Complete #13 GitHub CLI compatibility cleanup.
- [ ] Continue with #6 backlog filters, labels and search.
- [ ] Then continue with #7 concise CLI help examples.
- [ ] Re-evaluate #14 optional Issue scopes afterwards; it is no longer a blocker.

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

**Fast Track status — CLOSED**

Purpose: make one local Issue backlog authoritative across ordinary Git branches and linked worktrees without moving canonical Issue content into a database or making Git branches own workflow state.

- [x] Make all worktrees resolve one canonical visible `issues/` directory in the primary worktree.
- [x] Move runtime repository configuration and Issue locking onto the shared Git common directory so linked worktrees use one identity and one allocator.
- [x] Keep `issues/` outside ordinary branch tracking and add a shared Git exclude rule.
- [x] Fail clearly when tracked `issues/` would make project-wide semantics unsafe; do not silently rewrite the Git index.
- [x] Preserve existing Issue Markdown format, stable IDs, URLs, and monotonic numbering.
- [x] Add real-Git regression coverage for branch switches, linked worktrees, shared numbering, and tracked-Issue refusal.
- [x] Document the KISS storage semantics before Issue lifecycle expansion.
- [x] Run the complete deterministic suite and ContextCanon consistency check.
- [x] Keep Draft PR #10 unmerged until explicit owner approval.

Checkpoint: the owner ran the full deterministic suite successfully, regenerated ContextCanon output, and `contextcanon check --all .` passed. PR #10 was approved and squash-merged to `main` as `e8f546a`; Issue #3 was then closed manually because the PR body said `Implements #3` rather than a GitHub closing keyword.

Exit: one Git repository has one visible local Issue backlog and one number allocator regardless of which ordinary branch/worktree invokes `github-local`.


## Active Fast Track: complete the Issue lifecycle — Issue #4

**Fast Track status — CLOSED**

Purpose: make github.local useful for a real daily backlog: Issues can be edited, discussed, closed/reopened, filtered, and automatically leave the open backlog after accepted code reaches the configured accepted branch with an explicit closing reference.

- [x] Add explicit `issue close` and `issue reopen`.
- [x] Add `issue edit` for title/body while preserving Issue identity and comments.
- [x] Add durable visible Markdown comments with `issue comment`.
- [x] Add `issue list --state open|closed|all` while preserving the existing default.
- [x] Record one accepted branch per repository and reconcile explicit `Fixes/Closes/Resolves #N` references from that branch only.
- [x] Never auto-close from arbitrary mentions or unaccepted feature-branch commits.
- [x] Keep old config/Issue files backwards compatible and migration explicit.
- [x] Add focused real-Git lifecycle and auto-close regression tests.
- [x] Update README/storage docs for productive daily use.
- [x] Run the complete deterministic suite and ContextCanon build/check.
- [x] Keep Draft PR #11 unmerged until explicit owner approval; its body uses `Fixes #4` so GitHub should close Issue #4 automatically after merge.

Checkpoint: the owner ran the complete deterministic suite, regenerated ContextCanon output, and `contextcanon check --all .` passed. PR #11 was squash-merged to `main` as `1eabd3d`. Because its PR body used `Fixes #4`, GitHub automatically closed Issue #4 as intended.

Exit: create → edit/comment → close/reopen → state-filter → merge-with-closing-reference works with one visible project-wide backlog.


## Active Fast Track: first-class Change ↔ Issue links — Issue #5

**Fast Track status — CLOSED**

Purpose: replace the temporary naming-only convention with a tiny machine-readable layer around native Git branches, without duplicating commits, diffs, branch heads, or merge state.

- [x] Add `issue develop <number>` to create/switch to a conventional development branch from the accepted branch.
- [x] Record the Issue relation as branch-local Git metadata rather than a separate Change history store.
- [x] Reuse/adopt an existing conventional branch when safe and reject a branch already linked to another Issue.
- [x] Add `issue changes <number>` with stable human and JSON output derived from live Git refs.
- [x] Preserve compatibility with legacy `issue-N-...` branches by deriving a convention link when explicit metadata is absent.
- [x] Prove native `git branch -m` keeps the first-class link intact.
- [x] Keep linked-worktree behavior shared through the repository's common Git configuration.
- [x] Add focused real-Git and CLI regression tests.
- [x] Document the productive Issue → develop → commit → accepted-close workflow.
- [x] Run the complete deterministic suite and ContextCanon build/check.
- [x] Keep Draft PR #12 unmerged until explicit owner approval; its body uses `Fixes #5`.

Checkpoint: the owner ran the complete deterministic suite, regenerated ContextCanon output, and `contextcanon check --all .` passed. PR #12 was squash-merged to `main` as `a2ea817`; its `Fixes #5` reference automatically closed Issue #5.

Exit: an agent can create or discover the Git branch belonging to an Issue and inspect that relation cheaply as structured data, while Git remains authoritative for all code history.


## Active Fast Track: align Issue CLI with GitHub gh — Issue #13

**Fast Track status — CLOSED**

Purpose: make GitHub CLI vocabulary and behavior the default contract for every supported Issue capability; local deviations must be explicit and documented.

- [x] Replace local-only `issue changes <number>` with GitHub-compatible `issue develop --list <number>`.
- [x] Make `issue develop <number>` create/link without checkout by default; add GitHub-compatible `--checkout`.
- [x] Replace local `--branch` with GitHub-compatible `--name`.
- [x] Add GitHub-compatible `--base` using a local Git branch/ref as the base.
- [x] Make `issue list` default to open Issues and add the GitHub `issue ls` alias.
- [x] Make `issue view` show comments only with GitHub-compatible `--comments`.
- [x] Add low-cost `--comment` support to close/reopen where it maps directly to existing durable comments.
- [x] Audit/document the supported gh subset and every intentional github.local deviation.
- [x] Promote GitHub CLI compatibility to an explicit ContextCanon rule and route compatibility work to the current source-contract/trace evidence.
- [x] Add contributor documentation explaining source inspection vs black-box tracing and the evidence refresh workflow.
- [x] Update regression tests and daily-use documentation.
- [x] Run complete deterministic suite and ContextCanon build/check.
- [x] Keep Draft PR #15 unmerged until explicit owner approval; its body uses `Fixes #13`.

Checkpoint: the supported Issue surface follows current `gh` naming/defaults for develop/list/view/close/reopen; the owner completed the deterministic suite and ContextCanon checks, and PR #15 was squash-merged to `main` as `f22eab4`. Its `Fixes #13` reference closed Issue #13 automatically.

Exit: an LLM trained on ordinary `gh issue` commands encounters the same names/defaults for the subset github.local implements.

## Active Fast Track: backlog filters, labels and search — Issue #6

**Fast Track status — CLOSED**

Purpose: make a larger local backlog easy to discover without adding collaboration metadata, a database, or a hosted-search imitation.

- [x] Reconcile the post-#13 merge state and confirm #13 is closed.
- [x] Reframe #14 around one central Issue store plus optional explicit scope metadata; remove CWD-based store selection from the accepted direction.
- [x] Re-check current official `gh issue` vocabulary before adding flags.
- [x] Reduce #6 to the still-missing slice; state filtering already exists.
- [x] Add lightweight persistent labels while keeping existing schema-1 Issue files readable.
- [x] Add GitHub-compatible `issue create -l/--label`.
- [x] Add GitHub-compatible `issue edit --add-label/--remove-label`.
- [x] Add GitHub-compatible `issue list -l/--label` and `-S/--search`.
- [x] Add stable `labels` JSON output and concise human rendering.
- [x] Document deliberately smaller local search semantics and label representation.
- [x] Add focused storage/CLI regression coverage.
- [x] Run the complete deterministic suite and ContextCanon build/check.
- [x] Open Draft PR #16 with `Fixes #6`; keep it unmerged until explicit owner approval.

Checkpoint: the owner ran the complete deterministic suite successfully, regenerated ContextCanon output, and `contextcanon check --all .` passed. Two generated/context files missing from the first candidate were added by the owner before merge. PR #16 was squash-merged to `main` as `ba732c8`; its `Fixes #6` reference closed Issue #6 automatically.

Exit: an agent can classify and find a larger repository-local backlog with familiar `gh issue` flags while Markdown remains the sole canonical Issue truth.

## Active Fast Track: concise CLI examples — Issue #7

**Fast Track status — ACTIVE**

Purpose: reduce first-use trial-and-error for humans and terminal-capable agents without turning CLI help into a second README.

- [x] Reconcile the owner-tested/squash-merged #6 result on `main`.
- [x] Re-read the ContextCanon routes for agent-facing help/discovery and GitHub CLI compatibility.
- [x] Confirm current official `gh issue` help uses compact Examples sections.
- [ ] Add concise examples to top-level `github-local --help`.
- [ ] Add concise examples to `github-local issue --help`.
- [ ] Add focused examples to `issue create`, `issue list`, and `issue develop` help.
- [ ] Include structured `--json` examples for cheap agent inspection.
- [ ] Add regression tests that pin the examples to supported syntax.
- [ ] Update agent-validation documentation with the resolved #7 gap.
- [ ] Run the complete deterministic suite and ContextCanon build/check.
- [ ] Open a Draft PR with `Fixes #7` and keep it unmerged until explicit owner approval.

Exit: a new agent can infer the normal Issue workflow and the structured inspection path from one or two help surfaces instead of probing several commands.
