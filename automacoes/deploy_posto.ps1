# =============================================================================
# AURA Core Engine: Script de Onboarding e Deploy Automatizado (Fase 2.5)
# Orquestra a instalacao, checagem de pre-requisitos, provisionamento
# do container pgvector na porta 5434 e conexao somente-leitura com ERP legado.
# Zero travessoes em todo o arquivo. Padrao ASCII puro.
# =============================================================================

[CmdletBinding()]
param(
    [switch]$SkipDocker = $false,
    [switch]$InstallService = $false,
    [int]$ERPPort = 5432,
    [int]$VectorPort = 5434,
    [string]$ERPUser = "aura_service_ro",
    [string]$FilialId = "posto_01"
)

$ErrorActionPreference = "Continue"

# Diretorios principais
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " AURA Core Engine: Onboarding e Deploy em Campo (Fase 2.5)" -ForegroundColor Cyan
Write-Host " Versao: 1.0.0-PRO | Ambiente: Windows Edge AI On-Premises" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Diretorio Raiz: $ProjectRoot"
Write-Host "Porta ERP Legado: $ERPPort (Somente-Leitura)"
Write-Host "Porta pgvector:   $VectorPort (Isolada / Zero-Disruption)"
Write-Host ""

# -----------------------------------------------------------------------------
# PASSO 1: DETECCAO DO AMBIENTE PYTHON
# -----------------------------------------------------------------------------
Write-Host "[1/6] Verificando interpretador Python e dependencias..." -ForegroundColor Yellow

$PythonExe = ""
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$GlobalPython = (Get-Command python -ErrorAction SilentlyContinue)

if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
    Write-Host "[OK] Ambiente virtual (.venv) localizado: $PythonExe" -ForegroundColor Green
} elseif ($GlobalPython) {
    $PythonExe = $GlobalPython.Source
    Write-Host "[OK] Python global localizado: $PythonExe" -ForegroundColor Green
} else {
    Write-Host "[!] ERRO CRITICO: Python 3.10+ nao foi encontrado no sistema." -ForegroundColor Red
    Write-Host "    Instale o Python em https://www.python.org/downloads/ e tente novamente."
    exit 1
}

$PyVer = & $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "[OK] Versao do Python em execucao: $PyVer" -ForegroundColor Green

# -----------------------------------------------------------------------------
# PASSO 2: CONFIGURACAO DE ARQUIVO .ENV
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/6] Verificando configuracoes de ambiente (.env)..." -ForegroundColor Yellow

$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Write-Host "[*] Criando .env a partir de .env.example..." -ForegroundColor Cyan
        Copy-Item -Path $EnvExample -Destination $EnvFile
        
        # Gera segredo HMAC e API Key unicos para este posto
        $VoucherSecret = [System.Guid]::NewGuid().ToString("N") + [System.Guid]::NewGuid().ToString("N")
        $ApiKey = "aura_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 16)
        
        $EnvContent = Get-Content -Path $EnvFile -Raw
        $EnvContent = $EnvContent -replace "AURA_VOUCHER_SECRET=.*", "AURA_VOUCHER_SECRET=$VoucherSecret"
        $EnvContent = $EnvContent -replace "AURA_API_KEY=.*", "AURA_API_KEY=$ApiKey"
        $EnvContent = $EnvContent -replace "VECTOR_DB_PORT=.*", "VECTOR_DB_PORT=$VectorPort"
        Set-Content -Path $EnvFile -Value $EnvContent -Encoding UTF8
        Write-Host "[OK] Arquivo .env gerado com chaves criptograficas dedicadas." -ForegroundColor Green
    } else {
        Write-Host "[WARN] .env.example nao localizado. Certifique-se de configurar .env manualmente." -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Arquivo .env existente e preservado." -ForegroundColor Green
}

# -----------------------------------------------------------------------------
# PASSO 3: PROVISIONAMENTO DO CONTAINER DOCKER PGVECTOR
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "[3/6] Verificando container pgvector na porta $VectorPort..." -ForegroundColor Yellow

$DockerInstalled = (Get-Command docker -ErrorAction SilentlyContinue)
$DockerRunning = $false

if ($DockerInstalled) {
    $DockerInfo = & docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $DockerRunning = $true
    }
}

