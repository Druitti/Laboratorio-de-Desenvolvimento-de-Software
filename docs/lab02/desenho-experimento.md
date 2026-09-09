# Lab02 — Desenho do Experimento (Passo 1)

Issue: **#12** · Responsável: Gabriel Ferreira Amaral (`Druitti`)

## Goal (GQM)

Analisar o uso de assistentes de IA generativa na resolução de tarefas de programação, comparando-o à codificação manual quanto a **tempo**, **defeitos (testes)** e **qualidade estrutural** do código, do ponto de vista do grupo, em katas de dificuldade equivalente resolvidos por estudantes sob condições controladas (crossover within-subject, time-boxed).

## Questions

- **RQ1** — O uso de assistente de IA reduz o tempo necessário para resolver uma tarefa de programação?
- **RQ2** — O uso de assistente de IA reduz a quantidade de defeitos (testes que falham) no código produzido?
- **RQ3** — O uso de assistente de IA altera a complexidade ciclomática ou a duplicação do código produzido?

---

## (A) Hipóteses

### RQ1 — Tempo
- **H0:** Não há diferença na mediana do *time-to-green* (ou tempo censurado) entre tratamento com IA e sem IA.
- **H1:** A mediana do *time-to-green* com IA é **menor** que sem IA.

### RQ2 — Defeitos
- **H0:** Não há diferença na taxa de sucesso (testes passando / total) ao final do time-box entre com IA e sem IA.
- **H1:** A taxa de sucesso com IA é **maior** que sem IA (menos defeitos relativos).

### RQ3 — Estrutura
- **H0:** Não há diferença na mediana da complexidade ciclomática média (e/ou % duplicação), controlando por LOC, entre com IA e sem IA.
- **H1:** Há diferença (bilateral): a IA pode aumentar verbosidade/LOC e alterar complexidade/duplicação.

---

## (B) Variáveis dependentes (métricas escolhidas)

| RQ | Métrica primária | Agregação | Observação |
|---|---|---|---|
| RQ1 | Time-to-green (segundos até 100% testes) | Mediana + IQR | Trial sem sucesso: **censurado em 35 min** (não descartar) |
| RQ2 | Taxa de sucesso = testes OK / total ao fim | Mediana + IQR | Complementar: nº absoluto de falhas |
| RQ3 | Complexidade ciclomática média (Radon `cc`) | Mediana + IQR | **LOC** obrigatória como controle; duplicação (ex. jscpd) se disponível; MI opcional |

Inferência (S03): teste de **Wilcoxon** pareado (within-subject).

## (C) Variável independente

Uso do assistente de IA: **sim** vs **não**.

## (D) Tratamentos

1. **Com IA:** ChatGPT (web, versão gratuita do grupo), permitido durante o trial.
2. **Sem IA:** IDE/editor apenas; proibido qualquer assistente generativo (Copilot, ChatGPT, etc.).

Mesmo assistente em **todos** os trials com IA do grupo.

## (E) Objetos experimentais

**6 katas** em Python, autorais do grupo (baixa indexação), dificuldade comparável, com testes `pytest`:

| ID | Kata | Pasta |
|---|---|---|
| K1 | Mesclar intervalos de agenda | `lab02/katas/k1_merge_intervals` |
| K2 | Achatar dicionário aninhado (chaves pontuadas) | `lab02/katas/k2_flatten_dict` |
| K3 | Contagem de erros em log por hora | `lab02/katas/k3_log_errors` |
| K4 | Maior sequência de vagas livres | `lab02/katas/k4_parking_slots` |
| K5 | Validar código de verificação local (checksum) | `lab02/katas/k5_local_checksum` |
| K6 | Pontuação simplificada de frames | `lab02/katas/k6_frame_score` |

## (F) Tipo de projeto

**Crossover / within-subject**, contrabalanceado entre integrantes (metade dos katas com IA, metade sem; ordens diferentes — ver `docs/lab02/divisao-lab02.md`).

## (G) Quantidade de medições

- 3 integrantes × 6 katas = **18 trials**
- Por tratamento: 9 trials com IA e 9 sem IA (3 por pessoa em cada tratamento)
- Time-box: **35 min** / trial

## (H) Ameaças à validade

| Ameaça | Mitigação |
|---|---|
| Aprendizado entre katas | Ordem contrabalanceada; katas distintos |
| Familiaridade prévia com IA | Mesmo assistente; instrução padronizada |
| Vazamento / memorização pelo modelo | Katas **autorais**, pouco indexados (não LeetCode clássico) |
| Fadiga / ordem | Contrabalanceamento entre integrantes |
| Contaminação sem IA | Proibir Copilot/chat; registrar violação como trial inválido |
| Time-box enviesando média | Usar mediana; censurar em 35 min sem descartar |

## Ambiente (resumo)

Detalhamento operacional fica na Issue **#14** (Tavares). Premissas S01: Python 3, `pytest`, Radon, cronômetro via script da Issue **#13** (Santiago).
