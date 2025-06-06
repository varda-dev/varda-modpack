@echo off
echo ======================================
echo Reset Modpack and Sync Project
echo ======================================
echo.

REM === LOAD PACK_DIR ===
set "PACK_DIR_FILE=PACK_DIR.txt"

if not exist "%PACK_DIR_FILE%" (
    echo ERROR: PACK_DIR.txt not found! Please run set_pack_dir.bat first.
    pause
    exit /b
)

set /p PACK_DIR=<"%PACK_DIR_FILE%"

echo Using PACK_DIR:
echo %PACK_DIR%
echo.

REM === CLEAN ===
echo ======================================
echo Cleaning instance folder...
echo ======================================
echo.

REM --- Delete everything but the mods folder ---
REM --- FOLDERS ---
for %%F in (
    ".mixin.out"
    ".mtsession"
    "backups"
    "config"
    "configureddefaults"
    "crash-reports"
    "datapacks"
    "defaultconfigs"
    "downloads"
    "ESM"
    "kubejs"
    "local"
    "logs"
    "patchouli_books"
    "profileimage"
    "resourcepacks"
    "saves"
    "shaderpacks"
) do (
    echo Deleting folder %%F ...
    rmdir /s /q "%PACK_DIR%\%%F" 2>nul
)

REM --- FILES ---
for %%F in (
    "command_history.txt"
    "options.txt"
    "patchouli_data.json"
    "usercache.json"
    "usernamecache.json"
) do (
    echo Deleting file %%F ...
    del /q "%PACK_DIR%\%%F" 2>nul
)

echo.
echo Done cleaning %PACK_DIR%.
echo.

REM === COPY CONFIGS ===
echo ======================================
echo Copying configs to instance folder...
echo ======================================
echo.

REM --- COPY EACH FOLDER ---
for %%F in (
    "configureddefaults"
    "defaultconfigs"
    "kubejs"
    "profileImage"
) do (
    echo Copying folder %%F ...
    xcopy /e /i /y /exclude:exclude_patterns.txt "pack-configs\%%F" "%PACK_DIR%\%%F" >nul
)

echo.
echo Done copying configs to %PACK_DIR%.
echo.

REM === COMPLETE ===
echo ======================================
echo Modpack prep complete!
echo ======================================
pause
