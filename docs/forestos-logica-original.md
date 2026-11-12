# ForestOS — a lógica do app original

> **Documento de referência histórica.** O ForestOS foi removido do Hub em
> 28/08/2026 e será refeito do zero (regra 11 do `CLAUDE.md`: pasta própria,
> blueprint Flask, nada em `server.py`/`index.html`). Este texto explica **a ideia
> e a lógica** do app para servir de ponto de partida à reconstrução. Não descreve
> código atual.

## Proveniência — leia antes de confiar

O material tem duas origens com graus de certeza diferentes:

| Parte | Origem | Confiança |
|---|---|---|
| Seção 1 (produto e decisões de escopo) | Resumo recuperado da memória do Claude em 17/08/2026 (`_agentes/voice-hub.md` do vault), de um registro de **11/04/2026** | **Média.** É de segunda mão e a própria sessão pediu confirmação. O plano mestre (`FOREST_OS_PLANO_IMPLEMENTACAO_V2.md`) não está neste computador |
| Seções 2 a 9 (modelo, regras, telas) | Manual `docs/historico/forestos-vault/ForestOS - Documentação Completa.md` e `docs/forestos.md` | **Alta.** Descrevem a versão que rodou no Hub, com fórmulas e contratos de dados |

A versão do Hub foi uma **portagem** do app React+Supabase original, primeiro
para o Obsidian (SQLite + DataviewJS) e depois para o Hub. O manual afirma que
nenhuma fórmula foi reescrita na portagem. Ainda assim, o que existia no app
mobile original além disso (metas por prazo e por direção, revisão diária,
conquistas, energia) **não** chegou à versão do Hub.

---

## 1. A ideia do produto

O ForestOS é um app de produtividade pessoal **anti-procrastinação**, usado pelo
próprio autor no dia a dia (dogfooding). O público é quem procrastina e precisa
**quebrar objetivos grandes em passos pequenos** e, ao mesmo tempo, **construir
hábitos**.

A metáfora é uma **floresta**: você planta trabalho, foca nele, acumula XP e
**colhe** o que concluiu.

### Decisões de produto registradas (app original)

- **Missões** de dois tipos: únicas (com ou sem prazo) e recorrentes (hábitos com
  regra de frequência). Ambas carregam **prioridade e dificuldade**.
- **Metas** de dois tipos: por **prazo** (ex.: "aprender alemão em 1 ano", com
  marcos) e por **direção** (ex.: "ser mais saudável", acompanhada por tendência,
  sem fim definido).
- **Revisão diária** opcional. Convida, nunca trava o uso.
- **Gamificação moderada:** XP, nível, energia, conquistas e streaks com
  recompensa. Inspiração em Habitica e Factorio, **sem RPG completo** (sem avatar,
  pets ou equipamentos).
- **Sem IA conversacional na v1**, de propósito, para manter o foco no loop
  central. A classificação por IA (`POST /ai/classify`) é outra coisa.
- **Mobile-first** (Android/iOS via Capacitor), pensado para uso com um polegar;
  arrastar e soltar vira "toque longo + reordenar".
- **Sync multi-dispositivo obrigatório**, provavelmente via Supabase Realtime.
- **Freemium no futuro:** recursos marcados como pro/free, tudo liberado nos testes.
- **Idioma:** interface em português (BR), código em inglês.
- **Plano de implementação:** 14 fases (0 a 13), de correção de bugs até preparação
  de lançamento.

---

## 2. O loop central

```
planejar (Setor → Projeto → Objetivo → Missão / Hábito)
        │
        ▼
focar (cronômetro ou pomodoro)  ──►  XP e minutos acumulam
        │
        ▼
colher / completar  ──►  XP entra no total, streak sobe, heatmap acende
        │
        ▼
revisar (heatmaps, resumo por setor, lembretes)
```

O sistema existe para tornar visível o progresso de trabalho pequeno e repetido.
Tudo que o usuário faz gera um **evento** que alimenta os heatmaps e o histórico.

---

## 3. As sete entidades

Hierarquia: **Setor → Projeto → Objetivo → Missão**. Fora dela ficam **Hábito**,
**Lembrete** e **Anotação**.

