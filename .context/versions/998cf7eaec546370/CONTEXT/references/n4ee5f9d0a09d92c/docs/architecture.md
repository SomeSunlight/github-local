# Architecture

## CLI-first provider boundary

```text
Copilot / LLM / human
        ├── native filesystem + Git → code, branches, commits, merges, issue history
        └── github-local CLI        → local workflow operations over visible Markdown
                                       └── explicit nested Issue repositories
```

The CLI remains the primary interface for terminal-capable agents in restricted environments. A compatible implementation of the official `gh` protocol requires substantially more HTTPS/GraphQL infrastructure; it remains an optional future adapter. No external network or service is necessary.

## One ordinary Git history

**Code, Context, Issues, comments and durable workflow configuration travel in the same ordinary Git branch.** Switching to an older commit restores its historical workflow state as well as its code. There is no second Issue branch, hidden canonical database, or special Git worktree. Git performs merges as usual; github-local does not proxy or automatically commit Git operations.

Each initialized folder has an independent visible `issues/` backlog and stable local workflow repository identity. The containing Git **root** additionally has the versioned `.github-local/git-identity.json` for the logical project. Multiple initialized Issue subfolders inside that Git repository share a globally short-numbered Issue series. Git-free local Issue folders remain possible and use their own allocator.

Concurrent creation in branches/worktrees of the *same* local Git repository uses an OS lock and local Git-common cursor; its data loss cannot destroy Issue Markdown. Multiple clones have distinct local cursors, so their rare collision case is handled *after normal Git merge*, not by pretending to have a central online number service.

## IDs versus short numbers

A new Issue or comment has an independent immutable UUID in front matter. Short Issue numbers such as `#33` are convenient addresses, not durable technical identities.

Two offline clones can both create a different `#33`. After Git merges their distinct Markdown files, `issue status` detects the collision; normal number-dependent operations are blocked. `issue reconcile` previews a winner, lets the owner select a retained UUID, and, on confirmation, renumbers the other Issue to the next unused integer. The record keeps its UUID, gains provenance in metadata and prose, and UUID-linked comments follow. Unknown free-text `#33` references are reported for human review rather than rewritten by guesswork.

No special merge driver, mandatory hooks, automatic Git history rewriting, or forced renumbering during the happy path.

## Local state and safety

Only locks, allocator cursors, automatic-close cursors and temporary scratch are ignored through a visible managed `.gitignore` block. The previous hidden `.git/info/exclude` rule that hid canonical workflow data is retired via explicit `issue migrate`. The Git index and commits are not modified by the tool.

Git-root identity and Issue-repository configurations are regular files. An `issue deinit` operation on the Git root must not delete the Git identity still used by nested Issue repositories. If canonical files remain ignored, mutating commands fail with a migration hint.

Issue files remain atomic Markdown writes; a database, when introduced, may only be a reconstructable index. There is no silent forge synchronization.

## Git-native Change links

`github-local issue develop -R <path> N` uses ordinary native Git branches. Git branch configuration stores a local Issue repository ID, short number, and immutable Issue UUID. Renumbering is therefore not a new technical Issue identity. Historical number-only links remain readable for compatibility.

For accepted history, closing references are interpreted only while the accepted branch is checked out and only when Issue numbers are unambiguous. Nested Issue repositories continue to require qualified closing syntax `Fixes owner/repository#N`. This protects distinct contexts during a merge.

## Agent and operational constraints

An agent must still select the Issue repository with explicit `-R/--repo`; `-R .` searches for the nearest initialized parent from the given location. `issue status -R . --json` and `issue reconcile -R . --dry-run --json` provide inexpensive non-destructive inspection.

See [storage.md](storage.md) for canonical Markdown formats and migration examples, and [agent-validation.md](agent-validation.md) for original corporate Copilot evidence.
