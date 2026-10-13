@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==============================================================================
echo [AURA] Instalacao e Inicializacao do Servico Nativo do Windows via NSSM
echo ==============================================================================

:: Define diretorio raiz do projeto
cd /d "%~dp0\.."
set "PROJECT_ROOT=%CD%"
set "SERVICE_NAME=AuraBackendService"
set "BIN_DIR=%PROJECT_ROOT%\bin"
set "LOGS_DIR=%PROJECT_ROOT%\logs"
set "NSSM_EXE=%BIN_DIR%\nssm.exe"

:: 1. Verificacao de Privilegios Administrativos
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Este script requer permissoes de Administrador para gerenciar servicos do Windows.
    echo Por favor, clique com o botao direito e selecione "Executar como administrador".
    pause
    exit /b 1
)

:: 2. Criacao dos Diretorios bin e logs se nao existirem
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

:: 3. Verificacao e Download Automatico do nssm.exe caso ausente
if not exist "%NSSM_EXE%" (
    echo [INFO] nssm.exe nao encontrado em %BIN_DIR%. Iniciando download seguro...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference = 'SilentlyContinue';" ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
        "$dest = '%NSSM_EXE%';" ^
        "$url = 'https://github.com/homebridge/nssm/releases/download/v2.25.1/nssm_x64.exe';" ^
        "try { Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing; Write-Host '[OK] nssm.exe baixado com sucesso.' } catch { Write-Error ('Falha no download: ' + $_.Exception.Message); exit 1 }"
    if not exist "%NSSM_EXE%" (
        echo [ERRO] Nao foi possivel obter o nssm.exe automaticamente.
        pause
        exit /b 1
    )
)

:: 4. Deteccao do Executavel Python
set "PYTHON_EXE="
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
) else if exist "%PROJECT_ROOT%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%\venv\Scripts\python.exe"
) else (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)

if not defined PYTHON_EXE (
    echo [ERRO] Python nao foi localizado no ambiente virtual nem no PATH.
    pause
    exit /b 1
)
echo [OK] Python localizado: %PYTHON_EXE%

:: 5. Configuracao e Instalacao do Servico Windows
echo [INFO] Interrompendo versao anterior do servico se estiver ativa...
"%NSSM_EXE%" stop %SERVICE_NAME% >nul 2>&1

echo [INFO] Configurando servico %SERVICE_NAME%...
"%NSSM_EXE%" install %SERVICE_NAME% "%PYTHON_EXE%" "-m uvicorn core.aura_api:app --host 0.0.0.0 --port 8000 --workers 2" >nul 2>&1
"%NSSM_EXE%" set %SERVICE_NAME% AppDirectory "%PROJECT_ROOT%"
"%NSSM_EXE%" set %SERVICE_NAME% Description "AURA - Motor Cognitivo e IntelligentUI para Postos de Combustiveis"
"%NSSM_EXE%" set %SERVICE_NAME% Start SERVICE_AUTO_START
"%NSSM_EXE%" set %SERVICE_NAME% AppRestartDelay 5000
"%NSSM_EXE%" set %SERVICE_NAME% AppStdout "%LOGS_DIR%\aura_service.log"
"%NSSM_EXE%" set %SERVICE_NAME% AppStderr "%LOGS_DIR%\aura_service.log"
"%NSSM_EXE%" set %SERVICE_NAME% AppRotateFiles 1
"%NSSM_EXE%" set %SERVICE_NAME% AppRotateOnline 1
"%NSSM_EXE%" set %SERVICE_NAME% AppRotateSeconds 86400
"%NSSM_EXE%" set %SERVICE_NAME% AppRotateBytes 10485760

:: 6. Inicializacao do Servico
echo [INFO] Iniciando servico %SERVICE_NAME%...
"%NSSM_EXE%" start %SERVICE_NAME%

echo.
echo ==============================================================================
echo [OK] Servico %SERVICE_NAME% instalado e configurado com sucesso!
echo - Inicializacao automatica: SERVICE_AUTO_START (inicia com o Windows)
echo - Auto-restart em falha: 5000 ms
echo - Logs centralizados em: %LOGS_DIR%\aura_service.log
echo - API disponivel em: http://127.0.0.1:8000
echo ==============================================================================
pause
