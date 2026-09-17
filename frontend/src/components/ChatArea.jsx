import React, { useRef, useEffect, useCallback } from 'react';
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
  const scrollContainerRef = useRef(null);
  const messagesContentRef = useRef(null);
  const isUserNearBottomRef = useRef(true);

  // Reliable scroll-to-bottom utility directly operating on the message container
  const scrollToBottom = useCallback((behavior = 'smooth') => {
    const container = scrollContainerRef.current;
    if (!container) return;

    if (behavior === 'smooth') {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth'
      });
    } else {
      container.scrollTop = container.scrollHeight;
    }
  }, []);

  // Track if user is scrolled near bottom (within 130px threshold)
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const threshold = 130;
    const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    isUserNearBottomRef.current = distanceToBottom <= threshold;
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    // If the latest message was sent by user, force pin to bottom and scroll
    if (lastMsg && lastMsg.role === 'user') {
      isUserNearBottomRef.current = true;
      scrollToBottom('smooth');
    } else if (isUserNearBottomRef.current) {
      scrollToBottom('smooth');
    }
  }, [messages, scrollToBottom]);

  // Auto-scroll when loading state toggles (e.g. typing indicator appears/disappears)
  useEffect(() => {
    if (isUserNearBottomRef.current) {
      scrollToBottom('smooth');
    }
  }, [loading, scrollToBottom]);

  // Keep following streamed/expanding content as long as the user hasn't scrolled away
  useEffect(() => {
    const contentEl = messagesContentRef.current;
    if (!contentEl) return;

    const resizeObserver = new ResizeObserver(() => {
      if (isUserNearBottomRef.current) {
        scrollToBottom('auto');
      }
    });

    resizeObserver.observe(contentEl);
    return () => resizeObserver.disconnect();
  }, [scrollToBottom]);

  return (
    <main className="chat-main-layout">
      {/* Top Banner exactly matching the design reference */}
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

      {/* Messages Scroll Area with its own vertical scroll and container ref */}
      <div
        className="messages-scroll-area"
        ref={scrollContainerRef}
        onScroll={handleScroll}
      >
        <div className="messages-centered-column" ref={messagesContentRef}>
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

          {/* Bottom spacing element so the last word is never covered by the floating input */}
          <div
            className="chat-bottom-spacer"
            style={{ height: '96px', flexShrink: 0, pointerEvents: 'none' }}
            aria-hidden="true"
          />
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
