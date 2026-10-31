import React from 'react';
import { Sparkles, MessageSquarePlus } from 'lucide-react';

interface EmptyStateProps {
  onSelectPrompt?: (prompt: string) => void;
  onNewChat?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ onSelectPrompt, onNewChat }) => {
  const suggestions = [
    'Explain how stateful conversation memory works in LLMs',
    'Help me design a database schema for contextual chat history',
    'Compare SQLite vs PostgreSQL for local conversational state',
    'What are the key trade-offs between sliding window context and summarization?',
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-2xl mx-auto">
      {/* Brand icon */}
      <div className="w-12 h-12 rounded-2xl bg-app-composer border border-app-subtle flex items-center justify-center mb-6 text-app-primary shadow-sm">
        <Sparkles className="w-6 h-6" />
      </div>

      {/* Heading */}
      <h1 className="text-2xl md:text-3xl font-semibold text-app-primary tracking-tight mb-2">
        ContextAI
      </h1>

      {/* Short description */}
      <p className="text-app-secondary text-sm md:text-base max-w-md mb-8 leading-relaxed">
        An AI assistant that remembers the context of your conversations.
      </p>

      {/* Encouragement & Starter ideas */}
      <div className="w-full space-y-4">
        <div className="text-xs text-app-muted uppercase tracking-wider font-medium">
          Start a conversation
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              onClick={() => onSelectPrompt?.(suggestion)}
              className="p-3 bg-app-surface hover:bg-app-composer border border-app-subtle rounded-xl text-xs text-app-secondary hover:text-app-primary transition-all text-left group cursor-pointer"
            >
              <div className="line-clamp-2 leading-relaxed">{suggestion}</div>
            </button>
          ))}
        </div>

        {onNewChat && (
          <div className="pt-2">
            <button
              onClick={onNewChat}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium text-app-primary bg-app-composer hover:bg-app-surface border border-app-subtle rounded-lg transition-colors cursor-pointer"
            >
              <MessageSquarePlus className="w-3.5 h-3.5" />
              <span>New Conversation</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
