import hashlib
import math
import os
import re
import threading
from functools import lru_cache
from pathlib import Path
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
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as e:
            # 中文注释:
            # - 部署环境可能未安装 sentence-transformers（避免 torch 依赖导致构建/启动过慢）。
            # - 由上层调用在 embed_text 中做降级，不在这里抛出以免影响启动。
            raise RuntimeError(f"sentence-transformers unavailable: {e}") from e

        cache_folder = os.environ.get("SENTENCE_TRANSFORMERS_HOME") or os.environ.get("HF_HOME")
        local_only = (os.environ.get("MATCHMAKING_LOCAL_FILES_ONLY") or "").strip().lower() in {"1", "true", "yes", "on"}
        if local_only:
            # 兼容 huggingface-hub 的离线模式（避免每次启动都触发网络请求）
            os.environ.setdefault("HF_HUB_OFFLINE", "1")

        # 统一把 cache_folder 目录建好，避免某些环境下权限/不存在导致 fallback 到临时目录
        if cache_folder:
            try:
                Path(cache_folder).mkdir(parents=True, exist_ok=True)
            except Exception:
                cache_folder = None

        # SentenceTransformer 在不同版本的参数名可能略有差异，做一次兼容兜底
        try:
            return SentenceTransformer(model_name, cache_folder=cache_folder, local_files_only=local_only)
        except TypeError:
            try:
                return SentenceTransformer(model_name, cache_folder=cache_folder)
            except TypeError:
                return SentenceTransformer(model_name)

def _fallback_embed(text: str) -> List[float]:
    """
    纯 Python 降级 embedding（384 维）。

    中文注释:
    - 目标：让后端在“无 sentence-transformers/torch”的部署环境也能启动并提供基础排序能力。
    - 这不是语义向量，只是基于 token 哈希的稀疏计数向量（L2 normalize），足够用于 MVP 的“可用但不智能”。
    """
    vec = [0.0] * 384
    tokens = re.findall(r"[a-zA-Z0-9]{2,}", (text or "").lower())
    for tok in tokens[:2000]:
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = h[0] % 384
        sign = 1.0 if (h[1] % 2 == 0) else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_text(text: str, model_name: str) -> List[float]:
    """
    将文本向量化为 384 维 embedding。

    中文注释:
    - 我们在模型侧开启 normalize_embeddings，便于将 cosine distance 映射为 score = 1 - distance。
    - 必须严格在本地执行（不调用外部 AI API）。
    """
    try:
        model = _load_sentence_transformer(model_name)
        vectors = model.encode([text or ""], normalize_embeddings=True)
        vec = vectors[0].tolist()
        return vec
    except Exception as e:
        # 中文注释: 降级（不影响主流程）
        print(f"[matchmaking] embed fallback: {e}")
        return _fallback_embed(text)
