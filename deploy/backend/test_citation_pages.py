import os
import sys
import re
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

from backend.database import init_db, create_conversation, delete_conversation
from backend.chat import generate_chat_response
from backend.retrieval import retrieve_relevant_knowledge

def test_citations():
    print("=" * 80)
    print("FIREBIRD AI — PAGE CITATION BUG VERIFICATION")
    print("=" * 80)

    init_db()

    test_cases = [
        {
            "name": "Dark-colored water (Page 25)",
            "query": "According to Idronics 32, what causes dark-colored water or fluid in a hydronic system?",
            "expected_doc": "Idronics_32_NA_Troubleshooting hydronic systems.pdf",
            "expected_page": 25
        },
        {
            "name": "Exterior corrosion (Page 35)",
            "query": "According to Idronics 32, what causes corrosion on the exterior of piping components?",
            "expected_doc": "Idronics_32_NA_Troubleshooting hydronic systems.pdf",
            "expected_page": 35
        },
        {
            "name": "Sub-atmospheric pressure / air vent (Page 17)",
            "query": "According to Idronics 32, what can cause sub-atmospheric pressure at a float air vent?",
            "expected_doc": "Idronics_32_NA_Troubleshooting hydronic systems.pdf",
            "expected_page": 17
        }
    ]

    all_passed = True

    for idx, tc in enumerate(test_cases, 1):
        conv_id = create_conversation(title=f"Citation Test {idx}")
        try:
            print(f"\n--- SUBTEST {idx}: {tc['name']} ---")
            print(f"Query: {tc['query']}")

            # Step 1: Check retrieval metadata directly
            chunks = retrieve_relevant_knowledge(tc["query"], top_k=5)
            print(f"Retrieved {len(chunks)} chunks:")
            target_chunks = [c for c in chunks if tc["expected_doc"] in c["document_name"]]
            for c in target_chunks:
                print(f"  - Doc: {c['document_name']} | Page: {c.get('page_number')} (start={c.get('page_start')}, end={c.get('page_end')}) | Score: {c.get('similarity_score', 0):.4f}")

            assert len(target_chunks) > 0, f"Expected to retrieve chunks from {tc['expected_doc']}"
            retrieved_pages = [c.get("page_number") for c in target_chunks]
            print(f"Retrieved pages for target document: {retrieved_pages}")
            assert tc["expected_page"] in retrieved_pages, f"Expected page {tc['expected_page']} in retrieved pages: {retrieved_pages}"

            # Step 2: Call chat endpoint / generate_chat_response
            resp = generate_chat_response(tc["query"], conversation_id=conv_id)
            answer = resp["answer"]
            sources = resp.get("sources", [])

            print("\nResponse preview:")
            print(answer[:300] + "...\n")
            print("Response sources array:")
            for s in sources:
                print(f"  - {s.get('document_name')}, Page: {s.get('page_number')} (display: {s.get('page_display', s.get('page_number'))})")

            # Step 3: Verify sources array
            idr_sources = [s for s in sources if tc["expected_doc"] in s["document_name"]]
            assert len(idr_sources) > 0, "Expected sources to include the target PDF"
            source_pages = [s.get("page_number") for s in idr_sources]
            print(f"Target document pages in sources array: {source_pages}")
            assert tc["expected_page"] in source_pages, f"Expected page {tc['expected_page']} in sources array, got {source_pages}"

            # Step 4: Verify text citations at bottom of answer
            print("\nChecking formatted citation block in answer text:")
            # Looking for Source: ... or Sources: ...
            assert "**Source" in answer, "Answer must include formatted **Source(s):** section"
            
            # Check that Page X is present and NOT Page 1 (when expected_page != 1)
            citation_lines = [l for l in answer.split("\n") if tc["expected_doc"] in l or "Page" in l]
            for cl in citation_lines:
                print(f"  Citation line: {cl}")

            expected_page_str = f"Page {tc['expected_page']}"
            assert expected_page_str in answer, f"Expected '{expected_page_str}' in markdown citation, but got:\n{answer}"
            
            # Check that expected_page is in the citation lines for this doc
            doc_citation_lines = [l for l in answer.split("\n") if tc["expected_doc"] in l]
            has_expected_page = any(f"Page {tc['expected_page']}" in l for l in doc_citation_lines)
            assert has_expected_page, f"Expected 'Page {tc['expected_page']}' in citation lines: {doc_citation_lines}"

            # Verify no line is hardcoded to Page 1 when Page 1 wasn't retrieved
            if 1 not in source_pages:
                for line in doc_citation_lines:
                    assert not re.search(r"\bPage 1\b", line), f"Found hardcoded 'Page 1' in: {line}"

            print(f">> SUBTEST {idx} PASSED! Citation accurately reflects Page {tc['expected_page']}.")
        finally:
            delete_conversation(conv_id)

    print("\n" + "=" * 80)
    print("ALL CITATION TESTS PASSED SUCCESSFULLY! NO HARDCODED PAGE 1.")
    print("=" * 80)

if __name__ == "__main__":
    test_citations()
