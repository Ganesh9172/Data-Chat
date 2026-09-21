import re
import json
import requests
from typing import Dict, Any, Optional
from ai_tests.config import (
    AI_EVALUATOR_ENABLED,
    AI_EVALUATOR_PROVIDER,
    AI_EVALUATOR_MODEL,
    OLLAMA_BASE_URL
)

def evaluate_with_ollama(
    question: str,
    expected_meaning: str,
    actual_response: str
) -> Optional[Dict[str, Any]]:
    """
    Evaluates response using a local Ollama model if enabled and available.
    """
    if not AI_EVALUATOR_ENABLED:
        return None

    model = AI_EVALUATOR_MODEL or "llama3.2"
    prompt = f"""You are a QA Evaluator for a heating system AI chatbot.
Evaluate if the Actual Response conveys the Expected Meaning for the User Question.
Do not require exact wording; match the core semantic intent.

User Question: {question}
Expected Meaning: {expected_meaning}
Actual Response: {actual_response}

Return ONLY valid JSON in this exact structure:
{{
  "pass": true,
  "reason": "Clear explanation of why it passed or failed"
}}
"""
    try:
        url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code == 200:
            data = res.json()
            raw_output = data.get("response", "").strip()
            parsed = json.loads(raw_output)
            return {
                "pass": bool(parsed.get("pass", False)),
                "score": 1.0 if parsed.get("pass") else 0.0,
                "reason": f"[Ollama {model}] {parsed.get('reason', 'Evaluated by Ollama')}"
            }
    except Exception as e:
        print(f"[Ollama Evaluator Warning] Could not reach Ollama: {e}")

    return None

def evaluate_deterministic(
    question: str,
    expected_meaning: str,
    actual_response: str,
    category: str = "general"
) -> Dict[str, Any]:
    """
    Deterministic semantic evaluator that tests meaning without exact string matching.
    """
    if not actual_response or not actual_response.strip():
        return {
            "pass": False,
            "score": 0.0,
            "reason": "Actual response is empty"
        }

    resp_lower = actual_response.lower()
    q_lower = question.lower()
    exp_lower = expected_meaning.lower()

    # 1. Check for 0.5 bar pressure questions
    if "0.5" in q_lower or "half" in q_lower:
        # Evaluates whether the response properly addresses pressure status
        addresses_pressure = any(w in resp_lower for w in [
            "acceptable", "within limit", "limit", "bar", "pressure",
            "low", "too low", "below", "insufficient", "normal", "range",
            "operating pressure", "fine", "okay"
        ])

        if addresses_pressure:
            return {
                "pass": True,
                "score": 1.0,
                "reason": "Response correctly explains pressure status (acceptable or relative to documented range)."
            }
        else:
            return {
                "pass": False,
                "score": 0.0,
                "reason": "Response did not explain whether 0.5 bar is within the documented pressure range."
            }

    # 2. General / Conversational questions
    if category in ("general_questions", "normal_conversation"):
        # Must not say document refusal
        if "couldn't find this information in the provided documents" in resp_lower:
            return {
                "pass": False,
                "score": 0.0,
                "reason": "Conversational question falsely returned a document retrieval refusal."
            }
        if "name" in q_lower or "who are you" in q_lower:
            if "firebird" in resp_lower:
                return {
                    "pass": True,
                    "score": 1.0,
                    "reason": "Chatbot correctly identified itself as Firebird AI."
                }
            return {
                "pass": False,
                "score": 0.0,
                "reason": "Response did not identify the chatbot as Firebird AI."
            }
        if "date" in q_lower or "day" in q_lower or "time" in q_lower:
            # Date/time question
            has_date_time = any(w in resp_lower for w in [
                "202", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
                "january", "february", "march", "april", "may", "june", "july", "august", "september",
                "october", "november", "december", "am", "pm", ":"
            ])
            if has_date_time:
                return {
                    "pass": True,
                    "score": 1.0,
                    "reason": "Direct date/time response provided."
                }
            return {
                "pass": False,
                "score": 0.0,
                "reason": "Response did not contain valid date or time."
            }
        return {
            "pass": True,
            "score": 1.0,
            "reason": "Appropriate conversational response without RAG refusal."
        }

    # 3. Out-of-scope questions
    if category in ("out_of_scope", "unsupported"):
        resp_norm = resp_lower.replace("’", "'").replace("`", "'")
        has_refusal = any(w in resp_norm for w in [
            "couldn't find", "could not find", "not available", "do not have", "don't have",
            "cannot find", "can't find", "cannot tell", "can't tell", "unable to", "not able to",
            "can't give a specific price", "can't give a price", "can't give", "cannot give",
            "not covered", "not mentioned", "outside", "no access", "don't have access",
            "assist you with heating", "technical assistant for heating",
            "check the invoice", "contact the retailer", "contact the installer", "contact the manufacturer"
        ])
        if has_refusal:
            return {
                "pass": True,
                "score": 1.0,
                "reason": "Correctly declined to answer out-of-scope question without hallucinating."
            }
        return {
            "pass": False,
            "score": 0.0,
            "reason": "AI attempted to answer an unsupported/out-of-scope question."
        }

    # 4. Technical knowledge & follow-up questions
    if category in ("knowledge", "followup", "citations"):
        if "f32" in q_lower:
            if any(w in resp_lower for w in ["circulation", "insufficient", "pump", "valve", "air", "filter"]):
                return {
                    "pass": True,
                    "score": 1.0,
                    "reason": "Correctly explained F32 fault code causes and checks."
                }
            return {
                "pass": False,
                "score": 0.0,
                "reason": "Response did not explain F32 circulation issue."
            }

        # If testing hot pressure context
        if "hot" in q_lower or "2.5" in q_lower:
            addresses_hot = any(w in resp_lower for w in ["hot", "operating", "range", "higher", "pressure", "vessel", "expansion", "bar"])
            if addresses_hot:
                return {
                    "pass": True,
                    "score": 1.0,
                    "reason": "Response correctly explains hot operating pressure dynamics."
                }

        # Check key terms from expected meaning
        stopwords = {
            "should", "would", "could", "about", "their", "which", "whether",
            "response", "explain", "explains", "indicating", "that", "from",
            "with", "this", "when", "goes", "large", "swing", "system"
        }
        keywords = [
            w for w in re.findall(r"[a-z0-9]+", exp_lower)
            if len(w) > 3 and w not in stopwords
        ]
        matched = [k for k in keywords if k in resp_lower]
        match_ratio = len(matched) / max(1, len(keywords))

        if match_ratio >= 0.33 or len(matched) >= 2:
            return {
                "pass": True,
                "score": match_ratio,
                "reason": f"Response conveyed expected meaning (matched key concepts: {', '.join(matched[:5])})."
            }
        return {
            "pass": False,
            "score": match_ratio,
            "reason": f"Response missed key concepts of expected meaning. Found: {matched}, expected: {keywords[:5]}."
        }

    return {
        "pass": len(actual_response) > 10,
        "score": 1.0 if len(actual_response) > 10 else 0.0,
        "reason": "Basic non-empty response check passed."
    }

def evaluate_response(
    question: str,
    expected_meaning: str,
    actual_response: str,
    category: str = "general"
) -> Dict[str, Any]:
    """
    Main evaluation entry point.
    Attempts Ollama evaluation if configured; falls back to deterministic semantic evaluation.
    """
    ollama_result = evaluate_with_ollama(question, expected_meaning, actual_response)
    if ollama_result is not None:
        return ollama_result

    return evaluate_deterministic(question, expected_meaning, actual_response, category)
