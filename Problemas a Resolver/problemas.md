# Problemas a resolver

Lista de problemas conhecidos do Hub C.O.R.E. que ainda precisam de investigação
ou correção.

## Troca de modelo parece perder o histórico da conversa

Ao alternar para o modelo Sonnet no meio de uma sessão, parece que o histórico
da conversa que estava rolando com outro modelo é esquecido — como se a troca
resetasse o contexto em vez de continuar a mesma conversa.

Verificar em `server.py`: a troca de modelo (dropdown) mata o processo `claude`
daquele `sid` e reinicia com o novo modelo (ver `docs/servidor-api.md` e
`docs/arquitetura.md`, seção sobre troca de modelo). Confirmar se esse restart
usa `--continue` ou algum mecanismo de retomada de contexto, ou se está de fato
zerando a conversa sem querer.
