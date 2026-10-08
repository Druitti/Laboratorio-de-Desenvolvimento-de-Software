# Introdução do artigo Lab03

Responsável pela consolidação S01: Gabriel Ferreira Amaral (`Druitti`), issue #41.
Hipóteses formuladas antes da execução da coleta do Lab03. Texto-base para a seção
de introdução do artigo no template SBC; não contém resultados empíricos.

## Introdução

O desempenho de entrega de software envolve velocidade e estabilidade. As métricas
DORA descrevem essas dimensões por frequência de entrega, tempo entre mudança e
entrega, proporção de falhas e tempo de recuperação. Em repositórios públicos,
releases e execuções de CI permitem observar parte desse processo, mas não
comprovam deploys nem incidentes em produção. A interpretação depende, portanto,
da definição operacional e da qualidade das aproximações utilizadas.

Este estudo investigará repositórios populares que utilizam GitHub Actions, com
eventos observados entre 1º de janeiro de 2025 e 1º de janeiro de 2026 (fim exclusivo).
A inclusão exige pelo menos cinco releases principais e cinquenta execuções válidas
no default branch. Serão comparadas as definições obrigatórias do enunciado, com
estatística descritiva por mediana e IQR e validação humana em etapa posterior.
As hipóteses abaixo são expectativas anteriores à coleta, não conclusões.

## Hipóteses informais

- **RQ01:** esperamos maior concentração de frequências baixas de releases, com
  poucos projetos publicando diariamente, devido a ciclos de manutenção distintos.
- **RQ02:** esperamos lead time por release maior que por commit, pois um commit
  antigo pode elevar o máximo da release sem dominar a mediana de todos os commits.
  A hipótese será verificada, sem assumir que vale para todo repositório.
- **RQ03:** esperamos divergência entre CFR de pipeline e de entrega: uma falha de
  teste pode ocorrer antes de uma release, enquanto um defeito pode escapar de CI.
- **RQ04:** esperamos assimetria dos tempos de recuperação e episódios não encerrados
  até o fim da janela. Estes serão tratados como censurados, não descartados.
- **RQ05:** esperamos associação fraca entre frequência e CFR; entregas frequentes
  podem coexistir com estabilidade, e os dois proxies de CFR podem produzir sinais diferentes.
- **RQ06:** esperamos diferenças entre linguagens, quartis de estrelas e quartis de
  contribuidores, porque ecossistema e escala afetam práticas de entrega. Esses são
  fatores exploratórios; não inferiremos causalidade a partir das comparações.
- **RQ07:** esperamos mudanças de categoria DORA entre releases, pré-releases e tags,
  especialmente em projetos que publicam versões preliminares com frequência.

O estudo deverá distinguir características atuais dos repositórios de eventos
históricos da janela. Popularidade atual, exclusão de forks/arquivados e retenção
de histórico pelo GitHub podem limitar a representatividade. O objetivo é avaliar
tanto os valores das métricas quanto sua sensibilidade às definições adotadas.

## Referências de base

- Forsgren, N.; Humble, J.; Kim, G. *Accelerate*. IT Revolution, 2018.
- Enunciado Lab03, seções 3, 5, 7, 8 e 10, professor Danilo Maia.
- [Repositório](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software).
- [GitHub Projects v2](https://github.com/users/Druitti/projects/5).

O artigo completo em SBC, limitado a 10 páginas, será desenvolvido ao longo das
sprints; esta entrega fornece apenas a introdução e as hipóteses exigidas na S01.
