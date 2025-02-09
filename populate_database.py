from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import hashlib
import asyncio
from scraper.jobs_scraper import scrape_job_documents
from scraper.job_briefs_scraper import scrape_job_briefs
from dotenv import load_dotenv
import os
import openai
from db.mongodb_client import db
from models.job_brief_model import JobBriefModel

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to split text into chunks
def split_documents(documents, chunk_size=1000, chunk_overlap=100):
    """Split documents into smaller chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return text_splitter.split_documents(documents)

# Function to generate a unique ID for a document based on metadata only
def generate_chunk_id(chunk):
    """Generate a unique ID based on document metadata."""
    hash_input = str(chunk.metadata) 
    return hashlib.sha256(hash_input.encode()).hexdigest()

def calculate_chunk_ids(chunks):
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        current_page_id = generate_chunk_id(chunk)

        # If the page ID is the same as the last one, increment the index.
        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        # Calculate the chunk ID.
        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        # Add it to the page meta-data.
        chunk.metadata["id"] = chunk_id

    return chunks


# Function to store documents in a vector store
def add_to_chroma(chunks, vectorstore_path="./chroma"):
    """Store documents into Chroma vectorstore, updating existing documents as needed."""
    
    # Initialize Chroma
    db = Chroma(
        persist_directory=vectorstore_path,
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-small")
    )

    # Calculate chunk IDs
    chunks = calculate_chunk_ids(chunks)
    results = db.get()
    existing_ids = set(results["ids"])

    # Separate new and existing documents
    new_documents = []
    new_ids = []
    updated_documents = []
    for chunk in chunks:
        chunk_id = chunk.metadata["id"]
        if chunk_id in existing_ids:
            existing_chunk = db.get(ids=[chunk_id])
            page_content = existing_chunk['documents'][0]
        
            # Check if content differs
            if page_content != chunk.page_content:
                updated_documents.append((chunk_id, chunk))
        else:
            new_documents.append(chunk)
            new_ids.append(chunk_id)

    # Add new documents to vectorstore
    if new_documents:
        db.add_documents(documents=new_documents, ids=new_ids)

    # Update existing documents in the vectorstore
    if updated_documents:
        for doc_id, doc in updated_documents:
            db.update_document(document_id=doc_id, document=doc)

    if not new_documents and not updated_documents:
        print("No new or updated documents to process.")
    else:
        print(f"Added {len(new_documents)} new documents and updated {len(updated_documents)} documents.")

    return len(new_documents)

if __name__ == "__main__":
    print("🔎 Starting job scraping process...")

    jobs_collection = db["job_briefs"]
    job_briefs = [JobBriefModel(**job) for job in list(jobs_collection.find())]

    # Run the async function
    documents = asyncio.run(scrape_job_documents(job_briefs))
    print("✅ Job scraping process completed.")
    
    chunks = split_documents(documents)
    add_to_chroma(chunks)
    