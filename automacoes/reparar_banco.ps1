# Script de Desbloqueio Cirurgico e Nao-Invasivo da Role aura_service_ro no PostgreSQL 16
# Zero Downtime no PDV: usa pg_ctl reload (nunca reinicia o servico PostgreSQL)
# Preserva 100% intocadas as senhas e permissoes de 'postgres' e 'suporte' do ERP
# Executado como Administrador ou LocalSystem (AuraBackendService)
# Zero travessoes

$ErrorActionPreference = "Stop"

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "  DESBLOQUEIO CIRURGICO AURA (PORTA 5433) - ZERO DOWNTIME NO PDV" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan

$pgData = "C:\Program Files\PostgreSQL\16\data"
$pgCtl = "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"
$pgHba = Join-Path $pgData "pg_hba.conf"
$pgHbaBak = Join-Path $pgData "pg_hba.conf.aura_bak"
$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
$pgPort = if ($env:ERP_DB_PORT) { $env:ERP_DB_PORT } else { "5433" }

function Invoke-PgReload {
    $svc = Get-Service postgresql-x64-16 -ErrorAction SilentlyContinue
    if ($null -eq $svc -or $svc.Status -ne "Running") {
        throw "Servico postgresql-x64-16 nao esta em execucao; abortando para nao interferir no PDV."
    }
    $out = & $pgCtl reload -D $pgData 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao recarregar pg_hba.conf via pg_ctl reload: $($out | Out-String)"
    }
    Start-Sleep -Milliseconds 350
}

# Mutex global entre processos para evitar colisao entre workers Uvicorn
$mutex = New-Object System.Threading.Mutex($false, "Global\AuraPgRepairLock")
$hasLock = $false
$hbaModified = $false

try {
    try {
        $hasLock = $mutex.WaitOne(15000)
    } catch [System.Threading.AbandonedMutexException] {
        $hasLock = $true
    }
    if (-not $hasLock) {
        throw "Timeout aguardando mutex Global\AuraPgRepairLock."
    }

    if (-not (Test-Path $pgHba)) {
        throw "Arquivo pg_hba.conf nao encontrado em $pgHba"
    }
    if (-not (Test-Path $psql)) {
        throw "Executavel psql.exe nao encontrado em $psql"
    }

    # 1. Backup e insercao de regra trust local restrita APENAS ao usuario postgres
    Write-Host "[1/3] Abrindo canal local temporario restrito no pg_hba.conf (sem reiniciar PG)..." -ForegroundColor Yellow
    $originalBytes = [System.IO.File]::ReadAllBytes($pgHba)
    [System.IO.File]::WriteAllBytes($pgHbaBak, $originalBytes)

    $trustHeader = @"
# --- REGRA TEMPORARIA DO REPARO AURA (TRUST LOCAL RESTRITO) ---
host    posto           postgres        127.0.0.1/32            trust
host    posto           postgres        ::1/128                 trust
host    posto_ai        postgres        127.0.0.1/32            trust
host    posto_ai        postgres        ::1/128                 trust

"@
    $rawContent = [System.IO.File]::ReadAllText($pgHba)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($pgHba, $trustHeader + $rawContent, $utf8NoBom)
    $hbaModified = $true

    Invoke-PgReload

    # 2. Desbloqueio online exclusivo das roles de servico AURA (sem alterar senhas de postgres/suporte)
    Write-Host "[2/3] Desbloqueando roles 'aura_service_ro' e 'aura_brain_rw' (lock_timeout=1000ms)..." -ForegroundColor Yellow
    $unlockSql = @"
SET lock_timeout = '1000ms';
SET statement_timeout = '3000ms';
DO `$`$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aura_service_ro') THEN
        ALTER ROLE aura_service_ro WITH LOGIN CONNECTION LIMIT -1 VALID UNTIL 'infinity';
    ELSE
        RAISE EXCEPTION 'Role aura_service_ro nao existe no catalogo pg_roles.';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aura_brain_rw') THEN
        ALTER ROLE aura_brain_rw WITH LOGIN CONNECTION LIMIT -1 VALID UNTIL 'infinity';
    END IF;
END
`$`$;
SELECT CASE
    WHEN rolcanlogin AND rolconnlimit <> 0 THEN 'AURA_OK'
    ELSE 'AURA_LOCKED'
END AS status
FROM pg_roles
WHERE rolname = 'aura_service_ro';
"@

    $sqlOut = & $psql -h 127.0.0.1 -p $pgPort -U postgres -d posto -w -v ON_ERROR_STOP=1 -t -A -c $unlockSql 2>&1
    $sqlExit = $LASTEXITCODE
    $sqlText = ($sqlOut | Out-String).Trim()
    Write-Host $sqlText -ForegroundColor Cyan

    if ($sqlExit -ne 0 -or $sqlText -notmatch "AURA_OK") {
        throw "Falha ao confirmar desbloqueio da role aura_service_ro (exit=$sqlExit): $sqlText"
    }
} finally {
    # 3. Restauracao garantida do pg_hba.conf original e reload imediato
    if ($hbaModified -and (Test-Path $pgHbaBak)) {
        Write-Host "[3/3] Restaurando pg_hba.conf original (Zero Downtime)..." -ForegroundColor Yellow
        try {
            $bakBytes = [System.IO.File]::ReadAllBytes($pgHbaBak)
            [System.IO.File]::WriteAllBytes($pgHba, $bakBytes)
            Invoke-PgReload
            Remove-Item $pgHbaBak -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Error "CRITICO: falha ao restaurar pg_hba.conf: $_"
        }
    }
    if ($hasLock) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}

Write-Host "[SUCESSO] Role aura_service_ro desbloqueada com seguranca (AURA_OK)." -ForegroundColor Green
exit 0
