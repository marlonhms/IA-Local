@echo off
title AURA - Liberar Acesso Celular (Tailscale)
chcp 65001 >nul

echo ======================================================================
echo  AURA // LIBERAR ACESSO NO FIREWALL DO WINDOWS (PORTA 8000)
echo ======================================================================
echo.
echo Solicitando permissao de Administrador para liberar a porta 8000...
echo.

powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -Command \"New-NetFirewallRule -Name Aura-Porta-8000 -DisplayName ''AURA - Web Cockpit (Porta 8000)'' -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any -ErrorAction SilentlyContinue; Write-Host ''[OK] Porta 8000 liberada com sucesso no Firewall!''; Start-Sleep -Seconds 2\"'"

echo [OK] Regra enviada ao Firewall do Windows!
pause
