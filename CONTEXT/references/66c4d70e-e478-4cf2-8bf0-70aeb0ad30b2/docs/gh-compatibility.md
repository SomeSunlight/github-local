# Official `gh` compatibility spike

## Scope measured

Reference client: GitHub CLI **2.101.0** (released 2026-09-15). Source inspection was performed against tag `v2.101.0`.

This environment could inspect official source and current documentation but could not download or execute the `gh` binary because outbound DNS is disabled. The repository therefore contains a trace/fake server under `spike/` so the same probes can be run with a real current `gh.exe` on Windows. No unmeasured request sequence is presented here as observed runtime evidence.

## Evidence files

The current compatibility decision uses two complementary evidence forms:

- `spike/gh-2.101.0-source-contract.json` — machine-readable snapshot of the `gh v2.101.0` source inspection. It records which source paths and operations informed the decision and explicitly states that no black-box `gh` binary run occurred in the original inspection environment.
- `spike/gh_trace_server.py` with `spike/README.md` — reproducible black-box harness for redirecting a real `gh` client to a tiny fake GitHub Enterprise-shaped endpoint and recording the resulting HTTP/GraphQL requests as JSONL.

See `CONTRIBUTING.md` for an explanation of how these two evidence forms fit together and why CLI help alone is insufficient for protocol compatibility work.

## Host/routing facts

- `gh` supports alternate GitHub Enterprise hosts via host configuration / `GH_HOST` and enterprise tokens.
- Since 2.100.0, experimental per-host `api_host` can route API traffic through a different host while login, Git remotes and web URLs retain the logical GitHub host.
- `api_host` is a **bare hostname**: it cannot carry a port. The official black-box harness therefore binds its gateway to HTTPS port 443 and installs/trusts a local CA.
- For a non-github.com host, `gh` treats the host as enterprise-shaped and uses GitHub Enterprise API behavior.

## Issue command contract from 2.101.0 source

The important result is that normal Issue commands are GraphQL-heavy, not a small REST CRUD surface.

### `gh issue create`

At minimum the source path performs:

1. enterprise version probing for feature decisions (`GET meta`, resolved through the enterprise REST base);
2. Issue feature detection through GraphQL schema introspection on enterprise hosts;
3. `IssueRepositoryInfo` GraphQL query for repository id/databaseId/name/owner/issues-enabled/viewer-permission;
4. `IssueCreate` GraphQL mutation using `CreateIssueInput`;
5. optional follow-up mutations for issue type, parent/sub-issue and relationships.

The actual create mutation asks only for the new Issue `id` and `url`, and the command prints the URL.

### `gh issue list`

Uses GraphQL `IssueList`, querying `Repository.issues` with state/filter/page variables and requesting dynamic Issue fields. It supports structured `--json` output.

### `gh issue view`

Uses GraphQL `IssueByNumber` around `issueOrPullRequest(number: ...)`, with dynamic Issue/Pull Request fragments. With `--json`, the requested fields limit the payload; normal human output requests a much wider default field set.

### comments and close

Creating a comment uses GraphQL `addComment(input: ...)`. Closing first resolves the Issue/PR with GraphQL and then invokes `closeIssue(input: ...)`.

## Consequence

A tiny compatible server is possible, but it must impersonate enough GitHub Enterprise GraphQL semantics, HTTPS/certificate behavior, feature detection and response shape to satisfy an independently evolving client. That is substantially more implementation and compatibility risk than a purpose-built local CLI for the MVP.

Therefore the first product slice uses `github-local issue ...`. The `gh` surface stays an optional later adapter with this trace harness as the measurement tool.

## Real-`gh` reproduction on Windows

See `spike/README.md`. The probe uses an isolated GH config, a loopback hostname, a trusted local certificate, and `GH_DEBUG=api`; the fake server writes every request as JSONL. Use a throwaway shell/config so no normal GitHub credentials are exposed to the probe.


## Native CLI compatibility policy

The native `github-local issue ...` surface should use official GitHub CLI vocabulary, flags, aliases and defaults whenever the local architecture can support the same intent directly. github.local may implement a smaller subset; it should not invent a different name for an operation that already has a suitable `gh` spelling.

Current supported-subset alignment:

| Capability | GitHub CLI shape | github.local |
| --- | --- | --- |
| Create | `gh issue create -l/--label` | same command name and label flag; local title/body/label subset |
| List | `gh issue list` / `gh issue ls`; `-s/--state`, `-l/--label`, `-S/--search`; default state `open` | same names/flags/default for the supported local subset |
| View | `gh issue view N --comments` | same core name and `--comments` behavior |
| Close | `gh issue close N --comment TEXT` | same core name and comment flag; close reasons not yet implemented |
| Reopen | `gh issue reopen N --comment TEXT` | same core name and comment flag |
| Edit | `gh issue edit N --add-label/--remove-label` | same core name and label flags; local title/body/label subset |
| Comment | `gh issue comment N` | same core name and body/body-file flags; no interactive editor/web flow |
| Development branch | `gh issue develop N [--base] [--checkout] [--name]` | same names/flags; operates on local Git refs |
| List linked branches | `gh issue develop --list N` | same syntax; structured local JSON is also available |

Intentional deviations:

- `github-local init` is local-only because github.local needs repository-local workflow configuration and an accepted branch; GitHub CLI has no equivalent Issue initialization step.
- `gh issue develop --branch-repo` is not supported: github.local currently links branches inside the one local Git repository only.
- `gh issue develop --worktree` is not yet supported. Existing Git worktrees are understood by github.local, but worktree creation is not part of the supported Issue-develop subset yet.
- `--base` resolves a local Git branch/ref rather than a remote GitHub branch because github.local has no forge-side branch-creation API.
- `issue develop --json ...` is a github.local extension for cheap agent inspection; official `gh issue develop` has no JSON flag.
- `issue develop --name EXISTING_BRANCH` may adopt an existing unlinked local branch by attaching the Issue relation. This local convenience has no exact forge-side GitHub equivalent.
- Labels are free-form Issue metadata. github.local does not currently implement GitHub's repository-wide label objects or a `gh label` management subsystem.
- `issue list --search` uses a case-insensitive substring match over local title/body/label text. It does not emulate GitHub's hosted advanced-search query language.
- The local JSON `labels` field is a stable array of label-name strings rather than GitHub-hosted label objects.
- `--repo`, `--web`, remote authorization, projects, assignees, milestones and similar GitHub-service features are not emulated unless a later local use case justifies them.
- github.local JSON fields are deliberately small and stable rather than pretending to expose remote GitHub fields that do not exist locally.

Any future syntax deviation should be recorded here with its reason.
