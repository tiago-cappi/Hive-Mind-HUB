# Celular na rede de casa (`mobile/`)

> Estado do código em 26/08/2026. Fontes: `mobile/`, `server.py` (campo `mudo`).
> Guia do usuário, sem jargão: `mobile/COMECE-AQUI.md`.

O Hub é um HUD de mesa: microfone do computador, Chrome em app-mode, tela larga.
Este módulo resolve o caso em que **a pessoa está longe da mesa** e quer
continuar a conversa — pelo celular, na mesma rede Wi-Fi de casa.

---

## 1. Por que é um servidor separado

A tentação era ligar `app.run(host="0.0.0.0")` no `server.py` e acabou. Não dá:
a ponte roda **sem autenticação nenhuma** e spawna `claude` com
`--dangerously-skip-permissions`. Quem alcança a porta 8765 executa comandos
nesta máquina, com os arquivos do vault na mão. É a invariante 7 de
`arquitetura.md`, e ela continua valendo — **o `server.py` não mudou de bind**.

O que vai à rede é outro processo, com outra porta e outro contrato:

```
   celular (Wi-Fi de casa)
        |  http://<ip-da-lan>:8766        <- token + cookie + faixa privada
        v
+---------------- mobile/ (Flask proprio, processo separado) --------------+
|  auth.py     nega por padrao: faixa privada -> freio -> token            |
|  session.py  o turno roda em THREAD do servidor, nao na conexao HTTP     |
|  history.py  historico proprio em JSON, persistente                      |
|  bridge.py   whitelist de 5 rotas do Hub — a unica peca que fala com ele |
+-------------------------------|-----------------------------------------+
                                | http://127.0.0.1:8765  (inalterado)
                                v
                    server.py — o Hub, ainda so em loopback
```

Consequência da separação: derrubar o módulo mobile não afeta o Hub, e um bug
aqui não vira acesso a nada além das cinco rotas do `bridge`.

---

## 2. As peças

| Arquivo | Papel |
|---|---|
| `config.py` | Único lugar que lê `os.environ`. Porta, bind, sid, caminhos, limites |
| `auth.py` | Token, cookie, faixas de rede, freio de força bruta, log de acesso |
| `bridge.py` | Cliente HTTP do Hub. Whitelist explícita de rotas. Só stdlib (`urllib`) |
| `history.py` | Turnos em `<vault>/_agentes/historico-mobile.json`, escrita atômica, teto de `HISTORY_MAX` |
| `session.py` | O turno em curso: um por vez, em thread, com `rev` para long-poll |
| `app.py` | As 12 rotas Flask |
| `run.py` | Entrypoint: descobre o IP da LAN, imprime/salva o link, sobe |
| `static/` | A página (`index.html`, `style.css`, `app.js`, `icon.svg`) |
| `firewall.ps1` | Abre a porta 8766 só no perfil **Private** (pede admin) |
| `start_mobile.vbs` / `.ps1` / `stop_mobile.ps1` | Subir sem console / com console / derrubar |

Arquivos de estado, todos no `.gitignore` do módulo: `.secret`, `LINK.txt` e `access.log`. O histórico pessoal fica no vault,
configurável por `HUB_MOBILE_HISTORY_FILE`; ver `runtime.md`.

---

## 3. O cadeado (`auth.py`)

Três camadas, **nesta ordem** — a de rede vem antes da de token de propósito,
para que um cookie roubado não sirva de fora de casa:

1. **Faixa de rede.** `_FAIXAS` lista explicitamente 10/8, 172.16/12,
   192.168/16, 169.254/16, 127/8 e os equivalentes IPv6. Não usa
   `ipaddress.is_private`, que também aceita os blocos de documentação
   (203.0.113.0/24 e amigos) e o CGNAT 100.64.0.0/10. Desligável por
   `HUB_MOBILE_LAN_ONLY=0`, o que **não** se deve fazer.
2. **Freio.** `FAIL_MAX = 8` tokens errados por IP → `FAIL_WINDOW = 600`s de
   silêncio, inclusive para o token certo.
3. **Token.** 32 chars (`secrets.token_urlsafe(24)`), gerado no primeiro boot em
   `mobile/.secret`, comparado com `secrets.compare_digest`. Aceito em `?t=`
   (link), no campo do `/login` ou no cabeçalho `X-Core-Token`. Validado uma
   vez, vira cookie `HttpOnly`/`SameSite=Lax` de 60 dias.

`client_ip()` ignora `X-Forwarded-For` de propósito: não há proxy nesta
topologia, e confiar no cabeçalho deixaria o cliente escolher o próprio IP —
furo direto na camada 1.

**Sem TLS.** O tráfego é HTTP simples dentro da LAN: quem já está na sua rede
Wi-Fi consegue ler o token no fio. É a troca aceita para não ter certificado
auto-assinado e o aviso de segurança do navegador. Também é o motivo de o
microfone do navegador não ser usado (`getUserMedia` exige contexto seguro) — o
ditado do teclado do celular resolve o mesmo problema sem infraestrutura.

---

## 4. O turno não vive na aba (`session.py`)

