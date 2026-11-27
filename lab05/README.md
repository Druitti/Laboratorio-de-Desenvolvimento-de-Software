# Lab05 — SQLite: journal WAL × rollback

Experimento controlado com o SQLite em operação: a mesma versão mantida em produção
(3.54.1), rodando localmente, com o modo de journal variando entre DELETE (padrão) e WAL.
Proposta, hipóteses, GQM e as 7 categorias: [proposta](../docs/lab05/proposta.md) (#74).

## Piloto (Lab05S01)

Na raiz do repositório, com Python 3.12 ou superior (só biblioteca padrão):

```bash
python -m lab05.pilot
```

Roda 10 rodadas com as 4 condições (modo × carga) em ordem sorteada (semente 5), cada uma
num banco novo, e grava `lab05/data/pilot.csv` e `lab05/data/pilot_env.json`. Use
`--rounds`, `--seed`, `--write-transactions`, `--read-rows` e `--read-queries` para mudar o
tamanho. A versão do SQLite medida é a do módulo `sqlite3` do Python usado, e fica registrada
no JSON.

## Coleta reproduzível (Lab05S01 · #75)

Execute na raiz com Python 3.12 ou superior. O teste rápido usa o SQLite disponível
no Python local e grava os resultados em um diretório novo.

```bash
python -m lab05.collect --output-dir lab05/data/s01-verificacao --rounds 2 --seed 5 --warmup-rounds 1 --write-transactions 20 --read-rows 50 --read-queries 30
```

Para medir no ambiente da proposta, inicialize o Python vinculado ao SQLite 3.54.1
no Mac Apple M5 com SSD e escolha um diretório de saída em um volume APFS local.
Confira previamente o sistema de arquivos com o Utilitário de Disco. Exemplo de
execução com a carga do piloto e uma rodada de aquecimento:

```bash
python -m lab05.collect --output-dir lab05/data/s01-apfs --require-sqlite 3.54.1 --rounds 10 --seed 5 --warmup-rounds 1 --storage "SSD interno / APFS" --notes "Na tomada, máquina ociosa"
```

1. Ligue a máquina à tomada e aguarde ficar ociosa. Feche aplicações pesadas,
   pause sincronizações e backups e evite usar a máquina durante a execução.
   Use a mesma máquina, volume, versão do Python e configuração de energia em
   todas as repetições.
2. Registre em `--storage` o dispositivo e sistema de arquivos verificados e em
   `--notes` as condições observadas (energia, processos e intercorrências).
   O coletor registra processador, arquitetura, CPUs lógicas, SO, Python,
   SQLite, parâmetros, sementes e PRAGMAs. Cada banco roda com o modo de journal
   previsto, `synchronous=FULL`, `page_size=4096` e `fullfsync=0`, verificados na conexão.
3. Cada rodada executa uma vez cada combinação de WAL/DELETE e leitura/escrita,
   em ordem sorteada. Cada execução abre um banco novo no volume de saída.
   O aquecimento roda as mesmas cargas com a semente principal mais um. Suas
   medições são descartadas antes da coleta e o CSV começa na rodada 1.
4. Confira `validated_rows` em `environment.json`. Deve ser quatro vezes o número
   de rodadas. O coletor confere o CSV gravado, incluindo esquema do piloto,
   ordem prevista pela semente, quantidades, vazão e ordenação dos percentis.
   Mantenha os dois arquivos juntos. Se houver uma interrupção ou desvio do
   protocolo, registre o motivo e repita em outro diretório. Na S02, use o
   número de rodadas definido pelo plano amostral do grupo.

**Ética.** Use apenas os dados sintéticos gerados localmente pelo coletor.
Evite incluir nomes, identificadores ou dados pessoais nas notas e não execute
cargas contra serviços de terceiros.

## Verificações de validade (Lab05S02)

```bash
python -m lab05.validation
```

Mede quanto pesam as ameaças da proposta: leituras numa única transação, `fullfsync`,
sobrecarga do Python e efeito de ordem no piloto (cerca de 80 segundos). Grava
`lab05/data/validation.csv` e `lab05/data/validation_summary.json`. Interpretação e
decisões: [ameaças e medição](../docs/lab05/ameacas-medicao.md) (#79).

## Plano de análise e tamanho amostral (#76)

Precisa de numpy, scipy e matplotlib (`python -m pip install numpy scipy matplotlib`) e reaproveita
o Welch × Mann–Whitney do `lab04`:

```bash
python -m lab05.power   # simula o poder e grava lab05/data/power.json (cerca de 5 minutos)
python -m lab05.plots   # esboça as figuras F1 a F5 em docs/lab05/figuras/
```

`lab05.analysis` reúne o teste e o tamanho do efeito de cada métrica (razão das médias
geométricas com IC por bootstrap, g de Hedges, probabilidade de superioridade, Holm) e será
usado na análise completa (#78). Plano, n por condição e justificativa:
[plano de análise](../docs/lab05/plano-analise.md).

## Testes

```bash
python -m pip install pytest
python -m pytest lab05/tests -q
```
