from datetime import datetime, timezone
import os
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.services.owner_binding_service import get_profile_for_owner

router = APIRouter(tags=["Manuscripts"])

_PUBLISHED_AT_SUPPORTED: bool | None = None


def _m():
    # 中文注释:
    # - 通过运行时导入拿到主模块对象，避免循环导入问题。
    # - 测试里 monkeypatch app.api.v1.manuscripts.* 时，此处也能读取到 patch 后对象。
    from app.api.v1 import manuscripts as manuscripts_api

    return manuscripts_api


def _public_article_url(article_id: str) -> str:
    origin = (os.environ.get("FRONTEND_ORIGIN") or "").strip().rstrip("/")
    if origin:
        return f"{origin}/articles/{article_id}"
    return f"/articles/{article_id}"


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    try:
        # 中文注释: 兼容数据库常见的 Z 结尾时间格式
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _resolve_public_author_names(article: dict) -> list[str]:
    names: list[str] = []
    raw_authors = article.get("authors")
    if isinstance(raw_authors, list):
        for item in raw_authors:
            if isinstance(item, str):
                if item.strip():
                    names.append(item.strip())
                continue
            if not isinstance(item, dict):
                continue
            full_name = str(item.get("full_name") or "").strip()
            first_name = str(item.get("first_name") or item.get("firstName") or "").strip()
            last_name = str(item.get("last_name") or item.get("lastName") or "").strip()
            composed = " ".join(part for part in (first_name, last_name) if part).strip()
            label = full_name or composed
            if label:
                names.append(label)

    if names:
        deduped: list[str] = []
        seen: set[str] = set()
        for name in names:
            key = name.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(name.strip())
        if deduped:
            return deduped

    author_id = str(article.get("author_id") or "").strip()
    if author_id:
        try:
            resp = (
                _m()
                .supabase_admin.table("user_profiles")
                .select("id,full_name")
                .eq("id", author_id)
                .single()
                .execute()
            )
            profile = getattr(resp, "data", None) or {}
            full_name = str(profile.get("full_name") or "").strip()
            if full_name:
                return [full_name]
        except Exception:
            pass

    return ["Author"]


def _escape_bibtex_value(value: str) -> str:
    return str(value or "").replace("{", "\\{").replace("}", "\\}").replace("\n", " ").strip()


def _build_citation_payload(article: dict) -> dict:
    article_id = str(article.get("id") or "")
    published_raw = article.get("published_at") or article.get("created_at")
    published_dt = _parse_iso_datetime(str(published_raw or ""))
    if published_dt is None:
        published_dt = datetime.now(timezone.utc)

    year = str(published_dt.year)
    month = f"{published_dt.month:02d}"
    day = f"{published_dt.day:02d}"
    journal_title = str((article.get("journals") or {}).get("title") or "ScholarFlow Journal")
    title = str(article.get("title") or "Untitled")
    doi = str(article.get("doi") or "").strip()
    authors = _resolve_public_author_names(article)
    key_id = "".join(ch for ch in article_id if ch.isalnum())[:8] or "article"
    bibtex_key = f"scholarflow{year}{key_id}"

    return {
        "article_id": article_id,
        "title": title,
        "journal_title": journal_title,
        "doi": doi,
        "authors": authors,
        "year": year,
        "month": month,
        "day": day,
        "date_slash": f"{year}/{month}/{day}",
        "url": _public_article_url(article_id),
        "bibtex_key": bibtex_key,
    }


def _to_bibtex(payload: dict) -> str:
    lines: list[str] = [f"@article{{{payload['bibtex_key']},"]
    if payload.get("title"):
        lines.append(f"  title = {{{_escape_bibtex_value(payload['title'])}}},")
    if payload.get("journal_title"):
        lines.append(f"  journal = {{{_escape_bibtex_value(payload['journal_title'])}}},")
    if payload.get("authors"):
        author_text = " and ".join(_escape_bibtex_value(author) for author in payload["authors"])
        lines.append(f"  author = {{{author_text}}},")
    if payload.get("year"):
        lines.append(f"  year = {{{payload['year']}}},")
    if payload.get("doi"):
        lines.append(f"  doi = {{{_escape_bibtex_value(payload['doi'])}}},")
    if payload.get("url"):
        lines.append(f"  url = {{{_escape_bibtex_value(payload['url'])}}},")
    lines.append("}")
    return "\n".join(lines)


