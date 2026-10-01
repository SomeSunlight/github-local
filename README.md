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

Declare every folder that should own its own backlog:

```powershell
cd .\Product-A
github-local issue init --owner company --name product-a

cd .\Extension-X
github-local issue init --owner company --name extension-x
```

Git is optional for Issue storage. A company folder, product, and independently managed extension may each own a local Issue repository without creating nested Git repositories.

Normal Issue work always names the target repository explicitly. `-R .` means “the nearest explicitly initialized local Issue repository from here”:

```powershell
github-local issue create -R . --title "Add validation" --body "Why this change is needed." --label validation
github-local issue list -R . --state open
github-local issue list -R . --label validation
github-local issue list -R ..\..\Product-A --search "input validation"
github-local issue view -R . 1

github-local issue develop -R . 1 --checkout
github-local issue develop -R . --list 1 --json branch,head,current,relation

github-local issue comment -R . 1 --body "Implementation note."
github-local issue edit -R . 1 --title "Add input validation" --add-label ready
github-local issue close -R . 1
```

There is intentionally no implicit CWD fallback for ordinary Issue commands: omitting `-R/--repo` is an error. This makes the target visible to both humans and terminal-capable agents instead of silently filing an Issue in whichever directory happens to be current.

Each initialized folder owns its own `issues/` directory, Issue numbering, and stable path-independent repository identity. Moving that folder therefore moves its backlog as one unit. `github-local issue deinit -R .` removes an empty local Issue repository; `--delete-issues` makes teardown destructive and requires confirmation unless `--yes` is supplied. `github-local issue delete -R . --all` provides the same confirmation-protected bulk cleanup while keeping the repository initialized.

At a local Issue repository that is also the Git root, accepted Git history may use the usual unqualified closing form:

```text
Fixes #1
```

For a nested local Issue repository inside a larger Git repository, qualify the target just as GitHub does across repositories:

```text
Fixes company/extension-x#1
```

This prevents equal Issue numbers in sibling local repositories from being confused. A plain `#1` mention never closes anything.

Labels remain lightweight free-form names stored directly with the Issue. Repeating `--label` filters by all requested labels. Local `--search` is intentionally a case-insensitive substring search over title, body, and label names.

Use `github-local issue init --accepted-branch <branch>` when a containing Git repository exists but its accepted branch cannot be inferred correctly.

## First-use smoke tests

The first tests are intentionally split. You do **not** need to understand or inspect Git history just to prove that the local Issue provider works.

### 1. Manual Issue smoke test

Use a disposable Git repository:

```powershell
mkdir github-local-smoke
cd github-local-smoke
git init

github-local issue init --owner local --name smoke

github-local issue create -R . --title "Prove the local Issue workflow" --body "First manual smoke issue."
github-local issue create -R . --title "Add issue close" --body "Backlog only; do not implement."
github-local issue create -R . --title "Add explicit change links" --body "Backlog only; do not implement."

github-local issue list -R .
github-local issue list -R . --json number,title,state,path
github-local issue view -R . 1
```

Expected result:

- three Markdown files exist below `issues/`;
- `github-local issue list` shows Issues #1, #2 and #3 as `OPEN`;
- opening the files in an editor shows the same titles and bodies.

That is all that **visible backlog** means here: Issues #2 and #3 exist as ordinary project files and remain `OPEN`. There is no hidden database state to inspect.

If this works, the core v0.1.0 owner smoke test has passed.

### 2. Development-branch smoke test

Create the Git branch for Issue #1 through github.local:

```powershell
github-local issue develop -R . 1 --checkout
github-local issue develop -R . --list 1
github-local issue develop -R . --list 1 --json issue,branch,head,current,relation

"github.local smoke passed" | Set-Content SMOKE.md
git add SMOKE.md
git commit -m "docs: prove local Issue workflow (#1)"
```

Expected result:

- the conventional branch is created from the accepted branch and checked out because `--checkout` was requested;
- `issue develop --list 1` reports that branch as an explicit relation;
- the JSON form reports the live Git branch head rather than copied Change history.

The relation is stored as branch metadata in Git itself. Native `git branch -m` keeps the relation when the branch is renamed. Existing legacy branches named `issue-1-...` are still discoverable as convention-based links until adopted explicitly.

### 3. LLM / Copilot smoke test

This is the more important agent-facing test. Give the following task to an LLM that can run terminal commands in a disposable Git repository:

> Use only the terminal, local files, Git and `github-local`. Do not create external GitHub Issues and do not use MCP.
>
> Initialize a local Issue repository here with `github-local issue init`. Create three local Issues: one small Issue that you will act on, plus two backlog Issues that you must not implement. List the Issues both normally and as JSON, then view Issue #1. Use `github-local issue develop -R . 1 --checkout` to start the Change, inspect it with `github-local issue develop -R . --list 1 --json issue,branch,head,current,relation`, make one harmless small file change, and commit it with a message containing `#1`. At the end, show the Issue list, the linked branch, the files below `issues/`, the current branch name, and the latest commit.

The point of this test is not code quality. It checks whether a terminal-capable agent naturally understands and uses the `github-local` interface.

### 4. Developer automation: optional

`scripts/smoke.ps1` is an automated developer regression smoke test. It creates its own temporary repository and verifies init → create → list → view automatically.

If the manual smoke test above already passed, the project owner does **not** need to run `scripts/smoke.ps1` as an additional acceptance step.

## Project documentation

- `CONTRIBUTING.md` — contributor guide, including how `gh` compatibility is measured and updated
- `PLAN.md` — active/recoverable work block
- `STATE.md` — current architecture and implementation checkpoint
- `docs/gh-compatibility.md` — measured current `gh` contract and decision evidence
- `docs/architecture.md` — product boundary and layers
- `docs/storage.md` — canonical Issue format and safety model
- `docs/agent-validation.md` — real Copilot owner-test evidence and follow-up findings
- `spike/README.md` — reproduce the `gh` protocol trace with a real current CLI
