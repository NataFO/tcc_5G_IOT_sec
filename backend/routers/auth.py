from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from jose import jwt
from datetime import datetime, timedelta
import bcrypt
import os

from models.database import get_db
from schemas.schemas import LoginSchema, TokenSchema

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Configurações do JWT
SECRET_KEY = os.getenv("SECRET_KEY", "chave-secreta-tcc-5g-2026")
ALGORITHM = "HS256"
EXPIRE_MINUTES = 480  # 8 horas

def criar_token(dados: dict) -> str:
    """Gera um token JWT com os dados do usuário."""
    payload = dados.copy()
    expiracao = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    payload.update({"exp": expiracao})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verificar_senha(senha_digitada: str, hash_salvo: str) -> bool:
    """Compara a senha digitada com o hash salvo no banco."""
    return bcrypt.checkpw(
        senha_digitada.encode("utf-8"),
        hash_salvo.encode("utf-8")
    )

@router.post("/login", response_model=TokenSchema)
def login(dados: LoginSchema, db: Session = Depends(get_db)):
    """
    Recebe login e senha, valida no banco e retorna token JWT.
    """
    # Busca o usuário no banco
    query = text("SELECT id_usuario, login, senha_hash, perfil, ativo FROM tb_usuario WHERE login = :login")
    resultado = db.execute(query, {"login": dados.login}).fetchone()

    # Verifica se o usuário existe e está ativo
    if not resultado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login ou senha incorretos"
        )

    if resultado.ativo == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )

    # Verifica a senha
    if not verificar_senha(dados.senha, resultado.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login ou senha incorretos"
        )

    # Gera o token JWT
    token = criar_token({
        "sub": str(resultado.id_usuario),
        "login": resultado.login,
        "perfil": resultado.perfil
    })

    return {"access_token": token, "token_type": "bearer"}