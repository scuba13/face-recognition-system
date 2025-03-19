"""
Modelagem da coleção workstations (Postos de Trabalho)

Propósito: Representa os postos de trabalho dentro de uma linha de produção, sendo o terceiro nível 
na hierarquia organizacional do sistema.
"""

# Exemplo de documento na coleção workstations
workstation_schema = {
    "_id": "ObjectId",
    "factory_id": "ObjectId",  # Referência à fábrica
    "line_id": "ObjectId",  # Referência à linha de produção
    "name": "Posto A",
    "code": "P001",  # Código único do posto
    "description": "Posto de montagem inicial",
    "position": 1,  # Posição sequencial na linha (1, 2, 3...)
    
    # Dados desnormalizados para facilitar consultas
    "factory_name": "Nome da Fábrica",
    "factory_code": "FAB001",
    "line_name": "Linha 1",
    "line_code": "L001",
    
    # Configurações específicas do posto
    "capacity": 2,  # Número de funcionários que podem trabalhar simultaneamente
    "requires_certification": False,  # Se requer certificação específica
    "active": True,
    
    # Metadados
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Estação de trabalho: Representa um local específico onde uma ou mais pessoas trabalham
- Hierarquia: Pertence a uma linha de produção dentro de uma fábrica
- Sequencial: Possui uma posição na sequência da linha de produção
- Monitorado: É monitorado por uma ou mais câmeras

Uso Prático:
- Define onde os funcionários devem estar alocados
- Permite monitorar presença em locais específicos
- Facilita a identificação de gargalos ou problemas em pontos específicos da linha

Exemplo de Cenário:
"O Posto A é o primeiro posto da Linha 1 na Fábrica Matriz. Tem capacidade para 2 funcionários 
trabalhando simultaneamente e é monitorado por 2 câmeras. Os relatórios de presença podem ser 
filtrados por este posto específico."
"""

# Índices recomendados para a coleção workstations
workstation_indexes = [
    {"line_id": 1},  # Para buscar postos de uma linha
    {"factory_id": 1, "line_id": 1},  # Composto para busca por fábrica e linha
    {"factory_id": 1, "line_id": 1, "position": 1},  # Para ordenar por posição
    {"code": 1},  # Único, para busca por código
    {"active": 1}  # Para filtrar apenas postos ativos
] 