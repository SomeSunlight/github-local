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

The current MVP is already useful as a local backlog: agents and humans can initialize a Git repository, create as many Issues as needed, list them cheaply, and reload the canonical Markdown after a new shell/process. It does **not** yet claim the complete development lifecycle. `issue close/edit/comment` and explicit machine-readable Change ↔ Issue links are the next small slices. Ordinary Git branch and commit naming can carry the Issue number immediately.

## Installation

Python 3.11+ is required. `uv` is the recommended installer.

### From GitHub

While the first candidate is still in Draft PR #2, install the review branch explicitly:

```powershell
uv tool install git+https://github.com/SomeSunlight/github-local.git@issue-1-cli-first-mvp
github-local --help
```

After the candidate is owner-approved and merged, the normal installation becomes:

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

## First-use smoke assignment

Use a disposable Git repository first. This deliberately tests both a current work item and a backlog created before implementation:

```powershell
mkdir github-local-smoke
cd github-local-smoke
git init

github-local init --owner local --repo smoke
github-local issue create --title "Prove the local Issue workflow" --body "Create one Git change linked by branch and commit naming."
github-local issue create --title "Add issue close" --body "Backlog only; do not implement during this smoke test."
github-local issue create --title "Add explicit change links" --body "Backlog only; later make Change <-> Issue links machine-readable."

github-local issue list
github-local issue list --json number,title,state,path
github-local issue view 1

git switch -c issue-1-smoke-workflow
"github.local smoke passed" | Set-Content SMOKE.md
git add SMOKE.md issues .github-local/config.json
git commit -m "docs: prove local Issue workflow (#1)"
```

Expected result: three ordinary Markdown Issue files exist below `issues/`; Issues #2 and #3 remain a visible backlog; the Git branch and commit visibly reference Issue #1. Closing #1 is intentionally not part of v0.1.0 yet.

For an automated implementation smoke test of the installed source tree, run `scripts/smoke.ps1`.

## Project documentation

- `PLAN.md` — active/recoverable work block
- `STATE.md` — current architecture and implementation checkpoint
- `docs/gh-compatibility.md` — measured current `gh` contract and decision evidence
- `docs/architecture.md` — product boundary and layers
- `docs/storage.md` — canonical Issue format and safety model
- `spike/README.md` — reproduce the `gh` protocol trace with a real current CLI
