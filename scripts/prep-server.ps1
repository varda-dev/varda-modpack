[CmdletBinding()]
param(
    [Alias('t')]
    [string]$PackDir,

    [switch]$NoPause
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$PackDirFile = Join-Path $RepoRoot 'PACK_DIR.txt'
$PackConfigsDir = Join-Path $RepoRoot 'pack-configs'

if ([string]::IsNullOrWhiteSpace($PackDir)) {
    if (-not (Test-Path -LiteralPath $PackDirFile)) {
        throw 'PACK_DIR.txt not found. Run scripts/set-pack-dir.ps1 first or pass -PackDir.'
    }

    $PackDir = (Get-Content -LiteralPath $PackDirFile -Raw).Trim()
}

if ([string]::IsNullOrWhiteSpace($PackDir)) {
    throw 'PACK_DIR cannot be empty.'
}

$PackDir = [System.IO.Path]::GetFullPath($PackDir)
$MinecraftInstanceJson = Join-Path $PackDir 'minecraftinstance.json'
$ServerDir = Join-Path $RepoRoot 'varda-server'
$ZipFile = Join-Path $RepoRoot 'varda-server.zip'

if (-not (Test-Path -LiteralPath $MinecraftInstanceJson -PathType Leaf)) {
    throw "minecraftinstance.json not found: $MinecraftInstanceJson"
}

Write-Host "Using PACK_DIR: $PackDir"

if (Test-Path -LiteralPath $ServerDir) {
    Remove-Item -LiteralPath $ServerDir -Recurse -Force
}
New-Item -ItemType Directory -Path $ServerDir -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $PackDir 'mods') -Destination (Join-Path $ServerDir 'mods') -Recurse -Force
Copy-Item -LiteralPath $MinecraftInstanceJson -Destination $ServerDir -Force
Copy-Item -LiteralPath (Join-Path $PackConfigsDir 'config') -Destination (Join-Path $ServerDir 'config') -Recurse -Force
Copy-Item -LiteralPath (Join-Path $PackConfigsDir 'defaultconfigs') -Destination (Join-Path $ServerDir 'defaultconfigs') -Recurse -Force
Copy-Item -LiteralPath (Join-Path $PackConfigsDir 'kubejs') -Destination (Join-Path $ServerDir 'kubejs') -Recurse -Force

$ClientOnlyPatterns = @(
    'appleskin-neoforge-mc1.21-*.jar',
    'betterf3-*.jar',
    'clean_tooltips-*.jar',
    'cleanview-*.jar',
    'configured-*.jar',
    'controlling-*.jar',
    'craftingtweaks-*.jar',
    'craftpresence-*.jar',
    'comforts-*.jar',
    'embeddium-*.jar',
    'enchdesc-neoforge-*.jar',
    'ExtremeSoundMuffler-*.jar',
    'fastipping-*.jar',
    'inventoryessentials-*.jar',
    'inventorysorter-*.jar',
    'Jade-*.jar',
    'JadeAddons-*.jar',
    'jearchaeology-*.jar',
    'jeed-*.jar',
    'jei-1.21.1-neoforge-*.jar',
    'justenoughbreeding-neoforge-*.jar',
    'JustEnoughProfessions-neoforge-*.jar',
    'JustEnoughResources-NeoForge-*.jar',
    'mousetweaks-*.jar',
    'Searchables-neoforge-1.21.1-*.jar',
    'simplemenu-1.21.1-*.jar',
    'tipsmod-neoforge-1.21.1-*.jar',
    'TravelersTitles-1.21.1-NeoForge-*.jar',
    'villagernames-1.21.1-*.jar',
    'VoidFog-1.21.1-*.jar',
    'yeetusexperimentus-neoforge-*.jar'
)

$ServerModsDir = Join-Path $ServerDir 'mods'
foreach ($Pattern in $ClientOnlyPatterns) {
    Get-ChildItem -Path (Join-Path $ServerModsDir $Pattern) -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            Write-Host "Removing client-only mod $($_.Name) ..."
            Remove-Item -LiteralPath $_.FullName -Force
        }
}

$Instance = Get-Content -LiteralPath $MinecraftInstanceJson -Raw | ConvertFrom-Json
$MinecraftVersion = $Instance.minecraftVersion
$NeoForgeVersion = $Instance.baseModLoader.forgeVersion

if ([string]::IsNullOrWhiteSpace($NeoForgeVersion)) {
    throw 'Could not find baseModLoader.forgeVersion in minecraftinstance.json.'
}

Write-Host "Minecraft version: $MinecraftVersion"
Write-Host "NeoForge version: $NeoForgeVersion"

$InstallerName = "neoforge-$NeoForgeVersion-installer.jar"
$InstallerPath = Join-Path $ServerDir $InstallerName
$InstallerUrl = "https://maven.neoforged.net/releases/net/neoforged/neoforge/$NeoForgeVersion/$InstallerName"

Invoke-WebRequest -Uri $InstallerUrl -OutFile $InstallerPath

if (Test-Path -LiteralPath $ZipFile) {
    Remove-Item -LiteralPath $ZipFile -Force
}

$ServerItems = Get-ChildItem -LiteralPath $ServerDir -Force
Compress-Archive -Path $ServerItems.FullName -DestinationPath $ZipFile -Force

Write-Host "Created $ZipFile"

if (-not $NoPause) {
    Read-Host 'Press Enter to continue' | Out-Null
}
