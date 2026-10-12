# github.local — Local Context Source
<!-- ctx:node id="66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2" name="github.local" version="0.1.14-draft" -->

<!-- contextcanon:format Node
Format: Node metadata follows the # title: ctx:node id="..." name="..." version="...". Preserve existing identity.
Details: CONTEXT-format.md
-->

<!-- contextcanon:source-help:intro:start -->
Edit this local Context source; ContextCanon generates CONTEXT.md from it.
Some sections use a strict syntax. The comments below show the expected format.
New Rules, Topics and Resources receive IDs automatically during build; preserve existing IDs.
See [the source format guide](CONTEXT-format.md) for examples and editing instructions.
<!-- contextcanon:source-help:intro:end -->

## Context Imports

<!-- contextcanon:format Context Imports
Format: - [Name](location) — `version` — `relationship=parent|reference`; optional indented Why:, then ctx:source metadata. Preserve exact pins; use source list/adopt/update for package identity.
Details: CONTEXT-format.md
-->

<!-- contextcanon-placement-sources:start -->
- [GitHub](contextcanon.yaml) — `0.1.5-draft` — `relationship=parent`
  Why: Evidence explicitly says development of this public runtime project should use the reusable GitHub provider while its canonical remote is on github.com. This relationship is not among the already accepted STEP-07 assignments; Development Workflow is already assigned separately and is not re-emitted.
  <!-- ctx:source id="ccf4d7ee-4db1-4110-9ddc-5d70c69cf2bc" version="0.1.5-draft" normalized-digest="a2eccd94281c99f1dac2bad1a4379b1a5cb04cb58d52272a119f70a5563b5f65" package-digest="0292a626e9b4ec646623e678b0b681a4c9d14822121f161404f3bd5af35613dd" -->
<!-- contextcanon-placement-sources:end -->

## Local Overview

<!-- contextcanon:format Local Overview
Format: Ordinary Markdown orientation, local to this Node. Any existing placement identity follows its paragraph/item; do not change it.
Details: CONTEXT-format.md
-->

`github.local` is a deliberately small local development-workflow provider for projects where code and development history must remain local. Agents and humans should keep using the familiar vocabulary **Issue → branch → Pull Request → review → checks → merge**, while ordinary code work stays on the local filesystem and in native Git.

The first executable slice is intentionally CLI-first. It stores Issues as visible Markdown under `issues/` and does not require MCP, Docker, a browser UI, a cloud service, or a background daemon.

<!-- contextcanon-placement-overview:start -->
- github.local is a deliberately small local development-workflow provider for projects where code and development history must remain local.
  <!-- cc:placement-overview id="ONB-573AFDCD2A2F" -->

- github.local supplies local workflow operations; it is a provider implementation, not a ContextCanon subsystem.
  <!-- cc:placement-overview id="ONB-D4E7F2562CC6" -->

- Agents and humans use the familiar vocabulary Issue → branch → Pull Request → review → checks → merge while ordinary code work stays in the local filesystem and native Git.
  <!-- cc:placement-overview id="ONB-FAE8EAE354F9" -->
<!-- contextcanon-placement-overview:end -->

## Local Rules

<!-- contextcanon:format Local Rules
Format: ### Group, then - **Title:** Statement, then indented Why: Rationale. build adds a missing ctx:rule ID after the entry; preserve existing IDs.
Details: CONTEXT-format.md
-->

- **Keep project truth visible:** Canonical Issue content lives in ordinary Markdown below `issues/`; caches or indexes may accelerate access later but must remain reconstructable.
  Why: development reasoning is durable project knowledge, not opaque runtime state.
  <!-- ctx:rule id="GHLR-001" -->

- **Use native Git for code state:** Use the local working tree and Git for branches, commits, diffs, and merges; do not proxy file operations through `github.local`.
  Why: Git already solves these concerns locally and is the most compatible surface for IDE agents.
  <!-- ctx:rule id="GHLR-002" -->

- **Never fall back to an external forge silently:** Unsupported or unavailable operations must fail explicitly instead of creating state on github.com or another provider.
  Why: privacy-sensitive projects must not leak workflow state or acquire a second accidental source of truth.
  <!-- ctx:rule id="GHLR-003" -->

- **Keep the CLI model-friendly:** Prefer stable command names, exit codes, and structured JSON output over interactive UI requirements.
  Why: terminal-capable LLM harnesses need a predictable low-overhead contract.
  <!-- ctx:rule id="GHLR-004" -->

