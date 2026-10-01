# Current State

The first Fast Track implementation block is complete locally and remains backed by bootstrap Issue #1.

Architecture decision: **CLI-first native provider for the MVP**. Official `gh` remains a valuable vocabulary/reference and a possible later adapter, but current `gh` 2.101.0 Issue operations impose a GitHub Enterprise-shaped HTTPS/GraphQL contract that is disproportionate for the first local slice. See `docs/gh-compatibility.md` and `docs/architecture.md`.

The project owner has created `SomeSunlight/github-local` as the public development repository. The first verified candidate is being published there through GitHub Issue #1 and branch `issue-1-cli-first-mvp`. No merge is permitted without explicit project-owner approval.

## Implementation checkpoint

The v0.1.0 CLI implements repository initialization and the persisted Issue create → list → view slice, with structured JSON, safe visible-Markdown storage, and a dependency-free wheel. The deterministic suite covers restart, concurrent creation, UTF-8, Windows-safe filenames, corrupt metadata, stable error exits, JSON validation, and the trace server. Exact verification results, delivery status, and known gaps are maintained in [Project Context](CONTEXT.md).


## Real owner validation

The project owner completed both the manual and agent-facing smoke tests successfully.

The decisive agent test used corporate GitHub Copilot with Claude Sonnet 5 (Medium, 264k context) in an environment where MCP is administratively unavailable. The model was given terminal/filesystem/Git access and the documented `github-local` workflow. It successfully discovered the CLI, created/listed/viewed all three Issues, and completed the ordinary Git branch/commit steps. This validates CLI-first integration as a practical low-overhead tool surface for terminal-capable agents in the target environment.

The post-test LLM debrief confirmed that stable `--json`, clear failures, visible Markdown persistence and concise nested `--help` made the tool easy to use. It also identified the expected MVP gaps. One reported uncertainty was already implemented: `issue create --json ...` exists; the agent simply had not exercised it.

Follow-up work is recorded as:
- #3 project-wide Issue state across ordinary Git branches/worktrees;
- #4 close/reopen/edit/comment, state filtering, and early automatic close of accepted/merged work carrying an explicit closing reference;
- #5 first-class Change ↔ Issue linking;
- #6 backlog filters, labels and search;
- #7 concise CLI examples.

Assignees and milestones remain out of scope while the primary workflow is single-owner.

Before the next product implementation block, onboard this repository with ContextCanon and compose the reusable GitHub provider / Development Workflow for its public development workflow.


## Issue #8 — runtime development provenance candidate

PR #9 was owner-tested successfully and squash-merged to `main` as `14034cd`. `github-local --version` now implements CCW-014 while keeping release version `0.1.0` canonical only in `pyproject.toml`. Issue #8 is closed.


## Issue #3 — project-wide Issue state

The current MVP keeps `issues/` and its lock inside one worktree, so branch/worktree independence is not actually guaranteed. The accepted direction for #3 is one canonical visible Markdown backlog per Git repository: the primary worktree owns `issues/`; every linked worktree resolves that same directory; runtime config and locks live in the shared Git common directory; and `issues/` is excluded from ordinary branch tracking. If Issue files are already tracked, github.local must refuse unsafe project-wide operation and require an explicit migration rather than silently modifying the Git index.


PR #10 was owner-tested, ContextCanon-regenerated, approved, and squash-merged to `main` as `e8f546a`. Issue #3 is closed. One project-wide visible Issue backlog and shared allocator are now the accepted baseline.


## Issue #4 — lifecycle and accepted-change auto-close

The next product block completes everyday Issue handling. Manual close/reopen, title/body editing, visible comments, and state filtering remain explicit CLI operations. Auto-close will only interpret an explicit closing reference (`Fixes #N`, `Closes #N`, or `Resolves #N`) after that commit is reachable from the repository's configured accepted branch; feature-branch mentions or ordinary `#N` references do not close anything.


## Issue #4 implementation checkpoint

The review candidate now supports manual close/reopen, title/body edit with stable identity, visible Markdown comments under `issues/comments/<issue>/`, state-filtered listing, and automatic close from new commits reaching the configured accepted branch with explicit `Fixes/Closes/Resolves #N` references. A per-repository cursor in shared Git metadata prevents historical replay and preserves deliberate reopen behavior. The legacy tracked bootstrap Issue file was removed from the source tree so github.local can operate in its own repository under the accepted #3 semantics.

PR #11 was owner-tested, ContextCanon-regenerated, approved, and squash-merged to `main` as `1eabd3d`. Its `Fixes #4` PR-body reference automatically closed Issue #4, confirming the intended GitHub close workflow.


## Issue #5 — first-class Change ↔ Issue links

The next layer stays deliberately Git-native. A Change is represented by a normal Git branch plus one small branch-config relation to its local Issue. github.local does not copy commits, diffs, heads, or merge state. Conventional legacy branch names remain discoverable as a fallback; explicit links created by `issue develop` are first-class and machine-readable.


## Issue #5 implementation checkpoint

