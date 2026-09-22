from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

def criar_alerta(
    db: Session,
    id_log: int,
    id_dispositivo: int,
    tipo_ataque: str,
    severidade: str,
    probabilidade: float
):
    """
    Insere um alerta na tabela tb_alerta quando um ataque é detectado.
    Retorna o id do alerta criado.
    """

    query = text("""
        INSERT INTO tb_alerta (
            id_log,
            id_dispositivo,
            data_hora_alerta,
            tipo_ataque,
            severidade,
            probabilidade_confianca,
            status_alerta
        ) VALUES (
            :id_log,
            :id_dispositivo,
            :data_hora_alerta,
            :tipo_ataque,
            :severidade,
            :probabilidade_confianca,
            :status_alerta
        ) RETURNING id_alerta
    """)

    resultado = db.execute(query, {
        "id_log":                   id_log,
        "id_dispositivo":           id_dispositivo,
        "data_hora_alerta":         datetime.now(),
        "tipo_ataque":              tipo_ataque,
        "severidade":               severidade,
        "probabilidade_confianca":  probabilidade,
        "status_alerta":            "aberto"
    })

    db.commit()
    id_alerta = resultado.fetchone()[0]
    return id_alerta