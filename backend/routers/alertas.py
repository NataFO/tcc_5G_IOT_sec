from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.database import get_db
from schemas.schemas import AlertaResponse, AlertaUpdate
from security import get_current_user

# dependencies=[...] exige um token JWT válido em TODAS as rotas deste
# router (RF05 / CT13) — quem chamar sem "Authorization: Bearer <token>"
# ou com token expirado/inválido recebe 401 antes de a função rodar.
router = APIRouter(
    prefix="/alertas",
    tags=["Alertas"],
    dependencies=[Depends(get_current_user)],
)

@router.get("/")
def listar_alertas(
    limite: int = 50,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    Retorna os alertas gerados pelo sistema.
    Pode filtrar por status: aberto, investigando,
    falso_positivo, resolvido.
    """
    if status:
        query = text("""
            SELECT a.id_alerta, a.id_dispositivo, a.data_hora_alerta,
                   a.tipo_ataque, a.severidade, a.probabilidade_confianca,
                   a.status_alerta, d.nome_dispositivo
            FROM tb_alerta a
            JOIN tb_dispositivo d ON a.id_dispositivo = d.id_dispositivo
            WHERE a.status_alerta = :status
            ORDER BY a.data_hora_alerta DESC
            LIMIT :limite
        """)
        alertas = db.execute(query, {"status": status, "limite": limite}).fetchall()
    else:
        query = text("""
            SELECT a.id_alerta, a.id_dispositivo, a.data_hora_alerta,
                   a.tipo_ataque, a.severidade, a.probabilidade_confianca,
                   a.status_alerta, d.nome_dispositivo
            FROM tb_alerta a
            JOIN tb_dispositivo d ON a.id_dispositivo = d.id_dispositivo
            ORDER BY a.data_hora_alerta DESC
            LIMIT :limite
        """)
        alertas = db.execute(query, {"limite": limite}).fetchall()

    return [dict(a._mapping) for a in alertas]

@router.get("/{id_alerta}")
def buscar_alerta(id_alerta: int, db: Session = Depends(get_db)):
    """Retorna um alerta específico pelo ID."""
    query = text("""
        SELECT a.*, d.nome_dispositivo
        FROM tb_alerta a
        JOIN tb_dispositivo d ON a.id_dispositivo = d.id_dispositivo
        WHERE a.id_alerta = :id_alerta
    """)
    alerta = db.execute(query, {"id_alerta": id_alerta}).fetchone()

    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")

    return dict(alerta._mapping)

@router.patch("/{id_alerta}")
def atualizar_alerta(
    id_alerta: int,
    dados: AlertaUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza o status de um alerta.
    Usado para marcar como falso positivo ou resolvido (UC14).
    """
    query = text("""
        UPDATE tb_alerta
        SET status_alerta = :status_alerta,
            observacoes   = :observacoes,
            resolvido_em  = CASE
                WHEN :status_alerta = 'resolvido' THEN NOW()
                ELSE resolvido_em
            END
        WHERE id_alerta = :id_alerta
        RETURNING id_alerta
    """)

    resultado = db.execute(query, {
        "status_alerta": dados.status_alerta,
        "observacoes":   dados.observacoes,
        "id_alerta":     id_alerta
    })
    db.commit()

    if not resultado.fetchone():
        raise HTTPException(status_code=404, detail="Alerta não encontrado")

    return {"mensagem": "Alerta atualizado com sucesso"}