@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul
title Ecossistema AURA + WhatsApp - Inicializador Unificado
color 0A

echo ======================================================================
echo    ECOSSISTEMA INTEGRADO: AURA LOCAL + PAINEL WHATSAPP CRM
echo    Supervisao de Postos, Telemetria Edge e Orquestracao Autonoma
echo ======================================================================
echo.

REM ----------------------------------------------------------------------
REM 1. VERIFICAR E INICIAR DOCKER DESKTOP E CONTAINERS
REM ----------------------------------------------------------------------
echo [1/4] Verificando status do Docker Desktop...
docker info >nul 2>&1
if %errorlevel% equ 0 goto DOCKER_RUNNING

echo   - Docker Desktop nao esta rodando. Tentando iniciar o Docker Desktop...
if exist "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe" goto START_DOCKER_LOCAL
if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" goto START_DOCKER_PROG
start "" "Docker Desktop"
goto WAIT_DOCKER_INIT

:START_DOCKER_LOCAL
start "" "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe"
goto WAIT_DOCKER_INIT

:START_DOCKER_PROG
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

:WAIT_DOCKER_INIT
echo   - Aguardando o daemon do Docker responder...
:WAIT_DOCKER_LOOP
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if %errorlevel% equ 0 goto DOCKER_RUNNING
echo     Ainda aguardando o Docker inicializar...
goto WAIT_DOCKER_LOOP

:DOCKER_RUNNING
echo      [OK] Docker Desktop ativo e respondendo!
echo.
echo   - Inicializando containers do ecossistema WhatsApp [Redis, Postgres, Evolution, n8n]...
docker start n3-evolution-redis n3-evolution-postgres >nul 2>&1
timeout /t 1 /nobreak >nul
docker start n3-evolution-api n3-evolution-manager-3030 >nul 2>&1
timeout /t 1 /nobreak >nul
docker start n3-n8n >nul 2>&1
echo      [OK] Containers Docker prontos!
echo.

REM ----------------------------------------------------------------------
REM 2. VERIFICAR E INICIAR MOTOR AURA LOCAL [PORTA 8000]
REM ----------------------------------------------------------------------
echo [2/4] Verificando Motor AURA Local na porta 8000...
netstat -ano | findstr :8000 | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 goto AURA_ALREADY_RUNNING

echo   - Iniciando AURA Local [Python 3.12 / FastAPI] em janela dedicada...
start "AURA Engine - Porta 8000" /D "G:\Projetos\Aila - pgvector" cmd /k "python server.py"
timeout /t 4 /nobreak >nul
echo      [OK] Motor AURA Local inicializado!
goto CHECK_NEXTJS

:AURA_ALREADY_RUNNING
echo      [OK] Motor AURA Local ja esta ativo e escutando na porta 8000!

:CHECK_NEXTJS
echo.

REM ----------------------------------------------------------------------
REM 3. VERIFICAR E INICIAR PAINEL CRM WHATSAPP [PORTA 3000]
REM ----------------------------------------------------------------------
echo [3/4] Verificando Painel WhatsApp CRM na porta 3000...
netstat -ano | findstr :3000 | findstr LISTENING >nul 2>&1
if %errorlevel% equ 0 goto NEXTJS_ALREADY_RUNNING

echo   - Iniciando Painel WhatsApp [Next.js 16] em janela dedicada...
start "Painel WhatsApp - Porta 3000" /D "G:\Projetos\Painel Whatsapp" cmd /k "npm run dev"
timeout /t 4 /nobreak >nul
echo      [OK] Servidor Next.js 16 inicializado!
goto OPEN_BROWSER

:NEXTJS_ALREADY_RUNNING
echo      [OK] Painel WhatsApp ja esta ativo na porta 3000!

:OPEN_BROWSER
echo.

REM ----------------------------------------------------------------------
REM 4. ABRIR COCKPIT INTEGRADO NO NAVEGADOR
REM ----------------------------------------------------------------------
echo [4/4] Abrindo Cockpit Integrado no Navegador...
start "" "http://localhost:3000/partner-mvp"

echo.
echo ======================================================================
echo    ECOSSISTEMA OPERACIONAL 100%% PRONTO:
echo.
echo    - Cockpit AURA / Postos e Redes:  http://localhost:3000/partner-mvp
echo    - WhatsApp CRM / Inbox:          http://localhost:3000/inbox
echo    - AURA Local API / OpenAPI:      http://127.0.0.1:8000/docs
echo    - Cockpit Operacional AURA:      http://127.0.0.1:8000
echo    - Evolution API v2:              http://localhost:8080
echo    - Evolution Manager:             http://localhost:3030
echo    - n8n Workflows e Agentes:       http://localhost:5678
echo ======================================================================
echo.
echo Pressione qualquer tecla para fechar esta janela [os servicos continuam ativos]...
pause >nul
