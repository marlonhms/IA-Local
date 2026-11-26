# Provisionamento Unico e Isolado do Cerebro Cognitivo AURA (role aura_brain_rw em posto_ai)
# Zero Downtime no PDV: nunca reinicia o PostgreSQL, nunca toca no banco 'posto' nem nas senhas de 'postgres'/'suporte'
# Executa uma unica vez como Administrador para conceder autonomia plena a AURA no seu proprio banco posto_ai
# Zero travessoes

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repoRoot "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = Join-Path $logDir "provisionar_cerebro.log"
try { Start-Transcript -Path $logFile -Append | Out-Null } catch {}

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "  PROVISIONAMENTO DO CEREBRO COGNITIVO AURA (aura_brain_rw -> posto_ai)" -ForegroundColor Cyan
Write-Host "  Zero Downtime no PDV | Isolamento total do banco ERP 'posto'" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan

$envFile = Join-Path $repoRoot ".env"
$sqlFile = Join-Path $repoRoot "scripts\provisionar_aura_brain_rw.sql"
$pgData = "C:\Program Files\PostgreSQL\16\data"
$pgCtl = "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"
$pgHba = Join-Path $pgData "pg_hba.conf"
$pgHbaBak = Join-Path $pgData "pg_hba.conf.aura_brain_bak"
$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
$pgPort = if ($env:VECTOR_DB_PORT) { $env:VECTOR_DB_PORT } else { "5433" }
$py = "C:\Users\Marlon\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

function Invoke-PgReload {
    $svc = Get-Service postgresql-x64-16 -ErrorAction SilentlyContinue
    if ($null -eq $svc -or $svc.Status -ne "Running") {
        throw "Servico postgresql-x64-16 nao esta em execucao."
    }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & $pgCtl reload -D $pgData 2>&1
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($exitCode -ne 0) {
        throw "Falha no pg_ctl reload: $($out | Out-String)"
    }
    Start-Sleep -Milliseconds 350
}

function New-StrongPassword {
    $chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#%*_"
    $bytes = New-Object byte[] 28
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $rng.Dispose()
    $sb = New-Object System.Text.StringBuilder
    foreach ($b in $bytes) {
        [void]$sb.Append($chars[$b % $chars.Length])
    }
    return $sb.ToString()
}

function Set-EnvKey {
    param([string]$Path, [string]$Key, [string]$Value)
    $list = New-Object 'System.Collections.Generic.List[string]'
    if (Test-Path $Path) {
        foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
            $list.Add($line)
        }
    }
    $updated = $false
    for ($i = 0; $i -lt $list.Count; $i++) {
        if ($list[$i] -match "^$Key=") {
            $list[$i] = "$Key=$Value"
            $updated = $true
            break
        }
    }
    if (-not $updated) {
        $list.Add("$Key=$Value")
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($Path, $list.ToArray(), $utf8NoBom)
}

if (-not (Test-Path $sqlFile)) { throw "Script SQL nao encontrado: $sqlFile" }
if (-not (Test-Path $pgHba)) { throw "pg_hba.conf nao encontrado: $pgHba" }
if (-not (Test-Path $psql)) { throw "psql.exe nao encontrado: $psql" }

# Gera senha dedicada para aura_brain_rw (independente das credenciais do ERP)
$brainPass = New-StrongPassword

$mutex = New-Object System.Threading.Mutex($false, "Global\AuraPgRepairLock")
$hasLock = $false
$hbaModified = $false

