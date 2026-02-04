from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]{2,}")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _tfidf_vector(tokens: List[str], *, idf: Dict[str, float]) -> Dict[str, float]:
    """
    将 tokens 转为稀疏 TF-IDF 向量（dict）。

    中文注释:
    - 为了部署提速，我们不依赖 scikit-learn（它体积大、编译依赖重，CI/部署容易慢）。
    - 这里实现一个足够用于 MVP 的轻量 TF-IDF：tf = count / len(tokens)，idf 使用平滑公式。
    """

    if not tokens:
        return {}

    counts = Counter(tokens)
    denom = float(len(tokens)) or 1.0
    vec: Dict[str, float] = {}
    for term, c in counts.items():
        tf = c / denom
        vec[term] = tf * float(idf.get(term, 0.0))
    return vec


def _cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    if not a or not b:
        return 0.0

    # dot
    dot = 0.0
    # 只遍历较小的 dict，减少开销
    if len(a) <= len(b):
        for k, v in a.items():
            dot += v * float(b.get(k, 0.0))
    else:
        for k, v in b.items():
            dot += v * float(a.get(k, 0.0))

    # norm
    na = math.sqrt(sum(v * v for v in a.values())) or 1.0
    nb = math.sqrt(sum(v * v for v in b.values())) or 1.0
    return dot / (na * nb)


def recommend_reviewers(manuscript_abstract: str, reviewer_pool: List[Dict]) -> List[Dict]:
    """
    基于 TF-IDF 算法推荐匹配的审稿人
    
    中文注释:
    1. 遵循章程: 核心算法必须包含详细的中文注释。
    2. 将稿件摘要与所有审稿人的领域标签汇总，进行向量化处理。
    3. 计算稿件向量与各审稿人向量之间的余弦相似度。
    4. 优雅降级: 如果最大得分低于 0.1，前端应提示“未找到高度匹配的结果”。
    """
    if not manuscript_abstract or not reviewer_pool:
        return []

    # 准备文本语料：稿件摘要 + 每个审稿人的标签
    manuscript_tokens = _tokenize(manuscript_abstract)
    reviewer_texts: List[str] = []
    reviewer_tokens: List[List[str]] = []

    for r in reviewer_pool:
        domains = r.get("domains")
        if isinstance(domains, list):
            text = " ".join(str(d or "") for d in domains)
        else:
            text = str(domains or "")
        reviewer_texts.append(text)
        reviewer_tokens.append(_tokenize(text))

    # 计算 IDF（包含稿件 + reviewer 文档）
    docs = [manuscript_tokens] + reviewer_tokens
    n_docs = len(docs)
    df: Dict[str, int] = {}
    for doc in docs:
        for term in set(doc):
            df[term] = int(df.get(term, 0)) + 1

    # 平滑 IDF：log((1+N)/(1+df)) + 1
    idf = {t: math.log((1.0 + n_docs) / (1.0 + c)) + 1.0 for t, c in df.items()}

    manuscript_vec = _tfidf_vector(manuscript_tokens, idf=idf)

    # 组合结果并按得分降序排列
    results = []
    for i, r in enumerate(reviewer_pool):
        score = _cosine_similarity(manuscript_vec, _tfidf_vector(reviewer_tokens[i], idf=idf))
        results.append({
            "reviewer_id": r.get("id"),
            "email": r.get("email"),
            "score": round(float(score), 4),
        })
    
    return sorted(results, key=lambda x: x['score'], reverse=True)
