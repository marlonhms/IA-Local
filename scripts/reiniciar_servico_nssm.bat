@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==============================================================================
echo [AURA] Reinicializacao do Servico Nativo do Windows (AuraBackendService)
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
    echo [ERRO] Este script requer permissoes de Administrador para reiniciar servicos do Windows.
    echo Por favor, clique com o botao direito e selecione "Executar como administrador".
    pause
    exit /b 1
)

:: 2. Reinicio do Servico
if exist "%NSSM_EXE%" (
    echo [INFO] Reiniciando servico %SERVICE_NAME% via NSSM...
    "%NSSM_EXE%" restart %SERVICE_NAME%
) else (
    echo [INFO] Reiniciando via comandos net stop / net start...
    net stop %SERVICE_NAME% >nul 2>&1
    net start %SERVICE_NAME% >nul 2>&1
)

echo.
echo ==============================================================================
echo [OK] Servico %SERVICE_NAME% reiniciado com sucesso!
echo - API disponivel em: http://127.0.0.1:8000
echo ==============================================================================
pause
