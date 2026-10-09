@echo off
setlocal
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
echo ========================================================
echo   Iniciando Agente Inteligente...
echo ========================================================
echo.

python main.py

pause
