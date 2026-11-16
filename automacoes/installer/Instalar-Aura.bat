@echo off
setlocal EnableDelayedExpansion
title AURA - Instalador Standalone 1-Clique (Fase 8)

REM ==============================================================================
REM Instalar-Aura.bat
REM Instalador autonomo de um clique para estacoes de pista e caixas de postos.
REM Auto-elevacao de privilegios UAC, registro de servico nativo e firewall.
REM Regra inegociavel: ZERO travessoes em todo o arquivo.
REM ==============================================================================

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..") do set "PROJECT_ROOT=%%~fI"

REM 1. Verifica privilegios de Administrador (UAC)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Solicitando privilegios de Administrador para instalar o servico...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs"
    exit /b 0
)

cls
echo ======================================================================
echo    AURA - INSTALADOR STANDALONE DE BORDA (PRODUCAO ENTERPRISE)
echo ======================================================================
echo  Data / Versao    : Outubro 2026 - v2.1.0-PRO
echo  Destino do SCM   : AuraBackendService (Supervisor-Worker Nativo)
echo ======================================================================
echo.

REM 2. Localiza o executavel binario standalone AuraBackend.exe
set "AURA_EXE="
if exist "%SCRIPT_DIR%AuraBackend.exe" (
    set "AURA_EXE=%SCRIPT_DIR%AuraBackend.exe"
) else if exist "%SCRIPT_DIR%..\..\dist\AuraBackend\AuraBackend.exe" (
    set "AURA_EXE=%SCRIPT_DIR%..\..\dist\AuraBackend\AuraBackend.exe"
) else if exist "%PROJECT_ROOT%\dist\AuraBackend\AuraBackend.exe" (
    set "AURA_EXE=%PROJECT_ROOT%\dist\AuraBackend\AuraBackend.exe"
)

if defined AURA_EXE (
    echo [OK] Binario Standalone compilado detectado:
    echo      !AURA_EXE!
    goto :PROCEED_INSTALL
)

REM Fallback: se executavel compilado nao existir, verifica Python local
echo [*] Executavel dist\AuraBackend\AuraBackend.exe nao encontrado.
echo [*] Verificando ambiente Python local para execucao direta...
set "PYTHON_EXE=python"
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] ERRO: Nem o binario standalone nem o Python foram encontrados.
    echo     Execute primeiro a compilacao via: powershell scripts\build_aura_standalone.ps1
    pause
    exit /b 1
)

echo [OK] Runtime Python detectado: %PYTHON_EXE%
set "AURA_EXE=%PYTHON_EXE% \"%PROJECT_ROOT%\server.py\""

:PROCEED_INSTALL
REM 3. Provisionamento de diretorios no ProgramData
echo [*] Criando diretorios de dados e logs em %%ProgramData%%\Aura...
if not exist "%ProgramData%\Aura\data" mkdir "%ProgramData%\Aura\data" >nul 2>&1
if not exist "%ProgramData%\Aura\logs" mkdir "%ProgramData%\Aura\logs" >nul 2>&1
echo [OK] Diretorios estruturais preparados com sucesso.

REM 4. Configuracao da regra de Firewall para a porta 8000
echo [*] Configurando regra de entrada no Firewall do Windows (Porta 8000)...
netsh advfirewall firewall delete rule name="AURA Local AI (Porta 8000)" >nul 2>&1
netsh advfirewall firewall add rule name="AURA Local AI (Porta 8000)" dir=in action=allow protocol=TCP localport=8000 profile=any >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Regra no Firewall criada com sucesso.
) else (
    echo [WARN] Nao foi possivel configurar o Firewall automaticamente. Verifique manualmente.
)

REM 5. Instalacao e registro do Servico Windows SCM
echo [*] Registrando AuraBackendService no Windows SCM...
!AURA_EXE! --install-service
if %errorlevel% neq 0 (
    echo [!] AVISO: Registro retornou codigo %errorlevel%. Tentando prosseguir...
)

REM 6. Inicializacao do Servico
echo [*] Iniciando servico AuraBackendService...
!AURA_EXE! --start-service
if %errorlevel% neq 0 (
    echo [*] Verificando com sc.exe...
    sc.exe start AuraBackendService >nul 2>&1
)

REM 7. Verificacao de Status
echo.
echo ======================================================================
echo    STATUS DO SERVICO WINDOWS INSTALADO
echo ======================================================================
!AURA_EXE! --service-status
echo ======================================================================

REM 8. Abertura da Interface Web
echo [*] Abrindo interface AURA no navegador padrao (http://localhost:8000)...
timeout /t 2 /nobreak >nul 2>&1
start http://localhost:8000

echo.
echo [OK] Instalacao concluida com sucesso! A AURA esta ativa e operando em segundo plano.
echo      Para gerenciar o servico, utilize: scripts\gerenciar_servico_aura.bat
echo.
pause
exit /b 0
