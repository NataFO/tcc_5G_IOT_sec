"""
CT08 (carga) e CT09 (escalabilidade) — teste de carga da API.

Unidade de medida: cada requisição a POST /logs/ é UM FLUXO (uma janela de
5 s de tráfego de um dispositivo, já resumida em 20 features). O modelo
trabalha com fluxos, não com pacotes soltos. Por isso o script mede tudo em
fluxos por segundo e, só como referência, mostra quantos pacotes esses
fluxos representam (a soma de network_packets_all_count).

MODO "taxa" (CT08) — carga constante, em degraus:
  Envia fluxos num ritmo fixo (ex.: 10/s, depois 25/s, 50/s...) durante
  alguns segundos em cada degrau e mede, em cada um: taxa realmente
  atendida, erros e tempo de inferência (P95). Mostra até que ritmo o
  sistema aguenta com P95 de inferência <= 100 ms e zero erros.

  python testes/teste_carga.py --modo taxa --taxas 10,25,50,100 --duracao 20

MODO "maximo" (CT09) — vazão máxima com vários gNodeBs:
  Vários clientes em paralelo (um por gNodeB simulado) mandam fluxos o mais
  rápido possível. Mede a vazão máxima (fluxos/s). Rode duas vezes para
  comparar: com o backend normal (1 processo) e com 4 processos
  (uvicorn main:app --workers 4) — isso mostra se o sistema escala.

  python testes/teste_carga.py --modo maximo --clientes 8 --gnodebs 4 --duracao 30

Os fluxos vão para dispositivos próprios do teste ("Sensor-Carga-gNB1"...),
um por gNodeB simulado, para não misturar com os outros dados.

ATENÇÃO: gera milhares de logs e alertas no banco. Use o banco LOCAL.
"""
import argparse
import getpass
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import requests
except ImportError:
    sys.exit("Falta a biblioteca 'requests'. Rode: pip install requests")

PASTA = Path(__file__).resolve().parent
CRITERIO_P95_MS = 100.0
_local = threading.local()


def ler_server_timing(cab):
    tempos = {}
    for parte in (cab or "").split(","):
        nome, _, resto = parte.strip().partition(";")
        if resto.startswith("dur="):
            try:
                tempos[nome] = float(resto[4:])
            except ValueError:
                pass
    return tempos


def sessao(token):
    # uma sessão HTTP por thread (requests.Session não é segura entre threads)
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
        _local.s.headers["Authorization"] = f"Bearer {token}"
    return _local.s


def preparar_dispositivos(url, token, n):
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    existentes = {d["nome_dispositivo"]: d for d in s.get(f"{url}/dispositivos/", timeout=30).json()}
    ids = []
    for k in range(1, n + 1):
        nome = f"Sensor-Carga-gNB{k}"
        d = existentes.get(nome)
        if d is None:
            r = s.post(f"{url}/dispositivos/", json={
                "nome_dispositivo": nome, "tipo": "sensor",
                "ip_address": f"10.98.0.{k}", "gnodeb_associado": f"gNodeB-Carga-{k}",
            }, timeout=30)
            if r.status_code != 200:
                sys.exit(f"ERRO: não consegui criar {nome} (HTTP {r.status_code}: {r.text[:200]}). "
                         "O login precisa ser de um admin.")
            d = r.json()
        ids.append(d["id_dispositivo"])
    return ids


def montar_payloads(df, features, ids):
    payloads = []
    for i, linha in enumerate(df.itertuples(index=False)):
        linha = linha._asdict()
        pacotes = int(max(linha["network_packets_all_count"], 0))
        p = {
            "id_dispositivo": ids[i % len(ids)],
            "ip_origem": f"10.98.{(i // 250) % 250}.{i % 250 + 1}", "ip_destino": "10.0.0.1",
            "porta_origem": 40000 + (i % 20000), "porta_destino": 80, "protocolo": "TCP",
            "pacotes_enviados": pacotes,
            "bytes_enviados": int(pacotes * max(linha["network_packet_size_max"], 0)),
            "duracao_fluxo_ms": 5000.0,
        }
        p.update({f: float(linha[f]) for f in features})
        payloads.append((p, pacotes))
    return payloads


