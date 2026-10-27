# TAREFA: Redesign visual + UX da página /forestos

Contrato fechado com o usuário em grilling (2026-07-15). Implementar EXATAMENTE estas decisões, sem re-decidir.

## Contexto

A página ForestOS (`forestos.html`, servida em `GET /forestos` pelo `server.py`, porta 8765) foi entregue no ciclo anterior e está **100% funcional** — mas o usuário considera o design "muito feio e simplista demais". Este ciclo é um **redesign visual + UX**; a lógica de dados/ações NÃO muda.

Repo: `C:\Users\Meu Computador\Desktop\core-voice-hub-master\core-voice-hub-master\` (git, branch `feature/forestos-integration` — continuar nela, commits por slice).

**O que existe hoje e DEVE continuar funcionando (contrato funcional intocável):**
- Dados: polling `GET /forestos/state` a cada 3s + refresh imediato pós-ação; ações via `POST /forestos/action {cmd, args}` (whitelist no server.py).
- Barra de foco viva: timer client-side recalculado de `started_at` a cada 1s; cronômetro e pomodoro regressivo; XP previsto; iniciar/concluir/concluir-com-tempo-manual/cancelar.
- Missões ativas por setor ordenadas por peso com tier de cor (▶ focar, 🌾 colher, ➕ criar).
- Hábitos com streak/feito-hoje (▶, ✅, ↩, ➕).
- Sessão multi-missão (🎯: modo, presets pomodoro 15/25/45/60+custom, mini-missões add/toggle/remove/reorder, imp/dif 1–5).
- Cartografia (árvore Setor→Projeto→Objetivo→Missão + órfãos, criar entidades).
- Heatmaps de foco e de hábitos (grade mensal, escala verde).
- Resumo/perfil (XP total, nível, foco por setor).
- Lembretes (✔ ack, ➕ criar, vencidos destacados) + **alarme local** (checagem client-side de `time_of_day`/`frequency`/`custom_days`/`due_at`; earcon + `POST /speak`; tolerância 2h "lembrete atrasado"; `last_acked_at != hoje`). A lógica do alarme NÃO muda — só a apresentação visual.
- Botões = feedback visual **silencioso** (sem voz).
- Link de ida/volta com o Hub (`index.html` tem link 🌲 → `/forestos`; a página tem volta → `/`). `index.html` fica INTOCADO.

## Decisões do grilling (contrato)

1. **Estética = HUD C.O.R.E.** A página deve parecer um módulo do mesmo sistema do Hub (`index.html`). Reusar os design tokens do `index.html` (ler o `<style>` dele como fonte de verdade):
   - Paleta warm-dark: `--bg:#14120c`, `--bg2:#1c1913`, texto paper `--ink:#ECE4D4` / `--ink-bright:#FBF9F5` / `--ink-dim:#9A9079` / `--ink-faint:#645C4B`, linhas `--line:#332e22`, painel `rgba(28,25,18,0.66)`.
   - Acentos: honey `--accent:#B88A3F` / `--amber:#E8B658`, sage `--teal:#6FA89C`, verde `--green:#7FC4A6`, danger `--err:#C45656`.
   - Tipografia: `--mono: "JetBrains Mono", ...` (base) + `--display: "Space Grotesk", ...` (títulos/números).
   - Linguagem visual: painéis com canto chanfrado (`--chamf:11px`, técnica de clip-path/borda que o index.html usa), títulos `h3` com barra accent + glow, scanlines/vinheta de fundo, dots de status com glow, letter-spacing largo em rótulos uppercase, `tabular-nums` em números.
   - O verde/sage pode ter presença maior que no Hub (identidade "floresta" do ForestOS), mas dentro da mesma família de tokens.
2. **Escopo = visual + UX.** Pode reorganizar completamente layout, hierarquia e navegação da página. NÃO pode: mudar endpoints, payloads, whitelist, regras de negócio, nem a semântica das ações.
3. **Layout = dashboard + abas:**
   - **Barra de foco fixa no topo** (sempre visível, em qualquer aba) — é o coração da página: timer grande (fonte display), entidade focada, XP previsto, controles. Estado vazio elegante quando sem foco.
   - **Aba padrão "Visão Geral"**: resumo do dia — perfil/XP/nível, missões de maior peso, hábitos de hoje, lembretes vencidos/próximos.
   - Demais seções organizadas em abas/segmentos (agrupamento exato a critério do Planejador; ex.: Missões, Hábitos, Cartografia, Heatmaps, Lembretes+Anotações). Navegação por abas client-side (sem reload), estado da aba ativa preservado entre pollings.
4. **CDN liberado.** Pode puxar Google Fonts (JetBrains Mono, Space Grotesk — o index.html já as usa), ícones e libs pequenas via CDN. Regra: a página deve **degradar graciosamente offline** (font stack de fallback; nenhuma funcionalidade de dados/ações pode depender de CDN).

## Qualidade esperada do design

- Nível "produto polido", não protótipo: espaçamento consistente (escala 4/8px), hierarquia tipográfica clara, microinterações (hover/active/focus states, transições curtas), skeleton/empty states desenhados, tiers de missão com cor+glow coerentes com a paleta, heatmap bonito (células arredondadas, tooltip com data/minutos), feedback visual de ação (botão pulsa/confirma) silencioso.
- Responsivo: usável em desktop (grid multi-coluna) e estreito (colunas empilham); sem scroll horizontal.
- Acessível o básico: contraste legível, `:focus-visible`, botões com `title`/aria-label.

## Restrições

- NÃO tocar: `server.py` (exceto se algum teste de estático precisar de ajuste trivial), `forestos/` (CLI/engine), `index.html`, nada de Finanças, nada do vault.
- `forestos.html` continua **um arquivo próprio e self-contained** (CSS/JS inline), salvo fonts/ícones via CDN.
- Testes existentes DEVEM continuar verdes: `python -m pytest` na raiz do repo (usar `./.venv/Scripts/python.exe`) e `node --test forestos/test/` — se `test_frontend_static.py` (ou similar) assertar sobre conteúdo do forestos.html, atualizar as asserções junto com o redesign (testar o novo, não afrouxar).
- Smoke test obrigatório no final: `GET /forestos` responde 200 e o HTML contém os hooks JS das ações (ids/handlers que chamam `/forestos/state` e `/forestos/action`).
- `prd.md` e `issues.md`: escrever NO REPO voice-hub, em `docs/` (o repo foi reorganizado: docs do dev-loop em `docs/`, suíte pytest em `tests/`). Os do ciclo anterior já foram arquivados em `docs/_dev-loop-archive/`.
- Fatiar em vertical slices; sugestão: (1) fundação visual — tokens/reset/fonts/painéis chanfrados + shell dashboard+abas com conteúdo atual realocado, (2) barra de foco topo + Visão Geral, (3) abas de conteúdo (missões/hábitos/multi), (4) cartografia + heatmaps, (5) lembretes+anotações + polimento/microinterações + testes atualizados.
- Git: commits por slice na branch `feature/forestos-integration`.
