from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
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
    AnalystDecisionSubmit,
    AnalystEfficiencyOut
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


@router.get("/metrics/efficiency", response_model=AnalystEfficiencyOut)
def get_analyst_efficiency_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Computes analyst efficiency metrics including mean agent execution duration,
    mean analyst review time, case volumes, and justification percentages.
    """
    # 1. Avg investigation time
    avg_inv_val = db.query(func.avg(AgentExecution.duration)).scalar()
    avg_investigation_time_seconds = float(avg_inv_val) if avg_inv_val is not None else 0.0

    # 2. Avg analyst review time
    decisions_with_assessments = db.query(
        AnalystDecision.submitted_at, 
        RiskAssessment.analyzed_at
    ).join(
        RiskAssessment, 
        RiskAssessment.transaction_id == AnalystDecision.transaction_id
    ).all()
    
    if decisions_with_assessments:
        diffs = [
            (sub - ana).total_seconds() / 60.0 
            for sub, ana in decisions_with_assessments
        ]
        avg_analyst_review_minutes = sum(diffs) / len(diffs)
    else:
        avg_analyst_review_minutes = 0.0

    # 3. Total cases processed (distinct transactions with a RiskAssessment)
    total_cases_processed = db.query(RiskAssessment.transaction_id).distinct().count()

    # 4. Total overrides submitted
    total_overrides_submitted = db.query(AnalystDecision).count()

    # 5. Justification percentage
    if total_overrides_submitted > 0:
        justified = db.query(AnalystDecision).filter(
            AnalystDecision.notes.isnot(None),
            AnalystDecision.notes != ""
        ).count()
        pct_decisions_with_justification = (justified / total_overrides_submitted) * 100.0
    else:
        pct_decisions_with_justification = 0.0

    # 6. Cases by classification
    classification_counts = {"Safe": 0, "Suspicious": 0, "High Risk": 0}
    class_results = db.query(
        RiskAssessment.classification, 
        func.count(RiskAssessment.id)
    ).group_by(RiskAssessment.classification).all()
    
    for class_name, count in class_results:
        if class_name:
            classification_counts[class_name] = count

    return {
        "avg_investigation_time_seconds": avg_investigation_time_seconds,
        "avg_analyst_review_minutes": avg_analyst_review_minutes,
        "total_cases_processed": total_cases_processed,
        "total_overrides_submitted": total_overrides_submitted,
        "pct_decisions_with_justification": pct_decisions_with_justification,
        "cases_by_classification": classification_counts
    }


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
    decisions = db.query(AnalystDecision).filter(AnalystDecision.transaction_id == id).all()

    reasoning_steps = execution.reasoning_steps if execution else []
    
    # Map decisions to include analyst email
    decisions_out = []
    for d in decisions:
        decisions_out.append({
            "id": d.id,
            "transaction_id": d.transaction_id,
            "analyst_id": d.analyst_id,
            "action": d.action,
            "notes": d.notes,
            "submitted_at": d.submitted_at,
            "original_ai_recommendation": d.original_ai_recommendation,
            "analyst_email": d.analyst.email if d.analyst else "Unknown Analyst"
        })
    
    return {
        "transaction": tx,
        "assessment": assessment,
        "reasoning_steps": reasoning_steps,
        "memories": memories,
        "decisions": decisions_out
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

    # Save analyst decision override, persisting the original status as recommendation
    decision = AnalystDecision(
        transaction_id=tx.id,
        analyst_id=current_user.id,
        action=payload.action,
        notes=payload.notes,
        original_ai_recommendation=tx.status
    )
    db.add(decision)

    # Update transaction status
    tx.status = action_status
    db.add(tx)
    db.commit()
    db.refresh(tx)

    logger.info("analyst_override_submitted", transaction_id=tx.transaction_id, action=payload.action, analyst=current_user.email)
    return tx
