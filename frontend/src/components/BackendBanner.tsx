import React from 'react';
import { AlertCircle, RefreshCw, Terminal } from 'lucide-react';
import { getApiBaseUrl } from '../services/api';

interface BackendBannerProps {
  isAvailable: boolean;
  isChecking: boolean;
  onRetry: () => void;
  onOpenSettings: (openTab?: 'general' | 'chat' | 'about' | 'developer') => void;
  errorMessage?: string | null;
  developerModeEnabled?: boolean;
}

export const BackendBanner: React.FC<BackendBannerProps> = ({
  isAvailable,
  isChecking,
  onRetry,
  onOpenSettings,
  errorMessage,
  developerModeEnabled = false,
}) => {
  if (isAvailable) return null;

  const currentUrl = getApiBaseUrl();

  return (
    <div className="w-full bg-app-error border-b border-app-error px-4 py-2 text-xs text-app-error transition-all">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {developerModeEnabled ? (
            <span>
              <strong>Backend Unreachable:</strong> Cannot connect to FastAPI server at{' '}
              <code className="bg-black/20 px-1 py-0.5 rounded font-mono text-[11px] font-medium">
                {currentUrl}
              </code>
              {errorMessage ? ` (${errorMessage})` : ''}
            </span>
          ) : (
            <span>
              <strong>Service Offline:</strong> ContextAI is currently unable to reach the service. Please try reconnecting.
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
          <button
            onClick={onRetry}
            disabled={isChecking}
            className="flex items-center gap-1 px-2.5 py-1 bg-black/20 hover:bg-black/30 rounded transition-colors text-xs font-medium disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-3 h-3 ${isChecking ? 'animate-spin' : ''}`} />
            <span>Retry</span>
          </button>
          <button
            onClick={() => onOpenSettings(developerModeEnabled ? 'developer' : 'about')}
            className="flex items-center gap-1 px-2.5 py-1 bg-black/10 hover:bg-black/20 rounded transition-colors text-xs border border-current/20 cursor-pointer"
          >
            <Terminal className="w-3 h-3" />
            <span>{developerModeEnabled ? 'Configure' : 'Dev Mode'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
