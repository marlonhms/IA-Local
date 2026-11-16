@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul
title "IA Posto e PDV (pgvector + Gemini)"

echo ========================================================
echo   Iniciando IA do Posto (pgvector + Gemini 3.1 Flash)
echo ========================================================
echo.

cd /d "%~dp0"

REM 1. Banco Vetorial e ERP 100% Nativo no Windows (PostgreSQL 16 porta 5433)
echo [*] Modo 100%% Nativo Windows: PostgreSQL 16 com pgvector (sem Docker/WSL).

REM 2. Verificar servico do PostgreSQL local (porta 5433)
echo [*] Verificando servico do PostgreSQL ERP (porta 5433)...
sc query postgresql-x64-16 2>nul | find "RUNNING" > nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Servico postgresql-x64-16 ativo na porta 5433.
) else (
    echo [!] Iniciando servico postgresql-x64-16...
    net start postgresql-x64-16 > nul 2>&1
    sc query postgresql-x64-16 2>nul | find "RUNNING" > nul 2>&1
    if %errorlevel% neq 0 (
        if exist "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe" (
            echo [*] Iniciando PostgreSQL 16 via pg_ctl...
            "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe" start -D "C:\Program Files\PostgreSQL\16\data" > nul 2>&1
        )
    )
)

echo.
REM 3. Validacao Direta de Autenticacao Segura (Cofre DPAPI / aura_service_ro)
python -c "from config.settings import DB_ERP_CONFIG, get_erp_password; import psycopg2; c = psycopg2.connect(host=DB_ERP_CONFIG['host'], port=DB_ERP_CONFIG['port'], dbname=DB_ERP_CONFIG['dbname'], user=DB_ERP_CONFIG['user'], password=get_erp_password(), connect_timeout=3); c.close()" 2>nul
if %errorlevel% equ 0 (
    echo [OK] Autenticacao segura via cofre DPAPI confirmada.
    goto INICIAR_AGENTE
)

echo.
echo [!] Conexao direta com role tecnica falhou. Verificando contingencia...
python scripts\solicitar_senha_erp.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Falha na autenticacao do ERP.
    echo [DICA] Execute o script REPARAR_AUTENTICACAO_BANCO.bat como Administrador para desbloquear as senhas.
    pause
    exit /b 1
)

:INICIAR_AGENTE



echo.
echo ========================================================
echo   Iniciando Agente Inteligente...
echo ========================================================
echo.

python main.py

pause