The review candidate adds `issue develop <number>` and `issue changes <number>`. A first-class link is one `github-local-issue` value in the normal Git branch configuration; live branch name/head/current-worktree status are always read from Git. Existing `issue-N-...` branches remain discoverable as convention links, and `issue develop` upgrades an adopted branch to an explicit relation. Native branch rename moves the config relation with the branch, so github.local does not need a parallel Change-history store.

PR #12 was owner-tested, ContextCanon-regenerated, approved, and squash-merged to `main` as `a2ea817`. Its `Fixes #5` reference automatically closed Issue #5.


## Issue #13 — GitHub CLI compatibility cleanup

GitHub CLI compatibility is now an explicit product rule: use official `gh issue` names, flags, aliases and defaults wherever they map cleanly to the local architecture. A smaller supported subset is acceptable; accidental syntax divergence is not. Local-only behavior must be documented together with the reason for the deviation. Issue #14 is no longer a blocker: if scopes are later needed, they must remain optional metadata over the one repository-wide Issue store and must not be selected implicitly from CWD.


## Issue #13 implementation checkpoint

The review candidate removes the local-only `issue changes` command in favor of GitHub-compatible `issue develop --list`, makes branch checkout opt-in through `--checkout`, adopts GitHub's `--name` and `--base` spellings, makes `issue list` default to open with alias `ls`, gates human comment rendering behind `view --comments`, and supports `--comment` on close/reopen. Intentional local extensions and unsupported GitHub-service features are recorded explicitly in `docs/gh-compatibility.md`.

PR #15 was owner-tested and squash-merged to `main` as `f22eab4`; its `Fixes #13` reference closed Issue #13 automatically.

The #13 candidate now also promotes GitHub CLI compatibility into authored ContextCanon policy (GHLR-008), routes compatibility work to `CONTRIBUTING.md`, `spike/README.md`, and `spike/gh-2.101.0-source-contract.json`, and documents how source-derived evidence differs from a real-client black-box trace.

## Issue #14 — optional Issue scopes

The previous nested-store/CWD design has been rejected. The accepted direction keeps one canonical repository-wide `issues/` store. A future scope, if productive use still justifies it, is optional metadata with stable path-independent identity; a movable marker may help resolve a scope, but ordinary Issue commands remain repository-wide unless scope assignment is explicit. Any future `--scope` syntax is a documented github.local extension rather than an accidental `gh` divergence.

#14 is deliberately deferred until after #6 and #7.


## Issue #6 — backlog filters, labels and search

State filtering and the open-by-default list behavior already exist, so #6 has been reduced to the missing backlog-discovery slice. The current official GitHub CLI names map cleanly: `issue create -l/--label`, `issue edit --add-label/--remove-label`, and `issue list -l/--label -S/--search`. The local implementation will keep label metadata lightweight and search deliberately smaller than GitHub's hosted advanced-search language.

Active review branch: `issue-6-backlog-labels-search`. Assignees, milestones, projects, a full label-management subsystem, and any database/index remain out of scope.

## Issue #6 implementation checkpoint

The Draft PR #16 candidate stores optional label-name arrays directly in existing schema-1 Issue front matter; legacy files without `labels` are read as unlabeled. The CLI now supports `create -l/--label`, `edit --add-label/--remove-label`, `list -l/--label`, `list -S/--search`, and stable `labels` JSON. Multiple requested labels use AND filtering. Local search is a case-insensitive substring scan over title, body and labels rather than GitHub's hosted advanced-search grammar; that deviation is documented in `docs/gh-compatibility.md`.

Focused storage/CLI regression tests were added, including legacy-file compatibility. The owner then ran the complete deterministic suite successfully, regenerated ContextCanon output, ran `contextcanon check --all .`, added two missing generated/context files, and committed the final candidate. PR #16 was squash-merged to `main` as `ba732c8`; its `Fixes #6` reference closed Issue #6 automatically.

## Issue #7 — concise CLI examples

The remaining owner-test gap is discoverability rather than capability. The real corporate Copilot test succeeded through nested `--help`, but explicitly reported the lack of concise examples. Current official `gh` help uses compact Examples sections, so github.local will follow the same presentation pattern without copying GitHub-only operations.

The focused slice adds examples to the top-level and `issue` help plus the syntax-heavy `create`, `list`, and `develop` subcommands. Simple lifecycle commands remain discoverable from their options alone. At least one `--json` example must remain visible because structured output is the primary cheap agent inspection path.

Active review branch: `issue-7-cli-help-examples`.

## Issue #7 implementation checkpoint

The candidate adds compact `Examples:` epilogs to `github-local --help`, `github-local issue --help`, and the `issue create`, `issue list`, and `issue develop` help surfaces. The examples use only supported github.local syntax, retain GitHub-shaped vocabulary, and expose structured `--json` inspection without duplicating the README. Simpler lifecycle subcommands deliberately remain option-list-only.

CLI regression coverage invokes each help surface without repository initialization and asserts the supported example commands remain present. `docs/agent-validation.md` records #7 as the direct resolution of the final help/discovery gap from the real Copilot debrief. Draft PR #17 contains the candidate with `Fixes #7` and remains unmerged pending the owner test plus ContextCanon gate.

