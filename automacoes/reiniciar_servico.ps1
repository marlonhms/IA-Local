#Requires -Version 5.1
<#
.SYNOPSIS
    AURA - Reinicia o servico AuraBackendService liberando STOP_PENDING.
#>

$ServiceName = "AuraBackendService"
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   AURA - REINICIAR SERVICO WINDOWS ($ServiceName)                    " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$CurrentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$IsAdmin = $CurrentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $IsAdmin) {
    Write-Host "[!] ERRO: Privilegios de Administrador necessarios." -ForegroundColor Red
    Write-Host "Abra o PowerShell como Administrador e execute este script novamente." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/3] Verificando estado atual do servico $ServiceName..." -ForegroundColor Cyan
$Svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($Svc) {
    Write-Host "  Estado atual: $($Svc.Status)" -ForegroundColor Gray
}

# 1. Finaliza processo PID associado se estiver em STOP_PENDING
Write-Host "[2/3] Localizando e finalizando processos residuais..." -ForegroundColor Cyan
$QueryOut = sc.exe queryex $ServiceName
foreach ($line in $QueryOut) {
    if ($line -match "PID\s*:\s*(\d+)") {
        $PidVal = [int]$matches[1]
        if ($PidVal -gt 0) {
            Write-Host "  Encerrando processo residual PID $PidVal..." -ForegroundColor Yellow
            taskkill.exe /F /PID $PidVal 2>$null | Out-Null
        }
    }
}

Start-Sleep -Seconds 2

# 2. Inicia o servico limpo
Write-Host "[3/3] Iniciando servico $ServiceName..." -ForegroundColor Cyan
Start-Service -Name $ServiceName -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2
$SvcAfter = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
Write-Host "  Novo estado do servico: $($SvcAfter.Status)" -ForegroundColor Green

if ($SvcAfter.Status -eq "Running") {
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "   SERVICO REINICIADO COM SUCESSO!                                    " -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "  Painel Local     : http://localhost:8000" -ForegroundColor White
    Write-Host "  Metricas Prom    : http://localhost:8000/metrics" -ForegroundColor White
    Write-Host "======================================================================" -ForegroundColor Green
} else {
    Write-Host "[!] Nao foi possivel confirmar status Running. Verifique logs." -ForegroundColor Yellow
}
