@echo off
:: Reinicia o servico Windows da AURA com elevacao automatica
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Permissao de Administrador confirmada.
    echo [*] Reiniciando AuraBackendService...
    net stop AuraBackendService
    net start AuraBackendService
    echo.
    echo [SUCESSO] Servico AURA atualizado e operando na porta 8000!
    timeout /t 3
) else (
    echo [*] Solicitando elevacao de Administrador para reiniciar o servico AURA...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
)
