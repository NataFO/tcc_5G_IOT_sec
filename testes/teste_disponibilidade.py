"""
CT10 — Disponibilidade após falha de nó.

Critério do TCC: retomada automática em até 30 s.

Como funciona:
  1. Confere que a API está no ar (GET /).
  2. Provoca a falha: chama POST /admin/simular-falha, que encerra o
     processo do backend com código de erro (como um travamento real).
     (Com --sem-derrubar, o script não provoca nada: você reinicia o serviço
     pelo painel do Railway e ele só mede.)
  3. Fica consultando GET / a cada 0,5 s e registra:
       - quando a API parou de responder (queda);
       - quando voltou a responder sozinha (retorno);
       - quando voltou a CLASSIFICAR (faz login e envia um fluxo real).
  4. Tempo de recuperação = retorno - queda.

Onde rodar: no Railway. Localmente não há ninguém para reiniciar o processo
depois da queda, então o teste só faz sentido na nuvem, onde a política de
reinício ("Restart Policy: On Failure") coloca o serviço de pé de novo.

Antes, no Railway (serviço do backend):
  - Settings > Deploy > Restart Policy = "On Failure";
  - Variables > adicionar PERMITIR_TESTE_FALHA = 1 (e esperar o redeploy).
Depois do teste, APAGUE essa variável.

Uso:
  python testes/teste_disponibilidade.py --url https://SEU-BACKEND.up.railway.app
  python testes/teste_disponibilidade.py --url ... --sem-derrubar     (reinício manual)
"""
import argparse
import getpass
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    import requests
except ImportError:
    sys.exit("Falta a biblioteca 'requests'. Rode: pip install requests")

PASTA = Path(__file__).resolve().parent
CRITERIO_S = 30.0


def no_ar(url):
    try:
        return requests.get(url + "/", timeout=2).status_code == 200
    except requests.RequestException:
        return False


def login(url, usuario, senha):
    r = requests.post(f"{url}/auth/login", json={"login": usuario, "senha": senha}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def classifica(url, token, payload):
    try:
        r = requests.post(f"{url}/logs/", json=payload, timeout=10,
                          headers={"Authorization": f"Bearer {token}"})
        return r.status_code == 200
    except requests.RequestException:
        return False


def main():
    ap = argparse.ArgumentParser(description="CT10 — disponibilidade após falha")
    ap.add_argument("--url", required=True)
    ap.add_argument("--login", default="admin")
    ap.add_argument("--sem-derrubar", action="store_true",
                    help="não provoca a falha; você reinicia pelo painel e o script só mede")
    ap.add_argument("--limite", type=int, default=300, help="desiste depois de N segundos")
    args = ap.parse_args()
    url = args.url.rstrip("/")

    senha = os.getenv("TCC_SENHA") or getpass.getpass(f"Senha do usuário '{args.login}': ")
    if not no_ar(url):
        sys.exit("ERRO: a API não está respondendo agora. Ela precisa estar no ar antes do teste.")
    token = login(url, args.login, senha)

    df = pd.read_csv(PASTA / "conjunto_teste_bruto.csv")
    linha = df.iloc[0]
    features = [c for c in df.columns if c.startswith("network_")]
    dispositivos = requests.get(f"{url}/dispositivos/", headers={"Authorization": f"Bearer {token}"},
                                timeout=10).json()
    if not dispositivos:
        sys.exit("ERRO: cadastre ao menos um dispositivo antes.")
    payload = {"id_dispositivo": dispositivos[0]["id_dispositivo"], "ip_origem": "10.97.0.1",
               "ip_destino": "10.0.0.1", "porta_origem": 40000, "porta_destino": 80, "protocolo": "TCP",
               "bytes_enviados": 1000, "pacotes_enviados": 10, "duracao_fluxo_ms": 5000.0,
               **{f: float(linha[f]) for f in features}}
    if not classifica(url, token, payload):
        sys.exit("ERRO: a classificação não funcionou antes da falha. Confira o backend.")

    inicio = datetime.now()
    t0 = time.time()
    eventos = []

    def marca(nome):
        t = time.time() - t0
        eventos.append({"evento": nome, "t_s": round(t, 2), "hora": datetime.now().strftime("%H:%M:%S")})
        print(f"  [{eventos[-1]['hora']}] +{t:6.1f} s  {nome}")

    print(f"CT10 — {url}\n")
    if args.sem_derrubar:
        print("Reinicie agora o serviço do backend pelo painel do Railway. Monitorando...\n")
        marca("monitoramento iniciado (aguardando a queda)")
    else:
        r = requests.post(f"{url}/admin/simular-falha", headers={"Authorization": f"Bearer {token}"},
                          timeout=10)
        if r.status_code == 404:
            sys.exit("ERRO: a rota /admin/simular-falha não existe. Defina PERMITIR_TESTE_FALHA=1 nas "
                     "variáveis do backend no Railway, espere o redeploy e rode de novo.")
        if r.status_code != 200:
            sys.exit(f"ERRO ao provocar a falha: HTTP {r.status_code} {r.text[:200]}")
        marca("falha provocada (POST /admin/simular-falha)")

    t_queda = t_volta = t_funcional = None
    while time.time() - t0 < args.limite:
        vivo = no_ar(url)
        if t_queda is None and not vivo:
            t_queda = time.time()
            marca("API parou de responder (queda)")
        elif t_queda is not None and t_volta is None and vivo:
            t_volta = time.time()
            marca("API voltou a responder (GET / = 200)")
        if t_volta is not None:
            try:
                token = login(url, args.login, senha)
                if classifica(url, token, payload):
                    t_funcional = time.time()
                    marca("API voltou a classificar fluxos (POST /logs/ = 200)")
                    break
            except requests.RequestException:
                pass
        time.sleep(0.5)

    print()
    resultado = {"url": url, "inicio": inicio.isoformat(timespec="seconds"), "eventos": eventos,
                 "modo": "reinicio_manual" if args.sem_derrubar else "falha_provocada"}
    if t_queda is None:
        print("A API não chegou a cair dentro do tempo limite. Nada a medir.")
    elif t_volta is None:
        print(f"A API NÃO voltou em {args.limite} s. Resultado: Reprovado.")
        resultado["recuperacao_s"] = None
    else:
        rec = t_volta - t_queda
        resultado["recuperacao_s"] = round(rec, 1)
        resultado["ate_classificar_s"] = round(t_funcional - t_queda, 1) if t_funcional else None
        print(f"Tempo de recuperação (queda -> responder): {rec:.1f} s (critério <= {CRITERIO_S:.0f} s) "
              f"-> {'Aprovado' if rec <= CRITERIO_S else 'Reprovado'}")
        if t_funcional:
            print(f"Até voltar a classificar: {t_funcional - t_queda:.1f} s")

    pasta = PASTA / "resultados"
    pasta.mkdir(exist_ok=True)
    arq = pasta / f"ct10_disponibilidade_{inicio:%Y%m%d_%H%M%S}.json"
    arq.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSalvo: {arq}")


if __name__ == "__main__":
    main()
