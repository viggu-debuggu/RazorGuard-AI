from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime


class TransactionCreate(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    device_fingerprint: str
    ip_address: str
    billing_country: str
    card_country: str
    card_present: bool
    merchant_id: str
    merchant_category: str

class TransactionOut(BaseModel):
    id: int
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    device_fingerprint: str
    ip_address: str
    billing_country: str
    card_country: str
    card_present: bool
    merchant_id: str
    merchant_category: str
    status: str
    risk_score: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class RiskAssessmentOut(BaseModel):
    overall_score: float
    classification: str
    ml_score: float
    rule_score: float
    graph_score: float
    policy_score: float
    explanation: Optional[str]
    analyzed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AgentMemoryOut(BaseModel):
    agent_name: str
    reasoning: str
    evidence: Optional[str]
    confidence: float

    model_config = ConfigDict(from_attributes=True)

class AnalystDecisionSubmit(BaseModel):
    action: str # "Approve", "Block", "Escalate"
    notes: Optional[str]

class AnalystDecisionOut(BaseModel):
    id: int
    transaction_id: int
    analyst_id: int
    action: str
    notes: Optional[str]
    submitted_at: datetime
    original_ai_recommendation: Optional[str] = None
    analyst_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class EvidenceOut(BaseModel):
    evidence_id: str
    category: str
    severity: str
    value: Optional[str]
    description: str
    source: str
    confidence: float
    timestamp: datetime
    supporting_entity: Optional[str] = None
    supporting_transaction: Optional[str] = None
    policy_reference: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AuditLogOut(BaseModel):
    id: int
    event: str
    description: str
    actor: str
    timestamp: datetime
    metadata_json: Optional[Dict] = None

    model_config = ConfigDict(from_attributes=True)

class InvestigationOut(BaseModel):
    transaction: TransactionOut
    assessment: Optional[RiskAssessmentOut]
    reasoning_steps: List[Dict] # structured timeline trace
    memories: List[AgentMemoryOut]
    decidences: Optional[List[EvidenceOut]] = None # alias or explicit evidences
    evidences: List[EvidenceOut] = []
    audit_logs: List[AuditLogOut] = []
    decisions: List[AnalystDecisionOut] = []

class AnalystEfficiencyOut(BaseModel):
    avg_investigation_time_seconds: float
    avg_analyst_review_minutes: float
    total_cases_processed: int
    total_overrides_submitted: int
    pct_decisions_with_justification: float
    cases_by_classification: Dict[str, int]

    model_config = ConfigDict(from_attributes=True)

class DashboardMetricsOut(BaseModel):
    processed_today: int
    auto_approved: int
    awaiting_review: int
    blocked: int
    avg_risk_score: float
    volume_trend: List[Dict[str, Any]]
    rule_trigger_frequency: Dict[str, int]
    graph_relationships_count: int
    latency_trend_seconds: float

    model_config = ConfigDict(from_attributes=True)


