import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ArrowUp, Paperclip, Mic } from 'lucide-react';
import { useSpeechRecognition, DEFAULT_SPEECH_LANG } from '../hooks/useSpeechRecognition';

export default function ChatInput({ onSend, disabled, onOpenKnowledge, isAdmin }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);
  const baseTextRef = useRef('');

  // Handle incoming speech recognition transcript
  const handleTranscript = useCallback(({ transcript }) => {
    const base = baseTextRef.current;
    if (base && base.trim()) {
      const separator = base.endsWith(' ') ? '' : ' ';
      setText(base + separator + transcript);
    } else {
      setText(transcript);
    }
  }, []);

  const handleSpeechEnd = useCallback(() => {
    baseTextRef.current = '';
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  const {
    isSupported,
    isListening,
    error,
    startListening,
    stopListening,
    clearError
  } = useSpeechRecognition({
    lang: DEFAULT_SPEECH_LANG,
    onResult: handleTranscript,
    onEnd: handleSpeechEnd
  });

  // Auto-dismiss voice error notification after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        clearError();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, clearError]);

  // Dynamic textarea height calculation: supports multi-line typing naturally
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const calculatedHeight = Math.min(Math.max(textarea.scrollHeight, 48), 180);
      textarea.style.height = `${calculatedHeight}px`;
      textarea.style.overflowY = textarea.scrollHeight > 180 ? 'auto' : 'hidden';
    }
  }, [text]);

  // Auto-focus input on mount and whenever input becomes enabled
  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (isListening) {
      stopListening();
    }
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
    baseTextRef.current = '';
    if (textareaRef.current) {
      textareaRef.current.style.height = '48px';
      textareaRef.current.focus();
    }
  };

  const handleKeyDown = (e) => {
    // Ctrl+Enter or Cmd+Enter sends the message
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit();
      return;
    }
    // Enter without Ctrl/Cmd naturally creates a new line in the textarea
  };

  const handleMicToggle = () => {
    if (disabled) return;
    if (isListening) {
      stopListening();
    } else {
      baseTextRef.current = text;
      startListening();
    }
  };

  return (
    <div className="chat-input-container">
      {/* Voice Status Pill */}
      {error && (
        <div className="voice-status-pill error">
          <span>{error}</span>
          <button
            type="button"
            className="voice-status-close"
            onClick={clearError}
            title="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      {isListening && !error && (
        <div className="voice-status-pill listening">
          <span className="voice-status-dot" aria-hidden="true"></span>
          <span>Listening... Speak now</span>
        </div>
      )}

      {/* ChatGPT-style Message Composer */}
      <div
        className={`chat-composer-box chat-input-pill ${isListening ? 'input-listening' : ''}`}
      >
        <textarea
          ref={textareaRef}
          data-testid="chat-input"
          className="chat-composer-textarea chat-input-field"
          placeholder={isListening ? "Listening to your voice..." : "Ask questions about your problem..."}
          rows={1}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (isListening) {
              baseTextRef.current = e.target.value;
            }
          }}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />

        <div className="chat-composer-footer">
          <div className="composer-hints">
            <span className="composer-hint-badge">
              <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to send · <kbd>Enter</kbd> for new line
            </span>
          </div>

          <div className="chat-input-actions composer-actions">
            {isAdmin && (
              <button
                type="button"
                className="input-action-btn attach-btn"
                onClick={onOpenKnowledge}
                title="Upload Document / Knowledge Base (Admin)"
                aria-label="Upload Document"
              >
                <Paperclip size={18} />
              </button>
            )}

            <button
              type="button"
              className={`input-action-btn mic-btn ${isListening ? 'listening' : ''}`}
              onClick={handleMicToggle}
              disabled={disabled}
              title={isListening ? "Stop listening" : "Voice input (Speech to text)"}
              aria-label={isListening ? "Stop voice input" : "Start voice input"}
            >
              <Mic size={18} />
            </button>

            <button
              type="button"
              data-testid="send-btn"
              className="input-action-btn send-btn"
              onClick={handleSubmit}
              disabled={!text.trim() || disabled}
              title="Send Message (Ctrl + Enter)"
              aria-label="Send message"
            >
              <ArrowUp size={18} strokeWidth={2.5} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
