# Lab03S01 — divisão e critérios de entrega

Project v2: https://github.com/users/Druitti/projects/5

| Integrante | Issue | Entrega individual |
|---|---|---|
| Ferreira (`Druitti`) | #41 | Seleção, metadados, funil, testes do seletor, CI inicial e introdução com hipóteses |
| Santiago (`gabsant07`) | #42 | Releases, tags, comparações de commits, lead time nas duas variantes e testes |
| Tavares (`Tavaresds1`) | #43 | Transporte compartilhado com cache/rate limit, runs, CFR(a), recuperação e testes |

Somente a **S01** está em execução. Os componentes de #42 e #43 devem ser
implementados pelos respectivos integrantes. Cada commit deve citar sua issue.
O campo Sprint dos três cartões é `Lab03S01`. WIP máximo: dois cartões em Doing
em todo o quadro; o cartão antigo #16 também ocupa uma vaga enquanto estiver lá.

## Janela

Confirmada pelo responsável em 08/10/2026: início inclusivo **2025-01-01T00:00:00Z**,
fim exclusivo **2026-01-01T00:00:00Z**. São 365 dias, ou 365/7 semanas.
A configuração está em `lab03/config.json`. Datas de eventos fora desse intervalo
não entram no cálculo, exceto dados de contexto explicitamente previstos no enunciado
(por exemplo, a release anterior necessária ao lead time).

## Integração da sprint

1. #41 fornece candidatos com Actions e metadados; o arquivo não comprova elegibilidade.
2. #42 e #43 coletam os dados históricos e exportam as evidências conforme o contrato.
3. O finalizador de #41 aplica os limites de 5 releases e 50 runs válidos.
4. Se houver menos de 100 elegíveis, ampliar candidatos e repetir a coleta incremental.
5. Integrar em um único comando o pipeline completo, habilitar os testes dos módulos
   de métricas no CI e garantir sua cobertura de pelo menos 80%.

Concluir #41 não conclui a S01 inteira: a entrega do grupo exige 100 repositórios
**após** os filtros e todos os dados de releases, commits e runs. A introdução e
as hipóteses estão em `relatorio/lab03/introducao.md`; a diagramação do artigo
completo deve usar o template SBC, com limite de 10 páginas.
