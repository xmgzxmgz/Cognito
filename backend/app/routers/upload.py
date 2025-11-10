import os
import aiofiles
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal, engine
from ..models import Episode
from ..schemas import UploadResponse, EpisodeOut


router = APIRouter(prefix="/upload", tags=["upload"])


def get_db():
    """
    FastAPI 依赖项：获取数据库会话。

    返回:
        SQLAlchemy Session 对象。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/audio", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    接收并保存音频文件，创建节目记录。

    参数:
        file: 上传的音频文件（mp3/mp4/wav/m4a均可）。
        db: 数据库会话。

    返回:
        上传响应，其中包含新建的节目元数据与提示信息。
    """
    allowed_ext = {".mp3", ".mp4", ".wav", ".m4a"}
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in allowed_ext:
        raise HTTPException(status_code=400, detail="不支持的文件类型")

    os.makedirs("data/audio", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    safe_name = file.filename.replace(" ", "_")
    save_path = os.path.join("data/audio", f"{ts}-{safe_name}")

    async with aiofiles.open(save_path, "wb") as out:
        content = await file.read()
        await out.write(content)

    episode = Episode(title=file.filename, file_path=save_path, status="uploaded")
    db.add(episode)
    db.commit()
    db.refresh(episode)

    # 这里后续接入 ASR + 总结流水线（异步任务队列更佳）
    message = "文件已上传。稍后将进行转写与知识提取。"
    return UploadResponse(episode=EpisodeOut.model_validate(episode), message=message)