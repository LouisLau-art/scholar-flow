from typing import Dict, Any
from lxml import etree


class DublinCoreMapper:
    """
    Map internal Article models to Dublin Core (oai_dc) XML
    """

    def __init__(self):
        self.ns = {
            "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
            "dc": "http://purl.org/dc/elements/1.1/",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }
        # Correct schema location string format: "namespace URI" "schema URI"
        self.schema_location = "http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd"

    def to_xml(self, article: Dict[str, Any]) -> etree.Element:
        """
        Convert article dictionary to oai_dc XML element
        """
        root = etree.Element(f"{{{self.ns['oai_dc']}}}dc", nsmap=self.ns)
        root.set(f"{{{self.ns['xsi']}}}schemaLocation", self.schema_location)

        # Title
        if article.get("title"):
            title = etree.SubElement(root, f"{{{self.ns['dc']}}}title")
            title.text = article["title"]

        # Creators (Authors)
        if article.get("authors"):
            for author in article["authors"]:
                creator = etree.SubElement(root, f"{{{self.ns['dc']}}}creator")
                # Format: "Last, First" or "Name"
                first = author.get("first_name", "")
                last = author.get("last_name", "")
                full = author.get("full_name", "")
                
                if first and last:
                    creator.text = f"{last}, {first}"
                elif full:
                    # Try to split full name to "Last, First" if possible
                    parts = full.strip().split(" ", 1)
                    if len(parts) > 1:
                        creator.text = f"{parts[1]}, {parts[0]}"
                    else:
                        creator.text = full
                else:
                    creator.text = "Unknown"

        # Subject (Keywords)
        # Assuming keywords are in article data (not explicitly in my data model but common)
        if article.get("keywords"):
            for keyword in article["keywords"]:
                subject = etree.SubElement(root, f"{{{self.ns['dc']}}}subject")
                subject.text = keyword

        # Description (Abstract)
        if article.get("abstract"):
            desc = etree.SubElement(root, f"{{{self.ns['dc']}}}description")
            desc.text = article["abstract"]

        # Publisher
        if article.get("journal_title"):
            pub = etree.SubElement(root, f"{{{self.ns['dc']}}}publisher")
            pub.text = article["journal_title"]

        # Date
        if article.get("published_at"):
            date_elem = etree.SubElement(root, f"{{{self.ns['dc']}}}date")
            # ISO format YYYY-MM-DD
            # Assuming published_at is ISO string or datetime
            date_str = str(article["published_at"])
            if "T" in date_str:
                date_str = date_str.split("T")[0]
            date_elem.text = date_str

        # Type
        type_elem = etree.SubElement(root, f"{{{self.ns['dc']}}}type")
        type_elem.text = "Article"

        # Identifier (DOI or URL)
        if article.get("doi"):
            ident = etree.SubElement(root, f"{{{self.ns['dc']}}}identifier")
            ident.text = f"https://doi.org/{article['doi']}"

        # Language
        lang = etree.SubElement(root, f"{{{self.ns['dc']}}}language")
        lang.text = "en"  # Default to English, or fetch from article

        return root
