@echo off
setlocal EnableExtensions

:: ============================================================================
:: AURA - ATALHO DE INSTALACAO AUTOMATIZADA 1-CLIQUE (WINDOWS ON-PREMISE)
:: Duplo-clique neste arquivo para provisionar o posto automaticamente.
:: ============================================================================

cd /d "%~dp0"

echo ============================================================================
echo    AURA - INICIANDO INSTALADOR AUTOMATIZADO 1-CLIQUE
echo    Diretorio: %CD%
echo ============================================================================

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\instalar_posto.ps1" %*
set EXIT_CODE=%ERRORLEVEL%

:: Se nao estiver em modo automatizado/DryRun, aguarda tecla para fechar a janela
echo "%*" | findstr /I "DryRun" >nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    pause
)

exit /b %EXIT_CODE%
