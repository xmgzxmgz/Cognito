from typing import List, Tuple
import os
import json
import numpy as np
import faiss
from fastembed import TextEmbedding


class FaissIndexManager:
    """
    FAISS 索引管理器，负责加载、保存与查询。

    属性:
        index_path: 索引文件路径。
        meta_path: 元数据映射文件路径（faiss向量id -> chunk_id）。
        index: FAISS 索引实例。
        id_map: 向量ID到chunk_id的映射列表。
    """

    def __init__(self, base_dir: str = "data/index"):
        os.makedirs(base_dir, exist_ok=True)
        self.index_path = os.path.join(base_dir, "faiss.index")
        self.meta_path = os.path.join(base_dir, "meta.json")
        self.index = None
        self.id_map: List[int] = []

    def load(self, dim: int):
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            # 采用内积（需向量归一化以等价余弦相似度）
            self.index = faiss.IndexFlatIP(dim)
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                self.id_map = json.load(f)
        else:
            self.id_map = []

    def save(self):
        if self.index:
            faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.id_map, f)

    def add_vectors(self, vectors: np.ndarray, chunk_ids: List[int]):
        # 归一化以用内积近似余弦
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        self.id_map.extend(chunk_ids)
        self.save()

    def search(self, vectors: np.ndarray, top_k: int) -> List[Tuple[int, float]]:
        faiss.normalize_L2(vectors)
        D, I = self.index.search(vectors, top_k)
        results: List[Tuple[int, float]] = []
        for idx, score in zip(I[0], D[0]):
            if idx == -1:
                continue
            chunk_id = self.id_map[idx]
            results.append((chunk_id, float(score)))
        return results


class Embedder:
    """
    文本嵌入器，封装 FastEmbed 的 bge-m3 模型。

    方法:
        embed_texts(texts): 返回numpy数组的嵌入矩阵。
    """

    def __init__(self):
        self.model = TextEmbedding(model_name="BAAI/bge-m3")

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        vectors = list(self.model.embed(texts))
        return np.array(vectors, dtype="float32")