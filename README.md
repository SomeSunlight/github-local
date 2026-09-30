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

## Architecture

```text
Copilot / LLM / human
        ├── filesystem + PowerShell + git  → code state
        └── github-local CLI               → workflow objects
                                               └── issues/*.md
```

Native Git owns code state; `github-local` owns local workflow objects stored as visible files. The MVP uses a native CLI, while official-`gh` compatibility remains an optional measured adapter. Durable boundaries and the current decision are maintained in [Project Context](CONTEXT.md); protocol evidence remains in `docs/gh-compatibility.md` and `spike/`.

## Current status

The CLI-first Issue MVP is implemented and validated for humans and terminal-capable agents, including a real corporate Copilot test without MCP, which was successful. Detailed test evidence remains in `docs/agent-validation.md`.

## Installation

Python 3.11+ is required. `uv` is the recommended installer.

### Owner testing during development

For active development, clone the repository once and install the checkout **editable**:

```powershell
git clone https://github.com/SomeSunlight/github-local.git
cd github-local
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

## Daily Issue workflow

Initialize once from the branch that represents accepted work, normally `main`:

```powershell
github-local init --owner local --repo my-project
```

Then use the backlog directly:

```powershell
github-local issue create --title "Add validation" --body "Why this change is needed."
github-local issue list --state open
github-local issue view 1

github-local issue comment 1 --body "Implementation note."
github-local issue edit 1 --title "Add input validation"
github-local issue close 1
github-local issue reopen 1
```

When accepted Git history contains an explicit closing reference such as:

```text
Fixes #1
```

the next `github-local issue ...` command reconciles accepted history and closes that Issue automatically. A plain `#1` mention does not close it, and a closing reference on an unmerged feature branch has no effect until it reaches the configured accepted branch.

Use `github-local init --accepted-branch <branch>` when the accepted branch cannot be inferred correctly.

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
