import React, { useRef, useEffect, useCallback } from 'react';
import { Sparkles, RotateCcw, MessageSquare, Database, Menu, ChevronRight } from 'lucide-react';
import MessageItem from './MessageItem';
import ChatInput from './ChatInput';

const FAQ_QUESTIONS = [
  "Is 0.7 bar boiler pressure too low?",
  "Why does pressure rise to 2.8 bar when heating?",
  "Why does my boiler pressure keep dropping?",
  "Why are upstairs radiators cold?",
  "What does boiler fault code F32 mean?"
];

export default function ChatArea({
  messages,
  loading,
  onSendMessage,
  onOpenKnowledge,
  onNewChat,
  onToggleDrawer,
  isAdmin
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
          <button
            type="button"
            className="header-menu-btn"
            onClick={onToggleDrawer}
            title="Menu"
            aria-label="Open sidebar menu"
          >
            <Menu size={20} color="#FFFFFF" />
          </button>
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
            className="header-icon-btn header-chats-btn"
            onClick={onToggleDrawer}
            title="Recent Chats"
            aria-label="Recent Chats"
          >
            <MessageSquare size={18} color="#FFFFFF" />
          </button>

          {isAdmin && (
            <button
              type="button"
              className="header-icon-btn"
              onClick={onOpenKnowledge}
              title="Knowledge Base (Admin)"
              aria-label="Knowledge Base"
            >
              <Database size={18} color="#FFFFFF" />
            </button>
          )}

          <button
            type="button"
            data-testid="new-chat-btn"
            className="header-icon-btn refresh-btn"
            onClick={onNewChat}
            title="New Chat"
            aria-label="New Chat"
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
            <div className="empty-chat-state" data-testid="empty-chat-state">
              <div className="faq-header">
                <div className="faq-sparkle-badge" aria-hidden="true">
                  <Sparkles size={20} color="#1877F2" fill="#1877F2" />
                </div>
                <h2 className="faq-title">Frequently Asked Questions</h2>
                <p className="faq-subtitle">
                  Select a question to start, or type your own problem below.
                </p>
              </div>
              <div className="faq-list" role="list" aria-label="Frequently Asked Questions">
                {FAQ_QUESTIONS.map((question, index) => (
                  <button
                    key={index}
                    type="button"
                    className="faq-item-btn"
                    data-testid={`faq-question-${index}`}
                    onClick={() => onSendMessage(question)}
                  >
                    <span className="faq-item-text">{question}</span>
                    <ChevronRight size={18} className="faq-item-arrow" aria-hidden="true" />
                  </button>
                ))}
              </div>
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
              <div className="ai-card loading-card" data-testid="loading-indicator">
                <div className="typing-dots-indicator">
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
                </div>
              </div>
            </div>
          )}

          {/* Bottom spacing element so the last word is never covered by the floating input */}
          <div className="chat-bottom-spacer" aria-hidden="true" />
        </div>
      </div>

      {/* Input Pill Bar pinned at bottom */}
      <ChatInput
        onSend={onSendMessage}
        disabled={loading}
        onOpenKnowledge={onOpenKnowledge}
        isAdmin={isAdmin}
      />
    </main>
  );
}
