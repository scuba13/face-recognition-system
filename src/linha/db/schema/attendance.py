"""
Modelagem da coleção attendance (Presença)

Propósito: Representa o registro oficial de presença dos funcionários, gerado a partir 
da comparação entre quem deveria estar trabalhando (alocações) e quem foi realmente 
detectado (detecções diárias).
"""

# Exemplo de documento na coleção attendance
attendance_schema = {
    "_id": "ObjectId",
    "date": "ISODate",  # Data da presença
    "factory_id": "ObjectId",
    "line_id": "ObjectId",
    "workstation_id": "ObjectId",
    "shift_id": "ObjectId",
    "employee_id": "ObjectId",
    
    # Dados desnormalizados para facilitar consultas
    "factory_name": "Nome da Fábrica",
    "line_name": "Nome da Linha",
    "workstation_name": "Nome do Posto",
    "shift_name": "Nome do Turno",
    "shift_start": "08:00",
    "shift_end": "16:00",
    "employee_name": "Nome do Funcionário",
    
    # Informações de presença
    "status": "present",  # "present", "absent", "late", "early_departure"
    "expected": True,  # Se o funcionário estava alocado
    "check_in": "ISODate",  # Horário da primeira detecção
    "check_out": "ISODate",  # Horário da última detecção
    "late_minutes": 15,  # Minutos de atraso (se aplicável)
    "early_departure_minutes": 0,  # Minutos de saída antecipada (se aplicável)
    "detection_count": 15,
    "average_confidence": 0.93,
    
    # Detecções relevantes
    "first_detection": {
        "timestamp": "ISODate",
        "camera_id": "ObjectId",
        "camera_name": "Nome da Câmera",
        "image_path": "caminho/para/imagem.jpg",
        "batch_path": "/caminho/para/lote/linha_1/20230515_0800",
        "detection_id": "ObjectId"  # Referência à detecção original
    },
    "last_detection": {
        "timestamp": "ISODate",
        "camera_id": "ObjectId",
        "camera_name": "Nome da Câmera",
        "image_path": "caminho/para/imagem.jpg",
        "batch_path": "/caminho/para/lote/linha_1/20230515_0830",
        "detection_id": "ObjectId"  # Referência à detecção original
    },
    
    # Rastreabilidade
    "source_daily_detection_id": "ObjectId",  # ID da detecção diária que gerou este registro
    "source_allocation_id": "ObjectId",  # ID da alocação correspondente
    
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Registro consolidado: Combina informações de alocações e detecções
- Status derivado: Classifica os funcionários como presentes, ausentes, atrasados, etc.
- Inclui métricas: Contém informações como horário de entrada, saída, atrasos, etc.
- Base para relatórios: Serve como fonte principal para relatórios de presença

Uso Prático:
- Gerado automaticamente pelo sistema após comparar alocações e detecções
- Usado para relatórios gerenciais de presença, pontualidade, etc.
- Serve como registro oficial para fins administrativos e de RH
- Permite análise de tendências de presença ao longo do tempo

Exemplo de Cenário:
"No dia 15/05/2023, na Linha 1, Posto A, durante o turno da manhã, o funcionário João 
estava alocado e foi detectado (presente), chegou às 08:15 (15 minutos atrasado) e 
saiu às 16:00 (pontual na saída)."
"""

# Índices recomendados para a coleção attendance
attendance_indexes = [
    {"date": 1, "factory_id": 1},
    {"date": 1, "line_id": 1},
    {"date": 1, "workstation_id": 1, "shift_id": 1},  # Composto
    {"employee_id": 1, "date": 1},
    {"date": 1, "status": 1},  # Para relatórios de presença/ausência
    {"source_daily_detection_id": 1},
    {"source_allocation_id": 1}
]

# TTL Index para expirar documentos antigos (180 dias)
ttl_index = {
    "created_at": 1,
    "expireAfterSeconds": 15552000  # 180 dias
} 