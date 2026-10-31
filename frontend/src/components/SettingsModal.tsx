import React, { useState, useEffect } from 'react';
import {
  X,
  Palette,
  MessageSquare,
  Info,
  Terminal,
  Check,
  RefreshCw,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Zap,
  SlidersHorizontal,
  Brain,
  Keyboard,
} from 'lucide-react';
import { getApiBaseUrl, setApiBaseUrl, resetApiBaseUrl, api } from '../services/api';
import { HealthCheckResponse, IntelligenceMode, ThemeMode, UserPreferences } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApiUrlChanged: () => void;
  preferences: UserPreferences;
  onUpdatePreferences: (updates: Partial<UserPreferences>) => void;
}

type SettingsTab = 'general' | 'chat' | 'about' | 'developer';

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onApiUrlChanged,
  preferences,
  onUpdatePreferences,
}) => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('general');
  const [urlInput, setUrlInput] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    data?: HealthCheckResponse;
  } | null>(null);

  // Sync inputs on open
  useEffect(() => {
    if (isOpen) {
      setUrlInput(getApiBaseUrl());
      setTestResult(null);
      if (!preferences.developerModeEnabled && activeTab === 'developer') {
        setActiveTab('general');
      }
    }
  }, [isOpen, preferences.developerModeEnabled, activeTab]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSaveDevUrl = () => {
    if (!urlInput.trim()) return;
    setApiBaseUrl(urlInput);
    onApiUrlChanged();
  };

  const handleResetDevUrl = () => {
    const defaultUrl = resetApiBaseUrl();
    setUrlInput(defaultUrl);
    setTestResult(null);
    onApiUrlChanged();
  };

  const handleTestConnection = async () => {
    setApiBaseUrl(urlInput);
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.checkHealth();
      setTestResult({
        success: true,
        message: 'Connected successfully to ContextAI backend.',
        data: res,
      });
      onApiUrlChanged();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Connection failed';
      setTestResult({
        success: false,
        message: msg,
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
      <div className="bg-app-sidebar border border-app-subtle rounded-2xl w-full max-w-2xl h-[560px] max-h-[90vh] shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Top Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-app-subtle shrink-0 bg-app-sidebar">
          <h2 className="text-base font-semibold text-app-primary tracking-tight">Settings</h2>
          <button
            onClick={onClose}
            className="text-app-muted hover:text-app-primary p-1 rounded-lg transition-colors cursor-pointer"
            aria-label="Close settings"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body: Left Tab Navigation & Right Content */}
        <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
          {/* Tabs Sidebar */}
          <div className="w-full md:w-52 border-b md:border-b-0 md:border-r border-app-subtle p-2 md:p-3 flex md:flex-col gap-1 shrink-0 overflow-x-auto bg-app-sidebar">
            <button
              onClick={() => setActiveTab('general')}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors whitespace-nowrap text-left cursor-pointer ${
                activeTab === 'general'
                  ? 'bg-app-surface text-app-primary'
                  : 'text-app-secondary hover:bg-app-hover hover:text-app-primary'
              }`}
            >
              <Palette className="w-4 h-4 text-app-muted" />
              <span>General</span>
            </button>

            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors whitespace-nowrap text-left cursor-pointer ${
                activeTab === 'chat'
                  ? 'bg-app-surface text-app-primary'
                  : 'text-app-secondary hover:bg-app-hover hover:text-app-primary'
              }`}
            >
              <MessageSquare className="w-4 h-4 text-app-muted" />
              <span>Chat Preferences</span>
            </button>

            <button
              onClick={() => setActiveTab('about')}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors whitespace-nowrap text-left cursor-pointer ${
                activeTab === 'about'
                  ? 'bg-app-surface text-app-primary'
                  : 'text-app-secondary hover:bg-app-hover hover:text-app-primary'
              }`}
            >
              <Info className="w-4 h-4 text-app-muted" />
              <span>About</span>
            </button>

            {/* Developer tab - ONLY visible when Developer Mode is enabled */}
            {preferences.developerModeEnabled && (
              <button
                onClick={() => setActiveTab('developer')}
                className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-colors whitespace-nowrap text-left cursor-pointer ${
                  activeTab === 'developer'
                    ? 'bg-app-surface text-app-primary'
                    : 'text-amber-500 hover:bg-app-hover hover:text-amber-600'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Terminal className="w-4 h-4 text-amber-500" />
                  <span>Developer</span>
                </div>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-600 border border-amber-500/20 font-medium">
                  Dev
                </span>
              </button>
            )}
          </div>

          {/* Tab Content Area */}
          <div className="flex-1 p-6 overflow-y-auto bg-app-main text-xs text-app-secondary space-y-6">
            {/* GENERAL TAB */}
            {activeTab === 'general' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-app-primary mb-1">Appearance</h3>
                  <p className="text-app-muted text-xs">
                    Customize how ContextAI looks on your screen.
                  </p>
                </div>

                <div className="space-y-3">
                  <label className="text-xs font-medium text-app-primary block">Theme</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(['dark', 'system', 'light'] as ThemeMode[]).map((t) => {
                      const isSelected = preferences.theme === t;
                      const label = t === 'dark' ? 'Dark (Default)' : t === 'light' ? 'Light' : 'System';
                      return (
                        <button
                          key={t}
                          type="button"
                          onClick={() => onUpdatePreferences({ theme: t })}
                          className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
                            isSelected
                              ? 'bg-app-composer border-app-primary text-app-primary font-semibold shadow-xs'
                              : 'bg-app-surface border-app-subtle text-app-secondary hover:text-app-primary hover:bg-app-composer'
                          }`}
                        >
                          {isSelected && <Check className="w-3.5 h-3.5 text-app-primary" />}
                          <span>{label}</span>
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-[11px] text-app-muted">
                    Switch between the classic neutral dark theme and the crisp light theme with optimized contrast.
                  </p>
                </div>
              </div>
            )}

            {/* CHAT PREFERENCES TAB */}
            {activeTab === 'chat' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-app-primary mb-1">Chat Preferences</h3>
                  <p className="text-app-muted text-xs">
                    Configure default model intelligence and messaging shortcuts.
                  </p>
                </div>

                {/* Default Mode Selector */}
                <div className="space-y-3">
                  <label className="text-xs font-medium text-app-primary block">
                    Default Intelligence Mode
                  </label>
                  <div className="space-y-2">
                    {[
                      {
                        id: 'swift',
                        name: 'Swift',
                        desc: 'Optimized for speed and concise answers',
                        icon: Zap,
                      },
                      {
                        id: 'balanced',
                        name: 'Balanced',
                        desc: 'Everyday intelligence with balanced quality & speed (Default)',
                        icon: SlidersHorizontal,
                      },
                      {
                        id: 'deep',
                        name: 'Deep',
                        desc: 'Advanced reasoning, multi-step problem solving & complex tasks',
                        icon: Brain,
                      },
                    ].map((item) => {
                      const isSelected = preferences.defaultMode === item.id;
                      const ItemIcon = item.icon;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => onUpdatePreferences({ defaultMode: item.id as IntelligenceMode })}
                          className={`w-full flex items-center justify-between p-3 rounded-xl border text-left transition-colors cursor-pointer ${
                            isSelected
                              ? 'bg-app-surface border-app-primary text-app-primary'
                              : 'bg-app-main border-app-subtle text-app-secondary hover:bg-app-surface hover:text-app-primary'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div
                              className={`w-7 h-7 rounded-lg flex items-center justify-center border ${
                                isSelected
                                  ? 'bg-app-composer border-app-subtle text-app-primary'
                                  : 'bg-app-surface border-app-subtle text-app-muted'
                              }`}
                            >
                              <ItemIcon className="w-3.5 h-3.5" />
                            </div>
                            <div>
                              <div className="font-medium text-app-primary text-xs">{item.name}</div>
                              <div className="text-[11px] text-app-muted">{item.desc}</div>
                            </div>
                          </div>
                          {isSelected && <Check className="w-4 h-4 text-app-primary shrink-0 ml-2" />}
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-[11px] text-app-muted">
                    Newly created conversations will begin in this mode. You can still switch modes anytime in the chat composer.
                  </p>
                </div>

                {/* Enter to Send Toggle */}
                <div className="pt-4 border-t border-app-subtle space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs font-medium text-app-primary flex items-center gap-1.5">
                        <Keyboard className="w-3.5 h-3.5 text-app-muted" />
                        <span>Send Message Shortcut</span>
                      </div>
                      <div className="text-[11px] text-app-muted mt-0.5">
                        Choose how keyboard shortcuts trigger message submission.
                      </div>
                    </div>

                    <button
                      type="button"
                      role="switch"
                      aria-checked={preferences.enterToSend}
                      onClick={() => onUpdatePreferences({ enterToSend: !preferences.enterToSend })}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                        preferences.enterToSend ? 'bg-btn-primary' : 'bg-app-surface border border-app-subtle'
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-app-main shadow-sm ring-0 transition duration-200 ease-in-out ${
                          preferences.enterToSend ? 'translate-x-4' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>

                  <div className="bg-app-sidebar p-2.5 rounded-lg border border-app-subtle text-[11px] text-app-muted">
                    {preferences.enterToSend ? (
                      <span>
                        <strong className="text-app-primary">Enter</strong> sends message. <strong className="text-app-primary">Shift + Enter</strong> inserts a new line.
                      </span>
                    ) : (
                      <span>
                        <strong className="text-app-primary">Ctrl + Enter</strong> sends message. <strong className="text-app-primary">Enter</strong> inserts a new line.
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ABOUT TAB */}
            {activeTab === 'about' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-sm font-semibold text-app-primary mb-1">About ContextAI</h3>
                  <p className="text-app-muted text-xs">
                    Application details and system capabilities.
                  </p>
                </div>

                <div className="bg-app-sidebar border border-app-subtle rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between pb-3 border-b border-app-subtle">
                    <div>
                      <div className="text-sm font-semibold text-app-primary">ContextAI</div>
                      <div className="text-[11px] text-app-muted">
                        Stateful LLM Chatbot with Contextual Memory
                      </div>
                    </div>
                    <span className="text-[11px] font-mono bg-app-surface px-2 py-0.5 rounded text-app-primary border border-app-subtle">
                      v1.1.0
                    </span>
                  </div>

                  <div className="space-y-2 text-[11px] leading-relaxed">
                    <p>
                      ContextAI retains conversational context across multi-turn interactions, allowing the assistant to remember details, follow-up instructions, and problem constraints.
                    </p>
                    <div className="pt-2 flex items-center justify-between text-app-muted">
                      <span>Persistence Layer</span>
                      <span className="text-app-primary font-medium">SQLite Database</span>
                    </div>
                    <div className="flex items-center justify-between text-app-muted">
                      <span>Privacy & Security</span>
                      <span className="text-app-primary font-medium">Server-Isolated Credentials</span>
                    </div>
                  </div>
                </div>

                {/* Developer Mode Activation Section */}
                <div className="pt-4 border-t border-app-subtle space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs font-medium text-app-primary flex items-center gap-1.5">
                        <Terminal className="w-3.5 h-3.5 text-app-muted" />
                        <span>Developer Mode</span>
                      </div>
                      <div className="text-[11px] text-app-muted mt-0.5">
                        Enable developer settings to configure custom backend endpoints and connection diagnostics.
                      </div>
                    </div>

                    <button
                      type="button"
                      role="switch"
                      aria-checked={preferences.developerModeEnabled}
                      onClick={() => {
                        const next = !preferences.developerModeEnabled;
                        onUpdatePreferences({ developerModeEnabled: next });
                        if (next) {
                          setActiveTab('developer');
                        }
                      }}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                        preferences.developerModeEnabled ? 'bg-amber-500' : 'bg-app-surface border border-app-subtle'
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-app-main shadow-sm ring-0 transition duration-200 ease-in-out ${
                          preferences.developerModeEnabled ? 'translate-x-4' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>

                  {preferences.developerModeEnabled && (
                    <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-600 dark:text-amber-300 text-[11px] flex items-center justify-between">
                      <span>Developer Mode is active. Developer configuration tab is now accessible.</span>
                      <button
                        type="button"
                        onClick={() => setActiveTab('developer')}
                        className="underline hover:opacity-80 font-medium cursor-pointer"
                      >
                        Open Developer Tab
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* DEVELOPER TAB (Isolated from regular users) */}
            {activeTab === 'developer' && preferences.developerModeEnabled && (
              <div className="space-y-6">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-app-primary">Developer Configuration</h3>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-600 dark:text-amber-300 border border-amber-500/20 font-medium">
                      Advanced
                    </span>
                  </div>
                  <p className="text-app-muted text-xs mt-1">
                    Configure backend API routes, verify connectivity, and inspect service diagnostics.
                  </p>
                </div>

                {/* Endpoint Editor */}
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-app-primary">
                    Backend Service Endpoint URL
                  </label>
                  <p className="text-[11px] text-app-muted">
                    Specifies the target host for REST API calls (<code className="bg-app-surface px-1 py-0.5 rounded font-mono text-app-primary">/api/*</code> and <code className="bg-app-surface px-1 py-0.5 rounded font-mono text-app-primary">/health</code>).
                  </p>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      placeholder="http://localhost:8000"
                      className="flex-1 bg-app-sidebar border border-app-subtle focus:border-app-hover rounded-lg px-3 py-2 text-app-primary text-xs font-mono outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleTestConnection}
                      disabled={testing || !urlInput.trim()}
                      className="flex items-center gap-1.5 px-3 py-2 bg-app-surface hover:bg-app-composer border border-app-subtle text-app-primary rounded-lg transition-colors shrink-0 disabled:opacity-50 cursor-pointer"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
                      <span>Test</span>
                    </button>
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <button
                      type="button"
                      onClick={handleResetDevUrl}
                      className="flex items-center gap-1 text-[11px] text-app-muted hover:text-app-primary transition-colors cursor-pointer"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>Reset to default</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveDevUrl}
                      className="px-2.5 py-1 text-xs font-medium bg-btn-primary rounded-md transition-colors cursor-pointer"
                    >
                      Save Endpoint
                    </button>
                  </div>
                </div>

                {/* Test results banner */}
                {testResult && (
                  <div
                    className={`p-3 rounded-lg border flex items-start gap-2.5 text-xs ${
                      testResult.success
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-300'
                        : 'bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-300'
                    }`}
                  >
                    {testResult.success ? (
                      <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-500 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-4 h-4 shrink-0 text-red-500 mt-0.5" />
                    )}
                    <div className="space-y-1">
                      <div className="font-medium">{testResult.message}</div>
                      {testResult.data && (
                        <div className="text-[11px] opacity-85 font-mono">
                          Status: {String(testResult.data.status || 'OK')}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Architecture & Security Notes */}
                <div className="pt-3 border-t border-app-subtle space-y-2">
                  <div className="flex items-center gap-1.5 text-app-primary font-medium">
                    <ShieldCheck className="w-3.5 h-3.5 text-app-primary" />
                    <span>Security & Credential Isolation</span>
                  </div>
                  <ul className="space-y-1.5 text-[11px] text-app-muted leading-relaxed">
                    <li>
                      <strong className="text-app-primary">Zero Client Secrets:</strong> Model keys and tokens never enter the browser runtime.
                    </li>
                    <li>
                      <strong className="text-app-primary">Direct FastAPI Handlers:</strong> Persistence, conversational memory, and thinking levels are managed server-side.
                    </li>
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Bottom Footer */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-app-subtle bg-app-sidebar shrink-0">
          <div className="text-[11px] text-app-muted">
            {activeTab === 'developer'
              ? 'Developer configuration saved locally'
              : 'Preferences saved automatically'}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium bg-btn-primary rounded-lg transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
