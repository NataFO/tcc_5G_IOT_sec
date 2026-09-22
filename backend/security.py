"""
Dependência de autenticação JWT — exige um token válido nas rotas
protegidas (dispositivos, logs, alertas), completando o RF05 / CT13.

O POST /auth/login (routers/auth.py) já gera o token com SECRET_KEY e
ALGORITHM abaixo; este módulo só faz o caminho inverso: ler o header
"Authorization: Bearer <token>", decodificar e validar.
"""
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "chave-secreta-tcc-5g-2026")
ALGORITHM = "HS256"

# tokenUrl só é usado pelo botão "Authorize" do Swagger/OpenAPI para
# saber onde buscar o token; o frontend React já envia o header
# "Authorization: Bearer <token>" manualmente em toda chamada (src/api.js).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Valida o token JWT enviado no header Authorization.

    Levanta 401 se o header estiver ausente, o token for inválido,
    tiver assinatura incorreta ou estiver expirado (claim "exp").

    Retorna o payload decodificado (sub, login, perfil), disponível
    para as rotas que quiserem checar o usuário autenticado ou, no
    futuro, o perfil de acesso (admin/analista/viewer — RF05/CT13).
    """
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credenciais_invalidas

    if payload.get("sub") is None:
        raise credenciais_invalidas

    return payload
