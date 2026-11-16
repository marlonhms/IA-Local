# ==============================================================================
# build_aura_standalone.ps1
# Script de Compilacao Automatizada da AURA via PyInstaller (Fase 8).
# Gera distribuicao standalone em dist/AuraBackend/ pronta para novos postos.
# Regra inegociavel: ZERO travessoes em todo o arquivo.
# ==============================================================================

[CmdletBinding()]
param (
    [switch]$Clean = $true,
    [switch]$SkipTests = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   AURA BACKEND: COMPILACAO STANDALONE PYINSTALLER (FASE 8)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Diretorio do Projeto: $ProjectRoot" -ForegroundColor Gray

# 1. Localiza o executavel do Python
$PythonExe = "python"
if (Test-Path "$ProjectRoot\.venv\Scripts\python.exe") {
    $PythonExe = "$ProjectRoot\.venv\Scripts\python.exe"
}
Write-Host "[*] Utilizando Python Runtime: $PythonExe" -ForegroundColor Gray

# 2. Verifica se PyInstaller esta instalado
try {
    $PyInstallerVer = & $PythonExe -c "import PyInstaller; print(PyInstaller.__version__)"
    Write-Host "[OK] PyInstaller detectado: versao $PyInstallerVer" -ForegroundColor Green
}
catch {
    Write-Host "[!] ERRO: PyInstaller nao encontrado no ambiente Python. Execute: pip install pyinstaller" -ForegroundColor Red
    exit 1
}

# 3. Limpeza de builds anteriores se solicitado
if ($Clean) {
    Write-Host "[*] Limpando diretorios anteriores de build e dist..." -ForegroundColor Yellow
    if (Test-Path "$ProjectRoot\build\AuraBackend") {
        Remove-Item -Recurse -Force "$ProjectRoot\build\AuraBackend" -ErrorAction SilentlyContinue
    }
    if (Test-Path "$ProjectRoot\dist\AuraBackend") {
        Remove-Item -Recurse -Force "$ProjectRoot\dist\AuraBackend" -ErrorAction SilentlyContinue
    }
    Write-Host "[OK] Diretorios temporarios limpos." -ForegroundColor Green
}

# 4. Executa os testes unitarios antes de compilar (a menos que -SkipTests seja passado)
if (-not $SkipTests) {
    Write-Host "[*] Executando suite de testes de integridade antes do build..." -ForegroundColor Yellow
    & $PythonExe -m pytest tests/unit/test_shared_pgvector_convergence.py tests/unit/test_command_journal_idempotency.py tests/unit/test_windows_scm_service.py -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] ERRO: Testes unitarios falharam. Abortando compilacao para proteger release." -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Testes unitarios aprovados com sucesso." -ForegroundColor Green
}

# 5. Executa a compilacao com PyInstaller
Write-Host "[*] Iniciando compilacao standalone com AuraBackend.spec..." -ForegroundColor Cyan
$SpecPath = Join-Path $ProjectRoot "AuraBackend.spec"
if (-not (Test-Path $SpecPath)) {
    Write-Host "[!] ERRO: Arquivo AuraBackend.spec nao encontrado em $SpecPath." -ForegroundColor Red
    exit 1
}

& $PythonExe -m PyInstaller "$SpecPath" --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] ERRO: Falha durante a execucao do PyInstaller." -ForegroundColor Red
    exit 1
}

# 6. Validacao do artefato gerado
$TargetExe = Join-Path $ProjectRoot "dist\AuraBackend\AuraBackend.exe"
if (Test-Path $TargetExe) {
    $ExeItem = Get-Item $TargetExe
    $DistDir = Join-Path $ProjectRoot "dist\AuraBackend"
    $TotalBytes = (Get-ChildItem -Path $DistDir -Recurse | Measure-Object -Property Length -Sum).Sum
    $TotalMB = [math]::Round($TotalBytes / 1MB, 2)

    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "   COMPILACAO CONCLUIDA COM SUCESSO!" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "Executavel : $TargetExe" -ForegroundColor White
    Write-Host "Tamanho Dir: $TotalMB MB" -ForegroundColor White
    Write-Host "Para implantar em postos clientes, utilize: scripts/installer/Instalar-Aura.bat" -ForegroundColor Yellow
    Write-Host "======================================================================" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "[!] ERRO: Executavel AuraBackend.exe nao encontrado apos o build em $TargetExe." -ForegroundColor Red
    exit 1
}
