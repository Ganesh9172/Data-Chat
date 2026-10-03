import os
import sys
import uuid
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.intent import (
    INTENT_NORMAL_CONVERSATION,
    INTENT_GENERAL_KNOWLEDGE,
    INTENT_CURRENT_TIME_DATE,
    INTENT_TECHNICAL_RAG_QUESTION,
    INTENT_KNOWLEDGE_CORRECTION,
    INTENT_KNOWLEDGE_UPDATE,
    INTENT_UPDATE_CONFIRMATION,
    INTENT_UPDATE_CANCELLATION,
    INTENT_FOLLOW_UP_QUESTION,
    analyze_message_intent
)
from backend.chat import generate_chat_response, get_openai_client
from backend.database import get_conversation_pending_update, clear_conversation_pending_update

def run_suite():
    print("=" * 80)
    print("RUNNING COMPREHENSIVE REQUEST ROUTING TEST SUITE (SECTION 13 SPECIFICATION)")
    print("=" * 80)

    client = get_openai_client()
    model = os.getenv("AI_MODEL", "openai/gpt-oss-120b").strip()
    passed = 0
    total = 0

    def check(test_name, condition, details=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {test_name}")
        else:
            print(f"  [FAIL] {test_name} - {details}")

    # -------------------------------------------------------------
    # PART 1: NORMAL CONVERSATION
    # -------------------------------------------------------------
    print("\n--- 1. NORMAL CONVERSATION TESTS ---")
    normal_questions = [
        "Hi",
        "Hello",
        "How are you?",
        "Thank you",
        "What is your name?",
        "Who are you?",
        "What can you do?"
    ]

    for q in normal_questions:
        intent_res = analyze_message_intent(q, [], None, client=client, model=model)
        check(
            f"Intent: '{q}' -> NORMAL_CONVERSATION",
            intent_res["intent"] == INTENT_NORMAL_CONVERSATION,
            f"Got {intent_res['intent']}"
        )

        res = generate_chat_response(message=q, conversation_id=None, is_admin=False)
        ans = res["answer"].lower()
        check(
            f"Response: '{q}' no RAG error fallback",
            "couldn't find this information in the provided documents" not in ans,
            ans
        )
        check(
            f"Response: '{q}' no source citations",
            len(res.get("sources", [])) == 0,
            f"Got sources: {res.get('sources')}"
        )
        check(
            f"Response: '{q}' is_ground_truth_verified == False",
            res.get("is_ground_truth_verified") is False,
            f"Got {res.get('is_ground_truth_verified')}"
        )

        if q == "What is your name?":
            check(
                "Identity: 'What is your name?' says 'Firebird AI'",
                "firebird ai" in ans,
                res["answer"]
            )

    # -------------------------------------------------------------
    # PART 2: DATE AND TIME QUESTIONS
    # -------------------------------------------------------------
    print("\n--- 2. DATE AND TIME TESTS ---")
    datetime_questions = [
        "What is the date today?",
        "What day is today?",
        "What is today's date?",
        "What time is it?"
    ]

    for q in datetime_questions:
        intent_res = analyze_message_intent(q, [], None, client=client, model=model)
        check(
            f"Intent: '{q}' -> CURRENT_TIME_DATE",
            intent_res["intent"] == INTENT_CURRENT_TIME_DATE,
            f"Got {intent_res['intent']}"
        )

        res = generate_chat_response(message=q, conversation_id=None, is_admin=False)
        ans = res["answer"]
        check(
            f"Response: '{q}' no RAG error fallback",
            "couldn't find this information in the provided documents" not in ans.lower(),
            ans
        )
        check(
            f"Response: '{q}' no source citations",
            len(res.get("sources", [])) == 0,
            f"Got sources: {res.get('sources')}"
        )
        check(
            f"Response: '{q}' is_ground_truth_verified == False",
            res.get("is_ground_truth_verified") is False,
            f"Got {res.get('is_ground_truth_verified')}"
        )

        # Content verification
        now = datetime.now()
        if "time" in q.lower():
            check(
                f"Time content in response to '{q}'",
                "current time is" in ans.lower() or ("am" in ans.lower() or "pm" in ans.lower() or ":" in ans),
                ans
            )
        else:
            check(
                f"Date content in response to '{q}'",
                str(now.year) in ans or now.strftime("%B").lower() in ans.lower() or now.strftime("%A").lower() in ans.lower(),
                ans
            )

    # -------------------------------------------------------------
    # PART 3: GENERAL QUESTIONS
    # -------------------------------------------------------------
    print("\n--- 3. GENERAL KNOWLEDGE TESTS ---")
    general_questions = [
        "What is AI?",
        "What is RAG?",
        "How can you help me?"
    ]

    for q in general_questions:
        intent_res = analyze_message_intent(q, [], None, client=client, model=model)
        check(
            f"Intent: '{q}' -> GENERAL_KNOWLEDGE or NORMAL_CONVERSATION",
            intent_res["intent"] in [INTENT_GENERAL_KNOWLEDGE, INTENT_NORMAL_CONVERSATION],
            f"Got {intent_res['intent']}"
        )

        res = generate_chat_response(message=q, conversation_id=None, is_admin=False)
        ans = res["answer"]
        check(
            f"Response: '{q}' no RAG error fallback",
            "couldn't find this information in the provided documents" not in ans.lower(),
            ans
        )
        check(
            f"Response: '{q}' no source citations",
            len(res.get("sources", [])) == 0,
            f"Got sources: {res.get('sources')}"
        )
        check(
            f"Response: '{q}' is_ground_truth_verified == False",
            res.get("is_ground_truth_verified") is False,
            f"Got {res.get('is_ground_truth_verified')}"
        )

    # -------------------------------------------------------------
    # PART 4: TECHNICAL QUESTIONS
    # -------------------------------------------------------------
    print("\n--- 4. TECHNICAL RAG TESTS ---")
    technical_questions = [
        "What is F32?",
        "What causes low water pressure?",
        "What causes air noise inside a hydronic heating system?",
        "Why is my radiator cold?"
    ]

    for q in technical_questions:
        intent_res = analyze_message_intent(q, [], None, client=client, model=model)
        check(
            f"Intent: '{q}' -> TECHNICAL_RAG_QUESTION",
            intent_res["intent"] == INTENT_TECHNICAL_RAG_QUESTION,
            f"Got {intent_res['intent']}"
        )

        res = generate_chat_response(message=q, conversation_id=None, is_admin=False)
        ans = res["answer"]
        sources = res.get("sources", [])
        check(
            f"Response: '{q}' has sources",
            len(sources) > 0,
            f"Got 0 sources. Answer: {ans[:100]}"
        )
        check(
            f"Response: '{q}' is_ground_truth_verified == True",
            res.get("is_ground_truth_verified") is True,
            f"Got {res.get('is_ground_truth_verified')}"
        )

    # -------------------------------------------------------------
    # PART 5: UPDATE & CORRECTION TESTS
    # -------------------------------------------------------------
    print("\n--- 5. KNOWLEDGE UPDATE / CORRECTION TESTS ---")
    update_phrases = [
        "I want to update a value.",
        "I want to update this information.",
        "I need to correct something."
    ]

    for phrase in update_phrases:
        intent_res = analyze_message_intent(phrase, [], None, client=client, model=model)
        check(
            f"Intent: '{phrase}' -> KNOWLEDGE_UPDATE",
            intent_res["intent"] == INTENT_KNOWLEDGE_UPDATE,
            f"Got {intent_res['intent']}"
        )
        res = generate_chat_response(message=phrase, conversation_id=None, is_admin=True)
        ans = res["answer"].lower()
        check(
            f"Response: '{phrase}' prompts for update details",
            "update" in ans or "what should" in ans or "which value" in ans,
            res["answer"]
        )
        check(
            f"Response: '{phrase}' no RAG error",
            "couldn't find this information in the provided documents" not in ans,
            res["answer"]
        )
        check(
            f"Response: '{phrase}' is_ground_truth_verified == False",
            res.get("is_ground_truth_verified") is False,
            f"Got {res.get('is_ground_truth_verified')}"
        )

    correction_phrases = [
        "It's incorrect.",
        "That's wrong.",
        "The previous answer is incorrect."
    ]

    # Contextual correction: simulate previous answer was technical
    tech_history = [
        {"role": "user", "content": "What is normal cold pressure?"},
        {"role": "assistant", "content": "The typical cold fill pressure is approximately 1.0–1.5 bar.\n\n**Source:** 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1"}
    ]

    for phrase in correction_phrases:
        intent_res = analyze_message_intent(phrase, tech_history, None, client=client, model=model)
        check(
            f"Intent: '{phrase}' with context -> KNOWLEDGE_CORRECTION",
            intent_res["intent"] == INTENT_KNOWLEDGE_CORRECTION,
            f"Got {intent_res['intent']}"
        )
        # Create a conversation with technical history
        conv_res = generate_chat_response(message="What is normal cold pressure?", conversation_id=None, is_admin=True)
        cid = conv_res["conversation_id"]
        res = generate_chat_response(message=phrase, conversation_id=cid, is_admin=True)
        ans = res["answer"]
        check(
            f"Response: '{phrase}' acknowledges correction politely",
            "thanks for pointing that out" in ans.lower() or "what should" in ans.lower() or "what is the correct" in ans.lower(),
            ans
        )
        check(
            f"Response: '{phrase}' is_ground_truth_verified == False",
            res.get("is_ground_truth_verified") is False,
            f"Got {res.get('is_ground_truth_verified')}"
        )

    # -------------------------------------------------------------
    # PART 6: MULTI-TURN UPDATE WORKFLOW (SECTION 7 SPECIFICATION)
    # -------------------------------------------------------------
    print("\n--- 6. MULTI-TURN UPDATE WORKFLOW ---")
    # Turn 1: "I want to update a value."
    res1 = generate_chat_response(message="I want to update a value.", conversation_id=None, is_admin=True)
    cid = res1["conversation_id"]
    check(
        "Turn 1: 'I want to update a value.' -> prompts for value and target",
        "which value would you like to update, and what should the new value be?" in res1["answer"].lower() or "what would you like to update" in res1["answer"].lower(),
        res1["answer"]
    )
    check("Turn 1: is_ground_truth_verified == False", res1.get("is_ground_truth_verified") is False)

    # Turn 2: "The pressure value."
    res2 = generate_chat_response(message="The pressure value.", conversation_id=cid, is_admin=True)
    check(
        "Turn 2: 'The pressure value.' -> prompts for correct value",
        "what should the correct pressure value be?" in res2["answer"].lower(),
        res2["answer"]
    )
    check("Turn 2: is_ground_truth_verified == False", res2.get("is_ground_truth_verified") is False)

    # Turn 3: "1.2 bar."
    res3 = generate_chat_response(message="1.2 bar.", conversation_id=cid, is_admin=True)
    check(
        "Turn 3: '1.2 bar.' -> asks confirmation with staged value",
        "1.2 bar" in res3["answer"] and ("save this correction" in res3["answer"].lower() or "would you like me to save" in res3["answer"].lower()),
        res3["answer"]
    )
    check("Turn 3: is_correction_prompt == True", res3.get("is_correction_prompt") is True)
    check("Turn 3: is_ground_truth_verified == False", res3.get("is_ground_truth_verified") is False)

    # Turn 4: "Yes" (Confirmation)
    res4 = generate_chat_response(message="Yes", conversation_id=cid, is_admin=True)
    check(
        "Turn 4: 'Yes' -> saves update",
        "done" in res4["answer"].lower() or "saved" in res4["answer"].lower(),
        res4["answer"]
    )
    check("Turn 4: is_ground_truth_verified == False", res4.get("is_ground_truth_verified") is False)

    # Clean up update by reverting
    generate_chat_response(message="revert update", conversation_id=cid, is_admin=True)

    # -------------------------------------------------------------
    # PART 7: FOLLOW-UP QUESTIONS (SECTION 9 SPECIFICATION)
    # -------------------------------------------------------------
    print("\n--- 7. FOLLOW-UP QUESTIONS ---")
    # Follow-up sequence 1: F32 -> Why does that happen? -> Can you explain it?
    f_res1 = generate_chat_response(message="What is F32?", conversation_id=None, is_admin=False)
    f_cid = f_res1["conversation_id"]
    check("F32 initial answer has sources", len(f_res1.get("sources", [])) > 0)
    check("F32 initial is_ground_truth_verified == True", f_res1.get("is_ground_truth_verified") is True)

    # Why does that happen?
    f_res2 = generate_chat_response(message="Why does that happen?", conversation_id=f_cid, is_admin=False)
    check(
        "Follow-up: 'Why does that happen?' uses RAG context and provides technical answer",
        "couldn't find this information in the provided documents" not in f_res2["answer"].lower(),
        f_res2["answer"]
    )

    # Can you explain it?
    f_res3 = generate_chat_response(message="Can you explain it?", conversation_id=f_cid, is_admin=False)
    check(
        "Follow-up: 'Can you explain it?' explains conversationally without error fallback",
        "couldn't find this information in the provided documents" not in f_res3["answer"].lower(),
        f_res3["answer"]
    )
    check("Follow-up: 'Can you explain it?' is_ground_truth_verified == False", f_res3.get("is_ground_truth_verified") is False)

    # Follow-up sequence 2: Normal cold pressure -> What about when the system is hot?
    p_res1 = generate_chat_response(message="What is normal cold pressure?", conversation_id=None, is_admin=False)
    p_cid = p_res1["conversation_id"]

    p_res2 = generate_chat_response(message="What about the pressure when hot?", conversation_id=p_cid, is_admin=False)
    check(
        "Follow-up: 'What about the pressure when hot?' discusses hot pressure",
        "hot" in p_res2["answer"].lower() and "pressure" in p_res2["answer"].lower(),
        p_res2["answer"]
    )

    print("\n" + "=" * 80)
    print(f"TEST SUITE COMPLETE: {passed}/{total} checks PASSED")
    print("=" * 80)

    return passed == total

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
