@echo off
setlocal
chcp 65001 > nul
title "AURA - Assistente Executiva de Prontidao"

echo ===========================================================================
echo   AURA - ASSISTENTE EXECUTIVA DE PRONTIDAO
echo   Supervisao Inteligente de Pista, Tanques e Fechamento
echo ===========================================================================
echo.

cd /d "%~dp0"

REM 1. Banco Vetorial e ERP 100% Nativo no Windows (PostgreSQL 16 porta 5433)
echo [*] Modo 100%% Nativo Windows: PostgreSQL 16 com pgvector (sem Docker/WSL).


REM 2. Verificar servico PostgreSQL local (porta 5433)
echo [*] Verificando servico PostgreSQL ERP (porta 5433)...
sc query postgresql-x64-16 2>nul | find "RUNNING" > nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Servico postgresql-x64-16 ativo na porta 5433.
) else (
    echo [!] Tentando iniciar servico postgresql-x64-16...
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
REM 3. Solicitar e validar a senha do dia do ERP (webPosto)
python scripts\solicitar_senha_erp.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Inicializacao cancelada pelo usuario.
    pause
    exit /b %errorlevel%
)

REM Carrega no ambiente a senha atualizada
if exist "backups\erp_password.txt" (
    set /p ERP_DB_PASSWORD=<"backups\erp_password.txt"
)

echo.
echo ===========================================================================
echo   Iniciando Servidor Web e Abrindo Navegador em http://127.0.0.1:8000...
echo ===========================================================================
echo.

python server.py

pause
