import hashlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
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


