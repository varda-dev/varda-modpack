@echo off
echo Enter full path to your modpack instance folder:
set /p PACK_DIR=

echo Writing PACK_DIR.txt...
echo %PACK_DIR%> PACK_DIR.txt

echo PACK_DIR.txt written as:
type PACK_DIR.txt

pause