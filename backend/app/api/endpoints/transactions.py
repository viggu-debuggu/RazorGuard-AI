from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.session import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.risk_assessment import RiskAssessment
from app.models.agent import AgentExecution, AgentMemory
from app.models.decision import AnalystDecision
from app.schemas.transaction import (
    TransactionCreate,
    TransactionOut,
    InvestigationOut,
    AnalystDecisionSubmit
)
from app.services.agent_orchestrator import AgentOrchestrator
from app.core.logging import logger

router = APIRouter()


@router.post("/", response_model=TransactionOut, status_code=status.HTTP_202_ACCEPTED)
def ingest_payment_transaction(
    payload: TransactionCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingests a new transaction and automatically triggers the autonomous multi-agent
    investigation, RAG parsing, and consensus risk scoring engine.
    """
    # Check if duplicate transaction
    existing = db.query(Transaction).filter(Transaction.transaction_id == payload.transaction_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction ID already exists."
        )

    # Ingest record in pending state
    tx = Transaction(
        transaction_id=payload.transaction_id,
        user_id=payload.user_id,
        amount=payload.amount,
        currency=payload.currency,
        device_fingerprint=payload.device_fingerprint,
        ip_address=payload.ip_address,
        billing_country=payload.billing_country,
        card_country=payload.card_country,
        card_present=payload.card_present,
        merchant_id=payload.merchant_id,
        merchant_category=payload.merchant_category,
        status="Pending",
        risk_score=0.0
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    try:
        # Trigger Multi-Agent Orchestrator
        AgentOrchestrator.run_investigation(db, tx.transaction_id)
        db.refresh(tx)
    except Exception as e:
        logger.error("orchestrator_execution_failed_during_ingest", transaction_id=tx.transaction_id, error=str(e))
        # Fallback to general escalated status if agent pipeline fails
        tx.status = "Escalated"
        db.add(tx)
        db.commit()

    return tx


@router.get("/", response_model=List[TransactionOut])
def list_transactions_queue(
    status: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all transactions in the queue with active status filters."""
    query = db.query(Transaction)
    if status:
        query = query.filter(Transaction.status == status)
    if min_score is not None:
        query = query.filter(Transaction.risk_score >= min_score)
        
    transactions = query.order_by(Transaction.timestamp.desc()).offset(offset).limit(limit).all()
    return transactions


@router.get("/{id}", response_model=TransactionOut)
def get_transaction_details(
    id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves metadata of a specific transaction."""
    tx = db.query(Transaction).filter(Transaction.id == id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found."
        )
    return tx


@router.get("/{id}/investigation", response_model=InvestigationOut)
def get_transaction_investigation(
    id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves full agent reasoning steps, evidence summary, and grounding RAG explanation."""
    tx = db.query(Transaction).filter(Transaction.id == id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found."
        )

    assessment = db.query(RiskAssessment).filter(RiskAssessment.transaction_id == id).first()
    execution = db.query(AgentExecution).filter(AgentExecution.transaction_id == id).first()
    memories = db.query(AgentMemory).filter(AgentMemory.transaction_id == id).all()

    reasoning_steps = execution.reasoning_steps if execution else []
    
    return {
        "transaction": tx,
        "assessment": assessment,
        "reasoning_steps": reasoning_steps,
        "memories": memories
    }


@router.post("/{id}/resolve", response_model=TransactionOut)
def submit_analyst_decision(
    id: int,
    payload: AnalystDecisionSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submits a human-in-the-loop override decision (Approve / Block / Escalate) with analyst justification notes."""
    tx = db.query(Transaction).filter(Transaction.id == id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found."
        )

    # Map the action to new transaction status
    status_mapping = {
        "Approve": "Approved",
        "Block": "Blocked",
        "Escalate": "Escalated"
    }

    action_status = status_mapping.get(payload.action)
    if not action_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action payload '{payload.action}'. Select Approve, Block, or Escalate."
        )

    # Save analyst decision override
    decision = AnalystDecision(
        transaction_id=tx.id,
        analyst_id=current_user.id,
        action=payload.action,
        notes=payload.notes
    )
    db.add(decision)

    # Update transaction status
    tx.status = action_status
    db.add(tx)
    db.commit()
    db.refresh(tx)

    logger.info("analyst_override_submitted", transaction_id=tx.transaction_id, action=payload.action, analyst=current_user.email)
    return tx