def enviar(url, token, payload):
    t0 = time.perf_counter()
    try:
        r = sessao(token).post(f"{url}/logs/", json=payload, timeout=60)
        lat = (time.perf_counter() - t0) * 1000
        t = ler_server_timing(r.headers.get("Server-Timing"))
        return {"ok": r.status_code == 200, "http": r.status_code, "lat_ms": lat,
                "inf_ms": t.get("inferencia"), "srv_ms": t.get("total"),
                "fila_ms": t.get("fila_modelo"), "modelo_ms": t.get("modelo")}
    except requests.RequestException as e:
        return {"ok": False, "http": None, "lat_ms": (time.perf_counter() - t0) * 1000,
                "inf_ms": None, "srv_ms": None, "erro": type(e).__name__}


def resumir(resultados, duracao_real, pacotes):
    df = pd.DataFrame(resultados)
    ok = df[df.ok]
    pct = lambda s, q: float(np.percentile(s.dropna(), q)) if s.notna().any() else float("nan")
    return {
        "enviadas": len(df), "sucesso": int(df.ok.sum()), "erros": int((~df.ok).sum()),
        "tipos_de_erro": {str(k): int(v) for k, v in
                          df[~df.ok].apply(lambda r: r["erro"] if isinstance(r.get("erro"), str)
                                           else f"HTTP {int(r['http'])}", axis=1)
                          .value_counts().items()} if (~df.ok).any() else {},
        "duracao_s": round(duracao_real, 2),
        "fluxos_por_s": round(len(ok) / duracao_real, 2),
        "pacotes_representados_por_s": round(pacotes / duracao_real, 1),
        "inferencia_p50_ms": pct(ok.inf_ms, 50), "inferencia_p95_ms": pct(ok.inf_ms, 95),
        "servidor_p95_ms": pct(ok.srv_ms, 95),
        "modelo_p95_ms": pct(ok.modelo_ms, 95) if "modelo_ms" in ok else float("nan"),
        "fila_p95_ms": pct(ok.fila_ms, 95) if "fila_ms" in ok else float("nan"),
        "requisicao_p50_ms": pct(ok.lat_ms, 50), "requisicao_p95_ms": pct(ok.lat_ms, 95),
    }


def degrau_taxa(url, token, payloads, taxa, duracao):
    """Carga constante: dispara uma requisição a cada 1/taxa segundos."""
    total = int(taxa * duracao)
    resultados, pacotes = [], 0
    trava = threading.Lock()

    def tarefa(idx):
        nonlocal pacotes
        p, pk = payloads[idx % len(payloads)]
        res = enviar(url, token, p)
        with trava:
            resultados.append(res)
            if res["ok"]:
                pacotes += pk

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(200, max(8, int(taxa * 2)))) as ex:
        for k in range(total):
            alvo = inicio + k / taxa
            espera = alvo - time.perf_counter()
            if espera > 0:
                time.sleep(espera)
            ex.submit(tarefa, k)
    return resumir(resultados, time.perf_counter() - inicio, pacotes)


