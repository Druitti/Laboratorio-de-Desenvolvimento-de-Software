# Cronometragem dos trials - Issue #13

O script `timer_trial.py` mede o tempo até todos os testes passarem e registra o
resultado no arquivo `lab02/data/trials.csv`.

## Antes de iniciar

Na raiz do projeto, instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Confirme que o pytest está disponível:

```bash
python -m pytest --version
```

## Executar um trial

```bash
python lab02/scripts/timer_trial.py --integrante gabsant07 --kata k1_merge_intervals --tratamento sem_ia
```

Tratamentos aceitos: `com_ia` e `sem_ia`.

Durante o cronômetro, edite somente o arquivo `kata.py` indicado no terminal. Os
testes são executados a cada 5 segundos. O trial termina em uma destas situações:

- `GREEN`: todos os testes passaram; o tempo até o green é salvo no CSV.
- `CENSURADO`: o limite terminou sem green; são registrados 35 minutos e o estado final dos testes.
- `Ctrl+C`: o trial foi cancelado antes do limite; nenhuma linha é gravada, pois não é uma medição válida.

Os `kata.py` começam com `NotImplementedError` de propósito. Portanto, `0/6 testes
passando` no início é esperado: a implementação deve ser feita pelo integrante
durante o trial, conforme o tratamento definido.

## Conferência da coleta

Ao final, confira se o terminal mostra `GREEN` ou `CENSURADO` e se uma nova linha
foi adicionada a `lab02/data/trials.csv`. A linha contém:

- integrante, kata e tratamento;
- tempo em segundos e minutos;
- indicação de censura;
- testes passando, total e falhando;
- taxa de sucesso.

## Testar o próprio script

```bash
python -m pytest lab02/scripts/test_timer_trial.py -q
```
