import httpx
import os
from typing import Dict, Any, Optional
from lxml import etree
from app.core.config import CrossrefConfig


class CrossrefClient:
    """
    Crossref API Client

    Supports:
    1. Similarity Check (iThenticate) - Legacy/Mock
    2. DOI Registration (Deposit API) - Feature 015
    """

    def __init__(self, config: Optional[CrossrefConfig] = None):
        # Similarity Check config (Legacy)
        self.sim_api_key = os.environ.get("CROSSREF_API_KEY")
        self.sim_base_url = "https://api.ithenticate.com/v1"

        # DOI Deposit config (Feature 015)
        self.deposit_config = config

        self.ns = {
            "default": "http://www.crossref.org/schema/5.4.0",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "ai": "http://www.crossref.org/AccessIndicators.xsd",
            "jats": "http://www.ncbi.nlm.nih.gov/JATS1",
        }
        self.schema_location = "http://www.crossref.org/schema/5.4.0 http://www.crossref.org/schemas/crossref5.4.0.xsd"

    # === Similarity Check Methods (Mock) ===
    async def submit_manuscript(self, file_path: str) -> Optional[str]:
        """
        提交稿件全文至外部查重平台
        返回外部任务 ID (external_id)
        """
        return "ext_task_12345"

    async def get_check_status(self, external_id: str) -> Dict[str, Any]:
        """
        轮询外部查重任务状态与得分
        """
        return {
            "status": "completed",
            "similarity_score": 0.15,
            "report_url": "https://external-reports.com/pdf/123",
        }

    # === DOI Deposit Methods (Feature 015) ===
    def generate_xml(self, article_data: Dict[str, Any], batch_id: str) -> bytes:
        """
        Generate Crossref Deposit XML for an article
        """
        # Create root element
        root = etree.Element(f"{{{self.ns['default']}}}doi_batch", nsmap=self.ns)

        # 1. Head
        head = etree.SubElement(root, "head")
        etree.SubElement(head, "doi_batch_id").text = batch_id
        etree.SubElement(head, "timestamp").text = str(
            int(os.times()[4] * 100)
        )  # Simple timestamp

        depositor = etree.SubElement(head, "depositor")
        etree.SubElement(depositor, "depositor_name").text = "ScholarFlow System"
        etree.SubElement(depositor, "email_address").text = (
            self.deposit_config.depositor_email if self.deposit_config else ""
        )

        etree.SubElement(head, "registrant").text = "ScholarFlow"

        # 2. Body
        body = etree.SubElement(root, "body")
        journal = etree.SubElement(body, "journal")

        # Journal Metadata
        j_meta = etree.SubElement(journal, "journal_metadata")
        etree.SubElement(j_meta, "full_title").text = (
            self.deposit_config.journal_title if self.deposit_config else ""
        )
        if self.deposit_config and self.deposit_config.journal_issn:
            issn = etree.SubElement(j_meta, "issn")
            issn.text = self.deposit_config.journal_issn

        # Journal Article
        j_article = etree.SubElement(
            journal, "journal_article", publication_type="full_text"
        )

        # Titles
        titles = etree.SubElement(j_article, "titles")
        etree.SubElement(titles, "title").text = article_data.get("title", "")

        # Contributors
        if article_data.get("authors"):
            contributors = etree.SubElement(j_article, "contributors")
            for idx, author in enumerate(article_data["authors"]):
                # Determine sequence
                sequence = "first" if idx == 0 else "additional"
                person_name = etree.SubElement(
                    contributors,
                    "person_name",
                    contributor_role="author",
                    sequence=sequence,
                )
                # Intelligent name splitting fallback
                given_name = author.get("first_name", "")
                surname = author.get("last_name", "")
                
                if not given_name and not surname and author.get("full_name"):
                    parts = author["full_name"].strip().split(" ", 1)
                    given_name = parts[0]
                    surname = parts[1] if len(parts) > 1 else ""

                etree.SubElement(person_name, "given_name").text = given_name
                etree.SubElement(person_name, "surname").text = surname
                if author.get("affiliation"):
                    affiliations = etree.SubElement(person_name, "affiliations")
                    etree.SubElement(affiliations, "institution").text = author[
                        "affiliation"
                    ]

        # Publication Date
        pub_date_str = article_data.get("publication_date")
        if pub_date_str:
            # Assume YYYY-MM-DD
            try:
                date_parts = pub_date_str.split("-")
                pub_date = etree.SubElement(
                    j_article, "publication_date", media_type="online"
                )
                if len(date_parts) >= 1:
                    etree.SubElement(pub_date, "year").text = date_parts[0]
                if len(date_parts) >= 2:
                    etree.SubElement(pub_date, "month").text = date_parts[1]
                if len(date_parts) >= 3:
                    etree.SubElement(pub_date, "day").text = date_parts[2]
            except Exception:
                pass  # Log error or handle gracefully

        # DOI Data
        doi_data = etree.SubElement(j_article, "doi_data")
        etree.SubElement(doi_data, "doi").text = article_data.get("doi", "")
        etree.SubElement(doi_data, "resource").text = article_data.get("url", "")

        return etree.tostring(
            root, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )

    async def submit_deposit(
        self, xml_content: bytes, file_name: str = "crossref_submission.xml"
    ) -> str:
        """
        Submit XML to Crossref API
        """
        if not self.deposit_config:
            raise ValueError("Crossref deposit configuration missing")

        url = self.deposit_config.api_url
        params = {
            "operation": "doMDUpload",
            "login_id": self.deposit_config.depositor_email,
            "login_passwd": self.deposit_config.depositor_password,
        }

        files = {"fname": (file_name, xml_content, "application/xml")}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=params, files=files, timeout=60.0)
            response.raise_for_status()
            return response.text
