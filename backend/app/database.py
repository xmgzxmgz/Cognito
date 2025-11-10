from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


class Base(DeclarativeBase):
    """
    SQLAlchemy 基类，所有 ORM 模型继承自该类。
    """


def get_database_url() -> str:
    """
    构建 MySQL 数据库连接 URL。

    返回:
        形如 mysql+pymysql://user:pass@host:port/db 的连接字符串。
    """
    return f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)