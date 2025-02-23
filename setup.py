from setuptools import setup, find_packages

setup(
    name="linha",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # API
        "fastapi>=0.109.0",
        "python-multipart>=0.0.6",
        "uvicorn>=0.27.0",
        
        # Interface
        "streamlit>=1.29.0",
        "Pillow>=10.1.0",
        "streamlit-webrtc>=0.47.1",
        
        # Banco de dados
        "pymongo>=4.6.1",
        
        # Processamento de imagens
        "face-recognition>=1.3.0",
        "opencv-python>=4.8.1.78",
        "numpy>=1.26.3",
        
        # Utilitários
        "python-dotenv>=1.0.0",
        "colorlog>=6.8.0",
        "requests>=2.31.0",
        "psutil>=5.9.8",
        "backoff>=2.2.1",
        "colorama>=0.4.6",
        
        # Visualização
        "plotly>=5.18.0",
        "pandas>=1.5.3"
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "pytest-cov>=4.1.0",
        ]
    },
    python_requires=">=3.9",
) 