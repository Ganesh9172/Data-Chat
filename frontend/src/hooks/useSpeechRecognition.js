import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Default recognition language.
 * Easily configured here for internationalization (e.g., 'en-IN', 'en-US', 'hi-IN').
 */
export const DEFAULT_SPEECH_LANG = 'en-IN';

export function useSpeechRecognition({
  lang = DEFAULT_SPEECH_LANG,
  onResult,
  onEnd
} = {}) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState(null);
  const recognitionRef = useRef(null);
  const isManuallyStoppedRef = useRef(false);

  // Check Web Speech API support safely in browser environment
  const isSupported = typeof window !== 'undefined' &&
    !!(window.SpeechRecognition || window.webkitSpeechRecognition);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (_) {}
      }
    };
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const stopListening = useCallback(() => {
    isManuallyStoppedRef.current = true;
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (_) {}
    }
    setIsListening(false);
  }, []);

  const startListening = useCallback(() => {
    clearError();

    if (!isSupported) {
      setError('Speech recognition is not supported in this browser.');
      return;
    }

    // Stop any existing instance
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (_) {}
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.lang = lang;
    recognition.continuous = false; // Stop naturally when the user finishes speaking
    recognition.interimResults = true; // Stream interim results in real-time
    recognition.maxAlternatives = 1;

    isManuallyStoppedRef.current = false;

    recognition.onstart = () => {
      setIsListening(true);
      clearError();
    };

    recognition.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interimTranscript += result[0].transcript;
        }
      }

      if (onResult) {
        onResult({
          finalTranscript,
          interimTranscript,
          transcript: (finalTranscript + ' ' + interimTranscript).trim()
        });
      }
    };

    recognition.onerror = (event) => {
      console.warn('Speech recognition error event:', event.error);
      setIsListening(false);

      if (isManuallyStoppedRef.current) {
        return;
      }

      switch (event.error) {
        case 'not-allowed':
        case 'service-not-allowed':
          setError('Microphone permission is required for voice input.');
          break;
        case 'no-speech':
          setError('No speech was detected. Please try speaking again.');
          break;
        case 'audio-capture':
          setError('No microphone was found. Please check your audio settings.');
          break;
        case 'network':
          setError('Network error occurred during speech recognition.');
          break;
        default:
          setError('Speech recognition error. Please try again.');
          break;
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      if (onEnd) {
        onEnd();
      }
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
    } catch (err) {
      console.error('Failed to start speech recognition:', err);
      setIsListening(false);
      setError('Could not start microphone. Please try again.');
    }
  }, [isSupported, lang, onResult, onEnd, clearError]);

  return {
    isSupported,
    isListening,
    error,
    startListening,
    stopListening,
    clearError
  };
}
