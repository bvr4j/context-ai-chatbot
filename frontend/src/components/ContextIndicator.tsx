import React, { useState } from 'react';
import { Brain, Sparkles, ChevronDown, ChevronUp, Layers, CheckCircle2 } from 'lucide-react';

interface ContextIndicatorProps {
  messagesInContext?: number;
  contextSummary?: string | null;
  totalMessagesCount?: number;
}

export const ContextIndicator: React.FC<ContextIndicatorProps> = ({
  messagesInContext,
  contextSummary,
  totalMessagesCount = 0,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const hasContextData = typeof messagesInContext === 'number' || (contextSummary && contextSummary.trim().length > 0);

  if (!hasContextData && totalMessagesCount === 0) {
    return null;
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 px-2.5 py-1 text-xs text-app-secondary hover:text-app-primary bg-app-surface hover:bg-app-composer border border-app-subtle rounded-md transition-colors cursor-pointer"
        title="View conversation context and memory status"
        aria-expanded={isExpanded}
      >
        <Brain className="w-3.5 h-3.5 text-app-secondary" />
        <span>
          {typeof messagesInContext === 'number'
            ? `${messagesInContext} in context`
            : totalMessagesCount > 0
            ? 'Context active'
            : 'Context standby'}
        </span>
        {isExpanded ? (
          <ChevronUp className="w-3 h-3 text-app-muted" />
        ) : (
          <ChevronDown className="w-3 h-3 text-app-muted" />
        )}
      </button>

      {isExpanded && (
        <div className="absolute right-0 mt-2 w-80 bg-app-sidebar border border-app-subtle rounded-lg shadow-xl p-4 z-50 text-left text-xs text-app-secondary animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between pb-2 mb-3 border-b border-app-subtle">
            <div className="flex items-center gap-1.5 text-app-primary font-medium">
              <Sparkles className="w-4 h-4" />
              <span>Context & Memory State</span>
            </div>
            <span className="text-[10px] text-app-muted">FastAPI Backend</span>
          </div>

          <div className="space-y-3">
            <div>
              <div className="text-[11px] text-app-muted mb-1 flex items-center justify-between">
                <span>Messages In Active Context</span>
                <span className="text-app-primary font-mono font-medium">
                  {typeof messagesInContext === 'number' ? messagesInContext : 'Pending backend sync'}
                </span>
              </div>
              <div className="w-full bg-app-surface h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-app-primary h-full transition-all duration-300"
                  style={{
                    width: `${Math.min(100, Math.max(10, ((messagesInContext || 0) / 20) * 100))}%`,
                  }}
                />
              </div>
            </div>

            <div>
              <div className="text-[11px] text-app-muted mb-1">Retained Context Memory</div>
              {contextSummary ? (
                <div className="bg-app-main border border-app-subtle p-2.5 rounded text-app-primary text-[11px] leading-relaxed max-h-36 overflow-y-auto">
                  {contextSummary}
                </div>
              ) : (
                <div className="text-app-muted italic bg-app-main border border-app-subtle p-2 rounded text-[11px]">
                  No memory summary provided by backend yet. Context will be summarized as the conversation grows.
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-app-subtle flex items-center justify-between text-[11px] text-app-muted">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-app-primary" />
                <span>Stateful Persistence</span>
              </div>
              <div className="flex items-center gap-1">
                <Layers className="w-3 h-3" />
                <span>SQLite DB</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
