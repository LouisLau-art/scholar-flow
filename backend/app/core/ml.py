import hashlib
import threading
from functools import lru_cache
from typing import List


_MODEL_LOCK = threading.Lock()


def hash_source_text(text: str) -> str:
    """
    为 embedding 输入文本生成哈希，用于幂等跳过重复索引。

    中文注释:
    - 只要“研究兴趣 + 历史标题”不变，就无需重复算向量，减少 CPU 消耗。
    """

    normalized = (text or "").strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


@lru_cache(maxsize=4)
def _load_sentence_transformer(model_name: str):
    """
    延迟加载本地向量模型。

    中文注释:
    - sentence-transformers 首次加载可能触发模型下载；生产环境建议预热/离线缓存。
    - 这里加锁避免并发请求时重复加载同一模型。
    """

    with _MODEL_LOCK:
        from sentence_transformers import SentenceTransformer  # 延迟 import，避免测试环境强制拉起依赖

        return SentenceTransformer(model_name)


def embed_text(text: str, model_name: str) -> List[float]:
    """
    将文本向量化为 384 维 embedding。

    中文注释:
    - 我们在模型侧开启 normalize_embeddings，便于将 cosine distance 映射为 score = 1 - distance。
    - 必须严格在本地执行（不调用外部 AI API）。
    """

    model = _load_sentence_transformer(model_name)
    vectors = model.encode([text or ""], normalize_embeddings=True)
    vec = vectors[0].tolist()
    return vec

