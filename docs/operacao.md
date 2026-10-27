# Operação do Hub

Atualizado em 08/10/2026. Referências: [runtime.md](runtime.md),
[servidor-api.md](servidor-api.md), [voz-tts.md](voz-tts.md).

## Configuração

Executar da raiz. Flask/STT usam .venv; voz usa hub_runtime/voice/.venv e
modelos em hub_runtime/voice/models. CLI Claude instalado/autenticado e Chrome
continuam no sistema. Provisionamento da voz em runtime.md.
HUB_VAULT é o caminho absoluto de um acervo existente e separado do projeto.
Padrão: ~/Documents/Obsidian Vault. Erro de caminho impede execução; não cria
outro acervo. Para alterar permanentemente, configurar o ambiente do usuário.
Não versionar credenciais, state, modelos, venvs ou backups privados.

## Iniciar, parar e reiniciar

```powershell
./.venv/Scripts/python.exe launch.py
./stop.cmd
./restart_hub.ps1
./restart_hub.ps1 -DryRun
```

launch_hub.vbs resolve a pasta onde está salvo e abre launch.py sem console.
launch.py abre Chrome normal em app-mode; reutiliza a ponte somente se
/hub_identity confirmar esta raiz. Lançadores concorrentes aguardam um lock
de inicialização; a ponte mantém outro lock durante sua vida e encerramento. Se a porta estiver ocupada por origem
alheia ou versão antiga sem identidade, o conflito exige identificação manual.

stop.cmd e restart chamam hub_runtime/stop_instance.ps1: identidade e marcador
local são conferidos junto do command line; taskkill /T encerra a árvore própria.
Não usar filtros globais por nome ou matar qualquer ocupante de 8765. DryRun
mostra alvos sem modificar processos. Restart verifica identidade da nova ponte.
PID que veio só do marcador e hoje pertence a outro programa (o Hub caiu e o Windows
reaproveitou o número) é ignorado com aviso e o marcador é descartado; o PID da
identidade viva que não bater continua recusando a parada (teste
`test_stop_ignora_marcador_velho_sem_encerrar_processo_alheio`).

Fechar o último HUD continua acionando autoquit. HUB_AUTOQUIT=0 mantém o Hub
residente para o celular; HUB_HUD_TTL padrão 90 s. Só o dono do residente
manda __quit__. Estado de voz fica em canal temporário por instalação, descrito
em runtime.md, evitando colisão com hooks globais do Claude.

## Testar

```powershell
./.venv/Scripts/python.exe -m pytest tests -q
```

A suíte usa mocks de Whisper, CLI e áudio. Testes da guarda usam processos
independentes e arquivos descartáveis, sem tokens nem notas reais. No sandbox,
se TEMP/TMP não forem graváveis, atribuir diretório temporário exclusivo dentro
do projeto somente ao processo de teste. Não enfraquecer testes por esse motivo.
Testes de cancelamento/timeout também usam processos descartáveis reais, sem API.
Eles precisam de permissão do sistema para encerrar a árvore desses processos;
executá-los no ambiente do usuário quando o sandbox impedir essa operação.
Testes reais de CLI/áudio são registrados na verificação da tarefa.

## Celular

```powershell
mobile/start_mobile.vbs
./mobile/stop_mobile.ps1
```

Precisa da ponte. Gateway conserva token, faixa privada e whitelist; não recebeu
/hub_identity. Token em mobile/.secret, link em mobile/LINK.txt e log em
mobile/access.log são privados. Não publicar ou imprimir esses valores.
Histórico pessoal em <vault>/_agentes/historico-mobile.json; configuração
opcional HUB_MOBILE_HISTORY_FILE. Não apagar token ao migrar o histórico.

## Logs e recuperação

Transcript pessoal: <vault>/_agentes/voice-hub.md. Relatórios pessoais:
<vault>/_agentes/relatorios/. Diagnóstico de turno aparece em DEBUG do HUD.
Estado técnico da instância/guardas: hub_runtime/state/. Não apagar um lock
de escritor vivo; guarda recupera dono morto e exige releitura de versão alterada.

Plano, manifesto e resultados da centralização:
docs/planos/2026-10-08_centralizacao-hub/. Backups privados:
.migration-backups/2026-10-08_centralizacao-hub/. Restaurar arquivos técnicos
individualmente; não sobrescrever o acervo com backup antigo após novas notas.
