import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Paperclip } from 'lucide-react';

export default function ChatInput({ onSend, disabled, pbiContextActive, onOpenKnowledge }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 100)}px`;
    }
  }, [text]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="chat-input-wrapper">
      <div className="chat-input-clean-bar">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder="Ask Firebird AI anything grounded in your knowledge base..."
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />

        <div className="chat-input-actions">
          <button
            type="button"
            className="attach-icon-btn"
            onClick={onOpenKnowledge}
            title="Attach documents / Knowledge Base"
          >
            <Paperclip size={18} />
          </button>

          <button
            type="button"
            className="send-circle-btn"
            onClick={handleSubmit}
            disabled={!text.trim() || disabled}
            title="Send Message"
          >
            <ArrowUp size={18} strokeWidth={2.5} />
          </button>
        </div>
      </div>
    </div>
  );
}
