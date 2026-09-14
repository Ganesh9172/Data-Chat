import React from 'react';
import { Flame, Plus, MessageSquare, Trash2, Database, BarChart3, Settings, FileText, ChevronRight } from 'lucide-react';

export default function Sidebar({
  conversations,
  activeId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  stats,
  onOpenKnowledge,
  onOpenPowerBI,
  hasActivePBIContext
}) {
  // Preset queries from screenshot if no custom conversation history
  const defaultQueries = [
    { id: 'default-1', title: 'The boiler pressure is 0.7 bar...' },
    { id: 'default-2', title: 'What happened on the last burner service?' },
    { id: 'default-3', title: 'Why does pressure increase above 2.5 bar?' },
    { id: 'default-4', title: 'What are the boiler fault codes?' },
    { id: 'default-5', title: 'Is this temperature alert expected?' }
  ];

  const displayQueries = (conversations && conversations.length > 0) ? conversations : defaultQueries;

  return (
    <aside className="sidebar">
      {/* Header with V2.4 badge and settings */}
      <div className="sidebar-header">
        <div className="sidebar-header-left">
          <div className="logo-icon-box">
            <Flame size={19} color="#ea580c" />
          </div>
          <div className="logo-title-row">
            <span className="logo-title">Firebird AI</span>
            <span className="version-pill">V2.4</span>
          </div>
        </div>
        <button className="icon-subtle-btn" title="Settings" onClick={onOpenKnowledge}>
          <Settings size={17} />
        </button>
      </div>

      {/* New Diagnostic Session Button */}
      <div className="new-session-container">
        <button className="new-session-btn" onClick={onNewChat}>
          <Plus size={16} strokeWidth={2.5} />
          <span>New Diagnostic Session</span>
        </button>
      </div>

      {/* Queries List */}
      <div className="chat-list-container">
        <div className="list-section-header">
          <span>RECENT QUERIES</span>
        </div>

        {displayQueries.map((c) => {
          const isActive = c.id === activeId || (!activeId && c.id === 'default-1');
          return (
            <div
              key={c.id}
              className={`query-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectChat(c.id)}
            >
              <div className={`query-circle-icon ${isActive ? 'active' : ''}`} />
              <span className="query-title">{c.title || 'The boiler pressure is 0.7 bar...'}</span>
              {!c.id.startsWith('default-') && (
                <button
                  className="query-delete-btn"
                  title="Delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteChat(c.id);
                  }}
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          );
        })}

        {/* Hydronic Guidelines */}
        <div className="list-section-header" style={{ marginTop: '26px' }}>
          <span>HYDRONIC GUIDELINES</span>
        </div>
        <div className="guideline-item" onClick={onOpenKnowledge}>
          <FileText size={15} color="#94a3b8" />
          <span>Commercial Glycol Ratio Specs</span>
        </div>
        <div className="guideline-item" onClick={onOpenKnowledge}>
          <FileText size={15} color="#94a3b8" />
          <span>Expansion Vessel Sizing Table</span>
        </div>
      </div>

      {/* Sidebar Footer Cards */}
      <div className="sidebar-footer">
        <div className="footer-card" onClick={onOpenKnowledge}>
          <div className="footer-card-left">
            <div className="footer-icon-box orange-bg">
              <Database size={16} color="#ea580c" />
            </div>
            <div className="footer-card-text">
              <span className="card-title">Knowledge Base</span>
              <span className="card-subtitle">PDFs, SOPs & Guides</span>
            </div>
          </div>
        </div>

        <div className="footer-card" onClick={onOpenPowerBI}>
          <div className="footer-card-left">
            <div className="footer-icon-box blue-bg">
              <BarChart3 size={16} color="#2563eb" />
            </div>
            <div className="footer-card-text">
              <span className="card-title">Power BI Context</span>
              <span className="card-subtitle-live">
                <span className="green-dot">●</span> Sensor Feeds Live
              </span>
            </div>
          </div>
          <ChevronRight size={16} color="#94a3b8" />
        </div>
      </div>
    </aside>
  );
}
