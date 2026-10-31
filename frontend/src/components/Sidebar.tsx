import React from 'react';
import { PanelLeftClose, Plus, Settings, Sparkles, Server } from 'lucide-react';
import { ConversationList } from './ConversationList';
import { Conversation, BackendStatus } from '../types';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  conversations: Conversation[];
  selectedId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onDeleteConversation: (id: string) => void;
  isLoadingConversations: boolean;
  isDeletingId?: string | null;
  onOpenSettings: () => void;
  backendStatus: BackendStatus;
  developerModeEnabled?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  conversations,
  selectedId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  isLoadingConversations,
  isDeletingId,
  onOpenSettings,
  backendStatus,
  developerModeEnabled = false,
}) => {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-app-sidebar border-r border-app-subtle flex flex-col transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:hidden'
        }`}
      >
        {/* Top Section */}
        <div className="p-3 border-b border-app-subtle flex flex-col gap-2 shrink-0">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-app-composer border border-app-subtle flex items-center justify-center text-app-primary">
                <Sparkles className="w-3.5 h-3.5" />
              </div>
              <span className="font-semibold text-sm tracking-tight text-app-primary">
                ContextAI
              </span>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 text-app-muted hover:text-app-primary hover:bg-app-hover rounded-lg transition-colors cursor-pointer"
              title="Close sidebar"
              aria-label="Close sidebar"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* New Chat Button */}
          <button
            onClick={() => {
              onNewChat();
              if (window.innerWidth < 768) {
                onClose();
              }
            }}
            className="flex items-center gap-2 w-full px-3 py-2 text-xs font-medium text-app-primary bg-app-main hover:bg-app-hover border border-app-subtle rounded-lg transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New chat</span>
          </button>
        </div>

        {/* Conversation History List */}
        <ConversationList
          conversations={conversations}
          selectedId={selectedId}
          onSelect={(id) => {
            onSelectConversation(id);
            if (window.innerWidth < 768) {
              onClose();
            }
          }}
          onDelete={onDeleteConversation}
          isLoading={isLoadingConversations}
          isDeletingId={isDeletingId}
        />

        {/* Bottom Section */}
        <div className="p-3 border-t border-app-subtle bg-app-sidebar shrink-0 space-y-2">
          {/* Backend Status indicator - only visible in Developer Mode */}
          {developerModeEnabled && (
            <div className="flex items-center justify-between px-2 py-1.5 rounded-md bg-app-main border border-app-subtle text-[11px]">
              <div className="flex items-center gap-1.5">
                <Server className="w-3 h-3 text-app-muted" />
                <span className="text-app-muted">Backend</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    backendStatus.isChecking
                      ? 'bg-amber-400 animate-pulse'
                      : backendStatus.isAvailable
                      ? 'bg-emerald-500'
                      : 'bg-red-500'
                  }`}
                />
                <span
                  className={
                    backendStatus.isAvailable ? 'text-emerald-500 font-medium' : 'text-red-500 font-medium'
                  }
                >
                  {backendStatus.isChecking
                    ? 'Checking...'
                    : backendStatus.isAvailable
                    ? 'Connected'
                    : 'Offline'}
                </span>
              </div>
            </div>
          )}

          {/* Settings entry */}
          <button
            onClick={onOpenSettings}
            className="flex items-center gap-2 w-full px-2 py-1.5 text-xs text-app-secondary hover:text-app-primary hover:bg-app-hover rounded-lg transition-colors cursor-pointer"
          >
            <Settings className="w-4 h-4 text-app-muted" />
            <span>Settings</span>
          </button>

          {/* App Info */}
          <div className="px-2 pt-1 text-[11px] text-app-muted flex items-center justify-between">
            <span>ContextAI v1.1.0</span>
            <span>Stateful Chatbot</span>
          </div>
        </div>
      </aside>
    </>
  );
};
