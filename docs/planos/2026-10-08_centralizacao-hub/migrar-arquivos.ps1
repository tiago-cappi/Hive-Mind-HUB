# Corte de arquivos enumerados da migração aprovada. Não apaga diretórios em massa.
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$hubProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..')).TrimEnd('\')
$hubVaultRoot = 'C:\Users\m.rafael\Documents\Obsidian Vault'
$hubOldRoot = 'C:\Users\m.rafael\.claude\hooks\voice-hub'
$hubBackupRoot = Join-Path $hubProjectRoot '.migration-backups\2026-10-08_centralizacao-hub'
$hubArchiveRoot = Join-Path $hubBackupRoot 'old-checkout'
$hubManifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifesto-migracao.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$hubPersonalEdits = Get-Content -LiteralPath (Join-Path $hubBackupRoot 'personal-link-edits.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function Assert-HubPath($hubPath, $hubBoundary) {
    $hubAbsolute = [IO.Path]::GetFullPath($hubPath).TrimEnd('\')
    $hubAllowed = [IO.Path]::GetFullPath($hubBoundary).TrimEnd('\')
    if ($hubAbsolute -ne $hubAllowed -and -not $hubAbsolute.StartsWith($hubAllowed+'\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Caminho fora do escopo aprovado' }
    $hubCheck = $hubAbsolute
    while (Test-Path -LiteralPath $hubCheck) {
        if ((Get-Item -LiteralPath $hubCheck -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Junction/symlink não autorizado no corte' }
        if ($hubCheck -eq $hubAllowed) { break }
        $hubNext = [IO.Path]::GetDirectoryName($hubCheck)
        if (-not $hubNext -or $hubNext -eq $hubCheck) { break }
        $hubCheck = $hubNext
    }
}
function Hub-Hash($hubPath) { return (Get-FileHash -LiteralPath $hubPath -Algorithm SHA256).Hash.ToLowerInvariant() }
Assert-HubPath $hubBackupRoot $hubProjectRoot
Assert-HubPath $hubArchiveRoot $hubProjectRoot
Assert-HubPath $hubOldRoot 'C:\Users\m.rafael\.claude\hooks'
Assert-HubPath $hubVaultRoot $hubVaultRoot
if (@(Get-NetTCPConnection -LocalPort 8765,8766 -State Listen -ErrorAction SilentlyContinue).Count -gt 0) { throw 'Hub ou gateway em execução: corte de arquivos recusado' }
$hubRemovals = @(
    'CLAUDE.md',
    '.claude\skills\forestos-ops\SKILL.md',
    'forestos\ForestOS - Documentação Completa.md',
    'forestos\Modelo de Dados ForestOS.md'
)
foreach ($hubRelative in $hubRemovals) {
    $hubSourceFile = Join-Path $hubVaultRoot $hubRelative
    $hubBackupFile = Join-Path (Join-Path $hubBackupRoot 'vault') $hubRelative
    Assert-HubPath $hubSourceFile $hubVaultRoot
    Assert-HubPath $hubBackupFile $hubProjectRoot
    if (-not (Test-Path -LiteralPath $hubBackupFile)) { throw 'Backup obrigatório ausente' }
    if ((Test-Path -LiteralPath $hubSourceFile) -and (Hub-Hash $hubSourceFile) -ne (Hub-Hash $hubBackupFile)) { throw 'Origem técnica mudou depois do backup; corte interrompido' }
}
$hubPreferenceSource = Join-Path $hubBackupRoot 'prepared\Organizacao do acervo pessoal.md'
$hubPreferenceDestination = Join-Path $hubVaultRoot '_agentes\Organizacao do acervo pessoal.md'
Assert-HubPath $hubPreferenceDestination $hubVaultRoot
if ((Test-Path -LiteralPath $hubPreferenceDestination) -and (Hub-Hash $hubPreferenceDestination) -ne (Hub-Hash $hubPreferenceSource)) { throw 'Nota pessoal de destino já existe com conteúdo diferente' }
foreach ($hubEdit in $hubPersonalEdits) {
    Assert-HubPath $hubEdit.origin $hubVaultRoot
    Assert-HubPath $hubEdit.after $hubProjectRoot
    $hubActualHash = Hub-Hash $hubEdit.origin
    if ($hubActualHash -ne $hubEdit.shaBefore -and $hubActualHash -ne $hubEdit.shaAfter) { throw 'Nota mudou depois da preparação; nenhuma sobrescrita permitida' }
    if ((Hub-Hash $hubEdit.after) -ne $hubEdit.shaAfter) { throw 'Alteração de link não confere com manifesto privado' }
}
$hubHistorySource = Join-Path $hubProjectRoot 'mobile\history.json'
$hubHistoryDestination = Join-Path $hubVaultRoot '_agentes\historico-mobile.json'
Assert-HubPath $hubHistoryDestination $hubVaultRoot
if (Test-Path -LiteralPath $hubHistorySource) {
    if ((Hub-Hash $hubHistorySource) -ne $hubManifest.mobileHistory.source.sha256) { throw 'Histórico mobile mudou depois do backup' }
    if ((Test-Path -LiteralPath $hubHistoryDestination) -and (Hub-Hash $hubHistorySource) -ne (Hub-Hash $hubHistoryDestination)) { throw 'Históricos diferentes: reconciliar antes de transferir' }
}
if (Test-Path -LiteralPath $hubOldRoot) {
    if (Test-Path -LiteralPath $hubArchiveRoot) { throw 'Arquivo da cópia antiga já existe; não sobrescrever' }
    if ((Hub-Hash (Join-Path $hubOldRoot 'index.html')) -ne $hubManifest.oldCopyGit.indexSha256) { throw 'Cópia antiga mudou depois do inventário' }
}
Write-Output ('[cut] Preflight validado: '+$hubRemovals.Count+' origens técnicas, '+$hubPersonalEdits.Count+' links pessoais, histórico e checkout antigo.')
if ($DryRun) { exit 0 }
# Preservar dados e links antes de retirar instruções/documentos técnicos.
[IO.File]::Copy($hubPreferenceSource, $hubPreferenceDestination, $true)
foreach ($hubEdit in $hubPersonalEdits) { [IO.File]::WriteAllBytes($hubEdit.origin, [IO.File]::ReadAllBytes($hubEdit.after)) }
if (Test-Path -LiteralPath $hubHistorySource) {
    [IO.File]::Copy($hubHistorySource, $hubHistoryDestination, $false)
    if ((Hub-Hash $hubHistoryDestination) -ne (Hub-Hash $hubHistorySource)) { throw 'Histórico transferido não íntegro' }
    Remove-Item -LiteralPath $hubHistorySource
}
foreach ($hubRelative in $hubRemovals) {
    $hubSourceFile = Join-Path $hubVaultRoot $hubRelative
    if (Test-Path -LiteralPath $hubSourceFile) { Remove-Item -LiteralPath $hubSourceFile }
}
$hubEmptySkillFolder = Join-Path $hubVaultRoot '.claude\skills\forestos-ops'
if ((Test-Path -LiteralPath $hubEmptySkillFolder) -and @(Get-ChildItem -LiteralPath $hubEmptySkillFolder -Force).Count -eq 0) {
    Remove-Item -LiteralPath $hubEmptySkillFolder
}
# Move nativo, mesma unidade: preserva Git, alterações, arquivos exclusivos e venv antiga.
if (Test-Path -LiteralPath $hubOldRoot) { Move-Item -LiteralPath $hubOldRoot -Destination $hubArchiveRoot }
Write-Output '[cut] Arquivos técnicos centralizados; originais e alterações preservados em backup privado.'
