# Sobe o servidor do celular (mobile/run.py) com o Python do venv do Hub.
#   ./mobile/start_mobile.ps1
# Deixe esta janela aberta: fecha-la encerra o servidor do celular.
# O Hub (server.py, porta 8765) precisa estar no ar — suba-o antes.
$raiz = Split-Path -Parent $PSScriptRoot
$py = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "venv nao encontrado em $py" -Foreground Red; exit 1 }
Set-Location $raiz
& $py -m mobile.run
