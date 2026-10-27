---
tipo: referencia
status: ativo
area: aprendizado
criado: 2026-06-16
tags: [forestos, referencia, modelo-de-dados, obsidian]
---

# Modelo de Dados — ForestOS

> Contrato de **frontmatter** das entidades conceituais do ForestOS (cidadãos do
> segundo cérebro — vivem como **notas** em `forestos/`). O **estado** (perfil/XP, foco
> corrente, log de eventos) vive em `forestos/_state/profile.json` + `_state/events.jsonl`
> (SQLite aposentado para o ForestOS — migração one-shot em `voice-hub/forestos/migrate.js`).
> O domínio **Finanças** continua no SQLite (`db/central.db`, ver `db/schema.sql`) —
> não tocar. **Escritor único do ForestOS:** a CLI `voice-hub/forestos/cli.js`; o Obsidian
> é read-only. Porte fiel do schema Postgres do app original.

## Convenções

- **Nome/título da entidade = nome do arquivo** (`file.name`). Não duplicamos em frontmatter.
- **Campos de dados em inglês** = nomes idênticos ao schema original, para as libs
  puras (movidas para `voice-hub/forestos/lib/`) operarem sem tradução.
- **`tipo`** (PT) = discriminador da entidade para Dataview/Bases.
- **`id`** = uuid estável; é por ele que o **estado** referencia a nota:
  `_state/profile.json` (`focus.entity_id`, foco corrente) e `_state/events.jsonl`
  (`entity_id`). Antes da migração, esse papel era do SQLite (3 tabelas hoje
  aposentadas — migração one-shot em `voice-hub/forestos/migrate.js`).
- **Vínculos hierárquicos = wikilinks** (`sector: "[[Saúde]]"`) → grafo + backlinks.
- **Booleanos** = `true`/`false`; **datas** = `YYYY-MM-DD`; **timestamps** = ISO 8601.
- **Valores de `status`/`frequency`/etc.** seguem os enums do original (abaixo).

## Entidades

### `setor`
| campo | tipo | valores / notas |
|---|---|---|
| id | uuid | |
| tipo | `setor` | |
| color | text | hex, default `#a88a3d` |
| archived | bool | default `false` |
| created_at | date | |

### `projeto`
| campo | tipo | valores / notas |
|---|---|---|
| id | uuid | |
| tipo | `projeto` | |
| description | text | |
| sector | wikilink | → setor |
| status | text | `active` \| `paused` \| `done` \| `abandoned` |
| target_date | date | prazo |
| created_at | date | |

### `objetivo` (goals do ForestOS)
| campo | tipo | valores / notas |
|---|---|---|
| id | uuid | |
| tipo | `objetivo` | |
| description | text | |
| sector | wikilink | → setor |
| project | wikilink | → projeto |
| parent_goal | wikilink | → objetivo (sub-objetivo) |
| horizon | text | `quarter` \| `year` \| `multi_year` |
| status | text | `active` \| `paused` \| `done` \| `abandoned` |
| target_date | date | |
| created_at | date | |

### `missao`
| campo | tipo | valores / notas |
|---|---|---|
| id | uuid | referenciado por `_state/profile.json` (`focus.entity_id`) e `_state/events.jsonl` (`entity_id`) |
| tipo | `missao` | |
| description | text | |
| sector | wikilink | → setor |
| goal | wikilink | → objetivo |
| parent_mission | wikilink | → missao (sub-missão) |
| importance | int | 1–5 |
| difficulty | int | 1–5 |
| status | text | `inbox` \| `done` |
| harvested | bool | colhida? |
| focus_minutes | int | acumula durante o foco |
| xp_gained | int | acumula até a colheita |
| due_date | date | |
| created_at | date | |
| completed_at | date | |
| harvested_at | date | |
| sort_order | int | |

> **XP** = `round(focus_minutes × importance × difficulty / 10)` (idêntico ao original).

### `habito`
| campo | tipo | valores / notas |
|---|---|---|
| id | uuid | referenciado por `_state/profile.json` (`focus.entity_id`) e `_state/events.jsonl` (`entity_id`) |
| tipo | `habito` | |
| description | text | |
| sector | wikilink | → setor |
| goal | wikilink | → objetivo |
| project | wikilink | → projeto |
| frequency | text | `daily` \| `weekly` \| `monthly` \| `custom` |
| custom_days | list[int] | 0–6 (dom–sáb), quando `frequency: custom` |
| importance | int | 1–5 |
| difficulty | int | 1–5 |
| current_streak | int | |
| best_streak | int | |
| last_completed_at | date | |
| active | bool | default `true` |
| color | text | hex |
| focus_minutes | int | |
| xp_gained | int | |
| sort_order | int | |
| created_at | date | |

### `lembrete`
| campo | tipo | valores / notas |
|---|---|---|
| id | uuid | referenciado por `_state/events.jsonl` (`entity_id`) |
| tipo | `lembrete` | |
| message | text | |
| frequency | text | `daily` \| `weekly` \| `monthly` \| `custom` \| `once` |
| custom_days | list[int] | 0–6, quando `custom` |
| time_of_day | text | `HH:MM` |
| sector | wikilink | → setor |
| goal | wikilink | → objetivo |
| due_at | timestamp | |
| last_acked_at | date | |
| acknowledged | bool | |
| active | bool | default `true` |
| repeat | text | `none` (se `once`) senão = `frequency` |
| sort_order | int | |
| created_at | date | |

### `anotacao`
| campo | tipo | valores / notas |
|---|---|---|
| id | uuid | |
| tipo | `anotacao` | |
| category | wikilink | → categoria de anotação (opcional) |
| bg_color | text | hex; vazio = pergaminho padrão |
| sort_order | num | menor = topo |
| updated_at | timestamp | |

> Conteúdo da anotação = **corpo** da nota.

## Estado (NÃO é nota — vive em `forestos/_state/`)

- **`_state/profile.json`** — `{ total_xp, level, focus: {type, entity_id, started_at,
  mode, pomo_min, importance, difficulty, mini_missions[]}, updated_at }`. Sem campos
  `counter_*` (existiam no SQLite antigo; descartados na migração). `focus.type` é
  `"mission"|"habit"|"multi"|null` — mutuamente exclusivo (só um foco ativo por vez).
- **`_state/events.jsonl`** — log imutável, 1 JSON por linha (append-only): `id, type
  (habit_complete|xp_event|focus_session|reminder_ack), entity_type, entity_id,
  entity_title, focus_minutes, xp_gained, total_xp_after, streak_before, streak_after,
  data{}, occurred_at`. Sessões multi-missão não têm mais tabela própria — ao concluir
  (≥1min) viram direto 1 nota `missao` `done`+`harvested` (não um registro de estado à parte).

Escrita/leitura desse estado é **exclusiva** da CLI `voice-hub/forestos/cli.js`
(lockfile próprio serializa escritas). Detalhe da engine em
`[[ForestOS - Documentação Completa]]`.

## Relacionado
- [[ForestOS Index]]
- [[ForestOS e Finanças no Obsidian - Plano]]
