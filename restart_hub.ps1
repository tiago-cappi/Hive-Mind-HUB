# Reinicia apenas a instalação identificada desta pasta; não mata por nome/porta.
param([int]$DelaySeconds = 0, [switch]$DryRun)
$ErrorActionPreference = 'Stop'
if ($DelaySeconds -gt 0) { Start-Sleep -Seconds $DelaySeconds }
$hubStopScript = Join-Path $PSScriptRoot 'hub_runtime\stop_instance.ps1'
$hubStopArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $hubStopScript)
if ($DryRun) { $hubStopArgs += '-DryRun' }
& powershell @hubStopArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($DryRun) { exit 0 }
for ($hubAttempt = 0; $hubAttempt -lt 40; $hubAttempt++) {
    if (-not (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Milliseconds 250
}
if (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue) {
    Write-Error 'Porta 8765 ainda ocupada; reinício abortado.'; exit 1
}
$hubVbs = Join-Path $PSScriptRoot 'launch_hub.vbs'
Start-Process -FilePath 'wscript.exe' -ArgumentList ('"' + $hubVbs + '"') -WindowStyle Hidden
for ($hubAttempt = 0; $hubAttempt -lt 120; $hubAttempt++) {
    Start-Sleep -Seconds 1
    try {
        $hubIdentity = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/hub_identity' -TimeoutSec 3
        if ($hubIdentity.protocol -eq 'hub-runtime-v1' -and
            [IO.Path]::GetFullPath($hubIdentity.project_root).TrimEnd('\') -eq $PSScriptRoot.TrimEnd('\')) {
            Write-Output '[restart] Instância desta pasta confirmada.'; exit 0
        }
    } catch { }
}
Write-Error 'A instância desta pasta não respondeu em 120 segundos.'
exit 1
