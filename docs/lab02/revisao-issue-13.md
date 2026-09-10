# Revisão da Issue #13 - Cronometragem e coleta

## O que a entrega precisa fazer

- limitar cada trial a 35 minutos;
- identificar o tempo até todos os testes passarem;
- registrar como censurado o trial que chegar ao limite sem green;
- registrar testes passando, total e falhando;
- identificar integrante, kata e tratamento (`com_ia` ou `sem_ia`);
- acrescentar cada resultado ao CSV sem apagar coletas anteriores.

## Arquivos da entrega

- `lab02/scripts/timer_trial.py`: execução do cronômetro, dos testes e da coleta;
- `lab02/scripts/test_timer_trial.py`: testes automatizados do coletor;
- `lab02/scripts/README.md`: instruções de instalação, execução e conferência;
- `lab02/data/trials.csv`: cabeçalho do arquivo de coleta;
- `README.md`: exemplo rápido de uso na raiz do projeto.

## Decisões importantes

Os arquivos `kata.py` continuam com `NotImplementedError` porque são os objetos do
experimento. Cada integrante deve implementar o kata durante o trial. Deixar as
soluções prontas antes da coleta alteraria o tempo medido e invalidaria o resultado.

Um `Ctrl+C` antes do limite cancela o trial e não grava o CSV. A marcação
`censurado = sim` é usada somente quando o limite configurado termina sem green.

## Conferência realizada

- gabarito de referência: 6 testes passando;
- testes do script: caminho válido e inválido, coleta, kata incompleto, CSV,
  resultado green, resultado censurado e cancelamento;
- total da validação automatizada: 14 testes passando;
- seis pastas de katas reconhecidas, cada uma com seus testes coletados;
- compilação dos arquivos Python concluída sem erro;
- mensagens e instruções revisadas para execução no Windows e em outros sistemas.

## Resultado do Code Review

O script atende à Issue #13 e aos requisitos de coleta do roteiro. O tratamento de
erros agora mostra a saída real do pytest, o nome do kata é validado antes do início,
o limite não pode ultrapassar 35 minutos e interrupções não geram dados inválidos.
Não foram encontradas falhas bloqueantes após a revisão final.
