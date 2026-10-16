# Heuristica de releases corretivas e CFR(b)

## Estado desta entrega

A implementacao da heuristica e do CFR(b) esta em `corrective.py`; os testes
sinteticos estao em `tests/test_corrective.py`. A versao no codigo e `1.0.7`.
A infraestrutura de amostra-ouro e validacao humana esta em
`human_validation.py`, com fixtures sinteticas em
`tests/test_human_validation.py`.
Esta entrega nao produziu resultados de precisao, recall, F1, Fleiss ou CFR(b)
para os repositorios coletados. Esses resultados dependem da amostra-ouro e dos
rótulos humanos, que ainda nao existem neste checkout.

O checkout disponibilizado nao contem diretorio `.git`; por isso nao foi possivel
registrar ou verificar hash de commit para esta versao. O identificador
reproduzivel disponivel e `HEURISTIC_VERSION` no codigo.

O plano do grupo atribui a amostra-ouro e ao consenso a issue #45, a rotulagem de
Santiago a #47 e a heuristica/CFR(b) a #49. Issues #47 e #49 foram verificadas
no GitHub; [#47](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/47)
e [#49](https://github.com/Druitti/Laboratorio-de-Desenvolvimento-de-Software/issues/49)
continuam descritas como tarefas da S02. A selecao local registra 107 repositorios
examinados, 100 candidatos pendentes de coletores historicos e zero elegiveis no
funil registrado. Nao ha `runs_evidence.json`, lista congelada de 60 repositorios,
lista de 300 releases, nem arquivos individuais de avaliacao neste checkout.
Esses dados nao autorizam completar nem substituir a amostra.

## Sinais e regras da heuristica

`parse_semver` aceita `MAJOR.MINOR.PATCH`, prefixo `v` minusculo e os campos de
pre-release/build do SemVer 2.0.0. Tags fora da gramatica retornam ausencia de
interpretacao. A comparacao usa precedencia SemVer; metadados de build nao alteram
precedencia. Incrementos major, minor, patch, transicao de pre-release, downgrade
e ausencia de comparacao sao registrados separadamente. Uma mudanca PATCH
isolada nunca e evidencia suficiente para prever `yes`.

`classify_repository` usa apenas releases estaveis, nao draft, comprovadas no
branch padrao pelo coletor existente. Ordena o predecessor por `published_at` e
ID, nunca por ordenacao lexicografica de tags. Releases anteriores a janela podem
ser contexto para o predecessor; somente releases da janela sao marcadas
`in_window`. Commits relevantes sao lidos das comparacoes estaveis preservadas
no bruto de `releases.py`. Se `raw.complete` for falso, o adaptador nao produz
previsoes. Isso nao garante que toda comparacao de commits esteja disponivel:
`compare_404` pode permanecer em uma coleta completa. Nesse caso, o status da
comparacao fica registrado e a heuristica ainda pode usar titulo/notas; mensagens
de commits ausentes nao sao tratadas como evidencia negativa.

A evidencia textual e procurada no titulo, corpo das notas e mensagens de
commits. Sinais positivos reconhecem construcoes explicitas de hotfix, bug/issue/
regression fix, resolucao de defeito e revert. As expressoes sao regras de texto
em ingles, nao NLP nem prova semantica; negacoes conhecidas sao filtradas antes
de aceitar o sinal. Sinais de entrega de feature podem apoiar `no` somente com
incremento SemVer major/minor. Evidencia corretiva positiva prevalece em releases
mistas. Um incremento patch, texto ausente, texto sem sinal reconhecido ou
contexto contraditorio produz `uncertain`, nunca `no` por padrao.

Cada registro conserva `heuristic_version`, release anterior, versoes interpretadas,
tipo de incremento, status SemVer, previsao, motivo, trecho de evidencia e fontes
de texto. A versao atual e `1.0.7`; mudancas subsequentes devem receber nova
versao e manter resultados anteriores separados. O historico abaixo e declarado
pelo registro de desenvolvimento, mas nao pode ser verificado por commits neste
checkout sem `.git`.

| Versao | Alteracao tecnica | Avaliacao empirica |
|---|---|---|
| 1.0.0 | Primeira regra combinando SemVer e evidencias textuais | Nao executada |
| 1.0.1 | Downgrades explicitos, agregacao parcial e primeira filtragem de negacao | Nao executada |
| 1.0.2 | Busca de todos os sinais e negacao tambem em sinais de feature | Nao executada |
| 1.0.3 | Variantes de negacao com contracoes | Nao executada |
| 1.0.4 | Negacao modal antes da evidencia e controles para frases afirmativas | Nao executada |
| 1.0.5 | Negacao pos-frase com will/won't | Nao executada |
| 1.0.6 | Negacao com yet/never e parsing numerico SemVer sem limite de conversao | Nao executada |
| 1.0.7 | Negacao never com adverbios e comparacao de prerelease numerico longo | Nao executada |

As alteracoes acima foram revisoes tecnicas/testes, nao refinamentos com rotulos
humanos. Nao ha metricas experimentais por versao. Os exemplos de teste sao
sinteticos e nao devem ser publicados como amostra ou resultado.

## Infraestrutura de rotulagem e avaliacao

`validate_golden_sample` valida uma amostra fornecida pelo grupo; nao sorteia,
substitui nem completa releases. Os parametros padrao exigem 60 repositorios e
cinco releases por repositorio (300 linhas), IDs unicos, elegibilidade registrada,
URLs HTTPS do GitHub coerentes com o repositorio/release e `published_at` dentro
da janela UTC. O SHA-256 e retornado com as contagens. `write_sample_freeze_record`
registra hash, criterios, semente opcional, janela, contagens e data UTC. A criacao
e exclusiva, para nao sobrescrever um freeze anterior. Os testes podem usar
amostras menores, sem mudar os padroes de producao.

`write_individual_templates` cria tres CSVs separados com os mesmos IDs e coluna
de avaliador distinta. Rotulos e evidencias iniciam vazios; nenhum arquivo inclui
previsoes ou rotulos de colegas. A funcao nao sobrescreve arquivos existentes.
Os avaliadores preenchem os CSVs pessoalmente; o codigo nao inventa julgamentos.

`validate_independent_assessments` exige tres arquivos completos, esquema comum,
identidades iguais as da amostra, categorias permitidas, justificativa, evidencia
HTTPS e data de avaliacao. `uncertain` exige `evidence_insufficient=true`; vazio
nao se converte em `no`. `fleiss_kappa` calcula concordancia por dimensao e trata
`uncertain` como categoria. Denominador de acordo esperado zero retorna `None` e
status explicito.

`validate_consensus` aceita somente um registro por item, justificativa, evidencia
e status `resolved`/`unresolved`; unresolved exige motivo remanescente. Nao deriva
consenso por maioria. `freeze_human_consensus` so cria o objeto usado na avaliacao
depois de conferir hash/metadados do freeze da amostra, as tres rotulagens, Fleiss
nas tres dimensoes e o consenso completo. Registra hashes SHA-256 dos bytes de
entrada, do manifesto e digest canonico das linhas. O avaliador revalida entradas,
manifesto e digest apos consumir previsoes e antes da matriz. Isso protege contra
alteracoes acidentais no fluxo confiavel, mas nao e sandbox contra codigo hostil
no mesmo interpretador Python.

`evaluate_corrective_predictions` recusa consenso nao congelado e versao divergente.
Exige previsao `yes`, `no` ou `uncertain` para cada item consensual: previsao
ausente ou categoria invalida bloqueia a avaliacao. `uncertain` e abstencao
explicita, fica fora da matriz e e contada. `prediction_coverage` = previsoes
`yes`/`no` dividido pelo total de itens consensuais; `evaluation_coverage` = itens
na matriz dividido pelo total. Consensos unresolved/incertos ficam fora da matriz,
mas permanecem nessas contagens. Precisao, recall e F1 usam apenas consensos
binarios resolvidos com previsao binaria; denominadores zero retornam `None`.

O checkout nao contem amostra real congelada, arquivos individuais preenchidos ou
consenso. A infraestrutura nao sorteia a amostra, nao cria rotulos e nao foi usada
para gerar previsoes reais. Logo, nao liberou nem calculou avaliacao empirica.

## Definicao do CFR(b)

Para cada release de referencia `r`, usa-se `published_at` UTC. A referencia e
elegivel se estiver em `[window_start, window_end)` e o horizonte completo estiver
observavel. Com horizonte `H = 7 dias`, o teste e `published_at(r) + H <
window_end`. A desigualdade e estrita porque o fim experimental e exclusivo: uma
correcao exatamente em `window_end` nao e observavel. Assim, uma referencia
publicada exatamente em `window_end - H` e censurada, nao negativa.

Uma referencia elegivel e seguida por correcao quando existe release `f` com
`0 < published_at(f) - published_at(r) <= H` e previsao automatica `yes`. Varios
follow-ups contam uma unica vez no numerador da referencia. Timestamps de commits
nao substituem timestamps de publicacao. Releases com o mesmo timestamp nao sao
posteriores entre si.

`N` e o numero de referencias elegiveis com desfecho conhecido; `C` e o numero
dessas referencias seguidas por ao menos uma corretiva. `CFR(b) = C / N`; em
porcentagem, `100 * C / N`. Referencias censuradas saem do denominador. Se houver
follow-up `uncertain` e nenhuma corretiva positiva conhecida, o desfecho da
referencia fica incerto e sai do denominador, com contagem e auditoria explicitas.
Se houver uma corretiva positiva, o resultado e positivo mesmo que outro
follow-up seja incerto. Denominador zero retorna `None` com status
`denominator_zero`. Entradas com timestamps invalidos, sinalizador de janela
inconsistente ou coleta incompleta invalidam o resultado do repositorio; nao sao
convertidas em zero. Linhas fora da janela sao auditadas e excluidas.

A agregacao soma numeradores e denominadores validos; nao calcula media simples
das taxas por repositorio. Se houver resultados invalidos/incompletos, informa
`partial_data` e lista os repositorios excluidos. CFR(b) e uma associacao temporal
entre releases, nao prova que a primeira release causou a segunda.

## Independencia e avaliacao humana

Ordem obrigatoria: resolver/documentar a exposicao incidental abaixo; obter
evidencia de elegibilidade suficiente; congelar a mesma amostra para o trio;
concluir e validar as tres rotulagens independentes sem previsoes ou rotulos de
colegas; calcular Fleiss; discutir desacordos; registrar e congelar o consenso;
somente entao gerar/consultar previsoes da heuristica para a amostra e calcular
desempenho. Nao gerar nem consultar previsoes para itens da amostra-ouro antes
da conclusao das tres rotulagens e do consenso. A heuristica nao participa da
decisao do consenso.

O codigo acrescenta uma barreira: o scoring aceita apenas o objeto criado por
`freeze_human_consensus`, que valida os artefatos acima. Isso complementa, mas
nao substitui, os arquivos individuais separados e o procedimento humano; os
templates nao exibem previsoes automaticas.

**Risco de procedimento a resolver antes da rotulagem de Santiago:** durante uma
revisao tecnica, o revisor independente informou ter executado o classificador
sobre um artefato bruto real completo, obtendo 18 previsoes `yes`. O revisor nao
registrou qual repositorio/releases foram consultados, e nao existe artefato de
saida versionado. Nao ha evidencia de que os resultados tenham sido mostrados aos
avaliadores, mas a amostra-ouro ainda nao esta congelada e nao e possivel excluir
sobreposicao. Nao ha evidencia registrada de compartilhamento ou uso dessas
previsoes na rotulagem, mas a falta de rastreabilidade nao permite confirmar que
nao houve uso. Portanto, independencia nao esta estabelecida para itens
potencialmente sobrepostos. Antes de rotular, o grupo deve recuperar a identidade
dessa execucao e registrar se ela influenciou selecao, rotulagem ou decisoes, se
possivel. Se nao for possivel identifica-la, nenhum resultado potencialmente
sobreposto deve ser apresentado como independente; o grupo deve decidir se
descarta o lote possivelmente afetado ou o mantem apenas como analise
explicitamente nao independente. A decisao do grupo precisa ser registrada antes
de iniciar a rotulagem individual.

**Gate empirico pendente:** os dados presentes registram 107 repositorios
examinados, 100 candidatos pendentes de coletores historicos e zero elegiveis no
funil de selecao. Sem `runs_evidence.json` e sem 60 repositorios elegiveis, nao e
possivel congelar a amostra de 60x5. A insuficiencia deve ser resolvida pela coleta
historica e pelo procedimento de reposicao aprovado pelo grupo; nao selecionar,
substituir ou completar itens automaticamente.

A avaliacao de desenvolvimento deve aceitar apenas um consenso humano congelado
e previsoes com a mesma versao identificada. O protocolo para `uncertain` deve ser
congelado antes de calcular desempenho; os resultados devem incluir TP, FP, TN,
FN, precisao, recall, F1, itens avaliados, exclusoes e cobertura da heuristica.
Nao ha avaliacao disponivel para decidir o gatilho F1 < 0,70. Reutilizar os mesmos
rotulos para refinamento e avaliacao deve ser relatado como desenvolvimento, nao
como estimativa independente de generalizacao.

## Testes e reproducao

Os testes em `tests/test_corrective.py` usam fixtures sinteticas para SemVer,
sinais positivos/negativos, predecessores, fronteiras de sete dias, censura,
timestamps invalidos, releases duplicadas, incerteza, agregacao e adaptacao do
schema bruto. Os gates locais do workflow foram executados com Python 3.14.7:

```powershell
python -m pytest lab03/tests --cov=lab03.selection --cov=lab03.releases --cov=lab03.runs --cov=lab03.http --cov-report=term-missing --cov-fail-under=80
python -m pytest lab03/tests --cov=lab03.metrics --cov-report=term-missing --cov-fail-under=80
python -m pytest lab03/tests/test_corrective.py --cov=lab03.corrective --cov-report=term-missing --cov-fail-under=80
python -m pytest lab03/tests/test_human_validation.py --cov=lab03.human_validation --cov-report=term-missing --cov-fail-under=80
```

Resultados registrados nesta sessao em 2026-10-15: cada um dos dois gates de suite completa executou 202 testes; cobertura de
95,37% no conjunto selection/releases/runs/http, 100% em `metrics.py`, 96,38%
em `corrective.py` com 62 testes focados e 90,72% em `human_validation.py` com
37 testes focados (medido novamente nesta sessao). Sao execucoes locais, nao
equivalentes ao CI remoto. Os modulos ainda nao adicionam CLI, exportacao
consolidada de previsoes/datasets, metricas empiricas de classificacao ou coleta
real. A avaliacao segue bloqueada pelos insumos e etapas metodologicas acima.
