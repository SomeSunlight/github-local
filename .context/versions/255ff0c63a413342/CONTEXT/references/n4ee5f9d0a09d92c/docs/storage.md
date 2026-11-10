# Issue storage

## Canonical truth belongs to the checked-out Git snapshot

Every Issue is ordinary, readable Markdown in the initialized local Issue repository's `issues/` directory:

```text
product/
├── .github-local/
│   └── config.json
└── issues/
    └── 0033-short-title.md
```

Issue front matter remains explicitly machine-owned JSON (also valid YAML 1.2):

```markdown
---
{"github-local":{"schema":1,"id":"I_gl_<UUID-hex>","number":33,"state":"OPEN","labels":[],"created_at":"...","updated_at":"..."}}
---
# Human-readable title

Description of the problem.
```

The `id` is independently generated and immutable. `number` is a short, human-friendly reference and may change **only** during explicit collision repair. A title change may rename the slug, not the ID or number.

When an initialized Issue repository lies in Git, **these Markdown files belong to the current Git worktree and branch**, just like code and Context documents. Commit and push them with your normal Git tools. Checkout of an older revision restores its historical Issues as well as its code. There is no separate Issue branch, secondary worktree, hidden Issue database, or automatic Git commit.

Git-free local Issue folders remain supported and can maintain their Issues entirely on disk.

## Identity and explicit Issue repository boundaries

`github-local issue init` makes the current folder an Issue repository. The folder contains `.github-local/config.json`, its own Issue directory, and its own stable workflow-repository ID. Nested Issue repositories retain separate backlogs and explicit `-R/--repo` selection.

Inside Git, the containing Git **root** additionally receives `.github-local/git-identity.json`. This is a versioned identity for the *logical* Git project; normal clones inherit it. It is deliberately not a machine-local `.git` identity. It must be committed with the normal project files.

Issue numbers are allocated **globally per containing Git repository**, across its initialized nested Issue folders, branches, and linked worktrees on the same machine. Local OS locking and a reconstructable cursor under the shared Git common directory coordinate concurrent allocation. After cloning, number allocation scans available Issue files and Git history before choosing the next number. Gaps are normal; old numbers need not be reused. Git-free repositories use their own local allocator.

Clones that develop offline independently cannot share the local cursor. They may legitimately create different Issue UUIDs with the same short number; this is reconciled after a normal Git merge.

## Git ignore policy and migration

Canonical `issues/`, `.github-local/config.json` and the root `.github-local/git-identity.json` **must not be ignored**. The old `.git/info/exclude` policy is obsolete.

The managed block in the containing root `.gitignore` ignores only runtime files:

```gitignore
**/.github-local/locks/
**/.github-local/tmp/
**/.github-local/issue-state.json
**/.github-local/closing-state.json
```

This is intentionally visible in the ordinary project file. Nothing automatically stages, commits, or pushes these files for you.

For an **existing github-local installation**, use:

```bash
github-local issue status -R .
github-local issue migrate -R . --dry-run
github-local issue migrate -R .
git status
git add .gitignore .github-local/ issues/
git commit -m "Version local Issues with project"
```

Run migration separately for every initialized nested Issue repository that still has old hidden exclusions. The migration also **adopts existing plain Markdown Issues** whose filenames have the form `0004-abc.md` and whose content begins with `# Title`. It adds machine-owned JSON front matter with a fresh immutable UUID, the **existing filename number**, an initial `OPEN` state, and an import record. The first timestamps use the file's last modification time as a best-effort estimate, not a verified original creation date. Numbered plain Markdown comments can likewise acquire UUIDs and an immutable parent Issue ID. In the `--dry-run` report, `plainMarkdownIssues` and `plainMarkdownComments` count records that need this conversion; the dry run creates no metadata or UUIDs. Files that already contain invalid structured front matter, or numbered files without an Issue title, still fail explicitly instead of being silently overwritten.

It removes only matching legacy exclude entries and upgrades legacy Issue/comment IDs, while retaining Issue numbers, titles, comments, and their discussion. It does **not** invoke `git add`, modify the Git index, or push to any remote. Review your own `.gitignore` for additional rules that might exclude Issues. The status command reports ignored canonical paths.

A previously branch-independent backlog is associated with the worktree where it currently resides at migration time; commit it before switching branches. For existing linked worktrees, make sure your intended canonical branch has the records before checkout.

If a desired file is already Git-tracked, it is welcome. A tracked `issues/` directory no longer blocks initialization.

## Comments and lifecycle

Comments are files designed for **human reading and chronological discussion**. Their filenames start with a per-Issue sequence number and a short summary extracted from the first nonempty line of the comment, followed by an eight-character UUID suffix:

```text
issues/comments/0033/
  0001-fehler-reproduziert-2e7943a4.md
  0002-ursache-identifiziert-417bb82e.md
  0003-korrektur-getestet-990d7c8f.md
```

