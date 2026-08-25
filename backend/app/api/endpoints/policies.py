import hashlib
import httpx
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database.session import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.policy import PolicyDocument, PolicyChunk
from app.schemas.policy import PolicyChunkOut
from app.ai.chunking import split_text_into_sliding_chunks
from app.ai.embeddings import generate_embedding
from app.ai.vector_store import save_policy_chunk
from app.ai.rag_service import hybrid_retrieve_policy_chunks
from app.core.logging import logger

router = APIRouter()


class PolicyIngestPayload(BaseModel):
    url: HttpUrl
    title: str


@router.post("/upload", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def upload_compliance_policy(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a compliance manual (supports PDF/txt), extracts text, chunks it,
    and indexes embeddings into pgvector.
    """
    file_bytes = file.file.read()
    
    # Generate SHA256 checksum to prevent duplicate imports
    checksum = hashlib.sha256(file_bytes).hexdigest()
    existing = db.query(PolicyDocument).filter(PolicyDocument.checksum == checksum).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Compliance policy file already registered (ID: {existing.id})."
        )

    # 1. Parse text from file
    filename = file.filename or "policy.txt"
    text = ""
    
    if filename.endswith(".pdf"):
        try:
            import fitz # PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text()
        except Exception as e:
            logger.error("pdf_extraction_failed", filename=filename, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract text from PDF file. Verify formatting."
            )
    else:
        # Default fallback to plain text decode
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="File formatting not supported. Upload a valid utf-8 or PDF document."
                )

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded document contains no readable text."
        )

    # 2. Save Document Model
    doc_record = PolicyDocument(
        title=title,
        filename=filename,
        checksum=checksum
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    # 3. Chunk and Embed Text
    chunks = split_text_into_sliding_chunks(text, chunk_size=150, overlap=30)
    for index, chunk_data in enumerate(chunks):
        content = chunk_data["content"]
        embedding = generate_embedding(content)
        save_policy_chunk(
            db=db,
            document_id=doc_record.id,
            chunk_index=index,
            content=content,
            embedding=embedding
        )
        
    db.commit()
    logger.info("policy_imported_successfully", title=title, filename=filename, chunks_count=len(chunks))

    return {
        "document_id": doc_record.id,
        "title": doc_record.title,
        "filename": doc_record.filename,
        "chunks_indexed": len(chunks)
    }


@router.get("/search", response_model=List[PolicyChunkOut])
def search_compliance_policies(
    query: str,
    limit: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Searches compliance document vector store using dense-sparse hybrid RAG."""
    results = hybrid_retrieve_policy_chunks(db, query, limit=limit)
    
    formatted = []
    for chunk, score in results:
        formatted.append({
            "id": chunk.id,
            "content": chunk.content,
            "chunk_index": chunk.chunk_index,
            "document_title": getattr(chunk, "document_title", "Manual"),
            "filename": getattr(chunk, "filename", "policy.pdf"),
            "score": float(score)
        })
    return formatted


@router.post("/ingest", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def ingest_external_compliance_policy(
    payload: PolicyIngestPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingests an external policy document from a URL. Extracts content, chunks,
    generates embeddings, and indexes into the vector store.
    """
    url_str = str(payload.url)
    
    # 1. Fetch content from the URL
    try:
        # Simple HTTP request with a standard user-agent header
        headers = {"User-Agent": "RazorGuard-Policy-Ingest/1.0"}
        response = httpx.get(url_str, headers=headers, timeout=15.0)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        logger.error("policy_ingest_fetch_failed", url=url_str, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to retrieve content from provided URL: {str(e)}"
        )

    # 2. Extract plain text from HTML (simple tag stripping fallback)
    # Remove script and style tags
    clean_html = re.sub(r"<(script|style)\b[^>]*>([\s\S]*?)<\/\1>", "", html_content, flags=re.IGNORECASE)
    # Remove remaining HTML tags
    plain_text = re.sub(r"<[^>]+>", " ", clean_html)
    # Clean whitespace
    plain_text = re.sub(r"\s+", " ", plain_text).strip()

    if not plain_text or len(plain_text) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The retrieved webpage contains insufficient readable text."
        )

    # 3. Check for duplicates using SHA256 hash of plain text
    checksum = hashlib.sha256(plain_text.encode("utf-8")).hexdigest()
    existing = db.query(PolicyDocument).filter(PolicyDocument.checksum == checksum).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Compliance policy content already registered (ID: {existing.id}, Title: {existing.title})."
        )

    # 4. Save Document record
    filename = url_str.split("/")[-1] or "webpage.txt"
    doc_record = PolicyDocument(
        title=payload.title,
        filename=filename,
        checksum=checksum
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    # 5. Chunk and Embed Text
    chunks = split_text_into_sliding_chunks(plain_text, chunk_size=150, overlap=30)
    for index, chunk_data in enumerate(chunks):
        content = chunk_data["content"]
        embedding = generate_embedding(content)
        save_policy_chunk(
            db=db,
            document_id=doc_record.id,
            chunk_index=index,
            content=content,
            embedding=embedding
        )
        
    db.commit()
    logger.info("external_policy_imported_successfully", title=payload.title, url=url_str, chunks_count=len(chunks))

    return {
        "document_id": doc_record.id,
        "title": doc_record.title,
        "filename": doc_record.filename,
        "chunks_indexed": len(chunks),
        "source_url": url_str
    }


