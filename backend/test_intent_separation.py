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

def test_intent_separation():
    print("=" * 75)
    print("TESTING BUG FIX: NORMAL CHAT VS KNOWLEDGE UPDATE INTENT SEPARATION")
    print("=" * 75)

    init_db()

    # Clean up previous updates to start fresh
    for u in get_all_knowledge_updates():
        delete_knowledge_update(u["id"])

    # -------------------------------------------------------------
    # 1. Test "Hi"
    # -------------------------------------------------------------
    print("\n[Case 1] Testing: 'Hi'")
    res1 = generate_chat_response("Hi")
    print(f"User: Hi\nBot: {res1['answer']}")
    assert "Hi!" in res1["answer"] or "Hello!" in res1["answer"], f"Unexpected answer for 'Hi': {res1['answer']}"
    assert "pressure" not in res1["answer"].lower() and "bar" not in res1["answer"].lower()
    assert "temperature" not in res1["answer"].lower() and "document" not in res1["answer"].lower()
    assert len(res1["sources"]) == 0
    print(">> Case 1 PASSED: Normal greeting returned without RAG or update logic.")

    # -------------------------------------------------------------
    # 2. Test "Hello"
    # -------------------------------------------------------------
    print("\n[Case 2] Testing: 'Hello'")
    res2 = generate_chat_response("Hello")
    print(f"User: Hello\nBot: {res2['answer']}")
    assert "Hello!" in res2["answer"] or "Hi!" in res2["answer"], f"Unexpected answer for 'Hello': {res2['answer']}"
    assert "pressure" not in res2["answer"].lower() and "bar" not in res2["answer"].lower()
    assert "temperature" not in res2["answer"].lower() and "document" not in res2["answer"].lower()
    assert len(res2["sources"]) == 0
    print(">> Case 2 PASSED: Normal greeting returned.")

    # -------------------------------------------------------------
    # 3. Test "How are you?"
    # -------------------------------------------------------------
    print("\n[Case 3] Testing: 'How are you?'")
    res3 = generate_chat_response("How are you?")
    print(f"User: How are you?\nBot: {res3['answer']}")
    assert "doing well" in res3["answer"].lower() or "how can i help" in res3["answer"].lower()
    assert "bar" not in res3["answer"].lower() and "correction" not in res3["answer"].lower()
    assert len(res3["sources"]) == 0
    print(">> Case 3 PASSED: Polite conversation returned.")

    # -------------------------------------------------------------
    # 4. Test "Thank you"
    # -------------------------------------------------------------
    print("\n[Case 4] Testing: 'Thank you'")
    res4 = generate_chat_response("Thank you")
    print(f"User: Thank you\nBot: {res4['answer']}")
    assert "welcome" in res4["answer"].lower()
    assert len(res4["sources"]) == 0
    print(">> Case 4 PASSED: Courtesy response returned.")

    # -------------------------------------------------------------
    # 5. Test "What is F32?"
    # -------------------------------------------------------------
    print("\n[Case 5] Testing: 'What is F32?'")
    res5 = generate_chat_response("What is F32?")
    print(f"User: What is F32?\nBot:\n{res5['answer']}")
    assert "f32" in res5["answer"].lower() or "circulation" in res5["answer"].lower()
    assert "04_Heating_System_Fault_Codes_Demo.pdf" in res5["answer"] or any("04_Heating_System" in s["document_name"] for s in res5["sources"])
    assert "update the temperature" not in res5["answer"].lower()
    print(">> Case 5 PASSED: Normal technical answer from fault code document.")

    # -------------------------------------------------------------
    # 6. Test "What causes low pressure?"
    # -------------------------------------------------------------
    print("\n[Case 6] Testing: 'What causes low pressure?'")
    res6 = generate_chat_response("What causes low pressure?")
    print(f"User: What causes low pressure?\nBot:\n{res6['answer']}")
    assert "leak" in res6["answer"].lower() or "water loss" in res6["answer"].lower() or "relief" in res6["answer"].lower()
    assert len(res6["sources"]) > 0
    assert "would you like to update" not in res6["answer"].lower()
    print(">> Case 6 PASSED: Normal RAG technical answer.")

    # -------------------------------------------------------------
    # 7. Test "How can I troubleshoot this?"
    # -------------------------------------------------------------
    print("\n[Case 7] Testing: 'How can I troubleshoot this?'")
    res7 = generate_chat_response("How can I troubleshoot this?")
    print(f"User: How can I troubleshoot this?\nBot:\n{res7['answer']}")
    assert len(res7["answer"]) > 0
    assert "would you like to update" not in res7["answer"].lower()
    print(">> Case 7 PASSED: Normal technical response.")

    # -------------------------------------------------------------
    # 8. Test "This answer is incorrect." -> DO NOT invent values!
    # -------------------------------------------------------------
    print("\n[Case 8] Testing: 'This answer is incorrect.' (Without value)")
    res8 = generate_chat_response("This answer is incorrect.")
    print(f"User: This answer is incorrect.\nBot: {res8['answer']}")
    assert "what should the correct" in res8["answer"].lower() or "what is the correct information" in res8["answer"].lower()
    # CRITICAL: Must NOT invent 1.0-1.5 or 1.2-1.8 or bar
    assert "1.0" not in res8["answer"] and "1.2" not in res8["answer"] and "1.5" not in res8["answer"] and "1.8" not in res8["answer"]
    assert not res8.get("is_correction_prompt", False)
    assert len(get_active_knowledge_updates()) == 0
    print(">> Case 8 PASSED: Bot asks for the correct information without inventing values!")

    # -------------------------------------------------------------
    # 9. Test "The pressure value is incorrect. The correct value is 1.2–1.8 bar."
    # -------------------------------------------------------------
    print("\n[Case 9] Testing: 'The pressure value is incorrect. The correct value is 1.2–1.8 bar.'")
    conv9_id = create_conversation("Test 9")
    # First ask a baseline question
    generate_chat_response("What is the typical cold fill pressure?", conversation_id=conv9_id)
    res9 = generate_chat_response("The pressure value is incorrect. The correct value is 1.2–1.8 bar.", conversation_id=conv9_id)
    print(f"User: The pressure value is incorrect. The correct value is 1.2–1.8 bar.\nBot:\n{res9['answer']}")
    assert "1.2" in res9["answer"] and "1.8" in res9["answer"]
    assert "save this correction" in res9["answer"].lower()
    assert res9.get("is_correction_prompt", True)
    delete_conversation(conv9_id)
    print(">> Case 9 PASSED: Started confirmation workflow with extracted value.")

    # -------------------------------------------------------------
    # 10. Test "Update the document: pressure should be 1.2–1.8 bar."
    # -------------------------------------------------------------
    print("\n[Case 10] Testing: 'Update the document: pressure should be 1.2–1.8 bar.'")
    conv10_id = create_conversation("Test 10")
    generate_chat_response("What is the typical cold fill pressure?", conversation_id=conv10_id)
    res10 = generate_chat_response("Update the document: pressure should be 1.2–1.8 bar.", conversation_id=conv10_id)
    print(f"User: Update the document: pressure should be 1.2–1.8 bar.\nBot:\n{res10['answer']}")
    assert "1.2" in res10["answer"] and "1.8" in res10["answer"]
    assert "save this correction" in res10["answer"].lower()
    assert res10.get("is_correction_prompt", True)
    print(">> Case 10 PASSED: Update document workflow started.")

    # -------------------------------------------------------------
    # 11. Test "Yes" -> Confirm ONLY when update is pending
    # -------------------------------------------------------------
    print("\n[Case 11] Testing: 'Yes'")
    # A. With pending update:
    res11_a = generate_chat_response("Yes", conversation_id=conv10_id)
    print(f"User: Yes (with pending update)\nBot: {res11_a['answer']}")
    assert "done" in res11_a["answer"].lower() and "saved" in res11_a["answer"].lower()
    active_updates = get_active_knowledge_updates()
    assert len(active_updates) == 1
    print(">> 11A PASSED: Confirmed pending update.")

    # B. Without pending update in a fresh conversation:
    conv11_b = create_conversation("Test 11b")
    res11_b = generate_chat_response("Yes", conversation_id=conv11_b)
    print(f"User: Yes (NO pending update)\nBot: {res11_b['answer']}")
    assert "saved" not in res11_b["answer"].lower() and "correction" not in res11_b["answer"].lower()
    delete_conversation(conv10_id)
    delete_conversation(conv11_b)
    print(">> 11B PASSED: 'Yes' in normal conversation does NOT trigger knowledge update!")

    # -------------------------------------------------------------
    # 12. Test "Cancel" -> Cancel ONLY when update is pending
    # -------------------------------------------------------------
    print("\n[Case 12] Testing: 'Cancel'")
    # A. With pending update:
    conv12_a = create_conversation("Test 12a")
    generate_chat_response("The pressure should be 2.0 bar.", conversation_id=conv12_a)
    res12_a = generate_chat_response("Cancel", conversation_id=conv12_a)
    print(f"User: Cancel (with pending update)\nBot: {res12_a['answer']}")
    assert "cancelled" in res12_a["answer"].lower()
    print(">> 12A PASSED: Cancelled pending update.")

    # B. Without pending update:
    conv12_b = create_conversation("Test 12b")
    res12_b = generate_chat_response("Cancel", conversation_id=conv12_b)
    print(f"User: Cancel (NO pending update)\nBot: {res12_b['answer']}")
    assert "cancelled and was not saved" not in res12_b["answer"].lower()
    delete_conversation(conv12_a)
    delete_conversation(conv12_b)
    print(">> 12B PASSED: 'Cancel' in normal conversation handled safely.")

    # Clean up any leftover test updates
    for u in get_all_knowledge_updates():
        delete_knowledge_update(u["id"])

    print("\n" + "=" * 75)
    print("ALL 12 TEST CASES PASSED PERFECTLY!")
    print("=" * 75)

if __name__ == "__main__":
    test_intent_separation()
