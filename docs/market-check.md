# Existing-tool check

A short check was done before implementation.

- **git-bug** is a serious offline-first, Git-integrated tracker with CLI, terminal/web UI and a GraphQL API. It deliberately avoids adding Issue files to the project and uses its own `git bug` vocabulary. That conflicts with the visible-Markdown and GitHub-shaped-agent contract here.
- **Forgejo/Gitea** solve the much larger self-hosted forge problem. They bring their own server/database/API model and are intentionally not a minimal GitHub API clone. Forgejo documents Gitea API compatibility, not wholesale GitHub REST/GraphQL compatibility.

These projects are useful references, but neither removes the need for the deliberately smaller `github.local` shape.
