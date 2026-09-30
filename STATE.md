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
