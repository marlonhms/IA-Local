@echo off
chcp 65001 > nul
title Configurar Ponte Tailscale - Ai.la

:: 1. Verificar Privilégios de Administrador e Auto-Elevar via UAC se necessário
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Solicitando elevacao de Administrador (UAC)...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c `\"%~f0`\"' -Verb RunAs"
    exit /b
)

:: 2. Garantir diretório de trabalho correto (evita cair em System32 ao rodar como Admin)
cd /d "%~dp0"

echo ======================================================================
echo   Ai.la - Configuracao da Ponte de Rede Tailscale (Notebook ^<-> Casa)
echo ======================================================================
echo.

:: 3. Executar script PowerShell com bypass de politica
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\configurar_ponte_tailscale.ps1"

echo.
pause
