import os
import json
from typing import Dict, Any

async def parse_manuscript_metadata(content: str) -> Dict[str, Any]:
    """
    解析稿件元数据 (兼容模式)
    
    中文注释:
    1. 懒加载: 只有在调用时才检查 API Key。
    2. 兼容性: 如果未配置 AI 服务，返回 Mock 数据以保证流程跑通。
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    
    # === Mock 模式 (当没有 Key 或 Key 为 mock 值时) ===
    if not api_key or api_key.startswith("sk-mock"):
        print("警告: 未检测到有效 AI Key，使用 Mock 数据返回。")
        return {
            "title": "Mock Title: Deep Learning in Academic Workflows",
            "abstract": "This is a mock abstract generated because no real AI API key was provided. The system is running in demonstration mode.",
            "authors": ["Louis Lau", "AI Assistant"]
        }

    # === 真实调用模式 (保留给未来对接) ===
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        你是一个专业的学术助理。请从以下提供的论文文本中提取关键元数据。
        返回格式必须为 JSON，包含以下字段：
        - title: 论文的完整标题
        - abstract: 论文摘要
        - authors: 作者姓名列表（数组）

        论文文本内容：
        {content[:4000]}
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a metadata extraction assistant that outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"AI 解析异常: {str(e)}")
        # 降级返回空数据，防止前端崩溃
        return {"title": "", "abstract": "", "authors": []}