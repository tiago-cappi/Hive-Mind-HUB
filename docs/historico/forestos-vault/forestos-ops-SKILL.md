---
name: forestos-ops
description: Opera o ForestOS (produtividade gamificada — Setor/Projeto/Objetivo/Missão/Hábito/Lembrete/Anotação, foco, XP, streaks) através da CLI do Hub C.O.R.E., nunca editando notas ou estado na mão. Use quando o usuário pedir para criar setor/projeto/objetivo/missão/hábito/lembrete/anotação, iniciar ou parar foco, colher uma missão, completar ou desfazer um hábito, adicionar/marcar/remover mini-missão de uma sessão multi-missão, ou confirmar (ack) um lembrete.
---

# forestos-ops

O ForestOS foi migrado para o Hub C.O.R.E. (`voice-hub/`). O Obsidian agora é
**read-only** — o Vault não escreve mais estado nem frontmatter do ForestOS por
conta própria. Toda ação do ForestOS passa **exclusivamente** pela CLI Node do
Hub.

## Regra dura — nunca editar na mão

- **NUNCA** editar diretamente nenhuma nota `.md` de `forestos/` (frontmatter
  ou corpo) para refletir uma ação do ForestOS (criar entidade, mudar status,
  focar, colher, completar hábito, dar ack em lembrete etc.).
- **NUNCA** editar diretamente `forestos/_state/profile.json` nem
  `forestos/_state/events.jsonl`.
- Toda mutação de estado do ForestOS é feita **somente** invocando a CLI
  abaixo. A CLI é o único escritor (lock próprio, regras de XP/streak
  centralizadas).
- **Sem pedir confirmação ao usuário** antes de agir — execute o comando da
  CLI diretamente.
- Ao final, **a resposta declara o efeito** de forma objetiva, ex.:
  "Colhida: Revisar PR, +42 XP" ou "Hábito 'Ler 20min' completo, streak 7→8".

## Como invocar a CLI

Caminho absoluto exato do executável (Windows):

```
node C:/Users/m.rafael/.claude/hooks/voice-hub/forestos/cli.js <cmd> [args...]
```

O vault-alvo é o padrão (`C:\Users\m.rafael\Documents\Obsidian Vault`), a
menos que a env `FORESTOS_VAULT` esteja setada. Cada comando imprime **um
único JSON** no stdout descrevendo o efeito (`{ok:true, ...}` ou
`{ok:false, error:"..."}`). Leia esse JSON para compor a declaração de efeito
da resposta — não adivinhe o resultado.

## Comandos disponíveis

### Perfil e eventos (baixo nível — normalmente não é preciso chamar direto)

- `node cli.js profile:read` — lê `profile.json` (`total_xp`, `level`, `focus`).
- `node cli.js profile:write '<json patch>'` — aplica um patch no perfil.
- `node cli.js event:append '<json evento>'` — grava 1 evento em `events.jsonl`.
- `node cli.js event:read` — lê todos os eventos.

### Leitura consolidada

- `node cli.js dashboard` — devolve UM JSON com `profile`, `focus`,
  `missionsBySector`, `habits`, `reminders`, `anotacoes`, `cartografia`,
  `heatmaps`, `sectorSummary`. Use para responder "como está meu progresso"
  ou "quais missões estão ativas" sem varrer o vault manualmente.

### Criar entidades

```
node cli.js criar <tipo> '<json campos>'
```

`<tipo>` é um dos 7: `setor`, `projeto`, `objetivo`, `missao`, `habito`,
`lembrete`, `anotacao`.

Campo obrigatório em todos: `title`. Campos aceitos por tipo (todos
opcionais além de `title`; vínculos hierárquicos vão pelo **nome puro** da
entidade-alvo, a CLI grava como wikilink):

- `setor`: `color` (hex, default `#a88a3d`).
- `projeto`: `description`, `sector`, `status` (default `active`),
  `target_date`.
- `objetivo`: `description`, `sector`, `project`, `parent_goal`, `horizon`,
  `status` (default `active`), `target_date`.
