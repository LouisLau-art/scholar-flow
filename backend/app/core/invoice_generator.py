from __future__ import annotations

from datetime import datetime
from io import BytesIO
from uuid import UUID

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def build_invoice_pdf_bytes(invoice_id: UUID, manuscript_title: str, amount: float) -> bytes:
    """
    使用 ReportLab 生成财务账单 PDF（CPU 本地生成，避免 WeasyPrint 重依赖）
    
    中文注释:
    1. 遵循章程: 核心逻辑显性化，包含财务法律要素。
    2. 账单号基于 invoice_id 确保唯一性。
    3. 输出为 bytes，便于 FastAPI 直接返回下载响应。
    """
    try:
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=LETTER)

        width, height = LETTER
        left = 0.9 * inch
        y = height - 0.9 * inch

        c.setFont("Helvetica-Bold", 18)
        c.drawString(left, y, "ScholarFlow Invoice")
        y -= 0.35 * inch

        c.setFont("Helvetica", 10)
        c.drawString(left, y, f"Invoice ID: {invoice_id}")
        y -= 0.18 * inch
        c.drawString(left, y, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        y -= 0.35 * inch

        c.setLineWidth(1)
        c.line(left, y, width - left, y)
        y -= 0.35 * inch

        c.setFont("Helvetica-Bold", 12)
        c.drawString(left, y, "Manuscript Details")
        y -= 0.22 * inch

        c.setFont("Helvetica", 10)
        title = (manuscript_title or "").strip() or "Manuscript"
        c.drawString(left, y, f"Title: {title}")
        y -= 0.35 * inch

        c.setFont("Helvetica-Bold", 12)
        c.drawString(left, y, "Payment Summary")
        y -= 0.22 * inch

        c.setFont("Helvetica", 10)
        c.drawString(left, y, f"Amount Due: ${amount:,.2f}")
        y -= 0.6 * inch

        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.45, 0.45, 0.45)
        c.drawString(
            left,
            0.9 * inch,
            "Legal: This is a system-generated document. Payment is non-refundable upon manuscript publication.",
        )

        c.showPage()
        c.save()
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"PDF 账单生成失败: {str(e)}")
        return b""


def generate_invoice_pdf(
    invoice_id: UUID, manuscript_title: str, amount: float, output_path: str
) -> bool:
    """
    兼容旧调用：生成并写入本地文件（用于调试/本地备份）。
    """
    pdf_bytes = build_invoice_pdf_bytes(invoice_id, manuscript_title, amount)
    if not pdf_bytes:
        return False
    try:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"账单已生成: {output_path}")
        return True
    except Exception as e:
        print(f"写入账单失败: {str(e)}")
        return False
