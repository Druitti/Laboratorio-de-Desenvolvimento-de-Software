# Lab03S02 — Santiago — rotulação independente (#47)

Responsável pela avaliação pessoal: Gabriel Santiago (`gabsant07`).
Janela: `[2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z)`.

## Situação em 22/10/2026

A issue **não está concluída**. Na inspeção do checkout, não foram encontrados
`lab03/data/final_selection/eligible.csv`, `lab03/data/runs_evidence.json` ou
`lab03/data/gold_standard/manifest.json`. A amostra compartilhada de #45 e o
formulário individual real de Santiago ainda precisam ser disponibilizados.
Não foram produzidos rótulos, avaliação pessoal ou consenso nesta inspeção.

O suporte automatizado já existe em `lab03.validation`, com instruções em
[Ferreira S02](ferreira-s02.md). Não sortear outra amostra apenas para Santiago:
os três integrantes devem avaliar exatamente os mesmos itens congelados por #45.

## Execução pessoal quando #45 estiver disponível

1. Receber o manifesto e somente o formulário vazio `gabsant07.csv` da mesma
   execução de #45. Conferir 60 repositórios e 300 releases: o formulário contém
   420 linhas, sendo 60 de `project_type`, 60 de `real_delivery` e 300 de
   `corrective`, com IDs e links. Preservar o manifesto de origem.
2. Guardar a avaliação em local privado até os três integrantes confirmarem
   conclusão. Não consultar formulários preenchidos dos colegas, consenso ou
   previsões da heurística antes de concluir a avaliação independente.
3. Preencher pessoalmente somente `label` e `notes`. Ler documentação para tipo
   e entrega real; ler notas e commits de cada release para julgar correção.
   Registrar em `notes` a justificativa e os links adicionais consultados.
   Não inferir rótulos de ausência de evidência nem delegar o julgamento à IA.
4. Usar `library_framework`, `application_service`, `cli` ou `other` para tipo;
   `yes`, `no` ou `uncertain` para entrega; `yes` ou `no` para corretiva.
   Registrar dúvidas nas notas, conforme o protocolo de #45.
5. Depois da conclusão independente dos três integrantes, publicar o arquivo
   individual sem copiar o consenso, em commit referenciando `#47`. Preservar
   os campos de identidade, dimensão e URL gerados por #45.
6. Participar da discussão dos desacordos. Justificativas e confirmação dos três
   integrantes pertencem ao fluxo de consenso de #45; um resultado automático
   por maioria não comprova que essa discussão ocorreu.

## Evidências necessárias para concluir #47

- Manifesto real de #45 com 60 repositórios e cinco releases por repositório.
- `gabsant07.csv` completo, avaliado pessoalmente e vinculado a esse manifesto,
  com IDs, links e commit referenciando `#47`.
- Três avaliações independentes concluídas e registro da discussão efetiva dos
  desacordos, com justificativas do consenso.

Uma implementação ou teste com fixtures sintéticas não substitui essas evidências.
