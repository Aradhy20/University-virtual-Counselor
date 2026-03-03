import sys
import os
from langchain_community.document_loaders import Docx2txtLoader

def read_docx(path):
    try:
        loader = Docx2txtLoader(path)
        docs = loader.load()
        print(f"\n--- Content of {os.path.basename(path)} ---")
        for doc in docs:
            print(doc.page_content[:2000]) # First 2000 chars
    except Exception as e:
        print(f"Error reading {path}: {e}")

if __name__ == "__main__":
    files = [
        r"d:\tmu\university details\TMU_Scholarship_FAQs.docx",
        r"d:\tmu\university details\TMU_Hostel_FAQ_RAG.docx",
        r"d:\tmu\university details\BTech (AICTE Approved) in Computer Science & Engineering.docx"
    ]
    for f in files:
        if os.path.exists(f):
            read_docx(f)
        else:
            print(f"File not found: {f}")