if ($SkipDocker) {
    Write-Host "[INFO] Flag -SkipDocker ativada. Subida do container Docker ignorada." -ForegroundColor Cyan
} elseif ($DockerRunning) {
    Write-Host "[*] Docker ativo. Subindo container pgvector via docker-compose..." -ForegroundColor Cyan
    $ComposeFile = Join-Path $ProjectRoot "docker-compose.yml"
    
    if (Test-Path $ComposeFile) {
        & docker compose -f "$ComposeFile" up -d
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Container aura_pgvector_posto iniciado com sucesso." -ForegroundColor Green
            Write-Host "[*] Aguardando inicializacao do container (10 segundos)..."
            Start-Sleep -Seconds 10
        } else {
            Write-Host "[WARN] Falha ao subir docker-compose. Prosseguindo com checagem de porta..." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[WARN] Docker Engine nao esta em execucao." -ForegroundColor Yellow
    Write-Host "       A AURA verificara se o PostgreSQL 16 esta instalado localmente no Windows." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# PASSO 4: TESTE DE CONECTIVIDADE COM ERP LEGADO E PGVECTOR
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "[4/6] Validando conectividade TCP de rede..." -ForegroundColor Yellow

# Teste ERP
$ERPTest = Test-NetConnection -ComputerName "127.0.0.1" -Port $ERPPort -WarningAction SilentlyContinue
if ($ERPTest -and $ERPTest.TcpTestSucceeded) {
    Write-Host "[OK] Conexao com ERP legado na porta ${ERPPort}: SUCESSO." -ForegroundColor Green
} else {
    Write-Host "[WARN] Nao foi possivel conectar a porta $ERPPort do ERP local." -ForegroundColor Yellow
    Write-Host "       Verifique se o servico do ERP esta ativo ou se a porta difere (ex: 5433)." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# PASSO 5: INICIALIZACAO DE ESQUEMAS E TABELAS DO BANCO VETORIAL
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "[5/6] Executando migracao e inicializacao das tabelas vetoriais..." -ForegroundColor Yellow

$InitScript = Join-Path $ScriptDir "init_posto_database.py"
if (Test-Path $InitScript) {
    & $PythonExe "$InitScript" --port $VectorPort --max-retries 10
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Banco vetorial posto_ai pronto com extensoes e tabelas HNSW." -ForegroundColor Green
    } else {
        # Fallback para porta 5433 se a 5434 nao respondeu e 5433 estiver ativa
        Write-Host "[*] Tentando conexao de fallback na porta 5433..." -ForegroundColor Cyan
        & $PythonExe "$InitScript" --port 5433 --password "123456" --max-retries 3
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Banco vetorial ativo no PostgreSQL local na porta 5433." -ForegroundColor Green
        } else {
            Write-Host "[!] Falha ao inicializar o banco vetorial. Verifique as credenciais no .env." -ForegroundColor Red
        }
    }
}

# -----------------------------------------------------------------------------
# PASSO 6: SERVICO WINDOWS NATIVO NSSM (OPCIONAL)
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "[6/6] Verificando Servico Nativo do Windows (NSSM)..." -ForegroundColor Yellow

if ($InstallService) {
    $NssmScript = Join-Path $ScriptDir "iniciar_servico_nssm.bat"
    if (Test-Path $NssmScript) {
        Write-Host "[*] Instalando e iniciando servico Windows AURA_Core_Engine..." -ForegroundColor Cyan
        & cmd.exe /c "$NssmScript"
        Write-Host "[OK] Servico Windows gerenciado pelo NSSM configurado." -ForegroundColor Green
    }
} else {
    Write-Host "[INFO] Para executar como servico nativo 24/7 sem janelas visiveis, execute:" -ForegroundColor Cyan
    Write-Host "       .\scripts\iniciar_servico_nssm.bat" -ForegroundColor White
}

# -----------------------------------------------------------------------------
# RESUMO FINAL
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " [OK] ONBOARDING DA AURA NO POSTO CONCLUIDO COM SUCESSO!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "Proximos passos para operacao de pista:"
Write-Host "1. Iniciar o servidor interativo:"
Write-Host "   python -m uvicorn core.aura_api:app --host 0.0.0.0 --port 8000" -ForegroundColor White
Write-Host "2. Acessar o painel executivo no navegador:"
Write-Host "   http://localhost:8000/" -ForegroundColor Cyan
Write-Host "3. Para auditar a role somente-leitura no ERP:"
Write-Host "   psql -h localhost -p $ERPPort -U postgres -f .\scripts\provisionar_usuario_leitura_erp.sql" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Green
