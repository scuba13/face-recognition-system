"""
Modelagem da coleção factories (Fábricas)

Propósito: Representa as fábricas ou unidades produtivas da empresa, sendo o nível mais alto 
na hierarquia organizacional do sistema.
"""

# Exemplo de documento na coleção factories
factory_schema = {
    "_id": "ObjectId",
    "name": "Nome da Fábrica",
    "code": "FAB001",  # Código único da fábrica
    "address": {
        "street": "Rua Exemplo",
        "number": "123",
        "district": "Bairro Industrial",
        "city": "Cidade",
        "state": "Estado",
        "country": "País",
        "postal_code": "12345-678"
    },
    "contact": {
        "phone": "+55 11 1234-5678",
        "email": "contato@fabrica.com"
    },
    "location": {
        "type": "Point",
        "coordinates": [-46.123456, -23.123456]  # [longitude, latitude]
    },
    "timezone": "America/Sao_Paulo",
    "active": True,
    "created_at": "ISODate",
    "updated_at": "ISODate"
}

"""
Conceito:
- Unidade organizacional: Representa uma unidade física da empresa onde ocorre produção
- Nível superior: É o nível mais alto na hierarquia organizacional do sistema
- Contém linhas de produção: Cada fábrica pode ter múltiplas linhas de produção

Uso Prático:
- Permite organizar e filtrar dados por fábrica
- Facilita a gestão de múltiplas unidades produtivas
- Possibilita configurações específicas por fábrica (como fuso horário)

Exemplo de Cenário:
"A Fábrica Matriz, localizada em São Paulo, possui 3 linhas de produção e opera no fuso horário 
de Brasília. Todos os relatórios e configurações podem ser filtrados por esta unidade."
"""

# Índices recomendados para a coleção factories
factory_indexes = [
    {"name": 1},  # Para busca por nome
    {"code": 1},  # Único, para busca por código
    {"active": 1},  # Para filtrar apenas fábricas ativas
    {"location": "2dsphere"}  # Índice geoespacial para consultas de localização
] 