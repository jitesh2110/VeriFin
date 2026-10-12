@echo off
setlocal enabledelayedexpansion
title VeriFin - Safe Folder Rename Tool

echo ======================================================================
echo                VeriFin - Project Root Folder Rename
echo ======================================================================
echo.
echo All code, configurations, scripts, and dependencies have already been
echo updated to 'VeriFin'.
echo.
echo This script will safely rename:
echo   From: C:\D\Dev\Projects\fintel-ai
echo   To:   C:\D\Dev\Projects\VeriFin
echo.

set "PARENT_DIR=C:\D\Dev\Projects"
set "SRC_DIR=%PARENT_DIR%\fintel-ai"
set "DST_DIR=%PARENT_DIR%\VeriFin"

if not exist "%SRC_DIR%" (
    if exist "%DST_DIR%" (
        echo [INFO] '%DST_DIR%' already exists and '%SRC_DIR%' does not.
        echo [SUCCESS] The folder has already been renamed to VeriFin!
        goto :done
    ) else (
        echo [ERROR] Neither '%SRC_DIR%' nor '%DST_DIR%' was found in '%PARENT_DIR%'.
        goto :done
    )
)

if exist "%DST_DIR%" (
    echo [ERROR] Destination folder '%DST_DIR%' already exists!
    echo Please inspect or remove it before proceeding.
    goto :done
)

echo NOTE: If your IDE (VS Code / Antigravity) or terminals are currently open,
echo they may hold a file lock on the directory.
echo.
echo Press any key when you are ready to rename (close IDE/terminals if locked)...
pause >nul

:: Execute rename from parent directory using temporary script to prevent self-locking
set "TEMP_SCRIPT=%TEMP%\do_verifin_rename.bat"
(
    echo @echo off
    echo cd /d "%PARENT_DIR%"
    echo echo Attempting rename...
    echo ren "fintel-ai" "VeriFin"
    echo if errorlevel 1 ^(
    echo     echo.
    echo     echo [LOCKED] The folder could not be renamed because a process is using it.
    echo     echo Please close your IDE, terminals, and any background Node/Python processes,
    echo     echo then run this script again.
    echo ^) else ^(
    echo     echo.
    echo     echo ======================================================================
    echo     echo [SUCCESS] Folder successfully renamed to:
    echo     echo           C:\D\Dev\Projects\VeriFin
    echo     echo ======================================================================
    echo     echo You can now open C:\D\Dev\Projects\VeriFin in your IDE!
    echo ^)
    echo pause
) > "%TEMP_SCRIPT%"

start "" "%TEMP_SCRIPT%"
exit /b 0

:done
echo.
pause
