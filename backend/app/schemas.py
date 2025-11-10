from pydantic import BaseModel
from typing import Optional, List


class EpisodeOut(BaseModel):
    """
    节目实体的输出模型。

    字段:
        id: 节目ID。
        title: 标题。
        file_path: 文件路径。
        status: 处理状态。
    """
    id: int
    title: str
    file_path: str
    status: str

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """
    上传音频后的响应模型。

    字段:
        episode: 节目基本信息。
        message: 结果说明。
    """
    episode: EpisodeOut
    message: str


class QueryRequest(BaseModel):
    """
    查询请求模型。

    字段:
        question: 用户查询问题。
        top_k: 返回的相关块数量，默认3。
    """
    question: str
    top_k: int = 3


class RetrievedChunk(BaseModel):
    """
    召回的知识块信息。

    字段:
        id: 块ID。
        episode_id: 节目ID。
        text: 文本内容。
        start_time: 起始时间。
        end_time: 结束时间。
    """
    id: int
    episode_id: int
    text: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class QueryResponse(BaseModel):
    """
    查询响应模型。

    字段:
        answer: 生成的答案（当前为占位规则生成）。
        chunks: 参与生成的相关知识块列表。
    """
    answer: str
    chunks: List[RetrievedChunk]