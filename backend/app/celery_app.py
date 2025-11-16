"""
Celery 应用初始化：配置 Redis 作为 broker 与结果后端，并按环境动态路由队列。

函数:
    get_celery(): 返回配置好的 Celery 实例。
    - 当 `WHISPER_SKIP_FASTER` 为真（默认真）时，ASR 任务路由到 `cpu` 队列；否则路由到 `gpu`。
    - 其它任务维持在 `cpu` 队列。
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
    # 动态决定 ASR 任务的队列：跳过 faster-whisper 时走 CPU
    skip_faster = os.getenv("WHISPER_SKIP_FASTER", "1").lower() in {"1", "true", "yes"}
    asr_queue = os.getenv("ASR_QUEUE", "cpu" if skip_faster else "gpu")

    app.conf.task_routes = {
        "backend.app.tasks.transcribe_audio": {"queue": asr_queue},
        "backend.app.tasks.fetch_video_meta": {"queue": "cpu"},
        "backend.app.tasks.process_transcript_task": {"queue": "cpu"},
    }
    app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"]) 
    return app


# 让Celery命令行可发现
celery_app = get_celery()