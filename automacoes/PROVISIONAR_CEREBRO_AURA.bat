@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

set "PS1_TARGET=%~dp0provisionar_cerebro_aura.ps1"

:: Verificacao de Privilegios Administrativos
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando privilegios de Administrador para provisionar o Cerebro Autonomo da AURA ^(posto_ai^)...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$q=[char]34; Start-Process powershell.exe -Verb RunAs -ArgumentList ('-NoExit -NoProfile -ExecutionPolicy Bypass -File ' + $q + $env:PS1_TARGET + $q)"
    if %errorlevel% neq 0 (
        echo.
        echo [ERRO] Nao foi possivel solicitar elevacao automatica ^(UAC^).
        echo Clique com o botao direito neste arquivo e escolha "Executar como Administrador".
        pause
    )
    exit /b
)

title Provisionar Cerebro Autonomo AURA ^(aura_brain_rw -^> posto_ai^)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1_TARGET%"
echo.
pause
