"""
Modelagem da coleção shifts (Turnos)

Propósito: Representa os turnos de trabalho disponíveis nas fábricas, definindo os horários 
em que os funcionários devem estar presentes.
"""

# Exemplo de documento na coleção shifts
shift_schema = {
    "_id": "ObjectId",
    "factory_id": "ObjectId",  # Referência à fábrica (opcional, pode ser null para turnos globais)
    "name": "Turno da Manhã",
    "code": "T001",  # Código único do turno
    "start_time": "08:00",  # Horário de início (formato HH:MM)
    "end_time": "16:00",  # Horário de término (formato HH:MM)
    "duration_minutes": 480,  # Duração em minutos (8 horas)
    
    # Dados desnormalizados para facilitar consultas
    "factory_name": "Nome da Fábrica",  # Pode ser null para turnos globais
    
    # Tolerâncias
    "late_tolerance_minutes": 15,  # Tolerância para atraso
    "early_departure_tolerance_minutes": 10,  # Tolerância para saída antecipada
    
    # Intervalos
    "breaks": [
        {
            "name": "Almoço",
            "start_time": "12:00",
            "end_time": "13:00",
            "duration_minutes": 60
        },
        {
            "name": "Pausa da Tarde",
            "start_time": "15:00",
            "end_time": "15:15",
            "duration_minutes": 15
        }
    ],
    
    # Dias da semana aplicáveis (0 = Domingo, 6 = Sábado)
    "days_of_week": [1, 2, 3, 4, 5],  # Segunda a Sexta
    
    "active": True,
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Período de trabalho: Define um intervalo de tempo em que funcionários devem trabalhar
- Configurável: Possui horários de início, fim e intervalos
- Tolerâncias: Define limites aceitáveis para atrasos e saídas antecipadas
- Aplicabilidade: Pode ser específico de uma fábrica ou global

Uso Prático:
- Define quando os funcionários devem estar presentes
- Estabelece parâmetros para classificação de presença (pontual, atrasado, etc.)
- Permite configurar diferentes horários para diferentes operações
- Facilita a organização de escalas de trabalho

Exemplo de Cenário:
"O Turno da Manhã vai das 08:00 às 16:00, com intervalo para almoço das 12:00 às 13:00. 
Tem tolerância de 15 minutos para atraso e 10 minutos para saída antecipada. É aplicável 
de segunda a sexta-feira em todas as fábricas."
"""

# Índices recomendados para a coleção shifts
shift_indexes = [
    {"factory_id": 1},  # Para buscar turnos de uma fábrica
    {"code": 1},  # Único, para busca por código
    {"days_of_week": 1},  # Para buscar turnos por dia da semana
    {"active": 1}  # Para filtrar apenas turnos ativos
] 