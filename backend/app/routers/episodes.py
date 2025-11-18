from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from ..database import SessionLocal
from ..models import Episode, Task
from ..auth import get_current_user
from ..tasks import process_transcript_task
import os


router = APIRouter(prefix="/episodes", tags=["episodes"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TranscriptReq(BaseModel):
    """提交转录文本请求模型。"""
    episode_id: int
    transcript: str


class PageParams(BaseModel):
    """分页参数。"""
    page: int = 1
    size: int = 10
    status: str | None = None


@router.get("")
def list_episodes(page: int = 1, size: int = 10, status: str | None = None, db: Session = Depends(get_db)):
    q = select(Episode)
    if status:
        q = q.where(Episode.status == status)
    total = db.execute(select(Episode).where(Episode.status == status) if status else select(Episode)).scalars().count()
    rows = db.execute(q.offset((page - 1) * size).limit(size)).scalars().all()
    return {"items": [{"id": e.id, "title": e.title, "status": e.status} for e in rows], "page": page, "size": size, "total": total}


# 采用Celery异步处理，不在API进程内实例化Embedder/Index。


@router.post("/transcript")
def submit_transcript(req: TranscriptReq, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    提交转录文本并异步处理。
    需要鉴权。
    """
    ep = db.query(Episode).get(req.episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="节目不存在")

    # 异步执行处理流水线（Celery）
    task = Task(episode_id=req.episode_id, type="transcript_process", status="pending", message="已提交，排队中")
    db.add(task)
    db.commit()
    db.refresh(task)
    run_inline = os.getenv("RUN_INLINE_TASKS", "0").lower() in {"1", "true", "yes"}
    if run_inline:
        try:
            process_transcript_task(task_id=task.id, episode_id=req.episode_id, transcript_text=req.transcript)
        except Exception:
            pass
    else:
        process_transcript_task.delay(task_id=task.id, episode_id=req.episode_id, transcript_text=req.transcript)
    return {"task_id": task.id, "message": "任务已创建"}


@router.get("/tasks/{task_id}")
def task_status(task_id: int, db: Session = Depends(get_db)):
    t = db.query(Task).get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"id": t.id, "status": t.status, "message": t.message, "episode_id": t.episode_id}