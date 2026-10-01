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

## Git-native Change links

Change ↔ Issue linking adds workflow semantics around native Git rather than a second Change-history store.

`github-local issue develop <number>` creates or adopts a normal local Git branch. The first-class relation is stored as one branch-config value (`github-local-issue`) in the repository's shared Git configuration. Branch heads, commits, diffs, renames and deletion remain Git-owned.

`github-local issue changes <number>` enumerates live local refs and returns branch name, current head SHA, current-worktree status and relation source. Explicit branch metadata is authoritative; the historical `issue-N-...` naming convention remains a read-only fallback for compatibility until that branch is adopted through `issue develop`.

This deliberately avoids copying Git state into Markdown, SQLite or another Change database.
