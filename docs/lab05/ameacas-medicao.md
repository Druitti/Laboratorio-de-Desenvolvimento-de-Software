# Lab05S02 — Ameaças à validade e decisões de medição (#79)

Complementa a [proposta](proposta.md) (#74). As ameaças listadas lá foram medidas com quatro
verificações, em `python -m lab05.validation`: 10 rodadas com ordem sorteada (semente 7),
SQLite 3.54.1, cerca de 80 segundos. Os dados ficam em `lab05/data/validation.csv` e
`lab05/data/validation_summary.json`. A coleta completa continua em #77.

## 1. Escalas e estatísticas permitidas

| Métrica ou variável | Medida | Escala | Estatísticas permitidas | Uso no estudo |
|---|---|---|---|---|
| Tempo por operação (ns) | Direta | Razão | Todas: média, mediana, percentis, CV, razões | Latências p50, p95, p99 e máxima |
| Vazão (operações/s) | Derivada: operações ÷ tempo somado | Razão | Todas | Métrica principal |
| Razão WAL/DELETE | Derivada | Razão (adimensional) | Média geométrica, IC por bootstrap | Tamanho do efeito |
| `journal_mode`, carga, variante | Fator | Nominal | Frequência, moda; definem os grupos | Variáveis independentes |
| Rodada, posição na rodada | Contagem de ordem | Ordinal | Mediana, postos, correlação de Spearman | Verificação de efeito de ordem |

A vazão e as latências estão em escala de razão, então comparar médias com o t de Welch e
falar em "WAL 4,5× mais rápido" é legítimo. O mesmo não vale para as variáveis de ordem, que
só admitem estatísticas de postos.

## 2. Armadilhas de medição

| Armadilha | Como apareceria aqui | Decisão |
|---|---|---|
| Lei de Goodhart | A vazão vira meta e é "jogada" com `synchronous=OFF` ou `journal_mode=MEMORY`, que trocam durabilidade por velocidade. | `synchronous=FULL` fixo; durabilidade real medida com `fullfsync` (seção 3b). |
| Lei de Campbell | Um indicador único de vazão pressiona a adoção do WAL sem pesar seus custos: não funciona em sistema de arquivos de rede, cria arquivos -wal e -shm e exige checkpoints. | O documento final cita esses custos, da documentação oficial, ao lado dos números. |
| Falácia de McNamara | Medir só o que é fácil (vazão média) e ignorar o que importa (cauda, durabilidade, concorrência). | Reportar p95, p99 e máximo e medir a durabilidade; a concorrência entre leitores e escritores não foi medida e fica como limitação. |

## 3. Verificações executadas

### a) Leituras: uma transação por consulta × uma única transação (construto)

| Variante | DELETE (consultas/s) | WAL (consultas/s) | WAL/DELETE |
|---|---:|---:|---:|
| Uma transação por consulta, como no piloto | 244.536 | 708.966 | 2,90× |
| Todas as consultas numa única transação | 1.292.913 | 1.399.473 | 1,08× |

Na transação única, a vantagem do WAL quase some. Isso confirma que a diferença do piloto
vinha do custo de abrir uma transação de leitura (travas no arquivo no DELETE, contra o índice
em memória compartilhada no WAL), e não da leitura de páginas. Mesmo assim, o WAL ainda foi 8%
mais rápido, e não 1% a 2% mais lento, como diz a documentação.
**Decisão:** a coleta completa mede as duas variantes. A de uma transação por consulta
representa aplicativos que usam o modo de confirmação automática; a de transação única testa
diretamente a afirmação da documentação.

### b) Durabilidade: `fsync` padrão × F_FULLFSYNC (construto e externa)

| `fullfsync` | DELETE (transações/s) | WAL (transações/s) | WAL/DELETE |
|---|---:|---:|---:|
| 0, o padrão do SQLite no macOS | 4.483 | 24.217 | 5,40× |
| 1, esvazia o cache do disco | 87 | 266 | 3,07× |

No macOS, o `fsync` padrão não garante que o dado chegou ao meio físico. Com a durabilidade
real, a vazão cai cerca de 50× no DELETE e 90× no WAL, e a vantagem do WAL cai de 5,4× para
3,1×, mas não desaparece.
**Decisão:** a condição principal mantém o padrão (`fullfsync=0`), que é o que a maioria dos
aplicativos usa; `fullfsync=1` entra como cenário de sensibilidade. Os números absolutos com o
padrão não devem ser lidos como o custo de uma confirmação durável.

### c) Sobrecarga fixa do Python (construto)

Uma chamada `SELECT 1` levou 0,96 µs na mediana (p95 de 1,46 µs). Isso equivale a cerca de 74%
da latência mediana de leitura no WAL (1,3 µs) e 29% da do DELETE (3,3 µs), mas a menos de 3%
das escritas (de 39 a 176 µs).
**Decisão:** nas escritas, a sobrecarga é desprezível. Nas leituras, ela dilui a diferença
entre os modos: subtraindo a mediana da sobrecarga, a razão seria da ordem de 7×, e não 2,5×.
Por isso, a razão medida nas leituras é um limite inferior da diferença dentro da biblioteca.
A sobrecarga é reportada junto com os resultados, e não subtraída deles.

### d) Ordem e aquecimento (interna)

Correlação de Spearman entre a vazão e a rodada (ou a posição dentro dela), nos 10 runs de cada
condição do piloto. Com n = 10, |ρ| precisa passar de 0,648 para ser significativo a 5%.

| Condição | ρ com a rodada | ρ com a posição na rodada |
|---|---:|---:|
| Escrita, DELETE | 0,07 | −0,48 |
| Escrita, WAL | **0,70** | 0,20 |
| Leitura, DELETE | −0,03 | −0,16 |
| Leitura, WAL | 0,16 | 0,16 |

A vazão de escrita no WAL subiu ao longo da sessão, sinal de aquecimento ou de deriva da
máquina. Esse efeito explica parte do CV de 15,8% dessa condição. Como a ordem é sorteada, ele
afeta os dois modos por igual em média, mas aumenta a variância.
**Decisão:** a coleta completa descarta execuções de aquecimento, registra o horário de cada
execução e mantém o sorteio; a análise verifica a deriva e pode tratar a rodada como bloco.

## 4. Ameaças à validade e mitigação

| Tipo | Ameaça | Evidência | Mitigação |
|---|---|---|---|
| Conclusão | Poder baixo para diferenças pequenas | CV de 7% a 16% no piloto | n por condição da simulação de poder de #76 (preliminar: 40 para detectar 10%) |
| Conclusão | Várias métricas e cargas aumentam o erro tipo I | 2 testes principais e métricas secundárias | Holm nos testes principais; métricas secundárias só descritivas |
| Conclusão | Distribuições não normais e variância diferente entre grupos | CV diferente entre os modos | Welch × Mann–Whitney e IC por bootstrap |
| Interna | Aquecimento e deriva ao longo da sessão | ρ = 0,70 na escrita em WAL (seção 3d) | Aquecimento descartado, ordem sorteada, rodada como bloco |
| Interna | Arquivos reaproveitados entre execuções | Teste automatizado confirma diretório novo e vazio a cada execução | Banco novo por execução |
| Interna | Processos em segundo plano | Não controlados no piloto | Protocolo de máquina ociosa e na tomada, registrado em #75 |
| Construto | Latência inclui a sobrecarga do Python | 0,96 µs por chamada (seção 3c) | Sobrecarga reportada; razão das leituras tratada como limite inferior |
| Construto | Leitura com uma transação por consulta mede travas | 2,90× contra 1,08× (seção 3a) | Duas variantes de leitura |
| Construto | `fsync` padrão do macOS não garante durabilidade | Vazão cai de 50× a 90× com `fullfsync` (seção 3b) | Condição de sensibilidade com `fullfsync=1` |
| Construto | Vazão como único retrato do desempenho | Concorrência entre leitor e escritor não medida | Limitação declarada |
| Externa | Uma máquina (Apple M5, APFS) e um SO | Android relata 4× em ext4 e ~1× em F2FS | Não generalizar para Android; comparar com as afirmações publicadas |
| Externa | Binding Python e carga sintética | Aplicativos usam bindings nativos e cargas reais | Declarar o escopo: biblioteca SQLite via Python, cargas sintéticas |
| Externa | Uma única versão (3.54.1) | Versões mantidas anteriores existem em produção | Declarar a versão; repetir com outra versão seria extensão |

## 5. Conformidade com o protocolo da proposta

| Item da proposta | Situação no piloto |
|---|---|
| SQLite 3.54.1 | Confirmado em `pilot_env.json` |
| `synchronous=FULL`, `page_size` 4096 | Confirmado em `pilot_env.json` |
| `fullfsync` registrado | Registrado (0) |
| Ordem sorteada por rodada | Confirmada por teste automatizado |
| Banco novo por execução | Confirmado por teste automatizado |
| Dados versionados | `lab05/data/pilot.csv` no repositório |
| Execuções de aquecimento | Não houve; passam a ser exigidas (seção 3d) |
| Estado da máquina (energia, processos) | Não registrado automaticamente; passa a ser exigido em #75 |

## 6. Recomendações para a coleta completa (#77) e a análise (#78)

1. Medir as duas variantes de leitura e as duas de `fullfsync` na escrita.
2. Usar pelo menos 20.000 consultas por execução de leitura, para a soma dos tempos não ficar
   na casa dos milissegundos.
3. Descartar 2 execuções de aquecimento e registrar o horário de cada execução.
4. Usar o n por condição definido em #76 (preliminar: 40).
5. Na análise, verificar a deriva por rodada e reportar a sobrecarga do Python junto com as
   latências de leitura.
