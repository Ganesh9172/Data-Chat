import React from 'react';
import { Plus, MessageSquare, Trash2, Database, Lock, LogOut, Shield, Sparkles, PanelLeftClose } from 'lucide-react';

export default function Sidebar({
  isOpen,
  onClose,
  conversations,
  activeId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  onOpenKnowledge,
  stats,
  isAdmin,
  onLogout,
  onOpenLogin
}) {
  const defaultQueries = [
    { id: 'default-1', title: 'System pressure looks normal, but there’s no heat going to one zone' },
    { id: 'default-2', title: 'The boiler pressure is 0.7 bar when cold' }
  ];

  const displayQueries = (conversations && conversations.length > 0) ? conversations : defaultQueries;

  const handleSelect = (id) => {
    onSelectChat(id);
    // On small screens, close the slide-over overlay so user sees the conversation immediately
    if (typeof window !== 'undefined' && window.innerWidth <= 768) {
      onClose?.();
    }
  };

  const handleNewChat = () => {
    onNewChat();
    if (typeof window !== 'undefined' && window.innerWidth <= 768) {
      onClose?.();
    }
  };

  return (
    <>
      {/* Mobile-only backdrop overlay */}
      {isOpen && (
        <div
          className="sidebar-backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Main Left Sidebar */}
      <aside
        className={`app-sidebar ${isOpen ? 'open' : 'closed'}`}
        aria-label="Sidebar navigation"
      >
        {/* Sidebar Header: Branding & Collapse Toggle */}
        <div className="sidebar-header">
          <div className="sidebar-brand-group">
            <div className="sidebar-sparkle-badge" aria-hidden="true">
              <Sparkles size={16} color="#FFFFFF" fill="#FFFFFF" />
            </div>
            <span className="sidebar-brand-title">Firebird AI</span>
          </div>
          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={onClose}
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        </div>

        {/* Action Row: New Chat button */}
        <div className="sidebar-action-row">
          <button
            type="button"
            data-testid="sidebar-new-chat-btn"
            className="sidebar-new-chat-btn"
            onClick={handleNewChat}
          >
            <Plus size={16} strokeWidth={2.5} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Section Title: Recent Chats */}
        <div className="sidebar-section-title">
          <MessageSquare size={14} color="#64748B" />
          <span>Recent Chats</span>
        </div>

        {/* Scrollable Conversation List */}
        <div className="sidebar-chats-list" role="list">
          {displayQueries.map((c) => {
            const isActive = c.id === activeId;
            return (
              <div
                key={c.id}
                role="listitem"
                data-testid={`chat-item-${c.id}`}
                className={`sidebar-chat-item ${isActive ? 'active' : ''}`}
                onClick={() => handleSelect(c.id)}
              >
                <div className="sidebar-chat-info">
                  <span className="sidebar-chat-title">{c.title || 'Untitled Conversation'}</span>
                </div>
                {!c.id.startsWith('default-') && (
                  <button
                    type="button"
                    className="sidebar-chat-del-btn"
                    title="Delete Chat"
                    aria-label={`Delete chat ${c.title || ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteChat(c.id);
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* Sidebar Footer: Admin status & Knowledge base */}
        <div className="sidebar-footer">
          {isAdmin && (
            <div className="sidebar-admin-badge">
              <div className="sidebar-admin-info">
                <Shield size={15} color="#f97316" />
                <span>Admin Mode</span>
              </div>
              <button
                type="button"
                onClick={() => {
                  onLogout?.();
                  if (typeof window !== 'undefined' && window.innerWidth <= 768) {
                    onClose?.();
                  }
                }}
                title="Sign Out of Admin"
                className="sidebar-admin-lock-btn"
              >
                <LogOut size={13} />
                <span>Lock</span>
              </button>
            </div>
          )}

          {isAdmin ? (
            <button
              type="button"
              className="sidebar-kb-btn"
              onClick={() => {
                onOpenKnowledge();
                if (typeof window !== 'undefined' && window.innerWidth <= 768) {
                  onClose?.();
                }
              }}
            >
              <Database size={16} color="#f97316" />
              <span>Knowledge Base ({stats?.documents || 6} PDFs)</span>
            </button>
          ) : (
            <button
              type="button"
              className="sidebar-login-btn"
              onClick={() => {
                onOpenLogin?.();
                if (typeof window !== 'undefined' && window.innerWidth <= 768) {
                  onClose?.();
                }
              }}
            >
              <Lock size={14} />
              <span>Admin Access</span>
            </button>
          )}
        </div>
      </aside>
    </>
  );
}
