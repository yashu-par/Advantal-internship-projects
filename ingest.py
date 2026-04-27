import shutil
import os
import pdfplumber
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

PDF_DIR = "./pdfs"
CHROMA_DIR = "./chroma_db"

os.makedirs(PDF_DIR, exist_ok=True)

pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]

if not pdf_files:
    print("ERROR: pdfs/ folder mein koi PDF nahi!")
    exit()

print(f"Found {len(pdf_files)} PDF(s): {pdf_files}")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

splitter = CharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separator=""
)

def extract_tables_from_pdf(pdf_path, pdf_name):
    """
    pdfplumber se PDF ki tables extract karo.
    Har table ko ek Document banao taaki ChromaDB mein save ho sake.
    """
    table_docs = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables):
                    if not table:
                        continue
                    # Table ko readable text mein convert karo
                    table_text = f"[TABLE from {pdf_name}, Page {page_num + 1}]\n"
                    for row in table:
                        # None values ko empty string se replace karo
                        clean_row = [str(cell) if cell else "" for cell in row]
                        table_text += " | ".join(clean_row) + "\n"

                    doc = Document(
                        page_content=table_text,
                        metadata={
                            "source_pdf": pdf_name,
                            "page": page_num,
                            "type": "table",
                            "table_index": table_idx
                        }
                    )
                    table_docs.append(doc)
                    print(f"  Table {table_idx+1} extracted from page {page_num+1}")
    except Exception as e:
        print(f"  Table extraction error: {e}")
    return table_docs

# Har PDF ke liye alag collection banao
for pdf_file in pdf_files:
    pdf_path = os.path.join(PDF_DIR, pdf_file)

    # Collection naam — PDF ke naam se banao
    # Special characters hata do
    collection_name = "pdf_" + pdf_file.replace(".pdf", "").replace(" ", "_").replace("-", "_").lower()
    # ChromaDB collection naam max 63 chars
    collection_name = collection_name[:63]

    print(f"\nProcessing: {pdf_file}")
    print(f"Collection: {collection_name}")

    # Step 1: Text extract karo
    loader = PyMuPDFLoader(pdf_path)
    text_docs = loader.load()
    for doc in text_docs:
        doc.metadata["source_pdf"] = pdf_file
        doc.metadata["type"] = "text"
    print(f"  Text pages loaded: {len(text_docs)}")

    # Step 2: Tables extract karo
    table_docs = extract_tables_from_pdf(pdf_path, pdf_file)
    print(f"  Tables extracted: {len(table_docs)}")

    # Step 3: Text chunks banao
    text_chunks = splitter.split_documents(text_docs)
    print(f"  Text chunks: {len(text_chunks)}")

    # Step 4: Saare chunks jodo — text + tables
    all_chunks = text_chunks + table_docs
    print(f"  Total chunks: {len(all_chunks)}")

    # Step 5: Is PDF ki alag ChromaDB collection mein save karo
    vectorstore = Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=collection_name
    )
    print(f"  Saved to collection: {collection_name}")

# Collection names ek file mein save karo
# Taaki app.py ko pata rahe kaunsi collections hain
collections = []
for pdf_file in pdf_files:
    cname = "pdf_" + pdf_file.replace(".pdf", "").replace(" ", "_").replace("-", "_").lower()
    cname = cname[:63]
    collections.append({"pdf": pdf_file, "collection": cname})

import json
with open("./chroma_db/collections.json", "w") as f:
    json.dump(collections, f, indent=2)

print(f"\nDone! {len(pdf_files)} PDFs processed.")
print(f"Collections saved to chroma_db/collections.json")