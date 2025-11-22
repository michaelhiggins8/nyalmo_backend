from dotenv import load_dotenv
import os
import io
import uuid
from typing import List
from db import pool
from openai import OpenAI
from fastapi.security import HTTPBearer
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from Auth import supabase

# Import document processing libraries
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import chardet
except ImportError:
    chardet = None

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

security = HTTPBearer(auto_error=False)
router = APIRouter()


def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Extract text from various file types (PDF, DOCX, TXT, etc.)"""
    file_extension = filename.lower().split('.')[-1]
    
    try:
        if file_extension == 'pdf':
            if PyPDF2 is None:
                raise HTTPException(status_code=400, detail="PDF support not available. Please install PyPDF2.")
            # Extract text from PDF
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        
        elif file_extension in ['docx', 'doc']:
            if Document is None:
                raise HTTPException(status_code=400, detail="DOCX support not available. Please install python-docx.")
            # Extract text from DOCX
            doc_file = io.BytesIO(file_content)
            doc = Document(doc_file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        
        elif file_extension in ['txt', 'text', 'md', 'csv']:
            # Extract text from plain text files
            # Detect encoding
            if chardet:
                detected = chardet.detect(file_content)
                encoding = detected['encoding'] or 'utf-8'
            else:
                encoding = 'utf-8'
            return file_content.decode(encoding).strip()
        
        else:
            # Try to decode as text for other file types
            if chardet:
                detected = chardet.detect(file_content)
                encoding = detected['encoding'] or 'utf-8'
            else:
                encoding = 'utf-8'
            return file_content.decode(encoding).strip()
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error extracting text from file: {str(e)}")




import re
from typing import List

def chunk_text(text: str) -> List[str]:
    """
    General-purpose, RAG-friendly text chunker with a HARD guarantee:
    every character of the input `text` will appear in at least one
    returned chunk.

    Strategy:
    - We still try to respect large breaks (blank lines) and sentences.
    - BUT we finish with a character-level sweep over the ORIGINAL text,
      cutting it into windows with overlap. That sweep is the source of truth.
    - That way, even if earlier steps drop/truncate/reorder (they shouldn't,
      but PDFs/ocr can be messy), the final output is guaranteed complete.
    """

    # tunables
    max_chunk_size = 1000    # target chunk size
    overlap = 200            # how much previous context to keep

    if not text:
        return []

    # normalize newlines but DO NOT strip globally (we want to keep leading/trailing)
    norm_text = text.replace("\r\n", "\n").replace("\r", "\n")

    # ------------------------------------------------------------------
    # OPTIONAL: semantic-ish passes (not strictly needed for the guarantee)
    # We can keep them for future improvement, but the guarantee will come
    # from the final pass below.
    # ------------------------------------------------------------------

    # 1) split on big gaps — this is just to help us if we ever want to
    # generate "nice" chunks first
    _sections = [sec for sec in re.split(r"\n{2,}", norm_text) if sec]

    # 2) we could sentence-split here, but since the user wants a *guarantee*,
    # we'll rely on the final windowing step.

    # ------------------------------------------------------------------
    # HARD GUARANTEE STEP (source of truth)
    # We now walk the ORIGINAL normalized text in windows.
    # This alone guarantees that 100% of the original text is covered.
    # ------------------------------------------------------------------
    chunks: List[str] = []
    n = len(norm_text)

    # safety: if overlap is too big, clamp it
    if overlap >= max_chunk_size:
        overlap = max_chunk_size // 4  # pick something reasonable

    start = 0
    while start < n:
        end = start + max_chunk_size
        chunk = norm_text[start:end]
        chunks.append(chunk)
        if end >= n:
            break
        # move start forward but keep overlap
        start = end - overlap

    return chunks

@router.post("/upload_docs")
async def upload_docs(file: UploadFile = File(...), credentials=Depends(security)):
    """
    Upload document, extract text, chunk it, create embeddings, and store in database and storage.
    """
    
    # Check if token is valid
    token = credentials.credentials if (credentials and credentials.credentials != "undefined") else None

    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    try:
        claims = supabase.auth.get_claims(token)
        user_id = uuid.UUID(claims["claims"]["sub"])  # Get user ID from token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get org_id from database
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT org_id FROM org_userships WHERE user_id = %s LIMIT 1",
                    (user_id,)
                )
                result = cur.fetchone()
                
                if not result:
                    raise HTTPException(status_code=404, detail="Organization not found for this user")
                
                org_id = result[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching organization: {str(e)}")

    # Read file content
    try:
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    # Extract text from file
    text = extract_text_from_file(file_content, file.filename)
    
    if not text:
        raise HTTPException(status_code=400, detail="No text could be extracted from the file")
    
    # Chunk the text
    chunks = chunk_text(text)
    
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks created from text")

    # Create embeddings for all chunks
    try:
        response = client.embeddings.create(
            input=chunks,
            model="text-embedding-3-small"
        )
        embeddings = [item.embedding for item in response.data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating embeddings: {str(e)}")

    # Generate unique file path for storage
    file_uuid = str(uuid.uuid4())
    file_path = f"/{org_id}/{file_uuid}_{file.filename}"
    bucket_name = "documents"

    # Insert all chunks into database efficiently using batch insert
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                #make 'document' table entry
                cur.execute("INSERT INTO documents (org_id, file_path) VALUES  (%s, %s)", (org_id, file_path))

                # Prepare batch insert
                insert_query = """
                    INSERT INTO chunks (content, embedding, org_id, file_path)
                    VALUES (%s, %s, %s, %s)
                """
                
                # Create list of tuples for batch insert
                batch_data = [
                    (chunk, embedding, org_id, file_path)
                    for chunk, embedding in zip(chunks, embeddings)
                ]
                
                # Execute batch insert
                cur.executemany(insert_query, batch_data)
                conn.commit()
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inserting into database: {str(e)}")

    # Upload file to Supabase storage
    try:
        storage_result = supabase.storage.from_(bucket_name).upload(
            file_path,
            file_content,
            {
                "content-type": file.content_type or "application/octet-stream",
                "x-upsert": "true"  # Overwrite if exists
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file to storage: {str(e)}")

    return {
        "message": "Document uploaded and processed successfully",
        "filename": file.filename,
        "org_id": org_id,
        "chunks_created": len(chunks),
        "file_path": file_path
    }