O problema do celular: a tela apaga, o navegador congela a aba em segundo plano,
o Wi-Fi troca de canal. Se a resposta viesse por streaming HTTP preso à
conexão, cada uma dessas coisas mataria o turno no meio.

Então o turno roda em **thread do servidor**, alimentada pelo `bridge`, e a
página só **observa**:

- `_ST` guarda `rev`, `seq`, `busy`, `q`, `txt`, `passos`, `pensando`, `erro`.
- `rev` sobe a cada evento; `_CHANGED` (`threading.Condition`) acorda quem
  espera.
- `GET /api/state?rev=N` é **long-poll**: segura até 25s esperando `rev` passar
  de N. Texto nascendo na tela sem martelar a rede.
- **Um turno por vez** (`409` no segundo): é uma pessoa com um celular, e dois
  turnos no mesmo `sid` disputariam o lock do sid lá no Hub de qualquer jeito.

Fechar o navegador **não cancela nada**. O Claude termina, o turno entra no
histórico, e a resposta está lá quando o aparelho voltar. Coberto por
`test_desligar_o_celular_no_meio_nao_perde_a_resposta`.

---

## 5. A whitelist (`bridge.py`)

O celular alcança exatamente cinco rotas do Hub:

| Rota do Hub | Para quê |
|---|---|
| `POST /ask` | conversar |
| `POST /session_reset` | nova conversa |
| `POST /abort` | parar o turno |
| `GET /reports` | listar relatórios |
| `GET /reports/<fn>` | abrir um relatório |

Não há caminho daqui para `/forestos/action`, `/speak`, `/session_end` ou
`/stt`. Rota nova no Hub **não** vira rota nova no celular sozinha — tem que ser
escrita no `bridge`. Dois testes-canário guardam isso:
`test_bridge_so_conhece_as_rotas_da_whitelist` falha se alguma proibida aparecer
no arquivo, e `test_nao_ha_rota_de_shell_nem_de_arquivo` congela o `url_map` do
módulo.

`report_bytes` descarta o caminho do nome do arquivo antes de repassar
(`../../server.py` → `server.py`); quem barra traversal de verdade continua
sendo o `send_from_directory` do Hub.

---

## 6. Sessão, silêncio e o campo `mudo`

O celular usa `sid = "mobile"` (env `HUB_MOBILE_SID`), com `titulo = "Celular"`
— é assim que ele aparece no transcript `_agentes/voice-hub.md` do vault.
Contexto próprio, separado das abas do computador, e **ocupa 1 dos 6 slots** de
`MAX_SESS`.

A única alteração fora da pasta é o campo **`mudo`** no `POST /ask` do
`server.py`: quando verdadeiro, o turno não aciona a fala em streaming. Sem ele,
o computador declamaria em voz alta, sozinho, uma resposta que a pessoa está
lendo do outro cômodo. Ausente ou `false` = comportamento de sempre, então o
`index.html` segue idêntico.

Na tela do celular isso é a opção **"falar a resposta no computador"**
(desligada por padrão). Com ela ligada (`mudo: false` explícito), se a fala em
streaming não engatar no meio do turno (resposta menor que `SPEAK_MIN`, árbitro
ocupado), o próprio `/ask` do Hub enfileira a fala clássica no fim do turno —
o celular não tem como chamar o `/speak` de fallback do HUD, que nem está na
whitelist do `bridge`. Ver `servidor-api.md` §4.5. A opção irmã, **"ler a resposta aqui"**, usa o
`speechSynthesis` do próprio aparelho — o texto é lido por frases fechadas
conforme chega, e a síntese é aquecida no toque do botão porque iOS e Android só
liberam voz depois de um gesto do usuário.

### O modelo e o esforço, na gaveta de opções

O seletor **Modelo** manda o alias do CLI (`opus`, `fable`, `sonnet`, `haiku`,
ou vazio = default do Hub) junto do `POST /api/ask`. `session.py` guarda a
escolha em `_ST["modelo"]` — a tela não precisa repeti-la a cada turno — e
`config.MODELOS` espelha o `ALLOWED_MODELS` do `server.py`: nome fora da lista
vira `""`, então a tela nunca injeta uma flag inventada no spawn. A validação
é dupla de propósito (aqui e no Hub); o custo é uma tupla.

Trocar de modelo **mantém a conversa**: o `server.py` compara `s["model"]` com
o pedido e, se mudou, mata e resobe o `claude` daquele sid — mas o processo novo
sobe com `--resume s["cid"]`, então o histórico continua valendo no modelo novo.
O processo troca, a conversa não. (Até 2026-08-28 o contexto se perdia aqui; ver
`servidor-api.md` §4.1.) O `/api/reset` também aceita `{modelo}` para o botão
"nova conversa" já subir no modelo certo — e aí sim o contexto é zerado.

O seletor **Esforço** é o mesmo mecanismo, um andar ao lado: manda `low`,
`medium`, `high`, `xhigh`, `max` ou vazio, guardado em `_ST["esforco"]` e
validado contra `config.ESFORCOS`, que espelha o `ALLOWED_EFFORTS` do
`server.py` e vira `--effort` no spawn. Vale a mesma regra: mudar o nível
resobe o `claude` do sid, também com `--resume`, sem perder a conversa. Os dois seletores
viajam juntos em `/api/ask` e em `/api/reset`, e ficam guardados no
`localStorage` do aparelho.

