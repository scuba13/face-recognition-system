"""
Modelagem da coleção employees (Funcionários)

Propósito: Representa os funcionários da empresa, incluindo seus dados pessoais e 
as características faciais para reconhecimento.
"""

# Exemplo de documento na coleção employees
employee_schema = {
    "_id": "ObjectId",
    "employee_id": "12345",  # ID do funcionário no sistema de RH
    "name": "João Silva",
    "email": "joao.silva@empresa.com",
    "phone": "+55 11 98765-4321",
    "position": "Operador de Linha",
    "department": "Produção",
    
    # Dados de acesso (opcional, se o funcionário tiver acesso ao sistema)
    "user_id": "ObjectId",  # Referência ao usuário no sistema de autenticação
    
    # Dados para reconhecimento facial
    "face_encoding": [0.1, -0.2, 0.3, ...],  # Vetor de características faciais (128 dimensões)
    "face_images": [
        {
            "image_path": "/storage/faces/12345/face_1.jpg",
            "captured_at": "ISODate",
            "quality_score": 0.95,
            "is_primary": True
        },
        {
            "image_path": "/storage/faces/12345/face_2.jpg",
            "captured_at": "ISODate",
            "quality_score": 0.87,
            "is_primary": False
        }
    ],
    "last_encoding_update": "ISODate",
    "encoding_quality": 0.92,
    
    # Certificações e habilidades
    "certifications": [
        {
            "name": "Operação de Máquina X",
            "issued_date": "ISODate",
            "expiry_date": "ISODate",
            "issuer": "Departamento de Treinamento"
        }
    ],
    
    # Histórico de alocações frequentes
    "common_allocations": [
        {
            "factory_id": "ObjectId",
            "line_id": "ObjectId",
            "workstation_id": "ObjectId",
            "shift_id": "ObjectId",
            "frequency": 0.8  # Porcentagem de vezes alocado a este posto
        }
    ],
    
    "status": "active",  # "active", "inactive", "on_leave", "terminated"
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Pessoa: Representa um funcionário da empresa
- Reconhecível: Possui dados biométricos para reconhecimento facial
- Alocável: Pode ser alocado a postos de trabalho em turnos específicos
- Rastreável: Sua presença é monitorada pelo sistema

Uso Prático:
- Armazena dados necessários para reconhecimento facial
- Mantém informações de contato e função
- Registra certificações e habilidades relevantes
- Facilita a alocação baseada em histórico e competências

Exemplo de Cenário:
"João Silva é um Operador de Linha no departamento de Produção. Possui certificação para 
operar a Máquina X e geralmente é alocado ao Posto A da Linha 1 durante o turno da manhã. 
Seu rosto está registrado no sistema com alta qualidade para reconhecimento facial."
"""

# Índices recomendados para a coleção employees
employee_indexes = [
    {"employee_id": 1},  # Único, para busca por ID do funcionário
    {"name": 1},  # Para busca por nome
    {"email": 1},  # Único, para busca por email
    {"position": 1},  # Para busca por cargo
    {"department": 1},  # Para busca por departamento
    {"status": 1},  # Para filtrar por status
    {"certifications.name": 1},  # Para busca por certificação
    {"common_allocations.workstation_id": 1}  # Para busca por alocação comum
] 