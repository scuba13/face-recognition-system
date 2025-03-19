"""
Modelagem da coleção cameras (Câmeras)

Propósito: Representa as câmeras instaladas nos postos de trabalho, responsáveis pela 
captura de imagens para o reconhecimento facial.
"""

# Exemplo de documento na coleção cameras
camera_schema = {
    "_id": "ObjectId",
    "factory_id": "ObjectId",  # Referência à fábrica
    "line_id": "ObjectId",  # Referência à linha de produção
    "workstation_id": "ObjectId",  # Referência ao posto de trabalho
    "name": "Câmera 1",
    "code": "CAM001",  # Código único da câmera
    "ip_address": "192.168.1.100",
    "mac_address": "00:11:22:33:44:55",
    "model": "IP Cam Pro 4K",
    "manufacturer": "CamTech",
    
    # Dados desnormalizados para facilitar consultas
    "factory_name": "Nome da Fábrica",
    "line_name": "Linha 1",
    "workstation_name": "Posto A",
    
    # Configurações da câmera
    "resolution": "1920x1080",
    "fps": 30,
    "rtsp_url": "rtsp://admin:password@192.168.1.100:554/stream",
    "username": "admin",
    "password": "password",  # Em produção, deve ser criptografado
    "angle": "frontal",  # "frontal", "lateral", "superior"
    "position": "left",  # "left", "right", "center"
    
    # Status e monitoramento
    "status": "active",  # "active", "inactive", "maintenance", "error"
    "last_connection": "ISODate",
    "last_capture": "ISODate",
    "error_count": 0,
    "last_error": null,
    
    # Metadados
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Dispositivo de captura: Representa uma câmera física instalada em um posto de trabalho
- Fonte de dados: Captura imagens que serão processadas para reconhecimento facial
- Monitorada: Seu status é monitorado para garantir funcionamento contínuo
- Configurável: Possui parâmetros específicos de captura e conexão

Uso Prático:
- Fornece imagens para o sistema de reconhecimento facial
- Permite monitorar múltiplos ângulos de um mesmo posto
- Facilita a identificação de problemas de captura
- Possibilita configurações específicas por câmera

Exemplo de Cenário:
"A Câmera 1 está instalada no Posto A da Linha 1, capturando imagens frontais dos funcionários. 
Está configurada para resolução Full HD a 30 FPS e transmite via RTSP. Seu status é monitorado 
continuamente para garantir o funcionamento adequado."
"""

# Índices recomendados para a coleção cameras
camera_indexes = [
    {"workstation_id": 1},  # Para buscar câmeras de um posto
    {"line_id": 1},  # Para buscar câmeras de uma linha
    {"factory_id": 1},  # Para buscar câmeras de uma fábrica
    {"ip_address": 1},  # Para busca por IP
    {"mac_address": 1},  # Para busca por MAC
    {"code": 1},  # Único, para busca por código
    {"status": 1}  # Para filtrar por status
] 