try {
    try {
        $hasLock = $mutex.WaitOne(15000)
    } catch [System.Threading.AbandonedMutexException] {
        $hasLock = $true
    }
    if (-not $hasLock) { throw "Timeout aguardando mutex Global\AuraPgRepairLock." }

    Write-Host "[1/4] Abrindo canal local temporario restrito ao posto_ai no pg_hba.conf..." -ForegroundColor Yellow
    $originalBytes = [System.IO.File]::ReadAllBytes($pgHba)
    [System.IO.File]::WriteAllBytes($pgHbaBak, $originalBytes)

    $trustHeader = @"
# --- REGRA TEMPORARIA PROVISIONAMENTO CEREBRO AURA (APENAS posto_ai) ---
host    posto_ai        postgres        127.0.0.1/32            trust
host    posto_ai        postgres        ::1/128                 trust

"@
    $rawContent = [System.IO.File]::ReadAllText($pgHba)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($pgHba, $trustHeader + $rawContent, $utf8NoBom)
    $hbaModified = $true
    Invoke-PgReload

    Write-Host "[2/4] Provisionando role 'aura_brain_rw' como dona exclusiva do posto_ai..." -ForegroundColor Yellow
    $sqlBody = [System.IO.File]::ReadAllText($sqlFile)
    $escapedPass = $brainPass.Replace("'", "''")
    $fullSql = "SET aura.brain_rw_password = '$escapedPass';`n$sqlBody"

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $sqlOut = $fullSql | & $psql -h 127.0.0.1 -p $pgPort -U postgres -d posto_ai -w -v ON_ERROR_STOP=1 -t -A 2>&1
    $sqlExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    $sqlText = ($sqlOut | Out-String).Trim()
    if ($sqlExit -ne 0 -or $sqlText -notmatch "AURA_BRAIN_PROVISIONED") {
        throw "Falha ao provisionar aura_brain_rw (exit=$sqlExit): $sqlText"
    }
    Write-Host "  Role aura_brain_rw provisionada com sucesso em posto_ai." -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "[ERRO NO PROVISIONAMENTO] $_" -ForegroundColor Red
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
} finally {
    if ($hbaModified -and (Test-Path $pgHbaBak)) {
        Write-Host "[3/4] Restaurando pg_hba.conf original (Zero Downtime)..." -ForegroundColor Yellow
        try {
            $bakBytes = [System.IO.File]::ReadAllBytes($pgHbaBak)
            [System.IO.File]::WriteAllBytes($pgHba, $bakBytes)
            Invoke-PgReload
            Remove-Item $pgHbaBak -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Error "CRITICO: falha ao restaurar pg_hba.conf: $_"
        }
    }
    if ($hasLock) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}

Write-Host "[4/4] Atualizando .env (VECTOR_DB_USER=aura_brain_rw) e rodando auto-migracao do cerebro..." -ForegroundColor Yellow
Set-EnvKey -Path $envFile -Key "VECTOR_DB_USER" -Value "aura_brain_rw"
Set-EnvKey -Path $envFile -Key "VECTOR_DB_PASSWORD" -Value $brainPass

$env:PGPASSWORD = $brainPass
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$checkOut = & $psql -h 127.0.0.1 -p $pgPort -U aura_brain_rw -d posto_ai -w -t -A -c "SELECT 'AURA_BRAIN_OK';" 2>&1
$checkExit = $LASTEXITCODE
$ErrorActionPreference = $prevEap
Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

if ($checkExit -ne 0 -or ($checkOut | Out-String) -notmatch "AURA_BRAIN_OK") {
    Write-Host "[ERRO] Validacao de login como aura_brain_rw falhou: $($checkOut | Out-String)" -ForegroundColor Red
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
}

Push-Location $repoRoot
try {
    & $py -c "from core.migrations import bootstrap_autonomous_brain_schema; print(bootstrap_autonomous_brain_schema())"
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Green
Write-Host "  [SUCESSO] CEREBRO AUTONOMO DA AURA ATIVADO (aura_brain_rw -> posto_ai)!" -ForegroundColor Green
Write-Host "  - Banco do PDV 'posto': 100% isolado (aura_service_ro somente-leitura)" -ForegroundColor Green
Write-Host "  - Banco da IA 'posto_ai': autonomia plena (aura_brain_rw proprietaria)" -ForegroundColor Green
Write-Host "  - Log salvo em: $logFile" -ForegroundColor Green
Write-Host "  - Reinicie o AuraBackendService (REINICIAR_AURA.bat) para carregar o novo perfil." -ForegroundColor Green
Write-Host "===============================================================================" -ForegroundColor Green
try { Stop-Transcript | Out-Null } catch {}
exit 0