- **Keep the CLI as the primary agent contract:** Terminal-capable agents must be able to perform the normal workflow through stable CLI commands and structured output; MCP or other adapters are optional additions, not prerequisites.
  Why: the real corporate Copilot owner test succeeded without MCP and demonstrated that CLI calls provide a simple, low-overhead integration surface.
  <!-- ctx:rule id="GHLR-005" -->

- **Default to GitHub CLI compatibility:** For capabilities that github.local supports, prefer official `gh` command vocabulary, flags, aliases, and user-facing defaults wherever they map cleanly to the local architecture; every deliberate deviation must be explicit, documented, and justified.
  Why: humans and LLMs already trained on GitHub should be able to transfer that knowledge directly instead of learning accidental local syntax.
  <!-- ctx:rule id="GHLR-008" -->

- **Make local Issue repositories explicit workflow boundaries:** A folder owns an Issue backlog only after an explicit `github-local issue init`; local Issue-repository boundaries are independent of Git repository boundaries and may be nested.
  Why: A company, product, and independently managed extension can each be a GitHub-like unit of work without forcing nested Git repositories or mixing unrelated work into one label-heavy backlog.
  <!-- ctx:rule id="GHLR-009" -->

- **Require explicit Issue-repository selection for normal Issue work:** Issue commands must require `-R/--repo`; `-R .` explicitly asks github.local to resolve the nearest initialized local Issue repository from that location. Never select a repository merely because of the process CWD.
  Why: Humans and LLM agents both lose track of directory context. Making the target part of the command turns a likely silent misfile into an explicit decision that is visible in logs and prompts.
  <!-- ctx:rule id="GHLR-010" -->

- **Keep each local Issue repository an explicit, movable workflow boundary:** Each initialized folder owns a visible `issues/` store, its stable path-independent workflow repository ID, and local configuration. Inside Git, all nested Issue repositories share a short-number series per containing Git repository; Git-free folders allocate locally.
  Why: Products and extensions remain independently identifiable for future external mappings, while one Git project provides short unambiguous Issue references.
  <!-- ctx:rule id="GHLR-011" -->

- **Keep destructive Issue administration explicit and CLI-owned:** Initialization, teardown, Issue deletion, and bulk deletion must be available through github.local; destructive operations require confirmation unless the caller explicitly opts out.
  Why: Users and agents should never need to discover and manipulate hidden implementation files, while visible Markdown Issues remain intentionally inspectable project artifacts.
  <!-- ctx:rule id="GHLR-012" -->

- **Couple Issue state to normal Git history:** In Git, canonical Issues, comments and durable configuration belong to the currently checked-out branch/worktree and must be commit/push/clone-able with ordinary Git; never redirect to the primary worktree or silently exclude canonical data from Git.
  Why: The meaning of an Issue evolves with the code and project's Context. A historical commit must reproduce the corresponding historical Issue state, with normal PyCharm/Git semantics.
  <!-- ctx:rule id="GHLR-006" -->

- **Separate immutable identity from short, human-readable identifiers:** Every new Issue and comment has a separately generated immutable UUID in marked front matter. Within one Git repository allocate monotonically increasing short Issue numbers using a shared local lock/cursor; independent offline clones may temporarily allocate equal numbers. Comment Markdown filenames must start with a sortable per-Issue sequence and readable summary; a short UUID suffix prevents parallel Git branches from overwriting each other's comments.
  Why: People communicate using `#33` and browse discussions using `0001`, `0002`, `0003`; opaque UUID-only filenames and randomly ordered comments destroy that human workflow. The internal UUID, not the short display number, remains the technical identity.
  <!-- ctx:rule id="GHLR-013" -->

- **Diagnose and explicitly reconcile duplicate Issue numbers without guessing:** Duplicates may arise from independently numbered legacy subprojects being migrated into one Git repository or from ordinary Git merges of offline clones. Present a prominent actionable status and a human-readable list of the competing Issues. Block ambiguous writes and never select a keeper from arbitrary filename/path sorting; infer one only from unambiguous Git ancestry or explicit owner choice. Support owner-reviewed selection for multiple collisions, renumber losers to free integers only after confirmation, and preserve old numbers, dates, original paths and verified branch provenance in the affected Issues. Do not rewrite ambiguous text/commit/external references by guesswork.
  Why: A migration of legitimate older backlogs is not itself a Git conflict, and human-readable diagnostics plus deliberate keeper selection prevent silently changing the wrong Issue's identity or history.
  <!-- ctx:rule id="GHLR-014" -->