The sequence is the primary sort order for both file browsers and `issue view --comments`. The complete immutable `C_gl_...` ID and parent `issue_id` are stored inside JSON front matter; the short suffix protects against same-name collisions across independent Git branches. Within one Git repository, linked worktrees coordinate comment allocation under a shared lock. Offline clones may independently assign an equal sequence number; in that rare case the two unique filenames survive Git merge and API display resolves ties by creation timestamp and filename. Such ties are **not** automatically renumbered.

Migration preserves old comment numbers and discussion bodies. It converts `0001.md` (and optional earlier `C_gl_<UUID>.md`) to the new human-friendly convention. **The read-only dry run reports `commentFileRenames`**, including UUID-only names that already have valid metadata; `legacyComments` counts missing or obsolete IDs separately. Normal reads continue accepting the older numeric and UUID-only filenames. Running migration a second time is safe and retains existing full UUIDs.

Issue creation, edits, labels, comments, and state transitions are atomic Markdown writes under repository-local locks. The Git index is not manipulated by the application. `issue delete` and `issue deinit` remain confirmation-protected; deinit preserves the shared root Git identity when nested repositories use it.

## Git merges, number collisions, and repair

Let Git merge branches and files ordinarily. Most merges require no special work. After a merge, run:

```bash
github-local issue status -R .
github-local issue reconcile -R . --dry-run
github-local issue reconcile -R . --source-branch "Windows"
```

When previously separate Issue repositories are migrated into a single Git repository, their formerly independent numbers may overlap. This is an expected one-time reconciliation task, not necessarily a Git merge conflict.

The normal `github-local status -R .` starts with **OK** or **ACTION REQUIRED**, summarizes the conflicting numbers, and shows the candidate paths and titles in a readable form. `--json` includes `ok`, `actionRequired`, `collisionCount`, `affectedIssues`, and the candidate records. The read-only command makes no changes and returns normally; scripts should inspect `actionRequired`.

For ambiguous collisions, `github-local issue reconcile -R .` asks which Issue keeps each old number and shows the resulting new numbers before confirmation. `--dry-run` is always read-only. Scripts can supply repeated `--keep-id I_gl_...` flags for multiple collisions. A bare `--yes` is not permission to pick winners without sufficient evidence. If the origin branch is not known, the Issue records the original path rather than inventing a branch name.

The read-only status/report detects when **different immutable Issue IDs have the same number within a Git checkout**. Number-dependent writes and automatic closure are blocked until this is resolved. Reconciliation uses a unique *first-parent* Issue only where ordinary merge ancestry identifies it unambiguously. Otherwise it requires the owner to select a keeper interactively. It never chooses by alphabetical path or arbitrary UUID order. You may select the Issue that retains the old number with `--keep-id I_gl_...`. `--yes` confirms non-interactively.

Other colliding Issues receive the next available ordinary **integer** numbers, not special suffixes. The affected Issue retains its original UUID, gains an explicit machine-readable `renames` entry, and appends a visible record such as:

> Renamed on 2026-10-12T19:20:00Z from #33 of branch Windows.

Its UUID-associated comments move to the new numbered folder and retain their own UUIDs. If old comments lack an `issue_id`, github-local refuses to guess which duplicate Issue owns them: migrate/attribute them first.

A plain `#33` in arbitrary Markdown, commit messages, or external documents cannot always be assigned unambiguously to one Issue. **github-local never automatically replaces these references.** It reports possible internal text references for human review. Historical commit messages are not rewritten. Merge conflicts involving *identical filenames* must first be resolved normally in Git, preserving both records; only then can number reconciliation operate.

Repair leaves ordinary unstaged Git changes for review and commit. It also advances the accepted-history closing cursor past already-merged ambiguous closing references, rather than automatically closing the wrong Issue. Future closing references work normally after repair.

## Accepted branch and development links

When a Git accepted branch is configured, `Fixes #N`, `Closes #N`, or `Resolves #N` can close an Issue after the commit reaches the accepted branch. This reconciliation runs only when that branch is actually checked out; it must not mutate an unrelated feature branch. Nested local Issue repositories still require qualified `owner/repository#N` closing references.

Git remains authoritative for branches, commits, diffs, and merges. The branch-config Change relation now stores the immutable Issue ID as well as its short number and local Issue repository ID. Existing number-only relations remain readable as legacy links. Branch-local `.git/config` relation metadata is not automatically synchronized by ordinary Git clones.

## Index and error policy

There is no required database. Any future cache or index must be reconstructable from canonical Markdown and Git history. Readers never interpret temporary write files as Issues. Duplicate UUIDs indicate a distinct corruption problem and must not be silently resolved as if they were a number collision.

Use `github-local issue status -R . --json` for machine-readable diagnostics and `issue reconcile --json --dry-run` to inspect collision plans without side effects.