### O que o celular faz aparece no computador (§6-bis)

O HUD do computador mostra a sessão do celular numa aba especial **CELULAR**
(📱, somente leitura), que nasce sozinha na primeira atividade: a pergunta
enviada do aparelho, as etapas ("Lendo server.py"…), a resposta nascendo, o
plano e as alterações de arquivo — tudo com os mesmos widgets das abas normais.
O caminho é o espelho `GET /session_watch/mobile` do Hub (long-poll, fila de
linhas): o front do computador **observa** o NDJSON dos turnos do celular sem
consumi-lo nem interferir. A pergunta chega pelo evento `ask`, publicado pelo
próprio `/ask` no começo de cada turno. Detalhes: `servidor-api.md` §4.6 e
`frontend.md` (aba CELULAR).

Se a aba ativa do HUD estiver ociosa, a aba CELULAR assume o foco quando um
turno começa no celular; ocupada, ela fica em segundo plano com o ponto de
não lida. Ela não tem microfone, não envia turnos e fechá-la não mata nada —
o processo `claude` do sid `mobile` pertence ao celular.

---

## 7. Rotas do módulo

| Rota | Método | Papel |
|---|---|---|
| `/` | GET | a página (sem cookie → `/login`) |
| `/login` | GET/POST | entrada; com `?t=` já grava o cookie e redireciona |
| `/api/state` | GET | snapshot do turno; com `?rev=N` vira long-poll |
| `/api/ask` | POST | `{texto, falar, modelo, esforco}` → dispara o turno em segundo plano |
| `/api/cancel` | POST | mata o turno em curso no Hub |
| `/api/reset` | POST | `{modelo, esforco}` → nova conversa |
| `/api/history` | GET | `?limit=N` turnos guardados |
| `/api/history/clear` | POST | esvazia o histórico do celular |
| `/api/reports` | GET | lista os relatórios do vault |
| `/api/reports/<fn>` | GET | serve um relatório |
| `/manifest.webmanifest` | GET | PWA (ícone na tela inicial) |

Todas com `Cache-Control: no-store`. Todas atrás do cadeado, exceto `/login` e
`/manifest.webmanifest`.

---

## 8. Operação

```powershell
# subir (sem console)          -> mobile\start_mobile.vbs
# subir mostrando o link       -> ./.venv/Scripts/python.exe -m mobile.run
# derrubar                     -> ./mobile/stop_mobile.ps1
# liberar a porta (1x, admin)  -> mobile\firewall.ps1
# testes                       -> ./.venv/Scripts/python.exe -m pytest tests/test_mobile.py -q
```

O link com o token fica em `mobile/LINK.txt` a cada boot. Trocar o token: apague
`mobile/.secret` e suba de novo (todos os celulares saem).

O Hub precisa estar no ar — o módulo não o sobe. Com a ponte fora, a página
abre, a bolinha fica vermelha e os turnos falham com erro legível
(`bridge.HubOffline`), sem stacktrace.

Variáveis de ambiente: `HUB_MOBILE_PORT` (8766), `HUB_MOBILE_BIND` (0.0.0.0),
`HUB_MOBILE_URL` (127.0.0.1:8765), `HUB_MOBILE_SID` (`mobile`),
`HUB_MOBILE_HISTORY` (200), `HUB_MOBILE_LAN_ONLY` (1).

A regra do firewall é criada só no perfil **Private**. Se a rede Wi-Fi estiver
marcada como pública no Windows, o celular não conecta — `Get-NetConnectionProfile`
mostra em qual perfil a rede está.

---

## 9. Limitações conhecidas

- **Sem TLS** (seção 3): quem já está na sua LAN pode ler o token no fio.
- **Sem microfone no navegador**: consequência do item acima. O ditado do
  teclado do celular cobre o caso de uso.
- **Só rede local.** Acesso de fora exigiria VPN (Tailscale) ou túnel, com o
  cadeado atual valendo como segunda camada. Fora do escopo por decisão de uso.
- **Um turno por vez** e **um `sid` só**: não há abas paralelas no celular.
- **O IP da máquina pode mudar** com o DHCP do roteador; o link some junto.
  Reserva de IP no roteador resolve de vez.
- **Notificação de resposta pronta não existe.** Se a tela estiver apagada
  quando o turno terminar, você só descobre ao voltar ao app.
- **O `speechSynthesis` do celular é do sistema**, não o Kokoro — a voz é a do
  Android/iOS, diferente da voz do Hub no computador.

## Centralização em 08/10/2026

O gateway usa a ponte da raiz canônica, mantendo token, whitelist e estado
do turno. O histórico pessoal saiu do módulo e fica em
`<vault>/_agentes/historico-mobile.json`. O token não foi rotacionado.
O endpoint `/hub_identity` não é encaminhado ao celular. Configuração de
acervo e arquitetura em `runtime.md`; inventário e corte no plano da migração.
