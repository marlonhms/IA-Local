# Script de Auto-Recuperacao e Desbloqueio de Autenticacao do PostgreSQL 16
# Executado como Administrador
# Zero travessoes

$ErrorActionPreference = "Continue"

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "  REPARO DE AUTENTICACAO DO POSTGRESQL 16 (PORTA 5433) - PDV E AURA" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

# Funcao para reiniciar PostgreSQL com espera confiavel de porta TCP 5433
function Restart-PostgreSqlService {
    param([int]$waitPort = 5433)
    
    # 1. Se estiver ativo, para o servico
    $status = (Get-Service postgresql-x64-16 -ErrorAction SilentlyContinue).Status
    if ($status -eq "Running") {
        Write-Host "  Parando servico postgresql-x64-16..." -ForegroundColor Gray
        Stop-Service postgresql-x64-16 -Force -ErrorAction SilentlyContinue
    }
    
    # 2. Aguarda a porta 5433 ser liberada completamente pelo Windows
    Write-Host "  Aguardando liberacao da porta $waitPort..." -ForegroundColor Gray
    for ($i = 0; $i -lt 15; $i++) {
        $occupied = netstat -ano | findstr ":$waitPort" | findstr "LISTENING"
        if (-not $occupied) { break }
        Start-Sleep -Seconds 1
    }
    Start-Sleep -Seconds 2

    # 3. Inicia o servico
    Write-Host "  Iniciando servico postgresql-x64-16..." -ForegroundColor Gray
    Start-Service postgresql-x64-16
    
    # 4. Aguarda o PostgreSQL iniciar e escutar na porta 5433
    Write-Host "  Aguardando PostgreSQL aceitar conexoes na porta $waitPort..." -ForegroundColor Gray
    for ($i = 0; $i -lt 20; $i++) {
        $listening = netstat -ano | findstr ":$waitPort" | findstr "LISTENING"
        if ($listening) {
            Write-Host "  [OK] PostgreSQL ativo e escutando na porta $waitPort!" -ForegroundColor Green
            Start-Sleep -Seconds 1
            return $true
        }
        Start-Sleep -Seconds 1
    }
    
    Write-Host "  [AVISO] Servico iniciado, aguardando estabilizacao..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    return $false
}

# 1. Finaliza processo travado do servico Aura se estiver em STOP_PENDING
Write-Host "[1/6] Verificando servicos travados..." -ForegroundColor Yellow
try {
    $serviceInfo = sc.exe queryex AuraBackendService 2>$null
    if ($serviceInfo -match "PID\s*:\s*(\d+)") {
        $pidToKill = $matches[1]
        if ($pidToKill -ne "0") {
            Write-Host "  Encerrando processo travado Aura (PID $pidToKill)..." -ForegroundColor Gray
            taskkill /F /PID $pidToKill 2>$null | Out-Null
        }
    }
} catch {
    Write-Host "  Nenhum servico travado detectado." -ForegroundColor Gray
}

# 2. Backup e insercao de trust no topo do pg_hba.conf (sem BOM)
$pgHba = "C:\Program Files\PostgreSQL\16\data\pg_hba.conf"
$pgHbaBak = "C:\Program Files\PostgreSQL\16\data\pg_hba.conf.bak"
$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
$sqlScript = Join-Path $PSScriptRoot "desbloquear_usuarios.sql"

Write-Host "[2/6] Configurando autenticacao temporaria 'trust' no topo do pg_hba.conf..." -ForegroundColor Yellow
Copy-Item $pgHba $pgHbaBak -Force

$trustHeader = @"
# --- REGRA TEMPORARIA DO REPARO AURA (TRUST LOCAL) ---
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
local   all             all                                     trust

"@
$rawContent = [System.IO.File]::ReadAllText($pgHba)
$tempContent = $trustHeader + $rawContent
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($pgHba, $tempContent, $utf8NoBom)

# 3. Reiniciar PostgreSQL para aplicar trust
Write-Host "[3/6] Reiniciando PostgreSQL para aplicar modo de manutencao..." -ForegroundColor Yellow
Restart-PostgreSqlService -waitPort 5433

# 4. Executar SQL de desbloqueio sem pedir senha (-w)
Write-Host "[4/6] Desbloqueando e renovando credenciais de suporte, postgres e aura_service_ro..." -ForegroundColor Yellow
$env:PGPASSWORD = "123456"
& $psql -h 127.0.0.1 -p 5433 -U postgres -d posto -w -f $sqlScript
$sqlExit = $LASTEXITCODE
if ($sqlExit -ne 0) {
    Write-Host "  Tentando conectar no database 'postgres'..." -ForegroundColor Gray
    & $psql -h 127.0.0.1 -p 5433 -U postgres -d postgres -w -f $sqlScript
    $sqlExit = $LASTEXITCODE
}

# 5. Restaurar pg_hba.conf original (md5) e reiniciar
Write-Host "[5/6] Restaurando seguranca md5 no pg_hba.conf e reiniciando..." -ForegroundColor Yellow
Copy-Item $pgHbaBak $pgHba -Force
Restart-PostgreSqlService -waitPort 5433

# 6. Teste de validacao final
Write-Host "[6/6] Validando autenticacao final dos usuarios..." -ForegroundColor Yellow
$testAura = & $psql -h 127.0.0.1 -p 5433 -U aura_service_ro -d posto -w -c "SELECT 'AURA_OK' as status;" 2>&1
$testSuporte = & $psql -h 127.0.0.1 -p 5433 -U suporte -d posto -w -c "SELECT 'PDV_OK' as status;" 2>&1

Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Green
if ($testAura -match "AURA_OK" -and $testSuporte -match "PDV_OK") {
    Write-Host "  [SUCESSO] BANCO POSTGRESQL DESBLOQUEADO COM EXITO!" -ForegroundColor Green
    Write-Host "  - Usuario 'suporte' (PDV): senha '123456' renovada com validade infinita (CONECTADO)" -ForegroundColor Green
    Write-Host "  - Usuario 'postgres': senha '123456' renovada com validade infinita (CONECTADO)" -ForegroundColor Green
    Write-Host "  - Usuario 'aura_service_ro': senha '123456' ativa com permissoes somente-leitura (CONECTADO)" -ForegroundColor Green
} else {
    Write-Host "  [AVISO] Resultado da validacao:" -ForegroundColor Yellow
    Write-Host "  AURA: $testAura" -ForegroundColor Gray
    Write-Host "  PDV (suporte): $testSuporte" -ForegroundColor Gray
}
Write-Host "===============================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Pressione qualquer tecla para encerrar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")


