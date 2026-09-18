const RAW_API_URL = import.meta.env.VITE_API_URL;
export const API_BASE = RAW_API_URL
  ? `${RAW_API_URL.replace(/\/$/, '')}/api`
  : '/api';

/**
 * Retrieve or generate a cryptographically random session identifier.
 * Persisted in browser localStorage to isolate visitor conversations.
 */
export function getSessionId() {
  let sid = localStorage.getItem('firebird_session_id');
  if (!sid) {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      sid = 'sess_' + crypto.randomUUID();
    } else {
      sid = 'sess_' + Math.random().toString(36).substring(2, 12) + Date.now().toString(36);
    }
    localStorage.setItem('firebird_session_id', sid);
  }
  return sid;
}

/**
 * Admin JWT token management
 */
export function getAdminToken() {
  return localStorage.getItem('firebird_admin_token') || localStorage.getItem('firebird_token');
}

export function setAdminToken(token) {
  if (token) {
    localStorage.setItem('firebird_admin_token', token);
    localStorage.setItem('firebird_token', token);
  } else {
    localStorage.removeItem('firebird_admin_token');
    localStorage.removeItem('firebird_token');
  }
}

/**
 * Build request headers: automatically attaches X-Session-ID for chat privacy
 * and Authorization Bearer token if administrator is authenticated.
 */
function getHeaders(extraHeaders = {}) {
  const headers = {
    'X-Session-ID': getSessionId(),
    ...extraHeaders
  };
  const token = getAdminToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// --- Admin Authentication ---

export async function adminLogin(password, username = 'admin') {
  const res = await fetch(`${API_BASE}/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password, username })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Invalid admin credentials');
  }
  const data = await res.json();
  if (data.access_token) {
    setAdminToken(data.access_token);
  }
  return data;
}

// Backward-compatible alias
export const login = (emailOrUsername, password) => adminLogin(password, emailOrUsername);

export async function checkAdmin() {
  const token = getAdminToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_BASE}/admin/me`, {
      headers: getHeaders()
    });
    if (!res.ok) {
      setAdminToken(null);
      return null;
    }
    return await res.json();
  } catch {
    return null;
  }
}

// Backward-compatible alias
export const getMe = checkAdmin;

export function adminLogout() {
  setAdminToken(null);
}

// Backward-compatible alias
export const logout = adminLogout;

// --- Health ---

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to connect to Firebird AI service');
  return res.json();
}

// --- Chat & Session Conversations ---

export async function getChats() {
  const res = await fetch(`${API_BASE}/chats`, {
    headers: getHeaders()
  });
  if (!res.ok) throw new Error('Failed to load conversations');
  return res.json();
}

export async function createChat(title = 'New Conversation') {
  const res = await fetch(`${API_BASE}/chats`, {
    method: 'POST',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ title })
  });
  if (!res.ok) throw new Error('Failed to create new conversation');
  return res.json();
}

export async function getChat(chatId) {
  const res = await fetch(`${API_BASE}/chats/${chatId}`, {
    headers: getHeaders()
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to load chat history');
  }
  return res.json();
}

export async function deleteChat(chatId) {
  const res = await fetch(`${API_BASE}/chats/${chatId}`, {
    method: 'DELETE',
    headers: getHeaders()
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete conversation');
  }
  return res.json();
}

export async function sendChatMessage(message, conversationId = null, reportContext = null) {
  const payload = { message };
  if (conversationId) payload.conversation_id = conversationId;
  if (reportContext) payload.report_context = reportContext;

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate answer from knowledge base');
  }
  return res.json();
}

// --- Knowledge Base Operations (Admin-Protected) ---

export async function getKnowledgeBase() {
  const res = await fetch(`${API_BASE}/knowledge`, {
    headers: getHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch knowledge base items');
  return res.json();
}

export async function uploadKnowledgeDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const headers = getHeaders();
  // Do NOT set Content-Type header manually for FormData so boundary is generated
  delete headers['Content-Type'];

  const res = await fetch(`${API_BASE}/knowledge/upload`, {
    method: 'POST',
    headers: headers,
    body: formData
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to upload document: Admin access required');
  }
  return res.json();
}

export async function addQAPair(question, answer, source = 'Approved Technical Q&A') {
  const res = await fetch(`${API_BASE}/knowledge/qa`, {
    method: 'POST',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ question, answer, source })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to add Q&A: Admin access required');
  }
  return res.json();
}

export async function deleteKnowledgeItem(id) {
  const res = await fetch(`${API_BASE}/knowledge/${id}`, {
    method: 'DELETE',
    headers: getHeaders()
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete knowledge item: Admin access required');
  }
  return res.json();
}

export async function getKnowledgeUpdates() {
  const res = await fetch(`${API_BASE}/knowledge/updates`, {
    headers: getHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch knowledge updates');
  return res.json();
}

export async function revertKnowledgeUpdate(id) {
  const res = await fetch(`${API_BASE}/knowledge/updates/${id}/revert`, {
    method: 'POST',
    headers: getHeaders()
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to revert knowledge update');
  }
  return res.json();
}

export async function deleteKnowledgeUpdate(id) {
  const res = await fetch(`${API_BASE}/knowledge/updates/${id}`, {
    method: 'DELETE',
    headers: getHeaders()
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete knowledge update');
  }
  return res.json();
}
