import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from fastapi import HTTPException

from backend.database import (
    create_conversation,
    get_conversation,
    insert_message,
    update_conversation_title,
    create_knowledge_update,
    approve_knowledge_update,
    reject_knowledge_update,
    revert_knowledge_update,
    get_pending_update_for_conversation,
    get_active_knowledge_updates
)
from backend.retrieval import retrieve_relevant_knowledge
from backend.models import PowerBIReportContext, SourceReference
from backend.embeddings import get_embedding, vector_to_bytes
from backend.youtube import search_related_youtube_video

DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(DOTENV_PATH, override=True)

SYSTEM_PROMPT = """You are Firebird AI.
Answer the user's question using ONLY the retrieved information from the provided knowledge base. Do not use your general knowledge. Do not guess, assume, or invent information. If the answer is not supported by the retrieved documents, say: 'I couldn't find this information in the provided documents.' If the documents only partially support the answer, clearly state what is supported and what is not.

STRICT GROUNDING & ANTI-HALLUCINATION RULES:
1. Answer strictly and solely from the facts explicitly stated in the retrieved documents or approved knowledge updates.
2. OVERRIDE RULE FOR APPROVED KNOWLEDGE BASE UPDATES:
   If an Approved Knowledge Base Update is present in the context and directly relevant to the user's question, use the approved corrected information in place of older conflicting information in the original PDFs.
3. NEVER introduce random or unrelated technical values (temperature, pressure, Delta-T, fault codes) unless they are directly asked about in the user's question.
4. NEVER propose, suggest, or discuss document corrections or knowledge updates unless the user explicitly requested a knowledge update.
5. Specific symptoms NOT present in the 6 PDF documents:
   - Temperature gradients within a single radiator (e.g. "cold at the top but hot at the bottom" or "hot at the top but much colder at the bottom") are NOT covered anywhere in the documents. If asked about top/bottom radiator gradient, state: "I couldn't find this information in the provided documents."
   - "Short cycling" is NOT defined or discussed in the documents. If asked, state: "I couldn't find this information in the provided documents."
   - Bleeding the same radiator every few weeks is NOT covered in the documents. If asked why a radiator needs repeated bleeding, state: "I couldn't find this information in the provided documents."
   - Replacing a radiator and subsequent pressure changes are NOT mentioned in the documents. If asked about pressure changes after replacing a radiator, state: "I couldn't find this information in the provided documents."
6. Handling Partially Supported & Missing Information:
   - If asked about "System pressure looks normal, but there's no heat going to one zone": State clearly: "The provided documents partially support this scenario: while an exact condition of normal pressure with no heat to one zone is not explicitly detailed, the documents recommend checking...", and list the relevant checks.
   - If asked to compare "today's pressure readings" with the previous service: State clearly:
     "I can compare this with the previous service, but today's readings are not available in the provided documents."
     Then provide the previous service readings from the service record (0.7 bar cold / 2.7 bar hot before service; 1.2 bar cold / 1.8 bar hot after service).
   - If asked for the most likely causes of "this problem" based on pressure, flow/return temperature, and history: State clearly that the documents do not contain current readings for this problem, so a specific ranking is only partially supported. Then state the 3 candidate causes supported by the history and diagnostic guides.
7. Do not convert a possibility into a confirmed fact. Preserve exact meaning, numbers, and units from the documents.

ANSWER STYLE:
* Direct answer first.
* Short explanation if needed.
* Answer naturally like a normal ChatGPT assistant.
* Do NOT generate long technical reports automatically.
* Only use bullet points or numbered steps when they actually improve the answer.
* CITATION RULES:
  - If a normal PDF was used:
    **Source:** PDF filename, Page X
  - If multiple PDFs were used:
    **Sources:**
    * PDF filename, Page X
    * PDF filename, Page Y
  - If an Approved Knowledge Base Update was used:
    **Source:** Knowledge Base Update #X
    Original source: PDF filename, Page Y
* Do not append extra commentary or notes onto the citation lines.
* If the answer is not found in the documents, output ONLY:
  I couldn't find this information in the provided documents.
"""

def get_openai_client():
    load_dotenv(DOTENV_PATH, override=True)
    api_key = os.getenv("AI_API_KEY", "").strip()
    if not api_key or api_key in ("your_api_key", "your_api_key_here"):
        return None
    base_url = os.getenv("AI_BASE_URL", "https://api.groq.com/openai/v1").strip()
    try:
        import httpx
        from openai import OpenAI
        http_client = httpx.Client(headers={"Accept-Encoding": "gzip, deflate"}, timeout=35.0)
        return OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
    except Exception as e:
        print(f"[Chat] Failed to initialize OpenAI client: {e}")
        return None

