import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import KnowledgeModal from './components/KnowledgeModal';
import LoginModal from './components/LoginModal';
import {
  getChats,
  getChat,
  deleteChat,
  sendChatMessage,
  getKnowledgeBase,
  checkHealth,
  checkAdmin,
  adminLogout,
  getSessionId
} from './services/api';

const PRESET_CONVERSATIONS = {
  'default-1': {
    id: 'default-1',
    title: 'System pressure looks normal, but there’s no heat going to one zone',
    messages: [
      {
        id: 'msg-user-1',
        role: 'user',
        content: "System pressure looks normal, but there’s no heat going to one zone. Where should I start?",
        created_at: new Date().toISOString()
      },
      {
        id: 'msg-ai-1',
        role: 'assistant',
        content: `The documents suggest starting with a basic check of the system's mechanical and flow conditions:

* Verify that all radiator valves (including TRVs) are open and not stuck.
* Look for trapped air in the zone – bleed the radiators if necessary.
* Confirm that circulation is working (pump running, no blockages).
* Check the balancing of the system to ensure the zone is receiving adequate flow.
* Clarify whether the problem is limited to a single emitter, a single zone, or the entire floor.

These steps are recommended for a situation where the pressure appears normal but a zone is not heating.

**Source:** 05_Field_Plumber_FAQ_Knowledge_Base.pdf, Page 1`,
        sources: [
          { document_name: '05_Field_Plumber_FAQ_Knowledge_Base.pdf', page_number: 1, snippet: 'Upstairs radiators are cold. Check system pressure/static head, air, valve positions, circulation and balancing.' }
        ],
        created_at: new Date().toISOString()
      }
    ]
  },
  'default-2': {
    id: 'default-2',
    title: 'The boiler pressure is 0.7 bar when cold',
    messages: [
      {
        id: 'msg-user-2',
        role: 'user',
        content: 'The boiler pressure is 0.7 bar when cold. Is that too low, and what should I check first?',
        created_at: new Date().toISOString()
      },
      {
        id: 'msg-ai-2',
        role: 'assistant',
        content: `Yes – 0.7 bar cold is below the normal cold-fill range (roughly 1.0–1.5 bar) and indicates low system pressure.

First check: confirm that the gauge is showing system-water pressure rather than domestic mains pressure. Then inspect accessible valves, visible pipework, and the pressure-relief discharge termination for signs of water loss before topping up.

**Sources:**
* 05_Field_Plumber_FAQ_Knowledge_Base.pdf, Page 1
* 02_Low_Water_Pressure_Troubleshooting.pdf, Page 1`,
        sources: [
          { document_name: '05_Field_Plumber_FAQ_Knowledge_Base.pdf', page_number: 1, snippet: 'Normal cold fill range 1.0-1.5 bar' },
          { document_name: '02_Low_Water_Pressure_Troubleshooting.pdf', page_number: 1, snippet: 'Confirm gauge is system water pressure' }
        ],
        related_video: {
          title: "How to Increase Boiler Pressure and Check Your Pressure Gauge",
          url: "https://www.youtube.com/watch?v=I3HgvV2mIqY",
          thumbnail_url: "https://i.ytimg.com/vi/I3HgvV2mIqY/hqdefault.jpg",
          video_id: "I3HgvV2mIqY"
        },
        created_at: new Date().toISOString()
      }
    ]
  }
};

