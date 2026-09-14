import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import KnowledgeModal from './components/KnowledgeModal';
import PowerBIModal from './components/PowerBIModal';
import {
  getChats,
  getChat,
  deleteChat,
  sendChatMessage,
  getKnowledgeBase,
  checkHealth
} from './services/api';

const PRESET_CONVERSATIONS = {
  'default-1': {
    id: 'default-1',
    title: 'The boiler pressure is 0.7 bar when cold',
    messages: [
      {
        id: 'msg-user-1',
        role: 'user',
        content: 'The boiler pressure is 0.7 bar when cold. Upstairs radiators are cold while downstairs works — what to check?',
        created_at: new Date().toISOString()
      },
      {
        id: 'msg-ai-1',
        role: 'assistant',
        content: `A cold pressure of 0.7 bar is too low for a two-storey house. In a typical two-storey home, the system needs at least 1.1 to 1.2 bar to maintain enough pressure to push water to the upper radiators and prevent air pockets.

Here is what you should check:
* **System pressure:** Re-pressurize the heating system cold to about 1.2 bar using the filling loop.
* **Air in upstairs radiators:** Bleed the upstairs radiators to release trapped air, then recheck and top up the pressure if it drops.
* **Valves:** Check that the radiator thermostatic valves (TRVs) are not stuck closed, and verify that the motorized upstairs zone valve is opening properly.

**Sources:** 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1; 05_Field_Plumber_FAQ_Knowledge_Base.pdf, Page 1`,
        sources: [
          { document_name: '01_Hydronic_Water_Pressure_Field_Guide.pdf', page_number: 1, snippet: 'System cold pressure minimum operating static height' },
          { document_name: '05_Field_Plumber_FAQ_Knowledge_Base.pdf', page_number: 1, snippet: 'FAQ #19 Bleed upper radiator vent valves and check TRV pins' }
        ],
        created_at: new Date().toISOString()
      }
    ]
  },
  'default-2': {
    id: 'default-2',
    title: 'What happened on the last burner service?',
    messages: [
      {
        id: 'msg-user-2',
        role: 'user',
        content: 'What happened on the last burner service?',
        created_at: new Date().toISOString()
      },
      {
        id: 'msg-ai-2',
        role: 'assistant',
        content: `The last burner service for Heating Unit X24 was completed on September 8, 2026 (Service Report Ref: DEMO-FORM-007).

The service addressed customer reports of pressure drops over 2 to 3 days and cold upstairs radiators. The technician found a large cold-to-hot pressure swing caused by an improperly charged expansion vessel.

Key before and after measurements:
* **Cold Static Pressure:** Restored from 0.7 bar (critical deficit) to 1.2 bar (nominal).
* **Hot Operating Pressure:** Reduced from 2.7 bar to a stable 1.8 bar.
* **Flow / Return Temperatures:** Flow stabilized from 68°C to 66°C, and return from 47°C to 50°C (reducing Delta-T from 21°C to 16°C).

The technician recharged the expansion vessel pre-charge, restored cold pressure to 1.2 bar, and confirmed no external leaks were present.

**Source:** 06_Commissioning_and_Service_Record_Demo.pdf, Page 1`,
        sources: [
          { document_name: '06_Commissioning_and_Service_Record_Demo.pdf', page_number: 1, snippet: 'Service Ref DEMO-FORM-007 Heating Unit X24 before and after service readings' }
        ],
        created_at: new Date().toISOString()
      }
    ]
  },
  'default-3': {
    id: 'default-3',
    title: 'Why does pressure increase above 2.5 bar?',
    messages: [
      {
        id: 'msg-user-3',
        role: 'user',
        content: 'Why does pressure increase above 2.5 bar when heating?',
        created_at: new Date().toISOString()
      },
      {
        id: 'msg-ai-3',
        role: 'assistant',
        content: `Boiler pressure increases because the water expands as it gets hotter. In a sealed heating system, the expansion vessel absorbs this extra volume.

If the pressure rises excessively (above 2.5 bar), the expansion vessel has likely lost its air charge or the internal diaphragm is damaged. When pressure approaches 3.0 bar, the safety pressure relief valve (PRV) opens to discharge water, which often causes the system pressure to drop to zero once it cools down.

**Sources:** 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1; 02_Low_Water_Pressure_Troubleshooting.pdf, Page 1`,
        sources: [
          { document_name: '01_Hydronic_Water_Pressure_Field_Guide.pdf', page_number: 1, snippet: 'Water volumetric thermal expansion 3-4%' },
          { document_name: '02_Low_Water_Pressure_Troubleshooting.pdf', page_number: 1, snippet: 'Expansion vessel pre-charge and PRV discharge' }
        ],
        created_at: new Date().toISOString()
      }
    ]
  },
  'default-4': {
    id: 'default-4',
    title: 'What are the boiler fault codes?',
    messages: [
      {
        id: 'msg-user-4',
        role: 'user',
        content: 'What are the standard Firebird boiler fault codes (F04, F21, F32, F44) and first checks?',
        created_at: new Date().toISOString()
      },
      {
        id: 'msg-ai-4',
        role: 'assistant',
        content: `Here is what the standard Firebird fault codes indicate:

* **F04 / F10 (Low Water Pressure):** The system pressure has fallen below the 0.7 bar safety threshold. Check for leaks and top up to 1.2 bar using the filling loop.
* **F21 (Flow Sensor Implausible):** The temperature sensor reading is out of range or has a wiring fault. Check sensor wiring and connection.
* **F32 (Insufficient Circulation):** Water is circulating too slowly. Verify the circulator pump is running and ensure zone valves are open.
* **F44 (High Pressure Excursion):** Water pressure exceeded certified limits (above 2.5 bar) during heating, which typically points to an expansion vessel issue.

**Sources:** 04_Heating_System_Fault_Codes_Demo.pdf, Page 1; 01_Hydronic_Water_Pressure_Field_Guide.pdf, Page 1`,
        sources: [
          { document_name: '04_Heating_System_Fault_Codes_Demo.pdf', page_number: 1, snippet: 'Standard fault-code catalogue F04, F21, F32, F44 descriptions' },
          { document_name: '01_Hydronic_Water_Pressure_Field_Guide.pdf', page_number: 1, snippet: 'Cold static pressure baseline and operating limits' }
        ],
        created_at: new Date().toISOString()
      }
    ]
  },
  'default-5': {
    id: 'default-5',
    title: 'Is this temperature alert expected?',
    messages: [
      {
        id: 'msg-user-5',
        role: 'user',
        content: 'Is this temperature alert expected during initial boiler startup?',
        created_at: new Date().toISOString()
      },
      {
        id: 'msg-ai-5',
        role: 'assistant',
        content: `During the first 10 to 15 minutes of a cold startup, a noticeable temperature difference between flow and return pipes is normal while the cold system warms up.

However, if a temperature alert persists or the difference exceeds 20°C to 25°C after warmup, it indicates a circulation restriction. Check that the circulator pump is running and properly vented, verify that motorized zone valves are fully open, and check the flow sensor to rule out fault codes F21 or F32.

**Sources:** 03_Flow_Temperature_DeltaT_and_Circulation.pdf, Page 1; 04_Heating_System_Fault_Codes_Demo.pdf, Page 1`,
        sources: [
          { document_name: '03_Flow_Temperature_DeltaT_and_Circulation.pdf', page_number: 1, snippet: 'Delta-T and circulation symptom matrix' },
          { document_name: '04_Heating_System_Fault_Codes_Demo.pdf', page_number: 1, snippet: 'F21 and F32 circulation fault codes' }
        ],
        created_at: new Date().toISOString()
      }
    ]
  }
};

