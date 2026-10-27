# Derruba o que estiver escutando na porta do celular (8766).
$porta = 8766
$pids = (Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue).OwningProcess
if (-not $pids) { Write-Host "nada escutando na porta $porta"; exit 0 }
foreach ($procId in ($pids | Select-Object -Unique)) {
  try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host "encerrado PID $procId" }
  catch { Write-Host "nao consegui encerrar o PID $procId" }
}