def vazao_maxima(url, token, payloads, clientes, duracao):
    """Vários clientes em paralelo, cada um enviando o mais rápido possível."""
    fim = time.perf_counter() + duracao
    resultados, pacotes = [], 0
    trava = threading.Lock()
    contador = iter(range(10**9))

    def cliente():
        nonlocal pacotes
        while time.perf_counter() < fim:
            with trava:
                idx = next(contador)
            p, pk = payloads[idx % len(payloads)]
            res = enviar(url, token, p)
            with trava:
                resultados.append(res)
                if res["ok"]:
                    pacotes += pk

    inicio = time.perf_counter()
    threads = [threading.Thread(target=cliente) for _ in range(clientes)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return resumir(resultados, time.perf_counter() - inicio, pacotes)


def main():
    ap = argparse.ArgumentParser(description="CT08/CT09 — teste de carga")
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--login", default="admin")
    ap.add_argument("--modo", choices=["taxa", "maximo"], required=True)
    ap.add_argument("--taxas", default="10,25,50,100", help="modo taxa: fluxos/s de cada degrau")
    ap.add_argument("--clientes", type=int, default=8, help="modo maximo: clientes em paralelo")
    ap.add_argument("--gnodebs", type=int, default=4, help="quantos gNodeBs/dispositivos simular")
    ap.add_argument("--duracao", type=int, default=20, help="segundos por degrau / por rodada")
    ap.add_argument("--rotulo", default="", help="texto livre para identificar a rodada (ex.: 4workers)")
    args = ap.parse_args()
    url = args.url.rstrip("/")

    senha = os.getenv("TCC_SENHA") or getpass.getpass(f"Senha do usuário '{args.login}': ")
    r = requests.post(f"{url}/auth/login", json={"login": args.login, "senha": senha}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"ERRO: login falhou (HTTP {r.status_code})")
    token = r.json()["access_token"]

    df = pd.read_csv(PASTA / "conjunto_teste_bruto.csv").sample(frac=1, random_state=11)
    features = [c for c in df.columns if c.startswith("network_")]
    ids = preparar_dispositivos(url, token, args.gnodebs)
    payloads = montar_payloads(df, features, ids)

    # aquecimento (as primeiras inferências do TensorFlow são mais lentas)
    for p, _ in payloads[:5]:
        enviar(url, token, p)

    inicio = datetime.now()
    rodadas = []
    if args.modo == "taxa":
        print(f"CT08 — carga constante, {args.duracao} s por degrau, {args.gnodebs} gNodeBs\n")
        print(f"{'Degrau':>8} {'Atendida':>9} {'Erros':>6} {'Infer. P95':>11} {'(modelo':>8} {'+ fila)':>8} "
              f"{'Servidor P95':>13} {'Requis. P95':>12}  Situação")
        for taxa in [float(x) for x in args.taxas.split(",")]:
            res = degrau_taxa(url, token, payloads, taxa, args.duracao)
            res["taxa_alvo"] = taxa
            res["dentro_do_criterio"] = res["erros"] == 0 and res["inferencia_p95_ms"] <= CRITERIO_P95_MS
            rodadas.append(res)
            print(f"{taxa:>6.0f}/s {res['fluxos_por_s']:>7.1f}/s {res['erros']:>6} "
                  f"{res['inferencia_p95_ms']:>9.1f}ms {res['modelo_p95_ms']:>6.1f}ms {res['fila_p95_ms']:>6.1f}ms "
                  f"{res['servidor_p95_ms']:>11.1f}ms "
                  f"{res['requisicao_p95_ms']:>10.1f}ms  {'OK' if res['dentro_do_criterio'] else 'acima do limite'}")
        for r_ in rodadas:
            if r_["tipos_de_erro"]:
                print(f"  erros no degrau {r_['taxa_alvo']:.0f}/s: {r_['tipos_de_erro']}")
        ok = [r for r in rodadas if r["dentro_do_criterio"]]
        print()
        if ok:
            melhor = max(ok, key=lambda r: r["taxa_alvo"])
            print(f"Maior carga dentro do critério (P95 de inferência <= {CRITERIO_P95_MS:.0f} ms e zero erros): "
                  f"{melhor['taxa_alvo']:.0f} fluxos/s "
                  f"(~{melhor['pacotes_representados_por_s']:,.0f} pacotes/s representados)".replace(",", "."))
        else:
            print("Nenhum degrau ficou dentro do critério.")
    else:
        print(f"CT09 — vazão máxima: {args.clientes} clientes em paralelo, {args.gnodebs} gNodeBs, "
              f"{args.duracao} s {('[' + args.rotulo + ']') if args.rotulo else ''}\n")
        res = vazao_maxima(url, token, payloads, args.clientes, args.duracao)
        res.update({"clientes": args.clientes, "gnodebs": args.gnodebs, "rotulo": args.rotulo})
        rodadas.append(res)
        print(f"Requisições: {res['enviadas']} ({res['erros']} com erro{': ' + str(res['tipos_de_erro']) if res['erros'] else ''})")
        print(f"Vazão: {res['fluxos_por_s']:.1f} fluxos/s "
              f"(~{res['pacotes_representados_por_s']:,.0f} pacotes/s representados)".replace(",", "."))
        print(f"Inferência P50 {res['inferencia_p50_ms']:.1f} ms | P95 {res['inferencia_p95_ms']:.1f} ms "
              f"(execução do modelo P95 {res['modelo_p95_ms']:.1f} ms + espera na fila P95 {res['fila_p95_ms']:.1f} ms)")
        print(f"Requisição inteira P50 {res['requisicao_p50_ms']:.1f} ms | P95 {res['requisicao_p95_ms']:.1f} ms")

    pasta = PASTA / "resultados"
    pasta.mkdir(exist_ok=True)
    nome = f"{'ct08_carga' if args.modo == 'taxa' else 'ct09_vazao'}_{inicio:%Y%m%d_%H%M%S}"
    if args.rotulo:
        nome += f"_{args.rotulo}"
    arq = pasta / f"{nome}.json"
    arq.write_text(json.dumps({"url": url, "modo": args.modo, "inicio": inicio.isoformat(timespec="seconds"),
                               "gnodebs": args.gnodebs, "rodadas": rodadas}, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"\nSalvo: {arq}")


if __name__ == "__main__":
    main()