| Entidade | Papel | Campos de destaque |
|---|---|---|
| **Setor** | Área da vida (ex.: Saúde). Raiz da hierarquia | `color`, `archived` |
| **Projeto** | Agrupa objetivos de um setor | `sector`, `status` (`active/paused/done/abandoned`), `target_date` |
| **Objetivo** | Meta intermediária (os "goals") | `sector`, `project`, `parent_goal`, `horizon` (`quarter/year/multi_year`), `status` |
| **Missão** | Unidade de trabalho focável e colhível | `importance` e `difficulty` (1–5), `status` (`inbox/done`), `harvested`, `focus_minutes`, `xp_gained`, `due_date`, `parent_mission` |
| **Hábito** | Ação recorrente com streak | `frequency` (`daily/weekly/monthly/custom`), `custom_days`, `current_streak`, `best_streak`, `last_completed_at`, `active` |
| **Lembrete** | Aviso por horário ou data | `frequency` (inclui `once`), `time_of_day`, `due_at`, `last_acked_at`, `active` |
| **Anotação** | Nota livre em card colorido | `category`, `bg_color`, `sort_order` |

Convenções do modelo: o nome do arquivo é o nome da entidade; todo item tem `id`
(uuid) estável; os vínculos hierárquicos são wikilinks; os campos de dados ficam
em inglês e o discriminador `tipo` em português.

---

## 4. Foco, XP e peso

### Fórmulas

```
XP da sessão = round(minutos × importância × dificuldade / 10)
Peso         = importância × dificuldade          (1 a 25)
Score        = focus_minutes × importância × dificuldade
```

O **peso** define o tier de cor da missão (faixas 1–4, 5–9, 10–14, 15–19 e 20–25,
de "Trivial" a "Épico"). O **score** alimenta o resumo por setor.

### Regras do foco

1. **Exclusividade.** Só existe uma sessão de foco por vez. Iniciar outra
   encerra e credita a anterior.
2. **O timer nunca é um contador em memória.** A tela sempre calcula
   `agora − started_at`. Por isso o foco sobrevive a recarregar a página.
3. **Dois modos.** Cronômetro (conta para cima) e pomodoro (regressivo, com
   presets de 15, 25, 45 e 60 minutos, ou valor livre de 1 a 480).
4. **XP previsto** na barra de foco = `minutos decorridos × imp × dif / 10`.

### Quando o XP entra no total

Esta é a regra menos óbvia do sistema: a fórmula é sempre a mesma, o que muda é
**quando** o XP chega ao `total_xp`.

| Tipo de foco | Ao parar o foco | Quando o XP entra no total |
|---|---|---|
| **Missão** | Minutos e XP **acumulam na nota** | Só na **colheita** |
| **Hábito** | Minutos acumulam na nota | **Imediatamente** (auto-harvest) |
| **Multi-missão** | Cria uma nota de missão já concluída e colhida | **Imediatamente** |

- **Colher** (`harvest`) marca a missão como `done` e `harvested`, transfere o
  `xp_gained` acumulado para o total e é **idempotente**: colher de novo não
  credita duas vezes.
- **Cancelar** (`focus cancel`) zera o foco **sem creditar XP**.

### Sessão multi-missão

Uma sessão de foco com uma lista de **mini-missões** (adicionar, marcar e remover
durante a sessão). Ao concluir com **1 minuto ou mais**, vira uma única missão
consolidada, com o corpo listando as mini-missões. Com **menos de 1 minuto** é
descartada, sem nota e sem XP.

---

## 5. Hábitos e streak

Completar um hábito é **separado** de focar nele: completar marca
`last_completed_at = hoje` e recalcula o streak.

| Frequência | Regra para o streak subir |
|---|---|
| `daily` | A última conclusão foi **ontem** → `+1`; senão volta a `1` |
| `weekly` e `custom` | Intervalo de até **7 dias** → `+1`; senão `1` |
| `monthly` | Intervalo de até **31 dias** → `+1`; senão `1` |
| Sem conclusão anterior | `1` |
| Já concluído hoje | Mantém e responde `already` |

`best_streak` guarda o recorde. Desfazer a conclusão de hoje (`uncomplete`)
decrementa o streak e remove o evento do dia, em regime de melhor esforço.

O **nível** (`level`) era **estático**: não havia cálculo de progressão, apenas o
campo, fiel ao app original.

---

## 6. Eventos e heatmaps

Todo fato relevante vira uma linha em um log **imutável e só de acréscimo**.

