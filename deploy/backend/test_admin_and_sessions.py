import os
import sys
import unittest
import json
from fastapi.testclient import TestClient
from dotenv import load_dotenv

DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(DOTENV_PATH, override=True)

from backend.main import app
from backend.database import get_all_documents, get_all_qa_pairs, delete_document, delete_qa_pair, delete_conversation

client = TestClient(app)

class TestAdminAndSessionPrivacy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_pass = os.getenv("ADMIN_PASSWORD", "AdminSecurePass123!")
        cls.admin_user = os.getenv("ADMIN_USERNAME", "admin")

    def test_01_visitor_chat_creation_and_rag(self):
        """Verify normal visitor can chat without an account and get RAG answers."""
        headers = {"X-Session-ID": "sess_visitor_alpha"}
        res = client.post(
            "/api/chat",
            headers=headers,
            json={"message": "The boiler pressure is 0.7 bar when cold. Is that too low?"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("conversation_id", data)
        self.assertIn("answer", data)
        self.assertTrue(len(data["answer"]) > 20)
        # Verify citations are present
        self.assertIn("sources", data)
        self.assertTrue(len(data["sources"]) > 0)
        
        TestAdminAndSessionPrivacy.conv_alpha_id = data["conversation_id"]

    def test_02_visitor_session_isolation_chats_list(self):
        """Verify visitor only sees chats for their own session."""
        # Visitor Alpha sees their conversation
        res_a = client.get("/api/chats", headers={"X-Session-ID": "sess_visitor_alpha"})
        self.assertEqual(res_a.status_code, 200)
        chats_a = res_a.json()
        chat_ids_a = [c["id"] for c in chats_a]
        self.assertIn(TestAdminAndSessionPrivacy.conv_alpha_id, chat_ids_a)

        # Visitor Beta with different session ID sees NO chats from Alpha
        res_b = client.get("/api/chats", headers={"X-Session-ID": "sess_visitor_beta"})
        self.assertEqual(res_b.status_code, 200)
        chats_b = res_b.json()
        chat_ids_b = [c["id"] for c in chats_b]
        self.assertNotIn(TestAdminAndSessionPrivacy.conv_alpha_id, chat_ids_b)

        # Anonymous caller without session ID receives empty list (no global chat leakage)
        res_anon = client.get("/api/chats")
        self.assertEqual(res_anon.status_code, 200)
        self.assertEqual(len(res_anon.json()), 0)

    def test_03_visitor_cannot_access_other_user_conversation(self):
        """Verify backend rejects cross-session conversation access with 403."""
        # Visitor Beta attempts to fetch Visitor Alpha's conversation
        res = client.get(
            f"/api/chats/{TestAdminAndSessionPrivacy.conv_alpha_id}",
            headers={"X-Session-ID": "sess_visitor_beta"}
        )
        self.assertEqual(res.status_code, 403)

        # Visitor Beta attempts to delete Visitor Alpha's conversation
        del_res = client.delete(
            f"/api/chats/{TestAdminAndSessionPrivacy.conv_alpha_id}",
            headers={"X-Session-ID": "sess_visitor_beta"}
        )
        self.assertEqual(del_res.status_code, 403)

        # Visitor Beta attempts to post messages into Visitor Alpha's conversation
        post_res = client.post(
            "/api/chat",
            headers={"X-Session-ID": "sess_visitor_beta"},
            json={"message": "Hijack attempt", "conversation_id": TestAdminAndSessionPrivacy.conv_alpha_id}
        )
        self.assertEqual(post_res.status_code, 403)

    def test_04_normal_visitor_cannot_upload_document(self):
        """Verify normal visitor cannot upload documents (401/403)."""
        files = {"file": ("test_forbidden.txt", b"Forbidden content", "text/plain")}
        res = client.post("/api/knowledge/upload", files=files, headers={"X-Session-ID": "sess_visitor_alpha"})
        self.assertIn(res.status_code, [401, 403])

    def test_05_normal_visitor_cannot_delete_document(self):
        """Verify normal visitor cannot delete knowledge documents (401/403)."""
        res = client.delete("/api/knowledge/some-doc-id", headers={"X-Session-ID": "sess_visitor_alpha"})
        self.assertIn(res.status_code, [401, 403])

    def test_06_normal_visitor_cannot_add_qa(self):
        """Verify normal visitor cannot add knowledge Q&A (401/403)."""
        res = client.post(
            "/api/knowledge/qa",
            headers={"X-Session-ID": "sess_visitor_alpha"},
            json={"question": "Test Q?", "answer": "Test A", "source": "Test"}
        )
        self.assertIn(res.status_code, [401, 403])

    def test_07_normal_visitor_cannot_modify_knowledge_updates(self):
        """Verify normal visitor cannot create or revert knowledge updates (401/403)."""
        res = client.post(
            "/api/knowledge/updates",
            headers={"X-Session-ID": "sess_visitor_alpha"},
            json={"original_information": "old", "corrected_information": "new"}
        )
        self.assertIn(res.status_code, [401, 403])

    def test_08_admin_authentication(self):
        """Verify admin login with environment variable password."""
        # Wrong password fails
        bad_res = client.post("/api/admin/login", json={"password": "WrongPassword123!"})
        self.assertEqual(bad_res.status_code, 401)

        # Correct password succeeds
        good_res = client.post(
            "/api/admin/login",
            json={"password": self.admin_pass, "username": self.admin_user}
        )
        self.assertEqual(good_res.status_code, 200)
        data = good_res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["role"], "ADMIN")

        TestAdminAndSessionPrivacy.admin_token = data["access_token"]

        # Verify /api/admin/me
        me_res = client.get(
            "/api/admin/me",
            headers={"Authorization": f"Bearer {TestAdminAndSessionPrivacy.admin_token}"}
        )
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["role"], "ADMIN")

    def test_09_admin_can_upload_and_delete_document(self):
        """Verify admin can upload a document and delete it."""
        admin_headers = {"Authorization": f"Bearer {TestAdminAndSessionPrivacy.admin_token}"}

        # Admin upload
        test_filename = "admin_verify_doc.txt"
        files = {"file": (test_filename, b"Hydronic heating pressure safety operating limit is 3.0 bar.", "text/plain")}
        up_res = client.post("/api/knowledge/upload", files=files, headers=admin_headers)
        self.assertEqual(up_res.status_code, 200)
        up_data = up_res.json()
        self.assertEqual(up_data["status"], "success")

        # Verify document exists in list
        kb_res = client.get("/api/knowledge", headers=admin_headers)
        self.assertEqual(kb_res.status_code, 200)
        docs = kb_res.json().get("documents", [])
        uploaded_doc = next((d for d in docs if d["name"] == test_filename), None)
        self.assertIsNotNone(uploaded_doc)

        # Admin delete
        del_res = client.delete(f"/api/knowledge/{uploaded_doc['id']}", headers=admin_headers)
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["status"], "success")

    def test_10_admin_can_add_and_delete_qa(self):
        """Verify admin can add approved Q&A and delete it."""
        admin_headers = {"Authorization": f"Bearer {TestAdminAndSessionPrivacy.admin_token}"}

        # Admin add Q&A
        qa_payload = {
            "question": "What is the expansion vessel pre-charge standard?",
            "answer": "Standard pre-charge is 1.0 bar nitrogen for typical domestic systems.",
            "source": "Admin Technical Manual SOP"
        }
        res = client.post("/api/knowledge/qa", headers=admin_headers, json=qa_payload)
        self.assertEqual(res.status_code, 200)

        # Find the QA id and delete
        kb_res = client.get("/api/knowledge", headers=admin_headers)
        qas = kb_res.json().get("qa_pairs", [])
        qa_item = next((q for q in qas if q["question"] == qa_payload["question"]), None)
        self.assertIsNotNone(qa_item)

        del_res = client.delete(f"/api/knowledge/{qa_item['id']}", headers=admin_headers)
        self.assertEqual(del_res.status_code, 200)

    def test_11_admin_can_view_all_chats(self):
        """Verify admin can view conversations across sessions."""
        admin_headers = {"Authorization": f"Bearer {TestAdminAndSessionPrivacy.admin_token}"}
        res = client.get("/api/chats", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        chats = res.json()
        chat_ids = [c["id"] for c in chats]
        self.assertIn(TestAdminAndSessionPrivacy.conv_alpha_id, chat_ids)

    @classmethod
    def tearDownClass(cls):
        # Clean up test conversation
        if hasattr(cls, 'conv_alpha_id'):
            delete_conversation(cls.conv_alpha_id, is_admin=True)

if __name__ == "__main__":
    unittest.main()
