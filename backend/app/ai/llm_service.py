import re
import httpx
from app.core.config import settings
from app.core.logging import logger

class LLMService:
    """Zero-dependency service to interface with LLMs (Google Gemini API / Mock fallback)."""
    
    @staticmethod
    def generate_response(prompt: str, system_prompt: str = "") -> str:
        provider = settings.LLM_PROVIDER
        
        if provider == "mock" or not settings.GEMINI_API_KEY:
            logger.info("using_mock_llm_service_response")
            return _generate_mock_explanation(prompt)

        try:
            # Construct standard Gemini API call using httpx
            api_key = settings.GEMINI_API_KEY
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            
            # Combine system prompt with prompt if supported
            contents = []
            if system_prompt:
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"System Guidelines: {system_prompt}\n\nUser Request: {prompt}"}]
                })
            else:
                contents.append({
                    "role": "user",
                    "parts": [{"text": prompt}]
                })

            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 1000
                }
            }

            headers = {"Content-Type": "application/json"}
            
            response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                res_data = response.json()
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            else:
                logger.error("gemini_api_returned_error", status_code=response.status_code, body=response.text)
                return _generate_mock_explanation(prompt)
                
        except Exception as e:
            logger.error("llm_api_call_failed_falling_back", error=str(e))
            return _generate_mock_explanation(prompt)


def _generate_mock_explanation(prompt: str) -> str:
    """Synthesizes a structured, evidence-driven markdown explanation from risk metrics and agent findings."""
    # 1. Parse prompt variables using regular expressions
    tx_id_match = re.search(r"Transaction ID:\s*(\S+)", prompt, re.IGNORECASE)
    tx_id = tx_id_match.group(1) if tx_id_match else "Unknown"
    
    user_id_match = re.search(r"User ID:\s*(\S+)", prompt, re.IGNORECASE)
    user_id = user_id_match.group(1) if user_id_match else "Unknown"
    
    amount_match = re.search(r"Amount:\s*([^\n]+)", prompt, re.IGNORECASE)
    amount = amount_match.group(1).strip() if amount_match else "Unknown"
    
    score_match = re.search(r"Calculated Score:\s*([\d\.]+)%", prompt, re.IGNORECASE)
    score = score_match.group(1) if score_match else "0.0"
    
    class_match = re.search(r"Risk Classification:\s*([a-zA-Z\s]+)", prompt, re.IGNORECASE)
    classification = class_match.group(1).strip() if class_match else "Safe"
    
    # Extract agent evidence inputs
    tx_rules = "No flags detected."
    tx_rules_match = re.search(r"- Transaction Rules:\s*([^\n]+)", prompt, re.IGNORECASE)
    if tx_rules_match:
        tx_rules = tx_rules_match.group(1).strip()
        
    behavior_history = "No velocity spike or ticket size deviation."
    behavior_history_match = re.search(r"- Behavior History:\s*([^\n]+)", prompt, re.IGNORECASE)
    if behavior_history_match:
        behavior_history = behavior_history_match.group(1).strip()
        
    network_graph = "Isolated account, no device or IP sharing overlaps."
    network_graph_match = re.search(r"- Network Graph walks:\s*([^\n]+)", prompt, re.IGNORECASE)
    if network_graph_match:
        network_graph = network_graph_match.group(1).strip()
        
    policy_evidence = "No policy violations found."
    policy_evidence_match = re.search(r"- Compliance Policy:\s*([^\n]+)", prompt, re.IGNORECASE)
    if policy_evidence_match:
        policy_evidence = policy_evidence_match.group(1).strip()

    # Determine recommended action based on classification
    if classification == "High Risk":
        action = "ESCALATE (Suspends transaction state pending manual review)"
    elif classification == "Suspicious":
        action = "MONITOR (Permits processing but enqueues review alert)"
    else:
        action = "APPROVE (Automatic approval processed)"

    # 2. Build structured markdown briefing
    return (
        f"### Risk Summary\n"
        f"Transaction {tx_id} for user {user_id} valued at {amount} evaluates as **{classification}** "
        f"with a deterministic risk score of {score}%.\n\n"
        f"### Key Factors\n"
        f"- **Transaction Rules:** {tx_rules}\n"
        f"- **Behavioral History:** {behavior_history}\n"
        f"- **Network Relationships:** {network_graph}\n\n"
        f"### Policy Evidence\n"
        f"{policy_evidence}\n\n"
        f"### Recommended Action\n"
        f"{action}"
    )