| Tipo de evento | Quando nasce |
|---|---|
| `focus_session` | Ao parar um foco |
| `xp_event` | Quando XP entra no total |
| `habit_complete` | Ao completar um hábito |
| `reminder_ack` | Ao confirmar um lembrete |

Dois heatmaps leem esse log: **foco por dia** (minutos) e **conclusões de hábito
por dia** (contagem). A escala de cor é **relativa ao máximo do período** exibido,
com células de intensidade por faixa percentual.

O **resumo por setor** soma foco e XP acumulados por setor, mais o total geral.

---

## 7. Lembretes e alarme

Cada lembrete tem frequência, horário e, se for único, uma data (`due_at`). A tela
verifica periodicamente quais venceram e, para os vencidos:

1. Só dispara se **ainda não foi confirmado hoje** (`last_acked_at` diferente de hoje).
2. Respeita uma **tolerância de 2 horas**. Dentro dela, fala "lembrete: …" ou
   "lembrete atrasado: …" (quando o atraso passa de 1 minuto). Depois dela, fica só
   o destaque visual, sem fala, para não repetir alarme velho para sempre.
3. Nunca dispara duas vezes no mesmo dia para o mesmo lembrete.

**Armadilha conhecida:** "hoje" deve ser sempre a **data local**
(`getFullYear/getMonth/getDate`), nunca `toISOString().slice(0,10)`. Em UTC o dia
vira antes da meia-noite no Brasil, e um lembrete confirmado à noite voltaria a tocar.

Os botões de ação do app davam feedback **visual e silencioso**. O alarme era a
única fala da página.

---

## 8. As telas

A página operacional tinha uma **barra de foco fixa no topo** (timer grande,
entidade focada, XP previsto, iniciar multi-missão, concluir, concluir com tempo
manual, cancelar) e seis abas:

1. **Visão Geral:** resumo do dia (XP e nível, missões de maior peso, hábitos de
   hoje, lembretes vencidos).
2. **Missões:** agrupadas por setor, ordenadas por peso, com focar e colher.
3. **Hábitos:** streak, feito-hoje, focar, completar e desfazer.
4. **Multi-missão:** modo, presets de pomodoro, mini-missões, importância e dificuldade.
5. **Cartografia:** árvore Setor → Projeto → Objetivo → Missão, órfãos, criação de
   entidades e os dois heatmaps.
6. **Lembretes e Anotações:** confirmação, criação, cards coloridos.

A tela atualizava por polling a cada 3 segundos e depois de cada ação.

---

## 9. Princípios de arquitetura que valem para a reconstrução

Estas decisões nasceram de problemas reais e são as mais reaproveitáveis:

- **Escritor único.** Um só módulo grava estado e notas, sob **lockfile** que
  serializa escritas concorrentes (várias abas, botões e o assistente por voz).
  Todo o resto só lê ou chama esse módulo.
- **Armazenamento híbrido.** Entidades conceituais (as sete acima) como **notas
  Markdown com frontmatter**, para grafo, backlinks e edição manual. Estado e
  volume (perfil, foco corrente e log de eventos) como **JSON e JSONL**.
- **Regras puras separadas.** XP, peso, streak e calendário em funções puras, sem
  dependência de interface ou banco, testáveis isoladamente.
- **Operável por linguagem natural.** O assistente de voz aciona o mesmo módulo
  escritor, nunca editando frontmatter ou estado à mão.
- **O Obsidian como painel de leitura**, não de escrita.

### O que o app original tinha e a versão do Hub não

Itens da seção 1 sem equivalente nas seções 3 a 8, a decidir se entram na
reconstrução: metas por prazo com marcos, metas por direção com tendência, revisão
diária, energia, conquistas, recompensas de streak, sync multi-dispositivo, modelo
freemium e a classificação por IA.

---

## Fontes

- `docs/forestos.md`: integração com o Hub (histórico).
- `docs/historico/forestos-vault/ForestOS - Documentação Completa.md`: regras de
  negócio e contrato de dados.
- `docs/historico/forestos-vault/Modelo de Dados ForestOS.md`: frontmatter das entidades.
- `docs/prd.md` e `docs/_dev-loop-archive/`: PRDs do redesign e da migração.
- Vault Obsidian, `_agentes/voice-hub.md` (17/08/2026): resumo do app original
  recuperado da memória.
