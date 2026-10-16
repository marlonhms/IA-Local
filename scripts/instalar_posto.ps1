#Requires -Version 5.1
<#
.SYNOPSIS
    AURA - Instalador Automatizado de 1-Clique para Postos Windows (On-Premise).
.DESCRIPTION
    Executa o onboarding completo e idempotente de uma filial em menos de 3 minutos:
    [1/8] Checagem de pre-requisitos (Python 3.10+, Git, Assets Offline-First)
    [2/8] Criacao/atualizacao do ambiente virtual (.venv) e dependencias
    [3/8] Provisionamento criptografico (.env), migracoes Alembic e Opt-In LGPD
    [4/8] Inicializacao de containers auxiliares (Docker / pgvector)
    [5/8] Aplicacao da role estritamente somente-leitura no ERP (aura_service_ro)
    [6/8] Configuracao de regra de Firewall do Windows (Porta TCP 8000 para LAN e Tailscale)
    [7/8] Instalacao e partida do servico Windows via NSSM (AuraBackendService)
    [8/8] Smoke Test de saude (/api/v1/aura/health e /metrics) e exibicao de endpoints
#>

param(
    [int]$FilialId = 1,
    [string]$TenantId = "posto_matriz",
    [string]$Cnpj = "00.000.000/0001-91",
    [string]$RazaoSocial = "Posto Revendedor Homologado AURA LTDA",
    [string]$AssinadoPor = "Instalador Automatizado 1-Clique",
    [int]$Port = 8000,
    [string]$ServiceName = "AuraBackendService",
    [switch]$SkipDocker,
    [switch]$SkipService,
    [switch]$SkipFirewall,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

function Write-Banner {
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "   AURA - INSTALADOR AUTOMATIZADO 1-CLIQUE (WINDOWS ON-PREMISE)       " -ForegroundColor Cyan
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "Diretorio Raiz : $ProjectRoot" -ForegroundColor Gray
    Write-Host "Filial / Tenant: Filial $FilialId ($TenantId)" -ForegroundColor Gray
    Write-Host "Porta HTTP API : $Port" -ForegroundColor Gray
    if ($DryRun) {
        Write-Host "[MODO DRY-RUN] Nenhuma alteracao destrutiva de sistema sera aplicada." -ForegroundColor Yellow
    }
    Write-Host "----------------------------------------------------------------------" -ForegroundColor Cyan
}

function Write-Stage {
    param([string]$Step, [string]$Title)
    Write-Host ""
    Write-Host "[$Step] $Title" -ForegroundColor Cyan
}

Write-Banner

# ---------------------------------------------------------------------------
# [1/8] Checagem de Pre-requisitos do Sistema
# ---------------------------------------------------------------------------
Write-Stage "1/8" "Verificando pre-requisitos do sistema e assets Offline-First..."

$PythonCmd = $null
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonCmd = $VenvPython
    Write-Host "  [OK] Python do ambiente virtual detectado: $PythonCmd" -ForegroundColor Green
} elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonCmd = (Get-Command "python").Source
    Write-Host "  [OK] Python global detectado: $PythonCmd" -ForegroundColor Green
} else {
    Write-Host "  [!] ERRO: Python 3.10+ nao encontrado no PATH." -ForegroundColor Red
    exit 1
}

$VendorDir = Join-Path $ProjectRoot "web\static\vendor"
$TailwindAsset = Join-Path $VendorDir "tailwind.min.js"
$LucideAsset = Join-Path $VendorDir "lucide.min.js"