- **Keep lasting state Git-trackable and migrate legacy stores safely:** Use ordinary visible `.gitignore` only for locks/cursors/temporary files; never hide Issues or durable identity with `.git/info/exclude`. Provide a transparent, explicit legacy migration that preserves content and never stages/commits behind the user's back.
  Why: A user who commits/pushes the project must not silently lose hundreds of valuable Issues because a support tool kept them outside Git.
  <!-- ctx:rule id="GHLR-015" -->

- **Let completed work leave the open backlog:** Provide explicit close/reopen semantics and automatically close an Issue when accepted/merged work carries an explicit closing reference; do not treat an arbitrary Issue mention as a closing instruction.
  Why: the open backlog should naturally shrink as accepted work completes while closure remains deliberate and inspectable.
  <!-- ctx:rule id="GHLR-007" -->

<!-- contextcanon-placement-rules:start -->
### Onboarding placement

- **Use native Git for code state:** Use the local working tree and native Git for branches, commits, diffs, and merges; do not proxy file operations through github.local.
  Why: Git already owns code state locally and is the most compatible surface for IDE agents, while github.local owns workflow objects.
  <!-- ctx:rule id="ONB-B49912861E96" -->

- **Keep canonical Issue truth visible:** Keep canonical Issue content in ordinary Markdown below issues/; any cache or index must remain reconstructable.
  Why: Development reasoning is durable project knowledge, not opaque runtime state.
  <!-- ctx:rule id="ONB-C16E29C80641" -->

- **Never fall back to an external forge silently:** Unsupported or unavailable operations must fail explicitly instead of creating state on github.com or another provider.
  Why: Privacy-sensitive projects must not leak workflow state or acquire a second accidental source of truth.
  <!-- ctx:rule id="ONB-6A499DD99A1B" -->

- **Keep the CLI as the predictable primary agent contract:** Keep normal workflow available through discoverable stable CLI commands, explicit error exits, and structured JSON; MCP and other adapters are optional additions, not prerequisites.
  Why: Terminal-capable agents need a predictable low-overhead contract, and the target-environment owner test succeeded without MCP.
  <!-- ctx:rule id="ONB-F40586D91A16" -->

- **Keep workflow state coherent with its Git project snapshot:** Within a Git project, code and Issue Markdown follow ordinary branches/worktrees together. UUIDs never duplicate; short numbers are unique within each integrated checkout and exceptionally reconciled after a merge of independently numbered clones.
  Why: Historical code and its semantic Issue context must match. The earlier branch-independent backlog direction was explicitly superseded by owner decision in Issue #20.
  <!-- ctx:rule id="ONB-9FEE670D694B" -->

- **Let completed work leave the open backlog deliberately:** Provide explicit close and reopen semantics, and automatically close an Issue only when accepted or merged work carries an explicit closing reference.
  Why: The open backlog should shrink as accepted work completes while closure remains deliberate and inspectable; an arbitrary mention is not a closing instruction.
  <!-- ctx:rule id="ONB-D2571236E23F" -->

- **Mark Issue machine metadata explicitly:** Store each Issue as one Markdown file with a strict, delimited, machine-owned JSON front matter block; maintain its title and body once as Markdown.
  Why: Explicit metadata supports standard tooling without hiding parser semantics or duplicating human content.
  <!-- ctx:rule id="ONB-192F43493BCC" -->

- **Serialize shared local numbering and publish Issues atomically:** Allocate monotonically increasing Issue numbers per containing Git repository using a shared Git-local OS lock/cursor across local branches and worktrees; Git-free Issue repositories allocate locally. Publish content with same-directory atomic replacement.
  Why: Rapid local creation must not duplicate numbers or expose partial files; separately cloned offline histories can be reconciled after Git integration.
  <!-- ctx:rule id="ONB-47F89CA128E5" -->

- **Treat databases as rebuildable indexes:** If a database is added, use it only as an index or cache rebuildable from issues/ and Git state.
  Why: Canonical project truth must remain visible and reconstructable without opaque runtime state.
  <!-- ctx:rule id="ONB-8174142758A8" -->

- **Keep optional adapters outside canonical storage:** Build optional gh-compatible, MCP, IDE, or UI adapters on the same application service and canonical storage; adapter concerns must not contaminate Issue files.
  Why: Presentation and compatibility surfaces may evolve independently while durable project semantics remain stable.
  <!-- ctx:rule id="ONB-36E90990D445" -->

- **Keep repository discovery local:** Identify and configure the local project through repository discovery without network discovery.
  Why: The provider must remain usable as a local workflow surface without depending on a service or external host.
  <!-- ctx:rule id="ONB-62CF63BD255B" -->

