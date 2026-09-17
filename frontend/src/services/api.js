const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to connect to Firebird AI service');
  return res.json();
}

export async function getChats() {
  const res = await fetch(`${API_BASE}/chats`);
  if (!res.ok) throw new Error('Failed to load conversations');
  return res.json();
}

export async function createChat(title = 'New Conversation') {
  const res = await fetch(`${API_BASE}/chats`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title })
  });
  if (!res.ok) throw new Error('Failed to create new conversation');
  return res.json();
}

export async function getChat(chatId) {
  const res = await fetch(`${API_BASE}/chats/${chatId}`);
  if (!res.ok) throw new Error('Failed to load chat history');
  return res.json();
}

export async function deleteChat(chatId) {
  const res = await fetch(`${API_BASE}/chats/${chatId}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error('Failed to delete conversation');
  return res.json();
}

export async function sendChatMessage(message, conversationId = null, reportContext = null) {
  const payload = { message };
  if (conversationId) payload.conversation_id = conversationId;
  if (reportContext) payload.report_context = reportContext;

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate answer from knowledge base');
  }
  return res.json();
}

export async function getKnowledgeBase() {
  const res = await fetch(`${API_BASE}/knowledge`);
  if (!res.ok) throw new Error('Failed to fetch knowledge base items');
  return res.json();
}

export async function uploadKnowledgeDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/knowledge/upload`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to upload document');
  }
  return res.json();
}

export async function addQAPair(question, answer, source = 'User Approved Q&A') {
  const res = await fetch(`${API_BASE}/knowledge/qa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, answer, source })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to add Q&A to knowledge base');
  }
  return res.json();
}

export async function deleteKnowledgeItem(id) {
  const res = await fetch(`${API_BASE}/knowledge/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error('Failed to delete knowledge item');
  return res.json();
}

export async function getKnowledgeUpdates() {
  const res = await fetch(`${API_BASE}/knowledge/updates`);
  if (!res.ok) throw new Error('Failed to fetch knowledge updates');
  return res.json();
}

export async function revertKnowledgeUpdate(id) {
  const res = await fetch(`${API_BASE}/knowledge/updates/${id}/revert`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to revert knowledge update');
  return res.json();
}

export async function deleteKnowledgeUpdate(id) {
  const res = await fetch(`${API_BASE}/knowledge/updates/${id}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error('Failed to delete knowledge update');
  return res.json();
}
