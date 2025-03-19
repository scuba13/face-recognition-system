"""
Modelagem da coleção production_lines (Linhas de Produção)

Propósito: Representa as linhas de produção dentro de uma fábrica, sendo o segundo nível 
na hierarquia organizacional do sistema.
"""

# Exemplo de documento na coleção production_lines
production_line_schema = {
    "_id": "ObjectId",
    "factory_id": "ObjectId",  # Referência à fábrica
    "name": "Linha 1",
    "code": "L001",  # Código único da linha
    "description": "Linha de montagem principal",
    
    # Dados desnormalizados para facilitar consultas
    "factory_name": "Nome da Fábrica",
    "factory_code": "FAB001",
    
    # Configurações específicas da linha
    "capture_interval": 300,  # Intervalo de captura em segundos (5 minutos)
    "motion_detection": True,  # Se a detecção de movimento está ativada
    "active": True,
    
    # Metadados
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Unidade de produção: Representa uma linha de montagem ou produção específica
- Hierarquia: Pertence a uma fábrica e contém postos de trabalho
- Configurável: Possui configurações específicas para captura de imagens

Uso Prático:
- Organiza o fluxo de trabalho dentro de uma fábrica
- Permite configurar parâmetros de captura específicos por linha
- Facilita o monitoramento e relatórios por linha de produção

Exemplo de Cenário:
"A Linha 1 da Fábrica Matriz possui 5 postos de trabalho e está configurada para capturar 
imagens a cada 5 minutos, além de capturar quando detecta movimento. Todos os relatórios 
podem ser filtrados por esta linha específica."
"""

# Índices recomendados para a coleção production_lines
production_line_indexes = [
    {"factory_id": 1},  # Para buscar linhas de uma fábrica
    {"factory_id": 1, "name": 1},  # Composto para busca por fábrica e nome
    {"code": 1},  # Único, para busca por código
    {"active": 1}  # Para filtrar apenas linhas ativas
] 