def _to_ris(payload: dict) -> str:
    lines: list[str] = ["TY  - JOUR"]
    if payload.get("title"):
        lines.append(f"TI  - {payload['title']}")
    for author in payload.get("authors") or []:
        lines.append(f"AU  - {author}")
    if payload.get("journal_title"):
        lines.append(f"JO  - {payload['journal_title']}")
    if payload.get("year"):
        lines.append(f"PY  - {payload['year']}")
    if payload.get("date_slash"):
        lines.append(f"DA  - {payload['date_slash']}")
    if payload.get("doi"):
        lines.append(f"DO  - {payload['doi']}")
    if payload.get("url"):
        lines.append(f"UR  - {payload['url']}")
    lines.append("ER  -")
    return "\n".join(lines) + "\n"


def _get_published_article_for_citation(article_id: UUID) -> dict:
    try:
        ms_resp = (
            _m()
            .supabase_admin.table("manuscripts")
            .select("*")
            .eq("id", str(article_id))
            .eq("status", "published")
            .single()
            .execute()
        )
        manuscript = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if _m()._is_postgrest_single_no_rows_error(str(e)):
            raise HTTPException(status_code=404, detail="Article not found")
        raise

    if not manuscript:
        raise HTTPException(status_code=404, detail="Article not found")

    journal_id = manuscript.get("journal_id")
    manuscript["journals"] = None
    if journal_id:
        try:
            jr_resp = (
                _m()
                .supabase_admin.table("journals")
                .select("id,title,slug,issn")
                .eq("id", str(journal_id))
                .single()
                .execute()
            )
            manuscript["journals"] = getattr(jr_resp, "data", None) or None
        except Exception:
            manuscript["journals"] = None

    return manuscript


@router.get("/manuscripts/published/latest")
async def get_latest_published_articles(limit: int = 6):
    """
    Feature 024: 首页“Latest Articles”数据源（仅 published，按 published_at 倒序）
    """
    global _PUBLISHED_AT_SUPPORTED
    try:
        n = max(1, min(int(limit), 50))
    except Exception:
        n = 6

    try:
        if _PUBLISHED_AT_SUPPORTED is False:
            resp = (
                _m()
                .supabase.table("manuscripts")
                .select("id,title,abstract,doi,created_at,journal_id")
                .eq("status", "published")
                .order("created_at", desc=True)
                .limit(n)
                .execute()
            )
        else:
            try:
                resp = (
                    _m()
                    .supabase.table("manuscripts")
                    .select("id,title,abstract,doi,published_at,journal_id")
                    .eq("status", "published")
                    .order("published_at", desc=True)
                    .limit(n)
                    .execute()
                )
                _PUBLISHED_AT_SUPPORTED = True
            except Exception as e:
                if _m()._is_missing_column_error(str(e)):
                    _PUBLISHED_AT_SUPPORTED = False
                    resp = (
                        _m()
                        .supabase.table("manuscripts")
                        .select("id,title,abstract,doi,created_at,journal_id")
                        .eq("status", "published")
                        .order("created_at", desc=True)
                        .limit(n)
                        .execute()
                    )
                else:
                    raise

        return {"success": True, "data": getattr(resp, "data", None) or []}
    except Exception as e:
        print(f"[LatestArticles] 查询失败: {e}")
        return {"success": False, "data": []}


