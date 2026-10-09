# Launcher PowerShell para o Painel Web da AURA
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "AURA // Painel Operacional"

Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host "  AURA - AUTONOMOUS UNIFIED RETAIL ASSISTANT" -ForegroundColor Green
Write-Host "  Painel Operacional da Pista & Console Cognitivo" -ForegroundColor Magenta
Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Banco Vetorial e ERP 100% Nativo no Windows (PostgreSQL 16 porta 5433)
Write-Host "  [*] Modo 100% Nativo Windows: PostgreSQL 16 com pgvector (sem Docker/WSL)." -ForegroundColor Cyan


# 2. Verifica servico PostgreSQL ERP local
try {
    $service = Get-Service -Name "postgresql-x64-16" -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq "Running") {
        Write-Host "  [OK] Servico postgresql-x64-16 ativo na porta 5433." -ForegroundColor Green
    }
} catch {
    Write-Host "  [!] Servico PostgreSQL nao pode ser verificado." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Iniciando Painel Web da AURA (o navegador abrirá automaticamente)..." -ForegroundColor Cyan
python server.py
