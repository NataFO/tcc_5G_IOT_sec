"""
Cria um banco de dados LOCAL novo e limpo para os testes (tcc5g_local), com a
estrutura atual do sistema (db/01_criar_tabelas.sql), o usuário admin e um
dispositivo de exemplo. No fim, aponta o backend/.env e o backend/Local.env
para esse banco novo.

Por que um banco novo: o banco local antigo ("postgres") foi criado com uma
versão mais antiga das tabelas (a tb_dispositivo nem tem a coluna ip_address).
Em vez de apagar o que existe lá, este script cria outro banco ao lado —
nada do banco antigo é alterado ou apagado.

Segurança: o script SÓ roda se o .env apontar para o PostgreSQL da sua
máquina (localhost / 127.0.0.1). Ele se recusa a mexer no banco do Railway.

Uso (dentro da pasta backend, com o venv ativo):
  python preparar_banco_local.py
"""
import getpass
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

PASTA_BACKEND = Path(__file__).resolve().parent
RAIZ = PASTA_BACKEND.parent
DDL = RAIZ / "db" / "01_criar_tabelas.sql"
NOVO_BANCO = "tcc5g_local"

load_dotenv(PASTA_BACKEND / ".env")
HOST = os.getenv("DB_HOST", "localhost")
PORTA = os.getenv("DB_PORT", "5432")
BANCO_ATUAL = os.getenv("DB_NAME")
USUARIO = os.getenv("DB_USER")
SENHA_BD = os.getenv("DB_PASSWORD")

if HOST not in ("localhost", "127.0.0.1", "::1"):
    sys.exit(f"PAREI: o .env aponta para '{HOST}', que não é a sua máquina.\n"
             "Este script só mexe no PostgreSQL local. Troque o .env para o Local.env e rode de novo.")
if not DDL.exists():
    sys.exit(f"ERRO: não encontrei {DDL}")

import bcrypt
import psycopg2
from psycopg2 import sql


def conectar(banco):
    conn = psycopg2.connect(host=HOST, port=PORTA, dbname=banco, user=USUARIO, password=SENHA_BD)
    conn.autocommit = True
    return conn


print(f"PostgreSQL local em {HOST}:{PORTA} (usuário {USUARIO})")

# 1) Cria o banco novo, se ainda não existir
# (sem "with conn": no psycopg2 ele abre uma transação, e CREATE DATABASE
#  não pode rodar dentro de transação)
conn = conectar(BANCO_ATUAL)
with conn.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (NOVO_BANCO,))
    if cur.fetchone():
        print(f"[1/4] Banco '{NOVO_BANCO}' já existe — vou reaproveitar.")
    else:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(NOVO_BANCO)))
        print(f"[1/4] Banco '{NOVO_BANCO}' criado.")
conn.close()

conn = conectar(NOVO_BANCO)
with conn.cursor() as cur:
    # 2) Tabelas, a partir do script SQL oficial do projeto
    cur.execute("SELECT to_regclass('public.tb_usuario') IS NOT NULL")
    if cur.fetchone()[0]:
        print("[2/4] Tabelas já existem — pulei.")
    else:
        cur.execute(DDL.read_text(encoding="utf-8"))
        print(f"[2/4] Tabelas criadas a partir de {DDL.relative_to(RAIZ)}.")

    # 3) Usuário admin, com a senha que você escolher agora
    cur.execute("SELECT 1 FROM tb_usuario WHERE login = 'admin'")
    if cur.fetchone():
        print("[3/4] Usuário 'admin' já existe — pulei.")
    else:
        print("[3/4] Escolha a senha do usuário 'admin' deste banco local.")
        print("      (enquanto digita, nada aparece na tela — é normal)")
        while True:
            s1 = getpass.getpass("      Senha: ")
            s2 = getpass.getpass("      Repita a senha: ")
            if s1 and s1 == s2:
                break
            print("      As senhas não conferem (ou ficaram vazias). Tente de novo.")
        hash_ = bcrypt.hashpw(s1.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute(
            "INSERT INTO tb_usuario (nome_completo, login, senha_hash, perfil, ativo) "
            "VALUES ('Administrador', 'admin', %s, 'admin', 1)",
            (hash_,),
        )
        print("      Usuário 'admin' criado.")

    cur.execute("SELECT 1 FROM tb_dispositivo WHERE nome_dispositivo = 'Sensor-Teste-01'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO tb_dispositivo (nome_dispositivo, tipo, ip_address, gnodeb_associado, status) "
            "VALUES ('Sensor-Teste-01', 'sensor', '192.168.1.100', 'gNodeB-Centro-01', 'ativo')"
        )
conn.close()

# 4) Aponta o .env e o Local.env para o banco novo (só a linha DB_NAME muda)
for nome in (".env", "Local.env"):
    arq = PASTA_BACKEND / nome
    if not arq.exists():
        continue
    texto = arq.read_text(encoding="utf-8")
    novo, n = re.subn(r"(?m)^DB_NAME=[^\r\n]*$", f"DB_NAME={NOVO_BANCO}", texto)
    if n:
        arq.write_text(novo, encoding="utf-8")
print(f"[4/4] backend/.env e backend/Local.env agora usam DB_NAME={NOVO_BANCO}.")
print(f"      (O banco antigo '{BANCO_ATUAL}' continua intacto.)")

print("\nPronto! Agora reinicie o servidor: Ctrl+C no terminal do uvicorn e depois")
print("  uvicorn main:app --reload")
