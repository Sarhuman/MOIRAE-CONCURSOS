param([string]$Database = "var\henrique-windows.sqlite3")
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv-win\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Crie o ambiente: py -3.13 -m venv .venv-win; depois instale requirements-dev.lock.' }
$env:MOIRAE_DB = [IO.Path]::GetFullPath($Database)
$env:MOIRAE_ORIGIN = 'http://127.0.0.1:8000'
$env:MOIRAE_SECURE_COOKIE = 'false'
$env:MOIRAE_ESSAY_DEMO = 'true'
$env:MOIRAE_ESSAY_AI = 'false'
$env:MOIRAE_ESSAY_AI_REVIEWED = 'false'
$env:MOIRAE_MP_SANDBOX = 'false'
Write-Host "Python: $python"
Write-Host "Banco: $env:MOIRAE_DB"
if (!(Test-Path -LiteralPath $env:MOIRAE_DB)) {
    & $python -m backend.moirae.local_playtest --database $env:MOIRAE_DB --email henrique@example.test
    if ($LASTEXITCODE -ne 0) { throw 'Preparo falhou; servidor não iniciado.' }
}
& $python -m backend.moirae.preflight
if ($LASTEXITCODE -ne 0) { throw 'Configuração inválida.' }
Write-Host 'Abra http://127.0.0.1:8000/estudar — henrique@example.test'
& $python -m uvicorn backend.moirae.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers
