"""
Script de diagnóstico: testa a conexão com o PostgreSQL usando os mesmos
dados do .env, sem precisar subir o FastAPI (e sem carregar o TensorFlow).

Rode com:  python diagnostico_db.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

print("Lendo .env...")
print(f"  DB_HOST = {DB_HOST!r}")
print(f"  DB_PORT = {DB_PORT!r}")
print(f"  DB_NAME = {DB_NAME!r}")
print(f"  DB_USER = {DB_USER!r}")
print(f"  DB_PASSWORD = {'(definida, ' + str(len(DB_PASSWORD)) + ' caracteres)' if DB_PASSWORD else '(vazia/None!)'}")
print()

if not DB_NAME or not DB_USER or not DB_PASSWORD:
    print("ERRO: DB_NAME, DB_USER ou DB_PASSWORD está vazio.")
    print("Confira o arquivo .env dentro da pasta backend/ — cada linha deve")
    print("ser tipo DB_NAME=meubanco (sem aspas, sem espaço antes/depois do =).")
    raise SystemExit(1)

print("Tentando conectar no PostgreSQL...")
try:
    import psycopg2
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=5,
    )
    print("CONECTOU COM SUCESSO!")

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tb_usuario;")
        print(f"  tb_usuario tem {cur.fetchone()[0]} linha(s).")
        cur.execute("SELECT COUNT(*) FROM tb_dispositivo;")
        print(f"  tb_dispositivo tem {cur.fetchone()[0]} linha(s).")
        cur.execute("SELECT id_dispositivo, nome_dispositivo FROM tb_dispositivo;")
        print("  Dispositivos cadastrados:")
        for row in cur.fetchall():
            print(f"    id_dispositivo={row[0]}  nome={row[1]}")

    conn.close()
except Exception as e:
    print("ERRO AO CONECTAR:")
    print(f"  {type(e).__name__}: {e}")
