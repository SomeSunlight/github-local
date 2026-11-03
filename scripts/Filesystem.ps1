#requires -Version 7.4
# Cleanup of uniquely named, disposable github-local smoke checkouts only.
function Assert-GithubLocalSmokePath {
    param([string]$Path, [string]$TempRoot)
    $root = [IO.Path]::GetFullPath($TempRoot).TrimEnd('\', '/')
    $candidate = [IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    if (-not [string]::Equals([IO.Path]::GetDirectoryName($candidate), $root,
                             [StringComparison]::OrdinalIgnoreCase) -or
        [IO.Path]::GetFileName($candidate) -cnotmatch '^github-local-smoke-[0-9a-f]{32}$') {
        throw [InvalidOperationException]::new("Not an owned github-local smoke directory: $candidate")
    }
    return $candidate
}

function Get-GithubLocalSmokeDirectories {
    param([string]$Path)
    $pending = [Collections.Generic.Stack[string]]::new()
    $visited = [Collections.Generic.List[string]]::new()
    $pending.Push($Path)
    while ($pending.Count -gt 0) {
        $parent = $pending.Pop()
        $item = Get-Item -LiteralPath $parent -Force -ErrorAction Stop
        if (-not $item.PSIsContainer -or
            ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw [InvalidOperationException]::new("Unsafe smoke directory: $parent")
        }
        $visited.Add($parent)
        foreach ($child in Get-ChildItem -LiteralPath $parent -Force -ErrorAction Stop) {
            if (($child.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw [InvalidOperationException]::new("Refusing linked smoke entry: $($child.FullName)")
            }
            if ($child.PSIsContainer) { $pending.Push($child.FullName) }
        }
    }
    return $visited.ToArray()
}

function Remove-GithubLocalSmokeTree {
    param([string]$Path, [string]$TempRoot, [int[]]$DelaysMs = @(0, 50, 150, 350))
    $candidate = Assert-GithubLocalSmokePath -Path $Path -TempRoot $TempRoot
    foreach ($delay in $DelaysMs) {
        if ($delay -gt 0) { Start-Sleep -Milliseconds $delay }
        if (-not (Test-Path -LiteralPath $candidate)) { return $true }
        try {
            Get-GithubLocalSmokeDirectories -Path $candidate | Out-Null
            Remove-Item -LiteralPath $candidate -Recurse -Force -ErrorAction Stop
            return $true
        }
        catch {
            if ($_.Exception -is [InvalidOperationException]) { throw }
            if (-not (Test-Path -LiteralPath $candidate)) { return $true }
        }
    }
    return -not (Test-Path -LiteralPath $candidate)
}

function Clear-EmptyGithubLocalSmokeTrees {
    param([string]$TempRoot)
    if (-not (Test-Path -LiteralPath $TempRoot)) { return }
    foreach ($entry in Get-ChildItem -LiteralPath $TempRoot -Directory -Force) {
        if ($entry.Name -cnotmatch '^github-local-smoke-[0-9a-f]{32}$' -or
            $entry.LastWriteTimeUtc -gt [datetime]::UtcNow.AddMinutes(-5)) { continue }
        try {
            $folders = @(Get-GithubLocalSmokeDirectories -Path $entry.FullName)
            $hasFiles = $false
            foreach ($folder in $folders) {
                if (@(Get-ChildItem -LiteralPath $folder -File -Force).Count) {
                    $hasFiles = $true
                    break
                }
            }
            if ($hasFiles) { continue }
            if (-not (Remove-GithubLocalSmokeTree -Path $entry.FullName -TempRoot $TempRoot)) {
                Write-Warning "Old fileless smoke directory is locked: $($entry.FullName)"
            }
        }
        catch {
            Write-Warning "Skipped unsafe/unreadable smoke directory: $($entry.FullName)"
        }
    }
}
