from typing import List
import re
from sqlalchemy.orm import Session
from ..models import Episode, Chunk, Task
from ..services.embedder import Embedder, FaissIndexManager
from datetime import datetime


def simple_clean(text: str) -> str:
    """
    深度清洗：去除时间戳、说话人标签、HTML标签、重复空白与常见口语词。

    参数:
        text: 原始文本。
    返回值:
        清洗后文本。
    """
    # 移除WEBVTT/SRT时间戳行
    text = re.sub(r"\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\s+-->\s+\d{1,2}:\d{2}:\d{2}(?:\.\d+)?(?:.*)?", "", text)
    # 移除可能的序号行
    text = re.sub(r"^\d+\s*$", "", text, flags=re.M)
    # 移除说话人标签
    text = re.sub(r"^(?:Speaker\s*\d+|[\u4e00-\u9fa5]{2,10}|[A-Za-z]{2,20})\s*[:：]", "", text, flags=re.M)
    # 去掉HTML/标记
    text = re.sub(r"<[^>]+>", "", text)
    # 常见口语填充词
    fillers = ["嗯", "啊", "那个", "就是", "然后", "你知道", "我觉得", "这个", "呃"]
    for f in fillers:
        text = text.replace(f, "")
    # 合并空白
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def semantic_chunk(text: str, max_chars: int = 800) -> List[str]:
    """
    语义分块：优先段落、其次句子，保证块内容语义完整并控制长度。

    参数:
        text: 输入文本。
        max_chars: 每块最长字符数。
    返回值:
        文本块列表。
    """
    # 先按段落
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    sentences = []
    for p in paragraphs:
        sentences.extend([s.strip() for s in re.split(r"(?<=[。！？!?\.])\s+", p) if s.strip()])

    chunks: List[str] = []
    buf = []
    cur_len = 0
    for s in sentences:
        if cur_len + len(s) + 1 <= max_chars:
            buf.append(s)
            cur_len += len(s) + 1
        else:
            if buf:
                chunks.append(" ".join(buf))
            buf = [s]
            cur_len = len(s)
    if buf:
        chunks.append(" ".join(buf))
    return chunks


def _simple_summarize(text: str, max_len: int = 800) -> str:
    """
    摘要占位：选取前若干句拼接作为简要摘要。
    后续可替换为LLM的Map-Reduce总结。
    """
    sentences = [s.strip() for s in re.split(r"(?<=[。！？!?\.])\s+", text) if s.strip()]
    out = []
    total = 0
    for s in sentences:
        if total + len(s) + 1 > max_len:
            break
        out.append(s)
        total += len(s) + 1
    return " ".join(out)


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
        blocks = semantic_chunk(cleaned)

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

        try:
            vectors = embedder.embed_texts([c.text for c in created_chunks])
            index_manager.load(dim=vectors.shape[1])
            index_manager.add_vectors(vectors, [c.id for c in created_chunks])
        except Exception:
            pass

        # 生成摘要占位
        ep_summary = _simple_summarize(cleaned)
        episode.summary = ep_summary
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