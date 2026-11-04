@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ===============================================================================
    echo   SOLICITANDO ELEVACAO DE ADMINISTRADOR...
    echo ===============================================================================
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c `\"`\"%~f0`\"`\"' -Verb RunAs" 2>nul
    if %errorlevel% neq 0 (
        echo.
        echo [AVISO] Nao foi possivel abrir como Administrador com clique duplo simples.
        echo.
        echo Por favor, faca o seguinte:
        echo 1. Clique com o BOTAO DIREITO no arquivo: reparar_banco_posto.bat
        echo 2. Clique em 'Executar como Administrador'
        echo.
        pause
    )
    exit /b
)

title Reparar Autenticacao PostgreSQL 16 - PDV e AURA
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0reparar_banco.ps1"
pause
