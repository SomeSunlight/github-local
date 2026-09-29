# Official `gh` compatibility spike

## Scope measured

Reference client: GitHub CLI **2.101.0** (released 2026-09-15). Source inspection was performed against tag `v2.101.0`.

This environment could inspect official source and current documentation but could not download or execute the `gh` binary because outbound DNS is disabled. The repository therefore contains a trace/fake server under `spike/` so the same probes can be run with a real current `gh.exe` on Windows. No unmeasured request sequence is presented here as observed runtime evidence.

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
