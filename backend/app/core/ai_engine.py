import os
import json
from openai import OpenAI
from typing import Dict, Any

# 初始化 OpenAI 客户端 (需配置环境变量 OPENAI_API_KEY)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

async def parse_manuscript_metadata(content: str) -> Dict[str, Any]:
    """
    调用 OpenAI GPT-4o 解析稿件文本并提取结构化元数据
    
    中文注释:
    1. 使用 json_mode 确保返回的是合法的 JSON 格式。
    2. 提取的核心字段包括：title (标题), abstract (摘要), authors (作者列表)。
    3. 该逻辑为“显性逻辑”，解析结果直接用于填充前端投稿表单。
    """
    prompt = f"""
    你是一个专业的学术助理。请从以下提供的论文文本中提取关键元数据。
    返回格式必须为 JSON，包含以下字段：
    - title: 论文的完整标题
    - abstract: 论文摘要
    - authors: 作者姓名列表（数组）

    论文文本内容：
    {content[:4000]}  # 限制输入长度以节省 Token
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a metadata extraction assistant that outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # 解析返回的 JSON 内容
        metadata = json.loads(response.choices[0].message.content)
        return metadata
    except Exception as e:
        # 如果解析失败，返回空结构，触发前端的手动回退机制 (Fallback)
        print(f"AI 解析元数据失败: {str(e)}")
        return {"title": "", "abstract": "", "authors": []}
