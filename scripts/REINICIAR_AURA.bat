@echo off
setlocal EnableDelayedExpansion
title AURA - Reiniciar Servico em 1 Clique

cd /d "%~dp0"

REM 1. Verifica privilegios de Administrador e solicita elevacao UAC
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Solicitando privilegios de Administrador via UAC...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/k \"\"%~f0\"\" elevated' -Verb RunAs"
    exit /b 0
)

echo ======================================================================
echo    AURA - LIBERANDO STOP_PENDING E REINICIANDO SERVICO
echo ======================================================================
echo.

echo [*] Localizando processo residual do servico...
for /f "tokens=3" %%A in ('sc.exe queryex AuraBackendService ^| findstr /i "PID"') do (
    set "SVC_PID=%%A"
    if not "!SVC_PID!"=="0" (
        echo [!] Encerrando processo PID !SVC_PID! forcadamente...
        taskkill.exe /F /T /PID !SVC_PID! >nul 2>&1
    )
)

echo [*] Liberando conexoes presas na porta 8000...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000" ^| findstr /i "LISTENING"') do (
    if not "%%P"=="" (
        echo [!] Finalizando processo na porta 8000 - PID %%P...
        taskkill.exe /F /PID %%P >nul 2>&1
    )
)

timeout /t 2 /nobreak >nul

echo [*] Iniciando servico limpo AuraBackendService...
sc.exe start AuraBackendService >nul 2>&1
if %errorlevel% neq 0 (
    net start AuraBackendService >nul 2>&1
)

timeout /t 3 /nobreak >nul

sc.exe queryex AuraBackendService | findstr /i "STATE" | findstr /i "RUNNING" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ======================================================================
    echo   [SUCESSO] SERVICO AURA REINICIADO COM EXITO!
    echo ======================================================================
    echo   Painel Web: http://127.0.0.1:8000
    echo   Pressione Ctrl + F5 no navegador para atualizar.
    echo ======================================================================
) else (
    echo.
    echo [!] Status atual do servico:
    sc.exe queryex AuraBackendService | findstr /i "STATE"
)

echo.
pause
