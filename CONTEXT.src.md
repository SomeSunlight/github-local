# github.local — Local Context Source
<!-- ctx:node id="66c4d70e-e478-4cf2-8bf0-70aeb0ad30b2" name="github.local" version="0.1.1-draft" -->

## Local Overview

`github.local` is a deliberately small local development-workflow provider for projects where code and development history must remain local. Agents and humans should keep using the familiar vocabulary **Issue → branch → Pull Request → review → checks → merge**, while ordinary code work stays on the local filesystem and in native Git.

The first executable slice is intentionally CLI-first. It stores Issues as visible Markdown under `issues/` and does not require MCP, Docker, a browser UI, a cloud service, or a background daemon.

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
