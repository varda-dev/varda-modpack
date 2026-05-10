@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "MODS_FILE=varda-mods.txt"
set "MODS_DIR=mods"
set "STATE_FILE=%MODS_DIR%\.varda-mods-installed.txt"
set "STATE_TMP=%MODS_DIR%\.varda-mods-installed.txt.new"

if not exist "%MODS_FILE%" (
  echo error: missing %MODS_FILE%
  exit /b 1
)

if not exist "%MODS_DIR%" mkdir "%MODS_DIR%" || exit /b 1

where curl.exe >nul 2>nul
if not errorlevel 1 (
  set "DOWNLOAD_TOOL=curl"
) else (
  where powershell.exe >nul 2>nul || (
    echo error: curl.exe or powershell.exe is required to install Varda server mods.
    exit /b 1
  )
  set "DOWNLOAD_TOOL=powershell"
)

if exist "%STATE_TMP%" del /f /q "%STATE_TMP%" >nul 2>nul
type nul > "%STATE_TMP%" || exit /b 1

for /f "usebackq tokens=1,2,3,4,5,6,* delims=|" %%A in ("%MODS_FILE%") do (
  set "PROJECT_ID=%%A"
  set "FILE_ID=%%B"
  set "REQUIRED=%%C"
  set "FILE_NAME=%%D"
  set "SIZE=%%E"
  set "SHA1=%%F"
  set "URL=%%G"

  if not "!PROJECT_ID!"=="" if not "!PROJECT_ID:~0,1!"=="#" (
    if /I "!REQUIRED!"=="true" (
      call :ProcessEntry "!PROJECT_ID!" "!FILE_ID!" "!REQUIRED!" "!FILE_NAME!" "!SIZE!" "!SHA1!" "!URL!"
      if errorlevel 1 exit /b 1
    )
  )
)

call :CleanupStaleTrackedMods "%STATE_FILE%" || exit /b 1
move /y "%STATE_TMP%" "%STATE_FILE%" >nul || exit /b 1

echo Done.
exit /b 0

:ProcessEntry
setlocal EnableDelayedExpansion
set "PROJECT_ID=%~1"
set "FILE_ID=%~2"
set "REQUIRED=%~3"
set "FILE_NAME=%~4"
set "SIZE=%~5"
set "SHA1=%~6"
set "URL=%~7"

if "%FILE_NAME%"=="" (
  echo error: invalid varda-mods.txt entry for project %PROJECT_ID% file %FILE_ID%
  exit /b 1
)

if "%URL%"=="" (
  echo error: invalid varda-mods.txt entry for project %PROJECT_ID% file %FILE_ID%
  exit /b 1
)

set "OUTPUT=%MODS_DIR%\%FILE_NAME%"

if exist "%OUTPUT%" (
  call :ValidateFile "%OUTPUT%" "%SIZE%" "%SHA1%"
  if not errorlevel 1 (
    echo Already valid: %FILE_NAME%
    call :AppendStateLine "%PROJECT_ID%" "%FILE_ID%" "%FILE_NAME%" "%SHA1%"
    exit /b 0
  )
)

call :DownloadAndReplace "%PROJECT_ID%" "%FILE_ID%" "%FILE_NAME%" "%SIZE%" "%SHA1%" "%URL%" "%OUTPUT%"
if errorlevel 1 exit /b 1

call :AppendStateLine "%PROJECT_ID%" "%FILE_ID%" "%FILE_NAME%" "%SHA1%"
exit /b 0

:DownloadAndReplace
setlocal EnableDelayedExpansion
set "PROJECT_ID=%~1"
set "FILE_ID=%~2"
set "FILE_NAME=%~3"
set "SIZE=%~4"
set "SHA1=%~5"
set "URL=%~6"
set "OUTPUT=%~7"
set "TEMP_FILE=%MODS_DIR%\.varda-mod-%RANDOM%-%RANDOM%.tmp"

if exist "%TEMP_FILE%" del /f /q "%TEMP_FILE%" >nul 2>nul

echo Downloading %FILE_NAME%...
call :DownloadFile "%URL%" "%TEMP_FILE%"
if errorlevel 1 (
  del /f /q "%TEMP_FILE%" >nul 2>nul
  echo error: download failed for %FILE_NAME%
  exit /b 1
)

call :ValidateFile "%TEMP_FILE%" "%SIZE%" "%SHA1%"
if errorlevel 1 (
  del /f /q "%TEMP_FILE%" >nul 2>nul
  echo error: validation failed for %FILE_NAME%
  exit /b 1
)

move /y "%TEMP_FILE%" "%OUTPUT%" >nul || (
  del /f /q "%TEMP_FILE%" >nul 2>nul
  echo error: could not move %FILE_NAME% into place
  exit /b 1
)

echo Installed: %FILE_NAME%
exit /b 0

:DownloadFile
setlocal
set "URL=%~1"
set "TARGET=%~2"

if /I "%DOWNLOAD_TOOL%"=="curl" (
  curl.exe -fL --retry 3 --retry-delay 5 -o "%TARGET%" "%URL%"
  exit /b !errorlevel!
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri ""%URL%"" -OutFile ""%TARGET%"""
exit /b !errorlevel!

:ValidateFile
setlocal EnableDelayedExpansion
set "FILE_PATH=%~1"
set "EXPECTED_SIZE=%~2"
set "EXPECTED_SHA1=%~3"

if not exist "%FILE_PATH%" exit /b 1

if not "%EXPECTED_SIZE%"=="" (
  for %%I in ("%FILE_PATH%") do set "ACTUAL_SIZE=%%~zI"
  if not "!ACTUAL_SIZE!"=="%EXPECTED_SIZE%" exit /b 1
)

if not "%EXPECTED_SHA1%"=="" (
  where certutil >nul 2>nul
  if not errorlevel 1 (
    set "ACTUAL_SHA1="
    for /f "usebackq delims=" %%H in (`certutil -hashfile "%FILE_PATH%" SHA1 ^| findstr /R /I "^[0-9A-F][0-9A-F ]*$"`) do set "ACTUAL_SHA1=%%H"
    if not defined ACTUAL_SHA1 exit /b 1
    set "ACTUAL_SHA1=!ACTUAL_SHA1: =!"
    if /I not "!ACTUAL_SHA1!"=="%EXPECTED_SHA1%" exit /b 1
  )
)

exit /b 0

:AppendStateLine
>>"%STATE_TMP%" echo %~1^|%~2^|%~3^|%~4
exit /b 0

:CleanupStaleTrackedMods
setlocal EnableDelayedExpansion
set "STATE_PATH=%~1"

if not exist "%STATE_PATH%" exit /b 0
if not exist "%STATE_TMP%" exit /b 0

for /f "usebackq tokens=1,2,3,4 delims=|" %%A in ("%STATE_PATH%") do (
  set "OLD_PROJECT=%%A"
  set "OLD_FILE=%%C"

  if not "!OLD_PROJECT!"=="" if not "!OLD_PROJECT:~0,1!"=="#" (
    set "KEEP=0"
    for /f "usebackq tokens=1,2,3,4 delims=|" %%E in ("%STATE_TMP%") do (
      if "%%E"=="!OLD_PROJECT!" if "%%G"=="!OLD_FILE!" set "KEEP=1"
    )

    if "!KEEP!"=="0" if not "!OLD_FILE!"=="" if exist "%MODS_DIR%\!OLD_FILE!" del /f /q "%MODS_DIR%\!OLD_FILE!" >nul 2>nul
  )
)

exit /b 0
