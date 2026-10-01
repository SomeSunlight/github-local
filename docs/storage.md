# Issue storage

## Visible Markdown is canonical

Each Issue is one ordinary Markdown file below the local Issue repository that owns it:

```text
issues/0001-short-title.md
```

The file begins with a strict machine-owned front matter block. The content inside the delimiters is JSON; JSON is also valid YAML 1.2, so the format remains friendly to common front-matter tooling while the runtime needs only the Python standard library.

```markdown
---
{"github-local":{"schema":1,"id":"I_...","number":1,"state":"OPEN","labels":["bug","priority:high"],"created_at":"...","updated_at":"..."}}
---
# Human-readable title

Issue body.
```

The title and body are maintained once as Markdown. Labels are lightweight free-form names stored in the same Issue metadata. Existing schema-1 Issue files without a `labels` member remain valid.

## Local Issue repositories are explicit workflow boundaries

A folder becomes an Issue repository only through:

```text
github-local issue init
```

Initialization creates:

```text
<issue-repository>/
├── .github-local/
│   ├── config.json
│   ├── issue-state.json          # monotonic next-number cursor
│   ├── closing-state.json        # only meaningful with an associated Git repository
│   └── locks/
│       └── issues.lock
└── issues/
```

The hidden configuration is implementation metadata managed by the CLI. Canonical Issue content stays visible under `issues/`.

The schema-2 repository config carries a generated stable repository ID plus a human-readable owner/name. The ID is path-independent: moving the initialized folder moves the backlog without changing its identity. Legacy schema-1 config remains readable and receives a deterministic compatibility identity in memory; github.local does not silently rewrite it.

Issue-repository boundaries are deliberately independent of Git boundaries:

- an Issue repository may exist without Git;
- one Git repository may contain several nested local Issue repositories;
- a parent folder and selected child folders may each own an independent backlog;
- initializing an Issue repository never requires creating a nested Git repository.

This models GitHub's repository-level Issue separation without forcing the local filesystem to mirror Git repository boundaries.

## Repository selection is explicit

Ordinary Issue commands require `-R/--repo`.

`-R .` explicitly means: starting at this path, resolve the nearest folder that was initialized as a local Issue repository. A different path selects that repository instead.

The process CWD alone never chooses a target. This is intentional: humans and LLM agents can both lose track of directory context, so the destination of an Issue must be visible in the command itself.

`issue init` is the exception because its meaning is already explicit: “declare this current folder to be an Issue repository.”

## Independent numbering and identity

Every local Issue repository has its own monotonically increasing Issue number space. Two sibling repositories may both contain `#1`.

New stable Issue IDs are derived from the stable local repository ID plus the Issue number, not from filesystem paths or mutable display names.

Creation takes an OS-level exclusive lock inside that local repository's `.github-local/locks/`. A tiny `issue-state.json` cursor records the next number so deleting the highest Issue or bulk-deleting the backlog never makes an old number reusable. Existing files are still scanned as a safety floor, so the cursor can be reconstructed conservatively. Independent repositories never share allocators or require global coordination.

## Git integration is optional

Issue CRUD, labels, search, comments, deletion, and repository initialization work without Git.

When an initialized Issue repository lies inside a Git worktree, github.local additionally discovers:

- the current Git worktree;
- the primary worktree;
- the shared Git common directory;
- the accepted branch when it can be inferred.

The canonical local Issue files live in the corresponding folder of the primary worktree. Linked worktrees map the same relative folder back to that canonical location, preserving the existing guarantee that ordinary Git worktrees do not fork workflow state.

github.local adds path-specific entries for both `issues/` and `.github-local/` to the shared Git `info/exclude`. Workflow state therefore remains outside normal branch tracking without requiring project `.gitignore` changes. If Issue Markdown is already tracked, github.local refuses operation instead of silently changing the Git index.

## Lifecycle, comments, deletion, and teardown

State changes, title/body edits, labels, and comments use the same repository-local lock as creation. Renaming a title may rename the Markdown filename, but the Issue number and stable Issue ID remain unchanged.

Comments are visible Markdown records:

```text
issues/comments/0001/0001.md
issues/comments/0001/0002.md
```

`issue delete N` follows GitHub CLI vocabulary and requires confirmation unless `--yes` is supplied. github.local additionally supports `issue delete --all` as a local bulk-administration extension; it is confirmation-protected as well.

`issue deinit -R ...` removes local Issue-repository metadata only when the repository is empty. `--delete-issues` explicitly requests destructive teardown and prompts unless `--yes` is supplied. Destructive administration should never require manual deletion of hidden implementation files.

## Accepted branch and automatic close

If a local Issue repository is associated with Git, it records or infers one accepted branch. Only commits newly reachable from that branch are inspected for closing references.

When the local Issue repository is also the Git root, the ordinary GitHub-shaped form remains unambiguous:

```text
Fixes #17
Closes #17
Resolves #17
```

For a nested local Issue repository inside a larger Git repository, unqualified numbers are intentionally not interpreted. Use the GitHub-style cross-repository form:

```text
Fixes owner/repository#17
```

Only a qualified reference whose owner/repository matches the selected local Issue repository may close its Issue. This prevents two nested repositories that both contain `#17` from being confused.

A plain mention such as `#17` never closes anything. A closing reference on an unmerged feature branch has no effect until it reaches the accepted branch.

Each local Issue repository keeps its own `closing-state.json` cursor. Rewritten accepted history resets that cursor rather than replaying ambiguous historical closes.

## Change links across multiple Issue repositories

Git remains authoritative for branches and commits. A first-class branch relation records both:

- the Issue number;
- the stable local Issue-repository ID.

That pair, rather than the number alone, identifies the linked Issue.

For an Issue repository at the Git root, the historical default branch form `issue-17-title` remains available. Nested local Issue repositories qualify generated default branch names with the repository name, for example `issue-product-a-17-title`, avoiding collisions when sibling repositories contain the same Issue number.

Legacy number-only branch metadata remains readable for the Git-root Issue repository only; it is never guessed to belong to a nested repository.

## Atomicity

New or changed content is written to a temporary file in the same directory, flushed and `fsync`ed, then moved into place with `os.replace`. Directory metadata is `fsync`ed where the platform permits it. Readers never treat temporary files as Issues.

## Filenames are presentation, not identity

The numeric prefix is authoritative for discovery. The slug is generated conservatively, ASCII-normalized, and avoids Windows reserved device names. A title edit may rename the file while preserving the number and stable Issue ID.

## Labels and local search

Labels have no separate registry or database. They are case-insensitively matched free-form names persisted directly in each Issue's front matter. Repeated label filters use AND semantics.

`issue list --search` scans only the selected local Issue repository and performs a case-insensitive substring match over title, body, and label names. It deliberately does not reproduce GitHub's hosted advanced-search grammar.

## Index/database policy

There is no database in the MVP. If SQLite is added later it is an index/cache only and must be rebuildable from the selected local repository's canonical Markdown Issue files.
