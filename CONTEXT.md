# github.local — Official Context

> [!CAUTION]
> **GENERATED FILE — DO NOT EDIT.**
> This is the compact official entry for this Context Node.
> Together with `CONTEXT/` it forms the human/agent-facing Official Context Package.
>
> Edit [CONTEXT.src.md](CONTEXT.src.md) instead.

**Node:** github.local  
**Context version:** `0.1.10-draft`

**Resulting imported Contexts:**

- **Development Workflow** — `0.3.5-draft` — via Source **GitHub** — [inspect accepted carrier](.context/sources/0292a626e9b4ec646623e678b0b681a4c9d14822121f161404f3bd5af35613dd/CONTEXT.md)
- **GitHub** — `0.1.5-draft` — direct Source — Why: Evidence explicitly says development of this public runtime project should use the reusable GitHub provider while its canonical remote is on github.com. This relationship is not among the already accepted STEP-07 assignments; Development Workflow is already assigned separately and is not re-emitted. — [inspect accepted carrier](.context/sources/0292a626e9b4ec646623e678b0b681a4c9d14822121f161404f3bd5af35613dd/CONTEXT.md)

## Local Overview

`github.local` is a deliberately small local development-workflow provider for projects where code and development history must remain local. Agents and humans should keep using the familiar vocabulary **Issue → branch → Pull Request → review → checks → merge**, while ordinary code work stays on the local filesystem and in native Git.

The first executable slice is intentionally CLI-first. It stores Issues as visible Markdown under `issues/` and does not require MCP, Docker, a browser UI, a cloud service, or a background daemon.

<!-- contextcanon-placement-overview:start -->
<!-- cc:placement-overview id="ONB-573AFDCD2A2F" -->
- github.local is a deliberately small local development-workflow provider for projects where code and development history must remain local.

<!-- cc:placement-overview id="ONB-D4E7F2562CC6" -->
- github.local supplies local workflow operations; it is a provider implementation, not a ContextCanon subsystem.

<!-- cc:placement-overview id="ONB-FAE8EAE354F9" -->
- Agents and humans use the familiar vocabulary Issue → branch → Pull Request → review → checks → merge while ordinary code work stays in the local filesystem and native Git.
<!-- contextcanon-placement-overview:end -->

## Local State

<!-- contextcanon-placement-state:start -->
<!-- cc:placement-state id="ONB-0CFB25FEF085" -->
- The MVP uses the native github-local CLI; official gh remains a measured optional future adapter.

<!-- cc:placement-state id="ONB-C7397BA8C299" -->
- The last documented check used gh 2.101.0, whose alternate-host Issue operations require GitHub Enterprise-shaped HTTPS, feature detection, and GraphQL behavior; binary execution was not available in the inspection environment.

<!-- cc:placement-state id="ONB-2A0D9DB9CE94" -->
- github-local init creates repository-local configuration.

<!-- cc:placement-state id="ONB-0FA4677C99F9" -->
- The executable runtime currently supplies Issues; Pull Request, review, and checks operations remain future slices.

<!-- cc:placement-state id="ONB-7594DA134D05" -->
- issue create writes one canonical Markdown Issue atomically.

<!-- cc:placement-state id="ONB-8A039C0E8489" -->
- issue list and issue view reload canonical state from disk, including after restart.

<!-- cc:placement-state id="ONB-D64F234D9DFB" -->
- The CLI provides stable selected-field --json output for agent use.

<!-- cc:placement-state id="ONB-CC5013E28126" -->
- The installable wheel has no runtime dependencies.

<!-- cc:placement-state id="ONB-EB8702686598" -->
- The frozen candidate passes all 12 deterministic tests.

<!-- cc:placement-state id="ONB-F8D077AA9B38" -->
- Python compilation passes for the frozen candidate.

<!-- cc:placement-state id="ONB-2388F784A444" -->
- The wheel builds successfully for the frozen candidate.

<!-- cc:placement-state id="ONB-867FF7195FBD" -->
- An installed-wheel smoke test completes init → create → list → view in a fresh Git repository.

<!-- cc:placement-state id="ONB-AC230FD47742" -->
- Manual testing and a corporate GitHub Copilot test with Claude Sonnet 5 (Medium, 264k context) succeeded without MCP, validating the CLI as a practical agent integration surface.

<!-- cc:placement-unresolved id="ONB-54373873C2CE" -->
- Open question: How should the canonical project-wide Issue backlog remain consistent across ordinary Git branches and worktrees?

