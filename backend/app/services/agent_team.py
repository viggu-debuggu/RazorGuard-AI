from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.policy import PolicyChunk
from app.ai.rag_service import hybrid_retrieve_policy_chunks
from knowledge_graph.network_builder import PaymentNetworkGraph

def submission_addresses_category(submission, category: str) -> bool:
    if not submission:
        return False
    # If the submission explicitly targets this category
    if getattr(submission, "target_category", None) == category:
        return True
    
    # Keyword-based check as backup/fallback
    notes_lower = (submission.notes or "").lower()
    doc_lower = (submission.document_url or "").lower()
    
    if category == "rules":
        keywords = ["billing", "card", "mismatch", "cnp", "country", "limit", "amount", "present", "ticket"]
    elif category == "velocity":
        keywords = ["velocity", "spending", "frequency", "limit", "volume", "amount", "average", "pattern", "velocity_spike_1h", "velocity_spike", "ticket_size_deviation"]
    elif category == "graph":
        keywords = ["device", "ip", "shared", "hardware", "network", "overlap", "identity", "connection", "used_device", "shared_with"]
    elif category == "policy":
        keywords = ["policy", "compliance", "regulation", "guideline", "directive", "legal", "terms", "verification directive"]
    else:
        keywords = []
        
    return any(kw in notes_lower or kw in doc_lower for kw in keywords)

class TransactionRiskAgent:
    """Specialist evaluating immediate transaction features against core anti-fraud rules."""
    
    @staticmethod
    def process_task(db: Session, tx: Any) -> Dict[str, Any]:
        violations = []
        evidence_logs = []
        structured_evidences = []
        
        # Rule 1: High transaction amount check
        if tx.amount > 500000.0:
            violations.append("LARGE_TICKET_AMOUNT")
            evidence_logs.append("[LARGE_TICKET_AMOUNT] Transaction amount exceeds maximum soft limit of INR 500,000.")
            structured_evidences.append({
                "category": "rule_violation",
                "severity": "high",
                "value": f"INR {tx.amount}",
                "description": "Transaction amount exceeds maximum soft limit of INR 500,000.",
                "source": "Transaction Risk Agent",
                "confidence": 1.0,
                "supporting_entity": tx.transaction_id
            })
            
        # Rule 2: Country mismatch check (Card origin vs Billing)
        if tx.billing_country != tx.card_country:
            violations.append("GEOGRAPHIC_MISMATCH")
            evidence_logs.append(f"[GEOGRAPHIC_MISMATCH] Billing country '{tx.billing_country}' does not match card country '{tx.card_country}'.")
            structured_evidences.append({
                "category": "geographic_mismatch",
                "severity": "medium",
                "value": f"Billing: {tx.billing_country} vs Card: {tx.card_country}",
                "description": f"Billing country '{tx.billing_country}' does not match card country '{tx.card_country}'.",
                "source": "Transaction Risk Agent",
                "confidence": 1.0,
                "supporting_entity": tx.transaction_id
            })
            
        # Rule 3: High amount Card-Not-Present transaction
        if not tx.card_present and tx.amount > 50000.0:
            violations.append("HIGH_VALUE_CNP")
            evidence_logs.append("[HIGH_VALUE_CNP] Card-Not-Present transaction exceeds high-risk threshold of INR 50,000.")
            structured_evidences.append({
                "category": "amount_deviation",
                "severity": "high",
                "value": f"INR {tx.amount} (CNP)",
                "description": "Card-Not-Present transaction exceeds high-risk threshold of INR 50,000.",
                "source": "Transaction Risk Agent",
                "confidence": 1.0,
                "supporting_entity": tx.transaction_id
            })

        # Calculate rule score: 33.3 per violation, capped at 100.0
        rule_score = min(100.0, len(violations) * 33.3)
        

        # Check if merchant submitted resolving evidence
        submissions = []
        if db is not None:
            from app.models.merchant_submission import MerchantSubmission
            submissions = db.query(MerchantSubmission).filter(MerchantSubmission.transaction_id == tx.id).all()
        
        if submissions:
            fully_addressed = any(submission_addresses_category(s, "rules") for s in submissions)
            if fully_addressed:
                rule_score = 0.0
                outcome = "Transaction profile reviewed. Violations resolved via merchant submitted documentation."
                evidence = "Heuristic rule violations resolved. Merchant submitted verification notes."
                structured_evidences = []
            else:
                rule_score = rule_score * 0.80
                outcome = (
                    f"Transaction profiled. Violations found: {len(violations)}. "
                    f"Merchant submitted generic/insufficient evidence. Applied partial 20% risk reduction."
                )
                evidence = " | ".join(evidence_logs) if evidence_logs else "No heuristic rule violations detected."
                evidence += " (Partial 20% reduction applied: submission did not address heuristic rules)."
        else:
            outcome = (
                f"Transaction profiled. Violations found: {len(violations)}. "
                f"Rule status evaluates at {rule_score:.1f}% risk severity."
            )
            evidence = " | ".join(evidence_logs) if evidence_logs else "No heuristic rule violations detected."
        
        return {
            "agent_name": "Transaction Risk Agent",
            "score": rule_score,
            "outcome": outcome,
            "evidence": evidence,
            "evidences": structured_evidences
        }


