"""
Prepara o banco Postgres do Railway para o primeiro uso: cria as 4
tabelas (a partir de db/01_criar_tabelas.sql), cadastra o usuário admin
e um dispositivo de teste. É idempotente — pode rodar mais de uma vez
sem duplicar nada.

Como usar:
  1. No Railway, abra o serviço Postgres > aba "Variables" e copie os
     valores de PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD.
  2. Cole esses valores no backend/.env (na sua máquina), usando os
     MESMOS nomes que já usamos localmente:
       DB_HOST=<valor de PGHOST>
       DB_PORT=<valor de PGPORT>
       DB_NAME=<valor de PGDATABASE>
       DB_USER=<valor de PGUSER>
       DB_PASSWORD=<valor de PGPASSWORD>
     (Dica: faça isso numa cópia, tipo backend/.env, e depois volte o
     .env original apontando pro Postgres local quando quiser testar
     localmente de novo.)
  3. python seed_cloud_db.py
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    print("ERRO: preencha DB_HOST, DB_NAME, DB_USER e DB_PASSWORD no backend/.env")
    print("      com os dados do Postgres do Railway antes de rodar este script.")
    raise SystemExit(1)

import psycopg2
import bcrypt

# raiz do projeto: backend/seed_cloud_db.py -> backend -> raiz
BASE_DIR = Path(__file__).resolve().parent.parent
DDL_PATH = BASE_DIR / "db" / "01_criar_tabelas.sql"

print(f"Conectando em {DB_HOST}:{DB_PORT}/{DB_NAME} ...")
conn = psycopg2.connect(
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
)
conn.autocommit = True

with conn.cursor() as cur:
    # 1) Tabelas — só cria se ainda não existirem
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'tb_usuario'
    """)
    ja_existe = cur.fetchone()[0] > 0

    if ja_existe:
        print("Tabelas já existem — pulando criação (DDL).")
    else:
        if not DDL_PATH.exists():
            print(f"ERRO: não encontrei {DDL_PATH}")
            raise SystemExit(1)
        print(f"Criando tabelas a partir de {DDL_PATH} ...")
        ddl = DDL_PATH.read_text(encoding="utf-8")
        cur.execute(ddl)
        print("  OK — tabelas criadas.")

    # 2) Usuário admin (login: admin / senha: admin123 — troque depois do primeiro teste)
    cur.execute("SELECT id_usuario FROM tb_usuario WHERE login = 'admin'")
    if cur.fetchone():
        print("Usuário 'admin' já existe — pulando.")
    else:
        hash_ = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8")
        cur.execute(
            """
            INSERT INTO tb_usuario (nome_completo, login, senha_hash, perfil, ativo)
            VALUES ('Administrador', 'admin', %s, 'admin', 1)
            """,
            (hash_,),
        )
        print("Usuário 'admin' criado (login: admin / senha: admin123).")

    # 3) Dispositivo de teste (mesmo usado nos testes locais)
    cur.execute(
        "SELECT id_dispositivo FROM tb_dispositivo WHERE nome_dispositivo = 'Sensor-Teste-01'"
    )
    if cur.fetchone():
        print("Dispositivo 'Sensor-Teste-01' já existe — pulando.")
    else:
        cur.execute(
            """
            INSERT INTO tb_dispositivo (nome_dispositivo, tipo, ip_address, gnodeb_associado, status)
            VALUES ('Sensor-Teste-01', 'sensor', '192.168.1.100', 'gNodeB-Centro-01', 'ativo')
            """
        )
        print("Dispositivo 'Sensor-Teste-01' criado.")

conn.close()
print("\nBanco na nuvem pronto para uso.")
