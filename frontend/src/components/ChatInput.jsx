import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ArrowUp, Paperclip, Mic } from 'lucide-react';
import { useSpeechRecognition, DEFAULT_SPEECH_LANG } from '../hooks/useSpeechRecognition';

export default function ChatInput({ onSend, disabled, onOpenKnowledge }) {
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
    // Return focus to textarea for seamless manual editing
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

  // Dynamic textarea height calculation
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [text]);

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
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
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
      {/* Subtle Voice Status Banner (Listening / Error feedback) */}
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
          <span className="voice-status-dot"></span>
          <span>Listening... Speak now</span>
        </div>
      )}

      <div className={`chat-input-pill ${isListening ? 'input-listening' : ''}`}>
        <textarea
          ref={textareaRef}
          className="chat-input-field"
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

        <div className="chat-input-actions">
          <button
            type="button"
            className="input-action-btn attach-btn"
            onClick={onOpenKnowledge}
            title="Knowledge Base / Documents"
          >
            <Paperclip size={18} />
          </button>

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
            className="input-action-btn send-btn"
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

