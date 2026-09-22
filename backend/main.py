from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Importa os routers
from routers.auth import router as auth_router
from routers.logs import router as logs_router
from routers.alertas import router as alertas_router
from routers.dispositivos import router as dispositivos_router

# Inicializa o FastAPI
app = FastAPI(
    title="API - Segurança Cibernética 5G com IA",
    description="Sistema de detecção de ataques em infraestruturas 5G usando LSTM",
    version="1.0.0"
)

# Configura o CORS — permite que o frontend React acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra os routers
app.include_router(auth_router)
app.include_router(logs_router)
app.include_router(alertas_router)
app.include_router(dispositivos_router)

# Endpoint de verificação de saúde do servidor
@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "sistema": "Segurança Cibernética 5G com IA",
        "versao": "1.0.0"
    }