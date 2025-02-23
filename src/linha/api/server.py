from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from linha.api.routes import router
import uvicorn

def start_api_server(ready_event=None):
    """Inicia servidor API"""
    # Criar aplicação FastAPI
    app = FastAPI(title="Linha API")
    
    # Configurar CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Registrar rotas
    print("\n=== Configurando API ===")
    print("Registrando rotas:")
    app.include_router(router)
    for route in router.routes:
        print(f"- {route.path}")
    
    # Evento quando servidor estiver pronto
    @app.on_event("startup")
    async def startup_event():
        if ready_event:
            ready_event.set()
    
    # Iniciar servidor
    uvicorn.run(app, host="0.0.0.0", port=8000) 