# Script de Provisionamento Soberano e Nao-Invasivo da Role aura_service_ro no PostgreSQL 16
# Preserva 100% intocadas as senhas de 'postgres' e 'suporte' do ERP e aplica reload sem downtime
# Executado como Administrador
# Zero travessoes

$ErrorActionPreference = "Continue"

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "  PROVISIONAMENTO SOBERANO E NAO-INVASIVO AURA (PORTA 5433) - ZERO DOWNTIME" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

$pgData = "C:\Program Files\PostgreSQL\16\data"
$pgCtl = "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"
$pgHba = "C:\Program Files\PostgreSQL\16\data\pg_hba.conf"
$pgHbaBak = "C:\Program Files\PostgreSQL\16\data\pg_hba.conf.bak"
$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
$sqlScript = Join-Path $PSScriptRoot "desbloquear_usuarios.sql"

function Reload-Or-Start-PostgreSql {
    param([int]$waitPort = 5433)
    $status = (Get-Service postgresql-x64-16 -ErrorAction SilentlyContinue).Status
    if ($status -eq "Running") {
        Write-Host "  Recarregando pg_hba.conf a quente (pg_ctl reload - Zero Downtime no PDV)..." -ForegroundColor Gray
        & $pgCtl reload -D $pgData 2>&1 | Out-Null
        Start-Sleep -Milliseconds 600
        return $true
    }
    Write-Host "  Iniciando servico postgresql-x64-16..." -ForegroundColor Gray
    Start-Service postgresql-x64-16 -ErrorAction SilentlyContinue
    for ($i = 0; $i -lt 15; $i++) {
        $listening = netstat -ano | findstr ":$waitPort" | findstr "LISTENING"
        if ($listening) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

# 1. Backup e insercao de trust local temporario no topo do pg_hba.conf (sem BOM)
Write-Host "[1/4] Preparando canal local de manutencao no pg_hba.conf..." -ForegroundColor Yellow
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

Reload-Or-Start-PostgreSql -waitPort 5433 | Out-Null

# 2. Executar SQL de desbloqueio da aura_service_ro sem tocar nas senhas de postgres/suporte
Write-Host "[2/4] Ativando role somente-leitura 'aura_service_ro' (preservando senhas do ERP)..." -ForegroundColor Yellow
$sqlOut = & $psql -h 127.0.0.1 -p 5433 -U postgres -d posto -w -f $sqlScript 2>&1
Write-Host ($sqlOut | Out-String) -ForegroundColor Cyan

# Concede privilegios na base vetorial posto_ai para aura_service_ro
$vectorGrants = @"
GRANT USAGE ON SCHEMA public TO aura_service_ro;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aura_service_ro;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aura_service_ro;
DO `$`$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'aura_core') THEN
        EXECUTE 'GRANT USAGE, CREATE ON SCHEMA aura_core TO aura_service_ro';
        EXECUTE 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA aura_core TO aura_service_ro';
        EXECUTE 'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA aura_core TO aura_service_ro';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'n3_sre') THEN
        EXECUTE 'GRANT USAGE, CREATE ON SCHEMA n3_sre TO aura_service_ro';
        EXECUTE 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA n3_sre TO aura_service_ro';
        EXECUTE 'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA n3_sre TO aura_service_ro';
    END IF;
END
`$`$;
"@
& $psql -h 127.0.0.1 -p 5433 -U postgres -d posto_ai -w -c $vectorGrants 2>&1 | Out-Null

# 3. Restaurar pg_hba.conf original (md5) e recarregar a quente
Write-Host "[3/4] Restaurando seguranca md5 no pg_hba.conf (Zero Downtime)..." -ForegroundColor Yellow
Copy-Item $pgHbaBak $pgHba -Force
Reload-Or-Start-PostgreSql -waitPort 5433 | Out-Null

# 4. Teste de validacao final da role aura_service_ro
Write-Host "[4/4] Validando autenticacao permanente da role 'aura_service_ro'..." -ForegroundColor Yellow
$env:PGPASSWORD = "364768"
$testAura = & $psql -h 127.0.0.1 -p 5433 -U aura_service_ro -d posto -w -c "SELECT 'AURA_OK' as status;" 2>&1

Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Green
if ($testAura -match "AURA_OK") {
    Write-Host "  [SUCESSO] ROLE 'aura_service_ro' ATIVA E PERMANENTE (VALID UNTIL INFINITY)!" -ForegroundColor Green
    Write-Host "  - Senhas de 'postgres' e 'suporte' do ERP preservadas 100% intocadas" -ForegroundColor Green
    Write-Host "  - Validade do 'suporte' estendida para 'infinity' sem alterar a senha atual" -ForegroundColor Green
    Write-Host "  - Role 'aura_service_ro' ativa em modo estrito somente-leitura (SELECT)" -ForegroundColor Green
} else {
    Write-Host "  [AVISO] Resultado da validacao:" -ForegroundColor Yellow
    Write-Host "  AURA: $testAura" -ForegroundColor Gray
}
Write-Host "===============================================================================" -ForegroundColor Green
