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

## Numbering and concurrency

Issue numbers are repository-local monotonically increasing integers. Creation takes an OS-level exclusive lock on `.github-local/locks/issues.lock`, scans the canonical `issues/` filenames, chooses `max + 1`, and writes the new file before releasing the lock.

The lock uses `msvcrt.locking` on Windows and `fcntl.flock` on POSIX. This is intentionally standard-library only. A crash releases an OS lock when the process exits; a stale lock record therefore does not block later runs.

## Atomicity

New content is written to a temporary file in the same directory, flushed and `fsync`ed, then moved into place with `os.replace`. Directory metadata is `fsync`ed where the platform permits it. Readers never treat temporary files as Issues.

## Filenames are presentation, not identity

The numeric prefix is authoritative for discovery. The slug is generated conservatively, ASCII-normalized, and avoids Windows reserved device names. A future title edit may rename the file while preserving the number and stable Issue ID.

## Index/database policy

There is no database in the MVP. If SQLite is added later it is an index/cache only and must be rebuildable from `issues/` plus Git state.
