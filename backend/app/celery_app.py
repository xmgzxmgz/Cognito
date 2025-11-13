"""
Celery 应用初始化：配置Redis作为broker与结果后端，并定义默认队列。

函数:
    get_celery(): 返回配置好的Celery实例。
"""
from celery import Celery
import os


def get_celery() -> Celery:
    broker_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    backend_url = broker_url
    app = Celery(
        "cognito",
        broker=broker_url,
        backend=backend_url,
        include=["backend.app.tasks"],
    )
    app.conf.task_routes = {
        "backend.app.tasks.transcribe_audio": {"queue": "gpu"},
        "backend.app.tasks.fetch_video_meta": {"queue": "cpu"},
        "backend.app.tasks.process_transcript_task": {"queue": "cpu"},
    }
    app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"]) 
    return app


# 让Celery命令行可发现
celery_app = get_celery()