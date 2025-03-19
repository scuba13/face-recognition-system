"""
Modelagem da coleção batch_detections (Detecções de Lote)

Propósito: Armazena os resultados do processamento de um lote específico de imagens 
capturadas por câmeras em uma linha de produção. Representa o resultado bruto do 
reconhecimento facial.
"""

# Exemplo de documento na coleção batch_detections
batch_detection_schema = {
    "_id": "ObjectId",
    "batch_id": "ObjectId",  # Referência ao lote em batch_control
    "batch_path": "/caminho/para/lote/linha_1/20230515_0800",
    "date": "ISODate",  # Data do lote (apenas a data)
    "timestamp": "ISODate",  # Timestamp completo de processamento
    "capture_datetime": "ISODate",  # Timestamp de captura do lote
    "processed_at": "ISODate",  # Timestamp de conclusão do processamento
    "processor_id": "worker-1",
    "factory_id": "ObjectId",
    "factory_name": "Nome da Fábrica",  # Desnormalizado
    "line_id": "ObjectId",
    "line_name": "Nome da Linha",
    
    # Detecções por posto e turno
    "workstation_detections": [
        {
            "workstation_id": "ObjectId",
            "workstation_name": "Nome do Posto",
            "shift_id": "ObjectId",
            "shift_name": "Nome do Turno",
            "employee_detections": [
                {
                    "detection_id": "ObjectId",  # ID único para rastreabilidade
                    "employee_id": "ObjectId",
                    "employee_name": "Nome do Funcionário",
                    "timestamp": "ISODate",
                    "camera_id": "ObjectId",
                    "camera_name": "Nome da Câmera",
                    "image_path": "caminho/para/imagem.jpg",
                    "confidence": 0.95
                }
            ]
        }
    ],
    
    # Informações técnicas do processamento
    "total_images": 10,
    "processing_time": 5.2,  # Tempo de processamento em segundos
    "total_faces_detected": 8,
    "total_faces_recognized": 6,
    "total_faces_unknown": 2,
    "unique_people_recognized": 3,
    "unique_people_unknown": 2,
    "preprocessing_enabled": True,
    "capture_type": "interval",  # "interval" ou "motion"
    
    # Resumo para facilitar consultas
    "summary": {
        "total_workstations": 2,
        "total_shifts": 1,
        "total_employees_detected": 3,
        "detection_count_by_workstation": {
            "workstation_id_1": 4,
            "workstation_id_2": 2
        },
        "detection_count_by_shift": {
            "shift_id_1": 6
        }
    },
    
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Resultado de processamento: Contém os resultados do processamento de reconhecimento facial de um lote de imagens
- Específico por linha: Cada documento representa o processamento de um lote de imagens de uma linha específica
- Organizado hierarquicamente: Os resultados são organizados por posto → turno → funcionário
- Contém metadados técnicos: Inclui informações sobre o processamento, como tempo, número de faces detectadas, etc.

Uso Prático:
- Gerado automaticamente pelo sistema de processamento de imagens
- Serve como fonte de dados para agregação em detecções diárias
- Permite rastrear detecções específicas até as imagens originais
- Fornece métricas técnicas sobre o desempenho do sistema de reconhecimento facial

Exemplo de Cenário:
"No lote de imagens capturado às 08:00 do dia 15/05/2023 na Linha 1, o sistema processou 10 imagens, 
detectou 8 faces, reconheceu 6 delas como funcionários conhecidos, e identificou o funcionário João 
3 vezes no Posto A durante o turno da manhã."
"""

# Índices recomendados para a coleção batch_detections
batch_detection_indexes = [
    {"batch_id": 1},  # Único
    {"batch_path": 1},  # Único
    {"line_id": 1, "date": 1},
    {"workstation_detections.workstation_id": 1, "date": 1},
    {"workstation_detections.employee_detections.detection_id": 1},  # Único
    {"workstation_detections.employee_detections.employee_id": 1, "date": 1}
]

# TTL Index para expirar documentos antigos (30 dias)
ttl_index = {
    "created_at": 1,
    "expireAfterSeconds": 2592000  # 30 dias
} 