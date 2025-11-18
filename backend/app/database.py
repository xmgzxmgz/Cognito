from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
import os


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    # 允许通过环境变量 DB_URL 指定开发回退（例如 sqlite:///./data/cognito.db）
    db_url = os.getenv("DB_URL")
    if db_url:
        return db_url
    return f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"


url = get_database_url()
# 为 SQLite 创建目录
if url.startswith("sqlite"):
    os.makedirs("data", exist_ok=True)
engine = create_engine(url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)