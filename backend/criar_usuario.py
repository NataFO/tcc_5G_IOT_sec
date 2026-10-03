"""
Cria (ou reativa com senha nova) um usuário do sistema, com o perfil escolhido.
Usado no CT13 para criar o usuário 'viewer' (somente leitura).

Usa o banco apontado pelo backend/.env. Se o .env apontar para um banco que
não é o da sua máquina (ex.: Railway), o script pede confirmação antes.

Uso (dentro da pasta backend, com o venv ativo):
  python criar_usuario.py viewer viewer
  python criar_usuario.py analista1 analista "Ana Analista"
                          ^login    ^perfil   ^nome (opcional)
"""
import getpass
import os
import sys

from dotenv import load_dotenv

load_dotenv()

PERFIS = ("admin", "analista", "viewer")

if len(sys.argv) < 3 or sys.argv[2] not in PERFIS:
    sys.exit(f"Uso: python criar_usuario.py <login> <{'|'.join(PERFIS)}> [nome completo]")

login, perfil = sys.argv[1], sys.argv[2]
nome = sys.argv[3] if len(sys.argv) > 3 else f"Usuário {login}"

import bcrypt
import psycopg2

host = os.getenv("DB_HOST", "localhost")
banco = os.getenv("DB_NAME")
print(f"Banco: {banco} em {host}")
if host not in ("localhost", "127.0.0.1", "::1"):
    if input("Esse banco NÃO é o da sua máquina. Continuar? (digite SIM) ") != "SIM":
        sys.exit("Cancelado.")

print(f"Escolha a senha do usuário '{login}' (nada aparece enquanto digita).")
while True:
    s1 = getpass.getpass("Senha: ")
    s2 = getpass.getpass("Repita a senha: ")
    if s1 and s1 == s2:
        break
    print("As senhas não conferem (ou ficaram vazias). Tente de novo.")

hash_ = bcrypt.hashpw(s1.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

conn = psycopg2.connect(
    host=host, port=os.getenv("DB_PORT", "5432"), dbname=banco,
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("SELECT id_usuario FROM tb_usuario WHERE login = %s", (login,))
    existente = cur.fetchone()
    if existente:
        cur.execute(
            "UPDATE tb_usuario SET senha_hash = %s, perfil = %s, ativo = 1 WHERE login = %s",
            (hash_, perfil, login),
        )
        print(f"Usuário '{login}' já existia: senha e perfil atualizados (perfil = {perfil}).")
    else:
        cur.execute(
            "INSERT INTO tb_usuario (nome_completo, login, senha_hash, perfil, ativo) "
            "VALUES (%s, %s, %s, %s, 1) RETURNING id_usuario",
            (nome, login, hash_, perfil),
        )
        print(f"Usuário '{login}' criado (id {cur.fetchone()[0]}, perfil = {perfil}).")
conn.close()
