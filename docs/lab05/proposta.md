# Lab05S01 — Proposta: journal WAL × rollback no SQLite (#74)

Project v2: https://github.com/users/Druitti/projects/5 · Papel A (Planejamento e Método): Ferreira.
Instrumentação (#75): Santiago. Análise e tamanho amostral (#76): Tavares.

## 1. O software: SQLite

O SQLite é uma biblioteca em C que implementa um banco de dados SQL embutido no próprio
aplicativo, sem servidor. O objeto de pesquisa é a biblioteca em funcionamento: rodamos a
mesma versão mantida que está em produção e variamos uma configuração. Não analisamos o
repositório nem o código-fonte.

| Critério | Evidência | Fonte (acesso em 26/11/2026) |
|---|---|---|
| Real | Biblioteca de domínio público, com documentação oficial e versões publicadas desde 2000. | [sqlite.org](https://www.sqlite.org/index.html) |
| Em operação | Versão atual 3.54.1, de 16/10/2026; em 13/11/2026 saíram correções para as linhas 3.53, 3.50 e 3.44, que seguem mantidas. O estudo usa a 3.54.1. | [Histórico de releases](https://www.sqlite.org/chronology.html) |
| Alto impacto | Presente em todo aparelho Android, todo iPhone, todo Mac, toda instalação do Windows 10/11 e nos navegadores Firefox, Chrome e Safari. Os mantenedores estimam mais de 1 trilhão de bancos SQLite em uso, a partir de mais de 4 bilhões de smartphones ativos com centenas de bancos cada um. | [Most deployed](https://www.sqlite.org/mostdeployed.html) |
| Configuração estudada em produção | Desde o Android 9, os bancos dos aplicativos usam WAL por padrão; o Android relata ganho de até 4× na velocidade de escrita em ext4, mas desempenho semelhante ao do DELETE em F2FS. | [AOSP: Compatibility WAL](https://source.android.com/docs/core/perf/compatibility-wal) |

## 2. Pergunta de pesquisa e caminho

> No SQLite 3.54.1, num computador Apple com SSD e sistema de arquivos APFS, o modo de
> journal WAL muda a vazão e a latência de escritas e de leituras em relação ao journal
> de rollback padrão (DELETE)?

A documentação oficial afirma que o WAL é "significativamente mais rápido na maioria dos
cenários", mas talvez 1% a 2% mais lento quando quase só há leituras
([Write-Ahead Logging](https://www.sqlite.org/wal.html)). O Android relata 4× em ext4. O
APFS, sistema de arquivos de todo iPhone e Mac, não aparece nessas afirmações. O estudo
testa as duas afirmações nesse ambiente.

**Caminho:** rodar o software no ambiente do grupo (experimento controlado), combinado com
análise documental das afirmações publicadas pelos mantenedores e pelo Android, que servem
de referência para comparar os resultados.

## 3. GQM

**Objetivo (template de Basili):** analisar o modo de journal do SQLite 3.54.1 (WAL ×
DELETE) com o propósito de avaliar, com respeito à vazão e à latência de escritas e de
leituras, do ponto de vista de desenvolvedores que embarcam o SQLite em aplicativos, no
contexto de um computador Apple com SSD e APFS.

| Pergunta | Métrica |
|---|---|
| Q1. O WAL aumenta a vazão de transações de escrita? | M1: transações por segundo, por execução |
| Q2. O WAL reduz a latência de cauda das escritas? | M2: latência p95 e p99 por execução, em ms |
| Q3. O WAL muda o desempenho de leitura, como diz a documentação? | M3: consultas por segundo; M4: latência p95 |
| Q4. O ganho no APFS se aproxima dos 4× relatados para ext4? | M5: razão entre as médias WAL/DELETE, com IC de 95% |

## 4. Hipóteses e variáveis

Nível de significância de 5%, testes bilaterais. A documentação sugere direções opostas para
escrita e leitura; um teste bilateral não aposta em nenhuma delas.

- **H0-escrita:** a vazão de escrita tem a mesma distribuição em WAL e em DELETE.
  **H1-escrita:** difere.
- **H0-leitura:** a vazão de leitura tem a mesma distribuição em WAL e em DELETE.
  **H1-leitura:** difere.

| Tipo | Variável |
|---|---|
| Independente (fator) | `journal_mode` ∈ {DELETE, o padrão; WAL} |
| Segundo fator | Carga ∈ {escrita: 1 INSERT por transação; leitura: 1 SELECT por chave primária} |
| Dependentes | Vazão (operações/s); latências p50, p95, p99 e máxima (ms) |
| Controladas | SQLite 3.54.1; `synchronous=FULL`; `page_size` 4096; carga de 100 bytes por linha; tamanho das cargas; banco novo a cada execução; mesma máquina (Apple M5, 16 GiB, SSD, APFS) |
| Registradas, não controladas | Processos em segundo plano, temperatura, cache do sistema operacional, `fullfsync=0` |

**Entidade, atributo e escala.** A entidade é um produto (a biblioteca SQLite). O atributo é
externo, porque depende do ambiente: o desempenho, ou comportamento temporal da eficiência de
desempenho na ISO/IEC 25010. O tempo por operação é uma medida direta. Vazão, percentis e a
razão WAL/DELETE são medidas derivadas. Todas estão em escala de razão, que admite média,
média geométrica, coeficiente de variação e razões.

**Armadilhas de medição.** A vazão pode ser "jogada" (Lei de Goodhart) com
`synchronous=OFF` ou `journal_mode=MEMORY`, que trocam durabilidade por velocidade. Por isso,
`synchronous` fica fixo em FULL e o `fullfsync` é registrado. Olhar só a média esconderia a
cauda (Falácia de McNamara), então reportamos também p95, p99 e máximo.

## 5. As 7 categorias da pesquisa (primeira versão)

| Categoria | Classificação | Justificativa |
|---|---|---|
| Natureza | Aplicada | O resultado orienta uma decisão prática: qual `journal_mode` usar ao embarcar o SQLite. |
| Objetivos | Explicativa | Manipulamos o modo de journal para testar se ele causa a diferença de desempenho, e não só descrevê-la. |
| Abordagem | Quantitativa | Métricas em escala de razão, analisadas com estatística descritiva e testes de hipótese. |
| Procedimentos | Experimental, com apoio documental | Experimento controlado em laboratório; documentos oficiais sustentam os critérios, as hipóteses e o impacto. |
| Tempo | Transversal | Medições num intervalo curto, numa única versão do SQLite, sem acompanhar a evolução no tempo. |
| Controle | Experimento controlado | O grupo manipula o fator, fixa as demais configurações, sorteia a ordem das execuções e repete cada condição. |
| Nível de evidência | Alto para a validade interna, limitado para a generalização | Manipulação, aleatorização e repetição sustentam a relação causal nesta máquina; um único hardware, um único SO e cargas sintéticas limitam a extrapolação. |

## 6. Coleta piloto

`python -m lab05.pilot` roda 10 rodadas. Cada rodada executa as 4 condições em ordem sorteada
(semente 5), sempre num banco novo. A escrita faz 1.000 transações de um INSERT; a leitura
popula 10.000 linhas e faz 5.000 consultas por chave aleatória. Dados em
`lab05/data/pilot.csv` e ambiente em `lab05/data/pilot_env.json`. A coleta inteira leva
cerca de 3 segundos.

| Carga | Modo | Vazão média (ops/s) | CV | Latência p95 mediana (ms) |
|---|---|---:|---:|---:|
| Escrita | DELETE | 5.100 | 7,0% | 0,279 |
| Escrita | WAL | 23.061 | 15,8% | 0,053 |
| Leitura | DELETE | 287.439 | 12,0% | 0,0035 |
| Leitura | WAL | 758.348 | 7,3% | 0,0014 |

O que o piloto mostrou:

- **O desenho é viável e barato:** 40 execuções levam 3 segundos, então a coleta completa pode
  ter muitas repetições por condição.
- **Escrita:** o WAL teve vazão média 4,5× maior, perto dos 4× que o Android relata para ext4.
- **Leitura:** o WAL foi 2,6× mais rápido, ao contrário dos 1% a 2% a menos citados pela
  documentação. A explicação provável é de construto: com uma consulta por transação, cada
  leitura em DELETE adquire e libera travas no arquivo do banco, enquanto o WAL consulta um
  índice em memória compartilhada. A carga mede, portanto, o custo de abrir transações de
  leitura, e não o de ler páginas. A S02 deve incluir uma variante com as leituras dentro de
  uma única transação, para separar os dois efeitos.
- **Resolução:** as 5.000 leituras somam cerca de 6 ms por execução; a S02 deve aumentar a
  carga de leitura para reduzir o peso do ruído de medição.

O piloto é exploratório; os testes de hipótese ficam para a coleta completa.

## 7. Plano de coleta (S02, #75 e #77)

- Generalizar o piloto num coletor (#75): mesmo esquema de CSV, registro do ambiente, ordem
  aleatória com semente, validação dos dados e descarte documentado de execuções de
  aquecimento.
- **Repetições:** 100 execuções analisadas por condição, mais 2 de aquecimento descartadas (102
  rodadas), para 80% de poder de detectar uma razão WAL/DELETE de 1,05 a α = 0,025 (Holm). O
  n vem da simulação de poder de #76, com o par Welch × Mann–Whitney do Lab04; a estimativa
  preliminar anterior (cerca de 40 para 10% e 160 para 5%, por aproximação normal com o maior CV)
  foi substituída. Justificativa e cenários em [plano de análise](plano-analise.md).
- **Cargas:** leitura com mais consultas e a variante com uma única transação; possível
  terceiro fator `fullfsync` {0, 1}, porque no macOS o `fsync` padrão não esvazia o cache do
  disco, o que reduz o custo real da durabilidade.
- **Protocolo de execução:** máquina na tomada, sem outros aplicativos abertos, com os dados
  e o ambiente versionados no repositório.
- **Ética:** tudo roda localmente, sem sistemas de terceiros, sem carga sobre serviços
  externos e sem dados pessoais.

## 8. Plano de análise (S02, #76 e #78)

- **Unidade de análise:** a execução, porque cada uma usa um banco novo e é independente.
- **Teste por carga:** t de Welch × Mann–Whitney, reaproveitando o par e os módulos do Lab04,
  com correção de Holm para os dois testes principais (vazão de escrita e de leitura). Teste
  primário definido por métrica em [plano-analise.md](plano-analise.md): Welch em log na escrita,
  Mann–Whitney na leitura e nas variantes; o outro teste é sempre reportado.
- **Tamanho do efeito:** razão das médias WAL/DELETE com IC de 95% por bootstrap, g de Hedges
  e probabilidade de superioridade; latências descritas por mediana, p95 e p99.
- **Gráficos:** distribuição da vazão por condição e curva de distribuição acumulada das
  latências, com escala log quando a assimetria pedir.

## 9. Ameaças à validade (preliminares; versão completa em #79)

- **Conclusão:** poucas repetições no piloto e várias métricas por condição; mitigação com o
  n da simulação de poder e a correção de Holm.
- **Interna:** ordem das execuções, aquecimento e processos em segundo plano; mitigação com
  ordem sorteada, banco novo por execução e protocolo de máquina ociosa.
- **Construto:** a latência inclui a sobrecarga do Python; a leitura com uma consulta por
  transação mede travas, e não leitura de páginas; `fullfsync=0` subestima o custo de
  durabilidade.
- **Externa:** um único computador e um único SO (macOS, e não iOS ou Android) e cargas
  sintéticas; o APFS do Mac não equivale ao ext4 nem ao F2FS dos celulares Android.

## 10. O que vem dos laboratórios anteriores

| Laboratório | Reaproveitamento |
|---|---|
| Lab01 | Kanban no GitHub Projects com issues por integrante e sprint |
| Lab02 | Desenho com tratamentos e ordem aleatória das condições |
| Lab04 | Par Welch × Mann–Whitney, simulação de erro tipo I e poder para definir o n, dashboard |

## 11. Próximos passos

| Sprint | Issues |
|---|---|
| S01 | #74 (esta proposta) · #75 instrumentação · #76 plano de análise e n |
| S02 | #77 coleta completa · #78 análise · #79 ameaças à validade |
| S03 | #80 impacto · #81 categorias revisadas, conclusões e documento · #82 reprodutibilidade e apresentação |

Cada grupo precisa estudar um software diferente: o grupo deve confirmar com o professor que
nenhum outro grupo escolheu o SQLite.
