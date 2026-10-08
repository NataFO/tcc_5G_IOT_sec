# ATENCAO: arquivo so com caracteres ASCII (sem acentos) - o Python do
# Packet Tracer nao aceita acentos/caracteres especiais em strings.
#
# Coletor de fluxos v2 - roda DENTRO do Cisco Packet Tracer 8.2.1 (SBC Board > Programming).
#
# Diferenca para a v1 (coletor_pt.py): em vez de um dispositivo so, este script
# representa a topologia inteira. Cada sensor IoT da topologia envia fluxos
# NORMAIS com o seu proprio id_dispositivo e IP. O "Atacante-UE" comeca normal
# e, a partir da rodada RODADAS_NORMAIS + 1, passa a enviar fluxos com perfil de
# ATAQUE (no sistema, ele e um no comprometido; nao ha trafego malicioso real).
# A API real classifica cada fluxo com o LSTM e gera alerta quando for ataque.
#
# As 20 features estatisticas nao sao calculadas pelo Packet Tracer: vem de
# duas amostras reais do conjunto de teste (normal = 2032; ataque = 4789).
#
# Antes de rodar:
#   1. backend ligado (uvicorn main:app --reload) e usuario coletor-pt criado;
#   2. os 5 dispositivos cadastrados no dashboard (perfil admin) com o MESMO
#      nome e IP da topologia; anote o ID de cada um;
#   3. editar abaixo: SENHA, e na lista SENSORES o ID e o IP de cada dispositivo.
#   4. salvar o arquivo .pkt FORA da pasta do projeto (a senha fica no script).

from realhttp import *
from time import *

API = "http://127.0.0.1:8000"
LOGIN = "coletor-pt"
SENHA = "TROQUE_PELA_SENHA_DO_COLETOR"

# [nome, id_dispositivo no banco, IP do dispositivo na topologia]
# ids e IPs conferidos no dashboard em 08/10/2026
SENSORES = [
    ["Sensor-Temp-01", 10, "172.16.1.101"],
    ["Sensor-Mov-01", 11, "172.16.1.102"],
    ["Camera-01", 12, "172.16.1.103"],
    ["Fumaca-01", 13, "172.16.1.100"],
]
ATACANTE = ["Atacante-UE", 14, "172.16.1.104"]

RODADAS = 6            # quantas rodadas de envio
RODADAS_NORMAIS = 2    # o atacante fica normal nas primeiras rodadas
INTERVALO = 8          # segundos entre rodadas

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


def enviar_fluxo(nome, tipo, id_disp, ip_origem, features, pacotes, bytes_, duracao_ms):
    corpo = {
        "id_dispositivo": id_disp,
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
        print(nome + " (" + tipo + ", " + ip_origem + "): HTTP " + str(status))
        print("  " + str(dados)[:160])

    c = RealHTTPClient()
    c.onDone(resposta)
    clientes.append(c)
    c.postWithHeader(API + "/logs/", json_de(corpo),
                     {"Content-Type": "application/json",
                      "Authorization": "Bearer " + token})


def main():
    print("Coletor PT v2 -> " + API)
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

    rodada = 0
    while rodada < RODADAS:
        rodada = rodada + 1
        print("--- rodada " + str(rodada) + " de " + str(RODADAS))

        for d in SENSORES:
            enviar_fluxo(d[0], "normal", d[1], d[2], NORMAL, 14, 900, 207.0)
            sleep(1)

        if rodada > RODADAS_NORMAIS:
            print(ATACANTE[0] + " COMPROMETIDO: enviando perfil de ataque")
            enviar_fluxo(ATACANTE[0], "ataque", ATACANTE[1], ATACANTE[2],
                         ATAQUE, 120795, 7247700, 1312.0)
        else:
            enviar_fluxo(ATACANTE[0], "normal", ATACANTE[1], ATACANTE[2],
                         NORMAL, 14, 900, 207.0)

        sleep(INTERVALO)

    print("fim das rodadas")
    while True:
        sleep(60)


if __name__ == "__main__":
    main()
