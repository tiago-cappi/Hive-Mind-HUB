#!/usr/bin/env python
"""Sobe o servidor do celular e mostra o link para abrir no aparelho.

    ./.venv/Scripts/python.exe -m mobile.run

Imprime o endereco na rede de casa, o token (gerado sozinho na primeira vez) e
grava o link pronto em `mobile/LINK.txt` — e so mandar para si mesmo e clicar
uma vez; o cookie vale 60 dias.

O Hub (server.py, porta 8765) precisa estar no ar. Se nao estiver, este script
avisa e sobe assim mesmo — a pagina abre e reclama ate a ponte voltar.
"""
import os
import sys
import socket
import ipaddress

if __package__ in (None, ""):     # permite `python mobile/run.py` tambem
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "mobile"

from . import auth, bridge, config          # noqa: E402
from .app import app                        # noqa: E402

try:                                        # console do Windows e cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def lan_ips():
    """IPv4 privados desta maquina, o mais provavel primeiro."""
    achados = []
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:                                    # nao envia pacote: so escolhe a rota
        s.connect(("8.8.8.8", 80))
        achados.append(s.getsockname()[0])
    except OSError:
        pass
    finally:
        s.close()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            achados.append(info[4][0])
    except OSError:
        pass
    out = []
    for ip in achados:
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if a.is_private and not a.is_loopback and ip not in out:
            out.append(ip)
    return out


def qr(texto):
    """QR no terminal, se a lib `qrcode` existir. Sem ela, so nao ha QR."""
    try:
        import qrcode                       # noqa: PLC0415
    except ImportError:
        return False
    q = qrcode.QRCode(border=1)
    q.add_data(texto)
    q.make(fit=True)
    q.print_ascii(invert=True)
    return True


def main():
    tok = auth.token()
    ips = lan_ips()
    principal = ips[0] if ips else "127.0.0.1"
    link = f"http://{principal}:{config.PORT}/login?t={tok}"

    try:
        with open(os.path.join(config.HERE, "LINK.txt"), "w", encoding="utf-8") as fh:
            fh.write(link + "\n")
    except OSError:
        pass

    print()
    print("  C.O.R.E. · celular ".ljust(58, "-"))
    print(f"  Hub (127.0.0.1:8765) .... {'no ar' if bridge.hub_alive() else 'FORA DO AR — suba o Hub antes'}")
    print(f"  escutando ............... {config.BIND}:{config.PORT}")
    print(f"  so faixa privada ........ {'sim' if config.LAN_ONLY else 'NAO (perigoso)'}")
    print()
    print("  Abra no celular (mesma rede Wi-Fi):")
    print(f"    {link}")
    if len(ips) > 1:
        print("  Outros enderecos desta maquina:")
        for ip in ips[1:]:
            print(f"    http://{ip}:{config.PORT}/login?t={tok}")
    print()
    print(f"  Token (se preferir digitar): {tok}")
    print("  Link salvo em mobile/LINK.txt · Ctrl+C encerra")
    print("  " + "-" * 56)
    qr(link)
    print()

    app.run(host=config.BIND, port=config.PORT, threaded=True)


if __name__ == "__main__":
    main()
