"""
Modelagem da coleção batch_control (Controle de Lotes)

Propósito: Gerencia o processamento de lotes de imagens capturadas pelas câmeras, 
controlando o fluxo desde a captura até o processamento completo.
"""

# Exemplo de documento na coleção batch_control
batch_control_schema = {
    "_id": "ObjectId",
    "batch_id": "20230515_0800_L001",  # ID único do lote (timestamp + linha)
    "batch_path": "/caminho/para/lote/linha_1/20230515_0800",
    "date": "ISODate",  # Data do lote (apenas a data)
    "timestamp": "ISODate",  # Timestamp completo de criação
    "factory_id": "ObjectId",
    "line_id": "ObjectId",
    
    # Dados desnormalizados para facilitar consultas
    "factory_name": "Nome da Fábrica",
    "line_name": "Linha 1",
    
    # Informações do lote
    "capture_type": "interval",  # "interval" ou "motion"
    "total_images": 10,
    "total_cameras": 2,
    "cameras": [
        {
            "camera_id": "ObjectId",
            "camera_name": "Câmera 1",
            "image_count": 5
        },
        {
            "camera_id": "ObjectId",
            "camera_name": "Câmera 2",
            "image_count": 5
        }
    ],
    
    # Status de processamento
    "status": "pending",  # "pending", "processing", "completed", "error"
    "processor_id": null,  # ID do worker que está processando o lote
    "processing_started_at": null,  # Timestamp de início do processamento
    "processing_completed_at": null,  # Timestamp de conclusão do processamento
    "processing_time": null,  # Tempo de processamento em segundos
    "error": null,  # Mensagem de erro, se houver
    "retry_count": 0,  # Número de tentativas de processamento
    
    # Metadados
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Unidade de processamento: Representa um conjunto de imagens capturadas em um momento específico
- Controle de fluxo: Gerencia o estado do processamento de cada lote
- Específico por linha: Cada lote pertence a uma linha de produção específica
- Rastreável: Mantém informações sobre o processamento e possíveis erros

Uso Prático:
- Coordena o processamento assíncrono de imagens
- Permite monitorar o status de cada lote
- Facilita a identificação e resolução de problemas
- Possibilita a distribuição de carga entre múltiplos workers

Exemplo de Cenário:
"Um lote de 10 imagens foi capturado às 08:00 do dia 15/05/2023 na Linha 1, com 5 imagens 
da Câmera 1 e 5 imagens da Câmera 2. O lote está com status 'pending', aguardando processamento 
por um worker disponível."
"""

# Índices recomendados para a coleção batch_control
batch_control_indexes = [
    {"batch_id": 1},  # Único, para busca por ID do lote
    {"batch_path": 1},  # Único, para busca por caminho do lote
    {"line_id": 1, "date": 1},  # Para buscar lotes de uma linha em uma data
    {"status": 1},  # Para filtrar por status
    {"processor_id": 1, "status": 1},  # Para buscar lotes de um processador
    {"created_at": 1}  # Para ordenar por data de criação
]

# TTL Index para expirar documentos antigos (7 dias)
ttl_index = {
    "created_at": 1,
    "expireAfterSeconds": 604800  # 7 dias
} 