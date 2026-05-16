@echo off
REM Register 64bit INDI OCX. RUN AS ADMINISTRATOR.

setlocal

set INDI_DIR=C:\SHINHAN-i\indi
set OCX=%INDI_DIR%\giexpertcontrol64.ocx

if not exist "%OCX%" (
    echo [ERROR] file not found: %OCX%
    pause
    exit /b 1
)

REM Put INDI dir on PATH so dependent DLLs resolve.
set PATH=%INDI_DIR%;%PATH%
pushd "%INDI_DIR%"

echo Registering 64bit INDI OCX
echo   File : %OCX%
echo   Cwd  : %CD%
echo   PATH : %INDI_DIR% prepended
echo.
echo NOTE: If this fails with code 3, try:
echo   1. Launch INDI HTS first (so dependent DLLs are loaded into memory)
echo   2. Then re-run this bat as Administrator
echo.

C:\Windows\System32\regsvr32.exe "%OCX%"
set RC=%ERRORLEVEL%

popd

echo.
echo regsvr32 ExitCode = %RC%
if %RC% neq 0 (
    echo   3 = DllRegisterServer failed
    echo   5 = access denied (need Administrator)
    echo [FAIL]
    pause
    exit /b 1
)

echo [OK] Registered. Run verify_ocx.ps1 to confirm:
echo   powershell -ExecutionPolicy Bypass -File verify_ocx.ps1
pause
