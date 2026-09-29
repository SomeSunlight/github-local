# Agent validation

## Real target-environment test

The first owner validation used corporate GitHub Copilot with Claude Sonnet 5 (Medium, 264k context). MCP is administratively unavailable in that environment; the agent had ordinary terminal/filesystem/Git capabilities.

Using only the documented CLI workflow, the agent successfully:

- discovered `github-local` through `--help`;
- initialized a disposable Git repository;
- created three local Issues;
- listed them in human-readable and JSON form;
- viewed Issue #1;
- created the documented Issue-numbered branch and commit.

This validates the central product hypothesis: a terminal-capable LLM can use an unfamiliar local workflow tool effectively without MCP. CLI is therefore the primary agent contract; MCP can remain an optional future adapter.

## Agent debrief

The agent specifically found these properties useful:

- stable structured `--json` output;
- explicit errors rather than stack traces or silent failures;
- Markdown Issue persistence that is directly visible and Git-diff-friendly;
- consistent nested `--help` discovery;
- familiar GitHub-shaped command vocabulary.

The agent identified the following product gaps:

- missing close/reopen/edit/comment lifecycle;
- no first-class Change ↔ Issue relation;
- no automatic close of completed Issues;
- limited list filtering/search and no labels;
- no concise examples in CLI help.

It also wondered whether create supports JSON. That capability already exists (`issue create --json ...`); it simply was not exercised during the test.

## Product direction from the owner test

The next work is tracked in Issues #3–#7. Automatic close is an early requirement, not a distant convenience: accepted work with an explicit closing reference should remove the corresponding Issue from the open backlog. Explicit manual close/reopen must remain available.

Assignees and milestones remain deliberately out of scope while the primary workflow is single-owner.

The test demonstrates that future deterministic local tools can use the same general integration pattern where appropriate: a compact discoverable CLI plus structured output can be a practical agent surface even when MCP is unavailable.