class BehavioralRiskAgent:
    """Specialist evaluating card velocities, spending averages, and time-drift patterns."""
    
    @staticmethod
    def process_task(db: Session, tx: Any) -> Dict[str, Any]:
        violations = []
        evidence_logs = []
        structured_evidences = []
        
        # Rule 1: Instant velocity check in the last 1 hour
        one_hour_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        recent_count = db.query(Transaction).filter(
            Transaction.user_id == tx.user_id,
            Transaction.timestamp >= one_hour_ago
        ).count()
        
        if recent_count > 5:
            violations.append("VELOCITY_SPIKE_1H")
            evidence_logs.append(f"High velocity transaction rate detected: {recent_count} payments in the last hour.")
            structured_evidences.append({
                "category": "velocity",
                "severity": "high",
                "value": f"{recent_count} payments in 1 hour",
                "description": f"High velocity transaction rate detected: {recent_count} payments in the last hour.",
                "source": "Behavioral Risk Agent",
                "confidence": 1.0,
                "supporting_entity": tx.user_id
            })
            
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
                structured_evidences.append({
                    "category": "amount_deviation",
                    "severity": "high",
                    "value": f"INR {tx.amount} vs avg INR {avg_val:.2f}",
                    "description": f"Amount INR {tx.amount} is 3x greater than customer historical average of INR {avg_val:.2f}.",
                    "source": "Behavioral Risk Agent",
                    "confidence": 1.0,
                    "supporting_entity": tx.user_id
                })
        else:
            # First transaction check: moderate risk warning for unprofiled users on large sums
            if tx.amount > 100000.0:
                violations.append("UNPROFILED_LARGE_SUM")
                evidence_logs.append("First transaction registered for user exceeds baseline limit of INR 100,000.")
                structured_evidences.append({
                    "category": "rule_violation",
                    "severity": "medium",
                    "value": f"INR {tx.amount}",
                    "description": "First transaction registered for user exceeds baseline limit of INR 100,000.",
                    "source": "Behavioral Risk Agent",
                    "confidence": 0.8,
                    "supporting_entity": tx.user_id
                })

        behavioral_score = min(100.0, len(violations) * 50.0)
        
        # Check if merchant submitted resolving evidence
        submissions = []
        if db is not None:
            from app.models.merchant_submission import MerchantSubmission
            submissions = db.query(MerchantSubmission).filter(MerchantSubmission.transaction_id == tx.id).all()
        
        if submissions:
            fully_addressed = any(submission_addresses_category(s, "velocity") for s in submissions)
            if fully_addressed:
                behavioral_score = 0.0
                outcome = "Behavioral velocity reviewed. Anomalies resolved via merchant verification."
                evidence = "Velocity rules resolved. Merchant submitted verification notes."
                structured_evidences = []
            else:
                behavioral_score = behavioral_score * 0.80
                outcome = (
                    f"Behavioral velocity analyzed. Detected anomalies: {len(violations)}. "
                    f"Merchant submitted generic/insufficient evidence. Applied partial 20% risk reduction."
                )
                evidence = " | ".join(evidence_logs) if evidence_logs else "Customer spending velocity within normal historical bounds."
                evidence += " (Partial 20% reduction applied: submission did not address velocity patterns)."
        else:
            outcome = f"Behavioral velocity analyzed. Detected anomalies: {len(violations)}."
            evidence = " | ".join(evidence_logs) if evidence_logs else "Customer spending velocity within normal historical bounds."
            
        return {
            "agent_name": "Behavioral Risk Agent",
            "score": behavioral_score,
            "outcome": outcome,
            "evidence": evidence,
            "evidences": structured_evidences
        }


