# Architecture

## CLI-first provider boundary

```text
Copilot / LLM / human
        ├── filesystem + PowerShell + git  → optional code state
        └── github-local CLI               → workflow objects
                                               └── explicit local Issue repositories
```

The MVP uses the native `github-local` command while retaining GitHub-shaped vocabulary. This is a provider runtime, not a ContextCanon subsystem. The durable ownership boundary is maintained in [Project Context](../CONTEXT.md).

## Client and layer decision

The measured official `gh` Issue path requires a substantially larger GitHub Enterprise-shaped HTTPS and GraphQL surface than the first local slice. The native CLI therefore remains primary, with future adapters isolated from the application service and canonical Issue files. Maintained boundaries are in [Project Context](../CONTEXT.md); detailed measurements and the reproducible trace remain in `gh-compatibility.md` and `../spike/`.



## Local Issue repositories versus Git repositories

The durable Issue boundary is declared by `github-local issue init`, not by `.git`.

A local Issue repository is a GitHub-like unit of workflow ownership: it has its own visible `issues/` store, number space, stable repository identity, and later can carry its own external Jira/Bitbucket mapping. These boundaries may be nested and may exist with no Git at all.

Git remains a separate code-state boundary. One Git repository may therefore contain multiple local Issue repositories. This avoids nested-Git complexity while preserving the user-facing property that a company, product, or independently managed extension can each show only its own backlog.

Ordinary Issue commands require explicit `-R/--repo` selection. This is not merely CLI ergonomics: it prevents both humans and LLM agents from silently filing work into the wrong backlog because their current directory was not what they assumed.

## Validated agent integration

A real corporate Copilot session without MCP successfully used the CLI and native Git. This validates the intended terminal-first split; the maintained agent contract and validation status are in [Project Context](../CONTEXT.md), with detailed evidence in `agent-validation.md`.

## Git-native Change links

Change ↔ Issue linking adds workflow semantics around native Git rather than a second Change-history store.

`github-local issue develop -R <path> <number>` requires the selected local Issue repository to be inside Git. The first-class branch relation stores both the stable local repository ID and the Issue number in Git branch configuration. Branch heads, commits, diffs, renames and deletion remain Git-owned.

This composite relation is necessary because several local Issue repositories inside one Git repository may legitimately contain the same Issue number. Generated branch names for nested repositories therefore include the local repository name as a collision-resistant human hint.

Historical number-only branch metadata and `issue-N-...` convention fallback remain compatible only for an Issue repository at the Git root; github.local never guesses that such an ambiguous legacy relation belongs to a nested repository.

This deliberately avoids copying Git state into Markdown, SQLite or another Change database.
