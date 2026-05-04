[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$PackDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PackDirFile = Join-Path $RepoRoot 'PACK_DIR.txt'

if ([string]::IsNullOrWhiteSpace($PackDir)) {
    $PackDir = Read-Host 'Enter full path to your modpack instance folder'
}

if ([string]::IsNullOrWhiteSpace($PackDir)) {
    throw 'PACK_DIR cannot be empty.'
}

try {
    $PackDir = (Resolve-Path -LiteralPath $PackDir).Path
} catch {
    $PackDir = [System.IO.Path]::GetFullPath($PackDir)
    Write-Warning "Path does not exist yet. Writing unresolved path: $PackDir"
}

Set-Content -LiteralPath $PackDirFile -Value $PackDir -Encoding UTF8

Write-Host 'PACK_DIR.txt written as:'
Get-Content -LiteralPath $PackDirFile
