import React, { useRef, useEffect } from 'react';
import { ArrowUp, Loader2 } from 'lucide-react';
import { ModeSelector } from './ModeSelector';
import { IntelligenceMode } from '../types';

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSend: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
  mode: IntelligenceMode;
  onModeChange: (newMode: IntelligenceMode) => void;
  enterToSend?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  input,
  setInput,
  onSend,
  isLoading,
  disabled = false,
  placeholder = 'Message ContextAI...',
  mode,
  onModeChange,
  enterToSend = true,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on scrollHeight
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(Math.max(scrollHeight, 44), 200)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (enterToSend) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    } else {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleSubmit();
      }
    }
  };

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading || disabled) return;
    onSend(trimmed);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px';
    }
  };

  const canSubmit = input.trim().length > 0 && !isLoading && !disabled;

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 pt-1">
      {/* Mode Selector Header Bar */}
      <div className="flex items-center justify-between mb-1.5 px-1">
        <ModeSelector
          mode={mode}
          onModeChange={onModeChange}
          disabled={disabled || isLoading}
        />
        <div className="text-[11px] text-app-muted hidden sm:block">
          {mode === 'swift'
            ? 'Swift · Low latency'
            : mode === 'deep'
            ? 'Deep · Advanced reasoning'
            : 'Balanced · Everyday intelligence'}
        </div>
      </div>

      <div className="relative flex flex-col bg-app-composer border border-app-subtle rounded-2xl shadow-sm focus-within:border-app-hover transition-colors overflow-hidden">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          rows={1}
          className="w-full bg-transparent text-app-primary placeholder:text-app-muted text-sm md:text-base px-4 pt-3 pb-3 pr-14 resize-none outline-none max-h-[200px] leading-relaxed disabled:opacity-50"
          style={{ minHeight: '44px' }}
        />

        {/* Send button */}
        <div className="absolute right-2.5 bottom-2 flex items-center">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            aria-label="Send message"
            className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
              canSubmit
                ? 'bg-btn-primary active:scale-95 cursor-pointer shadow-sm'
                : 'bg-app-surface text-app-muted cursor-not-allowed opacity-50'
            }`}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowUp className="w-4 h-4 stroke-[2.5]" />
            )}
          </button>
        </div>
      </div>

      <div className="text-center mt-2 text-[11px] text-app-muted">
        ContextAI maintains conversation context across turns.
      </div>
    </div>
  );
};
