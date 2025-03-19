# Modelagem de Banco de Dados MongoDB

Este diretório contém a modelagem de banco de dados MongoDB para o sistema de monitoramento de presença em linhas de produção.

## Estrutura

A modelagem está organizada em vários arquivos, cada um representando uma coleção no MongoDB:

### Modelos Implementados:
1. `factories.py` - Fábricas
2. `production_lines.py` - Linhas de Produção
3. `workstations.py` - Postos de Trabalho
4. `cameras.py` - Câmeras
5. `shifts.py` - Turnos
6. `employees.py` - Funcionários
7. `batch_control.py` - Controle de Lotes
8. `batch_detections.py` - Detecções de Lote
9. `allocations.py` - Alocações
10. `daily_detections.py` - Detecções Diárias Agregadas
11. `attendance.py` - Presença
12. `historical_summaries.py` - Resumos Históricos

## Propósito

Esta modelagem foi projetada para:

1. **Aproveitar as Características do MongoDB**:
   - Documentos aninhados para representar hierarquias
   - Desnormalização estratégica para otimizar consultas
   - Resumos pré-calculados para relatórios eficientes

2. **Manter Consistência Estrutural**:
   - Estruturas otimizadas para consultas frequentes
   - Facilita comparação e agregação de dados

3. **Suportar o Fluxo de Processamento**:
   - Controle de lotes para processamento assíncrono
   - Rastreabilidade desde a captura até o registro de presença

4. **Otimizar para Casos de Uso Comuns**:
   - Relatórios de presença por linha, posto, turno ou funcionário
   - Monitoramento em tempo real
   - Análise histórica

## Fluxo de Dados

1. **Configuração da Estrutura Organizacional**:
   - Cadastro de fábricas, linhas de produção e postos de trabalho
   - Configuração de câmeras e mapeamento para postos
   - Definição de turnos

2. **Alocação de Funcionários**:
   - Criação de documentos na coleção `allocations` definindo quem deve trabalhar em cada posto durante cada turno

3. **Captura e Processamento de Imagens**:
   - Câmeras capturam imagens que são organizadas em lotes por linha de produção
   - Lotes são registrados na coleção `batch_control` com status "pending"
   - Workers processam os lotes, detectando e reconhecendo faces
   - Resultados são registrados na coleção `batch_detections`, com IDs únicos para cada detecção

4. **Agregação de Detecções Diárias**:
   - As detecções de todos os lotes do dia são agregadas na coleção `daily_detections`
   - Cada documento representa as detecções em um posto específico durante um turno específico
   - Mantém referências às detecções originais para rastreabilidade

5. **Geração de Registros de Presença**:
   - As detecções diárias são comparadas com as alocações do dia
   - O resultado é armazenado na coleção `attendance`, com um documento por funcionário-posto-turno-data
   - Inclui status como "presente", "ausente", "atrasado" e métricas como minutos de atraso

6. **Geração de Resumos Históricos**:
   - Periodicamente, os dados de presença são agregados em resumos históricos
   - Resumos são armazenados na coleção `historical_summaries` para relatórios eficientes
   - Dados detalhados antigos podem ser removidos automaticamente via TTL

## Observação

Esta modelagem é uma proposta e pode ser ajustada conforme necessário para atender a requisitos específicos ou evoluções futuras do sistema. 