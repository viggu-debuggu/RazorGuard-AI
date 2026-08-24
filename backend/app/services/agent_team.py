from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.policy import PolicyChunk
from app.ai.rag_service import hybrid_retrieve_policy_chunks
from knowledge_graph.network_builder import PaymentNetworkGraph
from ml.predict import predict_transaction_risk

class TransactionRiskAgent:
    """Specialist evaluating immediate transaction features against core anti-fraud rules."""
    
    @staticmethod
    def process_task(db: Session, tx: Transaction) -> Dict[str, Any]:
        violations = []
        evidence_logs = []
        
        # Rule 1: High transaction amount check
        if tx.amount > 500000.0:
            violations.append("LARGE_TICKET_AMOUNT")
            evidence_logs.append("[LARGE_TICKET_AMOUNT] Transaction amount exceeds maximum soft limit of INR 500,000.")
            
        # Rule 2: Country mismatch check (Card origin vs Billing)
        if tx.billing_country != tx.card_country:
            violations.append("GEOGRAPHIC_MISMATCH")
            evidence_logs.append(f"[GEOGRAPHIC_MISMATCH] Billing country '{tx.billing_country}' does not match card country '{tx.card_country}'.")
            
        # Rule 3: High amount Card-Not-Present transaction
        if not tx.card_present and tx.amount > 50000.0:
            violations.append("HIGH_VALUE_CNP")
            evidence_logs.append("[HIGH_VALUE_CNP] Card-Not-Present transaction exceeds high-risk threshold of INR 50,000.")

        # Calculate rule score: 25.0 per violation, capped at 100.0
        rule_score = min(100.0, len(violations) * 33.3)
        
        outcome = (
            f"Transaction profiled. Violations found: {len(violations)}. "
            f"Rule status evaluates at {rule_score:.1f}% risk severity."
        )
        
        return {
            "agent_name": "Transaction Risk Agent",
            "score": float(rule_score),
            "outcome": outcome,
            "evidence": " | ".join(evidence_logs) if evidence_logs else "No heuristic rule violations detected."
        }


class BehavioralRiskAgent:
    """Specialist evaluating card velocities, spending averages, and time-drift patterns."""
    
    @staticmethod
    def process_task(db: Session, tx: Transaction) -> Dict[str, Any]:
        violations = []
        evidence_logs = []
        
        # Rule 1: Instant velocity check in the last 1 hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_count = db.query(Transaction).filter(
            Transaction.user_id == tx.user_id,
            Transaction.timestamp >= one_hour_ago
        ).count()
        
        if recent_count > 5:
            violations.append("VELOCITY_SPIKE_1H")
            evidence_logs.append(f"High velocity transaction rate detected: {recent_count} payments in the last hour.")
            
        # Rule 2: Deviation from average ticket size
        # Calculate user's average past transaction amount (Approved payments only)
        avg_res = db.query(Transaction.amount).filter(
            Transaction.user_id == tx.user_id,
            Transaction.status == "Approved",
            Transaction.id != tx.id
        ).all()
        
        if avg_res:
            avg_val = sum(r[0] for r in avg_res) / len(avg_res)
            # If current amount is 3x the average historical ticket size
            if tx.amount > (avg_val * 3.0) and tx.amount > 10000.0:
                violations.append("TICKET_SIZE_DEVIATION")
                evidence_logs.append(f"Amount INR {tx.amount} is 3x greater than customer historical average of INR {avg_val:.2f}.")
        else:
            # First transaction check: moderate risk warning for unprofiled users on large sums
            if tx.amount > 100000.0:
                violations.append("UNPROFILED_LARGE_SUM")
                evidence_logs.append("First transaction registered for user exceeds baseline limit of INR 100,000.")

        behavioral_score = min(100.0, len(violations) * 50.0)
        outcome = f"Behavioral velocity analyzed. Detected anomalies: {len(violations)}."
        
        return {
            "agent_name": "Behavioral Risk Agent",
            "score": float(behavioral_score),
            "outcome": outcome,
            "evidence": " | ".join(evidence_logs) if evidence_logs else "Customer spending velocity within normal historical bounds."
        }


