from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import ALLOW_ORIGINS
from .database import Base, engine
from .routers.upload import router as upload_router
from .routers.query import router as query_router
from .routers.auth import router as auth_router
from .routers.episodes import router as episodes_router
from .logger import setup_logger


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用。

    配置项:
        - 跨域：允许前端开发地址访问。
        - 路由：注册上传与查询路由。
        - 数据库：创建所有模型表（仅在首次启动时生效）。

    返回:
        FastAPI 应用实例。
    """
    app = FastAPI(title="Cognito Knowledge Builder", version="0.2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 创建数据库表
    Base.metadata.create_all(bind=engine)

    # 注册路由
    app.include_router(auth_router)
    app.include_router(upload_router)
    app.include_router(episodes_router)
    app.include_router(query_router)

    return app


logger = setup_logger()
app = create_app()