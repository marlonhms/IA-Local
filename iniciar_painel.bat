@echo off
chcp 65001 > nul
title AURA // Assistente Executiva de Prontidão (Posto & PDV)

echo ===========================================================================
echo   AURA - ASSISTENTE EXECUTIVA DE PRONTIDÃO
echo   Supervisão Inteligente de Pista, Tanques e Fechamento
echo ===========================================================================
echo.

cd /d "%~dp0"

:: 1. Verificar container pgvector se Docker estiver presente
echo [*] Verificando banco vetorial pgvector (Docker porta 5434)...
docker start pgvector-posto > nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Docker container pgvector-posto nao detectado ou Docker fechado.
) else (
    echo [OK] pgvector ativo na porta 5434.
)

:: 2. Verificar servico PostgreSQL local (porta 5433)
echo [*] Verificando servico PostgreSQL ERP (porta 5433)...
sc query postgresql-x64-16 | find "RUNNING" > nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Servico postgresql-x64-16 ativo na porta 5433.
) else (
    echo [!] Tentando iniciar servico postgresql-x64-16...
    net start postgresql-x64-16 > nul 2>&1
    sc query postgresql-x64-16 | find "RUNNING" > nul 2>&1
    if %errorlevel% neq 0 (
        echo [*] Iniciando PostgreSQL 16 via pg_ctl...
        "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe" start -D "C:\Program Files\PostgreSQL\16\data" > nul 2>&1
    )
)

echo.
:: 3. Solicitar e validar a senha do dia do ERP (webPosto)
python scripts\solicitar_senha_erp.py
if %errorlevel% neq 0 (
    echo [!] Inicialização cancelada pelo usuário.
    pause
    exit /b %errorlevel%
)

:: Carrega no ambiente a senha atualizada
if exist "backups\erp_password.txt" (
    set /p ERP_DB_PASSWORD=<"backups\erp_password.txt"
)

echo.
echo ===========================================================================
echo   Iniciando Servidor Web e Abrindo Navegador em http://127.0.0.1:8000...
echo ===========================================================================
echo.

:: Inicia o servidor Python com FastAPI e Uvicorn (o navegador abrira automaticamente quando o servidor estiver pronto)
python server.py

pause
