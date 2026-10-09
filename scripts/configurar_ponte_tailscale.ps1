# ==============================================================================
# Script de Configuracao e Verificacao da Ponte Tailscale (Notebook <-> PC Casa)
# Projeto: Ai.la (IA do Posto & Banco Local)
# ==============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " [AI.LA] CONFIGURACAO DA PONTE TAILSCALE - BANCO DE DADOS DISTRIBUIDO" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Verificar Elevacao de Administrador
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "`n[!] Este script precisa de privilegios de Administrador para configurar o Firewall do Windows." -ForegroundColor Yellow
    Write-Host "[*] Solicitando elevacao UAC..." -ForegroundColor Yellow
    
    $scriptPath = $PSCommandPath
    if (-not $scriptPath) {
        $scriptPath = $MyInvocation.MyCommand.Path
    }
    Start-Process powershell.exe -Verb RunAs -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$scriptPath`"")
    Exit
}

Write-Host "`n[OK] Executando com permissoes de Administrador.`n" -ForegroundColor Green

# 2. Detectar IP e Adaptador de Rede Tailscale
Write-Host "[1/5] Detectando interface e adaptador de rede Tailscale..." -ForegroundColor Yellow
$tailscaleIP = $null
$tsAdapter = $null

try {
    $tsAdapter = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { ($_.InterfaceDescription -like "*Tailscale*") -or ($_.Name -like "*Tailscale*") } | Select-Object -First 1
} catch {}

try {
    $tsAddress = Get-NetIPAddress -InterfaceAlias *tailscale* -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($tsAddress) {
        $tailscaleIP = $tsAddress.IPAddress
    }
} catch {}

if (-not $tailscaleIP) {
    try {
        $cliIp = (tailscale ip -4 2>$null)
        if ($cliIp) {
            $tailscaleIP = $cliIp.Trim()
        }
    } catch {}
}

if ($tailscaleIP) {
    Write-Host "   [OK] Tailscale detectado! IP desta maquina (Notebook): $tailscaleIP" -ForegroundColor Green
} else {
    Write-Host "   [!] AVISO: Tailscale nao detectado ou desconectado. Certifique-se de que o Tailscale esta aberto." -ForegroundColor Red
}

$interfaceAlias = if ($tsAdapter) { $tsAdapter.Name } else { $null }
if ($interfaceAlias) {
    Write-Host "   [OK] Adaptador Tailscale identificado: '$interfaceAlias' (Status: $($tsAdapter.Status))" -ForegroundColor Green
} else {
    Write-Host "   [WARN] Adaptador virtual Tailscale nao identificado pelo nome padrao. Vinculacao sera feita via sub-rede 100.64.0.0/10." -ForegroundColor DarkYellow
}

# 3. Configurar Regras de Firewall do Windows (Restritas a Rede Tailscale e Adaptador)
Write-Host "`n[2/5] Verificando e criando regras no Firewall do Windows..." -ForegroundColor Yellow

$rules = @(
    @{
        Name = "AiLa-PostgreSQL-ERP-5433"
        DisplayName = "Ai.la - PostgreSQL ERP (Tailscale Porta 5433)"
        Port = 5433
        Desc = "Permite conexao de entrada ao PostgreSQL 16 ERP restrita a rede Tailscale"
    },
    @{
        Name = "AiLa-Docker-pgvector-5434"
        DisplayName = "Ai.la - Docker pgvector (Tailscale Porta 5434)"
        Port = 5434
        Desc = "Permite conexao de entrada ao Docker pgvector restrita a rede Tailscale"
    },
    @{
        Name = "AiLa-PostgreSQL-Dev-5435"
        DisplayName = "Ai.la - PostgreSQL Dev Fallback (Tailscale Porta 5435)"
        Port = 5435
        Desc = "Permite conexao de entrada a instancia dev fallback restrita a rede Tailscale"
    }
)

