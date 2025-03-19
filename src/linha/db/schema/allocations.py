"""
Modelagem da coleção allocations (Alocações)

Propósito: Representa o planejamento ou a programação de quem deveria estar trabalhando 
em cada posto durante cada turno. É essencialmente a escala de trabalho oficial.
"""

# Exemplo de documento na coleção allocations
allocation_schema = {
    "_id": "ObjectId",
    "date": "ISODate",  # Data da alocação
    "factory_id": "ObjectId",
    "line_id": "ObjectId",
    "workstation_id": "ObjectId",
    "shift_id": "ObjectId",
    
    # Dados desnormalizados para facilitar consultas
    "factory_name": "Nome da Fábrica",
    "line_name": "Nome da Linha",
    "workstation_name": "Nome do Posto",
    "shift_name": "Nome do Turno",
    "shift_start": "08:00",
    "shift_end": "16:00",
    
    # Lista de funcionários alocados
    "employees": [
        {
            "employee_id": "ObjectId",
            "employee_name": "Nome do Funcionário",
            "status": "active"  # "active", "inactive"
        }
    ],
    
    "is_recurring": False,  # Se é uma alocação recorrente
    "recurrence_pattern": {  # Apenas se is_recurring = True
        "start_date": "ISODate",
        "end_date": "ISODate",  # Opcional
        "days_of_week": [1, 2, 3, 4, 5]  # 0-6 (domingo a sábado)
    },
    "status": "active",  # "active", "inactive"
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Planejamento prévio: Define quais funcionários estão designados para trabalhar em quais postos durante quais turnos
- Expectativa: Representa o que é esperado, não o que realmente aconteceu
- Pode ser recorrente: Uma alocação pode ser configurada para se repetir em determinados dias da semana

Uso Prático:
- Gerentes de linha definem quais funcionários trabalharão em quais postos durante quais turnos
- Serve como base para comparar com as detecções reais e identificar ausências, atrasos, etc.
- Permite planejar a cobertura adequada de todos os postos em todos os turnos

Exemplo de Cenário:
"Para o dia 15/05/2023, na Linha 1, Posto A, durante o turno da manhã (08:00-16:00), 
os funcionários João e Maria estão alocados para trabalhar."
"""

# Índices recomendados para a coleção allocations
allocation_indexes = [
    {"date": 1, "factory_id": 1},
    {"date": 1, "line_id": 1},
    {"date": 1, "workstation_id": 1, "shift_id": 1},  # Composto
    {"employees.employee_id": 1, "date": 1},
    {"is_recurring": 1, "recurrence_pattern.days_of_week": 1}  # Para alocações recorrentes
] 