class FraudInvestigationAgent:
    """Specialist performing 3-hop walks across the payment graph database to uncover shared devices/IP loops."""
    
    @staticmethod
    def process_task(db: Session, tx: Transaction) -> Dict[str, Any]:
        # 1. Initialize network and build from current state of edges in DB
        graph = PaymentNetworkGraph()
        graph.build_from_db(db)
        
        # 2. Add current transaction nodes and edges to graph in-memory for testing
        graph.add_transaction_nodes_and_edges(tx)
        
        # 3. Walk relationships
        degrees_of_sharing, shared_entities, paths = graph.walk_shared_relationships(tx.user_id, "User")
        
        # Compute graph score: 33.3 per degree of sharing, capped at 100.0
        graph_score = min(100.0, degrees_of_sharing * 33.3)
        
        if degrees_of_sharing > 0:
            outcome = f"Relational walking detected link overlaps. Overlapping accounts: {degrees_of_sharing}."
            evidence = " | ".join(shared_entities)
        else:
            outcome = "Graph walking completed. Node is isolated from other registered entities."
            evidence = "No shared device fingerprints or IP addresses linked to external customer accounts."
            
        return {
            "agent_name": "Fraud Investigation Agent",
            "score": float(graph_score),
            "outcome": outcome,
            "evidence": evidence,
            "paths": paths
        }


class PolicyRAGAgent:
    """Specialist retrieving compliance policy vector chunks and mapping citations."""
    
    @staticmethod
    def process_task(db: Session, tx: Transaction) -> Dict[str, Any]:
        # Construct search query for RAG
        search_query = f"{tx.merchant_category} merchant categories card-not-present limitations and compliance verification"
        
        # Query policy chunks
        matching_chunks = hybrid_retrieve_policy_chunks(db, search_query, limit=2)
        
        policy_score = 0.0
        evidence_logs = []
        citations = []
        
        if matching_chunks:
            for chunk, score in matching_chunks:
                evidence_logs.append(chunk.content[:200] + "...")
                citations.append(f"[Source: {chunk.filename}, Index: {chunk.chunk_index}]")
                # If policy text contains risk keywords matching the current transaction's category
                if "block" in chunk.content.lower() or "requires verification" in chunk.content.lower():
                    if tx.amount > 50000.0:
                        policy_score = 100.0 # Force policy compliance review
                        
            outcome = f"Compliance policies verified. Citations resolved: {len(citations)}."
            evidence = " | ".join(evidence_logs) + " " + " ".join(citations)
        else:
            outcome = "No applicable compliance guidelines resolved in RAG registry."
            evidence = "No active regulatory rules breached. RAG returned empty search index."
            
        return {
            "agent_name": "Policy/RAG Agent",
            "score": float(policy_score),
            "outcome": outcome,
            "evidence": evidence,
            "citations": citations
        }


class DecisionAgent:
    """Specialist aggregating metrics, running composite scoring formula, and assigning risk label."""
    
    @staticmethod
    def process_task(
        db: Session, 
        ml_score: float, 
        rule_score: float, 
        graph_score: float, 
        policy_score: float
    ) -> Dict[str, Any]:
        # Weights: ML (35%), Heuristic Rules (20%), KG overlaps (30%), Policy RAG (15%)
        composite_score = (
            (0.35 * ml_score) + 
            (0.20 * rule_score) + 
            (0.30 * graph_score) + 
            (0.15 * policy_score)
        )
        
        if composite_score < 40.0:
            classification = "Safe"
        elif composite_score < 75.0:
            classification = "Suspicious"
        else:
            classification = "High Risk"
            
        outcome = (
            f"Consensus achieved. Weighted risk score evaluates at {composite_score:.1f}%. "
            f"Risk Classification: {classification}."
        )
        
        evidence = (
            f"Scoring breakdown -> ML: {ml_score:.0f}% | Rules: {rule_score:.0f}% | "
            f"Graph: {graph_score:.0f}% | Policy: {policy_score:.0f}%"
        )
        
        return {
            "agent_name": "Decision Agent",
            "score": float(composite_score),
            "classification": classification,
            "outcome": outcome,
            "evidence": evidence
        }


class ActionAgent:
    """Specialist routing final status and initiating escalations or auto-approvals."""
    
    @staticmethod
    def process_task(db: Session, tx: Transaction, classification: str, score: float) -> Dict[str, Any]:
        old_status = tx.status
        
        # Threshold Routing
        if classification == "Safe":
            new_status = "Approved"
            action = "AUTO_APPROVE"
            explanation = "Transaction risk score is low. Automatic approval processed."
        elif classification == "Suspicious":
            new_status = "Approved" # System warns but releases
            action = "FLAG_AND_RELEASE"
            explanation = "Transaction flagged as suspicious. System released payment but enqueued alert."
        else: # High Risk
            new_status = "Escalated" # Hold payment
            action = "HOLD_AND_ESCALATE"
            explanation = "High risk indicators. Transaction suspended, pending manual analyst review."
            
        # Update transaction status and score in DB
        tx.status = new_status
        tx.risk_score = score
        db.add(tx)
        db.flush()
        
        outcome = f"Transaction status transitioned from '{old_status}' to '{new_status}' via rule '{action}'."
        
        return {
            "agent_name": "Action/Escalation Agent",
            "action": action,
            "status": new_status,
            "outcome": outcome,
            "evidence": explanation
        }
