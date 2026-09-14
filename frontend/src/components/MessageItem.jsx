import React from 'react';
import { Flame, FileText, ShieldCheck } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

export default function MessageItem({ message, onSendPrompt }) {
  const isAI = message.role === 'assistant';
  const sources = message.sources || [];
  const content = message.content || '';

  const handleContentClick = (e) => {
    const btn = e.target.closest('.followup-btn');
    if (btn && onSendPrompt) {
      const text = btn.innerText.replace('→', '').trim();
      if (text) {
        onSendPrompt(text);
      }
    }
  };

  if (!isAI) {
    // User Question - Clean, right-aligned message bubble
    return (
      <div className="message-wrapper user-message-wrapper">
        <div className="user-message-card">
          <div className="user-content-text">
            {content}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message-wrapper ai-message-wrapper">
      <div className="ai-avatar-box">
        <Flame size={17} color="#ffffff" />
      </div>

      <div className="message-body ai-body">
        {/* Clean AI Header */}
        <div className="ai-header-row">
          <span className="ai-name">Firebird AI</span>
        </div>

        {/* Clean, Normal Conversational Answer Container */}
        <div className="ai-normal-response">
          <div className="ai-message-content markdown-technical" onClick={handleContentClick}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={{
                p: ({ node, children, ...props }) => {
                  const text = React.Children.toArray(children).map(c => typeof c === 'string' ? c : '').join('').trim();
                  if (text.startsWith('Source:') || text.startsWith('**Source:') || text.startsWith('Sources:') || text.startsWith('**Sources:')) {
                    return (
                      <div className="source-citation-line">
                        <FileText size={14} color="#ea580c" style={{ flexShrink: 0 }} />
                        <span>{children}</span>
                      </div>
                    );
                  }
                  return <p {...props}>{children}</p>;
                },
                table: ({ node, ...props }) => (
                  <div className="table-responsive-container">
                    <table {...props} />
                  </div>
                )
              }}
            >
              {content}
            </ReactMarkdown>
          </div>

          {/* Simple source line if sources array provided and not already in text */}
          {sources.length > 0 && !content.toLowerCase().includes('source:') && (
            <div className="source-citation-line">
              <FileText size={14} color="#ea580c" style={{ flexShrink: 0 }} />
              <span>
                <strong>Source{sources.length > 1 ? 's' : ''}:</strong>{' '}
                {sources.map((s, idx) => (
                  <span key={idx}>
                    {idx > 0 && '; '}
                    {s.document_name}{s.page_number ? `, Page ${s.page_number}` : ''}
                  </span>
                ))}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
