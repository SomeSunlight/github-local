# Architecture

## Decision: CLI-first, native provider first

The MVP uses a native command `github-local` instead of making the official GitHub CLI the mandatory front end. The vocabulary stays GitHub-shaped; the protocol does not have to be.

```text
Copilot / LLM / human
        │
        ├── filesystem + PowerShell + git
        │       └── working tree, branches, commits, diffs, merge
        │
        └── github-local CLI
                └── Issues now; PR/review/checks later
                        └── visible repository files
```

This is a provider implementation, not a ContextCanon subsystem. ContextCanon supplies project knowledge and the Development Workflow contract; `github.local` supplies the local workflow operations.

## Why not official `gh` as the mandatory MVP interface?

The current `gh` contract is perfectly reasonable for GitHub and GitHub Enterprise, but it is not small. For an alternative host, even the Issue slice combines enterprise-version probing, GraphQL schema/feature detection, repository lookup, and GraphQL mutations/queries. The newer `api_host` routing feature is useful for gateways, but still assumes HTTPS and a bare host rather than an arbitrary local HTTP endpoint.

Implementing that surface before the storage model exists would reverse the dependency: the local provider would be designed around compatibility with a large external client rather than around its own durable project semantics.

The compatibility spike is retained under `spike/` so the decision can be revisited with real `gh` traces. A future adapter can translate the official `gh` contract into the same storage/service layer without changing Issue files.

## Layers

1. **Repository discovery/config** — identifies the local project; no network discovery.
2. **Canonical storage** — Markdown Issues under `issues/`; atomic write + lock.
3. **Application service** — create/list/view operations independent of CLI presentation.
4. **CLI adapter** — model-friendly commands and JSON output.
5. **Optional future adapters** — `gh`-compatible HTTPS/GraphQL, MCP, IDE integration, or local web UI.

The first four layers are the MVP. Layer 5 must not contaminate canonical storage.


## Validated agent integration

The CLI-first boundary has been exercised in the target style of environment, not only unit-tested. A real corporate GitHub Copilot session without MCP access successfully discovered and operated `github-local` using terminal commands, structured JSON and native Git. This confirms the intended split:

- filesystem/shell/Git for code state;
- `github-local` CLI for workflow objects;
- adapters such as MCP remain optional convenience layers.

The result also reinforces a design constraint: keep commands discoverable, failures explicit and JSON stable rather than requiring an agent-specific protocol.

## Next architecture boundary

Before adding richer mutable Issue state, define how the canonical project-wide backlog remains consistent across ordinary Git branches/worktrees (#3). Immediately after that, complete the Issue lifecycle and automatic closure of explicitly referenced accepted work (#4). Change ↔ Issue linking (#5) should add workflow semantics around native Git rather than duplicate Git state.
