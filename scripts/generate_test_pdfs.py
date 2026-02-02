from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import random
import os

def create_real_pdf(filename, num_pages):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    topics = ["Machine Learning", "Quantum Physics", "Sustainable Agriculture", "Blockchain Ethics"]
    title = f"Research on {random.choice(topics)} - Study {random.randint(100, 999)}"
    
    for p in range(num_pages):
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, title)
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 120, f"Author: ScholarFlow Test Suite")
        c.drawString(100, height - 140, f"Page {p + 1} of {num_pages}")
        
        # Add some random "academic" text
        text_object = c.beginText(100, height - 180)
        text_object.setFont("Helvetica", 10)
        for _ in range(40):
            line = " ".join(["lorem ipsum"] * 10) + f" [Data Segment {random.random()}]"
            text_object.textLine(line)
        c.drawText(text_object)

        # Force size increase: Draw many tiny invisible lines or circles
        # (This is more "legal" for a PDF than raw urandom)
        c.setStrokeColorRGB(1, 1, 1, alpha=0.01) # Near invisible
        for _ in range(500):
            c.circle(random.random()*width, random.random()*height, 1)
        
        c.showPage()
    
    c.save()

def main():
    # Number of pages to vary size
    page_counts = [10, 50, 100, 200, 500, 20, 80, 150, 300, 40]
    for i, pages in enumerate(page_counts):
        fname = f"test_paper_{i+1:02d}.pdf"
        create_real_pdf(fname, pages)
        size = os.path.getsize(fname) / 1024
        print(f"Generated {fname} with {pages} pages ({size:.1f}KB)")

if __name__ == "__main__":
    main()