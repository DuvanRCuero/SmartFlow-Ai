# db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Cargamos las variables de entorno (.env)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/smartflow")

# Creamos el engine y la Session factory
engine = create_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para heredar los modelos ORM
Base = declarative_base()

def get_db():
    """
    Dependency de FastAPI / LangChain tools para obtener una sesión de DB.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
