from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, LargeBinary, Float, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .database import Base


class Episode(Base):
    """
    直播/录播节目实体。记录音频文件路径与基础元数据。

    字段:
        id: 主键。
        title: 标题或文件名。
        file_path: 音频文件的相对路径。
        created_at: 创建时间。
        status: 处理状态（uploaded, processed, failed）。
    """
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="uploaded")

    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="episode", cascade="all, delete-orphan")
    qas: Mapped[list["QA"]] = relationship("QA", back_populates="episode", cascade="all, delete-orphan")


class Chunk(Base):
    """
    知识块（Chunk）。存储从音频文本中切分出的段落与可选嵌入。

    字段:
        id: 主键。
        episode_id: 关联的节目 ID。
        text: 文本内容。
        start_time: 起始时间（秒）。
        end_time: 结束时间（秒）。
        embedding: 文本嵌入向量（可选，后续可用于向量检索）。
    """
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    episode: Mapped[Episode] = relationship("Episode", back_populates="chunks")

Index("idx_chunks_episode", Chunk.episode_id)


class QA(Base):
    """
    问答对（Q&A）。从主播与观众互动或总结生成的标准问答。

    字段:
        id: 主键。
        episode_id: 关联的节目 ID。
        question: 问题文本。
        answer: 答案文本。
    """
    __tablename__ = "qas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    episode: Mapped[Episode] = relationship("Episode", back_populates="qas")

Index("idx_qas_episode", QA.episode_id)


class User(Base):
    """
    用户实体。支持基础鉴权与权限控制。

    字段:
        id: 主键。
        username: 用户名（唯一）。
        password_hash: 密码哈希（bcrypt）。
        role: 角色（admin/creator/viewer）。
        created_at: 创建时间。
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="creator", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Task(Base):
    """
    异步任务实体。记录转录/索引构建等处理状态。

    字段:
        id: 主键。
        episode_id: 关联节目。
        type: 任务类型（transcript_process/index_build等）。
        status: 状态（pending/running/succeeded/failed）。
        message: 状态说明或错误信息。
        created_at/updated_at: 时间戳。
    """
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    episode_id: Mapped[int | None] = mapped_column(ForeignKey("episodes.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Index("idx_tasks_episode", Task.episode_id)