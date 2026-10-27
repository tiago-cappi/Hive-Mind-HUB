"""Modulo mobile do Hub C.O.R.E. — conversar com o Claude pelo celular, na LAN.

Isolado de proposito: o `server.py` (porta 8765) continua escutando SO em
127.0.0.1, sem autenticacao e com permissoes liberadas. Quem vai a rede e este
modulo, numa porta propria (8766), atras de token, com whitelist de rotas.

Pecas:
  config.py   constantes e variaveis de ambiente (unico lugar que le os.environ)
  auth.py     token, cookie, faixa de rede, freio de tentativas, log de acesso
  bridge.py   cliente HTTP do Hub local — a unica coisa que fala com o 8765
  history.py  historico de turnos em JSON, persistente entre reinicios
  session.py  turno em curso: um por vez, com buffer para recuperar queda de rede
  app.py      as rotas Flask e a pagina
  run.py      entrypoint: sobe o servidor e imprime o link do celular
"""