- **Use immutable Issue IDs and human-friendly mutable numbers:** Each Issue's UUID is its sole permanent technical identity. Its short numeric filename prefix is a human communication handle, normally stable but exceptionally renumbered after a confirmed offline-merge collision; the Windows-safe slug is presentation and may change with the title.
  Why: Renumbering must preserve the underlying Issue and its historical discussion without changing identity.
  <!-- ctx:rule id="ONB-9CD288976D1B" -->
<!-- contextcanon-placement-rules:end -->

## Local Topics

<!-- contextcanon:format Local Topics
Format: ### Title, condition text, Required: and/or Optional:, then - Resource: `path` or - Context Node: `node-path`. Resource may have indented Why:. build adds missing Topic/Resource IDs after their entries; preserve existing IDs.
Details: CONTEXT-format.md
-->

### Architecture and provider choice

When deciding between official `gh` compatibility and the native `github-local` CLI, changing the supported CLI surface, reproducing the client protocol, or extending the runtime boundary:

Required:
- Resource: `docs/architecture.md`
  <!-- ctx:resource id="RESOURCE-6A7948522CB7" -->
- Resource: `docs/gh-compatibility.md`
  <!-- ctx:resource id="RESOURCE-9308EC2680A8" -->
- Resource: `CONTRIBUTING.md`
  <!-- ctx:resource id="RESOURCE-2E0E3666C830" -->
- Resource: `spike/README.md`
  <!-- ctx:resource id="RESOURCE-E160697A4178" -->
- Resource: `spike/gh-2.101.0-source-contract.json`
  <!-- ctx:resource id="RESOURCE-1D254EFEDCA3" -->
<!-- ctx:topic id="GHLR-TOPIC-ARCH" -->

### Issue storage and CLI behavior

When changing local Issue-repository boundaries or selection, Issue persistence, numbering, Markdown format, locking, atomic writes, deletion, or structured output:

Required:
- Resource: `docs/storage.md`
  <!-- ctx:resource id="RESOURCE-AE1A0D0EF341" -->
<!-- ctx:topic id="GHLR-TOPIC-ISSUES" -->

### Agent integration evidence

When changing the agent-facing CLI contract, help/discovery behavior, or deciding whether an adapter such as MCP is required:

Required:
- Resource: `docs/agent-validation.md`
  <!-- ctx:resource id="RESOURCE-18D65FB143AD" -->
<!-- ctx:topic id="GHLR-TOPIC-AGENT" -->

<!-- contextcanon-placement-topics:start -->
### Route official gh compatibility work

When evaluating official gh compatibility, changing the supported CLI surface, changing host/protocol behavior, or reproducing the real-client trace:

Required:
- Resource: `docs/gh-compatibility.md`
  <!-- ctx:resource id="RESOURCE-9308EC2680A8" -->
- Resource: `CONTRIBUTING.md`
  <!-- ctx:resource id="RESOURCE-2E0E3666C830" -->
- Resource: `spike/README.md`
  <!-- ctx:resource id="RESOURCE-E160697A4178" -->
- Resource: `spike/gh-2.101.0-source-contract.json`
  <!-- ctx:resource id="RESOURCE-1D254EFEDCA3" -->

<!-- ctx:topic id="ONB-1DE6FDEDE8CF" -->

### Route Issue storage work

When changing Issue persistence, numbering, Markdown format, locking, atomic writes, identity, indexes, or structured metadata:

Required:
- Resource: `docs/storage.md`
  <!-- ctx:resource id="RESOURCE-AE1A0D0EF341" -->

<!-- ctx:topic id="ONB-AE22D5D54F87" -->

### Route agent integration evidence

When changing the agent-facing CLI contract, help and discovery behavior, structured output, or deciding whether an adapter such as MCP is required:

Required:
- Resource: `docs/agent-validation.md`
  <!-- ctx:resource id="RESOURCE-18D65FB143AD" -->

<!-- ctx:topic id="ONB-B06387F8E1D0" -->

### Route installation and smoke testing

When installing github.local, running owner acceptance checks, or reproducing the manual, Git-reference, LLM, or automated smoke tests:

Required:
- Resource: `README.md`
  <!-- ctx:resource id="RESOURCE-00215E4157B3" -->

<!-- ctx:topic id="ONB-C31D33B512BF" -->
<!-- contextcanon-placement-topics:end -->

## Local State

<!-- contextcanon:format Local State
Format: Ordinary Markdown describing the current local situation. Any existing placement identity follows its paragraph/item; preserve it.
Details: CONTEXT-format.md
-->

<!-- contextcanon-placement-state:start -->
- The MVP uses the native github-local CLI; official gh remains a measured optional future adapter.
  <!-- cc:placement-state id="ONB-0CFB25FEF085" -->

