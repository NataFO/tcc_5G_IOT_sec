"""
CT13 — Autenticação e controle de acesso por perfil.

Critério do TCC: usuário 'viewer' sem acesso a configurações.

O script testa três situações contra a API:
  1. SEM login           -> toda rota protegida deve responder 401.
  2. Logado como VIEWER  -> pode CONSULTAR (200), mas qualquer alteração
                            (dispositivos, alertas, envio de logs) deve dar 403.
  3. Logado como ADMIN   -> consulta normalmente (200) e passa pela checagem
                            de perfil nas rotas de alteração.

Nenhuma tentativa altera dados de verdade: as alterações usam IDs que não
existem (999999) e o cadastro usa um IP inválido de propósito. Então:
  - viewer  -> 403 (barrado ANTES de a API olhar os dados);
  - admin   -> passa pela checagem de perfil e só então recebe 404
               (ID inexistente) ou 422 (IP inválido), sem gravar nada.
Se a proteção falhar para o viewer, ele receberia 404/422 em vez de 403, e o
teste acusa a falha sem ter mexido no banco.

Antes, crie o usuário viewer:
  cd backend
  python criar_usuario.py viewer viewer

Uso (na raiz do projeto, venv ativo, backend rodando):
  python testes/teste_perfis.py
  python testes/teste_perfis.py --url https://SEU-BACKEND.up.railway.app
"""
import argparse
import getpass
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Falta a biblioteca 'requests'. Rode: pip install requests")

PASTA = Path(__file__).resolve().parent
ID_INEXISTENTE = 999999

DISPOSITIVO_TESTE = {
    "nome_dispositivo": "CT13-nao-deveria-existir",
    "tipo": "sensor",
    "ip_address": "ip-invalido-ct13",
    "gnodeb_associado": "gNodeB-Testes",
}
ALERTA_PATCH = {"status_alerta": "investigando", "observacoes": "CT13"}


def payload_log():
    base = {
        "id_dispositivo": ID_INEXISTENTE, "ip_origem": "10.0.0.5", "ip_destino": "10.0.0.1",
        "porta_origem": 51000, "porta_destino": 443, "protocolo": "TCP",
        "bytes_enviados": 1500, "pacotes_enviados": 12, "duracao_fluxo_ms": 100.0,
    }
    features = [
        "network_packets_all_count", "network_packets_dst_count", "network_ports_src_count",
        "network_ports_all_count", "network_time_delta_avg", "network_packet_size_min",
        "network_ports_dst_count", "network_packets_src_count", "network_tcp_flags_rst_count",
        "network_tcp_flags_syn_count", "network_tcp_flags_ack_count", "network_time_delta_max",
        "network_window_size_std_deviation", "network_time_delta_min", "network_mss_max",
        "network_time_delta_std_deviation", "network_ttl_avg", "network_packet_size_max",
        "network_interval_packets", "network_mss_min",
    ]
    return {**base, **{f: 1.0 for f in features}}


# (descrição, método, caminho, corpo, é_alteração?)
CASOS = [
    ("Listar dispositivos",              "GET",    "/dispositivos/",                   None,               False),
    ("Listar logs",                      "GET",    "/logs/?limite=5",                  None,               False),
    ("Listar alertas",                   "GET",    "/alertas/?limite=5",               None,               False),
    ("Resumo de alertas",                "GET",    "/alertas/resumo",                  None,               False),
    ("Cadastrar dispositivo",            "POST",   "/dispositivos/",                   DISPOSITIVO_TESTE,  True),
    ("Editar dispositivo",               "PATCH",  f"/dispositivos/{ID_INEXISTENTE}",  DISPOSITIVO_TESTE,  True),
    ("Desativar dispositivo",            "DELETE", f"/dispositivos/{ID_INEXISTENTE}",  None,               True),
    ("Mudar status de alerta",           "PATCH",  f"/alertas/{ID_INEXISTENTE}",       ALERTA_PATCH,       True),
    ("Enviar log de rede",               "POST",   "/logs/",                           payload_log(),      True),
]


