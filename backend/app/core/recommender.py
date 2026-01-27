from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict

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
    corpus = [manuscript_abstract] + [" ".join(r['domains']) for r in reviewer_pool]
    
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)
    
    # 计算第一个向量（稿件）与其他向量的相似度
    cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    
    # 组合结果并按得分降序排列
    results = []
    for i, score in enumerate(cosine_sim):
        results.append({
            "reviewer_id": reviewer_pool[i]['id'],
            "email": reviewer_pool[i]['email'],
            "score": round(float(score), 4)
        })
    
    return sorted(results, key=lambda x: x['score'], reverse=True)
