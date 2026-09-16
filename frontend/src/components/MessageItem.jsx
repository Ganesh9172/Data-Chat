import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

export default function MessageItem({ message, onSendPrompt }) {
  const isAI = message.role === 'assistant';
  const sources = message.sources || [];
  const rawContent = message.content || '';

  if (!isAI) {
    // User message: Right-aligned clean light blue-gray bubble
    return (
      <div className="message-row user-row">
        <div className="user-bubble">
          {rawContent}
        </div>
      </div>
    );
  }

  // Split out any trailing citation block from markdown content to render in dedicated box
  let bodyContent = rawContent;
  let citationText = '';

  const citationMatch = rawContent.match(/(\*\*Sources?:\*\*.*$)/s);
  if (citationMatch) {
    citationText = citationMatch[1].trim();
    bodyContent = rawContent.substring(0, citationMatch.index).trim();
  }

  // Clean citation text: remove bold markdown asterisks for clean rendering in citation box
  const formatCitation = (raw) => {
    return raw
      .replace(/\*\*Source:\*\*/gi, 'Source:')
      .replace(/\*\*Sources:\*\*/gi, 'Sources:')
      .trim();
  };

  return (
    <div className="message-row ai-row">
      <div className="ground-truth-badge">Ground-truth verified</div>
      
      <div className="ai-card">
        <div className="ai-card-content">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw]}
            components={{
              table: ({ node, ...props }) => (
                <div className="table-responsive-container">
                  <table {...props} />
                </div>
              )
            }}
          >
            {bodyContent}
          </ReactMarkdown>

          {/* Minimal confirmation action buttons for Knowledge Update workflow */}
          {isAI && (message.is_correction_prompt || bodyContent.toLowerCase().includes("should i save this correction") || bodyContent.toLowerCase().includes("do you want me to save")) && onSendPrompt && (
            <div className="correction-confirmation-actions" style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
              <button
                type="button"
                onClick={() => onSendPrompt("Yes")}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  border: '1px solid #10B981',
                  backgroundColor: '#ECFDF5',
                  color: '#047857',
                  fontWeight: '600',
                  fontSize: '0.82rem',
                  cursor: 'pointer'
                }}
              >
                ✓ Confirm Update
              </button>
              <button
                type="button"
                onClick={() => onSendPrompt("Cancel")}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  border: '1px solid #CBD5E1',
                  backgroundColor: '#F8FAFC',
                  color: '#475569',
                  fontWeight: '600',
                  fontSize: '0.82rem',
                  cursor: 'pointer'
                }}
              >
                ✕ Cancel
              </button>
            </div>
          )}
        </div>

        {/* Source citation box matching the exact design reference */}
        {citationText ? (
          <div className="source-citation-box">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {formatCitation(citationText)}
            </ReactMarkdown>
          </div>
        ) : sources.length > 0 && !rawContent.toLowerCase().includes("couldn't find this information") ? (
          <div className="source-citation-box">
            <span>
              <strong>Source{sources.length > 1 ? 's' : ''}:</strong>{' '}
              {sources.map((s, idx) => (
                <span key={idx}>
                  {idx > 0 && '; '}
                  {s.document_name}
                  {s.is_knowledge_update && s.original_source ? ` (Original source: ${s.original_source})` : (s.page_number ? `, Page ${s.page_number}` : '')}
                </span>
              ))}
            </span>
          </div>
        ) : null}
      </div>
    </div>
  );
}
