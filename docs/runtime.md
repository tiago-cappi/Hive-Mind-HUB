# Runtime do Hub e acervo pessoal

Atualização de 08/10/2026. Fontes: hub_runtime/, server.py e mobile/config.py.

## Fronteira

O projeto contém todo código, configuração, instruções operacionais, agentes,
skills e documentação específicos do Hub. O vault contém notas, ideias, memória,
transcript, histórico mobile e relatórios pessoais. Relatórios HTML/JS pessoais
continuam no acervo. ForestOS está removido; material antigo em docs/historico/
é somente referência, sem ativação automática.

## Caminhos e dependências

- PROJECT_ROOT deriva de hub_runtime/paths.py. Não depende do vault nem de pasta global.
- HUB_VAULT recebe caminho absoluto de uma pasta existente, separada do projeto.
  Padrão desta instalação: ~/Documents/Obsidian Vault. Configuração inválida
  causa erro; o Hub não cria outro acervo silenciosamente.
- Voz: hub_runtime/voice/speak_server.py, models/ e .venv/.
  Modelos: kokoro-v1.0.onnx e voices-v1.0.bin, provisionados localmente.
- Instalação e autenticação do CLI Claude, Python e Chrome permanecem no sistema.
  Nenhum componente específico do Hub usa a cópia global antiga como fonte.
- Estado técnico privado em hub_runtime/state/, ignorado no Git. Backups privados
  em .migration-backups/; não são código ativo nem documentação para a IA.

## Configuração da IA

hub_runtime.assistant é o único lançador da configuração operacional, usado
pelo persistente e fallback. Executa a partir do projeto e adiciona o acervo
explicitamente. Carrega uso-pessoal.md, settings geradas e hooks locais.
Exclui CLAUDE/AGENTS e rules de desenvolvimento da descoberta automática;
desliga memória automática específica do projeto e hooks globais, preservando
a autenticação existente. Instalação validada com CLI 2.1.289. Política gerenciada
do fornecedor continua valendo. Não usar --bare ou --safe-mode como substituição.

O Codex lê AGENTS e docs/desenvolvimento para desenvolver; a IA de uso cotidiano
recebe instruções diferentes para registrar e consultar conteúdo pessoal.
Trocar o diretório de execução não troca o fornecedor/modelo de conversa do Hub.

O contexto é retomado por ID explícito do sid, incluindo no fallback.
A prova de retomada real cobre IDs criados pelo runtime novo. O registro SESS
é somente em memória: ao reiniciar a ponte, a abertura normal inicia nova sessão,
como antes; não importa automaticamente a conversa anterior. Transcript, notas,
relatórios e armazenamento global do CLI permanecem preservados. A retomada
manual de IDs anteriores à migração não foi testada nem é prometida.
Não usar --continue global ao diretório: isso poderia misturar conversas de
abas ou de sessões de desenvolvimento. Reset cria uma nova conversa.
A configuração usa snapshots de prompt desligados para retomar instruções
atuais junto do histórico, sem carregar automaticamente o velho guia do vault.

## HiveMind opt-in

`hub_runtime.assistant --hivemind` é um lançador separado e somente para as
sessões efêmeras do HiveMind: sem vault, instruções pessoais, memória, plugins,
MCP ou ferramentas nativas. Não usar esse modo para o assistente cotidiano nem
usar `--safe-mode` como substituto geral de runtime. Isolamento, versões dos
CLIs, estado em `HiveMind/state/` e recuperação estão em
[hivemind/adaptadores.md](hivemind/adaptadores.md) e
[hivemind/backend.md](hivemind/backend.md).

## Guarda de arquivos

