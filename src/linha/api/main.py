from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from linha.api.routes import router

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

# Rota raiz
@app.get("/")
def root():
    return {"message": "API está online"} 