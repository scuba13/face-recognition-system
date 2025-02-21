# Linha - Sistema de Reconhecimento Facial

Sistema de reconhecimento facial para monitoramento de linhas de produção.

## 🚀 Requisitos

- Python 3.9+
- Docker e Docker Compose
- OpenCV
- MongoDB

## 📦 Estrutura do Projeto

```
Linha/
├── src/
│   └── linha/
│       ├── core/          # Módulos principais
│       ├── db/           # Banco de dados
│       ├── utils/        # Utilitários
│       └── config/       # Configurações
├── data/                # Dados e imagens
├── docker-compose.yml   # Configuração Docker
└── requirements.txt     # Dependências Python
```

## ⚙️ Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd Linha
```

2. Crie e ative um ambiente virtual:
```bash
# Criar venv
python -m venv venv

# Ativar (Mac/Linux)
source venv/bin/activate
# ou Windows
# venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
pip install -e .
```

4. Inicie o MongoDB:
```bash
docker compose up -d
```

5. Crie as pastas necessárias:
```bash
mkdir -p data/captured_images
mkdir -p data/employees
mkdir -p data/failed_batches
```

## 🎯 Uso

1. Inicie a aplicação:
```bash
python src/linha/main.py
```

A aplicação irá:
- Iniciar a captura de imagens das câmeras configuradas
- Processar as imagens em busca de faces
- Registrar as detecções no MongoDB
- Capturar imagens das câmeras configuradas
- Processar as imagens em busca de faces
- Registrar as detecções no MongoDB
- Remover automaticamente as imagens após processamento

## 📝 Configuração

### Câmeras

Configure as câmeras no arquivo `src/linha/config/settings.py`:

```python
PRODUCTION_LINES = {
    "linha_1": [
        {
            "type": "usb",
            "id": 0,  # ID da câmera
            "name": "Webcam Principal",
            "resolution": (1280, 960),
            "fps": 5,
            "position": "entrada"
        }
    ]
}
```

### MongoDB

O MongoDB roda em container Docker com as seguintes configurações:
- URL: mongodb://localhost:27017/
- Database: face_recognition_db

## 🔍 Monitoramento

- Logs coloridos no console mostram o status da aplicação
- Interface web do MongoDB Express: http://localhost:8081
  - Usuário: admin
  - Senha: admin123

## 🛠️ Desenvolvimento

Para instalar em modo desenvolvimento:
```bash
pip install -e .
```

## 📄 Licença

Este projeto está sob a licença MIT.

