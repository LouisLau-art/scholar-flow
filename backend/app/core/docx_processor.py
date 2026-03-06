import os
import zipfile
from typing import Optional

from lxml import etree


_DOCX_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_text_from_docx(
    file_path: str,
    *,
    max_paragraphs: Optional[int] = None,
    max_chars: Optional[int] = None,
) -> Optional[str]:
    """
    从 .docx 文件提取纯文本（段落级）。

    中文注释:
    1. 仅处理 Office Open XML（.docx）格式；旧版 .doc 不在这里处理。
    2. 默认提取前若干段，避免超长文档导致上传解析超时。
    3. 返回值作为本地元数据解析输入，不依赖远程大模型。
    """
    try:
        if max_paragraphs is None:
            try:
                max_paragraphs = int(os.environ.get("DOCX_PARSE_MAX_PARAGRAPHS", "300"))
            except Exception:
                max_paragraphs = 300
        if max_chars is None:
            try:
                max_chars = int(os.environ.get("DOCX_PARSE_MAX_CHARS", "20000"))
            except Exception:
                max_chars = 20000

        with zipfile.ZipFile(file_path) as archive:
            xml_bytes = archive.read("word/document.xml")

        root = etree.fromstring(xml_bytes)
        paragraphs: list[str] = []
        for paragraph in root.xpath(".//w:body/w:p", namespaces=_DOCX_NAMESPACE):
            text_parts: list[str] = paragraph.xpath(".//w:t/text()", namespaces=_DOCX_NAMESPACE)
            text = "".join(text_parts).strip()
            if text:
                paragraphs.append(text)
            if max_paragraphs and max_paragraphs > 0 and len(paragraphs) >= max_paragraphs:
                break

        combined = "\n".join(paragraphs)
        if max_chars and max_chars > 0:
            combined = combined[:max_chars]
        return combined or None
    except Exception as e:
        print(f"DOCX 文本提取失败: {str(e)}")
        return None

