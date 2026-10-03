import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.chat import generate_chat_response

QUESTIONS = [
    {
        "id": 1,
        "question": "The boiler pressure is 0.7 bar when cold. Is that too low, and what should I check first?",
        "expected_status": "Supported",
        "expected_docs": ["01_Hydronic_Water_Pressure_Field_Guide.pdf", "05_Field_Plumber_FAQ_Knowledge_Base.pdf", "02_Low_Water_Pressure_Troubleshooting.pdf"]
    },
    {
        "id": 2,
        "question": "Pressure is 1.2 bar cold but rises to 2.8 bar when the heating is on. What could cause that?",
        "expected_status": "Supported",
        "expected_docs": ["01_Hydronic_Water_Pressure_Field_Guide.pdf", "05_Field_Plumber_FAQ_Knowledge_Base.pdf"]
    },
    {
        "id": 3,
        "question": "I topped the system up yesterday and today the pressure has dropped again. What should I investigate?",
        "expected_status": "Supported",
        "expected_docs": ["01_Hydronic_Water_Pressure_Field_Guide.pdf", "05_Field_Plumber_FAQ_Knowledge_Base.pdf"]
    },
    {
        "id": 4,
        "question": "The pressure-relief discharge pipe is dripping outside. What are the likely causes?",
        "expected_status": "Supported",
        "expected_docs": ["02_Low_Water_Pressure_Troubleshooting.pdf", "01_Hydronic_Water_Pressure_Field_Guide.pdf"]
    },
    {
        "id": 5,
        "question": "Upstairs radiators are cold but downstairs is heating normally. What should I check?",
        "expected_status": "Supported",
        "expected_docs": ["05_Field_Plumber_FAQ_Knowledge_Base.pdf"]
    },
    {
        "id": 6,
        "question": "One radiator is cold at the top but hot at the bottom. What does that indicate?",
        "expected_status": "Not Found",
        "expected_docs": []
    },
    {
        "id": 7,
        "question": "The radiator is hot at the top but much colder at the bottom. What could be wrong?",
        "expected_status": "Not Found",
        "expected_docs": []
    },
    {
        "id": 8,
        "question": "My flow temperature is 70°C and return is 45°C. Is that difference significant?",
        "expected_status": "Supported",
        "expected_docs": ["03_Flow_Temperature_DeltaT_and_Circulation.pdf"]
    },
    {
        "id": 9,
        "question": "The boiler is running but the house is taking much longer than normal to heat. What should I check?",
        "expected_status": "Supported",
        "expected_docs": ["05_Field_Plumber_FAQ_Knowledge_Base.pdf"]
    },
    {
        "id": 10,
        "question": "The pump sounds like it is running, but I'm getting poor circulation. What should I look at?",
        "expected_status": "Supported",
        "expected_docs": ["04_Heating_System_Fault_Codes_Demo.pdf", "03_Flow_Temperature_DeltaT_and_Circulation.pdf"]
    },
    {
        "id": 11,
        "question": "I'm hearing rushing-water noises through the radiators. What could be causing that?",
        "expected_status": "Supported",
        "expected_docs": ["03_Flow_Temperature_DeltaT_and_Circulation.pdf"]
    },
    {
        "id": 12,
        "question": "What does fault code F32 mean, and what checks should I perform before resetting anything?",
        "expected_status": "Supported",
        "expected_docs": ["04_Heating_System_Fault_Codes_Demo.pdf"]
    },
    {
        "id": 13,
        "question": "The boiler keeps reaching temperature and switching off quickly. What could cause short cycling?",
        "expected_status": "Not Found",
        "expected_docs": []
    },
    {
        "id": 14,
        "question": "The customer says they have to bleed the same radiator every few weeks. What could be causing that?",
        "expected_status": "Not Found",
        "expected_docs": []
    },
    {
        "id": 15,
        "question": "System pressure looks normal, but there's no heat going to one zone. Where should I start?",
        "expected_status": "Partially Supported",
        "expected_docs": ["03_Flow_Temperature_DeltaT_and_Circulation.pdf", "05_Field_Plumber_FAQ_Knowledge_Base.pdf"]
    },
    {
        "id": 16,
        "question": "After replacing a radiator, the system pressure keeps changing. What checks should I perform?",
        "expected_status": "Not Found",
        "expected_docs": []
    },
    {
        "id": 17,
        "question": "What information should I collect before calling Firebird technical support?",
        "expected_status": "Supported",
        "expected_docs": ["05_Field_Plumber_FAQ_Knowledge_Base.pdf"]
    },
    {
        "id": 18,
        "question": "What happened on the last service visit at this customer's house?",
        "expected_status": "Supported",
        "expected_docs": ["06_Commissioning_and_Service_Record_Demo.pdf"]
    },
    {
        "id": 19,
        "question": "Compare today's pressure readings with the readings from the previous service and tell me if anything looks abnormal.",
        "expected_status": "Partially Supported",
        "expected_docs": ["06_Commissioning_and_Service_Record_Demo.pdf"]
    },
    {
        "id": 20,
        "question": "Based on the pressure, flow temperature, return temperature and previous service history, what are the three most likely causes of this problem?",
        "expected_status": "Partially Supported",
        "expected_docs": ["06_Commissioning_and_Service_Record_Demo.pdf", "01_Hydronic_Water_Pressure_Field_Guide.pdf", "03_Flow_Temperature_DeltaT_and_Circulation.pdf"]
    }
]

