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

- **Prefer editable installs for owner testing:** For active development, clone the repository once, install with `uv tool install --editable .`, and test new versions after `git pull` without reinstalling.
  Why: this is the project owner's preferred fast feedback loop for repeatedly testing development versions.
  <!-- ctx:rule id="GHLR-005" -->

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
