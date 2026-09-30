# github.local — Local Context Source
<!-- ctx:node id="66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2" name="github.local" version="0.1.1-draft" -->

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

## Local Rules

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

- **Keep Issue workflow state project-wide:** Ordinary Git branches/worktrees must not silently create divergent canonical backlogs or duplicate Issue identities/numbers.
  Why: Issues may exist long before implementation branches and represent project workflow state rather than one code branch.
  <!-- ctx:rule id="GHLR-006" -->

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

- **Keep Issue workflow state project-wide:** Ordinary Git branches and worktrees must not silently create divergent canonical backlogs or duplicate Issue identities or numbers.
  Why: Issues may predate implementation branches and represent project workflow state rather than one code branch.
  <!-- ctx:rule id="ONB-9FEE670D694B" -->

- **Let completed work leave the open backlog deliberately:** Provide explicit close and reopen semantics, and automatically close an Issue only when accepted or merged work carries an explicit closing reference.
  Why: The open backlog should shrink as accepted work completes while closure remains deliberate and inspectable; an arbitrary mention is not a closing instruction.
  <!-- ctx:rule id="ONB-D2571236E23F" -->

- **Mark Issue machine metadata explicitly:** Store each Issue as one Markdown file with a strict, delimited, machine-owned JSON front matter block; maintain its title and body once as Markdown.
  Why: Explicit metadata supports standard tooling without hiding parser semantics or duplicating human content.
  <!-- ctx:rule id="ONB-192F43493BCC" -->

- **Serialize numbering and write Issues atomically:** Allocate repository-local monotonically increasing Issue numbers under an OS-level exclusive lock and publish new content with a same-directory atomic replace.
  Why: Rapid or concurrent creation must not duplicate numbers, expose partial files, or leave stale process locks.
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

- **Treat Issue filenames as presentation:** Treat the numeric prefix and stable Issue ID as identity; the conservative Windows-safe filename slug is presentation and may change with the title.
  Why: A title edit must not change Issue identity or make discovery platform-dependent.
  <!-- ctx:rule id="ONB-9CD288976D1B" -->
<!-- contextcanon-placement-rules:end -->

## Local Topics

### Architecture and provider choice

When deciding between official `gh` compatibility and the native `github-local` CLI, or extending the runtime boundary:

Required:
- Resource: `docs/architecture.md`
- Resource: `docs/gh-compatibility.md`
<!-- ctx:topic id="GHLR-TOPIC-ARCH" -->

### Issue storage and CLI behavior

When changing Issue persistence, numbering, Markdown format, locking, atomic writes, or structured output:

Required:
- Resource: `docs/storage.md`
<!-- ctx:topic id="GHLR-TOPIC-ISSUES" -->

### Agent integration evidence

When changing the agent-facing CLI contract, help/discovery behavior, or deciding whether an adapter such as MCP is required:

Required:
- Resource: `docs/agent-validation.md`
<!-- ctx:topic id="GHLR-TOPIC-AGENT" -->

<!-- contextcanon-placement-topics:start -->
### Route official gh compatibility work

When evaluating official gh compatibility, changing host/protocol behavior, or reproducing the real-client trace:

Required:
- Resource: `docs/gh-compatibility.md`
  <!-- ctx:resource id="RESOURCE-9308EC2680A8" -->
- Resource: `spike/README.md`
  <!-- ctx:resource id="RESOURCE-E160697A4178" -->

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

## Sources

<!-- contextcanon-placement-sources:start -->
- [GitHub](contextcanon.yaml) — `0.1.3-draft`
  Why: Evidence explicitly says development of this public runtime project should use the reusable GitHub provider while its canonical remote is on github.com. This relationship is not among the already accepted STEP-07 assignments; Development Workflow is already assigned separately and is not re-emitted.
  <!-- ctx:source id="ccf4d7ee-4db1-4110-9ddc-5d70c69cf2bc" version="0.1.3-draft" normalized-digest="16a0e58a5881720e35b4b08456bc0bf6480b90464a56667f2b387e2199a4c2c1" package-digest="ebfc5ef834e4964de0611614fe2014be94968a1e51ff51c3925b29a45095ba6e" -->

- [Development Workflow](contextcanon.yaml) — `0.3.3-draft`
  Why: Use also here the same proven workflow as for the other projects
  <!-- ctx:source id="c4c94726-3cc7-4df6-b779-72bbf9c06f40" version="0.3.3-draft" normalized-digest="030956e2c3d141f213660871e4002f9045d7102f0482916f21d47493cd0a4934" package-digest="a2593ece6b5469a385c0b50898a9305565d4d8289453d08f5278e3fd40e66d27" -->
<!-- contextcanon-placement-sources:end -->
