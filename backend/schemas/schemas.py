from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ── AUTENTICAÇÃO ──────────────────────────────────────────
class LoginSchema(BaseModel):
    login: str
    senha: str

class TokenSchema(BaseModel):
    access_token: str
    token_type: str

# ── DISPOSITIVOS ──────────────────────────────────────────
class DispositivoCreate(BaseModel):
    nome_dispositivo: str
    tipo: str
    ip_address: str
    gnodeb_associado: str

class DispositivoResponse(BaseModel):
    id_dispositivo: int
    nome_dispositivo: str
    tipo: str
    ip_address: str
    gnodeb_associado: str
    status: str
    registrado_em: datetime

    class Config:
        from_attributes = True

# ── LOGS DE REDE ──────────────────────────────────────────
class LogRedeCreate(BaseModel):
    id_dispositivo: int
    ip_origem: str
    ip_destino: str
    porta_origem: int
    porta_destino: int
    protocolo: str
    bytes_enviados: int
    pacotes_enviados: int
    duracao_fluxo_ms: float
    network_packets_all_count: float
    network_packets_dst_count: float
    network_ports_src_count: float
    network_ports_all_count: float
    network_time_delta_avg: float
    network_packet_size_min: float
    network_ports_dst_count: float
    network_packets_src_count: float
    network_tcp_flags_rst_count: float
    network_tcp_flags_syn_count: float
    network_tcp_flags_ack_count: float
    network_time_delta_max: float
    network_window_size_std_deviation: float
    network_time_delta_min: float
    network_mss_max: float
    network_time_delta_std_deviation: float
    network_ttl_avg: float
    network_packet_size_max: float
    network_interval_packets: float
    network_mss_min: float

class LogRedeResponse(BaseModel):
    id_log: int
    id_dispositivo: int
    momento_captura: datetime
    classificacao_ia: str
    probabilidade_ia: float

    class Config:
        from_attributes = True

# ── ALERTAS ───────────────────────────────────────────────
class AlertaResponse(BaseModel):
    id_alerta: int
    id_dispositivo: int
    data_hora_alerta: datetime
    tipo_ataque: str
    severidade: str
    probabilidade_confianca: float
    status_alerta: str

    class Config:
        from_attributes = True

class AlertaUpdate(BaseModel):
    status_alerta: str
    observacoes: Optional[str] = None