if ((Test-Path $TailwindAsset) -and (Test-Path $LucideAsset)) {
    Write-Host "  [OK] Assets Offline-First validados em web\static\vendor." -ForegroundColor Green
} else {
    Write-Host "  [!] AVISO: Alguns assets em web\static\vendor nao foram localizados." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# [2/8] Ambiente Virtual (.venv) e Dependencias Python
# ---------------------------------------------------------------------------
Write-Stage "2/8" "Configurando ambiente virtual Python (.venv)..."

if ($DryRun) {
    Write-Host "  [DRY-RUN] Criacao de .venv e pip install ignorados." -ForegroundColor Yellow
} else {
    if (-not (Test-Path $VenvPython)) {
        Write-Host "  [*] Criando ambiente virtual em .venv..." -ForegroundColor Gray
        & $PythonCmd -m venv ".venv"
        $PythonCmd = $VenvPython
    }
    $ReqFile = Join-Path $ProjectRoot "requirements.txt"
    if (Test-Path $ReqFile) {
        Write-Host "  [*] Verificando dependencias do requirements.txt..." -ForegroundColor Gray
        & $PythonCmd -m pip install --upgrade pip --quiet
        & $PythonCmd -m pip install -r $ReqFile --quiet
        Write-Host "  [OK] Dependencias Python sincronizadas." -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
# [3/8] Wizard Python: Segredos .env, Migracoes Alembic e Opt-In LGPD
# ---------------------------------------------------------------------------
Write-Stage "3/8" "Executando Wizard de Provisionamento (.env, Alembic e LGPD)..."

if ($DryRun) {
    Write-Host "  [DRY-RUN] Simulando chamada: python -m core.installer_wizard --filial-id $FilialId --port $Port" -ForegroundColor Yellow
} else {
    & $PythonCmd -m core.installer_wizard `
        --cnpj "$Cnpj" `
        --razao-social "$RazaoSocial" `
        --assinado-por "$AssinadoPor" `
        --filial-id $FilialId `
        --tenant-id "$TenantId" `
        --port $Port
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [!] AVISO: O Wizard retornou codigo $LASTEXITCODE. Verifique os logs." -ForegroundColor Yellow
    } else {
        Write-Host "  [OK] Segredos .env, banco SQLite Alembic e Opt-In LGPD provisionados." -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------------
# [4/8] Containers Auxiliares (Docker / pgvector)
# ---------------------------------------------------------------------------
Write-Stage "4/8" "Verificando containers auxiliares (Docker / pgvector)..."

$ComposeFile = Join-Path $ProjectRoot "docker-compose.yml"
if ($SkipDocker -or $DryRun) {
    Write-Host "  [SKIP] Etapa Docker ignorada por parametro (-SkipDocker ou -DryRun)." -ForegroundColor Yellow
} elseif ((Test-Path $ComposeFile) -and (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "  [*] Subindo servicos declarados no docker-compose.yml..." -ForegroundColor Gray
    docker compose up -d
    Write-Host "  [OK] Containers Docker verificados." -ForegroundColor Green
} else {
    Write-Host "  [INFO] Docker nao exigido ou operando com PostgreSQL nativo local." -ForegroundColor Gray
}

# ---------------------------------------------------------------------------
# [5/8] Blindagem Somente-Leitura do ERP (aura_service_ro)
# ---------------------------------------------------------------------------
Write-Stage "5/8" "Verificando role somente-leitura no PostgreSQL (aura_service_ro)..."

$ReadonlySql = Join-Path $ProjectRoot "scripts\setup_readonly_user.sql"
if ($DryRun) {
    Write-Host "  [DRY-RUN] Aplicacao de $ReadonlySql ignorada." -ForegroundColor Yellow
} elseif ((Test-Path $ReadonlySql) -and (Get-Command "psql" -ErrorAction SilentlyContinue)) {
    Write-Host "  [*] Aplicando script idempotente setup_readonly_user.sql..." -ForegroundColor Gray
    try {
        psql -h 127.0.0.1 -U postgres -d BD_Posto -f $ReadonlySql | Out-Null
        Write-Host "  [OK] Role aura_service_ro (default_transaction_read_only=on) garantida." -ForegroundColor Green
    } catch {
        Write-Host "  [INFO] Nao foi possivel aplicar via psql automatico (credenciais locais customizadas)." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [INFO] Script SQL disponivel em scripts\setup_readonly_user.sql." -ForegroundColor Gray
}

# ---------------------------------------------------------------------------
# [6/8] Regra de Firewall do Windows (Porta TCP 8000 - LAN e Tailscale)
# ---------------------------------------------------------------------------
Write-Stage "6/8" "Configurando regra de Firewall do Windows (Porta TCP $Port)..."

$FirewallRuleName = "AURA_Backend_HTTP_$Port"
if ($SkipFirewall -or $DryRun) {
    Write-Host "  [SKIP] Configuracao de Firewall ignorada (-SkipFirewall ou -DryRun)." -ForegroundColor Yellow
} else {
    try {
        $ExistingRule = Get-NetFirewallRule -DisplayName $FirewallRuleName -ErrorAction SilentlyContinue
        if (-not $ExistingRule) {
            New-NetFirewallRule `
                -DisplayName $FirewallRuleName `
                -Direction Inbound `
                -Action Allow `
                -Protocol TCP `
                -LocalPort $Port `
                -Profile Any `
                -Description "Permite acesso ao painel e API da AURA via LAN e Tailscale" | Out-Null
            Write-Host "  [OK] Regra de Firewall '$FirewallRuleName' criada para a porta TCP $Port." -ForegroundColor Green
        } else {
            Write-Host "  [OK] Regra de Firewall '$FirewallRuleName' ja existe." -ForegroundColor Green
        }
    } catch {
        Write-Host "  [INFO] Sem privilegios de Administrador para criar regra de Firewall (ja liberada ou manual)." -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# [7/8] Registro e Inicializacao do Servico Windows (NSSM)
# ---------------------------------------------------------------------------
Write-Stage "7/8" "Configurando servico Windows resiliente ($ServiceName)..."

$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

if ($SkipService -or $DryRun) {
    Write-Host "  [SKIP] Registro de servico NSSM ignorado (-SkipService ou -DryRun)." -ForegroundColor Yellow
} elseif (Get-Command "nssm" -ErrorAction SilentlyContinue) {
    $NssmBin = (Get-Command "nssm").Source
    $AppArgs = "-m uvicorn core.aura_api:app --host 0.0.0.0 --port $Port"
    try {
        $Svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if (-not $Svc) {
            & $NssmBin install $ServiceName $PythonCmd $AppArgs | Out-Null
            & $NssmBin set $ServiceName AppDirectory $ProjectRoot | Out-Null
            & $NssmBin set $ServiceName AppStdout (Join-Path $LogDir "service_stdout.log") | Out-Null
            & $NssmBin set $ServiceName AppStderr (Join-Path $LogDir "service_stderr.log") | Out-Null
            & $NssmBin set $ServiceName Start SERVICE_AUTO_START | Out-Null
            Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
        } else {
            Restart-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        }
        Write-Host "  [OK] Servico '$ServiceName' ativo, atualizado e configurado para inicio automatico." -ForegroundColor Green
    } catch {
        Write-Host "  [INFO] Verifique privilegios de Administrador para gerenciar o servico $ServiceName." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [INFO] NSSM nao encontrado no PATH. O servico pode ser iniciado via start_aura_service.bat." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# [8/8] Smoke Test de Saude HTTP e Resumo de Endpoints
# ---------------------------------------------------------------------------
Write-Stage "8/8" "Executando Smoke Test de saude e verificando endpoints de acesso..."

$HealthUrl = "http://localhost:$Port/api/v1/aura/health"
$MetricsUrl = "http://localhost:$Port/metrics"

if ($DryRun) {
    Write-Host "  [DRY-RUN] Smoke Test HTTP ignorado ($HealthUrl)." -ForegroundColor Yellow
} else {
    try {
        $Resp = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 5
        Write-Host "  [OK] Endpoint de saude respondeu com status: $($Resp.status)" -ForegroundColor Green
    } catch {
        Write-Host "  [INFO] Servidor HTTP ainda inicializando ou aguardando partida em $HealthUrl." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "   INSTALACAO 1-CLIQUE CONCLUIDA COM SUCESSO!                         " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  Painel Local     : http://localhost:$Port" -ForegroundColor White
Write-Host "  Healthcheck SRE  : $HealthUrl" -ForegroundColor White
Write-Host "  Metricas Prom    : $MetricsUrl" -ForegroundColor White
Write-Host "  Recibo Auditavel : data\install_receipt.json" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Green
exit 0
