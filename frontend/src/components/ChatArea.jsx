import React, { useRef, useEffect } from 'react';
import { Flame, Sparkles, Download, Share2, Trash2 } from 'lucide-react';
import MessageItem from './MessageItem';
import ChatInput from './ChatInput';

export default function ChatArea({
  conversation,
  messages,
  loading,
  onSendMessage,
  onOpenKnowledge,
  onOpenPowerBI,
  pbiContext,
  onClearChat,
  stats
}) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handlePromptClick = (text) => {
    onSendMessage(text);
  };

  const handleExportCSV = () => {
    if (!messages.length) return;
    const csvContent = "data:text/csv;charset=utf-8," + 
      ["Role,Time,Content"].concat(
        messages.map(m => `"${m.role}","${m.created_at || ''}","${(m.content || '').replace(/"/g, '""')}"`)
      ).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `diagnostic_session_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const docCount = stats?.documents || 9;
  const currentTitle = conversation?.title || 'The boiler pressure is 0.7 bar when cold';

  return (
    <main className="main-content">
      {/* Topbar matching simplified screenshot */}
      <header className="chat-topbar">
        <div className="topbar-left-column">
          <div className="breadcrumb-nav">
            <span className="breadcrumb-category">Diagnostics</span>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-model">Enviromax C26 (SN: FB-2023-88941)</span>
            <span className="breadcrumb-separator">/</span>
          </div>
          <h2 className="topbar-session-title">{currentTitle}</h2>
        </div>

        <div className="topbar-right">
          <div className="toggle-pill-switch" title="Telemetry mode">
            <div className="toggle-pill-knob"></div>
          </div>

          <button className="topbar-btn export-btn" onClick={handleExportCSV} title="Export Diagnostic CSV">
            <Download size={14} />
            <span>Export Diagnostic CSV</span>
          </button>

          <button className="topbar-icon-btn" title="Share" onClick={() => navigator.clipboard?.writeText(window.location.href)}>
            <Share2 size={16} />
          </button>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="messages-container">
        <div className="messages-inner">
          {messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-sparkle-icon">
                <Flame size={32} color="#f97316" />
              </div>
              <h1 className="empty-heading">How can I help with hydronic diagnostics today?</h1>
              <p className="empty-subheading">
                Query technical SOPs, boiler fault trees, static pressure limits, and field plumber guides.
              </p>

              {/* Vertical Stack of Prompt Pills */}
              <div className="suggested-prompts-stack">
                <button
                  className="prompt-pill-btn"
                  onClick={() => handlePromptClick("I topped the system up yesterday and today the pressure has dropped again. What should I investigate?")}
                >
                  I topped the system up yesterday and today the pressure has dropped again. What should I investigate?
                </button>

                <button
                  className="prompt-pill-btn"
                  onClick={() => handlePromptClick("The boiler pressure is 0.7 bar when cold. Upstairs radiators are cold while downstairs works — what to check?")}
                >
                  The boiler pressure is 0.7 bar when cold. Upstairs radiators are cold while downstairs works — what to check?
                </button>

                <button
                  className="prompt-pill-btn"
                  onClick={() => handlePromptClick("Why does pressure increase when the system gets hot?")}
                >
                  Why does pressure increase when the system gets hot?
                </button>

                <button
                  className="prompt-pill-btn"
                  onClick={() => handlePromptClick("What happened on the last burner service?")}
                >
                  What happened on the last burner service?
                </button>

                <button
                  className="prompt-pill-btn"
                  onClick={() => handlePromptClick("What are the boiler fault codes (F04, F21, F32, F44)?")}
                >
                  What are the boiler fault codes (F04, F21, F32, F44)?
                </button>

                <button
                  className="prompt-pill-btn prompt-pill-action"
                  onClick={onOpenKnowledge}
                >
                  Upload or browse documents in the Knowledge Base ↗
                </button>
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <MessageItem
                key={msg.id || i}
                message={msg}
                onSendPrompt={handlePromptClick}
              />
            ))
          )}

          {loading && (
            <div className="message-wrapper ai-message-wrapper">
              <div className="ai-avatar-box">
                <Flame size={18} color="#ffffff" />
              </div>
              <div className="message-body ai-body">
                <div className="ai-header-row">
                  <span className="ai-name">Firebird AI</span>
                  <span className="ai-time">Thinking...</span>
                  <span className="guidance-tag">Verified Technical Guidance</span>
                </div>
                <div className="typing-indicator">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Box matching the screenshot card */}
      <ChatInput
        onSend={onSendMessage}
        disabled={loading}
        pbiContextActive={!!pbiContext}
        docCount={docCount}
        onOpenKnowledge={onOpenKnowledge}
      />
    </main>
  );
}
