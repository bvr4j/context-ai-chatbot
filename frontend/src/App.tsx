import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatHeader } from './components/ChatHeader';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { EmptyState } from './components/EmptyState';
import { SettingsModal } from './components/SettingsModal';
import { BackendBanner } from './components/BackendBanner';
import { api, getApiBaseUrl, ApiError } from './services/api';
import {
  Conversation,
  Message,
  BackendStatus,
  IntelligenceMode,
  ThemeMode,
  UserPreferences,
} from './types';
import { Loader2, AlertCircle } from 'lucide-react';

const LAST_CONV_STORAGE_KEY = 'contextai_active_conv_id';
const THEME_STORAGE_KEY = 'contextai_theme';
const DEFAULT_MODE_STORAGE_KEY = 'contextai_default_mode';
const ENTER_TO_SEND_STORAGE_KEY = 'contextai_enter_to_send';
const DEV_MODE_STORAGE_KEY = 'contextai_dev_mode';

export default function App() {
  // User Preferences
  const [preferences, setPreferences] = useState<UserPreferences>(() => {
    try {
      const theme = (localStorage.getItem(THEME_STORAGE_KEY) as ThemeMode) || 'dark';
      const defaultMode =
        (localStorage.getItem(DEFAULT_MODE_STORAGE_KEY) as IntelligenceMode) || 'balanced';
      const enterToSend = localStorage.getItem(ENTER_TO_SEND_STORAGE_KEY) !== 'false';
      const developerModeEnabled = localStorage.getItem(DEV_MODE_STORAGE_KEY) === 'true';
      return { theme, defaultMode, enterToSend, developerModeEnabled };
    } catch {
      return {
        theme: 'dark',
        defaultMode: 'balanced',
        enterToSend: true,
        developerModeEnabled: false,
      };
    }
  });

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [currentMode, setCurrentMode] = useState<IntelligenceMode>(preferences.defaultMode);

  // Loading states
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isDeletingId, setIsDeletingId] = useState<string | null>(null);

  // Error states
  const [chatError, setChatError] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);

  // Backend Health
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({
    isChecking: true,
    isAvailable: false,
    lastChecked: null,
    endpointUrl: getApiBaseUrl(),
  });

  // UI state
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Ref for auto-scroll
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  // Apply Theme to documentElement
  useEffect(() => {
    const applyTheme = (theme: ThemeMode) => {
      const isDark =
        theme === 'dark' ||
        (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
      const resolved = isDark ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', resolved);
      document.documentElement.classList.remove('dark', 'light');
      document.documentElement.classList.add(resolved);
    };

    applyTheme(preferences.theme);

    if (preferences.theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const listener = () => {
        applyTheme('system');
      };
      mediaQuery.addEventListener('change', listener);
      return () => mediaQuery.removeEventListener('change', listener);
    }
  }, [preferences.theme]);

  // Update preferences & sync to localStorage
  const updatePreferences = (updates: Partial<UserPreferences>) => {
    setPreferences((prev) => {
      const next = { ...prev, ...updates };
      try {
        if (updates.theme !== undefined) {
          localStorage.setItem(THEME_STORAGE_KEY, updates.theme);
        }
        if (updates.defaultMode !== undefined) {
          localStorage.setItem(DEFAULT_MODE_STORAGE_KEY, updates.defaultMode);
          // If no active conversation, sync currentMode with new defaultMode
          if (!activeConversationId) {
            setCurrentMode(updates.defaultMode);
          }
        }
        if (updates.enterToSend !== undefined) {
          localStorage.setItem(ENTER_TO_SEND_STORAGE_KEY, String(updates.enterToSend));
        }
        if (updates.developerModeEnabled !== undefined) {
          localStorage.setItem(DEV_MODE_STORAGE_KEY, String(updates.developerModeEnabled));
        }
      } catch (err) {
        console.error('Failed to save preferences to localStorage', err);
      }
      return next;
    });
  };

  // Check backend health
  const checkBackendHealth = useCallback(async () => {
    setBackendStatus((prev) => ({
      ...prev,
      isChecking: true,
      endpointUrl: getApiBaseUrl(),
    }));

    try {
      await api.checkHealth();
      setBackendStatus({
        isChecking: false,
        isAvailable: true,
        lastChecked: new Date(),
        error: null,
        endpointUrl: getApiBaseUrl(),
      });
      return true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Connection failed';
      setBackendStatus({
        isChecking: false,
        isAvailable: false,
        lastChecked: new Date(),
        error: msg,
        endpointUrl: getApiBaseUrl(),
      });
      return false;
    }
  }, []);

  // Fetch conversations from backend
  const fetchConversations = useCallback(async () => {
    setIsLoadingConversations(true);
    try {
      const list = await api.getConversations();
      setConversations(list);
      return list;
    } catch (err: unknown) {
      console.warn('Failed to fetch conversations from backend:', err);
      setConversations([]);
      return [];
    } finally {
      setIsLoadingConversations(false);
    }
  }, []);

  // Load a conversation's history
  const loadConversation = useCallback(async (id: string) => {
    setIsLoadingMessages(true);
    setChatError(null);
    try {
      const data = await api.getConversation(id);
      setActiveConversation(data.conversation);
      if (data.conversation.mode) {
        setCurrentMode(data.conversation.mode);
      }
      setMessages(data.messages || []);
      setActiveConversationId(id);
      try {
        localStorage.setItem(LAST_CONV_STORAGE_KEY, id);
      } catch {
        // ignore
      }
    } catch (err: unknown) {
      console.error('Failed to load conversation history:', err);
      const msg = err instanceof Error ? err.message : 'Failed to retrieve conversation history.';
      setChatError(msg);
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const initialize = async () => {
      const isOnline = await checkBackendHealth();
      if (isOnline) {
        const list = await fetchConversations();
        const storedId = localStorage.getItem(LAST_CONV_STORAGE_KEY);
        if (storedId && list.some((c) => c.id === storedId)) {
          loadConversation(storedId);
        } else if (list.length > 0) {
          loadConversation(list[0].id);
        }
      }
    };

    initialize();
  }, [checkBackendHealth, fetchConversations, loadConversation]);

  // Auto-scroll when messages change
  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom();
    }
  }, [messages, isSending]);

  // Switch conversation
  const handleSelectConversation = (id: string) => {
    if (id === activeConversationId) return;
    loadConversation(id);
  };

  // Start a new chat
  const handleNewChat = () => {
    setActiveConversationId(null);
    setActiveConversation(null);
    setMessages([]);
    setCurrentMode(preferences.defaultMode);
    setChatError(null);
    setLastFailedMessage(null);
    try {
      localStorage.removeItem(LAST_CONV_STORAGE_KEY);
    } catch {
      // ignore
    }
  };

  const handleModeChange = async (newMode: IntelligenceMode) => {
    setCurrentMode(newMode);
    if (activeConversationId) {
      setActiveConversation((prev) => (prev ? { ...prev, mode: newMode } : null));
      try {
        await api.updateConversationMode(activeConversationId, newMode);
        fetchConversations();
      } catch (err) {
        console.warn('Could not persist mode change to backend:', err);
      }
    }
  };

  // Delete conversation
  const handleDeleteConversation = async (id: string) => {
    setIsDeletingId(id);
    try {
      await api.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));

      if (activeConversationId === id) {
        handleNewChat();
      }
    } catch (err: unknown) {
      console.error('Failed to delete conversation:', err);
      const msg = err instanceof Error ? err.message : 'Could not delete conversation.';
      setChatError(msg);
    } finally {
      setIsDeletingId(null);
    }
  };

  // Send message
  const handleSendMessage = async (textToSend: string) => {
    if (!textToSend.trim() || isSending) return;

    setChatError(null);
    setLastFailedMessage(null);

    // Optimistically add user message
    const userMessage: Message = {
      role: 'user',
      content: textToSend,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);

    let targetConvId = activeConversationId;

    try {
      // If no conversation currently selected, create one through backend
      if (!targetConvId) {
        const initialTitle = textToSend.slice(0, 32) + (textToSend.length > 32 ? '...' : '');
        const newConv = await api.createConversation(initialTitle, currentMode);
        targetConvId = newConv.id;
        setActiveConversationId(newConv.id);
        setActiveConversation({ ...newConv, mode: currentMode });
        try {
          localStorage.setItem(LAST_CONV_STORAGE_KEY, newConv.id);
        } catch {
          // ignore
        }
      }

      // Send to /api/chat with selected intelligence mode
      const response = await api.sendMessage(targetConvId, textToSend, currentMode);

      // Add assistant response to messages
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.reply,
        created_at: new Date().toISOString(),
        context_summary: response.context_summary,
        messages_in_context: response.messages_in_context,
        mode: response.mode || currentMode,
        model_label: response.model_label,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Update active conversation context metadata
      setActiveConversation((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          messages_in_context: response.messages_in_context,
          context_summary: response.context_summary,
        };
      });

      // Refresh list to update ordering and titles
      fetchConversations();
    } catch (err: unknown) {
      console.error('Error sending message:', err);
      const errorMsg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : 'Failed to send message to backend.';

      setChatError(errorMsg);
      setLastFailedMessage(textToSend);

      if (err instanceof ApiError && err.isNetworkError) {
        checkBackendHealth();
      }
    } finally {
      setIsSending(false);
    }
  };

  const handleRetryLastMessage = () => {
    if (lastFailedMessage) {
      setMessages((prev) => prev.slice(0, prev.length - 1));
      handleSendMessage(lastFailedMessage);
    }
  };

  const handleApiUrlChanged = () => {
    checkBackendHealth().then((isOnline) => {
      if (isOnline) {
        fetchConversations();
      }
    });
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-app-main text-app-primary">
      {/* Left Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        conversations={conversations}
        selectedId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        isLoadingConversations={isLoadingConversations}
        isDeletingId={isDeletingId}
        onOpenSettings={() => setIsSettingsOpen(true)}
        backendStatus={backendStatus}
        developerModeEnabled={preferences.developerModeEnabled}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full min-w-0 bg-app-main relative">
        {/* Top Header */}
        <ChatHeader
          conversation={activeConversation}
          onToggleSidebar={() => setIsSidebarOpen(true)}
          isSidebarOpen={isSidebarOpen}
          onNewChat={handleNewChat}
          onDeleteCurrent={
            activeConversationId ? () => handleDeleteConversation(activeConversationId) : undefined
          }
          messagesCount={messages.length}
        />

        {/* Backend Unreachable Alert Banner */}
        <BackendBanner
          isAvailable={backendStatus.isAvailable}
          isChecking={backendStatus.isChecking}
          onRetry={async () => {
            const online = await checkBackendHealth();
            if (online) fetchConversations();
          }}
          onOpenSettings={(tab) => {
            if (tab === 'developer') {
              updatePreferences({ developerModeEnabled: true });
            }
            setIsSettingsOpen(true);
          }}
          errorMessage={backendStatus.error}
          developerModeEnabled={preferences.developerModeEnabled}
        />

        {/* Messages / Welcome View */}
        <div
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto flex flex-col"
        >
          {isLoadingMessages ? (
            <div className="flex-1 flex items-center justify-center p-8">
              <div className="flex items-center gap-2 text-xs text-app-muted">
                <Loader2 className="w-4 h-4 animate-spin text-app-primary" />
                <span>Loading conversation history...</span>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <EmptyState
              onSelectPrompt={(prompt) => {
                setInput(prompt);
              }}
              onNewChat={handleNewChat}
            />
          ) : (
            <div className="py-4 space-y-1">
              {messages.map((msg, idx) => (
                <ChatMessage
                  key={msg.id || idx}
                  message={msg}
                />
              ))}

              {/* Waiting for backend response loading state */}
              {isSending && (
                <div className="w-full py-5 px-4 md:px-6 bg-app-main">
                  <div className="max-w-3xl mx-auto flex items-start gap-4">
                    <div className="w-7 h-7 rounded-full bg-app-composer border border-app-subtle text-app-primary flex items-center justify-center shrink-0 mt-0.5">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    </div>
                    <div className="flex items-center gap-2 text-xs text-app-muted py-1">
                      <span>Generating contextual response...</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Error banner if last send failed */}
              {chatError && (
                <div className="max-w-3xl mx-auto px-4 py-2">
                  <div className="p-3 bg-app-error border border-app-error rounded-xl flex items-center justify-between text-xs text-app-error">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      <span>{chatError}</span>
                    </div>
                    {lastFailedMessage && (
                      <button
                        onClick={handleRetryLastMessage}
                        className="px-2.5 py-1 bg-app-surface hover:bg-app-composer text-app-primary rounded transition-colors border border-app-subtle cursor-pointer"
                      >
                        Retry
                      </button>
                    )}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Chat Composer */}
        <ChatInput
          input={input}
          setInput={setInput}
          onSend={handleSendMessage}
          isLoading={isSending}
          disabled={!backendStatus.isAvailable && !backendStatus.isChecking}
          placeholder={
            !backendStatus.isAvailable
              ? 'Backend offline. Check settings or start FastAPI server...'
              : 'Message ContextAI...'
          }
          mode={currentMode}
          onModeChange={handleModeChange}
          enterToSend={preferences.enterToSend}
        />
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onApiUrlChanged={handleApiUrlChanged}
        preferences={preferences}
        onUpdatePreferences={updatePreferences}
      />
    </div>
  );
}
