import PyPDF2
import sys

def extract_text_from_pdf(pdf_path):
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        with open("extracted_brochure.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print("Successfully extracted text to extracted_brochure.txt")
    except Exception as e:
        print(f"Error extracting text: {e}")

if __name__ == "__main__":
    extract_text_from_pdf("TMU Prog. Booklet Final 20 Pages.pdf")
