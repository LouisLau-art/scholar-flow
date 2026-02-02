import os
import statistics
from typing import Any, Optional, TypedDict

import pdfplumber

def extract_text_from_pdf(file_path: str, *, max_pages: Optional[int] = None, max_chars: Optional[int] = None) -> Optional[str]:
    """
    使用 pdfplumber 从 PDF 文件中提取全文文本
    
    中文注释:
    1. 该函数主要用于投稿后的初步解析。
    2. 如果 PDF 包含多栏布局，pdfplumber 的处理效果通常优于 PyPDF2。
    3. 提取的文本将作为后续“本地元数据解析”的上下文输入（不走远程大模型）。
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


class PdfLayoutLine(TypedDict):
    page: int
    top: float
    size: float
    page_height: float
    text: str


def _group_words_to_lines(words: list[dict[str, Any]], *, y_tol: float = 3.0) -> list[tuple[float, float, str]]:
    """
    将 pdfplumber.extract_words 的结果聚合为“行”。

    返回: [(top, median_font_size, line_text), ...]
    """
    cleaned = [
        w
        for w in (words or [])
        if w.get("text")
        and isinstance(w.get("top"), (int, float))
        and isinstance(w.get("x0"), (int, float))
        and isinstance(w.get("size"), (int, float))
    ]
    if not cleaned:
        return []

    cleaned.sort(key=lambda w: (float(w["top"]), float(w["x0"])))
    lines: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    cur_top: float | None = None

    for w in cleaned:
        top = float(w["top"])
        if cur_top is None:
            cur_top = top
            cur = [w]
            continue
        if abs(top - cur_top) <= y_tol:
            cur.append(w)
            continue
        lines.append(cur)
        cur = [w]
        cur_top = top

    if cur:
        lines.append(cur)

    out: list[tuple[float, float, str]] = []
    for ws in lines:
        text = " ".join(str(x["text"]).strip() for x in ws if str(x.get("text") or "").strip())
        if not text:
            continue
        sizes = [float(x["size"]) for x in ws if isinstance(x.get("size"), (int, float))]
        if not sizes:
            continue
        out.append((float(ws[0]["top"]), float(statistics.median(sizes)), text))
    return out


def extract_text_and_layout_from_pdf(
    file_path: str,
    *,
    max_pages: Optional[int] = None,
    max_chars: Optional[int] = None,
    layout_max_pages: Optional[int] = None,
    layout_max_lines: Optional[int] = None,
) -> tuple[Optional[str], list[PdfLayoutLine]]:
    """
    同时提取文本 + 版面（字号/位置）信息，供本地元数据解析使用。

    中文注释:
    - 解析标题/作者主要依赖“版面结构”（字号/位置），不是 NLP 本身。
    - 为提速：layout 默认只读更少页（通常 1~2 页足够）。
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

        if layout_max_pages is None:
            try:
                layout_max_pages = int(os.environ.get("PDF_LAYOUT_MAX_PAGES", "2"))
            except Exception:
                layout_max_pages = 2
        if layout_max_lines is None:
            try:
                layout_max_lines = int(os.environ.get("PDF_LAYOUT_MAX_LINES", "120"))
            except Exception:
                layout_max_lines = 120

        all_text: list[str] = []
        layout_lines: list[PdfLayoutLine] = []

        with pdfplumber.open(file_path) as pdf:
            pages = pdf.pages[: max_pages if max_pages and max_pages > 0 else 0]
            for page_idx, page in enumerate(pages):
                text = page.extract_text()
                if text:
                    all_text.append(text)

                if layout_max_pages and page_idx < layout_max_pages:
                    try:
                        words = page.extract_words(extra_attrs=["size"])
                        grouped = _group_words_to_lines(words)
                        for top, size, line_text in grouped:
                            layout_lines.append(
                                {
                                    "page": page_idx,
                                    "top": float(top),
                                    "size": float(size),
                                    "page_height": float(getattr(page, "height", 0) or 0),
                                    "text": line_text,
                                }
                            )
                    except Exception:
                        # layout 失败不影响文本提取
                        pass

        combined = "\n".join(all_text)
        if max_chars and max_chars > 0:
            combined = combined[:max_chars]

        if layout_max_lines and layout_max_lines > 0 and len(layout_lines) > layout_max_lines:
            # 只保留更“靠上”的行，通常更像标题/作者/摘要开头
            layout_lines.sort(key=lambda ln: (ln["page"], ln["top"]))
            layout_lines = layout_lines[:layout_max_lines]

        return (combined or None, layout_lines)
    except Exception as e:
        print(f"PDF 文本/版面提取失败: {str(e)}")
        return (None, [])