- `missao`: `description`, `sector`, `goal`, `parent_mission`,
  `importance` (1-5, default 3), `difficulty` (1-5, default 3), `due_date`.
- `habito`: `description`, `sector`, `goal`, `project`,
  `frequency` (`daily|weekly|custom|monthly`, default `daily`),
  `custom_days` (array), `importance` (default 3), `difficulty` (default 3),
  `color`.
- `lembrete`: `message` (default = `title`), `frequency`
  (`daily|weekly|custom|monthly|once`, default `daily`), `custom_days`,
  `time_of_day` (`HH:MM`), `sector`, `goal`, `due_at` (ISO, usado quando
  `frequency: once`).
- `anotacao`: `content`, `bg_color`.

Exemplo: `node cli.js criar missao '{"title":"Revisar PR","sector":"Trabalho","importance":4,"difficulty":3}'`

Saída: `{ok:true, path, id, tipo}` (ou `{ok:false, error}` se tipo desconhecido
ou `title` ausente).

### Foco (missão / hábito / multi-missão)

- `node cli.js focus start mission <nome-da-missão>` — inicia foco numa
  missão existente. Se já havia um foco ativo, ele é pausado e creditado
  antes (foco é exclusivo).
- `node cli.js focus start habit <nome-do-hábito>` — idem, para hábito.
- `node cli.js focus start multi '<json>'` — inicia sessão multi-missão.
  JSON: `{mode:"stopwatch"|"pomodoro", importance:1-5, difficulty:1-5,
  pomoDuration:min (só se mode="pomodoro"), miniMissions:[{title:"..."}]}`.
  Requer ao menos 1 mini-missão e imp/dif definidos.
- `node cli.js focus stop [minutosOverride]` — para o foco ativo (qualquer
  tipo) e credita conforme a regra: missão acumula `focus_minutes`/`xp_gained`
  na nota (XP só entra no total na colheita); hábito credita XP **direto** no
  total; multi com ≥1 min consolida 1 nota `missao` já `done`+`harvested` com
  XP direto no total, com <1 min descarta sem XP. `minutosOverride` (inteiro)
  substitui o cálculo automático de `now - started_at` — use só quando o
  usuário pedir explicitamente para registrar um tempo manual.
- `node cli.js focus cancel` — encerra o foco ativo **sem** creditar XP (na
  sessão multi, descarta sem gerar nota).

### Colheita

- `node cli.js harvest <nome-da-missão>` — credita `xp_gained` acumulado da
  missão no `total_xp` e marca `done`+`harvested`. Idempotente: chamar de
  novo numa missão já colhida devolve `{ok:true, already:true}` sem creditar
  de novo.

### Hábitos

- `node cli.js habit complete <nome>` — marca o hábito como feito hoje,
  aplica a regra de streak (`nextStreak`). Repetir no mesmo dia devolve
  `{ok:true, already:true}`.
- `node cli.js habit uncomplete <nome>` — desfaz a conclusão de hoje (só se
  foi feito hoje) e decrementa a streak.

### Mini-missões (só dentro de uma sessão multi ativa)

- `node cli.js mini add <título>` — adiciona mini-missão à sessão multi ativa.
- `node cli.js mini toggle <id>` — alterna pendente/concluída.
- `node cli.js mini remove <id>` — remove da sessão.

### Lembretes

- `node cli.js reminder ack <nome>` — marca o lembrete como confirmado hoje
  (`last_acked_at`) e grava o evento `reminder_ack`.

## Erros

Comando ou tipo/entidade desconhecidos nunca derrubam o processo — a CLI
sempre devolve JSON `{ok:false, error:"..."}` com uma mensagem clara. Repasse
essa mensagem ao usuário em vez de tentar adivinhar ou editar arquivos
manualmente para "corrigir" o estado.

## Onde estão as regras de negócio

Fórmulas de XP, peso/tier e streak vivem em `voice-hub/forestos/lib/` e são
reusadas pela CLI sem reescrita — não precisa (e não deve) recalculá-las na
mão. Documentação completa da arquitetura em
`forestos/ForestOS - Documentação Completa.md` do vault.
