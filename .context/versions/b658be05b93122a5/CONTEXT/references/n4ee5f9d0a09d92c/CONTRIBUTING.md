# Contributing

github.local deliberately follows GitHub CLI (`gh`) vocabulary and behavior wherever that maps cleanly to a local workflow. A smaller supported subset is fine; accidental divergence is not.

Before changing the Issue CLI surface, read:

- `CONTEXT.md` / `CONTEXT.src.md` for the maintained project rules;
- `docs/gh-compatibility.md` for the supported `gh` subset and intentional deviations;
- `spike/README.md` for the reproducible real-client probe;
- `spike/gh-2.101.0-source-contract.json` for the machine-readable source-inspection snapshot used by the current compatibility decision.

## Why `--help` is not enough

`gh ... --help` is useful for discovering command names, flags, aliases, and user-facing defaults. We use it for that surface.

It does **not** tell us the protocol contract behind a command. For example, help output cannot establish whether `gh issue list` uses REST or GraphQL, which preliminary feature/version probes run, which endpoint paths are required, or which fields and variables are sent.

For compatibility work we therefore separate two questions:

1. **CLI surface:** what command/flag/default does a user or LLM expect?
2. **Protocol behavior:** what does the real `gh` client send to a GitHub-compatible host?

The first can be checked from current documentation/help. The second needs source inspection and, where possible, a black-box trace.

## The source-contract snapshot

`spike/gh-2.101.0-source-contract.json` is a frozen, machine-readable summary of the source inspection performed against `gh` tag `v2.101.0`.

It records, for the commands relevant to the original architecture decision:

- the exact `gh` version/source tag;
- the source files inspected;
- the REST/GraphQL operations inferred from that source;
- the enterprise-host routing assumptions;
- structured-output observations;
- whether a real black-box client run was actually performed in that environment.

The important field is currently:

```json
"black_box_executed_here": false
```

That is deliberate evidence hygiene. The original inspection environment could read the source but had no executable `gh` binary and no outbound DNS, so the JSON must **not** be mistaken for a captured network trace.

The source-contract file answers:

> “What does this tagged `gh` source say the client is built to do?”

It does not answer:

> “What exact requests did a real `gh.exe` send during this run?”

That second question is what the trace harness is for.

## How the trace server works

`spike/gh_trace_server.py` does not inject into, hook, or instrument the `gh` process.

Instead, it impersonates a deliberately tiny GitHub Enterprise-shaped server:

```text
real gh.exe
    |
    | HTTPS / GraphQL requests
    v
gh_trace_server.py
    |
    +--> writes every request to gh-trace.jsonl
    |
    +--> returns small canned responses so gh can continue
```

The probe shell points `gh` at a disposable hostname such as `github.localhost` using `GH_HOST`, `GH_REPO`, an isolated `GH_CONFIG_DIR`, and a fake enterprise token.

Because `gh` treats a non-`github.com` host as GitHub Enterprise-shaped, it sends its normal enterprise traffic to the fake server.

### What the server records

For every request, `Handler._record()` writes one JSON object to the JSONL log containing:

- HTTP method;
- request path;
- selected headers;
- GraphQL operation name;
- GraphQL variables;
- raw request body.

The Authorization value is deliberately replaced with `<redacted>`.

### Why the server must answer too

Merely accepting the first request is not enough. A real client often needs the response before it can decide what to send next.

The trace server therefore returns minimal canned responses for the operations already identified during source inspection, including:

- enterprise metadata/version probing;
- Issue GraphQL field introspection;
- repository/Issue lookup;
- Issue create/list/view;
- comment creation;
- Issue close.

The responses are not meant to reproduce GitHub as a product. They only contain enough shape to let the current `gh` command advance to its next request.

Unknown GraphQL operations return an explicit `NOT_IMPLEMENTED` error. That is useful evidence: when a newer `gh` starts asking for something new, the harness fails visibly instead of silently pretending compatibility.

### Why HTTPS and port 443 appear in the probe

Current `gh` enterprise routing expects HTTPS. Its experimental `api_host` setting accepts a hostname, not an arbitrary `host:port` URL. The reproducible Windows harness therefore uses a loopback hostname plus a locally trusted certificate and normally listens on 443.

See `spike/README.md` for the concrete PowerShell recipe.

## Updating the evidence for a newer gh version

When compatibility with a newer `gh` release matters:

1. Record the exact `gh` version/tag being evaluated.
2. Compare current official help/documentation for the CLI surface.
3. Inspect the tagged source paths relevant to the supported commands.
4. Add or update a versioned source-contract JSON file; do not overwrite historical evidence ambiguously.
5. Run the black-box trace when a suitable real `gh` binary is available.
6. Compare the real JSONL requests with the source-derived expectation.
7. Update `docs/gh-compatibility.md` with supported behavior and intentional deviations.
8. Update ContextCanon resources/rules when the compatibility decision or maintained contract changes.
9. Run the normal tests plus `contextcanon build --all .` and `contextcanon check --all .`.

The goal is not perfect emulation of every GitHub feature. The goal is a small local implementation whose supported surface is unsurprising to humans and LLMs already familiar with `gh`, with every deliberate difference visible and justified.
