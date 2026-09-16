import React, { useRef, useEffect } from 'react';
import { Sparkles, RotateCcw, MessageSquare, Database } from 'lucide-react';
import MessageItem from './MessageItem';
import ChatInput from './ChatInput';

export default function ChatArea({
  messages,
  loading,
  onSendMessage,
  onOpenKnowledge,
  onNewChat,
  onToggleDrawer
}) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <main className="chat-main-layout">
      {/* Top Banner exactly matching the screenshot reference */}
      <header className="bot-header-banner">
        <div className="bot-header-left">
          <div className="bot-sparkle-icon">
            <Sparkles size={22} color="#FFFFFF" fill="#FFFFFF" />
          </div>
          <div className="bot-title-group">
            <h1 className="bot-name">Firebird Bot</h1>
            <p className="bot-subtitle">Ask questions about your problem</p>
          </div>
        </div>

        <div className="bot-header-right">
          <button
            type="button"
            className="header-icon-btn"
            onClick={onToggleDrawer}
            title="Recent Chats"
          >
            <MessageSquare size={18} color="#FFFFFF" />
          </button>

          <button
            type="button"
            className="header-icon-btn"
            onClick={onOpenKnowledge}
            title="Knowledge Base"
          >
            <Database size={18} color="#FFFFFF" />
          </button>

          <button
            type="button"
            className="header-icon-btn refresh-btn"
            onClick={onNewChat}
            title="New Chat"
          >
            <RotateCcw size={19} color="#FFFFFF" />
          </button>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="messages-scroll-area">
        <div className="messages-centered-column">
          {messages.length === 0 ? (
            <div className="empty-chat-state">
              <p className="empty-chat-prompt">
                Ask a question about hydronic water pressure, boiler fault codes, Delta-T, or service history.
              </p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <MessageItem
                key={msg.id || i}
                message={msg}
                onSendPrompt={onSendMessage}
              />
            ))
          )}

          {loading && (
            <div className="message-row ai-row">
              <div className="ground-truth-badge">Ground-truth verified</div>
              <div className="ai-card loading-card">
                <div className="typing-dots-indicator">
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Pill Bar pinned at bottom */}
      <ChatInput
        onSend={onSendMessage}
        disabled={loading}
        onOpenKnowledge={onOpenKnowledge}
      />
    </main>
  );
}
