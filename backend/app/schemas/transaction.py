from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class MerchantCategory(str, Enum):
    FOOD = "food"
    ELECTRONICS = "electronics"
    CRYPTO = "crypto"
    RETAIL = "retail"
    GAMING = "gaming"
    TRAVEL = "travel"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


class TransactionCreate(BaseModel):
    transaction_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    user_id: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    amount: float = Field(..., gt=0.0)
    currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    device_fingerprint: str = Field(..., min_length=1, max_length=128)
    ip_address: str = Field(..., min_length=1, max_length=45)
    billing_country: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    card_country: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    card_present: bool
    merchant_id: str = Field(..., min_length=1, max_length=100)
    merchant_category: MerchantCategory

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        import ipaddress
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("Invalid IP address format")
        return v


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
    merchant_category: MerchantCategory
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
    evidence: Optional[str] = None
    confidence: float

    model_config = ConfigDict(from_attributes=True)

class AnalystDecisionSubmit(BaseModel):
    action: str # "Approve", "Block", "Escalate"
    notes: Optional[str] = None

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

class MerchantSubmissionOut(BaseModel):
    id: int
    transaction_id: int
    notes: str
    document_url: Optional[str]
    target_category: Optional[str] = None
    submitted_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)

class MerchantSubmissionCreate(BaseModel):
    notes: str
    document_url: Optional[str] = None
    target_category: Optional[str] = None

class InvestigationOut(BaseModel):
    transaction: TransactionOut
    assessment: Optional[RiskAssessmentOut]
    reasoning_steps: List[Dict] # structured timeline trace
    memories: List[AgentMemoryOut]
    evidences: List[EvidenceOut] = []
    audit_logs: List[AuditLogOut] = []
    decisions: List[AnalystDecisionOut] = []
    submissions: List[MerchantSubmissionOut] = []

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


