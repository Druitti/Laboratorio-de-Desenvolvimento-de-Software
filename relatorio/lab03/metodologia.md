# Metodologia — Lab03S02

**Estado editorial:** texto-base para a seção do artigo SBC, limitado a 10 páginas
no total. O protocolo está definido; a amostra final e a validação manual ainda
não foram entregues. As etapas futuras são descritas como protocolo, não como
experimentos já realizados. Substituir o quadro de pendências ao concluir #45,
#49 e #50 e integrar esta seção à fonte SBC do artigo.

## Fonte, janela e seleção

O estudo utiliza dados públicos de repositórios GitHub coletados por scripts
próprios via API REST. A janela de observação compreende o intervalo UTC
`[2025-01-01, 2026-01-01)`, equivalente a 365 dias. Eventos no instante final
ficam excluídos. A análise considera apenas a branch padrão de cada repositório.

A seleção começa por projetos com mais de 1.000 estrelas, excluindo forks e
arquivados por decisão de amostragem do grupo. A busca prioriza popularidade;
portanto, a amostra não é aleatória em relação à população de projetos GitHub.
Ausência de workflows elimina o candidato antes das consultas mais custosas.
A elegibilidade exige ao menos cinco releases principais e cinquenta runs
válidos na janela. A S02 requer pelo menos 300 repositórios após esses filtros.
A ampliação e o particionamento das buscas são responsabilidade da coleta
completa (#50), respeitando o teto de resultados da API.

Na seleção inicial da S01 foram examinados 107 repositórios, sete excluídos por
ausência de Actions e cem mantidos como candidatos. Esses números não são o
funil final da S02 nem comprovam a elegibilidade histórica. Estrelas, linguagem,
contribuidores e branch são metadados do momento da coleta; a idade é calculada
até o fim da janela. Contagem de contribuidores indisponível permanece ausente,
sem substituição por zero.

## Definições operacionais e métricas

Releases publicadas, não draft e não prerelease, relacionadas à branch padrão,
representam entregas na definição principal. A frequência será o número dessas
releases dividido por `365/7` semanas. Pré-releases e tags são preservadas para
a análise de sensibilidade. Releases não equivalem necessariamente a deploys
em produção; essa adequação será examinada na validação humana.

O lead time, em horas, utiliza `commit.author.date` e `release.published_at`.
Para cada release, os commits são identificados pela comparação com a anterior,
mesmo quando esta é anterior à janela. A variante por release usa seu commit
mais antigo e agrega as releases pela mediana; a variante por commit agrega
todos os tempos individuais pela mediana. Releases sem antecessora ou sem
comparação utilizável não recebem tempo artificial; exclusões e motivos devem
ser contabilizados. Datas de autoria podem ser afetadas por rebases e squash.

São considerados runs disparados por `push` na branch padrão, criados dentro da
janela. `success` representa sucesso; `failure`, `timed_out` e `startup_failure`
representam falha. Demais conclusões ou conclusão vazia são ignoradas. CFR(a)
é a razão entre falhas e a soma de falhas e sucessos. Esse proxy mede falhas de
pipeline, não incidentes em produção.

CFR(b) considera falha uma release seguida em até sete dias por uma release
corretiva identificada pela heurística de #49. Releases dos últimos sete dias
da janela são censuradas e excluídas do denominador dessa variante. A regra
efetivamente implementada, suas versões e seu desempenho devem ser registrados
após a entrega de Santiago; nenhuma versão foi avaliada nesta seção preliminar.

Recuperação é medida por episódios dentro do mesmo workflow: primeira falha
após sucesso até `updated_at` da próxima execução bem-sucedida, subtraindo
`run_started_at` da primeira falha. Agregam-se os episódios pela mediana em horas.
Episódios sem recuperação na janela são contabilizados como censurados e sua
proporção é reportada por repositório. Para todas as métricas, resultados
descritivos usarão mediana e IQR, com tamanho da amostra válida e ausências.

## Validação manual e concordância

Após congelar a lista final de elegíveis, o script de Ferreira sorteará 60
repositórios sem reposição, com semente 42. De cada um serão sorteadas cinco
releases principais. Listas de repositórios e IDs de releases são ordenadas
antes de usar `random.Random(42).sample`; o manifesto registra os itens e os
hashes SHA-256 das fontes. Isso fixa a amostra independentemente da ordem das
linhas de entrada e permite identificar a versão dos dados utilizada.

Os três integrantes avaliarão independentemente: tipo do projeto
(biblioteca/framework, aplicação/serviço, CLI ou outro); se releases representam
entregas reais (sim, não ou incerto); e se cada uma das 300 releases sorteadas é
corretiva (sim ou não). Os formulários contêm links de evidência e não apresentam
previsões da heurística. As avaliações individuais serão concluídas antes de
compartilhar rótulos ou consultar previsões, com notas justificativas preservadas.

O kappa de Fleiss será calculado separadamente para as três dimensões, usando
`aggregate_raters` e `fleiss_kappa` do statsmodels. Os tamanhos previstos são 60,
60 e 300 itens, todos com três avaliadores. Serão rejeitados itens desalinhados,
duplicados, categorias inválidas ou rótulos ausentes. Uma única categoria global
torna o kappa indefinido e será reportada como tal. As 300 avaliações de releases
são agrupadas em 60 projetos; não constituem 300 repositórios independentes.

Após medir a concordância anterior ao consenso, os três discutirão divergências,
usando maioria como regra inicial e decidindo empates em reunião. Qualquer
desacordo exige rótulo final, justificativa e registro de confirmação dos três;
os votos originais são preservados. O consenso de releases corretivas será
fornecido à avaliação da heurística de Santiago, com precisão, recall e F1.
Se F1 for inferior a 0,70, a regra deverá ser refinada e reavaliada, documentando
cada versão. Reutilizar a amostra para refinamento e avaliação pode superestimar
o desempenho e deverá ser explicitado nas ameaças à validade.

## Reprodução e dados pendentes

O pipeline do grupo documenta execução por comando único, token em variável de
ambiente, paginação, cache, retomada e tratamento de rate limit. A validação é
uma etapa offline posterior à coleta, com comandos `prepare`, `analyze` e
`consensus`, documentados em `docs/lab03/ferreira-s02.md`. A análise não altera
os rótulos originais nem sobrescreve diretórios existentes. Fixtures sintéticas
verificam o código, mas não fornecem resultados científicos.

| Evidência necessária para a versão final desta seção | Responsável |
|---|---|
| Funil final, ≥300 elegíveis, datas de coleta e dicionário completo | Tavares, #50 |
| Manifesto real, três avaliações, Fleiss e consenso | Ferreira, #45; trio, #46–#48 |
| Regra corretiva e precisão/recall/F1 por versão | Santiago, #49 |
| Integração no artigo SBC e revisão da metodologia | Ferreira, #51 |

Repositório: https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software.
Quadro: https://github.com/users/Druitti/projects/5.