class FraudInvestigationAgent:
    """Specialist performing graph walking across the payment graph database to uncover shared devices/IP loops."""
    
    @staticmethod
    def process_task(db: Session, tx: Any) -> Dict[str, Any]:
        # 1. Initialize network and build from current state of edges in DB
        graph = PaymentNetworkGraph()
        graph.build_from_db(db)
        
        # 2. Add current transaction nodes and edges to graph in-memory for testing
        graph.add_transaction_nodes_and_edges(tx)
        
        # 3. Walk relationships
        degrees_of_sharing, shared_entities, paths = graph.walk_shared_relationships(str(tx.user_id), "User")
        
        # Compute graph score: 33.3 per degree of sharing, capped at 100.0
        graph_score = min(100.0, degrees_of_sharing * 33.3)
        
        structured_evidences = []
        if degrees_of_sharing > 0:
            outcome = f"Relational walking detected link overlaps. Overlapping accounts: {degrees_of_sharing}."
            evidence = " | ".join(shared_entities)
            for path in paths:
                cat = "device_relationship" if "Device" in path.get("type", "") else "account_relationship"
                # Safely split path values — guard against None or missing ':'
                node_raw = path.get("node") or ""
                linked_raw = path.get("linked_account") or ""
                node_label = node_raw.split(":", 1)[-1] if ":" in node_raw else node_raw
                linked_label = linked_raw.split(":", 1)[-1] if ":" in linked_raw else linked_raw
                path_type = path.get("type") or "entity"
                structured_evidences.append({
                    "category": cat,
                    "severity": "high",
                    "value": f"Shared {path_type}: {node_raw}",
                    "description": f"Customer account overlaps with user account '{linked_label}' via shared {path_type.lower()} {node_label}.",
                    "source": "Fraud Investigation Agent",
                    "confidence": 1.0,
                    "supporting_entity": node_raw
                })
        else:
            outcome = "Graph walking completed. Node is isolated from other registered entities."
            evidence = "No shared device fingerprints or IP addresses linked to external customer accounts."
            
        # Check if merchant submitted resolving evidence
        submissions = []
        if db is not None:
            from app.models.merchant_submission import MerchantSubmission
            submissions = db.query(MerchantSubmission).filter(MerchantSubmission.transaction_id == tx.id).all()
        
        if submissions:
            fully_addressed = any(submission_addresses_category(s, "graph") for s in submissions)
            if fully_addressed:
                graph_score = 0.0
                outcome = "Graph walk overlaps analyzed and resolved via merchant device authorization verification."
                evidence = "Graph overlap rules resolved. Merchant submitted verification notes."
                structured_evidences = []
            else:
                graph_score = graph_score * 0.80
                outcome = "Graph walk overlaps analyzed. Merchant submitted generic/insufficient evidence. Applied partial 20% risk reduction."
                evidence = " | ".join(shared_entities) if shared_entities else "No shared device fingerprints or IP addresses linked to external customer accounts."
                evidence += " (Partial 20% reduction applied: submission did not address graph relationships)."
        else:
            outcome = f"Relational walking detected link overlaps. Overlapping accounts: {degrees_of_sharing}." if degrees_of_sharing > 0 else "Graph walking completed. Node is isolated from other registered entities."
            evidence = " | ".join(shared_entities) if shared_entities else "No shared device fingerprints or IP addresses linked to external customer accounts."
            
        return {
            "agent_name": "Fraud Investigation Agent",
            "score": graph_score,
            "outcome": outcome,
            "evidence": evidence,
            "paths": paths,
            "evidences": structured_evidences
        }


