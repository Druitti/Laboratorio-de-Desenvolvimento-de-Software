# Lab03S02 — Ferreira (#45, #46, #51)

## Situação da entrega

Em 15/10/2026, após `git pull --ff-only origin main`, a base remota estava no
commit `da12b23`. Há coletores da S01, mas não há `final_selection/eligible.csv`,
`runs_evidence.json`, amostra final de ≥300 elegíveis ou rótulos humanos no
repositório. A issue #50 está aberta. Não foi realizado sorteio real nem foram
calculados kappa ou consenso reais com os candidatos da S01.

O módulo `lab03.validation` implementa a parte automatizável de #45, prepara os
formulários de #46–#48 e exige os três arquivos completos antes da análise.
O texto de metodologia está em [relatorio/lab03/metodologia.md](../../relatorio/lab03/metodologia.md).
As issues permanecem abertas até seus critérios empíricos serem atendidos.

## Entradas de Tavares (#50) e Santiago (#42)

- `eligible.csv`: saída do finalizador, com `repository`, `default_branch` e
  `selection_status=eligible`, sem duplicatas, pelo menos 300 linhas.
- `releases_evidence.json` e `runs_evidence.json`: envelopes do contrato vigente,
  com janela igual à configuração, coleta completa, branch consistente e
  contagens mínimas de 5 releases e 50 runs válidos para cada repositório.
- `raw/OWNER/REPO/releases.json`: formato produzido por `lab03.releases`, com
  coleta completa, releases estáveis na janela e prova de ancestralidade na
  branch padrão. Os 60 sorteados precisam dessas evidências brutas.

O código confere as contagens declaradas; a comprovação de runs brutos continua
sob responsabilidade do coletor. O manifesto registra SHA-256 das entradas
utilizadas, permitindo identificar exatamente a versão congelada. Não basta
renomear `candidates.csv` para `eligible.csv`.

## Execução

Na raiz do repositório, após instalar `lab03/requirements.txt`:

```bash
python -m lab03.validation prepare \
  --eligible lab03/data/final_selection/eligible.csv \
  --data lab03/data --config lab03/config.json --seed 42 \
  --out lab03/data/gold_standard
```

O sorteio usa listas ordenadas por nome/ID e `random.Random(42).sample`, sem
reposição: 60 repositórios e 5 releases estáveis por repositório. O manifesto
versionado é a referência definitiva da amostra; registrar também a versão de
Python na execução real. A ordem das linhas do CSV de origem não muda o sorteio.
São gerados 420 itens por avaliador: 60 tipos, 60 avaliações de entrega real e
300 avaliações de releases corretivas. Os arquivos `Druitti.csv`, `gabsant07.csv`
e `Tavaresds1.csv` começam com rótulos vazios e não contêm previsões da heurística.

Cada pessoa recebe somente seu formulário e os links de evidência. Não abrir
arquivos preenchidos dos colegas nem executar/consultar previsões antes de
terminar a avaliação individual. Guardar os formulários preenchidos fora do
repositório compartilhado até todos confirmarem conclusão; depois cada
integrante commita seu arquivo referenciando sua issue (#46, #47 ou #48).

### Rótulos permitidos

| Dimensão | Valores |
|---|---|
| `project_type` | `library_framework`, `application_service`, `cli`, `other` |
| `real_delivery` | `yes`, `no`, `uncertain` |
| `corrective` | `yes`, `no` |

Editar apenas `label` e `notes`. Ler README/documentação para tipo e entrega;
ler as notas da release e a lista de commits para avaliar se o objetivo principal
é corrigir defeito recente. Os links nas notas e as comparações do coletor podem
servir como evidência, sem consultar a saída da heurística de #49. Dúvidas sobre
releases corretivas devem ser registradas em `notes`, com julgamento pessoal
sim/não; ausência de evidência não deve ser preenchida automaticamente como não.

Depois de receber os três arquivos completos:

```bash
python -m lab03.validation analyze \
  --manifest lab03/data/gold_standard/manifest.json \
  --labels lab03/data/gold_standard --out lab03/data/agreement
```

`agreement.json` contém Fleiss nominal por dimensão, n e hashes das entradas.
O cálculo usa `aggregate_raters` e `fleiss_kappa` do statsmodels. Categoria
global única torna o kappa indefinido (`null`), mesmo com unanimidade: não se
substitui esse caso por 1. Não são imputados rótulos faltantes. `uncertain` é
uma categoria válida de entrega, não um valor ausente.

## Consenso após a análise

`consensus_review.csv` preserva os três votos e uma sugestão por maioria; empate
fica sem sugestão. **Sugestão não é consenso**. Os três discutem todo desacordo,
adotando maioria como regra inicial e registrando justificativa para a decisão
final, inclusive mudanças motivadas por nova evidência. No empate 1–1–1, a
decisão é tomada em reunião. Preencher `label`, `rationale` e
`confirmed_by=Druitti;gabsant07;Tavaresds1` somente após confirmação dos três.
A ferramenta valida essa declaração; não autentica participação em reunião.

```bash
python -m lab03.validation consensus \
  --manifest lab03/data/gold_standard/manifest.json \
  --labels lab03/data/gold_standard \
  --decisions lab03/data/agreement/consensus_review.csv \
  --out lab03/data/consensus
```

Unanimidades são preservadas. Desacordos sem justificativa/confirmação impedem
exportação. `consensus.csv` tem uma linha por item, com dimensão, identificação,
link, rótulo e justificativa; `provenance.json` registra hashes. O consenso de
`corrective` é a referência para Santiago avaliar a heurística na #49. Não há
cálculo de precisão/recall/F1 neste módulo, pois essa tarefa pertence a ele.

Nenhum comando sobrescreve pasta existente, rótulos originais ou resultados
anteriores. Para uma nova execução, usar outra pasta de saída. Os exemplos
de teste são sintéticos e nunca devem entrar no artigo como dados empíricos.

## Testes

```bash
python -m pytest lab03/tests/test_validation.py \
  --cov=lab03.validation --cov-report=term-missing --cov-fail-under=80
```

Incluem sorteio reproduzível e cego, elegibilidade/branches/janelas, contagens,
links, rótulos ausentes/duplicados/alterados, kappa com resultados calculados
à mão, caso degenerado, consenso com desacordo e preservação dos originais.

## Pendências para encerrar suas issues

- **#45:** receber a amostra de #50, executar sorteio, receber três rotulações,
  publicar concordância e consenso efetivamente discutido.
- **#46:** Ferreira preencher pessoalmente seu formulário e participar do consenso.
- **#51:** inserir funil final, dados de validação e versões/resultados da heurística;
  integrar a metodologia ao artigo SBC e revisar com os colegas.
