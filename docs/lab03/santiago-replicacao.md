# Lab03Final — Santiago — comparação da replicação (#57)

## Situação e dependência #56

O comparador `lab03.replication` implementa a parte automatizável de #57.
O grupo autor, seu repositório, o CSV original e a replicação efetiva dos 30
repositórios ainda precisam ser fornecidos pela #56. Não foram criados resultados
empíricos, diagnósticos atribuídos a esse grupo ou issues externas nesta entrega.
A issue #57 permanece pendente da execução real, investigação das divergências,
registro de problemas verificáveis no grupo autor e contribuição ao relatório final.

## Contrato dos CSVs

Os dois arquivos usam cabeçalho e UTF-8 (BOM aceito). Por padrão:

- `repository`: identidade `owner/repo`; alinhamento ignora maiúsculas/minúsculas
  e espaços externos. Duplicatas, inclusive apenas com capitalização diferente,
  bloqueiam a comparação. URLs completas devem ser normalizadas previamente.
- Métricas: selecionar explicitamente colunas numéricas comuns, de mesma fórmula
  e unidade, usando `--metrics`. Não há conversão automática de horas/dias,
  proporção/porcentagem ou definição de métricas. Célula vazia é ausência;
  textos, NaN e infinito são inválidos. Números usam ponto decimal.
- `dora_class`: `Low`, `Medium`, `High`, `Elite` ou números inteiros 1 a 4;
  representações CSV como `3.0` são aceitas. Vazio é ausência; outras categorias
  bloqueiam o processamento. A ordem numérica é Low=1 até Elite=4.
- Opcionalmente `window_start`, `window_end`, `collected_at`: strings preservadas
  na auditoria. São comparadas literalmente; representações equivalentes de UTC
  devem ser normalizadas previamente. Ausência não comprova equivalência temporal.

`--repository-column` e `--class-column` escolhem nomes alternativos comuns aos
dois arquivos. Se os nomes diferirem entre as fontes, preparar cópias normalizadas
e documentar o mapeamento; conservar os originais e seus hashes como evidência.
Escolher explicitamente a combinação DORA correspondente: por exemplo, `C1`
exige definição compatível nos dois lados. Não comparar combinações distintas
como se fossem a mesma classificação.

Sem `--selection`, o replicado deve ter exatamente 30 repositórios únicos.
Com `--selection`, fornecer um terceiro CSV com coluna `repository` e exatamente
30 identidades: assim até repositórios ausentes de um ou dos dois resultados
podem ser auditados. Fontes podem conter outros repositórios, listados como
excluídos em `summary.json`; não há escolha automática dos primeiros 30.

## Execução no PowerShell

Exemplo de interface, a adaptar aos caminhos e colunas reais recebidos de #56:

```powershell
python -m lab03.replication --original CAMINHO/original.csv --replicated CAMINHO/replicado.csv --selection CAMINHO/selecionados30.csv --metrics deployment_frequency lead_time_commit_hours cfr_ci recovery_hours --class-column C1 --out lab03/results/replicacao-NOVA
```

O programa recusa saída existente, colunas inválidas, identidades duplicadas,
números não finitos e seleção com tamanho diferente de 30. Os testes são offline:

```powershell
python -m pytest lab03/tests/test_replication.py -q
```

## Diferenças, classificação e artefatos

`comparison.csv` contém uma linha por repositório/métrica, valores originais e
replicados, diferença absoluta `abs(replicado-original)`, diferença relativa
`(replicado-original)/abs(original)` e porcentagem `100 × diferença relativa`.
Ambos zero produzem diferença relativa zero; original zero com replicado diferente
produz célula vazia e status `zero_baseline`. Ausências não são imputadas e têm
status `missing_original`, `missing_replicated` ou `missing_both`.

`summary.json` inclui hashes SHA-256 das entradas, argumentos e comando de execução,
repositórios excluídos, contagens por status/métrica e auditoria por repositório:
presença em cada fonte, classes e metadados temporais. `summary.md` fornece texto
de apoio e limitações. Percentual de mesma classe usa somente pares com duas
classes válidas, publicando numerador, denominador e pares ausentes. Denominador
zero produz `null`, não 0%. O percentual descreve concordância, não exatidão de
um grupo ou equivalência dos métodos.

Janelas diferentes/ausentes tornam a interpretação condicional. Comparação literal
de metadados não determina causa: investigar retenção de histórico, revisões de
tags/releases, mudanças no coletor, fórmulas e unidades somente com evidência.
Preservar logs, configuração, versões/commits dos dois projetos e fontes de #56.

## Rascunho de evidência para problemas do grupo autor

Preencher somente após reproduzir um problema real. Não publicar este modelo
com dados hipotéticos nem atribuir divergência a uma causa sem investigação.

```text
Título: [replicação] descrição objetiva do problema observado
Repositório/commit do grupo autor:
Ambiente e versões:
Comando exato:
Entradas, janela e SHA-256:
Erro e log reproduzível (sem credenciais):
Resultado esperado e fonte da expectativa:
Resultado obtido (métrica, unidade, repositório e valor):
Diferença e hipóteses investigadas; evidências que sustentam cada hipótese:
Limitações temporais e ameaças à validade:
Link da issue real, após publicação:
```

Incluir os links efetivos no relatório de replicação, analisando causas prováveis
com evidências, perdas de dados e limites da comparação. Abrir issues externas
exige o grupo autor identificado e um problema verificável;
nenhuma dessas ações é comprovada pela existência do comparador.
