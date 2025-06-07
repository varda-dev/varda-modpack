@echo off
cls

REM === LOAD PACK_DIR ===
set "PACK_DIR_FILE=PACK_DIR.txt"

if not exist "%PACK_DIR_FILE%" (
    echo ERROR: PACK_DIR.txt not found! Please run set_pack_dir.bat first.
    pause
    exit /b
)

set /p PACK_DIR=<"%PACK_DIR_FILE%"
echo Using PACK_DIR: %PACK_DIR%

REM === CONFIGURATION ===
set "varda_dir=%PACK_DIR%"
set "mc_instance_json=%varda_dir%\minecraftinstance.json"
set "varda_srv=%cd%\varda-server"
set "zip_file=%cd%\varda-server.zip"
set "neoforge_url=https://maven.neoforged.net/releases/net/neoforged/neoforged"

REM === PREPARE CLEAN SERVER DIRECTORY ===
if exist "%varda_srv%" rd /s /q "%varda_srv%"
md "%varda_srv%"

REM Copy mods folder
xcopy /s /e /h /y "%varda_dir%\mods" "%varda_srv%\mods\"

REM Copy minecraftinstance.json
copy /y "%varda_dir%\minecraftinstance.json" "%varda_srv%\"

REM Copy in pack-configs -> server config
xcopy /s /e /h /y "pack-configs" "%varda_srv%\config\"

REM === REMOVE CLIENT-ONLY MODS ===
for %%M in (
    "appleskin-neoforge-mc1.21-*.jar"
    "betterf3-*.jar"
    "clean_tooltips-*.jar"
    "cleanview-*.jar"
    "configured-*.jar"
    "controlling-*.jar"
    "craftingtweaks-*.jar"
    "craftpresence-*.jar"
    "comforts-*.jar"
    "embeddium-*.jar"
    "enchdesc-neoforge-*.jar"
    "ExtremeSoundMuffler-*.jar"
    "fastipping-*.jar"
    "inventoryessentials-*.jar"
    "inventorysorter-*.jar"
    "Jade-*.jar"
    "JadeAddons-*.jar"
    "jearchaeology-*.jar"
    "jeed-*.jar"
    "jei-1.21.1-neoforge-*.jar"
    "justenoughbreeding-neoforge-*.jar"
    "JustEnoughProfessions-neoforge-*.jar"
    "JustEnoughResources-NeoForge-*.jar"
    "mousetweaks-*.jar"
    "Searchables-neoforge-1.21.1-*.jar"
    "simplemenu-1.21.1-*.jar"
    "tipsmod-neoforge-1.21.1-*.jar"
    "TravelersTitles-1.21.1-NeoForge-*.jar"
    "villagernames-1.21.1-*.jar"
    "VoidFog-1.21.1-*.jar"
    "yeetusexperimentus-neoforge-*.jar"
) do (
    del "%varda_srv%\mods\%%M"
)

REM === FETCH NEOFORGE INSTALLER ===
for /f "usebackq tokens=*" %%i in (`powershell -noprofile -command "(Get-Content -Path '%mc_instance_json%' -Raw | ConvertFrom-Json).minecraftVersion"`) do set "mc_ver=%%i"
for /f "usebackq tokens=*" %%i in (`powershell -noprofile -command "(Get-Content -Path '%mc_instance_json%' -Raw | ConvertFrom-Json).baseModLoader.forgeVersion"`) do set "neoforge_ver=%%i"

echo Minecraft version: %mc_ver%
echo NeoForge version: %neoforge_ver%

curl -o "%varda_srv%\neoforge-%neoforge_ver%-installer.jar" "https://maven.neoforged.net/releases/net/neoforged/neoforge/%neoforge_ver%/neoforge-%neoforge_ver%-installer.jar"

REM === PACKAGE SERVER ZIP ===
if exist "%zip_file%" del "%zip_file%"

jar -cMfv "%zip_file%" -C "%varda_srv%" .

pause