export default function App() {
  const [isAdmin, setIsAdmin] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ documents: 6, chunks: 29, qa_pairs: 0 });
  const [toast, setToast] = useState(null);

  // Drawer & Modals
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isKnowledgeOpen, setIsKnowledgeOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);

  const showToast = (text) => {
    setToast(text);
    setTimeout(() => setToast(null), 3000);
  };

  const loadConversations = async () => {
    try {
      const data = await getChats();
      setConversations(data);
    } catch (e) {
      console.error('Failed to load conversations:', e);
    }
  };

  const loadStats = async () => {
    try {
      const kb = await getKnowledgeBase();
      if (kb?.stats) {
        setStats(kb.stats);
      }
    } catch (e) {
      console.error('Failed to load stats:', e);
    }
  };

  const initApp = async () => {
    // Ensure session ID is initialized for client
    getSessionId();

    // Check if user already holds a valid admin session
    try {
      const adminData = await checkAdmin();
      if (adminData && adminData.role === 'ADMIN') {
        setIsAdmin(true);
        loadStats();
      }
    } catch {
      setIsAdmin(false);
    }

    // Load visitor's conversations & verify health
    loadConversations();
    checkHealth().catch((e) => {
      console.warn('Backend service offline or starting:', e);
    });
  };

  useEffect(() => {
    initApp();
  }, []);

  const handleLoginSuccess = () => {
    setIsAdmin(true);
    setIsLoginOpen(false);
    showToast('Administrator mode unlocked');
    loadConversations();
    loadStats();
  };

  const handleLogout = () => {
    adminLogout();
    setIsAdmin(false);
    setIsKnowledgeOpen(false);
    showToast('Administrator signed out');
    loadConversations();
  };

  const handleSelectChat = async (id) => {
    setActiveChatId(id);

    if (PRESET_CONVERSATIONS[id]) {
      const preset = PRESET_CONVERSATIONS[id];
      setCurrentConversation(preset);
      setMessages(preset.messages);
      return;
    }

    setLoading(true);
    try {
      const fullConv = await getChat(id);
      setCurrentConversation(fullConv);
      setMessages(fullConv.messages || []);
    } catch (err) {
      console.error('Error fetching chat:', err);
      showToast('Failed to load conversation history');
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    setActiveChatId(null);
    setCurrentConversation(null);
    setMessages([]);
  };

  const handleDeleteChat = async (id) => {
    if (id.startsWith('default-')) {
      handleNewChat();
      return;
    }
    try {
      await deleteChat(id);
      if (activeChatId === id) {
        handleNewChat();
      }
      await loadConversations();
      showToast('Conversation deleted');
    } catch (err) {
      console.error('Failed to delete chat:', err);
      showToast('Failed to delete conversation');
    }
  };

  const handleSendMessage = async (text) => {
    if (!text.trim()) return;

    // Optimistically append user message
    const tempUserMsg = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setLoading(true);

    try {
      const convIdForBackend = activeChatId && !activeChatId.startsWith('default-') ? activeChatId : null;
      const response = await sendChatMessage(text, convIdForBackend);

      const aiMsg = {
        id: 'ai-' + Date.now(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources || [],
        related_video: response.related_video || null,
        created_at: new Date().toISOString()
      };
      setMessages((prev) => [...prev, aiMsg]);

      if (response.conversation_id) {
        setActiveChatId(response.conversation_id);
        setCurrentConversation({
          id: response.conversation_id,
          title: text.substring(0, 40)
        });
      }
      await loadConversations();
    } catch (err) {
      console.error('Chat error:', err);
      const errorMsg = {
        id: 'err-' + Date.now(),
        role: 'assistant',
        content: `Error: ${err.message || 'Unable to retrieve answer. Please verify backend connection.'}`,
        sources: [],
        created_at: new Date().toISOString()
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-root">
      {/* Slide-over Recent Chats Drawer */}
      <Sidebar
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        conversations={conversations}
        activeId={activeChatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        onOpenKnowledge={() => setIsKnowledgeOpen(true)}
        stats={stats}
        isAdmin={isAdmin}
        onLogout={handleLogout}
        onOpenLogin={() => setIsLoginOpen(true)}
      />

      {/* Main Chat Interface */}
      <ChatArea
        messages={messages}
        loading={loading}
        onSendMessage={handleSendMessage}
        onOpenKnowledge={() => setIsKnowledgeOpen(true)}
        onNewChat={handleNewChat}
        onToggleDrawer={() => setIsDrawerOpen((prev) => !prev)}
        isAdmin={isAdmin}
      />

      {/* Knowledge Base Modal (Admin Only) */}
      <KnowledgeModal
        isOpen={isKnowledgeOpen && isAdmin}
        onClose={() => setIsKnowledgeOpen(false)}
        onKnowledgeUpdated={loadStats}
        isAdmin={isAdmin}
      />

      {/* Admin Authentication Modal */}
      <LoginModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        onLoginSuccess={handleLoginSuccess}
      />

      {/* Toast Notification */}
      {toast && (
        <div className="toast-notification">
          {toast}
        </div>
      )}
    </div>
  );
}