- The last documented check used gh 2.101.0, whose alternate-host Issue operations require GitHub Enterprise-shaped HTTPS, feature detection, and GraphQL behavior; binary execution was not available in the inspection environment.
  <!-- cc:placement-state id="ONB-C7397BA8C299" -->

- github-local init creates repository-local configuration.
  <!-- cc:placement-state id="ONB-2A0D9DB9CE94" -->

- The executable runtime currently supplies Issues; Pull Request, review, and checks operations remain future slices.
  <!-- cc:placement-state id="ONB-0FA4677C99F9" -->

- issue create writes one canonical Markdown Issue atomically.
  <!-- cc:placement-state id="ONB-7594DA134D05" -->

- issue list and issue view reload canonical state from disk, including after restart.
  <!-- cc:placement-state id="ONB-8A039C0E8489" -->

- The CLI provides stable selected-field --json output for agent use.
  <!-- cc:placement-state id="ONB-D64F234D9DFB" -->

- The installable wheel has no runtime dependencies.
  <!-- cc:placement-state id="ONB-CC5013E28126" -->

- The frozen candidate passes all 12 deterministic tests.
  <!-- cc:placement-state id="ONB-EB8702686598" -->

- Python compilation passes for the frozen candidate.
  <!-- cc:placement-state id="ONB-F8D077AA9B38" -->

- The wheel builds successfully for the frozen candidate.
  <!-- cc:placement-state id="ONB-2388F784A444" -->

- An installed-wheel smoke test completes init → create → list → view in a fresh Git repository.
  <!-- cc:placement-state id="ONB-867FF7195FBD" -->

- Manual testing and a corporate GitHub Copilot test with Claude Sonnet 5 (Medium, 264k context) succeeded without MCP, validating the CLI as a practical agent integration surface.
  <!-- cc:placement-state id="ONB-AC230FD47742" -->

- Open question: How should the canonical project-wide Issue backlog remain consistent across ordinary Git branches and worktrees?
  <!-- cc:placement-unresolved id="ONB-54373873C2CE" -->

- Assignees and milestones remain out of scope while the primary workflow is single-owner.
  <!-- cc:placement-state id="ONB-A0D4599D0703" -->

- The frozen snapshot contains authored root CONTEXT.src.md but no generated CONTEXT.md or accepted package state because the bootstrap environment lacked the contextcanon executable.
  <!-- cc:placement-state id="ONB-9D51655FF5B4" -->

- v0.1.0 does not yet support close, reopen, edit, comments, or explicit machine-readable Change ↔ Issue links.
  <!-- cc:placement-state id="ONB-D72B21BFD852" -->
<!-- contextcanon-placement-state:end -->

### Maintained compatibility baseline

- The current measured GitHub CLI compatibility baseline is `gh 2.101.0`; supported native CLI parity and intentional deviations are maintained in `docs/gh-compatibility.md`.
  <!-- ctx:state id="GHLS-001" -->

- `spike/gh-2.101.0-source-contract.json` is the machine-readable source-inspection snapshot for that baseline. It explicitly records that the original environment did not execute a real `gh` binary.
  <!-- ctx:state id="GHLS-002" -->

- `spike/gh_trace_server.py` plus `spike/README.md` provide the reproducible black-box harness for capturing real `gh` HTTP/GraphQL behavior against a small fake GitHub Enterprise-shaped endpoint.
  <!-- ctx:state id="GHLS-003" -->

## Local Plan

<!-- contextcanon:format Local Plan
Format: Ordinary Markdown describing intended local work. Any existing placement identity follows its paragraph/item; preserve it.
Details: CONTEXT-format.md
-->

<!-- contextcanon-placement-plan:start -->
- Implement #4 next: close, reopen, edit, comment, state filtering, and automatic closure for accepted or merged work carrying an explicit closing reference.
  <!-- cc:placement-plan id="ONB-23D6597B221C" -->

- Implement #5 first-class Change ↔ Issue linking around native Git without duplicating Git state.
  <!-- cc:placement-plan id="ONB-F5537BFB06ED" -->

- Implement #6 backlog filters, labels, and search after Change ↔ Issue linking.
  <!-- cc:placement-plan id="ONB-CE7AE84864D9" -->

- Implement #7 concise examples in CLI help.
  <!-- cc:placement-plan id="ONB-233538BB01FB" -->

- After PR #2 is accepted and squash-merged, complete ContextCanon onboarding and compose the reusable GitHub provider and Development Workflow Source before the next product implementation block.
  <!-- cc:placement-plan id="ONB-95C18B6F9F9A" -->
<!-- contextcanon-placement-plan:end -->