def determine_status(answer: str, expected_status: str) -> str:
    ans_lower = answer.lower()
    if "couldn't find this information in the provided documents" in ans_lower:
        return "Not Found"
    if any(phrase in ans_lower for phrase in [
        "today's readings are not available",
        "today’s readings are not available",
        "today's pressure readings are not available",
        "today’s pressure readings are not available",
        "partially support",
        "partially supported",
        "cannot be confirmed",
        "not contained in any of the",
        "not contained in the provided",
        "don't state readings for",
        "documents do not contain current readings",
        "documents don't state"
    ]):
        return "Partially Supported"
    return "Supported"

def run_verification():
    print("=" * 70)
    print("FIREBIRD AI — 20-QUESTION BENCHMARK VERIFICATION")
    print("=" * 70)

    results = []
    supported_cnt = 0
    partially_cnt = 0
    not_found_cnt = 0
    pass_cnt = 0

    for item in QUESTIONS:
        qid = item["id"]
        qtext = item["question"]
        exp_status = item["expected_status"]

        print(f"\n--- Running Q{qid} ---")
        print(f"Question: {qtext}")

        # Execute single-turn response
        try:
            resp = generate_chat_response(qtext)
            ans = resp["answer"]
            sources = resp.get("sources", [])
        except Exception as e:
            ans = f"Error: {e}"
            sources = []

        actual_status = determine_status(ans, exp_status)

        if actual_status == "Supported":
            supported_cnt += 1
        elif actual_status == "Partially Supported":
            partially_cnt += 1
        else:
            not_found_cnt += 1

        is_correct_status = (actual_status == exp_status)
        if is_correct_status:
            pass_cnt += 1

        # Check citations
        cited_names = [s["document_name"] for s in sources]
        has_correct_citation = True
        if exp_status in ["Supported", "Partially Supported"] and item["expected_docs"]:
            # At least one of the expected docs should be cited
            has_correct_citation = any(ed in cited_names for ed in item["expected_docs"])

        status_flag = "PASS" if (is_correct_status and has_correct_citation) else "REVIEW"

        print(f"Answer:\n{ans}")
        print(f"Expected: {exp_status} | Got: {actual_status} | Result: {status_flag}")
        print(f"Cited Sources: {cited_names}")

        results.append({
            "id": qid,
            "question": qtext,
            "answer": ans,
            "expected_status": exp_status,
            "actual_status": actual_status,
            "status_flag": status_flag,
            "sources": cited_names
        })

        time.sleep(2.5) # rate-limit courtesy

    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"Total Questions: {len(QUESTIONS)}")
    print(f"Passed Accuracy Checks: {pass_cnt} / {len(QUESTIONS)}")
    print(f"Supported: {supported_cnt} (Expected: 12)")
    print(f"Partially Supported: {partially_cnt} (Expected: 3)")
    print(f"Not Found: {not_found_cnt} (Expected: 5)")

    # Save summary report as JSON
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "benchmark_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Detailed results saved to {report_path}")

    return results

if __name__ == "__main__":
    run_verification()
