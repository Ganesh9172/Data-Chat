import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

from backend.database import (
    init_db,
    create_conversation,
    delete_conversation,
    get_all_knowledge_updates,
    delete_knowledge_update,
    get_active_knowledge_updates
)
from backend.chat import generate_chat_response

def run_tests():
    print("=" * 80)
    print("TEST SUITE: NATURAL LANGUAGE UNDERSTANDING & CONVERSATION HANDLING")
    print("=" * 80)

    init_db()

    # Clean up updates baseline
    for u in get_all_knowledge_updates():
        delete_knowledge_update(u["id"])

    # -------------------------------------------------------------
    # 1. NORMAL CONVERSATION
    # -------------------------------------------------------------
    print("\n--- 1. Testing Normal Conversation ---")
    conv_id = create_conversation(title="Normal Conv")

    # "Hi"
    r = generate_chat_response("Hi", conversation_id=conv_id)
    print("User: Hi\nBot:", r["answer"])
    assert "Hi!" in r["answer"] or "Hello!" in r["answer"]
    assert len(r["sources"]) == 0
    assert "couldn't find" not in r["answer"].lower()

    # "Hello"
    r = generate_chat_response("Hello", conversation_id=conv_id)
    print("User: Hello\nBot:", r["answer"])
    assert "Hello!" in r["answer"] or "Hi!" in r["answer"]
    assert len(r["sources"]) == 0

    # "Thank you"
    r = generate_chat_response("Thank you", conversation_id=conv_id)
    print("User: Thank you\nBot:", r["answer"])
    assert "welcome" in r["answer"].lower()
    assert len(r["sources"]) == 0

    # "How are you?"
    r = generate_chat_response("How are you?", conversation_id=conv_id)
    print("User: How are you?\nBot:", r["answer"])
    assert "doing well" in r["answer"].lower() or "help" in r["answer"].lower()

    delete_conversation(conv_id)
    print(">> Normal conversation passed!")

    # -------------------------------------------------------------
    # 2. TECHNICAL QUESTIONS
    # -------------------------------------------------------------
    print("\n--- 2. Testing Technical Questions ---")
    conv_tech = create_conversation(title="Technical")

    # "What is F32?"
    r_f32 = generate_chat_response("What is F32?", conversation_id=conv_tech)
    print("User: What is F32?\nBot:\n", r_f32["answer"])
    assert "f32" in r_f32["answer"].lower() or "circulation" in r_f32["answer"].lower()
    assert len(r_f32["sources"]) > 0

    # "What causes low water pressure?"
    r_press = generate_chat_response("What causes low water pressure?", conversation_id=conv_tech)
    print("User: What causes low water pressure?\nBot:\n", r_press["answer"][:150], "...")
    assert len(r_press["sources"]) > 0
    assert any(term in r_press["answer"].lower() for term in ["leak", "water loss", "relief", "bleed"])

    # Contextual Follow-up: "How can I fix that?"
    r_fix = generate_chat_response("How can I fix that?", conversation_id=conv_tech)
    print("User: How can I fix that?\nBot:\n", r_fix["answer"][:150], "...")
    assert len(r_fix["sources"]) > 0
    assert "couldn't find" not in r_fix["answer"].lower()

    delete_conversation(conv_tech)
    print(">> Technical questions and contextual follow-up passed!")

    # -------------------------------------------------------------
    # 3. DISTINCTION TEST (Contains "change" or "correct" but NOT update)
    # -------------------------------------------------------------
    print("\n--- 3. Testing Technical Distinction ('change' / 'correct') ---")
    conv_dist = create_conversation(title="Distinction")

    # "What causes pressure to change?"
    r_chg = generate_chat_response("What causes pressure to change?", conversation_id=conv_dist)
    print("User: What causes pressure to change?\nBot:\n", r_chg["answer"][:150], "...")
    assert not r_chg.get("is_correction_prompt", False)
    assert "should i save" not in r_chg["answer"].lower()
    assert "which value would you like" not in r_chg["answer"].lower()

    # "Can you correct my understanding of pressure?"
    r_corr_und = generate_chat_response("Can you correct my understanding of pressure?", conversation_id=conv_dist)
    print("User: Can you correct my understanding of pressure?\nBot:\n", r_corr_und["answer"][:150], "...")
    assert not r_corr_und.get("is_correction_prompt", False)
    assert "should i save" not in r_corr_und["answer"].lower()

    delete_conversation(conv_dist)
    print(">> Distinction tests passed!")

    # -------------------------------------------------------------
    # 4. VAGUE & INCOMPLETE UPDATES (Do NOT call RAG!)
    # -------------------------------------------------------------
    print("\n--- 4. Testing Vague and Incomplete Update Requests ---")
    conv_vague = create_conversation(title="Vague")

    # "I want to update a value"
    r_v1 = generate_chat_response("I want to update a value", conversation_id=conv_vague)
    print("User: I want to update a value\nBot:", r_v1["answer"])
    assert "which value would you like to update" in r_v1["answer"].lower() or "what would you like to update" in r_v1["answer"].lower()
    assert "couldn't find this information" not in r_v1["answer"].lower()
    assert len(r_v1["sources"]) == 0

    # "I want to update something"
    conv_v2 = create_conversation(title="Vague 2")
    r_v2 = generate_chat_response("I want to update something", conversation_id=conv_v2)
    print("User: I want to update something\nBot:", r_v2["answer"])
    assert "what would you like to update" in r_v2["answer"].lower()
    assert "couldn't find this information" not in r_v2["answer"].lower()

    # "I want to update the pressure"
    conv_v3 = create_conversation(title="Vague 3")
    r_v3 = generate_chat_response("I want to update the pressure", conversation_id=conv_v3)
    print("User: I want to update the pressure\nBot:", r_v3["answer"])
    assert "what should the correct pressure value be" in r_v3["answer"].lower()
    assert "couldn't find this information" not in r_v3["answer"].lower()

    # "Can I update the knowledge base?"
    conv_v4 = create_conversation(title="Vague 4")
    r_v4 = generate_chat_response("Can I update the knowledge base?", conversation_id=conv_v4)
    print("User: Can I update the knowledge base?\nBot:", r_v4["answer"])
    assert "update the knowledge base" in r_v4["answer"].lower() or "what would you like" in r_v4["answer"].lower() or "what information" in r_v4["answer"].lower()
    assert "couldn't find this information" not in r_v4["answer"].lower()

    delete_conversation(conv_vague)
    delete_conversation(conv_v2)
    delete_conversation(conv_v3)
    delete_conversation(conv_v4)
    print(">> Vague and incomplete updates passed! No false RAG fallback.")

    # -------------------------------------------------------------
    # 5. NATURAL CORRECTIONS & CONTEXT (NEVER invent values!)
    # -------------------------------------------------------------
    print("\n--- 5. Testing Natural Corrections & Contextual Reference ---")
    conv_corr = create_conversation(title="Correction Context")

    # Baseline statement from assistant
    generate_chat_response("What is the typical cold fill pressure for the system?", conversation_id=conv_corr)
    
    # User says "That's wrong."
    r_wrong = generate_chat_response("That's wrong.", conversation_id=conv_corr)
    print("User: That's wrong.\nBot:", r_wrong["answer"])
    assert "what is the correct" in r_wrong["answer"].lower() or "what should the correct" in r_wrong["answer"].lower()
    # CRITICAL: Verify zero invented values
    assert not any(num in r_wrong["answer"] for num in ["1.0", "1.2", "1.5", "1.8", "2.0"])
    assert "couldn't find this information" not in r_wrong["answer"].lower()

    # Another conversational test: "The pressure you mentioned doesn't look right."
    conv_corr2 = create_conversation(title="Correction Mention")
    generate_chat_response("What is the typical cold fill pressure for the system?", conversation_id=conv_corr2)
    r_mention = generate_chat_response("The pressure you mentioned doesn't look right.", conversation_id=conv_corr2)
    print("User: The pressure you mentioned doesn't look right.\nBot:", r_mention["answer"])
    assert "what should the correct" in r_mention["answer"].lower() or "what is the correct" in r_mention["answer"].lower()
    assert not any(num in r_mention["answer"] for num in ["1.0", "1.2", "1.5", "1.8", "2.0"])

    delete_conversation(conv_corr)
    delete_conversation(conv_corr2)
    print(">> Natural corrections and zero invented values passed!")

    # -------------------------------------------------------------
    # 6. EXPLICIT UPDATE
    # -------------------------------------------------------------
    print("\n--- 6. Testing Explicit Update Extraction ---")
    conv_exp = create_conversation(title="Explicit Update")
    r_exp = generate_chat_response("The pressure should be 1.2 bar", conversation_id=conv_exp)
    print("User: The pressure should be 1.2 bar\nBot:", r_exp["answer"])
    assert "1.2" in r_exp["answer"]
    assert "should i save this correction" in r_exp["answer"].lower()
    assert r_exp.get("is_correction_prompt", False)

    # Natural confirmation
    r_conf = generate_chat_response("Yes, that's correct. Save it.", conversation_id=conv_exp)
    print("User: Yes, that's correct. Save it.\nBot:", r_conf["answer"])
    assert "done" in r_conf["answer"].lower() and "saved" in r_conf["answer"].lower()
    active_updates = get_active_knowledge_updates()
    assert len(active_updates) == 1
    assert "1.2" in active_updates[0]["corrected_information"]

    delete_conversation(conv_exp)
    for u in get_all_knowledge_updates():
        delete_knowledge_update(u["id"])
    print(">> Explicit update and natural confirmation passed!")

    # -------------------------------------------------------------
    # 7. NATURAL CANCELLATION
    # -------------------------------------------------------------
    print("\n--- 7. Testing Natural Cancellation ---")
    conv_canc = create_conversation(title="Cancellation")
    generate_chat_response("The pressure should be 1.2 bar", conversation_id=conv_canc)
    r_canc = generate_chat_response("Actually, never mind. Don't change it.", conversation_id=conv_canc)
    print("User: Actually, never mind. Don't change it.\nBot:", r_canc["answer"])
    assert "cancelled" in r_canc["answer"].lower()
    assert len(get_active_knowledge_updates()) == 0

    # Verification: "Actually, never mind. Don't change it." without pending update
    conv_canc_nopending = create_conversation(title="No pending cancel")
    r_nopending = generate_chat_response("Never mind", conversation_id=conv_canc_nopending)
    print("User: Never mind (no pending)\nBot:", r_nopending["answer"])
    assert "cancelled and was not saved" not in r_nopending["answer"].lower()

    delete_conversation(conv_canc)
    delete_conversation(conv_canc_nopending)
    print(">> Natural cancellation tests passed!")

    # -------------------------------------------------------------
    # 8. MULTI-TURN UPDATE WORKFLOW
    # -------------------------------------------------------------
    print("\n--- 8. Testing Multi-Turn Stateful Update Workflow ---")
    conv_multi = create_conversation(title="Multi-Turn Update")

    # Step 1: Vague request
    r_m1 = generate_chat_response("I want to update a value.", conversation_id=conv_multi)
    print("User: I want to update a value.\nBot:", r_m1["answer"])
    assert "which value would you like to update" in r_m1["answer"].lower()

    # Step 2: Topic specified
    r_m2 = generate_chat_response("The pressure value.", conversation_id=conv_multi)
    print("User: The pressure value.\nBot:", r_m2["answer"])
    assert "what should the correct pressure value be" in r_m2["answer"].lower()

    # Step 3: Value specified
    r_m3 = generate_chat_response("1.2 bar.", conversation_id=conv_multi)
    print("User: 1.2 bar.\nBot:", r_m3["answer"])
    assert "1.2" in r_m3["answer"]
    assert "should i save this correction to the knowledge base" in r_m3["answer"].lower()
    assert r_m3.get("is_correction_prompt", False)

    # Step 4: Confirmation
    r_m4 = generate_chat_response("Yes.", conversation_id=conv_multi)
    print("User: Yes.\nBot:", r_m4["answer"])
    assert "done" in r_m4["answer"].lower() and "saved" in r_m4["answer"].lower()
    active_updates = get_active_knowledge_updates()
    assert len(active_updates) == 1
    assert "1.2" in active_updates[0]["corrected_information"]

    # Step 5: Query after update -> must return updated value!
    r_m5 = generate_chat_response("What is the typical cold fill pressure for the system?", conversation_id=conv_multi)
    print("User: What is the typical cold fill pressure for the system?\nBot:\n", r_m5["answer"])
    assert "1.2" in r_m5["answer"]
    assert "knowledge base update" in r_m5["answer"].lower() or any("knowledge base update" in s["document_name"].lower() for s in r_m5["sources"])

    delete_conversation(conv_multi)
    for u in get_all_knowledge_updates():
        delete_knowledge_update(u["id"])
    print(">> Multi-turn stateful update workflow passed perfectly!")

    # -------------------------------------------------------------
    # 9. CONVERSATIONAL EXPLANATION ("Can you explain that again?")
    # -------------------------------------------------------------
    print("\n--- 9. Testing Conversational Explanation Context ---")
    conv_expl = create_conversation(title="Explain Context")
    generate_chat_response("What is F32?", conversation_id=conv_expl)
    r_expl = generate_chat_response("Can you explain that again?", conversation_id=conv_expl)
    print("User: Can you explain that again?\nBot:\n", r_expl["answer"])
    assert len(r_expl["sources"]) == 0
    assert "couldn't find this information" not in r_expl["answer"].lower()

    delete_conversation(conv_expl)
    print(">> Conversational explanation passed!")

    print("\n" + "=" * 80)
    print("ALL NATURAL LANGUAGE & CONVERSATION TEST CASES PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
