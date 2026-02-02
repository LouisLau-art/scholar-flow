import os
import json
from typing import Dict, Any
from openai import OpenAI

async def parse_manuscript_metadata(content: str) -> Dict[str, Any]:
    """
    调用豆包大模型 (Doubao) 解析稿件元数据
    
    中文注释:
    1. 使用 OpenAI SDK 兼容模式连接火山引擎 (Volcengine)。
    2. 模型: doubao-seed-1-6-lite-251015。
    3. 强制要求返回 JSON 格式。
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model_id = os.environ.get("OPENAI_MODEL_ID", "doubao-seed-1-6-lite-251015")
    try:
        max_chars = int(os.environ.get("AI_PARSE_MAX_CHARS", "4000"))
    except Exception:
        max_chars = 4000
    
    if not api_key or not base_url:
        print("警告: 缺少 AI 配置，无法解析。")
        return {"title": "", "abstract": "", "authors": []}

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        safe_content = content or ""
        
        prompt = f"""
        你是一个专业的学术助理。请从以下提供的论文文本中提取关键元数据。
        必须严格返回合法的 JSON 格式，不要包含 markdown 标记。
        
        需要提取的字段：
        - title: 论文的完整标题
        - abstract: 论文摘要
        - authors: 作者姓名列表（字符串数组）

        论文文本内容（前{max_chars}字符）：
        {safe_content[:max_chars]}
        """

        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "You are a metadata extraction assistant that outputs raw JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        # 清理可能存在的 markdown 代码块标记
        raw_content = response.choices[0].message.content.strip()
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:-3].strip()
        
        return json.loads(raw_content)
        
    except Exception as e:
        print(f"AI 解析异常: {str(e)}")
        # 降级返回空数据
        return {"title": "", "abstract": "", "authors": []}
