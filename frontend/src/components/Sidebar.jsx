import React from 'react';
import { Plus, MessageSquare, Trash2, Database, X, Lock, LogOut, Shield } from 'lucide-react';

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

  return (
    <>
      {/* Backdrop overlay */}
      {isOpen && <div className="drawer-backdrop" onClick={onClose} />}

      {/* Slide-over Drawer */}
      <aside className={`recent-chats-drawer ${isOpen ? 'open' : ''}`}>
        <div className="drawer-header">
          <div className="drawer-title-row">
            <MessageSquare size={18} color="#1877F2" />
            <span className="drawer-title">Recent Chats</span>
          </div>
          <button className="drawer-close-btn" onClick={onClose} title="Close drawer">
            <X size={18} />
          </button>
        </div>

        {/* Admin Status Banner if authenticated */}
        {isAdmin && (
          <div style={{
            padding: '10px 16px',
            background: 'rgba(249, 115, 22, 0.1)',
            borderBottom: '1px solid rgba(249, 115, 22, 0.25)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Shield size={16} color="#f97316" />
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#f97316' }}>
                Admin Mode Active
              </span>
            </div>
            <button
              onClick={() => {
                onLogout?.();
                onClose();
              }}
              title="Sign Out of Admin"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                fontSize: '0.76rem',
                padding: '4px 6px',
                borderRadius: 4
              }}
            >
              <LogOut size={14} />
              <span>Lock</span>
            </button>
          </div>
        )}

        {/* Action row: New Chat */}
        <div className="drawer-action-row">
          <button
            className="drawer-new-chat-btn"
            style={{ width: '100%' }}
            onClick={() => {
              onNewChat();
              onClose();
            }}
          >
            <Plus size={16} strokeWidth={2.5} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Session Conversation List */}
        <div className="drawer-chats-list">
          {displayQueries.map((c) => {
            const isActive = c.id === activeId;
            return (
              <div
                key={c.id}
                className={`drawer-chat-item ${isActive ? 'active' : ''}`}
                onClick={() => {
                  onSelectChat(c.id);
                  onClose();
                }}
              >
                <div className="drawer-chat-info">
                  <span className="drawer-chat-title">{c.title || 'Untitled Conversation'}</span>
                </div>
                {!c.id.startsWith('default-') && (
                  <button
                    className="drawer-chat-del-btn"
                    title="Delete Chat"
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

        {/* Drawer Footer */}
        <div className="drawer-footer" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Knowledge Base is strictly visible ONLY to authenticated Administrator */}
          {isAdmin ? (
            <button
              className="drawer-kb-btn"
              onClick={() => {
                onOpenKnowledge();
                onClose();
              }}
            >
              <Database size={16} color="#f97316" />
              <span>Knowledge Base ({stats?.documents || 6} PDFs)</span>
            </button>
          ) : (
            <button
              onClick={() => {
                onOpenLogin?.();
                onClose();
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                width: '100%',
                padding: '10px 14px',
                background: 'transparent',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '0.8rem',
                transition: 'all 0.15s ease'
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