@router.get("/manuscripts/articles/{id}")
async def get_article_detail(id: UUID):
    try:
        try:
            manuscript_response = (
                _m()
                .supabase.table("manuscripts")
                .select("*")
                .eq("id", str(id))
                .eq("status", "published")
                .single()
                .execute()
            )
            manuscript = manuscript_response.data
        except Exception as e:
            if _m()._is_postgrest_single_no_rows_error(str(e)):
                raise HTTPException(status_code=404, detail="Article not found")
            raise
        if not manuscript:
            raise HTTPException(status_code=404, detail="Article not found")

        owner_raw = manuscript.get("owner_id") or manuscript.get("kpi_owner_id")
        if owner_raw:
            try:
                profile = get_profile_for_owner(UUID(str(owner_raw)))
                if profile:
                    manuscript["owner"] = {
                        "id": profile.get("id"),
                        "full_name": profile.get("full_name"),
                        "email": profile.get("email"),
                    }
            except Exception as e:
                print(f"[OwnerBinding] 获取 owner profile 失败（降级忽略）: {e}")

        journal_id = manuscript.get("journal_id")
        if journal_id:
            journal_response = (
                _m()
                .supabase.table("journals")
                .select("*")
                .eq("id", journal_id)
                .single()
                .execute()
            )
            manuscript["journals"] = journal_response.data
        else:
            manuscript["journals"] = None
        return {"success": True, "data": manuscript}
    except HTTPException:
        raise
    except Exception as e:
        print(f"文章详情查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch article detail")


@router.get("/manuscripts/articles/{id}/citation.bib")
async def download_article_citation_bib(id: UUID):
    article = _get_published_article_for_citation(id)
    payload = _build_citation_payload(article)
    content = _to_bibtex(payload)
    filename = f"scholarflow-{payload['article_id'] or id}.bib"
    return PlainTextResponse(
        content=content,
        media_type="application/x-bibtex; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/manuscripts/articles/{id}/citation.ris")
async def download_article_citation_ris(id: UUID):
    article = _get_published_article_for_citation(id)
    payload = _build_citation_payload(article)
    content = _to_ris(payload)
    filename = f"scholarflow-{payload['article_id'] or id}.ris"
    return PlainTextResponse(
        content=content,
        media_type="application/x-research-info-systems; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/manuscripts/articles/{id}/pdf-signed")
async def get_published_article_pdf_signed(id: UUID):
    """
    公开文章页 PDF 预览：返回 published 稿件的 signed URL。
    """
    try:
        ms_resp = (
            _m()
            .supabase_admin.table("manuscripts")
            .select("id,status,file_path")
            .eq("id", str(id))
            .eq("status", "published")
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if _m()._is_postgrest_single_no_rows_error(str(e)):
            raise HTTPException(status_code=404, detail="Article not found")
        raise
    if not ms:
        raise HTTPException(status_code=404, detail="Article not found")
    file_path = ms.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Article PDF not found")

    signed_url = _m()._get_signed_url_for_manuscripts_bucket(str(file_path))
    return {"success": True, "data": {"signed_url": signed_url}}


@router.get("/manuscripts/articles/{id}/pdf")
async def get_published_article_pdf(id: UUID):
    """
    公开文章页 PDF 下载入口：302 重定向到 signed URL。
    """
    try:
        ms_resp = (
            _m()
            .supabase_admin.table("manuscripts")
            .select("id,status,file_path")
            .eq("id", str(id))
            .eq("status", "published")
            .single()
            .execute()
        )
        ms = getattr(ms_resp, "data", None) or {}
    except Exception as e:
        if _m()._is_postgrest_single_no_rows_error(str(e)):
            raise HTTPException(status_code=404, detail="Article not found")
        raise
    if not ms:
        raise HTTPException(status_code=404, detail="Article not found")
    file_path = ms.get("file_path")
    if not file_path:
        raise HTTPException(status_code=404, detail="Article PDF not found")

    signed_url = _m()._get_signed_url_for_manuscripts_bucket(str(file_path))
    resp = RedirectResponse(url=signed_url, status_code=302)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@router.get("/manuscripts/journals/{slug}")
async def get_journal_detail(slug: str):
    try:
        journal_response = (
            _m().supabase.table("journals").select("*").eq("slug", slug).single().execute()
        )
        journal = journal_response.data
        if not journal:
            raise HTTPException(status_code=404, detail="Journal not found")
        articles_response = (
            _m()
            .supabase.table("manuscripts")
            .select("*")
            .eq("journal_id", journal["id"])
            .eq("status", "published")
            .execute()
        )
        return {"success": True, "journal": journal, "articles": articles_response.data}
    except HTTPException:
        raise
    except Exception as e:
        print(f"期刊详情查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch journal detail")
