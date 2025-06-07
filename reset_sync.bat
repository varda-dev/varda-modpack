@echo off

REM === INITIAL VARIABLES ===
set "PACK_DIR="
set "FULL_WIPE=0"
set "PACK_DIR_FILE=PACK_DIR.txt"
set "NO_PAUSE=0"

REM === PARSE PARAMETERS ===
:parse_args
if "%~1"=="" goto end_parse

if /i "%~1"=="-t" (
    shift
    set "PACK_DIR=%~1"
) else if /i "%~1"=="-f" (
    set "FULL_WIPE=1"
) else if /i "%~1"=="--full" (
    set "FULL_WIPE=1"
) else if /i "%~1"=="-h" (
    goto show_help
) else if /i "%~1"=="--help" (
    goto show_help
) else if /i "%~1"=="--no-pause" (
    set "NO_PAUSE=1"
) else (
    echo WARNING: Unknown parameter %~1
)
shift
goto parse_args

:end_parse

REM === DISPLAY BANNER ===
cls
echo ======================================
echo Reset Modpack and Sync Project
echo ======================================
echo.

REM === LOAD PACK_DIR IF NOT PROVIDED ===
if "%PACK_DIR%"=="" (
    if not exist "%PACK_DIR_FILE%" (
        echo ERROR: PACK_DIR.txt not found! Please run set_pack_dir.bat first or use -t.
        if "%NO_PAUSE%"=="0" pause
        exit /b
    )
    set /p PACK_DIR=<"%PACK_DIR_FILE%"
    echo Using PACK_DIR from PACK_DIR.txt
) else (
    echo Using PACK_DIR from -t parameter
)

echo PACK_DIR: %PACK_DIR%
echo FULL_WIPE: %FULL_WIPE%
echo.

REM === CLEAN ===
echo ======================================
echo Cleaning instance folder...
echo ======================================
echo.

REM --- FOLDERS TO DELETE ---
if "%FULL_WIPE%"=="1" (
    echo Performing FULL wipe...
    set "FOLDERS=.mixin.out .mtsession backups config configureddefaults crash-reports defaultconfigs downloads ESM kubejs local logs patchouli_books profileimage resourcepacks saves"
    set "FILES=command_history.txt options.txt patchouli_data.json usercache.json usernamecache.json"
) else (
    echo Performing MINIMAL wipe...
    set "FOLDERS=config configureddefaults defaultconfigs kubejs"
    set "FILES=options.txt"
)

REM --- DELETE FOLDERS ---
for %%F in (%FOLDERS%) do (
    echo Deleting folder %%F ...
    rmdir /s /q "%PACK_DIR%\%%F" 2>nul
)

REM --- DELETE FILES ---
for %%F in (%FILES%) do (
    echo Deleting file %%F ...
    del /q "%PACK_DIR%\%%F" 2>nul
)

echo.
echo Done cleaning %PACK_DIR%.
echo.

REM === COPY CONFIGS ===
echo ======================================
echo Copying configs and assets to instance folder...
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
echo Done copying configs and assets to %PACK_DIR%.
echo.

REM === COMPLETE ===
echo ======================================
echo Modpack reset and synced!
echo ======================================
if "%NO_PAUSE%"=="0" pause
exit /b

REM === HELP MESSAGE ===
:show_help
echo Usage: reset_sync.bat [options]
echo.
echo Options:
echo   -t "target_directory"   Use the specified target modpack directory
echo   -f, --full              Perform FULL wipe (delete everything but mods and manifest)
echo   --no-pause              Skip final pause (useful for automation/scripts)
echo   -h, --help              Show this help message
echo.
echo If no options are provided, performs a MINIMAL wipe using PACK_DIR.txt
echo.
pause
exit /b
