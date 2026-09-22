"""
Diagnostica e corrige o problema de login: a coluna tb_usuario.senha_hash é
CHAR(64) (tamanho fixo), mas hash bcrypt tem 60 caracteres — o Postgres
completa com espaços até 64, corrompendo o hash e causando "Invalid salt".

Uso:
  python fix_login.py                     -> lista os usuários e mostra o problema
  python fix_login.py <login> <senha_nova> -> corrige a coluna e define uma senha nova bcrypt

Exemplo:
  python fix_login.py admin admin123
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

import psycopg2
import bcrypt

conn = psycopg2.connect(
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
)
conn.autocommit = True

with conn.cursor() as cur:
    # Mostra o tipo/tamanho atual da coluna
    cur.execute("""
        SELECT data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'tb_usuario' AND column_name = 'senha_hash'
    """)
    tipo, tamanho = cur.fetchone()
    print(f"Coluna senha_hash hoje: tipo={tipo}, tamanho={tamanho}")

    cur.execute("SELECT id_usuario, login, length(senha_hash), senha_hash FROM tb_usuario ORDER BY id_usuario")
    usuarios = cur.fetchall()
    print("\nUsuarios cadastrados:")
    for id_usuario, login, tamanho_hash, hash_ in usuarios:
        print(f"  id={id_usuario}  login={login!r}  tamanho_hash={tamanho_hash}  hash={hash_!r}")

    if len(sys.argv) == 3:
        login_alvo, senha_nova = sys.argv[1], sys.argv[2]

        print(f"\nCorrigindo a coluna senha_hash para VARCHAR(255) (sem padding)...")
        cur.execute("ALTER TABLE tb_usuario ALTER COLUMN senha_hash TYPE VARCHAR(255);")
        print("  OK.")

        print(f"Gerando novo hash bcrypt para a senha informada...")
        novo_hash = bcrypt.hashpw(senha_nova.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        print(f"  hash gerado ({len(novo_hash)} caracteres): {novo_hash}")

        cur.execute(
            "UPDATE tb_usuario SET senha_hash = %s WHERE login = %s RETURNING id_usuario",
            (novo_hash, login_alvo),
        )
        atualizado = cur.fetchone()
        if atualizado:
            print(f"\nSenha do usuario '{login_alvo}' atualizada com sucesso (id_usuario={atualizado[0]}).")
            print(f"Agora faca login no frontend/Swagger com:")
            print(f"  login: {login_alvo}")
            print(f"  senha: {senha_nova}")
        else:
            print(f"\nERRO: nenhum usuario encontrado com login={login_alvo!r}.")
    else:
        print("\nPara corrigir, rode: python fix_login.py <login> <senha_nova>")
        print("Exemplo: python fix_login.py admin admin123")

conn.close()