def esperado(perfil, alteracao, metodo, caminho):
    """Código HTTP esperado para cada perfil."""
    if perfil is None:
        return {401}
    if not alteracao:
        return {200}
    if perfil == "viewer":
        return {403}
    # admin passa pela checagem de perfil; como os dados são inválidos de
    # propósito, a rota responde 422 (IP inválido) ou 404 (ID inexistente).
    # (o que importa é NÃO ser 403: significa que o admin passou pela checagem)
    return {404, 422}


def login(url, usuario, senha):
    r = requests.post(f"{url}/auth/login", json={"login": usuario, "senha": senha}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"ERRO: login de '{usuario}' falhou (HTTP {r.status_code}: {r.text[:200]})")
    return r.json()["access_token"]


def rodar(url, perfil, token):
    s = requests.Session()
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    linhas = []
    for desc, metodo, caminho, corpo, alteracao in CASOS:
        r = s.request(metodo, url + caminho, json=corpo, timeout=60)
        ok_codigos = esperado(perfil, alteracao, metodo, caminho)
        detalhe = ""
        try:
            j = r.json()
            detalhe = j.get("detail", "") if isinstance(j, dict) else ""
        except ValueError:
            pass
        linhas.append({
            "perfil": perfil or "sem login", "acao": desc, "metodo": metodo, "rota": caminho,
            "http": r.status_code, "esperado": sorted(ok_codigos),
            "ok": r.status_code in ok_codigos, "detalhe": str(detalhe)[:120],
        })
    return linhas


def main():
    ap = argparse.ArgumentParser(description="CT13 — controle de acesso por perfil")
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--viewer", default="viewer", help="login do usuário viewer")
    ap.add_argument("--admin", default="admin", help="login do usuário admin")
    args = ap.parse_args()
    url = args.url.rstrip("/")

    senha_viewer = getpass.getpass(f"Senha do '{args.viewer}': ")
    senha_admin = getpass.getpass(f"Senha do '{args.admin}': ")

    inicio = datetime.now()
    resultados = []
    resultados += rodar(url, None, None)
    resultados += rodar(url, "viewer", login(url, args.viewer, senha_viewer))
    resultados += rodar(url, "admin", login(url, args.admin, senha_admin))

    print(f"\nCT13 — {url} — {inicio:%d/%m/%Y %H:%M}\n")
    print(f"{'Perfil':<10} {'Ação':<26} {'HTTP':>5}  {'Esperado':<10} Resultado")
    print("-" * 70)
    for r in resultados:
        esp = "/".join(str(c) for c in r["esperado"])
        print(f"{r['perfil']:<10} {r['acao']:<26} {r['http']:>5}  {esp:<10} {'OK' if r['ok'] else 'FALHOU'}")

    falhas = [r for r in resultados if not r["ok"]]
    viewer_bloq = sum(1 for r in resultados if r["perfil"] == "viewer" and r["http"] == 403)
    viewer_alt = sum(1 for r in resultados if r["perfil"] == "viewer" and r["metodo"] != "GET")
    print("-" * 70)
    print(f"Viewer bloqueado em {viewer_bloq} de {viewer_alt} tentativas de alteração.")
    print(f"Resultado: {'Aprovado' if not falhas else 'Reprovado'} "
          f"({len(resultados) - len(falhas)}/{len(resultados)} verificações OK)")
    for f in falhas:
        print(f"  FALHOU: {f['perfil']} / {f['acao']}: HTTP {f['http']} (esperado {f['esperado']}) {f['detalhe']}")

    pasta = PASTA / "resultados"
    pasta.mkdir(exist_ok=True)
    arq = pasta / f"ct13_perfis_{inicio:%Y%m%d_%H%M%S}.json"
    arq.write_text(json.dumps({"url": url, "inicio": inicio.isoformat(timespec="seconds"),
                               "resultados": resultados}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSalvo: {arq}")


if __name__ == "__main__":
    main()
