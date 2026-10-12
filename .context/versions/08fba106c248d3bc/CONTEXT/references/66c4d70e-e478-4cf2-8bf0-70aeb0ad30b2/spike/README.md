# `gh` protocol trace spike

This directory is evidence tooling, not the product runtime.

`gh_trace_server.py` records every HTTP request as JSONL and returns just enough canned GitHub-Enterprise-shaped responses to let a current `gh` client advance through common Issue probes. Unknown GraphQL operations are returned as explicit errors and remain visible in the log.

## Relationship to the source-contract snapshot

`gh_trace_server.py` is the black-box half of the compatibility evidence. The companion `gh-2.101.0-source-contract.json` is the source-inspection half.

The JSON contract says what the tagged `gh v2.101.0` source was found to require. The trace server lets a contributor verify what a real `gh` binary actually sends. Keep those claims separate: the current source-contract explicitly records that the original environment did not execute the binary.

For the full rationale and update workflow, see `../CONTRIBUTING.md`.

## Why this exists

The implementation environment used for the first spike had no executable `gh` and no outbound DNS, so current source could be inspected but a binary could not be downloaded. This harness makes the missing black-box step reproducible rather than inventing an observed trace.

## Recommended Windows probe

Use a disposable PowerShell session and an isolated `GH_CONFIG_DIR`. `gh` requires HTTPS for an enterprise-style host. The easiest probe host is `github.localhost` (the product is still called `github.local`) because `.localhost` resolves to loopback without editing the hosts file.

1. Create/trust a development certificate for `github.localhost` and start the server on port 443:

```powershell
python .\spike\gh_trace_server.py --listen 127.0.0.1 --port 443 --cert .\tmp\github.localhost.pem --key .\tmp\github.localhost-key.pem --log .\tmp\gh-trace.jsonl
```

`mkcert github.localhost` is one convenient way to create a locally trusted certificate; use any corporate-approved equivalent.

2. In a second disposable shell:

```powershell
$env:GH_CONFIG_DIR = "$PWD\tmp\gh-config"
$env:GH_HOST = "github.localhost"
$env:GH_ENTERPRISE_TOKEN = "local-probe-token"
$env:GH_REPO = "github.localhost/local/demo"
$env:GH_DEBUG = "api"

# Probe one command at a time.
gh issue create --title "Trace me" --body "Protocol probe"
gh issue list --json number,title,state
gh issue view 1 --json number,title,body,state
```

3. Compare PowerShell debug output with `tmp/gh-trace.jsonl`. Each JSONL row records method, path, selected headers, GraphQL operation name, variables, and request body.

Do not point normal GitHub credentials at the fake server. Use the disposable token shown above.

## `api_host` alternative

Current `gh` also has experimental `api_host` routing, but the setting accepts a bare hostname rather than a port. That is useful for a real loopback gateway on 443; it does not remove the TLS/certificate requirement or turn GitHub Issue commands into REST CRUD.
