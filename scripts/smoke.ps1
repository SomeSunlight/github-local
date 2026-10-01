$ErrorActionPreference = "Stop"
$repo = Join-Path $env:TEMP ("github-local-smoke-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $repo | Out-Null
try {
    Push-Location $repo
    git init | Out-Null
    $env:PYTHONPATH = (Resolve-Path (Join-Path $PSScriptRoot "..\src")).Path
    python -m github_local.cli issue init --owner local --name smoke
    python -m github_local.cli issue create -R . --title "Smoke issue" --body "Visible Markdown"
    python -m github_local.cli issue list -R . --json number,title,state,path
    python -m github_local.cli issue view -R . 1 --json number,title,body,state,path
    Get-Content .\issues\0001-smoke-issue.md
} finally {
    Pop-Location
    Remove-Item -Recurse -Force $repo -ErrorAction SilentlyContinue
}
