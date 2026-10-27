# Protótipo WinForms do Voice Hub — arquivo histórico

Arquivado em 08/10/2026. Não é componente executável do Hub atual. Estes três
arquivos são cópias exatas do protótipo global Win+H/WinForms e seus lançadores.
Usavam Claude no vault, --continue e o residente global. Não executar nem ativar
automaticamente; a instalação atual usa os lançadores da raiz do projeto.

- `voice_hub.ps1`: 6265 bytes, SHA-256 `592a0eb942a6a2460b56ba5269587b703c9c4eb5710988a94da99cf494708177`.
- `launch_voice_hub.cmd`: 236 bytes, SHA-256 `ddaa86d12587f534b93bae0feed3652b515868f1ac6931d5bc661c4281536650`.
- `launch_voice_hub.vbs`: 304 bytes, SHA-256 `ed6fbf44094d542677649bba2b2070dc8119bc3ab6aa9b3480cdbf8839ff0f6c`.

Origem: ~/.claude/hooks/voice-input/. Consumidores encontrados: apenas os dois
lançadores deste próprio protótipo. Atalho desktop do Hub atual já é canônico;
nenhum atalho/tarefa identificado usa o protótipo. Fonte compartilhada de voz,
modelos e ferramentas globais genéricas permanecem preservados. Backup privado
em .migration-backups/2026-10-08_centralizacao-hub/global/voice-hub-winforms/.

O residente original `speak_server-original.py` também foi arquivado byte a byte,
SHA-256 `67d4006caa205da801be182da96664388ab38d223af754a9174b527ca29fa72d`. Depois da retirada dos dois Hubs antigos, a busca de
referências globais não encontrou outro consumidor desse residente. Os hooks
genéricos say.py/speak.py sintetizam diretamente com Kokoro e mantêm seus
modelos/venv compartilhados; não dependem deste arquivo.
