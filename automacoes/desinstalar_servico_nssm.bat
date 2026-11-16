@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==============================================================================
echo [AURA] Desinstalacao do Servico Nativo do Windows (AuraBackendService)
echo ==============================================================================

:: Define diretorio raiz do projeto
cd /d "%~dp0\.."
set "PROJECT_ROOT=%CD%"
set "SERVICE_NAME=AuraBackendService"
set "BIN_DIR=%PROJECT_ROOT%\bin"
set "NSSM_EXE=%BIN_DIR%\nssm.exe"

:: 1. Verificacao de Privilegios Administrativos
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Este script requer permissoes de Administrador para gerenciar servicos do Windows.
    echo Por favor, clique com o botao direito e selecione "Executar como administrador".
    pause
    exit /b 1
)

:: 2. Parada e Remocao do Servico
if exist "%NSSM_EXE%" (
    echo [INFO] Interrompendo servico %SERVICE_NAME%...
    "%NSSM_EXE%" stop %SERVICE_NAME% >nul 2>&1
    echo [INFO] Removendo servico %SERVICE_NAME%...
    "%NSSM_EXE%" remove %SERVICE_NAME% confirm
) else (
    echo [INFO] nssm.exe nao localizado em %BIN_DIR%. Tentando remocao via comando sc...
    sc stop %SERVICE_NAME% >nul 2>&1
    sc delete %SERVICE_NAME%
)

echo.
echo ==============================================================================
echo [OK] Servico %SERVICE_NAME% removido com sucesso do Windows.
echo ==============================================================================
pause
