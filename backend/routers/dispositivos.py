from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError

from models.database import get_db
from schemas.schemas import DispositivoCreate, DispositivoResponse
from security import get_current_user, exigir_perfil

# dependencies=[...] exige um token JWT válido em TODAS as rotas deste
# router (RF05 / CT13) — quem chamar sem "Authorization: Bearer <token>"
# ou com token expirado/inválido recebe 401 antes de a função rodar.
def _executar_gravacao(db: Session, query, params: dict):
    """
    Executa um INSERT/UPDATE em tb_dispositivo e traduz os erros do banco
    em respostas HTTP claras. Sem isso, um IP repetido ou inválido virava
    um erro 500 genérico — e, no navegador, só "Failed to fetch" (a resposta
    de erro 500 sai sem os cabeçalhos de CORS). Encontrado no teste CT06.
    """
    try:
        resultado = db.execute(query, params)
        # Lê o resultado ANTES do commit: depois do commit a conexão volta ao pool e,
        # com requisições simultâneas, outra requisição pode pegá-la e fechar este
        # cursor ("cursor already closed" — achado no teste de carga CT09).
        linha = resultado.fetchone()
        db.commit()
        return linha
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Já existe um dispositivo cadastrado com o IP {params.get('ip_address')}.",
        )
    except DataError:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"Endereço IP inválido: {params.get('ip_address')!r}.",
        )


router = APIRouter(
    prefix="/dispositivos",
    tags=["Dispositivos IoT"],
    dependencies=[Depends(get_current_user)],
)

@router.post("/", response_model=DispositivoResponse, dependencies=[Depends(exigir_perfil("admin"))])
def cadastrar_dispositivo(dados: DispositivoCreate, db: Session = Depends(get_db)):
    """
    Cadastra um novo dispositivo IoT no sistema (UC04).
    """
    query = text("""
        INSERT INTO tb_dispositivo (
            nome_dispositivo,
            tipo,
            ip_address,
            gnodeb_associado,
            status
        ) VALUES (
            :nome_dispositivo,
            :tipo,
            :ip_address,
            :gnodeb_associado,
            'ativo'
        ) RETURNING *
    """)

    dispositivo = _executar_gravacao(db, query, {
        "nome_dispositivo": dados.nome_dispositivo,
        "tipo":             dados.tipo,
        "ip_address":       dados.ip_address,
        "gnodeb_associado": dados.gnodeb_associado
    })
    return dict(dispositivo._mapping)

@router.get("/")
def listar_dispositivos(db: Session = Depends(get_db)):
    """Retorna todos os dispositivos cadastrados."""
    query = text("""
        SELECT * FROM tb_dispositivo
        ORDER BY registrado_em DESC
    """)
    dispositivos = db.execute(query).fetchall()
    return [dict(d._mapping) for d in dispositivos]

@router.get("/{id_dispositivo}")
def buscar_dispositivo(id_dispositivo: int, db: Session = Depends(get_db)):
    """Retorna um dispositivo específico pelo ID."""
    query = text("""
        SELECT * FROM tb_dispositivo
        WHERE id_dispositivo = :id_dispositivo
    """)
    dispositivo = db.execute(query, {"id_dispositivo": id_dispositivo}).fetchone()

    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

    return dict(dispositivo._mapping)

@router.patch("/{id_dispositivo}", dependencies=[Depends(exigir_perfil("admin"))])
def atualizar_dispositivo(
    id_dispositivo: int,
    dados: DispositivoCreate,
    db: Session = Depends(get_db)
):
    """Atualiza os dados de um dispositivo existente (UC04)."""
    query = text("""
        UPDATE tb_dispositivo
        SET nome_dispositivo = :nome_dispositivo,
            tipo             = :tipo,
            ip_address       = :ip_address,
            gnodeb_associado = :gnodeb_associado
        WHERE id_dispositivo = :id_dispositivo
        RETURNING *
    """)

    dispositivo = _executar_gravacao(db, query, {
        "nome_dispositivo": dados.nome_dispositivo,
        "tipo":             dados.tipo,
        "ip_address":       dados.ip_address,
        "gnodeb_associado": dados.gnodeb_associado,
        "id_dispositivo":   id_dispositivo
    })
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

    return dict(dispositivo._mapping)

@router.delete("/{id_dispositivo}", dependencies=[Depends(exigir_perfil("admin"))])
def desativar_dispositivo(id_dispositivo: int, db: Session = Depends(get_db)):
    """
    Desativa um dispositivo IoT (não exclui fisicamente).
    Mantém o histórico de logs associados (UC04).
    """
    query = text("""
        UPDATE tb_dispositivo
        SET status = 'inativo'
        WHERE id_dispositivo = :id_dispositivo
        RETURNING id_dispositivo
    """)

    resultado = db.execute(query, {"id_dispositivo": id_dispositivo})
    linha = resultado.fetchone()  # antes do commit (ver _executar_gravacao)
    db.commit()

    if not linha:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

    return {"mensagem": "Dispositivo desativado com sucesso"}