from typing import List
from sqlalchemy.orm import Session
from .models import Episode, Chunk, Task
from .services.embedder import Embedder, FaissIndexManager
from datetime import datetime


def simple_clean(text: str) -> str:
    """
    文本清洗：移除多余空白与口语词的极简示例。

    参数:
        text: 原始文本。
    返回值:
        清洗后文本。
    """
    fillers = ["嗯", "啊", "那个", "就是", "然后"]
    for f in fillers:
        text = text.replace(f, "")
    return " ".join(text.split())


def simple_chunk(text: str, size: int = 500, overlap: int = 50) -> List[str]:
    """
    固定长度+重叠法的简易分块。

    参数:
        text: 输入文本。
        size: 每块长度。
        overlap: 重叠长度。
    返回值:
        文本块列表。
    """
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + size)
        chunks.append(text[start:end])
        start = start + size - overlap
        if start < 0:
            break
    return chunks


def process_transcript(db: Session, episode_id: int, transcript_text: str, index_manager: FaissIndexManager, embedder: Embedder) -> Task:
    """
    处理转录文本：清洗→分块→入库→嵌入→更新FAISS索引。

    参数:
        db: 数据库会话。
        episode_id: 节目ID。
        transcript_text: 原始转录文本。
        index_manager: FAISS 索引管理器。
        embedder: 嵌入器。

    返回值:
        Task 任务对象（状态已更新）。
    """
    task = Task(episode_id=episode_id, type="transcript_process", status="running", message="处理中...")
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        cleaned = simple_clean(transcript_text)
        blocks = simple_chunk(cleaned)

        episode = db.query(Episode).get(episode_id)
        if not episode:
            raise ValueError("节目不存在")

        created_chunks: List[Chunk] = []
        for b in blocks:
            c = Chunk(episode_id=episode_id, text=b)
            db.add(c)
            created_chunks.append(c)
        db.commit()
        for c in created_chunks:
            db.refresh(c)

        vectors = embedder.embed_texts([c.text for c in created_chunks])
        index_manager.load(dim=vectors.shape[1])
        index_manager.add_vectors(vectors, [c.id for c in created_chunks])

        episode.status = "processed"
        db.add(episode)
        task.status = "succeeded"
        task.message = f"已处理 {len(created_chunks)} 个块"
    except Exception as e:
        task.status = "failed"
        task.message = str(e)
    finally:
        task.updated_at = datetime.utcnow()
        db.add(task)
        db.commit()
        db.refresh(task)
    return task