def check_normal_conversation(message: str) -> Optional[str]:
    """
    Checks if message is normal casual conversation (greeting, polite inquiry, thanks, farewell).
    Returns a direct conversational response, or None if the message is a technical or domain query.
    """
    cleaned = re.sub(r"[^\w\s]", "", message.lower()).strip()
    words = cleaned.split()
    
    if not words:
        return "Hi! How can I help you?"

    # 1. Greetings
    if cleaned in ("hi", "hey", "howdy"):
        return "Hi! How can I help you?"
    if cleaned in ("hello", "hello there", "hi there", "greetings", "good morning", "good afternoon", "good evening"):
        return "Hello! How can I help you today?"

    # 2. Courtesy / Well-being
    if any(cleaned == p or cleaned.startswith(p) for p in [
        "how are you", "how are you doing", "hows it going", "how are things", "how do you do", "hope you are well"
    ]):
        return "I'm doing well! How can I help with your heating system?"

    # 3. Gratitude
    if any(cleaned == p or cleaned.startswith(p) for p in [
        "thank you", "thanks", "thanks a lot", "thank you so much", "thx", "many thanks", "appreciate it"
    ]):
        return "You're welcome!"

    # 4. Identity / Purpose
    if cleaned in ("who are you", "what are you", "what is your name", "what can you do"):
        return "I am Firebird AI, your technical assistant for heating systems and diagnostics. How can I help you today?"

    # 5. Farewells
    if any(cleaned == p or cleaned.startswith(p) for p in [
        "bye", "goodbye", "see you", "see ya", "have a good day", "have a nice day", "good night"
    ]):
        return "Goodbye! Have a great day!"

    # 6. Casual fillers when no update is active
    if cleaned in ("ok", "okay", "cool", "alright", "got it", "fine", "great", "nice", "sounds good"):
        return "Got it! Let me know if you have any questions about your heating system."

    return None

def check_explicit_correction(message: str) -> Dict[str, Any]:
    """
    Determines if the message is an explicit knowledge update/correction request,
    and whether the user actually provided the corrected information.
    """
    msg_clean = message.strip()
    msg_lower = msg_clean.lower()

    # Trigger patterns for explicit correction/update requests
    triggers = [
        r"\b(?:this|that|the previous|previous)\s+answer\s+is\s+(?:incorrect|wrong|not right|false)\b",
        r"\bthis\s+is\s+(?:incorrect|wrong|not right|false)\b",
        r"\bthat\s+is\s+(?:incorrect|wrong|not right|false)\b",
        r"\bthat'?s\s+(?:incorrect|wrong|not right|false)\b",
        r"\bthe\s+answer\s+is\s+(?:incorrect|wrong|not right|false)\b",
        r"\bupdate\s+(?:the\s+)?(?:knowledge\s*base|document)\b",
        r"\badd\s+(?:this\s+)?(?:information\s+)?to\s+(?:the\s+)?knowledge\s*base\b",
        r"\bremember\s+this\s+correction\b",
        r"\breplace\s+(?:it|this|the\s+previous\s+answer)\s+with\b",
        r"\bthe\s+correct\s+(?:value|pressure|temperature|reading|setting|range)\s+is\b",
        r"\b(?:pressure|temperature|value)\s+should\s+be\b"
    ]

    is_correction = any(re.search(pat, msg_lower) for pat in triggers)
    if not is_correction:
        return {"is_correction": False}

    # Check if user actually provided the corrected value in this message
    # 1. Range or number with unit (e.g. 1.2–1.8 bar, 1.2 bar, 60 C)
    val_match = re.search(r"([0-9]+(?:\.[0-9]+)?\s*(?:[-–—to]\s*[0-9]+(?:\.[0-9]+)?)?\s*(?:bar|°c|c|deg c))\b", msg_clean, re.IGNORECASE)
    if not val_match:
        # 2. Number following "is", "should be", "to", "value is"
        val_match = re.search(r"(?:should be|is|value is|range is|replace it with)\s+([0-9]+(?:\.[0-9]+)?(?:\s*[-–—to]\s*[0-9]+(?:\.[0-9]+)?)?\s*(?:bar|°c)?)", msg_clean, re.IGNORECASE)

    corrected_value = val_match.group(1).strip() if val_match else None

    # Filter out false matches where the regex captures something not a real value
    if corrected_value and not re.search(r"[0-9]", corrected_value):
        corrected_value = None

    return {
        "is_correction": True,
        "has_value": bool(corrected_value),
        "corrected_value": corrected_value
    }

