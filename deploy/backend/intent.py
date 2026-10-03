import os
import re
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv

# Standardized Router Categories (per Specification)
INTENT_NORMAL_CONVERSATION = "NORMAL_CONVERSATION"
INTENT_GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"
INTENT_CURRENT_TIME_DATE = "CURRENT_TIME_DATE"
INTENT_TECHNICAL_RAG_QUESTION = "TECHNICAL_RAG_QUESTION"
INTENT_KNOWLEDGE_CORRECTION = "KNOWLEDGE_CORRECTION"
INTENT_KNOWLEDGE_UPDATE = "KNOWLEDGE_UPDATE"
INTENT_UPDATE_CONFIRMATION = "UPDATE_CONFIRMATION"
INTENT_UPDATE_CANCELLATION = "UPDATE_CANCELLATION"
INTENT_FOLLOW_UP_QUESTION = "FOLLOW_UP_QUESTION"

# Aliases for backwards compatibility with existing tests
INTENT_TECHNICAL_QUESTION = INTENT_TECHNICAL_RAG_QUESTION
INTENT_FOLLOW_UP = INTENT_FOLLOW_UP_QUESTION
INTENT_CLARIFICATION = INTENT_NORMAL_CONVERSATION
INTENT_UNKNOWN = "UNKNOWN"

ALL_INTENTS = [
    INTENT_NORMAL_CONVERSATION,
    INTENT_GENERAL_KNOWLEDGE,
    INTENT_CURRENT_TIME_DATE,
    INTENT_TECHNICAL_RAG_QUESTION,
    INTENT_KNOWLEDGE_CORRECTION,
    INTENT_KNOWLEDGE_UPDATE,
    INTENT_UPDATE_CONFIRMATION,
    INTENT_UPDATE_CANCELLATION,
    INTENT_FOLLOW_UP_QUESTION,
    INTENT_UNKNOWN
]

