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
    # 先生成查询向量，再按其维度加载索引，避免硬编码维度不匹配
    vec = embedder.embed_texts([req.question])
    try:
        index.load(dim=vec.shape[1])
    except Exception:
        # 索引尚未构建时，load会新建空索引；此处容错即可
        pass
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