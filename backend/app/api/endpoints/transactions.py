from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.database.session import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.risk_assessment import RiskAssessment
from app.models.agent import AgentExecution, AgentMemory
from app.models.decision import AnalystDecision
from app.models.evidence import Evidence
from app.models.audit_log import AuditLog
from app.models.graph import GraphEdge
from app.models.merchant_submission import MerchantSubmission
from app.schemas.transaction import (
    TransactionCreate,
    TransactionOut,
    InvestigationOut,
    AnalystDecisionSubmit,
    AnalystEfficiencyOut,
    DashboardMetricsOut,
    MerchantSubmissionCreate
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


@router.get("/metrics/dashboard", response_model=DashboardMetricsOut)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns real, calculated statistics and data monitoring health indicators from the DB.
    """
    # 1. Total processed today (since start of day)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    processed_today = db.query(Transaction).filter(Transaction.timestamp >= today_start).count()

    # 2. Count by statuses
    auto_approved = db.query(Transaction).filter(Transaction.status == "Approved").count()
    awaiting_review = db.query(Transaction).filter(Transaction.status == "Escalated").count()
    blocked = db.query(Transaction).filter(Transaction.status == "Blocked").count()

    # 3. Avg risk score
    avg_score_val = db.query(func.avg(Transaction.risk_score)).scalar()
    avg_risk_score = float(avg_score_val) if avg_score_val is not None else 0.0

    # 4. Latency
    avg_lat_val = db.query(func.avg(AgentExecution.duration)).scalar()
    latency_trend_seconds = float(avg_lat_val) if avg_lat_val is not None else 0.0

    # 5. Graph relationships count
    graph_relationships_count = db.query(GraphEdge).count()

    # 6. Rule trigger frequencies
    rule_trigger_frequency = {
        "LARGE_TICKET_AMOUNT": db.query(Evidence).filter(Evidence.description.like("%LARGE_TICKET_AMOUNT%")).count(),
        "GEOGRAPHIC_MISMATCH": db.query(Evidence).filter(Evidence.category == "geographic_mismatch").count(),
        "HIGH_VALUE_CNP": db.query(Evidence).filter(Evidence.description.like("%HIGH_VALUE_CNP%")).count(),
        "VELOCITY_SPIKE_1H": db.query(Evidence).filter(Evidence.category == "velocity").count(),
        "TICKET_SIZE_DEVIATION": db.query(Evidence).filter(Evidence.description.like("%TICKET_SIZE_DEVIATION%")).count(),
        "UNPROFILED_LARGE_SUM": db.query(Evidence).filter(Evidence.description.like("%UNPROFILED_LARGE_SUM%")).count(),
    }

    # 7. Volume trend for last 24 hours (grouped by hour)
    volume_trend = []
    now = datetime.utcnow()
    for h in range(24):
        target_hour = now - timedelta(hours=23 - h)
        hour_start = target_hour.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        
        # Ingested count
        vol = db.query(Transaction).filter(
            Transaction.timestamp >= hour_start,
            Transaction.timestamp < hour_end
        ).count()

        # Risk events (Suspicious / High risk classification count today)
        risk = db.query(Transaction).filter(
            Transaction.timestamp >= hour_start,
            Transaction.timestamp < hour_end,
            Transaction.risk_score >= 40.0
        ).count()

        volume_trend.append({
            "time": hour_start.strftime("%H:%M"),
            "volume": vol,
            "risk": risk
        })

    return {
        "processed_today": processed_today,
        "auto_approved": auto_approved,
        "awaiting_review": awaiting_review,
        "blocked": blocked,
        "avg_risk_score": avg_risk_score,
        "volume_trend": volume_trend,
        "rule_trigger_frequency": rule_trigger_frequency,
        "graph_relationships_count": graph_relationships_count,
        "latency_trend_seconds": latency_trend_seconds
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
    evidences = db.query(Evidence).filter(Evidence.transaction_id == id).all()
    audit_logs = db.query(AuditLog).filter(AuditLog.transaction_id == id).order_by(AuditLog.timestamp.asc()).all()

    raw_steps = execution.reasoning_steps if execution else []
    reasoning_steps = []
    
    for step in raw_steps:
        if isinstance(step, dict):
            reasoning_steps.append(step)
        else:
            # Fallback wrapper for old string steps
            reasoning_steps.append({
                "timestamp": tx.timestamp.isoformat() + "Z",
                "event": "orchestrator_log",
                "description": str(step),
                "agent": "Orchestrator"
            })
    
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
        "evidences": evidences,
        "audit_logs": audit_logs,
        "decisions": decisions_out,
        "submissions": tx.submissions
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

    original_rec = tx.status

    # Capture evidence snapshot for auditability
    evs = db.query(Evidence).filter(Evidence.transaction_id == tx.id).all()
    evidence_snapshot = []
    for e in evs:
        evidence_snapshot.append({
            "evidence_id": e.evidence_id,
            "category": e.category,
            "severity": e.severity,
            "value": e.value,
            "description": e.description,
            "source": e.source,
            "confidence": e.confidence,
            "timestamp": e.timestamp.isoformat()
        })

    # Save analyst decision override, persisting score and evidence snapshot
    decision = AnalystDecision(
        transaction_id=tx.id,
        analyst_id=current_user.id,
        action=payload.action,
        notes=payload.notes,
        original_ai_recommendation=original_rec,
        risk_score_at_decision_time=tx.risk_score,
        evidence_snapshot=evidence_snapshot
    )
    db.add(decision)

    # Update transaction status
    tx.status = action_status
    db.add(tx)

    # Write to AuditLog
    event_name = "decision_overridden" if action_status != original_rec else "analyst_reviewed"
    audit_desc = f"Analyst override committed. Final status transitioned from '{original_rec}' to '{action_status}' with notes: \"{payload.notes}\"."
    
    log = AuditLog(
        transaction_id=tx.id,
        event=event_name,
        description=audit_desc,
        actor=f"Analyst: {current_user.email}",
        timestamp=datetime.utcnow(),
        metadata_json={
            "action": payload.action,
            "previous_status": original_rec,
            "new_status": action_status,
            "risk_score": tx.risk_score
        }
    )
    db.add(log)
    db.commit()
    db.refresh(tx)

    logger.info("analyst_override_submitted", transaction_id=tx.transaction_id, action=payload.action, analyst=current_user.email)
    return tx


@router.post("/{id}/merchant-submit", response_model=TransactionOut)
def submit_merchant_evidence(
    id: int,
    payload: MerchantSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submits explanation notes and mocked document verification links for the transaction hold resolution."""
    tx = db.query(Transaction).filter(Transaction.id == id).first()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found."
        )

    # Save merchant submission
    sub = MerchantSubmission(
        transaction_id=tx.id,
        notes=payload.notes,
        document_url=payload.document_url,
        target_category=payload.target_category,
        status="Submitted",
        submitted_at=datetime.utcnow()
    )
    db.add(sub)
    db.flush()

    # Log to Audit trail
    log = AuditLog(
        transaction_id=tx.id,
        event="merchant_evidence_submitted",
        description=(
            f"Merchant submitted hold verification materials (category: {payload.target_category or 'general'}). notes: \"{payload.notes}\""
            + (f", document: '{payload.document_url}'" if payload.document_url else "")
            + "."
        ),
        actor=f"Merchant Account: {tx.user_id}",
        timestamp=datetime.utcnow(),
        metadata_json={
            "notes": payload.notes,
            "document": payload.document_url,
            "target_category": payload.target_category
        }
    )
    db.add(log)
    db.commit()

    # Trigger Multi-Agent Re-evaluation
    try:
        AgentOrchestrator.run_investigation(db, tx.transaction_id)
        db.refresh(tx)
        
        # Log resolution status transition if status became Approved
        if tx.status == "Approved":
            log_resolve = AuditLog(
                transaction_id=tx.id,
                event="auto_resolved",
                description=f"Transaction automatically resolved and approved after verifying merchant materials. Risk score updated to {tx.risk_score:.0f}%.",
                actor="System Orchestrator",
                timestamp=datetime.utcnow(),
                metadata_json={
                    "new_score": tx.risk_score,
                    "new_status": tx.status
                }
            )
            db.add(log_resolve)
            db.commit()
            db.refresh(tx)
    except Exception as e:
        logger.error("reevaluation_failed", transaction_id=tx.transaction_id, error=str(e))
        db.rollback()

    return tx

