from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import SessionLocal
from ..models import Chunk
from ..schemas import QueryRequest, QueryResponse, RetrievedChunk
from ..services.embedder import Embedder, FaissIndexManager


router = APIRouter(prefix="/query", tags=["query"])


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


@router.post("", response_model=QueryResponse)
def query(req: QueryRequest, db: Session = Depends(get_db)):
    """
    RAG 查询接口：使用嵌入与FAISS索引召回相关块。

    参数:
        req: 查询请求，包含问题与返回数量。
        db: 数据库会话。

    返回:
        QueryResponse，包含简要答案与相关块。
    """
    embedder = Embedder()
    index = FaissIndexManager()
    # 尝试加载索引（使用默认维度，若未构建将返回空）
    try:
        # 使用bge-m3默认维度768（fastembed）
        index.load(dim=768)
    except Exception:
        pass

    vec = embedder.embed_texts([req.question])
    results = []
    if index.index is not None:
        results = index.search(vec, top_k=req.top_k)

    chunks: list[RetrievedChunk] = []
    if results:
        ids = [cid for cid, _ in results]
        stmt = select(Chunk).where(Chunk.id.in_(ids))
        rows = db.execute(stmt).scalars().all()
        id_to_chunk = {c.id: c for c in rows}
        for cid, score in results:
            c = id_to_chunk.get(cid)
            if c:
                chunks.append(RetrievedChunk(id=c.id, episode_id=c.episode_id, text=c.text, start_time=c.start_time, end_time=c.end_time))

    if not chunks:
        # 回退到LIKE检索
        stmt = select(Chunk).where(Chunk.text.like(f"%{req.question}%")).limit(req.top_k)
        rows = db.execute(stmt).scalars().all()
        chunks = [RetrievedChunk(id=c.id, episode_id=c.episode_id, text=c.text, start_time=c.start_time, end_time=c.end_time) for c in rows]

    answer = "以下为相关知识点摘录：\n" + ("\n---\n".join(c.text[:300] for c in chunks) if chunks else "暂无相关内容")
    return QueryResponse(answer=answer, chunks=chunks)