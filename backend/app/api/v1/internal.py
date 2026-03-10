import json
import logging
import os
from uuid import UUID

import httpx
import resend
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.config import get_admin_api_key
from app.models.platform_readiness import (
    PlatformReadinessCheck,
    PlatformReadinessResponse,
    PlatformRuntimeVersionResponse,
    PlatformReadinessStatus,
)
from app.core.scheduler import ChaseScheduler
from app.core.security import require_admin_key
from app.models.release_validation import (
    CreateRunRequest,
    FinalizeRequest,
    ReadinessRequest,
    RegressionRequest,
)
from app.services.release_validation_service import ReleaseValidationService
from app.services.doi_service import DOIService

router = APIRouter(prefix="/internal", tags=["Internal"])
logger = logging.getLogger(__name__)


def _is_local_url(value: str) -> bool:
    lowered = value.strip().lower()
    return "localhost" in lowered or "127.0.0.1" in lowered


def _extract_sender_domain(sender: str) -> str | None:
    normalized = sender.strip()
    if not normalized:
        return None
    if "<" in normalized and ">" in normalized:
        normalized = normalized.split("<", 1)[1].split(">", 1)[0].strip()
    if "@" not in normalized:
        return None
    return normalized.rsplit("@", 1)[-1].strip().lower() or None


def _looks_like_email_address(value: str) -> bool:
    normalized = value.strip()
    if not normalized or "@" not in normalized:
        return False
    local_part, domain = normalized.rsplit("@", 1)
    return bool(local_part.strip()) and "." in domain and " " not in normalized