<!-- cc:placement-state id="ONB-A0D4599D0703" -->
- Assignees and milestones remain out of scope while the primary workflow is single-owner.

<!-- cc:placement-state id="ONB-9D51655FF5B4" -->
- The frozen snapshot contains authored root CONTEXT.src.md but no generated CONTEXT.md or accepted package state because the bootstrap environment lacked the contextcanon executable.

<!-- cc:placement-state id="ONB-D72B21BFD852" -->
- v0.1.0 does not yet support close, reopen, edit, comments, or explicit machine-readable Change ↔ Issue links.
<!-- contextcanon-placement-state:end -->

### Maintained compatibility baseline

- The current measured GitHub CLI compatibility baseline is `gh 2.101.0`; supported native CLI parity and intentional deviations are maintained in `docs/gh-compatibility.md`.
  <!-- ctx:state id="GHLS-001" -->

- `spike/gh-2.101.0-source-contract.json` is the machine-readable source-inspection snapshot for that baseline. It explicitly records that the original environment did not execute a real `gh` binary.
  <!-- ctx:state id="GHLS-002" -->

- `spike/gh_trace_server.py` plus `spike/README.md` provide the reproducible black-box harness for capturing real `gh` HTTP/GraphQL behavior against a small fake GitHub Enterprise-shaped endpoint.
  <!-- ctx:state id="GHLS-003" -->

## Local Plan

<!-- contextcanon-placement-plan:start -->
<!-- cc:placement-plan id="ONB-23D6597B221C" -->
- Implement #4 next: close, reopen, edit, comment, state filtering, and automatic closure for accepted or merged work carrying an explicit closing reference.

<!-- cc:placement-plan id="ONB-F5537BFB06ED" -->
- Implement #5 first-class Change ↔ Issue linking around native Git without duplicating Git state.

<!-- cc:placement-plan id="ONB-CE7AE84864D9" -->
- Implement #6 backlog filters, labels, and search after Change ↔ Issue linking.

<!-- cc:placement-plan id="ONB-233538BB01FB" -->
- Implement #7 concise examples in CLI help.

<!-- cc:placement-plan id="ONB-95C18B6F9F9A" -->
- After PR #2 is accepted and squash-merged, complete ContextCanon onboarding and compose the reusable GitHub provider and Development Workflow Source before the next product implementation block.
<!-- contextcanon-placement-plan:end -->

## How to use this context

Apply all Rules below to every task in this Node.

For the current task, evaluate each Topic condition. When one matches, read every **Required** target before continuing; read **Optional** targets only when useful.

## Rules from Development Workflow

### Recoverable planning

#### `CCW-010` — Back every change with an Issue

Before implementation, framework-context, or substantial documentation changes, ensure an Issue records why the change exists; it may be brief.

#### `CCW-001` — Plan a coherent change block before editing

Before starting a new coherent development block, record a short purpose and checklist in the project's durable planning surface; use `PLAN.md` when the project follows this workflow convention.

#### `CCW-002` — Checkpoint completed plan items immediately

When a listed step is actually complete, mark its `PLAN.md` checkbox `[x]` immediately rather than reconstructing completion at the end of a long session.

#### `CCW-003` — Keep recovery-critical knowledge in the repository

Put decisions, active constraints, accepted state, and next steps needed to resume work in repository documentation such as `PLAN.md`, `STATE.md`, or the project's equivalent rather than relying on chat history or model memory.

#### `CCW-007` — Resume recent explicit continuation without re-proving unchanged state

When the project owner resumes work after a short conversational interruption, explicitly says to continue, and reports no intervening repository changes, continue from the last established branch/PR state unless a repository operation gives evidence that it changed. Do not spend a new work cycle re-checking already established repository facts merely to prove that nothing happened.

### Transparent machine semantics

#### `CCW-012` — Mark machine-significant Markdown explicitly

When Markdown is also parsed, compiled, extracted, or otherwise given machine-significant meaning, every field or wording whose value affects machine semantics must live in an explicitly marked machine structure rather than being inferred from ordinary presentation prose. Keep that machine significance recognizable in rendered and review surfaces; rendering may style or summarize the control structure, but must not make the machine/human boundary indistinguishable.

### Proportional verification

#### `CCW-004` — Batch related edits before expensive final verification

For one coherent correction block, make the related authoring/code changes and run proportionate focused checks first; do not repeat the project's most expensive generated-output, integration, packaging, or full verification cycle after every micro-edit.

#### `CCW-009` — Use owner-approved Fast Track blocks without weakening the final gate