export default function App() {
  const [conversations, setConversations] = useState([]);
  const [activeChatId, setActiveChatId] = useState('default-1');
  const [currentConversation, setCurrentConversation] = useState(PRESET_CONVERSATIONS['default-1']);
  const [messages, setMessages] = useState(PRESET_CONVERSATIONS['default-1'].messages);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ documents: 9, chunks: 0, qa_pairs: 0 });
  const [toast, setToast] = useState(null);

  // Modals
  const [isKnowledgeOpen, setIsKnowledgeOpen] = useState(false);
  const [isPowerBIOpen, setIsPowerBIOpen] = useState(false);
  const [pbiContext, setPbiContext] = useState(null);

  const showToast = (text) => {
    setToast(text);
    setTimeout(() => setToast(null), 3500);
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
      setStats(kb.stats || { documents: 9, chunks: 0, qa_pairs: 0 });
    } catch (e) {
      console.error('Failed to load stats:', e);
    }
  };

  useEffect(() => {
    loadConversations();
    loadStats();
    checkHealth().catch((e) => {
      console.warn('Backend server starting or offline:', e);
    });
  }, []);

  const handleSelectChat = async (id) => {
    setActiveChatId(id);

    if (PRESET_CONVERSATIONS[id]) {
      const preset = PRESET_CONVERSATIONS[id];
      if (preset.messages) {
        setCurrentConversation(preset);
        setMessages(preset.messages);
        return;
      } else if (preset.prompt) {
        setCurrentConversation({ id, title: preset.title });
        setMessages([]);
        handleSendMessage(preset.prompt);
        return;
      }
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

    // Optimistically show user message
    const tempUserMsg = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setLoading(true);

    try {
      // If activeChatId is a preset string, pass null to backend to create a real conversation
      const convIdForBackend = activeChatId && !activeChatId.startsWith('default-') ? activeChatId : null;
      const response = await sendChatMessage(text, convIdForBackend, pbiContext);
      
      const aiMsg = {
        id: 'ai-' + Date.now(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources || [],
        created_at: new Date().toISOString()
      };
      setMessages((prev) => [...prev, aiMsg]);

      // If new conversation was created by backend
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
    <div className="app-container">
      <Sidebar
        conversations={conversations}
        activeId={activeChatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        stats={stats}
        onOpenKnowledge={() => setIsKnowledgeOpen(true)}
        onOpenPowerBI={() => setIsPowerBIOpen(true)}
        hasActivePBIContext={!!pbiContext}
      />

      <ChatArea
        conversation={currentConversation}
        messages={messages}
        loading={loading}
        onSendMessage={handleSendMessage}
        onOpenKnowledge={() => setIsKnowledgeOpen(true)}
        onOpenPowerBI={() => setIsPowerBIOpen(true)}
        pbiContext={pbiContext}
        onClearChat={() => activeChatId && handleDeleteChat(activeChatId)}
        stats={stats}
      />

      {/* Modals */}
      <KnowledgeModal
        isOpen={isKnowledgeOpen}
        onClose={() => setIsKnowledgeOpen(false)}
        onKnowledgeUpdated={loadStats}
      />

      <PowerBIModal
        isOpen={isPowerBIOpen}
        onClose={() => setIsPowerBIOpen(false)}
        activeContext={pbiContext}
        onSaveContext={(ctx) => {
          setPbiContext(ctx);
          showToast(ctx ? 'Power BI Context attached to chat' : 'Power BI Context removed');
        }}
      />

      {/* Toast Notification */}
      {toast && (
        <div className="toast-banner">
          {toast}
        </div>
      )}
    </div>
  );
}
