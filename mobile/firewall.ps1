<#
  Prepara a rede desta maquina para o celular. Rode UMA VEZ, como Administrador:
    botao direito no arquivo -> "Executar com o PowerShell"
    (ou: powershell -ExecutionPolicy Bypass -File mobile\firewall.ps1)

  Faz duas coisas, ambas restritas a rede de casa:
    1. marca a sua rede Wi-Fi como PRIVADA (se estiver como Publica, o Windows
       bloqueia conexoes vindas do celular, mesmo com a regra de firewall);
    2. libera a porta 8766 (TCP) no firewall, SO no perfil Private.

  Desfazer:
    Remove-NetFirewallRule -DisplayName "C.O.R.E. celular (8766)"
    Set-NetConnectionProfile -Name "<sua rede>" -NetworkCategory Public
#>

$ErrorActionPreference = "Stop"
$regra = "C.O.R.E. celular (8766)"
$porta = 8766

# --- precisa ser administrador ---
$eu = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $eu.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Host ""
  Write-Host "  Este script precisa de Administrador." -Foreground Red
  Write-Host "  Feche, clique com o botao DIREITO no arquivo e escolha"
  Write-Host "  'Executar com o PowerShell' aceitando o aviso do Windows."
  Write-Host ""
  Read-Host "  Enter para sair" | Out-Null
  exit 1
}

Write-Host ""
Write-Host "  C.O.R.E. - preparar a rede para o celular" -Foreground Cyan
Write-Host "  ----------------------------------------"

# --- 1. perfil da rede ---
$publicas = Get-NetConnectionProfile | Where-Object { $_.NetworkCategory -eq "Public" }
foreach ($p in $publicas) {
  Write-Host ""
  Write-Host "  A rede '$($p.Name)' ($($p.InterfaceAlias)) esta marcada como PUBLICA." -Foreground Yellow
  Write-Host "  Enquanto ela estiver assim, o Windows recusa a conexao do celular."
  $r = Read-Host "  Marcar como PRIVADA? (s/n)"
  if ($r -match '^[sSyY]') {
    Set-NetConnectionProfile -InterfaceIndex $p.InterfaceIndex -NetworkCategory Private
    Write-Host "  '$($p.Name)' agora e uma rede privada." -Foreground Green
  } else {
    Write-Host "  Deixado como esta - o celular provavelmente nao vai conectar." -Foreground Yellow
  }
}
if (-not $publicas) {
  Write-Host "  Perfis de rede: ja estao privados. Nada a fazer." -Foreground Green
}

# --- 2. regra de firewall ---
Write-Host ""
if (Get-NetFirewallRule -DisplayName $regra -ErrorAction SilentlyContinue) {
  Write-Host "  Firewall: a regra '$regra' ja existe." -Foreground Green
} else {
  New-NetFirewallRule -DisplayName $regra -Direction Inbound -Action Allow `
    -Protocol TCP -LocalPort $porta -Profile Private | Out-Null
  Write-Host "  Firewall: porta $porta (TCP) liberada em redes PRIVADAS." -Foreground Green
}

# --- 3. o link, se ja existir ---
$link = Join-Path $PSScriptRoot "LINK.txt"
Write-Host ""
if (Test-Path $link) {
  Write-Host "  Abra este endereco no celular (mesmo Wi-Fi):" -Foreground Cyan
  Write-Host "    $(Get-Content $link -TotalCount 1)"
} else {
  Write-Host "  Agora suba o servidor do celular: mobile\start_mobile.vbs" -Foreground Cyan
  Write-Host "  O link aparece em mobile\LINK.txt."
}
Write-Host ""
Read-Host "  Enter para fechar" | Out-Null