INTENT_DETECTION_SYSTEM_PROMPT = """You are the Request Router and Intent Classification Engine for Firebird AI.

Classify the incoming user message in light of recent conversation context and any active pending update into EXACTLY ONE of the following 9 categories:

1. NORMAL_CONVERSATION:
   Greetings ("Hi", "Hello", "Hey", "Good morning"), polite inquiries ("How are you?"), gratitude ("Thank you", "Thanks"), courtesy ("You're welcome"), fillers ("Okay", "Great", "Nice"), chatbot identity questions ("What is your name?", "Who are you?", "What can you do?"), or requests to explain or clarify a previous answer conversationally ("Can you explain that again?", "Can you explain it?").
   Do NOT route to RAG.

2. GENERAL_KNOWLEDGE:
   General or conceptual questions that do NOT ask about the heating/boiler/plumbing PDF knowledge base.
   Examples: "What is AI?", "What is RAG?", "What does AI mean?", "How can you help me?", "What can you help me with?", "How do I use this chatbot?".
   Do NOT route to RAG.

3. CURRENT_TIME_DATE:
   Questions about today's date, day of week, or current time.
   Examples: "What is the date today?", "What date is it today?", "What day is today?", "What is today's date?", "What time is it?", "What day is it?", "What is the current date?".
   Do NOT route to RAG.

4. TECHNICAL_RAG_QUESTION:
   Questions about hydronic heating systems, boilers, water pressure, temperatures (flow/return/delta-T), radiators, circulation pumps, leaks, and fault codes (e.g. F32) that must be answered from the PDF technical documents.
   Examples: "What is F32?", "What causes low water pressure?", "What causes air noise inside a hydronic heating system?", "Why is my radiator cold?", "What should the cold pressure be?", "What causes pressure to rise when heating?".
   Route to RAG.

5. KNOWLEDGE_CORRECTION:
   The user indicates that the previous answer or document information is wrong/incorrect, or directly provides a corrected value.
   Examples: "It's incorrect.", "That's incorrect.", "That's wrong.", "Your answer is wrong.", "The previous answer is incorrect.", "The pressure should be 1.2 bar.", "Actually, the correct value is 1.2 bar.".
   Do NOT route to RAG.

6. KNOWLEDGE_UPDATE:
   The user expresses intent to update or change information in the knowledge base.
   Examples: "I want to update a value.", "I want to update this information.", "I need to correct something.", "Update this information.", "I want to update the pressure.".
   Do NOT route to RAG.

7. UPDATE_CONFIRMATION:
   The user is approving or saying yes to save a pending knowledge update (e.g., "Yes", "Save it", "Please save that", "Confirm").
   ONLY choose this if there is an active pending update awaiting confirmation! If no update is pending, "Yes" is NORMAL_CONVERSATION.

8. UPDATE_CANCELLATION:
   The user is cancelling or rejecting an active pending update (e.g., "No", "Cancel", "Don't save it", "Never mind", "No, don't change it").
   ONLY choose this if an update is pending!

9. FOLLOW_UP_QUESTION:
   A technical continuation directly referencing the previous topic using pronouns or shorthand.
   Examples: Following "What is F32?", user asks "Why does that happen?"; Following "What is normal cold pressure?", user asks "What about the pressure when hot?".

CRITICAL RULES:
- NEVER invent values. Only extract numerical/textual values explicitly written by the user.
- "What causes pressure to change?" is a TECHNICAL_RAG_QUESTION, NOT an update.
- "Can you correct my understanding of pressure?" is NORMAL_CONVERSATION or GENERAL_KNOWLEDGE, NOT an update.

Respond with ONLY valid JSON:
{
  "intent": "<ONE_OF_THE_9_CATEGORIES>",
  "topic": "<topic or field if applicable, e.g. 'pressure', 'F32', 'radiator', or null>",
  "extracted_value": "<exact string value explicitly provided by user, e.g. '1.2 bar', or null>",
  "resolved_query": "<resolved standalone question for retrieval if follow-up, or null>",
  "explanation_request": <true if user wants previous answer explained/clarified, false otherwise>
}
"""

