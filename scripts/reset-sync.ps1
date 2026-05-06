[CmdletBinding()]
param(
    [Alias('t')]
    [string]$TargetDirectory,

    [Alias('f')]
    [switch]$FullWipe,

    [Alias('i')]
    [switch]$Inline
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PackDirFile = Join-Path $RepoRoot 'PACK_DIR.txt'
$PackConfigsDir = Join-Path $RepoRoot 'pack-configs'
$ExcludePatterns = @('*.disabled')

function Test-ExcludedPath {
    param(
        [Parameter(Mandatory)]
        [System.IO.FileSystemInfo]$Item,

        [string[]]$ExcludePatterns
    )

    foreach ($Pattern in $ExcludePatterns) {
        if ($Item.Name -like $Pattern) {
            return $true
        }
    }

    return $false
}

function Copy-DirectoryFiltered {
    param(
        [Parameter(Mandatory)]
        [string]$Source,

        [Parameter(Mandatory)]
        [string]$Destination,

        [string[]]$ExcludePatterns = @()
    )

    $Separators = @([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $SourcePath = (Resolve-Path -LiteralPath $Source).Path.TrimEnd($Separators)

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null

    Get-ChildItem -LiteralPath $SourcePath -Recurse -Force | ForEach-Object {
        if (Test-ExcludedPath -Item $_ -ExcludePatterns $ExcludePatterns) {
            return
        }

        $RelativePath = $_.FullName.Substring($SourcePath.Length).TrimStart($Separators)
        $TargetPath = Join-Path $Destination $RelativePath

        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Path $TargetPath -Force | Out-Null
            return
        }

        $TargetParent = Split-Path -Parent $TargetPath
        New-Item -ItemType Directory -Path $TargetParent -Force | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $TargetPath -Force
    }
}

if ([string]::IsNullOrWhiteSpace($TargetDirectory)) {
    if (-not (Test-Path -LiteralPath $PackDirFile)) {
        throw 'PACK_DIR.txt not found. Run scripts/set-pack-dir.ps1 first or pass -TargetDirectory.'
    }

    $TargetDirectory = (Get-Content -LiteralPath $PackDirFile -Raw).Trim()
    Write-Host 'Using PACK_DIR from PACK_DIR.txt'
} else {
    Write-Host 'Using PACK_DIR from -TargetDirectory parameter'
}

if ([string]::IsNullOrWhiteSpace($TargetDirectory)) {
    throw 'PACK_DIR cannot be empty.'
}

if ($Inline -and $FullWipe) {
    throw '-Inline cannot be combined with -FullWipe.'
}

$PackDir = [System.IO.Path]::GetFullPath($TargetDirectory)

if (-not (Test-Path -LiteralPath $PackDir -PathType Container)) {
    throw "PACK_DIR does not exist: $PackDir"
}

$Separators = @([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
$PackRoot = [System.IO.Path]::GetPathRoot($PackDir)
if ([string]::Equals($PackDir.TrimEnd($Separators), $PackRoot.TrimEnd($Separators), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to use filesystem root as PACK_DIR: $PackDir"
}

Write-Host '======================================'
Write-Host 'Reset Modpack and Sync Project'
Write-Host '======================================'
Write-Host "PACK_DIR: $PackDir"
Write-Host "FULL_WIPE: $($FullWipe.IsPresent)"
Write-Host "INLINE: $($Inline.IsPresent)"
Write-Host ''

if ($Inline) {
    $Source = Join-Path $PackConfigsDir 'kubejs'
    $Destination = Join-Path $PackDir 'kubejs'

    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        throw "Source folder not found: $Source"
    }

    Write-Host 'Performing INLINE sync...'
    Write-Host 'Copying folder kubejs ...'
    Copy-DirectoryFiltered -Source $Source -Destination $Destination -ExcludePatterns $ExcludePatterns
    Write-Host ''
    Write-Host 'Inline sync complete!'
    exit 0
}

if ($FullWipe) {
    Write-Host 'Performing FULL wipe...'
    $Folders = @(
        '.mixin.out',
        '.mtsession',
        'backups',
        'config',
        'crash-reports',
        'defaultconfigs',
        'downloads',
        'dynamic-data-pack-cache',
        'dynamic-resource-pack-cache',
        'ESM',
        'ftbbackups3',
        'kubejs',
        'local',
        'logs',
        'moonlight-global-datapacks',
        'patchouli_books',
        'profileImage',
        'saves',
        'screenshots'
    )
    $Files = @('command_history.txt', 'options.txt', 'patchouli_data.json', 'usercache.json', 'usernamecache.json')
} else {
    Write-Host 'Performing MINIMAL wipe...'
    $Folders = @('config', 'defaultconfigs', 'kubejs')
    $Files = @('options.txt')
}

foreach ($Folder in $Folders) {
    $Path = Join-Path $PackDir $Folder
    Write-Host "Deleting folder $Folder ..."
    Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
}

foreach ($File in $Files) {
    $Path = Join-Path $PackDir $File
    Write-Host "Deleting file $File ..."
    Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
}

if ($FullWipe) {
    $ShaderpacksPath = Join-Path $PackDir 'shaderpacks'

    if (Test-Path -LiteralPath $ShaderpacksPath -PathType Container) {
        Write-Host 'Deleting shaderpacks/*.txt files ...'
        Get-ChildItem -LiteralPath $ShaderpacksPath -Filter '*.txt' -File -Force |
            Remove-Item -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ''
Write-Host 'Copying configs and assets to instance folder...'

foreach ($Folder in @('config', 'defaultconfigs', 'kubejs', 'profileImage')) {
    $Source = Join-Path $PackConfigsDir $Folder
    $Destination = Join-Path $PackDir $Folder

    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        Write-Warning "Skipping missing source folder: $Source"
        continue
    }

    Write-Host "Copying folder $Folder ..."
    Copy-DirectoryFiltered -Source $Source -Destination $Destination -ExcludePatterns $ExcludePatterns
}

foreach ($Folder in @('shaderpacks')) {
    $Source = Join-Path $PackConfigsDir $Folder
    $Destination = Join-Path $PackDir $Folder

    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        continue
    }

    Write-Host "Copying folder $Folder ..."
    Copy-DirectoryFiltered -Source $Source -Destination $Destination -ExcludePatterns $ExcludePatterns
}

Write-Host ''
Write-Host 'Modpack reset and synced!'
