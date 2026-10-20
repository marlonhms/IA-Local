@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

:: Verificacao de Privilegios Administrativos
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando privilegios de Administrador para desbloquear o PostgreSQL...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/k `\"%~f0`\"' -Verb RunAs"
    exit /b
)

title Reparar Autenticacao PostgreSQL - PDV e AURA
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\reparar_banco.ps1"
pause

