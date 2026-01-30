from weasyprint import HTML
from datetime import datetime
from uuid import UUID

def generate_invoice_pdf(invoice_id: UUID, manuscript_title: str, amount: float, output_path: str):
    """
    使用 WeasyPrint 生成财务账单 PDF
    
    中文注释:
    1. 遵循章程: 核心逻辑显性化，包含财务法律要素。
    2. 使用 HTML/CSS 模板进行排版，确保样式符合专业标准。
    3. 账单号基于 invoice_id 确保唯一性。
    """
    html_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: sans-serif; color: #334155; padding: 40px; }}
                .header {{ border-bottom: 2px solid #0f172a; padding-bottom: 20px; margin-bottom: 40px; }}
                .title {{ font-size: 24px; font-weight: bold; color: #0f172a; }}
                .details {{ margin-bottom: 40px; }}
                .footer {{ font-size: 10px; color: #94a3b8; margin-top: 100px; border-top: 1px solid #e2e8f0; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">ScholarFlow Invoice</div>
                <p>Invoice ID: {invoice_id}</p>
                <p>Date: {datetime.now().strftime('%Y-%m-%d')}</p>
            </div>
            
            <div class="details">
                <h3>Manuscript Details</h3>
                <p><strong>Title:</strong> {manuscript_title}</p>
                <hr/>
                <h3>Payment Summary</h3>
                <p><strong>Amount Due:</strong> ${amount:,.2f}</p>
            </div>
            
            <div class="footer">
                <p>Standard Legal Disclaimer: This is a system-generated document. Payment is non-refundable upon manuscript publication.</p>
            </div>
        </body>
    </html>
    """
    
    try:
        HTML(string=html_content).write_pdf(output_path)
        print(f"账单已生成: {output_path}")
        return True
    except Exception as e:
        print(f"PDF 账单生成失败: {str(e)}")
        return False
