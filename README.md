# github.local

A small local GitHub-shaped development workflow for humans and terminal-capable LLM agents.

## Problem

In restricted corporate environments the agent may have a filesystem, PowerShell and Git but no approved MCP bridge and no external forge for confidential development state. Plain Git covers code history well; it does not by itself provide durable Issue/PR/review/check semantics.

## Goal

Preserve the familiar mental model:

```text
Issue → branch → Pull Request → review → checks → merge
```

while keeping project truth local, inspectable and useful without a service. The MVP starts with Issues as Markdown and a CLI that is cheap for an LLM to call.

## Non-goals

The MVP is not a GitHub clone, not a browser forge, not a ContextCanon subsystem, not an MCP requirement, and not a filesystem proxy. It does not silently mirror anything to github.com.

## Architecture hypothesis

```text
Copilot / LLM / human
        ├── filesystem + PowerShell + git  → code state
        └── github-local CLI               → workflow objects
                                               └── issues/*.md
```

The official GitHub CLI was investigated first. Current `gh` Issue operations are heavily GraphQL/GitHub-Enterprise-shaped and require HTTPS host semantics, so the first slice uses a native CLI with familiar command names instead. The measured contract and a reproducible trace harness remain in `docs/gh-compatibility.md` and `spike/`.

## Current status

The first Fast Track implementation block is complete. The native Issue create/list/view vertical slice is green; the official-`gh` compatibility path remains a measured optional adapter. The review candidate is intentionally unmerged until project-owner approval.

The current MVP is already useful as a local backlog: agents and humans can initialize a Git repository, create as many Issues as needed, list them cheaply, and reload the canonical Markdown after a new shell/process.

A real owner test inside corporate GitHub Copilot validated the central integration hypothesis: a terminal-capable LLM with no MCP access discovered and used the unfamiliar `github-local` CLI successfully, created/listed/viewed the local Issues, and performed the Git work using the documented branch/commit convention. The CLI itself is therefore a proven agent integration surface, not only a design hypothesis. See `docs/agent-validation.md`.

The current v0.1.0 slice does **not** yet claim the complete development lifecycle. The immediate roadmap is tracked in Issues #3–#7. In particular, Issue #4 makes close/reopen and automatic closing of accepted work an early core capability; Assignees and milestones remain deliberately out of scope while the primary workflow is single-owner.

## Installation

Python 3.11+ is required. `uv` is the recommended installer.

### Owner testing during development

For active development, clone the repository once and install the checkout **editable**:

```powershell
git clone https://github.com/SomeSunlight/github-local.git
cd github-local
git switch issue-1-cli-first-mvp
uv tool install --editable .
github-local --help
```

After that, new development versions normally require only:

```powershell
git pull
```

This is the preferred owner-test workflow while the project changes frequently.

### Normal installation after merge/release

For a stable merged version, direct installation from GitHub remains available:

```powershell
uv tool install git+https://github.com/SomeSunlight/github-local.git
```

### Offline / restricted network

Build or download the wheel on a machine that can access this repository, copy the wheel into the restricted environment, then install it locally:

```powershell
uv tool install .\github_local-0.1.0-py3-none-any.whl
github-local --help
```

No runtime dependency has to be downloaded after the wheel is present.

For development from a checkout without installing:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m github_local.cli --help
```

## First-use smoke tests

The first tests are intentionally split. You do **not** need to understand or inspect Git history just to prove that the local Issue provider works.

### 1. Manual Issue smoke test

Use a disposable Git repository:

```powershell
mkdir github-local-smoke
cd github-local-smoke
git init

github-local init --owner local --repo smoke

github-local issue create --title "Prove the local Issue workflow" --body "First manual smoke issue."
github-local issue create --title "Add issue close" --body "Backlog only; do not implement."
github-local issue create --title "Add explicit change links" --body "Backlog only; do not implement."

github-local issue list
github-local issue list --json number,title,state,path
github-local issue view 1
```

Expected result:

- three Markdown files exist below `issues/`;
- `github-local issue list` shows Issues #1, #2 and #3 as `OPEN`;
- opening the files in an editor shows the same titles and bodies.

That is all that **visible backlog** means here: Issues #2 and #3 exist as ordinary project files and remain `OPEN`. There is no hidden database state to inspect.

If this works, the core v0.1.0 owner smoke test has passed.

### 2. Optional Git-reference smoke test

This does **not** test extra github.local behavior yet. It only demonstrates the temporary convention for associating normal Git work with an Issue number until explicit Change ↔ Issue links are implemented.

```powershell
git switch -c issue-1-smoke-workflow
"github.local smoke passed" | Set-Content SMOKE.md
git add SMOKE.md
git commit -m "docs: prove local Issue workflow (#1)"

git branch --show-current
git log -1 --oneline
```

Expected result:

- the current branch name contains `issue-1`;
- the latest commit message contains `#1`.

No checkout comparison is required. github.local does not interpret this relationship in v0.1.0; it is only a visible human/agent convention for now.

### 3. LLM / Copilot smoke test

This is the more important agent-facing test. Give the following task to an LLM that can run terminal commands in a disposable Git repository:

> Use only the terminal, local files, Git and `github-local`. Do not create external GitHub Issues and do not use MCP.
>
> Initialize github.local in this repository. Create three local Issues: one small Issue that you will act on, plus two backlog Issues that you must not implement. List the Issues both normally and as JSON, then view Issue #1. Create a Git branch whose name contains `issue-1`, make one harmless small file change, and commit it with a message containing `#1`. At the end, show the Issue list, the files below `issues/`, the current branch name, and the latest commit.

The point of this test is not code quality. It checks whether a terminal-capable agent naturally understands and uses the `github-local` interface.

### 4. Developer automation: optional

`scripts/smoke.ps1` is an automated developer regression smoke test. It creates its own temporary repository and verifies init → create → list → view automatically.

If the manual smoke test above already passed, the project owner does **not** need to run `scripts/smoke.ps1` as an additional acceptance step.

## Project documentation

- `PLAN.md` — active/recoverable work block
- `STATE.md` — current architecture and implementation checkpoint
- `docs/gh-compatibility.md` — measured current `gh` contract and decision evidence
- `docs/architecture.md` — product boundary and layers
- `docs/storage.md` — canonical Issue format and safety model
- `docs/agent-validation.md` — real Copilot owner-test evidence and follow-up findings
- `spike/README.md` — reproduce the `gh` protocol trace with a real current CLI
