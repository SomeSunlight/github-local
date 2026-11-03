#requires -Version 7.4
# Windows-only offline cleanup regressions; no Git repo removed outside fixture.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../scripts/Filesystem.ps1')
function Assert-True { param([bool]$Ok,[string]$Why) if (-not $Ok) { throw $Why } }
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('gh-local-cleanup-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture | Out-Null
$session = Join-Path $fixture ('github-local-smoke-' + [guid]::NewGuid().ToString('N'))
$foreign = Join-Path $fixture 'foreign'
New-Item -ItemType Directory -Path $session, $foreign | Out-Null
Set-Content -LiteralPath (Join-Path $session 'disposable.txt') -Value 'test'
Set-Content -LiteralPath (Join-Path $foreign 'keep.txt') -Value 'important'

try {
    $script:deletions = 0
    function Remove-Item {
        [CmdletBinding()]
        param([string]$LiteralPath,[switch]$Recurse,[switch]$Force)
        $script:deletions++
        if ($script:deletions -eq 1) { throw [IO.IOException]::new('transient AV lock') }
        Microsoft.PowerShell.Management\Remove-Item -LiteralPath $LiteralPath -Recurse:$Recurse -Force:$Force -ErrorAction Stop
    }
    Assert-True (Remove-GithubLocalSmokeTree -Path $session -TempRoot $fixture -DelaysMs @(0, 0)) 'Transient lock not recovered'
    Assert-True ($script:deletions -eq 2) 'Retry count mismatch'
    Assert-True (Remove-GithubLocalSmokeTree -Path $session -TempRoot $fixture -DelaysMs @(0)) 'Not idempotent'

    $blocked = Join-Path $fixture ('github-local-smoke-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $blocked | Out-Null
    Set-Content -LiteralPath (Join-Path $blocked 'keep.txt') -Value 'persist'
    function Remove-Item {
        [CmdletBinding()]
        param([string]$LiteralPath,[switch]$Recurse,[switch]$Force)
        throw [IO.IOException]::new('persistent AV lock')
    }
    Assert-True (-not (Remove-GithubLocalSmokeTree -Path $blocked -TempRoot $fixture -DelaysMs @(0, 0))) 'Persistent lock ignored'
    Assert-True (Test-Path -LiteralPath (Join-Path $blocked 'keep.txt')) 'Locked files were removed'
    $refused = $false
    try { Remove-GithubLocalSmokeTree -Path $foreign -TempRoot $fixture -DelaysMs @(0) | Out-Null }
    catch { $refused = $true }
    Assert-True $refused 'Foreign directory accepted'

    Microsoft.PowerShell.Management\Remove-Item -LiteralPath Function:\Remove-Item -Force
    $linked = Join-Path $blocked 'linked'
    try {
        New-Item -ItemType Junction -Path $linked -Target $foreign -ErrorAction Stop | Out-Null
        $refused = $false
        try { Remove-GithubLocalSmokeTree -Path $blocked -TempRoot $fixture -DelaysMs @(0) | Out-Null }
        catch { $refused = $true }
        Assert-True $refused 'Nested junction accepted'
        Assert-True (Test-Path -LiteralPath (Join-Path $foreign 'keep.txt')) 'Foreign junction target modified'
    }
    catch {
        if ($_.Exception.Message -notlike '*privilege*') { throw }
        Write-Host 'Junction creation unavailable; fixture skipped.'
    }

    $stale = Join-Path $fixture ('github-local-smoke-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path (Join-Path $stale 'empty/deep') -Force | Out-Null
    (Get-Item -LiteralPath $stale).LastWriteTimeUtc = [datetime]::UtcNow.AddMinutes(-10)
    Clear-EmptyGithubLocalSmokeTrees -TempRoot $fixture
    Assert-True (-not (Test-Path -LiteralPath $stale)) 'Old fileless skeleton not pruned'
    Assert-True (Test-Path -LiteralPath (Join-Path $foreign 'keep.txt')) 'Foreign file modified'
    Write-Host 'github-local Windows smoke cleanup tests passed.'
}
finally {
    Microsoft.PowerShell.Management\Remove-Item -LiteralPath Function:\Remove-Item -Force -ErrorAction SilentlyContinue
    Microsoft.PowerShell.Management\Remove-Item -LiteralPath $fixture -Recurse -Force -ErrorAction SilentlyContinue
}
