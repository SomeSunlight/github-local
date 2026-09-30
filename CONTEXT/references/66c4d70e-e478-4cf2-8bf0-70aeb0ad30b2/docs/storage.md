# Issue storage

## Canonical form

Each Issue is one ordinary Markdown file:

```text
issues/0001-short-title.md
```

The file begins with a strict machine-owned front matter block. The content inside the delimiters is JSON; JSON is also valid YAML 1.2, so the format remains friendly to common front-matter tooling while the runtime needs only the Python standard library.

```markdown
---
{"github-local":{"schema":1,"id":"I_...","number":1,"state":"OPEN","created_at":"...","updated_at":"..."}}
---
# Human-readable title

Issue body.
```

The title and body are maintained once as Markdown. Machine metadata does not duplicate them.

## One backlog per Git repository

Issue state is **project workflow state**, not ordinary branch state.

The primary Git worktree owns the canonical visible `issues/` directory. Every linked worktree discovers that primary worktree through Git and reads/writes the same Markdown files. Branch switches therefore do not select a different backlog, and linked worktrees do not get separate Issue number spaces.

Runtime coordination state is shared through Git's common metadata directory:

```text
<git-common-dir>/github-local/
├── config.json
└── locks/
    └── issues.lock
```

This shared metadata contains repository identity and locking only. Canonical Issue content remains visible Markdown below the primary worktree's `issues/`; it is not moved into the Git metadata directory or an opaque database.

Existing pre-#3 projects with `.github-local/config.json` are migrated lazily: github.local reads the visible legacy configuration once and writes the same repository identity into the common Git metadata area.

## Keep workflow state out of branch tracking

`github-local init` adds `/issues/` to the repository's shared `.git/info/exclude`. This keeps the canonical local backlog out of normal code-branch status without requiring a project `.gitignore` edit.

If Git already tracks files below `issues/`, github.local refuses project-wide Issue operation rather than pretending the backlog is branch-independent. The migration is deliberately explicit:

```text
git rm --cached -r issues
```

Commit that code-state change before using github.local across branches/worktrees. Historical or other active branches that still track `issues/` must likewise receive that migration before github.local is used there.

This separation is intentional:

- native Git branches/worktrees own code state;
- github.local owns one local workflow backlog per Git repository;
- Markdown remains inspectable with normal editors and file tools.

## Numbering and concurrency

Issue numbers are repository-local monotonically increasing integers. Creation takes an OS-level exclusive lock from the shared Git common directory, scans the one canonical `issues/` directory, chooses `max + 1`, and writes the new file before releasing the lock.

Because every linked worktree uses the same directory and the same lock, rapid or concurrent Issue creation across worktrees cannot allocate the same next number.

The lock uses `msvcrt.locking` on Windows and `fcntl.flock` on POSIX. This is intentionally standard-library only. A crash releases an OS lock when the process exits; a stale lock record therefore does not block later runs.

## Atomicity

New content is written to a temporary file in the same directory, flushed and `fsync`ed, then moved into place with `os.replace`. Directory metadata is `fsync`ed where the platform permits it. Readers never treat temporary files as Issues.

## Filenames are presentation, not identity

The numeric prefix is authoritative for discovery. The slug is generated conservatively, ASCII-normalized, and avoids Windows reserved device names. A future title edit may rename the file while preserving the number and stable Issue ID.

## Index/database policy

There is no database in the MVP. If SQLite is added later it is an index/cache only and must be rebuildable from the canonical Markdown Issue files.
