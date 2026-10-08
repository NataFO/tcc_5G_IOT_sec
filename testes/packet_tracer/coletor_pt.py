# ATENCAO: arquivo so com caracteres ASCII (sem acentos) - o Python do
# Packet Tracer nao aceita acentos/caracteres especiais em strings.
#
# Coletor de fluxos - roda DENTRO do Cisco Packet Tracer 8.2.1 (SBC Board > Programming).
#
# Faz o papel do coletor do nucleo da rede 5G: para cada fluxo de um sensor
# IoT da topologia, envia os metadados para a API real do sistema
# (POST /logs/), que classifica com o LSTM e gera alerta se for ataque.
#
# O envio usa o RealHTTPClient do Packet Tracer, que sai pela rede real
# do computador (nao pela rede simulada).
#
# As 20 features estatisticas nao sao calculadas pelo Packet Tracer: vem de
# duas amostras reais do conjunto de teste (a mesma origem dos botoes
# "Preencher exemplo" do dashboard). Normal = amostra 2032; ataque = amostra 4789.
#
# Antes de rodar:
#   1. backend ligado (uvicorn main:app --reload);
#   2. usuario proprio do coletor, so no banco local:
#        cd backend
#        python criar_usuario.py coletor-pt analista "Coletor Packet Tracer"
#   3. trocar SENHA abaixo pela senha criada para o coletor-pt
#      (use uma senha so para isso; nao use uma senha pessoal).

from realhttp import *
from time import *

API = "http://127.0.0.1:8000"
LOGIN = "coletor-pt"
SENHA = "TROQUE_PELA_SENHA_DO_COLETOR"
ID_DISPOSITIVO = 2   # dispositivo ativo no banco local (Sensor-Testes-Automatizados)

NORMAL = {
    "network_packets_all_count": 14,
    "network_packets_dst_count": 7,
    "network_ports_src_count": 2,
    "network_ports_all_count": 2,
    "network_time_delta_avg": 0.015919786,
    "network_packet_size_min": 54,
    "network_ports_dst_count": 2,
    "network_packets_src_count": 7,
    "network_tcp_flags_rst_count": 0,
    "network_tcp_flags_syn_count": 0,
    "network_tcp_flags_ack_count": 14,
    "network_time_delta_max": 0.067932,
    "network_window_size_std_deviation": 29218.571436953,
    "network_time_delta_min": 0,
    "network_mss_max": 0,
    "network_time_delta_std_deviation": 0.023477818,
    "network_ttl_avg": 159.5,
    "network_packet_size_max": 72,
    "network_interval_packets": 308.615384615,
    "network_mss_min": 0,
}

ATAQUE = {
    "network_packets_all_count": 120795,
    "network_packets_dst_count": 120625,
    "network_ports_src_count": 28911,
    "network_ports_all_count": 28911,
    "network_time_delta_avg": 0.000010861,
    "network_packet_size_min": 60,
    "network_ports_dst_count": 166,
    "network_packets_src_count": 170,
    "network_tcp_flags_rst_count": 164,
    "network_tcp_flags_syn_count": 0,
    "network_tcp_flags_ack_count": 164,
    "network_time_delta_max": 0.019545306,
    "network_window_size_std_deviation": 142.429407225,
    "network_time_delta_min": 0.000000026,
    "network_mss_max": 0,
    "network_time_delta_std_deviation": 0.000085158,
    "network_ttl_avg": 64.26090736,
    "network_packet_size_max": 230,
    "network_interval_packets": 0.022078911,
    "network_mss_min": 0,
}

token = ""
clientes = []   # guarda os clientes HTTP ate a resposta chegar


def json_de(d):
    partes = []
    for k in d:
        v = d[k]
        if type(v) == type(""):
            partes.append('"' + k + '":"' + v + '"')
        else:
            partes.append('"' + k + '":' + str(v))
    return "{" + ",".join(partes) + "}"


def ao_logar(status, dados, *resto):
    global token
    print("login: HTTP " + str(status))
    marca = '"access_token":"'
    i = str(dados).find(marca)
    if status != 200 or i < 0:
        print("  falhou: " + str(dados))
        return
    i = i + len(marca)
    token = dados[i:dados.find('"', i)]
    print("  token recebido")


def enviar_fluxo(nome, features, ip_origem, pacotes, bytes_, duracao_ms):
    corpo = {
        "id_dispositivo": ID_DISPOSITIVO,
        "ip_origem": ip_origem,
        "ip_destino": "10.0.0.1",
        "porta_origem": 40000,
        "porta_destino": 80,
        "protocolo": "TCP",
        "bytes_enviados": bytes_,
        "pacotes_enviados": pacotes,
        "duracao_fluxo_ms": duracao_ms,
    }
    for k in features:
        corpo[k] = features[k]

    def resposta(status, dados, *resto):
        print(nome + " (" + ip_origem + "): HTTP " + str(status))
        print("  " + str(dados)[:200])

    c = RealHTTPClient()
    c.onDone(resposta)
    clientes.append(c)
    c.postWithHeader(API + "/logs/", json_de(corpo),
                     {"Content-Type": "application/json",
                      "Authorization": "Bearer " + token})


def main():
    print("Coletor PT -> " + API)
    c = RealHTTPClient()
    c.onDone(ao_logar)
    clientes.append(c)
    c.postWithHeader(API + "/auth/login",
                     json_de({"login": LOGIN, "senha": SENHA}),
                     {"Content-Type": "application/json"})

    espera = 0
    while token == "" and espera < 20:
        sleep(1)
        espera = espera + 1
    if token == "":
        print("Sem token: confira login/senha e se o backend esta ligado.")
        return

    enviar_fluxo("fluxo normal", NORMAL, "192.168.10.11", 14, 900, 207.0)
    sleep(3)
    enviar_fluxo("fluxo de ataque", ATAQUE, "192.168.10.12", 120795, 7247700, 1312.0)

    while True:
        sleep(60)


if __name__ == "__main__":
    main()
