"""
Modelagem da coleção daily_detections (Detecções Diárias)

Propósito: Agrega as detecções de todos os lotes processados em um dia, organizadas por 
posto de trabalho e turno, facilitando a comparação com as alocações.
"""

# Exemplo de documento na coleção daily_detections
daily_detection_schema = {
    "_id": "ObjectId",
    "date": "ISODate",  # Data das detecções (apenas a data)
    "factory_id": "ObjectId",
    "line_id": "ObjectId",
    "workstation_id": "ObjectId",
    "shift_id": "ObjectId",
    
    # Dados desnormalizados para facilitar consultas
    "factory_name": "Nome da Fábrica",
    "line_name": "Linha 1",
    "workstation_name": "Posto A",
    "shift_name": "Turno da Manhã",
    "shift_start": "08:00",
    "shift_end": "16:00",
    
    # Detecções por funcionário
    "employee_detections": [
        {
            "employee_id": "ObjectId",
            "employee_name": "João Silva",
            "detection_count": 15,
            "average_confidence": 0.93,
            "first_detection": {
                "timestamp": "ISODate",
                "camera_id": "ObjectId",
                "camera_name": "Câmera 1",
                "image_path": "caminho/para/imagem.jpg",
                "batch_path": "/caminho/para/lote/linha_1/20230515_0800",
                "detection_id": "ObjectId",  # Referência à detecção original
                "confidence": 0.95
            },
            "last_detection": {
                "timestamp": "ISODate",
                "camera_id": "ObjectId",
                "camera_name": "Câmera 2",
                "image_path": "caminho/para/imagem.jpg",
                "batch_path": "/caminho/para/lote/linha_1/20230515_1530",
                "detection_id": "ObjectId",  # Referência à detecção original
                "confidence": 0.91
            },
            "detections_by_hour": {
                "08": 3,
                "09": 2,
                "10": 1,
                "11": 2,
                "12": 0,  # Almoço
                "13": 1,
                "14": 3,
                "15": 3
            },
            "source_batch_ids": ["batch_id_1", "batch_id_2", "batch_id_3"]
        }
    ],
    
    # Resumo para facilitar consultas
    "summary": {
        "total_employees_detected": 3,
        "total_detections": 45,
        "detection_count_by_hour": {
            "08": 9,
            "09": 6,
            "10": 3,
            "11": 6,
            "12": 0,  # Almoço
            "13": 3,
            "14": 9,
            "15": 9
        },
        "source_batches_count": 10
    },
    
    # Metadados
    "created_at": "ISODate",
    "updated_at": "ISODate",
    "last_batch_processed": "ISODate"
}

"""
Conceito:
- Agregação diária: Consolida todas as detecções de um dia em um único documento
- Organização hierárquica: Estruturado por posto de trabalho e turno
- Detalhado por funcionário: Mantém detalhes de cada funcionário detectado
- Resumo temporal: Inclui distribuição de detecções por hora

Uso Prático:
- Facilita a comparação com alocações para gerar registros de presença
- Permite análise de padrões de presença ao longo do dia
- Reduz a necessidade de consultar múltiplos lotes para relatórios diários
- Serve como fonte para geração de registros oficiais de presença

Exemplo de Cenário:
"No dia 15/05/2023, no Posto A da Linha 1, durante o turno da manhã, o funcionário João Silva 
foi detectado 15 vezes, com a primeira detecção às 08:10 e a última às 15:55. Suas detecções 
estão distribuídas ao longo do dia, com maior frequência nas horas da manhã e final da tarde."
"""

# Índices recomendados para a coleção daily_detections
daily_detection_indexes = [
    {"date": 1, "factory_id": 1},
    {"date": 1, "line_id": 1},
    {"date": 1, "workstation_id": 1, "shift_id": 1},  # Composto
    {"date": 1, "employee_detections.employee_id": 1},  # Para buscar detecções de um funcionário
    {"summary.total_employees_detected": 1}  # Para análises estatísticas
]

# TTL Index para expirar documentos antigos (90 dias)
ttl_index = {
    "created_at": 1,
    "expireAfterSeconds": 7776000  # 90 dias
} 