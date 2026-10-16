# Lab03 — planejamento do trio até a entrega final

[GitHub Projects v2](https://github.com/users/Druitti/projects/5).
Fonte: enunciado «Mineração de Métricas DORA», especialmente seções 6–10.
Janela de todos os componentes: **01/01/2025 inclusivo a 01/01/2026 exclusivo (UTC)**.

## Responsabilidades por etapa

| Etapa | Ferreira (`Druitti`) | Santiago (`gabsant07`) | Tavares (`Tavaresds1`) |
|---|---|---|---|
| S01 | Seleção, metadados, funil, introdução/hipóteses | Releases/tags, commits e lead time | Runs, cache/rate limit, CFR(a), recuperação e integração dos 100 elegíveis |
| S02 | Sorteio da amostra-ouro, Fleiss, consenso e metodologia | Heurística corretiva, CFR(b), precisão/recall/F1 | Coleta de ≥300 elegíveis, CSV completo e dicionário |
| S03 | RQ01–04, classificação C1 e consolidação do artigo | RQ05–06: correlações, fatores, Holm e efeitos | RQ07: sensibilidade; RQ08 opcional |
| Final | Executar replicação; consolidar e entregar relatório final | Comparar resultados e abrir issues de divergências | Responder issues recebidas, corrigir e testar pipeline |

Na S02, **cada integrante rotula pessoalmente** os mesmos 60 repositórios e cinco
releases por repositório, em arquivo próprio, sem ver rótulos dos colegas ou
previsões da heurística. Só depois ocorrem concordância e consenso.

O relatório final tem apenas `Druitti` como responsável. Os três fornecem suas
análises e revisam ameaças à validade e artigo. Cada integrante precisa de
artefato de código e commits próprios em **cada** etapa, inclusive a final;
tarefas de escrita ou rotulação isoladas não substituem essa exigência.

## Ordem e critérios de passagem

1. **S01:** integrar #41–#43, comprovar 100 elegíveis, comando único, cache e
   retomada, rate limit, testes das métricas com cobertura ≥80% no CI e introdução.
   Os 100 candidatos já coletados não encerram a entrega do grupo.
2. **S02:** ampliar para ≥300 elegíveis e congelar a amostra; sortear a amostra-ouro
   e releases; realizar as três avaliações independentes; calcular Fleiss e
   consenso; avaliar/refinar a heurística (se F1<0,70); consolidar todas as
   variantes no CSV, dicionário e metodologia. Congelar a lista de repositórios
   precede a rotulação; fechar CFR(b) e CSV final vem após a validação.
3. **S03:** executar RQ01–07 a partir do dataset, com mediana/IQR, classificação,
   Spearman, testes de grupos, Holm, efeitos e sensibilidade; integrar resultados
   e discussão com gráficos legíveis. RQ08 é bônus opcional e não bloqueia a entrega.
4. **Final:** após indicação do outro grupo pelo professor, replicar 30 repositórios
   usando apenas seu README; comparar resultados e abrir issues com evidências.
   Adicionar ao Projects e responder as issues recebidas. Entregar artigo SBC
   revisado, fonte e PDF, com até 10 páginas, quatro categorias de ameaças à
   validade, relato de replicação e links do repositório/quadro.

## Uso do quadro

- S01 pendente em **To Do**; S02, S03 e `Lab03Final` planejadas em **Backlog**.
- WIP máximo de dois cartões em **Doing** no quadro inteiro; atualizar semanalmente.
- Cada issue tem um responsável, critérios de aceite e dependências. Commits
  citam a issue executada; o commit deste planejamento não conclui suas tarefas.
- Em 15/10/2026 foi iniciada também a parte de Ferreira na S02 (#45, #46 e #51).
  A execução real da validação depende da amostra final e das avaliações humanas;
  ver [entrega de Ferreira](ferreira-s02.md). As partes dos colegas seguem suas issues.
- Datas de entrega seguem o cronograma da disciplina; não foram inventados prazos.

## Issues

As issues abaixo são a referência para execução e atualização do quadro.

| Issue | Etapa | Responsável | Tarefa |
|---|---|---|---|
| [#41](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/41) | Lab03S01 | Druitti | Seleção, metadados e funil (concluída) |
| [#42](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/42) | Lab03S01 | gabsant07 | Releases, commits e lead time |
| [#43](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/43) | Lab03S01 | Tavaresds1 | Workflows, cache e métricas de CI |
| [#56](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/56) | Lab03Final | Druitti | Ferreira: executar replicação cruzada |
| [#57](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/57) | Lab03Final | gabsant07 | Santiago: comparar replicação e registrar divergências |
| [#58](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/58) | Lab03Final | Tavaresds1 | Tavares: responder replicador e corrigir pipeline |
| [#59](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/59) | Lab03Final | Druitti | Ferreira: relatório final SBC e revisão da entrega |
| [#44](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/44) | Lab03S01 | Tavaresds1 | Tavares: integrar pipeline e comprovar 100 elegíveis |
| [#45](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/45) | Lab03S02 | Druitti | Ferreira: amostra-ouro, Fleiss e consenso |
| [#46](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/46) | Lab03S02 | Druitti | Ferreira: rotulação independente da amostra-ouro |
| [#47](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/47) | Lab03S02 | gabsant07 | Santiago: rotulação independente da amostra-ouro |
| [#48](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/48) | Lab03S02 | Tavaresds1 | Tavares: rotulação independente da amostra-ouro |
| [#49](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/49) | Lab03S02 | gabsant07 | Santiago: CFR(b) e validação da heurística corretiva |
| [#50](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/50) | Lab03S02 | Tavaresds1 | Tavares: coleta de 300 elegíveis e dataset completo |
| [#51](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/51) | Lab03S02 | Druitti | Ferreira: metodologia do artigo |
| [#52](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/52) | Lab03S03 | Druitti | Ferreira: RQ01–04 e classificação DORA C1 |
| [#53](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/53) | Lab03S03 | gabsant07 | Santiago: RQ05–06, correlações e fatores |
| [#54](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/54) | Lab03S03 | Tavaresds1 | Tavares: RQ07 e sensibilidade das classificações |
| [#55](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/55) | Lab03S03 | Druitti | Ferreira: consolidar resultados e discussão no artigo |
| [#60](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/60) | Lab03S03 | Tavaresds1 | Tavares: RQ08 opcional |
