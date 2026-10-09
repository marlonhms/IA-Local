# Iniciar IA do Posto com pgvector e Gemini
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Iniciando IA do Posto (pgvector + Gemini)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Banco Vetorial e ERP 100% Nativo no Windows (PostgreSQL 16 porta 5433)
Write-Host "[*] Modo 100% Nativo Windows: PostgreSQL 16 com pgvector (sem Docker/WSL)." -ForegroundColor Cyan


# 2. Garantir que o servico PostgreSQL local esta rodando
Write-Host "[*] Verificando servico postgresql-x64-16 (ERP porta 5433)..." -ForegroundColor Yellow
$pgService = Get-Service -Name "postgresql-x64-16" -ErrorAction SilentlyContinue
if ($pgService -and $pgService.Status -ne "Running") {
    Start-Service -Name "postgresql-x64-16" -ErrorAction SilentlyContinue
    Write-Host "[OK] Servico postgresql-x64-16 iniciado." -ForegroundColor Green
} else {
    Write-Host "[OK] Servico postgresql-x64-16 em execucao." -ForegroundColor Green
}

# 3. Rodar o Agente
Write-Host "`n[*] Iniciando o agente inteligente...`n" -ForegroundColor Cyan
Set-Location -Path $PSScriptRoot
python "$PSScriptRoot\main.py"
