"""
CT01 — Captura e registro de metadados de tráfego.

Critério do TCC: metadados capturados; latência < 5 ms.

O sistema não captura pacotes diretamente da rede: quem faz isso é a
ferramenta de captura (no protótipo, os dados vêm do dataset). O que o
backend faz é RECEBER os metadados de cada fluxo e REGISTRÁ-LOS no banco.
Este script testa essa parte:

  1. Integridade: envia fluxos com metadados variados (IPs, portas,
     protocolo TCP/UDP, bytes, pacotes, duração), lê cada um de volta em
     GET /logs/{id} e confere campo a campo se o que foi gravado é igual
     ao que foi enviado.
  2. Latência do registro: usa o cabeçalho Server-Timing para medir quanto
     tempo o servidor leva para gravar o log no banco (etapa "gravar_log").

Uso (na raiz do projeto, venv ativo, backend rodando):
  python testes/teste_metadados.py
  python testes/teste_metadados.py --fluxos 200
"""
import argparse
import getpass
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import requests
except ImportError:
    sys.exit("Falta a biblioteca 'requests'. Rode: pip install requests")

PASTA = Path(__file__).resolve().parent
CAMPOS = ["ip_origem", "ip_destino", "porta_origem", "porta_destino", "protocolo",
          "bytes_enviados", "pacotes_enviados", "duracao_fluxo_ms"]


def ler_server_timing(cab):
    tempos = {}
    for parte in (cab or "").split(","):
        nome, _, resto = parte.strip().partition(";")
        if resto.startswith("dur="):
            tempos[nome] = float(resto[4:])
    return tempos


def main():
    ap = argparse.ArgumentParser(description="CT01 — registro de metadados")
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--login", default="admin")
    ap.add_argument("--fluxos", type=int, default=100)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    url = args.url.rstrip("/")
    rnd = random.Random(args.seed)

    df = pd.read_csv(PASTA / "conjunto_teste_bruto.csv")
    features = [c for c in df.columns if c.startswith("network_")]
    amostras = df.sample(args.fluxos, random_state=args.seed).reset_index(drop=True)

    senha = os.getenv("TCC_SENHA") or getpass.getpass(f"Senha do usuário '{args.login}': ")
    s = requests.Session()
    r = s.post(f"{url}/auth/login", json={"login": args.login, "senha": senha}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"ERRO: login falhou (HTTP {r.status_code})")
    s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    disp = next((d for d in s.get(f"{url}/dispositivos/", timeout=30).json()
                 if d["status"] == "ativo"), None)
    if not disp:
        sys.exit("ERRO: nenhum dispositivo ativo para associar os fluxos.")

    inicio = datetime.now()
    linhas, divergencias = [], []
    print(f"Enviando {args.fluxos} fluxos para POST /logs/ e conferindo cada um em GET /logs/{{id}} ...")
    for i, amostra in amostras.iterrows():
        enviado = {
            "ip_origem": f"10.{rnd.randint(0, 255)}.{rnd.randint(0, 255)}.{rnd.randint(1, 254)}",
            "ip_destino": f"192.168.{rnd.randint(0, 255)}.{rnd.randint(1, 254)}",
            "porta_origem": rnd.randint(1024, 65535),
            "porta_destino": rnd.choice([22, 53, 80, 443, 1883, 8080]),
            "protocolo": rnd.choice(["TCP", "UDP"]),
            "bytes_enviados": rnd.randint(64, 10_000_000),
            "pacotes_enviados": rnd.randint(1, 100_000),
            "duracao_fluxo_ms": round(rnd.uniform(0.5, 5000), 3),
        }
        payload = {"id_dispositivo": disp["id_dispositivo"], **enviado,
                   **{f: float(amostra[f]) for f in features}}
        r = s.post(f"{url}/logs/", json=payload, timeout=60)
        if r.status_code != 200:
            sys.exit(f"ERRO: POST /logs/ falhou (HTTP {r.status_code}: {r.text[:200]})")
        tempos = ler_server_timing(r.headers.get("Server-Timing"))
        gravado = s.get(f"{url}/logs/{r.json()['id_log']}", timeout=30).json()

        erros = []
        for c in CAMPOS:
            a, b = enviado[c], gravado.get(c)
            igual = abs(float(a) - float(b)) < 1e-6 if c == "duracao_fluxo_ms" else str(a) == str(b)
            if not igual:
                erros.append(f"{c}: enviado={a!r} gravado={b!r}")
        if erros:
            divergencias.append({"id_log": gravado.get("id_log"), "erros": erros})
        linhas.append({"id_log": gravado.get("id_log"), "campos_ok": len(CAMPOS) - len(erros),
                       "momento_captura": gravado.get("momento_captura"),
                       "t_gravar_log_ms": tempos.get("gravar_log")})

    res = pd.DataFrame(linhas)
    total_campos = len(res) * len(CAMPOS)
    campos_ok = int(res.campos_ok.sum())
    tem_timing = res.t_gravar_log_ms.notna().all()
    if tem_timing:
        p50, p95, p99 = np.percentile(res.t_gravar_log_ms, [50, 95, 99])

    print(f"\nCT01 — {len(res)} fluxos — {url} — {inicio:%d/%m/%Y %H:%M}")
    print(f"Integridade: {campos_ok}/{total_campos} campos gravados exatamente como enviados "
          f"({'todos os fluxos com momento_captura preenchido' if res.momento_captura.notna().all() else 'HÁ fluxos sem momento_captura'})")
    if tem_timing:
        print(f"Tempo para registrar o log no banco: P50 {p50:.1f} ms | P95 {p95:.1f} ms | P99 {p99:.1f} ms "
              f"(critério < 5 ms)")
    else:
        print("Backend sem Server-Timing: não foi possível medir o tempo de registro.")
    for d in divergencias[:10]:
        print(f"  DIVERGÊNCIA no log {d['id_log']}: {'; '.join(d['erros'])}")

    pasta = PASTA / "resultados"
    pasta.mkdir(exist_ok=True)
    arq = pasta / f"ct01_metadados_{inicio:%Y%m%d_%H%M%S}.json"
    arq.write_text(json.dumps({
        "url": url, "inicio": inicio.isoformat(timespec="seconds"), "fluxos": len(res),
        "campos_ok": campos_ok, "campos_total": total_campos, "divergencias": divergencias,
        "gravar_log_ms": ({"p50": p50, "p95": p95, "p99": p99} if tem_timing else None),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSalvo: {arq}")


if __name__ == "__main__":
    main()
