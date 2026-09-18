import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Play, ExternalLink } from 'lucide-react';

export default function MessageItem({ message, onSendPrompt }) {
  const isAI = message.role === 'assistant';
  const sources = message.sources || [];
  const rawContent = message.content || '';
  const relatedVideo = message.related_video;

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

        {/* Related YouTube Video Card directly below generated answer */}
        {relatedVideo && relatedVideo.url && (
          <div className="related-video-box">
            <div className="related-video-header">
              <span className="related-video-header-title">
                <span className="yt-icon-badge" aria-hidden="true">
                  <svg width="15" height="11" viewBox="0 0 15 11" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14.5 1.7C14.3 1 13.8 0.5 13.1 0.3C11.9 0 7.5 0 7.5 0C7.5 0 3.1 0 1.9 0.3C1.2 0.5 0.7 1 0.5 1.7C0.2 2.9 0.2 5.5 0.2 5.5C0.2 5.5 0.2 8.1 0.5 9.3C0.7 10 1.2 10.5 1.9 10.7C3.1 11 7.5 11 7.5 11C7.5 11 11.9 11 13.1 10.7C13.8 10.5 14.3 10 14.5 9.3C14.8 8.1 14.8 5.5 14.8 5.5C14.8 5.5 14.8 2.9 14.5 1.7Z" fill="#FF0000"/>
                    <path d="M6 7.8L9.8 5.5L6 3.2V7.8Z" fill="white"/>
                  </svg>
                </span>
                <strong>Related YouTube Video</strong>
              </span>
            </div>

            <a
              href={relatedVideo.url}
              target="_blank"
              rel="noopener noreferrer"
              className="related-video-card"
              title={`Watch "${relatedVideo.title}" on YouTube`}
            >
              <div className="related-video-thumbnail-container">
                <img
                  src={relatedVideo.thumbnail_url}
                  alt={relatedVideo.title}
                  className="related-video-thumbnail"
                  loading="lazy"
                  onError={(e) => {
                    if (relatedVideo.video_id && !e.target.src.includes('hqdefault')) {
                      e.target.src = `https://i.ytimg.com/vi/${relatedVideo.video_id}/hqdefault.jpg`;
                    }
                  }}
                />
                <div className="related-video-play-overlay">
                  <Play size={20} fill="#ffffff" color="#ffffff" />
                </div>
              </div>

              <div className="related-video-details">
                <span className="related-video-title">{relatedVideo.title}</span>
                <span className="related-video-cta">
                  <Play size={12} fill="#EF4444" color="#EF4444" />
                  <span>Watch on YouTube</span>
                  <ExternalLink size={12} color="#64748B" />
                </span>
              </div>
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

