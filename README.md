# Sistema de Reconhecimento Facial

Sistema para reconhecimento facial em linhas de produção usando múltiplas câmeras (USB e IP).

## Funcionalidades

- Captura de imagens de múltiplas câmeras
- Reconhecimento facial em tempo real
- Suporte a câmeras USB e IP
- Processamento em lotes
- Interface web para gerenciamento
- Relatórios de presença

## Requisitos

- Python 3.9+
- MongoDB
- OpenCV
- Docker (opcional)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/face-recognition-system.git
```

2. Instale as dependências:
```bash
cd face-recognition-system/backend
pip install -r requirements.txt
```

3. Configure o arquivo config.py com suas configurações

4. Execute:
```bash
python main.py
```

## Usando com Docker

```bash
docker-compose up -d
```

