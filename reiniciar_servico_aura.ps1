# Reinicia o servico Windows da AURA com elevacao automatica e parada instantanea
# Zero travessoes em todo o arquivo.

$serviceName = "AuraBackendService"

# Verifica se o script esta rodando como Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[*] Solicitando permissao de Administrador..." -ForegroundColor Yellow
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -NoExit -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "[*] Permissao de Administrador confirmada." -ForegroundColor Green
Write-Host "[*] Destravando processo do servico (STOP_PENDING)..." -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Recupera o PID do servico caso esteja travado em STOP_PENDING
try {
    $scOut = sc.exe queryex $serviceName
    $pidLine = $scOut | Where-Object { $_ -match 'PID\s*:\s*(\d+)' }
    if ($pidLine -and $matches[1] -ne '0') {
        $svcPid = $matches[1]
        Write-Host "[*] Destravando processo PID $svcPid (NSSM)..." -ForegroundColor Yellow
        Stop-Process -Id $svcPid -Force -ErrorAction SilentlyContinue
    }
} catch {
    # Ignora
}

# 2. Finaliza processos orfaos na porta 8000
try {
    $conns = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        if ($c.OwningProcess -and $c.OwningProcess -ne 0) {
            Write-Host "[*] Liberando porta 8000 (PID $($c.OwningProcess))..." -ForegroundColor Yellow
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
} catch {
    # Ignora
}

Start-Sleep -Seconds 1

# 3. Inicia o servico
Write-Host "[*] Iniciando $serviceName com novo motor..." -ForegroundColor Cyan
try {
    Start-Service -Name $serviceName -ErrorAction Stop
    Write-Host "`n===================================================" -ForegroundColor Cyan
    Write-Host "[SUCESSO] Servico AURA reiniciado com sucesso!" -ForegroundColor Green
    Write-Host "===================================================`n" -ForegroundColor Cyan
} catch {
    Write-Host "`n[ERRO] Falha ao iniciar o servico: $_" -ForegroundColor Red
}

Start-Sleep -Seconds 3
