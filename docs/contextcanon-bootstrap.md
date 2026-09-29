# ContextCanon bootstrap status

The repository contains an authored root `CONTEXT.src.md` so the intended local project context is explicit from the first review candidate.

The reusable **GitHub** provider should govern development of this public runtime project while its canonical remote lives on github.com. The repository now exists at `SomeSunlight/github-local`, but this execution environment does not have the `contextcanon` executable installed. For that reason this bootstrap does **not** fabricate generated `CONTEXT.md`, `.context/` package state, or a fake reusable-Source acceptance record.

On a normal workstation shell, complete the deterministic ContextCanon initialization and select the reusable GitHub provider. Generated ContextCanon state should then be committed as ordinary project state in a separate reviewed change.

This boundary is deliberate: authored intent may be prepared manually; generated/accepted ContextCanon package identity must come from ContextCanon itself.


## Next step after MVP merge

The real Copilot owner test validated the CLI-first runtime before ContextCanon onboarding. After PR #2 is accepted and squash-merged, onboard this repository with ContextCanon and compose the reusable **GitHub** provider / **Development Workflow** Source before the next product implementation block.

The authored `CONTEXT.src.md` already captures the validated local product constraints that must survive that onboarding: CLI-first agent operation without mandatory MCP, visible/reconstructable Issue truth, project-wide Issue workflow state, native Git for code state, and early close/auto-close semantics for completed work.