def extract_explicit_value(text: str) -> Optional[str]:
    """
    Extracts numerical or measurement values explicitly provided by the user in their text.
    NEVER invents or defaults to any value. Returns None if no explicit value is present.
    """
    m = re.search(r"([0-9]+(?:\.[0-9]+)?\s*(?:[-–—to]\s*[0-9]+(?:\.[0-9]+)?)?\s*(?:bar|°c|c|deg c))\b", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    m = re.search(r"(?:should be|is|value is|range is|change it to|set to|use|to)\s+([0-9]+(?:\.[0-9]+)?(?:\s*[-–—to]\s*[0-9]+(?:\.[0-9]+)?)?\s*(?:bar|°c)?)", text, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        if re.search(r"[0-9]", val):
            return val

    clean_stripped = text.strip()
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?(?:\s*[-–—to]\s*[0-9]+(?:\.[0-9]+)?)?(?:\s*(?:bar|°c|c))?)$", clean_stripped, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return None

def normalize_value_unit(val: Optional[str], topic: Optional[str] = None) -> Optional[str]:
    """Appends appropriate unit if a bare number was provided."""
    if not val:
        return None
    val_clean = val.strip()
    if re.search(r"[0-9]", val_clean) and not re.search(r"(bar|°c|c|deg)", val_clean, re.IGNORECASE):
        if topic and any(t in topic.lower() for t in ["temp", "temperature", "celsius"]):
            return f"{val_clean}°C"
        return f"{val_clean} bar"
    return val_clean

def detect_topic_from_text_or_context(text: str, history: List[Dict[str, Any]]) -> Optional[str]:
    """Detects technical topic (e.g. pressure, temperature, fault code) from current or previous text."""
    combined = text.lower()
    if any(w in combined for w in ["pressure", "bar", "cold fill", "operating pressure"]):
        return "pressure"
    if any(w in combined for w in ["temperature", "delta-t", "delta t", "flow", "return", "70", "45", "°c"]):
        return "temperature"
    if any(w in combined for w in ["f32", "fault code", "error code"]):
        return "fault code F32"
    if any(w in combined for w in ["radiator", "cold radiator", "bleeding"]):
        return "radiator"
    if any(w in combined for w in ["air noise", "noise", "rushing"]):
        return "air noise"
    if any(w in combined for w in ["boiler", "pump", "circulator"]):
        return "boiler/pump"

    if history:
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                prev_text = msg.get("content", "").lower()
                if "f32" in prev_text or "insufficient circulation" in prev_text:
                    return "fault code F32"
                if "pressure" in prev_text or "bar" in prev_text:
                    return "pressure"
                if "temperature" in prev_text or "flow" in prev_text or "return" in prev_text:
                    return "temperature"
                if "radiator" in prev_text:
                    return "radiator"
                if "air noise" in prev_text or "noise" in prev_text:
                    return "air noise"
                break
    return None

def fast_heuristic_intent_analysis(
    message: str,
    history: List[Dict[str, Any]],
    pending_update: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    High-confidence deterministic parser for clear-cut intents.
    Returns structured analysis dict if confident, or None if deep LLM analysis is preferable.
    """
    msg_raw = message.strip()
    msg_lower = msg_raw.lower()
    cleaned_tokens = re.sub(r"[^\w\s]", "", msg_lower).strip()

    # -------------------------------------------------------------
    # 1. Date and Time Questions (Category: CURRENT_TIME_DATE)
    # -------------------------------------------------------------
    date_time_exact = {
        "what is the date today", "what date is it today", "what day is today", "what is todays date",
        "what time is it", "what day is it", "what is the current date", "current date", "current time",
        "tell me the date", "tell me the time", "what date is it", "date today", "today date",
        "whats today date", "whats todays date", "what is the time", "whats the time"
    }
    date_time_regex = [
        r"\bwhat\s+is\s+the\s+date\s+today\b",
        r"\bwhat\s+date\s+is\s+it\s+today\b",
        r"\bwhat\s+day\s+is\s+today\b",
        r"\bwhat\s+is\s+today'?s\s+date\b",
        r"\bwhat\s+time\s+is\s+it\b",
        r"\bwhat\s+day\s+is\s+it\b",
        r"\bwhat\s+is\s+the\s+current\s+date\b",
        r"\bwhat\s+is\s+the\s+current\s+time\b",
        r"\btoday'?s\s+date\b",
        r"\bwhat\s+date\s+is\s+it\b"
    ]
    if cleaned_tokens in date_time_exact or any(re.search(p, msg_lower) for p in date_time_regex):
        return {
            "intent": INTENT_CURRENT_TIME_DATE,
            "topic": "date_time",
            "extracted_value": None,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.99
        }

    # -------------------------------------------------------------
    # 2. General Knowledge / AI Concepts (Category: GENERAL_KNOWLEDGE)
    # -------------------------------------------------------------
    gen_exact = {
        "what is rag", "what is ai", "what does ai mean", "what does rag mean",
        "what can you help me with", "how can you help me", "how do i use this chatbot",
        "how to use this chatbot", "what is artificial intelligence"
    }
    gen_regex = [
        r"\bwhat\s+is\s+rag\b",
        r"\bwhat\s+does\s+rag\s+mean\b",
        r"\bwhat\s+is\s+ai\b",
        r"\bwhat\s+does\s+ai\s+mean\b",
        r"\bwhat\s+can\s+you\s+help\s+me\s+with\b",
        r"\bhow\s+can\s+you\s+help\s+me\b",
        r"\bhow\s+do\s+i\s+use\s+this\s+chatbot\b"
    ]
    if cleaned_tokens in gen_exact or any(re.search(p, msg_lower) for p in gen_regex):
        return {
            "intent": INTENT_GENERAL_KNOWLEDGE,
            "topic": "general",
            "extracted_value": None,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.99
        }

    # -------------------------------------------------------------
    # 3. Active Pending Update Confirmation / Cancellation
    # -------------------------------------------------------------
    has_active_pending = bool(pending_update and pending_update.get("active"))

    if has_active_pending:
        affirmative_patterns = [
            r"^(?:yes|yep|yeah|confirm|save|save it|do it|go ahead|approved|please save|please save that|please save it|yes please|yes save it|yes thats correct|thats right|yes thats the one|okay save it|ok save it)\b",
            r"\b(?:save (?:it|this|that)|confirm (?:it|this|that|update)|go ahead and save)\b"
        ]
        if any(re.search(pat, msg_lower) for pat in affirmative_patterns) or cleaned_tokens in {
            "yes", "yep", "yeah", "confirm", "save it", "save", "do it", "approved", "ok save", "sure",
            "please save", "yes please", "yes save it", "yes thats correct", "thats right", "yes thats the one",
            "please save that", "okay save it", "confirm update"
        }:
            return {
                "intent": INTENT_UPDATE_CONFIRMATION,
                "topic": pending_update.get("field") or pending_update.get("topic") or "pressure",
                "extracted_value": pending_update.get("corrected_information"),
                "resolved_query": None,
                "explanation_request": False,
                "confidence": 0.99
            }

        cancellation_patterns = [
            r"^(?:no|nope|cancel|dont update|dont save|do not save|forget it|leave it as it is|i changed my mind|never mind|stop|abort|discard|no thanks|no dont change it|dont change it|actually never mind)\b",
            r"\b(?:never mind|dont change (?:it|that)|leave it (?:alone|as is|as it is))\b"
        ]
        if any(re.search(pat, msg_lower) for pat in cancellation_patterns) or cleaned_tokens in {
            "no", "cancel", "dont save", "do not save", "never mind", "stop", "abort", "discard",
            "no thanks", "dont update it", "dont save it", "forget it", "leave it as it is",
            "i changed my mind", "no dont change it", "actually never mind dont change it"
        }:
            return {
                "intent": INTENT_UPDATE_CANCELLATION,
                "topic": pending_update.get("field") or pending_update.get("topic"),
                "extracted_value": None,
                "resolved_query": None,
                "explanation_request": False,
                "confidence": 0.99
            }

    # If NO pending update: "yes", "ok", "no", "cancel" must NEVER trigger update confirmation/cancellation
    if not has_active_pending:
        if cleaned_tokens in {"yes", "yep", "yeah", "ok", "okay", "sure", "fine", "cool", "got it", "no", "cancel", "stop", "great", "nice", "youre welcome"}:
            return {
                "intent": INTENT_NORMAL_CONVERSATION,
                "topic": None,
                "extracted_value": None,
                "resolved_query": None,
                "explanation_request": False,
                "confidence": 0.95
            }

    # -------------------------------------------------------------
    # 4. Revert Knowledge Update
    # -------------------------------------------------------------
    if any(phrase in msg_lower for phrase in ["revert update", "revert correction", "revert the last update", "revert knowledge update", "undo update"]):
        return {
            "intent": INTENT_KNOWLEDGE_UPDATE,
            "topic": "revert",
            "extracted_value": None,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.98
        }

    # -------------------------------------------------------------
    # 5. Normal Greetings, Courtesy, Identity (NORMAL_CONVERSATION)
    # -------------------------------------------------------------
    if cleaned_tokens in {"hi", "hey", "howdy", "hello", "hello there", "hi there", "greetings", "good morning", "good afternoon", "good evening"}:
        return {
            "intent": INTENT_NORMAL_CONVERSATION,
            "topic": None,
            "extracted_value": None,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.99
        }

    if cleaned_tokens in {"how are you", "how are you doing", "hows it going", "how are things", "how do you do", "hope you are well"}:
        return {
            "intent": INTENT_NORMAL_CONVERSATION,
            "topic": None,
            "extracted_value": None,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.99
        }

    if cleaned_tokens in {"thank you", "thanks", "thanks a lot", "thank you so much", "thx", "many thanks", "appreciate it"}:
        return {
            "intent": INTENT_NORMAL_CONVERSATION,
            "topic": None,
            "extracted_value": None,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.99
        }

    identity_triggers = [
        "what is your name", "who are you", "what can you do", "whats your name", "what are you", "tell me your name"
    ]
    if any(trig in cleaned_tokens for trig in identity_triggers) or cleaned_tokens in identity_triggers:
        return {
            "intent": INTENT_NORMAL_CONVERSATION,
            "topic": "identity",
            "extracted_value": None,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.99
        }

    if cleaned_tokens in {"bye", "goodbye", "see you", "see ya", "have a good day", "have a nice day", "good night"}:
        return {
            "intent": INTENT_NORMAL_CONVERSATION,
            "topic": None,
            "extracted_value": None,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.99
        }

    # -------------------------------------------------------------
    # 6. Conversational Explanation / Clarification
    # -------------------------------------------------------------
    explanation_triggers = [
        "can you explain that again",
        "explain that again",
        "can you explain that",
        "can you explain it",
        "explain it",
        "what did you mean by that",
        "what do you mean by that",
        "what does that mean",
        "tell me more about this",
        "tell me more",
        "can you elaborate",
        "could you clarify that",
        "can you clarify that",
        "can you explain in simpler terms",
        "can you explain this"
    ]
    if any(trig in cleaned_tokens for trig in explanation_triggers) or cleaned_tokens in explanation_triggers:
        return {
            "intent": INTENT_NORMAL_CONVERSATION,
            "topic": detect_topic_from_text_or_context(msg_raw, history),
            "extracted_value": None,
            "resolved_query": None,
            "explanation_request": True,
            "confidence": 0.95
        }

    # -------------------------------------------------------------
    # 7. Follow-Up Questions (Category: FOLLOW_UP_QUESTION)
    # -------------------------------------------------------------
    topic = detect_topic_from_text_or_context(msg_raw, history)

    if re.search(r"\b(?:why\s+does\s+that\s+happen|why\s+does\s+this\s+happen)\b", msg_lower):
        resolved = f"Why does {topic or 'the fault or circulation issue'} happen?" if topic else msg_raw
        return {
            "intent": INTENT_FOLLOW_UP_QUESTION,
            "topic": topic,
            "extracted_value": None,
            "resolved_query": resolved,
            "explanation_request": False,
            "confidence": 0.98
        }

    if re.search(r"\b(?:what\s+about\s+the\s+pressure\s+when\s+hot|what\s+about\s+when\s+(?:the\s+system\s+is\s+)?hot|what\s+about\s+hot\s+pressure)\b", msg_lower):
        return {
            "intent": INTENT_FOLLOW_UP_QUESTION,
            "topic": "pressure",
            "extracted_value": None,
            "resolved_query": "What should the system water pressure be when the heating is hot or on?",
            "explanation_request": False,
            "confidence": 0.98
        }

    if re.search(r"\b(?:how\s+can\s+i\s+fix\s+that|how\s+to\s+fix\s+that|how\s+do\s+i\s+fix\s+this)\b", msg_lower):
        last_user_query = ""
        for m in reversed(history):
            if m.get("role") == "user":
                last_user_query = m.get("content", "")
                break
        resolved = f"How to fix {topic or 'the issue'} ({last_user_query})" if last_user_query else msg_raw
        return {
            "intent": INTENT_FOLLOW_UP_QUESTION,
            "topic": topic,
            "extracted_value": None,
            "resolved_query": resolved,
            "explanation_request": False,
            "confidence": 0.98
        }

    # -------------------------------------------------------------
    # 8. Distinguish Technical "change/correct" from Knowledge Update
    # -------------------------------------------------------------
    if re.search(r"\b(?:what\s+causes|why\s+does|how\s+does)\b.*\b(?:change|drop|rise|fluctuate)\b", msg_lower):
        return {
            "intent": INTENT_TECHNICAL_RAG_QUESTION,
            "topic": "pressure",
            "extracted_value": None,
            "resolved_query": msg_raw,
            "explanation_request": False,
            "confidence": 0.95
        }
    if re.search(r"\b(?:correct\s+my\s+understanding|am\s+i\s+understanding\s+correctly)\b", msg_lower):
        return {
            "intent": INTENT_NORMAL_CONVERSATION,
            "topic": topic,
            "extracted_value": None,
            "resolved_query": msg_raw,
            "explanation_request": False,
            "confidence": 0.95
        }

    # -------------------------------------------------------------
    # 9. Explicit Correction with Value (KNOWLEDGE_CORRECTION)
    # -------------------------------------------------------------
    extracted_val = extract_explicit_value(msg_raw)

    explicit_correction_phrases = [
        r"\b(?:should\s+be|correct\s+value\s+is|correct\s+reading\s+is|the\s+document\s+should\s+say|change\s+.*\s+to|replace\s+.*\s+with|actually\s+use|actually\s+the\s+correct\s+value\s+is)\b",
        r"\b(?:update\s+the\s+document\s*:\s*pressure\s+should\s+be)\b"
    ]
    if extracted_val and any(re.search(p, msg_lower) for p in explicit_correction_phrases):
        normalized_val = normalize_value_unit(extracted_val, topic)
        return {
            "intent": INTENT_KNOWLEDGE_CORRECTION,
            "topic": topic or "pressure",
            "extracted_value": normalized_val,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.98
        }

    # -------------------------------------------------------------
    # 10. Multi-Turn Response when Awaiting Correction / Value
    # -------------------------------------------------------------
    if has_active_pending and pending_update.get("status") in ["awaiting_correction", "awaiting_field_and_value"]:
        if extracted_val:
            normalized_val = normalize_value_unit(extracted_val, pending_update.get("topic") or topic or "pressure")
            return {
                "intent": INTENT_KNOWLEDGE_CORRECTION,
                "topic": pending_update.get("topic") or topic or "pressure",
                "extracted_value": normalized_val,
                "resolved_query": None,
                "explanation_request": False,
                "confidence": 0.98
            }
        if any(w in cleaned_tokens for w in ["pressure", "the pressure value", "temperature", "fault code", "f32"]):
            return {
                "intent": INTENT_KNOWLEDGE_UPDATE,
                "topic": topic or "pressure",
                "extracted_value": None,
                "resolved_query": None,
                "explanation_request": False,
                "confidence": 0.95
            }

    # -------------------------------------------------------------
    # 11. Vague or Incomplete Knowledge Update Requests
    # -------------------------------------------------------------
    vague_update_patterns = [
        r"\bi\s+want\s+to\s+update\s+a\s+value\b",
        r"\bi\s+want\s+to\s+update\s+(?:this\s+)?information\b",
        r"\bi\s+want\s+to\s+change\s+(?:a\s+value|something|this\s+value)\b",
        r"\bi\s+need\s+to\s+correct\s+(?:something|this\s+information)\b",
        r"\bi\s+want\s+to\s+make\s+a\s+correction\b",
        r"\bupdate\s+(?:this\s+information|the\s+knowledge\s*base)\b",
        r"\bcan\s+i\s+update\s+(?:this|the\s+knowledge\s*base)\b",
        r"\bcan\s+i\s+correct\s+this\b",
        r"\bi\s+need\s+to\s+change\s+something\b",
        r"\badd\s+(?:this\s+)?(?:information\s+)?to\s+the\s+knowledge\s*base\b",
        r"\bremember\s+this\s+correction\b"
    ]
    if any(re.search(p, msg_lower) for p in vague_update_patterns):
        field_specified = None
        if "pressure" in msg_lower:
            field_specified = "pressure"
        elif "temperature" in msg_lower:
            field_specified = "temperature"

        return {
            "intent": INTENT_KNOWLEDGE_UPDATE,
            "topic": field_specified or topic,
            "extracted_value": extracted_val,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.95
        }

    if re.search(r"\b(?:update|change)\s+(?:the\s+)?(?:pressure|temperature|value)\b", msg_lower) and not extracted_val:
        return {
            "intent": INTENT_KNOWLEDGE_UPDATE,
            "topic": topic or "pressure",
            "extracted_value": None,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.95
        }

    # -------------------------------------------------------------
    # 12. Natural Corrections (Pointing out error without value)
    # -------------------------------------------------------------
    natural_correction_patterns = [
        r"\b(?:it'?s|that'?s|this\s+is|that\s+is)\s+(?:incorrect|wrong|not\s+right|false|not\s+correct)\b",
        r"\b(?:that|this|the\s+previous|your|your\s+previous)\s+answer\s+(?:is\s+|isn'?t\s+|does\s*not\s+look\s+)(?:incorrect|wrong|not\s+right|right|correct)\b",
        r"\b(?:that|this|the\s+above)\s+information\s+is\s+(?:wrong|incorrect|outdated)\b",
        r"\bthe\s+value\s+in\s+the\s+document\s+is\s+wrong\b",
        r"\bthis\s+information\s+is\s+outdated\b",
        r"\b(?:that\s+)?doesn'?t\s+look\s+correct\b",
        r"\bi\s+don'?t\s+think\s+that'?s\s+right\b",
        r"\bactually,?\s+that'?s\s+not\s+correct\b",
        r"\bthat'?s\s+not\s+what\s+i\s+meant\b",
        r"\bthe\s+(?:number|value)\s+you\s+gave\s+me\s+doesn'?t\s+look\s+right\b",
        r"\bthe\s+pressure\s+you\s+mentioned\s+doesn'?t\s+look\s+right\b",
        r"\bi\s+think\s+that\s+information\s+is\s+wrong\b",
        r"\bi\s+think\s+the\s+value\s+you\s+gave\s+me\s+isn'?t\s+right\b",
        r"\bthe\s+number\s+above\s+seems\s+wrong\b",
        r"\bcan\s+we\s+change\s+that\b",
        r"\bi'?d\s+like\s+to\s+correct\s+what\s+we\s+just\s+discussed\b"
    ]
    if any(re.search(p, msg_lower) for p in natural_correction_patterns):
        return {
            "intent": INTENT_KNOWLEDGE_CORRECTION,
            "topic": topic or "pressure",
            "extracted_value": extracted_val,
            "resolved_query": None,
            "explanation_request": False,
            "confidence": 0.95
        }

    # -------------------------------------------------------------
    # 13. Technical Heating & Plumbing RAG Questions
    # -------------------------------------------------------------
    if (
        any(term in msg_lower for term in [
            "what is f32", "f32", "fault code", "causes low", "low water pressure", "low pressure",
            "flow temperature", "return temperature", "delta-t", "delta t",
            "service visit", "boiler pressure", "hot at the top", "cold at the top", "short cycling",
            "how does the boiler work", "troubleshoot", "air noise", "hydronic", "circulator pump",
            "expansion vessel", "pressure-relief", "discharge pipe", "bleeding",
            "cold pressure", "pressure to rise", "pressure rise",
            "idronics", "piping", "corrosion", "heating system", "fluid in a hydronic"
        ])
        or "radiator" in msg_lower
    ):
        return {
            "intent": INTENT_TECHNICAL_RAG_QUESTION,
            "topic": topic or "heating_system",
            "extracted_value": None,
            "resolved_query": msg_raw,
            "explanation_request": False,
            "confidence": 0.95
        }

    return None

def analyze_intent_with_llm(
    message: str,
    history: List[Dict[str, Any]],
    pending_update: Optional[Dict[str, Any]],
    client: Any,
    model: str = "openai/gpt-oss-120b"
) -> Optional[Dict[str, Any]]:
    """
    Uses the Groq / OpenAI LLM to classify natural language intent and extract context.
    """
    if not client:
        return None

    context_msgs = []
    recent_history = history[-4:]
    for m in recent_history:
        context_msgs.append(f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}")
    history_str = "\n".join(context_msgs) if context_msgs else "None (New conversation)"

    pending_str = "None"
    if pending_update and pending_update.get("active"):
        pending_str = f"Active Pending Update: topic={pending_update.get('field') or pending_update.get('topic')}, status={pending_update.get('status')}, staged_value={pending_update.get('corrected_information')}"

    user_prompt = f"""Recent Conversation History:
{history_str}

Active Pending Update State:
{pending_str}

Latest User Message:
"{message}"

Analyze the intent and return JSON adhering to the system instructions."""

    candidate_models = [model, "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "groq/compound"]
    seen_models = set()
    models_to_try = [m for m in candidate_models if m and not (m in seen_models or seen_models.add(m))]

    for mod in models_to_try:
        try:
            response = client.chat.completions.create(
                model=mod,
                messages=[
                    {"role": "system", "content": INTENT_DETECTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            raw_intent = data.get("intent", "").upper().strip()
            # Map any slight variation
            if raw_intent == "TECHNICAL_QUESTION":
                raw_intent = INTENT_TECHNICAL_RAG_QUESTION
            elif raw_intent == "FOLLOW_UP":
                raw_intent = INTENT_FOLLOW_UP_QUESTION
            elif raw_intent == "CLARIFICATION":
                raw_intent = INTENT_NORMAL_CONVERSATION

            if raw_intent in ALL_INTENTS:
                val = data.get("extracted_value")
                if val and not any(part in message for part in re.findall(r"[0-9]+(?:\.[0-9]+)?", str(val))):
                    data["extracted_value"] = None
                data["intent"] = raw_intent
                data["confidence"] = 0.90
                return data
        except Exception as e:
            print(f"[Intent LLM] Error with {mod}: {e}")
            continue

    return None

def analyze_message_intent(
    message: str,
    history: List[Dict[str, Any]],
    pending_update: Optional[Dict[str, Any]],
    client: Optional[Any] = None,
    model: str = "openai/gpt-oss-120b"
) -> Dict[str, Any]:
    """
    Master Request Router function. Classifies incoming requests into the 9 categories.
    """
    heuristic_res = fast_heuristic_intent_analysis(message, history, pending_update)
    if heuristic_res and heuristic_res.get("confidence", 0) >= 0.95:
        return heuristic_res

    if client:
        llm_res = analyze_intent_with_llm(message, history, pending_update, client, model)
        if llm_res and llm_res.get("intent") in ALL_INTENTS:
            return llm_res

    if heuristic_res:
        return heuristic_res

    msg_lower = message.lower()
    topic = detect_topic_from_text_or_context(message, history)
    if any(w in msg_lower for w in [
        "pressure", "boiler", "radiator", "pump", "f32", "delta-t", "temperature", "leak", "valve",
        "idronics", "corrosion", "piping", "hydronic", "heating"
    ]):
        return {
            "intent": INTENT_TECHNICAL_RAG_QUESTION,
            "topic": topic,
            "extracted_value": None,
            "resolved_query": message,
            "explanation_request": False,
            "confidence": 0.85
        }

    return {
        "intent": INTENT_NORMAL_CONVERSATION,
        "topic": None,
        "extracted_value": None,
        "resolved_query": None,
        "explanation_request": False,
        "confidence": 0.70
    }
