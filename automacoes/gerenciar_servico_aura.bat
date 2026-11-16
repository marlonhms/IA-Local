@echo off
setlocal EnableDelayedExpansion
title AURA - Gerenciador do Servico Windows SCM Nativo (AuraBackendService)

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

set "PYTHON_BIN=python"
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_BIN=%PROJECT_ROOT%\.venv\Scripts\python.exe"
)

set "ACTION=%~1"
if /I "%ACTION%"=="status" goto :DO_STATUS
if /I "%ACTION%"=="info" goto :DO_INFO
if /I "%ACTION%"=="help" goto :SHOW_HELP
if /I "%ACTION%"=="--help" goto :SHOW_HELP

REM Verifica privilegios de Administrador para operacoes no SCM
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Solicitando privilegios de Administrador (UAC) para gerenciar o servico Windows...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs"
    exit /b 0
)

if /I "%ACTION%"=="install" goto :DO_INSTALL
if /I "%ACTION%"=="start" goto :DO_START
if /I "%ACTION%"=="stop" goto :DO_STOP
if /I "%ACTION%"=="restart" goto :DO_RESTART
if /I "%ACTION%"=="uninstall" goto :DO_UNINSTALL

:MENU
cls
echo ======================================================================
echo    AURA - GERENCIADOR DE SERVICO WINDOWS SCM (AuraBackendService)
echo ======================================================================
echo  Diretorio Raiz : %PROJECT_ROOT%
echo  Python Runtime : %PYTHON_BIN%
echo ----------------------------------------------------------------------
"%PYTHON_BIN%" "%PROJECT_ROOT%\server.py" --service-status
echo ----------------------------------------------------------------------
echo  [1] Instalar / Atualizar Servico Nativo (sc.exe + Auto-Restart)
echo  [2] Iniciar Servico (Start)
echo  [3] Parar Servico (Stop)
echo  [4] Reiniciar Servico (Restart)
echo  [5] Exibir Diagnostico Detalhado (JSON Info + Health State)
echo  [6] Remover Servico (Uninstall)
echo  [0] Sair
echo ======================================================================
set /p "OPT=Escolha uma opcao [0-6]: "

if "%OPT%"=="1" goto :DO_INSTALL
if "%OPT%"=="2" goto :DO_START
if "%OPT%"=="3" goto :DO_STOP
if "%OPT%"=="4" goto :DO_RESTART
if "%OPT%"=="5" goto :DO_INFO_PAUSE
if "%OPT%"=="6" goto :DO_UNINSTALL
if "%OPT%"=="0" exit /b 0
goto :MENU

:DO_INSTALL
echo.
echo [*] Registrando servico nativo AuraBackendService no SCM...
"%PYTHON_BIN%" "%PROJECT_ROOT%\server.py" --install-service
if "%ACTION%"=="" (
    pause
    goto :MENU
)
exit /b %errorlevel%

:DO_START
echo.
echo [*] Iniciando servico AuraBackendService...
"%PYTHON_BIN%" "%PROJECT_ROOT%\server.py" --start-service
if "%ACTION%"=="" (
    pause
    goto :MENU
)
exit /b %errorlevel%

:DO_STOP
echo.
echo [*] Parando servico AuraBackendService...
"%PYTHON_BIN%" "%PROJECT_ROOT%\server.py" --stop-service
if "%ACTION%"=="" (
    pause
    goto :MENU
)
exit /b %errorlevel%

:DO_RESTART
echo.
echo [*] Reiniciando servico AuraBackendService...
"%PYTHON_BIN%" "%PROJECT_ROOT%\server.py" --stop-service
timeout /t 2 /nobreak >nul
"%PYTHON_BIN%" "%PROJECT_ROOT%\server.py" --start-service
if "%ACTION%"=="" (
    pause
    goto :MENU
)
exit /b %errorlevel%

:DO_UNINSTALL
echo.
echo [*] Removendo servico AuraBackendService...
"%PYTHON_BIN%" "%PROJECT_ROOT%\server.py" --uninstall-service
if "%ACTION%"=="" (
    pause
    goto :MENU
)
exit /b %errorlevel%

:DO_STATUS
"%PYTHON_BIN%" "%PROJECT_ROOT%\server.py" --service-status
exit /b %errorlevel%

:DO_INFO
"%PYTHON_BIN%" "%PROJECT_ROOT%\server.py" --service-info
exit /b %errorlevel%

:DO_INFO_PAUSE
echo.
"%PYTHON_BIN%" "%PROJECT_ROOT%\server.py" --service-info
echo.
pause
goto :MENU

:SHOW_HELP
echo Uso: gerenciar_servico_aura.bat [install^|start^|stop^|restart^|status^|info^|uninstall]
exit /b 0
