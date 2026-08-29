import time
import json
from datetime import datetime, timezone, timedelta
from typing import Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.risk_assessment import RiskAssessment
from app.models.agent import AgentExecution, AgentMemory
from app.models.graph import GraphEdge
from app.models.evidence import Evidence
from app.models.audit_log import AuditLog
from app.services.agent_team import (
    TransactionRiskAgent,
    BehavioralRiskAgent,
    FraudInvestigationAgent,
    PolicyRAGAgent,
    DecisionAgent,
    ActionAgent
)
from app.ai.llm_service import LLMService
from app.core.logging import logger
from ml.predict import predict_transaction_risk

class AgentOrchestrator:
    """Orchestrates collaborative risk analysis, collects evidence, computes scores, and synthesizes explanation."""

    @classmethod
    def run_investigation(cls, db: Session, transaction_id: str) -> Tuple[RiskAssessment, List[Dict[str, Any]]]:
        """
        Coordinates the multi-agent pipeline for a specific transaction.
        Returns: Tuple of (RiskAssessment model instance, list of reasoning steps dicts)
        """
        start_time = time.time()
        reasoning_steps = []
        
        # 1. Fetch transaction
        tx = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
        if not tx:
            raise ValueError(f"Transaction '{transaction_id}' not found.")
            
        def log_event(event: str, description: str, agent: str = "Orchestrator"):
            now = datetime.now(timezone.utc)
            reasoning_steps.append({
                "timestamp": now.isoformat() + "Z",
                "event": event,
                "description": description,
                "agent": agent
            })
            log = AuditLog(
                transaction_id=tx.id,
                event=event,
                description=description,
                actor=agent,
                timestamp=now
            )
            db.add(log)
            db.flush()

        log_event("transaction_received", f"Orchestrator initiated investigation for transaction {transaction_id}.", "Orchestrator")
        logger.info("orchestrator_investigation_started", transaction_id=transaction_id)
        
        # 2. Run Nearest Centroid ML Classifier
        log_event("analysis_started", "Extracting transaction features for ML model evaluation.", "Orchestrator")
        # Calculate dynamic parameters based on current database state
        location_drift = 4500.0 if tx.billing_country != tx.card_country else 5.0
        
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        velocity_count = db.query(Transaction).filter(
            Transaction.user_id == tx.user_id,
            Transaction.timestamp >= one_hour_ago
        ).count()
        # velocity_1h_including_current: counts all transactions for this user within the last hour, which includes the current transaction being scored.
        velocity_1h_including_current = max(1, velocity_count)

        # Walk graph in-memory or query DB to find shared users
        shared_devices_count = db.query(GraphEdge).filter(
            GraphEdge.relation == "USED_DEVICE",
            GraphEdge.target_type == "Device",
            GraphEdge.target_id == tx.device_fingerprint
        ).count()
        
        if shared_devices_count >= 3:
            device_score = 0.95
        elif shared_devices_count > 0:
            device_score = 0.60
        else:
            device_score = 0.05

        # Predict status and baseline ML score
        ml_class, ml_score = predict_transaction_risk(
            amount=tx.amount,
            location_drift=location_drift,
            velocity_1h_including_current=velocity_1h_including_current,
            device_score=device_score
        )
        log_event("ml_inference_completed", f"ML Classifier generated baseline status '{ml_class}' with score {ml_score:.1f}%.", "ML Classifier")
        
        # 3. Execute Transaction Risk Agent (Rules)
        tx_res = TransactionRiskAgent.process_task(db, tx)
        rule_score = tx_res["score"]
        log_event("agent_completed", f"Transaction Risk Agent finished. Rules score: {rule_score:.1f}%.", "Transaction Risk Agent")
        
        # Save Agent Memory
        m1 = AgentMemory(
            agent_name=tx_res["agent_name"],
            transaction_id=tx.id,
            reasoning=tx_res["outcome"],
            evidence=tx_res["evidence"],
            confidence=100.0 - rule_score
        )
        db.add(m1)
        
        # 4. Execute Behavioral Risk Agent (Velocity)
        beh_res = BehavioralRiskAgent.process_task(db, tx)
        behavioral_score = beh_res["score"]
        log_event("agent_completed", f"Behavioral Risk Agent finished. Velocity score: {behavioral_score:.1f}%.", "Behavioral Risk Agent")
        
        m2 = AgentMemory(
            agent_name=beh_res["agent_name"],
            transaction_id=tx.id,
            reasoning=beh_res["outcome"],
            evidence=beh_res["evidence"],
            confidence=100.0 - behavioral_score
        )
        db.add(m2)
        
        # 5. Execute Fraud Investigation Agent (Knowledge Graph)
        graph_res = FraudInvestigationAgent.process_task(db, tx)
        graph_score = graph_res["score"]
        log_event("graph_completed", f"Fraud Investigation Agent finished. Graph score: {graph_score:.1f}%.", "Fraud Investigation Agent")
        
        m3 = AgentMemory(
            agent_name=graph_res["agent_name"],
            transaction_id=tx.id,
            reasoning=graph_res["outcome"],
            evidence=graph_res["evidence"],
            confidence=100.0 - graph_score
        )
        db.add(m3)
        
        # Write dynamically discovered graph edges to the database
        sql_edges = graph_res.get("paths", [])
        for edge_payload in sql_edges:
            # Check if edge already exists to prevent duplicate paths
            exists = db.query(GraphEdge).filter(
                GraphEdge.source_type == edge_payload.get("type", "Overlap"),
                GraphEdge.source_id == edge_payload.get("node", ""),
                GraphEdge.target_id == edge_payload.get("linked_account", "")
            ).first()
            if not exists:
                ge = GraphEdge(
                    source_type=edge_payload.get("type", "Overlap"),
                    source_id=edge_payload.get("node", ""),
                    relation="SHARED_WITH",
                    target_type="User",
                    target_id=edge_payload.get("linked_account", ""),
                    weight=1.0
                )
                db.add(ge)
                
        # 6. Execute Policy/RAG Agent (Compliance)
        policy_res = PolicyRAGAgent.process_task(db, tx)
        policy_score = policy_res["score"]
        log_event("policy_retrieved", f"Policy/RAG Agent finished. Policy score: {policy_score:.1f}%.", "Policy Agent")
        
        m4 = AgentMemory(
            agent_name=policy_res["agent_name"],
            transaction_id=tx.id,
            reasoning=policy_res["outcome"],
            evidence=policy_res["evidence"],
            confidence=100.0 - policy_score
        )
        db.add(m4)
        
        # 7. Execute Decision Agent (Weighted Consensus)
        # S_Rule component is the average of transaction rules and customer behavioral logs
        rule_component = (rule_score + behavioral_score) / 2.0
        dec_res = DecisionAgent.process_task(
            db=db,
            ml_score=ml_score,
            rule_score=rule_component,
            graph_score=graph_score,
            policy_score=policy_score
        )
        overall_score = dec_res["score"]
        classification = dec_res["classification"]
        log_event("risk_calculated", f"Decision Agent compiled composite score: {overall_score:.1f}%. Classification: {classification}.", "Decision Agent")
        
        m5 = AgentMemory(
            agent_name=dec_res["agent_name"],
            transaction_id=tx.id,
            reasoning=dec_res["outcome"],
            evidence=dec_res["evidence"],
            confidence=95.0
        )
        db.add(m5)
        
        # 8. Execute Action Agent (Routing status)
        act_res = ActionAgent.process_task(db, tx, classification, overall_score)
        log_event("recommendation_generated", f"Action Agent resolved status routing: {act_res['action']} -> {act_res['status']}.", "Action Agent")
        
        m6 = AgentMemory(
            agent_name=act_res["agent_name"],
            transaction_id=tx.id,
            reasoning=act_res["outcome"],
            evidence=act_res["evidence"],
            confidence=99.0
        )
        db.add(m6)

        # 9. Save all structured evidences to the database
        all_structured_evidences = []
        if "evidences" in tx_res:
            all_structured_evidences.extend(tx_res["evidences"])
        if "evidences" in beh_res:
            all_structured_evidences.extend(beh_res["evidences"])
        if "evidences" in graph_res:
            all_structured_evidences.extend(graph_res["evidences"])
        if "evidences" in policy_res:
            all_structured_evidences.extend(policy_res["evidences"])

        # Add ML signal to structured evidences
        all_structured_evidences.append({
            "category": "model_signal",
            "severity": "high" if ml_score >= 75 else ("medium" if ml_score >= 40 else "low"),
            "value": f"ML Score: {ml_score:.1f}%",
            "description": f"Nearest Centroid ML classifier generated baseline risk score of {ml_score:.1f}%.",
            "source": "ML Classifier",
            "confidence": 0.9,
            "supporting_entity": "Centroid Model"
        })

        # Clear previous evidences for this transaction before adding new ones
        db.query(Evidence).filter(Evidence.transaction_id == tx.id).delete(synchronize_session=False)

        for idx, ev_data in enumerate(all_structured_evidences):
            ev_id = f"EV-{tx.transaction_id}-{idx+1}"
            evidence_record = Evidence(
                transaction_id=tx.id,
                evidence_id=ev_id,
                category=ev_data["category"],
                severity=ev_data["severity"],
                value=ev_data.get("value"),
                description=ev_data["description"],
                source=ev_data["source"],
                confidence=ev_data.get("confidence", 1.0),
                supporting_entity=ev_data.get("supporting_entity"),
                supporting_transaction=ev_data.get("supporting_transaction"),
                policy_reference=ev_data.get("policy_reference"),
                timestamp=datetime.now(timezone.utc)
            )
            db.add(evidence_record)
        
        # 10. LLM Synthesis & Explanation Generation grounded in structured evidence
        evidence_lines = []
        for ev in all_structured_evidences:
            ref_str = f" ({ev['policy_reference']})" if ev.get('policy_reference') else ""
            evidence_lines.append(f"- [{ev['category'].upper()}] Source: {ev['source']} | Severity: {ev['severity'].upper()} | Value: {ev['value']} | Description: {ev['description']}{ref_str}")
        
        evidence_text = "\n".join(evidence_lines) if evidence_lines else "No suspicious evidence detected."

        llm_prompt = (
            f"Please synthesize a detailed payment risk briefing explanation.\n"
            f"Transaction ID: {tx.transaction_id}\n"
            f"User ID: {tx.user_id}\n"
            f"Amount: {tx.currency} {tx.amount}\n"
            f"Card Present: {tx.card_present}\n"
            f"Billing Country: {tx.billing_country} | Card Country: {tx.card_country}\n"
            f"Calculated Score: {overall_score:.1f}%\n"
            f"Risk Classification: {classification}\n\n"
            f"Agent Inputs:\n"
            f"- Transaction Rules: {tx_res['evidence']}\n"
            f"- Behavior History: {beh_res['evidence']}\n"
            f"- Network Graph walks: {graph_res['evidence']}\n"
            f"- Compliance Policy: {policy_res['evidence']}\n\n"
            f"Structured Evidence:\n{evidence_text}\n"
        )
        
        system_prompt = (
            "You are the consensus explanation engine for RazorGuard AI risk platform.\n"
            "Produce a structured markdown summary explaining the risk factors in a clear "
            "and professional tone suitable for compliance officers. "
            "Every statement in your briefing MUST be grounded in the provided Structured Evidence.\n"
            "If evidence is unavailable for any of the categories, state 'Evidence unavailable.' for that section.\n"
            "Highlight specific rule breaches, citation footnotes for any compliance documents, "
            "and explain graph relationship overlaps clearly."
        )
        
        explanation_markdown = LLMService.generate_response(llm_prompt, system_prompt)
        
        # 11. Persist Risk Assessment
        db.query(RiskAssessment).filter(RiskAssessment.transaction_id == tx.id).delete(synchronize_session=False)
        db.query(AgentExecution).filter(AgentExecution.transaction_id == tx.id).delete(synchronize_session=False)
        
        assessment = RiskAssessment(
            transaction_id=tx.id,
            overall_score=overall_score,
            classification=classification,
            ml_score=ml_score,
            rule_score=rule_component,
            graph_score=graph_score,
            policy_score=policy_score,
            explanation=explanation_markdown,
            analyzed_at=datetime.now(timezone.utc)
        )
        db.add(assessment)
        
        # 12. Log Execution Trace
        duration = time.time() - start_time
        exec_trace = AgentExecution(
            transaction_id=tx.id,
            agents_used="TransactionRiskAgent, BehavioralRiskAgent, FraudInvestigationAgent, PolicyRAGAgent, DecisionAgent, ActionAgent",
            reasoning_steps=reasoning_steps,
            evidence_retrieved=f"Rules: {tx_res['evidence']} | Graph: {graph_res['evidence']} | RAG: {policy_res['evidence']}",
            duration=duration
        )
        db.add(exec_trace)
        
        db.commit()
        logger.info("orchestrator_investigation_completed", transaction_id=transaction_id, final_score=overall_score)
        
        return assessment, reasoning_steps
