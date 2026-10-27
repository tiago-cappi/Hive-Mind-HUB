#!/usr/bin/env python
"""Lancador do Hub de voz.

Garante a ponte (server.py) no ar e abre a pagina em app-mode no Chrome
NORMAL do usuario (perfil default) -- e nele que o microfone Cirrus funciona;
um perfil dedicado caia no input default errado ("Could not start audio source").

Reabrir o Hub reaproveita o servidor ja no ar (nao sobe outro, nao acumula
Kokoro). FECHAR A JANELA DO HUB DERRUBA A PONTE: o HUD pulsa em /hud_ping e da
baixa em /hud_bye, e o servidor se encerra quando nao sobra janela viva. Antes
ele ficava residente para sempre -- um pythonw chegou a 18h no ar com codigo
velho em memoria. Para deixar a ponte de pe sem HUD (celular): HUB_AUTOQUIT=0.
Encerrar na mao continua valendo: stop.cmd ou restart_hub.ps1.
"""
import os
import time
import socket
import subprocess
from hub_runtime.instance import verify
from hub_runtime.instance_lock import hold

HERE = os.path.dirname(os.path.abspath(__file__))
VHPYW = os.path.join(HERE, ".venv", "Scripts", "pythonw.exe")
SERVER = os.path.join(HERE, "server.py")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 8765
URL = f"http://127.0.0.1:{PORT}"


def port_open():
    try:
        with socket.create_connection(("127.0.0.1", PORT), 0.3):
            return True
    except OSError:
        return False


def main():
    with hold("startup"):
        if not port_open():
            subprocess.Popen([VHPYW, SERVER], cwd=HERE, creationflags=0x08000000)  # CREATE_NO_WINDOW
            # 1a vez carrega whisper; espera ate ~90s.
            for _ in range(300):
                if port_open():
                    break
                time.sleep(0.3)
        if not port_open():
            raise RuntimeError("A ponte não iniciou em 90 segundos; consulte a configuração e as dependências.")
        verify(URL)
    # Chrome normal (perfil default): mic do usuario ja funciona aqui.
    # --app abre janela limpa; se o Chrome ja estiver aberto, anexa a sessao.
    # HUD widescreen (C.O.R.E.): janela larga; abaixo de 1100px o layout empilha.
    subprocess.Popen([CHROME, f"--app={URL}", "--window-size=1680,980",
                      "--window-position=40,24"])


if __name__ == "__main__":
    main()
