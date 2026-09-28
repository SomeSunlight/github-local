# ContextCanon bootstrap status

The repository contains an authored root `CONTEXT.src.md` so the intended local project context is explicit from the first review candidate.

The reusable **GitHub** provider should govern development of this public runtime project while its canonical remote lives on github.com. The repository now exists at `SomeSunlight/github-local`, but this execution environment does not have the `contextcanon` executable installed. For that reason this bootstrap does **not** fabricate generated `CONTEXT.md`, `.context/` package state, or a fake reusable-Source acceptance record.

On a normal workstation shell, complete the deterministic ContextCanon initialization and select the reusable GitHub provider. Generated ContextCanon state should then be committed as ordinary project state in a separate reviewed change.

This boundary is deliberate: authored intent may be prepared manually; generated/accepted ContextCanon package identity must come from ContextCanon itself.
