@echo off
:: Reinicia o servico Windows da AURA com elevacao automatica
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ===================================================
    echo [OK] Permissao de Administrador confirmada.
    echo [*] Reiniciando AuraBackendService...
    echo ===================================================
    net stop AuraBackendService
    timeout /t 2 >nul
    net start AuraBackendService
    echo.
    echo ===================================================
    echo [SUCESSO] Servico AURA reiniciado com o novo motor fiscal!
    echo ===================================================
    timeout /t 4
) else (
    echo Solicitando permissao de Administrador para reiniciar o servico...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
)