def _probe_resend_sender_domain_status(
    api_key: str,
    sender_domain: str | None,
) -> tuple[PlatformReadinessStatus, str, dict[str, object]]:
    evidence: dict[str, object] = {
        "provider_probe": "resend",
        "sender_domain": sender_domain,
        "domain_found": False,
        "domain_verified": False,
    }
    if not sender_domain:
        return (
            PlatformReadinessStatus.BLOCKED,
            "EMAIL_SENDER 缺少可识别的邮箱域名",
            evidence,
        )

    try:
        response = httpx.get(
            "https://api.resend.com/domains",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5.0,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        evidence["probe_error"] = type(exc).__name__
        return (
            PlatformReadinessStatus.FAILED,
            f"Resend 域名探测失败：{type(exc).__name__}",
            evidence,
        )

    rows = payload.get("data") if isinstance(payload, dict) else None
    domains = rows if isinstance(rows, list) else []
    matched = next(
        (
            item
            for item in domains
            if isinstance(item, dict) and str(item.get("name") or "").strip().lower() == sender_domain
        ),
        None,
    )
    if not matched:
        return (
            PlatformReadinessStatus.FAILED,
            f"Resend 中未找到 sender 域名：{sender_domain}",
            evidence,
        )

    evidence["domain_found"] = True
    domain_status = str(matched.get("status") or "").strip().lower()
    evidence["resend_domain_status"] = domain_status or None
    if domain_status != "verified":
        return (
            PlatformReadinessStatus.FAILED,
            f"Resend sender 域名未验证：{sender_domain} ({domain_status or 'unknown'})",
            evidence,
        )

    evidence["domain_verified"] = True
    return (
        PlatformReadinessStatus.PASSED,
        f"sender 域名已在 Resend 验证：{sender_domain}",
        evidence,
    )


def _build_platform_readiness_checks() -> list[PlatformReadinessCheck]:
    checks: list[PlatformReadinessCheck] = []

    admin_key = get_admin_api_key()
    checks.append(
        PlatformReadinessCheck(
            key="admin_key.configured",
            title="ADMIN_API_KEY 已配置",
            status=PlatformReadinessStatus.PASSED if admin_key else PlatformReadinessStatus.BLOCKED,
            detail="内部接口可使用 ADMIN_API_KEY 鉴权" if admin_key else "ADMIN_API_KEY 未配置，内部 smoke / readiness 无法运行",
            evidence={"configured": bool(admin_key)},
        )
    )

    magic_link_secret = (os.environ.get("MAGIC_LINK_JWT_SECRET") or "").strip()
    fallback_secret = (os.environ.get("SECRET_KEY") or "").strip()
    checks.append(
        PlatformReadinessCheck(
            key="magic_link_secret.configured",
            title="Reviewer Magic Link 密钥已配置",
            status=(
                PlatformReadinessStatus.PASSED
                if magic_link_secret
                else PlatformReadinessStatus.BLOCKED
            ),
            detail=(
                "MAGIC_LINK_JWT_SECRET 已配置"
                if magic_link_secret
                else "仅检测到 SECRET_KEY 兜底，部署基线要求显式配置 MAGIC_LINK_JWT_SECRET"
                if fallback_secret
                else "MAGIC_LINK_JWT_SECRET 未配置"
            ),
            evidence={
                "magic_link_secret_configured": bool(magic_link_secret),
                "secret_key_fallback_configured": bool(fallback_secret),
            },
        )
    )

    frontend_base_url = (os.environ.get("FRONTEND_BASE_URL") or "").strip()
    checks.append(
        PlatformReadinessCheck(
            key="frontend_base_url.ready",
            title="FRONTEND_BASE_URL 指向线上地址",
            status=(
                PlatformReadinessStatus.BLOCKED
                if not frontend_base_url
                else PlatformReadinessStatus.FAILED
                if _is_local_url(frontend_base_url)
                else PlatformReadinessStatus.PASSED
            ),
            detail=(
                "FRONTEND_BASE_URL 未配置"
                if not frontend_base_url
                else f"FRONTEND_BASE_URL 指向本地地址：{frontend_base_url}"
                if _is_local_url(frontend_base_url)
                else f"FRONTEND_BASE_URL={frontend_base_url}"
            ),
            evidence={
                "configured": bool(frontend_base_url),
                "is_local": _is_local_url(frontend_base_url) if frontend_base_url else False,
            },
        )
    )

    frontend_origin = (os.environ.get("FRONTEND_ORIGIN") or "").strip()
    checks.append(
        PlatformReadinessCheck(
            key="frontend_origin.ready",
            title="FRONTEND_ORIGIN 指向线上地址",
            status=(
                PlatformReadinessStatus.BLOCKED
                if not frontend_origin
                else PlatformReadinessStatus.FAILED
                if _is_local_url(frontend_origin)
                else PlatformReadinessStatus.PASSED
            ),
            detail=(
                "FRONTEND_ORIGIN 未配置"
                if not frontend_origin
                else f"FRONTEND_ORIGIN 指向本地地址：{frontend_origin}"
                if _is_local_url(frontend_origin)
                else f"FRONTEND_ORIGIN={frontend_origin}"
            ),
            evidence={
                "configured": bool(frontend_origin),
                "is_local": _is_local_url(frontend_origin) if frontend_origin else False,
            },
        )
    )

    resend_api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
    smtp_host = (os.environ.get("SMTP_HOST") or "").strip()
    smtp_from_email = (os.environ.get("SMTP_FROM_EMAIL") or "").strip()
    checks.append(
        PlatformReadinessCheck(
            key="email_provider.configured",
            title="邮件 provider 已配置",
            status=(
                PlatformReadinessStatus.PASSED
                if resend_api_key or smtp_host
                else PlatformReadinessStatus.BLOCKED
            ),
            detail=(
                "当前使用 Resend"
                if resend_api_key
                else "当前使用 SMTP"
                if smtp_host
                else "RESEND_API_KEY 与 SMTP_HOST 均未配置，邮件发送不可用"
            ),
            evidence={
                "uses_resend": bool(resend_api_key),
                "uses_smtp": bool(smtp_host),
            },
        )
    )

    email_sender = (
        (os.environ.get("EMAIL_SENDER") or "").strip()
        if resend_api_key
        else smtp_from_email
    )
    sender_domain = _extract_sender_domain(email_sender or "")
    sender_uses_fallback = bool(
        resend_api_key and (sender_domain == "resend.dev" or "onboarding@resend.dev" in email_sender.lower())
    )
    smtp_sender_invalid = bool(smtp_host and (not email_sender or not _looks_like_email_address(email_sender)))
    resend_probe_status = PlatformReadinessStatus.BLOCKED
    resend_probe_detail = "未执行 Resend sender 探测"
    resend_probe_evidence: dict[str, object] = {
        "provider_probe": "resend",
        "sender_domain": sender_domain,
    }
    if resend_api_key and email_sender and not sender_uses_fallback:
        resend_probe_status, resend_probe_detail, resend_probe_evidence = _probe_resend_sender_domain_status(
            resend_api_key,
            sender_domain,
        )
    checks.append(
        PlatformReadinessCheck(
            key="email_sender.ready",
            title="邮件发件人已配置正式地址",
            status=(
                PlatformReadinessStatus.BLOCKED
                if not email_sender and resend_api_key
                else PlatformReadinessStatus.BLOCKED
                if smtp_host and not email_sender
                else PlatformReadinessStatus.BLOCKED
                if not resend_api_key and not smtp_host
                else PlatformReadinessStatus.FAILED
                if smtp_sender_invalid
                else PlatformReadinessStatus.FAILED
                if sender_uses_fallback
                else resend_probe_status
                if resend_api_key
                else PlatformReadinessStatus.PASSED
            ),
            detail=(
                "未配置任何邮件 provider"
                if not resend_api_key and not smtp_host
                else "EMAIL_SENDER 未配置"
                if resend_api_key and not email_sender
                else "SMTP_FROM_EMAIL 未配置"
                if smtp_host and not email_sender
                else f"SMTP_FROM_EMAIL 不是合法邮箱：{email_sender}"
                if smtp_sender_invalid
                else f"当前仍使用 Resend 开发发件人：{email_sender}"
                if sender_uses_fallback
                else resend_probe_detail
                if resend_api_key
                else f"sender={email_sender}"
            ),
            evidence={
                "configured": bool(email_sender),
                "sender_domain": sender_domain,
                "uses_resend_dev_fallback": sender_uses_fallback,
                "provider": "resend" if resend_api_key else "smtp" if smtp_host else None,
                "smtp_sender_email_like": _looks_like_email_address(email_sender) if smtp_host else None,
                **(resend_probe_evidence if resend_api_key else {}),
            },
        )
    )

    supabase_url = (os.environ.get("SUPABASE_URL") or "").strip()
    supabase_service_key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY") or "").strip()
    checks.append(
        PlatformReadinessCheck(
            key="supabase.core_configured",
            title="Supabase 核心配置已存在",
            status=(
                PlatformReadinessStatus.PASSED
                if supabase_url and supabase_service_key
                else PlatformReadinessStatus.BLOCKED
            ),
            detail=(
                "SUPABASE_URL 与 service role 已配置"
                if supabase_url and supabase_service_key
                else "SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY 缺失"
            ),
            evidence={
                "url_configured": bool(supabase_url),
                "service_key_configured": bool(supabase_service_key),
            },
        )
    )

    return checks


def _derive_platform_readiness_status(checks: list[PlatformReadinessCheck]) -> PlatformReadinessStatus:
    if any(check.status == PlatformReadinessStatus.FAILED for check in checks):
        return PlatformReadinessStatus.FAILED
    if any(check.status == PlatformReadinessStatus.BLOCKED for check in checks):
        return PlatformReadinessStatus.BLOCKED
    return PlatformReadinessStatus.PASSED


@router.post("/cron/chase-reviews")
async def chase_reviews(_admin: None = Depends(require_admin_key)):
    """
    触发自动催办逻辑（内部接口）
    """
    scheduler = ChaseScheduler()
    result = scheduler.run()
    return {"success": True, **result}


@router.post("/cron/doi-tasks")
async def run_doi_tasks(
    limit: int = Query(default=5, ge=1, le=50),
    _admin: None = Depends(require_admin_key),
):
    """
    触发 DOI 任务消费（内部接口）。

    中文注释:
    - 用于 Hugging Face / CI cron 定时调用，避免单独常驻 worker 进程。
    """
    result = await DOIService().process_due_tasks(limit=limit)
    return {"success": True, "data": result}


@router.get("/sentry/test-error")
async def sentry_test_error(_admin: None = Depends(require_admin_key)):
    """
    Sentry 联调用的“已知错误”端点（Feature 027）。

    中文注释:
    - 仅内部接口（需 ADMIN_API_KEY），避免公网被滥用。
    - 目的：验证 Sentry 能捕获后端异常 + 堆栈。
    """
    raise RuntimeError("Sentry test error (backend)")


@router.get("/platform-readiness", response_model=PlatformReadinessResponse)
async def get_platform_readiness(_admin: None = Depends(require_admin_key)):
    """
    平台运行前置条件检查（内部接口）。

    中文注释:
    - 仅返回“是否配置正确”的布尔/域名信息，不泄露真实 secret。
    - 用于部署后 smoke gate，尽早发现 sender/frontend origin/localhost 之类配置漂移。
    """
    checks = _build_platform_readiness_checks()
    return PlatformReadinessResponse(
        status=_derive_platform_readiness_status(checks),
        checks=checks,
    )


@router.get("/runtime-version", response_model=PlatformRuntimeVersionResponse)
async def get_runtime_version(_admin: None = Depends(require_admin_key)):
    """
    当前后端运行版本（内部接口）。

    中文注释:
    - 用于 UAT smoke 校验 HF 运行中的容器是否已经切到本次 deploy SHA。
    - 只暴露 git SHA，不返回任何 secret。
    """
    deploy_sha = (os.environ.get("DEPLOY_SHA") or "").strip() or None
    return PlatformRuntimeVersionResponse(deploy_sha=deploy_sha)


@router.post("/webhooks/resend")
async def receive_resend_webhook(request: Request):
    """
    Resend Webhook 接收入口（签名校验）。

    中文注释:
    - 该接口不走 ADMIN_API_KEY（Resend 外部回调无法携带内部 key）；
    - 必须通过 svix header + RESEND_WEBHOOK_SECRET 校验签名；
    - 当前阶段先做“验签 + 事件日志”，后续可扩展为投递状态回写。
    """
    webhook_secret = (os.environ.get("RESEND_WEBHOOK_SECRET") or "").strip()
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="RESEND_WEBHOOK_SECRET is not configured")

    payload_bytes = await request.body()
    payload_text = payload_bytes.decode("utf-8")
    headers = {
        "id": request.headers.get("svix-id"),
        "timestamp": request.headers.get("svix-timestamp"),
        "signature": request.headers.get("svix-signature"),
    }
    if not headers["id"] or not headers["timestamp"] or not headers["signature"]:
        raise HTTPException(status_code=400, detail="Missing required webhook signature headers")

    try:
        resend.Webhooks.verify(
            {
                "payload": payload_text,
                "headers": headers,
                "webhook_secret": webhook_secret,
            }
        )
    except Exception as e:
        logger.warning("[ResendWebhook] invalid signature: %s", e)
        raise HTTPException(status_code=400, detail="Invalid webhook signature") from e

    try:
        event = json.loads(payload_text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid webhook payload JSON") from e

    event_type = str(event.get("type") or "").strip().lower()
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    provider_id = str((data or {}).get("email_id") or (data or {}).get("id") or "").strip()

    logger.info("[ResendWebhook] type=%s provider_id=%s", event_type or "unknown", provider_id or "-")
    return {"success": True}


@router.post("/release-validation/runs", status_code=201)
async def create_release_validation_run(
    payload: CreateRunRequest,
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    run = service.create_run(payload)
    return {"run": run}


@router.get("/release-validation/runs")
async def list_release_validation_runs(
    environment: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    runs = service.list_runs(environment=environment, limit=limit)
    return {"data": runs}


@router.post("/release-validation/runs/{run_id}/readiness")
async def execute_release_readiness(
    run_id: UUID,
    payload: ReadinessRequest,
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    return service.execute_readiness(run_id, payload)


@router.post("/release-validation/runs/{run_id}/regression")
async def execute_release_regression(
    run_id: UUID,
    payload: RegressionRequest,
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    return service.execute_regression(run_id, payload)


@router.post("/release-validation/runs/{run_id}/finalize")
async def finalize_release_validation(
    run_id: UUID,
    payload: FinalizeRequest | None = None,
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    return service.finalize(run_id, payload or FinalizeRequest())


@router.get("/release-validation/runs/{run_id}/report")
async def get_release_validation_report(
    run_id: UUID,
    _admin: None = Depends(require_admin_key),
):
    service = ReleaseValidationService()
    return service.get_report(run_id)
