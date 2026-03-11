import json
import os
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from app.core.pdf_processor import PdfLayoutLine


class ManuscriptMetadataResult(BaseModel):
    title: str = ""
    abstract: str = ""
    authors: List[str] = Field(default_factory=list)


def _local_parse():
    """
    中文注释:
    - 运行时回取 manuscripts 模块，保持历史 monkeypatch 路径兼容。
    - 现有测试大量 patch `app.api.v1.manuscripts.parse_manuscript_metadata`，
      这里不能静态绑定本地解析函数，否则 patch 不会生效。
    """
    from app.api.v1 import manuscripts as manuscripts_api

    return manuscripts_api.parse_manuscript_metadata


def _get_gemini_api_key() -> str:
    return str(
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    ).strip()


def _get_gemini_model() -> str:
    model = str(
        os.environ.get("GEMINI_METADATA_MODEL")
        or os.environ.get("GEMINI_MODEL")
        or "gemini-3.1-flash-lite-preview"
    ).strip()
    return model or "gemini-3.1-flash-lite-preview"


def _build_response_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The manuscript title only. Exclude journal name, running headers, and section headings.",
            },
            "abstract": {
                "type": "string",
                "description": "The abstract text only. Exclude the heading label itself.",
            },
            "authors": {
                "type": "array",
                "description": "Ordered list of author names only. Exclude affiliations, degrees, and emails.",
                "items": {"type": "string"},
            },
        },
        "required": ["title", "abstract", "authors"],
    }


def _clean_json_text(raw_text: str) -> str:
    text = str(raw_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _normalize_authors(values: List[Any]) -> List[str]:
    normalized: List[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
    return normalized[:20]


def _summarize_layout_lines(layout_lines: List[PdfLayoutLine], *, limit: int = 30) -> str:
    if not layout_lines:
        return ""
    ordered = sorted(
        (
            ln for ln in layout_lines
            if int(ln.get("page", 0)) == 0 and str(ln.get("text") or "").strip()
        ),
        key=lambda item: (float(item.get("top") or 0), -float(item.get("size") or 0)),
    )
    selected = ordered[:limit]
    rows: List[str] = []
    for line in selected:
        rows.append(
            f"- top={float(line.get('top') or 0):.1f}, size={float(line.get('size') or 0):.1f}, text={str(line.get('text') or '').strip()}"
        )
    return "\n".join(rows)


def _build_prompt(
    content: str,
    *,
    parser_mode: str,
    layout_lines: Optional[List[PdfLayoutLine]] = None,
) -> str:
    prompt_parts = [
        "You extract manuscript metadata for an academic submission system.",
        "Return only the manuscript title, abstract, and ordered author names.",
        "Do not return journal names, running headers, keywords, affiliations, emails, or section headings as title/authors.",
        "If a field is unavailable, return an empty string or empty array.",
        f"Source format: {parser_mode}.",
    ]
    layout_hint = _summarize_layout_lines(layout_lines or [])
    if layout_hint:
        prompt_parts.extend(
            [
                "PDF first-page layout hints (higher font size and smaller top usually indicate title lines):",
                layout_hint,
            ]
        )
    prompt_parts.extend(
        [
            "Document excerpt begins below:",
            content,
        ]
    )
    return "\n\n".join(prompt_parts)


async def extract_metadata_with_gemini(
    content: str,
    *,
    parser_mode: str,
    layout_lines: Optional[List[PdfLayoutLine]] = None,
) -> Optional[Dict[str, Any]]:
    api_key = _get_gemini_api_key()
    if not api_key:
        return None

    try:
        timeout_sec = float(os.environ.get("GEMINI_METADATA_TIMEOUT_SEC", "12"))
    except Exception:
        timeout_sec = 12.0

    try:
        max_chars = int(os.environ.get("GEMINI_METADATA_MAX_CHARS", "18000"))
    except Exception:
        max_chars = 18000

    model = _get_gemini_model()
    prompt = _build_prompt(
        (content or "")[:max_chars],
        parser_mode=parser_mode,
        layout_lines=layout_lines or [],
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseJsonSchema": _build_response_schema(),
        },
    }

    base_url = str(
        os.environ.get("GEMINI_API_BASE_URL")
        or "https://generativelanguage.googleapis.com"
    ).rstrip("/")
    url = f"{base_url}/v1beta/models/{model}:generateContent"

    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        response = await client.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    parts = (
        (data.get("candidates") or [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    raw_text = ""
    for part in parts:
        if isinstance(part, dict) and part.get("text"):
            raw_text = str(part.get("text") or "")
            break
    if not raw_text:
        return None

    parsed = json.loads(_clean_json_text(raw_text))
    metadata = ManuscriptMetadataResult.model_validate(parsed)
    return {
        "title": metadata.title.strip(),
        "abstract": metadata.abstract.strip(),
        "authors": _normalize_authors(metadata.authors),
    }


async def extract_manuscript_metadata(
    content: str,
    *,
    parser_mode: str,
    layout_lines: Optional[List[PdfLayoutLine]] = None,
) -> Dict[str, Any]:
    """
    元数据提取策略：
    1. 优先尝试 Gemini 结构化输出，提高标题/摘要抽取质量。
    2. 若 Gemini 缺字段，则用本地规则补空值。
    3. 若 Gemini 不可用或失败，则完全回退到本地规则。
    """
    local_metadata: Optional[Dict[str, Any]] = None

    try:
        gemini_metadata = await extract_metadata_with_gemini(
            content,
            parser_mode=parser_mode,
            layout_lines=layout_lines or [],
        )
    except Exception as e:
        print(f"Gemini 元数据提取失败，回退本地解析: {e}", flush=True)
        gemini_metadata = None

    if gemini_metadata:
        title = str(gemini_metadata.get("title") or "").strip()
        abstract = str(gemini_metadata.get("abstract") or "").strip()
        authors = _normalize_authors(gemini_metadata.get("authors") or [])

        if not title or not abstract or not authors:
            local_metadata = await _local_parse()(content or "", layout_lines=layout_lines or [])
        if local_metadata:
            title = title or str(local_metadata.get("title") or "").strip()
            abstract = abstract or str(local_metadata.get("abstract") or "").strip()
            authors = authors or _normalize_authors(local_metadata.get("authors") or [])

        return {
            "title": title,
            "abstract": abstract,
            "authors": authors,
        }

    return await _local_parse()(content or "", layout_lines=layout_lines or [])
