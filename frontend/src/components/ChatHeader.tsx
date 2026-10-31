import React from 'react';
import { PanelLeft, Sparkles, Plus, Trash2 } from 'lucide-react';
import { ContextIndicator } from './ContextIndicator';
import { Conversation } from '../types';

interface ChatHeaderProps {
  conversation: Conversation | null;
  onToggleSidebar: () => void;
  isSidebarOpen: boolean;
  onNewChat: () => void;
  onDeleteCurrent?: () => void;
  messagesCount: number;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  conversation,
  onToggleSidebar,
  isSidebarOpen,
  onNewChat,
  onDeleteCurrent,
  messagesCount,
}) => {
  return (
    <header className="h-14 border-b border-app-subtle bg-app-main px-4 flex items-center justify-between shrink-0 select-none z-10">
      {/* Left: Sidebar Toggle + Title */}
      <div className="flex items-center gap-3 min-w-0">
        {!isSidebarOpen && (
          <button
            onClick={onToggleSidebar}
            className="p-1.5 text-app-secondary hover:text-app-primary hover:bg-app-hover rounded-lg transition-colors cursor-pointer"
            title="Open sidebar"
            aria-label="Open sidebar"
          >
            <PanelLeft className="w-5 h-5" />
          </button>
        )}

        <div className="flex items-center gap-2 min-w-0">
          <h1 className="text-sm font-medium text-app-primary truncate max-w-xs sm:max-w-md">
            {conversation?.title || 'ContextAI'}
          </h1>
          <div className="hidden sm:flex items-center gap-1 text-[11px] text-app-muted">
            <span>·</span>
            <div className="flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-app-secondary" />
              <span>Stateful AI</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right: Context indicator and quick actions */}
      <div className="flex items-center gap-2">
        {conversation && (
          <ContextIndicator
            messagesInContext={conversation.messages_in_context}
            contextSummary={conversation.context_summary}
            totalMessagesCount={messagesCount}
          />
        )}

        {conversation && onDeleteCurrent && (
          <button
            onClick={onDeleteCurrent}
            className="p-1.5 text-app-muted hover:text-red-500 hover:bg-app-hover rounded-lg transition-colors hidden sm:flex cursor-pointer"
            title="Delete conversation"
            aria-label="Delete conversation"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}

        <button
          onClick={onNewChat}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-app-primary bg-app-surface hover:bg-app-composer border border-app-subtle rounded-lg transition-colors cursor-pointer"
          title="New conversation"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">New chat</span>
        </button>
      </div>
    </header>
  );
};
