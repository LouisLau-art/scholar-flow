from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import InvoiceConfig
from app.lib.api_client import supabase_admin
from app.services.storage_service import create_signed_url, upload_bytes

try:
    from weasyprint import HTML  # type: ignore
except Exception as e:  # pragma: no cover
    HTML = None  # type: ignore[assignment]
    _WEASYPRINT_IMPORT_ERROR = str(e)
else:
    _WEASYPRINT_IMPORT_ERROR = ""


@dataclass(frozen=True)
class InvoicePdfResult:
    invoice_id: UUID
    invoice_number: str | None
    pdf_path: str | None
    pdf_generated_at: str | None
    pdf_error: str | None


def _templates_dir() -> Path:
    # backend/app/services -> backend/app -> backend/app/core/templates
    return Path(__file__).resolve().parents[1] / "core" / "templates"


_jinja = Environment(
    loader=FileSystemLoader(str(_templates_dir())),
    autoescape=select_autoescape(["html", "xml"]),
)


def _format_amount(amount: float) -> str:
    return f"USD {amount:,.2f}"


def _invoice_number(*, invoice_id: UUID, when: datetime) -> str:
    year = when.strftime("%Y")
    short = str(invoice_id).split("-")[0].upper()
    return f"INV-{year}-{short}"


def _render_invoice_html(
    *,
    invoice_number: str,
    issue_date: str,
    author_name: str,
    manuscript_id: str,
    manuscript_title: str,
    amount_display: str,
    bank_details: str,
) -> str:
    return _jinja.get_template("invoice_pdf.html").render(
        invoice_number=invoice_number,
        issue_date=issue_date,
        author_name=author_name,
        manuscript_id=manuscript_id,
        manuscript_title=manuscript_title,
        amount_display=amount_display,
        bank_details=bank_details,
    )


def _html_to_pdf_bytes(html: str) -> bytes:
    if HTML is None:  # pragma: no cover
        raise RuntimeError(f"WeasyPrint is not available: {_WEASYPRINT_IMPORT_ERROR}")
    return HTML(string=html).write_pdf()


def _load_invoice_row(invoice_id: UUID) -> dict:
    resp = (
        supabase_admin.table("invoices")
        .select("id,manuscript_id,amount,status,confirmed_at,invoice_number,pdf_path")
        .eq("id", str(invoice_id))
        .single()
        .execute()
    )
    return getattr(resp, "data", None) or {}


def _load_manuscript_row(manuscript_id: str) -> dict:
    resp = (
        supabase_admin.table("manuscripts")
        .select("id,title,author_id")
        .eq("id", manuscript_id)
        .single()
        .execute()
    )
    return getattr(resp, "data", None) or {}


def _load_author_profile(author_id: str) -> dict:
    resp = (
        supabase_admin.table("user_profiles")
        .select("full_name,email")
        .eq("id", author_id)
        .single()
        .execute()
    )
    return getattr(resp, "data", None) or {}


def generate_and_store_invoice_pdf(*, invoice_id: UUID) -> InvoicePdfResult:
    """
    生成并上传 Invoice PDF，然后回填 invoices 表（不改变 payment status）。
    """
    now = datetime.now(timezone.utc)
    issue_date = now.strftime("%Y-%m-%d")
    cfg = InvoiceConfig.from_env()

    inv = _load_invoice_row(invoice_id)
    if not inv:
        raise RuntimeError("Invoice not found")

    manuscript_id = str(inv.get("manuscript_id") or "").strip()
    if not manuscript_id:
        raise RuntimeError("Invoice missing manuscript_id")

    ms = _load_manuscript_row(manuscript_id)
    title = (ms.get("title") or "Manuscript").strip() if ms else "Manuscript"
    author_id = str((ms or {}).get("author_id") or "").strip()

    author_name = "Author"
    if author_id:
        prof = _load_author_profile(author_id)
        author_name = (
            (prof.get("full_name") or "").strip()
            or (prof.get("email") or "").strip()
            or "Author"
        )

    try:
        amount = float(inv.get("amount") or 0)
    except Exception:
        amount = 0.0

    inv_no = (inv.get("invoice_number") or "").strip() or _invoice_number(
        invoice_id=invoice_id, when=now
    )
    pdf_path = f"{manuscript_id}/{invoice_id}.pdf"

    try:
        html = _render_invoice_html(
            invoice_number=inv_no,
            issue_date=issue_date,
            author_name=author_name,
            manuscript_id=manuscript_id,
            manuscript_title=title,
            amount_display=_format_amount(amount),
            bank_details=cfg.payment_instructions,
        )
        pdf_bytes = _html_to_pdf_bytes(html)
        print(
            f"[InvoicePDF] generating: invoice_id={invoice_id} manuscript_id={manuscript_id} bytes={len(pdf_bytes)}"
        )
        upload_bytes(
            bucket="invoices",
            path=pdf_path,
            content=pdf_bytes,
            content_type="application/pdf",
            upsert=True,
        )
        supabase_admin.table("invoices").update(
            {
                "invoice_number": inv_no,
                "pdf_path": pdf_path,
                "pdf_generated_at": now.isoformat(),
                "pdf_error": None,
            }
        ).eq("id", str(invoice_id)).execute()
        print(f"[InvoicePDF] stored: invoice_id={invoice_id} pdf_path={pdf_path}")
        return InvoicePdfResult(
            invoice_id=invoice_id,
            invoice_number=inv_no,
            pdf_path=pdf_path,
            pdf_generated_at=now.isoformat(),
            pdf_error=None,
        )
    except Exception as e:
        err = str(e)
        print(f"[InvoicePDF] failed: invoice_id={invoice_id} error={err}")
        supabase_admin.table("invoices").update(
            {"pdf_error": err, "pdf_generated_at": now.isoformat()}
        ).eq("id", str(invoice_id)).execute()
        return InvoicePdfResult(
            invoice_id=invoice_id,
            invoice_number=inv_no,
            pdf_path=None,
            pdf_generated_at=now.isoformat(),
            pdf_error=err,
        )


def get_invoice_pdf_signed_url(*, invoice_id: UUID) -> tuple[str, int]:
    inv = _load_invoice_row(invoice_id)
    if not inv:
        raise RuntimeError("Invoice not found")
    pdf_path = (inv.get("pdf_path") or "").strip()
    if not pdf_path:
        raise RuntimeError("Invoice PDF not generated")

    cfg = InvoiceConfig.from_env()
    signed = create_signed_url(bucket="invoices", path=pdf_path, expires_in=cfg.signed_url_expires_in)
    return signed.url, signed.expires_in
