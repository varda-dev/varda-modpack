[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PackDirFile = Join-Path $RepoRoot 'PACK_DIR.txt'
$PackConfigsDir = Join-Path $RepoRoot 'pack-configs'
$DestinationParent = Join-Path $PackConfigsDir 'config'
$Destination = Join-Path $DestinationParent 'ftbquests'

if (-not (Test-Path -LiteralPath $PackDirFile -PathType Leaf)) {
    throw 'PACK_DIR.txt not found. Run scripts/set-pack-dir.ps1 first.'
}

$PackDir = (Get-Content -LiteralPath $PackDirFile -Raw).Trim()

if ([string]::IsNullOrWhiteSpace($PackDir)) {
    throw 'PACK_DIR cannot be empty.'
}

$PackDir = [System.IO.Path]::GetFullPath($PackDir)

if (-not (Test-Path -LiteralPath $PackDir -PathType Container)) {
    throw "PACK_DIR does not exist: $PackDir"
}

$Source = Join-Path (Join-Path $PackDir 'config') 'ftbquests'

if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "FTB Quests source folder not found: $Source"
}

$DestinationFullPath = [System.IO.Path]::GetFullPath($Destination)
$Separators = @([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
$DestinationRoot = [System.IO.Path]::GetPathRoot($DestinationFullPath)
if ([string]::Equals($DestinationFullPath.TrimEnd($Separators), $DestinationRoot.TrimEnd($Separators), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to overwrite filesystem root as destination: $DestinationFullPath"
}

Write-Host '======================================'
Write-Host 'Copy FTB Quests Into Repo'
Write-Host '======================================'
Write-Host "Source: $Source"
Write-Host "Destination: $Destination"
Write-Host ''

New-Item -ItemType Directory -Path $DestinationParent -Force | Out-Null
Remove-Item -LiteralPath $Destination -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item -LiteralPath $Source -Destination $DestinationParent -Recurse -Force

Write-Host 'FTB Quests copied into pack-configs/config.'
