# Encerra somente processos identificados desta instalação, com seus filhos.
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$hubRootPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$hubMarkerFile = Join-Path $PSScriptRoot 'state\instance.json'
$hubCandidates = @()
$hubLivePid = 0
try {
    $hubIdentity = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/hub_identity' -TimeoutSec 3
    if ($hubIdentity.protocol -ne 'hub-runtime-v1' -or [IO.Path]::GetFullPath($hubIdentity.project_root).TrimEnd('\') -ne $hubRootPath) {
        throw 'A porta está ocupada por outra instalação. Nenhum processo será encerrado.'
    }
    $hubCandidates += [int]$hubIdentity.pid
    $hubLivePid = [int]$hubIdentity.pid
} catch {
    $hubListeners = @(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)
    if ($hubListeners.Count -gt 0) { Write-Error 'Porta 8765 ocupada sem identidade válida; parada recusada.'; exit 1 }
}
if (Test-Path -LiteralPath $hubMarkerFile) {
    $hubMarker = Get-Content -LiteralPath $hubMarkerFile -Raw | ConvertFrom-Json
    if ($hubMarker.protocol -eq 'hub-runtime-v1' -and [IO.Path]::GetFullPath($hubMarker.project_root).TrimEnd('\') -eq $hubRootPath) {
        $hubCandidates += [int]$hubMarker.pid
        $hubCandidates += [int]$hubMarker.speech_pid
    }
}
foreach ($hubProcessId in ($hubCandidates | Where-Object { $_ -gt 0 } | Select-Object -Unique)) {
    $hubProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $hubProcessId" -ErrorAction SilentlyContinue
    if (-not $hubProcess) { continue }
    $hubCommand = $hubProcess.CommandLine
    $hubServerFile = Join-Path $hubRootPath 'server.py'
    $hubSpeechFile = Join-Path $hubRootPath 'hub_runtime\voice\speak_server.py'
    if (-not $hubCommand -or (($hubCommand.IndexOf($hubServerFile, [StringComparison]::OrdinalIgnoreCase) -lt 0) -and
        ($hubCommand.IndexOf($hubSpeechFile, [StringComparison]::OrdinalIgnoreCase) -lt 0))) {
        # Um PID que veio só do marcador e hoje é de outro programa indica marcador velho: ignora sem encerrar.
        if ($hubProcessId -ne $hubLivePid) {
            Write-Warning "PID $hubProcessId do marcador não pertence mais a esta instalação; marcador velho ignorado."
            continue
        }
        Write-Error "PID $hubProcessId não pertence aos arquivos desta instalação. Parada recusada."
        exit 1
    }
    Write-Output "[stop] processo desta instalação: $hubProcessId"
    if (-not $DryRun) {
        & taskkill /PID $hubProcessId /T /F *> $null
        if ($LASTEXITCODE -ne 0 -and (Get-Process -Id $hubProcessId -ErrorAction SilentlyContinue)) {
            Write-Error "Não foi possível encerrar PID $hubProcessId"; exit 1
        }
    }
}
if (-not $DryRun -and (Test-Path -LiteralPath $hubMarkerFile)) { Remove-Item -LiteralPath $hubMarkerFile }
exit 0
