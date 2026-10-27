# Voice Hub: janela pequena e discreta.
# Fluxo: Win+H dita na caixa -> Enter envia -> claude -p --continue -> Kokoro fala.
# Indicador colorido: Ouvindo (azul) / Pensando (laranja) / Respondendo (verde).
$ErrorActionPreference = "Stop"

# claude.exe emite UTF-8; sem isto o PowerShell decodifica como cp1252 e corrompe
# acentos (mojibake), sujando o texto, o log e a fala do Kokoro.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Sob wscript o cwd herdado vem no formato 8.3 (ex.: M32C6~1.RAF) e o provider
# do PowerShell nao resolve esse alias, quebrando qualquer operacao de arquivo.
# Fixa um cwd valido em formato longo.
try { Set-Location -LiteralPath "C:\Users\m.rafael" } catch { }

# Silencia o gancho Stop do Kokoro (say.py) so para as chamadas deste Hub.
# O Hub fala por conta propria; sem isto a mesma resposta sairia falada 2 vezes.
$env:VOICE_HUB = "1"

$kpy      = "C:\Users\m.rafael\.claude\hooks\kokoro-tts\.venv\Scripts\python.exe"
$speakSrv = "C:\Users\m.rafael\.claude\hooks\voice-input\speak_server.py"
$vault    = "C:\Users\m.rafael\Documents\Obsidian Vault"
$log      = Join-Path $vault "_agentes\voice-hub.md"

# Protocolo de arquivos com o falador residente (speak_server.py).
# Caminho longo explicito: $env:TEMP pode vir em formato 8.3 que o provider
# nao resolve. E a mesma pasta fisica que o python usa (tempfile.gettempdir).
$tmp   = "C:\Users\m.rafael\AppData\Local\Temp"
$req   = Join-Path $tmp "hub_say_req.txt"
$done  = Join-Path $tmp "hub_say_done.txt"
$ready = Join-Path $tmp "hub_say_ready.txt"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class KB {
  [DllImport("user32.dll")] public static extern void keybd_event(byte v, byte s, uint f, UIntPtr e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  public const byte LWIN=0x5B; public const byte H=0x48; public const byte ALT=0x12;
  public static void WinH(){
    keybd_event(LWIN,0,0,UIntPtr.Zero); keybd_event(H,0,0,UIntPtr.Zero);
    keybd_event(H,0,2,UIntPtr.Zero); keybd_event(LWIN,0,2,UIntPtr.Zero);
  }
  // Forca o foco real do teclado para a janela. O toque em ALT engana o
  // bloqueio de foreground do Windows, sem isso o Win+H digita na janela errada.
  public static void Foreground(IntPtr h){
    ShowWindow(h,9); // SW_RESTORE
    keybd_event(ALT,0,0,UIntPtr.Zero); keybd_event(ALT,0,2,UIntPtr.Zero);
    SetForegroundWindow(h);
  }
}
"@

$form = New-Object System.Windows.Forms.Form
$form.Text = "Claude Voice"
$form.ClientSize = New-Object System.Drawing.Size(384,196)
$form.FormBorderStyle = "FixedToolWindow"
$form.StartPosition = "CenterScreen"
$form.TopMost = $true

# Indicador de estado (cor + texto)
$ind = New-Object System.Windows.Forms.Label
$ind.SetBounds(10,10,364,48)
$ind.TextAlign = "MiddleCenter"
$ind.Font = New-Object System.Drawing.Font("Segoe UI",14,[System.Drawing.FontStyle]::Bold)
$ind.ForeColor = [System.Drawing.Color]::White

$tbIn = New-Object System.Windows.Forms.TextBox
$tbIn.Multiline = $true; $tbIn.SetBounds(10,66,364,74)
$tbIn.Font = New-Object System.Drawing.Font("Segoe UI",12)
$tbIn.ScrollBars = "Vertical"

$btn = New-Object System.Windows.Forms.Button
$btn.Text = "Enviar (Enter)"; $btn.SetBounds(10,148,364,36)
$btn.Font = New-Object System.Drawing.Font("Segoe UI",10)

$form.Controls.AddRange(@($ind,$tbIn,$btn))

function Set-State($name) {
    switch ($name) {
        "listen" { $ind.BackColor = [System.Drawing.Color]::FromArgb(33,118,209);  $ind.Text = "Ouvindo... fale agora" }
        "think"  { $ind.BackColor = [System.Drawing.Color]::FromArgb(230,140,20);   $ind.Text = "Claude pensando..." }
        "speak"  { $ind.BackColor = [System.Drawing.Color]::FromArgb(40,160,70);    $ind.Text = "Claude respondendo..." }
    }
    $ind.Refresh(); [System.Windows.Forms.Application]::DoEvents()
}

function Start-Dictation {
    $tbIn.Clear()
    $form.TopMost = $true
    Set-State "listen"
    [KB]::Foreground($form.Handle)
    $tbIn.Focus(); [void]$tbIn.Select()
    Start-Sleep -Milliseconds 500
    [KB]::WinH()
}

function Send-Turn {
    $text = $tbIn.Text.Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { return }
    $btn.Enabled = $false
    Set-State "think"

    Set-Location $vault
    $reply = ($null | & claude -p $text --continue 2>$null | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($reply)) { $reply = "(sem resposta)" }

    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    if (-not (Test-Path (Split-Path $log))) { New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null }
    Add-Content -Path $log -Encoding utf8 -Value "`n**[$stamp] EU:** $text`n**[$stamp] CLAUDE:** $reply"

    # Hub fala via servidor residente (modelo ja carregado = sem delay).
    # Gancho Stop do Kokoro esta silenciado via VOICE_HUB (sem fala dobrada).
    Set-State "speak"
    Remove-Item $done -ErrorAction SilentlyContinue
    Set-Content -Path $req -Value $reply -Encoding UTF8
    $waited = 0
    while (-not (Test-Path $done) -and $waited -lt 1800) {
        [System.Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 100; $waited++
    }
    Remove-Item $done -ErrorAction SilentlyContinue

    $btn.Enabled = $true
    Start-Dictation
}

$btn.Add_Click({ Send-Turn })
$tbIn.Add_KeyDown({
    # Enter envia; Shift+Enter quebra linha (raramente necessario no ditado).
    if ($_.KeyCode -eq "Return" -and -not $_.Shift) { $_.SuppressKeyPress = $true; Send-Turn }
})
function Start-SpeakServer {
    # Encerra qualquer servidor antigo e sobe um novo (carga unica do modelo).
    Set-Content -Path $req -Value "__quit__" -Encoding UTF8
    Start-Sleep -Milliseconds 400
    Remove-Item $req,$done,$ready -ErrorAction SilentlyContinue
    Start-Process -FilePath $kpy -ArgumentList @($speakSrv) -WindowStyle Hidden | Out-Null
}

$form.Add_Shown({ $form.Activate(); Start-SpeakServer; Start-Dictation })
# Ao fechar a janela, encerra o servidor de fala residente.
$form.Add_FormClosing({ Set-Content -Path $req -Value "__quit__" -Encoding UTF8 })

[void]$form.ShowDialog()
