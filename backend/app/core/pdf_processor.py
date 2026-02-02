import pdfplumber
from typing import Optional
import os

def extract_text_from_pdf(file_path: str, *, max_pages: Optional[int] = None, max_chars: Optional[int] = None) -> Optional[str]:
    """
    使用 pdfplumber 从 PDF 文件中提取全文文本
    
    中文注释:
    1. 该函数主要用于投稿后的初步解析。
    2. 如果 PDF 包含多栏布局，pdfplumber 的处理效果通常优于 PyPDF2。
    3. 提取的文本将作为后续 AI 解析 (GPT-4o) 的上下文输入。
    """
    try:
        if max_pages is None:
            try:
                max_pages = int(os.environ.get("PDF_PARSE_MAX_PAGES", "5"))
            except Exception:
                max_pages = 5
        if max_chars is None:
            try:
                max_chars = int(os.environ.get("PDF_PARSE_MAX_CHARS", "20000"))
            except Exception:
                max_chars = 20000

        all_text = []
        with pdfplumber.open(file_path) as pdf:
            # 为了解析效率，仅提取前 5 页（通常包含标题、摘要和作者信息）
            pages_to_read = pdf.pages[: max_pages if max_pages and max_pages > 0 else 0]
            for page in pages_to_read:
                text = page.extract_text()
                if text:
                    all_text.append(text)

        combined = "\n".join(all_text)
        if max_chars and max_chars > 0:
            return combined[:max_chars]
        return combined
    except Exception as e:
        # 异常捕获由中间件统一处理，此处仅记录提取失败
        print(f"PDF 文本提取失败: {str(e)}")
        return None
