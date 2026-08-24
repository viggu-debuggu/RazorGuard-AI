from pydantic import BaseModel, ConfigDict
from typing import List, Optional
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

class InvestigationOut(BaseModel):
    transaction: TransactionOut
    assessment: Optional[RiskAssessmentOut]
    reasoning_steps: List[str]
    memories: List[AgentMemoryOut]
    decisions: List[AnalystDecisionOut] = []
