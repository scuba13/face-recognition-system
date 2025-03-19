"""
Modelagem da coleção historical_summaries (Resumos Históricos)

Propósito: Armazena resumos agregados de dados históricos de presença para consultas 
eficientes de longo prazo, sem necessidade de acessar os dados detalhados.
"""

# Exemplo de documento na coleção historical_summaries
historical_summary_schema = {
    "_id": "ObjectId",
    "summary_type": "monthly",  # "daily", "weekly", "monthly", "quarterly", "yearly"
    "period": "2023-05",  # Formato depende do tipo: YYYY-MM-DD, YYYY-WW, YYYY-MM, YYYY-QQ, YYYY
    "start_date": "ISODate",
    "end_date": "ISODate",
    "factory_id": "ObjectId",  # Opcional, pode ser null para resumos globais
    "line_id": "ObjectId",  # Opcional, pode ser null para resumos de fábrica
    "workstation_id": "ObjectId",  # Opcional, pode ser null para resumos de linha
    
    # Dados desnormalizados para facilitar consultas
    "factory_name": "Nome da Fábrica",  # Pode ser null para resumos globais
    "line_name": "Linha 1",  # Pode ser null para resumos de fábrica
    "workstation_name": "Posto A",  # Pode ser null para resumos de linha
    
    # Métricas de presença
    "attendance_metrics": {
        "total_allocations": 120,
        "total_present": 110,
        "total_absent": 10,
        "total_late": 15,
        "total_early_departure": 5,
        "average_late_minutes": 12.5,
        "average_early_departure_minutes": 8.2,
        "presence_rate": 0.917,  # 110/120
        "punctuality_rate": 0.864  # (110-15)/110
    },
    
    # Métricas por turno
    "shift_metrics": [
        {
            "shift_id": "ObjectId",
            "shift_name": "Turno da Manhã",
            "total_allocations": 60,
            "total_present": 55,
            "total_absent": 5,
            "presence_rate": 0.917
        },
        {
            "shift_id": "ObjectId",
            "shift_name": "Turno da Tarde",
            "total_allocations": 60,
            "total_present": 55,
            "total_absent": 5,
            "presence_rate": 0.917
        }
    ],
    
    # Métricas por funcionário (top 10 por presença e top 10 por ausência)
    "employee_metrics": {
        "top_presence": [
            {
                "employee_id": "ObjectId",
                "employee_name": "João Silva",
                "total_allocations": 20,
                "total_present": 20,
                "presence_rate": 1.0
            }
        ],
        "top_absence": [
            {
                "employee_id": "ObjectId",
                "employee_name": "Maria Souza",
                "total_allocations": 20,
                "total_absent": 5,
                "absence_rate": 0.25
            }
        ]
    },
    
    # Tendências (comparação com períodos anteriores)
    "trends": {
        "presence_rate_change": 0.02,  # Aumento de 2% em relação ao período anterior
        "punctuality_rate_change": -0.01,  # Redução de 1% em relação ao período anterior
        "average_late_minutes_change": -2.5  # Redução de 2.5 minutos em relação ao período anterior
    },
    
    # Metadados
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Agregação histórica: Consolida dados de presença em períodos específicos
- Hierárquico: Pode ser global, por fábrica, por linha ou por posto
- Estatístico: Contém métricas e tendências para análise
- Otimizado: Projetado para consultas rápidas de relatórios históricos

Uso Prático:
- Fornece dados para dashboards gerenciais
- Permite análise de tendências ao longo do tempo
- Facilita a identificação de padrões e problemas recorrentes
- Reduz a carga no banco de dados ao evitar agregações em tempo real

Exemplo de Cenário:
"O resumo mensal de maio de 2023 para a Linha 1 mostra uma taxa de presença de 91.7%, 
com 110 presenças e 10 ausências. Houve um aumento de 2% na taxa de presença em relação 
ao mês anterior, mas uma redução de 1% na pontualidade."
"""

# Índices recomendados para a coleção historical_summaries
historical_summary_indexes = [
    {"summary_type": 1, "period": 1},  # Para buscar por tipo e período
    {"factory_id": 1, "summary_type": 1, "period": 1},  # Para buscar por fábrica
    {"line_id": 1, "summary_type": 1, "period": 1},  # Para buscar por linha
    {"workstation_id": 1, "summary_type": 1, "period": 1},  # Para buscar por posto
    {"start_date": 1, "end_date": 1}  # Para buscar por intervalo de datas
] 