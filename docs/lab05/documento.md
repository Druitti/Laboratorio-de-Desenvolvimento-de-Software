# Lab05 — WAL × rollback no SQLite em operação

Documento do grupo (rascunho do documento final, #81). Proposta: [proposta.md](proposta.md)
(#74). Ameaças e decisões de medição: [ameacas-medicao.md](ameacas-medicao.md) (#79).

> **Estado dos números.** Os resultados abaixo vêm do piloto (10 execuções por condição) e das
> verificações de validade (10 por variante). A coleta completa (#77), a análise com testes de
> hipótese (#78) e a estimativa de impacto (#80) substituem estes números; as seções marcadas
> com essas issues são preenchidas por quem as executa.

## Resumo

O SQLite é o banco de dados mais usado do mundo, presente em todo celular, Mac e navegador.
Comparamos os dois modos de journal da versão atual (3.54.1), DELETE (o padrão) e WAL, num
computador Apple com SSD e APFS. Nas escritas, o WAL foi 4,5× mais rápido com o `fsync` padrão
e 3,1× mais rápido com a durabilidade real (F_FULLFSYNC). Nas leituras, a vantagem depende do
padrão de uso: 2,9× quando cada consulta abre sua própria transação, mas só 8% quando as
consultas compartilham uma transação. A recomendação dos mantenedores de usar WAL se confirma
nesse ambiente, e a afirmação de que o WAL seria 1% a 2% mais lento em leituras não se
confirmou.

## 1. O software e os três critérios

| Critério | Evidência (acesso em 26/11/2026) |
|---|---|
| Real | Biblioteca de domínio público com documentação oficial ([sqlite.org](https://www.sqlite.org/index.html)). |
| Em operação | Versão 3.54.1 de 16/10/2026; linhas 3.53, 3.50 e 3.44 corrigidas em 13/11/2026 ([histórico](https://www.sqlite.org/chronology.html)). |
| Alto impacto | Todo Android, iPhone, Mac, Windows 10/11 e os navegadores Firefox, Chrome e Safari; mais de 1 trilhão de bancos em uso, segundo os mantenedores ([most deployed](https://www.sqlite.org/mostdeployed.html)). |
| Configuração em produção | WAL é o padrão dos aplicativos Android desde a versão 9 ([AOSP](https://source.android.com/docs/core/perf/compatibility-wal)). |

O objeto de pesquisa é a biblioteca em funcionamento, rodando localmente. O estudo não minera
nem analisa o repositório, como exige o enunciado.

## 2. Pergunta e caminho

> No SQLite 3.54.1, num computador Apple com SSD e APFS, o modo de journal WAL muda a vazão e a
> latência de escritas e de leituras em relação ao journal de rollback padrão (DELETE)?

O caminho combina um experimento controlado, rodando o software no ambiente do grupo, com
análise documental: os resultados são comparados com as afirmações publicadas pelos
mantenedores (WAL "significativamente mais rápido", mas 1% a 2% mais lento em leituras) e pelo
Android (4× na escrita em ext4).

## 3. Método

- **Fatores:** `journal_mode` {DELETE, WAL} × carga {escrita, leitura}; variantes de sensibilidade:
  leitura em transação única e escrita com `fullfsync=1`.
- **Métricas (GQM):** vazão em operações/s; latências p50, p95, p99 e máxima. Todas em escala de
  razão.
- **Hipóteses:** H0 de distribuições iguais entre WAL e DELETE, por carga; testes bilaterais a 5%
  com Welch × Mann–Whitney e correção de Holm.
- **Controle:** banco novo por execução, ordem das condições sorteada em cada rodada,
  `synchronous=FULL` e as demais configurações fixas, ambiente registrado em JSON.

## 4. As 7 categorias da pesquisa (revisadas)

| Categoria | Classificação | Justificativa | Mudança desde a S01 |
|---|---|---|---|
| Natureza | Aplicada | Orienta a escolha do `journal_mode` por quem embarca o SQLite. | Nenhuma |
| Objetivos | Explicativa | O modo de journal é manipulado para testar se ele causa a diferença de desempenho. | As verificações também explicam o mecanismo: a diferença nas leituras vem do custo de abrir transações. |
| Abordagem | Quantitativa | Métricas em escala de razão, estatística descritiva, testes e tamanho do efeito. | Nenhuma |
| Procedimentos | Experimental, com apoio documental | Experimento controlado em laboratório; os resultados são confrontados com as afirmações oficiais. | A comparação com as afirmações publicadas virou parte explícita dos resultados. |
| Tempo | Transversal | Medições num intervalo curto, numa só versão. | Nenhuma; a deriva dentro da sessão (seção 7) reforça que o estudo não acompanha o tempo. |
| Controle | Experimento controlado | Fator manipulado, demais configurações fixas, ordem sorteada, repetição. | O protocolo passou a exigir execuções de aquecimento descartadas. |
| Nível de evidência | Alto para a validade interna nesta máquina; baixo para a generalização | Manipulação, aleatorização e repetição sustentam a causalidade local; uma máquina, um SO e cargas sintéticas limitam a extrapolação. | As verificações mostraram quanto pesam a sobrecarga do Python e a semântica do `fsync`. |

## 5. Conceitos da disciplina aplicados

| Conceito | Onde aparece |
|---|---|
| GQM | Objetivo no template de Basili, 4 perguntas e 5 métricas ([proposta](proposta.md), seção 3) |
| Entidades e atributos | Produto (biblioteca); atributo externo (desempenho); medidas diretas e derivadas |
| Escalas | Vazão e latências em escala de razão; fatores nominais; ordem ordinal ([ameaças](ameacas-medicao.md), seção 1) |
| Goodhart, Campbell, McNamara | `synchronous` fixo, durabilidade medida, cauda reportada, custos do WAL citados |
| Planejamento de experimentos | Hipóteses, variáveis, controle, aleatorização e repetição |
| Ameaças à validade | Os 4 tipos, com evidência medida e mitigação |
| Análise | Welch × Mann–Whitney, tamanho do efeito e poder, reaproveitados do Lab04 |

## 6. O que veio dos laboratórios anteriores

| Laboratório | Reaproveitamento | O que é novo |
|---|---|---|
| Lab01 | Kanban no GitHub Projects, issues por integrante e sprint | — |
| Lab02 | Tratamentos e ordem aleatória das condições | Objeto é um software em operação, não pessoas |
| Lab04 | Par Welch × Mann–Whitney, simulação de poder, dashboard | Dados vêm de um experimento controlado, e não de observação |

## 7. Resultados (provisórios)

Vazão média por condição. Piloto: 10 execuções por condição, semente 5. Verificações: 10 por
variante, semente 7.

| Carga e variante | DELETE | WAL | WAL/DELETE |
|---|---:|---:|---:|
| Escrita, `fsync` padrão (piloto) | 5.100 transações/s | 23.061 transações/s | 4,52× |
| Escrita, `fsync` padrão (verificação) | 4.483 transações/s | 24.217 transações/s | 5,40× |
| Escrita, F_FULLFSYNC | 87 transações/s | 266 transações/s | 3,07× |
| Leitura, uma transação por consulta (piloto) | 287.439 consultas/s | 758.348 consultas/s | 2,64× |
| Leitura, uma transação por consulta (verificação) | 244.536 consultas/s | 708.966 consultas/s | 2,90× |
| Leitura, transação única | 1.292.913 consultas/s | 1.399.473 consultas/s | 1,08× |

Nas escritas, a latência p95 mediana caiu de 0,279 ms no DELETE para 0,053 ms no WAL. Os testes
de hipótese, os intervalos de confiança e o tamanho do efeito com o n completo ficam em #78.

## 8. Ameaças à validade (resumo)

- **Conclusão:** n do piloto pequeno; vários testes. Mitigação: n de #76, Holm, testes robustos.
- **Interna:** a vazão de escrita no WAL subiu ao longo da sessão (ρ = 0,70). Mitigação: ordem
  sorteada, aquecimento descartado, rodada como bloco.
- **Construto:** sobrecarga do Python de cerca de 1 µs por chamada, que torna a razão das
  leituras um limite inferior; leituras com uma transação por consulta medem travas; `fsync`
  padrão do macOS sem durabilidade real. Todas foram medidas.
- **Externa:** uma máquina Apple com APFS, binding Python e cargas sintéticas; o Android relata
  resultados diferentes em ext4 e F2FS.

Detalhes, evidências e mitigação em [ameacas-medicao.md](ameacas-medicao.md).

## 9. O que o estudo mostrou

1. **O WAL acelera muito as escritas no APFS:** de 4,5× a 5,4× com o `fsync` padrão, na mesma
   ordem dos 4× que o Android relata para ext4.
2. **A vantagem resiste à durabilidade real:** com F_FULLFSYNC, a vazão absoluta cai de 50× a 90×,
   mas o WAL continua 3× mais rápido.
3. **Nas leituras, o que importa é o padrão de transação:** com uma transação por consulta o WAL
   é quase 3× mais rápido; com as consultas numa transação, a diferença cai para 8%.
4. **A afirmação de que o WAL é 1% a 2% mais lento em leituras não se confirmou** neste ambiente:
   ele empatou ou foi mais rápido em todas as variantes.

## 10. O que isso significa para quem usa o SQLite

- **Desenvolvedores em plataformas Apple:** ativar o WAL é uma decisão de uma linha
  (`PRAGMA journal_mode=WAL`) que multiplica a vazão de escrita, sem perder a vantagem quando a
  durabilidade é levada a sério.
- **Aplicativos que fazem muitas consultas pequenas:** agrupar consultas numa transação rende tanto
  quanto trocar de modo de journal; os dois ganhos se somam.
- **Usuários finais:** confirmações mais rápidas significam menos tempo de CPU e de disco por
  operação, em aparelhos que executam milhões delas. A estimativa em números, com fontes, fica em
  #80.
- **Custos a considerar:** o WAL não funciona em sistemas de arquivos de rede, cria os arquivos
  -wal e -shm e exige checkpoints, segundo a documentação oficial.

## 11. Limitações e o que não é possível afirmar

- Os resultados valem para um Apple M5 com APFS e SQLite 3.54.1 acessado pelo Python. Não é
  possível afirmar o mesmo ganho em iPhones, que também usam APFS mas outro hardware e outra
  pilha de armazenamento, nem em Android, onde o próprio projeto relata ganho de 4× em ext4 e
  quase nenhum em F2FS.
- As cargas são sintéticas, com uma linha de 100 bytes por operação; transações grandes,
  concorrência entre leitores e escritores e checkpoints longos não foram medidos.
- O estudo mostra que o modo de journal causa a diferença nesta máquina, não quanto tempo os
  usuários de fato economizam; isso depende do padrão de uso de cada aplicativo.
- Os números atuais são do piloto e das verificações; a coleta completa (#77) e a análise (#78)
  podem refinar as magnitudes, mas efeitos de 3× a 5× dificilmente mudam de sentido.

## 12. Próximos passos para a entrega final

1. Integrar a coleta completa (#77) e a análise com testes e IC (#78) nas seções 7 e 9.
2. Incluir a estimativa de impacto com fontes (#80) na seção 10.
3. Preparar a apresentação de 10 minutos e o comando único de reprodução (#82).
