import React, { useState } from 'react';
import { MessageSquare, Trash2, Check, X, Loader2 } from 'lucide-react';
import { Conversation } from '../types';

interface ConversationListProps {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  isLoading: boolean;
  isDeletingId?: string | null;
}

export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  selectedId,
  onSelect,
  onDelete,
  isLoading,
  isDeletingId,
}) => {
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Sort conversations by updated_at or created_at desc
  const sortedConversations = [...conversations].sort((a, b) => {
    const timeA = new Date(a.updated_at || a.created_at || 0).getTime();
    const timeB = new Date(b.updated_at || b.created_at || 0).getTime();
    return timeB - timeA;
  });

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setConfirmDeleteId(id);
  };

  const handleConfirmDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    onDelete(id);
    setConfirmDeleteId(null);
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirmDeleteId(null);
  };

  if (isLoading && conversations.length === 0) {
    return (
      <div className="p-4 space-y-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-9 rounded-lg bg-app-main animate-pulse border border-app-subtle"
          />
        ))}
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="px-4 py-8 text-center text-xs text-app-muted">
        <MessageSquare className="w-5 h-5 mx-auto mb-2 opacity-40" />
        <p>No conversations yet.</p>
        <p className="mt-1 text-[11px] opacity-75">Start a new chat to begin.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-2 space-y-0.5 py-1">
      <div className="px-2 pb-1 text-[11px] font-medium text-app-muted uppercase tracking-wider">
        Recent Chats
      </div>

      {sortedConversations.map((conv) => {
        const isSelected = conv.id === selectedId;
        const isConfirming = confirmDeleteId === conv.id;
        const isDeleting = isDeletingId === conv.id;

        return (
          <div
            key={conv.id}
            onClick={() => onSelect(conv.id)}
            className={`group relative flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
              isSelected
                ? 'bg-app-surface text-app-primary font-medium border border-app-subtle'
                : 'text-app-secondary hover:bg-app-main hover:text-app-primary border border-transparent'
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0 flex-1 pr-2">
              <MessageSquare className="w-3.5 h-3.5 shrink-0 text-app-muted group-hover:text-app-primary" />
              <span className="truncate whitespace-nowrap">
                {conv.title && conv.title.trim().length > 0 ? conv.title : 'New Chat'}
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center shrink-0">
              {isDeleting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-app-muted" />
              ) : isConfirming ? (
                <div className="flex items-center gap-1 bg-app-sidebar px-1 py-0.5 rounded border border-app-subtle">
                  <button
                    onClick={(e) => handleConfirmDelete(e, conv.id)}
                    className="p-1 hover:text-red-500 text-red-500 transition-colors"
                    title="Confirm delete"
                  >
                    <Check className="w-3 h-3" />
                  </button>
                  <button
                    onClick={handleCancelDelete}
                    className="p-1 hover:text-app-primary text-app-muted transition-colors"
                    title="Cancel"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={(e) => handleDeleteClick(e, conv.id)}
                  className="opacity-0 group-hover:opacity-100 hover:text-red-500 text-app-muted p-1 rounded transition-all"
                  title="Delete conversation"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