Código: hub_runtime/guards/file_guard.py. Estado: hub_runtime/state/guards/.
PreToolUse segura o acervo durante uma ferramenta; PostToolUse atualiza a versão
observada e libera a posse. Falha e PostToolBatch liberam ferramentas que não
concluíram. A posse só fica ativa depois de publicar metadados completos por rename;
publicação abandonada e retirada parcial são recuperáveis sob control.
Lock não é roubado por TTL de um escritor vivo; dono morto pode ser recuperado.
Eventos atrasados só liberam posse quando owner e tool_use_id coincidem.
Falhas transitórias de remoção têm tentativas limitadas; falha definitiva é reportada. Leitura atualiza a assinatura da sessão; edição com versão defasada
é recusada, exigindo releitura e recálculo. Nota existente exige Read antes de
Write/Edit. Texto de prompt sozinho não implementa esse controle.

Ferramentas de arquivo no vault, shell síncrono e MCP são cobertos. Shell/MCP
observam o inventário do acervo porque os destinos não são inferíveis do comando.
Operações internas de transcript e histórico mobile usam seus próprios locks
e ficam fora desse inventário. Ferramentas com run_in_background são recusadas:
sua escrita não pode continuar depois da liberação do lock. Não contornar a
guarda por scripts que lancem escritores independentes. A proteção é cooperativa
entre sessões do Hub; não é um sandbox de comandos maliciosos nem trava o Obsidian
e outros programas externos. Para novos canais de escrita, validar cobertura.

## Voz e instância

SPEAK_Q continua única. Protocolo hub_say_* e __stream__/__quit__ preservado.
HUB_SPEAK_TEMP é passado pelo servidor ao residente; por padrão o canal fica
em %TEMP%/core_hub_<hash-da-raiz>, separado de ferramentas globais de voz.
O processo que iniciou o residente é seu dono e registra os PIDs em state/.
Um lock de inicialização serializa lançadores; outro acompanha a vida da ponte
e impede duplicação mesmo antes do bind ou quando server.py é iniciado diretamente.
São locks do sistema operacional, liberados quando o processo termina.

GET /hub_identity retorna protocolo, raiz e PID. launch.py confirma a identidade
antes de reutilizar a porta. stop_instance.ps1 confirma identidade, marcador e
command line dos arquivos desta instalação antes de taskkill /T. Porta ocupada
por outro serviço causa conflito; não autoriza matar esse ocupante. O endpoint
é apenas local e não foi adicionado à whitelist mobile.

## Recriar a voz

Usar Python 3.13 compatível com a instalação validada:

```powershell
python -m venv hub_runtime/voice/.venv
./hub_runtime/voice/.venv/Scripts/python.exe -m pip install -r hub_runtime/voice/requirements-lock.txt
./hub_runtime/voice/.venv/Scripts/python.exe -m pip check
```

O lock declara as versões exatas da instalação anterior. requirements.txt
lista dependências diretas; usar o lock para reproduzir a instalação validada.
Modelos e ambientes não são versionados; manifesto registra hashes. Não copiar
uma venv global pronta. A instalação do Flask/STT continua em .venv da raiz.

## Dados pessoais

Transcript: <vault>/_agentes/voice-hub.md. Relatórios: <vault>/_agentes/relatorios/.
Histórico mobile: <vault>/_agentes/historico-mobile.json; override por
HUB_MOBILE_HISTORY_FILE. Token e log de acesso continuam privados no mobile/.
Persistente e fallback ficam registrados por sid, com reserva serializada dos
slots e o mesmo teto de seis processos de IA. Cancelar, fechar/resetar sessão
ou encerrar a ponte interrompe a árvore do processo em curso; o timeout do fallback
também encerra seus descendentes. Um turno cancelado não inicia novo fallback
nem publica resposta ou transcript tardios.

Transferência do JSON anterior deve comprovar integridade antes de retirar a
origem, sem sobrescrever destino existente.

## Migração e recuperação

Plano e evidências em docs/planos/2026-10-08_centralizacao-hub/.
Usar manifesto para saber o que foi copiado, retirado ou continua pendente.
Backups não substituem notas novas geradas depois da transição; restaurar código
e configuração individualmente e reconciliar dados pessoais sem overwrite.

O protótipo WinForms e seus dois lançadores globais foram arquivados, sem ativação,
em docs/historico/voice-hub-winforms/, com hashes e backup privado. A voz global
compartilhada permanece para consumidores genéricos.
