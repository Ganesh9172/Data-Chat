import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, get_stats, get_all_documents, get_all_qa_pairs
from backend.knowledge import process_pdf_file, process_qa_entry
from backend.retrieval import retrieve_relevant_knowledge
from backend.chat import generate_chat_response
from backend.models import PowerBIReportContext

def run_tests():
    print("=== 1. Initializing Database ===")
    init_db()
    stats = get_stats()
    print("Initial stats:", stats)

    print("\n=== 2. Ingesting Firebird Technical Guide ===")
    pdf_path = os.path.join("data", "knowledge", "01_Hydronic_Water_Pressure_Field_Guide.pdf")
    if os.path.exists(pdf_path):
        res = process_pdf_file(pdf_path, "01_Hydronic_Water_Pressure_Field_Guide.pdf")
        print(f"Indexed PDF: {res['document_name']}, Chunks: {res['chunk_count']}, Pages: {res['pages']}")

    print("\n=== 3. Adding Approved Q&A ===")
    qa_res = process_qa_entry(
        question="What is the minimum static cold pressure required for a two-storey house?",
        answer="Minimum 1.1 to 1.2 bar to maintain positive head pressure on top floor emitters.",
        source="01_Hydronic_Water_Pressure_Field_Guide.pdf"
    )
    print("Indexed Q&A:", qa_res["question"])

    print("\n=== 4. Testing Retrieval for Pressure Question ===")
    query1 = "The boiler pressure is 0.7 bar when cold. What to check?"
    results1 = retrieve_relevant_knowledge(query1, top_k=4)
    print(f"Query: '{query1}' -> Retrieved {len(results1)} chunks:")
    for r in results1:
        print(f"  - Source: {r['document_name']} | Page: {r.get('page_number')} | Sim: {r['similarity']}")
        print(f"    Snippet: {r['snippet']}")

    assert len(results1) > 0, "Failed to retrieve relevant chunks"

    print("\n=== 5. Testing Retrieval for Approved Q&A ===")
    query2 = "What is the minimum cold pressure for a 2 storey house?"
    results2 = retrieve_relevant_knowledge(query2, top_k=3)
    print(f"Query: '{query2}' -> Retrieved {len(results2)} matches:")
    for r in results2:
        print(f"  - Source: {r['document_name']} | Sim: {r['similarity']}")
        print(f"    Snippet: {r['snippet']}")

    print("\n=== 6. Testing Chat Response & Citations ===")
    chat_res1 = generate_chat_response(query1)
    print("Answer:")
    print(chat_res1["answer"][:300] + "...")
    print("Sources:", [s["document_name"] for s in chat_res1["sources"]])
    assert len(chat_res1["sources"]) > 0

    print("\n=== 7. Testing Conversational Memory Follow-up ===")
    conv_id = chat_res1["conversation_id"]
    follow_up = "What should I check next?"
    chat_res2 = generate_chat_response(follow_up, conversation_id=conv_id)
    print(f"Follow-up: '{follow_up}'")
    print("Answer:")
    print(chat_res2["answer"][:300] + "...")
    print("Sources:", [s["document_name"] for s in chat_res2["sources"]])

    print("\n=== 8. Testing Unknown Query (Out of Knowledge Base) ===")
    unknown_query = "What is the capital of Mars and who is its president?"
    chat_unknown = generate_chat_response(unknown_query)
    print(f"Unknown Query Answer:\n{chat_unknown['answer']}")
    print(f"Sources count: {len(chat_unknown['sources'])}")

    print("\n=== 9. Testing Power BI Report Context ===")
    pbi_context = PowerBIReportContext(
        report_name="Firebird Fleet Diagnostics",
        visual_title="Circuit Pressure & Thermal Delta-T Monitor",
        selected_filters={"Appliance": "Heating Unit X24", "Zone": "Domestic Central Heating"},
        data_summary="Observed Flow 68°C / Return 47°C (Delta-T 21°C) with cold static pressure 0.7 bar before service."
    )
    chat_pbi = generate_chat_response(
        "Is this temperature alert expected during initial boiler startup?",
        report_context=pbi_context
    )
    print("Power BI Chat Answer:\n", chat_pbi["answer"][:300] + "...")

    print("\n=== All Backend Tests Passed Successfully! ===")

if __name__ == "__main__":
    run_tests()
