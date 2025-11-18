from fastapi import APIRouter, Depends, HTTPException
import os
from pydantic import BaseModel, AnyUrl
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models import Task
from ..auth import get_current_user
from ..tasks import fetch_video_meta


router = APIRouter(prefix="/intake", tags=["intake"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SubmitURLReq(BaseModel):
    """提交视频URL进行摄入。"""
    url: AnyUrl


@router.post("/submit_url")
def submit_url(req: SubmitURLReq, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """
    接收平台URL并创建异步摄入任务。
    需要鉴权，返回task_id以供前端轮询。
    """
    task = Task(type="intake_url", status="pending", message="已接收URL，等待下载")
    db.add(task)
    db.commit()
    db.refresh(task)

    # 入队下载任务
    run_inline = os.getenv("RUN_INLINE_TASKS", "0").lower() in {"1", "true", "yes"}
    if run_inline:
        try:
            fetch_video_meta(task_id=task.id, source_url=str(req.url))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"任务执行失败: {e}")
    else:
        try:
            fetch_video_meta.delay(task_id=task.id, source_url=str(req.url))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"任务入队失败: {e}")

    return {"task_id": task.id}