When the project owner explicitly approves a coherent implementation scope and says intermediate product review is unnecessary, mark the Fast Track as active in the durable PLAN with its scope and exit condition, keep recovery checkpoints and focused verification inside bounded work blocks, and defer repeated PR-description polish, full CI, generated-output regeneration, and other review ceremony until the coherent review candidate. When the Fast Track ends, record that closure before returning to ordinary review cadence.

#### `CCW-005` — Require exact-head green verification at the merge gate, not the first review gate

A coherent development block may be presented for project-owner review while understood and disclosed CI failures or generated drift remain. After explicit project-owner approval and before merging, require the exact current head to pass the project's complete merge-gate verification, including zero generated drift when generated canonical output is part of the project contract.

#### `CCW-013` — Prefer editable installs for repeated owner testing

When actively testing an installable Python tool from a development checkout, prefer one editable install (`uv tool install --editable .`) and pull subsequent revisions with Git rather than reinstalling each version, when the environment supports it.

#### `CCW-014` — Expose development provenance without micro-bumping releases

When an executable tool is tested from a changing Git checkout, keep its release version stable until a real release/version boundary, but make runtime version output identify the current VCS state with the branch/ref when available, commit identity, and dirty state. Treat the commit identity as authoritative and the branch/ref as human orientation; release artifacts without checkout metadata still report the canonical release version.

### Human review gate

#### `CCW-011` — Expand change scope explicitly

Applicable Context constrains a task; it does not silently expand its writable scope.

#### `CCW-006` — Do not merge without explicit project-owner approval

Keep a review PR or equivalent change set open until the project owner explicitly approves the reviewed result.

### Accepted baseline

#### `CCW-008` — Close the post-merge baseline checkpoint before new development

After a reviewed change is successfully merged into the accepted branch, reconcile the durable repository state that records the accepted baseline before starting the next coherent development block. Record the merge outcome in `PLAN.md`, update `STATE.md` or equivalent current-state documentation, and refresh README/CHANGELOG or review-status wording made stale by the merge when applicable.

## Rules from GitHub

### Development infrastructure

#### `GH-001` — Use GitHub development objects

Manage workflow Issues, Pull Requests, reviews, checks/CI status, and merge state in the project's GitHub repository. Branches and commits remain ordinary Git objects; when a capable local harness is available, edit and test the local working tree directly rather than treating GitHub file APIs as a substitute filesystem.

## Local Rules

### Rules

#### `GHLR-001` — Keep project truth visible

Canonical Issue content lives in ordinary Markdown below `issues/`; caches or indexes may accelerate access later but must remain reconstructable.

#### `GHLR-002` — Use native Git for code state

Use the local working tree and Git for branches, commits, diffs, and merges; do not proxy file operations through `github.local`.

#### `GHLR-003` — Never fall back to an external forge silently

Unsupported or unavailable operations must fail explicitly instead of creating state on github.com or another provider.

#### `GHLR-004` — Keep the CLI model-friendly

Prefer stable command names, exit codes, and structured JSON output over interactive UI requirements.

#### `GHLR-005` — Keep the CLI as the primary agent contract

Terminal-capable agents must be able to perform the normal workflow through stable CLI commands and structured output; MCP or other adapters are optional additions, not prerequisites.

#### `GHLR-008` — Default to GitHub CLI compatibility

For capabilities that github.local supports, prefer official `gh` command vocabulary, flags, aliases, and user-facing defaults wherever they map cleanly to the local architecture; every deliberate deviation must be explicit, documented, and justified.

#### `GHLR-006` — Keep Issue workflow state project-wide

Ordinary Git branches/worktrees must not silently create divergent canonical backlogs or duplicate Issue identities/numbers.

#### `GHLR-007` — Let completed work leave the open backlog

Provide explicit close/reopen semantics and automatically close an Issue when accepted/merged work carries an explicit closing reference; do not treat an arbitrary Issue mention as a closing instruction.

### Onboarding placement

#### `ONB-B49912861E96` — Use native Git for code state

Use the local working tree and native Git for branches, commits, diffs, and merges; do not proxy file operations through github.local.

#### `ONB-C16E29C80641` — Keep canonical Issue truth visible

Keep canonical Issue content in ordinary Markdown below issues/; any cache or index must remain reconstructable.

#### `ONB-6A499DD99A1B` — Never fall back to an external forge silently

Unsupported or unavailable operations must fail explicitly instead of creating state on github.com or another provider.

#### `ONB-F40586D91A16` — Keep the CLI as the predictable primary agent contract

