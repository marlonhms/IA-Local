@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title [AURA] Reiniciar AuraBackendService

echo ==============================================================================
echo [AURA] Reinicializacao do Servico Nativo do Windows (AuraBackendService)
echo ==============================================================================

:: 1. Verificacao de Privilegios Administrativos
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] Privilegios de Administrador necessarios para gerenciar o servico.
    echo.
    echo Para prosseguir:
    echo 1. Feche esta janela.
    echo 2. Clique com o BOTAO DIREITO neste arquivo (%~nx0).
    echo 3. Selecione "Executar como administrador".
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0\.."
set "PROJECT_ROOT=%CD%"
set "SERVICE_NAME=AuraBackendService"
set "BIN_DIR=%PROJECT_ROOT%\bin"
set "NSSM_EXE=%BIN_DIR%\nssm.exe"

echo [INFO] Identificando processos residuais do servico %SERVICE_NAME%...
for /f "tokens=3" %%p in ('sc queryex %SERVICE_NAME% 2^>nul ^| findstr /i "PID"') do (
    if "%%p" neq "0" (
        echo [INFO] Finalizando processo PID %%p travado em STOP_PENDING...
        taskkill /f /pid %%p >nul 2>&1
    )
)

echo [INFO] Aguardando liberacao dos recursos do sistema...
timeout /t 3 /nobreak >nul

echo [INFO] Iniciando servico %SERVICE_NAME%...
if exist "%NSSM_EXE%" (
    "%NSSM_EXE%" start %SERVICE_NAME% >nul 2>&1
)
net start %SERVICE_NAME% >nul 2>&1

timeout /t 2 /nobreak >nul

echo.
echo ==============================================================================
sc query %SERVICE_NAME% | findstr /i "STATE"
echo [OK] Servico %SERVICE_NAME% processado com sucesso!
echo - API disponivel em: http://127.0.0.1:8000
echo - Metricas Prometheus: http://127.0.0.1:8000/metrics
echo ==============================================================================
echo.
pause