foreach ($r in $rules) {
    $existing = Get-NetFirewallRule -Name $r.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "   [OK] Atualizando regra existente: $($r.DisplayName)" -ForegroundColor Green
        if ($interfaceAlias) {
            Set-NetFirewallRule -Name $r.Name -Enabled True -Action Allow -RemoteAddress "100.64.0.0/10" -InterfaceAlias $interfaceAlias -ErrorAction SilentlyContinue
        } else {
            Set-NetFirewallRule -Name $r.Name -Enabled True -Action Allow -RemoteAddress "100.64.0.0/10" -ErrorAction SilentlyContinue
        }
    } else {
        $firewallParams = @{
            Name = $r.Name
            DisplayName = $r.DisplayName
            Description = $r.Desc
            Direction = "Inbound"
            Protocol = "TCP"
            LocalPort = $r.Port
            RemoteAddress = "100.64.0.0/10"
            Action = "Allow"
            Profile = "Any"
            ErrorAction = "SilentlyContinue"
        }
        if ($interfaceAlias) {
            $firewallParams["InterfaceAlias"] = $interfaceAlias
        }
        New-NetFirewallRule @firewallParams | Out-Null
        Write-Host "   [CRIADA] Nova regra liberada: $($r.DisplayName) (Porta $($r.Port), Origem 100.64.0.0/10)" -ForegroundColor Green
    }
}

# 4. Verificar e Iniciar Servico PostgreSQL 16 (Porta 5433)
Write-Host "`n[3/5] Verificando Servico do PostgreSQL ERP (postgresql-x64-16)..." -ForegroundColor Yellow
$pgService = Get-Service -Name "postgresql-x64-16" -ErrorAction SilentlyContinue
if (-not $pgService) {
    $pgService = Get-Service -Name "*postgres*" -ErrorAction SilentlyContinue | Select-Object -First 1
}

if ($pgService) {
    if ($pgService.Status -ne "Running") {
        Write-Host "   [*] Servico parado ($($pgService.Name)). Iniciando servico..." -ForegroundColor Yellow
        Start-Service -Name $pgService.Name -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        $pgService.Refresh()
    }
    Write-Host "   [OK] Servico $($pgService.Name): $($pgService.Status)" -ForegroundColor Green
} else {
    Write-Host "   [AVISO] Servico PostgreSQL nao encontrado na lista de servicos Windows." -ForegroundColor DarkYellow
}

# 5. Banco Vetorial pgvector Nativo (Porta 5433)
Write-Host "`n[4/5] Verificando PostgreSQL 16 Nativo (ERP e pgvector na Porta 5433)..." -ForegroundColor Yellow
$pgService = Get-Service -Name "postgresql-x64-16" -ErrorAction SilentlyContinue
if ($pgService -and $pgService.Status -eq "Running") {
    Write-Host "   [OK] Servico postgresql-x64-16 ativo na porta 5433 (ERP e pgvector nativos)." -ForegroundColor Green
} else {
    Write-Host "   [!] Servico postgresql-x64-16 nao esta em execucao." -ForegroundColor Yellow
}

# 6. Resumo de Uso no Computador de Casa
Write-Host "`n[5/5] Resumo de Conexao para o PC de Casa:" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------------------" -ForegroundColor DarkGray
if ($tailscaleIP) {
    Write-Host " No arquivo .env do seu Computador de Casa, configure:" -ForegroundColor White
    Write-Host "   ERP_DB_HOST=$tailscaleIP  (ou use o MagicDNS: marlonh-supwp)" -ForegroundColor Green
    Write-Host "   ERP_DB_PORT=5433" -ForegroundColor Green
    Write-Host "   VECTOR_DB_HOST=$tailscaleIP  (ou use o MagicDNS: marlonh-supwp)" -ForegroundColor Green
    Write-Host "   VECTOR_DB_PORT=5433" -ForegroundColor Green
} else {
    Write-Host " Configure ERP_DB_HOST e VECTOR_DB_HOST com o IP Tailscale deste notebook (ou marlonh-supwp)." -ForegroundColor Yellow
}
Write-Host "----------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "`n[OK] Configuracao da Ponte concluida com sucesso!" -ForegroundColor Cyan
