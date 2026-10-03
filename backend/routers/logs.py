import time

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Optional

from models.database import get_db
from schemas.schemas import LogRedeCreate, LogRedeResponse
from services.model_service import classificar_fluxo
from services.alert_service import criar_alerta
from security import get_current_user, exigir_perfil

# dependencies=[...] exige um token JWT válido em TODAS as rotas deste
# router (RF05 / CT13) — quem chamar sem "Authorization: Bearer <token>"
# ou com token expirado/inválido recebe 401 antes de a função rodar.
router = APIRouter(
    prefix="/logs",
    tags=["Logs de Rede"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=LogRedeResponse, dependencies=[Depends(exigir_perfil("admin", "analista"))])
def registrar_log(dados: LogRedeCreate, response: Response, db: Session = Depends(get_db)):
    """
    Recebe um fluxo de rede, classifica com o modelo LSTM,
    grava o log no banco (tb_log_rede) e, se for identificado
    como ataque, gera um alerta automaticamente (tb_alerta).

    A resposta traz o cabeçalho padrão "Server-Timing" com o tempo (ms) de
    cada etapa — consulta, inferência, gravação do log e do alerta — medido
    DENTRO do servidor. Assim o CT03 mede só a inferência e o CT04 o tempo
    até o alerta ser gravado, sem somar a latência de rede do cliente.
    """
    t_inicio = time.perf_counter()

    # Confere se o dispositivo existe antes de gravar o log
    dispositivo = db.execute(
        text("SELECT id_dispositivo FROM tb_dispositivo WHERE id_dispositivo = :id"),
        {"id": dados.id_dispositivo}
    ).fetchone()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

    t_consulta = time.perf_counter()

    # Classifica o fluxo com o modelo LSTM
    resultado_ia = classificar_fluxo(dados.dict())
    t_inferencia = time.perf_counter()

    momento_captura = datetime.now()

    query = text("""
        INSERT INTO tb_log_rede (
            id_dispositivo, momento_captura, ip_origem, ip_destino,
            porta_origem, porta_destino, protocolo, bytes_enviados,
            pacotes_enviados, duracao_fluxo_ms, classificacao_ia, probabilidade_ia
        ) VALUES (
            :id_dispositivo, :momento_captura, :ip_origem, :ip_destino,
            :porta_origem, :porta_destino, :protocolo, :bytes_enviados,
            :pacotes_enviados, :duracao_fluxo_ms, :classificacao_ia, :probabilidade_ia
        ) RETURNING *
    """)

    resultado = db.execute(query, {
        "id_dispositivo":   dados.id_dispositivo,
        "momento_captura":  momento_captura,
        "ip_origem":        dados.ip_origem,
        "ip_destino":       dados.ip_destino,
        "porta_origem":     dados.porta_origem,
        "porta_destino":    dados.porta_destino,
        "protocolo":        dados.protocolo,
        "bytes_enviados":   dados.bytes_enviados,
        "pacotes_enviados": dados.pacotes_enviados,
        "duracao_fluxo_ms": dados.duracao_fluxo_ms,
        "classificacao_ia": resultado_ia["classificacao"],
        "probabilidade_ia": resultado_ia["probabilidade"],
    })
    # Lê o resultado ANTES do commit: depois do commit a conexão volta ao pool e,
    # com requisições simultâneas, outra requisição pode pegá-la e fechar este
    # cursor ("cursor already closed" — achado no teste de carga CT09).
    log_criado = resultado.fetchone()
    db.commit()
    t_log = time.perf_counter()

    # Se o modelo classificou como ataque, gera um alerta automaticamente
    if resultado_ia["classificacao"] != "Normal":
        criar_alerta(
            db=db,
            id_log=log_criado.id_log,
            id_dispositivo=dados.id_dispositivo,
            tipo_ataque=resultado_ia["classificacao"],
            severidade=resultado_ia["severidade"],
            probabilidade=resultado_ia["probabilidade"],
        )
    t_fim = time.perf_counter()

    def ms(a, b):
        return f"{(b - a) * 1000:.2f}"

    response.headers["Server-Timing"] = ", ".join([
        f"consulta;dur={ms(t_inicio, t_consulta)}",
        f"inferencia;dur={ms(t_consulta, t_inferencia)}",
        f"fila_modelo;dur={resultado_ia.get('fila_ms', 0):.2f}",
        f"modelo;dur={resultado_ia.get('modelo_ms', 0):.2f}",
        f"gravar_log;dur={ms(t_inferencia, t_log)}",
        f"gravar_alerta;dur={ms(t_log, t_fim)}",
        f"total;dur={ms(t_inicio, t_fim)}",
    ])

    return dict(log_criado._mapping)


@router.get("/")
def listar_logs(
    limite: int = 50,
    id_dispositivo: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Retorna os logs de rede mais recentes, opcionalmente filtrando por dispositivo."""
    if id_dispositivo:
        query = text("""
            SELECT * FROM tb_log_rede
            WHERE id_dispositivo = :id_dispositivo
            ORDER BY momento_captura DESC
            LIMIT :limite
        """)
        logs = db.execute(query, {"id_dispositivo": id_dispositivo, "limite": limite}).fetchall()
    else:
        query = text("""
            SELECT * FROM tb_log_rede
            ORDER BY momento_captura DESC
            LIMIT :limite
        """)
        logs = db.execute(query, {"limite": limite}).fetchall()

    return [dict(l._mapping) for l in logs]


@router.get("/{id_log}")
def buscar_log(id_log: int, db: Session = Depends(get_db)):
    """Retorna um log específico pelo ID."""
    query = text("SELECT * FROM tb_log_rede WHERE id_log = :id_log")
    log = db.execute(query, {"id_log": id_log}).fetchone()

    if not log:
        raise HTTPException(status_code=404, detail="Log não encontrado")

    return dict(log._mapping)
