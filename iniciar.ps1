# Iniciar IA do Posto com pgvector e Gemini
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Iniciando IA do Posto (pgvector + Gemini)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Garantir que o container pgvector esta rodando
Write-Host "[*] Verificando container pgvector-posto no Docker..." -ForegroundColor Yellow
try {
    $res = docker start pgvector-posto 2>&1
    Write-Host "[OK] Container pgvector ativo na porta 5434." -ForegroundColor Green
} catch {
    Write-Host "[!] Nao foi possivel iniciar o container automaticamente. Verifique se o Docker Desktop esta aberto." -ForegroundColor Red
}

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
