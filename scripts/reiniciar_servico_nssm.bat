@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title [AURA] Reiniciando Servico AuraBackendService

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
    echo [INFO] Solicitando permissões de Administrador...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/k \"\"%~f0\"\"' -Verb RunAs" 2>nul
    if %errorlevel% neq 0 (
        echo [ERRO] Privilegios de Administrador necessarios para reiniciar o servico.
        echo Por favor, clique com o botao direito no arquivo e selecione "Executar como administrador".
        pause
    )
    exit /b
)

:: 2. Interrompendo o servico se estiver rodando
echo [INFO] Interrompendo servico %SERVICE_NAME%...
if exist "%NSSM_EXE%" (
    "%NSSM_EXE%" stop %SERVICE_NAME% >nul 2>&1
) else (
    net stop %SERVICE_NAME% >nul 2>&1
)

:: 3. Se estiver travado em STOP_PENDING ou processo orfao, encerra imediatamente
for /f "tokens=3" %%p in ('sc queryex %SERVICE_NAME% 2^>nul ^| findstr /i "PID"') do (
    if "%%p" neq "0" (
        echo [INFO] Encerrando processo residual PID %%p...
        taskkill /f /pid %%p >nul 2>&1
    )
)

:: Aguarda 2 segundos para liberacao de portas e descritores
timeout /t 2 /nobreak >nul

:: 4. Inicializando o servico
echo [INFO] Iniciando servico %SERVICE_NAME%...
if exist "%NSSM_EXE%" (
    "%NSSM_EXE%" start %SERVICE_NAME%
) else (
    net start %SERVICE_NAME%
)

echo.
echo ==============================================================================
echo [OK] Servico %SERVICE_NAME% reiniciado com sucesso!
echo - API disponivel em: http://127.0.0.1:8000
echo ==============================================================================
echo.
pause