class PolicyRAGAgent:
    """Specialist retrieving compliance policy vector chunks and mapping citations."""
    
    @staticmethod
    def process_task(db: Session, tx: Any) -> Dict[str, Any]:
        # Construct search query for RAG
        search_query = f"{tx.merchant_category} merchant categories card-not-present limitations and compliance verification"
        
        # Query policy chunks
        matching_chunks = hybrid_retrieve_policy_chunks(db, search_query, limit=2)
        
        policy_score = 0.0
        evidence_logs = []
        citations = []
        structured_evidences = []
        
        if matching_chunks:
            for chunk, score in matching_chunks:
                evidence_logs.append(str(chunk.content)[:200] + "...")
                citations.append(f"[Source: {chunk.filename}, Index: {chunk.chunk_index}]")
                # If policy text contains risk keywords matching the current transaction's category
                is_trigger = False
                if "block" in chunk.content.lower() or "requires verification" in chunk.content.lower():
                    if tx.amount > 50000.0:
                        policy_score = 100.0 # Force policy compliance review
                        is_trigger = True
                
                structured_evidences.append({
                    "category": "policy_match",
                    "severity": "high" if is_trigger else "medium",
                    "value": f"Similarity: {score:.1f}%",
                    "description": f"Retrieved compliance chunk: \"{chunk.content[:220]}...\"",
                    "source": "Policy Agent",
                    "confidence": score / 100.0,
                    "policy_reference": f"policies/{chunk.filename}#chunk_{chunk.chunk_index}"
                })
                        
            outcome = f"Compliance policies verified. Citations resolved: {len(citations)}."
            evidence = " | ".join(evidence_logs) + " " + " ".join(citations)
        else:
            outcome = "No applicable compliance guidelines resolved in RAG registry."
            evidence = "No active regulatory rules breached. Compliance policy search returned zero matches."
            
        # Check if merchant submitted resolving evidence
        submissions = []
        if db is not None:
            from app.models.merchant_submission import MerchantSubmission
            submissions = db.query(MerchantSubmission).filter(MerchantSubmission.transaction_id == tx.id).all()
        
        if submissions:
            fully_addressed = any(submission_addresses_category(s, "policy") for s in submissions)
            if fully_addressed:
                policy_score = 0.0
                outcome = "Compliance policies verified. All required documentation verified."
                evidence = "Policy compliance verified. Merchant submitted verification notes."
                for se in structured_evidences:
                    se["severity"] = "low"
            else:
                policy_score = policy_score * 0.80
                outcome = "Compliance policies analyzed. Merchant submitted generic/insufficient evidence. Applied partial 20% risk reduction."
                evidence = " | ".join(evidence_logs) + " " + " ".join(citations) if evidence_logs else "No active regulatory rules breached."
                evidence += " (Partial 20% reduction applied: submission did not address policy guidelines)."
        else:
            outcome = f"Compliance policies verified. Citations resolved: {len(citations)}." if citations else "No applicable compliance guidelines resolved in RAG registry."
            evidence = " | ".join(evidence_logs) + " " + " ".join(citations) if evidence_logs else "No active regulatory rules breached. Compliance policy search returned zero matches."
                
        return {
            "agent_name": "Policy Agent",
            "score": policy_score,
            "outcome": outcome,
            "evidence": evidence,
            "citations": citations,
            "evidences": structured_evidences
        }


class DecisionAgent:
    """Specialist aggregating metrics, running composite scoring formula, and assigning risk label."""
    
    @staticmethod
    def process_task(
        db: Optional[Session], 
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
            "score": composite_score,
            "classification": classification,
            "outcome": outcome,
            "evidence": evidence
        }


class ActionAgent:
    """Specialist routing final status and initiating escalations or auto-approvals."""
    
    @staticmethod
    def process_task(db: Session, tx: Any, classification: str, score: float) -> Dict[str, Any]:
        old_status = tx.status
        
        # Threshold Routing:
        # - LOW risk (Score < 40.0, Safe classification) -> APPROVE (Automatic approval)
        # - MEDIUM risk (Score 40.0 - 74.9, Suspicious classification) -> MONITOR (Release payment but alert)
        # - HIGH risk (Score >= 75.0, High Risk classification) -> ESCALATE / HOLD (Suspend payment for manual review)
        if classification == "Safe":
            new_status = "Approved"
            action = "APPROVE"
            explanation = "Transaction risk score is low. Automatic approval processed."
        elif classification == "Suspicious":
            new_status = "Approved" # System warns but releases
            action = "MONITOR"
            explanation = "Transaction flagged as suspicious. System released payment but enqueued alert."
        else: # High Risk
            new_status = "Escalated" # Hold payment
            action = "ESCALATE"
            explanation = "High risk indicators. Transaction suspended, pending manual analyst review."
            
        # Update transaction status and score in DB
        tx.status = new_status
        tx.risk_score = score
        db.add(tx)
        db.flush()
        
        outcome = f"Transaction status transitioned from '{old_status}' to '{new_status}' via action '{action}'."
        
        return {
            "agent_name": "Action Agent",
            "action": action,
            "status": new_status,
            "outcome": outcome,
            "evidence": explanation,
            "evidences": []  # ActionAgent does not produce structured evidence items
        }
