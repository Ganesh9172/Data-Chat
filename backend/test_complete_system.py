import os
import sys
import hashlib
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

from backend.database import (
    init_db,
    get_stats,
    get_all_documents,
    get_all_chunks_with_embeddings,
    create_conversation,
    get_conversation,
    delete_conversation,
    get_all_knowledge_updates,
    get_active_knowledge_updates,
    create_knowledge_update,
    approve_knowledge_update,
    revert_knowledge_update,
    delete_knowledge_update
)
from backend.chat import generate_chat_response
from backend.retrieval import retrieve_relevant_knowledge

PDF_FILES = [
    "01_Hydronic_Water_Pressure_Field_Guide.pdf",
    "02_Low_Water_Pressure_Troubleshooting.pdf",
    "03_Flow_Temperature_DeltaT_and_Circulation.pdf",
    "04_Heating_System_Fault_Codes_Demo.pdf",
    "05_Field_Plumber_FAQ_Knowledge_Base.pdf",
    "06_Commissioning_and_Service_Record_Demo.pdf"
]

def get_file_checksum(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def run_tests():
    print("=" * 75)
    print("FIREBIRD AI — COMPREHENSIVE BACKEND & TWO-WAY KNOWLEDGE VERIFICATION")
    print("=" * 75)

    # 1. Verify Microsoft SQL Server Database & Stats
    print("\n--- TEST 1: SQL Server Connection & Initial Stats ---")
    init_db()
    stats = get_stats()
    print("SQL Server current stats:", stats)
    assert stats["documents"] >= 6, "Expected at least 6 documents in SQL Server"
    assert stats["chunks"] >= 29, "Expected at least 29 chunks in SQL Server"
    print(">> TEST 1 PASSED: SQL Server is connected and populated!")

    # 2. Record initial PDF checksums to ensure immutability
    print("\n--- TEST 2: Original PDF Immutability Baseline ---")
    initial_checksums = {}
    knowledge_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "knowledge")
    for pdf in PDF_FILES:
        pdf_path = os.path.join(knowledge_dir, pdf)
        assert os.path.exists(pdf_path), f"PDF {pdf} not found!"
        initial_checksums[pdf] = get_file_checksum(pdf_path)
    print(f">> TEST 2 PASSED: All {len(PDF_FILES)} source PDFs verified and hashed.")

    # 3. Clean up any previous test updates so we start from a clean baseline
    for u in get_all_knowledge_updates():
        delete_knowledge_update(u["id"])

    # 4. Ask Baseline Question (Normal PDF Knowledge)
    print("\n--- TEST 3: Baseline Normal Question (Before Correction) ---")
    test_conv_id = create_conversation(title="Pressure Calibration Test")
    
    q1 = "What is the typical cold fill pressure for the system?"
    resp1 = generate_chat_response(q1, conversation_id=test_conv_id)
    print(f"User: {q1}")
    print(f"AI:\n{resp1['answer']}")
    print(f"Sources: {[s['document_name'] for s in resp1['sources']]}")
    
    assert "1.0" in resp1["answer"] and "1.5" in resp1["answer"], "Baseline answer should mention 1.0–1.5 bar"
    assert any("01_Hydronic_Water_Pressure_Field_Guide.pdf" in s["document_name"] for s in resp1["sources"])
    print(">> TEST 3 PASSED: Baseline answer is grounded in original PDF.")

    # 5. Casual feedback - verify safety (no modification or staging)
    print("\n--- TEST 4: Casual Remark Safety Check ---")
    q_casual = "That seems wrong."
    resp_casual = generate_chat_response(q_casual, conversation_id=test_conv_id)
    print(f"User: {q_casual}")
    print(f"AI:\n{resp_casual['answer']}")
    
    active_updates = get_active_knowledge_updates()
    assert len(active_updates) == 0, "Casual remark should NOT create active knowledge update!"
    assert not resp_casual.get("is_correction_prompt", False), "Casual remark should not prompt confirmation"
    print(">> TEST 4 PASSED: Casual remark did NOT alter or stage knowledge updates.")

    # 6. User submits specific correction
    print("\n--- TEST 5: Propose Specific Knowledge Correction ---")
    q_corr = "This is incorrect. For our latest system it should be 1.2–1.8 bar. Update the document."
    resp_corr = generate_chat_response(q_corr, conversation_id=test_conv_id)
    print(f"User: {q_corr}")
    print(f"AI:\n{resp_corr['answer']}")
    
    assert "1.2" in resp_corr["answer"] and "1.8" in resp_corr["answer"], "AI should recognize the proposed 1.2–1.8 bar"
    assert "Should I save this correction" in resp_corr["answer"], "AI should ask for confirmation"
    assert resp_corr.get("is_correction_prompt", False) or resp_corr.get("pending_update_id") is not None
    print(">> TEST 5 PASSED: AI identified proposed correction and requested confirmation.")

    # 7. User confirms correction
    print("\n--- TEST 6: Confirm Knowledge Correction ---")
    q_confirm = "Yes"
    resp_confirm = generate_chat_response(q_confirm, conversation_id=test_conv_id)
    print(f"User: {q_confirm}")
    print(f"AI:\n{resp_confirm['answer']}")
    
    assert "Done" in resp_confirm["answer"] and "saved" in resp_confirm["answer"], "AI should acknowledge saved correction"
    
    # Check SQL Server persistence
    active_updates = get_active_knowledge_updates()
    assert len(active_updates) == 1, f"Expected 1 active update in SQL Server, found {len(active_updates)}"
    saved_ku = active_updates[0]
    print(f"Verified SQL Server record: Update #{saved_ku.get('update_number')} | {saved_ku['corrected_information']} | Status: {saved_ku['status']}")
    assert "1.2" in saved_ku["corrected_information"] and "1.8" in saved_ku["corrected_information"]
    print(">> TEST 6 PASSED: Knowledge correction successfully approved and indexed in SQL Server!")

    # 8. Ask the same question again -> MUST use approved correction!
    print("\n--- TEST 7: Query After Correction (Must Use Approved Update) ---")
    q_again = "What is the typical cold fill pressure for the system?"
    resp_again = generate_chat_response(q_again, conversation_id=test_conv_id)
    print(f"User: {q_again}")
    print(f"AI:\n{resp_again['answer']}")
    print(f"Sources: {[s['document_name'] for s in resp_again['sources']]}")
    
    assert "1.2" in resp_again["answer"] and "1.8" in resp_again["answer"], f"AI should use the updated 1.2–1.8 bar! Got: {resp_again['answer']}"
    assert "Knowledge Base Update" in resp_again["answer"] or any("Knowledge Base Update" in s["document_name"] for s in resp_again["sources"])
    assert "01_Hydronic_Water_Pressure_Field_Guide.pdf" in resp_again["answer"] or any("01_Hydronic" in (s.get("original_source") or "") for s in resp_again["sources"])
    print(">> TEST 7 PASSED: Future question successfully used the approved correction with proper citation!")

    # 9. Verify PDFs remain strictly unchanged on disk
    print("\n--- TEST 8: Verify Original PDFs Remain 100% Immutable ---")
    for pdf in PDF_FILES:
        pdf_path = os.path.join(knowledge_dir, pdf)
        curr_checksum = get_file_checksum(pdf_path)
        assert curr_checksum == initial_checksums[pdf], f"CRITICAL: PDF {pdf} was modified on disk!"
    print(">> TEST 8 PASSED: All 6 original PDF files are completely unmodified and immutable.")

    # 10. Test Cancellation Workflow
    print("\n--- TEST 9: Knowledge Correction Cancellation ---")
    conv2_id = create_conversation(title="Cancellation Test")
    generate_chat_response("What is the typical cold pressure?", conversation_id=conv2_id)
    generate_chat_response("This is wrong. Change it to 3.0 bar.", conversation_id=conv2_id)
    resp_cancel = generate_chat_response("Cancel", conversation_id=conv2_id)
    print(f"User: Cancel")
    print(f"AI:\n{resp_cancel['answer']}")
    assert "cancelled" in resp_cancel["answer"].lower()
    
    # Check that 3.0 bar update is NOT active
    for u in get_active_knowledge_updates():
        assert "3.0" not in u["corrected_information"], "Cancelled update should NOT be active!"
    print(">> TEST 9 PASSED: Cancellation correctly rejected update.")

    # 11. Test Revert Workflow
    print("\n--- TEST 10: Revert Knowledge Update ---")
    resp_revert = generate_chat_response("Revert the last update", conversation_id=test_conv_id)
    print(f"User: Revert the last update")
    print(f"AI:\n{resp_revert['answer']}")
    assert "reverted" in resp_revert["answer"].lower()
    
    # Query again -> Should be back to 1.0–1.5 bar
    resp_post_revert = generate_chat_response("What is the typical cold fill pressure for the system?", conversation_id=test_conv_id)
    print("Post-revert AI answer:\n", resp_post_revert["answer"])
    assert "1.0" in resp_post_revert["answer"] and "1.5" in resp_post_revert["answer"]
    print(">> TEST 10 PASSED: Revert restored baseline PDF knowledge.")

    # Clean up test conversations
    delete_conversation(test_conv_id)
    delete_conversation(conv2_id)

    print("\n" + "=" * 75)
    print("ALL TESTS COMPLETED SUCCESSFULLY! ZERO REGRESSIONS.")
    print("=" * 75)

if __name__ == "__main__":
    run_tests()
