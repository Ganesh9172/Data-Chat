import React from 'react';
import { Plus, MessageSquare, Trash2, Database, X } from 'lucide-react';

export default function Sidebar({
  isOpen,
  onClose,
  conversations,
  activeId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  onOpenKnowledge,
  stats
}) {
  const defaultQueries = [
    { id: 'default-1', title: 'System pressure looks normal, but there’s no heat going to one zone' },
    { id: 'default-2', title: 'The boiler pressure is 0.7 bar when cold' },
    { id: 'default-3', title: 'What happened on the last burner service?' },
    { id: 'default-4', title: 'Why does pressure increase above 2.5 bar?' },
    { id: 'default-5', title: 'What are the boiler fault codes?' }
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

        <div className="drawer-action-row">
          <button
            className="drawer-new-chat-btn"
            onClick={() => {
              onNewChat();
              onClose();
            }}
          >
            <Plus size={16} strokeWidth={2.5} />
            <span>New Chat</span>
          </button>
        </div>

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

        <div className="drawer-footer">
          <button
            className="drawer-kb-btn"
            onClick={() => {
              onOpenKnowledge();
              onClose();
            }}
          >
            <Database size={16} color="#1877F2" />
            <span>Knowledge Base ({stats?.documents || 6} PDFs)</span>
          </button>
        </div>
      </aside>
    </>
  );
}
