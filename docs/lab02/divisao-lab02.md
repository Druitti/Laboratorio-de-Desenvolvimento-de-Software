# Lab02 — Divisão do trio

**Repositório:** https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software  
**Project:** https://github.com/users/Druitti/projects/5  

| Papel | Integrante | GitHub | Label |
|---|---|---|---|
| A | Gabriel Ferreira Amaral | `Druitti` | `integrante-Ferreira` |
| B | Gabriel Santiago | `gabsant07` | `Integrante-Santiago` |
| C | Gabriel Tavares | `Tavaresds1` | `Integrante-Tavares` |

Em **toda sprint**, cada integrante deve ser Assignee de ≥1 Issue com **artefato commitado** (código/notebook/gráfico/trial) referenciando `#N` no commit.

---

## Lab02S01 — Desenho + preparação (5 pts)

| Integrante | Issue | Entrega |
|---|---|---|
| **Ferreira** | **#12** | Desenho do experimento (Passo 1) + 6 katas Python com testes |
| **Santiago** | **#13** | Script de cronometragem / registro de trials (CSV) |
| **Tavares** | **#14** | Ambiente documentado + script Radon (métricas estáticas) |

Decisões fixas do grupo (S01):
- Linguagem: **Python 3**
- Métricas estáticas: **Radon** (+ LOC; duplicação com ferramenta a definir pelo Tavares)
- Assistente de IA (único): **ChatGPT (versão gratuita / web)** — mesmo em todos os trials
- Time-box: **35 min** por trial
- Desenho: **crossover within-subject** contrabalanceado

---

## Lab02S02 — Execução (5 pts)

Issue guarda-chuva: **#15**

Cada um resolve **os 6 katas**: 3 com IA e 3 sem, ordem contrabalanceada.

Sugestão de ordem (evitar mesmo padrão para os três):

| Integrante | Com IA (3) | Sem IA (3) | Ordem sugerida |
|---|---|---|---|
| Ferreira | K1, K2, K3 | K4, K5, K6 | IA → sem IA |
| Santiago | K4, K5, K6 | K1, K2, K3 | sem IA → IA |
| Tavares | K1, K3, K5 | K2, K4, K6 | intercalado |

Cada trial = **1 Issue** no board (Assignee = quem executou), com tempo, testes e métricas anexados/CSV.

---

## Lab02S03 — Análise + dashboard (5 pts)

Issue guarda-chuva: **#16**

| Integrante | Foco |
|---|---|
| Ferreira | Testes estatísticos Wilcoxon RQ1/RQ2 |
| Santiago | Análise RQ3 (métricas estáticas) |
| Tavares | Dashboard Pandas/Matplotlib/Seaborn |

---

## Relatório Final (5 pts)

Elaboração conjunta do documento (template da disciplina); Assignee principal a definir na sprint do relatório. Link repo/Project obrigatório.
