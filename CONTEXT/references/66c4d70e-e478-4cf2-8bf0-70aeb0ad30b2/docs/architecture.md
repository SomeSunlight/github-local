# Architecture

## CLI-first provider boundary

```text
Copilot / LLM / human
        ├── filesystem + PowerShell + git  → code state
        └── github-local CLI               → workflow objects in visible repository files
```

The MVP uses the native `github-local` command while retaining GitHub-shaped vocabulary. This is a provider runtime, not a ContextCanon subsystem. The durable ownership boundary is maintained in [Project Context](../CONTEXT.md).

## Client and layer decision

The measured official `gh` Issue path requires a substantially larger GitHub Enterprise-shaped HTTPS and GraphQL surface than the first local slice. The native CLI therefore remains primary, with future adapters isolated from the application service and canonical Issue files. Maintained boundaries are in [Project Context](../CONTEXT.md); detailed measurements and the reproducible trace remain in `gh-compatibility.md` and `../spike/`.


## Validated agent integration

A real corporate Copilot session without MCP successfully used the CLI and native Git. This validates the intended terminal-first split; the maintained agent contract and validation status are in [Project Context](../CONTEXT.md), with detailed evidence in `agent-validation.md`.

## Next architecture boundary

Before adding richer mutable Issue state, define how the canonical project-wide backlog remains consistent across ordinary Git branches/worktrees (#3). Immediately after that, complete the Issue lifecycle and automatic closure of explicitly referenced accepted work (#4). Change ↔ Issue linking (#5) should add workflow semantics around native Git rather than duplicate Git state.
