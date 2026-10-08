# Evidência da entrega individual — Ferreira (#41)

Janela histórica configurada: **01/01/2025 inclusivo a 01/01/2026 exclusivo**, UTC.
Metadados obtidos pela API REST do GitHub em 08/10/2026, entre 14:57 e 15:03 UTC.

| Etapa | Repositórios |
|---|---:|
| Examinados, com IDs distintos | 107 |
| Excluídos por ausência de workflows | 7 |
| Candidatos aguardando coletores históricos | 100 |
| Elegibilidade histórica comprovada nesta entrega | 0 |

Os arquivos estão em [lab03/data/selection](../../lab03/data/selection).
Dos 100 candidatos, 99 têm contribuidores medidos; `torvalds/linux` tem o campo
vazio porque a API recusa listar contribuidores em históricos muito grandes.
Os sete excluídos não tiveram contribuidores consultados.

A introdução e as hipóteses foram registradas no commit `b155e4c`, antes da
coleta. O commit `520bf64` registra o tratamento da limitação de contribuidores.
As interrupções foram retomadas pelo checkpoint, preservando os metadados
concluídos. Após alcançar 100 candidatos, uma execução com transporte que rejeita
qualquer chamada confirmou a retomada sem rede. Também foram verificados IDs únicos.

Validação: **30 testes passaram; cobertura do seletor de 91,41%**. O
[GitHub Actions do código](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/actions/runs/37797149453)
passou. Os testes de métricas dos outros componentes continuam a cargo de seus responsáveis.

Esta entrega conclui a seleção individual, não a coleta integrada da S01.
Santiago (#42) deve fornecer releases/commits e Tavares (#43), runs e transporte
compartilhado. Só então o finalizador poderá comprovar os limites de 5 releases
e 50 runs válidos por repositório. Se os filtros reduzirem a amostra abaixo de
100, será necessário ampliar candidatos e repetir a coleta incremental.

Estrelas, contribuidores, linguagem, branch padrão e presença de Actions são
metadados atuais, não snapshots de 2025. Não há resultados DORA ou análise
estatística nesta entrega; os vieses da busca por popularidade estão descritos
no [README](../../lab03/README.md).
