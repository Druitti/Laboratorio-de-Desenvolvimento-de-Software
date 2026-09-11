# Lab02 — Ambiente (Passo 2)

Issue: **#14** · Responsável: Gabriel Tavares (`Tavaresds1`)

## Ambiente do experimento

- **Linguagem:** Python 3 (o grupo usa Python 3.14 localmente; qualquer Python ≥ 3.11 funciona, pois os katas não usam recursos específicos de versão).
- **Testes:** `pytest` — usado para validar os katas (`test_kata.py`) e para o `timer_trial.py` decidir quando um trial chega ao green.
- **Métricas estáticas:** `radon` — usado pelo `static_metrics.py` (complexidade ciclomática, LOC e, opcionalmente, Índice de Manutenibilidade).
- **Assistente de IA único do grupo:** **ChatGPT** (versão web gratuita). É o único assistente permitido nos trials `com_ia`; nos trials `sem_ia` nenhum assistente generativo (ChatGPT, Copilot, etc.) pode ser usado — ver ameaças à validade em `desenho-experimento.md`.

## Instalação

Na raiz do projeto:

```bash
python -m pip install -r requirements.txt
```

Confirme que as ferramentas estão disponíveis:

```bash
python -m pytest --version
python -m pip show radon
```

## Como rodar

### 1. Cronometrar um trial (Issue #13)

```bash
python lab02/scripts/timer_trial.py --integrante <usuario> --kata <pasta_do_kata> --tratamento <com_ia|sem_ia>
```

Detalhes em [lab02/scripts/README.md](../../lab02/scripts/README.md).

### 2. Medir as métricas estáticas do kata (Issue #14)

Logo após o trial terminar (green ou censurado), antes de o próximo integrante sobrescrever o mesmo `kata.py`, rode:

```bash
python lab02/scripts/static_metrics.py --kata <pasta_do_kata> --integrante <usuario> --tratamento <com_ia|sem_ia> --mi
```

- `--mi` é opcional e adiciona o Índice de Manutenibilidade à linha.
- O resultado é acrescentado em `lab02/data/static_metrics.csv` (LOC, complexidade ciclomática média/total por bloco, e MI quando pedido).
- O campo `arquivo` na linha do CSV identifica exatamente qual `kata.py` foi medido, para cruzar depois com `lab02/data/trials.csv` (integrante + kata + tratamento) na análise da S03 (RQ3).

## Decisão: duplicação de código (adiada)

O desenho do experimento cita duplicação de código como métrica opcional para a RQ3 ("se necessário"/"se disponível"). Os katas são funções únicas de poucas linhas (10–20 LOC cada), tamanho em que essa métrica não costuma ser informativa, e adicionar uma ferramenta extra (ex.: `jscpd`) só para isso seria desproporcional ao escopo desta Issue. Por isso, **essa métrica fica fora do `static_metrics.py` por enquanto**. Se a análise da S03 mostrar necessidade real (por exemplo, blocos de código muito repetidos entre soluções geradas por IA), o grupo pode revisitar essa decisão nessa etapa, usando os dados já coletados como evidência.

## Testes do próprio script

```bash
python -m pytest lab02/scripts/test_static_metrics.py -q
```