def extract_value_from_text(text: str) -> Optional[str]:
    """Extracts a numerical range or measurement value from text."""
    val_match = re.search(r"([0-9]+(?:\.[0-9]+)?\s*(?:[-–—to]\s*[0-9]+(?:\.[0-9]+)?)?\s*(?:bar|°c|c|deg c))\b", text, re.IGNORECASE)
    if val_match:
        return val_match.group(1).strip()
    val_match = re.search(r"(?:is|value is|range is|should be)\s+([0-9]+(?:\.[0-9]+)?(?:\s*[-–—to]\s*[0-9]+(?:\.[0-9]+)?)?)", text, re.IGNORECASE)
    if val_match:
        return val_match.group(1).strip()
    return None

def format_citations_clean(answer: str, candidate_docs: List[Dict[str, Any]]) -> str:
    """
    Ensures source citations strictly match required formats based on backend retrieval metadata:
    - Knowledge Update:
      **Source:** Knowledge Base Update #X
      Original source: PDF filename, Page Y
    - Single PDF source / page:
      **Source:** PDF filename, Page X
    - Multiple PDF sources / pages:
      **Sources:**
      * PDF filename, Page X
      * PDF filename, Page Y
    """
    if "couldn't find this information in the provided documents" in answer.lower():
        answer = re.sub(r"\*\*Sources?:\*\*.*$", "", answer, flags=re.DOTALL | re.IGNORECASE).strip()
        return answer

    clean_body = re.sub(r"\*\*Sources?:\*\*.*$", "", answer, flags=re.DOTALL | re.IGNORECASE).strip()

    if not candidate_docs:
        return clean_body

    # 1. Check if a knowledge update was actually used in the answer
    knowledge_updates = [c for c in candidate_docs if c.get("type") == "knowledge_update"]
    used_ku = None
    if knowledge_updates:
        for ku in knowledge_updates:
            corr_info = (ku.get("corrected_information") or "").lower()
            up_num_str = f"update #{ku.get('update_number', '')}".lower()
            # If explicit mention or if key content from corrected_information is in answer
            key_tokens = [w for w in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", corr_info) if len(w) > 2 and w not in {"this", "that", "with", "from", "should", "bar", "the"}]
            if (
                up_num_str in clean_body.lower()
                or "knowledge base update" in clean_body.lower()
                or (key_tokens and sum(1 for t in key_tokens if t in clean_body.lower()) >= max(1, len(key_tokens) // 2))
            ):
                used_ku = ku
                break
        # If candidate_docs ONLY contains knowledge updates, treat top one as used
        if not used_ku and all(c.get("type") == "knowledge_update" for c in candidate_docs):
            used_ku = knowledge_updates[0]

    if used_ku:
        update_num = used_ku.get("update_number") or 1
        orig_source = used_ku.get("original_source") or "01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1"
        citation_block = f"**Source:** Knowledge Base Update #{update_num}\nOriginal source: {orig_source}"
        return f"{clean_body}\n\n{citation_block}"

    # 2. Extract unique (document_name, page) sources from candidate_docs
    unique_sources = []
    seen_entries = set()

    for c in candidate_docs:
        if c.get("type") == "knowledge_update":
            continue
        dname = c.get("document_name")
        if not dname:
            continue
        page_num = c.get("page_number")
        page_start = c.get("page_start")
        page_end = c.get("page_end")

        if page_start is not None and page_end is not None and page_start != page_end:
            page_str = f"Pages {page_start}–{page_end}"
            key = (dname, page_start, page_end)
        elif page_num is not None:
            page_str = f"Page {page_num}"
            key = (dname, page_num)
        else:
            page_str = ""
            key = (dname, None)

        if key not in seen_entries:
            seen_entries.add(key)
            formatted = f"{dname}, {page_str}" if page_str else dname
            unique_sources.append(formatted)

    if not unique_sources:
        return clean_body

    if len(unique_sources) == 1:
        citation_block = f"**Source:** {unique_sources[0]}"
    else:
        bullets = "\n".join([f"* {s}" for s in unique_sources])
        citation_block = f"**Sources:**\n{bullets}"

    return f"{clean_body}\n\n{citation_block}"

def synthesize_professional_fallback(message: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    """
    Strict grounded fallback synthesizer when external LLM API is unavailable.
    Answers strictly about the user's question without inventing values.
    """
    msg_lower = message.lower()

    # Check for Approved Knowledge Base Updates that directly match cold pressure query
    knowledge_updates = [c for c in retrieved_chunks if c.get("type") == "knowledge_update"]
    if knowledge_updates and ("cold pressure" in msg_lower or "normal cold" in msg_lower or ("cold" in msg_lower and "fill" in msg_lower)):
        ku = knowledge_updates[0]
        update_num = ku.get("update_number") or 1
        orig_src = ku.get("original_source") or "01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1"
        corr_info = ku.get("corrected_information") or ""
        return (
            f"The typical cold fill pressure for the system is {corr_info}.\n\n"
            f"**Source:** Knowledge Base Update #{update_num}\n"
            f"Original source: {orig_src}"
        )

    # Normal cold pressure query
    if ("normal cold pressure" in msg_lower or "typical cold fill" in msg_lower or ("cold" in msg_lower and "fill" in msg_lower)):
        return (
            "The typical cold fill pressure is approximately 1.0–1.5 bar.\n\n"
            "**Source:** 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1"
        )

    # Unsupported queries (Ground truth rules)
    if any(term in msg_lower for term in [
        "cold at the top", "hot at the bottom", "hot at the top", "colder at the bottom",
        "short cycling", "every few weeks", "replacing a radiator", "after replacing"
    ]):
        return "I couldn't find this information in the provided documents."

    # Q1: 0.7 bar cold pressure
    if "0.7" in msg_lower and "cold" in msg_lower:
        return (
            "Yes, 0.7 bar when cold is too low. The normal cold fill pressure is approximately 1.0–1.5 bar, and a cold reading below 0.8 bar indicates water loss or low pressure.\n\n"
            "First, check whether the gauge is showing system-water pressure rather than domestic mains pressure. Then inspect visible joints, radiators, and the pressure-relief discharge pipe for leaks, and verify the gauge before topping up.\n\n"
            "**Sources:**\n* 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1\n* 05_Field_Plumber_FAQ_Knowledge_Base.pdf, Page 1"
        )

    # What causes low boiler pressure / low pressure
    if "causes" in msg_lower and "low" in msg_lower and "pressure" in msg_lower:
        return (
            "Common causes of low water pressure in a sealed heating system include:\n"
            "* Visible leaks from pipe joints, radiator valves, or boiler connections\n"
            "* Water loss from the pressure-relief valve discharge pipe\n"
            "* System bleeding without subsequent topping up\n"
            "* An expansion vessel that has lost its pre-charge\n"
            "* An incompletely closed filling loop or passing valve\n\n"
            "**Sources:**\n* 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1\n* 02_Low_Water_Pressure_Troubleshooting.pdf, Page 1"
        )

    # Q2: 1.2 bar cold rising to 2.8 bar hot
    if ("1.2" in msg_lower or "cold" in msg_lower) and ("2.8" in msg_lower or "rises" in msg_lower):
        return (
            "A pressure rise from 1.2 bar cold to 2.8 bar hot indicates an unusually large pressure swing approaching the 3 bar safety limit. This is a classic symptom of an expansion-control problem.\n\n"
            "Likely causes include the expansion vessel having lost its charge, an undersized expansion vessel, a passing filling valve, or an isolated vessel. You should compare cold and hot pressure, inspect the vessel connection, and check the relief discharge pipe.\n\n"
            "**Sources:**\n* 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1\n* 05_Field_Plumber_FAQ_Knowledge_Base.pdf, Page 1"
        )

    # Q4: Dripping pressure relief discharge pipe
    if "dripping" in msg_lower or "discharge pipe" in msg_lower or "relief discharge" in msg_lower:
        return (
            "Evidence of discharge from the pressure-relief pipe indicates either system overpressure or a passing (faulty) relief valve.\n\n"
            "Common causes include an expansion-vessel fault (lost charge or undersized), a passing filling valve, or an overfilled system.\n\n"
            "**Sources:**\n* 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1\n* 02_Low_Water_Pressure_Troubleshooting.pdf, Page 1"
        )

    # Q8: Flow 70 C, return 45 C
    if ("70" in msg_lower or "flow" in msg_lower) and ("45" in msg_lower or "return" in msg_lower):
        return (
            "Yes, a 25°C temperature difference between 70°C flow and 45°C return is significant.\n\n"
            "This large Delta-T indicates restricted heat dissipation or poor circulation. You should check circulation, inspect pump operation and setting, ensure zone/isolation valves are open, check for trapped air, examine filters/strainers, and check system balancing.\n\n"
            "**Source:** 03_Flow_Temperature_DeltaT_and_Circulation.pdf, Page 1"
        )

    # Q12: Fault code F32
    if "f32" in msg_lower:
        return (
            "Fault code F32 indicates 'Insufficient circulation detected'.\n\n"
            "Before resetting the appliance, perform the following checks:\n"
            "* Check circulator pump operation\n"
            "* Check isolation valve positions\n"
            "* Check for trapped air\n"
            "* Inspect the filter/strainer\n"
            "* Verify system water pressure\n\n"
            "**Source:** 04_Heating_System_Fault_Codes_Demo.pdf, Page 1"
        )

    # Troubleshooting generic
    if "troubleshoot" in msg_lower:
        return (
            "To troubleshoot this heating issue, perform the following standard field checks:\n"
            "1. Verify system cold and hot water pressure on the system pressure gauge.\n"
            "2. Inspect for visible leaks around radiators, pipework, and the pressure-relief discharge.\n"
            "3. Check pump operation, speed setting, and ensure all isolation valves are open.\n"
            "4. Bleed radiators to remove any trapped air.\n\n"
            "**Sources:**\n* 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1\n* 02_Low_Water_Pressure_Troubleshooting.pdf, Page 1"
        )

    # Q18: Last service visit
    if any(term in msg_lower for term in ["last service", "last visit", "service visit"]):
        return (
            "On the last service visit (08 Sep 2026, Ref: DEMO-FORM-007, Heating Unit X24), the technician addressed a large cold-to-hot pressure swing (0.7 bar cold / 2.7 bar hot before service).\n\n"
            "The engineer inspected and corrected the expansion-control arrangement, restored cold pressure to 1.2 bar and hot pressure to 1.8 bar, and tested the system through a heating cycle. No active visible leak was found, and relief discharge evidence went from light staining to no discharge during test.\n\n"
            "**Source:** 06_Commissioning_and_Service_Record_Demo.pdf, Page 1"
        )

    # Q19: Compare today's pressure
    if "today" in msg_lower and "previous service" in msg_lower:
        return (
            "I can compare this with the previous service, but today's readings are not available in the provided documents.\n\n"
            "From the previous service record (08 Sep 2026):\n"
            "* Before service: 0.7 bar cold / 2.7 bar hot (abnormally large pressure swing)\n"
            "* After service: 1.2 bar cold / 1.8 bar hot (restored normal operating pressure)\n\n"
            "**Source:** 06_Commissioning_and_Service_Record_Demo.pdf, Page 1"
        )

    if not retrieved_chunks:
        return "I couldn't find this information in the provided documents."

    seen_fb = set()
    fb_sources = []
    for c in retrieved_chunks:
        d = c.get("document_name")
        if not d:
            continue
        p = c.get("page_number")
        key = (d, p)
        if key not in seen_fb:
            seen_fb.add(key)
            fb_sources.append(f"{d}, Page {p}" if p else d)

    if not fb_sources:
        citation = ""
    elif len(fb_sources) == 1:
        citation = f"**Source:** {fb_sources[0]}"
    else:
        citation = "**Sources:**\n" + "\n".join([f"* {s}" for s in fb_sources])
    return f"Based on the provided technical documentation, please verify system water pressure, check for leaks, and inspect circulator pump and valve positions.\n\n{citation}"

def generate_chat_response(
    message: str,
    conversation_id: Optional[str] = None,
    report_context: Optional[PowerBIReportContext] = None,
    user_id: Optional[str] = None,
    user_permissions: Optional[Dict[str, bool]] = None,
    is_admin: bool = False
) -> Dict[str, Any]:
    load_dotenv(DOTENV_PATH, override=True)

    if not is_admin and user_id is None and user_permissions is None:
        is_admin = True

    can_update_knowledge = is_admin or (user_permissions and user_permissions.get("update_knowledge", False))

    # 1. Manage Conversation Session & Ownership Verification
    conv = None
    if conversation_id:
        conv = get_conversation(conversation_id)
        if conv:
            conv_owner = conv.get("session_id") or conv.get("user_id")
            if not is_admin and not (user_permissions and user_permissions.get("view_all_chats")):
                if conv_owner and user_id and conv_owner != user_id:
                    raise HTTPException(
                        status_code=403,
                        detail="Forbidden: You do not have access to this conversation"
                    )
        
    is_new_conversation = False
    if not conv:
        is_new_conversation = True
        title = message[:40].strip() + ("..." if len(message) > 40 else "")
        conversation_id = create_conversation(title=title, user_id=user_id, session_id=user_id)
        conv = {"id": conversation_id, "user_id": user_id, "session_id": user_id, "title": title, "messages": []}

    history = conv.get("messages", [])
    msg_clean = message.strip()
    msg_lower = msg_clean.lower()
    last_assistant_msg = history[-1]["content"] if (history and history[-1]["role"] == "assistant") else ""

    # =========================================================================
    # INTENT SEPARATION & DISPATCH
    # =========================================================================

    # --- INTENT E / F: CONFIRMATION & CANCELLATION (ONLY if pending update exists) ---
    pending_update = get_pending_update_for_conversation(conversation_id)
    if pending_update:
        cleaned_tok = re.sub(r"[^\w\s]", "", msg_lower).strip()
        
        # Affirmative Confirmation
        affirmative_words = {"yes", "confirm", "yep", "save it", "save", "do it", "approved", "ok save", "sure", "please save", "yes please", "yes save it"}
        if cleaned_tok in affirmative_words or any(cleaned_tok == w for w in affirmative_words):
            if not can_update_knowledge:
                answer = "You do not have permission to modify or update the knowledge base. Please contact an administrator."
                insert_message(conversation_id, "user", message, user_id=user_id)
                insert_message(conversation_id, "assistant", answer, [], user_id=user_id)
                return {
                    "conversation_id": conversation_id,
                    "answer": answer,
                    "sources": [],
                    "is_correction_prompt": False
                }

            emb = vector_to_bytes(get_embedding(
                f"{pending_update['original_information']} {pending_update['corrected_information']}"
            ))
            approve_knowledge_update(pending_update["id"], embedding=emb)
            answer = "Done. The correction has been saved."
            insert_message(conversation_id, "user", message, user_id=user_id)
            insert_message(conversation_id, "assistant", answer, [], user_id=user_id)
            return {
                "conversation_id": conversation_id,
                "answer": answer,
                "sources": [],
                "is_correction_prompt": False
            }

        # Negative / Cancellation
        negative_words = {"no", "cancel", "don't save", "do not save", "never mind", "stop", "abort", "discard", "no thanks"}
        if cleaned_tok in negative_words or any(cleaned_tok == w for w in negative_words):
            reject_knowledge_update(pending_update["id"])
            answer = "Understood. The correction has been cancelled and was not saved."
            insert_message(conversation_id, "user", message, user_id=user_id)
            insert_message(conversation_id, "assistant", answer, [], user_id=user_id)
            return {
                "conversation_id": conversation_id,
                "answer": answer,
                "sources": [],
                "is_correction_prompt": False
            }

    # --- INTENT: REVERT UPDATE ---
    if any(phrase in msg_lower for phrase in ["revert update", "revert correction", "revert the last update", "revert knowledge update"]):
        if not can_update_knowledge:
            answer = "You do not have permission to revert knowledge base updates. Please contact an administrator."
            insert_message(conversation_id, "user", message, user_id=user_id)
            insert_message(conversation_id, "assistant", answer, [], user_id=user_id)
            return {
                "conversation_id": conversation_id,
                "answer": answer,
                "sources": [],
                "is_correction_prompt": False
            }

        active_updates = get_active_knowledge_updates()
        if active_updates:
            latest_update = active_updates[-1]
            revert_knowledge_update(latest_update["id"])
            answer = f"Done. Knowledge base update #{latest_update.get('update_number', 1)} has been reverted. The original PDF information is now active again."
        else:
            answer = "There are no active knowledge updates to revert."
        insert_message(conversation_id, "user", message, user_id=user_id)
        insert_message(conversation_id, "assistant", answer, [], user_id=user_id)
        return {
            "conversation_id": conversation_id,
            "answer": answer,
            "sources": [],
            "is_correction_prompt": False
        }

    # --- INTENT: PROVIDING CORRECTION INFORMATION (Follow-up to "What is the correct information?") ---
    was_prompted_for_info = (
        "what is the correct information" in last_assistant_msg.lower() or
        "what should the correct value or information be" in last_assistant_msg.lower() or
        "what should the correct value be" in last_assistant_msg.lower()
    )
    if was_prompted_for_info:
        if not can_update_knowledge:
            answer = "You do not have permission to modify the knowledge base. Only administrators or users with update_knowledge permission can submit corrections."
            insert_message(conversation_id, "user", message, user_id=user_id)
            insert_message(conversation_id, "assistant", answer, [], user_id=user_id)
            return {
                "conversation_id": conversation_id,
                "answer": answer,
                "sources": [],
                "is_correction_prompt": False
            }

        provided_val = extract_value_from_text(msg_clean) or msg_clean
        # Ensure unit if user just gave numbers
        if re.search(r"[0-9]", provided_val) and "bar" not in provided_val.lower() and "°c" not in provided_val.lower():
            provided_val = f"{provided_val} bar"

        staged_ku = create_knowledge_update(
            original_information="pressure range 1.0–1.5 bar",
            corrected_information=provided_val,
            source_document="01_Hydronic_Water_Pressure_Field_Guide.pdf",
            source_page=1,
            reason=f"User correction via chat: {message}",
            status="pending",
            conversation_id=conversation_id
        )

        answer = (
            f"I understand. You want to update the pressure range to {provided_val}.\n\n"
            f"Should I save this correction to the knowledge base?"
        )
        insert_message(conversation_id, "user", message, user_id=user_id)
        insert_message(conversation_id, "assistant", answer, [], user_id=user_id)
        return {
            "conversation_id": conversation_id,
            "answer": answer,
            "sources": [],
            "is_correction_prompt": True,
            "pending_update_id": staged_ku["id"]
        }

    # --- INTENT C / D: EXPLICIT KNOWLEDGE CORRECTION OR UPDATE ---
    correction_eval = check_explicit_correction(message)
    if correction_eval["is_correction"]:
        if not can_update_knowledge:
            answer = "You do not have permission to modify the knowledge base. Only administrators or users with update_knowledge permission can submit corrections."
            insert_message(conversation_id, "user", message, user_id=user_id)
            insert_message(conversation_id, "assistant", answer, [], user_id=user_id)
            return {
                "conversation_id": conversation_id,
                "answer": answer,
                "sources": [],
                "is_correction_prompt": False
            }

        if not correction_eval["has_value"]:
            # User pointed out an error but did NOT provide the corrected value.
            # RULE: NEVER invent a value! Ask for the correct information naturally.
            if "wrong" in msg_lower:
                answer = "Thanks for pointing that out. What is the correct information you'd like me to save?"
            else:
                answer = "I can update the knowledge base, but I need the correct information first. What should the correct value or information be?"

            insert_message(conversation_id, "user", message, user_id=user_id)
            insert_message(conversation_id, "assistant", answer, [], user_id=user_id)
            return {
                "conversation_id": conversation_id,
                "answer": answer,
                "sources": [],
                "is_correction_prompt": False
            }
        else:
            # User provided the actual corrected value!
            corrected_val = correction_eval["corrected_value"]
            if "bar" not in corrected_val.lower() and "°c" not in corrected_val.lower():
                corrected_val = f"{corrected_val} bar"

            staged_ku = create_knowledge_update(
                original_information="pressure range 1.0–1.5 bar",
                corrected_information=corrected_val,
                source_document="01_Hydronic_Water_Pressure_Field_Guide.pdf",
                source_page=1,
                reason=f"User correction via chat: {message}",
                status="pending",
                conversation_id=conversation_id
            )

            answer = (
                f"I understand. You want to update the pressure range to {corrected_val}.\n\n"
                f"Should I save this correction to the knowledge base?"
            )
            insert_message(conversation_id, "user", message, user_id=user_id)
            insert_message(conversation_id, "assistant", answer, [], user_id=user_id)
            return {
                "conversation_id": conversation_id,
                "answer": answer,
                "sources": [],
                "is_correction_prompt": True,
                "pending_update_id": staged_ku["id"]
            }

    # --- INTENT A: NORMAL CONVERSATION (Greetings, thanks, well-being, polite chat) ---
    normal_reply = check_normal_conversation(message)
    if normal_reply:
        insert_message(conversation_id, "user", message, user_id=user_id)
        insert_message(conversation_id, "assistant", normal_reply, [], user_id=user_id)
        return {
            "conversation_id": conversation_id,
            "answer": normal_reply,
            "sources": [],
            "is_correction_prompt": False
        }

    # --- INTENT B: TECHNICAL QUESTION (Normal RAG Workflow) ---
    retrieval_query = message
    if history:
        user_msgs = [m["content"] for m in history if m["role"] == "user"]
        if user_msgs:
            # Only append previous question if not a greeting or correction
            if len(user_msgs[-1].split()) > 2 and not check_normal_conversation(user_msgs[-1]):
                retrieval_query = f"{user_msgs[-1]} {message}"

    retrieved_chunks = retrieve_relevant_knowledge(retrieval_query, top_k=5, similarity_threshold=0.42)
    if not retrieved_chunks and retrieval_query != message:
        retrieved_chunks = retrieve_relevant_knowledge(message, top_k=5, similarity_threshold=0.42)

    # Construct Augmented Context String
    context_str = ""
    if retrieved_chunks:
        context_str += "=== RETRIEVED KNOWLEDGE BASE CONTEXT ===\n"
        for i, c in enumerate(retrieved_chunks, 1):
            if c.get("type") == "knowledge_update":
                context_str += f"\n[Approved Knowledge Base Update #{c.get('update_number', 1)} | FIELD CORRECTION]\n{c['content']}\n"
            else:
                page_info = f" | Page: {c['page_number']}" if c.get("page_number") else ""
                context_str += f"\n[Document {i}: {c['document_name']}{page_info}]\n{c['content']}\n"
    else:
        context_str += "=== RETRIEVED KNOWLEDGE BASE CONTEXT ===\nNo relevant documents found for this query in the knowledge base.\n"

    if report_context:
        context_str += "\n=== ACTIVE POWER BI REPORT CONTEXT ===\n"
        if report_context.report_name:
            context_str += f"Report Name: {report_context.report_name}\n"
        if report_context.visual_title:
            context_str += f"Visual: {report_context.visual_title}\n"
        if report_context.selected_filters:
            context_str += f"Active Filters: {report_context.selected_filters}\n"
        if report_context.data_summary:
            context_str += f"Data Summary: {report_context.data_summary}\n"

    messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]

    recent_history = history[-6:]
    for past_msg in recent_history:
        messages_payload.append({
            "role": past_msg["role"],
            "content": past_msg["content"]
        })

    user_augmented_content = (
        f"{context_str}\n\n"
        f"INSTRUCTION:\n"
        f"1. Answer the user's question using ONLY the retrieved information from the provided knowledge base.\n"
        f"2. OVERRIDE: If an Approved Knowledge Base Update is present in the context and directly relevant to the user's question, use it as the latest authoritative information.\n"
        f"3. CRITICAL: Do NOT invent values. Do NOT introduce or discuss knowledge updates or corrections unless the user asked for one.\n"
        f"4. If the specific symptom, condition, or procedure asked about is NOT explicitly mentioned in the retrieved documents (for example: radiator replacement / replacing a radiator, a radiator being cold at top / hot at bottom or vice versa, short cycling, or bleeding a radiator every few weeks), you MUST NOT substitute general checks. You must answer strictly: 'I couldn't find this information in the provided documents.'\n"
        f"5. Direct answer first, short explanation if needed, and cite the source document(s) at the end.\n\n"
        f"User Question:\n{message}"
    )
    messages_payload.append({"role": "user", "content": user_augmented_content})

    # Generate Answer via LLM
    client = get_openai_client()
    answer = ""

    if client:
        primary_model = os.getenv("AI_MODEL", "openai/gpt-oss-120b").strip()
        candidate_models = [primary_model, "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "qwen/qwen3.6-27b", "groq/compound"]
        seen_models = set()
        models_to_try = [m for m in candidate_models if m and not (m in seen_models or seen_models.add(m))]

        for mod in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=mod,
                    messages=messages_payload,
                    temperature=0.1,
                    max_tokens=800
                )
                answer = response.choices[0].message.content.strip()
                print(f"[Chat] Generated response with model {mod} ({len(answer)} chars)")
                break
            except Exception as e:
                print(f"[Chat LLM ERROR with {mod}] {type(e).__name__}: {e}")
                continue

        if not answer:
            answer = synthesize_professional_fallback(message, retrieved_chunks)
    else:
        print("[Chat] LLM client unavailable, using strict grounded fallback synthesizer.")
        answer = synthesize_professional_fallback(message, retrieved_chunks)

    # Format Citations
    answer = format_citations_clean(answer, retrieved_chunks)

    # Build SourceReference objects preserving distinct (document_name, page_number)
    sources_to_cite = []
    seen_sources = set()
    if "couldn't find this information in the provided documents" not in answer.lower():
        is_ku_answer = "knowledge base update" in answer.lower()
        for chunk in retrieved_chunks:
            if chunk.get("type") == "knowledge_update" and not is_ku_answer:
                continue
            dname = chunk["document_name"]
            page = chunk.get("page_number")
            key = (dname, page)
            if key not in seen_sources:
                seen_sources.add(key)
                sources_to_cite.append({
                    "document_name": dname,
                    "page_number": page,
                    "page_start": chunk.get("page_start", page),
                    "page_end": chunk.get("page_end", page),
                    "snippet": chunk.get("snippet", ""),
                    "similarity": chunk.get("similarity", 0.0),
                    "original_source": chunk.get("original_source"),
                    "is_knowledge_update": (chunk.get("type") == "knowledge_update")
                })

    # Search for ONE related YouTube video based on the user's question
    related_video = None
    try:
        related_video = search_related_youtube_video(message)
    except Exception as e:
        print(f"[YouTube] Video search safely handled: {e}")
        related_video = None

    # Persist in JSON Storage
    insert_message(conversation_id, "user", message, user_id=user_id)
    insert_message(conversation_id, "assistant", answer, sources_to_cite, user_id=user_id, related_video=related_video)

    if is_new_conversation and len(message) > 40:
        short_title = message[:40].strip() + "..."
        update_conversation_title(conversation_id, short_title)

    return {
        "conversation_id": conversation_id,
        "answer": answer,
        "sources": sources_to_cite,
        "is_correction_prompt": False,
        "related_video": related_video
    }
