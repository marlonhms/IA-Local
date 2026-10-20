@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

:: Verificacao de Privilegios Administrativos
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando privilegios de Administrador para desbloquear o PostgreSQL...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

title Reparar Autenticacao PostgreSQL e Desbloquear PDV / AURA
echo ===============================================================================
echo   REPARANDO AUTENTICACAO POSTGRESQL 16 (PORTA 5433) - PDV E AURA
echo ===============================================================================
echo.

:: 1. Finaliza processo de servico travado em STOP_PENDING se existir
for /f "tokens=3" %%a in ('sc queryex AuraBackendService 2^>nul ^| findstr /i "PID"') do (
    if not "%%a"=="0" (
        echo [1/6] Finalizando processo travado do servico Aura (PID %%a)...
        taskkill /F /PID %%a >nul 2>&1
    )
)

:: 2. Backup do pg_hba.conf
echo [2/6] Configurando modo de confianca temporario no PostgreSQL...
copy /Y "C:\Program Files\PostgreSQL\16\data\pg_hba.conf" "C:\Program Files\PostgreSQL\16\data\pg_hba.conf.bak" >nul

:: 3. Criando pg_hba.conf com trust local temporario
powershell -Command "$c = Get-Content 'C:\Program Files\PostgreSQL\16\data\pg_hba.conf'; $c -replace '127.0.0.1/32\s+md5', '127.0.0.1/32            trust' -replace '::1/128\s+md5', '::1/128                 trust' | Set-Content 'C:\Program Files\PostgreSQL\16\data\pg_hba.conf'"

:: 4. Recarregar PostgreSQL
echo [3/6] Recarregando configuracoes do PostgreSQL...
"C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe" reload -D "C:\Program Files\PostgreSQL\16\data" >nul 2>&1
if %errorlevel% neq 0 (
    net stop postgresql-x64-16 >nul 2>&1
    net start postgresql-x64-16 >nul 2>&1
)

:: 5. Aplicar SQL de desbloqueio de senhas
echo [4/6] Desbloqueando usuarios postgres, suporte e aura_service_ro...
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -h 127.0.0.1 -p 5433 -U postgres -d posto -f "%~dp0desbloquear_usuarios.sql"

:: 6. Restaurar pg_hba.conf seguro (md5)
echo [5/6] Restaurando seguranca md5 no pg_hba.conf...
copy /Y "C:\Program Files\PostgreSQL\16\data\pg_hba.conf.bak" "C:\Program Files\PostgreSQL\16\data\pg_hba.conf" >nul
"C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe" reload -D "C:\Program Files\PostgreSQL\16\data" >nul 2>&1
if %errorlevel% neq 0 (
    net stop postgresql-x64-16 >nul 2>&1
    net start postgresql-x64-16 >nul 2>&1
)

echo.
echo ===============================================================================
echo   [OK] AUTENTICACAO DESBLOQUEADA COM SUCESSO!
echo   - Usuario 'suporte' (PDV): senha '123456' renovada sem expiracao
echo   - Usuario 'postgres': senha '123456' renovada sem expiracao
echo   - Usuario 'aura_service_ro' (AURA): senha '123456' ativa com permissoes
echo ===============================================================================
echo.
timeout /t 5 >nul
exit /b 0
