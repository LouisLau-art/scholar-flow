import re
from typing import Any, Dict, List, Optional


_STOP_TITLE_PREFIXES = (
    "arxiv",
    "doi",
    "keywords",
    "abstract",
    "摘要",
    "introduction",
)


def _normalize(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def _non_empty_lines(text: str) -> List[str]:
    return [ln.strip() for ln in _normalize(text).split("\n") if ln.strip()]


def _looks_like_title(line: str) -> bool:
    s = (line or "").strip()
    if not s:
        return False
    low = s.lower()
    if any(low.startswith(p) for p in _STOP_TITLE_PREFIXES):
        return False
    if len(s) < 6:
        return False
    # 过长通常不是标题
    if len(s) > 180:
        return False
    # 太像邮箱/链接
    if "@" in s or "http://" in low or "https://" in low:
        return False
    return True


def _split_authors(raw: str) -> List[str]:
    s = (raw or "").strip()
    if not s:
        return []
    # 去掉邮箱与脚注符号
    s = re.sub(r"\S+@\S+", " ", s)
    s = re.sub(r"[\*\d†‡]+", " ", s)
    # 常见分隔符统一成逗号
    s = s.replace(" and ", ",")
    s = s.replace("；", ",").replace("，", ",").replace(";", ",")
    parts = [p.strip() for p in s.split(",") if p.strip()]
    # 过滤明显不是姓名的片段（机构/地址等）
    cleaned: List[str] = []
    for p in parts:
        if len(p) > 60:
            continue
        low = p.lower()
        if any(k in low for k in ("university", "institute", "department", "school", "lab", "china", "email")):
            continue
        cleaned.append(p)
    # 去重保持顺序
    seen = set()
    uniq: List[str] = []
    for a in cleaned:
        key = a.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq[:20]


def _extract_abstract(lines: List[str]) -> str:
    """
    提取摘要：
    - 支持 "Abstract:" / "ABSTRACT—" / 单独一行 "Abstract"
    - 支持中文 "摘要"
    """
    joined = "\n".join(lines)

    # 1) inline: Abstract: xxx
    m = re.search(r"(?is)\babstract\s*[:：\-—]\s*(.+)", joined)
    if m:
        # 截断到常见下一节标题
        tail = m.group(1).strip()
        tail = re.split(r"(?im)^\s*(keywords?|index terms?|introduction|1\s*[\.\)]|i\s*[\.\)])\b", tail)[0].strip()
        return tail[:4000]

    # 2) heading line: Abstract / 摘要
    start_idx: Optional[int] = None
    for i, ln in enumerate(lines):
        low = ln.lower()
        if low in {"abstract", "abstract."} or ln in {"摘要", "摘 要"}:
            start_idx = i + 1
            break
    if start_idx is None:
        return ""

    buf: List[str] = []
    for ln in lines[start_idx:]:
        low = ln.lower()
        if re.match(r"^(keywords?|index terms?)\b", low):
            break
        if re.match(r"^(introduction|1\s*[\.\)]|i\s*[\.\)])\b", low):
            break
        # 空行在 _non_empty_lines 里已过滤，这里直接拼
        buf.append(ln)
        if sum(len(x) for x in buf) > 5000:
            break
    return (" ".join(buf)).strip()[:4000]


async def parse_manuscript_metadata(content: str) -> Dict[str, Any]:
    """
    本地元数据解析（无远程大模型、无 HTTP）。

    中文注释:
    - 目标：快速从论文前几页文本中提取 title/abstract/authors，用于前端预填。
    - 该任务不追求 100% 准确率，强调速度与稳定性；失败时允许用户手动填写。
    """
    lines = _non_empty_lines(content)
    if not lines:
        return {"title": "", "abstract": "", "authors": []}

    # Title：取最早出现的“像标题”的行
    title = ""
    title_idx = 0
    for i, ln in enumerate(lines[:40]):
        if _looks_like_title(ln):
            title = ln.strip()
            title_idx = i
            break

    # Authors：标题后 1~5 行里拼一下（大多数论文作者会紧跟标题）
    author_candidates = []
    for ln in lines[title_idx + 1 : title_idx + 8]:
        if ln.lower().startswith(("abstract", "keywords", "摘要", "introduction")):
            break
        author_candidates.append(ln)
    authors = _split_authors(" ".join(author_candidates))

    abstract = _extract_abstract(lines)

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
    }

