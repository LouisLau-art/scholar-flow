import re
from typing import Any, Dict, List, Optional

from app.core.pdf_processor import PdfLayoutLine


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


def _score_title_candidate(text: str, *, size: float, top: float) -> float:
    """
    给“可能的标题行”打分：
    - 字号越大越像标题
    - 越靠上越像标题
    - 文本过短/像 header 会被惩罚
    """
    s = (text or "").strip()
    if not _looks_like_title(s):
        return -1e9
    low = s.lower()
    # 一些常见 header/页眉（不一定覆盖完全，但能显著提升命中）
    if any(k in low for k in ("proceedings", "preprint", "conference", "journal", "vol.", "issue", "issn")):
        penalty = 20.0
    else:
        penalty = 0.0
    length_bonus = min(len(s), 120) / 10.0
    # top 越小越靠上；适当降低 top 的影响，避免第一页页眉误判
    return (size * 10.0) + length_bonus - (top / 40.0) - penalty


def _extract_title_from_layout(layout: List[PdfLayoutLine]) -> str:
    page0 = [ln for ln in (layout or []) if int(ln.get("page", 0)) == 0 and (ln.get("text") or "").strip()]
    if not page0:
        return ""

    # 只看第一页上半部分更稳（标题通常在上半部分）
    top_region: list[PdfLayoutLine] = []
    for ln in page0:
        h = float(ln.get("page_height") or 0)
        if h > 0 and float(ln.get("top") or 0) <= h * 0.45:
            top_region.append(ln)
    if not top_region:
        top_region = page0

    best: PdfLayoutLine | None = None
    best_score = -1e18
    for ln in top_region:
        text = str(ln.get("text") or "")
        score = _score_title_candidate(text, size=float(ln.get("size") or 0), top=float(ln.get("top") or 0))
        if score > best_score:
            best_score = score
            best = ln

    if not best or best_score < -1e8:
        return ""

    # 将与标题同行或紧随其后的大字号行拼接为多行标题（最多 3 行）
    ordered = sorted(top_region, key=lambda x: float(x.get("top") or 0))
    try:
        start_idx = next(i for i, x in enumerate(ordered) if x is best)
    except StopIteration:
        start_idx = 0

    base_size = float(best.get("size") or 0) or 0.0
    base_top = float(best.get("top") or 0)
    title_lines: list[str] = []
    last_top = base_top

    for ln in ordered[start_idx : start_idx + 6]:
        text = str(ln.get("text") or "").strip()
        if not text:
            continue
        top = float(ln.get("top") or 0)
        size = float(ln.get("size") or 0)
        # 与第一行太远就不拼了
        if top - base_top > 80:
            break
        # 相邻行差太大也不拼（避免拼到作者/机构）
        if size < base_size * 0.82:
            break
        # 防止把页眉拼进来
        if top < base_top - 5:
            continue
        if top - last_top > 35:
            break
        title_lines.append(text)
        last_top = top
        if len(title_lines) >= 3:
            break

    title = " ".join(title_lines).strip()
    if _looks_like_title(title):
        return title
    # 回退：只用 best 行
    return str(best.get("text") or "").strip()


def _extract_authors_from_layout(layout: List[PdfLayoutLine], *, title: str) -> List[str]:
    if not layout:
        return []
    page0 = [ln for ln in layout if int(ln.get("page", 0)) == 0 and (ln.get("text") or "").strip()]
    if not page0:
        return []

    ordered = sorted(page0, key=lambda x: float(x.get("top") or 0))
    # 估算“标题结束位置”：取上半页内、字号接近最大值的行作为标题块
    top_region: list[PdfLayoutLine] = []
    for ln in ordered:
        h = float(ln.get("page_height") or 0)
        if h > 0 and float(ln.get("top") or 0) <= h * 0.55:
            top_region.append(ln)
    if not top_region:
        top_region = ordered[:30]

    max_size = max((float(ln.get("size") or 0) for ln in top_region), default=0.0)
    title_like = [
        ln
        for ln in top_region
        if float(ln.get("size") or 0) >= max_size * 0.82 and _looks_like_title(str(ln.get("text") or ""))
    ]
    title_end_top = max((float(ln.get("top") or 0) for ln in title_like), default=float(top_region[0].get("top") or 0))

    buf: list[str] = []
    for ln in ordered:
        t = str(ln.get("text") or "").strip()
        if not t:
            continue
        top = float(ln.get("top") or 0)
        if top <= title_end_top + 3:
            continue
        # 作者块通常紧跟标题下方，给一个合理窗口避免吸到机构/正文
        if top - title_end_top > 170:
            break
        low = t.lower()
        if low.startswith(("abstract", "keywords", "摘要", "introduction")):
            break
        # 机构/地址等通常包含较多关键字或数字；直接留给 _split_authors 过滤
        buf.append(t)
        if len(" ".join(buf)) > 260:
            break
    return _split_authors(" ".join(buf))


async def parse_manuscript_metadata(content: str, *, layout_lines: Optional[List[PdfLayoutLine]] = None) -> Dict[str, Any]:
    """
    本地元数据解析（无远程大模型、无 HTTP）。

    中文注释:
    - 目标：快速从论文前几页文本中提取 title/abstract/authors，用于前端预填。
    - 该任务不追求 100% 准确率，强调速度与稳定性；失败时允许用户手动填写。
    """
    lines = _non_empty_lines(content)
    if not lines and not layout_lines:
        return {"title": "", "abstract": "", "authors": []}

    # Title：优先用版面信息（字号/位置），更稳也更快；否则退回纯文本启发式
    title = _extract_title_from_layout(layout_lines or [])
    title_idx = 0
    if not title:
        for i, ln in enumerate(lines[:40]):
            if _looks_like_title(ln):
                title = ln.strip()
                title_idx = i
                break

    # Authors：同样优先用版面行（紧跟标题），否则退回文本行
    authors = _extract_authors_from_layout(layout_lines or [], title=title)
    if not authors and lines:
        author_candidates = []
        for ln in lines[title_idx + 1 : title_idx + 8]:
            if ln.lower().startswith(("abstract", "keywords", "摘要", "introduction")):
                break
            author_candidates.append(ln)
        authors = _split_authors(" ".join(author_candidates))

    abstract = _extract_abstract(lines) if lines else ""

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
    }
