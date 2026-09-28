---
{"github-local":{"schema":1,"id":"I_bootstrap_0001","number":1,"state":"OPEN","created_at":"2026-09-28T17:56:00Z","updated_at":"2026-09-28T17:56:00Z"}}
---
# Prove the CLI-first local development workflow

## Why

ContextCanon already defines GitHub Local as the local provider for the familiar Issue → branch → Pull Request → review → checks → merge workflow, while native Git and the working tree remain responsible for code state. The runtime itself still needs to be implemented as a separate project.

The first implementation block must determine whether the official GitHub CLI can be reused without turning a small local provider into a partial GitHub clone. If that burden is disproportionate, implement a small native CLI with GitHub vocabulary instead.

## Acceptance

- the protocol decision is evidence-backed and reproducible;
- Issue truth is visible Markdown under `issues/`;
- a local CLI can create, list, and view persisted Issues with structured output;
- numbering and writes are safe under rapid/concurrent creation;
- no operation silently contacts an external forge;
- the result is tested and left unmerged for owner review.
