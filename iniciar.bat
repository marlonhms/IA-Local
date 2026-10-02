@echo off
chcp 65001 > nul
title IA Posto & PDV (pgvector + Gemini)

echo ========================================================
echo   Iniciando IA do Posto (pgvector + Gemini 3.1 Flash)
echo ========================================================
echo.

:: 1. Verificar e iniciar container pgvector se necessario
echo [*] Verificando banco vetorial pgvector (Docker porta 5434)...
docker start pgvector-posto > nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Aviso: Certifique-se de que o Docker Desktop esta aberto.
) else (
    echo [OK] Container pgvector-posto ativo na porta 5434.
)

:: 2. Verificar servico do PostgreSQL local (porta 5433)
echo [*] Verificando servico do PostgreSQL ERP (porta 5433)...
sc query postgresql-x64-16 | find "RUNNING" > nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Servico postgresql-x64-16 ativo na porta 5433.
) else (
    echo [!] Iniciando servico postgresql-x64-16...
    net start postgresql-x64-16 > nul 2>&1
)

echo.
echo ========================================================
echo   Iniciando Agente Inteligente...
echo ========================================================
echo.

cd /d "%~dp0"
python main.py

pause