Keep normal workflow available through discoverable stable CLI commands, explicit error exits, and structured JSON; MCP and other adapters are optional additions, not prerequisites.

#### `ONB-9FEE670D694B` — Keep Issue workflow state project-wide

Ordinary Git branches and worktrees must not silently create divergent canonical backlogs or duplicate Issue identities or numbers.

#### `ONB-D2571236E23F` — Let completed work leave the open backlog deliberately

Provide explicit close and reopen semantics, and automatically close an Issue only when accepted or merged work carries an explicit closing reference.

#### `ONB-192F43493BCC` — Mark Issue machine metadata explicitly

Store each Issue as one Markdown file with a strict, delimited, machine-owned JSON front matter block; maintain its title and body once as Markdown.

#### `ONB-47F89CA128E5` — Serialize numbering and write Issues atomically

Allocate repository-local monotonically increasing Issue numbers under an OS-level exclusive lock and publish new content with a same-directory atomic replace.

#### `ONB-8174142758A8` — Treat databases as rebuildable indexes

If a database is added, use it only as an index or cache rebuildable from issues/ and Git state.

#### `ONB-36E90990D445` — Keep optional adapters outside canonical storage

Build optional gh-compatible, MCP, IDE, or UI adapters on the same application service and canonical storage; adapter concerns must not contaminate Issue files.

#### `ONB-62CF63BD255B` — Keep repository discovery local

Identify and configure the local project through repository discovery without network discovery.

#### `ONB-9CD288976D1B` — Treat Issue filenames as presentation

Treat the numeric prefix and stable Issue ID as identity; the conservative Windows-safe filename slug is presentation and may change with the title.

## Topics from Development Workflow

### Executing a development block

When planning, resuming, checkpointing, reviewing, testing, finalizing, merging, or closing the accepted baseline for a coherent development block:

**Required**

- [`CONTEXT/references/c4c94726-3cc7-4df6-b779-72bbf9c06f40/nodes/library/development-workflow/docs/change-workflow.md`](CONTEXT/references/c4c94726-3cc7-4df6-b779-72bbf9c06f40/nodes/library/development-workflow/docs/change-workflow.md)

### Implementing executable version identity

When adding or changing `--version`, package version lookup, or Git checkout provenance for an executable Python tool:

**Required**

- [`CONTEXT/references/c4c94726-3cc7-4df6-b779-72bbf9c06f40/nodes/library/development-workflow/docs/version-provenance-python.md`](CONTEXT/references/c4c94726-3cc7-4df6-b779-72bbf9c06f40/nodes/library/development-workflow/docs/version-provenance-python.md)

## Local Topics

### Architecture and provider choice

When deciding between official `gh` compatibility and the native `github-local` CLI, changing the supported CLI surface, reproducing the client protocol, or extending the runtime boundary:

**Required**

- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/architecture.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/architecture.md)
- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/gh-compatibility.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/gh-compatibility.md)
- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/CONTRIBUTING.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/CONTRIBUTING.md)
- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/spike/README.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/spike/README.md)
- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/spike/gh-2.101.0-source-contract.json`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/spike/gh-2.101.0-source-contract.json)

### Issue storage and CLI behavior

When changing Issue persistence, numbering, Markdown format, locking, atomic writes, or structured output:

**Required**

- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/storage.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/storage.md)

### Agent integration evidence

When changing the agent-facing CLI contract, help/discovery behavior, or deciding whether an adapter such as MCP is required:

**Required**

- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/agent-validation.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/agent-validation.md)

### Route official gh compatibility work

When evaluating official gh compatibility, changing the supported CLI surface, changing host/protocol behavior, or reproducing the real-client trace:

**Required**

- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/gh-compatibility.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/gh-compatibility.md)
- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/CONTRIBUTING.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/CONTRIBUTING.md)
- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/spike/README.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/spike/README.md)
- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/spike/gh-2.101.0-source-contract.json`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/spike/gh-2.101.0-source-contract.json)

### Route Issue storage work

When changing Issue persistence, numbering, Markdown format, locking, atomic writes, identity, indexes, or structured metadata:

**Required**

- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/storage.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/storage.md)

### Route agent integration evidence

When changing the agent-facing CLI contract, help and discovery behavior, structured output, or deciding whether an adapter such as MCP is required:

**Required**

- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/agent-validation.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/docs/agent-validation.md)

### Route installation and smoke testing

When installing github.local, running owner acceptance checks, or reproducing the manual, Git-reference, LLM, or automated smoke tests:

**Required**

- [`CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/README.md`](CONTEXT/references/66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2/README.md)
