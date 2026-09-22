from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Carrega as variáveis do arquivo .env
load_dotenv()

# No Railway, o plugin PostgreSQL expõe a variável DATABASE_URL pronta
# (Settings > Variables do serviço backend > "Add a Reference" >
# Postgres.DATABASE_URL). Se ela existir, usamos direto; senão, montamos
# a partir das variáveis separadas, como no ambiente local (.env).
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = os.getenv("DB_PORT", "5432")
    DB_NAME     = os.getenv("DB_NAME")
    DB_USER     = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Alguns provedores (Railway incluso, às vezes) ainda usam o prefixo
# antigo "postgres://"; o SQLAlchemy 2.x exige "postgresql://".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Cria a conexão com o banco
engine = create_engine(DATABASE_URL)

# Cria a sessão — é por ela que fazemos consultas e inserções
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos ORM
Base = declarative_base()

# Função que abre e fecha a sessão automaticamente
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()