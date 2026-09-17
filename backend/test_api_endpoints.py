import sys
import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

from backend.main import app

def test_api():
    print("=" * 70)
    print("FIREBIRD AI — FASTAPI API ENDPOINTS VERIFICATION")
    print("=" * 70)

    client = TestClient(app)

    # 1. Health check
    print("\n1. Testing GET /api/health...")
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    health_data = resp.json()
    print("Health response:", health_data)
    assert health_data["status"] == "online"
    assert health_data["database"] == "JSON File Storage"
    assert health_data["stats"]["documents"] >= 6
    print(">> Health check PASSED!")

    # 2. List Knowledge
    print("\n2. Testing GET /api/knowledge...")
    resp = client.get("/api/knowledge")
    assert resp.status_code == 200
    kb_data = resp.json()
    print(f"Indexed documents: {len(kb_data['documents'])}, QA pairs: {len(kb_data['qa_pairs'])}, Updates: {len(kb_data['knowledge_updates'])}")
    assert len(kb_data["documents"]) >= 6
    print(">> List knowledge PASSED!")

    # 3. Create & List Chats
    print("\n3. Testing Conversation management endpoints...")
    resp = client.post("/api/chats", json={"title": "Test Chat API"})
    assert resp.status_code == 200
    chat_info = resp.json()
    chat_id = chat_info["id"]
    print(f"Created chat: {chat_id}")

    resp = client.get(f"/api/chats/{chat_id}")
    assert resp.status_code == 200
    conv_data = resp.json()
    assert conv_data["title"] == "Test Chat API"
    print(">> Conversation created and retrieved successfully!")

    # 4. Chat Endpoint
    print("\n4. Testing POST /api/chat...")
    chat_payload = {
        "message": "What is the typical cold fill pressure?",
        "conversation_id": chat_id
    }
    resp = client.post("/api/chat", json=chat_payload)
    assert resp.status_code == 200
    chat_res = resp.json()
    print("Chat answer:", chat_res["answer"][:120] + "...")
    assert len(chat_res["answer"]) > 0
    print(">> Chat endpoint PASSED!")

    # 5. Knowledge Update Endpoints (CRUD)
    print("\n5. Testing Knowledge Update REST endpoints...")
    update_payload = {
        "original_information": "cold pressure range 1.0-1.5 bar",
        "corrected_information": "cold pressure range 1.3-1.7 bar",
        "source_document": "01_Hydronic_Water_Pressure_Field_Guide.pdf",
        "source_page": 1,
        "reason": "REST API Test update",
        "status": "approved"
    }
    resp = client.post("/api/knowledge/updates", json=update_payload)
    assert resp.status_code == 200
    ku_data = resp.json()
    ku_id = ku_data["id"]
    print(f"Created Knowledge Update: {ku_id} (Update #{ku_data.get('update_number')})")

    # List updates
    resp = client.get("/api/knowledge/updates")
    assert resp.status_code == 200
    updates_list = resp.json()
    assert any(u["id"] == ku_id for u in updates_list)

    # Revert update
    resp = client.post(f"/api/knowledge/updates/{ku_id}/revert")
    assert resp.status_code == 200
    print(">> Update reverted successfully!")

    # Delete update
    resp = client.delete(f"/api/knowledge/updates/{ku_id}")
    assert resp.status_code == 200
    print(">> Update deleted successfully!")

    # Clean up chat
    resp = client.delete(f"/api/chats/{chat_id}")
    assert resp.status_code == 200
    print(">> Test chat deleted successfully!")

    print("\n" + "=" * 70)
    print("ALL FASTAPI ENDPOINTS VERIFIED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_api()
